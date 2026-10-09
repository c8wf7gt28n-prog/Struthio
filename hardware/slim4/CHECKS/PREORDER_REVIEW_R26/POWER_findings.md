# SLIM4 PCB R26 — POWER TREE review

Reviewer scope: J2 VBUS path (D1, C403, C409), U13 VBUS sensing, U10 BQ24074 (every pin), J3 + Q2, SYS_RAW distribution, every regulator (U4 TPS63070 3V3, U3 TLV62569 1V1_HP, U5 TLV75518P, U6 ME6211C30, U7 TPS61165 + L3/D2/R309/C309/C310), inductors, diodes, capacitor ratings, enable/PG chaining, ESP32-P4 power-up (EN_DCDC/FB_DCDC/CHIP_PU), U14 TPS3808, grounds, thermal.
Sources: `R26_NETLIST.txt`, the docs listed in the brief, and the datasheets listed at the end (fetched 2026-10-09).

## Summary (10 lines)

1. **No BLOCKER found.** Every power IC pin was checked against its datasheet's pin table: U3, U4, U5, U6, U7, U10, U13, U14, Q2, D1 and D2. All match, and every pin is either connected correctly or left open where the datasheet allows it.
2. The charger settings are correct and match the docs: fast charge 443/494/542 mA, pre-charge 39–59 mA, termination 41–69 mA, input limit 1.00–1.15 A, USB500 450–500 mA, timers 24–36 min / 4–6 h, TS 0.75 V.
3. 3V3 = 3.31 V nominal (3.22–3.44 V worst case). 1V1_HP = 1.2 V nominal (1.176–1.224 V), under the P4's 1.3 V absolute maximum. LDOs: 1.8 V and 3.0 V.
4. **MINOR M1:** D1 (PESD5V0S1UL, VBR 6.4–7.2 V) clamps far below the BQ24074's 10.5 V OVP and 28 V rating. A faulty 9–12 V source would destroy D1 (and short VBUS) instead of being blocked by U10.
5. **MINOR M2:** the BQ24074 OUT capacitance on SYS_RAW is 68 µF nominal, above the 4.7–47 µF given in its pin table. Effective capacitance at 4.4 V is probably inside that range.
6. **MINOR M3:** on battery, the BQ24074 short-circuit detector (VO(SC2) 200–300 mV, BATFET up to 100 mΩ) can trip at about 2 A on a worst-case part. Full-scale audio into 4 Ω plus 100 % backlight reaches 2–3 A, which would black out SYS_RAW for 60 ms (reboot).
7. **MINOR M4–M7:** BQ_TS is routed 88 mm to R424 near J3. C309's effective capacitance at 24 V is below the TPS61165's 1 µF minimum. The firmware's thermal suspend resets the charger safety timer. At 100 % backlight on a cell near 3.0–3.2 V, the TPS61165 runs at its duty-cycle and current limits (the backlight dims; nothing is damaged).
8. **BRINGUP-CHECKs:** 3V3 margin over the TPS3808 trip (108 mV DC worst case); first start from USB with no cell while U10 is in its 100 mA mode; U10, U7 and Q2 temperatures; J3 pin polarity against the pack before plugging in.
9. **UNSURE (6 items):** L1 saturation current (no datasheet for MWSA0402S-1R0MT found); whether the two backlight strings share current evenly; panel supply sequencing; 1V1_HP level in download mode; JST PH 2 A contact rating; undershoot when a reversed pack is hot-plugged with USB present.
10. Probability view: none of the findings stops a board from booting from USB or from a good cell. The bring-up probe table (section D) gives the order to measure on a current-limited bench supply.

---

## A. Findings

### M1 — MINOR — VBUS TVS D1 standoff far below the charger's OVP; a faulty high-voltage source destroys D1
- **Evidence (netlist):**
  - D1 PESD5V0S1UL: D1.1 = USB_VBUS (cathode), D1.2 = GND (anode).
  - U10.13 IN = USB_VBUS. C403 (100 nF 16 V) and C409 (4.7 µF 16 V 0603) are also on USB_VBUS.
- **Evidence (datasheets):**
  - Nexperia PESD5V0S1UL (data sheet, Dec 2025), Characteristics table: VRWM 5 V, VBR 6.4/6.8/7.2 V at 5 mA, PPPM 150 W at 8/20 µs only.
  - TI BQ24074 SLUS810N §6 Device Comparison: VOVP 10.5 V for the '74.
  - TI BQ24074 §8.3: IN operating range 4.35–10.2 V.
  - TI BQ24074 §9.3.3: "accepts inputs up to 28 V without damage".
- **Why it matters:**
  - A legacy fast charger, a broken cable/adapter or a lab supply above about 6.5 V puts the source's full current through D1, which is rated only for ESD/surge pulses.
  - D1 fails, usually short, and the board can then never be powered or charged from USB.
  - The BQ24074 alone would have survived up to 28 V by entering OVP (§9.3.3).
  - Normal USB-C sources are 4.75–5.5 V. At 5.5 V D1 sits above its 5 V VRWM but below VBR, so it only leaks. Normal use is therefore fine.
- **Fix:** use a VBUS TVS whose standoff sits between 5.5 V and the 16 V cap rating, for example a 12 V-standoff SOD-882 TVS (PESD12VS1UL class). That protects D1/U10 against 9–12 V faults. Alternatively accept the risk and document "5 V sources only".

