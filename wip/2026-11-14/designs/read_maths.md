# Maths already in Graphite, and where conditions and evidence live

Graphite already does exact arithmetic with units, propagates a changed number along the wires, computes peak memory overlap, has a four-valued evidence lattice and runs two small searches. No record holds a measurement error bound today. In After Hours 07 the "Up to 80 ms" limit lives only as words in one cell and as a number in another, and the only check on it can't fail. Proposals (a) to (f) below build on those parts and need only the standard library (`fractions`, `decimal`, `itertools`).

I ran reads only, on a copy of the restored After Hours 07 workspace in the scratch area. No model was loaded and nothing was written to the repository.

---

## 1. The what-if ripple (`workbench/field_ripple.py`)

**Inputs.** A sheet or a calculation, plus 1 to 8 cells, each set to a number written as text of up to 40 characters (`field_ripple.py:114`). A cell can be named by its address, by the words of its row, or by a calculation input's symbol (`cells_named`, `:60-81`).

**What it reports, row by row** (`ripple`, `:107-226`):

| Row | What it does | Arithmetic |
|---|---|---|
| set | The cell as it is and as it would be (`:136-144`) | "moved" uses floats with relative equality: `_number` is `float()` (`:42-46`), `_same` allows 1e-9 relative (`field_doubt.py:64-67`) |
| says it, same sheet | Text cells on the same sheet that repeat the old number (`:145-149`) | Base-unit float match |
| reads it | Each calculation that reads a set cell is worked again with its own recipe through `datasheet_work.what_if` (`:168`, `datasheet_work.py:268-316`) | **Exact**: rationals through `math_model.compile_expression` and `evaluate`, `'arithmetic':'EXACT_RATIONAL'` (`math_model.py:147`). The rational is shown in the reason (`field_ripple.py:173`) |
| reads the sheet | Calculations of the sheet that read other cells: the result would not move, but saving sends them to recheck (`:161-166`) | Invalidation is per sheet: `report_state` compares the whole sheet revision (`datasheet_work.py:174-175`) |
| says it, findings and pages | Quantities in their words matched to moved values (`:180-200`) | `measure()` turns a quantity into base units as a **float** (`field_doubt.py:78-99`). `_made_with` tries only `other−old`, `old−other`, `old+other` with one moved value (`field_ripple.py:229-241`) |
| checks it | A check's own program is run on the would-be sheet and its own expectation applied (`_check_would`, `:84-104`, called at `:212`) | Text oracle (`investigations.py:108-119`) |
| watches it | An investigation that watches the sheet (`:220-222`) | none |

**What it does not follow.** A finding that compares in words ("allows 6 W"), totals bound to a page, and Agenda watches (`NOT_WORKED`, `:30-31`). Nothing is written (`'changed': 'nothing'`, `:226`).

**Units.** Quantities are compared in base units (`field_doubt.py:78-99`, `said_quantities` `:102-116`). A cell's unit is its own `unit` or column C of its row (`unit_of`, `:119-124`).

**Run on After Hours 07:**
- B3 280 → 300 mA: Settled power 3.36 → 3.6 W, shown exactly as `18/5 W`. The finding "Settled draw is 3.36 W…" and the conclusion page would move. Startup power 7.8 W does not move but would go to recheck.
- B5 110 → 100 ms: no calculation moves. The finding "Startup ran 30 ms past…" would say 20 ms, and the page's 10 ms would become 20 ms. Both were found only by `_made_with`, because no calculation records 30 ms.

## 2. Exact arithmetic and units

- **`math_units`.** Four base dimensions: time, voltage, current, memory. Power is V·A (`math_units.py:6-8`). `unit_spec` returns (dimension, exact `Fraction` factor) (`:23-38`). `rational` parses decimal or `p/q` text exactly (`:41-47`). Numbers are capped at 2048 bits (`bounded`, `:50-52`). `number_record` gives an exact decimal only when the denominator is 2^a·5^b, otherwise 28 digits (`:55-64`).
- **`math_model`.** A typed intermediate form with at most 16 variables and 128 nodes (`:32`). Add, subtract and compare need equal dimensions (`:60`). Division and negative powers record a "denominator non-zero" condition (`:65`, `:73`).
  - Variables may carry `lower` and `upper`, but these are domain bounds the value must sit inside (`:34`, `:40-45`, `:102`), not error bars.
  - Comparisons are boolean nodes, and `constraint=True` makes one a constraint (`:150-181`).
  - `affine()` gives the exact linear form c + Σ kᵢxᵢ, and refuses products of two variables (`:184-218`).
  - `sweep()` reports the exact boundary of a linear comparison in one free variable, root = −c/k (`:246-256`).
  - A Z3/SymPy backend runs as a bounded subprocess (`math_backend.py:24-40`).
