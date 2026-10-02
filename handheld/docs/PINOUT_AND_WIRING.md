# STRUTHIO handheld — pinout and wiring

The firmware's copy of this map is `firmware/main/board_pins.h`. Header pin
numbers follow Waveshare's pinout diagram (pin 1 = BAT, at the battery-socket end, on
the row nearer the board edge). The schematic's J8 numbers swap the two rows; see
`HARDWARE_FACTS.md`.

## Controls (all inputs, internal pull-up, active low, common GND)

| Control | GPIO | Header pin | CP1 pad | Wire |
| --- | --- | --- | --- | --- |
| LEFT WING | 17 | 16 | L | white |
| RIGHT WING | 18 | 18 | R | blue |
| DART LEFT | 21 | 5 | DL | yellow |
| DART RIGHT | 38 | 7 | DR | orange |
| GND | — | 3, 4, 29 or 30 | G | black |

Sampled at 1 kHz, debounced for 8 ms; each press keeps the time of its first
edge, so the 100 ms chord window measures real thumb timing.

A bench build can use just the two wings (GPIO17, GPIO18, GND): DART mode C
(both wings held 200 ms) stands in for the rocker.

**Camera pins.** GPIO17/18 are the camera's VSYNC/HREF and GPIO21/38 its D7 /
XCLK. Leave the camera FPC connector empty; the firmware has no camera code.

## Power and audio

| From | To | Notes |
| --- | --- | --- |
| THOR-503450 BAT+ | E-Switch 500SSP1S1M7QEA common | red, >= 22 AWG |
| E-Switch throw 1 | board BAT+ (J7, PH1.25-2P, pin 1) | throw 3 stays unconnected: positions 2 and 3 are OFF |
| THOR-503450 BAT- | board BAT- | never switched |
| board speaker socket J9 (PH1.25-2P) | PUI AS02808MR-R | pin 1 OUT+, pin 2 OUT−; neither is ground |
| USB-C panel jack | board USB-C | short full-data extension |

## Full board pin map (Waveshare ESP-IDF example, commit 840daf2)

| Function | Pins |
| --- | --- |
| LCD AXS15231B, QSPI on SPI2 | CS 12, SCLK 5, D0-D3 1-4; backlight 6 (LEDC); reset via the TCA9554 expander, EXIO1 |
| I2C (AXP2101 0x34, TCA9554 0x20, ES8311 0x18, touch 0x3B, IMU 0x6B, RTC 0x51) | SDA 8, SCL 7 |
| I2S (ES8311) | MCLK 44, BCLK 13, LRCK 15, DOUT 16, DIN 14 |
| SD card (unused) | CMD 10, CLK 11, D0 9 |
| Camera (do not fit) | XCLK 38, PCLK 41, VSYNC 17, HREF 18, D 45 47 48 46 42 40 39 21 |
| BOOT / USB / UART0 TX | 0 / 19, 20 / 43 |

Spare with no camera fitted: 39, 40, 41, 42, 47, 48. Avoid 45 and 46
(strapping pins).
