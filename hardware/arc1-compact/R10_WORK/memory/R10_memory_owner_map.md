# R10 memory owner map (ARC1_MEMORY_R10 v0.1 §7.3 item 1)

Source: `spec/ARC1_MEMORY_R10.docx` (v0.1, 15 Oct 2026; sha256 in `spec/SHA256SUMS`). Capacities are the owner's
SELECTED targets; nothing here is measured on hardware. Rule (memory spec §1): **every RAM belongs to exactly one
domain; nothing is shared or coherent across domains; data moves only as explicit transfers.**

## Domains
| Domain | Reset source | RAM | Directly accessed by | Nonvolatile image source |
|---|---|---|---|---|
| F133-B | TPS3808 supervisor (R8.5-C U8) | 64 MiB DDR2 in package | F133 CPU + its DMA | NOR F1BT/F1RC/F1MA/F1MB, read by the boot ROM and loader |
| D213ECV | own supervisor (`hardware/R10_change_sheet.md` §4) | 128 MiB DDR3 in package | D213 CPU, GE, DE, GMAC/USB DMA | NOR D2FA/D2FB, sent by the F133 over USB — **flashless start UNPROVEN** |
| ECP5-45F | PROGRAMN/INITN, driven by the D213 | 32 MiB x16 SDR SDRAM (AS4C16M16SA family, candidate) + EBR | 45F SDRAM controller only | NOR C45G/C45A: F133 → D213 → 45F slave SPI |
| ECP5-12F | PROGRAMN/INITN, driven by the F133 | 4 MiB QSPI PSRAM (APS3204L family, candidate) + EBR | 12F PSRAM controller only | NOR C12G/C12A: F133 → 12F slave SPI |

Total working RAM 64 + 128 + 32 + 4 = **228 MiB**, distributed (not one address space). Block RAM is excluded.

## F133 DDR2 (64 MiB) — proposed map
| Range | Use | Notes |
|---|---|---|
| 0x4000_0000 + 0 .. 1 MiB | loader, stacks, NOR read buffers | the boot ROM's SRAM stage loads the loader; DDR2 init before anything else |
| + 1 .. 32 MiB | main firmware, game logic, audio state | |
| + 32 .. 48 MiB | game package cache from SD | |
| + 48 .. 56 MiB | **USB DMA window** (F133 → D213 graphics commands, D213 firmware download) | non-cacheable or explicitly cleaned/invalidated; EHCI descriptors here |
| + 56 .. 60 MiB | **EMAC DMA window** (F133 ↔ 12F RGMII jobs, R8.5-C `emac_d1`) | same rule |
| + 60 .. 64 MiB | NOR staging for streamed updates (one 64 KiB block at a time; never a whole 16 MiB image) | spec §4: updates stream into the inactive slot |
DDR2 base 0x4000_0000 is the D1/F133 DRAM base in the D1-H memory map (confirm in the F133 user manual); the split is a plan.

## D213 DDR3 (128 MiB) — proposed map
| Range | Use |
|---|---|
| 0 .. 16 MiB | graphics firmware (one D2Fx image ≤ 16 MiB) |
| 16 .. 24 MiB | display buffers: 3 × 1280×720×4 B = 10.5 MiB worst case → 8 MiB at RGB565, more if 32-bit |
| 24 .. 32 MiB | GE scratch surfaces, 2D layers |
| 32 .. 112 MiB | asset cache (sprites, textures, decoded game data) |
| 112 .. 120 MiB | **GMAC DMA window** (45F job/tile frames, decision D1) — non-cacheable or cleaned/invalidated |
| 120 .. 128 MiB | **USB device DMA window** (F133 commands, 45F bitstream staging: ≤ 3 MiB) |

## 45F SDRAM (32 MiB) and 12F PSRAM (4 MiB)
- 45F: textures, geometry lists, colour/Z working tiles beyond the on-chip tile buffers. Accessed only by the 45F
  controller (`rtl/ecp5_45f_sdram`). The D213 sends whole buffers (textures, descriptors) and receives tiles.
- 12F: work queues, lookup tables, intermediate results for F133 assist jobs; never a framebuffer.

## Transfers (the only ways data crosses a domain)
| From → to | Transport | Status |
|---|---|---|
| F133 → 12F, 12F → F133 | RGMII job frames (R8.5-C link) | RTL_SIMULATED + routed (`fpga12/`) |
| F133 → D213 | USB 2.0 bulk, `f133/graphics_link` | protocol HOST_TESTED; USB NOT_RUN |
| D213 ↔ 45F | **GMAC0 RGMII job frames (decision D1)** | RTL_SIMULATED + routed (`fpga45/`) |
| F133 → 12F config, D213 → 45F config | ECP5 slave SPI | F133 loader HOST_TESTED (R8.5-C `ecp5_cfg`); D213 side NOT_RUN |

## Conflict recorded
The memory spec (§1 table, §3.1, §7.1 gate "45F SDRAM + PBUS") assumes **D213 PBUS** between the D213 and the 45F.
It is dated 15 Oct 2026, the same day as R10 rev 0.1 and before decision D1 (16 Oct, delegated by the owner), and it
does not address the D213ECV PBUS/display pad conflict (`architecture/R10_PINMUX_CONFLICTS.md`). This pass keeps D1
(GMAC0 RGMII) and reads every "PBUS" in the memory spec as "the D213 ↔ 45F link". The memory decisions themselves
(capacities, ownership, one NOR) do not depend on which link is used.