- **staC quantities.** `UNITS` are exact `Decimal` (`stac/quantities.py:19-42`); `as_base` and `compare` are exact (`:67-91`).
  - `Requirement` has `upper_limit`, `conditions` and `grade` (`:95-101`); `Observation` has `value`, `source_revision` and `evidence_class` (`:105-112`).
  - `assess_upper_bound` compares single values (`:151`). It refuses unless the parameter, grade and conditions strings are **equal** (`:138-140`).
- **Page units** (`quantities.py:9-14`, `:36`). Resistance, temperature, mass and similar are local dimensions that the exact calculator cannot carry. Ranges like "3-5" are left alone (`:20`).
- **Worst-case analysis already in the code** (hardware proof only): `proof_checks.power` takes a relative resistor tolerance t, bounds a ratio by (1−t)/(1+t) … (1+t)/(1−t), and passes only if every margin is positive (`proof_checks.py:14-35`). This is interval arithmetic done by hand.
- **Other "tolerances" are not measurement error.** `math_office.py:57-59` and `joined_work.py:148-151` check a float result against the exact one to 1e-10 absolute or 1e-12 relative.

## 3. Peak overlap and the one memory rule

- **`schedule_math.evaluate(problem, capacity, allocations)`** (`schedule_math.py:16-63`) is a pure function over `problem['variables']`.
  - Lifetimes are `{start, stop, unit}` JSON in half-open [start, stop) (`:31-43`).
  - The sweep processes **releases before allocations** at each event time (`:52-55`), takes the peak, and records each segment with whether it fits (`:58-59`). The result is FEASIBLE or INFEASIBLE (`:60-63`), or UNKNOWN with the missing lifetimes (`:49`).
  - Its assumptions say no overhead, fragmentation or indivisibility is modelled (`:47-48`).
  - `math.schedule.get` turns a receipt STALE when the problem or the code changes (`:77-84`). `math.concurrent` is the case where everything overlaps (`:67-74`).
- **The one memory rule** is `budget_room(available, reserve, future, credit) = max(0, available − reserve − future) + max(0, credit)` (`resource_control.py:66-71`).
  - The reserve defaults to 2048 MiB, capped at a quarter of RAM (`:18`, `:51-56`).
  - `credit` is what a sequential model handover frees (`:192`).
- **Model size.** The owner's model file is 20,542,732,576 bytes (`tools/campaign_lib/gguf_fixture.py:27`). The campaign requires 24 GiB available (`tools/campaign_lib/runner.py:435-437`).

## 4. The Field's records: what each thing is

| Kind | Record and read | Revision | Where it comes from | How the Field decides its state |
|---|---|---|---|---|
| source | intake item (`field_source.py:130-145`) | sha256 | Admission ACCEPTED, HELD or waiting (`:140-142`) | current / **held** / waiting |
| sheet | office record (`office.get`) | sha256 text; "version" shown (`:192`) | `origin.pdf` (page, rectangle, layer, decision) and `reviewed_rows` with `original_cells`, `source_words`, `ocr_uncertain` (`datasheet_work.py:111-112`, `:159-160`) | `source_word` of CURRENT_PDF_SOURCE or PDF_SOURCE_REVIEW_REQUIRED (`field_source.py:53-59`, `datasheet_work.py:126-131`) |
| calculation | document with a `derivation` (`datasheet_work.py:249-257`) | whole number | Inputs carry `basis` REVIEWED_PDF_ROW or WORKING_SHEET_EDIT (`:221-226`); a recheck makes a new page with `replaces` (`:253-257`) | `report_state`: CURRENT, RECHECK_SHEET_CHANGED, PDF_SOURCE_REVIEW_REQUIRED, SHEET_UNAVAILABLE (`:166-178`) |
| finding / question | investigation claim | none; evidence rows | `inv_evidence` (direction, source or step, independence, stale); checks (program, oracle, expectation) (`investigations.py:76-93`) | Evidence state is computed, never typed (`:222-228`). Map: NEEDS_REVIEW or a stale path → recheck; CONFLICT → **held**; REFUTED → refuted; SUPPORTED → current; else open (`field_source.py:259-267`). Words quoting a reworked result → recheck (`:425-430`, `_moved` `:451-461`) |
| total ("condition" kind, tag TOTAL) | `ledger.condition/1` card | document revision | Block id, character span and quoted words (`conditions.py:5-14`) | CURRENT, STALE, BROKEN (`:47`, `assess` `:102-113`) |
| problem | `arc.problem/1` | whole number plus `context_digest` (`problem_service.py:50-62`) | Variables of type quantity, **interval** (a lifetime), boolean or text, with state KNOWN or UNKNOWN (`:16-22`) | Freshness CURRENT or REVIEW_REQUIRED (`:176-192`) |

