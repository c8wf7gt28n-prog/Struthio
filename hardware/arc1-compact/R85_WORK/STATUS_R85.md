# ARC-1 Compact R8.5 (ECP5-45F change order) status: **HOLD / PARTIAL – HARD STOP raised, owner decision required**

Date 2026-10-15. Authority: owner change order *ARC-1 Compact R8.5 – ECP5-45F Design Change Order* (sha256 2faa469e…,
`handoff_inputs/`). Based on R08 commit 66bed02; R05/R06/R07/R08 are byte-for-byte unchanged.

> **Not approved for fabrication. R09 routing was not entered. Nothing was tested on hardware.** The ECP5 substitution
> is complete at the source level. It is electrically reviewed by calculation and self-authored rules, native ERC is
> clean, and a routed, reproducible bitstream exists. The firmware and RTL tests pass. But the change order's
> **performance criterion (5.3) is not met**: over the SPI mailbox, every representative workload spends more time in
> transfer than in compute, and the FPGA path is slower than the F133 CPU. This is a stop condition: the options are
> in §5, and the choice is the owner's. No confidence percentage is claimed.

Runner: `python3 R85_WORK/tools/run_r85_checks.py` (from `hardware/arc1-compact/`); latest evidence in `R85_WORK/evidence/LATEST.txt`
(run directories are in the source ZIP).

## 1. Gates (CO §7)

| Gate | Result | Evidence |
|---|---|---|
| G1 part identity | **PARTIAL** | LFE5U-45F-6BG381C fixed in the schematic/BOM; Lattice DS/TN/pinout with SHA-256 (`sources/lattice/sources.json`). **No distributor check or JLCPCB assembly quote in this pass** |
| G2 native CAD | **PASS** | KiCad 9.0.9 ERC **0 errors / 0 warnings**, 9 sheets, 353 parts, 154 nets; 381-ball map; bank table; cross-check A/B/C/D 0 mismatches incl. routed placement of all 17 I/O |
| G3 NOR independence | **PASS (design + model) / bench open** | FPGA off by default (PE0 pull-down), SPI0 isolation buffers off at reset (rules `boot_straps_00`, `spi0_fpga_isolated` + negative tests); FIT F03a–c, F09a; R08 boot trace. The BROM facts are still R08's open P0 |
| G4 configuration | **PASS (HOST_TESTED/BUILD_ONLY)** | slave-SPI circuit per TN-02038/39 (rule `ecp5_sysconfig`); loader + P0–P6 service; 33 FIT cases; independent JTAG J5 + J11 power override (`docs/JTAG_RECOVERY_R85.md`). No silicon |
| G5 FPGA logic | **PASS (OPEN_TOOLCHAIN_ROUTED)** | Yosys 0.33 / nextpnr-ecp5 0.6 / ecppack: sys_clk **87.0 MHz** (80 required), psram_mclk 96.2 MHz (40), seeds 1–5 all pass (worst ≈ 82.6 MHz); 5 975 LUT/3 839 FF/14 DP16KD/8 of 72 MULT18X18D; 0 latches; bitstream 288 697 B sha256 `87ca8d61…e829`, **byte-identical rebuild**. No pad-timing sign-off |
| G6 PSRAM | **PASS (RTL) / CONDITIONAL timing** | R06 controller bench re-run (walking bits/addresses, random, page/wrap, bursts, recovery, mutants); tb_ecp5_top P0–P4 + CE# stuck; 20 MHz SCLK pad budget 13.0 ns < 25 ns (assumed pad delays) |
| G7 game link | **PASS (RTL + HOST)** | AJOB/ARES v1 with CRC, sequence, version, length, ABORT; 11 RTL cases byte-exact vs the C reference, RTL bytes re-parsed by the F133 driver; FIT X06–X12 |
| G8 graceful fail | **PASS (model)** | all 11 CO 7.1 cases covered (`docs/FAILURE_INJECTION_R85.md`); every fault ends in P1 with the FPGA off and isolated; the service never touches SPI1 or NOR CS |
| G9 power | **PARTIAL** | rail budget, ramps, VCC/VCCAUX windows, decoupling per TN-02038, test points (`docs/ECP5_POWER_R85.md`); margins 29 PASS / 11 CONDITIONAL / 2 OPEN / 3 FAIL – the FAILs are R08's RK-3V3-SUP and RK-USB-BUDGET plus the deliberately rejected 40 MHz PSRAM clock |
| G10 release | **NOT MET** | delta table (117 rows), BOM, test outputs, risk register exist; **independent review not done; HARD STOP open** |
| CO 5.3 benchmark | **HARD STOP** | `docs/BENCHMARK_R85.md`: speed-up vs worst-case CPU 0.007–0.15 on the current link |

