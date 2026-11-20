export const meta = {
  name: 'graphite-085-money-dates',
  description: '0.8.5 Maths in lines, second item: money and dates, exactly, on the one maths core; built, reviewed and fixed',
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
    key: 'money',
    review: true,
    task: `MONEY AND DATES, EXACTLY, ON THE ONE MATHS CORE (release 0.8.5, second maths item). The core is merged in your starting commit: workbench/math_ranges.py, math_answers.py (the operation math.answer and the record ledger.math-answer/1), tolerances.py, the stac_bridge grammar (math ... | solve / range / check), tests_integrated/test_math_core.py and test_math_lines.py, and the lines page in docs (find it: it holds three Rail Demo examples). Read them first; their design is ${REPO}/wip/2026-11-14/pal/judge_one-math-core.md PART 2. The owner wants Kasandra to help with "managing life and money" as well as engineering and civil legal reasoning; a talk he has read promised: "amounts in a currency kept as exact decimals, never floating point, with rounding to the cent only when you ask and always honest; and the days between two dates, a date plus a number of days or months, done the calendar's way", with examples like "what can I spend each week and stay under the month's budget" and "when does this notice period actually end".
BUILD, with the same honesty as the core (exact Fractions only, no float, errors as states never exceptions, every answer the same ledger.math-answer/1 record with its receipt, holds / does not hold / cannot tell):
1. MONEY: an amount with a currency (an ISO 4217 code the owner writes, like USD or EUR); exact decimals in, exact rationals inside; adding or comparing different currencies is refused in words (no exchange rates unless the owner gives one as an input, and then the receipt names it); multiplying or dividing by plain numbers allowed; rounding only when asked (a "round to 0.01" step or similar), with the rule named in the receipt (choose one rule, half to even or half away from zero, say which and why, and keep it the only one), and the exact value always beside the rounded one. Money must work inside solve, range and check (a budget: solve "4 * weekly <= 1200 USD" for weekly gives up to 300 USD; with a range of rent between 950 and 1000 USD, the weekly allowance is a range).
2. DATES: calendar dates only (no times of day, no time zones), written ISO (2026-11-20); the days between two dates; a date plus or minus days, weeks, months or years with the month-end rule named (31 January plus one month: choose clamp to the month's last day, say so in the receipt); the weekday; business days (Monday to Friday; holidays only from a list the owner admits as a source, named in the receipt; none by default, and the receipt says "no holidays counted"); and dates inside check ("2026-12-21 <= deadline"). A deadline computed from a rule ("30 days after service on 2026-11-20") shows the rule, the count and the end date, and says whether the end day itself is included (state it; no hidden convention).
3. WHERE IT FITS: decide the cleanest way to add these without changing the FROZEN files the design names (math_model.py, math_units.py, math_backend.py, math_service.py, math_office.py, office_math_runtime.py, LedgerOffice.java): new modules beside the core are expected (for example workbench/math_money.py and math_dates.py) and new line verbs or new forms of the existing ones, whichever keeps the grammar simplest for the owner. Document the choice.
4. ON SCREEN AND IN THE DOCS: answers in words the owner reads (amounts with their currency and the exact value; dates with their weekday), no key named, no internal names. Add worked examples to the lines page: a weekly budget under a month's limit, two loans compared by total repaid (exact, from the owner's own numbers, no advice), a notice period's end date, a payment due in business days. Each example must be true: run it in a test.
5. TESTS: exact vectors written before the code (each fails before it exists), at least: money sums and refusals across currencies; rounding at exact halves under the named rule; a budget solve and a budget range; days between across a leap day (2028-02-28 to 2028-03-01 is 2 days); 31 January plus one month clamped; business days across a weekend; a deadline with the end day included and excluded; a date check holding and failing. Property tests: adding then subtracting days returns the date; rounding never moves an amount by more than half a cent; no float anywhere in the new modules (AST check).
The legal and money line: this computes what the owner asks, from his numbers and the rules he states or admits; it never gives financial or legal advice, and the docs say so in one sentence.`,
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
const lanes = await parallel([() => lane(['money'])])
const done = lanes.filter(Boolean).flat()
log(`finished: ${done.map(d => d.key + (d.failed ? ' NOT FINISHED' : d.fix ? ' fixed' : ' clean')).join(', ')}`)
return { items: done, files: `${OUT}/<key>.patch, .progress.md, .review.md, .build.result.json, .review.result.json, .fix.result.json` }
