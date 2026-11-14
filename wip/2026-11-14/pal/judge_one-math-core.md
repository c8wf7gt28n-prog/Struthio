# Judgment on PAL draft 0.2 §6 and slice S2

I did not have the text of draft 0.2 itself, so I judged it through the two verifier reports. I checked the code I rely on at HEAD bbf033b, read-only, and recomputed every number below with `Fraction`.

## PART 1: Verdict

### Right; we keep these
- **Every number is correct.** Graphite's exact engine gives the same value and unit for each one: 84/25 W, 66/25 W, 1/2 A, 1503/250 W, 30 ms, 18/5 W, 12/5 W, the box [1593/500, 1769/500] W, 30000/61 mA, 29951/5000 W, 7503/1250 W and 12 mW.
- **The four steps** (evaluate, solve for, bound, check) are a sound way to split the work.
- **The affine rule is right:** a boundary at −b/a, its direction set by the sign of a, and the a = 0 case giving either the whole domain or a contradiction.
- **Three further rules are right:** intersect the answer with the domain, keep each endpoint closed or open, and respect integer steps.
- **The cautions are right:** subtracting x from itself as two independent ranges widens the answer, and a denominator range that contains 0 needs an obligation.
- **Solvers are framed correctly.** They stay optional. A solver's "infeasible" is not certified (math_backend.py:43,72,114). Only an answer that comes with a witness is rechecked exactly.

### Wrong; corrections
1. **"The 6 W Rev B settled limit".** The row is called "Continuous limit", and Rev A and Rev B both say 6 W (tests_integrated/test_faces_find_light.py:348,350). That is exactly how a limit gets wrongly deduced. S2's rule stands: which limit applies is bound by the owner or by a goal, never deduced.
2. **Clock Lab: "4 MiB holds when the two 6 MiB allocations overlap".** The model's assumption is "All three allocations are concurrent" (workbench/math_checks.py:12). The declared workspace is 5 MiB (examples/clock_lab/inputs/problem.json:39), which gives 17 MiB > 16 MiB, INFEASIBLE.
   - Correct wording: "with all three live at once, the workspace may be at most 4 MiB; the declared 5 MiB does not fit."
   - When lifetimes are known, the right tool is `math.schedule`, not the sum.
3. **"The engine can recheck a candidate against the original model".** Only partly true. `witness_check` rejects any value that overrides a declared one (math_model.py:225). "Solve for" must first remove the solved variable's declared value, then recheck on that copy.
4. **"The two optional-backend tests were skipped because Z3 was absent".** They skip if SymPy *or* Z3 is missing. The scratch venv has both, and all 8 tests run there.

### Imprecise; corrections
5. **Integer steps.**
   - With ≤, the upper end on a lattice with offset o and step s is o + s·⌊(r−o)/s⌋.
   - With a strict relation and r on the lattice, it is r − s: 12 V·I < 6 W in whole mA gives **499**.
   - A strict relation at a closed domain edge can be empty (12x < 0 with x ≥ 0).
6. **"Corners suffice".** This holds only when the function is monotone in each variable, or each variable is used once with no even power, and the function is continuous on the box. It never holds across a pole.
7. **"An enclosure touching both sides decides nothing".** These are two separate questions:
   - **For every value in the ranges:** an exact, attained enclosure can refute this. The failing corner is a real counterexample.
   - **For the one real, unknown value:** the answer stays "cannot tell". Example C2: the corner (12.12 V, 663 mA) gives 8.03556 W > 8 W, yet C2 is still "cannot tell", and S2's value-of-information ranking still applies.
8. **The typed line "12 V × I ≤ 6 W" cannot be written today.**
   - Bare numbers compile as dimensionless, so 6 W must be a declared variable.
   - Inline quantity literals such as "12 V" are later work.
