# Graphite 1.1 · Your desktop for Debian

**Graphite 1.1.1** (28 November 2026) adds the system door (software, services, the clock and accounts through
Debian's own password prompt; [notes](docs/RELEASE_NOTES_1.1.1.md)). **Graphite 1.1** makes Graphite a full desktop for Debian for a Windows-and-DOS hand. It installs as
Debian packages from a folder repository. One bar along the bottom holds Start, the line, your windows, Kas with HALT,
the tray and the clock. Files is an Explorer, the menus are File, Edit, View, Go, Tools and Help, Windows keys and DOS
words work, and a Terminal drops from the top. Kas speaks sharp and dry, and runs forty recipes and a classified command
tool on the whole box, each change shown first and done only on your press. **Start here:** [What's new in
1.1](docs/RELEASE_NOTES_1.1.md) (installing, what was and was not tested, your evening) and the kit's `START_HERE.md`.

What follows describes 1.0, on which 1.1 is built; where they differ, 1.1's notes are right.


Graphite is a desktop for one minimal Debian computer: it is the session, the whole computer is in it, and its assistant,
Kasandra (Kas for short), is an agent user of the system who works beside you under your authority. Everything stays on
that computer unless you turn a service on. Before November 6, 2026 the program was called Ledger & Slate; folders,
scripts, settings keys and internal names keep those earlier names for compatibility.

- **Graphite is the session.** A supervisor keeps it alive; your apps outlive a crash of its window; one bar along the
  bottom of the screen holds Start, the line and every open window, and brings any window forward; Lock, Suspend, Log out, Restart, Shut down and Return to Debian are plain actions that
  close apps politely.
- **The whole computer.** Files as an Explorer, from Quick access to This computer, Home open as a List (rename, move, copy, delete to the bin, many at
  once, each batch with one Undo); Apps from what is installed; the Machine for real (USB drives, sound, screens,
  network and Wi-Fi, the battery); Settings that change real settings; notifications kept in Log.
- **The Living Desktop.** The bulletin board: what you select sits in the middle with its neighbours around it, sized by
  relevance; recorded links solid, guessed ones dashed; Why am I shown?, Pin, Turn down. Double-click to work on it;
  Save and Return; tabs and a split; Back and Forward. The foot is the computer's line: Line, Terminal, Search, Web, Log.
- **The ghost in the shell.** Kas plans a task from the registered tools, asks for each permission in plain words, and
  marks a step done only when its effect is verified; a journal survives a crash or a Stop. She edits Writer and Calc
  documents through LibreOffice, works in your apps through accessibility while you watch (a touch stops her), runs a
  utility she writes only sealed on copies, reads the web only as quarantined data, and reads the pages of your
  documents in Home. HALT stops all of her work and nothing else. The model proposes; the desk disposes.
- **Her model.** llama.cpp v1.0.0, sealed; the model check measures your machine and tunes it toward 99 tokens a
  second; an optional quick model takes a kind of question only where it passed its exam.
- **The look.** Day, the launch look, and Night, its twin, from one set of design tokens with the Inter typeface;
  Graphite and Kasandra as alternatives. No picture of Kas: her name, her state and her work.

**For 1.0:** [Your first evening with 1.0](docs/ACCEPTANCE_1.0.md) (the install, your paper's §2 test, the model, the
§18 day, what to send back), [the ThinkPad page](docs/THINKPAD_FIRST_INSTALL.md), and
[What's new in 1.0](docs/RELEASE_NOTES_1.0.md). In Graphite: Help ▸ The Living Desktop, and Help ▸ Kasandra, the Ghost
in the Shell.

**Not tested.** By the owner's rule ("No testing") nothing in 1.0 has been through the test suite, the tiers or the
window checks, and nothing of it has run on the ThinkPad. It was built in a cloud machine without a screen, USB, sound,
Wi-Fi, suspend or Radeon, and seen working there offscreen and against stand-ins, with twenty-four walkthroughs and the
paper's §18 day walked in the window (the day with a real 4B model). The 35B has never been loaded anywhere.

## Install

From the release volumes (`Graphite_1.0_part_NN.zip`, `RELEASE_PARTS.json` and `INSTALL_LS.py` in one folder, for
example a USB stick), as your ordinary Debian user:

```
python3 INSTALL_LS.py --usb . --target "$HOME/Applications/Graphite-1.0" --minimal-session --vulkan --plan
python3 INSTALL_LS.py --usb . --target "$HOME/Applications/Graphite-1.0" --minimal-session --vulkan --yes
```

`INSTALL_LS.py` is the Graphite installer (its file name is kept: scripts, tests and earlier notes call it). It verifies
every volume, restores the program into a new folder, installs the Debian prerequisites (with `--yes`, through sudo) and
the pinned Python dependencies, checks the runtime imports, the payload and the seed, and ends with one line that says
what actually happened. `--extract-only` verifies and restores without installing anything; `--offline` uses a prepared
cache only; `--public-manifest URL --manifest-sha256 HASH` installs from a published release. Every option and refusal is
explained in [docs/MINIMAL_DEBIAN_INSTALL_01.md](docs/MINIMAL_DEBIAN_INSTALL_01.md).

From an already extracted program folder:

```
bash INSTALL_DEBIAN.sh --quick            # asks before sudo; add --vulkan for Radeon dependencies, --minimal-session for the dedicated session, or other tool options as needed
bash INSTALL_LEDGER.sh --quick            # the runtime only, on a system that already has the prerequisites
```

Keep your previous program folder and every workspace; install a new release into a new folder. A local model is
optional: the daily guide says which small GGUF file to fetch and how to register it in the Brain room. No model file is
included.

## Start

```
bash START_MINIMAL_DEBIAN.sh   # from a Debian text login: the dedicated fullscreen session; prints "Graphite ended with status N" when you leave
bash START_OFFICE.sh           # from an existing desktop: the ordinary window on the Office workspace (~/Concern/Office)
```

Leave through the File menu's last group (or the foot of Start) → Return to Debian, or Exit Graphite on an
existing desktop. The same group's Log out, Restart and Shut down first save or set aside your work as leaving does, ask you
to confirm, and then ask the system's own logind (never sudo); without a login session they say they are unavailable. On Windows, `START_OFFICE.cmd` starts the same program after Python
and `requirements-qt.txt` are installed.

## Operator tools

```
bash LEDGER.sh doctor                 # inspects the installation; creates no workspace, starts nothing
bash LEDGER.sh doctor --self-test     # a disposable capture, restart, backup and restore round trip
bash LEDGER.sh doctor --qt-check      # the real window and capture widget, offscreen
bash LEDGER.sh baseline --out my-baseline.json
bash LEDGER.sh inventory
```

## Complete backups

Close Graphite before taking a backup. This includes ordinary workspace files and working copies; restore always writes
NEW folders and leaves existing work untouched:

```
bash LEDGER.sh backup create --root ~/Concern/Office --out ~/Graphite-backups/office
bash LEDGER.sh backup verify ~/Graphite-backups/office
bash LEDGER.sh backup restore ~/Graphite-backups/office --to ~/Concern/Office-restored
bash LEDGER.sh open --root ~/Concern/Office-restored --profile ~/Concern/Office-restored-profile
```

External originals and external model weights are not included; model files inside the workspace are left out unless
`--include-models` is given. Complete snapshots and no-replace publication target Linux. docs/STAGE1.md explains backup and
restore in full.

## Checks

```
python3 tools/check_release.py               # payload, seed and syntax; the live program against docs/GRAPHITE_0.1_REGISTRY.json; the privacy scan
python3 tools/check_release.py --self-test   # adds the focused tests_integrated modules, one module per child process
python3 tools/check_release.py --ui          # adds the offscreen Qt checks of the UI gate (docs/WINDOW_CHECKS.md lists them)
python3 tools/run_tiers.py 0                 # the checks in tiers: 0 at every change, 1 before a commit, 2 at a release (docs/CHECKS.md)
python3 -m workbench.slate_checks --runtime
python3 -m workbench.continuing_checks --workers
python3 -m workbench.deployment_checks --ui
```

`tools/check_release.py` is the one entry for the release check (it runs `tools/check_hatch.py`). The registry record
`docs/GRAPHITE_0.1_REGISTRY.json` holds every operation's scope and argument-schema digest, the job tools, every setting
definition's digest and the adapters; `tools/record_registry.py` writes it from the live tree, and any difference is listed
in words. It submits no job, starts no model or worker, makes no provider request and invokes no native tool. A passing
check is integrity, not readiness or acceptance. Tests run one module at a time:
`python3 -B -m unittest tests_integrated.test_graphite` (tests_integrated has no `__init__.py`; do not use discover).

## Paired exchange, signed releases and deployment

Go ▸ Exchange & deployment holds recipient-bound request and result pills, pinned mutual TLS 1.3, replay protection,
explicit signed offline release verification and recovery, reviewable launch files and optional read-only phone progress.
A received pill stays in quarantine until explicitly accepted; returned edits become a frozen working-copy proposal, and
originals still need separate owner publication. Nothing starts merely by opening the panel. Read docs/STAGE6.md before
pairing or updating. No publisher private key or default trust root is included.

## Packaging

```
python3 tools/package_graphite.py --dry-run                                     # what would be shipped; writes nothing
python3 tools/package_graphite.py OUT
python3 tools/package_release_parts.py OUT/Graphite_1.0_full.zip PARTS "Graphite 1.0"
```

Graphite's own code and documents are free software under the GNU General Public License, version 2 only (COPYING).
Stacy's artwork, the other project art, the names and the game copy are kept back (RIGHTS.md). Licences of bundled fonts,
runtimes and dependencies are in THIRD_PARTY_NOTICES.md; the pinned dependencies are the requirements-*.txt files.
