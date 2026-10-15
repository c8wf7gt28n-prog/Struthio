# ARC-1 Compact R06: board-level architecture (draft)

Status: **SELECTED_UNVERIFIED**. This document describes a design that follows the owner's direction. It
is not proof that the design works electrically: no schematic, PCB, BOM or prototype exists. The
machine-checked source of truth for pins and voltages is `../board/r06_board_plan.json`; its
generated table is `../board/PIN_MAP_R06.md`.

## 1. Topology

```
                 3V3 ─┬──────────────┬──────────────────┬───────────────┐
                      │              │                  │               │
        ┌─────────────┴───┐   SPI1 (PD10-15, single     ┌┴──────────────┐ LVDS  ┌───────────┐
        │ F133-B eLQFP128 │── mode baseline) ─────────▶ │ MN820 (BT820B │──────▶│ LCD cand. │
        │ 64 MiB DDR2     │   RST_N PD16, INT_N PD17    │ + 128 MiB     │       │ (unfrozen)│
        │                 │                             │ DDR3L)        │       └───────────┘
        │  HPOUT L/R ─────┼──▶ stereo speaker amp (NOT selected; SD_N on PE10)
        │  SMHC0 PF0-5 ───┼──▶ microSD (boot + assets)
        │                 │   SPI0 (PC2-5), IRQ PC6,    ┌───────────────┐ QPI  ┌──────────────┐
        │                 │── CRESET_N PE8, CDONE PE9 ─▶│ T35F400C3     │─────▶│ APS6404L 8MiB│
        └─────────────────┘   (OPTIONAL path)           │ BANK1D mailbox│BANK1C│ PSRAM SOP-8  │
                                                        │ BANK1A config │      └──────────────┘
                                                        └──────┬────────┘
                                                        SPI flash (active x1 config)
```

* **Single command master for the BT820.** Only F133 nets reach MN820 CN1 SPIS_* (enforced by
  rules `topology.bt820_independent_of_t35` and `topology.bt820_single_command_master`).
* **The T35 is optional.** Nothing on the boot path, display path or audio path passes through it.
  The F133 can hold it in reset (CRESET_N) or reconfigure it, and sees it only through the SPI0
  mailbox and IRQ.
* **Memory pools are private:** F133 DDR2 (in package), BT820 DDR3L (on MN820), and T35 PSRAM
  (`topology.psram_private_to_t35`).

## 2. Interface decisions and evidence

| Link | Decision | Evidence | Open item |
|---|---|---|---|
| F133 → BT820 | SPI1 PD10–PD15 (Function4), VCC-PD = 3.3 V, BT820 VCCIO1 = 3.3 V | F133 DS Table 4-2/4-3 + Linux pinctrl cross-check; BT820 DS 4.5 | **Baseline single-channel SPI.** F133 lists Quad-Output/Quad-Input only, and BT820 quad mode needs a quad *address* phase. Dual/Quad only after the F133 user-manual register check plus a bench test. WP = IO2, HOLD = IO3 is the usual convention but is unconfirmed for F133. |
| BT820 SPI clock | ≤ 60 MHz (Tsclk ≥ 16.6 ns), mode 0 | BT820 DS Table 28 | The F133 SPI1 achievable clock is not in the F133 DS. Plan ≤ 30 MHz until measured. |
| F133 → T35 | SPI0 PC2–PC5 (Function2), VCC-IO 3.3 V, T35 BANK1D 3.3 V | as above | PC4/PC5 are also BOOT-SEL0/1. The boot-select encoding is **BLOCKED** (not in the F133 DS). |
| Boot / storage | microSD on SMHC0 PF0–PF5 | F133 DS 2.2.1, Table 4-3 | eMMC on SMHC2 is impossible (it shares PC2–PC7 with SPI0). UART0 debug moves to PE2/PE3 (Function6). |
| T35 → PSRAM | BANK1C GPIOL_46..51 (one clock region L2), 3.3 V LVCMOS | T35 pinout workbook (R05 CSV), T35 DS Tables 63/66 | Efinity IO placement and STA: NATIVE_EDA_NOT_RUN |
| T35 config | SPI active x1 from its own flash in BANK1A; F133 controls CRESET_N/CDONE | T35 DS "Configuration" and Table 61 | AN 006 not yet reviewed; flash part not selected |
| Audio | F133 codec HPOUTL/R → external stereo speaker amplifier. I2S2 (PB4–PB7) and TWI0 (PB2/PB3) **reserved** for an optional external DAC/codec fallback | F133 DS 2.8.1, Table 4-3 | Amplifier, speaker, load and noise: not selected or measured. No audio processor is added. |

### I/O level margins (worst case over each rail's window, PLANNING_CALCULATED)

The `level.compatible[...]` rules in `check_board_plan.py` evaluate VOH−VIH and VIL−VOL at both
ends of the 3V3 window (3.14–3.47 V). The tightest results:

