export const meta = {
  name: 'graphite-085-maths',
  description: '0.8.5 Maths in lines: the one maths core (solve, range, check, tolerances, receipts) built, reviewed and fixed; and the two small changes held from 0.8.4 finished',
  phases: [
    { title: 'Build', detail: 'one builder per item, each in its own worktree, leaving a patch' },
    { title: 'Review', detail: 'an independent reviewer applies the patch to a fresh copy and tries to break it' },
    { title: 'Fix', detail: 'the must-fix findings, then the patch is rewritten' },
  ],
}

const REPO = '/home/user/Struthio'
const S = '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad'
const OUT = S + '/work/b085'
const PY = S + '/work/venv/bin/python'
const M = REPO + '/wip/2026-11-14/tests_measure'

const RULES = `PROJECT. Graphite is a local-first PySide6 desktop with an assistant, Kasandra (Kas). Version 0.8.4 is released; we are building 0.8.5 "Maths in lines". The order of releases is in ${REPO}/wip/BUILD_STATE.md ("The owner's decisions of 20 Nov 2026"); standing rules are in the same file ("Rules that never bend"). 0.8.4 is merged and released in the commit your worktree started from: zero failing tests in both looks (about 1,200), Rail Demo (an invented workspace kept in the program, workbench/rail_demo.py), the tiered runner (tools/run_tiers.py: tier 0 in about 40 s; tier 1 for what a change touches, which needs git, so run it in your worktree only as a list and run the modules on your copy), the sweeps (tools/name_sweep.py) and the planted bugs (tools/planted_bugs/).

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
    key: 'maths',
    review: true,
    task: `THE ONE MATHS CORE, IN LINES (release 0.8.5; the owner: "Let's just do maths ... Then we have the strongest base to build on"). Everything Kasandra judges later (goals, her checks, money) stands on this, so it must be exact and honest.
