// ARC-1 Compact R8.5-C -- RGMII transmit MAC (raw frames, no PHY): ECP5 -> F133 EMAC.
// txc = 125 MHz from arc1_eth_pll. Data, CTL and the forwarded clock all leave through ODDRX1F, so the
// clock edge is aligned with the data edge; the F133 receive delay chain (D1-H UM EMAC ERXDC) centres it.
// Frame: 7x55 D5 | dst(6) src 02:A1:C1:00:00:01 | type 88B5 | len16 LE | len bytes from the TX buffer |
// zero pad to the 60-byte minimum | FCS | 12-byte inter-frame gap. start_tgl (sys) -> done_tgl (txc).
// TX buffer read port: buf_raddr is combinational, buf_rdata registered one txc later (EBR).
// Evidence: RTL_SIMULATED; ECP5 primitive semantics per sim/ecp5_ddr_sim.v.
`default_nettype none
module rgmii_tx (
    input  wire        txc,
    input  wire        start_tgl,       // sys toggles after tx_len/dst_mac are stable and the buffer is written
    input  wire [15:0] tx_len,
    input  wire [47:0] dst_mac,
    output wire [12:0] buf_raddr,
    input  wire [7:0]  buf_rdata,
    output reg         done_tgl,
    output wire        rgmii_txc,
    output wire [3:0]  rgmii_txd,
    output wire        rgmii_tx_ctl
);
    localparam [47:0] SRC_MAC = 48'h02A1C1000001;
    function automatic [31:0] crc8(input [31:0] c, input [7:0] d);
        integer k;
        reg [31:0] x;
        begin
            x = c ^ {24'd0, d};
            for (k = 0; k < 8; k = k + 1) x = x[0] ? (x >> 1) ^ 32'hEDB88320 : (x >> 1);
            crc8 = x;
        end
    endfunction

    reg  [2:0]  st_s;                  // start_tgl synchroniser
    reg         act;
    reg  [15:0] pos, len, data_end;     // data_end = first FCS position
    reg  [47:0] dst;
    reg  [31:0] crc;
    reg  [7:0]  ob;                    // byte presented to the ODDRs this cycle
    reg         oen;
    initial begin st_s = 3'b000; act = 1'b0; done_tgl = 1'b0; oen = 1'b0; ob = 8'h00; pos = 16'd0; end

    assign buf_raddr = pos[12:0] - 13'd23;             // data for position pos+1 (payload starts at 24)

    reg [7:0] cur;
    always @* begin
        cur = 8'h00;
        if (pos < 16'd7) cur = 8'h55;
        else if (pos == 16'd7) cur = 8'hD5;
        else if (pos < 16'd14) cur = dst[16'd47 - (pos - 16'd8) * 16'd8 -: 8];
        else if (pos < 16'd20) cur = SRC_MAC[16'd47 - (pos - 16'd14) * 16'd8 -: 8];
        else if (pos == 16'd20) cur = 8'h88;
        else if (pos == 16'd21) cur = 8'hB5;
        else if (pos == 16'd22) cur = len[7:0];
        else if (pos == 16'd23) cur = len[15:8];
        else if (pos < 16'd24 + len) cur = buf_rdata;
    end

    always @(posedge txc) begin
        st_s <= {st_s[1:0], start_tgl};
        if (!act) begin
            oen <= 1'b0; ob <= 8'h00;
            if (st_s[2] != st_s[1]) begin
                act <= 1'b1; pos <= 16'd0; len <= tx_len; dst <= dst_mac;
                data_end <= (tx_len + 16'd24 < 16'd68) ? 16'd68 : tx_len + 16'd24;
                crc <= 32'hFFFFFFFF;
            end
        end else begin
            pos <= pos + 16'd1;
            if (pos < data_end) begin
                oen <= 1'b1; ob <= cur;
                if (pos >= 16'd8) crc <= crc8(crc, cur);
            end else if (pos < data_end + 16'd4) begin
                oen <= 1'b1;
                case (pos - data_end)
                16'd0:   ob <= ~crc[7:0];
                16'd1:   ob <= ~crc[15:8];
                16'd2:   ob <= ~crc[23:16];
                default: ob <= ~crc[31:24];
                endcase
            end else begin
                oen <= 1'b0; ob <= 8'h00;
                if (pos == data_end + 16'd4 + 16'd12) begin act <= 1'b0; done_tgl <= ~done_tgl; end
            end
        end
    end

    genvar i;
    generate for (i = 0; i < 4; i = i + 1) begin : g_dd
        ODDRX1F u (.SCLK(txc), .RST(1'b0), .D0(ob[i]), .D1(ob[i + 4]), .Q(rgmii_txd[i]));
    end endgenerate
    ODDRX1F u_ctl (.SCLK(txc), .RST(1'b0), .D0(oen), .D1(oen), .Q(rgmii_tx_ctl));
    ODDRX1F u_ck  (.SCLK(txc), .RST(1'b0), .D0(1'b1), .D1(1'b0), .Q(rgmii_txc));
endmodule
`default_nettype wire
