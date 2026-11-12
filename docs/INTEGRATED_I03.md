# Integrated I03 experiments and explanations

Candidate 5.1.0a3 adds actual Python experiments, selected-board native KiCad checks, and finite support/refutation graphs inside the existing Project Desk problem sheet. It carries the complete I02, I01 and Stage Six program. It introduces no second scheduler, application, model PLAN grammar or generic record-write authority.

## Install and use

Keep the previous program folder and workspace. Extract the complete ZIP into a new program folder. On the Debian desktop, run `bash INSTALL_DEBIAN.sh --math --experiments` as the ordinary desktop user. This adds the pinned optional math/Office/Wasmtime packages and the distribution's KiCad. The selected-board adapter requires KiCad 9 or newer. If prerequisites are already installed, `bash INSTALL_LEDGER.sh --math --experiments` installs the optional Python dependencies. Existing offline and check-only behavior is preserved; include the new pinned Wasmtime wheel in an offline wheel folder. Missing tools do not prevent ordinary Ledger startup.

1. Open Project Desk → Problem sheet and start or reopen Clock Lab. Keep an exact **Concurrent memory case** observation under Calculate.
2. On Investigate → Experiment bench, click **Qualify Python on this host**. This executes boundary, fuel, memory, output and sparse-file probes. A detected package alone never grants qualified status. The receipt expires after 24 hours and is bound to the host, pinned distribution, embedding implementation and actual Wasmtime library.
3. Select the delegated working copy on Sources and results. **Create experiment in selected copy** creates a coordinator-owned Python stub and parameter file through the existing frozen Changes/journal mechanism. It cannot overwrite an earlier experiment. Existing Changes can edit the script; no new permission prompt is introduced for each internal step within this delegated copy.
4. **Freeze and run experiment** pins the exact script, selected inputs, parameters, problem revision, implementation and qualified runtime. The Kernel executes the selected script in WASI CPython. A real result JSON and CSV are created. The default Clock Lab experiment measures 17 MiB and reports that 17 does not fit inside 16 under the declared concurrent-allocation model.
5. Process exit, schema validity, source applicability and mathematical/design conclusions are separate. Failed attempts remain available. A script that exits zero but emits an invalid unit or schema is not admitted as an observation. **Keep generated outputs in this copy** publishes only retained generated output bytes into a new result directory after job completion. The originals remain separate.
6. **Check board and export outline** selects a `.kicad_pcb` from the same owned copy. A private immutable snapshot goes to native KiCad, which first reproduces the good and broken-outline DRC fixtures. The adapter captures actual native DRC JSON and an explicit single-file Edge.Cuts SVG export. The old ARC/R10 adapter and its project bindings are retained.
7. On Why and alternatives, select the saved exact memory comparison and an executed memory result. **Compare memory results** checks that this helper is using the saved concurrent-memory model and the saved MiB quantities. It proposes a finite graph with two alternative reasons. Each requires the explicit concurrency assumption. Advanced callers can propose other bounded graphs using registered operations.
8. Recompute after changing an input. The exact verdict can remain SUPPORTED while the experiment path becomes stale. The UI says **Verdict stayed the same. Reason paths changed.** It retains the earlier snapshot and shows the inactive path. A right-click menu derives actions from the selected retained path: open its owned receipt or preview its tracked consequences.

The lifetime variables remain unknown. This pass does not infer that the three allocations must overlap in every possible schedule. It does not make hardware measurements or approve fabrication.

## Qualified experiment profile

The execution host lacks usable Landlock and a user systemd session; a nested bubblewrap probe also failed. The pre-existing namespace/cgroup worker profiles are unchanged and are not presented as qualified here. I03 adds a distinct `ledger.python-wasi/1` profile. This is actual CPython bytecode execution inside a WebAssembly instance with capability-based WASI filesystem access. It is not Python AST parsing, a Python `eval` filter, or an unconfined native-Python fallback.

