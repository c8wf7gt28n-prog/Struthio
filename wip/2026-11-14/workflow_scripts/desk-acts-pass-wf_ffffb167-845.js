export const meta = {
  name: 'desk-acts-pass',
  description: 'Kasandra drives the desk, foundation: map the window, her hand and the test side; design a registry of named desk acts with three doors; build it in a worktree; an adversarial review; fixes',
  phases: [
    { title: 'Understand', detail: 'three readers map the window controls, her hand and the model path, and the test and campaign side' },
    { title: 'Design', detail: 'one designer writes the plan from the three maps' },
    { title: 'Build', detail: 'one builder in its own worktree' },
    { title: 'Review', detail: 'one reader tries to break it' },
    { title: 'Fix', detail: 'the builder fixes what the review proved' },
  ],
}

const S = '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad'
const PY = S + '/work/venv/bin/python'
const MIRROR = S + '/work/desk_acts_mirror'
const REPO = '/home/user/Struthio'

const GOAL = `
Graphite is a local-first Python 3.13 / PySide6 desktop workspace (repository ${REPO}, read-only for readers). Its assistant
is called Kasandra in the Kasandra appearance and Stacy in the Graphite appearance (workbench/assistant_identity.named()).
The owner's direction for this pass (14 November 2026): "a pass that builds as much capabilities of Kasandra to control the
graphite interface ... eventually we're going to do that, and that opens up more testing options and simulating options".
Today her hand (workbench/stacy_hand.py, shell2.SlateFace.stage) can only change data through Kernel operations; nothing lets
anyone but a person drive the window (open the Field, select a sheet, open a right-click and choose a row, carry the line
panel, put words in the typing line, zoom, choose the appearance, read back what is open). The offscreen probes reach into
widgets directly.

The pass: a registry of named DESK ACTS, one per thing a person can do in the window, each with an argument schema, a mark
"navigates" (changes nothing: opens, selects, zooms, reads back) or "changes" (goes through her hand as Kernel operations do
today, with its card, trail entry and Undo; what always asks still asks), and the function that does it on the live window.
Three doors over one registry: (1) her model, LATER (the owner: "Then we will do Kasandra's hand after you feel we're
ready"): this pass only exports the acts as tool descriptions and the hand's rule for them, it does NOT offer them to the
model; (2) the owner: an act typed in the writing line; (3) tests and the campaign: scripts of acts instead of reaching into
widgets, and a first scene: the owner's "playable scene" in the After Hours 07 workspace (open a menu across the head; Then
over a CSV in Files: Keep rows where unit is mA, Count, Put it in the writing line; back to the Field; Trace 07 Bench
readings; a comparison where the data supports it), run by mouse-equivalent acts and by keyboard-equivalent acts, with
reduced motion too.
Owner rules that hold: the window never names the line language (staC): call it "a line"; no keyboard key is printed on screen
(keys still work); "Apps", never "Programs"; at rest the window shows names and pictures and the machinery is one move away
(so an act's name is not printed on rows at rest); nothing is removed to make things simple.
`

const READ_RULES = `
You are a reader. Do not edit anything under ${REPO}. Scratch only under ${S}/work/desk_read/. If you run code, only inside
"QT_QPA_PLATFORM=offscreen unshare --pid --fork --mount-proc --kill-child ${PY} -B ..." from a copy you make with
"git -C ${REPO} archive HEAD | tar -x -C <dir>"; never run tools/check_*_ui.py anywhere. Cite file:line for every claim.
Return a Markdown map (plain words, tables welcome), no preamble.
`

const R1 = GOAL + READ_RULES + `
YOUR PART: the window's controls. For every surface a person uses (the head: the menus across the top, Apps, the meters, the
equalizer; the left pane: Files/Machine/Settings trees and Trash; the centre: Home/Today, the Field and its faces, Files,
pages, rooms, the Compare room; the right pane: her column, hand, trail; the typing line and its five targets and expand; the
right-click (workbench/context_menu.py: ContextMenu, LinePanel, first_level, perform) ; the Field (workbench/field_qt.py,
field_page.py): select, zoom, show whole, the face, Trace/Doubt/Do/What if/Brief; appearance and glow (boss_theme,
boss_qt.choose_appearance, Rules menu)), list the actual Python call a desk act would make to do it on a live
WorkbenchWindow (attribute path from the window object, function, arguments), whether it changes data or only navigates,
what it shows afterwards that a read-back could report (widget, attribute), and any modal dialog it opens (an act must not
block on a dialog: say which ones would and how a scripted value could be passed). Also find how the offscreen probes drive
these today: read ${S}/tools/field/rc_shots.py, cascade_probe.py, mouse2_probe.py, look_probe.py, action_shots.py and the
harness ${S}/tools/field/nomodel.py. End with a proposed list of 30 to 40 acts (name, arguments, navigates/changes,
the call), grouped: go places, point, the right-click and the line panel, the typing line, look, read back.
`

