# Firmware pin map — PCB R23 (ESP32-P4NRW32X, chip revision v3.x)

Everything the Struthio firmware needs from the board. Read from the R23 netlist; R23 uses the same GPIOs as R22. `firmware/slim4/tools/check_pinmap.py` checks the firmware's `slim4_pins.h` against the U1 pad nets of `SLIM4_R23_PCB_LAYER.json` and the ESP32-P4 pin table.

## Inputs

| GPIO | Function | Electrical | Notes |
|---|---|---|---|
| 1 | BTN_LEFT (left flap, SW1) | 10 k pull-up, switch to GND | active low; debounce in firmware |
| 2 | BTN_RIGHT (right flap, SW2) | 10 k pull-up | active low |
| 3 | DART_LEFT (rocker left, SW3) | 10 k pull-up | active low |
| 4 | DART_RIGHT (rocker right, SW4) | 10 k pull-up | active low |
| 0 | PWR_WAKE (power button, SW5) | 10 k pull-up, 100 nF | active low; LP-domain pin: use it as the deep-sleep wake source (ext1, wake on low) |
| 35 | BOOT button (SW7) | 10 k pull-up | strapping pin: held low at reset = download mode. Free to read after boot. |
| 11 | CHG_STATUS (BQ24074 CHG) | open drain, 100 k pull-up | low = charging |
| 44 | PGOOD_STATUS (BQ24074 PGOOD) | open drain, 100 k pull-up | low = valid USB power |
| 43 | USB_CURR_OUT1 (TUSB320 OUT1) | open drain, 10 k pull-up | USB-C source current (OUT1/OUT2): H/H nothing attached, H/L default (500 mA), L/H medium (1.5 A), L/L high (3.0 A) |
| 17 | USB_CURR_OUT2 (TUSB320 OUT2) | open drain, 10 k pull-up | see above |
| 16 | BAT_ADC | VBAT × 33 k / 133 k (4.2 V → 1.04 V), 100 nF | ADC; use the 12 dB attenuation range and calibration |

## Outputs

| GPIO | Function | Default at reset | Notes |
|---|---|---|---|
| 9 | BACKLIGHT_PWM (TPS61165 CTRL) | low (100 k pull-down) = backlight off | PWM 6.5–100 kHz (LEDC; TI recommends this range) sets brightness 0–100 % of 74 mA (two strings, 37 mA each). Keep it low until the panel is initialised. Do not turn it on with no panel connected for long: the boost then sits at its 38 V open-LED limit. |
| 10 | LCD_RESET_GATE | high (100 k pull-up) = panel held in reset | Drive LOW to release reset: low → panel RESX high. Sequence: power up, GPIO10 low, wait 120 ms, init commands. |
| 8 | AUDIO_SD_CTRL | low (100 k pull-down) = both amplifiers shut down | Drive HIGH to enable both MAX98357A. Left takes the left I2S slot, right takes the right (set by resistors). |
| 13 | BQ_EN1 | high (10 k pull-up to 3V3) | Charger input limit, with EN2: EN2/EN1 = 0/0 100 mA, 0/1 500 mA (default), 1/0 ILIM 1.0 A, 1/1 USB suspend. Use 1/0 only when the TUSB320 reports 1.5 A or 3 A. |
| 46 | BQ_EN2 | low (10 k pull-down) | see above |

## Buses

| Bus | Pins | Notes |
|---|---|---|
| I2S (TX only, 2 amplifiers) | GPIO5 BCLK, GPIO6 LRCLK (WS), GPIO7 DOUT | Philips I2S, 16- or 32-bit stereo; MAX98357A class D, gain 12 dB (GAIN_SLOT to GND), powered from SYS_RAW. |
| MIPI-DSI | dedicated DSI pins (U1 pads 35–40: D1, CLK, D0), 2 lanes + clock, through 0 Ω R301–R306 to J1 | Crystalfontz CFAF7201280A0-050TN, ILI9881C, 720 × 1280 portrait. ESP-IDF `esp_lcd` MIPI-DSI bus + the `esp_lcd_ili9881c` component, 2 lanes at 1 Gbit/s, RGB565, 78 MHz pixel clock (59 Hz). The init sequence is Crystalfontz's (Linux `panel-ilitek-ili9881c.c`). |
| USB (USB-Serial-JTAG) | GPIO24 D−, GPIO25 D+ | console, flashing and JTAG over the USB-C port. Leave these pins alone in the app, or auto-download stops working. |
| Flash | dedicated SPI flash pins | W25Q512JV, 3.3 V. Boots as 16 MB (3-byte mode). |
| PSRAM | in package | 32 MB, 1.9 V from VDDO_PSRAM (set by the 2nd-stage bootloader) |

## Power facts the firmware should know

- 3.3 V is always on while a cell is connected. "Off" is deep sleep, woken by the power button (GPIO0).
- The core rail (VDD_HP, external TLV62569) is enabled by the chip itself (EN_DCDC) once the app runs.
- The battery has no temperature sensor on the board (TS is a fixed 10 k): if you want a charge-temperature guard, read the P4's internal temperature sensor and pull BQ_EN1/EN2 to suspend (1/1) when it is too hot.
- The USB-C port is a sink only (TUSB320 in UFP mode); charge current is 494 mA (ISET 1.8 k), within the 500 mA default input limit.
- The battery plugs into J3 (JST PH 2.0) behind Q2: a reversed pack leaves the board unpowered. BAT_ADC reads the cell after Q2.
- No free test pads: GPIO37/38 (UART0) are unconnected. Use the USB-Serial-JTAG console.

## Toolchain

ESP-IDF with ESP32-P4 chip revision v3.x support (select v3 as the minimum revision in menuconfig), target `esp32p4`, 40 MHz crystal. First flash: hold BOOT, tap RESET, release BOOT, `idf.py -p <port> flash monitor`.
