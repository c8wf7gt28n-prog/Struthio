# CASE layer — R12

Editable source: `build_r12.py` (CadQuery 2.8 + shapely; pinned versions in `requirements.txt` at the package root). Most dimensions are in the `P` dictionary at the top; the support/clamp post positions, the R10 silhouette control points and the FPC/harness route geometry are constants further down. The same file builds the ACRYLIC film. `export_layer_formats.py` writes (plus the ACRYLIC files in `LAYERS/03_ACRYLIC/` and `ASSEMBLY/STRUTHIO_SLIM4_R26_ASSEMBLY.step`):

| File | Content |
|---|---|
| `STRUTHIO_CASE_R12.step` / `.stl` | all CASE parts (STL omits the route reserves) |
| `CASE_FRONT_SHELL_R12.step` / `.stl` | plate, molded relief, lap skirt (0.10 mm radial clearance), DART pivot bosses, front clamp posts |
| `CASE_REAR_SHELL_R12.step` / `.stl` | floor, walls, lap lip with 0.10 mm tape seat, speaker chambers and ledges, board supports, USB-C relief, service holes |
| `CASE_CONTROLS_R12.step` / `.stl` | two flap caps, DART rocker, power plunger |
| `CASE_SCREEN_STACK_R12.step` | LCD module envelope, 0.10 mm display tape frame and 0.70 mm cover glass |
| `CASE_INTERNALS_R12.step` | cell, foam pad, speakers, gaskets, lap tape ring, FPC and harness route reserves |
| `CASE_LAYER_R12_MESH.json` | viewer mesh (also `case-layer-data.js` at the package root) |
| `R12_FIT_CHECKS.json` | Z stack, key positions and the full parameter set |

R12 = R11 plus the R26 decisions (`DECISIONS_R26.md` #6–#8). The cross-layer checks live in `CHECKS/`. R12 is a converged CAD design for the EVT prototype, not a tooling release.
