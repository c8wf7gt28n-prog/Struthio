export const meta = {
  name: 'kasandra-hand-s1-her-door-on-the-field',
  description: "Kasandra's hand, slice S1: her door on the Field with a planner over the desk acts (forward search, receding horizon, goals with evidence), touch-stop, put back, the pick turn and the 4B check; build, two reviews, fix",
  phases: [
    { title: 'Build', detail: 'one builder in its own worktree, from the judged plan' },
    { title: 'Review', detail: 'a safety reviewer and a planner-and-model reviewer' },
    { title: 'Fix', detail: 'the builder fixes what the reviews proved' },
  ],
}

const S = '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad'
const PY = S + '/work/venv/bin/python'
const REPO = '/home/user/Struthio'
const PLAN = S + '/work/hand_design/judge_hand-plan.md'
const MAPS = S + '/work/hand_design'
const MIRROR = S + '/work/hand_mirror'

const GOAL = `
Graphite (repository ${REPO}, branch head bbf033b: 0.8.2 plus Kasandra's look pass, which added her hologram in the left column
with states workbench/hologram.py, workbench/hologram_qt.py, and her column workbench/kasandra_column.py) is a PySide6 desktop
workspace. Her assistant is Kasandra (Stacy in the Graphite appearance; workbench/assistant_identity.named()). 0.8.2 gave the desk 40
named acts (workbench/desk_acts.py, desk_doers.py, desk_scene.py; the scene P01 in tools/campaign_lib/data/scenes/P01.json); her
door to them, door='her', is refused today.

The owner: "We keep building for Kasandra's hand" and "Keep working on the big things you're smart about like maths." A design
workflow mapped the code and a judge wrote the plan: READ ${PLAN} (PART 1 is the plan; PART 2 the owner page). The readers' maps
and both designs are beside it in ${MAPS}/ (read_desk-states.md, read_model-path.md, read_maths.md, design_planner-first.md,
design_model-in-loop.md) for reference. This workflow builds SLICE S1 ONLY ("Her door on the Field", the plan's section 10, S1),
with the decided elements of sections 1-6 that S1 needs. The owner accepted the plan's six defaults (Go ahead lets her do the moves
up to the next goal or change, and touching voids it; her changes keep the owner's identity, the journal says hers; DELETE waits
until it has an exact Undo; an ambiguous limit shows both; tolerances are the owner's; touching stops her, scrolling does not).
Connect HerHand.state_changed to her hologram's states (look at hologram.py for the state names: idle, working, waiting, done,
stopped or as named there): thinking/acting -> working, waits -> waiting, stopped -> stopped, finished -> done.
Owner rules: no keyboard key printed on screen; never name the line language on screen ("a line"); "Apps", never "Programs";
what always asks still asks; nothing is removed.
`

const RULES = `
HARD RULES:
- Tests only inside: cd <your worktree> && QT_QPA_PLATFORM=offscreen nice -n 10 unshare --pid --fork --mount-proc --kill-child ${PY} -B -m unittest tests_integrated.<module> (or tests.<module> for pure ones). Never run tools/check_*_ui.py. Never the whole suite at once. Run before (base) and after: test_desk_acts, test_desk_scenes, test_stacy_hand, test_writing_line, test_context_menu, test_kasandra, test_hologram, test_kasandra_column, test_release_check, test_campaign, test_local_brain or the brain modules you touch, and your new modules. A new test module goes into tools/check_hatch.py FOCUSED_MODULES.
- Scenes: P01 must still pass in all four runs; P02 and P03 as the plan says, in both appearances (GRAPHITE_APPEARANCE=kasandra and unset), through desk_scene and through the campaign: cd <a copy of your worktree> && GRAPHITE_APPEARANCE=... QT_QPA_PLATFORM=offscreen nice -n 10 unshare ... ${PY} -B tools/campaign.py run --set scenes --fixtures ${S}/work/campaign_fixtures --out <new folder under ${S}/work/hand_build/>.
- The 4B check (workbench/hand_model_checks.py) with ${S}/models/Qwen3.5-4B-Q4_K_M.gguf (and the 2B ${S}/models/Qwen3.5-2B-Q4_K_M.gguf for the record): run it only when "uptime" shows a 1-minute load under 1.5 (other work shares this 4-core machine; wait and retry up to 40 minutes, checking every few minutes); if the load never falls, report that and the orchestrator will run it. Never run two model processes at once.
- ${REPO} is read-only for you. Never push. Do not change workbench/version.py or write release notes.
- After any change: ${PY} -B tools/package_graphite.py --manifest-only, ${PY} -B tools/record_registry.py, the manifest again; seed_status 'VERIFIED_SOURCE_BINDINGS', release_integrity.verify 'VERIFIED'; stage every regenerated file (MANIFEST.json, project/stacy_seed/current/*, docs/GRAPHITE_0.1_REGISTRY.json). If a new module must be in workbench/stacy_foundation.py SEED_FILES, add it.
- Mirror every changed or added file to ${MIRROR}/<path>.
- Commit in your worktree (git status first; never .claude/). Message ends with:
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01SSUMdyhHQH2idKFXpgDCV8
- Each new module starts with a plain-words docstring; comments say why, briefly. Pure planning and goal code has no Qt import.
`

