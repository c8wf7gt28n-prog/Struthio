# Review of item "checks" (independent reviewer)

Copy: checks/review/copy (main checkout tracked tree at 42a7080 + checks.patch; git apply --check clean; seed made current, registry MATCHES).
Scripts: checks/review/bin (seed.sh, tests.sh, ui.sh, gate_one.py, batch_main.sh, exp.sh, edits.py, ratchet.py). Logs: checks/review/logs.

## Done
- Patch applies clean to the main tree (49 files: 8 deleted, 3 new). Registry record unchanged by the patch.
- Read the whole patch except the bodies of the 8 deleted files.
- Main batch running: 30 test modules in both looks, then all 22 window checks in both looks (logs/main.txt).
  Default look so far: all modules OK.

## Findings so far
- Pane-width ratchet (builder found, did not fix): kept step 14 stops at 20 pt to avoid it; retired frame check went to 28.
  SPEC rules: "retire only with evidence", "no list of known failures". To confirm with ratchet.py (patched and base).
- Unit tests for the Date Modified fix test the helpers only; reverting FinderPage.scale_columns to the old width
  is not caught by any unit test (to confirm: exp.sh 'columns').
- Numbers: check_hatch comment "as twelve had by 0.8.3" and WINDOW_CHECKS "nine of those twelve" vs builder's own baseline: 10 of 12 failed.
- Docs: 36 mentions of retired scripts remain in GRAPHITE_DESK.md body, 8 in GRAPHITE_01.md (note at top). Task said remove from docs.
- test_whole_words.py has 5 raw U+200B characters in its source (house style writes '​').
- appearance.cursive "Script for incidental text" still in Settings, does nothing (builder reported).

## Next
- Wait for main batch; run exp.sh (reverts: card, columns, toggle, stray, named; ratchet probe patched both looks + base).
- Write result JSON, delete copy.

## More (19 Nov, during the main batch)
- Default look: 30 modules all OK (see logs/main.txt).
- Merge: look.patch edits tools/check_head_ui.py, which this patch deletes (git apply --check fails on that file only; the rest
  of look.patch applies on top). Both edit tools/check_hatch.py, menus2.py, typebar_qt.py, test_system_menu.py (apply cleanly).
- Retired frame check step 04 (F11 round trip keeps both column widths) still describes today's desk (qt_app.toggle_fullscreen,
  _fullscreen_panel_widths); no test or check calls toggle_fullscreen after the patch; not kept, not listed as dropped.
- check_finder_ui docstring not updated for steps 13-15.
- Gate grows from ~200 s to ~377 s per look while the road asks the release check to shrink to ~15 min.
- Pre-existing, outside the patch: empty_workspace_qt.py:101 prints 'F11 fullscreen · Ctrl+Alt+= / − text size' on screen;
  finder_qt fill_more row 'Show preview (Space)'.

## Finished (19 Nov)
- Tests: 30 modules x 2 looks, 562 tests each; default 0 failing; Kasandra 1 failing (test_faces_find_light, known, look item).
- Window checks: 22/22 PASSED in both looks, 287 steps per look; 365.7 s default, 382.6 s Kasandra (summed).
- Reverts: card -> caught; toggle -> caught; stray/named -> caught; scale_columns -> NOT caught by unit tests (only check_finder_ui kasandra).
- Ratchet: 14->28->14 leaves 415 (default) / 479 (kasandra) vs 326/354, on the base tree too; builder's "direct trip comes back" not reproduced.
- Verdict: accept_after_fixes; must_fix: ratchet hidden by step 14 stopping at 20 pt; unit test for FinderPage.scale_columns.
- Result: checks.review.result.json. Copy deleted.
