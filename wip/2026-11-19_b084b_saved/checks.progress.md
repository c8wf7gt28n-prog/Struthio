# checks: progress (builder of item "checks", 0.8.4 part B)

Patch: checks.patch (final tree; applies to a clean checkout of HEAD: `git apply --check` clean, 1306 files compared equal).
Helper scripts: checks/bin/ (mkcopy.sh, runui.sh, runtests.sh, runpy.sh, gate_one.py, batch1.sh, batch2.sh, headcopy.sh, applycheck.sh).

## Done (all in the patch)
- Seven scripts removed: check_desk_ui, check_frame_ui, check_hatch_ui, check_head_ui, check_graphite_ui, check_rename_ui,
  check_paper_ui; tools/symmetry.py too (only check_desk_ui imported it).
- Kept steps folded: check_finder_ui 13 (head words fold, 1040-1400 px, 14 and 18 pt), 14 (one pane width, drag), 15 (Line/Half/Tall);
  check_navigation_ui (Apps list between the bands); check_cabinet_ui (prose face).
- Ports: machine, cabinet, navigation, presentation_settings, memory_cabinet, memory_settings, model_settings, return_thread,
  settings, cabinet_actions, settings_02; check_context_menu_ui step 09 (the script was wrong).
- Dead toggle removed (shell2.py, menus2.py, control_qt.py); tests_integrated/test_lit_controls.py.
- Two program faults found by the Kasandra-look run of check_finder_ui, fixed: finder_qt.column_width/title_need (List column title cut),
  shell2.breakable_path (long folder name cut on a Today card); tests_integrated/test_whole_words.py.
- tools/check_hatch.py: UI_CHECKS = all 22; ON_DEMAND_CHECKS holds no window check; ui_check_lists(); FOCUSED_MODULES line
  ('test_lit_controls','test_whole_words') after 'test_faces_find_light'; new test in test_release_check.py (UiGate).
- docs/WINDOW_CHECKS.md (new); notes in GRAPHITE_01.md, GRAPHITE_DESK.md; edits in FINDER_01, SETTINGS_INVENTORY_07, IMPLEMENTATION_MAP,
  HATCH_AGENT_01, README, DAILY_GUIDE.

## Verified
- Before any change (default look): 10 of the 22 passed, 12 failed (logs/base.default.jsonl).
- New tests against the tree as it was (HEAD + the three test files): test_lit_controls 1 of 2 fails; test_whole_words 1 fails, 4 error;
  the new release-check test errors. On the new tree all pass in both looks.
- Round before the last program edits: 22 of 22 default; kasandra 19 of 22 (cabinet, finder, navigation: fixed since and rerun green).

## Finished
- batch1.sh: final run of all 22 in both looks (44 of 44 PASSED) and 30 test modules in both looks -> logs/batch1.txt.
- Relaunched run: patch applied to the new worktree (HEAD 42a7080), rewritten byte-identical, applies clean; tested copy equals
  the worktree apart from MANIFEST.json and the seed. Result written: checks.build.result.json (bin/result.py). Copy deleted.

## Found, not fixed (report it)
- Pane width ratchet: 14 pt -> 16 -> 14 -> 20 -> 14 -> 28 -> 14 (or 16,18,20,28 -> 14) leaves both panes 415 px (Graphite) / 479 px
  (Kasandra) instead of 326 / 354 until restart: the right pane's content keeps a stale minimum width. Direct 14 -> 28 -> 14 comes back.
  The retired frame check asserted "no ratchet" through 28 pt. Folded step 14 goes to 20 pt only.
- The setting appearance.cursive ("Script for incidental text") is still in Settings and still changes nothing on screen.
- test_faces_find_light fails in the Kasandra look (172 not less than 150): known before this work (BUILD_STATE), not touched.

## Fix round after the review (19 Nov, worktree wf_401c7b30-522-5; working notes in checks.fix.md)
- CORRECTION: "Direct 14 -> 28 -> 14 comes back" above was wrong (the reviewer could not reproduce it, nor could I): one trip
  to 28 pt left both panes 415 px (479 in the Kasandra look). Now fixed in the program: pane_qt.remeasure (the faces out of
  sight are measured again at each new size) and pane_qt.place asks the window again when a pane's least width changes.
- check_finder_ui step 14 goes through 28 pt again, and full screen and back (the frame check's step 04) is folded into it.
  Docstring describes steps 13 to 15.
- New: tests_integrated/test_pane_width.py (FOCUSED_MODULES, on the line with test_lit_controls and test_whole_words).
- test_whole_words pins FinderPage.scale_columns (stub page on a bare list); its U+200B now written as ​.
- check_hatch: on-demand entries may carry arguments (ui_check_lists); each window check's run folder is made under a
  temporary TMPDIR of the gate's, removed when the check ends (test in test_release_check).
- docs/WINDOW_CHECKS.md: who runs the Kasandra pass and when, the checkable "ten of the twelve" figure, the frame check's
  step 05 named as a gap, the third fault (the panes after 28 pt).
- Results: 32 modules / 571 tests per look: default 0 failing, Kasandra 1 (test_faces_find_light, known). 22 of 22 window
  checks pass in both looks, 287 steps each, 371.4 s and 373.8 s summed. Every new test fails on the program before the fix.
- checks.patch rewritten (50 files) and applies clean to HEAD. The reviewed patch is kept as checks/review/checks.reviewed.patch.
