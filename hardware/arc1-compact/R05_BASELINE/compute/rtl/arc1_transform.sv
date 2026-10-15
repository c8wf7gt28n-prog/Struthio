`timescale 1ns/1ps
`default_nettype none
module arc1_transform (
    input  wire clk,
    input  wire reset,
    input  wire in_valid,
    output wire in_ready,
    input  wire signed [31:0] in_xmin, in_ymin, in_xmax, in_ymax,
    input  wire signed [31:0] in_m00, in_m01, in_m02, in_m10, in_m11, in_m12,
    input  wire [15:0] in_viewport_width, in_viewport_height,
    input  wire [31:0] in_tag,
    output reg out_valid,
    input  wire out_ready,
    output reg signed [31:0] out_minx, out_miny, out_maxx, out_maxy,
    output reg [2:0] out_flags,
    output reg [31:0] out_tag
);
    reg busy, axis;
    reg [1:0] corner;
    reg signed [31:0] xmin, ymin, xmax, ymax;
    reg signed [31:0] m00, m01, m02, m10, m11, m12;
    reg [15:0] viewport_width, viewport_height;
    reg [31:0] tag;
    reg signed [31:0] minx, miny, maxx, maxy;
    reg saturated;
    wire signed [31:0] x = corner[0] ? xmax : xmin;
    wire signed [31:0] y = corner[1] ? ymax : ymin;
    wire signed [31:0] a = axis ? m10 : m00;
    wire signed [31:0] b = axis ? m11 : m01;
    wire signed [31:0] t = axis ? m12 : m02;
    wire signed [63:0] product0 = a * x;
    wire signed [63:0] product1 = b * y;
    wire signed [65:0] accumulator =
        $signed({{2{product0[63]}}, product0}) +
        $signed({{2{product1[63]}}, product1}) +
        ($signed({{34{t[31]}}, t}) <<< 16);

    function automatic [32:0] quantize(input reg signed [65:0] value);
        reg [65:0] magnitude;
        reg [49:0] rounded;
        reg signed [31:0] result_value;
        reg clipped;
        begin
            magnitude = value[65] ? (~value + 66'd1) : value;
            rounded = magnitude[65:16] + {{49{1'b0}}, magnitude[15]};
            clipped = 1'b0;
            if (!value[65] && rounded > 50'd2147483647) begin
                result_value = 32'sh7fffffff;
                clipped = 1'b1;
            end else if (value[65] && rounded > 50'd2147483648) begin
                result_value = 32'sh80000000;
                clipped = 1'b1;
            end else if (value[65]) begin
                result_value = -$signed(rounded[31:0]);
            end else begin
                result_value = $signed(rounded[31:0]);
            end
            quantize = {clipped, result_value};
        end
    endfunction

    wire [32:0] quantized = quantize(accumulator);
    wire signed [31:0] coordinate = $signed(quantized[31:0]);
    wire signed [31:0] next_miny = (corner == 0 || coordinate < miny) ? coordinate : miny;
    wire signed [31:0] next_maxy = (corner == 0 || coordinate > maxy) ? coordinate : maxy;
    wire signed [33:0] viewport_x_limit = $signed({2'b00, viewport_width, 16'b0});
    wire signed [33:0] viewport_y_limit = $signed({2'b00, viewport_height, 16'b0});
    wire visible = maxx >= 0 && next_maxy >= 0 &&
        $signed({{2{minx[31]}}, minx}) <= viewport_x_limit &&
        $signed({{2{next_miny[31]}}, next_miny}) <= viewport_y_limit;

    assign in_ready = !reset && !busy && (!out_valid || out_ready);

    always @(posedge clk) begin
        if (reset) begin
            busy <= 1'b0;
            axis <= 1'b0;
            corner <= 2'b0;
            saturated <= 1'b0;
            out_valid <= 1'b0;
            out_minx <= 0; out_miny <= 0; out_maxx <= 0; out_maxy <= 0;
            out_flags <= 0; out_tag <= 0;
            xmin <= 0; ymin <= 0; xmax <= 0; ymax <= 0;
            m00 <= 0; m01 <= 0; m02 <= 0; m10 <= 0; m11 <= 0; m12 <= 0;
            viewport_width <= 0; viewport_height <= 0; tag <= 0;
            minx <= 0; miny <= 0; maxx <= 0; maxy <= 0;
        end else begin
            if (out_valid && out_ready) out_valid <= 1'b0;
            if (in_valid && in_ready) begin
                xmin <= in_xmin; ymin <= in_ymin; xmax <= in_xmax; ymax <= in_ymax;
                m00 <= in_m00; m01 <= in_m01; m02 <= in_m02;
                m10 <= in_m10; m11 <= in_m11; m12 <= in_m12;
                viewport_width <= in_viewport_width; viewport_height <= in_viewport_height;
                tag <= in_tag; corner <= 0; axis <= 0; saturated <= 0;
                if (in_xmin > in_xmax || in_ymin > in_ymax ||
                    in_viewport_width == 0 || in_viewport_height == 0) begin
                    busy <= 0;
                    out_valid <= 1;
                    out_tag <= in_tag;
                    out_minx <= 0; out_miny <= 0; out_maxx <= 0; out_maxy <= 0;
                    out_flags <= 3'b100;
                end else begin
                    busy <= 1;
                end
            end else if (busy) begin
                saturated <= saturated | quantized[32];
                if (!axis) begin
                    if (corner == 0 || coordinate < minx) minx <= coordinate;
                    if (corner == 0 || coordinate > maxx) maxx <= coordinate;
                    axis <= 1;
                end else begin
                    miny <= next_miny; maxy <= next_maxy;
                    axis <= 0;
                    if (corner == 3) begin
                        busy <= 0;
                        out_valid <= 1;
                        out_tag <= tag;
                        out_minx <= minx; out_maxx <= maxx;
                        out_miny <= next_miny; out_maxy <= next_maxy;
                        out_flags <= {1'b0, saturated | quantized[32], visible};
                    end else begin
                        corner <= corner + 1'b1;
                    end
                end
            end
        end
    end
endmodule
`default_nettype wire
