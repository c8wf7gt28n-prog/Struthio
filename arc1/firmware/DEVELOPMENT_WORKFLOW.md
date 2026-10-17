# ARC-1 firmware workflow — R02 integration

Firmware and SDK belong in one source repository with **separate build artifacts**.

## Edit and compile

On Windows 11 open this directory in VS Code, Visual Studio (as folder), or any text editor.
For a DOS-style launcher double-click `START_ARC1.cmd` or run `arc1.cmd firmware status`
from CMD/PowerShell. Python 3 and a C11 compiler are prerequisites.

```text
arc1 firmware status
arc1 firmware build --target status-lcd --toolchain host
arc1 firmware build --target graphics-link --toolchain host
arc1 firmware test
arc1 firmware build --target status-lcd --toolchain riscv-clang
```

Last command requires a Clang toolchain with RISC-V code-generation support; emits **a freestanding RISC-V object only**, not a linked F133 image. There is no validated F133/D213 BSP, startup assembly, linker script, target sysroot, signature chain, or on-board debugging in this revision.

## Edit locations

- `firmware/f133/src/lcd_status.c` + `include/arc1/lcd_status.h`: shared status presentation logic (transport-independent).
- `firmware/include/arc1/brand.h`: official identity and boot stage definitions.
- `firmware/imports/r10/f133_graphics_link/`: real archived R10 command protocol source; object compilation and host tests supported.
- `firmware/imports/r10/f133_bootloader/`, `d213_gpu_driver/`, `d213_fpga45_loader/`: untouched imports, **not yet standalone builds**; original R10 build relied on sibling source directories unavailable in this subset. Do not imply a flashable boot image exists.

## Why device flash remains disabled

No assembled board or tested recovery path exists; the R10 NOR partitions and boot straps are not physically qualified. An object file is not a bootable image. Allow building and testing now; add device detection, signed package verification, user-authorized write, readback and recovery tests before enabling flash later. Never silently upload an image from a build command.

## LCD status

The `arc1_lcd_emit` service pads two ASCII lines to 16 characters and only emits READY after evidence flags for all four chips and NOR validation are present. These flags are supplied by future hardware diagnostics; the service cannot test the chips by itself. The 4-wire SerLCD physical implementation using candidate F133 PB3/PB2 is pending pinout/voltage/board review; an actual I2C transport HAL is **not** supplied by this starter source.

Host unit tests cover row formatting, READY gating, FAULT state, invalid arguments, and the preserved R10 graphics-link protocol. Run the tests after modifying C code.

Native Windows execution is **designed, not yet tested on Windows 11**. This development bundle has been built/tested on a Linux host.
