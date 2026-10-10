# Firmware pin map — PCB R28 (ESP32-P4NRW32X, chip revision v3.x)

Everything the Struthio firmware needs from the board. Read from the R26 netlist; R27, R26, R25, R24 and R23 use the same GPIOs as R22 (R27 changed values on R401/R402 and added capacitors, no GPIO). R28 keeps all of them and adds the radio on three GPIOs that had no net (*Radio*). `firmware/slim4/tools/check_pinmap.py` checks the firmware's `slim4_pins.h` against U1's pad nets and the ESP32-P4 pin table; the pad nets ship with the firmware (`tools/u1_pad_nets.json`, taken from `SLIM4_R28_PCB_LAYER.json`), and inside this repository the script also checks that table against the board export.

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
| MIPI-DSI | dedicated DSI pins (U1 pads 35–40: D1, CLK, D0), 2 lanes + clock, straight to J1 (R25 removed the 0 Ω links R301–R306; R26 routes them as 100 Ω coupled pairs) | Crystalfontz CFAF7201280A0-050TN, ILI9881C, 720 × 1280 portrait. ESP-IDF `esp_lcd` MIPI-DSI bus + the `esp_lcd_ili9881c` component, 2 lanes, RGB565: 560 Mbit/s a lane and 60 MHz (about 45 Hz) by default, inside the ILI9881C's 2-lane limit; 1000 Mbit/s and 78 MHz (59 Hz) with the console's `display fast` (firmware R12). The init sequence is Crystalfontz's (Linux `panel-ilitek-ili9881c.c`). |
| USB (USB-Serial-JTAG) | GPIO24 D−, GPIO25 D+ | console, flashing and JTAG over the USB-C port. Leave these pins alone in the app, or auto-download stops working. |
| Flash | dedicated SPI flash pins | W25Q512JV, 3.3 V. Boots as 16 MB (3-byte mode). |
| PSRAM | in package | 32 MB, 1.9 V from VDDO_PSRAM (set by the 2nd-stage bootloader) |

## Radio (PCB R28+)

U15, a RAKwireless RAK3172-SiP (STM32WLE5 LoRa / FSK radio, 902–928 MHz, running RAKwireless's RUI3 AT firmware). U1 talks to it over UART1 at 115200 8N1 with AT commands (`firmware/slim4/components/slim4_bsp/slim4_radio.c`).

| GPIO | U1 pad | Net | U15 pin | Notes |
|---|---|---|---|---|
| 39 | 80 | RADIO_UART_TX | 30 (UART2_RX) | U1 transmits |
| 40 | 81 | RADIO_UART_RX | 29 (UART2_TX) | U1 receives. Idle high once the SiP runs; with no SiP (or R701 off) nothing drives it, which is how the self-test tells "not fitted" (U1's pull-down) |
| 50 | 93 | RADIO_NRST | 44 (NRST) | Active low. Drive it open-drain (low only): R703 10 k pulls it up to RADIO_3V3, C726 100 nF filters it |

- BOOT0 (U15 pin 43) is not on U1: R702 holds it low, so the SiP always starts RUI3. RUI3 updates itself over the same UART after `AT+BOOT`; a wire from R702's BOOT0 pad to R703's RADIO_3V3 pad starts the STM32 ROM bootloader instead (recovery).
- RADIO_3V3 comes from 3V3_SYS through R701 (0 Ω): it is on whenever 3V3 is. The SiP idles in its own low-power state between commands.
- The antenna socket is J701 (U.FL). The firmware transmits only when asked (`radio ping`); `slim4_radio_tx_cap_dbm()` caps the power from the power state (22 dBm on USB or on a cell at 3.5 V or more, 14 dBm below 3.5 V or when the cell reading is uncertain, off when the battery is flagged low).
- Default channel 915 MHz, LoRa SF7, 500 kHz (US 902–928 MHz; `slim4_radio_freq_ok()` keeps channels away from harmonics of the 40 MHz and 32 MHz crystals).

## Power facts the firmware should know

- 3.3 V is always on while a cell is connected. "Off" is deep sleep, woken by the power button (GPIO0).
- The core rail (VDD_HP, external TLV62569) is enabled by the chip itself (EN_DCDC) once the app runs.
- The battery has no temperature sensor on the board (TS is a fixed 10 k): if you want a charge-temperature guard, read the P4's internal temperature sensor and pull BQ_EN1/EN2 to suspend (1/1) when it is too hot.
- The USB-C port is a sink only (TUSB320 in UFP mode); charge current is 494 mA (ISET 1.8 k), within the 500 mA default input limit.
- The battery plugs into J3 (JST PH 2.0) behind Q2. BAT_ADC reads BAT_PLUS (after Q2). On USB, BAT_ADC below 1.5 V for 1.5 s means a reversed or shorted pack (Q2 then sits at its threshold and the charger stays in its short-circuit check): the firmware reports it.
- On a 500 mA USB source, unless a qualified cell can supplement (charging, no fault, ≥ 3.5 V for 2 s), the firmware caps the backlight at 15 % (the BQ24074's 450 mA minimum input limit at 4.4 V cannot carry the worst-case 3.3 V load plus more backlight without a cell to supplement). On the battery, or on USB-C 1.5 A / 3 A (charger input 1.07 A), there is no cap.
- No free test pads: GPIO37/38 (UART0) are unconnected. Use the USB-Serial-JTAG console. GPIO41 and GPIO51 (pads 82 and 94) stay unconnected in R28: U1's pad row escapes only the three radio lines.

## Toolchain

ESP-IDF with ESP32-P4 chip revision v3.x support (select v3 as the minimum revision in menuconfig), target `esp32p4`, 40 MHz crystal. First flash: hold BOOT, tap RESET, release BOOT, `idf.py -p <port> flash monitor`.
