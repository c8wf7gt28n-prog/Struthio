export const meta = {
  name: 'kasandra-hand-planner-design',
  description: "Design Kasandra's hand on the desk with a planner over conditions (weakest preconditions, intervals, receding horizon): map, two designs, one judged plan; no building",
  phases: [
    { title: 'Understand', detail: 'three readers: the desk as states and acts, the model path and the work loop, the maths already in the code' },
    { title: 'Design', detail: 'two designers from different angles' },
    { title: 'Judge', detail: 'one judge writes the plan and the owner page' },
  ],
}

const S = '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad'
const PY = S + '/work/venv/bin/python'
const REPO = '/home/user/Struthio'

const GOAL = `
Graphite is a local-first Python 3.13 / PySide6 desktop workspace (repository ${REPO}, branch at 0.8.2). Its assistant is
Kasandra ("Kas") in the Kasandra appearance and Stacy in Graphite (workbench/assistant_identity.named()). The owner runs a
Qwen3.6-35B-A3B (a mixture of experts) on a ThinkPad (Ryzen 7 7735HS, Radeon 680M, 64 GB shared memory); here we test with
small Qwen3.5 4B and 2B GGUF models (${S}/models/) on a 4-core CPU.

Where we are. 0.8.2 gave the desk 40 named DESK ACTS (workbench/desk_acts.py: registry, schemas, marks "navigates" or
"changes", OWNER_ONLY, MENU_ROWS/PANEL_ROWS allow-lists, desk_hers() = her hand's rule for an act at a dial place, tools() and
plan_variants() exports; workbench/desk_doers.py: run(host, name, args, door=...) does an act on the live window by pointer or
keys and returns an envelope with a read-back; read.desk reads the window back; workbench/desk_scene.py: scripts of acts with
expected read-backs; the owner's playable scene tools/campaign_lib/data/scenes/P01.json). The door for her model, door='her',
is REFUSED today (desk_doers.run raises NOT_OFFERED). Her hand for data changes is workbench/stacy_hand.py (the dial: Ask
first / Do and show / Free hand; hers(), why_asks, what always asks) and shell2.SlateFace.stage (card, trail, one Undo).

The owner's direction now: "We keep building for Kasandra's hand" and "Keep working on the big things you're smart about like
maths." Earlier the owner proposed, and we agreed, a planner (verbatim excerpts):
  "make Graphite's Field into a planner that can reason backward from what you want, then check forward against what actually
  happened. Kasandra would take a request ... and propose what has to be true when she's done. Graphite would use those
  conditions to decide what to inspect, which programs to run, and which checks to repeat when something changes."
  "Dijkstra's weakest precondition ... wp(a1;a2,G) = wp(a1, wp(a2,G)) ... A checked method can supply this decomposition, in
  the spirit of hierarchical task network planning ... An operation would carry what it needs, what it can affect, and how to
  check its result."
  "interval arithmetic to decide when to investigate ... The measured startup pulse is 110 ms and the Rev B limit is 80 ms.
  Suppose ... a verified error bound of ±5 ms ... T_pulse - T_limit in [105,115]-80 = [25,35] ms. Every value in that interval
  exceeds the limit. A more precise reading has zero value for that particular pass/fail decision ... value of information."
  "receding-horizon control. Consider a few steps ahead, execute the first authorized action, observe the actual result, then
  update the plan. If an input changes, use the dependency graph to repair the affected part."
  "M_resident + max_t sum_{i: s_i<=t<e_i} m_i <= M_budget" (memory admissibility of a schedule; workbench/schedule_math.py:16).
  "The first version I'd try: give the same 35B two runs of the I05 case that got stuck. One uses the current loop. The other
  gets a graph of outstanding conditions and a short lookahead over available actions. If it proposes a repeated read on the
  same inputs, Graphite hands back the existing evidence and shows which condition still needs work. If a write times out,
  Graphite checks what actually landed before considering a retry. Finish requires evidence for each agreed condition."
We also agreed an escalation rule: when the model cannot decide, first more thinking or self-consistency, then a batched model
swap (a dense model, or a vision model where pictures matter) proposed under her hand (brain.model.use is approve scope).

The aim of THIS workflow: a plan for the next build pass, "Kasandra's hand on the desk, with a planner over conditions": her
door to the desk acts, and one conditions engine that serves both the desk (window state, verified by read.desk) and the work
(data conditions verified by Kernel reads, intervals where tolerances are recorded), with the model naming goals and choosing
questions while deduction does what can be deduced. Owner rules that hold: never name the line language (staC) on screen ("a
line"); no keyboard key printed on screen; "Apps", never "Programs"; what always asks still asks; nothing is removed.
`

const READ_RULES = `
You are a reader. Do not edit anything under ${REPO}. Scratch only under ${S}/work/hand_read/<your part>/. To run code, make a
copy with "git -C ${REPO} archive HEAD | tar -x -C <dir>" and run only inside "QT_QPA_PLATFORM=offscreen unshare --pid --fork
--mount-proc --kill-child ${PY} -B ..."; never run tools/check_*_ui.py anywhere; do not load a model (the CPU is shared).
Cite file:line for every claim. Return a Markdown map, no preamble.
`

