# CASE R13 symmetric controls — prototype, reference only

Supplied with the owner's Stru-dio 0.6.0 workspace (2026-10-09/10). Three control parts redrawn from the CASE R12 caps and DART rocker so that what shows on the front is mirror-symmetric about the panel body's centreline (X = +1.2 mm), while the parts that press the switches stay where the switches are. **Not a case release and not print-ready:** the R12 shell holes do not fit the shifted caps, and guides, retention, travel stops and the shell outline are not drawn. CASE R12 is still the package's case layer, and the case remains set aside by the owner.

| File | What it is |
|---|---|
| `STEP/R13_SYMMETRIC_L.step`, `_R`, `_DART` | the three parts (single solids) |
| `STEP/BEZEL_REFERENCE_L.step`, `_R` | 2 mm bezel rails between panel and caps: references for a future shell, not parts |
| `STL/R13_SYMMETRIC_*.stl` | the same parts as meshes (mm) |
| `r13_symmetric_controls.py` | the CadQuery generator (expects the R31 builder pack's case STEP files under `input/`; not run in this package) |
| `GEOMETRY_CHECKS.json`, `SYMMETRY_PREVIEW.png`, `SOURCE_README.md` | as supplied |

**Checked here (R32):**
- The three STLs are closed meshes: L 3848 triangles, 793.6 mm³; R 3724, 774.6 mm³; DART 4096, 1232.4 mm³.
- Above Z 5.66 (the visible part), the L and R caps run from 35.55 to 48.75 mm either side of X = +1.2 and the DART rocker ±24.5 mm about it: symmetric as claimed.
- SW1–SW7, J1–J5 and the board outline are at the same positions in PCB R27 as in R26, so the parts still sit on the switches they were drawn for.

**Not checked:** travel, the D2LS stop stack, the DART pivot and force balance (its visible face is offset from the pivot), fit in any shell, printing. The panel position the parts were cleared against (Z 5.00–6.85) is the old case's assumption.

The studio shows the three parts with LAYERS → CASE → *R13 symmetric controls · prototype* (off by default; `case-r13-data.js`, written by `CHECKS/build_r13_reference_data.py`).
