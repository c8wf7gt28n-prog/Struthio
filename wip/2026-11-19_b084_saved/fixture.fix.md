# fixture: finishing after review (fix run)
Worktree: /home/user/Struthio/.claude/worktrees/wf_023c5420-966-5 (fixture.patch applied with git apply; nothing committed).
Scripts: b084/fixture/fix/{recopy,sync,t,many,save,final}.sh, edit1..4.py (already applied: do NOT run again), mutate.py (copy only).
Throwaway copy: b084/fixture/copy (delete at the end).

## Done (all in the worktree; patch saved with fix/save.sh: 2,430 lines; `git apply -R --check` passes in the worktree;
## name.patch, lines.patch, faults.patch still apply on top)
- M1: fixture.rail_demo_workspace blocks only on rail_demo.available(); a build that breaks propagates and is a Fail.
  Tests: test_rail_demo_campaign.ABuildThatBreaks (2: the rule itself; a real run with a Poppler that only fails -> Fail).
- M2: run_scene works `args` out once (doer and row). test_rail_demo play() reads the file hand.write wrote (after_step)
  and compares it with Rail Demo's CSV text, in every run of the scene.
- should_fix done: _Desk.job puts back a held launch; job wait deadline (JOB_WAIT 60 s, cancel through jobs.cancel, reason
  said); find() pages documents.list; set_settled_current carried on after a stop + wording per what was being done;
  one unchanged limits row (REVISION 2, new hashes for limits_a/b); build_window early= (bench seed under the holds again)
  + clean-up test; for_workspace refuses unusable names in words (both copies); DA17 reads the restored desk with the
  original profile moved away; report 'not recorded' asserted; SETTLED_POWER/STARTUP_POWER compared with Graphite's result.
- Mutation run in the copy (five fixes taken away at once): every one caught. doer args -> 6 scene tests fail on the CSV
  text; DA17 without the profile switch -> Fail; Blocked-for-everything -> 'Blocked' != 'Fail'; hold not put back -> fails;
  no paging -> 'not whole'. Copy put back afterwards.
- Default look, whole modules: test_rail_demo 34 OK, test_rail_demo_campaign 21 OK (after two slips in my own tests fixed).

## FINISHED
- fix/final.sh on a fresh copy with the seed current: both looks OK, 0 failing: test_rail_demo 34, test_rail_demo_campaign 21,
  test_desk_acts 28, test_desk_scenes 5, test_campaign 23, test_resource_rules 15 (lines in fix/final.out).
- Patch rewritten (2,430 lines, 16 files; reverse check passes), fixture.progress.md appended, b084/fixture/copy deleted.
- Nothing left to do for this item except the "Not done" list below.

## Not done (say so)
- `tools/campaign.py list` with a damaged scene file still ends in a traceback (now a ValueError with words, not a
  mangled name); catching it at the command needs a test with a damaged copy of the program. Predates the patch for
  other damage (bad JSON, a missing run).
- ThinkPad / another Poppler: not run.
