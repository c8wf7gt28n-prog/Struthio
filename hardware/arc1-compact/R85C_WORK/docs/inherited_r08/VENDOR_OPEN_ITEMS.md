# Vendor-open items (VENDOR_OPEN until a written, dated answer is filed in `R08_WORK/vendor/`)

Only the owner or an authorised sender transmits these questions. An unanswered question is not a resolved one. The R07 questions Q1–Q9 (`R07_WORK/docs/VENDOR_QUESTIONS.md`) remain open unless restated here.

| ID | Vendor | Question | Why it matters | R08 interim position |
|---|---|---|---|---|
| V1 (R07 Q1) | Bridgetek | Confirm that MN820 CN1 pins 13/15/17/19 are a 3.0–3.6 V **input** from the host, give the maximum current (Table 3 gives only 245 mA typical), and state any sequencing constraint | supply sizing, back-power | host supplies the module via U11 (VM820C reference); the budget uses a 1.6× typical allowance |
| V2 (R07 Q2) | Bridgetek | Silicon decode of the 0xFF-prefixed RAM_CMD writes vs host commands | graphics protocol | host-tested and matches EveApps; first-article S3 |
| V3 | Bridgetek | Module-level VOH/VOL test currents for SPIS_* | the buffer covers it, but quad mode would need it | single-SPI baseline with buffer |
| V4 | Bridgetek | MN820 mounting-hole diameter, connector datum (centre?), keep-out under the module | mechanical | 2.7 mm NPTH assumed |
| V5 (R07 Q6) | AP Memory | APS6404L VOH vs IOH curve or IBIS model; abs-max input current when VDD = 0 | the R08 design keeps the load ≤ 34 µA in operation and pins ≤ 0.37 V when unpowered | closed by design, pending confirmation |
| V6 | Winbond | W25Q256JVFIQ lifecycle (active vs NRND), VOH vs IOH (IBIS), and the exact BP/TB code to protect the lower 1 MiB | BOOT-SEL1 pull-down loads DO with 1.04 mA (RK-NOR-VOH) | OPEN |
| V7 | Allwinner | F133-B BROM: SPI NOR boot0 format, opcode, clock, address width; fall-through to USB FEL when NOR/NAND fail; default BOOT_MODE eFuse state; pin 47 (NC vs DZQ 240 Ω); EPAD connection; VRA1/VRA2 and TVIN-VRP/VRN termination; crystal load capacitance; per-rail currents | boot (G1/G3), PDN | D1-H UM + MangoPi reference + bench |
| V8 | Efinix | T35 pad state while CRESET_N is held low; Hardware Design Checklist (decoupling, CDONE/CRESET values); FBGA400 package drawing (ball and body size) | footprint, PDN, isolation | isolation buffers make the CRESET_N state irrelevant for SPI0 |
| V9 | TI | TUSB320LAI dead-battery Rd presence (sink without VDD) | USB-C power-up | DNP 5.1 kΩ Rd fallback |
| V10 | Hirose | DF40C-100DS-0.4V(51) drawing: pad numbering vs MN820 CN1, land pattern | footprint (GENERATED_DERIVED) | derived from the catalogue |
| V11 | ADI | MAX98357A TQFN-16 EP size and land pattern | footprint PLACEHOLDER | KiCad generic QFN-16 3×3 |
| V12 | JLCPCB | assembly-time programming of a SOIC-16 NOR; 0.8 mm BGA X-ray; stackup impedance | DFM | R09 |
