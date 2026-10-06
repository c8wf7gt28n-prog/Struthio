# STRUTHIO SLIM4 R25 convergence report (PCB R21 · CASE R11 · ACRYLIC R1)

Result: **CONVERGED** · GATE 12 · INFO 3 · PASS 69

| ID | Interface | Check | Status | Value | Limit |
|---|---|---|---|---|---|
| A1 | PCB | LAYERS/01_PCB/SLIM4_R21.kicad_pcb unchanged from R24 delivery | PASS | "daac1da0536f04f4" | "daac1da0536f04f4" |
| A1 | PCB | LAYERS/01_PCB/SLIM4_R21_PCB_LAYER.json unchanged from R24 delivery | PASS | "92a31435a101cde7" | "92a31435a101cde7" |
| A2 | PCB↔CASE | Board thickness used by the case = board file thickness | PASS | 1.2 | 1.2 |
| B1 | CASE | Exterior envelope (approved 104.0 × 135.3) | PASS | [104.0, 135.3] | [104.0, 135.3] |
| B2 | PCB↔CASE | R21 board inside the 2.0 mm wall with ≥0.3 mm clearance | PASS | 0.334 | 0.3 |
| B3 | CASE | LCD module inside the 2.0 mm wall with ≥0.2 mm clearance | PASS | 0.21 | 0.2 |
| B4 | CASE | R11 silhouette change versus R10 (max outward move) | INFO | 2.351 |  |
| B5 | CASE | Plate, floor and side wall thickness | PASS | [2.0, 2.0, 2.0] | 2.0 |
| B6 | CASE | Minimum structural web in the front plate | PASS | 2.0 | 2.0 |
| B7 | CASE | Grille slot bars (between slots) | PASS | 1.1 | 1.0 |
| C1 | CASE↔LCD | Screen opening centred on the LCD active area | PASS | 55.648 | 55.648 |
| C2 | CASE↔LCD | Opening margin around the active area (each side) | PASS | [0.348, 0.348, 0.352, 0.352] | [0.2, 0.6] |
| C3 | CASE | Lens covers the opening and fits the rebate | PASS | 0.1 | 0.1 |
| C4 | CASE↔LCD | LCD active-area position relies on the 1.79 mm top border (R3 assumption) | GATE | 1.79 |  |
| C5 | CASE↔LCD | LCD pocket leaves room for the panel FPC bend at the bottom edge | PASS | 0.6 | 0.5 |
| D1 | PCB↔CASE | Flap cap axis on SW1 | PASS | 0.0 | 0.0 |
| D1 | PCB↔CASE | Flap cap axis on SW2 | PASS | 0.0 | 0.0 |
| D2 | PCB↔CASE | DART nub on SW3 | PASS | 0.0 | 0.0 |
| D2 | PCB↔CASE | DART nub on SW4 | PASS | 0.0 | 0.0 |
| D3 | PCB↔CASE | Nub-to-plunger gap at rest (nominal) | PASS | 0.15 | [0.05, 0.25] |
| D4 | PCB↔CASE | Overtravel past OP at the hard stop (nominal; datasheet OT ≥ 0.1) | PASS | 0.15 | 0.1 |
| D5 | PCB↔CASE | Overtravel at the stop across FP/OP ±0.2 (D2LS tolerance) | GATE | [-0.05, 0.35] | [0.0, null] |
| D6 | PCB↔CASE | DART nub travel at the rocker stop | PASS | 0.6 | 0.6 |
| D7 | CASE | DART stop leg reaches the board at the stop angle | PASS | 1.202 | 1.2 |
| D8 | CASE | Opposite DART switch is released while one side is pressed | PASS | 5.45 | 4.7 |
| D11 | PCB↔CASE | D2LS actuator assumed at the body centre | GATE |  |  |
| D12 | CASE | DART trunnions snap into closed bosses (0.05 mm radial running clearance) | GATE | 1.0 |  |
| D9 | PCB↔CASE | Power plunger on SW5 (PWR_WAKE) and pinholes on SW6 RESET / SW7 BOOT | PASS | ["SW5", "SW6", "SW7"] |  |
| E1 | ACRYLIC↔CASE | Film outline equals the case outline | PASS | 0.0 | 0.0 |
| E2 | ACRYLIC↔CASE | Film clears the molded relief (relief rises through the film) | PASS | 0.2 | 0.2 |
| E3 | ACRYLIC↔CASE | Film continuous over the screen opening and lens (no screen cutout) | PASS |  |  |
| E4 | ACRYLIC↔CASE | Film vent cuts register over every grille slot | PASS | 6 | 6 |
| E5 | ACRYLIC | Film edge web beside the flap cutouts | PASS | 1.948 | 1.5 |
| E6 | ACRYLIC | Cut specification JSON matches the geometry | PASS |  |  |
| E7 | ACRYLIC | Film thickness 0.20 mm is a planning assumption | GATE | 0.2 |  |
| H1 | CASE↔PCB | FPC route reserve is one continuous body from the panel to J1 | PASS | 1 | 1 |
| H2 | CASE↔PCB | BATTERY LEAD RESERVE · TO J3 continuous | PASS | 1 | 1 |
| H2 | CASE↔PCB | SPEAKER LEAD RESERVE · TO J4 continuous | PASS | 1 | 1 |
| H2 | CASE↔PCB | SPEAKER LEAD RESERVE · TO J5 continuous | PASS | 1 | 1 |
| F1 | ALL | No positive-volume interference (rest, flap pressed, DART left/right pressed) | PASS | 0 | 0 |
| G1 | ALL | Clearances: moving parts ≥0.2, purchased/reserve envelopes ≥0.1, designed contacts honoured | PASS | 0 | 0 |
| D10 | PCB↔CASE | Each control engages its own switch when pressed, none at rest | PASS | ["press:SW1", "press:SW2", "press:SW5", "press_left:SW3", "press_right:SW4"] | ["press:SW1", "press:SW2", "press:SW5", "press_left:SW3", "press_right:SW4"] |
| H3 | CASE↔PCB | FPC wrap around the board tab clears the bottom wall | PASS | 0.351 | 0.2 |
| H4 | CASE↔LCD | Panel FPC needs an extension tail (~70 mm, 20 × 0.5 mm, one 45° fold) | GATE |  |  |
| I1 | PCB↔CASE | Support/clamp posts land on bare board (no pads within 0.3 mm, ≥0.3 mm from edges/window) | PASS | 0 | 0 |
| I2 | PCB↔CASE | Every front switch backed by a rear support within 10 mm | PASS | {"SW1": 6.0, "SW2": 6.0, "SW3": 6.778, "SW4": 8.25} | 10.0 |
| I3 | CASE | Board clamped front-and-back at matched points | PASS | 6 | 6 |
| I4 | PCB↔CASE | Vias under support posts (must be tented/solder-masked) | GATE | 1 | 0 |
| J1 | CASE | Speaker chamber at (-38.3, 125.6) clear of the board | PASS | 0.5 | 0.3 |
| J2 | CASE | Speaker inside its chamber with ≥0.2 mm | PASS | 0.2 | 0.2 |
| J3 | CASE | Grille slots inside the speaker gasket opening | PASS | 3 | 3 |
| J1 | CASE | Speaker chamber at (38.3, 125.6) clear of the board | PASS | 0.5 | 0.3 |
| J2 | CASE | Speaker inside its chamber with ≥0.2 mm | PASS | 0.2 | 0.2 |
| J3 | CASE | Grille slots inside the speaker gasket opening | PASS | 3 | 3 |
| J4 | CASE | Sealed back volume per speaker (cc) | INFO | [1.558, 1.558] |  |
| J5 | CASE | Acoustic response, gasket compression and wire feedthrough seal | GATE |  |  |
| K1 | PCB↔CASE | USB-C overmold relief ≥ USB-IF max overmold 12.35 × 6.5 + clearance | PASS | [12.6, 6.6] | [12.55, 6.6] |
| K2 | PCB↔CASE | Relief reaches the receptacle mating face | PASS | 2.575 |  |
| K3 | CASE | Material left under the USB relief (localised, below the 2.0 mm rule) | GATE | 0.745 | 0.7 |
| L1 | ALL | Body thickness (face film to rear floor) | INFO | 13.55 |  |
| L2 | CASE | Battery envelope fits the board window with swelling allowance | PASS | 1.7 | 0.7 |
| L3 | PCB↔CASE | Battery XY clearance to the board window | PASS | 2.0 | 1.0 |
| L4 | CASE | Cell choice (703450 class, ~1300 mAh) and protected pack with JST SH 3-pin lead | GATE |  |  |
| L5 | CASE | Enclosure joint: 1.0 mm lap with detent; no board holes exist for screws | GATE |  |  |
| L6 | CASE↔LCD | LCD retained by adhesive on the pocket ledge (no rear support under the module) | GATE |  |  |

