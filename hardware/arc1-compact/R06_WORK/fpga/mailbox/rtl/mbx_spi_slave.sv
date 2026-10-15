// ARC-1 Compact R06 -- F133 -> T35 mailbox: oversampled SPI mode-0 slave.
// Evidence level: RTL_SIMULATED only.
//
// SCK/SS_N/MOSI are synchronised into `clk` (2 FF + edge detector), so the
// SPI clock must satisfy f_SCK <= f_clk / 8 (tested at /8 and /16).
// MISO is driven only while SS_N is (synchronously) low and is tri-stated
// otherwise, so the line is free whenever the F133 is not selecting the T35.
// (F133 PC5 is also its BOOT-SEL1 strap pin; see the board plan.)
//
// Frame (one CS# low period):
//   write : 0x02, A[15:8], A[7:0], D0, D1, ...      (address auto-increments)
//   read  : 0x0B, A[15:8], A[7:0], dummy, D0, D1, ...
// Other command bytes are ignored until CS# rises. A CS# rise mid-byte
// discards the partial byte; nothing is written for it.
module mbx_spi_slave (
    input  wire        clk,
    input  wire        rst,
    input  wire        sck_i,
    input  wire        ss_n_i,
    input  wire        mosi_i,
    output reg         miso_o,
    output reg         miso_oe,
    // byte bus to the register file (read data valid 2 clk after bus_re)
    output reg  [15:0] bus_addr,
    output reg         bus_we,
    output reg  [7:0]  bus_wdata,
    output reg         bus_re,
    input  wire [7:0]  bus_rdata,
    output reg         frame_end      // pulse when CS# rises (for statistics)
);
    localparam [7:0] CMD_WRITE = 8'h02, CMD_READ = 8'h0B;
    localparam [2:0] F_CMD = 3'd0, F_A1 = 3'd1, F_A2 = 3'd2, F_DUMMY = 3'd3,
                     F_RD = 3'd4, F_WR = 3'd5, F_IGNORE = 3'd6;

    reg [2:0] sck_s, ss_s, mosi_s;
    always @(posedge clk) begin
        sck_s  <= {sck_s[1:0],  sck_i};
        ss_s   <= {ss_s[1:0],   ss_n_i};
        mosi_s <= {mosi_s[1:0], mosi_i};
    end
    wire active = !ss_s[1];
    wire rise   = active &&  sck_s[1] && !sck_s[2];

    reg [2:0]  f_state;
    reg [2:0]  bitcnt;
    reg [7:0]  rx_sr;
    reg [7:0]  cmd;
    reg [7:0]  tx_sr;
    reg [7:0]  tx_next;
    reg [1:0]  rd_pipe;        // bus read latency tracking

    wire [7:0] rx_byte = {rx_sr[6:0], mosi_s[1]};

    // MISO changes right after each (synchronised) SCK rise, i.e. 2-3 clk
    // after the master sampled the previous bit: setup to the next rise is
    // ~one SCK period minus 3 clk, hold is 2-3 clk (F133 needs 0.2 ns).
    always @(posedge clk) begin
        bus_we    <= 1'b0;
        bus_re    <= 1'b0;
        frame_end <= 1'b0;
        rd_pipe   <= {rd_pipe[0], bus_re};
        if (rd_pipe[1]) tx_next <= bus_rdata;
        if (rst) begin
            f_state   <= F_CMD;
            bitcnt    <= 3'd0;
            miso_o    <= 1'b0;
            miso_oe   <= 1'b0;
            tx_next   <= 8'h00;
            tx_sr     <= 8'h00;
            rd_pipe   <= 2'b00;
        end else begin
            miso_oe <= active;
            if (!active) begin
                f_state <= F_CMD;
                bitcnt  <= 3'd0;
                miso_o  <= 1'b0;
                if (ss_s[1] && !ss_s[2]) frame_end <= 1'b1;
            end else begin
                if (bus_we) bus_addr <= bus_addr + 16'd1;
                if (rise) begin
                    rx_sr  <= rx_byte;
                    bitcnt <= bitcnt + 3'd1;
                    // default: present the next bit of the current tx byte
                    miso_o <= tx_sr[7];
                    tx_sr  <= {tx_sr[6:0], 1'b0};
                    if (bitcnt == 3'd7) begin
                        case (f_state)
                        F_CMD: begin
                            cmd     <= rx_byte;
                            f_state <= (rx_byte == CMD_WRITE || rx_byte == CMD_READ) ? F_A1 : F_IGNORE;
                        end
                        F_A1: begin bus_addr[15:8] <= rx_byte; f_state <= F_A2; end
                        F_A2: begin
                            bus_addr[7:0] <= rx_byte;
                            if (cmd == CMD_READ) begin bus_re <= 1'b1; f_state <= F_DUMMY; end
                            else f_state <= F_WR;
                        end
                        F_DUMMY, F_RD: begin
                            // tx_next = data at bus_addr (prefetched 8 SCK earlier):
                            // its MSB goes out now, prefetch the following byte
                            miso_o   <= tx_next[7];
                            tx_sr    <= {tx_next[6:0], 1'b0};
                            bus_addr <= bus_addr + 16'd1;
                            bus_re   <= 1'b1;
                            f_state  <= F_RD;
                        end
                        F_WR: begin
                            bus_we    <= 1'b1;
                            bus_wdata <= rx_byte;
                        end
                        default: ;
                        endcase
                    end
                end
            end
        end
    end
endmodule
