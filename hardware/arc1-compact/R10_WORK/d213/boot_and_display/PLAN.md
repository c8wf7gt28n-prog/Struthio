# D213 bare-metal boot and display — plan (R10 §12.1 item 5)

Status: **NOT_RUN** (no D213 hardware, no SDK build in this pass). Gate R10-D. Everything below is a plan with its
pass/fail criterion; nothing here is a result.

## Pads used (from `architecture/R10_interface_matrix.csv`, DOCUMENTED pads)
| Function | D213ECV pads | Note |
|---|---|---|
| Boot SPI NOR | PB0–PB5 (SPI0) | boot source order and strap/eFuse behaviour: read from the D21x user manual before schematic — OPEN |
| Debug console | PA0/PA1 (UART0) | first-light log |
| USB0 device | PU0/PU1 (pins 79/80) | F133 graphics link (`f133/graphics_link`) **and** D213 USB upgrade/recovery — sharing rule below |
| Video | LVDS0 on PD18–PD27 (or parallel RGB on PD0–PD27) | HDMI bridge not selected (R10 §3 "video bridge open") |
| 45F link | GMAC0 RGMII on PE0–PE15 | decision D1, `d213/gmac_link/PLAN.md` |

## Bring-up order (each step gates the next)
1. **Power and DDR.** In-package 128 MiB DDR3: vendor DDR init blob/parameters from the ArtInChip SDK (Luban-Lite);
   pass = memtest over all 128 MiB (walking bits + address-in-address) logged on UART0.
2. **Boot from SPI NOR.** Vendor boot ROM → SPL/first stage from NOR. Pass = cold boot 100/100 power cycles to the
   UART banner. Record SDK revision, toolchain, image hash (R10 Q7).
3. **DE scan-out, no GE.** Static test pattern (colour bars + 1-px grid) from a DDR frame buffer at the first video
   mode the selected bridge accepts; 800×600/60 then 1280×720/60 (R10 §5.2). Pass = bridge reports lock; pattern
   CRC readback from DE write-back (if the DE has one — OPEN) or camera inspection; 10 min without loss of lock.
4. **GE 2D.** Fill, blit, alpha blend, rotate on the GE; compare GE output buffers against a CPU reference (CRC per
   operation). Pass = bit-exact for integer ops; documented tolerance for scaled/blended ops.
5. **Diagnostic video mode.** Built-in screen showing: boot id, F133 link state (`gl_dev` counters), 45F link
   state (RRES STATUS counters), DDR test result. This is also the **fallback screen** that `gl_dev.link_lost`
   selects (R10 §3.1: D213 must show 2D with both FPGAs blank).
6. **Both FPGAs blank.** Repeat steps 3–5 with the 45F and 12F unconfigured (PROGRAMN held). Pass = identical output.

## SDK risk
Luban-Lite (v1.0.3, commit 77fbe30) has bare-metal (`KERNEL_BAREMETAL`) D21x configurations that build the GE and
DE drivers; the bare-metal helloworld runs LVGL on them (DOCUMENTED in vendor code). DDR3 init is a closed vendor
binary (PreBootProgram) — usable, not inspectable. CherryUSB (bare-metal OSAL) provides the USB0 device stack.
