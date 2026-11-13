# SLIM4 PCB R28 — bring-up procedure

The first boards are measured in this order: each phase passes before the next, so a fault is found before power reaches what it could damage. Every step gives the probe point (a part pad), the expected value and what a wrong reading means. Compiled from the five pre-order reviews (power, ESP32-P4 core, display, audio/controls/USB, firmware), checked against the R26 netlist and the parts' datasheets, updated for R27's added parts (C138, C139, C140, D2 60 V, R424 at U10, R401/R402 22 Ω, silkscreen labels), and for R28's radio (U15 RAK3172-SiP and its parts: rows B8–B9, C14, D13 and phase I, after the stress tests).

Tools: DMM; bench supply with current limit (5 V, and a second one as a stand-in cell); oscilloscope (≥ 100 MHz; ≥ 1 GHz differential for the optional DSI step); thermal camera or thermocouple; a PC with ESP-IDF v6.1 or esptool. For phase I: a second R28 board, and a 915 MHz antenna with a U.FL plug for each. Firmware R13 or later (`firmware/slim4`; R12 has no radio driver), which runs the self-test at every boot, starts the display in the in-spec 560 Mbit/s profile and opens a command console on the USB-C port (`help`).

## Phase A — before ordering (no board needed)

| # | Check | Pass | If not |
|---|---|---|---|
| A1 | A sample Crystalfontz CFAF7201280A0-050TN tail in a loose Hirose FH12A-40S-0.5SH(55): with the tail folded as in `DISPLAY_PORT.md`, its contacts face the connector's contacts and pin 1 lands on J1's west pad | Matches | A mirrored J1 loses every board: stop and fix the footprint |
| A2 | Each battery pack to be used, in a loose JST PH S2B socket: which socket pin the red wire lands on | Red on pin 1 (J3.1 = BAT+) | Re-pin the pack's housing (Q2 blocks a reversed pack only without USB) |
| A3 | JLCPCB placement preview: D1 cathode on USB_VBUS; D2 cathode on LCD_LED_A; C138, C139 and C140 on the back beside U1 and C309; pin 1 of U1, U2, U8, U9, U10, U13; J1 mouth toward the board's bottom edge; SW1–SW4 (symmetric boss holes allow a 180° error); J2's four shell legs soldered | All as on the board drawings | Correct the rotation in the CPL before paying |
| A4 | Order notes: no-clean (the B3U and D2LS switches must not be washed); impedance control on the DSI pairs; U1 revision v3.1 preferred (marking ending G or H) | Stated | — |

## Phase B — unpowered (DMM)

