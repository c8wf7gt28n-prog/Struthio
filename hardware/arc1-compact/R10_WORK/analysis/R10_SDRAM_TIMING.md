# R10 — 45F SDR SDRAM timing from the datasheet, read-capture window, PCB rules

Part: Alliance AS4C16M16SA (16M×16, 3.3 V LVTTL), **DOCUMENTED** values from "AS4C16M16SA-C&I 256M SDRAM" Rev 3.0
(March 2015) Table 16. Worst case of the −6 and −7 grades is used everywhere, so either grade can be fitted.
Controller: `fpga45/rtl/sdram_ctrl.sv` at 80 MHz (tCK = 12.5 ns), CL3, BL1, closed page.

## 1. Command timing (closes, with margin from the controller's state overhead)
| Parameter | Datasheet (worst) | Controller (clocks × 12.5 ns) | Margin |
|---|---|---|---|
| tCK at CL3 | ≥ 7 ns (−7) | 12.5 | 5.5 ns |
| tRCD | 21 | 2 → 25 (+1 state clock: 37.5 ns issued) | ≥ 4 ns |
| tRP | 21 | 2 → 25 | ≥ 4 ns |
| tRAS | 42 – 120 000 | ≥ 4 → 50 | 8 ns; burst ≤ 256 words = 3.2 µs ≪ 120 µs |
| tRC / tRFC | 63 | 6 → 75 | 12 ns |
| tWR / tMRD | 14 | 2 → 25 | 11 ns |
| tREFI | 7.8 µs (8192 / 64 ms) | 624 clocks = 7.8 µs; a refresh waits ≤ one 256-word burst | max gap 10.7 µs simulated; JEDEC allows postponing up to 8 |
| Init | 200 µs clock, PRE ALL, ≥ 2 AREF, MRS | 200 µs, PRE ALL, 8 AREF, MRS | — |
| tIS / tIH (command, address, data in) | 1.5 / 0.8 | sd_clk inverted: commands change ~½ period (6.25 ns) before and after the SDRAM edge | ≈ 4.7 ns / 5.4 ns before skew |
Simulation: `make sdram` with `sim/sdram_model.sv` set to these worst-case values: 0 violations; 5/5 mutants killed.

## 2. Read capture — does NOT close as built
Timeline for a READ registered at FPGA clock edge 0 (all ns, 80 MHz):
- the SDRAM samples it at its clock edge, ½ period later plus the clock path: **6.25 + t_ck_out + t_ck_pcb**;
- data at the SDRAM pins from that edge + CL·tCK + **tAC (≤ 5.4)**, held until the next edge + **tOH (≥ 2.5)**;
- data at the FPGA pad after **t_dq_pcb**; the pad register samples at FPGA edge CL+1 and needs **t_su**.

Setup condition: 6.25 + t_ck_out + t_ck_pcb + 5.4 + t_dq_pcb + t_su ≤ 12.5 → **t_ck_out + t_ck_pcb + t_dq_pcb + t_su ≤ 0.85 ns**.
An ECP5 LVCMOS33 output alone (t_ck_out) takes several ns, so this is not achievable: the read data window is
roughly [6.25 + t_ck_out + t_pcb + 5.4, 18.75 + t_ck_out + t_pcb + 2.5], about 9.6 ns wide but late.

**Implemented: phase calibration.** `sd_clk` now comes from a second output of the system PLL with dynamic
phase adjust (`rtl/arc1_sd_pll.v`, 56 steps of ≈ 223 ps per 12.5 ns — step size UNVERIFIED against the Lattice
sysCLOCK note), forwarded through an ODDR. At power-up `rtl/sdram_cal.sv` walks the phase once round the full period
for each of two capture latencies; at every step it re-initialises the SDRAM (so a mis-sampled MRS cannot persist),
writes 16 words and reads them back; it then moves to the centre of the longest passing run and the normal self test
runs. Command and read windows move together with the phase, so a pass covers both. The window width is reported in
STATUS caps [12:7].

Evidence (RTL_SIMULATED, `make sdram_corners`): the SDRAM model now applies clock / command / return delays and
checks tIS 1.5 / tIH 0.8 ns (a breached command is dropped) and drives garbage between tOH and tAC:
| Delays clk : cmd : return (ns) | Calibrated result | Same corner, fixed phase, no calibration |
|---|---|---|
| 0 : 0 : 0 | window 25 steps (5.6 ns), latency +0 — PASS | PASS |
| 4.5 : 4.5 : 1.0 | 32 steps (7.1 ns), +1 — PASS | FAIL |
| 2.0 : 2.0 : 0.5 | 19 steps (4.2 ns), +1 — PASS | FAIL |
| 6.0 : 6.0 : 1.5 | 41 steps (9.2 ns), +1 — PASS | FAIL |
| 3.0 : 5.0 : 2.5 | 41 steps (9.2 ns), +1 — PASS | FAIL |
| 5.0 : 3.0 : 0.5 | 23 steps (5.1 ns), +1 — PASS | FAIL |
The delay values are PLANNING brackets, not ECP5 datasheet figures; the smallest window (4.2 ns ≈ ±2.1 ns around
the chosen phase) is the margin left for temperature/voltage drift after calibration. Still CONDITIONAL on silicon:
PLL phase-step semantics, real I/O delays, and drift over temperature (re-calibration hook: `reinit` + sweep).

ECP5 I/O timing (t_ck_out, t_su for LVCMOS33 SDR registers) must come from the ECP5 datasheet DS-02012 external
switching tables and the routed design's timing report; not taken here.

## 3. PCB requirements (derived from the budget above)
- All SDRAM signals (CLK, 16 DQ, 2 DQM, 13 A, 2 BA, CS#, RAS#, CAS#, WE#, CKE) on one layer pair with an unbroken
  ground reference; 45F banks 2/3 face the SDRAM (pin plan `hardware/R10_flash_pinmux.csv`).
- Length match: address/command/control to CLK within ±10 mm, DQ/DQM to CLK within ±10 mm (≈ ±65 ps at
  ~6.5 ps/mm, PLANNING value for FR-4) — small against the ±4.7 ns command window; the read window is set by the
  calibrated capture phase, so absolute length matters less than DQ-to-DQ skew: **DQ group within ±5 mm**.
- Total flight CLK + DQ ≤ 100 mm (≈ 0.65 ns) keeps the calibrated phase inside the PLL's range with margin.
- 22–33 Ω series termination at the FPGA on CLK and address/command. DQ termination (series at one or both ends)
  is a signal-integrity choice to make with IBIS models — NOT_RUN.
- Decoupling per the SDRAM datasheet pin list (VDD/VDDQ pairs), 3.3 V shared with 45F banks 2/3.
These are planning rules for the schematic/layout pass, not verified by SI simulation (NOT_RUN).
