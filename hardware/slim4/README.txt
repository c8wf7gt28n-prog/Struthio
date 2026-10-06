STRUTHIO SLIM4 — R24 THREE-LAYER AI HANDOFF

Open index.html for the integrated local viewer. Use the LAYERS button to toggle CASE, PCB, and ACRYLIC independently and switch their implemented sublayers.

The ZIP contains three standalone parent layers in LAYERS/:
  01_PCB — unchanged native KiCad R21 project, local footprints, and JSON inspection projection.
  02_CASE — R10 front/screen/control STEP and STL plus reproducible CadQuery sources and fit gates.
  03_ACRYLIC — separate clear face film STEP/STL, SVG/DXF cutline and machine-readable specification/mesh.

Shared CAD datum: millimeters, R21 PCB XY, board bottom at Z=0, +Z toward the front. The acrylic thickness is assumed 0.20 mm. This package is an engineering/debug handoff, not manufacturing approval. Rear housing, speakers/acoustic chambers, battery enclosure, final FPC routing, and final sticker artwork remain open.

See AI_HANDOFF.md, PROJECT_MANIFEST.json and PRODUCTION_GATES.md before edits. `REFERENCES/R10_CONTEXT/` is explicitly non-authority comparison data.
