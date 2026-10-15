# ARC-1 Compact — CURRENT ROOT ENGINEERING INSTRUCTION, R06

## Product-direction update — supersedes older graphics/audio assumptions (2026-10-14)

READ `PRODUCT_VISION_2D_FPGA_AUDIO.md` as an active owner-approved requirement. ARC-1 prioritizes extremely polished 60-fps-target **2D** ('128-bit Super Nintendo' metaphor, NOT literal 128-bit CPU). T35 is optional, reprogrammable Super FX-style enhancement for batched 2D math (MMC3 is only an organizational analogy); no new direct BT820 bus ownership. F133 handles software audio mixing via audio DMA and integrated audio hardware; provide a stereo speaker amplifier, with external I2S codec only as a tested-quality fallback. Do NOT add a fourth programmable processor. Do not allow visual ambition/audio scope to displace pass-6 basic compatibility and tests. All graphics/audio targets remain UNMEASURED.

## Authority / chronological override
The owner's latest confirmed request is to simplify the *Compact* architecture while keeping three chips: **F133 controls BT820 directly; T35 is optional accelerator; T35 has 8 MiB QSPI PSRAM instead of 128 MiB DDR3L**. This file plus `START_HERE.md`, `ENGINEERING_CHANGE_R06.md`, `PASS_6_AND_7.md`, and `CURRENT_ARCHITECTURE.json` override R05 where they conflict. The entirety of `R05_BASELINE/` is reference material and source; it is not a second active handoff. Do not reintroduce R05 mandatory FPGA->BT QSPI or T35 DDR3L from any old nested file or diagram.

This file reflects a design DECISION, not proof that the revised scheme electrically works. A proposed pin/controller/storage assignment remains pending vendor/tool qualification. Stop and present a concrete blocker for impossible electrical assignments.

## Retain all usable tested work
Reuse `R05_BASELINE/protocol/`, `compute/`, `integration/`, `display/`, `memory/`, `system/`, and earlier evidence. Preserve wire ABI, fixed-point numerical contract, test vectors and resets unless changes are explicitly versioned and tested. Prior R05 successful test logs remain historical R05 evidence. Do not edit R05 sources in-place to make untested changes look like validated R05; develop new R06 changes under `R06_WORK/`, copying relevant modules or patching reproducibly and documenting paths.

## Priority technical principles
1. Independent baseline: CPU->BT820 graphics must operate without any FPGA configuration or even FPGA being present. Prove by tests, later hardware.
2. GPU always has *one* commanding SPI master at a time, F133 in baseline; no dual-master shared bus without engineered arbitration.
3. CPU->T35 mailbox optional; CPU handles failed/late jobs and uses CPU fallback.
4. T35->private 8 MiB QSPI PSRAM on legal IO bank. Verify exact memory voltage and pinouts. Controller synthesis/sim must handle read/write, reset, high-Z turnaround, dummy cycles, chip select timing, address wrap and timeouts. Avoid declaring full bandwidth from wire-rate math.
5. Confirm F133 simultaneous SPI pin mux vs boot/storage restrictions, IO level matching, BT820 SPI/QSPI electrical + command compatibility and FPGA bitstream configuration independently; avoid assigning pins based solely on family-name similarities.
6. Keep BT820/MN820 DDR3L as provided by module, without claiming CPU/FPGA shared access. Preserve source and source attribution.
7. No new game mode, STRUTHIO code or visual asset fidelity claim without authoritative source. A synthetic graphics demo is clearly labeled synthetic.
8. Treat display orientation/form factor and panel choice as unresolved: previous 7-inch LVDS screen candidate was never frozen or measured.
9. No automated fabricated milestones, logs, costs, invented procurement or 60-fps claims. Use labels SELECTED, MANUFACTURER_DOCUMENTED, PLANNING_CALCULATED, HOST_TESTED, RTL_SIMULATED, NATIVE_EDA_VERIFIED, PROTOTYPE_MEASURED, BLOCKED, NOT_RUN.
10. JLCPCB is a potential fabrication/assembly vendor, not a designer or guarantor; require exact netlist, BOM, verified footprint and DFM constraints before order.

## Required response after EACH engineering pass
Return a concise status table with completed artifacts, exact commands and exit statuses, evidence paths, failed and unavailable checks, unresolved blockers, assumptions and next tests. Produce source patches/new code rather than a prose-only pass whenever tools permit. If a native Efinix Efinity tool is unavailable, report `NATIVE_EDA_NOT_RUN`; never invent pin-fit/timing reports. Distinguish host/RTL simulation from prototype measurements. Finish R06 before moving to R07 unless the dependencies can proceed concurrently without making a false success claim.

## Build/reference paths
For baseline scripts, `cd R05_BASELINE` and consult `VERIFY.md`. `R05_BASELINE/CLAUDE.md` describes the *superseded R05 wiring only*, not current root authority. New implementation should be made under `R06_WORK/` with new tests or reproducible changes clearly tracked, plus a fresh revision ledger and source/build manifest.
