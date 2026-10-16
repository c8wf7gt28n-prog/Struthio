# Traceability: ARC1-SDK-ER-002 v0.2 → this repository

State as of ARC1-PASS-0004 (M0–M1, R10 hardware facts, debug console). "Enforced" means a check that fails, and
a negative fixture that proves it fails. Test names refer to
`tests/run_tests.py`.

| Req. | Status | Where | Acceptance |
|---|---|---|---|
| DEC-01 / CLI-004 | Enforced by design | stdlib-only CLI, C11 API, no provider code | review; `python_packages: []` in lock schema |
| DEC-05 | Enforced | `evidence_level` in every result, ladder in schemas | `tool-result.schema.json` |
| COV-001 | Enforced | `passrec.py` (exact rational 5% check) | `budget-below-five-percent`, positive `exactly-five-percent` |
| COV-002 | Enforced | reusable, separable, existing paths, passing acceptance test | `missing-sdk-evidence`, `sdk-path-missing`, `sdk-not-separable`, `sdk-not-reusable` |
| COV-003 | Enforced | no self-acceptance; COMPLETE needs accepted review | `self-acceptance`, `complete-without-review` |
| COV-004 | Partly | changelog-only SDK change rejected | `changelog-only` |
| COV-005 | Not implemented | — | — |
| COV-006 | Enforced | deferral needs approver ≠ owner | `unapproved-deferral`, positive `approved-deferral` |
| COV-007 | Not implemented | — | — |
| PASS-001 | Enforced | single `owner` pattern | `missing-owner`, `two-owners` |
| PASS-002 | Enforced | 40-hex `base_commit`, existence in git, schema rev, lock digest | `branch-name-as-base`, `test_unknown_base_commit_rejected` |
| PASS-003 | Not enforced | policy only (AGENTS.md) | — |
| PASS-004 | Enforced | commands, reports and digests for executed checks; reasons for unrun checks; report/record consistency | `report-tampered`, `artifact-tampered`, `verdict-contradicts-report`, `not-run-without-reason` |
| PASS-005 | Enforced (structure) | handoff has `## Reproduce`; BLOCKED lists blockers | `handoff-not-reproducible`, `blocked-without-blockers` |
| REP-001 / SEC-002 / TST-003 | Enforced vs git | `policy/protected_paths.json` + `git diff base` must be disclosed | validator `_git_checks`; GitHub branch protection still needed |
| REP-002 | N/A yet | no generated register docs | — |
| REP-003 | Partly | artifact digests, lock, reproduction steps | pass record artifacts |
| HW-001 | Enforced | every field present; every reference resolves to a vendored source whose SHA-256 matches and whose text contains the anchor | `required-field-dropped`, `duplicate-chip`, `source-tampered`, `source-missing`, `source-path-escape`, `dangling-reference`, `dangling-anchor`, `duplicate-peripheral-id` |
| HW-002 | Enforced | per-pool owner, no shared address space, cited capacity | `flat-memory-claim`, `memory-owner-mismatch`, `memory-fact-uncited` |
| HW-003 | Enforced | endpoints known, measured needs evidence, board links cite sources, pin lists equal the R10 interface table | `measured-without-evidence`, `throughput-on-proposed-link`, `link-to-unknown-chip`, `link-without-source`, `peripheral-unknown-attachment`, `test_r10_link_pins_match_interface_table` |
| HW-004 | Not started | SystemRDL source not chosen | — |
| HW-005 | Enforced | `simulation_only` ⇔ `SIM-` revision ⇔ `NOT_APPLICABLE`; positive claims and RELEASED need evidence | `mock-posing-as-board`, `boot-claim-without-evidence`, `sixty-fps-claim`, `released-without-boot`, `not-applicable-on-board` |
| CLI-001 | Enforced | result schema, missing artifact → FAIL | `test_result_contract_rejects_missing_artifact` |
| CLI-002 | Enforced | device deploy/flash → NOT_AVAILABLE; detect is read-only; board claims need board id | `test_device_deploy_never_simulates_success`, `board-pass-without-board`, `evidence-level-inflated` |
| CLI-003 | Enforced | bounded paths, timeouts, scrubbed env, rlimits | `path-escape`, `test_replay_path_cannot_escape_project` |
| API-001 | Host only | capability query; target mapping open | `ConformanceTests`, `accelerator-on-host` |
| API-002 / API-003 | Declared | header has no FPGA registers, no shared memory | review |
| PKG-001 | Enforced | package schema, asset digests, pool ceilings | `asset-digest-mismatch`, `undeclared-asset`, `f133-over-capacity` |
| PKG-002 / PKG-003 | Not started | no signing, no loader | — |
| SEC-001 | Partly | child processes are sandboxed lightly (env, limits, timeouts); no OS sandbox | — |
| SEC-004 | Enforced | `device flash` shows operation, target identity (none), risks and rollback readiness, and never writes; locked partitions refused | `DeviceTests`, `test_flasher_plan_screen_says_write_disabled` |
| SEC-005 | Policy | AGENTS.md | — |
| TST-001 | Enforced | every validator has negative fixtures; `must_differ` controls in test plans | whole suite |
| TST-002 | Declared | traces are labelled host-model; no fps claims | — |
| TST-004 | Pending | needs a second agent or maintainer | handoff |

## Gates

| Gate | State |
|---|---|
| G0 Source hygiene | schema validation, manifest checks, lock, policy: **runs** (`run_tests.py`, CI). No secret scanner or C formatter is wired in yet. |
| G1 Host SDK | CLI and C demo compile, golden and replay tests, negative fixtures, pass checker: **runs**. |
| G2–G5 | **Not established.** No RTL, firmware, board or production process exists in this repository. |
