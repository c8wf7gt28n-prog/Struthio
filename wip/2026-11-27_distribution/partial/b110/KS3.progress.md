# KS3 progress (builder notes): goes into 1.1.1

## Status: DONE (result file written: KS3.build.result.json)
- system_bus.py, system_door.py, system_door_qt.py, test_system_door.py (13 tests, OK); hooks marked 1.1 KS3 in engineering_kernel/cli, shell2, her_column_qt, line_finder, system_settings_qt, kas_voice; debian/control: graphite-session Recommends packagekit, accountsservice.
- Kernel ops: system.door.plan/run/undo/runs/read/state.
- Final run: test_system_door + test_kas_voice, 25 OK. Touched tests earlier: 63 OK.
- Patch apply-checked on a clean archive of f162d8c: APPLIES.
- Frames: b110/KS3/frames/ (18 PNGs; 1920x1200 Day looked at).
- Copy, areas and probe deleted.
