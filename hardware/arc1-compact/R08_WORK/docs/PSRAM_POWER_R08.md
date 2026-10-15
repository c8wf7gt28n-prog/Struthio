# PSRAM power, start-up levels and brown-out (R08: closes R07 RK-PSRAM-VOH / RK-PSRAM-PU by design, and RK-PSRAM-BROWNOUT in RTL)

## 1. Why R07's network had to change

R07 used permanent 2.2 kΩ pull-downs so that SCLK/SIO stayed low against the T35's 27 kΩ (min) configuration-time
pull-ups during the PSRAM's VDD ramp. In operation, though, the PSRAM had to source **1.63 mA** into each pull-down,
while APS6404L specifies VOH only at **0.2 mA** (DS Rev 2.7 Table 9). R07 rejected a switched PSRAM supply because the
pulled-up T35 pins would back-power an unpowered PSRAM.

## 2. R08 circuit (native schematic sheets `psram`, `power`, `t35`)

1. **The PSRAM is never powered while the T35 is unconfigured.**
   - PSRAM_VDD comes from load switch U12 (TPS22918) on 3V3_T35.
   - ON = U13 AND(F133 PSRAM_PWR_REQ, CDONE_DLY).
   - CDONE_DLY is T35 CDONE delayed by an RC of about 2 ms, through a Schmitt buffer U20. A diode with 470 Ω discharges it quickly when CDONE falls.
   - So power can only appear more than 25 µs (tUSER) after configuration is complete: about 0.96 ms worst case (CONDITIONAL on the LVC1G17 VT+ value).
2. **While the T35 is unconfigured** (CDONE_DLY low), an SN74LVC07A (U26, Ioff) pulls CE#, SCLK and SIO0–3 to ground through 1.5 kΩ each.
   - Worst-case level against the 27 kΩ weak pull-up at 3.40 V: **0.368 V**.
   - That is ≤ VDD + 0.4 V with VDD = 0, so there is no back-power, and it is ≤ VIL 0.4 V.
3. **In user mode** the switched pull-downs are released. Only 100 kΩ static pull-downs remain: **0.034 mA** of load, inside the 0.2 mA VOH test condition.
4. **CE# is pulled up to PSRAM_VDD itself**, and the T35 releases its CE# pad while the guard is OFF. During the ramp CE# therefore equals VDD exactly; with the R07 pull-up to 3V3 it could only approximate VDD.
5. **U14 TPS3808G30** monitors PSRAM_VDD (2.748–2.832 V, above the 2.7 V minimum) and drives PSRAM_PG to the T35 (J17) and to the F133 (PE11).

## 3. RTL: `fpga/rtl/psram_power_guard.sv` (new; the R06 controller RTL is unchanged)

| State | Pads | Controller |
|---|---|---|
| OFF (PG low, or EN low, or PG high for < 64 mclk) | CE# released (pull-up to the switched rail); SCLK low; SIO driven low | held in reset (memory-side reset of `psram_user_port`) |
| ON | follow the controller | runs its own tPU (150 µs), then RSTEN/RST, Read ID and QPI entry |

- **Fall to OFF:** any low synchronised sample of PG or EN causes it in the same clock.
- **Effect on the user:** the in-flight request ends with CORE_FAULT.
- **Mailbox AMBX v2:**
  - STATUS b11 POWER_ON and b12 POWER_LOST (sticky);
  - READY is withheld until the host clears POWER_LOST;
  - EPOCH counts power-ups.
- **F133 contract:** after POWER_LOST, PSRAM content is unknown. The host must reload assets (or run BIST first) before clearing the flag.

## 4. Evidence (RTL_SIMULATED, `fpga/Makefile sim`, tb_top_r08)

| Scenario | Result |
|---|---|
| All R06 top-level tests: identity, buffers, CS# abort, 5 R05 golden frames, doorbell rules, BIST pass/fault, recover, FPGA reset | PASS |
| P0: PSRAM unpowered at start | no pad high while VDD is off; not ready |
| P1: controlled power-up | 0 tPU pin-state violations (CE# = VDD, CLK low, SIO low for 150 µs); EPOCH = 1 |
| P2: commanded power-off during BIST (EN falls first) | BIST fails (never passes across a loss); POWER_LOST sticky; READY withheld until CLEAR; 0 back-power events while EN is low; BIST passes again after re-power |
| P3: 1-clock PG glitch | treated as a full loss; EPOCH increments |
| P4: unannounced rail loss with EN high (load-switch fault) | detected through PG. **Measured back-power window before detection: ≈ 1.2 µs** (the T35 still drives CE# high during the assumed 2 µs supervisor response). Residual risk RK-PSRAM-FAULT-BP, P2 |

Model protocol violations before P2: 0. The model flags accesses to an unpowered or uninitialised device during the
deliberate power cuts, and those are expected.

## 5. Still open

- No analog simulation of the ramp.
- The VOL of the 74LVC07 at 0.12 mA is the 100 µA datasheet figure (0.2 V); the 4 mA value at 3.3 V is NOT_FOUND.
- The supervisor response time was assumed to be 2 µs; check it in the TPS3808 datasheet in R09.
- Bench steps C2/C3 of the bring-up plan remain (class E).