THE DESIGN IS WRITTEN AND JUDGED: ${REPO}/wip/2026-11-14/pal/judge_one-math-core.md, PART 2 ("One math core") and PART 3. Read PART 2 in full before writing code; it names the modules, the line grammar, the core rules, the one record ledger.math-answer/1, ledger.tolerance/1, the names to use and to avoid, what each piece reuses, and the exact test vectors. The release as the owner will see it: ${REPO}/wip/2026-11-14/SPEC_0.8.3_to_1.0.md, search "### 0.8.6 · Maths in lines" (the old number of this release). Line numbers in the design date from 0.8.3; find each place by name.
BUILD what PART 2 calls "New S2, One math core, in lines": workbench/math_ranges.py (pure: no Qt, Kernel, model, SymPy or Z3), workbench/math_answers.py with the Kernel operation math.answer (read scope), workbench/tolerances.py (tolerances.get and tolerances.list read; tolerances.set approve scope AND an ALWAYS_ASKS row in workbench/stacy_hand.py with the design's words), the stac_bridge grammar for solve, range and check with freshness on every MATH result, the Kernel registration (follow schedule_math), the two test modules listed in tools/check_hatch.py FOCUSED_MODULES, and the grammar line in the docs page the design names (find it). Respect the FROZEN files exactly as PART 2 says (math_model.py, math_units.py, math_backend.py, math_service.py, math_office.py, office_math_runtime.py, LedgerOffice.java): do not change them; new answers carry their own implementation hashes. No float anywhere in the new modules (an AST test checks it).
TESTS: the design's test vectors 1 to 26, each exact, each a test that fails before your code exists (most simply cannot import) and passes after; vector 17's numbers are pure arithmetic on invented ranges and belong here; vectors 27 to 30 (the goal face) are NOT this release. Add property tests as vector 18 says, seeded and deterministic.
ON SCREEN: a math line typed in the writing line (to Kasandra or the Terminal, as lines run today) must show its answer in words the owner reads: Holds / Does not hold / Cannot tell (the existing headings), the number rounded outward with the exact value beside it, and a way to see the receipt (the inputs with their revisions, the method, the guarantee). Use the words and the place the window already uses for line answers; no key named, "Apps" not "Programs", no internal names (staC, Lain) on screen. Take one frame in each look at 1366x768 of a solve answer and read it yourself. A Then row ("Solve for…") on a calculation is wanted only if it is cheap and clearly right; otherwise list it in not_done.
SHOW IT ON RAIL DEMO: in the docs page for lines, give three worked examples on Rail Demo's invented numbers (12 V, 250 mA, a limit): solve for current under the limit, range with a tolerance the owner sets, and check. They must be true: run them in a test.
Not in this release: goals over data, money and dates (a separate item after this one is merged), Z3 or SymPy anywhere in the path.`,
  },
  {
    key: 'setting',
    review: false,
    task: `FINISH: REMOVE THE SETTING THAT DOES NOTHING ("Script for incidental text", appearance.cursive). An earlier builder did this work and was stopped by the coordinator just before its last test run; its patch is ${OUT}/setting.patch and its notes ${OUT}/setting.progress.md (they name a worktree that is gone: ignore that). Apply the patch to your worktree, re-read the notes, and finish: run every module that imports what it touched, in both looks, and tools/check_settings_02_ui.py on a copy in both looks; fix what fails; rewrite the patch. The rule it serves: "a control is lit only when a press would do something". A session file or settings store that still holds the old value must load without a word and without an error. No independent review is planned for this item, so be your own reviewer: revert each piece in your copy and see its test fail.`,
  },
  {
    key: 'private',
    review: true,
    task: `FINISH: TAKE THE OWNER'S OWN WORKSPACE VALUES OUT OF THE SHARED FILES. An earlier builder started this and was stopped by the coordinator after its survey; its partial patch is ${OUT}/private.patch and its notes ${OUT}/private.progress.md, with its survey in ${OUT}/private_all.txt (the notes may name a worktree that is gone: ignore that). The owner may share Graphite publicly one day. Since 0.8.2 some values taken from the owner's own workspace backup ("After Hours 07", never shipped) have been in the repository: record ids and a PDF's SHA-256 in tools/campaign_lib/fixture.py, the settled current and powers in tools/campaign_lib/cases_anchor.py and docs/CAMPAIGN.md, CSV text in tools/campaign_lib/data/scenes/P01.json, a bench seed in tests_integrated/test_desk_acts.py (and whatever else the survey found; the shipped tree only, not wip/). The owner's default: replace them with invented values, keeping the cases able to run on the owner's backup when it is present.
FIRST CLASSIFY every such value, with evidence: (a) taken from the program's own fictional first-run example that already ships (examples/thinkpad_first_run; docs/THINKPAD_FIRST_INSTALL.md "First-run workshop" uses 250 mA, 3.00 W, 280 mA, 3.36 W): public already, may stay; (b) identifiers and fingerprints that only make sense for the owner's own files (record ids, the hash of a file only the owner has); (c) the owner's own content. A copy of the owner's backup may exist under ${S}/work/campaign_fixtures: you may LOOK at it only to classify, never copy anything from it, never print its contents beyond what the classification needs.
THEN remove or replace everything in (b) and (c). The anchor cases (A01, A16, A17, A27) and the scene cases (P01a..d) must still run on the owner's backup when present: find the records at run time by kinds and names (as workbench/rail_demo.find does), not by ids written into the code; a check that the backup is the expected one must not need a hash written into the code (if one is needed, read it from a small file the owner keeps beside the backup, and say so in docs/CAMPAIGN.md). The demo cases and every test must still pass in both looks. Put the classification as a table in your report (value, where, class, evidence, what you did). Do not rewrite git history; say in the report that older commits keep what they hold.`,
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
  if (it.review === false) return { key: it.key, verdict: 'not reviewed (by plan)', build: b.summary }
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
const lanes = await parallel([() => lane(['maths']), () => lane(['setting', 'private'])])
const done = lanes.filter(Boolean).flat()
log(`finished: ${done.map(d => d.key + (d.failed ? ' NOT FINISHED' : d.fix ? ' fixed' : ' clean')).join(', ')}`)
return { items: done, files: `${OUT}/<key>.patch, .progress.md, .review.md, .build.result.json, .review.result.json, .fix.result.json` }
