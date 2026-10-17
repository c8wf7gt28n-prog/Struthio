# ARC-1 Workbench — execution plan after R03

**Official product name:** ARC-1 Workbench — Adaptive RISC-V Console Development System.  
**Source of truth:** R10 hardware handoff; hardware board fabrication HOLD.  
**Host platform target:** Windows 11 x64, using Command Prompt/PowerShell; Python.org 3.11+ with Tkinter. Native Windows validation has NOT yet occurred.

## Pass 1 — Windows shell and source development (R03 initial implementation)
Deliver GUI that opens actual SDK and firmware files, saves source and invokes the real build, sim and test commands. The interface must show device `NOT CONNECTED`, distinguish host-only object builds from boot images, and keep flash disabled. Add Windows 11 smoke test, compile adapter for MSVC/Clang/GCC, packaging to EXE, and UI accessibility validation as the next refinements. Only host/Linux/Xvfb smoke tests are presently proven.

## Pass 2 — F133 and D213 linked target firmware
Create genuine target definitions with toolchain probes, SDK/BSP provenance, startup assembly, memory maps, linker scripts, reset vectors, F133 core initialization and D213 graphics initialization stubs. Generate `.elf`, `.map`, `.bin`, ELF metadata and SHA-256 without writing the board. Validate build determinism, resource size and partition geometry. Do not claim bootability until verified against vendor boot requirements.

## Pass 3 — LCD and boot-event protocol
Qualify the candidate F133 PB3/PB2 TWI0 pins electrically against R10 schematic, boot pin mux and voltage domain. Specify I2C module connector, 3.3V supply/filtering, bus pull-ups, cable length, ESD and powered/unpowered behavior. Implement a bounded nonblocking LCD queue, 16×2 formatting, bus timeout and recovery, reset-stage and error codes. The hardware power/FAULT indicators must not depend on successful CPU firmware execution. Test all stages in the Workbench simulated LCD; differentiate `POWER PRESENT` from `F133 ALIVE` and `SYSTEM READY`.

## Pass 4 — USB removable game cartridge, executable and asset loader
Formal game package manifest, version and integrity metadata; FAT32 read support in the hardware platform; per-asset asynchronous IO and buffer ownership by F133/D213; latency/throughput/cancel/remove tests. Implement a fake host source that injects outliers and resource limits. An off-the-shelf USB drive can remain mounted while the game runs; the code should be preloaded or fault-managed and should not rely on executing directly from USB 2.0. Define controller polling latency targets and supply limits on the shared USB hub.

## Pass 5 — System launcher and graphics pipeline
Create a true launcher running through the same public ARC-1 runtime used by games. Connect F133<>D213 rendering protocol and 45F tile/raster reference model, maintain a software fallback, simulate bandwidth and transfer contention, render branding and per-game identities separately. Start with a minimal STRUTHIO vertical slice, not with a completed game port.

## Pass 6 — Bench diagnostics and qualified deployment
Implement read-only presence detection, serial log capture and true status reporting. Add full NOR image assembly, partition validators, duplicate manifest/rollback protection and recovery planning. Physical write commands require independent first-article bench evidence of cold boot, recovery and flash verification plus explicit user authorization. If these are missing, keep deploy blocked and supply dry-run files.

## Cross-cutting release gates
1. All actions have explicit result labels: `HOST_SIM`, `STATIC_CHECK`, `BOARD_OBSERVED` only with actual hardware, or `NOT_AVAILABLE`.
2. All software targets are derived from versioned R10 pin/memory interfaces; interface changes must trigger reconciliation.
3. No test reports software build PASS as evidence of hardware operation.
4. Windows 11 native execution and toolchain compatibility are mandatory before declaring Windows support complete.
5. Official ARC-1 branding uses the supplied artwork without alterations to logo design; games retain their own separate identities.
