# STRUTHIO SLIM4 R24 baseline audit (PCB R21 · CASE R10 · ACRYLIC R0)

Result: **NOT CONVERGED** · FAIL 17

| ID | Interface | Check | Status | Value | Limit |
|---|---|---|---|---|---|
| B2 | PCB↔CASE | R21 board inside a 2.0 mm wall with ≥0.3 mm | FAIL | -1.999 | 0.3 |
| B3 | CASE | LCD module inside the wall | FAIL | 0.0 | 2.2 |
| A2 | PCB↔CASE | Board thickness used by the case = board file | FAIL | 1.6 | 1.2 |
| D3 | PCB↔CASE | Flap caps reach the D2LS plungers | FAIL | 3.15 | [0.05, 0.25] |
| D6 | PCB↔CASE | DART pill reaches SW3/SW4; pivot and stops defined | FAIL | 3.15 |  |
| D13 | CASE | Caps retained in the shell | FAIL |  |  |
| E2 | ACRYLIC↔CASE | Molded relief vs film | FAIL |  |  |
| C1 | CASE↔LCD | Opening centred on active area (R3 1.79 mm top border) | FAIL | 55.7 | 53.438 |
| X1 | CASE | rear shell present | FAIL |  |  |
| X1 | CASE | battery package present | FAIL |  |  |
| X1 | CASE | speakers and chambers present | FAIL |  |  |
| X1 | CASE | USB-C aperture present | FAIL |  |  |
| X1 | CASE | FPC route present | FAIL |  |  |
| X1 | CASE | board retention present | FAIL |  |  |
| X1 | CASE | power/reset/boot access present | FAIL |  |  |
| S1 | VIEWER | Service worker precache list resolves | FAIL |  |  |
| S2 | VIEWER | Lens sublayer toggle | FAIL |  |  |

## Notes

- **B2 R21 board inside a 2.0 mm wall with ≥0.3 mm** — value = how far the board edge reaches into the 2.0 mm wall: it touches the R10 outer surface at the shoulders (Y≈78-80) and enters the wall zone at Y 70-89 and 103-117
- **B3 LCD module inside the wall** — LCD top edge at Y=0 is on the exterior surface
- **D3 Flap caps reach the D2LS plungers** — cap underside 7.85 vs plunger free position 4.70: 3.15 mm air, no stem
- **D6 DART pill reaches SW3/SW4; pivot and stops defined** — pill floats on the film; no pivot, return or stop
- **D13 Caps retained in the shell** — 16 mm caps in 17 mm holes with nothing under the plate
- **E2 Molded relief vs film** — bezels/pill surround placed on top of the film (Z 7.85) although labelled molded; film not cut around them
- **C1 Opening centred on active area (R3 1.79 mm top border)** — the module was centred on the opening; with the module top at Y=0 the active area centre is Y 53.44, so the opening sits 2.26 mm low
- **X1 rear shell present** — not in R10 CAD
- **X1 battery package present** — not in R10 CAD
- **X1 speakers and chambers present** — not in R10 CAD
- **X1 USB-C aperture present** — not in R10 CAD
- **X1 FPC route present** — not in R10 CAD
- **X1 board retention present** — not in R10 CAD
- **X1 power/reset/boot access present** — not in R10 CAD
- **S1 Service worker precache list resolves** — sw.js lists R21_REFERENCE/.../SLIM4_R3_integration.step and build.py, which are not in the package; addAll() rejects so offline install fails
- **S2 Lens sublayer toggle** — lens mesh exported in group "display", so the Protective lens checkbox has no effect
