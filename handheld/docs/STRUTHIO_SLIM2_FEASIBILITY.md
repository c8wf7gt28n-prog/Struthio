# STRUTHIO ONE SLIM 2 · feasibility: one board, no soldering, thinner

Status: **study only**. The 16.5 mm ONE SLIM (case rev S3, board rev S2) stays the build; nothing here changes it.
Everything below is from datasheets and distributor listings (linked); anything not yet seen in a datasheet or in
hand is marked **confirm**. Thicknesses and costs are estimates until a part is quoted or measured.

## 1. What the game needs (from the firmware, not guessed)

| Need | Why | Source |
|---|---|---|
| ESP32-S3, **16 MB flash, 8 MB octal PSRAM** | the game (0.6 MB), the art pack (8.7 MB) and the music (1.9 MB) live in flash; frames in PSRAM | `partitions.csv`, `sdkconfig.defaults` |
| 320 × 480 panel, 48.96 × 73.44 mm active area | the art, HUD and face panel are drawn for it | `cad/one`, `render/` |
| Fast enough for 30 frames/s full screen | the renderer sends whole frames | 320 × 480 × 16 bit × 30 = 74 Mbit/s |
| I2S codec + speaker amp | sound effects and music | `audio/`, ES8311 driver |
| Charger, fuel gauge, power key, off state | power button, auto-off, battery check | AXP2101 driver (`board_pmu.cpp`) |
| 4 buttons on GPIOs | wings, rocker | `board_pins.h` |

## 2. How the parts are chosen (in this order)

1. **The panel first**: it sets the thickness, the outline and the firmware. Must be 320 × 480 at 3.5", must
   reach 30 frames/s, must be buyable one at a time, must have a datasheet with its FPC pinout.
2. **Keep the chips the firmware already drives** (AXS15231B, AXP2101, ES8311): every one kept is code that is
   already written and tested, so only pin numbers change.
3. **Only parts JLCPCB stocks and places**, so the board arrives finished. Checked in stock, not assumed.
4. **Height of the tallest part on the board**: after the panel it is what sets the thickness.
5. **A certified radio module** rather than a bare chip: no antenna design, no RF tuning on the first spin.
6. Cost last: the board is a one-off for the builder; a few dollars do not outweigh 1-5.

## 3. Candidates found

### Panel