9. **Ranking inputs by derivative.** W/V and W/mA cannot be compared. Rank by each input's effect over its stated range (V: 14/125 W, I: 6/25 W) or by decisive share. S2 already does the latter.
10. **"Evaluate is already there".** Mostly true, but two errors escape as a bare `ValueError` instead of a state:
    - INCOMPATIBLE_OUTPUT_UNIT (math_units.py:70, called from math_model.py:136);
    - the 2048-bit size limit (`bounded` at math_model.py:122, outside the `MathError` catch at :129).
11. **The staC preview ignores whether sources changed.**
    - `math.preview` reads the problem with `problems.load` (math_service.py:215), with no freshness check.
    - The draft's own "stale limit" acceptance vector therefore needs a fix.
12. **"Read-only".** The new steps write no math records, but the Kernel still writes audit and activity rows. Say exactly that.
13. **field_ripple is not exact arithmetic.**
    - `_same` uses a relative float tolerance of 1e-9 (field_doubt.py:64-67).
    - `_plain` rounds without saying so (field_doubt.py:70-72).
    - A math receipt never takes numbers from the ripple. The exact what-if path is `datasheet_work.what_if` → `math_model` (datasheet_work.py:291-307).
14. **Offline wheels: cannot be checked, and the premise fails for the ThinkPad anyway.**
    - `--math` is passed only for `--profile suite` (INSTALL_LS.py:331; INSTALL_LEDGER.sh:41).
    - The documented ThinkPad command uses the default profile with `--calc` (docs/THINKPAD_FIRST_INSTALL.md:29-32).
    - So SymPy and Z3 are not on the owner's machine by default.
15. **The step name "bound" collides** with existing meanings in Graphite (see the names table in Part 2).

### What 0.2 adds beyond the S2 plan
- **A line face:** the owner, or a line built with Then, can run the maths as typed steps.
- **"Solve for" specified precisely.** S2 planned to derive boundaries from `affine` and `sweep`. Sweep's boundary does none of the following:
  - says upper or lower;
  - intersects with the domain;
  - rounds to integer steps;
  - says why it gave no boundary (it drops a zero coefficient silently at math_model.py:190 and :252, and swallows errors at :257).

  So the boundary must come from `affine` alone.
- **Check over a range,** with a counterexample record and an exactness status.
- **Receipt fields:** method or guarantee class, exactness, and witness or derivation.
- **Acceptance vectors:** 30000/61 mA, the 491/492 mA pair, 499 mA, zero coefficient, domain clipping, unavailable solver, stale source.

### What S2 has that 0.2 lacks, and the merge keeps
- Tolerances set by the owner only.
- Which limit applies is never deduced.
- Decisive share, break-even, and value-of-information ranking.
- Belnap combination of goals.
- Rebinding when a value is unchanged, and repair in topological order.
- A measured cell is never edited to make its own goal true.

### Corrections to S2 itself
- **The decision rule covers ≤ only.** It needs strict, equal and not-equal forms (rule 3 in Part 2).
- **Do not write a new Belnap.** It already exists: `EvidenceSupport`, `truth_and` and `knowledge_join` (workbench/stac/evidence.py:11-15, 78-101).
- **The After Hours 07 tests cannot use the owner's backup.** It is not shipped (tools/campaign_lib/fixture.py:10-11). They need an in-repo fixture.
- **The "admissibility helper" belongs in the escalation slice,** next to `schedule_math`.
- **Names:** `bounds.py`, `ledger.bound/1` and `bounds.*` collide with existing meanings (Part 2).

## PART 2: One math core

### Modules

