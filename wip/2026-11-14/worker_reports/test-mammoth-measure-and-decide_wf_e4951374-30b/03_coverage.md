# Coverage of workbench/ by each test module (d1df337)

Every focused module ran under coverage, and the 20 failures came out exactly the same as the baseline (`modules_082.json`), test id for test id. Of the 20 failing tests, 16 add no line that another test doesn't already run. One runs no workbench line inside its own test method. The other three add 11 lines between them.

## How it ran
- **Copy:** `git archive d1df337` into `.../testclean/coverage/tree`. coverage.py 7.17.3 is installed in `.../testclean/coverage/lib`.
- **Process:** each module ran alone with `nice -n 19 unshare --pid --fork --mount-proc --kill-child python -B -m unittest -v tests_integrated.<m>`. No more than two ran at once, and each had a fresh empty HOME.
- **Coverage settings:** branch on, `source=<tree>/workbench`, parallel data files, the module name as the static context, and the test method as the dynamic context.
- **How coverage started:** `boot/sitecustomize.py` starts it in the main process. It also starts in any Python child that inherits the environment. That sitecustomize first runs the image's own sitecustomize (the zlib fix).
- **Scope:** the 59 focused modules plus `test_exact_math_solvers`, which is not in the focused set: 60 modules, 939 tests.
- **Wall time:** 4 min 44 s for the main run. A second run (4 min 32 s) measured code outside workbench (tools/, sdk/, root scripts) so that modules testing that code are not wrongly scored as useless.
- **Overhead:** per-module seconds add up to 562 s under coverage, against 488 s in the baseline (about +15%).

## Headline numbers (workbench/, 468 files)

| | All 60 modules | 59 focused |
|---|---|---|
| Statements covered (of 90,533) | 42,545 (47.0%) | 42,458 (46.9%) |
| Branches covered (of 34,982) | 11,470 (32.8%) | 11,418 (32.6%) |
| Function-body statements covered (of 76,851) | 30,596 (39.8%) | 30,509 |

"Function-body" lines run only when a function is called. The full statement figure is inflated: just importing workbench runs about 5,000–6,000 module-level lines in every module.

- **Files:**
  - 386 of 468 files run at all.
  - 325 run at least one function body.
  - 82 are never imported (11,179 statements).
  - 57 are imported but none of their functions ever run (5,132 body statements).
- **Functions in files that do run:** 7,151, of which 3,215 are never called (31,448 statements).
- **Tests:** 839 of 939 run at least one workbench line inside their own test method; 100 run none. 72 of those 100 are in modules that test code outside workbench: test_campaign 23, test_release_check 19, test_install_media 17, test_startup_scripts 13.
- **Lines no other test runs, per test:** 441 tests have 0, 234 have 1–5, 102 have 6–20, 51 have 21–100, and 11 have more than 100.
- **Smallest set of tests that still covers everything** (greedy pick over the 27,378 body lines run inside test methods):

| Share of those lines | Tests needed |
|---|---|
| 50% | 2 |
| 80% | 27 |
| 90% | 67 |
| 95% | 123 |
| 99% | 268 |
| 100% | 432 |

## The 20 failing tests
- **16 add no line of their own:** all 6 in test_desk, all 5 in test_model_settings, 3 of 4 in test_paper, test_public_name_and_internal_identities and test_the_colours_are_named_constants_and_the_coat_is_warm_paper.
- **test_palette_is_graphite_paper_eraser_and_pencil_only** runs no workbench line inside its own test method.
- **Only three add lines of their own** (11 in total):
  - test_the_band_places_the_cat_by_its_pale_coat: `workbench/graphite_brand.py:360-361` (`cat_ink`).
  - test_reduce_motion_is_static_with_no_timer_and_the_setting_hides_the_mark: `workbench/writing_marker.py:304-306`, `319-320` and `324-325` (the reduce-motion branch of `tick`, then `readback` and `stats`).
  - test_the_two_menus_are_point_mirror_images: `workbench/programs_qt.py:120-121` (the lower-left placement).
- **Caveat:** a failing test stops at its first failed assertion, so these figures show only what ran before the failure. Fixing a test could add coverage past that point.

## (2) Per test module

"Unique" means no other module runs that line. The last column is the single other module that runs the largest share of this module's body lines.

