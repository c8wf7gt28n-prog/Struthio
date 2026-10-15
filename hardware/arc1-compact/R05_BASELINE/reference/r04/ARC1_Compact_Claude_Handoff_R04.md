---
title: ARC-1 Compact — Claude confirmation and continuation handoff
date: 14 October 2026 · Revision 0.4
---

**Selected working combination: Allwinner F133-B + Efinix T35F400C3 + Bridgetek BT820B, a built-in LVDS screen, and three separately owned RAM pools with a 320 MiB installed-capacity target.** The owner has approved this direction and asks Claude to independently confirm it and continue engineering. This is the active Compact baseline; Tabletop R23 remains a separate historical project. No assembled Compact memory installation has been observed.

The architecture has documented component capabilities and a concrete screen-timing candidate. Interconnect implementation, exact DRAM selection, FPGA timing closure, actual game performance and the final board remain unverified. Continue useful design and code work while producing the evidence needed to qualify those boundaries.

![Selected Compact core and proposed interfaces](assets/compact_architecture.png)

## 1. Selected components and memory

| Element | Selected working proposal | Responsibility / status |
|---|---|---|
| CPU | F133-B, included 64 MiB DDR2 | Game/platform authority; exact board/BSP and runtime to confirm |
| FPGA | T35F400C3, dedicated 128 MiB x16 DDR3L | Transform calculations, command construction/scheduling, timed input and future custom rendering |
| Graphics | BT820B, dedicated 128 MiB DDR3L | Active bitmap drawing, affine transforms, alpha composition and display presentation |
| Initial graphics module | MN820 | Includes BT820B, 1-Gbit DDR3L and memory power support |
| Screen candidate | Newhaven NHD-7.0-1024600AF-LSXP | 7-inch IPS, 1024×600, direct single-channel LVDS; qualify exact revision |

64 + 128 + 128 = **320 MiB selected installed-capacity target**, not a unified address space. One 1-Gbit x16 DRAM contains 128 MiB. Each controller owns its memory; transfers need explicit protocols, address windows and fences.

T35F400 has hardened x8/x16 DDR support. Do not substitute F256 or reuse Tabletop x32 LPDDR2 mappings. Confirm exact memory geometry, timing, rails and controller configuration in the current T35 datasheet and Efinity. An 800 MT/s starting point gives an x16 raw ceiling of 1.6 GB/s, not achieved bandwidth. Exact FPGA RAM SKU remains open; qualify sourcing and timings together. Earlier Alliance C-die research established a possible geometry, not a preferred purchase.

Use MN820's 128 MiB DDR3L for the first BT prototype. A final bare BT820 and discrete memory layout require their own exact-part, initialization and board qualification. Reserve BT's documented upper 2.5 MiB DDR region before allocating user buffers. Framebuffer stride, alignment, atlases and working allocations further reduce asset space.

Sources: S01–S06 in `engineering/sources.json`.

## 2. Proposed initial topology

**F133 SPI scene mailbox → T35 transforms/command scheduling → BT820 QSPI → LVDS panel.**

The FPGA is the sole BT host-bus master. CPU packets should carry compact scene descriptors and necessary uploads, not a fresh full-resolution framebuffer per refresh. Define frame/job sequence, protocol version, epochs, payload lengths, CRC, credits/backpressure, persistent status/IRQ acknowledgment, timeouts and reset behavior.

Start the CPU link in single-bit SPI and qualify quad separately. A proposed prototype uses SD0 for CPU boot and SPI0 for the FPGA mailbox; this is not a finalized storage or pin plan. SPI0 PC2–PC7 overlaps SD/MMC2, and PC4/PC5 also serve boot-select functions. Preserve strap sampling and safe high impedance during reset/configuration. Verify the exact bonded F133 package pins and selected software implementation.

Give the FPGA useful initial work: a batched fixed-point transform and viewport-culling kernel, followed by drawing-command assembly. Provide a CPU reference, golden vectors, defined rounding/saturation and tests for edge cases. Compare the whole FPGA path against the CPU, including transfer and wait time. Rendering pixels is BT's active accelerator role.

