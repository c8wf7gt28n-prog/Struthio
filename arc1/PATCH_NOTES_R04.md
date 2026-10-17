# ARC-1 WORKBENCH — R04 / PASS 2

2026-10-16 — Two interfaces, one project and first linked target artifacts.

## Added

- Human-facing GUI redesigned after **Windows File Manager (`WINFILE.EXE`) and Word 6**: File/Edit/View/Build/Tools/Help menus, directory tree, file contents panel, source editor, Ctrl+O/Ctrl+S/Ctrl+F, F1 help, F5 build, DOS-like output and status LCD simulation.
- Second AI-agent-facing user interface: `py -3 arc1 agent` stdio JSON-Lines (`arc1.agent/1`) for capabilities, project status, source navigation/read, builds and tests. Optional SHA-protected source writes only with `--allow-writes`. No automatic or physical flash operations.
- Freestanding LLVM RISC-V 64-bit link stage for **F133** and **D213**: ELF, raw BIN, linker maps, SHA-256 manifest. F133 link-stage includes actual existing `lcd_status.c` and statically emits a boot-state message into a RAM buffer; no physical I2C output.
- `firmware image --target f133|d213|all` CLI and R04 smoke test.
- Windows `START_ARC1_AGENT.cmd` and explicitly permission-gated `START_ARC1_AGENT_WRITE.cmd`.

## Evidence and limitations

- LLVM Clang/LLD/llvm-objcopy generate the two ELF/BIN artifacts in a Linux test environment. ELF header confirms 64-bit RISC-V executable format; neither image is a silicon-approved boot image.
- Linker base 0x00020000 is a placeholder for link testing, **not a verified D213 address**. There is no ROM header, genuine DRAM bring-up, peripheral initialization, verified boot handoff or image signing.
- Existing two firmware unit tests and four host game tests pass. GUI+agent smoke passes under Xvfb Linux desktop. Native Windows 11 has NOT been qualified.
- Full R10 bootloader and D213 graphics sources remain imported/preserved and are NOT yet linked into target firmware. F133/D213 entry functions are development-only stubs.
- All hardware flashing is still unavailable and must not be inferred from `Build PASS`.

## Remaining Pass 2 production work

1. Obtain and lock manufacturer boot ROM, SRAM load and memory-initialization details for both SoCs.
2. Prove F133 ROM-compatible eGON header and safe recovery entry using actual silicon or vendor reference board; validate DDR initialization.
3. Prove D213 boot-transfer/initialization method and real DRAM training.
4. Port tested bootloader/NOR code and D213 display/GPU driver against qualified F133/D213 board-support packages.
5. Integrate hardware UART, I2C LCD, clocks, interrupt controllers, USB link, watchdogs and fault reset.
6. Replace placeholder memory map with verified per-device linker scripts and bootloaders; run first-board tests before marking images bootable or deployment possible.
