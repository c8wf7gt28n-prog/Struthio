// ARC-1 R10 -- 45F graphics FPGA, MEMORY VARIANT (ARC1_MEMORY_R10 v0.1 s2.3): r10_raster_top + 32 MiB x16 SDR SDRAM
// controller (sdram_ctrl) with a power-on self test (sdram_bist). The rasterizer does not use the SDRAM yet (textures
// are R10 7.1 step 4): this top proves fit, timing and the pin plan (hardware/lpf/r10_45f_sdram.lpf), and reports the
// SDRAM state in STATUS caps: b1 SDRAM present, b2 init done, b3 self test passed, b4 self test failed.
// sd_clk = sys_clk inverted through an ODDRX1F (commands sampled mid-window; see sdram_ctrl.sv "read timing").
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
    wire sys_clk, unused_mclk, pll_locked, eth_txclk, eth_locked;
    arc1_ecp5_pll u_pll (.clk_25m(clk_25m), .sys_clk(sys_clk), .psram_mclk(unused_mclk), .locked(pll_locked));
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
    wire        sd_init, b_busy, b_pass, b_fail, cmd_valid, cmd_ready, cmd_write, cmd_err, wr_ready, rd_valid;
    wire [15:0] b_errs, wr_data, rd_data;
    wire [23:0] cmd_addr;
    wire [9:0]  cmd_len;
    wire [31:0] cnt_refresh;
    sdram_ctrl #(.CLK_MHZ(80), .CL(2)) u_sd (
        .clk(sys_clk), .rst(rst), .init_done(sd_init), .cmd_valid(cmd_valid), .cmd_ready(cmd_ready),
        .cmd_write(cmd_write), .cmd_addr(cmd_addr), .cmd_len(cmd_len), .cmd_err(cmd_err),
        .wr_valid(1'b1), .wr_ready(wr_ready), .wr_data(wr_data), .rd_valid(rd_valid), .rd_data(rd_data),
        .cnt_refresh(cnt_refresh),
        .sd_cke(sd_cke), .sd_cs_n(sd_cs_n), .sd_ras_n(sd_ras_n), .sd_cas_n(sd_cas_n), .sd_we_n(sd_we_n),
        .sd_ba(sd_ba), .sd_a(sd_a), .sd_dqm(sd_dqm), .sd_dq(sd_dq));
    sdram_bist #(.BURSTS(16)) u_bist (
        .clk(sys_clk), .rst(rst), .init_done(sd_init), .start(1'b0), .busy(b_busy), .pass(b_pass), .fail(b_fail),
        .errs(b_errs), .cmd_valid(cmd_valid), .cmd_ready(cmd_ready), .cmd_write(cmd_write), .cmd_addr(cmd_addr),
        .cmd_len(cmd_len), .wr_ready(wr_ready), .wr_data(wr_data), .rd_valid(rd_valid), .rd_data(rd_data));
    ODDRX1F u_sdclk (.D0(1'b0), .D1(1'b1), .SCLK(sys_clk), .RST(1'b0), .Q(sd_clk));

    r10_raster_engine u_eng (
        .clk(sys_clk), .rst(rst), .job_valid(job_valid), .job_len(job_len), .idle(eng_idle),
        .req_raddr(req_raddr), .req_rdata(req_rdata),
        .resp_we(resp_we), .resp_waddr(resp_waddr), .resp_wdata(resp_wdata),
        .resp_post(resp_post), .resp_len(resp_len), .eth_counters(counters),
        .ext_caps({11'd0, b_fail, b_pass, sd_init, 1'b1, 1'b0}), .perf_jobs(perf_jobs));
    reg [25:0] hb = 26'd0;
    always @(posedge sys_clk) hb <= hb + 26'd1;
    assign led = (hb[25] & eth_locked) | b_fail;
    wire unused_ok = &{1'b0, unused_mclk, u_we, u_post, perf_jobs, c_ok, c_fcs, c_drop, c_other, c_tx, c_under,
                       b_busy, b_errs, cmd_err, cnt_refresh};
endmodule
`default_nettype wire
