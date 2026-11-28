# KS3 progress (builder notes)

## Done
- workbench/system_bus.py: a stdlib D-Bus client (wire protocol, AUTH EXTERNAL, typed signatures, signals, a service side for fakes). Probed against a real dbus-daemon: calls, uint64, arrays, structs, errors, signals all good (probe in b110/KS3/probe).

## Decisions so far
- Transport: own D-Bus client (PySide6 QtDBus cannot send uint64; PackageKit answers by signals so busctl/dbus-send cannot). No shell, no helper of ours, no pkexec.
- Agent: lxpolkit, already a Depends of graphite-session and started by LS_XSESSION.sh since 1.0 S5: nothing new there.
- New packages: packagekit, accountsservice -> graphite-session Recommends (build_repo.sh downloads Recommends).
- 1.0 has NO services/time/users pages in Settings > This computer (the note's premise): KS3 adds one page "System changes".
- Scopes: door.plan/door.read/door.runs/door.state read; door.run/door.undo approve; refuse in her work (hr.in_her_work covers grants' _PERMIT) and under HALT.

## Next
- workbench/system_door.py (actions, validate, plan, run, verify, undo, words, offer(argv), Kernel ops, records door_runs)
- workbench/system_door_qt.py (her talk, NEXT STEPS, line rows, Settings page)
- hooks: engineering_kernel/cli, shell2 ask chain, her_column NEXT STEPS, line_finder, system_settings_qt, kas_voice, debian/control
- tests_integrated/test_system_door.py with fake services on a private dbus-daemon; frames (8: 1920x1200 day+kasandra)
