// ARC-1 Compact R06 -- user-clock front end for psram_qspi_core.
//
// Evidence level: RTL_SIMULATED only.
//
// Clock-domain crossing scheme (uclk <-> mclk), chosen for verifiability:
//   * Buffer ownership handshake. The user side owns wbuf/rbuf and the request
//     descriptor while req_tgl == ack (in sync). It fills wbuf, freezes the
//     descriptor, then flips req_tgl. The memory side synchronises req_tgl
//     (2 FF), copies the frozen descriptor, executes, writes rbuf and the
//     status register, then sets ack := req level. The user side synchronises
//     ack (2 FF) before it reads status/rbuf. Multi-bit data never crosses
//     while its writer may change it.
//   * Memory-side reset adopts the current synchronised req level instead of 0,
//     so a stale descriptor can never replay as a new request after reset.
//   * The user side times out (UTIMEOUT cycles) and reports ST_TIMEOUT. It then
//     refuses new work (ST_NOT_READY) until the domains are in sync again; a
//     late completion is drained and discarded.
//   * Reset policy: urst must also reset the memory side (system reset). A
//     memory-side-only reset (mrst) is supported and tested.
//
// Request protocol (uclk):
//   req_valid/req_ready, req_write, req_addr[22:0], req_len (1..BUF_BYTES).
//   After acceptance EITHER a response arrives without consuming data
//   (rejected: NOT_READY / INVALID) OR, for a write, wr_ready accepts exactly
//   req_len bytes first. Reads with status OK stream req_len bytes on
//   rd_valid/rd_ready before the response. Exactly one response per request.

