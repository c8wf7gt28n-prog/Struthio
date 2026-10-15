# F133 / D1s reference design notes

Source schematic: **MangoPi MQ "D1s-eLQFP128_mq_sch_v1.5_mp.pdf"**. KiCad, Rev V1.5, dated 2021-11-25, 3 pages.
- Mirror: https://github.com/devdotnetorg/MangoPi-MQ1/blob/master/Hdk/D1s-eLQFP128_mq_sch_v1.5_mp.pdf (raw: https://raw.githubusercontent.com/devdotnetorg/MangoPi-MQ1/master/Hdk/D1s-eLQFP128_mq_sch_v1.5_mp.pdf)
- sha256 `ac21d23608f3b651ab82d1ee4587b9fc61fa944123bfcfc14ee4a91bb327b3a5`
- Pages: p.1 = SoC (D1s.kicad_sch), p.2 = peripherals and power (Periph.kicad_sch), p.3 = Wi-Fi/BT (WIFI-BT.kicad_sch).
- The SoC symbol is "D1s-eLQFP128". D1s and F133 share the same pinout: every pin number and name on the symbol matches F133 datasheet Table 4-2. The two exceptions are listed under "Discrepancies" below.
- I read the values from 300-dpi renders of the PDF. Text in brackets is my interpretation, not something the schematic says.

No official Allwinner F133 reference schematic ("F133_Schematic_Diagram", which datasheet 5.8 refers to) was found in a public, TLS-valid location.

## 1. Regulator topology (p.2, upper right; p.1)
The board has no PMIC. It uses a discrete triple buck plus LDOs.
- **U4 RY1303 triple buck**, powered from VCCIN (USB-C VBUS, 5 V).
  - VIN1/2/3 and VCC are tied together. Input caps are C25, C26, C27, C76 (4 × 10 µF).
  - VF = 0.6 V.
- **SW1 → VCC3V3 (3.3 V)**
  - L1 2.2 µH.
  - Feedback R8 680 k 1 % (top) / R9 150 k 1 % (bottom) gives 0.6 × (1 + 680/150) = 3.32 V.
  - Output caps C28 10 µF and C29 0.1 µF.
  - EN1 is tied to VIN, so this rail comes up first.
- **SW2 → VCC-DRAM, "DRAM 1.8V"**
  - L3 2.2 µH.
  - Feedback R10 300 k / R11 150 k gives 1.8 V.
  - Output caps C30 10 µF and C31 0.1 µF.
  - EN2 is pulled up by R23 100 k from VCC3V3.
- **SW3 → VCC-CORE, "CORE 0.9V"**
  - L2 2.2 µH.
  - Feedback R12 75 k / R13 150 k gives 0.9 V.
  - Output caps C32 10 µF and C33 0.1 µF.
  - EN3 is driven from VCC3V3 through R1 100 k, with R2 100 k and C4 0.1 µF to GND (R45 NC). This is an RC delay; the note reads "PWR-ON Sequence wait 2ms". It implements the datasheet 5.12 rule that VCC-IO must be up ≥ 2 ms before VDD-CORE/SYS.
  - Note: datasheet rev 2.3 Table 5-2 gives 0.95 V typ (0.85–0.99 V). 0.9 V is the old v1.0 typical, and it is still within range.
- **U2 XC6206-1.8V LDO**: VCC3V3 → AVCC1.8. Caps C5 0.1 µF and C22 2.2 µF, to AGND. AVCC1.8 feeds:
  - AVCC (pin 89)
  - HPVCC (pin 97)
  - VCC-TVIN (pin 107), via R71 0 Ω
- **U8 XC6206-1.2** and **U9 XC6206-2.8** are for the camera only (DVP_DVDD, AVDD2V8).
- **Internal LDOs (p.1)**
  - LDO-IN (pin 29) is fed from VCC3V3 through D2 "MSK4010" (Schottky) [inference], with C68 2.2 µF.
  - LDOA-OUT (pin 28) has C44 2.2 µF. It is annotated "1.8V@0.26A".
  - LDOA-OUT feeds:
    - VCC-PLL (pin 20), C79 0.1 µF
    - VCC-RTC (pin 26), via R61 0 Ω
    - VDD18-DRAM (pin 50)
    - VCC-LVDS (pin 65), C13 0.1 µF
    - the RESET pull-up
  - LDOB-OUT (pin 30) has C50 2.2 µF and is annotated "1.8V/1.5V/1.35@0.4A Default 1.35V". There is a KiCad "x" no-connect mark on the LDOB-OUT net segment, and VCC-DRAM comes from the buck instead. **Ambiguous**: LDOB is likely unused, with only the cap fitted.
