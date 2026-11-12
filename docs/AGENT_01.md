# The resident agent loop (HATCH AGENT-01)

November 5, 2026 · UTC. The owner's direction (Commission v2.1 and the decisions of 2026-11-05, D19): Slate takes an assignment, works it one bounded step at a time with real tools, keeps a durable record of findings and open conditions, can be paused, resumed and stopped, and stays useful with the smallest model because explicit procedure comes first and the model only chooses among a few proposed next steps.

## The record

An assignment is an **investigation** (`workbench/investigations.py`: the question, claims as FINDING, CANDIDATE or QUESTION with computed evidence states, every step with its input digests, outcome and result digest, sources, checks, stop, refresh) plus one row in `agent_assignments` (same Kernel SQLite file): profile, request, context, plan, cursor, state, reason, budget, paused reason, model job. The investigation sheet (`investigation.sheet`) and the room Hatch ▸ Work ▸ Investigations & assignments show all of it. Nothing new was added as a store, scheduler or dispatcher.

States: READY (assigned), RUNNING (a driver is stepping it), PAUSED (Ledger closed, Master Stop or the owner), WAITING (the owner is needed: a question, a refused step, units that differ), DONE, STOPPED, FAILED.

## The step

`agent.step {id}` runs exactly one planned step: the profile's next operation is dispatched through the Kernel with a principal bounded to the budget's effects (read, or read and execute; never approve or candidate), the step is recorded in `inv_steps` **before** its result is interpreted (operation and arguments as the program, input digests, outcome, summary, result digest, seconds, authority), then the profile turns the actual result into claims and context, and the cursor moves. A refused or failed dispatch is recorded FAILED and moves the assignment to WAITING with the error in words; Resume retries it. Budget exhaustion is STOPPED with "Budget used: N steps, S seconds". `agent.run` repeats steps synchronously within limits (tests, command line); the desktop uses a timer driver (`workbench/agent_qt.py`) that calls `agent.step` while an assignment is RUNNING and yields to the interface between steps.

## Profiles

A profile (`workbench/agent_profiles.py`, interface in its docstring) is explicit Python: `plan` gives the first steps as registered operations or `helpers:<name>` local computations; `arguments` completes a step from earlier results; `interpret` turns a result into claims, context, `done`, `waiting`, further steps or `options`; `failed` says what to do after a refusal. This pass ships `operation_sequence` (an explicit plan, for tests) and `numbers_on_page` (`workbench/profile_numbers.py`): read the page → find the quantities with units (helper `quantities_from_text`) → sum them with a dimension check through `math.evaluate` → append the result paragraph to the page through `documents.edit` → bind a condition card to the exact input words. A request earns a profile by its words (`agent_loop.request_profile`: a verb such as add up, total, sum, count, a noun such as numbers, quantities, values, and a place such as on this page); a request no profile fits becomes a WAITING assignment that says so, with its own investigation, rather than a silent nothing.

## Where the model plugs in

Where a profile offers options, `choose_next` asks the local model only when more than one option is acceptable and a worker is READY: `brain.ask` in **choice mode** (added in this pass: the message lists the numbered options; the answer is one option number, schema-constrained, temperature 0, at most 24 tokens). The pick is taken only if the profile marks that option acceptable; otherwise the default is taken and the step says "model chose k, not acceptable here, default taken". Every consultation is a recorded step (kind MODEL_CHOICE: operation, job id, pick, decision, prompt); a rule-only choice is kind CHOICE. Measured in the build container (docs/MODEL_TRIAL_01.md): the 0.5B model chose poorly every time, the 1.5B model chose the plain case right; the rules therefore stay primary, and a better model simply picks better.

## Condition cards and helpers

A **condition card** (`workbench/conditions.py`, record kind `condition`) binds a written result to the block ids, offsets and quoted words it was calculated from on the saved revision. Every document write marks affected cards STALE (words changed or moved) or BROKEN (the result paragraph is gone); the page shows a quiet line with the word recheck; `conditions.recheck` re-extracts from the current revision, recomputes and rewrites only the result paragraph, bound again. A **helper** (`workbench/helpers.py`, record kind `helper`) is a procedure Slate uses, kept with its purpose, inputs, outputs, limits and source and counted on every use (uses, successes, failures, effectiveness), so effective helpers are reused and improved; this pass ships three module helpers (`quantities_from_text`, `sum_model`, `condition_card`), and the record shape already allows sandboxed Python helpers Slate writes later.

## The right column

`agent.status` gives five plain lines per assignment: working on (the request), doing now (the running or next step's purpose, or the reason it waits), found (FINDING claims with their evidence state), needs you (QUESTION claims and the WAITING reason), inspect (the investigation, the document, the condition cards). The Work block under Slate's face shows them with the words Stop, Pause, Resume and Inspect; the Related block beneath lists the owner's own records that share the page's words (`ledger.related`, word match, dismissable). Closing Ledger pauses running assignments ("Ledger closed"); Master Stop pauses them too; the Today page lists paused assignments with a resume word.

## Operations added and recorded

`agent.assign`, `agent.step`, `agent.run`, `agent.pause`, `agent.resume`, `agent.stop` (execute), `agent.status`, `agent.list` (read); `conditions.recheck` (execute), `conditions.list`, `conditions.get` (read); `helpers.list`, `helpers.get` (read); `ledger.related` (read). Extensions of recorded operations: `documents.edit` change `append` (a paragraph after the selected one; WORKSHOP-01's own addition), `brain.ask` mode `choice` with `choices` (SERVICE-01 baseline, recorded extension), `ledger.navigate` destination `investigations` (recorded extension). All are private to this computer for cloud proposals; the reads are journal observers.

## Boundaries that hold

No second dispatcher, scheduler or data store; zero workers, models or native tools started by the loop itself; the budget's authority is enforced by the Kernel's scope checks, not by asking a model to behave; every step is recorded before it is interpreted; stale or changed inputs are refused, never merged; the live model column is filled only by the trial records in `build/agent01_ui/model_trial/` and says where they ran.
