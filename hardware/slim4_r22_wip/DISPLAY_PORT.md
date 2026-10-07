# Display: panel choice and the J1 display port

## Panel

**Startek KD047HDFID001**: 4.7 in IPS, 720 × 1280, Sitronix ST7703 driver, MIPI-DSI, 450 cd/m², 800:1 contrast, full viewing angle. Module 61.00 × 110.60 × 1.80 mm, active area 58.10 × 103.30 mm, 0.0807 mm pixels (315 ppi). Backlight: 14 LEDs, 2 parallel strings of 7, 21 V at 40 mA. 31-pin FPC tail, 50 mm long. Startek sells single units ("support small quantity").

Why this panel:
- **Fit.** Its active area (58.10 × 103.30) is the area the case was designed around (58.104 × 103.296), and the module is 0.7 mm wider and 0.8 mm shorter than the envelope in CASE R12. The flap and DART switches on the board do not move. A 5 in panel (about 66 × 120 mm) would collide with the DART rocker.
- **Quality.** It is the highest-resolution IPS panel in this size: the 256 × 384 game scales to 720 × 1080 (×2.81) with 200 px left for a status bar.
- **Software.** Espressif's `esp_lcd_st7703` component drives an ST7703 over 2 lanes on the ESP32-P4. The ST7703 sets its lane count in its SETMIPI command, so the panel runs 2-lane although it is wired for 4.

When ordering, ask Startek for the full KD047HDFID001 datasheet: the FPC pin definition, the drawing with the contact side, and the initialisation code. These are not on the product page.

The fully documented alternative is the Crystalfontz CFAF7201280A0-050TN (5 in, 720 × 1280 IPS, ILI9881C, public datasheet). It needs a longer case and moved front controls, so it is not used for this board.

## J1 — the display port on the main board

J1 is a Hirose FH12-20S-0.5SH(55): 20 pins, 0.5 mm pitch, bottom contact, on the back of the board. It is a fixed, panel-independent port. The panel connects through a **display adapter** that maps the port to the panel's FPC. Any pin-order mistake therefore lands on a cheap adapter, never on the main board.

| Pin | Net | What it carries |
|---|---|---|
| 1 | LCD_RESX | Panel reset, active low. Pulled up to 1.8 V (10 k). A 2N7002 pulls it low while GPIO10 is high (GPIO10 has a pull-up, so the panel is held in reset from power-up until firmware drives GPIO10 low). |
| 2 | LCD_VCI_3V0 | VCI (panel analog supply), 3.0 V from TLV75530 (500 mA max) |
| 3 | LCD_1V8 | IOVCC (panel logic supply), 1.8 V from TLV75518 (500 mA max) |
| 4, 5 | — | not connected (data lane 3 is not used) |
| 6, 9, 12, 15, 18 | GND | ground between the pairs |
| 7, 8 | — | not connected (data lane 2 is not used) |
| 10, 11 | MIPI_DSI_CLK_P / N | DSI clock lane |
| 13, 14 | MIPI_DSI_D1_P / N | DSI data lane 1 |
| 16, 17 | MIPI_DSI_D0_P / N | DSI data lane 0 |
| 19 | LCD_LED_K | Backlight cathode return into the TPS61165 current sense (5.1 Ω → 39 mA) |
| 20 | LCD_LED_A | Backlight anode: the boost output, up to 38 V with no LEDs connected |

Electrical limits: backlight 39 mA regulated (both panel strings tied together, about 20 mA each), PWM-dimmed from GPIO9. Lane rate up to 1.5 Gbit/s per lane on the P4; 720 × 1280 at 60 Hz needs about 1 Gbit/s per lane in RGB888 and about 0.7 Gbit/s in RGB565. Board-side DSI runs are 29–40 mm, with at most 5.8 mm of skew within a pair.

## The display adapter (designed when the panel datasheet is in hand)

A small flex, or a rigid board with an FFC, that:
- plugs into the panel's 31-pin FPC on one end and J1 on the other, along the route the case reserves (panel → between the DART switches → around the bottom tab → J1);
- maps CLK, D0 and D1 and their grounds, leaves D2/D3 open, and ties the panel's two LED cathodes to pin 19;
- connects VCI to pin 2 (3.0 V) and IOVCC to pin 3 (1.8 V); check both against the panel datasheet's ranges;
- faces its J1 contacts toward the board (FH12 is bottom contact).

It is cheap and quick to remake, which is the point: the main board does not depend on it.
