// Behavioural stand-in for the ecppll-generated EHXPLLL wrapper (SIMULATION ONLY).
// Same ports as rtl/arc1_ecp5_pll.v. Clock periods are produced by the testbench
// through `ifdef`-free parameters so that the tb can also run unrelated ratios.
`timescale 1ns/1ps
module arc1_ecp5_pll #(parameter real SYS_NS = 12.5, parameter real MEM_NS = 25.0)
(input clk_25m, output reg sys_clk = 1'b0, output reg psram_mclk = 1'b0, output reg locked = 1'b0);
    always #(SYS_NS / 2.0) sys_clk <= ~sys_clk;
    always #(MEM_NS / 2.0) psram_mclk <= ~psram_mclk;
    // lock follows the reference: the tb drops clk_25m activity by forcing locked
endmodule