const BUILD = GOAL + `
You are the builder, in your OWN git worktree (your current directory). Build S1 exactly as the plan lists it (items 1-13), with
its tests table, the scenes P02 and P03, P01 unchanged, and the 4B check. Where the plan is wrong against the code, follow the code
and say so. Keep the planner deterministic and within its budgets (expansions, depth, time); measure plan time.
` + RULES + `
REPORT: worktree, branch, commit; each S1 item done (file:function); the act count and exports; tests before and after per module;
P01, P02, P03 results per run and appearance (and the campaign summary paths); the 4B check's numbers (each turn's seconds, prompt
and output tokens, exact or not), the 2B's for the record; plan times; what is not done or deviates, plainly.
`

const REVIEW = (who, built) => GOAL + `
A builder built S1. Their report:
---
${built}
---
The worktree named there is READ-ONLY for you; copy it (rsync -a --exclude .git) to ${S}/work/hand_review_${who}/tree and work
there, only inside QT_QPA_PLATFORM=offscreen nice -n 10 unshare --pid --fork --mount-proc --kill-child ${PY} ...; never run
tools/check_*_ui.py; do not load a model unless your part says so.
` + (who === 'safety' ? `You review SAFETY AND CONTROL. Try to break: can her door do anything outside a turn, an owner-only act,
a change act (refused in S1), a by= form, a row not on the lists; can she act at Ask first without the Go ahead, or after the
offer was voided by a touch; does a real press on the window stop her between presses and never halfway through a click, and does
a press on her card or a wheel not stop her; does Put my window back return exactly to the snapshot and never clear words in the
line that are not hers; does every act she does leave a journal line marked hers (OFFERED, STOPPED states) and is anything done
unseen; do the words fixes hold (no key printed: the Approve tip, the console's approval words; no "Programs"); is what always asks
still asking. Run P02 and P03 yourself in both appearances.` : `You review THE PLANNER, THE GOALS AND THE MODEL TURN. Check: the
operators' certain effects against the live window (rerun the conformance test and add your own sampled states); the forward search
is exact, deterministic (same input, same plan), within budgets, and its plans are minimal for the plan's cases (from Today a trace
of Bench = 2 acts; Rev A beside Rev B plus a trace of Bench jointly = 5; zoom first only when the sheet is not in sight); the finish
rule (evidence with the read digest, no popups at the final read); the progress measure and stall rule; the pick mode's schema,
validation and late fallback; prompt and output token limits. Then run the 4B check yourself ONLY if uptime's 1-minute load is under
1.5 (wait and retry up to 30 minutes), and say whether each turn met 60 s and the expected sets.`) + `
Report findings MOST SEVERE FIRST, each with evidence (command, output, file:line) and a concrete fix. Say what holds. Do not fix.
`

const FIX = (built, a, b) => GOAL + `
You built S1 in a git worktree. Your report:
---
${built}
---
The safety review:
---
${a}
---
The planner and model review:
---
${b}
---
Work in THAT SAME worktree (cd to the path in your report). Reproduce each proven finding, fix it, show the check passing; for one
you judge wrong, say why with evidence. Re-run the modules, the scenes and (if the load allows) the 4B check, rebuild seed and
manifest, commit (a new commit), keep the mirror.
` + RULES + `
REPORT: worktree, branch, final commit; per finding fixed or not; final tests per module; final scene runs; the 4B check's final numbers
or why it could not run; what is still not done.
`

phase('Build')
const built = await agent(BUILD, { label: 'build:her-door', phase: 'Build', isolation: 'worktree' })
if (!built) return { built: null }
phase('Review')
const [rA, rB] = await parallel([
  () => agent(REVIEW('safety', built), { label: 'review:safety', phase: 'Review' }),
  () => agent(REVIEW('planner', built), { label: 'review:planner', phase: 'Review' }),
])
phase('Fix')
const fixed = await agent(FIX(built, rA || '(no safety review)', rB || '(no planner review)'), { label: 'fix:her-door', phase: 'Fix' })
return { built, rA, rB, fixed }