const R1 = GOAL + READ_RULES + `
YOUR PART: the desk as states and acts. (1) The state vocabulary: every field read.desk reports (desk_doers: read_desk and the
*_said helpers): surface, popups, menu (open, which, rows, panel count/line/preview), field (face, selected, whole, zoom, route,
revisions), files (folder, view, names, selected), line (target, text, results, room), talk (cards, trail, hand), look, motion.
Propose a finite abstraction of it a planner can search (which fields, which values, what is "unknown"). (2) For EACH of the 40
acts: its preconditions (what must hold for the doer to succeed, read from the doer's code and its refusals, e.g. sheet.trace
needs the Field in front and a sheet selected; then.keep needs the line panel open), its effects (what holds after, certain or
only observed), its mark and owner_only, and what desk_hers says at each dial place. Give it as an operator table (STRIPS-like:
pre, add, delete, observe). Verify a sample of 8 acts on a live offscreen window: the bench window of
tests_integrated/test_desk_acts.py (build_window) from your copy, or ${S}/tools/field/desk/harness.py with DESK_TREE pointing
at your copy; report what each act's envelope and read.desk said before and after. (3) The playable scene P01 as a plan: which
of its 17 steps a backward planner would derive from the goal conditions alone (e.g. goal "REV A / REV B of 07 Limits shown"),
and which need the model's choice. (4) Where her door would plug in (desk_doers.run, door='her'; desk_hers; record(); her trail)
and what must be added so that what she does is seen, stoppable, and undoable where it changes data.
`

const R2 = GOAL + READ_RULES + `
YOUR PART: the model path and the work loop. Map: how a chat or plan turn offers operations to the model and checks its answer
(workbench/local_brain.py proposal_profile, plan_prompt, checked_plan, run_reply; stacy_control.validate_actions;
agent_operations DIRECT_OPERATIONS; tool_selection); the token budgets (context sizes, PROGRAM_TOOL_LIMIT etc.); the
assignment loop (workbench/adaptive_work.py: advance, the duplicate guard DUPLICATE_ACTION_ON_UNCHANGED_INPUTS, the completion
check near :164; adaptive_contract.py: the next-step schema with oneOf variants near :145; agent_loop.py; decision_seconds and
the 180 s limit); the joined trial I05 (workbench/joined_model_checks.py) and what happened when the 4B ran it here:
${S}/work/live4b/i05_4b_baseline.json (the capacity trial, passed 3/3) and ${S}/work/live4b/i05_joined_4b.json (I05 Current_A
failed MODEL_DECISION_FAILED LOCAL_STREAM_TIME_BUDGET under CPU load); read their records for what the model was asked and
what it answered. Then say exactly: where a "goal and conditions" turn would sit; what a small model (4B) can do reliably in
one short structured answer (from the evidence); how the duplicate guard could hand back evidence instead of failing; how a
timed-out write could be checked for what landed; where a model swap (brain.model.use) is decided today and how an escalation
could be proposed under her hand. Also map how her cards, trail and Undo are shown (shell2.SlateFace) so a plan's progress
(conditions turning held) could be shown there.
`

const R3 = GOAL + READ_RULES + `
YOUR PART: the maths already in the code and where conditions and evidence live. Map: workbench/field_ripple.py (the what-if
propagation near :107: how values are re-worked along wires, units, exactness), workbench/schedule_math.py (peak overlap near
:16), the Field's records (office records, revisions, provenance: what a sheet, source, calculation, finding is; "current",
"recheck", "held"; where a finding's condition like "Up to 80 ms" or a limit lives; field_doubt's traps; quantities in base
units), where an error bound or tolerance could be recorded today (a sheet column? a datasheet field? nowhere?), and what
After Hours 07 holds (docs/RELEASE_NOTES_0.4.3.md:10 and the restored workspace via ${S}/tools/field/nomodel.py if needed:
07 Bench readings 110 ms startup, Rev A 120 ms, Rev B 80 ms, settled and startup power). Then propose, with exact formulas and
small worked examples on After Hours 07: (a) a condition record {statement, a machine-checkable predicate, evidence (record,
revision), state open/held/broken/unknown, what it depends on}; (b) operators with pre/effects for Kernel operations (which
operations are reads that establish evidence, which change, which are checks); (c) the regression (weakest precondition) over a
finite abstraction, with a bound on search size; (d) interval arithmetic with units and recorded tolerances (sum, difference,
product, quotient; inclusion monotonicity; outward rounding with exact decimals or fractions as field_ripple does), the
decision rule "robust when the interval lies wholly on one side", and value of information for choosing the next observation;
(e) receding horizon with repair along the dependency graph; (f) memory admissibility of a plan's jobs with schedule_math.
Keep it buildable in Python without new dependencies.
`

