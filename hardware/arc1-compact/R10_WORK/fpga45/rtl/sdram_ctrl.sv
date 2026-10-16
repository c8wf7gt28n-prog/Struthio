// ARC-1 R10 (ARC1_MEMORY_R10 v0.1 s2.3) -- x16 SDR SDRAM controller for the ECP5-45F, 32 MiB (4 banks x 8192 rows x
// 512 columns x 16 bit, AS4C16M16SA family candidate). One clock domain (the 45F sys_clk, 80 MHz by default).
//   * Mode: burst length 1, sequential, CAS latency CL (2 or 3); a READ or WRITE command every clock gives one word
//     per clock inside a row. Closed-page policy: ACTIVE, column commands, PRECHARGE (after tWR for writes).
//   * Burst port: cmd_valid/cmd_ready, cmd_write, cmd_addr (word address: bank[23:22] row[21:9] col[8:0]),
//     cmd_len (1..MAX_BURST words; a burst must not cross a 512-word row: cmd_err otherwise, nothing issued).
//     Write data: wr_valid/wr_ready, one word per accepted clock (wr_ready only while the WRITE is issued).
//     Read data: rd_valid/rd_data, RD_LAT clocks after each READ, no back-pressure.
//   * Refresh: one AUTO REFRESH per tREFI (7.8 us); a due refresh waits for the current burst only
//     (MAX_BURST = 256 words = 3.2 us at 80 MHz).
//   * Init: wait T_INIT, PRECHARGE ALL, INIT_REF x AUTO REFRESH, LOAD MODE REGISTER, then init_done.
// Timing: DOCUMENTED worst case of the -6 and -7 grades (Alliance AS4C16M16SA-C&I Rev 3.0, March 2015, Table 16):
// tRCD/tRP 21, tRAS 42, tRC 63, tWR 14, tMRD 14, tRFC 63 ns; refresh 8192 / 64 ms (tREFI 7.8 us; the automotive grade
// needs 3.9 us -- not selected); init 200 us + >= 2 refreshes (8 used). Every value is a parameter in clocks.
// Clocking (top level): sd_clk is clk INVERTED (ODDR 0/1), so the SDRAM samples commands mid-window (setup and hold
// about half a period each). Read timing: a READ registered at clk edge k is sampled at sd_clk k+0.5; data is valid
// from k+0.5+CL+tAC and is captured by the pad register at clk edge k+CL+1. With the documented tAC (5.0 / 5.4 ns at
// CL3) that leaves under 1.3 ns for FPGA clock-out, both trace flights and input setup: NOT closable as is -- see
// analysis/R10_SDRAM_TIMING.md (needs a PLL phase-shifted capture clock, calibrated at boot). CONDITIONAL.
// Evidence: RTL_SIMULATED (tb_sdram with the sdram_model protocol checker).
`default_nettype none
module sdram_ctrl #(
    parameter integer CLK_MHZ   = 80,
    parameter integer CL        = 3,           // CL3: tAC 5.0 (-6) / 5.4 ns (-7) vs 6 ns at CL2; tCK 12.5 >= 7 ns
    parameter integer RD_LAT    = CL + 3,      // READ issue -> rd_valid, see "read timing" below
    // AS4C16M16SA-C&I Rev 3.0 Table 16, worst of -6/-7, rounded up to whole clocks: ceil(ns * MHz / 1000)
    parameter integer T_RCD     = (21 * CLK_MHZ + 999) / 1000,
    parameter integer T_RP      = (21 * CLK_MHZ + 999) / 1000,
    parameter integer T_RAS     = (42 * CLK_MHZ + 999) / 1000,
    parameter integer T_RC      = (63 * CLK_MHZ + 999) / 1000,
    parameter integer T_WR      = (14 * CLK_MHZ + 999) / 1000,
    parameter integer T_MRD     = (14 * CLK_MHZ + 999) / 1000,
    parameter integer T_RFC     = (63 * CLK_MHZ + 999) / 1000,
    parameter integer T_REFI    = 7800 * CLK_MHZ / 1000,
    parameter integer T_INIT    = 200 * CLK_MHZ,
    parameter integer INIT_REF  = 8,
    parameter integer MAX_BURST = 256
) (
    input  wire        clk,
    input  wire        rst,
    output reg         init_done,
    // burst port
    input  wire        cmd_valid,
    output wire        cmd_ready,
    input  wire        cmd_write,
    input  wire [23:0] cmd_addr,
    input  wire [9:0]  cmd_len,
    output reg         cmd_err,               // pulse: rejected burst (row crossing / bad length)
    input  wire        wr_valid,
    output wire        wr_ready,
    input  wire [15:0] wr_data,
    output reg         rd_valid,
    output reg  [15:0] rd_data,
    output reg  [31:0] cnt_refresh,
    // SDRAM pins (registered)
    output reg         sd_cke,
    output reg         sd_cs_n,
    output reg         sd_ras_n,
    output reg         sd_cas_n,
    output reg         sd_we_n,
    output reg  [1:0]  sd_ba,
    output reg  [12:0] sd_a,
    output reg  [1:0]  sd_dqm,
    inout  wire [15:0] sd_dq
);
    // command encodings {cs_n, ras_n, cas_n, we_n}
    localparam [3:0] C_NOP = 4'b0111, C_ACT = 4'b0011, C_RD = 4'b0101, C_WR = 4'b0100, C_PRE = 4'b0010,
                     C_REF = 4'b0001, C_MRS = 4'b0000;
    localparam [3:0] S_INIT = 0, S_IREF = 2, S_IMRS = 3, S_IDLE = 4, S_ACT = 5, S_RW = 6, S_WREC = 7,
                     S_PRE = 8, S_WAIT = 10;
    reg [3:0]  st, st_after;
    reg [15:0] wait_cnt;
    reg [3:0]  iref;
    reg [15:0] refi_cnt;
    reg        ref_due;
    reg        b_write;
    reg [1:0]  b_ba;
    reg [12:0] b_row;
    reg [8:0]  b_col;
    reg [9:0]  b_left;
    reg [7:0]  ras_cnt;                         // clocks since ACTIVE (tRAS / tRC)

    // DQ output path: registered data + output enable
    reg [15:0] dq_o;
    reg        dq_oe;
    assign sd_dq = dq_oe ? dq_o : 16'hzzzz;
    // read capture: pad register, then a valid pipeline RD_LAT deep
    reg [15:0] dq_in1;
    reg [RD_LAT-1:0] rd_pipe;
    always @(posedge clk) begin
        dq_in1 <= sd_dq;
        rd_pipe <= {rd_pipe[RD_LAT-2:0], (st == S_RW) && !b_write};
        rd_valid <= rd_pipe[RD_LAT-2];
        rd_data <= dq_in1;
        if (rst) begin rd_pipe <= {RD_LAT{1'b0}}; rd_valid <= 1'b0; end
    end

    assign cmd_ready = init_done && (st == S_IDLE) && !ref_due;
    assign wr_ready  = (st == S_RW) && b_write;

    task automatic issue(input [3:0] c);
        begin {sd_cs_n, sd_ras_n, sd_cas_n, sd_we_n} <= c; end
    endtask

    always @(posedge clk) begin
        issue(C_NOP);
        cmd_err <= 1'b0;
        dq_oe <= 1'b0;
        if (st != S_INIT) begin
            if (refi_cnt == T_REFI[15:0] - 16'd1) begin refi_cnt <= 16'd0; ref_due <= 1'b1; end
            else refi_cnt <= refi_cnt + 16'd1;
        end
        if (ras_cnt != 8'hFF) ras_cnt <= ras_cnt + 8'd1;
        if (rst) begin
            st <= S_INIT; wait_cnt <= 16'd0; init_done <= 1'b0; sd_cke <= 1'b0; sd_dqm <= 2'b11; ref_due <= 1'b0;
            refi_cnt <= 16'd0; cnt_refresh <= 32'd0; iref <= 4'd0; ras_cnt <= 8'hFF; sd_a <= 13'd0; sd_ba <= 2'd0;
        end else case (st)
        S_INIT: begin                                         // inputs stable, clock running, CKE high, NOPs
            sd_cke <= 1'b1;
            if (wait_cnt == T_INIT[15:0]) begin
                issue(C_PRE); sd_a[10] <= 1'b1; wait_cnt <= T_RP[15:0] - 16'd1; st <= S_WAIT; st_after <= S_IREF;
            end else wait_cnt <= wait_cnt + 16'd1;
        end
        S_IREF: begin
            issue(C_REF); cnt_refresh <= cnt_refresh + 32'd1; iref <= iref + 4'd1;
            wait_cnt <= T_RFC[15:0] - 16'd1; st <= S_WAIT;
            st_after <= (iref == INIT_REF[3:0] - 4'd1) ? S_IMRS : S_IREF;
        end
        S_IMRS: begin                                         // BL = 1, sequential, CL, write burst = programmed
            issue(C_MRS); sd_ba <= 2'b00; sd_a <= {3'b000, 1'b0, 2'b00, CL[2:0], 1'b0, 3'b000};
            wait_cnt <= T_MRD[15:0] - 16'd1; st <= S_WAIT; st_after <= S_IDLE; ref_due <= 1'b0; refi_cnt <= 16'd0;
        end
        S_WAIT: if (wait_cnt == 16'd0) begin
                    st <= st_after;
                    if (st_after == S_IDLE) init_done <= 1'b1;
                end else wait_cnt <= wait_cnt - 16'd1;
        S_IDLE: begin
            sd_dqm <= 2'b00;
            if (ref_due) begin
                if (ras_cnt >= T_RC[7:0]) begin                // all banks precharged (closed-page policy)
                    issue(C_REF); ref_due <= 1'b0; cnt_refresh <= cnt_refresh + 32'd1;
                    wait_cnt <= T_RFC[15:0] - 16'd1; st <= S_WAIT; st_after <= S_IDLE;
                end
            end else if (cmd_valid) begin
                if (cmd_len == 10'd0 || cmd_len > MAX_BURST[9:0] || {1'b0, cmd_addr[8:0]} + cmd_len > 10'd512)
                    cmd_err <= 1'b1;
                else begin
                    b_write <= cmd_write; b_ba <= cmd_addr[23:22]; b_row <= cmd_addr[21:9]; b_col <= cmd_addr[8:0];
                    b_left <= cmd_len; st <= S_ACT;
                end
            end
        end
        S_ACT: if (ras_cnt >= T_RC[7:0]) begin                // tRC from the previous ACTIVE (any bank: one open at a time)
            issue(C_ACT); sd_ba <= b_ba; sd_a <= b_row; ras_cnt <= 8'd0;
            wait_cnt <= T_RCD[15:0] - 16'd1; st <= S_WAIT; st_after <= S_RW;
        end
        S_RW: begin                                           // one column command per clock
            if (!b_write || wr_valid) begin
                issue(b_write ? C_WR : C_RD); sd_ba <= b_ba; sd_a <= {4'b0000, b_col};    // A10 = 0: no auto precharge
                if (b_write) begin dq_o <= wr_data; dq_oe <= 1'b1; end
                b_col <= b_col + 9'd1; b_left <= b_left - 10'd1;
                if (b_left == 10'd1) begin
                    wait_cnt <= b_write ? T_WR[15:0] - 16'd1 : 16'd0; st <= S_WREC;
                end
            end
        end
        S_WREC: if (wait_cnt == 16'd0) st <= S_PRE; else wait_cnt <= wait_cnt - 16'd1;
        S_PRE: if (ras_cnt >= T_RAS[7:0]) begin
            issue(C_PRE); sd_ba <= b_ba; sd_a[10] <= 1'b0;
            wait_cnt <= T_RP[15:0] - 16'd1; st <= S_WAIT; st_after <= S_IDLE;
        end
        default: st <= S_IDLE;
        endcase
    end
endmodule
`default_nettype wire
