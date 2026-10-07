STRUTHIO SLIM4 — R25 CONVERGED THREE-LAYER HANDOFF (clean re-issue)

R25 makes the three parent layers agree with each other in CAD:

  01_PCB     R21, unchanged byte for byte (locked baseline).
  02_CASE    R11 — complete enclosure built around R21: front shell, rear shell,
             flap caps, DART rocker, power plunger, screen stack, battery, speakers,
             FPC and harness routes.
  03_ACRYLIC R1  — clear face film cut to the R11 face (STEP/STL, SVG/DXF, cut spec).

CHECKS/convergence_check.py tests every interface between the layers (board vs walls,
LCD vs shell, caps vs switches, film vs relief, parts vs parts at rest and pressed,
supports and stop legs vs pads, speakers, USB-C, battery). Result for this package:

  CONVERGED — 71 PASS · 0 FAIL · 13 GATE · 3 INFO   (CHECKS/R25_CONVERGENCE_REPORT.md)
  The R24 package, audited on the same interfaces: 17 FAIL · 1 PASS (CHECKS/R24_BASELINE_AUDIT.md).

A GATE is an item the CAD agrees on but that still needs a physical sample, supplier
drawing or test (switch tolerance coupon, HOTHMI drawing, FPC extension, film stock,
cell choice, via tenting, thin ledges, acoustic and drop tests). This is an
engineering/debug handoff, not a fabrication release.

Shared CAD datum (unchanged): millimetres, R21 PCB XY (Y down), board bottom at Z=0,
+Z toward the front. Body thickness 13.55 mm (15.05 mm over the caps).

This clean re-issue replaces the first R25 zip. CASE R11 and ACRYLIC R1 geometry is
unchanged; documents, checks, viewer and references were corrected (CHANGELOG.md).

Start with:
  index.html                          integrated viewer (LAYERS: CASE, PCB, ACRYLIC sublayers)
  CHECKS/R25_CONVERGENCE_REPORT.md    what was checked and what is still open
  CHECKS/renders/                     cross-sections and shaded views from the B-rep
  AI_CHANGE_REPORT_R25.md             what changed from R24 and why
  ASSEMBLY/ASSEMBLY_SEQUENCE.md       build order
  PRODUCTION_GATES.md                 open gates before any release

Package layout:
  LAYERS/01_PCB      locked R21 KiCad board, project, footprints, PCB interchange JSON (authority)
  LAYERS/02_CASE     CASE R11 source (build_r11.py, export_layer_formats.py) and its exports;
                     the same source also builds the ACRYLIC film
  LAYERS/03_ACRYLIC  film R1 outputs: STEP, STL, SVG, DXF, cut spec, mesh
  ASSEMBLY/          all three layers in one STEP, and the build order
  CHECKS/            convergence checker and its reports, renderer and renders,
                     component height table, manifest/checksum generator, viewer
                     deploy-bundle builder, builder-pack generator
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
writes STRUTHIO_SLIM4_R25_BUILDER_FILES/ (1_PCB_FABRICATION, 2_3D_PRINTING, 3_ACRYLIC_STICKER,
each with an order README) and its zip. Needs KiCad 7.0.x (kicad-cli, and a python3 that
imports pcbnew) besides requirements.txt. The R21 board is plotted from a temporary copy and
its hash is checked before and after; nothing in the package changes. R21 remains an
engineering-review board: the PCB pack is labelled prototype only.

CHECKS/R24_BASELINE_AUDIT.* is a frozen comparison. To regenerate it, unzip the R24
package (identity in AI_CHANGE_REPORT_R25.md) and add --baseline <unzipped R24 folder>
to the convergence_check.py command.