const DESIGNER = (angle, m1, m2, m3) => GOAL + `
Three readers mapped the code:
=== THE DESK AS STATES AND ACTS ===
${m1}
=== THE MODEL PATH AND THE WORK LOOP ===
${m2}
=== THE MATHS AND WHERE CONDITIONS LIVE ===
${m3}
===
You are a designer with this angle: ${angle}
Read-only for ${REPO} (check claims against the code; cite file:line). Write a design (Markdown) for the next build pass,
covering: (1) the conditions engine: the record, its states, evidence and revision binding, where it is stored, how it is
shown; (2) operators: the desk acts' pre/effects and the Kernel operations' (reads that establish evidence, changes, checks);
(3) the planner: backward regression (weakest precondition) over a finite abstraction, search and bounds, HTN methods for known
jobs, what is deduced and what is asked of the model; (4) execution: receding horizon, one authorized act at a time, verified
by read.desk or a Kernel read, repair on surprise, stop at any moment by the owner, the dial (Ask first / Do and show / Free
hand) and what always asks; (5) her door: desk_doers.run(door='her'), what she may do without asking (desk_hers), how each act
she does is shown to the owner (her column, the pointer on the window, the trail) and undone where it changes data; (6) the
model's contract: what she is asked (goal and conditions, the next question, a choice among the planner's options), the JSON
schema, the token budget for a 4B at 4096 context, and what happens when the answer is wrong or late; (7) intervals and value
of information on After Hours 07 (the 110 ms vs 80 ms example with a recorded ±5 ms), where tolerances are recorded;
(8) the escalation rule (thinking, self-consistency, a batched model swap under her hand); (9) the I05 experiment: the current
loop against the conditions loop with the same model (the 4B here; the 35B on the ThinkPad), what is measured; (10) the build
order in slices, each shippable with its tests and scenes (new scenes P02... for her door), and what is NOT in the pass.
Be concrete: names, files, functions, formulas, numbers. Return the design only.
`

const ANGLE_A = 'PLANNER FIRST. Deduction does every step it can: the model only names the goal (and conditions) in one short answer, the planner derives the act sequence by regression, executes it with receding horizon and verifies each step. Small models become reliable because they are asked little. Open-ended work falls back to the model choosing among the planner\'s options.'
const ANGLE_B = 'MODEL IN THE LOOP. The model proposes each next step from the outstanding conditions and a short lookahead the planner computes and shows it; the planner checks, repairs and refuses; evidence is handed back on repeats. Best for open-ended research where the method is not known in advance, while staying safe and cheap enough for a 4B and fast with the 35B.'

const JUDGE = (m1, m2, m3, a, b) => GOAL + `
Two designers proposed the next pass.
=== DESIGN A (planner first) ===
${a}
=== DESIGN B (model in the loop) ===
${b}
=== THE MAPS (for checking) ===
--- desk ---
${m1}
--- model path ---
${m2}
--- maths ---
${m3}
===
You are the judge. Score each on: reliability with a 4B here and the 35B on the ThinkPad; safety (her hand's rules, what always
asks, nothing done unseen); the owner's maths (weakest precondition, intervals, value of information, receding horizon) used
where it truly helps, not decoration; buildability in slices. Check claims you rely on against the code (read-only, cite
file:line). Then write TWO things:
PART 1, THE PLAN for the builder: the synthesis (say what you took from each), with every element of the designers' ten
points decided, the first slice to build (small enough for one builder session, with its tests, a scene for her door, and the
4B check), then the later slices in order.
PART 2, THE OWNER PAGE: at most 450 words in plain English for the owner, who reads on a phone: what Kasandra's hand on the
desk will do, how the maths makes a small model reliable, what the owner will see and control, and what is tested here versus
on the ThinkPad. No code, no file names, no jargon without a one-line meaning; never name the line language; never print a key.
Return PART 1 and PART 2, nothing else.
`

phase('Understand')
const [m1, m2, m3] = await parallel([
  () => agent(R1, { label: 'read:desk-states', phase: 'Understand' }),
  () => agent(R2, { label: 'read:model-path', phase: 'Understand' }),
  () => agent(R3, { label: 'read:maths', phase: 'Understand' }),
])
if (!m1 || !m2 || !m3) return { m1, m2, m3, plan: null }
phase('Design')
const [dA, dB] = await parallel([
  () => agent(DESIGNER(ANGLE_A, m1, m2, m3), { label: 'design:planner-first', phase: 'Design' }),
  () => agent(DESIGNER(ANGLE_B, m1, m2, m3), { label: 'design:model-in-loop', phase: 'Design' }),
])
if (!dA && !dB) return { m1, m2, m3, plan: null }
phase('Judge')
const plan = await agent(JUDGE(m1, m2, m3, dA || '(missing)', dB || '(missing)'), { label: 'judge:hand-plan', phase: 'Judge' })
return { m1, m2, m3, dA, dB, plan }
