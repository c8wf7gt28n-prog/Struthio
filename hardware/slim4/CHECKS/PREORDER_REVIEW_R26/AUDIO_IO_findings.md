# STRUTHIO SLIM4 R26: AUDIO, CONTROLS, USB DATA/CC review

Reviewer scope: U8/U9 MAX98357A, SD_MODE network, J4/J5, I2S firmware; SW1-SW7, pull-ups, BOOT/RESET; J2, U11/U12, U13 TUSB320LAI, R401/R402, R416/R417, OUT1/OUT2 firmware decode; J3 pinout.
Sources: R26_NETLIST.txt, SLIM4_R26.kicad_pcb (track/zone/footprint geometry), SLIM4.pretty, firmware slim4_board.c / slim4_power.c / slim4_pins.h / app_main.c, ESP-IDF v6.1 at /root/esp/esp-idf. Datasheets were fetched and read (citations below).

## SUMMARY (10 lines)

1. **No BLOCKER in these three subsystems.** Every MAX98357A, TUSB320LAI, TPD2EUSB30, USB4105, B3U, D2LS, JST PH and PicoBlade pin is on the right net, and each land matches its datasheet.
2. USB-C: U13 presents Rd in every state: dead-battery 4.1-6.1 k, active 4.6-5.6 k, and shutdown. A C-to-C charger therefore supplies 5 V with a flat or absent cell. The classic first-spin failure is not present.
3. TUSB320 is strapped as PORT=GND (UFP), ADDR open (GPIO mode), EN_N=GND, VDD=3V3. VBUS_DET is 470 k + 430 k = 900 k (datasheet 855-920 k). OUT1/OUT2 are valid in this mode, and the firmware decode (H/H none, H/L 500 mA, L/H 1.5 A, L/L 3 A) matches datasheet Table 3 exactly.
4. D+ and D- are joined on both rows of J2 (stubs under 3.5 mm) and reach U1 pad 53 (GPIO25, D+) and pad 52 (GPIO24, D-), which are the USB-Serial-JTAG pins. The ESD parts are correct. The series links are 0 Ω, placed at the connector; Espressif asks for 22/33 Ω at the chip (MINOR).
5. SD_MODE: the left amplifier sits at 3.24 V typ (3.13 V worst case; B2 is 1.5 V max), so it plays LEFT. The right amplifier sits at 1.067 V typ, between 0.968 and 1.162 V worst case, inside the 0.825-1.245 V window, so it plays RIGHT with 83-143 mV margin. With SD_CTRL low or floating, both pins read 0 V and both amplifiers shut down.
6. GAIN_SLOT is tied to GND, giving 12 dB. Supply is SYS_RAW (4.4 V on USB, 3.0-4.2 V on the cell). Each amplifier has 10 µF + 1 µF + 2 × 100 nF, which meets the datasheet's 10 µF + 0.1 µF. The firmware's I2S setup (Philips, 16-bit stereo, BCLK = 32 × fs, no MCLK, 48 kHz) is fully compatible.
7. MINOR, layout: the speaker outputs are 0.152 mm tracks on inner layer In3 (15 µm copper, about 0.1-0.15 Ω per leg), and U8/U9 have thin VDD/GND necks with no vias in their exposed pads. This works, but sustained full-scale output into 4 Ω heats the In3 tracks. Cap volume in firmware.
8. MINOR, firmware: the API accepts sample rates the MAX98357A does not support (11.025/12/22.05/24 kHz, datasheet p16); the end of each sound is cut about 12 ms short by the 20 ms idle shutdown; and 100 % volume overdrives 1 W 8 Ω speakers.
9. BRINGUP and pre-order checks: D1 (VBUS TVS) cathode orientation, U13/U8/U9 pin 1, and J2 shell legs in JLC's preview; battery pack polarity (pin 1 = BAT+ is NOT a universal JST PH convention, see UNSURE); BCLK edge quality at the amplifiers (90 mm unterminated branch); no-battery operation on a 1.5 A/3 A USB-C charger at loud volume.
10. Controls are correct. All SPST-NO switches go to GND with 10 k pull-ups (within the D2LS 1 mA and B3U 50 mA ratings). There are no RC debounce caps on SW1-4/SW7 (firmware debounces for 5 ms). BOOT goes to GPIO35, reset goes through TPS3808 MR to CHIP_PU, and PWR_WAKE goes to GPIO0 with 100 nF. The board has no silkscreen text at all (no BAT+, L/R, BOOT/RST/PWR labels; MINOR).

---

## Datasheets used (fetched 2026-10-09)