**Name clashes the planner must avoid:**
- In the Field, **"held" means a finding whose evidence conflicts**, or a source held at review (`field_model.py:26-27`, `field_source.py:141`, `:264`). It also counts as needing the owner's attention.
- **"BROKEN"** on a total means its result paragraph is gone (`conditions.py:105`), not that a test failed.
- Kind `condition` and schema `ledger.condition/1` are already taken by totals (`conditions.py:45-46`, `field_model.py:15`, `:22`).
- Problem type `interval` already means a time lifetime (`schedule_math.py:31-43`, `adaptive_contract.py:98`, `:106`).

**`field_doubt`'s traps** (no model is asked):
- Calculation: agrees with its sheet (`:150-153`); inputs as the page says (`:156-162`); conditions missing or different (`:164-171`); what moves the result by 1 % (`:172-187`).
- Sheet: its source (`:196-202`); counted twice, exact `Decimal`, the owner's specification situation 07, not After Hours 07 (`:240-286`); cells as reviewed, columns A–D only (`:212-228`); OCR uncertain, no unit, no condition (`:221-226`); another sheet differs (`:294-319`).
- Finding: how much independent support (`:371-377`); its checks (`:379-397`); a check that can't fail (`weak_check`, `:466-483`); its words after a value moved (`:399-401`); a check on a replaced page (`:402-405`); numbers on the desk, the same digits under another prefix, or made from two values (`:413-435`).
- Also pages (`:439-463`), totals (`:499-504`) and sources (`:507-512`).

## 5. After Hours 07, read from the restored records

| Value | Where it is | Condition text beside it |
|---|---|---|
| 12 V rail | Bench `owner:db5f…` B2, revision `69dada6f…` | "During both observations" (D2) |
| 280 mA settled | Bench B3 | "After settling" |
| 650 mA startup | Bench B4 | "During startup pulse" |
| **110 ms** startup duration | Bench B5 | "Measured pulse" |
| 6 W continuous | Rev A `owner:5a43…` B2 and Rev B `owner:4f35…` B2 | "Continuous" |
| 8 W pulse ceiling | Rev A B3 and Rev B B3 | Rev A D3 **"Up to 120 ms"**, Rev B D3 **"Up to 80 ms"** |
| **120 ms** and **80 ms** pulse duration | Rev A B4 and Rev B B4 | "At up to 8 W" |
| Settled power 3.36 W (`84/25`) | Calculation `0e39…`, `voltage * settled_current` | |
| Startup power 7.8 W (`39/5`) | Calculation `500c…`, `voltage * startup_current` | |

**Where "Up to 80 ms" lives:**
- As words in Rev B D3, repeated in `reviewed_rows[1].conditions`.
- As the number 80 ms in Rev B B4.
- As a finding: "The reviewed sheet keeps the 80 ms condition." Its check is `@office:owner:4f35…`, CONTAINS "Up to 80 ms", PASSED. The doubt calls this check one that can't fail, because the whole record also keeps the reviewed words. It proposes narrowing the check to `cells.D3.value` (`field_doubt.py:471-482`).

The limit is a pair: the 8 W ceiling holds for at most 80 ms, and the 80 ms holds at up to 8 W.

