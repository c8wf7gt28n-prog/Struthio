# Model path and work loop: how Kasandra's hand could carry a planner over conditions

**Sources.** Paths under `workbench/` are relative to `/home/user/Struthio`. Trial evidence comes from these files:
- **R1** `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/live4b/i05_4b_baseline.json`
- **R2** `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/live4b/i05_joined_4b.json`
- **LOG** `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/live4b/i05_run1/Office/.ledger/brain/30a2605dae1f4f64b21c00a46f467344/runtime.log`
- **J1** `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/live4b/i05_run1/Office/.ledger/jobs/ccd978062e2c4dffa19b403612875051/` (I05 decision 1)
- **J2** `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/live4b/i05_run1/Office/.ledger/jobs/1b7efdc0521943b2aa8db4d64a7d49c9/` (I05 decision 2)

## 1. A chat or plan turn: how operations are offered and the answer checked

1. **Where it starts.** SlateFace tries the direct paths first (make, set, run, what-if, the selected thing) at `shell2.py:2560-2573`.
   - A question about something already read becomes a chat that sticks to those rows (`RECORDS_HINT`) at `shell2.py:2580-2598`.
   - Anything else becomes `brain.ask` with `mode:'plan'`, plus any program context or receipt, at `shell2.py:2616-2635`.
2. **The job.** `brain.ask` is checked and then submitted as a `brain.respond` job (`local_brain.py:1055-1063`). Its timeout is 120 s (`local_brain.py:1022`).
3. **`run_reply`** (`local_brain.py:796-1005`) builds the system prompt (`:817`). In plan mode it calls `plan_prompt` (`:884`, defined at `:750-769`), which calls `proposal_profile` (`:703-747`). The operations offered depend on the request:
   - No message: the whole `DIRECT_OPERATIONS` set (`local_brain.py:591-595`). This set lives in `local_brain`, not in `agent_operations`; `agent_operations` only supplies `validate()`.
   - A message: the 7 `CORE_OPERATIONS` (`:600`) plus up to `RELEVANT_TOOLS=6` (`:596`) from `tool_selection.relevant` (`:735-737`).
   - A request about an open page: `PAGE_OPERATIONS` plus at most 2 tools, each at most 1,000 characters (`:727-733`, `:605-606`).
   - A program context or receipt: discovery plus at most 3 tools within 2,200 characters (`:715-726`, `:608-609`).
   - Each operation becomes one `oneOf` variant `{operation: const, arguments}` (`:744`).
   - The `ledger.settings.set` key is narrowed (`:741-742`).
   - `documents.edit` is narrowed to one kind of change per proposal (`:743`, `:679-701`).
   - The top-level schema is `{text ≤240, actions ≤3}` (`:746`).
4. **How tools are chosen.** `tool_selection.relevant` uses explicit word matching and no model (`tool_selection.py:94-140`).
   - It has a deny list (`:20`).
   - It offers read and execute operations only, except the program review actions (`:101-104`).
   - It takes at most two per family before filling the rest (`:134-139`).
   - Each chosen tool gets one line of "why" (`:143-145`), appended to the prompt at `local_brain.py:765-767`.
   - Learned examples from the instruction matrix are appended too (`local_brain.py:885-889`).
5. **Generation.**
   - `slate_stream.fit_history` drops older dialogue until the prompt fits (`slate_stream.py:27-40`).
   - `complete` decodes against a strict `json_schema` (`slate_stream.py:79`) at temperature 0 (`:77`), with thinking switched off (`local_brain.py:471`).
6. **Checking the answer** (`checked_plan`, `local_brain.py:772-793`):
   - The JSON is parsed strictly, and its keys must be exactly `text` and `actions` (`:777-779`).
   - Every operation must be one that was offered, or it fails with `MODEL_PLAN_OPERATION_NOT_OFFERED` (`:780-783`).
   - The advertised schema is checked only on the program inquiry path (`:784-787`).
   - Approve scope is added only for `PROGRAM_REVIEW_ACTIONS` (`:788-791`, `stacy_control.py:170-177`).
   - Then `validate_actions` (`stacy_control.py:272-292`) checks:
     - between one and three actions, each within the delegated scope;
     - Tutor mode is read-only;
     - a provider may not propose approve-scope or owner-key operations, nor `jobs.submit` of `brain.activate` (`:286-291`);
     - finally `agent_operations.validate` against the **public** schema (`:292`). That validator ignores `oneOf`, `const` and `pattern` (`agent_operations.py:38-78`), so the narrowed forms are enforced only during decoding.
