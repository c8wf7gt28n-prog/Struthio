// Behavioural stand-in for rtl/arc1_eth_pll.v (SIMULATION ONLY): 125 MHz.
`timescale 1ns/1ps
module arc1_eth_pll #(parameter real NS = 8.0) (input clk_25m, output reg eth_txclk = 1'b0, output reg locked = 1'b0);
    always #(NS / 2.0) eth_txclk <= ~eth_txclk;
endmodule
