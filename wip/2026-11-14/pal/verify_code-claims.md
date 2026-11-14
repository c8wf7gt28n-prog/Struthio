## PAL 0.2 §6 code claims checked against HEAD bbf033b

Of the 15 claims, 11 hold, 3 hold only in part and 1 cannot be checked. The three partial ones are the test counts, the 4 MiB boundary and the offline wheels. I worked on a copy at /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/pal02/code. Every run used the scratch venv inside `nice … unshare`. The repository was not touched.

| # | Claim | Verdict | Evidence |
|---|---|---|---|
| 1 | Exact rational quantities | TRUE | `math_units.py:41-52`: `rational()` takes decimal or rational strings only and returns a `Fraction`. It refuses floats, `nan` and exponents over 100, and limits values to 2048 bits. `math_model.py:95-103` evaluates in base units. Probe: 0.1+0.2 gives `3/10`; 12 V × 280 mA gives `84/25` W (3.36). `stac/quantities.py:68-82` also uses `Fraction`. |
| 2 | Dimensional checks | TRUE | `math_model.py:60` refuses add, subtract and compare across different dimensions (`DIMENSION_MISMATCH`). `math_units.py:70` raises `INCOMPATIBLE_OUTPUT_UNIT`. `KB` is refused (`test_exact_math.py:22`). One catch: a bare literal has no unit, so `p - v*i <= 0` is refused. A zero must be written as a quantity with a unit. |
| 3 | Typed arithmetic | TRUE | `math_model.py:25-87`: each node gets a signature (kind, dimension, unit, degree). Limits are 16 variables, 128 nodes, depth 24 and degree 4. `compile_expression` (`:150-181`) walks the parsed expression against a whitelist. There is no `eval`, and calls, attributes and indexing are refused. |
| 4 | An affine boundary calculation, and where it lives | TRUE | `affine()` at `math_model.py:184-218` builds a base-unit constant plus coefficients. It refuses products of two variables (`:211`) and variable denominators (`:214`). The boundary itself is computed only inside `sweep()`, as `root=-c/coefficients[variable]` (`:253`). It is not a separate operation. |
| 5 | Optional bounded SymPy adapter, restricted linear-equality profile | TRUE | `math_backend.py:83-120`: `linsolve` runs on `eq` constraints only. Inequalities return `UNSUPPORTED` (`:109`); underdetermined or non-rational results return `UNKNOWN` (`:116-117`). Bounds: a child process (`:36-37`) with CPU 3 s, address space 512 MiB, file size 1 MiB (`:127-128`), wall time ≤5 s and stdout ≤256 KiB (`:39`). Probe: `12V*I==6W` gives i=500, FEASIBLE and rechecked; `12V*I<=6W` gives UNSUPPORTED. Beyond the claim: with no constraints, SymPy also normalises nonlinear rational expressions, because `solve()` lets the affine check fail for SYMPY in that case (`:27-30`). |
| 6 | Z3 adapter checks feasibility for a declared linear real and integer fragment | TRUE | `math_backend.py:54-80` uses `z3.Int`/`z3.Real` (`:57`), timeout 2500 ms and rlimit 150000 (`:62`), and adds nonzero guards for denominators (`:70`). Nonlinear input is refused with `UNSUPPORTED` before any process starts. Probe: `12V*I<=6W` with I≥0 gives the witness i=**0**, not a ceiling. Contradictory bounds give INFEASIBLE. |
| 7 | The exact engine can recheck a candidate assignment against the original model | TRUE | `witness_check` at `math_model.py:221-231` checks that known values are unchanged, integer domains, bounds, zero denominators (through `values()`), no missing inputs, and that every constraint is True. `solve()` uses it at `math_backend.py:43-44`. A forged backend answer of i=501 came back `UNKNOWN BACKEND_WITNESS_REJECTED_BY_EXACT_IR`. SymPy also uses it (`:119`). |
| 8 | The `math problem:ID \| calculate "…" \| unit W` shorthand lowers to one read-only preview | TRUE | `stac_bridge.py:76-87`; routing `:18-30`; one dispatch in `run()` `:113-120`. Details below the table. |
| 9 | The sweep gives exact single-variable affine boundaries separately from its sampled chart | TRUE (with limits) | `math_model.py:234-260` returns `boundaries` separately from `samples`, with the notice "Sampled graph, not a proof between samples…". Clock Lab through `math.sweep` (read scope) gives `4` MiB; samples at 4 and 9/2 give True and False. 12 V gives 500 mA; 12.2 V gives `30000/61`. The limits are listed in the notes. |
| 10 | The solver adapter does not independently certify infeasibility | TRUE | Z3 `unsat` becomes `INFEASIBLE` (`math_backend.py:72`); SymPy `EmptySet` does the same (`:114`). Only FEASIBLE answers are rechecked (`:43`). Probe: a forged INFEASIBLE for a feasible model was passed through as `INFEASIBLE` with `witness_check: NO_WITNESS_CLAIM`. The result does name the backend (`:45`). |
| 11 | "Six exact-math tests passed; the two optional-backend tests were skipped because Z3 was absent" | PARTLY | The counts are right. Whether they skip depends on the interpreter, and the skip needs either package missing, not Z3 alone. Details below. |
| 12 | Clock Lab has a 16 MiB capacity model | TRUE | `examples/clock_lab/inputs/problem.json`: memory_limit 16 MiB, buffer_A 6, buffer_B 6, workspace 5, and all three lifetimes UNKNOWN; also `requirements.md`. With all three concurrent, 17 MiB > 16 MiB gives INFEASIBLE (`math_checks.py:12,26-28`; reproduced). |
| 13 | "Its 4 MiB workspace boundary holds when the two 6 MiB allocations overlap" | PARTLY | The 4 MiB comes from the all-concurrent expression `buffer_A + buffer_B + workspace <= memory_limit` (`math_checks.py:36-40`, `test_exact_math.py:41-42`). Buffers A and B overlapping is not enough; the workspace must also be live while both are. Reproduction below. |
| 14 | Packages installed here, in the release's offline wheels, and behaviour when absent | the draft's premise that Z3 is absent is FALSE for this venv; whether the offline wheels contain them is UNVERIFIABLE | Details below. |
| 15 | The cited lines and the Atlas description | TRUE | `math_model.py:127` evaluate, `:184` affine, `:221` witness_check, `:234` sweep; `math_units.py:41` rational; `math_backend.py:24` solve, `:54` z3_solve, `:83` sympy_solve; `stac_bridge.py:76` math branch. `HATCH_ALGORITHM_ATLAS.md:3` gives signature, domain, preconditions, guarantees, counterexample and cost; the table is at `:9-22`. Linear optimization is listed as reference only (`:18`). |

