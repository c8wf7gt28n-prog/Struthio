# Kasandra's hand on the desk, with a planner over conditions

**Design for the next build pass.** This design takes the planner-first approach. It was checked against HEAD `d1df337` (0.8.2), and paths are relative to `/home/user/Struthio`.

**Abbreviations used in citations:**

| Short | File |
|---|---|
| A | `workbench/desk_acts.py` |
| D | `workbench/desk_doers.py` |
| H | `workbench/stacy_hand.py` |
| SH | `workbench/shell2.py` |
| FP | `workbench/field_page.py` |
| FQ | `workbench/field_qt.py` |
| SC | `workbench/desk_scene.py` |
| AW | `workbench/adaptive_work.py` |
| SA | `workbench/slate_action.py` |
| LB | `workbench/local_brain.py` |
| T | `tests_integrated/test_desk_acts.py` |

**Probe outputs** from the states reader, under `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/hand_read/states_acts/`:
- P1 = `probe.out`
- P2 = `probe2.out`
- P3 = `probe3.out`

**My own check of every interval number in §7:** `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/planner_design/iv.py`.

---

## 0. The shape in one page

**Ask little, deduce the rest, check everything.**

- **The model is asked three kinds of question, never more.** Each answer is a short enum:
  - **GOAL:** which of the planner's grounded goals answer the request.
  - **CHOICE:** which meaning is intended, when the planner has a real tie whose branches move the window or change data.
  - **OPTIONS:** which of the planner's next options to take, when no operator can achieve the goal.

  The model never writes an act, an argument, an operation, a tolerance or a goal's words. The 4B already does well at exactly this: it filled 11 of 11 enum slots correctly in R1 and R2, while free text always runs to its cap (model-path reader §5).
- **The planner** turns agreed goals into acts by regression (weakest precondition) over a finite abstraction of the window and the records. Known jobs use HTN methods.
- **The executor** does one authorized act. It reads back (`read.desk` or a Kernel read), compares the result with the act's effects, records evidence or a surprise, and plans again from what it read. Her dial decides each act exactly as it does today (`desk_hers` A:299-339, `hers` H:150-158). What always asks still asks (H:46-57). The owner can stop it at any moment.
- **There is one conditions engine.** A goal is a predicate with evidence:
  - A **desk goal** is a `{path: matcher}` over `read.desk`, the same language as a scene's `expect` (SC:35-69). So a scene step's expectation and a desk goal are the same thing.
  - A **work goal** is a relation, text, state or artifact predicate over records, bound to their revisions. Owner-recorded bounds turn it into exact interval arithmetic.

```
owner's words ─► hand_words.match (no model) ─┬─ one full match ─────────────┐
                                               └─ candidates ─► GOAL turn ───┤
                                                                             ▼
                                agreed goals ─► planner (methods, then regression) ─► plan
                                                                             │
              ┌──────────── read back ◄── one act through her door ◄── dial ◄┘
              ▼
   evidence / surprise ─► goals assessed ─► all agreed hold? ─► tidy ─► finish (card + evidence)
              └────────── no ─► plan again from what was read ──────────────────┘
```

**New files.** All are pure Python with no Qt, except `hand_turn.py`'s timer and the card:

| File | What it holds |
|---|---|
| `workbench/goals.py` | The goal record, its assessment, the store and the operations |
| `workbench/bounds.py` | Exact intervals, verdicts, decisive share, break-even, the bound record |
| `workbench/desk_ops.py` | The acts as planning operators: pre, effects, what to observe, cost |
| `workbench/hand_methods.py` | HTN methods, written as parameterised scene fragments |
| `workbench/planner.py` | Abstraction, regression search, numeric weakest precondition, value of information, admissibility |
| `workbench/hand_words.py` | Deterministic request matching and goal grounding |
| `workbench/hand_turn.py` | The receding-horizon executor, the stop flag, the turn record |
| `workbench/hand_qt.py` | Her hand card and the pointer ring |

**Changed:**
- `desk_doers.run` and `read_desk`
- `desk_acts` (refusals; `desk_hers` for read steps)
- `stacy_hand` (desk trail; DELETE Undo; `why_waits`)
- `local_brain` (`goal` mode)
- `adaptive_work` and `slate_action` (arm B of I05)
- `desk_scene` (`say` steps)

---

## 1. The conditions engine

### 1.1 Names (avoiding words the code already uses)

| Taken | Where | So the engine uses |
|---|---|---|
| kind `condition`, schema `ledger.condition/1` (totals cards) | `conditions.py:45-46` | kind **`goal`**, schema **`ledger.goal/1`** |
| "held" = a finding with conflicting evidence | `field_source.py:264` | internal state **HOLDS**; on screen **"holds"**, never "held" |
| "BROKEN" = a total whose result paragraph is gone | `conditions.py:105` | **FAILS**; on screen **"does not hold"** |
| problem type `interval` = a time lifetime | `schedule_math.py:6`, `:31-43` | bounds live in **`ledger.bound/1`**; "interval" is used only inside `bounds.py` |

The five words on screen are: **open, holds, does not hold, cannot tell, recheck**. These are the doubt's own register (`field_doubt.py:27`).

### 1.2 The record

```python
# ledger.goal/1   (Project Desk record, kind 'goal'; written like conditions.create, conditions.py:150-180, with desk_history)
{ 'id', 'kind':'goal', 'schema':'ledger.goal/1', 'project',
  'turn': <hand-turn id> | None, 'work': <adaptive work id> | None,
  'template': 'check.limit',  'params': {'x':'office:owner:db5f…#B5', 'L':'office:owner:4f35…#B4'},
  'statement': 'The startup pulse of “07 Bench readings” stays within “07 Limits Rev B CURRENT”.',   # planner's words, never the model's
  'aim': 'achieve' | 'decide',            # decide: holds and does-not-hold are both answers
  'form': 'desk' | 'relation' | 'text' | 'state' | 'artifact',
  'predicate': {...},                      # per form, §1.3
  'bind':   {'x': {'address':'office:owner:db5f…','cell':'B5','revision':'69dada6f…','unit':'ms','role':'measured'},
             'L': {'address':'office:owner:4f35…','cell':'B4','revision':'334cce26…','unit':'ms','role':'limit'}},
  'bounds': {'x': <ledger.bound id> | None, 'L': None},
  'evidence': [{'sym','record','revision','read','digest','at','step'}],
  'state': 'OPEN'|'HOLDS'|'FAILS'|'UNDECIDED',  'stale': bool,
  'slack': {'lo','hi','unit','exact':{'lo':'-35','hi':'-25'}} | None,
  'depends': ['office:owner:db5f…#B5', 'office:owner:4f35…#B4', 'goal:<id>'],
  'origin': 'OWNER' | 'HER' | 'DEDUCED',   'agreed': bool, 'agreed_by': 'request' | 'owner word' | 'work order' }
```

**Desk goals** are not stored on their own. They live inline in the **hand-turn record**, `ledger.hand-turn/1` (kind `hand_turn`, ≤ 64 KiB). The reason is that a desk goal is a *milestone*: the route stops being shown as soon as the selection moves (FQ:1257), so it only has to have held once, with evidence. Only goals marked `persist` (for example "leave the comparison open", or the tidy goal) must also hold at the final read.

The hand-turn record holds:
- the request and the dial;
- the snapshot of the window at the start;
- the goals and their evidence;
- every plan version;
- each step: act, args, state (DONE / OFFERED / WAITING / REFUSED / STOPPED), envelope summary, read digest, expected effect and surprise;
- the model turns (kind, prompt and output tokens, seconds, answer);
- the outcome (FINISHED / STOPPED / LIMIT / WAITING).

### 1.3 Forms and how each is assessed

`goals.assess(goal, reads) -> (state, slack, reason)` is pure.

| Form | Predicate | Assessed by |
|---|---|---|
| `desk` | `{'desk.field.route.owner_title': '07 Bench readings', 'desk.field.selected.title#v': '07 Bench readings'}` | `desk_scene.lookup` and `matches` (SC:35-69) on `{desk: read.desk all}`. HOLDS when every pair matches. |
| `relation` | `{'expression':'x <= L', 'bind':…}` | `math_model.compile_expression(…, constraint=True)` (`math_model.py:150`). Point values use exact `values()` (`:90-124`); bounded inputs use `bounds.enclose` (§7). Slack is S = L − x, with "holds" meaning S ≥ 0. |
| `text` | `{'read':'office.get', 'path':'document.sheets.0.cells.D3.value', 'expect':'CONTAINS', 'value':'Up to 80 ms'}` | The narrowed check that `field_doubt` asks for (`field_doubt.py:471-482`) |
| `state` | `{'read':'documents.get', 'path':'source_state.state', 'equals':'CURRENT'}` | One read |
| `artifact` | `{'read':'joined.result', 'job':…, 'types': APPLICATION_TYPES}` | `completion_evidence`'s own test (AW:173-177) |

**Assessment rules:**
- **OPEN:** some bound input has no evidence yet.
- **HOLDS:** lo(S) ≥ 0 (or the matcher holds), and all evidence is current.
- **FAILS:** hi(S) < 0, and all evidence is current.
- **UNDECIDED:**
  - S straddles 0; or
  - two readings of the same input have intervals that do not overlap ("the two readings cannot both be right"); or
  - a `DOMAIN_ERROR`, such as zero in a denominator (`math_model.py:110`).
