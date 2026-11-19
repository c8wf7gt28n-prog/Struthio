export const meta = {
  name: 'graphite-084-part-a',
  description: '0.8.4 part A: an invented in-program workspace, three 0.8.3 faults, one name (Kasandra), the seven line bugs; each built, independently reviewed, fixed',
  phases: [
    { title: 'Build', detail: 'one builder per item, each in its own worktree, leaving a patch' },
    { title: 'Review', detail: 'an independent reviewer applies the patch to a fresh copy and tries to break it' },
    { title: 'Fix', detail: 'the must-fix findings, then the patch is rewritten' },
  ],
}

const REPO = '/home/user/Struthio'
const S = '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad'
const OUT = S + '/work/b084'
const PY = S + '/work/venv/bin/python'

const RULES = `PROJECT. Graphite is a local-first PySide6 desktop with an assistant, Kasandra (Kas). Version 0.8.3; we are building 0.8.4 "Tests you can believe". The plan is ${REPO}/wip/2026-11-14/ROAD_REVISED_2026-11-19.md; standing rules and facts are in ${REPO}/wip/BUILD_STATE.md (read its "Rules that never bend") and ${REPO}/wip/2026-11-14/NOTES.md. The main checkout ${REPO} is at the commit your worktree started from; the twenty formerly failing tests are already fixed there, so the suite should be green.

HARD RULES.
- Never edit, stage or commit anything in ${REPO} itself. Builders work only in the worktree they were started in (your current directory). Do NOT commit. Do NOT touch wip/, the version number, release notes, MANIFEST.json or project/stacy_seed/current/ in what you hand over.
- Tests and the app run ONLY on a throwaway COPY of your tree under ${OUT}/<your key>/copy (make it with: git ls-files -z --cached --others --exclude-standard | grep -z -v -E '^(wip/|\\.claude/)' | xargs -0 cp --parents -t <copy>). In the copy, first make the seed current: ${PY} tools/package_graphite.py --manifest-only ; ${PY} tools/record_registry.py ; ${PY} tools/package_graphite.py --manifest-only ; ${PY} tools/record_registry.py --check (with QT_QPA_PLATFORM=offscreen). Re-copy and redo this after every source change you want to test.
- Every test or app run: nice -n 19 unshare --pid --fork --mount-proc --kill-child env HOME=$(mktemp -d) QT_QPA_PLATFORM=offscreen ${PY} -B -m unittest -v tests_integrated.<module>   (one module at a time; at most two processes at once on this 4-core machine). Never run tools/check_*_ui.py in a worktree or in ${REPO}; only in a copy.
- On screen: "Apps", never "Programs"; no keyboard shortcut printed in any on-screen text; a pipeline is called "a line" (the internal name staC never shows); "Lain" is never used as a name; every colour that carries meaning also has a word or a shape. The owner's personal details never appear in code, tests, data or comments. The owner's real workspace ("After Hours 07") and its numbers must never be copied into the repository.
- Write code the way the surrounding code is written. Every behaviour you add or fix gets a test that fails before and passes after; say which.
- Zero failing tests is the rule from this release on: the modules you touch, and every module that imports what you touched, must pass in the default look and with GRAPHITE_APPEARANCE=kasandra.
- When done, write your patch: in your worktree run  git add -A -N . ; git diff HEAD -- . ':(exclude)MANIFEST.json' ':(exclude)project/stacy_seed/current' ':(exclude)wip' > ${OUT}/<key>.patch  and check it is not empty and applies to a clean checkout (git -C <a fresh git worktree or copy> apply --check).
- SAVE EARLY AND OFTEN. This run can be cut off at any moment by a usage limit. After every milestone (a test written, a fault fixed, a module green) rewrite your patch file with the command above and update a short note ${OUT}/<key>.progress.md saying what is done, what is half done and what is next, so an interrupted run leaves usable work behind.
- Report honestly: what you built, what you tested with exact results, what you did not do, and any decision you took where the plan was silent (give the reason). Do not claim anything ran on the owner's ThinkPad.`

