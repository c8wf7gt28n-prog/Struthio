# Running the native Efinity flow for the R08 T35 design (owner PC; Efinity could not run in this environment)

Efinity is licensed per user from the Efinix Support Center (https://www.efinixinc.com/support/). Do not send a
license or password to an agent. The files here are **GENERATED and never opened in Efinity** (NATIVE_EDA_NOT_RUN).
Expect Efinity to rewrite them on first save, and archive both versions.

## Files

| File | Purpose |
|---|---|
| `arc1_t35_r08.xml` | project: device T35F400, timing model C3, top `arc1_t35_top_r08`, 8 RTL files (relative paths), SDC, bitstream active x1 |
| `arc1_t35_r08_isf.py` | Interface Designer script (DesignAPI): bank voltages, 17 GPIO with ball, pull and drive, PLL_BL0 from 25 MHz on R16 |
| `arc1_t35_r08.isf` | the same calls as a plain .isf (GUI: Interface Designer → File → Import GPIO / ISF) |
| `arc1_t35_r08.sdc` | clocks (osc_25m 40 ns; sys_clk 12.5 ns; psram_mclk 25 ns), asynchronous groups, PSRAM I/O budgets, false paths for synchronised inputs |
| `arc1_t35_r08_pins.csv` | ports / balls / resources / banks / nets (cross-checked with the schematic and RTL by the R08 runner) |

## Linux (Ubuntu 22.04/24.04 per Efinity release notes)

```bash
cd R08_WORK/fpga/efinity
source <EFINITY_INSTALL>/bin/setup.sh            # sets EFXPT_HOME etc.
efx_run.py --version > efinity_version.txt
python3 arc1_t35_r08_isf.py | tee isf.log        # creates arc1_t35_r08.peri.xml; prints check_design: True/False
efx_run.py arc1_t35_r08.xml --flow compile 2>&1 | tee compile.log
#   or step by step: --flow map | --flow interface | --flow pnr | --flow pgm
```

On Windows, use `efx_run_pt_script.bat arc1_t35_r08_isf.py`, then `efx_run.bat arc1_t35_r08.xml --flow compile`, or the GUI:
1. File → Open Project → arc1_t35_r08.xml.
2. Interface Designer → import the .isf.
3. Check Design.
4. Generate Efinity Constraint Files.
5. Run Synthesis, Place, Route, Timing and Bitstream.

## Expected first-run issues (fix in the source generator, not by hand)

1. `auto_calc_pll_clock` is used for 80/40 MHz from 25 MHz. If Efinity rejects it, set M/N/O manually within FPFD 10–100 MHz and FVCO 500–1600 MHz (T35 DS Tables 15/90). Then rename the PLL outputs to `sys_clk`, `psram_mclk`, `pll_locked`.
2. `def_veri_version="sv_09"` is assumed for SystemVerilog. If rejected, choose SystemVerilog 2009 in the project editor.
3. The inout naming (`<name>_IN/_OUT/_OE`) matches the RTL. Unused `*_IN` ports are intentional.

## Archive into `R08_WORK/fpga/efinity/native_run_<date>/` (all required before anyone says NATIVE_EDA_VERIFIED)

- `efinity_version.txt`, `isf.log`, `compile.log`
- `outflow/*.timing.rpt` (setup/hold slack for all clocks)
- `outflow/*.place.rpt`, `outflow/*.route.rpt`, `outflow/*.res.csv` (resources)
- `outflow/*.pinout.rpt` / `*.pinout.csv`, compared against `arc1_t35_r08_pins.csv` (run `python3 ../../cad/check/crosscheck_r08.py`)
- `*.hex` / `*.bit` + SHA-256
- the regenerated `*.peri.xml` / `*.pt.sdc`

Then fill in `NATIVE_FIT_TIMING_REPORTS_OR_NOT_RUN.md` with the real numbers (WNS/TNS, LUT/FF/RAM usage) and
re-run `python3 R08_WORK/tools/run_r08_checks.py`.
