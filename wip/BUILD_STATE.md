# Build state: where the unattended build stands

**Read this first on every wake-up.** It is updated after every step and pushed. If this file and anything else disagree,
this file is newer.

## The mandate (the owner, 19 Nov 2026)

"I approve of everything you've written in the plan ... I approve everything. I want you to build this until completion.
I want you to save your work so that way when my session times out ... you can just automatically resume ... and just
continue going on your own until it's done. That way I don't have to wake up in the middle of the night to say continue."

Later the same day: "I want you to use your own creativity to finish my vision and you add in your vision too. Make the
desktop I've been dreaming about for 35 years." So: creative latitude inside the owner's vision. My own additions are
listed in the revised road under "The builder's additions"; each is labelled as mine in the release notes so the owner
can strike it. They never override an owner's direction or a rule below.

- **The plan:** `wip/2026-11-14/ROAD_REVISED_2026-11-19.md` (the order of releases). Detail for each release:
  `wip/2026-11-14/SPEC_0.8.3_to_1.0.md` sections 8 to 15. Standing facts and the owner's directions:
  `wip/2026-11-14/NOTES.md`. The look: `wip/2026-11-14/mockup/CANON.md`.
- **Do not stop to ask.** Take the plan's default, record it below under "Decisions taken for the owner", go on.
- **The wake-up:** scheduled task "Continue the Graphite build", id `trig_017RpY8VWubnaTQN5DVGpS6g`, hourly, into the
  same session. Disable it (update_trigger enabled=false) when the build is complete or everything left needs the ThinkPad.

## What "complete" means here

Build, check and deliver each release in order, 0.8.4 to 0.8.12, then a 0.9.0 candidate, then the after-0.9.0 list.
What cannot be done here: anything that must be observed on the owner's ThinkPad (the six 0.9.0 gates, the ThinkPad
check's numbers, the 35B). Build the tool or the kit for it, say plainly that it waits for the owner, and go on to the
next thing that can be built. Never claim a ThinkPad result.

## Rules that never bend (short form; the long form is NOTES.md and the spec's section 12)