module psram_user_port #(
    parameter integer MCLK_HZ    = 40000000,
    parameter integer CLK_DIV    = 1,
    parameter integer BUF_BYTES  = 256,
    parameter integer TCEM_NS    = 8000,
    parameter integer UTIMEOUT   = 65536      // uclk cycles
) (
    // ---------------- user domain ----------------
    input  wire                           uclk,
    input  wire                           urst,
    input  wire                           req_valid,
    output wire                           req_ready,
    input  wire                           req_write,
    input  wire [22:0]                    req_addr,
    input  wire [$clog2(BUF_BYTES+1)-1:0] req_len,
    input  wire                           wr_valid,
    output wire                           wr_ready,
    input  wire [7:0]                     wr_data,
    output wire                           rd_valid,
    input  wire                           rd_ready,
    output wire [7:0]                     rd_data,
    output reg                            resp_valid,
    input  wire                           resp_ready,
    output reg  [2:0]                     resp_status,
    input  wire                           recover,      // pulse: rerun PSRAM init
    output wire                           ram_ready,
    output wire                           ram_error,
    output wire [1:0]                     ram_err_code,
    // ---------------- memory domain ----------------
    input  wire                           mclk,
    input  wire                           mrst,         // includes urst at system level
    input  wire                           dbg_freeze,
    output wire                           psram_ce_n,
    output wire                           psram_sclk,
    output wire [3:0]                     psram_dq_o,
    output wire [3:0]                     psram_dq_oe,
    input  wire [3:0]                     psram_dq_i
);
    localparam integer LENW = $clog2(BUF_BYTES+1);
    localparam integer BW   = $clog2(BUF_BYTES);
    localparam [2:0] ST_OK = 3'd0, ST_NOT_READY = 3'd1, ST_INVALID = 3'd2,
                     ST_TIMEOUT = 3'd3, ST_CORE_FAULT = 3'd4;

    // =========================== user domain ===========================
    reg              req_tgl;
    reg              rec_tgl;
    reg              u_write;
    reg  [22:0]      u_addr;
    reg  [LENW-1:0]  u_len;
    reg  [LENW-1:0]  u_idx;
    reg  [31:0]      u_timer;
    localparam [2:0] U_IDLE = 3'd0, U_FILL = 3'd1, U_WAIT = 3'd2, U_RD_A = 3'd3,
                     U_RD_D = 3'd4, U_RESP = 3'd5;
    reg [2:0] u_state;

    // synchronisers into uclk (not reset: they track the other domain)
    reg [1:0] ack_s, rdy_s, err_s;
    reg [1:0] ec0_s, ec1_s;
    reg [2:0] st0_s, st1_s;
    wire      m_ack;
    wire      m_ready, m_error;
    wire [1:0] m_err_code;
    wire [2:0] m_status;
    always @(posedge uclk) begin
        ack_s <= {ack_s[0], m_ack};
        rdy_s <= {rdy_s[0], m_ready};
        err_s <= {err_s[0], m_error};
        ec0_s <= m_err_code; ec1_s <= ec0_s;
        st0_s <= m_status;   st1_s <= st0_s;
    end
    wire in_sync = (ack_s[1] == req_tgl);
    assign ram_ready    = rdy_s[1] & in_sync;
    assign ram_error    = err_s[1];
    assign ram_err_code = ec1_s;

    // buffers
    wire [7:0]    rbuf_q;
    reg  [BW-1:0] rbuf_raddr;
    wire          wbuf_we = (u_state == U_FILL) && wr_valid;


    wire [23:0] req_end = {1'b0, req_addr} + {{(24-LENW){1'b0}}, req_len};
    wire        req_bad = (req_len == {LENW{1'b0}}) || (req_len > BUF_BYTES[LENW-1:0]) ||
                          (req_end > 24'h800000);

    assign req_ready = (u_state == U_IDLE) && !resp_valid;
    assign wr_ready  = (u_state == U_FILL);
    assign rd_valid  = (u_state == U_RD_D);
    assign rd_data   = rbuf_q;

    always @(posedge uclk) begin
        if (urst) begin
            u_state     <= U_IDLE;
            req_tgl     <= 1'b0;
            rec_tgl     <= 1'b0;
            resp_valid  <= 1'b0;
            resp_status <= ST_OK;
            u_idx       <= {LENW{1'b0}};
            u_timer     <= 32'd0;
            rbuf_raddr  <= {BW{1'b0}};
        end else begin
            if (recover) rec_tgl <= ~rec_tgl;
            if (resp_valid && resp_ready) resp_valid <= 1'b0;
            case (u_state)
            U_IDLE: if (req_valid && req_ready) begin
                u_write <= req_write;
                u_addr  <= req_addr;
                u_len   <= req_len;
                u_idx   <= {LENW{1'b0}};
                if (req_bad) begin
                    resp_valid <= 1'b1; resp_status <= ST_INVALID;
                end else if (!in_sync || !rdy_s[1]) begin
                    resp_valid <= 1'b1; resp_status <= ST_NOT_READY;
                end else if (req_write) begin
                    u_state <= U_FILL;
                end else begin
                    req_tgl <= ~req_tgl; u_timer <= 32'd0; u_state <= U_WAIT;
                end
            end
            U_FILL: if (wr_valid) begin
                u_idx <= u_idx + 1'b1;
                if (u_idx + 1'b1 == u_len) begin
                    req_tgl <= ~req_tgl; u_timer <= 32'd0; u_state <= U_WAIT;
                end
            end
            U_WAIT: begin
                u_timer <= u_timer + 32'd1;
                if (in_sync) begin
                    if (!u_write && st1_s == ST_OK) begin
                        u_idx      <= {LENW{1'b0}};
                        rbuf_raddr <= {BW{1'b0}};
                        u_state    <= U_RD_A;
                    end else begin
                        resp_status <= st1_s;
                        u_state     <= U_RESP;
                    end
                end else if (u_timer >= UTIMEOUT) begin
                    resp_status <= ST_TIMEOUT;
                    u_state     <= U_RESP;     // stays out of sync until drained
                end
            end
            U_RD_A: u_state <= U_RD_D;          // sync RAM latency
            U_RD_D: if (rd_ready) begin
                if (u_idx + 1'b1 == u_len) begin
                    resp_status <= ST_OK;
                    u_state     <= U_RESP;
                end else begin
                    u_idx      <= u_idx + 1'b1;
                    rbuf_raddr <= rbuf_raddr + 1'b1;
                    u_state    <= U_RD_A;
                end
            end
            U_RESP: begin
                resp_valid <= 1'b1;
                u_state    <= U_IDLE;
            end
            default: u_state <= U_IDLE;
            endcase
        end
    end

    // =========================== memory domain ===========================
    reg [2:0] req_s, rec_s;                // [2] is the delayed copy
    always @(posedge mclk) begin
        req_s <= {req_s[1:0], req_tgl};
        rec_s <= {rec_s[1:0], rec_tgl};
    end
    reg        m_ack_q;
    reg        req_seen, rec_seen;
    reg [1:0]  settle;
    reg [1:0]  ack_pend;
    reg        c_valid;
    reg [2:0]  m_status_q;
    reg        c_busy;
    wire       c_ready;
    wire       c_done;
    wire [2:0] c_done_st;
    wire       c_init_req = (settle == 2'd3) && (rec_s[1] != rec_seen);

    always @(posedge mclk) begin
        if (mrst) begin
            // A request in flight is aborted: report CORE_FAULT. The status
            // register is written >= 3 mclk before ack moves (settle below).
            settle     <= 2'd0;
            ack_pend   <= 2'd0;
            c_valid    <= 1'b0;
            c_busy     <= 1'b0;
            m_status_q <= ST_CORE_FAULT;
        end else if (settle != 2'd3) begin
            // adopt the synchronised levels: no stale request can replay
            settle   <= settle + 2'd1;
            req_seen <= req_s[1];
            rec_seen <= rec_s[1];
            if (settle == 2'd2) m_ack_q <= req_s[1];
        end else begin
            if (c_init_req) rec_seen <= rec_s[1];
            if (!c_busy && (req_s[1] != req_seen)) begin
                req_seen <= req_s[1];
                c_valid  <= 1'b1;
                c_busy   <= 1'b1;
            end
            if (c_valid && c_ready) c_valid <= 1'b0;
            // status first, ack two mclk later, so the user side can never
            // see the new ack together with an old status value
            if (c_done) begin
                m_status_q <= c_done_st;
                ack_pend   <= 2'd1;
            end else if (ack_pend == 2'd1) begin
                ack_pend   <= 2'd2;
            end else if (ack_pend == 2'd2) begin
                ack_pend   <= 2'd0;
                m_ack_q    <= req_seen;
                c_busy     <= 1'b0;
            end
        end
    end
    assign m_ack    = m_ack_q;
    assign m_status = m_status_q;

    wire [BW-1:0] wbuf_raddr, rbuf_waddr;
    wire [7:0]    wbuf_rdata, rbuf_wdata;
    wire          rbuf_we;
    wire [7:0]    id_mfid, id_kgd;

    psram_qspi_core #(
        .MCLK_HZ(MCLK_HZ), .CLK_DIV(CLK_DIV), .BUF_BYTES(BUF_BYTES), .TCEM_NS(TCEM_NS)
    ) u_core (
        .clk(mclk), .rst(mrst),
        .cmd_valid(c_valid), .cmd_ready(c_ready), .cmd_write(u_write),
        .cmd_addr(u_addr), .cmd_len(u_len),
        .done_valid(c_done), .done_status(c_done_st),
        .init_req(c_init_req),
        .wbuf_raddr(wbuf_raddr), .wbuf_rdata(wbuf_rdata),
        .rbuf_we(rbuf_we), .rbuf_waddr(rbuf_waddr), .rbuf_wdata(rbuf_wdata),
        .ready(m_ready), .error(m_error), .err_code(m_err_code),
        .id_mfid(id_mfid), .id_kgd(id_kgd),
        .dbg_freeze(dbg_freeze),
        .psram_ce_n(psram_ce_n), .psram_sclk(psram_sclk),
        .psram_dq_o(psram_dq_o), .psram_dq_oe(psram_dq_oe), .psram_dq_i(psram_dq_i)
    );

    psram_dc_ram #(.AW(BW)) u_wbuf (
        .wclk(uclk), .we(wbuf_we), .waddr(u_idx[BW-1:0]), .wdata(wr_data),
        .rclk(mclk), .raddr(wbuf_raddr), .rdata(wbuf_rdata));
    psram_dc_ram #(.AW(BW)) u_rbuf (
        .wclk(mclk), .we(rbuf_we), .waddr(rbuf_waddr), .wdata(rbuf_wdata),
        .rclk(uclk), .raddr(rbuf_raddr), .rdata(rbuf_q));
endmodule

// Simple dual-port, dual-clock RAM with registered read (block-RAM style).
module psram_dc_ram #(parameter integer AW = 8) (
    input  wire          wclk,
    input  wire          we,
    input  wire [AW-1:0] waddr,
    input  wire [7:0]    wdata,
    input  wire          rclk,
    input  wire [AW-1:0] raddr,
    output reg  [7:0]    rdata
);
    reg [7:0] mem [0:(1<<AW)-1];
    always @(posedge wclk) if (we) mem[waddr] <= wdata;
    always @(posedge rclk) rdata <= mem[raddr];
endmodule
