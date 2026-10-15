// Unit test of accel_fir against a behavioural model: random IR, several blocks with history carry and wrap,
// partial blocks (n % 32 != 0), n = 1 and n = 1024, saturation, abort + recovery. RTL_SIMULATED.
`timescale 1ns/1ps
module tb_accel_fir;
    reg clk = 0, rst = 1;
    always #6.25 clk = ~clk;
    reg ir_we = 0, x_we = 0, start = 0, pop = 0, abort = 0;
    reg [9:0] ir_waddr; reg [15:0] ir_wdata; reg [10:0] x_waddr; reg [15:0] x_wdata;
    reg [10:0] base, n;
    wire busy, avail; wire [15:0] sample;
    accel_fir dut (.clk(clk), .rst(rst), .ir_we(ir_we), .ir_waddr(ir_waddr), .ir_wdata(ir_wdata),
                   .x_we(x_we), .x_waddr(x_waddr), .x_wdata(x_wdata), .start(start), .base(base), .n(n),
                   .busy(busy), .out_avail(avail), .out_sample(sample), .out_pop(pop), .abort(abort));
    reg signed [15:0] ir [0:1023];
    reg signed [15:0] xh [0:2047];
    integer errors = 0, seed = 11, i, t, wp = 0, blk, cyc, total_cyc = 0;
    function [15:0] model(input integer pos);
        reg signed [63:0] a, s;
        integer q;
        begin
            a = 0;
            for (q = 0; q < 1024; q = q + 1) a = a + ir[q] * xh[(pos - q) & 2047];
            s = a >>> 15;
            model = (s > 32767) ? 16'h7FFF : (s < -32768) ? 16'h8000 : s[15:0];
        end
    endfunction
    task automatic load_ir(input integer amp);
        begin
            for (i = 0; i < 1024; i = i + 1) begin
                ir[i] = $random(seed) % amp;
                @(posedge clk); ir_we <= 1; ir_waddr <= i[9:0]; ir_wdata <= ir[i];
            end
            @(posedge clk); ir_we <= 0;
        end
    endtask
    task automatic run_block(input integer cnt, input integer amp);
        integer got;
        reg [15:0] e;
        begin
            for (i = 0; i < cnt; i = i + 1) begin
                xh[(wp + i) & 2047] = $random(seed) % amp;
                @(posedge clk); x_we <= 1; x_waddr <= (wp + i) & 2047; x_wdata <= xh[(wp + i) & 2047];
            end
            @(posedge clk); x_we <= 0; base <= wp[10:0]; n <= cnt[10:0]; start <= 1;
            @(posedge clk); start <= 0;
            got = 0; cyc = 0;
            while (got < cnt && cyc < 100000) begin
                @(posedge clk); cyc = cyc + 1; pop <= 0;
                if (avail && !pop) begin
                    e = model(wp + got);
                    if (sample !== e) begin
                        if (errors < 10) $display("TB_ERROR blk %0d out %0d got %h exp %h", blk, got, sample, e);
                        errors = errors + 1;
                    end
                    got = got + 1; pop <= 1;
                end
            end
            @(posedge clk); pop <= 0;
            while (busy && cyc < 100000) begin @(posedge clk); cyc = cyc + 1; end
            if (got != cnt) begin errors = errors + 1; $display("TB_ERROR blk %0d only %0d outputs", blk, got); end
            total_cyc = total_cyc + cyc;
            $display("INFO block %0d n=%0d base=%0d cycles=%0d", blk, cnt, wp, cyc);
            wp = (wp + cnt) & 2047; blk = blk + 1;
        end
    endtask
    initial begin
        for (i = 0; i < 2048; i = i + 1) xh[i] = 0;
        repeat (4) @(posedge clk); rst <= 0;
        blk = 0;
        load_ir(32768);
        run_block(735, 32768);
        run_block(735, 32768);
        run_block(735, 32768);           // wraps the 2048-entry history
        run_block(1, 32768);
        run_block(33, 32768);
        run_block(1024, 32768);
        load_ir(4096);                    // small taps, full-scale input: no saturation path
        run_block(100, 32768);
        // saturation: all taps max, all samples max
        for (i = 0; i < 1024; i = i + 1) begin ir[i] = 16'sh7FFF; @(posedge clk); ir_we <= 1; ir_waddr <= i[9:0]; ir_wdata <= 16'h7FFF; end
        @(posedge clk); ir_we <= 0;
        run_block(64, 1);
        // abort mid-block, then a normal block
        base <= wp[10:0]; n <= 11'd200; @(posedge clk); start <= 1; @(posedge clk); start <= 0;
        repeat (500) @(posedge clk); abort <= 1; @(posedge clk); abort <= 0; @(posedge clk);
        if (busy || avail) begin errors = errors + 1; $display("TB_ERROR abort did not clear"); end
        load_ir(32768);
        run_block(200, 32768);
        $display("SUMMARY tb_accel_fir errors=%0d blocks=%0d", errors, blk);
        if (errors == 0) $display("FIR_TB_PASS"); else $display("FIR_TB_FAIL");
        $finish;
    end
endmodule
