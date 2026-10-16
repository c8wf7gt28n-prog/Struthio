// Behavioural stand-in for rtl/arc1_sd_pll.v (SIMULATION ONLY): sd_clk_pll = sys_clk delayed by ph * period / PHASES,
// ph += 1 (mod PHASES) per phase_step pulse.
`timescale 1ns/1ps
module arc1_sd_pll #(parameter real SYS_NS = 12.5, parameter integer PHASES = 56)
(input clk_25m, input phase_step, output reg sys_clk = 1'b0, output reg sd_clk_pll = 1'b0, output reg locked = 1'b0);
    integer ph = 0;
    always #(SYS_NS / 2.0) sys_clk <= ~sys_clk;
    always @(posedge sys_clk) if (phase_step) ph <= (ph + 1) % PHASES;
    always @(sys_clk) sd_clk_pll <= #(ph * SYS_NS / PHASES) sys_clk;
endmodule
