// ARC-1 Compact R8.5 -- pipelined ECP5 implementation of the R05 compute contract v1
// (R05_BASELINE/compute/CONTRACT.md). Same module name and ports as the R05 RTL, so the
// unchanged R05 testbench (oracle vectors, stalls, reset cases) verifies it bit-exactly.
//
// Why: the R05 datapath (two 32x32 products + 66-bit sum + rounding in one cycle) closes at
// only ~21 MHz on LFE5U-45F-6 (nextpnr-ecp5, R8.5 probe), far below the 80 MHz sys clock.
// Here each 32x32 product is split into four <=17x17 signed partial products (one
// MULT18X18D each, 8 per job datapath), and the sums/rounding are spread over registered
// stages. Exactness: a = ah*2^16 + al with ah = a[31:16] (signed), al = a[15:0] (unsigned),
// so a*x = ah*xh*2^32 + (ah*xl + al*xh)*2^16 + al*xl exactly (|a*x| < 2^62, no overflow).
//
// Contract differences (cycle level only): a valid job needs 8 issue cycles + pipeline
// latency (= 18 cycles accept->out_valid instead of 8). One transaction in flight, same
// ready/valid, hold, invalid-input and reset semantics.
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
    localparam integer NST = 8;               // pipeline register stages S1..S8
    reg busy;
    reg [3:0] issue;                          // 0..8 operations issued
    // R8.5-C timing: the invalid-input check runs on the registered inputs over two cycles after accept
    // (chk1: compare -> inv, chk2: act); no operation is issued until it has passed. Invalid inputs now
    // answer 3 cycles after accept instead of 1 (cycle-level only; same outputs).
    reg       chk1, chk2, inv;
    reg [3:0] got;                            // results collected
    reg signed [31:0] xmin, ymin, xmax, ymax, m00, m01, m02, m10, m11, m12;
    reg [15:0] vw, vh;
    reg [31:0] tag;

    // ---------------- S0: operand select (registered) ----------------
    wire [1:0] corner = issue[2:1];
    wire       axis   = issue[0];
    reg        v0, ax0;
    reg signed [31:0] a0, b0, t0, x0, y0;
    always @(posedge clk) begin
        v0 <= 1'b0;
        if (!reset && busy && !chk1 && !chk2 && issue < 4'd8) begin
            v0  <= 1'b1;
            ax0 <= axis;
            a0  <= axis ? m10 : m00;
            b0  <= axis ? m11 : m01;
            t0  <= axis ? m12 : m02;
            x0  <= corner[0] ? xmax : xmin;
            y0  <= corner[1] ? ymax : ymin;
        end
    end

    // ---------------- S1: partial products (MULT18X18D) ----------------
    function automatic signed [16:0] lo17(input signed [31:0] v); lo17 = $signed({1'b0, v[15:0]}); endfunction
    function automatic signed [16:0] hi17(input signed [31:0] v); hi17 = $signed({v[31], v[31:16]}); endfunction
    reg        v1, ax1;
    reg signed [31:0] t1;
    reg signed [33:0] p_hh, p_hl, p_lh, p_ll, q_hh, q_hl, q_lh, q_ll;
    always @(posedge clk) begin
        v1 <= v0 & ~reset; ax1 <= ax0; t1 <= t0;
        p_hh <= hi17(a0) * hi17(x0); p_hl <= hi17(a0) * lo17(x0);
        p_lh <= lo17(a0) * hi17(x0); p_ll <= lo17(a0) * lo17(x0);
        q_hh <= hi17(b0) * hi17(y0); q_hl <= hi17(b0) * lo17(y0);
        q_lh <= lo17(b0) * hi17(y0); q_ll <= lo17(b0) * lo17(y0);
    end

    // ---------------- S2: cross terms; hh/ll are bit-disjoint (concatenate) ----------------
    reg        v2, ax2;
    reg signed [31:0] t2;
    reg signed [34:0] p_mid, q_mid;
    reg signed [63:0] p_out, q_out;
    always @(posedge clk) begin
        v2 <= v1 & ~reset; ax2 <= ax1; t2 <= t1;
        p_mid <= p_hl + p_lh;  q_mid <= q_hl + q_lh;
        p_out <= {p_hh[31:0], p_ll[31:0]};
        q_out <= {q_hh[31:0], q_ll[31:0]};
    end

    // ---------------- S3: full products ----------------
    reg        v3, ax3;
    reg signed [31:0] t3;
    reg signed [63:0] prod0, prod1;
    always @(posedge clk) begin
        v3 <= v2 & ~reset; ax3 <= ax2; t3 <= t2;
        prod0 <= p_out + ($signed({{29{p_mid[34]}}, p_mid}) <<< 16);
        prod1 <= q_out + ($signed({{29{q_mid[34]}}, q_mid}) <<< 16);
    end

    // ---------------- S4: product sum; S5: + translation ----------------
    reg        v4, ax4, v5, ax5;
    reg signed [31:0] t4;
    reg signed [65:0] sum01, acc;
    always @(posedge clk) begin
        v4 <= v3 & ~reset; ax4 <= ax3; t4 <= t3;
        sum01 <= $signed({{2{prod0[63]}}, prod0}) + $signed({{2{prod1[63]}}, prod1});
        v5 <= v4 & ~reset; ax5 <= ax4;
        acc <= sum01 + ($signed({{34{t4[31]}}, t4}) <<< 16);
    end

    // ---------------- S6: magnitude; S7: round; S8: clamp + sign ----------------
    reg        v6, ax6, neg6, v7, ax7, neg7, v8, ax8, sat8;
    reg [65:0] mag6;
    reg [49:0] rnd7;
    reg signed [31:0] coord8;
    always @(posedge clk) begin
        v6 <= v5 & ~reset; ax6 <= ax5; neg6 <= acc[65];
        mag6 <= acc[65] ? (~acc + 66'd1) : acc;
        v7 <= v6 & ~reset; ax7 <= ax6; neg7 <= neg6;
        rnd7 <= mag6[65:16] + {{49{1'b0}}, mag6[15]};
        v8 <= v7 & ~reset; ax8 <= ax7;
        if (!neg7 && rnd7 > 50'd2147483647)      begin coord8 <= 32'sh7fffffff; sat8 <= 1'b1; end
        else if (neg7 && rnd7 > 50'd2147483648)  begin coord8 <= 32'sh80000000; sat8 <= 1'b1; end
        else if (neg7)                           begin coord8 <= -$signed(rnd7[31:0]); sat8 <= 1'b0; end
        else                                     begin coord8 <= $signed(rnd7[31:0]); sat8 <= 1'b0; end
    end

    // ---------------- collector ----------------
    reg signed [31:0] minx, maxx, miny, maxy;
    reg firstx, firsty, saturated;
    wire signed [33:0] lim_x = $signed({2'b00, vw, 16'b0});
    wire signed [33:0] lim_y = $signed({2'b00, vh, 16'b0});
    // values including the result arriving this cycle (the last one completes the job)
    wire signed [31:0] fminx = (v8 && !ax8 && (firstx || coord8 < minx)) ? coord8 : minx;
    wire signed [31:0] fmaxx = (v8 && !ax8 && (firstx || coord8 > maxx)) ? coord8 : maxx;
    wire signed [31:0] fminy = (v8 &&  ax8 && (firsty || coord8 < miny)) ? coord8 : miny;
    wire signed [31:0] fmaxy = (v8 &&  ax8 && (firsty || coord8 > maxy)) ? coord8 : maxy;
    // visibility is evaluated one cycle after the last min/max update (registered values)
    wire visible = maxx >= 0 && maxy >= 0 &&
                   $signed({{2{minx[31]}}, minx}) <= lim_x && $signed({{2{miny[31]}}, miny}) <= lim_y;
    reg  finish;

    assign in_ready = !reset && !busy && (!out_valid || out_ready);

    always @(posedge clk) begin
        if (reset) begin
            busy <= 1'b0; issue <= 4'd0; got <= 4'd0; out_valid <= 1'b0; finish <= 1'b0; chk1 <= 1'b0; chk2 <= 1'b0; inv <= 1'b0;
            out_minx <= 0; out_miny <= 0; out_maxx <= 0; out_maxy <= 0; out_flags <= 0; out_tag <= 0;
            xmin <= 0; ymin <= 0; xmax <= 0; ymax <= 0;
            m00 <= 0; m01 <= 0; m02 <= 0; m10 <= 0; m11 <= 0; m12 <= 0;
            vw <= 0; vh <= 0; tag <= 0;
            minx <= 0; maxx <= 0; miny <= 0; maxy <= 0; firstx <= 1'b1; firsty <= 1'b1; saturated <= 1'b0;
        end else begin
            if (out_valid && out_ready) out_valid <= 1'b0;
            if (in_valid && in_ready) begin
                xmin <= in_xmin; ymin <= in_ymin; xmax <= in_xmax; ymax <= in_ymax;
                m00 <= in_m00; m01 <= in_m01; m02 <= in_m02; m10 <= in_m10; m11 <= in_m11; m12 <= in_m12;
                vw <= in_viewport_width; vh <= in_viewport_height; tag <= in_tag;
                issue <= 4'd0; got <= 4'd0; firstx <= 1'b1; firsty <= 1'b1; saturated <= 1'b0;
                busy <= 1'b1; chk1 <= 1'b1;
            end else if (busy && chk1) begin
                chk1 <= 1'b0; chk2 <= 1'b1;
                inv  <= xmin > xmax || ymin > ymax || vw == 0 || vh == 0;
            end else if (busy && chk2) begin
                chk2 <= 1'b0;
                if (inv) begin
                    busy <= 1'b0;
                    out_valid <= 1'b1;
                    out_tag <= tag;
                    out_minx <= 0; out_miny <= 0; out_maxx <= 0; out_maxy <= 0;
                    out_flags <= 3'b100;
                end
            end else if (busy) begin
                if (issue < 4'd8) issue <= issue + 4'd1;
                if (v8) begin
                    saturated <= saturated | sat8;
                    if (!ax8) begin minx <= fminx; maxx <= fmaxx; firstx <= 1'b0; end
                    else      begin miny <= fminy; maxy <= fmaxy; firsty <= 1'b0; end
                    got <= got + 4'd1;
                    if (got == 4'd7) finish <= 1'b1;
                end
                if (finish) begin
                    finish <= 1'b0;
                    busy <= 1'b0;
                    out_valid <= 1'b1;
                    out_tag <= tag;
                    out_minx <= minx; out_maxx <= maxx; out_miny <= miny; out_maxy <= maxy;
                    out_flags <= {1'b0, saturated, visible};
                end
            end
        end
    end
    wire unused_ok = &{1'b0, NST[0]};
endmodule
`default_nettype wire
