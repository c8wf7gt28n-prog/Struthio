# REFERENCES — reference only

Nothing in this folder is a layer authority. Current geometry lives in `LAYERS/` (PCB R23, CASE R12, ACRYLIC R2) and `ASSEMBLY/`.

| Folder | What it is | Why it is kept |
|---|---|---|
| `PCB_R22/` | the R22 board, project, footprint library, layer JSON, DRC report and release gates as delivered in R27 (superseded by PCB R23) | the input of `LAYERS/01_PCB/R23_FROM_R22/build_r23.sh` |
| `DISPLAY_FLEX_R1/` | the display adapter flex generator for the R22 J1 port and the Startek panel (superseded: R23 takes the Crystalfontz panel's own tail) | the flex generator and its preview, should an adapter be needed again |
| `PCB_R21/` | the R21 board, project, footprint library, layer JSON, DRC report and release gates as delivered through R26 (superseded by PCB R22) | the input of `LAYERS/01_PCB/R22_FROM_R21/build_r22.sh`; its layer JSON gives `CHECKS/export_pcb_layer.py` the board outline and the part heights |
| `R10_CONTEXT/` | R10 fit-study assembly STEP (superseded by CASE R11) | the only in-package geometry of the R10 baseline audited in `CHECKS/R24_BASELINE_AUDIT.md` |
| `SLIM4_R3_INTEGRATION/` | SLIM4 R3 integration study, 2026-10-03 (superseded) | source of the viewer's SHOW R3 CASE CAD overlay (`case-r3-data.js`), of the 1.79 mm LCD top-border assumption used by check C4, and of the acoustic-volume study cited by J4 |

Each folder has its own README. Inherited files are kept byte-for-byte as delivered; notes about them are in these READMEs.
