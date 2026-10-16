// ARC-1 R10 -- LFE5U-45F graphics FPGA top (decision D1): D213 GMAC0 RGMII <-> RJOB/RRES raster engine.
// RGMII endpoint = R8.5-C eth_link/rgmii_rx/rgmii_tx/eth_tx_pump (via fpga12/rtl, unchanged); mailbox job source tied
// off. Pins: R8.5-C 45F bank-0 RGMII plan (rxc on PCLKT0_0 B11), constraints/r10_45f.lpf.
// Evidence: RTL_SIMULATED (tb_r10_45f) + open-toolchain P&R. Not on silicon.
`default_nettype none
module r10_raster_top (
    input  wire       clk_25m,
    input  wire       rgmii_rxc,
    input  wire [3:0] rgmii_rxd,
    input  wire       rgmii_rx_ctl,
    output wire       rgmii_txc,
    output wire [3:0] rgmii_txd,
    output wire       rgmii_tx_ctl,
    output wire       led
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
    r10_raster_engine u_eng (
        .clk(sys_clk), .rst(rst), .job_valid(job_valid), .job_len(job_len), .idle(eng_idle),
        .req_raddr(req_raddr), .req_rdata(req_rdata),
        .resp_we(resp_we), .resp_waddr(resp_waddr), .resp_wdata(resp_wdata),
        .resp_post(resp_post), .resp_len(resp_len), .eth_counters(counters), .perf_jobs(perf_jobs));
    reg [25:0] hb = 26'd0;
    always @(posedge sys_clk) hb <= hb + 26'd1;
    assign led = hb[25] & eth_locked;
    wire unused_ok = &{1'b0, unused_mclk, u_we, u_post, perf_jobs, c_ok, c_fcs, c_drop, c_other, c_tx, c_under};
endmodule
`default_nettype wire
