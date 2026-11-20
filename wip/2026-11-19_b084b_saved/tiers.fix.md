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

## Resumed after the restart (worktree wf_401c7b30-522-12)
- tiers.patch applied cleanly; regenerated from the worktree it is byte-identical. Code read again against every review
  finding: all must_fix and should_fix are in the code (see the list above).
- The earlier fix run's logs (tiers/fixlogs, tiers/fixruns-t0-*-1..3) show: test_run_tiers 14 OK, test_release_check 23 OK,
  test_machine 6 OK in both looks; tier 0 35/37/37 s Graphite, 38 s Kasandra, 0 failing. Its tier 2 Graphite run was cut
  by the container restart at 80 of 100 and wrote tier2.json with 2 INTERRUPTED and 19 NOT RUN rows (the stop worked).
- Now running tiers/fix3.sh (background): fresh copy, modules both looks, tier 1 plan, tier 0 each look, tier 2 both looks.
- Next: read tiers/fix3.out; update docs/CHECKS.md "Measured here" with the new numbers; rewrite tiers.patch; result file.
- DONE (00:40 UTC 20 Nov). fix3.sh on a fresh copy: test_run_tiers 14 OK, test_release_check 23 OK, test_machine 6 OK in
  both looks; tier 1 plan for agenda_qt.py: same 5 modules (30 units); for the patch's own 7 files: 30 chosen (README.md
  21, docs/WINDOW_CHECKS.md 12, docs/CHECKS.md now 1); tier 0 51.8 s Graphite, 47.0 s Kasandra (another build's tests
  beside it), 412 tests, 0 failing; tier 2 --look both 25 min 3 s, 196 runs, 2,302 tests, 0 failing, 10 skipped
  (test_startup_scripts 5 a look); no /tmp/graphite-tier-* left. 'first Ran line' mutation now caught (12 of 12).
- Found, not fixed (not this item): test_rail_demo alone through run_all, Graphite look, -B and PYTHONDONTWRITEBYTECODE=1,
  leaves 7 .pyc in workbench/view_modules/__pycache__ of the copy. Likely the Kernel's job environment (allow-list of
  os.environ; PYTHONDONTWRITEBYTECODE set only in the snapshot branch, engineering_kernel.py ~1455). Not traced further.
- docs/CHECKS.md: measured numbers updated (tier 0 after the fix; tier 2 both looks measured, no longer estimated).
- tiers.patch rewritten (7 files, 88,236 bytes), applies to a clean export of HEAD. Copy removed.
