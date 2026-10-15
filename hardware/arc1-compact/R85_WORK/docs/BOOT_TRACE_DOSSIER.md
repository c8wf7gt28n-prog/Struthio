# Boot trace dossier (R08, corrective handoff v1.0 §4, gate G1)

Evidence classes (corrective handoff §9): **A** manufacturer fact, **B** calculation, **C** native CAD/EDA report,
**D** software simulation, **E** physical observation. R08 provides A–D. **Nothing here is E.**

## 1. Boot-source selection: what is documented and what is not

| Item | Finding | Class | Source |
|---|---|---|---|
| BOOT-SEL pins | BOOT-SEL0 = PC4 (pin 17), BOOT-SEL1 = PC5 (pin 16), function 4. They are also SPI0-MOSI/MISO (function 2) | A | F133 DS rev 2.3 Table 4-3 (`sources/f133/f133_boot_usb_facts.json`) |
| Reset state | PC3, PC4, PC5 reset with an internal pull-up of 12/15/18 kΩ. PC2, PC6, PC7 reset high-Z | A | F133 DS Table 4-2, Table 5-3 |
| GPIO select table | 00 = SPI NOR → SPI NAND; 01 = SMHC0 → SPI NOR → other; 10 = SMHC0 → SPI NAND → other; 11 = SMHC0 → eMMC2 | A, but **D1-H** manual | D1-H UM v1.0 §3.3.2.1 Table 3-5, PDF p.160. The F133 manual was not retrievable (mangopi.org TLS certificate expired; not bypassed) |
| eFuse override | BOOT_MODE eFuse = 0 → GPIO select; = 1 → eFuse select (straps ignored). Readable at SID 0x03006210 [27:16]; pad status at VER_REG 0x03000024 [12:11] | A (D1-H) | D1-H UM §3.3.2.1 |
| Fall-through to USB FEL after all media fail | **NOT documented** in any retrieved Allwinner text. Figure 3-5 has no readable text | — | `sources/f133/f133_boot_usb_facts.json` |
| SPI NOR boot0 offset, header, size, opcode, clock | **NOT documented** in retrieved Allwinner text. Community practice (sunxi): eGON boot0 at offset 0, 03h read, 3-byte address. That is not a vendor fact | — | — |

**Consequence (gate G1 = HOLD).** NOR-first boot is **designed**, not proven. The straps are set for code 00, and the
diagnostic image prints the pad status and eFuse select so that the first board measures it (class E, R09/R10 bench).

## 2. Strap network (class B; `analysis/electrical_margins_r08.py`)

