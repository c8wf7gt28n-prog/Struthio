# Vendor questions (R07) — ready to send; no answers received

Status of each: **OPEN** (not sent from this environment; the owner sends them).

## Bridgetek
**Q1.** MN820 DS v1.0 Table 2/3 call CN1 pins 13/15/17/19 (VCC3V3) a "3.3V output power supply"
while §5.1 says the module accepts a 3.0–3.6 V input. The VM820C v1.1 schematic (Fig. 5/7) shows
the baseboard buck driving these pins. Please confirm in writing that the host board must supply
3.3 V into these pins. Please also give the maximum current, the recommended ramp/sequence
relative to RESET_N, and any errata.

**Q2.** In single-channel SPI mode, a memory write to RAM_CMD (0x7F000000) begins with 0xFF, the
same byte as the host-command prefix (DS_BT820 §4.5.2.3, AN086 §2.3). We infer that the BT820
tells them apart by the second byte (host-command codes 0xE0–0xEB versus address bytes
0x00/0x01/0x80) and/or by the transaction length (5 bytes versus ≥ 8). Please confirm the
decoding rule. Please also confirm that 0x7FE0_0000–0x7FEB_FFFF are never valid targets, and
give any timing requirement between host commands and memory transactions.

**Q3.** Are the MN820 CN1 I/O levels in DS Table 3 (VOH ≥ 2.4 V) module-specific, for example
because of series parts or buffers? Or are the BT820 VCCIO1 = 3.3 V levels (VOH ≥ VCCIO − 0.4 V,
DS_BT820 Table 21) valid at the connector? Do the SPIS_IO data lines on the module already have
the pull-downs DS_BT820 §4.5.1 requires?

**Q4.** Is there a recommended LVDS/scan-out register set (REG_LVDSTX_PLLCFG, REG_SO_MODE) for
a 1024×600 single-channel 18/24-bit panel at about 48 MHz pixel clock?

## AP Memory
**Q6.** APS6404L-3SQR DS Rev 2.7 Table 9 specifies VOH = 0.8·VDD at IOH = −0.2 mA. Our board needs
2.2 kΩ pull-downs on SIO0–3 (power-up LOW requirement, §8), which load the outputs with up to
about 1.6 mA. What is the guaranteed VOH at 2 mA, and what is the output impedance range of the
default 50 Ω driver over PVT? Is any constraint on external pull-downs during normal operation?

**Q7.** Does a 2-clock, quad-format 'h66/'h99 fragment sent while the device is in SPI mode
leave it unaffected (treated as an incomplete command)? Our controller sends a QPI reset before
the SPI reset so that it can recover a device left in QPI mode.

## Efinix / FPGA integrator
**Q8.** Please confirm, for T35F400C3: (a) BANK1C/BANK1D at 3.3 V LVCMOS for the pins in
`R07_WORK/board/PIN_MAP_R07.md`; (b) GPIO state while CRESET_N is held low (weak pull-up as
during configuration?); (c) CRESET_N VIL and minimum low time; (d) active-x1 flash wiring per
AN 006. The R07 handoff cites "T35 DS tables 98–99" for pull/bank behaviour. In DS v3.2 the
relevant tables are 12 (banks), 66 (DC), 67–69 (Schmitt/leakage/pulls) and 59 (unused
resources), so please indicate the intended document.

## Allwinner / distributor
**Q9.** Please provide the F133 User Manual v1.0 (the mangopi.org mirror's TLS certificate has
expired), and confirm for F133-B that BROM boot select matches the D1-H UM v1.0 Tables 3-4/3-5.
Please give the factory eFuse BOOT_MODE state, and confirm the BROM falls back to USB FEL when
no medium is valid (the eLQFP128 has no FEL pin).
