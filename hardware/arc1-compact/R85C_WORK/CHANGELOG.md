# R8.5 changelog (ECP5-45F change order; relative to R08 commit 66bed02)

R05_BASELINE, R06_WORK, R07_WORK, R08_WORK and the root handoff files are byte-for-byte unchanged (runner step
`frozen_r05_r06_r07_r08_unchanged`). The R08 regression (which nests R07 and R06) runs in a scratch copy.

## Hardware (cad/gen/design.py → regenerated KiCad, ERC 0/0)
- U18 T35F400C3 → **LFE5U-45F-6BG381C** (symbol from the Lattice pinout CSV, 381 balls; KiCad library footprint).
- Power: U9 retuned to **1.095 V** (82.5k/100k); new **U30 TLV75525P** VCCAUX 2.5 V + FB2 ferrite; U10 → 3V3_FPGA for all
  VCCIO; **one shared enable** (VCC, VCCIO, VCCAUX together); FPGA_VCC_PG → F133 PD1; **J11** power override for JTAG service;
  PE0 drives the enable through 1 kΩ.
- sysCONFIG slave SPI: CFG = 001, 4.7 kΩ on PROGRAMN/INITN/DONE/SN/JTAG, 1 kΩ CCLK pull-up + 33 Ω series, HOLDN pull-up,
  PROGRAMN via 470 Ω from PE8 (open-drain use), INITN → PD0, DONE → PE9; J5 JTAG (ARM-10 layout, pin 10 = PROGRAMN).
- **Removed:** U19 W25Q32 configuration flash, U26 74LVC07 + 6 × 1.5 kΩ switched pull-downs, T35 PLL rail, TEST_N/CSI pulls.
- IRQ, LED, UART moved to bank 0 (hot-socket tolerant); UART RX 1 kΩ series.
- Net renames T35_* → FPGA_*, CDONE → DONE, CRESET → PROGRAMN (full table: docs/T35_TO_ECP5_DELTA_R85.md).

## FPGA (fpga_ecp5/, replaces fpga/ + Efinity flow)
- Vendor-neutral top with real tri-states and an ecppll PLL; AJOB v1 job engine (TRANSFORM_BATCH) replacing the loopback;
  pipelined bit-exact transform on 8 × MULT18X18D; AMBX v3 (perf counters, ABORT).
- LPF **generated** from the board plan; Yosys/nextpnr-ecp5/ecppack build with report, pinned tool versions and a byte-identical
  reproducibility check.
- tb_ecp5_top: R08 suite + 11 AJOB cross-simulation cases + ABORT + CE# stuck injection.

## Firmware
- New: ecp5_cfg (sysCONFIG loader, container, streaming, probe), fpga_link (AMBX v3), accel_job (AJOB framing),
  accel_service (P0–P6), board model + 33 failure-injection cases + 6 mutants; diag image S4/S5 ported.

## Analysis / docs
- Pin matrices (F133 mux, 381-ball map, bank table), margins incl. ECP5 rail budget and PSRAM pad timing, benchmark
  (ISS + link model) with the HARD STOP finding, delta table, failure-injection table, 45F/85F migration, power,
  configuration, JTAG and PSRAM dossiers. R08 documents moved to docs/inherited_r08/ (valid except FPGA content).

---

# R08 changelog (relative to R07-draft-1)

R05_BASELINE, R06_WORK, R07_WORK and the root handoff files are byte-for-byte unchanged. The runner verifies this
against the root manifest and git. The R07 (and nested R06) regression runs in a scratch copy, so no prior evidence is
modified. The pre-change R07 baseline run is archived in `evidence/r07_baseline_prechange/`.

## Corrective handoff v1.0 integrated (owner decisions D-01 … D-07)
- **Boot:** 32 MiB SPI NOR (W25Q256JVFIQ) on SPI0 CS0. BOOT-SEL straps changed from 11 (SD first) to **00** (NOR first) with 3.3 kΩ pull-downs.
- **SPI0 sharing:** the T35 moved behind 4 × SN74LVC1G125 isolation buffers with a GPIO chip-select (PE4). The MISO buffer is enabled only by the T35 chip-select.
- **Recovery:** FEL button (NOR /RESET), RESET button, clip/LA access, recovery dossier.
- **microSD = games only** (never in the boot list). Library/package validation and power-fail-safe saves, host-tested.
- **USB:** Type-C sink + USB0 device/FEL; USB1 host removed; TUSB320LAI reports the source current.
- **Audio:** 2 × MAX98357A on I2S2 (L/R by SD_MODE).
- **Panel:** deferred to R09; LVDS mapping preserved.

## R08 electrical closure
- MN820 MISO margin fixed with a buffer (+0.40 V instead of +0.02 V).
- PSRAM: switched VDD (AND of F133 request and delayed CDONE), switched start-up pull-downs (74LVC07), 100 kΩ static, CE# pull-up to the switched rail, supervisor PG → T35. RTL power guard + AMBX v2 status.
- T35 rails: own 1V2 (F133-enabled) → PG → 3V3_T35 (VCC before VCCIO).
- Supervisors on 3V3 (core/DRAM enable after 13 ms), VDD_CORE (F133 RESET 86 ms), PSRAM_VDD.

## New native engineering sources
- KiCad 9 hierarchical schematic (9 sheets, 329 components) generated from `cad/gen/design.py`. ERC 0/0, netlist, PDF.
- Cross-check: netlist ↔ plan ↔ footprints ↔ Efinity ↔ RTL ↔ firmware pins.
- Board rule checker (11 rules) + 16 tests (15 hazard mutations).
- Margin analysis with tagged inputs.
- RTL: `psram_power_guard.sv`, `mbx_regs_r08.sv`, `arc1_t35_top_r08.sv`, `tb_top_r08.sv`.
- Firmware: `spi_nor.c`, `flash_layout.c`, `game_lib.c`, `crc32.c` + tests + 4 mutants; generated `board_pins_r08.h`.
- F133 diagnostic boot0 image (`f133_diag`).
- Efinity project generator (fixes R06 PLLIN/device/bank/SDC errors).
- Reports: BOM candidates, pin table, SLIM4 reuse decisions.

## Tooling
- KiCad 9.0.9 from the official PPA (Launchpad-published signing key) for native ERC.
- Efinity: not available (NOT_RUN).
