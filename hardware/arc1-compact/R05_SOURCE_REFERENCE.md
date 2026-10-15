# R05 baseline preservation / instructions

All R05 original files were extracted unchanged under `R05_BASELINE/`; no source files were omitted. Run prior tests **from within that directory**, where existing relative paths remain valid:

```bash
cd R05_BASELINE
python3 tools/check_package.py
python3 tools/check_all.py --skip-hdl  # explicitly PARTIAL host-only check if Icarus is absent
# without --skip-hdl the full R05 test suite requires Icarus installed
```

Do not report R05's 128 MiB FPGA DDR3L as an active R06 memory plan merely because `R05_BASELINE/engineering/architecture.json` says so. Do not report R05's FPGA-to-BT820 graphics bus as the current topology. Preserve reference evidence and provenance. R06 new code belongs in `R06_WORK/` until validated, then incorporate with a new revision and recorded tests.
