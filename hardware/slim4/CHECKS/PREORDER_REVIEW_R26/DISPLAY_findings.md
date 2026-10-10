# SLIM4 R26: display path review (U1 to J1 to CFAF7201280A0-050TN)

## Summary (10 lines)
1. No BLOCKER found in the display hardware. J1's 40 pads match the Crystalfontz pin table pad for pad. The DSI P/N and lane order is correct at U1's pads, J1 and the panel. Supplies, reset polarity and the TPS61165 pinout and topology are all correct.
2. J1's orientation looks right: top contact (FH12A, Hirose p.7 and p.11; JLC C506795 lists "Top Contact"), pin 1 on the west, FPC contacts on the tail's rear face. The panel drawing shows this, but only on a drawing, so before ordering check a real tail against an FH12A sample (UNSURE U1). It costs one panel and one connector.
3. MAJOR (firmware): the lane rate is 1000 Mbit/s. The ILI9881C datasheet limits 2-lane operation to 850 Mbit/s for any format and to 566 Mbit/s for RGB565 (Table 39, p.299). Two lanes also cannot carry 59 Hz at 78–80 MHz within that spec. Espressif runs the same overspec setting and it works there, but add an in-spec fallback profile (60 MHz / 560 Mbit/s).
4. MINOR (firmware): the self-test expects ID 98 81 0C, but the ILI9881C-0D datasheet gives 98 81 1C (p.181). A good panel can therefore be reported as `PANEL FAIL`.
5. MINOR (firmware): Espressif's driver sends Sleep Out before the Crystalfontz register table, which is the opposite of the Linux order. The table itself is byte-identical to the Raspberry Pi kernel's `cfaf7201280a0_050tx_init` (191 entries).
6. Backlight: 200 mV / 2.7 Ω = 74 mA (71.9–76.3 mA worst case), 37 mA per string against the 40 mA rating. The two 7-LED strings run in parallel. In the worst case the boost can deliver only about 78 mA at a 3.0 V input, so the LEDs can drop out of regulation near battery cut-off (MINOR).
7. Mechanical (MINOR, documentation): FH12 is a front-flip connector, so the actuator is at the mouth, not "the side away from the mouth". A 40 mm tail with a 1.5–2 mm fold reaches only about Y 78.5–80. The panel will sit 2.5–4.5 mm further north than the documented Y 109.8.
8. MINOR (power): the panel rails are always on and RESX is held low through R307 10 k. In deep sleep that is about 0.18 mA in R307, plus about 0.1 mA in the panel and LDOs.
9. TPS61165 open-LED protection latches the boost off (datasheet §8.3.2). With no panel the output does not "sit at 38 V" as the docs say: it spikes to 37–39 V once and then falls back to SYS_RAW.
10. The bring-up probe table is at the end. Measure the rails, RESX, LED_A and LED_K with the panel unplugged first, then plugged. The R309 check (J1.39/40 to GND = 2.7 Ω, unpowered) is a free assembly test.

