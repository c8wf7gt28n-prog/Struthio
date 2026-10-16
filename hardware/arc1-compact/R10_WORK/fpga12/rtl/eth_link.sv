// ARC-1 Compact R8.5-C -- RGMII job link glue + job-source arbiter (sys clock domain).
// * RX buffer (8 KiB, write rxc / read sys, EBR); TX buffer in eth_tx_pump (sys domain, EBR) feeding
//   rgmii_tx through a 16-entry async FIFO (no EBR in the 125 MHz domain).
// * Two job sources share accel_engine: the SPI mailbox (mbx_regs_r85 doorbell pulse, latched here) and
//   accepted Ethernet frames. Grant only while the engine is idle; mailbox first on a tie.
// * Ethernet job: the engine reads the RX buffer; its response bytes go to the TX buffer and the response
//   is sent as a frame to the requester's MAC, then the RX buffer is released. Mailbox jobs are unchanged.
// * A new Ethernet job is not granted until the previous response frame has left (TX buffer free).
// Evidence: RTL_SIMULATED (tb_ecp5_top over a host EMAC model).
`default_nettype none
module eth_link (
    input  wire        clk,
    input  wire        rst,
    // RGMII pads
    input  wire        rgmii_rxc,
    input  wire [3:0]  rgmii_rxd,
    input  wire        rgmii_rx_ctl,
    input  wire        txc,                // 125 MHz from arc1_eth_pll
    output wire        rgmii_txc,
    output wire [3:0]  rgmii_txd,
    output wire        rgmii_tx_ctl,
    // mailbox side (mbx_regs_r85)
    input  wire        mbx_job_valid,      // pulse
    input  wire [15:0] mbx_job_len,
    input  wire [7:0]  mbx_req_rdata,
    output wire        mbx_resp_we,
    output wire        mbx_resp_post,
    // engine side (accel_engine)
    input  wire        eng_idle,
    output reg         eng_job_valid,
    output reg  [15:0] eng_job_len,
    input  wire [12:0] eng_req_raddr,
    output wire [7:0]  eng_req_rdata,
    input  wire        eng_resp_we,
    input  wire [12:0] eng_resp_waddr,
    input  wire [7:0]  eng_resp_wdata,
    input  wire        eng_resp_post,
    input  wire [15:0] eng_resp_len,
    // status (sys domain; counters are quasi-static, read by software twice for consistency)
    output wire [15:0] cnt_rx_ok, cnt_rx_crc, cnt_rx_drop, cnt_rx_other,
    output reg  [15:0] cnt_tx,
    output wire [15:0] cnt_tx_underrun,
    output reg  [95:0] counters_sys      // all six counters in the sys domain (2-FF per bit; read twice)
);
    // ---------------- receive ----------------
    wire        rx_we, rx_frame_tgl;
    wire [12:0] rx_waddr;
    wire [7:0]  rx_wdata;
    wire [15:0] rx_len;
    wire [47:0] rx_src;
    reg         release_tgl;
    rgmii_rx u_rx (
        .rxc(rgmii_rxc), .rxd(rgmii_rxd), .rx_ctl(rgmii_rx_ctl), .release_tgl(release_tgl),
        .buf_we(rx_we), .buf_waddr(rx_waddr), .buf_wdata(rx_wdata),
        .frame_tgl(rx_frame_tgl), .frame_len(rx_len), .src_mac(rx_src),
        .cnt_ok(cnt_rx_ok), .cnt_crc(cnt_rx_crc), .cnt_drop(cnt_rx_drop), .cnt_other(cnt_rx_other));
    reg [7:0] rxbuf [0:8191];
    reg [7:0] rx_q;
    always @(posedge rgmii_rxc) if (rx_we) rxbuf[rx_waddr] <= rx_wdata;
    always @(posedge clk) rx_q <= rxbuf[eng_req_raddr];

    // ---------------- transmit ----------------
    reg         tx_go;
    reg  [15:0] tx_len;
    reg  [47:0] tx_dst;
    wire        tx_start_tgl, tx_done_tgl, f_valid, f_pop;
    wire [15:0] f_data;
    reg         src_eth;
    eth_tx_pump u_pump (
        .clk(clk), .rst(rst), .we(eng_resp_we & src_eth), .waddr(eng_resp_waddr), .wdata(eng_resp_wdata),
        .start(tx_go), .len(tx_len), .tx_start_tgl(tx_start_tgl),
        .txc(txc), .f_valid(f_valid), .f_data(f_data), .f_pop(f_pop));
    rgmii_tx u_tx (
        .txc(txc), .start_tgl(tx_start_tgl), .tx_len(tx_len), .dst_mac(tx_dst),
        .f_valid(f_valid), .f_data(f_data), .f_pop(f_pop), .cnt_underrun(cnt_tx_underrun), .done_tgl(tx_done_tgl),
        .rgmii_txc(rgmii_txc), .rgmii_txd(rgmii_txd), .rgmii_tx_ctl(rgmii_tx_ctl));

    // ---------------- counters into the sys domain ----------------
    reg [95:0] cnt_s1;
    always @(posedge clk) begin
        cnt_s1       <= {cnt_tx_underrun, cnt_tx, cnt_rx_other, cnt_rx_drop, cnt_rx_crc, cnt_rx_ok};
        counters_sys <= cnt_s1;
    end

    // ---------------- arbiter ----------------
    reg [2:0]  fr_s, dn_s;
    reg        mbx_pend, eth_pend, active, tx_busy;
    reg [15:0] mbx_len_q;
    assign eng_req_rdata = src_eth ? rx_q : mbx_req_rdata;
    assign mbx_resp_we   = eng_resp_we   & ~src_eth;
    assign mbx_resp_post = eng_resp_post & ~src_eth;

    always @(posedge clk) begin
        fr_s <= {fr_s[1:0], rx_frame_tgl};
        dn_s <= {dn_s[1:0], tx_done_tgl};
        eng_job_valid <= 1'b0;
        tx_go <= 1'b0;
        if (rst) begin
            mbx_pend <= 1'b0; eth_pend <= 1'b0; src_eth <= 1'b0; active <= 1'b0; tx_busy <= 1'b0;
            release_tgl <= 1'b0; cnt_tx <= 16'd0;
            fr_s <= 3'b000; dn_s <= 3'b000;
        end else begin
            if (mbx_job_valid) begin mbx_pend <= 1'b1; mbx_len_q <= mbx_job_len; end
            if (fr_s[2] != fr_s[1]) eth_pend <= 1'b1;               // rx_len/rx_src stable while owned
            if (dn_s[2] != dn_s[1]) begin tx_busy <= 1'b0; cnt_tx <= cnt_tx + 16'd1; end
            if (!active && eng_idle && !eng_job_valid) begin
                if (mbx_pend && !mbx_job_valid) begin
                    mbx_pend <= 1'b0; src_eth <= 1'b0; active <= 1'b1;
                    eng_job_valid <= 1'b1; eng_job_len <= mbx_len_q;
                end else if (eth_pend && !tx_busy) begin
                    eth_pend <= 1'b0; src_eth <= 1'b1; active <= 1'b1;
                    eng_job_valid <= 1'b1; eng_job_len <= rx_len;
                end
            end
            if (active && eng_resp_post) begin
                active <= 1'b0;
                if (src_eth) begin
                    tx_len <= eng_resp_len; tx_dst <= rx_src;
                    tx_go <= 1'b1; tx_busy <= 1'b1;
                    release_tgl <= ~release_tgl;
                end
            end
        end
    end
endmodule
`default_nettype wire
