# Census of tests_integrated at d1df337

## Data files (all under /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/testclean/census/)
- **Per test (939 rows):** `census.json`. Each row has the id, `where` (file:line), focused, kind, seconds per run, mean seconds, share of module, share of suite, static and executed assertions, imports, outcomes in 5 runs, flaky, the failure line, churn and flags (tautology, constant_only, wording_assertions, near_duplicates).
- **Per file (61 rows):** `modules.json`. Each row has the role, the module docstring (what it guards), times and spread, overhead, kinds, failing, direct imports, churn and drift.
- **Headline numbers:** `summary.json`.
- **Import map:** `importmap.json` (test module → workbench modules, named directly and loaded at runtime, plus the untested lists). `reach.json` checks the untested modules against the program's start points.
- **Churn:** `churn.json` (git log --follow per file, per-test changes per commit), `testdiffs.json` (what each change did), `followed_look.txt` (hand-read: edits made only to follow a look or wording change), `drift.json`.
- **Kinds:** `kinds_hand.txt` (the hand table) and `kinds.json`.
- **Weak checks:** `constants.json`, `dupes.json`, `contradictions.json`, `static.json`.
- **Raw runs:** `runs/run1..3/` (timed), `runs/counted4/` (counts executed assertions), `at_import_runs/` (the 5 failing modules run at the import commit aa0ce07).
- **Scripts:** `tools/*.py`.

## Headline numbers
| | |
|---|---|
| Files | 61 `.py` files: 60 test modules with 939 tests, plus 1 helper |
| Focused (release check) | 59 modules, 937 tests |
| Not focused | `test_exact_math_solvers` (2 tests), on demand at tools/check_hatch.py:69-70. Needs sympy/z3 and starts a solver process. It passed every run (4.2–5.6 s). |
| Helper | `protocol_fixture.py`: a fake model server speaking the HTTP protocol. Used at test_slate_reasoning.py:18 and test_change_sets.py:221-222. |
| Dead folder | `diagnostics/` (README + a 32 KB sqlite.gz). Referenced only by MANIFEST.json and docs/INTEGRATED_I02.md:68. No code reads it. |
| Time, 59 focused modules | 511.3 / 502.6 / 494.8 s (0.8.2 baseline: 487.5 s). The machine was shared with another build. |
| Spread per module | median 7.5%. Worst: test_stacy_start 5.8 → 3.2 s (82%); test_system_menu 28.0 → 18.4 s (52%). |
| **Flaky tests** | **0 of 939** over 5 runs (the 0.8.2 baseline, 3 timed runs, 1 counting run) |
| Failing | **20**: the same ids in every run, and the same 20 already failed at the import commit aa0ce07 |
| Kinds | BEHAVIOUR 745 (405 s) · LOOK 96 (18 s) · CONTRACT 52 (4 s) · TEXT 46 (17 s) |
| Kinds of the 20 failing | LOOK 14 · BEHAVIOUR 5 · TEXT 1 |
| Assertions | 6,146 in the source (5,427 in test bodies, 719 in helpers); 28,088 actually executed |
| Tests with no assertion | 0 in the source, 0 executed. 21 tests execute exactly one. |
| Wording assertions | 707 assertions in 303 tests compare against a literal of 3 or more words |
| Concentration | 14 tests take 50% of the time. 606 tests run under 0.1 s; 883 under 1 s. |
| Fixed cost | process start, imports and window setup add 63 s per run (12.6%) |
| Workbench coverage | 468 modules (445 top-level + stac 16 + view_modules 7), 122,535 lines. 168 are imported directly by some test, 386 are loaded in some test process. **82 modules (14,323 lines) are never loaded by any test.** |

## Re-running
No test changed outcome in five runs. Re-running the same commit therefore gave timing only, and no new pass/fail information. The 20 "known" failures carry no information: their outcome has been fixed since before the git history began.

There are 80 commits from the import (aa0ce07, 2026-11-12) to d1df337. None of them fixed these 20 tests (see at_import_runs/). Their test files were never edited after the import, while the code they test kept changing. drift.json: test_desk.py has 0 edits against 33 commits to its source files; test_system_menu 0 against 37; test_paper 0 against 9.

## The 20 failing tests (cause from the run)
- **test_desk, 6 tests, LOOK:**
  - test_desk.py:26 and :48: `268 != 360` (default pane width).
  - test_desk.py:37: `674 != 600`.
  - test_desk.py:111: grain spread `4 ≤ 6`.
  - test_desk.py:116: mean tone `#0c0f0e` vs expected `#4a4741`.
  - test_desk.py:124: `#f2a369` vs `#ff9a36`.
  - These pin a light "paper" look that the dark look has replaced.
