# Stage Five: continuing work within a visible grant

Open **View → Continuing work**, or **Continue an assignment** in Project Desk. Prepare exact registered calls, inspect the selected copies, source revisions, dependencies and budgets, then **Authorize this exact plan once**. Slate may advance those calls through the existing Agenda without asking again for each covered step. Originals, exports, network access, arbitrary native commands and changes to the grant remain outside this executor.

## First project

1. Create a Project Desk assignment. Keep the original request and intended result. Import a project through Changes and select **Delegate draft preparation in this copy to Slate**.
2. In Continuing work, select the assignment and copy. Choose a text path. Start with **Read selected text**, or **Draft a replacement** and enter the desired text. Preparing steps grants nothing. A generated assignment report, protected parts check or protected local-model patch is another preparation choice.
3. Optionally include applying the frozen draft **to the working copy**. This is part of the authority you are about to review. Leave it off to return only a proposal. A model draft can therefore be applied within a separately owner-authorized work order; an ordinary Ask Slate/Changes model job still never applies its own output.
4. Choose active seconds, step attempts, reserved model tokens, native-worker memory, changed-file count and expiry. Freeze the plan. Review the exact calls, result references, success checks, roots and effects. Authorize that digest once.
5. The Agenda advances one ready step at a time, in order with other Agenda items. The headless coordinator uses the same runner for granted work; legacy suggestions are not silently authorized. The desktop can continue to show progress. Advance one step explicitly in embedded/CLI use, or let the coordinator advance it.
6. A finished order waits for review. Open Changes to inspect its whole proposal or applied working revision, and accept the result only after inspecting it. Publishing to an OS-home original remains the separate Stage Four preview and owner-update action.

## What the grant means

The immutable order binds the original assignment wording/revision, project revision, input bindings, selected working-copy trees, exact call schemas, dependencies, effects, budgets and expiry. Its digest identifies the entire reviewed plan. A separate owner-only grant binds that digest. A plan, model statement, source file or client-supplied effect description creates no authority.

An executor-code or registered-schema change pauses the old order; prepare a new reviewed order under the new implementation. It does not silently reinterpret an old grant.

Each step may read selected UTF-8 working text, run a restricted existing staC query, freeze a text/cell proposal or assignment report, apply a proposal produced by this order to a selected working copy, or invoke a protected parser/check/model profile. Typed references select named fields from completed prerequisites; they do not interpolate commands. Targets, arguments and schemas are checked again after reference resolution. An application must reference an earlier proposal from this order and still be a WORKING proposal with the exact digest.

The order cannot publish originals, accept another source, export a pill/ZIP, change permissions, add an Agenda item, run a shell or reach a network service. Optional external reasoning remains a different explicit authority. A new order starts ungranted, including an instance of a saved procedure.

## Budgets and stopping

Step attempts, maximum active seconds and model-token reservations are committed before work begins. A failed or interrupted attempt keeps its reservation. Successful steps settle measured active time; model calls keep their full context-token reservation rather than trusting an untrusted worker to refund it. Input plus output must fit that context, with no clipping of exact bases. Active time includes validation and worker operation; bounded termination/cleanup can finish afterward. The file budget counts unique copy/path targets actually authorized for application, across the order. Output limits cover retained step result/proposal data; essential control/journal metadata is additional.

Default failure and repeated-result limits are two. Retries are fixed in the frozen plan (zero by default, at most two), limited to read-only steps and delayed with bounded backoff through the Agenda. A failed prerequisite blocks dependent steps. A limit cannot enlarge itself: prepare another reviewed order. Missing/changed input, permission or qualification needs, failed execution, owner pause, interruption and finished proposals have distinct machine-readable reasons beside their journals. The older recurring Agenda behavior is retained; a correction permits a missed item to run once immediately while preserving the next scheduled occurrence, instead of waiting another interval or creating a backlog.

