export const meta = {
  name: 'pal-draft-02-verify-and-merge',
  description: "Verify PAL draft 0.2's mathematics section (every number and every claim about Graphite's existing math engine) and merge it with the planned conditions engine (hand slice S2) into one math core",
  phases: [
    { title: 'Verify', detail: 'one checks every number exactly; one checks every claim about the code' },
    { title: 'Merge', detail: 'one judge: verdicts, and one math core serving PAL stages and the goals engine' },
  ],
}

const S = '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad'
const PY = S + '/work/venv/bin/python'
const REPO = '/home/user/Struthio'
const W = S + '/work/pal02'

const DRAFT = `
PAL draft 0.2, section 6 "Mathematics in staC" (the owner pasted it; summarised faithfully, numbers verbatim):
- Claims about the code: "Graphite already implements exact rational quantities, dimensional checks, typed arithmetic and an affine
  boundary calculation. Its optional bounded SymPy adapter handles a restricted linear-equality profile. Its Z3 adapter checks
  feasibility for a declared linear real and integer fragment. The exact engine can recheck a candidate assignment against the
  original model. The current staC shorthand math problem:PROBLEM_ID | calculate "voltage * assumed_typical_current" | unit W lowers
  to one read-only preview." "The existing sweep supplies exact single-variable affine boundaries separately from its sampled chart."
  "The current solver adapter does not independently certify infeasibility." "Six existing exact-math tests passed. The two
  optional-backend suite tests were skipped in this run because Z3 was absent." "A second fixture can use Clock Lab's existing 16 MiB
  capacity model. Its 4 MiB workspace boundary holds when the two 6 MiB allocations overlap." Sources it cites:
  docs/INTEGRATED_I02.md; workbench/math_model.py:127,184,221,234; math_units.py:41; math_backend.py:24,54,83; stac_bridge.py:76;
  docs/HATCH_ALGORITHM_ATLAS.md (the Algorithm and Theory Atlas: method domains, preconditions, costs, guarantees).
- Proposed stages on a checked model: evaluate (exact quantities or predicates, preserving unit, source, revision, measured or
  assumed), solve for (a named unknown -> an admissible range or sufficient constraints; start with one affine variable, several
  intersecting limits, open endpoints, integer settings; a solver's example assignment is a witness), bound (declared input
  intervals -> a conservative enclosure with exactness status and assumptions; elementary rational interval operations), check (a
  requirement -> an assessment, a rechecked counterexample, or an open obligation; incompatible units, contradictory assumptions,
  unsupported methods, resource exhaustion kept distinct). Then could offer "Solve for current" on the checked power model.
- Worked numbers (After Hours 07): 12 V x 280 mA = 3.36 W, 2.64 W below the 6 W Rev B settled limit. Solve 12 V x I <= 6 W, I >= 0:
  inclusive ceiling 500 mA; 501 mA gives 6.012 W (a counterexample). Startup 110 ms against 80 ms: over by 30 ms. Change settled
  current to 300 mA: 3.60 W, 2.40 W headroom. Voltage 11.8-12.2 V and current 270-290 mA: 3.186-3.538 W, at least 2.462 W headroom
  (ranges invented for the example). Robust ceiling across that voltage range: at 12.2 V exactly 30,000/61 mA, about 491.803 mA; with
  whole-mA settings 491 mA passes at 5.9902 W, 492 mA gives 6.0024 W. At fixed 12 V each mA adds 12 mW; derivatives in W/V and W/mA
  cannot be ranked by magnitude alone.
- Rules: for a x + b <= 0 the boundary is -b/a exactly; positive a gives an upper bound, negative a lower, zero a either the whole
  domain or a contradiction; intersect with the domain, keep inclusive or exclusive endpoints, respect integer steps. Uncertainty:
  propagate bounds with an enclosure guarantee, preserve repeated inputs' identity (x - x is exactly 0; independent interval
  subtraction is wider), simplify exactly or affinely first, then intervals; a denominator interval containing zero needs a domain
  obligation or a checked split. Guarantee: first establish the admissible domain is nonempty, then check the conjunction with the
  negated requirement; a checked violating assignment is a counterexample; an enclosure touching both sides decides nothing alone;
  solver-only infeasibility labelled with its backend; timeout, inconsistent assumptions and missing observations distinct.
- Math receipt: typed expression or constraints, model digest, inputs and units, source revisions, assumptions, method, exact result
  or enclosure, scope, witness or derivation. Acceptance: the 500 mA and 30,000/61 mA vectors, an exclusive endpoint, negative and zero
  coefficients, inconsistent bounds, an integer step, a unit mismatch, a denominator crossing zero, repeated variables, a stale limit
  record, an unavailable solver; the same model through the typed line and Then; benchmark calculation, inverse bound and witness
  recheck separately.
`

