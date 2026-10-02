# STRUTHIO handheld firmware

ESP-IDF 5.5.x app for the Waveshare ESP32-S3-Touch-LCD-3.5B. The game is the
bit-exact C port in `../core` (built as the `struthio` component); this folder
adds the hardware around it. The build manual (`manual/` in the package) walks
through every step below; `STRUTHIO.bat` / `struthio.sh` run them from a menu.

## Build, flash, monitor

    cd handheld/firmware
    idf.py set-target esp32s3                              # once per fresh folder
    idf.py -D STRUTHIO_ART=greybox build flash monitor     # first boot: flat-colour picture
    idf.py -D STRUTHIO_ART=full build flash monitor        # the real art (the default)

`idf.py flash` writes the bootloader, the partition table, the app
(`build/struthio.bin`), the art pack (`../build/assets/struthio.pak`, 8.3 MB,
to `assets` at 0x410000) and the soundtrack (`../build/assets/struthio_music.ima`,
1.9 MB, to `music` at 0xD10000). `idf.py app-flash` writes only the app.

`STRUTHIO_ART=greybox` writes an 8-byte marker to the start of `assets`
instead of the art pack, so even a board that already holds the art shows the
greybox picture; the log says `assets: greybox marker`. `STRUTHIO_ART` is
remembered by the build folder, so switch back with `-D STRUTHIO_ART=full`.
Adding or removing a file in `../build/assets` re-runs the configure step by
itself.

Leave the monitor with `Ctrl + ]`. `Ctrl + T` then `Ctrl + L` starts and stops
a log file in the current folder.

## Tasks

| Task | Core | Rate | Job |
| --- | --- | --- | --- |
| `wings` | 0 | 1 kHz | GPIO17/18 wings + GPIO21/38 DART rocker -> debounce -> input normalizer (`struthio_buttons.c`) |
| `game` | 1 | 60 Hz fixed | normalizer frame -> `st_step()` -> events -> scene builder + HUD model; a frame published every 2nd tick; watchdog |
| `render` | 0 | <= 30 fps | newest frame -> panel renderer, even 16-line bands -> panel as each band finishes; may drop frames |
| `render1` | 1 | with `render` | the odd bands of the same frame (below `game` in priority) |
| `audio` | 0 | 5.33 ms blocks | game events -> the browser's conductor + synth, plus the soundtrack -> ES8311 |

The game clock uses a rational microsecond schedule (exactly 60 ticks/s on
average) and never waits on the panel. Flash writes happen in the render task,
never inside a tick.

## Controls

| Action | Buttons |
| --- | --- |
| Flap left / right | press that wing (flaps at once, no added latency) |
| Steer | hold a wing |
| Straight-up flap | both wings within 100 ms |
| DART | press an end of the DART rocker: GPIO21 darts left, GPIO38 darts right (one dart per press) |
| DART without a rocker (bench) | select DART mode C in service mode: hold both wings 200 ms |
| Restart after GAME OVER | hold both wings together for one second |
| Service mode | hold both wings while powering on |

DART modes, chosen in service mode and saved: `ROCKER ONLY` (default, the
handheld: the wings never dart), `C BOTH-HOLD` (for a bench build with only two wing
switches), and two experimental wing gestures, `A HOLD` and `B TAP-HOLD`. The
rocker darts in every mode. `make -C host_test run` prints how each mode behaves
on recorded play.

## Hard power

The slide switch cuts BAT+, so power can vanish at any moment. NVS is built to
survive that. The firmware writes the high score, the DART mode and the volume
only when they change, never periodically, and reads back every flash write
(`CONFIG_SPI_FLASH_VERIFY_WRITE`).

## Service mode

Hold both wings at power-on. The screen shows the build, the reset reason and
free memory; live wing and rocker states with press counts; the DART mode and
darts fired; the on-device golden replay (the embedded `climb.trace`, 10,011
ticks, every tick's SHA-256 checked); simulation and panel timings; and the
AUDIO / MUSIC / VOL line. LEFT tap: next DART mode. LEFT held 1 s: next volume
level (a chime plays). RIGHT tap: run the checks again. Power-cycle to play.

## Board adapter

`main/board_waveshare_35b.c` and `main/board_pmu.cpp` implement `board.h`,
ported from Waveshare's own ESP-IDF example (Apache-2.0, commit 840daf2): the
I2C bus, the AXP2101 rails and charger (through the vendored XPowersLib, MIT),
the TCA9554 LCD reset, the AXS15231B QSPI panel and the LEDC backlight. Audio is
the ES8311 through espressif/esp_codec_dev at 48 kHz mono. The panel, expander
and codec drivers come from the component registry (`main/idf_component.yml`).

Two board facts shape the code:
- **No row address over QSPI.** Bands must reach the panel top to bottom: the
  two render cores pass a turn back and forth, and the adapter counts any band
  that arrives out of order (`band-order` in the log).
- **The wings share pins with the camera.** GPIO17/18 are the camera's
  VSYNC/HREF, so no camera module may be fitted (`main/board_pins.h`).

## Checks without the board

    make -C host_test run       # button unit tests + DART mode report
