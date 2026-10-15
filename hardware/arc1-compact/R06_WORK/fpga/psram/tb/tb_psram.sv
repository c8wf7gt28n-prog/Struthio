// ARC-1 Compact R06 -- self-checking testbench: psram_user_port +
// psram_qspi_core against aps6404l_model. RTL SIMULATION ONLY.
//
// The scoreboard is an independent byte-shadow of every successful write;
// it never reads the model's array. Every handshake gets random stalls.
// Pass criteria: zero scoreboard mismatches, zero model protocol violations,
// zero bus-contention events, zero X on returned data, every expected status.
`timescale 1ns/1ps
module tb_psram;
    parameter integer MCLK_HZ   = 40000000;
    parameter integer CLK_DIV   = 1;
    parameter integer UCLK_PS   = 20000;
    parameter integer TCEM_NS   = 8000;
    parameter integer BUF       = 256;
    parameter integer UTIMEOUT  = 20000;
    parameter integer N_RANDOM  = 200;
    parameter integer SEED      = 1;
    parameter CFG = "cfg";

    localparam integer LENW = $clog2(BUF+1);
    localparam real MCLK_NS = 1.0e9 / MCLK_HZ;
    localparam real UCLK_NS = UCLK_PS / 1000.0;
    localparam [2:0] ST_OK = 0, ST_NOT_READY = 1, ST_INVALID = 2, ST_TIMEOUT = 3, ST_CORE_FAULT = 4;

    // ---------------- clocks / resets ----------------
    reg mclk = 0, uclk = 0, mclk_en = 1;
    always begin #(MCLK_NS/2.0); if (mclk_en) mclk = ~mclk; end
    always #(UCLK_NS/2.0) uclk = ~uclk;
    reg urst = 1, mrst_x = 0, dbg_freeze = 0;
    wire mrst = urst | mrst_x;

    // ---------------- DUT ----------------
    reg             req_valid = 0, req_write = 0;
    reg  [22:0]     req_addr = 0;
    reg  [LENW-1:0] req_len = 0;
    wire            req_ready;
    reg             wr_valid = 0;
    reg  [7:0]      wr_data = 0;
    wire            wr_ready;
    wire            rd_valid;
    reg             rd_ready = 0;
    wire [7:0]      rd_data;
    wire            resp_valid;
    reg             resp_ready = 0;
    wire [2:0]      resp_status;
    reg             recover = 0;
    wire            ram_ready, ram_error;
    wire [1:0]      ram_err_code;
    wire            ce_n, sclk;
    wire [3:0]      dq_o, dq_oe;
    wire [3:0]      sio;

    psram_user_port #(.MCLK_HZ(MCLK_HZ), .CLK_DIV(CLK_DIV), .BUF_BYTES(BUF),
                      .TCEM_NS(TCEM_NS), .UTIMEOUT(UTIMEOUT)) dut (
        .uclk(uclk), .urst(urst),
        .req_valid(req_valid), .req_ready(req_ready), .req_write(req_write),
        .req_addr(req_addr), .req_len(req_len),
        .wr_valid(wr_valid), .wr_ready(wr_ready), .wr_data(wr_data),
        .rd_valid(rd_valid), .rd_ready(rd_ready), .rd_data(rd_data),
        .resp_valid(resp_valid), .resp_ready(resp_ready), .resp_status(resp_status),
        .recover(recover), .ram_ready(ram_ready), .ram_error(ram_error), .ram_err_code(ram_err_code),
        .mclk(mclk), .mrst(mrst), .dbg_freeze(dbg_freeze),
        .psram_ce_n(ce_n), .psram_sclk(sclk), .psram_dq_o(dq_o), .psram_dq_oe(dq_oe),
        .psram_dq_i(sio));

    // FPGA pads: tri-state outputs; weak pull-ups (Trion default for GPIO)
    genvar g;
    generate for (g = 0; g < 4; g = g + 1) begin : g_pad
        assign sio[g] = dq_oe[g] ? dq_o[g] : 1'bz;
        pullup (weak1) pu (sio[g]);
    end endgenerate

    aps6404l_model #(.TCEM_NS(TCEM_NS * 1.0)) psram (.ce_n(ce_n), .sclk(sclk), .sio(sio));

    // ---------------- monitors ----------------
    integer errors = 0, contention = 0, xdata = 0, compared = 0, n_ops = 0;
    always @(dq_oe or psram.doe) if (|(dq_oe & psram.doe)) begin
        contention = contention + 1;
        $display("TB_ERROR t=%0t bus contention ctrl_oe=%b model_oe=%b", $realtime, dq_oe, psram.doe);
    end

    // ---------------- scoreboard ----------------
    reg [7:0] shadow [0:8388607];
    reg       known  [0:8388607];
    integer   k0;
    initial for (k0 = 0; k0 < 8388608; k0 = k0 + 1) known[k0] = 1'b0;

    reg [7:0] wbuf [0:BUF-1];
    reg [7:0] rbuf [0:BUF-1];
    integer   n_rd;
    reg [2:0] last_status;
    integer   p_wr_gap = 30, p_rd_stall = 40, p_resp_stall = 30;
    integer   seed = SEED;

    function integer rnd(input integer m);   // 0..m-1
        integer r; begin r = $random(seed); if (r < 0) r = -r; rnd = r % m; end
    endfunction

    task automatic fail(input [8*80-1:0] msg);
        begin errors = errors + 1; $display("TB_ERROR t=%0t %0s", $realtime, msg); end
    endtask

    // one complete request/response transaction from the user side
    task automatic op(input w, input [22:0] a, input integer n);
        integer kw, cyc;
        reg done;
        begin
            n_ops = n_ops + 1;
            @(negedge uclk);
            req_valid = 1; req_write = w; req_addr = a; req_len = n[LENW-1:0];
            @(posedge uclk); while (!req_ready) @(posedge uclk);
            @(negedge uclk); req_valid = 0;
            kw = 0; n_rd = 0; done = 0; cyc = 0;
            while (!done) begin
                wr_valid   = w && (kw < n) && (rnd(100) >= p_wr_gap);
                wr_data    = (kw < BUF) ? wbuf[kw] : 8'h00;
                rd_ready   = (rnd(100) >= p_rd_stall);
                resp_ready = (rnd(100) >= p_resp_stall);
                @(posedge uclk);
                if (wr_valid && wr_ready) kw = kw + 1;
                if (rd_valid && rd_ready) begin
                    if (^rd_data === 1'bx) begin xdata = xdata + 1; fail("X on rd_data"); end
                    if (n_rd < BUF) rbuf[n_rd] = rd_data;
                    n_rd = n_rd + 1;
                end
                if (resp_valid && resp_ready) begin last_status = resp_status; done = 1; end
                cyc = cyc + 1;
                if (cyc > 4 * UTIMEOUT + 100000) begin fail("TB op watchdog"); done = 1; end
                @(negedge uclk);
            end
            wr_valid = 0; rd_ready = 0; resp_ready = 0;
            // protocol checks
            if (last_status == ST_OK && w && kw != n) fail("OK write without full data transfer");
            if (last_status != ST_OK && w && kw != 0 && last_status != ST_CORE_FAULT && last_status != ST_TIMEOUT)
                fail("rejected write consumed data");
            if (last_status == ST_OK && !w && n_rd != n) fail("OK read returned wrong byte count");
            if (last_status != ST_OK && !w && n_rd != 0) fail("failed read returned data");
            // scoreboard
            if (w) begin : sb_w
                integer i;
                for (i = 0; i < n; i = i + 1)
                    if (last_status == ST_OK) begin shadow[a + i] = wbuf[i]; known[a + i] = 1'b1; end
                    else if ((last_status == ST_CORE_FAULT || last_status == ST_TIMEOUT) && (a + i) < 8388608)
                        known[a + i] = 1'b0;   // possibly partially written: undefined
            end else if (last_status == ST_OK) begin : sb_r
                integer i;
                for (i = 0; i < n; i = i + 1)
                    if (known[a + i]) begin
                        compared = compared + 1;
                        if (rbuf[i] !== shadow[a + i]) begin
                            fail("read data mismatch");
                            $display("        addr=%h got=%h exp=%h", a + i, rbuf[i], shadow[a + i]);
                        end
                    end
            end
        end
    endtask

    task automatic expect_status(input [2:0] st, input [8*40-1:0] what);
        begin
            if (last_status !== st) begin
                fail("unexpected status");
                $display("        %0s: got %0d expected %0d", what, last_status, st);
            end
        end
    endtask

    task automatic fill_random(input integer n);
        integer i; begin for (i = 0; i < n; i = i + 1) wbuf[i] = rnd(256); end
    endtask

    task automatic wr(input [22:0] a, input integer n);
        begin op(1, a, n); expect_status(ST_OK, "write"); end
    endtask
    task automatic rd(input [22:0] a, input integer n);
        begin op(0, a, n); expect_status(ST_OK, "read"); end
    endtask

    task automatic wait_ready(input integer max_us);
        integer t;
        begin
            t = 0;
            while (!ram_ready && t < max_us * 1000) begin #100; t = t + 100; end
            if (!ram_ready) fail("ram_ready timeout");
        end
    endtask

    task automatic pulse_recover;
        begin @(negedge uclk); recover = 1; @(negedge uclk); recover = 0; end
    endtask

    task automatic mark(input [8*24-1:0] name);
        begin
            $display("TEST %0s done t=%0t errors=%0d violations=%0d contention=%0d",
                     name, $realtime, errors, psram.violations, contention);
        end
    endtask

    // ---------------- test sequence ----------------
    integer i, j, a, n, base_cmds, t0_ce;
    real    t_ready, t_start, t_end;
    initial begin
        $display("TB_CONFIG cfg=%0s MCLK_HZ=%0d CLK_DIV=%0d SCLK_HZ=%0d UCLK_NS=%0.3f TCEM_NS=%0d BUF=%0d",
                 CFG, MCLK_HZ, CLK_DIV, MCLK_HZ / (2 * CLK_DIV), UCLK_NS, TCEM_NS, BUF);
        repeat (10) @(posedge uclk);
        urst = 0;

        // ---- T1 reset readiness / no access before init ----
        #5000;
        if (ram_ready) fail("ram_ready asserted during tPU");
        fill_random(16);
        op(1, 23'h000100, 16); expect_status(ST_NOT_READY, "write before init");
        op(0, 23'h000100, 16); expect_status(ST_NOT_READY, "read before init");
        if (psram.n_data_cmds != 0) fail("PSRAM accessed before init complete");
        if (psram.n_ce != 0) fail("CE# asserted before tPU");
        wait_ready(400);
        t_ready = $realtime;
        if (t_ready < 150000.0) fail("ready before 150 us");
        if (dut.u_core.id_mfid !== 8'h0D || dut.u_core.id_kgd !== 8'h5D) fail("ID registers");
        if (!psram.qpi) fail("device not in QPI after init");
        if (psram.n_resets < 1 || psram.n_id_reads != 1) fail("init sequence counts");
        $display("INFO ready_at_ns=%0.1f resets=%0d id_reads=%0d", t_ready, psram.n_resets, psram.n_id_reads);
        mark("T1_reset_readiness");

        // ---- T2 data-bit walking ----
        for (i = 0; i < 8; i = i + 1) begin wbuf[2*i] = 8'h01 << i; wbuf[2*i+1] = ~(8'h01 << i); end
        wr(23'h012340, 16); rd(23'h012340, 16);
        for (i = 0; i < 16; i = i + 1) wbuf[i] = (i[0]) ? 8'h55 : 8'hAA;
        wr(23'h012350, 16); rd(23'h012340, 32);
        mark("T2_data_bit_walk");

        // ---- T3 address-bit walking (aliasing detection) ----
        wbuf[0] = 8'hA5; wr(23'h000000, 1);
        for (i = 0; i < 23; i = i + 1) begin wbuf[0] = i + 1; wr(23'h1 << i, 1); end
        rd(23'h000000, 1);
        for (i = 0; i < 23; i = i + 1) rd(23'h1 << i, 1);
        for (i = 0; i < 23; i = i + 1) begin wbuf[0] = ~(i + 1); wr(~(23'h1 << i), 1); end
        for (i = 0; i < 23; i = i + 1) rd(~(23'h1 << i), 1);
        rd(23'h000000, 1);
        mark("T3_address_walk");

        // ---- T5 first / last address ----
        fill_random(BUF); wr(23'h000000, BUF); rd(23'h000000, BUF);
        fill_random(1);   wr(23'h7FFFFF, 1);   rd(23'h7FFFFF, 1);
        fill_random(BUF); wr(24'h800000 - BUF, BUF); rd(24'h800000 - BUF, BUF);
        mark("T5_first_last");

        // ---- T6 page boundaries (1 KiB) ----
        a = psram.n_page_cross;
        fill_random(8);   wr(23'h0003FC, 8);  rd(23'h0003FC, 8);
        fill_random(64);  wr(23'h0007F0, 64); rd(23'h0007E0, 96);
        fill_random(BUF); wr(23'h000C80, BUF); rd(23'h000C80, BUF);
        fill_random(BUF); wr(23'h7FFC00 - 3, BUF); rd(23'h7FFC00 - 3, BUF);
        if (psram.n_page_cross != a) fail("controller let a burst cross a 1 KiB page");
        mark("T6_page_boundaries");

        // ---- T7 sequential maximum bursts (+ simulated throughput) ----
        p_wr_gap = 0; p_rd_stall = 0; p_resp_stall = 0;
        t_start = $realtime;
        for (i = 0; i < 32; i = i + 1) begin fill_random(BUF); wr(23'h100000 + i * BUF, BUF); end
        t_end = $realtime;
        $display("INFO seq_write bytes=%0d ns=%0.1f MBps_sim=%0.3f", 32 * BUF, t_end - t_start,
                 (32.0 * BUF) / (t_end - t_start) * 1000.0);
        t_start = $realtime;
        for (i = 0; i < 32; i = i + 1) rd(23'h100000 + i * BUF, BUF);
        t_end = $realtime;
        $display("INFO seq_read bytes=%0d ns=%0.1f MBps_sim=%0.3f", 32 * BUF, t_end - t_start,
                 (32.0 * BUF) / (t_end - t_start) * 1000.0);
        p_wr_gap = 30; p_rd_stall = 40; p_resp_stall = 30;
        mark("T7_sequential_bursts");

        // ---- T8 invalid requests: no PSRAM traffic ----
        base_cmds = psram.n_data_cmds; t0_ce = psram.n_ce;
        op(1, 23'h000000, 0);        expect_status(ST_INVALID, "len 0");
        op(0, 23'h000000, BUF + 1);  expect_status(ST_INVALID, "len > BUF");
        op(1, 23'h7FFFFF, 2);        expect_status(ST_INVALID, "wrap past 8 MiB (write)");
        op(0, 23'h7FFF80, BUF);      expect_status(ST_INVALID, "wrap past 8 MiB (read)");
        if (psram.n_data_cmds != base_cmds || psram.n_ce != t0_ce) fail("invalid request reached PSRAM");
        mark("T8_invalid_requests");

        // ---- T14 read-after-write / overlap ----
        fill_random(32); wr(23'h222200, 32); rd(23'h222200, 32);
        fill_random(8);  wr(23'h222208, 8);  rd(23'h222200, 32);
        rd(23'h222204, 1); fill_random(1); wr(23'h222204, 1); rd(23'h222204, 1);
        mark("T14_read_after_write");

        // ---- T4 pseudo-random traffic with random stalls ----
        for (j = 0; j < N_RANDOM; j = j + 1) begin
            n = 1 + rnd(BUF);
            case (rnd(4))
            0: a = rnd(8388608 - n + 1);
            1: a = 23'h300000 + rnd(4096);            // hot region: many overlaps
            2: a = (rnd(8192) << 10) - rnd(8);        // around page starts
            default: a = 8388608 - n - rnd(64);      // near the top
            endcase
            if (a < 0) a = 0;
            if (rnd(2)) begin fill_random(n); wr(a, n); end
            else rd(a, n);
        end
        mark("T4_random");

        // ---- T10 memory-domain reset during a transfer ----
        fill_random(BUF);
        fork
            op(1, 23'h400000, BUF);
            begin
                @(negedge ce_n); @(negedge ce_n);       // inside the transfer
                repeat (7) @(posedge mclk);
                @(negedge mclk); mrst_x = 1;
                repeat (10) @(negedge mclk); mrst_x = 0;
            end
        join
        if (last_status != ST_CORE_FAULT && last_status != ST_TIMEOUT) fail("reset-in-transfer status");
        $display("INFO reset_in_transfer status=%0d", last_status);
        if (ram_ready) fail("ram_ready while memory domain re-initialising");
        wait_ready(400);
        rd(23'h012340, 32); rd(23'h100000, BUF);      // earlier data intact
        fill_random(BUF); wr(23'h400000, BUF); rd(23'h400000, BUF);
        mark("T10_reset_in_transfer");

        // ---- T11 init failure (bad KGD) and recovery ----
        psram.inject_kgd_fail = 1;
        pulse_recover;
        #2000;
        i = 0; while (!(ram_error && ram_err_code == 2'd1) && i < 200) begin #1000; i = i + 1; end
        if (!(ram_error && ram_err_code == 2'd1)) fail("ID failure not reported");
        op(0, 23'h012340, 4); expect_status(ST_NOT_READY, "read while ID error");
        op(1, 23'h012340, 4); expect_status(ST_NOT_READY, "write while ID error");
        psram.inject_kgd_fail = 0;
        pulse_recover;
        wait_ready(200);
        if (ram_error) fail("error flag stuck after recovery");
        fill_random(64); wr(23'h500000, 64); rd(23'h500000, 64);
        mark("T11_id_error_recovery");

        // ---- T12 controller watchdog (stalled engine) and recovery ----
        fill_random(BUF);
        fork
            op(1, 23'h600000, BUF);
            begin
                @(negedge ce_n); @(negedge ce_n);
                repeat (5) @(posedge mclk);
                @(negedge mclk); dbg_freeze = 1;
                @(posedge ce_n);                       // watchdog aborted the CE# period
                @(negedge mclk); dbg_freeze = 0;
            end
        join
        expect_status(ST_CORE_FAULT, "watchdog abort");
        if (!(ram_error && ram_err_code == 2'd2)) fail("watchdog error code");
        pulse_recover;
        wait_ready(200);
        fill_random(BUF); wr(23'h600000, BUF); rd(23'h600000, BUF);
        mark("T12_watchdog_recovery");

        // ---- T13 user-side timeout (memory clock stopped between CE# periods) ----
        fill_random(BUF);
        fork
            op(1, 23'h700000, BUF);
            begin
                @(negedge ce_n); @(posedge ce_n);       // CE# high: stopping is tCEM-safe
                mclk_en = 0;
                #((UTIMEOUT + 2000) * UCLK_NS);
                mclk_en = 1;
            end
        join
        expect_status(ST_TIMEOUT, "user timeout");
        // the late completion may still be pending: requests are refused, not queued
        i = 0;
        while (!ram_ready && i < 1000) begin #1000; i = i + 1; end
        if (!ram_ready) fail("link did not resynchronise after timeout");
        fill_random(BUF); wr(23'h700000, BUF); rd(23'h700000, BUF);
        mark("T13_user_timeout");

        // ---- final ----
        #2000;
        if (psram.n_page_cross != 0) fail("a CE# burst crossed a 1 KiB page");
        $display("SUMMARY cfg=%0s ops=%0d compared_bytes=%0d errors=%0d model_violations=%0d contention=%0d xdata=%0d",
                 CFG, n_ops, compared, errors, psram.violations, contention, xdata);
        $display("SUMMARY_MODEL ce=%0d data_cmds=%0d writes=%0d reads=%0d bytes_w=%0d bytes_r=%0d resets=%0d incomplete_cmds=%0d page_cross=%0d partial_writes=%0d max_ce_low_ns=%0.1f min_sclk_period_ns=%0.2f",
                 psram.n_ce, psram.n_data_cmds, psram.n_writes, psram.n_reads, psram.n_bytes_w, psram.n_bytes_r,
                 psram.n_resets, psram.n_incomplete, psram.n_page_cross, psram.n_partial_write,
                 psram.max_ce_low_ns, psram.min_period_ns);
        if (errors == 0 && psram.violations == 0 && contention == 0 && xdata == 0)
            $display("PSRAM_TB_PASS cfg=%0s", CFG);
        else
            $display("PSRAM_TB_FAIL cfg=%0s", CFG);
        $finish;
    end

    // absolute simulation guard
    initial begin #200_000_000; $display("PSRAM_TB_FAIL global timeout"); $finish; end
endmodule
