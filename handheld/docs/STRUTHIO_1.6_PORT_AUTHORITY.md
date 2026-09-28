# STRUTHIO 1.6.0 port authority snapshot

These hashes identify the browser source files used to start the ESP port.

- ZIP SHA-256: `2a845b94416d678602f9c6a4e5ed167fc18eb2f882d8734c1eb27f621a7d62ee`

- `src/data/rules.mjs`: `6484d5dcfded4db34d4bbee7229252ed620afeb0efb4c5b0882d6d6c62108d89`
- `src/input/input.mjs`: `26f7ca0218e33b83c6099930c278e51fc13845f01e7227aedb67cf8a6c76159f`
- `src/sim/step.mjs`: `ef5171d6aa532ca6a34f49d56fbe80361a020f95efb3bce8de663d5b894729c4`
- `src/sim/physics.mjs`: `392bbeecc6c5c00b82b77e9f7dc2f401497a5735df3e1f26c276395ce791f497`
- `src/sim/ai.mjs`: `498250797726c7eb21f0204e4a10f9bc48df813704847e80e7bb1bb2677db84e`
- `src/sim/state.mjs`: `4601ba656d9c07302f46256cd0ed5f9125d6b69ec04925ab6ebb7abca7f0d727`
- `src/sim/tower.mjs`: `ce06c3f5fad811713784e3fbd80505c282f10e3d9adbec5efd14ba3b49791eb8`
- `src/sim/world.mjs`: `09bf0526c5642a210109b39b805916221a2670434a6978bc4735232a07c91de5`

Input authority confirmed from 1.6.0:
- chord window: 100 ms
- logical size: 256 x 384
- simulation: 60 Hz
- first wing press may flap immediately; opposite wing inside chord window corrects to STRAIGHT
- current touchscreen DART is a directional gesture; A0 physical-port experiment begins with 230 ms hold-to-DART.
