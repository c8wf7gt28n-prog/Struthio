export const meta = {
  name: 'graphite-086-kas-mind',
  description: '0.8.6 Kas\'s mind without a model, one phase of its build per run (args.phase): slices built, reviewed where they touch the logic core or safety, and fixed',
  phases: [
    { title: 'Build', detail: 'one builder per slice, each in its own worktree, leaving a patch' },
    { title: 'Review', detail: 'an independent reviewer applies the patch to a fresh copy and tries to break it' },
    { title: 'Fix', detail: 'the must-fix findings, then the patch is rewritten' },
  ],
}

const REPO = '/home/user/Struthio'
const S = '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad'
const OUT = S + '/work/b086'
const PY = S + '/work/venv/bin/python'
const M = REPO + '/wip/2026-11-14/tests_measure'

const RULES = `PROJECT. Graphite is a local-first PySide6 desktop with an assistant, Kasandra (Kas). Version 0.8.5 ("Maths in lines") is released; we are building 0.8.6 "Kas's mind, no model", whose full design is ${REPO}/wip/2026-11-20_kas_mind/DESIGN_0.8.6_kas_mind.md (read its sections 1 to 6 as your task needs; section 6 holds the slices, lanes, files each lane owns, and the exact tests). The order of releases is in ${REPO}/wip/BUILD_STATE.md ("The owner's decisions of 20 Nov 2026"); standing rules are in the same file ("Rules that never bend"). 0.8.5 is merged and released in the commit your worktree started from (the one maths core with solve, range, check, tolerances and receipts; money and dates; Rail Demo; the tiered runner tools/run_tiers.py; the sweeps tools/name_sweep.py). Earlier slices of 0.8.6 are merged too where this run's phase comes after them. The open questions of the design (its section 8) are taken at their DEFAULTS: (1) on a revision disagreement she asks once per desk, the first button 'for this desk, the current revision applies', a standing word only if pressed; (2) the logic core gets exact vectors and one independent review; (3) Home Demo may carry an invented statute marked INVENTED: NOT THE LAW OF ANY PLACE on every page; (4) nothing medicine-specific is built beyond the fixed decline; (5) with no model she may answer a READ reached by elimination, showing the elimination and naming the other sense, never a change.

HARD RULES.
- Never edit, stage or commit anything in ${REPO} itself. Builders work only in the worktree they were started in (your current directory). Do NOT commit. Do NOT touch wip/, the version number, release notes, MANIFEST.json or project/stacy_seed/current/ in what you hand over.
- Tests and the app run ONLY on a throwaway COPY of your tree under ${OUT}/<your key>/copy (make it with: git ls-files -z --cached --others --exclude-standard | grep -z -v -E '^(wip/|\\.claude/)' | xargs -0 cp --parents -t <copy>). In the copy, first make the seed current: ${PY} tools/package_graphite.py --manifest-only ; ${PY} tools/record_registry.py ; ${PY} tools/package_graphite.py --manifest-only ; ${PY} tools/record_registry.py --check (with QT_QPA_PLATFORM=offscreen). Re-copy and redo this after every source change you want to test.
- Every test or app run: nice -n 19 unshare --pid --fork --mount-proc --kill-child env HOME=$(mktemp -d) QT_QPA_PLATFORM=offscreen ${PY} -B -m unittest -v tests_integrated.<module>   (one module at a time; at most two processes at once on this 4-core machine, and another builder is working beside you). Never run tools/check_*_ui.py in a worktree or in ${REPO}; only in a copy. Keep the disk tidy: delete copies you no longer need; never keep more than two copies of the tree.
- On screen: "Apps", never "Programs"; no keyboard shortcut printed in any on-screen text; a pipeline is called "a line" (the internal name staC never shows); "Lain" is never used as a name; her name is Kasandra in every look; every colour that carries meaning also has a word or a shape. The owner's personal details never appear in code, tests, data or comments. The owner's real workspace ("After Hours 07") and its numbers must never be copied into the repository; tests use Rail Demo or their own invented data.
- Write code the way the surrounding code is written. Every behaviour you add or fix gets a test that fails before and passes after; say which. A test asserts behaviour, not wording, unless the words are the point.
- Zero failing tests is the rule: the modules you touch, and every module that imports what you touched, must pass in the default look and with GRAPHITE_APPEARANCE=kasandra.
- Registrations in workbench/engineering_kernel.py and engineering_cli.py, the registry record and the seed are shared: add your operations in your own block, clearly commented with your slice name, and regenerate docs/GRAPHITE_0.1_REGISTRY.json with tools/record_registry.py in your copy, copying it back; expect another slice's builder to do the same beside you.
- A new test module must be listed in tools/check_hatch.py FOCUSED_MODULES (tests_integrated/test_release_check.py checks that). Other builders add lines there too: add yours on its own line, away from the others, and say so in your report.
- When done, write your patch: in your worktree run  git add -A -N . ; git diff HEAD -- . ':(exclude)MANIFEST.json' ':(exclude)project/stacy_seed/current' ':(exclude)wip' > ${OUT}/<key>.patch  and check it is not empty and applies to a clean checkout (git apply --check in a fresh copy).
- SAVE EARLY AND OFTEN. This run can be cut off at any moment by a usage limit. After every milestone rewrite your patch file with the command above and update a short note ${OUT}/<key>.progress.md saying what is done, what is half done and what is next, so an interrupted run leaves usable work behind. If ${OUT}/<key>.progress.md and ${OUT}/<key>.patch already exist when you start, an earlier attempt was cut off: read the note, apply the patch in your worktree if it is sound, and carry on from there.
- ECONOMY (binding). The usage allowance is tight and this run can be cut off at any moment. Work in few, large steps: put a batch of commands in a script file and run it once, blocking, with a long timeout (up to 9 minutes; a longer batch runs with run_in_background and you wait for its completion notice). Never loop on sleep, never poll. Never print whole test output into your context: send it to a log file and print only the lines matching '^Ran |^OK|^FAILED|^ERROR:|^FAIL:' and, for a failure, the last 15 lines of its traceback. Read files in the ranges you need; read a patch once. Do not run the whole suite unless your task says so: the coordinator runs it in both looks at merge.
- RESULT FILE. When you finish, before you return, write your whole return value as JSON to the result file named in your instructions. If that result file already exists when you start, your job was already done in an earlier run: check the patch file is there, then return the content of the result file at once, without redoing anything.
- Report honestly: what you built, what you tested with exact results, what you did not do, and any decision you took where the plan was silent (give the reason). Do not claim anything ran on the owner's ThinkPad.`

