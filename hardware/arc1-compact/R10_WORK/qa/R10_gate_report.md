# ARC-1 R10 gate report — first engineering pass

Spec: `spec/ARC1_R10.docx` (R10 rev 0.1, 15 Oct 2026, sha256 in `spec/SHA256SUMS`). Fabrication: **HOLD** (R10 §10.2).
Evidence labels: DOCUMENTED (vendor states it), DERIVED (our calculation from documented data), LISTING_SNAPSHOT
(distributor page at a time), HOST_TESTED, RTL_SIMULATED, OPEN_TOOLCHAIN_ROUTED, NOT_RUN. No confidence scores.

## Gates

| Gate | Work item | Status | Evidence |
|---|---|---|---|
| R10-A | Freeze parts and topology candidates | **PARTIAL — HOLD condition found** | `architecture/sources/` (Lattice ECP5U-12 pinout FPGA-SC-02032 v2.1; D213ECV pin table from the ArtInChip D21x pin-multiplex page; `sources.json` with URL/revision/sha256 for 54 sources), `architecture/R10_interface_matrix.csv` (65 rows, generated), `architecture/R10_PINMUX_CONFLICTS.md` |
| R10-B | 12F RGMII isolation and P&R | **PASS on the 12F die (proxy package); TQFP144 pin-locked P&R NOT_RUN** | `fpga12/` — `make lint rgmii sim build seeds report`: lint clean; RGMII unit TB PASS; system TB `R10_12F_TB_PASS`; `timing/R10_12F_FIT_TIMING.md`: LUT 40.8 %, EBR 25 %, MULT 28.6 %, PLL 2/2; 10/10 runs (seeds 1–5 × speed −6/−7) meet 80/125/125 MHz |
| R10-C | 45F stand-alone triangle + Z RTL | **PASS in RTL simulation and open-toolchain P&R** (host link = RGMII per D1, not PBUS) | `fpga45/` — `make ref sim seeds sim45 seeds45`: C model + coverage check 0 violations; core RTL == C on 18 522 words (18 tiles, 62 triangles); 4/4 RTL mutants killed; **`r10_raster_top` (RGMII endpoint + RJOB/RRES engine) system TB `R10_45F_TB_PASS`**: all 18 tiles bit-exact over RGMII both as whole tiles (2092-byte jumbo frames) and as half tiles (≤ 1066-byte standard frames), CRC'd responses, truncated command → status 5 without wedging the engine, corrupted payload rejected (status 4) with the next tile still exact, bad opcode/length, STATUS counters, loopback; **pin-locked LFE5U-45F-6 CABGA381 P&R 5/5 seeds**: sys 90.8–95.9 MHz (80), eth TX 151–160 MHz (125), RGMII RX 157–176 MHz (125); 16 % LUT, 10 EBR, 16 MULT, 2/4 PLL; core alone 96.5–104.0 MHz |
| R10-D | D213 standalone bare-metal video | NOT_RUN | plan with pass criteria: `d213/boot_and_display/PLAN.md` |
| R10-E | D213 ↔ 45F throughput | NOT_RUN on hardware; 45F side simulated | `d213/gmac_link/PLAN.md`: simulated round trip 119.7 µs/tile with jumbo frames (≈ 9.0 ms of 16.7 ms for 75 tiles) or 173.5 µs/tile with standard frames (≈ 13.0 ms), both before D213 driver cost; D213 GMAC jumbo support UNVERIFIED |
| R10-F | F133 ↔ D213 command pipeline | protocol HOST_TESTED; transport NOT_RUN | `f133/graphics_link/` — `make all`: 45 checks pass, ASan/UBSan clean, freestanding compile, 7/7 mutants killed (lost/corrupt/stale packets, device restart, dead link → fallback + reprobe, D213 watchdog). USB host/device stacks NOT_RUN |
| R10-G | Integrated 2D + low-res 3D scene | NOT_RUN | — |
| R10-H | Fabrication release | **HOLD** | §10.2 criteria 1 (pin conflict, option A) and 5 (D213 procurement unconfirmed) are currently met |

## R10-A findings

1. **D213ECV PBUS and display share pads (DOCUMENTED pads; DERIVED conflict).** The only full 16-bit PBUS group is
   PD0–PD20 (AD0–AD15 = PD0–PD15, CLK PD16, NCS PD17, NADV PD18, NWE PD19, NOE PD20). These pads also carry LCD_D0–D20,
   all of LVDS1 (PD8–PD17) and LVDS0/DSI lanes 0–1 (PD18–PD20); LVDS0/DSI need PD18–PD27, parallel RGB PD0–PD27.
   A full PBUS leaves **no display output**. The PF alternative carries only AD0–AD11 (PF11 = AD11 or CLK).
   → R10 §10.2 hold criterion 1 is met for the link "D213 PBUS ↔ 45F" as written.