### Claim 8: the shorthand, in detail
- **Compiled plan:**
  ```
  {"kind":"MATH","ir":{"schema":"arc.stac.math-ir/1","operation":"math.preview","arguments":{"id":…,"expression":"voltage * assumed_typical_current","output_unit":"W"},"effects":["read"],"result_type":"SourceBoundMathematicalPreview","program_id":…},"runtime_authorization":false}
  ```
- **`stac.inspect`:** returns one step, `{"command":"read","operation":"math.preview",…}`, with `required_scope:"read"` and `source_binding:{"state":"RUNTIME_CHECK_REQUIRED"}`.
- **Read-only:** a principal with read scope only ran it and got `5/4` W, both bindings `PROBLEM_REVISION`. The same principal's `math.prepare` was refused.
- **Strict grammar:** it takes 5 or 8 tokens only. A non-32-hex ID gives `STAC_MATH_PROBLEM_ID`; an unquoted expression or a `solve` verb gives `STAC_MATH_SYNTAX`.

### Claim 11: the test runs
- `tests_integrated/test_exact_math.py` holds 6 tests: 4 in `ExactMath` and 2 in `MathematicalBindings`. The fixture's own tests are switched off at `:71-73`.
- `tests_integrated/test_exact_math_solvers.py` holds 2 tests under `skipIf(MISSING)` (`:7-10`). It skips if sympy **or** z3 is missing.
- **Scratch venv** (sympy 1.14.0, z3-solver 4.15.4.0, mpmath 1.3.0, all at the pinned versions): 8 ran, 8 OK, 0 skipped, 4.4 s.
- **With site-packages hidden (`-S`)**, which matches `/usr/local/bin/python3` (it has neither package): 6 OK and 2 skipped. The skip message is "needs requirements-math.txt: **sympy, z3** not installed".
- `test_exact_math` is in the hatch gate (`tools/check_hatch.py:67`); the solver tests are on-demand only (`:71-72`).

### Claim 13: the schedule reproduction
The fixture's lifetimes are UNKNOWN, so `math.schedule` on it returns UNKNOWN with all three lifetimes missing. I declared lifetimes in ms (half-open intervals) and called `schedule_math.evaluate` directly:

| Scenario | Results | Boundary |
|---|---|---|
| A and B overlap, workspace inside the overlap | w=4 FEASIBLE (peak 16); w=4.000001 INFEASIBLE | 4 MiB |
| A and B overlap, workspace overlaps A only | w=10 FEASIBLE (peak 16); w=10.5 INFEASIBLE | 10 MiB |
| Workspace after both | w=10.5 FEASIBLE (peak 12) | not 4 MiB |
| A and B disjoint, workspace spans both | 10 MiB | 10 MiB |

`schedule_math` gives a verdict for one scenario, not a boundary. Lifetimes can only come from the problem's interval variables (`schedule_math.py:31-32`); there is no override path for them.

### Claim 14: packages and offline wheels
- **Installed:** the venv has all three packages at the pinned versions; the system python3 has none.
- **Offline wheels:** there are no `*.whl` files and no `OFFLINE_FILES.json` in the repository. The cache is "not contained in the programme parts" (`docs/MINIMAL_DEBIAN_INSTALL_01.md:72`).
- **Install path:** `requirements-math.txt` is installed only with `--math` (`INSTALL_LEDGER.sh:41`). `INSTALL_LS.py:331` passes `--math` only for `--profile suite`. The documented ThinkPad command (`docs/THINKPAD_FIRST_INSTALL.md:29-31`) uses the default desktop profile with `--calc` and no `--math`. On that path, SymPy and Z3 would not be installed.
- **When absent:** `math_backend.py:31-33` returns `UNAVAILABLE` with the dependency rows (reproduced with `-S`). The affine check at `:27-30` runs first, so a nonlinear model still gets `UNSUPPORTED` without the packages.

