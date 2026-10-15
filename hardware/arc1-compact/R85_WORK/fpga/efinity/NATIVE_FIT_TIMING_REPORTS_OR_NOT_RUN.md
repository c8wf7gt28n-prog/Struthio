# Native Efinity fit / timing / bitstream: **NOT_RUN** (gate G5 open)

| Item | Status |
|---|---|
| Efinity synthesis (efx_map) | NOT_RUN: Efinity is not installed in this environment (licensed tool; owner PC) |
| Interface Designer check_design | NOT_RUN |
| Place and route (efx_pnr) | NOT_RUN |
| Static timing (setup/hold) | NOT_RUN: **no timing claim exists** |
| Bitstream (efx_pgm) | NOT_RUN |
| Pin placement legality per the Efinity package database | NOT_RUN; the balls/resources/banks agree with the T35-PINOUT v1.5 data (crosscheck C) |

What exists instead (not a substitute):

- **Open-source Yosys `synth_efinix`:** 1312 EFX_LUT4, 858 EFX_FF, 50 EFX_RAM_5K, 785 EFX_ADD, 2 EFX_GBUFCE. This is a mapping estimate only, with no placement and no timing.
- **RTL simulation:** tb_top_r08 passes with Icarus Verilog.
- **Lint:** Verilator `-Wall` is clean.

Fill this file from the native reports per `RUN_EFINITY_LOCALLY.md`.