The fixed-board target includes FPGA-local DDR for textures, buffers and future pixel effects. The first mailbox/kernel test may use block RAM. A future T35 LVDS → BT LVDS capture path is optional and must independently prove serializer timing, buffer ownership, format and latency. Decide whether to route/reserve its legal pins, banks and clocks **before PCB freeze**, because adding that connection later may require a motherboard change. Its RTL and capture benchmark may be deferred. Captured RGB does not provide a per-pixel alpha input. Do not make this extra frame pipeline mandatory for the initial command-rendered scene.

Recovery must work with invalid FPGA logic. A mailbox implemented in user RTL disappears when that RTL is absent. Plan externally reachable reset/configuration/JTAG, CDONE observation, bus isolation and safe outputs. Permanent CPU/FPGA boot flash, game storage and configuration ownership remain open.

Sources: S02–S05, S07–S10.

## 3. Screen and 60 Hz planning candidate

The named Newhaven panel has a 3.3 V logic supply, four LVDS data pairs plus clock, and a 40-pin FFC. Its datasheet permits the proposed **48 MHz clock with horizontal total 1280 and vertical total 625**. The documented BT clock expression gives:

`38.4 MHz × 15 / (2 × 6) = 48 MHz`

`48,000,000 / (1280 × 625) = 60 Hz nominal`

`SYSPLL_NS=15`, `TXCLKDIV=5` are the proposed clock settings, subject to confirmation of the exact silicon/firmware and register semantics. Proposed porches are H sync/back/front 16/160/80 and V 1/23/1. Confirm the panel's definition of porch lengths, BT offsets/units, polarity and single-channel mode before implementation. These numbers are arithmetic evidence, not measured screen operation.

Inspect the exact 8-bit LVDS slot mapping; VESA24/SPWG is a documented-map inference to verify using color-bit-walk patterns. Confirm differential swing/common mode, termination, pair polarity and connector contact orientation; the 3.3 V panel supply is not the LVDS signal level. Do not assume cable pin compatibility. Design the panel reset/standby, connector and a separate constant-current LED backlight supply, nominally 150 mA at 19.2 V.

The panel's specified rise-plus-fall response is 30 ms typical / 40 ms maximum. Test scrolling, sharp moving sprites and contrast transitions before final screen signoff. Electrical refresh and motion quality are separate checks. Screen orientation remains open; physical portrait mounting plus supported rendering rotation can be evaluated without changing wire resolution. Scan-reversal pins are not a 90-degree rotation function.

Direct panel output avoids requiring the historical Tabletop HDMI bridge in this prototype. It does not eliminate timing qualification. If HDMI is added later, it needs its own clock/mapping/monitor dossier; do not promise standard 720p60/1080p60 from a resolution feature list.

Sources: S05, S11–S13. Calculations: `engineering/calculations.json`.

## 4. STRUTHIO rendering contract

The goal remains rich 2D animation and selected perspective effects: animated birds/enemies/bosses; rings with front/back layers; independently scrolling backgrounds; floating islands and shadows; transparency; rotation/scaling; and a convincing perspective flourish. BT supplies affine bitmap transforms. Perspective strips, billboards, layered artwork or optional FPGA imagery provide the proposed depth techniques. No general perspective-correct textured-triangle/shader capability is promised.

Recover the authoritative game build and extract renderer, viewport, camera, pose/atlas format, object dimensions/counts, simulation and collision boundaries. The historical 256×384/60 Hz manual is a reference, not automatic authority. Do not change game rules to fit the screen.

While game source is unavailable, build a clearly labeled synthetic scene with animated subjects, four parallax planes, islands, rings/sparks, alpha, transforms and a floor/tunnel flourish. Progress toward the handoff challenge: 256 independently placed instances and 64 transformed instances. These are challenge targets, not certified sprite capacities.

