// ARC-1 R10 -- 45F graphics FPGA, MEMORY VARIANT (ARC1_MEMORY_R10 v0.1 s2.3): r10_raster_top + 32 MiB x16 SDR SDRAM
// controller (sdram_ctrl) with a power-on self test (sdram_bist). The rasterizer does not use the SDRAM yet (textures
// are R10 7.1 step 4): this top proves fit, timing and the pin plan (hardware/lpf/r10_45f_sdram.lpf), and reports the
// SDRAM state in STATUS caps: b1 SDRAM present, b2 init done, b3 self test passed, b4 self test failed,
// b5 interface calibration done, b6 calibration failed, [12:7] calibration window width (phase steps).
// sd_clk comes from a phase-steppable PLL output (arc1_sd_pll) through an ODDRX1F; sdram_cal picks the phase and the
// capture latency at power-up (analysis/R10_SDRAM_TIMING.md), then sdram_bist runs.
// Evidence: RTL_SIMULATED (tb_r10_45f -DMEMTOP with sim/sdram_model.sv) + open-toolchain P&R. Not on silicon.
`default_nettype none
module r10_raster_mem_top (
    input  wire        clk_25m,
    input  wire        rgmii_rxc,
    input  wire [3:0]  rgmii_rxd,
    input  wire        rgmii_rx_ctl,
    output wire        rgmii_txc,
    output wire [3:0]  rgmii_txd,
    output wire        rgmii_tx_ctl,
    output wire        led,
    output wire        sd_clk,
    output wire        sd_cke,
    output wire        sd_cs_n,
    output wire        sd_ras_n,
    output wire        sd_cas_n,
    output wire        sd_we_n,
    output wire [1:0]  sd_ba,
    output wire [12:0] sd_a,
    output wire [1:0]  sd_dqm,
    inout  wire [15:0] sd_dq
);
    wire sys_clk, sd_clk_pll, pll_locked, eth_txclk, eth_locked, cal_step;
    arc1_sd_pll u_pll (.clk_25m(clk_25m), .phase_step(cal_step), .sys_clk(sys_clk), .sd_clk_pll(sd_clk_pll), .locked(pll_locked));
    arc1_eth_pll u_eth_pll (.clk_25m(clk_25m), .eth_txclk(eth_txclk), .locked(eth_locked));
    reg [3:0] rst_sr = 4'hF;
    always @(posedge sys_clk or negedge pll_locked)
        if (!pll_locked) rst_sr <= 4'hF; else rst_sr <= {rst_sr[2:0], 1'b0};
    wire rst = rst_sr[3];

    wire        job_valid, resp_we, resp_post, eng_idle, u_we, u_post;
    wire [15:0] job_len, resp_len, c_ok, c_fcs, c_drop, c_other, c_tx, c_under;
    wire [12:0] req_raddr, resp_waddr;
    wire [7:0]  req_rdata, resp_wdata;
    wire [95:0] counters;
    wire [31:0] perf_jobs;
    eth_link u_eth (
        .clk(sys_clk), .rst(rst),
        .rgmii_rxc(rgmii_rxc), .rgmii_rxd(rgmii_rxd), .rgmii_rx_ctl(rgmii_rx_ctl),
        .txc(eth_txclk), .rgmii_txc(rgmii_txc), .rgmii_txd(rgmii_txd), .rgmii_tx_ctl(rgmii_tx_ctl),
        .mbx_job_valid(1'b0), .mbx_job_len(16'd0), .mbx_req_rdata(8'd0), .mbx_resp_we(u_we), .mbx_resp_post(u_post),
        .eng_idle(eng_idle), .eng_job_valid(job_valid), .eng_job_len(job_len),
        .eng_req_raddr(req_raddr), .eng_req_rdata(req_rdata),
        .eng_resp_we(resp_we), .eng_resp_waddr(resp_waddr), .eng_resp_wdata(resp_wdata),
        .eng_resp_post(resp_post), .eng_resp_len(resp_len),
        .cnt_rx_ok(c_ok), .cnt_rx_crc(c_fcs), .cnt_rx_drop(c_drop), .cnt_rx_other(c_other),
        .cnt_tx(c_tx), .cnt_tx_underrun(c_under), .counters_sys(counters));

    // ---------------- SDRAM ----------------
    wire        sd_init, b_busy, b_pass, b_fail, cmd_ready, cmd_err, wr_ready, rd_valid;
    wire        b_valid, b_write, k_valid, k_write, cal_reinit, cal_extra, cal_busy, cal_done, cal_fail;
    wire [15:0] b_errs, b_wdata, k_wdata, rd_data;
    wire [23:0] b_addr, k_addr;
    wire [9:0]  b_len, k_len;
    wire [6:0]  cal_w, cal_c;
    wire        cal_owns = !cal_done;
    wire [31:0] cnt_refresh;
    sdram_cal #(.PHASES(56)) u_cal (
        .clk(sys_clk), .rst(rst), .init_done(sd_init), .reinit(cal_reinit), .rd_extra(cal_extra), .phase_step(cal_step),
        .busy(cal_busy), .done(cal_done), .fail(cal_fail), .win_width(cal_w), .win_center(cal_c),
        .cmd_valid(k_valid), .cmd_ready(cmd_ready), .cmd_write(k_write), .cmd_addr(k_addr), .cmd_len(k_len),
        .wr_ready(wr_ready), .wr_data(k_wdata), .rd_valid(rd_valid), .rd_data(rd_data));
    sdram_ctrl #(.CLK_MHZ(80), .CL(3)) u_sd (
        .clk(sys_clk), .rst(rst), .init_done(sd_init), .reinit(cal_owns & cal_reinit), .rd_extra(cal_extra),
        .cmd_valid(cal_owns ? k_valid : b_valid), .cmd_ready(cmd_ready),
        .cmd_write(cal_owns ? k_write : b_write), .cmd_addr(cal_owns ? k_addr : b_addr),
        .cmd_len(cal_owns ? k_len : b_len), .cmd_err(cmd_err),
        .wr_valid(1'b1), .wr_ready(wr_ready), .wr_data(cal_owns ? k_wdata : b_wdata), .rd_valid(rd_valid), .rd_data(rd_data),
        .cnt_refresh(cnt_refresh),
        .sd_cke(sd_cke), .sd_cs_n(sd_cs_n), .sd_ras_n(sd_ras_n), .sd_cas_n(sd_cas_n), .sd_we_n(sd_we_n),
        .sd_ba(sd_ba), .sd_a(sd_a), .sd_dqm(sd_dqm), .sd_dq(sd_dq));
    sdram_bist #(.BURSTS(16)) u_bist (
        .clk(sys_clk), .rst(rst), .init_done(sd_init & cal_done), .start(1'b0), .busy(b_busy), .pass(b_pass), .fail(b_fail),
        .errs(b_errs), .cmd_valid(b_valid), .cmd_ready(cmd_ready & !cal_owns), .cmd_write(b_write), .cmd_addr(b_addr),
        .cmd_len(b_len), .wr_ready(wr_ready & !cal_owns), .wr_data(b_wdata), .rd_valid(rd_valid & !cal_owns), .rd_data(rd_data));
    ODDRX1F u_sdclk (.D0(1'b1), .D1(1'b0), .SCLK(sd_clk_pll), .RST(1'b0), .Q(sd_clk));   // forwarded, phase from the PLL

    r10_raster_engine u_eng (
        .clk(sys_clk), .rst(rst), .job_valid(job_valid), .job_len(job_len), .idle(eng_idle),
        .req_raddr(req_raddr), .req_rdata(req_rdata),
        .resp_we(resp_we), .resp_waddr(resp_waddr), .resp_wdata(resp_wdata),
        .resp_post(resp_post), .resp_len(resp_len), .eth_counters(counters),
        .ext_caps({3'd0, cal_w[5:0], cal_fail, cal_done, b_fail, b_pass, sd_init, 1'b1, 1'b0}), .perf_jobs(perf_jobs));
    reg [25:0] hb = 26'd0;
    always @(posedge sys_clk) hb <= hb + 26'd1;
    assign led = (hb[25] & eth_locked) | b_fail;
    wire unused_ok = &{1'b0, cal_busy, cal_c, cal_w[6], u_we, u_post, perf_jobs, c_ok, c_fcs, c_drop, c_other, c_tx, c_under,
                       b_busy, b_errs, cmd_err, cnt_refresh};
endmodule
`default_nettype wire