const R2 = GOAL + READ_RULES + `
YOUR PART: her hand, the model's tool path and the line. Map: workbench/stacy_hand.py (the dial: Ask first / Do and show /
Free hand; hers(); why_asks; ALWAYS_ASKS; HERS_SHOW; UNDOES; takes_back); shell2.SlateFace (stage, her trail, Undo, cards,
show_hand); how the model is offered operations today (workbench/agent_operations.py DIRECT_OPERATIONS and validate,
local_brain/brain_link/model turn: where a tool list or operation catalogue is given to the model, its format), and the
Kernel's capability registry (engineering_kernel CAPABILITIES, scopes, schemas via engineering_cli.schemas, record_registry,
docs/GRAPHITE_0.1_REGISTRY.json): would a desk act be a Kernel operation (the Kernel runs without a window; the seed binds
registered operations) or a window-side registry, and what breaks either way (seed bindings, release check, registry
tests). The typing line: how text is run (workbench/typebar_qt.py, console_qt.py, shell2.to_console/ask; the "/op {json}"
form, the arrow, the five targets Kasandra/Stacy, Terminal, Search, Web, Log), and the cleanest place for a typed desk act
(a "/desk.x {...}" form? a word form?), with its echo and refusal. Receipts: where acts are recorded today (activity.record,
journal, her trail, work_trail) so that each desk act could leave one record. End with a recommendation: where the registry
lives, how the three doors attach, how her hand classifies acts (navigates = hers at Do and show? asks on Ask first?), and
what must not change.
`

const R3 = GOAL + READ_RULES + `
YOUR PART: the test and simulation side. Map: tests_integrated (which modules build a live offscreen WorkbenchWindow and how:
setUpModule fixtures, holds that keep processes and models from starting, the After Hours 07 restored workspace if any
test uses it), tools/check_hatch.py FOCUSED_MODULES and tools/check_release.py (what a new test module must do to be in the
release check), the campaign (tools/campaign.py, tools/campaign_lib/: cases, the anchor situations of the owner's spec
${S}/in/spec_docx/spec.txt, how a case runs, outcomes, the fixture workspace, whether it can or could run a window
offscreen), and the probe harness ${S}/tools/field/nomodel.py (how After Hours 07 is restored into a run there:
REHEARSAL_* variables, the workspace it builds). Then propose: (a) a scene format (a list of desk acts with expected
read-backs) and one runner usable from a test, from a probe and from the campaign; (b) the first scene, the owner's
"playable scene" in After Hours 07: open a menu across the head (Tools); right-click a CSV in Files, Then, Keep rows where
unit is mA, Count, Put it in the writing line; back to the Field; Trace 07 Bench readings; a revision comparison where the
data supports it (say which records support it); run once mouse-style and once keyboard-style, and with reduced motion;
(c) which campaign anchor situations could become scenes next, by number and title. Say what would need a real model and
must wait for the ThinkPad.
`

const DESIGN = (m1, m2, m3) => GOAL + `
Three readers mapped the code. Their maps:
=== WINDOW CONTROLS ===
${m1}
=== HER HAND, THE MODEL PATH, THE LINE ===
${m2}
=== TESTS, CAMPAIGN, SCENES ===
${m3}
===
You are the designer. Check any claim you rely on against the code (read-only; ${REPO}; cite file:line). Write ONE plan a
builder can follow in one session, in Markdown, with: (1) where the registry lives and why (window-side vs Kernel; seed and
release-check consequences); (2) the act table: 30 to 40 acts, each name, arguments (JSON schema), navigates/changes, the
exact call it makes, what its read-back reports, how a dialog it would open is avoided; (3) her hand's rule for acts
(navigates: hers at Do and show and at Free hand, asks on Ask first? changes: through the existing stage path) and the tool
descriptions exported for later (NOT offered to the model in this pass); (4) the typed form in the writing line, its echo,
refusal words (never naming the line language, never printing a key); (5) one record per act (where); (6) the scene format,
the runner, and the first scene (the playable scene in After Hours 07, mouse-style, keyboard-style, reduced motion);
(7) files and functions to add or change, marking which are seed inputs (workbench/stacy_foundation.py SEED_FILES) and the
rebuild needed; (8) tests with exact assertions (a new module must be added to tools/check_hatch.py FOCUSED_MODULES or the
release check fails); (9) what is NOT in this pass. Keep it buildable: prefer reusing existing functions; no new Kernel
operation unless clearly needed. Return the plan only.
`