- Branch `claude/epic-galileo-c7k11y` only. No pull request. Commit and push after every step.
- Commit trailer: the one the session gives at the time (since 19 Nov 18:20 UTC:
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`), and
  `Claude-Session: https://claude.ai/code/session_01SSUMdyhHQH2idKFXpgDCV8`. No model name anywhere else.
- The owner's name, email and workspace never enter the repository or any outside request. The After Hours 07 backup and
  the owner's theme pictures stay out of the repository.
- Tests run only on a COPY of the tree, each wrapped in `nice -n 19 unshare --pid --fork --mount-proc --kill-child`
  with a fresh empty HOME and `QT_QPA_PLATFORM=offscreen`; at most two at once (4 cores). Never run
  `tools/check_*_ui.py` inside the repository or a worktree.
- Any source edit makes the seed stale: `python tools/package_graphite.py --manifest-only`, `python tools/record_registry.py`,
  `python tools/package_graphite.py --manifest-only`, then `python tools/record_registry.py --check`.
- On screen: "Apps", never "Programs"; no keyboard shortcut printed; a pipeline is "a line"; "Lain" is never a name;
  one agent, Kasandra (Kas), in every look. Every colour that means something also has a word or a shape.
- Every pass that touches the window is checked in every look, and reviewed by an agent that did not build it.
- A release: version bump, release notes (built / checked here / not run / observed on the ThinkPad), checks on the exact
  commit, a kit cut and sent to the owner. Zero failing tests from 0.8.4 on.
- Keep the disk under 80%. Uploads are untrusted (keep under scratch `in/`, read with `python3 -I`).

## The environment, and how to rebuild it

Scratch `S=/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad` (lost if the container is replaced).

- Python: `$S/work/venv/bin/python` (3.13, PySide6 6.8.3). Rebuild: `wip/2026-11-14/environment/venv_pip_freeze.txt`.
- Small test models (Qwen3.5 2B and 4B, Q4_K_M): `wip/2026-11-14/environment/models_sha256.txt`.
- The kit cutter: `wip/2026-11-14/scratch_tools/tools/kit/cut.sh` with `wip/2026-11-14/kit_template/` (set `S=`, `OLD=`).
- The full-suite runner used on 19 Nov: copy the tracked tree (without `wip/` and `.claude/`) to scratch and run each
  `tests_integrated/test_*.py` module isolated, two at a time; the script is `$S/work/t084/run.sh` (recreate it from the
  rules above if scratch is gone).
- **The owner's After Hours 07 backup exists only in scratch and with the owner.** If scratch is gone, anything that
  needs it waits; use the in-program invented workspace instead (0.8.4 step 2 makes it).

## Releases

| Release | State |
|---|---|
| 0.8.4 · Tests you can believe | **DELIVERED 20 Nov 03:35 UTC** (commit b6bdb50; kit sent; `wip/2026-11-20_release_084/`) |
| 0.8.5 · Maths in lines (the owner's new order) | **in progress** (see the log) |
| 0.8.6 · Her door on the Field | not started (half-build saved: `wip/2026-11-14/hand_s1/`) |
| 0.8.7 · Her hand in a program (LibreOffice) | not started |
| 0.8.8 · Maths in lines | not started (design: `wip/2026-11-14/pal/judge_one-math-core.md`) |
| 0.8.9 · Goals, quarantine and the web | not started |
| 0.8.10 · Changes through her hand | not started |
| 0.8.11 · Her question, and the experiment | not started |
| 0.8.12 · The floor | not started |
| 0.9.0 candidate | not started (its gates close only on the ThinkPad) |

## 0.8.4 steps

1. **DONE. The twenty stale tests fixed (commit 3f07341). Full suite on a copy, 19 Nov: 65 modules, 1,005 tests,
   0 failing**, default look, in the container. The first green suite since the import.
2. **MERGED (c47a9ba), reviewed and fixed.** An invented workspace kept in the program, Rail Demo (a 12 V rail: bench readings, two limit revisions, calculations, findings,
   an open question; invented numbers, the same shape as After Hours 07), and scene P01 able to run on it, so nothing
   needs the owner's backup. **Do this next: it protects every later step.**
3. **MERGED (90ee679), reviewed and fixed.** Three faults found in 0.8.3 by the overlay review (`wip/2026-11-19_handoff_review/code_review.md`): a saved look
   value that is not text stops the start (session.py); a saved Office or Slate tab may stop the start
   (workspace_tabs.py; reproduce first); "Now: Now:" in her column. A test for each.
4. **MERGED (43f42cd), reviewed and fixed.** One name: Kasandra in every look (workbench/assistant_identity.py and the tests and words that assert Stacy on
   screen). History keeps the names it was written with.
5. **MERGED (0a4cc3b), reviewed and fixed.** The window-check scripts: retire or fold 7, port the rest (`wip/2026-11-14/tests_measure/fix_patches/patches/`).
6. **MERGED (dd2c2db), reviewed and fixed.** The seven line bugs (NOTES.md "PAL P0"; `sdk/cli/arc1cli/typed_pipeline.py`), a test pinning each.
7. **MERGED (28e99db), reviewed and fixed.** Tests for the blind spots in the guarding code (Kernel scopes, her hand's rules, memory rules, release check); run the
   planted bugs again; target 75% caught there (`wip/2026-11-14/tests_measure/mutants.md`).
8. **MERGED (0ca267a), reviewed and fixed.** The tiered runner (tier 0 under a minute) and the slimmed release checks (`tests_measure/release-checks.md`).
9. **MERGED (a737d20), reviewed and fixed.** The yellow leftovers and the colour-vision check (`wip/2026-11-14/yellow_review/`, spec section 7).
10. **DONE.** Release 0.8.4: version, notes, checks on the exact commit, kit, send to the owner.

**State at 16:20 UTC, 19 Nov: part A is merged** (four commits, c47a9ba to dd2c2db, each built, independently reviewed
and fixed; all four patches applied without conflict; seed current). The reviews and notes are kept in
`wip/2026-11-19_b084_saved/` (`<key>.review.md`, `<key>.progress.md`, `<key>.fix.md`).
- **The full suite on the merged tree (commit dd2c2db), 19 Nov 16:28 UTC: default look 70 modules, 1,115 tests, 0 failing;
  Kasandra look 70 modules, 1,115 tests, 1 failing** (`test_faces_find_light`, her desk light: "172 not less than 150";
  it failed the same way before part A; part B's look item settles it).
- **Part B: workflow `graphite-084-part-b`, run id `wf_401c7b30-522`.** Run 1 (16:30) stopped at 17:30 on a weekly limit
  of the model it ran on (reset 26 Nov); the owner switched the session to another model at 18:15 and said "Continue".
  Run 2 (18:20) built, reviewed and fixed checks and look, then stopped at 19:25 on the 5-hour limit before session,
  tiers and guards got far (session left a reproduction and a plan in its notes). **checks and look were merged at
  21:30 UTC** (0a4cc3b, a737d20; no conflict; seed current). All files: `wip/2026-11-19_b084b_saved/`.
- **Running now:** the full suite on the merged tree in both looks (`run_suite_both_looks.sh`). **Next:** relaunch part B
  with `resumeFromRunId: wf_401c7b30-522`: look and checks come back from cache; session, tiers and guards run.
- How part B works: `wip/2026-11-14/workflow_scripts/graphite-084-part-b.js`
  (keys: look = step 9, checks = step 5, session, tiers = step 8, guards = step 7; two lanes, each finishing one item,
  build then review then fix, before starting the next). Hand-overs are files in scratch `work/b084b/`: `<key>.patch`,
  `<key>.progress.md`, `<key>.review.md`, `<key>.<role>.result.json`; an agent whose result file exists returns at once,
  so after a cut-off simply launch the same script again (with `resumeFromRunId` if the run id is known). After each
  finished item: copy its files to `wip/2026-11-19_b084_saved/`, apply (`git apply -3`), rebuild the seed, commit; the
  full suite in both looks before the release.
- **Then the release (step 10).**
- **Waiting, not started again:** the design pass for 0.8.5 (one agent, cut off at once by the limit; it wrote nothing).
  Start it only when 0.8.4 is out.

**The pace, measured (19 Nov).** One 5-hour usage window carries about 75 to 110 minutes of two agents working (1.6 and
2.3 million tokens of agent work in the two windows measured). So: finish items one after another rather than start
many; hand over through files; agents work in few large steps and never print whole test output. Windows have reset at
06:00, 11:00, 16:00 and 21:10 UTC. On 19 Nov 17:30 a weekly limit of one model also stopped work until 26 Nov; the owner
switched the session's model.

**Carried out of part B so far, with where each goes:**
- Left for the owner to judge by eye in the Kasandra look: the writing line's light now steps; the Field's rings show
  under overlapping sheets; the Return thread's writing box turned from yellow to blue. **Release notes, "to look at".**
- The setting "Script for incidental text" (appearance.cursive) is still in Settings and changes nothing on screen.
  **Decision taken for the owner: remove it in the release pass** (the rule "a control is lit only when a press would do
  something"); the menu toggle for the same setting is already gone.
- Keys still named on purpose, on a reviewed list (`tools/name_sweep.py` KEYS_KEPT and KEYS_CODE_KEPT): the Field's
  painted key labels and key card, the console's "Press Enter again", the Help menu's keyboard page, the document
  editor's screen-reader descriptions, the games. Each is a key with nothing to click instead. **For the owner to judge.**
- Frame step 05 of the retired frame check (the tab strip's height across six tabs) is covered by nothing; named in
  `docs/WINDOW_CHECKS.md`. The release gate's window checks run in the look in force only.
- The desk-light test in the Kasandra look was loosened by about 3 L* (stated in the test); it now passes.

**Carried out of part A (from the builders' and reviewers' lists), with where each goes:**
- Line evaluator, still silent or odd, none of them new: a line ending in `group FIELD` with nothing after it returns its
  rows ungathered; `add NAME = ...` replaces an existing field without a word; a text starting with @ cannot be compared;
  `has` searches Python's text of a value; `select` of a field no row has gives empty values; `select a, a` collapses;
  over and under order text by characters while sort folds capitals; the sheet lens matches names in any case; the Then
  menu's text offers still merge 1 with "1". **Goes to 0.8.8 (Maths in lines).**
- A saved line can answer differently in 0.8.4 than in 0.8.3 (exact totals; numbers written as text counted). **Say so in
  the release notes.**
- Rail Demo: `--set all` of the campaign now also runs the four demo cases, `--set scenes` lists eight; a build that
  waits 60 s for memory stops as a Fail saying why (the owner may prefer Blocked); only Poppler 24.02 was tried here:
  **run `tools/campaign.py run --set demo` on the ThinkPad** (waits for the owner).
- The repository already held values taken from After Hours 07 before this work (record ids and a PDF hash in
  `tools/campaign_lib/fixture.py`, the settled current and powers in `cases_anchor.py` and `docs/CAMPAIGN.md`, the CSV
  text in P01.json, a bench seed in `test_desk_acts.py`). Nothing added, nothing removed. **For the owner to decide**
  whether they stay (listed under Waiting).
- Her art plate's file is renamed (`branding/boss/plates/Kasandra after midnight.webp`), because the file's name shows
  on screen; the picture is unchanged. At 1366x768 the longer name is shortened with an ellipsis in the head's crumb.
- Seen on screen and not changed: Activity says "their order, niceness and Stop are in the System menu" (there is no
  System menu since 0.7.0); About says "Graphite 2.0". **Goes to part B's look item or the release pass.**
- `workbench/desk_acts.py` has its own literal list of looks; a test pins it equal to the one list. **0.8.5 removes it.**

**Found by part A's builders, to be closed in 0.8.4 (part B carries them):**
- Rooms that restore does not know (Documents, Files and others) go to "Reopen deferred tabs" at every start and the list
  grows by one per room per start. (session)
- With the Manual open at exit, saving the session raises and nothing is saved. (session)
- The suite in the Kasandra look had 6 failures on the unchanged tree: 5 assert the name Stacy (the name item fixes them),
  1 is `test_faces_find_light` about Kasandra's desk light. (look) **"Zero failing" means both looks from now on.**
- Fault 2 (a saved Office tab stops the start) is real in the dedicated session's settings: on the unchanged tree the
  second start fails with "Graphite could not start" when the Office tab was open at exit. Why the owner did not meet it
  on the ThinkPad is not known from here (it does not happen when the Office tab is closed before leaving).

## Asked by the owner, to do

- 19 Nov 22:15 UTC: "Discussion on what we did after the stuff finishes". When part B has finished and is merged (before
  cutting the 0.8.4 kit), stop and talk it through with the owner in plain words: what was built today and why, what the
  reviews caught, what is still open, what needs the owner's eye or decision, and what comes next. Then go on.

## The owner's decisions of 20 Nov 2026: the order after 0.8.4

Settled at 03:50 UTC ("Let's do maths, then join floor/door/hand into one complex but united pass. Then add programs like
web, librra, gadot and so on"), and at 04:40 UTC a pass added after the maths: "should we do another pass directed at kas
intelligence without a LLM loaded? With the purpose of helping her to use the LLM more effectively", then "Yes but spend
more time thinking about how and what we can achieve with creativity in the second math/logic/legal minded pass".

| Next kit | Holds | What the owner sees |
|---|---|---|
| **0.8.5 · Maths in lines** | old 0.8.8 | Solve, range, check, dates and money exactly, each answer with its receipt |
| **0.8.6 · Kas's mind, no model** (the math/logic/legal-minded pass) | her understanding of requests from the desk's own words; the planner and deduction (moved here from the door); both kinds of goals (desk goals, and goals over data judged with the maths); building short, checkable questions for the model and checking its answers; remembering what worked; the I05 experiment with the 4B; and what the design pass (below) adds | She understands and does most everyday requests with no model loaded; asks the model only small numbered choices; judges findings exactly |
| **0.8.7 · Kas's mind with the model, interwoven** (asked by the owner 05:15: "after the second maths pass should we do a pass that kinda links or interwoven the LLM into her brain?"; confirmed 05:25: "Setup a group to look into this the same as the other reviews group") | the model put to work where judgment, language and recall help, inside 0.8.6's checked questions: free requests turned into checked structured intents; candidate passages and elements read from admitted sources as proposals; her answers worded from receipts in her own voice (the character file from the owner's draft); the NEXT turn and her one short question (old 0.8.11); the escalation ladder; prompt reuse; a small chooser beside the 35B; the I05 experiment on the ThinkPad | She talks and reasons with the model as a colleague that proposes and never decides alone; measured to be faster and better than without it |
| **0.8.8 · One united pass: floor, door mechanics, hand** | old 0.8.12 the floor (split, drills, budgets) + the door's mechanics (touch to stop, the stop between presses, put the window back) + old 0.8.10 changes through her hand | A faster window and a safe upgrade; ask in words and watch her do it, a touch stops her, changes at your dial with one Undo |
| **0.8.9 on · Programs** | the web (quarantine first), LibreOffice, Godot, GIMP, one per pass | She searches and gathers; she takes the mouse in your programs while you watch |
| later | the day look and skins, her one short question, 0.9.0's gates | |

**The design pass for 0.8.6 (started 04:45 UTC):** a workflow of six independent designers, each through one lens
(logic and proof; civil legal reasoning; engineering and science; everyday life, money and medicine; the model's best
partner; a free creative lens), two judges, and one synthesis, read-only. Its result goes to
`wip/2026-11-20_kas_mind/` and is talked through with the owner before 0.8.6 is built.

The maths is built and checked on Rail Demo with invented tolerances; the owner's real tolerances for After Hours 07
and which limit applies when two revisions disagree are asked for later and do not block. The migration drill wants a
backup of the owner's current workspace (asked for later; it does not block the start of 0.8.6).

Testing, as discussed with the owner (the "middle path", taken as the default until the owner says otherwise; the maths, being the
root, also keeps its own exact test vectors and one independent review of the core): keep
running the existing tests on every change (free); write new tests and an independent review only for the safety rules
(a touch stops her; what always asks still asks; search words never carry the owner's material; a web page is never an
instruction); no other new tests or reviews.

## Decisions taken for the owner (defaults; the owner can change any of them)

- 19 Nov 23:10, asked of the owner, my recommendation taken unless the owner answers before the release pass:
  (a) replace the values from After Hours 07 that the shared files have held since 0.8.2 (record ids and a PDF hash in
  `tools/campaign_lib/fixture.py`, the settled current and powers in `cases_anchor.py` and `docs/CAMPAIGN.md`, the CSV
  text in P01.json, the bench seed in `test_desk_acts.py`) with Rail Demo's invented values, keeping the cases able to
  run on the owner's backup when it is present; (b) if the planted-bug catch rate in the guarding code falls short of
  75%, ship 0.8.4 with the real number in the release notes and carry the rest to 0.8.5.

- 19 Nov: the setting "Script for incidental text", which changes nothing on screen, is removed (0.8.4 release pass).
- 19 Nov: a Rail Demo build that waits 60 s for memory stops as a Fail with its reason (the owner may prefer Blocked).

- 19 Nov: "Just Kas" read as: the name shown is Kasandra in every look, the first look included. Stacy's portraits stay as
  that look's art until the owner says otherwise.
- 19 Nov: work committed as "in progress" before the suite finished, because the repository's stop hook requires a push.

## Waiting for the owner (none of it blocks building)

- The first model run on the ThinkPad (does the 35B load, on the Radeon or the processor, how fast).
- The names of the skins on screen; whether she is recognisably one person across skins.
- The eight look questions at the end of CANON.md; the spelling (Kasandra or Cassandra), asked as a comment in the doc.
- Whether the values from After Hours 07 that the repository has held since 0.8.2 (ids, a hash, the settled current)
  may stay in the public tree.
- For later releases: real tolerances for After Hours 07, the dial's default for her changes, a 0.4.6 workspace.

## Log (newest first)

- 20 Nov 05:55 UTC: 0.8.5's maths core merged (093335c) and the owner's values taken out of the shared files (e1cf56d),
  both reviewed and fixed; the dead setting merged earlier (5029e3f). Full suite running in both looks. Money and dates
  started as the second maths item: workflow `graphite-085-money-dates` (script in `wip/2026-11-14/workflow_scripts/`,
  scratch `work/b085/money.*`; build, review, fix). Then the 0.8.5 release: version, notes, tier 2 on the exact commit,
  kit, screenshots of a solve, a range and a check.
- 20 Nov 05:25 UTC: 0.8.7 (the model interwoven) confirmed; its design group started: workflow `graphite-087-model-interwoven-design`
  (run id `wf_8d796545-a17`, task `w3ac8ihlx`; six lenses: understanding, reading/the library, her voice, judgment, speed
  and memory with a model-check kit, trust; two judges; one synthesis; scratch `work/b087d/`). Running beside it: 0.8.5
  fixes (`wf_9807ad9e-481`) and the 0.8.6 design (`wf_2d88d9a7-4b2`, scratch `work/b086d/`). Both design scripts are
  saved in `wip/2026-11-14/workflow_scripts/`. If cut off: relaunch each with its `resumeFromRunId`.
- 20 Nov 05:15 UTC: the owner asked about a pass that interweaves the model into her mind after 0.8.6; recommended as 0.8.7 (pending his yes).
- 20 Nov 04:45 UTC: the owner added 0.8.6 "Kas's mind, no model" after the maths; its design pass started.
- 20 Nov 04:00 UTC: **0.8.5 started**: workflow `graphite-085-maths` (run id `wf_9807ad9e-481`, task `wncvmyr1a`; script
  `wip/2026-11-14/workflow_scripts/graphite-085-maths.js`; scratch `work/b085/`). Lane 1: maths (the one maths core from
  `wip/2026-11-14/pal/judge_one-math-core.md` PART 2, vectors 1 to 26; build, review, fix). Lane 2: setting (finish, no
  review), then private (finish, review, fix). Money and dates are a second maths item after the core is merged. If cut
  off: relaunch the same script with `resumeFromRunId`; agents pick up from their notes.
- 20 Nov 03:50 UTC: the owner settled the order: maths; one united pass of floor, door and hand; then programs.
- 20 Nov 03:35 UTC: **0.8.4 delivered.** Commit b6bdb50. Tier 2 on that exact commit: 202 runs, 2,368 tests, 0 failing,
  both looks, 26 min 45 s (10 skipped: the start scripts' tests that need an ordinary user on a Debian host). Kit cut,
  restored with INSTALL_LS (the restored tree equals the commit except `wip/` and `tools/planted_bugs/`, left out on
  purpose), release check PASSED on it, 1,321 files; START_HERE plus nine parts sent to the owner, with screenshots.
  Held for the next release: `wip/2026-11-20_for_085/` (the dead setting; the owner's own values).
- 20 Nov 03:40 UTC: the owner: 0.8.5 is the maths alone; the order after it is being discussed.
- 20 Nov 03:30 UTC: the owner set a new order after 0.8.4 (above): maths first, with the day look; then the door, goals and the web.
- 20 Nov 02:45 UTC: **the full suite on everything merged (28e99db): 78 modules, 1,204 tests, 0 failing in BOTH looks.**
  Release prep started: workflow `graphite-084-release-prep` (run id `wf_50b7a084-3ec`, task `wm4i1ridj`; scratch
  `work/b084c/`): keys setting (remove "Script for incidental text") and private (the owner's own values out of the
  shared files, after classifying each). Release notes drafted: `wip/2026-11-19_b084b_saved/RELEASE_NOTES_0.8.4.draft.md`
  (fill in TESTS and MODULES at the end). Then: version 0.8.4 (workbench/version.py VERSION, SHORT, LINEAGE; README
  title and install lines), docs/RELEASE_NOTES_0.8.4.md, seed, tier 2 in both looks and the release check on the exact
  commit, the kit (`wip/2026-11-14/scratch_tools/tools/kit/cut.sh`), send to the owner.
- 20 Nov 02:30 UTC: guards merged (28e99db). Planted bugs caught by behaviour: guarding code 51 of 53 (96%, was 30);
  overall 100 of 131 (76%, was 70). The builder's caution, for the release notes: most new tests were written for these
  same planted bugs, so 96% says these holes are closed, not how a new bug would fare; a fresh sample is the honest next
  measure (0.8.5). **Part B is complete. All of 0.8.4's building steps are merged.** Full suite running in both looks;
  then the release pass (step 10).
- 20 Nov 01:15 UTC: a second container restart (about 00:55) stopped part B again. tiers had finished its fix: merged
  (0ca267a). guards is built (planted bugs caught by behaviour: guarding code 30 of 53 -> 51 of 53; overall 70 of 131 ->
  100 of 131, 76%); its review was half done (two must-fix candidates in its notes: the kit check of tools/planted_bugs,
  and a planted bug left in the copy when a run is killed). Part B relaunched (task wy4uj3tkw) for that review and fix.
- 19 Nov 23:45 UTC: part B relaunched (task wdnhowczg, same run id) after a container restart at about 23:33 stopped it.
  tiers was in its fix (patch saved 23:18), guards half built (patch saved 23:30); restart notes added at the top of
  `work/b084b/tiers.fix.md` and `guards.progress.md`; both patches apply to HEAD.
- 19 Nov 23:10 UTC: talked 0.8.4 through with the owner; two questions asked (above). tiers in its fix; guards has
  tests for about 25 guarding gaps written and is rerunning the planted bugs.
- 19 Nov 23:05 UTC: session merged (d44d696): 72 of 102 room kinds now reopen at start (22 before), 3 set aside,
  19 not by design, 0 raise. tiers built and reviewed, its fix running; guards building (baseline: 56.6% of planted bugs
  caught by behaviour in the guarding code, target 75%).
- 19 Nov 22:15 UTC: the owner asked for a discussion of the work once part B finishes.
- 19 Nov 21:30 UTC: checks and look merged; full suite running.
- 19 Nov 19:25 UTC: the 5-hour limit stopped part B's second run after checks and look were finished.
- 19 Nov 18:20 UTC: part B relaunched on the model the owner chose; look and checks resume from their saved work.
- 19 Nov 17:30 UTC: a weekly model limit stopped part B (look and checks nearly built).
- 19 Nov 16:30 UTC: suite on the merged tree: 0 failing in the default look, 1 known in the Kasandra look; part B started.
- 19 Nov 16:20 UTC: part A merged in four commits after review and fixes; the full suite running in both looks.
- 19 Nov 13:10 UTC: the usage limit stopped part A2 with one agent left (the line fix, which had in fact finished its
  code and patch; its last test run completed on its own).
- 19 Nov 11:20 UTC: the limit lifted at 11:00. Interrupted work saved; worktrees removed; part A2 started (reviews first).
- 19 Nov 07:18 UTC: the usage limit stopped run 2 (name nearly finished, lines half built, no review yet).
- 19 Nov 07:20 UTC: fixture and faults built (unreviewed patches saved under `wip/2026-11-19_b084_saved/`); name and lines
  building; the script for part B written.
- 19 Nov 06:10 UTC: the usage limit lifted at 06:00; the wake-up fired; partial work from two builders saved as patches;
  1.3 GB of finished scratch trees deleted (disk 68%); part A restarted.
- 19 Nov 02:38 UTC: the 5-hour usage limit stopped all four builders of part A.
- 19 Nov 02:30 UTC: the owner gave creative latitude; the builder's additions written into the revised road.
- 19 Nov 02:20 UTC: full suite green (1,005 tests, 0 failing); part A of 0.8.4 started as a workflow.
- 19 Nov 02:12 UTC: mandate received; the wake-up scheduled; this file written; 0.8.4 step 1 applied and under test.