| Layer | File | Contents |
|---|---|---|
| exact base, **unchanged** | `math_units.py`, `math_model.py` | units, `rational`, IR, `evaluate`, `affine`, `witness_check` |
| core, NEW, pure (no Qt, Kernel, model, SymPy or Z3) | `workbench/math_ranges.py` | `Enclosure`, `outward`, `enclose`, `decide`, `allowed`, `check_box`, `corner_witness`. The goal slice later adds `decisive_share`, `break_even`, `value_of_information`. |
| answer, NEW | `workbench/math_answers.py` | `answer(stage, bindings, …)` returns `ledger.math-answer/1`; templated words; implementation hashes; `bindings_from_problem` (reuses `math_service.model_for` and freshness from `problems.get`, plus tolerances); Kernel op **`math.answer`** (read). The goal slice adds `bindings_from_cells`. |
| owner's ranges, NEW | `workbench/tolerances.py` | `ledger.tolerance/1`; `tolerances.get` and `tolerances.list` (read); `tolerances.set` (approve) |

**The two faces call the same `math_answers.answer`:**
- **Line face:** a `math` line (stac_bridge.py:76-87) compiles to `math.answer`. The owner types it, or puts it in the writing line from Then. `stac.observe` stores it.
- **Goal face:** `goals.py` (desk form from S1; relation form in the goal slice) calls `answer` in process with bindings to sheet cells. It never composes line text.

**Frozen in the first slice:** math_model.py, math_units.py, math_backend.py, math_service.py, math_office.py, office_math_runtime.py and LedgerOffice.java.
- They are hashed by `components()` (math_service.py:41-42).
- Touching any of them makes every prepared action refuse with MATH_CONTRACT_CHANGED (:74), and makes `math.get` report HISTORICAL_INPUTS_CHANGED (:223-224).
- New answers instead carry their own `implementation` hashes, as `schedule_math` does (schedule_math.py:91).

### Line grammar
Strict shlex tokens, at most 40, optional steps in this order:
```
math problem:ID | calculate "EXPR" [| unit U]                    -> math.preview (unchanged)
math problem:ID | solve "REL" for NAME [| within LO HI] [| step S] [| given NAME LO HI]x<=4 [| unit U]
math problem:ID | range "EXPR" [| given NAME LO HI]x<=4 [| unit U]
math problem:ID | check "REL" [| given NAME LO HI]x<=4
```
- LO, HI and S are in that variable's declared unit.
- Problem variables carry no domain (math_service.py:47), which is why `within` and `step` exist.
- `stac_bridge.run` attaches `freshness` (CURRENT or REVIEW_REQUIRED, from `problems.get`) to every MATH result, `calculate` included. stac_bridge is not hashed.
- **Rule:** the planner never produces `given`. Her ranges come only from tolerance records.

### Core rules (`math_ranges.py`)
1. **Enclosures** are closed and in base units. Each has a status:
   - **ATTAINED** when either:
     - the slack is affine in the variables that have a range, so the range comes exactly from the coefficients (x − x cancels); or
     - each such variable occurs once and never under an even power.
   - **SOUND_ENCLOSURE** otherwise.
   - **WIDENED** when the 2048-bit limit forced outward dyadic rounding.
2. **A denominator range containing 0** gives state DENOMINATOR_MAY_BE_ZERO and no enclosure. For a goal this reads "cannot tell".
3. **Decide on S = right − left:**

   | Relation | holds | does not hold |
   |---|---|---|
   | le | lo ≥ 0 | hi < 0 |
   | lt | lo > 0 | hi ≤ 0 |
   | ge, gt | mirrored | mirrored |
   | eq | lo = hi = 0 | 0 ∉ S |
   | ne | 0 ∉ S | lo = hi = 0 |

   Anything else is UNDECIDED.
4. **Two questions, two fields:**
   - `state` (HOLDS, FAILS or UNDECIDED) is about the one real value.
   - `for_all` (HOLDS_FOR_ALL, FAILS_FOR_SOME with a witness, FAILS_FOR_ALL, or UNDECIDED) is about every value in the ranges.
   - A witness is a corner re-evaluated by `math_model.evaluate`. It never turns `state` into FAILS.
