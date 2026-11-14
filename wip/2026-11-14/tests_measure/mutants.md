# Mutation testing of the focused suite (d1df337): what the tests catch

Of the 156 sampled mutants, 140 ran. 4 of those ran while the disk was full, which leaves **136 valid mutants**. **70 were caught by a test that checks behaviour. 18 more were caught only by a source-digest check, which fails on any change to the file.** 48 survived every module. After setting aside 5 equivalent mutants, that leaves **61 real gaps**.

The behaviour score is **53.4%** (70 of 131 non-equivalent mutants). Counting the digest-only kills as caught, it would be 67.2%.

## How it ran
- **Trees and mutator:** three `git archive d1df337` copies, one pristine and two work trees. The mutator is my own `ast` code with no new dependency. Each mutant is a minimal text edit that keeps line numbers. Only function-body lines are mutated; logging and print calls are never deleted.
- **Mutation kinds:** cmp (flip a comparison), if (negate the condition), ret (return `not X` or `None`), num (constant +1), call (delete a call statement).
- **Sample:** seed 20261114. 102 mutants are in the 17 named files, 6 each. typed_pipeline is `sdk/cli/arc1cli/typed_pipeline.py`, mapped from the coverage part's `data_other`. 54 are spread one per file over the rest.
- **What ran per mutant:** only the modules that cover the line in `line_map.json`. Each ran at nice 19 in `unshare --pid --fork --mount-proc --kill-child`, with a fresh HOME, at most two at once.
  - Failfast was on, and the 20 known failures were excluded.
  - The timeout was 3× the control run's wall time, with a 30 s floor.
- **Control run first:** all 60 modules, unmutated, with the same exclusions. All passed in 499 s, and the trees were unchanged afterwards (`baseline.json`).
- **Deviation 1, the three slow modules:** test_desk_acts, test_desk_scenes and test_context_menu ran only the tests that the per-test map says execute the line. The whole module ran when no single test did. This only lowers their kill counts; it can never add a false kill.
- **Deviation 2, the cut-off:** the run stopped at 140 of 156 mutants, and I tell it as it happened:
  - The deadline was 13:00.
  - Before that, the harness stopped the run once at its 30-minute background limit. I resumed it and re-ran the 2 mutants it lost.
  - At 13:07 the main session stopped it. I restored the trees afterwards (`diff -rq` against the pristine copy is clean).
  - The 16 not run: 3 in change_sets, 2 in context_menu, 2 in local_brain, 1 each in desk_acts, engineering_kernel, line_steps, resource_control and stacy_foundation, and 4 others.
- **Cost:** 548 module runs and 11,062 worker-seconds. test_desk_acts alone took 7,132 s (64%), and test_desk_scenes 1,616 s.

## Two things that would have falsified the matrix
1. **The disk filled up near the end.** At 13:12, `/` had 235 MB free of 252 GB. My own files were under 1 GB; most of the space went to other parts of the work.
   - 14 module verdicts failed with `OSError: [Errno 28] No space left on device` or `disk I/O error`. I voided them.
   - Mutants with no other verdict are void: M013, M074, M075 and M135.
   - **Any later run on this machine will fail the same way until space is freed.**
2. **Digest kills.** `project/stacy_seed/current/manifest.json` records the sha256 of 345 `.py` files. Changing any byte of one of them makes the seed "not current", so the line panel cannot read its source.
   - Three broad tests then fail the same way, whatever the mutant did:
     - test_desk_acts: `then.keep` → "This line panel offers no rows to keep." (`workbench/desk_doers.py:1039`, raised through `tests_integrated/test_desk_acts.py:330`).
     - test_desk_scenes: `menu.panel.preview` comes back `[]`.
     - test_context_menu: the ops list lacks `ledger.address.read` (`tests_integrated/test_context_menu.py:824`).
   - 22 of the 23 files killed this way are in that manifest; none of the 16 survivor files are.
   - Re-running M091, a one-byte change to a 32 MB bound, failed the same way again, while the unmutated control passed (`recheck.json`).
   - So these 60 module verdicts (code D in the matrix) count as detection of the edit, not of the behaviour. **A comment edit would be "killed" the same way.**

## Results
| | Detected | Digest only | Equivalent | Gaps (real / low / boundary) | Void |
|---|---|---|---|---|---|
| Named files (90) | 47 | 9 | 5 | 35 | 3 |
| Others (50) | 23 (1 by timeout) | 9 | 0 | 26 | 1 |
| **Total (140)** | **70** | **18** | **5** | **61 (44 / 8 / 9)** | **4** |

