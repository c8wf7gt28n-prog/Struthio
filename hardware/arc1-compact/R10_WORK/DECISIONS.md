# R10 decisions log

Owner instruction 2026-10-16: "Do what you think is best" — the four open decisions from `qa/R10_gate_report.md` were
delegated to engineering. Each is recorded with its reason and is reversible.

| # | Decision | Reason | Reversal cost |
|---|---|---|---|
| D1 | D213 ↔ 45F link = **D213 GMAC0 RGMII (pads PE0–PE15) ↔ 45F RGMII endpoint**, replacing the PBUS of R10 §4 | Full 16-bit PBUS (PD0–PD20) takes every D213 display output (R10_PINMUX_CONFLICTS.md); GMAC-1000M x2 is DOCUMENTED (D21x DS Table 3-2); PE has no conflict with video/boot/USB/debug; ~125 MB/s raw per direction with DMA vs ≈20 MB/s derived PBUS ceiling; reuses the simulated R8.5-C RGMII endpoint | 45F host interface only (raster core is transport-independent) |
| D2 | R10 governs over PRODUCT_VISION "no fourth programmable processor" and CLAUDE.md three-chip/BT820 | Owner delegated; R10 is the newest dated change-control document from the owner | none in RTL; documents only |
| D3 | 12F grade **−6** (LFE5U-12F-6TG144C) | closes timing on the proxy at −6 (seeds 1–5); authorised stock in the 2026-10-16 listing snapshot; −7 not stocked | LPF/P&R rerun at −7 (already passing) |
| D4 | TQFP144 pin-locked P&R stays NOT_RUN until Lattice Diamond/Radiant is available; same-PIO-site proxy used meanwhile | Trellis has no TQFP144 | — |

Consequences of D1: R10 §4.2 register map is carried as STATUS/counters inside the RGMII job protocol (as on the 12F);
the 45F needs a top-bank RGMII group (the R8.5-C 45F pin plan, bank 0, rxc on PCLKT0_0 B11, is reused); the D213 side
needs a bare-metal GMAC driver (Luban-Lite) — NOT_RUN.
Status after this pass: 45F `r10_raster_top` built and simulated end to end over RGMII (18/18 tiles bit-exact) and
routed pin-locked (5/5 seeds). Frame size under D1: whole-tile responses are 2092-byte (jumbo) frames; the engine also returns half tiles in
≤ 1066-byte standard frames, so D1 no longer depends on D213 jumbo support (at a cost: 173.5 vs 119.7 µs/tile
simulated, `d213/gmac_link/PLAN.md`).

## Fabrication-path decisions (owner approved 2026-10-16: "Approved")

Context: the owner cannot obtain development kits; the first hardware is the full board. Every unproven function must
therefore have an on-board fallback, and the first board is a bring-up prototype.

| # | Decision | Reason | Reversal cost |
|---|---|---|---|
| D5 | **Fit the D213 boot SPI NOR (SPI0, PB0–PB5) on prototypes**, plus a D213 USB0 recovery connector behind the power-off service disconnect. **F133 GPIOs drive D213 RESETN and PA0 (boot/upgrade pin) open-drain**, so the F133 can force USB download mode whether or not the D213 NOR holds firmware. Production keeps the single central NOR; the D213 NOR becomes DNP once F133-driven flashless boot is PROTOTYPE_MEASURED. | Flashless boot depends on reimplementing a closed host protocol and a closed DDR-init binary. With the D213 NOR fitted the D213 boots the vendor-standard way (AiBurn over USB0), so a flashless failure costs firmware time, not boards. D21x HW guide 2.2.4: blank media → USB burn mode; with firmware, PA0 low at reset → burn mode (sampled only at reset; PA0 is also UART0_TX). | Footprint already planned (DNP); BOM delta one SOIC-8 NOR + 2 pull-ups |
| D6 | **HDMI = TI TFP410 (DVI 1.0 transmitter) from D213 parallel RGB888 (PD0–PD27), strap-configured, into a type-A HDMI receptacle.** DVI video only; no HDMI audio (audio stays on the I2S/DSPK amplifiers). | Only bridge class with a complete public datasheet and no initialisation firmware (pin-strap mode). PD0–PD27 are free under D1 (GMAC0 on PE). RGB888 is the D21x-recommended LCD mapping (HW guide 2.4.6). | Video sheet only; I2C-capable bridge later if HDMI audio becomes a requirement |
| D7 | **The 45F forwards a 125 MHz clock to D213 GMAC0_CLKIN (PE3).** DNP footprints: 0R from the 45F RXCK net, and a 125 MHz 3.3 V oscillator. | GAP found while reading the D21x documents: the user manual documents RGMII only with an external 125 MHz MAC clock (UM 12.2.3.4; HW guide Table 2-8 PE3 ← PHY 125 MHz CLKOUT). The R10 plan had no source for PE3. | One 45F output pin + LPF/RTL change |

D5 refines interconnect decision 4: the prototype second flash is a recovery and bring-up path, not a disguise of the
cold-boot limit; independence is still defined as continued D213 operation after a successful boot.
