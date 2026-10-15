# ECP5 power tree, sequencing, decoupling and test points (R8.5)

Source of truth: `cad/gen/design.py` (sheets `power` and `fpga`). Numbers: `analysis/electrical_margins_r85.py`
(generated `docs/ELECTRICAL_MARGINS_R85.md`). Lattice facts: `sources/lattice/ecp5_power_config_facts.json`.
Evidence: DERIVED_WITH_CALC. Nothing here has been measured.

## 1. Tree

```
VBUS_5V ──U9 TLV62569P (EN = FPGA_PWR_EN, PG -> F133 PD1) ── L4 2.2 µH ── 1V1_FPGA_REG ──0R── 1V1_FPGA   ECP5 VCC   (20 balls)
3V3 ─────U10 TPS22918 (ON = FPGA_PWR_EN, CT 1 nF) ──────────────────────────────────────── 3V3_FPGA   VCCIO0/1/2/3/6/7/8 (18 balls)
                                                                                          ├─ X1 25 MHz XO, PSRAM switch U12, supervisor U14
3V3_FPGA ─U30 TLV75525P (IN = EN = 3V3_FPGA) ── 2V5_AUX_REG ── FB2 120 Ω ferrite ────────── 2V5_FPGA_AUX ECP5 VCCAUX (4 balls)
FPGA_PWR_EN: 100 kΩ pull-down (FPGA off while the F133 is in reset); F133 PE0 drives it through 1 kΩ; J11 jumper 1-2 forces it high
```

| Rail | Nominal | ECP5 limit (DS Table 3.2) | Worst-case DC (calc) | Budget (calc, ASSUMPTION parts) | Regulator rating |
|---|---|---|---|---|---|
| 1V1_FPGA (VCC) | 1.095 V (0.6 × (1 + 82.5k/100k)) | 1.045–1.155 V | inside the window with ±2 % VFB, 1 % resistors | 0.27 A (116 mA static DS + 150 mA dynamic ASSUMPTION) | 2 A |
| 2V5_FPGA_AUX (VCCAUX) | 2.5 V | 2.375–2.625 V | 2.46–2.54 V incl. ferrite drop (LDO ±1.5 % ASSUMPTION) | 0.04 A (17 mA DS + 23 mA ASSUMPTION) | 0.5 A |
| 3V3_FPGA (all VCCIO) | 3V3 − switch drop | LVCMOS33 3.135–3.465 V | see margins (same root cause as RK-3V3-SUP) | ≈ 0.08 A incl. PSRAM, XO, LDO input, pull-ups | 2 A |

The R08 T35 rails (1V2_T35, 1V2_T35_PLL, 3V3_T35 sequenced by the 1V2 PG) are gone; see `docs/T35_TO_ECP5_DELTA_R85.md`.

## 2. Sequencing (why one shared enable)

* TN-02038 §4: VCCIO should come up **before or together with** VCC and VCCAUX. DS: POR watches VCC, VCCAUX and VCCIO8 on
  ramp-up. For slave SPI the DS gives no further order.
* TN-02032 §4.6: left/right banks (2, 3, 6, 7) are not hot-socket safe when a pin is driven above VCCIO, or when VCCIO is
  up before VCC reaches POR and a pair pin is driven. Bank 6 holds the PSRAM and the clock.
* Design: VCC, VCCIO and VCCAUX start from **one** enable. The VCCAUX LDO is fed and enabled by 3V3_FPGA, so its output
  follows the 1.7 V/ms VCCIO ramp until it regulates: VCCIO and VCCAUX rise together, and VCC (buck soft-start ≈ 1 ms)
  rises at the same time. No FPGA rail waits for another FPGA rail's PG (the R08 T35 order, VCC first, contradicts
  the ECP5 checklist).
* In bank 6 during the ramp: the PSRAM is unpowered (EN = PSRAM_PWR_REQ AND DONE_DLY), CE#/SIO/SCLK are pulled low,
  and the XO drives only P3 (its pair ball P4 is unconnected). So no pin is driven above VCCIO and no pair pin is
  driven against another.
