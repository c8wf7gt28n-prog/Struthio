# STRUTHIO SLIM4 PCB R23 — release gates

**Order files ready.** `CHECKS/build_builder_packs.py` writes the JLCPCB order (Gerbers, drill, BOM, CPL, README) into `1_PCB_FABRICATION/`. The R22 gates (`REFERENCES/PCB_R22/RELEASE_GATES_R22.md`) stay closed; R23 closes the three it left open about the panel and the battery.

## Closed

| Gate | How R23 closes it |
|---|---|
| Schematic-level review | R22's pin-by-pin review (`ELECTRICAL_REVIEW_R22.md`) covers every part R23 kept. The R23 changes were checked against their datasheets: AO3401A reverse-polarity switch (body diode, V<sub>GS</sub> ±12 V, 50–85 mΩ at a 3–4.2 V cell), BQ24074 ISET (1.8 k → 494 mA), TPS61165 sense (2.7 Ω → 74 mA, inside the boost's 84 mA worst case at 24 V), ESP32-P4 DSI and GPIO pads (pin table, chip revision v1.3 datasheet section 2.2; pad 54 is VDD_HP_1 on v3). |
| Panel connection | The Crystalfontz pin table is public. J1's 40 pads carry it pad for pad (convergence check N1, every pin's position and net). No adapter flex. |
| MIPI-DSI signal integrity | 2 lanes at 1 Gbit/s. P = N within 0.01 mm on every pair; flight-time skew ≤ 8 ps within a pair and ≤ 39 ps clock to data, counting the outer-layer and In3 delays separately. Outer-layer pairs are about 90–108 Ω differential on JLCPCB's 1.2 mm 6-layer stackup (`README_PCB_LAYER.md`, edit 15). |
| Battery polarity | J3 is the keyed JST PH plug of hobby 1-cell packs, pin 1 BAT+. A pack wired the other way round: with no USB Q2 blocks it; with USB the steady-state analysis predicts only the charger's 4–11 mA short-circuit test current (≤ 64 mW in Q2, BAT_PLUS ≥ 0 V; not tested) and the firmware shows BATTERY REVERSED (`README_PCB_LAYER.md`, edit 12). Open: verify the pack's pin polarity before assembly; never test with a reversed lithium pack. |
| USB power budget | On a 500 mA USB source the BQ24074 passes at least 450 mA at 4.4 V (1.98 W). The 3.3 V rail at Espressif's 380 mA design provision plus the panel logic takes 1.55 W, which leaves 14 mA (19 %) of backlight without a cell to supplement. The firmware caps the backlight at 15 % on 500 mA USB unless a qualified cell can supplement (charging, no fault, a valid reading ≥ 3.5 V for 2 s; host-tested, `firmware/slim4/tests/host`); USB-C 1.5 A / 3 A (input limit 1.07 A) and the battery have no cap. |
| Footprints vs orderable parts | New footprints come from the KiCad 7 library for the exact parts: Hirose FH12-40S land (common to FH12 and FH12A), JST PH S2B-PH-SM4-TB, Molex PicoBlade 53261-0271, SOT-23. All parts have LCSC numbers. |
| Production DRC, Gerbers, BOM, CPL | KiCad 7.0.11 DRC 0 / 0 / 0 with the board's own net-class rules (`NATIVE_KICAD_DRC.txt`); zones refilled; the board rebuilds copper-identical from R22 (`R23_FROM_R22/build_r23.sh`). Run JLCPCB's own DFM check on upload. |
| Firmware GPIO map | `FIRMWARE_PINMAP.md`; `firmware/slim4/tools/check_pinmap.py` checks the firmware's pins against this board. |

## Open

1. **U1 stock.** ESP32-P4NRW32X had no stock at JLCPCB, LCSC, DigiKey or Mouser on 2026-10-07. See *Sourcing U1* in `README_PCB_LAYER.md`.
2. **Rotations in JLCPCB's placement preview.** Check pin 1 of every IC, diode, connector and the crystal before confirming assembly. J1 is a top-contact socket on the front, mouth toward the board's bottom edge.
3. **Panel support.** The panel sits over the board's front on its folded tail and overhangs the top edge by 13.6 mm; it needs 2.3 mm over J1 and about 3.3 mm at the fold. Until the case pass, mount it on 3–4 mm foam spacers.
4. **Bring-up on the first boards** (no case needed): rails (SYS_RAW, 3V3_SYS, 1V1_HP, LCD 1.8 / 3.0 V, backlight boost) on a current-limited supply; USB-Serial-JTAG enumerates and `idf.py flash monitor` works; flash and PSRAM tests; charger with a cell (and a reversed cell: the board must stay off); audio on both amplifiers; panel init and backlight (`firmware/slim4/docs/FIRST_BOOT.md`).
