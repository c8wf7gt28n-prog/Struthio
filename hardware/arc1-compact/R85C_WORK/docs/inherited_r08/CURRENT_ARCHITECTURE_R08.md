# ARC-1 Compact architecture as of R08 (authority: CLAUDE_R08_AUTHORITY.md + corrective handoff v1.0)

```
                 USB-C (sink only) ──ESD── USB0 (device / BROM FEL)
                        │ VBUS 5 V
     ┌──────────────────┴─────────────────────────────────────────────────────────┐
     │ 3V3 buck ─ supervisors ─ core 0.95 V / DRAM 1.8 V ─ F133 RESET              │
     │                                                                           │
     │ 32 MiB SPI NOR ═SPI0 CS0═╗          ╔═ SPI1 (single) ═ 33R ═ MN820 module ═ LVDS ─> panel (R09)
     │  (boot0, A/B slots)      ║  F133-B  ║          MISO via LVC1G125 buffer      BT820B + 128 MiB DDR3L
     │ BOOT-SEL = 00 (3.3k PD)  ║  64 MiB  ║
     │                          ║  DDR2    ╠═ SMHC0 ═ microSD (games/saves only, switched VDD)
     │ T35 via 4x LVC1G125 ═════╝          ╠═ I2S2 ═ 2x MAX98357A (L/R by SD_MODE) ─ speakers
     │ (OE# pulled up; CS = PE4)           ╠═ GPIO ═ 13 buttons, LEDs, UART0 console
     │                                     ╚═ GPIO ═ T35 power/config/IRQ, PSRAM power request
     │ T35F400C3 (optional, own rails 1V2 → 3V3_T35) ── 8 MiB APS6404L (switched VDD + guard)
     └───────────────────────────────────────────────────────────────────────────┘
```

| Decision | Status in R08 |
|---|---|
| F133 is the sole BT820 master (SPI1) | kept; the MISO level is fixed by a buffer (+0.40 V instead of +0.02 V) |
| T35 optional; graphics work without it | kept. The T35 is now also **unpowered by default** and isolated from SPI0 |
| T35 private 8 MiB PSRAM | kept; the power architecture was redesigned (PSRAM_POWER_R08.md) |
| CPU audio | changed by the owner: 2 × MAX98357A on I2S instead of the HPOUT DAC |
| Boot | changed by the owner: 32 MiB SPI NOR, BOOT-SEL 00. microSD carries games only |
| USB | changed by the owner: Type-C sink + USB0 device/FEL; USB host removed |
| Panel / LVDS / backlight | deferred to R09 (MN820 LVDS pins are left unconnected in R08, with the mapping kept in PANEL_INTERFACE_R09.md) |

## Prior assumptions that R08 found contradictory or obsolete

1. **R07 boot straps "11 = SD first"** contradict the owner's NOR-first order. Replaced by 00. R07's argument that 11 is "robust because three codes try SMHC0" no longer applies.
2. **R07: the T35 shares SPI0 directly with the strap pins** and was kept off them only by holding CRESET_N. Corrective §4.1 does not accept reset alone, and R08 research found that **no Efinix source defines the pad state while CRESET_N is held**. R08 adds hardware isolation instead.
3. **R07: "single 3V3 rail for the T35"** contradicts the T35 power-up rule (VCC before VCCIO). R08 gives the T35 its own sequenced 3V3_T35.
4. **R07: PSRAM 2.2 kΩ permanent pull-downs** run the PSRAM outside its VOH test condition. Replaced (see above).
5. **R07: tightening the 3V3 rail to 3.20–3.40 V** was the only MN820 VOH mitigation, with +0.02 V of margin. Superseded by the buffer. Worst-case regulator DC tolerance is 3.199–3.440 V anyway, so the R07 window was not achievable with ±2 % parts.
6. **R06/R07 Efinity inputs:**
   - the 25 MHz oscillator was on GPIOL_66_CLK0 (D20), which is **not a PLL reference pin**. R08 uses GPIOL_15_PLLIN0 (R16);
   - the device name "T35F400C3" should be "T35F400" with timing model C3;
   - bank voltages were unset, and the SDC used `get_ports` on PLL clocks.
7. **R07 "F133 = D1-H BROM"** is still an assumption. The fall-through to FEL is undocumented, and a D1s schematic shows a "DZQ" resistor on pin 47, which the datasheet lists as NC.
8. **R07 audio "HPOUT → external amplifier"** is replaced by the owner's two I2S amplifiers.
9. **The SLIM4 R26 earlier description "AXP2101/ES8311"** is wrong. Its actual BOM has BQ24074 + TPS63070 + 2 × MAX98357A + TUSB320, per the handoff correction, confirmed in the BOM CSV.
