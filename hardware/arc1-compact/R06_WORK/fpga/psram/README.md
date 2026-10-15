# T35 private PSRAM controller (R06)

Evidence level: **RTL_SIMULATED** (Icarus Verilog 12), lint-clean under Verilator 5.020, and
synthesizable by Yosys 0.33 (generic `synth` plus open-source `synth_efinix`, giving a resource
**estimate** only). **NATIVE_EDA_NOT_RUN**: Efinity has not been run, so there is no T35 fit, no
timing and no IO placement. **No hardware exists**: nothing here shows a working 8 MiB memory.

| File | Role |
|---|---|
| `rtl/psram_qspi_core.sv` | mclk-domain controller: power-up wait, QPI/SPI reset, Read ID check, QPI entry, chunked QPI 'h38 write / 'hEB read, watchdog, recovery |
| `rtl/psram_user_port.sv` | user-clock front end: request/stream/response interface, buffer-ownership CDC, user-side timeout, two dual-clock 256-byte buffers |
| `tb/aps6404l_model.sv` | behavioural PSRAM model with protocol and timing checkers (simulation only, not vendor IP) |
| `tb/tb_psram.sv` | self-checking testbench with an independent byte-shadow scoreboard and random stalls |
| `Makefile` | `make lint sim synth synth-efx mutants` |
| `PSRAM_TIMING_TABLE.md` | traceable datasheet command/timing table and how each value is met |

## User interface (uclk domain)

```
req_valid/req_ready, req_write, req_addr[22:0], req_len (1..256)
wr_valid/wr_ready/wr_data   -- write data; consumed only if the request is accepted for execution
rd_valid/rd_ready/rd_data   -- read data, streamed before an OK response
resp_valid/resp_ready/resp_status: 0 OK, 1 NOT_READY, 2 INVALID, 3 TIMEOUT, 4 CORE_FAULT
recover (pulse), ram_ready, ram_error, ram_err_code (1 = ID/KGD mismatch, 2 = watchdog)
```

Every request receives exactly one response. Writes and reads are refused (`NOT_READY`) until
initialisation finishes, so no write can reach the device after reset before init. After a
`TIMEOUT` the port refuses work until the clock domains are in sync again; a late completion is
discarded. `CORE_FAULT` or `TIMEOUT` on a write leaves that address range **undefined**, and the
owner must rewrite it.

## Tests (PASS_6_AND_7 step 5 → where covered)

| Required test | Testbench section |
|---|---|
| reset readiness, no access before init | T1 (also checks no CE# before tPU, ID registers, QPI state) |
| bit walking | T2 |
| address walking | T3 (walking ones and zeros over all 23 address bits) |
| pseudo-random data | T4 (200 random ops: random, hot-spot, page-edge, top-of-memory) |
| first/last address | T5 |
| page / wrap boundaries | T6 (+ global check: zero page-crossing bursts); wrap past 8 MiB is rejected in T8 |
| sequential bursts | T7 (32 × 256 B back-to-back, plus simulated throughput) |
| randomized stalls | all tests: 30 % write gaps, 40 % read back-pressure, 30 % response stalls |
| invalid requests | T8 (len 0, len > 256, end > 8 MiB: no PSRAM traffic) |
| clock-domain crossing | 3 configurations: uclk faster than mclk, slower, and 2.5× faster with CLK_DIV = 2 |
| reset in transfer | T10 (memory-domain reset mid-burst → CORE_FAULT, re-init, older data intact) |
| recovery after error | T11 (KGD = FAIL injected → ERR_ID → recover), T12 (watchdog → recover), T13 (user timeout → resync) |
| read-after-write | T14 (plus every write/read pair) |
| CS timing | model checks tPU, tCPH, tCEM, tCSP, tCHD, tSP, tHD, tRST, mode-0 CLK level, 33 MHz Read ID limit, contention |

Mutation check: four deliberately broken controllers (no page split, no bus turnaround, skipped
reset, one wait cycle short) must each **fail** the bench (`make mutants`).

## Known limits / next steps

* The FPGA-reset path assumes PSRAM VDD has been stable for ≥ 150 µs; the PU counter also runs
  after every FPGA reset. The board must not power the PSRAM from a rail that comes up after T35
  user mode starts. See the board plan.
* The QPI-form reset sent to a device already in SPI mode is assumed to be ignored. Confirm on a
  bench.
* If the controller clock stops while CE# is low, the device's tCEM is violated, and data loss is
  possible in real silicon. The T13 test only stops the clock while CE# is high, which is when
  stopping is safe.
* Store-and-forward 256-byte buffers keep CE# timing deterministic. Streaming or prefetch is a
  later optimisation, once a measured workload calls for it.
