# arc1 CLI contract (schema 0.2)

Every command supports `--help` and `--json`, and `arc1 --version` prints
the SDK and schema versions. Commands never prompt. Results conform to
`sdk/schemas/tool-result.schema.json`; the CLI validates each result before
emitting it.

## Exit codes

| Code | Verdict |
|---|---|
| 0 | PASS |
| 1 | FAIL: a check ran and failed, or a promised artifact is missing |
| 2 | Usage or input error: bad arguments, unreadable JSON, a path escaping its project, an existing directory for `new` |
| 3 | NOT_AVAILABLE / NOT_RUN: the capability does not exist here; nothing was simulated in its place |
| 4 | Internal error (SDK bug) |

## Result fields (CLI-001)

`schema_version`, `sdk_version`, `command`, `invocation_id`,
`toolchain_digest`, `input_digest`, `evidence_level`, `verdict`, `board_id`,
`warnings`, `failure_reasons[{code, message, path?}]`,
`artifacts[{path, sha256}]`, and optionally `test_count`, `failed_count`,
`log_sha256` and `details`.

- `invocation_id` is derived from the command, the input digest and the
  toolchain digest. Identical inputs give byte-identical reports.
- `toolchain_digest` covers the lock file, the Python version and the
  compiler's `--version` line.
- A `PASS` with an artifact missing on disk is converted to `FAIL` with code
  `CLI-001`.
- `board_id` must be non-null exactly when `evidence_level` is `BOARD_TEST`.

## Commands

| Command | Evidence | Writes |
|---|---|---|
| `arc1 doctor` | STATIC_CHECK | — |
| `arc1 new <name> [--dir D]` | STATIC_CHECK | `D/<name>/` from `sdk/templates/game` |
| `arc1 build [project]` | STATIC_CHECK | `build/gen/arc1_assets.h`, `build/host/<name>`, `build/host/build-stamp.json`, `build/logs/build.log`, `reports/build.json` |
| `arc1 sim [project] [--frames N] [--replay F] [--dump 0,60]` | HOST_SIM | `build/sim/trace.txt`, `frame_NNNNNN.ppm`, `sim.log`, `reports/sim.json` |
| `arc1 test [project] [--only ID] [--update-golden]` | HOST_SIM | `build/test/…`, `reports/test.json`; with `--update-golden`, `tests/golden/*` |
| `arc1 hw inspect [--manifest F] [--chip ID]` | DESIGN | — |
| `arc1 pass validate <dir or pass.json> [--root D] [--no-git]` | STATIC_CHECK | — |
| `arc1 fpga check` | NONE → NOT_RUN | — |
| `arc1 device deploy` | NONE → NOT_AVAILABLE | — |
| `arc1 device detect` | NONE: PASS if a FEL device answers `xfel version`, else NOT_AVAILABLE | — |
| `arc1 device flash --partition ID --image F` | NONE → NOT_AVAILABLE for a valid plan; FAIL if the image does not fit or the partition is locked | — |
| `arc1 ui [project] [--snapshot ITEM]` | interactive; exit 0 on Q | build/sim/test outputs like the commands it runs |

`sim` and `test` refuse to run on a missing or stale build (`BUILD_STALE`).
The build stamp records the digest of the sources, assets, manifest, SDK
runtime and toolchain.

## Test plan kinds (`tests/arc1.tests.json`)

- `golden`: the trace and the dumped frames must match
  `tests/golden/<id>.json`, and so must the replay digest recorded with the
  golden. A mismatch reports the first divergent frame.
- `determinism`: 2–5 runs of the same replay must agree.
- `must_differ`: a negative control. The given input must **not** reproduce
  the named golden, which proves the golden can detect the change.

`--update-golden` re-records goldens and emits a `TST-003 review-sensitive`
warning. Disclose the change in the pass record.

## Safety (CLI-003)

Paths from manifests, replays and pass records are resolved inside their
base directory, and escapes are refused. Child processes get a scrubbed
environment (`PATH`, `LC_ALL=C`, `TZ=UTC`, `SOURCE_DATE_EPOCH=0`; no tokens
or credentials) and a timeout (120 s compile, 60 s sim). On POSIX they also
get CPU and file-size limits. `ARC1_CC` may select only a compiler listed in
the lock.

## Debug console and flasher

`arc1 ui` draws an 80×25 DOS-style screen with curses. Every menu item calls
the same `execute()` path as the command line, so the UI shows exactly the
verdicts the CLI would give. `--snapshot ITEM` renders one screen as plain text
without a terminal, for tests and scripts. ITEM is a menu name (`doctor`,
`hardware`, `build`, `sim`, `test`, `frames`, `passes`, `detect`, `flasher`,
`about`), `flasher:<partition>:<image>`, or `menu`. Without UTF-8, the screen
falls back to ASCII. It needs at least 80×25 and asks for a bigger window
otherwise.

`device flash` reads the vendored R10 NOR map. A plan lists the operation, the
image size and SHA-256, the fit, the risks, the rollback state, the three open
gates and the `xfel` commands a write would use: version, spinor, backup read,
write, readback and compare. That sequence is UNVERIFIED on R10. The command
always ends NOT_AVAILABLE or FAIL; there is no code path that writes. `device
detect` runs only `xfel version` (10 s timeout). A device that answers is
reported with a warning that this does not identify a board.

## Not yet implemented

- An MCP adapter. When one is added, it may expose only these commands.
- COV-005 aggregation windows.
- COV-007 impact review.
- Target builds, FPGA flows and device deploy.

### `arc1 brand [--json]`
Verifies official image digests and 16x2 LCD text constraints. This is a STATIC_CHECK, not a hardware or Windows-11 compatibility claim.
