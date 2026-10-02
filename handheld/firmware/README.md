# STRUTHIO ESP32-S3 Prototype A0 firmware

ESP-IDF 5.5+ app for the Waveshare ESP32-S3-Touch-LCD-3.5B. The game is the
bit-exact C port in `../core` (built as the `struthio` component); this folder
adds the hardware around it.

## Tasks

| Task | Core | Rate | Job |
| --- | --- | --- | --- |
| `wings` | 0 | 1 kHz | GPIO17/18 wings + GPIO21/38 DART rocker -> debounce -> input normalizer (`struthio_buttons.c`) |
| `game` | 1 | 60 Hz fixed | normalizer frame -> `st_step()` -> events -> scene builder + HUD model (every tick, as the browser); a frame published every 2nd tick; watchdog |
| `render` | 0 | <= 30 fps | newest frame -> panel renderer, even 16-line bands -> panel as each band finishes; may drop frames |
| `render1` | 1 | with `render` | the odd bands of the same frame (below `game` in priority) |
| `audio` | 0 | 5.33 ms blocks | game events -> the browser's conductor + synth, plus the soundtrack -> ES8311 (`../audio`, `docs/AUDIO_PORT.md`) |

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
| DART (A1.5) | press an end of the DART rocker: GPIO21 darts left, GPIO38 darts right (one dart per press) |
| DART (A0, no rocker) | trial C (default): hold both wings 200 ms, dives toward facing. On A1.5 set the DART mode to ROCKER ONLY in service mode |
| Service mode | hold both wings while powering on |
| Volume (in service mode) | hold LEFT 1 s: next of 5 levels (0 = off), saved |

DART trials A (hold one wing 230 ms) and B (tap then hold) are kept for the
thumb test. On the golden bots' press timelines they fire 40-78 unwanted darts
a minute, because steering is holding a wing and a flap while steering is a
quick re-press. Trial C fires 0.3-2 a minute. Run
`make -C host_test run` for the report.

## Hard power (A1.5)

The slide switch cuts BAT+, so power can vanish at any moment. NVS is built to
survive that (a value being written at that instant can be lost, the store
recovers). The firmware writes high score, DART mode and volume only when they
change, never periodically, and reads back every flash write
(`CONFIG_SPI_FLASH_VERIFY_WRITE`, `CONFIG_SPI_FLASH_LOG_FAILED_WRITE`).

## Service mode

Hold both wings at power-on:

- build, reset reason, free PSRAM / internal RAM
- live wing states, press counts, darts fired, active DART trial
- **on-device golden replay:** the embedded `climb.trace` (10,011 ticks) is run
  through the core, with every tick's SHA-256 checked against the browser. It
  shows PASS/FAIL, simulation µs/tick, and µs/tick including the digest. Both
  timings include a one-tick yield every 256 ticks.
- panel benchmark: ms per full 320x480 present

LEFT tap cycles the DART trial (saved in NVS). LEFT held 1 s steps the volume
(saved; a chime plays). RIGHT tap re-runs the checks; the round-clear sting
plays when they finish. The screen shows AUDIO OK / NO CODEC, MUSIC OK / NONE
and the volume.
Power-cycle to play.

## Build

    make -C handheld/host pak          # build/assets/struthio.pak (needs build/reference, see docs)
    make -C handheld/host music        # build/assets/struthio_music.ima (needs ffmpeg and the arcade MP3)
    cd handheld/firmware
    idf.py set-target esp32s3
    idf.py build flash monitor         # flashes the app, the asset pack and the soundtrack

Not yet built with the real toolchain: this environment cannot download it.
`make -C host_test compile` type-checks every source against `host_shim/`, a
stand-in for the IDF headers. That catches mistakes in this code, not
mismatches with the real SDK.

## Board adapter

`main/board_waveshare_35b.c` and `main/board_pmu.cpp` implement `board.h`. They are ported, not written from
memory, from Waveshare's own ESP-IDF example (Apache-2.0, commit 840daf2). That covers:
- the I2C bus;
- the AXP2101 rails, charger and power key (vendor values, through the vendored XPowersLib, MIT);
- the TCA9554 LCD reset pulse;
- the AXS15231B QSPI panel with the vendor's init commands;
- the LEDC backlight.

Audio: the ES8311 through espressif/esp_codec_dev, as the vendor's `bsp_es8311.c` (48 kHz mono, playback only). The panel and codec drivers come from the component registry (`main/idf_component.yml`).

Two board facts shape the code:
- **No row address over QSPI.** A band at y 0 starts a frame and every other band continues where the last one ended. So bands must reach the panel top to bottom: the two render cores pass a turn back and forth (`band_out` in main.c), and the adapter counts any band that arrives out of order. `host/band_order_test` shows the earlier scheme would have misplaced most bands.
- **The wings share pins with the camera.** GPIO17/18 are the camera's VSYNC/HREF, so no camera module may be fitted (`main/board_pins.h`).

## Checks without the board

    make -C host_test run       # button unit tests + DART trial report
    make -C host_test compile   # hardware-independent sources against host_shim
    idf_check/idf_check.sh      # every source against the REAL ESP-IDF 5.5.5 headers + board drivers

`idf_check` fetches ESP-IDF and the driver components by git (pinned). It generates the real `sdkconfig.h` with Espressif's kconfgen from `sdkconfig.defaults`, then compiles everything with `-Wall -Wextra -Werror` for a 32-bit newlib target. It catches wrong struct fields, signatures and missing functions. It is still not `idf.py build`: nothing is generated for Xtensa or linked.


