# look builder: progress
DONE. look.patch is final (30 files; git apply --check on a clean archive of HEAD: exit 0, and the applied tree equals the worktree).
look.build.result.json is written. The copies (look/base, look/copy) are deleted; frames, crops, logs and the colour-vision tables are kept under look/.
This run: re-applied the first run's patch, made the tree-search tip name the search button (removed its KEYS_KEPT entry, added a check in test_one_name),
ran test_one_name, test_context_menu and test_desk_acts in both looks (all OK), measured the numbers (logs/NUM.*.txt) and compared the frames.

# look fix run (after the independent review) — DONE
look.patch rewritten from a fresh worktree (46 files; applies to a clean HEAD alone and after checks.patch).
- must_fix 2: tools/check_head_ui.py hunk dropped.
- must_fix 1: KEYS widened (key in brackets, hit/tap, Ctrl-S, ⌘, Backspace, PgUp/PgDn, Page Up, or Return/Esc) and narrowed
  (F-names joined by '/' or followed by curve/net/...; 'Escape' alone); new name_sweep.keys_in_code (every non-doc sentence in
  workbench/ naming a key; key names alone, Qt shortcuts and text after a menu tab set aside) with KEYS_CODE_KEPT (15 reviewed).
  30 shown strings fixed (the reviewer's 13 and 17 more found by the sweep). New tests in test_one_name.
- should_fix done: desk-light limit stated as CIE L* < 65 (was L* 62 in effect); KEYS false positives; Full Screen tip; GETTING_STARTED
  step 4 names her logo; boss_theme notes the Return box change; colour_vision: 'cue' meaning, BAR in 'chosen', the halo in 'ready',
  threshold explained (Mahy 1994 JND), 11 new REVIEWED pairs, 2 rewritten; named_in keeps the key text apart.
- Tests (both looks, all OK): colour_vision 7, faces_find_light 34, model_turn 28, writing_line 32, one_name 19, network_watch 50,
  documents 13, context_menu 44, delete_words 6, desk_acts 28, graphite 29, hologram 23, kasandra 20, kasandra_highlight 20,
  launcher 17, related 11, session_start 20, tool_atlas 8, tool_selection 5, typewriter_faces 13, vocabulary 9, release_check 22,
  system_menu 31 (23 modules, 489 tests per look).
- Not done: frames not retaken (no paint changed; words changed are not in the four frames).
