# Production gates — R25

This is a cross-platform engineering/debug package. It is not a fabrication release.

R25 closes the **CAD convergence** gates: every interface between PCB R21, CASE R11 and ACRYLIC R1 is defined and checked (`CHECKS/R25_CONVERGENCE_REPORT.md`, 0 FAIL). What remains needs parts in hand, supplier drawings, or tests (the 13 GATE rows).

## Closed in CAD by R25

- Board fits the enclosure with 2.0 mm walls and ≥0.3 mm clearance; LCD fits with ≥0.2 mm (checks B2, B3).
- Screen opening and lens centred on the LCD active area; film continuous over the lens (C1–C3, E3).
- Every control reaches its switch when pressed and none at rest (D1–D10). Caps are retained by the Ø17.8 flange under the Ø17.0 plate hole, the rocker by trunnions in closed bosses (D14). Stop legs and support posts land clear of pads (I1, I5).
- Front plate webs ≥ 2.0 mm (B6). Plate nominal 2.0 mm, locally 0.70 mm over the LCD pocket ledge (B8, gate below); floor and walls 2.0 mm (B5).
- Film follows the case outline and clears the molded relief; vent cuts register on the grille (E1–E6).
- No interference between any two parts at rest, flaps pressed, or DART pressed either way. Moving parts clear by ≥0.2 mm except designed contacts: the cap-flange up-stop and power-plunger collar (touching), stop legs on the board at the stop, the DART trunnion (0.05 mm radial in its bosses), and the actuator nubs 0.05 mm (flaps) / 0.024 mm (DART) above the switch bodies at the stop (F1, G1).
- Rear shell, battery bay, speaker chambers, USB-C relief, FPC and harness routes, board clamps and service access exist and fit (H1–H3, I1–I3, J1–J3, K1–K2, L2–L3).

## Open — PCB (unchanged from R24)

- R21 native board is included and preserved unchanged. Complete schematic-to-board reconciliation and electrical intent review.
- Re-run native KiCad DRC/ERC with the final tool/version and confirm all nets, constraints, clearances, creepage, impedance, and board stackup.
- Select exact orderable/assembly parts, approved footprints, alternate parts, BOM/CPL, and assembly-side constraints. Verify JLCPCB capabilities and quoting limits against current files before ordering.
- Complete power-tree, MIPI, USB, audio, battery/charging, connector, protection, programming, and test-point review.
- Confirm via tenting in the fabrication notes: two vias sit under contact points — the SW2 flap cap's stop leg at (35.69, 107.06) on 3V3_SYS and the rear support post at (21.5, 76.0) on RESET_MR (I4).
- **Decision needed for sub-12 mm:** R25 is 13.55 mm (15.05 mm over the caps). The rear floor sits 0.2 mm below L2 (Sunlord ASWPA4035, 3.50 mm). Sub-12 mm needs every back-side part ≤ 1.95 mm — L2 3.50, J2 3.31, J3/J4/J5 3.00 and J1/L1/L3 2.00 are taller today — which is a PCB change, and a cell no thicker than 6.5 mm (the 7.0 mm cell alone holds the body at ≥ 12.55 mm). Replacing only L2 and J2 gives 13.05 mm (L1).

## Open — case, controls and screen

- **D2LS tolerance (D5):** with FP/OP ±0.2 mm a fixed stop cannot both reach OP on a low-FP switch and limit overtravel on a high-FP one (range −0.05…+0.35 mm past OP). Measure FP on a coupon of the ordered lot and trim the four stop legs per cap (or use 0.05 mm shims) before tooling.
- Confirm the D2LS actuator position on a sample (D11) and print-test the DART trunnion bosses (D12).
- **HOTHMI module (C4, H4):** confirm the 1.79 mm top border, active area, outline and FPC exit/length against the supplier drawing. The panel tail must reach J1 by the R25 route (under the module, between the DART switches, around the board tab, back to J1): about 70 mm with one 45° fold — order or design an FH12-20 extension FPC.
- LCD retention and ledge: the LCD bonds to a 0.70 mm ledge (B8). Specify the adhesive frame and check ledge stiffness on the print; keep the 1.7 mm gap behind the module empty (L6).
- Enclosure joint: a plain 1.0 mm lap; no detent is modelled. Print and drop-test it; the board has no mounting or screw holes, so add a detent or snap feature, perimeter clips or adhesive if it opens (L5).
- USB-C: the overmold relief leaves 0.745 mm under it; confirm by insertion/drop test (K3).
- Print tolerances, surface finish and the R10/R11 grip silhouette still need a hand-test print.

## Open — power and audio

- Cell (L4): order a protected 703450-class pouch (≤34 × 52 × 7.0 mm with PCM) with NTC and a JST SH 3-pin lead to J3 (BAT+, NTC, GND). Confirm swelling allowance with the supplier (1.7 mm reserved).
- Speakers (J4, J5): Same Sky CMS-18138A-SP are spring-contact parts; order a factory-wired variant or harness to JST SH 2-pin (J4/J5). Back volume is 1.56 cc per side. Measure impedance, response and distortion on a printed chamber pair; confirm gasket compression and seal the wire feedthroughs.

## Open — acrylic face layer

- 0.20 mm is a planning assumption, not a selected stock thickness. Choose the actual film/adhesive stack and vendor process (E7).
- Verify perimeter, control/vent cutouts, optical clarity, haze/reflection, screen readability, corner radii, application registration, and tolerance.
- Create final printed artwork, ink/white-mask separations, relief/texture and adhesive instructions only after the visible design is approved.
- Obtain a supplier preflight for SVG/DXF layer naming, polarity, kerf/offset, and material compensation.

Release only after these gates are closed and a physical fit/acoustic/optical prototype passes review.
