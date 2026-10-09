# SLIM4 R26: ESP32-P4 core (U1) and flash (U2) review

## Summary (10 lines)

1. **No BLOCKER found.** All 105 U1 pads match the ESP32-P4 v3 QFN104 pin table (datasheet v0.7, Table 2-1). Every supply domain is fed at a legal voltage, and pad 54 is VDD_HP_1 as v3 requires.
2. The core supply copies Espressif's v3 TLV62569 circuit exactly (499 k / 499 k / 22 pF, 2.2 µH, 22 µF; HDG Fig. 5). U3's pinout and its EN/FB wiring to pads 79/78 are correct.
3. Flash U2 (W25Q512JV-IQ) is wired pin-for-pin per datasheet Table 2-15 and Winbond Fig. 1a, on VDDO_FLASH at 3.3 V. The firmware's DIO at 80 MHz is within the part's 133 MHz rating. QE is fixed at 1 on "IQ" parts, so QIO would also work.
4. Straps: GPIO35 is pulled up (SPI boot) and GPIO36 is pulled up (joint download when BOOT is held), which is correct. GPIO34 is pulled down, which is harmless with factory eFuses, but the docs state its meaning backwards (m1).
5. CHIP_PU timing meets tSTBL ≥ 50 µs and tRST ≥ 1 ms: the TPS3808G33 (3.07 V, 20 ms) plus 10 k / 1 µF gives about 34 ms.
6. **MAJOR M1:** U3 sits 12–21 mm from U1. FB_DCDC is a 33 mm trace (2 vias) and EN_DCDC is 25.5 mm, against HDG Fig. 1 "IMPORTANT: Please place DCDC close to P4".
7. **MAJOR M2:** U1's four VDD_HP pins have only 4 × 100 nF next to them. The only bulk capacitor (22 µF) is 13–16 mm away at L2. The reference has 10 µF at VDD_HP_0 as well.
8. **MAJOR M3:** U1's exposed pad is the chip's only GND connection, and it has just 4 vias (0.2 mm drill) to the ground planes.
9. MINOR: missing 10 µF on VDD_LDO/VDD_DCDCC; LDO-output capacitors placed far from their pins; VDDO_4 left without a capacitor; long CHIP_PU and crystal traces with vias; 0 Ω instead of 22 Ω on the USB lines; no UART0 or recovery test pads; several documentation errors.
10. Bring-up: buy chip revision v3.1 or later, and expect 1V1_HP ≈ 1.25 V (not 1.2 V) once the app runs, VDDO_PSRAM = 1.8 V (not 1.9 V), and VDDO_FLASH possibly 0 V in download mode until esptool turns it on.

Severity counts: BLOCKER 0 · MAJOR 3 · MINOR 12 · BRINGUP-CHECK 7 · UNSURE 7.

