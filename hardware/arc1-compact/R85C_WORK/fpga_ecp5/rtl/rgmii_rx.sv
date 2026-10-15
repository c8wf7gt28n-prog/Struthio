// ARC-1 Compact R8.5-C -- RGMII receive MAC (raw frames, no PHY): F133 EMAC -> ECP5.
// rxc = F133 RGMII-TXCK (125 MHz); data centred by the F133 transmit delay chain (D1-H UM EMAC ETXDC, F133 DS
// Table 5-21 "transmitter integrated delay"). Nibbles: rising edge = bits [3:0], falling edge = bits [7:4];
// CTL rising = DV, CTL falling = DV ^ ER. Frame: 7x55 D5 | dst(6) src(6) type(2) | payload | FCS(4).
// Accepted: FCS good (CRC-32 residue 0xDEBB20E3), no RX_ER, EtherType 0x88B5, payload = len16 LE + len bytes,
// len <= 8192, buffer free. Payload bytes after len16 are written to the 8 KiB RX buffer (rxc domain port).
// Every frame outcome is counted. Evidence: RTL_SIMULATED; ECP5 primitive semantics per sim/ecp5_ddr_sim.v.
`default_nettype none
module rgmii_rx (
    input  wire        rxc,
    input  wire [3:0]  rxd,
    input  wire        rx_ctl,
    input  wire        release_tgl,     // sys toggles when it has finished with the buffer (synchronised here)
    output reg         buf_we,
    output reg  [12:0] buf_waddr,
    output reg  [7:0]  buf_wdata,
    output reg         frame_tgl,       // toggles once per accepted frame (len/src_mac stable until next toggle)
    output reg  [15:0] frame_len,
    output reg  [47:0] src_mac,
    output reg  [15:0] cnt_ok, cnt_crc, cnt_drop, cnt_other
);
    wire [3:0] lo, hi;
    wire       dv, dvxer;
    genvar i;
    generate for (i = 0; i < 4; i = i + 1) begin : g_dd
        IDDRX1F u (.D(rxd[i]), .SCLK(rxc), .RST(1'b0), .Q0(lo[i]), .Q1(hi[i]));
    end endgenerate
    IDDRX1F u_ctl (.D(rx_ctl), .SCLK(rxc), .RST(1'b0), .Q0(dv), .Q1(dvxer));
    // one register stage after the IOL DDR flip-flops (R8.5-C timing: IOL -> fabric routing is long)
    reg  [7:0] b = 8'h00;
    reg        dvr = 1'b0, er = 1'b0, is_sfd = 1'b0, is_pre = 1'b0;   // byte compares done in the input stage
    always @(posedge rxc) begin
        b <= {hi, lo}; dvr <= dv; er <= dv ^ dvxer;
        is_sfd <= ({hi, lo} == 8'hD5); is_pre <= ({hi, lo} == 8'h55);
    end

    function automatic [31:0] crc8(input [31:0] c, input [7:0] d);
        integer k;
        reg [31:0] x;
        begin
            x = c ^ {24'd0, d};
            for (k = 0; k < 8; k = k + 1) x = x[0] ? (x >> 1) ^ 32'hEDB88320 : (x >> 1);
            crc8 = x;
        end
    endfunction

    // 125 MHz structure (R8.5-C timing): one-hot control, header counter / CRC / flags cleared continuously
    // outside DATA (single-flag clear), separate payload counter, flags precomputed during the frame,
    // end-of-frame verdict one clock after DV falls (DECIDE).
    reg [2:0]  rel_s;
    reg        own;                   // buffer holds an accepted frame not yet released by sys
    reg        skip;                  // this frame started while the buffer was owned: drop it whole
    reg        s_hunt, s_data, s_wait, s_dec;   // one-hot
    reg [4:0]  hcnt;                  // header bytes seen (0..16, saturating)
    reg [13:0] dcnt;                  // bytes after the 16-byte header (payload + pad + FCS), saturating
    reg [31:0] crc;
    reg        bad, type_ok, len_ok;
    reg [15:0] len;
    reg [14:0] need;                  // len + 4 (payload + FCS must fit in the frame)
    reg [47:0] src;
    reg        e_crc, e_len;
    initial begin
        s_hunt = 1'b1; s_data = 1'b0; s_wait = 1'b0; s_dec = 1'b0;
        frame_tgl = 1'b0; own = 1'b0; rel_s = 3'b000; buf_we = 1'b0;
        cnt_ok = 0; cnt_crc = 0; cnt_drop = 0; cnt_other = 0;
    end
    always @(posedge rxc) begin
        rel_s <= {rel_s[1:0], release_tgl};
        if (rel_s[2] != rel_s[1]) own <= 1'b0;
        buf_we <= 1'b0;
        if (!s_data) begin                                      // hunting / waiting / deciding
            hcnt <= 5'd0; crc <= 32'hFFFFFFFF; bad <= er; skip <= own;
        end
        if (s_hunt) begin
            if (dvr && is_sfd) begin s_hunt <= 1'b0; s_data <= 1'b1; end
            else if (dvr && !is_pre) begin s_hunt <= 1'b0; s_wait <= 1'b1; end
        end
        if (s_data) begin
            if (dvr) begin
                crc <= crc8(crc, b);
                if (er) bad <= 1'b1;
                if (!hcnt[4]) begin
                    hcnt <= hcnt + 5'd1;
                    dcnt <= 14'd0;
                    case (hcnt[3:0])
                    4'd6, 4'd7, 4'd8, 4'd9, 4'd10, 4'd11: src <= {src[39:0], b};
                    4'd12: type_ok <= (b == 8'h88);
                    4'd13: type_ok <= type_ok & (b == 8'hB5);
                    4'd14: len[7:0] <= b;
                    default: len[15:8] <= b;                    // 15
                    endcase
                end else begin
                    if (dcnt == 14'd0) begin
                        need   <= {1'b0, len[13:0]} + 15'd4;
                        len_ok <= (len[15:13] == 3'b000) || (len == 16'h2000);
                    end
                    if (!dcnt[13] && !skip) begin buf_we <= 1'b1; buf_waddr <= dcnt[12:0]; buf_wdata <= b; end
                    if (dcnt != 14'h3FFF) dcnt <= dcnt + 14'd1;
                end
            end else begin
                s_data <= 1'b0; s_dec <= 1'b1;
                e_crc <= (crc == 32'hDEBB20E3);
                e_len <= hcnt[4] && (need <= {1'b0, dcnt});
            end
        end
        if (s_dec) begin
            s_dec <= 1'b0;
            if (dvr) s_wait <= 1'b1; else s_hunt <= 1'b1;
            if (!e_crc) cnt_crc <= cnt_crc + 16'd1;
            else if (bad || !type_ok || !len_ok || !e_len) cnt_other <= cnt_other + 16'd1;
            else if (skip) cnt_drop <= cnt_drop + 16'd1;
            else begin
                frame_len <= len; src_mac <= src; frame_tgl <= ~frame_tgl; cnt_ok <= cnt_ok + 16'd1; own <= 1'b1;
            end
        end
        if (s_wait && !dvr) begin s_wait <= 1'b0; s_hunt <= 1'b1; end
    end
endmodule
`default_nettype wire
