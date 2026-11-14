# Kasandra's hand on the desk, with a planner over conditions

Design for the next build pass. Angle: **the model stays in the loop.** At every point where there is a real choice, the model proposes the next step. It works from the conditions still open and from a short lookahead that the planner computes and shows it. The planner checks each proposal, repairs it or refuses it. When a step would repeat, the planner hands back the evidence it already has. Wherever a step can be deduced, the model is not asked.

All code references are to HEAD d1df337. I checked each claim against the code. Section 11 lists where the readers' maps needed correcting.

---

## 0. The shape on one page

- **One conditions engine** holds "what must be true when she is done". It lives in `workbench/goals.py` and `workbench/bounds.py`, with Kernel operations in `workbench/goals_service.py`. A condition can be:
  - a desk milestone, checked by `read.desk`;
  - a data relation, checked by Kernel reads in exact rationals, or as an interval where the owner has recorded an error bound;
  - a record's state;
  - a check result;
  - an open question that only the owner can settle.
- **One planner** lives in `workbench/planner.py` and `workbench/desk_ops.py`.
  - It works backward from the open conditions over a finite abstraction of the window and the records.
  - It looks ahead H = 3 steps.
  - It ranks first steps by value of information per second.
  - It deduces every step that has exactly one admissible answer with settled arguments.
- **The model is asked only at real choices:**
  - **GOAL**: pick the conditions from candidates the planner built.
  - **NEXT**: choose among at most 5 ranked next steps. Some of these are questions for the owner.
  - **PROPOSE** (rare): name an operation that is not in the list. The planner then checks it, repairs it or refuses it.

  The model never sees the 35 exported acts (`plan_variants` is 6,327 bytes, `tests_integrated/test_desk_acts.py:238-239`). It never writes prose that the planner can write from evidence.
- **One act at a time, then read back.**
  - Window acts go through her door, `desk_doers.run(door='her')`.
  - Data changes go through `SlateFace.stage` (`shell2.py:2006`), so each keeps its card, trail line, Undo and what-always-asks rule.
  - A repeated step gets the earlier evidence back and runs nothing.
  - The owner's touch, or Stop, halts her before her next press.
