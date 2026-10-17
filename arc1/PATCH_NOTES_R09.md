# R09 — Compact collapsible output and build diagnostics

* The black lower area in earlier screenshots is the **host Build Console / DOS Commands** pane. It is not a physical ARC-1 terminal.
* **F10** collapses/restores this panel; Code/Cartridge workspaces normally hide it while Debug shows it. F5/build actions reopen the output panel and show actual compiler output.
* Added **Build Output**, **Problems**, **Debug**, and **Agent Activity** views to the classic interface; the experimental Qt dock exposes Console, Build Output, Problems, Debug, and Agent Activity.
* Compiler diagnostics are parsed from real host command output. Nonzero exit codes are authoritative even when the compiler message does not match a known pattern. GCC/Clang/MSVC diagnostics can be indexed by file and line.
* Agent Activity has an explicit not-connected message: the headless agent still operates independently, and no live event bus is claimed.
* Existing game, firmware, and agent backend preserved. Real silicon, Windows-native Qt execution, bootable firmware, device debugging, and flash deployment still require later work.