7. **Program inquiry.** It makes at most `MAX_READS=2` automatic reads (`program_inquiry.py:8`) within 110 s (`local_brain.py:882`). It refuses a repeated `(operation, paths)` (`program_inquiry.py:111-113`), which ends the loop (`local_brain.py:952-957`). If replanning runs out of budget, the answer becomes "Local reads finished" (`:965-974`).
8. **After a valid plan.** `bind_actions` runs, the instruction matrix records the plan (`:979-984`), and the dialogue is committed under model and conversation digest checks (`:989-997`).
9. **On screen.** `poll` shows proposal cards with Run and Edit (`shell2.py:2637-2720`). Only a `documents.edit` on the open page applies by itself (`:2761-2787`). Run calls `execute` directly (`:2715`), so **model proposals never pass through her hand** (`stage`).
10. **Choice mode** is the smallest structured answer in the codebase: `{"choice":n}`, 24 tokens, using only the last 2 messages (`local_brain.py:892-896`, `:897`, `:915-920`). `agent_loop` uses it (`agent_loop.py:548-557`).

## 2. Token and time budgets

| Budget | Value | Where |
|---|---|---|
| Context options | 512–8192; 2048 when unset | `local_brain.py:18`, `:221` |
| Trial context | 6144 tokens, 4 threads, 4480 MB | `joined_model_checks.py:96`, `adaptive_checks.py:301` |
| Fit rule | prompt + output + 32 ≤ context | `local_brain.py:476`, `slate_stream.py:34`, `:67`, `slate_action.py:134` |
| Output tokens | choice 24, plan or reference 384, chat 256 | `local_brain.py:897` |
| Plan text | ≤240 characters; prompt asks for <120 and one action | `local_brain.py:746`, `:768` |
| History | last 8 messages (choice: last 2) | `local_brain.py:890`, `:896` |
| Seed excerpts / matrix | 2,400 characters (matrix on a page: 800) | `local_brain.py:862`, `:889`, `:607` |
| Program context / receipt | 1,800 / 2,500 | `local_brain.py:31-32`, `stacy_control.py:215` |
| `PROGRAM_TOOL_LIMIT` | 2,200 characters, ≤3 tools | `local_brain.py:608-609` |
| Why the core set exists | the full direct set's schemas are about 6,800 characters and overflowed 2,048 tokens | `local_brain.py:597-599` |
| Adaptive limits | frontier 1–16, decisions 1–32, `max_tokens` 128–2048, **`decision_seconds` 5–180**, failures 1–10 | `adaptive_contract.py:22-26` |
| SELECT / ARGUMENTS split | `min(256, max_tokens//3)` / the rest | `slate_action.py:180`, `:201` |
| SELECT prose caps | why 180, uncertainty 160, expected 2×100 | `slate_action.py:177-178` |
| Tokens reserved per decision | 2×context, refunded by actual use | `adaptive_work.py:431`, `:401-402` |
| Frame | ≤131,072 bytes; last 24 observations | `adaptive_work.py:244`, `:224` |
| ACTION job deadline | 240 s, fixed by the Kernel | `engineering_kernel.py:1223`, `local_brain.py:1022` |
| `agent_loop` | prompt ≤600 characters, ≤4 options, 180 s patience, then the default | `agent_loop.py:128-129`, `:511`, `:620-622` |

## 3. The two assignment loops

### 3a. `adaptive_work` (`work.investigate`): the model chooses each step

**Setup.**
- `create` requires the `brain.action` tool, binds the current model, and requires `memory_mb` at least the model's (`adaptive_work.py:39-59`).
- `initialize` builds the frontier from the owner's candidates and freezes the operation schemas (`:62-69`).