Sources (fetched 2026-10-09; local copies in scratchpad/dl):
- [CFAF] Crystalfontz CFAF7201280A0-050TN datasheet, release 2022-11-17: p.5 drawing (front, side and rear views, Detail A), p.6 §6.2 pin table, p.7 §6.4, p.8 §6.6 backlight and circuit. https://www.crystalfontz.com/products/document/4870/CFAF7201280A0-050TNDatasheet.pdf
- [HRS] Hirose FH12 catalogue (2010): p.3 ordering code "A: Top contact type", p.7 "0.5mm Pitch Top Contact Type" with mated cross-section, p.11 recommended FPC and land. https://www.physics.utoronto.ca/~astummer/Archives/2014%20Micro%203D%20Magnetometer/Docs/Hirose%20FH12-16S-1SV(55),%20FFC%20connector,%20SMT%201mm%2016-pos.pdf . JLCPCB C506795 = FH12A-40S-0.5SH(55), "Top Contact".
- [ILI] Ilitek ILI9881C-0D specification V102 (2017-03-16), via Crystalfontz https://crystalfontz.com/controllers/Ilitek/ILI9881C/504 : p.17–18 features and lane rates, p.22–23 pin description, p.38 Table 2 lane mapping, p.181 §5.4.1 ID4, p.198 §5.4.14 B6h/B7h, p.217 §5.7.1, p.282–283 §12.1 power sequences, p.308 §18.4.10 reset timing (Table 47), §18 DC characteristics (standby current, note 2 VDDI ≤ VCI), p.299 Table 39 lane-speed limits, Tables 42–43 LP timings.
- [LNX] Raspberry Pi Linux rpi-6.12.y `drivers/gpu/drm/panel/panel-ilitek-ili9881c.c`: `cfaf7201280a0_050tx_init` (line 1459), `cfaf7201280a0_050tx_default_mode` (line 2298; 78 MHz, 720+120/2/80, 1280+60/2/90), desc (line 2518; 4 lanes, VIDEO|SYNC_PULSE), probe sets `MIPI_DSI_FMT_RGB888` (line 2440), prepare order (lines 2086–2137). https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/drivers/gpu/drm/panel/panel-ilitek-ili9881c.c
- [TPS] TI TPS61165 datasheet SLVS790E (rev. April 2019): p.3 pin functions, p.4 §7.2, p.5 §7.4, p.7 §8.3.2 OVP, §8.4.1, p.10 §9.1.1 Eq.1–2, p.11 §9.1.2–9.1.5, p.12 §9.2.1.2.1 EasyScale and PWM detection. https://www.ti.com/lit/ds/symlink/tps61165.pdf
- [P4] ESP32-P4 datasheet v0.7, Table 2-1 pin table (pins 9–11, 34–41, 73).
- ESP-IDF v6.1 (`~/esp/esp-idf`): `esp_lcd/dsi/esp_lcd_mipi_dsi_bus.c`, `esp_lcd_panel_dpi.c`, `esp_lcd_panel_io_dbi.c`, `esp_hal_lcd/mipi_dsi_hal.c`; managed `espressif__esp_lcd_ili9881c` 1.1.0.

---

## Findings

### F1. MAJOR (firmware): DSI lane rate and pixel rate exceed the ILI9881C 2-lane limits
- **Evidence:** `slim4_panel_cfaf.h`: `SLIM4_PANEL_LANE_MBPS 1000`, `dpi_clock_freq_mhz = 78`, RGB565, 2 lanes. [ILI] p.17–18 limits 2 data lanes to 850 Mbit/s. [ILI] Table 39 (p.299, "Limited Clock Channel Speed") gives the 2-lane maximum by data type: RGB565 (0Eh) 566 Mbit/s, RGB666 637, RGB666 loose or RGB888 850. All rows come to the same pixel-rate ceiling of about 70.8 Mpixel/s on 2 lanes. ESP-IDF rounds the DPI clock to 240/3 = 80 MHz (`mipi_dsi_hal_host_dpi_calculate_divider`, PLL_F240M default) and stretches HFP to 144 to keep 59.06 Hz. That pixel stream needs 640 Mbit/s a lane in RGB565, above 566, and 960 in RGB888, above 850. Linux runs this panel on 4 lanes in RGB888 at 468 Mbit/s, which is in spec.
- **Why it matters:** the run is 1.77× over the controller's rated lane speed. The panel receiver may lose HS sync and show no image, sparkles or a rolling picture. Espressif's own `ILI9881C_PANEL_BUS_DSI_2CH_CONFIG()` uses 1000 Mbit/s with an 80 MHz DPI clock on 2 lanes and works on their ILI9881C panel, so this is not certain to fail. It can be fixed in firmware, and the PCB is unaffected.
- **Fix:** add an in-spec fallback profile selectable from the console or Kconfig, and bring up with it first.
  - DPI clock 60 MHz (240/4), lane 560 Mbit/s, RGB565.
  - With the vendor porches that gives 45.4 Hz. With tighter horizontal porches, for example 720 + 40/2/40, it gives about 52 Hz. The vendor comment says its porches are a compromise, so other values should be tolerated.
  - Burst mode still fits: 723 byte clocks at 70 MHz is 10.3 µs per line, against a 15.4 µs line.
  - The escape clock stays legal: 560/8/18 rounds to a divider of 4, so 17.5 MHz, TLPX 57 ns, inside [ILI] Table 42's 50–75 ns.

  Keep 1000 Mbit/s as the "fast" profile only after it has been proven on hardware with `pattern checker` and `pattern gradient`.

