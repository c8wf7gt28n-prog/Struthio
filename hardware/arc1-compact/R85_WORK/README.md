# ARC-1 Compact: R8.5 work area – ECP5-45F design change order

Start with `STATUS_R85.md`. R05/R06/R07/**R08 stay frozen**. R8.5 re-runs the R08 suite (which nests R07 and R06) as
regression in a scratch copy.

```
python3 R85_WORK/tools/run_r85_checks.py              # everything (from hardware/arc1-compact/)
python3 R85_WORK/tools/run_r85_checks.py --skip-r08   # R8.5 steps only
```
Tools beyond R08: Yosys 0.33, nextpnr-ecp5 0.6, Project Trellis 1.4 (ecppack/ecppll), openFPGALoader 0.12 (JTAG,
optional); exact versions and hashes are in each run's `TOOL_VERSIONS.txt`.

| Path | Content | Evidence |
|---|---|---|
| `STATUS_R85.md`, `RISK_REGISTER_R85.md`, `CHANGELOG.md`, `EVIDENCE_LEDGER.json` | outcome, gates G1–G10, HARD STOP options, risks, per-claim evidence | — |
| `cad/` | native KiCad 9 project `ARC1_R85` (9 sheets incl. `fpga_ecp5.kicad_sch`), ERC, netlist, PDF; `gen/` = design source; `check/crosscheck_r85.py` | TOOL_VERIFIED_NATIVE |
| `board/` | `r85_board_plan.json`, **`F133_PINMUX_MATRIX_R85.csv/.json`**, **`ECP5_BALL_MAP_R85.csv`** (all 381 balls), `ECP5_BANK_TABLE_R85.csv`, rule checker + negative tests | HOST_TESTED (self-authored) |
| `fpga_ecp5/` | RTL, testbench, generated LPF, open-toolchain Makefile, build scripts (see its README) | RTL_SIMULATED, OPEN_TOOLCHAIN_ROUTED |
| `firmware/` | R08 NOR/layout/library + R8.5 ECP5 loader, AMBX v3 link, AJOB, P0–P6 service, board model, FIT tests, mutants, `tools/ajob_vectors.c`, `tools/bench_link.c` | HOST_TESTED |
| `f133_diag/` | F133 boot0 diagnostic image with ECP5 probe | BUILD_ONLY |
| `analysis/` | margins (`electrical_margins_r85.py`), benchmark result JSON | DERIVED_WITH_CALC / ISS_COUNTED |
| `tools/` | runner, pin matrix + LPF generator, reports, delta table, failure-injection table, 45F/85F migration, `bench/` (RV64IM ISS + kernels + benchmark) | — |
| `docs/` | ECP5 power, configuration/protocol/state machine, JTAG recovery, PSRAM, benchmark, failure injection, delta table, margins, pin table, interconnect, migration; `inherited_r08/` | — |
| `sources/lattice/` | Lattice document list with URLs + SHA-256, extracted facts, pinout and migration CSVs (no PDFs redistributed) | VERIFIED_BY_VENDOR_DOC |
| `handoff_inputs/` | the change order (.docx + extracted text) | input |
| `evidence/` | runner output per run (`LATEST.txt`) | — |
