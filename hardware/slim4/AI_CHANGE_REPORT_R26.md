# AI change report — R26

- Platform/model: Claude Code (Anthropic), cloud session
- Input package revision: R25 (this repository, commit c7f62b4; studio 1.1)
- Output revision: R26 — PCB R21 (unchanged), CASE R12, ACRYLIC R2
- Parent layer edited: CASE and ACRYLIC (one source, `LAYERS/02_CASE/build_r12.py`); PCB none
- Source files changed: `LAYERS/02_CASE/build_r12.py` (from `build_r11.py`), `LAYERS/02_CASE/export_layer_formats.py`, `CHECKS/convergence_check.py`, `CHECKS/render_review.py`, `CHECKS/build_builder_packs.py`, `CHECKS/build_pcb_viewer_data.py`, `CHECKS/build_viewer_bundle.py`, `CHECKS/make_manifest.py`, `app.js`, `eye.js`, `index.html`, `sw.js`, `manifest.webmanifest`; new `DECISIONS_R26.md`, `CHECKS/BOM_SOURCING_R21.json`
- Dimensions or coordinates changed (before → after): see the table in `CHANGELOG.md` (R26). Parameters added to `P`: `lcd_tape` 0.10, `dart_trunnion_clear` 0.10, `film_edge_inset` 0.20, `film_stack`, `film_vent_r` 0.3, `lap_clear` 0.10, `lap_tape` 0.10; changed: `lcd_z0` 5.20 → 5.10, `dart_boss_z0` 4.45 → 4.30. New parts: DISPLAY TAPE FRAME 0.10, LAP TAPE RING 0.10.
- Shared datum and units preserved: yes (mm; R21 PCB XY, Y down; board bottom Z=0; +Z front)
- PCB edits: none. `SLIM4_R21.kicad_pcb` SHA-256 daac1da0… unchanged (check A1). LCSC numbers for 14 parts live beside the board in `CHECKS/BOM_SOURCING_R21.json`.
- Fit/interference checks run and results: `python -B CHECKS/convergence_check.py` → **converged, 79 PASS, 0 FAIL, 9 GATE, 3 INFO**; 326 pair evaluations over 287 distinct pairs (284 at rest, 18 flaps and plunger pressed, 12 DART left, 12 DART right); 21/21 solids valid.
- STEP/STL/vector/DRC validation run and results: all CASE/ACRYLIC exports regenerated; builder files rebuilt (six printed-part STLs watertight after the boss-floor fix; STEP volumes equal the CAD); KiCad 7.0.11 DRC on R21 0 / 0 / 0; renders regenerated, including the new section F.
- Production gates closed or still open: closed E7, L5, L6 and the owner decisions in `DECISIONS_R26.md`; open: the 9 GATE rows (B8, C4, D5, D11, D12, H4, J5, K3, L4) and R21's electrical review — the full list is `PRODUCTION_GATES.md`.
- Known limitations: tape and cover-glass behaviour, lap retention and trunnion wear are modelled as geometry only and need the EVT prototype; the speaker lead method depends on the CMS-18138A-SP contact layout.
