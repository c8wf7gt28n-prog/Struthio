# Manufacturing, stackup and BGA plan (R08 planning only; no PCB exists)

## 1. Stackup candidate (to be confirmed with JLCPCB's impedance calculator in R09)

SLIM4 R26 was ordered as JLC06121H-3313 (6 layers, 1.2 mm, ENIG, 1 oz outer / 0.5 oz inner, POFV via-in-pad). It is a
**comparison point only** (`SLIM4_REUSE_DECISIONS.csv`). Proposed starting point for ARC-1:

| Layer | Use |
|---|---|
| L1 top | F133, MN820 receptacle, T35, PSRAM, NOR; short SPI routes; LVDS breakout from the receptacle |
| L2 | solid GND reference for L1 |
| L3 | BGA escape signals, SPI0/SPI1, SD |
| L4 | power planes / pours: 3V3, VDD_CORE, 1V2_T35, 1V8_DRAM islands |
| L5 | GND |
| L6 bottom | regulators, decoupling under the BGA/QFP, buttons (enclosure-dependent) |

Board thickness, outline and component side are R09 decisions tied to the enclosure and the panel (D-07).

## 2. T35F400 (400 balls, 0.8 mm pitch, 20 × 20) breakout

- **Pad:** 0.40 mm NSMD in the generated footprint. The ball size and body size must be taken from the Efinix package drawing (not retrieved in R08).
- **Escape:**
  - Only 17 user I/O plus configuration and JTAG are used; most I/O balls are no-connect.
  - The used balls cluster in banks 1A–1D: rows A–K and T–Y on the left/right edges (pin table in `docs/PIN_TABLE_R08.md`).
  - Most can escape on L1 directly or with dog-bone vias.
- **Power balls:** the inner array needs vias.
  - VCC: 24 balls, H–P × 8–13.
  - GND: 45 balls.
  - VCCIO: 30+ balls.
  - A dog-bone with a 0.2/0.45 mm via on the 0.8 mm diagonal (1.13 mm) leaves (1.13 − 0.40 − 0.45)/2 ≈ 0.14 mm of clearance, compatible with a 0.1/0.1 mm process. Via-in-pad (POFV) is the alternative SLIM4 already used at JLC.
- **Decoupling:** Efinix decoupling recommendations were **NOT_FOUND** (the Hardware Design Checklist is behind the support login). R08 places 12 × 100 nF + 2 × 22 µF on 1V2_T35, 12 × 100 nF + 10 µF on 3V3_T35, and 3 × 100 nF + 10 µF behind the ferrite on VCCA. This is a placeholder until the Efinix PDN guidance or a PDN simulation exists (R09).
- **Unused banks:** all VCCIO balls are tied to 3V3_T35 (Interface Designer bank voltage 3.3 V). VCCIO_DDR floats and DDR_VREF goes to GND, as the T35 DS requires when DDR is unused.

## 3. F133 eLQFP128 (0.4 mm pitch, 5.72 mm EP)

- The EP carries ground (MangoPi practice; the datasheet does not state it: OPEN). It needs a thermal via array (R09).
- Fine-pitch QFP at 0.4 mm requires a stencil and the JLC fine-pitch capability check.

## 4. Route classes (R09 to turn into net classes)

| Class | Nets | Rule (preliminary) |
|---|---|---|
| LVDS (deferred panel) | MN820 LVDS_TX0/TX1 pairs | 100 Ω differential, length-matched within pair; recalculate on the final stackup (SLIM4 DSI method) |
| SPI1 BT820 | BT_SCK/MOSI/MISO/SS_N | ≤ 50 mm, series 33 Ω at the F133, ground reference continuous; target 30 MHz |
| SPI0 boot | SPI0_* and the T35 buffer stubs | NOR within 25 mm of the F133; buffers near the NOR to keep the T35 stubs off the strap nodes |
| PSRAM QSPI | PSRAM_SCLK/SIO/CE | ≤ 30 mm, matched ±2 mm, 22 Ω SCLK source termination |
| USB0 | USB0_DP/DM | 90 Ω differential, ESD at the connector |
| SD | SD_CLK (33 Ω), CMD, D0–3 | ≤ 60 mm, matched ±5 mm |
| Power | VBUS, 3V3, buck SW nodes | SW loops minimal (TI layout guide), 1 oz outer |

## 5. Assembly / DFM

- **Parts:** 329 schematic components; 96 BOM lines (`sourcing/BOM_CANDIDATES.csv`).
- **LCSC numbers:** only lines reused from the SLIM4 R26 BOM carry them (2026-10-07 snapshot; stock must be rechecked).
- **Sourcing to resolve in R09:**
  - F133-B, T35F400C3, APS6404L-3SQR-SN, W25Q256JVFIQ and W25Q32JVSSIQ: availability and lifecycle;
  - the MN820 module and its DF40C-100DS-0.4V(51) receptacle: consigned or global sourcing.
- **BGA:** X-ray inspection required (JLC offers it for BGA assemblies, checked on their capability page in R09).
- **NOR programming at assembly:** JLC programming service availability for this part is OPEN. The fallback is the first-article FEL or clip procedure (`RECOVERY_DOSSIER.md`).
- **Fabrication is NOT approved.** No layout, no DRC, no Gerbers.