- **stale** is a flag beside the state. The old state is kept with "recheck" until it is evaluated again, as `investigations.refresh` does (`investigations.py:327-352`).

**Two safety rules:**
1. A goal's words come from its template, not from the model.
2. **A goal is never achieved by editing its own evidence.** A cell bound with `role:'measured'` is never in the add-list of an achiever the planner chooses for that goal. `field.set` on it is used only for what-if answers (§3.5) or when the owner's goal *is* to set it.

### 1.4 Evidence and revision binding

**Work evidence:**
- Each read establishes `{sym, record, revision, read, digest, at, step}`.
- The revision is the one the read returned: `office.get` revision, `documents.get` revision, the `investigation.sheet` digest, or an adaptive observation's `context_digest` (AW:330-333).
- Evidence is current when the record's current revision equals the evidence revision.
- `goals.refresh(kernel, ids, p)` compares those revisions only (cheap). On a difference it marks the goal stale and plans a re-read.
- If the bound cell's value is unchanged on the new revision, the re-read just rebinds and the state stands. This is the ripple's split between work that must be redone and work that only needs confirming (`field_ripple.py:160-166`).
- If the value changed, the goal is re-evaluated, in the order of the goals' `depends` (a topological order, as `reason_graph.validate` orders nodes, `reason_graph.py:50-57`).

**Desk evidence:**
- `{'at', 'step': n, 'paths': {path: got}, 'read_digest': sha256(canonical(read.desk subtree)), 'act': envelope summary}`, taken at the moment the predicate held.
- Desk evidence is not re-checked later, except for `persist` goals.

**The finish rule** (both domains): a turn or work finishes only when every agreed goal is in one of these states:
- HOLDS, with current evidence (for `achieve`); or
- HOLDS or FAILS robustly, with current evidence (for `decide`); and
- every `persist` desk goal holds at the final read.

Otherwise the outcome lists the open goals.

### 1.5 Store and operations

Store and operations are registered like `conditions.FIELDS` and `SCOPES` (`conditions.py:49-54`):

| Operation | Scope | Hers? |
|---|---|---|
| `goals.list {project?, turn?, work?}`, `goals.get {id}` | read | always |
| `goals.make {template, params, aim}` | execute | add to HERS_SHOW: it makes a record beside what was there and changes nothing of the owner's |
| `goals.refresh {ids}` | execute | add to HERS_SHOW |
| `goals.agree {id}` | approve | on no list, so it is always the owner's click |
| `bounds.list`, `bounds.get` | read | always |
| `bounds.set {address, cell, revision, form, value, unit, basis}` | execute | **always asks**: ALWAYS_ASKS gains `(('bounds.set',), 'a tolerance is yours to say: it decides what I conclude')`. Reads still never ask, because `hers` returns True for read scope first (H:154). |
| `hand.turns.save` (the hand-turn record) | execute | written by the executor, not by a model proposal. The model can never propose it, because `stacy_control.validate_actions` checks only offered operations (`stacy_control.py:272-292`). |

### 1.6 How it is shown

- **Her hand card** (§5.3): one row per goal with its state word, plus a "seen" word that opens the evidence.
- **Work goals** also feed the WorkBlock (`agent_qt.py:330`):
  - Doing now: the open goal being worked;
  - Found: *k* of *n* hold or are decided;
  - Needs you: questions, cards that wait, escalation;
  - Inspect: the goals.
- **Slack is shown in words**, such as "over by 25 to 35 ms" or "within by 5 to 15 ms". The lower end is rounded down and the upper end rounded up. The exact rational is kept beside it, as `number_record` keeps `rational`.

---

## 2. Operators

### 2.1 The abstraction (`planner.abstract(tree) -> State`)

The state is a frozen mapping from fluent to value, or `UNKNOWN`. Object constants are read once per turn: the sheets on each face, the files in the folder, `HEAD_ROWS`, `MENU_ROWS` and `PANEL_ROWS` (A:37-54). A panel line is at most base + 7 steps (`line_steps.py:23`), so every domain is finite.

| Fluent | Domain | From read.desk (current + additions) |
|---|---|---|
| `surface` | field, home, workspace | where.surface (D:175-181) |
| `centre` | files, page(s), app, record, none | where.tab.type |
| `left`, `right` | 3 × 3 | where.left, where.right |
| `popups` | subset of {menu, panel, head:M, apps, meter, equalizer} | where.popups (sticky: only `menu.close` clears it, P1:88-142) |
| `keyboard` **(new)** | field, line, files, menu, other | where.keyboard |
| `face` | work, apps, network | field.face |
| `sel` | sheets on the face ∪ {none} | field.selected.id |
| `in_sight(s)` **(new)** | bool per sheet | field.in_sight |
| `over` | none, reading(k), revisions(a,b), steps, would | field.reading, revisions, steps, would |
| `route` | owner ∈ sheets ∪ {none} | field.route (**fixed** to None unless owner = selected, FQ:1257) |
| `came_from` **(new)** | today, elsewhere | field.came_from (FP:171) |
| `menu` | closed, root(t), screen(t, title), panel(t, L) | menu.* plus **(new)** menu.rows |
| `files` | folder, view, has(name), selected | files.* |
| `line` | target, text, ours **(new)**, pending **(new)** | line.* |
| `waiting` **(new)** | int | talk.waiting |
| `hand`, `undoable` | dial; bool | talk.hand, talk.trail |

### 2.2 Additions to `read_desk` (D:580-649)

These are additive: nothing already read is removed.

| Addition | How it is read |
|---|---|
| `where.keyboard` | `QApplication.focusWidget()` against the Field view, `type_bar.box` and the FilesTab views (`keyboard_on`, D:285-286) |
| `line.ours` | `text == host._desk_put` (`unsent`, D:352-355) |
| `line.pending` | The console's pending approval (`console_qt.py:532-533`) |
| `talk.waiting` | `len(waiting_cards(host))` (D:1290-1306) |
| `field.came_from` | `_field_from_home` |
| `field.in_sight` | Ids whose rectangle centre is in the body, the test `sheet_point` uses (D:211-216); at most 60 (`field_source.py:43`) |
| `field.objects` | `[{id, title, kind, state}]`, at most 60 |
| `field.route` | None when `route.owner != field.selected`. Today it reports a stale route (P2:12-17) because the paint clears it (FQ:1257). |
| `menu.rows` | The current screen's `[{key, words, enabled, sub, listed}]`, where `listed = desk_acts.listed(key, MENU_ROWS+SCREENS or PANEL_ROWS)` |

`read.desk` stays free: no journal line (D:1451), about 0.115 s (P2:169-173).

### 2.3 Desk operators (`workbench/desk_ops.py`)

```python
Op('point.sheet', args=('title',),
   pre=[('surface','field'), ('on_face','$title'), ('in_sight','$title')],   # pointer form; her door is always pointer/direct
   add=[('sel','$title')],                    # certain: the doer checks it (D:837)
   dele=['steps','go'],                       # FQ:176
   observe=['route'],                         # shown only while owner = sel
   cost=0.4)
```

**The planner's operator set is 30 acts.** It excludes:
- the 5 owner-only acts (A:33);
- `look.set`;
- this pass, also `point.move` (keys only, so it needs the keyboard), `go.app` (MAKES risk, D:777-781), `head.meter` and `type.room`.

The owner's line door still has all 40 acts.

**Costs** are the median of the act's envelope `seconds` from the journal. The seeds are the probe's values: `go.files` 0.63, `then.keep` 0.78, `sheet.compare` 0.78, others 0.5.

In the table, ✓ marks an effect the doer checks itself. Any other effect is *observed*: unknown until the next read.

