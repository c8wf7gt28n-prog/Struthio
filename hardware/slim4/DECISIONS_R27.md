# R27 decisions

R27 replaces PCB R21 with PCB R22 and adds the display cable. These choices were made with the owner in the R22 sessions; each one names the file that carries it. `DECISIONS_R26.md` still holds for everything not listed here.

| # | Decision | Why | Supersedes | Where it lives |
|---|---|---|---|---|
| 1 | **Order PCB R22, not R21.** R22 is R21 with the electrical and land-pattern review fixed (11 scripted edits, copper-identical rebuild from R21). | R21 could not have worked as ordered: 1 × 1 mm USB ESD parts on SOT-23 pads, connectors without solder tabs, proxy pads short of several parts' terminals, USB on the high-speed PHY, which auto-download does not use. | R26 #2 ("keep PCB R21") | `LAYERS/01_PCB/`, `ELECTRICAL_REVIEW_R22.md` |
| 2 | **USB-C to the ESP32-P4's USB-Serial-JTAG** (GPIO24 D−, GPIO25 D+). | One cable gives flashing with auto-reset, the boot log, the console and JTAG, all from ROM. | — | R22 edit 1 |
| 3 | **Display: Startek KD047HDFID001**, 4.7 in 720 × 1280 IPS, ST7703, 450 cd/m², run as 2-lane DSI. Backlight 39 mA, panel VCI 3.0 V. | Its active area is the one the case was drawn around; highest resolution in the size; ST7703 has an Espressif driver. | the HOTHMI 540 × 960 panel assumed since R3 | `LAYERS/01_PCB/DISPLAY_PORT.md` |
| 4 | **J1 is a fixed display port; one custom flex maps it to the panel.** FH26W-31S on the flex for the panel tail, 20 gold fingers into J1, 2-layer polyimide, 70 mm. | A pin-order mistake then costs a cheap flex, not the main board. | the "extension FPC" gate (H4) | `LAYERS/04_DISPLAY_FLEX/` |
| 5 | **Battery: any protected 1-cell pack on a JST SH 2-pin plug** (J3 pin 1 BAT+, pin 2 GND); a fixed 10 k on the charger's TS pin. | Cheapest and most versatile: no thermistor wire needed. The pack's own protection board covers over-charge, over-discharge and short circuit. | R26 #13 (3-pin cell with NTC) | R22 edit 9 |
| 6 | **JLCPCB stock substitutions** (same value and package) and **Sunlord's recommended inductor lands**. | Every line except U1 in stock at JLCPCB on 2026-10-07; L1–L3 proxy pads were short of or narrower than the terminals. | — | R22 edits 10, 11 |
| 7 | **U1 sourcing**: pre-order ESP32-P4NRW32X through JLCPCB Global Sourcing, or consign v3 chips from an Espressif-authorised source. Never substitute ESP32-P4NRW32 (revision v1). | U1 had no stock anywhere on 2026-10-07; the board's power network is for chip revision v3. | — | `LAYERS/01_PCB/README_PCB_LAYER.md` |
| 8 | **Plastic later.** The case pass for the chosen panel and the R22 connectors comes after the board, panel and cable are in hand. | The owner's order of work. | — | `PRODUCTION_GATES.md`, case-pass list |