## 2. Latest run (R85_WORK/evidence/run_20261015T121701Z, then re-run after this file was added)

| Step | Result |
|---|---|
| frozen R05–R08 + root files vs 66bed02 | PASS |
| R08 regression (nests R07, R06) in a scratch copy | PASS_R08… 30 pass, 0 fail, 7 NOT_RUN |
| firmware test / sanitize / freestanding / mutants | 799 checks, 0 failures; ASan/UBSan clean; 10/10 mutants killed (6 new) |
| RTL lint / R05 transform bench / tb_ecp5_top + cross-sim | clean / 1165 vectors PASS / TOP_ECP5_TB_PASS + AJOB_RTL_CHECK_PASS |
| R06 PSRAM controller regression | PASS (sim + mutants) |
| pin matrix + LPF (reproducible) | PASS |
| ECP5 build, report, reproducibility, seed sweep | PASS, REPRO_IDENTICAL |
| real bitstream through the loader model | PASS |
| KiCad generate (byte-identical) / ERC / netlist / PDF | PASS, 0/0 |
| cross-check, board rules, negative tests | PASS, 16/16, 29 OK |
| margins, reports, delta, migration, benchmark, FIT table, diag image ×2 | PASS (benchmark verdict HARD_STOP) |
| NOT_RUN | Lattice Diamond/Radiant + power calculator, FPGA pad-timing sign-off, PCB/DRC/SI, hardware, part/assembly quote, independent review, fabrication |

## 3. Deliverables vs the change order

| CO item | Where |
|---|---|
| F133 pin-mux matrix (machine-readable) | `board/F133_PINMUX_MATRIX_R85.csv/.json` |
| complete caBGA381 ball-to-net map | `board/ECP5_BALL_MAP_R85.csv`, `board/ECP5_BANK_TABLE_R85.csv` |
| power tree, sequencing, test points | `docs/ECP5_POWER_R85.md`, margins |
| sysCONFIG + PROGRAMN/INITN/DONE + JTAG; config flash decision | `docs/ECP5_CONFIGURATION_R85.md` §1, `docs/JTAG_RECOVERY_R85.md` |
| state machine P0–P6, two interfaces, versioned protocol | `docs/ECP5_CONFIGURATION_R85.md` §2–4, `firmware/src/accel_service.c` |
| PSRAM tests | `docs/PSRAM_R85.md` |
| reality benchmark + HARD STOP | `docs/BENCHMARK_R85.md` |
| reproducible open build, LPF from the pin matrix, logs, .bit + hash | `fpga_ecp5/` (README, Makefile, BUILD_REPORT, TOOL_VERSIONS) |
| cross-simulation + error injection | `fpga_ecp5/tb/tb_ecp5_top.sv`, `firmware/tools/ajob_vectors.c`, `firmware/tests/test_ecp5.c` |
| failure-injection table | `docs/FAILURE_INJECTION_R85.md` |
| T35→ECP5 delta table | `docs/T35_TO_ECP5_DELTA_R85.md/.csv` |
| risk register, BOM, power budget, native ERC | `RISK_REGISTER_R85.md`, `sourcing/BOM_CANDIDATES.csv`, margins, `cad/ERC.txt` |
| 45F vs 85F from the migration table only | `docs/MIGRATION_45F_85F_R85.md` (85F not selected) |