- **test_graphite, 3 tests:**
  - test_graphite.py:75 (LOOK): the brand palette is light (`#504d46…`) but the test says it equals shell2's dark palette.
  - test_graphite.py:242 (LOOK): `15 != 16`.
  - test_graphite.py:331 (TEXT): expects version `'0.1'`, gets `'0.8.2'`. Behind it is a second, hidden failure: test_graphite.py:332 expects `('slate','Assignment')`, but the program and test_writing_line.py:14 (and test_frame.py:42) say `'Assistant'`. **These are contradictory tests.**
- **test_system_menu, 2 tests, LOOK:** test_system_menu.py:503 `319 != 236`; test_system_menu.py:528 (cat colours vs shell2, same light-vs-dark mismatch as test_graphite.py:75).
- **test_paper, 4 tests, LOOK:** test_paper.py:197, :218, :245, :265 all fail `0 not greater than 20/10` (marker widget geometry).
- **test_model_settings, 5 tests, BEHAVIOUR, out-of-date test setup (the expected options and the fake model worker no longer match the code):**
  - test_model_settings.py:87 and :92: the launch options gained `backend`, `requested_backend`, `gpu_layers` and `cpu_fallback`.
  - test_model_settings.py:157 and :168: the fake worker and its restore are no longer seen.
  - test_model_settings.py:185: `ValueError: Owned model worker termination was not confirmed` (raised at workbench/local_brain.py:309).