const BUILD = {
  type: 'object',
  properties: {
    summary: { type: 'string' },
    patch_path: { type: 'string' },
    files_changed: { type: 'array', items: { type: 'string' } },
    tests: { type: 'array', items: { type: 'object', properties: { module: { type: 'string' }, look: { type: 'string' }, ran: { type: 'number' }, failed: { type: 'number' }, note: { type: 'string' } }, required: ['module', 'look', 'ran', 'failed'] } },
    new_tests: { type: 'array', items: { type: 'string' }, description: 'test ids added, each with what it pins' },
    decisions: { type: 'array', items: { type: 'string' } },
    not_done: { type: 'array', items: { type: 'string' } },
    release_note: { type: 'string', description: 'two to five plain sentences for the 0.8.4 release notes, in the owner\'s terms' },
  },
  required: ['summary', 'patch_path', 'files_changed', 'tests', 'new_tests', 'decisions', 'not_done', 'release_note'],
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
    key: 'fixture',
    task: `BUILD AN INVENTED WORKSPACE KEPT IN THE PROGRAM, so that scenes and tests no longer need the owner's private backup.
Background: the campaign's playable scene P01 (${REPO}/tools/campaign_lib/, data/scenes/P01.json, cases_scene.py, fixture.py; ${REPO}/docs/CAMPAIGN.md "The playable scene"; tests_integrated/test_desk_scenes.py) and the Field probes were written against the owner's real workspace, restored from a backup that is never shipped (see fixture.py). A copy of that restored workspace may still exist under ${S}/work/campaign_fixtures or ${S}/work/campaign_mirror*: you may LOOK at it to learn the SHAPE (which records exist and how they link) but you must not copy its files, names beyond generic ones, or numbers.
Build: a small engineering workspace made entirely of invented data, created by code through the Kernel's own operations (the same doors a person uses), with the same shape: a 12 V rail on a bench; a source document of bench readings (generate a small PDF or the kind of source the admission path accepts, in code, deterministically); a reviewed sheet of readings (12 V; settled current 250 mA; startup current and startup duration with invented values); two revisions of a limits sheet (Rev A archived, Rev B current, invented limits that make one finding hold and one not hold); calculations (settled power 3 W exactly; startup power); findings bound to their sources; one open question. Changing the settled current to 300 mA must give 3.6 W and mark what rests on it for recheck. Give it its own neutral name (for example "Rail Demo"), clearly marked as invented demonstration data.
Make it usable three ways: (1) a function tests can call to build it into a temporary workspace quickly (seconds, deterministic, no network, no model); (2) the campaign runner and scenes can run on it: P01 must be able to play on the invented workspace with its acts adapted by name (add a scene variant or a "workspace" switch in the scene's "given"; keep the original able to run when the owner's backup is present); (3) tests: add tests that build it, check every record and link, check the 250 to 300 mA change gives 3.6 W and marks recheck, and play P01 on it in the default look and the kasandra look.
Also find every test and tool that today silently depends on the owner's backup being present (grep fixture.py's users, KEEP_ENV, "After Hours") and report them; switch those that can run on the invented workspace without weakening what they check.`,
  },
  {
    key: 'faults',
    task: `FIX THREE FAULTS FOUND IN 0.8.3, in every look. They were found by a code review of an outside overlay; its text is ${REPO}/wip/2026-11-19_handoff_review/code_review.md (read the items "Reading the saved appearance safely", "A guard so a saved Office or Slate room tab does not stop Graphite from starting", and "Her column's line no longer says 'Now: Now:'"). The overlay's own diff may still be at ${S}/handoff3_work/overlay.diff (hunks for workbench/session.py, workbench/workspace_tabs.py, workbench/kasandra_column.py) as a hint only; it fixed two of them for one look only. Do them properly:
1. A saved appearance value that is not text (a list or an object, from a damaged or hand-edited session file) raises TypeError and Graphite cannot start. Reproduce with a test, fix so any bad value falls back to the default look, keep one list of allowed appearances without making the session module import the theme.
2. A session saved with the Office (or Slate) room tab open may fail at the next start, because the window restores its tabs before the bridge that opens rooms exists. FIRST reproduce it for real in a copy (write a session file with that tab, start the window offscreen the way the launcher does, see what happens) and report exactly what you saw. The owner has used 0.8.3 for several days with no problems, so it may not occur in the dedicated session; say whether it is real, under which conditions. If real, fix it at the cause (restore must not call what does not exist yet; the tab is restored once the bridge is there) and pin it with a test. If it cannot be reproduced, add the cheap guard and a test for the damaged case anyway and say so.
3. When something is running, her column shows "Now: Now: ...". Fix the doubled word for every look, with a test.
Then run every module that imports the files you touched, in both looks.`,
  },
  {
    key: 'name',
    task: `ONE NAME: KASANDRA IN EVERY LOOK. The owner decided on 19 Nov: "Just kas. Otherwise we have too many people." Today workbench/assistant_identity.py shows "Stacy" in the first look (graphite) and "Kasandra" in the kasandra look. Make the name shown on screen Kasandra in every look (the short form "Kas" only where the screen already uses a short form).
Scope: everything a person can read on screen or hear from a screen reader: her column, menus ("Ask ... about this"), tips, cards, the dial's words, model error words, accessible names, the Guide pages shown inside the program. Find them all (grep -rn "Stacy" workbench/ sdk/ tools/ docs/ project/ --include=*.py --include=*.md --include=*.json, then judge each hit).
Do NOT change: internal identifiers, module and file names (stacy_hand.py, stacy_seed, stacy_control ...), protocol and record identifiers, stored history (it keeps the names it was written with: add a test that an old record written under "Stacy" still reads back with that name), RIGHTS.md and COPYING (they keep "Stacy" as a name the owner holds), branding/stacy/ (her portraits stay as the first look's art), old release notes and RECORD_OF_DIRECTIONS.md history.
Update the tests that assert the old name on screen, and add one test that fails if any on-screen string in either look contains "Stacy" (reuse the name sweep under tools/ if it fits: read tools/ for the existing sweep and extend its pattern rather than writing a second one).
Check with frames: in a copy, open the window offscreen in both looks at 1920x1200 and 1366x768, capture her column and one right-click menu, read the PNGs yourself and confirm the name and that nothing is clipped by the longer word. Save the frames under ${OUT}/name/frames/.`,
  },
  {
    key: 'lines',
    task: `FIX THE SEVEN VERIFIED LINE BUGS in the line evaluator, ${REPO}/sdk/cli/arc1cli/typed_pipeline.py, each pinned by a test. They are listed in ${REPO}/wip/2026-11-14/NOTES.md (search "PAL P0") with probes in ${REPO}/wip/2026-11-14/pal/probes/ and reasoning in ${REPO}/wip/2026-11-14/pal/judge_one-math-core.md. The bugs and the behaviour wanted:
1. "add x = 2*-3" gives -3; it must give -6 (a unary minus after an operator).
2. "where v=1" skips the text "1" but "over 0" keeps it: a where filter and a comparison must treat a number written as text the same way. Choose one rule (recommended: text that is exactly a number compares as that number in both), apply it everywhere a value is compared, and document it in the step's own help words.
3. "group" merges true with 1: they must stay separate groups.
4. "sum" skips numeric text that passed a comparison (8 becomes 3): a sum either includes numbers written as text under the same rule as 2, or refuses visibly with the count of what it could not add. Never a silent skip.
5. "select title, state" (with a space after the comma) is refused: it must work.
6. A quoted ";" is refused while a quoted "|" passes: a quoted semicolon is accepted like a quoted bar.
7. "join" trims and case-folds its keys and overwrites an existing other_* field: it must match keys exactly as written and never overwrite a field (choose and document how a clash is named).
First write the seven failing tests from the probes (one test per bug, plus edge cases: negative numbers, "1.0" versus "1", empty text, mixed types, nested quotes), see them fail, then fix. Keep every existing line test green, and check the callers: the Then menu and line steps (workbench/line_steps.py and whatever builds lines for the right-click panel) must still produce lines that run, and the words each step shows must match its new behaviour. Search for any other place with the same class of bug (silent skip, silent coercion, silent overwrite) in the evaluator, fix what is clearly the same fault, and list the rest in not_done.`,
  },
]