## 4. Findings the owner should know

1. **HARD STOP (CO 5.3).** At 10 MHz the mailbox moves ≈ 1.3 MB/s; a 170-rectangle transform batch costs ≈ 10 ms of
   link time against 0.06–0.12 ms on the CPU. The ECP5 engine itself needs 0.2 ms, because it reads the request
   byte-serially. Even with a quad link at 4 × 50 MHz, only brute-force collision and FIR come out ahead (≈ 1.7–1.9×),
   and a CPU with a better algorithm would still win those. The cause is the architecture: results must return over
   SPI because the F133 alone drives the BT820. Swapping the FPGA (T35 or ECP5) does not change this.
2. **NOR streaming is impossible** on the shared SPI0 during a configuration burst, so bitstreams are staged in DRAM or
   read from microSD. boot0 only probes the FPGA.
3. **Sequencing changed** from the R08 order (VCC first, then VCCIO) to one shared enable, as the ECP5 checklist requires.
4. **U26 and the configuration flash are gone.** The ECP5 pulls down during configuration and the F133 streams the
   bitstream. PSRAM balls need PULLMODE=NONE, and the LPF generator sets it.
5. **PROGRAMN series resistor reduced 1 kΩ → 470 Ω.** The margin analysis showed only 18 mV of VIL margin with 1 kΩ.

## 5. Stop / revert options (CO 8.2 – submitted, not chosen)

| Option | What it changes | Cost / risk |
|---|---|---|
| A. Keep the ECP5 as an optional, default-off board option (DNP-able); ship games CPU-only | nothing electrical; the FPGA path stays for future work | BOM/area for a part with no measured benefit |
| B. Remove the accelerator (FPGA + PSRAM) from Compact | simplest board; F133 + BT820 carry everything | gives up the FPGA vision for this product |
| C. Re-architect the link: wider/faster host interface (e.g. 8-bit parallel or quad SPI with a source-synchronous slave) **and** move whole subsystems (state resident in FPGA/PSRAM, small results) | could pass 5.3 for selected work (collision/FIR break-even ≈ 25 MB/s) | new pins, new RTL, F133 driver work; must be re-benchmarked |
| D. Revert to the T35 | restores R08 | **does not fix the HARD STOP** (same link) and loses the open toolchain |
| E. Owner-approved FPGA→display/BT820 path | removes the return trip | explicitly forbidden by the protected baseline; listed only for completeness |

Recommendation (an engineering opinion, not a decision): **A now**, with **C** as a separately scoped study if the owner
still wants hardware acceleration. Neither T35 vs ECP5 nor 45F vs 85F changes the outcome.

## 6. Next steps

1. Owner chooses among §5 A–E (and confirms the USB power policy from R08).
2. G1: distributor stock + JLCPCB caBGA381 assembly quote; G10: independent R8.5 review.
3. Only after acceptance: R09 placement/routing (`docs/inherited_r08/R09_LAYOUT_AND_RELEASE_PLAN.md`, ECP5 land-pattern
   review vs DS-02053, IBIS for PSRAM/SPI, Lattice power calculator).
4. First article: J11 + JTAG `--detect`, F133 diag S4 probe, SSPI load, AMBX DISCOVER, PSRAM BIST.

## 7. Assumptions in force

F133 CPU 1.0 GHz, CPI 1–2 (benchmark); ECP5 dynamic currents and pad delays; TLV755 accuracy and start-up; LVC1G17 VT+;
F133 driver 2 µs per CS transaction; sysCONFIG status-bit positions; all R08 assumptions. Each one is tagged in the
margins inputs, the benchmark JSON or `EVIDENCE_LEDGER.json`.