Ordinary bounded record/text operations run in the trusted Kernel. Their application scopes and byte limits are not an OS memory sandbox for the whole Ledger. Native-worker memory is an aggregate cgroup limit, not a claim about the desktop's entire RSS. A step-time check runs before publishing a proposal and between file mutations. Full hashing of a selected tree may take time; close other writers during an authorized update.

## Restart, Stop and recovery

The same Kernel database holds the work plan, grant, counters, steps, event journal and an association with an ordinary Agenda row. Versioned component migrations are additive. There is no new database or scheduling service.

Each step has durable intent before its effect. Draft proposals use a deterministic work/step identity. If a process dies after freezing a proposal, explicit resumption reuses it. Working applications retain Stage Four's journal and one-use proposal/application mapping. If an application completed before the work checkpoint, resumption verifies the completed commit and its actual bytes, then acknowledges it without reapplying. A partial application requires inspection/recovery in Changes before the work order resumes. Unknown later bytes are never overwritten automatically.

Completed prerequisites are not repeated. Source and copy identities are revalidated. The original input snapshot remains in the plan; an exact working-file revision produced by this order has a separate successor link to its commit, so its own authorized edit can continue without pretending the old source bytes are still current. Other source/project/assignment changes pause the order.

Master Stop persists a hold and changes the admission epoch. Every later step, proposal publication, file boundary and protected-worker admission checks it. A quick global Resume cannot silently revive the old order: explicitly inspect and resume that order too. Revocation remains revoked. A restarted coordinator terminates tracked protected units before accepting their old state. An interrupted in-flight step waits for explicit resumption, while a completed effect is reconciled. Complete backups preserve plans, grants, counters, working files and the hold. External masters/model weights remain outside the default complete snapshot.

## Protected workers and actual coverage

The **Worker protection** tab and **This Computer** separate installed tools, the configured profile, real probe outcomes and current qualification. A qualified receipt is bound to the current boot, UID, namespace, cgroup context, relevant program/tool hashes and policy. It expires after 24 hours. Changing the code, tools or boot requires requalification.

The new PARSER, CHECK and MODEL profiles require Linux, bubblewrap, a functioning systemd user manager and delegated cgroup v2 CPU/memory/process controls. Qualification is an explicit native probe, not installation or reconfiguration. Debian users can request prerequisites with `bash INSTALL_DEBIAN.sh --workers` and ensure their normal login has a functioning user manager. The ordinary installer keeps these additional packages optional. Do not run Ledger as root to bypass a failed profile. If a tracked worker needs cleanup, inspect `workers.runs` and use **Stop my protected workers**; global Resume refuses unresolved active units.

The Worker protection tab records qualification in your actual workspace through its coordinator. The `continuing_checks --workers` command is a disposable diagnostic; its temporary receipts do not enable another workspace. CLI/MCP users can invoke `workers.qualify` through their normal authenticated workspace connection. Qualification must match the context that will run the work.

Every launch uses private filesystem, user, PID and network namespaces; drops capabilities; blocks further user namespaces; supplies read-only selected inputs and runtime dependencies; and permits writes only in bounded temporary filesystems. No user HOME, Ledger database, service endpoint, display socket, original-file mount or desktop credentials are supplied. A small trusted gate waits before reading task input. The broker reads actual cgroup `memory.max`, `memory.swap.max`, `pids.max` and `cpu.max` plus service restrictions before admitting the task. Time/output limits and whole-unit termination apply. Control intents and owned launcher identities survive interruption.

The qualification tests forbidden reads/writes, admitted reads and scratch writes, private namespaces, dropped capabilities, no-new-privileges, host TCP/UDP separation, child-process limits, aggregate memory pressure and termination of a descendant that creates its own session. PARSER/CHECK then run a real sample data task. MODEL also launches the pinned native executable inside the boundary. A refused launch is recorded as unavailable/failed, never successful containment. Protected tasks have no ordinary-process fallback.

