// ARC-1 Compact R06 -- conservative QPI controller for one AP Memory
// APS6404L-3SQR (64 Mbit, 8 MiB) PSRAM, T35 private memory candidate.
//
// Evidence level: RTL_SIMULATED only (see ../tb). Not NATIVE_EDA_VERIFIED,
// not PROTOTYPE_MEASURED. Pad timing, IO standard and bank placement must be
// closed by Efinity STA and bench measurement.
//
// Datasheet basis (APM SPI 3V PSRAM datasheet Rev. 2.7, 2024-01-05):
//   * power-up: CE# high, CLK low for tPU >= 150 us, then RSTEN 'h66 + RST 'h99,
//     tRST >= 50 ns before the next command (section 8, 14, table 10)
//   * Read ID 'h9F (SPI only, directly after global reset): MF ID 'h0D,
//     KGD 'h5D = PASS (section 12, figure 13, table 3)
//   * Enter Quad Mode 'h35 (SPI) -> QPI; QPI Fast Quad Read 'hEB with 6 wait
//     cycles; QPI Write 'h38 (== 'h02 in QPI) with 0 wait cycles (section 9.5)
//   * tCEM (CE# low pulse width) max 8 us standard grade / 3 us extended grade;
//     tCPH >= 18 ns; every read/write must end with CE# high (section 9.6)
//   * 1 KiB page; linear bursts may cross a page once only and only <= 84 MHz.
//     This controller never crosses a page: every CE# transaction is split at
//     1 KiB boundaries and at a tCEM-derived byte limit.
//
// Clocking: one clock `clk` (mclk). SCLK = mclk / (2*CLK_DIV), SPI mode 0.
// Outputs change on SCLK falling edges (and at CE# assertion); read data is
// sampled by the mclk edge that raises SCLK, i.e. half an SCLK period after
// the PSRAM launched it (tACLK <= 5.5 ns after the falling edge). This is the
// deliberately simple, low-frequency scheme; it is NOT a >84 MHz design.
//
// Reset is synchronous, active high, in the clk domain.

