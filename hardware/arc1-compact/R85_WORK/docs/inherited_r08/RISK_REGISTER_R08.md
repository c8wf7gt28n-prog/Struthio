# R08 risk register (supersedes the R07 ranking where stated; R07_WORK/RISK_REGISTER.md is unchanged)

Status: **HOLD / PARTIAL**. P0 items remain open, so no fabrication release is possible.

| Rank | ID | Risk | R08 action | Status | Evidence | Owner / next |
|---|---|---|---|---|---|---|
| P0 | RK-BOOT-NOR (was RK-BOOT-STRAP/-EFUSE/-DOC) | NOR-first boot rests on the D1-H boot table; the eFuse BOOT_MODE of the delivered lot is unknown; the BROM's NOR opcode/format and **fall-through to FEL are undocumented** | straps 00 (0.794 V worst case vs 0.96 V), T35 isolated, diag prints pad/eFuse/fast-boot, clip path guaranteed | **OPEN** (design done; facts missing) | BOOT_TRACE_DOSSIER.md; rule `boot_straps_00` + 2 negative tests | Allwinner V7; first article 2.2–2.6 |
| P0 | RK-T35-EDA | no native Efinity fit/timing/bitstream | importable project, ISF, SDC and pins generated from the schematic; R06 errors fixed (PLLIN pin, device name, banks, SDC) | **OPEN** (NOT_RUN) | fpga/efinity/*; crosscheck C | owner PC (RUN_EFINITY_LOCALLY.md) |
| P0 | RK-MN-PWR | MN820 supply direction/current only inferred from the VM820C reference | host supplies via U11; budget uses a 1.6× allowance | **VENDOR_OPEN** | POWER_TREE_AND_RESET.md | Bridgetek V1 |
| P0 | RK-PCB | no layout, DRC or footprint review | native schematic, ERC 0, netlist, 1:1 cross-check | **OPEN** (R09) | SCHEMATIC_CROSSCHECK.md | R09 |
| P0 | RK-USB-BUDGET | estimated ≈ 0.88 A even with the amplifiers muted: does not fit a 500 mA default source; panel/backlight not yet counted | TUSB320 current reporting + firmware policy; requirement stated | **OWNER DECISION** | ELECTRICAL_MARGINS_R08.md | owner (≥ 1.5 A Type-C or battery) |
| P1 | RK-MN-VOH | R07 margin +0.02 V | **closed by design**: SN74LVC1G125 buffer, +0.40 V at the buffer input, +0.72 V at the F133 | CLOSED (calc) | margins; rule `mn820_miso_buffered` + negative test | bench 3.1 |
| P1 | RK-PSRAM-VOH / RK-PSRAM-PU | R07 2.2 kΩ load outside the VOH test condition | **closed by design**: switched supply + CDONE-gated switched pull-downs; user-mode load 34 µA; unpowered pins ≤ 0.368 V | CLOSED (calc + RTL) | PSRAM_POWER_R08.md | AP Memory V5 confirmation |
| P1 | RK-PSRAM-BROWNOUT | R07: PSRAM power loss undetected | **closed in RTL**: supervisor PG + guard + sticky POWER_LOST + READY gating + EPOCH | CLOSED (RTL_SIMULATED P0–P4) | tb_top_r08 | bench 4.5 |
| P1 | RK-NOR-VOH | 3.3 kΩ BOOT-SEL1 pull-down loads NOR DO with 1.04 mA; VOH spec is at 0.1 mA | OPEN (same class as the old PSRAM issue) | **OPEN** | margins | Winbond V6 IBIS |
| P1 | RK-3V3-SUP | the G33 supervisor dead band 3.02–3.14 V is below the T35 VCCIO minimum | T35 optional; PSRAM separately supervised | **OPEN** (FAIL in margins) | margins | R09 decision |
| P1 | RK-NOR-LIFECYCLE | W25Q256JVFIQ lifecycle unknown (handoff warns of an NRND variant) | OPEN | **VENDOR_OPEN** | NOR_BOOT_AND_FLASH.md | Winbond V6 |
| P1 | RK-BT-DECODE | 0xFF RAM_CMD vs host-command decode on silicon | unchanged from R07 | OPEN | R07 | bench 3.2 |
| P1 | RK-F133-IMG | images built, never executed | R08 diag image adds NOR/T35/PSRAM stages | BUILD_ONLY | f133_diag | first article |
| P1 | RK-FOOTPRINT | 3 generated + 3 SLIM4 + 2 placeholder footprints; library land patterns not yet reviewed against datasheets | pad-name cross-check only | OPEN | crosscheck B | R09 #5 |
| P1 | RK-F133-PDN | F133 per-rail currents, decoupling and crystal CL unknown; pin 47 DZQ / EPAD / VRA terminations taken from a D1s schematic | MangoPi reference practice; DNP options | OPEN | reference_design_notes.md | Allwinner V7 |
| P2 | RK-PSRAM-FAULT-BP | a load-switch fault with EN high back-powers the PSRAM for about 1.2 µs before PG falls | measured in RTL sim; accepted | ACCEPTED | tb_top_r08 P4 | — |
| P2 | RK-SPI1-TIMING | 30 MHz SPI1 read relies on an assumed F133 setup time | bring-up at 20 MHz | CONDITIONAL | margins | bench + F133 UM |
| P2 | RK-T35-TUSER | CDONE_DLY delay depends on the LVC1G17 VT+ (not transcribed) | ≥ 0.96 ms calc (needs ≥ 0.1 ms) | CONDITIONAL | margins | R09 datasheet |
| P2 | RK-AUDIO | I2S2 mux and audio quality unproven; LRCLK restrictions | 2 × MAX98357A per owner | OPEN | POWER_TREE_AND_RESET.md §5 | bench stage 5 |
| P2 | RK-SPI-QUAD | quad SPI to the BT820 would need bidirectional level translation (the buffer is unidirectional) | single SPI baseline | DEFERRED | — | R10+ |
| R09 | RK-PANEL | panel, LVDS, backlight | deferred per D-07 | DEFERRED | PANEL_INTERFACE_R09.md | R09 #1 |
