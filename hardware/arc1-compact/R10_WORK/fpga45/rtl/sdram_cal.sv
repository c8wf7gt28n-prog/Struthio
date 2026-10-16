// ARC-1 R10 -- SDRAM interface calibration for the 45F (analysis/R10_SDRAM_TIMING.md section 2).
// The SDRAM clock comes from a PLL output whose phase can be stepped (EHXPLLL dynamic phase, PHASES steps per clock
// period). For each capture latency (rd_extra 0/1) the calibrator walks the phase once round the full period; at each
// step it re-initialises the SDRAM (PRE ALL / refreshes / MRS, so a command mis-sampled at a bad phase cannot leave a
// wrong mode behind), writes TEST_WORDS words of a step-dependent pattern and reads them back. The pass map is then
// searched for the longest circular run of passing phases; the calibrator steps to the centre of the best run (over
// both latencies), selects that latency, re-initialises once more and reports done. No passing phase -> fail.
// The command window and the read window move together with the phase, so a pass means both are met.
// Evidence: RTL_SIMULATED (tb_sdram, P_CAL = 1, with I/O + board delays in the SDRAM model). Not on silicon.
`default_nettype none
module sdram_cal #(
    parameter integer PHASES     = 56,          // steps per clock period (12.5 ns / 223 ps at VCO 560 MHz -- bench-verify)
    parameter integer TEST_WORDS = 16,
    parameter integer SETTLE     = 32           // clocks after a phase step
) (
    input  wire        clk,
    input  wire        rst,
    input  wire        init_done,               // from sdram_ctrl
    output reg         reinit,
    output reg         rd_extra,
    output reg         phase_step,              // one pulse = one PLL phase step
    output reg         busy, done, fail,
    output reg  [6:0]  win_width,               // passing steps in the chosen run
    output reg  [6:0]  win_center,
    // command port (while busy)
    output reg         cmd_valid,
    input  wire        cmd_ready,
    output reg         cmd_write,
    output reg  [23:0] cmd_addr,
    output wire [9:0]  cmd_len,
    input  wire        wr_ready,
    output wire [15:0] wr_data,
    input  wire        rd_valid,
    input  wire [15:0] rd_data
);
    assign cmd_len = TEST_WORDS[9:0];
    localparam [23:0] TADDR = {2'd3, 13'h1ABC, 9'd64};       // bank 3, a row away from the self-test area
    reg [6:0]  step;
    reg        ex;
    reg [63:0] pass0, pass1;
    reg [9:0]  wi, ri;
    reg        bad;
    reg [7:0]  cnt;
    // pattern differs per step and latency, so stale data from a previous step cannot pass
    function automatic [15:0] pat(input [6:0] s, input e, input [9:0] i);
        pat = {i[6:0], e, 1'b0, s} ^ 16'h5AA5 ^ {i[3:0], i[3:0], i[3:0], i[3:0]};
    endfunction
    assign wr_data = pat(step, ex, wi);

    localparam [3:0] C_IDLE = 0, C_REINIT = 1, C_WINIT = 2, C_WCMD = 3, C_WDATA = 4, C_RCMD = 5, C_RDATA = 6,
                     C_STEP = 7, C_SETTLE = 8, C_SCAN = 9, C_GOTO = 10, C_FINAL = 11, C_WFINAL = 12, C_CTR = 13;
    reg [3:0] st;
    // longest circular run search
    reg [7:0]  si;
    reg [6:0]  run, best;
    reg [6:0]  best_end;
    reg        best_ex, scan_ex;
    reg [6:0]  goto_left;
    reg  [6:0] sj;                                   // si mod PHASES, kept as a wrapping counter (no divider)
    wire       pbit = scan_ex ? pass1[sj[5:0]] : pass0[sj[5:0]];
    reg  [7:0] ctr;

    always @(posedge clk) begin
        reinit <= 1'b0; phase_step <= 1'b0;
        if (rst) begin
            st <= C_IDLE; busy <= 1'b0; done <= 1'b0; fail <= 1'b0; cmd_valid <= 1'b0; rd_extra <= 1'b0;
            pass0 <= 64'd0; pass1 <= 64'd0; step <= 7'd0; ex <= 1'b0;
        end else case (st)
        C_IDLE: if (init_done && !done && !fail) begin busy <= 1'b1; step <= 7'd0; ex <= 1'b0; rd_extra <= 1'b0; st <= C_REINIT; end
        C_REINIT: begin reinit <= 1'b1; cnt <= 8'd0; if (!init_done) st <= C_WINIT; end   // held until accepted
        C_WINIT: begin                                       // init_done drops on reinit, then rises again
            if (cnt != 8'hFF) cnt <= cnt + 8'd1;
            if (cnt > 8'd4 && init_done) begin wi <= 10'd0; ri <= 10'd0; bad <= 1'b0; st <= C_WCMD; end
        end
        C_WCMD: begin
            cmd_valid <= 1'b1; cmd_write <= 1'b1; cmd_addr <= TADDR;
            if (cmd_valid && cmd_ready) begin cmd_valid <= 1'b0; st <= C_WDATA; end
        end
        C_WDATA: if (wr_ready) begin
            wi <= wi + 10'd1;
            if (wi == TEST_WORDS[9:0] - 10'd1) st <= C_RCMD;
        end
        C_RCMD: begin
            cmd_valid <= 1'b1; cmd_write <= 1'b0; cmd_addr <= TADDR; cnt <= 8'd0;
            if (cmd_valid && cmd_ready) begin cmd_valid <= 1'b0; st <= C_RDATA; end
        end
        C_RDATA: begin
            cnt <= cnt + 8'd1;
            if (rd_valid) begin
                if (rd_data != pat(step, ex, ri)) bad <= 1'b1;
                ri <= ri + 10'd1;
            end
            if ((rd_valid && ri == TEST_WORDS[9:0] - 10'd1) || cnt == 8'd200) begin
                if (ex) pass1[step[5:0]] <= !bad && !(rd_valid && rd_data != pat(step, ex, ri)) && rd_valid;
                else    pass0[step[5:0]] <= !bad && !(rd_valid && rd_data != pat(step, ex, ri)) && rd_valid;
                st <= C_STEP;
            end
        end
        C_STEP: begin
            phase_step <= 1'b1; cnt <= 8'd0; st <= C_SETTLE;
            if (step == PHASES[6:0] - 7'd1) begin            // a full turn: back at phase 0
                step <= 7'd0;
                if (ex) begin si <= 8'd0; sj <= 7'd0; run <= 7'd0; best <= 7'd0; best_end <= 7'd0; best_ex <= 1'b0; scan_ex <= 1'b0; end
                ex <= ~ex;
            end else step <= step + 7'd1;
        end
        C_SETTLE: begin
            cnt <= cnt + 8'd1;
            if (cnt == SETTLE[7:0]) begin
                if (step == 7'd0 && !ex) st <= C_SCAN;      // both latencies done
                else begin rd_extra <= ex; st <= C_REINIT; end
            end
        end
        C_SCAN: begin                                        // two passes per latency over 2*PHASES positions
            if (pbit) begin
                if (run + 7'd1 > best && run < PHASES[6:0]) begin best <= run + 7'd1; best_end <= sj; best_ex <= scan_ex; end
                if (run < PHASES[6:0]) run <= run + 7'd1;
            end else run <= 7'd0;
            sj <= (sj == PHASES[6:0] - 7'd1) ? 7'd0 : sj + 7'd1;
            if (si == 8'd2 * PHASES[7:0] - 8'd1) begin
                si <= 8'd0; sj <= 7'd0; run <= 7'd0;
                if (scan_ex) begin
                    if (best == 7'd0) begin fail <= 1'b1; busy <= 1'b0; st <= C_IDLE; end
                    else begin
                        ctr <= {1'b0, best_end} + PHASES[7:0] - {2'b0, best[6:1]};   // in [P/2, 2P): one subtract
                        st <= C_CTR;
                    end
                end
                scan_ex <= 1'b1;
            end else si <= si + 8'd1;
        end
        C_CTR: begin
            win_width <= best;
            win_center <= (ctr >= PHASES[7:0]) ? ctr[6:0] - PHASES[6:0] : ctr[6:0];
            goto_left  <= (ctr >= PHASES[7:0]) ? ctr[6:0] - PHASES[6:0] : ctr[6:0];
            rd_extra <= best_ex; cnt <= 8'd0; st <= C_GOTO;
        end
        C_GOTO: begin                                        // step from phase 0 to the centre
            cnt <= cnt + 8'd1;
            if (goto_left == 7'd0) st <= C_FINAL;
            else if (cnt == 8'd8) begin phase_step <= 1'b1; goto_left <= goto_left - 7'd1; cnt <= 8'd0; end
        end
        C_FINAL: begin reinit <= 1'b1; cnt <= 8'd0; if (!init_done) st <= C_WFINAL; end
        C_WFINAL: begin
            if (cnt != 8'hFF) cnt <= cnt + 8'd1;
            if (cnt > 8'd4 && init_done) begin busy <= 1'b0; done <= 1'b1; st <= C_IDLE; end
        end
        default: st <= C_IDLE;
        endcase
    end
endmodule
`default_nettype wire
