// ARC-1 R10 -- ECP5-45F tile rasterizer, step 1 (R10 spec 7.1 items 2-3): flat-colour triangles with signed edge
// functions, top-left fill rule and a tile-local 16-bit Z buffer. Bit-exact with fpga45/tools/raster_ref.c (job
// format, geometry and depth arithmetic are specified there). 32x32 tile; colour + Z in EBR (2 x 2 KiB).
// Throughput: 1 sample/clock over bbox(triangle) intersect tile, ~70 clocks setup per triangle, 1024 clocks clear,
// 2 clocks per output word. Evidence: RTL_SIMULATED (tb_r10_raster) + open-toolchain P&R. Not on silicon.
`default_nettype none
module r10_raster (
    input  wire        clk,
    input  wire        rst,
    input  wire        in_valid,
    input  wire        abort,            // in S_ARGS only: drop a partly received command (nothing drawn yet)
    input  wire [15:0] in_data,
    output wire        in_ready,
    output reg         out_valid,
    output reg  [15:0] out_data,
    input  wire        out_ready,
    output wire        busy,
    output reg  [31:0] cnt_tris, cnt_samples, cnt_written, cnt_busy_cycles, cnt_bad_cmd
);
    localparam integer TS = 32;
    localparam [4:0] S_IDLE = 0, S_ARGS = 1, S_CLEAR = 2, S_T0 = 3, S_T1 = 4, S_T2 = 5, S_T3 = 6, S_T4 = 7, S_DIV = 8,
                     S_T5 = 9, S_T6A = 10, S_T6B = 11, S_SCAN = 12, S_DRAIN = 13, S_OHDR = 14, S_ORD = 15,
                     S_OWAIT = 16, S_OCOL = 17, S_OCRC = 18, S_T1B = 19, S_T3B = 20, S_T3C = 21, S_T3D = 22,
                     S_T3E = 23, S_T5B = 24, S_T6C = 25, S_T6D = 26, S_T5N = 27, S_OWAIT2 = 28;
    // R10 timing: setup is split into one-operation steps (products registered before sums; bbox in 3 steps)
    reg signed [36:0] p_a, p_b, p_c, p_d, q_a, q_b;   // q_*: area products (not shared with p_*)
    reg [15:0] cr_qq;
    reg signed [17:0] mnx, mxx, mny, mxy;
    reg signed [23:0] ra, rb, rc, rd;
    // tile_x/tile_y must be 0..2016 (job format): every sample offset then fits 18 bits -> one MULT18X18D each
    reg signed [17:0] dsx [0:2], dsy [0:2], dzx, dzy;
    reg signed [35:0] pxh, pxl, pyh, pyl;           // gx/gy split: high signed 16 x 18, low unsigned 16 x 18
    reg [4:0]  st;
    reg [15:0] cmd;
    reg [3:0]  nargs, ai;
    reg [15:0] arg [0:9];
    assign in_ready = (st == S_IDLE) || (st == S_ARGS);
    assign busy = (st != S_IDLE);

    function automatic [31:0] crc8(input [31:0] c, input [7:0] d);
        integer k;
        reg [31:0] x;
        begin
            x = c ^ {24'd0, d};
            for (k = 0; k < 8; k = k + 1) x = x[0] ? (x >> 1) ^ 32'hEDB88320 : (x >> 1);
            crc8 = x;
        end
    endfunction

    // ---------------- tile buffers ----------------
    reg  [4:0]  lx, ly, lx0;
    wire [9:0]  cur_a = {ly, lx};
    reg  [15:0] col_mem [0:TS*TS-1];
    reg  [15:0] z_mem   [0:TS*TS-1];
    reg         wr_en;
    reg  [9:0]  wr_a, cr_a;
    reg  [15:0] wr_col, wr_z, zr_q, cr_q;
    reg         wr_z_en;
    always @(posedge clk) begin
        if (wr_en) col_mem[wr_a] <= wr_col;
        cr_q <= col_mem[cr_a];
    end
    always @(posedge clk) begin
        if (wr_z_en) z_mem[wr_a] <= wr_z;
        zr_q <= z_mem[cur_a];                          // read for the sample being issued this clock
    end

    // ---------------- triangle state ----------------
    reg  [15:0] tile_x, tile_y, clr_c, clr_z, rgb;
    reg signed [17:0] x0, y0, x1, y1, x2, y2;
    reg  [15:0] z0, z1, z2;
    reg signed [17:0] dx1, dy1, dx2, dy2, dz1, dz2;
    reg signed [36:0] A, nx, ny;
    reg signed [17:0] edx [0:2], edy [0:2], eax [0:2], eay [0:2];
    reg        tl [0:2];
    reg signed [23:0] bx0, bx1, by0, by1;           // pixel bounds
    // dividers: |n| << 16 / A, 53 steps, two in parallel
    reg [52:0] qx, qy, dvx, dvy;
    reg [37:0] rx, ry;
    reg        sx_neg, sy_neg;
    reg [5:0]  dstep;
    reg signed [31:0] gx, gy;
    // scan
    reg signed [47:0] E [0:2], Erow [0:2], Ex [0:2], Ey [0:2];
    reg signed [63:0] zq, zqrow, zx, zy;
    reg signed [47:0] pe0 [0:2], pe1 [0:2];
    reg signed [63:0] pz0, pz1;
    reg signed [23:0] sx0, sy0, px, py;
    // stage B (Z compare / write)
    reg        b_v, b_in;
    reg [9:0]  b_a;
    reg [15:0] b_z;
    reg [1:0]  drain;
    reg        c_v, c_in;
    reg [9:0]  c_a;
    reg [15:0] c_z, c_zbuf;
    // output
    reg [10:0] oi;
    reg [31:0] ocrc;
    integer i;


    reg  signed [53:0] gxv, gyv;                   // signed quotients (negated in S_T5N, saturated in S_T5)
    // sample inside test + depth for the current scan position
    wire in0 = (E[0] > 48'sd0) || (E[0] == 48'sd0 && tl[0]);
    wire in1 = (E[1] > 48'sd0) || (E[1] == 48'sd0 && tl[1]);
    wire in2 = (E[2] > 48'sd0) || (E[2] == 48'sd0 && tl[2]);
    wire signed [47:0] zs = zq[63:16];
    wire [15:0] zc = zs < 48'sd0 ? 16'd0 : (zs > 48'sd65535 ? 16'hFFFF : zs[15:0]);

    always @(posedge clk) begin
        wr_en <= 1'b0; wr_z_en <= 1'b0;
        if (st != S_IDLE) cnt_busy_cycles <= cnt_busy_cycles + 32'd1;
        // ---- stage B: register the stored depth (EBR clock-to-out is not followed by logic) ----
        c_v <= b_v; c_in <= b_in; c_a <= b_a; c_z <= b_z; c_zbuf <= zr_q;
        // ---- stage C: Z compare and write (two clocks after the sample) ----
        if (c_v && c_in && c_z < c_zbuf) begin
            wr_en <= 1'b1; wr_z_en <= 1'b1; wr_a <= c_a; wr_col <= rgb; wr_z <= c_z;
            cnt_written <= cnt_written + 32'd1;
        end
        b_v <= 1'b0;
        if (rst) begin
            st <= S_IDLE; out_valid <= 1'b0; b_v <= 1'b0; c_v <= 1'b0;
            cnt_tris <= 0; cnt_samples <= 0; cnt_written <= 0; cnt_busy_cycles <= 0; cnt_bad_cmd <= 0;
        end else case (st)
        S_IDLE: if (in_valid) begin
            cmd <= in_data; ai <= 4'd0;
            if (in_data == 16'd1) begin nargs <= 4'd4; st <= S_ARGS; end
            else if (in_data == 16'd2) begin nargs <= 4'd10; st <= S_ARGS; end
            else if (in_data == 16'd3) begin oi <= 11'd0; ocrc <= 32'hFFFFFFFF; st <= S_OHDR; end
            else cnt_bad_cmd <= cnt_bad_cmd + 32'd1;
        end
        S_ARGS: if (abort) begin st <= S_IDLE; cnt_bad_cmd <= cnt_bad_cmd + 32'd1; end
        else if (in_valid) begin
            arg[ai] <= in_data;
            ai <= ai + 4'd1;
            if (ai == nargs - 4'd1) st <= (cmd == 16'd1) ? S_CLEAR : S_T0;
            if (ai == nargs - 4'd1 && cmd == 16'd1) begin
                tile_x <= arg[0]; tile_y <= arg[1]; clr_c <= arg[2]; clr_z <= in_data;   // arg[3] arrives now
                oi <= 11'd0;
            end
            if (ai == nargs - 4'd1 && cmd == 16'd2) begin
                x0 <= $signed({{2{arg[0][15]}}, arg[0]}); y0 <= $signed({{2{arg[1][15]}}, arg[1]}); x1 <= $signed({{2{arg[2][15]}}, arg[2]}); y1 <= $signed({{2{arg[3][15]}}, arg[3]});
                x2 <= $signed({{2{arg[4][15]}}, arg[4]}); y2 <= $signed({{2{arg[5][15]}}, arg[5]}); z0 <= arg[6]; z1 <= arg[7]; z2 <= arg[8]; rgb <= in_data;
            end
        end
        S_CLEAR: begin
            wr_en <= 1'b1; wr_z_en <= 1'b1; wr_a <= oi[9:0]; wr_col <= clr_c; wr_z <= clr_z;
            oi <= oi + 11'd1;
            if (oi == 11'd1023) st <= S_IDLE;
        end
        // ---- triangle setup ----
        S_T0: begin
            dx1 <= x1 - x0; dy1 <= y1 - y0; dx2 <= x2 - x0; dy2 <= y2 - y0;
            dz1 <= $signed({2'b00, z1}) - $signed({2'b00, z0}); dz2 <= $signed({2'b00, z2}) - $signed({2'b00, z0});
            st <= S_T1;
        end
        S_T1: begin q_a <= dx1 * dy2; q_b <= dx2 * dy1; st <= S_T1B; end
        S_T1B: begin A <= q_a - q_b; st <= S_T2; end
        S_T2: begin
            if (A == 37'sd0) st <= S_DRAIN;
            else if (A < 37'sd0) begin                       // clockwise: swap v1/v2 and recompute
                x1 <= x2; y1 <= y2; z1 <= z2; x2 <= x1; y2 <= y1; z2 <= z1; st <= S_T0;
            end else st <= S_T3;
        end
        S_T3: begin
            p_a <= dz1 * dy2; p_b <= dz2 * dy1; p_c <= dz2 * dx1; p_d <= dz1 * dx2;
            eax[0] <= x1; eay[0] <= y1; edx[0] <= x2 - x1; edy[0] <= y2 - y1;
            eax[1] <= x2; eay[1] <= y2; edx[1] <= x0 - x2; edy[1] <= y0 - y2;
            eax[2] <= x0; eay[2] <= y0; edx[2] <= x1 - x0; edy[2] <= y1 - y0;
            mnx <= (x0 < x1) ? x0 : x1; mxx <= (x0 > x1) ? x0 : x1;
            mny <= (y0 < y1) ? y0 : y1; mxy <= (y0 > y1) ? y0 : y1;
            st <= S_T3B;
        end
        S_T3B: begin
            nx <= p_a - p_b; ny <= p_c - p_d;
            if (x2 < mnx) mnx <= x2;
            if (x2 > mxx) mxx <= x2;
            if (y2 < mny) mny <= y2;
            if (y2 > mxy) mxy <= y2;
            st <= S_T3C;
        end
        S_T3C: begin                                       // first/last pixel whose centre can be inside
            ra <= ($signed({{6{mnx[17]}}, mnx}) + 24'sd7) >>> 4; rb <= ($signed({{6{mxx[17]}}, mxx}) - 24'sd8) >>> 4;
            rc <= ($signed({{6{mny[17]}}, mny}) + 24'sd7) >>> 4; rd <= ($signed({{6{mxy[17]}}, mxy}) - 24'sd8) >>> 4;
            st <= S_T3D;
        end
        S_T3D: begin                                       // clamp to the tile
            bx0 <= (ra < $signed({8'd0, tile_x})) ? $signed({8'd0, tile_x}) : ra;
            bx1 <= (rb > $signed({8'd0, tile_x}) + 24'sd31) ? $signed({8'd0, tile_x}) + 24'sd31 : rb;
            by0 <= (rc < $signed({8'd0, tile_y})) ? $signed({8'd0, tile_y}) : rc;
            by1 <= (rd > $signed({8'd0, tile_y}) + 24'sd31) ? $signed({8'd0, tile_y}) + 24'sd31 : rd;
            st <= S_T4;
        end
        S_T4: begin
            for (i = 0; i < 3; i = i + 1) tl[i] <= (edy[i] < 18'sd0) || (edy[i] == 18'sd0 && edx[i] > 18'sd0);
            if (bx0 > bx1 || by0 > by1) st <= S_DRAIN;
            else begin
                sx_neg <= nx[36]; sy_neg <= ny[36];
                dvx <= {(nx[36] ? -nx : nx), 16'd0}; dvy <= {(ny[36] ? -ny : ny), 16'd0};
                qx <= 53'd0; qy <= 53'd0; rx <= 38'd0; ry <= 38'd0; dstep <= 6'd0;
                st <= S_DIV;
            end
        end
        S_DIV: begin                                         // restoring division, MSB first
            begin : dv
                reg [38:0] tx_, ty_;
                tx_ = {rx, dvx[52]} - {2'b00, A};
                ty_ = {ry, dvy[52]} - {2'b00, A};
                if (!tx_[38]) begin rx <= tx_[37:0]; qx <= {qx[51:0], 1'b1}; end
                else begin rx <= {rx[36:0], dvx[52]}; qx <= {qx[51:0], 1'b0}; end
                if (!ty_[38]) begin ry <= ty_[37:0]; qy <= {qy[51:0], 1'b1}; end
                else begin ry <= {ry[36:0], dvy[52]}; qy <= {qy[51:0], 1'b0}; end
            end
            dvx <= {dvx[51:0], 1'b0}; dvy <= {dvy[51:0], 1'b0};
            dstep <= dstep + 6'd1;
            if (dstep == 6'd52) st <= S_T5N;
        end
        S_T5N: begin
            gxv <= sx_neg ? -$signed({1'b0, qx}) : $signed({1'b0, qx});
            gyv <= sy_neg ? -$signed({1'b0, qy}) : $signed({1'b0, qy});
            st <= S_T5;
        end
        S_T5: begin
            gx <= (gxv > 54'sd2147483647) ? 32'sh7FFFFFFF : (gxv < -54'sd2147483648) ? 32'sh80000000 : gxv[31:0];
            gy <= (gyv > 54'sd2147483647) ? 32'sh7FFFFFFF : (gyv < -54'sd2147483648) ? 32'sh80000000 : gyv[31:0];
            sx0 <= (bx0 <<< 4) + 24'sd8; sy0 <= (by0 <<< 4) + 24'sd8;
            st <= S_T5B;
        end
        S_T5B: begin                                       // sample-origin offsets
            for (i = 0; i < 3; i = i + 1) begin dsy[i] <= sy0[17:0] - eay[i]; dsx[i] <= sx0[17:0] - eax[i]; end
            dzx <= sx0[17:0] - x0; dzy <= sy0[17:0] - y0;
            st <= S_T6A;
        end
        S_T6A: begin
            for (i = 0; i < 3; i = i + 1) begin
                pe0[i] <= edx[i] * dsy[i];
                pe1[i] <= edy[i] * dsx[i];
                Ex[i] <= -(edy[i] * 48'sd16);
                Ey[i] <= edx[i] * 48'sd16;
            end
            pxh <= $signed(gx[31:16]) * dzx; pxl <= $signed({1'b0, gx[15:0]}) * dzx;
            pyh <= $signed(gy[31:16]) * dzy; pyl <= $signed({1'b0, gy[15:0]}) * dzy;
            zx <= gx * 64'sd16; zy <= gy * 64'sd16;
            st <= S_T6B;
        end
        S_T6B: begin
            for (i = 0; i < 3; i = i + 1) begin E[i] <= pe0[i] - pe1[i]; Erow[i] <= pe0[i] - pe1[i]; end
            pz0 <= ($signed({{28{pxh[35]}}, pxh}) <<< 16) + $signed({{28{pxl[35]}}, pxl});
            pz1 <= ($signed({{28{pyh[35]}}, pyh}) <<< 16) + $signed({{28{pyl[35]}}, pyl});
            st <= S_T6C;
        end
        S_T6C: begin pz0 <= pz0 + pz1; st <= S_T6D; end
        S_T6D: begin
            zq <= ($signed({48'd0, z0}) <<< 16) + pz0;
            zqrow <= ($signed({48'd0, z0}) <<< 16) + pz0;
            px <= bx0; py <= by0;
            lx <= bx0[4:0] - tile_x[4:0]; ly <= by0[4:0] - tile_y[4:0]; lx0 <= bx0[4:0] - tile_x[4:0];
            cnt_tris <= cnt_tris + 32'd1;
            st <= S_SCAN;
        end
        S_SCAN: begin
            // stage A: issue the Z read for this sample, carry the verdict to stage B
            b_v <= 1'b1; b_in <= in0 & in1 & in2; b_a <= cur_a; b_z <= zc;
            cnt_samples <= cnt_samples + 32'd1;
            if (px == bx1) begin
                if (py == by1) begin drain <= 2'd0; st <= S_DRAIN; end
                py <= py + 24'sd1; ly <= ly + 5'd1; px <= bx0; lx <= lx0;
                for (i = 0; i < 3; i = i + 1) begin Erow[i] <= Erow[i] + Ey[i]; E[i] <= Erow[i] + Ey[i]; end
                zqrow <= zqrow + zy; zq <= zqrow + zy;
            end else begin
                px <= px + 24'sd1; lx <= lx + 5'd1;
                for (i = 0; i < 3; i = i + 1) E[i] <= E[i] + Ex[i];
                zq <= zq + zx;
            end
        end
        S_DRAIN: begin                                       // let stage B finish before the next command
            drain <= drain + 2'd1;
            if (drain == 2'd3) st <= S_IDLE;
        end
        // ---- tile output: 'TI', tile_x, tile_y, 1024 colours, CRC-32 lo/hi ----
        S_OHDR: begin
            if (!out_valid || out_ready) begin
                out_valid <= 1'b1;
                out_data <= (oi == 11'd0) ? 16'h5449 : (oi == 11'd1) ? tile_x : tile_y;
                oi <= oi + 11'd1;
                if (oi == 11'd2) begin oi <= 11'd0; st <= S_ORD; end
            end
        end
        S_ORD: if (out_ready || !out_valid) begin out_valid <= 1'b0; cr_a <= oi[9:0]; st <= S_OWAIT; end
        S_OWAIT: st <= S_OWAIT2;
        S_OWAIT2: begin cr_qq <= cr_q; st <= S_OCOL; end      // EBR output registered before the CRC
        S_OCOL: begin
            out_valid <= 1'b1; out_data <= cr_qq;
            ocrc <= crc8(crc8(ocrc, cr_qq[7:0]), cr_qq[15:8]);
            oi <= oi + 11'd1;
            st <= (oi == 11'd1023) ? S_OCRC : S_ORD;
            if (oi == 11'd1023) oi <= 11'd0;
        end
        S_OCRC: if (out_ready) begin
            out_valid <= 1'b1;
            out_data <= (oi == 11'd0) ? ~ocrc[15:0] : ~ocrc[31:16];
            oi <= oi + 11'd1;
            if (oi == 11'd2) begin out_valid <= 1'b0; st <= S_IDLE; end
        end
        default: st <= S_IDLE;
        endcase
    end
endmodule
`default_nettype wire
