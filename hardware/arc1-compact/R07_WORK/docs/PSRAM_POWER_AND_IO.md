# APS6404L power-up, DC margins and controller fault behaviour (R07)

Evidence: **PLANNING_CALCULATED** (`R07_WORK/analysis/psram_power_io.py`, datasheet limits
plus resistor tolerance plus leakage) and **RTL_SIMULATED** (`R07_WORK/fpga/psram_r07/`). This is
not an analog simulation and not a measurement.

## 1. Requirement (APS6404L-3SQR DS Rev 2.7 §8, re-checked at the source)

From the start of the VDD ramp until ≥ 150 µs after VDD ≥ VDDmin: **CE# HIGH (tracking VDD
within 200 mV), CLK LOW, SI/SO/SIO[3:0] LOW**. Then a RESET operation (RSTEN 'h66 + RST 'h99)
and tRST ≥ 50 ns. The R07 handoff quotes this correctly. RTL simulation cannot validate it,
because it is an analog condition during the ramp.

## 2. Conflict and plan

While configuring (and, in R07, while held in CRESET_N), every Trion GPIO is weak pull-up,
27–65 kΩ at 3.3 V (T35 DS Table 69). Board plan: **2.2 kΩ pull-downs on SCLK and SIO0–3** and a
**10 kΩ pull-up on CE#**, all on the shared 3V3 rail (3.20–3.40 V in R07).

## 3. Worst-case DC results (`psram_power_io.py`, 5 % resistors)

| Check | Result | Limit | Status |
|---|---|---|---|
| SCLK/SIO level, T35 pull-up 27 kΩ min to 3.40 V, 2.2 kΩ +5 %, +11 µA leakage (T35 10 µA, PSRAM 1 µA) | **0.291 V** | ≤ VIL 0.4 V | PASS (0.109 V margin) |
| CE# droop below VDD from leakage through 10 kΩ +5 % | **0.116 V** | ≤ 0.2 V | PASS |
| T35 current into each pull-down when driving high | **1.63 mA** | ≪ 14.4 mA (Table 68, drive 1, 25 °C) | PASS |
| PSRAM VOH while sourcing the pull-down | 1.63 mA load | VOH specified **only at 0.2 mA** | **OPEN**: vendor question Q6 |
| PSRAM VOH estimate (0.8·VDD at 3.20 V − I × 50 Ω, ASSUMPTION) vs T35 VIH 2.0 V | +0.479 V | ≥ 0 | PASS on assumption |
| T35 → PSRAM high / low (same rail) | +0.200 / +0.200 V | ≥ 0 | PASS |
| PSRAM → T35 low (0.2·VDD vs 0.8 V) | +0.160 V @3.20, **+0.120 V @3.40** | ≥ 0 | PASS (thin) |
| PSRAM → T35 high | +0.56 / +0.72 V | ≥ 0 | PASS |

The R06 report gave +0.106 V for the PSRAM→T35 low margin at the old 3.47 V rail limit. With
the R07 rail (3.40 V max), the figure is +0.120 V. Both numbers are datasheet-limit
arithmetic. Neither includes ground bounce or the pull-down's effect on edges.

**Not covered by DC arithmetic (needs SI simulation or bench):** rise/fall time with the
2.2 kΩ + ≤ 15 pF load at the chosen SCLK; undershoot/overshoot (DS §16.2 allows −1.0/+1.0 V
for 20 ns); ESD; the ramp itself (CE# tracking during a real regulator ramp).

**Alternatives considered:** (a) a PSRAM VDD load switch after T35 configuration was rejected,
because pulled-up T35 pins would back-power an unpowered PSRAM beyond VT ≤ VDD + 0.4 V.
(b) Weaker pull-downs: 3.3 kΩ gives 0.40–0.42 V worst case, which fails. (c) A buffer with
power-off isolation adds a part and delay; keep it in reserve if Q6 comes back negative.

## 4. Controller behaviour under faults (RTL_SIMULATED, unchanged R06 RTL)

| Scenario | Result | Bench |
|---|---|---|
| R1 dead chip at first power-up | `ERR_ID` (MF/KGD read 0x00 via pull-downs); requests refused; **no data command issued**; recovers after `recover` | `tb_psram_r07` |
| R2 KGD = FAIL at init | `ERR_ID`; recovers | `tb_psram_r07` |
| **R3 PSRAM VDD interruption while T35 runs** | **Not detected.** Status OK, `ram_ready` stays 1, 255/256 bytes wrong; the model flags 592 protocol violations (access to an un-reset device). After ≥ 150 µs and `recover`, operation is correct. | `tb_psram_r07` |
| Clock-ratio variation | C4 (66.67 MHz/27 MHz), C5 (100 MHz ÷ 3 / 75 MHz): 0 errors, 0 violations | R06 bench, new parameters |
| Reset in transfer, watchdog, user timeout, contention, tCEM, page split | Carried over: R06 C1–C3 rerun in the R07 regression | R06 suite |

**Mitigation for R3** (risk RK-PSRAM-BROWNOUT): (1) PSRAM VDD stays on the same 3V3 rail as
T35 VCCIO, as planned. (2) A 3V3 supply supervisor drives F133 RESET, and through the F133 the
T35 CRESET_N, so any rail dip resets everything. (3) Host-level canary: the F133 job layer
reads a known pattern through the BIST path before trusting PSRAM after any unexplained FPGA
or host event. None of these is implemented in RTL yet.
