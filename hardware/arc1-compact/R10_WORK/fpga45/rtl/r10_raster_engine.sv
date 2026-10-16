// ARC-1 R10 -- 45F job engine for the D213 GMAC0 RGMII link (decision D1): RJOB/RRES frames around the tile
// rasterizer. Same request/response buffer interface as R8.5-C accel_engine, so it plugs into eth_link unchanged.
//   Request:  0 "RJOB" | 4 version 1 | 5 opcode | 6 count (u16, words) | 8 seq (u32) | 12 CRC-32 of the payload bytes |
//             16 payload: count x u16 LE raster job words (fpga45/tools/raster_ref.c format)
//             opcode 1 RASTER (1 <= count <= 4088), opcode 0x10 STATUS (count 0),
//             opcode 2 RASTER_HALF0 / 3 RASTER_HALF1: like RASTER but the job must produce exactly one tile (one
//             TILE_END); HALF0 returns output words 0..514 ('TI', x, y, rows 0-15), HALF1 words 515..1028 (rows 16-31,
//             CRC lo/hi). The tile buffers persist, so HALF1 is normally sent with the single job word TILE_END (0x0003)
//             to re-emit the tile drawn by HALF0. Each half fits a standard 1518-byte Ethernet frame (1068 bytes with
//             header and FCS); a full tile (opcode 1) needs a 2092-byte jumbo frame.
//   Response: 0 "RRES" | 4 version 1 | 5 status | 6 count (output words) | 8 seq | 12 CRC-32 of the output bytes |
//             16 output words (u16 LE); STATUS: 32 bytes ("R10G", rev, caps, 6 RGMII counters, tris, samples, written)
//   status: 0 OK, 1 BAD_LENGTH, 2 BAD_VERSION, 3 BAD_OPCODE, 4 PAYLOAD_CRC (nothing reaches the rasterizer),
//           5 TRUNCATED_COMMAND (the job ended inside a command; that command is dropped, earlier ones stand),
//           7 OUTPUT_OVERFLOW (opcode 1: more than 4088 output words, send at most one TILE_END per request;
//             opcodes 2/3: the job did not produce exactly one tile)
//   Any request not starting with "RJOB" is looped back unchanged (link calibration, eth_link.c el_calibrate).
// The payload CRC is checked in a first pass before any word is given to the rasterizer (tile state is never touched
// by a corrupted frame). Simple byte reader: 3 clocks per byte (not optimised).
// Evidence: RTL_SIMULATED (tb_r10_45f). Not on silicon.
`default_nettype none
module r10_raster_engine #(parameter [15:0] IF_REV = 16'h0001) (
    input  wire        clk,
    input  wire        rst,
    input  wire        job_valid,
    input  wire [15:0] job_len,
    output wire        idle,
    output reg  [12:0] req_raddr,
    input  wire [7:0]  req_rdata,        // valid 2 clocks after req_raddr is set
    output reg         resp_we,
    output reg  [12:0] resp_waddr,
    output reg  [7:0]  resp_wdata,
    output reg         resp_post,
    output reg  [15:0] resp_len,
    input  wire [95:0] eth_counters,
    output reg  [31:0] perf_jobs
);
    localparam [7:0] S_OK = 0, S_BADLEN = 1, S_BADVER = 2, S_BADOP = 3, S_CRC = 4, S_TRUNC = 5, S_OVF = 7;
    localparam integer MAXW = 4088;
    localparam [15:0] TILE_W = 16'd1029, HALF_W = 16'd515;
    localparam [3:0] E_IDLE = 0, E_HDR = 1, E_CHK = 2, E_CRC = 3, E_FEED = 4, E_WAIT = 5, E_HDRW = 6, E_POST = 7,
                     E_LOOP = 8, E_STAT = 9, E_CRCCHK = 10;
    reg [3:0] st;
    assign idle = (st == E_IDLE);

    function automatic [31:0] crc8(input [31:0] c, input [7:0] d);
        integer k;
        reg [31:0] x;
        begin
            x = c ^ {24'd0, d};
            for (k = 0; k < 8; k = k + 1) x = x[0] ? (x >> 1) ^ 32'hEDB88320 : (x >> 1);
            crc8 = x;
        end
    endfunction

    // ---- 3-clock byte reader ----
    reg [1:0]  rph;               // 0 idle, 1..2 waiting
    reg        rgo, rdone;
    reg [7:0]  rbyte;
    always @(posedge clk) begin
        rdone <= 1'b0;
        if (rst) rph <= 2'd0;
        else if (rgo && rph == 2'd0) rph <= 2'd1;
        else if (rph == 2'd1) rph <= 2'd2;
        else if (rph == 2'd2) begin rph <= 2'd0; rdone <= 1'b1; rbyte <= req_rdata; end
    end

    // ---- rasterizer ----
    reg         r_in_valid, r_abort;
    reg  [15:0] r_in_data;
    wire        r_in_ready, r_out_valid, r_busy;
    reg         hi_phase;
    wire        r_out_ready = !hi_phase;            // byte-wide response buffer: one word every 2 clocks
    wire        r_take = r_out_valid && r_out_ready;
    wire [15:0] r_out_data;
    wire [31:0] c_tris, c_samples, c_written, c_busy, c_bad;
    r10_raster u_r (.clk(clk), .rst(rst), .in_valid(r_in_valid), .abort(r_abort), .in_data(r_in_data), .in_ready(r_in_ready),
        .out_valid(r_out_valid), .out_data(r_out_data), .out_ready(r_out_ready), .busy(r_busy),
        .cnt_tris(c_tris), .cnt_samples(c_samples), .cnt_written(c_written), .cnt_busy_cycles(c_busy), .cnt_bad_cmd(c_bad));

    reg [7:0]   hdr [0:15];
    reg [15:0]  bi, count, nout, nw, wbase, wlim;
    reg         in_win;                              // = wbase <= nout < wlim, kept registered
    reg [31:0]  seq, crc_in, crc_out;
    reg [7:0]   status, opc;
    reg [7:0]   lo;
    reg         ovf, trunc;
    reg [255:0] ssr;
    wire [15:0] caps = 16'h0001;                     // b0 flat-triangle tile rasterizer (R10 7.1 steps 2-3)
    wire [255:0] status_words = {c_written, c_samples, c_tris, eth_counters, caps, IF_REV, 8'h47, 8'h30, 8'h31, 8'h52};

    // output words of the rasterizer are written straight into the response buffer
    always @(posedge clk) begin
        resp_we <= 1'b0; resp_post <= 1'b0; rgo <= 1'b0; r_abort <= 1'b0;
        if (r_take) begin
            if (in_win) begin
                resp_we <= 1'b1; resp_waddr <= 13'd16 + {nw[11:0], 1'b0}; resp_wdata <= r_out_data[7:0];
                lo <= r_out_data[15:8];
                hi_phase <= 1'b1;
                crc_out <= crc8(crc8(crc_out, r_out_data[7:0]), r_out_data[15:8]);
                nw <= nw + 16'd1;
            end else if (opc == 8'd1) ovf <= 1'b1;
            nout <= nout + 16'd1;
            in_win <= (nout + 16'd1 >= wbase) && (nout + 16'd1 < wlim);
        end else if (hi_phase) begin                    // second byte of the word, next clock
            resp_we <= 1'b1; resp_waddr <= 13'd17 + {nw[11:0] - 12'd1, 1'b0}; resp_wdata <= lo;
            hi_phase <= 1'b0;
        end
        if (r_in_valid && r_in_ready) r_in_valid <= 1'b0;
        if (rst) begin
            st <= E_IDLE; perf_jobs <= 32'd0; r_in_valid <= 1'b0; hi_phase <= 1'b0;
        end else case (st)
        E_IDLE: if (job_valid) begin
            bi <= 16'd0; req_raddr <= 13'd0; rgo <= 1'b1;
            if (job_len < 16'd16) begin bi <= 16'd0; st <= E_LOOP; end else st <= E_HDR;
        end
        E_HDR: if (rdone) begin
            hdr[bi[3:0]] <= rbyte;
            bi <= bi + 16'd1;
            if (bi == 16'd15) st <= E_CHK;
            else begin req_raddr <= bi[12:0] + 13'd1; rgo <= 1'b1; end
        end
        E_CHK: begin
            count <= {hdr[7], hdr[6]}; seq <= {hdr[11], hdr[10], hdr[9], hdr[8]}; opc <= hdr[5];
            nout <= 16'd0; nw <= 16'd0; ovf <= 1'b0; trunc <= 1'b0;
            wbase <= hdr[5] == 8'd3 ? HALF_W : 16'd0;
            wlim  <= hdr[5] == 8'd2 ? HALF_W : hdr[5] == 8'd3 ? TILE_W : MAXW[15:0];
            in_win <= hdr[5] != 8'd3; crc_in <= 32'hFFFFFFFF; crc_out <= 32'hFFFFFFFF; bi <= 16'd0;
            if ({hdr[3], hdr[2], hdr[1], hdr[0]} != 32'h424F4A52) begin              // not "RJOB": loop back
                req_raddr <= 13'd0; rgo <= 1'b1; st <= E_LOOP;
            end else if (hdr[4] != 8'd1) begin status <= S_BADVER; count <= 16'd0; st <= E_HDRW; end
            else if (hdr[5] == 8'h10) begin
                if ({hdr[7], hdr[6]} != 16'd0 || job_len != 16'd16) begin status <= S_BADLEN; count <= 16'd0; st <= E_HDRW; end
                else begin status <= S_OK; ssr <= status_words; st <= E_STAT; end
            end else if (hdr[5] != 8'd1 && hdr[5] != 8'd2 && hdr[5] != 8'd3) begin status <= S_BADOP; count <= 16'd0; st <= E_HDRW; end
            else if ({hdr[7], hdr[6]} == 16'd0 || {hdr[7], hdr[6]} > MAXW[15:0] ||
                     job_len != 16'd16 + {hdr[7][6:0], hdr[6], 1'b0}) begin
                status <= S_BADLEN; count <= 16'd0; st <= E_HDRW;
            end else begin req_raddr <= 13'd16; rgo <= 1'b1; st <= E_CRC; end
        end
        E_CRC: if (rdone) begin                          // pass 1: payload CRC only
            crc_in <= crc8(crc_in, rbyte);
            bi <= bi + 16'd1;
            if (bi == {count[14:0], 1'b0} - 16'd1) st <= E_CRCCHK;
            else begin req_raddr <= 13'd17 + bi[12:0]; rgo <= 1'b1; end
        end
        E_CRCCHK: begin
            bi <= 16'd0;
            if (~crc_in != {hdr[15], hdr[14], hdr[13], hdr[12]}) begin status <= S_CRC; count <= 16'd0; st <= E_HDRW; end
            else st <= E_FEED;
        end
        E_FEED: begin                                    // pass 2: words into the rasterizer
            if (!r_in_valid && rph == 2'd0 && !rdone && !rgo) begin
                if (bi == {count[14:0], 1'b0}) st <= E_WAIT;
                else begin req_raddr <= 13'd16 + bi[12:0]; rgo <= 1'b1; end
            end
            if (rdone) begin
                if (!bi[0]) begin lo <= rbyte; bi <= bi + 16'd1; end
                else begin r_in_valid <= 1'b1; r_in_data <= {rbyte, lo}; bi <= bi + 16'd1; end
            end
        end
        E_WAIT: if (r_busy && r_in_ready && !r_in_valid && !r_abort) begin    // waiting for arguments: truncated
            r_abort <= 1'b1; trunc <= 1'b1;
        end else if (!r_busy && !r_in_valid && !r_out_valid && !hi_phase) begin
            status <= trunc ? S_TRUNC : (ovf || (opc != 8'd1 && nout != TILE_W)) ? S_OVF : S_OK;
            count <= (trunc || ovf || (opc != 8'd1 && nout != TILE_W)) ? 16'd0 : nw;
            bi <= 16'd0; st <= E_HDRW;
        end
        E_STAT: if (!hi_phase) begin
            resp_we <= 1'b1; resp_waddr <= 13'd16 + bi[12:0]; resp_wdata <= ssr[7:0];
            crc_out <= crc8(crc_out, ssr[7:0]); ssr <= {8'd0, ssr[255:8]};
            bi <= bi + 16'd1;
            if (bi == 16'd31) begin bi <= 16'd0; count <= 16'd0; nout <= 16'd16; st <= E_HDRW; end
        end
        E_HDRW: if (!hi_phase) begin
            resp_we <= 1'b1; resp_waddr <= bi[12:0];
            case (bi[3:0])
            4'd0: resp_wdata <= 8'h52;  4'd1: resp_wdata <= 8'h52;  4'd2: resp_wdata <= 8'h45;  4'd3: resp_wdata <= 8'h53;
            4'd4: resp_wdata <= 8'd1;   4'd5: resp_wdata <= status;
            4'd6: resp_wdata <= count[7:0]; 4'd7: resp_wdata <= count[15:8];
            4'd8: resp_wdata <= seq[7:0];   4'd9: resp_wdata <= seq[15:8];
            4'd10: resp_wdata <= seq[23:16]; 4'd11: resp_wdata <= seq[31:24];
            4'd12: resp_wdata <= (count != 0 || opc == 8'h10) && status == S_OK ? ~crc_out[7:0]   : 8'h00;
            4'd13: resp_wdata <= (count != 0 || opc == 8'h10) && status == S_OK ? ~crc_out[15:8]  : 8'h00;
            4'd14: resp_wdata <= (count != 0 || opc == 8'h10) && status == S_OK ? ~crc_out[23:16] : 8'h00;
            default: resp_wdata <= (count != 0 || opc == 8'h10) && status == S_OK ? ~crc_out[31:24] : 8'h00;
            endcase
            bi <= bi + 16'd1;
            if (bi == 16'd15) begin
                resp_len <= (opc == 8'h10 && status == S_OK) ? 16'd48 : 16'd16 + {count[14:0], 1'b0};
                st <= E_POST;
            end
        end
        E_LOOP: begin                                    // legacy loopback: copy job_len bytes
            if (rdone) begin
                resp_we <= 1'b1; resp_waddr <= bi[12:0]; resp_wdata <= rbyte;
                bi <= bi + 16'd1;
                if (bi + 16'd1 == job_len) begin resp_len <= job_len; st <= E_POST; end
                else begin req_raddr <= bi[12:0] + 13'd1; rgo <= 1'b1; end
            end
        end
        E_POST: begin resp_post <= 1'b1; perf_jobs <= perf_jobs + 32'd1; st <= E_IDLE; end
        default: st <= E_IDLE;
        endcase
    end
    wire unused_ok = &{1'b0, c_busy, c_bad};
endmodule
`default_nettype wire
