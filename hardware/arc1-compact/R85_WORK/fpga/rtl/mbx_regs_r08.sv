// ARC-1 Compact R08 -- mailbox register file and frame buffers ("AMBX" v2).
// Copied from R06_WORK/fpga/mailbox/rtl/mbx_regs.sv (unchanged there). R08 additions:
//   VERSION 2; CAPS b2 = PSRAM power guard; STATUS b11 PSRAM_POWER_ON, b12 PSRAM_POWER_LOST
//   (sticky); STATUS b1 PSRAM_READY is reported only while POWER_LOST is clear;
//   CONTROL b5 CLEAR_POWER_LOST; 0x0020 PSRAM_EPOCH u8 (count of guard power-ups).
// Evidence level: RTL_SIMULATED only.
//
// The mailbox moves opaque bytes. The host writes a complete R05 ARC1 wire
// frame (20-byte header, payload, CRC32; 24..4120 bytes) into REQ, writes
// REQ_LEN and rings the doorbell. FPGA logic answers through RESP. The R05 wire
// ABI is carried unchanged; this block neither parses nor alters frames.
//
// Byte map (multi-byte registers are little endian):
//   0x0000  MAGIC     "AMBX" (41 4D 42 58)                       RO
//   0x0004  VERSION   u16 = 2;  0x0006 CAPS u16 (bit0 PSRAM fitted, bit1 BIST, bit2 power guard)
//   0x0008  STATUS    u16: b0 FPGA_READY, b1 PSRAM_READY, b2 PSRAM_ERROR,
//                     b3 JOB_PENDING, b4 RESP_READY, b5 DOORBELL_OVERRUN,
//                     b6 BIST_BUSY, b7 BIST_PASS, b8 BIST_FAIL, b10:9 PSRAM err code,
//                     b11 PSRAM_POWER_ON, b12 PSRAM_POWER_LOST (sticky until CLEAR)
//   0x000C  CONTROL   write-1 pulses: b0 DOORBELL, b1 RESP_ACK, b2 PSRAM_RECOVER,
//                     b3 BIST_START, b4 CLEAR_OVERRUN, b5 CLEAR_POWER_LOST
//   0x0010  REQ_LEN   u16 (host writes)                           RW
//   0x0014  RESP_LEN  u16                                         RO
//   0x0018  DOORBELLS u32 accepted doorbell count                 RO
//   0x001C  BIST_ERRS u32 mismatching bytes + failed operations   RO
//   0x0020  PSRAM_EPOCH u8 guard power-up count (wraps)            RO
//   0x2000..0x3FFF REQ  buffer (8 KiB)                            RW (host)
//   0x4000..0x5FFF RESP buffer (8 KiB)                            RO (host)
//   other addresses read 0x00, writes ignored
module mbx_regs_r08 #(
    parameter [15:0] CAPS = 16'h0007
) (
    input  wire        clk,
    input  wire        rst,
    // SPI-side byte bus (read data registered; valid 1 clk after bus_re)
    input  wire [15:0] bus_addr,
    input  wire        bus_we,
    input  wire [7:0]  bus_wdata,
    input  wire        bus_re,
    output reg  [7:0]  bus_rdata,
    output wire        irq,          // RESP_READY (level)
    // job interface (FPGA user logic)
    output reg         job_valid,    // pulse on accepted doorbell
    output reg  [15:0] job_len,
    input  wire [12:0] req_raddr,
    output reg  [7:0]  req_rdata,
    input  wire        resp_we,
    input  wire [12:0] resp_waddr,
    input  wire [7:0]  resp_wdata,
    input  wire        resp_post,    // pulse: response complete
    input  wire [15:0] resp_len_in,
    // PSRAM / BIST status and controls
    input  wire        psram_ready,
    input  wire        psram_error,
    input  wire [1:0]  psram_err_code,
    output reg         psram_recover,
    output reg         bist_start,
    input  wire        bist_busy,
    input  wire        bist_pass,
    input  wire        bist_fail,
    input  wire [31:0] bist_errs,
    input  wire        psram_power_on    // guard state, already synchronised to clk
);
    reg [7:0] req_mem  [0:8191];
    reg [7:0] resp_mem [0:8191];

    reg        job_pending, resp_ready, overrun;
    reg [15:0] req_len, resp_len;
    reg [31:0] doorbells;

    reg        power_lost, power_on_q;
    reg [7:0]  epoch;
    wire [15:0] status = {3'd0, power_lost, psram_power_on, psram_err_code, bist_fail, bist_pass, bist_busy,
                          overrun, resp_ready, job_pending, psram_error, psram_ready & ~power_lost, 1'b1};
    assign irq = resp_ready;

    wire in_req  = (bus_addr[15:13] == 3'b001);   // 0x2000..0x3FFF
    wire in_resp = (bus_addr[15:13] == 3'b010);   // 0x4000..0x5FFF

    // ---------------- buffers ----------------
    reg [7:0] req_q, resp_q;
    always @(posedge clk) begin
        if (bus_we && in_req) req_mem[bus_addr[12:0]] <= bus_wdata;
        req_q     <= req_mem[bus_addr[12:0]];
        req_rdata <= req_mem[req_raddr];
    end
    always @(posedge clk) begin
        if (resp_we) resp_mem[resp_waddr] <= resp_wdata;
        resp_q <= resp_mem[bus_addr[12:0]];
    end

    // ---------------- registers ----------------
    reg [7:0] reg_q;
    always @(*) begin
        case (bus_addr)
        16'h0000: reg_q = 8'h41;  16'h0001: reg_q = 8'h4D;
        16'h0002: reg_q = 8'h42;  16'h0003: reg_q = 8'h58;
        16'h0004: reg_q = 8'h02;  16'h0005: reg_q = 8'h00;
        16'h0006: reg_q = CAPS[7:0]; 16'h0007: reg_q = CAPS[15:8];
        16'h0008: reg_q = status[7:0]; 16'h0009: reg_q = status[15:8];
        16'h0010: reg_q = req_len[7:0];  16'h0011: reg_q = req_len[15:8];
        16'h0014: reg_q = resp_len[7:0]; 16'h0015: reg_q = resp_len[15:8];
        16'h0018: reg_q = doorbells[7:0];   16'h0019: reg_q = doorbells[15:8];
        16'h001A: reg_q = doorbells[23:16]; 16'h001B: reg_q = doorbells[31:24];
        16'h001C: reg_q = bist_errs[7:0];   16'h001D: reg_q = bist_errs[15:8];
        16'h001E: reg_q = bist_errs[23:16]; 16'h001F: reg_q = bist_errs[31:24];
        16'h0020: reg_q = epoch;
        default:  reg_q = 8'h00;
        endcase
    end

    reg [1:0] sel_q;   // 0 regs, 1 req, 2 resp
    reg [7:0] reg_qq;
    always @(posedge clk) begin
        sel_q  <= in_req ? 2'd1 : (in_resp ? 2'd2 : 2'd0);
        reg_qq <= reg_q;
    end
    always @(*) begin
        case (sel_q)
        2'd1:    bus_rdata = req_q;
        2'd2:    bus_rdata = resp_q;
        default: bus_rdata = reg_qq;
        endcase
    end

    always @(posedge clk) begin
        job_valid     <= 1'b0;
        psram_recover <= 1'b0;
        bist_start    <= 1'b0;
        if (rst) begin
            job_pending <= 1'b0;
            resp_ready  <= 1'b0;
            overrun     <= 1'b0;
            req_len     <= 16'd0;
            resp_len    <= 16'd0;
            doorbells   <= 32'd0;
            job_len     <= 16'd0;
            power_lost  <= 1'b0;
            power_on_q  <= 1'b0;
            epoch       <= 8'd0;
        end else begin
            power_on_q <= psram_power_on;
            if (psram_power_on && !power_on_q) epoch <= epoch + 8'd1;
            // A fall of the guard state means the PSRAM lost power (or PG glitched):
            // contents are unknown until the host clears the flag and reloads.
            if (!psram_power_on && power_on_q) power_lost <= 1'b1;
            if (bus_we) begin
                case (bus_addr)
                16'h0010: req_len[7:0]  <= bus_wdata;
                16'h0011: req_len[15:8] <= bus_wdata;
                16'h000C: begin
                    if (bus_wdata[0]) begin
                        if (job_pending || resp_ready || req_len == 16'd0 || req_len > 16'd8192)
                            overrun <= 1'b1;
                        else begin
                            job_pending <= 1'b1;
                            job_valid   <= 1'b1;
                            job_len     <= req_len;
                            doorbells   <= doorbells + 32'd1;
                        end
                    end
                    if (bus_wdata[1]) resp_ready    <= 1'b0;
                    if (bus_wdata[2]) psram_recover <= 1'b1;
                    if (bus_wdata[3]) bist_start    <= 1'b1;
                    if (bus_wdata[4]) overrun       <= 1'b0;
                    if (bus_wdata[5] && !(!psram_power_on && power_on_q)) power_lost <= 1'b0;
                end
                default: ;
                endcase
            end
            if (resp_post) begin
                job_pending <= 1'b0;
                resp_ready  <= 1'b1;
                resp_len    <= resp_len_in;
            end
        end
    end
endmodule
