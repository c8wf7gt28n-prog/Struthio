# ARC-1 Compact R06 — Lower-risk architecture decision (not yet implemented)

**Status:** owner-directed development target and engineering change request, not release for fabrication.

## 1. Repartition the processors

**Previous R05 critical chain:** F133-B -> T35F400C3 -> BT820B (MN820) -> LVDS display. T35 was the sole BT820 QSPI command master. T35 had a 128 MiB x16 DDR3L private memory target, with exact IC not selected.

**New R06 intended critical chain:** F133-B -> BT820B (MN820) -> LVDS display. F133-B -> T35F400C3 is a separate accelerator mailbox, and T35 -> a dedicated 8 MiB QSPI PSRAM is a separate local-memory connection. The GPU's 128 MiB DDR3L stays on MN820 and remains private.

This repartitioning is conditional on checking the F133 physical SPI pinmuxes, reserved boot-select pins, current development-board exposed GPIO, boot storage, BT820 host requirements, simultaneous device use, voltage domains and the BT820 exact QSPI command timing. The Allwinner F133 family describes two SPI controllers; Linux pinctrl definitions show SPI0 PC2-5 and SPI1 PD10-13, extended quad SPI pins depending on exact package. Use SPI1 as a *candidate* BT host and SPI0 as a *candidate* T35 mailbox, not a preapproved pin map. Both sets have boot/alternate-function conflicts that must be audited.

**Graceful degradation requirement:** The FPGA is not required for graphics startup. On `FPGA_NOT_READY`, timeout, invalid version or job failure, game firmware falls back to CPU calculations and the BT renderer continues. Test this both in simulation and on a physical prototype later.

Do not wire two independent SPI masters to one BT820 bus without an explicit, tested mux/arbitration design. Avoid that complexity in first hardware.

## 2. FPGA local memory — baseline

Select **one AP Memory APS6404L-3SQR-SN candidate**: 64 Mbit = 8 MiB, single supply 2.7-3.6 V, 8-pin SOP, SPI or quad-I/O serial access, self-refresh managed inside the memory. This is ordinary volatile RAM, not NOR flash and not retained through power-off. Supplier/distributor part numbers and stock must be rechecked at ordering time; this is a candidate, not an approved BOM item.

Pins at logical-interface level: `PSRAM_SCLK`, `PSRAM_CS_N`, `PSRAM_DQ[3:0]`. Additionally VCC, GND, correct local decoupling and the recommended PCB layout. Connect all data and clock pins to a compatible 3.3-V T35 I/O bank, subject to exact bank/ball assignment and allowed IO standards. Never assume all FPGA GPIO are available at a chosen bank voltage. Reserve FPGA configuration, JTAG and clock resources independently; reject pin conflicts.

Implement a **memory controller in synthesizable SystemVerilog** (or evaluate properly licensed, device-compatible third-party IP). Start with simple read/write transactions at conservative clock rates, then QPI bursts with documented latency/dummy cycles, turnaround and maximum chip-select active time. The PSRAM handles its own refresh, but transaction and timing limits still exist. Data buffers and clock domain crossings belong inside T35; interface reads/writes should be bounded and acknowledged. In particular, implement RAM-ready and RAM-error flags, timeout/recovery and prevent writes after reset until initialization is complete.

The first usable version should seek correctness at 10-20 MHz, then demonstrate e.g. 40 MHz with real timing constraints; these are bring-up goals, not a clock specification or guaranteed performance. At 40 MHz four-bit SDR the raw serial-wire ceiling is 20 MB/s (before command and memory overhead). At 80 MHz the raw ceiling is 40 MB/s; sustained performance will be less. Do not claim DDR-like bandwidth or entire-scene streaming performance from this design.

If 8 MiB proves insufficient, first measure actual FPGA working-set usage. Consider 16 MiB only after validating an exact alternate memory part and its address protocol. The previous 128 MiB DDR3L choice remains a future R&D option, but is removed from the baseline BOM and timing-critical bring-up.

The T35 has 1,475 kbits of embedded SRAM (approximately 180 KiB of raw block RAM), shared among queues, working buffers and controllers. Do not represent all of that as freely available to games. The 8 MiB is FPGA-private, **not** automatically accessible by CPU, BT820 or display.

**HyperRAM caveat:** Efinix has a HyperRAM controller IP, but its official supported families are Titanium and Topaz, not Trion T35. Do not assume that this IP directly works with T35 or assert a native Efinity build unless actually tested. For R06 baseline select Quad-SPI PSRAM with a separately developed/verified controller.

## 3. Preserve R05 implementation value

Do not throw away the existing `protocol/` portable C codec/session, `compute/` numerical contract, SystemVerilog transform engine, test vectors, scene payload, validation checks, sources or original attachments. Preserve byte-compatible V1 transport/message behavior unless a consciously versioned extension is required. Avoid copying native C structs onto the wire. Port reference code incrementally to F133; do not claim a real F133 BSP/boot image without producing one.

Any software that previously sent all BT drawing commands through T35 must be refactored into the direct BT renderer in the CPU runtime. T35 generates *compute results*, not mandatory drawing transport. Profile CPU-only against offload including mailbox command/response time, PSRAM accesses, retries and timeouts. Offload jobs only when mathematically profitable.

## 4. Non-RAM problems remain

LCD panel selection and orientation, real LVDS mapping, backlight and power, physical buttons and audio, storage, clocking, reset, power sequencing, Efinity compilation, actual IO placement, SPI pinmux, JLCPCB DFM and real throughput are still undecided or untested. The first bench prototype should use existing F133/MN820 hardware where suitable. The eventual custom board should be reviewed against JLCPCB fabrication/assembly requirements but **never** called fabrication-ready based only on host simulation.

## 5. Evidence language / stop conditions

Tags allowed: `SELECTED`, `MANUFACTURER_DOCUMENTED`, `PLANNING_CALCULATED`, `HOST_TESTED`, `RTL_SIMULATED`, `NATIVE_EDA_VERIFIED`, `PROTOTYPE_MEASURED`. No invented build reports, benchmarks, EDA log excerpts or claim of working hardware. The R05 checks remain R05 checks until rerun on changed code.

Stop and report: no legal pin assignment / voltage domains, incompatible QSPI command protocol, memory timing not closed at the required clock, unsupported BSP/display init, or no measurable accelerator benefit after proper benchmarking. Otherwise continue on unaffected tasks.

## References for engineering confirmation (recheck current revisions)

- Efinix T35: https://www.efinixinc.com/docs/trion35-ds-v3.2.pdf
- AP Memory PSRAM distributor datasheet: https://www.mouser.com/datasheet/3/4815/1/APS6404L_3SQR.pdf
- AP Memory candidate sourcing: https://www.mouser.com/en/ProductDetail/AP-Memory/APS6404L-3SQR-SN
- Efinix HyperRAM core: https://www.efinixinc.com/support/ip/hyperram-controller.php
- F133 Linux SPI1 pinmux reference: https://code.googlesource.com/linux/torvalds/linux/+/75f2c0b3690702c90863c2e138cb5520670845ea/arch/riscv/boot/dts/allwinner/sunxi-d1s-t113.dtsi


## 2026-10-14 product-target supplement

The latest premium 2D / FPGA enhancement-chip / F133 audio decisions are authoritative in root `PRODUCT_VISION_2D_FPGA_AUDIO.md` and do not alter R06 critical CPU->BT820 topology, optional CPU->T35 link or 8 MiB private PSRAM. Do not reintroduce a 128-bit CPU requirement, a mandatory FPGA graphics path, an FPGA audio processor or an elaborate 3D rendering requirement.