| module | tests | s (base) | body lines | unique body | unique branches | unique lines outside workbench | most overlapping module (body %) |
|---|---|---|---|---|---|---|---|
| test_desk_acts | 28 | 189.7 | 18,197 | 4,011 | 1,067 | 16 | test_desk_scenes 62.7 |
| test_context_menu | 44 | 61.9 | 13,572 | 1,504 | 568 | 40 | test_desk_acts 83.2 |
| test_network_watch | 50 | 4.3 | 2,480 | 677 | 379 | 0 | test_agent_loop 49.7 |
| test_deployment | 16 | 5.7 | 2,260 | 526 | 213 | 493 | test_continuing_work 69.3 |
| test_change_sets | 12 | 4.1 | 2,803 | 507 | 253 | 0 | test_slate_reasoning 59.9 |
| test_continuing_work | 13 | 6.3 | 2,420 | 466 | 220 | 0 | test_deployment 64.7 |
| test_model_turn | 28 | 3.6 | 1,492 | 224 | 133 | 0 | test_context_menu 77.8 |
| test_writing_line | 32 | 2.8 | 1,286 | 206 | 96 | 51 | test_context_menu 62.7 |
| test_discovery | 13 | 3.8 | 1,670 | 199 | 105 | 0 | test_exact_math 68.3 |
| test_project_desk | 11 | 3.9 | 1,375 | 188 | 89 | 20 | test_slate_reasoning 76.4 |
| test_profile_files | 16 | 3.1 | 1,728 | 179 | 85 | 0 | test_agent_loop 71.0 |
| test_resource_rules | 15 | 2.9 | 1,462 | 175 | 69 | 194 | test_model_settings 76.1 |
| test_agent_loop | 24 | 4.9 | 2,456 | 170 | 97 | 0 | test_conditions 59.6 |
| test_slate_reasoning | 12 | 10.9 | 2,146 | 170 | 105 | 0 | test_change_sets 78.3 |
| test_joined_work | 9 | 0.8 | 423 | 155 | 92 | 0 | test_adaptive_contract 62.2 |
| test_service_lifecycle | 23 | 1.5 | 1,361 | 148 | 66 | 0 | test_context_menu 84.8 |
| test_documents | 13 | 1.5 | 1,512 | 147 | 100 | 0 | test_context_menu 87.8 |
| test_system_menu | 32 | 17.9 | 7,762 | 142 | 82 | 0 | test_context_menu 96.7 |
| test_workspace_backup | 7 | 1.3 | 1,110 | 140 | 58 | 0 | test_deployment 72.3 |
| test_faces_find_light | 34 | 0.7 | 1,299 | 139 | 75 | 0 | test_desk_acts 89.1 |
| test_kasandra | 20 | 0.9 | 312 | 134 | 54 | 0 | test_desk_scenes 56.7 |
| test_graphite | 31 | 7.9 | 783 | 122 | 29 | 0 | test_desk_acts 71.1 |
| test_conditions | 16 | 2.0 | 1,604 | 108 | 63 | 0 | test_agent_loop 91.2 |
| test_memory_cabinet | 9 | 1.4 | 1,012 | 104 | 58 | 0 | test_cabinet 83.1 |
| test_stacy_start | 14 | 3.2 | 112 | 96 | 35 | 0 | test_desk_scenes 14.3 |
| test_readiness | 10 | 4.8 | 261 | 92 | 28 | 0 | test_model_settings 62.5 |
| test_related | 11 | 1.2 | 1,471 | 91 | 48 | 0 | test_context_menu 87.3 |
| test_desk_scenes | 5 | 62.7 | 11,551 | 87 | 51 | 0 | test_desk_acts 98.8 |
| test_exact_math_solvers (not focused) | 2 | – | 379 | 87 | 52 | 0 | test_exact_math 75.7 |
| test_settings_registry | 19 | 2.5 | 1,310 | 84 | 71 | 0 | test_settings_advanced 90.3 |
| test_settings_advanced | 15 | 2.2 | 1,304 | 79 | 37 | 0 | test_settings_registry 90.7 |
| test_machine | 6 | 1.2 | 1,029 | 68 | 41 | 0 | test_desk_acts 92.2 |
| test_memory_settings | 9 | 1.8 | 1,181 | 66 | 40 | 36 | test_paper 90.6 |
| test_operations | 16 | 1.9 | 1,295 | 57 | 29 | 0 | test_context_menu 88.6 |
| test_adaptive_contract | 14 | 0.7 | 445 | 54 | 39 | 0 | test_discovery 78.2 |
| test_exact_math | 6 | 1.4 | 1,594 | 53 | 18 | 0 | test_problem 81.7 |
| test_reasoning_graph | 7 | 0.7 | 263 | 52 | 32 | 0 | test_algorithm_atlas 72.6 |
| test_problem | 7 | 2.3 | 1,363 | 49 | 18 | 0 | test_exact_math 95.6 |
| test_paper | 17 | 1.9 | 1,335 | 47 | 25 | 0 | test_desk_acts 87.7 |
| test_stacy_hand | 19 | 0.1 | 227 | 46 | 43 | 0 | test_desk_acts 79.3 |
| test_tool_atlas | 8 | 3.6 | 957 | 42 | 16 | 0 | test_desk_acts 89.2 |
| test_desk | 28 | 1.2 | 322 | 40 | 19 | 0 | test_system_menu 82.9 |
| test_launcher | 17 | 4.5 | 1,616 | 38 | 16 | 0 | test_desk_acts 93.9 |
| test_algorithm_atlas | 10 | 1.6 | 1,117 | 29 | 22 | 0 | test_discovery 90.8 |
| test_cabinet | 14 | 1.6 | 1,370 | 21 | 10 | 17 | test_cabinet_actions 84.0 |
| test_presentation_settings | 16 | 2.4 | 1,198 | 19 | 13 | 9 | test_settings_registry 97.3 |
| test_startup_scripts | 14 | 1.4 | 41 | 18 | 4 | 0 (it tests bash scripts) | test_graphite 56.1 |
| test_return_thread | 9 | 1.2 | 752 | 17 | 17 | 0 | test_paper 93.9 |
| test_browse | 6 | 0.9 | 645 | 13 | 9 | 0 | test_context_menu 96.4 |
| test_hardware_settings | 8 | 1.8 | 1,169 | 13 | 13 | 0 | test_paper 98.5 |
| test_model_settings | 13 | 5.2 | 1,543 | 10 | 13 | 0 | test_context_menu 73.0 |
| test_frame | 11 | 1.1 | 1,139 | 9 | 7 | 0 | test_context_menu 94.6 |
| test_vocabulary | 9 | 0.9 | 171 | 6 | 6 | 0 | test_context_menu 96.5 |
| test_cabinet_actions | 9 | 1.2 | 1,214 | 5 | 6 | 0 | test_cabinet 94.8 |
| test_explore | 13 | 3.7 | 1,162 | 4 | 4 | 0 | test_launcher 96.7 |
| test_release_check | 22 | 5.5 | 303 | 2 | 2 | 243 (tools/check_*.py) | test_workspace_backup 91.7 |
| test_tool_selection | 5 | 0.8 | 311 | 1 | 3 | 0 | test_model_turn 98.7 |
| test_campaign | 23 | 15.4 | 0 | 0 | 0 | 659 (tools/campaign_lib) | – |
| test_install_media | 17 | 0.3 | 0 | 0 | 0 | 282 (INSTALL_LS.py, tools/package_release_parts.py) | – |
| test_continue_setting | 2 | 0.8 | 1,040 | 0 | 0 | 0 | test_settings_registry 99.2 |

