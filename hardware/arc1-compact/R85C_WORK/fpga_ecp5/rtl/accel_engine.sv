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
// status: 0 OK, 1 BAD_LENGTH, 2 BAD_VERSION, 3 BAD_OPCODE, 4 PAYLOAD_CRC, 5 ABORTED, 6 BAD_STATE
// R8.5-C opcodes (accel_fir.sv, state resident in the FPGA):
//   2 FIR_SET_IR : count = 1024 int16 Q15 taps (2 B each); response count 0
//   3 FIR_BLOCK  : count = 1..1024 int16 samples appended to the history; response count int16 outputs
//                  (BAD_STATE if no valid IR; on PAYLOAD_CRC the history write pointer is NOT advanced)
// On any error the result count is 0 (no partial results are ever presented).
// The math is the unchanged R05 RTL (R05_BASELINE/compute/rtl/arc1_transform.sv).
module accel_engine (
    input  wire        clk,
    input  wire        rst,
    input  wire        abort,          // pulse: drop the current job, post ABORTED
    input  wire        job_valid,
    input  wire [15:0] job_len,
    output reg  [12:0] req_raddr,
    input  wire [7:0]  req_rdata,      // valid 2 clocks after req_raddr is set; re-registered here (rdq)
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
    localparam [7:0] S_OK = 8'd0, S_BADLEN = 8'd1, S_BADVER = 8'd2, S_BADOP = 8'd3, S_CRC = 8'd4, S_ABORT = 8'd5,
                     S_BADSTATE = 8'd6;
    localparam integer FIRMAX = 1024;

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

    // ---------------- resident FIR engine (opcodes 2/3) ----------------
    reg         fir_ir_we, fir_x_we, fir_start, fir_pop;
    reg  [9:0]  fir_ir_waddr;
    reg  [10:0] fir_x_waddr, fir_wp;
    reg  [15:0] fir_wdata;
    wire        fir_busy, fir_avail;
    wire [15:0] fir_out;
    reg         ir_valid;
    accel_fir u_fir (
        .clk(clk), .rst(rst), .ir_we(fir_ir_we), .ir_waddr(fir_ir_waddr), .ir_wdata(fir_wdata),
        .x_we(fir_x_we), .x_waddr(fir_x_waddr), .x_wdata(fir_wdata),
        .start(fir_start), .base(fir_wp), .n(count[10:0]), .busy(fir_busy),
        .out_avail(fir_avail), .out_sample(fir_out), .out_pop(fir_pop), .abort(abort));

    // ---------------- byte stream reader (2-clock read latency) ----------------
    reg [15:0] rd_next, rd_end;     // next address to issue, exclusive end
    reg        rd_go;
    reg [2:0]  vpipe;               // valid pipeline: 2-clock RAM latency + 1 register (timing)
    wire       byte_v = vpipe[2];
    reg [7:0]  rdq;                 // registered read byte (breaks BRAM -> mux -> CRC path)
    always @(posedge clk) rdq <= req_rdata;

    // ---------------- control ----------------
    localparam [3:0] E_IDLE = 0, E_HDR = 1, E_CHECK = 2, E_JOB = 3, E_XF = 4, E_RES = 5, E_FIN = 6,
                     E_HDRW = 7, E_LOOP = 8, E_POST = 9, E_CHECK2 = 10, E_FIRLD = 11, E_FIRIN = 12,
                     E_FIRCHK = 13, E_FIROUT = 14;
    // No multipliers in the control path (R8.5 timing fix): lengths/addresses use shift-adds
    // and running bases, and the header check is split over two registered states.
    reg [15:0] len_expect, req_base;
    reg [12:0] res_base;
    reg        magic_ok, ver_ok, op_ok, cnt_ok;
    reg [3:0]  st;
    reg [15:0] bidx;                // byte index inside the current unit
    reg [7:0]  hdr [0:15];
    reg [15:0] count, jidx;
    reg [31:0] seq, crc_in, crc_out, cycles;
    reg [7:0]  status;
    reg [191:0] res_sr;             // 24 result bytes, LSB first
    reg [7:0]   opc;
    reg [7:0]   lo_byte;
    reg         hi_phase;
    reg        legacy;
    integer i;

    wire [31:0] magic = {hdr[3], hdr[2], hdr[1], hdr[0]};

    always @(posedge clk) begin
        resp_we   <= 1'b0;
        resp_post <= 1'b0;
        t_in_valid <= 1'b0;
        fir_ir_we <= 1'b0; fir_x_we <= 1'b0; fir_start <= 1'b0; fir_pop <= 1'b0;
        vpipe <= {vpipe[1:0], 1'b0};
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
            st <= E_IDLE; rd_go <= 1'b0; vpipe <= 3'b000; cycles <= 32'd0;
            perf_last_cycles <= 32'd0; perf_jobs <= 32'd0; perf_items <= 32'd0; last_status <= 8'd0;
            resp_len <= 16'd0; ir_valid <= 1'b0; fir_wp <= 11'd0;
        end else if (abort && st != E_IDLE) begin
            status <= S_ABORT; count <= 16'd0; rd_go <= 1'b0; vpipe <= 3'b000;
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
                    hdr[bidx[3:0]] <= rdq;
                    bidx <= bidx + 16'd1;
                end
                if (!rd_go && vpipe == 3'b000 && !byte_v) st <= E_CHECK;
            end
            E_CHECK: begin
                count <= {hdr[7], hdr[6]};
                seq   <= {hdr[11], hdr[10], hdr[9], hdr[8]};
                magic_ok <= (job_len >= 16'd16) && (magic == 32'h424F4A41);       // "AJOB"
                ver_ok <= hdr[4] == 8'd1;
                opc    <= hdr[5];
                op_ok  <= hdr[5] == 8'd1 || hdr[5] == 8'd2 || hdr[5] == 8'd3;
                cnt_ok <= (hdr[5] == 8'd1) ? ({hdr[7], hdr[6]} != 16'd0 && {hdr[7], hdr[6]} <= MAXCOUNT[15:0]) :
                          (hdr[5] == 8'd2) ? ({hdr[7], hdr[6]} == FIRMAX[15:0]) :
                                             ({hdr[7], hdr[6]} != 16'd0 && {hdr[7], hdr[6]} <= FIRMAX[15:0]);
                len_expect <= (hdr[5] == 8'd1) ? 16'd16 + ({hdr[7], hdr[6]} << 5) + ({hdr[7], hdr[6]} << 4)   // 16 + 48*count
                                               : 16'd16 + ({hdr[7], hdr[6]} << 1);                           // 16 + 2*count
                hi_phase <= 1'b0;
                crc_in <= 32'hFFFFFFFF; crc_out <= 32'hFFFFFFFF;
                jidx <= 16'd0; bidx <= 16'd0; req_base <= 16'd16; res_base <= 13'd16;
                st <= E_CHECK2;
            end
            E_CHECK2: begin
                legacy <= !magic_ok;
                if (!magic_ok) begin
                    rd_next <= 16'd0; rd_end <= job_len; rd_go <= 1'b1; st <= E_LOOP;
                end else if (!ver_ok) begin
                    status <= S_BADVER; count <= 16'd0; st <= E_HDRW;
                end else if (!op_ok) begin
                    status <= S_BADOP; count <= 16'd0; st <= E_HDRW;
                end else if (!cnt_ok || job_len != len_expect) begin
                    status <= S_BADLEN; count <= 16'd0; st <= E_HDRW;
                end else if (opc == 8'd1) begin
                    status <= S_OK; st <= E_JOB;
                    rd_next <= 16'd16; rd_end <= 16'd64; rd_go <= 1'b1;
                end else if (opc == 8'd3 && !ir_valid) begin
                    status <= S_BADSTATE; count <= 16'd0; st <= E_HDRW;
                end else begin
                    status <= S_OK; st <= (opc == 8'd2) ? E_FIRLD : E_FIRIN;
                    if (opc == 8'd2) ir_valid <= 1'b0;           // an interrupted IR load must never be used
                    rd_next <= 16'd16; rd_end <= job_len; rd_go <= 1'b1;
                end
            end
            E_JOB: begin                                         // 48 job bytes -> fields
                if (byte_v) begin
                    crc_in <= crc8(crc_in, rdq);
                    if (bidx < 16'd40) f[bidx[5:2]] <= {rdq, f[bidx[5:2]][31:8]};
                    else if (bidx < 16'd42) vw <= {rdq, vw[15:8]};
                    else if (bidx < 16'd44) vh <= {rdq, vh[15:8]};
                    else jtag <= {rdq, jtag[31:8]};
                    bidx <= bidx + 16'd1;
                end
                if (!rd_go && vpipe == 3'b000 && !byte_v) begin t_in_valid <= 1'b1; st <= E_XF; end
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
                resp_waddr <= res_base + bidx[12:0];
                resp_wdata <= res_sr[7:0];
                crc_out <= crc8(crc_out, res_sr[7:0]);
                res_sr <= res_sr >> 8;
                bidx <= bidx + 16'd1;
                if (bidx == 16'd23) begin
                    jidx <= jidx + 16'd1;
                    bidx <= 16'd0;
                    res_base <= res_base + 13'd24;
                    req_base <= req_base + 16'd48;
                    if (jidx + 16'd1 == count) st <= E_FIN;
                    else begin
                        rd_next <= req_base + 16'd48; rd_end <= req_base + 16'd96;
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
                    resp_len <= (opc == 8'd3) ? 16'd16 + (count << 1)                 // 16 + 2*count
                                              : 16'd16 + (count << 4) + (count << 3); // 16 + 24*count (0 for op 2)
                    st <= E_POST;
                end
            end
            E_FIRLD, E_FIRIN: begin                              // stream int16 payload into taps / history
                if (byte_v) begin
                    crc_in <= crc8(crc_in, rdq);
                    if (!hi_phase) lo_byte <= rdq;
                    else begin
                        fir_wdata <= {rdq, lo_byte};
                        if (st == E_FIRLD) begin fir_ir_we <= 1'b1; fir_ir_waddr <= bidx[9:0]; end
                        else begin fir_x_we <= 1'b1; fir_x_waddr <= fir_wp + bidx[10:0]; end
                        bidx <= bidx + 16'd1;
                    end
                    hi_phase <= ~hi_phase;
                end
                if (!rd_go && vpipe == 3'b000 && !byte_v) st <= E_FIRCHK;
            end
            E_FIRCHK: begin
                bidx <= 16'd0; hi_phase <= 1'b0;
                if (~crc_in != {hdr[15], hdr[14], hdr[13], hdr[12]}) begin
                    status <= S_CRC; count <= 16'd0; st <= E_HDRW;
                    if (opc == 8'd2) ir_valid <= 1'b0;            // a damaged IR is never used
                end else if (opc == 8'd2) begin
                    ir_valid <= 1'b1; count <= 16'd0; st <= E_HDRW;
                end else begin
                    fir_start <= 1'b1; st <= E_FIROUT;
                end
            end
            E_FIROUT: begin                                      // 2 response bytes per output sample
                if (fir_avail && !fir_pop) begin
                    resp_we <= 1'b1;
                    resp_waddr <= res_base + bidx[12:0];
                    resp_wdata <= hi_phase ? fir_out[15:8] : fir_out[7:0];
                    crc_out <= crc8(crc_out, hi_phase ? fir_out[15:8] : fir_out[7:0]);
                    bidx <= bidx + 16'd1;
                    if (hi_phase) fir_pop <= 1'b1;
                    hi_phase <= ~hi_phase;
                end
                if (bidx == {count[14:0], 1'b0}) begin               // all outputs written
                    fir_wp <= fir_wp + count[10:0];
                    bidx <= 16'd0; st <= E_HDRW;
                end
            end
            E_LOOP: begin                                        // legacy transport loopback
                if (byte_v) begin
                    resp_we <= 1'b1; resp_waddr <= bidx[12:0]; resp_wdata <= rdq; bidx <= bidx + 16'd1;
                end
                if (!rd_go && vpipe == 3'b000 && !byte_v) begin resp_len <= job_len; status <= S_OK; count <= 16'd0; st <= E_POST; end
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