| # | Probe | Expected | Wrong reading means |
|---|---|---|---|
| B0 | Visual: the silkscreen + and − at J3 sit level with J3 pin 1 (BAT+) and pin 2; D2 marked as the 60 V part (STPS1L60ZFY); R401/R402 22 Ω (not 0 Ω links); R424 beside U10 | As listed | The wrong part: compare the BOM line with what was placed |
| B1 | USB_VBUS (C409.1) to GND; diode test with + on VBUS | > 50 kΩ; no diode drop (with probes reversed about 0.6–0.7 V) | Low, or a diode drop with + on VBUS: D1 reversed or a short at U10 pin 13 or C409 |
| B2 | SYS_RAW (C411.1), 3V3_SYS (C414.1 / C101.1), 1V1_HP (C135.1 / C103.1), BAT_PLUS (C412.1), VDDO_FLASH (C104.1), VDDO_PSRAM (C113.1), VDDO_MIPI (C108.1), CHIP_PU (C136.1) to GND | Each > 50 Ω once the capacitors have charged (1V1_HP reads lowest) | < 5 Ω: a solder bridge (U1's 0.35 mm pads, U3, U4, U10, U7) or a shorted capacitor. Do not power |
| B3 | LCD_LED_A (C309.1 / C140.1 / J1.38) to GND | > 1 MΩ | C309, C140 or D2 short: fix before power (a 38 V node) |
| B4 | J1.39/40 to GND (R309); J1.14 to J1.19 (R307) | 2.7 Ω; 10 kΩ | Open: R309 or R307 missing, or a J1 joint |
| B5 | Each DSI pin of J1 (28, 29, 31, 32, 34, 35) to its neighbouring GND pin | > 100 kΩ | Low: a bridge at J1's 0.5 mm pitch |
| B6 | CC1 and CC2 to GND at J2 | about 5.1 kΩ each (TUSB320 Rd, present unpowered) | Open: a USB-C to USB-C charger will give no VBUS (U13 missing or unsoldered) |
| B7 | Diode test J3.1 (+) to BAT_PLUS (C412.1) | 0.6–0.8 V (Q2 body diode) | Q2 rotated or the wrong part |
| B8 | Visual: U15 (RAK3172-SiP) pin-1 corner as on the silkscreen, no skew on its 0.6 mm pads; R701 and R704 fitted (0 Ω); C724 and C725 empty; J701 square on its pads | As listed | Rotated U15: do not power. C724/C725 fitted: the RF match is detuned (remove them) |
| B9 | RADIO_3V3 (C701.1) to GND; RADIO_3V3 to 3V3_SYS across R701 | > 50 Ω once charged; < 0.5 Ω | Low: a bridge under U15 or at L701 / the beads. Open R701: the radio is unpowered (the self-test says NOT FITTED) |

## Phase C — USB power, no cell, no panel (bench 5 V into J2, limit 100 mA, then 500 mA after C3)

| # | Probe | Expected | Wrong reading means |
|---|---|---|---|
| C1 | USB_VBUS at C409.1; supply current | 5.0 V; < 30 mA before 3V3 starts | Current limit: a short behind U10 |
| C2 | PGOOD at R421.2 | < 0.4 V about 1 ms after VBUS | High: U10 sees no valid input (pin 13 joint) |
| C3 | SYS_RAW at C411.1 | 4.40 V (4.30–4.50) | Low or oscillating: U10 current limit, OUT short |
| C4 | 3V3_SYS at C414.1 and at U1 pad 9 (C101) | 3.31 V (3.22–3.44); ripple < 50 mV p-p | Wrong: R410/R411 (swapped gives 1.06 V), U4 or L1 joints. Stop |
| C5 | VDD_USBPHY at C112 | = 3V3 ±10 mV | 0 V: R403 open |
| C6 | CHIP_PU at C136.1 (scope, trigger on 3V3) | low for 12–28 ms after 3V3 passes 3.1 V, then an RC rise to 3.3 V | Never rises: 3V3 below U14's threshold, or SW6 / RESET_MR held |
| C7 | SW6 pressed and released | CHIP_PU < 0.3 V while pressed, low ≥ 12 ms after | No change: MR path open |
| C8 | Straps after reset: GPIO34 (R107.1), GPIO35 (R108.2), GPIO36 (R109.2) | < 0.3 V; 3.3 V; 3.3 V | GPIO35 low: SW7 stuck, the board always enters download mode |
| C9 | BQ_EN1 (R603.2) / BQ_EN2 (R604.1) | 3.3 V / 0 V | Both high = USB suspend |
| C10 | ITERM (R413.1) / TS (R424.1) | 0.24–0.26 V / 0.72–0.78 V | TS < 0.3 V or > 2.1 V: charging suspended (R424) |
| C11 | USB_VBUS_SENSE at U13.4; 3V3 at U13.12 | about 0.47 V; 3.3 V | ≈ 0: R416/R417 open, U13 never attaches |
| C12 | LCD_1V8 at C306.1 / LCD_VCI_3V0 at C308.1 | 1.78–1.82 V / 2.97–3.03 V | U5 / U6 rotated, swapped or missing |
| C13 | USB-C cable to the PC (data) | enumerates as 303a:1001 "USB JTAG/serial debug unit" in both plug orientations | Not at all: D+/D- route, R401/R402, U11, U1 pads 52/53. One orientation only: a row of J2 not joined |
| C14 | RADIO_3V3 at C701.1 | = 3V3_SYS ±20 mV | 0 V: R701 open or missing |

## Phase D — processor, flash and firmware

| # | Action / probe | Expected | Wrong means |
|---|---|---|---|
| D1 | Hold SW7, tap SW6, release SW7; ROM log on USB-C | `waiting for download` | Normal boot: GPIO35 not low at reset |
| D2 | `esptool chip_id` / `flash_id` | ESP32-P4 v3.x (v3.1 preferred); flash EF 40 20, 64 MB | v1.x: wrong part. FF FF FF / 00 00 00: flash wiring or VDDO_FLASH (in download mode VDDO_FLASH may read 0 V until esptool connects) |
| D3 | Flash firmware R12+ (`prebuilt/` or `idf.py flash`); then monitor | bootloader and app log on USB-C | Silent after the bootloader: watch D4–D6 |
| D4 | VDDO_FLASH at C202 / U2.8; VDDO_PSRAM at C113 | 3.18–3.35 V; 1.75–1.85 V | 0 V: U1 not running or a short |
| D5 | EN_DCDC at U3.1 with the app running | ≥ 1.2 V | Low: the core DC-DC is not enabled |
| D6 | 1V1_HP at C129 (pad 91) and C103 (pad 26) | 1.20–1.28 V DC (the chip trims about 1.25 V); never above 1.30 V | > 1.30 V: power down; check R104/R105/C134 and FB_DCDC. < 1.15 V: the FB network or plane drop |
| D7 | 1V1_HP ripple at C129 and C139, 20 MHz bandwidth, CPU + PSRAM busy | ≤ 50 mV p-p, trough ≥ 0.99 V | Larger: C138/C139 missing or open, or the FB_DCDC route (core review M1/M2) |
| D8 | FB_DCDC at R105.1 | about 0.6 V | 0 or 1.2 V: R104/R105 missing, swapped or open |
| D9 | The self-test lines (`SELFTEST …`, then `SELFTEST RESULT`), or console `report` | No FAIL. INFO lines as described in `firmware/slim4/docs/FIRST_BOOT.md` | Each FAIL line names the pad, the parts and where to look |
| D10 | Console `info` | chip v3.x, flash EF4020 64 MiB, PSRAM 32 MiB, reset reason | — |
| D11 | Reset by SW6, by the watchdog and by `reboot` | the app boots every time | Hangs after a reset that is not a power cycle: flash left in 4-byte mode |
| D12 | 40 MHz crystal: an XTAL-derived output on a counter (not a probe on Y1) | ±30 ppm | > 100 ppm or no start: C203/C204 or Y1 |
| D13 | The self-test's RADIO line, or console `radio` | `RADIO RAK3172 OK` with the SiP's firmware version (`RUI_…`) and its mode | NOT FITTED: nothing drives U1's RX (GPIO40, pad 81) after a reset: R701, RADIO_3V3, U15 pin 29. NO ANSWER TO AT: GPIO39 / pad 80 to U15 pin 30, BOOT0 (R702) or the SiP's firmware. RESET NOT SEEN: NRST, U1 pad 93 to U15 pin 44 |

## Phase E — display (power off, plug the panel tail into J1, latch closed)

| # | Action / probe | Expected | Wrong means |
|---|---|---|---|
| E1 | Boot; the log line `panel probe: …` and the PANEL line | `answered, ID 98 81 xx` | `NO ANSWER`: tail seating or orientation, D0 pair, LCD_RESX, panel supplies. The boot carries on without the display |
| E2 | VDDO_MIPI_2V5 at C108 / C109 (pads 41, 73) after the display init | 2.43–2.58 V | 0: LDO channel 3 not enabled, the DSI is dead |
| E3 | LCD_RESET_GATE at Q1.1 / LCD_RESX at J1.14 | before the release 3.3 V / < 0.05 V; after the release 0 V / 1.80 V | RESX 1.8 V while the gate is high: Q1 open; 0 V after the release: Q1 short, R307 open |
| E4 | The image, the self-test page's bars and 1-pixel lines; console `pattern checker`, `gradient`, `bars`, `white`, `red`, `green`, `blue` | clean: no sparkles, shifted rows or wrong colours; colours in order (safe profile, 560 Mbit/s, the default) | Wrong colours: RGB order. Nothing but the backlight: CLK or D1. Then `display fast`, `reboot` and the same patterns (1000 Mbit/s, above the ILI9881C's 2-lane limit): keep it only if they stay clean, otherwise `display safe` |
| E5 | LCD_LED_A at C309 (backlight on) | 19.8–24.0 V | ≈ SYS_RAW: open-LED protection latched (tail not seated, J1.38–40 joints) |
| E6 | LCD_LED_K at R309.1 with `bl 100` (allowed by the power cap) | 200 mV ±2 % (74 mA); about 90 mV at 45 % | Other: R309 wrong value |
| E7 | Current in each LED string (1 Ω in series, breakout) | 30–44 mA each, 74 mA in total | One above 40 mA: string imbalance; R309 3.0 Ω gives 67 mA in total |
| E8 | BL_SW at U7.3 (scope); ripple on C309 / C140 | 1.0–1.5 MHz, clean; < 0.2 V ripple | Erratic duty: output capacitance too low (C140 missing or open) |
| E9 | Optional, ≥ 1 GHz differential: DSI at J1 with video | about 200 mV differential HS, LP-11 between bursts | No HS on CLK or D1: open line |
| E10 | Console `panel` | `answered`, about 45 frames a second in the safe profile (59 in the fast one) | — |

