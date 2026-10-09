# STRUTHIO SLIM4 platform firmware — R10, for PCB R26 (and R23-R25: same pins)

ESP-IDF project for the SLIM4 main board (`hardware/slim4/LAYERS/01_PCB/`, PCB R26; R24 changed the power layout, R25 the DSI routing and plane shapes and R26 the DSI routing again (coupled pairs) only, so every pin and part the firmware uses is as on R23, and the boot log still names R23). Its job is to bring the board up and give games a hardware-independent API; it is not a game.

## What it drives

| Hardware (R23) | Firmware |
|---|---|
| ESP32-P4NRW32X, chip revision v3, 32 MiB PSRAM in package; W25Q512JV 64 MiB flash | `sdkconfig.defaults`: minimum revision v3.0, 40 MHz crystal, hex PSRAM at 200 MHz, 64 MiB flash, A/B + recovery partitions (`partitions.csv`) |
| Display on J1: Crystalfontz CFAF7201280A0-050TN (5 in 720 × 1280 IPS, ILI9881C), 2-lane MIPI-DSI | `slim4_bsp`: P4 LDO channel 3 at 2.5 V for the D-PHY; 2-lane DSI at 1 Gbit/s; `espressif/esp_lcd_ili9881c` with the Crystalfontz init sequence (`slim4_panel_cfaf.c`); 78 MHz pixel clock, 59 Hz, RGB565; reset through the board's Q1 gate (GPIO10 high = reset) |
| Backlight: TPS61165, 74 mA full scale (R309 2.7 Ω), CTRL on GPIO9 | LEDC PWM at 20 kHz (TI's 6.5–100 kHz range), 12-bit; 45 % after the first frame; off before reset and deep sleep; capped at 15 % on USB below 1 A unless a qualified cell can supplement (the power budget, `docs/FIRST_BOOT.md`) |
| Controls: SW1–SW4 on GPIO1–4 (10 k pull-ups, active low); power button SW5 on GPIO0 | debounced inputs, edge logs, deep-sleep wake on GPIO0 |
| Audio: two MAX98357A on one I2S stream (GPIO5 BCLK, 6 LRCLK, 7 DOUT), enable on GPIO8; speakers on J4 (left) and J5 (right) | stereo 16-bit Philips I2S, no MCLK; amplifiers enabled only while sound plays; muted (held in shutdown) while the USB backlight cap is on, since a 500 mA source has no budget left for audio |
| Charger BQ24074 (CHG GPIO11, PGOOD GPIO44, EN1/EN2 GPIO13/46), USB-C TUSB320 (GPIO43/17), battery ADC GPIO16 (× 133/33) | `slim4_power.c`: battery voltage, USB-C advertisement, charger input limit, low-battery switch-off (2 s below 3.3 V, whatever the button does), die-temperature charge suspend (only with a qualified cell above 3.6 V), reversed/shorted-pack warning; only a calibrated battery reading drives a decision (uncalibrated: shown as `battery_approx`, treated as no reading) |
| USB-C data to USB-Serial-JTAG (GPIO24/25) | flashing, JTAG and every app log line over the one cable (UART0 primary console, USB-Serial-JTAG secondary output, ESP-IDF's P4 default; UART0's pins reach nothing on the board) |

`tools/check_pinmap.py` checks every `SLIM4_GPIO_*` in `components/slim4_bsp/include/slim4_pins.h` against the net on the matching U1 pad of the R26 board, through the ESP32-P4 pin table. The pad nets ship with the firmware (`tools/u1_pad_nets.json`, taken from `SLIM4_R26_PCB_LAYER.json`), so the check runs from this folder alone; inside the repository it also checks that table against the board export. Run it after any board or pin change: `--board <export.json>` checks against another board export, `--write-table <export.json>` refreshes the table.

## Build and flash

ESP-IDF **v6.1**, target `esp32p4`:

```sh
. $HOME/esp/esp-idf/export.sh
idf.py set-target esp32p4      # once
idf.py build
idf.py -p <port> flash monitor
```

The first flash of a new board: hold BOOT (SW7), tap RESET (SW6), release BOOT, then flash. After that `idf.py flash` resets the chip itself over USB-Serial-JTAG. `dependencies.lock` pins the managed components (`esp_lcd_ili9881c`).

This tree builds cleanly with ESP-IDF v6.1 (0 warnings) from `sdkconfig.defaults` alone. It has not run on hardware yet: the first boards are not built. `docs/FIRST_BOOT.md` lists what the first boot should show and what to check.

### Host test of the power policy

`sh tests/host/run.sh` compiles `components/slim4_bsp/slim4_power.c` unchanged against small stand-ins for the ESP-IDF calls (`tests/host/sdk/`) with any C compiler, and runs 42 cases: the 500 mA USB cap and what may lift it, the audio mute that goes with it, uncalibrated battery readings, reversed or shorted pack, low-battery switch-off with the button released or held and with a transient dip, failed battery readings, the over-temperature charge suspend and every way out of it, and the power button. It checks decisions, not analog behaviour.

### Emulator

Espressif's esp-emu (beta) runs the merged image: `esp-emu --chip esp32p4 --firmware merged.bin --psram-size 32M --timeout 20s`. It prints UART0 to the terminal, and from R7 the app's console is UART0, so the app's log should appear there too (not yet run in the emulator: its release binary is not reachable from the build machine). R6 sent its console to USB-Serial-JTAG only, which the emulator does not print: an R6 run stopped printing after `esp_psram: Reserving pool`, while the app went on (its NVS reads at 0x9000 and both cores idling in FreeRTOS show in the emulator's debug log). MIPI-DSI is not in the emulator's peripheral list, so expect the display stage to report a failure there.

## Layout

- `components/slim4_bsp`: the R23 hardware boundary (pins, display, backlight, audio, inputs, power)
- `components/slim4_game_api`: game-facing API: fixed 60 Hz frame pump, controls, RGB565 framebuffer, stereo PCM, per-game saves
- `components/slim4_system_update`: A/B image writer that never overwrites the factory recovery image
- `main`: boot identity, hardware diagnostic loop and platform loop
- `docs/FIRST_BOOT.md`: first power-on behaviour and the bench checks
- `docs/ESPIDF_DISPLAY_REFERENCES.md`: the driver, panel and datasheet sources
- `docs/ARCHITECTURE.md`, `docs/GAME_API.md`, `docs/SYSTEM_UPDATE.md`
- `docs/R22_*`, `docs/RECONSTRUCTION_SOURCES.md`, `docs/STATIC_REVIEW_R*.md`: evidence and reviews of the R22 board (R23 keeps every GPIO)

## Licence note

`slim4_panel_cfaf.c` reproduces the ILI9881C register table from the Linux kernel's `panel-ilitek-ili9881c.c` (GPL-2.0, Crystalfontz's own submission). If this firmware is ever distributed under a licence that is not GPL-compatible, replace the table with the one in Crystalfontz's customer sample code.

## Next bring-up gates

1. On the first assembled board: boot log and chip revision, reset, PSRAM and flash ID.
2. Panel: boot stamp visible, orientation, colour order, timing (draw rate and VSYNC near 59 Hz), backlight range.
3. Controls, left/right speaker channels, charger status with a cell, power button wake.
4. A USB transport for the image-update API, then a launcher and game loader.
