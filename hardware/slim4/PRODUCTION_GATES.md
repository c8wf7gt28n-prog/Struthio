# Production gates — R27

R27 puts PCB R22 in the package. **The board is ready to order** (`LAYERS/01_PCB/RELEASE_GATES.md`), except for sourcing U1. **The display flex is generated** and waits for the panel's pin table. **The case has not been redone for the chosen panel and the R22 connectors:** the convergence check (`CHECKS/R27_CONVERGENCE_REPORT.md`) reports 3 FAIL, all of them case items, and the owner deferred the plastic until the board and parts are in hand. It is not a production release.

## Order now

1. **PCB R22 + assembly at JLCPCB** (`1_PCB_FABRICATION`). Before ordering, pre-order or consign U1 (ESP32-P4NRW32X, v3). In the placement preview, check the rotations.
2. **Panel**: Startek KD047HDFID001. Ask for the full datasheet (FPC pin definition, contact side, init code).
3. **Battery**: any protected 1-cell pack, up to 34 × 52 × 7 mm, on a JST SH 1.0 2-pin plug, pin 1 BAT+. Check the polarity: the board has no reverse protection.
4. **Speakers**: 2 × Same Sky CMS-18138A-SP (spring contacts), with JST SH 2-pin leads soldered on, pin 1 +.

## Then

5. **Display flex** (`LAYERS/04_DISPLAY_FLEX`). Fill `panel_pinmap.csv` from the Startek datasheet, rebuild, and order 5 at JLCPCB (flex PCB, FH26 assembled). The J1 end is checked against the board (N1 PASS).
6. **Bring-up** on the assembled boards, as listed in `LAYERS/01_PCB/RELEASE_GATES.md` item 4.

## Case pass (CASE R13; plastic, deferred by the owner)

Each item is a FAIL or GATE row of the R27 report:
- **C6**: widen the LCD pocket for the 61.0 mm Startek module (now 60.5). Set the module to 110.6 × 1.8 mm, and take the active-area offset from Startek's drawing (C4 replaces the HOTHMI 1.79 mm assumption).
- **F1, I1**: J5's real JST SH body and its solder tab now reach the rear support post at (40.75, 108). Move the post about 1 mm toward SW2, and re-check I2 (switch backing).
- **H4**: the flex's panel end (FH26 and fan-out, about 22.6 mm wide) sits behind the module, so place it and redraw the route reserve. Print the 1:1 template, fit it on a printed case, and set `--length`.
- The earlier physical gates are unchanged:
  - **D5, D11**: D2LS lot free position and actuator position. Trim the stop legs or shim them.
  - **B8, D12, K3**: print tests for the ledge, trunnions and USB-C floor.
  - **J5**: speaker acoustics and the feedthrough seal.
  - **L4**: the cell in hand.
  - A drop test of the taped lap joint.

## Film, tapes and lens

Order these after the case pass and a fit check on the printed case. You also need supplier quotes:
- film stock and bubble-free lamination;
- kiss-cut tolerance;
- the cover glass.

Deferred by decision:
- artwork on the face film (`DECISIONS_R26.md` #9);
- a sub-12 mm body (needs lower back-side parts and a thinner cell).
