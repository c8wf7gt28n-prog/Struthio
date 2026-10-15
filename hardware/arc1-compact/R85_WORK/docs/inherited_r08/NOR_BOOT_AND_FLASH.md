# Flash image dossier: 32 MiB boot NOR (R08, corrective handoff §5, D-01/D-02)

## 1. Device

W25Q256JVFIQ (Winbond):
- 256 Mbit = 33,554,432 bytes; SOIC-16 300 mil; 2.7–3.6 V.
- 133 MHz, or 50 MHz for the 03h read.
- JEDEC ID EF 40 19. QE is fixed at 1, so IO2/IO3 always act as data pins: both get pull-ups.

The SOIC-16 package was chosen over WSON-8 or BGA for three reasons:
- it has a dedicated /RESET (used for forced FEL);
- it can be programmed with a test clip;
- it can be probed visually.

Source: W25Q256JV DS Rev I §3.4 and §9 (`sources/glue/glue_facts.json`). Lifecycle status and JLC stock are
**NOT_FOUND / R09 sourcing**.

## 2. Partition plan (`firmware/include/flash_layout.h`, checked by `fl_layout_check`)

| Region | Base | Size | Contents | Notes |
|---|---|---|---|---|
| BOOT | 0x0000000 | 1 MiB | boot0 (eGON) at 0, ARC-1 loader at 0x10000 | single copy. The BROM reads offset 0 only (community practice, UNDOCUMENTED). Updated only with the FEL or clip procedure |
| JOURNAL | 0x0100000 | 64 KiB | 2 × 4 KiB ping-pong sectors of 32-byte boot-state records (seq + CRC32) | a torn write leaves the previous record valid (HOST_TESTED) |
| SETTINGS | 0x0110000 | 64 KiB | user settings, same ping-pong scheme (format R09) | |
| RECOVERY | 0x0120000 | 3.875 MiB | minimal recovery system (USB device service) | not needed to enter FEL |
| ASSETS | 0x0500000 | 4 MiB | boot-critical assets + a T35 diagnostic bitstream copy | games stay on microSD |
| SLOT_A | 0x0900000 | 7 MiB | system image A | lower half |
| SLOT_B | 0x1000000 | 7 MiB | system image B | **starts exactly at 16 MiB**: every update to B exercises 4-byte addressing |
| SPARE | 0x1700000 | 9 MiB | growth; last 64 KiB (0x1FF0000) = factory capacity-test block | |

Image header: 64 bytes, magic "A1IM", kind, length, CRC32 of the payload, load/entry address, version, build ID and header CRC.

**A/B rule** (`fl_boot_select`, HOST_TESTED):
- A trial image gets 3 attempts, and each attempt is consumed *before* the jump.
- An exhausted or invalid trial is marked bad, and the board falls back to the confirmed slot.
- A valid but unconfirmed image in the other slot runs as a trial.
- After that comes the recovery image, then NONE.

**Install** (`fl_install_update`):
1. Disarm any trial on the target slot.
2. Erase, program and read back the image.
3. Check the CRC.
4. Arm the trial.

## 3. Image-size ledger (corrective §5: measure, do not assume)

| Image | Status | Size | Evidence |
|---|---|---|---|
| R08 diagnostic boot0 `arc1_r08_diag.egon` | BUILD_ONLY | **16,384 bytes** file, 13,268 bytes used of the 32 KiB SRAM A1 | `f133_diag/` and the runner log `f133_diag_build` |
| R07 bring-up boot0 `arc1_r07_f133.egon` | BUILD_ONLY (R07) | 8,192 bytes | R07 evidence |
| ARC-1 loader (second stage, DRAM init) | **NOT WRITTEN** | — | R09 firmware item. F133 DRAM init code is not available in R08 |
| System image (launcher, BT820 graphics, audio mixer) | **NOT WRITTEN** | — | must fit 7 MiB per slot. No Linux is assumed; a bare-metal/RTOS launcher is the working assumption |
| Recovery image | **NOT WRITTEN** | — | ≤ 3.875 MiB |
| T35 bitstream | known size | 8,139,168 bits = 1,017,396 bytes | Efinix AN006 (`sources/efinix`); lives in the T35 config flash U19 (W25Q32JV), with a backup copy in ASSETS |

The 7 MiB slot size is a plan, not a measurement. Once real binaries exist, R09 must re-run `fl_layout_check` against the sizes.

## 4. Programming and lifecycle

- **First assembly, primary route:** USB FEL with `xfel spinor write 0 <image>`. xfel supports F133/D1s (chip ID 0x00185900). Its SPI routine configures only PC2–PC5; IO2/IO3 are held by the board pull-ups.
  - **Status:** documented by a third party and untested here.
- **Guaranteed route:** a SOIC-16 test clip with F133 RESET held low (TP on F133_RESET_N).
  - In reset, the F133 SPI0 pins are inputs and the T35 is unpowered and isolated.
  - Any 3.3 V SPI programmer works: flashrom with W25Q256JV support, which uses 4-byte mode or EAR internally. **After any external programming, run `nor_prepare_reboot`, or power-cycle (ADP = 0 restores 3-byte mode).**
- **Verify:** read back the full image and compare against its SHA-256. The diagnostic image prints the JEDEC ID, SFDP data, the eGON magic at 0 and the upper-half test word.
- **Write protection** (R09 firmware): after factory programming, set BP/TB so the BOOT region (lower 1 MiB) is protected and SRP = 0, which keeps it software-reversible during development. The exact BP code for 1 MiB at the bottom of a 256 Mbit part must be taken from the datasheet's protection table; it is not transcribed in R08 (OPEN).
- **Update:** A/B slots as above. boot0 itself is not field-updatable (single copy). A bad boot0 means FEL or the clip, which is acceptable for a development board and documented.

## 5. What is proven (class D only)

`make -C R08_WORK/firmware all` runs 757 host checks plus ASan/UBSan, a freestanding compile and 4 killed mutants. It covers:
- probe and mode repair;
- ID failures: no device, MISO stuck high or low, SFDP/JEDEC size mismatch, unknown 32 MiB part;
- full-capacity lower/upper/boundary reads and writes, under both the 4B-opcode and the EAR strategies;
- page wrap, alignment, a stuck busy flag, WEL that never sets, and a power cut during program;
- the journal across 300 records with ping-pong, plus a torn record;
- the A/B trial/rollback cycle.
