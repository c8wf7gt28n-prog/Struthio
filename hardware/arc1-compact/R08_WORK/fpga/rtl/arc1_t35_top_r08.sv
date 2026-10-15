// ARC-1 Compact R08 -- T35F400C3 top level (OPTIONAL accelerator FPGA).
// Copied from R06_WORK/fpga/top/arc1_t35_top.sv (unchanged there). R08 changes:
//   * psram_power_guard between the controller and the PSRAM pads; new pad
//     psram_pg_IN (supervisor on the switched PSRAM_VDD), psram_pwr_en_IN (the
//     load-switch EN, so a commanded power-off parks the pads before the rail
//     decays) and CE# output enable
//     (psram_ce_n_OE): CE# is released to its pull-up while the PSRAM is off.
//   * mbx_regs_r08 (AMBX v2): PSRAM_POWER_ON / POWER_LOST / EPOCH.
//   * SPI0 is now shared with the F133 boot NOR (corrective handoff v1.0): the
//     board isolates this FPGA's SPI pins with buffers; the RTL is unchanged
//     on that side (mailbox selected by its own SS_N).
// Evidence level: RTL_SIMULATED (tb_top_r08). NATIVE_EDA_NOT_RUN.
//
// Port naming follows the Efinity convention where the Interface Designer owns
// the I/O cells and PLL: bidirectional pads appear as <name>_IN/_OUT/_OE and
// PLL outputs as plain clock inputs. Ball assignments live in
// ../../board/r06_board_plan.json and ../efinity/arc1_t35_r06_pins.csv.
//
// Contents in R06:
//   * F133 SPI0 mailbox (mbx_spi_slave + mbx_regs), IRQ to F133 (open drain)
//   * TRANSPORT LOOPBACK job engine (copies request frame to response).
//     The R05 transform engine is NOT yet wired in: that is PASS 7 step 4.
//   * PSRAM controller (psram_user_port + psram_qspi_core) and a BIST the F133
//     can start through the mailbox.
module arc1_t35_top_r08 #(
    parameter integer SYS_HZ   = 80000000,   // sys_clk from PLL (mailbox, BIST, PSRAM user side)
    parameter integer MCLK_HZ  = 40000000,   // psram_mclk from PLL -> SCLK 20 MHz
    parameter integer BIST_BLOCKS = 64
) (
    input  wire       sys_clk,
    input  wire       psram_mclk,
    input  wire       pll_locked,
    // F133 SPI0 mailbox (BANK1D)
    input  wire       t35_sck_IN,
    input  wire       t35_ss_n_IN,
    input  wire       t35_mosi_IN,
    output wire       t35_miso_OUT,
    output wire       t35_miso_OE,
    output wire       t35_irq_n_OUT,     // drive 0 ...
    output wire       t35_irq_n_OE,      // ... only when asserted (open drain)
    // PSRAM (BANK1C)
    output wire       psram_ce_n,
    output wire       psram_ce_n_OE,
    input  wire       psram_pg_IN,       // PSRAM_VDD supervisor, open drain, low = power bad
    input  wire       psram_pwr_en_IN,   // load-switch EN (F133 PSRAM_PWR_REQ & CDONE): low = power going away
    output wire       psram_sclk,
    input  wire [3:0] psram_sio_IN,
    output wire [3:0] psram_sio_OUT,
    output wire [3:0] psram_sio_OE,
    // debug
    output wire       t35_led0,
    output wire       t35_dbg_tx
);
    // ---------------- resets ----------------
    // Held until the PLL locks, then released synchronously in each domain.
    reg [3:0] rst_sys_sr = 4'hF, rst_mem_sr = 4'hF;
    always @(posedge sys_clk or negedge pll_locked)
        if (!pll_locked) rst_sys_sr <= 4'hF; else rst_sys_sr <= {rst_sys_sr[2:0], 1'b0};
    always @(posedge psram_mclk or negedge pll_locked)
        if (!pll_locked) rst_mem_sr <= 4'hF; else rst_mem_sr <= {rst_mem_sr[2:0], 1'b0};
    wire rst_sys = rst_sys_sr[3];
    wire rst_mem = rst_mem_sr[3];

    // ---------------- mailbox ----------------
    wire [15:0] bus_addr;
    wire        bus_we, bus_re, frame_end;
    wire [7:0]  bus_wdata, bus_rdata;
    mbx_spi_slave u_spi (
        .clk(sys_clk), .rst(rst_sys),
        .sck_i(t35_sck_IN), .ss_n_i(t35_ss_n_IN), .mosi_i(t35_mosi_IN),
        .miso_o(t35_miso_OUT), .miso_oe(t35_miso_OE),
        .bus_addr(bus_addr), .bus_we(bus_we), .bus_wdata(bus_wdata),
        .bus_re(bus_re), .bus_rdata(bus_rdata), .frame_end(frame_end));

    wire        irq, job_valid, resp_we, resp_post;
    wire [15:0] job_len, resp_len;
    wire [12:0] req_raddr, resp_waddr;
    wire [7:0]  req_rdata, resp_wdata;
    wire        ram_ready, ram_error, psram_recover, bist_start, bist_busy, bist_pass, bist_fail;
    wire [1:0]  ram_err_code;
    wire [31:0] bist_errs;
    wire        guard_on, guard_on_sys, guard_core_rst, c_ce_n, c_sclk;
    wire [3:0]  c_dq_o, c_dq_oe;

    mbx_regs_r08 u_regs (
        .clk(sys_clk), .rst(rst_sys),
        .bus_addr(bus_addr), .bus_we(bus_we), .bus_wdata(bus_wdata), .bus_re(bus_re), .bus_rdata(bus_rdata),
        .irq(irq), .job_valid(job_valid), .job_len(job_len),
        .req_raddr(req_raddr), .req_rdata(req_rdata),
        .resp_we(resp_we), .resp_waddr(resp_waddr), .resp_wdata(resp_wdata),
        .resp_post(resp_post), .resp_len_in(resp_len),
        .psram_ready(ram_ready), .psram_error(ram_error), .psram_err_code(ram_err_code),
        .psram_recover(psram_recover), .bist_start(bist_start),
        .bist_busy(bist_busy), .bist_pass(bist_pass), .bist_fail(bist_fail), .bist_errs(bist_errs),
        .psram_power_on(guard_on_sys));

    mbx_loopback u_loop (
        .clk(sys_clk), .rst(rst_sys), .job_valid(job_valid), .job_len(job_len),
        .req_raddr(req_raddr), .req_rdata(req_rdata),
        .resp_we(resp_we), .resp_waddr(resp_waddr), .resp_wdata(resp_wdata),
        .resp_post(resp_post), .resp_len(resp_len));

    assign t35_irq_n_OUT = 1'b0;
    assign t35_irq_n_OE  = irq;

    // ---------------- PSRAM + BIST ----------------
    wire        p_req_valid, p_req_ready, p_req_write, p_wr_valid, p_wr_ready;
    wire        p_rd_valid, p_rd_ready, p_resp_valid, p_resp_ready;
    wire [22:0] p_req_addr;
    wire [8:0]  p_req_len;
    wire [7:0]  p_wr_data, p_rd_data;
    wire [2:0]  p_resp_status;

    psram_bist #(.BLOCKS(BIST_BLOCKS)) u_bist (
        .clk(sys_clk), .rst(rst_sys), .start(bist_start),
        .busy(bist_busy), .pass(bist_pass), .fail(bist_fail), .errs(bist_errs),
        .req_valid(p_req_valid), .req_ready(p_req_ready), .req_write(p_req_write),
        .req_addr(p_req_addr), .req_len(p_req_len),
        .wr_valid(p_wr_valid), .wr_ready(p_wr_ready), .wr_data(p_wr_data),
        .rd_valid(p_rd_valid), .rd_ready(p_rd_ready), .rd_data(p_rd_data),
        .resp_valid(p_resp_valid), .resp_ready(p_resp_ready), .resp_status(p_resp_status));

    psram_user_port #(.MCLK_HZ(MCLK_HZ), .CLK_DIV(1), .BUF_BYTES(256), .TCEM_NS(8000),
                      .UTIMEOUT(SYS_HZ / 1000)) u_psram (
        .uclk(sys_clk), .urst(rst_sys),
        .req_valid(p_req_valid), .req_ready(p_req_ready), .req_write(p_req_write),
        .req_addr(p_req_addr), .req_len(p_req_len),
        .wr_valid(p_wr_valid), .wr_ready(p_wr_ready), .wr_data(p_wr_data),
        .rd_valid(p_rd_valid), .rd_ready(p_rd_ready), .rd_data(p_rd_data),
        .resp_valid(p_resp_valid), .resp_ready(p_resp_ready), .resp_status(p_resp_status),
        .recover(psram_recover), .ram_ready(ram_ready), .ram_error(ram_error), .ram_err_code(ram_err_code),
        .mclk(psram_mclk), .mrst(guard_core_rst), .dbg_freeze(1'b0),
        .psram_ce_n(c_ce_n), .psram_sclk(c_sclk),
        .psram_dq_o(c_dq_o), .psram_dq_oe(c_dq_oe), .psram_dq_i(psram_sio_IN));

    // ---------------- R08 PSRAM power guard ----------------
    psram_power_guard #(.PG_STABLE(64)) u_guard (
        .mclk(psram_mclk), .rst(rst_mem), .pg_raw(psram_pg_IN & psram_pwr_en_IN),
        .on(guard_on), .core_rst(guard_core_rst),
        .c_ce_n(c_ce_n), .c_sclk(c_sclk), .c_dq_o(c_dq_o), .c_dq_oe(c_dq_oe),
        .p_ce_n_o(psram_ce_n), .p_ce_n_oe(psram_ce_n_OE), .p_sclk_o(psram_sclk),
        .p_dq_o(psram_sio_OUT), .p_dq_oe(psram_sio_OE));
    reg [1:0] guard_on_sync = 2'b00;
    always @(posedge sys_clk) guard_on_sync <= {guard_on_sync[0], guard_on};
    assign guard_on_sys = guard_on_sync[1];

    // ---------------- debug ----------------
    reg [25:0] hb = 26'd0;
    always @(posedge sys_clk) hb <= hb + 26'd1;
    assign t35_led0   = ram_ready ? hb[25] : (guard_on ? hb[22] : hb[20]);   // slow = ready, fast = init, very fast = PSRAM off
    assign t35_dbg_tx = 1'b1;                          // UART idle (not implemented in R06)
endmodule
