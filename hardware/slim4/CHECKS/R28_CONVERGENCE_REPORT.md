# STRUTHIO SLIM4 R28 convergence report (PCB R23 · CASE R12 · ACRYLIC R2)

Result: **NOT CONVERGED** · FAIL 3 · GATE 9 · INFO 3 · PASS 78

| ID | Interface | Check | Status | Value | Limit |
|---|---|---|---|---|---|
| A1 | PCB | LAYERS/01_PCB/SLIM4_R23.kicad_pcb unchanged from R28 delivery | PASS | "4375dc0aafefc80a" | "4375dc0aafefc80a" |
| A1 | PCB | LAYERS/01_PCB/SLIM4_R23_PCB_LAYER.json unchanged from R28 delivery | PASS | "6d40148de66320a9" | "6d40148de66320a9" |
| A2 | PCB↔CASE | Board thickness used by the case = board file thickness | PASS | 1.2 | 1.2 |
| B1 | CASE | Exterior envelope (approved 104.0 × 135.3) | PASS | [104.0, 135.3] | [104.0, 135.3] |
| B2 | PCB↔CASE | R23 board inside the 2.0 mm wall with ≥0.3 mm clearance | PASS | 0.334 | 0.3 |
| B3 | CASE | LCD module inside the 2.0 mm wall with ≥0.2 mm clearance | PASS | 0.21 | 0.2 |
| B4 | CASE | R12 silhouette change versus R10 (max outward move) | INFO | 2.351 |  |
| B5 | CASE | Nominal plate, floor and side wall thickness (design parameters) | PASS | [2.0, 2.0, 2.0] | 2.0 |
| B8 | CASE↔LCD | Plate left over the LCD pocket ledge (localised, below the 2.0 mm rule) | GATE | 0.7 | 2.0 |
| B6 | CASE | Minimum structural web in the front plate | PASS | 2.0 | 2.0 |
| B7 | CASE | Grille slot bars (between slots) | PASS | 1.1 | 1.0 |
| C1 | CASE↔LCD | Screen opening centred on the LCD active area | PASS | 55.648 | 55.648 |
| C2 | CASE↔LCD | Opening margin around the active area (each side) | PASS | [0.348, 0.348, 0.352, 0.352] | [0.2, 0.6] |
| C3 | CASE | Lens covers the opening and fits the rebate | PASS | 0.1 | 0.1 |
| C4 | CASE↔LCD | LCD active-area position relies on the 1.79 mm top border (R3 assumption) | GATE | 1.79 |  |
| C5 | CASE↔LCD | LCD pocket leaves room for the panel FPC bend at the bottom edge | PASS | 0.6 | 0.5 |
| C6 | CASE↔LCD | Chosen panel (Crystalfontz CFAF7201280A0-050TN, 66.10 × 120.40 × 1.85) fits the LCD pocket and stack | FAIL | [66.1, 120.4, 1.85] | [60.5, 111.5, 1.75] |
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
| D12 | CASE | DART trunnions snap into closed bosses (0.10 mm radial running clearance) | GATE | 1.0 |  |
| D14 | CASE | Controls retained: cap flange overlaps the plate hole; DART trunnions run in closed bosses | PASS | [0.4, 1.39] | [0.3, 0.5] |
| D15 | CASE | Material under each DART trunnion bore (boss floor) | PASS | 0.15 | 0.15 |
| D9 | PCB↔CASE | Power plunger on SW5 (PWR_WAKE) and pinholes on SW6 RESET / SW7 BOOT | PASS | ["SW5", "SW6", "SW7"] |  |
| E1 | ACRYLIC↔CASE | Film edge sits 0.20 mm inside the case outline all round | PASS | [0.2, 0.206] | 0.2 |
| E2 | ACRYLIC↔CASE | Film clears the molded relief (relief rises through the film) | PASS | 0.2 | 0.2 |
| E3 | ACRYLIC↔CASE | Film continuous over the screen opening and lens (no screen cutout) | PASS |  |  |
| E4 | ACRYLIC↔CASE | Film vent windows uncover every grille slot with ≥0.1 mm margin | PASS | 2 | 6 |
| E5 | ACRYLIC | Film edge web beside every cutout | PASS | 1.748 | 1.5 |
| E8 | ACRYLIC | Narrowest cutout is wide enough for a die or plotter cut | PASS | 4.8 | 1.5 |
| E6 | ACRYLIC | Cut specification JSON matches the geometry (every cutout field and the thickness) | PASS | 10 | 10 |
| E7 | ACRYLIC | Film stack selected and equal to the CAD film thickness | PASS | 0.2 | 0.2 |
| H1 | CASE↔PCB | FPC route reserve (the R12 extension-FPC path) is one continuous body | PASS | 1 | 1 |
| H2 | CASE↔PCB | BATTERY LEAD RESERVE · TO J3 continuous | PASS | 1 | 1 |
| H2 | CASE↔PCB | SPEAKER LEAD RESERVE · TO J4 continuous | PASS | 1 | 1 |
| H2 | CASE↔PCB | SPEAKER LEAD RESERVE · TO J5 continuous | PASS | 1 | 1 |
| F1 | ALL | No positive-volume interference (rest, flap pressed, DART left/right pressed) | FAIL | 2 | 0 |
| G1 | ALL | Clearances: moving parts ≥0.2, purchased/reserve envelopes ≥0.1, designed contacts honoured | FAIL | 1 | 0 |
| D10 | PCB↔CASE | Each control engages its own switch when pressed, none at rest | PASS | ["press:SW1", "press:SW2", "press:SW5", "press_left:SW3", "press_right:SW4"] | ["press:SW1", "press:SW2", "press:SW5", "press_left:SW3", "press_right:SW4"] |
| H3 | CASE↔PCB | FPC wrap around the board tab clears the bottom wall | PASS | 0.351 | 0.2 |
| H4 | CASE↔LCD | Panel tail (40 mm) folds once behind the panel into J1 on the front, under the panel | GATE |  |  |
| N1 | PCB↔LCD | J1: all 40 pins match the panel pin table (position after the single fold, and net) | PASS | 40 | 40 |
| I1 | PCB↔CASE | Support/clamp posts land on bare board (no pads within 0.3 mm, ≥0.3 mm from edges/window) | PASS | 0 | 0 |
| I2 | PCB↔CASE | Every front switch backed by a rear support within 10 mm | PASS | {"SW1": 6.0, "SW2": 6.0, "SW3": 6.778, "SW4": 8.25} | 10.0 |
| I3 | CASE | Board clamped front-and-back at matched points | PASS | 6 | 6 |
| I5 | PCB↔CASE | Stop legs land clear of pads (no pad within 0.3 mm) | PASS | 0 | 0 |
| I4 | PCB↔CASE | Vias under support posts and stop legs are tented (solder-masked) | PASS | 2 | 0 |
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
| L2 | CASE | Battery envelope fits the board window with swelling allowance | PASS | 1.6 | 0.7 |
| L3 | PCB↔CASE | Battery XY clearance to the board window | PASS | 1.5 | 1.0 |
| L4 | CASE | Cell in hand: any protected 1-cell pack up to 34 × 50 × 7 mm on a JST PH 2.0 plug (R23 J3) | GATE |  |  |
| L5 | CASE | Enclosure joint: lap running clearance and tape seat (retention by a 0.10 mm tape ring) | PASS | [0.1, 0.1] | [0.1, 0.1] |
| L6 | CASE↔LCD | Display stack: one 0.10 mm tape frame bonds the module to the ledge and carries the lens | PASS | [6.85, 0.1, 6.95, 0.498] |  |

