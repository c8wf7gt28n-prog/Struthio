export const meta = {
  name: 'test-mammoth-measure-and-decide',
  description: 'Clean up the test mammoth, part 1: diagnose every failing test and gate script, measure what each test catches (coverage, sampled mutants), cost and flakiness, and decide test by test what to fix, port, merge, retire or tier',
  phases: [
    { title: 'Inventory', detail: 'a census of every test module, the 20 failing tests, the 29 window-check scripts' },
    { title: 'Effectiveness', detail: 'coverage per module, then sampled mutants with a kill matrix; the release checks track record and cost' },
    { title: 'Decide', detail: 'one judge: the decision table, the tiers, the runner, the savings' },
  ],
}

const S = '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad'
const PY = S + '/work/venv/bin/python'
const REPO = '/home/user/Struthio'
const W = S + '/work/testclean'

const GOAL = `
Graphite is a local-first Python 3.13 / PySide6 desktop workspace (repository ${REPO}, branch at 0.8.2, commit d1df337):
about 118,000 lines in 445 workbench modules; tests_integrated/ has 61 files (14,574 lines); the release check runs the
59 modules in tools/check_hatch.py FOCUSED_MODULES (937 tests), each in its own process, and they took 488 s on d1df337
(per-module seconds and failing test ids: ${S}/work/modules_082.json; the runner: ${S}/tools/tests/run_modules.py).
Twenty tests fail and have been carried as "known" for many releases:
  test_desk (6): test_the_band_colours_are_the_palettes, test_the_default_follows_the_interface_size_under_the_ceiling,
    test_the_grain_is_deterministic_quiet_and_centred_on_the_band_tone, test_the_lettering_reads_on_the_band,
    test_the_owners_width_is_one_width_for_both, test_the_workspace_keeps_the_floor_the_old_rules_protected
  test_model_settings (5): test_explicit_request_and_restore_override_launch_defaults,
    test_failed_activation_retains_original_restore_and_reports_owned_restored_worker,
    test_new_requests_freeze_defaults_auto_and_keep_idempotency_after_defaults_change,
    test_owner_cancellation_stays_stopped_and_never_automatically_restores, test_worker_uses_frozen_options_even_after_saved_defaults_change
  test_paper (4): test_attach_adds_nothing_to_the_accessible_tree_and_marks_only_the_focused_passage,
    test_reduce_motion_is_static_with_no_timer_and_the_setting_hides_the_mark,
    test_source_editor_is_refused_and_a_narrow_margin_shrinks_the_x_instead_of_entering_the_passage,
    test_the_page_is_never_an_ancestor_whose_margin_a_sibling_covers_nor_outside_the_scrolling_page
  test_graphite (3): test_palette_is_graphite_paper_eraser_and_pencil_only, test_public_name_and_internal_identities,
    test_the_band_places_the_cat_by_its_pale_coat
  test_system_menu (2): test_the_colours_are_named_constants_and_the_coat_is_warm_paper, test_the_two_menus_are_point_mirror_images
The window gate (tools/check_release.py --ui) runs 17 of the 29 tools/check_*_ui.py scripts (6,522 lines); 7 of 17 pass and
the other ten stop at the same lines release after release (results: ${S}/work/reports2/ui_082.json; baseline
${S}/work/reports2/ui_070d.json; compare tool ${S}/tools/tests/compare_ui.py).
Outside the repository, each release I also run (script: ${S}/work/checks_082.sh, logs: ${S}/work/logs082/): the suite
(8 min), the playable scene through the campaign in both appearances (2.5 min), 30 window probes at two sizes (30 min; the
probe scripts are ${S}/tools/field/*_probe.py plus window.py, stacy.py, regress.py, run through ${S}/tools/field/nomodel.py),
a crawler pressing every control in both appearances (28 min), a name sweep (1 min) and the gate (3 min): about 73 minutes.

The owner, verbatim: "We need to solve or retire ALL failing tests. We need to eliminate useless tests. We need to evaluate
the effectiveness to run and rerun all tests over and over again. Let's clean up this mammoth".

The owner's standing directions that tests must follow (they supersede older tests): RECORD_OF_DIRECTIONS.md and
docs/RELEASE_NOTES_*.md (newest first). Examples: no keyboard key printed on screen; the line language never named on
screen ("a line"); "Apps", never "Programs"; two appearances (Graphite, Kasandra); Neon glow by default; what always asks
still asks.
`

