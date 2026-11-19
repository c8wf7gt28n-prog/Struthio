# faults: progress (second run, 19 Nov) — FINISHED, nothing half done

Patch: work/b084/faults.patch (596 lines, 9 files; applies to a clean export of d09c3b7 and reproduces the worktree's
files: `bash work/b084/faults/applycheck.sh`). Nothing committed. Worktree: /home/user/Struthio/.claude/worktrees/wf_16a59868-66f-2.
Scripts and logs: work/b084/faults/ (repro*.sh, repro_start.py, sweep_restore.py, mutants.sh, suite.sh, ui.sh, logs/,
suite_logs/, ui_logs/, suite_default.txt, suite_kasandra.txt). Copies kept: faults/base (unchanged tree + the new tests
copied in), faults/copy (the final tree).

## Done
- All three faults reproduced for real on a copy of the unchanged tree (through workbench.launch for 1 and 2, in the real
  window through the probe for 3):
  1. appearance ["kasandra"] in the session file: "Graphite could not start: TypeError: unhashable type: 'list'".
  2. dedicated session's settings (ARC_LEDGER_EDITION=office ARC_LEDGER_OPEN=office ARC_LEDGER_FULLSCREEN=1
     ARC_LEDGER_XSESSION=1), fresh HOME: start 1 fine, leave; start 2 and 3: "Graphite could not start: AttributeError:
     'WorkbenchWindow' object has no attribute 'ledger_bridge'". Also with other rooms open, with work in the workspace,
     in the Kasandra look, and from a hand-written session with OfficeBuildingTab or SlateRoomTab. Not when the Office tab
     is closed before leaving, nor on a plain start that opens no room. Sweep: ClipWorkspaceTab stops the start the same way.
  3. her column, something running: "Now: Now: Read the bench readings · ..." in both looks.
- Fixes: workbench/presentation_preferences.py, boss_theme.py, session.py (1); workspace_tabs.py, qt_app.py (2);
  agenda_qt.py (3). Tests: new tests_integrated/test_session_start.py (13 tests), probe case now_line in
  tests_integrated/kasandra_window_probe.py, the module listed in tools/check_hatch.py FOCUSED_MODULES.
- New module: 13/13 OK in the default look and with GRAPHITE_APPEARANCE=kasandra. On the unchanged tree with only the
  tests copied in: all 13 fail (logs/test_session_start.BASE.log; three of them only because they name something the fix
  adds: the list of looks, _first_tab, restore_waiting_tabs).
- 12 mutations of the fix (one piece taken out each): all 12 caught by the new module (logs/mutant_*.log).
- After the fix, through the launcher on the copy: three starts in a row with the dedicated settings exit 0, one Office
  tab, deferred empty; the profile 0.8.3 could no longer start on starts; a list or object appearance starts in Graphite.
