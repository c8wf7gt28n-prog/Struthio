# ARC-1 Compact: PASS 8 (R08) status: **HOLD / PARTIAL**

Date 2026-10-15. Authority: R08 handoff (CLAUDE_R08_AUTHORITY.md) plus the **corrective handoff v1.0** (NOR-first
boot, SD games only, USB device-only, LCD deferred). The latter was received mid-pass and integrated without restarting.

> **Not approved for fabrication. Nothing has been tested on hardware.** R08 produced native engineering sources
> (KiCad 9 schematic + ERC + netlist, an importable Efinity project, RTL, firmware) and calculations. P0 items remain
> open (NOR-boot facts, native Efinity, MN820 supply confirmation, layout, USB power budget), so the status is
> HOLD/PARTIAL, not READY FOR FAB. No confidence percentage is claimed.

Runner: `python3 R08_WORK/tools/run_r08_checks.py` (from `hardware/arc1-compact/`). Latest evidence: `R08_WORK/evidence/LATEST.txt`.
Result **PASS_R08_HOST_RTL_NATIVE_KICAD_CHECKS: 30 pass, 0 fail, 7 NOT_RUN**. This includes the full R07 regression
(16 pass, 0 fail, 6 NOT_RUN, with the R06 suite nested) run in a scratch copy.

## 1. Acceptance gates (ACCEPTANCE_GATES.md)

| Gate | Result | Basis |
|---|---|---|
| G1 regressions + sources unmodified | **PASS** | root manifest (142 entries, R06 README exempt as in R07), `git diff` vs 1262c1a for R05/R06/R07 = 0, R07+R06 regression PASS in a scratch copy, pre-change baseline archived (`evidence/r07_baseline_prechange/`) |
| G2 native multi-sheet KiCad + ERC/netlist; exact MPNs | **PARTIAL** | 9 sheets, 329 parts, **kicad-cli 9.0.9 ERC 0 errors / 0 warnings**, netlist + PDF. MPNs are exact where chosen; remaining lines are explicitly `TBD` (crystal, oscillator, LED, PTC, generic passives). None is fabricated |
| G3 importable Efinity project | **PARTIAL: R08-T35-NATIVE = NOT_RUN** | project XML, ISF and SDC generated from the schematic and cross-checked with RTL. **Owner must run Efinity before the PCB pin freeze** (`fpga/efinity/RUN_EFINITY_LOCALLY.md`) |
| G4 interconnect matrix, domains, inactive/boot states | **PASS** (documentary) | `docs/INTERCONNECT_MATRIX_R08.md` (65 nets, generated), `docs/PIN_TABLE_R08.md`, `docs/BOOT_TRACE_DOSSIER.md` §3; LVDS mapping in `docs/PANEL_INTERFACE_R09.md` |
| G5 P0 voltage/boot risks: remedial circuits + worst-case calc | **PARTIAL → HOLD** | MN820 VOH and PSRAM VOH/PU/brownout are closed by circuit + calc (+ RTL). NOR-boot BROM facts and the MN820 supply are still VENDOR_OPEN; RK-NOR-VOH OPEN; RK-3V3-SUP FAIL |
| G6 power tree, sequencing, back-power, PG supervision, access points | **PASS** (design) | three supervisors, PG-chained T35 rails, AND-gated PSRAM rail, rules `power_sequencing` / `switched_domain_pullups` + negative tests, 0 Ω staging links, ~30 test points |
| G7 BGA escape, stackup, BOM risk, JLC review | **PARTIAL** | `docs/MANUFACTURING_AND_BGA_PLAN.md`, `sourcing/BOM_CANDIDATES.csv`; the JLC capability check and stock are R09 |
| G8 diagnostic firmware separating CPU boot / BT820 ID / graphics / FPGA config / PSRAM BIST | **PASS (BUILD_ONLY)** | `f133_diag/` stages S0–S5, reproducible eGON 16,384 bytes; physical results **NOT_TESTED** |
| G9 archive with manifest, hashes, comparison, reports, scripts; unverified statements named | **PASS** | `ARC1_R08_ENGINEERING_SOURCE.zip` + `MANIFEST_SHA256.txt`, `EVIDENCE_LEDGER.json` (28 entries) |

Corrective handoff gates:
- **G0 owner alignment:** PASS (D-01…D-07 reflected; the LCD is explicitly deferred).
- **G1 boot electrical:** HOLD (designed; the BROM fall-through and NOR format are undocumented).
- **G2 chip qualification:** PARTIAL (exact P/N W25Q256JVFIQ; lifecycle NOT_FOUND).
- **G3 recovery:** PARTIAL (the clip path is guaranteed by design; FEL is unverified).
- **G4 native CAD:** PASS.
- **G5 FPGA native:** NOT_RUN.
- **G6 firmware tests:** PASS (simulation-labelled).
- **G7 power/assembly:** PARTIAL (the USB budget needs an owner decision).
- **G8 R09 intake:** PASS (`docs/R09_LAYOUT_AND_RELEASE_PLAN.md`).

