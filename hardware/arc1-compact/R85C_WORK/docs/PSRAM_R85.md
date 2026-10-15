# APS6404L 8 MiB PSRAM on the ECP5 (R8.5, CO 5.2)

## Electrical fit to the selected bank

| Item | Value | Source |
|---|---|---|
| Device | APS6404L-3SQR, 3.3 V version, VDD 2.7–3.6 V, QSPI, 8 MiB | AP Memory DS Rev 2.7 (R06/R07 sources) |
| ECP5 bank | bank 6, VCCIO6 = 3V3_FPGA, LVCMOS33, PULLMODE = NONE, SLEWRATE = FAST | LPF (generated), `board/ECP5_BANK_TABLE_R85.csv` |
| Balls | CE# L1, SCLK L2 (22 Ω series), SIO0 L3, SIO1 M1, SIO2 M3, SIO3 M4, PSRAM_PG N1, PSRAM_EN N2 | `board/ECP5_BALL_MAP_R85.csv` |
| Power | PSRAM_VDD switched by U12 (ON = PSRAM_PWR_REQ AND DONE_DLY), TPS3808G30 PG → FPGA guard | rule `psram_power_architecture` |
| Unconfigured FPGA | ECP5 user I/O tri-state with weak pull-**down** (DS 4.1); PSRAM unpowered; R08 U26 switched pull-downs removed | margins `psram` group |
| CE# pull-up | 10 kΩ to PSRAM_VDD; the FPGA ball must not pull down in user mode (1.7 V otherwise) → PULLMODE = NONE | margins row (RK-ECP5-PULLMODE, OPEN by design choice) |
| Read timing | SCLK 20 MHz (psram_mclk 40 MHz): hand budget 13.0 ns < 25 ns half period; 40 MHz fails (13.0 > 12.5 ns) | margins `psram_timing`; pad delays are ASSUMPTIONS |

## Controller and tests (RTL unchanged from R06, re-run in R8.5)

The R06 controller (`R06_WORK/fpga/psram/rtl`) and the R08 power guard are used unchanged, and vendor-neutral. The R8.5
runner re-runs the R06 controller bench (three clock configurations plus mutants) into a scratch directory:

| CO 5.2 requirement | Where |
|---|---|
| power-on bring-up, CE#/CLK/IO default levels, reset | R06 T1 (no CE# before tPU, ID check, QPI entry); R8.5 tb_ecp5_top P0/P1 (CE# = VDD, CLK low, SIO low during tPU, monitored continuously) |
| datasheet command/mode handling | R06 model checks tPU, tCPH, tCEM, tCSP, tCHD, tSP, tHD, tRST, Read ID ≤ 33 MHz; `R06_WORK/fpga/psram/PSRAM_TIMING_TABLE.md` |
| fixed patterns, walking bits | R06 T2 (bit walking) |
| random addresses | R06 T4 (200 random ops incl. hot-spot, page-edge, top of memory), T3 (address walking all 23 bits) |
| page/burst crossings | R06 T6 (+ global zero page-crossing check), T7 (32 × 256 B back-to-back) |
| sustained / worst-case rate | R06 `PSRAM_TIMING_TABLE.md` (RTL_SIMULATED, sequential 256 B ops incl. CDC): C1 SCLK 20 MHz ≈ 7.5 MB/s write, ≈ 6.3 MB/s read; worst case listed C3 12.5 MHz ≈ 3.1 / 2.4 MB/s. C2 (40 MHz) is excluded on the ECP5 by the pad budget |
| failures | R07 R1 dead chip, R2 KGD fail, R3 power interruption; R8.5 P2–P4 power loss, F06 CE# stuck (PSRAM_ERROR + BIST fail, then recovery) |
| in-system BIST | `psram_bist` (64 × 256 B LFSR, write then read back), started from the F133 over AMBX (P4) |

Read latency (PLANNING_CALCULATED, wire only): QPI 'hEB = 2 command + 6 address + 6 wait SCLK cycles = 14 cycles =
0.7 µs at 20 MHz before the first data nibble. Controller start-up and the CDC handshake add to this. They have not
been measured separately.

## Not proven

Pad timing (no IBIS, no layout), real power-up behaviour, VOH under load, and that the device ignores the QPI-form reset
while in SPI mode (R06 note). PSRAM is optional: the service runs register-only jobs without it, unless a game image sets
CAPS bit 0 as required (FIT F07a/F07b).