## Notes

- **B4 R11 silhouette change versus R10 (max outward move)** — area +102.9 / -0.3 mm²; shoulders and finger scallop pushed out to clear the board; saddle lift 4.5 → 4.0 mm for the FPC wrap
- **C4 LCD active-area position relies on the 1.79 mm top border (R3 assumption)** — Confirm against the HOTHMI drawing; the opening, lens and film window follow ACTIVE_CY automatically.
- **D5 Overtravel at the stop across FP/OP ±0.2 (D2LS tolerance)** — A fixed stop cannot cover the full ±0.2 band (low-FP switch would not reach OP). Measure FP on a coupon and trim the stop legs, or use the shim set; see PRODUCTION_GATES.md.
- **D11 D2LS actuator assumed at the body centre** — The Omron outline does not dimension the plunger position in text form; the Ø1.4 nubs sit on the switch centres. Confirm on a sample before cutting tools.
- **D12 DART trunnions snap into closed bosses (0.05 mm radial running clearance)** — Print-test the boss flex and wear; add a lead-in slot if the bosses crack on assembly.
- **E7 Film thickness 0.20 mm is a planning assumption** — Select film/adhesive stock; Z stack above the plate follows this value.
- **H4 Panel FPC needs an extension tail (~70 mm, 20 × 0.5 mm, one 45° fold)** — J1 faces the board-tab edge on the back side; with the screen raised for the R10 face the panel tail must run under the module, between the DART switches, around the tab and back to J1. Confirm HOTHMI tail length/exit or order an FH12-20 extension FPC.
- **I4 Vias under support posts (must be tented/solder-masked)** — Confirm via tenting in the fabrication notes.
- **J4 Sealed back volume per speaker (cc)** — R3 study compared 1.0 / 1.5 / ~2.0 cc; response must be measured
- **J5 Acoustic response, gasket compression and wire feedthrough seal** — Measure impedance/response/distortion on a printed chamber pair.
- **K3 Material left under the USB relief (localised, below the 2.0 mm rule)** — Accepted locally because the port sits 3.31 mm deep on the back side; confirm by drop/insertion test.
- **L1 Body thickness (face film to rear floor)** — with caps 15.05 mm. The rear floor is set by L2 (3.50 mm, Sunlord ASWPA4035) and J2 (3.31 mm). Sub-12 mm needs both replaced with ≤1.9 mm parts: a PCB change.
- **L4 Cell choice (703450 class, ~1300 mAh) and protected pack with JST SH 3-pin lead** — Order a protected cell with NTC, 3-pin to J3 (BAT+, NTC, GND).
- **L5 Enclosure joint: 1.0 mm lap with detent; no board holes exist for screws** — Print and drop-test the lap/detent; add adhesive if it opens.
- **L6 LCD retained by adhesive on the pocket ledge (no rear support under the module)** — Specify the adhesive frame; the 1.7 mm gap behind the module is the battery swelling allowance and must stay empty.

Solid validity: 19/19 solids valid.
