# CASE layer — R11

Editable source: `build_r11.py` (CadQuery 2.8 + shapely). Every dimension is in the `P` dictionary at the top. `export_layer_formats.py` writes:

| File | Content |
|---|---|
| `STRUTHIO_CASE_R11.step` / `.stl` | all CASE parts (STL omits the route reserves) |
| `CASE_FRONT_SHELL_R11.step` / `.stl` | plate, molded relief, lap skirt, DART pivot bosses, front clamp posts |
| `CASE_REAR_SHELL_R11.step` / `.stl` | floor, walls, lap lip, speaker chambers and ledges, board supports, USB-C relief, service holes |
| `CASE_CONTROLS_R11.step` / `.stl` | two flap caps, DART rocker, power plunger |
| `CASE_SCREEN_STACK_R11.step` | LCD module envelope and protective lens |
| `CASE_INTERNALS_R11.step` | cell, foam pad, speakers, gaskets, FPC and harness route reserves |
| `CASE_LAYER_R11_MESH.json` | viewer mesh (also `case-layer-data.js` at the package root) |
| `R11_FIT_CHECKS.json` | Z stack, key positions and the full parameter set |

The cross-layer checks live in `CHECKS/`. R11 is a converged CAD candidate, not a tooling release.
