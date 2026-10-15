# First-article debug plan (R08 phase F). No development boards: the first prototype is the ARC-1 PCB itself.

Every step records an artifact under `evidence/bench_<date>/`: a photo or scope/LA capture, the UART log, the
instrument model and the supply current. A step that fails stops the sequence. **Nothing below has been performed.**

Equipment: current-limited bench supply (5 V, 0–3 A), DMM, 4-channel ≥ 200 MHz scope, logic analyser (≥ 100 MS/s),
3.3 V USB-UART, PC with xfel, SOIC-16 clip and 3.3 V SPI programmer, and an Efinix-compatible JTAG cable.

## Stage 0: bare board, no power
- Check rail-to-GND resistance at each rail test point (none may be a short).
- Inspect BGA/QFP (X-ray report from the assembler).
- Confirm the DNP list: J2/J4 LA headers, the 5.1 kΩ Rd, the 240 Ω DZQ.

## Stage 1: staged power (0 Ω links 3V3, VDD_CORE, 1V2_T35 **not fitted**)

| Step | Action | Pass |
|---|---|---|
| 1.1 | 5 V at 200 mA limit into the VBUS TP (not USB) | VBUS_5V present, current < 30 mA |
| 1.2 | Measure 3V3_REG, VDD_CORE_REG, 1V8_DRAM and 1V8_AN; scope PG_3V3 vs 3V3_REG | within the setpoint windows of POWER_TREE_AND_RESET.md §1; PG_3V3 rises ≥ 2 ms after 3V3 |
| 1.3 | Fit the 3V3 link, then the VDD_CORE link; scope F133_RESET_N | RESET rises ≥ 64 ms after VDD_CORE is stable (expect about 86 ms) |
| 1.4 | 1V2_T35_REG must stay **off** (T35_PWR_EN pulled down) | 0 V; 3V3_T35 0 V; PSRAM_VDD 0 V |
| 1.5 | 3V3_MN present (default on); MN820 **not** yet plugged | 3V3_MN ≈ 3V3 |

## Stage 2: CPU boot (gate G1/G3 evidence)

| Step | Action | Pass | Closes |
|---|---|---|---|
| 2.1 | Scope PC4/PC5 through RESET release | both ≤ 0.96 V (expect about 0.6–0.8 V) | strap math |
| 2.2 | Blank NOR (as assembled): power on, USB to PC | `xfel version` enumerates (0x00185900) | **BROM fall-through to FEL (UNDOCUMENTED)** |
| 2.3 | If 2.2 fails: hold SW2 + SW1 and retry; if it still fails, use the clip (RECOVERY_DOSSIER B) | — | records the actual BROM behaviour |
| 2.4 | `xfel spinor`; program `arc1_r08_diag.egon` at 0; read back | ID EF 40 19, 32 MiB; SHA-256 match | NOR + programming path |
| 2.5 | Power-cycle, UART0 | banner; `BOOT_SEL_PAD = 0`; eFuse select printed; S2 NOR OK with the upper-half word read | NOR-first boot (D-02) |
| 2.6 | LA on SPI0 during 2.5 | BROM opcode, clock and address width recorded | BROM facts (missing from all documents) |

## Stage 3: graphics (no FPGA)

| Step | Action | Pass |
|---|---|---|
| 3.1 | Plug the MN820; scope BT_MISO at the module and at the F133 | module VOH ≥ 2.4 V; F133 side ≥ 2.9 V |
| 3.2 | Diag S3 | REG_BOOT_STATUS 0x522E2E2E, REG_CHIP_ID 0x08200100, REG_ID 0x7C |
| 3.3 | Panel (after the R09 panel decision) | photographed lit test frame before any display claim |

## Stage 4: optional T35 + PSRAM

| Step | Action | Pass |
|---|---|---|
| 4.1 | Fit the 1V2_T35 link; diag drives PE0 | 1V2 then PG then 3V3_T35 order on the scope (VCC before VCCIO) |
| 4.2 | Program the T35 config flash over JTAG with the **native Efinity** bitstream (gate G5) | CDONE high; diag S4 OK |
| 4.3 | Scope CDONE vs CDONE_DLY vs PSRAM_EN vs PSRAM_VDD | PSRAM_VDD rises ≥ 0.5 ms after CDONE; SCLK/SIO ≤ 0.4 V and CE# tracks VDD during the ramp |
| 4.4 | Diag S5 | MAGIC "AMBX", VERSION 2, POWER_ON, BIST pass |
| 4.5 | Pull PSRAM_PWR_REQ low during BIST | POWER_LOST reported; no silent pass |
| 4.6 | Hold CRESET_N low and repeat stage 2 | boot unaffected by the T35 (isolation proven) |

## Stage 5: USB power classes and audio
- Use 500 mA, 1.5 A and 3 A sources and log the TUSB320 OUT1/OUT2 states (diag S1).
- Measure the VBUS current at each firmware policy level.
- I2S tone on both amplifiers: L/R channel identity and no pop at AMP_EN.

## Isolation features available for debug
- 0 Ω links on 3V3, VDD_CORE and 1V2_T35.
- The T35 can stay entirely unpowered (PE0).
- MN820 power switch (PD21).
- SD power switch (PD20).
- FEL button; RESET button.
- UART0 (J10) and T35 UART (J6).
- T35 JTAG (J5).
- DNP LA headers J2 (SPI0) and J4 (SPI1).
- LEDs: status, error, 3V3, T35.
