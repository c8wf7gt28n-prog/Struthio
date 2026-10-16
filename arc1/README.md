<p align="center"><img src="docs/assets/arc1-logo.jpg" alt="ARC-1 Adaptive RISC-V Console" width="640"></p>

# ARC-1 host SDK (M0–M1)

This is the first vertical slice of the agent-native SDK described in
*ARC1-SDK-ER-002 Engineering Requirements v0.2*. It contains:

- a portable `arc1` CLI
- a C11 game API
- a deterministic host simulator
- the `hello_arc1` demo, with golden-frame and replay tests
- JSON Schemas and validators for pass records, hardware manifests and game
  packages, each with negative fixtures

**What this is not:** it is not evidence that any ARC-1 hardware works. There
is no board, no target cross-compiler, no firmware and no RTL here. Results
are labelled `HOST_SIM` or lower, and device commands answer `NOT_AVAILABLE`.

Coding agents: read [AGENTS.md](AGENTS.md).

## Hardware facts

`./arc1 hw inspect` reports the board as the R10 engineering handoff describes
it: F133-B, D213ECV, LFE5U-45F and LFE5U-12F with four separate memory pools,
a 64 MiB central NOR, an ADV7513 HDMI transmitter with F133 I2S audio, and a
USB2514B hub for two controller ports and the top cartridge port. Every fact
cites an unmodified R10 file in `hardware/sources/r10/` by SHA-256, and the
tool fails if a cited file changes. The board is on **fabrication HOLD**:
schematic and first placement only, not routed, not built, nothing measured.

## Prerequisites

- Python 3.9 or newer, standard library only. Nothing is installed with pip.
- A C11 compiler on `PATH` as `cc`, `gcc` or `clang`. Tested versions are
  listed in `tools/lock/toolchain.lock.json`.
- git (optional). It enables the base-commit and protected-file checks in
  `arc1 pass validate`.

Linux and macOS are the targets. On Windows, run the CLI as `python arc1 …`
from a shell where a C compiler is on `PATH`. That setup has not been tested.

## Clean build (copy and paste)

```sh
git clone https://github.com/c8wf7gt28n-prog/Struthio.git && cd Struthio/arc1
./arc1 doctor
./arc1 build examples/hello_arc1
./arc1 sim examples/hello_arc1 --replay tests/replays/steer.replay --dump 0,60,119
./arc1 test examples/hello_arc1
./arc1 pass validate passes/ARC1-PASS-0001
./arc1 pass validate passes/ARC1-PASS-0002
python3 tests/run_tests.py
```

Each command exits 0 on success. `sim` writes PPM frames to
`examples/hello_arc1/build/sim/`. `doctor` warns that no physical board
exists, which is expected.

## Make a game

```sh
./arc1 new mygame --dir /tmp
./arc1 build /tmp/mygame && ./arc1 test /tmp/mygame
```

Edit `src/main.c`, then rebuild. `test` fails with the first divergent frame
until you record new goldens with `./arc1 test /tmp/mygame --update-golden`.
Re-recording a golden is a review-sensitive change.

## Reference

- [docs/API.md](docs/API.md): the `arc1/game.h` contract.
- [docs/CLI.md](docs/CLI.md): commands, exit codes and the result format.
- [docs/TRACEABILITY.md](docs/TRACEABILITY.md): requirement status.
- [docs/MIGRATION.md](docs/MIGRATION.md): schema changes between versions.
- [hardware/sources/r10/PROVENANCE.md](hardware/sources/r10/PROVENANCE.md):
  where the hardware facts come from.
- [passes/ARC1-PASS-0002/HANDOFF.md](passes/ARC1-PASS-0002/HANDOFF.md): the
  latest handoff.