The complete CPython 3.13.17 WASI SDK 24 distribution is bundled without trimming its standard library. The archive SHA-256 is `ceec2512d4bf2d2377a4791603e9879329c9b6aa0e7514a19ef827cdefe3b274`. It is Brett Cannon's unofficial CPython WASI build, not a Python Software Foundation binary release. The full license and provenance descriptor are included. The optional native embedding is pinned to Wasmtime 50.0.1. No runtime is silently downloaded by the experiment runner.

| Boundary | Admitted behavior |
| --- | --- |
| Inputs | Exact selected files copied into a fresh private input tree; maximum 16 extra files, 1 MiB each, bounded total. The frozen Python script runs as `/inputs/experiment.py`; parameters are the explicitly frozen object. Extra inputs appear under `/inputs/selected/` with their relative paths. |
| Filesystem | Bundled runtime and selected inputs read-only; only the job's fresh output directory writable. Host home, workspace metadata, database, credentials and original files are not preopened. No inherited host file descriptors or environment. |
| Dependencies | Bundled CPython standard library. No arbitrary native extensions, pip installs, threads, native subprocesses or host shell. Native application adapters remain separate registered tools. |
| Network | No network capabilities or socket descriptors are supplied. TCP, UDP and Unix-socket attempts are tested as denied/unsupported. This is a guest capability boundary, not a claim of host network-namespace isolation. |
| Memory | 128 MiB guest linear memory; actual oversized allocation fails. This is not a cap on the trusted Wasmtime compiler or the embedding process's entire RSS. The module is fixed and hash-pinned. |
| Compute | 20 billion Wasm fuel units, plus a 30-second Kernel wall deadline including startup. Direct `jobs.submit` cannot extend the profile deadline. A smaller fuel probe must reach its loop marker before exhausting fuel. |
| Output | 2 MiB cumulative guest write budget, 128 guest file-open calls, bounded retained diagnostics. Host callbacks meter writes before performing them. File growth without writes, sparse seeks beyond the file-position budget, links and new subdirectories are refused. |
| Cancellation | Existing Kernel process group owns the trusted embedding process; cancel and wall timeout kill it. A stopped run never becomes a completed observation. Pause/resume is refused; prepare a fresh action. |

The WASI forwarding shim preserves the native WASI calling convention and the guest memory when metered callbacks re-enter WASI. The guest cannot call the unmetered forwarding functions directly. The profile has no authority to load arbitrary Wasm or host callbacks. Unsupported packages, versions, missing archives, changed hashes and failed qualification are explicit refusals.

## Observations, failure and context

New actions/results use existing owner-scoped Project Desk records and history. Inputs are retained through the existing content-addressed edit store. Three new job tools—`lab.qualify`, `lab.python`, `lab.board`—use existing Kernel request keys, logs, source-change guards, cancellation, stop control and restart behavior. `jobs.submit` gains one optional `lab` field; all previous fields and required arguments are preserved. No database migration or automatic repair was added.

A Completed lab job means the trusted coordinator finished retaining an attempt. Its `observation.state` can be OBSERVED, OUTPUT_INVALID or EXECUTION_FAILED; actual Python exit/trap is separate. Native board jobs distinguish COMPLETED process execution from NO_REPORTED_VIOLATIONS or VIOLATIONS. A native failure remains a failed Kernel job with retained logs and native attempt files. No stage converts a missing/failed observation into a successful premise.

The result JSON schema admits named exact rational-string quantities with checked units and booleans with unit `1`, plus explicit assumptions. Duplicate keys, floats as exact input facts, unknown units and malformed payloads are refused. Checking this schema does not prove that the script models the intended problem correctly. The connected demonstration deliberately executes a faulty threshold variant; its valid output conflicts with exact arithmetic and remains visible for correction.

Source files, source-copy delegation, problem revision, context and implementation are checked again at execution and result access. Old observations remain historical when those bindings change. Generated output is written under the private job during execution. Publication into a delegated working copy happens after completion, is idempotent for unchanged bytes and refuses conflicting existing bytes. This retains I02's source-change guard behavior.

The selected-board profile binds the actual installed executable/version, known program files, adapter and fixture outputs. It operates on selected embedded board geometry and stored zone fills. It does not refill zones, compare external footprint libraries, perform schematic parity/ERC, or establish physical correctness. KiCad 9.0.9 on this Ubuntu execution host passed the good/bad fixture pair and both SVG exports. The Debian ThinkPad's installed build must qualify independently. This host's temporary package layout is not embedded as a target installation path.