## Notes

- **The staC preview ignores whether sources changed.** `math.preview` uses `problems.load` (`math_service.py:215`), not `current()`. After I edited `power.csv`, the problem's freshness was `REVIEW_REQUIRED`, yet `stac.run` still returned 5/4 W with no freshness field in the result. `math.prepare` was correctly refused with `MATH_SOURCE_CHANGED`. This matters for the "stale limit record" acceptance vector.
- **"Read-only" still writes log rows.** `stac.run` added rows to `audit` (11→13), `activity_journal` (22→26) and `instruction_matrix` (0→1). It wrote no math records.
- **The solvers depend on the working directory.** `math_backend.py:36` runs `python -m workbench.math_backend` with no `cwd` and no `PYTHONPATH`. Started from any directory other than the program root, both backends return `UNKNOWN BACKEND_RESOURCE_OR_PROCESS_FAILURE` (exit 1) even though they are installed. The launchers `cd` into the program folder first (`START_OFFICE.sh:5`), so the app itself works. The risk is for the "unavailable solver" vector, where a working-directory failure would be reported as a resource failure instead of `UNAVAILABLE`.
- **Sweep boundary limits (claim 9):**
  - The root is not clipped to the variable's declared bounds: with an upper bound of 400 mA it still reports 500, with only `within_sample_range:false`.
  - Integer steps are ignored: an integer `i` still reports `30000/61`.
  - Strict and inclusive are told apart only by the `relation` field (`lt` and `le` both give 500).
  - A zero coefficient (`x - x`) or a second free variable produces no boundary, and nothing says why.
  - The sweep reads a prepared math action, and preparing one needs execute scope.
- **The worked numbers reproduce exactly:** 3.36 W; ceiling 500 mA; 501 mA gives 6.012 W (witness check False); 12.2 V gives 30000/61 mA; 491 mA gives 5.9902 W and passes; 492 mA gives 6.0024 W and fails.

### What already exists for each proposed stage
- **evaluate: already there (mostly).**
  - `core.evaluate` is exact, carries units, model digest and assumptions, and sets `scope:DECLARED_MODEL_CONSEQUENCE`.
  - The `math.prepare`/`math.run` receipt (`math_service.py:78-110`) binds the problem revision, context digest, sources, implementation hashes, and per-variable origin (`PROBLEM_REVISION` or `DECLARED_SCENARIO`).
  - Missing: "measured" versus "assumed" exists only as free text in `basis` (`problem_service.py:16-22`); there is no typed flag.
- **solve for: partly there.**
  - Pieces: `affine()`, the sweep's root and coefficient sign, Z3's single witness (arbitrary, e.g. i=0, with no optimisation), and SymPy's unique solution of linear equalities.
  - New work: an admissible-range result, intersecting several limits, intersecting with the domain, open and closed endpoints, rounding to integer steps, the zero-coefficient verdict (whole domain or contradiction), and a `solve` verb in staC.
- **bound: new.**
  - There is no interval arithmetic. Only scalar domains are admitted (`math_model.py:37`), and I02 says interval arithmetic is unsupported (`INTEGRATED_I02.md:29`).
  - Reusable pieces: lower and upper bounds on variables (used by Z3 and the witness check today), exact cancellation of repeated variables in `affine()` (`x - x` gives `(0, {})`), and the nonzero-denominator conditions (`math_model.py:65,73`). There is no check for a denominator interval crossing zero.
- **check: partly there.**
  - Pieces:
    - **Relation at fixed inputs:** `evaluate` gives a relation's truth for fixed inputs, with INFEASIBLE when a constraint is false (`:144`).
    - **Witness recheck:** `witness_check`.
    - **Distinct states:** `DIMENSION_MISMATCH`, `DOMAIN_ERROR`, `UNSUPPORTED`, `UNAVAILABLE`, `UNKNOWN` (`BACKEND_WALL_TIME_LIMIT` or a resource failure), and a list of missing inputs.
  - New work: one operation that first checks the domain is nonempty and then checks the domain together with the negated requirement. Today there is no negation node; you can only flip the relation by hand. Also new: a counterexample record, detection of contradictory assumptions (assumptions are free strings, `:86`), and an explicit "not certified" marker on infeasibility found only by a solver.
- **Math receipt: mostly there** as the action plus `math_result` (`math_service.py:82-86,106-108`). Missing fields: method or guarantee class, enclosure or exactness status, and witness or derivation.

### Probe scripts
- /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/pal02/code_scripts/probe_engine.py
- /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/pal02/code_scripts/probe_absent.py
- /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/pal02/code_scripts/probe_kernel.py