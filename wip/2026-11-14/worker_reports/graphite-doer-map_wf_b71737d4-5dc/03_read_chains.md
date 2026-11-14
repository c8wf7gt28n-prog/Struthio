{
 "summary": "Most of the design already exists, in three layers that are not yet joined. I tried nearly everything below in the throwaway After Hours 07 workspace; items I only read are marked.\n\n**The tree moved while I read.** The task named commit 1d45b9c; the same session has since committed a9a1b4e and bf42691 on the branch, and `workbench/field_page.py` has uncommitted edits. Those commits build the first part of the doer. Line numbers for `shell2.py`, `field_do.py` and `field_page.py` are as of bf42691; every other file is unchanged since 1d45b9c.\n\n**1. staC is two read-only dialects, routed by `stac_bridge.route_program` (stac_bridge.py:22).**\n- **Start words:** `library desk package map source packet investigation inquiries inquiry algorithms atlas math use` go to `stac.run {program}`.\n- **Everything else** goes to `language.run {text}`: one source plus at most seven transforms. The source is a read-scope operation with optional JSON arguments, or `@kind:id` (rewritten to `ledger.address.read`, stacy_language.py:38). Aliases: `jobs`, `models`, `activity`.\n- **Verbs** (typed_pipeline.py:44-106):\n  - `where F=V`, or `F over|under|at least|at most|has|is not V`; `V` may be `@OtherField`.\n  - `take N`, `keep rows 1,3`, `select a,b`, `sort [-]f`, `count`.\n  - `group f` followed by `count`, `sum`, `avg`, `min` or `max`.\n  - `add Name = arithmetic`.\n  - `join` / `missing @addr [lens] on F`.\n  - Lenses: `sheet NAME`, `rows`, `facts`, `layers`, `lines`, `headings`, `texts`, `pick path`.\n- **No variables, no parameters, no assignment, no line feeding another line.** `$name` and `{name}` are literals. The only composition is join/missing; the joined side cannot join again (stacy_language.py:79). A start-word program can be a pipeline source: `stac.run {\"program\":\"desk\"} | pick result | \u2026`.\n- **`explain LINE`** goes to `stac.inspect`: it shows the planned reads and transforms and executes nothing.\n- **It cannot write.** The refusal reads \"A pipeline source must be a registered read-only Kernel operation\" (stacy_language.py:67). `> < ; $( ${` and backtick give \"Shell syntax and command substitution are not part of Stacy language\".\n\n**2. Operation lines.** `/op {json}` or `/op name=value` runs through `shell2.to_console(host,'kernel',line)` (shell2.py:988) into `Console.run_kernel` (console_qt.py:478).\n- Read and execute scope run on the first Enter; `/files.write` wrote at once with no confirmation.\n- Approve scope prints \"<op> acts with your approval. Press Enter again\u2026\", leaves the line in the box, and runs on the second Enter only if the text is unchanged.\n- A refusal prints \"refused <Code> <message>\".\n- The journal holds operation, state, origin and correlation id only: no arguments, no results.\n- No single function has the new design's rule (reads free, every write waits). `field_page.take` (line 214) comes closest, but it goes by a hand-set `Step.kind`, not by the Kernel's scope.\n\n**3. What a chain is today.**\n- **Chain menu and tray:** one staC line built link by link. `ChainTray` stages, previews, runs and saves a CSV plus a `graphite.chain-result/1` receipt (program, source digests, seed) under Files/Slate/Chains.\n- **Kept chains:** lines `[chain] (Name) {staC} then console|sheet|watch|agenda` in the plain text file `~/Concern/Ledger menu`. No Kernel operation.\n- **Method Press:** one hard-coded shape, the stock shortage. It is a `[stock]` line in the same file; replay regenerates the staC from the selected rows, checks unit and columns, and saves receipts under Slate/Chains/Methods/<id>. `methods.*` (checked_methods.py) is a different thing: one additive-capacity maths profile.\n- **Agenda:** one program per item, run with read-only authority. `when.after` sequences items and `watch` repeats. A finished item cannot be queued again.\n- **Instruction matrix:** program text, shape, outcome and reason for every staC run. Read back with `matrix.examples {text}`, `matrix.patterns`, `matrix.list`.\n\n**4. A record that holds ordered steps, exact calls, what each returned, checks, and replays on new material does exist: `work.*` plus `procedures.*` (continuing_work.py, \"Night Shift\").** I ran it end to end: a two-step order (`work.read`, then `changes.propose` using a `$step` reference) was authorized, advanced, accepted, saved as a procedure with one parameter, and instantiated on a different working copy with a different value. Its limits: eight allowed step operations, all on delegated working copies; it needs a project and an assignment; check literals cannot be parameters. The second fit is an investigation (`investigation.step` / `check` / `continue`): ordered staC steps with input digests, plus checks with oracles. It holds reads only and has no parameters.\n\n**5. Putting a write in front of the owner.**\n- `SlateFace.stage(title, step, done)` (shell2.py:1667): one line, one Run, then `done(ok, result)`.\n- `SlateFace.say_plan(plan, done)` (shell2.py:1727): a list run in order on one Run, stopping at the first refusal, then `done([(line, ok, result-or-message)])`.\n- Older routes: `proposal_card` (shell2.py:1874), `files.propose` then `files.decide`, `changes.propose` then `changes.apply`, and `inspect_in_line(operation_line(op,args))` for the second Enter.\n\n**6. The seam** is in the advice field.",
 "operations": [
  {
   "name": "language.run",
   "arguments": "{\"text\": staC line (1..8192 chars), \"expected_seed\"?: seed id}",
   "scope": "read",
   "effect": "Runs one typed pipeline: one read-scope source (operation + JSON args, or @kind:id) and up to 7 transforms. Returns {schema:'arc.stacy-pipeline-result/1', plan:{call, transforms, plan_id, seed_id, \u2026}, rows:[\u2026], execution:'REGISTERED_READ_ONLY_KERNEL_CALL', model_calls:0}. At most 200 output rows; source at most 2000 rows / 512 KiB. Refuses any source that is not read scope, any language.* source and stac.inspect. Refuses everything when the seed is stale.",
   "evidence": "Tried (p2, p3, p4): about 30 lines including join, missing, add, group, @Field compare, and 20 refusals. Code: workbench/stacy_language.py:107-127, sdk/cli/arc1cli/typed_pipeline.py:14-26, 44-106, 212-273."
  },
  {
   "name": "language.parse",
   "arguments": "{\"text\": staC line}",
   "scope": "read",
   "effect": "Returns the plan without reading rows (call, transforms, plan_id, seed_id, permission 'read'). The chain tray uses it to bind a preview to a seed.",
   "evidence": "Tried (p3). Code: workbench/stacy_language.py:111."
  },
  {
   "name": "stac.run",
   "arguments": "{\"program\": text beginning with a start word}",
   "scope": "read",
   "effect": "Runs the start-word dialects (desk, package, map, source, packet, investigation <job> | inspect/gaps/why, inquiries, inquiry, algorithms, atlas, math, library, use PROJECT@REV \u2026). Returns {schema:'arc.stac-kernel-result/1', result, effects:['read'], \u2026}, or state 'BLOCKED' with a reason. Refuses a language.run pipeline with \"Select a context: use ARC1@R10 | part U45\". Not seed-bound.",
   "evidence": "Tried (p3, p13): desk, atlas, algorithms and inquiries ran; a pipeline was refused. Code: workbench/stac_bridge.py:18-30, 64-124. That it is not seed-bound is read only."
  },
  {
   "name": "stac.inspect",
   "arguments": "{\"program\": staC line without the word explain}",
   "scope": "read",
   "effect": "What typing 'explain LINE' does: returns {schema:'arc.stac-inspection/1', operation, steps:[{command:'read', operation, arguments}, {command: transform kind, arguments}\u2026], required_scope:'read', effects, source_binding, executed:false}. 'explain explain X' is refused.",
   "evidence": "Tried (p3, p4): Ctrl+Enter on an explain line printed the numbered plan in the working area. Code: workbench/stac_bridge.py:127-160, workbench/console_qt.py:134-165, 453-467."
  },
  {
   "name": "stac.observe / stac.history / stac.export",
   "arguments": "stac.observe {\"program\"}; stac.history {}; stac.export {\"program\", \"destination\"}",
   "scope": "execute / read / approve",
   "effect": "observe stores {id, created, program, result (full), result_sha256} in memory and history lists them: a kept 'line plus what it returned' for a single start-word program. export writes the result as JSON to a fresh path. All three refuse language.run pipelines.",
   "evidence": "Tried (p3, p13). Code: workbench/stac_bridge.py:170-181."
  },
  {
   "name": "agenda.add",
   "arguments": "{\"title\" (required), \"program\"?: staC, \"investigation\"?: id, \"nice\"?: now|normal|background, \"when\"?: {at, every_hours, after: agenda id, idle, timezone}, \"rounds\"?: 1..20, \"watch\"?: bool, \"copy\"?: id}",
   "scope": "execute",
   "effect": "Keeps one staC program (or an investigation, or a words-only question for the model) as an Agenda item in state NEXT or LATER. watch:true makes it repeat every 6 hours and report only changed rows. when.after makes it wait until another item is DONE.",
   "evidence": "Tried (p7): two items chained with when.after ran in order; a watch reported \"Changed: 1 new (Part R1).\" Code: workbench/agenda.py:46-50, 198-224."
  },
  {
   "name": "agenda.run_next",
   "arguments": "{\"idle\"?: bool}",
   "scope": "execute",
   "effect": "Runs the first ready item once with a principal cut down to read scope. The program goes through route_program, so only staC. Returns {ran, state, progress, authority:['read'], suggested}. The outcome text is stored on the item and shown by agenda.view under done. A write or a '/op' line as program ends FAILED. A DONE item cannot be queued again: agenda.resume and agenda.accept answer \"AGENDA_NOT_NEXT: it is done\". In the window a timer calls this when something is due.",
   "evidence": "Tried (p7). Code: workbench/agenda.py:258-349 (bounded principal at 307), workbench/agenda_qt.py:262-281. The timer is read only: the harness stops it."
  },
  {
   "name": "matrix.examples / matrix.patterns / matrix.list / matrix.mark / matrix.promote",
   "arguments": "matrix.examples {\"text\"}; matrix.patterns {\"limit\"?}; matrix.list {\"outcome\"?, \"query\"?, \"limit\"?}; matrix.mark {\"id\", \"mark\": GOOD|BAD|NONE, \"note\"?}; matrix.promote {\"shape\", \"title\"}",
   "scope": "read / read / read / approve / execute",
   "effect": "Every language.run, stac.run, stac.observe and ledger.address.read is recorded automatically as one row: program, shape (ids, strings and numbers replaced by <ID> <TEXT> <N>), operation, outcome SUCCESS|EMPTY|BLOCKED|FAILED, reason, mark, intent (only when a model proposed it). examples returns {worked:[{instruction, program}], failed:[\u2026]} by word overlap; the writing line shows these as WORKED BEFORE and the model prompt receives them. promote turns a shape into a proposed lesson (memory.lessons).",
   "evidence": "Tried (p3, p10). Code: workbench/instruction_matrix.py:28-46, 73-78, 106-137, 180-217; workbench/shell2.py:919-925."
  },
  {
   "name": "work.create",
   "arguments": "{\"assignment\": id, \"copies\": [1..4 working copy ids], \"steps\": [{\"key\", \"operation\", \"arguments\", \"after\": [keys], \"seconds\"?, \"retries\"?, \"require\"?: [{\"path\": [..], \"equals\": value}]}], \"budget\": {seconds, steps, tokens, memory_mb, output_bytes, files}, \"expires\": unix time within 30 days, \"title\"}",
   "scope": "execute",
   "effect": "Freezes an ordered plan as a DRAFT work order with an Agenda row; nothing runs. Step operation must be one of work.read, work.query, changes.propose, changes.report, changes.apply, workers.inspect, workers.check, workers.draft. An argument may be {\"$step\": key, \"path\": [..]} to take a field from an earlier step's result. Copies must be delegated to Graphite. A work.query may only read work.read, projects.get or assignments.get.",
   "evidence": "Tried (p6, p11), with these refusals seen: files.write as a step gives \"Invalid choice: params.steps[].operation\"; a documents.list query gives \"Continuing queries read selected working text or this assignment/project\"; an undelegated copy gives \"Delegate each selected working copy to Graphite\u2026\". Code: workbench/continuing_work.py:22-58, 172-236."
  },
  {
   "name": "work.authorize / work.advance / work.get / work.review / work.resume",
   "arguments": "work.authorize {\"id\", \"expected_digest\": content_digest from work.create or work.get}; work.advance {\"id\"}; work.get {\"id\"}; work.review {\"id\", \"decision\": ACCEPT|CHANGES_REQUESTED|DEFER, \"note\"}; work.resume {\"id\"}",
   "scope": "approve / execute / read / approve / approve",
   "effect": "authorize is the owner's one grant for the exact frozen plan. advance runs one step per call; a changes.apply inside the plan runs under the grant with no further approval. Each step's resolved arguments, full result, result_digest and attempts are stored and returned by work.get under steps, with events. A step's require list is checked on the actual result: a mismatch gives state WAITING, reason SUCCESS_CHECK_FAILED, and the order can then be neither accepted nor resumed. When all steps are DONE the state is REVIEW.",
   "evidence": "Tried (p6, p11): Read then Draft ended in REVIEW; a four-step order with a wrong expected text ended WAITING SUCCESS_CHECK_FAILED after the apply had already changed the working copy. Code: workbench/continuing_work.py:371-377, 433-539, 693-722."
  },
  {
   "name": "procedures.save / procedures.list / procedures.get / procedures.instantiate",
   "arguments": "procedures.save {\"work\": accepted work id, \"title\", \"parameters\": {name: {\"step\": key, \"path\": [argument path], \"type\": string|integer|number|boolean}}}; procedures.instantiate {\"id\", \"assignment\", \"copies\": [one per saved slot], \"values\": {name: value}, \"budget\", \"expires\", \"title\"}",
   "scope": "approve / read / read / execute",
   "effect": "save keeps an ACCEPTED order's steps as an 'arc.stac-procedure/1' record (steps, parameters, operations, effects, copy_slots). instantiate substitutes the values, remaps copies and assignment, and creates a new DRAFT order that needs its own grant. Parameters replace whole scalar step arguments only: not require, not the operation, not text inside a staC line.",
   "evidence": "Tried (p6): saved with parameter replacement = Draft.operations.0.text; instantiated on the Lamp copy with \"shade: black\"; after authorize and two advances the proposal diff read \"-shade: green +shade: black\". Refusals seen: \"Only an owner-accepted completed order becomes a reusable procedure\", \"Supply exactly the declared parameters\". Code: workbench/continuing_work.py:611-650, 670-688."
  },
  {
   "name": "imports.preview / imports.accept / projects.create / assignments.create",
   "arguments": "imports.preview {\"source\": folder path, \"profile\": \"CODE\"}; imports.accept {\"id\", \"expected_digest\", \"for_slate\": true}; projects.create {\"title\", \"intent\"}; assignments.create {\"project\", \"request\", \"interpretation\", \"intended_output\", \"success\": [..], \"stop\": [..], \"inputs\": [addresses]}",
   "scope": "approve / approve / execute / execute",
   "effect": "What a work order needs first: a working copy delegated to Graphite (for_slate true), a project and an assignment. inputs may be empty.",
   "evidence": "Tried (p6, p11). Argument shapes taken from tests_integrated/test_continuing_work.py:45-63 (read, not run)."
  },
  {
   "name": "investigation.create / add_source / step / claim / check / continue / refresh / review / sheet",
   "arguments": "create {\"question\", \"objective\"?, \"budget\"?: {max_steps, max_seconds, effects: read|execute}}; add_source {\"id\", \"address\"}; step {\"id\", \"program\": staC, \"purpose\"}; claim {\"id\", \"text\", \"role\": FINDING|CANDIDATE|QUESTION}; check {\"claim\", \"program\": staC, \"oracle\": words, \"expect\": NONEMPTY|CONTAINS|NOT_CONTAINS|COUNT_AT_LEAST, \"value\"?, \"refutes_on_fail\"?}; continue {\"id\"}; refresh {\"id\"}; review {\"claim\", \"decision\": ACCEPT_CHANGE|RETIRE}; sheet {\"id\"}",
   "scope": "execute (review: approve; sheet: read)",
   "effect": "step runs one staC line and records seq, purpose, program, input digests, outcome, summary (600 chars) and result digest; a repeat on unchanged inputs is marked duplicate_of. check binds a staC line and an oracle to a claim. continue runs only checks that are NOT_RUN, FAILED or STALE; when all hold the state is CRITERIA_SATISFIED. refresh re-reads registered sources and marks dependent steps STALE and claims NEEDS_REVIEW. Steps accept staC only.",
   "evidence": "Tried (p10): two steps and a COUNT_AT_LEAST 2 check gave CRITERIA_SATISFIED; after the file changed, refresh then review ACCEPT_CHANGE then continue gave CHECK_FAILED. A '/files.write' step failed with \"Expected a registered operation name\". Code: workbench/investigations.py:51-71, 108-120, 156-191, 294-352."
  },
  {
   "name": "files.propose / files.proposals / files.decide",
   "arguments": "files.propose {\"path\", \"text\", \"why\"}; files.proposals {}; files.decide {\"id\", \"apply\": bool}",
   "scope": "execute / read / approve",
   "effect": "A whole-file write that waits. It appears in agenda.view under waiting as kind 'proposal' (\"Change <path>\", \"Graphite proposed it: <why>\"). decide applies it (refused if the file changed since) or declines it; returns {state:'APPLIED', path, kept_version}.",
   "evidence": "Tried (p7, p7b). Code: workbench/files_service.py:536-559."
  },
  {
   "name": "changes.propose / changes.review / changes.apply",
   "arguments": "changes.propose {\"copy\", \"operations\": [{\"op\": WRITE|PATCH|CREATE|DELETE|RENAME|CELLS, \"path\", \"base_sha256\"?, \"text\"?, \u2026}], \"note\"?, \"origin\"?}; changes.review {\"id\"}; changes.apply {\"id\", \"expected_digest\"}",
   "scope": "execute / read / approve",
   "effect": "A frozen multi-file proposal on a working copy, with diff and content_digest. review shows it. apply needs the exact digest and returns a commit; changes.undo reverses it.",
   "evidence": "propose and review tried inside work orders (p6); apply tried as a work step (p11). Code: workbench/change_sets.py:30-50."
  },
  {
   "name": "field_do.call(line) [Python, new at a9a1b4e]",
   "arguments": "line: a staC line or '/operation {json}'",
   "scope": "function, no UI",
   "effect": "Returns (operation, arguments) for either kind of line. Limits: JSON arguments only ('/op name=value' raises JSONDecodeError); 'explain \u2026' is not recognised; an unknown operation name is passed through for the Kernel to refuse.",
   "evidence": "Tried (p8). Code: workbench/field_do.py:43-49."
  },
  {
   "name": "field_do.steps_for(kernel, principal, obj, field) / field_do.sweep / field_do.settling [Python, new]",
   "arguments": "obj: a Field object; returns [Step(words, kind 'read'|'write', line, why, scope, settles)]",
   "scope": "function, no UI",
   "effect": "The program enumerating next steps from the records, with no model: per kind (calculation, sheet, finding, question, source, condition, job, document), each an exact staC or operation line. sweep returns (waiting, lines) for the whole desk; settling picks the no-decision writes.",
   "evidence": "Tried (p8): printed the steps for all 14 objects of the worked case; D and digit keys worked. Code: workbench/field_do.py:24-31, 181-235 at bf42691."
  },
  {
   "name": "SlateFace.stage(title, step, done=None) / run_staged [Python, new]",
   "arguments": "step: field_do.Step; done(ok, result) callback",
   "scope": "UI function (w.shell2.face)",
   "effect": "Puts one line in Talk with its why, the exact line, a Run button and an 'in the line' link. Run dispatches once with the owner's full scopes, whatever the scope of the operation. The card then says \"Done\u2026\" or \"It was refused, and nothing was changed: <message>\", the button says Ran or Refused, and done(ok, result) receives the Kernel result.",
   "evidence": "Tried (p8): files.write staged, ran, callback received the result dict; a second click did nothing; a refused files.decide gave Refused and ok False. Code: workbench/shell2.py:1667-1704."
  },
  {
   "name": "SlateFace.say_plan(plan, done=None) / run_plan [Python, new at bf42691]",
   "arguments": "plan: [(object with .title, Step)]; done(results)",
   "scope": "UI function",
   "effect": "Several lines shown numbered with one Run. They dispatch in order and stop at the first refusal. card.results = [(line, ok, result or error message)] and done(results) is called. Held in memory only.",
   "evidence": "Tried (p12): a write, a staC read and an agenda.add gave \"Ran 3 of 3\" with three results; a plan with a refused second step gave \"Ran 1 of 3\" and the third never ran. Code: workbench/shell2.py:1727-1765."
  },
  {
   "name": "SlateFace.proposal_card(action, model_id, request, chain, seed_id) / execute [Python]",
   "arguments": "action: {\"operation\", \"arguments\"}",
   "scope": "UI function",
   "effect": "The older PROPOSED STAC card (REVIEW ACTION for programs.*): Run and Edit. Run calls execute(), which dispatches with the owner's full scopes in one click, approve-scope operations included, and answers only as a Talk bubble with Right/Wrong marks; nothing is returned to the caller. Edit puts 'op {json}' in the line without the leading slash. A documents.edit for the open page is applied at once when chain is given.",
   "evidence": "Tried (p7): files.write, language.run, agenda.add and files.decide cards. Code: workbench/shell2.py:1874-1910, 2009-2026. The model-fed path at 1840-1872 is read only."
  },
  {
   "name": "shell2.to_console(host, page, text) / Console.run_kernel / Console.run_stac [Python]",
   "arguments": "page: 'stac' | 'kernel' | 'find' | 'shell'; text: the line",
   "scope": "UI function",
   "effect": "The one function behind the writing strip for both kinds of line. 'kernel' accepts both argument forms, plus help NAME, ops WORD and history. Approve scope asks for a second Enter and puts the line back in the box. 'stac' runs through route_program with explain allowed, and the table gets links: save as a sheet, watch it, add to the Agenda, again.",
   "evidence": "Tried (p4, p11). Code: workbench/shell2.py:988-998, workbench/console_qt.py:67-81, 453-507."
  },
  {
   "name": "context_menu.operation_line(op, args) / inspect_in_line(host, text) / run_stac(host, program) / dispatch(host, op, args) [Python]",
   "arguments": "as named",
   "scope": "UI function",
   "effect": "operation_line builds '/op {json}'. inspect_in_line puts a line in the strip and runs nothing. run_stac runs through the working area and raises Refused(\"Not run: <reason> \u00b7 the working area shows the refusal\"). dispatch is the plain Kernel call with the owner's principal.",
   "evidence": "Tried (p7b, p7c, p11). Code: workbench/context_menu.py:142-146, 221-248, 282-283."
  },
  {
   "name": "chain_workbench_qt.stage(host, program) -> ChainTray: preview(), run_chain(), save_sheet(), keep() [Python]",
   "arguments": "program: staC pipeline",
   "scope": "UI function (host.chain_tray)",
   "effect": "The retained chain preview. stage shows the links as chips and runs nothing. preview runs language.run bound to the seed and fingerprints every source before and after. save_sheet writes Slate/Chains/chain-<uuid>.csv and a .json receipt {schema:'graphite.chain-result/1', program, sources:[{operation, arguments, digest}], seed, rows, output, created}. A source changed after preview gives \"Source changed \u00b7 preview again before running or saving.\" keep() writes a [chain] line, despite the label 'Keep as a method\u2026'.",
   "evidence": "Tried (p9). Code: workbench/chain_workbench_qt.py:42-60, 165-201, 227-255, 282-345, 357-358."
  },
  {
   "name": "chain_menu.keep(host, program, then_word) / parse_menu(text) / then(host, program, how) / stock_methods() [Python]",
   "arguments": "then_word and how: console | sheet | watch | agenda",
   "scope": "UI function plus the plain file ~/Concern/Ledger menu",
   "effect": "keep asks for a name in a dialog and appends '[chain] (Name) {staC} then word'. parse_menu reads the file into a tree; chains appear on the root right-click menu. then runs a chain to its ending. A kept line is offered only if it parses as staC.",
   "evidence": "Tried (p9) with the name dialog patched. Code: workbench/chain_menu.py:269-280, 331-391, 416-455."
  },
  {
   "name": "Worksheet.shortage_method(binding, fields, expected=None, method=None) [Python: Method Press]",
   "arguments": "binding: (sheet name or None, [row indexes]); fields: (Part, Required, Available, Unit) column names",
   "scope": "UI function (sheet_workbench_qt.Worksheet)",
   "effect": "With expected None it keeps a '[stock] (Name) {json}' line holding {schema:'graphite.stock-shortage-method/1', id, unit, columns, source:{path, sha256, sheet, rows}}. With a method it regenerates the staC for the current selection, previews it, and save_sheet writes the CSV and a receipt carrying method, plan_id and output_sha256 under Slate/Chains/Methods/<id>/.",
   "evidence": "Tried (p9): kept from stock.csv rows 1 and 3; replayed on stock2.csv, which gave 2 rows and \"new source revision\"; rows in another unit were refused. Code: workbench/sheet_workbench_qt.py:542-560, 612-631, 655-729."
  },
  {
   "name": "investigations.record_step(kernel, investigation, operation, arguments, principal, purpose, outcome, summary, result, inputs) [Python]",
   "arguments": "as named",
   "scope": "internal function",
   "effect": "Records a step that already ran as an inv_steps row with program = {operation, arguments} as JSON. The agent loop uses it. Nothing replays it.",
   "evidence": "Read only: workbench/investigations.py:194-219, workbench/agent_loop.py:469."
  }
 ],
 "recipes": [
  {
   "goal": "Run a staC line exactly as the writing strip does, and read the refusal when it is not a read",
   "steps": "From code: `from workbench.stac_bridge import route_program, blocked_reason`; `op, args = route_program(line, allow_inspection=True)`; `r = k.dispatch(op, args, p)`. On `r['ok']`, rows are in `r['result']['rows']` (language.run) or the record is in `r['result']` (stac.run; check `blocked_reason`). From the UI: `box = w.type_bar.box; box.setText(line); QTest.keyClick(box, Qt.Key_Return, Qt.ControlModifier)`. Plain Enter on the same text gives it to Stacy as a question instead.",
   "tried": true,
   "result": "Six varied lines ran on the worked case: an @document read; sort/select/take; group/count over the investigation's checks; join + add + sum (13.7); missing; a @Field compare. Ctrl+Enter printed the table and \"3 rows \u00b7 0.08 s \u00b7 read only \u00b7 save as a sheet \u00b7 watch it \u00b7 add to the Agenda \u00b7 again\". `files.write {\u2026}` typed as staC printed \"refused A pipeline source must be a registered read-only Kernel operation\" and was journaled as language.run DENIED_OR_FAILED."
  },
  {
   "goal": "Run an operation line from the strip with the right confirmation for its scope",
   "steps": "`from workbench.shell2 import to_console`; `to_console(w, 'kernel', '/files.write {\"path\":\"notes/a.txt\",\"text\":\"hello\"}')`. Or, to let the owner read it first: `from workbench.context_menu import operation_line, inspect_in_line`; `inspect_in_line(w, operation_line('files.decide', {'id': ID, 'apply': True}))`, then Enter, then Enter again.",
   "tried": true,
   "result": "Read and execute scope ran on the first Enter (files.write and files.trash wrote at once). Approve scope (agenda.cancel, files.decide, files.restore) printed \"<op> acts with your approval. Press Enter again to run it as written; change it or press Esc to leave it.\", left '/line' in the box, and ran on the second Enter (\"state APPLIED\"). Unknown operation: \"refused no operation named \u2026\". Schema failure: \"refused ValueError Invalid length: params.id\". Journal: two events per call, REQUEST_RECEIVED then REQUEST_COMPLETED or DENIED_OR_FAILED, with operation, origin and correlation_id and no arguments; `/documents.list` left no journal line."
  },
  {
   "goal": "Stage one write for a one-click Run and get its result back in code",
   "steps": "`from workbench.field_do import Step, op`; `step = Step('Write a note', 'write', op('files.write', path='notes/staged.txt', text='\u2026'), 'a new file in Files/notes', 'execute')`; `card = w.shell2.face.stage('a title', step, done=lambda ok, result: \u2026)`. The owner clicks Run (in a script, `card.run.click()`).",
   "tried": true,
   "result": "The card showed the words, the why, the exact line, Run and 'in the line'. After Run the button said 'Ran', the card said 'Done.', `card.ran` was True and the callback received the files.write result dict. A second click did nothing. A refused line gave 'Refused', \"It was refused, and nothing was changed: FILES_PROPOSAL_NOT_FOUND\" and ok False. A line in name=value form raised JSONDecodeError inside the click and left the card untouched."
  },
  {
   "goal": "Run several lines in order on one Run and collect what each returned",
   "steps": "`plan = [(obj, Step(words, kind, line, why, scope)), \u2026]`, where obj only needs `.title`; `card = w.shell2.face.say_plan(plan, done=lambda results: \u2026)`; Run.",
   "tried": true,
   "result": "Three lines (files.write, a staC read, agenda.add) gave 'Ran 3 of 3' and results = [(line, True, result dict) \u00d73]; each row on the card gained '\u00b7 done'. With a refused second step: 'Ran 1 of 3', results ended with (line, False, 'FILES_PROPOSAL_NOT_FOUND'), and the third line never ran. Nothing is persisted."
  },
  {
   "goal": "Keep a two-step sequence with what each step returned, and run it again on other material (the closest existing fit)",
   "steps": "1. `imports.preview {source, profile:'CODE'}`, then `imports.accept {id, expected_digest, for_slate:true}`, for each of two folders.\n2. `projects.create {title, intent}`; `assignments.create {project, request, interpretation, intended_output, success, stop, inputs}`.\n3. `work.create` with steps Read = `work.read {copy, path:'note.md'}` and Draft = `changes.propose {copy, operations:[{op:'WRITE', path:'note.md', base_sha256:{'$step':'Read','path':['sha256']}, text:'hands: black\\n'}]}`, after ['Read'], require [{path:['target'], equals:'WORKING'}].\n4. `work.authorize {id, expected_digest}`; `work.advance {id}` twice; `work.review {id, decision:'ACCEPT', note}`.\n5. `procedures.save {work, title, parameters:{replacement:{step:'Draft', path:['operations','0','text'], type:'string'}}}`.\n6. `procedures.instantiate {id, assignment, copies:[other copy], values:{replacement:'shade: black\\n'}, budget, expires, title}`; then authorize and advance twice.",
   "tried": true,
   "result": "Worked end to end. First order: DRAFT, READY, then REVIEW with reason FINISHED_PROPOSAL; `work.get` held each step's resolved arguments and full result (Read: text 'hands: blue', sha256; Draft: proposal id and content_digest). The procedure was saved as 'arc.stac-procedure/1'. The instance on the Lamp copy read 'shade: green' and froze a proposal whose diff was '-shade: green / +shade: black'. Originals were untouched. Readable in staC: `work.get {\"id\":\u2026} | pick steps | select key,state,attempts,result_digest` and `procedures.get {\"id\":\u2026} | pick steps | select key,operation,after`."
  },
  {
   "goal": "A job that is done when its checks pass, with the steps on record, and run again after the material changes",
   "steps": "`investigation.create {question, budget:{max_steps:10, max_seconds:60, effects:'read'}}`; `investigation.add_source {id, address:'files:stock.csv'}`; `investigation.step {id, program, purpose}` twice; `investigation.claim {id, text, role:'FINDING'}`; `investigation.check {claim, program, oracle, expect:'COUNT_AT_LEAST', value:'2'}`; `investigation.continue {id}`. After the file changes: `investigation.refresh {id}`, `investigation.review {claim, decision:'ACCEPT_CHANGE'}`, `investigation.continue {id}`.",
   "tried": true,
   "result": "continue ran the check: PASSED, state CRITERIA_SATISFIED, claim SUPPORTED. The sheet's 'attempted' listed both steps in order with exact program, input digest, outcome and summary. After the file changed, refresh reported changed ['files:stock.csv'], the check went STALE and the claim NEEDS_REVIEW; continue ran nothing until the review; then the check ran again and gave CHECK_FAILED. A second continue on unchanged inputs ran nothing. The plain steps are never rerun, only the checks."
  },
  {
   "goal": "Keep a staC chain with a source receipt, and keep it on the menu",
   "steps": "`from workbench import chain_workbench_qt, chain_menu`; `t = chain_workbench_qt.stage(w, program)`; `t.preview()`; `t.save_sheet(open_folder=False)`; `chain_menu.keep(w, program, 'sheet')` (asks for a name); later `chain_menu.then(w, program, 'sheet')` or choose it from the root right-click menu.",
   "tried": true,
   "result": "preview said \"2 rows returned \u00b7 current sources recorded\". save_sheet wrote Slate/Chains/chain-<uuid>.csv and the .json receipt with program, source digest and seed. Changing the source after the preview blocked the save. The menu file gained `[chain] (Short parts) {\u2026} then sheet` and the root menu listed it. The file accepts duplicate names."
  },
  {
   "goal": "Method Press: keep a shortage method from selected rows and replay it on another file",
   "steps": "Open a CSV with Part, Required, Available, Unit columns (`w.open_in_viewer(path)`); select rows; right-click, Method Press, Keep shortage method\u2026 (`ws.shortage_method(binding, fields)`). On another sheet select rows and choose the kept name (`ws.shortage_method(binding, fields, unit, method=method)`); then [>] Run chain (`ws.tray.save_sheet(open_folder=False)`).",
   "tried": true,
   "result": "Kept as a `[stock]` line with schema 'graphite.stock-shortage-method/1', id, unit 'pcs', columns, and source path, sha256 and rows. Replay on stock2.csv gave R9 short 6 and Q3 short 5, status \"[+] Shortage in pcs \u00b7 preview on 63b3ac4d05 \u00b7 new source revision\", and a receipt under Slate/Chains/Methods/<id>/ carrying method, plan_id and output_sha256. Rows in unit 'reel' were refused: \"Method expects pcs but these rows use reel. Review the supplier units.\""
  },
  {
   "goal": "Keep a program on the Agenda, sequence two, and watch one",
   "steps": "`agenda.add {title, program}`; `agenda.add {title, program, when:{after: first id}}`; `agenda.run_next {}` repeatedly; `agenda.view {}`. For a watch: `agenda.add {title, program, watch:true}`.",
   "tried": true,
   "result": "Items ran in order, each ending DONE with its outcome text ('Part: R1 / Short: 6 \u2026', 'count: 2'), authority ['read']. The watch went to LATER; after the file changed and it came due it put \"A watched question changed \u2026 Changed: 1 new (Part R1).\" under waiting. A files.write program FAILED with the read-only message. A '/files.write \u2026' program FAILED with \"Expected a registered operation name\"."
  },
  {
   "goal": "A file change that waits for the owner",
   "steps": "`files.propose {path, text, why}`; the owner decides with `files.decide {id, apply:true}`, either on a card or through `inspect_in_line` and two Enters.",
   "tried": true,
   "result": "The proposal showed in agenda.view waiting as ('proposal', 'Change notes/proposed.txt', 'Graphite proposed it: \u2026'). files.decide gave state APPLIED and the file existed. On a proposal_card one click on Run applied it with no second confirmation."
  },
  {
   "goal": "Read back what worked before for a request",
   "steps": "`matrix.examples {\"text\": \"which parts are short in stock\"}`; `matrix.patterns {\"limit\": 10}`; `matrix.list {\"query\": \u2026}`.",
   "tried": true,
   "result": "examples returned the three stock pipelines under 'worked' with instruction null (no model had proposed them). patterns grouped by shape with tries, success and failed, for example '@files:stock.csv | rows | add Short = Required - Available | where Short over <N>'. matrix.promote turned a shape into a lesson with review PROPOSED_UNREVIEWED."
  },
  {
   "goal": "Know why every staC line suddenly refuses after an edit",
   "steps": "`from workbench import stacy_foundation`; `stacy_foundation.seed_status(k.root)` and look at state and changed_sources. Rebuild with `tools/package_graphite.rebuild()` (tools/package_graphite.py:78-103).",
   "tried": true,
   "result": "Seen live while another session had workbench/datasheet_work.py modified: state STALE, and every language.run and explain was refused with \"Graphite seed/source binding is not current\", while operation lines still ran. 444 files are seed inputs, among them shell2.py, typebar_qt.py, console_qt.py, stac_bridge.py, stacy_language.py, typed_pipeline.py, chain_menu.py, chain_workbench_qt.py, agenda.py, continuing_work.py and engineering_kernel.py. The two new commits each carry a rebuilt seed. I did not run the rebuild myself."
  }
 ],
 "gaps": [
  "No persistent record of 'the lines that produced this result, in order, each with what it returned' exists for general operation lines. `run_plan` produces exactly that list, [(line, ok, result)], but only in memory on a Talk card (shell2.py:1745-1765).",
  "`work.*` / `procedures.*` is the only store with ordered steps, full results, checks, references and parameters. It is limited to 8 step operations on delegated working copies (continuing_work.py:22-23), needs a project and an assignment, and a `work.query` may read only `work.read`, `projects.get` or `assignments.get` (line 330-341). It cannot hold a `documents.*`, `office.*`, `investigation.*`, `files.write` or `agenda.add` step.",
  "Procedure parameters replace whole scalar step arguments only (continuing_work.py:635-644). A `require` literal cannot be a parameter. A value inside a staC text cannot be one either, because `language.run` has the single argument `text`.",
  "A work order whose check fails is stuck: it cannot be accepted (\"Finish the order before reviewing its result\") or resumed (\"A failed step needs a new reviewed order\u2026\"). In my trial the apply step had already changed the working copy before the read-back check failed.",
  "staC has no variables, parameters, assignment or line-to-line feed. `$name` and `{name}` are literals and quietly give 0 rows. Replay on new material today means editing the line, or regenerating it as Method Press does (`Worksheet.program`, sheet_workbench_qt.py:548).",
  "The Agenda runs staC only, with read authority (agenda.py:307). An operation line as program fails, and a DONE item cannot be queued again. Repetition exists only as a watch or as `when.at` with `every_hours`.",
  "Investigation steps are staC only through the operation; `record_step` for operation steps is internal to the agent loop. `investigation.continue` reruns checks, never the plain steps. There are no parameters, and a step keeps a 600-character summary and a digest, not the result.",
  "Kept chains and Method Press are not Kernel records. They are lines in the text file ~/Concern/Ledger menu, written by a function that opens a name dialog (chain_menu.py:336-350), so neither the Agenda nor a model can reach them through dispatch. Method Press is one hard-coded shape. The tray's 'Keep as a method\u2026' only writes a `[chain]` line (chain_workbench_qt.py:337-340).",
  "`methods.*` is not a general method store. It is one profile, 'ledger.additive-capacity-method/1', proposed from a joined-work job (checked_methods.py:5, 72-94).",
  "Read versus write is decided by a hand-set `Step.kind` in field_do.py, not by the Kernel's scope for the operation. In the writing strip an execute-scope write such as `/files.write` or `/files.trash` runs on the first Enter with no confirmation; only approve scope asks. `stage`, `say_plan` and `proposal_card` run approve-scope operations on one click.",
  "`field_do.call` accepts JSON arguments only. `'/op name=value'` raises JSONDecodeError (field_do.py:47), and `run_staged` and `run_plan` do not catch it, so the card stays on 'Run' with no message (seen as a traceback from shell2.py:1691). `explain` is not recognised there either. `console_qt.parse_command` (line 67) already handles both argument forms.",
  "`inspect_in_line` sets the line without refreshing or hiding the results popup (context_menu.py:221-231). If the popup is open for other text, Enter runs that stale first row. I saw \"Ask staC \u00b7 <old text>\" run instead of the operation line; cause read from shell2.py:1064-1070. `use_program` hides the popup and is safe.",
  "The Edit button on a `proposal_card` puts 'op {json}' in the line without the leading slash (shell2.py:1874-1910), so it cannot be run from there as written.",
  "The journal and audit keep operation, state, origin, correlation id and time, with no arguments and no results (engineering_kernel.py:389-399, 508-522). Reads listed in `activity.OBSERVER_OPERATIONS` leave no line. A receipt for a step therefore has to be written by whoever runs it.",
  "Reviewed office sheets are cell maps, not rows. `@office:<id> | rows` answers \"Nothing at data.rows for this source\", and no lens turns sheet cells into rows; the new code reads single cells with `pick document.sheets | select cells.B2.value`.",
  "The start word `investigation <id> | inspect|gaps|why` means a knowledge investigation job, not the `investigation.*` records. On the worked case's investigation id it answers \"Record not found\".",
  "`apply` unwraps any result holding a list under jobs, models, events, operations or records (typed_pipeline.py:215-217). `@procedure:<id>` therefore returns its operation names, not the record; use `procedures.get {\"id\":\u2026} | pick steps`."
 ],
 "advice": "**Do not build again:**\n- the step type and line format: `field_do.Step`, `field_do.op`, `field_do.call`;\n- the enumerator: `field_do.steps_for`, `sweep`, `settling`;\n- one-step staging: `SlateFace.stage`;\n- the ordered runner with per-line results: `SlateFace.say_plan` / `run_plan`;\n- the durable template shape: 'arc.stac-procedure/1' in table `flow_procedures`, listed by `procedures.list` / `procedures.get` and addressable as `@procedure:ID`;\n- reference resolution: `continuing_work.resolve`, line 308;\n- typed scalar parameters: `parameter_parent` and the substitution loop, lines 611-624 and 675-680;\n- step checks: `assert_result`, line 371, and `investigations.oracle_holds`, line 108;\n- receipts: the 'graphite.chain-result/1' JSON written by `ChainTray.save_sheet`.\n\n**Smallest honest seam.** `run_plan` already yields (line, ok, result) in order. Keep that list as a record, and walk it again.\n\n**What is new, three pieces:**\n1. **A keep operation** (for example `procedures.keep {title, steps, parameters}`, execute scope). It turns lines into steps `{key, operation, arguments, after, require}` using `field_do.call`, and stores them in `flow_procedures` with a marker key. `checked_methods.sync_procedure` (checked_methods.py:59-69) already stores a foreign template there, and `procedures.instantiate` already refuses such a record (continuing_work.py:672); the marker makes it refuse kept chains the same way instead of failing on the step allowlist.\n2. **A walker outside the work-order executor.** For each step it substitutes values, resolves `$step` references, and looks up `CAPABILITIES[operation]`. Read scope dispatches at once; anything else goes to `say_plan` or `stage`. It then applies the step's checks and writes a receipt with the results. Deciding by scope rather than by `Step.kind` gives the rule the owner asked for in one place.\n3. **Parameters that reach inside a staC line.** Existing parameters replace whole arguments, so either add named placeholders in the `text`, or keep the source as its own parameter and assemble the line. This is the only piece with no precedent in the tree.\n\n**Fix on the way:**\n- make `field_do.call` use `console_qt.parse_command` and catch its errors in `run_staged` and `run_plan`;\n- hide or refresh the popup in `inspect_in_line`.\n\n**Mind the seed.** Any edit to `shell2.py`, `typebar_qt.py`, `console_qt.py`, `stac_bridge.py`, `stacy_language.py`, `typed_pipeline.py`, `agenda.py`, `continuing_work.py` or `engineering_kernel.py` stops all staC until `tools/package_graphite.rebuild()` has run. Check with `stacy_foundation.seed_status(root)['state']`.\n\n**Do not widen `work.*` for this.** Its grant, executor digest and working-copy rules are a different promise (unattended edits to copies). A kept chain of desk operations is better as a sibling record that reuses its helpers.\n\n**Where my trials are.** Scripts, outputs (out/p1.txt to out/p13.txt) and a pristine copy of the tree at bf42691 (tree/) are in /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/doer/chains/. run.sh there runs a script against that copy, because the live tree's seed goes stale whenever someone is mid-edit.",
 "not_checked": "- **Anything with a model.** The `brain.ask` plan path that feeds `proposal_card` with real proposals, `apply_on_page` for `documents.edit`, `run_program_proposal` for `programs.*` (REVIEW ACTION), and the matrix's intent linking (PROPOSED rows becoming outcomes) are read only.\n- **The `agent.*` loop** (agent_loop.py: profiles, `choose_next` with `brain.ask` mode 'choice'): I read its header and its `record_step` call only.\n- **`methods.*`** (checked_methods.py) end to end: it needs a joined-work job.\n- **`workers.*` steps, `changes.publish` to originals, `changes.undo`, `copies.*`.**\n- **Unattended running.** The Agenda Runner timer in a live window (the harness stops it) and the headless `host_service.tick_agenda` / `continuing_work.pump` path, so 'leave and come back' for a granted work order is read from code.\n- **`tools/package_graphite.rebuild()`**: not run.\n- **`stac.translate`**: it refused both sentences I gave it; its accepted forms are unread.\n- **The engineering dialect** (`use PROJECT@REV | part \u2026 | why`): no project is attached in the worked case.\n- **The uncommitted edits in `workbench/field_page.py`** and anything committed after bf42691.\n- **Line numbers.** In `shell2.py`, `field_do.py` and `field_page.py` they are as of bf42691 and were still moving while I worked.\n- **The ThinkPad.** Nothing here was run on it."
}