**`advance`** (`:417-497`):
1. Runs only from READY. Gate and foundations are checked; a pending job goes to `consume_pending` (`:422-423`).
2. Budget checks: steps, failures, decisions, frontier exhausted (`:424-428`).
3. With no choice yet, it is a **decision**: operation `slate.action`, `decision_seconds`, 2×context tokens (`:426-431`).
4. Otherwise it is an **action**:
   - `validate_call` (`:433`, `:254-296`) checks the grant, the branch, that the operation is available now, the schema, the copy, that the action was produced by this work, and that jobs and receipts belong to it.
   - A fingerprint `{op, args, binding}` is taken (`:434`). **The duplicate guard raises `DUPLICATE_ACTION_ON_UNCHANGED_INPUTS` at `:435`.**
5. Seconds, tokens and files budgets (`:436-441`).
6. The intent is saved before the effect (`:451-455`).
7. A work-scope guard enforces `ADAPTIVE_STEP_TIME_LIMIT` (`:456-460`).
8. Effects:
   - A decision goes to `slate_action.submit` (`:465`); the job is bound and the work waits READY with `AWAITING_ACTUAL_MODEL_RESULT` (`:476-480`).
   - An inline operation's exception becomes `TOOL_ERROR` and a FAILURE (`:468-475`).
   - On success, the copies' signatures are checked (`:482-483`), then `finish_item` (`:487`).
9. Any `ValueError` leaves the work WAITING, or LIMIT for `BUDGET_*`, with the reason (`:489-497`).

**`consume_pending`** (`:384-414`):
- A failed decision job marks the step FAILED, adds one failure, and leaves the work WAITING with `MODEL_DECISION_FAILED: …` (`:390-397`).
- Otherwise it refunds unused time and tokens (`:401-403`) and calls `apply_decision` (`:359-382`):
  - FINISH needs current completion evidence and must cite it (`:363-366`).
  - ASK leaves the work WAITING with a question (`:374-376`).
  - FINISH moves it to REVIEW (`:377`).
  - CALL leaves it READY with the choice (`:378`).

**A decision has two model phases** (`slate_action.run_job`, `:163-225`).
- `phase_view` shows the problem, the frontier, the actual observations, and the tools without their argument schemas (`:32-61`).
- **SELECT** chooses `{operation enum, candidate enum, why, uncertainty, expected}` (`:177-181`). The answer is written to `action-selection.txt` (`:182`).
- **ARGUMENTS** fills in the selected operation's arguments, plus alternatives (≤1) and updates (≤2), using the rest of the deadline (`:186-202`).
- The two answers are reassembled and checked against `frame['response_schema']` (`:209-212`). That is the next-step schema with `oneOf` variants (`adaptive_contract.py:123-145`):
  - one CALL variant per available tool (`:129`);
  - ASK only when declared unknowns exist (`:130-132`);
  - FINISH only when allowed, with citations when required (`:133-135`).
  - `validate_schema` requires exactly one variant to match (`:56-61`).
- Semantic rules follow (`slate_action.py:75-110`): REJECT needs an ADVERSE observation (`:91`), every adverse result must be interpreted (`:97-100`), ASK may name only declared unknowns (`:101-103`), and CALL needs `expected` (`:105-106`).
- So the `oneOf` is used to check the answer afterwards. Decoding uses the two smaller schemas.

**The frame already computes condition-like facts** (`adaptive_work.frame`, `:188-245`):
- `producer_readiness` (`:125-161`) narrows `*.run`, `*.result` and `joined.prepare` arguments to enums of ids this work actually produced. Where nothing is ready, it writes `missing_dependencies` (`:141`, `:149`, `:160`).
- Methods are available only with a KNOWN quantity and a KNOWN interval (`:210`).
- It also computes `finish_observations` (`:229`) and `pending_adverse` and `adverse_targets` (`:240-241`).

**The completion check** (`completion_evidence`, `:164-185`) reads current state again. It is satisfied by:
- a `joined.result` that is AVAILABLE and carries all four `APPLICATION_TYPES` (`:173-177`, `adaptive_contract.py:13`); or
- a `methods.preview` run again that still rejects its precondition, with the same digest (`:178-181`).

**The 180 s limit.**
- 180 s is the schema maximum (`adaptive_contract.py:26`) and the UI's default (`adaptive_qt.py:81`). The trials use it too (`joined_model_checks.py:51`).
- It is the **whole two-phase deadline** (`slate_action.py:138`, `:180-181`, `:199-202`).
- It is also the step guard (`adaptive_work.py:456-458`) and the stream deadline (`slate_stream.py:48`, `:113`).

