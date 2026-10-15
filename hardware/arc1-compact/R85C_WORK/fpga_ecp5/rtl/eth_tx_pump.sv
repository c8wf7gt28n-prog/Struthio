// ARC-1 Compact R8.5-C -- RGMII TX payload path: sys-domain TX buffer + pump + async FIFO to txc.
// Why: an EBR read port in the 125 MHz txc domain leaves the EBR clock-to-out (5.8 ns, Yosys 0.33 maps
// DP16KD with REGMODE NOREG) in an 8 ns path and closure became placement-dependent. Here the buffer is
// two byte banks (even/odd address, EBR) written and read in the sys domain (16 bits per sys clock =
// 160 MB/s at 80 MHz > 125 MB/s line rate); words cross through a 16-entry flip-flop FIFO with gray-coded
// pointers (2-FF synchronisers). The frame start is signalled only after min(words, 12) words are queued.
// Evidence: RTL_SIMULATED (tb_rgmii with unrelated 80/125 MHz clocks, tb_ecp5_top).
`default_nettype none
module eth_tx_pump (
    input  wire        clk,             // sys
    input  wire        rst,
    input  wire        we,              // response byte writes (sys)
    input  wire [12:0] waddr,
    input  wire [7:0]  wdata,
    input  wire        start,           // pulse (sys): len is valid, all response bytes are written
    input  wire [15:0] len,
    output reg         tx_start_tgl,    // to rgmii_tx (synchronised there)
    // txc side
    input  wire        txc,
    output wire        f_valid,
    output wire [15:0] f_data,
    input  wire        f_pop            // txc pulse: consume f_data
);
    function automatic [4:0] b2g(input [4:0] b); b2g = b ^ (b >> 1); endfunction
    function automatic [4:0] g2b(input [4:0] g);
        integer k;
        begin g2b[4] = g[4]; for (k = 3; k >= 0; k = k - 1) g2b[k] = g2b[k + 1] ^ g[k]; end
    endfunction

    // ---------------- buffer (sys) ----------------
    reg [7:0] bank_e [0:4095];
    reg [7:0] bank_o [0:4095];
    always @(posedge clk) if (we && !waddr[0]) bank_e[waddr[12:1]] <= wdata;
    always @(posedge clk) if (we &&  waddr[0]) bank_o[waddr[12:1]] <= wdata;

    // ---------------- FIFO storage + pointers ----------------
    reg [15:0] fmem [0:15];
    reg [4:0]  wptr, wptr_g;            // sys
    reg [4:0]  rptr, rptr_g;            // txc
    reg [4:0]  rg_s1, rg_s2;            // rptr_g -> sys
    reg [4:0]  wg_s1, wg_s2;            // wptr_g -> txc
    initial begin wptr = 0; wptr_g = 0; rptr = 0; rptr_g = 0; rg_s1 = 0; rg_s2 = 0; wg_s1 = 0; wg_s2 = 0; tx_start_tgl = 1'b0; end

    // ---------------- pump (sys) ----------------
    reg        act, started, rd_v;
    reg [12:0] ra, words, pushed;
    reg [7:0]  qe, qo;
    wire [4:0] used = wptr - g2b(rg_s2);
    always @(posedge clk) begin
        rg_s1 <= rptr_g; rg_s2 <= rg_s1;
        rd_v <= 1'b0;
        if (rst) begin
            act <= 1'b0; started <= 1'b1; rd_v <= 1'b0;
        end else begin
            if (start) begin
                act <= 1'b1; started <= 1'b0; ra <= 13'd0; pushed <= 13'd0;
                words <= len[13:1] + {12'd0, len[0]};                   // ceil(len / 2), len <= 8192
            end else if (act) begin
                if (ra != words && ({1'b0, used} + {5'd0, rd_v}) < 6'd15) begin
                    qe <= bank_e[ra[11:0]]; qo <= bank_o[ra[11:0]]; rd_v <= 1'b1; ra <= ra + 13'd1;
                end
                if (rd_v) begin
                    fmem[wptr[3:0]] <= {qo, qe}; wptr <= wptr + 5'd1; wptr_g <= b2g(wptr + 5'd1);
                    pushed <= pushed + 13'd1;
                end
                if (!started && (pushed >= 13'd12 || pushed == words)) begin
                    started <= 1'b1; tx_start_tgl <= ~tx_start_tgl;
                end
                if (started && ra == words && !rd_v) act <= 1'b0;
            end
        end
    end

    // ---------------- txc side ----------------
    always @(posedge txc) begin
        wg_s1 <= wptr_g; wg_s2 <= wg_s1;
        if (f_pop) begin rptr <= rptr + 5'd1; rptr_g <= b2g(rptr + 5'd1); end
    end
    assign f_valid = (rptr_g != wg_s2);
    assign f_data  = fmem[rptr[3:0]];
endmodule
`default_nettype wire
