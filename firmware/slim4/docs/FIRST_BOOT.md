# First firmware boot on PCB R26

This image is a board bring-up build for the R26 main board (R23-R25 have the same pins) with the Crystalfontz CFAF7201280A0-050TN plugged into J1 (`hardware/slim4/LAYERS/01_PCB/DISPLAY_PORT.md` shows how the tail folds in). From R11 it checks the board for assembly faults at every boot (*Self-test* below). It has not run on hardware yet.

## Before power

- Panel tail fully in J1, latch closed, contacts up (away from the board). Battery on J3 with pin 1 (red) = BAT+: check it. A reversed pack is blocked while the board runs from it; with USB connected it is not disconnected: the design analysis predicts the charger's 4–11 mA test current (not tested), and the screen shows `BATTERY REVERSED - UNPLUG`. Never plug in a reversed pack on purpose. Speakers on J4 (left) and J5 (right).
- First power from USB-C on a current-limited supply if you can (5 V, 500 mA limit). The board draws well under that until the backlight comes on.
- Keep your hands off the controls while it boots: the self-test reads their pull-ups first. A control held at power-on (the wake press of SW5 too) is waited for, up to 5 s.

## Expected behaviour

1. Over the USB-C port (USB-Serial-JTAG), the ROM banner and then every app line: app information with the chip revision, PSRAM, `firmware=slim4_platform version=0.10.0` and `target=ESP32-P4 board=SLIM4 PCB R26`. The second-stage bootloader's own lines (partition table) go to UART0 only, whose pins are not brought out.
2. The self-test's GPIO checks (under a second; `GPIO checks took … ms`). Their results are printed with the rest after step 5.
3. The BSP requests 2.5 V from P4 LDO channel 3 for the MIPI D-PHY, holds the panel in reset (GPIO10 high), sets up the backlight PWM (off), opens the 2-lane DSI bus at 1 Gbit/s and installs the ILI9881C driver with the Crystalfontz init sequence.
4. It releases reset (GPIO10 low), waits 120 ms and probes the panel (`panel probe: answered, ID 98 81 0C, …`). If the panel does not answer, the display bring-up stops here and the boot goes on without it. Otherwise it sends the init sequence (the driver logs the ID again), turns the display on, draws the boot stamp (navy, "SLIM4 / R26"), and only then turns the backlight on at 45 % (about 33 mA), or at 15 % on USB below 1 A until a cell qualifies (`backlight limited to 15 %` in the log).
5. The log line `ILI9881C two-lane DSI initialized: 720x1280 RGB565, 78 MHz pixel clock (59 Hz)` confirms the controller side. The self-test's other checks follow, then every result as a `SELFTEST PASS|FAIL|INFO <check> …` line and `SELFTEST RESULT: …`.
6. The stamp's bottom line changes from `STARTING` to `VERIFIED` (or `SERVICE MODE`) once the controls, framebuffer and audio worker pass (or fail) their software checks. That label covers the software only. The self-test page follows: it stays up 10 s, or until a control is pressed.
7. The diagnostic loop redraws a moving sweep at the panel's 59 Hz, lights a tile and counts presses for each of the four controls, and logs every input edge. Each press plays a short tone at 20 % volume on its side (flaps 880 Hz, DART 660 Hz).
8. The screen shows the self-test counts in its header (BOOT, SW7, shows the page again), firmware draws per second, DPI VSYNC events per second, the longest render-and-submit time, the frame number and late frames. Readings of 58–62 are cyan, others red, zero gold while starting.
9. At start, the power log line gives the battery voltage, USB-C current advertisement, charging state, the charger input limit, the backlight cap and the die temperature; the policy then re-reads them every 0.5 s (charger input 1.07 A only when USB-C advertises 1.5 A or 3 A; above 75 °C die temperature charging is suspended, but only with a qualified cell above 3.6 V, since suspend also takes the system off USB). On the battery, 2 s below 3.3 V switches the board off whatever the button does. Holding the power button 2 s switches off (deep sleep); pressing it wakes the board. If the battery reading fails, the log says so: there is then no low-battery switch-off (the pack's own protection still cuts off) and the backlight stays capped on USB below 1 A.

A display error is logged with the stage that failed; the app keeps running so the serial diagnostics stay available.

## Self-test

The checks run at every boot. Each prints one line: PASS, FAIL or INFO, the check's name, a short result (as on the page) and the details: what was measured, the parts and U1 pads involved, and where to look.

| Check (lines) | How | What a FAIL means |
|---|---|---|
| Pull resistors and U1 pad joints: BTN_LEFT, BTN_RIGHT, DART_LEFT, DART_RIGHT, BOOT_STRAP, PWR_WAKE, BQ_EN1, BQ_EN2, CHG_STATUS, PGOOD_STATUS, USB_CURR_OUT1/OUT2, LCD_RESET_GATE, BACKLIGHT_PWM, AUDIO_SD_CTRL | U1's own pull (about 45 kΩ) the same way as the board's resistor: the net must rest at its level. Then, on 10 k nets, U1's pull against the resistor: a 10 k still wins. Then the pin is driven to the other level for 20 µs and released: a net with its resistor returns within microseconds, a pad that is not connected keeps the level it was driven to | `OPEN`: the U1 pad is not soldered, or the resistor is missing or open. `WEAK PULL`: a higher value fitted (100 k for 10 k). `HELD`: a switch pressed or stuck, or the net shorted to GND or 3V3 |
| PWR_WAKE rise time | C601 discharged, then the time until the pin reads high through R110: about 0.7 ms, 0.2–3 ms accepted | `TOO FAST`: C601 missing. `TOO SLOWLY`: extra capacitance or leakage, e.g. a bridge to CHIP_PU (pad 103, 1 µF) |
| SHORTS (SHORT, DRIVE) | 24 pins, the 19 board nets and the unconnected U1 pads beside them (GPIO12, 14, 15, 18, 45), each driven high then low at U1's weakest drive for 50 µs (1 ms on PWR_WAKE and BAT_ADC, which carry 100 nF) while the others are read, two scans | `SHORT A - B`: the two nets are joined. On neighbouring U1 pads, look for a solder bridge. `DRIVE`: a pin cannot reach a level, so its net is shorted to a rail |
| CHIP, PSRAM, FLASH, RESET | eFuse revision; PSRAM size; U2's JEDEC ID and size; reset reason | Not v3.x; not 32 MiB; not EF4020 / 64 MiB (wrong part); a brownout or power-glitch reset before this boot |
| PANEL, DSI_LANE0 | Before the panel driver: page select, the three ID registers, then a second exchange (ID again, a write with acknowledge), each wait limited to 20 ms. Low-power DSI drives D0_P and D0_N separately, so an answer shows both lines work | `NO ANSWER`: see *If the display stays dark*. `ID …`: a different controller. `ERRORS ON DSI LANE 0`: the panel or the D-PHY flagged errors in the second exchange (D0 pair, J1, FPC) |
| VIDEO | Frames per second from the DSI host | `NO FRAMES`: video did not start |
| USB_INPUT, USB_CC, BATTERY, DIE_TEMP | A USB host's start-of-frame packets against the charger's PGOOD; TUSB320 OUT1/OUT2; battery rail; die temperature | `USB HOST BUT NO PGOOD`: the VBUS path from J2 to U10 pin 13 (D1, C403, C409) or U10 |

INFO lines need no action but tell you something:
- `LOW - ASSERTED BY ITS CHIP` on PGOOD or CHG: the charger has its output on, which is right with USB in or a charge running. A short to GND would read the same, so these two nets' joints are checked only on a boot without USB, or with no charge running.
- `LINK_ONCE`: two nets moved together in one scan of two, and one is a chip's status output, which can switch by itself (CHG toggles while the charger looks for a cell). Reboot: a real short shows in both scans.
- RESET, USB_CC, BATTERY (it wanders with no cell fitted), DIE_TEMP, and VIDEO (look at the bars).

Look at the page's bars and lines. CLK and D1 carry video only, and the probe cannot reach them, so the picture is their check. The colour bars and the 1-pixel gratings must be clean, with no sparkles, shifted rows or wrong colours.

What it does not check: the regulator outputs and ripple (no ADC on the rails: measure them), the backlight current, the I2S lines (no pull on them: the speaker tones check them), and the battery charge path. If every 10 k net reads `WEAK PULL` at once, suspect U1's internal pulls (the firmware assumes the datasheet's 45 kΩ) rather than every resistor; report it.

