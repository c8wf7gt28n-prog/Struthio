# Recovery dossier: USB0 / FEL and first-board NOR programming (corrective handoff §6, gate G3)

## 1. Hardware provisions (in the R08 schematic)

| Provision | Where | Purpose |
|---|---|---|
| USB-C J1 → USB0 D+/D− (F133 pins 115/114) through ESD U2 (TPD2EUSB30) | `usb_power` sheet | BROM FEL device and the later USB debug service. USB1 (host) is unconnected (D-04) |
| USB-C sink only: TUSB320LAI U1 in UFP/GPIO mode, DNP 5.1 kΩ Rd fallback; no VBUS source path | `usb_power` | board powered from any Type-C source; no thumb-drive host |
| SW2 "FEL": NOR /RESET to GND | `boot_nor` | holds the NOR in reset during F133 reset, so the BROM cannot read boot0 |
| SW1 "RESET": U8 MR# | `power` | a clean F133 reset with the full ≥ 64 ms supervisor delay |
| TP F133_RESET_N, the SPI0 TPs, DNP header J2 (SPI0 + T35_SS_N + NOR_RESET_N + F133_RESET_N) | `boot_nor`, `power` | SOIC-16 clip or external programmer while the F133 is held in reset |
| UART0 header J10 (PE2/PE3) | `controls` | console for the BROM-independent diagnostics |

## 2. Procedure A: USB FEL (primary; the BROM fall-through is UNDOCUMENTED and must be confirmed on the first board)

1. Power from a current-limited 5 V supply (≤ 1.5 A limit) through the USB-C cable. The PC is the host.
2. Press and hold SW2 (FEL). Press and release SW1 (RESET). Release SW2 after ≥ 0.5 s, by which time the BROM has given up on SPI NOR.
3. On the PC, run `xfel version`. It must report the D1/F133 chip ID 0x00185900. **If nothing enumerates, stop:** the fall-through assumption is false for this silicon/eFuse lot. Use procedure B and report it as a P0 finding.
4. Run `xfel spinor`. It must print the W25Q256JV ID (EF 40 19) and 32 MiB.
5. Load the diagnostic image into SRAM and run it without touching the NOR. `xfel write 0x20000 arc1_r08_diag.egon` followed by `xfel exec 0x20060` is **R09 to confirm**: the address follows the R07/R08 link map (eGON header at 0x20000, entry at 0x20060). This command sequence is NOT verified.
6. Program the NOR: `xfel spinor write 0 arc1_r08_diag.egon`, then (R09) the loader, slots and recovery image at the offsets in `NOR_BOOT_AND_FLASH.md`.
7. Verify: `xfel spinor read 0 16384 readback.bin` and `sha256sum` both files. For the upper half, run `xfel spinor read 0x1000000 ...`.
8. Power-cycle without SW2. The UART must show `ARC-1 Compact R08 F133 diagnostic image` and `BOOT_SEL_PAD[12:11] = 0x00000000`.

## 3. Procedure B: SOIC-16 clip (guaranteed path; independent of BROM behaviour)

1. Board powered. Hold F133 RESET low: TP F133_RESET_N to GND, or hold SW1 (U8 MR#).
2. The T35 is unpowered and isolated (T35_PWR_EN pulled down, buffers high-Z). The MN820 does not touch SPI0.
3. Attach the clip to U16. Use a 3.3 V programmer (CH341A-class at 3.3 V, or a Dediprog) with flashrom: `flashrom -p ch341a_spi -c W25Q256JV_Q -w image.bin`. The chip name must match flashrom's database.
4. flashrom leaves the device in 3-byte mode with EAR = 0 after power-down (ADP = 0). Power-cycle before releasing reset.
5. **Back-power check (bench):** the programmer's VCC must not be connected while the board is powered. Use a programmer with VCC sense or with VCC disconnected.

## 4. Status

| Element | Class | State |
|---|---|---|
| USB0 wiring, ESD, sink-only Type-C | C (native schematic, ERC 0) | designed |
| BROM fall-through to FEL with the NOR held in reset | — | **UNDOCUMENTED → bench P0** |
| xfel F133 SPI NOR support | A (third-party source) | untested |
| Clip programming path | B (state analysis) | designed, untested |
| Blank-NOR first boot | — | expected FEL (same open item) |
