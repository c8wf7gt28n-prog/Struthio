// ARC-1 R10 -- system testbench for the 12F MEMORY variant (r10_support_mem_top, ARC1_MEMORY_R10 s2.4): the full
// tb_r10_support sequence (reference AJOB cases now pass through r10_mem_engine) plus the PSRAM opcodes against the
// R07 APS6404L protocol-checking model: BAD_STATE before PSRAM init, BIST, 4096-byte unaligned write/read across
// 256-byte boundaries, end-of-memory and RANGE, corrupted-payload write leaves memory untouched, bad length,
// model rule violations = 0. Derived from tb_r10_support.sv: host EMAC model (copied from
// R85C_WORK/fpga_ecp5/tb/tb_ecp5_top.sv at 0defcfe) sends AJOB frames over RGMII and checks every response.
//   * cases 0..10 (transform batches, error frames, legacy loopback) byte-for-byte against the C reference
//     (firmware/tools/ajob_vectors.c, R85C build), including the 170-job (8176-byte) batch
//   * STATUS (opcode 0x10): magic "R10S", interface revision, caps (FIR absent), counters, header CRC
//   * FIR opcodes 2/3 -> BAD_OPCODE (status 3) because HAS_FIR = 0 on the 12F
//   * bad FCS / wrong EtherType ignored and counted
// RTL SIMULATION ONLY.
`timescale 1ns/1ps
module tb_r10_support_mem;
    parameter AJOB_DIR = "build/ajob";
    `include "ajob_cases.svh"
    reg clk_25m = 0;
    always #20 clk_25m = ~clk_25m;
    reg        h_txc = 1'b0;
    reg  [3:0] h_txd = 4'h0;
    reg        h_txctl = 1'b0;
    wire       e_txc, e_txctl, led, irq_n;
    wire [3:0] e_txd;
    always #4 h_txc = ~h_txc;
    pullup (weak1) pu_irq (irq_n);
    wire       psram_ce_n, psram_sclk;
    wire [3:0] psram_sio;
    pullup (weak1) pu_ce (psram_ce_n);
    r10_support_mem_top #(.HAS_FIR(0)) dut (
        .clk_25m(clk_25m), .rgmii_rxc(h_txc), .rgmii_rxd(h_txd), .rgmii_rx_ctl(h_txctl),
        .rgmii_txc(e_txc), .rgmii_txd(e_txd), .rgmii_tx_ctl(e_txctl), .led(led), .irq_n(irq_n),
        .psram_ce_n(psram_ce_n), .psram_sclk(psram_sclk), .psram_sio(psram_sio));
    aps6404l_model_r07 u_ps (.ce_n(psram_ce_n), .sclk(psram_sclk), .sio(psram_sio));
    reg pll_locked = 0;
    initial force dut.u_pll.locked = pll_locked;
    wire sys_clk = dut.sys_clk;

    integer errors = 0;
    task automatic fail(input [8*72-1:0] m);
        begin errors = errors + 1; $display("TB_ERROR t=%0t %0s", $time, m); end
    endtask
    reg [7:0] aq [0:8191];
    reg [7:0] ar [0:8191];
    task automatic load_case(input integer k);
        reg [8*160-1:0] fq, fr;
        begin
            $sformat(fq, "%0s/ajob_%0d_req.memh", AJOB_DIR, k);
            $sformat(fr, "%0s/ajob_%0d_resp.memh", AJOB_DIR, k);
            $readmemh(fq, aq);
            $readmemh(fr, ar);
        end
    endtask

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
    realtime eth_t0;
    task automatic run_eth(input integer k);
        integer c0;
        begin
            load_case(k);
            eth_build(ajob_qlen(k), 16'h88B5);
            c0 = erx_cnt; eth_t0 = $realtime;
            eth_send(0);
            eth_wait(c0, 20000, eth_got);
            if (!eth_got) fail("RGMII: no response frame");
            else begin
                eth_check(ajob_rlen(k), "rgmii ajob");
                $display("INFO rgmii case=%0d req=%0d resp=%0d status=%0d round_trip=%0.2f us (first request preamble -> last response FCS)",
                         k, ajob_qlen(k), ajob_rlen(k), ajob_status(k), (erx_t - eth_t0) / 1000.0);
            end
        end
    endtask

    // STATUS: request = AJOB header, opcode 0x10, count 0, seq, crc 0
    task automatic run_status(input [31:0] seq, output integer ok);
        integer c0, q;
        reg [31:0] c, hc;
        begin
            for (q = 0; q < 16; q = q + 1) aq[q] = 8'h00;
            aq[0] = "A"; aq[1] = "J"; aq[2] = "O"; aq[3] = "B"; aq[4] = 8'd1; aq[5] = 8'h10;
            aq[8] = seq[7:0]; aq[9] = seq[15:8]; aq[10] = seq[23:16]; aq[11] = seq[31:24];
            eth_build(16, 16'h88B5); c0 = erx_cnt;
            eth_send(0);
            eth_wait(c0, 200, eth_got);
            ok = 0;
            if (!eth_got) fail("STATUS: no response");
            else if ({erb[23], erb[22]} !== 16'd48) fail("STATUS: len16 != 48");
            else begin
                c = 32'hFFFFFFFF;
                for (q = 0; q < 32; q = q + 1) c = ecrc8(c, erb[40 + q]);
                hc = {erb[39], erb[38], erb[37], erb[36]};
                if ({erb[24], erb[25], erb[26], erb[27]} !== "ARES" || erb[29] !== 8'd0 || erb[30] !== 8'd0 ||
                    {erb[35], erb[34], erb[33], erb[32]} !== seq) fail("STATUS: header");
                else if (hc !== ~c) fail("STATUS: payload CRC");
                else if ({erb[40], erb[41], erb[42], erb[43]} !== "R10S") fail("STATUS: magic");
                else if ({erb[45], erb[44]} !== 16'h0001 || {erb[47], erb[46]} !== (dut.ram_ready ? 16'h001D : 16'h000D)) fail("STATUS: rev/caps");
                else ok = 1;
                $display("INFO status: rev=%0d caps=%04h rx_ok=%0d rx_fcs=%0d rx_drop=%0d rx_other=%0d tx=%0d underrun=%0d jobs=%0d items=%0d uptime_ms=%0d",
                         {erb[45], erb[44]}, {erb[47], erb[46]}, {erb[49], erb[48]}, {erb[51], erb[50]}, {erb[53], erb[52]},
                         {erb[55], erb[54]}, {erb[57], erb[56]}, {erb[59], erb[58]},
                         {erb[63], erb[62], erb[61], erb[60]}, {erb[67], erb[66], erb[65], erb[64]},
                         {erb[71], erb[70], erb[69], erb[68]});
            end
        end
    endtask

    // ---------------- PSRAM opcodes ----------------
    reg [7:0] md [0:4095];
    integer m_st, m_cnt;
    task automatic mem_req(input [7:0] op, input [31:0] addr, input integer n, input integer corrupt, input [31:0] seq);
        integer q, pl, c0m;
        reg [31:0] c;
        begin
            pl = (op == 8'h22) ? 0 : 4 + ((op == 8'h20) ? n : 0);
            aq[0] = "A"; aq[1] = "J"; aq[2] = "O"; aq[3] = "B"; aq[4] = 8'd1; aq[5] = op;
            aq[6] = n[7:0]; aq[7] = n[15:8];
            aq[8] = seq[7:0]; aq[9] = seq[15:8]; aq[10] = seq[23:16]; aq[11] = seq[31:24];
            if (pl) begin aq[16] = addr[7:0]; aq[17] = addr[15:8]; aq[18] = addr[23:16]; aq[19] = addr[31:24]; end
            if (op == 8'h20) for (q = 0; q < n; q = q + 1) aq[20 + q] = md[q];
            c = 32'hFFFFFFFF;
            for (q = 0; q < pl; q = q + 1) c = ecrc8(c, aq[16 + q]);
            c = ~c;
            aq[12] = c[7:0]; aq[13] = c[15:8]; aq[14] = c[23:16]; aq[15] = c[31:24];
            if (corrupt) aq[16 + pl - 1] = aq[16 + pl - 1] ^ 8'h40;
            eth_build(16 + pl, 16'h88B5); c0m = erx_cnt; eth_send(0);
            eth_wait(c0m, 20000, eth_got);
            m_st = -1; m_cnt = -1;
            if (!eth_got) fail("PSRAM op: no response");
            else if ({erb[24], erb[25], erb[26], erb[27]} !== "ARES" || {erb[35], erb[34], erb[33], erb[32]} !== seq)
                fail("PSRAM op: magic/seq");
            else begin
                m_st = erb[29]; m_cnt = {erb[31], erb[30]};
                if ({erb[23], erb[22]} !== 16 + m_cnt) fail("PSRAM op: len16 != 16 + count");
                if (m_cnt != 0) begin
                    c = 32'hFFFFFFFF;
                    for (q = 0; q < m_cnt; q = q + 1) c = ecrc8(c, erb[40 + q]);
                    if (~c !== {erb[39], erb[38], erb[37], erb[36]}) fail("PSRAM op: response CRC");
                end
            end
        end
    endtask
    task automatic mem_check_read(input integer n, input [8*40-1:0] what);
        integer q, bad;
        begin
            bad = 0;
            if (m_st !== 0 || m_cnt !== n) begin $display("TB_ERROR %0s: status %0d count %0d", what, m_st, m_cnt); errors = errors + 1; end
            else begin
                for (q = 0; q < n; q = q + 1) if (erb[40 + q] !== md[q]) bad = bad + 1;
                if (bad) begin $display("TB_ERROR %0s: %0d bytes differ", what, bad); errors = errors + 1; end
            end
        end
    endtask

    integer j, ok, c0, ok0, crc0, oth0, q, t_us;
    realtime tw;
    initial begin
        #200;
        pll_locked = 1;
        repeat (40) @(posedge sys_clk);
        // ---- PSRAM not initialised yet (tPU 150 us): BAD_STATE, nothing forwarded to accel_engine ----
        mem_req(8'h21, 32'd0, 16, 0, 32'h100);
        if (m_st !== 6 || m_cnt !== 0) fail("PSRAM read before init not BAD_STATE");
        // ---- cases 0..10 against the C reference over RGMII ----
        for (j = 0; j < 11; j = j + 1) run_eth(j);
        $display("TEST r10_ajob_rgmii done errors=%0d", errors);
        // ---- STATUS ----
        run_status(32'h5A5A0001, ok);
        if (ok && {erb[63], erb[62], erb[61], erb[60]} != 11) fail("STATUS: perf_jobs != 11");
        // + the early BAD_STATE PSRAM request: rx_ok 13 (incl. this STATUS request), tx 12 (its reply not yet counted)
        if (ok && ({erb[49], erb[48]} != 13 || {erb[57], erb[56]} != 12)) fail("STATUS: rx_ok != 13 or tx != 12");
        $display("TEST r10_status done errors=%0d", errors);
        // ---- FIR opcodes are rejected (HAS_FIR = 0) ----
        for (j = 11; j < 13; j = j + 1) begin
            load_case(j);
            eth_build(ajob_qlen(j), 16'h88B5); c0 = erx_cnt;
            eth_send(0);
            eth_wait(c0, 200, eth_got);
            if (!eth_got) fail("FIR op: no response");
            else if ({erb[23], erb[22]} !== 16'd16 || erb[29] !== 8'd3 || erb[30] !== 8'd0 || erb[31] !== 8'd0)
                fail("FIR op: expected BAD_OPCODE (3), count 0");
            else $display("INFO case %0d (FIR opcode %0d) -> status %0d (BAD_OPCODE, FIR not built)", j, aq[5], erb[29]);
        end
        $display("TEST r10_fir_absent done errors=%0d", errors);
        // ---- bad FCS / foreign EtherType: ignored and counted ----
        ok0 = dut.u_eth.cnt_rx_ok; crc0 = dut.u_eth.cnt_rx_crc; oth0 = dut.u_eth.cnt_rx_other;
        load_case(0);
        eth_build(ajob_qlen(0), 16'h88B5); c0 = erx_cnt; eth_send(1); eth_wait(c0, 50, eth_got);
        if (eth_got) fail("response to bad FCS");
        eth_build(ajob_qlen(0), 16'h0800); c0 = erx_cnt; eth_send(0); eth_wait(c0, 50, eth_got);
        if (eth_got) fail("response to IPv4 frame");
        if (dut.u_eth.cnt_rx_crc != crc0 + 1 || dut.u_eth.cnt_rx_other != oth0 + 1 || dut.u_eth.cnt_rx_ok != ok0)
            fail("RX counters after negative frames");
        run_status(32'h5A5A0002, ok);
        if (ok && ({erb[51], erb[50]} != 1 || {erb[55], erb[54]} != 1)) fail("STATUS does not show fcs=1 other=1");
        $display("TEST r10_negative done errors=%0d", errors);
        // ---- PSRAM ----
        t_us = 0; while (!dut.ram_ready && t_us < 2000) begin #1000; t_us = t_us + 1; end
        if (!dut.ram_ready) fail("PSRAM never ready");
        $display("INFO PSRAM ready at %0.1f us", $realtime / 1000.0);
        mem_req(8'h22, 0, 0, 0, 32'h101);
        if (m_st !== 0 || m_cnt !== 4 || {erb[43], erb[42], erb[41], erb[40]} !== 32'd0) fail("BIST");
        else $display("INFO BIST pass, errors 0");
        for (q = 0; q < 4096; q = q + 1) md[q] = (q * 37 + 11) ^ (q >> 4);
        tw = $realtime;
        mem_req(8'h20, 32'h0012345, 4096, 0, 32'h102);                  // unaligned, crosses 17 boundaries
        if (m_st !== 0 || m_cnt !== 0) fail("PSRAM write 4096");
        $display("INFO 4096-byte write round trip %0.1f us", ($realtime - tw) / 1000.0);
        tw = $realtime;
        mem_req(8'h21, 32'h0012345, 4096, 0, 32'h103);
        $display("INFO 4096-byte read round trip %0.1f us", ($realtime - tw) / 1000.0);
        mem_check_read(4096, "read-back 4096");
        // ---- corrupted payload: nothing written ----
        for (q = 0; q < 64; q = q + 1) md[q] = 8'hEE;
        mem_req(8'h20, 32'h0012345, 64, 1, 32'h104);
        if (m_st !== 4) fail("corrupted write not PAYLOAD_CRC");
        for (q = 0; q < 64; q = q + 1) md[q] = ((q * 37 + 11) ^ (q >> 4)) & 8'hFF;
        mem_req(8'h21, 32'h0012345, 64, 0, 32'h105);
        mem_check_read(64, "memory after rejected write");
        // ---- end of the 4 MiB and RANGE ----
        for (q = 0; q < 256; q = q + 1) md[q] = 255 - q;
        mem_req(8'h20, 32'h3FFF00, 256, 0, 32'h106); if (m_st !== 0) fail("write at the top 256 bytes");
        mem_req(8'h21, 32'h3FFF00, 256, 0, 32'h107); mem_check_read(256, "read at the top 256 bytes");
        mem_req(8'h21, 32'h3FFF01, 256, 0, 32'h108); if (m_st !== 9) fail("read past 4 MiB not RANGE");
        mem_req(8'h20, 32'h400000, 1, 0, 32'h109);   if (m_st !== 9) fail("write at 4 MiB not RANGE");
        // ---- single byte, bad lengths ----
        md[0] = 8'h5A;
        mem_req(8'h20, 32'h0000FF, 1, 0, 32'h10A); mem_req(8'h21, 32'h0000FF, 1, 0, 32'h10B); mem_check_read(1, "one byte");
        mem_req(8'h21, 32'd0, 0, 0, 32'h10C);    if (m_st !== 1) fail("read count 0 not BAD_LENGTH");
        mem_req(8'h21, 32'd0, 4097, 0, 32'h10D); if (m_st !== 1) fail("read count 4097 not BAD_LENGTH");
        // ---- the transform path still works after PSRAM traffic ----
        run_eth(0);
        if (u_ps.violations != 0) fail("PSRAM model rule violations");
        $display("INFO psram model violations=%0d mem_jobs=%0d mem_bytes=%0d", u_ps.violations, dut.mem_jobs, dut.mem_bytes);
        $display("TEST r10_psram done errors=%0d", errors);
        if (irq_n !== 1'b1) fail("irq_n asserted without a fault");
        if (errors == 0) $display("R10_12F_MEM_TB_PASS"); else $display("R10_12F_MEM_TB_FAIL errors=%0d", errors);
        $finish;
    end
endmodule
