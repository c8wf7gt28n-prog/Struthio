# ARC1-PASS-0004 handoff — DOS-style debug console and plan-only flasher

- **State:** REVIEW. Waiting for an independent reviewer (COV-003).
- **Owner:** agent:claude-code
- **Base commit:** `e9166a99c131d456921dc4dda1eb6987d1e9ab7a` (ARC1-PASS-0003)
- **Risk tier:** MEDIUM. It adds the first board-facing commands, and none of
  them write to hardware.

## Reproduce

In `arc1/`:

```sh
./arc1 build examples/hello_arc1
./arc1 ui                                    # interactive; Q quits
./arc1 ui --snapshot hardware                # same screen as plain text
./arc1 device flash --partition F1MA --image passes/ARC1-PASS-0004/reports/plan-image-fw.bin; echo "exit $?"
./arc1 device flash --partition F1BT --image passes/ARC1-PASS-0004/reports/plan-image-fw.bin; echo "exit $?"
./arc1 device detect; echo "exit $?"
python3 tests/run_tests.py
```

Expected results:

- The F1MA plan prints NOT_AVAILABLE with "write disabled" and exits 3.
- F1BT prints FAIL SEC-004 (a locked partition) and exits 1.
- `device detect` prints NOT_AVAILABLE and exits 3 when `xfel` is not
  installed.
- The suite runs 56 tests and reports OK. The pseudo-terminal test is
  skipped on Windows.

The interactive check uses a non-SDK tool, which needs pyte:

```sh
pip install pyte==0.8.2
python3 passes/ARC1-PASS-0004/tools/drive_terminal.py passes/ARC1-PASS-0004/reports/plan-image-fw.bin
```

It presses 19 keys through a pseudo-terminal and checks each resulting
screen. Expect every line to say `ok` and the run to end with `exit: 0`.

## What was delivered

- **Main change:** `arc1 ui` (`sdk/cli/arc1cli/ui.py`), an 80×25 DOS-style
  curses console:
  - Menu items: system check, hardware facts, build, simulator, tests, frame
    viewer, pass records, console detection, flasher and about.
  - Screen: title bar with the R10 HOLD badge, double-line boxes with
    shadows, a session box and a key bar.
  - Frame viewer: half-block pixels mapped to the 16 DOS colours, with
    `[`/`]` to step 10 frames.
  - Every item runs the same `main.execute()` path as the command line.
  - Rendering goes through a cell buffer, so `--snapshot` and the tests need
    no terminal.
  - Also: README screenshot (`docs/assets/arc1-ui.png`), README, AGENTS.md,
    CLI and TRACEABILITY docs.
- **SDK change (covenant):** `sdk/cli/arc1cli/device.py`, which adds two
  commands:
  - `arc1 device flash` builds a NOR write plan from the vendored R10
    partition map: fit, SHA-256, locked-partition refusal, risks, rollback
    state, the three open gates and the exact `xfel` commands. It always
    ends NOT_AVAILABLE or FAIL. No code path writes.
  - `arc1 device detect` runs only the read-only `xfel version`.
  - The `xfel` syntax and the F133 chip ID come from two R08 files, now
    vendored and cited (`hardware/sources/r10/PROVENANCE.md`).
  - Beneficiary: any future bring-up, which can check a write plan for fit,
    digest and gates before a board exists.
- **Effort:** 50 planned task units, 12 reserved for the SDK change.
  Actual effort was not measured.
- **Deviation from COV-001, again:** no PLANNED record was committed first.

## Bugs found and fixed during this pass

These came from driving the real curses UI through a pseudo-terminal:

- **Image prompt:** `getstr` truncated typed paths to the visible field
  (about 65 characters), and the leftover keys went to the flasher as
  commands. Replaced with a horizontally scrolling line editor that accepts
  up to 1024 characters.
- **vt100:** the UI crashed (exit 4) because `curs_set` is unsupported there.
  It now tolerates that.
- **Escape quit the app** from the main menu. A terminal without a key such
  as PgDn delivers a stray Escape, so the app quit unexpectedly. Now only Q
  and F10 quit; Escape backs out of sub-screens.
- **C locale:** in a plain `C` locale the UI emitted UTF-8 box characters,
  because Python's UTF-8 mode reported UTF-8. Detection now asks the C
  library (`nl_langinfo`), and anything non-ASCII is replaced in ASCII mode.

## Checks run

| Check | Level | Result |
|---|---|---|
| Device and UI tests (13) | HOST_SIM | PASS |
| Full suite (56) | HOST_SIM | PASS |
| Plan for F1MA | NONE | NOT_AVAILABLE (expected, `reports/flash-plan-F1MA.json`) |
| Plan for F1BT (locked) | NONE | FAIL (expected, artifact) |
| `device detect` without xfel | NONE | NOT_AVAILABLE (expected) |
| Interactive drive: xterm-256color, xterm (8 colours), screen with C locale | HOST_SIM | 19/19 screens each |
| Interactive drive: vt100 | HOST_SIM | 17/19 (see below) |

The screens were checked with the pyte 0.8.2 terminal emulator. On vt100 the
two PgDn steps miss because vt100 terminals have no PgDn key; the UI did not
crash or quit. The pyte runs use `TERM=screen` for the C locale, because pyte
does not implement the `rep` sequence that xterm terminfo enables.

## Not run / not available

- **Any write to a console.** Disabled until three gates close: an identified
  board, bench-proven FEL recovery (R10 change order CO-4) and recorded owner
  approval.
- **`xfel` against a real device:** none exists. Detection was tested only
  with a fake `xfel` script.
- **Real terminals:** Windows (needs `windows-curses` or WSL), macOS
  Terminal and real hardware terminals were not tested. Only emulated
  pseudo-terminals were.
- **TST-004** independent reproduction.

## Known limitations

- The frame viewer maps the ARC-1 palette onto 16 DOS colours, so colours
  are approximate. The PPM files from `arc1 sim` hold the exact frames.
- The `xfel` command sequence in a plan was written for R08 (32 MiB NOR). It
  is marked UNVERIFIED on the R10 64 MiB NOR.
- The UI needs at least 80×25 and asks for a bigger window otherwise.
