# R04 F133/D213 linked-stage artifacts — NOT BOOTABLE

These files prove that a freestanding RISC-V 64-bit image can be compiled, linked, mapped, and mechanically inspected by Workbench. They **do not** implement production startup, DRAM training, BSP/HAL, Boot ROM headers, NOR image envelopes, D213 load paths, or hardware I/O. Even their link address 0x00020000 is a hypothetical build-stage choice, and **must not be used as a validated D213 memory address**.

`python arc1 firmware image --target all` builds both `.elf`, `.bin`, `.map` and the JSON manifest if LLVM Clang, LLD and llvm-objcopy are available. The emitted `.bin` files are deliberately labeled `LINK_TEST_ONLY`, never as deployable firmware. Do not flash them. A true boot image requires documented executable SRAM/DDR layout, reset/boot-ROM handoff, clocks, memory init, UART and recovery checks against silicon manuals and actual board measurements.
