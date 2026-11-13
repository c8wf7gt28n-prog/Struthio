# STRUTHIO SLIM4 R3 — motherboard and mechanism integration
R.A. Peddycoart • 2026-10-03

## What is now concrete
This revision combines the approved 104×135.296 mm XY outline, 16 mm primary caps, four switch bodies, two shared-depth audio cores, LCD envelope, battery window, and a single connected motherboard reserve. The STEP is a real CAD assembly. It is not a completed enclosure or electronic PCB layout. No Gerbers or assembly ordering files are issued.

The full XY silhouette matches R2. Primary button and switch centers move outward 0.75 mm to X=±40.75, Y=102. This explicitly replaces the previous ±40 mm centers. The visual change provides nominal 0.8 mm guide-to-LCD clearance. Guide OD19.6, ID16.4 gives a1.6 mm radial wall and0.2 mm radial cap clearance. Print tolerances, surface finish, return force and off-axis thumb loading still require a physical mechanism coupon.

The rectangular R2 acoustic cores have been re-created inside the approved curved outline. Both voids and their walls were rebuilt, rather than simply trimming through an existing chamber. Rear air space is approximately1.936 cc per side before wiring, seals, ribs and final rear curvature. This is geometric capacity, not an acoustic optimum or measured response. The17 mm deep local core envelopes still need the final rear grip surface and shell closure integrated around them. The ≤12 mm screen-stem target remains11.5 mm.

## Files
- `SLIM4_R3_integration.step`: full placement study with named parts and circuit reserve volumes.
- `PCB_MECHANICAL_RESERVE.step` and `.dxf`: one-piece board region with a rounded38×56 mm battery opening. NOT FOR FABRICATION; no copper, footprints, nets or drill specification.
- `placement_regions.csv`: component-group space reservations in mm, not a pick-and-place file.
- `build.py`: editable generator; requires CadQuery, NumPy, Shapely and matplotlib. X is left/right, Y down from top, Z rearward from front face.
- `checks.json`: actual geometry-check results.
- `ELECTRICAL_HANDOFF.md`: architecture, placement priorities and release gates.

## Verification and its limits
All generated solids pass validity checks. The motherboard is one solid. Pairwise solid-intersection tests report no positive-volume interference between included objects. Contacts between the board and support roof are intentional. These checks omit switch actuator heads/leads, PCB solder joints, wires, gaskets, moving cap sweeps, rocker pivot/return parts, full component footprints, lens and the complete exterior shell. They therefore do not establish finished fit, strength or acoustic sealing.

All circuit reserves lie over board area except USB_C. The USB body reserve intentionally projects1 mm beyond the proposed board top edge; the actual connector's pad, shell-tab, insertion and enclosure aperture geometry still needs verification. This is a visible top-edge connector change required by the existing USB architecture, not a decorative side opening.

R3 retains 1 mm PCB thickness as a target. The acoustic roof contacts the PCB rear surface underneath each primary switch; reserve these areas free of rear components, exposed pads and connector bodies. Add local electrical insulation as needed. PCB fastening and support contact positions must be approved with the actual footprint and tolerances. No screw holes have been invented in this board outline.

## Mechanical work still open
1. Model actual D2LS actuator and terminals, then tolerance-stack the switch, board seat, striker and cap. The manufacturer lists FP3.5±0.2 and OP3.2±0.2 mm; nominal travel alone cannot determine a safe hard stop. Its0.1 mm OT is a minimum, not a maximum permissible stroke. Use adjustable coupon spacers before fixing hard stops. Design a compliant return and prevent cap tilt; do not rely on uncontrolled switch preload.
2. Detail the DART pivot and two independent actuation points at X=±16, Y=119.296. The rocker remains48×8; the switch bodies are present but pivot/return/hard stops are not.
3. Define lens, panel seat and flex fold from the actual sample. The LCD module orientation uses the earlier 1.79 mm inactive top assumption. Do not release until confirmed.
4. Finish speaker gasket lands, gasket compression stops, sealed wire feedthroughs and removable rear closure. A clearance gap around the nominal speaker is not a seal. Both channels remain separate.
5. Integrate the rounded rear grip surface, ribs and service fasteners; recompute net chamber volumes after that work. Validate button-force deflection and thin walls before calling the assembly printable.
6. Review battery swelling allowance, cable exit, connector access, protected-pack specification, thermal clearance and removal tab. The34×52×3.5 mm model is a candidate envelope, not a purchased pack.

## Acoustic continuity
Keep the R2 research direction: sealed rear volume, short front path first; compare1.0/1.5/~2.0 cc and short/folded outlets at equal drive. The Same Sky speaker's nominal500 Hz free-air resonance is not its installed response. Do not claim bass extension without impedance/response/distortion measurements. The speaker must arrive factory wired with a matched plug, or be replaced by a suitable factory-connected assembly. No user soldering or crimping.

## Source
Omron D2LS manufacturer drawing: https://omronfs.omron.com/en_US/ecb/products/pdf/en-d2ls.pdf
Current family page: https://components.omron.com/us-en/products/switches/D2LS
The legacy drawing establishes nominal geometry/forces; confirm the exact current20M ordering variant and mechanical model before footprint release.
