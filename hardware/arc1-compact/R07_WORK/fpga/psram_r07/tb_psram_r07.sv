// ARC-1 Compact R07 -- additional PSRAM controller scenarios requested by the
// R07 handoff (section 5 "Controller function"), run against the UNCHANGED
// R06 RTL (R06_WORK/fpga/psram/rtl). RTL SIMULATION ONLY.
//   R1  dead chip at first power-up (never drives)  -> ERR_ID, no traffic, recover
//   R2  KGD=FAIL at first power-up                   -> ERR_ID, recover
//   R3  PSRAM power interruption while the T35 runs  -> controller CANNOT detect it by
//       itself; reads return garbage (documented limitation); recover -> OK
//   R4  CE#-high clock stop inside a burst sequence  -> covered by R06 T13 (rerun in R06 suite)
`timescale 1ns/1ps
module tb_psram_r07;
    parameter integer MCLK_HZ = 40000000;
    parameter integer UCLK_PS = 20000;
    localparam integer BUF = 256, LENW = 9;
    localparam real MCLK_NS = 1.0e9 / MCLK_HZ;
    localparam real UCLK_NS = UCLK_PS / 1000.0;

    reg mclk = 0, uclk = 0;
    always #(MCLK_NS / 2.0) mclk = ~mclk;
    always #(UCLK_NS / 2.0) uclk = ~uclk;
    reg urst = 1;

    reg req_valid = 0, req_write = 0, wr_valid = 0, rd_ready = 1, resp_ready = 1, recover = 0;
    reg [22:0] req_addr = 0;
    reg [LENW-1:0] req_len = 0;
    reg [7:0] wr_data = 0;
    wire req_ready, wr_ready, rd_valid, resp_valid, ram_ready, ram_error;
    wire [7:0] rd_data;
    wire [2:0] resp_status;
    wire [1:0] ram_err_code;
    wire ce_n, sclk;
    wire [3:0] dq_o, dq_oe, sio;

    psram_user_port #(.MCLK_HZ(MCLK_HZ), .CLK_DIV(1), .BUF_BYTES(BUF), .TCEM_NS(8000), .UTIMEOUT(20000)) dut (
        .uclk(uclk), .urst(urst), .req_valid(req_valid), .req_ready(req_ready), .req_write(req_write),
        .req_addr(req_addr), .req_len(req_len), .wr_valid(wr_valid), .wr_ready(wr_ready), .wr_data(wr_data),
        .rd_valid(rd_valid), .rd_ready(rd_ready), .rd_data(rd_data), .resp_valid(resp_valid),
        .resp_ready(resp_ready), .resp_status(resp_status), .recover(recover), .ram_ready(ram_ready),
        .ram_error(ram_error), .ram_err_code(ram_err_code), .mclk(mclk), .mrst(urst), .dbg_freeze(1'b0),
        .psram_ce_n(ce_n), .psram_sclk(sclk), .psram_dq_o(dq_o), .psram_dq_oe(dq_oe), .psram_dq_i(sio));
    genvar g;
    generate for (g = 0; g < 4; g = g + 1) begin : pad
        assign sio[g] = dq_oe[g] ? dq_o[g] : 1'bz;
        pulldown (weak0) pd (sio[g]);                 // R06/R07 board plan: 2.2k pull-downs
    end endgenerate
    aps6404l_model_r07 psram (.ce_n(ce_n), .sclk(sclk), .sio(sio));

    integer errors = 0, contention = 0;
    always @(dq_oe or psram.doe) if (|(dq_oe & psram.doe)) contention = contention + 1;
    task automatic fail(input [8*72-1:0] m); begin errors = errors + 1; $display("TB_ERROR t=%0t %0s", $realtime, m); end endtask

    reg [7:0] pat [0:BUF-1];
    reg [7:0] got [0:BUF-1];
    integer nrd;
    reg [2:0] st;
    task automatic op(input w, input [22:0] a, input integer n);
        integer k;
        begin
            @(negedge uclk); req_valid = 1; req_write = w; req_addr = a; req_len = n[LENW-1:0];
            @(posedge uclk); while (!req_ready) @(posedge uclk);
            @(negedge uclk); req_valid = 0;
            k = 0; nrd = 0;
            forever begin
                wr_valid = w && (k < n); wr_data = pat[k < BUF ? k : 0];
                @(posedge uclk);
                if (wr_valid && wr_ready) k = k + 1;
                if (rd_valid && rd_ready) begin got[nrd] = rd_data; nrd = nrd + 1; end
                if (resp_valid) begin st = resp_status; @(negedge uclk); wr_valid = 0; disable op; end
                @(negedge uclk);
            end
        end
    endtask
    task automatic wait_flag(input integer which, input integer max_us);   // 0 ready, 1 error
        integer t;
        begin
            t = 0;
            while (((which == 0) ? !ram_ready : !ram_error) && t < max_us) begin #1000; t = t + 1; end
        end
    endtask
    task automatic pulse_recover; begin @(negedge uclk); recover = 1; @(negedge uclk); recover = 0; end endtask
    function integer mismatches(input integer n);
        integer i, m; begin m = 0; for (i = 0; i < n; i = i + 1) if (got[i] !== pat[i]) m = m + 1; mismatches = m; end
    endfunction

    integer i, v0, d0, mm;
    initial begin
        for (i = 0; i < BUF; i = i + 1) pat[i] = (i * 37 + 11) & 8'hFF;
        // ---------- R1 dead chip at first power-up ----------
        psram.inject_dead = 1;
        repeat (5) @(posedge uclk); urst = 0;
        wait_flag(1, 400);
        if (!(ram_error && ram_err_code == 2'd1)) fail("R1: dead chip not reported as ID error");
        if (ram_ready) fail("R1: ready with dead chip");
        d0 = psram.n_data_cmds;
        op(1, 23'h000100, 16); if (st != 3'd1) fail("R1: write not refused");
        if (psram.n_data_cmds != d0) fail("R1: data command reached dead chip");
        $display("INFO R1 id_mfid=%h id_kgd=%h err=%0d", dut.u_core.id_mfid, dut.u_core.id_kgd, ram_err_code);
        psram.inject_dead = 0; pulse_recover; wait_flag(0, 400);
        if (!ram_ready) fail("R1: no recovery");
        op(1, 23'h000100, 64); op(0, 23'h000100, 64);
        if (st != 0 || mismatches(64) != 0) fail("R1: data after recovery");
        $display("TEST R1_dead_chip done errors=%0d", errors);

        // ---------- R2 KGD = FAIL ----------
        psram.inject_kgd_fail = 1; pulse_recover;
        #2000; wait_flag(1, 200);
        if (!(ram_error && ram_err_code == 2'd1)) fail("R2: KGD fail not reported");
        psram.inject_kgd_fail = 0; pulse_recover; wait_flag(0, 200);
        if (!ram_ready) fail("R2: no recovery");
        $display("TEST R2_kgd_fail done errors=%0d", errors);

        // ---------- R3 PSRAM power interruption ----------
        op(1, 23'h040000, BUF); if (st != 0) fail("R3: setup write");
        wait (ce_n === 1'b1); #100;                 // bus idle: CE# high
        v0 = psram.violations;
        psram.power_cycle;
        op(0, 23'h040000, BUF);
        mm = mismatches(BUF);
        $display("INFO R3 after power loss: status=%0d ready=%0d mismatching_bytes=%0d new_model_violations=%0d",
                 st, ram_ready, mm, psram.violations - v0);
        if (st != 0 || !ram_ready) fail("R3: controller unexpectedly noticed the power loss (update the limitation note)");
        if (mm == 0) fail("R3: data survived a power loss in the model (test ineffective)");
        if (psram.violations == v0) fail("R3: model did not flag access to an uninitialised device");
        #160000;                                       // >= tPU after the power ramp
        v0 = psram.violations;
        pulse_recover; #2000; wait_flag(0, 200);
        if (!ram_ready) fail("R3: no recovery after power loss");
        op(1, 23'h040000, BUF); op(0, 23'h040000, BUF);
        if (st != 0 || mismatches(BUF) != 0) fail("R3: data after recovery");
        if (psram.violations != v0) fail("R3: violations during recovery");
        $display("TEST R3_power_interruption done errors=%0d", errors);

        if (contention) fail("bus contention");
        $display("SUMMARY tb_psram_r07 errors=%0d contention=%0d model_violations_total=%0d (R3 deliberately provokes some)",
                 errors, contention, psram.violations);
        if (errors == 0) $display("PSRAM_R07_TB_PASS"); else $display("PSRAM_R07_TB_FAIL");
        $finish;
    end
    initial begin #50_000_000; $display("PSRAM_R07_TB_FAIL timeout"); $finish; end
endmodule