| Pin | Net | Network | Worst-case level at sampling | Limit | Result |
|---|---|---|---|---|---|
| PC4 BOOT-SEL0 | SPI0_MOSI | 3.3 kΩ ±1 % to GND (R in `boot_nor` sheet) against the internal 12 kΩ min pull-up, 3.40 V, plus 21 µA of leakage | **0.794 V** (`docs/ELECTRICAL_MARGINS_R08.md`) | 0.3 × 3.20 V = 0.96 V | PASS |
| PC5 BOOT-SEL1 | SPI0_MISO | same; NOR DO is high-Z (CS# high, 10 kΩ pull-up); the T35 MISO buffer U24 is high-Z (OE# = T35_SS_N_F, pulled up) | 0.794 V | 0.96 V | PASS |

The R07 straps (10 kΩ pull-ups = code 11, SD first) are removed. The checker rule `boot_straps_00` plus the negative test
`test_r07_strap_11_is_rejected` enforce this.

**Cost of the pull-down (OPEN, RK-NOR-VOH).** When the NOR drives DO high, it sources about 1.04 mA into 3.3 kΩ. Winbond
specifies VOH only at −100 µA, so the actual level is unspecified (class A gap). This is the same class of problem R07 had
with the PSRAM. Closure needs the Winbond IBIS model (R09) or a bench measurement. A weaker pull-down is not available:
4.7 kΩ leaves only about 0.02 × VCC of margin against the internal pull-up.

## 3. Bus ownership state table (corrective handoff §4.1)

| Phase | F133 SPI0 (PC2–PC7) | NOR U16 | T35 / isolation | Hardware guarantee |
|---|---|---|---|---|
| Power ramp | in reset: PC3–PC5 internal PU, PC2/6/7 high-Z | CS# pulled up to 3V3 (R, 10 kΩ); /RESET pulled up; IO2/IO3 pulled up | **unpowered**: T35_PWR_EN pulled down (100 kΩ) → 1V2 off → 3V3_T35 off. Buffers U21–U24 have OE# pulled up = high-Z, Ioff | U4 holds core/DRAM rails; U8 holds F133 RESET ≥ 86 ms |
| Strap sampling | PC4/PC5 read by BROM | DO high-Z | no T35 driver can reach PC4/PC5: the T35 sits only behind U21–U24 (rule `spi0_t35_isolated`) | 3.3 kΩ pull-downs win against the 12 kΩ internal pull-ups |
| BROM read (expected) | SPI0 master, CS0 = PC3 | selected, 3-byte mode (driver never sets 4-byte mode) | still unpowered | — |
| Application | NOR via CS0; T35 via GPIO CS PE4 after BUS_EN_N = 0 | deselected while the T35 is addressed (CS0 driven high by GPIO in the diag image) | powered on firmware request; MISO buffer drives PC5 only while PE4 is low | U24 OE# = T35_SS_N_F |
| USB FEL | BROM owns USB0 | may be blank or corrupt, or held in reset by SW2 | unpowered (firmware has not run) | — |
| Warm reset | F133 pins revert to reset state | NOR may be mid-operation → the R08 driver issues 66h/99h at init, exits 4-byte mode, clears EAR | T35 rail stays as left; CRESET_N pull-down (4.7 kΩ) holds the T35 when F133 releases PE8; buffers high-Z via pull-ups | — |

**Unpowered-FPGA back-feed (corrective §4.1 note).**
- **SPI0 lines:** the T35 SPI0 lines are separated by Ioff buffers (±10 µA, SN74LVC1G125 §5.5).
- **CRESET_N:** passes through a 1 kΩ series resistor (≤ 3.3 mA < 10 mA abs-max clamp, T35 DS).
- **CDONE, IRQ_N and PSRAM_PG:** pulled up to 3V3_T35 and read as inputs by the F133, so there is no source into an unpowered T35.

## 4. NOR addressing (gate G2 partial)

- **Part:** W25Q256JVFIQ, SOIC-16 300 mil. JEDEC ID EF 40 19. QE = 1 is fixed on the IQ variant. Dedicated /RESET on pin 3. It powers up in 3-byte mode (ADP = 0) (class A, `sources/glue`).
- **Lifecycle status:** **NOT_FOUND**. Winbond product pages could not be read; the corrective handoff warns about an NRND variant. This item is VENDOR_OPEN.
- **Driver policy** (`firmware/src/spi_nor.c`, HOST_TESTED):
  - The driver never enters 4-byte mode. It reaches all 32 MiB through the dedicated 4-byte opcodes 13h/12h/21h.
  - The fallback for parts without those opcodes is the Extended Address Register, restored to 0 after every access.
  - At init and before any reboot it repairs a device found in 4-byte mode or with EAR ≠ 0.
  - It refuses ADP = 1 (would power up in 4-byte mode).
  - It refuses unknown > 16 MiB parts and JEDEC/SFDP size mismatches.
- **Tests:**
  - The upper-half test writes and reads 0x01000000 and 0x01FFE000 and crosses the 16 MiB boundary.
  - Four mutants are killed: 3-byte opcode for the upper half, entering 4-byte mode, no busy polling, no EAR restore.
- **Upper-half proof on silicon:** the diagnostic image reads the factory test block at 0x01FF0000 (class E pending).

## 5. Boot-state diagram (intended behaviour)

```
power-up --> U4 PG_3V3 (13 ms) --> core/DRAM bucks --> U8 (86 ms) --> F133 RESET released
   --> BROM samples BOOT-SEL = 00 (unless eFuse BOOT_MODE=1 or fast-boot set: printed by diag S0)
   --> SPI NOR: boot0 eGON at 0 valid?  -- yes --> ARC-1 loader: fl_boot_select():
          |                                            trial slot (3 attempts) -> confirmed slot -> other slot (trial)
          |                                            -> recovery image -> NONE (print, LED error, stay for USB)
          no / NOR held in /RESET by SW2
          v
       SPI NAND (none fitted) --> [UNDOCUMENTED] expected USB FEL on USB0 --> xfel (RECOVERY_DOSSIER.md)
microSD is never in the 00 boot list: a game card cannot replace system firmware (D-03).
```
