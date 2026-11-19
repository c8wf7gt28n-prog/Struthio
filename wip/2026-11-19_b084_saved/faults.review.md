# faults: independent review notes (in progress)

Work area: work/b084/faults/review/ (lib.sh, stage*.sh, logs/, homes/). One copy: review/copy.

## Milestone 1 (done): fault 2 and fault 1 reproduced on the UNCHANGED tree (copy of main checkout, seed current)
- Dedicated settings (ARC_LEDGER_EDITION=office ARC_LEDGER_OPEN=office ARC_LEDGER_FULLSCREEN=1 ARC_LEDGER_XSESSION=1), fresh HOME:
  start 1 (builder's harness, closes window) exit 0, session saved with tabs [OfficeBuildingTab];
  start 2 (harness) exit 1; start 2 again with the REAL launcher `python -B -m workbench.launch` (as START_OFFICE.sh): exit 1,
  "Graphite could not start: AttributeError: 'WorkbenchWindow' object has no attribute 'ledger_bridge'" (qt_app.py:3201 show_office).
- Hand-written session with OfficeBuildingTab, real launcher, ARC_LEDGER_EDITION=office only: same failure, exit 1.
- Plain fresh HOME, real launcher: still running after 25 s (exit 124) = starts.
- appearance ["kasandra"], real launcher: "Graphite could not start: TypeError: unhashable type: 'list'".
Logs: review/logs/base_*.log

## Next
- apply patch, seed, tests both looks; post-patch starts; mutants; edge inputs.

## Milestone 2 (in progress): patch applied cleanly to the copy (git apply, 9 files), seed refreshed; tests running (review/tests_default.txt, tests_kasandra.txt)
Scripts ready: review/stage3.sh (starts after the fix, fuzz_session.py, edge_tabs.py), stage3b.sh (10 mutants), stage4.sh (patch out, Kasandra-look baseline of 5 modules).

## Milestone 2 (done): tests on the patched copy, 41 modules (new, changed, and those that import a changed file)
- default look: 41 modules, 696 tests, 0 failures (test_session_start 13/13 OK).
- GRAPHITE_APPEARANCE=kasandra: 41 modules, 696 tests, 6 failures in 5 modules: test_context_menu 1, test_frame 1, test_faces_find_light 1,
  test_writing_line 2, test_conditions 1 (builder says the same on the unchanged tree; to be checked in stage 4). test_session_start 13/13 OK.
Next: stage3.sh (starts after the fix, fuzz, edges), stage3b.sh (mutants), stage4.sh (baseline), then delete review/copy.

## Milestone 3 (done): starts after the fix (review/stage3_A.out, stage3_B.out, stage3.out)
- Dedicated settings x3 on one HOME: exit 0 each, Office restored, nothing deferred; real launcher on that HOME still running after 20 s.
- Plain fresh HOME: runs. Hand-written Office+Slate+conversation: all three back. appearance list + Office tab: runs (Graphite look).
- Other rooms open (Office, Slate, Documents, Files, a pin, a Preview): Office, Slate, pin, Preview back; Documents and Files go to deferred (as before the patch for those kinds).
- Session file cut in half: starts fresh.
- FOUND: Preview dragged left of the Office, then restart: Office NOT restored, "1 former tabs retained in View → Reopen deferred tabs"; the stale row stays and the
  message shows at every later start (pB2_2..4). Cause: restore_rows applies the Preview-slot check to room rows.
- FOUND (same class as fault 1, also on unchanged tree to be confirmed): session 'target' or 'settings_navigation.selected' as a list/object -> Session() TypeError unhashable.
- TO INVESTIGATE: pB3_3 (left with Home in front, tabs Office+Slate, then dedicated start) exit 139 with empty log.

## Milestone 4 (done): MUST FIX found — segmentation fault at every start after leaving with Home in front and a room open
Reproduce on the patched copy (offscreen, as every run here):
  1. fresh HOME, dedicated settings (ARC_LEDGER_EDITION=office ARC_LEDGER_OPEN=office ARC_LEDGER_FULLSCREEN=1 ARC_LEDGER_XSESSION=1), start;
     the start script opens the Office; go Home (show_start / open_destination(w,'home')); leave (window closed, session saved:
     tabs [OfficeBuildingTab], view_preferences.last_surface 'home').
  2. start again the same way: exit 139, "Fatal Python error: Segmentation fault" at qt_app.py:3668 in _close_start
     (context_bar.show();doc_info.show();workspace_status.show()) <- control_qt.py:242 add_tab <- show_office <- qt_app.py:5368 (the ARC_LEDGER_OPEN lambda).
     Every later start the same (session file is not rewritten). No "Graphite could not start", no launch-error.log.
Seen with: my harness (c1 x3, c2 without fullscreen, c7 Office only), the real launcher python -B -m workbench.launch (c13), the builder's own
harness repro_start.py with action "home" (c14 starts 2 and 3). Also with view_preferences.startup 'home' and a room saved (c11).
Not seen: no ARC_LEDGER_OPEN (c3; and opening the Office 3 s later, c9); no room saved (c4); a pinned non-room tab saved with Home last (c6v);
rooms saved with the workspace in front (c5). So it needs the patch's second pass (rooms opened after Home was shown, Home closed and shown again in
restore_waiting_tabs) plus an opening at the first turn of the event loop. Offscreen platform only; not checked on a real display (rules).
Logs: review/logs/c1_same_*.log, c13_real_launcher_home_last.log, c14_builder_harness_*.log; scripts review/stage3c.sh, stage3d.sh, stage3e.sh.

