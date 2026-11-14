## Failing tests and window checks (part: failing)

### Summary

- **All 20 failing tests are STALE.** None is a code defect, flaky, or caused by this container. Every one fails with the same message at aa0ce07, the first commit (the 0.2a13 import), so all of them broke before the git history begins.
  - With my patches, the five modules pass: test_model_settings 13/13, test_desk 27/27, test_paper 17/17 (in both Graphite and Kasandra), test_graphite 29/29, test_system_menu 31/31. I ported 16 tests and retired 4.
  - I checked that the ported tests still catch real faults: I deliberately broke the code each one guards (the "mutation" runs below), and the tests failed.
- **The five model tests: the behaviour is right.** I checked each against the current code with corrected fixtures:
  - an explicit request overrides the saved defaults;
  - restore uses the previous selection with its old CPU setting;
  - the worker uses the options frozen at request time even after the defaults change;
  - a failed activation restores the previous model and reports it;
  - a restore whose weights changed on disk is stopped and never marked Ready;
  - an owner who cancels while the new model loads gets no automatic restore;
  - a job cancelled before it runs never stops the running model.
  
  The tests went stale because new code was added and the test fixtures were not updated:
  - 0.2a2 added backend fields to the launch settings (`workbench/version.py:47`);
  - 0.2a5 added the check that the model files are still the verified ones, and a cancel check at the start of `run_model_job` (`version.py:44`, `docs/BOSS_IMPLEMENTATION_PLAN.md:118`).
  
  `RECORD_OF_DIRECTIONS.md:318` says the twenty "assert the earlier look, layout and version". That is true for 15 of them, but not for these five.
- **Window checks:** 10 failing gate scripts and 12 the gate does not run.
  - Every one of the 10 gate failures stops at the same line at aa0ce07 as today.
  - 9 of the 12 unrun scripts passed at aa0ce07 and broke later. I bisected three of them to the exact commit (c748812, 94244c2, a95732b).
  - Recommendation: retire or fold 7 gate scripts (2,802 of the 6,522 lines), fix the measuring tool behind check_finder_ui, port check_machine_ui, and fix the code behind check_continue_ui.
  - With my patches applied to a fresh copy (`tree_clean`, manifest rebuilt), all 22 scripts I ran pass: 3 former gate failures, all 12 unrun scripts, and the 7 that already passed (`logs/ui/batch_clean2.txt`).
- **Three defects found:**
  1. The background service's resource check and the model-launch check read the full hardware profile, which starts `dpkg-query`, when they only need free memory.
  2. `tools/ui_fit.py` reports words in the head as cut when the screen captures show them whole.
  3. A menu toggle that does nothing: "Pleasantries in script".
- **Before running the window checks after any source change, rebuild the manifest.** Without `tools/package_graphite.py --manifest-only`, check_context_menu_ui fails at `:335`; after the rebuild it passes. The repository already asks for this at `RECORD_OF_DIRECTIONS.md:353`.

### The 20 tests

