# ARC1-PASS-0006 handoff — Workbench R10.1: installer and resource budgets

- **State:** REVIEW. Waiting for an independent reviewer and a first run on
  Windows 11.
- **Owner:** agent:claude-code
- **Base commit:** `1f2d1a0` (ARC1-PASS-0005, Workbench R10). The full SHA is
  in pass.json.

## Reproduce

In `arc1/`:

```sh
python3 tests/test_r10_installer.py                                  # 14 tests: real Linux installs + Windows layer via fakes
QT_QPA_PLATFORM=offscreen python3 tests/test_r10_workbench.py         # 24 tests (PySide6 needed for 6 of them)
python3 workbench/setup_arc1.py install --target /tmp/arc1-try --yes --no-launch   # a real install (downloads Qt)
sh "/tmp/arc1-try/Uninstall ARC-1 Workbench.sh"                         # answer y
./arc1 pass validate passes/ARC1-PASS-0006
```

On Windows: extract the ZIP and double-click `INSTALL_ARC1.cmd`.

## What was delivered

- **Main change:** the installer.
  - `INSTALL_ARC1.cmd` is a CRLF bootstrap. It finds Python 3.11+ or offers
    a per-user winget install, and refuses to run from inside the ZIP.
  - `workbench/setup_arc1.py` runs a six-step guided install:
    1. copy the app, swapped in atomically
    2. create a private venv
    3. install PySide6-Essentials 6.8.1 (or from a bundled `wheels/` folder)
    4. find a compiler, or offer winget LLVM
    5. create shortcuts, the uninstaller and the Apps & Features entry
    6. run `arc1 doctor`
  - Upgrades and uninstalls back up user-changed files to
    `Documents\ARC-1 Workbench backups`.
  - `workbench/launch.py` is what the shortcuts run. It opens the Qt window,
    falls back to Tk, and adds compiler folders found off PATH.
  - New icon: `workbench/arc1.ico` / `arc1_icon.png`, made from the official
    logo.
  - R09's Tk drag installer was removed.
- **SDK change (covenant):**
  - `workbench/resources.py` and `hardware/budgets/r10_resources.json`
    provide cited frame-time, link-bandwidth and memory budgets.
  - A figure whose quote is not in its source is dropped. Unknowns stay
    `null` and are drawn as "not measured".
  - The data is shared by the Qt Inspector (View › Resource Budgets) and
    the agent (`inspect.resources`).

## Checks run

| Check | Result |
|---|---|
| Installer tests (fresh, upgrade, backup of edits, failed copy, refusals, uninstall, Windows layer via fakes) | 14 passed |
| Real Linux cycle: install with Qt download, launch through the shortcut command, uninstall | passed (`reports/linux-install-launch-uninstall.log`) |
| R10 Workbench tests incl. the Resources view | 24 passed |
| R05–R09 regression, SDK suite | passed |

## Not run

- **`INSTALL_ARC1.cmd` on Windows:** never run. The batch syntax was
  reviewed, not executed.
- **Windows-only steps:** winget, the PowerShell shortcut creation,
  `winreg` writes and `Uninstall ARC-1 Workbench.cmd` were exercised only
  through fakes.
- **Behind a proxy or offline:** pip install of PySide6 was not tried there.
  The bundled-wheels option exists for offline installs.
- **TST-004:** independent reproduction not done.

## Known limits

- Workbench edits files inside its install folder (as R09 did). Upgrades
  protect them with a backup, but git or a separate project folder is
  still the better home for real work.
- The Resources charts show figures side by side, not a schedule. How the
  stages overlap on a real console is unknown.

## Suggested next step

- **A person runs the installer on Windows 11.** Double-click
  `INSTALL_ARC1.cmd`, check the shortcuts, the Installed apps entry and the
  uninstall, and send `launch-error.log` if anything fails.
- **Then R11:** professional editing.