## Milestone 5 (done): mutants (review/stage3b.out) — 10 pieces of the fix taken out one at a time, test_session_start run
Caught (8): Now: prefix back (2 tests fail); no second pass; Home not put back; first tab opened while rooms wait; RecursionError not caught in session;
_initializing not set in second pass; appearance() without the text check; first tab not opened when nothing could be restored.
NOT caught (2): workspace_tabs "self.restored=[... if self.indexOf(tab)>=0]" removed (13/13 still OK: no test closes a tab between the passes);
"if self.waiting:return / self.restored=[]" removed (class TabsThatWaitForTheBridge 5/5 OK: no test has a row set aside while others wait).
Crash experiments: X1 (Home not shown again after the second pass) -> no crash (but Home no longer comes back); X2 (keep the first saved dock state) -> still exit 139.

## Milestone 6 (done): last checks; copy and homes deleted (logs and scripts kept in review/)
- X3 experiment (qt_app._close_start returns while _initializing, so the second pass never leaves Home): the crash scenario starts (exit 0) and Home is back
  in front on a start with no opening (X3_4). A direction only; the suite was not run with it.
- Other values of the session file that are not text: {"target": []} and {"settings_navigation": {"mode": "settings", "selected": [], "expanded": []}}
  -> real launcher: "Graphite could not start: TypeError: unhashable type: 'list'" on the patched tree; "target" also run on the unchanged tree: same (0.8.3 already).
  session.py: `data.get('target') in TARGETS` and `navigation.get('selected') in allowed`. Fuzz: 1,230 inputs over every key, only these two keys fail; the theme reader never fails.
- Patch taken out again (copy identical to the first unchanged copy): the same 6 Kasandra-look failures in the same 5 modules (same test names). Not caused by the patch.
- Patch: 9 files, none that should not be there; no owner data, no new on-screen string; the only on-screen text touched is "Now:" (once).

## VERDICT: accept_after_fixes
MUST FIX
1. Segmentation fault at every start after leaving with Home in front and a room open, when the start script opens the Office (dedicated session). See Milestone 4.
SHOULD FIX
2. A room row is set aside when a Preview is already open (Preview dragged left of the Office): Office not restored, "1 former tabs retained ..." at every later start.
   workspace_tabs.restore_rows applies the Preview-slot check to rooms (rooms are neither Preview nor pins).
3. "target" and "settings_navigation.selected" not text -> could not start (0.8.3 already; same class as fault 1); the new module's first line
   ("Graphite starts on whatever its session file holds") says more than is true until these are guarded.
4. No test leaves Home after a restored start, or runs the start script's opening at once; add one for the fix of 1 (in a subprocess: a segfault would take the runner down).
5. Untested: the filter of closed tabs between passes; no status message while rows wait. WorkspaceTabs.waiting is not set in __init__ (restore_waiting on a strip never
   restored raises AttributeError; qt_app guards with getattr).
6. desk_acts.py:167 keeps its own literal list of looks (pinned equal by a test, not derived).
7. Carried from the builder, not this patch: Manual tab open at exit raises in closeEvent (session not saved); rooms restore does not know pile up in deferred;
   a tab that cannot be reopened is explained only on stderr.