### F2. MINOR (firmware): the self-test's expected panel ID does not match the datasheet
- **Evidence:** `slim4_selftest.h:153-155` expects 98 81 0C, and `slim4_selftest_logic.c:466-474` reports `PANEL FAIL` otherwise. [ILI] p.181 §5.4.1: page 1 registers 00h–02h read 98h, 81h, 1Ch on the ILI9881C-0D. Logs from other boards show other ID3 values as well.
- **Why it matters:** a working panel can be flagged FAIL ("a different panel or controller"), which sends bring-up the wrong way. Display init still continues, because `slim4_st_panel_usable` checks only `answered`.
- **Fix:** pass on 98 81 xx and log ID3 as information. The 98 81 check confirms the controller, and the ID3 check proves nothing more.

### F3. MINOR (firmware): driver call order differs from the panel vendor's order
- **Evidence:** `esp_lcd_ili9881c.c:panel_ili9881c_init` sends this, in order:
  1. Page 1, three ID reads, then B7h = 03 (2-lane).
  2. Page 0, then **11h Sleep Out**, then 120 ms.
  3. 36h = 00 and 3Ah = 55.
  4. The Crystalfontz table (pages 3, 4, 1, then 0, 35h, a second 11h with 120 ms, and 29h).
  5. DPI start.

  [LNX] `ili9881c_prepare` sends the table first, then page 0, TE on and Sleep Out, then display on. So Sleep Out (charge pumps on) happens here before the GIP and power registers on pages 3 and 4 are loaded. `init_display` then calls `esp_lcd_panel_disp_on_off(true)` while video is already running, which sends a third 29h.
