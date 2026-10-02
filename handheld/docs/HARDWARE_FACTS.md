# STRUTHIO handheld — hardware facts from the manufacturers

Everything here was read from the manufacturers' own published documents
(fetched 2026-10-02; `tools/fetch_datasheets.sh` downloads them again and checks
the fingerprints). Values read off a drawing by measuring pixels are marked
**measured**; anything that still needs the part in hand is marked **confirm**.
The PDFs themselves are not stored in the repository (some forbid copying).

| Source | File | SHA-256 (first 16) |
|---|---|---|
| Waveshare schematic, rev 2.0 | `ESP32-S3-Touch-LCD-3.5B_V2.0.pdf` | a0b65d8be900a401 |
| Waveshare schematic, first release | `ESP32-S3-Touch-LCD-3.5B-Schematic.pdf` | 71fe3528189c6242 |
| Waveshare dimension drawing (bare board) | `…-details-size-1-….webp` | ce448ce06c3665db |
| Waveshare dimension drawing (cased "-C" version) | `…-details-size-c….webp` | 1c4953f7e3625b22 |
| E-Switch drawing T511012 rev C | `500SSP1S1M7QEA.pdf` | 57d0ea1c47d45d63 |
| E-Switch 500 series datasheet | `500.pdf` | a46cf77d0dac1a82 |
| PUI Audio data sheet rev D (2025-07-17) | `AS02808MR-R.pdf` | 9745b0373bdd5e52 |
| THOR-503450 product page | thorbattery.com/product/thor-503450/ | (web page) |
| Epec rubber keypad design guide | epectec.com/keypads/design/ | (web page) |

## Waveshare ESP32-S3-Touch-LCD-3.5B

**Outline (drawing):** 92.44 × 61.00 mm, corner radius 6.00, 11.50 mm overall
thickness (1.10 cover-glass step, 7.50 to the module back). Active area
73.44 × 48.96 mm, offset 9.50 from the right edge and 6.02 from the top edge
(landscape view from the front).

**Mounting:** four M2 holes, 72.00 × 48.50 mm apart, symmetric about the board
centre: (±36.00, ±24.25) mm. Edge distances 10.22 mm and 6.25 mm.

**Expansion header J8:** 2 × 16 **female** socket, 2.54 mm pitch, on the back,
along the long edge on the battery-socket side, centred on the board's long axis.
Both schematic revisions give the same pin map:

| Pin | Net | | Pin | Net |
|---|---|---|---|---|
| 1 | VBUS (USB 5 V, after the ferrite) | | 2 | VBAT (battery +, AXP2101 BAT) |
| 3 | GND | | 4 | GND |
| 5 | USB_N (GPIO19, D−) | | 6 | **IO21** — DART LEFT |
| 7 | USB_P (GPIO20, D+) | | 8 | **IO38** — DART RIGHT |
| 9 | ESP_SCLK | | 10 | IO39 |
| 11 | ESP_MOSI | | 12 | IO40 |
| 13 | ESP_MISO | | 14 | IO41 (CAM_PCLK) |
| 15 | **IO17** — LEFT WING | | 16 | IO42 |
| 17 | **IO18** — RIGHT WING | | 18 | IO45 (strapping) |
| 19 | IO0 (BOOT) | | 20 | IO46 (strapping) |
| 21 | ESP_EN (reset) | | 22 | IO47 |
| 23 | PWRON (AXP2101 power key) | | 24 | IO48 |
| 25 | ESP_SCL | | 26 | ESP_TXD |
| 27 | ESP_SDA | | 28 | ESP_RXD |
| 29 | GND | | 30 | GND |
| 31 | VCC3V3 | | 32 | VCC3V3 |

All four STRUTHIO controls are on the header: no firmware change is needed.