**What no record holds:**
- "30 ms past the Rev B limit" (110 − 80). The doubt says "30 ms is on no sheet… no calculation records it" (`field_doubt.py:323-336`).
- A calculation can't record it either: `office.datasheet.report` takes inputs from one sheet's Value column (`datasheet_work.py:189-199`).
- "Rev B allows 6 W" compares in words, so the ripple does not work it (`field_ripple.py:30-31`).
- Of the four findings, only the 80 ms one has a check (`investigations.py:269-270`).

**Where the investigation stands:** WAITING on the question "What stretched the startup pulse?" (`investigations.py:267-268`). The conclusion page "07 Case conclusion · HOLD" is a plain page, so it has no state.

**`assess_upper_bound` could not be used here as written:** "Startup duration" against "Pulse duration", and "Measured pulse" against "At up to 8 W", would fail on PARAMETER_MISMATCH and OPERATING_CONDITIONS_MISMATCH (`stac/quantities.py:138-140`).

## 6. Where an error bound could be recorded today: nowhere

- **Office cell:** the key set is closed at 7 keys (`sdk/cli/arc1cli/office_tables.py:43-44`, `:60`).
- **Reviewed row and sheet columns:** the row schema is closed to parameter, value, unit, conditions (`datasheet_work.py:14-15`, `:20`). The columns are Parameter, Value, Unit, Conditions, PDF page, Extraction (`:10`).
  - Writing "±5 ms" in Conditions would make `field_doubt` see two different conditions (`field_doubt.py:164-171`).
  - An extra column G would not be compared with the reviewed rows (`:215`).
- **`math_model` variables:** `lower`/`upper` are domain bounds, and a variable with no value evaluates to UNKNOWN (`math_model.py:34`, `:44`, `:98`).
- **Problem variables:** `basis` is free text, and `interval` is a lifetime (`problem_service.py:16-22`).
- **staC `Observation`:** a single value with no error field (`stac/quantities.py:105-112`).
- **The only tolerance in the code** is the hardware proof fixture's `resistor_tolerance` (`proof_checks.py:20`).

## 7. Parts to build on

- **Evidence lattice:** `EvidenceSupport` with UNKNOWN, SUPPORTED, REFUTED, CONFLICT. `truth_and`: false wins. `ScopedJudgement.admissible` means CURRENT, reviewed and cited (`stac/evidence.py:26-49`, `:78-90`, `:105-147`).
- **Obligations:** SATISFIED or OPEN, each with a source witness (`stac/obligations.py:36-41`).
- **`reason_graph.compute`:** a finite acyclic rule graph with a state per node. Budgets: 64 nodes, 128 rules, at most 8 premises per rule, 4096 combinations, 256 paths. Cycles are refused (`reason_graph.py:14-58`, `:61-99`). This can serve as the method decomposition, in the spirit of hierarchical task networks.
- **`checked_methods`:** declared preconditions, typed inputs, expected checks, failure cases and ordered steps (`checked_methods.py:79-90`). Its mapping checks the preconditions again (`:97-110`).
- **`investigations` already keys repeats and propagates staleness:**
  - `input_key = digest([program, input digests, check])` (`:163`). A repeat is marked `duplicate_of`, but **it is still dispatched** (`:164-167`, `:182`) and adds no evidence (`:184`).
  - `refresh` marks evidence and steps stale and claims NEEDS_REVIEW (`:327-352`).
  - `next_action` is an ordered policy (`:259-272`). `continue_` has a budget (`:294-324`).
- **`desk_acts.key_path`:** a breadth-first search over the Field's own moves (`desk_acts.py:399-415`).
- **`desk_scene.matches` and `lookup`:** dotted-path predicates on `read.desk` (equal, contains, in, decimal, gte, lte, between, not) (`desk_scene.py:35-69`). `read.desk` has parts where, field, menu, files, line, talk, look, motion, last (`desk_doers.py:580-649`).
- **Her hand:**
  - `desk_hers`: a read never asks; navigation is offered at Ask first and done at Do and show or Free hand; a change goes to `stacy_hand.hers` on its Kernel operation (`desk_acts.py:299-339`).
  - `hers`, `HERS_SHOW`, `HERS_FREE` and what always asks (`stacy_hand.py:39-57`, `:150-158`).
  - The `door='her'` refusal (`desk_doers.py:1425`).

---

# Proposals

## (a) The condition record

Use **schema `ledger.goal-condition/1`, kind `goal`**, stored in Project Desk records like the totals cards (`conditions.py:118-180`), with history.