## Notes

- **B4 R12 silhouette change versus R10 (max outward move)** — area +102.9 / -0.3 mm²; shoulders and finger scallop pushed out to clear the board; saddle lift 4.5 → 4.0 mm for the FPC wrap
- **B8 Plate left over the LCD pocket ledge (localised, below the 2.0 mm rule)** — Measured on the front-shell solid at (0, 111.08). The ledge outside the lens rebate is 0.70 mm: a band 60.5 mm wide at Y 107.95–114.21, plus a 1.24 mm top strip and 0.55 mm side strips. The LCD front face bonds to it (L6). Set by the stack (LCD 1.75 + lens 0.70 in a 2.0 mm plate); confirm stiffness on the print.
- **C4 LCD active-area position relies on the 1.79 mm top border (R3 assumption)** — The case still uses the R3/HOTHMI envelope. In the case pass, set the LCD parameters from the Crystalfontz drawing (C6); the opening, lens and rebate follow ACTIVE_CY automatically (the film has no screen cutout).
- **C6 Chosen panel (Crystalfontz CFAF7201280A0-050TN, 66.10 × 120.40 × 1.85) fits the LCD pocket and stack** — CASE R12 was drawn around the R3/HOTHMI envelope 60.3 × 111.4 × 1.75. The Crystalfontz module is +5.60 mm against the 60.5 mm pocket width, +9.00 mm in length and +0.10 mm in thickness; its active area (62.1 × 110.4) against the case opening design (58.104 × 103.296). The owner set the case aside for R23: the case pass redraws the pocket, opening, lens and film for the 5 in panel.
- **D5 Overtravel at the stop across FP/OP ±0.2 (D2LS tolerance)** — A fixed stop cannot cover the full ±0.2 band (low-FP switch would not reach OP). Measure FP on a coupon and trim the stop legs, or use the shim set; see PRODUCTION_GATES.md.
- **D11 D2LS actuator assumed at the body centre** — The Omron outline does not dimension the plunger position in text form; the Ø1.4 nubs sit on the switch centres. Confirm on a sample before cutting tools.
- **D12 DART trunnions snap into closed bosses (0.10 mm radial running clearance)** — Print-test the boss flex and wear; add a lead-in slot if the bosses crack on assembly.
- **F1 No positive-volume interference (rest, flap pressed, DART left/right pressed)** — [{"pose": "rest", "a": "REAR SHELL R12 \u00b7 FLOOR, WALLS, CHAMBERS, SUPPORTS", "b": "J3 S2B-PH-SM4-TB(LF)(SN)", "volume_mm3": 187.68}, {"pose": "rest", "a": "REAR SHELL R12 \u00b7 FLOOR, WALLS, CHAMBERS, SUPPORTS", "b": "J5 53261-0271", "volume_mm3": 6.065}]
- **G1 Clearances: moving parts ≥0.2, purchased/reserve envelopes ≥0.1, designed contacts honoured** — [{"pose": "rest", "a": "REAR SHELL R12 \u00b7 FLOOR, WALLS, CHAMBERS, SUPPORTS", "b": "J4 53261-0271", "distance": 0.08, "required": 0.1}]
- **H4 Panel tail (40 mm) folds once behind the panel into J1 on the front, under the panel** — R23 has no adapter flex: the Crystalfontz tail folds once behind the module (datasheet 7.6: bend radius 1.5 mm, at least 2 mm past the glass), contacts away from the board, and enters J1 (FH12A-40S, top contact, mouth toward +Y) at Y 76. The tail end lands about 34.3 mm above the panel bottom edge, so the panel bottom edge sits at Y 109.8 with its centre at X 1.2. The panel needs 2.3-3.3 mm between its back and the board front (J1 is 2.0 mm tall; the fold is 3.0 mm across). The case route reserve still follows the R12 extension-FPC path; the case pass redraws it and the LCD pocket for the 5 in panel.
- **J4 Sealed back volume per speaker (cc)** — R3 reserved ~1.94 cc per side (CAD geometric capacity) and, following the R2 research direction, recommended comparing 1.0 / 1.5 / ~2.0 cc; response must be measured
- **J5 Acoustic response, gasket compression and wire feedthrough seal** — Measure impedance/response/distortion on a printed chamber pair.
- **K3 Material left under the USB relief (localised, below the 2.0 mm rule)** — Accepted locally because the port sits 3.31 mm deep on the back side; confirm by drop/insertion test.
- **L1 Body thickness (face film to rear floor)** — with caps 15.05 mm. The rear floor sits 0.2 mm below the tallest back-side part, L2 (Sunlord ASWPA4035, 3.50 mm). Sub-12 mm needs every back-side part ≤ 1.95 mm (over today: J3 6.00, L2 3.50, J5 3.40, J4 3.40, J2 3.31, L3 2.00, L1 2.00), which is a PCB change, and a cell no thicker than 6.41 mm: the 7.0 mm cell alone holds the body at ≥ 12.65 mm. Replacing only L2 and J2 gives 16.05 mm.
- **L4 Cell in hand: any protected 1-cell pack up to 34 × 50 × 7 mm on a JST PH 2.0 plug (R23 J3)** — J3 pin 1 = BAT+, pin 2 = GND (Adafruit/SparkFun convention); Q2 blocks a reversed pack. Check the cell size and swelling allowance in hand.

Solid validity: 21/21 solids valid.
