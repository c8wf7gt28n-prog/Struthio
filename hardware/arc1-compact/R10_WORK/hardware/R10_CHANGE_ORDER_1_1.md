# R10 change order 1.1: four-port, buttonless console

**Authority:** owner handoff `spec/ARC1_R10_Handoff_rev1.1.docx` (16 Oct 2026, SHA-256 in `spec/SHA256SUMS`).

**Decisions:** D8–D11 in `DECISIONS.md`. D8 supersedes D6.

**Status:** schematic updated and machine-checked; nothing here is measured on hardware. Fabrication: **HOLD**.

Evidence labels used below:

| Label | Meaning |
|---|---|
| DOCUMENTED | Stated in a vendor document; the reference is given. |
| DERIVED | Calculated from documented facts. |
| CONDITIONAL | Correct only if a named assumption holds. |
| OPEN | Not yet known or not yet verified. |
| NOT_RUN | Needs hardware or a tool that is not available. |

## 1. Connector map (handoff s1)

| Position | Connector (schematic) | Function | Check |
|---|---|---|---|
| Rear | USB-C, GCT USB4105 | 5 V input (auto-start); F133 USB0 device/FEL through the USB0 role mux (default position) | `crosscheck_r10` I: PASS |
| Rear | HDMI type-A, Molex 208658 | ADV7513 video + embedded stereo LPCM | PASS |
| Front | USB-A, Molex 67643 (through-hole shell) | Player 1: hub port 1, 0.5 A switched VBUS | PASS |
| Front | USB-A, Molex 67643 (reinforced) | Player 2 / game load: hub port 2, 0.5 A switched VBUS | PASS |

`cad/check/crosscheck_r10.py` section I enforces these rules automatically:

- **Exterior connectors:** exactly these four. A connector counts as exterior when its note starts with FRONT or REAR.
- **Switches:** none on the board.
- **Service pads and headers:** all DNP fixture features.
- **HDMI audio:** I2S from the F133 is actually wired to the HDMI transmitter.
- **USB roles:**
  - F133 USB0 goes only to the role mux.
  - F133 USB1 still reaches the D213.
- **eMMC:** wired to the F133.

Internal-only items (no case opening): JTAG headers for both FPGAs; DNP fixture pads for F133 reset, FEL (NOR reset), D213 reset and D213 boot (PA0); D213 recovery USB pads; UART headers.

## 2. USB topology and state table (handoff s2, s5)

The F133 USB0 role mux is TS3USB221A U(usb_host):
- **S = L** (10k pull-down: at every cold boot and whenever the F133 is in reset): F133 USB0 ↔ rear USB-C.
- **S = H** (F133 PD2): F133 USB0 ↔ USB2422 hub upstream.

The hub is held in reset by F133 PD3 (10k pull-down). Its downstream ports drive TPS2051C switches through PRTPWR (active high), and the switches report faults on OCS_N.

The internal F133 USB1 → D213 USB0 link is unchanged. Its own mux (default: F133) can switch to internal recovery pads only through an internal fixture jumper.

| State | Mux S | Hub | USB-A VBUS | Rear USB-C data | F133 role | D213 link | Notes |
|---|---|---|---|---|---|---|---|
| Power applied, F133 in reset | L (pull-down) | reset (pull-down) | off (PRTPWR pull-downs) | F133 USB0 | — | — | Deterministic; no firmware involved |
| Boot ROM, NOR invalid/blank | L | reset | off | F133 USB0 | **FEL device** | — | Firmware-independent recovery to a PC on rear USB-C. FEL fall-through: D1-H UM fig. (bench OPEN) |
| Boot ROM, fixture shorts FEL pads (NOR held in reset) | L | reset | off | F133 USB0 | FEL device | — | Forced recovery with a valid NOR, internal fixture only. OPEN until bench-proven |
| Loader: recovery request | L | reset | off | F133 USB0 | device (ARC-1 updater) | idle | Request sources: (a) persistent "recovery" flag; (b) the A/B trial counter exhausted (`firmware/f133_bootloader`); (c) rear USB-C partner is a PC data port (TUSB320 reports "default USB" current) — **heuristic, OPEN** |
| Normal: both controllers | H | running | on, 0.5 A limit each | **disconnected** | host via hub | host → D213 running | Simultaneous enumeration of P1 + P2 (USB2422 2-port, high speed) |
| Normal: thumb drive in Player 2 | H | running | on | disconnected | host, mass storage on port 2 | running | Player 2 controller absent unless an external hub is used (handoff s3) |
| Port overcurrent | H | port n off (hub OCS) | port n off | disconnected | host sees port-power fault | running | TPS2051C limits at 0.5 A ±20 % |
| Failed firmware (application) | — | — | — | — | A/B fallback, then golden (`r10_boot`) | — | Never erases the only working image |
| Restricted source (≤ 900 mA) | per firmware | port power withheld | **off** | — | — | FPGAs off | See section 5: only the processor core set runs |
| USB-C removed | — | — | — | — | power lost | — | Next connection is a cold boot. Storage writes are protected by section 4 |