Safe for the board: pins are driven only at U1's weakest drive strength, for microseconds (PWR_WAKE a few milliseconds, like a short press of SW5), and never against a net that something holds. The charger's EN1/EN2 pins are never driven: changing them would change the charger's input limit.

## Bench checks

| Press | Screen | Speaker |
|---|---|---|
| Flap left (SW1) | left flap tile, count, background colour | left, 880 Hz |
| Flap right (SW2) | right flap tile | right, 880 Hz |
| DART left (SW3) | left DART tile | left, 660 Hz |
| DART right (SW4) | right DART tile | right, 660 Hz |

- Chip revision v3.x in the boot log; PSRAM 32 MiB found; flash ID of the W25Q512JV (64 MiB).
- Draws and VSYNC near 59, no late frames; the sweep moves smoothly; the stamp is upright with correct colours.
- Backlight even on both halves of the screen (the panel has two LED strings, both on J1 pins 39–40).
- Charging: with a cell and USB-C, CHG reads charging; unplug USB and the board runs from the cell.

## Power budget on USB

A 500 mA USB port (a computer, or a USB-A cable) gives the BQ24074 at least 450 mA at 4.4 V, 1.98 W. At Espressif's worst-case 380 mA design provision for the chip, flash and PSRAM, plus the panel logic, that leaves about 19 % backlight with no cell to help. The firmware therefore caps the backlight at 15 % on such a source. The cap lifts only for a cell that can supplement: the charger running a charge cycle, no battery fault, and a valid reading of at least 3.5 V for 2 s (it returns below 3.4 V, when charging stops, on a fault or a failed reading). CHG low alone does not lift it: CHG is also low in pre-charge, when the cell is below 3.0 V. With the battery, or a USB-C charger offering 1.5 A or 3 A, there is no cap. For a first power-up without a battery, the 15 % cap keeps the board inside a 500 mA supply.

