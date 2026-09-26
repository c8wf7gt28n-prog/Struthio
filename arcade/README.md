# STRUTHIO · ARCADE

A standalone, arcade-only fork of STRUTHIO. You climb one tower of floating
islands, eight screens tall, from the grid floor to the moon. Take the six
rings in any order, then take the gold ring at the moon: it destroys every
rival and starts the next, harder round. The ring placements run through ten
fixed sets, then repeat.

This fork has no console, cartridges, episodes, story, bosses, developer
menus or relay code. It shares no saves with the console build (its save
namespace is `struthio.arcade.v1`).

## Play

Serve the folder over https (or `localhost`) and open `index.html`. You need
a WebGPU browser: current Chrome or Edge, or Safari 26 or later. Once it has
loaded, the game installs as an app and plays offline.

    python3 -m http.server 8000     # then open http://localhost:8000/

Controls:

| Action | Touch | Keys |
| --- | --- | --- |
| Flap left / right | tap that wing | ← / → (A / D) |
| Strong vertical flap | tap both wings | ↑ / Space / W |
| DART | slide a wing down | ↓ |
| Pause | — | Esc, or Start on a controller |

Gamepads work as well.

## Layout

    index.html             page shell (hero art title, HUD, controller)
    assets/arcade.css      all styles
    assets/art, audio      art plates, island sheet, sprites, music loop
    src/core               sha256, canonical JSON digests, rng, fixed-point maths
    src/sim                deterministic 60 Hz tower sim (state, step, ai, physics, world, tower data)
    src/data/rules.mjs     the rulebook: physics, scoring, palette, audio, font
    src/save               A/B checkpoint slots with schema and checksum validation
    src/render             WebGPU renderer, atlas, scene, tower camera
    src/audio              synth worklet, SFX conductor, music loop
    src/ui, src/input      HUD, touch controller, PWA, keyboard and gamepad
    src/app                boot, session loop, art loading
    tests                  sim test suite
    tools/build.py         service worker, checksums, release zip

## Tests

    node tests/run-all.mjs

The suite covers:

- **tower-rings**: static ring placement rules.
- **tower-report**: every island and ring is reachable in flight.
- **save**: slots, corruption and restore.
- **parity**: identical to the console arcade it was forked from (skipped when the console build isn't present).
- **tower-sim**: a 12-round bot soak, with the cap, zone, camera, save and determinism rules checked every tick.

Test hooks (`window.__struthio`, URL flags such as `?seed=7`) exist only on a
local server. A published host exposes none.

## Release

    python3 tools/build.py

The build rewrites `sw.js` (the precache list and build id) and
`SHA256SUMS.txt`, then writes `dist/STRUTHIO_ARCADE_<version>.zip`. Deploy
the zip contents, and keep `_headers` (or mirror it) so `sw.js` is never
served from a cache.
