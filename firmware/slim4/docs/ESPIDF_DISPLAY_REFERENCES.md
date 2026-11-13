# Display and audio driver references

The display uses Espressif's `espressif/esp_lcd_ili9881c` component (1.1.0, pinned in `dependencies.lock`) on ESP-IDF 6.1.

- [ILI9881C component](https://components.espressif.com/components/espressif/esp_lcd_ili9881c): ESP32-P4 MIPI-DSI driver. It reads the panel ID, writes the lane count (page 1 register 0xB7: 2 lanes here), leaves sleep, sets MADCTL/COLMOD, then sends the vendor table passed in `ili9881c_vendor_config_t`. The Crystalfontz table never writes 0xB7, so the 2-lane setting holds.
- Crystalfontz CFAF7201280A0-050TN datasheet (2022-11-17): pin table (section 6.2), tail fold (section 7.6), backlight (two strings, 19.6–23.8 V, 40 mA each). The board's J1 follows the pin table pad for pad (`hardware/slim4/LAYERS/01_PCB/DISPLAY_PORT.md`).
- Linux `drivers/gpu/drm/panel/panel-ilitek-ili9881c.c` (Raspberry Pi kernel, rpi-6.12.y): the panel's init sequence `cfaf7201280a0_050tx_init` and video mode (78 MHz; H 720 + 120 / 2 / 80; V 1280 + 60 / 2 / 90), contributed by Crystalfontz. `slim4_panel_cfaf.c` and `slim4_panel_cfaf.h` reproduce them (GPL-2.0, see the README's licence note).
- [Espressif MIPI-DSI guide](https://docs.espressif.com/projects/esp-iot-solution/en/latest/display/lcd/mipi_dsi_lcd.html): P4 supports 2-lane DSI up to 1.5 Gbit/s a lane, needs a stable 2.5 V D-PHY rail (LDO channel 3 on this board, U1 pads 41/73), and updates the DPI framebuffer with `esp_lcd_panel_draw_bitmap()`.
- [ESP-IDF 6.1 P4 MIPI-DSI guide](https://docs.espressif.com/projects/esp-idf/en/v6.1/esp32p4/api-reference/peripherals/lcd/dsi_lcd.html): DPI `on_vsync` event, DMA2D copy hook and colour-transfer-complete callback. The diagnostics count VSYNC separately and wait for the transfer callback before reusing the draw buffer.
- [ESP32-P4 datasheet](https://documentation.espressif.com/esp32-p4_datasheet_en.html): pin table used by `tools/check_pinmap.py` (DSI pads 34–41, GPIO pads); ESP32-P4NRW32X has 32 MB in-package PSRAM.
- [TPS61165 datasheet](https://www.ti.com/lit/ds/symlink/tps61165.pdf): PWM dimming on CTRL in the 6.5–100 kHz range (20 kHz here); FB 200 mV, so R309 2.7 Ω sets 74 mA full scale.
- [MAX98357A/MAX98357B datasheet](https://www.analog.com/media/en/technical-documentation/data-sheets/MAX98357A-MAX98357B.pdf): SD_MODE left/right selection thresholds. The board routes GPIO8 through 2 kΩ to the left amp and through 100 kΩ + 110 kΩ to the right amp, so one enable GPIO selects distinct stereo slots. Firmware raises GPIO8, waits 1 ms, then starts the I²S clocks.

These sources confirm the interface, the driver pattern and the panel's own sequence. The image on the glass, the colour order and the timing margins are first-boot checks (`FIRST_BOOT.md`).
