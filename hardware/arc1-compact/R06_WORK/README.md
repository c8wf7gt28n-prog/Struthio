# ARC-1 Compact: R06 work area (PASS 6)

Read `STATUS_PASS6.md` first: what was done, the exact commands with exit statuses, evidence,
blockers and next tests. `R05_BASELINE/` is untouched; every R06 change lives here.

```
python3 R06_WORK/tools/run_r06_checks.py          # everything, ~4-5 min; writes evidence/run_<UTC>/
python3 R06_WORK/tools/run_r06_checks.py --quick  # skip R05 HDL and PSRAM mutants
```
Requirements: Python ≥ 3.10, a C11 compiler, GNU make, Icarus Verilog 12, Verilator 5, Yosys ≥ 0.33.
Efinity is optional; without it the runner reports `NATIVE_EDA_NOT_RUN`.

| Path | What | Evidence level |
|---|---|---|
| `STATUS_PASS6.md` | pass-6 status report (required response format) | — |
| `REVISION_LEDGER.md` | revision ledger and R05 compatibility statement | — |
| `docs/ARCHITECTURE_R06.md` | board-level architecture, rails, sequencing, reset graph, power-up hazard | SELECTED_UNVERIFIED |
| `docs/AUDIO_R06.md` | audio note and pin reservation | reserved interface |
| `docs/SOURCES_R06.json` | every document used: URL, SHA-256, what was taken; PSRAM procurement candidate | — |
| `docs/PASS7_PLAN.md` | R07 plan with entry/exit tests | — |
| `board/` | draft pin/voltage map (`r06_board_plan.json`), checker, tests, generated `PIN_MAP_R06.md` | PLANNING_CALCULATED |
| `fpga/psram/` | APS6404L QPI controller, model, testbench, timing table | RTL_SIMULATED |
| `fpga/mailbox/`, `fpga/top/` | F133↔T35 SPI mailbox, PSRAM BIST, T35 top level | RTL_SIMULATED |
| `fpga/efinity/` | T35F400C3 project inputs and steps | NATIVE_EDA_NOT_RUN |
| `firmware/` | BT820 host layer, mailbox client, offload with CPU fallback | HOST_TESTED |
| `tools/run_r06_checks.py` | one-command reproduction | — |
| `evidence/` | run logs, reports, manifests (`LATEST.txt` points at the newest run) | — |