## Phase F — controls, audio, USB-C

| # | Action / probe | Expected | Wrong means |
|---|---|---|---|
| F1 | Every control: the self-test pull lines PASS; console `gpio` reads 1 idle and 0 pressed; the diagnostic tiles light | as described | OPEN: switch or pull-up unsoldered. HELD: switch stuck, D2LS rotated, a bridge |
| F2 | AUDIO_SD_CTRL (R504), U8.4, U9.4 idle | 0 V | > 0.1 V: the amplifiers are not in shutdown |
| F3 | `tone left 1000 1000`, then `tone right …`: U8.4 / U9.4 during the tone | 3.1–3.3 V / 0.97–1.16 V | U9 > 1.25 V plays left; < 0.83 V plays (L+R)/2: R502/R503 values |
| F4 | Speakers on J4 (left) and J5 (right) | the tone only from the side asked | Swapped: J4/J5 or U8/U9 |
| F5 | Scope BCLK at U8.16 / U9.16, LRCLK pin 14, DIN pin 1 | 1.536 MHz, 48.000 kHz, clean edges, overshoot < 0.5 V | Ringing: lower the I2S pin drive strength |
| F6 | USB-C to USB-C charger, no cell: VBUS, SYS_RAW | 5.0–5.25 V within 1 s; 4.4 V | 0 V: no Rd (B6) |
| F7 | CC voltage in use; console `power` (USB-C advertisement) | default 0.25–0.61 V / 1.5 A 0.7–1.16 V / 3 A 1.31–2.04 V, and the console agrees | VBUS_DET or CC path |