"Digest only" mutants are counted again among the gaps; they make up 17 of the 61.

**By kind:**

| Kind | Detected | Gaps |
|---|---|---|
| num | 3 of 26 | 23 |
| ret | 18 | 7 |
| cmp | 17 | 9 |
| if | 17 | 10 |
| call | 15 | 12 |

Numeric constants are close to unguarded.

**Named files:**
- **Weakest:** resource_control (1 detected, 4 gaps), change_sets (0 detected, 2 gaps, 1 equivalent), field_page (2/3), field_ripple (3/3), desk_doers (2/3), continuing_work (3/3), typed_pipeline (3/3).
- **Strongest:** stacy_hand 5/1, release_integrity 5/1, stacy_foundation 3/2.

## Per module (behaviour kills; D = digest kills)
| Module | Mutants covered | Killed | D | Unique |
|---|---|---|---|---|
| test_desk_acts | 86 | 27 | 28 | **9** |
| test_context_menu | 49 | 17 | 14 | 5 |
| test_release_check | 11 | 7 | 0 | 4 |
| test_continuing_work | 19 | 9 | 0 | 3 |
| test_slate_reasoning, test_change_sets, test_model_settings, test_service_lifecycle | 17, 14, 16, 10 | | | 2 each |
| **test_desk_scenes** | 52 | 13 (+1 timeout) | 18 | **1** |

test_desk_scenes' one unique kill is M033, the deleted Return key press at `desk_doers.py:381`. It cost 1,616 worker-seconds.

**Modules with one unique kill:** test_system_menu, test_stacy_hand, test_cabinet, test_deployment, test_resource_rules, test_workspace_backup, test_conditions, test_operations, test_faces_find_light, test_graphite, test_joined_work, test_kasandra and test_stacy_start (a timeout).

**Modules with zero unique kills (35):**
- **Covering 7 or more sampled mutants, and still none unique:** test_project_desk (14 covered / 6 killed), test_network_watch (12/4), test_launcher (9/5), test_profile_files (9/4), test_explore (8/5), test_tool_atlas (8/3), test_agent_loop (8/2), test_memory_settings (8/3), test_machine (7/3), test_paper (7/2), test_presentation_settings (7/3), test_settings_registry (7/2), test_discovery (7/4).
- **Too few sampled mutants to judge:** test_adaptive_contract, test_algorithm_atlas, test_browse, test_cabinet_actions, test_continue_setting, test_desk, test_documents, test_exact_math, test_exact_math_solvers, test_frame, test_hardware_settings, test_memory_cabinet, test_model_turn, test_problem, test_readiness, test_reasoning_graph, test_related, test_return_thread, test_settings_advanced, test_tool_selection, test_vocabulary, test_writing_line.
- **No sampled mutant covered at all** (they test code outside workbench): test_campaign, test_install_media, test_startup_scripts.

**Most kills by one test** (these counts include digest kills): `LiveActs.test_every_navigation_changes_nothing` 40, `PlayableScene.test_p01_by_keys` 25, `Window.test_opening_reads_nothing_and_the_line_panel_reads_once` 15. Many of these are digest kills.

## The 44 real gaps (behaviour that no test guards)
- **Resource rules:**
  - `resource_control.py:187`: the one-coordinator rule is inverted.
  - `:167`: a live resident model's reservation is dropped from the memory view.
  - `:62`: the owner's foreground reserve is ignored when a model starts (`local_brain.py:509`).
- **Change sets:**
  - `change_sets.py:269`: the temporary file of a file two or more folders deep is looked for in the wrong folder.
  - `:444`: undo no longer clears retained temporaries.
- **Continuing work:**
  - `continuing_work.py:724`: pausing or revoking an adaptive investigation no longer stops its branches.
  - `:231`: a new order starts with rounds_used=1.
  - `:533`: the retry back-off schedule changes.
- **The Field:**
  - `field_ripple.py:39`, `:65`, `:71`: whatever ripple computes is never asserted; only crashes are caught.
  - `field_doubt.py:526`: doubts_for returns None.
  - `field_page.py:684`: opening an object no longer leaves the Field.
  - `field_page.py:57`: face_chosen is no longer connected.
  - `field_page.py:715`: reviewed_rows returns None on a refused read.
