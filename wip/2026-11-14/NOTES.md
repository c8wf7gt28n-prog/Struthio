# Where we stopped, 14 November 2026 (Graphite 0.8.3, commit 951c789)

Saved here because the build container is temporary. Nothing in `wip/` is part of the program; packaging leaves it out.

## Shipped
- **0.8.2** (d1df337): 40 desk acts typed in the writing line, the playable scene P01, after-hours look, typewriter face.
- **0.8.3** (951c789): Kasandra's hologram lower left with moving static and her state; her column for her words; every
  word in her typewriter face (fixed-width cut for code, numbers, Terminal); DELETE (a document's Delete is Erase);
  burnt-yellow highlight (bar in menus, edge elsewhere, never green; pointer halo pale violet in Kasandra); the neon kp
  logo on Apps as the only kp mark. Suite: 64 modules, 1,007 tests, the same 20 known failures; P01 4/4 in Kasandra;
  restore identical; release check PASSED. Not run for 0.8.3: probes, crawler, name sweep, gate.

## Order changed (14 Nov, after the test measurements): tests first
The measurement found all 20 failing tests stale, with fixes already written (`tests_measure/fix_patches/`), a behaviour
catch rate of 53% on 136 planted bugs (61 real gaps), and release checks of 73 minutes that caught one real fault since
0.5.0 (15 minutes after dropping duplicates and dead checks). So 0.8.4 is the test clean-up; her door is 0.8.5. The
release-by-release plan is in `TALK_my_plans_long_chat.md`.

## Paused (original order below; see the change above)
1. **Kasandra's hand, slice S1 "Her door on the Field"** (stopped mid-build).
   - Plan: `designs/judge_hand-plan.md` PART 1 §10 S1 (items 1-13, tests, scenes P02/P03, the 4B check).
   - Unfinished build, applied on bbf033b: `hand_s1/hand_s1_unfinished.patch` (28 files, `hand_s1/files.txt`; its build record, tests and scene results are in `hand_s1/build_record/`: all touched modules passed in the default look, P01-P03 9/9 in both looks, the 4B and 2B passed the goal turn; test_her_hand in Kasandra was mid-run when stopped; nothing reviewed).
     Apply on a branch from 951c789 with `git apply --3way`; expect small conflicts with 0.8.3's version and notes.
     It was NOT reviewed or tested to the end. Rebuild seed/manifest after applying.
   - The owner accepted the plan's six defaults (Go ahead covers moves up to the next goal or change, touch voids it;
     her changes keep the owner's identity, the journal says hers; DELETE waits until it has an exact Undo; an
     ambiguous limit shows both answers; tolerances are the owner's; touching stops her, scrolling does not).
   - Connect `HerHand.state_changed` to the hologram's states (thinking/acting → at work, waits → waits for you,
     stopped → stopped, finished → done).
2. **Test clean-up** ("solve or retire ALL failing tests ... eliminate useless tests ... evaluate the effectiveness").
   - Measurements done (`tests_measure/`): census, the 20 failing and the window-check scripts, coverage, about 160
     sampled mutants with a kill matrix, the release checks' worth. Only the judge step was left: re-run it from
     these reports (the judge prompt is in the workflow script `test-mammoth-measure-and-decide`).
   - Then a build pass: zero failing tests; retire tests only with evidence (no unique mutant kills AND brittle, duplicate,
     flaky or slow); never retire safety, privacy, data, her hand's permissions, what always asks, memory rules or release
     integrity; tiered runner (tier 0 under 60 s; tier 1 by changed files; tier 2 at a release; tier 3 the ThinkPad).
   - Fold in PAL P0: the line-evaluator bugs verified on 14 Nov (all real): `add x = 2*-3` gives -3; `where v=1`
     skips text "1" but `over 0` keeps it; `group` merges true with 1; `sum` skips numeric text that passed a comparison
     (8 becomes 3); `select title, state` refused; a quoted `;` refused while a quoted `|` passes; join trims and
     case-folds keys and overwrites an existing `other_*` field. File: sdk/cli/arc1cli/typed_pipeline.py.
3. **Small 0.8.3 leftovers** (`yellow_review/review_look.md`, `review_code.md`): the yellow glow around the writing line
   and the Field's selected sheet reads grey (it is added as light over blue); lists with their own colours (process
   list, Log, Explore, cabinet, Documents) keep the old fill; the PDF evidence highlight is see-through; the sheet's Run
   button focus is cyan; `boss_theme.LEGACY` maps some old colours to yellow.
