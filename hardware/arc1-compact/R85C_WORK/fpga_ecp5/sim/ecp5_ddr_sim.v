// Behavioural models of the ECP5 IDDRX1F / ODDRX1F primitives (SIMULATION ONLY; Yosys ships black boxes).
// Assumed semantics (to be confirmed against Lattice FPGA-TN-02035 on the bench, risk RK-ECP5-DDR-SEM):
//   IDDRX1F: D sampled at the rising edge (r) and the following falling edge (f); both presented at the next rising
//            edge as Q0 = r, Q1 = f.
//   ODDRX1F: D0/D1 sampled at a rising edge; Q = D0 for the next high phase, D1 for the following low phase.
`timescale 1ns/1ps
module IDDRX1F (input D, SCLK, RST, output reg Q0 = 1'b0, output reg Q1 = 1'b0);
    parameter GSR = "ENABLED";
    reg r = 1'b0, f = 1'b0;
    always @(posedge SCLK) begin Q0 <= r; Q1 <= f; r <= D; end
    always @(negedge SCLK) f <= D;
endmodule
module ODDRX1F (input SCLK, RST, D0, D1, output reg Q = 1'b0);
    parameter GSR = "ENABLED";
    reg d1h = 1'b0;
    always @(posedge SCLK) begin Q <= D0; d1h <= D1; end
    always @(negedge SCLK) Q <= d1h;
endmodule