The ENGINEERING copy profile now explicitly admits `.svg`, so the native outline export can be kept in that working copy. CODE and the other narrower profiles retain their filters. Existing traversal, symlink, hidden/credential and original-publication boundaries remain in force. Board publication selects the actual board's DRC report and SVG, excluding qualification fixture reports.

## Finite reasons and Chronicle

The existing staC four-valued evidence representation supplies UNKNOWN, SUPPORTED, REFUTED and CONFLICT. The new calculator accepts at most 64 nodes, 128 acyclic rules, 8 premises per rule and bounded alternative paths/combinations. Rules combine joint positive or negative premises; separate rules retain alternative derivations. Unsupported cycles, dangling references, unsolicited attestation fields and undeclared assumption nodes are refused. Every recomputation currently traverses the whole admitted graph.

Only coordinator-checked comparisons of owned, completed, current math/Python/board receipts can supply observation bits. A model can propose labels, rules and graphs. It cannot submit observation bits, a reviewed flag, a completed job record or physical qualification through this interface. The interpretation of an arbitrary proposed inference is still **PROPOSED_RULES_NOT_APPROVED_FACTS**. Executing a script does not prove its semantics; agreement under one model does not prove physical truth. Each admitted atom retains its actual model/parameters/script and assumption context for review. A different problem revision/context is excluded.

Verdict, source applicability, reason paths and dependency coverage are separate. A stable verdict with changed support is a recorded event. An absent edge is never treated as proof that a change cannot matter: dependencies outside the declared finite graph remain UNKNOWN. Contradictions retain both directions rather than overwriting one result.

The existing Chronicle now also admits an explicitly validated `REASON_RECOMPUTATION` event. Existing read-event hashes and invariants remain intact. Full reason snapshots remain in the shared record store, referenced by their digests from the existing hash chain. The chain is local tamper evidence, not independent author identity or source truth. Saving a reason record and appending Chronicle use separate local transactions; a failed append returns PENDING without erasing the result, and `reasons.record` retries the append idempotently.

The GUI exposes the retained snapshot and a current preview. Reopening performs read-only dependency recomputation and does not resume execution. Older rule definitions/results remain in version history. The dynamic right-click actions operate on retained selected records, an incremental step toward the planned Fluxbox command-menu interaction model.

## Validation and remaining work

Run `python tools/check_release.py --self-test --native --ui --runtime` with the optional dependencies installed. The wrapper preserves the complete earlier check chain, including native Calc/Writer, source copies, Changes recovery, continuing work, exchange, signed updates, database concurrency and prior Qt views. It adds the connected Python/board/reason fixture, real cancellation, the real 30-second timeout, and actual Qt experiment/reason interactions. `python -m workbench.lab_checks --keep NEW_FOLDER --output REPORT.json` retains a fresh disposable connected exercise. It never launches a model.

The included observed examples and report are synthetic execution-host evidence, outside the input fixture. They are not model-visible oracle inputs or portable live receipts for a new workspace. The original I01 input manifest and previous deliverables are retained.

I03 measures implemented, observed tool mechanics. I04 adds the adaptive local-model action/observation loop, per-session working-copy grants and its compatibility profile. I05 adds methods/transfer and visible application sessions. I06 measures unseen tasks with the real local model on the target ThinkPad. No live model was invoked in I03 and no increase in model intelligence is claimed. Three candidate passes out of six is 50% of delivery milestones, not 50% of all validation or elapsed effort.

Primary implementation references: [Wasmtime Python API](https://bytecodealliance.github.io/wasmtime-py/), [CPython WASI distribution](https://github.com/brettcannon/cpython-wasi-build/releases/tag/v3.13.17), [CPython WASI platform documentation](https://github.com/python/cpython/blob/main/Platforms/WASI/README.md), and [KiCad 9 CLI](https://docs.kicad.org/9.0/en/cli/cli.html). Native tool help was checked again before using the explicit SVG export mode.
