# R08 — Qt source prototype, restrained orange Aqua

- Created PySide6-based professional Workbench desktop shell; same R07 backend/agent engine.
- Compact graphite/ivory controls with thin orange active accents, not large glossy orange buttons.
- Added classic file navigation, dockable panes, source tabs, menu/keyboard actions, console, cartridge shelf, host simulator frame preview.
- Applied restrained button styling to the still-runnable Tk fallback too.
- Reused verified R07 host-only cartridge security and firmware test-stage commands.
- Qt itself cannot be run in this environment because PySide6 is unavailable and package network access is blocked. This is a **code-complete prototype pending GUI qualification**, not a certified running Qt release.
- Windows native tests, high DPI, complete embedded debug tools, USB hardware streaming, bootable firmware and flashing all remain pending.
