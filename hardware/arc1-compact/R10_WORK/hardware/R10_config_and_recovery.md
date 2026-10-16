# R10 FPGA configuration, reset and recovery access — schematic input

Scope: what the schematic pass must draw for configuring both ECP5s from the single NOR (ARC1_MEMORY_R10 §3.1)
and for recovering every device when firmware or the NOR is bad (§5.3, §7.1 "Recovery"). Pins:
`hardware/R10_flash_pinmux.csv` (groups CFG12, CFG45, NOR, D213NOR). Resistor values are the R8.5-C board's
(`R85C_WORK/cad/gen/design.py`, Lattice FPGA-TN-02038 references there); nothing here is measured. Status: PROPOSED.

## 1. 12F configuration (master: F133, slave SPI, CFG[2:0] = 001)
| Net | 12F pin (TQFP144) | F133 | Parts | Source |
|---|---|---|---|---|
| CCLK | 54 | PC2 SPI0-CLK via isolation buffer | 1 k pull-up to VCCIO8; 33 Ω series at the buffer output | TN-02038 Table 6.2 (R8.5-C R) |
| MOSI (D0) | 47 | PC4 via buffer | — | R8.5-C U22 |
| MISO (D1) | 46 | PC5 via buffer enabled by SN | — | R8.5-C U24 |
| SN | 48 | PE4 (GPIO chip select) | 10 k pull-up (deselected while the F133 is in reset) | R8.5-C |
| PROGRAMN | 57 | PE8 open-drain through 470 Ω | 4.7 k pull-up to VCCIO8 | TN-02038 |
| INITN | 55 | PD0 input | 4.7 k pull-up | TN-02038 |
| DONE | 56 | PE9 input (edge IRQ) | 4.7 k pull-up; DONE → 10 k/100 nF/Schmitt delay "DONE_DLY" if a DONE-gated enable is still needed | R8.5-C |
| CFG_0 / CFG_1 / CFG_2 | 62 / 59 / 58 | — | 4.7 k pull-up / GND / GND | slave SPI |
| Isolation | — | PE6 FPGA_BUS_EN_N | LVC1G125 ×4 (R8.5-C U21–U24), OE# pulled up (off) | keeps the shared SPI0/NOR bus clean while the 12F is unpowered |
The NOR and the 12F share SPI0; the burst holds SN low for the whole bitstream, so the loader stages the image in
DDR2 first (`ecp5_cfg.h` rule; `firmware/f133_bootloader` does this).

## 2. 45F configuration (master: D213, slave SPI, CFG[2:0] = 001)
| Net | 45F ball (CABGA381) | D213 | Parts |
|---|---|---|---|
| CCLK | U3 | PB11 SPI1_CLK | 1 k pull-up; 33 Ω series at the D213 |
| MOSI (D0) | W2 | PB10 SPI1_MOSI | — |
| MISO (D1) | V2 | PB9 SPI1_MISO | — |
| SN | T2 | PB8 SPI1_CS | 10 k pull-up |
| PROGRAMN | W3 | PA4 (open-drain use) through 470 Ω | 4.7 k pull-up |
| INITN | V3 | PA5 | 4.7 k pull-up |
| DONE | Y3 | PA6 | 4.7 k pull-up |
| CFG_0 / 1 / 2 | U4 / T4 / R4 | — | 4.7 k pull-up / GND / GND (as R8.5-C) |
SPI1 is dedicated to the 45F: no isolation buffers. Loader: `d213/fpga45_loader` (HOST_TESTED end to end with the
F133 bootloader and the USB link, `firmware/f133_bootloader/tests/test_fpga45_path.c`).

## 3. Reset and power-up behaviour
| Condition | 12F | 45F | Required behaviour (memory spec §5.3) |
|---|---|---|---|
| F133 in reset / no firmware | CFG = 001 (slave SPI): the 12F waits unconfigured with user I/O tri-stated | unaffected | F133 boots without the 12F |
| D213 in reset / not started | unaffected | waits unconfigured | D213 2D works without the 45F (R10 §3.1) |
| Bad application image | golden used (`r10_boot_fpga12`) | golden used (`r10_boot_fpga45`) | HOST_TESTED |
| Both images bad | F133 runs, reports 12F down | D213 runs 2D only, reports 45F down | HOST_TESTED |
| RGMII before DONE | F133 PG pins IO-disable | D213 PE pins IO-disable | pin-mux rule, firmware |
Open: whether the 45F rails are switched (R8.5-C had FPGA_PWR_EN from the F133); with the D213 as configuration
master, the D213 binding currently treats VCC_PG as always good (`d213/fpga45_loader/include/d213_fpga45.h`).

## 4. Recovery and programming access (all headers 2.54 mm or 1.27 mm as space allows)
| Target | Access | Purpose | Notes |
|---|---|---|---|
| F133 | UART0 3-pin header (R8.5-C J10) | console | 3.3 V TTL |
| F133 | USB0 (Type-C) + FEL button (R8.5-C SW2 holds NOR_RESET_N low during reset) | boot-ROM USB recovery when the NOR is unreadable | FEL fall-through is NOT documented for this condition — bench item carried from R08 |
| 64 MiB NOR | 2×5 SPI0 header (R8.5-C J2) + NOR_RESET_N | external programmer when the NOR is erased/bad (spec §5.3 "single point of failure") | the F133 must be held in reset so its SPI0 pins are hi-Z: CONFIRM F133 reset pin state; WP# reachable for unlocking |
| 12F | 10-pin JTAG (R8.5-C J5 layout: VTref, TMS, TCK, TDO, TDI, PROGRAMN) | SRAM load / debug without the F133 | jumper to power the FPGA rails without firmware (R8.5-C J11) |
| 45F | 10-pin JTAG, same layout | SRAM load / debug without the D213 | same jumper rule if its rails are switched |
| D213 | UART0 PA0/PA1 3-pin header | console, boot log (flashless-proof evidence) | |
| D213 | USB0 recovery: test points + a boot-mode strap/button; F133 keeps USB1 VBUS off during recovery | vendor USB upgrade from a PC | `f133/graphics_link/README.md` open item 3 |
| D213 | JTAG alternate on PA8–PA11 (JTAG_DO/DI/MS/CK in the pin table) — 4-pin test points | CPU debug | confirm with the D21x hardware guide |
| D213 | DNP footprint for a boot NOR on PB0–PB5 | fallback if flashless start fails (spec §7.2) | |
