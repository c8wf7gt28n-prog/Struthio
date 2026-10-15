# ARC1_R85_ENGINEERING_SOURCE – start here

1. `R85_WORK/STATUS_R85.md`: outcome (HOLD/PARTIAL, **HARD STOP raised for owner decision**), gates G1–G10, commands.
2. `R85_WORK/RISK_REGISTER_R85.md`: unresolved-risk ledger.
3. Reproduce: unpack next to the repository's `hardware/arc1-compact/` (R05_BASELINE, R06_WORK, R07_WORK, R08_WORK are
   included unchanged under `FROZEN_INPUTS/`), then `python3 R85_WORK/tools/run_r85_checks.py`.
4. `MANIFEST_SHA256.txt` lists every file in this archive.

Nothing in this archive has been tested on hardware. It does not approve fabrication and does not start R09 routing.