2. **D213ECV has two 1000M GMACs (DOCUMENTED: D21x Datasheet EN v1.4 Table 3-2 "GMAC-1000M x2"; "Two GMAC with
   selectable 100M RMII/1000M RGMII").** GMAC0 is on PE0–PE15 (VCC33_IO0), GMAC1 on PF0–PF15 (VCC33_IO1). GMAC0 shares
   no pad with display (PD), boot SPI NOR (PB0–PB5), SD (PC), debug UART0 (PA0/PA1) or USB (PU0–PU3).
3. **PBUS throughput (DOCUMENTED parameters, DERIVED ceiling):** single AHB accesses only, no burst; default timing
   TH_CS 8 + TD_CS 2 ≥ 10 PBUS clocks per 16-bit access ⇒ ≈ 20 MB/s at a 100 MHz PBUS clock versus the "100 MB/s"
   marketing figure. R10 §5.1 needs ≥ 9.2 MB/s for 320×240 RGB565 at 60 Hz before any command upload. No measured figure
   exists (R10 Q4 open).
4. **LFE5U-12F-7TG144C exists** (DOCUMENTED, DS-02012 ordering table). TQFP144 bonds PCLKT0_0 (pin 128, top bank 0)
   and every bonded bank has its own VCCIO pin (pinout v2.1; DS-02012 p.98 disagrees on TQFP144 power-pin counts —
   the pinout file governs). Quad SPI configuration is not available on TQFP144 (D2 not bonded).
5. **F133 USB1 is a separate USB 2.0 host with its own PHY** (DOCUMENTED, F133 DS rev 2.3 §2.10; pins 112/113);
   D213 USB0 is device-capable (pins 79/80) and is also D213's USB upgrade/recovery port.
6. **Procurement (LISTING_SNAPSHOT ~2026-10-16 00:05 UTC, not a supply confirmation):** LFE5U-12F-7TG144C — DigiKey not
   stocked (40-week lead time), independent brokers list stock; LFE5U-12F-6TG144C — DigiKey 148 in stock. **D213ECV —
   no listing found** (DigiKey, findchips; artinchip.com offers a sample-request form). Mouser/Arrow/Octopart/LCSC
   search were blocked to automated access.

## Other R10 §12.1 outputs
| Item | Path | Status |
|---|---|---|
| 5 D213 boot and display | `d213/boot_and_display/PLAN.md` | plan, NOT_RUN |
| 6 D213 PBUS driver | `d213/pbus_driver/README.md` → `d213/gmac_link/PLAN.md` (D1) | plan, NOT_RUN |
| 7 F133 graphics link | `f133/graphics_link/` | protocol HOST_TESTED; USB NOT_RUN |
| 8 Hardware change sheet | `hardware/R10_change_sheet.md` | delta + open items; power budget NOT_RUN |

## R10-B notes
- Provenance: `fpga12/PROVENANCE_R85C_0defcfe.sha256` holds the R85C hashes; `sha256sum -c` passes for every copied
  file except `rtl/accel_engine.sv`, which is intentionally modified (HAS_FIR parameter, STATUS opcode).
- Built from R8.5-C RTL as reference only (R10 §6.3): RGMII MACs and job link unchanged; SPI mailbox, PSRAM and power
  guard removed; engine with `HAS_FIR = 0` (the 32-lane FIR needs 32 MULT18X18D > 28) and a new STATUS opcode 0x10
  (interface revision, caps, six RGMII counters, jobs/items, uptime; CRC-protected).
- Toolchain limit: Project Trellis has no TQFP144 package; P&R used caBGA256 balls that bond **the same PIO sites** as
  the planned TQFP144 pins (`timing/r10_12f_proxy256.lpf`). Package parasitics are modelled in neither case.
  Pin-locked TQFP144 P&R needs Lattice Diamond/Radiant — NOT_RUN.
- `nextpnr --12k` uses the 25F die database (56 EBR); utilisation is computed against the 12F datasheet limits.
- Pad-level RGMII timing: same GDDRX1 figures as the 45F (DS-02012 Table 3.22, all devices); budget and delay-chain
  calibration in `R85C_WORK/docs/RGMII_LINK_R85C.md` — CONDITIONAL until bench.
- Speed grade: −6 and −7 both close; −6 is the grade with authorised stock in the snapshot.

## R10-C notes
- Step 1 of R10 §7.1 (items 2–3): flat triangles, signed edge functions, top-left fill rule, tile Z (16-bit, strict
  less-than), 32×32 tiles in EBR, CRC'd tile output. Job format and arithmetic: `fpga45/tools/raster_ref.c` (tile
  origin 0..2016 px). Throughput: 1 sample/clock over bbox∩tile; setup ≈ 80 clocks/triangle; clear 1024 clocks;
  output 4 clocks/word (not optimised). Not yet: textures, perspective, tile queues, two tiles in flight.
