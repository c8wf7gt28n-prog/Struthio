# ARC-1 Workbench R09 — Output panel

The lower black/graphite pane is a **PC host console**, not an ARC-1 motherboard terminal. It records actual commands executed by the SDK and their textual output.

## Keyboard and visibility

- **F10**: hide/show the bottom pane. This frees vertical editor space.
- **F5**: run the configured firmware link-stage build; automatically reveal Build Output.
- **Code / Cartridge / Debug** presets: saved preferences include output visibility. Code and Cartridge default to hidden; Debug defaults to visible. Last per-preset selection persists.
- **F9**: separate toggle for the right diagnostics panel.

## Five tabs

- **Console**: chronological session output (DOS-like interface, currently read-only).
- **Build Output**: log of the most recently executed SDK command.
- **Problems**: GCC/Clang/MSVC warning and error extraction, reporting explicit exit status even if parsing fails.
- **Debug**: host simulation state, not physical CPU registers. More tools are forthcoming.
- **Agent Activity**: an honest disconnected indicator. The external JSON-lines agent API does not yet feed the GUI.

Do not display `READY` for hardware unless physical evidence exists. R09 cannot flash or boot real hardware. Windows 11 and Qt native GUI have not been runtime-tested.