### 3b. `agent_loop` (`agent.assign`): profiles choose; the model only picks among options

- Profiles plan explicit steps (`agent_loop.py:325-361`).
- Each step dispatches one operation with a principal bounded to read and execute, never approve (`:237-241`, `:403-415`). A failure leaves the assignment WAITING (`:476-481`).
- The model is asked only when more than one option is acceptable, in choice mode. After 180 s the default is taken (`:590-638`, `:128`).
- `status_row` (`:273-292`) feeds the right column's WorkBlock.

## 4. What the 4B did here

**Capacity trial: 3 of 3 passed** (`adaptive_checks.live_checks`, `:286-313`; operations at `:208`).
- Nine decisions, all validated on the first attempt, with no failures (R1:636, 3673, 6630).
- Capacity_A and Capacity_B followed the same sequence (R1 `cases[i].work.decisions`):
  1. `math.concurrent` with the right variable names, about 75 s. SELECT read about 1,957 prompt tokens and wrote 90–94; ARGUMENTS wrote 28.
  2. ASK for exactly the 3 declared lifetimes, with REJECT of b1 citing O1, about 104–106 s.
  3. `math.schedule` with the right quantity and lifetime pairs, 107–152 s. In one case under CPU load: 49 tokens/s prompt, 3.3 tokens/s generation.
  4. FINISH citing O2, 143.5 s and **172.9 s** (R1:4714). The second was 7 s under the limit.
- Direct_title: FINISH with no tools, 71.4 s.

**Joined trial (I05) Current_A: failed.**
1. **Decision 1, 148.2 s** (R2:1436), validated:
   - SELECT took 69.4 s: 2,529 prompt tokens at 56 tokens/s and 138 output at 5.6 tokens/s (LOG:32-37).
   - ARGUMENTS took 78.6 s: 2,662 prompt at 75 tokens/s and 241 output at 5.6 tokens/s (LOG:59-64).
   - It chose `methods.preview` with a correct mapping and all 7 declarations exactly as the method expects (J1 `action-arguments.txt`; `checked_methods.py:14-15`).
   - The preview was observed SUPPORTED (R2:1812).
2. **Decision 2.**
   - SELECT chose `methods.instantiate`, the right next step (J2 `action-selection.txt`). It took 74.5 s: 2,926 prompt at 74 tokens/s and 144 output at **4.1 tokens/s** under load (LOG:82-87).
   - ARGUMENTS read about 3,170 prompt tokens (3,072 at 97% progress, LOG:101) at 59–70 tokens/s. Generation ran at 3.6–4.0 tokens/s with dips to 1.5 (LOG:102-111).
   - The deadline came at about 200 of the roughly 240 tokens the same mapping needed in decision 1 (`n_tokens=3366`, LOG:113).
   - Result: `LOCAL_STREAM_TIME_BUDGET` (J2 `stdout.log`; R2:1353).
3. The work stopped WAITING after 328.6 s and 17,858 tokens (R2:1369-1371). The trial stops at the first failed case (`joined_model_checks.py:122`).

**What the time went on (from the records):**
- **The model was copying arguments the coordinator already had.** After a SUPPORTED preview, `method_continuations` puts the exact `methods.instantiate` arguments into the ARGUMENTS view (`slate_action.py:8-29`, `:46`).
- **Prose always runs to the cap.** In all 11 SELECT answers, `why` is 180 characters and `uncertainty` is 160, cut mid-sentence (for example R2:1340, which ends "…The prelude in"). That is about 90–145 tokens, roughly 16–26 s per SELECT. The operation and candidate take about 15.
- **Pretty-printed JSON.** Decision 1's arguments were 712 characters with 31 newlines; the same JSON compact is 498 characters (J1).
- **No prompt reuse.**
  - `run_job` passes no `cache_key`, so `cache_prompt` is false (`slate_stream.py:73-78`); the records show `cache_n 0`.
  - The 4,348-character system prompt (`adaptive_contract.py:148-165`) is read again in every phase.
  - Canonical JSON sorts its keys (`project_desk.py:77-78`), so the view's first key differs between phases straight after the system prompt.