- **Rail-to-pin assignments**
  - VCC-DRAM0/1 (pins 48, 49): from the buck SW2. Caps C21 10 µF, C24 1 µF, C52 0.1 µF, C77 0.1 µF. Labeled "DDR2 1.8V".
  - VCC-CORE: to VDD-CORE0/1 (116/117) and VDD-SYS0/1/2 (46/51/81). Caps C10 10 µF and C38, C39, C53, C37 (0.1 µF each).
  - VCC3V3: to VCC-IO (83), VCC-PG (128) and VCC-PD (66, with C20 0.1 µF). Bulk caps C2 10 µF and C34, C35, C36 (0.1 µF each).
  - VCC-TVOUT (77): VCC3V3 via R70 0 Ω, C12 0.1 µF.
  - VCC-PE (34): from VCC-RMII-CSI. That net comes from AVDD2V8 via R56 0 Ω, or from VCC3V3 via R57 (NC). C66 0.1 µF. Note on the sheet: "2.8V/3.3V".

## 2. Crystals (p.1, left)
- **24 MHz (X1)**: XTAL2520-24M, 2.5×3.2 mm, CL = 18 pF.
  - Load caps C8 = C9 = 22 pF to GND.
  - X0 goes to DXOUT (22), XI to DXIN (23).
  - No series or feedback resistor.
  - Symbol note: "Cshunt = 6.5pF".
- **32.768 kHz (XT1)**: CL = 12.5 pF.
  - Load caps C43 = C45 = 22 pF.
  - R40 680 k 1 % is placed across the crystal.
  - 32O goes to X32KOUT (24), 32I to X32KIN (25).
  - Symbol note: "Cshunt = 1.1pF".
- REFCLK-OUT (21) becomes net AP-CLK24M-OUT, which goes to Wi-Fi TCXO_IN via R41 (NC/0R) on p.3.

## 3. Reset (p.1, lower left; p.2)
- RESET (pin 27) is pulled up by R74 10 k to **LDOA-OUT (1.8 V)**, with C84 0.1 µF to GND. Labeled "复位电路" (reset circuit).
- Push-button S2 shorts RESET to GND (p.2).
- There is no external supervisor IC. The SoC's internal reset (64 ms) is relied on.

## 4. Boot straps / FEL (p.1, p.2)
- SPI0 strap resistors:
  - SPI0_MISO (PC5 = BOOT-SEL1): R75 10 k pull-up to VCC3V3, R76 (NC) pull-down.
  - SPI0_MOSI (PC4 = BOOT-SEL0): R77 (NC) pull-up, R78 10 k pull-down.
  - Result: **SEL[1:0] = 10** as fitted.
- Silkscreen table on the sheet:
  - 00: NOR > NAND
  - 01: SD > NOR > Other
  - √10: SD > NAND > Other (the fitted setting is ticked)
  - 11: SD0 > EMMC2 > EMMC2_USR > Other
