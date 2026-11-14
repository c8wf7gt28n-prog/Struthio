PART 1: THE PLAN

# Kasandra's hand on the desk, with a planner over conditions
For the next build pass, from HEAD d1df337 (0.8.2). All paths are relative to /home/user/Struthio.

## 0. Verdict

The two designs come out level, so this plan merges them. From A it takes the model contract and the safety defaults. From B it takes the runtime: working state kept in the session, a forward search for desk moves, a touch filter keyed on the window, offers made one segment at a time, a state signal for the hologram, and the B1/B2 experiment arms. It also adds three fixes I found while checking the code.

| Criterion (score out of 5) | A, planner first | B, model in the loop | Why |
|---|---|---|---|
| Reliability: 4B here, 35B on the ThinkPad | **5** | 4 | A asks the model only enum questions and skips it when a request matches fully. B asks NEXT at every tie between options that do not dominate each other. Each option is admissible, but that means more turns, and agent_loop.py:47-49 already records that small models pick worse than a rule's default. B's "late answer takes the read by default" rule and its prompt reuse are good, and both are kept. |
| Safety | 4 | 4 | **A's strengths:** DELETE waits at every place until it has an Undo; a measured cell is never edited to make its own goal true; a tie between two meanings whose branches are only reads is shown, not asked. **A's weaknesses:** `goals.make` is execute scope, and a hand-turn record is written by the executor, so at Ask first her own bookkeeping would either wait or be written without being seen. **B's strengths:** nothing is written while she works; an offer is voided by the owner's touch; goals are agreed before any change. **B's weaknesses:** at Free hand it trashes with no Undo, lets the model write file text, and changes `investigations.execute`, which is on the owner's own path. |
| Maths used where it helps | 4 | **5** | Both are exact, and their numbers agree (I re-derived them, §7). A runs a backward A* search over the desk. But the whole state is read at every tick and effects are conditional (`go.field` selects the first sheet), so a forward search over the projected state is exact and simpler. B does that, and keeps regression and weakest precondition for the cases where they give a boundary. B also puts a cost on asking the owner (300 s), so questions rank after reads. |
| Buildability in slices | 4 | 4 | A's S0 ships nothing the owner can see. B's S1 ships real value, but its S4 is very large. Neither first slice has both a door scene and a 4B check, which the brief requires. |

## 0.1 Claims I checked in the code (read-only, d1df337)

**Her door and the presses**
- `desk_doers.py:1425` refuses `door='her'` outright.
- Synthetic presses come in two kinds:
  - `mouse`, `right_click` and `type_text` use `sendEvent` with events the code builds itself, so they are non-spontaneous (`desk_doers.py:252-253`, `:259`, `:274`).
  - `key`, the menu rows, `go.app`, the panes, the line chooser and `hand.approve` use QTest's widget overloads (`:265`, `:333`, `:465`, `:787`, `:808`, `:1187`, `:1333`). Without `QTEST_QPA_MOUSE_HANDLING` these deliver the event to the widget through `notify`, with no QWindow in the path.
  - So `spontaneous()` cannot tell the owner's input from hers. No doer sends to a QWindow (grep finds no `windowHandle` or `QWindow` in desk_doers), so "the receiver is a QWindow" can.

**Her hand's lists and the Trash**
- In stacy_hand.py:
  - `KEPT=40` at `:34`.
  - `files.trash` is on `HERS_SHOW` (`:39`).
  - `UNDOES=('field.set','files.trash')` (`:43`).
  - `'*.delete'` is in ALWAYS_ASKS (`:50`), so renaming the operation would change how it behaves.
  - `why_waits` gives the list reason even when the real reason is the dial (`:161-164`).
- `files.trash` returns an `id` (`files_service.py:510`). `files.restore` is approve scope (`:72`). It refuses an id that is already used and restores to a free name, never overwriting (`:514-523`). So a restore Undo protects itself.
- `operator()` holds approve scope (`engineering_kernel.py:299-302`). The Undo path dispatches with `operator()` (`shell2.py:2100-2101`), so a `/files.restore` Undo runs at the owner's click.

**The desk acts**
- `route_said` reports a route that is no longer shown (`desk_doers.py:546-551`). The view clears it only when it paints (`field_qt.py:1256-1257`).
- `menu_choose` walks whatever root menu is open and never checks the target (`desk_doers.py:979-983`).
- `asked` is hard-coded to True at `desk_doers.py:662`, `field_page.py:324` and `field_page.py:517`.
- `hand_step` calls `field_page.do`, which puts the steps page over the work (`desk_doers.py:1276-1278`).
- `desk_hers` refuses owner-only acts (`desk_acts.py:311`). It accepts `by`, because `check` accepts it.
- `hand_approve` takes the latest waiting card (`desk_doers.py:1318-1322`).
- The Approve tooltip prints a key: "in the Field, G does the same" (`shell2.py:2035`).
- The console prints "Press Enter again … Esc" (`console_qt.py:534`). This is a key on screen, and the owner will see it when typing an approve-scope operation such as `bounds.set`.
- `local_brain.py:623`, `:631` and `:633` say "Programs" in errors that reach the screen.