5. **`allowed`** ("solve for x"):
   - **Per corner:** call `affine(ir, free=(x,))` at each corner of the variables with a range (at most 4 such variables, so at most 16 corners). Each gives a·x + c REL 0, and the sign of a sets the upper or lower end, with closedness from REL. a = 0 gives WHOLE_DOMAIN or EMPTY by testing c REL 0.
   - **Intersect** over the corners, up to 8 relations, the declared lower and upper, and `within`.
   - **Round** to the lattice as in Part 1, item 5.
   - **Guard:** the corner shortcut is used only when each ranged variable occurs once, is never under a division or a power, and a keeps one strict sign at every corner. Otherwise the answer is UNSUPPORTED, with its reason.
   - **Refusals:** an expression that is not affine in x, a second free variable, or a variable denominator gives UNSUPPORTED with its reason, never an empty list.
   - **Reports:** the exact end, the extreme lattice point, and whether the declared value lies inside.
   - **Witnesses** are checked on a copy with x's declared value removed.
6. **Errors come back as states and never raise:** DIMENSION_MISMATCH, DOMAIN_ERROR, UNSUPPORTED, MISSING_INPUT, INCOMPATIBLE_OUTPUT_UNIT, EXACT_ARITHMETIC_SIZE_BOUND.

### One record: `ledger.math-answer/1`
PAL's math receipt and the goal's evidence are the same object:
- The line returns it.
- `stac.observe` stores it.
- The goal embeds it. S2's `slack` is `result.slack`, and `exact` is true iff guarantee = EXACT_RANGE.

| Field | Contents |
|---|---|
| `stage` | calculate, solve, range or check |
| `asked` | the expression or relation, `for`, `within`, `step`, `unit`; template or owner words only |
| `model`, `model_digest`, `assumptions`, `obligations` | `domain_conditions` plus DENOMINATOR_MAY_BE_ZERO |
| `inputs[]` | `{name, unit, value, range?}` |
| `inputs[].origin` | PROBLEM_REVISION, DECLARED_SCENARIO, GIVEN_IN_LINE, OWNER_TOLERANCE, SHEET_CELL or FREED |
| `inputs[].source` | `{problem, revision, context_digest, variable}` or `{address, cell, revision}` |
| `inputs[].tolerance` | `{id, revision, state}`, state APPLIES, CARRIED_OVER or RECHECK; or null |
| `inputs[].role` | measured, limit, …; filled in the goal slice |
| `result` | stage-specific; numbers as `number_record` plus unit |
| `state` | see rule 4 |
| `for_all` | see rule 4 |
| `witness` | `{assignment, value}` |
| `guarantee` | EXACT_VALUE, EXACT_RANGE, SOUND_ENCLOSURE, EXACT_ALLOWED_SET or WITNESS_CHECKED; later SOLVER_WITNESS_RECHECKED or SOLVER_INFEASIBLE_NOT_CERTIFIED |
| `derivation` | at most 8 templated steps |
| `freshness` | CURRENT or REVIEW_REQUIRED |
| `words` | rounded outward, with the exact rational beside them; the screen uses the existing headings Holds / Does not hold / Cannot tell (field_page.py:441) |
| `implementation` | sha256 of math_ranges, math_answers, math_model, math_units |
| fixed fields | `model_calls: 0`, `physical_qualification: False`, `digest` |