```
{statement:   "The startup pulse stays within the Rev B pulse duration.",   # her words or the owner's
 predicate:   {form: 'relation', expression: 'pulse <= limit',               # math_model.compile_expression(constraint=True)
               bind: {pulse: {address:'office:owner:db5f…', cell:'B5', revision:'69dada6f…', unit:'ms'},
                      limit: {address:'office:owner:4f35…', cell:'B4', revision:'334cce26…', unit:'ms'}},
               bounds: {pulse: null, limit: null}}                           # see (d); null = none recorded
              | {form:'text',  line:'@office:… | pick document.sheets | select cells.D3.value', expect:'CONTAINS', value:'Up to 80 ms'}
              | {form:'state', read:'documents.get', path:'source_state.state', equals:'CURRENT'}
              | {form:'desk',  path:'field.selected', want:{'contains':'Rev B'}},   # desk_scene.matches
 evidence:    [{record, revision, read, digest, step}],                      # one per bound input; step = investigation step id
 state:       'open'|'held'|'broken'|'unknown',  stale: bool,
 slack:       {lo, hi, unit, rational:{lo, hi}},
 depends:     ['office:…#B5@69dada6f…', 'office:…#B4@334cce26…', 'goal:<id>'],
 agreed:      bool, origin: 'HER'|'OWNER'}
```

