export const meta = {
  name: 'graphite-084-part-b',
  description: '0.8.4 part B: window checks retired or ported, blind-spot tests and the planted bugs rerun, the tiered runner, the look leftovers and colour-vision check, two session leftovers; each built, independently reviewed, fixed',
  phases: [
    { title: 'Build', detail: 'one builder per item, each in its own worktree, leaving a patch' },
    { title: 'Review', detail: 'an independent reviewer applies the patch to a fresh copy and tries to break it' },
    { title: 'Fix', detail: 'the must-fix findings, then the patch is rewritten' },
  ],
}

const REPO = '/home/user/Struthio'
const S = '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad'
const OUT = S + '/work/b084b'
const PY = S + '/work/venv/bin/python'
const M = REPO + '/wip/2026-11-14/tests_measure'

const RULES = `PROJECT. Graphite is a local-first PySide6 desktop with an assistant, Kasandra (Kas). Version 0.8.3; we are building 0.8.4 "Tests you can believe". The plan is ${REPO}/wip/2026-11-14/ROAD_REVISED_2026-11-19.md; the release is defined in ${REPO}/wip/2026-11-14/SPEC_0.8.3_to_1.0.md (search "### 0.8.4" and "The rules for keeping or retiring a test"); standing rules are in ${REPO}/wip/BUILD_STATE.md ("Rules that never bend"). Part A of 0.8.4 is already merged in the commit your worktree started from: an invented workspace kept in the program (workbench/rail_demo.py, "Rail Demo"), three start-up faults fixed, one name on screen (Kasandra in every look), the seven line bugs fixed. The suite is green there in both looks.

HARD RULES.
- Never edit, stage or commit anything in ${REPO} itself. Builders work only in the worktree they were started in (your current directory). Do NOT commit. Do NOT touch wip/, the version number, release notes, MANIFEST.json or project/stacy_seed/current/ in what you hand over.
- Tests and the app run ONLY on a throwaway COPY of your tree under ${OUT}/<your key>/copy (make it with: git ls-files -z --cached --others --exclude-standard | grep -z -v -E '^(wip/|\\.claude/)' | xargs -0 cp --parents -t <copy>). In the copy, first make the seed current: ${PY} tools/package_graphite.py --manifest-only ; ${PY} tools/record_registry.py ; ${PY} tools/package_graphite.py --manifest-only ; ${PY} tools/record_registry.py --check (with QT_QPA_PLATFORM=offscreen). Re-copy and redo this after every source change you want to test.
- Every test or app run: nice -n 19 unshare --pid --fork --mount-proc --kill-child env HOME=$(mktemp -d) QT_QPA_PLATFORM=offscreen ${PY} -B -m unittest -v tests_integrated.<module>   (one module at a time; at most two processes at once on this 4-core machine, and another builder is working beside you). Never run tools/check_*_ui.py in a worktree or in ${REPO}; only in a copy. Keep the disk tidy: delete copies you no longer need; never keep more than two copies of the tree.
- On screen: "Apps", never "Programs"; no keyboard shortcut printed in any on-screen text; a pipeline is called "a line" (the internal name staC never shows); "Lain" is never used as a name; her name is Kasandra in every look; every colour that carries meaning also has a word or a shape. The owner's personal details never appear in code, tests, data or comments. The owner's real workspace ("After Hours 07") and its numbers must never be copied into the repository; tests use Rail Demo or their own invented data.
- Write code the way the surrounding code is written. Every behaviour you add or fix gets a test that fails before and passes after; say which. A test asserts behaviour, not wording, unless the words are the point.
- Zero failing tests is the rule: the modules you touch, and every module that imports what you touched, must pass in the default look and with GRAPHITE_APPEARANCE=kasandra.
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
  {
    key: 'checks',
    task: `THE WINDOW-CHECK SCRIPTS: RETIRE OR FOLD SEVEN, PORT THE REST, so that every tools/check_*_ui.py that remains passes in both looks and none is an orphan.
