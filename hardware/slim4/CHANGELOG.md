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
