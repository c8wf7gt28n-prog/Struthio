RESTART NOTE (coordinator, 19 Nov 23:40 UTC): the container restarted while this work was running. The patch file named in this note's item (23:35 copy) is the latest: it equals the worktree at the moment of the restart. Apply it and carry on from 'Next'; do not redo what is listed as done.
For tiers: tiers.patch = the builder's patch PLUS every fix listed below as done. The pre-fix patch is tiers/tiers.patch.before-fix. A fixer starting now applies tiers.patch (not the before-fix one) and does only what is under 'Next'.

# tiers fix (after review) - working notes
Worktree: /home/user/Struthio/.claude/worktrees/wf_401c7b30-522-13 ; tiers.patch (before fix) applied cleanly; a copy of
it is kept at tiers/tiers.patch.before-fix. tiers.patch now holds the fixed version (rewritten after each milestone).

## Done (code)
- must_fix 1: Stop class (SIGINT/SIGTERM/SIGHUP handlers while run_all runs; ignored signals stay ignored), daemon
  threads, killpg of every running child, NOT RUN / INTERRUPTED rows, tier<N>.json written, exit 128+signal; `timeout -s
  KILL limit+grace` in front of each child as a backstop when the run itself is killed.
- must_fix 2: --no-renames in changed_files.
- should_fix: skipped kept/shown/last line; crash branch tested (os._exit(0)); check/scene/integrity/sweep readers
  tested; killpg after a normal end; program variables dropped by prefix (ARC_LEDGER_, ARC1_WORKBENCH_, LEDGER_,
  GRAPHITE_); Graphite look = variable unset; --out resolved; cache shape checked; worker exception -> failed row;
  non-Python files by whole-word name; last 'Ran' line; docs (git checkout for tier 1, all of the above); tiers.json
  test_run_tiers 28 s; stale release_check.json removed before the integrity unit.
- Tests: 14 in test_run_tiers, pass both looks (28 s). All 8 new/changed tests fail against the pre-fix runner.
  Mutations: 12 of 12 caught (after the nested-summary fake got a leading newline).
- Tier 0 caught my own fault: fake window checks named check_*_ui tripped test_release_check -> renamed window_*.

## Next
- re-copy; test_run_tiers, test_release_check, test_machine both looks; tier 0 both looks; maybe tier 2 graphite.
