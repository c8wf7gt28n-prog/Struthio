# ARC-1 Compact — continuation authority

Read this file, `OWNER_SELECTION.md`, the full current handoff and `engineering/architecture.json` before work.

## Active scope and authority

Continue the owner-selected **Compact** core: **Allwinner F133-B + Efinix T35F400C3 + Bridgetek BT820B + built-in display**. RAM target: **64 MiB internal CPU DDR2 + 128 MiB FPGA-private x16 DDR3L + 128 MiB BT-private DDR3L = 320 MiB installed**. Use MN820 for the initial BT implementation. Confirm the named Newhaven NHD-7.0-1024600AF-LSXP panel.

Authority order: latest owner instructions → this selection/current decision register → original Compact R0.2 handoff → supporting recommendation/reconciliation research → applicable historical Tabletop facts. Current instructions override older “all parts/memory open” wording for the selected Compact core and RAM targets.

Tabletop R19/R22/R23 is separate history. Its dual T120s, x32 LPDDR2, 384/448 MiB totals, three 16 MiB NORs, mandatory NAND and external HDMI do not become Compact requirements. Do not modify or rebrand that project. Preserve original attachments byte-identically.

## Confirm and continue

Use `engineering/tasks.json` as the work queue. Begin with independent primary-document confirmation and the display/memory worksheets; then prepare the representative BT renderer, scene protocol and exact T35 project. Missing game source or bench hardware does not prevent a clearly labeled synthetic workload, timing model, protocol specification or useful source implementation.

Keep the selected core while qualifying supporting parts and interfaces. Do not ask the owner to repeat the selection. Report genuine conflicts with exact evidence, consequences and a minimal remedy; continue independent work. Exact RAM SKUs, storage, pin allocation, screen orientation, power/audio and numeric implementation details remain engineering choices to resolve.

Initial topology is proposed: F133 → SPI scene mailbox → T35 transform/command processing → QSPI → BT820 → LVDS panel. Start single-bit CPU SPI and qualify quad separately. The FPGA is the sole BT host master. Calculate a useful fixed-point transform/culling kernel; measure its benefit including transfer and wait time. T35 LVDS → BT capture is optional future expansion, not a prerequisite for the first command-rendered scene. Decide its physical routing/resource reservation before PCB freeze so the fixed-board development goal is preserved. Produce a real bootable F133 firmware/BSP and SPI/HAL build, with pinned sources/toolchain and actual boot/transport evidence when hardware is available.

## Evidence rules

Separate SELECTED DESIGN, MANUFACTURER DOCUMENTED, PROPOSED IMPLEMENTATION, EDA VERIFIED, PROTOTYPE MEASURED and MANUFACTURING RELEASED. Arithmetic, declarations, hashes, synthetic tests and advertised resolutions do not establish hardware performance. Keep measured fields null until real measurements exist. This handoff's numerical checks are planning arithmetic.

Produce native T35F400C3 Efinity projects/reports only when the actual tool is run; retain tool/IP versions, constraints, warnings, pin/bank/clock reports, STA and actual loadable images. Never substitute a T20/T120 compilation or package inventory. Check F133 SPI0 boot-select sharing, safe high impedance and independent recovery when FPGA logic is invalid.

Recheck source revisions and actual sourcing. Do not inherit the Tabletop BT LPDDR2 assumption; Compact selects DDR3L. A 1-Gbit x16 device is 128 MiB. The exact FPGA DRAM remains unselected; do not default to an expensive old SKU simply because its geometry fits.

Use primary sources in `engineering/sources.json`, archive permitted versions and record provenance. Downloaded-original hashes must remain null when only web extraction exists. Preserve third-party licensing; do not redistribute proprietary tools/IP. Draft vendor questions when necessary; sending messages requires explicit owner authorization.

## Every continuation return

Lead with confirmed facts, actual changes and the next concrete result. List changed files, executed commands/tool versions, generated or measured artifacts, unresolved issues and source IDs. Distinguish unavailable checks from failed checks. Keep the final handoff and decision register current. Do not claim a hardware pass, working game port, real-browser check or fabrication-ready PCB without the corresponding evidence.
