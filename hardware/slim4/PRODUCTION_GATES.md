# Production gates — R26

R26 is an engineering prototype (EVT) package. The three layers converge in CAD (`CHECKS/R26_CONVERGENCE_REPORT.md`: 0 FAIL), every open owner decision has been made (`DECISIONS_R26.md`), and the builder files are complete (`CHECKS/build_builder_packs.py`). It is not a production release: the items below need hardware, tests or supplier data.

## Closed in CAD

- Board fits the enclosure with 2.0 mm walls and ≥0.3 mm clearance; LCD fits with ≥0.2 mm (B2, B3).
- Screen opening and lens centred on the LCD active area; film continuous over the lens (C1–C3, E3).
- Every control reaches its switch when pressed and none at rest (D1–D10). Caps are retained by the Ø17.8 flange under the Ø17.0 plate hole, the rocker by trunnions in closed bosses with 0.15 mm under each bore (D14, D15). Stop legs and support posts land clear of pads (I1, I5).
- Via tenting (I4): the two vias under case contact points are covered by solder mask in the plotted Gerbers.
- Enclosure joint (L5): 0.10 mm radial lap clearance, 0.10 mm tape seat; the skirt lands on the rear wall.
- Display stack (L6): module + 0.10 mm tape frame = ledge underside = lens underside; 1.6 mm free behind the module for cell swelling.
- Film (E1–E8): edge 0.20 mm inside the case outline, clears the molded relief, vent windows over every grille slot, narrowest cut 4.8 mm, stack equal to the CAD thickness, cut spec matches.
- No interference between any two parts at rest, flaps pressed, or DART pressed either way; moving parts clear by ≥0.2 mm except designed contacts (F1, G1).
- Rear shell, battery bay, speaker chambers, USB-C relief, FPC and harness routes, board clamps and service access (H1–H3, I1–I3, J1–J3, K1–K2, L2–L3).

## Open — needs parts, tests or supplier data

PCB R21 (locked; `LAYERS/01_PCB/RELEASE_GATES.md`):
1. **Schematic and ERC.** No schematic is in the package; the R21 netlist cannot be checked against intent here.
2. **Electrical design review**: ESP32-P4 power, boot, USB and flash against Espressif references; power tree, current and thermal.
3. **Signal integrity**: MIPI-DSI and USB 2.0 were not routed to a defined stackup; measure on the EVT boards (no impedance control ordered).
4. **Land-pattern audit**: 152 footprints are package proxies; the assembler's DFM review checks them against the bound BOM.
5. **Board house DFM** on the uploaded Gerbers (the KiCad 7.0.11 DRC uses the design's own 0.1 mm rules).
6. **Firmware** for the R21 GPIO remaps (USB_CURR_OUT1 GPIO43, PGOOD_STATUS GPIO44, BQ_EN2 GPIO46). No firmware is in this repository.

Case, controls and screen:
7. **HOTHMI panel drawing (C4, H4)**: confirm the 1.79 mm top border, active area, outline and the FPC tail exit and length; then order or design the 20-pin 0.5 mm extension FPC (about 70 mm, one 45° fold) along the reserved route to J1.
8. **D2LS lot (D5, D11)**: measure free position on a coupon of the ordered switches and confirm the actuator position; trim the four stop legs per cap (or shim 0.05 mm) to land overtravel.
9. **Print tests (B8, D12, K3)**: ledge stiffness under the LCD, trunnion snap-in and wear, USB-C insertion and drop over the thin relief floor; print tolerance, finish and grip by hand.
10. **Drop test of the taped lap joint.**

Power and audio:
11. **Cell in hand (L4)**: order the cell specified in `DECISIONS_R26.md` #13; confirm size with the PCM and swelling allowance with the supplier.
12. **Speakers (J5)**: Same Sky CMS-18138A-SP has spring contacts: choose a factory-wired variant or a harness to JST SH 2-pin (J4/J5) once the contact layout is in hand; measure impedance, response and distortion on a printed chamber pair; confirm gasket compression and seal the feedthroughs.

Film, tapes and lens (supplier confirmation of the specified items):
13. **Supplier quotes**: film stock and bubble-free lamination over the screen, kiss-cut tolerance on the film and both tapes, cover-glass quote.

Deferred by decision (not needed for EVT):
- Printed artwork on the face film (`DECISIONS_R26.md` #9).
- Sub-12 mm body (`DECISIONS_R26.md` #2; needs a PCB revision).

Release only after these items are closed and the EVT prototype passes fit, acoustic, optical and drop review.