- Host transport (decision D1): `rtl/r10_raster_top.sv` = the R8.5-C RGMII endpoint (`fpga12/rtl/eth_link.sv` etc.,
  byte-identical to R85C 0defcfe) + `rtl/r10_raster_engine.sv` (RJOB/RRES: header + payload CRC checked before
  anything reaches the rasterizer; STATUS opcode 0x10 "R10G"; non-RJOB frames looped back for delay calibration).
  Pins = the R8.5-C 45F bank-0 RGMII balls (`constraints/r10_45f.lpf`), rxc on PCLKT0_0 B11.
- A whole-tile response frame is 2092 bytes (jumbo). Opcodes 2/3 return a tile in two standard frames (≤ 1066 bytes)
  so the link works without jumbo support (`d213/gmac_link/PLAN.md` item 1).
- Robustness fix found by the new tests: a job ending inside a command used to leave the rasterizer waiting for
  arguments forever (the 45F stopped answering). The rasterizer now has an `abort` input (argument phase only) and
  the engine returns status 5.
- Pad-level RGMII timing CONDITIONAL, as for the 12F; D213 GMAC delay controls UNVERIFIED.

## Mandatory questions (R10 §14)
| Q | Answer from this pass |
|---|---|
| Q1 D213ECV supplier/lot | **Open.** No distributor listing found; ArtInChip sample request required. |
| Q2 D213 pins for boot + USB device + PBUS + video | **No** for full 16-bit PBUS + any video (finding 1). Boot SPI NOR (PB0–5), USB0 (PU0/1), UART0 (PA0/1), LVDS0 (PD18–27) + GMAC0 (PE) coexist in the generated matrix. |
| Q3 12F RGMII timing with DDR I/O and margin | Core timing: yes (10/10 runs, proxy package). Pad-level: CONDITIONAL (budget + bench calibration). TQFP144 pin-locked: NOT_RUN. |
| Q4 Measured D213 PBUS read bandwidth | NOT_RUN (no hardware). Derived ceiling ≈ 20 MB/s at default timing. |
| Q5 45F graphics-memory interface for textures | Open (step 4 of §7.1 not started; 8 MiB QSPI PSRAM not frozen). |
| Q4' (D1) D213 GMAC RGMII throughput | NOT_RUN; 45F side ≈ 120 µs/tile simulated, wire 16.9 µs/tile derived. |
| Q6 D213 video + 2D with both FPGAs blank | Open (R10-D, hardware). Pin plan keeps video independent of both FPGA links. |
| Q7 Exact tool/SDK revisions | Yosys/nextpnr-ecp5/Trellis as recorded in R85C build TOOL_VERSIONS; Icarus/Verilator as installed; D213 SDK not used. |

## Decisions (delegated by the owner 2026-10-16, "Do what you think is best")
Recorded in `DECISIONS.md`: **D1** D213 ↔ 45F over D213 GMAC0 RGMII; **D2** R10 governs over the earlier three-chip
rules; **D3** 12F −6 grade; **D4** TQFP144 pin-locked P&R waits for Lattice tools. The original option text follows.

### Options as first presented
- **D1 — D213 ↔ 45F transport.** (a) Keep PBUS: requires a different video path (none left on D213ECV) or a different
  D21x package/part — contradicts R10 §3.1 "D213 boots and shows 2D with both FPGAs blank" only if video moves to an
  FPGA. (b) **Use D213 GMAC0 RGMII (PE) ↔ 45F RGMII endpoint** (recommended for evaluation: pads free of video/boot/USB,
  ~125 MB/s per direction raw with DMA, reuses the simulated R8.5-C endpoint; needs a 45F top bank and the D213 GMAC
  driver). (c) PBUS on PF (12-bit only) — not viable for a 16-bit A/D protocol.
- **D2 — supersession of standing owner rules.** PRODUCT_VISION "no fourth programmable processor" and CLAUDE.md
  three-chip/BT820 direction vs R10's four programmable devices (see `BASE.md`).
- **D3 — 12F speed grade:** −6 closes timing on the proxy and has authorised stock in the snapshot; −7 does not.
- **D4 — tool access for TQFP144 pin-locked P&R** (Lattice Diamond/Radiant) before the 12F footprint is frozen.
