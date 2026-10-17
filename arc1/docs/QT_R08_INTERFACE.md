# ARC-1 Workbench R08 — restrained orange Aqua / Qt 6 prototype

## Intent

R08 is an **experimental alternative human desktop**, not a replacement for the verified R07 Tk application. This uses Qt 6 / PySide6 QMainWindow, QDockWidget, QFileSystemModel, QTabWidget, QPlainTextEdit, QProcess, and QSettings.

**The same R07 back-end powers both desktop shells and the existing agent interface.** The agent's JSON-lines command protocol is unchanged: `python arc1 agent`. Source files, firmware tests, cartridge checks, and launcher state machines are shared.

## Visual authority

The latest visual specification is *orange Aqua, but not cartoonish*. Preserve the official metallic ARC-1 logo and orange color; reduce button saturation and bulk. Standard buttons have 3–4 px radii, restrained graphite surfaces, hairline edges and modest padding. Orange identifies the active editor tab, focus, and selection—not every button. Single compact branding/action strip; other controls belong in menus, shortcuts and docks.

## Windows usage

- Install Python 3.11+ and PySide6 (`py -3 -m pip install PySide6`).
- Extract the complete project folder (do not run scripts directly from the ZIP).
- Run `START_ARC1_QT.cmd` from the project root.
- For the proven original GUI use `START_ARC1.cmd` (Tkinter, no PySide6 requirement).
- For AI agents use `py -3 arc1 agent` and `docs/AGENT_INTERFACE_R07.md`.

The Qt application has **not** been executed or screenshot-tested because PySide6 is unavailable in this build environment. Its Python source has been syntax validated and host-side backend tests are executed separately. Native Windows 11 packaging and functional Qt QA remain required.

## Implemented Qt desktop source

- Native dockable Project Files, Build Output, Inspector/LCD, Cartridge/Game preview.
- Tabbed multi-document C/Python/JSON source editing with atomic saves and dirty-close prompts.
- Menus, compact toolbar, file Quick Open, command palette, search and replace.
- QProcess-backed SDK/F133/D213 link-test build commands, with genuine process exit codes.
- Local cartridge verification, drag-import with explicit copy/replacement consent, host game launch, host frame preview, and deterministic USB stream model.
- Named Code / Cartridge / Debug layouts and Qt persistent geometry/dock state.
- Shared `HostLauncher`, `Cartridge`, `BootModel`, and unmodified structured agent interface.

## Engineering truth / restrictions

- The F133 and D213 linker-stage images are NOT bootable firmware and no ARC-1 board is connected.
- Simulated LCD stages are synthetic. No real I2C display path is verified.
- `.arc1cart` archives contain assets and manifests only. Never execute code contained in a cartridge.
- Actual USB read performance, FPGA function and console deployment are unproven.
- No flash write, firmware installation or board-deploy command is available.

## Next gate

Install PySide6 on native Windows 11; run menu/edit/dock/drag/backend smoke tests, high DPI and keyboard/accessibility audit. Only after Qt qualification should it replace the Tk default. Add real code-editor search/navigation and a graphics diagnostics lab in subsequent passes.
