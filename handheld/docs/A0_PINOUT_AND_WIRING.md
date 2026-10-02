# Prototype A0 pinout and wiring lock

## Wing buttons
Use the board's exposed general-purpose GPIOs:

- **LEFT WING -> GPIO17** (Waveshare expansion header pin 16 in the published 2x16 pinout image)
- **RIGHT WING -> GPIO18** (header pin 18)
- other side of both switches -> **GND** (for example header pin 30)
- A1.5 DART rocker: **DART LEFT -> GPIO21**, **DART RIGHT -> GPIO38**, common GND, active low (firmware v0.12). Confirm which header positions carry 21 and 38 on the board in hand.

Firmware configures GPIO17/GPIO18 as inputs with pull-ups. Pressing a button pulls the line LOW.
The lines are sampled at 1 kHz and debounced for 8 ms. Each press is stamped at its raw edge, so the 100 ms chord window measures real thumb timing.

No extra wiring for DART: trial C (the v0.5 default) is both wings held for 200 ms.

GPIO17 and GPIO18 are preferred for A0 because the board publishes them as exposed GPIOs, while GPIO0/45/46 are boot strapping pins and GPIO19/20 are native USB.

**Shared with the camera connector.** Waveshare's own example (`esp_bsp/bsp_camera.c`) uses GPIO17 as the camera's VSYNC and GPIO18 as its HREF. The wings work only with **no camera module fitted**, and the firmware never initialises the camera. Leave the camera FPC connector empty and do not port the vendor's camera code.

## Full board pin map (from Waveshare's ESP-IDF example, commit 840daf2)

| Function | Pins |
| --- | --- |
| LCD AXS15231B, QSPI on SPI2 | CS 12, SCLK 5, D0-D3 1-4; backlight 6 (LEDC); reset via the TCA9554 expander, EXIO1 |
| I2C (AXP2101 0x34, TCA9554, ES8311, touch, IMU, RTC) | SDA 8, SCL 7 |
| I2S (ES8311) | MCLK 44, BCLK 13, LRCK 15, DOUT 16, DIN 14 |
| SD card | CMD 10, CLK 11, D0 9 |
| Camera (unused in STRUTHIO) | XCLK 38, PCLK 41, **VSYNC 17, HREF 18**, D 45 47 48 46 42 40 39 21 |
| BOOT / USB / UART0 TX | 0 / 19, 20 / 43 |

Almost every GPIO is spoken for. With no camera fitted, spare pins are **39, 40, 41, 42, 47, 48** (21 and 38 now carry the A1.5 DART rocker). 45 and 46 are also camera pins, but they are strapping pins, so avoid them. With the SD slot empty, 9, 10 and 11 are free as well. Check on the schematic which of these reach the expansion header. The firmware's copy of this map is `firmware/main/board_pins.h`.

## Candidate switch
**Omron B3F-4050** projected-plunger 12 x 12 mm through-hole tactile switch is the first feel-test candidate. Omron specifies 7.3 mm height and 1.27 N operating force for B3F-4050. The related B3F-4055 shares the general projected-plunger mechanical family and gives a firmer alternative. Do not call either final until a real thumb test is performed through the printed STRUTHIO caps.

## Speaker
For the first audio test, use an **8 ohm, ~1 W mono speaker around 28 mm diameter**. The board uses an NS4150B mono Class-D amplifier; its published characteristics include 4-ohm and 8-ohm loads. Keep firmware gain low on first power-up.

## USB-C
The board USB-C is needed for easiest flashing/charging. In portrait packaging it is internal to the handheld footprint. A0 CAD therefore reserves a bottom opening for a **short full-data USB-C male-to-female panel extension**. Bench A0 may be run with the rear shell off until an extension is chosen.

## Service access
Keep BOOT/RESET/PWR reachable during bring-up. Normal gameplay should expose only power; BOOT and RESET become recessed service access later.
