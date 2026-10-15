# Independent ECP5 JTAG service and recovery (R8.5, CO 4.2 / 6.2)

Use JTAG when the F133 firmware is absent, crashed, or cannot configure the FPGA. It needs neither the F133 nor the
NOR nor the microSD. **Procedure only. It has not been carried out (no board exists).**

## 1. Connector J5 (2 × 5, 1.27 mm, ARM Cortex 10-pin layout)

| Pin | Signal | Notes |
|---|---|---|
| 1 | VTref = 3V3_FPGA (VCCIO8) | the adapter must use it as its I/O reference (3.3 V); it reads 0 V while the FPGA is unpowered |
| 2 | TMS | 4.7 kΩ pull-up |
| 3, 5, 9 | GND | |
| 4 | TCK | 4.7 kΩ pull-down; ECP5 fTCK max 25 MHz (DS Table 3.43); use ≤ 6 MHz on the first article |
| 6 | TDO | 4.7 kΩ pull-up |
| 7 | key / not connected | |
| 8 | TDI | 4.7 kΩ pull-up |
| 10 | PROGRAMN (nRESET position) | an adapter that drives nRESET low restarts configuration; leave it unconnected unless intended |

Test pads: FPGA_DONE, FPGA_INITN, FPGA_PROGRAMN, DONE_DLY, 1V1_FPGA, 2V5_FPGA_AUX, 3V3_FPGA, FPGA_VCC_PG.

## 2. Powering the FPGA without the F133: J11

The FPGA rails are off by default (FPGA_PWR_EN 100 kΩ pull-down). Fit a jumper on **J11 pins 1-2** (3V3 → FPGA_PWR_EN):
the 1 kΩ in series with F133 PE0 limits the current if firmware drives PE0 low at the same time (3.3 mA). Check the
TP voltages: 1V1_FPGA 1.05–1.15 V, 2V5_FPGA_AUX 2.38–2.62 V, 3V3_FPGA ≥ 3.14 V, then FPGA_INITN high within 33 ms.
F133 held in reset (RESET button, or `F133_RESET_N` TP to GND) keeps SPI0 isolated (BUS_EN_N pull-up) and PROGRAMN
released.

## 3. Commands (openFPGALoader 0.12.0, as installed for this pass)

```
openFPGALoader --detect -c <cable>                       # expect IDCODE 0x41112043 (LFE5U-45)
openFPGALoader -c <cable> fpga_ecp5/build/arc1_ecp5.bit  # SRAM load over JTAG (volatile)
openFPGALoader -c <cable> --verbose --detect             # read status after load
```
`<cable>` is the adapter in use (e.g. `ft2232`, `ft232`, `digilent_hs2`; `openFPGALoader --list-cables`). The
`--detect` IDCODE must match before anything is loaded; an 85F would report 0x41113043 and the bitstream must not be
loaded (wrong device). DONE high, then DONE_DLY high after ≈ 0.7 ms.

## 4. After a JTAG load

* The F133 diagnostic image (S4) sees DONE + INITN + VCC_PG high and skips the probe; S5 then runs DISCOVER and the
  PSRAM power/BIST stages over the operational interface.
* SRAM configuration is lost at power-off or on PROGRAMN. Nothing on the board is written by JTAG in this design,
  because there is no configuration flash.

## 5. Recovery flow

| Symptom | Action |
|---|---|
| F133 firmware crashes while configuring | F133 reset releases PE0 → rails off (FIT F09a); next boot reconfigures. With J11 fitted, the FPGA stays powered half-configured; the next PROGRAMN pulse clears it (FIT F09b) |
| configuration fails repeatedly | JTAG `--detect` (IDCODE/rails), then JTAG load of the known-good `arc1_ecp5.bit`; compare the loader's error code |
| suspected FPGA rail fault | J11 off, measure the TPs with FPGA_PWR_EN forced; FPGA_VCC_PG is also readable on F133 PD1 |
| BT820/launcher problem | unrelated to the FPGA: remove J11, keep the FPGA off. The launcher does not need it |

## 6. Fixture for the first PCB

Tag-Connect-style pads are not used; J5 is a populated 1.27 mm header. The fixture needs a 3.3 V JTAG adapter with a VTref
input, a jumper for J11, and probes on the TPs above. Keep the header within 50 mm of the BGA (R09 placement note).