BT's display list is 16 KiB / 4096 32-bit words; its command FIFO is 16 KiB. Every state change, transform and background contributes. At 60 Hz, transmitting 16 KiB per frame is 0.983 MB/s payload before other commands/assets/framing. 1024×600 RGB565 full-frame host uploads would require 73.728 MB/s at 60 Hz, above the QSPI raw ceiling of 30 MB/s. Reuse resident assets and local drawing.

Vary object area, overlap, transparency and asset changes. Keep the same scene seed and art across revisions. Measure distinct presentation, not just panel refresh or loop iterations. Record 30-minute cadence, deadline misses, worst/percentile frame times, display-list/FIFO occupancy, upload bursts, artifacts and input-to-photon latency. Report measured latency before declaring responsiveness acceptable.

Start with official BT82X sample/HAL sources and pin the actual revision and license. VM820C includes MN820 and USB-QSPI for a computer-driven accelerator test. Constrain host traffic to the proposed embedded link budget, then re-run on the F133/T35 chain under input/audio/storage load. A computer demo does not qualify the final embedded transport.

Sources: S05–S06, S14–S16 and original Compact handoff.

## 5. Claude's first implementation queue

1. **Confirm the baseline:** produce a claim-by-claim source table for exact CPU/package, T35 hard DDR, BT firmware/module and screen. Independently recheck current documents; record revision differences and actual sourcing. Prepare vendor questions if a published support contract is insufficient.
2. **Finish display and memory worksheets:** exact proposed timing/register model, lane/pin map and backlight needs; exact DRAM candidates/timing/geometry/footprint/procurement. No invented assignment or init bytes.
3. **Prepare the renderer proof:** representative source scene, asset inventory, deterministic challenge configuration, telemetry and test procedure using official BT code as permitted. Separate synthetic visuals from an actual game port.
4. **Implement the scene transport and kernel:** protocol specification, host/reference code, FPGA kernel/control engine and meaningful fault/edge-case tests. Specify every memory owner and reset boundary.
5. **Generate the exact T35 project:** compile DDR, mailbox, kernel, BT QSPI, IRQ/reset/status, configuration/debug and clocks together. Retain native files, bank/pin/clock/resource/STA reports, warnings and actual binary length. Add optional video only as a separately budgeted expansion.
6. **Complete system integration:** actual bootable F133 firmware/BSP and SPI/HAL build with pinned sources/toolchain, UART boot/transport evidence, CPU RAM budget, boot/game storage, FPGA configuration recovery, power/clock/reset, panel/backlight, controls/audio, current BOM and component availability. Then perform actual hardware scene/DDR/latency/fault tests when boards are available.

Task dependencies, concrete deliverables and acceptance criteria are in `engineering/tasks.json`. Lack of bench equipment or Efinity must be reported precisely; source/specification/model work can continue, but generated or measured results cannot be invented.

## 6. Prior work, limits and return format

The package includes the original Compact handoff and all four original R19/R22/R23 ZIPs, unchanged, plus the recommendation/reconciliation and verification logs. Relevant legacy lessons include exact-package auditing, private RAM ownership, grants/fences/epochs, independent recovery and reproducible tools. Tabletop's T120 pin coordinates, x32 memory, storage locks and mandatory video chain do not govern Compact.

Reproduced historical software checks passed 112 R23 tests and 67 DEV-002 tests; all 484 F484 source rows matched the workbook. Those checks are not Compact hardware validation. Actual STRUTHIO source, native Compact EDA/RTL/images, finalized CAD, full BOM and physical measurements are absent. See `COVERAGE_AND_EVIDENCE.md`.

Return: confirmed findings and conflicts; changed files; source/tool versions; executed checks and genuine artifacts; remaining uncertainties; and one next bounded task. Maintain a selected/documented/proposed/generated/measured distinction. The goal is a confirmed working platform on fixed hardware with room for future software and RTL development, not a supplier-availability guarantee or an unverified fabrication release.