const BUILD = {
  type: 'object',
  properties: {
    summary: { type: 'string' },
    patch_path: { type: 'string' },
    files_changed: { type: 'array', items: { type: 'string' } },
    tests: { type: 'array', items: { type: 'object', properties: { module: { type: 'string' }, look: { type: 'string' }, ran: { type: 'number' }, failed: { type: 'number' }, note: { type: 'string' } }, required: ['module', 'look', 'ran', 'failed'] } },
    new_tests: { type: 'array', items: { type: 'string' }, description: 'test ids added, each with what it pins' },
    numbers: { type: 'array', items: { type: 'string' }, description: 'measured numbers the release notes should carry (times, counts, rates), each with how it was measured' },
    decisions: { type: 'array', items: { type: 'string' } },
    not_done: { type: 'array', items: { type: 'string' } },
    release_note: { type: 'string', description: 'two to five plain sentences for the 0.8.4 release notes, in the owner\'s terms' },
  },
  required: ['summary', 'patch_path', 'files_changed', 'tests', 'new_tests', 'numbers', 'decisions', 'not_done', 'release_note'],
}
const REVIEW = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['accept', 'accept_after_fixes', 'reject'] },
    must_fix: { type: 'array', items: { type: 'object', properties: { what: { type: 'string' }, where: { type: 'string' }, how_to_reproduce: { type: 'string' } }, required: ['what', 'where', 'how_to_reproduce'] } },
    should_fix: { type: 'array', items: { type: 'string' } },
    checked: { type: 'array', items: { type: 'string' }, description: 'what you ran and saw, with results' },
    summary: { type: 'string' },
  },
  required: ['verdict', 'must_fix', 'should_fix', 'checked', 'summary'],
}

