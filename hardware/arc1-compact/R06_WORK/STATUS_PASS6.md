# ARC-1 Compact: PASS 6 (R06) status report

Date 2026-10-15. Evidence run: `evidence/run_20261015T015312Z/` (`summary.json`). Overall:
**PASS_R06_HOST_RTL_PLANNING_CHECKS**, with 18 steps executed, 0 failed and 5 NOT_RUN.

Nothing in this pass ran on hardware or in Efinity. No claim is made of a working PSRAM, a working
BT820 display, electrical compatibility, FPGA fit or timing, a PCB, or any FPS figure.

## 1. Status table

| # | PASS_6 item | Artifact | Result | Evidence label |
|---|---|---|---|---|
| 1 | Baseline hashes and tests | `tools/run_r06_checks.py` (handoff manifest check + R05 rerun in a scratch copy) | 141/141 handoff files unchanged; R05 `check_package` PASS; R05 `check_all` **PASS_HOST_AND_RTL_SIMULATION** (with Icarus) | HOST_TESTED / RTL_SIMULATED (rerun of R05) |
| 2 | F133 pin/boot/storage mux, BT820 host mode, voltages | `board/r06_board_plan.json`, `board/check_board_plan.py`, `board/PIN_MAP_R06.md` | 391 rules PASS; 19 checker tests, which show every rule family rejects a broken plan | PLANNING_CALCULATED |
| 3 | Board architecture, rails, bank plan, reset graph | `docs/ARCHITECTURE_R06.md`, `docs/AUDIO_R06.md` | Written. F133→BT820 path proven T35-free by checker rule | SELECTED_UNVERIFIED |
| 4 | PSRAM datasheet → traceable command/timing table | `fpga/psram/PSRAM_TIMING_TABLE.md`, `docs/SOURCES_R06.json` | Rev. 2.7 datasheet, SHA-256 recorded; Read ID values taken from figure 13 | MANUFACTURER_DOCUMENTED |
| 5 | Synthesizable PSRAM controller, model, testbench | `fpga/psram/` | 3 clock configs PASS (SCLK 20 / 40 / 12.5 MHz; uclk faster, slower, 2.5×; tCEM 8 µs and 3 µs). 0 scoreboard errors, 0 model timing violations, 0 bus contention. 4/4 mutants killed. Verilator lint clean; Yosys synth clean | RTL_SIMULATED; OPEN_SOURCE_SYNTH_ESTIMATE |
| 6 | Exact-device T35F400C3 Efinity skeleton | `fpga/efinity/`, `fpga/top/`, `fpga/mailbox/` | Pin CSV, ISF script (unvalidated), SDC, steps. The top level (mailbox + PSRAM + BIST) passes the system testbench. `synth_efinix` estimate: ~1272 LUT4, 836 FF, 50 RAM_5K | **NATIVE_EDA_NOT_RUN**; RTL_SIMULATED |
| 7 | Preserve R05 ABI; rerun its tests | R05 sources compiled unmodified by path in `firmware/`; R05 golden frames sent through the RTL mailbox byte-exact | R05 checks PASS; 5 golden frames (24–4120 B) unchanged | HOST_TESTED / RTL_SIMULATED |
| + | Independent CPU→BT820 path with FPGA fallback | `firmware/` | 231 checks PASS (also under ASan/UBSan). BT820 command stream identical with no FPGA, a healthy FPGA, and 8 fault modes | HOST_TESTED (mocks) |

## 2. Exact commands and exit statuses (final run)

All commands run from `hardware/arc1-compact/` through `python3 R06_WORK/tools/run_r06_checks.py`,
which exited **0**. Each step's log, with the command line and exit status, is in the run
directory.

| Step | Command (cwd) | Exit |
|---|---|---|
| r05_check_package | `python3 tools/check_package.py` (scratch copy of R05_BASELINE) | 0 |
| r05_check_all | `python3 tools/check_all.py` (scratch copy) | 0 |
| board_unit_tests | `python3 -m unittest discover -s tests -v` (R06_WORK/board) | 0 |
| board_plan_check | `python3 check_board_plan.py --report … --pinmap PIN_MAP_R06.md` | 0 |
| psram_lint / sim / synth / synth-efx / mutants | `make <target> OUT=<tmp>` (R06_WORK/fpga/psram) | 0 / 0 / 0 / 0 / 0 |
| top_lint / sim / synth-efx | `make <target> OUT=<tmp>` (R06_WORK/fpga/top) | 0 / 0 / 0 |
| efinity_inputs_generate | `python3 gen_efinity_inputs.py <tmp>` + byte comparison with committed files | 0, identical |
| firmware_test / sanitize / freestanding | `make <target> OUT=<tmp>` (R06_WORK/firmware) | 0 / 0 / 0 |

Tool versions: Python 3.13.16, GCC 13.3.0, GNU Make 4.3, Icarus Verilog 12.0, Verilator 5.020,
Yosys 0.33, Efinity **not found**.