const RULES = `
RULES: Read-only for ${REPO}; work under ${W}/<part>/ on a copy made with "git -C ${REPO} archive HEAD | tar -x -C <dir>". Run code
only inside "nice -n 15 unshare --pid --fork --mount-proc --kill-child ${PY} -B ..." (QT_QPA_PLATFORM=offscreen if Qt is imported);
never run tools/check_*_ui.py; other builds share this machine, so stay light. Cite file:line. Return a Markdown report: a table of
claim -> verdict (TRUE / FALSE / PARTLY / UNVERIFIABLE) -> evidence, then notes; no preamble.
`

const NUMBERS = DRAFT + RULES + `
YOUR PART: every number in the draft, recomputed in exact rational arithmetic (fractions.Fraction), and every rule tested on small
cases: the affine boundary with positive, negative and zero coefficients, exclusive endpoints and integer steps; the interval
enclosure of the power product over the rectangle (monotone in each nonnegative input, so the corners suffice; say so); the
dependency problem (x - x); a denominator interval containing zero. Then reproduce what Graphite's own engine gives for the same
cases (workbench/math_model.py, math_units.py, field_ripple.py where relevant): call its functions directly and compare outputs
exactly, including units and endpoint inclusivity. Report any number or rule that is wrong, imprecise, or where Graphite's engine
disagrees with exact arithmetic.
`

const CODE = DRAFT + RULES + `
YOUR PART: every claim about the code. Read docs/INTEGRATED_I02.md, docs/HATCH_ALGORITHM_ATLAS.md, workbench/math_model.py,
math_units.py, math_backend.py, stac_bridge.py and any module they name. Check each claim: exact rational quantities, dimensional
checks, typed arithmetic, the affine boundary calculation and where it lives; the SymPy adapter's profile and bound; the Z3 adapter's
fragment, whether either package is installed here (and in the release's offline wheels: look for them under the repository and the
packaging manifests), and what happens when absent; whether the exact engine rechecks a candidate assignment; the
"math problem:PROBLEM_ID | calculate ... | unit W" shorthand: does it parse and lower to one read-only preview (show the plan); the
sweep's exact single-variable affine boundary; whether infeasibility is certified independently; the test counts (find the
exact-math tests, run them, report passed and skipped and why); Clock Lab's 16 MiB capacity model and its 4 MiB workspace boundary
with two 6 MiB allocations overlapping (find it; reproduce it with workbench/schedule_math.py). Also map what exists for each proposed
stage (evaluate, solve for, bound, check): already there, partly there, or new.
`

const MERGE = (numbers, code, plan) => `
Graphite's assistant Kasandra is getting a hand on the desk with a planner over conditions. Its judged design (slices S1-S7) plans,
in slice S2 "Conditions over data", a pure-maths module bounds.py (exact Fraction intervals in base units built from unit_spec and
rational, the decision rule holds/does not hold/cannot tell, division by an interval containing 0 -> cannot tell, outward widening,
decisive share, break-even, value of information ranking, weakest-precondition boundaries from math_model.affine and sweep,
ledger.bound/1 tolerances set only by the owner) and goals (C1A, C1B, C2, C3, C4 on After Hours 07). The plan's full text:
${plan}
Now the owner sent PAL draft 0.2 whose section 6 proposes math stages for lines. Two verifiers checked it:
=== NUMBERS AND RULES ===
${numbers}
=== CLAIMS ABOUT THE CODE ===
${code}
===
You are the judge. Read-only for ${REPO} (check what you rely on, cite file:line). Write:
PART 1, VERDICT: what in draft 0.2 is right, wrong or imprecise (with the corrections), and what it adds beyond the S2 plan.
PART 2, ONE MATH CORE: a merged design so that PAL's stages (evaluate, solve for, bound, check) and the goals engine (S2) are ONE
implementation with two faces (a line step the owner or Then can use, and a goal assessment the planner uses): module boundaries,
the receipt (PAL's math receipt and the goal's evidence as one record), names that do not collide with existing meanings of
"condition" and "bound", which existing code each part reuses (math_model, math_units, math_backend, schedule_math, field_ripple),
what stays optional (SymPy, Z3: are they shipped?), the exact test vectors (the draft's and S2's), and how it changes slice S2's
scope and order (what moves in, what stays later). Keep it buildable in one builder session for its first slice.
PART 3, OWNER NOTE: at most 200 words in plain English: is draft 0.2 a good idea, what we take, what we fix, when.
`

phase('Verify')
const [numbers, code] = await parallel([
  () => agent(NUMBERS, { label: 'verify:numbers', phase: 'Verify' }),
  () => agent(CODE, { label: 'verify:code-claims', phase: 'Verify' }),
])
phase('Merge')
const plan = await agent(MERGE(numbers || '(missing)', code || '(missing)', 'READ IT: ' + S + '/work/hand_design/judge_hand-plan.md (PART 1, sections 1, 3, 7, 10 S2).'), { label: 'judge:one-math-core', phase: 'Merge' })
return { numbers, code, plan }