| Test | Fails at | Why | Superseded by | Action |
|---|---|---|---|---|
| model_settings `…new_requests_freeze…` | test_model_settings.py:87 | `model_settings.config()` now also returns backend, gpu_layers and cpu_fallback (model_settings.py:64-77). The frozen 6144/6/2048 values are correct. | 0.2a2 backend readback | PORT: compare the three launch keys plus backend AUTO |
| model_settings `…explicit_request_and_restore…` | :92 (then :96) | Same whole-dict comparison | 0.2a2 | PORT: restore asserts backend CPU |
| model_settings `…failed_activation_retains…` | :157 | Restore calls `verify_resident` (local_brain.py:583). The fixture worker has no `verified_files`, so the fixture path's stat fails and the restore is rolled back. Confirmed with `probe/why_restore.py`. | 0.2a5 P08 | PORT: fixture carries verified file stamps, plus one line: changed weights mean no restore |
| model_settings `…owner_cancellation…` | :168 | `check_job` runs first (local_brain.py:506), so a job cancelled before it starts never runs | 0.2a5 P08 | PORT: cancel during the load; plus cancelled before start leaves the model running |
| model_settings `…worker_uses_frozen…` | :185 (error) | `KeyError 'backend'` at local_brain.py:540; the fixture worker lacks backend | 0.2a2 | PORT: fixture worker has backend CPU |
| desk default / owner's width / workspace floor | test_desk.py:26, :48, :37 | Default pane is 268, not 360 (desk_qt.py:31) | BOSS desk, 0.2a1: `BOSS_M1.md:18-20`, `RECORD:80-81` | PORT: rules written in terms of `desk.PANE` |
| desk grain | :111 | `GRAIN_AMPLITUDE = 2` (desk_qt.py:247) gives at most 5 levels | 0.2a1 | PORT: at least 3 levels |
| desk lettering | :116 | Band tone is now `#0c0f0e` | 0.2a1 | PORT: 4.5:1 and 3:1 contrast checked in both appearances |
| desk band colours | :124 | The band has its own colour roles (boss_theme.py:37,48) | 0.2a1, 0.8.0 | RETIRE (test_kasandra covers palettes); the `CAT` line moved to BandTests |
| paper ×4 | test_paper.py:197, 218, 245, 265 | Marker ink is the desk's cream text (writing_marker.py:21) drawn on a 0.1 paper-coloured fixture | "no white box", `RECORD:144-147` | PORT: desk-coloured fixture, ink measured against the background |
| graphite palette | test_graphite.py:75 | Asserts the 0.1 paper palette | 0.2a1 | RETIRE |
| graphite cat on band | :242 | The cat is never shown (typebar_qt.py:259, :579) | `BOSS_M1.md:18-19` | RETIRE |
| graphite public name | :331 | Expects version 0.1 and the mode name "Assignment" | `RECORD:72-74, 182-184` | PORT: name and title; the key stays `slate` |
| system_menu cat colours | test_system_menu.py:528 | Colours of a hidden cat | 0.2a1 | RETIRE |
| system_menu mirrored menus | :503 | The cat list and the System menu are gone; Apps opens from the head (programs_qt.py:701) | 0.7.0, `RECORD:192-202` | PORT to the Apps list placement; nothing else tests it |

### The 10 failing gate scripts

| Script | Stops at | Cause | Action |
|---|---|---|---|
| check_desk_ui (1197 lines) | :145 IndexError | The mirrored 0.1 desk (cat, System symbol, mirrored band words) no longer exists | RETIRE; covered by test_desk and check_finder_ui |
| check_frame_ui | :173 | Expects "Assignment"; four ports only moved the stop to :219 (pane widths from 360) and :243 still walks through the cat | RETIRE; optionally move two steps into check_finder_ui (menus fold before clipping across 1040-1400 px; one pane width through sizes and drag) |
| check_hatch_ui | :124 | Opening the Brain room runs `dpkg-query`, which the check forbids; the room reads hardware by design (brain_runtime.py:11-13). Ports moved it to :136, :162, :221 | RETIRE; covered by test_launcher and check_navigation_ui |
| check_head_ui | :106 | The meters moved to the foot and the System menu is gone (0.7.0) | RETIRE; covered by test_faces_find_light `:252`, test_operations, test_system_menu |
| check_graphite_ui | :99 | Head mark and cat are hidden | RETIRE; the startup-screen part is in test_graphite |
| check_rename_ui | :136 | "Assignment"; then the Game row (:154) and the right pane title (:163) | RETIRE; covered by test_graphite RenameGuardTests and the external name sweep |
| check_paper_ui | :110 | Writing areas are dark plates now (then :131, :114) | RETIRE; covered by the ported test_paper and the external boxes probe |
| check_finder_ui | :112 | Fault in the measuring tool: `ui_fit.py:81-85` over-counts a styled tool button's padding. Captures show every word whole (`shots/head_1366x768.png`, `apps_1366_18pt_x3.png`) | FIX the tool: passes, 13 checks |
| check_machine_ui | :75 | Left tabs are Files, Machine, Settings (`BOSS_M1.md:20`) | PORT (one line): passes, 8 checks |
| check_continue_ui | :142 | Defect plus stale check, see Defect 1 below | FIX-CODE + PORT: passes, 11 checks |

