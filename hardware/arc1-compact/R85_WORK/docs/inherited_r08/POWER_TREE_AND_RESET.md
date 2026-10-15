# Power tree, sequencing, reset and audio (R08; corrective handoff power/audio dossier, gate G7)

Numbers are computed in `analysis/electrical_margins_r08.py`, and the result table is `docs/ELECTRICAL_MARGINS_R08.md`.
Labels: DOC = datasheet value, PLAN = chosen in `design.py`, ASSUMPTION = no source yet.

## 1. Rails

| Rail | Source | Setpoint (calc) | Consumers | Limit (DOC) |
|---|---|---|---|---|
| VBUS_RAW → VBUS_5V | USB-C J1 → PTC F1 (1812, hold ≥ 2.6 A, MPN R09) + TVS D1 | 4.75–5.25 V | bucks, MAX98357A × 2, TUSB320 VBUS_DET | sink only, no source path (D-04) |
| 3V3_REG → 0 Ω link → 3V3 | U3 TLV62569PDDC, 453k/100k | 3.199–3.440 V worst case (3.318 nominal) | F133 VCC-IO/PD/PE/PG/TVOUT/LDO-IN, NOR, buffers, LDO U7, switches U10/U11/U12/U27 | T35 VCCIO 3.14–3.47 (tightest); F133 2.97–3.63 |
| VDD_CORE_REG → 0 Ω → VDD_CORE | U5 TLV62569, 57.6k/100k, EN = PG_3V3 | 0.919–0.973 V | F133 VDD-CORE0/1, VDD-SYS0/1/2 | 0.85/0.95/0.99 (F133 DS rev 2.3) |
| 1V8_DRAM | U6 TLV62569, 200k/100k, EN = PG_3V3 | 1.746–1.854 V | F133 VCC-DRAM0/1 | 1.7–1.9 |
| 1V8_LDOA | F133 internal LDOA (pin 28) | 1.8 V | VCC-PLL, VCC-RTC, VDD18-DRAM, VCC-LVDS, RESET pull-up | per MangoPi MQ D1s reference (A, third-party) |
| F133_LDOB | F133 internal LDOB (pin 30) | unused | 2.2 µF only | as MangoPi |
| 1V8_AN | U7 TLV75518P from 3V3 | 1.8 V | AVCC, HPVCC, VCC-TVIN | 1.764–1.836 (AVCC/HPVCC) |
| 1V2_T35_REG → 0 Ω → 1V2_T35 (+ FB1 → 1V2_T35_PLL) | U9 TLV62569PDDC, 100k/100k, EN = F133 PE0 (pull-down) | 1.164–1.236 V | T35 VCC, VCCA_BL/BR/TR | 1.15–1.25 (margin 14 mV at the low corner: DC only) |
| 3V3_T35 | U10 TPS22918, ON = T35_1V2_PG | follows 3V3 − Ron×I | every T35 VCCIO bank, config flash U19, oscillator X1, U14/U16/U20/U26 | T35 rule: VCCIO after VCC |
| PSRAM_VDD | U12 TPS22918 from 3V3_T35, ON = U13 AND(PSRAM_PWR_REQ, CDONE_DLY) | as 3V3_T35 | APS6404L | 2.7–3.6 |
| 3V3_MN | U11 TPS22918, ON = MN_PWR_EN (pull-up = default on, F133 PD21 may cut) | as 3V3 | MN820 CN1 13/15/17/19 | 3.0–3.6 (MN820 DS 5.1) |
| SD_VDD | U27 TPS22918, ON = SD_PWR_EN (pull-down = off) | as 3V3 | microSD + its pull-ups | SD spec |

**Rail findings (class B):**
- **1V2 margin:** the 1V2_T35 low corner has only 14 mV of DC margin. R09 should choose 1 % feedback resistors closer to the target or a 1 % regulator.
- **3V3 supervisor dead band (RK-3V3-SUP, FAIL):** the 3V3 supervisor (G33, 3.024–3.116 V) leaves a 3.02–3.14 V band where the T35 VCCIO is out of spec and no reset is asserted. The T35 is optional, and PSRAM data is protected by its own supervisor (U14). R09 must choose between a ±1 % regulator and accepting the band.

## 2. Sequencing (structure verified by `board/check_board_r08.py` rule `power_sequencing` + negative tests)

```
VBUS ─> U3 3V3_REG ─0R─> 3V3 ─> U4 TPS3808G33 (CT 2.2 nF -> 13.1 ms) ─PG_3V3─> U5 VDD_CORE, U6 1V8_DRAM
                                     F133 VCC-IO >= 2 ms before VDD-CORE  (F133 DS 5.12)          │
                                                                    U8 TPS3808G09 on VDD_CORE (CT 15 nF -> 86 ms) ─> F133 RESET (pull-up 1V8_LDOA)
F133 firmware: PE0 T35_PWR_EN ─> U9 1V2_T35 ─PG─> U10 3V3_T35 (CT 1 nF ~1.7 V/ms) ─> T35 config (PE8 releases CRESET_N)
               CDONE ─RC 2 ms─> U20 Schmitt ─> CDONE_DLY ─┬─> U13 AND with PE7 PSRAM_PWR_REQ ─> U12 PSRAM_VDD ─> U14 G30 ─> PSRAM_PG (T35, F133)
                                                           └─> U26 LVC07: switched PSRAM pull-downs released
```

