export const meta = {
  name: 'graphite-084-part-a2',
  description: '0.8.4 part A, second half: independent review and fixes for the invented workspace, the three faults and the one-name change; the line bugs finished, reviewed and fixed',
  phases: [
    { title: 'Review', detail: 'an independent reviewer applies each patch to a fresh copy and tries to break it' },
    { title: 'Build', detail: 'the line bugs, continued from the interrupted work' },
    { title: 'Fix', detail: 'the must-fix findings, then the patch is rewritten' },
  ],
}

const REPO = '/home/user/Struthio'
const S = '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad'
const OUT = S + '/work/b084'
const PY = S + '/work/venv/bin/python'
const A = REPO + '/wip/2026-11-14/workflow_scripts/graphite-084-part-a.js'

const COMMON = key => `You are working on release 0.8.4 of Graphite (a local-first PySide6 desktop with an assistant, Kasandra). First read ${A}: the RULES text near its top binds you (its HARD RULES included; REPO, OUT and PY there are ${REPO}, ${OUT} and ${PY}), and the ITEMS entry with key "${key}" is the task this work answers. The main checkout ${REPO} holds the starting tree: only files under wip/ differ from the commit the patches were made against.

ECONOMY (binding). The usage allowance is tight and this run can be cut off at any moment.
- Work in few, large steps: put a batch of commands in a script file and run it once, blocking, with a long timeout (up to 9 minutes; a longer batch runs with run_in_background and you wait for its completion notice). Never loop on sleep, never poll.
- Never print whole test output into your context: send it to a log file and print only the lines matching '^Ran |^OK|^FAILED|^ERROR:|^FAIL:' and, for a failure, the last 15 lines of its traceback.
- Read files in the ranges you need; read a patch once. Do not run the whole suite: the coordinator runs it in both looks at merge. Run the modules that matter to this item.
- SAVE EARLY: after each milestone update your notes file (named below). If it already exists when you start, an earlier attempt at your job was cut off: read it and carry on from there instead of starting again.
- Keep at most one copy of the tree and delete it when you finish.`

const REVIEW = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['accept', 'accept_after_fixes', 'reject'] },
    must_fix: { type: 'array', items: { type: 'object', properties: { what: { type: 'string' }, where: { type: 'string' }, how_to_reproduce: { type: 'string' } }, required: ['what', 'where', 'how_to_reproduce'] } },
    should_fix: { type: 'array', items: { type: 'string' } },
    checked: { type: 'array', items: { type: 'string' }, description: 'what you ran and saw, with exact results; at most 12 short lines' },
    summary: { type: 'string', description: 'at most 150 words' },
  },
  required: ['verdict', 'must_fix', 'should_fix', 'checked', 'summary'],
}
const WORK = {
  type: 'object',
  properties: {
    summary: { type: 'string', description: 'at most 200 words' },
    tests: { type: 'array', items: { type: 'object', properties: { module: { type: 'string' }, look: { type: 'string' }, ran: { type: 'number' }, failed: { type: 'number' } }, required: ['module', 'look', 'ran', 'failed'] } },
    decisions: { type: 'array', items: { type: 'string' } },
    not_done: { type: 'array', items: { type: 'string' } },
    release_note: { type: 'string', description: 'two to five plain sentences for the 0.8.4 release notes, in the owner\'s terms' },
  },
  required: ['summary', 'tests', 'decisions', 'not_done', 'release_note'],
}

const ITEMS = {
  fixture: {
    key: 'fixture',
    extra: `The patch is large (about 2,100 lines, 16 files). Read closest: the new workbench/rail_demo.py (every number in it must be invented, nothing from the owner's workspace; the build must be deterministic and need no network or model), the campaign changes under tools/campaign_lib/, and whether the two new test modules really test what they say. The builder's full report is ${OUT}/fixture.build_report.json.`,
  },
  faults: {
    key: 'faults',
    extra: `The builder says fault 2 is real: with the dedicated session's settings, a second start after leaving with the Office tab open fails. Reproduce that once yourself on the unchanged tree (the builder's scripts are in ${OUT}/faults/: repro*.sh, repro_start.py), then confirm it is gone with the patch and that an ordinary start, a start with other rooms open, and a start from a damaged session file all still work. The builder's full report is ${OUT}/faults.build_report.json.`,
  },
  name: {
    key: 'name',
    extra: `THE BUILDER WAS CUT OFF near the end. Not done: the full suite in both looks (the coordinator does that at merge), tools/check_context_menu_ui.py on a copy, and the final frames. Do the last two as part of your review: run tools/check_context_menu_ui.py on your copy in both looks; take frames in both looks at 1920x1200 and 1366x768 of her column and of one right-click menu on a file (the builder's script ${OUT}/name/scripts/frames.py may serve; its first frames are in ${OUT}/name/frames/), read the PNGs yourself and confirm the name is Kasandra and nothing is clipped by the longer word. Also judge each place the builder chose to KEEP the old name (history, rights, identifiers) against the task.`,
  },
  lines: {
    key: 'lines',
    extra: `Correctness of the line evaluator matters most here: for each of the seven bugs check the rule chosen is one rule applied everywhere, that nothing is skipped, coerced or overwritten silently, and that the words each step shows match what it now does.`,
  },
}