const ITEMS = [
  { key: 'S0', review: true, task: `SLICE S0 OF 0.8.6: THE HALF-BUILD OF HER DOOR, MERGED (lane A). Read the design ${REPO}/wip/2026-11-20_kas_mind/DESIGN_0.8.6_kas_mind.md section 6.2 'S0' and section 6.1 (what lane A owns). The saved half-build is ${REPO}/wip/2026-11-14/hand_s1/hand_s1_unfinished.patch (with its notes in ${REPO}/wip/2026-11-14/hand_s1/): rebase it onto this tree (git apply -3, resolve conflicts keeping today's code where the half-build is older), run test_desk_planner and test_her_hand to the end, fix what fails, add test_planner_apps.py exactly as S0 says (an invented two-act App table: plans 'F is exported' in exactly 2 acts; refuses 'F is printed' with the design's words). Scenes P01 to P03 pass in both looks with P01 unchanged. The door's mechanics come as built (they are finished in 0.8.8); every safety rule in the half-build (touch stops her, what always asks, the trail, Undo) must hold and be tested. The 4B GOAL check: run it if the 4B model under ${S}/models/ starts within your budget (three requests, each under 60 s and 1,200 prompt tokens, all exact); if the machine is too loaded, say so and give the numbers you got.` },
  { key: 'S2', review: true, task: `SLICE S2 OF 0.8.6: DATES DELTA AND HOME DEMO (lane C). Read the design ${REPO}/wip/2026-11-20_kas_mind/DESIGN_0.8.6_kas_mind.md section 6.2 'S2', section 2 (the legal part and the money part), section 3 where it describes Home Demo, and section 5 (the legal and medical line). 0.8.5's money and dates DID land (workbench/math_dates.py, math_money.py and their tests): build the dates delta on them (days after an event with the roll from a quoted counting clause, holidays, an uncertain event, break-even, as_of with origin CLOCK and REVIEW_REQUIRED when the frozen clock moves, the property tests), and build Home Demo (workbench/home_demo.py: an invented household and an invented tenancy act, 'Demoland Tenancy Act', INVENTED: NOT THE LAW OF ANY PLACE on every page; built by code through the Kernel's own operations like workbench/rail_demo.py; deterministic; with the 41-row bank sheet and the groceries and household vectors exactly as S2 lists). Tests test_mind_dates.py and test_home_demo.py exactly as S2 lists, each failing before your code exists.` },
  { key: 'S1', review: true, task: `SLICE S1 OF 0.8.6: THE EXACT GOAL FACE (lane B), and mind_types.py FIRST. Read the design ${REPO}/wip/2026-11-20_kas_mind/DESIGN_0.8.6_kas_mind.md section 3 (the architecture: the open point, the pieces, mind_types) and section 6.2 'S1'. First write workbench/mind_types.py (OpenPoint, Way, Leaf, Judgement, Budget) exactly as section 3 defines them, small and frozen: later slices read it. Then math_zones.py, the math_answers stages room and settle, bindings_from_cells, and the goals relation form with ledger.goal/1 and the goals.* operations (S0's half-build is merged in your starting commit, with its goals.py: build on it). Tests test_math_goals.py exactly as S1 lists, with every vector exact; no float (AST scan); model_calls 0; the banned-word scan on the room and zone templates.` },
  { key: 'L', review: false, task: `THE OWNER'S HEAD AND FOOTER LAYOUT, HIS STRUTHIO ICON, A RADICAL EQUALIZER AND COOL METERS (0.8.6, window only). The owner's directions and the approved mockups are recorded in ${REPO}/wip/BUILD_STATE.md under 'Asked by the owner, to do' (read every entry dated 20 Nov from 07:50 to 08:45) and the pictures are in ${REPO}/wip/2026-11-20_head_footer_mockup/ (mock3_kasandra.png and mock3_graphite.png: the layout he approved; equalizer/ and meters/: the styles; render.py and meters.py there are the picture code, use them only as a reference for shapes and colours). Build, in BOTH looks: (1) the head: the 16-bar equalizer moves to the upper left, over the left column; the menus (Work ... Guide) start exactly at the middle column's left edge and follow it when the column is resized; the Apps button upper right shows the owner's Struthio icon (his picture: ${S}/in/struthio_icon/struthio.png; make its white background transparent, crop it, draw it crisp at head height, put it in branding/struthio/ with a note in RIGHTS.md that it is the owner's art like his other pictures; the button keeps its name 'Apps' for screen readers and its tip; the kp logo stays as the window icon and in the Guide). (2) the equalizer in style D, 'neon tubes over a scope': with the room upper left, one bar per processor thread (up to 16, as many as the machine has; more than 16 averaged in equal groups) beside the kernel, memory, disks, network and graphics pairs; glowing rounded tubes in the look's colours, floating peak dots that sink, a faint grid floor, and behind them a glowing trace of all activity over the last two minutes. Keep every rule of workbench/equalizer_qt.py's docstring (every height means one thing; fixed scales; a missing source rests and the card says so; near the limit is its own colour AND said in words on the card; reduce motion holds it still) and keep it cheap: measure its paint time and its share of a core and report them (budget: under 1% of a core at rest, under 2% when everything moves). (3) the footer: the prompt box starts at the middle column's left edge; then the room button (Line / Half / Tall); then send, cyan in the Kasandra look (orange stays in the Graphite look), whose right edge is exactly the middle column's right edge; the chooser (Kasandra, Terminal, Search, Web, Log) stays under the left column; the four meters CPU, GPU, RAM, TXT are centred and evenly spaced under the right column, in style H, 'a ring with a minute of history': a glowing ring with the number inside and a small trace of the last minute ending in a bright dot; a meter with no reading stays honestly dim with its dash and 'no reading'; each meter is still a door (a click opens the same card). Take frames in both looks at 1920x1200 and 1366x768 of the whole window, read them yourself against the mockups, and save them under ${OUT}/L/frames/. Run every window test module that touches the head, the footer, the equalizer, the meters, the writing line and the Apps button, in both looks, and the window checks that do (tools/check_*_ui.py on a copy).` },
  { key: 'S3', review: true, task: `SLICE S3 OF 0.8.6: YOUR WORD AND HER REASONS (lane B). Read the design ${REPO}/wip/2026-11-20_kas_mind/DESIGN_0.8.6_kas_mind.md sections 2.2, 2.3, 3.3 (ledger.word/1) and 6.2 'S3'. Build your_word.py (one family of the owner's words, always asked at every dial setting; her proposals write nothing), reasons.py (the reasons graph and Why, four-valued through workbench/stac/evidence.py, the proof's edges lit on the Field), 'Rests on' and 'Without it', and the panel in her column if section 6.2 places it in this slice. Tests test_your_word.py and test_reasons.py exactly as S3 lists (Why on Rail Demo; rests on and without it; your word; the same answer every time with local_brain unimportable; budgets and the reason_graph oracle).` },
  { key: 'S4', review: true, task: `SLICE S4 OF 0.8.6: HER DICTIONARY (lane A). Read the design ${REPO}/wip/2026-11-20_kas_mind/DESIGN_0.8.6_kas_mind.md sections 2.1, 3.4 (how a request flows), 4 (how the model is used) and 6.2 'S4'. Build reading.py (understanding the owner's words from the desk's own vocabulary with no model) and what S4 needs around it. Tests test_reading.py exactly as S4 lists, the metamorphic tests, the authority test, the decline test, and the speed test (p99 of reading at most 20 ms here). The everyday score's request files under tests_integrated/data/everyday/ belong to S8; a SEALED set must be written by someone who does not build the dictionary: do NOT write or read a sealed set.` },
  { key: 'S5', review: true, task: `SLICE S5 OF 0.8.6: EITHER WAY AND WHAT WOULD SETTLE IT (lane B). Read the design ${REPO}/wip/2026-11-20_kas_mind/DESIGN_0.8.6_kas_mind.md sections 2.4, 2.5, 3.1 and 6.2 'S5'. Build either_way.py and settle.py on mind_types.py, reasons.py and the maths core. Tests test_either_way.py and test_settle.py exactly as S5 lists, including the property tests against brute force and the B2 test (a fake brain that fails if called is never called when exactly one decisive leaf is open).` },
  { key: 'S6', review: true, task: `SLICE S6 OF 0.8.6: PINNED QUOTES AND RULE CARDS (lane C). Read the design ${REPO}/wip/2026-11-20_kas_mind/DESIGN_0.8.6_kas_mind.md sections 2.7, 2.8, 5 (the legal line) and 6.2 'S6'. Build quotes.py (pinned quotes: exact words, page, region, file fingerprint; current / moved / gone across revisions) and rules.py (rule cards: needs, unless, gives, four-valued, never the fallacies the design lists), and mind_words.py with its banned-word scan and footers. Tests test_quotes.py, test_rules.py, test_no_fallacies.py (all 256 combinations against a table written before the code) and test_mind_words.py exactly as S6 lists. rules.set and quotes.rebind are caught by ALWAYS_ASKS at all three dial settings; a rule without a quote or row is refused.` },
  { key: 'S7', review: true, task: `SLICE S7 OF 0.8.6: THE BRIEF, THE CHECKER, THE PHRASEBOOK AND THE BUTTONS (lane A). Read the design ${REPO}/wip/2026-11-20_kas_mind/DESIGN_0.8.6_kas_mind.md sections 2.9, 2.10, 4 and 6.2 'S7'. Build brief.py, answer_check.py (including the WORDS check and the page check), phrases.py (the visible phrasebook: kept only from the owner's explicit keep; a phrase never authorises a change; the kit cutter excludes phrasebook rows) and the buttons that stand in for the model when none is loaded. Tests test_brief.py, test_answer_check.py (replaying the half-build's recorded 2B and 4B answers), test_phrases.py and the button tests exactly as S7 lists. Also test_mind_no_model.py (every 0.8.6 read identical with local_brain unimportable) and the Guide page 'An evening with Kas's mind' if lane C has not written it: check docs/ first.` },
  { key: 'R', review: false, task: `IF THERE IS ROOM IN 0.8.6 (the design ${REPO}/wip/2026-11-20_kas_mind/DESIGN_0.8.6_kas_mind.md section 6.2, 'If there is room', items 1 and 2 only): 'What this change did' (recheck_order.py, the read side only, with its 300 mA vector test) and 'Where does my desk say it' (places.py over the existing FTS5 search, with its Home Demo top-3 test). Build item 1 first; build item 2 only if item 1 is finished and green. Window parts get only the safety tests.` },
  { key: 'S8', review: false, task: `SLICE S8 OF 0.8.6: THE EVERYDAY SCORE AND THE I05 MEASUREMENT (lane A, last). Read the design ${REPO}/wip/2026-11-20_kas_mind/DESIGN_0.8.6_kas_mind.md sections 6.3 and 6.4 IN FULL: their predictions are written and must not be changed. Build tests_integrated/data/everyday/ (the open set) and everyday_score.py (tier 0; fails the build if any reading is wrong with no model; a planted fault must fail it), and the I05 arms B3 and N beside the specification's A, B1, B2 and B2@4096 (i05_arms.py). The SEALED sets (20 more requests plus one more phrasing of each open request; and the fourth I05 case D) must be written by a separate agent that does not build the dictionary or the deduction rules, and committed as a sha256 before the run: write a short instruction file for that agent at ${OUT}/S8/sealed_brief.md and STOP before writing them yourself; report that they are pending, and run everything that does not need them. Run the open score and the I05 arms that the machine can finish within your budget with the 4B (the full run takes hours: run at most one repeat per arm here and say so), report every measured number against its prediction honestly, and pack the I05 kit for the ThinkPad.` },
]

