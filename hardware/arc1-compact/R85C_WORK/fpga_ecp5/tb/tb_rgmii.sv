// ARC-1 Compact R8.5-C -- unit testbench: rgmii_rx and rgmii_tx against a host EMAC model.
// Host TX: data launched 2 ns after each rxc edge it is not sampled on (centred, like the F133 ETXDC delay).
// Host RX: samples the ECP5 output 2 ns after each forwarded-clock edge (like the F133 ERXDC delay).
`timescale 1ns/1ps
`default_nettype none
module tb_rgmii;
    integer errors = 0;
    // ---------------- DUT: receive ----------------
    reg        rxc = 1'b0;
    reg  [3:0] rxd = 4'h0;
    reg        rx_ctl = 1'b0;
    reg        release_tgl = 1'b0;
    wire       buf_we, frame_tgl;
    wire [12:0] buf_waddr;
    wire [7:0] buf_wdata;
    wire [15:0] frame_len, cnt_ok, cnt_crc, cnt_drop, cnt_other;
    wire [47:0] src_mac;
    always #4 rxc = ~rxc;
    rgmii_rx u_rx (.rxc(rxc), .rxd(rxd), .rx_ctl(rx_ctl), .release_tgl(release_tgl),
        .buf_we(buf_we), .buf_waddr(buf_waddr), .buf_wdata(buf_wdata), .frame_tgl(frame_tgl),
        .frame_len(frame_len), .src_mac(src_mac), .cnt_ok(cnt_ok), .cnt_crc(cnt_crc), .cnt_drop(cnt_drop),
        .cnt_other(cnt_other));
    reg [7:0] rbuf [0:8191];
    always @(posedge rxc) if (buf_we) rbuf[buf_waddr] <= buf_wdata;

    // ---------------- DUT: transmit ----------------
    reg        txc = 1'b0;
    always #4.0 txc = ~txc;
    reg        start_tgl = 1'b0;
    reg [15:0] tx_len = 16'd0;
    reg [47:0] dst_mac = 48'h0;
    wire [12:0] tx_raddr;
    reg  [7:0] tbuf [0:8191];
    reg  [7:0] tx_q;
    wire       done_tgl, o_txc, o_ctl;
    wire [3:0] o_txd;
    always @(posedge txc) tx_q <= tbuf[tx_raddr];
    rgmii_tx u_tx (.txc(txc), .start_tgl(start_tgl), .tx_len(tx_len), .dst_mac(dst_mac),
        .buf_raddr(tx_raddr), .buf_rdata(tx_q), .done_tgl(done_tgl),
        .rgmii_txc(o_txc), .rgmii_txd(o_txd), .rgmii_tx_ctl(o_ctl));

    // ---------------- CRC ----------------
    function automatic [31:0] crc8(input [31:0] c, input [7:0] d);
        integer k;
        reg [31:0] x;
        begin
            x = c ^ {24'd0, d};
            for (k = 0; k < 8; k = k + 1) x = x[0] ? (x >> 1) ^ 32'hEDB88320 : (x >> 1);
            crc8 = x;
        end
    endfunction

    // ---------------- host transmit (frame bytes after SFD, without FCS) ----------------
    reg [7:0] fb [0:9000];
    integer   fn;
    task automatic put_byte(input [7:0] b, input er);
        begin
            @(negedge rxc); #2; rxd = b[3:0]; rx_ctl = 1'b1;
            @(posedge rxc); #2; rxd = b[7:4]; rx_ctl = 1'b1 ^ er;
        end
    endtask
    // er_at: byte index (after SFD) carrying RX_ER, -1 none; bad_fcs flips one FCS bit
    task automatic host_send(input integer er_at, input integer bad_fcs);
        integer k;
        reg [31:0] c;
        begin
            c = 32'hFFFFFFFF;
            for (k = 0; k < fn; k = k + 1) c = crc8(c, fb[k]);
            c = ~c;
            if (bad_fcs) c = c ^ 32'h00010000;
            for (k = 0; k < 7; k = k + 1) put_byte(8'h55, 1'b0);
            put_byte(8'hD5, 1'b0);
            for (k = 0; k < fn; k = k + 1) put_byte(fb[k], k == er_at);
            for (k = 0; k < 4; k = k + 1) put_byte(c[8*k +: 8], 1'b0);
            @(negedge rxc); #2; rx_ctl = 1'b0; rxd = 4'h0;
            @(posedge rxc); #2; rx_ctl = 1'b0;
            repeat (12) @(posedge rxc);                     // inter-frame gap
            repeat (4) @(posedge rxc);                      // let the MAC finish end-of-frame
        end
    endtask
    // build: dst, src, type, len16, payload (pattern seeded by seed), padded to 60 bytes
    task automatic build(input [15:0] type_, input [15:0] len16, input integer plen, input integer seed);
        integer k;
        begin
            for (k = 0; k < 6; k = k + 1) fb[k] = 8'h02 + k;
            fb[6] = 8'h02; fb[7] = 8'h00; fb[8] = 8'h00; fb[9] = 8'hF1; fb[10] = 8'h33; fb[11] = seed[7:0];
            fb[12] = type_[15:8]; fb[13] = type_[7:0]; fb[14] = len16[7:0]; fb[15] = len16[15:8];
            for (k = 0; k < plen; k = k + 1) fb[16 + k] = (k * 7 + seed * 13 + (k >> 8)) & 8'hFF;
            fn = 16 + plen;
            while (fn < 60) begin fb[fn] = 8'h00; fn = fn + 1; end
        end
    endtask
    task automatic expect_rx(input [15:0] ok, input [15:0] crc, input [15:0] drop, input [15:0] other, input [319:0] what);
        begin
            if (cnt_ok !== ok || cnt_crc !== crc || cnt_drop !== drop || cnt_other !== other) begin
                $display("ERROR %0s: counters ok=%0d crc=%0d drop=%0d other=%0d (exp %0d %0d %0d %0d)",
                         what, cnt_ok, cnt_crc, cnt_drop, cnt_other, ok, crc, drop, other);
                errors = errors + 1;
            end else $display("ok  %0s", what);
        end
    endtask
    task automatic check_buf(input integer len16, input integer seed, input [319:0] what);
        integer k, bad;
        begin
            bad = 0;
            if (frame_len !== len16[15:0]) begin $display("ERROR %0s: frame_len %0d", what, frame_len); errors = errors + 1; end
            if (src_mac !== {8'h02, 8'h00, 8'h00, 8'hF1, 8'h33, seed[7:0]}) begin
                $display("ERROR %0s: src_mac %h", what, src_mac); errors = errors + 1;
            end
            for (k = 0; k < len16; k = k + 1)
                if (rbuf[k] !== ((k * 7 + seed * 13 + (k >> 8)) & 8'hFF)) bad = bad + 1;
            if (bad) begin $display("ERROR %0s: %0d payload bytes differ", what, bad); errors = errors + 1; end
        end
    endtask
    task automatic do_release;
        begin release_tgl = ~release_tgl; repeat (6) @(posedge rxc); end
    endtask

    // ---------------- host receive ----------------
    reg [7:0] hb [0:9100];
    integer   hn = 0;
    reg [3:0] lo_n;
    reg       lo_v;
    always @(posedge o_txc) begin
        #2;
        lo_n = o_txd; lo_v = o_ctl;
    end
    always @(negedge o_txc) begin
        #2;
        if (lo_v && o_ctl) begin hb[hn] = {o_txd, lo_n}; hn = hn + 1; end
    end
    task automatic host_expect(input integer len, input integer seed, input [319:0] what);
        integer k, bad, body;
        reg [31:0] c;
        begin
            bad = 0;
            body = (16 + len < 60) ? 60 : 16 + len;
            if (hn != 8 + body + 4) begin
                $display("ERROR %0s: %0d bytes on the wire, expected %0d", what, hn, 8 + body + 4); errors = errors + 1;
            end else begin
                for (k = 0; k < 7; k = k + 1) if (hb[k] !== 8'h55) bad = bad + 1;
                if (hb[7] !== 8'hD5) bad = bad + 1;
                if ({hb[8], hb[9], hb[10], hb[11], hb[12], hb[13]} !== dst_mac) bad = bad + 1;
                if ({hb[14], hb[15], hb[16], hb[17], hb[18], hb[19]} !== 48'h02A1C1000001) bad = bad + 1;
                if ({hb[20], hb[21]} !== 16'h88B5 || {hb[23], hb[22]} !== len[15:0]) bad = bad + 1;
                for (k = 0; k < len; k = k + 1) if (hb[24 + k] !== ((k * 5 + seed) & 8'hFF)) bad = bad + 1;
                for (k = 16 + len; k < body; k = k + 1) if (hb[8 + k] !== 8'h00) bad = bad + 1;
                c = 32'hFFFFFFFF;
                for (k = 8; k < 8 + body + 4; k = k + 1) c = crc8(c, hb[k]);
                if (c !== 32'hDEBB20E3) begin $display("ERROR %0s: FCS residue %h", what, c); bad = bad + 1; end
                if (bad) begin $display("ERROR %0s: %0d mismatches", what, bad); errors = errors + 1; end
                else $display("ok  %0s (%0d bytes on the wire)", what, hn);
            end
        end
    endtask
    task automatic tx_send(input integer len, input integer seed, input [319:0] what);
        integer k;
        reg d0;
        begin
            for (k = 0; k < len; k = k + 1) tbuf[k] = (k * 5 + seed) & 8'hFF;
            hn = 0; tx_len = len[15:0]; dst_mac = {8'h02, 8'h00, 8'h00, 8'hF1, 8'h33, seed[7:0]};
            d0 = done_tgl;
            #20 start_tgl = ~start_tgl;
            fork : wt
                begin wait (done_tgl != d0); disable wt; end
                begin #200000; $display("ERROR %0s: done timeout", what); errors = errors + 1; disable wt; end
            join
            host_expect(len, seed, what);
        end
    endtask

    integer t0;
    initial begin
        repeat (10) @(posedge rxc);
        // --- receive ---
        build(16'h88B5, 16'd100, 100, 1);  host_send(-1, 0); expect_rx(1, 0, 0, 0, "rx good 100");   check_buf(100, 1, "rx good 100");
        build(16'h88B5, 16'd100, 100, 2);  host_send(-1, 0); expect_rx(1, 0, 1, 0, "rx while owned -> drop"); check_buf(100, 1, "owned buffer intact after drop");
        do_release;
        build(16'h88B5, 16'd5, 5, 3);      host_send(-1, 0); expect_rx(2, 0, 1, 0, "rx short padded");  check_buf(5, 3, "rx short padded");
        do_release;
        build(16'h88B5, 16'd300, 300, 4); host_send(-1, 1); expect_rx(2, 1, 1, 0, "rx bad FCS");
        build(16'h0800, 16'd64, 64, 5);    host_send(-1, 0); expect_rx(2, 1, 1, 1, "rx wrong EtherType");
        build(16'h88B5, 16'd64, 64, 6);    host_send(30, 0); expect_rx(2, 1, 1, 2, "rx RX_ER");
        build(16'h88B5, 16'd200, 100, 7); host_send(-1, 0); expect_rx(2, 1, 1, 3, "rx len16 > payload");
        build(16'h88B5, 16'd9000, 8192, 8);host_send(-1, 0); expect_rx(2, 1, 1, 4, "rx len16 > 8192");
        build(16'h88B5, 16'd8192, 8192, 9);host_send(-1, 0); expect_rx(3, 1, 1, 4, "rx 8192 max");      check_buf(8192, 9, "rx 8192 max");
        do_release;
        build(16'h88B5, 16'd1500, 1500, 10);host_send(-1, 0); expect_rx(4, 1, 1, 4, "rx 1500 after release"); check_buf(1500, 10, "rx 1500");
        // release arriving during a frame that started while owned: that frame is still dropped whole
        fork
            begin build(16'h88B5, 16'd400, 400, 11); host_send(-1, 0); end
            begin repeat (200) @(posedge rxc); release_tgl = ~release_tgl; end
        join
        expect_rx(4, 1, 2, 4, "rx release mid-frame -> whole frame dropped"); check_buf(1500, 10, "buffer intact after mid-frame release");
        build(16'h88B5, 16'd400, 400, 12); host_send(-1, 0); expect_rx(5, 1, 2, 4, "rx next frame accepted"); check_buf(400, 12, "rx next");
        build(16'h88B5, 16'd101, 100, 13); host_send(-1, 0); expect_rx(5, 1, 2, 5, "rx len16 = payload + 1 (boundary)");
        // --- transmit ---
        tx_send(16, 1, "tx 16 (padded)");
        tx_send(0, 2, "tx 0 (padded)");
        tx_send(44, 3, "tx 44 (exact minimum)");
        tx_send(45, 4, "tx 45");
        tx_send(1486, 5, "tx 1486");
        tx_send(8192, 6, "tx 8192");
        t0 = $time; tx_send(1486, 7, "tx back-to-back");
        $display("tx 1486-byte payload frame + IFG: %0d ns", $time - t0);
        if (errors == 0) $display("RGMII_TB_PASS"); else $display("RGMII_TB_FAIL errors=%0d", errors);
        $finish;
    end
endmodule
`default_nettype wire
