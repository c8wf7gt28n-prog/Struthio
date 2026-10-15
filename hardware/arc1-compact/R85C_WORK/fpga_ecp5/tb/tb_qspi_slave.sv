// Unit test: mbx_qspi_slave against a 64 KiB byte memory with the register file's read latency (2 clk).
// Single (0x02/0x0B) and quad (0x32/0x6B) frames at several SCK rates, random data, long bursts, back-to-back
// frames, CS# abort mid-byte, unknown command, idle bus while the clk domain is in reset. RTL_SIMULATED.
`timescale 1ns/1ps
module tb_qspi_slave;
    reg clk = 0, rst = 1;
    always #6.25 clk = ~clk;                       // 80 MHz
    reg sck = 0, cs_n = 1;
    reg [3:0] ho = 0; reg hon = 0;                 // host drive of IO[3:0] (hon: drive all four)
    reg mosi = 0, rel = 0;
    wire [3:0] io;
    wire [3:0] so, soe;
    assign io[0] = rel ? 1'bz : (hon ? ho[0] : mosi);
    assign io[3:1] = (hon && !rel) ? ho[3:1] : 3'bzzz;
    genvar gi;
    generate for (gi = 0; gi < 4; gi = gi + 1) begin : g
        assign io[gi] = soe[gi] ? so[gi] : 1'bz;
        pulldown (weak0) pd (io[gi]);
    end endgenerate
    wire [15:0] ba; wire bwe, bre, fe; wire [7:0] bwd;
    reg  [7:0] mem [0:65535];
    reg  [7:0] rq1, rq2;
    reg  [15:0] ra1;
    always @(posedge clk) begin
        if (bwe) mem[ba] <= bwd;
        ra1 <= ba; rq1 <= mem[ba]; rq2 <= rq1;        // registered once, like mbx_regs_r85 (sampled 2 clk after the address)
    end
    mbx_qspi_slave dut (.clk(clk), .rst(rst), .sck(sck), .cs_n(cs_n), .io_i(io), .io_o(so), .io_oe(soe),
                        .bus_addr(ba), .bus_we(bwe), .bus_wdata(bwd), .bus_re(bre), .bus_rdata(rq1), .frame_end(fe));
    real hp = 20.0;
    integer errors = 0, seed = 3, i, k, n;
    reg [7:0] buf_w [0:8191];
    reg [7:0] buf_r [0:8191];
    task automatic clk1(input b); begin mosi = b; #(hp); sck = 1; #(hp); sck = 0; end endtask
    task automatic hdr(input [7:0] c, input [15:0] a);
        integer b; reg [23:0] h;
        begin h = {c, a}; cs_n = 0; #(2 * hp); for (b = 23; b >= 0; b = b - 1) clk1(h[b]); end
    endtask
    task automatic fin; begin hon = 0; rel = 0; mosi = 0; #(hp); cs_n = 1; #80; end endtask
    task automatic wr1(input [15:0] a, input integer cnt);
        integer b;
        begin hdr(8'h02, a); for (i = 0; i < cnt; i = i + 1) for (b = 7; b >= 0; b = b - 1) clk1(buf_w[i][b]); fin; end
    endtask
    task automatic rd1(input [15:0] a, input integer cnt);
        integer b;
        begin
            hdr(8'h0B, a); for (b = 0; b < 8; b = b + 1) clk1(0);
            for (i = 0; i < cnt; i = i + 1) for (b = 7; b >= 0; b = b - 1) begin #(hp); sck = 1; buf_r[i][b] = io[1]; #(hp); sck = 0; end
            fin;
        end
    endtask
    task automatic wr4(input [15:0] a, input integer cnt);
        begin
            hdr(8'h32, a); hon = 1;
            for (i = 0; i < cnt; i = i + 1) for (k = 1; k >= 0; k = k - 1) begin
                ho = k ? buf_w[i][7:4] : buf_w[i][3:0]; #(hp); sck = 1; #(hp); sck = 0; end
            fin;
        end
    endtask
    task automatic rd4(input [15:0] a, input integer cnt);
        begin
            hdr(8'h6B, a); for (k = 0; k < 16; k = k + 1) clk1(0);
            rel = 1;
            for (i = 0; i < cnt; i = i + 1) for (k = 1; k >= 0; k = k - 1) begin
                #(hp); sck = 1; if (k) buf_r[i][7:4] = io; else buf_r[i][3:0] = io; #(hp); sck = 0; end
            fin;
        end
    endtask
    task automatic check(input [15:0] a, input integer cnt, input [8*24-1:0] what);
        integer e;
        begin
            e = 0;
            for (i = 0; i < cnt; i = i + 1) if (buf_r[i] !== mem[(a + i) & 16'hFFFF] && e < 4) begin
                $display("TB_ERROR %0s @%0d: got %h exp %h", what, i, buf_r[i], mem[(a + i) & 16'hFFFF]); e = e + 1; end
            errors = errors + e;
        end
    endtask
    task automatic checkw(input [15:0] a, input integer cnt, input [8*24-1:0] what);
        integer e;
        begin
            e = 0;
            #200;
            for (i = 0; i < cnt; i = i + 1) if (mem[(a + i) & 16'hFFFF] !== buf_w[i] && e < 4) begin
                $display("TB_ERROR %0s write @%0d: mem %h exp %h", what, i, mem[(a + i) & 16'hFFFF], buf_w[i]); e = e + 1; end
            errors = errors + e;
        end
    endtask
    integer sp;
    real rates [0:3];
    initial begin
        for (i = 0; i < 65536; i = i + 1) mem[i] = i[7:0] ^ 8'h5A;
        // reset: the slave must not drive anything
        hp = 20.0;
        rd1(16'h0000, 4);
        for (i = 0; i < 4; i = i + 1) if (buf_r[i] !== 8'h00) begin errors = errors + 1; $display("TB_ERROR driven while in reset: %h", buf_r[i]); end
        repeat (4) @(posedge clk); rst = 0; repeat (4) @(posedge clk);
        rates[0] = 50.0; rates[1] = 20.0; rates[2] = 10.0; rates[3] = 5.0;   // SCK 10, 25, 50, 100 MHz
        for (sp = 0; sp < 4; sp = sp + 1) begin
            hp = rates[sp];
            n = (sp == 0) ? 64 : 2048;
            if (sp < 2) begin                                          // single mode only up to 25 MHz
                for (i = 0; i < n; i = i + 1) buf_w[i] = $random(seed);
                wr1(16'h1000 + sp * 16'h100, n); checkw(16'h1000 + sp * 16'h100, n, "single");
                rd1(16'h1000 + sp * 16'h100, n); check(16'h1000 + sp * 16'h100, n, "single");
            end
            for (i = 0; i < n; i = i + 1) buf_w[i] = $random(seed);
            wr4(16'h4000 + sp * 16'h1000, n); checkw(16'h4000 + sp * 16'h1000, n, "quad");
            rd4(16'h4000 + sp * 16'h1000, n); check(16'h4000 + sp * 16'h1000, n, "quad");
            rd4(16'hFFF0, 40); check(16'hFFF0, 40, "quad wrap");
            $display("INFO SCK %0d MHz done errors=%0d", 500 / rates[sp], errors);
        end
        // CS# abort mid-byte in a single write: only whole bytes land
        hp = 20.0;
        mem[16'h0200] = 8'h11; mem[16'h0201] = 8'hBB;               // the frame sends 0xAA, then 5 stray bits
        hdr(8'h02, 16'h0200); for (k = 7; k >= 0; k = k - 1) clk1(k[0]); for (k = 0; k < 5; k = k + 1) clk1(1); fin;
        #200;
        if (mem[16'h0200] !== 8'hAA || mem[16'h0201] !== 8'hBB) begin errors = errors + 1; $display("TB_ERROR abort: %h %h", mem[16'h0200], mem[16'h0201]); end
        // unknown command is ignored
        hdr(8'hA5, 16'h0300); for (k = 0; k < 16; k = k + 1) clk1(1); fin; #200;
        if (mem[16'h0300] !== (8'h00 ^ 8'h5A)) begin errors = errors + 1; $display("TB_ERROR unknown command wrote memory"); end
        $display("SUMMARY tb_qspi_slave errors=%0d", errors);
        if (errors == 0) $display("QSPI_TB_PASS"); else $display("QSPI_TB_FAIL");
        $finish;
    end
endmodule
