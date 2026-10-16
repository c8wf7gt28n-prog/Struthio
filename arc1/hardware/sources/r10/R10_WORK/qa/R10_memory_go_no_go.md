# R10 memory architecture — go / no-go (ARC1_MEMORY_R10 v0.1 §7.3 item 8)

Spec: `spec/ARC1_MEMORY_R10.docx` (v0.1, 15 Oct 2026; sha256 in `spec/SHA256SUMS`). Labels: DOCUMENTED, DERIVED,
RTL_SIMULATED, HOST_TESTED, OPEN_TOOLCHAIN_ROUTED/MEASURED, CONDITIONAL, NOT_RUN. No confidence scores.
Reproduce: `./run_all.sh` (writes `qa/RUN_ALL.log`).

**Overall: HOLD.** Every §7.1 fabrication gate still needs hardware or a datasheet check; the RTL, firmware and pin
plans for all four memories exist and pass their simulations and host tests.

## §7.1 gates
| Gate | Evidence required | Result | Evidence |
|---|---|---|---|
| NOR / F133 boot | exact 64 MiB part bootable by the F133 ROM; 3-/4-byte transition works | **HOLD** — host side PASS; silicon NOT_RUN | `firmware/f133_bootloader` (74 checks, 6/6 mutants): images above 16 MiB read with 4-byte opcodes, device left in 3-byte mode (`nor_mock_brom_read_ok`). Driver fix found here: JEDEC capacity code 0x20 (512 Mbit) was decoded as `1 << 32`. W25Q512JV ID/opcodes ASSUMED from the JV family — datasheet not read |
| D213 flashless boot | D213 runs validated graphics firmware with no local NOR/eMMC | **HOLD — NOT_RUN** | `firmware/d213_flashless_proof/PLAN.md` (P1–P7 with pass criteria). Fallback pads reserved: `hardware/R10_flash_pinmux.csv` group D213NOR |
| FPGA configuration | both FPGAs load from the shared NOR via CPU-controlled vendor modes | **HOLD** — 12F path HOST_TESTED; 45F path NOT_RUN | 12F: `r10_boot_fpga12` application→golden, app marked bad on image corruption, F133 survives both failing (tests `boot_fpga12*`, R8.5-C sysCONFIG mock). 45F: images located and staged by the F133 (`boot_c45`); D213 slave-SPI loader not written. Bitstreams fit: 45F 1 055 505 B in 3 MiB, 12F 600 913 B in 2 MiB (OPEN_TOOLCHAIN_MEASURED, uncompressed) |
| 12F RAM + RGMII | RGMII link, QSPI controller and workload fit the exact package with margin | **PASS in RTL simulation and proxy-package P&R; TQFP144 pin-locked NOT_RUN** | `fpga12/timing/R10_12F_MEM_FIT_TIMING.md`: TB `R10_12F_MEM_TB_PASS`; 10/10 runs; −6 sys 81.6–87.4 MHz (80; 2 % worst margin), −7 89–102; LUT 59 %, EBR 10/32, MULT 8/28, PLL 2/2. PSRAM part protocol ASSUMED APS6404L-compatible |
| 45F SDRAM + link | controller synthesis, bank voltage/pinmux and board timing verified | **PASS in RTL simulation and P&R; board timing CONDITIONAL (calibrated)** | Timing parameters are now the DOCUMENTED worst case of AS4C16M16SA -6/-7 (Rev 3.0 Table 16), CL3. The fixed read-capture point was shown NOT to work with realistic I/O delays (`analysis/R10_SDRAM_TIMING.md` §2); fixed by a phase-steppable PLL SDRAM clock + power-up calibration (`sdram_cal.sv`): 6/6 delay corners pass calibrated, 5/6 fail without (`make sdram_corners`); model checks tIS/tIH and drives garbage outside tOH..tAC. `SDRAM_TB_PASS`, 5/5 mutants; 45F top `R10_45F_TB_PASS` with calibration + self test; P&R 5/5 seeds sys 84.3–91.0 MHz (80), LUT 20 %. Open: PLL phase-step semantics, real I/O delays, drift |
| D213 memory coherency | PBUS DMA reads / CPU cache coherency and full frame-pipeline test | **HOLD — NOT_RUN** | the link is GMAC0 RGMII (decision D1), not PBUS: `d213/gmac_link/PLAN.md` item 2 (cache clean/invalidate or uncached DMA windows; windows in `memory/R10_memory_owner_map.md`) |
| Recovery | A/B rollback, erased/bad-slot behaviour, external programming access | **HOLD** — firmware behaviour HOST_TESTED; access path OPEN | tests: unconfirmed trial rolls back after 3 attempts; erased NOR → rescue / none; corrupt newest manifest → older copy; power cut while writing the manifest keeps the previous state; power cut mid-update refused at commit; locked partitions (boot, rescue, goldens, META) never written. External programmer/JTAG header: schematic item, OPEN |

## Deliverables (§7.3)
| Item | Path | Status |
|---|---|---|
| 1 owner map | `memory/R10_memory_owner_map.md` | written; records the PBUS-vs-D1 conflict |
| 2 NOR partition | `memory/R10_nor_partition.csv` (+ `gen_nor_partition.py`, generated C header) | map of §4 unchanged; checks pass |
| 3 flash pinmux | `hardware/R10_flash_pinmux.csv` (+ `gen_flash_pinmux.py`, LPF fragments) | 85 rows, vendor-file checks, 4/4 injected errors caught |
| 4 F133 bootloader | `firmware/f133_bootloader` | HOST_TESTED |
| 5 D213 flashless proof | `firmware/d213_flashless_proof/PLAN.md` | NOT_RUN (needs hardware) |
| 6 12F memory | `fpga12/rtl/r10_support_mem_top.sv`, `r10_mem_engine.sv`; memoryless fallback `r10_support_top.sv` unchanged | RTL_SIMULATED + routed |
| 7 45F SDRAM | `fpga45/rtl/sdram_ctrl.sv`, `sdram_bist.sv`, `r10_raster_mem_top.sv` | RTL_SIMULATED + routed |
| 8 this report | `qa/R10_memory_go_no_go.md` | — |

## Open questions of §8, as they stand
1. D213 run-from-USB without boot flash — open (plan P1 is a document check that can be done before hardware).
2. 64 MiB NOR boot with factory address mode — driver policy keeps 3-byte mode; ROM behaviour with this part NOT_RUN.
3. 12F package with RGMII + QSPI + config simultaneously — yes in the pin plan (banks 0/1 RGMII, 3 PSRAM, 8 config)
   and in proxy P&R; TQFP144 pin-locked timing NOT_RUN (decision D4).
4. 45F SDRAM pinout/rail/refresh margin — banks 2/3 at 3.3 V; refresh never postponed beyond one 256-word burst
   (max gap 10.05 µs simulated); read-capture margin CONDITIONAL.
5. Failure-resilient updates with one NOR — host-tested as above; NOR itself remains a single point of failure
   (external programmer access required, spec §5.3).

## Decisions taken in this pass
- **D1 kept**: the memory spec's PBUS references are read as "the D213 ↔ 45F link"; capacities, ownership and the
  one-NOR plan do not depend on it.
- FPGA application-image *configuration* failures (device side) do not mark the image bad (could be transient);
  image *corruption* does.
- PSRAM VDD on the 12F is the switched FPGA rail; the R8.5-C PSRAM power guard is not carried over.