const RULES = `
RULES: Do not edit anything under ${REPO}. Work under ${W}/<your part>/. Make your own copy of the tree with
"git -C ${REPO} archive d1df337 | tar -x -C <dir>". Run every test or script with low priority and inside a private pid
namespace: "cd <copy> && QT_QPA_PLATFORM=offscreen nice -n 19 unshare --pid --fork --mount-proc --kill-child ${PY} -B ...".
A tools/check_*_ui.py script runs ONLY in your extracted copy, with HOME set to a new empty folder under ${W}, never in the
repository or a git worktree. Another session is building in the same machine: stay at nice 19 and never run more than two
test processes at once. Cite file:line for claims. Write your full data (JSON) under ${W}/<your part>/ and return a Markdown
report with the paths of your data files; no preamble.
`

const CENSUS = GOAL + RULES + `
YOUR PART (census): every test module in tests_integrated/ (all 61 files, not only the 59 focused ones; say which are not
focused and why they exist). For each module: tests, runtime (from modules_082.json; run each module 3 more times to measure
spread and FLAKINESS: any test that passes on one run and fails on another), the workbench modules it imports (an import map:
module -> source modules), what its assertions guard, classified as BEHAVIOUR (what the program does for the owner: rules,
records, safety, privacy, data, the hand's permissions, memory rules), CONTRACT (an interface other code relies on), LOOK
(colour constants, pixel sizes, layout positions, words of the current look) or TEXT (exact wording); count assertions; find
tests with no assertion, tests that only re-check a constant against itself, near-duplicate tests (the same check in two
modules), and tests whose file was changed in git only to follow a look change (git -C ${REPO} log --follow on each test
file: how many commits touched it and how many of those also changed theme or look files: churn). Also list workbench
modules that NO test imports. Save ${W}/census/census.json (one row per test: id, module, seconds share, kind, assertions,
imports, flaky, churn) and report the headline numbers and the worst offenders.
`

const FAILING = GOAL + RULES + `
YOUR PART (the failing): diagnose each of the 20 failing tests and each of the 10 failing window-gate scripts (which ten:
see ui_082.json), and the 12 check_*_ui.py scripts the gate does not run. For each failing test: run it alone, read the
assertion and the code it exercises, find WHEN it started failing (git bisect-style over the history: git -C ${REPO} log on the
code it tests; you may check out old commits into a scratch copy), and classify: STALE (it asserts a look or behaviour the owner
later changed: quote the direction or release note that superseded it), DEFECT (the code is wrong: show a minimal reproduction
and the fix), FLAKY, ENVIRONMENT (fails only in this container: say why). Give each a concrete action: FIX-CODE (the patch),
PORT (the new assertion that tests what the owner wants now, if that behaviour still deserves a test), or RETIRE (why nothing
of value is lost). Be especially careful with the five in test_model_settings: they are about model activation, restore and
cancellation, which the coming model-swap escalation depends on; reproduce each against the current code and say plainly
whether the behaviour is right. For the gate scripts and the 12 unrun ones: what each checks, why it stops, and FIX / PORT /
RETIRE / FOLD-INTO (a test module or a scene that already covers it). Save ${W}/failing/failing.json and report.
`

const COVERAGE = GOAL + RULES + `
YOUR PART (coverage): measure line and branch coverage of workbench/ by each focused test module separately. Install
coverage.py where it cannot disturb anything: "${PY} -m pip install --target ${W}/coverage/lib coverage" and run with
PYTHONPATH including that folder (coverage run --branch --source=workbench -p, one data file per module, with the module name
recorded). Produce: (1) per source module: covered lines, covering test modules; (2) per test module: lines it covers that NO
other module covers (unique coverage) and its total; (3) source modules or functions no test executes (with their size: dead or
untested?); (4) the map line -> covering test modules, saved as ${W}/coverage/line_map.json (compact: per file, per line, a list
of module indexes) for the mutation step. Report the numbers and the paths. Keep the whole run under about 90 minutes of wall
time; if it would be longer, cover the 59 focused modules first.
`

const MUTANTS = (cov) => GOAL + RULES + `
A coverage run produced this report:
---
${cov}
---
YOUR PART (mutants): measure what the tests actually CATCH with sampled mutation testing. Write a small AST mutator (no new
dependency needed): one mutant at a time in a scratch copy, of these kinds: flip a comparison (< to <=, == to !=), negate an
if condition, replace a return value with None or its negation, change a numeric constant by one, delete a call statement.
Sample about 160 mutants over covered lines, weighted toward the modules whose failure would hurt the owner most:
engineering_kernel, stacy_hand, desk_acts, desk_doers, resource_control, model_settings, local_brain, line_steps,
typed_pipeline, field_ripple, field_page, files_service, context_menu, release_integrity, stacy_foundation, change_sets,
continuing_work, and about a third spread over everything else. For each mutant run ONLY the test modules that cover that
line (from ${W}/coverage/line_map.json), at nice 19, with a per-module timeout of three times its normal runtime. Record
killed (a test failed), survived, timeout. Build the kill matrix (mutant x module) and from it: each module's kill count and
UNIQUE kills (mutants only it kills), mutants that survive everything (real gaps in the tests: list the source line and what
behaviour went unguarded), and the modules with zero unique kills. Equivalent mutants (that change nothing observable) must be
recognised and set aside, not counted as gaps. Keep wall time under about 2.5 hours (reduce the sample if needed and say so).
Save ${W}/mutants/kill_matrix.json and report.
`

