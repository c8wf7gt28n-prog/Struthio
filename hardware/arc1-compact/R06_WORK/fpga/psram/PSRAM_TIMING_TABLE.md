# APS6404L-3SQR command / timing table used by the R06 controller

Source: **AP Memory "APM SPI 3V PSRAM Datasheet" Rev. 2.7, 2024-01-05**,
retrieved 2026-10-15 from apmemory.com, SHA-256 `8defcc47238ab297a8780220fed57c8a8d39e265b8d7e50661bfbfc5be0e3bb4`
(the PDF is not redistributed here; see `../../docs/SOURCES_R06.json`). An older Rev. 2.3 copy
(pjrc.com mirror) agrees on every value below except standby current and the tCEM extended-grade
history note. Label: **MANUFACTURER_DOCUMENTED**. How the RTL uses each value is **RTL_SIMULATED**
only. Nothing here is measured on a board.

## Device facts

| Item | Datasheet value | Section | Controller use |
|---|---|---|---|
| Organisation | 64 Mbit = 8 M x 8, A[22:0] | p.1, 9.1 | 23-bit byte address; requests ending past 0x800000 are rejected (`ST_INVALID`) |
| Supply | VDD 2.7–3.6 V, single supply | p.1, 16.6 | Needs a 3.3 V (or 3.0 V) T35 bank; see board plan |
| VIH / VIL | VDD−0.4 V min / 0.4 V max | 16.6 | T35 3.3 V LVCMOS VOH = VCCIO−0.2 V, VOL = 0.2 V (Trion DS table 66) satisfy this. Margin still needs bench confirmation. |
| VOH / VOL | 0.8·VDD / 0.2·VDD at 0.2 mA | 16.6 | T35 3.3 V LVCMOS VIH 2.0 V / VIL 0.8 V satisfied at VDD = 3.3 V |
| Page | 1 KiB (CA[9:0]) | 9.2 | Every CE# transaction is split so that it never crosses a page |
| Linear burst page crossing | once per burst, ≤ 84 MHz only | 9.2, 10 | Not used (split instead) |
| Wrap 32 | via 'hC0 toggle; no page crossing | 10 | Not used; device stays in power-on default linear mode |
| Drive strength | powers up at 50 Ω | 9.3 | No change |
| Power-on mode | SPI mode; CE# high before any operation | 9.4 | Init starts in SPI |
| Load capacitance | CL ≤ 15 pF system | 16.3 table 7 | PCB constraint (short traces) |
| Decoupling | 1 µF low-ESR at VDD (+ optional 0.1 µF) | 16.4 | BOM/layout requirement |

## Commands (table in section 9.5)

| Command | Code | SPI mode (QE=0) | QPI mode (QE=1) | Max f | Controller use |
|---|---|---|---|---|---|
| Read | 'h03 | S cmd, S addr, 0 wait, S data | n/a | 33 MHz | not used |
| Fast Read | 'h0B | S/S, 8 wait | Q/Q, 4 wait (66 MHz) | 133/84 | not used |
| Fast Read Quad | 'hEB | S cmd, Q addr, 6 wait, Q data | Q/Q, 6 wait | 133/84* | **data reads (QPI), 6 wait cycles** |
| Write | 'h02 | S/S/S | Q/Q/Q, 0 wait | 133/84* | not used (same as 'h38 in QPI) |
| Quad Write | 'h38 | S cmd, Q addr, Q data | same as 'h02 | 133/84* | **data writes (QPI), 0 wait** |
| Enter Quad Mode | 'h35 | S | n/a | 133 | init step 5 |
| Exit Quad Mode | 'hF5 | n/a | Q | 133 | not used (reset is used instead) |
| Reset Enable | 'h66 | S | Q | 133 | init steps 0 (Q) and 2 (S) |
| Reset | 'h99 | S | Q | 133 | init steps 1 (Q) and 3 (S) |
| Wrap Boundary Toggle | 'hC0 | S | Q | 133 | not used |
| Read ID | 'h9F | S cmd, S addr (24 b), 0 wait, S data | n/a | **33 MHz** | init step 4, run at SCLK ≤ 25 MHz |

\* 133 MHz at 3.0 V ±10 % and 109 MHz at 3.3 V ±10 % for Wrap-32 only; 84 MHz for linear bursts.
The R06 controller targets 10–40 MHz SCLK. It makes no claim above that.

Read ID (figure 13): after 8 command and 24 address clocks the device shifts out MF ID = **'h0D**
and KGD = **'h5D (PASS)**, with 'h55 meaning FAIL (table 3), then EID[47:0]. The datasheet allows
Read ID **only** directly after the power-up global reset (section 12, figure 12). The controller
checks for an exact positive match. Any other value, including an undriven bus, sets
`ERR_ID` and keeps the memory unavailable.

