# AI change report — R25 (clean re-issue)

- **Platform/model:** Claude Code (Anthropic)
- **Input package revision and ZIP SHA-256:** R24 (`First full package.zip`), `96f9da59946eed5a22e70d03417e1953490420a2211e77d91bdb6a3f9b612f96`
- **Output revision:** R25 — PCB R21 (unchanged) · CASE R11 · ACRYLIC R1. This clean re-issue replaces the first R25 zip; geometry is unchanged.
- **Parent layers edited:** CASE and ACRYLIC. PCB: none.
- **Shared datum and units preserved:** yes — mm, R21 PCB XY (Y down), board bottom Z=0, +Z front.
- **PCB edits:** none. `SLIM4_R21.kicad_pcb` and `SLIM4_R21_PCB_LAYER.json` hash-match R24 (check A1). One decision is requested (sub-12 mm thickness needs lower back-side parts — see below).

## Source files changed (R24 → R25)

| File | Change |
|---|---|
| `LAYERS/02_CASE/build_r11.py` | new; replaces `build_r10.py`. Most dimensions in one `P` dictionary |
| `LAYERS/02_CASE/export_layer_formats.py` | rewritten for R11/R1, full assembly STEP, viewer meshes |
| `CHECKS/convergence_check.py`, `CHECKS/render_review.py`, `CHECKS/make_manifest.py`, `CHECKS/COMPONENT_ENVELOPES_R21.json` | new |
| `index.html`, `app.js`, `eye.js`, `eye.css`, `sw.js`, `manifest.webmanifest`, `model-data.js` (labels/notes only), `case-r3-data.js` (Z remap) | viewer follows R25 |
| `model.json` | removed (orphaned duplicate of `model-data.js`) |
| `R21_REFERENCE/CAD_REFERENCE/SLIM4_R3/` → `REFERENCES/SLIM4_R3_INTEGRATION/` | moved, files unchanged; label README added |
| `requirements.txt` | new (pinned build/check environment) |
| Docs | README, AI_HANDOFF, CHANGELOG, PRODUCTION_GATES, QC_REPORT, PROJECT_MANIFEST, SHA256SUMS, layer READMEs, `REFERENCES/README.md`, `REFERENCES/R10_CONTEXT/README.md`, ASSEMBLY_SEQUENCE |

## Dimensions or coordinates changed (before → after)

| Item | R10 / R0 | R11 / R1 |
|---|---|---|
| Exterior envelope | 104.0 × 135.3 | 104.0 × 135.3 (unchanged) |
| Shoulder / finger-scallop contour | board broke through the outer surface by 0.03 mm | moved out up to 2.35 mm: 2.0 wall + ≥0.33 clearance |
| Bottom-centre saddle lift | 4.5 | 4.0 (Y 130.8 → 131.3) |
| Datum board thickness | 1.6 | 1.2 (board file) |
| LCD module top / centre Y | 0.00 / 55.70 | 2.21 / 57.91 |
| Screen opening / lens centre Y | 55.70 | 55.648 (active-area centre) |
| LCD pocket | 60.5 × 111.6, centred on module | 60.5 wide, Y 2.11 → 114.21 (0.6 FPC bend allowance) |
| Flap caps | Ø16 × 1.5 disc on the film, Z 7.85–9.35 | Ø16 crown Z 4.85–9.35, Ø1.4 nub, Ø17.8 × 0.8 flange, 4 × Ø1.2 stop legs (stroke 0.60) |
| DART pill | 49 × 7.5 disc on the film, centre Y 118 | 49 × 6.5 rocker, centre Y 119.80; pivot X=0, Z 5.05; nubs at X ±16, Y 119.296; legs at X ±23; stop 2.15° |
| DART opening / surround | 50 × 8 / 52 × 10 at Y 118 | 50 × 7 / 52 × 9 at Y 119.80 |
| Relief (bezels, DART surround) | Z 7.85–8.35 on the film | Z 7.65–8.35, part of the shell |
| Grille slots | X ±41.5, Y 120.7 / 122.6 / 124.5 | X ±38.3, Y 123.7 / 125.6 / 127.5 |
| Film cutouts | Ø17 flap, 50 × 8 pill, 12.2 × 1.0 slots | Ø18.4 flap, 52.4 × 9.4 r4.6 DART, 12.2 × 1.0 slots on the new grille |
| Rear shell | none | floor Z −5.70…−3.70, walls 2.0, plain 1.0 mm lap joint to Z 5.65 |
| Battery | none | 34 × 52 × 7.0 at (0, 45), Z −3.5…3.5, in the board window |
| Speakers | none | CMS-18138A-SP at (±38.3, 125.6), Z 2.90–5.40, sealed 1.56 cc chambers |
| Board retention | none | 6 front/back clamps + 13 rear-only supports (19 rear posts) |

