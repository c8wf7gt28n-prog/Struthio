# name: review (independent reviewer) — FINAL

Patch reviewed: work/b084/name.patch (23 files, 1090 lines; applies clean to the main checkout's tracked tree).
My area: work/b084/name/review/ (logs/, scripts/, frames/). My copy of the tree is deleted.
VERDICT: accept_after_fixes (3 must-fix, all small).

## What I ran (my copy, patch applied, seed made current; each module alone in its own process and empty HOME)
| module | default look | GRAPHITE_APPEARANCE=kasandra |
| test_one_name (new) | 12 OK | 12 OK |
| test_kasandra | 20 OK | 20 OK |
| test_writing_line | 32 OK | 32 OK |
| test_frame | 11 OK | 11 OK |
| test_context_menu | 44 OK | 44 OK |
| test_conditions | 16 OK | 16 OK |
| test_graphite | 29 OK | 29 OK |
| test_kasandra_column | 18 OK | 18 OK |
| test_continuing_work | 13 OK | 13 OK |
| test_desk | 27 OK | 27 OK |
| test_desk_acts | 28 OK | 28 OK |
| test_model_turn | 28 OK | 28 OK |
| test_operations | 16 OK | 16 OK |
| test_system_menu | 31 OK | 31 OK |
| test_typewriter_faces | 13 OK | 13 OK |
| test_kasandra_highlight | 10 OK | 10 OK |
| test_delete_words | 6 OK | 6 OK |
| test_stacy_hand | 19 OK | 19 OK |
| test_stacy_start | 14 OK | 14 OK |
| test_hologram | 23 OK | 23 OK |
| test_settings_registry | 19 OK | 19 OK |
| test_faces_find_light | 34 OK | 34 ran, 1 FAILED (not from this patch, see below) |
| test_release_check | 22 ran, 1 FAILED | 22 ran, 1 FAILED (FROM THIS PATCH, must-fix 2) |

Mutations (the fix reverted in my copy, then restored):
- agenda.py without named() + app.js back to 'STACY · OWNER-HOSTED': History.test_an_agenda_row..., TheCode.test_every_sentence...,
  TheCode.test_the_phone_page... all FAIL (3 of 6); restored: 6 OK.
- boss_qt.py `plates.addAction(asset.stem)`: TheWindow.test_no_word_on_screen_says_stacy_in_either_look FAILS in both looks
  ("stacy · the start · QAction text: Stacy after midnight").
So the new tests do guard what they say. (History.test_her_trail_and_the_activity_actor... is a guard that never failed: the
trail never carried her name; its 'Stacy wrote ...' row is an invented shape.)

tools/check_context_menu_ui.py on my copy: exit 1 in BOTH looks at step 09, line 336 (`panel.slab.styleSheet()==bt.line_sheet()`),
after 11 check lines (01 to 08) pass; 07 reads "Ask Kasandra about this". The SAME failure at the same line with the patch
reversed and the seed made current again: the gate script is already red on the main commit. Not from this patch.

Frames (name/review/frames/, the builder's frames.py on my copy: 31 files per look, plus 4 of my own at 20 pt). I read 18 PNGs.
Both looks, 1920x1200 and 1366x768: strip "Kasandra Terminal Search Web Log" whole; the Kasandra look's masthead "Kasandra"
whole; the right-click on a file "Ask Kasandra about this…" whole; TXT card "TEXT · WHAT KASANDRA HOLDS" whole;
"‹ Kasandra · Activity" whole (221 of 237 px; 176 of 193); Art plates row "Kasandra after midnight" whole. Also whole at the
18 and 20 pt reading sizes at 1366x768 (frames/probe2_*.json, two PNGs read). In the first look her column itself shows no
name (portrait, "no model yet", "does and shows"); her name is on the strip and on the pane's title.

## MUST FIX
1. New brain events still read "Stacy" on screen, in both looks. workbench/tail_words.readable() builds the row's words with
   `origin.title() + ' · '`, and workbench/local_brain.put() (and line 588) still writes the actor 'STACY' on every brain event
   0.8.4 itself records (selection ACTIVATED, worker READY, handover CHECKPOINTED, acceleration_probe DEVICE_DISCOVERY, ...).
   Shown by log_qt.event_line (Log > Events and its pin), console_qt (TIMELINE) and control_qt (Activity's timeline); the pin's
   details also say "origin STACY". The code sweep cannot see it (the word is computed), CODE_KEPT exempts 'STACY', and the walk
   has no brain event. Repro (either look, in a copy):
     python -B -c "from workbench import tail_words,activity; print(tail_words.readable(activity.make_event('STACY','brain.worker','READY')))"
     -> Stacy · brain.worker
   On the window: scripts/probe.py step A (logs/probe.<look>.json: A_log_rows, A_pin, A_found_log).
   Fix at the one place the words are made (the record keeps its identifier), and give the walk a brain event so the window
   test holds it.
2. The patch turns test_release_check red in both looks: FocusedSet.test_every_test_module_is_in_the_focused_set_or_named_on_demand
   -> "'test_one_name' : a test module nothing runs". Add it to tools/check_hatch.py FOCUSED_MODULES (or ON_DEMAND_MODULES with why).
3. Guide > About Graphite says "Stacy's artwork, the names and the game are kept back (RIGHTS.md)" in both looks
   (workbench/qt_app.py show_about; exempted by tools/name_sweep.CODE_KEPT; the walk never opens About). The task keeps the
   name in the files RIGHTS.md and COPYING, not in the program's own sentence on screen. RIGHTS.md keeps back all artwork under
   branding/, so "The artwork, the names and the game are kept back (RIGHTS.md)" loses nothing. Repro: scripts/probe.py step B
   (B_found_about). Then drop the CODE_KEPT entry and have the window test read About.

## SHOULD FIX
- Rules > Desk artwork > Art plates > "Kasandra after midnight" opens a tab "Preview · Stacy after midnight.webp", with
  "Viewer · Stacy after midnight.webp", "Working area · Stacy after midnight.webp", the path bar and an Activity row "Opened
  Stacy after midnight.webp" (probe step C). The file is branding/boss/plates/Stacy after midnight.webp (not under
  branding/stacy/). The row hides the name one click before the screen says it five times. A rename of a binary cannot travel
  in this patch format (git diff without --binary), so this is a decision for the merge: rename the plate there, or accept it
  as a file's own name and say so in the release note.
- docs/DAILY_GUIDE.md, "Two appearances (0.8.0)": still "In Kasandra the assistant is called Kasandra", which now reads as if
  she had another name in Graphite.
- The window sweep reaches no dialog opened with exec(), no Log with a brain event, no opened art plate: three places where
  I found the old name. Each fix above should add its place to tools/name_sweep.walk.
- The Log pin's "origin STACY" (a stored identifier shown raw): decide whether a raw record view may say it; if so, say so
  in name_sweep's KEPT notes, because the sweep's pattern flags it.
- My frames are in name/review/frames/ (I may not write to name/frames/, whose 24 per look are from the builder's earlier script).

## What the builder kept, judged
- Agenda rows already stored: kept, right (kernel-level test; new rows say Kasandra; a stored row is rewritten with her name
  the next time the agenda retries it, which is a new write).
- Her trail: kept, right (it never carried her name).
- The activity actor 'STACY' as a stored identifier: right to keep in the record; WRONG to let it be shown as a name (must-fix 1).
- Settings keys (stacy.enabled ...), object names, module and file names, record schemas: kept, right; the only lowercase
  "stacy" read on the walk is settings keys.
- RIGHTS.md, COPYING, old release notes, RECORD_OF_DIRECTIONS.md, branding/: untouched, right. README's legal sentence keeps
  "Stacy's artwork ... (RIGHTS.md)": a file beside the program, acceptable.
- The About sentence: should not be kept (must-fix 3).
- workbench/version.py exempted as a whole file: harmless, LINEAGE is shown nowhere.
- The parser's refusal "not part of Stacy language": kept in the sdk, replaced by line_steps.plain before the window; right.

## Checked and found sound
- named() is called with a non-literal argument in 4 places only (logs/named_args.txt); none takes the owner's data. A file of
  the owner's named "Stacy notes.txt" is listed under its own name.
- No code compares shown words against the old name; no other tools/check_*_ui.py asserts it.
- remote_pwa/sw.js fetches from the network first: the phone page does not stay on the old words.
- The model's prepared context is tied to the live worker, so no prompt cached under the old name survives a restart.
- The patch holds no wip/, MANIFEST.json, seed, version, release notes, RIGHTS or branding change; no private path or data.
- No "Kas" short form was added on screen (none existed).

## For the coordinator (not from this patch)
- tests_integrated.test_faces_find_light fails in the kasandra look on the main commit itself:
  DeskLightTests.test_white_paper_comes_down... "172 not less than 150" (same with the patch reversed).
- tools/check_context_menu_ui.py (in check_hatch.UI_CHECKS) stops at step 09, line 336, in both looks on the main commit.
- Activity still says "their order, niceness and Stop are in the System menu" (there is no System menu since 0.7.0).