- Button S1 shorts **SPI0_MOSI (PC4/BOOT-SEL0)** to GND (p.2). [This is the board's FEL/boot-override button. The mechanism is not documented by Allwinner.]

## 5. SPI NOR (p.1, top left)
- U3 is a SOP8W SPI flash.
- Pull-ups to VCC3V3: /CS has R7 10 k, /WP has R33 10 k, /HOLD has R25 10 k.
- C42 0.1 µF decoupling.
- SPI0_CLK has a 33 Ω series resistor (refdes printed "R4?", partly obscured; R40 is also used for the 680 k part), at the SoC side (pin 19).
- Pin mapping: PC2 = CLK (19), PC3 = CS0 (18), PC4 = MOSI (17), PC5 = MISO (16), PC6 = WP (15), PC7 = HOLD (14).

## 6. microSD (p.1, top left)
- J1 TF5033981892, on SDC0 (PF0–PF5).
- Pin mapping: D1 = PF0 (7), D0 = PF1 (8), CLK = PF2 (9), CMD = PF3 (10), D3 = PF4 (11), D2 = PF5 (12).
- Card detect SDC0_DET = PF6 (13), with R48 10 k pull-up to VCC3V3.
- Resistors and caps:
  - CMD: R18 10 k pull-up to VCC3V3.
  - CLK: R43 33 Ω in series.
  - **No external pull-ups drawn on DAT0–DAT3.**
  - VDD: C41 0.1 µF.
- VDD is VCC3V3 directly, with no load switch.

## 7. UART debug (p.1 right, p.2)
- The console is **UART3 on PB6 (TX3, pin 80) / PB7 (RX3, pin 79)**, which is function F7 per datasheet Table 4-3.
- It goes to header P8 (3-pin: GND, TX3, RX3) labeled "UART3 CONSOLE".
- No series resistors or level shifting.

## 8. USB (p.2)
- **USB0 (OTG)**: USB-C J3 (16P).
  - DP1/DP2 are tied together to USB0_P, and DN1/DN2 to USB0_N.
  - These connect directly to USB0-DP (115) and USB0-DM (114). **No series resistors, common-mode choke or ESD part is drawn.**
  - CC1 and CC2 each have 5.1 k to GND (R28, R30), so the port is a UFP/sink.
  - VBUS goes to VCCIN, which also powers the board.
  - VCCIN bulk caps: C82 and C83, 10 µF each.
- **USB1 (Host)**: USB-C J2.
  - Also wired with 5.1 k CC pull-downs (R24, R26) and VBUS on VCCIN.
  - USB1_N/P go to pins 113/112.
- There is no USB ID/VBUS-detect connection to the SoC (the package has no such pins).

## 9. Headphone / audio (p.1 right, p.2)
- HPOUTL (99) and HPOUTR (98) go through **C54 / C85 10 µF series coupling caps** to header P6 pins 2 and 3. P6 pin 4 is AGND and P6 pin 1 is TVIN0.
- HPOUTFB (100) is decoupled with C86 0.1 µF to AGND.
- RC snubbers to AGND (p.1): R64 33 Ω + C80 0.1 µF, and R3 33 Ω + C6 0.1 µF, on the HPOUTL/HPOUTR nets. Annotated "540Vrms" [presumably mVrms].
- Reference and supply caps:
  - VRA1 (92): C40 0.47 µF.
  - VRA2 (90): C78 0.47 µF.
  - AVCC (89): C11 2.2 µF, to AGND.
- AGND is tied to GND with R15 0 Ω.
- Mic input:
  - MICIN3P/N go through C46 / C47 0.1 µF to the electret mic M1.
  - Bias: AVCC1.8 → R55 75 Ω → C81 10 µF filter → R27 1 k → M+. M− has R34 1 k to AGND. C7 100 pF is across the mic.
- FMINL/R are not connected. LINEINL/R go to test points; the note reads "1.7Vpp".

## 10. Other
- GPADC0 (101): R29 100 k pull-up to AVCC1.8, C49 1 nF to AGND (key ADC).
- TP-X1/X2/Y1/Y2: C72–C75 1 nF filter caps. TVIN-VRP/VRN: C69 / C71 1 µF.
- TVOUT0 (78) is terminated with R60 75 Ω to GND.
- EPAD (symbol pin 129) is tied to **GND**.
- The Wi-Fi module (p.3) uses SDIO1 on PG0–PG5, with 47 k pull-ups R65–R69 to VCC3V3. UART1 is on PG6–PG9. PG11 is an optional LPO 32 k (R84 NC).

## Discrepancies vs the F133 datasheet
- **Pin 47**: the datasheet calls it "NC". The D1s schematic labels it **"DZQ"** and connects it to R42 240 Ω 1 % to GND (a DRAM ZQ calibration resistor). The F133 datasheet does not document this. [Fitting the 240 Ω to GND is a low-risk choice, but it is not documented by Allwinner.]
- **Pin 106**: the datasheet calls it "NC0". The schematic fits R54 "NC/1K" to GND, i.e. optional and not fitted.
- **VDD-CORE**: the schematic uses 0.9 V. Datasheet rev 2.3 gives 0.95 V typ (0.85–0.99 V).
