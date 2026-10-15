# PASS 7 plan (R07): direct graphics and optional compute bring-up

R06 is finished as far as host, RTL and planning evidence can take it. R07 needs things this
environment does not have: hardware, the Efinity toolchain, the F133 SDK, and BRT_AN_086. Each
item lists its **entry condition**, **work**, **evidence produced** and **exit test**.

## 0. Unblock first (cheap, highest value)

| # | Item | Why it blocks |
|---|---|---|
| U1 | Obtain the F133 user manual (or the D1s one): BROM BOOT-SEL table and SPI_BCC / quad-mode registers | Decides whether PC4/PC5 strap resistors are needed. Decides whether BT820 Dual/Quad is possible, or Single only |
| U2 | Obtain BRT_AN_086 (BT82X programming guide) | Register map, host-command codes, REG_SYS_CFG, display init, data byte order, the meaning of 0x7Fxxxxxx |
| U3 | Run Efinity on `fpga/efinity` (any licensed workstation) | Turns NATIVE_EDA_NOT_RUN into real fit/STA results for T35F400C3 |
| U4 | Confirm the MN820 CN1 power-pin direction (Bridgetek support / VM820C schematic) | Board power tree |

## 1. F133 BSP and two SPI drivers (PASS_6_AND_7 R07.1)

* Entry: an F133 board or a D1s-class dev board with SPI1 on PD10–PD13 and SPI0 on PC2–PC5
  reachable, plus a pinned toolchain and SDK (record versions and licences).
* Work: implement `arc1_spi_hal` for SPI1 (BT820) and SPI0 (T35). CS# must stay asserted across
  calls, or a one-shot read with in-buffer 0x01 search is needed (firmware README assumption 3).
* Evidence: a build log and image hash (build-only if there is no board), then a logic-analyser
  capture of one BT820 read and one AMBX read.
* Exit: `bt820_read` returns the BT820 chip-ID register (address from U2), and `t35_probe` reads
  "AMBX".

## 2. BT820 init and drawing (R07.2/.3)

* Entry: U2, an MN820 (or VM820C) board, and the candidate panel or Bridgetek's evaluation panel.
* Work: init sequence from BRT_AN_086 in single channel mode; a display list with a test
  pattern; capture the command trace through the existing `bt820_host` layer. Mock tests are
  extended with the real command encodings.
* Exit: a visibly lit, photographed test pattern, plus a reproducible SPI trace. Claim nothing
  before the display is visibly working.

## 3. T35 on hardware (R07.4)

* Entry: U3 clean (fit + timing), plus a T35 board with the PSRAM wired per
  `board/r06_board_plan.json` (including the 2.2 kΩ power-up pull-downs).
* Work: start at SCLK 10 MHz, then 20 MHz. The F133 starts the BIST over SPI. Then compare
  BIST at a temperature corner and after FPGA reconfiguration (QPI-reset assumption). Scope
  SCLK/SIO to check edges and the pull-down load.
* Work (RTL): an R05 frame receiver behind the mailbox: CRC32, R05 session/credit rules, the
  R05 `arc1_transform.sv` engine, RESULT/STATUS emission. The host mock `ENG_SW_ACCEL` is the
  behavioural specification. Its tests become the RTL acceptance tests.
* Exit: BIST PASS on real silicon (that is the first PROTOTYPE_MEASURED item), plus
  `accel_transform_batch` returning ACCEL_FB_NONE against the real FPGA with `verify = 1`.

## 4. Fallback on hardware (R07.4)

Repeat the R06 degradation matrix on the bench: T35 unpowered, held in CRESET_N, unconfigured,
reset mid-job, and a deliberately broken bitstream. The BT820 test pattern must keep updating
throughout. Log the fallback counters.

## 5. Synthetic 2D workload, CPU vs. offload (R07.5)

Label everything **synthetic**: N layers, M animated sprites, culling and batch transforms.
Measure on the F133: CPU-only frame time; offload frame time including mailbox SPI time, PSRAM
traffic and retries. Use the R06 simulated PSRAM figures (≈ 11.8/8.6 MB/s at 40 MHz SCLK) only to
pre-screen job sizes. Decide **go/hold/redirect** for the T35 strictly from the measured
end-to-end difference.

## 6. Manufacturing dependencies (R07.6)

Schematic capture from the board plan (single source of truth). Footprints: SOP-8 PSRAM, BGA400
T35, eLQFP128 F133, DF40 receptacle. Power tree with the R06 sequence. Then SI review of the
PSRAM and SPI nets, and JLCPCB DFM/assembly constraints. **No order until all of it is signed
off.**

## Carry-over risks from R06

BOOTSEL_SHARED_WITH_SPI0, F133_QUAD_IO_UNCONFIRMED, PSRAM_POWERUP_PULLS (load and SI),
MN820_POWER_PIN_WORDING, the QPI-reset-to-SPI-device assumption, the PSRAM→T35 low-level
margin (+0.106 V on datasheet limits), and the BT820 32-bit byte order.
