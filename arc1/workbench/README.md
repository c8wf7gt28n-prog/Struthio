# Workbench R07 — Host launcher / workspace presets

Use F6 for the host cartridge shelf, Ctrl+P for Quick Open, Ctrl+Shift+P for commands, View for presets. See PATCH_NOTES_R07.md at project root for verification and limitations.

# ARC-1 Workbench R06 — Orange Aqua

Run `python -m workbench.app` or double-click `START_ARC1.cmd` on Windows 11.

- Compact branded 51-pixel title strip, with File Manager/Word 6-inspired workflows.
- File > Open, Save; F5 builds staged F133/D213 firmware targets, F9 toggles diagnostics, Ctrl+F finds source.
- Cartridge menu makes/inspects/imports a checksummed `.arc1cart` and runs host streaming models.
- Drag internal file onto another directory to copy after confirmation; no silent moves or overwrites.
- Native OS external drag/drop is optional and uses tkinterdnd2/TkDND if installed. Fallback is Cartridge > Import.
- Machine UI `python arc1 agent` accepts JSON-lines, documented in `docs/AGENT_INTERFACE_R04.md` and R06 cartridge specs.
- `INSTALL_ARC1.cmd` is a per-user Windows installer with drag-to-My-Apps UI; portable drag-folder installation is also supported.
- Never mistake hosted simulations, linker smoke targets, or visual status for physical hardware proof.
