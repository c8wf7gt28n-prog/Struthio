# First firmware boot on PCB R24

This image is a board bring-up build for the R24 main board (R23 has the same pins; the log and the boot stamp say R23) with the Crystalfontz CFAF7201280A0-050TN plugged into J1 (`hardware/slim4/LAYERS/01_PCB/DISPLAY_PORT.md` shows how the tail folds in). It has not run on hardware yet.

## Before power

- Panel tail fully in J1, latch closed, contacts up (away from the board). Battery on J3 with pin 1 (red) = BAT+: check it. A reversed pack is blocked while the board runs from it; with USB connected it is not disconnected: the design analysis predicts the charger's 4–11 mA test current (not tested), and the screen shows `BATTERY REVERSED - UNPLUG`. Never plug in a reversed pack on purpose. Speakers on J4 (left) and J5 (right).
- First power from USB-C on a current-limited supply if you can (5 V, 500 mA limit). The board draws well under that until the backlight comes on.

## Expected behaviour

1. Over the USB-C port (USB-Serial-JTAG), the ROM banner and then every app line: app information with the chip revision, PSRAM, `firmware=slim4_platform version=…` and `target=ESP32-P4 board=SLIM4 R23`. The second-stage bootloader's own lines (partition table) go to UART0 only, whose pins are not brought out.
2. The BSP requests 2.5 V from P4 LDO channel 3 for the MIPI D-PHY, holds the panel in reset (GPIO10 high), sets up the backlight PWM (off), opens the 2-lane DSI bus at 1 Gbit/s and installs the ILI9881C driver with the Crystalfontz init sequence. The driver logs the panel ID bytes it reads back.
3. It releases reset (GPIO10 low), waits 120 ms, sends the init sequence, turns the display on, draws the boot stamp (navy, "SLIM4 / R23"), and only then turns the backlight on at 45 % (about 33 mA), or at 15 % on USB below 1 A until a cell qualifies (`backlight limited to 15 %` in the log).
4. The log line `ILI9881C two-lane DSI initialized: 720x1280 RGB565, 78 MHz pixel clock (59 Hz)` confirms the controller side.
5. The stamp's bottom line changes from `STARTING` to `VERIFIED` (or `SERVICE MODE`) once the controls, framebuffer and audio worker pass (or fail) their software checks. That label does not claim the buttons, speakers or panel were measured.
6. The diagnostic loop redraws a moving sweep at the panel's 59 Hz, lights a tile and counts presses for each of the four controls, and logs every input edge. Each press plays a short tone at 20 % volume on its side (flaps 880 Hz, DART 660 Hz).
7. The screen shows firmware draws per second, DPI VSYNC events per second, the longest render-and-submit time, the frame number and late frames. Readings of 58–62 are cyan, others red, zero gold while starting.
8. At start, the power log line gives the battery voltage, USB-C current advertisement, charging state, the charger input limit, the backlight cap and the die temperature; the policy then re-reads them every 0.5 s (charger input 1.07 A only when USB-C advertises 1.5 A or 3 A; above 75 °C die temperature charging is suspended, but only with a qualified cell above 3.6 V, since suspend also takes the system off USB). On the battery, 2 s below 3.3 V switches the board off whatever the button does. Holding the power button 2 s switches off (deep sleep); pressing it wakes the board. If the battery reading fails, the log says so: there is then no low-battery switch-off (the pack's own protection still cuts off) and the backlight stays capped on USB below 1 A.

A display error is logged with the stage that failed; the app keeps running so the serial diagnostics stay available.

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

## If the display stays dark

Read the `display failed at …` stage first:
- Before "panel initialization commands": D-PHY rail, reset gate, backlight PWM, DSI bus, DBI channel or driver setup.
- Panel ID bytes all zero or the init commands time out: the tail is not seated, not straight, or upside down in J1 (contacts must face up, away from the board).
- Init completes but nothing shows: check that the backlight is lit (a faint image under a torch means the panel works and the backlight does not). LCD_LED_A should be about 20–24 V with the panel connected.
- Image present but rolling or torn: timing; the values are in `slim4_panel_cfaf.h` (from Crystalfontz's Linux mode).
