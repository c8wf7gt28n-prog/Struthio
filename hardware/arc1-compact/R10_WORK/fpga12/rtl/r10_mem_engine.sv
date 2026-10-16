// ARC-1 R10 (ARC1_MEMORY_R10 v0.1 s2.4) -- 12F job dispatcher with the 4 MiB QSPI PSRAM opcodes.
// Sits between eth_link and the unchanged accel_engine. Every request header is read first; AJOB opcodes 0x20..0x22
// are executed here, everything else (transform, STATUS, legacy loopback, bad opcodes) is handed to accel_engine,
// which re-reads the request from byte 0. Framing as accel_engine ("AJOB"/"ARES", LE, CRC-32 IEEE):
//   0x20 PSRAM_WRITE  count = n data bytes (1..4096); payload = addr u32 + n bytes; CRC over addr + data.
//                     The payload CRC is checked BEFORE any byte reaches the PSRAM. Response count 0.
//   0x21 PSRAM_READ   count = n bytes (1..4096); payload = addr u32. Response count n, the data, CRC over it.
//   0x22 PSRAM_BIST   count 0, no payload. Runs psram_bist (R8.5-C); response count 4 = error count u32 LE.
// The BIST is destructive over PSRAM bytes 0..16383 (64 blocks x 256 B at address 0).
//   status: 0 OK, 1 BAD_LENGTH, 2 BAD_VERSION, 4 PAYLOAD_CRC, 6 BAD_STATE (PSRAM not ready),
//           8 MEM_ERROR (controller rejected/timed out, or BIST failed), 9 RANGE (addr + n > MEM_BYTES)
// Transfers are split at 256-byte boundaries (controller buffer; never crosses a PSRAM page).
// Evidence: RTL_SIMULATED (tb_r10_support_mem with the R07 APS6404L protocol-checking model). Not on silicon.
`default_nettype none
module r10_mem_engine #(parameter integer MEM_BYTES = 4194304) (
    input  wire        clk,
    input  wire        rst,
    // from eth_link
    input  wire        job_valid,
    input  wire [15:0] job_len,
    output wire        idle,
    output wire [12:0] req_raddr,
    input  wire [7:0]  req_rdata,
    output wire        resp_we,
    output wire [12:0] resp_waddr,
    output wire [7:0]  resp_wdata,
    output wire        resp_post,
    output wire [15:0] resp_len,
    // to accel_engine
    output reg         a_job_valid,
    output reg  [15:0] a_job_len,
    input  wire        a_idle,
    input  wire [12:0] a_req_raddr,
    input  wire        a_resp_we,
    input  wire [12:0] a_resp_waddr,
    input  wire [7:0]  a_resp_wdata,
    input  wire        a_resp_post,
    input  wire [15:0] a_resp_len,
    // PSRAM user port (psram_user_port, uclk = clk) -- shared with the BIST
    output wire        p_req_valid,
    input  wire        p_req_ready,
    output wire        p_req_write,
    output wire [22:0] p_req_addr,
    output wire [8:0]  p_req_len,
    output wire        p_wr_valid,
    input  wire        p_wr_ready,
    output wire [7:0]  p_wr_data,
    input  wire        p_rd_valid,
    output wire        p_rd_ready,
    input  wire [7:0]  p_rd_data,
    input  wire        p_resp_valid,
    output wire        p_resp_ready,
    input  wire [2:0]  p_resp_status,
    input  wire        ram_ready,
    // counters
    output reg  [31:0] mem_jobs,
    output reg  [31:0] mem_bytes
);
    localparam [32:0] MEMB = 33'(MEM_BYTES);
    localparam [7:0] S_OK = 0, S_BADLEN = 1, S_BADVER = 2, S_CRC = 4, S_STATE = 6, S_MEM = 8, S_RANGE = 9;
    localparam [4:0] M_IDLE = 0, M_HDR = 1, M_CHK = 2, M_CRC = 3, M_CRCCHK = 4, M_FWD = 5, M_WREQ = 6, M_WRD = 7,
                     M_WDAT = 8, M_WRSP = 9, M_RREQ = 10, M_RDAT = 11, M_RRSP = 12, M_BIST = 13, M_BWAIT = 14,
                     M_HDRW = 15, M_POST = 16, M_NEXT = 17;
    reg [4:0] st;
    wire fwd = (st == M_FWD);
    assign idle = (st == M_IDLE) && a_idle;

    function automatic [31:0] crc8(input [31:0] c, input [7:0] d);
        integer k;
        reg [31:0] x;
        begin
            x = c ^ {24'd0, d};
            for (k = 0; k < 8; k = k + 1) x = x[0] ? (x >> 1) ^ 32'hEDB88320 : (x >> 1);
            crc8 = x;
        end
    endfunction

    // ---- 3-clock byte reader (address registered here, data registered in eth_link) ----
    reg [12:0] m_raddr;
    reg [1:0]  rph;
    reg        rgo, rdone;
    reg [7:0]  rbyte;
    always @(posedge clk) begin
        rdone <= 1'b0;
        if (rst) rph <= 2'd0;
        else if (rgo && rph == 2'd0) rph <= 2'd1;
        else if (rph == 2'd1) rph <= 2'd2;
        else if (rph == 2'd2) begin rph <= 2'd0; rdone <= 1'b1; rbyte <= req_rdata; end
    end

    reg         m_we, m_post;
    reg  [12:0] m_waddr;
    reg  [7:0]  m_wdata;
    reg  [15:0] m_len;
    assign req_raddr  = fwd ? a_req_raddr : m_raddr;
    assign resp_we    = fwd ? a_resp_we   : m_we;
    assign resp_waddr = fwd ? a_resp_waddr : m_waddr;
    assign resp_wdata = fwd ? a_resp_wdata : m_wdata;
    assign resp_post  = fwd ? a_resp_post : m_post;
    assign resp_len   = fwd ? a_resp_len  : m_len;

    // ---- PSRAM port: engine or BIST ----
    reg         bist_own, bist_start;
    wire        b_req_valid, b_req_write, b_wr_valid, b_rd_ready, b_resp_ready, b_busy, b_pass, b_fail;
    wire [22:0] b_req_addr;
    wire [8:0]  b_req_len;
    wire [7:0]  b_wr_data;
    wire [31:0] b_errs;
    psram_bist #(.BLOCKS(64)) u_bist (
        .clk(clk), .rst(rst), .start(bist_start), .busy(b_busy), .pass(b_pass), .fail(b_fail), .errs(b_errs),
        .req_valid(b_req_valid), .req_ready(p_req_ready & bist_own), .req_write(b_req_write),
        .req_addr(b_req_addr), .req_len(b_req_len),
        .wr_valid(b_wr_valid), .wr_ready(p_wr_ready & bist_own), .wr_data(b_wr_data),
        .rd_valid(p_rd_valid & bist_own), .rd_ready(b_rd_ready), .rd_data(p_rd_data),
        .resp_valid(p_resp_valid & bist_own), .resp_ready(b_resp_ready), .resp_status(p_resp_status));
    reg         e_req_valid, e_req_write, e_wr_valid, e_rd_ready, e_resp_ready;
    reg  [22:0] e_req_addr;
    reg  [8:0]  e_req_len;
    reg  [7:0]  e_wr_data;
    assign p_req_valid  = bist_own ? b_req_valid  : e_req_valid;
    assign p_req_write  = bist_own ? b_req_write  : e_req_write;
    assign p_req_addr   = bist_own ? b_req_addr   : e_req_addr;
    assign p_req_len    = bist_own ? b_req_len    : e_req_len;
    assign p_wr_valid   = bist_own ? b_wr_valid   : e_wr_valid;
    assign p_wr_data    = bist_own ? b_wr_data    : e_wr_data;
    assign p_rd_ready   = bist_own ? b_rd_ready   : e_rd_ready;
    assign p_resp_ready = bist_own ? b_resp_ready : e_resp_ready;

    reg [7:0]   hdr [0:15];
    reg [7:0]   opc, status;
    reg [15:0]  bi, n, rem, off, clen, cpos;
    reg [31:0]  seq, crc_in, crc_out, addr, errs_q;
    reg         bstarted;
    wire [8:0]  room = 9'd256 - {1'b0, addr[7:0]};

    always @(posedge clk) begin
        m_we <= 1'b0; m_post <= 1'b0; rgo <= 1'b0; a_job_valid <= 1'b0; bist_start <= 1'b0;
        if (rst) begin
            st <= M_IDLE; bist_own <= 1'b0; e_req_valid <= 1'b0; e_wr_valid <= 1'b0; e_rd_ready <= 1'b0;
            e_resp_ready <= 1'b0; mem_jobs <= 32'd0; mem_bytes <= 32'd0;
        end else case (st)
        M_IDLE: if (job_valid) begin
            a_job_len <= job_len; bi <= 16'd0;
            if (job_len < 16'd16) begin a_job_valid <= 1'b1; st <= M_FWD; end   // legacy loopback: accel_engine
            else begin m_raddr <= 13'd0; rgo <= 1'b1; st <= M_HDR; end
        end
        M_HDR: if (rdone) begin
            hdr[bi[3:0]] <= rbyte;
            bi <= bi + 16'd1;
            if (bi == 16'd15) st <= M_CHK;
            else begin m_raddr <= bi[12:0] + 13'd1; rgo <= 1'b1; end
        end
        M_CHK: begin
            opc <= hdr[5]; n <= {hdr[7], hdr[6]}; seq <= {hdr[11], hdr[10], hdr[9], hdr[8]};
            crc_in <= 32'hFFFFFFFF; crc_out <= 32'hFFFFFFFF; bi <= 16'd0; off <= 16'd0; errs_q <= 32'd0;
            if ({hdr[3], hdr[2], hdr[1], hdr[0]} != 32'h424F4A41 || hdr[5] < 8'h20 || hdr[5] > 8'h22) begin
                a_job_valid <= 1'b1; st <= M_FWD;                                   // not ours
            end else if (hdr[4] != 8'd1) begin status <= S_BADVER; n <= 16'd0; st <= M_HDRW; end
            else if ((hdr[5] == 8'h22) ? ({hdr[7], hdr[6]} != 16'd0 || job_len != 16'd16) :
                     ({hdr[7], hdr[6]} == 16'd0 || {hdr[7], hdr[6]} > 16'd4096 ||
                      job_len != (hdr[5] == 8'h20 ? 16'd20 + {hdr[7], hdr[6]} : 16'd20))) begin
                status <= S_BADLEN; n <= 16'd0; st <= M_HDRW;
            end else if (!ram_ready) begin status <= S_STATE; n <= 16'd0; st <= M_HDRW; end
            else if (hdr[5] == 8'h22) st <= M_BIST;
            else begin m_raddr <= 13'd16; rgo <= 1'b1; st <= M_CRC; end
        end
        M_CRC: if (rdone) begin                          // payload CRC (and the address) before touching the PSRAM
            crc_in <= crc8(crc_in, rbyte);
            if (bi < 16'd4) addr <= {rbyte, addr[31:8]};
            bi <= bi + 16'd1;
            if (bi + 16'd1 == job_len - 16'd16) st <= M_CRCCHK;
            else begin m_raddr <= 13'd17 + bi[12:0]; rgo <= 1'b1; end
        end
        M_CRCCHK: begin
            rem <= n;
            if (~crc_in != {hdr[15], hdr[14], hdr[13], hdr[12]}) begin status <= S_CRC; n <= 16'd0; st <= M_HDRW; end
            else if ({1'b0, addr} + {17'd0, n} > MEMB) begin status <= S_RANGE; n <= 16'd0; st <= M_HDRW; end
            else st <= (opc == 8'h20) ? M_WREQ : M_RREQ;
        end
        // ---------------- write: chunks of up to 256 bytes, never across a 256-byte boundary ----------------
        M_WREQ: begin
            clen <= ({7'd0, room} < rem) ? {7'd0, room} : rem;
            e_req_valid <= 1'b1; e_req_write <= 1'b1; e_req_addr <= addr[22:0];
            e_req_len <= ({7'd0, room} < rem) ? room : rem[8:0];
            cpos <= 16'd0;
            if (e_req_valid && p_req_ready) begin
                e_req_valid <= 1'b0; e_resp_ready <= 1'b1;
                m_raddr <= 13'd20 + off[12:0]; rgo <= 1'b1; st <= M_WRD;
            end
        end
        M_WRD: if (p_resp_valid) begin e_resp_ready <= 1'b0; status <= S_MEM; n <= 16'd0; st <= M_HDRW; end
               else if (rdone) begin e_wr_data <= rbyte; e_wr_valid <= 1'b1; st <= M_WDAT; end
        M_WDAT: if (p_resp_valid) begin e_wr_valid <= 1'b0; e_resp_ready <= 1'b0; status <= S_MEM; n <= 16'd0; st <= M_HDRW; end
               else if (p_wr_ready) begin
                   e_wr_valid <= 1'b0; cpos <= cpos + 16'd1;
                   if (cpos + 16'd1 == clen) st <= M_WRSP;
                   else begin m_raddr <= 13'd21 + off[12:0] + cpos[12:0]; rgo <= 1'b1; st <= M_WRD; end
               end
        M_WRSP: if (p_resp_valid) begin
            e_resp_ready <= 1'b0;
            if (p_resp_status != 3'd0) begin status <= S_MEM; n <= 16'd0; st <= M_HDRW; end
            else st <= M_NEXT;
        end
        // ---------------- read ----------------
        M_RREQ: begin
            clen <= ({7'd0, room} < rem) ? {7'd0, room} : rem;
            e_req_valid <= 1'b1; e_req_write <= 1'b0; e_req_addr <= addr[22:0];
            e_req_len <= ({7'd0, room} < rem) ? room : rem[8:0];
            cpos <= 16'd0;
            if (e_req_valid && p_req_ready) begin
                e_req_valid <= 1'b0; e_rd_ready <= 1'b1; e_resp_ready <= 1'b1; st <= M_RDAT;
            end
        end
        M_RDAT: begin
            if (p_rd_valid) begin
                m_we <= 1'b1; m_waddr <= 13'd16 + off[12:0] + cpos[12:0]; m_wdata <= p_rd_data;
                crc_out <= crc8(crc_out, p_rd_data);
                cpos <= cpos + 16'd1;
                if (cpos + 16'd1 == clen) begin e_rd_ready <= 1'b0; st <= M_RRSP; end
            end
            if (p_resp_valid) begin e_rd_ready <= 1'b0; e_resp_ready <= 1'b0; status <= S_MEM; n <= 16'd0; st <= M_HDRW; end
        end
        M_RRSP: if (p_resp_valid) begin
            e_resp_ready <= 1'b0;
            if (p_resp_status != 3'd0) begin status <= S_MEM; n <= 16'd0; st <= M_HDRW; end
            else st <= M_NEXT;
        end
        M_NEXT: begin
            addr <= addr + {16'd0, clen}; off <= off + clen; rem <= rem - clen;
            mem_bytes <= mem_bytes + {16'd0, clen};
            if (rem == clen) begin status <= S_OK; if (opc == 8'h20) n <= 16'd0; st <= M_HDRW; end
            else st <= (opc == 8'h20) ? M_WREQ : M_RREQ;
        end
        // ---------------- BIST ----------------
        M_BIST: begin bist_own <= 1'b1; bist_start <= 1'b1; bstarted <= 1'b0; st <= M_BWAIT; end
        M_BWAIT: begin
            if (b_busy) bstarted <= 1'b1;
            if (bstarted && !b_busy) begin
                bist_own <= 1'b0; errs_q <= b_errs; status <= (b_pass && !b_fail) ? S_OK : S_MEM; n <= 16'd4;
                bi <= 16'd0; st <= M_HDRW;
                // the 4 result bytes are written by M_HDRW (bi 16..19)
            end
        end
        // ---------------- response header (+ BIST result) ----------------
        M_HDRW: begin
            m_we <= 1'b1; m_waddr <= bi[12:0];
            case (bi[4:0])
            5'd0: m_wdata <= 8'h41;  5'd1: m_wdata <= 8'h52;  5'd2: m_wdata <= 8'h45;  5'd3: m_wdata <= 8'h53;
            5'd4: m_wdata <= 8'd1;   5'd5: m_wdata <= status;
            5'd6: m_wdata <= n[7:0]; 5'd7: m_wdata <= n[15:8];
            5'd8: m_wdata <= seq[7:0];   5'd9: m_wdata <= seq[15:8];  5'd10: m_wdata <= seq[23:16]; 5'd11: m_wdata <= seq[31:24];
            5'd12: m_wdata <= n != 0 ? ~crc_out[7:0]   : 8'h00;
            5'd13: m_wdata <= n != 0 ? ~crc_out[15:8]  : 8'h00;
            5'd14: m_wdata <= n != 0 ? ~crc_out[23:16] : 8'h00;
            5'd15: m_wdata <= n != 0 ? ~crc_out[31:24] : 8'h00;
            5'd16: m_wdata <= errs_q[7:0];  5'd17: m_wdata <= errs_q[15:8];
            5'd18: m_wdata <= errs_q[23:16]; default: m_wdata <= errs_q[31:24];
            endcase
            // BIST: CRC over the 4 result bytes, computed before the header bytes 12..15 are written
            if (opc == 8'h22 && bi == 16'd0)
                crc_out <= crc8(crc8(crc8(crc8(32'hFFFFFFFF, errs_q[7:0]), errs_q[15:8]), errs_q[23:16]), errs_q[31:24]);
            bi <= bi + 16'd1;
            if (bi == ((opc == 8'h22 && n == 16'd4) ? 16'd19 : 16'd15)) begin m_len <= 16'd16 + n; st <= M_POST; end
        end
        M_POST: begin m_post <= 1'b1; mem_jobs <= mem_jobs + 32'd1; st <= M_IDLE; end
        M_FWD: if (a_resp_post) st <= M_IDLE;            // resp_post is forwarded combinationally
        default: st <= M_IDLE;
        endcase
    end
endmodule
`default_nettype wire
