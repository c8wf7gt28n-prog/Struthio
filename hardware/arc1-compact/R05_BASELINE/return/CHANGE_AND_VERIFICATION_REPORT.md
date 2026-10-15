# R05 change and verification report

R04 established the owner-selected Compact direction and continuation queue. R05
adds actual implementations and reproducible checks while retaining the same
F133-B/T35F400C3/BT820B core, named panel and 64+128+128 MiB private RAM target.

| Changed group | Concrete result |
|---|---|
| `protocol/` | C11 frame codec, stream parser, session/credits/retries plus independent codec/golden vectors, behavior/fuzz/sanitizer checks |
| `compute/` | Checked portable C reference, sequential SystemVerilog transform/culling kernel, independent numeric oracle and actual HDL testbench |
| `integration/` | Proposed explicit LE application ABI, synchronous C-library endpoint model, duplicate result cache, 256-object bounds demo and 13 integration tests |
| `display/` | Corrected porch convention, executable timing/range checks, invalid R04 regression and conditional BT register model |
| `memory/` | BT address-allocation model and overlap/alignment/reserved-range validation |
| `system/` | 400-ball manufacturer source extraction/independent comparison, blank-net CSV, ownership/recovery worksheet |
| `tools/`, `VERIFY.md` | Standard-library reproducible check runner, source bindings, actual logs and source/archive checker |
| Root handoff and `engineering/` | R05 instructions, Word/Markdown handoff, current task/decision/source registers and evidence coverage |
| `reference/r04/` | Preserved superseded handoff and registers; all five original attachments retained unchanged |

The actual final commands, executable paths, start/finish times, exit codes,
per-step logs and source hashes are in `verification/last_run/summary.json` and
its linked run directory. `compute/verification_results.json` retains explicit
C/RTL PASS markers and numeric/backpressure/reset coverage. Component reports
distinguish earlier records from the final consolidated run. The author used a
locally extracted Icarus11.0 package; acquisition/hash details are in
`tools/toolchain_provenance.json`. Host C was not cross-compiled to F133.

Independent reviews checked display/memory evidence limits, protocol/application
integration and kernel/ABI/handoff accuracy. A review found Python ctypes could
silently narrow out-of-range wire fields; strict validation and regression cases
were added before final verification. An initial Icarus testbench file-read issue
was fixed in the testbench; its failed log is retained. The final compute runner
requires real PASS markers and rejects ERROR/FATAL diagnostics despite process exit.

R05 corrects R04's additive display porch interpretation. The same 48 MHz clock,
1280×625 raster and nominal 60 Hz are retained; panel-native back intervals include
sync by inference and remain subject to endpoint confirmation. No BT register was
written. No other hardware choice was changed.

Still unexecuted: full native Efinity synthesis/place/route/STA/fit; F133 boot and
SPI HAL; integrated FPGA SPI/QSPI/DDR/BT firmware; real renderer/game fidelity;
board power/memory/display/recovery/latency/load tests. No acceleration, throughput
or rendered FPS result was measured. The immediate next result is a reproducible
real host/FPGA mailbox and BT initialization/drawing path, with pinned tools and
raw evidence at each boundary.
