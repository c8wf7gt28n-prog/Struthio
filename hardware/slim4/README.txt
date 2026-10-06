STRUTHIO SLIM4 — R25 CONVERGED THREE-LAYER HANDOFF

R25 makes the three parent layers agree with each other in CAD:

  01_PCB     R21, unchanged byte for byte (locked baseline).
  02_CASE    R11 — complete enclosure built around R21: front shell, rear shell,
             flap caps, DART rocker, power plunger, screen stack, battery, speakers,
             FPC and harness routes.
  03_ACRYLIC R1  — clear face film cut to the R11 face (STEP/STL, SVG/DXF, cut spec).

CHECKS/convergence_check.py tests every interface between the layers (board vs walls,
LCD vs shell, caps vs switches, film vs relief, parts vs parts at rest and pressed,
supports vs pads, speakers, USB-C, battery). Result for this package:

  CONVERGED — 69 PASS · 0 FAIL · 12 GATE · 3 INFO   (CHECKS/R25_CONVERGENCE_REPORT.md)
  The R24 package scores 17 FAIL on the same interfaces (CHECKS/R24_BASELINE_AUDIT.md).

A GATE is an item the CAD agrees on but that still needs a physical sample, supplier
drawing or test (switch tolerance coupon, HOTHMI drawing, FPC extension, film stock,
cell choice, acoustic and drop tests). This is an engineering/debug handoff, not a
fabrication release.

Shared CAD datum (unchanged): millimetres, R21 PCB XY (Y down), board bottom at Z=0,
+Z toward the front. Body thickness 13.55 mm (15.05 mm over the caps).

Start with:
  index.html                          integrated viewer (LAYERS: CASE, PCB, ACRYLIC sublayers)
  CHECKS/R25_CONVERGENCE_REPORT.md    what was checked and what is still open
  CHECKS/renders/                     cross-sections and shaded views from the B-rep
  AI_CHANGE_REPORT_R25.md             what changed from R24 and why
  ASSEMBLY/ASSEMBLY_SEQUENCE.md       build order
  PRODUCTION_GATES.md                 open gates before any release

Regenerate after a CASE/ACRYLIC edit (CadQuery 2.8, shapely):
  python LAYERS/02_CASE/export_layer_formats.py
  python CHECKS/convergence_check.py
  python CHECKS/render_review.py
