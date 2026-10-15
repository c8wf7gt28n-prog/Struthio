// ARC-1 Compact R06 -- TRANSPORT LOOPBACK job engine (not compute).
// Copies the request buffer to the response buffer unchanged and posts it.
// Used to prove the mailbox path and the host fallback logic before the R07
// frame parser / transform engine exists. Evidence level: RTL_SIMULATED.
module mbx_loopback (
    input  wire        clk,
    input  wire        rst,
    input  wire        job_valid,
    input  wire [15:0] job_len,
    output reg  [12:0] req_raddr,
    input  wire [7:0]  req_rdata,     // valid 1 clk after req_raddr
    output reg         resp_we,
    output reg  [12:0] resp_waddr,
    output reg  [7:0]  resp_wdata,
    output reg         resp_post,
    output reg  [15:0] resp_len
);
    reg        busy;
    reg [15:0] idx;
    reg        rd_v;
    reg [12:0] rd_a;
    always @(posedge clk) begin
        resp_we   <= 1'b0;
        resp_post <= 1'b0;
        if (rst) begin
            busy <= 1'b0; rd_v <= 1'b0; idx <= 16'd0; req_raddr <= 13'd0;
        end else begin
            rd_v <= 1'b0;
            if (job_valid && !busy) begin
                busy <= 1'b1; idx <= 16'd0; resp_len <= job_len;
            end else if (busy) begin
                if (idx < resp_len) begin
                    req_raddr <= idx[12:0];
                    rd_a      <= idx[12:0];
                    rd_v      <= 1'b1;
                    idx       <= idx + 16'd1;
                end else if (!rd_v) begin
                    busy      <= 1'b0;
                    resp_post <= 1'b1;
                end
            end
            if (rd_v) begin
                resp_we    <= 1'b1;
                resp_waddr <= rd_a;
            end
        end
    end
    // req_rdata is valid in the cycle after req_raddr was registered
    always @(*) resp_wdata = req_rdata;
endmodule
