# STRUTHIO Prototype A0 validation report

v0.5, 2026-10-01 (v0.4: 2026-09-28)

## v0.5: completed off-board checks

Run them all with `handheld/run_tests.sh`.

- **Simulation port is bit-exact with STRUTHIO ARCADE 1.8.0.** The C core replays
  five browser-recorded golden traces, 75,144 ticks in all. The frames are
  identical, every tick's SHA-256 of the canonical `{state, events}` is
  identical, and so are the digest chains and the final state digests.

  | Trace | Ticks | Covers |
  | --- | ---: | --- |
  | climb | 10,011 | three round clears, gold ring, jousts, eggs, darts, chords (test shield on) |
  | mortal | 14,143 | real lives: 12 deaths, an extra life, GAME OVER |
  | duel | 20,000 | joust losses, frequent darts and chords |
  | late | 10,990 | rounds 9-11 (8-rival cap, top tiers, short egg timers) |
  | raw | 20,000 | frames straight into the sim: chord-during-cooldown, side-less darts |

- The input normalizer (100 ms chord rewrite of a pending flap, 4-deep flap
  queue, 8-tick flap buffer gated like the browser session) produces the same
  frame as the browser on every tick of the four button traces.
- Mutation check: changing gravity, ring slack, an AI branch, the egg-landing
  margin or the chord window each fails the replay within a few hundred ticks.
  Not caught: the straight-up joust threshold 24 -> 25 subpixels (no trace hits
  that boundary).
- Host timing: 0.9-2.0 µs per simulation tick; about 60 µs with the per-tick
  SHA-256 (x86-64; the ESP32-S3 figure comes from service mode).
- Rulebook constants are generated from `rules.mjs` and statically asserted
  in the core.
- Port authority re-pointed from 1.6.0 to 1.8.0. Of the authority files, only
  `step.mjs` changed (1.7.0: rising straight up wins a joust).
- Wing-button layer unit-tested: debounce, raw-edge chord timing, chord in and
  across frames, DART trials A/B/C, service-mode hold.
- DART trials measured on the bots' millisecond press timelines (unwanted darts
  per minute): **A HOLD 69-78, B TAP-HOLD 40-49, C BOTH-HOLD 0.3-2.0**. A and B
  collide with steering and with flapping while steering. C is the proposed
  default, pending a human thumb test.
- Greybox renderer and 1.25x RGB565 presenter render every game state on the
  host (`renders/a0_greybox_sheet.png`).
- Firmware sources type-check (`-Wall -Wextra -Werror`) against a host shim of
  the ESP-IDF headers.

## v0.5 correction to the v0.4 input mapper

The v0.4 mapper allowed one queued flap. Its chord required the first wing to
still be held, and it had no flap buffer. The browser authority differs on all
three points, and v0.5 ports the browser normalizer exactly:

- a 4-deep flap queue;
- the chord rewrites the pending flap, or else queues a STRAIGHT chord;
- the chord depends only on press times within 100 ms;
- an 8-tick buffer for a flap that cannot fire yet.

## Deliberately not claimed yet

These need the physical board, switches, battery and speaker, or the real toolchain:

- `idf.py build` with ESP-IDF (toolchain download blocked here) and flashing.
- Waveshare panel / power / audio init (`board_waveshare_35b.c` is a stub).
- On-device golden replay result and ESP32-S3 µs per tick (service mode measures it).
- AXS15231B QSPI throughput; whether 40-line bands or full-frame writes work.
- GPIO17/18 conflict test with display, audio and storage active.
- Physical board fit, glass clearance, button travel, switch feel.
- DART trial C under a real thumb.
- USB-C extension, audio loudness, battery runtime and thermals.

A0 passes only when: **POWER ON -> STRUTHIO STARTS -> A PLAYABLE ROUND IS COMPLETED USING ONLY THE TWO PHYSICAL BUTTONS.**

---

## v0.4 record (2026-09-28)

- Portable C two-button input mapper compiled with `-std=c11 -Wall -Wextra -Werror -O2` and host-tested
  (superseded in v0.5 by `firmware/main/struthio_buttons.c` + `core/struthio_input.c`).
- Front shell, rear shell, LEFT cap and RIGHT cap STLs regenerated from the OpenSCAD source.
  After vertex welding, all four are watertight, single connected solids.
- Rear internal posts, pads and rails fused into the rear wall; front speaker slots shortened.