- Full suite on the copy, one module at a time: default look 66 modules, 1,018 tests, 1 failure (test_release_check: the
  new module was not yet listed; listed since, rerun 22 OK). Kasandra look 66 modules, 1,018 tests, 7 failures: that same
  one (rerun 22 OK) and 6 that fail the same way on the unchanged tree (test_frame 1, test_context_menu 1,
  test_writing_line 2, test_conditions 1: they assert the name Stacy; test_faces_find_light 1: Kasandra's desk light).
- Window checks on the copy: check_continue_ui PASSED in both looks (it restarts on a saved session). check_frame_ui,
  check_return_thread_ui, check_memory_settings_ui, check_memory_cabinet_ui, check_desk_ui stop at the same line on the
  unchanged tree and on the copy (stale scripts).

## Seen, not fixed (reported)
- Rooms that restore does not know (DocumentsTab, FilesTab, ...) go to "Reopen deferred tabs" at every start and the list
  grows by one per such room per start (unchanged tree: logs/repro_B_deferred_*.log; copy: logs/repro_fixE_*.log).
- ManualTab open at exit: closeEvent raises in workspace_tabs.descriptor (widget.group is a QComboBox without .title), seen
  in the sweep (logs/sweep_base.log); the session is then not saved.
- The five Kasandra-look failures above.
- Why the owner did not meet fault 2 on the ThinkPad cannot be told from here.

# faults: after the independent review (fix pass, 19 Nov) — FINISHED

Patch rewritten: work/b084/faults.patch (10 files; applies to a clean export of 155c24c and reproduces the fix worktree,
`bash work/b084/faults/fix/savepatch.sh`). Nothing committed. Fix worktree: /home/user/Struthio/.claude/worktrees/wf_023c5420-966-6.
Scripts and logs of this pass: work/b084/faults/fix/ (lib.sh, stage1..3.sh and .out, mutate.py, logs/, tests_default.txt,
tests_kasandra.txt, builder/ = the builder's versions of the three files changed). The copy (faults/copy) is deleted.

## Must fix: done
Left with Home in front and a room open, every next start of the dedicated session ended inside Qt (exit 139, no message).
- Cause: the second pass (the rooms that waited for the bridge) left Home for each room and showed it again before the window
  was on screen; the start script's opening at the first turn then died in the main window's layout (gdb, fix/logs/gdb_second.log:
  QWidgetPrivate::setVisible -> QLayout::activate -> QLayoutPrivate::doResize -> SIGSEGV in libQt6Widgets). Why Qt's layout
  is left in that state by restoring the dock state once before and once after the first show was not traced further.
- Fix (workbench/qt_app.py): _close_start does nothing while the window restores its session (_initializing), so the second
  pass never leaves Home, as the first pass never did; the lines that closed Home and showed it again are gone.
- Test: new helper tests_integrated/session_start_probe.py (one start = workbench.qt_app.main in a process of its own, with what
  the start script sets) and StartScript in test_session_start.py: three starts on one profile. With the builder's qt_app.py
  put back it fails "the start ended with exit code -11 ... Segmentation fault"; with the fix it passes. SecondStart also
  checks, in the real window, that Home is never left on the way (no last_surface 'workspace' is written during the start).
- The reviewer's own recipe on the fixed copy (builder's repro_start.py "3 home", dedicated settings, one HOME): starts 1, 2, 3
  exit 0, Office back, nothing deferred; the real launcher on that HOME still running after 25 s; Kasandra look exit 0.

## Should fix: done
- A Preview left of a room no longer sets the room aside (workspace_tabs.ROOMS: Office, Slate, Return thread).
- Session 'target' and settings_navigation.selected are looked up only when text (session.py), with a test.
- WorkspaceTabs.waiting, restored, restore_active and deferred exist from __init__; qt_app reads tabs.waiting directly.
- Tests for the two lines no test held: a tab closed between the two turns; nothing said while rows still wait.
- Leaving with the Manual open no longer raises while the strip is written down (descriptor: a group's title only when it is
  text), so the session is saved; checked in the real window (third and fourth start of SecondStart).
- Mutants: 8 pieces of this pass taken out one at a time, each caught by the new tests (fix/stage2.out).

## Should fix: not done, on purpose
- desk_acts.py:167 keeps its literal list of looks until the 'name' item has landed (the reviewer's own advice; a test pins it equal).
- A tab that cannot be reopened still explains itself only on stderr: launch-error.log means "the start failed", and writing
  there after a start that succeeded is not clearly right. The status line still says how many tabs were set aside.
- Rooms the restore does not know (Documents, Files) still go to Reopen deferred tabs at each start: 0.8.3 behaviour, a design choice.

## Tests (fresh copy of the final tree, seed current; fix/tests_default.txt, fix/tests_kasandra.txt)
- test_session_start: 20 tests OK in the default look and with GRAPHITE_APPEARANCE=kasandra (13 before this pass).
- The reviewer's 41 modules (the new one and every module that imports a changed file): default look 703 tests, 0 failures;
  Kasandra look 703 tests, 6 failures in 5 modules (test_context_menu 1, test_frame 1, test_faces_find_light 1,
  test_writing_line 2, test_conditions 1): the same test names as in the reviewer's run of the unchanged tree.

## Not checked
- A real display (offscreen only, as the rules say). The owner's ThinkPad.
- Whether Home closed before the window is first shown by the Field opening at start (open_on_work, 0.8.3 code, untouched)
  can meet the same Qt fault later: no workspace with work was started here.