- **The prompt grows with each observation**, by 333 to 659 tokens (R1 SELECT prompts 1957, 2290, 2652, 3311; R2 2529, 2926).
- **Estimate:** Current_A still needs about 7 more decisions. The frame would reach about 5,300 tokens and press against the 6,144-token check (`slate_action.py:134`) by the FINISH turn, whatever the speed.

## 5. What a 4B does reliably in one short structured answer

**Reliable (evidence):**
- It picks one operation, branch, alias or variable from enums every time: 11 of 11 SELECTs were sensible, and every enum slot was valid (R1, R2).
- It cites the right ADVERSE alias for REJECT and names exactly the declared unknowns for ASK.
- It fills an argument object correctly when its values are enum names (Capacity cases, I05 decision 1).

**Not reliable:**
- Free text: it always fills the cap.
- Long argument objects inside a deadline: about 240 tokens took about 43–60 s.
- Two phases within 180 s once the prompt passes about 2.9k tokens on this CPU.
- Earlier findings in the code agree:
  - small models filled every optional key under constrained decoding (`local_brain.py:680-686`);
  - Qwen2.5-0.5B picked badly, so the rule's default stays primary (`agent_loop.py:47-49`).

**A shape that fits:**
- one phase;
- all slots enums, no optional keys;
- at most one text slot of about 60 characters, or none;
- about 40 output tokens or fewer (about 8 s here);
- a prompt of about 2.5k tokens or fewer (about 35 s).

That is about 45 s under load, well inside 180 s. Choice mode (`local_brain.py:892-896`) is the existing primitive for it.

## 6. Where a "goal and conditions" turn would sit

**The work (primary).**
- **Where it goes.**
  - Add `state['conditions']=None` in `initialize` (`adaptive_work.py:67`).
  - In `advance`, split the decision branch (`:426-431` → `:449-450`): with no conditions yet, run a **GOAL** turn through the same `slate_action.prepare` and `submit` (`:127-152`).
  - Give `run_job` (`:163`) a single-phase branch whose schema is `{conditions:[enum ids], uniqueItems}`.
  - Consume the answer where `apply_decision` consumes decisions (`:359-382`), and save it with `flow.save`.
- **Where the conditions come from.** The coordinator builds the condition list in `frame` (`:188-245`) from:
  - `completion_evidence`'s required artifacts (`:164-185`);
  - declared UNKNOWN variables, which only ASK can settle (`adaptive_contract.py:130-132`);
  - each catalogue row's `effects` (`adaptive_contract.py:118-119`);
  - `missing_dependencies` (`adaptive_work.py:141`, `:149`, `:160`).
- **Deduction before asking.** For each open condition, if exactly one producing operation is ready and its arguments are already settled, the coordinator writes `state['choice']` itself, in the same shape `apply_decision` writes at `:378`, marked as deduced. "Settled" means every required argument is a single-value enum from `producer_readiness`, or there is a `method_continuation`.
  - The ACTION phase still runs `validate_call`, the gate and the grant (`:254-296`, `:422`), so deduction gains no authority.
  - Otherwise, one short SELECT over open conditions and their producing operations.
- **I05 after the preview, entirely deducible:**
  - instantiate: from the continuation;
  - `methods.run` and `joined.run`: `action` and `expected_digest` are single enums (`adaptive_work.py:132-140`; `checked_methods.py:30`; `joined_work.py:13`);
  - `*.result`: `job` is a single enum (`adaptive_work.py:142-148`);
  - `joined.prepare`: `receipt`, `copy` and `method_job` are single enums (`:150-160`; `adaptive_contract.py:105`).
  - Only the mapping and the FINISH wording need the model.
- **Finish rule.** Extend `apply_decision`'s FINISH check (`:363-366`) so every agreed condition must be held by a current observation.
- **Owner's A/B.** The frozen spec says "no model choice injection" (`joined_model_checks.py:95`). Run B needs its own frozen spec, and deduced steps must be recorded as the coordinator's.
- **Gap for intervals.** Problem variables have no tolerance field (`problem_service.py:16-22`), and the `interval` type means a time lifetime (`schedule_math.py:6`, `:31-40`). Interval arithmetic on a recorded error bound needs a schema addition.

**Talk.** Add a `goal` mode beside `choice`: the `brain.ask` modes are at `local_brain.py:57`, and the choice handling at `:892-896` and `:915-920`. This is where the word-only fallback sits today when no profile fits (`agent_loop.py:143-157`).