**Header position (measured** from the drawing, ±0.5 mm; seen from the back,
landscape, origin at the board centre, x toward the right-hand short edge, y toward
the header edge): pin columns at x = −19.05 + 2.54·k (k = 0…15, the header is
centred); row centre y ≈ +23.2. Pin 1 (VBUS) is at the end nearest the USB-C edge,
odd pins on the row toward the board centre (from the "-C" version's printed label;
**confirm** on the board).

**Header height:** the socket's mating face is at the 11.50 mm overall thickness,
measured from the cover glass. Socket depth: **confirm** (it is a low socket, so
the mating male header needs short pins; the first fit print checks it).

**Board sockets:**

| Ref | Type | Pins | Where (back view) |
|---|---|---|---|
| J5 | USB-C 16P | VBUS, D+/D− (to J8 pins 1, 7, 5), CC 5.1 kΩ to GND | left short edge |
| J7 | PH1.25-2P (battery) | 1 = VBAT, 2 = GND | bottom-left, beside MIC / RTC_BKP |
| J9 | PH1.25-2P (speaker) | 1 = OUT+, 2 = OUT− (NS4150B bridge output: **neither pin is ground**) | top edge, beside the BOOT key |
| J6 | SH1.0-2P | RTC backup cell | bottom-left |
| K3 | PWR key | to PWRON (J8 pin 23) | top edge |

**Power path:** USB VBUS → AXP2101 VBUS; battery J7 pin 1 = VBAT = J8 pin 2 →
AXP2101 BAT (pin 33), with a 10 kΩ NTC on TS fitted on the board.

## E-Switch 500SSP1S1M7QEA

- Miniature slide switch, **right-angle PCB mount** ("M7"), SPDT with **three
  positions**: 1 = ON (2–1), 2 = OFF, 3 = ON (2–3). Pin 2 is the common.
- Body 12.70 × 6.60 mm; actuator 3.83 mm square, standing 4.72 mm out of the body,
  parallel to the PCB.
- Pins: three in a row at 3.81 mm pitch, plus two ø1.85 mm mounting pegs 4.45 mm
  apart; recommended holes on the drawing ("RECOMMEND P.C.B. LAYOUT").
- Rating 5 A at 28 V DC; 30,000 operations.
- STRUTHIO use: BAT+ → common (2), throw 1 → VBAT; throw 3 left open, so
  position 1 is ON and positions 2 and 3 are OFF.

## PUI Audio AS02808MR-R

- ø28.0 ± 0.2 mm, 5.2 ± 0.3 mm thick; rear magnet boss ø12.2 mm, 2.4 mm deep.
- 8 Ω ± 15 %, 1.0 W rated (1.5 W max), resonance 500 Hz ± 20 %, 80 dB at 1 m/1 W.
- Metal frame, 5.5 g. Diaphragm excursion up to 0.8 mm: keep that clear in front.
- **Terminals: two solder tabs on the rim, no leads.**

## THOR-503450

- LiPo pouch cell, 1S1P, 3.7 V nominal, 1000 mAh, 3.7 Wh; charge 4.20 V,
  standard 200 mA, max 1.0 A; discharge cut-off 3.0 V, max continuous 1.0 A.
- **5 × 34 × 50 mm bare cell; protection board (included) adds about 2 mm of
  length → 5 × 34 × 52 mm.** Tolerance: thickness ±0.2, width/length ±0.5 mm.
  (The current CAD cavity is sized for 6.2 × 36 × 54 mm.)
- Protection: overcharge 4.28 V, over-discharge cut-off per PCM.
- Connector and lead length are chosen when ordering ("PH2.0 / Molex 1.25,
  custom available"; NTC optional).

## Rubber dome keypads (Epec design guide)

- Travel 0.8–1.5 mm; force 60–300 g; contact bounce < 5 ms;
  carbon contact < 200 Ω; carbon pill hardness 65 ± 5 Shore A.
- Force tolerance grows with force (150 g: ±30–40 g, "good" tactile feel).
  STRUTHIO's targets (1.5 mm / 125 g wings, 1.3 mm / 150 g rocker ends) are inside
  these ranges.