| Part | Document | Key pages / tables |
|---|---|---|
| MAX98357A | Maxim 19-6779 Rev 7 (2/16), via cdn-shop.adafruit.com/product-files/3006/ (analog.com timed out) | p1 features; p4 abs max, VDD 2.5-5.5 V, tON 7 ms; p5 POUT, gain, ILIM 2.8 A; p6 LRCLK ranges, BCLK 32/48/64 × fs, jitter; p7 SD_MODE trip points B0/B1/B2, RPD 92-108 k, GAIN_SLOT thresholds; p15 pin table; p16 I2S polarity, supported fs, standby; p17 Table 5 SD_MODE, Table 6 RSMALL 210.2 k @ 3.3 V, 2 k series note; p28 Table 8 gain, click/pop; p33 bypass 10 µF + 0.1 µF, layout |
| TUSB320LAI | TI SLLSEQ8D (May 2017) | p3 pin functions; p4 abs max/ROC; p5-6 Rd values, VBUS_DET 855-920 k; p10 UFP; p12 Table 3 OUT1/OUT2; p13-14 dead-battery/shutdown Rd; p22 Table 14 VBUS bulk 1-10 µF; p28 init; p29 layout (100 nF at VDD, D+/D- stub ≤ 3.5 mm) |
| TPD2EUSB30 | TI SLVSAC2G (Jun 2021) | p3 Table 5-1 DRT pinout (1 D+, 2 D-, 3 GND); p4 VIO max 6 V, operating 0-5.5 V; p5 VRWM 5.5 V, VBR 7 V min, 0.7 pF |
| USB4105-GF-A | GCT drawing (scratchpad/ds_usb/usb4105.pdf) | recommended PCB layout pad order "A1B12 A4B9 B8 A5 B7 A6 A7 B6 A8 B5 B4A9 B1A12"; VBUS 5 A total |
| B3U-1000P | Omron B3U catalogue | p1 ratings 1-50 mA 3-12 VDC, SPST-NO, bounce 5 ms, "Washing: not possible"; p2 PCB pad 4.2 / 2.6 mm, 1.7 mm |
| D2LS-21 (SW1-4) | Omron Cat. B122-E1-02 | p1 rating 6 VDC 1 mA, SPST-NO (COM/NO), bounce 1 ms; p2 land 11.8/8.8, COM 2.2, NO 1.6, 2 × Ø1.1 at 4.0; cannot be washed |
| JST S2B-PH-SM4-TB | JST ePH (text layer unreadable); geometry from KiCad 7 library footprint | pin 1/pin 2 at ±1.0 mm, MP tabs |
| Molex 53261-0271 | Mouser/element14 listing of Molex spec (molex.com timed out) | 1.0 A per contact, 125 V |
| ESP32-P4 | Datasheet v0.7 + HDG (scratchpad/DS) | Table 2-1 pad map, reset pulls; Table 3-1/3-3 strapping; HDG p18: 22/33 Ω series on USB FS D+/D- near chip, ESD at connector |
| BQ24074 | SLUS810N | Table 7-2 EN1/EN2; VO(SC2) 200-300 mV |
| PESD5V0S1UL | Nexperia product page/distributors | VRWM 5 V, VBR ≥ 6.4 V |

---

## FINDINGS

### MINOR

**M1. Speaker outputs are 0.152 mm tracks on inner layer In3 (15.2 µm copper).**
- Evidence: U8.9/10 → J4.1/2 (SPK_L_P 14.9 mm, 12.1 mm on In3; SPK_L_N 15.2 mm, 13.6 mm on In3). U9.9/10 → J5 (SPK_R_P 17.2 mm, SPK_R_N 20.9 mm, 15-18 mm on In3), each with 2 × 0.2 mm vias. The stackup in SLIM4_R26.kicad_pcb gives inner copper 0.0152 mm.
- Resistance is about 7.4 mΩ/mm, so the right channel has about 0.3 Ω round trip. MAX98357A p33 asks for "wide, low-resistance output traces": 100 mΩ already costs 5 % of the power.
- Thermal: at 4.4 V into 4 Ω, 10 % THD gives about 2.5 W, which is 0.79 A rms. IPC-2221 (external-layer constant) estimates about 70 °C rise for 0.152 mm × 15 µm at 0.79 A. Real program material (crest factor 10-12 dB) at the default 35 % volume is under 0.2 A rms, which is harmless.
- Why it matters: this is not a bring-up failure. It is a reliability and efficiency risk at sustained 100 % volume into 4 Ω.
- Fix: in firmware, cap the maximum volume (see M4). Next spin: 0.4-0.5 mm tracks on B.Cu, no layer change.

