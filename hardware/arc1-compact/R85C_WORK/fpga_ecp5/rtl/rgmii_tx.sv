// ARC-1 Compact R8.5-C -- RGMII transmit MAC (raw frames, no PHY): ECP5 -> F133 EMAC.
// txc = 125 MHz from arc1_eth_pll. Data, CTL and the forwarded clock all leave through ODDRX1F, so the
// clock edge is aligned with the data edge; the F133 receive delay chain (D1-H UM EMAC ERXDC) centres it.
// Frame: 7x55 D5 | dst(6) src 02:A1:C1:00:00:01 | type 88B5 | len16 LE | len bytes from the TX buffer |
// zero pad to the 60-byte minimum | FCS | 12-byte inter-frame gap. start_tgl (sys) -> done_tgl (txc).
// TX buffer read port: buf_raddr registered here, buf_rdata registered one txc later (EBR).
// 125 MHz structure (R8.5-C timing): phase state machine with small counters, header shift register,
// CRC over the registered output byte, first FCS byte from crc8(crc, last byte).
// Evidence: RTL_SIMULATED; ECP5 primitive semantics per sim/ecp5_ddr_sim.v.
`default_nettype none
module rgmii_tx (
    input  wire        txc,
    input  wire        start_tgl,       // sys toggles after tx_len/dst_mac are stable and the buffer is written
    input  wire [15:0] tx_len,
    input  wire [47:0] dst_mac,
    output reg  [12:0] buf_raddr,
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

    localparam [2:0] IDLE = 3'd0, PRE = 3'd1, HDR = 3'd2, PAY = 3'd3, PAD = 3'd4, FCS = 3'd5, IFG = 3'd6;
    reg  [2:0]   st_s;                 // start_tgl synchroniser
    reg  [2:0]   ph;
    reg  [3:0]   cnt;                  // preamble / header / FCS / IFG byte counter
    reg  [13:0]  rem;                  // payload bytes still to send
    reg  [5:0]   pad;                  // pad bytes after the payload (60-byte minimum frame)
    reg  [127:0] hsr;                  // dst | src | type | len16 LE, MSB first
    reg  [31:0]  crc;
    reg  [23:0]  fsr;                  // remaining FCS bytes
    reg  [7:0]   ob;                   // byte presented to the ODDRs
    reg          oen, incrc;
    wire [31:0]  crc_n = crc8(crc, ob);
    initial begin st_s = 3'b000; ph = IDLE; done_tgl = 1'b0; oen = 1'b0; incrc = 1'b0; ob = 8'h00; buf_raddr = 13'd0; end

    always @(posedge txc) begin
        st_s <= {st_s[1:0], start_tgl};
        if (incrc) crc <= crc_n;
        buf_raddr <= buf_raddr + 13'd1;
        case (ph)
        IDLE: begin
            oen <= 1'b0; ob <= 8'h00; incrc <= 1'b0; crc <= 32'hFFFFFFFF;
            if (st_s[2] != st_s[1]) begin
                ph <= PRE; cnt <= 4'd0;
                hsr <= {dst_mac, SRC_MAC, 16'h88B5, tx_len[7:0], tx_len[15:8]};
                rem <= tx_len[13:0];
                pad <= (tx_len < 16'd44) ? 6'd44 - tx_len[5:0] : 6'd0;
            end
        end
        PRE: begin
            oen <= 1'b1; ob <= (cnt == 4'd7) ? 8'hD5 : 8'h55; cnt <= cnt + 4'd1;
            if (cnt == 4'd7) begin ph <= HDR; cnt <= 4'd0; end
        end
        HDR: begin
            ob <= hsr[127:120]; hsr <= {hsr[119:0], 8'h00}; incrc <= 1'b1; cnt <= cnt + 4'd1;
            if (cnt == 4'd14) buf_raddr <= 13'd0;                 // payload byte 0 is needed two clocks later
            if (cnt == 4'd15) ph <= (rem != 14'd0) ? PAY : ((pad != 6'd0) ? PAD : FCS);
        end
        PAY: begin
            ob <= buf_rdata; rem <= rem - 14'd1;
            if (rem == 14'd1) ph <= (pad != 6'd0) ? PAD : FCS;
        end
        PAD: begin
            ob <= 8'h00; pad <= pad - 6'd1;
            if (pad == 6'd1) ph <= FCS;
            cnt <= 4'd0;
        end
        FCS: begin
            cnt <= cnt + 4'd1; incrc <= 1'b0;
            if (cnt == 4'd0) begin ob <= ~crc_n[7:0]; fsr <= ~crc_n[31:8]; end
            else begin ob <= fsr[7:0]; fsr <= {8'h00, fsr[23:8]}; end
            if (cnt == 4'd3) begin ph <= IFG; cnt <= 4'd0; end
        end
        IFG: begin
            oen <= 1'b0; ob <= 8'h00; cnt <= cnt + 4'd1;
            if (cnt == 4'd11) begin ph <= IDLE; done_tgl <= ~done_tgl; end
        end
        default: ph <= IDLE;
        endcase
    end

    genvar i;
    generate for (i = 0; i < 4; i = i + 1) begin : g_dd
        ODDRX1F u (.SCLK(txc), .RST(1'b0), .D0(ob[i]), .D1(ob[i + 4]), .Q(rgmii_txd[i]));
    end endgenerate
    ODDRX1F u_ctl (.SCLK(txc), .RST(1'b0), .D0(oen), .D1(oen), .Q(rgmii_tx_ctl));
    ODDRX1F u_ck  (.SCLK(txc), .RST(1'b0), .D0(1'b1), .D1(1'b0), .Q(rgmii_txc));
endmodule
`default_nettype wire
