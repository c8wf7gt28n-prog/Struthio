// ARC-1 Compact R06 -- PSRAM built-in self test, started by the F133 over the
// mailbox (CONTROL.b3). It writes BLOCKS x 256 bytes of a per-block LFSR
// pattern starting at BASE, reads everything back and counts mismatching bytes
// plus any non-OK operation. Intended for first board bring-up; a PASS here
// would be PROTOTYPE_MEASURED only when it runs on real hardware.
// Evidence level of this RTL: RTL_SIMULATED.
module psram_bist #(
    parameter integer BLOCKS = 64,             // 64 x 256 B = 16 KiB
    parameter [22:0]  BASE   = 23'h000000
) (
    input  wire        clk,
    input  wire        rst,
    input  wire        start,
    output reg         busy,
    output reg         pass,
    output reg         fail,
    output reg  [31:0] errs,
    // psram_user_port request side
    output reg         req_valid,
    input  wire        req_ready,
    output reg         req_write,
    output reg  [22:0] req_addr,
    output wire [8:0]  req_len,
    output reg         wr_valid,
    input  wire        wr_ready,
    output wire [7:0]  wr_data,
    input  wire        rd_valid,
    output wire        rd_ready,
    input  wire [7:0]  rd_data,
    input  wire        resp_valid,
    output wire        resp_ready,
    input  wire [2:0]  resp_status
);
    assign req_len    = 9'd256;
    assign rd_ready   = 1'b1;
    assign resp_ready = 1'b1;

    localparam [2:0] B_IDLE = 3'd0, B_REQ = 3'd1, B_DATA = 3'd2, B_RESP = 3'd3, B_NEXT = 3'd4;
    reg [2:0]  st;
    reg        phase_read;
    reg [15:0] blk;
    reg [8:0]  cnt;
    reg [15:0] lfsr;

    // per-block pattern: 16-bit Galois LFSR seeded from the block number
    function [15:0] step(input [15:0] x);
        step = x[0] ? ((x >> 1) ^ 16'hB400) : (x >> 1);
    endfunction
    wire [15:0] seed = {blk[7:0], ~blk[7:0]} ^ 16'h1D0F;
    assign wr_data = lfsr[7:0];

    always @(posedge clk) begin
        if (rst) begin
            st <= B_IDLE; busy <= 1'b0; pass <= 1'b0; fail <= 1'b0; errs <= 32'd0;
            req_valid <= 1'b0; wr_valid <= 1'b0; req_write <= 1'b0; req_addr <= 23'd0;
            blk <= 16'd0; cnt <= 9'd0; lfsr <= 16'd0; phase_read <= 1'b0;
        end else begin
            case (st)
            B_IDLE: if (start) begin
                busy <= 1'b1; pass <= 1'b0; fail <= 1'b0; errs <= 32'd0;
                blk <= 16'd0; phase_read <= 1'b0; st <= B_REQ;
            end
            B_REQ: begin
                req_valid <= 1'b1;
                req_write <= !phase_read;
                req_addr  <= BASE + {blk[14:0], 8'h00};
                lfsr      <= seed;
                cnt       <= 9'd0;
                if (req_valid && req_ready) begin
                    req_valid <= 1'b0;
                    wr_valid  <= !phase_read;
                    st        <= B_DATA;
                end
            end
            B_DATA: begin
                // rejected requests answer without a data phase
                if (resp_valid) begin
                    wr_valid <= 1'b0;
                    if (resp_status != 3'd0) errs <= errs + 32'd1;
                    st <= B_NEXT;
                end else if (!phase_read && wr_valid && wr_ready) begin
                    lfsr <= step(lfsr);
                    cnt  <= cnt + 9'd1;
                    if (cnt == 9'd255) begin wr_valid <= 1'b0; st <= B_RESP; end
                end else if (phase_read && rd_valid) begin
                    if (rd_data != lfsr[7:0]) errs <= errs + 32'd1;
                    lfsr <= step(lfsr);
                    cnt  <= cnt + 9'd1;
                    if (cnt == 9'd255) st <= B_RESP;
                end
            end
            B_RESP: if (resp_valid) begin
                if (resp_status != 3'd0) errs <= errs + 32'd1;
                st <= B_NEXT;
            end
            B_NEXT: begin
                if (blk == BLOCKS[15:0] - 16'd1) begin
                    if (phase_read) begin
                        busy <= 1'b0;
                        pass <= (errs == 32'd0);
                        fail <= (errs != 32'd0);
                        st   <= B_IDLE;
                    end else begin
                        phase_read <= 1'b1; blk <= 16'd0; st <= B_REQ;
                    end
                end else begin
                    blk <= blk + 16'd1; st <= B_REQ;
                end
            end
            default: st <= B_IDLE;
            endcase
        end
    end
endmodule
