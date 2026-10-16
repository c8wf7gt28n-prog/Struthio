// ARC-1 R10 -- LFE5U-12F F133-support FPGA (R10 spec section 6): RGMII job endpoint, bounded math jobs, health/
// self-test register (AJOB opcode 0x10 STATUS) and performance counters. NO external memory of any kind: every queue
// and buffer is EBR or distributed RAM (R10 6.3 gate "No memory chip").
//
// Derived from R85C_WORK/fpga_ecp5 (0defcfe) as reference only (R10 6.3): rgmii_rx/rgmii_tx/eth_tx_pump/eth_link
// unchanged; the SPI mailbox, PSRAM controller/BIST and power guard are removed; accel_engine gains HAS_FIR and STATUS.
// Configuration stays on the dedicated sysCONFIG pins (slave SPI from the F133 or a config NOR: R10 4 / 5, open).
// Increment order (R10 6.3 migration rule): STEP 1 protocol core (HAS_TRANSFORM = 0 is not offered: the engine always
// contains the R05 transform, 8 MULT18X18D), STEP 2 + FIR only if HAS_FIR fits (32 MULT18X18D > 28 on the 12F: off).
// Evidence: RTL_SIMULATED (tb_r10_support) + open-toolchain P&R on the LFE5U-12F die (fpga12/timing). Not on silicon.
`default_nettype none
module r10_support_top #(
    parameter integer HAS_FIR = 0,
    parameter [15:0]  IF_REV  = 16'h0001
) (
    input  wire       clk_25m,
    // RGMII to the F133 EMAC (F133 transmit -> rgmii_rx*, F133 receive <- rgmii_tx*)
    input  wire       rgmii_rxc,
    input  wire [3:0] rgmii_rxd,
    input  wire       rgmii_rx_ctl,
    output wire       rgmii_txc,
    output wire [3:0] rgmii_txd,
    output wire       rgmii_tx_ctl,
    // diagnostics
    output wire       led,
    output wire       irq_n            // open drain: low while the health word reports a fault (TX underrun)
);
    wire sys_clk, unused_mclk, pll_locked;
    arc1_ecp5_pll u_pll (.clk_25m(clk_25m), .sys_clk(sys_clk), .psram_mclk(unused_mclk), .locked(pll_locked));
    wire eth_txclk, eth_locked;
    arc1_eth_pll u_eth_pll (.clk_25m(clk_25m), .eth_txclk(eth_txclk), .locked(eth_locked));

    reg [3:0] rst_sr = 4'hF;
    always @(posedge sys_clk or negedge pll_locked)
        if (!pll_locked) rst_sr <= 4'hF; else rst_sr <= {rst_sr[2:0], 1'b0};
    wire rst = rst_sr[3];

    // ---------------- RGMII link (R8.5-C eth_link; the mailbox job source is tied off) ----------------
    wire        job_valid, resp_we, resp_post, eng_idle;
    wire [15:0] job_len, resp_len;
    wire [12:0] req_raddr, resp_waddr;
    wire [7:0]  req_rdata, resp_wdata, last_status;
    wire [15:0] c_ok, c_fcs, c_drop, c_other, c_tx, c_under;
    wire [95:0] counters;
    wire        unused_mbx_we, unused_mbx_post;
    eth_link u_eth (
        .clk(sys_clk), .rst(rst),
        .rgmii_rxc(rgmii_rxc), .rgmii_rxd(rgmii_rxd), .rgmii_rx_ctl(rgmii_rx_ctl),
        .txc(eth_txclk), .rgmii_txc(rgmii_txc), .rgmii_txd(rgmii_txd), .rgmii_tx_ctl(rgmii_tx_ctl),
        .mbx_job_valid(1'b0), .mbx_job_len(16'd0), .mbx_req_rdata(8'd0),
        .mbx_resp_we(unused_mbx_we), .mbx_resp_post(unused_mbx_post),
        .eng_idle(eng_idle), .eng_job_valid(job_valid), .eng_job_len(job_len),
        .eng_req_raddr(req_raddr), .eng_req_rdata(req_rdata),
        .eng_resp_we(resp_we), .eng_resp_waddr(resp_waddr), .eng_resp_wdata(resp_wdata),
        .eng_resp_post(resp_post), .eng_resp_len(resp_len),
        .cnt_rx_ok(c_ok), .cnt_rx_crc(c_fcs), .cnt_rx_drop(c_drop), .cnt_rx_other(c_other),
        .cnt_tx(c_tx), .cnt_tx_underrun(c_under), .counters_sys(counters));

    // ---------------- health / performance (STATUS payload, 32 bytes LE) ----------------
    wire [31:0] perf_cycles, perf_jobs, perf_items;
    reg  [16:0] ms_div = 17'd0;
    reg  [31:0] uptime_ms = 32'd0;
    always @(posedge sys_clk) begin
        if (rst) begin ms_div <= 17'd0; uptime_ms <= 32'd0; end
        else if (ms_div == 17'd79999) begin ms_div <= 17'd0; uptime_ms <= uptime_ms + 32'd1; end
        else ms_div <= ms_div + 17'd1;
    end
    wire [15:0] caps = {13'd0, 1'b1 /* b2 RGMII */, (HAS_FIR != 0) /* b1 FIR */, 1'b1 /* b0 transform */};
    // bytes 0..3 "R10S", 4..5 IF_REV, 6..7 caps, 8..19 RGMII counters (rx_ok, rx_fcs, rx_drop, rx_other, tx, tx_underrun),
    // 20..23 perf_jobs, 24..27 perf_items, 28..31 uptime_ms
    wire [255:0] status_words = {uptime_ms, perf_items, perf_jobs, counters, caps, IF_REV, 8'h53, 8'h30, 8'h31, 8'h52};

    accel_engine #(.HAS_FIR(HAS_FIR)) u_eng (
        .clk(sys_clk), .rst(rst), .abort(1'b0), .job_valid(job_valid), .job_len(job_len), .idle(eng_idle),
        .req_raddr(req_raddr), .req_rdata(req_rdata),
        .resp_we(resp_we), .resp_waddr(resp_waddr), .resp_wdata(resp_wdata),
        .resp_post(resp_post), .resp_len(resp_len),
        .perf_last_cycles(perf_cycles), .perf_jobs(perf_jobs), .perf_items(perf_items), .last_status(last_status),
        .status_words(status_words));

    reg [25:0] hb = 26'd0;
    always @(posedge sys_clk) hb <= hb + 26'd1;
    assign led   = hb[25] & eth_locked;
    assign irq_n = (counters[95:80] != 16'd0) ? 1'b0 : 1'bz;
    wire unused_ok = &{1'b0, unused_mclk, unused_mbx_we, unused_mbx_post, perf_cycles, last_status,
                       c_ok, c_fcs, c_drop, c_other, c_tx, c_under};
endmodule
`default_nettype wire