**`ledger.tolerance/1`** (kind `tolerance`):
- **Fields:** `subject` (`{problem, variable}` now, `{address, cell}` in the goal slice), `at` `{revision, value, unit}`, `said` (one of plus_minus, percent or between), `unit`, `basis` (the owner's words), exact `lo` and `hi`, `set_by: owner`.
- **On read:** if the value is unchanged at a newer revision, the state is CARRIED_OVER. If it changed, the state is RECHECK and the tolerance is not applied. Nothing is written in the background.
- **Guards:** `tolerances.set` is approve scope *and* gets an ALWAYS_ASKS row (stacy_hand.py:46) with the words "a tolerance is yours to say: it decides what I conclude".
- **Why both:** her calls run as `operator()`, which already holds approve scope (engineering_kernel.py:299-302), so the dial rule is the real guard.

### Names

| Planned name | Already means | Use instead |
|---|---|---|
| `bounds.py`, `ledger.bound/1`, `bounds.get`/`.set`, goal field `bounds`, PAL step "bound" | `problems.BOUND` and `check_bound` (revision binding; problem_service.py:30,60; problem_checks.bound); variable lower and upper (math_model.py:40,102); `bounded()` size limit (math_units.py:50) | `math_ranges.py`, `ledger.tolerance/1`, `tolerances.*`, goal field `tolerances`, line verb `range` |
| interval | problem variable type `interval` (problem_service.py:17); `schedule_math.INTERVAL` (:6); Atlas `interval_capacity` | type `Enclosure`; the word "range" on screen |
| condition | condition cards `ledger.condition/1` and `conditions.*` (conditions.py:44-57); `domain_conditions`; the datasheet `conditions` column; field_doubt's "conditions" | "goal"; `obligations` |
| admissible | `ScopedJudgement.admissible` (stac/evidence.py:129) | `allowed` |
| verdict | `Doubt.verdict` (field_doubt.py:27) | field `state`, values HOLDS, FAILS, UNDECIDED |
| evaluate | `math.evaluate` and the line verb `calculate` (stac_bridge.py:78) | keep `calculate` |
| check (as an op) | `investigation.check`, desk `check` | the line verb `check` maps to op `math.answer` |

### What each piece reuses
- **math_units, math_model:** everything listed, unchanged.
- **math_service:** `model_for` (variables, overrides, origins, and assumptions required for scenario values; :45-64). `problems.get` supplies freshness.
- **math_backend:** not imported by the core.
  - SymPy and Z3 stay optional `math.solve` cross-checks. They are not shipped on the owner's install path, and no stage depends on them.
  - Later: Z3 for allowed regions over several variables, with "infeasible" marked not certified.
  - Fix the working-directory dependency (math_backend.py:36) the next time the hashed files are deliberately changed.
- **schedule_math:** not used by the core. The memory gate in the escalation slice calls `evaluate` in process. Clock Lab questions about overlapping lifetimes go to `math.schedule`.
- **field_ripple and field_trace:** only for *which* records lie downstream (repair order in the goal slice), never for numbers. Cell values come through datasheet_work.py:291-307's exact unit path.
- **stac/evidence.py:** the Belnap "and", "or" and knowledge join. Two readings whose ranges cannot both be right give CONFLICT, shown as "cannot tell: the two readings cannot both be right".
- **project_desk:** the record helpers for tolerances, as conditions.py uses them.
- **Registration:** follow schedule_math (engineering_kernel.py:45,176,568; engineering_cli.py:32).

### Test vectors (all exact; an AST scan finds no float in the new modules)

**Core, pure** (`tests_integrated/test_math_core.py`). The model has voltage (V), current (mA), and limit = 6 W.
1. **Calculate:** 12 V·280 mA = 84/25 W, or 3360 mW. Headroom `limit - voltage*current` = 66/25 W. `6 - voltage*current` gives DIMENSION_MISMATCH.
2. **Solve ≤** for current, ≥ 0: [0, 1/2 A] closed, so "up to 500 mA". 500 mA HOLDS; 501 mA gives 1503/250 W, FAILS, and is the witness.
3. **Solve <** with integer mA: 499 mA. With ≤: 500 mA.
4. **Robust solve,** V over [11.8, 12.2] V: upper end 30000/61 mA. In whole mA: 491 mA, which gives 29951/5000 W and HOLDS; 492 mA gives 7503/1250 W and FAILS. At 11.8 V alone the end would be 30000/59 mA, so the robust end is the 12.2 V one.
5. **Range** of V·I over 11.8–12.2 V and 270–290 mA: [1593/500, 1769/500] W, EXACT_RANGE. Slack against 6 W: [1231/500, 1407/500] W. HOLDS.
6. **Range** with 270–500 mA: slack [−1/10, 1407/500] W. `state` is UNDECIDED; `for_all` is FAILS_FOR_SOME with witness (12.2 V, 500 mA) giving 61/10 W.
7. **Limit as a lower end:** `limit - voltage*current <= h` with h = 2.4 W gives current ≥ 300 mA (299 mA FAILS, 300 mA HOLDS). `limit >= voltage*current` gives an upper end at 500 mA.
8. **Zero coefficient:** `x-x <= 0` gives WHOLE_DOMAIN; `x-x < 0` gives EMPTY; `x-x+1 <= 0` gives EMPTY (a contradiction).
9. **Domain:** V·I ≤ −1 W with current ≥ 0 gives EMPTY, with the words "needs current ≤ −250/3 mA". `12x < 0` with x ≥ 0 gives EMPTY.
10. **5 mA steps:** an end of 30000/61 mA gives 490 mA; a strict relation with root 500 mA gives 495 mA.
11. **Dependency and powers:**
    - `x - x` over [1, 3] gives [0, 0], exact.
    - `x*x` over [−1, 2] gives a SOUND_ENCLOSURE that contains [0, 4].
    - `x**2` over [−1, 2] gives exactly [0, 4].
12. **Pole:** `1/x` over [−1, 2] gives DENOMINATOR_MAY_BE_ZERO, never [−1, 1/2].
13. **Units:** V + mA, or an mA limit compared with W, gives DIMENSION_MISMATCH. A wrong output unit gives the *state* INCOMPATIBLE_OUTPUT_UNIT.
14. **Unsupported:** solving with two free variables multiplied gives UNSUPPORTED with its reason.
15. **Widening:** `outward(1/3^1300)` contains the value, uses at most 2048 bits, and is marked WIDENED.
16. **Freed witness:** on the declared power model (current = 280 mA), solving frees current, and `witness_check` at 500 mA is True on the copy.
17. **S2 numbers:**
    - C1B: 80 − [105, 115] = [−35, −25] ms, FAILS, "over by 25 to 35 ms".
    - C1A: [5, 15] ms, HOLDS.
    - C2: slack [−889/25000, 10811/25000] W, UNDECIDED, witness 200889/25000 W.
    - C3: [79329/31250, 85629/31250] W, HOLDS.
    - Weakest preconditions: 1/2 A, 50/101 A, 200/303 A.
18. **Properties** (seeded rational points):
    - every point evaluation lies inside the enclosure;
    - the ends of an ATTAINED enclosure are reached at some corner;
    - a sub-box's enclosure lies inside the box's.

**Line face** (`tests_integrated/test_math_lines.py`, on the Clock Lab fixture as test_exact_math.py:45-67 does):
19. **Calculate** voltage·assumed_typical_current in W: 5/4 W. Freshness is CURRENT; after editing power.csv it is REVIEW_REQUIRED.
20. **Memory check:** `check` on the all-concurrent sum FAILS (17 vs 16 MiB). `solve` for workspace gives at most 4 MiB, with the declared 5 MiB outside.
21. **Current solve:** `solve "assumed_typical_current <= declared_current_limit" for assumed_typical_current | within 0 1000 | step 1` gives [0, 300] mA, with the declared 250 mA inside.
22. **Range with `given`:** assumed_typical_current 240–260 mA gives [6/5, 13/10] W, origin GIVEN_IN_LINE.
23. **Tolerance on voltage:** after `tolerances.set` with voltage ±0.25 V, the range is [19/16, 21/16] W, origin OWNER_TOLERANCE.
    - Revising an unrelated field gives CARRIED_OVER.
    - Revising voltage to 5.1 V gives RECHECK, and the tolerance is not applied.
24. **Scopes:** a principal with read scope only runs 19–22. `tolerances.set` is refused for that principal, and the ALWAYS_ASKS matcher catches it.
25. **Solvers hidden** (`-S`): every answer is identical, and none of the new modules imports `sympy` or `z3`.
26. **Grammar:**
    - `solve` without `for` gives STAC_MATH_SYNTAX.
    - A fifth `given` gives STAC_MATH_GIVEN_BOUND.
    - `stac.inspect` shows `math.answer` with scope read.

**Goal face** (the goal slice):
27. **C2 details:** decisive share 6989/7878 for current and 3089/3978 for voltage, so ask about current first. Break-even 40/39. **C3** break-even 25/14. **C1B** break-even e < 30 ms.
28. **Combined goals:** HOLD = C1B ∧ C2 gives FAILS through `truth_and`, and the value of information is 0. Two readings whose ranges do not overlap give CONFLICT.
29. **Effects over the ranges:** V 14/125 W, I 6/25 W, together 44/125 W. Never rank by per-unit derivatives.
30. **Candidates:** from an in-repo fixture made of the rows at P01.json:20 and test_faces_find_light.py:348-350, plus a pulse-ceiling row, they give C1A, C1B, C2, C3 and C4, and nothing with mismatched units.

### Effect on S2's scope and order
- **S1 is unchanged.**
- **New S2, "One math core, in lines" (one builder session, no Qt):**
  - the three new modules;
  - the `stac_bridge` grammar and freshness;
  - Kernel registration;
  - one ALWAYS_ASKS row;
  - two test files added to the hatch gate (tools/check_hatch.py:67);
  - the grammar line in docs/INTEGRATED_I02.md:51.

  Moved in from old S2: the ranges module, tolerances for problems, the decision rule, outward widening, the weakest-precondition ends, and the interval-law tests. It shares no file with S1 except stacy_hand.py, so it can go first if the owner wants lines sooner.
- **New S3, "Goals over data"** (the rest of old S2):
  - the relation, text, state and artifact forms;
  - bindings to cells and tolerances on cells;
  - `goals.check`, `goals.get`, `goals.list`;
  - decisive share, break-even, value of information;
  - Belnap through evidence.py;
  - rebind, and repair in topological order.

  It ships "±5 ms → does not hold, over by 25 to 35 ms".
- **The old S3–S7 each move down one.**
  - The what-if boundary (P07, "up to 500 mA") becomes `math.answer` stage solve.
  - The admissibility helper moves to the escalation slice.
- **Later, with no slice yet:**
  - Then menu rows for the steps;
  - quantity literals such as "12 V" in expressions;
  - allowed regions over several variables, checked against Z3;
  - bisection for nonlinear cases;
  - splitting at poles;
  - repairing sweep's boundary, together with the math_backend working-directory fix, the next time the hashed files are changed on purpose;
  - Atlas rows (they change the catalog digest and its "seven linked profiles" text, docs/HATCH_ALGORITHM_ATLAS.md:24).

## PART 3: Owner note

Draft 0.2 is a good idea, and we take it. Every number in it is right: Graphite's exact engine gets each one. Its four steps (work it out, solve for, range, check) are the maths her goals needed anyway. So we build them once: you use them in a line, and Kasandra uses them to judge her goals.

What we fix:
- The 6 W row is the "Continuous limit", and Rev A and Rev B agree on it.
- Clock Lab's 4 MiB needs all three blocks live at once. The declared 5 MiB does not fit.
- "Below 500 mA" in whole mA is 499.
- Checking corners only is safe for sums like volts times amps, not in general.
- When a range straddles a limit, the real part stays "cannot tell", even when the worst corner fails.
- The step is called "range", because "bound" already means something else in Graphite.

Tolerances stay yours: only you record one, and it waits for your Approve. SymPy and Z3 stay optional. Your ThinkPad install leaves them out, and nothing new needs them.

When: one build session right after her first hand on the Field, for lines on problem sheets. Her goals on your After Hours sheets follow in the next session.

Files:
- /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/hand_design/judge_hand-plan.md
- /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/hand_design/read_maths.md