const PHASES = { 1: ['S0', 'S2'], 2: ['S1', 'L'], 3: ['S3', 'S4'], 4: ['S5', 'S6'], 5: ['S7', 'R'], 6: ['S8'] }

const F = (it, role) => `${OUT}/${it.key}.${role}.result.json`

const buildPrompt = it => `${RULES}

YOU ARE THE BUILDER of item "${it.key}". Your throwaway area: ${OUT}/${it.key}/ . Your patch goes to ${OUT}/${it.key}.patch , your notes to ${OUT}/${it.key}.progress.md , your result file is ${F(it, 'build')} .

YOUR TASK.
${it.task}`

const reviewPrompt = it => `${RULES}

YOU ARE THE INDEPENDENT REVIEWER of item "${it.key}". You did not build it; your job is to find what is wrong with it before it is merged. You may not edit a worktree or ${REPO}; work in ${OUT}/${it.key}/review/ only (delete your copy when you are done). Your notes file is ${OUT}/${it.key}.review.md , your result file is ${F(it, 'review')} .
THE PATCH: ${OUT}/${it.key}.patch . THE BUILDER'S NOTES AND REPORT: ${OUT}/${it.key}.progress.md and ${F(it, 'build')} (do not trust them; verify).

THE TASK THE BUILDER WAS GIVEN:
${it.task}

DO THIS:
1. Make a fresh copy of the main checkout's tracked tree (cd ${REPO} && git ls-files -z | grep -z -v -E '^(wip/|\\.claude/)' | xargs -0 cp --parents -t ${OUT}/${it.key}/review/copy), apply the patch there (git apply or patch -p1), make the seed current, and run the new and changed test modules plus the modules that import a changed file, in the default look and with GRAPHITE_APPEARANCE=kasandra. Report exact counts.
2. Read the whole patch once. Look for: behaviour asserted but not really tested (take two of the new tests, revert the piece each guards in your copy, see them fail); a number in the report that you cannot reproduce; house-rule breaks in any on-screen string; the owner's real data or name; silent fallbacks; anything that changes what the owner sees without being asked; dead code; files that should not be in the patch; anything that would ship in the kit and should not.
3. Try to break it with inputs the builder did not think of.
4. Think about what a picture or a test cannot show: timing, a slow disk, a damaged file, a restart in the middle.
Be proportionate: spend your effort where a mistake would cost the owner most. Return must_fix only for real defects, each with a way to reproduce it; should_fix for the rest.`

