# guards: independent review (DONE 20 Nov, second run after the 01:05 container restart)

Verdict: accept after fixes. Result: work/b084b/guards.review.result.json. Copies deleted; logs in guards/review/logs.

Base: main checkout at 0ca267a (tiers merged) + guards.patch: applies cleanly; seed made current.

Ran (exact):
- 19 modules (the 18 touched or importing + test_run_tiers) in both looks: all OK, 341 tests per look, 0 failing.
- Kit-shaped folder (payload_paths + MANIFEST.json, 1319 files, no tools/planted_bugs): test_release_check FAILED
  (failures=1: Kit.test_the_planted_bug_tools_stay_out_of_the_kit, line 192); test_project_desk OK.
- Stale seed (a comment appended to workbench/engineering_kernel.py): test_project_desk 1 failure (Seed, as designed);
  test_context_menu 45 OK; test_desk_scenes 5 OK; test_rail_demo FAILED 4; test_rail_demo_campaign FAILED 2;
  12 other seed-touching modules OK.
- Manual reverts (my own edits): record_io hidden-name rule, images_plus HEIF line, stacy_hand quote strip: each
  new test fails (1 failure each), passes on the clean tree.
- run.py --ids M127 M020 M086 M097 M122 M007 M088 M089 M024 M085 M079 M078: 12/12 caught (73 s), each by the new
  test; tree clean afterwards. Matches bugs.json verdict_0_8_4.
- kill -9 mid-bug (M078): model_settings.py left planted, no row; then M075 recorded 'caught' (clean tree: 'missed');
  file still planted after that run.
- Ctrl-C (SIGINT to the group, default disposition): rc=130 but the worker ran on to the end (59 s); verdicts right.
- Missing bug file: worker dies (FileNotFoundError), later bugs never run, report crashes (rc=1).

MUST: kit test; digest claim false for test_rail_demo(+campaign); run.py stopped mid-bug leaves the bug planted and
corrupts the restarted run.
SHOULD: Ctrl-C does not stop workers; missing file / refresh timeout crash the worker; SystemExit swallowed in thread;
test_record_paths not in tier 0; seed_bound duplicated; test_frame pins words; release note's 96% needs the
same-sample caveat.
