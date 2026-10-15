// ARC-1 Compact R06 -- behavioural + protocol-checking model of AP Memory
// APS6404L-3SQR (64 Mbit QSPI PSRAM). SIMULATION ONLY, not vendor IP.
//
// Written from "APM SPI 3V PSRAM Datasheet Rev. 2.7 (2024-01-05)": command
// table 9.5, power-up section 8, reset section 14, Read ID figure 13, wrap
// section 10, AC table 10. Behaviour the datasheet does not define is marked
// MODEL ASSUMPTION and must be confirmed on a bench:
//   * a command terminated (CE# high) before 8 command bits is ignored;
//   * a write terminated mid-byte discards the partial byte;
//   * EID bytes after MF ID / KGD are arbitrary here (0x40 0x00 ...);
//   * memory content after power-up is pseudo-random here; contents across a
//     software reset are retained here.
//
// Every detected rule breach increments `violations` and prints MODEL_VIOLATION.
`timescale 1ns/1ps
module aps6404l_model #(
    parameter real TACLK    = 5.0,      // CLK fall -> data out (2..5.5 ns)
    parameter real THZ      = 5.5,      // CE# high -> high-Z
    parameter real TPU_NS   = 150000.0,
    parameter real TCEM_NS  = 8000.0,   // 3000.0 for the X (105 C) grade
    parameter real TCPH_NS  = 18.0,
    parameter real TCSP_NS  = 2.5,
    parameter real TCHD_NS  = 3.0,
    parameter real TSP_NS   = 2.0,
    parameter real THD_NS   = 2.0,
    parameter real TRST_NS  = 50.0,
    parameter real TCLK_LIN = 11.9,     // linear burst / page-cross min period
    parameter real TCLK_RD03= 30.3,     // 'h03 and 'h9F min period (33 MHz)
    parameter real TCLK_Q0B = 15.1,     // QPI 'h0B min period (66 MHz)
    parameter integer SEED  = 32'h5EED_A5A5
) (
    input  wire       ce_n,
    input  wire       sclk,
    inout  wire [3:0] sio
);
    // ---------------- storage ----------------
    reg [7:0] mem [0:8388607];

    // ---------------- observable state / counters ----------------
    integer violations      = 0;
    integer n_ce            = 0;   // CE# low periods
    integer n_data_cmds     = 0;   // read/write commands that reached data phase
    integer n_writes        = 0;
    integer n_reads         = 0;
    integer n_bytes_w       = 0;
    integer n_bytes_r       = 0;
    integer n_resets        = 0;
    integer n_incomplete    = 0;
    integer n_page_cross    = 0;
    integer n_partial_write = 0;
    integer n_id_reads      = 0;
    real    max_ce_low_ns   = 0.0;
    real    min_period_ns   = 1.0e9;
    reg     qpi             = 1'b0;
    reg     wrap32          = 1'b0;
    reg     initialized     = 1'b0;   // a global reset happened after power-up
    reg     inject_kgd_fail = 1'b0;   // fault injection: report KGD = FAIL
    reg     inject_dead     = 1'b0;   // fault injection: never drive outputs

    // ---------------- output drivers ----------------
    reg [3:0] dout = 4'h0;
    reg [3:0] doe  = 4'h0;
    assign sio[0] = doe[0] ? dout[0] : 1'bz;
    assign sio[1] = doe[1] ? dout[1] : 1'bz;
    assign sio[2] = doe[2] ? dout[2] : 1'bz;
    assign sio[3] = doe[3] ? dout[3] : 1'bz;

    // ---------------- transaction state ----------------
    localparam P_CMD = 0, P_ADDR = 1, P_WAIT = 2, P_DIN = 3, P_DOUT = 4, P_DONE = 5;
    integer   phase;
    integer   bitcnt;
    reg [7:0] cmd;
    reg [23:0] addr;
    integer   addr_bits_per_clk;
    integer   data_bits_per_clk;
    integer   wait_left;
    reg       is_read, is_write, is_id;
    reg [22:0] cur;
    reg [7:0] sr_in;
    integer   in_bits;
    reg [7:0] out_byte;
    integer   out_bits;
    integer   id_idx;
    integer   burst_cross;
    integer   last_page;      // page of the previous byte accessed in this burst
    reg [22:0] out_addr;      // address of the byte currently being driven
    reg       out_new = 1'b0; // its first bit has not been sampled yet
    real      burst_min_period;
    real      cmd_min_period;
    reg       rsten_armed = 1'b0;   // previous complete command was 'h66
    reg       pend_rsten, pend_rst, pend_qe, pend_qx, pend_wrap;
    reg       first_rise;
    real      t_ce_fall = -1.0e9, t_ce_rise = -1.0e9, t_last_rise = -1.0e9;
    real      t_reset_done = -1.0e9;
    real      t_in_chg [0:3];
    integer   i;

    task automatic viol(input [8*64-1:0] what);
        begin
            violations = violations + 1;
            $display("MODEL_VIOLATION t=%0t %0s", $realtime, what);
        end
    endtask

    initial begin : init_mem
        integer s, k;
        s = SEED;
        for (k = 0; k < 8388608; k = k + 1) mem[k] = $random(s);
        for (k = 0; k < 4; k = k + 1) t_in_chg[k] = -1.0e9;
    end

    // input change tracking for hold checks (only host-driven lines)
    genvar g;
    generate for (g = 0; g < 4; g = g + 1) begin : g_hold
        always @(sio[g]) begin
            if (!doe[g] && sio[g] !== 1'bz) begin
                if (!ce_n && ($realtime - t_last_rise) < THD_NS && t_last_rise > t_ce_fall)
                    viol("tHD: input changed too soon after CLK rise");
                t_in_chg[g] = $realtime;
            end
        end
    end endgenerate

    // ---------------- power-up rules ----------------
    always @(posedge sclk) if ($realtime < TPU_NS) viol("CLK toggled during tPU");

    // ---------------- CE# falling: start of a transaction ----------------
    always @(negedge ce_n) begin
        n_ce = n_ce + 1;
        if ($realtime < TPU_NS)                    viol("CE# low before tPU (150 us)");
        if (sclk !== 1'b0)                         viol("CLK not low at CE# fall (mode 0)");
        if (($realtime - t_ce_rise) < TCPH_NS)     viol("tCPH: CE# high time too short");
        if (($realtime - t_reset_done) < TRST_NS)  viol("tRST: command too soon after reset");
        t_ce_fall = $realtime;
        phase = P_CMD; bitcnt = 0; cmd = 8'h00; addr = 24'h0;
        is_read = 0; is_write = 0; is_id = 0;
        in_bits = 0; out_bits = 0; id_idx = 0;
        burst_cross = 0; last_page = -1; out_new = 1'b0; burst_min_period = 1.0e9; cmd_min_period = 1.0e9;
        pend_rsten = 0; pend_rst = 0; pend_qe = 0; pend_qx = 0; pend_wrap = 0;
        first_rise = 1;
    end

    // ---------------- CE# rising: termination ----------------
    always @(posedge ce_n) begin
        t_ce_rise = $realtime;
        if (t_ce_fall > 0) begin
            if (($realtime - t_ce_fall) > max_ce_low_ns) max_ce_low_ns = $realtime - t_ce_fall;
            if (($realtime - t_ce_fall) > TCEM_NS) viol("tCEM: CE# low longer than allowed");
            if (!first_rise && ($realtime - t_last_rise) < TCHD_NS) viol("tCHD: CE# hold after CLK rise");
        end
        doe <= #(THZ) 4'h0;
        if (phase == P_CMD) begin
            if (bitcnt != 0) n_incomplete = n_incomplete + 1;   // MODEL ASSUMPTION: ignored
            rsten_armed = 1'b0;
        end else begin
            if (phase == P_DIN && in_bits != 0) n_partial_write = n_partial_write + 1;
            if (pend_rsten) rsten_armed = 1'b1;
            else            rsten_armed = 1'b0;
            if (pend_rst) begin
                if ($realtime >= TPU_NS) initialized = 1'b1;
                qpi = 1'b0; wrap32 = 1'b0;
                n_resets = n_resets + 1;
                t_reset_done = $realtime;
            end
            if (pend_qe)   qpi = 1'b1;
            if (pend_qx)   qpi = 1'b0;
            if (pend_wrap) wrap32 = ~wrap32;
            if (is_read || is_write) begin
                if (is_read && burst_min_period < TCLK_LIN && burst_cross > 0)
                    viol("linear burst crossed a page above 84 MHz");
                if (cmd_min_period < TCLK_LIN && !wrap32) viol("linear burst above 84 MHz");
            end
        end
        phase = P_DONE;
    end

    // called for every byte actually written or driven out; a crossing is a
    // byte whose 1 KiB page differs from the previous byte of the same burst
    task automatic touch(input [22:0] at);
        begin
            if (last_page >= 0 && at[22:10] != last_page[12:0]) begin
                burst_cross = burst_cross + 1;
                n_page_cross = n_page_cross + 1;
                if (burst_cross > 1) viol("linear burst crossed more than one page");
            end
            last_page = at[22:10];
        end
    endtask

    // address increment with wrap rules
    task automatic advance;
        begin
            if (wrap32) cur = {cur[22:5], cur[4:0] + 5'd1};
            else        cur = cur + 23'd1;
        end
    endtask

    task automatic decode;
        begin
            if (!qpi) begin
                case (cmd)
                8'h66: begin pend_rsten = 1; phase = P_DONE; end
                8'h99: begin if (rsten_armed) pend_rst = 1; phase = P_DONE; end
                8'h35: begin pend_qe = 1; phase = P_DONE; end
                8'hC0: begin pend_wrap = 1; phase = P_DONE; end
                8'h03: begin is_read = 1; addr_bits_per_clk = 1; data_bits_per_clk = 1; wait_left = 0; phase = P_ADDR; end
                8'h0B: begin is_read = 1; addr_bits_per_clk = 1; data_bits_per_clk = 1; wait_left = 8; phase = P_ADDR; end
                8'hEB: begin is_read = 1; addr_bits_per_clk = 4; data_bits_per_clk = 4; wait_left = 6; phase = P_ADDR; end
                8'h02: begin is_write = 1; addr_bits_per_clk = 1; data_bits_per_clk = 1; wait_left = 0; phase = P_ADDR; end
                8'h38: begin is_write = 1; addr_bits_per_clk = 4; data_bits_per_clk = 4; wait_left = 0; phase = P_ADDR; end
                8'h9F: begin is_id = 1; addr_bits_per_clk = 1; data_bits_per_clk = 1; wait_left = 0; phase = P_ADDR; end
                default: begin viol("unsupported SPI command"); phase = P_DONE; end
                endcase
            end else begin
                case (cmd)
                8'h66: begin pend_rsten = 1; phase = P_DONE; end
                8'h99: begin if (rsten_armed) pend_rst = 1; phase = P_DONE; end
                8'hF5: begin pend_qx = 1; phase = P_DONE; end
                8'hC0: begin pend_wrap = 1; phase = P_DONE; end
                8'h0B: begin is_read = 1; addr_bits_per_clk = 4; data_bits_per_clk = 4; wait_left = 4; phase = P_ADDR; end
                8'hEB: begin is_read = 1; addr_bits_per_clk = 4; data_bits_per_clk = 4; wait_left = 6; phase = P_ADDR; end
                8'h02, 8'h38: begin is_write = 1; addr_bits_per_clk = 4; data_bits_per_clk = 4; wait_left = 0; phase = P_ADDR; end
                default: begin viol("unsupported QPI command"); phase = P_DONE; end
                endcase
            end
            if (rsten_armed && cmd != 8'h99) rsten_armed = 1'b0;
            if (is_read || is_write || is_id) begin
                if (!initialized) viol("array/ID access before power-up global reset");
                if (is_id && qpi)  viol("Read ID is SPI-mode only");
            end
            bitcnt = 0;
        end
    endtask

    // ---------------- CLK rising: sample inputs ----------------
    always @(posedge sclk) if (!ce_n) begin : rise
        real per;
        if (first_rise) begin
            if (($realtime - t_ce_fall) < TCSP_NS) viol("tCSP: CE# setup to first CLK rise");
            first_rise = 0;
        end else begin
            per = $realtime - t_last_rise;
            if (per < min_period_ns)    min_period_ns = per;
            if (per < cmd_min_period)   cmd_min_period = per;
            if ((is_id || (cmd == 8'h03 && !qpi)) && per < TCLK_RD03) viol("'h03/'h9F above 33 MHz");
            if (cmd == 8'h0B && qpi && per < TCLK_Q0B) viol("QPI 'h0B above 66 MHz");
            if (phase == P_DOUT && per < burst_min_period) burst_min_period = per;
        end
        t_last_rise = $realtime;
        case (phase)
        P_CMD: begin
            if (qpi) begin
                for (i = 0; i < 4; i = i + 1) begin
                    if (sio[i] !== 1'b0 && sio[i] !== 1'b1) viol("X/Z on command nibble");
                    if (($realtime - t_in_chg[i]) < TSP_NS) viol("tSP: input setup");
                end
                cmd = {cmd[3:0], sio}; bitcnt = bitcnt + 4;
            end else begin
                if (sio[0] !== 1'b0 && sio[0] !== 1'b1) viol("X/Z on SI command bit");
                if (($realtime - t_in_chg[0]) < TSP_NS) viol("tSP: input setup");
                cmd = {cmd[6:0], sio[0]}; bitcnt = bitcnt + 1;
            end
            if (bitcnt == 8) decode;
        end
        P_ADDR: begin
            if (addr_bits_per_clk == 4) begin
                for (i = 0; i < 4; i = i + 1)
                    if (sio[i] !== 1'b0 && sio[i] !== 1'b1) viol("X/Z on address nibble");
                addr = {addr[19:0], sio}; bitcnt = bitcnt + 4;
            end else begin
                if (sio[0] !== 1'b0 && sio[0] !== 1'b1) viol("X/Z on SI address bit");
                addr = {addr[22:0], sio[0]}; bitcnt = bitcnt + 1;
            end
            if (bitcnt == 24) begin
                cur = addr[22:0];
                bitcnt = 0;
                if (is_write) begin phase = P_DIN; n_writes = n_writes + 1; n_data_cmds = n_data_cmds + 1; end
                else if (wait_left == 0) begin
                    phase = P_DOUT;
                    if (is_id) n_id_reads = n_id_reads + 1;
                    else begin n_reads = n_reads + 1; n_data_cmds = n_data_cmds + 1; end
                end else phase = P_WAIT;
            end
        end
        P_WAIT: begin
            // bus contention during turnaround is checked by the testbench
            wait_left = wait_left - 1;
            if (wait_left == 0) begin
                phase = P_DOUT;
                n_reads = n_reads + 1; n_data_cmds = n_data_cmds + 1;
            end
        end
        P_DOUT: begin
            // a read byte counts as accessed once the host clocks its first bit
            if (out_new) begin touch(out_addr); out_new = 1'b0; end
        end
        P_DIN: begin
            if (data_bits_per_clk == 4) begin
                for (i = 0; i < 4; i = i + 1)
                    if (sio[i] !== 1'b0 && sio[i] !== 1'b1) viol("X/Z on write data");
                sr_in = {sr_in[3:0], sio}; in_bits = in_bits + 4;
            end else begin
                sr_in = {sr_in[6:0], sio[0]}; in_bits = in_bits + 1;
            end
            if (in_bits == 8) begin
                touch(cur);
                mem[cur] = sr_in; n_bytes_w = n_bytes_w + 1;
                advance; in_bits = 0;
            end
        end
        default: ;
        endcase
    end

    // ---------------- CLK falling: launch output data ----------------
    always @(negedge sclk) if (!ce_n && phase == P_DOUT && !inject_dead) begin : fall
        reg [3:0] nib;
        if (out_bits == 0) begin
            if (is_id) begin
                case (id_idx)
                0: out_byte = 8'h0D;                                  // MF ID
                1: out_byte = inject_kgd_fail ? 8'h55 : 8'h5D;        // KGD
                2: out_byte = 8'h40;                                  // EID (arbitrary)
                default: out_byte = 8'h00;
                endcase
                id_idx = id_idx + 1;
            end else begin
                out_addr = cur; out_new = 1'b1;     // counted when sampled
                out_byte = mem[cur]; n_bytes_r = n_bytes_r + 1;
                advance;
            end
            out_bits = 8;
        end
        if (data_bits_per_clk == 4) begin
            nib = out_byte[7:4]; out_byte = {out_byte[3:0], 4'h0}; out_bits = out_bits - 4;
            dout <= #(TACLK) nib;
            doe  <= #(TACLK) 4'hF;
        end else begin
            nib = {2'b00, out_byte[7], 1'b0}; out_byte = {out_byte[6:0], 1'b0}; out_bits = out_bits - 1;
            dout <= #(TACLK) nib;
            doe  <= #(TACLK) 4'b0010;          // SO = SIO[1]
        end
    end
endmodule
