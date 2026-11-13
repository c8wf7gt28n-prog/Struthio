# AI change report — R27

- Platform/model: Claude Code (Anthropic), cloud session.
- Input package revision: R26 (commit 94cbc3b), plus the PCB R22 work committed beside it in `hardware/slim4_r22_wip` (commits 93b3ece to 2946c78), now moved into the package.
- Output revision: R27, made of PCB R22, CASE R12 (unchanged parameters), ACRYLIC R2 and DISPLAY FLEX R1.
- Parent layers edited: PCB (R21 → R22, owner-approved in the R22 sessions) and DISPLAY FLEX (new). CASE and ACRYLIC are untouched; only their derived harness reserves follow the R22 connector positions.
- Source files changed:
  - `LAYERS/01_PCB/*` (R22 board, library, docs, `R22_FROM_R21/` including the new `r22_land.py`), `LAYERS/04_DISPLAY_FLEX/*`.
  - `CHECKS/export_pcb_layer.py` (new), `convergence_check.py`, `build_builder_packs.py`, `build_pcb_viewer_data.py`, `build_viewer_bundle.py`, `render_review.py`, `make_manifest.py`, `COMPONENT_ENVELOPES_R22.json`.
  - `LAYERS/02_CASE/build_r12.py` (data paths and labels), `export_layer_formats.py` (labels).
  - Studio: `app.js`, `eye.js`, `index.html`, `sw.js`, `manifest.webmanifest`.
  - Docs: `DECISIONS_R27.md`, `PRODUCTION_GATES.md`, `README.txt`, `AI_HANDOFF.md`, `ASSEMBLY/ASSEMBLY_SEQUENCE.md`, `REFERENCES/`.
- Dimensions or coordinates changed:
  - Board outline, thickness, switches, J1 and J2 are unchanged.
  - J3 is at (−23.5, 66.0); its 2-pin library footprint has a new origin.
  - J4 moved 2.7 mm inboard.
  - U11 and U12 moved to (4.6, 12.2) and (−4.0, 14.0).
  - C603 moved 0.15 mm.
  - The L1–L3 lands changed.
  - The full list is in `LAYERS/01_PCB/README_PCB_LAYER.md`.
- Shared datum and units preserved: yes.
- PCB edits: 11 scripted edits. `build_r22.sh` reproduces the board from R21 with identical parts, pads, tracks, vias and nets (verified 2026-10-07). KiCad 7.0.11 DRC: 0 / 0 / 0.
- Fit and interference checks: 78 PASS, 3 FAIL, 9 GATE, 3 INFO, over 327 pair evaluations. The FAIL rows are:
  - C6: the Startek panel against the R12 pocket.
  - F1 and I1: the J5 body and tab against the rear post at (40.75, 108).

  All three are case-pass items, deferred by the owner. N1 (the flex's J1 fingers against the board) passes.
- Validation:
  - Builder files rebuilt: the R22 order has 13 Gerber layers and 0 mask openings at vias; all 6 printed STLs are watertight.
  - Flex preview DRC: 0 / 0 / 0.
  - The R22 layer JSON was validated through the R21 re-export.
  - Renders regenerated.
- Production gates closed or still open: the R21 review hold is closed by R22 (`LAYERS/01_PCB/RELEASE_GATES.md`). Still open: U1 stock, the flex pin table, bring-up, the case pass and the R26 physical gates (`PRODUCTION_GATES.md`).
- Known limitations:
  - No schematic exists; the review worked from the netlist.
  - The display flex cannot be ordered until Startek's pin definition is in hand.
  - Firmware is not part of this package.
