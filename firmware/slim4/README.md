# STRUTHIO SLIM4 platform firmware — R12, for PCB R27 (and R23-R26: same pins)

ESP-IDF project for the SLIM4 main board (`hardware/slim4/LAYERS/01_PCB/`, PCB R27; R24 changed the power layout, R25 the DSI routing and plane shapes, R26 the DSI routing again (coupled pairs) and R27 added margin parts and ground vias only, so every pin the firmware uses is as on R23; the boot log names PCB R27). Its job is to bring the board up, check it for assembly faults, and give games a hardware-independent API; it is not a game.

## What it drives

| Hardware (R23) | Firmware |
|---|---|
| ESP32-P4NRW32X, chip revision v3, 32 MiB PSRAM in package; W25Q512JV 64 MiB flash | `sdkconfig.defaults`: minimum revision v3.0, 40 MHz crystal, hex PSRAM at 200 MHz, 64 MiB flash, A/B + factory (recovery) partitions (`partitions.csv`) |
| Display on J1: Crystalfontz CFAF7201280A0-050TN (5 in 720 × 1280 IPS, ILI9881C), 2-lane MIPI-DSI | `slim4_bsp`: P4 LDO channel 3 at 2.5 V for the D-PHY; 2-lane DSI, RGB565, `espressif/esp_lcd_ili9881c` with the Crystalfontz init sequence (`slim4_panel_cfaf.c`); safe profile by default, 560 Mbit/s a lane and 60 MHz (about 45 Hz), inside the ILI9881C's 2-lane limits; fast profile (`display fast` on the console) 1000 Mbit/s and 78 MHz (59 Hz), Espressif's setting, above them; bring-up limited to 8 s; reset through the board's Q1 gate (GPIO10 high = reset) |
| Backlight: TPS61165, 74 mA full scale (R309 2.7 Ω), CTRL on GPIO9 | LEDC PWM at 20 kHz (TI's 6.5–100 kHz range), 11-bit (12 bits at 20 kHz is a divider ESP-IDF rejects); a backlight failure does not stop the display; 45 % after the first frame; off before reset and deep sleep; capped at 15 % on USB below 1 A unless a qualified cell can supplement (the power budget, `docs/FIRST_BOOT.md`) |
| Controls: SW1–SW4 on GPIO1–4 (10 k pull-ups, active low); power button SW5 on GPIO0 | debounced inputs, edge logs, deep-sleep wake on GPIO0 |
| Audio: two MAX98357A on one I2S stream (GPIO5 BCLK, 6 LRCLK, 7 DOUT), enable on GPIO8; speakers on J4 (left) and J5 (right) | stereo 16-bit Philips I2S, no MCLK; amplifiers enabled only while sound plays; muted (held in shutdown) while the USB backlight cap is on, since a 500 mA source has no budget left for audio |
| Charger BQ24074 (CHG GPIO11, PGOOD GPIO44, EN1/EN2 GPIO13/46), USB-C TUSB320 (GPIO43/17), battery ADC GPIO16 (× 133/33) | `slim4_power.c`: battery voltage, USB-C advertisement, charger input limit, low-battery switch-off (2 s below 3.3 V, whatever the button does), die-temperature charge suspend (only with a qualified cell above 3.6 V), a 6 h charge-time limit per USB session once a suspend has restarted the charger's timer, reversed/shorted-pack warning; only a calibrated battery reading drives a decision (uncalibrated: shown as `battery_approx`, treated as no reading) |
| USB-C data to USB-Serial-JTAG (GPIO24/25) | flashing, JTAG, the bootloader's and every app log line, and the bring-up console (`main/slim4_console.c`, `docs/FIRST_BOOT.md` *Console*) over the one cable; USB-Serial-JTAG is the primary console (UART0's pins reach nothing on the board) |

## Hardware self-test (R11)

At every boot the firmware checks the board before using it and reports each check as PASS, FAIL or INFO. The results go to the serial log (`SELFTEST …` lines) and to a self-test page on the panel. The checks:
- every pulled-up or pulled-down GPIO net (15): U1's pad joint, the resistor (missing or wrong value), stuck switches, shorts to a rail;
- PWR_WAKE's RC time (C601);
- shorts between 24 pins, including the unconnected U1 pads beside the board nets;
- U1's revision, PSRAM size, U2's flash ID and size, and a brownout before this boot;
- a bounded probe of the panel over DSI lane 0 (ID 98 81 xx and error flags);
- the frame rate, and USB against the charger's PGOOD.