- **What the owner sees:**
  - a plan card at the top of her column. Her column is the right one, which gets the room the portrait leaves when the 0.8.3 look pass moves the picture to the lower left (#50);
  - her pointer moving on the window;
  - the trail and Undo, as today;
  - her state as the hologram's static.

**Why this shape.** On this machine (4B Q4_K_M, 4 threads) prompts read at 56–97 tokens/s and answers generate at 3.6–5.6 tokens/s (LOG:32-111).
- Today one decision takes two model phases: 148.2 s for I05 decision 1 (R2:1436). Decision 2 hit the 180 s wall with about 200 of its roughly 240 argument tokens written (LOG:113).
- In this design a NEXT turn is at most 1,600 prompt tokens and at most 16 output tokens: about 13 s when the prompt prefix is reused, about 26 s cold. In I05, every step after the mapping can be deduced (section 9).

---

## 1. The conditions engine

### 1.1 The record

In code a condition is a "goal"; on screen it is "what must be true". Goals live inside a goal set.

```
ledger.goal-set/1          (Project Desk kind 'goal_set', with history, written only by goals.keep)
{schema, id, revision, owner, created,
 request:  "<the owner's words, ≤ 400 chars>",   word: "<Talk message id, or 'noticed'>",
 place:    'ask' | 'show' | 'free',               # the dial when the turn began
 state:    'proposed' | 'working' | 'waits' | 'paused' | 'done' | 'stopped',
 goals:    [goal, …],                              # ≤ 8 agreed + ≤ 4 derived sub-goals
 observations: [{alias:'O1', kind:'kernel'|'desk', op, args, record, revision, digest, at, summary≤200}],   # ≤ 64; last 24 shown
 turns:    [{n, kind:'goal'|'next'|'propose'|'words'|'deduced'|'default'|'returned',
             model_id, prompt_tokens, cached_tokens, output_tokens, seconds, pick, refusal}],
 snapshot: <abstract desk state at the turn's start>,          # for "Put the window back"
 phi:      [int, …],  budget: {steps: 40, seconds: 600}}       # agent_loop.DEFAULT_BUDGET, agent_loop.py:122

goal:
{id: 'C1'…'C12', words: "<≤160 chars, shown>", origin: 'OWNER'|'HER'|'WORK_ORDER', agreed: bool,
 mode: 'hold' | 'seen' | 'decide',
 form: 'relation' | 'state' | 'check' | 'desk' | 'question',
   relation: {expression: 'pulse <= limit',                     # math_model.compile_expression(constraint=True)
              bind: {pulse: {address:'office:owner:db5f…', cell:'B5', unit:'ms'},
                     limit: {address:'office:owner:4f35…', cell:'B4', unit:'ms'}}},
   state:    {read:'documents.get', args:{id}, path:'source_state.state', equals:'CURRENT'},
   check:    {line:'<a line>', expect:'CONTAINS', value:'Up to 80 ms'},   # narrowed by field_doubt.weak_check (:466-483)
   desk:     {path:'field.revisions.b', want:{'contains':'Rev B'}},        # desk_scene.matches/lookup (:35-69)
   question: {words},                                                       # only the owner's answer settles it
 of: [ids], join: 'and'|'or',                                               # mode 'decide'
 verdict: 'open'|'holds'|'fails'|'cannot_tell'|'seen',  stale: bool,
 slack: {lo, hi, unit, exact:{lo:'p/q', hi:'p/q'}} | null,
 evidence: ['O1','O2'],  depends: ['office:owner:db5f…#B5@69dada6f…', …, 'goal:C1']}
```

**Modes.**
- `hold`: must hold, with current evidence, at finish. This is for data.
- `seen`: a desk milestone, held at some moment. It is recorded with the achieving act's envelope and the digest of the relevant `read.desk` subtree. It need not still hold at finish. This matters because the route stops showing as soon as the selection moves (FQ:1257), which makes P01's goals milestones, not a final state.
- `decide`: a decision over sub-goals, using Belnap "and"/"or". A false conjunct decides an "and" (`stac/evidence.py:78-82`). For example, "decide whether Rev B allows this pulse" is C1B and C2.

**Names chosen to avoid clashes.**
- Kind `condition` and schema `ledger.condition/1` are already totals (`conditions.py:45-46`, `field_model.py:15`).
- "held" in the Field is a finding whose evidence conflicts (`field_source.py:264`).
- "BROKEN" is a total whose result paragraph is gone (`conditions.py:105`).
- Problem type `interval` is a lifetime (`problem_service.py:16-22`, `schedule_math.py:31-43`).

So this design uses `goal_set`, the verdict words below, and `bound` for error bars.

### 1.2 States, and the words on screen

S is the slack: the limit minus the value, oriented so that "holds" means S ≥ 0.

| verdict | rule | on screen |
|---|---|---|
| open | some bound input has no evidence yet | open |
| holds | lo(S) ≥ 0 (lo > 0 for `<`), every evidence revision current | holds |
| fails | hi(S) < 0 (≤ 0 for `<`) | does not hold |
| cannot_tell | S straddles 0; or two readings' intervals do not intersect; or DOMAIN_ERROR (`math_model.py:110`) | cannot tell |
| seen | a desk milestone was observed | shown |
| + stale | an evidence revision differs from the record's current revision | recheck, with the old verdict beside it in quiet ink |

"holds" and "cannot tell" are already `field_doubt`'s words (`field_doubt.py:27`).

### 1.3 Evidence and revision binding

- **Evidence comes only from actual reads**, never from the model:
  - `office.get` gives a cell's value and unit plus the sheet revision;
  - `documents.get`, `investigation.sheet` (step id and `input_key`, `investigations.py:162`) and `conditions.get`;
  - `read.desk` gives a subtree digest.
- **A relation** compiles through `math_model.compile_expression(expr, variables, constraint=True)` (`math_model.py:150`). Its variables are built from the cells read.
  - With no bound recorded, the comparison is exact (`EXACT_RATIONAL`, `math_model.py:147`).
  - With bounds, `bounds.evaluate` is used (section 7).
  - The domain bounds `lower`/`upper` (`math_model.py:34`, `:102`) are never used as error bars.
- **Staleness.** `goals.refresh(set)` compares each evidence revision with the current one.
  - Changed revision, but the bound cells hold the same values: the read rebinds the evidence and nothing else is done.
  - Values changed: the goal is evaluated again.
- **Dependency graph.** The graph D is each goal's `depends` plus the Field's links (`field_source.py:199`, `:233-236`, `:277-286`).
  - When node v changes, everything reachable from v, desc(v), is evaluated again in topological order, the way `reason_graph.validate` orders it (`reason_graph.py:50-57`). The cost is O(|desc(v)| + edges).
  - The ripple's split between calculations that read the changed cell and those that only read the sheet (`field_ripple.py:160-166`) separates "work again" from "confirm".

### 1.4 Where it lives

- **While she works:** `host.session.state['her_plan']`, bounded at 64 KiB canonical, the same way the trail is kept (`stacy_hand.py:33`). Working does not write records, so Ask first is never blocked by her own bookkeeping.
- **When done:** `goals.keep` (execute, added to `HERS_SHOW`) writes the set as a Project Desk record with history (`project_desk.py:121`). At Ask first, keeping it waits like any other change.
- **Inside adaptive work:** `state['conditions']` beside `observations` (`adaptive_work.py:67`), saved by `flow.save` (`:356`).
- **Bounds:** their own records (section 7.1).

New Kernel operations, in `workbench/goals_service.py`, registered in `CAPABILITIES`:

| operation | scope | what |
|---|---|---|
| `goals.check` | read | evaluate a set's goals now; writes nothing |
| `goals.get`, `goals.list` | read | kept sets |
| `goals.keep` | execute (`HERS_SHOW`) | keep a finished set |
| `bounds.get` | read | the recorded bound of a cell |
| `bounds.set` | approve | the owner records an error bound. It is never hers: no list names it, and providers may not propose approve scope (`stacy_control.py:286-291`) |

### 1.5 How it is shown

- **The plan card** sits at the top of her conversation, in her column:
  - the request's words;
  - one row per goal: the verdict word, the goal's words, the slack ("by 25 to 35 ms"), and an evidence word ("from O3") that inspects the read the same way `inspect_in_line` does;
  - the act in progress ("Opening the Field");
  - the owner's words Stop, Continue and Put the window back, and Agree / Strike on each proposed goal.
  - Lines are added as things change: "Holds · C3 · from O4"; "Already known · O2"; "Stopped where you took the window".
- **WorkBlock** (`agent_qt.py:330-392`) gets four rows:
  - Doing now: the goal being worked;
  - Found: how many of the goals are decided;
  - Needs you: asks and escalation cards;
  - Inspect: the set.
- **The hologram** is the lower-left picture, built in #50. `HerHand.state_changed(str)` emits one of `idle`, `thinking` (a model turn is running), `acting` (an act on the window), `waits` (for the owner), `stopped`. The look pass maps these to the intensity of the static. With reduced motion the static is still. There is no other coupling.
- **Words.** No key is printed, the line language is "a line", and the list is "Apps".

---

## 2. Operators

### 2.1 Desk acts (`workbench/desk_ops.py`, pure Python)

**Fluents.** Each has a finite domain, read once per turn. Object constants are the sheets on each face, files, `HEAD_ROWS` (`desk_acts.py:37-38`) and `MENU_ROWS`/`PANEL_ROWS` (`:46-54`).

| fluent | domain | read from |
|---|---|---|
| `surface` | field, home, workspace | where.surface (D:175-181) |
| `centre` | files, page, app, record, none | where.tab.type |
| `face` | work, apps, network | field.face |
| `sel` | relevant sheets ∪ {other, none} | field.selected |
| `view` | whole, reading, other | field.whole, zoom |
| `over` | none, reading, revisions(a,b), steps, would | field.reading / revisions / steps / would |
| `route` | owner ∈ relevant ∪ {none} | field.route, **valid only while owner = sel** |
| `menu` | closed, root(t), screen(t, title), panel(t, L) | menu.* |
| `popups` | a subset of {menu, panel, head:M, apps, meter, equalizer} | where.popups |
| `line` | target, text ∈ {empty, ours(L), owner's}, room, pending | line.* + new fields |
| `hand`, `waiting`, `undoable` | dial; cards waiting; latest trail entry | talk.* + new field |

**Restricting to relevant objects keeps the search small.** `point.sheet`'s argument domain is the sheets named in the goals plus the current selection, not all 60. With g ≤ 4 named sheets, the projected state space is at most 3 · 3 · 5 · 6 · 2 · 2 = 1,080 states, from surface · face · sel · over · popups-empty · in-sight. That is fewer than 16,200 act edges, and a breadth-first search over them takes milliseconds.

**Encoding.** `Op(name, pre, add, delete, certain, observe, cost_s)` for each of the 40 acts, transcribed from the states_acts map (its section 2).
- **Certain** effects are the ones the doer itself checks before returning ok: `go.field` (D:710), `go.files` (D:736), `point.sheet` (D:837), `menu.open` (D:947-952), `menu.close` (D:1012-1013), `sheet.trace` (D:1087-1088), `sheet.compare` (D:1111-1112), `sheet.close` (D:1149), `type.to` (D:1189), `type.put` (D:1210-1213).
- **Observed** effects (zoom, folder and view, `go.back`'s destination) become unknown until the next `read.desk`.

The rows the planner uses most:

| act | pre | add | delete |
|---|---|---|---|
| `go.field{face}` | none (the pointer goes through Arrange › Field, D:707-708) | surface=field ✓, face ✓; sel=first sheet (observed) | none |
| `point.zoom{whole}` | F | view=whole (observed) | none |
| `point.sheet{title}` | F; sheet on this face, unique; pointer form needs it in sight (D:211-216) | sel=s ✓ | steps, go; route shown (FQ:1257) |
| `sheet.compare` | F; sel; face=work; a sibling exists (FP:691-706) | over=revisions(older, newer) ✓ | reading |
| `sheet.trace` | F; sel | route=sel ✓ | none |
| `sheet.close` | F | over=none ✓ | reading, revisions, steps, would |
| `go.files{folder,view}` | no owner words in the line (D:346, D:363) | workspace+Files ✓ | none |
| `menu.open{file\|sheet}` | Files with the file / F with the sheet in sight | menu=root(t) ✓ | panel |
| `menu.choose{then}` | a menu is open on the **expected target** | menu=panel(base) | none |
| `then.keep/count/back/end` | panel; step offered | L updated / ended ✓ | none |
| `menu.close` | none | popups=∅ ✓ | menu, panel, head menus, Apps, cards |
| `read.desk` | none | free sensing; writes no journal line (D:1451); about 0.1 s | none |

**Rules carried into the planner:**
- **A refusal is not a no-op.** A failed `menu.choose` leaves a screen open (P3:86-90). `changed` means attempted, not landed (D:126-128). Read back after every refusal.
- **The owner's input, or a background refresh, makes every fluent unknown**, because the window is shared.
- **Popups are sticky.** Only `menu.close` clears them (P1:88-142). A standing tidy goal ends every turn with popups = ∅.

**Hidden state to add to `read.desk`** (section 10, S2):
- `keyboard`: where the keyboard is (D:285-286);
- `line.ours`: the inverse of `unsent()` (D:352-355);
- `line.pending`: a Kernel approval waiting in the console (`console_qt.py:532-533`);
- `talk.waiting`: the count from `waiting_cards` (D:1290-1306);
- `field.came_from`: from `_field_from_home` (`field_page.py:171`);
- `field.in_sight`: the ids with `sheet_point` inside the body;
- `field.objects`: id, title, kind, state and links, at most 60;
- `menu.rows`: key, words, enabled, listed, asks.

`route_said` should return None when the route's owner is not the selected sheet, matching the view's rule at FQ:1257.

**Conformance test.** For each act, from 3 sampled states on the offscreen bench window, predict the abstract state after the act, run it, and compare with `read.desk`. Certain effects must match exactly. Observed effects must match or be marked unknown.

### 2.2 Kernel operations

| class | operations (scope) | needs | adds / affects | how it is checked or found to have landed |
|---|---|---|---|---|
| **read: establishes evidence** | `office.get`, `documents.get`, `investigation.sheet`, `.path`, `field.read`, `conditions.get`, `goals.check`, `bounds.get` (read) | the record exists | `known(cell@rev)`, `state(record)` | the read itself, with a digest |
| **simulate** | `field.whatif`, `field.ripple`, `field.doubt` (read) | readable | hypothetical values; traps. The doubt can make a goal **cannot tell** (a weak check, a missing condition) | itself |
| **change** | `field.set` (execute; Do and show) | revision = expected; the cell holds a number; the value differs (`field_service.py:170-185`) | cell := v; new revision; the sheet's calculations go to RECHECK (`datasheet_work.py:174-175`) | `office.get` shows the cell = v and revision ≠ expected; Undo exists (`stacy_hand.py:197-200`) |
| change | `office.datasheet.recheck` (approve; Free hand only, `stacy_hand.py:41`) | page current; source decision stands | a new page with `replaces`; output := f(cells) exactly | some page's `derivation.replaces` = the old id |
| change | `files.write` (execute; Do and show) | the path is free (else it waits, D:1243-1248) | file | `files.get` sha256 = sha256(text); Undo `/files.trash` with a guard (`stacy_hand.py:201-212`) |
| change | `files.trash` (execute; Do and show) | not reserved | moved to the Trash; returns `id` (`files_service.py:504-510`) | `files.trash_list` holds the id; Undo **new**: `/files.restore {"id"}` (section 5.5) |
| **check** | `investigation.continue` (execute), `investigation.refresh`, `conditions.recheck` | a check is due (`investigations.py:265-266`) | PASSED / CHECK_FAILED; SUPPORTS / OPPOSES | the step row |
| check | `math.calculate`, `math.schedule` (execute) | problem revision and digest bound | an exact receipt | `math.schedule.get` CURRENT / STALE (`schedule_math.py:77-84`) |
| owner's decision | `investigation.review`, `bounds.set`, `goals` Agree / Strike | none | none | never hers |
| swap | `brain.model.use` (approve) | memory admissible (section 8) | the resident model | `brain.status` |

**Consequences.**
- Reads add facts and delete none, so they commute and repeat harmlessly. A plan's reads are a set, not a sequence.
- Only changes and navigation take sequence slots.
- An operator whose delete list contains an agreed `hold` literal cannot come last in a plan.

---

## 3. The planner (`workbench/planner.py`, pure Python)

### 3.1 Abstraction

The atoms are:
- each goal's verdict;
- `current(record@rev)` and `known(address#cell@rev)`;
- the desk fluents of section 2.1, restricted to relevant objects;
- `asked(question)`.

There are at most 64 atoms. Each goal fans out to at most 8 sub-goals. These are `reason_graph`'s budgets (`reason_graph.py:19`, `:42`).

### 3.2 Regression (weakest precondition)

**Logical regression (STRIPS style).** For operator o and goal set G:

  Reg(G, o) = (G \ add(o)) ∪ pre(o), defined only when add(o) ∩ G ≠ ∅ and del(o) ∩ G = ∅.

**Numeric regression.** For changes: wp(x := e, Q) = Q[e/x], and wp(a₁; a₂, G) = wp(a₁, wp(a₂, G)). The linear boundary comes from `math_model.affine` (`:184-218`) and `sweep`'s root −c/k (`:246-256`). A product of two unknown inputs falls outside the linear form and goes to interval bisection (section 7).

**Worked on After Hours 07.** Take G = "C3 holds and the settled power is current". Then

  wp(field.set(B3 := v); office.datasheet.recheck, G) = 12 V · v ≤ 6 W ∧ pre(recheck) ∧ pre(set)  ⇒  **v ≤ 500 mA**.

- With the rail at 12 V ± 1 % recorded, this becomes v ≤ 6 / 12.12 A = **50/101 A**, shown rounded down as "495.04 mA".
- For the pulse ceiling, I_start ≤ 8/12 A = 2/3 A. With the rail ± 1 %, I_start ≤ **200/303 A** (660.06 mA).

She offers this as a what-if (read) and never sets it on her own.

### 3.3 Search and its bounds

- **Kernel layer.** Breadth-first regression to H = 3, using only relevant operators (add ∩ G ≠ ∅) and remembering goal sets already seen.
  - Node count N(H) ≤ (b^{H+1} − 1)/(b − 1), capped at 4,096, the same as `reason_graph`'s combination budget (`reason_graph.py:77`).
  - After Hours 07 has b ≤ 10, so N(3) ≤ 1,111. Because reads commute, only changes and navigation branch, b_seq ≤ 4, giving at most 85.
- **Desk layer.** Breadth-first search over the projected state space of section 2.1, at most about 1,080 states. This generalises `desk_acts.key_path` (`:399-415`) from the Field's own moves to acts.
- **Unknown fluents** after an observed effect: insert `read.desk` before any act whose precondition reads them. In practice the loop reads back after every act anyway (section 4.1).

### 3.4 HTN methods for known jobs

Methods are data in `planner.METHODS`, checked like a `reason_graph`: acyclic, at most 64 nodes, at most 8 subtasks per method. The model does not write methods in this pass. It picks one when two apply.

| method | decomposition | when |
|---|---|---|
| `shown(s)` | [go.field] · [point.zoom whole if ¬in_sight(s)] · point.sheet(s) | desk `seen` on field.selected |
| `side_by_side(a)` | shown(a) · sheet.compare | field.revisions.a/b |
| `traced(s)` | shown(s) · sheet.trace | field.route.owner_title = s |
| `both_shown(a, s)` | side_by_side(a) · point.sheet(s) · sheet.trace | revisions persist across a selection move (P3:21-25); trace works under a comparison (P3:26-30) |
| `line_count(f, col, val)` | go.files · menu.open(f) · menu.choose(then) · then.keep(col, val) · then.count · then.end(line) | line.text = L |
| `menu_read(M)` | head.open(M) · menu.close | rows read as evidence |
| `relation(c)` | {office.get(bind)}: reads as a set · evaluate | data `hold` |
| `apply_checked_method` | methods.preview · instantiate · run · result · joined.prepare · run · result | I05 completion (`adaptive_work.py:164-185`) |
| `recheck_after_set(s, cell)` | field.set · {office.datasheet.recheck for each calculation reading cell} · evaluate | wp case (3.2) |
| `tidy` | menu.close if popups ≠ ∅ | end of every turn |

P01's four milestones then plan to **12 acts** against P01's 17 steps. Two of P01's steps are not derivable and stay standing rules or owner acts: the tidy `sheet.close` and the owner-only `hand.undo` (section 5.2).

### 3.5 The lookahead the model is shown

For each open goal c:
1. Take the cheapest plan of length at most 3 that reaches c, or that narrows it if c is cannot tell.
2. Collect the plans' first steps and remove duplicates.
3. Score each first step o by

  score(o) = Σ_c w_c · φ_c(o) / cost(o)

Here:
- φ_c is the probability that doing o decides c. It is 1 for a read that supplies missing evidence; for a narrowing step it is the **decisive share** (section 7.3).
- w_c is 1 for an agreed goal, and 0 when c only feeds a `decide` parent that is already decided.
- cost(o) is seconds: an EWMA of the envelope's `seconds` per act (0.1–0.8 s, P1/P2), of Kernel read times, and of model turn times. An ask to the owner costs a fixed 300 s of "your attention", so asks rank after reads.

The view shows at most 5 options, each with its "then" (the rest of its plan, at most 2 steps), what it serves, its decisive share, its seconds, and whether it is hers or will wait. Then come the controls: ASK (when a declared unknown or a needed bound exists), OTHER (which leads to PROPOSE), and REPORT (offered when progress stalls).

### 3.6 What is deduced and what is asked

| deduced (no model turn, recorded as `deduced`) | asked of the model |
|---|---|
| a step whose option is the only admissible one and whose arguments are single-value enums or a checked continuation (`slate_action.py:8-29`) | the goal set, from candidates (GOAL) |
| every navigation inside a desk method; the presses (`key_path`) | which of at least 2 non-dominated options (NEXT), including which question to put to the owner |
| reads with value of information > 0, as a set | an operation outside the options (PROPOSE), and its arguments when they are not settled: a methods mapping and declarations; a `then.keep` column and value read from words |
| a repeated step: hand back the evidence | file text for `hand.write` (PROPOSE, Free hand only) |
| rechecks after a change (repair along D) | finish words, optional (WORDS) |
| interval verdicts, break-even, decisive shares, wp boundaries | none |
| finish: all agreed goals decided with current evidence | none |
| tidy: menu.close | none |

Which limit applies ("Rev B applies to this run") is chosen as a goal by the model or the owner and recorded in `bind`. It is never deduced: string matching of conditions would refuse it (`stac/quantities.py:138-140`).

---

## 4. Execution: a receding horizon, one act at a time

### 4.1 The loop

The loop runs in `workbench/her_hand_qt.py`, class `HerHand`. A QTimer ticks every 250 ms. Each tick does at most one act, one Kernel operation, or one poll of a model job. All logic lives in `planner.py`.

```python
def tick(plan):
    if plan.stop.is_set(): return pause(plan)
    if plan.model_job: return poll_model(plan)                  # one model turn at a time
    sensed = sense(plan)            # read.desk('all') + goals.check for bound cells whose revision may have moved
    planner.absorb(plan, sensed)    # verdicts, stale marks, Φ; compare with plan.expected → surprise
    if planner.finished(plan): return finish(plan)              # every agreed goal decided, current evidence
    options = planner.lookahead(plan, H=3)                      # ranked first steps, ≤ 5, each with its rest
    step = planner.deduce(options) or ask_model(plan, options)  # None while the model thinks
    if step is None: return
    if (prior := planner.repeat_of(plan, step)): return hand_back(plan, step, prior)   # nothing runs
    if not authorized(plan, step): return offer_or_stage(plan, step)    # Ask first: offer; change: card waits
    envelope = do(step)                                         # ONE act (door='her') or ONE Kernel operation
    plan.record(step, envelope); plan.expected = step.predicts  # read back on the next tick
```

### 4.2 Verification by class

| class | verified by |
|---|---|
| navigation | `read.desk` on the next tick against the act's certain effects; observed effects are absorbed |
| Kernel read | its digest becomes an observation O<n> |
| change through `stage` | the card's result (D:675-690), then the "landed" read of section 2.2. `changed` is not proof (D:126-128) |
| check | the investigation step row (`investigations.py:183-188`) |
| desk milestone | `desk_scene.matches` on the `read.desk` tree at that tick; the tree's digest is stored |

### 4.3 Repair on surprise

- **Refused act.** Read back, mark the touched fluents unknown, and re-plan from the read. The refusal's words become an observation. If the same act is refused twice in a turn, that option is dropped for the turn.
- **Observed effect differs** (for example `go.back` landed on Today, P2:64-68). Absorb it and re-plan. This costs no model turn unless options now tie.
- **A record changed under us** (new revision). The goals that depend on it go stale. Repair desc(v) (section 1.3).
- **A write timed out or raised.** Probe whether it landed before any retry:
  - landed: adopt the new revision;
  - not landed and the revision is unchanged: a retry is safe, because the save is compare-and-set (`field_service.py:174-175`);
  - otherwise: re-plan.
  - For desk acts, `read.desk` plus the journal line with this turn's origin (D:1455-1466).
  - For work steps, call `continuing_work.reconcile_apply` on the exception path (today it runs only on explicit resume, `adaptive_work.py:517-523`).
- **Progress.** Φ = Σ_c (2·[open] + [cannot tell] + [stale]), with the total relative width of the slack intervals as a tie-breaker.
  - Each step must lower Φ, or be a read that narrows an interval.
  - Two steps in a row that do neither are a **stall**, which starts escalation (section 8).

### 4.4 Stop at any moment

- **The flag.** `plan.stop` is set by:
  - Stop on the plan card;
  - a new owner-only act `hand.stop`;
  - **the owner's touch.**
- **Owner's-touch filter.** While a plan runs, `HerHand.eventFilter` is installed on `QApplication`. A `MouseButtonPress`, `KeyPress`, `Wheel` or `TouchBegin` whose receiver `isWindowType()` stops her.
  - Real input enters through the window system to a `QWindow` and is then forwarded to the widget.
  - The doers send straight to widgets: `sendEvent` in `mouse`, `right_click` and `type_text` (D:248-276), and QTest's widget overloads in `key` and `click_menu_row` (D:262-265, D:333). These never reach a `QWindow` receiver.
  - `spontaneous()` cannot be the test, because QTest marks its widget key and mouse events spontaneous (section 11).
- **Where the flag is checked:** in `run` before the doer; in each press of `key`; in each character of `type_text`; in each segment of `walk` (D:474); and in `wait_until` (D:70-78). The act raises `Refusal('STOPPED', 'You took the window; I stopped before <act words>.')`, and the plan goes to `paused`.
- **After a stop** the card offers Continue (sense, then plan from wherever the window is) and Put the window back.
  - Put the window back is a desk plan from the current abstract state to `snapshot`, made with the same breadth-first search: go.*, point.sheet, sheet.close, menu.close.
  - The writing line is cleared only if its words are still hers (D:352-355).

### 4.5 The dial, and what always asks

| | Ask first | Do and show | Free hand |
|---|---|---|---|
| `read.desk`, Kernel reads, `goals.check` | done | done | done |
| navigation | **offered**, one bundle per plan segment (section 5.3) | done, shown | done, shown |
| change on `HERS_SHOW` | waits (card) | done, with Undo | done, with Undo |
| change on `HERS_FREE` only (e.g. `office.datasheet.recheck`) | waits | waits | done |
| `ALWAYS_ASKS` (`stacy_hand.py:46-57`), `brain.model.use`, `bounds.set`, `*.review` | waits | waits | waits |
| owner-only acts | never | never | never |
| a plan from her own noticing | none | none | allowed (`stacy_hand.py:14-15`) |

Agreement: a plan's goal set must be **agreed** before any change in the plan and before a finding is reported as final.
- At Ask first and Do and show, the owner agrees with Agree on the card.
- At Free hand, the set counts as agreed once it is shown, and Strike re-plans.
- A desk-only plan needs no agreement to run.

### 4.6 Budgets and pace

- Steps and seconds: `DEFAULT_BUDGET`, 40 steps and 600 s (`agent_loop.py:122`).
- Model turns: at most 12 per plan.
- Pace: at least 300 ms between window acts, so the owner can follow. Scenes set this with `given.pace`.
- A repeat handed back costs nothing. The decision that chose it is counted as a turn, not as a step.

---

## 5. Her door

### 5.1 `desk_doers.run(door='her')`

```python
# desk_doers.run, replacing D:1425
if door == 'her':
    turn = her_turn(host)                          # HerHand's live turn token, or None
    if turn is None: raise Refusal('NOT_OFFERED', REFUSALS['NOT_OFFERED'])      # only HerHand opens this door
    if turn.stop.is_set(): raise Refusal('STOPPED', REFUSALS['STOPPED'])
    if name in OWNER_ONLY: raise Refusal('OWNER_ONLY', 'Only you do this.')   # today only desk_hers refuses (A:311)
    if 'by' in (args or {}): raise Refusal('BAD_ARGUMENTS', 'How the hand moves is not hers to choose.')
    clean = desk_acts.check(name, args)
    line = field_do_line(host, clean) if ACTS[name].line_decides else None    # field_do.steps_for, field_do.py:241
    ok, why = desk_acts.desk_hers(turn.place, name, clean, line=line)
    if not ok and ACTS[name].mark == 'navigates' and not turn.offer_ok(name, clean):
        return offered(host, turn, name, clean, why)         # journal state OFFERED; the act does not run
    origin = 'desk-her:%s:%d' % (turn.set_id[:8], turn.n); word = turn.word   # provenance in the journal and the trail
    by = None                                                # default form: pointer or direct (D:1409)
```

What changes alongside it:
- **Changes still go through `stage_change`** (D:663-672) with `asked=turn.asked`. That is True for the owner's request, and for her own noticing only at Free hand. The dial then decides exactly as it does for "set B3 to 300" said to her.
- **`hand.step`** gets its line from `field_do.steps_for(kernel, operator(), obj, field)` (`field_do.py:241`), which reads without showing. A read step's line is run as a Kernel read, not through `field_page.do`, because that puts a page over the work (`field_page.py:270-292`).
- **`menu.choose`** is given the expected target internally. The doer refuses if `menu_said().target` differs, because today it walks whatever menu is open (D:979-983).
- **`record`** (D:1455-1460) gains state `OFFERED`. The origin `desk-her:…` replaces the default `desk-script:script` (D:1423).
- **Kernel principal.** Her changes keep `operator()` (SH:2057-2058), as her hand does since 0.6.0. The journal origin and the trail's `word` say it was her. A principal of her own is not in this pass.
- **New refusals:** `STOPPED`, `OWNER_ONLY`. New owner-only acts: `hand.stop` and `hand.putback`. The act count becomes 42 and `test_forty_acts_and_their_marks` (T:130-141) is updated. Nothing is removed.

### 5.2 What she may do without asking

Her door uses `desk_hers` (A:299-339) as it is, plus these door rules:
1. owner-only acts are refused at the door;
2. `by` is refused;
3. `hand.step` gets its line;
4. at Ask first a read step is run as a read, so the window does not move.

In P01, `hand.undo` (step 17) and `look.set`/`hand.dial` passed only because `door='script'` does not enforce OWNER_ONLY (D:1425-1429). Scenes keep that door for setup. Her door never has it.

`hand.trash` is the one change that is hers at Do and show but has no Undo (P1:179-183). Section 5.5 gives it one. Until that lands, her door makes `hand.trash` wait at Do and show; Free hand still does it.

### 5.3 Ask first: one offer per plan segment, not a card per act

At Ask first the planner groups the navigation up to the next goal into one offer, for example:

> To show Rev A beside Rev B I would open the Field, select "07 Limits Rev A" and compare them: 3 moves of your window. **Go ahead**

- Go ahead, or `hand.approve`, now also takes the latest waiting offer. It authorises **that bundle only**, for this turn.
- Any owner touch voids it, and the next offer is made against the new state.
- Changes inside the bundle still stage their own cards.

### 5.4 How each act is shown

- **Her column:** the plan card (section 1.5) with the current act's words. Each act's words are its `ACTS[name].words` with arguments filled in. They print no key and never name the line language (A:20-21, T:241-247).
- **Her pointer:** `workbench/her_pointer_qt.py`, `HerPointer(QWidget)`, is a child of the host with `WA_TransparentForMouseEvents`, kept on top.
  - When `c.door == 'her'`, `mouse`, `right_click` and `click_menu_row` call `show_at(global_point)` first.
  - The pointer glides there in 200 ms and pulses on the press. With reduced motion it jumps and does not pulse.
  - For keys forms nothing is drawn. Her door seldom uses keys forms.
- **The trail:**
  - data changes go to `stacy_trail` as today (`stacy_hand.py:241-249`), with `word` set to the request;
  - navigations go to a separate `desk_trail` (session key; 100 kept; `type.put` records only its length, as D:1464-1465 does). Her trail keeps 40 entries (H:34) and P01 alone has 17 acts, so navigations would otherwise push data Undo lines out of reach;
  - the plan card shows the latest 5 navigations, folded.

### 5.5 Undo where data changes

| change | Undo |
|---|---|
| `field.set` | `/field.set {id, cell, value: was, expected_revision}`, which guards itself (`stacy_hand.py:197-200`) |
| `files.write` (new file) | `/files.trash {path}` with the sha256 guard (`:201-212`) |
| `files.trash` | **new:** `/files.restore {"id": <trash id>}`. `files.trash` already returns `id` (`files_service.py:510`). Add `files.restore` to `UNDOES` (`stacy_hand.py:43`); `undo_allowed` accepts exactly `{'id'}` with 32 hex digits. It is approve scope (`files_service.py:72`), and it runs only from the owner's Undo click, the same path as the existing Undo (SH:2105-2148) |
| `files.rename` | none; it always waits (not on any list) |
| `office.datasheet.recheck` | none needed; the old page stays and the new one `replaces` it |
| navigation | Put the window back (section 4.4) |

**The word "Delete".** The owner wants the Trash called DELETE. On her cards the word is "Delete “x” (it goes to the Trash; Undo brings it back)". The look pass (#50) owns the word everywhere else. **The operation keeps its name `files.trash`.** Renaming it to `*.delete` would put it under `ALWAYS_ASKS` (`stacy_hand.py:50`) and would drop its Undo.

---

## 6. The model's contract

### 6.1 Turns

| turn | asked when | answer schema | max_tokens | deadline (4B) |
|---|---|---|---|---|
| GOAL | a request reaches the planner and the candidates exceed what the request names exactly | `{"pick":[k,…]}`, 1–8 unique integers in 1..K | 48 | 60 s |
| NEXT | at least 2 non-dominated options | `{"n":k}`, k in 1..K, K = options + controls | 16 | 60 s |
| PROPOSE-1 | NEXT chose OTHER | `{"op":<enum of available ops>,"for":<enum of open goal ids>}` | 24 | 60 s |
| PROPOSE-2 | the chosen operation's arguments are not settled | the operation's narrowed argument schema, with **numbered enums** (6.2) | ≤ 384 | 120 s |
| WORDS | finish or ask, optional (off by default on the 4B) | `{"words": string ≤ 400}` | 128 | 60 s |

Every deadline is under the 180 s cap (`adaptive_contract.py:26`). No turn carries a "why" or an "uncertainty" field. In all 11 SELECTs those fields ran to their caps (R2:1340), costing 16–26 s per turn. The card's "why" is the planner's: what the option serves and its decisive share.

### 6.2 Schemas

```json
GOAL   {"type":"object","additionalProperties":false,"required":["pick"],
        "properties":{"pick":{"type":"array","minItems":1,"maxItems":8,"uniqueItems":true,
                              "items":{"type":"integer","minimum":1,"maximum":12}}}}
NEXT   {"type":"object","additionalProperties":false,"required":["n"],
        "properties":{"n":{"type":"integer","minimum":1,"maximum":8}}}
PROPOSE-2 for methods.preview (I05), numbered enums decoded by the coordinator:
       {"type":"object","additionalProperties":false,
        "required":["capacity","pairs","additive","constant_capacity","interval_semantics","overhead","fragmentation","indivisibility"],
        "properties":{"capacity":{"type":"integer","minimum":1,"maximum":4},
          "pairs":{"type":"array","minItems":1,"maxItems":8,"items":{"type":"array","minItems":2,"maxItems":2,
                   "items":{"type":"integer","minimum":1,"maximum":8}}},
          "additive":{"type":"boolean"},"constant_capacity":{"type":"boolean"},
          "interval_semantics":{"enum":["HALF_OPEN","CLOSED","UNKNOWN"]}, "overhead":{"enum":["NONE","PRESENT","UNKNOWN"]},
          "fragmentation":{"enum":["NOT_APPLICABLE","REQUIRED","UNKNOWN"]},"indivisibility":{"enum":["NOT_APPLICABLE","REQUIRED","UNKNOWN"]}}}
```

- The coordinator supplies `method`, `method_revision`, the problem binding and `basis` (the problem source's label). It decodes the integers against the lists shown in the view, then runs `validate_call` (`adaptive_work.py:254-296`) and the method's own mapping check (`checked_methods.py:97-110`).
- The declaration words stay as words, because they carry the judgement I05 tests: `overhead` is NONE vs PRESENT/UNKNOWN in the Overhead_unknown case.
- The I05 decision-1 arguments were 712 characters pretty-printed and 498 compact (J1). This form is about 190 characters, roughly 70 tokens.

### 6.3 The view (NEXT), as compact lines rather than JSON

Example: After Hours 07, with C2 agreed on its own and ±1 % / ±2 % recorded.

```
You choose Kasandra's next step. Answer only {"n": k}.                      ← stable prefix (cached)
REQUEST: Does the startup pulse fit Rev B, and is startup power under its 8 W ceiling?
MUST BE TRUE (agreed):
C1B Startup duration (Bench B5) <= Pulse duration (Rev B B4)    does not hold, by 25 to 35 ms   O1 O2
C2  Startup power (calc 500c)   <= Pulse ceiling (Rev B B3)     cannot tell: -0.036 to 0.432 W  O3 O4
C3  Settled power (calc 0e39)   <= Continuous (Rev B B2)        holds, by 2.53 to 2.74 W        O3 O5
LAST: O5 read Rev B B2 = 6 W (rev 334c)                                    ← volatile tail
OPTIONS:
1 ask you the error of Startup current (Bench B4) · decides C2 for 89% of its range · you answer
2 ask you the error of Rail voltage (Bench B2) · decides C2 for 78% · you answer
3 doubt "07 Bench readings" · may show a trap in C2's inputs · 1 s
4 report now: C1B does not hold; C2 cannot tell, good to 1.27% each
5 something else
```

That is about 330 tokens of content. The stable part (the instruction, the request, the goal words) comes first, so the llama.cpp prefix cache can reuse it (section 6.6).

### 6.4 Token and time budget for a 4B at 4096 context

The fit rule is prompt + output + 32 ≤ context (`slate_stream.py:67`).

| turn | prompt (tokens) | output (tokens) | fit at 4096 | seconds here: cold / prefix reused |
|---|---|---|---|---|
| GOAL | ≤ 1,200 | ≤ 48 | 1,280 | 29 / 18 |
| NEXT | ≤ 1,600 | ≤ 16 (typically 6) | 1,648 | 26 / 13 |
| PROPOSE-1 | ≤ 1,800 | ≤ 24 | 1,856 | 33 / 15 |
| PROPOSE-2 (I05 mapping) | ≤ 2,400 | ≈ 70 (≤ 384) | ≤ 2,816 | 53 / 35 |
| WORDS | ≤ 1,400 | ≤ 128 | 1,560 | 50 / 40 |

How the seconds are computed: prompt at 65 tokens/s; output at 4.5 tokens/s; the prefix reuse assumes about 900 cached tokens. CPU load can double these; the deadlines in 6.1 allow for that.
- A whole After Hours 07 request costs 1 GOAL + 0–2 NEXT, about 1 minute of model time.
- I05 Current_A costs 1 PROPOSE + 1 WORDS (section 9).
- The current frame grows by 333–659 tokens per observation (R1/R2 SELECT prompts) and would reach about 5,300 tokens by FINISH. The views here show the last 4 observations as lines, so they stay under 2,400 tokens.

### 6.5 When the answer is wrong or late

| case | detected by | what happens |
|---|---|---|
| not JSON, or out of the schema | `record_io.strict_json` + `validate_schema`; constrained decoding makes it rare | no answer; same as late |
| late (`LOCAL_STREAM_TIME_BUDGET`) | `slate_stream.events` (`:46`) | If the top option is a read, or a navigation that is hers now, it is taken as the **default**, recorded as `default` (precedent: `MODEL_PATIENCE`, `agent_loop.py:128`). A change is never taken by default. Otherwise: "I could not decide in time", the turn waits, and escalation step 1 runs |
| a choice that makes no progress | Φ is not lowered after the act | counts toward a stall; two in a row escalate |
| PROPOSE arguments invalid | `desk_acts.check` / `validate_call` | refused; the refusal becomes an observation; asked once more; then the top option, or ASK the owner |
| PROPOSE precondition false | planner | repaired by prefixing a method (e.g. needs F → `shown(s)`) and shown as "then"; if it cannot be repaired, refused |
| repeat on unchanged inputs | `input_key` (`investigations.py:162`) / fingerprint (`adaptive_work.py:434`) / the same act with the same arguments and an unchanged desk digest | **evidence handed back**: "Already known · O<n>", nothing runs, nothing is charged; a second repeat in a row → WAITING, as today |
| wrong goal set (semantic) | the owner | the card shows the set; Strike / Agree; no change runs before agreement (section 4.5) |
| model changed mid-turn | `ACTION_MODEL_CHANGED` / `MODEL_CHANGED_DURING_INFERENCE` | the turn is void; re-plan |

### 6.6 Transport and prompt reuse

- **Talk and desk plans** go through `brain.ask`.
  - NEXT is the existing `choice` mode as it is (`local_brain.py:892-896`, `:915-920`).
  - Add mode `pick`, a multi-select `{"pick":[…]}` with `picks ≤ 8`, to the enum at `local_brain.py:57` for GOAL.
  - Each plan uses one conversation id, its set id.
  - Jobs are polled the way `agent_loop` does (`agent_loop.py:548-570`).
- **Adaptive work** goes through `brain.action`. The request gains a `turn` of NEXT, PROPOSE or WORDS (new `ledger.action-request/2`), with branches in `slate_action.run_job` (`:163`). The frame-binding checks (`:113-124`) are unchanged.
- **Prompt reuse.**
  - Today `run_job` passes no `cache_key` (`cache_n 0`).
  - The claim is consumed by every generation (`slate_stream.py:72-76`), and it works only when the worker runs `PINNED_SINGLE_SLOT` (`slate_stream.py:20`, `local_brain.py:416`).
  - Plan turns pass `cache_key = prefix_key(worker, owner, set_digest, stable_messages)`, computed over the stable head only, and republish the claim after each validated answer, the way `slate_reasoning` does (`:360-371`).
  - The stable head must not start with keys sorted canonically (`project_desk.py:77-78`). That is why the view is written as lines.

### 6.7 The 35B profile

The profile is chosen by the registered model's file size and a context of at least 8,192. With the 35B:
- 7 options are shown instead of 5, and the lookahead goes to H = 5;
- WORDS is on by default;
- GOAL may add one `question` goal of at most 120 characters, settled only by the owner.

The schemas are otherwise identical, so the same tests cover both models.

---

## 7. Intervals and value of information on After Hours 07

### 7.1 Where tolerances are recorded

Today no record holds a measurement error bound:
- the Office cell's key set is closed (`office_tables.py:43-44`);
- the reviewed-row schema is closed (`datasheet_work.py:14-15`);
- writing "±5 ms" in Conditions would make `field_doubt` see two different conditions (`field_doubt.py:164-171`).

New: `ledger.bound/1`, Project Desk kind `bound`, one per (address, cell), with history:

```
{schema, id, revision, address:'office:owner:db5f…', cell:'B5', sheet_revision:'69dada6f…',
 kind:'abs'|'rel'|'range', e:'5' | r:'0.01' | lo:'105', hi:'115', unit:'ms',
 basis:"<the owner's words, e.g. scope at 100 µs/div>", source:'<address>'|null, set_by:'OWNER', created}
```

- **Only the owner sets it**, through `bounds.set` (approve). A bound she invents is the worst failure this design can have.
- **It is bound to the sheet revision.** If a later revision changes the cell's value, the bound shows "recheck"; if the value is unchanged, a read rebinds it.
- **Shown:** in the sheet's reading in the Field ("B5 110 ms ± 5 ms, recorded by you"), and as the slack in the plan card.

### 7.2 Arithmetic (`workbench/bounds.py`, standard library only)

- An `Interval(lo, hi, dimension)` has `Fraction` endpoints in base units, made with `math_units.unit_spec` and `rational` (`math_units.py:23-47`). The float `measure()` is not used.
- From a bound: abs gives [x − e, x + e]; rel gives [x(1−r), x(1+r)] for x ≥ 0; range gives [lo, hi].
- Operations:

| operation | result |
|---|---|
| [a,b] + [c,d] | [a+c, b+d] |
| [a,b] − [c,d] | [a−d, b−c] |
| [a,b] · [c,d] | [min(ac, ad, bc, bd), max(…)], dimensions add |
| [a,b] ÷ [c,d] | [a,b] · [1/d, 1/c] if 0 ∉ [c,d]; otherwise DOMAIN_ERROR, verdict cannot tell |
| negation | [−b, −a] |
| xⁿ | endpoints; for even n with 0 inside, [0, max] |

- `bounds.evaluate(ir, intervals)` mirrors `math_model.values` node by node (`:90-124`).
- **Soundness:** inclusion monotonicity holds, and the natural extension encloses the true range.
- **Exactness:** the enclosure is exact when each variable occurs once, which covers L − T and V·I. For linear predicates the exact range comes from `affine()`: c + Σ min/max(kᵢ·loᵢ, kᵢ·hiᵢ).
- **Rounding** happens only when a value is shown: lo rounds down, hi rounds up, and the rational is kept beside it. A number past the 2,048-bit cap (`math_units.py:50-52`) is widened outward, which keeps the enclosure valid.

### 7.3 The decision rule and value of information

- **Rule:** holds if lo(S) ≥ 0; does not hold if hi(S) < 0; otherwise cannot tell. Equality is decidable because there are no floats.
- **When S is already on one side,** every narrower reading lies inside S, so the value of information is 0. A new reading is intersected with the old one. An empty intersection means "the two readings cannot both be right": verdict cannot tell, shown as a conflict.
- **Decisive share of input i** when S straddles 0: the measure of the x ∈ Xᵢ for which S(Xᵢ := x, other inputs as intervals) lies on one side, divided by |Xᵢ|.
  - For a predicate that is monotone in each input and uses each once, it is computed exactly by solving the boundary.
  - Otherwise, bisecting Xᵢ into 64 pieces gives a sound lower bound.
  - Under a uniform prior this is φ in section 3.5.
- **Break-even:** when no bound is recorded, she reports the largest error that would still decide the goal. She never invents a tolerance.

### 7.4 Worked (exact; the tolerances are the owner's to record, and these are examples)

| goal | recorded bound | slack | verdict | what a better reading is worth |
|---|---|---|---|---|
| **C1B** pulse ≤ Rev B (80 ms) | T = 110 ± 5 ms | 80 − [105, 115] = **[−35, −25] ms** | **does not hold**, robustly | 0. A ±1 ms reading gives [−31, −29], inside the old slack. It stays decided for any e < 30 ms |
| C1A pulse ≤ Rev A (120 ms) | same | [5, 15] ms | holds | robust while e ≤ 10 ms |
| C2 startup power ≤ 8 W | V ± 1 %, I ± 2 % | P = [189189/25000, 200889/25000] = [7.56756, 8.03556] W; S = **[−0.03556, 0.43244] W** | **cannot tell** | share for I = **6989/7878 ≈ 0.887**: holds for every I ≤ 200/303 A. Share for V = **3089/3978 ≈ 0.777**. Ask about the current first. Break-even (1+r_V)(1+r_I) ≤ 40/39; with r_V = r_I, r ≤ √(40/39) − 1 ≈ **1.27 %** |
| C3 settled power ≤ 6 W | same | S = [2.538528, 2.740128] W | holds | break-even (1+r)² ≤ 25/14, r ≤ 33.6 % |
| HOLD = C1B ∧ C2 | none | none | **decided (does not hold)**, because C1B does not hold | the value of V and I for HOLD is 0 (w = 0), so the NEXT turn does not offer options 1–2 and goes straight to "report" |

With no bound recorded, C1B is exact: 80 − 110 = −30 ms, does not hold.

**This is the owner's statement as the system computes it.** With ±5 ms the excess is [25, 35] ms. Every value exceeds the limit, so a more precise reading has zero value for this pass/fail decision. The planner therefore never offers that reading.

### 7.5 What she says (templated from the evidence; no model prose)

> The startup pulse does not fit Rev B: it runs 25 to 35 ms past the 80 ms limit (110 ms ± 5 ms, your bound). A better reading would not change this. Startup power against the 8 W ceiling: cannot tell from these readings; it is decided if the rail and the current are each good to 1.27 %.

The investigation's question "What stretched the startup pulse?" (`investigations.py:267-268`) has no operator on this computer that answers it. She says so and asks for the page's own next step, a repeat capture at the load.

---

## 8. The escalation rule

**Triggers:**
- two late turns in a row;
- a stall (two steps without progress, section 4.3);
- self-consistency disagreement;
- PROPOSE refused twice.

**The ladder,** cheapest first:

1. **Narrow the turn.**
   - Deduce whatever is now unique.
   - Drop options scoring below 10 % of the top.
   - Reuse a selection that already landed. Today `consume_pending` discards it (`adaptive_work.py:390-397`); retry under the same frame binding (`slate_action.py:113-124`).
2. **Think more.** Repeat the same turn with thinking on and a think budget of 256 tokens on the 4B, 1,024 on the 35B.
   - This needs a per-call template option. Today `TEMPLATE_OPTIONS` is global (`local_brain.py:471`) and `slate_stream` passes it (`:78`).
   - The model binding must record the turn's thinking. It is hard-coded False at `slate_action.py:72`.
   - To verify on the build: that the server applies the JSON schema only after the reasoning block. If it does not, this step is skipped.
3. **Self-consistency.** k = 3 NEXT turns with the option order rotated; a pick 2 of 3 agree on is taken. About 40 s warm on the 4B. If all three differ, ASK the owner.
4. **A batched model swap, under her hand.**
   - The planner marks the turns that need a bigger model (or a vision model, where pictures matter; it is named only as the owner's choice) and queues them.
   - When no reply and no ACTION job is running (`local_brain.py:515-517`), it stages one card `/brain.model.use {id, options}`. That is approve scope, never hers: it is on no list and providers are refused it (`stacy_control.py:286-291`). It waits at every place of the dial.
   - The card carries the schedule below and its verdict.
   - After the batch, a `/brain.restore {}` card (`local_brain.py:1041-1047`).
   - In adaptive work, the grant must name the allowed models and their memory (`adaptive_work.py:39-59`). Otherwise the swap stops the work with `ADAPTIVE_MODEL_CONFIGURATION_CHANGED` (`:30`).

**Admissibility of the swap,** checked in process with `schedule_math.evaluate` (`:16-63`) on an in-memory problem:

  M_resident + max_t Σ_{i: sᵢ ≤ t < eᵢ} mᵢ ≤ M_budget,  where M_budget = budget_room(available, reserve, future, credit) (`resource_control.py:66-71`)

- The resident model is included as an allocation, so a sequential handover appears as release-before-allocate at the boundary (`schedule_math.py:52-55`). That is what `credit` means (`resource_control.py:192`).
- KV cache and compute buffers are explicit allocations, because the sweep models no overhead (`:47-48`).
- Example, illustrative 32 GB budget, the 35B at 20,542,732,576 bytes (`gguf_fixture.py:27`):
  - 35B on [0, 600) + KV 3 GB on [0, 300) + dense 16 GB on [300, 600) + a 1 GB read on [250, 320): peak **37.54 GB** on [300, 320), **INFEASIBLE**.
  - The same with the 35B released at 300: peak **24.54 GB**, **FEASIBLE**.
  - The card proposes only the feasible schedule.
- Here, the mechanism is tested with the 2B (1,280,835,840 bytes) as the small model and the 4B (2,740,937,888 bytes, granted 4,480 MB as in `joined_model_checks.py:96`) as the bigger one.

---

## 9. The I05 experiment: the current loop against the conditions loop, same model

**Arms.** Same model file, same config (context 6144, 4 threads, 4480 MB), same three cases (`joined_model_checks.py:11-13`), same budgets (`:57-59`) and the **unchanged acceptance checks in `run_case`** (`:61-90`).

| arm | loop | model turns |
|---|---|---|
| **A** | today's two-phase SELECT/ARGUMENTS (`slate_action.run_job`), run again the same day for timing | every step |
| **B1** | conditions + lookahead shown; the model picks **every** step (NEXT; PROPOSE for the mapping); evidence handed back on repeats; finish needs every condition held | every step, small turns |
| **B2** | B1 + deduction wherever the option is unique and its arguments are settled | branch points only |
| B2@4096 | B2 at context 4096 (A's frame does not fit there) | as B2 |

- `--arm A|B1|B2` selects the arm.
- A's code path is unchanged: B behaviour is switched on only by `plan['adaptive']['conditions']` being present in the work order.

**The B frozen spec** is `ledger.i05-conditions-spec/1`. It differs from A's spec (`:95`) by declaring:
- the conditions (K1: preview SUPPORTED and current; K2: method result current; K3: joined result AVAILABLE with all four `APPLICATION_TYPES` (`adaptive_contract.py:13`); K3′: preview rejected and current);
- that finish requires K3 ∨ K3′;
- the deduction rule, recorded with origin `COORDINATOR_DEDUCED`;
- evidence handback;
- that no expected answers are exposed.

**What B2 should do on Current_A.** After the mapping, every step can be deduced:
- `instantiate` from the continuation (`slate_action.py:8-29`);
- `methods.run` and `joined.run` from their single-value enums `action`/`expected_digest` (`adaptive_work.py:132-140`);
- `*.result` from the single-value enum `job` (`:142-148`);
- `joined.prepare` from the single-value enums `receipt`/`method_job` (`:150-160`).

So the model work is one PROPOSE-2 (mapping and declarations, about 70 tokens) plus WORDS. On Overhead_unknown it is the mapping (where `overhead` must not be NONE), then K3′, then WORDS.

**Measured, per case and per arm:**
- pass/fail by the unchanged acceptance checks;
- wall seconds and model seconds;
- model turns by kind; prompt, cached and output tokens per turn; the longest turn;
- deadline misses;
- deduced steps; evidence handbacks; refusals by code;
- the Φ trace; escalations;
- whether the finish citations are complete;
- fresh-process reopen (`:82-87`);
- an independent semantic review of the finding, as today (`REQUIRED_SEPARATELY`).

**Pre-registered expectations, written so they can be wrong:**
- A fails Current_A again on the 180 s wall at decision 2 (R2:1353).
- B2 passes all three cases here with at most 3 model turns per case, no turn over 150 s, and under 6 minutes of model time per case.
- B1 passes with 7–9 NEXT turns of 13–30 s each.
- In B1 the model picks the planner's top option at least 80 % of the time. If so, deduction is shown to be safe.

**The 35B on the ThinkPad.** The same arms run through the campaign runner (`tools/campaign_lib/runner.py`; 24 GiB available, `:435-437`) at context 8192, with the same measurements. That gives two tables: 4B here, 35B there.

---

## 10. Build order: each slice ships with its tests and scenes

**S1. Bounds and goals, pure.** New files `bounds.py`, `goals.py`, `goals_service.py`; entries in `CAPABILITIES`.
- Tests (`tests/test_bounds.py`):
  - interval laws as property tests over random rationals (inclusion monotonicity, enclosure);
  - every After Hours 07 number in 7.4 exactly (6989/7878, 3089/3978, 40/39, 50/101, 200/303);
  - DOMAIN_ERROR when 0 is in a denominator;
  - display rounding is outward.
- Tests (`tests/test_goals.py`): verdict rules; stale and rebind on a new revision; Belnap decide; candidate generation for After Hours 07 gives C1A, C1B, C2, C3 and C4 and nothing with mismatched units.
- Ships: the owner records ±5 ms with `/bounds.set …` (approve), and `/goals.check` in the line answers "does not hold, by 25 to 35 ms".

**S2. Read-back and doer fixes, no door yet.**
- Additions to `read.desk` (section 2.1); `route_said` follows FQ:1257.
- `menu.choose` checks the expected target internally.
- `investigations.execute` stops dispatching a repeat (`:163-166`) and returns the earlier row with `returned: True`.
- `takes_back` for `files.trash` → `/files.restore`; `UNDOES` += `files.restore`.
- The Approve tooltip loses "in the Field, G does the same" (`shell2.py:2035`).
- Tests: `test_read_desk_reports_hidden_state`, `test_route_only_while_selected`, `test_repeat_returns_evidence`, `test_trash_undo_restores`. **P01 passes in all 4 runs.**

**S3. The desk planner.** New files `desk_ops.py` and the desk layer of `planner.py`, with the methods of 3.4.
- Tests:
  - `test_desk_ops_conformance`: the offscreen model-vs-window check of 2.1;
  - `test_p01_goals_plan_to_12_acts`;
  - `test_putback_plans_to_snapshot`;
  - `test_search_bounds` (at most 4,096 nodes).
- Ships: `/goals.plan` (read) shows a plan as words, without running it.

**S4. Her door.**
- `desk_doers.run(door='her')`; `STOPPED`, `OWNER_ONLY`; `OFFERED` in the journal.
- New files `her_hand_qt.py` (`HerHand`, the owner's-touch filter, the plan card, Continue, Put the window back) and `her_pointer_qt.py`.
- `desk_trail`; `hand.stop` and `hand.putback` (owner-only).
- `SlateFace.plan_asked(text)`, inserted after `run_asked` (`shell2.py:2563`), so no existing path changes.
- Talk requests are matched to desk goal templates without a model in this slice.
- `desk_scene` gains step forms `{"ask_her": text}`, `{"wait_her": {"until": "done|waits|paused", "seconds": n}}`, `{"owner": "touch"}` (a QTest click on the `QWindow`), and a `read.desk` part `plan`.
- Tests:
  - `test_her_door_refuses_owner_only_and_by`;
  - `test_touch_filter_discriminates`: P01's 17 acts trip it 0 times, and one `QWindow` click trips it;
  - `test_stop_between_presses`;
  - `test_offer_bundle_voided_by_touch`.
- Scenes:
  - **P02** (Do and show): "Show me the limits' Rev A and Rev B side by side, and where the bench readings come from". Expect both milestones `shown`, every envelope `door: her` with `changed: []`, popups `[]` at the end, and no `stacy_trail` entry.
  - **P03** (Ask first): the same request. Expect one offer, journal `OFFERED`, `hand.approve` runs the bundle.
  - **P04**: the owner touches mid-plan. Expect `paused` and `STOPPED`; then `hand.putback` returns to the snapshot.
  - **P05** (Do and show): changes inside a plan. `hand.cell` is done with Undo; `office.datasheet.recheck` waits ("the records mark it for your approval"); `hand.trash` is shown as "Delete" with a `/files.restore` Undo.

**S5. Conditions over data.**
- The Kernel layer of `planner.py`: regression and wp, value of information, repair along D, Φ and stall detection, the finish rule, the landed probe, `goals.keep`.
- Changes go through `stage`.
- Tests: `test_wp_settled_current` (v ≤ 500 mA; with the rail ±1 %, 50/101 A); `test_voi_zero_when_decided`; `test_repair_order_topological`; `test_landed_probe_field_set`; `test_finish_refused_with_open_goals`.
- Scenes:
  - **P06**: After Hours 07. The owner records ±5 ms, asks "Does the startup pulse fit Rev B?". Expect C1B does not hold, slack [−35, −25] ms, no reading offered, and she points at Bench B5 and Rev B B4.
  - **P07**: "What would let settled power stay in Rev B's continuous rating?" Expect a what-if only (read) with "up to 500 mA", nothing changed.

**S6. The model's contract.**
- New file `plan_turn.py` (views, schemas, decoding, self-consistency); `brain.ask` mode `pick`; the stable-prefix cache key; the default-taken rule.
- Tests: with a fake worker, as `agent_loop`'s tests patch `ask_model`: `test_next_turn_fits_4096`, `test_late_turn_takes_only_hers_reads`, `test_propose_repaired_or_refused`, `test_numbered_enums_decode`.
- Live check script `workbench/plan_model_checks.py` with the 4B (scene **P08**, `needs: model`): GOAL + NEXT on After Hours 07. Records the seconds per turn and fails if a turn takes over 60 s.

**S7. The conditions arms in adaptive work, and the I05 experiment.**
- `state['conditions']`, deduction, the handback at `adaptive_work.py:435`, the finish extension at `:363-366`; `slate_action` turns; `joined_model_checks --arm`; the B frozen spec.
- Run A, B1, B2 and B2@4096 here with the 4B. The 35B runs are queued for the owner on the ThinkPad.

**S8. Escalation.** The per-turn thinking option, k = 3 self-consistency, the batched swap card with the admissibility schedule, and `brain.restore` afterwards.
- Tests: `test_swap_card_waits_at_every_place`; `test_schedule_admissibility` (the 37.54 / 24.54 GB rows); a live 2B → 4B swap here.

**Not in this pass:**
- a Kernel principal of her own;
- methods written by the model;
- free-text goals on the 4B;
- bounds she sets, or any automatic tolerance;
- vision chat (still refused, `local_brain.py:217`);
- changing `assess_upper_bound`'s matching (`stac/quantities.py:138-140`);
- exactness for non-linear predicates with repeated variables (bisection only);
- her door for `type.send`, the Terminal or the Web (owner-only);
- an Undo for rename;
- showing kept goal sets in the Field;
- offering acts to cloud providers;
- renaming `files.trash`;
- removing anything.

Two items here are #50's, not this pass's: the picture's move, the typeface and the "DELETE" word across the app. This pass only emits `HerHand.state_changed` and uses "Delete" on her own cards.

---

## 11. Corrections to the readers' maps, and hazards found while checking

1. **`hand.step`'s line** should be read from `field_do.steps_for` (`field_do.py:241`). `field_page.py:277` is where `field_page.do` calls it, and `do` also puts the steps page over the work (`:288`).
2. **Spontaneous events cannot detect the owner.** `desk_doers.key` uses `QTest.keyClick` (D:265) and `click_menu_row` uses `QTest.mouseClick` (D:333). QTest marks its widget events spontaneous. Only `mouse`, `right_click` and `type_text` use `sendEvent`. The owner's-touch filter therefore keys on a `QWindow` receiver (section 4.4), and S4 tests it in both directions.
3. **Prompt reuse needs a pinned single slot** (`slate_stream.py:20`, `local_brain.py:416`), and every generation consumes the claim (`slate_stream.py:72-76`). Plan turns must republish their stable-prefix claim after each validated answer.
4. **Hand-step reading pages do not print keys.** The Field draws the `KEY  words` foot as words alone (`field_qt.py:652-659`). The key text that does reach the screen is:
   - the Approve tooltip, "in the Field, G does the same" (`shell2.py:2035`), fixed in S2;
   - the console's "Press Enter again … Esc" (`console_qt.py:534`), for the look pass.
5. **`desk_hers` accepts `by`.** `desk_hers('show','go.field',{'face':'apps','by':'keys'})` is True because `check` accepts `by` (A:249-276). Her door refuses `by` before `desk_hers` is consulted (section 5.1).
6. **Model proposals bypass her hand today:** Run calls `execute` directly (`shell2.py:2715`). Plan steps never take that path. They go through `stage`.