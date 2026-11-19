# faults: fix after review (19 Nov)
Worktree: /home/user/Struthio/.claude/worktrees/wf_023c5420-966-6 (builder's patch applied with git apply, then the fixes below; nothing committed)
Scripts and logs: work/b084/faults/fix/ (lib.sh, edit_tests.py, stage*.sh, stage*.out, logs/, builder/ = the builder's versions of the files I changed)
Copy for tests: work/b084/faults/copy (mine; delete at the end)

## Done in the worktree (stage 1 run: fix/stage1.out)
- MUST FIX (segfault at start after leaving with Home in front and a room open, script opens the Office):
  workbench/qt_app.py: _close_start returns while the window restores its session (_initializing), so the second pass never
  leaves Home; restore_waiting_tabs no longer closes Home and shows it again (those lines are gone).
  New helper tests_integrated/session_start_probe.py (one start = workbench.qt_app.main in its own process, as the start
  script: Office edition, whole screen, ARC_LEDGER_OPEN=office) and test StartScript in test_session_start.py (3 starts).
  Evidence: with the builder's qt_app.py put back in the copy the test fails "the start ended with exit code -11 ...
  Fatal Python error: Segmentation fault"; with the fix it passes. Native backtrace of the old crash (gdb, logs/gdb_second.log):
  QWidgetPrivate::setVisible -> QLayout::activate -> QLayoutPrivate::doResize -> 4 unnamed frames in libQt6Widgets (SIGSEGV):
  the main window's layout, after its dock state was restored once before the window was on screen and once after.
- should_fix done: Preview left of a room no longer sets the room aside (workspace_tabs ROOMS); session 'target' and
  settings_navigation.selected only looked up when text (session.py); WorkspaceTabs.waiting/restored/restore_active/deferred set
  in __init__ (qt_app uses tabs.waiting directly); tests for the two untested lines (tab closed between the passes; nothing said
  while rows wait); Manual open at leaving no longer raises in descriptor (group title only when text) + test in the real window.
- test_session_start on the fixed copy, default look: 20 tests OK (48 s).

## Next
- stage 2: mutants of my own pieces (each must be caught), the reviewer's recipe with repro_start.py and the real launcher.
- stage 3: the modules that touch what I changed, both looks; then rewrite faults.patch, apply-check, append to faults.progress.md, delete the copy.

## Not doing (say so in the report)
- desk_acts.py:167 own literal list of looks: left, as the reviewer says, until the 'name' item has landed (same lines).
- a tab that cannot be reopened: reason still only on stderr (launch-error.log means "the start failed"; not clearly right to write there).
- rooms restore does not know (Documents, Files) still go to Reopen deferred tabs at each start (0.8.3 behaviour, a design choice).

## Stage 2 done (fix/stage2.out)
- 8 mutants of this pass, each caught by the new tests: M1 guard in _close_start out (SecondStart, StartScript, the unit test fail);
  M2 Preview sets a room aside; M3 group title unchecked; M4 strip attributes not set when made; M5 closed tab counted;
  M6 said while rows wait; M7 target looked up as it is; M8 settings place looked up as it is.
- Reviewer's recipe on the fixed copy (builder's repro_start.py "3 home", dedicated settings, one HOME): starts 1, 2, 3 exit 0,
  Office back each time, nothing deferred; start 4 the real launcher still running after 25 s (exit 124); Kasandra look exit 0.
- After stage 2: probe act 'manual' removed (unused); ReturnTab added to the Preview-left-of-a-room test. Patch saved before stage 3.

## Running: stage 3 (fix/stage3.sh -> fix/tests_default.txt, tests_kasandra.txt): 41 modules in both looks on a fresh copy.
Then: savepatch.sh, append to faults.progress.md, delete faults/copy.

## Stage 3 done (fix/stage3.out): FINISHED
- default look: 41 modules, 703 tests, 0 failures. Kasandra look: 41 modules, 703 tests, 6 failures in 5 modules, the same test
  names as on the unchanged tree (reviewer's base logs). test_session_start 20/20 in both looks.
- Patch rewritten (10 files), apply-check OK; faults.progress.md appended; faults/copy deleted.