**M2. U8/U9 supply and ground connections are thin, and the exposed pads have no thermal vias.**
- Evidence: VDD (pins 7/8) reaches one 0.45/0.2 mm via to the In2 SYS_RAW plane through 0.152 mm B.Cu tracks; C420/C421 connect through 0.4 mm. GND pins 2/3/11/15 and the EP join through 0.114-0.152 mm tracks to one via about 3 mm away (U8: via at (-28.7, 109.0)). There is no B.Cu GND pour under either amplifier (zone check: only the In1/In4 GND planes cover (±29, 112)).
- Datasheet p4: θJA 48 °C/W assumes a 4-layer board with the EP soldered to a plane. Datasheet p15: "Connect the exposed pad to a solid ground plane". Datasheet p33: "wide output, supply, and ground traces".
- Why it matters: ground bounce of about 10-20 mV at 1 A peaks, higher junction temperature (estimated 80-100 °C/W in place of 48), and some loss of efficiency and THD. Function is not at risk; the device has thermal and short-circuit protection.
- Fix: next spin, add 4-5 vias in the EP to In1/In4 and 0.4 mm VDD/GND tracks. For R26, a volume cap is enough.

**M3. USB D+/D- series links are 0 Ω and sit at the connector, not 22/33 Ω at the chip.**
- Evidence: R401/R402 are 0402WGF0000TCE at (6.6, 13.4/15.6), next to J2. USB_JTAG_DP/DM then run 108-110 mm (104 mm of it on In3, 0.152 mm, impedance not controlled) to U1.53/U1.52.
- ESP32-P4 HDG p18: "add a 22/33 Ω series resistor … on the D- and D+ lines … close to the chip end".
- Why it matters: Full-Speed USB (12 Mbit/s) will very likely enumerate anyway. The resistors damp ringing on a 110 mm unterminated line and improve EMC margin.
- Fix: optional for R26 (swap R401/R402 to 22 Ω: a value-only BOM change, although they are at the wrong end of the line). Next spin: 22 Ω near U1. Bring-up: enumerate on several hosts and hubs.

