# Reference only — SLIM4 R3 integration study (2026-10-03)

Not an authority. Superseded by CASE R11 (`LAYERS/02_CASE`) on the locked R21 PCB (`LAYERS/01_PCB`). R3 assumed a 1.0 mm board; R21 is 1.2 mm. In R24 this folder was `R21_REFERENCE/CAD_REFERENCE/SLIM4_R3/`; the five files are unchanged.

Kept because:
- the viewer's SHOW R3 CASE CAD overlay (`case-r3-data.js`) is triangulated from `SLIM4_R3_integration.step`;
- check C4 relies on the R3 assumption of a 1.79 mm inactive border at the top of the LCD;
- check J4 cites its chamber-volume study (about 1.94 cc per side of CAD geometric capacity, and the recommendation to compare 1.0 / 1.5 / ~2.0 cc).

Datum: in `SLIM4_R3_integration.step`, Z runs rearward from the device front (caps Z −1.5…0, LCD 1.2…2.95, board 5.5…6.5). The shared R25 datum has the board bottom at Z=0 and +Z toward the front; `case-r3-data.js` is mapped with z′ = 6.5 − z.

Notes on `INTEGRATION_README.md` (the original R3 text, kept verbatim):
- It names `PCB_MECHANICAL_RESERVE.step`, `PCB_MECHANICAL_RESERVE.dxf` and `ELECTRICAL_HANDOFF.md`. None is included in this package, and none was in the R24 delivery.
- The original lost the space before some numbers (for example "remains11.5 mm", "compare1.0/1.5").

`build.py` (CadQuery, NumPy, Shapely, matplotlib) rewrites `SLIM4_R3_integration.step`, `checks.json` and `placement_regions.csv` in this folder, writes `PCB_MECHANICAL_RESERVE.step/.dxf` here and `STRUTHIO_SLIM4_R3_Integration.png` one folder up. Run it only on a copy.
