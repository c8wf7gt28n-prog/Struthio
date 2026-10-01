# STRUTHIO ESP32-S3 Prototype A0 firmware

ESP-IDF 5.5+ app for the Waveshare ESP32-S3-Touch-LCD-3.5B. The game is the
bit-exact C port in `../core` (built as the `struthio` component); this folder
adds the hardware around it.

## Tasks

| Task | Core | Rate | Job |
| --- | --- | --- | --- |
| `wings` | 0 | 1 kHz | GPIO17/18 -> debounce -> input normalizer (`struthio_buttons.c`) |
| `game` | 1 | 60 Hz fixed | normalizer frame -> `st_step()` -> events -> scene builder + HUD model (every tick, as the browser); a frame published every 2nd tick; watchdog |
| `render` | 0 | <= 30 fps | newest frame -> panel renderer, even 16-line bands -> panel as each band finishes; may drop frames |
| `render1` | 1 | with `render` | the odd bands of the same frame (below `game` in priority) |

The picture is the browser's: `render/struthio_panel.c` draws the quads the
scene builder produces (the same lists the browser hands WebGPU) with
textures from the asset pack, which is mapped from the `assets` flash
partition. Frames are triple-buffered in PSRAM. Without an asset pack in
flash the firmware falls back to the greybox renderer.

The game clock uses a rational microsecond schedule (exactly 60 ticks/s on
average) and never waits on the panel. Flash writes (high score) happen in the
render task, never inside a tick. GAME OVER shows the browser's result
screen; both wings held together start a new run after one second, so a stray
flap from the last fight cannot skip it.

## Controls

| Action | Buttons |
| --- | --- |
| Flap left / right | press that wing (flaps at once, no added latency) |
| Steer | hold a wing |
| Straight-up flap | both wings within 100 ms |
| DART | trial C (default): hold both wings 200 ms, dives toward facing |
| Service mode | hold both wings while powering on |

DART trials A (hold one wing 230 ms) and B (tap then hold) are kept for the
thumb test. On the golden bots' press timelines they fire 40-78 unwanted darts
a minute, because steering is holding a wing and a flap while steering is a
quick re-press. Trial C fires 0.3-2 a minute. Run
`make -C host_test run` for the report.

## Service mode

Hold both wings at power-on:

- build, reset reason, free PSRAM / internal RAM
- live wing states, press counts, darts fired, active DART trial
- **on-device golden replay:** the embedded `climb.trace` (10,011 ticks) is run
  through the core, with every tick's SHA-256 checked against the browser. It
  shows PASS/FAIL, simulation µs/tick, and µs/tick including the digest. Both
  timings include a one-tick yield every 256 ticks.
- panel benchmark: ms per full 320x480 present

LEFT tap cycles the DART trial (saved in NVS). RIGHT tap re-runs the checks.
Power-cycle to play.

## Build

    make -C handheld/host pak          # build/assets/struthio.pak (needs build/reference, see docs)
    cd handheld/firmware
    idf.py set-target esp32s3
    idf.py build flash monitor         # flashes the app and the asset pack

Not yet built with the real toolchain: this environment cannot download it.
`make -C host_test compile` type-checks every source against `host_shim/`, a
stand-in for the IDF headers. That catches mistakes in this code, not
mismatches with the real SDK.

## Board adapter (the one file to finish on the bench)

`main/board_waveshare_35b.c` implements `board.h`. Panel (AXS15231B over QSPI),
power (AXP2101, backlight) and audio (ES8311 + NS4150B) init are deliberately
not written from memory. Copy them from Waveshare's example for the exact board
revision, then set `g_panel`. Until then the firmware boots headless: the game
runs at 60 Hz and logs over USB, and service mode still runs the golden replay.

## Host tests

    make -C host_test run       # button unit tests + DART trial report
    make -C host_test compile   # type-check the firmware against host_shim
