# ARC-1 Compact — R06 / R07 proof plan

Pass designations describe **the next two engineering work sessions**, not guaranteed completion or native hardware measurements. Report what actually runs and what is blocked by toolchain or missing physical board.

## R06: architecture refactor + memory controller specification

1. Use the already-extracted unchanged `R05_BASELINE/` source and evidence. Record all source hashes and run baseline tests (include environment, commands, complete exits, warnings).
2. Build an F133 pin/boot/storage mux table for separate BT SPI and T35 SPI, including safe boot straps and SD/MMC conflicts. Resolve BT820 QSPI host mode and exact voltage constraints.
3. Write updated board-level architecture, rails, BGA bank plan and reset dependency graph: `F133 -> BT820 -> LCD` independent of `T35`; `F133 <-> T35`; `T35 <-> PSRAM`.
4. Check AP Memory datasheet commands, initialization, timing, maximum burst / chip-select assertions, QPI entry and exit modes, read data hold/dummy periods, and return a traceable register/timing table.
5. Implement a synthesizable conservative T35 PSRAM controller plus a simulator/behavioral PSRAM model and testbench. Tests: reset readiness; bit walking; address walking; pseudo-random data; first/last address; page/wrap boundaries; sequential bursts; randomized stalls; invalid requests; clock domain crossing; reset in transfer; recovery after error; read-after-write; CS timing. Include test evidence.
6. Produce an exact-device T35 Efinity project skeleton for exact T35F400C3 with PSRAM GPIO constraints, mailbox/compute, clocks, debug. Run native Efinity synthesis/fit/STA if available. If unavailable, flag `NATIVE_EDA_NOT_RUN` and deliver exact commands/instructions, not fictitious reports.
7. Preserve R05 numeric and protocol ABI; re-run their existing tests after any code change.

**R06 exit gate:** honest artifact inventory + pass/fail simulation; legal draft pin/voltage map; device-specific Efinity results where available; PSRAM procurement candidate. No claims of working 8 MiB hardware.

## R07: direct graphics and optional compute bring-up

1. Compile actual F133 BSP and two separate SPI device drivers. Pin current toolchain and SDK sources (license permitting). If physical boards unavailable, report build-only status.
2. Create a BT820 graphics initialization/command layer with exact documented commands and display mode, using MN820 official eval hardware where available.
3. Show a real, reproducible CPU->BT drawing command trace and the automated mock/HAL tests for timeout/sequence/command validity. Don't claim a lit display until one is visibly tested.
4. Integrate PSRAM controller and T35 computation as *optional* CPU-submitted jobs; test fallback to CPU whenever FPGA reset/not-ready/error, without disrupting the CPU->BT path.
5. Run synthetic STRUTHIO-style workload (explicitly not game-source authority): scrolling layers, animated sprites, scaling/culling, batch transforms. Compare CPU-only and accelerator-assisted end-to-end frame budgets. Include mailbox traffic cost and PSRAM throughput. Distinguish modeled timing from measured hardware.
6. Document JLCPCB manufacturing dependencies, schematic/netlist open items, official firmware tooling blockers and the exact next practical bench demonstration.

**R07 exit gate:** evidence-backed compatibility/maturity report, runnable builds/simulations, demonstrated graceful degradation in tests and a go/hold/redirect decision. No PCB ordering until full electrical and manufacturing verification.

## Performance sanity math

- 60 unique FPS = 16.667 ms per frame.
- QSPI PSRAM at 40 MHz x4 SDR has 20 MB/s **wire-rate** (not net useful data rate).
- 8 MiB transfer at this ideal 40 MHz wire-rate takes ~419 ms, before overhead; do not treat it as a one-frame raster buffer transfer path.
- 1 MiB transfer at this ideal rate takes ~52.4 ms; use batched compute or selective data movement instead.
- `FPGA_MEMORY_BYTES = 8 * 1024 * 1024`; unlike 64-Mbit flash this is volatile.

The final difficulty reduction depends more on *optional FPGA and direct display* than on memory technology alone.


## Product-direction constraints added after original unified handoff

Prioritize stable, polished **2D** work as `PRODUCT_VISION_2D_FPGA_AUDIO.md` specifies. For pass 6 record audio pinmux/DMA/DAC or I2S resource needs and initial stereo amplifier requirement as a **reserved design interface**, not a demonstrated audio implementation. For pass 7 use lightweight synthetic sprite/layer graphics with a baseline CPU-only mode and test that disabling T35 does not disrupt it; a later rich-scene / audio benchmark remains a future performance gate. Do not treat '128-bit' as literal ISA/memory requirement; no new DSP/MCU for sound. All actual FPS, audio voice count and visual quality are UNMEASURED until hardware tests.
