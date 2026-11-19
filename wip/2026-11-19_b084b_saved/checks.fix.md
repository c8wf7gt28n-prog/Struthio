# checks: fix round after review
- [x] applied checks.patch to fresh worktree wf_401c7b30-522-5 (49 files)
- [x] must_fix 1, the program part: pane_qt.remeasure + place() key carries the pane's least width. Ratchet probe (reviewer's ratchet.py):
      default fresh 326, after 28->14 326, after 16,14,20,14,28,14 326; kasandra 354 / 354 / 354. (before: 415 / 479)
- [x] check_finder_ui step 14: F11 round trip + 16,18,20 growing, 28 pt (one width, wider than 14; the workspace floor holds
      the panes in at 28 pt, 444 < 459 at 20) and back to 14; docstring describes 13-15
- [x] tests_integrated/test_pane_width.py (new; FOCUSED_MODULES on my line with test_lit_controls, test_whole_words)
- [x] must_fix 2: test_whole_words pins FinderPage.scale_columns (stub page on a bare list); U+200B escaped (6)
- [x] check_hatch: on-demand entries with arguments; TMPDIR per window check (run folders removed); counts "ten of the twelve"
- [x] WINDOW_CHECKS.md: who runs the Kasandra pass, counts, frame row, step 05 named as a gap, the ratchet fault, timings
- [x] fix_batch.sh (logs/fix_batch.txt): before-fix copy: every new test fails in both looks; fixed copy: 32 modules 571 tests,
      default 0 failing, kasandra 1 (test_faces_find_light, known); window checks 22/22 both looks after the step-14 correction
- [x] finder_batch.sh: check_finder_ui fixed tree PASSED both looks (67.7 s each); with HEAD's pane_qt FAILED both looks at
      'did not come back' ([415,415] vs [326,326]; [479,479] vs [354,354])
- [x] checks.patch rewritten (50 files); apply --check on a clean HEAD archive: clean. Copies deleted.
- [x] result file: checks.fix.result.json (fixbin/result.py)
