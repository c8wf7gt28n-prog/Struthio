# Electrical and land-pattern review of PCB R21 → R22

The R21 netlist was checked pin by pin against the datasheets: Espressif ESP32-P4 datasheet v0.7, the ESP32-P4 hardware design guidelines, the ESP32-P4-Function-EV-Board schematic v1.52, and the TI, Analog Devices and Winbond part datasheets. There is no schematic, so the review works from the board's own netlist. Every footprint was then compared with the KiCad 7 library footprint for its package (`scripts/fpcmp.py`).

## Verified correct (no change)

| Block | What was checked | Result |
|---|---|---|
| ESP32-P4NRW32X | Ordering code X = chip revision v3.x. Every power pin connected, including pin 54 VDD_HP_1 (v3). VDDO_4 unused (defaults to 0 V). | OK |
| Core supply | TLV62569 (SOT-23-5: EN, GND, SW, VIN, FB) driven by EN_DCDC/FB_DCDC. 499 k / 499 k + 22 pF populated, as v3 requires. | OK |
| Boot | GPIO35 10 k pull-up + BOOT button to GND. GPIO36 pull-up (joint download when BOOT is held). GPIO34 pull-down (JTAG from USB-Serial-JTAG). GPIO37/38 are "any value" for both boot modes. | OK |
| Reset | TPS3808G33 (RESET, GND, MR, CT, SENSE, VDD): SENSE on 3V3, 10 k pull-up on CHIP_PU, 1 µF, MR on the RESET button. | OK |
| Flash | W25Q512JV (3.3 V) on VDDO_FLASH (3.3 V default). Powers up in 3-byte mode, so it boots as 16 MB with no special support. | OK |
| MIPI / USB PHY | REXT 4.02 k; VDDO_3 → VDD_MIPI_DPHY 2.5 V; VDD_USBPHY from 3V3 through 0 Ω (v3 needs no DP pull-down). | OK |
| Charger | BQ24074: pin 4 CE to GND (charging enabled); EN1 10 k to 3V3, EN2 10 k to GND → 500 mA USB mode once 3V3 is up, 100 mA before (the TPS63070 starts within that). ILIM 1.5 k ≈ 1.0 A; ISET 3.6 k ≈ 250 mA charge; ITERM 3.3 k; TMR 47 k; CHG/PGOOD 100 k pull-ups to GPIOs. OUT regulates to 4.4 V. | OK |
| 3.3 V | TPS63070: pin 1 PS/SYNC high (power save), EN through 100 k from SYS_RAW (always on), VSEL (15) to GND, FB2 open, VAUX 100 nF. FB 470 k / 150 k with VFB 0.8 V → 3.31 V. | OK |
| Panel LDOs | TLV75518 / TLV75528 (DBV: IN, GND, EN, NC, OUT), EN tied to IN. | OK (rails depend on the panel, see Open) |
| Backlight | TPS61165 SOT-23-6 (VIN, CTRL, SW, GND, COMP, FB): CTRL on BACKLIGHT_PWM (100 k pull-down, off at reset); LED string between D2 and FB; R309 24.9 Ω → 8 mA. | Topology OK; current depends on the panel |
| LCD reset | 2N7002 (G, S, D): gate pulled up, so the panel is held in reset until firmware drives GPIO10 low. RESX pulled up to LCD_1V8. | OK (firmware: GPIO10 low releases reset) |
| USB-C | TUSB320LAI in GPIO mode (ADDR open), PORT to GND = sink, EN_N low. Presents Rd with no power, so a USB-C charger works on a dead cell. VBUS_DET through 470 k + 430 k = 900 k. OUT1/OUT2 (current advertisement) to GPIO43/GPIO17 with pull-ups. TPD2EUSB30 0.7 pF on D+/D−. PESD5V0S1UL on VBUS. | OK |
| Audio | MAX98357A (TQFN-16: DIN, GAIN_SLOT, GND, SD_MODE, NC, NC, VDD, VDD, OUTP, OUTN, GND, NC, NC, LRCLK, GND, BCLK) ×2, sharing BCLK/LRCLK/DOUT. GAIN_SLOT to GND = 12 dB. SD_MODE: left through 2 k ≈ 3.2 V (left channel); right through 100 k + 110 k with the internal 100 k ≈ 1.06 V (right channel); 100 k pull-down holds both off at reset. VDD from SYS_RAW (≤ 4.4 V). | OK |
| Battery sense | 100 k / 33 k divider: 4.2 V → 1.04 V on GPIO16 (ADC capable); about 32 µA drain. | OK |
| Buttons | D2LS and B3U to GND with 10 k pull-ups. The power button is on GPIO0 (LP domain, wakes from deep sleep). | OK |

