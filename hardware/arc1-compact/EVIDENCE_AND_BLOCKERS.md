# R06 Evidence Ledger / Gaps

## Evidence actually enclosed (pre-change R05)
- 132 original non-directory R05 archive entries preserved byte-for-byte under `R05_BASELINE/`, including tests, C sources, isolated HDL source, simulation logs, engineering calculators and provenance files.
- R05 `protocol` C codec/reference and checks are host work, not confirmed physical SPI.
- R05 compute block C reference and SystemVerilog transforms include archived isolated Icarus RTL-simulation results; no native Efinity synthesis/STA evidence in R05.
- R05 synthetic C scene integration and memory/display validators are host/planning checks, not pixels on a physical screen or working FPGA external memory.
- The R06 topology and 8 MiB PSRAM decision in root instructions are new selections, NOT source code already implemented or validated.

## No demonstrated R06 implementation yet
- **NOT RUN:** F133 two simultaneous legal host SPI pinmuxes / boot constraints and actual HAL.
- **NOT RUN:** CPU->BT820 direct physical link, software graphics driver, booted output.
- **NOT RUN:** T35 memory controller synthesizable RTL and QSPI PSRAM behavioral model.
- **NOT RUN:** PSRAM test vector/burst/recovery tests; exact read/write timing and achievable throughput.
- **NOT RUN:** Efinity exact-device fit, timing and BGA pin assignment of full R06 FPGA design.
- **NOT RUN:** Real F133 bootable image; integrated FPGA communications.
- **NOT RUN:** JLCPCB-ready schematic/layout/BOM, signal integrity review, prototype fabrication or bring-up.
- **NOT RUN:** Actual 60 fps / input latency / watts / heat / 10-year optimization headroom.

## Gating questions
1. Can legal CPU pins, controller modes and boot straps support **both** direct GPU traffic and FPGA mailbox simultaneously?
2. Are voltage domains, boot/reset and bus ownership safe throughout startup and failure?
3. Is the selected PSRAM electrically compatible with the intended T35 pins and possible to control with native synthesized logic?
4. Does T35's bounded SRAM plus PSRAM bandwidth support assigned workloads without making the graphics path slower?
5. Can BT820 really initialize and paint the selected candidate display through a tested driver?
6. Are modules, board footprints, components and power regulators actually sourceable/assembleable for JLCPCB?
7. Does accelerative offloading yield positive whole-frame improvement after protocol overhead, under representative content?

## Redirection rule
If one critical link is impossible, propose the smallest correct modification; if the FPGA does not improve relevant workloads, keep the FPGA as *optional extension*, not mandatory game hardware. Do not discard the CPU/GPU renderer or validated R05 C/RTL contracts because optional logic is deferred.


## Added owner targets — NOT YET VERIFIED
Premium 2D visual quality, 60 fps, 4–8 layers, approximately 64+ animated objects, 48 kHz stereo/32-voice mixer target, CPU fallback when FPGA unavailable, and all analog speaker/amplifier performance remain DESIGN INTENT. R05 logs do not prove any of them. See `PRODUCT_VISION_2D_FPGA_AUDIO.md`.
