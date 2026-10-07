# PCB R21 — superseded by PCB R22

The R21 board as delivered through package R26, byte-for-byte: `SLIM4_R21.kicad_pcb`, `SLIM4_R21.kicad_pro`, `fp-lib-table`, the R21 copy of `SLIM4.pretty`, `SLIM4_R21_PCB_LAYER.json`, `NATIVE_KICAD_DRC.txt`, and `RELEASE_GATES_R21.md` (the R21 review hold, closed by R22).

Why it is kept:
- `LAYERS/01_PCB/R22_FROM_R21/build_r22.sh` rebuilds R22 from this board, one scripted edit at a time.
- `CHECKS/export_pcb_layer.py` takes the board outline polygon and the part heights (`z`) from `SLIM4_R21_PCB_LAYER.json`, which are not stored in the KiCad file in that form.

Known error in `SLIM4_R21_PCB_LAYER.json`: 80 pads on back-side parts rotated 90° or 270° (for example U2, C104, C110) are mirrored about their part's centre, and their `rot` values differ from the board. The KiCad board is correct. The exporter that writes the R22 layer file places pads as pcbnew does, so R22 does not have this error.

Do not order from this board: R21 has the land-pattern and USB errors listed in `LAYERS/01_PCB/ELECTRICAL_REVIEW_R22.md`.
