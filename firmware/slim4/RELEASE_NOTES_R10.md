# R10 — self-contained pin check, PCB R26

The R30/R25 pre-order audit found that the firmware folder could not check itself: `tools/check_pinmap.py` read U1's pad nets from the board export in `hardware/slim4/`, which the firmware zip does not carry.

- `tools/u1_pad_nets.json` (new) holds U1's pad → net table, taken from `SLIM4_R26_PCB_LAYER.json`. `tools/check_pinmap.py` reads it by default, so the check runs from the firmware folder alone; inside the repository it also compares the table with the board export and fails if they differ. `--board <export.json>` checks against another export; `--write-table <export.json>` refreshes the table.
- PCB R26 reroutes the DSI pairs and moves no GPIO: 19 of 19 firmware pins match (also on R25's export).
- No firmware source changed: version 0.9.0, and the prebuilt images are R9's (same SHA-256). Not yet run on hardware.