The protected parser supports bounded text, JSON, CSV/TSV, the Stage Four simple-XLSX profile and GGUF header identification only. Registered checks include JSON/table/text parsing, Python syntax without execution and a parts-table count check (`Part,Need,Have`). These are named checks, not engineering proof or execution of arbitrary imported code. Inputs are limited to eight files, 16 MiB each and 32 MiB combined; source hashes are rechecked after the worker returns.

The protected model path is a separate one-shot use of a registered, owner-held GGUF and the unchanged pinned CPU runtime. Its native server and loopback API stay inside the private network namespace. Only complete exact-base patches to the selected text paths can become a proposal. Up to eight paths/16000 characters, context 512–8192 and output 64–4096 tokens are supported. Actual weights and native model quality/performance remain host acceptance tasks.

Existing manual Brain, engineering tools, viewers and legacy `confine.*` routes remain accessible with their previous declared boundaries. They are explicitly not covered by these new aggregate-cgroup receipts. This stage does not claim a security review of every historical parser or a hostile-kernel defense. The earlier This Computer echo probe is now labelled a launch probe rather than containment verification.

## Reusable staC call procedures

After accepting a completed result, save its plan as an `arc.stac-procedure/1` record. It retains registered operations, effects, prerequisites, checks and origin. This uses existing staC registered-call/query forms; it introduces no shell grammar. Parameters replace declared scalar arguments at typed JSON paths. For example:

```json
{"replacement":{"step":"Draft","path":["operations","0","text"],"type":"string"}}
```

Instantiating supplies values, a current assignment, one selected working copy per saved copy slot, budgets and a new expiry. Fixed direct copy/report-assignment slots are rebound explicitly; query strings and literal base hashes are not automatically rewritten. Use result references or declared parameters for changing values. The result is a new DRAFT requiring its own grant. Procedures do not carry old authority or automatically renew a recurring task.

## Interfaces and checks

All operations are available through Kernel, CLI, MCP and registered-call staC. `work:*`, `procedure:*` and `worker:*` addresses use the same owner checks. Core operations are `work.create/list/get/authorize/pause/resume/revoke/advance/review/read/query`, `procedures.save/list/get/instantiate`, and `workers.status/qualify/stop/inspect/check/draft/runs/run`. All 535 Stage Four operation schemas and all 78 protected SDK, policy and runtime payloads remain unchanged.

```sh
python3 tools/check_release.py --self-test --runtime
python3 -m unittest discover -s tests_stage_five -v
python3 -m workbench.continuing_checks
python3 -m workbench.continuing_checks --host
python3 -m workbench.continuing_checks --workers
python3 -m workbench.continuing_checks --ui
```

The disposable continuation check exits a real child process after working application but before its work checkpoint, then resumes in a new process without replay. A complete restore preserves the plan, grant, counters, result and hold. The separate `--host` check exercises real authenticated coordinator IPC and automatic Agenda advancement without Qt. Worker qualification and real Qt are separate commands and return nonzero if unavailable; the ordinary integrity/self-test gate does not turn those omissions into passes. Read STAGE5_RESULT.json for actual outcomes on the execution host and pending ThinkPad acceptance.

The normal host transport is a private Unix socket. A runtime that cannot create Unix sockets can explicitly select the existing authenticated loopback transport for its disposable IPC check with `ARC_LEDGER_HOST_TRANSPORT=loopback python3 -m workbench.continuing_checks --host`. This does not change the application's default transport or qualify a private native-worker network boundary.

Implementation references: [Debian 13 bubblewrap manual](https://manpages.debian.org/trixie/bubblewrap/bwrap.1.en.html), [systemd-run](https://www.freedesktop.org/software/systemd/man/257/systemd-run.html), [systemd resource control](https://www.freedesktop.org/software/systemd/man/257/systemd.resource-control.html), and [Linux Landlock](https://docs.kernel.org/userspace-api/landlock.html). Landlock remains the legacy optional layer; it is not used as a fallback for these required profiles. Stage Six covers deployment and pill transport/update qualification.