What this means for running and rerunning:
- **Three modules take most of the time.** test_desk_acts, test_desk_scenes and test_context_menu take 314 of the 488 s (64%). Without them the suite takes 173 s and still runs 69.8% of the body lines.
- **test_desk_scenes adds almost nothing.** It costs 62.7 s for 87 lines of its own; 98.8% of its body lines also run in test_desk_acts. Its 5 tests play the same P01 scene (by keys, by mouse, reduced motion, small window) and add only 3, 2, 2, 0 and 0 lines no other test runs. Dropping it keeps 99.71% of body lines and saves 62.7 s.
- **One test holds most of test_desk_acts' own coverage.** `LiveActs.test_every_navigation_changes_nothing` alone has 4,258 lines no other test runs.
- **Greedy pick of modules:**

| Share of body lines | Modules needed | Baseline seconds |
|---|---|---|
| 97.6% | 38 | 352 |
| 99% | 43 | 380 |
| 100% | 56 | 471 |

- **test_continue_setting** adds no line anywhere, inside or outside workbench. 99.2% of its body lines also run in test_settings_registry.
- **Close to nothing of their own:** test_tool_selection (1 line), test_release_check (2 in workbench, but 243 in tools), test_explore (4 lines, 3.7 s), test_cabinet_actions (5), test_vocabulary (6), test_frame (9), test_model_settings (10 lines, 5.2 s; its 5 failing tests add none).
- **Not redundant despite zero workbench coverage:** test_campaign and test_install_media test code outside workbench (659 and 282 lines of their own there).

These figures measure line coverage, not how strong the assertions are. The mutation step should confirm any retirement.

## (1) Per source module
`per_source.json` has, for each file: statements, covered lines, branches, body statements, the covering test modules with their line counts, and the lines only one module covers.

The largest uncovered parts of files that do run (uncovered body statements / total body statements):

