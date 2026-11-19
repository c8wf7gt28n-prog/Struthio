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
