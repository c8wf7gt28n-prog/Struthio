# R25 change log — convergence

PCB R21 unchanged (SHA-256 verified by check A1). CASE R10 → R11. ACRYLIC R0 → R1.

## Cross-layer defects found in R24 and fixed in R25

| R24 defect (CHECKS/R24_BASELINE_AUDIT.md) | R25 fix |
|---|---|
| R10 outline did not contain the R21 board: the board edge reached the outer surface at the shoulders (Y≈78-80) and entered the 2 mm wall at Y 70-89 and 103-117 | Outline R11 = R10 silhouette ∪ (board + 2.0 wall + 0.3 clearance) ∪ (LCD + 2.0 wall + 0.25), smoothed. Envelope still 104.0 × 135.3. Shoulders and finger scallop move out by up to 2.35 mm |
| LCD module top edge at Y=0, on the exterior surface | LCD back to the R3 position: top Y 2.21, centre Y 57.91 |
| Screen opening centred on the module, not on the active area (R3 1.79 mm top border) | Opening, lens and rebate centred on the active area, Y 55.648 (margins 0.35 mm) |
| Case modelled the board at 1.6 mm; the board file says 1.2 mm | Board thickness read from the board file |
| 16 mm caps and the DART pill sat on top of the film, 3.15 mm above the switch plungers, with no stem, retention, pivot or stop | Flap caps: Ø1.4 nub 0.15 mm above D2LS FP, Ø17.8 retention flange, four stop legs landing on bare board after 0.60 mm (OT 0.15 past OP). DART rocker: trunnion pivot in two plate bosses at X=0, nubs on SW3/SW4, stop legs at X ±23 (2.15°) |
| "Molded" bezels and DART surround sat on top of the film | Relief is part of the front shell and rises 0.5 mm through film cutouts with 0.2 mm clearance |
| No rear shell, battery, speakers, chambers, USB-C aperture, FPC route, board retention or service access | Added: rear shell (2.0 mm floor/walls, 1.0 mm lap joint), 34 × 52 × 7.0 cell in the board window, two Same Sky CMS-18138A-SP speakers in sealed 1.56 cc chambers, USB-C overmold relief, FPC extension route (panel → between DART switches → around the board tab → J1), battery and speaker lead routes, 6 front/back board clamps + 14 rear supports on bare board, power plunger on SW5 and pinholes on SW6/SW7 |
| Viewer: sw.js precached two files that are not in the package (offline install failed); lens exported in the "display" group | Service worker rewritten (precache list resolves; big CAD files cached on first use); lens in its own group; new Rear shell, Battery, Speakers and Routes sublayers; explode applies to the CAD layers |
| R0 SVG/DXF cutlines were drawn upside down (vertical mirror; harmless only because the film is left-right symmetric) | R1 SVG is Y-down in the shared datum, DXF is the same front view in Y-up |

## Other R25 changes

- DART pill and opening centred at Y 119.80 (0.504 below the fixed switch row) so the LCD pocket can run 0.6 mm past the module for the panel FPC bend and still leave a 2.0 mm web.
- Saddle lift at the bottom centre reduced from 4.5 to 4.0 mm so the FPC can wrap the board tab (0.35 mm to the wall).
- Grille slots moved onto the speakers (X ±38.3, Y 123.7 / 125.6 / 127.5).
- `CHECKS/COMPONENT_ENVELOPES_R21.json`: datasheet heights replace placeholder JSON heights where they matter (L2 Sunlord ASWPA4035 is 3.5 mm, not 1.6; B3U is 1.6 mm, not 4.6; D2LS FP/OP/OT from the Omron sheet). The rear floor depth follows L2.
- New: `CHECKS/convergence_check.py`, `CHECKS/render_review.py`, `CHECKS/renders/`, `ASSEMBLY/STRUTHIO_SLIM4_R25_ASSEMBLY.step`, `ASSEMBLY/ASSEMBLY_SEQUENCE.md`, `AI_CHANGE_REPORT_R25.md`.
- Removed from LAYERS: the R10 case and R0 film outputs and `build_r10.py` (kept in the R24 package and in git history). `REFERENCES/R10_CONTEXT/` remains as non-authority comparison data.

# R24 change log

- Kept the R21 native KiCad board byte-for-byte unchanged and placed it in the PCB parent folder with its project and local footprints.
- Separated the R10 front enclosure/screen/control solids from the clear acrylic face film into standalone CASE and ACRYLIC layers.
- Added STEP/STL per parent, 2D SVG/DXF sticker cutline, platform-neutral geometry JSON, shared-coordinate documentation, and repeatable CadQuery export sources.
- Split the PWA mesh data by CASE and ACRYLIC parent so the studio viewer reads separate parent-layer files.
- Retained R3 and the mixed R10 STEP assembly only as clearly labeled reference material.
- Added AI handoff guidance, production gates, file manifest, and checksums.