**Desk.**
- Her door is `desk_doers.run` with `door='her'`, refused at `desk_doers.py:1425`. It would sit behind `desk_hers` (`desk_acts.py:299-339`).
- `plan_variants` supplies the choices (`:364-374`). That is about 9,000 bytes for 35 acts (`:366`), which is too heavy for a 4B without narrowing.
- `read.desk` checks window conditions and never asks (`:324`). The Field's key-path search can deduce the presses (`:399-417`).

## 7. The duplicate guard: hand back evidence instead of failing

**Today.**
- `:435` raises, and the work is left WAITING (`:489-497`).
- The decision that chose the repeat was already spent against the decisions budget (`:427`).
- The fingerprint includes `binding` (`:15-16`), so the same call after a problem revision is still allowed.

**Proposal, at `:435`:**
1. Find the observation row with the same operation, the same canonical arguments and the current `context_digest`. Rows store all three (`:330-333`).
2. Do not run anything. Clear the choice and record `{returned:'O<n>', for:key}`.
3. Set READY with reason `EXISTING_EVIDENCE_RETURNED: O<n>`. Nothing is charged, because charging happens later at `:446`.
4. `frame` shows the returned evidence and the conditions still open.
5. A repeat counter brings back today's WAITING on the second repeat.

**Precedents.** Inquiry's seen-set (`program_inquiry.py:111-113`). The "an unchanged preview is a duplicate" hint (`slate_action.py:26`, `:52`). Jobs cannot repeat at all: used actions and jobs drop out of the enums (`adaptive_work.py:134-136`, `:145-146`).

## 8. A timed-out write: checking what landed

- **Inline write.** An exception is recorded as a FAILURE without looking (`:468-475`).
  - `continuing_work.reconcile_apply` (`:409-430`) does the right check: `edit_applications` → commit DONE → `assert_result` → `signatures` equal `expected_after` (`:137-144`, `:350-355`). But it is called only from an explicit resume (`adaptive_work.py:517-523`).
  - Proposal: call it on exception or `ADAPTIVE_STEP_TIME_LIMIT` for `working_write`.
    - Landed: `finish_item` with the recovered commit, as resume does (`:551-554`).
    - Partial: `PARTIAL_APPLICATION_REQUIRES_CHANGES_RECOVERY` → WAITING.
    - Nothing landed: a retry may then be proposed (`seen` popped, as at `:523` and `:544`).
  - `changes.propose` already reuses its stable proposal id (`:444`, `:467`, `:537-539`).
- **Job submission.** If a crash comes before the job id is saved, the `requests` lookup by `pending_key` finds it (`:299-302`, `:524-533`).
- **Model turn.** A valid SELECT had already landed in J2 when the deadline came, but `consume_pending` discards it (`:390-397`). A retry under the same frame binding (`slate_action.py:113-124`) could reuse it.
- **Desk act.** `desk_doers.run` reports what was changed (`:1430-1439`) and what happened before a window that asks (`:1440-1441`). It writes a journal line with a correlation id (`:1455-1466`). So: `read.desk` plus the journal, before any retry.

## 9. Model swap today, and escalation under her hand

**Today only the owner swaps.**
- `brain.model.use` has approve scope (`local_brain.py:65`).
- The Kernel refuses activation without approve (`engineering_kernel.py:1225`).
- Model proposals cannot include it (`stacy_control.py:286-291`).
- It is not on her free-hand list (`stacy_hand.py:41-42`), so `hers` is false at every place of the dial (`:150-158`) and it waits with "not among the things I do by myself" (`:161-164`). It is not on the always-asks list (`:46-57`).
- Where swaps are started: `brain_qt.py:227-228`, `model_settings_qt.py:27` and `:66`, `office_building_qt.py:435`, `service_lifecycle_qt.py:174`, and the campaign scripts (`tools/campaign_lib/runner.py:75`, `:80`).

**How a swap runs** (`run_model_job`, `local_brain.py:504-589`):
- It refuses while a reply is running (`:515-517`).
- It checkpoints, stops the old model, waits for memory, loads, probes, and activates (`:513-552`).
- It restores the previous model on failure (`:565-589`). `brain.restore` swaps back (`:1041-1047`).