## Initialisation sequence implemented

| Step | Bus | Bytes | Why |
|---|---|---|---|
| wait | CE# high, CLK low | — | tPU ≥ 150 µs after VDD stable (section 8). The controller counts from its own reset, so the **board must guarantee VDD is stable before FPGA user mode** (see board plan). |
| 0 | QPI | 'h66 | Reset-enable in case an FPGA-only reset left the device in QPI. *ASSUMPTION:* a device in SPI mode ignores this 2-clock fragment as an incomplete command. Needs bench confirmation. |
| 1 | QPI | 'h99 | Reset (QPI form) |
| 2 | SPI | 'h66 | Reset-enable (SPI form) |
| 3 | SPI | 'h99 | Global reset; then tRST ≥ 50 ns |
| 4 | SPI | 'h9F + 24-bit addr, 2 data bytes | ID / KGD check |
| 5 | SPI | 'h35 | Enter QPI. All data traffic is QPI from here. |

## AC timing (table 10) and how the RTL meets it

| Symbol | Value | RTL mechanism | Checked by model |
|---|---|---|---|
| tCLK (linear) | ≥ 11.9 ns (84 MHz) | SCLK = mclk/(2·CLK_DIV); tested at 12.5, 20, 40 MHz | yes |
| tCLK ('h03/'h9F) | ≥ 30.3 ns (33 MHz) | init runs at `INIT_DIV` (SCLK ≤ 25 MHz) | yes |
| tCH/tCL | 0.45–0.55 tCLK | 50 % duty by construction | no (by construction) |
| tCPH | ≥ 18 ns CE# high between bursts | `GAP_CYC` = max(tCPH, tRST, one SCLK period) | yes |
| tCEM | ≤ 8 µs (std) / ≤ 3 µs (X grade) | Chunk size from a 75 % tCEM budget. A watchdog at 87.5 % aborts. Elaboration fails if one byte or Read ID cannot fit. | yes |
| tCSP | ≥ 2.5 ns CE# setup to CLK rise | CLK_DIV mclk periods from CE# fall to the first rise | yes |
| tCHD | ≥ 3 ns CE# hold after CLK rise | (1 + CE_HOLD_TICKS)·CLK_DIV mclk periods | yes |
| tSP / tHD | ≥ 2 ns | Outputs change on SCLK fall: half an SCLK period of setup and of hold (RTL zero-delay) | yes |
| tACLK | 2–5.5 ns CLK fall → data | Sampled half a period after the fall, at the mclk edge that raises SCLK | model drives at 5.0 ns |
| tKOH | ≥ 1.5 ns | not relied on | — |
| tHZ | ≤ 5.5 ns CE# high → high-Z | Next drive is ≥ tCPH later | contention monitor |
| tRST | ≥ 50 ns | In `GAP_CYC` | yes |
| tPU | ≥ 150 µs | `PU_CYC` counter | yes |
| Termination | every R/W ends with CE# high | Engine always ends in E_HOLD → CE# high | yes (tCEM) |

**Real pad delays** (T35 output/input buffer, board flight time, PSRAM tACLK) are **not** in the
zero-delay RTL simulation. At 40 MHz SCLK (12.5 ns half period) the read sample point leaves
about 12.5 − 5.5 − pad/board delay. That margin must be closed by Efinity STA with board delay
constraints, then measured. 20 MHz is the recommended first bring-up clock.

## Simulated bandwidth (RTL_SIMULATED, not hardware)

From the C1/C2/C3 runs (`R06_WORK/evidence/`): sequential 256-byte operations with no user stalls,
including chunking, commands, wait cycles and CE# gaps:

| Config | SCLK | Wire ceiling (4 bit SDR) | Simulated write | Simulated read |
|---|---|---|---|---|
| C1 | 20 MHz | 10 MB/s | ≈ 7.5 MB/s | ≈ 6.3 MB/s |
| C2 | 40 MHz | 20 MB/s | ≈ 11.8 MB/s | ≈ 8.6 MB/s |
| C3 (3 µs tCEM) | 12.5 MHz | 6.25 MB/s | ≈ 3.1 MB/s | ≈ 2.4 MB/s |

These figures include the CDC handshake and the store-and-forward buffer, but no pad timing. Use
them to rule designs out, not to promise anything. At C2 rates, moving 1 MiB takes about
**89–122 ms**: several 60 Hz frames. This confirms PASS_6_AND_7's warning that PSRAM is
working-set storage, not a frame-streaming path.