const PARTIAL = { fixture: true, faults: true }
const buildPrompt = it => `${RULES}

YOUR KEY: ${it.key}. Your throwaway area: ${OUT}/${it.key}/ . Your patch goes to ${OUT}/${it.key}.patch .
${PARTIAL[it.key] ? `\nAN EARLIER ATTEMPT AT THIS ITEM WAS CUT OFF by a usage limit after about twenty minutes. Its unfinished, unreviewed work is saved as ${OUT}/partial/${it.key}.partial.patch (made against the same starting commit), and its logs and scripts are in ${OUT}/${it.key}/ . Read the patch first. If it is sound, apply it in your worktree (git apply) and carry on from there; if parts are wrong, take only what is good. Do not trust it: nothing in it was tested to the end.\n` : ''}
YOUR TASK.
${it.task}`

const reviewPrompt = (it, b) => `${RULES}

YOU ARE THE INDEPENDENT REVIEWER of item "${it.key}". You did not build it and your job is to find what is wrong with it. You may not edit the worktree or ${REPO}; work in ${OUT}/${it.key}/review/ only.

THE TASK THE BUILDER WAS GIVEN:
${it.task}

THE BUILDER'S REPORT (do not trust it; verify):
${JSON.stringify(b, null, 1)}

DO THIS:
1. Make a fresh copy of the main checkout's tracked tree (cd ${REPO} && git ls-files -z | grep -z -v -E '^(wip/|\\.claude/)' | xargs -0 cp --parents -t ${OUT}/${it.key}/review/copy), apply ${OUT}/${it.key}.patch there with git apply or patch -p1, make the seed current, and run the modules the builder named plus every module that imports a changed file, in the default look and with GRAPHITE_APPEARANCE=kasandra. Report exact counts.
2. Read the whole patch. Look for: behaviour that is asserted but not really tested (a test that would pass without the fix: revert the fix in your copy and see the new tests fail); house-rule breaks in any on-screen string; the owner's real data or name; silent fallbacks; anything that changes the existing looks; dead code; files that should not be in the patch.
3. Try to break it with inputs the builder did not think of.
4. Think about what a picture or a test cannot show: timing, a slow disk, a damaged file, a restart in the middle.
Return must_fix only for real defects with a way to reproduce each; should_fix for the rest.`

