# R6 — PCB R23 and the Crystalfontz panel

- Board support moved from PCB R22 to **R23**. R23 keeps every GPIO; the display now plugs straight into J1 (no adapter flex), the battery into a JST PH socket behind a reverse-polarity MOSFET, the speakers into PicoBlade sockets.
- Display driver: **ILI9881C** (`espressif/esp_lcd_ili9881c` 1.1.0) for the Crystalfontz CFAF7201280A0-050TN, replacing the assumed ST7703. Init sequence and video mode from Crystalfontz's Linux driver (`slim4_panel_cfaf.c/.h`): 2 lanes at 1 Gbit/s, 78 MHz pixel clock, 59.1 Hz, RGB565.
- Backlight full scale is now 74 mA on the board (R309 2.7 Ω); the firmware's 45 % start level gives about 33 mA.
- Power: battery voltage, USB-C current advertisement, charger status and die temperature; charger input 1.07 A only when USB-C offers 1.5 A or 3 A; charging suspended above 75 °C die temperature; 2 s power-button hold switches off into deep sleep, the button wakes it.
- `tools/check_pinmap.py` now checks every `SLIM4_GPIO_*` against the R23 board itself (U1 pad nets from `SLIM4_R23_PCB_LAYER.json`, through the ESP32-P4 pin table), not a reconstructed R22 table: 19 of 19 match.
- Builds with ESP-IDF v6.1 for `esp32p4` (app 388 KiB, 91 % of the 4 MiB app slot free). Not yet run on hardware.
