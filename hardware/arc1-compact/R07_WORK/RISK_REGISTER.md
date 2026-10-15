# ARC-1 Compact risk register (updated R07, 2026-10-15)

Owner key: **OWN** = project owner (vendor contact, purchasing, bench); **ENG** = engineering
(next pass); **VEND** = vendor answer needed. Status: OPEN / MITIGATED (design change, not yet
measured) / RESOLVED-DOC (closed by manufacturer documentation, bench confirmation pending) /
CLOSED.

| ID | Pri | Risk | R07 status | Evidence | Next action | Owner |
|---|---|---|---|---|---|---|
| RK-BT-0x7F | P0 | Host driver refused all writes ≥ 0x7F000000 (FIFO, registers, display list) | **CLOSED in code** (R06 defect, reproduced and fixed) | R07-BT-02/03 | Bench capture of a RAM_CMD write vs a host command | ENG |
| RK-BT-DECODE | P0 | Silicon decodes 0xFF-prefixed writes vs host commands differently from the documented/vendor-reference reading | OPEN (low likelihood: vendor driver uses identical framing) | R07-BT-04 | Vendor Q2; bench B1.4 | VEND/OWN |
| RK-MN-PWR | P0 | MN820 VCC3V3 direction | **RESOLVED-DOC**: host supplies (VM820C schematic) | R07-MN-02 | Written confirmation Q1; current-limited first power (A0) | VEND/OWN |
| RK-MN-VOH | P1 | Module VOH 2.4 V vs F133 VIH 0.7·VCC-IO | MITIGATED: 3V3 rail 3.20–3.40 V, +0.02 V margin | R07-MN-03 | Measure VOH (B1.3); Q3; buffer if marginal | ENG/OWN |
| RK-BOOT-STRAP | P0 | BOOT-SEL PC4/PC5 shared with SPI0/T35 | MITIGATED: straps 11 by 10 kΩ pull-ups; T35 held in CRESET_N by 4.7 kΩ | R07-BOOT-02 | Bench A1/A2 | OWN |
| RK-BOOT-EFUSE | P1 | eFuse BOOT_MODE=1 or Fast Boot overrides straps | OPEN | R07-BOOT-01 | Read SID/VER_REG with banner image (A2); Q9 | OWN |
| RK-BOOT-DOC | P1 | F133 manual unavailable; D1-H manual used | OPEN | R07-BOOT-01 | Q9; retry download when mirror fixed | OWN |
| RK-FEL | P2 | No FEL pin; recovery relies on BROM fallback | OPEN (ASSUMPTION) | R07-BOOT-03 | Bench A3 | OWN |
| RK-SPI-QUAD | P2 | BT820 dual/quad over F133 SPI | DOWNGRADED: single baseline; quad plausible with STC=0 | R07-SPI-01 | Bench B2 | ENG |
| RK-PSRAM-PU | P1 | PSRAM power-up LOW vs T35 config pull-ups | MITIGATED: 2.2 kΩ pull-downs (0.291 V worst case) | R07-PS-02 | Scope during ramp (C2) | OWN |
| RK-PSRAM-VOH | P1 | PSRAM VOH spec only at 0.2 mA; pull-downs draw ~1.6 mA | OPEN | R07-PS-02 | Vendor Q6; bench VOH (C3) | VEND |
| RK-PSRAM-BROWNOUT | P1 | PSRAM power loss undetected by controller; silent garbage | OPEN (found in R07 sim) | R07-PS-03 | 3V3 supervisor → F133 RESET; canary check before trusting PSRAM | ENG |
| RK-PSRAM-QPIRST | P2 | QPI-format reset fragment harmless in SPI mode | OPEN (ASSUMPTION) | — | Vendor Q7; bench C4 | VEND |
| RK-T35-EDA | P1 | No native fit/IO/STA | OPEN: NATIVE_EDA_NOT_RUN | R07-T35-01 | Run Efinity (owner licence) | OWN |
| RK-T35-SPISLAVE | P2 | Mailbox oversampled slave: first-bit MISO timing under real SCK/clock ratio | OPEN (RTL only at /8, /16) | R06 tb_top | STA + logic analyser at the chosen SCK | ENG |
| RK-PANEL | P2 | Panel timing/LVDS mapping/orientation unconfirmed | OPEN | BT820_HOST_PROTOCOL §6 | Vendor Q4; panel datasheet confirmation; bench B1.6 | OWN |
| RK-F133-IMG | P1 | Bring-up image never executed (registers from D1-H UM) | OPEN: BUILD-ONLY | R07-F133-01 | Bench A2 | OWN |
| RK-AUDIO | P2 | Speaker amplifier unselected; audio unmeasured | OPEN (deferred per vision doc) | R06 AUDIO note | After graphics bring-up | ENG |
| RK-PCB | P0 for release | No schematic/PCB/BOM/DFM | OPEN: **fabrication not approved** | — | Schematic from `r07_board_plan.json` after stage A/B | ENG/OWN |

R06 risks carried forward and closed: `MN820_POWER_PIN_WORDING` → RK-MN-PWR (RESOLVED-DOC).
`F133_QUAD_IO_UNCONFIRMED` → RK-SPI-QUAD (downgraded).
