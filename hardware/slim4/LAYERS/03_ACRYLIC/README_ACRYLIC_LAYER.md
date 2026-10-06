# ACRYLIC layer — R1

Clear face film, 0.20 mm assumed, laminated on the front plate (Z 7.65–7.85). Source: the film section of `LAYERS/02_CASE/build_r11.py`; files written by `export_layer_formats.py`.

- Outline identical to CASE R11. No screen cutout: the film is continuous over the lens.
- Cutouts: Ø18.4 at each flap control, 52.4 × 9.4 (r4.6) at the DART relief, six 12.2 × 1.0 vent slots over the speaker grilles. The molded relief rises 0.5 mm through these cutouts with 0.2 mm clearance.
- `ACRYLIC_FACE_FILM_CUTLINE_R1.svg` uses the shared datum (Y down, front view). `ACRYLIC_FACE_FILM_CUTLINE_R1.dxf` is the same front view in Y-up CAD coordinates, layer `CUTLINE`.
- `ACRYLIC_LAYER_R1_CUT_SPEC.json` lists the numbers; check E6 keeps it equal to the geometry.

Planning study only: material, adhesive, kerf/offset and artwork are open (PRODUCTION_GATES.md).
