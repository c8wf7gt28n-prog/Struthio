# Reproduce the Compact R0.5 checks

Run from the extracted package root with Python 3.10+, a C11-capable `cc`, GNU Make,
and Icarus Verilog (`iverilog` and `vvp`). Python uses only its standard library; no
package installation or network connection is needed. The Makefiles and shared
library targets assume a POSIX host such as Linux. No F133 cross-toolchain or Efinity
installation is required for these software/simulation checks.

With Icarus on PATH:

```sh
python3 tools/check_all.py
```

In the present workspace, Icarus is outside PATH. Use:

```sh
python3 tools/check_all.py \
  --iverilog /workspace/.tools/iverilog/bin/iverilog \
  --vvp /workspace/.tools/iverilog/bin/vvp
```

Those absolute tool paths describe this environment only; use the installed paths
on another machine. The runner finds the project root from its own file location,
so it can also be invoked by absolute script path from another working directory.
HDL tool paths must have no whitespace or make/shell metacharacters because the
existing compute Makefile expands those variables in recipes without quoting.

**Default execution requires HDL simulation.** A missing compiler/runtime, nonzero
subprocess, missing explicit pass marker, skipped required unit test, invalid planning
report, stale compute report or explicit compute `FAIL` causes a nonzero runner exit.
The runner stops at the first failure and records incomplete coverage.

For an explicitly partial check when Icarus is unavailable:

```sh
python3 tools/check_all.py --skip-hdl
```

This still rebuilds and tests C compute code for integration, but reports
`PASS_HOST_ONLY_HDL_SKIPPED` and `hdl_status: SKIPPED_EXPLICITLY`. It does not read an
old compute RTL report as evidence for the new run and does not report an HDL pass.
Use `--timeout SECONDS` to change the default 300-second timeout per subprocess.

## Executed sequence

1. Record Python/compiler/Make version output and resolve required executables.
2. Run display unit tests (at least 14) and its CLI planning validator.
3. Run memory unit tests (at least 18) and its CLI planning validator.
4. Force a fresh protocol build, C behavior/fault checks and independent Python/C
   reference tests (at least 14, with no skipped differential suite).
5. Run protocol AddressSanitizer/UndefinedBehaviorSanitizer checks with
   `SANITIZER_OPTIONS=detect_leaks=0`, then strict freestanding C object compilation.
6. Run `compute/tests/run_verification.py --iverilog ... --vvp ...`. Require its fresh
   `PASS_HOST_AND_RTL_SIMULATION` report, 1165-case C and RTL comparisons, exercised
   stalls/simultaneous handshakes, reset checks, and no ERROR/FATAL diagnostic. In
   explicit skip mode, run only `make -B check-c` and verify its C oracle markers.
7. Run integration unit tests (at least 13), then the 256-object/four-batch host demo.
   Validate its known 218 visible/38 culled bounds and zero duplicate re-executions.

The protocol implementation has no heap allocation. LeakSanitizer was blocked by
ptrace in this execution environment; the runner deliberately disables only that
scan. ASan and UBSan remain enabled. **No leak-scan pass is claimed.** Freestanding
object compilation checks portable C compilation, not startup code, linking, an
F133 image or firmware boot.

## Outputs and interpretation

Each invocation creates a new timestamped directory beneath
`verification/last_run/`, containing raw subprocess logs, planning JSON, a copied
fresh compute report (or explicit host-only report), integration output and a
machine-readable `summary.json`. Prior run directories are preserved.
`verification/last_run/summary.json` is the latest-run index, including commands,
tool paths, exits, evidence scope, failures and the runner source hash.
Each run's `source_manifest.json` binds the current display/memory input JSON,
validators, test code and protocol/compute/integration source with SHA-256 and byte
counts. This includes changes to the source references embedded in the display
configuration. The run fails if those inputs change during execution. The fresh
consolidated manifest, reports and command logs establish this invocation's software
provenance; prior component verification files retain only their recorded evidence.
Hashes identify local bytes, not vendor authenticity or physical validation.

`integration/demo_report.json` contains the current successful demo JSON and its run
identifier. At run start it is marked not run, and a failed run replaces it with an
explicit failure/not-validated record, preventing reuse of a stale successful demo.
Build products are regenerated under `protocol/build/` and `compute/build/`.
The compute verifier also refreshes its own `compute/verification_logs/` and
`compute/verification_results.json`; the runner retains a report copy for its run.

`PASS_HOST_AND_RTL_SIMULATION` means planning checks, host software checks and RTL
simulation passed. `PASS_HOST_ONLY_HDL_SKIPPED` is a partial result. Neither state
qualifies an Efinity build, synthesis, static timing, board routing, real DDR/SPI,
display operation, game frame rate, input latency, power, useful FPGA acceleration
or hardware recovery. The integration byte/time figures remain calculated protocol
budgets and its C compute endpoint remains a host stand-in for future firmware/RTL.
