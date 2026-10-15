# R8.5 risk register (unresolved-risk ledger; the R08 register is kept unchanged in docs/inherited_r08/)

Status: **HOLD / PARTIAL – HARD STOP raised (CO 5.3), owner decision required.** No fabrication release. R09 not entered.

| Rank | ID | Risk | R8.5 action / state | Status | Evidence | Owner / next |
|---|---|---|---|---|---|---|
| **P0** | **RK-OFFLOAD-LINK** (new) | The F133↔FPGA mailbox (single SPI, ≤ sys/8 = 10 MHz, results must come back because the F133 alone drives the BT820) moves data 100–1000× slower than the CPU computes. Every representative 60 Hz workload is transfer-dominated and slower than the CPU | benchmark with ISS-counted CPU work, real driver over the link model, RTL engine cycles | **HARD STOP (CO 5.3)** | docs/BENCHMARK_R85.md | **owner**: options in STATUS_R85.md §5 |
| P0 | RK-BOOT-NOR | NOR-first boot facts (BROM NOR format, FEL fall-through, eFuse) | unchanged from R08; FPGA isolation re-proven for the ECP5 (rules + FIT F03) | OPEN | inherited_r08/BOOT_TRACE_DOSSIER.md | Allwinner V7 / first article |
| P0 | RK-ECP5-SILICON (new) | sysCONFIG flow, status bits, wake-up timing, SSPI over the buffers at 25 MHz never run on an ECP5 | loader + model + RTL; JTAG independent path | **PHYSICAL_NOT_TESTED** | ECP5_CONFIGURATION_R85.md | first article: JTAG detect, then F133 SSPI load |
| P0 | RK-ECP5-SOURCING (new, G1) | exact orderable part, stock, JLCPCB caBGA381 assembly handling not confirmed in this pass (CO quotes a DigiKey listing) | MPN fixed in the BOM, nothing ordered or quoted | **OPEN** | sourcing/BOM_CANDIDATES.csv | owner/Claude: distributor + JLC quote |
| P0 | RK-MN-PWR | MN820 supply confirmation | unchanged | VENDOR_OPEN | inherited_r08 | Bridgetek V1 |
| P0 | RK-PCB | no layout/DRC/footprint review | ECP5 uses the KiCad library caBGA-381 footprint (pad names cross-checked) | OPEN (R09) | crosscheck B | R09 after R8.5 acceptance |
| P0 | RK-USB-BUDGET | ≈ 0.88 A with amps muted vs a 500 mA default source | ECP5 budget replaces the T35 estimate (similar) | OWNER DECISION (FAIL in margins) | ELECTRICAL_MARGINS_R85.md | owner |
| P1 | RK-ECP5-POWER-EST (new) | dynamic VCC/VCCAUX currents assumed (Lattice power calculator not run); TLV755 start-up slope and accuracy not transcribed | 50 % derating on regulators; ramps calculated | CONDITIONAL | margins `fpga_rails` | R09: power calculator, LDO DS |
| P1 | RK-ECP5-IO-TIMING (new) | nextpnr-ecp5 does not time pads; PSRAM read budget at 20 MHz relies on assumed pad delays | 20 MHz SCLK (13.0 ns vs 25 ns budget); 40 MHz rejected | CONDITIONAL | margins `psram_timing` | IBIS + layout (R09) |
| P1 | RK-PSRAM-IO-TIMING (new) | 40 MHz SCLK fails the hand budget | design runs 20 MHz | ACCEPTED (design limit) | margins | — |
| P1 | RK-ECP5-PULLMODE (new) | default PULLMODE=DOWN on the CE# ball would hold CE# at ≈ 1.7 V during tPU | LPF generated with PULLMODE=NONE on all PSRAM balls; crosscheck C checks LVCMOS33; config-time pull-down harmless (PSRAM unpowered) | CLOSED by constraint (OPEN row documents why) | LPF, margins | bench: CE# waveform at power-up |
| P1 | RK-ECP5-HOTSOCKET (new) | banks 2/3/6/7 not hot-socket safe | one shared enable for all rails; bank 6 nets only pulled low while unconfigured; debug/IRQ on bank 0; UART RX series 1 kΩ | CLOSED by design (calc) | ECP5_POWER_R85.md §2–3 | bench sequencing capture |
| P1 | RK-NOR-STREAM (new) | a NOR-resident bitstream cannot be streamed during the burst on the shared SPI0 | images staged in DRAM / from microSD; boot0 only probes | CLOSED by design | ECP5_CONFIGURATION_R85.md | — |
| P1 | RK-ECP5-STATUS-BITS (new) | LSC_READ_STATUS bit positions (DONE 8, BUSY 12, FAIL 13, BSE 23–25) from the Linux driver + TN | loader fails safe on any unexpected status (DONE pin still required) | OPEN (bench) | ecp5_cfg.h | first article |
| P1 | RK-NOR-VOH | 3.3 kΩ strap pull-down loads NOR DO beyond its VOH test current | unchanged | OPEN | margins | Winbond V6 IBIS |
| P1 | RK-3V3-SUP | 3V3 supervisor dead band 3.02–3.135 V below LVCMOS33 VCCIO min | unchanged root cause (now ECP5 VCCIO) | OPEN (FAIL in margins) | margins | R09: 1 % regulator or accept |
| P1 | RK-FOOTPRINT | generated/SLIM4/placeholder footprints; ECP5 library land pattern vs DS-02053 drawing not reviewed | ECP5 footprint is STD_LIB | OPEN | crosscheck B | R09 #5 |
| P1 | RK-F133-IMG | images built, never executed | diag image now probes the ECP5 | BUILD_ONLY | f133_diag | first article |
| P1 | RK-NOR-LIFECYCLE, RK-BT-DECODE, RK-F133-PDN | unchanged from R08 | — | OPEN / VENDOR_OPEN | inherited_r08/RISK_REGISTER_R08.md | as R08 |
| P2 | RK-ECP5-HOLDN (new) | HOLDN treated as an optional SSPI input and pulled up | conservative | OPEN (bench) | design.py note | first article |
| P2 | RK-ECP5-85F (new) | the owner might expect a drop-in 85F | migration table: 0 bank/dual changes on used balls, 9 pad-name changes; different IDCODE/bitstream/power; NOT selected | INFORMATIVE | MIGRATION_45F_85F_R85.md | owner only on request |
| P2 | RK-PSRAM-FAULT-BP | ≈ 1.2 µs back-power window on an unannounced rail loss | unchanged (RTL P4 re-run on ECP5) | ACCEPTED | tb_ecp5_top P4 | — |
| P2 | RK-SPI1-TIMING, RK-AUDIO, RK-SPI-QUAD, RK-PANEL | unchanged from R08 | — | as R08 | inherited | as R08 |
| closed | RK-T35-EDA | native Efinity never ran | superseded: the ECP5 has an open-tool routed build | SUPERSEDED | BUILD_REPORT | — |
| closed | RK-T35-TUSER | CDONE_DLY vs tUSER | replaced by DONE_DLY ≥ 100 µs requirement (0.7 ms calc, VT+ ASSUMPTION) | CONDITIONAL | margins | R09 LVC1G17 DS |
