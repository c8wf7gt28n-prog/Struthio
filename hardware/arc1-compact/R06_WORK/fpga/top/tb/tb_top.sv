// ARC-1 Compact R06 -- system-level RTL testbench for arc1_t35_top:
// the testbench acts as the F133 SPI0 master (mode 0); the APS6404L model sits
// on the PSRAM pins. RTL SIMULATION ONLY.
`timescale 1ns/1ps
module tb_top;
    parameter real SYS_NS   = 12.5;   // 80 MHz
    parameter real MEM_NS   = 25.0;   // 40 MHz -> SCLK 20 MHz
    parameter      GOLD_DIR = "build";
    `include "golden_frames.svh"

    reg sys_clk = 0, mem_clk = 0, pll_locked = 0;
    always #(SYS_NS / 2.0) sys_clk = ~sys_clk;
    always #(MEM_NS / 2.0) mem_clk = ~mem_clk;

    // ---------------- pads ----------------
    reg  sck = 0, ss_n = 1, mosi = 0;
    wire miso_out, miso_oe, irq_out, irq_oe;
    wire miso_pad, irq_n_pad;
    assign miso_pad  = miso_oe ? miso_out : 1'bz;
    pullup (weak1) pu_miso (miso_pad);                // F133 PC5 internal pull-up
    assign irq_n_pad = irq_oe ? irq_out : 1'bz;
    pullup (weak1) pu_irq (irq_n_pad);                // 10k board pull-up
    wire       ce_n, sclk;
    wire [3:0] sio_out, sio_oe, sio;
    genvar g;
    generate for (g = 0; g < 4; g = g + 1) begin : g_sio
        assign sio[g] = sio_oe[g] ? sio_out[g] : 1'bz;
        pulldown (weak0) pd (sio[g]);                // 2.2k board pull-downs
    end endgenerate
    wire led, dbg_tx;

    arc1_t35_top #(.SYS_HZ(80000000), .MCLK_HZ(40000000), .BIST_BLOCKS(64)) dut (
        .sys_clk(sys_clk), .psram_mclk(mem_clk), .pll_locked(pll_locked),
        .t35_sck_IN(sck), .t35_ss_n_IN(ss_n), .t35_mosi_IN(mosi),
        .t35_miso_OUT(miso_out), .t35_miso_OE(miso_oe),
        .t35_irq_n_OUT(irq_out), .t35_irq_n_OE(irq_oe),
        .psram_ce_n(ce_n), .psram_sclk(sclk),
        .psram_sio_IN(sio), .psram_sio_OUT(sio_out), .psram_sio_OE(sio_oe),
        .t35_led0(led), .t35_dbg_tx(dbg_tx));

    aps6404l_model psram (.ce_n(ce_n), .sclk(sclk), .sio(sio));

    // ---------------- checks ----------------
    integer errors = 0;
    task automatic fail(input [8*72-1:0] m);
        begin errors = errors + 1; $display("TB_ERROR t=%0t %0s", $realtime, m); end
    endtask
    always @(sio_oe or psram.doe) if (|(sio_oe & psram.doe)) fail("PSRAM bus contention");

    // MISO must be released whenever SS_N is high (checked 4 sys clocks after)
    always @(posedge ss_n) begin
        repeat (4) @(posedge sys_clk);
        if (ss_n && miso_oe) fail("MISO driven while SS_N high");
    end

    // ---------------- SPI master (F133 model) ----------------
    real    hp = 50.0;                  // SCK half period
    reg [7:0] tx [0:8199];
    reg [7:0] rx [0:8199];
    task automatic spi(input integer n);
        integer i, b;
        begin
            ss_n = 0; #(2 * hp);         // F133 ts(cs) = 2T
            for (i = 0; i < n; i = i + 1)
                for (b = 7; b >= 0; b = b - 1) begin
                    mosi = tx[i][b];
                    #(hp); sck = 1;
                    rx[i][b] = miso_pad;
                    #(hp); sck = 0;
                end
            #(2 * hp); ss_n = 1; #(4 * hp);
        end
    endtask
    reg [7:0] payload [0:8191];
    task automatic write_mem(input [15:0] a, input integer n);
        integer i;
        begin
            tx[0] = 8'h02; tx[1] = a[15:8]; tx[2] = a[7:0];
            for (i = 0; i < n; i = i + 1) tx[3 + i] = payload[i];
            spi(3 + n);
        end
    endtask
    task automatic read_mem(input [15:0] a, input integer n);   // result in rx[4..]
        integer i;
        begin
            tx[0] = 8'h0B; tx[1] = a[15:8]; tx[2] = a[7:0];
            for (i = 3; i < 4 + n; i = i + 1) tx[i] = 8'h00;
            spi(4 + n);
        end
    endtask
    function [15:0] rx16(input integer o); rx16 = {rx[4 + o + 1], rx[4 + o]}; endfunction
    function [31:0] rx32(input integer o); rx32 = {rx[4 + o + 3], rx[4 + o + 2], rx[4 + o + 1], rx[4 + o]}; endfunction

    task automatic ctrl(input [7:0] v);
        begin payload[0] = v; write_mem(16'h000C, 1); end
    endtask
    task automatic set_req_len(input [15:0] l);
        begin payload[0] = l[7:0]; payload[1] = l[15:8]; write_mem(16'h0010, 2); end
    endtask
    reg [15:0] st;
    task automatic status;
        begin read_mem(16'h0008, 2); st = rx16(0); end
    endtask

    task automatic check_ident(input expect_ok);
        begin
            read_mem(16'h0000, 8);
            if (expect_ok) begin
                if ({rx[4], rx[5], rx[6], rx[7]} !== "AMBX") fail("MAGIC");
                if (rx16(4) !== 16'h0001) fail("VERSION");
                if (rx16(6) !== 16'h0003) fail("CAPS");
            end else if ({rx[4], rx[5], rx[6], rx[7]} === "AMBX") fail("MAGIC visible while FPGA not ready");
        end
    endtask

    // ---------------- sequence ----------------
    integer i, j, len, t, seed = 5;
    reg [7:0] gold [0:8191];
    initial begin
        // FPGA not configured / PLL not locked: host must see "not ready"
        #200;
        check_ident(0);
        if (rx[4] !== 8'hFF) fail("idle MISO should read pulled-up 0xFF");
        pll_locked = 1;
        repeat (20) @(posedge sys_clk);
        check_ident(1);
        status;
        if (!st[0]) fail("FPGA_READY");
        if (st[1]) fail("PSRAM_READY before tPU");
        $display("TEST ident done errors=%0d", errors);

        // buffer integrity at SCK = sys/8 and sys/16
        for (j = 0; j < 2; j = j + 1) begin
            hp = (j == 0) ? 4 * SYS_NS : 8 * SYS_NS;
            for (i = 0; i < 4120; i = i + 1) payload[i] = $random(seed);
            write_mem(16'h2000, 4120);
            read_mem(16'h2000, 4120);
            for (i = 0; i < 4120; i = i + 1) if (rx[4 + i] !== payload[i]) begin
                fail("REQ buffer readback"); i = 4120; end
        end
        hp = 4 * SYS_NS;
        $display("TEST buffer_integrity done errors=%0d", errors);

        // CS# abort mid-byte: only complete bytes are written, slave resynchronises
        payload[0] = 8'hA1; payload[1] = 8'hB2; write_mem(16'h2100, 2);
        tx[0] = 8'h02; tx[1] = 8'h21; tx[2] = 8'h00; tx[3] = 8'h5A;
        ss_n = 0; #(2 * hp);
        for (i = 0; i < 4 * 8 + 5; i = i + 1) begin      // 4 bytes + 5 bits
            mosi = (i < 32) ? tx[i / 8][7 - (i % 8)] : 1'b1;
            #(hp); sck = 1; #(hp); sck = 0;
        end
        #(2 * hp); ss_n = 1; #(4 * hp);
        read_mem(16'h2100, 2);
        if (rx[4] !== 8'h5A || rx[5] !== 8'hB2) fail("partial-byte abort handling");
        check_ident(1);
        $display("TEST cs_abort done errors=%0d", errors);

        // R05 golden wire frames through the transport loopback, byte-exact
        for (j = 0; j < NGOLD; j = j + 1) begin
            len = golden_len(j);
            case (j)
            0: $readmemh({GOLD_DIR, "/golden_0.memh"}, gold, 0, len - 1);
            1: $readmemh({GOLD_DIR, "/golden_1.memh"}, gold, 0, len - 1);
            2: $readmemh({GOLD_DIR, "/golden_2.memh"}, gold, 0, len - 1);
            3: $readmemh({GOLD_DIR, "/golden_3.memh"}, gold, 0, len - 1);
            default: $readmemh({GOLD_DIR, "/golden_4.memh"}, gold, 0, len - 1);
            endcase
            for (i = 0; i < len; i = i + 1) payload[i] = gold[i];
            write_mem(16'h2000, len);
            set_req_len(len);
            ctrl(8'h01);                                   // doorbell
            t = 0; while (irq_n_pad !== 1'b0 && t < 100000) begin #100; t = t + 100; end
            if (irq_n_pad !== 1'b0) fail("no IRQ after doorbell");
            status;
            if (!st[4] || st[3]) fail("RESP_READY/JOB_PENDING state");
            read_mem(16'h0014, 2);
            if (rx16(0) !== len) fail("RESP_LEN");
            read_mem(16'h4000, len);
            for (i = 0; i < len; i = i + 1) if (rx[4 + i] !== gold[i]) begin
                fail("golden frame altered by mailbox"); i = len; end
            ctrl(8'h02);                                   // RESP_ACK
            #(20 * SYS_NS);
            if (irq_n_pad !== 1'b1) fail("IRQ not released after RESP_ACK");
            $display("INFO golden frame %0d len=%0d passed through unchanged", j, len);
        end
        read_mem(16'h0018, 4);
        if (rx32(0) !== NGOLD) fail("DOORBELLS count");
        $display("TEST golden_loopback done errors=%0d", errors);

        // doorbell overrun / invalid length
        set_req_len(16); ctrl(8'h01); ctrl(8'h01);         // second ring while busy/resp pending
        status; if (!st[5]) fail("DOORBELL_OVERRUN not flagged");
        ctrl(8'h02); ctrl(8'h10);
        status; if (st[5]) fail("overrun not cleared");
        set_req_len(0); ctrl(8'h01);
        status; if (!st[5]) fail("zero-length doorbell accepted");
        ctrl(8'h10);
        $display("TEST doorbell_rules done errors=%0d", errors);

        // PSRAM ready + BIST pass
        t = 0; status;
        while (!st[1] && t < 400) begin #1000; t = t + 1; status; end
        if (!st[1]) fail("PSRAM_READY never set");
        if (st[2]) fail("PSRAM_ERROR set");
        ctrl(8'h08);
        t = 0; status;
        while (st[6] || (!st[7] && !st[8])) begin #20000; t = t + 1; status; if (t > 2000) begin fail("BIST hang"); st = 16'h0080; end end
        read_mem(16'h001C, 4);
        if (!st[7] || st[8] || rx32(0) != 0) fail("BIST should pass");
        $display("INFO bist pass=%0d fail=%0d errs=%0d", st[7], st[8], rx32(0));
        $display("TEST psram_bist_pass done errors=%0d", errors);

        // BIST must detect a corrupted byte (written block, before its read-back)
        ctrl(8'h08);
        wait (dut.u_bist.phase_read === 1'b1);
        psram.mem[23'h003F05] = ~psram.mem[23'h003F05];   // block 63, read last
        t = 0; status;
        while (st[6] || (!st[7] && !st[8])) begin #20000; t = t + 1; status; if (t > 2000) begin fail("BIST hang"); st = 16'h0100; end end
        read_mem(16'h001C, 4);
        if (!st[8] || st[7] || rx32(0) != 1) fail("BIST should report exactly one error");
        $display("INFO bist-with-fault pass=%0d fail=%0d errs=%0d", st[7], st[8], rx32(0));
        $display("TEST psram_bist_detects_fault done errors=%0d", errors);

        // PSRAM recover command
        ctrl(8'h04);
        #5000; status;
        t = 0; while (!st[1] && t < 100) begin #1000; t = t + 1; status; end
        if (!st[1]) fail("PSRAM not ready after recover");
        $display("TEST psram_recover done errors=%0d", errors);

        // FPGA reset in the middle of a job: host sees NOT ready, then a clean state
        for (i = 0; i < 64; i = i + 1) payload[i] = i;
        write_mem(16'h2000, 64); set_req_len(64);
        ss_n = 0; #(2 * hp);                               // start a doorbell write ...
        pll_locked = 0;                                    // ... and lose the FPGA
        #(40 * hp); ss_n = 1; #(4 * hp);
        check_ident(0);
        pll_locked = 1; repeat (20) @(posedge sys_clk);
        check_ident(1);
        status;
        if (st[3] || st[4] || st[5]) fail("stale job state after FPGA reset");
        read_mem(16'h0018, 4); if (rx32(0) != 0) fail("doorbell counter not reset");
        $display("TEST fpga_reset done errors=%0d", errors);

        $display("SUMMARY tb_top errors=%0d model_violations=%0d", errors, psram.violations);
        if (errors == 0 && psram.violations == 0) $display("TOP_TB_PASS"); else $display("TOP_TB_FAIL");
        $finish;
    end
    initial begin #200_000_000; $display("TOP_TB_FAIL global timeout"); $finish; end
endmodule
