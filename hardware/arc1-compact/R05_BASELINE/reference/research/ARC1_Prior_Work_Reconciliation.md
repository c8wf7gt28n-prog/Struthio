---
title: ARC-1 — prior-work reconciliation and BT820 decision path
date: 14 October 2026
---

The four uploaded packages have now been reviewed as the available earlier engineering record. They contain a coherent Tabletop revision history, original FPGA package data, architecture reviews and working evidence-management software. They also show that **BT820B was already part of Tabletop R23**. The earlier F133/T35/BT820 recommendation in this conversation was made from the separate Compact handoff and must not be treated as a replacement for R23.

## Project scope and authority

| Item | ARC-1 Compact | ARC-1 Tabletop R23 |
|---|---|---|
| Authority supplied | ARC1_Handoff R0.2, 14 October 2026 | ARC1_R23_Handoff, 12 October 2026 |
| Locked scope | RISC-V processor, FPGA, distinct hardware 2.5D accelerator | Owner-selected F133-B, two T120F484I4 devices, tabletop HDMI/USB, memory/storage decisions |
| FPGA arrangement | Open; earlier recommendation uses one T35F400 | T120-A permanent GPU plus T120-B game-specific accelerator |
| BT820 role | Candidate main sprite/command renderer; optional FPGA video input | Selected evaluation target for capture and final composition of A's video |
| BT memory | MN820 prototype provides 128 MiB DDR3L; final memory open | Selected 64 MiB x16 LPDDR2; named candidate actually 128 MiB |
| Display | Panel, orientation and HDMI open | External HDMI; 720p60/1080p60 targets; no internal LCD |
| Storage | Open | Three dedicated 16 MiB NOR devices; separate SPI NAND games; no eMMC |

The newer date of the Compact handoff does not overwrite the separate Tabletop project. The supplied R23 instructions govern continuation of Tabletop; the Compact brief explicitly protects that separation. No owner-selected Tabletop parts, topology or capacities were changed in this review. The active project remains a clarification point in the conversation.

## What the packages preserve

| Package | Role and principal contribution |
|---|---|
| R19 FPGA pin audit | T120F484 plus T20F256 source-coordinate audit and provisional bank/signal plan |
| R22 Claude handoff | Dual-T120 Tabletop architecture and Project House continuation baseline |
| R22 DEV-002 | Evidence intake, provenance, conflict checks and expanded software tests |
| R23 engineering | Adds BT820 composition, three dedicated NORs, separate NAND and fourteen engineering gates; includes earlier source reviews |

All **180 file entries** were inventoried; there are **122 distinct byte contents**. The original packages remain unedited in `/workspace/arc1_import`. The full R23 DOCX body was extracted and its SHA-256 matches the supplied extraction record: `007186705ecdde8a22860b0c287a3baaeb622cf526f9c1b7b22f9ca66a9e0d2a`. The owner architecture diagram was inspected as a functional diagram.

R19's original sheets contain 484 unique T120 and 256 unique T20 coordinates. Its provisional mapping has 106 entries: 84 candidates, 20 reservations and two configuration-mode-TBD entries. Source consistency does not demonstrate bank, clock or electrical legality.

The same T120 workbook survives unchanged across R19/R22/R23. R22 and R23 preserve the same 968 A/B package records and clean unassigned CSV. Their connection-net fields are blank. Manufacturer resource counts and real ball coordinates are useful inputs, not a completed board netlist.

R22 handoff → DEV-002 preserves 22 files, changes nine and adds sixteen. DEV-002 → R23 preserves thirty, changes seventeen and adds forty-eight. Neither transition deletes files. R23 also references an intermediate R22 source-review delivery that is not among these uploads; its R23-only diff cannot be reconstructed solely from these four ZIPs. No Git commit was supplied.

## Current Tabletop architecture

**F133-B → candidate RGMII/SPI paths → T120-A → LVDS → BT820B → LVDS → IT6263N candidate → external HDMI.** T120-B connects directly to A through a separately qualified accelerator link.

F133 has private 64 MiB DDR2. Each T120 targets its own 128 MiB x32 LPDDR2. BT has a separately owned memory pool. A remains the programmable renderer; B remains game-configurable hardware; BT adds professional 2D/video composition. These roles differ from the Compact command-renderer proposal.

Retain the source research, independent-memory contracts, packet/fence/reset concepts, recovery strategy and immutable pin data. Retire T20, internal portrait LCD, eMMC and direct A-to-HDMI assumptions only as current Tabletop architecture; their historical artifacts remain useful records.

## BT820 findings that affect the next decision

**1. Capacity is unresolved, not merely mislabeled.** R23 targets 64 MiB BT memory and 384 MiB total. `AS4C64M16MD2A-25BIN` contains 64M x16 bits = 1 Gbit = **128 MiB**. Installing the named candidates produces **448 MiB** total. A software allocation limit cannot change installed capacity. This contradiction was already correctly identified in the R23 BT review and migration record.