### M2 — MINOR — SYS_RAW (BQ24074 OUT) capacitance above the datasheet's 47 µF range
- **Evidence (netlist):** U10.10/11 OUT = SYS_RAW, which carries:
  - C311 4.7 µF (CL10A475KO8NNNC)
  - C402 10 µF 10 V 0603
  - C411, C420, C421: 10 µF 25 V 0805 each
  - C413 22 µF 6.3 V 0805
  - C505, C506: 1 µF each
  - C501–C504: 100 nF each
  - Total: **68.4 µF nominal**.
- **Evidence (datasheet):** BQ24074 Table 7-1 (OUT): "Bypass OUT to VSS with a 4.7-µF to 47-µF ceramic capacitor". §10.2.2.5 says to start from the application-diagram values.
- **Why it matters:**
  - At 4.4 V the X5R parts lose a large part of their value: C413 (6.3 V part at 70 % of its rating) and C402 (10 V 0603) lose the most. The effective total is probably about 40–50 µF, so it is likely inside the range in practice.
  - However, the nominal value is outside the datasheet range. Stability of the OUT LDO loop and the VO(SC1) start-up check (100 mA until OUT > 0.8–1.0 V, §9.3.2) were characterised up to 47 µF.
  - The start-up check itself is fine: 68 µF reaches 0.9 V in about 0.6 ms at 100 mA.
- **Fix:** none required for this spin. Optionally depopulate C411, which duplicates C402/C413 (−10 µF). At bring-up, watch SYS_RAW for oscillation at load steps (probe table D, step 4).

### M3 — MINOR — Battery-only overload trip of the BQ24074 (VO(SC2)) is reachable at full audio + full backlight
- **Evidence (netlist):** every high-current load hangs on SYS_RAW: U4.12/13 (3V3), U7.1 (backlight), U8.7/8 and U9.7/8 (two MAX98357A). The battery path is J3.1 → Q2 → BAT_PLUS → U10.2/3 → U10.10/11.
- **Evidence (datasheet):**
  - BQ24074 §9.3.4.2: with no input, "If the OUT voltage falls below the BAT voltage by 250 mV for longer than tDGL(SC2), OUT is turned off… After tREC(SC2) [60 ms] OUT turns on".
  - §8.5: VO(SC2) is 200/250/300 mV, tDGL(SC2) 250 µs, tREC(SC2) 60 ms.
  - VDO(BAT-OUT) is 50 typ / 100 max mV at 1 A, which means a BATFET resistance of 50–100 mΩ.
  - The trip current is therefore 200 mV / 100 mΩ = **2.0 A worst case** (typical about 5 A).