Physical mutual exclusion: with S = H, the rear USB-C data pair is open-circuit at the mux. A PC on the rear port then sees no device, and nothing back-feeds: the board has no VBUS source to USB-C, J1 is sink-only, and the TUSB320 is in UFP mode.

## 3. HDMI audio/video compatibility report (handoff s2, s5)

| Item | Value | Evidence |
|---|---|---|
| Transmitter | ADI ADV7513BSWZ, HDMI 1.4 / DVI 1.0, LQFP-64 EP, −25…+85 °C; LCSC C408901: 87 pcs (16 Oct 2026) | DOCUMENTED: DS Rev. B |
| 720p60 pixel clock | 74.25 MHz (≤ 165 MHz) | DOCUMENTED (CEA-861) |
| D213 pixel clock | PLL_FRA2 (fractional, LCD/LVDS/DSI): 24 MHz × 49.5 = 1188 MHz, ÷16 = 74.25 MHz. VCO is within the recommended 720–1584 MHz | DERIVED: D21x UM 8.1.3.1 |
| Video bus | RGB888 4:4:4, separate syncs. D213 LCD_D[23:0] → ADV D[23:0] (pin order verified from glyph coordinates). R/B group swap and bit reversal are programmable on both sides | DOCUMENTED |
| Input timing | ADV7513 setup 1.8 ns / hold 1.3 ns. Clock/data phase programmable in 400 ps steps on the ADV7513; D213 has DCLK phase options; DNP RC footprint on DCLK | DOCUMENTED; margin NOT_RUN |
| Logic levels | ADV inputs 1.8–3.3 V (VIH 1.35 V, abs max 3.63 V); D213 VCC33_IO 3.3 V | DOCUMENTED |
| Audio source | F133 I2S2 (PB4 DOUT0, PB5 BCLK, PB6 LRCK) → ADV7513 I2S0/SCLK/LRCLK; game audio stays on the game-state owner | Pads DOCUMENTED (F133 DS Table 4-3) |
| Audio format | Stereo LPCM 48 kHz (baseline), 16-bit or 24-bit, standard I2S, BCLK = 64 fs = 3.072 MHz | ADV7513 supports I2S up to 192 kHz: DOCUMENTED |
| Audio clocking | No MCLK needed (DS features). HDMI audio clock regeneration: N = 6144 at 48 kHz; CTS = 74250 at 74.25 MHz (automatic CTS measurement) | DOCUMENTED (HDMI 1.4 / Linux `adv7511_audio.c`); bench NOT_RUN |
| F133 audio clock | 48 kHz family needs a 24.576 MHz-derived audio PLL | DERIVED; F133 audio PLL configuration OPEN (driver) |
| Initialization | D213 I2C2 (PA8/PA9, 2.2k pull-ups, ≤ 400 kHz) → main map 0x72 (7-bit 0x39, PD low at power-up). Sequence: ADI AN-1270 List 4 + Linux fixed registers (0x98=0x03, 0x9A=0xE0, 0x9C=0x30, 0x9D=0x61, 0xA2=0xA4, 0xA3=0xA4, 0xE0=0xD0, 0xF9=0x00), then audio N/CTS, I2S enable, HDMI mode, AVI/audio InfoFrames | DOCUMENTED (vendor app note + mainline driver) |
| DDC / EDID | ADV7513 DDC master (on-chip MPU reads the EDID) → TPD12S016 A side (internal pull-ups) → connector. HPD: TPD HPD_A → ADV HPD + D213 PA10 | DOCUMENTED |
| HDMI 5 V | TPD12S016 load switch 55 mA from VBUS_5V | DOCUMENTED (SLLSE96F) |
| ESD | TMDS/DDC/CEC/HPD through TPD12S016 | DOCUMENTED |
| R_EXT | 887 Ω 1 % to ground | **OPEN**: quoted from an index of the ADV7513 Hardware User's Guide; the guide itself was not retrievable here (analog.com refuses this environment) |
| CEC_CLK / INT output type / layout rules | CEC unused: CEC_CLK held low, 12 MHz oscillator DNP. INT: 10k pull-up | **OPEN**: same guide |

**Action for the owner:** download *ADV7513 Hardware User's Guide* (UG Rev. 0) and *ADV7513 Programming Guide* from analog.com and add them to `sources/adi/`. Those two documents close the three OPEN rows above.

## 4. eMMC and install/recovery plan (handoff s3)

**Part:** Samsung KLMAG1JETD-B041, 16 GB eMMC 5.1, 153-FBGA 11.5 × 13 mm, VCCQ = VCC = 3.3 V. LCSC C499919: 404 pcs (16 Oct 2026).

