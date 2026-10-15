// ARC-1 Compact R8.5-C -- source-synchronous quad-SPI mailbox slave (replaces the oversampling R06 mbx_spi_slave).
//
// Matches the F133 (D1-family) SPI controller quad mode: command, address and dummy are sent 1-bit on IO0 (MOSI);
// only data uses IO[3:0] (D1-H UM 9.3.3.8). Mode 0, MSB first, high nibble first. Frames (one CS# low period):
//   0x02 A1 A0 D...             single write (R8.5-compatible)
//   0x0B A1 A0 <8 dummy> D...   single read  (R8.5-compatible; MISO = IO1)
//   0x32 A1 A0 D...             quad write   (data nibbles on IO[3:0])
//   0x6B A1 A0 <16 dummy> D...  quad read    (slave drives IO[3:0] from the first data clock)
// Clocking: SCK is a real clock (no oversampling). Received bytes cross to clk through an async FIFO; read data is
// prefetched in clk and crosses back through a second async FIFO (the dummy clocks cover the latency). Register
// reads have no side effects (mbx_regs_r85), so prefetching beyond the host's length is harmless.
// Host requirements: CS# high >= 4 clk periods (50 ns at 80 MHz) between frames.
// Evidence: RTL_SIMULATED (tb_ecp5_top) + routed build. Not on silicon.
`default_nettype none
/* verilator lint_off SYNCASYNCNET */   // intentional: CS#/rst are async resets of the SCK domain and sampled in clk
module mbx_qspi_slave (
    input  wire        clk,
    input  wire        rst,
    input  wire        sck,
    input  wire        cs_n,
    input  wire [3:0]  io_i,
    output reg  [3:0]  io_o,
    output reg  [3:0]  io_oe,
    output reg  [15:0] bus_addr,
    output reg         bus_we,
    output reg  [7:0]  bus_wdata,
    output reg         bus_re,
    input  wire [7:0]  bus_rdata,      // registered once in mbx_regs_r85: captured 2 clk after bus_re
    output reg         frame_end
);
    localparam [7:0] C_WR1 = 8'h02, C_RD1 = 8'h0B, C_WR4 = 8'h32, C_RD4 = 8'h6B;
    function automatic [4:0] g(input [4:0] b); g = b ^ (b >> 1); endfunction
    function automatic [4:0] bin(input [4:0] gg);
        integer i;
        begin bin[4] = gg[4]; for (i = 3; i >= 0; i = i - 1) bin[i] = bin[i + 1] ^ gg[i]; end
    endfunction

    // ===================== SCK domain, rising edge: receive (state reset while CS# is high) =====================
    reg [5:0]  ecnt;                 // rising edges in this frame, saturating at 63 (>= every data start)
    reg [2:0]  pc;                   // rising edges mod 8 (byte phase; all headers are byte aligned)
    reg [7:0]  sr;
    reg        quad, rd;
    wire       hdr      = ecnt < 6'd24;
    wire       rx1      = hdr || (!quad && !rd);               // 1-bit receive: header, single-write data
    wire       rx4      = !hdr && quad && !rd;                 // quad-write data
    wire [7:0] nx1      = {sr[6:0], io_i[0]};
    wire [7:0] nx4      = {sr[3:0], io_i};
    wire       done1    = !cs_n && rx1 && pc == 3'd7;
    wire       done4    = !cs_n && rx4 && pc[0] == 1'b1;
    wire       wpush    = done1 || done4;                     // a whole byte completes on THIS edge
    wire [8:0] wbyte    = {done1 && ecnt == 6'd7, done1 ? nx1 : nx4};
    always @(posedge sck or posedge cs_n) begin
        if (cs_n) begin
            ecnt <= 6'd0; pc <= 3'd0; quad <= 1'b0; rd <= 1'b0; sr <= 8'd0;
        end else begin
            if (ecnt != 6'd63) ecnt <= ecnt + 6'd1;
            pc <= pc + 3'd1;
            if (rx1) sr <= nx1; else if (rx4) sr <= nx4;
            if (ecnt == 6'd7) begin
                quad <= nx1 == C_WR4 || nx1 == C_RD4;
                rd   <= nx1 == C_RD1 || nx1 == C_RD4;
            end
        end
    end
    // async FIFO SCK -> clk; written on the edge that completes a byte (no extra edge needed), never reset by CS#
    reg [8:0]  wf_mem [0:15];
    reg [4:0]  wf_wp, wf_wp_g;
    always @(posedge sck or posedge rst) begin
        if (rst) begin wf_wp <= 5'd0; wf_wp_g <= 5'd0; end
        else if (wpush) begin
            wf_wp   <= wf_wp + 5'd1;
            wf_wp_g <= g(wf_wp + 5'd1);
        end
    end
    always @(posedge sck) if (wpush) wf_mem[wf_wp[3:0]] <= wbyte;

    // ===================== SCK domain, falling edge: transmit =====================
    reg [7:0]  rf_mem [0:15];
    reg [4:0]  rf_wp_g;              // clk domain, gray
    reg [4:0]  rf_rp, rf_rp_g, rf_wp_s1, rf_wp_s2;
    reg [7:0]  tx;
    wire [5:0] dstart = quad ? 6'd40 : 6'd32;
    wire       rd_data = rd && ecnt >= dstart;                 // the next rising edge carries read data
    wire       need    = quad ? (pc[0] == 1'b0) : (pc == 3'd0);
    wire       avail   = rf_wp_s2 != rf_rp_g;
    wire [7:0] cur     = need ? (avail ? rf_mem[rf_rp[3:0]] : 8'hFF) : tx;   // underrun -> 0xFF (CRC catches it)
    reg rst_s1, rst_s2;                                            // clk-domain reset seen at the SCK falling edge
    always @(negedge sck or posedge rst) if (rst) begin rst_s1 <= 1'b1; rst_s2 <= 1'b1; end else begin rst_s1 <= 1'b0; rst_s2 <= rst_s1; end
    initial begin io_oe = 4'b0000; io_o = 4'b0000; end
    always @(negedge sck or posedge cs_n) begin
        if (cs_n) begin
            io_oe <= 4'b0000; io_o <= 4'b0000; tx <= 8'hFF;
            rf_rp <= 5'd0; rf_rp_g <= 5'd0; rf_wp_s1 <= 5'd0; rf_wp_s2 <= 5'd0;
        end else begin
            rf_wp_s1 <= rf_wp_g; rf_wp_s2 <= rf_wp_s1;
            if (rd_data && !rst_s2) begin                          // never drive while the clk domain is in reset
                tx <= cur;
                if (need && avail) begin rf_rp <= rf_rp + 5'd1; rf_rp_g <= g(rf_rp + 5'd1); end
                if (quad) begin io_oe <= 4'b1111; io_o <= pc[0] ? cur[3:0] : cur[7:4]; end
                else      begin io_oe <= 4'b0010; io_o <= {2'b00, cur[3'd7 - pc], 1'b0}; end
            end
        end
    end

    // ===================== clk domain =====================
    reg [2:0]  cs_s;
    wire       cs_hi = cs_s[1];
    reg [4:0]  wf_rp, wf_wp_s1, wf_wp_s2;
    reg [1:0]  hst;                  // 0 idle, 1 expect A1, 2 expect A0, 3 data
    reg        is_rd;
    reg [7:0]  a_hi;
    reg [15:0] waddr, raddr;
    reg        prefetch;
    reg [4:0]  rf_wp, rf_rp_s1, rf_rp_s2;
    reg [1:0]  rpipe;
    wire [8:0] wf_q = wf_mem[wf_rp[3:0]];
    wire       wf_ne = g(wf_rp) != wf_wp_s2;
    wire [4:0] rf_used = rf_wp - bin(rf_rp_s2) + {4'd0, rpipe[0]} + {4'd0, rpipe[1]};
    always @(posedge clk) begin
        cs_s <= {cs_s[1:0], cs_n};
        bus_we <= 1'b0; bus_re <= 1'b0; frame_end <= 1'b0;
        wf_wp_s1 <= wf_wp_g; wf_wp_s2 <= wf_wp_s1;
        rf_rp_s1 <= rf_rp_g; rf_rp_s2 <= rf_rp_s1;
        rpipe <= {rpipe[0], 1'b0};
        if (rst) begin
            wf_rp <= 5'd0; wf_wp_s1 <= 5'd0; wf_wp_s2 <= 5'd0; hst <= 2'd0; is_rd <= 1'b0;
            rf_wp <= 5'd0; rf_wp_g <= 5'd0; prefetch <= 1'b0; rpipe <= 2'b00;
        end else begin
            if (wf_ne) begin                                   // one received byte per clock
                wf_rp <= wf_rp + 5'd1;
                if (wf_q[8]) begin
                    hst <= 2'd1; prefetch <= 1'b0;
                    is_rd <= wf_q[7:0] == C_RD1 || wf_q[7:0] == C_RD4;
                    if (!(wf_q[7:0] == C_RD1 || wf_q[7:0] == C_RD4 || wf_q[7:0] == C_WR1 || wf_q[7:0] == C_WR4))
                        hst <= 2'd0;                             // unknown command: ignore the frame
                end else case (hst)
                    2'd1: begin a_hi <= wf_q[7:0]; hst <= 2'd2; end
                    2'd2: begin waddr <= {a_hi, wf_q[7:0]}; raddr <= {a_hi, wf_q[7:0]}; hst <= 2'd3; prefetch <= is_rd; end
                    2'd3: if (!is_rd) begin
                        bus_we <= 1'b1; bus_addr <= waddr; bus_wdata <= wf_q[7:0]; waddr <= waddr + 16'd1;
                    end
                    default: ;
                endcase
            end
            if (prefetch && !cs_hi && rf_used < 5'd13 && !(wf_ne && hst == 2'd3 && !is_rd)) begin
                bus_re <= 1'b1; bus_addr <= raddr; raddr <= raddr + 16'd1; rpipe[0] <= 1'b1;
            end
            if (rpipe[1]) begin
                rf_mem[rf_wp[3:0]] <= bus_rdata;
                rf_wp <= rf_wp + 5'd1; rf_wp_g <= g(rf_wp + 5'd1);
            end
            if (cs_hi) begin                                   // frame over: empty the read FIFO for the next frame
                prefetch <= 1'b0; rf_wp <= 5'd0; rf_wp_g <= 5'd0; rpipe <= 2'b00;
                if (!cs_s[2]) frame_end <= 1'b1;
            end
        end
    end
endmodule
/* verilator lint_on SYNCASYNCNET */
`default_nettype wire
