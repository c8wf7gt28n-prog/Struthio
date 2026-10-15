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