**Wiring:** F133 SMHC0 4-bit (PF0–PF5), RST_n on PF6. Pull-ups: CMD 10k, DAT0–3 47k. CLK has a 33 Ω series resistor. VDDi has a 1 µF + 100 nF regulator capacitor.

**Interface status: CONDITIONAL (gate).** Allwinner documents SMHC0 for SD memory and SMHC2 for eMMC. SMHC2 shares PC2–PC7 with the SPI0 boot NOR and the BOOT-SEL straps, so using it would put a bus switch into the only boot path; it was rejected.

SMHC0 drives the same 4-bit SDR 3.3 V bus that eMMC uses; only the identification sequence (CMD1) differs, and that is software. First-article test: CMD1/CMD2/CMD3/CMD7 identification, EXT_CSD read, 4-bit bus width, 25/50 MHz, then a 1 GiB write/read/verify.

**Fallback if the test fails:** eMMC cannot then be used on this board revision, and a respin moves it to SMHC2 behind a bus switch. Games would run from the 64 MiB NOR's free space only. This is the one change-order item that a respin could hinge on, which is why it is labelled CONDITIONAL rather than SELECTED.

| Store | Contents | Written by | Protection |
|---|---|---|---|
| 64 MiB SPI NOR (F133, BOOT-SEL 00) | Boot loader, golden F133 image, D213 images, FPGA golden/app bitstreams, manifests (`memory/R10_nor_partition.csv`) | Factory + validated updates | Golden partitions write-protected (block locks); A/B with trial counter; manifest generation counter |
| eMMC user area | Game library (packages + manifest), saves | Installer, from a front-port thumb drive | Package = manifest + payload + SHA-256. Copy into a staging area, fsync, verify the hash, then flip the library index atomically (two copies, generation counter, as the NOR manifest). An interrupted copy leaves the old index valid; the staging area is erased at next boot |
| eMMC boot partitions | Unused (BOOT-SEL 00 never reads SMHC0) | — | — |

**Buttonless rescue:**
1. A corrupt NOR makes the ROM fall through to FEL on rear USB-C; recovery is then done with the PC tool (`xfel`).
2. A healthy NOR but bad application: the A/B / golden fallback in the loader.
3. Forced FEL: internal fixture shorts the FEL pads.
4. D213: firmware is supplied by the F133 over USB; if needed, the D213 prototype boot NOR plus internal AiBurn pads (D5).

"Safe to remove" is shown over HDMI after the eMMC flush completes. A sudden unplug during a copy is recovered by the staging and index rules above.

## 5. Power (handoff s2): first-pass envelope, DERIVED, to be closed in analysis/R10_POWER_BUDGET.md

| Load | Estimate at 5 V input | Basis |
|---|---|---|
| Two USB-A ports | 2 × 0.5 A = 5.0 W (switch-limited) | TPS2051C limit |
| HDMI 5 V | 0.28 W (55 mA) | TPD12S016 |
| F133 + DDR2 | ~0.5–0.8 W | F133 DS (R8.5-C budget) |
| D213 | 0.53 W measured by the vendor on a 7-inch dev board | D21x HW guide 2.2.1 |
| ADV7513 | 0.26 W at 1080p typ (less at 720p) | DS Rev. B |
| 45F + SDRAM, 12F + PSRAM | **OPEN**: needs the Lattice power calculator with the routed designs | — |
| Hub, muxes, eMMC (active), NOR, glue | ~0.6 W | datasheets, typical |
| Total without FPGAs | ≈ 7.5 W from the 5 V input incl. regulator losses | DERIVED |

Policy:

| USB-C source current (TUSB320 report) | Allowed |
|---|---|
| 3.0 A | Everything |
| 1.5 A | Everything except one USB-A port's full 0.5 A while both FPGAs run (firmware enforces) |
| Default USB (≤ 900 mA, a PC port) | Processors only: USB-A ports and FPGAs off |

The rear port is **not** assumed to deliver 15 W (handoff s2). USB PD is not used: a fixed 5 V sink keeps the power path simple and deterministic.

## 6. Open items introduced or kept by this change order

| ID | Item | Closes with |
|---|---|---|
| CO-1 | ADV7513 hardware user guide / programming guide not read (R_EXT confirmation, CEC_CLK, INT type, layout) | Owner downloads the guides (section 3) |
| CO-2 | eMMC on SMHC0 | First-article test (section 4) |
| CO-3 | USB2422 and ADV7513 exposed-pad lands use KiCad candidate footprints | Vendor package drawings |
| CO-4 | FEL fall-through when the NOR is held in reset | Bench |
| CO-5 | Recovery-request heuristic on the rear USB-C (PC versus charger) | Bench + firmware |
| CO-6 | FPGA power numbers | Lattice power calculator |
| CO-7 | HDMI 720p60 picture + 48 kHz audio on an ordinary TV | First article |
| CO-8 | Mechanical envelope / circular diameter | KiCad PCB placement (`cad/pcb`, task H5) |
