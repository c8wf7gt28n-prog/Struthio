# AI platform handoff

## Source authority

The project has three independent physical layers. Keep each layer in its own folder and preserve the shared coordinate system: **millimeters; R21 PCB XY; board bottom at Z=0; +Z toward the front.** The R21 PCB file is the locked motherboard baseline. Do not change its footprint positions, nets, outline, or routing while editing the case or acrylic. If a proposed change needs a PCB edit, describe the conflict and request an explicit decision instead of moving the board silently.

| Parent | Main editable source | Neutral interchange | Current scope |
|---|---|---|---|
| PCB | `LAYERS/01_PCB/SLIM4_R21.kicad_pcb` | `SLIM4_R21_PCB_LAYER.json` | R21 board/layout; preserved baseline, engineering review only |
| CASE | `LAYERS/02_CASE/build_r10.py` | `STRUTHIO_CASE_FRONT_R10.step`, `.stl`, `CASE_LAYER_R10_MESH.json` | R10 front shell, screen stack, lens, bezels and caps; no rear/audio/battery housing |
| ACRYLIC | case build source plus `LAYERS/03_ACRYLIC/ACRYLIC_LAYER_R0_CUT_SPEC.json` | STEP, STL, SVG and DXF | clear face film and cutline only; 0.20 mm assumed; print artwork incomplete |

## How to make a change

1. Read this file, `PROJECT_MANIFEST.json`, and `PRODUCTION_GATES.md` first.
2. Edit one parent layer at a time. Keep its source revision, shared origin, and units. Record every changed file and changed dimension in the next revision’s changelog.
3. For CASE geometry, install CadQuery and run `python LAYERS/02_CASE/build_r10.py`, then `python LAYERS/02_CASE/export_layer_formats.py`. These scripts regenerate separate STEP/STL sublayers, acrylic vector cutlines, and the PWA’s split CASE/ACRYLIC mesh data.
4. For PCB edits, use KiCad with the bundled project, local footprint library, and project file. Exported JSON is for inspection/interchange, not a replacement for the native board.
5. Never treat the transparent acrylic film as print art. The SVG/DXF paths describe an unapproved cutting study; confirm material, process tolerance, edge margins, adhesive, optical zone, and supplier conventions before manufacturing.
6. Return the revised source files with a short change report, CAD screenshots or neutral exports, geometry checks, and updated checksums. Do not overwrite this baseline package; create a new revision.

## Interchange files

STEP is the primary CAD exchange for solids; STL is for mesh viewers/printing; SVG/DXF are two-dimensional acrylic cutting references; KiCad remains native for the PCB; JSON supports inspection by tools that cannot open the native application formats. `index.html` opens the integrated browser viewer. The viewer’s CASE and ACRYLIC geometry is loaded from separate `case-layer-data.js` and `acrylic-layer-data.js` files.