- **Load estimate at a 3.4 V cell:**

  | Load | Input power | Current from SYS_RAW |
  |---|---|---|
  | 3V3 rail (firmware's 1.55 W provision) | 1.55 W | 0.46 A |
  | Backlight 100 % (74 mA × 24.2 V at η ≈ 0.8) | 2.24 W | 0.66 A |
  | Two MAX98357A clipping into 4 Ω (up to VDD²/RL each) | — | 1.0–2.0 A |
  | **Total** | | **2.1–3.1 A** |

- **Why it matters:** above about 2 A for more than 250 µs on a worst-case U10, SYS_RAW is switched off for 60 ms and the board browns out (TPS3808 resets the P4). Today's firmware defaults (45 % backlight, 35 % volume tones) stay far below this, so it is a latent limit.
- **Fix:**
  - Firmware: cap backlight + volume together on battery, or set MAX98357A gain to 9 dB, or require 8 Ω speakers.
  - Optional hardware: none needed.
  - Bring-up: test the full-volume square wave plus 100 % backlight on a cell at 3.4 V.

### M4 — MINOR — BQ_TS (high-impedance analog node) routed 88 mm to R424 beside J3
- **Evidence (netlist):** BQ_TS = U10.1 + R424.1 only.
- **Evidence (board JSON):**
  - BQ_TS track is 88.3 mm of 0.152 mm with 2 vias.
  - U10 is at (17, 8). R424 is at (−22.5, 59) next to Q2/J3.
- **Evidence (datasheet):**
  - BQ24074 §8.5 Battery-pack NTC monitor: INTC 72–78 µA, so VTS = 0.72–0.78 V with 10 kΩ.
  - Charging suspends if VTS < VHOT (0.27–0.33 V) or > VCOLD (2.0–2.2 V), with tDGL(TS) 50 ms.
  - §9.3.6: TS fault → charging suspended.
- **Why it matters:**
  - The margins are about 0.42 V low and 1.25 V high, and the deglitch is 50 ms, so ordinary switching noise should not trip it.
  - However, a long unshielded 10 kΩ node crosses the board, and a coupling event or a solder bridge on that run silently stops charging. The CHG pin keeps reading "charging" in a TS fault (§9.3.6), so firmware cannot tell.
- **Fix:** move R424 next to U10 pin 1 (the TS route then becomes about 1 mm), or add 100 nF at U10.1. Low cost, but it is a layout edit, so it can wait for the next spin.

### M5 — MINOR — Backlight output capacitor C309 effective capacitance below the TPS61165 minimum
- **Evidence (netlist):** C309 CL10A105KB8NNNC (1 µF, 50 V, X5R, 0603), C309.1 = LCD_LED_A, C309.2 = GND. It is the only capacitor on LCD_LED_A.
- **Evidence (datasheet):**
  - TPS61165 SLVS790E §7.2: CO 1–10 µF.
  - §9.1.5: "If the output capacitor is below the range, the boost regulator can potentially become unstable… Ceramic capacitors can lose as much as 50% of its capacitance at its rated voltage… leave the margin".
- **Why it matters:**
  - At about 24 V (48 % of rating) an 0603 X5R 1 µF typically keeps only about 40–60 % of its value. That is roughly 0.4–0.6 µF, below the 1 µF minimum.
  - TI's own typical application uses the same class of part (GRM188R61E105K, 25 V 0603), so the risk is modest.
  - Output ripple at 74 mA would be about 0.1–0.15 V p-p (Eq. 4).
- **Fix:** add a second CL10A105KB8NNNC in parallel, or change C309 to 2.2 µF 50 V 0805 (for example CL21B225KBFNNNE class). If the layout is frozen: at bring-up, check LCD_LED_A ripple and the inductor current for sub-harmonic behaviour at 100 % and 15 %.

### M6 — MINOR — TPS61165 at 100 % backlight on a low cell runs at its duty-cycle and current limits
- **Evidence (netlist):** U7.1 VIN = SYS_RAW; L3 = WPN4020H100MT (10 µH); D2 = STPS1L40ZFY; R309 = 2.7 Ω, giving 200 mV / 2.7 Ω = 74 mA. Panel strings are 19.6–23.8 V (CFAF7201280A0-050TN datasheet §6.6).
- **Evidence (datasheet):**
  - TPS61165 §7.4: Dmax 90 % min; ILIM 0.96/1.2/1.44 A; fS 1.0–1.5 MHz; RDS(on) 0.7 Ω at VIN 3.0 V; VREF 196–204 mV.
  - §9.1.1 Eq. 1–2 give Iout_max.
- **Calculation (worst case):** VIN 3.0 V, Vout 24.0 V, Vf 0.42 V, L −20 % = 8 µH, fS 1.0 MHz, η 0.75.
  - Ip = 0.33 A.
  - Iout_max = 3.0 × (0.96 − 0.165) × 0.75 / 24 = **75 mA**, against the 74 mA required.
  - Duty needed with the switch and DCR drops (about 0.7 V at 0.8 A) ≈ 0.90–0.91, against **Dmax min 0.90**.
  - At VIN 3.3 V both margins open up (about 82 mA, D ≈ 0.89).
- **Why it matters:**
  - Near the end of discharge, and only at 100 %, a worst-case part loses regulation: the backlight dims or flickers.
  - Nothing is damaged. The current limit protects the switch, and L3's Isat ≥ 2.8 A is far above the 1.44 A ILIM max (no saturation).
  - If the ADC calibration is missing, the firmware never switches off at 3.3 V (slim4_power.c: `adc` false disables `battery_low`), so the cell can run down to pack cut-off (2.5–3.0 V). There, VIN is below the 3.0 V recommended minimum (§7.2) and above UVLO 2.2–2.5 V.
- **Fix:** firmware: cap the backlight to about 80 % below 3.4 V. No hardware change needed. An optional 22 µH inductor (TI's efficiency recommendation, §9.1.2) would cut ripple.

### M7 — MINOR — The firmware's thermal charge-suspend restarts the safety timer every cycle; the temperature it uses is not the charger's or the cell's
- **Evidence (netlist):**
  - BQ_EN1 = U1.14 (GPIO13) + R603 10 k to 3V3.
  - BQ_EN2 = U1.88 (GPIO46) + R604 10 k to GND.
  - U10.14 TMR is open (net BQ_TMR, no other pin).
- **Evidence (firmware):** `slim4_power.c` `update_policy()` enters USB suspend (EN2/EN1 = 1/1) when the **P4 die** temperature is above 75 °C, and leaves it below 65 °C.
- **Evidence (datasheet):** BQ24074 §9.3.5.6: "Reset the timers by toggling the CE pin, or by toggling EN1, EN2 pin to put the device in and out of USB suspend mode".
- **Why it matters:**
  - Each suspend/resume starts a new 4–6 h fast-charge window, so a hot device cycling around 65–75 °C defeats the safety timer.
  - The P4 (U1 at y = 84 mm) is about 76 mm from U10 (y = 8 mm) and nowhere near the cell.
  - Combined with TS fixed at 10 kΩ (no cell temperature), the cell has no temperature-qualified charge stop other than the pack's protection board. The docs state this as a decision.
- **Fix:** firmware: count accumulated charge time across suspends and stop for good after 6 h total. Optional hardware for R27: an NTC footprint at TS in parallel with the R424 option (pack with a 3-wire plug).

### BRINGUP-CHECK items (correct on paper, must be measured)

**B1 — Reset threshold margin.**
- U14 TPS3808G33: U14.5 SENSE = 3V3_SYS, U14.1 RESET = CHIP_PU (R106 10 k, C136 1 µF), U14.4 CT open, U14.3 MR = RESET_MR.
- TPS3808 SBVS050N §6.5: VIT 3.07 V ±1.5 % (3.024–3.116 V); tD with CT open 12–28 ms; pulses of about 20 µs or less are ignored.
- 3V3 from U4 (R410 470 k / R411 150 k, VFB 0.8 V):
  - nominal 3.307 V;
  - worst DC low 3.224 V (1 % resistors, VFB −1 % in PFM, TPS63070 §7.5 "−1 %/+3 %");
  - DC margin to the maximum VIT is **108 mV**.
- Load steps, for example display start or the 1V1 DCDC enable, must not dip 3V3 below about 3.12 V for more than about 20 µs, or the P4 resets.
- Measure 3V3 at U14.5 with a scope during boot and display init.

**B2 — First start from USB with no cell.**
- Before 3V3 exists, EN1 = 0 (R603 pulls to 3V3_SYS) and EN2 = 0, so U10 is in USB100 (90–100 mA, BQ24074 §8.5).
- U4 starts as soon as SYS_RAW reaches its UVLO (EN via R423 from SYS_RAW). During soft-start it draws up to about 1 A input (TPS63070 §8.4.4).
- Energy check:
  - SYS_RAW caps (about 45 µF effective) falling from 4.4 V to 3.0 V give 0.23 mJ.
  - 3V3 needs about 0.08 mJ to reach 1.4 V, where EN1 goes high and the input limit becomes 500 mA.
  - On paper, start-up succeeds.
- With no cell, BAT is only C412. If OUT dips below BAT − 40 mV, supplement mode and the VO(SC2) check could cut OUT for 60 ms (§9.3.4.1.3).
- Verify the 3V3 ramp is monotonic within about 5 ms on a 5 V / 500 mA supply with no cell.

**B3 — Thermal.**
- U10 at 1.5 A USB-C (§12.3 Eq. 11): (5.0 − 4.4) V × 1.15 A + (4.4 − 3.4) V × 0.54 A ≈ 1.23 W. With θJA 44.5 °C/W that is about +55 °C. Thermal regulation starts at 125 °C.
- U7 (SOT-23-6, θJA 210 °C/W) at 100 % on a 3.2 V cell: switch loss about 0.3–0.4 W, so about +60–85 °C.
- U3 and U4 are low dissipation.
- Q2 at 1 A: 60–85 mΩ (AO3401A at VGS −4.5 V / −2.5 V), under 0.1 W.
- Check all of these with a thermal camera.

**B4 — J3 polarity.**
- J3.1 = BAT_CONN → Q2.3 (drain); J3.2 = GND.
- Hobby JST-PH packs are not consistent in which pin is +. Check each pack with a meter before plugging it in.
- Q2 blocks a reversed pack without USB (AO3401A: body diode reverse-biased, VGS ≈ 0).

**B5 — D2 margin at open LED.**
- With no panel, SW reaches VOVP 37–39 V (TPS61165 §7.4), then the device latches off (§8.3.2).
- D2 VRRM is 40 V (STPS1L40-Y Table 2), so the margin is about 1 V plus ringing.
- TI's own recommended diode (MBR0540, §9.1.3) is also 40 V, so this follows TI.
- Run open-LED tests only briefly, and scope the SW pin to confirm the overshoot stays under 40 V.

---

## B. UNSURE (what would settle each)

| # | Item | What would settle it |
|---|---|---|
| U1 | **L1 MWSA0402S-1R0MT saturation current.** Steady peak is only about 0.7 A (TPS63070 §9.2.2.2 Eq. 8: 0.5 A out, VIN 3.0 V, D 0.09 → 0.61 + 0.06 A). The question is whether Isat ≥ the TPS63070 average input current limit of 3.05–4.15 A (§7.5), needed for clean overload/short behaviour. The non-"S" MWSA0402-1R0MT is rated 7.0 A Isat (Sunlord catalog); no "S" datasheet was found. | Sunlord MWSA0402S datasheet row for 1R0, or the LCSC part page for the BOM's LCSC number. |
| U2 | **Two backlight strings in parallel with no ballast.** J1.39 (LED1−) and J1.40 (LED2−) are joined on LCD_LED_K into one sense resistor (R309). Panel datasheet §6.6: VLED 19.6–23.8 V, ILED 40 mA (typ only, no max given). Uneven Vf between strings could push one string above 40 mA at 74 mA total. | Panel maker's maximum per-string current, or a measurement (cut-trace test board, or panel string Vf matching data). If the strings do not share evenly: firmware cap ≤ 54 %, or drive each cathode separately. |
| U3 | **Panel supply sequencing.** U5 (LCD_1V8, EN tied to IN = 3V3_SYS) and U6 (LCD_VCI_3V0, CE tied to VIN) both start with 3V3, so IOVCC and VCI rise together and the panel can never be power-cycled. | ILI9881C / CFAF7201280A0-050TN power-on sequence (not in the Crystalfontz datasheet extract). Display reviewer. |
| U4 | **1V1_HP voltage in download mode.** The Espressif checklist says EN_DCDC = 0 in download mode, yet the chip runs, so the HP domain is fed internally (datasheet Table 2-13: "HP LDO 1.1 V"). Whether pins 26/54/76/91 then read 0 V or about 1.1 V is not documented. | Measure C135 in download mode. Either value is fine; anything above 1.3 V is not. |
| U5 | **JST PH current rating vs battery-only peaks** (M3: 2–3 A). JST PH is commonly rated 2 A per contact. | JST PH catalog, plus the firmware cap from M3. |
| U6 | **Reversed pack hot-plugged with USB present.** C412 (up to 4.2 V) discharges through Q2 into the pack. BAT_PLUS must not go below −0.3 V (BQ24074 §8.1 BAT abs. min). The steady state is ≥ 0 V (README edit 12, consistent with BQ24074 §8.5 IBAT 4–11 mA, VBAT(SC) 1.6–2.0 V), but the transient is not analysed. | Simulation or a bench test with a reversed bench supply (current-limited, not a cell). |

---

## C. VERIFIED OK (coverage)

Capacitor code decode (Samsung): `CL05B104KO5` 100 nF 16 V X7R 0402; `CL05B103KB5` 10 nF 50 V X7R 0402; `CL05A105KA5` 1 µF 25 V X5R 0402; `CL05B224KO5` 220 nF 16 V X7R 0402; `CL10A475KO8` 4.7 µF 16 V X5R 0603; `CL10A106KP8` 10 µF 10 V X5R 0603; `CL10A105KB8` 1 µF 50 V X5R 0603; `CL21A106KAY` 10 µF 25 V X5R 0805; `CL21A226MQQ` 22 µF 6.3 V X5R 0805. Resistors (UniOhm): 4993 = 499 k, 4703 = 470 k, 4303 = 430 k, 1503 = 150 k, 1003 = 100 k, 3302 = 33 k, 1002 = 10 k, 3301 = 3.3 k, 1801 = 1.8 k, 1501 = 1.5 k, 0603WAF270K = 2.70 Ω (R309).

### USB input
| Item | Check | Reference |
|---|---|---|
| J2 A4/A9/B4/B9 = USB_VBUS; A1/A12/B1/B12 = GND; SH = CHASSIS_GND → R404 0 Ω → GND | OK | — |
| D1.1 cathode = VBUS, D1.2 anode = GND (unidirectional, correct polarity); 2 unnetted F.Cu pads in footprint, DRC clean | OK (see M1) | PESD5V0S1UL pinning table |
| C403 + C409 = 4.8 µF on IN: within the 1–10 µF IN range and below 10 µF USB inrush | OK | BQ24074 Table 7-1 IN; §9.3.4.1 |
| VBUS caps 16 V vs 10.2 V max operating (BQ OVP 10.2–10.8 V) | OK | §8.3, §8.5 |
| U13 TUSB320LAI: 1 CC1, 2 CC2, 3 PORT = GND (UFP), 4 VBUS_DET via R416 470 k + R417 430 k = 900 k (spec 855–920 k), 5 ADDR open = GPIO mode, 6 OUT3 open, 7/8 OUT1/OUT2 → 10 k to 3V3 → GPIO43/GPIO17, 9 ID open (open-drain output), 10 GND, 11 EN_N = GND, 12 VDD = 3V3_SYS (2.7–5 V) | OK | TUSB320LAI SLLSEQ8D Pin Functions, §6.5 (RVBUS, RCC_DB) |
| Dead-battery start: TUSB320LA presents Rd 4.1–6.1 kΩ with VDD off, so a USB-C source turns on VBUS with a flat cell | OK | §7.3.3, §6.5 RCC_DB |
| VBUS_DET at 5 V = 0.48 V; at 28 V = 2.67 V (abs max 4 V; RVBUS_PD 95 k) | OK | §6.1, §6.5 |
| Firmware OUT1/OUT2 decode (H/H none, H/L default, L/H 1.5 A, L/L 3 A) | OK | Table 3 |
| U11/U12 TPD2EUSB30 GND pin 3 = GND (data/CC ESD only) | OK | — |

### Charger U10 BQ24074RGT (every pin)
| Pin | Net | Check | Reference |
|---|---|---|---|
| 1 TS | BQ_TS → R424 10 k → GND | VTS = 72–78 µA × 10 k = 0.72–0.78 V, inside 0.30–2.1 V window; datasheet's no-NTC connection (route length: M4) | Table 7-1 TS; §8.5 NTC; §10.2.2.3 |
| 2, 3 BAT | BAT_PLUS, C412 10 µF 25 V | 4.7–47 µF range met; BAT abs max 5 V vs 4.23 V | Table 7-1; §8.1 |
| 4 CE | GND | charging enabled (internal 285 k pull-down; tied, not floating) | Table 7-1 CE |
| 5 EN2 | R604 10 k to GND + GPIO46 | P4 GPIO46 has no reset pull (P4 Table 2-1) | Table 7-2; §8.5 VIL 0.4/VIH 1.4 V |
| 6 EN1 | R603 10 k to 3V3 + GPIO13 | GPIO13 no reset pull; defaults USB100 before 3V3, USB500 after | Table 7-2 |
| 7 PGOOD | 100 k to 3V3 → GPIO44 | open drain, 1–100 k range | Table 7-1; §9.3.5.7 |
| 8 VSS, EP | GND | OK | Table 7-1 Thermal Pad |
| 9 CHG | 100 k to 3V3 → GPIO11 | OK | Table 7-1 |
| 10, 11 OUT | SYS_RAW | VO(REG) 4.3–4.5 V (capacitance: M2) | §8.5 |
| 12 ILIM | R415 1.5 k | KILIM 1500–1720 gives 1.00/1.07/1.15 A; R range 1.1–8 k | §8.5, Eq. 1 |
| 13 IN | USB_VBUS | OVP 10.2–10.8 V, UVLO 3.2–3.4 V | §8.5 |
| 14 TMR | open | default timers: pre-charge 1440–2160 s, fast 14400–21600 s; dynamic (slowed in DPPM, VIN-DPM, thermal) | Table 7-1; §8.5; §9.3.5.6 |
| 15 ITERM | R413 3.3 k | 0.0225–0.0375 × 3.3 k / 1.8 k = 41/55/69 mA (USB500/ILIM); 15/18/22 mA in USB100; ≤ 50 % rule met | §8.5; §9.3.5.2 Eq. 5 |
| 16 ISET | R412 1.8 k | 797–975 AΩ → 443/494/542 mA, ≤ 0.55 C for ≥ 1000 mAh; pre-charge 70–106 AΩ → 39/49/59 mA; range 590–8900 Ω | §8.5; §9.3.5 Eq. 2 |

Also checked:
- USB500 input limit 450–500 mA, VIN-DPM 4.35–4.63 V (USB modes only). The docs' 1.98 W budget at 450 mA × 4.4 V is consistent.
- Junction thermal regulation 125 °C; thermal shutdown 155 °C (B3).

### Battery, Q2, SYS_RAW
| Item | Check | Reference |
|---|---|---|
| Q2 AO3401A: 1 G = GND, 2 S = BAT_PLUS, 3 D = BAT_CONN. Body diode D→S conducts toward the load and turns the FET on (VGS = −VBAT); blocks a reversed pack with no USB | OK | AO3401A pinout, VGS(th) −0.5/−0.9/−1.3 V |
| VGS max 4.23 V vs ±12 V; VDS −30 V; RDS 60 mΩ max at −4.5 V, 85 mΩ max at −2.5 V | OK | AO3401A abs-max and electrical tables |
| BAT_CONN 0.5 mm track 18 mm; BAT_PLUS In2 plane | OK | board JSON |
| Reversed pack + USB steady state (README edit 12): IBAT(SC) 4–11 mA, VBAT(SC) 1.6–2.0 V, Q2 ≤ 11 mA × about 5.5 V ≈ 60 mW | consistent | BQ24074 §8.5 |
| BAT_ADC R418 100 k / R419 33 k: 4.23 V → 1.05 V; about 32 µA drain | OK | — |
| SYS_RAW loads: U4 (VIN 2–16 V), U7 (3–18 V), U8/U9 (MAX98357A, 2.5–5.5 V; audio reviewer to confirm), R423 | ≤ 4.5 V OK | TPS63070 §7.3; TPS61165 §7.2 |

### 3V3 buck-boost U4 TPS63070RNM
| Item | Check | Reference |
|---|---|---|
| Pins: 1 PS/SYNC and 14 EN = 3V3_ENABLE (R423 100 k from SYS_RAW: shared 1 k–1 MΩ series resistor allowed); 2 PG open (OK); 3 VAUX C401 100 nF; 4 GND; 5 FB; 6 FB2 open (VSEL low); 7, 8 VOUT; 9 L2; 10 PGND; 11 L1; 12, 13 VIN; 15 VSEL = GND | OK | Pin Functions; §8.4.2, §8.4.5, §8.4.7; ROC CVAUX 100 nF |
| PS/SYNC high = power save (README wording correct) | OK | Pin Functions |
| FB: R410 470 k / R411 150 k, exactly TI Table 4 for 3.3 V; R2 ≤ 400 k; 5.3 µA ≥ 2 µA | OK | §9.2.2.1 |
| VOUT 3.307 V nominal, 3.22–3.44 V worst case (PFM −1 %/+3 %) | within P4 3.0–3.6 V and USB PHY 2.97–3.63 V | §7.5; P4 Table 5-2 |
| L1 1.0 µH: effective 0.7–2.8 µH OK; Table 3 lists 1.0 µH with 47/68/100 µF | OK (Isat: U1) | §7.3, Table 3 |
| COUT ≈ 159 µF nominal (5 × 22, 4 × 10, 4.7, 3 × 1, 16 × 0.1): 15–470 µF range OK; effective ≥ 10 × L | OK | §7.3; §9.2.2 |
| CIN C402 10 µF + C413 22 µF (min 4.7 µF) | OK | §7.3 |
| Start-up needs VIN ≥ 3.0 V while VOUT < 3.0 V: a cell below about 3.1 V under load will not cold-start (USB will) | note | §7.5 |
| RHPZ at 0.5 A, VIN 3.0 V ≈ 870 kHz (> 400 kHz) | OK | §9.2.2.2 Eq. 9 |

### 1V1_HP buck U3 TLV62569DBV and P4 core sequencing
| Item | Check | Reference |
|---|---|---|
| Pins: 1 EN = EN_DCDC (U1.79), 2 GND, 3 SW = CORE_SW → L2, 4 VIN = 3V3_SYS, 5 FB = FB_DCDC (U1.78) | OK | TLV62569 Pin Functions |
| Matches Espressif's v3 reference exactly: 499 k / 499 k + 22 pF, 2.2 µH, 22 µF out (C135 + 4 × 100 nF), EN from EN_DCDC, no EN pull-down | OK | ESP32-P4 HW Design Guidelines, Schematic Checklist "Internal Voltage Regulators and External DCDC" (TLV62569 rev ≥ 3.0 figure) |
| R2 = 499 k exceeds TI's 200 k guidance; required by Espressif v3 (chip trims through FB_DCDC) | accepted | TLV62569 §8.2.2.2 |
| VOUT = 0.588–0.612 × 2 = 1.176–1.224 V; P4 VDD_HP range 0.99–1.3 V, abs max 1.3 V; chip trims it | OK | TLV62569 §6.5; P4 datasheet v0.7 Tables 5-1, 5-2 |
| EN must not float: driven by P4 (0 in download mode / no firmware per Espressif) | OK (bring-up D7) | TLV62569 Pin Functions; Espressif checklist |
| L2 ASWPA4035S2R2MT: Isat 4.35 / 4.80 A, Irms 3.0 / 3.5 A vs ILIM 3 A typ, peak load about 0.62 A at 0.5 A | OK | Sunlord ASWPA4035S table; TLV62569 §6.5, §8.2.2.4 |
| VIN 3.22–3.44 V in 2.5–5.5 V; C126 10 µF (≥ 4.7 µF) | OK | §6.3; §8.2.2.5 |
| C135 22 µF (6.3 V at 1.2 V): Table 4 "+" for 1.2–1.8 V / 2.2 µH; inside 10–47 µF | OK | §8.2.2.3 Table 4, §8.2.2.5 |
| P4 3V3 pins 9, 21, 62, 75, 77, 85, 96, 101, 102 on 3V3_SYS; VDD_HP 26/54/76/91 on 1V1_HP; GND 105 | OK | P4 datasheet Table 2-12 |

### Reset U14 TPS3808G33DBV
- Pins: 1 RESET = CHIP_PU, 2 GND, 3 MR = RESET_MR (R607 10 k, C602, SW6; internal 70–90 k), 4 CT open (20 ms), 5 SENSE = 3V3, 6 VDD = 3V3. OK (TPS3808 Table 5-1).
- R106 10 k / C136 1 µF: Espressif's recommended RC; inside the 10 k–1 MΩ pull-up range. OK.
- Timing: tD 12–28 ms ≫ tSTBL 50 µs. CHIP_PU low ≤ 0.4 V at 1 mA, below VIL_nRST = 0.825 V. OK (P4 Table 2-14 and Table 5-4).
- Threshold margin: B1.

### LCD LDOs
- U5 TLV75518PDBV: 1 IN = 3V3, 2 GND, 3 EN = 3V3, 4 NC, 5 OUT = LCD_1V8.
  - C305 1 µF in, C306 1 µF + C304 100 nF out. TLV755P needs ≥ 0.47 µF effective, so OK.
  - Dissipation 1.5 V × ~44 mA ≈ 66 mW. OK.
  - Reference: TLV755P SBVS320D Pin Functions and footnote; §ROC CIN/COUT 1 µF.
- U6 ME6211C30M5G-N: 1 VIN = 3V3, 2 VSS, 3 CE = 3V3, 4 NC, 5 VOUT = LCD_VCI_3V0.
  - C307 / C308 1 µF, as the datasheet's CIN = CL = 1 µF.
  - Dropout 100 mV at 100 mA, 210 mV at 200 mA (typ) against ≥ 0.22 V headroom from 3.22 V. OK.
  - Panel VCI 2.5–3.6 V. OK.
  - Reference: Microne ME6211 V24 p.4 and C30 table; panel datasheet IOVCC 1.65–3.6 V.

### Backlight boost U7 TPS61165DBV
- Pins: 1 VIN = SYS_RAW, 2 CTRL = BACKLIGHT_PWM (R422 100 k pull-down: off at reset), 3 SW = BL_SW, 4 GND, 5 COMP = C310 220 nF (TI's recommended value), 6 FB = LCD_LED_K / R309. OK (TPS61165 Pin Functions; §9.1.4).
- Current setting: 196–204 mV / 2.7 Ω (1 %) = 72–76 mA. OK.
- Dimming: PWM at 20 kHz (slim4_board.c:487), inside 5–100 kHz. The low time is far above or below the EasyScale 260 µs detect only at extreme duty. OK (§7.2, §7.4).
- L3 WPN4020H100MT: 10 µH (recommended 10–22 µH); Isat 2.8 / 3.5 A, Irms 2.0 / 2.35 A against ILIM 1.44 A max. OK (Sunlord WPN table).
- D2 STPS1L40ZFY: A = BL_SW, K = LCD_LED_A (correct). 1 A IF(AV), 40 V VRRM against OVP 39 V max (B5).
- C309: 50 V rating against 39 V (M5 for capacitance). C311 4.7 µF at VIN (1–4.7 µF recommended). OK.
- Shutdown path: SYS_RAW ≤ 4.5 V < the strings' minimum 19.6 V, so the LEDs stay off when U7 is disabled. OK (§8.4.1).
- Open-LED latch-off; the string's maximum 24.0 V is well under the 37 V minimum OVP (§8.3.2).

### Grounds and voltage ratings
- GND pins: U3.2; U4.4, U4.10, U4.15 (VSEL); U5.2; U6.2; U7.4; U10.4, U10.8, U10.EP; U13.3, U13.10, U13.11; U14.2; Q2.1 (gate); J3.2; J2 GND ×4. All on GND. The chassis is tied through R404 0 Ω.
- Voltage-rating check by net maximum:
  - USB_VBUS ≤ 10.8 V: 16 V parts.
  - SYS_RAW ≤ 4.5 V: weakest is C413 at 6.3 V (71 %).
  - BAT_PLUS ≤ 4.23 V: 25 V.
  - 3V3 ≤ 3.44 V: 6.3 V (55 %).
  - 1V1 ≤ 1.3 V.
  - LCD_LED_A ≤ 39 V: 50 V (78 %).
  - COMP ≤ 3 V: 16 V.
  - VAUX ≤ 7 V: 16 V.
  - All OK. DC-bias derating is covered in M2, M5 and the TPS63070 COUT row.

---

## D. Bring-up probe table (current-limited bench supply, in this order)

Step 0 is unpowered. Steps 1–9 use 5.00 V into J2 VBUS (or a USB-C PD-less source) with no cell, current limit 100 mA, raised to 500 mA after step 3. Steps 10–13 use a second bench supply as the "cell" on J3, 3.70 V, 1 A limit.

| # | Probe point (pad) | Expected | Wrong reading means |
|---|---|---|---|
| 0a | Ohmmeter USB_VBUS (C409.1) to GND (C409.2) | > 50 kΩ (900 k divider ∥ U10 IN) | Low: D1 reversed or shorted, U10 IN short, C409 short |
| 0b | SYS_RAW (C411.1), 3V3_SYS (C414.1), 1V1_HP (C135.1), BAT_PLUS (C412.1), LCD_LED_A (C309.1) to GND | each > 100 Ω, no dead short; LCD_LED_A > 1 MΩ | Short on that rail: solder bridge at U4/U3/U10/U7, wrong capacitor |
| 0c | Diode test J3.1 (+) to J3.2 (−) | Q2 body diode toward BAT_PLUS: J3.1 → C412.1 ≈ 0.6–0.8 V | Q2 rotated or wrong part |
| 1 | USB_VBUS at C409.1 | 5.0 V; supply current < 30 mA before 3V3 starts | Current limit hit: short downstream of U10 |
| 2 | PGOOD at U10.7 (R421.2) | < 0.4 V, about 1.2 ms after VBUS | High: U10 not seeing a valid input (pin 13, solder, OVP) |
| 3 | SYS_RAW at C411.1 | 4.40 V (4.30–4.50) | Low or oscillating: U10 in current limit (USB100, see B2), OUT short, M2 instability |
| 4 | 3V3_ENABLE at R423.2 | ≈ SYS_RAW (≥ 0.83 V needed) | 0 V: R423 open |
| 5 | 3V3_SYS at C414.1 | 3.31 V (3.22–3.44); ripple < 50 mV p-p in PFM | Wrong: R410/R411 swapped (gives 1.06 V), FB bridge, L1 or U4 joints |
| 6 | BQ_EN1 at R603.2 / BQ_EN2 at R604.1 | 3.3 V / 0 V | EN2 high and EN1 high = suspend (no SYS_RAW from USB) |
| 7 | CHIP_PU at C136.1 (scope, trigger on 3V3) | low for 12–28 ms after 3V3 > 3.1 V, then RC rise to 3.3 V | Never rises: 3V3 below VIT (B1), MR held (SW6, C602 short) |
| 8 | ITERM at R413.1 / TS at R424.1 | 0.24–0.26 V / 0.72–0.78 V | TS < 0.3 V or > 2.1 V: charger suspended (R424 wrong, M4); ITERM 0: R413 short |
| 9 | USB_VBUS_SENSE at U13.4; OUT1/OUT2 at R605.2 / R606.2 | about 0.48 V; H/L on a default port, L/H 1.5 A, L/L 3 A | VBUS_DET wrong: R416/R417 value; no Rd: VBUS never on from a C-C cable |
| 10 | EN_DCDC at U3.1 | 0 V in download mode; > 1.2 V after the app starts | High in download mode, or floating: check U1.79 joint |
| 11 | 1V1_HP at C135.1 (scope CORE_SW at L2.1) | app: 0.99–1.3 V (about 1.2 V nominal, chip-trimmed); download mode: 0 V or about 1.1 V (see UNSURE U4) | > 1.3 V: stop (R104/R105 wrong or open FB, P4 abs max) |
| 12 | LCD_1V8 at C306.1 / LCD_VCI_3V0 at C308.1 | 1.78–1.82 V / 2.97–3.03 V | Wrong: U5/U6 rotated or swapped |
| 13 | Battery: BAT_CONN at J3.1 and BAT_PLUS at C412.1, bench "cell" 3.70 V / 1 A | BAT_PLUS within 10 mV of J3.1 at no load (Q2 on) | ~0.6 V lower: Q2 not enhanced (gate not at GND) |
| 14 | Charge current via ISET at R412.1, VBUS + "cell" 3.7 V | 1.8 kΩ × I/400: about 2.2 V at full 494 mA (USB-C 1.5 A), less in USB500 (DPPM) | ≈ 0: TS fault, CE high, ISET open |
| 15 | Reverse test: bench supply −3.7 V on J3 (1 → −), 50 mA limit, no USB | < 1 mA drawn; BAT_PLUS ≈ 0 V | Current: Q2 wrong orientation |
| 16 | Backlight: LCD_LED_K at R309.1 (panel connected) | 0.20 V × duty (45 % → about 90 mV); LCD_LED_A 20–24 V; ripple at C309 < 0.2 V | LED_A at 37–39 V then collapse: open LED (J1 seating); dims at low VIN: M6 |
| 17 | Thermal camera: U10 (USB-C charge), U7 (100 % BL), U4, U3, Q2 | ≤ 70 °C board-level at 25 °C ambient | Hotter: thermal vias or layout (B3) |
| 18 | 3V3 min at U14.5 during display init and backlight on (scope, 20 µs/div) | stays > 3.15 V | Dips: reset risk (B1); add bulk capacitance or check the U4 layout |

---

## Datasheets used
- TI BQ24072/3/4/5/9 SLUS810N (Oct 2021): §6 Table, §7 Table 7-1/7-2, §8.1, §8.3, §8.4, §8.5, §9.3.2–9.3.6, §10.2.2, §12.3
- TI TPS63070 SLVSC58B (Mar 2019): Pin Functions, §7.3, §7.5, §8.4.2–8.4.7, §9.2.2 (Tables 3–6, Eq. 6–9)
- TI TLV62569 SLVSDG1C (Oct 2017): Pin Functions, §6.3–6.5, §8.2.2.2–8.2.2.5 (Table 4)
- TI TPS61165 SLVS790E (Apr 2019): Pin Functions, §7.1–7.4, §8.3, §8.4.1, §9.1.1–9.1.5
- TI TPS3808 SBVS050N (Aug 2026): Table 5-1, §6.5, §7.4
- TI TUSB320LAI/HAI SLLSEQ8D (May 2017): Pin Functions, §6.1, §6.5, §6.7, §7.2.5, §7.3.3, Table 3
- TI TLV755P SBVS320D: Pin Functions, ROC
- Espressif ESP32-P4 Datasheet v0.7 (Table 2-1, 2-11, 2-12, 2-13, 2-14, 5-1, 5-2, 5-4); ESP32-P4 Hardware Design Guidelines, Schematic Checklist (power, DCDC, CHIP_PU)
- Nexperia PESD5V0S1UL; AOS AO3401A Rev 3.1; ST STPS1L40-Y DocID018247 Rev 2; Microne ME6211 V24; Sunlord WPN4020H and ASWPA4035S series tables; Crystalfontz CFAF7201280A0-050TN datasheet (2022-11-17) §6.5–6.6
