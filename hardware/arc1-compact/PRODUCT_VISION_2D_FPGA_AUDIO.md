# ARC-1 Compact — Owner's Product Direction (14 October 2026)

**Authority:** This is the current user-approved product and architectural direction, included in R06. It is a requirements statement, not proof of delivered performance, native chip support, working software or working electronics. Read with root `CLAUDE.md` and `START_HERE.md`; overrides older design ambitions when inconsistent. Preserve prior R05 source/test evidence without relabeling it.

## Product identity: a generationally advanced 2D arcade console

- Design for exceptionally polished **2D arcade gaming**. The owner's metaphor is **"a 128-bit Super Nintendo"** — a generational visual leap, not a requirement for a literal 128-bit CPU, 128-bit memory bus, instruction set, 3D GPU, or a marketing claim about confirmed performance.
- Favor beautiful high-detail 2D character artwork, excellent animation, animated environments, layered scrolling/parallax, bitmap rotation/scaling, alpha composition, masked effects, rich colors, expressive boss animation and reliable game feel.
- STRUTHIO (the jousting game) is the key artistic/workload reference, but do not invent/import assets or misrepresent synthetic demos as the actual game.
- Target stable **60 *unique* frames/s** and good input latency as engineering goals. Not measured and not guaranteed. The actual screen resolution, diagonal, orientation and panel remain open; the R05 1024x600 7-inch LVDS panel is a *candidate for development*, not a frozen enclosure target.
- No general-purpose PlayStation-class 3D, polygon rasterizer, 3D emulation, or CPU word-width race. Selective 2.5D and perspective effects are future options only if they do not compromise premium 2D.
- Representative later-stage synthetic graphics stress scene (not an R06 first-pass deliverable): 4–8 layered planes, roughly 64 or more animated objects, large scaling boss, particles, transparency and scrolling, measured at the actual output resolution. THESE COUNTS ARE TARGETS ONLY. Establish real display-list complexity, drawing bandwidth, storage, refresh, and CPU cost empirically.

## FPGA design philosophy: a reprogrammable enhancement chip

- The optional T35 is analogous in *role* to a Super FX/DSP-style cartridge enhancement processor, with possible MMC3-inspired asset scheduling in software—not a literal hardware implementation of Nintendo's chips or direct control of BT820 scanlines/VRAM.
- Candidate FPGA workloads: batched coordinate transforms, culling, hit/collision tests, particle motion, procedural animation, sprite geometry and other proven high-return accelerators. Preserve R05 compute/ABI contracts until deliberately versioned and retested.
- **F133 controls the BT820 directly.** The FPGA is not required for display bring-up, boot, normal gameplay, or audio. If FPGA is absent/reset/late/faulted, CPU software fallback must permit continued game/graphics operation.
- The FPGA has ~180 KiB raw on-chip memory plus **candidate 8 MiB APS6404L-3SQR-SN QSPI PSRAM**. This private RAM is for working data, not a high-bandwidth shared GPU framebuffer. Controller RTL, pinout and practical bandwidth remain unverified.
- Game-specific FPGA bitstreams are a long-term extensibility idea requiring reliable configuration, safe fallback and versioned driver ABI—not an R06 mandatory deliverable.
- Measure end-to-end CPU time saved AFTER submission, retrieval and memory-transfer overhead. Don't add accelerator complexity if it does not help actual 2D workloads.

## Audio: no extra programmable audio processor in baseline

- **F133 owns audio mixing, playback scheduling and DMA-buffered output.** Its documented integrated audio facilities are the initial baseline, subject to exact F133-B pin/package, audio registers, clock and analog validation.
- Plan **16-bit stereo at 48 kHz** as the initial quality target, with ~32 simultaneous software-mixed voices as a **benchmark goal**, not a guaranteed hardware count. Higher/lower counts depend on measurements and algorithms.
- A dedicated suitable **stereo speaker amplifier** remains required for speakers; do not assume an integrated headphone output can directly drive loudspeakers. Design power, analog grounding, output loads, connector and EMI accordingly.
- Consider external I2S audio DAC/codec as an **electrical/audio-quality fallback** if onboard DAC proves inadequate. This does not automatically offload mixing. Do not add a dedicated DSP/MCU/FPGA audio subsystem in R06; only revisit after actual audio CPU/underrun/noise measurements warrant it.
- A later acceptance benchmark should test music + overlapping effects while graphics/FPGA workloads run; log mixer CPU percent, buffer underruns, audio latency, output quality and stability.

## Two-pass scope discipline

- R06 is a direct F133->BT820 host/pinmux feasibility + optional T35 mailbox/PSRAM feasibility milestone; preserve current pass-6 acceptance tests.
- R07 is integrated command-path/mocked bring-up, genuine firmware / native EDA attempts, graceful fallback and a preliminary stylized 2D scene; not a polished full game or final audio subsystem.
- Add an *audio architecture note* and preliminary pin/resource reservation to R06/R07 but **do not divert these two passes into building a full audio engine or production amplifier PCB** before graphics and basic feasibility are established.
- Report manufacturer-documented versus host-tested, RTL-simulated, natively synthesized, electrical test and real on-board measurements distinctly.

## Manufacturing / delivery

- JLCPCB is a candidate assembler. The custom PCB cannot be ordered based on software sims. Require signed-off schematics, legal pin assignments, voltage compatibility, power tree, DDR/PSRAM and LVDS constraints, production BOM, correct footprints, assembly/DFM review and a bench-debug/bring-up plan.
- Retain R05 baseline unchanged; implement modifications under R06_WORK and document each verification. Don't silently write over authoritative R05 test evidence.
