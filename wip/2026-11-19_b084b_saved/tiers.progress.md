# tiers: progress (builder) - DONE

Worktree: /home/user/Struthio/.claude/worktrees/wf_401c7b30-522-8 (base f3c7036). Patch: ../tiers.patch (7 files,
applies to HEAD). Result: ../tiers.build.result.json. Measurements: tiers/measure.txt, tiers/runs/*/tier*.json.

## Done
- tools/run_tiers.py, tools/tiers.json, tests_integrated/test_run_tiers.py (12 tests, both looks pass), docs/CHECKS.md,
  README Checks line, docs/WINDOW_CHECKS.md note, test_run_tiers in FOCUSED_MODULES on its own line (after
  test_colour_vision, own comment, blank line above).
- Measured: tier 0 39.9 / 39.4 / 38.6 s (+35 s after ordering by measured seconds); tier 1 (agenda_qt.py one-line
  change) 1m 46s, 5 modules chosen; tier 2 graphite 11m 36s, kasandra 11m 35s, each 100 runs, 1160 tests, 0 failing.
- Fixed waits measured (waitprobe.py): 115 of 351 s in qWait across the 22 window checks; none replaced (see CHECKS.md).

## Not done
- Step 2 new scenes / probe assertions; fixed waits in check_finder_ui; --look both not measured as one run.

## Fix after review - DONE (20 Nov, worktree wf_401c7b30-522-12)
- All must_fix (Ctrl-C/SIGTERM stop with killpg, result written, exit 130, `timeout` backstop; --no-renames) and all
  should_fix items are in tiers.patch; test_run_tiers 14 tests, both looks OK; 12 of 12 mutations caught.
- Re-measured: tier 0 35/37/37 s (G) 38 s (K) on a quiet machine, 52/47 s with another build beside; tier 2 both looks one
  run 25 min 3 s, 2,302 tests, 0 failing, 10 skipped named. Notes: tiers.fix.md; result: tiers.fix.result.json.