## Fixed in R22

| Severity | Finding | Fix |
|---|---|---|
| **Would not work** | U11/U12 TPD2EUSB30 are 1 × 1 mm DRT parts on a SOT-23-sized proxy (pads 1.9 mm apart): they cannot be soldered. | KiCad `Texas_DRT-3`, routes redrawn |
| **Programming path** | USB-C data on the high-speed PHY. ROM download works there, but auto-reset, console and JTAG over the same cable do not. | USB-C to GPIO24/25 USB-Serial-JTAG |
| Mechanical | J3/J4/J5 JST SH proxies had no tab pads; J4's real body overhung the board edge. | Library footprints with tabs; J4 moved 2.7 mm inboard |
| Assembly yield | D1, Y1 and SW5–SW7 proxies did not match the parts' terminals. | Library land patterns |
| Tuning | Crystal load caps 18 pF for a 10 pF crystal (only affects accuracy: the P4 has no radio). | 12 pF C0G |

Land-pattern audit of the rest, against KiCad 7 library footprints (worst pad-centre offset / largest pad-size difference): 0402 ×117 and 0603 ×6 ≤ 0.03 / 0.10 mm; 0805 ×9 0.05 / 0.15 mm; SOT-23-5/6 0.05 mm with pads 1.0 mm long (library 1.33; they still cover the leads); SOT-23 0.15 mm; BQ24074 VQFN-16 0.06 mm; MAX98357A TQFN-16 0.01 mm; TUSB320 X2QFN-12 and W25Q WSON-8 exact. U1 (Espressif pattern), U4 (TI RNM0015A), J1, J2, the D2LS switches, the inductors and D2 have no matching KiCad library footprint. They were built from the manufacturers' patterns, as each footprint's description records.

## Open — needed before ordering

1. **Display panel (blocker).** No part number or drawing exists for the panel. J1 (20-pin 0.5 mm FH12, bottom contact), its pin order, the 2.8 V / 1.8 V rails, two MIPI lanes and the 8 mA backlight were all assumed. The panel must be chosen, with its datasheet (FPC pinout, contact side, supply rails, LED string voltage and current, driver IC), and J1 made to match it before the board is ordered.
2. **Case** (after the board works): re-run the clearance checks for J4's new position and the real JST body depth.

## Bring-up with one USB-C cable

1. Before plugging in the cell: connect USB-C and measure SYS_RAW at C411 (≈ 4.4 V), 3V3 at C414 (3.31 V) and VDDO_FLASH at C202 (3.3 V). All are 0805/0402 capacitors on the back, ground on the other pad.
2. For the first flash, hold BOOT (SW7), tap RESET (SW6) and release BOOT. The P4 enumerates as "USB JTAG/serial debug unit" (303a:1001), and the ROM log on the port shows `waiting for download`.
3. `idf.py -p <port> flash monitor`. Use an ESP-IDF release that supports ESP32-P4 chip revision v3.x and select v3 as the chip revision in menuconfig. After the first flash, esptool resets into download mode by itself; the buttons are only needed again if an app disables or reassigns GPIO24/25.
4. 1V1_HP at C135 rises to about 1.1 V only once firmware runs (EN_DCDC stays low in download mode, by design).
5. JTAG: `idf.py openocd` over the same cable (GPIO34 strap low selects USB-Serial-JTAG).
