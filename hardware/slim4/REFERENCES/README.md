# REFERENCES — reference only

Nothing in this folder is a layer authority. Current geometry lives in `LAYERS/` (PCB R21, CASE R11, ACRYLIC R1) and `ASSEMBLY/`.

| Folder | What it is | Why it is kept |
|---|---|---|
| `R10_CONTEXT/` | R10 fit-study assembly STEP (superseded by CASE R11) | the only in-package geometry of the R10 baseline audited in `CHECKS/R24_BASELINE_AUDIT.md` |
| `SLIM4_R3_INTEGRATION/` | SLIM4 R3 integration study, 2026-10-03 (superseded) | source of the viewer's SHOW R3 CASE CAD overlay (`case-r3-data.js`), of the 1.79 mm LCD top-border assumption used by check C4, and of the acoustic-volume study cited by J4 |

Each folder has its own README. Inherited files are kept byte-for-byte as delivered; notes about them are in these READMEs.