Read ${M}/the-failing.md (sections "The 10 failing gate scripts", "The 12 scripts the gate does not run", "Defects and patches"). The written ports are ${M}/fix_patches/patches/apply_clean_ports.py (read it: each edit has its reason) and ui_checks_ported.diff. Already applied in the tree: the tools/ui_fit.py fix, the workbench/resource_control.py fix, and the check_continue_ui port. Everything else is still to do. The scripts have moved since those patches were written (part A changed names on screen), so apply each port by hand and verify, do not trust line numbers.
1. RETIRE seven gate scripts: check_desk_ui, check_frame_ui, check_hatch_ui, check_head_ui, check_graphite_ui, check_rename_ui, check_paper_ui. Before deleting each, verify the "covered by" claim in the-failing.md by reading the covering test; where a step is covered by nothing and still describes today's desk, fold it into an existing test module or into check_finder_ui (the-failing.md names two such steps from check_frame_ui: menus fold before clipping across 1040 to 1400 px; one pane width through sizes and a drag). Remove every reference to a retired script (tools/check_hatch.py UI_CHECKS and its capture-dir and description maps, docs, test docstrings that name the script). Write the reason for each retirement in docs/ where the checks are described (find the page; if none, add a short docs/WINDOW_CHECKS.md).
2. PORT the others: check_machine_ui, check_cabinet_ui, check_navigation_ui, check_presentation_settings_ui, check_memory_cabinet_ui, check_memory_settings_ui, check_model_settings_ui, check_return_thread_ui, check_settings_ui, check_cabinet_actions_ui, check_settings_02_ui.
3. THE DEAD TOGGLE: "Pleasantries in script" (workbench/shell2.py, menus2.py '@pleasantries') writes a setting nothing reads, which breaks the rule "a control is lit only when a press would do something". Remove the action and its menu entry; keep reading an old saved setting harmless; a test.
4. THE GATE: every remaining check_*_ui.py is either in the gate's list (tools/check_hatch.py UI_CHECKS) or in a second, named list of checks run on demand, with a one-line reason. Add a test to tests_integrated/test_release_check.py that fails when a tools/check_*_ui.py file is in neither list, or a list names a file that does not exist.
5. RUN every remaining check script on a copy, in the default look and with GRAPHITE_APPEARANCE=kasandra, the way the gate runs them (read tools/check_hatch.py for the environment it sets). Report a table: script, look, pass or fail, seconds. All must pass; a script that cannot pass in the Kasandra look for a reason that is not a defect says so in the on-demand list and in your report. Known already: tools/check_context_menu_ui.py stops at its step 09 on the main tree (seen by part A's reviewer): find out whether the script or the program is wrong and fix the right one.`,
  },
  {
    key: 'guards',
    task: `TESTS FOR THE BLIND SPOTS, AND THE PLANTED BUGS RUN AGAIN. Read ${M}/mutants.md (all of it) and the spec's rules for keeping or retiring a test. At 0.8.2, 136 planted bugs were run: 70 caught by a behaviour test (53.4%), 18 only by the seed's source digest, 61 gaps (44 real, 9 boundary, 8 drawing only). The scripts, the sample and every verdict are in ${M}/raw.tar.gz under mutants/ (untar into ${OUT}/guards/mutants; scripts/mutator.py, run_mutants.py, runmod.py, mutlib.py; sample.json; kill_matrix.json lists every planted bug with file, line, old and new text). The code has moved since: locate each planted bug by its old text and function, not its line number.
1. WRITE BEHAVIOUR TESTS for the real gaps, the guarding code first. "Guarding code" is the code that protects the owner: the Kernel's scopes and record paths (workbench/engineering_kernel.py, record_io.py), her hand's rules and what always asks (workbench/stacy_hand.py, desk_acts.py, desk_doers.py), the memory and resource rules (resource_control.py, local_brain.py, memory_settings.py, model_settings.py), change sets and undo (change_sets.py), continuing work (continuing_work.py), the seed and release integrity (stacy_foundation.py, release_integrity.py, tools/check_release.py, tools/check_hatch.py). Then the rest of the 44 (the Field: field_ripple, field_doubt, field_page; files_service; context_menu "Compare with Rev"; rooms; idle display; images_plus; evidence_compiler). Two line gaps (typed_pipeline.py "add loses every operator", "+ takes the precedence of *") may already be caught by part A's tests_integrated/test_line_rules.py: check before writing. Put tests in the existing module for that code where there is one; new modules only where none fits. Each test must assert the behaviour (what the owner would lose), never a line of source.
2. THE DIGEST RULE: "No test may pass or fail because of the source digest alone." Find how a stale seed digest makes whole GUI modules fail (mutants.md "digest kills"), and make sure there is exactly one clear test whose job is "the seed is current" (test_project_desk has one). Do not weaken the program's own refusal to run on a seed that does not match; this is about tests saying why they fail. If decoupling the GUI modules from the digest is more than a small change, describe it in not_done instead of doing it.
3. RUN THE PLANTED BUGS AGAIN against the new suite: every former gap in the guarding code first (plant it, make the seed current the way the scripts do or bypass the digest as the scripts did, run only the test modules that cover that file), then as many of the other gaps as time allows. Budget about forty minutes of machine time, two processes at most. Report: the catch rate by behaviour in the guarding code before and after (the target is 75% or more; say exactly which files you counted and the counts), the overall rate before and after, and every gap still open with its file and what it would take.
4. Keep the rerun repeatable: put the scripts needed to plant and run a named list of bugs under tools/planted_bugs/ (small, documented, no absolute paths), with the list of planted bugs as a data file, so each later release can report the number. Not part of the shipped program: check how tools/package_graphite.py decides what ships and keep this out of the kit if tools/ ships.`,
  },
  {
    key: 'tiers',
    task: `THE TIERED RUNNER AND THE SLIMMED RELEASE CHECKS. Read ${M}/release-checks.md (all), ${M}/census.md ("Per module" timings, "Worst offenders") and the spec (search "Tiers", "Tier 0", "release check"). Today: one focused suite (tools/check_hatch.py FOCUSED_MODULES, about 66 modules, 8 to 10 minutes here), window checks (UI_CHECKS), and release checks outside the suite that took about 65 minutes at 0.8.2 (scene, probes at two sizes, a crawler in two looks, a name sweep, the gate).
Build:
1. tools/run_tiers.py: one command, "python tools/run_tiers.py 0|1|2 [--look graphite|kasandra|both] [--changed <git ref>]". Tier 0: under ONE MINUTE of wall time on this 4-core machine, two processes at once: the fastest modules that guard the most (choose from the timings and from ${M}/kill_matrix.json "killer_tests" and "per_module": unique kills per second), and always the guarding tests (scopes, her hand's rules, memory rules, release integrity, the seed-is-current test, the one-name sweep). Tier 1: tier 0 plus the modules that import a changed file (build the import map in code, cached; read ${M}/raw.tar.gz census/tools/importmap.py for how it was done before), so a small change runs a small set. Tier 2: everything, the release tier: the full suite in both looks, the window checks, the scene on Rail Demo in both looks, the name sweep; it prints one table and one final line "0 failing" or the list. Each tier runs every module isolated the way the rules say (its own process and HOME), two at a time, with a per-module timeout, and writes a JSON result (module, look, ran, failed, seconds) under a folder given by --out. The tier lists live in one data file (tools/tiers.json or a table in the tool), and a test checks that every tests_integrated/test_*.py is in tier 2 and that tier 0 is a subset of it.
2. Slim the release checks as release-checks.md proposes in its "Step 1" (stop runs, write nothing new): find where each lives in the repository (tools/check_release.py, tools/check_hatch.py, tools/campaign.py, docs) and apply what applies to code that is in the repository; the probes and the crawler that lived only in scratch are simply not part of tier 2 (say so in the doc). From "Step 2" do only what is cheap and clearly right (for example the name sweep inside the suite is already done by part A's tests_integrated/test_one_name.py; compare_ui comparing the assertion message as well as the line).
3. Replace fixed waits with waits for a condition only where a tier-0 or window-check script spends most of its time waiting and the change is mechanical and safe; list the rest.
4. Measure, on a copy: tier 0 wall time (three runs), tier 1 for a one-file change in workbench/agenda_qt.py, tier 2 wall time once in each look (run the looks one after the other). Targets: tier 0 under 60 s; tier 2 (the whole release check) 15 minutes or less per look; if a target is missed say by how much and what would close it.
5. docs: a short page docs/CHECKS.md (or the existing page where checks are described) saying what each tier is, when to run it, and the measured times. tests: tests_integrated/test_run_tiers.py for the tool's own logic (tier membership, the changed-files map on a tiny fake tree, the result file, a failing module makes the run fail, a timeout is reported as a failure).
Another builder (key "checks") is retiring seven window-check scripts and porting the rest at the same time: read UI_CHECKS from tools/check_hatch.py at run time instead of copying the list.`,
  },
  {
    key: 'look',
    task: `THE LOOK LEFTOVERS FROM 0.8.3, AND A COLOUR-VISION CHECK. Read ${REPO}/wip/2026-11-14/yellow_review/review_code.md and review_look.md (the findings of two independent reviews of the burnt-yellow highlight in the Kasandra look), the spec's "What the look still owes" (search it), and ${REPO}/wip/2026-11-14/mockup/CANON.md for the rules of the look. Some findings were fixed in 0.8.3: check each against today's code before touching it, and report fixed-already / fixed-now / left with the reason.
1. The findings: (code review) chain-menu pictures vanish on the yellow bar (chain_icons.icon needs Active and Selected pixmaps drawn in the on-bar ink, as tool_faces does); lists with their own stylesheet keep the old selection fill (the process list, Log, Explore results, the cabinet, Documents, the Slate switch); the PDF evidence highlight is a see-through yellow fill (make it an opaque edge in Kasandra); the sheet's Run button focus is cyan; boss_theme.LEGACY sends some Graphite colours to yellow (list them, decide each, record the decision); the full-size logo kept in memory. (look review) the pointer's cyan glow turns green over the yellow bar (in Kasandra draw the glow so that laid over BAR, BAR_EDGE and AMBER_SOFT there are 0 pixels at hue 70 to 170 with saturation 0.25 or more: write that as a test using pointer.drawn()); the yellow "light" around the writing line and the Field's selected sheet comes out grey (make it warm: ring pixels at saturation 0.25 or more and hue 25 to 45, and still 0 green; a test that measures it on a rendered frame); the logo's ghosts at Neon. Leave for the owner to judge, do not change: the menu row's 2 px edge colour.
2. The words: a widened sweep found tips and descriptions that still name a key (the rule: no keyboard shortcut is printed on screen), and tests that still assert "Programs". Find them (tooltips, status tips, accessible descriptions, "what's this", the Guide pages shown in the program; patterns like Ctrl+, Shift+, F9, "press X") and fix them; extend part A's tools/name_sweep.py NEVER patterns or add a sibling sweep so a test fails when a shown string names a key. Words that describe a key the owner must really press with no pointer alternative are a finding to report, not to delete.
3. One failing test in the Kasandra look: tests_integrated/test_faces_find_light (one test about Kasandra's desk light fails with GRAPHITE_APPEARANCE=kasandra on the unchanged tree). Find out whether the test or the look is wrong, fix the right one.
4. THE COLOUR-VISION CHECK: a tool and a test. For each look's palette (workbench/boss_theme.py PALETTES), take every pair of colours that carry different meanings where they can appear together (ready / warning / error / live / chosen / held / her highlight; read the palette's role names and CANON.md's states), simulate weak red (protan) and weak green (deutan) sight with a standard published matrix (Machado, Oliveira and Fernandes 2009 at severity 1.0 and 0.6; cite it in the docstring), and compute the difference (CIEDE2000 or CIE76 in Lab; say which). A pair that falls under a stated threshold must have a word or a shape that tells the two apart on screen: the tool reports every such pair, and the test fails for a pair that is under the threshold and not in a reviewed table "told apart by" (each entry names the word or shape and where it is drawn). Put the tool in tools/colour_vision.py, the test in the look's existing test module or tests_integrated/test_colour_vision.py. Report the table for both looks. Do not change a palette colour to pass the check without saying so; prefer adding the word or shape.
5. Frames: on a copy, both looks at 1920x1200 and 1366x768: a menu open with the pointer's row lit, the writing line with the keyboard, the Field with a sheet selected, the Log with a row selected. Read the PNGs yourself and say what you see. Graphite (the first look) must be unchanged pixel for pixel except where a finding names it: compare before and after frames and report the count of changed pixels per frame. Save under ${OUT}/look/frames/.`,
  },
  {
    key: 'session',
    task: `THE LIST OF TABS SET ASIDE AT START GROWS, AND SAYS WHY ONLY ON stderr. Part A fixed the start-up faults (workbench/session.py, workspace_tabs.py, qt_app.py; tests_integrated/test_session_start.py and its helper session_start_probe.py: read those first and build on them; the Manual open at leaving no longer raises). Left open by it, on purpose, for this item:
1. Rooms that restore does not know how to reopen (Documents, Files and others) are put under "Reopen deferred tabs" at every start, and the list grows by one per such room per start. First reproduce it for real on a copy (three starts through the start-script probe, with those rooms open at leaving; print the saved session each time). Then do what is right for the owner: a room that can be reopened IS reopened at start (find out why these are not known: if a restore entry is simply missing, add it); a room that truly cannot be restored is listed once, never twice, and the list is bounded. Say what you found.
2. A saved tab that cannot be reopened gives its reason only on stderr. The owner never sees stderr in the full-screen session. Say it once in the window where such things are said (find where the desk reports a start-up note: Activity or the Log), in plain words, without a key name, the same in every look; a test.
3. Sweep every kind of tab the desk can open: open it, leave, start again (the faults builder's sweep script may still be at ${S}/work/b084/faults/sweep_restore.py). Report a table: tab kind; saved; restored, set aside, or raises. Fix what raises.
Keep the changes small. Run test_session_start and every module that imports the files you touched, in both looks.`,
  },
]

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
  const r = await agent(reviewPrompt(it), { label: `review:${it.key}`, phase: 'Review', schema: REVIEW })
  if (!r) return { key: it.key, failed: 'the review did not finish' }
  const base = { key: it.key, verdict: r.verdict, must_fix: r.must_fix.length, review: r.summary }
  if (r.must_fix.length === 0) return { ...base, fix: null }
  const f = await agent(fixPrompt(it, r), { label: `fix:${it.key}`, phase: 'Fix', schema: BUILD, isolation: 'worktree' })
  return { ...base, fix: f ? f.summary : 'the fix did not finish' }
}
// Two lanes, each finishing one item (build, review, fix) before it starts the next, so a cut-off run leaves whole items.
const by = k => ITEMS.find(i => i.key === k)
const lane = async keys => { const out = []; for (const k of keys) out.push(await chain(by(k))); return out }
const lanes = await parallel([() => lane(['look', 'session', 'guards']), () => lane(['checks', 'tiers'])])
const done = lanes.filter(Boolean).flat()
log(`finished: ${done.map(d => d.key + (d.failed ? ' NOT FINISHED' : d.fix ? ' fixed' : ' clean')).join(', ')}`)
return { items: done, files: `${OUT}/<key>.patch, .progress.md, .review.md, .build.result.json, .review.result.json, .fix.result.json` }
