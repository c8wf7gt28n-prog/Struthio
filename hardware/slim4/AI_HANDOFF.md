# AI platform handoff

## Source authority

The project has three independent physical layers. Keep each layer in its own folder and preserve the shared coordinate system: **millimetres; R21 PCB XY (Y down, as in KiCad); board bottom at Z=0; +Z toward the front.** The R21 PCB file is the locked motherboard baseline. Do not change its footprint positions, nets, outline, or routing while editing the case or acrylic. If a proposed change needs a PCB edit, describe the conflict and request an explicit decision instead of moving the board silently.

| Parent | Main editable source | Neutral interchange | Current scope |
|---|---|---|---|
| PCB | `LAYERS/01_PCB/SLIM4_R21.kicad_pcb` | `SLIM4_R21_PCB_LAYER.json` | R21 board/layout; preserved baseline, engineering review only |
| CASE | `LAYERS/02_CASE/build_r11.py` | `STRUTHIO_CASE_R11.step/.stl`; per-sublayer STEP (STL also for front shell, rear shell and controls); `CASE_LAYER_R11_MESH.json` | R11 complete enclosure: front shell, rear shell, controls, screen stack, internals (battery, speakers, FPC/harness reserves) |
| ACRYLIC | `LAYERS/02_CASE/build_r11.py` (film section and `P`) | STEP, STL, SVG, DXF; generated cut spec `ACRYLIC_LAYER_R1_CUT_SPEC.json` | clear face film R1 and cutline; 0.20 mm assumed; print artwork not designed |

Cross-layer authority: `CHECKS/convergence_check.py`. A revision is converged only when it reports **0 FAIL**. GATE rows are physical or supplier items that CAD cannot close; they are listed in `PRODUCTION_GATES.md`.

`SLIM4_R21_PCB_LAYER.json` is kept byte-identical to R24 (check A1). Its top-level `"name"` string is a legacy R23 label ("R21 PCB + R10 CASE"); it does not mean an R10 case is included. Use its `"layer"` / `"revision"` keys (PCB / R21).

## How to make a change

1. Read this file, `PROJECT_MANIFEST.json`, `PRODUCTION_GATES.md` and `CHECKS/R25_CONVERGENCE_REPORT.md` first.
2. Edit one parent layer at a time. Most CASE/ACRYLIC dimensions are in the `P` dictionary at the top of `build_r11.py`; derived positions (screen opening on the active area, film cutouts on the relief, grille on the speakers) follow automatically. The support/clamp post positions (`CLAMP_POSTS`, `REAR_ONLY_POSTS`), the R10 silhouette control points and the FPC/harness route geometry are constants further down `build_r11.py` and are edited there. Record every changed file and dimension in the next revision's changelog.
3. For CASE or ACRYLIC geometry, install the pinned environment (`python -m pip install -r requirements.txt`: CadQuery 2.8, OCP 7.9, shapely, numpy, matplotlib, Pillow), then run from the package root, in this order:
   `python -B LAYERS/02_CASE/export_layer_formats.py` (STEP/STL, SVG/DXF, cut spec, fit summary, viewer meshes, full assembly STEP)
   `python -B CHECKS/convergence_check.py` (must end with 0 FAIL)
   `python -B CHECKS/render_review.py` (sections and views for the change report)
   `python -B CHECKS/make_manifest.py` (last: PROJECT_MANIFEST.json and SHA256SUMS.txt).
4. Component heights the checks use live in `CHECKS/COMPONENT_ENVELOPES_R21.json`, with their sources. Update that table (not the PCB) when a supplier figure changes.
5. For PCB edits, use KiCad with the bundled project, local footprint library, and project file. Exported JSON is for inspection/interchange, not a replacement for the native board. A PCB edit is a new PCB revision and needs an explicit decision.
6. Never treat the transparent acrylic film as print art. The SVG/DXF paths describe an unapproved cutting study; confirm material, process tolerance, edge margins, adhesive, optical zone, and supplier conventions before manufacturing.
7. Return the revised source files with a change report (see `AI_CHANGE_REPORT_TEMPLATE.md` and `AI_CHANGE_REPORT_R25.md`), the convergence report, renders, and updated checksums (`python -B CHECKS/make_manifest.py`). Do not overwrite this package; create a new revision.

## Interchange files

STEP is the primary CAD exchange for solids; STL is for mesh viewers/printing; SVG/DXF are two-dimensional acrylic cutting references (SVG is Y-down in the shared datum; DXF is Y-up, i.e. the same front view); KiCad remains native for the PCB; JSON supports inspection by tools that cannot open the native application formats. `ASSEMBLY/STRUTHIO_SLIM4_R25_ASSEMBLY.step` combines all three layers (PCB solids are derived envelopes, not the PCB authority). `index.html` opens the integrated browser viewer; its CASE and ACRYLIC geometry is loaded from `case-layer-data.js` and `acrylic-layer-data.js`. To publish the viewer, run `python -B CHECKS/build_viewer_bundle.py <folder outside the package>` and deploy that 7-file folder; the package itself stays the source. To produce the files for the PCB house, the print service and the sticker printer, run `python -B CHECKS/build_builder_packs.py <folder outside the package>` (needs KiCad 7.0.x as well); it never edits the PCB.

Rebuilds are reproducible with the pinned `requirements.txt`: every STL, SVG, DXF and JSON file written by `export_layer_formats.py`, the viewer meshes `case-layer-data.js` and `acrylic-layer-data.js`, the convergence reports and the renders regenerate byte-for-byte. STEP headers carry a fixed timestamp; the only remaining STEP differences between runs are how OCCT orders its colour-style records (part names, colours and geometry identical), so the STEP hashes in `PROJECT_MANIFEST.json` and `SHA256SUMS.txt` change after every export. `model-data.js`, `case-r3-data.js` and `R21_REAR_BOARD.svg` are maintained by hand; no script in this package writes them.
