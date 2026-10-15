# ARC-1 Compact: R08 work area (PASS 8)

Start with `STATUS_R08.md`. R05, R06 and R07 remain frozen; R08 reruns R07 (which reruns R06) as regression.

```
python3 R08_WORK/tools/run_r08_checks.py              # everything, ~8 min (from hardware/arc1-compact/)
python3 R08_WORK/tools/run_r08_checks.py --skip-r07   # R08 steps only, ~2 min
```
Extra tools beyond R07: **KiCad 9 (`kicad-cli`, ERC needs ≥ 8)**. Optional: Efinity (owner PC).

| Path | Content | Evidence |
|---|---|---|
| `STATUS_R08.md`, `RISK_REGISTER_R08.md`, `CHANGELOG.md`, `EVIDENCE_LEDGER.json` | outcome, gates, risks, changes, per-claim evidence | — |
| `cad/` | **native KiCad 9 project**: `ARC1_R08.kicad_pro`, root + 9 sheets, `symbols-and-footprints/`, `ERC.txt`/`ERC.json`, `NETLIST.xml`, `ARC1_R08_schematic.pdf`; `gen/` is the design source (`design.py`, `parts.py`, `gen_kicad.py`); `check/crosscheck_r08.py` | TOOL_VERIFIED_NATIVE (ERC/netlist) |
| `board/` | `r08_board_plan.json` (exported), `check_board_r08.py` + negative tests | HOST_TESTED (self-authored rules) |
| `analysis/` | `electrical_margins_r08.py` (+ JSON): DC levels, timing, regulators, supervisors, VBUS budget | DERIVED_WITH_CALC |
| `fpga/` | `rtl/` (power guard, AMBX v2 regs, R08 top), `tb/tb_top_r08.sv`, `efinity/` (generator, project, ISF, SDC, pins, local-run instructions, NOT_RUN note) | RTL_SIMULATED / NATIVE_EDA_NOT_RUN |
| `firmware/` | NOR driver, flash layout + A/B journal, microSD game library + saves, CRC32, generated `board_pins_r08.h`; mock + tests + mutants | HOST_TESTED |
| `f133_diag/` | F133 diagnostic boot0 image (S0–S5) | BUILD_ONLY |
| `docs/` | boot-trace, flash-image and recovery dossiers; power/reset/audio; PSRAM power; architecture; engineering change; schematic cross-check; interconnect matrix; pin table; margins; manufacturing/BGA; SLIM4 reuse decisions; first-article debug; vendor-open items; panel interface (R09); R09 plan | — |
| `sourcing/BOM_CANDIDATES.csv` | grouped BOM with MPN/LCSC status | candidates |
| `sources/` | manufacturer facts (URL + SHA-256 per document, no PDFs redistributed) | VERIFIED_BY_VENDOR_DOC |
| `handoff_inputs/` | the corrective handoff v1.0 (.docx + extracted text) | input |
| `evidence/` | runner logs per step, `summary.json`, manifests; `r07_baseline_prechange/` | — |

Regenerating the 3 SLIM4-copied footprints needs `SLIM4_PRETTY=<SLIM4 R26 SLIM4.pretty>`. Without it the committed
copies are kept, so the runner works either way.