| Act | Pre (pointer form) | Add | Delete or unknown |
|---|---|---|---|
| `go.field {face?}` | — | surface=field ✓; face=f | sel, whole, zoom observed; popups untouched |
| `go.today` | — | surface=home | — |
| `go.files {folder, view}` | — | surface=workspace, centre=files ✓; folder, view observed | — |
| `go.open {sheet}` | surface=field, on_face(s), in_sight(s) | centre=page(s), surface=workspace | — |
| `go.back` | surface=field | surface=came_from | over |
| `go.pane {left?, right?}` | — | left, right | centre may change (P2:139-143) |
| `point.sheet {title}` | field, on_face, in_sight | sel=s ✓ | steps, go |
| `point.zoom {to:whole}` | field | whole observed | — |
| `head.open {M}` | — | popups ∋ head:M; **evidence: the rows** | — |
| `head.row {M, row}` | row ∈ HEAD_ROWS[M] (D:345) | per row (Today → surface=home) | — |
| `menu.open {file, name}` | centre=files, has(name) | menu=root(file:name) ✓ | panel |
| `menu.open {sheet, name}` | field, on_face, in_sight | menu=root(sheet:name) ✓ | panel |
| `menu.choose {path}` | menu open **with the expected target** (new check, §5.1); each row enabled and listed | `then` → panel(base(t)) | a failed choose can leave a screen open (P3:86-90) |
| `menu.close` | — | popups=∅ ✓ | menu, panel, head menus, apps, cards |
| `then.keep {c, w}` | panel(L), steps(L) < 8, column c, value w | panel(L ∣ where c=v) | — |
| `then.count` | panel(L) | panel(L ∣ count). **Not idempotent** (P2:99-108). | — |
| `then.back` | panel(L), L ≠ base | panel(back(L)) | — |
| `then.end {line}` | panel(L), ¬owner words, ¬pending (D:1061-1063) | line.text=L, ours ✓ | menu, panel |
| `sheet.trace` | field, sel, in_sight(sel) | route=sel ✓ | — |
| `sheet.doubt` | field, sel | over=reading(doubt) | — |
| `sheet.compare` | field, face=work, sel, sibling(sel) | over=revisions(pair(sel)) ✓ | reading |
| `sheet.close` | field | over=none ✓ | reading, revisions, steps, would |
| `sheet.whatif {cell, value}` | field, sel, number_at(sel, cell) | would | — |
| `sheet.steps` | field, sel, in_sight | steps listed | — |
| `type.to {who}` | — | line.target ✓ | — |
| `type.put {text}` | ¬owner words, ¬pending, no unseen characters (A:274) | line.text, ours ✓ | — |
| `read.desk` | — | (sensing) | — |
| `hand.cell {cell, value}` | field, sel, number_at | data: cell=v **once landed**, by her hand | calculations of the sheet → recheck |
| `hand.write {path, text}` | path not reserved (D:1240) | data: file(path) | if taken, it waits (D:1243-1248) |
| `hand.step {n}` | field, sel, n ≤ \|steps_for(sel)\| | the step's line | — |
| `hand.rename`, `hand.trash` | — | data | rename always waits; trash, see §5.4 |

### 2.4 Kernel operators (work)

Scopes were read from `engineering_kernel.CAPABILITIES` on this copy.

| Class | Operations (scope) | Needs | Affects | Landed or checked by |
|---|---|---|---|---|
| **sense** (establishes evidence) | `office.get`, `documents.get`, `field.read`, `investigation.sheet`, `investigation.path`, `conditions.get`, `ledger.address.read`, `goals.get`, `bounds.get` (read) | the record exists | adds known(cell@rev), state(record) | the read itself, with its digest |
| **simulate** (no effect on the world) | `field.whatif`, `field.ripple`, `field.doubt` (read) | the record is readable | hypothetical values; the doubt's traps can make a goal UNDECIDED | itself |
| **change** | `field.set` (execute; Do and show) | revision = expected; the cell holds a number; the value differs (`field_service.py:173-185`) | cell := v; new revision; the sheet's calculations go to recheck | `office.get`: the cell = v and the revision ≠ expected. Undo `/field.set` (H:197-200). |
| **change** | `office.datasheet.recheck` (approve; Free hand only) | page current; same parameters | new page with `replaces`; output := f(cells) exactly | some page has `derivation.replaces` = old id |
| **check** | `investigation.continue`, `investigation.refresh`, `conditions.recheck` (execute; Do and show) | a due check | PASSED or CHECK_FAILED evidence | the step row |
| **compute** | `math.calculate`, `math.schedule` (execute) | the problem revision and digest are bound | an exact receipt | `math.schedule.get` CURRENT or STALE (`schedule_math.py:77-84`) |
| **owner's** | `investigation.review`, `bounds.set`, `goals.agree`, `brain.model.use`, `brain.restore`, `files.restore` | — | — | a card that waits |

### 2.5 Rules that come from the tables

- **Reads commute and never delete a fact.** A plan's reads are a set, done first and all together. Only changes and navigation take sequence slots.
- **A refusal is not a no-op.** `changed` means "attempted" (D:126-128). A refused `menu.choose` left "More" open (P3:86-90). After every refusal the executor reads again before planning again.
- **An operator whose effects delete an agreed `persist` literal cannot be last in a plan.**
- **Owner input, or a background refresh, makes every fluent unknown.** The window is shared, so the executor reads before every act.

---

## 3. The planner (`workbench/planner.py`)

### 3.1 Regression

A literal is ℓ = (f, v). For a grounded operator o and a goal set G:

```
Reg(G, o) = pre(o) ∪ (G \ ach(o))
   defined iff  ach(o) ∩ G ≠ ∅                                  (relevance: o adds some goal literal by a ✓-certain effect)
            and no literal of G \ ach(o) is set otherwise or made unknown by o   (consistency)
            and pre(o) ∪ (G \ ach(o)) gives no fluent two values                  (mutex)
```

- **Lifted regression.** Arguments are unified with the goal literal (`point.sheet(title=s)` for `sel=s`). Free arguments (the `go.files` folder when the goal names only the file) take the value read now.
- **Grounding is driven by goals,** so the literal universe stays small. It is capped at 64, the `reason_graph` node budget (`reason_graph.py:19`).
- **Observed effects never satisfy a goal literal in regression.** If a later precondition needs one (such as `in_sight` after `go.field`), the plan contains its certain achiever (`point.zoom whole`). The read after `go.field` usually shows it already holds, and the next plan drops the act. That is exactly the 13 → 12 acts in the reader's toy over P01.
- **Numeric literals** (the work domain) regress by substitution, §3.5.

### 3.2 Search and its bounds

**The search:**
- A* backward from G until the goal set is satisfied by S₀ (the state read now).
- g = Σ cost(o) in seconds.
- h = h_max(G) = max over ℓ ∈ G with ℓ ∉ S₀ of c*(ℓ), where c*(ℓ) is the cheapest achiever's cost (precomputed per fluent). This is admissible.
- Visited sets are keyed by the canonical frozen goal set.
- Ties are broken deterministically by (cost, length, act names), so tests are stable.

**Bounds:**
- ≤ 4,096 expansions (the `reason_graph` combination budget, `reason_graph.py:77`), depth ≤ 12, ≤ 64 grounded literals.
- Past these, the answer is `TOO_FAR` and the card says so: "I could not plan that within twelve acts."
- Node count ≤ Σ_{d≤H} b^d = (b^{H+1} − 1)/(b − 1), where b is the relevant branching per goal set. For the desk, b ≤ 3 (sel is added by `point.sheet` or `go.field`, and so on), giving ≤ 3,280 at H = 7. In practice it is a few dozen.
- For reference, the reader's forward breadth-first toy plans P01's four milestones twice, plus the joint G3∧G4 plan, in **0.16 s** of pure Python (measured here). Target for `planner.plan`: < 50 ms per plan, with a test bound of 0.5 s.

**Plan check.** Every plan is simulated forward from S₀ in the abstraction before its first act runs. A plan that does not reach G in simulation is a planner bug (asserted in tests), never executed.

### 3.3 Milestones and joint goals

Goals from one request are first planned jointly. If the joint search fails because of delete interactions (a selection move clears the route), they are planned **sequentially in the order the owner said them**, each from the state the previous one leaves. Receding horizon makes that natural.

P01 shows both cases:
- G3 (trace) and G4 (compare) coexist, because revisions persist across a selection move (P3:21-25) and a trace works under a comparison (P3:26-30). The joint plan is go.field, point.sheet Rev A, compare, point.sheet Bench, trace (5 acts).
- G2 (the writing line) and G3 do not need joint planning, because G2 stays true while the window moves.

A **standing tidy goal**, `popups = ∅`, is appended to every turn as a `persist` goal. Popups are sticky (P1:88-142, P2:119-173). It adds `menu.close` only when something is open.

### 3.4 HTN methods (`workbench/hand_methods.py`)

**A method is a scene fragment with parameters; a scene is a method with constants.** Methods use the scene step shape (`{act, args, expect}`, SC:35-69), so the matchers, the read-backs and the test machinery are shared.

```python
Method('line.count', params=('folder','file','column','value'),
  steps=[{'act':'go.files',   'args':{'folder':'$folder','view':'list'}, 'expect':{'desk.files.names':{'contains':'$file'}}},
         {'act':'menu.open',  'args':{'on':'file','name':'$file'},       'expect':{'desk.menu.open':True}},
         {'act':'menu.choose','args':{'path':'then'},                    'expect':{'desk.menu.panel.ready':True}},
         {'act':'then.keep',  'args':{'column':'$column','words':'is $value'}, 'expect':{'desk.menu.panel.line':{'contains':'where $column=$value'}}},
         {'act':'then.count', 'args':{},                                 'expect':{'desk.menu.panel.line':{'contains':'| count'}}},
         {'act':'then.end',   'args':{'how':'line'},                     'expect':{'desk.line.text':'$line'}}])
```

**Rules:**
- A method is tried before plain regression.
- Its steps are checked by forward simulation from S. A step whose precondition does not hold is preceded by a regression **gap fill**, bounded at depth 4 (for example, getting to Files from wherever the window is).
- If the method fails even with gap fills, regression over all 30 operators runs.

**Method library v1:**

