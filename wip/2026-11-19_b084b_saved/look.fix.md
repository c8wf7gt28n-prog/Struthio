# look fix run (after review)
- applied look.patch in fresh worktree; dropped tools/check_head_ui.py hunk (must_fix 2).
- next: KEYS gaps + false positives, named_in `rest`, fix shown key strings, code sweep keys_in_code + test, should_fix items, tests both looks, patch.
- DONE (in worktree, saved as look.fix.wip.patch = full patch incl. look.patch, minus check_head_ui): KEYS widened (brackets, hit/tap, Ctrl-S, ⌘, Backspace, PgUp, or Return) and narrowed (F-names joined by '/', 'Escape' alone); named_in keeps key text apart; keys_in_code + KEYS_CODE_KEPT (15 reviewed) + KEY_SPEC; 30 shown strings fixed (before: 30 found on the reviewed look.patch tree; after: 0); test_one_name: 2 new tests + extended pattern lists; faces_find_light limit = L* < 65 stated; colour_vision: cue meaning, BAR in chosen, halo in ready, threshold explained; 11 new REVIEWED, 2 rewritten; GETTING_STARTED step 4; Full Screen tip; boss_theme LEGACY note places the Return box change.
- Tests OK both looks: colour_vision 7, faces_find_light 34, model_turn 28, writing_line 32, one_name 19.
- running: batch of 18 modules (lookfix/batch2.txt).
- DONE. look.patch final; result file written next.
