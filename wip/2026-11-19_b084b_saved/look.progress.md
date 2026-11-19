# look builder: progress (rewritten at each milestone)
look.patch is CURRENT (30 files, applies cleanly to the starting commit: scripts/applycheck.sh said exit 0 and the applied tree equals the worktree).
Scripts: look/scripts (mkcopy.sh, t.sh, runset.sh, final.sh, before.sh, numbers.py, frames2.py + take.sh, cmp.py, mkpatch.sh, applycheck.sh).

## Done
- All five parts built. Tests passing in a copy, BOTH looks (runset.sh, logs/runset.*.txt): test_colour_vision 7, test_faces_find_light 34,
  test_kasandra_highlight 20, test_system_menu 31, test_writing_line 32, test_launcher 17, test_explore 13, test_hologram 23, test_kasandra 20,
  test_kasandra_column 18, test_documents 13, test_cabinet 14, test_release_check 22, test_frame 11, test_desk 27, test_graphite 29,
  test_typewriter_faces 13, test_delete_words 6 (context_menu, desk_acts, one_name were still running when this note was written).
- Frames taken: look/frames (before_, before2_ = unchanged tree twice; after_ = this work), both looks, both sizes, 4 frames each.
  Graphite before vs after outside live rectangles: menu 0, line 0, field 0 (1366) / 326 px at 1920 in a place that also differs between
  two takes of the unchanged tree; log 1652 px = the Log's note line reworded (no key named).
- Colour-vision table: look/colour_vision_table.txt (under threshold) and _all.txt.
## Left to do when this note was written
- scripts/final.sh: fresh copy, BEFORE runs (new tests on the unchanged program), numbers, last modules again.
- write look.build.result.json; delete look/base and look/copy when done.