| File | Uncovered / total |
|---|---|
| qt_app.py | 3,135 / 4,098 |
| shell2.py | 1,047 / 2,486 |
| engineering_kernel.py | 628 / 981 |
| universal_view.py | 462 / 564 |
| reference_service.py | 440 / 445 |
| intake_service.py | 382 / 397 |
| local_brain.py | 373 / 755 |
| concern_qt.py | 370 / 478 |
| context_menu.py | 352 / 1,664 |

## (3) Code no test runs
The 82 never-imported modules (11,179 statements), sorted by how the rest of the tree refers to them:

| How they are referred to | Files | Statements | Examples |
|---|---|---|---|
| No code names them (only MANIFEST.json): likely dead | 5 | 1,039 | `workbench/app.py` (750; line 1 says "ARC-1 Workbench R08: orange Aqua visual design"; `START_OFFICE.sh:7-8` launches `workbench.launch` instead), `stacy_presence.py` 147, `unix_setup.py` 93, `owner_tls.py` 47, `stac/__main__.py` 2 |
| Imported only by modules that are themselves never run (a dead chain, or untested) | 10 | 1,713 | `sheet_workbench_qt.py` 654 (only from `universal_viewer_qt.py:143`), `stac/cli.py` 262, `joined_checks.py` 225, `workspaces.py` 63 (only from app.py) |
| Started by path or `-m` (standalone checks and tools) | 22 | 2,111 | `setup_arc1.py` 477, `adaptive_checks.py` 262, `arcfairy_qt.py` 258, `lab_checks.py` 169 |
| Lazily imported by code that runs, on paths no test takes (untested) | 43 | 6,019 | `genesis_tab.py` 398, `pdf_qt.py` 331, `universal_viewer_qt.py` 313, `console_tab.py` 247 (`qt_app.py:4350`, `4919`) |
| Imported only from sdk/ | 2 | 297 | `agent.py`, `imagebuild.py` (via `sdk/cli/arc1cli/main.py`) |

Never-called functions inside files that run (3,215 functions, 31,448 statements):

| Kind | Functions | Statements |
|---|---|---|
| Name used elsewhere in the tree (untested) | 2,749 | 27,688 |
| Nested | 213 | 872 |
| Qt or standard-library hook | 140 | 1,122 |
| Protocol method | 92 | 1,637 |
| Name appears nowhere else (likely dead) | 21 | 129 |

The 21 likely-dead functions include:
- `stac/quantities.py:115 assess_upper_bound` (28 statements)
- `rooms.py:116 add_live_tree` (22)
- `shell2.py:674 TopBar.plan_menus` (13)
- `view_modules/markdown_view.py:26 living` (13)
- `shell2.py:358 quiet_icon` (10)
- `explore_qt.py:191 fill_capability_groups` (7)
- `explore_qt.py:182 group_menus` (5)
- `stac/evidence.py:71-97`: `negate`, `truth_and`, `truth_or`, `knowledge_meet`

`host_service.py:302 handle_error` is a false positive: socketserver calls it.

## (4) Line map
`line_map.json` has this shape:
```
{"modules": [60 names; a module's index is its position],
 "files": {"workbench/x.py": {"<line>": [module indexes]}},
 "statements": {"workbench/x.py": [every statement line]}}
```
It covers 386 files and 42,545 covered lines. Index 19 is `test_exact_math_solvers`, which is not in the focused set. A spot check holds: `graphite_brand.py:360` maps to test_graphite only. `test_line_map.json` is the same map at the level of single tests, and `branch_map.json` maps each branch ("a>b") to module indexes.

## Limitations
- **Qt threads are not traced.** The bodies of `QThread.run` aren't traced (`project_tabs.py:18`, `register_tabs.py:36`, `home_qt.py:56`). Python 3.13 cannot measure branches with the tracer that would follow them.
- **Some child processes are not measured.** Children that drop the environment are missed: `test_install_media.py:115` runs `INSTALL_LS.py` with `-I`, and bash scripts aren't Python (`test_startup_scripts.py:49`, `test_network_watch.py:919`). Children that inherit the environment are measured (`test_kasandra.py:202`, `test_release_check.py:305`).
- **Per-test figures understate some tests.** Lines run in `setUp` or `setUpClass` count for the module only, not for the single test.

Every file is in `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/testclean/coverage/`:
- summary.json
- per_source.json
- per_module.json
- per_test.json
- never_executed.json
- line_map.json
- test_line_map.json
- branch_map.json
- greedy.json
- outside_workbench.json
- run_results.json
- run_results_other.json
- logs/, logs_other/ (unittest output)
- data/, data_other/ (raw coverage data, 60 MB)
- scripts/ (run_cov.py, run_cov_other.py, analyze.py, analyze_other.py)
- boot/sitecustomize.py