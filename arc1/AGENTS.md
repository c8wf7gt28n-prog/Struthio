# AGENTS.md — ARC-1 agent-native SDK

You are a coding agent working on the ARC-1 host SDK (milestones M0–M1 of
ARC1-SDK-ER-002 v0.2). Read this file and `README.md` first. You do not need
any earlier chat transcript; everything you need is in this repository.

## What exists, honestly

- A host-only SDK: the `arc1` CLI (Python ≥ 3.9, standard library only), the
  `arc1/game.h` C11 API (ABI 0.2, *proposed*), a deterministic headless host
  runtime, the `hello_arc1` demo and self-tests.
- **No** ARC-1 board, target cross-compiler, firmware, RTL or device transport.
  `arc1 device deploy` returns `NOT_AVAILABLE`, `arc1 fpga check` returns `NOT_RUN`.
  Never write code, docs or reports that suggest otherwise.

## Commands (run from this directory)

| Goal | Command |
|---|---|
| Health check | `./arc1 doctor` |
| Build the demo | `./arc1 build examples/hello_arc1` |
| Run it, dump frames | `./arc1 sim examples/hello_arc1 --replay tests/replays/steer.replay --dump 0,60` |
| Project tests | `./arc1 test examples/hello_arc1` |
| Hardware facts | `./arc1 hw inspect [--chip gpu45]` |
| Check a pass record | `./arc1 pass validate passes/ARC1-PASS-0001` |
| Whole SDK suite | `python3 tests/run_tests.py` |

Add `--json` to any command for the machine-readable result
(`sdk/schemas/tool-result.schema.json`). Exit codes: 0 PASS, 1 FAIL, 2 usage or
input error, 3 NOT_AVAILABLE/NOT_RUN, 4 internal error. On Windows, prefix with
`python`.

## How to run a pass

1. Copy `passes/ARC1-PASS-0001/pass.json` to `passes/ARC1-PASS-<next>/` and fill in
   `state: PLANNED`, `owner` (one accountable agent or human), `objective`, the
   full 40-character `base_commit` (`git rev-parse HEAD`), `inputs` (the
   lock digest is `sha256sum tools/lock/toolchain.lock.json`) and `effort`.
2. **SDK Evolution Covenant:** `effort.sdk_reserved` must be at least 5% of
   `effort.planned_total`. The SDK change must be reusable, live in separate
   paths from the main change, and be proven by an acceptance test listed in
   `validation`. A changelog edit is not an SDK change.
3. Implement. Keep the main change and the SDK change separately identifiable.
4. Verify. Copy the reports you cite into `passes/<id>/reports/` and record
   their SHA-256. Use `not_run`/`not_available` with a reason for anything you
   could not execute — never mark it passed.
5. Write `HANDOFF.md` with a `## Reproduce` section a fresh agent can run.
6. Set `state: REVIEW` and run `./arc1 pass validate passes/<id>`. Only an
   independent reviewer may set `review.state: accepted` and `state: COMPLETE`.

## Rules

- **Evidence classes.** Every claim carries one of DESIGN, STATIC_CHECK,
  HOST_SIM, RTL_SIM, FPGA_PNR, BOARD_TEST. Host simulation never satisfies a
  board gate. A positive hardware claim needs a board ID, equipment and a
  hashed log.
- **Hardware facts.** `hardware/manifests/` is the only source of hardware
  facts. Do not invent register addresses, clocks, pin maps, bandwidth or
  electrical limits. Unknown is `null`. The four memory pools are independent;
  nothing has a shared address space.
- **Protected files** (`policy/protected_paths.json`): schemas, public
  headers, the runtime, hardware manifests, the toolchain lock, test plans,
  goldens and this file. Modifying or deleting one must be disclosed in the
  pass record's `sensitive_changes`, and the validator checks this against
  `git diff`. Never weaken a test, loosen a check or re-record a golden
  (`--update-golden`) without disclosing it.
- **No self-approval.** You cannot accept your own SDK change or your own
  test-baseline change (COV-003).
- **Stop and ask the owner** before anything touching board flashing,
  firmware, power or clocks, pin maps, the 45F shell interface, package trust,
  or any assumption about the memory map, F133–D213 boot path, HDMI audio or
  USB port allocation (spec §13.2). These are blocking issues, not things to
  document around.
- **Tool safety.** The CLI refuses paths that escape a project, runs
  compilers and simulations with a timeout, a scrubbed environment and
  resource limits. Do not bypass it to reach hardware.
- **Provider neutrality.** Nothing in the CLI, C API or schemas may depend on
  a specific model provider or agent framework.
- Record observable actions and evidence. Do not store private reasoning.

## Layout

```
arc1                    CLI launcher (python3 script)
sdk/cli/arc1cli/        CLI implementation, stdlib-only JSON Schema subset validator
sdk/include/arc1/       public C headers (ABI 0.2, proposed)
sdk/runtime/host/       host reference runtime (HOST_SIM evidence)
sdk/templates/game/     `arc1 new` template, with goldens
sdk/schemas/            JSON Schemas: pass, hardware, package, tests, golden, tool result, lock
hardware/manifests/     R10 design facts (unverified) and the simulation-only descriptor
examples/hello_arc1/    vertical-slice demo
tests/                  SDK self-tests, conformance test, fixtures (positive and negative)
tools/lock/             toolchain lock
policy/                 protected paths
passes/                 pass records, reports, handoffs
docs/                   API, CLI and traceability reference
```
