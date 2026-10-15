# ARC-1 Compact — R06 Unified Engineering Handoff
**Issued 2026-10-14 | Classification: development directive, NOT completed R06 implementation**

## ONE ZIP ONLY
Give Claude **this archive only**. It contains ALL 132 unchanged file payloads from the complete R05 development archive under `R05_BASELINE/`, including original source, HDL, tests, logs, prior engineering attachments, research, and handoffs. The older R05 source is not overwritten or represented as R06 results. Do not also upload the previous R05 or preliminary R06 zip unless Claude specifically requests a missing external artifact.

Read **root `CLAUDE.md` first**, then `PRODUCT_VISION_2D_FPGA_AUDIO.md`, `ENGINEERING_CHANGE_R06.md`, `PASS_6_AND_7.md`, `CURRENT_ARCHITECTURE.json`, `EVIDENCE_AND_BLOCKERS.md`, and `PROMPT_FOR_CLAUDE.txt`. Source lives under `R05_BASELINE/`; its own `CLAUDE.md`, `OWNER_SELECTION.md`, `README_FIRST.md`, `engineering/architecture.json`, task queue, and old architecture diagrams are **historical and superseded only where this root R06 directive changes their assumptions**. If a nested assistant-instruction file is automatically loaded, resolve contradictions in favor of root R06 direction; do not erase old documents.

## Product outcome (latest owner decision)
Produce an unusually polished 2D arcade console: beautiful sprite art and animation, layered effects, and an unmeasured 60 fps target. The "128-bit Super Nintendo" phrase is an art/performance ambition, NOT a CPU-width requirement. The T35 acts as an OPTIONAL Super FX-like enhancement chip; F133 is also the software-audio processor using DMA and a stereo amplifier, NOT another dedicated sound CPU. Read `PRODUCT_VISION_2D_FPGA_AUDIO.md` for the full requirements and the explicit distinction between goals and proven hardware.

## Owner-approved architecture direction

```
                          +----------------------------+
                          | F133-B CPU                 |
                          | 64 MiB in-package DDR2    |
                          +-----+----------------+-----+
                                |                |
                  graphics SPI/QSPI            SPI mailbox
                                |                |
                     +----------v-----+  +-------v-----------+
                     | BT820B / MN820 |  | T35F400C3 FPGA   |
                     | graphics       |  | optional compute  |
                     | 128 MiB DDR3L  |  | accelerator       |
                     +----------+-----+  +-------+-----------+
                                |                |
                              LVDS        quad-SPI private RAM
                                |                |
                         LCD candidate    8 MiB PSRAM
```

- F133 is the *only initial* BT820 command master; FPGA is not required to initialize graphics or run a fallback game loop.
- F133 and T35 use a separate link with timeout and `FPGA_NOT_READY` fallback.
- T35 local memory is one candidate 8 MiB (64 Mbit) Quad-SPI PSRAM, **AP Memory APS6404L-3SQR-SN**. Exact device qualification, bank voltages and controller implementation are pending.
- MN820 keeps its self-contained 128 MiB graphics DDR3L. RAM pools remain physically distinct, not one 200 MiB CPU-addressable bank.
- The previous 128 MiB T35 DDR3L is **deferred**, not implemented in R06. No required direct T35 -> BT820 command link in the baseline.
- The R05 7-inch landscape LVDS panel is a *screen evaluation candidate*, not a frozen size/orientation. Do not silently assume a portrait display or vice versa.

## Deliverables
Start with R06 work (architecture + factual pinmux/signal compatibility, PSRAM controller and independent graphics command path), then R07 work (integrated proof and decision gates). See `PASS_6_AND_7.md`. The R05 protocols, numerical contract, scripts and tests remain authoritative *for behavior* until a deliberately versioned migration occurs.

## Absolute safety/evidence rules
No fabricated tool runs; no claims that a display, memory or PCB works merely because planning validations pass; no custom PCB order release until electrical, PCB and supply risks are closed. Unavailable Efinity or dev boards must be reported as BLOCKED/NOT RUN and accompanied by runnable next steps. Preserve original vendor IP licenses and do not bundle proprietary toolchains.