const reviewPrompt = it => `${COMMON(it.key)}

YOU ARE THE INDEPENDENT REVIEWER of item "${it.key}". You did not build it; your job is to find what is wrong with it before it is merged. Never edit ${REPO}. Work only in ${OUT}/${it.key}/review/ ; your notes file is ${OUT}/${it.key}.review.md .
THE PATCH: ${OUT}/${it.key}.patch . THE BUILDER'S NOTES: ${OUT}/${it.key}.progress.md (do not trust them; verify).
${it.extra}

DO THIS:
1. Make a fresh copy of the main checkout's tracked tree (cd ${REPO} && git ls-files -z | grep -z -v -E '^(wip/|\\.claude/)' | xargs -0 cp --parents -t ${OUT}/${it.key}/review/copy), apply the patch there (git apply or patch -p1), make the seed current, and run the new and changed test modules plus the modules that import a changed file, in the default look and with GRAPHITE_APPEARANCE=kasandra. Report exact counts.
2. Read the whole patch once. Look for: behaviour asserted but not really tested (take two of the new tests, revert the piece of the fix each guards in your copy, and see them fail); house-rule breaks in any on-screen string; the owner's real data or name; silent fallbacks; anything that changes what the owner sees without being asked; dead code; files that should not be in the patch.
3. Try to break it with inputs the builder did not think of.
4. Think about what a picture or a test cannot show: timing, a slow disk, a damaged file, a restart in the middle.
Be proportionate: spend your effort where a mistake would cost the owner most. Return must_fix only for real defects, each with a way to reproduce it; should_fix for the rest. Before you return, write your findings to ${OUT}/${it.key}.review.md and delete your copy.`

const buildLines = `${COMMON('lines')}

YOU ARE THE BUILDER of item "lines", continuing work that was cut off by a usage limit. You are in a fresh git worktree at the starting commit (your current directory); work only there and in ${OUT}/lines/ . Your notes file is ${OUT}/lines.progress.md .
The earlier builder's unfinished work is ${OUT}/partial/lines.partial.patch (about 900 lines, 7 files): apply it with git apply. Its notes ${OUT}/lines.progress.md are OLDER than the patch (they say nothing was edited yet): trust the patch. Its scripts and logs are in ${OUT}/lines/ (recopy.sh makes a copy with a current seed; t.sh runs one module; probe.py shows the seven bugs; logs/).
First find out what state the work is in: for each of the seven bugs, is there a test that fails on the unchanged tree, and a fix? Then finish the task as written in the ITEMS entry, test as the rules say (tests_integrated/test_line_rules and the modules that use the evaluator: test_context_menu, test_graphite, test_writing_line, test_memory_settings, test_desk_acts, test_desk_scenes, test_project_desk, test_release_check, test_typewriter_faces, both looks), and after every milestone rewrite ${OUT}/lines.patch (the command is in the RULES) and your notes.`

const fixPrompt = (it, r) => `${COMMON(it.key)}

YOU ARE FINISHING item "${it.key}" after an independent review. You are in a fresh git worktree at the starting commit (your current directory): apply ${OUT}/${it.key}.patch (git apply), fix every must_fix finding below and the should_fix findings that are cheap and clearly right, re-test the modules concerned in both looks, then rewrite ${OUT}/${it.key}.patch from your worktree (the command is in the RULES) and append what you did to ${OUT}/${it.key}.progress.md . Your notes file while working is ${OUT}/${it.key}.fix.md . If you disagree with a finding, say why and leave the code; do not paper over it. The builder's notes: ${OUT}/${it.key}.progress.md .

THE REVIEW:
${JSON.stringify(r, null, 1)}`

const review = it => agent(reviewPrompt(it), { label: `review:${it.key}`, phase: 'Review', schema: REVIEW })
const finish = (it, r, b) => {
  if (!r) return { key: it.key, failed: 'review did not finish', build: b || null }
  const base = { key: it.key, verdict: r.verdict, must_fix: r.must_fix.length, should_fix: r.should_fix, review: r.summary, build: b || null }
  if (r.must_fix.length === 0) return { ...base, fix: null }
  return agent(fixPrompt(it, r), { label: `fix:${it.key}`, phase: 'Fix', schema: WORK, isolation: 'worktree' })
    .then(f => ({ ...base, fix: f || 'the fix did not finish' }))
}

// Issued in this order on purpose: the two finished items are reviewed first, then the name change, then the line bugs are built.
const results = await parallel([
  () => review(ITEMS.fixture).then(r => finish(ITEMS.fixture, r)),
  () => review(ITEMS.faults).then(r => finish(ITEMS.faults, r)),
  () => review(ITEMS.name).then(r => finish(ITEMS.name, r)),
  () => agent(buildLines, { label: 'build:lines', phase: 'Build', schema: WORK, isolation: 'worktree' })
    .then(b => b ? review(ITEMS.lines).then(r => finish(ITEMS.lines, r, b)) : { key: 'lines', failed: 'the build did not finish' }),
])
const keys = ['fixture', 'faults', 'name', 'lines']
const done = results.map((r, i) => r || { key: keys[i], failed: 'did not finish' })
log(`finished: ${done.map(d => d.key + (d.failed ? ' NOT FINISHED' : d.fix ? ' fixed' : ' clean')).join(', ')}`)
return { items: done, patches: keys.map(k => `${OUT}/${k}.patch`), reviews: keys.map(k => `${OUT}/${k}.review.md`) }