**2. LPDDR2 needs an applicable current support contract.** The R23 review notes that current BT82X guide Table 5 lists DDR3/DDR3L presets without LPDDR2/512-Mbit entries. A further check found Appendix C of AN086 v1.4, printed page 286: the v1.2 change entry lists “LPDDR2 DRAM support” among removed items. This conflicts with the older DS v1.1 capability statement. It does not establish that the silicon cannot operate LPDDR2; it prevents assuming a supported present firmware/init path. Obtain the applicable silicon/firmware version and sanctioned initialization before choosing that memory. [Current BT82X guide](https://brtchip.com/wp-content/uploads/2026/09/BRT_AN_086_BT82X-Series-Programming-Guide-1.pdf)

**3. Standard HDMI timing is not established.** The reviewed documented clock choices do not generate 74.25 MHz, needed for standard single-link 720p60 and dual-link 1080p60. Using 72 MHz with standard totals gives approximately **58.18 Hz**. Manufacturer AN097 alternate-blanking examples provide a test path, but their listed totals conditionally calculate approximately 60.81/60.73 Hz. Actual register units, generated rate and monitor acceptance must be reproduced. This is a standard-timing gap, not proof that all usable HDMI timing is impossible.

**4. Both LVDS boundaries need real contracts.** Odd/even channels represent one video stream. The BT input does not supply per-pixel alpha. BT output clock pairs versus the ITE reference's shared clock, channel phase/mapping and exact N/FN bridge revision remain unresolved. Do not join driven clock outputs or copy an F576 development-board mapping to F484.

**5. Composition consumes memory traffic and latency.** A hypothetical four-pass RGB888 1080p60 model is 1.493 GB/s against an x16 LPDDR2-800 raw ceiling of 1.6 GB/s. The real pipeline may differ; this is neither a measured pass nor a measured rejection. Count changing input frames, overlays and presentation timestamps under load. Reserve the BT guide's upper 2.5 MiB DDR region before user allocations.

Primary local records: R23 `BT820_MEMORY_VIDEO_REVIEW.md` lines 7–25; `VIDEO_CHAIN_REVIEW.md` lines 23–65; `R23_ARCHITECTURE_DECISION_RECORD.md` lines 32–38. The newly noted guide change-history detail is recorded here without rewriting those supplied records. Guide review used web extraction; original downloaded guide bytes and their hash are not available in the uploads.

## What transfers to Compact, and what must be regenerated

- Reuse private-memory ownership, bounded queues, explicit transfers, CRC/epochs/fences, instrumentation and fault recovery.
- Reuse exact-package auditing and the requirement to compile all simultaneous interfaces in Efinity.
- Reuse the principle that recovery must remain reachable when user FPGA logic is absent or invalid.
- Regenerate all T35 pin/bank/clock/DDR work. T35F400 hardened DDR is x8/x16; the Tabletop x32 Alliance mapping and F484 resource counts cannot be ported directly.
- Rebuild the storage/control matrix. The earlier Compact SD0-boot/SPI0-mailbox proposal does not preserve R23's dedicated CPU NOR plus NAND without a new pinmux and ownership study.
- Adapt Project House's evidence schemas before applying them to Compact. Its existing validators are tied to the Tabletop dual-T120 topology.

## Verification performed in this review

| Check | Fresh result | Scope |
|---|---|---|
| R23 `npm test` | 112/112 passed | Software, including synthetic DOM/service-worker fixtures |
| DEV-002 `npm test` | 67/67 passed | Software regression |
| R23 package-facts script | All 484 F484 rows match workbook columns A–H | Manufacturer source-data consistency |
| Working manifests | R23 94/94 and DEV-002 46/46 entries match | Supplied byte integrity |
| Original R22 manifest | 30/30 entries match original package | Original supplied byte integrity |
| Architecture diagnostics | SOURCE_REVIEW_ONLY; fourteen OPEN gates | Correctly retains unresolved hardware status |

Reviewed scripts were run locally without source changes, network work or browser execution. Fresh logs and independent arithmetic are retained under `arc1_review/verification`. Original inherited manifests in later packages intentionally describe historical bytes and are not substitutes for their current working manifests.

No authentic Efinity project/STA export, HDL implementation or simulator trace, loadable firmware/bitstream, electrical CAD/ERC/DRC/SI, authoritative STRUTHIO build/renderer trace, or physical benchmark was found in these four packages. This describes the supplied archive, not all work that may exist elsewhere. Referenced U2/U3/U4 interconnect, OverDrive and DDR handoff documents are absent. These contents cannot be claimed as reviewed. All fourteen Tabletop hardware gates remain open.

## Recommendation after reconciling the prior work

**For Compact:** retain F133-B + T35F400 + BT820B as the leading exploratory combination. Start graphics evaluation on the manufacturer's 128 MiB DDR3L module. It avoids treating the unresolved R23 64 MiB LPDDR2 configuration as established. Use a mode actually supported by the prototype display, preserve the authoritative STRUTHIO rules, and benchmark the real scene before final part selection. If HDMI is selected, the end-to-end timing issue must also be addressed.

**For Tabletop R23:** continue the selected dual-T120 architecture. The next high-value work is a supported BT memory/init and complete video timing dossier, in parallel with independent full-interface A/B Efinity projects. A DDR3L module can investigate BT rendering/composition but cannot qualify the selected LPDDR2 channel. The manufacturer-reference **128 MiB DDR3L** arrangement is an engineering alternative worth evaluating if the owner revises BT memory; it would change selected total RAM to 448 MiB. It is not adopted by this review.

The common first proof is BT initialization and a deterministic standalone rendering scene with frame IDs, known alpha images, scripted motion and timestamps. **Tabletop R23 then requires a changing live-video source plus local BT overlays through its selected HDMI path. Compact can first qualify its command-rendered STRUTHIO scene without adopting live-video capture; that input path remains optional.** Add actual game load and concurrent FPGA traffic as each prototype is integrated. Record sustained unique frames, command/memory occupancy, repeated/dropped frames, latency and recovery. A graphics demo or software test cannot approve the final HDMI bridge, memory part or FPGA pin plan.

This review preserves the work already done and identifies the smallest useful next experiments. It does not freeze new parts, contact vendors or authorize fabrication.
