# tiers review (independent reviewer) - DONE
Verdict: accept_after_fixes. Result: tiers.review.result.json. Copy deleted.

Ran (fresh copy of main tree + tiers.patch, seed current, registry --check PASSED; isolated per the rules):
- test_run_tiers 12 OK x2 looks; test_release_check 23 OK x2; test_kasandra_highlight 20 OK x2; test_one_name 19 OK x2;
  test_machine 6 OK x2; test_launcher 17 OK x2; test_settings_registry 19 OK x2.
- tier 0: 34.3 s wall, 25 runs, 412 tests, 0 failing (builder 39.9/39.4/38.6/35.3). 22 window checks (Graphite): 180.5 s,
  0 failing. Builder's tier JSONs agree with the report (t2 696.0/695.0 s, 100 rows, 1160 tests). Tier 2 not re-run.
- Mutations: killpg->child.kill fails 1 test; helper traversal removed fails 2; look not set fails 2; crash clause removed
  fails 0 (gap).
Must fix: (1) Ctrl-C: first SIGINT ignored until every unit ran, then no result; second leaves children past their limit
and their temp HOMEs in /tmp. (2) git diff without --no-renames: a staged rename hides the old name from tier 1.
Should fix: skipped not recorded; crash path untested; read_result for check/scene/integrity untested; fallback leaves
grandchildren after normal exit; ARC_LEDGER_* not dropped; graphite look sets the variable; --out guard uses absolute();
wrong-shape cache crashes; worker exception -> TypeError; filename-substring over-selection; first 'Ran' line.
