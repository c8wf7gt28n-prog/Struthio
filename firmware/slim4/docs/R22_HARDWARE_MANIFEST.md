# SLIM4 R22 firmware hardware manifest

> **R22 evidence, kept for reference.** PCB R23 keeps every GPIO listed here; its display port, panel and connectors changed (`hardware/slim4/LAYERS/01_PCB/README_PCB_LAYER.md`). The panel question below is settled in R23: the Crystalfontz CFAF7201280A0-050TN's own tail plugs into J1, checked pin for pin. `tools/check_pinmap.py` checks the firmware against the R23 board.

Source: `SLIM4_R22.kicad_pcb`, exported board model, and R22 JLCPCB BOM/CPL. This is firmware evidence only, not a PCB fabrication certification.

| Function | R22 evidence | Firmware state |
|---|---|---|
| MCU | ESP32-P4NRW32X, U1 | target is `esp32p4`; silicon revision to read at bring-up |
| External flash | W25Q512JVEIQ, U2, 512 Mbit = 64 MiB | partition layout draft; verify JEDEC ID, mode, usable capacity |
| Panel | J1 FH12-20S-0.5SH, 20-pin FPC, 2-lane MIPI DSI; LCD_RESX, VCI/1V8, DSI D0/D1/CLK; TPS61165 backlight | Firmware assumes the intended ribbon/panel combination works. ST7703 720×1280 driver path, reset gate and PWM backlight are implemented; validate image, timing and brightness on assembled hardware |
| Inputs | SW1/2 BTN_LEFT/BTN_RIGHT; SW3/4 DART_LEFT/DART_RIGHT, contacts to GND, 10 kΩ external pull-ups | Verified GPIO1–GPIO4 active-low; implemented and sampled by the game API |
| Audio | U8/U9 MAX98357A; common I2S_BCLK/LRCLK/DOUT; separate AUDIO_SD_L/R and SPK_L/R outputs | Stereo 16-bit Philips I²S TX implemented on GPIO5/6/7. GPIO8 controls both shutdown/select nets. R501 = 2 kΩ sets left; R502 + R503 = 100 kΩ + 110 kΩ set right; R504 = 100 kΩ pulls the control low. Verify physical channel identity and safe volume before acoustic tuning |
| USB | USB4105 J2, TUSB320 U13, TPD2EUSB30 U11/U12; recovery logical nets present | USB service/recovery path requires data-role and GPIO mapping confirmation |
| Boot/service | SW5–SW7 B3U-1000P; CHIP_PU, BOOT_STRAP, DOWNLOAD_STRAP; recovery logical GPIO26/27 | Validate actual strap sequence and recovery-mode behavior on assembled unit |
| Battery/charge | BQ24074 U10 and battery/power nets | Telemetry/charge-state nets need GPIO/ADC mapping; no charging control assumed in game API |

## Mapped logical signals from R22 board model

`BTN_LEFT`, `BTN_RIGHT`, `DART_LEFT`, `DART_RIGHT`, `I2S_BCLK`, `I2S_LRCLK`, `I2S_DOUT`, `AUDIO_SD_L`, `AUDIO_SD_R`, `BACKLIGHT_PWM`, `LCD_RESET_GATE`, `CHG_STATUS`, `FLASH_CS_SOC`, `FLASH_CLK_SOC`, `FLASH_IO0_SOC..FLASH_IO3_SOC`, `USB_RECOVERY_GPIO26`, `USB_RECOVERY_GPIO27`, `UART0_TX`, `UART0_RX`.

The release folder contains no `.kicad_sch`, but the native `.kicad_pcb` preserves each footprint pad-to-net association. MCU GPIO mappings below were derived from those U1 pad numbers and Espressif’s package pin table. They are sufficient to implement gameplay GPIO input. The original schematic is still useful for design intent and review, but is not required to recover these board connections.

## Verified gameplay pin map

| PCB net | U1 package pin | ESP32-P4 GPIO | Polarity / board evidence |
|---|---:|---:|---|
| BTN_LEFT | 1 | GPIO1 | active low; SW1 to GND; R111 10 kΩ pull-up to 3V3_SYS |
| BTN_RIGHT | 2 | GPIO2 | active low; SW2 to GND; R112 10 kΩ pull-up to 3V3_SYS |
| DART_LEFT | 3 | GPIO3 | active low; SW3 to GND; R601 10 kΩ pull-up to 3V3_SYS |
| DART_RIGHT | 4 | GPIO4 | active low; SW4 to GND; R602 10 kΩ pull-up to 3V3_SYS |

More R22 pin mappings are recorded in `R22_P4_GPIO_MAP.csv`. Dedicated flash and DSI package pins are not ordinary GPIO. Strap pins GPIO34–GPIO38 need careful startup treatment. Panel cable/pin compatibility remains an open item despite the board-side J1 net map.
