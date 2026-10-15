# Two-stage bench bring-up plan (R07)

Goal: turn RESOLVED-DOC / ASSUMPTION / BUILD-ONLY items into **PHYSICAL-HARDWARE** evidence
on development hardware **before** any custom PCB. Each step changes one unknown and has a pass
criterion and an artifact to archive under `evidence/bench_<date>/`: photo, log, scope or
logic-analyser capture, and instrument model.

Equipment: current-limited bench supply, 4-channel scope (≥ 200 MHz), logic analyser
(≥ 100 MS/s with SPI decode), USB-UART (3.3 V), multimeter, PC with `sunxi-fel`.

## Stage A: F133 alone (D1s-class dev board, e.g. MangoPi MQ-R, or the first ARC-1 board with MN820/T35 unpopulated)

| Step | Action | Pass criterion | Closes |
|---|---|---|---|
| A0 | Power from a current-limited supply; log idle current | No over-current; rails in window (3V3 3.20–3.40 V) | power tree sanity |
| A1 | Scope PC4/PC5 through RESET release, T35 absent and T35 held in CRESET_N | Both ≥ 0.7·VCC-IO throughout | RK-BOOT-STRAP |
| A2 | Boot `arc1_r07_f133.egon` from microSD (sector 16) | UART banner. VER_REG[12:11] = 3. SID/fast-boot logged. | RK-F133-IMG, RK-BOOT-EFUSE, RK-BOOT-DOC (empirical) |
| A3 | Remove microSD, power-cycle | `sunxi-fel version` sees the SoC | RK-FEL |
| A4 | Logic analyser on SPI1 with nothing attached (MISO pulled down) | Read polling shows TIMEOUT signature; CS# behaviour as coded | HAL sanity |

## Stage B: F133 + MN820 (VM820C as carrier first, then the ARC-1 board)

| Step | Action | Pass criterion | Closes |
|---|---|---|---|
| B0 | MN820 on VM820C under Bridgetek's own tools/samples | Vendor demo runs (known-good module) | module sanity |
| B1.1 | Wire F133 SPI1 + RST_N + INT_N to the module per board plan; module powered by the host 3V3 through a current limit | ≤ ~245 mA typical with test card (MN820 Table 3); no back-feed | RK-MN-PWR |
| B1.2 | Run the banner image | REG_BOOT_STATUS 0x522E2E2E, REG_CHIP_ID 0x08200100, REG_ID 0x7C, CPURESET 0 | first silicon proof of the host layer |
| B1.3 | Scope MISO/IO high level at the F133 pin | VOH margin vs 0.7·VCC-IO measured | RK-MN-VOH |
| B1.4 | Capture a RAM_CMD write (FF 00 00 00 …) and a host command (FF E9 …) | Wire bytes equal the host tests; chip behaves (FIFO advances; config applied) | RK-BT-DECODE |
| B1.5 | Command FIFO test frame | REG_CMD_READ catches up; no 0x3FFF | FIFO path |
| B1.6 | Scan-out with confirmed panel timing | **Visibly lit blue screen, photographed**; REG_FRAMES increments at the expected rate | RK-PANEL (first display claim) |
| B2 | Optional: SPI_WIDTH dual/quad with STC=0 | Correct data at 2×/4× width | RK-SPI-QUAD |

## Stage C: T35 + PSRAM (after a native Efinity run is clean)

| Step | Action | Pass criterion | Closes |
|---|---|---|---|
| C1 | Efinity build with reports archived | Fit + STA pass at sys 80 MHz / PSRAM 40 MHz | RK-T35-EDA |
| C2 | Scope PSRAM CE#/SCLK/SIO during the 3V3 ramp with the T35 held in reset | CE# within 200 mV of VDD; SCLK/SIO ≤ 0.4 V for ≥ 150 µs | RK-PSRAM-PU |
| C3 | Measure PSRAM VOH while driving the pull-downs | ≥ 2.0 V + margin at the T35 pin | RK-PSRAM-VOH |
| C4 | F133 releases CRESET_N; mailbox MAGIC "AMBX"; BIST at 10 then 20 MHz, after warm FPGA reset (QPI-reset assumption) | BIST PASS, 0 errors | RK-PSRAM-QPIRST, controller on silicon |
| C5 | Degradation matrix on the bench (T35 off, held, unconfigured, reset mid-job) while the BT820 test pattern runs | Picture keeps updating; fallback counters as in the host tests | functional gold rule |
| C6 | Brown-out the PSRAM rail (if separable) or the whole 3V3 under supervisor | System resets, no silent corruption | RK-PSRAM-BROWNOUT |

Only after stages A–C pass may schematic capture be frozen and a JLCPCB quote be requested. That
still requires the R07 handoff §8 release list: schematic review, layout, DFM/DFA, BOM, test
plan.
