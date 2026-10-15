# ARC-1 Compact: PASS 7 (R07) status

Date 2026-10-15. Evidence run `evidence/run_20261015T032803Z/summary.json`:
**PASS_R07_HOST_RTL_PLANNING_BUILD_CHECKS**, 16 steps pass, 0 fail, 6 NOT_RUN.

> **No fabrication approval.** Nothing in R07 ran on silicon or in Efinity. No display has been
> lit, no PSRAM has been tested on hardware, and no timing, power or FPS figure has been
> measured. The next authorised stage is the bench plan (`docs/BENCH_BRINGUP_PLAN.md`) and
> schematic capture, not a JLCPCB order.

## 1. Outcome against the R07 handoff's ordered instruction

| # | Handoff item | Result | Level |
|---|---|---|---|
| 1 | Repair/justify BT820 high-address writes | **Fixed.** R06 refused every write ≥ 0x7F000000, which blocked the FIFO, registers and display list. R07 validates against the AN086 memory map; byte-exact wire tests; probe reproduces the R06 defect; 4 mutants killed. Disambiguation from host commands is documented (second byte 0xE0–0xEB vs 0x00/0x01/0x80; 5 bytes vs ≥ 8) and matches Bridgetek's reference driver. Silicon decode is still a bench/vendor item. | HOST-TESTED + MANUFACTURER-DOCUMENTED |
| 2 | F133 BOOT-SEL / eFuse / reset | Table found in the **D1-H UM** (the F133 UM mirror has an expired certificate). Straps defined as **11** (SD first). The T35 is held in CRESET_N so it cannot touch the straps. eFuse/Fast-Boot are read out by the boot image. | PLANNING-CALCULATED + ASSUMPTION (F133 = D1-H BROM) |
| 3 | MN820 VCC3V3 direction | **Resolved from the VM820C v1.1 reference schematic: the host supplies the module.** Written confirmation is still requested. New finding: module VOH 2.4 V forces a 3V3 rail of 3.20–3.40 V. | MANUFACTURER-DOCUMENTED |
| 4 | PSRAM startup and I/O margins | Worst case 0.291 V ≤ 0.4 V during power-up, CE# droop 0.116 V, logic margins ≥ +0.12 V. **OPEN:** PSRAM VOH is specified only at 0.2 mA. **New limitation found:** a PSRAM power loss goes undetected by the controller. | PLANNING-CALCULATED + RTL-SIMULATED |
| 5 | Native Efinity fit/STA | **NATIVE_EDA_NOT_RUN** (tool not available). | NOT_RUN |
| 6 | F133 boot image + graphics demo | Bare-metal eGON image (UART banner, boot-select readout, BT820 boot + scan-out + test frame from the host-tested driver). Reproducible, header-checked. **Never executed.** | BUILD-ONLY |
| 7 | Rerun regression + fault tests | Full R06 suite (incl. R05 rerun, PSRAM C1–C3, mutants, top level) PASS in a scratch copy. R07 firmware 266 checks + ASan/UBSan + mutants. PSRAM R1–R3 + C4/C5. | HOST-TESTED / RTL-SIMULATED |

## 2. Commands and results (final run; all from `hardware/arc1-compact/`)

`python3 R07_WORK/tools/run_r07_checks.py` → exit 0. Each step log has its exact command and exit.

| Step | Command (cwd) | Result |
|---|---|---|
| handoff_integrity | manifest SHA-256 of 141 handoff files | 0 changed |
| r06_regression_full | `python3 R06_WORK/tools/run_r06_checks.py` (scratch copy) | PASS (18/18, 5 NOT_RUN as in R06) |
| fw_test / fw_sanitize / fw_freestanding | `make test|sanitize|freestanding` (R07_WORK/firmware) | 266 checks, 0 failures; clean |
| fw_mutants | `make mutants` | 4/4 killed (map check, endianness, config-while-active, FIFO wrap) |
| fw_r06_defect_probe | `make r06-probe` | R06 defect reproduced |
| board_unit_tests / board_plan_check | `python3 -m unittest …`, `check_board_plan.py` (R07_WORK/board) | 25 tests OK; 396 rules PASS |
| psram_power_io | `python3 psram_power_io.py` (R07_WORK/analysis) | 13 PASS, 1 OPEN |
| psram_r07_scenarios / psram_extra_clocks | `make r07|extra-clocks` (R07_WORK/fpga/psram_r07) | R1–R3 PASS; C4, C5 PASS with 0 violations |
| f133_image_build ×2 | `make` (R07_WORK/f133_boot) | EGON_OK; identical SHA-256 `9467622f…532b0b` |
| evidence_ledger_schema | ledger validation | 20 entries valid |

Tools: GCC 13.3 (host), riscv64-unknown-elf-gcc 13.2.0, mkimage 2025.10, Icarus 12.0,
Verilator 5.020, Yosys 0.33, Python 3.13. Efinity not found.

## 3. Handoff claims checked at the source

All checked citations match except these, now corrected or annotated:
* "F133 User Manual §3.4.2.1": the same table content sits at **§3.3.2.1 of the D1-H UM**;
  the F133 document itself could not be retrieved.
* "T35 DS tables 98–99": in DS v3.2 the relevant tables are 12, 59, 66–69 (vendor Q8).
* "Read REG_ID (0x7C)": correct, but the BT820B-specific identity is REG_CHIP_ID = 0x08200100
  (AN086 Table 6). Both are checked.
* "R06 851 LUT4/470 FF/2 RAM_5K": that is the PSRAM-only estimate. The R06 top level was
  ~1272/836/50 (still open-source Yosys, not Efinity). The handoff is right that neither is a
  timing result.
* "+0.106 V low margin": correct at the R06 rail; it becomes +0.120 V at the R07 rail.

## 4. Unresolved blockers (owner and next step in `RISK_REGISTER.md`)

P0: silicon confirmation of BT820 0xFF-prefixed writes (Q2/B1.4); written MN820 power answer
(Q1); straps and eFuse on a real F133 (A1/A2). P1: native Efinity (owner licence); PSRAM VOH
under pull-down load (Q6); PSRAM brown-out detection (supervisor + canary); module VOH margin
+0.02 V (B1.3); F133 image execution. P2: FEL recovery, quad SPI, panel timing, audio, PCB.

## 5. Assumptions in force

F133 BROM and peripherals = D1-H UM. The microSD boot0 sits at sector 16. The CPU clock after
BROM is ≤ 1.2 GHz (delays only get longer otherwise). A QPI reset fragment is harmless in SPI
mode. PSRAM VOH at about 1.6 mA is ≥ 0.8·VDD − 80 mV. The R05 panel timing interpretation
holds. Each assumption is tagged ASSUMPTION in the ledger.