## 2. Steps and results (latest run)

| Step | Command (cwd) | Result |
|---|---|---|
| handoff_integrity / frozen trees | manifest SHA-256; `git diff --quiet 1262c1a -- R05_BASELINE R06_WORK R07_WORK` | PASS |
| r07_regression_full | `python3 R07_WORK/tools/run_r07_checks.py` (scratch copy) | PASS (R07 16/0/6, incl. the R06 suite) |
| fw_r08_test / sanitize / freestanding / mutants | `make test|sanitize|freestanding|mutants` (R08_WORK/firmware) | 757 checks, 0 failures; ASan/UBSan clean; 4/4 mutants killed |
| rtl_r08_lint / top_sim / synth_estimate | `make lint|sim|synth-efx` (R08_WORK/fpga) | Verilator clean; tb_top_r08 PASS (R06 suite + P0–P4); Yosys 1312 LUT4 / 858 FF / 50 RAM_5K |
| kicad_generate (+ reproducible) | `python3 gen/gen_kicad.py` (R08_WORK/cad) | byte-identical regeneration |
| kicad_erc / erc_json / netlist / pdf | `kicad-cli sch erc|export ...` 9.0.9 | **ERC 0/0**; netlist; 10-page PDF |
| crosscheck_1to1 | `python3 cad/check/crosscheck_r08.py` | A/B/C/D 0 mismatches |
| board_rules / negative tests | `check_board_r08.py`; `unittest test_check_board_r08` | 11/11; 16 tests (15 hazards caught) |
| electrical_margins | `python3 analysis/electrical_margins_r08.py` | 22 PASS, 5 CONDITIONAL, 1 OPEN, 2 FAIL (every FAIL/OPEN has a risk ID) |
| efinity inputs (+ reproducible, syntax) | `gen_efinity_r08.py` | 17 GPIO, XML well-formed, ISF compiles |
| efinity_native | — | **NOT_RUN** (Efinity unavailable) |
| f133_diag build ×2 | `make` (R08_WORK/f133_diag) | EGON_OK, identical SHA-256 |
| evidence_ledger_schema | — | 28 entries valid |
| pcb_layout_drc, si_pi_simulation, hardware_any, vendor_answers, fabrication | — | NOT_RUN (named) |

Tools: KiCad 9.0.9 (official PPA), GCC 13.3, riscv64-unknown-elf-gcc 13.2.0, mkimage 2025.10, Icarus 12.0,
Verilator 5.020, Yosys 0.33, Python 3.13. Efinity: **not available**.

## 3. What changed electrically (summary; details in docs/ENGINEERING_CHANGE_R08.md)

1. **Boot:** BOOT-SEL **00** with a 32 MiB SOIC-16 NOR on SPI0 CS0. Worst-case strap level is 0.794 V vs VIL 0.96 V.
2. **T35 isolation:** the T35 is isolated from SPI0 by 4 Ioff buffers (OE# pulled up) and is **unpowered by default**. Its rails are sequenced VCC (1V2) → PG → VCCIO (3V3_T35).
3. **MN820 MISO:** buffered (SN74LVC1G125, OE# = BT_SS_N). Margin is +0.40 V where R07 had +0.02 V.
4. **PSRAM:** switched VDD (AND of F133 request and CDONE delayed > tUSER), switched start-up pull-downs, 100 kΩ static pull-downs, CE# pull-up to the switched rail, supervisor PG → T35 RTL guard → AMBX v2 POWER_LOST/EPOCH.
5. **USB / audio / SD:** USB-C sink + USB0 FEL/device only; 2 × MAX98357A on I2S; microSD for games with a switched VDD.

## 4. Open blockers (owner / next step in RISK_REGISTER_R08.md and R09 plan)

| Priority | Item |
|---|---|
| P0 | BROM NOR/FEL facts and eFuse state (Allwinner V7 + first article) |
| P0 | Native Efinity run (owner PC) |
| P0 | MN820 supply confirmation (Bridgetek V1) |
| P0 | Layout / DRC / footprint review (R09) |
| P0 | USB power budget (owner: ≥ 1.5 A Type-C or battery) |
| P1 | NOR VOH under the strap load |
| P1 | 3V3 supervisor dead band |
| P1 | NOR lifecycle |
| P1 | F133 PDN facts |
| P1 | Generated/candidate footprints |

## 5. Assumptions in force (each tagged in EVIDENCE_LEDGER.json / margins inputs)

- **F133 BROM:** behaves as the D1-H UM describes, and falls through to FEL (bench).
- **SPI timing:** F133 SPI setup 3 ns; board flight 1 ns.
- **Load estimates:** F133 1.2 W, T35 0.6 W, buck efficiency 0.85, amplifier efficiency 0.85.
- **Component values:** LVC1G17 VT+ ≥ 1.3 V; PSRAM supervisor response 2 µs.
- **Packages:** T35 FBGA400 body 17 × 17 mm.
- **Third-party practice:** the MangoPi D1s reference for EPAD, LDOA usage, RESET pull-up and the VRA caps.
