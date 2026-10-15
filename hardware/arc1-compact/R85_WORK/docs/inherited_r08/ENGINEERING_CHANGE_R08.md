# Engineering change summary R07 → R08 (corrective handoff deliverable 6)

The R07 baseline is `R07_WORK/board/r07_board_plan.json`, a pin/voltage plan with no schematic. R08 is the native KiCad
schematic generated from `cad/gen/design.py`, with the plan exported to `board/r08_board_plan.json`.

## Net / pin changes on the F133

| F133 pin | R07 | R08 | Reason |
|---|---|---|---|
| PC2 SPI0-CLK | T35_SCK (direct) | SPI0_CLK_F → 22 Ω → NOR CLK; buffered to T35 (U21) | NOR boot on SPI0 (D-01) |
| PC3 SPI0-CS0 | T35_SS_N | SPI0_CS0_N = NOR CS#, 10 kΩ pull-up | BROM NOR boot uses CS0 |
| PC4 MOSI / BOOT-SEL0 | T35_MOSI, 10 kΩ pull-up (strap 1) | SPI0_MOSI, **3.3 kΩ pull-down (strap 0)**, buffered to T35 (U22) | BOOT-SEL 00 = NOR first |
| PC5 MISO / BOOT-SEL1 | T35_MISO, 10 kΩ pull-up (strap 1) | SPI0_MISO, **3.3 kΩ pull-down**; NOR DO; T35 MISO via U24 (OE# = T35 CS) | same |
| PC6 / PC7 | PC6 = T35_IRQ_N, PC7 unused | NOR IO2 / IO3, 10 kΩ pull-ups (QE = 1) | NOR |
| PE4 | — | T35_SS_N_F (GPIO chip-select for the T35) | T35 moved off CS0 |
| PE5 | — | T35_IRQ_N (moved from PC6) | PC6 is now NOR IO2 |
| PE6 | — | T35_BUS_EN_N (isolation buffers) | isolation |
| PE7 | — | PSRAM_PWR_REQ | PSRAM switched supply |
| PE0 | — | T35_PWR_EN | T35 rails off by default |
| PE11 | — | PSRAM_PG (diagnostic read) | |
| PE10 | AMP_SD_N (one analog amplifier) | AMP_EN → 2 × MAX98357A SD_MODE (L direct, R via 210 kΩ) | I2S audio |
| PB4/PB5/PB6 | reserved I2S (fallback) | I2S_DOUT/BCLK/LRCK (primary audio) | owner: 2 × I2S amps |
| PB2/PB3, PB7 | reserved TWI0 / MCLK | unconnected (spare) | TUSB320 runs in GPIO mode |
| HPOUTL/R/FB | analog audio out | unconnected | |
| PD13 SPI1-MISO | direct from MN820 | via U17 SN74LVC1G125 (OE# = BT_SS_N) | MN820 VOH margin |
| PD14/PD15 | BT_IO3/IO2 (quad option) | unconnected; module IO2/IO3 10 kΩ pull-downs only | single-SPI baseline; quad needs a bidirectional redesign (R09+) |
| PD10/11/12/16 | direct | 33 Ω series; SS_N/INT_N pull-ups to 3V3_MN | back-power, SI |
| PD18/PD19 | — | LED_STATUS / LED_ERROR | debug-first |
| PD20 / PD21 | — | SD_PWR_EN / MN_PWR_EN | card and module power control |
| PF6 | — | SD_DET_N | card detect |
| PE1, PE12, PE13 | — | VBUS_SENSE, USB_CUR_OUT1/2 | power policy |
| PG0–PG12 | — | 13 buttons | controls |
| USB0 D± | reserved | USB-C J1 via ESD | FEL / device |
| USB1 D± | (unassigned) | explicitly unconnected | D-04: no host |

## Components added (beyond the R07 plan)

- **Boot:** W25Q256JVFIQ (U16), SW2 FEL, SW1 RESET.
- **Isolation and level shifting:** 5 × SN74LVC1G125 (U17 MISO buffer, U21–U24 T35 isolation).
- **PSRAM power:** SN74LVC07A (U26), SN74LVC1G08 (U13), SN74LVC1G17 (U20), TPS22918 × 4 (U10 T35 VCCIO, U11 MN820, U12 PSRAM, U27 SD).
- **Supervisors:** TPS3808 × 3 (U4 3V3, U8 core/RESET, U14 PSRAM).
- **Regulators:** TLV62569(P) × 4 (3V3, core, DRAM, T35 1V2), TLV75518P.
- **USB-C:** TUSB320LAI, TPD2EUSB30, USB4105 Type-C, 1812 PTC, TVS.
- **Media and audio:** microSD DM3AT, 2 × MAX98357A, 2 speaker connectors.
- **T35 support:** T35 config flash W25Q32JV (U19), 25 MHz XO (X1), JTAG/UART headers.
- **Debug:** LA headers (DNP), 13 buttons, LEDs, test points, 0 Ω staged-power links, the DNP pin-47 DZQ option.

## Removed / not carried

- USB host power path, USB1 and USB-A connectors (D-04).
- SD boot (straps 11) (D-02/D-03).
- Analog HPOUT amplifier.
- Panel FFC, LCD supply and backlight driver (D-07 → R09).
- The R07 3.20–3.40 V rail tightening as an MN820 mitigation.

## Code changes

| Area | Change | Evidence |
|---|---|---|
| T35 RTL | new `psram_power_guard.sv`; `mbx_regs_r08.sv` (AMBX v2: POWER_ON/LOST/EPOCH, READY gating); `arc1_t35_top_r08.sv` (guard, CE# OE, PG/EN inputs, Efinity inout port names). The R06 controller/mailbox RTL is unchanged | RTL_SIMULATED tb_top_r08 |
| Host firmware | new `spi_nor.c` (32 MiB, 4B opcodes / EAR, mode repair), `flash_layout.c` (map, image check, journal, A/B), `game_lib.c` (package validation, scan, power-fail-safe saves), `crc32.c` | HOST_TESTED 757 checks + 4 mutants |
| F133 image | new `f133_diag` (boot0 diagnostics S0–S5), reusing the R07 BT820 driver unchanged | BUILD_ONLY |
| Efinity | `gen_efinity_r08.py` generates project XML / ISF / SDC / pins from the schematic | syntax-checked only; NATIVE_EDA_NOT_RUN |
| Mailbox ABI | VERSION 1 → 2, CAPS bit2. R07 hosts that check VERSION == 1 see NOT_READY and fall back to the CPU (safe) | RTL_SIMULATED |
