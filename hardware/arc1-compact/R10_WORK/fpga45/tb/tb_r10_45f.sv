// ARC-1 R10 -- system testbench for the 45F graphics FPGA (r10_raster_top) over RGMII (decision D1: D213 GMAC0).
// Host EMAC model copied from R85C_WORK/fpga_ecp5/tb/tb_ecp5_top.sv (0defcfe). Each tile of the C-model job stream
// (fpga45/tools/raster_ref.c) is sent as one RJOB frame; every RRES word is compared with the C model. Also: STATUS,
// payload-CRC error (tile buffers untouched: the following tile still matches), bad length/opcode, loopback.
// RTL SIMULATION ONLY.
`timescale 1ns/1ps
module tb_r10_45f;
    parameter VEC = "build/vec";
    reg clk_25m = 0;
    always #20 clk_25m = ~clk_25m;
    reg        h_txc = 1'b0;
    reg  [3:0] h_txd = 4'h0;
    reg        h_txctl = 1'b0;
    wire       e_txc, e_txctl, led, e_refclk;
    wire [3:0] e_txd;
    always #4 h_txc = ~h_txc;
`ifdef MEMTOP
    // memory variant: same tests + SDRAM self test reported in STATUS caps, SDRAM model protocol violations = 0
    wire sd_clk, sd_cke, sd_cs_n, sd_ras_n, sd_cas_n, sd_we_n;
    wire [1:0] sd_ba, sd_dqm;
    wire [12:0] sd_a;
    wire [15:0] sd_dq;
    r10_raster_mem_top dut (.clk_25m(clk_25m), .rgmii_rxc(h_txc), .rgmii_rxd(h_txd), .rgmii_rx_ctl(h_txctl),
        .rgmii_txc(e_txc), .rgmii_txd(e_txd), .rgmii_tx_ctl(e_txctl), .gmac_refclk(e_refclk), .led(led),
        .sd_clk(sd_clk), .sd_cke(sd_cke), .sd_cs_n(sd_cs_n), .sd_ras_n(sd_ras_n), .sd_cas_n(sd_cas_n), .sd_we_n(sd_we_n),
        .sd_ba(sd_ba), .sd_a(sd_a), .sd_dqm(sd_dqm), .sd_dq(sd_dq));
    sdram_model u_sdm (.clk(sd_clk), .cke(sd_cke), .cs_n(sd_cs_n), .ras_n(sd_ras_n), .cas_n(sd_cas_n), .we_n(sd_we_n),
        .ba(sd_ba), .a(sd_a), .dqm(sd_dqm), .dq(sd_dq));
