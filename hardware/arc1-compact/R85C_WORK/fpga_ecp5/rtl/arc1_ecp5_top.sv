// ARC-1 Compact R8.5-C -- LFE5U-45F-6BG381C top level (OPTIONAL accelerator FPGA): quad-SPI mailbox + resident FIR.
//
// Derived from R08_WORK/fpga/rtl/arc1_t35_top_r08.sv. Changes for ECP5 (vendor-neutral where possible):
//   * real tri-state pads at the top (Yosys/nextpnr-ecp5 map them to TRELLIS_IO); no
//     Efinity-style _IN/_OUT/_OE pad split
//   * PLL from ecppll (arc1_ecp5_pll.v): 25 MHz -> sys_clk 80 MHz, psram_mclk 40 MHz;
//     simulation uses a behavioural model (sim/arc1_ecp5_pll_sim.v)
//   * accel_engine (AJOB transform jobs + legacy loopback) replaces mbx_loopback
//   * AMBX v3 register file (perf counters, ABORT)
// The mailbox SPI pins are the ECP5 sysCONFIG slave-SPI pins after DONE: MOSI = D0 (W2),
// MISO = D1 (V2), CS = SN (T2); SCK reaches CCLK (U3, dedicated) and user pin R1 (same board net).
// Evidence level: RTL_SIMULATED (tb_ecp5_top) + Yosys/nextpnr-ecp5 routed build. Not on silicon.
module arc1_ecp5_top #(
    parameter integer SYS_HZ  = 80000000,
    parameter integer MCLK_HZ = 40000000,
    parameter integer BIST_BLOCKS = 64
) (
    input  wire       clk_25m,
    // F133 SPI0 operational link (R8.5-C: quad SPI through the board CB3Q3125 bus switch; IO0 = MOSI, IO1 = MISO)
    input  wire       spi_sck,
    input  wire       spi_cs_n,
    inout  wire       spi_mosi,
    inout  wire       spi_miso,
    inout  wire       spi_io2,
    inout  wire       spi_io3,
    inout  wire       irq_n,          // open drain
    // APS6404L PSRAM
    inout  wire       psram_ce_n,
    output wire       psram_sclk,
    inout  wire [3:0] psram_sio,
    input  wire       psram_pg,       // PSRAM_VDD supervisor (low = power bad)
    input  wire       psram_pwr_en,   // load-switch EN (F133 request & DONE_DLY)
    // debug
    output wire       led,
    output wire       dbg_tx,
    input  wire       dbg_rx
);
    wire sys_clk, psram_mclk, pll_locked;
    arc1_ecp5_pll u_pll (.clk_25m(clk_25m), .sys_clk(sys_clk), .psram_mclk(psram_mclk), .locked(pll_locked));

    // ---------------- resets ----------------
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
    wire [3:0]  q_o, q_oe;
    wire [3:0]  q_i = {spi_io3, spi_io2, spi_miso, spi_mosi};
    mbx_qspi_slave u_spi (
        .clk(sys_clk), .rst(rst_sys), .sck(spi_sck), .cs_n(spi_cs_n),
        .io_i(q_i), .io_o(q_o), .io_oe(q_oe),
        .bus_addr(bus_addr), .bus_we(bus_we), .bus_wdata(bus_wdata),
        .bus_re(bus_re), .bus_rdata(bus_rdata), .frame_end(frame_end));
    assign spi_mosi = q_oe[0] ? q_o[0] : 1'bz;
    assign spi_miso = q_oe[1] ? q_o[1] : 1'bz;
    assign spi_io2  = q_oe[2] ? q_o[2] : 1'bz;
    assign spi_io3  = q_oe[3] ? q_o[3] : 1'bz;

    wire        irq, job_valid, resp_we, resp_post, job_abort;
    wire [15:0] job_len, resp_len;
    wire [12:0] req_raddr, resp_waddr;
    wire [7:0]  req_rdata, resp_wdata, last_status;
    wire        ram_ready, ram_error, psram_recover, bist_start, bist_busy, bist_pass, bist_fail;
    wire [1:0]  ram_err_code;
    wire [31:0] bist_errs, perf_last_cycles, perf_jobs, perf_items;
    wire        guard_on, guard_on_sys, guard_core_rst, c_ce_n, c_sclk;
    wire [3:0]  c_dq_o, c_dq_oe;

    mbx_regs_r85 u_regs (
        .clk(sys_clk), .rst(rst_sys),
        .bus_addr(bus_addr), .bus_we(bus_we), .bus_wdata(bus_wdata), .bus_re(bus_re), .bus_rdata(bus_rdata),
        .irq(irq), .job_valid(job_valid), .job_len(job_len),
        .req_raddr(req_raddr), .req_rdata(req_rdata),
        .resp_we(resp_we), .resp_waddr(resp_waddr), .resp_wdata(resp_wdata),
        .resp_post(resp_post), .resp_len_in(resp_len),
        .psram_ready(ram_ready), .psram_error(ram_error), .psram_err_code(ram_err_code),
        .psram_recover(psram_recover), .bist_start(bist_start),
        .bist_busy(bist_busy), .bist_pass(bist_pass), .bist_fail(bist_fail), .bist_errs(bist_errs),
        .psram_power_on(guard_on_sys), .job_abort(job_abort),
        .perf_last_cycles(perf_last_cycles), .perf_jobs(perf_jobs), .perf_items(perf_items), .last_status(last_status));

    accel_engine u_eng (
        .clk(sys_clk), .rst(rst_sys), .abort(job_abort), .job_valid(job_valid), .job_len(job_len),
        .req_raddr(req_raddr), .req_rdata(req_rdata),
        .resp_we(resp_we), .resp_waddr(resp_waddr), .resp_wdata(resp_wdata),
        .resp_post(resp_post), .resp_len(resp_len),
        .perf_last_cycles(perf_last_cycles), .perf_jobs(perf_jobs), .perf_items(perf_items), .last_status(last_status));

    assign irq_n = irq ? 1'b0 : 1'bz;

    // ---------------- PSRAM + BIST (R06 controller, R08 guard; unchanged RTL) ----------------
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
    wire [3:0] sio_i = psram_sio;
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
        .psram_dq_o(c_dq_o), .psram_dq_oe(c_dq_oe), .psram_dq_i(sio_i));
    wire       p_ce_o, p_ce_oe;
    wire [3:0] p_dq_o, p_dq_oe;
    psram_power_guard #(.PG_STABLE(64)) u_guard (
        .mclk(psram_mclk), .rst(rst_mem), .pg_raw(psram_pg & psram_pwr_en),
        .on(guard_on), .core_rst(guard_core_rst),
        .c_ce_n(c_ce_n), .c_sclk(c_sclk), .c_dq_o(c_dq_o), .c_dq_oe(c_dq_oe),
        .p_ce_n_o(p_ce_o), .p_ce_n_oe(p_ce_oe), .p_sclk_o(psram_sclk),
        .p_dq_o(p_dq_o), .p_dq_oe(p_dq_oe));
    assign psram_ce_n = p_ce_oe ? p_ce_o : 1'bz;
    genvar g;
    generate for (g = 0; g < 4; g = g + 1) begin : g_sio
        assign psram_sio[g] = p_dq_oe[g] ? p_dq_o[g] : 1'bz;
    end endgenerate
    reg [1:0] guard_on_sync = 2'b00;
    always @(posedge sys_clk) guard_on_sync <= {guard_on_sync[0], guard_on};
    assign guard_on_sys = guard_on_sync[1];

    // ---------------- debug ----------------
    reg [25:0] hb = 26'd0;
    always @(posedge sys_clk) hb <= hb + 26'd1;
    assign led    = ram_ready ? hb[25] : (guard_on ? hb[22] : hb[20]);
    assign dbg_tx = 1'b1;                 // UART not implemented (reserved)
    wire unused_ok = &{1'b0, dbg_rx, frame_end};
endmodule
