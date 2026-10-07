# PCB R22 — ready to order

This folder holds the R22 board: R21 plus the fixes from the electrical and land-pattern review in `ELECTRICAL_REVIEW_R22.md`. It sits beside the `slim4` package, which stays the checksummed R26 set (case, film, studio on R21) until the case pass. In that pass R22 replaces R21 in the package and the case is refined around the real panel.

**Status: ready to order.** `ORDER/STRUTHIO_SLIM4_R22_PCB_ORDER.zip` holds everything JLCPCB needs (Gerbers + drill, BOM, CPL) and a README with the exact order options.

The display is the Startek KD047HDFID001 (4.7 in 720 × 1280 IPS). J1 is a fixed display port, and one custom flex maps it to the panel's cable. The flex is designed when Startek's datasheet with the pin definition arrives, so the main board does not depend on that pinout (`DISPLAY_PORT.md`). Firmware pin map: `FIRMWARE_PINMAP.md`.

## What changed from R21

| # | Change | Why |
|---|---|---|
| 1 | USB-C D+/D− now go to GPIO25/GPIO24 (USB-Serial-JTAG) instead of the USB 2.0 high-speed PHY pins 50/49. The existing inner-layer pair is kept; D− reaches pad 52 inside the pad ring, and D+ drops through one new via to pad 53. Two front-side tracks (FB_DCDC, CHIP_PU) are jogged around the via, and a redundant In3 GND tie is removed. Nets renamed `USB_JTAG_DP/DM`. | One USB-C cable then gives flashing with auto-reset (`idf.py flash`), the ROM boot log, the app console and JTAG debugging, all in ROM with no firmware support needed. On the high-speed port, auto-download stops working as soon as an app uses USB, and the console and JTAG need extra work. |
| 2 | U11, U12 (TPD2EUSB30): KiCad `Texas_DRT-3` footprint; local D+/D− and CC1/CC2 routes redrawn across the pads, GND to a via. | The R21 proxy was SOT-23 sized (pads 1.9 mm apart). The part is the 1 × 1 mm DRT package and could not have been soldered. |
| 3 | J3, J4, J5 (JST SH): KiCad `JST_SH_SM0xB-SRSS-TB` footprints with both solder tabs. J4 moved 2.7 mm inboard. | The proxies had no tab pads, so the connectors would have been held only by their signal pins. With the real body depth, J4's tabs fell off the board edge. |
| 4 | D1 (PESD5V0S1UL, SOD-882), Y1 (Lucki 3225 crystal), SW5–SW7 (Omron B3U-1000P): KiCad library land patterns; nearby GND tracks moved clear of the larger pads. | The proxies' pads did not match the parts' terminals (D1 pads 0.2 mm off each end; B3U pads short of the terminals). |
| 5 | C203, C204: 18 pF → 12 pF C0G (0402CG120J500NT, LCSC C1547, JLC Basic). | Y1's load capacitance is 10 pF: 12 pF in series pairs to 6 pF, plus about 4 pF of pin and trace stray. |
| 6 | C603 moved 0.15 mm. | Courtyard clear of J3. |
| 7 | R309 24.9 Ω → 5.1 Ω (0603WAF510KT5E, C25197); C309 1 µF 25 V → 1 µF 50 V (CL10A105KB8NNNC, C15849). | Backlight set to 39 mA for the chosen panel's two 7-LED strings (40 mA rated). The boost's open-LED limit is 38 V, so the output capacitor must survive it when no panel is plugged in. |
| 8 | U6 TLV75528 → TLV75530 (C507268); net LCD_2V8 → LCD_VCI_3V0. | Panel analog supply 3.0 V: mid-range for ST7703 / ILI9881C / ST7701S panels, closer to the panel's 3.3 V rating. |
| 9 | J3 battery socket: JST SH 3-pin → 2-pin (the speakers' part, SM02B-SRSS-TB, C160402): pin 1 BAT+, pin 2 GND. New R424 10 kΩ (C25744) from the charger's TS pin to GND; the NTC route is cut back to it (net BAT_NTC → BQ_TS). | Any 2-wire cell plugs in (on a JST SH 1.0 2-pin plug), instead of only a cell with a 10 k thermistor lead. The BQ24074 datasheet specifies 10 k to ground when no thermistor is used. Over-charge, over-discharge and short-circuit protection stay on the cell's own protection board; charging no longer pauses for cell temperature. |

KiCad 7.0.11 DRC on R22: **0 violations, 0 unconnected pads, 0 footprint errors** (`board/DRC_R22.rpt`). Board outline, stackup, every other part and the J1/J2 positions are unchanged, so CASE R12 still fits. Exceptions: J4's body now sits 2.7 mm further inboard, and the J3/J4/J5 bodies are the real JST depth (the case pass after the board works will re-run the clearance checks).

## Rebuild

`scripts/build_r22_order_pack.py <folder>` writes the JLCPCB order files from `board/` (run it with the package's pinned Python environment, which has matplotlib, and KiCad 7.0.x on the machine).

`scripts/build_r22.sh` regenerates the R22 board from the unchanged R21 board, one scripted edit at a time, then refills zones and runs DRC. The result is copper-identical to `board/SLIM4_R22.kicad_pcb`. It needs KiCad 7.0.x with its Python module, and the `kicad-footprints` 7.0.x library in `/usr/share/kicad/footprints`. `scripts/fpcmp.py` is the land-pattern audit: it compares each board footprint with the KiCad library footprint for its package.
