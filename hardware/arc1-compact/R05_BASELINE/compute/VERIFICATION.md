# Executed compute verification

Status: **host and RTL simulation PASS**; device implementation pending.

`make check-c` executed successfully on 14 October 2026 with GCC 14.2.0
(Debian 14.2.0-19) and Python 3.12.14:

- Strict C11 warning-as-error shared-library and vector-runner builds.
- GCC undefined-behavior sanitizer: 1165 independent-oracle vectors passed.
- ctypes scalar and batch calls: 1165 comparisons each passed, including ABI sizes,
  tag preservation and zero-count/null batch behavior.
- The oracle includes 15 hand-checked results and deterministic random full-range,
  gameplay-sized, boundary/tie, saturation/cancellation and invalid cases.

Icarus Verilog 11.0 and vvp 11.0 actually compiled and simulated the RTL:

- All 1165 independent-oracle arithmetic/result-order comparisons passed.
- Output stability under backpressure: 3563 stalled output cycles checked.
- Input hold/backpressure: 12261 stalled input cycles checked.
- 1164 simultaneous output-retirement/new-input-acceptance events exercised.
- Reset during calculation and while a completed result is stalled both canceled
  their transaction without a later ghost result.
- The normal oracle run plus drain used 13465 arbitrary simulation cycles. The
  testbench clock does not establish a target device frequency or achieved rate.

The initial simulator attempt exposed an Icarus 11 `$fscanf` limitation when
scanning directly into an indexed memory element. Reading through a scalar
temporary fixed testbench portability; an explicit timescale removed the compiler
warning. No arithmetic or handshake RTL change was needed. That failed attempt
returned exit code zero despite ERROR diagnostics, so the verification runner
requires explicit host/RTL PASS markers and rejects ERROR/FATAL output.

Reproduce the full clean rebuild, simulation, logs and machine-readable record:

```
python3 tests/run_verification.py --iverilog /workspace/.tools/iverilog/bin/iverilog --vvp /workspace/.tools/iverilog/bin/vvp
```

See [verification_results.json](verification_results.json),
[complete output](verification_logs/complete_verification.log),
[tool versions](verification_logs/tool_versions.log) and
[initial failed attempt](verification_logs/initial_icarus_attempt.log).

No Efinity project, synthesis, placement, STA, resource fit, physical timing, real
FPGA test or CPU-versus-FPGA speedup is established by these checks. No guessed
device pins, SPI PHY, board netlist or BT inverse-matrix conversion is supplied.
