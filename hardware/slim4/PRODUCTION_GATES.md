# Production gates — R31

R31 puts PCB R26 in the package: the R23 main board with four plug-and-play ports, its power layout redone after the second hardware review (R24), its processor supply planes corrected after the R24 deep audit (R25), and its MIPI-DSI routed as matched 100 Ω coupled pairs after the R30/R25 pre-order audit (R26). **The board is ready to order** (`LAYERS/01_PCB/RELEASE_GATES.md`), except for sourcing U1. **The firmware builds** (`firmware/slim4`, R10). **The case is set aside by the owner:** the convergence check (`CHECKS/R31_CONVERGENCE_REPORT.md`) reports 3 FAIL, all case items. It is not a production release.

## Order now

1. **PCB R26 + assembly at JLCPCB** (`1_PCB_FABRICATION`), with impedance control on stackup JLC06121H-3313 (100 Ω differential for the three DSI pairs; the order README lists widths and gaps) and ENIG. Before ordering, pre-order or consign U1 (ESP32-P4NRW32X, v3). In the placement preview, check the rotations (J1 is a top-contact socket on the front).
2. **Panel**: Crystalfontz CFAF7201280A0-050TN (5.0 in, 720 × 1280, ILI9881C). It plugs straight into J1; no cable to order.
3. **Battery**: a protected 1-cell Li-ion/LiPo of 1000 mAh or more, up to 34 × 50 × 7 mm (503450 about 1000 mAh, 703450 about 1500 mAh), on a JST PH 2.0 2-pin plug, red = pin 1 = BAT+ (Adafruit / SparkFun packs). It charges at up to 0.55 A with no cell-temperature sensing, so the pack's own protection board matters. Check the polarity: a reversed pack is blocked when the board runs from it, but with USB connected it is not disconnected (the design analysis predicts the charger's 4–11 mA test current, not tested; the screen shows BATTERY REVERSED). Verify the pack's polarity before plugging it in.
4. **Speakers**: 2 × 4–8 Ω, up to 3 W, on Molex PicoBlade 1.25 mm 2-pin plugs (Adafruit 3923 / 4227 class); J4 left, J5 right.

## Then

5. **Bring-up** on the assembled boards with the four parts plugged in (including the regulators' switching waveforms, ripple and temperatures), as listed in `LAYERS/01_PCB/RELEASE_GATES.md` item 4 and `firmware/slim4/docs/FIRST_BOOT.md`. Until there is a case, mount the panel over the board on 3–4 mm foam spacers.

## Case pass (CASE R13; plastic, set aside by the owner)

Each item is a FAIL or GATE row of the R31 report:
- **C6**: redraw the LCD pocket, opening, lens and film for the 66.10 × 120.40 × 1.85 mm Crystalfontz module (active area 62.10 × 110.40), placed as R23-R26 put it: bottom edge at Y 109.8, centre at X 1.2, 13.6 mm past the board's top edge.
- **H4**: the panel lies 2.3–3.3 mm over the board front (J1 2.0 mm tall; the tail's fold about 3.3 mm). Replace the R12 extension-FPC reserve with the folded tail.
- **F1, G1**: the rear shell meets J3's JST PH body (R23 moved J3 to the window's left edge; R24-R26 keep it there) and J5's PicoBlade body, and sits 0.08 mm from J4's. Move or relieve the rear supports and walls there.
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
