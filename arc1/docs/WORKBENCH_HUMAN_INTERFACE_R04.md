# ARC-1 Workbench human interface: WINFILE.EXE + Word 6 design language

The Windows 11 application intentionally uses classic desktop operating patterns, **not** a modern web app or a visual clone of Microsoft software.

- **Directory navigation**: expandable tree pane on the left, sortable-style file details in the main list, file-open on double-click, visible current directory field.
- **Document editing**: predictable plain text source editor with undo, cut/copy/paste, find, mouse selection, cursor-position status and explicit save; no hidden autosave.
- **Traditional commands**: File, Edit, View, Build, Tools and Help menus; visually raised toolbar controls. F1 help, F5 build, Ctrl+O open, Ctrl+S save, Ctrl+F find. Designed for mouse and keyboard.
- **Build feedback**: terminal-style results pane; explicit PASS/FAIL and warnings. Compilation never claims successful on-board execution.
- **Diagnostics**: status LCD simulator and device-condition panel, visibly labeled `HOST SIM ONLY` and `NO BOARD`.
- **Agent separation**: agents use a formal stdio JSON interface, not mouse coordinates or clipboard automation. The human can edit in Workbench while the agent reads the same files; opt-in guarded writes require the old SHA-256 to match.

## Planned experience after R04

R05: Real F133/D213 BSP evidence, boot messages linked to qualified bring-up states, better build target chooser and source diff.

R06: LCD transport and fault simulation with verified PB3/PB2 electrical assignment; per-chip stage tracing.

R07: Cartridge image format, removable-media model and asynchronous streaming under host simulator.

R08: Branded game launcher, D213 graphics queue and 45F/12F reference fallbacks.

R09: Read-only first-article diagnostics, FPGA image metadata, approved recovery-aware deployment after hardware testing, Windows 11 native qualification and installer.

Release rule: ability to *compile* never implies ability to *flash*.