Audio does not fit in what is left (about 0.09 W after the 3.3 V rail and the capped backlight: the two MAX98357A idle at about 21 mW between them and, at 12 dB gain, can clip into 4 Ω speakers), so from R9 the amplifiers are held in shutdown whenever the backlight cap is on: no sound on a 500 mA source until a cell qualifies, or on a 1.5 A / 3 A USB-C charger or the battery alone. The log says `audio muted (USB below 1 A, no qualified cell)`.

Only a calibrated battery reading drives these decisions. If the chip has no ADC calibration in eFuse, the log says `battery reading uncalibrated`; the voltage is still shown (`battery_approx`), but the board then behaves as with a failed reading: no low-battery switch-off (the pack's protection board still cuts off), the USB cap and mute stay on, no charge suspend.

## Battery

Use a protected 1-cell Li-ion/LiPo of 1000 mAh or more (503450 about 1000 mAh, 703450 about 1500 mAh; up to 34 × 50 × 7 mm) on a 2-pin JST PH plug, pin 1 (red) = BAT+. The BQ24074 charges at 0.49 A nominal, 0.55 A at most (R412 1.8 k): 0.55 C on 1000 mAh. Its safety timer ends a charge after 4–6 h (TMR open); a 1500 mAh cell finishes inside it. The board does not sense cell temperature (TS is a fixed 10 k): the pack's own protection board is the only cell-level protection.

## If the display stays dark

Read the PANEL line and the `display failed at …` stage first:
- Before "panel probe on DSI lane 0": D-PHY rail, reset gate, backlight PWM, DSI bus, DBI channel or driver setup.
- `NO ANSWER ON DSI LANE 0` (stage "panel probe on DSI lane 0"): the panel did not answer, so the bring-up stopped there instead of hanging. The tail is not seated, not straight, or upside down in J1 (contacts must face up, away from the board); or the D0 pair (U1 pads 39/40 to J1), the panel supplies or LCD_RESX (Q1, R308) is at fault. The line names the step that got no answer and any error flags.
- Init completes but nothing shows: check that the backlight is lit (a faint image under a torch means the panel works and the backlight does not). LCD_LED_A should be about 20–24 V with the panel connected.
- Image present but rolling or torn: timing; the values are in `slim4_panel_cfaf.h` (from Crystalfontz's Linux mode).
