# ARC-1 Compact — R10 engineering handoff

R10 is the current architecture. Start with:

1. `R10_WORK/BASE.md` — authority and provenance.
2. `R10_WORK/DECISIONS.md` — the four resolved architecture choices.
3. `R10_WORK/IMPROVEMENTS_CODEX.md` — latest implementation delta and exact evidence limits.
4. `R10_WORK/qa/R10_gate_report.md` and `R10_WORK/qa/R10_memory_go_no_go.md` — gates and fabrication holds.
5. `R10_WORK/spec/ARC1_R10.txt` and `R10_WORK/spec/ARC1_MEMORY_R10.txt` — controlling specifications.

`R05_BASELINE`, `R06_WORK`, `R07_WORK`, `R08_WORK`, `R85_WORK`, and `R85C_WORK` are preserved historical/reference
trees. Their root-direction documents do not override R10. Reuse is allowed only with explicit provenance and fresh
R10 evidence.

Run host checks with `cd R10_WORK && ./run_host_checks.sh`. Run the full RTL/P&R suite with `./run_all.sh` only in an
environment containing Icarus, Verilator, Yosys, nextpnr-ecp5, and Project Trellis. Neither suite proves hardware.

Fabrication remains **HOLD**. Do not convert HOST_TESTED, RTL_SIMULATED, or OPEN_TOOLCHAIN_ROUTED results into a claim
of electrical or prototype success.
