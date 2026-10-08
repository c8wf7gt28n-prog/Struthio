# STRUTHIO SLIM4 platform firmware — R6, for PCB R23

ESP-IDF project for the SLIM4 R23 main board (`hardware/slim4/LAYERS/01_PCB/`). Its job is to bring the board up and give games a hardware-independent API; it is not a game.

## What it drives

| Hardware (R23) | Firmware |
|---|---|
| ESP32-P4NRW32X, chip revision v3, 32 MiB PSRAM in package; W25Q512JV 64 MiB flash | `sdkconfig.defaults`: minimum revision v3.0, 40 MHz crystal, hex PSRAM at 200 MHz, 64 MiB flash, A/B + recovery partitions (`partitions.csv`) |
| Display on J1: Crystalfontz CFAF7201280A0-050TN (5 in 720 × 1280 IPS, ILI9881C), 2-lane MIPI-DSI | `slim4_bsp`: P4 LDO channel 3 at 2.5 V for the D-PHY; 2-lane DSI at 1 Gbit/s; `espressif/esp_lcd_ili9881c` with the Crystalfontz init sequence (`slim4_panel_cfaf.c`); 78 MHz pixel clock, 59 Hz, RGB565; reset through the board's Q1 gate (GPIO10 high = reset) |
| Backlight: TPS61165, 74 mA full scale (R309 2.7 Ω), CTRL on GPIO9 | LEDC PWM at 20 kHz (TI's 6.5–100 kHz range), 12-bit; 45 % after the first frame; off before reset and deep sleep |
| Controls: SW1–SW4 on GPIO1–4 (10 k pull-ups, active low); power button SW5 on GPIO0 | debounced inputs, edge logs, deep-sleep wake on GPIO0 |
| Audio: two MAX98357A on one I2S stream (GPIO5 BCLK, 6 LRCLK, 7 DOUT), enable on GPIO8; speakers on J4 (left) and J5 (right) | stereo 16-bit Philips I2S, no MCLK; amplifiers enabled only while sound plays |
| Charger BQ24074 (CHG GPIO11, PGOOD GPIO44, EN1/EN2 GPIO13/46), USB-C TUSB320 (GPIO43/17), battery ADC GPIO16 (× 133/33) | `slim4_power.c` |
| USB-C data to USB-Serial-JTAG (GPIO24/25) | console, flashing and JTAG over the one cable (`CONFIG_ESP_CONSOLE_USB_SERIAL_JTAG`) |

`tools/check_pinmap.py` checks every `SLIM4_GPIO_*` in `components/slim4_bsp/include/slim4_pins.h` against the net on the matching U1 pad of the R23 board (`SLIM4_R23_PCB_LAYER.json`), through the ESP32-P4 pin table. Run it after any board or pin change.

## Build and flash

ESP-IDF **v6.1**, target `esp32p4`:

```sh
. $HOME/esp/esp-idf/export.sh
idf.py set-target esp32p4      # once
idf.py build
idf.py -p <port> flash monitor
```

The first flash of a new board: hold BOOT (SW7), tap RESET (SW6), release BOOT, then flash. After that `idf.py flash` resets the chip itself over USB-Serial-JTAG. `dependencies.lock` pins the managed components (`esp_lcd_ili9881c`).

This tree builds cleanly with ESP-IDF v6.1. It has not run on hardware yet: the first boards are not built. `docs/FIRST_BOOT.md` lists what the first boot should show and what to check.

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
