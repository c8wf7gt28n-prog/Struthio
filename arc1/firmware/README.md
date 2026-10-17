# ARC-1 platform firmware — shared development workbench

This folder establishes where the ARC-1 system firmware should live, inside the
**same development repository as the SDK** but as **separate target builds**.
This patch includes a shared identity/LCD stage header **and a preserved R10 firmware SOURCE snapshot** under `imports/r10/`, imported from the latest handoff without compiling or modifying its source.
**No flashable F133 or D213 boot image, NOR flash writer, FPGA image, or working LCD driver is provided, compiled, or validated by this change.**

Proposed target tree (not yet implemented):

- `firmware/f133/` — F133 startup, USB host, game streaming, diagnostics, LCD driver
- `firmware/d213/` — video processor bring-up, graphics and HDMI composition
- `firmware/fpga/12f/` — 12F FPGA configuration and host protocol
- `firmware/fpga/45f/` — 45F GPU configuration and host protocol
- `firmware/boot/` — shared image metadata, safe update and recovery contracts
- `firmware/include/arc1/brand.h` — shared textual identity and LCD boot stages

## LCD requirements

Proposed I2C connection is F133 PB3/PB2 through a replaceable 3.3-V display
module **only after Astra confirms** the exact package pinout, boot-ROM behavior,
I/O voltage, pin mux, pull-ups, mechanical placement and bus fault behavior.
The LCD may present a module-stored splash at power-on, but NOR integrity,
F133 boot success, FPGA state and USB status require an executing processor to
read hardware and report what actually happened. Hardwired PWR/FAULT indicators
are a separate hardware matter. Never display READY from a fixed delay.

See `../docs/BRANDING_FIRMWARE_INTEGRATION.md` for decisions and acceptance gates.

## Existing R10 firmware code is preserved, not replaced

The uploaded `ARC1_R10_UPDATED_20261016.zip` already contains an F133 bootloader
source tree, F133 graphics-link sources, D213 GPU driver sources, and a D213 FPGA
loader. These are now mirrored **unchanged** in `imports/r10/` with checksums.
Future steps must integrate them into clean target builds, not create redundant
second implementations or assume these were validated on the assembled board.

## R02 live build workflow

`python arc1 firmware build` compiles a real LCD status module to an object; `python arc1 firmware test` runs its tests and the imported R10 graphics-link tests. A RISC-V Clang can compile the LCD object for RV64. **This is not a linked image and not a physical SerLCD driver.** See `DEVELOPMENT_WORKFLOW.md`.
