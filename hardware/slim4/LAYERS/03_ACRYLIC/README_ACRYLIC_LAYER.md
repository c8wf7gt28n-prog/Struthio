# ACRYLIC layer — R2

Clear face film laminated on the front plate (Z 7.65–7.85): 0.175 mm clear optical PET with a hard-coat face + 0.025 mm optically clear adhesive = 0.20 mm. Unprinted for the prototype (`DECISIONS_R26.md` #9). Source: the film section of `LAYERS/02_CASE/build_r12.py`; every file here is written by `export_layer_formats.py`.

- Outline: the CASE R12 outline set in 0.20 mm all round, so die-cut tolerance cannot leave film overhanging the case edge. No screen cutout: the film is continuous over the cover glass.
- Cutouts: Ø18.4 at each flap control, 52.4 × 9.4 (r4.6) at the DART relief, one 12.2 × 4.8 (r0.3) vent window over each speaker grille. The molded relief rises 0.5 mm through the control cutouts with 0.2 mm clearance. Narrowest cut 4.8 mm.

| File | Content |
|---|---|
| `STRUTHIO_ACRYLIC_FACE_FILM_R2.step` / `.stl` | film solid (STEP for CAD, STL for mesh viewers) |
| `ACRYLIC_FACE_FILM_CUTLINE_R2.svg` | cutline in the shared datum (Y down, front view; canvas = case outline) |
| `ACRYLIC_FACE_FILM_CUTLINE_R2.dxf` | the same front view in Y-up CAD coordinates, layer `CUTLINE` |
| `ACRYLIC_LAYER_R2_CUT_SPEC.json` | generated cut numbers and stack; check E6 compares every field with the geometry |
| `ACRYLIC_LAYER_R2_MESH.json` | viewer mesh (same content as `acrylic-layer-data.js` at the package root) |

The sticker-printer pack (`CHECKS/build_builder_packs.py`) adds a CutContour PDF, a 1:1 check drawing and the two tape die-cuts. Supplier confirmation of stock and tolerance is open (PRODUCTION_GATES.md item 13).