## Fit/interference checks run and results

`python -B CHECKS/convergence_check.py --baseline <R24>`: **R25 converged — 71 PASS, 0 FAIL, 13 GATE, 3 INFO.** Volume interference and clearance were tested in 308 pair evaluations over 273 distinct part pairs (270 at rest, 16 with the flaps and power plunger pressed, 11 DART left, 11 DART right). R24 baseline on the same interfaces: **17 FAIL, 1 PASS**. The checker was mutation-tested (LCD moved to the edge, a post placed on pads/under the LCD, overtravel cut to 0.02, floor raised 0.15): each injected fault was reported.

## STEP/STL/vector/DRC validation run and results

- All 19 R11/R1 solids pass B-rep validity (check M1); STEP and STL written by CadQuery 2.8 / OCCT 7.9.
- SVG/DXF cutlines are generated from the same film polygon the checks use; every cut-spec field is compared with the geometry (E1–E6).
- KiCad DRC not re-run: the board is unchanged; `NATIVE_KICAD_DRC.txt` remains the R21 draft-rule result.

## Clean re-issue — what the audit corrected

Four independent audits (references, factual accuracy, hygiene, reproducibility), each checked by an adversarial verifier, found 57 issues; 55 survived verification and are fixed here (CHANGELOG.md "R25 clean re-issue"). The most important:

- The first R25 report marked R24 row S1 FAIL, saying R24's service worker listed missing files. That was my error: the files exist. S1 is now computed and passes; a real R24 viewer defect (the clipped LAYERS panel) is recorded as S3.
- The sub-12 mm statement was wrong (see the decision below).
- The plate is 0.70 mm over the LCD ledge, not 2.0 mm everywhere (new GATE B8).
- One flap-cap stop leg lands on a via; I4 now covers stop legs and I5 checks they avoid pads.
- The viewer's labels and picks used legacy positions, and its R3 overlay was mirrored; both fixed.

## Production gates closed or still open

Closed in CAD: board/LCD containment, screen alignment, control actuation and retention, relief vs film, interference/clearance, rear shell, battery bay, speaker chambers, USB relief, routes, board clamps, service access. Still open (13 GATE rows): LCD ledge thickness (B8), HOTHMI top border (C4), D2LS FP/OP tolerance coupon (D5), D2LS actuator position (D11), DART boss print test (D12), film stock (E7), FPC extension (H4), via tenting (I4), acoustic measurement (J5), USB lip (K3), cell order (L4), lap-joint drop test (L5), LCD adhesive (L6). See `PRODUCTION_GATES.md`.

## Decision requested

Thickness is 13.55 mm (15.05 over the caps). The rear floor sits 0.2 mm below L2 (Sunlord ASWPA4035, 3.50 mm; the R21 JSON listed 1.6 mm). Sub-12 mm needs every back-side part ≤ 1.95 mm — L2, J2 (3.31), J3/J4/J5 (3.00) and J1/L1/L3 (2.00) are taller today — which is a new PCB revision, and a cell no thicker than 6.5 mm; the 7.0 mm cell alone holds the body at ≥ 12.55 mm. Replacing only L2 and J2 gives 13.05 mm. Nothing in the PCB was changed.

## Known limitations

- Purchased parts (LCD, cell, speakers) are envelopes, not supplier models. The FPC and harness routes are reserves.
- The D2LS plunger is modelled as a Ø1.6 cylinder at the body centre.
- The enclosure joint is a plain lap; no screw bosses are possible without mounting holes in the board.
