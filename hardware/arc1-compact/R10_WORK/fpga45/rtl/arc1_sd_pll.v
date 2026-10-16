// ARC-1 R10 -- 45F memory-variant PLL: CLKOP = sys_clk 80 MHz (feedback), CLKOS = sd_clk_pll 80 MHz with dynamic
// phase adjust for the SDRAM interface calibration (rtl/sdram_cal.sv). Same divider plan as arc1_ecp5_pll.v
// (CLKI 25 MHz / 5, feedback x16, VCO 560 MHz, CLKOP/CLKOS /7). Dynamic phase: PHASESEL selects the output, each
// PHASESTEP pulse moves it by one step (1/8 VCO period = 223 ps -> 56 steps per 12.5 ns). The PHASESEL encoding,
// step direction and step size are from the ECP5 sysCLOCK documentation as understood here -- UNVERIFIED until read in
// FPGA-TN-02200 (ECP5 sysCLOCK PLL/DLL) and checked on the bench; the calibrator sweeps a full turn, so a wrong step
// direction or count per period changes only the reported numbers, not the search.
module arc1_sd_pll (
    input  clk_25m,
    input  phase_step,
    output sys_clk,
    output sd_clk_pll,
    output locked
);
(* FREQUENCY_PIN_CLKI="25" *)
(* FREQUENCY_PIN_CLKOP="80" *)
(* FREQUENCY_PIN_CLKOS="80" *)
(* ICP_CURRENT="12" *) (* LPF_RESISTOR="8" *) (* MFG_ENABLE_FILTEROPAMP="1" *) (* MFG_GMCREF_SEL="2" *)
EHXPLLL #(
        .PLLRST_ENA("DISABLED"),
        .INTFB_WAKE("DISABLED"),
        .STDBY_ENABLE("DISABLED"),
        .DPHASE_SOURCE("ENABLED"),
        .OUTDIVIDER_MUXA("DIVA"),
        .OUTDIVIDER_MUXB("DIVB"),
        .OUTDIVIDER_MUXC("DIVC"),
        .OUTDIVIDER_MUXD("DIVD"),
        .CLKI_DIV(5),
        .CLKOP_ENABLE("ENABLED"),
        .CLKOP_DIV(7),
        .CLKOP_CPHASE(3),
        .CLKOP_FPHASE(0),
        .CLKOS_ENABLE("ENABLED"),
        .CLKOS_DIV(7),
        .CLKOS_CPHASE(3),
        .CLKOS_FPHASE(0),
        .FEEDBK_PATH("CLKOP"),
        .CLKFB_DIV(16)
    ) pll_i (
        .RST(1'b0),
        .STDBY(1'b0),
        .CLKI(clk_25m),
        .CLKOP(sys_clk),
        .CLKOS(sd_clk_pll),
        .CLKFB(sys_clk),
        .CLKINTFB(),
        .PHASESEL0(1'b0),
        .PHASESEL1(1'b0),
        .PHASEDIR(1'b0),
        .PHASESTEP(phase_step),
        .PHASELOADREG(1'b0),
        .PLLWAKESYNC(1'b0),
        .ENCLKOP(1'b0),
        .LOCK(locked)
	);
endmodule
