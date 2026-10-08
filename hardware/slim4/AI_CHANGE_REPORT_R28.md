# AI change report — R28

- Platform/model: Claude Code (Anthropic), cloud session.
- Input package revision: R27 (commit 462009d).
- Output revision: R28, made of PCB R23, CASE R12 (set aside; battery envelope and FPC reserve follow the board), ACRYLIC R2, and the firmware in `firmware/slim4` (R6).
- Parent layers edited: PCB (R22 → R23, asked for by the owner: "put the adapter cable into the motherboard PCB as one … four plug-and-play connections … make firmware too"). The DISPLAY FLEX layer is retired to `REFERENCES/DISPLAY_FLEX_R1/`. CASE and ACRYLIC are set aside by the owner.
- Source files changed:
  - `LAYERS/01_PCB/*`: R23 board, library, docs, `R23_FROM_R22/` (new).
  - `CHECKS/export_pcb_layer.py` (cut-outs from the board), `convergence_check.py`, `build_builder_packs.py`, `build_pcb_viewer_data.py`, `build_viewer_bundle.py`, `render_review.py`, `make_manifest.py`, `COMPONENT_ENVELOPES_R23.json`.
  - `LAYERS/02_CASE/build_r12.py` (data paths, cell 34 × 50 × 7 at Y 43.5, FPC reserve ends at the board back), `export_layer_formats.py` (labels).
  - Studio: `app.js`, `eye.js`, `index.html`, `sw.js`, `manifest.webmanifest`.
  - Docs: `DECISIONS_R28.md`, `PRODUCTION_GATES.md`, `README.txt`, `QC_REPORT.txt`, `CHANGELOG.md`, `AI_HANDOFF.md`, `ASSEMBLY/ASSEMBLY_SEQUENCE.md`, `REFERENCES/`.
  - Firmware: `firmware/slim4` (ILI9881C panel, R23 docs, `tools/check_pinmap.py` against the R23 board).
- Dimensions or coordinates changed:
  - Board outer outline, thickness, switches and J2 are unchanged.
  - Battery window bottom edge Y 73 → 70.5.
  - J1 moved from the back of the bottom tab to the front at (1.9, 76.0); J3 to (−24.8, 67.9); J4 (−44.0, 113.7); J5 (44.3, 111.6); new Q2 at (−21.4, 56.0).
  - The full list is in `LAYERS/01_PCB/README_PCB_LAYER.md`.
- Shared datum and units preserved: yes.
- PCB edits: 4 scripted edits (12–15). `build_r23.sh` reproduces the board from R22 with every track and via identical. KiCad 7.0.11 DRC: 0 / 0 / 0.
- Fit and interference checks: 78 PASS, 3 FAIL, 9 GATE, 3 INFO, over 317 pair evaluations. The FAIL rows (C6 panel pocket; F1, G1 rear shell against J3/J4/J5) are the case pass the owner set aside. N1 (J1 against the panel pin table) passes 40/40.
- Validation: DSI per-pair and per-layer timing; DSI and GPIO pads against the ESP32-P4 pin table; firmware clean build with ESP-IDF v6.1 (0 warnings) and its pin check against the board (19/19).
- Production gates closed or still open: `LAYERS/01_PCB/RELEASE_GATES.md` and `PRODUCTION_GATES.md`. Open: U1 stock, bring-up, the case pass.
- Known limitations:
  - No schematic exists; reviews work from the netlist.
  - Nothing has been built: the panel image, audio and charging are first-boot checks.
  - The panel init table is GPL-2.0 (from the Linux kernel); replace it with Crystalfontz's sample code if the firmware is ever distributed under a non-GPL licence.

## Update 2026-10-08: the R23 / R6 simulation audit

- Board unchanged. Q2's reversed-pack behaviour with USB connected analysed against the BQ24074 datasheet (IBAT(SC) 4–11 mA, VBAT(SC) 1.6–2.0 V) and the AO3401A threshold (0.5–1.3 V): bounded, no part outside its ratings; claims corrected in every document.
- Firmware R7: console, USB backlight cap, reversed-pack warning, safe charge suspend (see `CHANGELOG.md`).
- Builder pack: `PROJECT_DOCS/`.

## Update 2026-10-08: the R7 review

- Firmware R8: the three power-policy defects the review reproduced are fixed; `tests/host` (29 cases) runs the unmodified `slim4_power.c` on a host. The review's own harness passes 6 of 7 on R8; the seventh expects switch-off after one reading, which R8 deliberately qualifies over 2 s.
- Reversed-pack wording: an untested steady-state analysis, not a no-damage promise.