**M4. Firmware audio issues** (`slim4_board.c`).
- (a) **Sample rates.** `slim4_board_audio_write()` accepts 8000-96000 Hz. The MAX98357A supports only 8/16/32/44.1/48/88.2/96 kHz, and states that 11.025, 12, 22.05 and 24 kHz are NOT supported (p16; p6 LRCLK ranges 7.6-8.4 / 15.2-16.8 / 30.4-50.4 / 83.8-100.8 kHz). A game that submits 22050 Hz audio will get silence or undefined output. Fix: reject or resample anything outside those ranges. The diagnostic tone uses 48 kHz and is fine.
- (b) **Tail truncation and click.** After `i2s_channel_write()` returns, up to 6 × 256 frames (32 ms at 48 kHz) are still in DMA. The worker's 20 ms idle timeout then calls `stop_audio_clock()`, which drives SD low and disables I2S, cutting the last ~12 ms (and the 2.5 ms fade-out) of every sound. Datasheet p28: the device has no ramp-down on shutdown, so "ramp down the digital data … before powering down". Streams with gaps over 20 ms also toggle shutdown, and each restart costs tON = 7 ms (p4). Fix: wait for the DMA queue to drain (on_sent callback, or write ≥ 32 ms of zeros) before stopping, and use an idle timeout of about 200 ms or more.
- (c) **Volume ceiling.** At 12 dB, 0 dBFS = 14.1 dBV (5.07 Vrms, p28 equation), which clips at 4.4 V. Into an 8 Ω 1 W speaker that is about 1.39 W (10 % THD, p5 scaled to 4.4 V); into 4 Ω about 2.5 W (0.79 A rms, peaks of about 1.1 A, against PicoBlade's 1.0 A per contact). Fix: clamp volume to about 50-60 % (about -5 dB), or choose speakers rated at 2 W or more.

**M5. No silkscreen text on the board.**
- Evidence: `grep -c gr_text SLIM4_R26.kicad_pcb` = 0. All footprint references are hidden. J3, J4, J5, SW5-SW7 carry only library outline lines.
- Why it matters: the three identical B3U switches (SW5 power at (25, 30), SW6 reset at (25, 39), SW7 boot at (25, 48)) and the battery and speaker polarity are unmarked. Mistakes at bring-up become likely, especially plugging a reversed battery into J3.
- Fix: add B.SilkS text "BAT+ / −" at J3, "L+ / R+" at J4/J5, "PWR / RST / BOOT" at SW5/6/7. This costs nothing and is low risk.

**M6. Switches must not be washed.**
- Evidence: B3U p1 "Washing: Not possible"; D2LS p2 "cannot be washed".
- Fix: state "no-clean, do not wash" in the JLC order notes, and do not order "PCBA cleaning".

**M7. Loud audio with no battery on a 1.5 A/3 A USB-C charger can brown out SYS_RAW.**
- Evidence: firmware mutes audio only when the input limit is under 1 A (`slim4_power.c` update_policy). On 1.5 A/3 A USB-C the BQ24074 input limit is 1.07 A (ILIM 1.5 k).
- Estimate: 3V3 at 380 mA ≈ 0.32 A from SYS_RAW, plus backlight 100 % ≈ 0.44 A, plus audio at the default 35 % with 0 dBFS content into 4 Ω ≈ 0.43 A. That is about 1.2 A, over 1.07 A, and with no cell the OUT rail droops.
- Why it matters: brownout or reset on loud passages, but only in a no-battery configuration (bring-up bench).
- Fix: mute or cap audio whenever no qualified cell is present, whatever the USB current; or document "bench without a cell: keep the volume low".

### BRINGUP-CHECK / pre-order checks

**B1. Orientation in JLC's placement preview** (complements RELEASE_GATES Open 2):
- D1 PESD5V0S1UL (SOD-882): cathode must be on USB_VBUS (D1.1). Reversed, it short-circuits VBUS (about 0.7 V forward) the moment USB is plugged in; with no battery the board is then dead.
- U13 TUSB320LAI (X2QFN-12, 1.6 × 1.6 mm, footprint "asymmetric 0.5/0.7 mm side pads"): a 180° error puts CC1/CC2 on OUT1/OUT2 and VDD on PORT.
- U8/U9 TQFN-16 pin 1 (DIN corner).
- U11/U12 DRT-3: the 2+1 pad pattern only fits one way, which is self-checking.
- J2: the shell's 4 through-hole legs must be soldered (pin-in-paste or hand finish). Without them, VBUS and GND see only 0.6 mm SMD pads and the receptacle can tear off.
- SW1-SW4 D2LS: the two Ø1.1 boss holes are symmetric (±2.0 mm), so a 180° placement fits mechanically. COM (2.2 mm pad) and NO (1.6 mm pad) must land on the matching terminals so the plunger sits where the case expects it.

**B2. BCLK/LRCLK/DOUT signal integrity.**
- Evidence: 90-93 mm unterminated, 4-5 vias, 63 mm on In3, branching to two loads 58 mm apart. The ESP32-P4 default drive is 20 mA (datasheet v0.7 Table 2-1 note 3), with rise time about 1-2 ns.
- Risk: ringing or double-clocking on BCLK (classic I2S fault). The datasheet's 10 ns setup/hold has plenty of margin at 1.536 MHz.
- Check: scope BCLK at U8.16 and U9.16 for monotonic edges. Fix if needed: `gpio_set_drive_capability(GPIO5/6/7, GPIO_DRIVE_CAP_0)`.

**B3. Battery pack polarity at J3.** Design: pin 1 = BAT_CONN (Q2 drain), pin 2 = GND. See UNSURE U1. Measure every pack in a loose PH socket before plugging it in.

**B4. Deep-sleep audio shutdown.** After switch-off, AUDIO_SD_CTRL must read 0 V. If it reads 1.5-1.7 V, an internal pull-up is on in sleep and both amplifiers draw about 340 µA each in standby (datasheet p4).

**B5. USB host back-power.** ESP32 USB-Serial-JTAG enables its D+ pull-up with no VBUS sensing, so the board pulls a host's D+ up even when the host is off. This is common practice and accepted; noted only.

---

## UNSURE

- **U1. JST PH battery polarity convention.** Hobby packs (Adafruit/SparkFun) put red on the right when looking into the plug's mating face with the latch bump up (DigiKey and Particle forum threads; there is no official standard; some vendors ship reversed). I could not confirm from a primary schematic whether that maps to board-socket pin 1 or pin 2 of S2B-PH-SM4-TB. The project docs assert "pin 1 (red) = BAT+". If the common packs are wired the other way, every pack plugged in would be reversed: Q2 blocks with no USB, but with USB the charger pushes 4-11 mA into the reversed cell (README edit 12). **Action:** before ordering, mate one of the intended packs to a loose S2B-PH-SM4-TB, or check against Adafruit's published Eagle/KiCad footprint, and add silkscreen "+".
- **U2. SD_MODE noise susceptibility.** The right amplifier's SD node is high impedance (about 68 kΩ Thevenin, 1.07 V, 83 mV margin to B2 min) with no filter capacitor. Coupling from the 330 kHz class-D edges or from BCLK could in principle cause momentary mode flips (the datasheet gives no comparator hysteresis or deglitch). It is probably fine; R502/R503 sit beside U9 on short B.Cu tracks. Check: right-channel dropouts at high volume. Fix if needed: 1-10 nF from AUDIO_SD_R to GND (next spin).
- **U3. USB_DP_CONN under the receptacle body.** The D+ track that joins A6 and B6 (y ≈ 8.0-9.6) runs on B.Cu under J2's body, on the same side as the connector. GCT's drawing shows no keep-out, and solder mask insulates it. A mask defect under the stainless shell would short D+ to chassis. Low risk.
- **U4. TUSB320 GPIO mode reports the current once per attach** (p10: "one time in the Attached.SNK state"). If a multi-port charger lowers its Rp after attach (3 A → 1.5 A), the board keeps drawing 1.07 A, which is still within 1.5 A. A drop to default would not be seen. This is rare.
- **U5. BCLK jitter.** ESP-IDF v6.1 I2S_CLK_SRC_DEFAULT selects PLL_F160M on P4. MCLK = 12.288 MHz from 160 MHz is a /13.02 fractional divider (6.25 ns steps, pattern repeating at about 256 kHz). The MAX98357A tolerates 12 ns rms above 40 kHz and 0.5 ns below (p6, p16 Table 1). It should be within spec; listen for noise. APLL is the fallback.
- **U6. PicoBlade wire gauge.** The 1.0 A per contact rating applies to the larger crimp gauges; the 28-32 AWG leads on small speakers derate. This matters only at sustained 4 Ω full scale.

---

## VERIFIED OK (coverage)

### MAX98357A U8/U9: pin by pin (TQFN, datasheet p15)

| Pin | Datasheet | U8 net | U9 net | OK |
|---|---|---|---|---|
| 1 | DIN | I2S_DOUT (U1.7 GPIO7) | I2S_DOUT | ✓ |
| 2 | GAIN_SLOT | GND (0-0.1 × VDD → 12 dB, p7; Table 8 p28) | GND | ✓ |
| 3, 11, 15 | GND | GND | GND | ✓ |
| 4 | SD_MODE | AUDIO_SD_L (via R501 2 k) | AUDIO_SD_R (via R502 100 k + R503 110 k) | ✓ |
| 5, 6, 12, 13 | N.C. | open | open | ✓ |
| 7, 8 | VDD | SYS_RAW | SYS_RAW | ✓ |
| 9 | OUTP | SPK_L_P → J4.1 | SPK_R_P → J5.1 | ✓ |
| 10 | OUTN | SPK_L_N → J4.2 | SPK_R_N → J5.2 | ✓ |
| 14 | LRCLK | I2S_LRCLK (GPIO6) | I2S_LRCLK | ✓ |
| 16 | BCLK | I2S_BCLK (GPIO5) | I2S_BCLK | ✓ |
| EP | not internally connected, to ground for heat | GND | GND | ✓ (see M2) |

- The part is MAX98357**A**: I2S, left channel when LRCLK is low (p16 Table 3), data on BCLK rising edge (p16 Table 2). Footprint is Maxim 90-0031 (pads at 0.5 mm pitch, EP 1.23 mm).
- Logic levels: VIH 1.3 V, VIL 0.6 V (p6/p7). The 3.3 V GPIO meets both. LRCLK/BCLK/DIN abs max is 6 V.

### SD_MODE network (p7 trip points; p17 Tables 5/6)

Trip points: B0 0.08/0.16/0.355 V; B1 0.65/0.77/0.825 V; B2 1.245/1.4/1.5 V; RPD 92/100/108 k. Calculation assumes 3V3_SYS 3.2-3.4 V (3.307 V nominal) and 1 % resistors.

| Condition | Node | Typ | Worst case | Required | Result |
|---|---|---|---|---|---|
| GPIO8 high | SD_L = 3.3 × RPD/(RPD + 2 k) | 3.24 V | 3.13 V min | > B2 (1.5 V max) | LEFT ✓ |
| GPIO8 high | SD_R = 3.3 × RPD/(RPD + 210 k) | 1.067 V | 0.968-1.162 V | B1max 0.825 < V < B2min 1.245 | RIGHT ✓ (margins +143 / -83 mV) |
| GPIO8 low, or floating at reset (GPIO8 has no reset pull, P4 Table 2-1) | both | 0 V (R504 100 k; leakage ≤ 1 µA × 44 k = 44 mV) | | < B0 min 0.08 V | SHUTDOWN ✓ |

- 100 k + 110 k = 210 k equals the datasheet RSMALL at 3.3 V (210.2 k, Table 6, p17).
- R501 2 k is the series resistor the datasheet asks for when VDD can fall below VDDIO (p17). Here SYS_RAW (VDD) can fall below 3.3 V on a low cell. Abs max SD_MODE is VDD + 0.3 V (p4); the 2 k limits the current. ✓
- GPIO load when high is about 76 µA. ✓

### Supply, decoupling, power, connectors

- Supply: SYS_RAW is 4.4 V (BQ24074 VO(REG)) on USB and VBAT on the cell. The 2.5-5.5 V range (p4) is met at all times; UVLO is ≤ 2.3 V. ✓
- Decoupling, U8: C420 10 µF 25 V X5R 0805 (3.6 mm away), C505 1 µF, C501/C503 100 nF. U9: C421, C506, C502/C504. Datasheet p33 asks for 10 µF + 0.1 µF. ✓ Bulk on SYS_RAW elsewhere: C411/C420/C421 10 µF, C413 22 µF, the In2 SYS_RAW plane.
- Output power at 12 dB gain:
  - 4.4 V, 4 Ω: about 2.5 W (10 % THD) / 1.9 W (1 %).
  - 4.4 V, 8 Ω: about 1.4 W.
  - 3.7 V, 8 Ω: 0.93 W (p5).
  - The 4-8 Ω speaker spec is appropriate. Current limit 2.8 A typ, hiccup (p28), protects a shorted speaker lead.
- J4/J5 (53261-0271, KiCad library land, MP tabs): pin 1 = OUTP, pin 2 = OUTN, both channels the same polarity. ✓ 1.0 A per contact covers realistic program levels (see M4c).
- Firmware I2S, checked against the datasheet:

| Item | Firmware | Datasheet |
|---|---|---|
| Format | `I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(16BIT, STEREO)` | I2S ✓ |
| Slot width | 16 → BCLK = 32 × fs = 1.536 MHz | 32/48/64 × fs, 0.243-25.8 MHz (p6) ✓ |
| MCLK | `I2S_GPIO_UNUSED` | no MCLK needed (p16) ✓ |
| Inversions | none | ✓ |
| Sample rate | 48 kHz (tone) | supported (p16) ✓ |
| Sequencing | SD high → 1 ms → clocks; on stop SD low then clocks stop, BCLK and LRCLK together | "do not remove LRCLK while BCLK is present" (p16) ✓ |
| Mapping | left sample = slot 0 = LRCLK low = U8/J4; app_main left buttons → left samples | ✓ |

- Bench test in FIRST_BOOT plays distinct left and right tones, so a channel-select error would be visible.

### Controls

| Ref | Part | Pads | Net → U1 | Pull-up | Cap | OK |
|---|---|---|---|---|---|---|
| SW1 | D2LS-21 (front) | COM/NO, land per Omron p2 | BTN_LEFT → U1.1 GPIO1 | R111 10 k | none | ✓ |
| SW2 | D2LS-21 | COM/NO | BTN_RIGHT → U1.2 GPIO2 | R112 10 k | none | ✓ |
| SW3 | D2LS-21 | COM/NO | DART_LEFT → U1.3 GPIO3 | R601 10 k | none | ✓ |
| SW4 | D2LS-21 | COM/NO | DART_RIGHT → U1.4 GPIO4 | R602 10 k | none | ✓ |
| SW5 | B3U-1000P (back) | 1/2 at ±1.7, 0.9 × 1.7 (Omron 4.2/2.6/1.7) | PWR_WAKE → U1.104 GPIO0 (LP, ext1 wake) | R110 10 k | C601 100 nF (τ 1 ms) | ✓ |
| SW6 | B3U-1000P | same | RESET_MR → U14.3 MR (TPS3808: 90 k internal pull-up; RESET → CHIP_PU) | R607 10 k | C602 100 nF | ✓ |
| SW7 | B3U-1000P | same | BOOT_STRAP → U1.66 GPIO35 (strap: 0 = download) | R108 10 k | none | ✓ |

- SW1-SW4 are D2LS-21, not B3U. The D2LS is rated 6 VDC / 1 mA; the 0.33 mA through 10 k is within it.
- U14 TPS3808G33: RESET open drain → CHIP_PU with R106 10 k + C136 1 µF, CT open = 12-28 ms delay, threshold 3.07 V against 3.31 V.
- Strapping: GPIO36 has R109 pull-up (joint download needs 1). GPIO34 has R107 pull-down (ignored with default eFuses). GPIO37/38 accept any value. Table 3-3: BOOT held + RESET tap = download. ✓
- Debounce: firmware 5 ms (`SLIM4_BUTTON_DEBOUNCE_US`) against D2LS 1 ms bounce. ✓ The B3U's 5 ms bounce matters only on PWR_WAKE, which has 100 nF. ✓
- GPIO2-5 are pad-JTAG pins only if eFuse JTAG_SEL_ENABLE is set (P4 Table 3-7). With defaults the source is USB-Serial-JTAG, so the buttons and BCLK are not hijacked. ✓ GPIO1 (XTAL_32K_P) is free: sdkconfig has `RTC_CLK_SRC_INT_RC`. ✓

### USB

- J2 USB4105-GF-A:

| Pads | Net | OK |
|---|---|---|
| A1/B12/B1/A12 | GND | ✓ |
| A4/B9/B4/A9 | USB_VBUS | ✓ |
| A5 | CC1 | ✓ |
| B5 | CC2 | ✓ |
| A6/B6 | USB_DP_CONN | ✓ |
| A7/B7 | USB_DM_CONN | ✓ |
| A8/B8 | NC | ✓ |
| SH (4 × THT) | CHASSIS_GND → R404 0 Ω → GND | ✓ |

  - The footprint pad order matches GCT's "A1B12 A4B9 B8 A5 B7 A6 A7 B6 A8 B5 B4A9 B1A12" and is correctly mirrored for the back side.
  - The mouth datum is at y = 3.0, which is the board edge.
  - D+/D- stubs are about 1-2 mm (≤ 3.5 mm, TUSB320 p29).
- U11 TPD2EUSB30 (DRT-3): pin 1 D+, pin 2 D-, pin 3 GND, 0.7 pF (p3, p5). ✓
- U12 TPD2EUSB30 on CC1/CC2: VRWM 5.5 V covers the CC range. ✓
- D1 PESD5V0S1UL on VBUS: VBR ≥ 6.4 V, above 5.5 V. ✓ It caps the BQ24074's 28 V tolerance, which is acceptable for a no-PD sink.
- VBUS bulk: C409 4.7 µF + C403 100 nF, within the UFP 1-10 µF (TUSB320 p22 Table 14). ✓
- U13 TUSB320LAI (p3):

| Pin | Function | Net | OK |
|---|---|---|---|
| 1 | CC1 | USB_CC1 | ✓ |
| 2 | CC2 | USB_CC2 | ✓ |
| 3 | PORT | GND → UFP | ✓ |
| 4 | VBUS_DET | 900 k (R416 470 k + R417 430 k; spec 855-920 k, p6; 5.5 V → 0.53 V < 4 V abs max) | ✓ |
| 5 | ADDR | NC → GPIO mode | ✓ |
| 6 | INT_N/OUT3 | NC (audio-accessory flag unused) | ✓ |
| 7 | OUT1 | GPIO43 + R605 10 k to 3V3 | ✓ |
| 8 | OUT2 | GPIO17 + R606 10 k | ✓ |
| 9 | ID | NC (DFP only) | ✓ |
| 10 | GND | GND | ✓ |
| 11 | EN_N | GND (enabled) | ✓ |
| 12 | VDD | 3V3_SYS (2.7-5 V) | ✓ |

  - Decoupling: C408 1 µF at 2.6 mm and C407 100 nF at 4.5 mm (p29 asks for 100 nF close). ✓
  - OUT pins: VOL 0.4 V at 1.6 mA; 0.33 mA through 10 k. ✓
  - Abs max VDD + 0.3: pulled up to the same 3V3 rail. ✓
  - CC pins present Rd in all states: dead battery 4.1-6.1 k, UFP 4.6-5.6 k (p5), shutdown (p14). ✓ A C-to-C charger supplies 5 V; at 3 A Rp, CC = 330 µA × 5.1 k = 1.68 V, inside VUFP_CC_HIGH 1.31-2.04 V.
- Firmware `read_usb_current()`: H/H NONE, H/L DEFAULT, L/H 1A5, L/L 3A0. This equals TUSB320 Table 3 (p12). ✓
- `set_charger_mode()` EN2/EN1: 0/1 500 mA, 1/0 ILIM, 1/1 suspend. This equals BQ24074 Table 7-2. ✓ 1.07 A is used only on 1.5 A/3 A. ✓
- D- → U1.52 (GPIO24 = USB1P1_N0), D+ → U1.53 (GPIO25 = USB1P1_P0, USB_PU); USB-Serial-JTAG by default (P4 v0.7 Table 2-1 / pin-function table). ✓ Pin header and FIRMWARE_PINMAP agree.

### J3 battery

- S2B-PH-SM4-TB, KiCad library land. Pin 1 BAT_CONN → Q2.3 (AO3401A drain); Q2.2 source = BAT_PLUS; Q2.1 gate = GND (SOT-23 G/S/D). The reverse-blocking topology is right. Pin 2 GND, MP tabs unconnected. Trace 0.5 mm. ✓ Polarity convention: see U1.

---

## BRING-UP PROBE / TEST TABLE

| # | Measurement or action | Expected | A wrong result means |
|---|---|---|---|
| 1 | Unpowered: diode test D1 (VBUS(+) to GND) and resistance VBUS-GND at C409 | open or > 100 kΩ forward on VBUS; about 0.6-0.7 V with probe reversed (GND → VBUS) | Low or diode drop with + on VBUS: D1 placed reversed (B1) or a short |
| 2 | Unpowered: resistance CC1-GND and CC2-GND at J2 (or U12) | about 5.1 kΩ each (dead-battery Rd 4.1-6.1 k) | Open: no Rd, so C-to-C chargers give no VBUS (U13 missing, rotated or unsoldered). Short: bridge |
| 3 | Plug a USB-C to USB-C charger, no cell | VBUS 5.0-5.25 V at C409 within 1 s, SYS_RAW ≈ 4.4 V | 0 V: Rd missing or CC open (see #2). Cycling VBUS: Rd glitch at U13 power-up (VDD ramp > 25 ms) |
| 4 | With USB: CC1 or CC2 voltage (the one in use) | 0.25-0.61 V default; 0.7-1.16 V 1.5 A; 1.31-2.04 V 3 A | Out of range: Rd value wrong or U12 leaking |
| 5 | Pins 3V3 → U13.12; U13.4 VBUS_DET | 3.3 V; about 0.47 V (5 V × 95 k/995 k) | VBUS_DET ≈ 0: R416/R417 open, so U13 never attaches (OUT stays H/H) |
| 6 | USB_CURR_OUT1/OUT2 (GPIO43/GPIO17) on a laptop C-port / 3 A charger / unplugged | H/L; L/L (or L/H); H/H. Log `USB-C current advertisement` matches | Stuck H/H with a C source: VBUS_DET or CC path. Stuck L: pull-up missing or short |
| 7 | `idf.py flash monitor`; `lsusb` | 303a:1001 enumerates in both plug orientations | Works in one orientation only: one D+ or D- row not joined. Not at all: D+/D- swapped or open at R401/R402/U1.52/53, or U11 short |
| 8 | AUDIO_SD_CTRL (R504) idle, U8.4, U9.4 | 0 V, 0 V, 0 V | > 0.1 V: GPIO8 pulled up (amplifiers not in shutdown) |
| 9 | Press any control (tone playing): U8.4 / U9.4 | 3.1-3.3 V / 0.97-1.16 V (typ 1.07 V) | U9 > 1.25 V: R502/R503 wrong value (plays left). U9 < 0.83 V: plays (L+R)/2 (R503 too high, e.g. 1.1 M). U8 ≈ 1 V: R501 wrong |
| 10 | SYS_RAW at C420/C421 | 4.4 V on USB, VBAT on the cell | Lower under load: VDD neck or via too resistive |
| 11 | Scope BCLK at U8.16/U9.16, LRCLK at pin 14, DIN pin 1 while a tone plays | BCLK 1.536 MHz, LRCLK 48.000 kHz 50 % duty, monotonic edges, overshoot < 0.5 V | Ringing or steps on edges: reduce drive (B2). Wrong frequency: I2S clock configuration |
| 12 | Press SW1/SW3 then SW2/SW4 with speakers on J4 and J5 | Left tone only from J4 (880 / 660 Hz); right only from J5 | Both from one side or mixed: SD_MODE levels (#9). Swapped: J4/J5 cable or U8/U9 swapped. Silence: amplifier solder, SD high, or BCLK |
| 13 | Differential output at J4 with the speaker attached, scope | 330 kHz PWM, about 0 V average in shutdown; outputs low (p28) | DC offset: LRCLK/BCLK sequencing fault |
| 14 | Loud tone, 1 minute, thermal camera on the In3 speaker tracks and U8/U9 (100 % volume, 4 Ω) | U8/U9 < 70 °C; no hot spot over SPK traces | Confirms M1/M2; apply the firmware volume cap |
| 15 | SW1-SW4 / SW7: GPIO idle and pressed; self-test lines | 3.3 V idle, < 0.1 V pressed; SELFTEST PASS for each pull | OPEN: switch or pull-up unsoldered. HELD: switch stuck, D2LS rotated (B1), or bridge |
| 16 | SW6 RESET tap; scope CHIP_PU | goes low while pressed, rises 12-28 ms after release (τ 10 ms) | No reset: U14 MR or RESET path. Stays low: 3V3 below 3.07 V |
| 17 | Hold SW7, tap SW6, release SW7 | ROM log `waiting for download` on USB | Normal boot: GPIO35 not low at reset (R108/SW7 path) |
| 18 | SW5: deep sleep, then press | wakes (ext1 on GPIO0); PWR_WAKE rise about 0.7 ms (self-test) | No wake: GPIO0 / C601 / R110 |
| 19 | Before connecting: measure the pack in a loose PH socket. Then on J3 | J3.1 = +VBAT, J3.2 = GND | Pack reversed: re-pin the housing, never plug it in |
| 20 | Deep sleep current from the cell | below about 0.2 mA (no amplifier standby) | About 0.7 mA more: amplifiers in standby (#8) |
| 21 | No cell, USB-C 3 A, backlight 100 %, play loud music | no reset or brownout | Reset: M7 confirmed; cap or mute audio without a cell |
