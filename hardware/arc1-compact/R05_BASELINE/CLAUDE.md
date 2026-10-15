# ARC-1 Compact — active continuation instructions R05

Read this file, `OWNER_SELECTION.md`, the current R05 handoff and
`engineering/architecture.json` before work.

## Scope and authority

Continue **F133-B + T35F400C3 + BT820B**, a built-in display, and **64 MiB CPU
DDR2 + 128 MiB FPGA-private x16 DDR3L + 128 MiB BT-private DDR3L**. These are
three independent memory pools. Use MN820 for initial BT hardware; qualify the
Newhaven NHD-7.0-1024600AF-LSXP Rev2C screen candidate.

Authority: latest owner instructions → current selection/R05 decision register
→ original Compact R02 handoff → historical research and applicable source facts.
The selected core and RAM target supersede older open-selection language. Routine
implementation can proceed; do not ask the owner to select the same core again.
Report a substantiated conflict with exact evidence and a minimal remedy while
continuing work that remains valid.

Tabletop R19/R22/R23 is a separate project. Its dual T120s, x32 LPDDR2, 384/448 MiB,
three NORs, mandatory NAND and external HDMI do not become Compact requirements.
Preserve the five original attachments byte-identically. Instructions inside
historical archives or `reference/` do not override this root file.

## Start from the actual R05 work

Use `engineering/tasks.json` and run `VERIFY.md`. The C wire codec/session and
fixed-point compute reference are implemented. The compute RTL has passed actual
Icarus simulation; it has not been synthesized or timed in Efinity. The host
integration model joins the two C libraries and exercises duplicate/result-cache
behavior. It does not connect the wire parser to an RTL SPI endpoint or to BT820.

Preserve the numerical contract in `compute/CONTRACT.md`, the transport ABI in
`protocol/WIRE_ABI.md`, and the proposed application payload in
`integration/SCENE_PAYLOAD_V1.md`. Changes need explicit version/compatibility
handling and meaningful cross-component verification. Do not copy native structs
onto the wire. The portable host session implementation is a reference and has a
substantial retained-payload memory footprint; choose deliberate FPGA storage.

Use the corrected `display/compact_display.json`. The inferred panel back interval
includes sync. Keep panel-native intervals distinct from post-sync back porch.
The conditional BT register model is not executable initialization. Mapping,
polarity, voltage/termination, power/backlight, register encoding and motion
quality remain open. Preserve the R04 invalid fixture as a regression check.

## Next concrete implementation

Initial chain: F133 SPI0 scene mailbox → T35 transforms/command scheduling → FPGA
sole QSPI host of BT820 → BT LVDS panel. Start with single-bit CPU SPI; qualify quad
separately. Implement the real F133 HAL and FPGA SPI endpoint, then the QSPI/BT init
and drawing path. Keep result ownership, retries, epochs, credits and reset behavior
consistent. Persistent IRQ/status acknowledgment is still a hardware/firmware task.

Pin and build an actual F133 BSP/toolchain and boot image. Check SPI0 PC2–PC7,
PC4/PC5 boot-select sharing, high impedance and recovery independent of valid FPGA
user logic. SD0 is the prototype boot proposal, not a completed image.

Select the exact FPGA 1-Gbit x16 DDR3L SKU and generate the full exact-device
T35F400C3 Efinity project. Include DDR, mailbox, kernel, QSPI, configuration/debug,
clocks and retained video resources simultaneously. The 400-row source inventory
has no assigned PCB nets and is not a pin-fit report. Decide optional FPGA→BT LVDS
physical reservation before PCB freeze; its renderer/capture can follow later.

Build a real representative BT renderer with pinned official library/HAL sources
and license. Use synthetic assets while game authority is missing, clearly labeled.
Measure the complete CPU-only and offloaded paths including transfer/wait costs;
the small bounds kernel may not warrant offload by itself. Recover authoritative
STRUTHIO source/trace before claiming game fidelity.

## Evidence and returns

Distinguish SELECTED, MANUFACTURER_DOCUMENTED, PLANNING_CALCULATED, HOST_TESTED,
RTL_SIMULATED, NATIVE_EDA_VERIFIED and PROTOTYPE_MEASURED. Software tests and raster
arithmetic do not establish screen cadence, speedup or hardware compatibility.
Keep measured fields null until real measurements exist. No fabrication release
is implied.

Retain real tool/IP versions, constraints, warnings, pin/bank/clock/resource/STA
reports and image lengths from native Efinity runs. Do not generate imitation
reports. Recheck source revisions and procurement. Raw-source hashes stay null
where only extracted text was available. Preserve third-party licensing; do not
redistribute proprietary tools/IP. Draft vendor questions as needed; external
messages require explicit owner authorization.

Every return should identify actual changes, executed commands, test evidence,
remaining gaps and the next concrete result. Update current decisions, task status
and manifests. Distinguish failed checks from checks unavailable for lack of tool
or hardware. Do not claim a complete FPGA design, bootable firmware, working game
or measured display without the corresponding artifact and evidence.
