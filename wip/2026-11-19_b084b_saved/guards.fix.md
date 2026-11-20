# guards fix notes (fix run, 20 Nov)
- Applied guards.patch in worktree wf_401c7b30-522-15 (base a1f86b5): clean.
- Next: must_fix 1 (Kit test), 2 (rail_demo stale seed), 3 (run.py marker); then should_fix.
- Edits made (all in worktree; wip patch at work/b084b/guards.fix.wip.patch; guards.patch NOT yet rewritten):
  must 1: Kit test on a temp tree; must 2: tests_integrated/seed_hold.py shared hold (desk_acts build_window starts it
  before an early seed; context_menu imports it; rail_demo Workspace holds it), rail_demo_campaign TheRuns skips on an
  edited seed with the reason; must 3: plant.py marker + restore, run.py rewritten (Stop, prepare(), gone/error rows,
  setpriv+own session, default --out beside the copy), README; new tests_integrated/test_planted_bugs.py (+FOCUSED line);
  tiers.json tier 0 test_record_paths; test_frame status line by parts.
- Running: guards/fix/bin/round1.sh (summary guards/fix/round1.summary).
- Round 1 DONE (02:17): 11 modules default + 9 Kasandra all OK; stale seed: rail_demo 34 OK, campaign skipped (1 class),
  context_menu/desk_scenes/desk_acts OK, project_desk only Seed fails; kit: release_check 25 OK, planted_bugs skipped,
  project_desk OK; old run.py vs new test: 3 failures + 1 error. guards.patch REWRITTEN (26 files) after round 1.
- Next: round2.sh (real run.py: kill -9 then rerun, Ctrl-C, five bugs), then recopy check of run_tiers/release_check, report.
- Round 2 DONE (02:21): kill -9 and rerun, Ctrl-C, five bugs, final-copy checks all as expected. Patch rewritten and
  checked against a clean HEAD export. Result file written. Copies deleted.
