# look: independent review (DONE)

Verdict: accept_after_fixes. Result: look.review.result.json. Logs and scripts: look/review/logs, look/review/scripts (the copy is deleted).

Copy: the main checkout's tracked tree at 42a7080 (same code as 044e080) + look.patch (git apply: clean, 30 files, git diff --check clean), with the seed made current.

## Tests (both looks, on the patched copy)
26 modules, 564 tests per look, 0 failing in default and in kasandra:
colour_vision 7, faces_find_light 34, kasandra_highlight 20, system_menu 31, release_check 22, one_name 17, context_menu 44,
delete_words 6, desk 27, desk_acts 28, documents 13, frame 11, graphite 29, kasandra 20, launcher 17, model_turn 28,
network_watch 50, operations 16, related 11, session_start 20, typewriter_faces 13, writing_line 32, cabinet 14, explore 13,
hologram 23, kasandra_column 18.

## Reproduced
- window report: Kasandra line 18384 px, 18384 warm, 0 green; Field 32483 px, 30823 warm, 0 green; Log row [#e2a72e, #5a3f0c].
  Graphite line 13788/13784, Field 34935/32501, Log row fill #202520. Same as the builder's numbers.
- tools/colour_vision.py: exit 0; Graphite 25 pairs under 10, Kasandra 11, all reviewed. Machado 2009 matrices = published values.
- Graphite frame counts from the builder's PNGs: log 1652 px (reworded note) at both sizes, field 1920 326 px (noise; two unchanged takes differ by 2201 there).
- Signs named in colour_vision.SIGNS exist (field_qt._mark shapes, corner ticks, dashed recheck edge, hologram.STATE_LOOK words).

## Reverts (each test fails when its piece is put back)
- m1 PDF fill back in Kasandra: test_the_pdf_evidence_mark... FAILS (inside #4ea8d6, not the page's #2aa8ff).
- m2 typebar_qt back to base: test_her_keyboard_light_is_warm... FAILS (line 13788 px, 0 warm).
- m3 field_qt back to base: same test FAILS (field 34400 px, 4123 warm = 12 %).
- m4 KEYS + "(Space)": test_one_name.TheWindow FAILS in both looks with "key · Today · QPushButton toolTip: Show or hide the preview (Space)".

## Must fix
1. Shown strings still name a key, and KEYS misses "(Space)", "hit Enter", "Ctrl-S", "Backspace", "or Return":
   finder_qt.py:358 Preview tip (the walk reads it on Today), finder_qt.py:602 "Show preview (Space)", field_page.py:546 status
   "Enter opens it", field_qt.py:940 tip "Close this page (Esc)", reading_preferences.py:221 "Ctrl+Alt+= / Ctrl+Alt+- adjusts prose",
   qt_app.py:356 "press Enter to open it" (Manual), 1590 "Hide Graphite  (Esc)", 4366/4967 "Ctrl+Break stops it",
   empty_workspace_qt.py:101/140, engineering_tabs.py:597 "Flap (Space)".
2. Merge: tools/check_head_ui.py hunk conflicts with checks.patch (which deletes the file); look.patch on top of checks.patch fails
   only there, applies with --exclude=tools/check_head_ui.py. The edited line is unreachable anyway: check_head_ui exits 1 at
   line 106 (the head meters moved to the foot in 0.7.0), before line 126.

## Should fix
- test_faces_find_light: measure corrected, but the limit loosened: lightness 150 on a grey = luminance 0.305; her tone 0.322; new limit 0.4 = lightness 170. Say so or set the limit with a reason.
- KEYS false positives: "Matching F45 / F12 curves overlap." (spice legend), "Escape ..." at a sentence start.
- qt_app Full Screen tip "the same line returns..." ("line" is a pipeline on screen).
- GETTING_STARTED "Apps, at the upper right": in Kasandra the button is the kp logo, no word.
- Kasandra line light = three hard opaque steps (reads as stripes); Field rings now under overlapping sheets and over the selected sheet's stack edges.
- #f8edc9 -> CUE turns the Return thread's writing box (return_thread_qt.py:144) from her yellow to blue in Kasandra; report does not place it.
- colour_vision: one colour per meaning; cue colours, BAR, pointer halo not in the table; threshold 10 uncited.
- name_sweep.named_in reassigns `rest` in the loop (fragile if a name is added after 'key').
