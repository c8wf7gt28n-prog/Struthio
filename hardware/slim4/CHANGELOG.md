# R29 — PCB R24: power layout after the second hardware review (2026-10-09)

PCB R23 → **R24** (9 scripted edits in `LAYERS/01_PCB/R24_FROM_R23/`; three independent rebuilds from R23 give the same copper). Same outline, ports, connector positions and GPIOs; firmware unchanged (`check_pinmap.py` passes on R24). R23 moves to `REFERENCES/PCB_R23/`. CASE R12 and ACRYLIC R2 are still set aside and were checked against R24 as they are: **78 PASS · 3 FAIL · 9 GATE · 3 INFO** (323 pair evaluations over 284 distinct pairs), the same 3 case FAIL rows as R28; no new interference from the moved or added parts. Decisions: `DECISIONS_R29.md`.

| Review item | R24 |
|---|---|
| Power distribution in 0.152 mm traces | In2 BAT_PLUS plane (721 mm²) and SYS_RAW plane (998 mm²); thin track BAT_PLUS 95 → 9 mm, SYS_RAW 247 → 31 mm, USB_VBUS 55 → 14 mm, 1V1_HP 72 → 41 mm, 3V3_SYS 382 → 238 mm (mostly U1's 3.3 V fan-out and pull-ups: a few mV); 124 power/ground segments widened; ground vias 34 → 87 |
| Switch nodes in thin traces through In3, inductors and capacitors far from their ICs | U4 (TPS63070), U3 (TLV62569) and U7 (TPS61165) re-laid per their datasheets: inductors 1–1.6 mm from the SW pins (were 4.4–8 mm), switch nodes as B.Cu copper areas with no inner-layer section, input and output capacitors at the pins, U7's SW–D2–C309–GND loop closed on B.Cu (about 4 × 4 mm) |
| TPS63070 PS/SYNC tied to VIN without a resistor | PS/SYNC joins EN on 3V3_ENABLE, behind R423 100 k |
| DSI return paths | A ground via within 1.75 mm of every DSI layer change (24 of 32 within 1.2 mm; R23: 3–10 mm). Pairs not re-routed: R23's length and skew matching stands |
| Found while checking | TPS63070 output 98 µF nominal (C416 10 µF 0603 + C414, C417–C419 22 µF); its input 10 µF 0603 C402 at the pins; 10 µF C420/C421 at each MAX98357A; four thermal vias in the BQ24074 pad; R414 removed (TMR open: default 30 min / 5 h timers) |

Parts: C301, C405, R414 removed; C416–C421 added; C402 0.1 µF 0402 → 10 µF 0603; 23 parts moved (U3, U6, U7, L1–L3, D2 and their capacitors and resistors). 170 placements, 54 BOM lines, LCSC numbers for all (new: C19702, C5674, C15850, each read from its LCSC page); U1 still to source. KiCad 7.0.11 DRC 0 / 0 / 0.

Package: `CHECKS/COMPONENT_ENVELOPES_R24.json`, `CHECKS/R24_FAB_SUMMARY.json`, `CHECKS/R29_CONVERGENCE_REPORT.*`, `ASSEMBLY/STRUTHIO_SLIM4_R29_ASSEMBLY.step`, `R24_REAR_BOARD.svg`, studio, renders and builder files regenerated. `build_builder_packs.py` now counts a solder-mask opening only for vias outside SMD pads (the U10 exposed-pad vias sit in the pad's own opening and are filled and capped). Not measured: switching waveforms, ripple and temperatures are bring-up items (`LAYERS/01_PCB/RELEASE_GATES.md`).

# R28 update 2 — the R7 review (2026-10-08)

Board files unchanged (check A1). Firmware R7 → **R8** (`firmware/slim4/RELEASE_NOTES_R8.md`).

| R7 review item | Change |
|---|---|
| Low-battery switch-off unreachable with the button released | Evaluated before the button logic; 2 s of valid readings below 3.3 V; a failed reading never switches off. |
| Thermal charge suspend entered below 3.6 V | Entry needs a qualified cell at ≥ 3.6 V; exits on cooling, < 3.6 V, a failed reading or USB removal; backlight capped while suspended. |
| CHG low alone lifted the USB backlight cap | Lifts only for a qualified cell (charging, no fault, ≥ 3.5 V for 2 s), back below 3.4 V, on a fault, a failed reading or when charging stops. |
| Scenario evidence | `firmware/slim4/tests/host`: 29 host cases on the unmodified `slim4_power.c`, including failed readings and transient dips. |
| "No damage" for a reversed pack on USB | Removed: stated as an untested steady-state analysis; the warning does not disconnect the pack; verify pack polarity before assembly. |

# R28 update — answers to the R23 / R6 simulation audit (2026-10-08)

Board files unchanged (check A1). Firmware R6 → **R7**.

| Audit item | Finding | Change |
|---|---|---|
| Emulator "stall" after `esp_psram: Reserving pool` | Not a stall. R6's console was USB-Serial-JTAG only, which esp-emu does not print. In the audit's own debug log the app reads the NVS partition (0x9000, 390 reads, `nvs_flash_init`) and both cores then idle in FreeRTOS (addresses resolved in the identical ELF, SHA-256 cc3797e8…). | R7: UART0 primary console with USB-Serial-JTAG secondary output (ESP-IDF's P4 default); USB-C still carries every app log line. |
| Q2 with USB connected | Correct: with USB the charger holds Q2's source up, so a reversed pack is not hard-blocked. Bounded: Q2 sits at its 0.5–1.3 V threshold, under the BQ24074's 1.6 V short-circuit check, so only its 4–11 mA test current flows (≤ 64 mW in Q2, BAT_PLUS ≥ 0 V). A connector-side gate drive would block it but stop the charger reviving an over-discharged pack, so the circuit stays. | Docs: the blanket "blocks a reversed pack" claim replaced everywhere. Firmware: `BATTERY REVERSED - UNPLUG` when the battery rail stays under 1.5 V on USB. |
| USB power budget | Correct at the worst-case 380 mA design provision: 1.98 W available (450 mA × 4.4 V) leaves 19 % backlight with no cell. | Firmware: backlight capped at 15 % on 500 mA USB unless a charge cycle is running. Also fixed: the over-temperature charge suspend (USB suspend, CE is tied low) now only happens while a cell is charging. |
| Firmware evidence missing | The R6 zip held images only. | R7 release zip: images, merged image for esp-emu, ELF, map, sdkconfig, dependencies.lock, source and docs. |
| Builder pack references | The READMEs cite package documents not in the zip. | New `PROJECT_DOCS/` folder: PRODUCTION_GATES, RELEASE_GATES, ASSEMBLY_SEQUENCE, the convergence report, BOM sourcing. |
| Two-lane panel set-up | The driver writes page-1 register 0xB7 = 0x03 (2 lanes) before the Crystalfontz table, which never writes 0xB7. | None; the image is a bench check. |

# R28 — PCB R23: four plug-and-play ports; firmware for R23; case set aside

PCB R22 → **R23** (4 scripted edits in `LAYERS/01_PCB/R23_FROM_R22/`, rebuilt copper-identically from R22). The display flex is gone: the panel's own tail plugs into the main board. CASE R12 and ACRYLIC R2 are set aside by the owner and were checked against R23 as they are: **78 PASS · 3 FAIL · 9 GATE · 3 INFO** (317 pair evaluations over 278 distinct pairs); the 3 FAIL rows are case items. Decisions: `DECISIONS_R28.md`.

## PCB R23 (from R22)

| # | Change |
|---|---|
| 12 | Battery: J3 JST PH 2.0 socket at the window's left edge; Q2 AO3401A reverse-polarity switch (new net BAT_CONN) |
| 13 | Speakers: J4, J5 Molex PicoBlade 53261-0271, pin 1 + |
| 14 | R412 1.8 k: charging 494 mA. R309 2.7 Ω: backlight 74 mA (two strings, 37 mA each) |
| 15 | J1 Hirose FH12A-40S-0.5SH(55), top contact, on the front at (1.9, 76.0), pad k = Crystalfontz panel pin k; battery window bottom edge Y 73 → 70.5 (38 × 53.5 mm); J1 fan-out and routes to the display circuits; BQ_EN2, CHG_STATUS, PGOOD_STATUS, PWR_WAKE, USB_CURR_OUT2 rerouted; DSI P = N within 0.01 mm (CLK 60.25, D0 56.25, D1 54.84 mm) |

KiCad 7.0.11 DRC 0 / 0 / 0. 167 parts, 52 BOM lines, LCSC numbers for all; U1 to source.

## Package

- R22's board, library, layer JSON, DRC report and gates moved to `REFERENCES/PCB_R22/`; the display flex to `REFERENCES/DISPLAY_FLEX_R1/`.
- `CHECKS/export_pcb_layer.py` takes the board's cut-outs (the moved battery window) from the board.
- `CHECKS/COMPONENT_ENVELOPES_R23.json`: J1 FH12A (2.0 mm) on the front; JST PH and PicoBlade sockets; AO3401A.
- `CHECKS/convergence_check.py`: A1 locks the R23 board and layer JSON; N1 checks J1's 40 pads against the Crystalfontz pin table (40/40); H4 describes the folded tail; L4 the 34 × 50 mm cell.
- `CHECKS/build_builder_packs.py`: R28 builder files; no flex folder; the order README covers the four plug-in parts, the top-contact J1 and the DSI impedance.
- `LAYERS/02_CASE/build_r12.py`: cell envelope 34 × 50 × 7 in the shorter window; the FPC reserve ends at the board's back face.
- Studio: R23 board data, J1 on the front in the tour, 74 mA backlight, DSI lengths.
- Firmware (`firmware/slim4`, R6): ILI9881C driver with the Crystalfontz init sequence, 2 lanes at 1 Gbit/s; builds with ESP-IDF v6.1 with no warnings; `tools/check_pinmap.py` checks every firmware GPIO against the R23 board.

## Case pass (set aside)

- **C6:** the 5 in Crystalfontz module against the R12 pocket.
- **F1, G1:** the rear shell against the J3, J5 and J4 bodies.

# R27 — PCB R22 in the package; display flex R1; case checked on R22

PCB R21 → **R22** (the electrical and land-pattern review fixed, 11 scripted edits in `LAYERS/01_PCB/R22_FROM_R21/`, rebuilt copper-identically from R21). The display cable is a new fourth layer, `LAYERS/04_DISPLAY_FLEX`. CASE R12 and ACRYLIC R2 are unchanged and were checked against R22: **78 PASS · 3 FAIL · 9 GATE · 3 INFO** (327 pair evaluations over 288 distinct pairs). The 3 FAIL rows are the case pass the owner deferred (`PRODUCTION_GATES.md`). Decisions: `DECISIONS_R27.md`.

## PCB R22 (from R21)

| # | Change |
|---|---|
| 1 | USB-C data to the ESP32-P4's USB-Serial-JTAG (GPIO24/25) |
| 2–4 | KiCad library lands for U11/U12 (1 × 1 mm DRT), J3–J5 (with solder tabs; J4 2.7 mm inboard), D1, Y1, SW5–SW7 |
| 5–8 | Crystal load 12 pF; backlight 39 mA with a 50 V output capacitor; panel VCI 3.0 V; C603 moved 0.15 mm |
| 9 | Battery port: JST SH 2-pin (any protected cell), 10 k on the charger's TS pin |
| 10 | JLCPCB stock substitutions, same value and package; SW1–SW4 all D2LS-21 |
| 11 | L1–L3 to Sunlord's recommended lands (the proxies were short of or narrower than the terminals); one 3V3_SYS track under L2 moved; audited-land descriptions |

KiCad 7.0.11 DRC 0 / 0 / 0. 166 parts, 50 BOM lines, LCSC numbers for all, in stock at JLCPCB on 2026-10-07 except U1.

## Package

- R21's board, library, layer JSON and gates moved to `REFERENCES/PCB_R21/` (inputs of the R22 rebuild and the exporter).
- New `CHECKS/export_pcb_layer.py` writes `SLIM4_R22_PCB_LAYER.json` from the board. Validated on R21: its segments, vias and nets reproduce the R21 file exactly. Its pads also fix the R21 file's 80 mirrored pads on rotated back-side parts.
- `CHECKS/COMPONENT_ENVELOPES_R22.json`: the R22 part values (D2LS-21, Samsung CL21/CL10, 0402CG, 0603WAF); J3 is the 2-pin header.
- `CHECKS/convergence_check.py`:
  - A1 locks the R22 board and layer JSON.
  - New C6 tests the chosen Startek panel against the LCD pocket.
  - New N1 tests the flex's 20 J1 fingers against the R22 J1 pads, position and net.
  - H4, I4 and L4 were rewritten for the flex, filled-and-capped vias and the 2-pin cell.
- `CHECKS/build_builder_packs.py`:
  - `1_PCB_FABRICATION` is the R22 JLCPCB order (courtyard assembly drawings, review docs in REFERENCE, U1 stock note).
  - New `4_DISPLAY_FLEX` holds the flex order once the pin map is filled; until then it has the 1:1 fit template.
  - The print README says not to print until the case pass.
  - It writes `CHECKS/R22_FAB_SUMMARY.json`.
- Studio:
  - `model-data.js` geometry is now written from the R22 layer file by `build_pcb_viewer_data.py`, along with the pours, sourcing, fab status, open FAIL and GATE rows, and the `R22_REAR_BOARD.svg` plot.
  - The tour computes its counts from the loaded board.
  - Labels read R22 / R27.
  - Lands audited in R22 show as such.
- Case harness reserves follow the R22 J3/J4/J5 positions; the shells, controls and film are unchanged.

## Case pass (open)

The R27 report lists three FAIL rows:
- **C6:** the Startek module is 61.0 mm wide; the R12 pocket is 60.5 mm.
- **F1 and I1:** J5's real JST SH body and its solder tab reach the rear support post at (40.75, 108).

# R26 — decisions made; CASE R12, ACRYLIC R2

PCB R21 unchanged (check A1). Every open item that needed only a decision is decided in `DECISIONS_R26.md`; the rest is listed exactly in `PRODUCTION_GATES.md`. Convergence: **79 PASS · 0 FAIL · 9 GATE · 3 INFO** (326 pair evaluations over 287 distinct pairs).

## Geometry (CASE R11 → R12, ACRYLIC R1 → R2)

| Item | R11 / R1 | R12 / R2 |
|---|---|---|
| Lap joint | skirt and lip 1.0 mm each, line-to-line, no retention | 0.95 mm each, 0.10 mm radial clearance; lip top 0.10 mm under the plate; 0.10 mm tape ring (new part) |
| LCD module Z | 5.20–6.95, touching ledge and lens | 5.10–6.85; 0.10 mm display tape frame (new part) bonds module, ledge and lens; 1.6 mm free behind it |
| FPC route under the module | Z 4.75–5.15 (fold to 6.85) | Z 4.65–5.05 (fold to 6.75) |
| DART trunnion bore | Ø1.10 (0.05 radial) | Ø1.20 (0.10 radial) |
| DART boss floor | Z 4.45 | Z 4.30 (0.15 mm under the bore; the wider bore would otherwise be tangent to the floor) |
| Lens | 0.70 mm, material open | 0.70 mm chemically strengthened cover glass |
| Film outline | equal to the case outline | 0.20 mm inside it |
| Film vents | six 12.2 × 1.0 slots | two 12.2 × 4.8 r0.3 windows |
| Film stack | 0.20 mm assumed | 0.175 PET + 0.025 OCA = 0.20 mm, unprinted |

Body thickness unchanged: 13.55 mm (15.05 mm over the caps).

## Checks

- Closed: E7 (film stack), L5 (joint: measured clearance and tape seat), L6 (display stack: module + tape = ledge = lens underside). L4 now tracks only the cell in hand (spec decided).
- New: D15 (material under each trunnion bore ≥ 0.15 mm), E8 (narrowest film cut ≥ 1.5 mm). E1, E4, E5 and E6 rewritten for the inset outline and vent windows; contact rules added for the two tapes.
- Renderer: new section F (lap joint and display stack). Fixed a bug in the exploded view: its "keep PCB parts in place" test matched any part name starting with R, C, D or L, so the rear shell, film, DART rocker and cell were never exploded.

## Builder files and BOM

- `CHECKS/BOM_SOURCING_R21.json`: LCSC numbers for the 14 parts the locked board file lacks, each checked on its LCSC/JLCPCB page (C310 → C16772). All 165 parts are now bound.
- PCB, print and film READMEs carry the decided specifications (EVT quantities, stackup, finish, via-in-pad, SLA resin, film stack). The sticker pack adds the display tape frame and lap tape ring die-cuts; the lens folder is now a cover-glass order.

## Studio

Labels read CASE R12 / FILM R2 / R26; the film's print, white and relief layers show "not used" (unprinted prototype film) and the adhesive layer shows the 0.025 mm OCA. Service-worker caches renamed.

# R25 studio 1.1

PCB R21, CASE R11 and ACRYLIC R1 geometry unchanged. The studio is brought up to date with the package:

- **Copper pours.** The six filled zones stored in the R21 board (GND planes on In1 and In4; 3V3_SYS, SYS_RAW, BAT_PLUS and 1V1_HP pours on In2) are drawn under the tracks in COPPER and XRAY modes and in the INNER stack view. Per-zone areas equal KiCad's.
- **BOM and sourcing per part.** Tapping a part shows its manufacturer part number, package, LCSC number or "by manufacturer part number" / "not bound yet", and whether its land pattern is a vendor pattern or a proxy awaiting audit; R403 and C408 show their via in pad. FIND also searches part numbers and LCSC codes.
- **Fab status.** The board view shows the builder files (Gerber ×13, drill, BOM, CPL) and the KiCad 7.0.11 DRC result, labelled prototype only.
- **Tour.** The connector stop was wrong: the pad nets show that J1 is the display link (MIPI-DSI clock and two lanes, LCD power, backlight) and J3 the cell lead (BAT_PLUS, BAT_NTC, GND); it now says so (basis FILE). New stops: PLANES, BUILDER FILES and OPEN GATES, all computed from the data.
- **Gate I4 closed.** `build_builder_packs.py` now tests the plotted mask Gerbers at every via (no opening at any of the 269; the same test finds an opening at all 587 pads) and records it in `CHECKS/R21_FAB_SUMMARY.json`. I4 passes only when the board's plot setting tents vias and that record, made from the same board hash, shows no opening. Result: 72 PASS · 0 FAIL · 12 GATE · 3 INFO.
- New `CHECKS/build_pcb_viewer_data.py` adds `zones`, per-part sourcing, `fab` and `gates` to `model-data.js` without changing its board geometry (checked field by field). `CHECKS/build_builder_packs.py` now also writes `CHECKS/R21_FAB_SUMMARY.json`.
- Studio version 1.1; service-worker caches renamed (package and deploy bundle) so installed copies update.

# R25 builder packs

No geometry, check or source changed. New `CHECKS/build_builder_packs.py` writes the files for the three suppliers, each folder with an order README:

- **1_PCB_FABRICATION**: Gerber X2 (13 layers) and Excellon drill zip plotted with KiCad 7.0.11 from a temporary copy of the unchanged R21 board; BOM (52 lines, LCSC numbers where the board records them; 14 parts by manufacturer number only, C310 still to be bound); placement (CPL, 165 parts); assembly drawings; drill maps; KiCad 7.0.11 DRC (0 violations, 0 unconnected, 0 footprint errors; zone fills current); the KiCad source. The README carries the board specification read from the file (6 layers, 1.2 mm, 0.10 mm track/space, 269 tented 0.20/0.45 vias, two vias in pads, USB-C plated slots) and keeps R21's "prototype only" status and its release gates.
- **2_3D_PRINTING**: one STL and one STEP per printed part (front shell, rear shell, flap caps L/R, DART rocker, power plunger), meshes checked closed, volumes checked against the CAD, with a process recommendation and the features to protect.
- **3_ACRYLIC_STICKER**: the R1 cut line as a 1:1 PDF in a CutContour spot colour, SVG and DXF (the DXF is identical to the R1 file), an A4 1:1 check drawing with the screen keep-clear zone, and the optional 0.7 mm lens outline. Print artwork is still not designed; the README flags the zero-margin perimeter and the 1.0 mm vent slots for the printer to confirm.

Rebuilds are byte-identical (plot timestamps are pinned to the package date).

# R25 viewer deploy bundle

No geometry, check or viewer source changed. New `CHECKS/build_viewer_bundle.py` writes a deployable copy of the viewer: 7 files, about 2.7 MB (about 465 KB zipped), against 30 precached files and 5.3 MB for the viewer inside the package and about 250 files and 45 MB for the whole package. The CSS is inlined; scripts and meshes are joined into `studio.js`; CASE, ACRYLIC and R3 mesh coordinates are packed as Int16 at 0.01 mm (largest decode error 0.005 mm) with Uint16 shades (exact), and unpacked at load, so `app.js` and `eye.js` run unchanged. The SVG is trimmed to 0.001 mm. Its service worker precaches only those files. Headless-browser checks match the package viewer (CAD picks, LAYERS panel, R3 overlay, offline cache, no errors).

# R25 clean re-issue

Replaces the first R25 zip. CASE R11 and ACRYLIC R1 geometry is unchanged (every STL, SVG, DXF, JSON, mesh and render file is byte-identical; in the STEP files OCCT re-orders its colour-style records, but every part keeps the same name, colour, volume and bounding box — checked by an XDE comparison). PCB R21 unchanged (check A1). Four independent audits, each with an adversarial verifier, drove these changes.

## Corrections

- **R24 baseline row S1 was wrong.** The first R25 report said R24's service worker precached files missing from the package. They exist (`R21_REFERENCE/CAD_REFERENCE/SLIM4_R3/SLIM4_R3_integration.step` and `build.py`, now under `REFERENCES/SLIM4_R3_INTEGRATION/`). S1 is now computed from R24's `sw.js` and passes. A new computed row, S3, records a real R24 defect that was not in the audit: the LAYERS panel was clipped and never visible. R24 baseline: **17 FAIL · 1 PASS**.
- **Sub-12 mm statement was wrong.** Replacing L2 and J2 alone gives 13.05 mm, not sub-12. Sub-12 needs every back-side part ≤ 1.95 mm (L2, J2, J3, J4, J5, J1, L1 and L3 are taller today) and a cell no thicker than 6.5 mm; the 7.0 mm cell alone holds the body at ≥ 12.55 mm. Check L1 now computes this from the envelope table.
- **Plate thickness.** The plate is 2.0 mm nominal but only 0.70 mm over the LCD pocket ledge outside the lens rebate. New GATE row B8 measures it on the solid; B5 is retitled as nominal design parameters.
- **Stop legs.** One SW2 flap-cap stop leg lands on a 3V3_SYS via. I4 now covers stop legs as well as posts (two vias, both to be tented), and a new row I5 confirms every stop leg is clear of pads. Cap and rocker retention is now a check row (D14).
- **Counts and wording.** 13 rear-only supports (19 rear posts), not 14. Six front clamp posts, not four. 308 is the number of pair evaluations (273 distinct pairs), not 308 pairs in each pose. The enclosure joint is a plain 1.0 mm lap: no detent is modelled. Screen-stack and internals sublayers are STEP only. The film has no screen window. The cut spec is a generated file. Clearance exceptions for designed contacts are now listed. Not every dimension is in `P`. "No holes" now reads "no mounting or screw holes". The J4 note on the R3 volume study is corrected.
- **Checker.** E6 compares every cut-spec field (it compared three). B7 tests the grille bars directly. The R24 B2 ranges are computed (break-through 0.03 mm at Y 78.8–79.7; wall entry at Y 72.5–87.9 and 109.6–117.4).

## Viewer

- Labels and click-picks for the LCD, cell, speakers, caps, rocker and power plunger now come from the R11 CAD parts; they used the legacy R4 envelope positions, which point at the wrong places. The legacy boxes are now a real fallback when `case-layer-data.js` is missing.
- The R3 reference overlay (`case-r3-data.js`) was mirrored in Z (the R3 display drew behind the board). It is remapped with z′ = 6.5 − z_step.
- The EYE tour's last stop said the CASE and ACRYLIC sources were missing; it now describes R11/R1. The inspector keeps "R1" in the ACRYLIC label. A favicon link removes the 404 on load. The service-worker cache is renamed so installed copies update.

## Package clean-up

- Removed `model.json`: an orphaned R22-labelled duplicate of `model-data.js` that nothing loaded.
- Moved `R21_REFERENCE/CAD_REFERENCE/SLIM4_R3/` to `REFERENCES/SLIM4_R3_INTEGRATION/` (files unchanged) and added `REFERENCES/README.md` and a README in that folder labelling it reference-only, with notes on its datum, missing files and `build.py` side effects. Notes were also added to `REFERENCES/R10_CONTEXT/README.md` (stale lens name, one mis-encoded product name); its STEP is unchanged.
- Added `requirements.txt` (pinned), `python -B` in the documented commands and a bytecode guard in the scripts that import the checker, so regenerating leaves no `__pycache__`. `CHECKS/make_manifest.py` is now documented as the last step.
- `build_r11.py`: removed two unused aliases and corrected two stale comments (outputs unchanged).
- README now maps the package layout; the layer READMEs list all their outputs.

# R25 change log — convergence

PCB R21 unchanged (SHA-256 verified by check A1). CASE R10 → R11. ACRYLIC R0 → R1.

## Cross-layer defects found in R24 and fixed in R25

| R24 defect (CHECKS/R24_BASELINE_AUDIT.md) | R25 fix |
|---|---|
| R10 outline did not contain the R21 board: the board edge broke through the outer surface by 0.03 mm at the shoulders (Y 78.8–79.7) and entered the 2.0 mm wall at Y 72.5–87.9 and 109.6–117.4 | Outline R11 = R10 silhouette ∪ (board + 2.0 wall + 0.3 clearance + 0.05 margin) ∪ (LCD + 2.0 wall + 0.25), smoothed. Envelope still 104.0 × 135.3. Shoulders and finger scallop move out by up to 2.35 mm |
| LCD module top edge at Y=0, on the exterior surface | LCD back to the R3 position: top Y 2.21, centre Y 57.91 |
| Screen opening centred on the module, not on the active area (R3 1.79 mm top border) | Opening, lens and rebate centred on the active area, Y 55.648 (margins 0.35 mm); the film stays continuous over the lens |
| Case modelled the board at 1.6 mm; the board file says 1.2 mm | Board thickness read from the board file |
| 16 mm caps and the DART pill sat on top of the film, 3.15 mm above the switch plungers, with no stem, retention, pivot or stop | Flap caps: Ø1.4 nub 0.15 mm above D2LS FP, Ø17.8 retention flange, four stop legs landing on the board after 0.60 mm (OT 0.15 past OP; one SW2 leg lands on a via that must be tented, I4). DART rocker: trunnion pivot in two plate bosses at X=0, nubs on SW3/SW4, stop legs at X ±23 (2.15°) |
| "Molded" bezels and DART surround sat on top of the film | Relief is part of the front shell and rises 0.5 mm through film cutouts with 0.2 mm clearance |
| No rear shell, battery, speakers, chambers, USB-C aperture, FPC route, board retention or service access | Added: rear shell (2.0 mm floor/walls, plain 1.0 mm lap joint), 34 × 52 × 7.0 cell in the board window, two Same Sky CMS-18138A-SP speakers in sealed 1.56 cc chambers, USB-C overmold relief, FPC extension route (panel → between DART switches → around the board tab → J1), battery and speaker lead routes, 6 front/back board clamps + 13 rear-only supports (19 rear posts) clear of pads, power plunger on SW5 and pinholes on SW6/SW7 |
| Viewer: LAYERS panel clipped and never visible; lens exported in the "display" group | LAYERS panel moved out of the clipped column; lens in its own group; new Rear shell, Battery, Speakers and Routes sublayers; explode applies to the CAD layers |
| R0 SVG/DXF cutlines were drawn upside down (vertical mirror; harmless only because the film is left-right symmetric) | R1 SVG is Y-down in the shared datum, DXF is the same front view in Y-up |

## Other R25 changes

- DART pill and opening centred at Y 119.80 (0.504 below the fixed switch row) so the LCD pocket can run 0.6 mm past the module for the panel FPC bend and still leave a 2.0 mm web.
- Saddle lift at the bottom centre reduced from 4.5 to 4.0 mm so the FPC can wrap the board tab (0.35 mm to the wall).
- Grille slots moved onto the speakers (X ±38.3, Y 123.7 / 125.6 / 127.5).
- `CHECKS/COMPONENT_ENVELOPES_R21.json`: datasheet heights replace placeholder JSON heights where they matter (L2 Sunlord ASWPA4035 is 3.5 mm, not 1.6; B3U is 1.6 mm, not 4.6; D2LS FP/OP/OT from the Omron sheet). The rear floor depth follows L2.
- New: `CHECKS/convergence_check.py`, `CHECKS/render_review.py`, `CHECKS/make_manifest.py`, `CHECKS/renders/`, `ASSEMBLY/STRUTHIO_SLIM4_R25_ASSEMBLY.step`, `ASSEMBLY/ASSEMBLY_SEQUENCE.md`, `AI_CHANGE_REPORT_R25.md`.
- Removed from LAYERS: the R10 case and R0 film outputs and `build_r10.py` (kept in the R24 package and in git history). The R10 reference STEP remains in `REFERENCES/R10_CONTEXT/` as non-authority comparison data.

# R24 change log

- Kept the R21 native KiCad board byte-for-byte unchanged and placed it in the PCB parent folder with its project and local footprints.
- Separated the R10 front enclosure/screen/control solids from the clear acrylic face film into standalone CASE and ACRYLIC layers.
- Added STEP/STL per parent, 2D SVG/DXF sticker cutline, platform-neutral geometry JSON, shared-coordinate documentation, and repeatable CadQuery export sources.
- Split the PWA mesh data by CASE and ACRYLIC parent so the studio viewer reads separate parent-layer files.
- Retained R3 and the mixed R10 STEP assembly only as clearly labeled reference material.
- Added AI handoff guidance, production gates, file manifest, and checksums.
