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
    wire [7:0] b  = {hi, lo};
    wire       er = dv ^ dvxer;

    function automatic [31:0] crc8(input [31:0] c, input [7:0] d);
        integer k;
        reg [31:0] x;
        begin
            x = c ^ {24'd0, d};
            for (k = 0; k < 8; k = k + 1) x = x[0] ? (x >> 1) ^ 32'hEDB88320 : (x >> 1);
            crc8 = x;
        end
    endfunction

    reg [2:0]  rel_s;
    reg        own;                   // buffer holds an accepted frame not yet released by sys
    reg        skip;                  // this frame started while the buffer was owned: drop it whole
    reg [1:0]  st;                    // 0 idle, 1 preamble, 2 frame, 3 wait for DV low
    reg [15:0] idx;                   // byte index after SFD
    reg [31:0] crc;
    reg        bad;
    reg [15:0] type_, len;
    reg [47:0] src;
    initial begin st = 2'd0; frame_tgl = 1'b0; own = 1'b0; rel_s = 3'b000; cnt_ok = 0; cnt_crc = 0; cnt_drop = 0; cnt_other = 0; buf_we = 1'b0; end
    always @(posedge rxc) begin
        rel_s <= {rel_s[1:0], release_tgl};
        if (rel_s[2] != rel_s[1]) own <= 1'b0;
        buf_we <= 1'b0;
        case (st)
        2'd0: if (dv) begin
                  st <= (b == 8'hD5) ? 2'd2 : 2'd1;
                  idx <= 16'd0; crc <= 32'hFFFFFFFF; bad <= er; skip <= own;
              end
        2'd1: if (!dv) st <= 2'd0;
              else if (b == 8'hD5) begin st <= 2'd2; idx <= 16'd0; crc <= 32'hFFFFFFFF; bad <= er; skip <= own; end
              else if (b != 8'h55) st <= 2'd3;
        2'd2: if (dv) begin
                  crc <= crc8(crc, b);
                  if (er) bad <= 1'b1;
                  if (idx >= 16'd6 && idx < 16'd12) src <= {src[39:0], b};
                  if (idx == 16'd12) type_[15:8] <= b;
                  if (idx == 16'd13) type_[7:0] <= b;
                  if (idx == 16'd14) len[7:0] <= b;
                  if (idx == 16'd15) len[15:8] <= b;
                  if (idx >= 16'd16 && idx < 16'd16 + 16'd8192 && !skip) begin
                      buf_we <= 1'b1; buf_waddr <= idx[12:0] - 13'd16; buf_wdata <= b;
                  end
                  if (idx != 16'hFFFF) idx <= idx + 16'd1;
              end else begin                                   // end of frame
                  st <= 2'd0;
                  if (crc != 32'hDEBB20E3) cnt_crc <= cnt_crc + 16'd1;
                  else if (bad || type_ != 16'h88B5 || idx < 16'd20 || len > 16'd8192 || {len + 16'd20} > idx)
                      cnt_other <= cnt_other + 16'd1;
                  else if (skip) cnt_drop <= cnt_drop + 16'd1;
                  else begin
                      frame_len <= len; src_mac <= src; frame_tgl <= ~frame_tgl; cnt_ok <= cnt_ok + 16'd1; own <= 1'b1;
                  end
              end
        default: if (!dv) st <= 2'd0;
        endcase
    end
endmodule
`default_nettype wire
