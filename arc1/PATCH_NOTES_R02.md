# R02 — Unified SDK/Firmware workbench

- Created single `arc1 firmware` command family: `status`, `build`, `test`.
- Added portable LCD boot status firmware logic with explicit READY evidence gating and host tests.
- Added optional RISC-V64 clang compile-only mode for LCD module (not a bootable binary).
- Added existing R10 F133↔D213 graphics protocol module to firmware object build and host testing.
- Added native Windows `arc1.cmd` and DOS-style `START_ARC1.cmd` launcher; Windows 11 execution not yet verified.
- Kept archived R10 import source and official branding art unchanged.
- Hardware deployment still intentionally blocked; a separate, eventually gated flashing action is required.
- This revision is a **development integration**; F133/D213 target BSPs and boot images not yet validated.