4. **One math core** (`pal/judge_one-math-core.md`): PAL draft 0.2's evaluate / solve for / range / check stages and
   the goals engine as one implementation (`math_ranges.py`, `math_answers.py`, `tolerances.py`, Kernel op
   `math.answer`, record `ledger.math-answer/1`). It becomes the new S2; goals over data become S3. Corrections to the
   draft are in PART 1 (the 6 W row is "Continuous limit" in both revisions; Clock Lab needs all three allocations live;
   "under 6 W" in whole mA is 499; the step is "range", not "bound").
5. **Toward 0.9.0** (the talk of 14 Nov): six gates — the ThinkPad itself (a one-command check that reports the GPU's
   memory window, memory speed, the 35B's measured prompt and generation speed, Qt scale, fonts); her hand with the
   planner (S1-S4) and the I05 experiment (arms A, B1, B2); tests you can believe; architecture split of qt_app.py
   (5,358 lines), shell2.py (3,609) and context_menu.py (2,951) with performance budgets; data migration from 0.4.6;
   the look settled on the owner's panel.

## Measured facts worth keeping
- **4B (Qwen3.5-4B Q4_K_M), CPU, 4 threads:** memory-rules smoke PASSED (Auto activation, reply "ready", handover to the
  2B 4.1 s and back 6.1 s). I05 Current_A on a quieter CPU: 3 correct decisions (preview, instantiate, run), then the 4th
  passed the 180 s wall after 651 s and 30,827 tokens (under load it had managed 1). `model_runs/`.
- **Release checks cost** about 73 minutes (suite 8, scene 2.5, probes 30, crawler 28, sweep 1, gate 3).
  `test_desk_acts` alone is 190 of the suite's 488 seconds.
- **The yellow:** bar `#e2a72e` with ink `#171b3c` 7.79:1; edge-and-words fill `#5a3f0c`, edge `#e2a72e`, words `#ffd27a`.
  Yellow over cyan or the old blue turns green (hue 86-156); over her indigo it stays warm.
- **The neon logo** file keeps its halo in alpha-1 pixels; Graphite draws the glow instead (`workbench/kp_logo.py`).

## Owner's open items
- Run the ThinkPad check once it exists, and spend one evening with 0.8.x on the ThinkPad.
- The real tolerances for After Hours 07; the 35B's daily context size.
- A small vision model to prototype the "swap in a visual model" idea: offered, not answered.

## The scratch tools
`scratch_tools/` holds the orchestrator's probes, harnesses, kit cutter and test runner as they were (they expect the
scratchpad paths of this session; adjust `S=` at their top).

## What a new session needs (checked 14 Nov, before the pause)
- **Everything in the repository is pushed** (`claude/epic-galileo-c7k11y`); nothing in the container is needed except below.
- **Not in the repository on purpose, so bring it back:**
  - the owner's After Hours 07 backup (`Graphite_After_Hours_07.zip`, about 1.1 MB): the campaign's scenes and the Field
    probes need it; it was never put in this public repository;
  - the 35B simulation spec (the .docx) if the campaign's anchor work continues.
  Both were sent back to the owner on 14 Nov (the spec rebuilt as Graphite_35B_Simulation_Spec.docx, with a .txt copy),
  because the owner had only the 0.8.3 kit. Ask for them at the start of the next session.
- **Rebuildable, with the record here:**
  - the Python environment: `environment/venv_pip_freeze.txt` and `python_version.txt` (Python 3.13, PySide6 6.8.3);
  - the small test models: `environment/models_sha256.txt` (Qwen3.5 2B and 4B, Q4_K_M; re-download and check the hashes);
  - the kit cutter's install metadata: `kit_template/` (OFFLINE_FILES.json, DEBIAN_USB.sha256, INSTALL_GRAPHITE.sh), used
    with `scratch_tools/tools/kit/cut.sh` (set S= and OLD= at its top);
  - the workflows that built 0.8.2 and 0.8.3, and the paused ones: `workflow_scripts/`.
- **The unfinished hand slice** is `hand_s1/hand_s1_unfinished.patch` (on bbf033b); the test fixes are in
  `tests_measure/fix_patches/` (written against d1df337: re-run the five modules after applying).