- **Desk acts and doers:**
  - `desk_acts.py:372`: plan_variants is empty.
  - `desk_doers.py:829`: "by keys" and "direct" are swapped.
  - `desk_doers.py:180`: surface() loses 'home'.
  - `desk_doers.py:972`: the fallback click point lands off the viewport.
- **The line and typed_pipeline:**
  - `sdk/cli/arc1cli/typed_pipeline.py:125`: `add` loses every operator.
  - `typed_pipeline.py:116`: `+` takes the precedence of `*`.
- **Files and records:**
  - `files_service.py:259`: text cells are not read as numbers.
  - `files_service.py:331`: added diff lines are numbered one too high.
  - `record_io.py:61`: `.ledger/.hidden` is accepted as a private path.
- **Seed:**
  - `stacy_foundation.py:359`: carried() is inverted, so staC would run on a seed missing `.py` files. Only the digest notices.
- **Stacy:**
  - `stacy_hand.py:185`: quotes around the contents of a made file are no longer stripped.
- **Other:**
  - `memory_settings.py:91`: an undo no longer marks the earlier record undone.
  - `idle_display_qt.py:80`: the idle screen never listens for input.
  - `rooms.py:179`: "N arrived" is dropped from the status line.
  - `context_menu.py:1441`: "Compare with Rev" names the wrong item.
  - `view_modules/images_plus.py:21`: HEIF/AVIF files are no longer recognised as images.
  - `evidence_compiler.py:29`: the receipts table is never created.
- **Qt tabs caught only by the digest:** `knowledge_qt.py:147`, `program_rooms_qt.py:161`, `explore_qt.py:313`, `memory_qt.py:85`, `discovery_qt.py:64`, `writing_marker.py:240`, `empty_workspace_qt.py:49`, `machine_overview.py:553`, `kibot_tools.py:320`, `office_qt.py:348`, `typebar_qt.py:383`, `reading_preferences.py:22`.

**Low (drawing or style only):** `pane_qt.py:359`, `glyph_set.py:399`, `trash_can_qt.py:121`, `programs_qt.py:166`, `field_model.py:314`, `arc_desktop.py:363`, `model_settings.py:143` (a field nothing reads), `release_integrity.py:28` (the 4 MiB cap).

**Boundary (a limit moved by one unit):** `engineering_kernel.py:1241`, `local_brain.py:260`, `model_settings.py:66`, `line_steps.py:142`, `line_steps.py:242`, `resource_control.py:172`, `stac_bridge.py:66`, `stacy_foundation.py:256`, `typed_pipeline.py:53`.

**Equivalent, set aside (5):**
- `desk_acts.py:230`: `split('.', 2)[0]` gives the same first field as `split('.', 1)[0]`.
- `engineering_kernel.py:825`: `BEGIN IMMEDIATE` is redundant under the flock in `database_guard.py:18-37`.
- `change_sets.py:317`: the directory fsync only matters on a power cut.
- `field_page.py:282`: a 1 ms change to a status-bar timeout.
- `desk_doers.py:1020`: a fallback click point moved by 1 px.

## What this means for running and rerunning
- **test_desk_scenes** has 1 unique kill for 62 s per run, and 18 of its 31 kills are digest kills. It is the clearest case for leaving the per-commit run (moving it to a release-only run).
- **test_desk_acts** holds 9 of the unique kills. Most of them come from one 107 s test, `test_every_navigation_changes_nothing`; keep that test.
- **The digest coupling makes the GUI suites look stronger than they are.** A direct test that the seed is current (test_project_desk already has one) would let these suites fail only on behaviour.

## Not verified
- Survivors whose slow-module verdict came from a restricted run were not re-run in full; the main session stopped the run before that step. These are listed per gap in `slow_modules_restricted`.
- Kills were checked again only for M091.

## Data files (in `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/testclean/mutants/`)
- `kill_matrix.json`: summary, per_module, the matrix (K/S/T/D/E), every mutant, survivors_gaps, survivors_equivalent and killer_tests.
- `results.jsonl`: raw per-mutant module verdicts.
- `sample.json` (156 mutants), `classify.json` (hand classification), `baseline.json` (the control run), `recheck.json`, `seed_manifest_py.json`, `sdk_line_map.json`, `pool_counts.json`.
- `scripts/`: `mutator.py`, `sample.py`, `run_mutants.py`, `runmod.py`, `mutlib.py`, `analyze.py`, `baseline.py`, `recheck.py`, `show.py`, `cls.py`, `sdk_map.py`.
- `run.log` and `baseline.log`.