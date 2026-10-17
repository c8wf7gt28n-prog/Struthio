# R10.2 — Windows installer second pass, and Clip

- **Clip:** a paperclip helper in the empty right-hand end of the toolbar
  (`ClipAssistant` in `workbench/qt_app.py`). It will become the go-between
  for you and the AI coder. For now it isn't connected to any agent and
  says so when clicked.
- **Windows installer fixes** (from a review; not yet run on Windows):
  - **Microsoft Store Python is refused.** It redirects files written in
    AppData to a private folder, so the shortcuts would point at nothing.
    `INSTALL_ARC1.cmd` skips it when looking for Python.
  - **Python 3.11–3.13 is preferred,** since PySide6 6.8.1 has no wheels for
    3.14. When Qt can't install, the message gives the actual reason:
    Python too new, paths too long, or no connection.
  - **Workbench left open:** upgrade and uninstall stop with "close
    Workbench" and change nothing, instead of crashing halfway through.
  - **Uninstaller:** `Uninstall ARC-1 Workbench.cmd` deletes itself while it
    runs. It now runs its last steps from one line, so it no longer ends
    with "batch file cannot be found".
  - **Backups follow OneDrive:** they go to the real Documents folder,
    even when OneDrive has moved it.
  - **Taskbar:** Workbench gets its own taskbar button and icon instead of
    Python's. The Tk fallback also asks Windows for sharp text on scaled
    displays.
  - **SmartScreen:** the installer explains the "Windows protected your PC"
    prompt, which appears because the file isn't signed.
  - Unexpected file errors now print a plain message, not a traceback.
- **Not tested:** tests were not run for this change, and no pass record was
  written.

# R10.1 — Installer and resource budgets

- **One-double-click installer:** `INSTALL_ARC1.cmd` replaces R09's
  drag-to-My-Apps installer (`workbench/installer.py`, removed). It finds or
  installs Python, then copies Workbench into place and installs Qt
  privately. It finds or installs a C compiler, creates shortcuts with a new
  ARC-1 icon and an Installed apps entry, runs `arc1 doctor`, and offers to
  start Workbench.
  - **Your work is safe:** upgrades and uninstalls back up any file you
    changed or added.
  - **Code:** `workbench/setup_arc1.py` (standard library only) and
    `workbench/launch.py`. The launcher opens the Qt window, falls back to
    Tk, and reports start-up errors.
  - **Line endings:** batch files are now stored with CRLF line endings
    (`.gitattributes`).
- **Resource budgets in the Hardware Inspector** (View › Resource Budgets),
  from the owner's frame-budget sketch:
  - Charts: frame time against 16.67 ms, link bandwidth against the 60 fps
    need, and memory pools.
  - Every figure quotes its R10 source. Missing quotes drop the number;
    unknowns are hatched "not measured".
  - Code: `workbench/resources.py`, `hardware/budgets/r10_resources.json`.
  - Agents get the same data with `inspect.resources`.
- **Not run on Windows:** the installer's Windows layer was checked with
  stand-ins. On Linux, a real install, launch and uninstall cycle passed:
  Qt downloaded, `ARC1_LAUNCH_OK qt`, uninstall removed everything.

# R10 — Familiar main screen (Qt "Classic")

Owner decision: Workbench should behave like File Manager and Word, with the
console-engineering tools appearing when the task needs them. See
[docs/WORKBENCH_R10.md](docs/WORKBENCH_R10.md).

## Changed

- **New main window** (`workbench/qt_app.py`, rewritten):
  - Layout: native Windows title bar, menu bar, one compact toolbar (Open,
    Save, Build ▾, Run, Tests, Target), a ~236 px logical project navigator,
    document tabs and a status bar.
  - Hidden until needed: Output/Problems (F10), the Hardware Inspector and the
    Cartridge Shelf.
  - Start page, Browse tab (File Manager listing, optional dual pane) and
    Preview tab for simulator frames.
- **Light Classic theme** (`workbench/qt_theme.py`): ivory and grey surfaces,
  restrained orange accents, subtle toolbar and button depth. It replaces
  R08/R09's dark graphite.
- **Editor:** line numbers, current-line band and problem-line marker. Undo,
  Redo, Cut, Copy, Paste, Find, Find Next, Replace (a single undo step) and
  Go to Line.
- **Build, Tests and Run follow the work in front of you:**
  - A file in a game project builds and tests that game.
  - Otherwise the selected Target is used.
  - Run (F5) builds the game and then runs the host simulator.
- **Compiler errors are navigable:**
  - The Problems list has severity, description, file and line.
  - Double-click or press F8 / Shift+F8 to jump to the line.
  - Game builds read the compiler log the CLI writes; firmware builds read
    the CLI failure text.
- **Session memory** (`workbench/session.py`): project, documents, cursor
  positions, active tab, target, recent files, output panel, panel sizes and
  window layout. **View › Reset Window Layout** restores the factory layout.
- **File operations** (`workbench/fileops.py`): New File, New Folder, Rename,
  Duplicate and Delete.
  - Windows naming rules, case-insensitive clash checks and no overwrites.
  - Recorded evidence is read-only.
- **Shared engine** (`workbench/engine.py`): the Qt window and the agent
  interface (`workbench/agent.py`) now use one command table, so the agent
  no longer keeps its own copy.

## Fixed (found by the R10 acceptance test)

- **Firmware errors were cut off.** `arc1 firmware build` and `arc1 firmware
  test` kept only the last 1,200–1,500 characters of compiler output, so the
  first error, usually the one you caused, was lost. The build then pointed
  at a knock-on error in another file.
- They now keep the beginning of the log, and the end too when it is long
  (`sdk/cli/arc1cli/firmware.py`, `compiler_excerpt`).

## Kept

The R09 backend, launcher, cartridge system, firmware tests, boot-diagnostic
model, agent protocol and the Tk desktop (`START_ARC1.cmd`) are unchanged.
The R09 Tk smoke test passes under Xvfb.

## Verified (see R10_VERIFICATION.json)

- **Qt acceptance workflow:** run with the offscreen platform, PySide6 6.8.1
  on Linux (`tests/test_r10_workbench.py`, 20 tests):
  - find a file, open it, edit it, save it
  - build the relevant target and read the compiler error
  - go back to the source line, fix it, rebuild clean, run the simulator
  - reopen to check what was remembered, and reset the layout
- **Earlier tests:** the SDK suite and the R08/R09 regression tests pass.

## Not done

- **Windows 11:** native run, installation, display scaling, and keyboard and
  accessibility qualification (R14).
- **Editing:** split editing, project-wide search and crash recovery (R11).
- **Workspaces:** per-activity saved workspaces (R12).
- **Agent Activity:** live streaming of agent requests.
- **Hardware:** everything that needs a board.