const CHECKS = GOAL + RULES + `
YOUR PART (the release checks' worth): judge the effectiveness of running and rerunning the slow checks outside the suite.
(1) Cost: from the log timestamps in ${S}/work/logs082/ and earlier ${S}/work/logs0*/ folders, time per check and per probe.
(2) Track record: what each check has actually caught. Read git -C ${REPO} log (messages mention probes, the crawler, the gate,
the scene, the sweep, "found"), and the probe scripts themselves (${S}/tools/field/: which ones assert something and print
WRONG, which only take pictures). For each probe: what does it check that no test module checks (compare with the census
when you can: grep the tests for the same widget names and assertions)? (3) Overlap: the crawler at two appearances, the probes
at two sizes, the gate's 17 scripts, the scene: which of these duplicate each other or the suite. (4) Propose which of them
should become repository tests or scenes (so they run everywhere), which should run only at a release, which only when certain
files change (by the import map: e.g. the crawler only when a window file changed), and which should be retired, with the
minutes saved per release. Save ${W}/checks/checks.json and report.
`

const JUDGE = (census, failing, cov, mut, checks) => GOAL + `
Five parts measured the test mammoth:
=== CENSUS ===
${census}
=== THE FAILING ===
${failing}
=== COVERAGE ===
${cov}
=== MUTANTS ===
${mut}
=== THE RELEASE CHECKS ===
${checks}
===
You are the judge. Read-only for ${REPO}; you may read the parts' data files under ${W}. Decide, so a builder can act without
judging again:
(1) THE FAILING: every one of the 20 tests and every failing or unrun window-check script: FIX-CODE (with the patch outline and a
test that pins it), PORT (the new assertion and why the behaviour deserves a test), or RETIRE (one line of reason). None may be
left failing.
(2) USELESS TESTS: the retire and merge list. Rules: retire only with evidence (no unique mutant kills AND no unique coverage of
behaviour that matters, AND at least one of: brittle LOOK/TEXT assertion with churn, near-duplicate, flaky, slow for what it
catches). NEVER retire a test that guards safety, privacy, the owner's data, her hand's permissions and what always asks, the
model memory rules, release integrity or the seed, unless the very same check exists elsewhere (name it). Where a look test
still guards an owner direction (no key printed, the language never named, Apps), keep ONE good test for it, not ten.
(3) GAPS: the surviving mutants that matter, and the few tests to add for them.
(4) TIERS AND THE RUNNER: tier 0 (pure logic, no window, target under 60 s, run on every change), tier 1 (window modules,
chosen by an import and coverage impact map from the changed files, run before a commit), tier 2 (everything at a release:
full suite, scenes, the probes that earned their place, crawler, sweep, gate), tier 3 (on the ThinkPad). How the runner picks,
runs two modules at a time, and reports; where the slow test_desk_acts sweep and test_desk_scenes belong; what moves from the
scratch probes into the repository.
(5) THE NUMBERS: tests and lines before and after, minutes per change and per release before and after, and the mutant kill
rate before and after the retirements (it must not drop for what matters).
Return: PART 1, the decision table and plan for the builder (Markdown, exact test ids, files, actions); PART 2, an owner summary
of at most 300 words in plain English (no file names), what changes and why.
`

phase('Inventory')
const [census, failing] = await parallel([
  () => agent(CENSUS, { label: 'census', phase: 'Inventory' }),
  () => agent(FAILING, { label: 'the-failing', phase: 'Inventory' }),
])
phase('Effectiveness')
const [covmut, checks] = await parallel([
  async () => {
    const cov = await agent(COVERAGE, { label: 'coverage', phase: 'Effectiveness' })
    if (!cov) return { cov: null, mut: null }
    const mut = await agent(MUTANTS(cov), { label: 'mutants', phase: 'Effectiveness' })
    return { cov, mut }
  },
  () => agent(CHECKS, { label: 'release-checks', phase: 'Effectiveness' }),
])
phase('Decide')
const cov = covmut ? covmut.cov : null
const mut = covmut ? covmut.mut : null
const plan = await agent(JUDGE(census || '(missing)', failing || '(missing)', cov || '(missing)', mut || '(missing)', checks || '(missing)'), { label: 'judge:cleanup', phase: 'Decide' })
return { census, failing, cov, mut, checks, plan }