**Power-down and brownout:**
- **3V3 sag below the U4 threshold:** PG_3V3 drops, the core and DRAM bucks disable, and the U8 RESET follows as VDD_CORE falls.
- **T35 side:** dropping PE0 removes 1V2, then PG, then 3V3_T35 (QOD discharges it).
- **PSRAM rail loss:** U14 pulls PG low and the T35 guard parks the pads. The mailbox raises POWER_LOST (RTL_SIMULATED, tb_top_r08 P2–P4).

## 3. Reset

| Reset | Source | Hold | Note |
|---|---|---|---|
| F133 RESET (pin 27, VCC-RTC domain) | U8 open drain, 10 kΩ to 1V8_LDOA | ≥ 86 ms after VDD_CORE good; SW1 via MR# | test point for clip programming |
| BT820 RST_N | F133 PD16 via 33 Ω, 10 kΩ pull-down | held until firmware | BT820 DS: ≥ 214 µs low; the firmware boot sequence follows AN086 |
| T35 CRESET_N | F133 PE8 via 1 kΩ, 4.7 kΩ pull-down | held until firmware | unpowered T35 protected |
| NOR /RESET | 10 kΩ pull-up, SW2 (FEL) | — | software reset 66h/99h at every driver init |

## 4. VBUS budget (DERIVED_WITH_CALC on ASSUMPTION loads; panel backlight NOT included: R09)

| Source class (TUSB320 OUT1/OUT2) | Estimated VBUS current | Status | Firmware policy |
|---|---|---|---|
| Default USB (500 mA) | ≈ 0.88 A | **FAIL (RK-USB-BUDGET)** | ARC-1 cannot run at full function from a 500 mA port. Policy: amplifiers shut down, T35 off, "low power source" screen. Even then, the estimate (F133 + MN820) is above 0.5 A |
| Type-C 1.5 A | ≈ 1.0 A with 0.25 W per channel | CONDITIONAL | normal play at reduced volume |
| Type-C 3.0 A | ≈ 1.6 A with 1.4 W per channel into 8 Ω | CONDITIONAL | full volume |

**Owner decision needed (R09):**
- Either require a ≥ 1.5 A Type-C source, or adopt a battery (the BQ24074 power path from SLIM4 is a candidate, see `SLIM4_REUSE_DECISIONS.csv`).
- F133 per-rail current is NOT given in its datasheet. MN820 maximum current is NOT given either (only 245 mA typical).

## 5. Audio: two MAX98357A on I2S (owner decision; F133 analog HPOUT unused)

| Item | Value | Class |
|---|---|---|
| Interface | F133 I2S2: PB4 DOUT0 (F3), PB5 BCLK (F3), PB6 LRCK (F3); no MCLK needed | A (F133 DS Table 4-3; MAX98357A DS) |
| Channel select | U28 SD_MODE driven directly by AMP_EN (high → left). U29 SD_MODE through 210 kΩ with its internal 100 kΩ (3.3 × 100/310 = 1.06 V, inside 0.77–1.4 V → right). AMP_EN low → both < 0.16 V → shutdown | A + B (MAX98357A DS Table 6) |
| Default state | AMP_EN 100 kΩ pull-down: amplifiers off while the F133 is in reset | B |
| Supply | VBUS_5V (2.5–5.5 V OK), 10 µF + 100 nF each | A |
| Gain | GAIN_SLOT left open (datasheet default). Final gain is an R09 tuning item | A |
| Restrictions | LRCLK must not be 11.025, 12, 22.05 or 24 kHz (MAX98357A DS). Firmware must use 32/44.1/48 kHz | A |
| Speakers | J8/J9 JST PH 2-pin SMD (SLIM4 part). Speaker impedance/power selection is R09 | — |

**Not proven:** I2S2 pin function selection on the F133 (needs the F133 user manual register map) and the audio output
quality (class E). The R08 diagnostic image does not exercise audio.

## 6. Test points (debug-first, phase F)

Rails: VBUS_5V, 3V3_REG, 3V3, VDD_CORE, 1V8_DRAM, 1V8_AN, 1V2_T35, 3V3_T35, 3V3_MN, PSRAM_VDD, SD_VDD and 4 × GND.
Control: PG_3V3_BUCK, PG_3V3, F133_RESET_N, T35_1V2_PG, T35_CDONE, CDONE_DLY, T35_CRESET_N, PSRAM_EN, PSRAM_PG,
SD_DET_N, the USB0 D±, UART0 TX/RX, all SPI0 nets, BT_SCK/MISO/INT_N/RST_N and T35_OSC_25M.
0 Ω staged-power links: 3V3, VDD_CORE and 1V2_T35.