const RULES = `
HARD RULES:
- Run tests only inside: cd <your worktree> && QT_QPA_PLATFORM=offscreen unshare --pid --fork --mount-proc --kill-child ${PY} -B -m unittest <module>. Never run any tools/check_*_ui.py script (not in the repo, not in a worktree). Never run the whole tests_integrated suite at once: run the modules you touch plus test_context_menu, test_stacy_hand, test_writing_line, test_kasandra, test_release_check, test_campaign.
- ${REPO} itself is read-only for you (another session works there). Never push.
- The window never names the line language (staC/stac): "a line". Never print a keyboard key or shortcut on screen. "Apps", never "Programs". The assistant is named through assistant_identity.named().
- If you edit a file listed in workbench/stacy_foundation.py SEED_FILES, or any source/doc file, finish with: ${PY} -B tools/package_graphite.py --manifest-only, then ${PY} -B tools/record_registry.py, then the manifest again (a stale seed refuses every line). Check workbench.stacy_foundation.seed_status('.')['state']=='VERIFIED_SOURCE_BINDINGS' and workbench.release_integrity.verify('.')['state']=='VERIFIED'; git status must show every regenerated file staged (MANIFEST.json, project/stacy_seed/current/*, docs/GRAPHITE_0.1_REGISTRY.json).
- A new test module goes into tools/check_hatch.py FOCUSED_MODULES.
- After each file you change, copy it to ${MIRROR}/<same relative path> (mkdir -p), generated files included.
- Commit in your worktree (git status first; never add .claude/). Message ends with the two lines
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01SSUMdyhHQH2idKFXpgDCV8
- Each new module starts with a plain-words docstring; comments say why, briefly.
`

const BUILD = (plan) => GOAL + `
You are the builder. You work in your OWN git worktree (your current directory). The designer's plan:
---
${plan}
---
Build it. Run the tests after each piece. Add the plan's tests. Run the first scene through the runner offscreen and report
what each act read back. If the plan is wrong against the code, follow the code and say so.
` + RULES + `
REPORT: worktree path, branch, commit; the acts built (name, navigates/changes); test results (command and result line) before
and after for each module you ran; the scene's run (each act and its read-back), mouse-style, keyboard-style, reduced motion;
what is not done or deviates from the plan, plainly.
`

const REVIEW = (plan, built) => GOAL + `
A builder built the desk acts from this plan:
---
${plan}
---
Their report:
---
${built}
---
The worktree named there is READ-ONLY for you, as is ${REPO}; the changed files are mirrored in ${MIRROR}. Copy the worktree
(cp -a, excluding .git) to ${S}/work/desk_review/tree and work there. Run only inside QT_QPA_PLATFORM=offscreen unshare --pid
--fork --mount-proc --kill-child ${PY} -B ...; never run tools/check_*_ui.py.
Try to break it: (1) safety: can any act change data or the session without going through her hand, or bypass what always
asks (a "navigates" act that in fact writes, deletes, runs a shell, sends, stops a job, or approves)? Can a typed act from the
line do more than the person could by hand? (2) blocking: does any act open a modal dialog or wait forever offscreen? (3)
read-back honesty: does each act's read-back report what the window really shows after it? (4) the scene: run it yourself,
mouse-style, keyboard-style, reduced motion, at 1366x768 and 1920x1200; (5) words: any act name, echo or refusal that names
the line language, prints a key, or says Programs; (6) the release: seed state, manifest verify, FOCUSED_MODULES,
test_release_check; (7) the existing tests the builder ran, run them again and compare. Report findings MOST SEVERE FIRST,
each with evidence (command, output, file:line) and a concrete fix. Say plainly what holds. Do not fix anything.
`

const FIXUP = (built, review) => `
You built Graphite's desk acts in a git worktree. Your report:
---
${built}
---
A reviewer attacked it:
---
${review}
---
Work in THAT SAME worktree (cd to the path in your report; do not create another). Reproduce each proven finding, fix it,
show the same check passing; for a finding you judge wrong, say why with evidence. Re-run the modules and the scene, rebuild
the seed and manifest, commit (a new commit), keep the mirror current.
` + RULES + `
REPORT: worktree path, branch, final commit; per finding fixed or not (file:function, evidence); final test results; the
scene's final run; what is still not done.
`

phase('Understand')
const maps = await parallel([
  () => agent(R1, { label: 'read:window', phase: 'Understand' }),
  () => agent(R2, { label: 'read:hand-and-line', phase: 'Understand' }),
  () => agent(R3, { label: 'read:tests-and-scenes', phase: 'Understand' }),
])
const [m1, m2, m3] = maps
if (!m1 || !m2 || !m3) return { maps, plan: null }
phase('Design')
const plan = await agent(DESIGN(m1, m2, m3), { label: 'design:desk-acts', phase: 'Design' })
if (!plan) return { maps, plan: null }
phase('Build')
const built = await agent(BUILD(plan), { label: 'build:desk-acts', phase: 'Build', isolation: 'worktree' })
if (!built) return { maps, plan, built: null }
phase('Review')
const review = await agent(REVIEW(plan, built), { label: 'review:desk-acts', phase: 'Review' })
if (!review) return { maps, plan, built, review: null }
phase('Fix')
const fixed = await agent(FIXUP(built, review), { label: 'fix:desk-acts', phase: 'Fix' })
return { maps, plan, built, review, fixed }