`else
    r10_raster_top dut (.clk_25m(clk_25m), .rgmii_rxc(h_txc), .rgmii_rxd(h_txd), .rgmii_rx_ctl(h_txctl),
        .rgmii_txc(e_txc), .rgmii_txd(e_txd), .rgmii_tx_ctl(e_txctl), .gmac_refclk(e_refclk), .led(led));
`endif
    // D7: gmac_refclk must run at 125 MHz (8 ns) once the Ethernet PLL is up
    integer rc_edges = 0;
    realtime rc_last = 0, rc_per = 0;
    always @(posedge e_refclk) begin
        if (rc_last > 0) rc_per = $realtime - rc_last;
        rc_last = $realtime; rc_edges = rc_edges + 1;
    end
    reg pll_locked = 0;
    initial force dut.u_pll.locked = pll_locked;
    wire sys_clk = dut.sys_clk;
    integer errors = 0;
    task automatic fail(input [8*72-1:0] m);
        begin errors = errors + 1; $display("TB_ERROR t=%0t %0s", $time, m); end
    endtask
    reg [7:0] aq [0:8191];
    reg [7:0] ar [0:8191];
    // ---------------- R8.5-C RGMII host EMAC model ----------------
    // Host TX: nibbles launched 2 ns after the opposite edge of h_txc (centred, as the F133 ETXDC delay
    // chain is configured to do). Host RX: samples 2 ns after each edge of the ECP5 forwarded clock
    // (edge-aligned source; the F133 ERXDC delay chain provides this skew). Frame = 7x55 D5 | dst | src |
    // 0x88B5 | len16 LE | AJOB bytes | pad | FCS.
    localparam [47:0] HOST_MAC = 48'h020000F13344, FPGA_MAC = 48'h02A1C1000001;
    function automatic [31:0] ecrc8(input [31:0] c, input [7:0] d);
        integer k;
        reg [31:0] x;
        begin
            x = c ^ {24'd0, d};
            for (k = 0; k < 8; k = k + 1) x = x[0] ? (x >> 1) ^ 32'hEDB88320 : (x >> 1);
            ecrc8 = x;
        end
    endfunction
    reg [7:0] efb [0:9000];
    integer   efn;
    task automatic eth_put(input [7:0] b);
        begin
            @(negedge h_txc); #2; h_txd = b[3:0]; h_txctl = 1'b1;
            @(posedge h_txc); #2; h_txd = b[7:4]; h_txctl = 1'b1;
        end
    endtask
    // frame body from aq[0..n-1]; type_ / bad_fcs for negative tests
    task automatic eth_build(input integer n, input [15:0] type_);
        integer q;
        begin
            for (q = 0; q < 6; q = q + 1) efb[q] = FPGA_MAC[47 - 8 * q -: 8];
            for (q = 0; q < 6; q = q + 1) efb[6 + q] = HOST_MAC[47 - 8 * q -: 8];
            efb[12] = type_[15:8]; efb[13] = type_[7:0]; efb[14] = n[7:0]; efb[15] = n[15:8];
            for (q = 0; q < n; q = q + 1) efb[16 + q] = aq[q];
            efn = 16 + n;
            while (efn < 60) begin efb[efn] = 8'h00; efn = efn + 1; end
        end
    endtask
    task automatic eth_send(input integer bad_fcs);
        integer q;
        reg [31:0] c;
        begin
            c = 32'hFFFFFFFF;
            for (q = 0; q < efn; q = q + 1) c = ecrc8(c, efb[q]);
            c = ~c ^ (bad_fcs ? 32'h00000100 : 32'h0);
            for (q = 0; q < 7; q = q + 1) eth_put(8'h55);
            eth_put(8'hD5);
            for (q = 0; q < efn; q = q + 1) eth_put(efb[q]);
            for (q = 0; q < 4; q = q + 1) eth_put(c[8 * q +: 8]);
            @(negedge h_txc); #2; h_txctl = 1'b0; h_txd = 4'h0;
            repeat (12) @(posedge h_txc);
        end
    endtask
    // receiver: every completed frame is copied to erb[0..ern-1], erx_cnt increments, erx_t = end time
    reg [7:0] ecur [0:9100];
    reg [7:0] erb  [0:9100];
    integer   ecn = 0, ern = 0, erx_cnt = 0;
    realtime  erx_t = 0;
    reg [3:0] e_lo;
    reg       e_lov = 1'b0, e_in = 1'b0;
    always @(posedge e_txc) begin
        #2; e_lo = e_txd; e_lov = e_txctl;
    end
    always @(negedge e_txc) begin : e_rx
        integer q;
        #2;
        if (e_lov && e_txctl) begin ecur[ecn] = {e_txd, e_lo}; ecn = ecn + 1; e_in = 1'b1; end
        else if (e_in) begin
            for (q = 0; q < ecn; q = q + 1) erb[q] = ecur[q];
            ern = ecn; ecn = 0; e_in = 1'b0; erx_t = $realtime; erx_cnt = erx_cnt + 1;
        end
    end
    task automatic eth_wait(input integer c0, input integer tmo_us, output integer got);
        integer t;
        begin
            t = 0;
            while (erx_cnt == c0 && t < tmo_us * 10) begin #100; t = t + 1; end
            got = (erx_cnt != c0);
        end
    endtask
    // check the received frame: header, len16 == rl, payload == exp[0..rl-1] (exp = ar), pad, FCS
    task automatic eth_check(input integer rl, input [8*48-1:0] what);
        integer q, bad;
        reg [31:0] c;
        begin
            bad = 0;
            if (ern != 8 + ((16 + rl < 60) ? 60 : 16 + rl) + 4) begin
                $display("TB_ERROR %0s: %0d bytes on the wire, len16 exp %0d", what, ern, rl); bad = 1;
            end else begin
                for (q = 0; q < 7; q = q + 1) if (erb[q] !== 8'h55) bad = bad + 1;
                if (erb[7] !== 8'hD5) bad = bad + 1;
                if ({erb[8], erb[9], erb[10], erb[11], erb[12], erb[13]} !== HOST_MAC) bad = bad + 1;
                if ({erb[14], erb[15], erb[16], erb[17], erb[18], erb[19]} !== FPGA_MAC) bad = bad + 1;
                if ({erb[20], erb[21]} !== 16'h88B5 || {erb[23], erb[22]} !== rl[15:0]) bad = bad + 1;
                for (q = 0; q < rl; q = q + 1) if (erb[24 + q] !== ar[q]) begin
                    if (bad < 4) $display("TB_ERROR %0s byte %0d rtl=%02x ref=%02x", what, q, erb[24 + q], ar[q]);
                    bad = bad + 1;
                end
                for (q = 24 + rl; q < 68; q = q + 1) if (erb[q] !== 8'h00) bad = bad + 1;
                c = 32'hFFFFFFFF;
                for (q = 8; q < ern; q = q + 1) c = ecrc8(c, erb[q]);
                if (c !== 32'hDEBB20E3) bad = bad + 1;
            end
            if (bad) fail("RGMII response frame differs from C reference");
        end
    endtask

    integer eth_got;
    reg [15:0] jobs [0:65535];
    reg [15:0] expw [0:65535];
    integer nj, ne;
    // RJOB frame from job words w[a..b-1] into aq; returns its byte length
    task automatic make_rjob(input integer a, input integer b, input [31:0] seq, input [7:0] op, output integer n);
        integer q;
        reg [31:0] c;
        begin
            n = 16 + 2 * (b - a);
            aq[0] = "R"; aq[1] = "J"; aq[2] = "O"; aq[3] = "B"; aq[4] = 8'd1; aq[5] = op;
            aq[6] = (b - a) & 255; aq[7] = (b - a) >> 8;
            aq[8] = seq[7:0]; aq[9] = seq[15:8]; aq[10] = seq[23:16]; aq[11] = seq[31:24];
            c = 32'hFFFFFFFF;
            for (q = a; q < b; q = q + 1) begin
                aq[16 + 2 * (q - a)] = jobs[q][7:0]; aq[17 + 2 * (q - a)] = jobs[q][15:8];
                c = ecrc8(ecrc8(c, jobs[q][7:0]), jobs[q][15:8]);
            end
            c = ~c;
            aq[12] = c[7:0]; aq[13] = c[15:8]; aq[14] = c[23:16]; aq[15] = c[31:24];
        end
    endtask
    // send aq[0..n-1], wait for the RRES; returns status and output word count
    integer st_o, cnt_o, c0;
    realtime tf0;
    task automatic xfer(input integer n, input [31:0] seq);
        begin
            eth_build(n, 16'h88B5); c0 = erx_cnt; tf0 = $realtime;
            eth_send(0);
            eth_wait(c0, 5000, eth_got);
            st_o = -1; cnt_o = -1;
            if (!eth_got) fail("no RRES frame");
            else if ({erb[24], erb[25], erb[26], erb[27]} !== "RRES" || {erb[35], erb[34], erb[33], erb[32]} !== seq)
                fail("RRES magic/seq");
            else begin st_o = erb[29]; cnt_o = {erb[31], erb[30]}; end
        end
    endtask
    integer i, a, b, ei, tiles, n, q, bad, us_total, h, maxfr;
    reg [31:0] c;
    initial begin
        for (i = 0; i < 65536; i = i + 1) begin jobs[i] = 16'hxxxx; expw[i] = 16'hxxxx; end
        $readmemh({VEC, "/jobs.memh"}, jobs);
        $readmemh({VEC, "/expect.memh"}, expw);
        nj = 0; while (jobs[nj] !== 16'hxxxx) nj = nj + 1;
        ne = 0; while (expw[ne] !== 16'hxxxx) ne = ne + 1;
        #200; pll_locked = 1;
        repeat (40) @(posedge sys_clk);
        // ---- loopback (link calibration path) ----
        for (q = 0; q < 64; q = q + 1) aq[q] = q * 7 + 1;
        aq[0] = "L";
        eth_build(64, 16'h88B5); c0 = erx_cnt; eth_send(0); eth_wait(c0, 200, eth_got);
        bad = !eth_got || {erb[23], erb[22]} !== 16'd64;
        for (q = 0; q < 64 && !bad; q = q + 1) if (erb[24 + q] !== aq[q]) bad = 1;
        if (bad) fail("loopback");
        $display("TEST r10g_loopback done errors=%0d", errors);
        // ---- every tile as one RJOB frame ----
        a = 0; ei = 0; tiles = 0; us_total = 0;
        while (a < nj) begin
            b = a;
            while (b < nj && jobs[b] !== 16'd3) b = b + (jobs[b] == 16'd1 ? 5 : jobs[b] == 16'd2 ? 11 : 1);
            b = b + 1;                                            // include TILE_END
            make_rjob(a, b, 32'h100 + tiles, 8'd1, n);
            xfer(n, 32'h100 + tiles);
            if (st_o !== 0 || cnt_o !== 1029) begin
                $display("TB_ERROR tile %0d: status %0d count %0d", tiles, st_o, cnt_o); errors = errors + 1;
            end else begin
                bad = 0; c = 32'hFFFFFFFF;
                for (q = 0; q < 1029; q = q + 1) begin
                    if ({erb[41 + 2 * q], erb[40 + 2 * q]} !== expw[ei + q]) bad = bad + 1;
                    c = ecrc8(ecrc8(c, erb[40 + 2 * q]), erb[41 + 2 * q]);
                end
                if (bad) begin $display("TB_ERROR tile %0d: %0d words differ", tiles, bad); errors = errors + 1; end
                if (~c !== {erb[39], erb[38], erb[37], erb[36]}) fail("RRES CRC");
            end
            us_total = us_total + (erx_t - tf0) / 1000.0;
            if (tiles == 0) $display("INFO tile 0: %0d job words, round trip %0.1f us", b - a, (erx_t - tf0) / 1000.0);
            ei = ei + 1029; a = b; tiles = tiles + 1;
            // ---- after tile 3: corrupted frame -> PAYLOAD_CRC, nothing drawn ----
            if (tiles == 3) begin
                make_rjob(0, 17, 32'hBAD, 8'd1, n);                 // TILE_BEGIN + 1 TRI + END of tile 0
                aq[20] = aq[20] ^ 8'h01;                             // flip one payload bit, CRC left as is
                xfer(n, 32'hBAD);
                if (st_o !== 4 || cnt_o !== 0) fail("corrupted payload not rejected with status 4");
            end
        end
        if (ei != ne) fail("expected-word count mismatch");
        $display("INFO %0d tiles over RGMII, %0d us total round trips (sequential, one tile in flight)", tiles, us_total);
        $display("TEST r10g_tiles_rgmii done errors=%0d", errors);
        // ---- every tile again in two halves (opcodes 2/3), each a standard <= 1518-byte frame ----
        a = 0; ei = 0; tiles = 0; us_total = 0; maxfr = 0;
        while (a < nj) begin
            b = a;
            while (b < nj && jobs[b] !== 16'd3) b = b + (jobs[b] == 16'd1 ? 5 : jobs[b] == 16'd2 ? 11 : 1);
            b = b + 1;
            for (h = 0; h < 2; h = h + 1) begin
                if (h == 0) make_rjob(a, b, 32'h200 + 2 * tiles, 8'd2, n);
                else        make_rjob(b - 1, b, 32'h201 + 2 * tiles, 8'd3, n);   // TILE_END alone re-emits the tile
                xfer(n, 32'h200 + 2 * tiles + h);
                us_total = us_total + (erx_t - tf0) / 1000.0;
                if (ern - 8 > maxfr) maxfr = ern - 8;
                if (st_o !== 0 || cnt_o !== (h ? 514 : 515)) begin
                    $display("TB_ERROR half tile %0d.%0d: status %0d count %0d", tiles, h, st_o, cnt_o); errors = errors + 1;
                end else begin
                    bad = 0; c = 32'hFFFFFFFF;
                    for (q = 0; q < cnt_o; q = q + 1) begin
                        if ({erb[41 + 2 * q], erb[40 + 2 * q]} !== expw[ei + (h ? 515 : 0) + q]) bad = bad + 1;
                        c = ecrc8(ecrc8(c, erb[40 + 2 * q]), erb[41 + 2 * q]);
                    end
                    if (bad) begin $display("TB_ERROR half tile %0d.%0d: %0d words differ", tiles, h, bad); errors = errors + 1; end
                    if (~c !== {erb[39], erb[38], erb[37], erb[36]}) fail("RRES CRC (half)");
                end
            end
            ei = ei + 1029; a = b; tiles = tiles + 1;
        end
        if (maxfr > 1518) fail("half-tile frame larger than 1518 bytes");
        $display("INFO %0d tiles as halves, largest frame %0d bytes incl. FCS, %0d us total round trips", tiles, maxfr, us_total);
        // a half request whose job does not produce exactly one tile -> status 7
        make_rjob(0, 5, 32'h7A, 8'd2, n); xfer(n, 32'h7A);                 // TILE_BEGIN only: no tile output
        if (st_o !== 7 || cnt_o !== 0) fail("half request without a tile not status 7");
        // a job ending inside a command (TILE_BEGIN cut after 4 of 5 words) -> status 5, engine still serves jobs
        make_rjob(0, 4, 32'h7B, 8'd1, n); xfer(n, 32'h7B);
        if (st_o !== 5 || cnt_o !== 0) fail("truncated command not status 5");
        make_rjob(0, 17, 32'h7C, 8'd1, n); xfer(n, 32'h7C);                // tile 0 again, complete
        bad = (st_o !== 0 || cnt_o !== 1029);
        for (q = 0; q < 1029 && !bad; q = q + 1) if ({erb[41 + 2 * q], erb[40 + 2 * q]} !== expw[q]) bad = 1;
        if (bad) fail("tile after a truncated command not exact");
        $display("TEST r10g_tiles_halves done errors=%0d", errors);
        // ---- bad opcode / bad length ----
        make_rjob(0, 5, 32'h77, 8'd9, n); xfer(n, 32'h77); if (st_o !== 3) fail("bad opcode not status 3");
        make_rjob(0, 5, 32'h78, 8'd1, n); aq[6] = 8'd6; xfer(n, 32'h78); if (st_o !== 1) fail("bad length not status 1");
        // ---- STATUS ----
        make_rjob(0, 0, 32'h79, 8'h10, n); xfer(n, 32'h79);
        if (st_o !== 0 || {erb[23], erb[22]} !== 16'd48 || {erb[40], erb[41], erb[42], erb[43]} !== "R10G")
            fail("STATUS frame");
        else $display("INFO status: rev=%0d caps=%04h rx_ok=%0d tx=%0d tris=%0d samples=%0d written=%0d",
                      {erb[45], erb[44]}, {erb[47], erb[46]}, {erb[49], erb[48]}, {erb[57], erb[56]},
                      {erb[63], erb[62], erb[61], erb[60]}, {erb[67], erb[66], erb[65], erb[64]}, {erb[71], erb[70], erb[69], erb[68]});
        $display("TEST r10g_errors_status done errors=%0d", errors);
`ifdef MEMTOP
        if (({erb[47], erb[46]} & 16'h007F) !== 16'h002F || {erb[47], erb[46]} >> 7 == 0)
            fail("STATUS caps: SDRAM present + init + self test pass + calibration done with a window expected");
        $display("INFO SDRAM calibration: window %0d phase steps, centre %0d, capture latency +%0d",
                 dut.cal_w, dut.cal_c, dut.cal_extra);
        if (u_sdm.violations != 0) fail("SDRAM model protocol violations");
        $display("INFO SDRAM: self test %0s, errors %0d, refreshes %0d, model act=%0d rd=%0d wr=%0d ref=%0d violations=%0d",
                 dut.b_pass ? "PASS" : "FAIL", dut.b_errs, dut.cnt_refresh, u_sdm.n_act, u_sdm.n_rd, u_sdm.n_wr, u_sdm.n_ref,
                 u_sdm.violations);
        $display("TEST r10g_sdram done errors=%0d", errors);
`endif
        if (rc_edges < 1000 || rc_per < 7.99 || rc_per > 8.01) fail("gmac_refclk not 125 MHz");
        $display("gmac_refclk edges=%0d period=%0.3f ns", rc_edges, rc_per);
        if (errors == 0) $display("R10_45F_TB_PASS"); else $display("R10_45F_TB_FAIL errors=%0d", errors);
        $finish;
    end
endmodule
