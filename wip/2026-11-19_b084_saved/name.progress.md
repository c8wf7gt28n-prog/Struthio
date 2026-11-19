# name: progress (builder, key "name")

Worktree: /home/user/Struthio/.claude/worktrees/wf_16a59868-66f-3 . Scratch: work/b084/name/ (scripts/: mkcopy.sh, t.sh, py.sh, save.sh, frames.py).
The patch work/b084/name.patch is rewritten after each milestone (scripts/save.sh).

## Done (in the patch)
- workbench/assistant_identity.py: NAME = 'Kasandra' in every look; named() always puts her name where the code says 'Stacy'.
- Leaks closed: agenda.py (the "Waiting for ... brain" reason, new rows only), boss_qt.py (three accessible names in the
  first look; the Art plates menu row, which showed "Stacy after midnight" in BOTH looks), remote_pwa (three strings, and
  the manifest's description).
- tools/name_sweep.py (new): NEVER (the language's name, Stacy), words_of, sweep, walk (51 places by desk acts), in_code.
- tests_integrated/test_one_name.py (new, 12 tests): the name, the sweep's own tests, the code, the phone page, the guide
  pages, the window in both looks (child process each), history (agenda row, her trail, the activity actor).
  ON THE CHANGED COPY: 12/12 OK in the default look and with GRAPHITE_APPEARANCE=kasandra (110 s each).
  ON THE PROGRAM AS IT WAS (scripts/mkcopy.sh with BEFORE=1): 8 failures in 7 tests; 5 pass (the sweep's own three, what
  is kept, the trail/actor guard).
- Existing tests updated: test_kasandra (NameTests), test_writing_line (3 lines), test_frame, test_context_menu:335,
  test_conditions:219, test_graphite:305 (message only).
- Guides: GETTING_STARTED.md, docs/WORKSHOP.md, README.md, docs/DAILY_GUIDE.md, docs/THINKPAD_FIRST_INSTALL.md
  (the legal sentence in README keeps "Stacy's artwork ... (RIGHTS.md)").
- Window checks' words: tools/check_finder_ui.py, check_rename_ui.py, check_context_menu_ui.py, check_desk_ui.py, desk_review.py.
- First frames taken (work/b084/name/frames/): the strip and both right-click menus read whole at 1366x768 in both looks.

## Half done
- Final frames (add the right pane with Activity up, the Rules menu's hand, the Art plates rows) and reading them.
- The full suite in both looks on a copy has NOT been run yet.

## Next
1. Full suite on a copy, default look and kasandra, two modules at a time; fix what fails.
2. tools/check_context_menu_ui.py on a copy (one of the seven passing gate scripts; its notes were edited).
3. Final frames; patch; `git apply --check` on a clean checkout.