| Method | Decomposition |
|---|---|
| `see.place(p)` | `go.field` / `go.today` / `go.files` |
| `see.sheet(s)` | go.field(face of s) → point.sheet(s) |
| `see.trace(s)` | see.sheet(s) → sheet.trace |
| `see.compare(s)` | see.sheet(s) → sheet.compare |
| `see.doubt(s)`, `see.steps(s)`, `see.whatif(s, c, v)` | see.sheet(s) → the act |
| `see.menu(M)` | head.open(M) |
| `line.count(file, col, val)`, `line.keep(file, col, val)` | as above |
| `set.cell(s, c, v)` | see.sheet(s) → hand.cell(c, v) → verify by `office.get` |
| `make.file(path, text)` | hand.write (when the owner's words are `stacy_hand.made(text)`, H:173-190: no model) |
| `check.limit(x, L)` | read x, L and their bounds (one read set) → assess → VOI ranking → question to the owner if undecided (§7) |
| `recheck.page(p)` | `office.datasheet.recheck` (Free hand; otherwise a card that waits) → verify `replaces` |
| `tidy` | menu.close if popups ≠ ∅ |
| `put_back(snapshot)` | regression to the snapshot's surface, centre, face, sel, zoom (within one 0.10 step), over=none, popups=∅. Navigation only. The line is cleared only if its words are still ours. |
| `i05.application_chain` | preview → instantiate → methods.run → methods.result → joined.prepare → joined.run → joined.result (§9) |

### 3.5 Numeric weakest precondition (data goals)

```
wp(x := e, Q) = Q[e/x]            wp(a1; a2, G) = wp(a1, wp(a2, G))
wp(field.set(c := v), φ) = φ[v/c] ∧ revision(c's sheet) = expected      (compare-and-set, field_service.py:173-174)
wp(datasheet.recheck(p), φ) = φ[f_p(cells)/out_p] ∧ pre(recheck)
```

- Compile φ with `math_model.compile_expression` and take `affine(ir, free=(v,))` (`math_model.py:184-218`).
- For a linear relation c + k·v ⋈ 0, the boundary is v* = −c/k, exactly the root `sweep` reports (`math_model.py:246-256`).
- Products of two unknowns fall outside the linear form and go to interval bisection (§7).

**Worked example (After Hours 07):** G = "settled power stays within 6 W". This is an *answer*, not a plan to change anything:
- wp(field.set(B3 := v); recheck, G) = 12 V · v ≤ 6 W ⇒ **v ≤ 1/2 A = 500 mA**.
- With a recorded rail of 12 V ± 1 %: v ≤ 6 / 12.12 A = **50/101 A ≈ 495.04 mA**, shown as "up to 495.0 mA", rounded down because it is an upper bound.
- The pulse ceiling: I_start ≤ 8/12 A = 2/3 A.

A `field.whatif` at the boundary confirms it on the page (simulation, nothing changed).

### 3.6 What is deduced, and what is asked

| Deduced by Graphite (no model) | Asked of the model (enum answers only) | Asked of the owner (never the model) |
|---|---|---|
| The act sequence, its arguments and the form (pointer) | GOAL: which grounded goals answer the request, only when `hand_words.match` finds no single full match | Agreement on goals at Ask first |
| When to read; reads as one set | CHOICE: a meaning tie whose branches move the window or change data ("which current: settled B3 or startup B4?") | Every change that is not hers at this dial place; what always asks |
| Recovery after a refusal; repair after a surprise | OPTIONS: which next option, when no operator achieves the goal | Tolerances (`bounds.set`) |
| Returning existing evidence instead of a repeat | — | A measurement nobody can make on this computer ("a repeat capture at the load") |
| Interval verdicts, break-even, value of information | — | A model swap |
| Finishing, and tidying the window | — | — |

**A meaning tie whose branches are only reads is not asked: both branches are evaluated and shown.** For example, "is the pulse within the limit?" with Rev A and Rev B on the desk gives C1A holds and C1B does not hold, both shown. Asking would have zero value of information.

### 3.7 P01 as plans

| Goal | Plan | Acts |
|---|---|---|
| G1 | `see.menu(Tools)` | 1 |
| G2 | `line.count(seed, 07 Bench readings.csv, unit, mA)`: go.files → menu.open → menu.choose then → then.keep → then.count → then.end | 6, plus tidy's menu.close when head:Tools is still open |
| G3 | go.field → (point.zoom whole, only while `whole` is unknown) → sheet.trace. `go.field` already selects Bench (P1:92). | 2–3 |
| G4 | point.sheet Rev A or Rev B (equivalent, P1:118-122) → sheet.compare | 2 |
| **Total** | | **12–13**, against P01's 17 |

P01's `hand.write` is the owner's choice of content (the seed copy already has the data). `sheet.close` would delete G4. `hand.undo` is owner-only. None of the three is ever in her plan. P01 can still run them only because `door='script'` does not enforce OWNER_ONLY (D:1426-1429).

---

## 4. Execution (`workbench/hand_turn.py`)

### 4.1 The hand turn: receding horizon, one act at a time

The turn is driven by a zero-interval `QTimer` on the GUI thread, because desk acts must run there.

```python
def tick(turn):
    if turn.stop.is_set(): return turn.end('STOPPED')
    tree = desk_doers.read_desk(host, 'all'); S = planner.abstract(tree, turn.constants)
    goals.assess_all(turn, tree, kernel_reads=turn.pending_reads())     # records evidence the moment a goal holds
    if turn.surprised(S): turn.repairs += 1                             # expected effect missing, or a held persist goal lost
    if all_agreed_done(turn): return turn.finish()                      # tidy is a goal, so it is already planned
    plan = planner.plan(S, turn.open_goals(), methods=hand_methods.LIBRARY, budget=turn.budget)
    if plan is None: return turn.no_plan()                              # → OPTIONS (§6) or "I cannot do that from here"
    act = plan[0]; turn.expect = act.effects
    if turn.fingerprint(act, S) in turn.seen: return turn.end('WAITING', 'the same act on the same window did not help')
    env = desk_doers.run(host, act.name, act.args, door='her', origin='stacy-hand:' + turn.id, word=turn.request[:200])
    turn.record_step(act, env)                                          # hand-turn record + desk trail + the card's row
    if env.get('offered') or (env.get('result') or {}).get('waits'): return turn.wait_for_owner(act, env)
```

- **Work goals** use the same loop with a horizon of 3 and value-of-information ranking (§7). Their sensor is a Kernel read through `SlateFace.run_line`-style dispatch.
- **A turn that waits** (an offered navigation, a card that waits) resumes from the card's own callbacks (`stage(…, done=…)`, SH:2006). It never polls in a busy loop.

### 4.2 Verify, surprise and repair

**Verify.** The doer has already checked its ✓ effects; otherwise it returns FAILED. After the act, observed effects are compared with what the next `read.desk` shows. Evidence is recorded only from the read, never from the envelope's words.

**Surprise and repair by refusal code:**

| Code | Repair |
|---|---|
| NOT_HERE | The state was not what was assumed. Read, plan again. |
| UNSENT / PENDING | **An obstacle that belongs to the owner.** Stop and say so; never clear the owner's words. |
| DIALOG | Stop: the act reached a window that asks (D:1440-1441). |
| FAILED | Plan again once, then stop. |
| A held persist goal lost | Plan again (the owner or a refresh moved something). |

**Data writes that time out** are never retried blind:
- `field.set`: `office.get` decides.
  - Cell = v and revision ≠ expected: it landed; adopt it.
  - Revision unchanged: retrying is safe (compare-and-set).
  - Otherwise: plan again.
- Adaptive working writes: `continuing_work.reconcile_apply` (§9).
- Desk acts: `read.desk` plus the journal line with its correlation (D:1455-1466).

### 4.3 Stop at any moment

- **One flag:** `hand_turn.STOP`, a per-host `threading.Event`-like attribute.
- **Checked:**
  - in `run` before each act;
  - inside every press loop: `key` (D:262-265), `type_text` (D:268-276), `walk` (D:474), `wait_until` (D:70-78).
- **On a stop:** raise `Refusal('STOPPED', …)`. The act stops between presses, never halfway through a click.
- **Set by:**
  - "Stop" on her card;
  - Master Stop;
  - **any owner press or key outside her card while the turn runs**. Wheel and hover do not count, and neither do clicks on the card's own words.
- **How owner input is told apart.** The doers wrap each synthetic send (`mouse`, `right_click`, `key`, `type_text`, the `QTest.mouseClick` in `click_menu_row` D:333 and `choose_row` D:465) in `with hand_pressing(host):`. An application event filter, installed for the length of the turn, treats any `MouseButtonPress` or `KeyPress` delivered while that marker is off as the owner's.
  - Do not rely on `QEvent.spontaneous()`. QTest's click and key helpers mark their events spontaneous to imitate the window system, so the doers' own presses would read as the owner's.
  - Test: an act does not trip the filter; a posted press outside the marker does.
- **After a stop,** the card says: "You took the window back after step 2 of 5; nothing more was done." It offers "Put my window back", which is the `put_back` method, run at the owner's word.

### 4.4 The dial and what always asks

| Place | Reads | Navigation acts | Changes |
|---|---|---|---|
| **Ask first** | done | **offered**: the whole derived plan is listed on the card, with "Do these" (the owner's word for *this turn's navigation acts only*) | staged; every one waits |
| **Do and show** | done | done | HERS_SHOW done with Undo; others wait |
| **Free hand** | done | done | HERS_FREE as well. Her own noticing still does not start turns in this pass. |

- **What always asks** (H:46-57) is planned as a *wait node*. The plan shows it, the executor stages it and waits. The planner never looks for a route around it.
- **Owner-only acts never appear in her plans.** If the only achiever is one (for example `type.send`), the goal's last step is the owner's: "the line is in the writing line; only you send it".
- **`hand.step` with a read line** is ruled as an act that navigates, because it puts the steps page over the work (P2:39-43). `desk_hers` gets this rule (§5.2).

### 4.5 Budgets per turn

| Budget | Limit | Note |
|---|---|---|
| Acts | ≤ 24 | P01 is 17 |
| Wall time, excluding waits for the owner | ≤ 120 s | |
| Plans | ≤ 6 | |
| Consecutive surprises | ≤ 2 | |
| Same (act, args, abstract state) | at most once | the second time, stop with words |

Work loops keep `DEFAULT_BUDGET` (40 steps, 600 s; `agent_loop.py:122`).

**Progress measure:**
```
Φ = Σ_c (2·[open] + [cannot tell] + [recheck])
```
plus, per goal, the width of the slack interval.
- Each step must lower Φ, or be a read that narrows a slack.
- Two steps that do neither are a **stall**, which goes to escalation (§8).

---

## 5. Her door

### 5.1 `desk_doers.run(door='her')`

This replaces the refusal at D:1425. Outside a turn, the code `NOT_OFFERED` stays, with true words: "Stacy's hand acts only inside a turn you started."

```python
if door == 'her':
    turn = hand_turn.current(host)
    if turn is None: raise Refusal('NOT_OFFERED', REFUSALS['NOT_OFFERED'])
    if turn.stop.is_set(): raise Refusal('STOPPED', REFUSALS['STOPPED'])           # 'You stopped my hand; nothing more was done.'
    if ACTS[name].owner_only: raise Refusal('OWNER_ONLY', REFUSALS['OWNER_ONLY'])  # 'Only you do this.'  (today only desk_hers refuses, A:311)
    if isinstance(args, dict) and 'by' in args: raise Refusal('BAD_ARGUMENTS', 'How the hand moves is not mine to choose.')
    clean = desk_acts.check(name, args)
    line = hand_step_line(host, clean) if name == 'hand.step' else None             # field_do.steps_for (field_do.py:241): a read, nothing shown
    ok, why = desk_acts.desk_hers(turn.place_for(ACTS[name]), name, clean, line)   # 'show' for navigation after "Do these"
    if not ok and ACTS[name].mark == 'navigates':
        return offered(envelope, why)                                              # nothing done; journal state OFFERED
    c.asked = turn.asked; c.expect_target = turn.expect_target; c.door = 'her'      # changes go on: stage decides and waits if not hers
```

**Other changes in D:**
- `Ctx` gains `asked`, `expect_target` and `door`.
- `stage_change(…, asked=c.asked)` (D:663). `field_page.stage_set` and `take` gain an `asked` parameter; they hard-code True today (FP:324, FP:517).
  - `asked` is True when the turn came from the owner's words.
  - It is False for her own noticing (allowed at Free hand only, H:14-15; not started in this pass).
- `walk` (D:469) refuses with NOT_HERE when `root_menu(host).target.label != c.expect_target`. Today it walks any open menu (D:979-983).
- `record` (D:1455-1460) gains the states OFFERED and STOPPED. Origin is `stacy-hand:<turn>`; correlation is `<turn>:<n>` when the Kernel gives none.
- **Kernel principal: unchanged** (`operator()` in `run_staged`, SH:2051-2058). Her changes are made in the owner's window, on the owner's behalf, as "set B3 to 300" said to her is today. "Hers" is recorded in the journal's origin and in the trail. A principal of her own would split ownership of the owner's records (`owned()` checks), so it is not in this pass.

### 5.2 What is hers without asking (`desk_hers`, A:299-339)

| Act kind | Ask first | Do and show | Free hand |
|---|---|---|---|
| `read.desk`, Kernel reads | hers | hers | hers |
| Acts that navigate (and `hand.step` with a read line: **new rule**) | offered | hers | hers |
| `hand.write` new path / taken path | waits / waits | hers / waits (D:1243-1248) | hers / waits |
| `hand.cell` | waits | hers | hers |
| `hand.trash` (shown as DELETE) | waits | **waits until it has an Undo** (§5.4) | same |
| `hand.rename` | waits | waits | waits |
| `hand.step` with a write line | per `hers(line's operation)` | | |
| owner-only | never | never | never |

**Two fixes in H:**
- `why_waits` (H:161-164) says "it is not among the things I do by myself" even when the real reason is the dial. At Ask first, for an operation on HERS_SHOW or HERS_FREE, it now says "my hand is at Ask first".
- `desk_hers` checks `by` and owner-only first. Its export (`tools`, `plan_variants`, A:353-374) stays as it is. Nothing is removed, but her model is not offered it in this pass: the GOAL catalogue (§6) replaces it for the model.

### 5.3 How each act is shown to the owner

**1. Her column: one hand card per turn** (`Card`, SH:2927, in the conversation). In 0.8.3 the picture moves to the lower left, so this column has the room for it. The card draws with the appearance's faces, so 0.8.3's typewriter face carries over, and it names no font itself. Example:

```
For “trace 07 Bench readings and put Rev A beside Rev B”
  holds   The trace of “07 Bench readings” is shown                seen
  open    “07 Limits Rev A ARCHIVED” and its other revision side by side
   1  Bring the Field to the front, on its work face               done
   2  Select “07 Limits Rev A ARCHIVED”                            done
   3  Compare it with its other revision, side by side             next
   4  Select “07 Bench readings”
   5  Trace it: where it comes from and what rests on it
                                                                   Stop
```

- **Row words** are the act's own words (`ACTS[name].words`) with the arguments filled in. They print no key, call the line language "a line", and say "Apps".
- **Row states:** next / done / offered / waits for your Approve / refused (with the refusal's words) / stopped.
- **At Ask first** the card shows "Do these". At the end it shows "Done in 5 acts; both hold." and "Put my window back".
- **Changes keep their own stage cards** (SH:2006-2045): Approve, the why, the line in a code label, Undo.

**2. The pointer on the window.**
- Before each pointer act, `desk_doers.show_hand(host, widget, point)` draws a small ring in her colour at the place the press will land, on a `WA_TransparentForMouseEvents` overlay.
- It grows over 0.22 s and then the press happens. With less motion (`look_now` motion = reduced, D:652-658) the ring is held still for 0.3 s.
- Keys-form acts are not used by her door, so no key is ever shown.
- An optional hook, `kasandra_art.note_hand(host, moving)` beside `note_outcome` (`kasandra_art.py:232`), lets the 0.8.3 hologram's static show that her hand is on the window. How it looks is that pass's decision.

**3. The trail.**
- Navigation goes to a **desk trail**, `stacy_hand.DESK_TRAIL = 'stacy_desk_trail'`, keeping 200 entries of `{at, turn, n, act, words, state}`. It is kept separate because `stacy_trail` keeps 40 (H:34) and P01 alone is 17 acts.
- The trail view (SH:2166-2181) shows both trails interleaved by time under "What I did". Undo appears only on data entries.

### 5.4 Undo where data changes

- **`field.set`**: unchanged (`takes_back`, H:197-200).
- **Files she made**: unchanged (`/files.trash` with a sha256 guard, H:201-215).
- **DELETE (the owner's word for the Trash in 0.8.3).**
  - **The operation stays `files.trash`.** Renaming it to `*.delete` would match ALWAYS_ASKS (H:50) and change behaviour.
  - This pass gives it an exact Undo. `files.trash` returns `{'trashed', 'id'}` (`files_service.py:510`), so `takes_back('files.trash', …)` returns `/files.restore {"id": "<32 hex>"}`.
  - `UNDOES` gains `files.restore`. `undo_allowed` accepts exactly `{'id'}` matching `[0-9a-f]{32}`.
  - The Undo runs at the owner's click, so its approve scope is the owner's (`files.restore` is approve, `files_service.py:72`).
  - Until this slice lands, her door keeps `hand.trash` waiting at every place. Today it is done at Do and show with no Undo (P1:179-183).
- **The window:** "Put my window back" (§3.4).

---

## 6. The model's contract

### 6.1 Three questions

| Turn | When | Answer schema | Max output |
|---|---|---|---|
| **GOAL** | `hand_words.match` finds no single fully grounded match | `{"goals":["G3","G7"]}` | 32 tokens |
| **CHOICE** | a meaning tie whose branches move the window or change data | `{"choice": n}`, n ≤ 9 (existing mode, LB:892-896, LB:915-920) | 24 tokens |
| **OPTIONS** | no plan achieves the goal, or a stall | `{"choice": n}` over the planner's ranked options | 24 tokens |

`brain.ask`'s mode enum (LB:57) gains `'goal'`. GOAL and CHOICE turns carry **no dialogue history**: the desk summary replaces it. CHOICE already uses only the last 2 messages (LB:896).

### 6.2 GOAL: grounding, schema, prompt

**Grounding** (`hand_words.candidates(request, desk, kernel)`):
- Templates (§3.4) are instantiated over the objects in sight and in the request: sheet titles via `find_sheet`'s exact-then-unique-substring rule (D:196-208), files in the folder, columns and values of a named file, and same-dimension cell pairs for `check.limit`. Pairs are filtered hard by `math_units.unit_spec` dimension equality.
- Candidates are ranked by word overlap, as `tool_selection.relevant` does (`tool_selection.py:94-140`). At most 16 are kept, plus G0 ("none of these").
- **A single full match skips the model.** Examples: "trace 07 Bench readings"; "how many mA rows in 07 Bench readings.csv" (where mA is a distinct value of exactly one column, `unit`); "set B3 of 07 Bench readings to 300".

**Schema** (strict, with no optional keys):

```json
{"type":"object","additionalProperties":false,"required":["goals"],
 "properties":{"goals":{"type":"array","minItems":1,"maxItems":3,"uniqueItems":true,
   "items":{"type":"string","enum":["G0","G1","G2","G3","G4","G5","G6","G7","G8","G9","G10","G11","G12","G13","G14","G15","G16"]}}}}
```

**Prompt.** The system part is fixed text, so the prefix can be reused through `slate_stream.prefix_key` (`slate_reasoning.py:263-283`). Every generation consumes the slot claim (`slate_stream.py:69-76`), so reuse is measured, not assumed.

```
system: You choose what must be true when Stacy's hand is done. Below are the owner's request, the desk as it is now,
        and numbered goals Graphite can plan and check. Choose the one to three goals that together answer the request,
        in the order the owner asked. Choose G0 alone if none fits. Answer only as JSON {"goals": [...]}. Do not explain.
user:   Request: show me where the bench readings come from, then put the limits side by side
        Now: The Field is in front, its work face. “07 Bench readings” is selected. Nothing is open over it.
        Goals:
        G1 The trace of “07 Bench readings” is shown
        G2 “07 Limits Rev B CURRENT” and its other revision are side by side
        G3 The doubts about “07 Bench readings” are shown
        …
```

**Validation:**
- Parse with `record_io.strict_json`.
- If G0 appears together with other goals → `MODEL_GOAL_INVALID`.
- Goals are agreed:
  - at Do and show and Free hand, when chosen; they are listed on the card first and any one can be struck;
  - at Ask first, when the owner says "Do these".
- Model goals have `origin: 'HER'` and `agreed_by: 'request'`.

### 6.3 CHOICE and OPTIONS

**CHOICE** example:

```
Which current do you mean?   1 Settled current (B3, 280 mA)   2 Startup current (B4, 650 mA)
```

- If the records justify a default, it stays primary, as in `agent_loop` (`agent_loop.py:47-49`). The model is asked only when no default is justified.
- **OPTIONS** are the planner's ranked next options: value of information over cost for work (§7), `investigations.next_action` order otherwise (`investigations.py:259-272`). The question to the owner is always one of the options.

### 6.4 Token and time budget: a 4B at 4,096 context

Rates measured on this 4-core CPU (model-path reader §4): prefill 56–75 tokens/s, decode 4.1–5.6 tokens/s, with dips to 1.5.

| Turn | Prompt cap | Output cap | Check (prompt + output + 32 ≤ 4,096, LB:476) | Expected here |
|---|---|---|---|---|
| GOAL | 1,200 (≈ 220 system + 100 request + 80 now + 16 × 25 goals + room for ≤ 200 tokens of learned examples) | 32 | 1,264 ✓ | 11–21 s prefill + 2–6 s decode, so **≈ 15–27 s** |
| CHOICE / OPTIONS | 800 | 24 | 856 ✓ | ≈ 10–20 s |
| Deadline per turn | 60 s (≥ 2× the worst case above) | | | |

**Comparison:** today's I05 SELECT alone read 2,529–2,926 prompt tokens and wrote 138–144 at 69–75 s (LOG:32-37, LOG:82-87). The ThinkPad's rates are measured by the campaign. The caps are set so the 4B fits here, and the 35B-A3B (3B active) should do no worse.

### 6.5 When the answer is wrong or late

| Case | What happens |
|---|---|
| Invalid JSON or outside the enum | `MODEL_GOAL_INVALID`. No act runs. Fall back to the deterministic candidates, shown on the card as words the owner can pick (the owner's pick is agreed). |
| Late (60 s) | The job is cancelled (LB:1015-1018 path). Same fallback; the card says "I could not settle what you meant in time". Escalation (§8) runs only if the owner asks again or the goal is work. |
| G0 | "I don't have a way to do that on the desk yet." The existing plan mode (`brain.ask mode:'plan'`, SH:2616-2635) still answers in words. |
| Wrong goal | Visible on the card before or while acts run. Every navigation is reversible by "Put my window back"; every change sits under her hand with its Undo. The owner strikes the goal or presses Stop. The pair (request words, struck goal) is recorded as a failed example in the instruction matrix (LB:885-889), as data, never as authority. |
| No brain running | Deterministic path only; says so. |

---

## 7. Intervals and value of information on After Hours 07

### 7.1 Where tolerances are recorded: `ledger.bound/1`

There is no place today:
- Office cells are closed at 7 keys (`office_tables.py:43-44`).
- Reviewed rows are closed too (`datasheet_work.py:14-20`).
- `math_model` `lower`/`upper` are domain bounds (`math_model.py:34`).
- staC `Observation` has no error field (`stac/quantities.py:105-112`).

The new record:

```python
{ 'id', 'kind':'bound', 'schema':'ledger.bound/1',
  'address':'office:owner:db5f…', 'cell':'B5', 'revision':'69dada6f…',
  'form':'abs' | 'rel' | 'range',  'value':'5' | '0.01' | ['105','115'],  'unit':'ms',
  'basis':'Scope cursor resolution at 5 ms/div (the owner’s words)', 'set_by':'OWNER', 'created' }
```

- **Set only through `bounds.set`, which always asks.** She may *propose* one, for example from a datasheet's words "accuracy ±1 %", as a card that waits. **A bound she invents is the worst failure this design can have.**
- The owner can say it in words: "B5 of 07 Bench readings is good to 5 ms". `hand_words` parses that into the staged card.
- A new revision of the sheet makes the bound "recheck" unless the bound cell's value is unchanged, in which case it is rebound.

| Form | Interval (Fractions, base units via `math_units.unit_spec`/`rational`, `math_units.py:23-47`) |
|---|---|
| abs, x ± e | [x − e, x + e] |
| rel, x ± r | [x(1 − r), x(1 + r)] for x ≥ 0 |
| range | [lo, hi] |

### 7.2 `workbench/bounds.py`

**Operations** (all exact over rationals):

| Operation | Result |
|---|---|
| add | [a+c, b+d] |
| sub | [a−d, b−c] |
| mul | [min(ac, ad, bc, bd), max(…)], with dimensions carried |
| div | [a,b]·[1/d, 1/c]; `DOMAIN_ERROR` → cannot tell when 0 ∈ [c,d] |
| neg | [−b, −a] |
| integer power | endpoint powers; for even n with 0 inside, [0, max] |

**Evaluation and soundness:**
- `enclose(ir, boxes)` mirrors `math_model.values()` over the node list (`math_model.py:90-124`).
- Inclusion monotonicity makes the enclosure sound.
- Each variable occurs once in L − T and V·I, so the enclosure is exact there.
- For a linear predicate, the exact range comes from `affine()`: c + Σ min/max(kᵢ·loᵢ, kᵢ·hiᵢ).
- Past the 2048-bit cap (`math_units.py:50-52`), endpoints are widened outward, which keeps the enclosure valid.

**`verdict(S, rel)`**, using the slack S of the predicate:
- for ≤: holds iff lo ≥ 0; does not hold iff hi < 0; else cannot tell.
- for <: holds iff lo > 0; does not hold iff hi ≤ 0.

There are no floats, so equality is decided exactly.

**`decisive_share(ir, boxes, var)`:**
```
φ_i = |{x ∈ X_i : S(X_−i, x) lies on one side of 0}| / |X_i|
```
- Exact when S is affine or monotone in xᵢ: solve the boundary as `sweep` does.
- Otherwise a sound lower bound by bisecting into 64 pieces.

**`break_even(…)`:** the largest symmetric error that keeps the verdict. For x ± e against a limit L with x > L, it does not hold robustly iff e < x − L.

**Value of information ranking:**
```
score(r) = Σ_c w_c · φ_c(r) / cost(r)
```
- w_c = 1 for an undecided agreed goal; 0 for a decided one.
- For a conjunction, a robust false conjunct decides it, so the other conjuncts get w = 0 (Belnap: false wins, `stac/evidence.py:78-82`).
- **VOI = 0 whenever S is already on one side.** Any reading consistent with the recorded bound lies inside it, so the new slack lies inside the old one. A new reading is intersected with the old; an empty intersection makes the goal undecided ("the two readings cannot both be right").

### 7.3 Worked numbers

Exact, checked by `iv.py`. **Only the ±5 ms is the task's recorded bound. The V ±1 % and I ±2 % are illustrative, since no bound is recorded today.**

| Goal | Predicate | Inputs | Slack S | Verdict | Value of a better reading |
|---|---|---|---|---|---|
| **C1B** | B5@Bench ≤ B4@Rev B | T = 110 ± 5 ms (recorded); L = 80 ms | 80 − [105, 115] = **[−35, −25] ms** | **does not hold, robustly** | 0. A ±1 ms reading gives [−31, −29], inside the old slack. **Break-even e < 30 ms**: at e = 30, S = [−60, 0] → cannot tell. |
| C1A | B5@Bench ≤ B4@Rev A | same; L = 120 ms | **[5, 15] ms** | holds | robust while e ≤ 10 ms |
| C2 | Startup power (`500c…`, V·I) ≤ 8 W | V = 12 V ± 1 %, I = 650 mA ± 2 % | P = [7.56756, 8.03556] W, so **S = [−0.03556, 0.43244] W** | cannot tell | Measure current first: φ_I = **6989/7878 ≈ 0.887**, φ_V = **3089/3978 ≈ 0.777** (bisection lower bounds 56/64 and 49/64). Holds robustly iff (1+r_V)(1+r_I) ≤ **40/39**; with r_V = r_I, r ≤ √(40/39) − 1 ≈ **1.27 %**. |
| C3 | Settled power (`0e39…`) ≤ 6 W | same V; I = 280 mA ± 2 % | [3.259872, 3.461472] W → S = **[2.538528, 2.740128] W** | holds | 0 |
| HOLD page | "Rev B allows this pulse" = C1B ∧ C2 | | | **does not hold, robustly**, because C1B does | VOI of V and I = 0 for this decision. Only the page's separate sentence "clears the wattage ceiling" (C2 alone) has value. |

**The words on her card (C1B, with ±5 ms recorded):**
> Does not hold. The startup pulse ran 110 ms, measured to within 5 ms; Rev B allows up to 80 ms. It is over by 25 to 35 ms whatever the true value within those 5 ms, so a finer measurement would not change this. Only an error of 30 ms or more could.

**Without a recorded bound,** she states the point verdict and the break-even ("this stands unless the reading is off by 30 ms or more"). She never assumes a tolerance.

**Which limit applies** ("Rev B applies to this run", on the conclusion page) is the owner's binding, recorded in `bind`. It is never deduced from condition strings, which `assess_upper_bound` would refuse (`stac/quantities.py:138-140`). Both C1A and C1B are shown (§3.6).

**Repair example:** the owner sets B5 to 100 ms (`field.set`).
1. The Bench revision changes, so C1A and C1B are marked recheck.
2. B5 is re-read as 100.
3. C1B: 80 − 100 = −20, does not hold. C1A: 120 − 100 = 20, holds.
4. The card shows "Recheck · 07 Bench readings was saved again", then the new states. The ripple's words ("would say 20 ms") are left to `field_ripple` and not rewritten here.

**The question for "what stretched the startup pulse?"** has no operator on this computer that adds it. Her OPTIONS put the owner's own next step first, "a repeat capture at the load", and she asks.

---

## 8. Escalation

**Triggers:**
- a GOAL or CHOICE turn is invalid or late;
- G0 while deterministic candidates are tied;
- a stall (§4.5);
- an adaptive decision fails (`consume_pending`, AW:389-397).

**The ladder, cheapest first.** Each rung is recorded in the turn or work.

1. **Ask less.**
   - Deduce more (method continuation, single ready producer).
   - Use a single phase.
   - **Reuse a SELECT that landed.** J2's SELECT was valid and written to `action-selection.txt` (SA:182) before its ARGUMENTS phase timed out. Under the same frame binding (SA:113-124) it can be reused.
2. **Think, then choose.**
   - A free-text notes turn (no schema, ≤ min(256, measured decode rate × 60 s) tokens).
   - Then the same strict turn with "Notes: …" appended.
   - This avoids `enable_thinking` under a strict JSON grammar. Thinking is off globally (LB:471) and pinned in the adaptive model binding (SA:72).
   - Cost here: about 60–80 s.
3. **Self-consistency.**
   - k = 3 strict turns with the candidate order permuted: identity, reversed, rotated by one. Temperature is 0 (LB:477), so the permutation is the only variation.
   - Majority on goal identity (for GOAL: the same set), not on the number.
   - No majority → rung 4.
4. **A batched model swap under her hand.**
   - Staged with `SlateFace.stage` as the line `/brain.model.use {"id": …, "options": …}`, approve scope.
   - It is never hers: it is on no list (H:39-42). Model proposals cannot contain it (`stacy_control.py:286-291`), so it is the planner, not the model, that stages it.
   - **Batching:** turns that need the larger model are queued. The card appears once. The swap runs only when no reply or ACTION job runs (`run_model_job` refuses otherwise, LB:515-517). Then the queued turns run, then `brain.restore` is staged (approve) to swap back.
   - **Memory admissibility gate** (`planner.admissible`):
     ```
     M_resident + max_t Σ_{i: sᵢ ≤ t < eᵢ} mᵢ ≤ budget_room(available, reserve, future, credit)   (resource_control.py:66-71)
     ```
     - Checked with `schedule_math.evaluate` in process on an in-memory problem (`schedule_math.py:16-63`).
     - The resident model is one allocation that releases at the handover. The sweep's release-before-allocate at a boundary (`:52-55`) is exactly `credit`.
     - KV and compute buffers are explicit allocations, because the sweep models no overhead (`:47-48`).
   - **Example** (illustrative 32 GB budget; the 35B weights are 20.542732576 GB, `gguf_fixture.py:27`):

     | Schedule | Peak | Verdict |
     |---|---|---|
     | Overlapping: 35B [0, 600) + KV 3 GB [0, 300) + dense 16 GB [300, 600) + read 1 GB [250, 320) | **37.542732576 GB** at [300, 320) | INFEASIBLE |
     | Same, but the 35B released at 300 s | **24.542732576 GB** | FEASIBLE |

     Here: the 2B (1.28 GB file) hands over to the 4B (`memory_mb` 4,480, `joined_model_checks.py:96`). The card shows the feasible schedule's words.
   - **Vision models** are refused for chat (LB:217), so vision escalation is not in this pass.
   - **Swaps inside adaptive work** stop it (`ADAPTIVE_MODEL_CONFIGURATION_CHANGED`, AW:30), so adaptive work escalates only to rung 3 in this pass. It then waits with "needs a larger model" as its reason.

---

## 9. The I05 experiment: the current loop against the conditions loop

**Arms.** Same model file and binding, same problem, method, grant, copies, budgets, threads and seeds.

| Arm | What it is |
|---|---|
| **A (current)** | `adaptive_work` as is: two-phase SELECT/ARGUMENTS each decision, 180 s (`adaptive_contract.py:26`), frozen spec `ledger.i05-model-family-spec/1` with "no model choice injection or automatic retry" (`joined_model_checks.py:95`) |
| **B (conditions, planner-first)** | its own frozen spec `ledger.i05-conditions-spec/1` declaring the interventions below |
| **C (optional ablation)** | B without deduction (conditions view + evidence return + landed-check only), to separate "asked little" from "a graph of conditions" |

**What B changes:**
1. **Conditions at `initialize`** (AW:62-69): `state['conditions']` comes from the order's completion policy.
   - K1 = a current `joined.result` AVAILABLE carrying all four `APPLICATION_TYPES` (`adaptive_contract.py:13`).
   - K2 = a current `methods.preview` whose precondition is rejected (AW:178-181).
   - K1 decomposes by `i05.application_chain` into K1a–K1g, one per producer.
2. **Deduction at the decision branch** (AW:426-431). If the next open sub-condition has exactly one ready producer with settled arguments, the coordinator writes `state['choice']` itself with `origin:'COORDINATOR_DEDUCED'`. Settled means every required argument is a single-value enum from `producer_readiness` (AW:125-161), or comes from a `method_continuation` (SA:8-29). `validate_call`, the gate and the grant still run (AW:254-296, :422), so deduction gains no authority. After a SUPPORTED preview, every step to `joined.result` is deducible:
   - instantiate, from the continuation;
   - `*.run`, because `action` and `expected_digest` are single enums;
   - `*.result`, because `job` is a single enum;
   - `joined.prepare`, because `receipt` and `method_job` are single enums.
3. **Model turns in B:**
   - **MAPPING**, once, for `methods.preview` when no continuation exists. All slots are enums: each typed method input → enum of the problem's variable names of that type. No optional keys, about 45 output tokens, prompt ≤ 2,000 tokens.
   - **FINISH words**: ≤ 400 characters, citations fixed by the coordinator to the observations that hold the conditions. The model writes words only.
   - SELECT runs only if two or more sub-conditions are open with ready producers and no method orders them. That never happens in I05.
4. **Duplicate guard → existing evidence** (AW:435). Find the observation with the same operation, canonical arguments and current `context_digest` (rows store all three, AW:330-333). Dispatch nothing. Record `{returned:'O<n>'}` and set READY with `EXISTING_EVIDENCE_RETURNED: O<n>`. Nothing is charged, because charging happens at :446. A second repeat restores today's WAITING.
5. **A write that times out:** on an exception or `ADAPTIVE_STEP_TIME_LIMIT` for a working write, call `continuing_work.reconcile_apply`.
   - Landed: `finish_item` with the recovered commit.
   - Partial: WAITING with `PARTIAL_APPLICATION_REQUIRES_CHANGES_RECOVERY`.
   - Nothing landed: a retry may be proposed.
6. **The finish rule.** `apply_decision`'s FINISH check (AW:363-366) also requires every agreed condition to be held by a current observation.
7. **The SELECT shape** (when it runs): no `why`/`uncertainty` prose (today 180 and 160 characters, always filled to the cap, SA:177-178), compact JSON, and the frame view showing open conditions plus the last 6 observations. Target ≤ 2,000 prompt tokens, so B also runs at **4,096 context**.

**Runs:**
- **Here:** the 4B at 6,144 context for both arms (A's spec), plus B at 4,096. Three repeats per arm (temperature 0, so repeats measure CPU variance). A and B are interleaved, with `posix_fadvise DONTNEED` before each, as the trial does today.
- **ThinkPad:** the 35B through the campaign runner (`tools/campaign_lib/runner.py`), same harness, the owner's context setting, three repeats per arm.

**What is measured** (per case and arm, from the work state, the decision receipts and the journal):

| Measure | Source |
|---|---|
| Outcome: REVIEW with completion evidence satisfied / WAITING (reason) / LIMIT | `flow.load` state and reason |
| Model turns; coordinator-deduced steps; evidence returned instead of repeats; timeouts and how each was reconciled | B's step records |
| Prompt and output tokens per turn; peak prompt tokens; seconds per model turn, per tool step and in total; tokens/s (prefill and decode); `cache_n` | `metrics`, `timings` (`slate_stream.py`) |
| Conditions agreed / held at finish; Φ per step; FINISH citations valid | `state['conditions']` |
| Artifact digests (equal between arms when both pass) | `joined.result` receipt |
| Model binding, executor digest, CPU load note | spec files |

**Pre-registered expectations:**
- A with the 4B fails as before: `LOCAL_STREAM_TIME_BUDGET` at decision 2, 328.6 s, 17,858 tokens (R2:1353, :1369-1371).
- B passes with ≤ 3 model turns (MAPPING, maybe none if a continuation exists, and FINISH), each under 60 s here, and well under half of A's model tokens.
- B never dispatches a repeat, and never finishes without held conditions.

**A failure of B is reported as such, with the step that failed.**

---

## 10. Build order

Each slice can ship on its own, with its tests and scenes. New scenes need one schema addition (`graphite.scene/1`, SC:72-104, additive):
- a step may be `{"say": "<owner words>", "dial"?: …, "interrupt_after"?: n, "expect": {…}}` instead of `{"act": …}`. It starts a hand turn and waits for its end.
- `expect` may read `turn.*` (the hand-turn record) as well as `act.*` and `desk.*`.
- `check_scene` accepts `say` steps; `run_scene` plays them through `hand_turn.start(host, words, origin=…)`.

| # | Slice | Files | Tests | Scenes | Done when |
|---|---|---|---|---|---|
| **S0** | `read.desk` additions; `route_said` fix; desk trail store; `why_waits` at Ask first; `desk_hers` rule for a `hand.step` read line; the Approve tooltip's key removed | D, A, H, SH:2035 | `test_desk_acts.py`: new parts present and typed; route None after the selection moves; key-literal check (T:243) extended to every new file | P01 still passes in all four runs | P01 unchanged; new parts read back |
| **S1** | Conditions engine core and bounds | `goals.py`, `bounds.py`, `ledger.goal/1`, `ledger.bound/1`, `goals.*`, `bounds.*` ops | `test_goals.py`: states, staleness, rebind on an unchanged value, the store round trip, no float anywhere (assert Fraction). `test_bounds.py`: every number in §7.3 exactly; division by an interval holding 0; outward widening at the cap | — | AH07 C1A/C1B/C2/C3 assessed exactly from the seed |
| **S2** | Planner core (no Qt) | `desk_ops.py`, `planner.py`, `hand_methods.py` | `test_planner.py`: P01 milestones → 13 acts with `whole` unknown, 12 with it read true; G3∧G4 jointly → 5 acts; owner-only acts never planned; measured cells never achievers; `TOO_FAR` at the budget; forward simulation of every plan; v ≤ 1/2 A and 50/101 A by weakest precondition; < 0.5 s | — | plans match the reader's toy |
| **S3** | Her door | D `run(door='her')`, Ctx `asked`/`expect_target`, stop flag and input filter, OFFERED/STOPPED in the journal, pointer ring (`hand_qt.py`), DELETE Undo via `files.restore` | T:575 updated (still NOT_OFFERED outside a turn); OWNER_ONLY; `by` refused; offered at Ask first; owner input stops between presses; the doers' own presses do not trip the filter; trash → `/files.restore` Undo restores | **P02** "Her door at three places" (Ask first offers and nothing moves; "Do these" runs; Do and show runs; owner-only refused). **P03** "The owner takes the window back" (`interrupt_after: 2` → `turn.outcome` STOPPED, 2 acts done) | her door runs every planned act under `desk_hers` |
| **S4** | The hand turn without a model | `hand_turn.py`, `hand_words.py` (deterministic matches), the hand card, "Put my window back" | `test_hand_turn.py`: finish rule, budgets, fingerprint stop, surprise repair, put-back plan | **P04** "P01 by her words" (four `say` steps; P01's milestone checks; `turn.acts` lte 13). **P05** "Out of sight" (zoom 150 %, "trace 07 Bench readings" → route shown, `turn.plans` lte 2). **P06** "Data under her hand" (set B3 to 300 at Do and show → done with Undo; at Ask first → waits; DELETE with Undo) | P04 passes by pointer, with less motion, in two runs |
| **S5** | The model's contract | LB `goal` mode; candidates; CHOICE use; fallbacks; instruction-matrix marks | `test_hand_model.py` with a fake worker: schema, G0 rules, invalid → fallback, late → fallback, struck goal recorded | **P07** (campaign, 4B): "show me where the bench readings come from, then the limits side by side" → GOAL turn; `turn.model.seconds` lte 60 | the 4B answers GOAL within budget in three runs here |
| **S6** | Work goals on the desk | `check.limit`, `set.cell`, `recheck.page` methods; VOI ranking; card rows; WorkBlock rows; refresh hook after `field.set` | AH07: C1B does not hold; after the owner's `bounds.set` ±5 → "over by 25 to 35 ms"; B5 := 100 → recheck → new states | **P08** "Limits" (`say` "is the startup pulse within the limits?" → both C1A and C1B shown; no question asked) | — |
| **S7** | I05 arm B | AW conditions, deduction, evidence return, landed-check, finish rule; SA MAPPING and FINISH turns; `ledger.i05-conditions-spec/1`; the A/B harness | `test_adaptive_contract.py`/`test_joined_work.py` additions: deduced steps pass `validate_call`; a repeat returns O<n> and charges nothing; FINISH refused with an open condition | — | A/B results here; the ThinkPad kit prepared |
| **S8** | Escalation | think-then-choose, self-consistency, swap card with the admissibility gate, swap back | `test_hand_model.py`: majority rules; the swap card waits at every place; the INFEASIBLE schedule is not proposed | — | — |

**Not in this pass:**
- Her own noticing starting turns (Free hand initiative).
- A Kernel principal of her own.
- Keys-form acts for her.
- `point.move`, `go.app`, `head.meter`, `type.room` and `look.set` in her plans.
- Model swaps inside adaptive work; vision models.
- Bounds she sets (always the owner's).
- Measurements made by Graphite.
- Non-uniform priors in value of information.
- Plans that span sessions.
- Partial-order or contingent planning.
- Rewriting finding words from slack.
- Offering `tools()`/`plan_variants()` to her model (kept, unused).
- 0.8.3's look itself (DELETE as the word on screen, the typewriter face everywhere, the hologram and its static lower left, the right column, the new kp emblem). This pass only reads the appearance's faces and leaves the `note_hand` hook for the hologram.
- Nothing is removed; what always asks still asks.

---

## Appendix A: owner-rule hazards on this path

- **A key on screen.** The Approve tooltip says "in the Field, G does the same" (SH:2035). It is fixed in S0, and her card must not copy it.
- **"Programs" on screen.** Some errors reach the screen through "I could not start: …" (SH:2633), and LB:623, :631 and :633 say "Programs". Change their words to "Apps" in S5, when hand turns can surface them.
- **"held" and "BROKEN".** On screen they keep their Field meanings. Goals say holds / does not hold / cannot tell / open / recheck.
- **The line language** is never named. The card calls `then.end line` "a line in the writing line".
- **DELETE.** It is the word on screen; the operation stays `files.trash` (H:50).

## Appendix B: decisions for the owner

1. **At Ask first,** "Do these" lets her do *this turn's* navigation acts. Changes still wait one by one.
2. **Her changes keep your Kernel identity;** the journal's origin and the trail say they were hers.
3. **DELETE gets an exact Undo** through `files.restore`, run by your click. Until then her DELETE always waits.
4. **When the limit sheet is ambiguous,** both are evaluated and shown rather than asked.
5. **Tolerances are yours only:** she may propose one, never set it.