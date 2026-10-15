# Documents inherited from R08 (moved here unchanged, except one path in f133_diag/Makefile)

These R08 documents remain valid for everything except the FPGA subsystem: NOR boot, recovery, BT820/MN820, USB,
audio, panel deferral, manufacturing notes, vendor questions. Where they mention the T35, its rails (1V2_T35/3V3_T35),
CRESET/CDONE, the U19 configuration flash, U26 or the Efinity flow, they are **superseded** by the R8.5 documents:

| R08 topic | Superseded by |
|---|---|
| T35 rails, sequencing (POWER_TREE_AND_RESET.md §T35) | ../ECP5_POWER_R85.md |
| T35 configuration, CDONE delay, isolation discussion | ../ECP5_CONFIGURATION_R85.md |
| PSRAM_POWER_R08.md (U26 switched pull-downs) | ../PSRAM_R85.md, ../ELECTRICAL_MARGINS_R85.md |
| PIN_TABLE / INTERCONNECT_MATRIX / ELECTRICAL_MARGINS (R08) | ../PIN_TABLE_R85.md, ../INTERCONNECT_MATRIX_R85.md, ../ELECTRICAL_MARGINS_R85.md |
| STATUS_R08.md, RISK_REGISTER_R08.md, EVIDENCE_LEDGER_R08.json | ../../STATUS_R85.md, ../../RISK_REGISTER_R85.md, ../../EVIDENCE_LEDGER.json |
| run_r08_checks.py / package_r08.py (kept as .txt for reference; the live copies are in R08_WORK/tools) | ../../tools/run_r85_checks.py, ../../tools/package_r85.py |
| R09_LAYOUT_AND_RELEASE_PLAN.md | still the R09 plan, but R09 starts only after R8.5 acceptance (STATUS_R85.md §6) |