**The model path and the I05 check**
- The `brain.ask` modes are chat, plan and choice (`local_brain.py:57`). Choice mode answers `{"choice":n}` in 24 tokens with the last 2 messages (`:892-897`).
- The fit rule is prompt + output + 32 ≤ context (`slate_stream.py:67`).
- Every generation consumes the slot claim. The prompt is reused only when the claim's key matches (`:69-78`), and only on `PINNED_SINGLE_SLOT` (`:20-21`).
- In adaptive_work, the duplicate guard raises at `:435`, before `used` is charged at `:446`. So handing back evidence there costs nothing.
- The method's declarations are 6 enums plus `basis` (`checked_methods.py:10-15`).
- **New finding.** I05's acceptance would mislabel a run that uses deduction:
  - its failure words say "model-selected" (`joined_model_checks.py:68-69`);
  - it counts `validated_model_generations = 2*len(decisions)` (`:93`);
  - the frozen spec says "no model choice injection" (`:95`).
  Arms B need their own wording and a count of real generations.
- Master Stop exists on the service side (`agent_loop.py:81-83`, `:833`).

## 1. The conditions engine (decided)

**One engine**, `workbench/goals.py`.
- **While she works**, the goal set lives in session state `her_plan` (≤ 64 KiB) (from B). Nothing is written to the owner's records.
- **At the finish**, `goals.keep` writes it as `ledger.goal-set/1`, kind `goal_set`, with history. `goals.keep` is execute scope and on HERS_SHOW. At Ask first it waits like any change.
- **Inside adaptive work**, the goals live in `state['conditions']`.

**The goal's fields** (A's names):

| Field | Values |
|---|---|
| `id` | C1… |
| `statement` | from a template, never the model's words |
| `template`, `params` | |
| `aim` | achieve, or decide (with `of`/`join`, Belnap: in an "and", false wins) |
| `mode` | seen (a desk milestone) or hold |
| `persist` | for desk goals that must still hold at the end (tidy; "leave the comparison open") |
| `form` | desk, relation, text, state, artifact, question (question: 35B only, settled only by the owner) |
| `bind` | {address, cell, revision, unit, role: measured, limit, …} |
| `bounds` | references to bound records |
| `evidence`, `state`, `stale` | |
| `slack` | {lo, hi, unit, exact} |
| `depends` | |
| `origin` | OWNER, HER, DEDUCED or WORK_ORDER |
| `agreed`, `agreed_by` | |

**States.** Internally: OPEN, HOLDS, FAILS, UNDECIDED, SEEN, plus the `stale` flag. On screen: open, holds, does not hold, cannot tell, shown, recheck (the old verdict beside it in quiet ink). The engine never uses "held", "BROKEN", "condition" or "interval" as names, because the code already gives them other meanings.

**Assessment** follows A §1.3. Desk goals use `desk_scene.lookup` and `matches`, so a scene's `expect` and a desk goal are one language. Desk evidence is the paths that matched plus a digest of the `read.desk` subtree, taken at the moment the goal held. A seen goal is not checked again unless it is `persist`.

**Two safety rules** (from A):
1. A goal's words come from its template.
2. A cell bound with role `measured` is never added by an achiever that the planner chooses for that goal.

**Staleness.** Revisions are compared cheaply. If the bound value is unchanged, the read just rebinds. Otherwise the planner re-evaluates everything downstream of the changed node, in topological order. The ripple already separates "work it again" from "confirm".

**The finish rule** (A §1.4) applies to the desk and to work alike.

**Kernel operations:**

| Operation | Scope | Notes |
|---|---|---|
| `goals.check`, `goals.get`, `goals.list` | read | |
| `goals.keep` | execute | on HERS_SHOW |
| `bounds.get` | read | |
| `bounds.set` | **approve** | also listed in ALWAYS_ASKS with the words "a tolerance is yours to say: it decides what I conclude" |

There is no `goals.make` or `goals.agree` operation. Agree and Strike are words on the card, clicked by the owner.

**How it is shown**
- **Her hand card**, one per turn, in her column.
- **The WorkBlock** gets four rows for work goals:
  - Doing now: the goal being worked.
  - Found: k of n hold or are decided.
  - Needs you: questions and escalation cards.
  - Inspect: the goals.
- **Slack** is shown in words, rounded outward, with the exact rational kept beside it.

## 2. Operators (decided)

**Operator records.** `workbench/desk_ops.py` holds `Op(name, pre, add, delete, certain, observe, cost)`.
- The fluents are the map's, plus the `read.desk` additions in §5.
- Objects are restricted to the sheets the goals name plus the current selection.

**The planner's acts this pass: 30.** Excluded are:
- the owner-only acts;
- `look.set`;
- `point.move` (keys only);
- `go.app` (it can make a document);
- `head.meter` and `type.room`.

The owner's line door keeps every act.