The page ends with colour bars and 1-pixel gratings, which are the visual check of the CLK and D1 lanes. The probe also stops a panel that does not answer from hanging the boot (through R10 it would have). How it works and what each line means: `docs/FIRST_BOOT.md`, *Self-test*; the code is `components/slim4_bsp/slim4_selftest*.c` and the probe in `slim4_board.c`.

`tools/check_pinmap.py` checks every `SLIM4_GPIO_*` in `components/slim4_bsp/include/slim4_pins.h` against the net on the matching U1 pad of the R27 board, through the ESP32-P4 pin table. The pad nets ship with the firmware (`tools/u1_pad_nets.json`, taken from `SLIM4_R27_PCB_LAYER.json`), so the check runs from this folder alone; inside the repository it also checks that table against the board export. It also checks the self-test's pin table: each pad and net, and, inside the repository, each pull resistor's value and rail and the 100 nF capacitors. Run it after any board or pin change: `--board <export.json>` checks against another board export, `--write-table <export.json>` refreshes the table.

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

### Host tests

`sh tests/host/run.sh` builds and runs two tests with any C compiler.

`test_selftest_logic.c` runs the self-test's decisions (`slim4_selftest_logic.c`, unchanged) on a simulated board with 65 cases:
- solder bridges between neighbouring and distant pads, including nets that are never driven;
- open U1 pads, missing and wrong-value resistors, C601 missing or a slow PWR_WAKE;
- held switches and nets shorted to a rail;
- charger outputs asserted or toggling;
- every panel-probe outcome, chip and memory identities, the power lines, and the report limits.

`test_power_policy.c` compiles `components/slim4_bsp/slim4_power.c` unchanged against small stand-ins for the ESP-IDF calls (`tests/host/sdk/`), and runs 51 cases: the 500 mA USB cap and what may lift it, the audio mute that goes with it, uncalibrated battery readings, reversed or shorted pack, low-battery switch-off with the button released or held and with a transient dip, failed battery readings, the over-temperature charge suspend and every way out of it, the charge-time limit across suspends (hours of simulated charging), and the power button. It checks decisions, not analog behaviour.

### Emulator

Espressif's esp-emu (beta) runs the merged image: `esp-emu --chip esp32p4 --firmware merged.bin --psram-size 32M --timeout 20s`. It prints UART0 only, and from R12 the console is USB-Serial-JTAG (on the board UART0 reaches nothing), so the app's log does not appear there, as with R6: an R6 run stopped printing after `esp_psram: Reserving pool`, while the app went on (its NVS reads at 0x9000 and both cores idling in FreeRTOS show in the emulator's debug log). For an emulator run, build with `CONFIG_ESP_CONSOLE_UART_DEFAULT=y`. MIPI-DSI is not in the emulator's peripheral list, so expect the display stage to report a failure there.

## Layout

- `components/slim4_bsp`: the hardware boundary (pins, display, backlight, audio, inputs, power) and the self-test
- `components/slim4_game_api`: game-facing API: fixed 60 Hz frame pump, controls, RGB565 framebuffer, stereo PCM, per-game saves
- `components/slim4_system_update`: A/B image writer that never overwrites the factory recovery image
- `main`: boot identity, hardware diagnostic loop, platform loop and the USB console (`slim4_console.c`)
- `docs/FIRST_BOOT.md`: first power-on behaviour and the bench checks
- `docs/ESPIDF_DISPLAY_REFERENCES.md`: the driver, panel and datasheet sources
- `docs/ARCHITECTURE.md`, `docs/GAME_API.md`, `docs/SYSTEM_UPDATE.md`
- `docs/R22_*`, `docs/RECONSTRUCTION_SOURCES.md`, `docs/STATIC_REVIEW_R*.md`: evidence and reviews of the R22 board (R23 keeps every GPIO)

## Licence note

`slim4_panel_cfaf.c` reproduces the ILI9881C register table from the Linux kernel's `panel-ilitek-ili9881c.c` (GPL-2.0, Crystalfontz's own submission). If this firmware is ever distributed under a licence that is not GPL-compatible, replace the table with the one in Crystalfontz's customer sample code.

## Next bring-up gates

1. On the first assembled board: the self-test's lines (chip revision, PSRAM and flash ID, every GPIO net, shorts, the panel probe) and the page's bars and lines.
2. Panel: boot stamp visible, orientation, colour order, timing (draws near 60, VSYNC near 45 Hz in the safe profile), backlight range; console patterns `checker` and `gradient` clean. Then `display fast`, reboot and the same patterns: keep the fast profile only if they stay clean.
3. Controls, left/right speaker channels, charger status with a cell, power button wake.
4. A USB transport for the image-update API, then a launcher and game loader.
