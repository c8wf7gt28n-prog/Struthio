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

## Change order: ARC1_R10_Handoff rev 1.1 (owner, 2026-10-16; spec/ARC1_R10_Handoff_rev1.1.docx)

Owner requirements (locked): exactly four exterior connectors (rear USB-C power/debug, rear HDMI video+audio, front
USB-A Player 1, front USB-A Player 2 / game load), no exterior buttons or switches, HDMI with embedded audio, new eMMC.

| # | Decision | Reason / evidence | Status |
|---|---|---|---|
| D8 | **ADI ADV7513BSWZ** HDMI 1.4 transmitter replaces the TFP410 (**supersedes D6**). D213 RGB888 (PD0-PD27) video, D213 I2C2 (PA8/PA9) configuration, PA7 INT, PA10 HPD, PA11 PD. **Audio = F133 I2S2 (PB4/PB5/PB6) -> ADV7513 I2S0/SCLK/LRCLK**, so game audio stays with the game-state owner. Own 1.8 V buck, three ferrite-filtered domains. TPD12S016 kept for ESD, DDC/HPD and the HDMI 5 V switch. | DS Rev. B: 165 MHz (720p60 = 74.25 MHz), 8-ch I2S up to 192 kHz, no MCLK needed, 1.8-3.3 V inputs, 5 V-tolerant DDC/HPD/I2C; init: ADI AN-1270 List 4 + Linux `adv7511` driver (`adi,adv7513`); LCSC C408901 87 pcs. | SELECTED; R_EXT 887 ohm from the HW user guide (quoted only), CEC_CLK / INT type OPEN until the guide is read |
| D9 | **F133 USB0 -> TS3USB221A role mux.** Default (pull-down, every cold boot, F133 in reset): rear USB-C device/FEL. F133 PD2 switches to a **USB2422 2-port hub** (strap mode, held in reset by F133 PD3) -> two **TPS2051C** 0.5 A switches -> two front USB-A. F133 USB1 stays the internal D213 link. The D5 D213 recovery USB-C becomes **internal fixture pads**. | Mutual exclusion is physical (one mux); recovery never depends on firmware choosing the port. USB2422 DS00001726A; TPS20xxC SLVSAU6I. | SELECTED; enumeration OPEN (bench) |
| D10 | **Samsung KLMAG1JETD-B041 16 GB eMMC 5.1 on F133 SMHC0 (PF0-PF5, 4-bit, 3.3 V), RST_n on PF6.** microSD removed. | F133 documents eMMC only on SMHC2, which shares PC2-PC7 with the SPI0 boot NOR and BOOT-SEL straps: rejected (would put a bus switch in the boot path). SMHC0 is an SD3.0 host; eMMC 4-bit SDR at 3.3 V is electrically identical, MMC init is software. BOOT-SEL 00 never tries SMHC0 (D1-H UM Table 3-5), so the boot path is unchanged. LCSC C499919 404 pcs. | **CONDITIONAL** (not documented by Allwinner for SMHC0): first-article test is a gate |
| D11 | **Buttonless.** All switches become DNP internal fixture pad pairs (F133 reset, FEL/NOR reset, D213 reset/boot). 13 game buttons removed (controllers are USB). **Speakers removed** (MAX98357A x2, no exterior opening; audio = HDMI only). **Owner confirmed 2026-10-16: "NO SPEAKERS".** | Handoff s1/s2. Auto-start on USB-C power is already the power-tree behaviour (bucks enabled from VBUS / PG_3V3). | SELECTED |
| D12 | **Owner, 2026-10-16: "eMMC isn't needed if games can be played off a top USB-A that acts as our game cartridge."** Front = 2x USB-A controller ports; **top = third USB-A, the game cartridge; games run directly from the USB drive.** eMMC removed (**supersedes D10**; F133 PF0-PF6 freed). Hub changed to **Microchip USB2514B-I/M2** (4-port; port 4 disabled by strap) with three TPS2051C 0.5 A port switches. This amends the handoff's "exactly four exterior connectors, no top socket" rule: five exterior connectors now. | Removes the one CONDITIONAL interface (eMMC on an SMHC that Allwinner documents for SD only). USB2514B: DS00001692C Table 3-1/5-1; LCSC C220679, 6767 pcs (2026-10-16). Same USB 2.0 high-speed path for controllers and cartridge; no new F133 interface. | SELECTED |
