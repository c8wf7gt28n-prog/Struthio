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

The title screen flashes START: tap anywhere, press a wing, Enter, Space or a
controller's Start. START continues a run you left mid-climb; otherwise it
starts a new one.

Controls:

| Action | Touch | Keys |
| --- | --- | --- |
| Flap left / right | tap that wing | ← / → (A / D) |
| Strong vertical flap | tap both wings | ↑ / Space / W |
| DART | slide a wing down | ↓ |
| Pause | — | Esc, or Start on a controller |

Gamepads work as well.

## Forgiveness

Small, invisible helps in the player's favour, after Celeste's and Nintendo's
published practice:

- **Mercy invincibility:** 2.5 s after a respawn, as long as Super Mario Bros.
  after a hit (158 frames).
- **Joust grace:** a rival up to 2.5 px higher only bounces you; it no longer
  knocks you off.
- **Corner correction:** clipping an island's underside by up to 4 px slides
  you round the edge instead of bonking (Celeste).
- **Ring slack:** rings are caught 2 px beyond their drawn radius.
- **Quiet assist:** from the third death since your last ring, one fewer rival
  is in play until you take a ring (after Nintendo's Super Guide and
  Invincibility Leaf).
- **Flap buffer:** a flap pressed up to 8 ticks early is kept and fires as soon
  as it can (already in the input layer).

You start with 11 Joust Marks (lives), the maximum.

## Layout

    index.html             page shell (hero art title, HUD, controller)
    assets/arcade.css      base styles
    assets/arcade-frame.css side rails, HUD skin and the START title
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
- **tower-report**: every island and ring is reachable in flight, at four points of the islands' motion cycles.
- **save**: slots, corruption and restore.
- **tower-sim**: a 12-round bot soak, with the cap, zone, camera, save and determinism rules checked every tick.

Test hooks (`window.__struthio`, URL flags such as `?seed=7`) exist only on a
local server. A published host exposes none.

## Release

    python3 tools/build.py

The build rewrites `sw.js` (the precache list and build id) and
`SHA256SUMS.txt`, then writes `dist/STRUTHIO_ARCADE_<version>.zip`. Deploy
the zip contents, and keep `_headers` (or mirror it) so `sw.js` is never
served from a cache.
