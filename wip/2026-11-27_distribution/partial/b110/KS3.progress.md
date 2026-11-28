# KS3 progress (builder notes) — goes into 1.1.1 (coordinator, after the 1.1 release)

## Done (in the patch KS3.patch)
- workbench/system_bus.py: stdlib D-Bus client (wire protocol, AUTH EXTERNAL, typed signatures, signals, service side for fakes). Probed OK against a real dbus-daemon.
- workbench/system_door.py: 15 fixed actions (package install/remove/update, refresh; service start/stop/restart/enable/disable; time zone, NTP, set clock; host name; user add, real name), validate, plan (PackageKit SIMULATE + GetDetails), run (digest, her work/grant/HALT gate, interactive flag), verify, undo (inverse fixed action), records door_runs, read/state, read_words (her words), offer(argv) for KS2.
- Kernel ops RENAMED to system.door.plan/run/undo/runs/read/state ('door.state' etc. are the hand door's: hand_door.py). NEXT STEPS kind 'system_door'.
- workbench/system_door_qt.py: her talk, NEXT STEPS, line rows, Settings page "System changes".
- hooks (1.1 KS3): engineering_kernel/cli, shell2 ask chain (before recipes), her_column NEXT STEPS + take_step, line_finder door_rows, system_settings_qt (row + open_page), kas_voice door_* words, debian/control (graphite-session Recommends packagekit, accountsservice).
- tests_integrated/test_system_door.py (13 tests, fake services on a private dbus-daemon). Run 1: 12/13 OK; the page failure was the op-name clash (fixed by the rename; not yet re-run).

## Next
- sync copy (b110/KS3/sync.sh), seed (seed.sh), test (test.sh tests_integrated.test_system_door door2); also run touched tests: test_kas_voice, test_start_line (line_finder), maybe test_recipes.
- frames (8: 1920x1200 day+kasandra: offered, before prompt, done, service restarted) via a frames script like KS1's (b110/KS1/xinner.sh, frames.py) with the fake system on DBUS_SYSTEM_BUS_ADDRESS.
- result JSON; apply-check on a clean archive of f162d8c; delete copy.
- Result must say: system_door.offer replaces KS2's command_forms.py root refusal text later (do not edit command_forms.py).