### The 12 scripts the gate does not run

| Script | Status | Action | Result after patch |
|---|---|---|---|
| check_explore_ui, check_operations_ui | Already pass | Candidates for the gate | Pass |
| check_presentation_settings_ui, check_memory_cabinet_ui, check_memory_settings_ui, check_model_settings_ui, check_return_thread_ui | All stop near their end on the Return-thread link. It now sits in the right pane's Activity view; the pane opens on Stacy since 0.5.0 (bisected to 94244c2). | One-line PORT: open Activity first | Pass |
| check_cabinet_ui | Find's search box has its own hint (c748812) | One-line PORT | Pass |
| check_navigation_ui | The Apps list now ends with a Game row (a95732b) | One-line PORT | Pass |
| check_cabinet_actions_ui | The cabinet tree now opens the desk's general right-click menu | PORT: drop that step (check_context_menu_ui covers it) | Pass |
| check_settings_ui | Asserts a 0.1 colour | PORT: drop the colour line | Pass |
| check_settings_02_ui | Exposes Defect 3 | PORT + FIX-CODE | Pass |

### Defects and patches (in `patches/`)

1. **Memory-only checks read the full hardware profile.** `resource_control.py:315` (`background_reason`) and `:290` (`model_room`) call `brain_runtime.host()` with the full profile, which runs `dpkg-query`. Commit 13ddfc5 moved the other memory-only callers to `host(profile=False)` and missed these two.
   - Effect in the check: the service's step test (`agent_loop.py:781`) swallows the exception, so work never continues while Graphite is closed.
   - Effect on the ThinkPad: a package query every 15 minutes, and any exception there would silently stop closed-window work.
   - Fix: `fix_resource_control_memory_only.diff`. The related unit modules still pass with it.
   - check_continue_ui also needs its own port, because since 0.2a3 the service waits out an 8-second foreground lease after window activity (`resource_control.py:74-84`).
2. **`tools/ui_fit.py` false clipping.** Fix: `fix_ui_fit_drawn_words.diff` compares the button's drawn ink with the same words drawn alone. It still flags a word that is really cut (`probe/uifit_sanity.py`).
3. **Dead toggle.** "Pleasantries in script" sits in Tools ▸ Engineering ▸ More (shell2.py:3299-3312). It writes the `appearance.cursive` setting, but `cursive_on()` always returns False (shell2.py:66-69), so the press changes nothing. This breaks `RECORD:141`: "a control is lit only when a press would do something". Proposed fix (not applied): remove the action and its `'@pleasantries'` entry at menus2.py:197, or make `cursive_on()` honour the setting.

### Files

All under `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/testclean/failing/`:
- Data: `failing.json` (per test and per script: assertion and code `file:line`, when it broke, class, superseding direction with quote, action, patch, result)
- Patches: `patches/` (`test_*.diff`, `tests_ported.diff`, `ui_checks_ported.diff`, `fix_resource_control_memory_only.diff`, `fix_ui_fit_drawn_words.diff`, `apply_clean_ports.py`)
- Patched copy: `tree_clean/` (manifest rebuilt); ported tests also in `tree/`; exploration copy in `tree_port/`
- Logs: `logs/` (including `logs/ui/a13_*.err` at aa0ce07, `logs/bisect_ui_1.txt`, `logs/bisect_ui_2.txt`, `logs/ui/batch_clean2.txt`, `logs/batch_clean_units.txt`)
- Runners: `bin/at.sh`, `bin/ui.sh`, `bin/bisect_ui.sh`
- Probes: `probe/`; captures: `shots/`