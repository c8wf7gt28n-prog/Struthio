# R8.5-C RGMII job link — board connection, timing budget, power-state rules

Status: PLANNING_CALCULATED + RTL_SIMULATED (FPGA side). Nothing here is measured on hardware.
Sources: F133 DS rev 2.3 (sha256 59d743fa…69b2) Table 4-3 (pin functions) and Table 5-21 (RGMII timing);
ECP5 DS FPGA-DS-02012 rev 3.4 (sha256 26570f8b…93c3) Table 3.5 (hot socketing) and Table 3.22 (generic DDRX1 I/O);
D1-H User Manual v1.0 (EMAC delay chains ETXDC/ERXDC; same EMAC as F133).

## Why RGMII
The F133 EMAC (10/100/1000, RGMII/RMII, DMA) talks straight to the ECP5 with no PHY: a raw-frame,
point-to-point link of about 125 MB/s each way with DMA, separate from SPI0 (boot NOR + ECP5 configuration).
Single-bit SPI remains for configuration, DISCOVER and control. Frames: EtherType 0x88B5, payload = len16 LE +
an unchanged AJOB request / ARES response (fpga_ecp5/rtl/eth_link.sv).

## Connection (generated: board/F133_PINMUX_MATRIX_R85.csv, board/ECP5_BALL_MAP_R85.csv, LPF)

| Signal | F133 pin (F4) | Driver | Series 22R at | ECP5 ball (bank 0) | RTL port |
|---|---|---|---|---|---|
| TXCK | PG3 (pin 121) | F133 | F133 | B11 PCLKT0_0 | rgmii_rxc |
| TXD0..3 | PG4, PG5, PG6, PG7 | F133 | F133 | C10, B9, C9, D10 | rgmii_rxd[0..3] |
| TXCTL | PG12 (pin 124) | F133 | F133 | E10 (+100k pull-down) | rgmii_rx_ctl |
| RXCK | PG10 (pin 5) | ECP5 | ECP5 | C8 | rgmii_txc |
| RXD0..3 | PG1, PG2, PG8, PG9 | ECP5 | ECP5 | D9, E9, D8, E8 | rgmii_txd[0..3] |
| RXCTL | PG0 (pin 120) | ECP5 | ECP5 | C7 (+100k pull-down) | rgmii_tx_ctl |

PG11 (EPHY-25M) is unused; no MDC/MDIO (no PHY). The 13 buttons moved from PG0–PG12 to PD2–PD9, PD14, PD15, PD22,
PB2, PB3 (every one has an EINT function, F14). Checked by board rule `rgmii_link` (7 negative tests).

## Layout rules (for C3 layout / R09; not yet done)
- Route the 12 signals as one group on one reference plane, no plane splits, F133 and ECP5 placed close.
- Length-match each direction's data/CTL to its clock within ±10 mm (≈ ±65 ps); no deliberate clock skew (the F133
  delay chains provide it). Keep both directions short (target < 50 mm).
- Series resistors within 5 mm of the driving pin (the netlist encodes this only as the resistor note; rule
  `rgmii_link` checks the note names the driver).

## Timing budget (analysis/electrical_margins_r85.py, docs/ELECTRICAL_MARGINS_R85.md)

| Direction | Driver guarantees | Receiver needs | Margin | Status |
|---|---|---|---|---|
| F133 → ECP5 | setup/hold ≥ 1.2 ns (TsetupT/TholdT, transmit delay on) | 0.52/0.52 ns (GDDRX1_RX.SCLK.Centered, PCLK) | 0.53 ns each, after 0.15 ns skew | CONDITIONAL |
| ECP5 → F133 | edge-aligned, invalid ±0.3 ns around each edge (GDDRX1_TX.SCLK.Aligned) → 3.4 ns valid per half cycle | 1.0 + 1.0 ns (TsetupR/TholdR, receive delay on) | 0.5 ns after skew and ±0.3 ns centring | CONDITIONAL |

CONDITIONAL because the board skew (no layout) and the ERXDC centring residual are assumptions, and because the ECP5
numbers are Lattice's characterised generic-DDR paths while nextpnr does not time the pads (risk RK-RGMII-IO-TIMING).
Closure: per-board delay-chain calibration — firmware sweeps ETXDC/ERXDC, sends loopback frames (legacy AJOB
loopback), counts FCS errors on both ends (F133 EMAC counters; ECP5 cnt_rx_crc via the mailbox, C4) and picks the
centre of the error-free window; record the window width as PROTOTYPE_MEASURED evidence.

## Power-state rules
- ECP5 bank 0 is a top bank: input leakage ≤ ±1 mA per pin for 0 ≤ VIN ≤ VIH(max) even while unpowered
  (DS Table 3.5, IDK_HS, Tj ≤ 85 °C), so an F133 output into an unpowered bank 0 is within the hot-socket limit.
  Firmware still keeps PG0–PG12 as GPIO inputs (function 0) until DONE and returns them to inputs before removing
  FPGA power (C4 rule), so the steady state never relies on the hot-socket limit.
- The 100k pull-downs hold both CTL lines low while the other side is unpowered, in reset or not yet muxed: neither
  MAC sees a frame start.
- The F133 EMAC needs the receive clock (RXCK = ECP5 rgmii_txc) running for some register operations; the ECP5
  forwards it continuously once configured (ODDRX1F on the PLL clock).

## Open items
- RK-RGMII-IO-TIMING: bench calibration as above; IBIS check of 22R vs trace impedance.
- RK-ECP5-DDR-SEM: confirm IDDRX1F/ODDRX1F semantics against Lattice TN-02035 (sim models are assumptions).
- F133 EMAC forwarded clock duty (Duty_G 45–55 %): ECP5 ODDR clock duty is not specified in DS-02012 → bench.
