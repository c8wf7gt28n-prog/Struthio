// ARC-1 R10 -- power-on self test for the 45F SDRAM: after init_done, writes BURSTS x 256 words of pattern(addr)
// spread over all 4 banks and distant rows, reads them back and compares. One run per reset (or per start pulse).
// Result: pass/fail, error count. Evidence: RTL_SIMULATED (tb_sdram_bist + tb_r10_45f with -DMEMTOP).
`default_nettype none
module sdram_bist #(parameter integer BURSTS = 16) (
    input  wire        clk,
    input  wire        rst,
    input  wire        init_done,
    input  wire        start,                       // optional re-run
    output reg         busy, pass, fail,
    output reg  [15:0] errs,
    output reg         cmd_valid,
    input  wire        cmd_ready,
    output reg         cmd_write,
    output reg  [23:0] cmd_addr,
    output wire [9:0]  cmd_len,
    input  wire        wr_ready,
    output wire [15:0] wr_data,
    input  wire        rd_valid,
    input  wire [15:0] rd_data
);
    assign cmd_len = 10'd256;
    function automatic [15:0] pat(input [23:0] a);
        pat = a[15:0] ^ {a[23:16], a[23:16]} ^ 16'hA55A;
    endfunction
    reg [4:0]  b;
    reg [8:0]  wcnt, rcnt;
    reg        phase_rd, ran;
    // burst k: bank k[1:0], row {k[4:2], 10'h155}, columns 0..255
    wire [23:0] base = {b[1:0], b[4:2], 10'h155, 9'd0};
    assign wr_data = pat(base + {15'd0, wcnt});
    localparam [1:0] B_IDLE = 0, B_CMD = 1, B_DATA = 2;
    reg [1:0] st;
    always @(posedge clk) begin
        if (rst) begin
            st <= B_IDLE; busy <= 1'b0; pass <= 1'b0; fail <= 1'b0; errs <= 16'd0; cmd_valid <= 1'b0; ran <= 1'b0;
        end else case (st)
        B_IDLE: if (init_done && (!ran || start)) begin
            ran <= 1'b1; busy <= 1'b1; pass <= 1'b0; fail <= 1'b0; errs <= 16'd0; b <= 5'd0; phase_rd <= 1'b0; st <= B_CMD;
        end
        B_CMD: begin
            cmd_valid <= 1'b1; cmd_write <= !phase_rd; cmd_addr <= base; wcnt <= 9'd0; rcnt <= 9'd0;
            if (cmd_valid && cmd_ready) begin cmd_valid <= 1'b0; st <= B_DATA; end
        end
        B_DATA: begin
            if (!phase_rd && wr_ready) wcnt <= wcnt + 9'd1;
            if (phase_rd && rd_valid) begin
                if (rd_data != pat(base + {15'd0, rcnt})) errs <= errs + 16'd1;
                rcnt <= rcnt + 9'd1;
            end
            if ((!phase_rd && wr_ready && wcnt == 9'd255) || (phase_rd && rd_valid && rcnt == 9'd255)) begin
                if (b == BURSTS[4:0] - 5'd1) begin
                    b <= 5'd0;
                    if (phase_rd) begin                     // last word: the result includes its compare
                        busy <= 1'b0; st <= B_IDLE;
                        pass <= (errs == 16'd0) && (rd_data == pat(base + {15'd0, rcnt}));
                        fail <= (errs != 16'd0) || (rd_data != pat(base + {15'd0, rcnt}));
                    end else begin phase_rd <= 1'b1; st <= B_CMD; end
                end else begin b <= b + 5'd1; st <= B_CMD; end
            end
        end
        default: st <= B_IDLE;
        endcase
    end
endmodule
`default_nettype wire