**How the state is decided** (slack S = limit − value, normalised so that "holds" means S ≥ 0):
- **open**: some bound input has no evidence yet.
- **held**: lo(S) ≥ 0, with every evidence revision current.
- **broken**: hi(S) < 0, with every evidence revision current.
- **unknown**: S straddles 0; or the evidence conflicts (two readings whose intervals don't overlap); or a domain error such as zero in a denominator (`math_model.py:110`).
- **stale**: any evidence revision differs from the record's current revision. The old state is kept, as `investigations.refresh` does.

"Held" is the owner's word, but the Field already draws a conflicting finding as "held" (`field_source.py:264`). On screen the five states should read **holds / does not hold / open / cannot tell / recheck**, the doubt's own words (`field_doubt.py:27`).

**After Hours 07 examples:**

| Id | Predicate | Values | State |
|---|---|---|---|
| C1B | B5@bench ≤ B4@RevB | 80 − 110 = −30 ms | broken |
| C1A | B5@bench ≤ B4@RevA | 120 − 110 = 10 ms | held |
| C2 | output(500c…) ≤ B3@RevB | 8 − 7.8 = 0.2 W | held as recorded; robustness unknown, see (d) |
| C3 | output(0e39…) ≤ B2@RevB | 6 − 3.36 = 2.64 W | held |
| C4 | text predicate, Rev B D3 contains "Up to 80 ms" | the narrowed check | held |

The pulse is allowed by Rev B only if C1B and C2 both hold.

Which limit sheet applies ("Rev B applies to this run" on the conclusion page) is a goal she or the owner names and records in `bind`. It is not deduced, and string matching of conditions would refuse it (`stac/quantities.py:140`).

## (b) Operators: what each operation needs, what it affects, how to check it

Scopes below are read from `CAPABILITIES`, which I printed from a copy.

| Operation (scope) | Class | Needs | Affects | Checked or landed by |
|---|---|---|---|---|
| `office.get`, `documents.get`, `investigation.sheet`, `.path`, `field.read`, `conditions.get`, `ledger.address.read` (read) | **read: establishes evidence** | the record exists | adds `known(cell@rev)`, `state(record)` | the read itself, with a digest (`investigations.py:141-153`) |
| `read.desk` (an act, not a Kernel operation) | read, desk | none | adds the desk atoms where, selected, menu, line, pending | `desk_scene.matches` |
| `field.whatif`, `field.ripple`, `field.doubt` (read) | **simulate**: no effect on the world | the record is readable | adds hypothetical values and traps; the doubt can set **unknown** (a weak check, no condition recorded) | itself |
| `field.set` (execute; Do and show) | **change** | revision = expected; the cell holds a number; the new value differs (`field_service.py:174-185`) | cell := v; new revision; every calculation of the sheet goes to RECHECK (`datasheet_work.py:174-175`); watchers go stale on refresh | **landed** when `office.get` shows the cell = v and the revision ≠ the expected one. Undo exists (`stacy_hand.py:43`) |
| `office.datasheet.recheck` (approve; Free hand only) | change | the page revision is current; the source PDF decision still stands (`datasheet_work.py:188`); same parameters (`:206`) | a new page with `replaces`; output := f(cells) exactly; findings quoting the old result → recheck (`field_source.py:425-430`) | landed when some page has `derivation.replaces` = the old id (`field_source.py:217-218`) |
| `investigation.claim`, `.check`, `.evidence` (execute) | change | the investigation is owned | a claim or check exists | `investigation.sheet` |
| `investigation.continue` (execute; Do and show) | **check** | a due check (`investigations.py:265-266`) | outcome PASSED or CHECK_FAILED; SUPPORTS or OPPOSES evidence unless a repeat (`:184-188`) | the step row |
| `investigation.refresh`, `conditions.recheck` (execute; Do and show) | check | none | stale marks, NEEDS_REVIEW; the total re-added | the sheet or card |
| `math.calculate`, `math.schedule` (execute) | check (a model consequence) | the problem revision and digest are bound (`problem_service.py:60-62`) | an exact receipt, `physical_qualification: False` | `math.schedule.get` CURRENT or STALE |
| `investigation.review` (approve; `*.review` always asks) | owner's decision | | | |
| `brain.model.use` (approve) | swap | memory admissible, see (f) | the resident model | |
| Desk acts that navigate | navigation | `where = field` where refusal NOT_HERE applies; no unsent line or pending approval (`desk_acts.py:185-203`) | where, selected, menu | the act's envelope (`desk_doers.py:6`) |

**Rules that follow from the table:**
- A read never deletes a fact, so reads commute and repeat harmlessly. A plan's reads are a set, not a sequence.
- Only changes and navigation need ordering.
- An operator whose deletes include an agreed goal literal can't come last in a plan.

## (c) Regression (weakest precondition) over a finite abstraction

**Abstraction.** Atoms are: each goal's state; `current(record@rev)`; `known(cell@rev)`; and the desk atoms where, selected, menu and pending. Each goal fans out to at most 8 sub-goals, like a `reason_graph` rule (`reason_graph.py:42`), and there are at most 64 atoms (`:19`).

**Logical regression (STRIPS style).** For operator o and goal set G:

  Reg(G, o) = (G \ add(o)) ∪ pre(o), defined only if add(o) ∩ G ≠ ∅ and del(o) ∩ G = ∅.

**Numeric weakest precondition.** For an assignment, wp(x := e, Q) = Q[e/x], and wp(a₁; a₂, G) = wp(a₁, wp(a₂, G)).

Worked on After Hours 07, with G = "C3 holds and settled power is current":

  wp(field.set(B3 := v); datasheet.recheck, G)
  = 12 V · v ≤ 6 W ∧ pre(recheck) ∧ pre(set)
  ⇒ **v ≤ 500 mA**.

With a rail of 12 V ± 1 %, this becomes v ≤ 6/12.12 A = **50/101 A ≈ 495.04 mA**. Round down when showing it, because it is an upper bound.

For the pulse ceiling, I_start ≤ 8/12 A = 2/3 A.

The boundary comes from `math_model.affine` and `sweep` (`math_model.py:184-218`, `:246-256`). Products of two unknown inputs fall outside the linear form and go to interval bisection, see (d).

**Bound on the search.**
- Breadth-first regression to horizon H, using only relevant operators (those with add ∩ G ≠ ∅) and remembering goal sets already seen.
- Node count N(H) ≤ Σ_{d≤H} b^d = (b^{H+1} − 1)/(b − 1), with a hard cap of 4096, the same as `reason_graph`'s combination budget (`reason_graph.py:77`).
- After Hours 07: b ≤ 10 (three `office.get`, two `documents.get`, `investigation.sheet`, `field.doubt`, `continue`, `recheck`, `set`) and H = 3 gives at most 1,111 regressions, each a set operation on 64 or fewer atoms.
- Because reads commute, only changes and navigation take sequence slots: here b_seq ≤ 4, so at most 85.
- The desk layer is solved by the existing breadth-first search: states are at most 8 places × 60 sheets (`field_source.py:43`) × open menu, with 40 acts. This generalises `key_path` (`desk_acts.py:399-415`).

## (d) Interval arithmetic with units and recorded bounds

**Where bounds come from.** A new desk record `ledger.bound/1`:

  {address, cell, revision, kind: abs | rel | range, e | r | [lo, hi], unit, basis, source address}

It is set or approved by the owner only. A bound she invents is the worst failure this design can have.

| Kind | Interval |
|---|---|
| abs, x ± e | [x − e, x + e] |
| rel, x ± r | [x(1 − r), x(1 + r)] for x ≥ 0 |
| range | [lo, hi] |

Endpoints are `Fraction`s in base units through `unit_spec` and `rational`, with the dimension carried along. **Use these, not the float `measure()`.**

**Operations.** Exact, because the rationals are closed under all four.

| Operation | Result |
|---|---|
| [a,b] + [c,d] | [a+c, b+d] |
| [a,b] − [c,d] | [a−d, b−c] |
| [a,b] · [c,d] | [min(ac, ad, bc, bd), max(…)], dimensions add |
| [a,b] ÷ [c,d] | [a,b] · [1/d, 1/c] if 0 ∉ [c,d]; otherwise DOMAIN_ERROR, state unknown |
| negation | [−b, −a] |
| integer power xⁿ | endpoints; for even n with 0 inside, [0, max] |

**Properties that make the decisions sound:**
- **Inclusion monotonicity**: X ⊆ X′ ∧ Y ⊆ Y′ ⇒ X∘Y ⊆ X′∘Y′.
- **The natural extension encloses the range**: f(X) ⊆ F(X).
- When each variable occurs once in the expression, the enclosure is exact. That is the case for L − T and V·I. For linear predicates, take the exact range from `affine()`: c + Σ min/max(kᵢ·loᵢ, kᵢ·hiᵢ).
- **Outward rounding** happens only at the edges: when shown (lo with `ROUND_FLOOR`, hi with `ROUND_CEILING`, the rational kept beside it, as `number_record` keeps `rational`), and when a bound would pass the 2048-bit cap (`math_units.py:50-52`). Widening outward keeps the enclosure valid.

**Decision rule.** For a slack S = limit − value: **holds** if lo(S) ≥ 0, **broken** if hi(S) < 0, otherwise **cannot tell**. Equality is decidable because there are no floats.

**Value of information.**
- If S is already on one side, every narrower reading stays inside S, so VOI = 0. This is the owner's "zero value" statement. A new reading is intersected with the old one; an empty intersection means "the two readings cannot both be right", state unknown.
- If S straddles 0, the **decisive share** of input i is the measure of x ∈ Xᵢ for which S(Xᵢ := x, others as intervals) lies on one side, divided by |Xᵢ|. It can be found exactly by solving the boundary, or soundly by bisecting into 64 pieces.
- Under a uniform prior this share is the probability that observing i decides.
- Choose o* = argmax over o of Σ_c w_c·φ_c(o) / cost(o). Here w_c = 0 when c's parent decision is already robust: in Belnap logic a false conjunct decides the conjunction (`stac/evidence.py:78-82`).

**Worked on After Hours 07** (exact output of my prototype; the tolerances are hypothetical, since none is recorded):

| Case | Assumed bound | Slack | Verdict | What a better reading is worth |
|---|---|---|---|---|
| C1B, pulse vs Rev B | T = 110 ± 5 ms | 80 − [105, 115] = **[−35, −25] ms** | **broken robustly** | Excess is [25, 35] ms. A ±1 ms reading gives [−31, −29], inside the old slack. Break-even e < 30 ms. VOI = 0 |
| C1A, pulse vs Rev A | T = 110 ± 5 ms | [5, 15] ms | holds | robust while e ≤ 10 ms |
| C2, startup power vs 8 W | V ± 1 %, I ± 2 % | P = [7.56756, 8.03556] W, so S = **[−0.03556, 0.43244] W** | **cannot tell** | Decisive share for I = **6989/7878 ≈ 0.887**; for V = **3089/3978 ≈ 0.777** (bisection lower bounds 0.875 and 0.766). Measure current first. Break-even: (1+r_V)(1+r_I) ≤ 40/39; with r_V = r_I, r ≤ √(40/39) − 1 ≈ 1.27 % |
| C3, settled power vs 6 W | same | [2.538528, 2.740128] W | holds | break-even (1+r)² ≤ 25/14, r ≤ 33.6 % |
| HOLD decision, C1B ∧ C2 | | | **broken robustly**, because C1B is | VOI of V and I for HOLD = 0. Only the page's separate sentence "clears the wattage ceiling" has VOI > 0 |

Without any recorded bound, she should report the **break-even** (for C2: "good to 1.27 % each"), not invent a tolerance.

## (e) Receding horizon, with repair along the dependency graph

**The loop.** Each turn: read, then evaluate the goals, plan to H = 3 by (c), and pick the first action by VOI/cost with reads preferred. Then ask `desk_hers` / `hers`: if the action is not hers to do, propose it and stop. Otherwise do **one** action, read back, record the step, and repeat.

**Repeated read.** Before dispatching, look the step up by `input_key` (`investigations.py:163`). If an earlier step has the same key, is not stale and is PASSED or DONE, **don't dispatch**. Hand back that step's summary and digest, together with the goals still open. Today the lookup exists but the repeat is still dispatched (`:164-167`).

**Write that times out.** Probe whether it landed (table in (b)) before any retry:
- landed: adopt the new revision;
- not landed and the revision is unchanged: retrying is safe, because the save is compare-and-set (`field_service.py:174-175`);
- otherwise: plan again.

**Repair.** The dependency graph D is the Field's links (`field_source.py:199`, `:233-236`, `:277-286`) plus each goal's `depends`. When node v changes, everything reachable from v, desc(v), is evaluated again in topological order, as `reason_graph.validate` orders it (`reason_graph.py:50-57`). The cost is O(|desc(v)| + edges).
- The ripple's split into calculations that read the changed cell and those that only read the sheet (`field_ripple.py:160-166`) separates "must be worked again" from "confirm; the result is predictable".
- A sheet with a new revision but the same values for a goal's bound cells needs only a read to rebind its evidence.

**Progress and stall.** Track Φ = Σ_c (2·[open] + [cannot tell] + [stale]), plus the total width of the slack intervals.
- Each step must lower Φ, or be a read that narrows an interval.
- Two steps that fail to do either count as a stall.
- A stall escalates: more thinking first, then self-consistency (k = 3 predicate sets, compared exactly once normalised), then a model swap proposal checked by (f).
- **Finish** is allowed only when every agreed goal is held (or decided, for goals of the form "decide whether") with current evidence. Otherwise finishing is refused with the list of open goals.
- The step budget stays at `DEFAULT_BUDGET` (40 steps, 600 s; `agent_loop.py:122`).
- In After Hours 07, the question "What stretched the startup pulse?" has no operator on this computer that adds it. She should say so and ask: the page's own next question is a repeat capture at the load.

## (f) Memory admissibility of a plan's jobs

The plan's jobs fit if

  M_resident + max_t Σ_{i: sᵢ ≤ t < eᵢ} mᵢ ≤ M_budget, with M_budget = budget_room(available, reserve, future, credit).

Run `schedule_math.evaluate` in process on a problem dict built in memory; it needs no record (`schedule_math.py:16-63`). Either set capacity = M_budget − M_resident, or include the resident model as an allocation so that a swap shows up as release-before-allocate at the boundary (`:52-55`), which is what `credit` means (`resource_control.py:192`).

There is no overhead term, so add the KV cache and compute buffers as explicit allocations (`:47-48`).

**Example** (illustrative budget of 32 GB; the 35B weights are 20.542732576 GB):

| Plan | Peak | Where | Verdict |
|---|---|---|---|
| 35B for [0, 600) + KV 3 GB [0, 300) + dense 16 GB [300, 600) + read 1 GB [250, 320) | **37.542732576 GB** | [300, 320) | **INFEASIBLE** |
| Same, but the 35B leaves at 300 s | **24.542732576 GB** | | **FEASIBLE** |

A `brain.model.use` proposal under her hand carries the feasible schedule.

---

**Suggested files** (pure Python, no Qt, no new dependencies):
- `workbench/bounds.py`: interval evaluation over the `math_model` node form, mirroring `values()` (`math_model.py:90-124`), plus the decisive share.
- `workbench/goals.py`: the record, its state, evidence binding and the store.
- `workbench/planner.py`: the operator table, regression, VOI, the loop and the admissibility check.

**Scratch files:**
- After Hours 07 reads: `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/hand_read/maths/ah07.json`
- Interval and schedule prototype: `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/hand_read/maths/scripts/proto.py`
- Doubt and ripple reads: `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/hand_read/maths/scripts/read_more.py`