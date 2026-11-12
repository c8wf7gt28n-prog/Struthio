# Ledger Engineering API v1

1.9 additive operations: `clip.prepare/context/inspect/propose/test/finish` and
`remote.sessions/revoke`. See `LEDGER_1_9.md` and `OWNER_HOSTED_1_9.md` for exact
schemas, scoped grants and trust boundaries. The external Clip route has zero
automatic inference calls. Agent proposals bind one ARC-OS C implementation file;
exact native-execution authorization and independent source acceptance remain
separate. Direct TLS is optional, HTTP remains loopback-only, and same-policy
unexpired pairings survive service restart. Historical 1.3 proxy assumptions
below are superseded by the current owner-hosted guide.


1.4.9 additive operations: `project.authority`, `agent.handoff`, `tasks.templates`,
`tasks.plan`, `clip.overview`, `repairs.propose/inspect/attest/authorize`.
See `READINESS_V1_4_9.md` for the narrow failing-assertion exception, separate
review role and exact revision binding. Existing envelope and normal promotion
requirements remain; plans are read-only and do not authorize their own steps.

Authority: workbench.engine.engineering(root). All new clients call
Kernel.dispatch(operation, params, Principal). Identity, file scope, tools and
mode come from the trusted local operator or authenticated session, never from
request parameters. Responses are {schema: "arc-ledger.kernel/1", ok: true,
result: ...} or {schema, ok: false, error: {code, message}}.

## Discovery and transports

- CLI: python -m workbench.engineering_cli call capabilities
- Isolated edits: add --allow-candidates before call. This grants no acceptance.
- Local owner decisions: --operator before call. Never give that launch flag
  to an external agent or treat it as remote authentication.
- MCP stdio: python -m workbench.engineering_cli --allow-candidates mcp
  Standard JSON-RPC initialize, notifications/initialized, tools/list, tools/call.
  Protocol 2025-11-25; tool names replace dots with underscores. Schemas are
  discoverable and reject extra parameters. Logs never share the protocol stream.
- Existing JSON-lines: python arc1 agent --allow-writes; method names have the
  engineering. prefix (e.g. engineering.jobs.submit). Legacy envelope encloses
  the kernel envelope. Direct files.write is retired in favor of candidates.
- Remote: POST /api/call {operation, params}; authenticated cookie and CSRF token.
  Same kernel, no remote shell, flash method or caller-supplied principal.

## Operations

Simulation-first additions (PASS-0020): `simulation.inspect` is read-only and
returns source bindings, missing critical models and the unestimated confidence
goal. `jobs.submit` with tool `simulation.campaign` runs bounded causal fixture
cases and existing host C firmware checks. The tool is discovered by every
transport and the existing desktop selector. A Completed experiment job can
carry outcome BLOCKED: its host checks passed, but target-model completeness and
fabrication remain blocked. Scenario success never supplies a first-boot
probability. See `SIMULATION_FIRST_V1_5.md`.

capabilities, project.inspect, project.inventory, files.read, files.search;
jobs.submit/list/get/pause/cancel/resume; evidence.list/read;
candidates.create/patch/diff/review/reject/authorize_execution/accept/rollback/stage;
clip.submit/authorize; remote.disable. Query capabilities for permission-filtered
availability and schemas() / MCP discovery for exact fields.

jobs.submit takes tool, optional candidate, timeout (1–600 seconds), goal and
request_key. Reuse request_key with the same identity to reconnect without
starting duplicate work. jobs.get returns state, current step and evidence ID.
Four active jobs maximum, one compiler/test job per source workspace. Read-only
inspection holds no long-running source lock.

candidates.create takes goal, paths and required_tools. Paths must be normalized
relative paths inside approved prefixes. Hardware, original JS and pass evidence
cannot be modified by these agents. candidates.patch requires id, path, current
sha256 and complete UTF-8 content. Existing tests/oracles/generated constants
are protected. Changes are recoverable and the original diff remains available.

Baseline and candidate tests must both pass at their exact source revisions.
Any source drift requires a fresh candidate/baseline. Candidate execution requires
an operator's authorization for the exact revision; changes invalidate that grant.
Source promotion also checks current hashes while holding the write transaction.
Human editor saves participate in the same transaction and recheck disk state.

clip.submit takes goal, 1–5 exact C/header paths, provider, max_iterations (1–3),
max_runtime (10–600), max_provider_calls (0–3), test_tool and share_source.
The deterministic provider additionally takes proposals: a list of iterations,
each containing patch objects {path, sha256, content}. This adapter is explicitly
for offline tests. Gemini is an adapter using the existing user settings.
Compatible external models can orchestrate candidates through MCP/CLI without
using Gemini. Delegation retains the originating identity and bounded scope.

## Tool catalog and evidence

`boot.first_stage` cross-builds and runs the RV64 startup/loader experiment on
QEMU virt; `boot.first_stage.inspect` exposes its source-bound coverage and
remaining gates. The execution class is a generic target CPU model, stored
under the existing conservative HOST_SIM evidence class. It never qualifies
F133/D213 SoC behavior or a board image. See `software/boot/first_stage/README.md`.

`boot.campaign` runs the bounded firmware/image host campaign; `boot.inspect`
is a read-only, source-bound status operation. It never promotes host test or
image-format success to target boot readiness. Target status remains BLOCKED.
See `docs/HARDWARE_STATUS.md` for exact scope and remaining gates.

STRUTHIO build/test/replay/package/reference_parity, diagnostic.compare,
hardware.inspect, ledger.kernel_tests/desktop_tests, firmware.f133/d213,
rtl.fpga45/fpga12 and SDK test/simulate. Availability means a registered command,
not that the machine has every dependency installed. No arbitrary argv/shell
is accepted. A failed/missing dependency is a real failed job with diagnostics.

Evidence contains source revision, tool/argv/cwd, environment, exit status,
stdout/stderr, duration and generated artifact hashes. Native build reports also
contain compiler version and every native input hash. Resource use not measured
is null. Physical hardware is false for host runs. See .ledger/jobs/<id>/ logs
locally and evidence.read remotely. Database/session/candidate internals are
excluded from file-read APIs and exports. Do not distribute .ledger/.

## Extension points

Add a fixed tool in TOOLS and tests for its permission/timeout/error behavior.
Add operations to CAPABILITIES, schemas(), dispatch and regression tests together.
Provider adapters propose patches only; they do not execute commands or approve
source. Update the schema version when breaking compatibility. Keep UI/provider
imports out of engineering_kernel.py. See docs/WORKSHOP.md for application
self-development and safe restart/apply.