**Effects and costs**
- Certain effects are the ones the doer checks itself (the map's list). Any other effect is unknown until the next read.
- Costs in seconds are a running average (EWMA) of the journal's `seconds` per act, seeded from the probes: `go.files` 0.63, `then.keep` 0.78, `sheet.compare` 0.78, others 0.5.

**Kernel operators** use the classes both designs agree on: sense, simulate, change, check, compute, owner's, swap.

**Rules:**
- Reads are a set.
- A refusal is not a no-op, so read again after it.
- An op that deletes a `persist` goal cannot be last in a plan.
- The owner's input, or a background refresh, makes every fluent unknown. Read before every act.

**Conformance test** (from B): for each planned act, from 3 sampled states on the offscreen bench window, predict the state, run the act and compare with `read.desk`. Certain effects must match exactly.

## 3. The planner (decided)

**Desk layer: forward uniform-cost search** from the state read now (from B), not backward A*.
- Methods are tried first. They are HTN methods written as parameterised scene fragments `{act, args, expect}` (A's form), with gap fills up to depth 4.
- Budgets: ≤ 4,096 expansions, depth ≤ 12, ≤ 64 literals. Past them the answer is TOO_FAR, said as "I could not plan that within twelve acts."
- Ties break on cost, then length, then act names, so tests are stable.
- Target: under 50 ms per plan, with a test bound of 0.5 s.
- **Several goals from one request** are planned jointly first. If that fails, they are planned one after another, in the order the owner said them (A).
- **A standing `persist` tidy goal**, no popups open, ends every turn.

**Work layer: regression over Kernel operators** to a horizon of 3, with reads taken as one set.
- For numeric goals the weakest precondition comes from `math_model.affine` and `sweep`. Example: v ≤ 1/2 A, or 50/101 A with the rail recorded at ±1 %.
- Products of two unknowns go to bisection.
- A weakest-precondition result is offered as a what-if (a read), never set.

**Method library v1:**

| Method | What it does |
|---|---|
| `see.place` | go to the Field, Today or Files |
| `shown(s)` | go.field, point.zoom whole only if s is not in sight, point.sheet |
| `traced(s)` | shown(s), then sheet.trace |
| `side_by_side(s)` | shown(s), then sheet.compare |
| `both_shown` | side_by_side, then select and trace the second sheet |
| `see.menu` | head.open, then tidy |
| `line.count`, `line.keep` | Files → menu.open → then → keep → count → end |
| `set.cell` | select the sheet, set the cell, verify by a read |
| `make.file` | only from the owner's exact words via `stacy_hand.made`; never model text |
| `check.limit` | read the value, the limit and their bounds; assess; rank by value of information |
| `recheck.page`, `recheck_after_set` | recheck a page; recheck after a set |
| `tidy` | close what is open |
| `put_back(snapshot)` | navigation only, back to the snapshot |
| `i05.application_chain` | preview → instantiate → run → result → prepare → run → result |

**Deduced or asked.** Graphite deduces the acts, their arguments, when to read, recovery, returning existing evidence, interval verdicts, value of information, finishing and tidying. The model gets only GOAL, plus NEXT on real ties (§6). The owner gets agreement, every change that is not hers, tolerances, measurements this computer cannot make, and model swaps.

**A meaning tie whose branches are only reads is not asked.** Both branches are evaluated and shown, because asking would have zero value of information. Example: Rev A and Rev B both on the desk; one holds and one does not, and both are shown.

**The lookahead view** (B §3.5) feeds the NEXT turn and the card's "next" rows.

## 4. Execution (decided)

**`workbench/her_hand_qt.py`, class `HerHand`.**
- A QTimer ticks on the GUI thread. Each tick does at most one window act, one Kernel operation, or one poll of a model job.
- All the logic is pure Python in `planner.py` and `goals.py`.
- At least 300 ms pass between window acts, so the owner can follow. A scene's `given.pace` can lower this.

**Verify by class** (B's table). Evidence comes only from reads. `changed` means "attempted", not "landed".

**Repair:**
- by refusal code, as in A's table (NOT_HERE, UNSENT/PENDING, DIALOG, FAILED);
- an act refused twice in a turn is dropped for the rest of that turn;
- an effect that differs from what was expected is absorbed, and the planner plans again;
- a write that times out is probed before any retry:
  - `field.set` by `office.get`;
  - adaptive working writes by `continuing_work.reconcile_apply`;
  - desk acts by `read.desk` plus the turn's journal line.

**Repeats:**
- A repeated read returns the earlier observation ("Already known · O<n>"). Nothing runs and nothing is charged.
- A repeated navigation on the same abstract state stops the turn, with words.
- For investigations, the planner checks `input_key` itself before dispatching. `investigations.execute` is unchanged.

**Stop:**
- **One flag per host.** It is set by Stop on the card, the new owner-only act `hand.stop`, Master Stop, and **the owner's touch**.
- **What counts as a touch:** a MouseButtonPress, KeyPress or TouchBegin whose receiver is a QWindow (from B), unless the press lands inside her card. Wheel and hover do not stop her, so the owner can scroll to read the card (from A).
- **Fallback:** if the two-direction test fails on the pinned Qt, use A's marker instead: wrap each synthetic send in `with hand_pressing(host):`.
- **Where the flag is checked:** in `run` before each act, in each press of `key`, each character of `type_text`, each segment of `walk`, and in `wait_until`.
- **On a stop:** the act refuses with STOPPED, between presses, never halfway through a click. The turn is paused, and the card offers Continue and "Put my window back".

**The dial:**

| | Ask first | Do and show | Free hand |
|---|---|---|---|
| Reads | done | done | done |
| Navigation | offered | done | done |
| Changes on HERS_SHOW | wait | done, with Undo | done, with Undo |
| Changes on HERS_FREE only | wait | wait | done |

- ALWAYS_ASKS, `brain.model.use`, `bounds.set` and `*.review` wait at every place.
- Owner-only acts are never hers.
- Turns started by her own noticing: none in this pass.

**Agreement** (from B):
- A desk-only turn runs without agreement at Do and show and at Free hand, because it is shown and can be put back.
- A change, or a finding reported as final, needs agreed goals.
- At Free hand, a goal shown counts as agreed, and Strike re-plans.
- At Ask first, Go ahead is the agreement.

**Budgets:**

| Budget | Limit |
|---|---|
| Desk turn | ≤ 24 acts; ≤ 120 s, not counting waits for the owner; ≤ 6 plans; ≤ 2 surprises in a row |
| Work | `DEFAULT_BUDGET`: 40 steps, 600 s |
| Model turns per plan | ≤ 12 |

**Progress.** Φ = Σ (2·open + cannot tell + recheck), with the width of each slack as a tie-break. Each step must lower Φ, or be a read that narrows a slack. Two steps in a row that do neither are a stall, and a stall escalates.

## 5. Her door (decided)

**`desk_doers.run(door='her')`:**
1. Outside a turn, the code stays NOT_OFFERED, with true words: "Stacy's hand acts only inside a turn you started."
2. STOPPED if the stop flag is set.
3. Owner-only acts are refused at the door. `desk_hers` also checks owner-only first.
4. `by` is refused at the door, and `desk_hers` returns False for it.
5. `check` the arguments.
6. **`hand.step`** takes its line from `field_do.steps_for`. A read step runs as a Kernel read, and its answer goes on her card; the window does not move.
7. `desk_hers` rules on the act. An act that navigates and is not hers is OFFERED: a journal state, and the act does not run.
8. A change goes to `stage_change(asked=turn.asked)`.

**Context and journal:**
- `Ctx` gains `asked`, `expect_target` and `door`.
- `walk` refuses NOT_HERE when the open menu's target is not the expected one.
- The journal gains the states OFFERED and STOPPED. Origin is `stacy-hand:<turn>`; the correlation is `<turn>:<n>` when the Kernel gives none.
- The Kernel principal is unchanged (`operator()`). The journal's origin and the trail say the act was hers.

**New owner-only acts:** `hand.stop` and `hand.putback`. That makes 42 acts, with 35 still exported. `test_forty_acts_and_their_marks` is updated.

**Ask first.** The card lists the whole plan. The owner's word authorises **one segment**: the moves up to the next goal or the next change. Go ahead on the card, or `hand.approve` (which already takes the latest waiting card), authorises exactly those acts, matched by fingerprint. The offer is voided by any owner touch, or by a repair that changes the acts; the new acts are then offered again.

**What the owner sees:**
- **The card** (A's layout):
  - goal rows with their state and a "seen" word that opens the evidence;
  - numbered act rows, each next, done, offered, waits for your Approve, refused or stopped;
  - Stop, Go ahead, and "Put my window back";
  - a closing line such as "Done in 5 acts; both hold".

  Each row's words are `ACTS[name].words` with the arguments filled in. They print no key, call the line language "a line", and say "Apps". The card draws with the appearance's faces and names no font, so #50's typewriter face carries over.
- **The pointer.** `HerPointer` is an overlay that mouse events pass through. In S1 it draws a ring at the press point 200 ms before the press. S3 adds a 200 ms glide. With reduced motion the ring is held still. Her door does not use keys forms.
- **The hologram.** `HerHand.state_changed` emits idle, thinking, acting, waits or stopped. #50 maps these to the static. With reduced motion the static is still.
- **The trails.** A separate desk trail keeps 200 entries; `type.put` is recorded by its length only. "What I did" shows both trails interleaved by time, with Undo only on data entries.

**Undo:**
- `field.set` and files she made: unchanged.
- **DELETE.** The operation stays `files.trash`, because renaming it would fall under `*.delete` in ALWAYS_ASKS (`stacy_hand.py:50`).
  - `takes_back('files.trash')` returns `/files.restore {"id"}`.
  - `UNDOES` gains `files.restore`. `undo_allowed` accepts exactly `{'id'}` with 32 hex digits, and no guard is needed (§0.1).
  - Until this lands, her door makes `hand.trash` wait at every place.
  - On screen the word is DELETE: "DELETE “x” — Undo brings it back."
- **The window:** "Put my window back" is a desk plan to the snapshot. The writing line is cleared only if its words are still hers.

## 6. The model's contract (decided)

**On the desk: two turns**

| Turn | Schema | Asked when | Limits |
|---|---|---|---|
| **GOAL** | new `brain.ask` mode `pick`: `{"pick":[k…]}`, 1–3 unique integers in 1..K+1 (K ≤ 16 candidates, the last option "none of these") | `hand_words` finds no single full match, and only when the request names a desk verb or a sheet in sight; every other Talk request keeps its present path | prompt ≤ 1,200 tokens, output ≤ 32, no dialogue history, 60 s deadline |
| **NEXT** | existing choice mode `{"choice":n}` | ≥ 2 options that do not dominate each other. This covers A's CHOICE (a meaning tie whose branches move the window or change data) and OPTIONS (no operator achieves the goal) | prompt ≤ 1,600, output ≤ 16, 60 s |

- For GOAL, "none" chosen together with other goals is invalid.
- Candidates are deduplicated by their predicate. For example, comparing from Rev A or from Rev B gives one goal.

**In adaptive work: two more**
- **PROPOSE** for the I05 mapping only, with numbered enums (B's schema). The coordinator supplies `method`, `method_revision`, the binding and `basis`.
- **WORDS**, only for FINISH: ≤ 400 characters, with the citations fixed by the coordinator.

**Never in this pass:**
- PROPOSE on the desk: OTHER leads to "I don't have a way to do that on the desk yet", and plan mode still answers in words.
- File text written by the model.
- A `why` or `uncertainty` field in any new turn.

The card's words are always templated from evidence.

**A wrong or late answer:**
- **Invalid:** no act runs.
- **Late:** if the top option is a read, or a navigation that is hers now, it is taken as the default and recorded as `default`. A change is never taken by default. Otherwise the card says "I could not settle what you meant in time" and lists the deterministic candidates as words the owner can pick.
- **A struck goal:** the pair (request words, struck goal) is recorded in the instruction matrix as data.

**Prompt reuse** (from B):
- The cache key covers the stable head only.
- The view is written as lines, not canonical JSON, whose sorted keys would change the head.
- The claim is published again after each validated answer.
- This works only on PINNED_SINGLE_SLOT, and reuse is measured, never assumed.

**The 35B profile** applies with a context of at least 8,192 and the 35B's file size:
- 7 options instead of 5;
- a horizon of 5;
- one `question` goal allowed.

The schemas are otherwise the same.

**At 4,096 context**, the expected time here:

| Turn | Expected here |
|---|---|
| GOAL | ≈ 15–27 s |
| NEXT | ≈ 13 s with the prefix reused, ≈ 26 s cold |
| PROPOSE (the mapping) | ≤ 2,400 prompt tokens, about 70 output, ≈ 35–53 s |

## 7. Intervals and value of information (decided; the designs agree)

**Where a tolerance lives.** `ledger.bound/1` holds one bound per (address, cell), bound to the sheet's revision.
- Only the owner sets it, through `bounds.set` (approve).
- She may propose one from a page's own words, as a card that waits. A bound she invents is the worst failure this design could have.
- The owner can say it in words, such as "B5 is good to 5 ms", which becomes a staged card.
- **On a new revision:** if the bound cell's value is unchanged, the bound is rebound; otherwise it shows "recheck".

**`bounds.py`:**
- Exact `Fraction` intervals in base units, built with `unit_spec` and `rational`; never the float `measure()`.
- The decision rule: holds if lo(S) ≥ 0; does not hold if hi(S) < 0; otherwise cannot tell.
- Division by an interval that contains 0 gives "cannot tell".
- Endpoints are widened outward past the 2048-bit cap.
- Display rounds outward.

**Decisive share** is computed exactly for a predicate that is monotone in each input and uses each once. Otherwise it is a sound lower bound from bisecting into 64 pieces.

**Value of information:**
- It is 0 once a goal is decided. Weights follow Belnap: a false conjunct decides an "and".
- A new reading is intersected with the old one. An empty intersection gives "cannot tell: the two readings cannot both be right".
- With no bound recorded, she reports the break-even instead.

**Which limit applies** is bound by the owner or by a goal, and is never deduced. When it is ambiguous, both limits are shown.

**The numbers, re-derived:**

| Goal | Result |
|---|---|
| C1B, pulse against Rev B | 80 − [105, 115] = [−35, −25] ms: does not hold, robustly; break-even e < 30 ms |
| C1A, pulse against Rev A | [5, 15] ms: holds |
| C2, startup power against 8 W | P = [7.56756, 8.03556] W, S = [−0.03556, 0.43244] W: cannot tell. Decisive share for current 6989/7878 ≈ 0.887, for voltage 3089/3978 ≈ 0.777, so ask about the current first. Break-even (1+r_V)(1+r_I) ≤ 40/39, giving r ≤ 1.27 % each |
| C3, settled power against 6 W | S = [2.538528, 2.740128] W: holds; break-even 25/14 |
| HOLD = C1B ∧ C2 | does not hold, so the value of information of V and I is 0 for it |
| Weakest precondition | 1/2 A, 50/101 A, 200/303 A |

The card's words for C1B are A's §7.3 text.

## 8. Escalation (decided)

**Triggers:**
- two invalid or late turns;
- "none" chosen while the deterministic candidates are tied;
- a stall;
- self-consistency disagreement;
- PROPOSE refused twice;
- an adaptive decision that fails.

**The ladder, cheapest first:**
1. **Narrow.** Deduce what is now unique, drop options under 10 % of the top, use a single phase, and reuse a SELECT that already landed under the same binding.
2. **Think.** By default, A's notes-then-strict turn. B's per-call thinking is used only if a build check shows the server applies the JSON schema after the reasoning block.
3. **Self-consistency.** k = 3 turns with the order rotated; take what 2 of 3 agree on; otherwise ask the owner.
4. **A batched model swap**, staged by the planner and never by the model, as a `brain.model.use` card (approve scope) that waits at every place.
   - The turns that need the bigger model are queued, so the card appears once.
   - The memory-admissibility gate runs `schedule_math.evaluate` in process, with the resident model as an allocation and the KV cache as explicit allocations. The card proposes only a feasible schedule: 37.54 GB INFEASIBLE, against 24.54 GB FEASIBLE with the 35B released at 300 s.
   - A `brain.restore` card follows the batch.

**Adaptive work** escalates only to rung 3 in this pass, then waits with "needs a larger model".

**Not in this pass:** vision models. The live mechanism test is a 2B → 4B swap here.

## 9. The I05 experiment (decided)

**Arms**, with the same model file, configuration, cases, budgets and threads:

| Arm | What it is |
|---|---|
| **A** | today's loop; its code path is untouched |
| **B1** | **the owner's experiment as he wrote it.** The model is shown the open conditions and a lookahead and picks every step; repeats get existing evidence back; writes are checked for what landed; finish needs every condition |
| **B2** | B1 plus deduction wherever exactly one ready producer has settled arguments, recorded as `COORDINATOR_DEDUCED`; deduction gains no authority |
| **B2@4096** | B2 at 4,096 context |

**The B spec.** Arms B switch on only when the work order carries `plan['adaptive']['conditions']`. They have their own `ledger.i05-conditions-spec/1`, which declares:
- the conditions K1–K3 and K3′;
- deduction;
- the evidence handback;
- the landed check;
- the finish rule.

**Acceptance.** The checks are the same, with two fixes for arms B:
- the failure words say "selected by the model or deduced by Graphite (recorded which)";
- `validated_model_generations` comes from the turn records.

**Runs**
- Here: the 4B, three repeats per arm, interleaved, with the page cache dropped (`DONTNEED`) before each run.
- On the ThinkPad: the 35B through the campaign runner at the owner's context setting, three repeats per arm.

**What is measured:** the union of both designs' measures, including the B1 rate of picking the planner's top option.

**Pre-registered expectations**, written so they can be wrong:
- A fails again at decision 2 on the 180 s wall.
- B2 passes all three cases with ≤ 3 model turns per case, each under 60 s here, using under half of A's model tokens.
- B1 passes with 7–9 NEXT turns of 13–30 s, picking the top option ≥ 80 % of the time.
- No arm B ever dispatches a repeat or finishes with an open condition.

A failure is reported as one, with the step that failed.

## 10. Build order

### S1, the first slice: "Her door on the Field" (one builder session)

**In this slice:**
1. **`read.desk` additions:** `where.keyboard`, `line.ours`, `line.pending`, `talk.waiting`, `field.came_from`, `field.in_sight`, `field.objects` (≤ 60), and `route_said` returning None unless the route's owner is the selected sheet.
2. **`desk_ops.py`, the Field subset:** `go.field`, `point.zoom` whole, `point.sheet`, `sheet.trace`, `sheet.compare`, `sheet.close`, `menu.close`, `read.desk`.
3. **`planner.py` desk layer:** forward search, the methods `shown`, `traced`, `side_by_side`, `both_shown`, `tidy` and `put_back`, and the budgets.
4. **`goals.py`, desk form only:** seen and persist goals, evidence, the finish rule, Φ.
5. **`hand_words.py`, deterministic matching:**
   - trace, or "where X comes from";
   - show or select X;
   - "X beside its other revision";
   - close what is open.

   Sheets are matched by `find_sheet`'s exact-then-unique rule. The GOAL candidates come from the same place.
6. **`her_hand_qt.py`:** the tick, the card, the touch filter, the stop flag, the ring pointer, `state_changed`, the snapshot and put back, and session state `her_plan`.
7. **`SlateFace.plan_asked(text)`**, inserted after `run_asked` (`shell2.py:2563`).
8. **`desk_doers.run(door='her')` for navigation and reads only.** In this slice the door refuses change acts with NOT_OFFERED: "Changes on the desk through my hand come next; ask me in words." The journal gains OFFERED and STOPPED, and the stop checks go into the press loops.
9. **`desk_acts`:** `hand.stop` and `hand.putback` (owner-only); `desk_hers` refuses `by`; `hand.approve` takes the latest offer.
10. **`stacy_hand`:** `why_waits` says "my hand is at Ask first" at Ask first; `DESK_TRAIL`.
11. **`local_brain`:** mode `pick`.
12. **Words fixes:**
    - the Approve tooltip loses its key (`shell2.py:2035`);
    - the console's approval words lose their key names (`console_qt.py:534`), becoming "Send the same line again to run it as written; change it to leave it";
    - "Programs" becomes "Apps" in `local_brain.py:623`, `:631` and `:633`.
13. **`desk_scene`:** a `say` step `{say, dial?, until: done|waits|stopped, seconds, touch_after?, expect}`. `expect` can read `turn.*`. `touch_after` sends a real press to the window through QTest's QWindow overload.

**Tests** (`tests/test_desk_planner.py`, pure Python; `tests_integrated/test_her_hand.py`):

| Test | What it checks |
|---|---|
| hidden state | the new `read.desk` parts are present and typed |
| route | `route` is None once the selection moves |
| door outside a turn | NOT_OFFERED (T:575 kept) |
| door refusals | owner-only and `by` are refused |
| Ask first | the act is offered: journal OFFERED, `read.desk` digest unchanged |
| changes | change acts are refused in this slice |
| conformance | 8 acts × 3 sampled states; certain effects match exactly |
| planning | from Today, a trace of Bench = 2 acts; Rev A beside Rev B plus a trace of Bench, jointly = 5; at 150 % zoom, point.zoom comes first; with `whole` read true, it is dropped; owner-only acts never planned; TOO_FAR at the budget; deterministic; under 0.5 s |
| finish rule | evidence recorded with the read digest; no popups at the final read |
| repeats and budgets | a repeated navigation stops the turn; budgets hold |
| touch filter | all S1 acts by pointer trip it 0 times; one window press trips it once; a press on her card does not |
| stop | stops between presses |
| put back | returns to the snapshot |
| `pick` mode, with a fake worker | the schema; "none" with others invalid; out of range invalid; late falls back to the deterministic candidates; no act runs on an invalid answer |
| words | the key-literal check (T:243) extended to the new files, the card words, the tooltip and the console text; no "Programs" |
| act count | 42 acts, 35 exported |

**Scenes:**
- **P02, "Her door on the Field".** `say` "trace 07 Bench readings and put Rev A beside Rev B".
  - At Do and show, by pointer, and again with less motion: FINISHED; every goal shown; every envelope `door: her` with `changed: []`; no popups at the end; no `stacy_trail` entry; `turn.acts` ≤ 6.
  - At Ask first: one offer, the desk unchanged, then `hand.approve` → FINISHED.
- **P03, "You take the window back".** The same request with `touch_after: 2` → STOPPED, 2 acts done, journal STOPPED. Then `hand.putback` → the surface, the selection and what is open over the work equal the snapshot.
- **P01** still passes in all four runs.

**The 4B check.** `workbench/hand_model_checks.py`, marked `needs: model`. The 4B Q4_K_M at 4,096 context, 4 threads.
- **Three requests**, with their expected sets frozen in the file before it runs:
  1. "show me where the bench readings come from" → {traced Bench};
  2. "where do the bench readings come from, and put the limits side by side" → {traced Bench, side by side Limits}, in that order;
  3. "what's for dinner" → none.

  The check asks GOAL directly, bypassing the deterministic match, so it measures the model.
- **Passes when** all 3 are exact, every turn takes ≤ 60 s, prompts are ≤ 1,200 tokens and outputs ≤ 32.
- **Records** prefill and decode tokens/s, `cache_n`, and any over-picking.
- **Also:**
  - the 2B is run for the record, not as a gate;
  - P02-model, a `needs: model` variant with a request the matcher leaves ambiguous, must show `turn.model.seconds` ≤ 60.

**Done when:** P01 is unchanged in 4 runs; P02 and P03 pass in 2 runs each; the 4B check passes in 3 runs.

### Later slices, in order

**S2. Conditions over data: pure maths, no Qt**
- **Contents:**
  - `bounds.py`;
  - the relation, text, state and artifact forms;
  - `ledger.bound/1`;
  - `goals.check`, `goals.get`, `goals.list`, `bounds.get` and `bounds.set`;
  - weakest-precondition boundaries;
  - decisive share, break-even, value-of-information ranking;
  - the admissibility helper.
- **Tests:**
  - every §7 number exact, as a Fraction, with no float anywhere;
  - property tests of the interval laws;
  - Belnap;
  - candidates for After Hours 07 give C1A, C1B, C2, C3 and C4, and nothing with mismatched units;
  - rebind on an unchanged value;
  - repair in topological order.
- **Ships:** the owner records ±5 ms (it waits for Approve), and the answer is "does not hold, over by 25 to 35 ms".

**S3. Changes and the rest of the desk under her door**
- **Contents:**
  - the DELETE Undo;
  - changes through `stage`, with `asked` taken from the turn;
  - `hand.cell`, `hand.write`, `hand.trash` and `hand.step`;
  - the landed probe for `field.set`;
  - the menu, Files, then and type acts, with the expected-target check;
  - the `line.count` and `line.keep` methods;
  - the desk trail;
  - the gliding pointer.
- **Scenes:**
  - P04, "P01 by her words": `turn.acts` ≤ 13.
  - P05, "Changes under her hand":
    - B3 to 300 at Do and show is done, with Undo; at Ask first it waits;
    - DELETE, then Undo restores the file;
    - rename waits;
    - a page recheck waits at Do and show.

**S4. Work goals on the desk, and NEXT**
- **Contents:**
  - `check.limit` (both limits shown, no question asked), the what-if boundary, `recheck_after_set`;
  - options ranked by value of information on the card;
  - the NEXT turn, and the late-answer default;
  - repair after a revision;
  - `goals.keep`;
  - the WorkBlock rows;
  - the prompt-reuse key.
- **Scenes:**
  - P06, "Limits";
  - P07, "What would let settled power stay in": "up to 500 mA", nothing changed;
  - B5 := 100 → recheck → the new states.
- **4B check:** a NEXT turn on After Hours 07 with C2's bounds recorded, ≤ 60 s.

**S5. The I05 arms.** A, B1, B2 and B2@4096 run here. The ThinkPad kit is prepared for the 35B.

**S6. Escalation**
- Notes-then-strict, and the thinking check;
- k = 3 self-consistency;
- the swap card with its schedule;
- the restore card;
- a live 2B → 4B swap here.

**S7. Model proposals through her hand** (pending #35). Run on a proposal card goes through `stage(asked=True)`, so each proposal gets her trail and Undo. Nothing is removed.

**Not in this pass:**
- turns started by her own noticing;
- a Kernel principal of her own;
- keys forms for her;
- PROPOSE on the desk, and file text from the model;
- swaps inside adaptive work, and vision models;
- bounds she sets;
- measurements made by Graphite;
- non-uniform priors;
- plans that span sessions;
- renaming `files.trash`;
- changing `investigations.execute`;
- #50's look itself.

What always asks still asks, and nothing is removed.

### Owner decisions to confirm

1. Go ahead lets her do the moves up to the next goal or change, and touching the window voids it.
2. Her changes keep your identity; the journal and the trail say they were hers.
3. DELETE gets an exact Undo; until then it waits.
4. An ambiguous limit shows both answers.
5. Tolerances are yours only.
6. Touching the window stops her; scrolling does not.

PART 2: THE OWNER PAGE

**Kasandra's hand on the desk: what comes next**

**What she will do**
You ask her in Talk, in your own words: "trace the bench readings and put the limits side by side." She works out what must be true when she's done, then moves your window there one step at a time. After each step she looks at the window again to check it worked. When everything she promised is true, she says so and shows the proof. She leaves no menus open behind her.

**How the maths makes a small model reliable**
The model never drives. It gets one small question: "which of these numbered goals did you mean?" It answers with a number or two, in under half a minute here. Graphite deduces the rest:
- **Working backward:** it starts from the goal and finds the shortest set of moves that gets there.
- **Look a few steps ahead, do one:** it plans ahead, does one step, looks, then plans again, so a surprise never runs on.
- **Exact sums, and ranges when you give one:** if you record how precise a reading is (110 ms, give or take 5), she works with the whole range. Against an 80 ms limit that is over by 25 to 35 ms whatever the true value, so she won't ask for a finer measurement, because it couldn't change the answer. When a reading could change it, she asks for the one most likely to settle it.
- **No repeats:** she never repeats a read that hasn't changed. She points to what she already found.

**What you see and control**
- **Her card** in the right column. It lists each goal (open, holds, does not hold, cannot tell) and each step (next, done, waiting).
- **A small ring** where she is about to click. Her picture's static can show when her hand is moving.
- **The dial still rules.** At Ask first she lists the moves and waits for your Go ahead. At Do and show she moves and tells you.
- **Touch the mouse or keyboard** and she stops before her next click. "Put my window back" returns it as it was.
- **Undo stays.** Changes to sheets and files keep their Undo, and DELETE gets an exact Undo too. Anything that can't be undone still asks, every time.
- **Tolerances are yours.** Only you set one. She may suggest one, and it waits for you.
- **If the model can't decide,** she thinks again, then asks three times. Only after that does she suggest a bigger model, as a card you approve, and only if it fits in memory.

**Tested here, and on your ThinkPad**
- **Here,** on a 4-core machine with the small 4B and 2B models: every rule above, scenes that play her hand on the bench window, and a timing check. Each question to the model must be answered within a minute.
- **On your ThinkPad,** the 35B runs the same scenes and the comparison you proposed: the I05 case that got stuck, run with today's loop and with the loop that has goals, a short look ahead and proof at the finish. Three runs each, timed, with a note of whether she finishes with proof.

**First step:** her hand on the Field only, moving and looking. She makes no changes yet.