| | A: AXS15231B 3.5" (Startek KD035QVFID225-C086A) | B: ST7796U 3.5" (QD3525, LCDwiki) |
|---|---|---|
| Thickness | **3.24 mm**, touch included in the glass | **2.5 mm**, no touch |
| Outline | 61.90 × 96.04 mm (the Waveshare's panel has the same outline) | 55.50 × 84.96 mm |
| Interface | controller supports QSPI; Startek lists this part as MIPI, 30-pin 0.5 mm: **confirm a QSPI build** | 4-wire SPI on the module; the bare panel's 8080 parallel option: **confirm** |
| Speed for 30 frames/s | QSPI: what the Waveshare does today | single-line SPI tops out near 60 MHz (about 25 frames/s): too slow unless 8080 parallel |
| Firmware | **display code unchanged** | new driver (ST7796 is well supported in ESP-IDF) |
| Backlight | 8 LEDs in series, 24.5 V, 20 mA: needs a boost driver | 6 LEDs, 95 mA total |
| Buying one | "no MOQ", samples from stock; price on request | sold widely as modules; bare panel from LCD shops |

**Choice: A**, if Startek confirms a QSPI version and its datasheet. It keeps the display code and the art
exactly as they are; B saves 0.74 mm but costs a new driver and needs the parallel bus.

### Electronics (all JLCPCB-placeable, checked in stock)

| Part | What | LCSC | Stock / price seen |
|---|---|---|---|
| ESP32-S3-WROOM-1-**N16R8** | module: 16 MB flash, 8 MB octal PSRAM, PCB antenna, 3.1 mm tall | C2913202 | 1,700-30,000 / from $3.41 |
| AXP2101 | the power chip the firmware already drives | C3036461 | 1,396 / $1.97 |
| ES8311 | the codec the firmware already drives | C962342 | 79,642 / $0.56 |
| NS4150B | 3 W class-D speaker amp | C189961 | in the JLC library |
| AP3031 | LED boost for panel A's 24 V backlight, PWM dimming | C82636 | in the JLC library |
| plus | USB-C socket, panel FPC connector (30-pin 0.5 mm, **confirm** against the panel), JST PH battery socket, 1.25 mm speaker socket, 4 tact switches (C318884, used now), passives | | to pick at schematic time |

## 4. Thickness, estimated

One board, panel in front, everything else on the back of the board; the battery beside the module.

| Layer | mm |
|---|---|
| Face panel (acrylic) | 1.0 |
| Shell rim over the glass | 0.5 |
| Panel A | 3.24 |
| Foam tape between panel and board | 0.3 |
| Board | 0.8 |
| Tallest part on the back: the module (the 3.0 mm battery sits beside it) | 3.2 |
| Clearance | 0.2 |
| Back wall | 1.5 |
| **Total** | **≈ 10.7 mm** (panel B: ≈ 10.0) |

Against 16.5 mm today. A bare ESP32-S3 chip with its own flash instead of the module would take the tallest
part down to the battery (3.0 mm) and save about 0.2 mm more, at the cost of antenna design: not worth it.

## 5. The build, without soldering

1. Flash over USB-C (the same FLASH_ME).
2. Panel: slide its ribbon into the connector, close the latch, stick the panel to the board.
3. Plug the battery and the speaker in.
4. Board into the front shell, back shell on, screws.

## 6. Cost, rough (to be quoted)

| | Each, building 2 |
|---|---|
| Board + assembly at JLCPCB (two-sided: panel side and back) | about $25-45 (setup fees dominate at 2) |
| Panel A | price on request (similar panels sell for about $8-20) |
| Cell, speaker, screws, panel acrylic | as today |

About the same as the Waveshare board ($25-30) plus today's control board, before volume.

## 7. Risks

| Risk | How it is handled |
|---|---|
| Our own power, radio and audio design: a first board may need a fix | follow Espressif's and X-Powers' reference circuits; order 2-5 test boards first |
| Panel A only listed as MIPI | ask Startek for the QSPI build and its datasheet before drawing anything |
| JLC stock can move | recheck at order time; every chip has an alternative |
| Firmware | pins change; panel A keeps the display driver; AXP2101 and ES8311 keep theirs |

## 8. Also looked at: the Guition JC3248W535 (off the shelf)

ESP32-S3, 16 MB / 8 MB, the same AXS15231B panel on QSPI, LiPo charging, about $11-18. It would need no board
design at all, but it has no AXP2101 or ES8311 (new power and sound code), its thickness and connectors are not
published (**confirm** with one in hand), and the buttons would have to reach its GPIOs through its connectors.
Worth buying one to measure; it is the cheap way to see the panel too.

## 9. Next steps, in order

1. Ask Startek for the KD035QVFID225 QSPI datasheet, its FPC pinout and a sample price (one email).
2. Optionally buy a JC3248W535 to measure the panel in hand.
3. Then: schematic from the reference circuits → board → case at about 11 mm → firmware pin map → 2 test boards.

Sources: [Waveshare 3.5B](https://www.waveshare.com/esp32-s3-touch-lcd-3.5b.htm),
[Startek KD035QVFID225-C086A](https://www.startek-lcd.com/product/1188-KD035QVFID225-C086A-3.5-inch-320x480-AXS15231-MIPI-Interface-High-Brightness-TFT-LCD-Display-Module-with-Capacitive-touch.html),
[AXS15231B datasheet](https://dl.espressif.com/AE/esp_iot_solution/AXS15231B_Datasheet_V0.5_20230306.pdf),
[LCDwiki 3.5" ST7796](https://www.lcdwiki.com/3.5inch_IPS_SPI_Module_ST7796),
[ESP32-S3-WROOM-1-N16R8 at LCSC](https://www.lcsc.com/product-detail/WiFi-Modules_Espressif-Systems-ESP32-S3-WROOM-1-N16R8_C2913202.html),
[AXP2101 at LCSC](https://www.lcsc.com/product-detail/C3036461.html),
[ES8311 at LCSC](https://www.lcsc.com/product-detail/C962342.html),
[NS4150B at JLCPCB](https://jlcpcb.com/partdetail/Shenzhen_NsiwayTech-NS4150B/C189961),
[AP3031 at JLCPCB](https://jlcpcb.com/partdetail/DiodesIncorporated-AP3031KTRG1/C82636),
[Guition JC3248W535 notes](https://www.atomic14.com/esp32/boards/guition-jc3248w535/).