## 3. Failed / unavailable checks

| Check | Status | Reason |
|---|---|---|
| Efinity synthesis, fit, STA, bitstream for T35F400C3 | NOT_RUN | Proprietary tool not installed; exact steps are in `fpga/efinity/README.md` |
| F133 cross-build / BSP / boot image | NOT_RUN | No toolchain or SDK in this environment |
| BT820/MN820 on silicon, display output | NOT_RUN | No hardware; BRT_AN_086 not read |
| PSRAM and T35 on silicon | NOT_RUN | No board |
| Schematic, PCB, SI/PI, thermal, JLCPCB DFM | NOT_RUN | Out of R06 reach |
| LeakSanitizer | disabled | Same policy as R05 (`detect_leaks=0`) |
| Mouser datasheet URL from the handoff | NOT_RETRIEVED | Bot-check page. AP Memory's own Rev. 2.7 was used instead |

## 4. Blockers and findings (concrete)

1. **BOOT-SEL on SPI0 (PC4/PC5): BLOCKED.** SPI0 is the only bonded SPI left for the T35. Its
   MOSI and MISO pins are also F133 BOOT-SEL0/1, and the encoding is not in the F133 datasheet.
   T35 MISO tri-states while SS_N is high, and PC3 has a 15 kΩ reset pull-up. Strap values wait
   on the F133 user manual.
2. **eMMC boot is impossible** with this split, because SMHC2 shares PC2–PC7 with SPI0. Boot must
   be microSD on SMHC0 (PF0–PF5), with UART0 debug moved to PE2/PE3.
3. **The SPI1 alternate pins on PB8–PB12 do not exist on the eLQFP128 F133**, which bonds PB2–PB7
   only. The BT820 link must use PD10–PD15.
4. **BT820 quad mode is unconfirmed on the F133.** The F133 datasheet lists Quad-Output/Input,
   not Quad-IO, while BT820 quad needs a quad address phase. **Baseline: single channel**
   (≤ 60 MHz per the BT820, F133 limit unmeasured).
5. **PSRAM power-up versus T35 configuration pull-ups (found in R06).** The PSRAM needs CLK and SIO
   low during tPU, but Trion GPIOs pull up while configuring. Mitigation in the plan: 2.2 kΩ
   pull-downs (≤ 0.261 V computed) and a 10 kΩ CE# pull-up. The load and SI cost needs review.
6. **BT820 0xFF prefix ambiguity.** A write to ≥ 0x7F000000 starts with the host-command byte
   0xFF. The library refuses such writes until BRT_AN_086 is reviewed.
7. **MN820 datasheet wording conflict** about whether CN1 VCC3V3 is an input or an output.
8. **PSRAM → T35 low-level margin** is only +0.106 V on datasheet limits, so it must be measured.

No stop condition from ENGINEERING_CHANGE_R06 §5 was hit. A legal draft pin and voltage map
exists, and the command protocols are compatible as documented. Timing closure and BSP support
remain unproven, not disproven.

## 5. Assumptions (each one marked at the point of use)

* A QPI-format reset sent to a PSRAM that is in SPI mode is ignored. The datasheet doesn't say.
* F133 SPI1 WP carries IO2 and HOLD carries IO3. This is convention, not stated in the datasheet.
* BT820 32-bit data is little-endian. BRT_AN_086 has not been read.
* The board keeps PSRAM VDD stable before T35 user mode starts.
* 25 MHz T35 reference oscillator, 80/40 MHz PLL outputs. These are SELECTED, not checked
  against the PLL tables.
* Simulated PSRAM bandwidth (≈ 7.5/6.3 MB/s at 20 MHz, ≈ 11.8/8.6 MB/s at 40 MHz) excludes pad
  and board delays.

## 6. Exit gate (PASS_6_AND_7 "R06 exit gate")

| Gate item | State |
|---|---|
| Honest artifact inventory + pass/fail simulation | **met** (sections 1–3, `evidence/`) |
| Legal draft pin/voltage map | **met as a draft**: machine-checked against package, mux and DC tables. The boot strap value is blocked (item 4.1) |
| Device-specific Efinity results where available | **not available**: NATIVE_EDA_NOT_RUN, with steps provided |
| PSRAM procurement candidate | **met**: APS6404L-3SQR-SN, Mouser 878-APS6404L-3SQR-SN; stock, price and lifecycle **not checked** |
| No claim of working 8 MiB hardware | **held** |

## 7. Next tests

In order: U1–U4 in `docs/PASS7_PLAN.md` (F133 manual, BRT_AN_086, an Efinity run, MN820 power
pin). Then the BT820 chip-ID read over F133 SPI1 with a logic-analyser capture. Then PSRAM BIST on
a real T35 at 10 and 20 MHz. Then the bench repeat of the fallback matrix with a live BT820 test
pattern. Then the synthetic CPU-versus-offload frame budget.
