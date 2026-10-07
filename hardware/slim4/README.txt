STRUTHIO SLIM4 — R26 ENGINEERING PROTOTYPE PACKAGE

R26 takes the converged R25 layers and makes every decision that was still open, so the
project can be built as an engineering prototype (EVT). The decisions and their reasons are
in DECISIONS_R26.md.

  01_PCB     R21, unchanged byte for byte (locked baseline).
  02_CASE    R12 — complete enclosure built around R21: front shell, rear shell,
             flap caps, DART rocker, power plunger, screen stack (LCD, 0.10 mm tape frame,
             0.70 mm cover glass), battery, speakers, lap tape ring, FPC and harness routes.
  03_ACRYLIC R2  — clear unprinted face film, 0.175 mm PET + 0.025 mm OCA, edge 0.20 mm inside
             the case outline, one vent window per speaker (STEP/STL, SVG/DXF, cut spec).

CHECKS/convergence_check.py tests every interface between the layers (board vs walls,
LCD vs shell, caps vs switches, film vs relief, parts vs parts at rest and pressed,
supports and stop legs vs pads, joints and tape seats, speakers, USB-C, battery). Result:

  CONVERGED — 79 PASS · 0 FAIL · 9 GATE · 3 INFO   (CHECKS/R26_CONVERGENCE_REPORT.md)
  The R24 package, audited on the same interfaces: 17 FAIL · 1 PASS (CHECKS/R24_BASELINE_AUDIT.md).

A GATE is an item the CAD agrees on but that still needs a physical sample, supplier
drawing or test (switch tolerance coupon, HOTHMI drawing, FPC extension, cell in hand,
thin ledge, trunnion and drop tests, acoustics). PRODUCTION_GATES.md lists exactly what is
still open, including the R21 electrical review. Not a production release.

Shared CAD datum (unchanged): millimetres, R21 PCB XY (Y down), board bottom at Z=0,
+Z toward the front. Body thickness 13.55 mm (15.05 mm over the caps).

Start with:
  index.html                          integrated viewer, Studio 1.1 (LAYERS: CASE, PCB, ACRYLIC sublayers;
                                      copper pours, BOM/sourcing per part, fab status, open gates)
  DECISIONS_R26.md                    every decision R26 made, why, and how to reverse it
  CHECKS/R26_CONVERGENCE_REPORT.md    what was checked and what is still open
  CHECKS/renders/                     cross-sections and shaded views from the B-rep
  AI_CHANGE_REPORT_R26.md             what changed from R25 and why (R25: AI_CHANGE_REPORT_R25.md)
  ASSEMBLY/ASSEMBLY_SEQUENCE.md       build order
  PRODUCTION_GATES.md                 exactly what is still open

Package layout:
  LAYERS/01_PCB      locked R21 KiCad board, project, footprints, PCB interchange JSON (authority)
  LAYERS/02_CASE     CASE R12 source (build_r12.py, export_layer_formats.py) and its exports;
                     the same source also builds the ACRYLIC film
  LAYERS/03_ACRYLIC  film R2 outputs: STEP, STL, SVG, DXF, cut spec, mesh
  ASSEMBLY/          all three layers in one STEP, and the build order
  CHECKS/            convergence checker and its reports, renderer and renders,
                     component height table, BOM sourcing (BOM_SOURCING_R21.json),
                     manifest/checksum generator, viewer deploy-bundle builder, builder-pack generator
  REFERENCES/        reference only, not authorities: the R10 fit-study STEP and the
                     SLIM4 R3 integration study (each folder has a README)
  root               viewer (index.html, app.js, eye.js, styles.css, eye.css, model-data.js,
                     case-layer-data.js, acrylic-layer-data.js, case-r3-data.js [R3 reference],
                     R21_REAR_BOARD.svg, sw.js, manifest.webmanifest, icons), package docs,
                     requirements.txt, PROJECT_MANIFEST.json, SHA256SUMS.txt

Regenerate after a CASE/ACRYLIC edit (Python 3.13; python -m pip install -r requirements.txt),
from the package root, in this order:
  python -B LAYERS/02_CASE/export_layer_formats.py
  python -B CHECKS/convergence_check.py
  python -B CHECKS/render_review.py
  python -B CHECKS/build_pcb_viewer_data.py   (studio PCB data: pours, sourcing, fab status, gates)
  python -B CHECKS/make_manifest.py      (last: rewrites PROJECT_MANIFEST.json and SHA256SUMS.txt)

Deploying the viewer: publish a bundle, not this folder (the package is ~250 files and
~45 MB; the viewer needs 7 files and ~2.7 MB). From the package root:
  python -B CHECKS/build_viewer_bundle.py <folder outside the package>
writes index.html (CSS inlined), studio.js (scripts and meshes, coordinates packed at
0.01 mm), R21_REAR_BOARD.svg (trimmed), sw.js, manifest and two icons. Upload that folder as
its own site or at its own path. Nothing in the package changes; rebuild the bundle after
any viewer or mesh change. Do not serve it under another PWA's service-worker scope.

Files for the builders (PCB house, 3D print service, sticker printer): from the package root,
  python -B CHECKS/build_builder_packs.py <folder outside the package>
writes STRUTHIO_SLIM4_R26_BUILDER_FILES/ (1_PCB_FABRICATION, 2_3D_PRINTING, 3_ACRYLIC_STICKER,
each with an order README; the sticker folder also holds the two tape die-cuts and the
cover-glass outline) and its zip. Needs KiCad 7.0.x (kicad-cli, and a python3 that
imports pcbnew) besides requirements.txt. The R21 board is plotted from a temporary copy and
its hash is checked before and after. The one package file it writes is CHECKS/R21_FAB_SUMMARY.json
(DRC, BOM coverage, plotted via tenting, which check I4 reads); after it rerun
convergence_check.py, build_pcb_viewer_data.py and make_manifest.py.
The PCB pack orders an engineering prototype (DECISIONS_R26.md #1, #3); R21's electrical
review gates stay open.

CHECKS/R24_BASELINE_AUDIT.* is a frozen comparison. To regenerate it, unzip the R24
package (identity in AI_CHANGE_REPORT_R25.md) and add --baseline <unzipped R24 folder>
to the convergence_check.py command.
