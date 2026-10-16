// ARC-1 R10 -- r10_raster against the bit-exact C model (tools/raster_ref.c): every output word (tile header,
// 1024 colours, CRC) compared; random input gaps and random output back-pressure. RTL SIMULATION ONLY.
`timescale 1ns/1ps
module tb_r10_raster;
    parameter VEC = "build/vec";
    reg clk = 0, rst = 1;
    always #6.25 clk = ~clk;                              // 80 MHz
    reg  [15:0] jobs [0:65535];
    reg  [15:0] expw [0:65535];
    integer nj, ne, ji = 0, ei = 0, errors = 0, seed = 7, t0, t1;
    reg         in_valid = 0;
    reg  [15:0] in_data = 0;
    wire        in_ready, out_valid, busy;
    wire [15:0] out_data;
    reg         out_ready = 0;
    wire [31:0] c_tris, c_samples, c_written, c_busy, c_bad;
    r10_raster dut (.clk(clk), .rst(rst), .in_valid(in_valid), .abort(1'b0), .in_data(in_data), .in_ready(in_ready),
        .out_valid(out_valid), .out_data(out_data), .out_ready(out_ready), .busy(busy),
        .cnt_tris(c_tris), .cnt_samples(c_samples), .cnt_written(c_written), .cnt_busy_cycles(c_busy), .cnt_bad_cmd(c_bad));
    initial begin
        for (nj = 0; nj < 65536; nj = nj + 1) begin jobs[nj] = 16'hxxxx; expw[nj] = 16'hxxxx; end
        $readmemh({VEC, "/jobs.memh"}, jobs);
        $readmemh({VEC, "/expect.memh"}, expw);
        nj = 0; while (jobs[nj] !== 16'hxxxx) nj = nj + 1;
        ne = 0; while (expw[ne] !== 16'hxxxx) ne = ne + 1;
        $display("INFO %0d job words, %0d expected words", nj, ne);
        repeat (5) @(posedge clk); rst = 0;
        t0 = $time;
    end
    // input driver with random gaps
    always @(posedge clk) if (!rst) begin
        if (in_valid && in_ready) begin ji = ji + 1; in_valid <= 1'b0; end
        if ((!in_valid || (in_valid && in_ready)) && ji < nj && ($random(seed) & 3) != 0) begin
            in_valid <= 1'b1; in_data <= jobs[ji];
        end
    end
    // output checker with random back-pressure
    always @(posedge clk) if (!rst) begin
        if (out_valid && out_ready) begin
            if (out_data !== expw[ei]) begin
                if (errors < 10) $display("TB_ERROR word %0d: rtl %04h ref %04h", ei, out_data, expw[ei]);
                errors = errors + 1;
            end
            ei = ei + 1;
        end
        out_ready <= ($random(seed) & 7) != 0;
    end
    initial begin
        wait (!rst);
        wait (ei == ne || $time > 200000000);
        t1 = $time;
        repeat (10) @(posedge clk);
        if (ei != ne) begin $display("TB_ERROR only %0d of %0d words", ei, ne); errors = errors + 1; end
        if (out_valid) begin $display("TB_ERROR extra output word %04h", out_data); errors = errors + 1; end
        $display("INFO tris=%0d samples=%0d written=%0d busy_cycles=%0d bad_cmd=%0d elapsed=%0d ns", c_tris, c_samples,
                 c_written, c_busy, c_bad, t1 - t0);
        if (errors == 0) $display("R10_RASTER_TB_PASS"); else $display("R10_RASTER_TB_FAIL errors=%0d", errors);
        $finish;
    end
endmodule
