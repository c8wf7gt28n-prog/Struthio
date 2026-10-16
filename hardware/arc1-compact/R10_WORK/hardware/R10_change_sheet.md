# R10 hardware change sheet (R10 §12.1 item 8) — delta from the archived R8.5-C board

Baseline: `R85C_WORK/cad/gen/design.py` (R8.5-C, commit 0defcfe; frozen). Fabrication: **HOLD**. No schematic has been
drawn for R10; this sheet lists what the schematic pass must change. Labels: DOCUMENTED / DERIVED / SELECTED /
OPEN / NOT_RUN.

## 1. Netlist delta
| R8.5-C item | R10 | Status |
|---|---|---|
| J3 MN820 receptacle (BT820B + 128 MiB DDR3L), U17 MISO buffer, J4 SPI1 header, U11 3V3_MN switch, H5/H6 | **removed** — graphics moves to D213ECV (R10 §2) | SELECTED |
| — | **D213ECV (QFN128)** + boot SPI NOR (PB0–PB5) + 24 MHz crystal (frequency per D21x DS — OPEN) + UART0 header + USB0 to F133 USB1 + LVDS0/RGB to HDMI bridge | SELECTED part; procurement OPEN (gate A) |
| — | **HDMI bridge** (LVDS or RGB input) | OPEN — not selected (R10 §3) |
| U18 LFE5U-45F-6BG381C: bank-0 RGMII to F133 PG0–PG12 | 45F bank-0 RGMII (same balls B11/C10/B9/C9/D10/E10 in, C8/D9/E9/D8/E8/C7 out) now to **D213 GMAC0 PE0–PE15** | SELECTED (D1); 45F side routed in P&R |
| U18 configured by the F133 over SPI0 (slave SPI, CFG=001) through U21–U24 isolation buffers | 45F needs its **own configuration flash** (master SPI) + JTAG (R10 §4 "each FPGA config: separate power-on bitstream path"); F133 SPI0 isolation buffers no longer needed for the 45F | SELECTED; flash part OPEN |
| U25 APS6404L 8 MiB QSPI PSRAM on the 45F | kept as the texture-memory candidate; R10 Q5 open | OPEN |
| — | **LFE5U-12F-6TG144C** (decision D3) + config flash + JTAG + 25 MHz oscillator; RGMII to **F133 PG0–PG12** (the R8.5-C F133 pin plan; 22 Ω series resistors kept on F133 outputs) | SELECTED; pins in `fpga12/timing/r10_12f_tqfp144.lpf` |
| F133 USB1 DP/DM unused ("removed, D-04") | **F133 USB1 host → D213 USB0 device** (graphics command link) | SELECTED (R10 §5.1) |
| F133 USB0 device (Type-C J1, TUSB320) | unchanged — console USB / FEL recovery | — |
| U9/U10/U30 FPGA rails (1V1, switched 3V3, 2V5 aux) for one ECP5 | rails for **two** ECP5s (see §2) | OPEN sizing |

## 2. Power budget
| Rail | Loads (R10) | Figure | Label |
|---|---|---|---|
| 5 V VBUS | everything | ≤ 3 A from USB-C if the source advertises it (TUSB320 current detection, R8.5-C) | DOCUMENTED (R8.5-C) |
| 3V3 | F133 IO, D213 IO (VCC33_IO0/1), both FPGA VCCIO, NOR ×3, PSRAM, HDMI bridge IO | sum NOT_RUN | NOT_RUN |
| 1V1 ×2 (ECP5 core) | 45F, 12F | needs the Lattice Power Calculator with the routed designs (Diamond) | NOT_RUN |
| 2V5 ×2 (ECP5 VCCAUX) | 45F, 12F | small; LDO per FPGA as R8.5-C U30 | DERIVED topology |
| D213 core / DDR3 rails | D213ECV | from the D21x hardware design guide — not yet read | OPEN |
| F133 core / DRAM | unchanged | R8.5-C U5/U6 | DOCUMENTED (R8.5-C) |

The 5 V input budget cannot be closed until the D213 and ECP5 figures exist; this is a gate-H item (R10 §10.2,
E03 power).

## 3. Clocks
| Clock | Source | Consumers |
|---|---|---|
| 24 MHz | Y1 crystal (R8.5-C) | F133 |
| D213 reference | own crystal (frequency per D21x DS) | D213 |
| 25 MHz | X1 oscillator (R8.5-C) | 45F PLLs: sys 80 MHz, RGMII TX 125 MHz |
| 25 MHz | new oscillator | 12F PLLs: sys 80 MHz, RGMII TX 125 MHz |
| 125 MHz RGMII | F133 EMAC TXCK → 12F PCLKT0_0 (pin 128); D213 GMAC0 TXCK → 45F PCLKT0_0 (B11) | RX clocks |

## 4. Reset and power-up sequence (proposed; each step has a pass check on the bench)
1. 3V3 good (TPS3808, R8.5-C U4) → F133 reset released (U8).
2. D213 reset released by its own supervisor at the same time as the F133 — **not** by the F133 — so D213 video
   comes up with both FPGAs blank and with the F133 halted (R10 §3.1).
3. Each FPGA loads from its own flash at power-up (configuration time to be measured on the bench).
   The F133 (12F) and D213 (45F) only enable their RGMII pin mux after reading DONE (IO-disable before, mirrors
   R8.5-C rule `rgmii_link`).
4. F133 enables USB1 VBUS to the D213 after D213 firmware asserts "ready" (GPIO or USB attach) — sequencing of USB0
   recovery mode in `f133/graphics_link/README.md`.

## 5. Memory / converter BOM delta
| Add | Remove |
|---|---|
| D213ECV (128 MiB DDR3 in package) | MN820 module (BT820B + 128 MiB DDR3L) |
| SPI NOR for D213 boot | — |
| SPI flash for 45F config, SPI flash for 12F config | F133→45F slave-SPI isolation (U21–U24), if no other use |
| LFE5U-12F-6TG144C + 25 MHz oscillator | — |
| HDMI bridge (OPEN) + HDMI connector | LVDS panel connector of R09 (if the panel path is dropped — OPEN) |
