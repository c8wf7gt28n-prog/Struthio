// ARC-1 R10 -- SDR SDRAM controller testbench (ARC1_MEMORY_R10 s7.3 "rtl/ecp5_45f_sdram": refresh/stress tests and
// tile-buffer throughput). sdram_ctrl at 80 MHz against sim/sdram_model.sv (protocol checker), sd_clk = ~clk.
//   T1 tile traffic: 32 colour tiles (1024 words = 4 x 256-word bursts each) written then read back
//   T2 random stress: 400 random bursts (bank/row/column/length 1..256, inside a row) mixed write/read, every read
//      compared with a TB reference copy; runs across many refresh intervals
//   T3 rejected bursts (row crossing, length 0, length > 256): cmd_err, no SDRAM command
//   T4 idle 300 us: refresh keeps running (count and maximum gap checked by the model)
//   throughput: sustained tile write / read in MB/s (cycle counts), refresh included
// RTL SIMULATION ONLY.
`timescale 1ns/1ps
module tb_sdram;
    // mutation hooks (Makefile target sdram_mutants): each non-default value must make the TB fail
    parameter integer P_REFI = 624, P_INIT_REF = 8, P_RD_LAT = 6, P_T_INIT = 16000;
    reg clk = 0;
    always #6.25 clk = ~clk;                       // 80 MHz
    reg rst = 1;
    wire init_done, cmd_ready, wr_ready, rd_valid, cmd_err;
    reg  cmd_valid = 0, cmd_write = 0;
    reg  [23:0] cmd_addr = 0;
    reg  [9:0]  cmd_len = 0;
    reg  wr_valid = 0;
    reg  [15:0] wr_data = 0;
    wire [15:0] rd_data;
    wire [31:0] cnt_refresh;
    wire sd_cke, sd_cs_n, sd_ras_n, sd_cas_n, sd_we_n;
    wire [1:0] sd_ba, sd_dqm;
    wire [12:0] sd_a;
    wire [15:0] sd_dq;
    sdram_ctrl #(.CLK_MHZ(80), .CL(3), .T_REFI(P_REFI), .INIT_REF(P_INIT_REF), .RD_LAT(P_RD_LAT), .T_INIT(P_T_INIT)) dut (
        .clk(clk), .rst(rst), .init_done(init_done), .cmd_valid(cmd_valid), .cmd_ready(cmd_ready), .cmd_write(cmd_write),
        .cmd_addr(cmd_addr), .cmd_len(cmd_len), .cmd_err(cmd_err), .wr_valid(wr_valid), .wr_ready(wr_ready),
        .wr_data(wr_data), .rd_valid(rd_valid), .rd_data(rd_data), .cnt_refresh(cnt_refresh),
        .sd_cke(sd_cke), .sd_cs_n(sd_cs_n), .sd_ras_n(sd_ras_n), .sd_cas_n(sd_cas_n), .sd_we_n(sd_we_n),
        .sd_ba(sd_ba), .sd_a(sd_a), .sd_dqm(sd_dqm), .sd_dq(sd_dq));
    sdram_model u_m (.clk(~clk), .cke(sd_cke), .cs_n(sd_cs_n), .ras_n(sd_ras_n), .cas_n(sd_cas_n), .we_n(sd_we_n),
        .ba(sd_ba), .a(sd_a), .dqm(sd_dqm), .dq(sd_dq));

    integer errors = 0;
    task automatic fail(input [8*64-1:0] m); begin errors = errors + 1; $display("TB_ERROR t=%0t %0s", $time, m); end endtask

    reg [15:0] ref_mem [0:16777215];              // X = never written
    function automatic [15:0] pat(input [23:0] a, input [15:0] salt);
        reg [31:0] x;
        begin x = {8'h5A, a} * 32'h9E3779B1 + {16'd0, salt}; pat = x[31:16] ^ x[15:0]; end
    endfunction

    // one burst; writes take data from pat(addr, salt); reads compare with ref_mem
    integer rd_got, rd_bad;
    reg [23:0] rd_base;
    always @(posedge clk) if (rd_valid) begin
        if (^ref_mem[rd_base + rd_got] === 1'bx) begin
            if (rd_data !== 16'hDEAD) rd_bad = rd_bad + 1;
        end else if (rd_data !== ref_mem[rd_base + rd_got]) begin
            if (rd_bad < 3) $display("TB_ERROR read %06x: %04x expected %04x", rd_base + rd_got, rd_data, ref_mem[rd_base + rd_got]);
            rd_bad = rd_bad + 1;
        end
        rd_got = rd_got + 1;
    end
    task automatic burst(input wr, input [23:0] a, input integer n, input [15:0] salt);
        integer i;
        reg take;
        begin
            @(posedge clk);                                    // hold cmd_valid until the handshake edge
            cmd_valid <= 1; cmd_write <= wr; cmd_addr <= a; cmd_len <= n[9:0];
            @(negedge clk); while (!cmd_ready) begin @(posedge clk); @(negedge clk); end
            @(posedge clk); cmd_valid <= 0;
            if (wr) begin
                i = 0;
                wr_valid <= 1; wr_data <= pat(a, salt);
                while (i < n) begin                              // wr_ready is sampled at the edge it applies to
                    @(negedge clk); take = wr_ready;
                    @(posedge clk);
                    if (take) begin
                        ref_mem[a + i] = wr_data; i = i + 1;
                        wr_data <= pat(a + i, salt);
                    end
                end
                wr_valid <= 0;
            end else begin
                rd_base = a; rd_got = 0;
                while (rd_got < n) @(posedge clk);
            end
        end
    endtask

    integer t, k, n, wr, nrej, act0, cyc0, rb;
    reg [23:0] a;
    reg [31:0] seed = 32'h1234567;
    realtime t0;
    real mbps;
    initial begin
        rd_bad = 0; rd_got = 0;
        repeat (4) @(posedge clk); rst <= 0;
        fork : w_init
            begin wait (init_done); disable w_init; end
            begin #2000000; fail("init_done never set"); $display("SDRAM_TB_FAIL"); $finish; end
        join
        @(posedge clk);
        $display("INFO init done at %0.1f us, %0d init refreshes", $realtime / 1000.0, cnt_refresh);
        // ---- T1 tile traffic + throughput ----
        t0 = $realtime;
        for (t = 0; t < 32; t = t + 1) for (k = 0; k < 4; k = k + 1) burst(1, {t[1:0], 13'd100 + t[12:0], 9'd0} + k * 256, 256, 16'd1);
        mbps = 32.0 * 2048.0 / (($realtime - t0) / 1000.0);
        $display("INFO tile write: 32 tiles x 2048 B in %0.1f us = %0.1f MB/s (refresh included)", ($realtime - t0) / 1000.0, mbps);
        t0 = $realtime;
        for (t = 0; t < 32; t = t + 1) for (k = 0; k < 4; k = k + 1) burst(0, {t[1:0], 13'd100 + t[12:0], 9'd0} + k * 256, 256, 16'd0);
        mbps = 32.0 * 2048.0 / (($realtime - t0) / 1000.0);
        $display("INFO tile read:  32 tiles x 2048 B in %0.1f us = %0.1f MB/s (refresh included)", ($realtime - t0) / 1000.0, mbps);
        if (rd_bad) fail("tile read-back");
        $display("TEST sdram_tiles done errors=%0d", errors);
        // ---- T2 random stress ----
        for (k = 0; k < 400; k = k + 1) begin
            seed = seed * 32'd1664525 + 32'd1013904223;
            a = {seed[31:30], seed[24:12], seed[8:0]};
            seed = seed * 32'd1664525 + 32'd1013904223;
            n = 1 + seed[23:16];
            if (a[8:0] + n > 512) n = 512 - a[8:0];
            wr = (k < 100) || seed[3];
            if (!wr && k > 0) begin                                   // read a range that was written recently
                rb = seed[4:0];                                         // one of the 32 tiles written in T1
                a = {seed[27:26], 13'd100 + rb[12:0], 9'd0} + seed[9:5] * 9'd8;
                n = 1 + seed[20:13] % 200;
                if (a[8:0] + n > 512) n = 512 - a[8:0];
            end
            burst(wr, a, n, k[15:0]);
        end
        if (rd_bad) fail("random stress read-back");
        $display("INFO stress: 400 bursts, reads checked against the reference, refreshes so far %0d", cnt_refresh);
        $display("TEST sdram_stress done errors=%0d", errors);
        // ---- T3 rejected bursts ----
        act0 = u_m.n_act; nrej = 0;
        for (k = 0; k < 3; k = k + 1) begin
            @(posedge clk);
            cmd_valid <= 1; cmd_write <= 1;
            cmd_addr <= (k == 0) ? 24'h0001F0 : 24'h000000;
            cmd_len <= (k == 0) ? 10'd32 : (k == 1) ? 10'd0 : 10'd257;
            @(negedge clk); while (!cmd_ready) begin @(posedge clk); @(negedge clk); end
            @(posedge clk); cmd_valid <= 0;
            @(posedge clk); if (cmd_err) nrej = nrej + 1;
        end
        repeat (20) @(posedge clk);
        if (nrej != 3 || u_m.n_act != act0) fail("rejected bursts reached the SDRAM");
        $display("TEST sdram_reject done errors=%0d", errors);
        // ---- T4 idle refresh ----
        rb = cnt_refresh;
        #300000;
        $display("INFO idle 300 us: %0d refreshes (expected ~38), model max gap %0.2f us", cnt_refresh - rb, u_m.max_gap / 1000.0);
        if (cnt_refresh - rb < 37 || cnt_refresh - rb > 40) fail("refresh rate");
        // ---- final: data still intact after idle (tile 0 read back) ----
        for (k = 0; k < 4; k = k + 1) burst(0, {2'd0, 13'd100, 9'd0} + k * 256, 256, 16'd0);
        if (rd_bad) fail("read-back after idle");
        if (u_m.violations != 0) fail("SDRAM model protocol violations");
        if (u_m.n_ref != cnt_refresh) fail("controller and model refresh counts differ");
        $display("INFO model: act=%0d rd=%0d wr=%0d ref=%0d violations=%0d max_ref_gap=%0.2f us",
                 u_m.n_act, u_m.n_rd, u_m.n_wr, u_m.n_ref, u_m.violations, u_m.max_gap / 1000.0);
        $display("TEST sdram_refresh done errors=%0d", errors);
        if (errors == 0) $display("SDRAM_TB_PASS"); else $display("SDRAM_TB_FAIL errors=%0d", errors);
        $finish;
    end
endmodule