### Sources used (cited below by short name)
- **DS**: ESP32-P4 Series Datasheet v0.7 (covers ESP32-P4NRW16X/32X, chip revision v3.x; Table 1-1), espressif.com/sites/default/files/documentation/esp32-p4_datasheet_en.pdf. Page numbers are the printed page numbers.
- **HDG**: ESP32-P4 Hardware Design Guidelines, release "master", dated Oct 09 2026 (docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32p4/). Fig. 1 is the v3 reference schematic, the same circuit as the ESP32-P4-Function-EV-Board core.
- **ERR**: ESP32-P4 Series SoC Errata v1.3 (esp-chip-errata, master).
- **TLV**: TI TLV62569 datasheet SLVSDG1C. **TPS**: TI TPS3808 datasheet SBVS050N.
- **W25**: Winbond W25Q512JV datasheet Rev B (2019-06-25, LCSC copy for C7389628). **XT**: Lucki L327S400H11L datasheet (LCSC C5261245).
- **IDF**: ESP-IDF v6.1 at ~/esp/esp-idf.
- **Board data**: R26_NETLIST.txt; u1_pad_nets.json (identical to the netlist's U1 rows); positions, tracks and vias from SLIM4_R26_PCB_LAYER.json and SLIM4_R26.kicad_pcb (read-only).
- **EV**: ESP32-P4-Function-EV-Board schematic v1.5.2 (dl.espressif.com/dl/schematics/esp32-p4-function-ev-board-schematics_v1.5.2.pdf).
  - It marks the 499 k / 22 pF DC-DC feedback parts as (NC), which is the v1.x arrangement. HDG Fig. 1 is therefore used as the v3 reference.
  - Page 3 "Boot Strapping Pins": GPIO35 and GPIO36 have 10 k pull-ups (R208/R209); GPIO34/37/38 go only to test points and headers.
  - Reset is 10 k + 100 nF.
  - Page 2: 33 Ω series resistors R105 (GPIO25) and R228 (GPIO26).
  - The EV-board PCB layout was not examined (see U3).

---

## Findings

### MAJOR

**M1. The core DC-DC (U3) and its feedback network sit far from U1. FB_DCDC is a 33 mm, high-impedance trace.**
- Evidence:
  - Positions: U3 (TLV62569DBVR) is at (0, 101.0). R104/R105/C134 are at (−4.5, 99.6–103.0). U1.78 FB_DCDC is at (−4.875, 79.625) and U1.79 EN_DCDC at (−4.375, 79.125), both on U1's north-west corner. Straight-line distance from FB to the divider is 20 mm.
  - Routed lengths: FB_DCDC is 33.3 mm (F.Cu 17.0 + B.Cu 16.3, 2 vias, 0.114–0.152 mm wide). EN_DCDC is 25.5 mm (2 vias).
  - FB_DCDC runs 0.151 mm from CHIP_PU on F.Cu for 5 segments. U3 is 12 mm from U1's body edge.
  - FB node impedance is 499 k ∥ 499 k = 250 kΩ. TLV §8.2.2.2 recommends R2 ≤ 200 kΩ "to achieve … acceptable noise sensitivity". Espressif mandates 499 k for v3 (HDG §1.3.2, Fig. 5), so the high impedance cannot be changed. That makes trace length the only thing the layout controls.
  - HDG Fig. 1 note: "IMPORTANT: Please place DCDC close to P4." HDG §1.3.2: "ensure that they [EN_DCDC, FB_DCDC] are connected … and that the DCDC regulator is placed close to the ESP32-P4." HDG §1.4.1: "the external DCDC should be placed close to the chip to ensure that the input, output, and feedback loops are as short as possible."
- Why it matters:
  - DS §2.5 Table 2-11 and HDG §1.3.2 say FB_DCDC is driven by the P4's internal circuitry. The chip sets VDD_HP by working into the feedback network (IDF `rtc_clk_init.c` lines 69–86 sets `dcm_vset`).
  - The 2nd-stage bootloader enables the DC-DC and then switches the internal HP regulator off (`pmu_ll_hp_set_regulator_xpd(..., false)`). From then on, VDD_HP depends entirely on this loop.
  - Noise picked up on a 33 mm, 250 kΩ node moves the core voltage directly. Symptoms would be random resets or crashes that start right after the ROM stage. The ROM stage runs on the internal LDO, so this would not show up as "no boot log".
  - Nothing switching runs next to FB_DCDC today. The nearest nets are CHIP_PU, EN_DCDC, 3V3 and 1V1. The risk is therefore moderate, but the design departs from an instruction Espressif marks "IMPORTANT".
- Fix:
  - Preferred: move U3, L2, C135, C126 and R104/R105/C134 to the west/north-west side of U1, next to pads 76–79. Target FB_DCDC and EN_DCDC ≤ 5 mm with no layer change.
  - Minimum: keep R104/R105/C134 at U3 (TI rule: divider at FB). Reroute FB_DCDC as a guarded trace with GND on both sides and a continuous ground plane underneath. Keep it ≥ 0.3 mm from CHIP_PU and from any clock or switching net.

**M2. No bulk capacitor at U1's VDD_HP pins.**
- Evidence:
  - 1V1_HP decoupling at U1: C103 (pad 26, 1.43 mm), C105 (pad 54, 1.44 mm), C125 (pad 76, 1.56 mm), C129 (pad 91, 1.23 mm). All four are 100 nF (CL05B104KO5NNNC).
  - The only bulk is C135, 22 µF (CL21A226MQQNNNE), at L2's output. It is 16.3 mm from pad 26 and further from pads 76 and 91. The path is a reshaped In2 plane, which the README itself estimates at 15–20 mΩ.
  - The HDG Fig. 1 reference has C28 10 µF + C29 100 nF at VDD_HP_0, in addition to C3 22 µF at the DC-DC.
  - HDG §1.3.2 "Digital Power Supply": "place a 10 μF capacitor at the main power source and 0.1 μF capacitors near each power pin." HDG §1.4.1: "Place a 10 µF capacitor at the power entry point for this series of power supply."
  - DS Table 5-2: VDD_HP range is 0.99–1.3 V, I_VDD 0.5 A.
- Why it matters:
  - When active, the DC-DC sits at about 1.25 V (IDF `pmu_param.h:24` `HP_CALI_ACTIVE_DCM_VSET_DEFAULT 27 // about 1.25v`). That is only 50 mV under the 1.3 V absolute maximum (DS Table 5-1).
  - The floor is 0.99 V. Load steps from a 400 MHz dual core plus PSRAM at 200 MHz must be absorbed through about 15 mm of plane with only 400 nF locally.
  - Both overshoot when load is released and undershoot when it is applied matter here.
- Fix: add one 10 µF X5R (0603 or 0805, ≥ 6.3 V) on 1V1_HP within 3 mm of U1, at the In2 1V1 via feeding pads 76/91 or 26/54. Ideally add two, one on each side. This is one BOM line, already used on the board as CL21A106KAYNNNE.

**M3. U1's exposed pad, the chip's only ground connection, reaches the ground planes through only 4 vias.**
- Evidence:
  - DS Table 2-1/2-12: pad 105 "GND – External ground connection" is the only GND pin of the QFN104. The footprint uses nine 2.1 mm tiles at a 2.7 mm pitch, an outer extent of 7.5 mm, matching DS Fig. 6-1 D2/E2 7.5 mm nominal.
  - Vias inside that 7.5 mm square: 4 GND vias (0.45 / 0.2 mm), at (−1.29, 85.29), (0.255, 87.07), (0.719, 87.07) and (1.627, 87.07). Two are inside tile (0, 86.7) and two in the gaps between tiles.
  - There is no GND copper pour on B.Cu (zones near U1: GND only on In1, In4 and a small In2 band). U1 is on B.Cu, so every return current goes EP → 4 vias → In4/In1.
- Why it matters:
  - The whole chip's return current, including core at up to about 0.5 A, three 50 mA LDOs, IO and the DSI PHY, passes through 4 vias. Shared inductance in that path adds ground bounce to every rail at the die.
  - Thermal: the EP is the main heat path. A rough estimate is about 50 K/W through 4 plated 0.2 mm barrels on a 1.2 mm board.
  - The README does not mention this. It is a cheap fix while the board is still in CAD.
- Fix:
  - Add GND vias in the EP: at least one per tile (9) plus the tile gaps, giving 16 or more. A 0.2 / 0.45 mm via can go into the 0.6 mm gaps.
  - Via-in-pad is already ordered as "epoxy filled and capped (POFV)" (`CHECKS/build_builder_packs.py` line 306), so vias in the tiles do not wick solder.
  - Keep them clear of the In3 DSI lanes under U1, and re-run `dsi_pair_check.py`.
  - The severity rests on general practice. Espressif's own via count was not seen (UNSURE U3).

### MINOR

**m1. GPIO34 strap: the documented meaning is backwards. It is harmless only while eFuses stay at default.**
- Evidence:
  - U1.65 GPIO34 is net STRAP_GPIO34, pulled down by R107 10 k (0402WGF1002TCE) to GND.
  - DS §3.4, Table 3-7: with factory eFuses (EFUSE_DIS_PAD_JTAG = 0, DIS_USB_JTAG = 0, JTAG_SEL_ENABLE = 0), GPIO34 is ignored and JTAG comes from USB-Serial-JTAG. Only with JTAG_SEL_ENABLE = 1 does GPIO34 matter: 1 = USB-Serial-JTAG, 0 = JTAG pins.
  - IDF `soc/esp32p4/register/hw_ver3/soc/io_mux_reg.h:363`: "USB2JTAG select: 1->usb2jtag 0-> pad_jtag".
  - ELECTRICAL_REVIEW_R22.md says "GPIO34 pull-down (JTAG from USB-Serial-JTAG)" and "GPIO34 strap low selects USB-Serial-JTAG". Both are wrong.
- Why it matters: if anyone burns JTAG_SEL_ENABLE, the low strap would hand GPIO2–5 to pad JTAG. Those pins are BTN_RIGHT, DART_LEFT, DART_RIGHT and I2S_BCLK, and JTAG over USB would be lost.
- Fix: correct the docs. Optionally change R107 to a 10 k pull-up to 3V3_SYS, so the strap selects USB-JTAG in every eFuse state. Never burn JTAG_SEL_ENABLE.

**m2. VDD_LDO (pad 75) and VDD_DCDCC (pad 77) have no local 10 µF and share one 100 nF.**
- Evidence:
  - The nearest 100 nF is C131, at 2.83 mm from pad 75 and 2.25 mm from pad 77, shared by both.
  - The nearest 10 µF (C123, C133, CL21A106KAYNNNE) are on the east side, more than 11 mm away. C126 (10 µF) is U3's input capacitor, 20 mm away.
  - HDG §1.3.2 "Internal Voltage Regulators and External DCDC": "Due to the high current on these pins, place a 10 μF capacitor on the power traces of VDD_LDO and VDD_DCDCC, and add a 0.1 μF capacitor at each pin." HDG §1.4.1: "place a 10 µF capacitor close to each power pin." The Fig. 1 reference has C14 10 µF + C13 100 nF at VDD_DCDCC and C16 100 nF at VDD_LDO.
- Why it matters: VDD_LDO feeds the flash, PSRAM and MIPI LDOs, each up to 50 mA (DS Table 2-12). VDD_DCDCC feeds the DC-DC control loop of M1.
- Fix: add one 10 µF (0603) and one 100 nF on the 3V3 vias at pads 75 and 77.

**m3. Some 3.3 V pins have shared or remote 100 nF capacitors.**
- Evidence:
  - Pad 62 VDD_IO_4: nearest 100 nF is C124 at 3.64 mm. This pin powers GPIO24–38, which includes USB-JTAG and all the straps.
  - Pads 96 VDD_IO_6, 101 VDD_ANA and 102 VDD_BAT share C117. VDD_BAT has no dedicated 100 nF; the nearest 10 µF is C133 at 4.9 mm.
  - HDG §1.3.2: one 0.1 µF for each of VDD_LP, VDD_IO_x and VDD_ANA. VDD_BAT should have "0.1 μF + 10 μF". The Fig. 1 reference has C7, C11 and C12 separately.
- Fix: add 100 nF at pad 62 and at pad 102. Optionally move C133 (10 µF) next to pad 102.

**m4. Several LDO-output and PHY-supply capacitors are 9–15 mm from their pins.**
- Evidence:
  - VDDO_3 (pad 73): 100 nF C108 at 1.4 mm, but the 1 µF capacitors C109 and C122 are at 9.3 and 10.4 mm.
  - VDD_MIPI_DPHY (pad 41): only the 10 nF C107 is at 1.3 mm; 100 nF and 1 µF are about 9.4 mm away.
  - VDD_FLASHIO (pad 30): 1 µF is 10.6 mm away.
  - C118 (1 µF on VDDO_PSRAM) sits at (9.6, 84), on the opposite side of U1, 15 mm from any PSRAM pin.
  - HDG §1.3.2: "place a 1 μF capacitor near the VDDO_FLASH, VDDO_PSRAM, and VDDO_3/4"; "10 nF + 0.1 μF + 1 μF capacitors near VDD_MIPI_DPHY"; "0.1 μF + 1 μF capacitors near VDD_FLASHIO"; and the same near VDD_PSRAM_0/1.
- Why it matters: an internal LDO with its output capacitor 10 mm away through thin track (VDDO_MIPI_2V5 has 24 mm on In3) can ring. The MIPI D-PHY rail feeds 1 Gbit/s lanes.
- Fix: move C109 or C122 next to pads 73/41, add a 1 µF at pad 30, and move C118 next to pads 59/67. If CAD time is short, treat these as BRINGUP-CHECK B4 instead.

**m5. VDDO_4 (pad 74) is left open with no capacitor.**
- Evidence: U1.74 has no net. DS Table 2-12 lists VDDO_4 as an output, 50 mA. HDG §1.3.2: "The LDO outputs VDDO_3/4 … The default output is 0", and recommends 1 µF near VDDO_3/4. The Fig. 1 reference has C22 1 µF on VDDO_4.
- Why it matters: legal as long as LDO channel 4 is never enabled (the firmware only acquires channel 3). If channel 4 is ever enabled, an output LDO with no capacitor may oscillate.
- Fix: add 1 µF from pad 74 to GND, or document "never enable LDO channel 4".

**m6. The CHIP_PU RC and supervisor sit far from the pad.**
- Evidence: C136 is 14.3 mm from U1.103, U14 is 19.4 mm and R106 is 19.9 mm. The CHIP_PU net is 35.8 mm long (F.Cu 14.8, In3 17.0, B.Cu 4.0) with 5 vias. It runs 0.142 mm from 1V1_HP and 0.151 mm from FB_DCDC on F.Cu. HDG §1.3.3: "To avoid reboots caused by external interferences, make the CHIP_PU trace as short as possible."
- Fix: add 100 nF (CL05B104KO5NNNC) from pad 103 to GND at the pad, or move C136 there. The 1 µF stays the RC timing capacitor.

**m7. The 40 MHz crystal is 13 mm from the chip and its traces have vias.**
- Evidence:
  - Y1 is at (−10, 76.5) and pads 99/100 at (2.6–3.0, 79.1).
  - Routed lengths: XTAL_P 7.9 mm (0 vias) + XTAL_P_SOC 7.0 mm (2 vias); XTAL_N 11.3 mm (2 vias) + XTAL_N_SOC 8.5 mm (2 vias).
  - HDG §1.4.2: "There should be no vias for the clock input and output traces." It also asks for series components near the chip; R207 and R208 are 5.9 and 7.5 mm away.
- Why it matters: the extra stray capacitance and coupling are acceptable for a part with no radio. It is a guideline deviation, and timing accuracy and start-up margin are mildly reduced. Load capacitance: see the VERIFIED list and B5.
- Fix: optional. Bring Y1 within about 5 mm of pads 99/100 on B.Cu with no vias, or accept and measure (B5).

**m8. USB-Serial-JTAG series resistors are 0 Ω, and the pair is long.**
- Evidence:
  - R401/R402 are 0402WGF0000TCE (0 Ω). HDG §1.3.12 and Fig. 13: "recommended to add a 22/33 Ω series resistor … placed close to the chip end."
  - USB_JTAG_DP is 109.9 mm (In3 104.2 mm, 3 vias, including a 1.5 mm piece on In1, the ground-plane layer). USB_JTAG_DM is 108.5 mm (2 vias).
  - HDG §1.4.3 asks for minimal vias and a 90 Ω differential impedance.
- Why it matters: at Full Speed (12 Mbit/s) the link is tolerant and is likely to work. This is the only flashing and console path, so margin is worth having. Espressif's own EV board fits 33 Ω (EV page 2: R105 on GPIO25, R228 on GPIO26).
- Fix: change R401/R402 to 22 Ω (e.g. 0402WGF220JTCE). Remove the In1 segment of D+ if possible.

**m9. No UART0 or recovery access; the "USB_RECOVERY" nets go nowhere; GPIO37/38 straps float.**
- Evidence:
  - USB_RECOVERY_GPIO26 (U1.55) and USB_RECOVERY_GPIO27 (U1.56) are single-pin nets with no track.
  - UART0_TX (U1.69, GPIO37) and UART0_RX (U1.70, GPIO38) are also single-pin nets. HDG §1.3.6: UART0 is "typically used for download and log printing".
  - GPIO37/38 are strapping pins that float at reset (DS Table 3-1). They are "any value" in Table 3-3, but see U2.
- Why it matters: on a first spin, if USB enumeration fails (U11 ESD part, connector, routing), there is no other way to flash or read the ROM log.
- Fix:
  - Add test pads for UART0_TX, UART0_RX, GND, 3V3_SYS, CHIP_PU, GPIO35 and 1V1_HP. Optionally add pads for GPIO26/27 (the USB FS OTG PHY, a second USB port for ROM download; DS Table 3-3 note 2).
  - Add 10 k pull-ups on GPIO37/38. This idles UART0 high and defines the strap value.

**m10. Documentation errors that will mislead bring-up.**
- (a) VDDO_PSRAM is 1.8 V, not 1.9 V. The firmware sets `CONFIG_ESP_LDO_VOLTAGE_PSRAM_1800_MV=y` (sdkconfig line 2135), and IDF `Kconfig.ldo` offers only 1.8 V. FIRMWARE_PINMAP.md says 1.9 V and the net is named VDDO_PSRAM_1V9. Both 1.8 and 1.9 V are inside DS Table 5-2 (1.65–1.95 V). HDG §1.3.2 gives 1.9 V as "typical".
- (b) 1V1_HP is not simply 0.6 × (1 + 499/499) = 1.2 V. The P4 drives FB_DCDC (DS Table 2-11), and IDF's active setting is "about 1.25 V" (`pmu_param.h:24`). It runs at ~1.1 V (internal LDO, U1) in the ROM stage. DS Table 5-2 footnote: "The chip can automatically adjust the input voltage of VDD_HP_x."
- (c) GPIO34: see m1.
- (d) FIRMWARE_PINMAP.md "Boots as 16 MB (3-byte mode)" versus sdkconfig `CONFIG_ESPTOOLPY_FLASHSIZE_64MB=y` and `CONFIG_BOOTLOADER_FLASH_32BIT_ADDR=y`. ROM boot is 3-byte (W25 §7.1.11, ADP = 0 factory default) and the app uses 32-bit addressing. The wording should say this.
- (e) VDDO_FLASH can be 0 V in joint download mode until esptool turns it on. ERR §3.7: "in Joint Download Boot Mode, the PMU does not power on the flash by default". ELECTRICAL_REVIEW_R22.md tells the tester to expect 3.3 V.
- Fix: correct README_PCB_LAYER.md, FIRMWARE_PINMAP.md and ELECTRICAL_REVIEW_R22.md, and use the probe table below.

**m11. Crystal tolerance is wider than HDG's figure.**
- Evidence: Y1 L327S400H11L: ±10 ppm at 25 °C, ±20 ppm over −40 to +85 °C, CL 10 pF, ESR 20 Ω (XT spec table). HDG §1.3.5: "the accuracy of the selected crystal should be within ±10 ppm".
- Why it matters: that limit is for RF. The P4 has no radio, and USB Full Speed allows ±2500 ppm. Only the RTC/clock drift is affected.
- Fix: none required. Use a ±10 ppm-over-temperature part only if timekeeping matters.

**m12. A DSI via lies under the flash package's exposed pad.**
- Evidence: the MIPI_DSI_D0_P via at (16.6055, 86.1055) and a GND via at (15.0, 86.04) are outside U2's 3.4 × 4.3 mm EP land but under the package's metal EP (W25 §9.1: D2 4.65 × E2 5.2 mm, so the package EP reaches y = 86.33). W25 §9.1 note: "Avoid placement of exposed PCB vias under the pad." The vias are tented (`viasonmask false`, kicad_pcb line 62), so they are not exposed.
- Fix: none needed if tenting is kept. Do not order "untented vias".

### BRINGUP-CHECK

- **B1. Chip revision.** Ask JLCPCB or the supplier for marking "X G XX" (v3.1) or "X H XX" (v3.2), not "X F XX" (v3.0) (ERR Table 1.2). v3.0 has MSPI-749 (an occasional failed power-on boot, recovered by watchdog; ERR §3.3) and Analog-765 (output LDOs unreliable when the peripheral domain is off in light sleep; ERR §3.9). The firmware already enables `CONFIG_P4_REV3_MSPI_CRASH_AFTER_POWER_UP_WORKAROUND=y`. Read the revision from the boot log.
- **B2. 4-byte flash addressing across resets.** Reset a running app with SW6, a WDT timeout and `esp_restart()`, and confirm each reboots. ROM reads in 3-byte mode (W25 §7.1.11, ADP = 0), so a W25Q512JV left in 4-byte mode would not boot after a non-power-cycle reset.
- **B3. 1V1_HP after the DC-DC takes over.** Scope C129 (pad 91) and C103 (pad 26) during CPU or PSRAM stress. Expect 1.20–1.28 V DC, ≤ 1.30 V peak (DS Table 5-1) and ≥ 0.99 V trough (DS Table 5-2). This covers M1 and M2.
- **B4. VDDO_MIPI_2V5 ripple and ringing** at C108/C107 with the display running (m4).
- **B5. 40 MHz crystal frequency** with a counter (see the probe table). Expect within about +25 / −25 ppm. Estimated effective load: 12 pF ∥ 12 pF = 6 pF plus about 2–4 pF stray, against CL 10 pF, so a few ppm fast at most.
- **B6. EN_DCDC while CHIP_PU is held low.** Measure with SW6 held. TLV §7.4.1: "The EN input must be terminated and should not be left floating" (see U4).
- **B7. Deep-sleep wake on GPIO0.** Confirm SW5 wakes the board via EXT1 `ESP_EXT1_WAKEUP_ANY_LOW`. GPIO0 = LP_GPIO0 (DS Table 2-5) = RTCIO channel 0 (IDF `rtc_io_channel.h:10`). Measure deep-sleep current.

### UNSURE (with what would settle each)

- **U1. 1V1_HP voltage in download mode / ROM.** HDG §1.3.2 says EN_DCDC stays 0 in download mode. IDF shows the internal HP regulator is on until `rtc_clk_init` turns it off, which suggests VDD_HP shows about 1.1 V, not 0 V. To settle: measure on the first board, or read the TRM power-management chapter.
- **U2. GPIO37/38 floating during download mode.** DS Table 3-3 and HDG Table 4 say "Any value". IDF `soc/esp32p4/include/soc/boot_mode.h` decodes a 4-bit strap word in which 01xx patterns map to legacy-SPI/ATE/SPI-download/diag-UART modes, and Espressif's guide shows a download boot log of `boot:0x107` (low nibble 0111). If the ROM uses GPIO37/38 there, floating pins could give an unexpected mode when BOOT is held. Normal SPI boot (GPIO35 = 1) is unaffected. To settle: TRM chapter "Chip Boot Control", or hold BOOT on the first board and check that the log reads `DOWNLOAD(USB/UART0/SPI)`. Cheap mitigation: 10 k pull-ups on GPIO37/38 (m9). Lower likelihood: Espressif's EV board (page 3) also has no pull resistors on GPIO37/38. It does wire them to a header and test points (CNN_GPIO37/38), whose levels in its own download test are unknown.
- **U3. Espressif's EP via count and DC-DC placement on the Function-EV-Board layout.** The schematic (v1.5.2) was read, but the layout files were not. To settle: open the EV-board PCB (or the ESP32-P4 KiCad footprint Espressif publishes) and count EP vias and the U1–DC-DC distance (M1, M3).
- **U4. EN_DCDC drive while the P4 is in reset or unpowered.** The reference has no pull-down, which suggests the P4 drives it low. If it floats, the TLV62569 might enable at random, which is harmless at 1.2 V standalone (inside DS Table 5-2). To settle: measure (B6). Optionally add a DNP 1 MΩ pull-down footprint.
- **U5. U1 thermal with 4 EP vias.** To settle: thermal camera at full load (CPU, PSRAM, DSI), case off.
- **U6. 80 MHz DIO timing over flash traces of about 18–25 mm with 4 vias** (FLASH_CLK 7.4 + 11.0 mm). It is likely fine. To settle: run flash read/write stress at 80 MHz, and optionally try QIO (W25 line 830: QE = 1 fixed on "IQ" parts).
- **U7. PSRAM at 200 MHz on v3.0 silicon.** This is a firmware matter. To settle: IDF PSRAM documentation for P4 v3.0 versus v3.1.

---

## VERIFIED OK

### Parts
| Ref | Part (decoded) | Checked against | Result |
|---|---|---|---|
| U1 | ESP32-P4NRW32X: 32 MB in-package PSRAM, v3.x ("X") | DS Table 1-1 | OK. Footprint: 104 perimeter pads at 0.35 mm pitch, 26 per side, 0.20 × 0.65 mm at ±4.875 mm. Order runs clockwise seen from the board top, which is correct for a bottom-side part (DS §6, "anti-clockwise … top view"). EP 7.5 mm (Fig. 6-1). |
| U2 | W25Q512JVEIQ: 512 Mbit, 2.7–3.6 V, WSON8 8 × 6, industrial, QE = 1 fixed | W25 Fig. 1a, §3.2, §7.1.11, §9.4 | OK. Pins 1 /CS, 2 IO1, 3 IO2, 4 GND, 5 IO0, 6 CLK, 7 IO3, 8 VCC match. EP to GND is allowed (W25 §9.1 note). JEDEC ID EF 40 20 (W25 ID table). |
| U3 | TLV62569DBVR: 2 A buck, 0.6 V ref, ILIM 3 A | TLV pin table, §8.2.2.2, Table 4 | OK. Pins 1 EN = EN_DCDC, 2 GND, 3 SW = CORE_SW, 4 VIN = 3V3_SYS, 5 FB = FB_DCDC. VIN equals VDD_DCDCC as HDG §1.3.2 requires. |
| L2 | Sunlord ASWPA4035S2R2MT: 2.2 µH, Isat ≥ 4.35 A | HDG Fig. 5; TLV Table 4 | OK. 2.2 µH with 22 µF is TI's "++" for 1.2–1.8 V; Isat is above ILIM of 3 A. |
| R104/R105 | 0402WGF4993TCE, 499 kΩ 1 % | HDG §1.3.2, Fig. 5 | OK, mandatory for v3. Top of R104 taps 1V1_HP at the regulator. |
| C134 | 22 pF C0G 0402 (JLC C1555) | HDG Fig. 5 | OK |
| C135 | CL21A226MQQNNNE, 22 µF X5R 6.3 V 0805 | HDG Fig. 5 (C3 22 µF) | OK, but see M2 |
| C126 | CL21A106KAYNNNE, 10 µF 25 V 0805 at U3 VIN | HDG Fig. 5 (4.7 µF) | OK |
| U14 | TPS3808G33DBVR: VIT 3.07 V, open-drain RESET | TPS Table 4-1, Fig. 5-1 pins | OK. 1 RESET = CHIP_PU, 2 GND, 3 MR = RESET_MR, 4 CT open = 20 ms (TPS §7.3.2), 5 SENSE = 3V3, 6 VDD = 3V3. The R106 10 k pull-up is inside TPS's 10 k–1 MΩ range. |
| R106 / C136 | 10 kΩ / 1 µF (CL05A105KA5NQNC) | HDG §1.3.3 (recommends R = 10 kΩ, C = 1 µF) | OK |
| Y1 | Lucki L327S400H11L: 40 MHz, CL 10 pF, ESR 20 Ω, pin 1/3 crystal, 2/4 GND | XT; HDG §1.3.5 ("only supports 40 MHz") | OK. Y1.1 → XTAL_P, Y1.3 → XTAL_N, as in HDG Fig. 8. |
| C203/C204 | 0402CG120J500NT, 12 pF C0G | HDG §1.3.5 formula CL = C4·C5/(C4+C5) + Cstray | OK: 6 pF + about 3–4 pF stray ≈ 10 pF. |
| R207/R208 | 0 Ω series | HDG Fig. 8 (R3/R4 = 0) | OK |
| R103 | 0402WGF4021TCE, 4.02 kΩ 1 % | DS Table 2-9/2-10; HDG §1.3.15 | OK |
| R107/R108/R109 | 10 kΩ straps | DS Tables 3-1/3-3/3-7 | OK (see m1) |
| SW7 | B3U-1000P on GPIO35 | esptool boot-mode page: a strong pull-down is needed against the 45 k internal pull-up | OK (direct short to GND) |
| R201–R206 | 0 Ω flash series links | HDG §1.3.4 ("add zero-ohm resistor footprints in series") | OK |
| R209 | 10 kΩ pull-up on flash /CS to VDDO_FLASH | HDG §1.3.4 ("Place a pull-up resistor at the FLASH_CS pin") | OK |
| C201/C202 | 100 nF + 1 µF at U2 VCC (3.2 mm) | HDG §1.3.4 (0.1 µF at flash power pin) | OK |
| R403 | 0 Ω, 3V3 → VDD_USBPHY | HDG §1.3.2 (0 Ω may be kept on v3) | OK |
| C110/C111/C112 | 10 nF / 100 nF / 4.7 µF on VDD_USBPHY | HDG §1.3.2 | OK |
| C107/C108/C109/C122 | 10 nF / 100 nF / 1 µF / 1 µF on VDDO_MIPI_2V5 | HDG §1.3.2 | Values OK; placement m4 |
| C104/C115/C120 | VDDO_FLASH: 100 nF + 2 × 1 µF | HDG §1.3.2 | Values OK; placement m4 |
| C113/C116/C118/C119/C121 | VDDO_PSRAM: 2 × 100 nF + 3 × 1 µF | HDG §1.3.2 | Values OK; C118 placement m4 |
| C101/102/114/117/124/131 (+C106/127/128/130/132 at 5–6 mm), C123/C133 10 µF | 3V3 decoupling around U1 | HDG §1.3.2, §1.4.1 | OK except m2, m3 |
| C103/C105/C125/C129 | 100 nF at each VDD_HP pin (≤ 1.6 mm) | HDG §1.3.2 | OK (bulk: M2) |

### Supply domains
| U1 pads | Domain | Fed from | Voltage | Spec | OK? |
|---|---|---|---|---|---|
| 9 | VDD_LP | 3V3_SYS (TPS63070, 3.31 V) | 3.31 V | 3.0–3.6 V (DS T5-2) | OK |
| 21, 62, 85, 96 | VDD_IO_0/4/5/6 | 3V3_SYS | 3.31 V | 1.65–3.6 V | OK (all IO at 3.3 V, matching every peripheral on the board) |
| 75 | VDD_LDO | 3V3_SYS | 3.31 V | 3.0–3.6 V | OK. Flash headroom: 3.31 − 40 mA × 3 Ω (DS T5-3 R_VFB) = 3.19 V > 2.7 V (W25 VCC min) |
| 77 | VDD_DCDCC | 3V3_SYS (same as U3 VIN) | 3.31 V | 3.0–3.6 V | OK |
| 101 | VDD_ANA | 3V3_SYS | 3.31 V | 3.0–3.6 V | OK |
| 102 | VDD_BAT | 3V3_SYS | 3.31 V | 2.5–3.6 V; must not float | OK |
| 26, 54, 76, 91 | VDD_HP_0–3 | 1V1_HP (U3, chip-controlled) | ~1.25 V active | 0.99–1.3 V, abs max 1.3 V | OK (margin: M2, B3) |
| 30 ← 71 | VDD_FLASHIO ← VDDO_FLASH (LDO ch1) | internal | 3.3 V (eFuse default, DS T3-4) | 1.65–3.6 V | OK. Never burn EFUSE_0PXA_TIEH_SEL_0: it would set 1.8 V on a 2.7 V-minimum flash. |
| 59, 67 ← 72 | VDD_PSRAM_0/1 ← VDDO_PSRAM (LDO ch2) | internal | 1.8 V (firmware) | 1.65–1.95 V | OK |
| 41 ← 73 | VDD_MIPI_DPHY ← VDDO_3 (LDO ch3) | internal, `esp_ldo_acquire_channel(chan 3, 2500 mV)` in `slim4_board.c:723` | 2.5 V | 2.25–2.75 V; VO3 range 0.5–2.7 V (DS T2-13) | OK |
| 74 | VDDO_4 | unused | 0 V | optional | OK (m5) |
| 51 | VDD_USBPHY | 3V3 via R403 0 Ω | 3.31 V | 2.97–3.63 V | OK |
| 105 | GND (EP) | GND planes | — | — | OK electrically (via count: M3) |

### Other checks passed
- **Power-up timing:**
  - Every rail Fig. 2-3 / Table 2-14 lists (VDD_LP, IO_0/4/5/6, USBPHY, LDO, DCDCC, ANA) is on 3V3_SYS, so they rise together. VDD_PSRAM is internal and handled by ROM and firmware, as in the reference.
  - Sequence: 3V3 crosses 3.07 V, then the TPS3808 holds RESET for 20 ms (CT open; TPS §7.3.2), then CHIP_PU rises with τ = 10 k × 1 µF = 10 ms and reaches VIH_nRST = 0.75 × VDD_BAT (DS T5-4) after about 13.9 ms. The chip is enabled about 34 ms after the rail is good, far above tSTBL = 50 µs.
  - On a brown-out below 3.07 V, CHIP_PU is actively pulled low and held for at least 20 ms after recovery, above tRST = 1 ms. HDG §1.3.3 recommends exactly this supervisor solution for battery and slow-ramp cases.
  - SW6 via MR: R607 10 k + C602 100 nF debounce, then a 20 ms reset pulse.
- **Strap hold time:** tH = 3 ms (DS T3-2); SW7 is pressed by hand. GPIO35 has no capacitor (HDG §1.3.8: "Do not add high-value capacitors at GPIO35"). BOOT_STRAP is 84 mm long, about 10 pF, which is negligible with 10 k.
- **Boot modes:**
  - GPIO35 = 1 → SPI boot (DS T3-3).
  - BOOT held → GPIO35 = 0, GPIO36 = 1 → joint download (DS T3-3; esptool boot-mode page: "GPIO36 must also be driven High … GPIO36 = 0 and GPIO35 = 0 is invalid"). The board can never produce 35 = 0 / 36 = 0.
  - ROM printing: EFUSE_UART_PRINT_CONTROL = 0, so GPIO36 is ignored (DS T3-5). USB-JTAG printing is on (DS T3-6).
  - JTAG over USB with default eFuses (DS T3-7).
- **USB-Serial-JTAG:** pads 52/53 = GPIO24/25 = USB1P1_N0/P0 (DS T2-7), USB_USJ_INT_PHY_DM/DP_GPIO_NUM 24/25 (IDF `io_mux_reg.h:177–184`). D− goes to pad 52 and D+ to pad 53, the correct polarity (HDG §1.3.12 notes the roles could even be swapped in software). ESD protection is TPD2EUSB30 (0.7 pF per R22 review). VDD_IO_4 powers these pads.
- **MIPI DSI:** pad-to-net polarity is D1P 35, D1N 36, CLKN 37, CLKP 38, D0P 39, D0N 40, matching DS Table 2-1 and J1. REXT is 4.02 k. Unused CSI pins and CSI_REXT may float (HDG §1.3.15 Attention).
- **Flash mapping (DS Table 2-15; HDG Table 3):** FLASH_CS 27 → /CS, FLASH_Q 28 → DO, FLASH_WP 29 → /WP (IO2), FLASH_HOLD 31 → /HOLD (IO3), FLASH_CK 32 → CLK, FLASH_D 33 → DI (IO0).
  - Firmware: `ESPTOOLPY_FLASHMODE_DIO`, `FLASHFREQ_80M`, `FLASHSIZE_64MB` (sdkconfig lines 1258/1268/1283). DIO needs no QE. QE = 1 is fixed on "IQ" parts (W25 §7.1, line 830), so IO2/IO3 are data pins and /HOLD and /WP are inactive; no pull-ups are needed.
  - 80 MHz is within 133 MHz. The power-up address mode is 3-byte (ADP = 0, W25 §7.1.11), which the ROM needs.
- **Firmware GPIOs** (`check_pinmap.py` P4_PAD versus DS Table 2-1): all 19 GPIO-to-pad entries match, including GPIO0 = pad 104 (LP_GPIO0, beside CHIP_PU on 103) and GPIO9+ shifted one pad by VDD_LP on pad 9 (GPIO9 on pad 10). The 43/44/45/46 entries skip pad 85 (VDD_IO_5).
  - The P4 has no input-only pins: all pins are I/O/T (DS T2-3). All 55 GPIOs are valid outputs (IDF `soc_caps.h:269–270`).
  - BAT_ADC on GPIO16 is ADC1_CH0 (DS T2-7) with 100 nF (HDG §1.3.10).
  - PWR_WAKE on GPIO0 is an LP IO in the VDD_LP domain and works in deep sleep (HDG §1.3.9). EXT1 any-low per pin is supported (IDF `SOC_PM_SUPPORT_EXT1_WAKEUP_MODE_PER_PIN`).
  - Console pins 24/25 are left alone. UART0 37/38 are free.
  - GPIO2–5 hold the pad-JTAG functions only if pad JTAG is selected (m1).
  - No used GPIO is a strapping pin except GPIO35 (the BOOT button, read after boot; fine).
- **Unconnected U1 pads:** 13, 15, 16, 19, 20, 22–25, 42–50, 57, 58, 60, 61, 63, 64, 74, 80–83, 87, 89, 90, 92–95, 97, 98. All are unused GPIOs, unused CSI/HS-USB pins, or the optional VDDO_4 output. **No pad that must be connected is open.**
- **DC-DC enable logic:** TLV EN VIH max 1.2 V; the P4 drives EN_DCDC directly as in HDG Fig. 5. The firmware Kconfig sets `ESP_SLEEP_DCM_VSET_VAL_IN_SLEEP = 14`, the value IDF lists for the TLV62569 (`Kconfig.dcdc`).

### Pad-by-pad table (all 105 U1 pads)
"Datasheet name" is from DS Table 2-1 (v3, QFN104). "Board net" is from R26_NETLIST.txt and u1_pad_nets.json, which are identical.

| Pad | Datasheet name (Table 2-1) | Board net | Verdict |
|---|---|---|---|
| 1 | GPIO1 | BTN_LEFT | OK. LP GPIO (VDD_LP). 10 k pull-up R111 + SW1. XTAL_32K_P analog function unused (RTC clk = internal RC) |
| 2 | GPIO2 | BTN_RIGHT | OK. MTCK at reset (IE, WPU); R112 pull-up + SW2. Pad JTAG only if EFUSE_JTAG_SEL_ENABLE=1 and GPIO34=0 (see m1) |
| 3 | GPIO3 | DART_LEFT | OK. MTDI; R601 + SW3 |
| 4 | GPIO4 | DART_RIGHT | OK. MTMS; R602 + SW4 |
| 5 | GPIO5 | I2S_BCLK | OK. MTDO tri-state while JTAG source is USB; to U8/U9 BCLK inputs |
| 6 | GPIO6 | I2S_LRCLK | OK. I2S LRCLK to U8/U9 |
| 7 | GPIO7 | I2S_DOUT | OK. I2S DOUT to U8/U9 |
| 8 | GPIO8 | AUDIO_SD_CTRL | OK. 100 k pull-down R504 holds amps off |
| 9 | VDD_LP | 3V3_SYS | OK. VDD_LP 3.0-3.6 V (HDG 1.3.2) on 3V3_SYS; C101 100 nF at 1.4 mm |
| 10 | GPIO9 | BACKLIGHT_PWM | OK. GPIO9, R422 100 k pull-down |
| 11 | GPIO10 | LCD_RESET_GATE | OK. GPIO10, R308 100 k pull-up |
| 12 | GPIO11 | CHG_STATUS | OK. GPIO11, open-drain CHG with R420 100 k |
| 13 | GPIO12 | (no net) | OK unused (no net) |
| 14 | GPIO13 | BQ_EN1 | OK. GPIO13 R603 pull-up |
| 15 | GPIO14 | (no net) | OK unused (LP_UART_TXD, free) |
| 16 | GPIO15 | (no net) | OK unused (LP_UART_RXD, free) |
| 17 | GPIO16 | BAT_ADC | OK. GPIO16 = ADC1_CH0 (Table 2-7); C603 100 nF per HDG 1.3.10 |
| 18 | GPIO17 | USB_CURR_OUT2 | OK. GPIO17 R606 pull-up |
| 19 | GPIO18 | (no net) | OK unused |
| 20 | GPIO19 | (no net) | OK unused |
| 21 | VDD_IO_0 | 3V3_SYS | OK. VDD_IO_0 1.65-3.6 V; C102 at 1.4 mm |
| 22 | GPIO20 | (no net) | OK unused |
| 23 | GPIO21 | (no net) | OK unused |
| 24 | GPIO22 | (no net) | OK unused |
| 25 | GPIO23 | (no net) | OK unused |
| 26 | VDD_HP_0 | 1V1_HP | OK. VDD_HP_0 0.99-1.3 V (Table 5-2); C103 at 1.4 mm. No 10 uF near (M2) |
| 27 | FLASH_CS | FLASH_CS_SOC | OK. FLASH_CS -> R201 -> U2.1 /CS; R209 10 k pull-up to VDDO_FLASH (HDG 1.3.4) |
| 28 | FLASH_Q | FLASH_IO1_SOC | OK. FLASH_Q -> U2.2 DO(IO1) (Table 2-15) |
| 29 | FLASH_WP | FLASH_IO2_SOC | OK. FLASH_WP -> U2.3 /WP(IO2) |
| 30 | VDD_FLASHIO | VDDO_FLASH_3V3 | OK. VDD_FLASHIO <- VDDO_FLASH (3.3 V); C104 100 nF at 1.2 mm, nearest 1 uF 10.6 mm (m4) |
| 31 | FLASH_HOLD | FLASH_IO3_SOC | OK. FLASH_HOLD -> U2.7 /HOLD(IO3) |
| 32 | FLASH_CK | FLASH_CLK_SOC | OK. FLASH_CK -> U2.6 CLK |
| 33 | FLASH_D | FLASH_IO0_SOC | OK. FLASH_D -> U2.5 DI(IO0) |
| 34 | DSI_REXT | DSI_REXT | OK. DSI_REXT 4.02 k 1 % (R103 0402WGF4021TCE) to GND (Table 2-10, HDG 1.3.15) |
| 35 | DSI_DATAP1 | MIPI_DSI_D1_P | OK. DSI_DATAP1 -> J1.31 |
| 36 | DSI_DATAN1 | MIPI_DSI_D1_N | OK. DSI_DATAN1 -> J1.32 |
| 37 | DSI_CLKN | MIPI_DSI_CLK_N | OK. DSI_CLKN -> J1.29 |
| 38 | DSI_CLKP | MIPI_DSI_CLK_P | OK. DSI_CLKP -> J1.28 |
| 39 | DSI_DATAP0 | MIPI_DSI_D0_P | OK. DSI_DATAP0 -> J1.34 |
| 40 | DSI_DATAN0 | MIPI_DSI_D0_N | OK. DSI_DATAN0 -> J1.35 |
| 41 | VDD_MIPI_DPHY | VDDO_MIPI_2V5 | OK. VDD_MIPI_DPHY 2.25-2.75 V <- VDDO_3 (2.5 V by firmware); 10 nF at 1.3 mm, 0.1/1 uF ~9.4 mm (m4) |
| 42 | CSI_DATAN0 | (no net) | OK NC (CSI unused; HDG 1.3.15 allows floating) |
| 43 | CSI_DATAP0 | (no net) | OK NC |
| 44 | CSI_CLKP | (no net) | OK NC |
| 45 | CSI_CLKN | (no net) | OK NC |
| 46 | CSI_DATAN1 | (no net) | OK NC |
| 47 | CSI_DATAP1 | (no net) | OK NC |
| 48 | CSI_REXT | (no net) | OK NC (CSI_REXT, CSI unused) |
| 49 | USB_DM | (no net) | OK NC (USB 2.0 HS PHY unused) |
| 50 | USB_DP | (no net) | OK NC (HS PHY unused; v3 needs no DP pull-down, HDG 1.3.12) |
| 51 | VDD_USBPHY | VDD_USBPHY_LOCAL | OK. VDD_USBPHY 2.97-3.63 V via R403 0 R; 10 nF+0.1 uF+4.7 uF (C110/C111/C112) as HDG 1.3.2 |
| 52 | GPIO24 | USB_JTAG_DM | OK. GPIO24 = USB1P1_N0, USB-Serial-JTAG D- (Table 2-7; IDF USB_USJ_INT_PHY_DM_GPIO_NUM 24) |
| 53 | GPIO25 | USB_JTAG_DP | OK. GPIO25 = USB1P1_P0, D+ (USB_PU at reset) |
| 54 | VDD_HP_1 | 1V1_HP | OK. VDD_HP_1 (v3; NC on v1.x, HDG 1.3.1); C105 at 1.4 mm |
| 55 | GPIO26 | USB_RECOVERY_GPIO26 | OK. GPIO26 net USB_RECOVERY_GPIO26 goes nowhere (single-pin net, m9) |
| 56 | GPIO27 | USB_RECOVERY_GPIO27 | OK. GPIO27 same (m9) |
| 57 | GPIO28 | (no net) | OK unused |
| 58 | GPIO29 | (no net) | OK unused |
| 59 | VDD_PSRAM_0 | VDDO_PSRAM_1V9 | OK. VDD_PSRAM_0 1.65-1.95 V <- VDDO_PSRAM; C116 at 1.4 mm |
| 60 | GPIO30 | (no net) | OK unused |
| 61 | GPIO31 | (no net) | OK unused |
| 62 | VDD_IO_4 | 3V3_SYS | OK. VDD_IO_4 (powers GPIO24-38 incl. USB-JTAG and straps); nearest 100 nF 3.6 mm (m3) |
| 63 | GPIO32 | (no net) | OK unused (IE at reset) |
| 64 | GPIO33 | (no net) | OK unused (IE at reset) |
| 65 | GPIO34 | STRAP_GPIO34 | OK. GPIO34 strap, R107 10 k to GND; ignored with default eFuses (Table 3-7) - see m1 |
| 66 | GPIO35 | BOOT_STRAP | OK. GPIO35 strap, R108 10 k pull-up + SW7 to GND: 1 = SPI boot (Table 3-3) |
| 67 | VDD_PSRAM_1 | VDDO_PSRAM_1V9 | OK. VDD_PSRAM_1; C113 at 1.5 mm |
| 68 | GPIO36 | DOWNLOAD_STRAP_GPIO36 | OK. GPIO36 strap, R109 10 k pull-up: with SW7 held = joint download (Table 3-3) |
| 69 | GPIO37 | UART0_TX | OK (floating strap, 'any value' per Table 3-3; UART0 TXD, no test pad - m9/U2) |
| 70 | GPIO38 | UART0_RX | OK (floating strap, as 69; UART0 RXD) |
| 71 | VDDO_FLASH | VDDO_FLASH_3V3 | OK. VDDO_FLASH output, 3.3 V default (Table 3-4); C115 1 uF at 2.8 mm |
| 72 | VDDO_PSRAM | VDDO_PSRAM_1V9 | OK. VDDO_PSRAM output (LDO ch2, 1.8 V by firmware); C113 1.85 mm, C121 1 uF 3.8 mm |
| 73 | VDDO_3 | VDDO_MIPI_2V5 | OK. VDDO_3 output (LDO ch3) -> pad 41; 100 nF C108 at 1.4 mm, 1 uF 9.3 mm (m4) |
| 74 | VDDO_4 | (no net) | VDDO_4 output left open; default 0 V (HDG 1.3.2) so legal, but no 1 uF as reference (m5) |
| 75 | VDD_LDO | 3V3_SYS | OK supply (VDD_LDO 3.0-3.6 V) but no local 10 uF, 100 nF shared (m2) |
| 76 | VDD_HP_2 | 1V1_HP | OK. VDD_HP_2; C125 at 1.6 mm |
| 77 | VDD_DCDCC | 3V3_SYS | OK supply (VDD_DCDCC 3.0-3.6 V, same rail as U3 VIN as HDG requires) but no local 10 uF (m2) |
| 78 | FB_DCDC | FB_DCDC | OK net (FB_DCDC -> U3.5 FB, R104/R105 499 k, C134 22 pF as HDG Fig. 5) - routing 33 mm (M1) |
| 79 | EN_DCDC | EN_DCDC | OK net (EN_DCDC -> U3.1 EN) - routing 25.5 mm (M1) |
| 80 | GPIO39 | (no net) | OK unused |
| 81 | GPIO40 | (no net) | OK unused |
| 82 | GPIO41 | (no net) | OK unused |
| 83 | GPIO42 | (no net) | OK unused |
| 84 | GPIO43 | USB_CURR_OUT1 | OK. GPIO43 R605 pull-up (TUSB320 OUT1) |
| 85 | VDD_IO_5 | 3V3_SYS | OK. VDD_IO_5 3.3 V; C114 at 1.2 mm |
| 86 | GPIO44 | PGOOD_STATUS | OK. GPIO44 R421 pull-up (PGOOD) |
| 87 | GPIO45 | (no net) | OK unused |
| 88 | GPIO46 | BQ_EN2 | OK. GPIO46 R604 pull-down (BQ EN2) |
| 89 | GPIO47 | (no net) | OK unused |
| 90 | GPIO48 | (no net) | OK unused |
| 91 | VDD_HP_3 | 1V1_HP | OK. VDD_HP_3; C129 at 1.2 mm |
| 92 | GPIO49 | (no net) | OK unused |
| 93 | GPIO50 | (no net) | OK unused |
| 94 | GPIO51 | (no net) | OK unused |
| 95 | GPIO52 | (no net) | OK unused |
| 96 | VDD_IO_6 | 3V3_SYS | OK. VDD_IO_6 3.3 V; nearest 100 nF C117 2.3 mm (shared with 101/102) |
| 97 | GPIO53 | (no net) | OK unused |
| 98 | GPIO54 | (no net) | OK unused |
| 99 | XTAL_N | XTAL_N_SOC | OK. XTAL_N -> R208 0 R -> Y1.3 (XOUT) + C204 12 pF (HDG Fig. 8) |
| 100 | XTAL_P | XTAL_P_SOC | OK. XTAL_P -> R207 0 R -> Y1.1 (XIN) + C203 12 pF |
| 101 | VDD_ANA | 3V3_SYS | OK. VDD_ANA 3.0-3.6 V; C117 at 1.24 mm (shared) |
| 102 | VDD_BAT | 3V3_SYS | OK. VDD_BAT 2.5-3.6 V tied to 3V3 (must not float, HDG 1.3.2); C117 shared, 10 uF C133 4.9 mm (m3) |
| 103 | CHIP_PU | CHIP_PU | OK. CHIP_PU: TPS3808G33 open-drain RESET + R106 10 k + C136 1 uF (HDG 1.3.3) - trace length m6 |
| 104 | GPIO0 | PWR_WAKE | OK. GPIO0 = LP_GPIO0 (Table 2-5), RTCIO 0 -> valid EXT1 wake; R110 10 k + C601 100 nF + SW5 |
| 105 | GND | GND | OK. GND exposed pad, 9 tiles 2.1 mm = 7.5 mm (Fig. 6-1 D2/E2 7.5 nom) - only 4 vias (M3) |

---

## Bring-up probe table (U1/U2 subsystem, in measurement order)

Power from a current-limited bench supply on BAT or USB. Ground reference: any GND pad of the capacitors named; all are 0402/0805 on the back.

| # | Condition | Probe point | Expected (tolerance) | A wrong reading means |
|---|---|---|---|---|
| 0 | Unpowered, DMM Ω | 3V3_SYS (C101.1), 1V1_HP (C103.1), VDDO_FLASH (C104.1), VDDO_PSRAM (C113.1), VDDO_MIPI (C108.1), CHIP_PU (C136.1) to GND | No reading < 50 Ω after the capacitors charge. 1V1_HP may read lowest (core leakage), typically hundreds of Ω or more. | < 5 Ω: solder short under U1 (0.35 mm pitch) or a capacitor reversed or shorted. Do not power. |
| 1 | Power on, no button pressed | 3V3_SYS at C101 (pad 9) | 3.31 V ±3 % (3.21–3.41) | Outside range: the 3V3 subsystem (U4); stop. |
| 2 | Same | VDD_USBPHY at C112 | Equal to 3V3_SYS (±10 mV) | 0 V: R403 open. |
| 3 | Same, scope on CHIP_PU at C136 | CHIP_PU | 0 V for about 20 ms after 3V3 reaches 3.07 V, then an RC rise (τ about 10 ms) to 3V3 ±50 mV | Stays low: U14 stuck, MR (RESET_MR) low, or SW6 shorted. Rises at once: U14 missing or wrong part. Never above 3V3: R106 open. |
| 4 | Press and release SW6 | CHIP_PU | Goes to < 0.3 V while pressed and stays low ≥ 20 ms after release | No change: MR path open. |
| 5 | After reset, SPI boot (BOOT not pressed) | Pad-side straps: R107.1 (GPIO34), R108.2 (GPIO35), R109.2 (GPIO36) | GPIO34 < 0.3 V; GPIO35 ≈ 3.3 V; GPIO36 ≈ 3.3 V | GPIO35 low: SW7 stuck or short, so the board always enters download mode. |
| 6 | Same | VDDO_FLASH at C202 / U2.8 | 3.18–3.35 V (3.3 V minus ≤ 0.12 V for 40 mA × 3 Ω) | ≈ 1.8 V: EFUSE_0PXA_TIEH_SEL_0 burned (flash out of spec). 0 V in SPI boot: U1 not running or a short on VDDO_FLASH. |
| 7 | Same, scope U2.6 (FLASH_CLK) at boot | FLASH_CLK burst | Clock bursts in the first ms after CHIP_PU rises | None: U1 not out of reset (check rows 3, 8, 9). |
| 8 | App running (boot log seen) | EN_DCDC at U3.1 | ≥ 1.2 V (logic high) | Low while the app runs: DC-DC not enabled. Expect a crash right after the bootloader's switch to DC-DC (see M1). |
| 9 | App running | 1V1_HP at C129 (pad 91) and C103 (pad 26) | 1.20–1.28 V DC (≈ 1.25 V, IDF `vset 27`); never > 1.30 V | > 1.30 V: chip is above absolute maximum. Power down and check the R104/R105/C134 values and FB_DCDC continuity. < 1.15 V: FB network or plane drop. |
| 10 | App running, scope 20 MHz bandwidth, CPU + PSRAM stress | 1V1_HP AC at C129 | Engineering target ≤ 50 mVpp; trough ≥ 0.99 V; peak ≤ 1.30 V | Larger: add local 10 µF (M2) or reroute FB (M1). |
| 11 | App running | FB_DCDC at R105.1 | About 0.6 V (0.588–0.612 per TLV, slightly modulated by the P4) | ≈ 0 or ≈ 1.2 V: R104/R105 swapped, missing or open. |
| 12 | Download mode (hold SW7, tap SW6, release SW7) | EN_DCDC; 1V1_HP | EN_DCDC ≈ 0 V (HDG §1.3.2); 1V1_HP about 1.0–1.15 V from the internal LDO (UNSURE U1) | 1V1_HP > 1.3 V: fault. |
| 13 | Download mode | VDDO_FLASH | May read 0 V until esptool connects, then 3.3 V (ERR §3.7) | 0 V after esptool has connected: flash LDO problem. |
| 14 | After the 2nd-stage bootloader | VDDO_PSRAM at C113 (pads 59/67/72) | 1.80 V ±3 % (1.75–1.85) | 0 V: PSRAM LDO not enabled (PSRAM init will fail in the log). > 1.95 V: out of spec. |
| 15 | After `init_display` runs | VDDO_MIPI_2V5 at C108 (pad 73) and C107 (pad 41) | 2.50 V ±3 % (2.43–2.58); 0 V before display init | > 2.75 V: wrong `voltage_mv`. Ringing: m4. |
| 16 | Any boot | USB-C to PC | Enumerates as 303a:1001 "USB JTAG/serial debug unit"; ROM log shows `boot:… (SPI_FAST_FLASH_BOOT)` or, with BOOT held, `DOWNLOAD(USB/UART0/SPI)` | No enumeration: USB_JTAG_DP/DM route, R401/R402, U11, VDD_IO_4. With BOOT held and a strange boot mode: GPIO37/38 floating (U2). |
| 17 | Boot log | Chip revision; PSRAM; flash ID | "v3.1" or "v3.2" (v3.0 is acceptable with B1 caveats); 32 MB PSRAM; flash JEDEC EF 40 20 | v1.x: wrong part, will not run. ID FF FF FF or 00 00 00: flash wiring or VDDO_FLASH. |
| 18 | App running | 40 MHz crystal: measure an XTAL-derived output with a counter (e.g. LEDC PWM on BACKLIGHT_PWM, no panel connected, with LEDC clocked from XTAL). Do not probe Y1 directly: the probe loads it. | Nominal ±30 ppm | Off by > 100 ppm or not starting: C203/C204 or Y1 wrong or misplaced (m7). |
| 19 | SW6 reset, WDT reset and `esp_restart()` from a running app | Boot log | Every reset reboots into the app | Hangs after a non-power-cycle reset: flash left in 4-byte mode (B2). |
| 20 | Deep sleep, then press SW5 | 3V3 current; wake | Board wakes on SW5 (EXT1 GPIO0); measure sleep current | No wake: GPIO0 path or EXT1 configuration. |
| 21 | Full load, 10 min, case off | U1 package temperature (thermal camera) | Record; compare with the EV board | Hot spot well above the board: EP via count (M3). |