| Path | High margin | Low margin |
|---|---|---|
| T35 → PSRAM (VOH = VCCIO−0.2 vs VIH = VDD−0.4, same rail) | +0.200 V | +0.200 V |
| PSRAM → T35 (VOL = 0.2·VDD vs VIL 0.8 V) | +0.512 V | **+0.106 V** |
| BT820 → F133 | +0.542 V | +0.542 V |

These are datasheet DC limits at the stated test currents, not measurements. Ground bounce and
the 2.2 kΩ pull-downs (below) consume part of the PSRAM low-level margin, so it has to be
measured on the first board.

## 3. A power-up hazard found and mitigated in R06

The APS6404L requires **CLK low, CE# high and SIO low** from the start of the VDD ramp until
tPU (150 µs) has elapsed (DS section 8). Trion GPIOs sit in **weak pull-up** (27–65 kΩ) during
configuration, which drives CLK and SIO *high* for the whole configuration time. The draft plan
therefore adds:

* 10 kΩ pull-up on PSRAM CE#.
* **2.2 kΩ pull-downs on PSRAM SCLK and SIO0–3**, which hold the lines at ≤ 0.261 V against the
  T35's minimum 27 kΩ pull-up at 3.47 V (VIL max 0.4 V). The checker computes this
  (`psram.powerup_low_during_t35_config`).
* A cost: about 1.5 mA per line whenever the T35 drives it high. T35 drive strength and edge
  rates need an SI review.

The alternative (switching PSRAM VDD after T35 user mode) was rejected for now. The T35's
pulled-up I/O would back-power an unpowered PSRAM beyond its VT ≤ VDD+0.4 V absolute maximum.

## 4. Rails and sequencing (draft)

| Rail | Consumers | Window | Source |
|---|---|---|---|
| 1V2_T35 | T35 VCC, VCCA_PLL (+ MIPI analog pins tied to VCC per Table 59) | 1.15–1.25 V | T35 DS Table 63, 59 |
| 3V3 | F133 VCC-IO/PD/PE/PG; every T35 VCCIO bank; PSRAM VDD; MN820 VIN; microSD; T35 config flash | 3.14–3.47 V (tightest consumer: T35) | T35 Table 63, F133 Table 5-2, APS6404L Table 9, MN820 5.1 |
| 1V8_AN | F133 AVCC, HPVCC (and VCC-RTC/VCC-PLL if noise allows) | 1.764–1.836 V | F133 Table 5-2 |
| F133 core / DRAM | VDD-CORE, VDD-SYS, VCC-DRAM | not transcribed in R06 | F133 Table 5-2 and reference design |
| T35 VCCIO_DDR | — | **left floating**, DDR_VREF to GND (DDR unused) | T35 Table 59 |
| AMP_VIN | speaker amplifier | not selected | — |

Sequence (`power_sequence` in the plan): 1V2_T35 → 3V3 (within 10 ms, ramp VCCIO/10 to
10 V/ms) → F133 core rails ≥ 2 ms after VCC-IO → F133 RESET released > 64 ms after its rails are
stable. The T35 configures itself after tCRESET_N. The F133 can force reconfiguration through
PE8.

## 5. Reset / dependency graph

```mermaid
graph TD
  PWR[3V3 + 1V2_T35 + F133 rails stable] --> F133RST[F133 RESET release > 64 ms]
  F133RST --> BROM[F133 BROM: microSD boot]
  BROM --> FW[F133 firmware]
  FW -->|PD16 high| BTRST[BT820 RST_N released]
  BTRST --> BTINIT[BT820 host cmds + display init<br/>(single SPI mode)]
  BTINIT --> GFX[CPU-only graphics: CPU -> BT820 -> LCD]
  PWR --> T35CFG[T35 self-configures from flash]
  T35CFG -->|CDONE| T35UM[T35 user mode]
  T35UM --> PSRAMINIT[PSRAM PU wait, reset, ID, QPI]
  PSRAMINIT --> MBX[Mailbox reports FPGA_READY]
  FW -.optional HELLO via SPI0.-> MBX
  MBX -.optional jobs.-> GFX
  FW -.timeout / NOT_READY / error.-> CPUFB[CPU fallback computes the job]
  CPUFB --> GFX
```

The solid path from power to `GFX` contains **no T35 node**. Every T35 edge is dotted, and
`CPUFB` closes the loop when the accelerator is absent, late or faulty. The host model in
`../firmware/` exercises this fallback (HOST_TESTED).

## 6. Not decided in R06

LCD panel, size and orientation (the R05 Newhaven 7" 1024×600 remains an evaluation
candidate). F133 PMIC or regulators. Oscillator and config-flash part numbers. Speaker amplifier.
Buttons. Mating CN1 receptacle. ESD/EMI. Stack-up. JLCPCB DFM. Any PCB release: none is
permitted on this evidence.