## Phase G — battery and charging (a second bench supply as the cell on J3: 3.70 V, 1 A limit)

| # | Action / probe | Expected | Wrong means |
|---|---|---|---|
| G1 | BAT_CONN (J3.1) and BAT_PLUS (C412.1), no USB | within 10 mV (Q2 on) | about 0.6 V lower: Q2 not enhanced |
| G2 | Reverse: −3.7 V on J3 (pin 1 negative), 50 mA limit, no USB | < 1 mA drawn | Current: Q2 the wrong way round |
| G3 | Charge current from ISET (R412.1) with USB and the "cell" at 3.7 V | about 2.2 V at the full 494 mA (USB-C 1.5 A); less on a 500 mA port | ≈ 0: TS fault, CE, ISET open |
| G4 | A real protected cell (1000 mAh+), charge to full | CHG low while charging, high at the end; console `power` | — |

## Phase H — margins and stress

| # | Action / probe | Expected | Wrong means |
|---|---|---|---|
| H1 | 3V3 minimum at U14.5 during the display init and the backlight switching on (scope, 20 µs/div) | stays > 3.15 V (U14 trips at 3.07–3.12 V) | Dips: reset risk; more bulk on 3V3 |
| H2 | SYS_RAW at C311 as the backlight goes from 0 to 100 % (on the cell) | droop < 150 mV | Resets: input decoupling, power budget |
| H3 | 10 minutes at full load (`pattern checker`, `bl 100`, loud tones): U1, U10, U7, U4, U3, Q2, U8/U9, the In3 speaker tracks | ≤ 70 °C on the board at 25 °C ambient | U1 hot: the exposed-pad joint (31 ground vias from R27; voids under the pad) |
| H4 | No cell, USB-C 3 A charger, `bl 100`, loud audio | no reset | Reset: the input limit is exceeded (audio review M7) |
| H5 | `sleep`, then SW5 | wakes; sleep current from the cell about 0.3 mA (panel rails stay on) | No wake: GPIO0, C601, R110. About 0.7 mA more: the amplifiers not in shutdown |

