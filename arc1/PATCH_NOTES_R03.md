# R03 — First Runnable ARC-1 Workbench Window

The official public name is **ARC-1 Workbench** — Adaptive RISC-V Console Development System.

- Added Python standard-library graphical development shell for Windows-first use.
- Existing R02 CLI and imported R10 source trees retained; no changes to the actual electrical design.
- Added source editor, save, validated path handling, host build/test runners, simulated LCD, official branding and six-pass roadmap.
- Added `START_ARC1.cmd` for graphical launch; previous text launcher preserved as `START_ARC1_TEXT.cmd`.
- All hardware deployment remains disabled until physical proof of recovery and programming.
- Validation target: smoke test GUI in an X virtual framebuffer, run host build and tests, test no-flash policy and report native Windows testing as outstanding.
