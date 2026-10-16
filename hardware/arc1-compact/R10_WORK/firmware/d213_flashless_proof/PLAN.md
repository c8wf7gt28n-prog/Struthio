# D213 flashless start — proof plan (ARC1_MEMORY_R10 v0.1 §7.3 item 5, gate "D213 flashless boot")

Status: **NOT_RUN** — needs a D213ECV board. The memory spec makes the single 64 MiB NOR **conditional** on this proof
(§3 "Established vs unproven": USB firmware *upgrade* is documented for D21x; executing full firmware loaded into
DDR with no local NOR/eMMC is not). Nothing below is a result.

## What has to be shown
1. From power-on with **no** D213 boot medium (SPI NOR footprint unpopulated, no SD/eMMC), the D213 boot ROM enters
   USB device mode on USB0 and enumerates on the F133's USB1 host.
2. The F133 can download a first stage that initialises the in-package DDR3 and then a graphics firmware image
   (partition D2FA/D2FB, R08 image header kind 3) into DDR3, and **execute** it — not only write it to flash.
3. The downloaded firmware brings up the display (`d213/boot_and_display/PLAN.md` steps 3–5) and answers the
   graphics-link HELLO (`f133/graphics_link`, `gl_dev`).
4. Repeatability and failure behaviour.

## Steps and pass criteria
| # | Step | Pass |
|---|---|---|
| P1 | Read the D21x boot-ROM documentation and the Luban-Lite USB upgrade host tool sources: boot-source order, USB upgrade entry condition (strap/button/empty media), protocol, whether "run from RAM" exists | documented answer with source revision; if "run from RAM" does not exist → fallback §7.2 (D213 local NOR) immediately |
| P2 | PC host (vendor tool) against a bare D213 board: enter USB upgrade with no boot media | enumeration log (VID/PID, descriptors) |
| P3 | Same, download a minimal "UART hello + DDR3 test" image and execute it | UART0 log: banner + 128 MiB DDR3 test PASS |
| P4 | Port the download sequence to the F133 (USB1 EHCI host, bare metal) | same UART0 log, initiated by the F133; image read from NOR D2Fx |
| P5 | Full graphics firmware from NOR via the F133 | display test pattern + `gl_dev` HELLO answered; time from F133 reset to first frame recorded |
| P6 | 100 cold power cycles | 100/100 reach P5; any failure logged with stage |
| P7 | Faults: corrupted D2FA (CRC) → F133 selects D2FB (r10_select); D213 held in reset; USB unplugged mid-download | F133 stays alive with serial/USB diagnostics (memory spec §5.3); D213 retried or reported |

## Evidence to keep (memory spec §7.3: "actual boot logs")
UART0 logs of P3–P7, USB enumeration dump, image hashes (sha256 of the D2Fx payload), SDK/tool revisions,
board revision, and the F133-side log of `r10_select` / download timing.

## Already in place on the F133 side (HOST_TESTED)
- D213 images live in NOR above 16 MiB (D2FA 0x0130_0000, D2FB 0x0230_0000); `r10_select(R10C_D213)` picks the
  confirmed or trial slot and never leaves the NOR in 4-byte mode (`firmware/f133_bootloader`, test `boot_d213`).
- After the firmware runs, `f133/graphics_link` carries commands; `gl_dev` provides the D213-side watchdog that
  shows the 2D fallback screen.

## If it fails
Memory spec §7.2: keep the F133-owned 64 MiB NOR and add the smallest D213-local boot NOR on PB0–PB5 (pads reserved
in `hardware/R10_flash_pinmux.csv`, group D213NOR). FPGA images stay central. Two flash packages, not four.