- **Why it matters:** this is very likely harmless. The same driver does it with its default table, and both register pages are writable in Sleep Out ([ILI] availability tables). It is still a deviation from the only validated sequence for this panel. One bring-up symptom to watch for is a brief flash or garbage at power-on.
- **Fix:** leave it as it is for bring-up. If the picture is unstable, send the vendor table yourself over `s_dbi_io` straight after the probe and before `esp_lcd_panel_init` (the driver's later writes are idempotent). Alternatively, fork the driver so its leading SLPOUT is skipped when `init_cmds` is supplied.

### F4. MINOR (firmware): glitch on the reset gate during configuration
- **Evidence:** `init_display` calls `gpio_config(OUTPUT)` and only then `gpio_set_level(…,1)`. In between, GPIO10 drives its default output latch, 0, which releases RESX for some µs. U1.11 is GPIO10 ([P4] Table 2-1).
- **Why it matters:** RESX goes high and then gets a 10 ms low pulse, which is still a valid reset (≥10 µs, [ILI] Table 47). It is harmless today, but it is a trap if timings change.
- **Fix:** call `gpio_set_level(SLIM4_GPIO_LCD_RESET_GATE, 1)` before `gpio_config`.

### F5. MINOR (firmware): the backlight can be enabled when no panel answered
- **Evidence:** `s_backlight_ready` is set right after `init_backlight()`, before the probe (`slim4_board.c:799-802`). The new console `bl <n>` (commit af0771a) calls `slim4_board_set_backlight`, which works even when the probe failed.
- **Why it matters:** with the tail unseated, the boost runs into open-LED protection. [TPS] §8.3.2 says it shuts down after 8 cycles, but SW and LED_A reach 37–39 V on every CTRL re-enable. That is close to D2's 40 V rating and puts the 38 V spike on J1.38 next to a half-inserted tail.
- **Fix:** set `s_backlight_ready` only after the probe answers, or let the console refuse `bl` unless `s_probe.answered`.

### F6. MINOR (firmware / documentation): the stated pixel clock is not what is generated
- **Evidence:** the log and docs say "78 MHz pixel clock". The real DPI clock is 80 MHz (240 MHz / 3), and IDF stretches the bridge HFP from 120 to about 144 to hold 59.06 Hz (`mipi_dsi_hal.c:240-260`).
- **Fix:** log `real_dpi_clock_freq_mhz`, or choose a value that divides exactly.

### F7. MINOR (mechanical / documentation): FPC fold geometry and latch description
- **Evidence:**
  - [CFAF] p.5: tail 40 ±0.5 mm from the module edge. The side view shows the FPC leaving flush with the front face, 0.30 mm thick.
  - [HRS] p.7 mated cross-section: the FPC goes (5) mm in from the housing front.
  - The KiCad footprint puts the housing rear at local y −1.2 and the front about 5.0 mm south, so a fully inserted tail ends near Y ≈ 76.0.
  - With a 2 mm straight run and an r = 1.5 mm fold, the tail end reaches Y ≈ 109.8 + 2 − (40 − 2 − 4.7) = 78.5. With r = 2 mm (fold diameter about 4 mm to drop from the front plane to J1's slot) it reaches about 80.
  - The actuator in [HRS] p.7's side view hinges at the insertion side. FH12 is a front flip-lock.
- **Why it matters:**
  - Either the panel moves 2.5–4.5 mm north (bottom edge at Y ≈ 105–107.3, overhang 16–18 mm instead of 13.6), or the tail is not fully inserted. A partly inserted tail gives intermittent contacts that are hard to diagnose.
  - Following DISPLAY_PORT.md step 3 ("lift the dark actuator on the side away from the mouth") means prying at the solder-tail side.
  - Only the case and the docs are affected, not the PCB.
- **Fix:** correct DISPLAY_PORT.md step 3: flip the actuator up at the mouth side. Insert until the tail stops, so that the ~3.5 mm gold area is fully hidden, and let the panel position follow. Re-derive the panel Y position from a measured sample for the case pass.

### F8. MINOR: two LED strings driven in parallel from one sense resistor
- **Evidence:** [CFAF] p.8 shows two 7-LED strings with a common anode (J1.38) and cathodes LED1−/LED2− on J1.39/40. The netlist joins J1.39 and J1.40 on LCD_LED_K into U7.6 FB and R309 (2.7 Ω, 0603WAF270KT5E, 1 %, JLC C22946). [TPS] §7.4 gives VREF 196–204 mV, so 72–76 mA in total. [CFAF] §6.6: ILED 40 mA typical, power 1.68 W typical, which at about 21 V is about 80 mA, so roughly 40 mA per string.
- **Why it matters:** the average is 37 mA per string. A Vf mismatch between strings (19.6–23.8 V spread across parts) splits the current unevenly, and the stronger string can exceed 40 mA, which shortens LED life. This is the vendor's own topology, so it is not a failure.
- **Fix (optional):** use R309 = 3.0 Ω (67 mA total). Otherwise accept it; the firmware already runs at 45 %.

### F9. MINOR: boost headroom at low battery
- **Evidence:** [TPS] §9.1.1 Eq.1–2, worst case with ILIM 0.96 A, L = 10 µH −20 %, fs 1.0 MHz, η 0.8, Vout = 23.8 + 0.2 + 0.4 (D2):
  - Iout_max ≈ 78 mA at VIN 3.0 V and ≈ 85 mA at 3.3 V, against 76 mA needed.
  - Dmax is 90 % minimum, and about 88–90 % is needed at 3.0 V.
  - SYS_RAW ≈ VBAT − 0.1 V. The firmware cuts off at VBAT < 3.3 V.
  - Inductor peak about 0.8 A at 3.2 V, against L3 WPN4020H100MT Isat 2.8–3.5 A (distributor data) and DCR 216 mΩ.
- **Why it matters:** with a high-Vf panel at full brightness near cut-off, LED current falls out of regulation (dimmer, no damage).
- **Fix:** none needed. Optionally limit full brightness below VBAT 3.4 V.

### F10. MINOR: C309 effective capacitance and D2 voltage margin
- **Evidence:**
  - C309 is CL10A105KB8NNNC, 1 µF 50 V X5R 0603. At 24 V DC bias it gives roughly 0.4–0.5 µF. [TPS] §7.2 asks for 1–10 µF and §9.1.5 warns about DC bias.
  - D2 is STPS1L40ZFY, 40 V, against an OVP of 37–39 V ([TPS] §7.4). [TPS] §9.1.3 requires a breakdown voltage above OVP, and TI's own example diode, MBR0540, is also 40 V.
- **Why it matters:** loop stability and ripple, and little margin for ringing during an open-LED event.
- **Fix (optional):** 2.2 µF 50 V X7R 0805 for C309. A 60 V Schottky in SOD-123F (for example STPS1L60ZF or SS16-class) if one is in stock.

### F11. MINOR (power): panel rails are always on, and reset is held through R307 in sleep
- **Evidence:**
  - U5 TLV75518P and U6 ME6211C30 have EN tied to 3V3_SYS (U5.3 and U6.3 on 3V3_SYS).
  - In deep sleep, GPIO10 goes high-Z, R308 turns Q1 on, and RESX is held low, so R307 (10 k from LCD_1V8) draws 180 µA.
  - [ILI] §18 DC characteristics ("Standby mode current consumption") gives sleep-in currents of VDDI 35 µA and VCI 25 µA. Add the two LDO quiescent currents of about 25 + 40 µA.
  - There is no way to power-cycle the panel short of removing the battery.
- **Why it matters:** about 0.3 mA "off" drain, roughly 4 months for a 1000 mAh cell. A latched-up panel cannot be recovered by software.
- **Fix:** R307 can be 100 k (RESX is a CMOS input; a 2N7002 still holds it low). For a later revision, put the LDO EN pins on a GPIO, or put a load switch on the panel rails.

### F12. BRINGUP-CHECK: placement and rotation of J1
- **Evidence:** J1 is the only connector on F.Cu, at (1.9, 76.0), rotation 0. Pad 1 is at local (−9.75, −1.85), so board X −7.85. Signal pads are on the north side and the MP tabs (±11.65, +1.4) on the south side, so the mouth faces +Y. This matches [HRS] p.11 (A 19.5, B 25.1, C 21.5, MP 1.8 × 2.2, 1.5 mm gap).
- **Fix:** in JLCPCB's placement preview, check that the FH12A model's solder tails sit on the 40-pad row and the actuator faces south. A 180° error turns the mouth toward U1, and the panel can then only be inserted with its contacts facing the board, which mirrors the connection.

---

## UNSURE (what would settle each)
- **U1. FPC contact side and pin-1 direction.**
  - Evidence from [CFAF] p.5:
    - The rear view (plain outline, tail 22.1 mm from the left, which is the mirror of the front view's 23.5 mm) carries Detail A with the contacts drawn and pin 40 on the left, pin 1 on the right.
    - The front view shows only a stiffener rectangle on the tail end.
    - In the side view the "Pins" leader points to the rear side.
  - So the contacts are on the rear, and pin 1 is on the left in the front view. After the fold, pin 1 is at west and the contacts face up, which needs a top-contact FH12A with pad 1 at west. The board has exactly that.
  - **Settle:** before ordering, take one panel and one FH12A-40S sample. The gold fingers should be on the side opposite the stiffener, which is the backlight side. Then check that the J1-equivalent pin 1 lines up with VCI/NC (pins 1–13 NC/VCI) on the west. Optionally email Crystalfontz. This is the only total-loss failure mode in this subsystem, and the check costs about $30.
- **U2. Is ILED 40 mA per string or in total?** The 1.68 W figure implies per string, which makes 74 mA OK. **Settle:** ask Crystalfontz, or measure the current split with a 1 Ω shunt on one cathode on a bench panel.
- **U3. Does this module run at 1000 Mbit/s on 2 lanes (F1)?** **Settle:** at bring-up, a stable `pattern checker` with no host or panel error flags in the probe, for 10 minutes.
- **U4. Do the module's FPC labels D0/D1 match the controller's logical lanes 0/1?** [ILI] Table 2 shows that for every IM[2:0] strap, logical lanes 0 and 1 sit on the same pads in 4-lane and 2-lane mode, so B7h = 03 cannot move them. **Settle:** the probe's LP read proves D0, and an image proves D1.
- **U5. Actual ID3 value (F2).** **Settle:** read it on the first board.
- **U6. VCI current of the module's internal power IC (not specified).** ME6211 is rated 500 mA, and 3.31 V in for 3.0 V out leaves 310 mV of headroom. **Settle:** measure the drop across U6 with the image on.
- **U7. Tail reach (F7).** **Settle:** measure it with a sample panel and calipers.

---

## VERIFIED OK (coverage)
- **J1 pin table** against [CFAF] §6.2 p.6 and the p.5 table:
  - 1–9 NC (touch reserved): no net.
  - 10–11 VCI: LCD_VCI_3V0. 12–13 NC: no net. 14 RESET: LCD_RESX.
  - 15 TE: open ("Leave open when not in use"). 16 NC: no net.
  - 17, 18, 21, 24, 27, 30, 33, 36, 37: GND. 19–20 IOVCC: LCD_1V8.
  - 22/23 D3P/N and 25/26 D2P/N: open ([ILI] p.23, "Leave it open … when not in use").
  - 28/29 CLKP/N: MIPI_DSI_CLK_P/N. 31/32 D1P/N: MIPI_DSI_D1_P/N. 34/35 D0P/N: MIPI_DSI_D0_P/N.
  - 38 LED+: LCD_LED_A. 39/40 LED1−/LED2−: LCD_LED_K. MP pads: no net (fine).
- **U1 DSI pads** against [P4] Table 2-1: 34 DSI_REXT (R103, 0402WGF4021 = 4.02 k, the value Espressif specifies), 35/36 DATAP1/N1 (D1_P/N), 37 CLKN (CLK_N), 38 CLKP (CLK_P), 39/40 DATAP0/N0 (D0_P/N), 41 VDD_MIPI_DPHY plus 73 VDDO_3 on VDDO_MIPI_2V5 (C107 10 nF, C108 100 nF, C109 and C122 1 µF). The firmware sets LDO VO3 (chan 3) to 2.5 V before the bus is created. Every pair is P to P and N to N end to end, so no lane or polarity swap is needed.
- **ILI9881C 2-lane mode:** [ILI] §5.4.14 B7h, LANSEL_SW_EN plus LANSEL_SW = 1 gives 2 lanes (the driver writes 03h on page 1). The vendor table never writes B6h/B7h, and Page 4 00h keeps its default 80h. Lane mapping is invariant (U4).
- **DSI routing** (R26_DSI_REPORT and README): coupled pairs 44.32–44.54 mm, intra-pair skew ≤ 0.031 mm, inter-pair spread 0.201 mm, P and N through the same vias, reference planes continuous, impedance control ordered. Two GND pins sit between pairs at J1. At ≤ 1 Gbit/s over about 90 mm in total (board plus FPC) this is ample.
- **Supplies:**
  - VCI 3.0 V from U6 ME6211C30M5G-N (SOT-23-5 VIN/VSS/CE/NC/VOUT, CE tied to IN, 500 mA, C307 1 µF in, C308 1 µF out), within 2.5–3.6 V ([CFAF] §6.4).
  - IOVCC 1.8 V from U5 TLV75518PDBVR (IN/GND/EN/NC/OUT, EN tied to IN, 500 mA, C304 100 nF and C306 1 µF out), within 1.65–3.6 V. IDD is 44 mA typical.
  - [ILI] §18 DC characteristics note 2 requires VDDI ≤ VCI: 1.8 ≤ 3.0.
- **Power sequence** against [ILI] §12.1.2 Power Mode 3: rails come up at boot with RESX held low (R308 pull-up, GPIO10 has no pull at reset per [P4] Table 2-1). The firmware then sees:

  | Parameter (ILI9881C) | Required | Firmware |
  |---|---|---|
  | TPS_RES (power to reset high) | ≥ 5 ms | seconds |
  | TRES_PULSE (reset low) | ≥ 10 µs | 10 ms |
  | TFS_CMD (reset to first command) | ≥ 10 ms | 120 ms |
  | tRT (reset cancel) | ≤ 120 ms | 120 ms wait |

  The lanes are in LP-11 (DSI bus created) before RESX rises.
- **Reset polarity:**
  - Q1 2N7002 (SOT-23 G=1, S=2, D=3): G on LCD_RESET_GATE (U1.11 = GPIO10, R308 100 k to 3V3), S to GND, D on LCD_RESX (R307 10 k to LCD_1V8).
  - GPIO10 high turns Q1 on and pulls RESX low (reset). GPIO10 low releases it to 1.8 V, which is ≥ 0.7 × IOVCC.
  - The firmware drives it high to assert reset, which is correct. In deep sleep the pin is high-Z and the panel is held in reset.
- **TPS61165 (U7, DBV)** against [TPS] p.3: 1 VIN (SYS_RAW, C311 4.7 µF), 2 CTRL (BACKLIGHT_PWM = U1.10 GPIO9, R422 100 k pull-down), 3 SW (BL_SW to L3 and D2.A), 4 GND, 5 COMP (C310 220 nF, as §9.1.4 recommends), 6 FB (LCD_LED_K and R309 to GND). L3 10 µH is within the 10–22 µH range. D2 cathode on LCD_LED_A with C309, 50 V rated (above OVP). 7 × VLED max 23.8 V + 0.2 V < 37 V OVP minimum. VIN 2.9–4.4 V is within 3–18 V.
- **PWM:** 20 kHz LEDC is within the 5–100 kHz fdim range ([TPS] §7.2). The low time is ≤ 50 µs, under the 160 µs limit, so EasyScale is never entered ([TPS] §9.2.1.2.1). Duty 0 for > 2.5 ms shuts the boost down. The backlight is turned on only after the boot stamp.
- **Shutdown leakage path:** LED Vf (19.6 V) is well above VIN max (4.4 V) ([TPS] §8.4.1).
- **Init sequence origin:** `slim4_panel_cfaf.c` matches [LNX] `cfaf7201280a0_050tx_init` entry for entry (scripted compare: 191 = 191, identical). The appended page 0, 35h 00, 11h (120 ms) and 29h follow [LNX] prepare and enable.
- **Video timing:** 720 + 120/2/80 and 1280 + 60/2/90 equal [LNX] `cfaf7201280a0_050tx_default_mode` (78 MHz). Burst with sync pulses (IDF) is acceptable. RGB565 (DT 0Eh) is supported by the ILI9881C ([ILI] p.17 and §4.2.1.1). The COLMOD 55h written by the driver matches 16 bpp, and the vendor table writes no page-0 3Ah or 36h that would override it (its 3Ah is on page 4, a different register).
- **Firmware probe validity:**
  - The page select is a DCS long write (DT 39h) of FF 98 81 01 on VC0, as Linux does.
  - The reads use Set Maximum Return Packet Size = 1, then DCS Read with no parameter (06h) of 00h/01h/02h. [ILI] §4.1.3.3.2.4 supports this sequence, and the registers are readable in Sleep In ([ILI] p.181).
  - The probe returns to page 0. It runs in command mode: IDF enables video only in `dpi_panel_init`, at `esp_lcd_panel_dpi.c:469`.
  - It runs after the DBI IO enables command ACK and LP mode, so its "wait for idle and stop state" logic matches what IDF itself does without time limits.
  - The LP escape clock is 1000/8/18 rounded to a divider of 7, so 17.9 MHz and TLPX ≈ 56 ns, inside [ILI] Table 42's 50–75 ns.
- **No ESD or termination parts are needed** on DSI. The ILI9881C terminates HS internally, and the panel is a captive FPC.
- **FH12A land pattern:** [HRS] p.11 gives one land for top and bottom contact. The recommended FPC is 20.5 wide, contacts ≥ 3.5 mm, 0.3 ± 0.05 thick, which [CFAF] p.5 matches: 20.50 ± 0.10, 3.50, 0.30 ± 0.05, conductors 0.35.
- **Clearance:** nothing on F.Cu except J1 under the tail path. SW3 and SW4 are at Y 119.3, X ±16, clear of the 20.5 mm tail centred at X 1.9.

---

## Bring-up probe table
Measure with U1 running the R11+ firmware unless stated. "Unplugged" means no panel in J1 (latch closed, empty).

| # | Point (ref.pin / net) | State | Expected | A wrong reading means |
|---|---|---|---|---|
| 0 | J1.39/40 to GND (or R309) | unpowered, unplugged | 2.7 Ω (meter lead offset subtracted) | open: R309 missing or FB route open. 0 Ω: K shorted to GND |
| 0b | J1.14 to J1.19 | unpowered | 10 k (R307) | open: R307 missing or J1 joint open |
| 0c | J1.38 to GND | unpowered | > 1 MΩ after C309 charges (diode-test direction: D2 blocks) | low: C309 or D2 short. Fix before power (38 V node) |
| 0d | Each DSI pin (28, 29, 31, 32, 34, 35) to its neighbour GND pin | unpowered, unplugged | > 100 kΩ | low: solder bridge at the 0.5 mm pitch (most likely J1 assembly defect) |
| 1 | LCD_VCI_3V0 at C308 or J1.10/11 | both | 3.00 V ± 2 % | 0 V: U6 missing or reversed, or 3V3_SYS absent. ~3.3 V: wrong LDO fitted |
| 2 | LCD_1V8 at C306 or J1.19/20 | both | 1.80 V ± 1.5 % | 0: U5 fault. Drops plugged-in: IOVCC short on the panel or a J1 bridge to GND |
| 3 | VDDO_MIPI_2V5 at C109 (U1.41/73) | after display init | 2.50 V | 0: VO3 LDO not enabled, so DSI dead |
| 4 | LCD_RESET_GATE at Q1.1 or R308.2 | download mode or before init / after release | 3.3 V / 0 V | stuck 3.3 V: firmware not releasing, or U1.11 open. Stuck 0: R308 missing |
| 5 | LCD_RESX at J1.14 or Q1.3 | before release / after release | < 0.05 V / 1.80 V | 1.8 V while gate high: Q1 open or misplaced. 0 V after release: Q1 shorted, R307 open, or a panel short |
| 6 | DSI lines (J1.28–35), DMM DC | bus idle (LP-11, probe failed) | ≈ 1.1–1.3 V each line | 0 V on one line: open route or U1 pad. Equal on P and N but 0: VO3 off |
| 6b | Same, oscilloscope ≥ 1 GHz, differential | video running | 200 mV diff (about 400 mV unplugged), common mode ≈ 200 mV, LP-11 bursts each line | no HS on D1 or CLK: open. A "panel probe" FAIL with good D0 voltages points at the FPC seating |
| 7 | BACKLIGHT_PWM at U7.2 | before or after init | 0 V / 20 kHz, 0–3.3 V, DMM ≈ 0.45 × 3.3 = 1.5 V at 45 % | DC 3.3 V before init: GPIO9 driven, so boost ran with no panel |
| 8 | LCD_LED_A at C309 or J1.38 | backlight off (CTRL low) | ≈ SYS_RAW − 0.3 V (path L3 then D2) | 0: L3 or D2 open |
| 8b | LCD_LED_A | plugged, backlight on | 19.8–24.0 V (VLED + 0.2) | ≈ SYS_RAW: OVP latched (LED path open: tail not seated, J1.38–40 joints) or U7 off. > 25 V: one string open (check per-string current) |
| 8c | LCD_LED_A | unplugged, backlight on (avoid; see F5) | one spike to 37–39 V, then ≈ SYS_RAW (latched) | staying at 38 V would mean OVP not latching. Anything > 40 V: stop (D2 and SW at their ratings) |
| 9 | LCD_LED_K at R309.1 or U7.6 | plugged, `bl 100` (cap allowing) | 200 mV ± 2 %, so 74 mA. At 45 %: ≈ 90 mV (PWM sets VFB = duty × 200 mV) | 0 V with LED_A ≈ SYS_RAW: LEDs not connected. Higher than 200 mV: R309 is the wrong value (current is 0.2/R regardless) |
| 9b | Current per string (1 Ω in series with J1.39 or 40, or a clamp meter on a breakout) | plugged, 100 % | 30–44 mA each, sum 74 mA | > 40 mA in one string: imbalance (F8); consider R309 3.0 Ω |
| 10 | BL_SW at U7.3, oscilloscope | plugged, on | 1.0–1.5 MHz, 0 to Vout + 0.4 V, no subharmonic | erratic duty: loop instability (C309 derating, F10) |
| 11 | SYS_RAW at C311 during backlight 0 → 100 % | battery | droop < 150 mV, soft-start about 7 ms (32 × 213 µs) | large droop: input decoupling. Resets: brown-out budget (power reviewer) |
| 12 | Console `panel` | plugged | `answered, ID 98 81 xx`, no host flags, about 59 fps | no answer: D0, RESX or supplies, or tail upside down (U1). Image noise only: F1 lane-rate profile |
