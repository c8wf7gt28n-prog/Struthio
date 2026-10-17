# ARC-1 Workbench R05 — Pass 3 (Orange Aqua)

## Human interface
- Official metallic ARC-1 logo unchanged; warm metallic orange Aqua-inspired header, amber glossy rounded buttons, ivory editor/document surface and amber SerLCD preview.
- Retained File Manager-style navigator/files panes, Word 6-era direct editing, menus, keyboard shortcuts, real C firmware builds and tests.
- Host boot evidence is **simulated and explicitly labeled**. No displayed stage or LCD text is real physical telemetry.

## Firmware and agent interface
- C boot monitor: evidence gates, `READY` prerequisites, latched error code, 16-character fault message.
- SerLCD I2C transport-independent byte encoder at default address 0x72, using 0xFE cursor instructions. Real F133 PB3/PB2 TWI HAL and pinmux not yet connected.
- RISC-V F133 link-stage now contains boot monitor and LCD encoding modules; D213 stage remains link-only.
- Agent API adds `boot.simulate` JSON-lines method; cannot flash or run arbitrary commands.

## Evidence and non-claims
- Firmware host tests: 4 tests. F133/D213 ELF/BIN link-stage outputs are clearly marked `LINK_TEST_ONLY`, `board_bootable=false`, `flash_approved=false`.
- Windows 11 UI not yet executed on a physical Windows PC; GUI tested on Linux Xvfb.
- Not available: actual boot ROM-compatible firmware, F133 I2C HAL driver, real rail supervision, USB game streaming, physical cartridge detection, physical flashing.

## Next (Pass 4)
- USB mass-storage host and game-cartridge specification; deterministic asset streaming and fault-injection tests, integrating with agent/UI. Hardware SPI NOR and USB flash writes must remain qualified separately.