module psram_qspi_core #(
    parameter integer MCLK_HZ       = 40000000,  // <= 200 MHz (32-bit param math)
    parameter integer CLK_DIV       = 1,         // SCLK = MCLK/(2*CLK_DIV)
    parameter integer BUF_BYTES     = 256,       // power of two
    parameter integer TPU_US        = 150,
    parameter integer TCEM_NS       = 8000,      // 3000 for the X (105 C) grade
    parameter integer TCPH_NS       = 18,
    parameter integer TRST_NS       = 50,
    parameter integer CE_HOLD_TICKS = 2,         // SCLK-low half periods before CE# high
    parameter [7:0]   EXPECT_MFID   = 8'h0D,
    parameter [7:0]   EXPECT_KGD    = 8'h5D
) (
    input  wire                         clk,
    input  wire                         rst,
    // user operation (one outstanding)
    input  wire                         cmd_valid,
    output wire                         cmd_ready,
    input  wire                         cmd_write,
    input  wire [22:0]                  cmd_addr,
    input  wire [$clog2(BUF_BYTES+1)-1:0] cmd_len,
    output reg                          done_valid,
    output reg  [2:0]                   done_status,
    // re-run reset/ID/QPI-entry sequence (recovery)
    input  wire                         init_req,
    // write-data buffer read port (sync read, 1 cycle latency)
    output reg  [$clog2(BUF_BYTES)-1:0] wbuf_raddr,
    input  wire [7:0]                   wbuf_rdata,
    // read-data buffer write port
    output reg                          rbuf_we,
    output reg  [$clog2(BUF_BYTES)-1:0] rbuf_waddr,
    output reg  [7:0]                   rbuf_wdata,
    // status
    output reg                          ready,
    output reg                          error,
    output reg  [1:0]                   err_code,
    output reg  [7:0]                   id_mfid,
    output reg  [7:0]                   id_kgd,
    // verification-only stall hook (tie 0 in hardware)
    input  wire                         dbg_freeze,
    // PSRAM pins (to IO cells)
    output reg                          psram_ce_n,
    output reg                          psram_sclk,
    output reg  [3:0]                   psram_dq_o,
    output reg  [3:0]                   psram_dq_oe,
    input  wire [3:0]                   psram_dq_i
);
    localparam integer LENW = $clog2(BUF_BYTES+1);
    localparam integer BW   = $clog2(BUF_BYTES);

    // ---- status codes (shared with psram_user_port) ----
    localparam [2:0] ST_OK = 3'd0, ST_NOT_READY = 3'd1, ST_INVALID = 3'd2, ST_CORE_FAULT = 3'd4;
    localparam [1:0] ERR_NONE = 2'd0, ERR_ID = 2'd1, ERR_WDOG = 2'd2;

    // ---- timing in mclk cycles ----
    localparam integer MCLK_KHZ  = MCLK_HZ / 1000;
    localparam integer PU_CYC    = TPU_US * (MCLK_KHZ / 1000) + (MCLK_KHZ % 1000 != 0 ? TPU_US : 0) + 2;
    localparam integer TCPH_CYC0 = (TCPH_NS * MCLK_KHZ + 999999) / 1000000;
    localparam integer TRST_CYC0 = (TRST_NS * MCLK_KHZ + 999999) / 1000000;
    localparam integer GAP_MIN   = 2 * CLK_DIV;  // >= one SCLK period CE# high
    localparam integer GAP_CYC   = (TRST_CYC0 > TCPH_CYC0 ? TRST_CYC0 : TCPH_CYC0) > GAP_MIN ?
                                   (TRST_CYC0 > TCPH_CYC0 ? TRST_CYC0 : TCPH_CYC0) : GAP_MIN;
    localparam integer TCEM_CYC  = (TCEM_NS / 10) * (MCLK_KHZ / 100) / 1000;  // floor
    localparam integer BUDGET    = (TCEM_CYC * 3) / 4;     // planned max CE# low
    localparam integer WDOG_CYC  = (TCEM_CYC * 7) / 8;     // abort before tCEM
    // CE# low cycles for a QPI read of n bytes:
    //   CLK_DIV*(1 + 2*(14 + 2n) + CE_HOLD_TICKS)
    localparam integer NMAX_RAW  = ((BUDGET / CLK_DIV - 1 - CE_HOLD_TICKS) / 2 - 14) / 2;
    localparam integer CHUNK0    = NMAX_RAW < BUF_BYTES ? NMAX_RAW : BUF_BYTES;
    localparam integer CHUNK     = CHUNK0 < 1024 ? CHUNK0 : 1024;
    // Init commands include SPI Read ID ('h9F, max 33 MHz): run every init
    // transaction with SCLK <= 25 MHz.
    localparam integer IDIV_RAW  = (MCLK_HZ + 49999999) / 50000000;
    localparam integer INIT_DIV  = IDIV_RAW;
    // longest init transaction: Read ID = 8 cmd + 24 addr + 16 data clocks
    localparam integer ID_CE_CYC = INIT_DIV * (1 + 2 * 48 + CE_HOLD_TICKS);

    generate
        if (NMAX_RAW < 1) begin : g_bad_tcem
            // Elaboration error: the chosen MCLK_HZ/CLK_DIV cannot move one
            // byte inside the tCEM budget.
            PARAMETER_ERROR_tcem_budget_too_small u_param_error();
        end
        if (ID_CE_CYC >= BUDGET) begin : g_bad_init
            // Read ID at <= 25 MHz would not fit inside the tCEM budget.
            PARAMETER_ERROR_read_id_exceeds_tcem u_param_error();
        end
        if ((1 << BW) != BUF_BYTES) begin : g_bad_buf
            PARAMETER_ERROR_buf_bytes_not_power_of_two u_param_error();
        end
    endgenerate

    // =====================================================================
    // Transaction engine: one CE# low period.
    // =====================================================================
    localparam [2:0] E_IDLE = 3'd0, E_SETUP = 3'd1, E_RUN = 3'd2, E_HOLD = 3'd3, E_GAP = 3'd4;
    reg  [2:0]      e_state;
    reg             e_start;          // pulse from sequencer
    reg             e_done;           // pulse to sequencer
    reg             e_abort;          // pulse from watchdog
    // descriptor
    reg             d_quad;           // cmd/addr on 4 lines (else SIO0 only)
    reg  [31:0]     d_osr;            // cmd/addr bits, left aligned
    reg  [5:0]      d_ca_cycles;
    reg  [2:0]      d_wait;
    reg  [LENW-1:0] d_bytes;
    reg             d_write;
    reg             d_serial_rd;      // SPI read on SO (SIO1), e.g. Read ID
    reg  [BW-1:0]   d_base;
    reg  [15:0]     d_div;            // SCLK half period in mclk cycles

    reg  [31:0]     osr;
    reg  [15:0]     cyc;              // current SCLK cycle index
    reg  [15:0]     div_cnt;
    reg  [15:0]     gap_cnt;
    reg  [3:0]      rd_hi;
    reg  [7:0]      rd_sr;
    reg             rd_byte_v;        // serial read byte strobe (for ID)
    reg  [LENW-1:0] rd_byte_idx;
    reg  [7:0]      rd_byte;

    wire [15:0] ca_end  = {10'd0, d_ca_cycles};
    wire [15:0] w_end   = ca_end + {13'd0, d_wait};
    wire [15:0] d_end   = w_end + (d_serial_rd ? ({{(16-LENW){1'b0}}, d_bytes} << 3)
                                               : ({{(16-LENW){1'b0}}, d_bytes} << 1));
    wire        tick    = (div_cnt == d_div - 16'd1) && !dbg_freeze;
    wire [15:0] hold_last = CE_HOLD_TICKS[15:0] * d_div - 16'd1;

    // next-cycle helpers
    wire [15:0] ncyc    = cyc + 16'd1;
    wire [15:0] nrel    = ncyc - w_end;                 // data-relative index of next cycle
    wire [15:0] crel    = cyc - w_end;                  // data-relative index of this cycle
    wire [15:0] n2cyc   = cyc + 16'd2;
    wire [15:0] n2rel   = n2cyc - w_end;
    wire [31:0] osr_sh  = d_quad ? {osr[27:0], 4'd0} : {osr[30:0], 1'b0};

    always @(posedge clk) begin
        e_done    <= 1'b0;
        rbuf_we   <= 1'b0;
        rd_byte_v <= 1'b0;
        if (rst || e_abort) begin
            e_state     <= E_IDLE;
            psram_ce_n  <= 1'b1;
            psram_sclk  <= 1'b0;
            psram_dq_o  <= 4'd0;
            psram_dq_oe <= 4'd0;
            div_cnt     <= 16'd0;
            cyc         <= 16'd0;
            gap_cnt     <= 16'd0;
            if (e_abort) e_done <= 1'b0;
        end else begin
            case (e_state)
            E_IDLE: begin
                psram_ce_n  <= 1'b1;
                psram_sclk  <= 1'b0;
                psram_dq_oe <= 4'd0;
                if (e_start) begin
                    // CE# low and cycle-0 data together (CLK low: mode 0).
                    psram_ce_n  <= 1'b0;
                    osr         <= d_osr;
                    cyc         <= 16'd0;
                    div_cnt     <= 16'd0;
                    wbuf_raddr  <= d_base;
                    if (d_quad) begin
                        psram_dq_o  <= d_osr[31:28];
                        psram_dq_oe <= 4'hF;
                    end else begin
                        psram_dq_o  <= {3'b000, d_osr[31]};
                        psram_dq_oe <= 4'b0001;
                    end
                    e_state <= E_SETUP;
                end
            end
            E_SETUP: begin  // tCSP: CLK_DIV mclk with CE# low before first rise
                if (tick) begin div_cnt <= 16'd0; e_state <= E_RUN; end
                else if (!dbg_freeze) div_cnt <= div_cnt + 16'd1;
            end
            E_RUN: begin
                if (!tick) begin
                    if (!dbg_freeze) div_cnt <= div_cnt + 16'd1;
                end else begin
                    div_cnt <= 16'd0;
                    if (!psram_sclk) begin
                        // ---------------- rising edge: sample ----------------
                        psram_sclk <= 1'b1;
                        if (!d_write && cyc >= w_end && cyc < d_end) begin
                            if (d_serial_rd) begin
                                rd_sr <= {rd_sr[6:0], psram_dq_i[1]};
                                if (crel[2:0] == 3'd7) begin
                                    rd_byte_v   <= 1'b1;
                                    rd_byte_idx <= crel[LENW+2:3];
                                    rd_byte     <= {rd_sr[6:0], psram_dq_i[1]};
                                end
                            end else if (!crel[0]) begin
                                rd_hi <= psram_dq_i;
                            end else begin
                                rbuf_we    <= 1'b1;
                                rbuf_waddr <= d_base + crel[BW:1];
                                rbuf_wdata <= {rd_hi, psram_dq_i};
                            end
                        end
                    end else begin
                        // ---------------- falling edge: drive -----------------
                        psram_sclk <= 1'b0;
                        if (ncyc >= d_end) begin
                            psram_dq_oe <= 4'd0;
                            gap_cnt     <= 16'd0;
                            e_state     <= E_HOLD;
                        end else begin
                            cyc <= ncyc;
                            // sync-RAM prefetch: address for cycle ncyc+1 is
                            // presented now, data is used at the next fall.
                            if (d_write && n2cyc >= w_end)
                                wbuf_raddr <= d_base + n2rel[BW:1];
                            if (ncyc < ca_end) begin
                                osr <= osr_sh;
                                if (d_quad) psram_dq_o <= osr_sh[31:28];
                                else        psram_dq_o <= {3'b000, osr_sh[31]};
                            end else if (ncyc < w_end || !d_write) begin
`ifdef MUTANT_NO_TURNAROUND
                                psram_dq_oe <= 4'hF;       // verification mutant
`else
                                psram_dq_oe <= 4'd0;       // turnaround / read data
`endif
                            end else begin
                                psram_dq_oe <= 4'hF;
                                psram_dq_o  <= nrel[0] ? wbuf_rdata[3:0] : wbuf_rdata[7:4];
                            end
                        end
                    end
                end
            end
            E_HOLD: begin   // SCLK low, CE# still low (tCHD)
                if (!dbg_freeze) begin
                    if (gap_cnt == hold_last) begin
                        psram_ce_n <= 1'b1;
                        gap_cnt    <= 16'd0;
                        e_state    <= E_GAP;
                    end else gap_cnt <= gap_cnt + 16'd1;
                end
            end
            E_GAP: begin    // CE# high >= max(tCPH, tRST, one SCLK period)
                if (gap_cnt == GAP_CYC[15:0] - 16'd1) begin
                    e_done  <= 1'b1;
                    e_state <= E_IDLE;
                end else gap_cnt <= gap_cnt + 16'd1;
            end
            default: e_state <= E_IDLE;
            endcase
        end
    end

    // =====================================================================
    // Sequencer: power-up, reset, ID check, QPI entry, chunked user ops.
    // =====================================================================
    localparam [3:0] S_PU = 4'd0, S_INIT = 4'd1, S_INIT_W = 4'd2, S_READY = 4'd3,
                     S_OP = 4'd4, S_OP_W = 4'd5, S_ERR = 4'd6;
    reg  [3:0]      s_state;
    reg  [2:0]      init_step;
    reg  [31:0]     pu_cnt;
    reg  [31:0]     wdog;
    reg             op_active;
    reg             op_write;
    reg  [22:0]     op_addr;
    reg  [LENW-1:0] op_rem;
    reg  [BW:0]     op_off;
    reg  [2:0]      op_status;
    reg  [7:0]      rd_cap0, rd_cap1;

`ifdef MUTANT_NO_PAGE_SPLIT
    wire [15:0]     page_rem  = 16'd1024;                       // verification mutant
`else
    wire [15:0]     page_rem  = 16'd1024 - {6'd0, op_addr[9:0]};
`endif
    wire [15:0]     rem16     = {{(16-LENW){1'b0}}, op_rem};
    wire [15:0]     lim16     = CHUNK[15:0];
    wire [15:0]     c_a       = (rem16 < lim16) ? rem16 : lim16;
    wire [15:0]     c_b       = (c_a < page_rem) ? c_a : page_rem;
    wire [LENW-1:0] chunk_len = c_b[LENW-1:0];

    wire [23:0] cmd_end = {1'b0, cmd_addr} + {{(24-LENW){1'b0}}, cmd_len};
    wire        cmd_bad = (cmd_len == {LENW{1'b0}}) || (cmd_len > BUF_BYTES[LENW-1:0]) ||
                          (cmd_end > 24'h800000);

    assign cmd_ready = !op_active && ((s_state == S_READY) || (s_state == S_ERR) ||
                       (s_state == S_PU) || (s_state == S_INIT) || (s_state == S_INIT_W));

    // init microcode: QPI-format RSTEN/RST (in case the device was left in QPI
    // by an FPGA-only reset), SPI RSTEN/RST, SPI Read ID, SPI Enter Quad.
    task automatic load_init(input [2:0] step);
        begin
            d_div <= INIT_DIV[15:0];
            d_write <= 1'b0; d_wait <= 3'd0; d_bytes <= {LENW{1'b0}}; d_serial_rd <= 1'b0; d_base <= {BW{1'b0}};
            case (step)
            3'd0: begin d_quad <= 1'b1; d_osr <= {8'h66, 24'd0}; d_ca_cycles <= 6'd2;  end
            3'd1: begin d_quad <= 1'b1; d_osr <= {8'h99, 24'd0}; d_ca_cycles <= 6'd2;  end
            3'd2: begin d_quad <= 1'b0; d_osr <= {8'h66, 24'd0}; d_ca_cycles <= 6'd8;  end
            3'd3: begin d_quad <= 1'b0; d_osr <= {8'h99, 24'd0}; d_ca_cycles <= 6'd8;  end
            3'd4: begin d_quad <= 1'b0; d_osr <= {8'h9F, 24'd0}; d_ca_cycles <= 6'd32;
                        d_serial_rd <= 1'b1; d_bytes <= 2; end
            default: begin d_quad <= 1'b0; d_osr <= {8'h35, 24'd0}; d_ca_cycles <= 6'd8; end
            endcase
        end
    endtask

    always @(posedge clk) begin
        e_start    <= 1'b0;
        e_abort    <= 1'b0;
        done_valid <= 1'b0;
        if (rst) begin
            s_state   <= S_PU;
            pu_cnt    <= 32'd0;
            ready     <= 1'b0;
            error     <= 1'b0;
            err_code  <= ERR_NONE;
            id_mfid   <= 8'd0;
            id_kgd    <= 8'd0;
            op_active <= 1'b0;
            init_step <= 3'd0;
            wdog      <= 32'd0;
            d_quad <= 1'b0; d_osr <= 32'd0; d_ca_cycles <= 6'd0; d_wait <= 3'd0;
            d_bytes <= {LENW{1'b0}}; d_write <= 1'b0; d_serial_rd <= 1'b0; d_base <= {BW{1'b0}};
            d_div <= INIT_DIV[15:0];
        end else begin
            // ---- immediate replies while not ready / for invalid ops ----
            if (cmd_valid && cmd_ready) begin
                done_valid  <= 1'b1;
                if (s_state != S_READY)  done_status <= ST_NOT_READY;
                else if (cmd_bad)        done_status <= ST_INVALID;
                else begin
                    done_valid <= 1'b0;
                    op_active  <= 1'b1;
                    op_write   <= cmd_write;
                    op_addr    <= cmd_addr;
                    op_rem     <= cmd_len;
                    op_off     <= {(BW+1){1'b0}};
                    op_status  <= ST_OK;
                end
            end

            // ---- watchdog on every started CE# transaction ----
            if (s_state == S_INIT_W || s_state == S_OP_W) begin
                wdog <= wdog + 32'd1;
                if (wdog >= WDOG_CYC) begin
                    e_abort  <= 1'b1;
                    ready    <= 1'b0;
                    error    <= 1'b1;
                    err_code <= ERR_WDOG;
                    s_state  <= S_ERR;
                    if (op_active) begin
                        op_active   <= 1'b0;
                        done_valid  <= 1'b1;
                        done_status <= ST_CORE_FAULT;
                    end
                end
            end else wdog <= 32'd0;

            case (s_state)
            S_PU: begin
                if (pu_cnt >= PU_CYC) begin
`ifdef MUTANT_SKIP_RESET
                    init_step <= 3'd4;                      // verification mutant
`else
                    init_step <= 3'd0;
`endif
                    s_state   <= S_INIT;
                end else pu_cnt <= pu_cnt + 32'd1;
            end
            S_INIT: begin
                load_init(init_step);
                e_start <= 1'b1;
                s_state <= S_INIT_W;
            end
            S_INIT_W: if (e_done && wdog < WDOG_CYC) begin
                if (init_step == 3'd4) begin
                    id_mfid <= rd_cap0;
                    id_kgd  <= rd_cap1;
                    // positive match only: X/Z/garbage all count as failure
                    if (rd_cap0 == EXPECT_MFID && rd_cap1 == EXPECT_KGD) begin
                        init_step <= 3'd5;
                        s_state   <= S_INIT;
                    end else begin
                        error    <= 1'b1;
                        err_code <= ERR_ID;
                        s_state  <= S_ERR;
                    end
                end else if (init_step == 3'd5) begin
                    ready    <= 1'b1;
                    error    <= 1'b0;
                    err_code <= ERR_NONE;
                    s_state  <= S_READY;
                end else begin
                    init_step <= init_step + 3'd1;
                    s_state   <= S_INIT;
                end
            end
            S_READY: begin
                if (op_active) s_state <= S_OP;
                else if (init_req) begin
                    ready     <= 1'b0;
                    init_step <= 3'd0;
                    s_state   <= S_INIT;
                end
            end
            S_OP: begin
                if (op_rem == {LENW{1'b0}}) begin
                    op_active   <= 1'b0;
                    done_valid  <= 1'b1;
                    done_status <= op_status;
                    s_state     <= S_READY;
                end else begin
                    d_quad      <= 1'b1;
                    d_osr       <= {(op_write ? 8'h38 : 8'hEB), 1'b0, op_addr};
                    d_ca_cycles <= 6'd8;
`ifdef MUTANT_SAMPLE_EARLY
                    d_wait      <= op_write ? 3'd0 : 3'd5;      // verification mutant
`else
                    d_wait      <= op_write ? 3'd0 : 3'd6;
`endif
                    d_bytes     <= chunk_len;
                    d_write     <= op_write;
                    d_serial_rd <= 1'b0;
                    d_base      <= op_off[BW-1:0];
                    d_div       <= CLK_DIV[15:0];
                    e_start     <= 1'b1;
                    s_state     <= S_OP_W;
                end
            end
            S_OP_W: if (e_done && wdog < WDOG_CYC) begin
                op_addr <= op_addr + {{(23-LENW){1'b0}}, d_bytes};
                op_rem  <= op_rem - d_bytes;
                op_off  <= op_off + {{(BW+1-LENW){1'b0}}, d_bytes};
                s_state <= S_OP;
            end
            S_ERR: begin
                ready <= 1'b0;
                if (init_req) begin
                    init_step <= 3'd0;
                    s_state   <= S_INIT;
                end
            end
            default: s_state <= S_ERR;
            endcase
        end
    end

    // capture serial ID bytes
    always @(posedge clk) begin
        if (rst) begin rd_cap0 <= 8'd0; rd_cap1 <= 8'd0; end
        else if (rd_byte_v) begin
            if (rd_byte_idx == 0) rd_cap0 <= rd_byte;
            else                  rd_cap1 <= rd_byte;
        end
    end

`ifdef PSRAM_CORE_EXPOSE_PARAMS
    initial $display("psram_qspi_core: PU_CYC=%0d GAP_CYC=%0d TCEM_CYC=%0d BUDGET=%0d WDOG=%0d CHUNK=%0d INIT_DIV=%0d",
                     PU_CYC, GAP_CYC, TCEM_CYC, BUDGET, WDOG_CYC, CHUNK, INIT_DIV);
`endif
endmodule
