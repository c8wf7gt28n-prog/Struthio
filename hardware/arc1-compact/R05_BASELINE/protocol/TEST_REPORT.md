# Portable protocol verification — 14 October 2026

Evidence level: **executed host software tests**. No SPI controller, F133 boot,
physical transport, FPGA RTL endpoint, Efinity build or bench measurement is covered.
The core C and its tests were built with GCC 14.2.0 on this host; Python 3.12.14 and
GNU Make 4.4.1 ran the independent reference checks. Exact commands/exits are in
[verification/results.json](verification/results.json).

| Executed check | Result |
|---|---|
| `make test` | PASS: C behavioral checks plus 14 Python/reference/C differential tests; zero failures/skips |
| `make sanitize` | PASS: C suite under AddressSanitizer and UndefinedBehaviorSanitizer, leak scan disabled |
| Strict `-ffreestanding` C object compilation | PASS with warning-as-error checks; not an embedded link or firmware image |
| Independent committed vectors | 38 vectors: 9 valid, 29 invalid; regenerated purely from Python `struct`/`zlib` and compared byte-for-byte |

Raw [functional output](verification/test.log), [sanitizer output](verification/sanitize.log)
and [freestanding compilation](verification/freestanding_compile.log) are included.
Golden-vector `valid` labels mean a valid frame envelope; arbitrary eight-byte STATUS
data in those vectors is not a typed status signoff. Status semantics have separate tests.

Meaningful boundary/fault checks include:

- CRC standard check, each single-bit mutation of a sample frame, exact endian
  vectors, unsupported version/type/flags/header length, correct-CRC semantic
  violations, oversized payloads, encoder output capacity and `SIZE_MAX` arithmetic.
- Every truncated prefix of a maximum 4120-byte frame, exact-frame/trailing-data
  rejection and overlapping encoder input/output.
- Independent Python encode/decode and 1024 deterministic C/reference roundtrips;
  the C bytes must equal Python bytes, rather than only roundtrip through C itself.
- Every split point of a sample incremental stream, noise, bad-CRC resynchronization,
  payload containing magic, explicit truncated-transaction discard and continued use.
- HELLO idempotence, stale/new epochs, reset with pending work, sequence gaps,
  exhausted credits, exact duplicate pending/completed requests, changed duplicate
  payloads, out-of-order completion, record eviction, repeated completion, exhaustion
  at UINT32_MAX and 10000 reuse cycles without credit underflow.
- Typed STATUS code and credit limits. Generic frame tests deliberately keep STATUS
  contents opaque; consumers must also run `arc1_read_status`.
- 20000 deterministic bounded malformed buffers through decoder and stream parser,
  run both normally and under ASan/UBSan. This is sampled fuzz coverage, not an
  exhaustive formal proof.

The first sanitizer attempt enabled LeakSanitizer and was blocked by the execution
environment: `LeakSanitizer does not work under ptrace`. The subsequent logged run
uses `detect_leaks=0`; ASan and UBSan remain active. No leak-scan success is claimed.
The C implementation and its C tests make no heap allocations.

Session tests use a direct boundary-state fixture to reach UINT32_MAX without
executing billions of requests. No generated native hardware trace is implied.
Results are application-owned: duplicate detection itself does not retain or replay
kernel output. The caller must implement bounded result retention and safe completion
ordering before claiming reliable output delivery.

Remaining integration work includes a real SPI HAL and FPGA byte/queue endpoint,
response ordering/poll/IRQ/timeouts, capacity negotiation, app payload validation,
result retention, CPU restart and independent hardware recovery. Cross-reset
exactly-once behavior, throughput, latency and useful FPGA acceleration are unmeasured.