const fixPrompt = (it, b, r) => `${RULES}

YOUR KEY: ${it.key}. You are finishing item "${it.key}" after an independent review. You are in a fresh worktree at the same starting commit: first apply the existing patch (git apply ${OUT}/${it.key}.patch), then fix every must_fix finding below and as many should_fix as are cheap and clearly right, re-test as the rules say, and rewrite ${OUT}/${it.key}.patch from your worktree (same command as before). If you disagree with a finding, say why and leave the code; do not paper over it.

THE TASK:
${it.task}

THE BUILDER'S REPORT:
${JSON.stringify(b, null, 1)}

THE REVIEW:
${JSON.stringify(r, null, 1)}`

const results = await pipeline(
  ITEMS,
  it => agent(buildPrompt(it), { label: `build:${it.key}`, phase: 'Build', schema: BUILD, isolation: 'worktree' }),
  (b, it) => b ? agent(reviewPrompt(it, b), { label: `review:${it.key}`, phase: 'Review', schema: REVIEW }).then(r => ({ b, r })) : null,
  (br, it) => {
    if (!br) return null
    if (!br.r || !br.r.must_fix || br.r.must_fix.length === 0) return { key: it.key, build: br.b, review: br.r, fix: null }
    return agent(fixPrompt(it, br.b, br.r), { label: `fix:${it.key}`, phase: 'Fix', schema: BUILD, isolation: 'worktree' }).then(f => ({ key: it.key, build: br.b, review: br.r, fix: f }))
  },
)
const done = results.map((r, i) => r || { key: ITEMS[i].key, failed: true })
log(`finished: ${done.map(d => d.key + (d.failed ? ' FAILED' : d.fix ? ' fixed' : ' clean')).join(', ')}`)
return { items: done, patches: ITEMS.map(i => `${OUT}/${i.key}.patch`) }
