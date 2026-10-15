# R06 revision ledger

| Date (UTC) | Revision | Change | Evidence |
|---|---|---|---|
| 2026-10-14 | handoff | Owner R06 directive plus unchanged R05 baseline (142-file manifest) received | `../MANIFEST_SHA256.txt` |
| 2026-10-15 | R06-draft-1 | Pass 6 implementation, all of it new under `R06_WORK/`; no file outside `R06_WORK/` changed. `R06_WORK/README.md` placeholder replaced (the one manifest entry intentionally changed) | `evidence/` (see `LATEST.txt`) |

## R06-draft-1 contents

* `fpga/psram/`: APS6404L QPI controller, user-clock CDC port, behavioural/checking model,
  testbench in 3 clock configurations, 4 mutation checks, lint, Yosys synthesis.
* `fpga/mailbox/`, `fpga/top/`: AMBX v1 SPI mailbox, transport loopback, PSRAM BIST, T35 top
  level, and a system testbench that drives R05 golden frames through the mailbox.
* `fpga/efinity/`: pin CSV, Interface Designer script (unvalidated), SDC, build steps.
  NATIVE_EDA_NOT_RUN.
* `board/`: machine-checked draft pin/voltage map, source extractors, 19 checker tests,
  generated `PIN_MAP_R06.md`.
* `firmware/`: BT820 host transactions, AMBX client, accelerator dispatch with CPU fallback,
  mocks, and 231 host checks (also under ASan/UBSan).
* `docs/`: architecture, audio note, sources register (URLs and SHA-256), PASS 7 plan.
* `tools/run_r06_checks.py`: one-command reproduction, including the R05 rerun in a scratch copy.

## R05 compatibility statement

R05 wire ABI v1, the transform numeric contract and the scene payload v1 are used **unchanged**.
The R05 C sources compile by path, unmodified. R05's own checks pass again (`r05_check_all` in
every evidence run, executed in a copy so `R05_BASELINE/` stays byte-identical). No versioned
protocol change was made in R06.
