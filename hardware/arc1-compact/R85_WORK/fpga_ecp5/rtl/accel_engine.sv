// ARC-1 Compact R8.5 -- accelerator job engine (replaces the R06 transport loopback).
//
// Evidence level: RTL_SIMULATED (tb_ecp5_top) + open-toolchain routed build (Yosys/nextpnr-ecp5).
//
// Request buffer (REQ, written by the F133 through the AMBX mailbox):
//   * starts with "AJOB": a versioned job frame (little endian)
//       0  "AJOB"            4  version = 1      5  opcode (1 = TRANSFORM_BATCH)
//       6  count (u16)       8  seq (u32)        12 payload CRC32 over count*48 bytes
//      16  count x 48-byte R05 transform jobs (field order of R05_BASELINE/compute/CONTRACT.md)
//   * anything else: legacy R06 transport loopback (copied unchanged; keeps the
//     R05 golden-frame transport tests valid)
// Response buffer (RESP):
//       0  "ARES"            4  version = 1      5  status
//       6  count (u16)       8  seq (u32)        12 CRC32 over count*24 result bytes
//      16  count x 24-byte R05 results (tag, minx, miny, maxx, maxy, flags)
// status: 0 OK, 1 BAD_LENGTH, 2 BAD_VERSION, 3 BAD_OPCODE, 4 PAYLOAD_CRC, 5 ABORTED
// On any error the result count is 0 (no partial results are ever presented).
// The math is the unchanged R05 RTL (R05_BASELINE/compute/rtl/arc1_transform.sv).
module accel_engine (
    input  wire        clk,
    input  wire        rst,
    input  wire        abort,          // pulse: drop the current job, post ABORTED
    input  wire        job_valid,
    input  wire [15:0] job_len,
    output reg  [12:0] req_raddr,
    input  wire [7:0]  req_rdata,      // valid 2 clocks after req_raddr is set (mbx_regs registers it)
    output reg         resp_we,
    output reg  [12:0] resp_waddr,
    output reg  [7:0]  resp_wdata,
    output reg         resp_post,
    output reg  [15:0] resp_len,
    // performance / status (sys clock domain)
    output reg  [31:0] perf_last_cycles,
    output reg  [31:0] perf_jobs,
    output reg  [31:0] perf_items,
    output reg  [7:0]  last_status
);
    localparam integer MAXCOUNT = 170;            // (8192-16)/48
    localparam [7:0] S_OK = 8'd0, S_BADLEN = 8'd1, S_BADVER = 8'd2, S_BADOP = 8'd3, S_CRC = 8'd4, S_ABORT = 8'd5;

    // ---------------- CRC32 (IEEE, reflected) one byte per clock ----------------
    function automatic [31:0] crc8(input [31:0] c, input [7:0] d);
        integer k;
        reg [31:0] x;
        begin
            x = c ^ {24'd0, d};
            for (k = 0; k < 8; k = k + 1) x = x[0] ? (x >> 1) ^ 32'hEDB88320 : (x >> 1);
            crc8 = x;
        end
    endfunction

    // ---------------- R05 transform core ----------------
    reg         t_in_valid;
    wire        t_in_ready, t_out_valid;
    reg signed [31:0] f [0:9];
    reg  [15:0] vw, vh;
    reg  [31:0] jtag;
    wire signed [31:0] o_minx, o_miny, o_maxx, o_maxy;
    wire [2:0]  o_flags;
    wire [31:0] o_tag;
    arc1_transform u_xf (
        .clk(clk), .reset(rst | abort), .in_valid(t_in_valid), .in_ready(t_in_ready),
        .in_xmin(f[0]), .in_ymin(f[1]), .in_xmax(f[2]), .in_ymax(f[3]),
        .in_m00(f[4]), .in_m01(f[5]), .in_m02(f[6]), .in_m10(f[7]), .in_m11(f[8]), .in_m12(f[9]),
        .in_viewport_width(vw), .in_viewport_height(vh), .in_tag(jtag),
        .out_valid(t_out_valid), .out_ready(1'b1),
        .out_minx(o_minx), .out_miny(o_miny), .out_maxx(o_maxx), .out_maxy(o_maxy),
        .out_flags(o_flags), .out_tag(o_tag));

    // ---------------- byte stream reader (2-clock read latency) ----------------
    reg [15:0] rd_next, rd_end;     // next address to issue, exclusive end
    reg        rd_go;
    reg [1:0]  vpipe;               // valid pipeline matching the 2-clock latency
    wire       byte_v = vpipe[1];

    // ---------------- control ----------------
    localparam [3:0] E_IDLE = 0, E_HDR = 1, E_CHECK = 2, E_JOB = 3, E_XF = 4, E_RES = 5, E_FIN = 6,
                     E_HDRW = 7, E_LOOP = 8, E_POST = 9;
    reg [3:0]  st;
    reg [15:0] bidx;                // byte index inside the current unit
    reg [7:0]  hdr [0:15];
    reg [15:0] count, jidx;
    reg [31:0] seq, crc_in, crc_out, cycles;
    reg [7:0]  status;
    reg [191:0] res_sr;             // 24 result bytes, LSB first
    reg        legacy;
    integer i;

    wire [31:0] magic = {hdr[3], hdr[2], hdr[1], hdr[0]};

    always @(posedge clk) begin
        resp_we   <= 1'b0;
        resp_post <= 1'b0;
        t_in_valid <= 1'b0;
        vpipe <= {vpipe[0], 1'b0};
        if (rd_go) begin
            if (rd_next < rd_end) begin
                req_raddr <= rd_next[12:0];
                rd_next   <= rd_next + 16'd1;
                vpipe[0]  <= 1'b1;
            end else begin
                rd_go <= 1'b0;
            end
        end
        if (st != E_IDLE) cycles <= cycles + 32'd1;

        if (rst) begin
            st <= E_IDLE; rd_go <= 1'b0; vpipe <= 2'b00; cycles <= 32'd0;
            perf_last_cycles <= 32'd0; perf_jobs <= 32'd0; perf_items <= 32'd0; last_status <= 8'd0;
            resp_len <= 16'd0;
        end else if (abort && st != E_IDLE) begin
            status <= S_ABORT; count <= 16'd0; rd_go <= 1'b0; vpipe <= 2'b00;
            bidx <= 16'd0; st <= E_HDRW;
        end else begin
            case (st)
            E_IDLE: if (job_valid) begin
                cycles <= 32'd0; bidx <= 16'd0;
                rd_next <= 16'd0; rd_end <= (job_len < 16'd16) ? job_len : 16'd16; rd_go <= 1'b1;
                st <= E_HDR;
            end
            E_HDR: begin
                if (byte_v) begin
                    hdr[bidx[3:0]] <= req_rdata;
                    bidx <= bidx + 16'd1;
                end
                if (!rd_go && vpipe == 2'b00 && !byte_v) st <= E_CHECK;
            end
            E_CHECK: begin
                count <= {hdr[7], hdr[6]};
                seq   <= {hdr[11], hdr[10], hdr[9], hdr[8]};
                legacy <= (job_len < 16'd16) || (magic != 32'h424F4A41);          // "AJOB"
                crc_in <= 32'hFFFFFFFF; crc_out <= 32'hFFFFFFFF;
                jidx <= 16'd0; bidx <= 16'd0;
                if ((job_len < 16'd16) || (magic != 32'h424F4A41)) begin
                    rd_next <= 16'd0; rd_end <= job_len; rd_go <= 1'b1; st <= E_LOOP;
                end else if (hdr[4] != 8'd1) begin
                    status <= S_BADVER; count <= 16'd0; st <= E_HDRW;
                end else if (hdr[5] != 8'd1) begin
                    status <= S_BADOP; count <= 16'd0; st <= E_HDRW;
                end else if ({hdr[7], hdr[6]} == 16'd0 || {hdr[7], hdr[6]} > MAXCOUNT[15:0] ||
                             job_len != 16'd16 + {hdr[7], hdr[6]} * 16'd48) begin
                    status <= S_BADLEN; count <= 16'd0; st <= E_HDRW;
                end else begin
                    status <= S_OK; st <= E_JOB;
                    rd_next <= 16'd16; rd_end <= 16'd64; rd_go <= 1'b1;
                end
            end
            E_JOB: begin                                         // 48 job bytes -> fields
                if (byte_v) begin
                    crc_in <= crc8(crc_in, req_rdata);
                    if (bidx < 16'd40) f[bidx[5:2]] <= {req_rdata, f[bidx[5:2]][31:8]};
                    else if (bidx < 16'd42) vw <= {req_rdata, vw[15:8]};
                    else if (bidx < 16'd44) vh <= {req_rdata, vh[15:8]};
                    else jtag <= {req_rdata, jtag[31:8]};
                    bidx <= bidx + 16'd1;
                end
                if (!rd_go && vpipe == 2'b00 && !byte_v) begin t_in_valid <= 1'b1; st <= E_XF; end
            end
            E_XF: begin
                if (t_in_valid && !t_in_ready) t_in_valid <= 1'b1;   // hold until accepted
                if (t_out_valid) begin
                    res_sr <= {{29'd0, o_flags}, o_maxy, o_maxx, o_miny, o_minx, o_tag};
                    bidx <= 16'd0; st <= E_RES;
                end
            end
            E_RES: begin                                         // 24 result bytes
                resp_we <= 1'b1;
                resp_waddr <= 13'd16 + jidx[12:0] * 13'd24 + bidx[12:0];
                resp_wdata <= res_sr[7:0];
                crc_out <= crc8(crc_out, res_sr[7:0]);
                res_sr <= res_sr >> 8;
                bidx <= bidx + 16'd1;
                if (bidx == 16'd23) begin
                    jidx <= jidx + 16'd1;
                    bidx <= 16'd0;
                    if (jidx + 16'd1 == count) st <= E_FIN;
                    else begin
                        rd_next <= 16'd16 + (jidx + 16'd1) * 16'd48; rd_end <= 16'd16 + (jidx + 16'd2) * 16'd48;
                        rd_go <= 1'b1; st <= E_JOB;
                    end
                end
            end
            E_FIN: begin
                if (~crc_in != {hdr[15], hdr[14], hdr[13], hdr[12]}) begin
                    status <= S_CRC; count <= 16'd0;             // results already written are not presented
                end
                bidx <= 16'd0; st <= E_HDRW;
            end
            E_HDRW: begin                                        // response header
                resp_we <= 1'b1;
                resp_waddr <= bidx[12:0];
                case (bidx[3:0])
                4'd0: resp_wdata <= 8'h41;  4'd1: resp_wdata <= 8'h52;  4'd2: resp_wdata <= 8'h45;  4'd3: resp_wdata <= 8'h53;
                4'd4: resp_wdata <= 8'd1;   4'd5: resp_wdata <= status;
                4'd6: resp_wdata <= count[7:0]; 4'd7: resp_wdata <= count[15:8];
                4'd8: resp_wdata <= seq[7:0];   4'd9: resp_wdata <= seq[15:8];
                4'd10: resp_wdata <= seq[23:16]; 4'd11: resp_wdata <= seq[31:24];
                4'd12: resp_wdata <= (count != 0) ? ~crc_out[7:0]   : 8'h00;
                4'd13: resp_wdata <= (count != 0) ? ~crc_out[15:8]  : 8'h00;
                4'd14: resp_wdata <= (count != 0) ? ~crc_out[23:16] : 8'h00;
                default: resp_wdata <= (count != 0) ? ~crc_out[31:24] : 8'h00;
                endcase
                bidx <= bidx + 16'd1;
                if (bidx == 16'd15) begin
                    resp_len <= 16'd16 + count * 16'd24;
                    st <= E_POST;
                end
            end
            E_LOOP: begin                                        // legacy transport loopback
                if (byte_v) begin
                    resp_we <= 1'b1; resp_waddr <= bidx[12:0]; resp_wdata <= req_rdata; bidx <= bidx + 16'd1;
                end
                if (!rd_go && vpipe == 2'b00 && !byte_v) begin resp_len <= job_len; status <= S_OK; count <= 16'd0; st <= E_POST; end
            end
            E_POST: begin
                resp_post <= 1'b1;
                perf_last_cycles <= cycles;
                perf_jobs <= perf_jobs + 32'd1;
                perf_items <= perf_items + {16'd0, count};
                last_status <= status;
                st <= E_IDLE;
            end
            default: st <= E_IDLE;
            endcase
        end
    end
endmodule