## Phase I — radio (two R28 boards, each with a 915 MHz antenna on J701)

Fit the antennas first: the firmware transmits only on `radio ping`, but a radio should not transmit without one.

| # | Action / probe | Expected | Wrong means |
|---|---|---|---|
| I1 | Console `radio at AT+VER=?` and `radio at AT+NWM=?` | a `RUI_…` version and `OK`; NWM 0 (peer to peer) after the first `radio ping` or `radio listen` sets it | No reply: phase D13. ERROR replies: the SiP's firmware is not RUI3 (reflash it, see below) |
| I2 | Board B `radio listen 120`; board A `radio ping 20 14`, 1 m apart | 20 replies; RSSI about −30 to −50 dBm both ways, SNR > 5 dB | No replies on both: frequency or settings differ (same firmware on both). One-way only: that board's antenna, J701, R704 or the RF trace |
| I3 | Supply current on USB during `radio ping 20 22` (bench supply on J2, or a USB meter) | bursts of roughly 90–120 mA above idle (datasheet: 87 mA typical at 20 dBm; more at 22 dBm; record the value) | Far more: an RF fault or oscillation (check the antenna, C724/C725 empty). Nothing more: the SiP is not transmitting |
| I4 | 3V3_SYS at C414.1 and RADIO_3V3 at C701.1 during `radio ping 20 22` (scope, 1 ms/div) | dips < 100 mV, no reset | Resets: 3V3 bulk or R701 / C701 |
| I5 | Range: board B `radio listen 600` outdoors; walk board A away with `radio ping` at 22 dBm, both in hand | replies to 200 yd (183 m) and more, line of sight; record RSSI against distance | Short range: the antennas (type, cable, near the battery or a hand), the RF path, or the SiP's power setting |

Recovery, only if the SiP's firmware is ever lost (it ships with RUI3 loaded): with the board off, solder a wire from R702's BOOT0 pad (towards U15) to R703's RADIO_3V3 pad and power up: the SiP starts the STM32 ROM bootloader on the UART U1 drives (GPIO39 / 40). Writing RUI3 back over it needs a UART pass-through in U1's firmware, which is not written yet (an open item in `RELEASE_GATES.md`). Remove the wire afterwards.
