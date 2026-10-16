# R10 — datasheet and vendor-document findings (2026-10-16)

Read for the open items "validate the exact memory parts" and "resolve the D213 risk". Labels: **DOC** = read in a
vendor document or vendor source code; **SEC** = third-party. Full source list with URLs, revisions and section
numbers: §6. Values not found are listed as open; nothing was filled in from typical figures.

## 1. Consequences for the design (what changed)
| Finding | Label | Consequence | Done in this pass |
|---|---|---|---|
| D21x **boot ROM USB upgrade mode downloads to SRAM/DRAM and executes**; it does not write flash ("仅支持下载数据和组件到 SRAM/DRAM，以及执行下载的组件") | DOC | The single-NOR plan's key unknown has a documented mechanism. Still open: DDR3 init is a **closed binary** ("PreBootProgram" + ddr_init.bin, loaded to SRAM 0x00103000 first); whether BROM EXEC needs a signed/AIC-format image; the UPGRADE-BOOT pin; the host side must be re-implemented on the F133 (protocol: USB bulk CBW/CSW "USBC/USBS", "UPGC/UPGR" commands 0x02 WRITE, 0x04 EXEC — device side open source, host tool closed; an unofficial Rust host exists) | `firmware/d213_flashless_proof/PLAN.md` P1 updated |
| D21x GMAC: jumbo frames up to 10 240 B (MAC reg 0x0020 bit 4 JE; bit 5 2K packets); vendor driver default 1524 B | DOC | Whole-tile 2092-byte RRES frames are possible with JE set; half tiles remain the fallback | `d213/gmac_link/PLAN.md` item 1 |
| D21x RGMII delays: SYSCFG GMAC0_CFG (0x1800_0410) TXDLY_SEL [16:12], RXDLY_SEL [22:18], 32 steps of **170 ps** (0–5.3 ns), clock invert bits | DOC (vendor code + SDK doc) | Same calibration method as the F133 link (sweep, centre of the passing window); range covers the 1.5–2 ns RGMII skew | `d213/gmac_link/PLAN.md` item 5 |
| Luban-Lite bare-metal builds include the **GE and DE drivers** (helloworld runs LVGL); CherryUSB device stack with a bare-metal OSAL | DOC (vendor code) | "vendor-compatible bare-metal" (R10 §12.1 item 5) is available; USB vendor-bulk graphics link can sit on CherryUSB | `d213/boot_and_display/PLAN.md` SDK risk |
| D213ECV listed with **5 in stock** at LCSC (C19268972, $15.56 @1) | SEC (listing snapshot) | Sample quantity obtainable; production supply still unconfirmed (R10 Q1) | gate report |
| W25Q512JV: IDs EF4020 (IQ/IN) / EF7020 (IM), ADP = 0 factory, dedicated 4-byte opcodes, EAR volatile, tPP ≤ 3.5 ms, tSE ≤ 400 ms, 03h ≤ 50 MHz | DOC | Matches the driver rows and timeouts (5 ms / 500 ms); comment changed from ASSUMED to DOCUMENTED | `spi_nor.c` |
| W25Q512JV **-IQ/-IN have QE = 1 fixed (HOLD# disabled)**; -IM has QE = 0 | DOC | IO3 is a data pin on -IQ; the R08 10 k pull-ups on IO2/IO3 stay harmless. Pick -IQ or -IM consistently with the F133 boot-ROM read mode (bench) | note |
| W25Q512JV individual block locks (WPS = 1) are **volatile and all set at power-up** | DOC | Fits the partition rule "locked": with WPS = 1 every block is protected after reset and the updater unlocks only its target slot (36h/39h). The R10 bootloader does not issue lock commands yet — OPEN | partition note |
| W25Q512JV SFDP BFPT DWORD1 [18:17] = 01b (3- or 4-byte) | SEC (QEMU table) | the driver's SFDP check for > 16 MiB parts passes; vendor SFDP note not found | — |
| AS4C16M16SA -6/-7 AC table (tRC/tRFC 63 ns for -7, tAC 5.0/5.4 ns CL3, tOH 2.5 ns …) | DOC | controller parameters set to the documented worst case, CL3; model checks them (0 violations). **Read capture does not close at 80 MHz without a phase-shifted capture clock** | `analysis/R10_SDRAM_TIMING.md`, `sdram_ctrl.sv` |
| APS3204L-3SQNA-SN exists: 32 Mb, 2.7–3.6 V, SOP-8 150 mil, APS6404L opcode set, tCEM 8 µs, 1 KB page, tPU 150 µs, 133 MHz @ 3.0 V | DOC | The 12F PSRAM assumption (APS6404L-compatible protocol, 8 µs tCEM, 1 KB page) is confirmed; 4 MiB range enforced in RTL | `R10_12F_MEM_FIT_TIMING.md` |
| ECP5 IDCODE LFE5U-12 = 0x2111_1043, LFE5U-45 = 0x4111_2043 | DOC (FPGA-TN-02039-2.5 App. B Table B.5) | matches `R10_IDCODE_LFE5U_12` and `ECP5_IDCODE_LFE5U_45` | header comment |

## 2. Still open after this research
- D21x: PBP/DDR-init binary is closed (no source); BROM image format/signing for EXEC; UPGRADE-BOOT pin; SYSCFG and
  MAC register pages read in vendor code, not in the user manual.
- W25Q512JV vendor SFDP table; a W25Q512JV-IM SFDP dump.
- AS4C16M16SA: 2017 MDS sheets not read; ECP5 SDR I/O timing numbers (DS-02012) for the capture budget.
- APS3204L vendor ID byte.

## 6. Sources
- Winbond W25Q512JV Rev I (2026-05-05), Rev B (2019-06-25); W25Q512JV-DTR Rev D (2020-06-29) — winbond.com resource files.
- Alliance Memory AS4C16M16SA-C&I Rev 3.0 (March 2015); AS4C16M16SA-Automotive Rev 2.0 (March 2015).
- AP Memory "APS3204L-3SQNA-SN QSPI PSRAM" Rev 1.1 (2024-01-05); apmemory.com SPI/QSPI product table.
- ArtInChip D21x Datasheet v1.4 (2024-10-17); aicdoc.artinchip.com pages: MAC function (D21x), AICUPG burning,
  Luban-Lite custom boot, MAC Ethernet configuration, BROM upgrade start mode; Luban-Lite github.com/artinchip/luban-lite
  commit 77fbe30 (v1.0.3, 2024-02-23).
- Lattice FPGA-TN-02039-2.5 (January 2026) Appendix B; Project Trellis devices.json (cross-check).
- LCSC product C19268972 (listing snapshot 2026-10-16).
