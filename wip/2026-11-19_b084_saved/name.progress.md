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

# name: after the review (fix pass, 19 Nov)

Worktree: /home/user/Struthio/.claude/worktrees/wf_023c5420-966-7 . Scripts: name/scripts/fix_*.{py,sh} ; logs: name/logs/fix/
(batch3.out is the run of record). The patch work/b084/name.patch is rewritten: 29 files, 1265 lines; `git apply --check`
OK on a clean copy of main's tracked tree, and the applied files equal the worktree's (28 compared, 0 different).
THE PATCH NOW HOLDS A RENAME (a "rename from / rename to" hunk, similarity 100%, no binary content):
branding/boss/plates/Stacy after midnight.webp -> Kasandra after midnight.webp. `git apply` carries it; MANIFEST.json and
the seed name the old file and are remade at merge as always.

## Must-fix
1. Brain events read "Stacy". workbench/tail_words.py: shown_origin(origin) (her actor 'STACY' is read as her name; the
   record is not touched, local_brain still writes 'STACY') and readable() uses it. Also through it: the Log's pinned details
   (log_qt.details: "origin KASANDRA") and two listings the review did not name, found by the walk once it had a brain event:
   qt_app._refresh_activity (Agent Activity: "time  origin  operation  state") and project_tabs.refresh_activity (the
   Project Desk's events). The walk writes a brain event with the program's own writer (local_brain.put) and reads it in
   Activity, in the listing of recorded commands, pinned in the Log and in Search's timeline.
   Test: History.test_a_brain_event_keeps_its_actor_and_is_read_with_her_name. FAILS with readable() as it was
   ('Stacy · brain.worker' != 'Kasandra · brain.worker'), and so does TheWindow in both looks (mutation 1 in batch3.out:
   3 failures); passes now.
2. test_release_check red: 'test_one_name' is in tools/check_hatch.FOCUSED_MODULES (beside test_kasandra). 22 OK both looks.
3. About: "The artwork, the names and the game are kept back (RIGHTS.md)." The CODE_KEPT entry is gone, so the code sweep
   holds it (mutation 2: with the old sentence back, tools/name_sweep.py finds 1 place, exit 1); the walk shows About
   (QDialog.exec held, the dialog shown instead) and reads it.

## Should-fix
- The art plate: RENAMED in the patch (see above), boss_qt.MIDNIGHT_PORTRAIT follows, the row is the file's own stem again
  (no named() there), the CODE_KEPT entry is gone, and the walk opens her plate and reads "Preview · Kasandra ...".
  Nothing else in the tracked tree names the file (git grep), no setting stores its name. If the merge would rather keep
  the file's name: drop the rename hunk and the one-line boss_qt constant, put back named(asset.stem) and the CODE_KEPT
  entry, and take 'Rules: her art plate opened' out of the walk and the test.
- docs/DAILY_GUIDE.md: "The assistant is Kasandra in both."
- The walk reaches the three places (and a fourth, the listings). 55 places, all done, nothing found, both looks.
- "origin STACY": DECIDED and written in tools/name_sweep.py (the KEPT note): words made for reading say her name (rows,
  the pinned line and its details, listings with a column for who acted); an event printed whole as it is stored (the JSON
  in the tip of a row of Activity's timeline, control_qt.py:103) keeps "origin": "STACY", as it keeps its operation and
  state, and name_sweep.RECORD sets exactly that pair aside. The walk does read that tip, so the exemption is in use.
  To turn it the other way: pass the tip's event through shown_origin and delete RECORD.
- History.test_her_trail_and_the_activity_actor_keep_what_was_written: now says in its own comment that it is a guard
  that never failed. The tests of the change in History are the agenda row and the brain event.
- Frames: name/frames/ remade from the final tree by scripts/frames.py (34 per look) plus scripts/fix_frames.py (8 per
  look: 40 Activity with a brain event, 41 the Log with it pinned, 42 About, 43 her plate opened; 1366x768 and 1920x1200).
  76 PNGs. Read by me (7): the Log pinned in both looks at 1366x768, About, the plate opened (Kasandra look), the
  right-click on a file in both looks, Activity at 1920x1200. Her name whole on the strip, the masthead, the menu row, the
  pane's title, the pinned line, the tab. A long file name is cut with an ellipsis in the head's crumb and in the line's
  note ("Preview · Kasan…r midnight.webp"), as any long name is there; the tab and the viewer's title show it whole.

## Tests (the copy of the final tree, seed check exit 0; each module alone, own empty HOME; logs/fix/batch3.out)
Both looks OK: test_one_name 13, test_release_check 22, test_graphite 29, test_kasandra 20, test_writing_line 32,
test_delete_words 6, test_typewriter_faces 13, test_browse 6, test_frame 11, test_context_menu 44, test_desk 27,
test_desk_acts 28, test_project_desk 11, test_kasandra_column 18, test_hologram 23, test_kasandra_highlight 10,
test_conditions 16, test_stacy_hand 19, test_readiness 10.
test_faces_find_light: default 34 OK; kasandra 34 ran, 1 FAILED (DeskLightTests.test_white_paper_comes_down...,
"172 not less than 150"): the failure the review found on the main commit; the module imports nothing this patch touches.

## Not done
- The whole suite was not run (the coordinator runs it at merge). tools/check_*_ui.py were not run.
- test_faces_find_light in the kasandra look and tools/check_context_menu_ui.py step 09: on main already, left.
- Seen, not changed: Activity says "their order, niceness and Stop are in the System menu"; About says "Graphite 2.0";
  a test script's origin reads "Desk-Script:Test · ..." in a timeline (origin.title() of any actor that is not quiet).
- Scratch: the copy is deleted; name/before (the builder's 149 MB copy of the program as it was) is deleted too.
