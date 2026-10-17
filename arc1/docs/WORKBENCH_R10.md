# ARC-1 Workbench R10 — Classic main screen

**Design rule (owner decision, R10):** Workbench behaves like the File
Manager and document editor you already know, and shows the console
engineering tools when a task needs them.

Start it with `START_ARC1_QT.cmd` on Windows, or `python -m workbench.qt_app`.
It needs Python 3.11+ with PySide6 (`py -3 -m pip install PySide6`). The Tk
desktop (`START_ARC1.cmd`) is unchanged and remains the fallback.

![Default screen with two firmware files open](assets/workbench_r10_2_editor.png)

## What is on the screen

- **Title bar:** the standard Windows title bar with minimize, maximize and
  close. Workbench does not draw its own.
- **Menus:** File, Edit, View, Project, Build, Debug, Cartridge, Tools, Help.
  The badge at the right of the menu bar always reads **HOST SIM · BOARD
  OFFLINE**.
- **One toolbar:** Open, Save, Build ▾, Run, Tests and **Target**. The Build ▾
  arrow holds *Build All Firmware Stages* and the target list.
- **Project navigator** (left, about 236 px): ARC-1 › Firmware, SDK, FPGA,
  Games, Cartridges, Hardware, Tests and Docs.
  - FPGA is greyed out: this project holds no FPGA sources (the R10 RTL is in
    the hardware handoff), and the navigator doesn't pretend otherwise.
  - Clicking a folder opens it in the Browse tab.
  - Double-clicking a file opens it.
- **Documents:** one tab per file, with line numbers and a highlighted current
  line.
  - The strip under the editor shows language, target and position, e.g.
    `C11 · F133 · Simulation target   Ln 17, Col 5`.
- **Status bar:** `ARC-1 · F133 · C11 · UTF-8` on the left and **No physical
  device connected** on the right.

These start hidden and appear when the work needs them:

- **Output panel** (F10), with tabs for Output, Problems, Debug and Agent
  Activity. It opens by itself when a build fails, on the Problems tab. A
  successful build only reports in the status bar.
- **Hardware Inspector** (host boot-diagnostic model) and the **Cartridge
  Shelf**, both in the View menu.
  - On a monitor 1900 px or wider, the Inspector opens by itself the first
    time.

## How the screen follows your work

| Activity | Main area | What appears |
|---|---|---|
| Open Workbench with no documents | **Start** tab: open, find a file, browse, new game, recent files | Navigator only |
| Edit firmware or game code | Source editor | Navigator |
| Browse files | **Browse** tab: Name, Size, Type, Date Modified. Optional dual pane (View) | Navigator |
| Build or test | The editor stays in front | Output on failure (Problems tab); status bar on success |
| Run a game | **Preview** tab with the simulator's frames and a frame slider, labelled HOST SIMULATION | Debug tab gets the run summary |
| Inspect hardware status | Hardware Inspector (View), host model only | — |
| Prepare a cartridge | Cartridge menu and Cartridge Shelf | Output shows the inspection |

Saved Code, Cartridge and Debug layouts for each activity are part of R12,
not this pass.

## The everyday workflow

1. **Find a file:** use the navigator, or press **Ctrl+P** and type part of the
   name (`main.c`).
2. **Open, edit, save:** Ctrl+O and Ctrl+S, plus Ctrl+Shift+S to save all.
   Ctrl+Z / Ctrl+Y, Ctrl+F / F3, Ctrl+H and Ctrl+G work as in any Windows
   editor.
3. **Build** with **F7** (or Ctrl+Shift+B). Build picks the target for the
   file in front of you:
   - A file inside a game project (`examples/<game>/…`) builds that game.
   - Any other file builds the selected Target: F133 firmware, D213 firmware,
     the F133 LCD status service or Host game.
4. **Read the compiler error:** a failed build opens Problems with Error,
   Description, File and Line.
5. **Go back to the source line:** double-click the problem, or press **F8**
   (Shift+F8 for the previous one). The line is marked in the editor and the
   gutter.
6. **Run the simulator** with **F5**. It rebuilds the game, runs 120 frames on
   this PC and shows them in the Preview tab.

![A failed build: Problems lists the error; F8 jumps to line 35](assets/workbench_r10_3_build_error.png)

## What Workbench remembers

It remembers the documents you had open (with cursor positions), the active
tab, the target, the recent files, whether the output panel was open, the
panel sizes and the window layout. The next start puts you back where you
were.

To get a clean screen back, use **View › Reset Window Layout**. It restores
the factory layout and keeps your documents open.

The memory lives in one small JSON file:
- Windows: `%APPDATA%\ARC-1\Workbench\session-r10.json`
- Linux: `~/.config/arc1-workbench/`

Every value is checked when it is loaded. A layout saved by a different
layout version is ignored rather than applied wrongly.

## File operations (Browse tab)

New File, New Folder, Rename (F2), Duplicate (makes `name - Copy.c`, as
Explorer does) and Delete (Del, with confirmation, files only). Windows naming
rules apply on every platform, so a project stays portable:
- no `< > : " / \ | ? *`
- no `CON`, `NUL`, `COM1` and the like
- no trailing dot or space
- a name that differs only in upper/lower case counts as the same name

Nothing is ever overwritten. Recorded evidence (`passes/` and
`hardware/sources/`) opens read-only and cannot be renamed or deleted from
Workbench.

## One engine for people and agents

```
Qt window ─┐
CLI ───────┼──►  workbench/engine.py  ──►  arc1 CLI commands  ──►  host compiler / simulator
agent ─────┘     (targets, plans,           (validated, timeouts,
                  problem paths)             scrubbed environment)
```

The Qt window and `python arc1 agent` take their build, test and run commands
from the same table in `workbench/engine.py`. Changing the screen therefore
cannot change what automation does. Agents never drive the GUI.

## Known limits of R10

- **Windows and display scaling:** Workbench has not run on Windows 11 yet
  (R14). It was tested with Qt 6.8.1 on Linux with the offscreen platform.
  Display scaling and keyboard and accessibility qualification are not done.
- **Editor:** one document per tab, with no split view, project-wide search
  or crash recovery. That is R11.
- **Agent Activity:** it does not stream agent requests yet. It says so
  rather than showing invented activity.
- **No device features:** there is no device, no debugger connection and no
  flashing. Debug › Run uses the host simulator.