const fixPrompt = (it, r) => `${RULES}

YOU ARE FINISHING item "${it.key}" after an independent review. You are in a fresh worktree at the same starting commit: first apply the existing patch (git apply ${OUT}/${it.key}.patch), then fix every must_fix finding below and the should_fix findings that are cheap and clearly right, re-test the modules concerned in both looks, rewrite ${OUT}/${it.key}.patch from your worktree (same command as before) and append what you did to ${OUT}/${it.key}.progress.md . Your notes file while working is ${OUT}/${it.key}.fix.md , your result file is ${F(it, 'fix')} . If you disagree with a finding, say why and leave the code; do not paper over it.

THE TASK:
${it.task}

THE REVIEW:
${JSON.stringify(r, null, 1)}`

const chain = async it => {
  const b = await agent(buildPrompt(it), { label: `build:${it.key}`, phase: 'Build', schema: BUILD, isolation: 'worktree' })
  if (!b) return { key: it.key, failed: 'the build did not finish' }
  if (it.review === false) return { key: it.key, verdict: 'not reviewed (by plan)', build: b.summary }
  const r = await agent(reviewPrompt(it), { label: `review:${it.key}`, phase: 'Review', schema: REVIEW })
  if (!r) return { key: it.key, failed: 'the review did not finish' }
  const base = { key: it.key, verdict: r.verdict, must_fix: r.must_fix.length, review: r.summary }
  if (r.must_fix.length === 0) return { ...base, fix: null }
  const f = await agent(fixPrompt(it, r), { label: `fix:${it.key}`, phase: 'Fix', schema: BUILD, isolation: 'worktree' })
  return { ...base, fix: f ? f.summary : 'the fix did not finish' }
}
// One phase per run (args.phase); the coordinator merges each phase into the main checkout before the next.
const by = k => ITEMS.find(i => i.key === k)
const keys = PHASES[(args && args.phase) || 1]
log(`phase ${(args && args.phase) || 1}: ${keys.join(', ')}`)
const lanes = await parallel(keys.map(k => () => chain(by(k))))
const done = lanes.filter(Boolean)
log(`finished: ${done.map(d => d.key + (d.failed ? ' NOT FINISHED' : d.fix ? ' fixed' : ' clean')).join(', ')}`)
return { items: done, files: `${OUT}/<key>.patch, .progress.md, .review.md, .build.result.json, .review.result.json, .fix.result.json` }
