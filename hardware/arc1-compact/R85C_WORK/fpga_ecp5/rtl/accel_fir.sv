// ARC-1 Compact R8.5-C -- resident FIR / convolution engine (AJOB opcodes 2 FIR_SET_IR and 3 FIR_BLOCK).
//
// State kept in the FPGA between jobs (only new samples and results cross the host link):
//   ir[0..1023]  Q15 taps (written by FIR_SET_IR)
//   x[]          2048-entry circular sample history, zero after configuration
// Output for a block of n new samples written at history positions wp..wp+n-1:
//   y[j] = sat16( (sum_{t=0}^{1023} ir[t] * x[wp+j-t]) >>> 15 )        (arithmetic shift, then clamp)
// Bit-exact reference: firmware/src/accel_job.c (ajob_ref_*).
// Schedule: 32 output lanes per block. A descending sample stream v_k = x[base+31-k] is shifted into a 32-entry
// window (lane 0 = newest entry). After 32 preload shifts, lane l holds x[base+l]; for tap t the MAC uses the window,
// then v_{32+t} = x[base-1-t] is shifted in. 32 MULT18X18D in parallel, 1056 stream cycles + pipeline per block.
// Evidence: RTL_SIMULATED (tb_ecp5_top) + routed build. Not on silicon.
`default_nettype none
module accel_fir (
    input  wire        clk,
    input  wire        rst,
    // tap / history writes from the job engine
    input  wire        ir_we,
    input  wire [9:0]  ir_waddr,
    input  wire [15:0] ir_wdata,
    input  wire        x_we,
    input  wire [10:0] x_waddr,
    input  wire [15:0] x_wdata,
    // block control
    input  wire        start,          // pulse: compute n outputs for samples at base..base+n-1
    input  wire [10:0] base,
    input  wire [10:0] n,              // 1..1024
    output reg         busy,
    // output samples, in order; consumer pops one per pop pulse
    output wire        out_avail,
    output wire [15:0] out_sample,
    input  wire        out_pop,
    input  wire        abort
);
    // ---------------- memories (inferred DP16KD) ----------------
    reg [15:0] irm [0:1023];
    reg [15:0] xm  [0:2047];
    integer z;
    initial begin
        for (z = 0; z < 1024; z = z + 1) irm[z] = 16'd0;
        for (z = 0; z < 2048; z = z + 1) xm[z] = 16'd0;
    end
    reg [9:0]  ir_raddr;
    reg [10:0] x_raddr;
    reg [15:0] ir_q, x_q;
    always @(posedge clk) begin
        if (ir_we) irm[ir_waddr] <= ir_wdata;
        if (x_we)  xm[x_waddr]   <= x_wdata;
        ir_q <= irm[ir_raddr];
        x_q  <= xm[x_raddr];
    end

    // ---------------- control ----------------
    localparam [2:0] F_IDLE = 0, F_STREAM = 1, F_DRAIN = 2, F_OUT = 3, F_NEXT = 4;
    reg [2:0]  st;
    reg [10:0] blk_base;          // base + j0 of the current block
    reg [10:0] left;              // outputs still to produce (including this block)
    reg [10:0] k;                 // stream index 0..1055
    reg        va, ma;            // address issued this cycle / it is a MAC tap
    reg        v1, m1;            // RAM output valid / MAC tap (aligned with ir_q/x_q, 2 clocks after issue)
    reg        vb, mb;            // broadcast register stage (timing: BRAM -> FF -> 32 multipliers)
    reg signed [15:0] ir_b, x_b;
    reg        m2;                // product valid
    reg [5:0]  drain;
    reg signed [15:0] win [0:31];
    reg signed [31:0] prod [0:31];
    reg signed [43:0] acc  [0:31];
    reg signed [43:0] osr  [0:31];
    reg [5:0]  ocnt;              // outputs waiting in osr
    integer l;

    function automatic [15:0] sat16(input signed [43:0] a);
        reg signed [43:0] s;
        begin
            s = a >>> 15;
            if (s > 44'sd32767) sat16 = 16'h7FFF;
            else if (s < -44'sd32768) sat16 = 16'h8000;
            else sat16 = s[15:0];
        end
    endfunction

    assign out_avail  = ocnt != 6'd0;
    assign out_sample = sat16(osr[0]);

    always @(posedge clk) begin
        // RAM address issue: stream v_k = x[blk_base + 31 - k], tap t = k - 32
        va <= 1'b0; ma <= 1'b0; v1 <= va; m1 <= ma; vb <= v1; mb <= m1 & v1; m2 <= mb & vb;
        ir_b <= $signed(ir_q); x_b <= $signed(x_q);
        if (st == F_STREAM) begin
            x_raddr  <= blk_base + 11'd31 - k;
            ir_raddr <= k[9:0] - 10'd32;
            va <= 1'b1;
            ma <= k >= 11'd32;
            k  <= k + 11'd1;
            if (k == 11'd1055) st <= F_DRAIN;
        end
        // stage 1: product with the current window, then shift the new sample in
        if (vb) begin
            for (l = 0; l < 32; l = l + 1) prod[l] <= ir_b * win[l];
            for (l = 31; l > 0; l = l - 1) win[l] <= win[l - 1];
            win[0] <= x_b;
        end
        // stage 2: accumulate (m2 marks a valid MAC product; m1 was registered with the RAM outputs)
        if (m2)
            for (l = 0; l < 32; l = l + 1) acc[l] <= acc[l] + {{12{prod[l][31]}}, prod[l]};
        if (out_pop && ocnt != 6'd0) begin
            for (l = 0; l < 31; l = l + 1) osr[l] <= osr[l + 1];
            ocnt <= ocnt - 6'd1;
        end
        case (st)
        F_IDLE: if (start) begin
            busy <= 1'b1; blk_base <= base; left <= n; k <= 11'd0; st <= F_STREAM;
            for (l = 0; l < 32; l = l + 1) acc[l] <= 44'sd0;
        end
        F_STREAM: ;                                     // address issue handled above
        F_DRAIN: begin                                  // let the last products reach the accumulators
            drain <= drain + 6'd1;
            if (drain == 6'd6) begin drain <= 6'd0; st <= F_OUT; end
        end
        F_OUT: if (ocnt == 6'd0) begin                   // previous block fully consumed
            for (l = 0; l < 32; l = l + 1) osr[l] <= acc[l];
            ocnt <= (left > 11'd32) ? 6'd32 : left[5:0];
            st <= F_NEXT;
        end
        F_NEXT: begin
            if (left > 11'd32) begin
                left <= left - 11'd32; blk_base <= blk_base + 11'd32; k <= 11'd0; st <= F_STREAM;
                for (l = 0; l < 32; l = l + 1) acc[l] <= 44'sd0;
            end else if (ocnt == 6'd0) begin
                busy <= 1'b0; st <= F_IDLE;
            end
        end
        default: st <= F_IDLE;
        endcase
        if (rst || abort) begin
            st <= F_IDLE; busy <= 1'b0; ocnt <= 6'd0; drain <= 6'd0; k <= 11'd0;
            va <= 1'b0; ma <= 1'b0; v1 <= 1'b0; m1 <= 1'b0; vb <= 1'b0; mb <= 1'b0; m2 <= 1'b0;
        end
    end
endmodule
`default_nettype wire
