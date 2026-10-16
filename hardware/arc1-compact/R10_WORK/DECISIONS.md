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