## Weak or useless tests
- **Tautology:** test_system_menu.py:511 `assertIs(programs.m, programs.m)`. `m` is a plain attribute (workbench/programs_qt.py:440), so this cannot fail. test_kasandra.py:106 compares `pick(...)` with itself, but that is a real determinism check and should stay.
- **Tests that only restate constants (5):**
  - test_desk.py:122 (also failing).
  - test_kasandra.py:41 (pins Graphite's hex colours).
  - test_launcher.py:318: restates the explore schema that the recorded registry already pins. Its own comment at :319 says so; the check that compares against the recorded registry is test_release_check LiveRecord.
  - test_vocabulary.py:53 (`'Egress'`/`'Exports'`).
  - test_writing_line.py:12 (the TARGETS tuple, also asserted at test_frame.py:42).
- **Near-duplicates across modules (read by hand; dupes.json has the 29 mechanical groups):**
  - test_paper.py:15 `WritingMarkerSettingTests` copies the test_hardware_settings.py:14 template: two test pairs at Jaccard 0.70–0.71, with 10 identical assertions.
  - test_explore.py:58 is contained in test_launcher.py:87 (Jaccard 0.68; same job-count fixture, payload and assertions).
  - test_cabinet_actions "private and missing" is close to test_explore "private or stale" (0.50).
  - Centre floor 400/514/560 is asserted in both test_frame.py:16 and test_desk.py:32.
  - The palette tie to shell2 is asserted in four places: test_desk.py:122, test_graphite.py:73, test_system_menu.py:526, test_kasandra.py:41.
  - The settings family (8 files) shares the same receipt and journal assertions.
- **Words the standing directions retired, still asserted:** test_system_menu.py:386 checks a tooltip saying "Programs Graphite does not manage keep running". test_launcher.py:328 asserts an Explore group named 'Programs'. The directions say Programs is now Apps (RECORD_OF_DIRECTIONS.md:286-287; docs/RELEASE_NOTES_0.8.1.md:85). The owner should decide whether these on-screen words count.
- **Stale name:** test_writing_line `test_the_poem_placeholder…` now asserts `'prompt'`.

## Churn (git, 80 commits)
- 46 of the 61 files were never edited after the import. 8 were created later; 7 were edited.
- 48 tests were modified after the import (52 edits). **26 tests (29 edits) were changed only to follow a look or wording change** (followed_look.txt):
  - test_context_menu: 11, all in ddad387 (the right-click redesign).
  - test_launcher: 4 ("Open programs" → "Open apps"; the Game row added).
  - test_faces_find_light: 4.
  - test_writing_line: 3 ("poem" → "prompt"; "CTRL+ENTER" → "THE ARROW"; "STAC" → "A LINE").
  - test_graphite: 2; test_frame: 1; test_conditions: 1.
- 6 tests were removed after the import; 3 of those removals were in look commits (459583b, 94244c2, 6a7ef43).
- Most look-driven churn per file: test_faces_find_light has 9 commits, 7 of which touched look files; test_kasandra 4 of 4; test_writing_line 4 of 5.

## Workbench code no test touches
- **Never loaded by any test:** 82 modules, 14,323 lines. The largest are sheet_workbench_qt (767), setup_arc1 (695), genesis_tab (467), stac.chronicle (434), stac.cli (405), universal_viewer_qt (371), qt_theme (367), pdf_qt (361), chain_workbench_qt (358) and clip_jobs (351). Only clip_workspace is imported by a UI check.
- **Never loaded and not reached from any start point:** app (883), stacy_presence (181), unix_setup (117), workspaces (72), owner_tls (62), stac.__main__ (2). Apart from MANIFEST.json, nothing references them, so they are likely dead code. imagebuild (62) is the exception: sdk/cli/arc1cli/main.py uses it.
- **Never imported directly by a test:** 300 modules (56,677 lines). 220 of them are loaded only as a side effect of other imports.

## Worst offenders
1. **test_desk_acts.py:313 `test_every_navigation_changes_nothing`:** 109 s, 21.7% of the whole suite on its own. Next slowest: test_desk_acts.py:580 (23 s), test_desk_scenes.py:54 (20 s), test_desk_acts.py:664 (15 s), test_context_menu.py:790 (11.6 s, LOOK).
2. **test_desk:** 6 failing, 27 of 28 tests LOOK, 11,472 executed pixel assertions in 1 s. The file has never been edited since the import.
3. **test_model_settings:** the only failing BEHAVIOUR tests (5). The cause is out-of-date test setup, not a proven fault in the program.
4. **test_desk_scenes (62 s):** plays the same P01 scene through `desk_scene.run_scene` that the out-of-repo check plays again through `tools/campaign.py --set scenes` (tools/campaign_lib/cases_scene.py:1-24; test_desk_scenes.py:1-11).
5. **test_system_menu:**
   - 2 failing tests and the tautology at :511.
   - The 'Programs' wording at :386.
   - Its slowest tests, in the RealWindowLeaveTests class, build a whole window per test (test_system_menu.py:292-307). The two tests take 18 s and vary 4–12 s between runs.
6. **test_paper:** 4 failing tests, and 7 tests copied from test_hardware_settings.
7. **test_graphite.py:329:** pins version '0.1' and hides a contradiction with test_writing_line.
8. **test_campaign:** 15 s, of which 14 s is class setup, to test a developer tool (tools/campaign.py), not the program.

## Per module (sorted by 0.8.2 seconds; * = not focused)
| module | tests | s 0.8.2 | s runs 1/2/3 | B/C/L/T | asserts static / executed | failing | edits after import / with look files |
|---|---|---|---|---|---|---|---|
| test_desk_acts | 28 | 189.7 | 190.9/193.1/191.0 | 19/6/0/3 | 226 / 1474 | 0 | 2 / 0 |
| test_desk_scenes | 5 | 62.7 | 62.3/62.7/62.5 | 5/0/0/0 | 29 / 55 | 0 | 2 / 0 |
| test_context_menu | 44 | 61.9 | 64.7/65.4/63.5 | 30/2/6/6 | 299 / 1952 | 0 | 2 / 2 |
| test_system_menu | 32 | 17.9 | 28.0/19.3/18.4 | 24/1/4/3 | 215 / 274 | 2 | 0 / 0 |
| test_campaign | 23 | 15.4 | 16.0/15.9/15.2 | 20/3/0/0 | 117 / 258 | 0 | 3 / 0 |
| test_slate_reasoning | 12 | 10.9 | 11.7/11.3/11.4 | 12/0/0/0 | 72 / 72 | 0 | 0 / 0 |
| test_graphite | 31 | 7.9 | 8.5/7.9/8.2 | 5/2/17/7 | 135 / 403 | 3 | 2 / 2 |
| test_continuing_work | 13 | 6.3 | 5.7/6.1/5.9 | 13/0/0/0 | 108 / 225 | 0 | 0 / 0 |
| test_deployment | 16 | 5.7 | 7.0/6.5/5.7 | 16/0/0/0 | 69 / 69 | 0 | 0 / 0 |
| test_release_check | 22 | 5.5 | 5.8/6.5/6.0 | 13/9/0/0 | 133 / 270 | 0 | 0 / 0 |
| test_model_settings | 13 | 5.2 | 5.6/5.5/5.4 | 13/0/0/0 | 108 / 136 | 5 | 1 / 0 |
| test_agent_loop | 24 | 4.9 | 5.1/5.3/5.2 | 22/1/0/1 | 311 / 494 | 0 | 0 / 0 |
| test_readiness | 10 | 4.8 | 4.8/4.8/4.8 | 10/0/0/0 | 23 / 25 | 0 | 0 / 0 |
| test_launcher | 17 | 4.5 | 4.7/4.7/4.7 | 9/4/1/3 | 200 / 1453 | 0 | 2 / 2 |
| test_network_watch | 50 | 4.3 | 4.2/4.1/4.1 | 46/2/0/2 | 360 / 1999 | 0 | 0 / 0 |
| test_change_sets | 12 | 4.1 | 4.3/4.8/4.2 | 12/0/0/0 | 74 / 80 | 0 | 0 / 0 |
| test_project_desk | 11 | 3.9 | 3.8/3.7/3.8 | 11/0/0/0 | 48 / 55 | 0 | 0 / 0 |
| test_discovery | 13 | 3.8 | 3.6/3.9/4.0 | 13/0/0/0 | 75 / 99 | 0 | 0 / 0 |
| test_explore | 13 | 3.7 | 3.6/3.7/3.6 | 12/1/0/0 | 65 / 84 | 0 | 0 / 0 |
| test_model_turn | 28 | 3.6 | 3.7/3.7/3.7 | 27/0/0/1 | 184 / 243 | 0 | 0 / 0 |
| test_tool_atlas | 8 | 3.6 | 3.6/3.6/3.6 | 7/1/0/0 | 37 / 1713 | 0 | 0 / 0 |
| test_stacy_start | 14 | 3.2 | 5.8/3.2/3.2 | 13/0/0/1 | 58 / 101 | 0 | 3 / 2 |
| test_profile_files | 16 | 3.1 | 3.2/3.4/3.3 | 14/2/0/0 | 168 / 323 | 0 | 0 / 0 |
| test_resource_rules | 15 | 2.9 | 3.1/3.2/3.2 | 15/0/0/0 | 74 / 92 | 0 | 2 / 0 |
| test_writing_line | 32 | 2.8 | 2.7/2.8/2.8 | 25/1/2/4 | 203 / 380 | 0 | 5 / 4 |
| test_settings_registry | 19 | 2.5 | 2.9/2.9/2.7 | 18/1/0/0 | 130 / 275 | 0 | 0 / 0 |
| test_presentation_settings | 16 | 2.4 | 2.8/2.8/2.7 | 15/1/0/0 | 108 / 138 | 0 | 0 / 0 |
| test_problem | 7 | 2.3 | 2.3/2.1/2.2 | 7/0/0/0 | 27 / 31 | 0 | 0 / 0 |
| test_settings_advanced | 15 | 2.2 | 2.7/2.5/2.4 | 15/0/0/0 | 105 / 139 | 0 | 0 / 0 |
| test_conditions | 16 | 2.0 | 2.4/2.4/2.2 | 16/0/0/0 | 194 / 360 | 0 | 1 / 1 |
| test_operations | 16 | 1.9 | 2.0/2.1/1.9 | 15/0/0/1 | 101 / 137 | 0 | 0 / 0 |
| test_paper | 17 | 1.9 | 2.0/1.9/2.1 | 7/1/9/0 | 161 / 191 | 4 | 0 / 0 |
| test_hardware_settings | 8 | 1.8 | 2.0/2.3/2.1 | 8/0/0/0 | 99 / 138 | 0 | 0 / 0 |
| test_memory_settings | 9 | 1.8 | 1.8/1.9/1.9 | 9/0/0/0 | 69 / 114 | 0 | 0 / 0 |
| test_algorithm_atlas | 10 | 1.6 | 1.5/1.6/1.7 | 9/1/0/0 | 52 / 184 | 0 | 0 / 0 |
| test_cabinet | 14 | 1.6 | 1.6/1.7/1.7 | 13/1/0/0 | 98 / 162 | 0 | 0 / 0 |
| test_documents | 13 | 1.5 | 1.5/1.3/1.4 | 12/1/0/0 | 132 / 165 | 0 | 0 / 0 |
| test_service_lifecycle | 23 | 1.5 | 1.8/1.8/1.6 | 23/0/0/0 | 115 / 140 | 0 | 0 / 0 |
| test_exact_math | 6 | 1.4 | 1.5/1.4/1.4 | 6/0/0/0 | 23 / 26 | 0 | 0 / 0 |
| test_memory_cabinet | 9 | 1.4 | 1.6/1.5/1.4 | 9/0/0/0 | 64 / 92 | 0 | 0 / 0 |
| test_startup_scripts | 14 | 1.4 | 1.5/1.5/1.5 | 12/2/0/0 | 85 / 101 | 0 | 0 / 0 |
| test_workspace_backup | 7 | 1.3 | 1.7/1.3/1.4 | 7/0/0/0 | 32 / 32 | 0 | 0 / 0 |
| test_cabinet_actions | 9 | 1.2 | 1.2/1.2/1.1 | 8/1/0/0 | 52 / 76 | 0 | 0 / 0 |
| test_desk | 28 | 1.2 | 1.1/0.9/1.1 | 1/0/27/0 | 134 / 11472 | 6 | 0 / 0 |
| test_machine | 6 | 1.2 | 1.4/1.2/1.4 | 5/0/0/1 | 81 / 105 | 0 | 0 / 0 |
| test_related | 11 | 1.2 | 1.4/1.3/1.1 | 10/0/0/1 | 132 / 147 | 0 | 0 / 0 |
| test_return_thread | 9 | 1.2 | 1.3/1.2/1.2 | 9/0/0/0 | 39 / 63 | 0 | 0 / 0 |
| test_frame | 11 | 1.1 | 1.0/0.9/1.2 | 1/1/6/3 | 55 / 65 | 0 | 1 / 1 |
| test_browse | 6 | 0.9 | 0.8/0.8/0.8 | 5/1/0/0 | 72 / 74 | 0 | 0 / 0 |
| test_kasandra | 20 | 0.9 | 1.1/1.1/1.1 | 9/2/8/1 | 82 / 102 | 0 | 4 / 4 |
| test_vocabulary | 9 | 0.9 | 0.8/0.8/0.9 | 5/0/0/4 | 33 / 36 | 0 | 0 / 0 |
| test_continue_setting | 2 | 0.8 | 1.0/0.9/1.0 | 2/0/0/0 | 13 / 18 | 0 | 0 / 0 |
| test_joined_work | 9 | 0.8 | 0.7/0.7/0.7 | 9/0/0/0 | 40 / 55 | 0 | 0 / 0 |
| test_tool_selection | 5 | 0.8 | 0.8/0.9/0.8 | 5/0/0/0 | 37 / 86 | 0 | 0 / 0 |
| test_adaptive_contract | 14 | 0.7 | 0.8/0.7/0.7 | 12/2/0/0 | 22 / 29 | 0 | 0 / 0 |
| test_faces_find_light | 34 | 0.7 | 0.7/0.8/0.7 | 12/2/16/4 | 149 / 417 | 0 | 9 / 7 |
| test_reasoning_graph | 7 | 0.7 | 0.7/0.7/0.7 | 7/0/0/0 | 18 / 23 | 0 | 0 / 0 |
| test_install_media | 17 | 0.3 | 0.3/0.4/0.3 | 17/0/0/0 | 103 / 155 | 0 | 0 / 0 |
| test_stacy_hand | 19 | 0.1 | 0.1/0.1/0.1 | 19/0/0/0 | 91 / 401 | 0 | 3 / 2 |
| test_exact_math_solvers * | 2 | – | 5.6/4.3/4.2 | 2/0/0/0 | 7 / 10 | 0 | 0 / 0 |
| protocol_fixture * (helper) | 0 | – | – | – | – | – | 0 / 0 |

## Method and limits
- **How the runs were done:** one module per process, each in its own pid namespace at nice 19, HOME set to a fresh folder per run, never more than two test processes at once. Per-test seconds come from unittest's own test timing hook. "Executed" assertions come from wrapping every `assert*` method in the counting run.
- **Kinds are a judgement:** each module has a default kind with named exceptions (kinds_hand.txt), read from test names and assertion bodies, not every line of every test. Where it could go either way, the cat's pose machine and the menu order count as LOOK.
- **Near-duplicates:** found two ways (the same assertion in two modules; similar test bodies), then read by hand.
- **Imports:** the per-test list is the names each test uses. The runtime list is what the module's process had loaded.
- **Churn:** covers only the 80 commits in git, since the import of 0.2a13.
- **Timing:** taken while another session was building on the same machine.