* Ramp rates: 3V3_FPGA ≈ 1.7 V/ms (TPS22918 CT = 1 nF), VCC ≈ 1.1 V/ms (buck soft-start, typical) – both inside
  0.01–10 V/ms (DS Table 3.3). VCCAUX inherits the VCCIO ramp (limit 30 mV/µs). Bench item: confirm the TLV755
  start-up does not step faster when its UVLO releases.
* Power-down: the F133 drops PSRAM_PWR_REQ, isolates SPI0 (BUS_EN_N = 1), then FPGA_PWR_EN (`ecp5_safe`). POR
  ramp-down detection covers VCC/VCCAUX only. VCCIO8 has none, so it falls together with VCCAUX from the same switch.

## 3. Back-power and isolation (FPGA off, rest of the system running)

| Path into an unpowered ECP5 | Protection |
|---|---|
| SPI0 SCK/MOSI/SS (bank 8) | U21–U23 SN74LVC1G125 outputs hi-Z (BUS_EN_N 10 kΩ pull-up, firmware keeps 1 while off); bank 8 is hot-socket tolerant |
| PROGRAMN (bank 8) | F133 PE8 used open-drain only (low or input), 470 Ω series. The firmware never drives it high (ecp5_safe releases it when powering off) |
| INITN / DONE / IRQ_N | inputs to the F133; their pull-ups go to 3V3_FPGA (read 0 while off, no back-feed) |
| PSRAM pins (bank 6) | PSRAM unpowered while the FPGA is unconfigured; only pull-downs and CE#→PSRAM_VDD |
| FPGA UART RX (bank 0) | 1 kΩ series to the header (external adapter) |
| PSRAM_PG / PSRAM_EN (bank 6) | driven from the 3V3_FPGA domain only (supervisor U14 and AND gate output U13 pulled low) |

## 4. Decoupling (TN-02038 Table 3.1) – implemented counts

| Rail | Balls | Implemented | Checklist |
|---|---|---|---|
| VCC | 20 | 20 × 100 nF + 3 × 10 µF (+ 2 × 22 µF at the buck) | 100 nF per ball + 3 × 10 µF |
| VCCAUX | 4 | 120 Ω ferrite + 10 µF + 4 × 100 nF (+ 1 µF LDO output) | ferrite + 10 µF + 100 nF per ball |
| VCCIO (7 banks) | 18 | 18 × 100 nF + 7 × 10 µF | 10 µF + 100 nF per ball (1 µF allowed for unused banks) |

Rule `ecp5_decoupling` and negative test `test_vcc_decoupling_short` enforce it. Placement (caps under the BGA, short
via-in-pad or dog-bone) is an R09 layout item.

## 5. Test points and diagnosis

TP: 1V1_FPGA, 2V5_FPGA_AUX, 3V3_FPGA, FPGA_PWR_EN, FPGA_VCC_PG, FPGA_DONE, DONE_DLY, FPGA_PROGRAMN, FPGA_INITN,
FPGA_OSC_25M, FPGA_SCK, PSRAM_VDD, PSRAM_PG, PSRAM_EN. The F133 reads FPGA_VCC_PG (PD1), INITN (PD0), DONE (PE9) and
PSRAM_PG (PE11). The loader turns them into distinct errors: E_POWER (no VCC PG), E_INITN_TIMEOUT (POR not released
→ VCCAUX/VCCIO8), E_PROGRAMN_HELD. These are failure cases F03a/F11/F05 in `docs/FAILURE_INJECTION_R85.md`.
The 0 Ω link 1V1_FPGA_REG→1V1_FPGA allows staged power-on and current measurement.

## 6. Open items

Dynamic currents (Lattice power calculator not run), LDO accuracy and TLV755 start-up slope, ferrite DCR, 3V3 supervisor
dead band (RK-3V3-SUP), and every layout-dependent PDN property.