**Blocks to escalation:**
- Adaptive work pins one model. A swap stops it with `ADAPTIVE_MODEL_CONFIGURATION_CHANGED` (`adaptive_work.py:30`, `:50`; `slate_action.py:123`, `:130`).
- No "think more" lever: thinking is off (`local_brain.py:471`), temperature is 0 (`:477`), the 180 s cap is already reached, and the Kernel fixes the 240 s deadline.
- Self-consistency at temperature 0 needs varied prompts, such as a permuted option order.
- Vision models are refused for chat (`:217`).

**Escalation proposal:**
1. Detect at `consume_pending`'s failure branch (`adaptive_work.py:391-397`).
2. First, a smaller turn: deduction, a single phase, reusing the selection that landed.
3. Then more thinking, which needs contract changes.
4. Then a card from `SlateFace.stage` with the `brain.model.use` line, approve scope, `asked=True` (`shell2.py:2006-2045`). It is never hers, so it always waits for Approve.
   - Batch it: queue the turns that need the bigger model and swap once, when no reply or ACTION job is running.
   - Afterwards, propose `brain.restore` to swap back.
   - The work order must name the allowed models and memory when it is granted (`adaptive_work.py:39-59`), so the binding check accepts the swap.

## 10. Her cards, trail and Undo in SlateFace, and where plan progress could show

**What is there now.**
- **Pane layout:** portrait, name and hand dial (`shell2.py:1786-1795`); the This line and the Now line (`:1804-1808`); WorkBlock and RelatedBlock (`:1811-1813`); the conversation (`:1814-1817`).
- **`stage`** (`:2006-2045`):
  - lead words that depend on her hand (`:2021-2027`);
  - the why, and the line in a code label (`:2028-2033`);
  - an amber Approve, or done at once if it is hers (`:2034-2045`).
- **`run_staged`** (`:2047-2092`):
  - the Kernel's reply is kept with its correlation id (`:2057`);
  - Kasandra's picture shows the outcome (`:2061-2062`);
  - the result is said in words (`:2063-2076`);
  - a trail line and one Undo, or a note that there is no exact Undo (`:2077-2091`).
- **Undo:** guarded by `changed_since` (`:2105-2148`).
- **Trail:** each entry holds `{at, words, line, undo, word, state, guard}`, 40 kept (`stacy_hand.py:34`, `:241-249`). It is shown latest first with "Undo this" (`shell2.py:2166-2181`). What always asks is listed at `:2205-2214`.
- **Model proposal cards:** `shell2.py:2684-2720`.
- **WorkBlock:** five lines from `agent.status` (`agent_qt.py:330-392`). It already has a `condition` inspect kind with a stale recheck (`:376-379`, `:409-427`; condition states CURRENT, STALE, BROKEN at `conditions.py:47`).
- Adaptive investigations show only in the Lab's tables (`lab_qt.py:39-40`; `adaptive_qt.py:17-41`), not in SlateFace.

**Proposal:**
- **A plan card** (`Card`, `shell2.py:2927`) when the goal is agreed: one row per condition, with its state (open, held, not held, stale) and an evidence word that inspects the observation.
  - It is updated by `poll` (`:2637`) or a timer like WorkBlock's (`agent_qt.py:342`).
  - When a condition becomes held, a line is added to the card: "Held · <condition> · from O<n>".
  - Returned evidence appears as "Already known · O<n>".
- **The trail stays acts only.** Her acts inside a plan still go through `stage`, so each keeps its card, trail line, Undo, and always-asks rule.
- **WorkBlock rows:**
  - Doing now: the open condition being worked;
  - Found: how many conditions are held;
  - Needs you: ASK questions and escalation cards;
  - Inspect: the conditions (`agent_loop.py:287-288`).

## 11. Owner-rule hazards on this path

- **A key on screen.** The Approve tooltip says "in the Field, G does the same" (`shell2.py:2035`). The plan card must not copy it.
- **"Programs" on screen.** These errors reach the screen through "I could not start: …" (`shell2.py:2633`): `local_brain.py:623`, `:631`, `:633`.
- **The I05 frozen spec** forbids injected choices (`joined_model_checks.py:95`). Deduced steps need run B's own spec, and must be recorded as the coordinator's.