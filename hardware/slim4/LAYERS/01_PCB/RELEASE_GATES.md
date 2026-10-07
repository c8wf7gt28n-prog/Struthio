# STRUTHIO SLIM4 PCB R22 — release gates

**Order files ready.** `CHECKS/build_builder_packs.py` writes the JLCPCB order (Gerbers, drill, BOM, CPL, README) into `1_PCB_FABRICATION/`. The R21 review hold (`REFERENCES/PCB_R21/RELEASE_GATES_R21.md`) is closed as below.

## Closed

| R21 gate | How R22 closes it |
|---|---|
| 1. Schematic and ERC | There is no schematic. The board netlist was reviewed pin by pin against the ESP32-P4 datasheet, the hardware design guidelines, the Function-EV-Board schematic and every IC datasheet (`ELECTRICAL_REVIEW_R22.md`). |
| 2. ESP32-P4 power, boot, USB, flash; power tree | Same review: v3 DCDC network (499 k / 499 k + 22 pF), strapping pins, flash, crystal load (C203/C204 → 12 pF), supervisor, charger, regulators, backlight (39 mA, 50 V output capacitor). USB moved to USB-Serial-JTAG. |
| 3. MIPI-DSI and USB signal integrity | DSI runs are 29–40 mm with ≤ 5.8 mm in-pair skew at ≤ 1 Gbit/s per lane; USB is full speed (12 Mbit/s). Impedance control is not needed at these lengths and rates; bring-up confirms it. |
| 4. Footprints vs orderable parts | Every footprint compared with the KiCad library or manufacturer land (`R22_FROM_R21/fpcmp.py`, the inductor and diode datasheets); 13 lands replaced (U11, U12, J3–J5, D1, Y1, SW5–SW7, L1–L3). All 166 parts have LCSC numbers; all in stock at JLCPCB on 2026-10-07 except U1. |
| 5. Panel, battery, speakers | Panel chosen (`DISPLAY_PORT.md`); battery on a 2-pin JST SH (any protected cell); speakers on JST SH 2-pin (J4/J5). |
| 6. Production DRC, Gerbers, BOM, CPL | KiCad 7.0.11 DRC 0 / 0 / 0 (`NATIVE_KICAD_DRC.txt`); plotted masks have no opening at any via; BOM 50 lines / CPL 166 placements. Run JLCPCB's own DFM check on upload. |
| 7. Firmware GPIO map | `FIRMWARE_PINMAP.md`. |

## Open

1. **U1 stock.** ESP32-P4NRW32X had no stock at JLCPCB, LCSC, DigiKey or Mouser on 2026-10-07. See *Sourcing U1* in `README_PCB_LAYER.md`.
2. **Rotations in JLCPCB's placement preview.** Check pin 1 of every IC, diode, connector and the crystal before confirming assembly.
3. **Display flex pin table.** The panel's 31-pin order comes from Startek's datasheet; `LAYERS/04_DISPLAY_FLEX` generates the flex when it is filled in.
4. **Bring-up on the first boards** (no case needed): rails (SYS_RAW, 3V3_SYS, 1V1_HP, LCD 1.8 / 3.0 V, backlight boost) on a current-limited supply; USB-Serial-JTAG enumerates and `idf.py flash monitor` works; flash and PSRAM tests; charger with a cell; audio on both amplifiers; panel init and backlight once the flex is in.
5. **Battery polarity.** The board has no reverse-polarity protection: check each cell's lead (pin 1 BAT+) before plugging it in.
