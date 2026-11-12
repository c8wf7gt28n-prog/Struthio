# Stage One baseline

This is Ledger & Slate 5.0.0a1, the first implementation stage of the approved upgrade. It adds operator diagnostics, a reproducible baseline, a complete workspace backup, and a smaller default Debian installation. It preserves the 4.9 interface and registered operation schemas.

## Start on Debian

Extract the whole package into a new folder. Keep your previous program and workspace. As your ordinary desktop user, run:

```
bash INSTALL_DEBIAN.sh
bash START_OFFICE.sh
```

The Debian helper asks before installing system prerequisites through sudo. Compilers, Git, Node, Icarus and clangd are added only with `--engineering`. Python 3.11-3.13 is supported. The Python installer uses a local `.venv`; it does not download model weights or migrate workspaces.

If prerequisites are already installed, use `bash INSTALL_LEDGER.sh`. Offline mode is `bash INSTALL_LEDGER.sh --offline /path/to/wheels`. The wheel folder must contain every pinned dependency for this Python and platform; the package does not include that wheel bundle. Offline mode uses no-index installation and never falls back to a download. `INSTALL_DEBIAN.sh --offline` also skips apt.

## Doctor and measurements

```
bash LEDGER.sh doctor
bash LEDGER.sh doctor --self-test
bash LEDGER.sh doctor --qt-check
bash LEDGER.sh baseline --out baseline-report.json
bash LEDGER.sh inventory
```

`python3 -m workbench.launch --doctor` also works before Qt is installed. Normal inspection does not create a workspace or start a model or service. The report records package integrity, source bindings, registry agreement, database quick checks where databases already exist, dependency versions, CPU/RAM measurements, free space, and reported confinement availability. Confinement availability is not a successful containment test.

The disposable baseline saves the same catalog-note form used by Jot it down, opens a fresh process, runs staC over a saved file, backs up the workspace/profile, restores into new folders, and opens another fresh process. It requires no model and touches no existing workspace or profile.

The optional Qt check opens the real window and exercises the real capture widget offscreen, using disposable storage. It requires installed PySide6 and platform libraries. It does not replace a walkthrough on your actual display. Doctor exit code 0 means its requested checks passed and dependencies match; 2 means attention or a requested check is incomplete; 1 means a command/report error.

## Complete workspace backups

Close Ledger windows and stop its coordinator before taking a backup. Close other Ledger sessions sharing the same profile. SQLite databases are backed up consistently through SQLite's API; the several databases and ordinary files are not one global atomic snapshot.

```
bash LEDGER.sh backup create --root ~/Concern/Office --out ~/Ledger-backups/office-stage-one
bash LEDGER.sh backup verify ~/Ledger-backups/office-stage-one
bash LEDGER.sh backup restore ~/Ledger-backups/office-stage-one --to ~/Concern/Office-restored
```

The complete format includes the workspace marker, ordinary files, Arrived, working copies, private state, and the selected profile. It retains empty folders. Rebuildable caches, coordinator/model scratch, and model weights are omitted as declared in BACKUP.json. Add `--include-models` to include managed or workspace GGUF weights. External master files and externally registered model files remain outside this backup.

Restore requires NEW workspace and profile destinations. The default restored profile is beside the new workspace with `-profile` appended. Existing work is never selected for replacement. All members and database integrity are verified before publication. New directory publication uses Linux's no-replace rename; an unsupported filesystem/host is refused. Keep backups private: a profile backup can contain your account settings and credentials.

To open the restored pair, use the paths printed by restore:

```
bash LEDGER.sh open --root ~/Concern/Office-restored --profile ~/Concern/Office-restored-profile
```

The older `python3 -m workbench.state_backup` still operates on private state only. Its backup format is distinct. Do not confuse a private-state backup with a complete workspace backup.

## What was preserved

No SDK, policy or pinned-runtime payload is changed. The 485 registered operation schemas are compared with the original baseline. The legacy full-project release checker is retained; the normal checker now selects the checks actually shipped in the runtime edition. The original README, starter guide, and omitted-file list are retained under docs with 4_9 in their names.

The 41 historical notes carried by the seed remain byte-identical. Explicit authoring rebuilds the source foundation from those verified notes and the new source. The notes are materialized only in a temporary assembly tree. Startup never silently rebuilds or relaxes source bindings.

## Checks shipped with this package

```
python3 tools/check_release.py --self-test
python3 -m unittest discover -s tests_stage_one -v
```

The checks cover complete recovery, corrupted backups, active-coordinator refusal, unsafe names and links, destination collisions, read-only diagnostics, and unchanged protected payload/schema identities. This is a focused Stage One suite; it is not the omitted historical full-project regression suite.

## Stage status

The candidate's measured results are in STAGE1_RESULT.json. That report identifies the execution host and does not claim to be a ThinkPad measurement. The package and service-level baseline can be qualified here. Real Qt startup, the owner-display walkthrough, native model inference, and physical hardware must be reported separately when actually performed.

Owner walkthrough: open Today, keep an idea in Notes, close Ledger, reopen and find it, close Ledger again, make and verify a complete backup, restore into new folders, then open the restored workspace/profile pair. Use the doctor report to retain the host measurements and record which steps actually passed.
