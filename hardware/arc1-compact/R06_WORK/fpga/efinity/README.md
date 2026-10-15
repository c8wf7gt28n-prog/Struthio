# T35F400C3 Efinity project skeleton (R06)

**Status: NATIVE_EDA_NOT_RUN.** Efinity is proprietary and is not installed in the environment
that produced R06. This directory contains no synthesis, fit, timing or bitstream report, and none
may be inferred. Everything below is input data plus the exact steps for a machine that has
Efinity.

| File | Content | Status |
|---|---|---|
| `arc1_t35_r06_pins.csv` | top-level port → ball/bank/IO standard, generated from `../../board/r06_board_plan.json` | SELECTED_UNVERIFIED |
| `arc1_t35_r06_isf.py` | Interface Designer Python API script, generated | **UNVALIDATED**: never executed; check API names against your Efinity version |
| `arc1_t35_r06.sdc` | clocks, CDC groups, PSRAM I/O budgets (placeholder board delays) | DRAFT |
| `gen_efinity_inputs.py` | regenerates the CSV and the script from the board plan | HOST_TESTED (runs) |

## RTL file list (top: `arc1_t35_top`)

```
../top/arc1_t35_top.sv
../mailbox/rtl/mbx_spi_slave.sv ../mailbox/rtl/mbx_regs.sv
../mailbox/rtl/mbx_loopback.sv  ../mailbox/rtl/psram_bist.sv
../psram/rtl/psram_user_port.sv ../psram/rtl/psram_qspi_core.sv
```
Language: SystemVerilog (the subset accepted by Icarus 12, Verilator 5.020 and Yosys 0.33).

## Steps on an Efinity workstation (record the exact version used)

1. Create a project: family **Trion**, device **T35F400C3**, top `arc1_t35_top`, and add the RTL above.
2. Interface Designer: build the GPIO from `arc1_t35_r06_pins.csv` (or adapt and run
   `arc1_t35_r06_isf.py`). Set every bank to 3.3 V. Make `t35_miso` and `t35_irq_n` GPIO
   outputs with an output enable. `t35_irq_n` must be driven low only when the OE is set
   (open-drain emulation). Make `psram_sio[3:0]` inout, registered I/O if possible.
3. PLL: input `osc_25m` (GPIOL_66_CLK0, D20). Outputs `sys_clk` 80 MHz and `psram_mclk`
   40 MHz, plus `pll_locked`. Check the PLL's legal multiplier range in the T35 data sheet PLL
   tables before choosing a 25 MHz reference.
4. Add `arc1_t35_r06.sdc`. Replace the placeholder board delays once a layout exists.
5. Run the full compile (GUI, or `efx_run.py` with the project file; confirm the CLI flags with
   `efx_run.py --help` in your installed version).
6. Archive the synthesis utilisation, place-and-route, timing (all corners) and IO reports, plus
   the tool version, under `R06_WORK/evidence/efinity_<date>/`. Report what passed and what
   failed. Only then may anything be labelled **NATIVE_EDA_VERIFIED**.

## Open-source estimate (not Efinity)

Yosys 0.33 `synth_efinix` maps the whole top level to approximately **1272 EFX_LUT4, 836 EFX_FF,
50 EFX_RAM_5K, 768 EFX_ADD** (`make -C ../top synth-efx`). The two 8 KiB mailbox buffers account
for most of the RAM blocks. This is a sanity estimate of size only: no placement, no timing, and
the result may differ from Efinity's mapping.
