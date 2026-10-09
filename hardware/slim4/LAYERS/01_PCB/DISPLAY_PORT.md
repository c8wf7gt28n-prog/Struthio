# Display: the panel and the J1 display port

## Panel

**Crystalfontz CFAF7201280A0-050TN**: 5.0 in IPS, 720 × 1280, Ilitek ILI9881C driver, MIPI-DSI. Module 66.10 × 120.40 × 1.85 mm, active area 62.10 × 110.40 mm. Backlight: two LED strings on one anode (two cathode pins), 19.6–23.8 V at 40 mA each. The FPC tail has 40 pins at 0.5 mm, contacts on its back, and is 40 mm long. Crystalfontz sells single units and publishes the full datasheet (pin table, drawing, initialisation), so the board can be checked against it before ordering.

Why this panel:
- **Plug and play.** Its tail is long enough to fold behind the module into a socket on the main board. No adapter cable.
- **Documented.** Public pin table and drawing; the init sequence is in the Linux kernel (`panel-ilitek-ili9881c.c`, Crystalfontz's own submission).
- **Software.** Espressif's `esp_lcd_ili9881c` component drives the ILI9881C over 2 lanes on the ESP32-P4. The firmware in `firmware/slim4` uses it.

The case was drawn around a 4.7 in panel; it is set aside for R23-R25, and the case pass redraws the pocket, opening, lens and film for this module (convergence check C6).

## J1: the display port on the main board

J1 is a **Hirose FH12A-40S-0.5SH(55)** (LCSC C506795): 40 pins, 0.5 mm pitch, **top contact**, on the **front** of the board at (1.9, 76.0), mouth toward +Y (the board's bottom edge). Pad k takes panel pin k: pin 1 is the west end (X −7.85), pin 40 the east end (X 11.65).

| Panel pin | Net | What it carries |
|---|---|---|
| 1–9 | — | touch panel signals: not connected |
| 10, 11 | LCD_VCI_3V0 | VCI (panel analog supply), 3.0 V from ME6211C30 (500 mA max) |
| 12, 13 | — | not connected |
| 14 | LCD_RESX | Panel reset, active low. Pulled up to 1.8 V (10 k). A 2N7002 pulls it low while GPIO10 is high (GPIO10 has a pull-up, so the panel is held in reset from power-up until firmware drives GPIO10 low). |
| 15, 16 | — | TE and a reserved pin: not connected |
| 17, 18, 21, 24, 27, 30, 33, 36, 37 | GND | ground between the pairs; a via to the ground planes at each pin or pair |
| 19, 20 | LCD_1V8 | IOVCC (panel logic supply), 1.8 V from TLV75518 (500 mA max) |
| 22, 23, 25, 26 | — | data lanes 3 and 2: not used (2-lane mode) |
| 28, 29 | MIPI_DSI_CLK_P / N | DSI clock lane |
| 31, 32 | MIPI_DSI_D1_P / N | DSI data lane 1 |
| 34, 35 | MIPI_DSI_D0_P / N | DSI data lane 0 |
| 38 | LCD_LED_A | Backlight anode: the TPS61165 boost output, up to 38 V with no panel plugged in |
| 39, 40 | LCD_LED_K | Backlight cathodes (both strings), joined at J1, into the TPS61165 current sense (2.7 Ω → 74 mA) |

`CHECKS/convergence_check.py` check N1 compares every J1 pad's position and net with this table.

Electrical limits: backlight 74 mA regulated (37 mA a string, under the 40 mA rating), PWM-dimmed from GPIO9. Lane rate up to 1.5 Gbit/s on the P4; the firmware runs 1 Gbit/s a lane (720 × 1280 at 59 Hz in RGB565 needs 624 Mbit/s). Board-side DSI runs, U1's pads to J1's, are 65.97–70.56 mm, all six matched to 423.9 ps flight time (R25 edits 25–26, `README_PCB_LAYER.md`), 50 Ω single-ended per layer.

## Plugging the panel in

1. Lay the panel face down on a clean, soft surface, its tail toward you, extended flat.
2. Fold the tail once, back over the module's rear face: start the bend at least 2 mm past the glass edge and keep it round (radius about 1.5 mm, as the datasheet's section 7.6 shows). Do not crease it. The tail now lies on the module's rear face with its contacts facing that rear face (with the panel turned face up they face up, away from the board).
3. Open J1's latch (lift the dark actuator on the side away from the mouth).
4. Hold the board front side up, its bottom edge toward you. Bring the panel over it, face up, its bottom edge toward the board's bottom edge, and slide the tail end into J1's mouth (it opens toward the board's bottom edge) until it stops, contacts up, straight.
5. Close the latch. The tail should not pull out with a light tug.

Placed this way, the panel's bottom edge sits at Y 109.8 and its centre at X 1.2, overhanging the board's top edge by 13.6 mm. Under the panel the only front part is J1 (2.0 mm tall), so the panel's back needs 2.3 mm over J1 and about 3.3 mm at the fold. Until the case is redrawn, support the panel on 3–4 mm spacers (foam tape on the board's front, clear of SW1–SW4).

## What R22 had instead

R22 had a 20-pin FH12 socket on the back of the bottom tab and a custom display flex (now in `REFERENCES/DISPLAY_FLEX_R1/`) between it and a 4.7 in Startek panel whose pin table was not public. R23 removes both: the panel is fully documented and its own tail reaches J1.
