# ARC1-PASS-0005 handoff — Workbench R10, Classic main screen

- **State:** REVIEW. Waiting for an independent reviewer (COV-003), and for the
  owner to try it on Windows.
- **Owner:** agent:claude-code
- **Base commit:** `8e26c4013616a558f69d2f2ca55c5b31684d53e5`. That commit
  imported Workbench R09 verbatim from the owner's archive (SHA-256
  `86bafd00…81ff`).
- **Risk tier:** MEDIUM. It replaces the Qt main window, changes the theme and
  touches the firmware CLI's error reporting.

## Reproduce

In `arc1/`, with PySide6 installed (`python3 -m pip install PySide6-Essentials==6.8.1`):

```sh
QT_QPA_PLATFORM=offscreen python3 tests/test_r10_workbench.py   # 20 tests; prints the acceptance timing
python3 tests/test_r10_workbench.py                             # without PySide6: 5 Qt tests skip, reported as NOT run
python3 tests/run_tests.py
./arc1 pass validate passes/ARC1-PASS-0005
python -m workbench.qt_app                                       # the real window (Windows: START_ARC1_QT.cmd)
```

Linux needs `libegl1 libxkbcommon0 libfontconfig1` for Qt. To repeat the R09
Tk smoke test, you need Python with tkinter, Pillow, Xvfb and a writable
`/mnt/data` (the R09 test hard-codes that path).

## What was delivered

- **Main change: the R10 Classic main window.**
  - **Default screen:** menu bar (File, Edit, View, Project, Build, Debug,
    Cartridge, Tools, Help), one toolbar (Open, Save, Build ▾, Run, Tests,
    Target), a 236 px logical project navigator, document tabs with line
    numbers, an info strip and a status bar.
  - **Truthful badge and status:** HOST SIM · BOARD OFFLINE, and "No physical
    device connected".
  - **Hidden until needed:** the output panel (F10), the Hardware Inspector
    and the Cartridge Shelf.
  - **Tabs for each activity:** Start (no documents), Browse (File Manager
    listing, optional dual pane) and Preview (simulator frames).
  - **Light ivory/orange theme.**
  - **Session memory and View › Reset Window Layout.**
  - **File operations** with Windows naming rules; evidence is read-only.
  - **Docs:** `docs/WORKBENCH_R10.md`, `PATCH_NOTES_R10.md`, README, AGENTS
    and `R10_VERIFICATION.json`; CI now runs the Workbench tests with a real
    Qt window.
- **SDK change (covenant):**
  - `workbench/engine.py`: one command table and planner shared by the Qt
    window and the agent interface. It covers the relevant target, problem
    path resolution and truthful device status.
  - `sdk/cli/arc1cli/firmware.py` `compiler_excerpt`: firmware build and test
    failures now keep the **first** compiler error. Before, they kept only
    the last 1,200–1,500 characters, so the error you caused was dropped and
    Workbench pointed at a knock-on error.
  - Beneficiary: every front end, and every person or agent reading a
    firmware build failure.
- **Effort:** 80 planned task units, 14 for the SDK change. Actual effort was
  not measured. As in earlier passes, this record was written at the end and
  not committed as PLANNED first.

## Checks run

| Check | Result |
|---|---|
| `tests/test_r10_workbench.py` with Qt 6.8.1 offscreen | 20 passed. Acceptance workflow in 2.0 s machine time |
| Same, without PySide6 | 15 passed, 5 skipped and labelled NOT run |
| R05–R09 regression (boot, cartridge, launcher, Qt contract, output) | passed |
| R09 Tk smoke test under Xvfb (Python 3.12) | passed: the fallback desktop still works |
| SDK suite (`tests/run_tests.py`) | passed |

## Sensitive changes (disclosed in pass.json)

- `tests/test_r08_qt_contract.py`: its theme assertions pinned R08's dark
  graphite colours and "no gradients". The owner's R10 decision replaces
  that look, so the assertions now check the R10 palette. The other three
  tests in that file are unchanged.
- `AGENTS.md`: adds the R10 rules.

## Not run / open

- **Windows 11:** no native run. Display scaling (125–200 %), installer,
  keyboard-only and screen-reader checks were not done (R14).
- **Human timing:** nobody has timed the acceptance workflow. The 2.0 s is a
  script.
- **The real title bar:** the offscreen screenshots show only the client
  area. Windows draws the title bar.
- **Agent Activity:** it does not stream agent requests yet. It says so.
- **Board:** no board exists; fabrication is on HOLD.

## Suggested next pass (R11, professional editing)

- Split editing, project-wide search and replace, and crash recovery for
  unsaved buffers.
- Syntax colouring.
- Then measure the acceptance workflow with a person on Windows.
