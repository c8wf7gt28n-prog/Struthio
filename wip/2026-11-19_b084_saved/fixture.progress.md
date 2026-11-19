# fixture (the invented workspace, Rail Demo): progress

STATE: COMPLETE (second run, 19 Nov). Worktree: /home/user/Struthio/.claude/worktrees/wf_16a59868-66f-1 (nothing committed).
Patch: b084/fixture.patch (2,146 lines, 16 files). It is exactly the worktree's difference from its commit, and
`git apply --check` passes on a clean copy of that commit's tree.
Scratch scripts: b084/fixture/{recopy.sh,sync.sh,t.sh,many.sh,save.sh,before.sh,try*.py}; logs in b084/fixture/logs,
the last full run's lines in b084/fixture/final.out.

## Done (all in the patch)
- workbench/rail_demo.py (new): build(), find(), set_settled_current(), workspace(base). Build about 7 s here.
- Scene: P01.json "workspaces.rail_demo.names" + step "args_by_seed"; desk_scene.for_workspace/arguments; run_scene switches
  by seed. Campaign: seed rail_demo, DP01a..d (scenes set), DA01/DA16/DA17/DA27 (new demo set), need "rail_demo".
- tests_integrated/test_rail_demo.py (26 tests) and test_rail_demo_campaign.py (18 tests), listed in tools/check_hatch.py
  FOCUSED_MODULES. docs/CAMPAIGN.md has a Rail Demo section.
- Final run on a fresh copy with the seed made current, default look and kasandra look, every module OK (0 failing):
  test_rail_demo 26, test_rail_demo_campaign 18, test_desk_acts 28, test_desk_scenes 5, test_campaign 23,
  test_resource_rules 15, test_release_check 22, test_delete_words 6, test_graphite 29, test_kasandra_highlight 10,
  test_presentation_settings 16, test_system_menu 31, test_deployment 16, test_workspace_backup 7.
- Before the patch (the starting commit plus only the two new test modules): test_rail_demo fails at import; the campaign
  module's tests error and the run stops at "Unknown case id".
- Verified once by hand on the owner's backup read from scratch campaign_fixtures (nothing copied; run folder deleted):
  A01, A16, A17, A27, P01a, P01b all Pass with this patch.

## Not done
- The full 67-module suite was not run, only the 14 modules above in both looks.
- The probes under wip/ that copy the owner's restored workspace were not switched (wip/ is out of bounds for a builder).
- Nothing was run on the ThinkPad.

---
# fixture: finished after the independent review (fix run, 19 Nov)

STATE: COMPLETE. Worktree: /home/user/Struthio/.claude/worktrees/wf_023c5420-966-5 (nothing committed).
Patch rewritten: b084/fixture.patch (2,430 lines, 16 files). It is the worktree's whole difference from its commit
(`git apply -R --check` passes there), and name.patch, lines.patch and faults.patch each still apply on top of it.
Working notes: b084/fixture.fix.md. Scripts and logs: b084/fixture/fix/ (final.out holds the last run's lines).

## Must-fix, both done
1. A Rail Demo build that breaks is a Fail, not Blocked. tools/campaign_lib/fixture.py rail_demo_workspace asks
   rail_demo.available() first and blocks only on that; whatever stops the build afterwards is not caught, so the runner
   scores it as a Fail with the build's own sentence. Tests (test_rail_demo_campaign.ABuildThatBreaks): the rule itself,
   and a real `campaign run` of DA01 with a pdftotext and pdftoppm that only fail first on the PATH: outcome Fail, need
   shown as met, reason "case broke after 0 of 7 checks met: Unavailable: Rail Demo could not be built: ...".
2. The per-seed arguments in run_scene are guarded. workbench/desk_scene.py works `args = arguments(step, seed)` out once
   and uses it for the doer and for the row. tests_integrated/test_rail_demo.py play() reads, at the hand.write step, the
   file that was actually written in Files and compares it with Rail Demo's readings ("Settled current,250,mA" among
   them), in every run of the scene (six tests).

## Should-fix done
- DA17 reads the restored desk with the profile it was backed up from moved away, so the sheets can only be the
  restored profile's.
- _Desk.job puts back a `launch` hold the caller had put on the Kernel (it used to delete it).
- A job of the build that Graphite does not start within 60 s (JOB_WAIT; free memory, held work) is cancelled through
  jobs.cancel and the build stops saying what the job waited for. Tested on a stand-in and on the real Kernel with the
  host reporting 600 MiB free.
- find() asks documents.list a page at a time (found among 101 other pages).
- set_settled_current: asked again with the value the cell already holds, when the settled power was worked from another
  value, it leaves the cell and works the power again (a stop between the two is carried on). Refusals now say what was
  being done ("Rail Demo could not be read: ...", "The settled current of Rail Demo could not be changed: ...").
- Both limit sheets have one row that is the same in both (Nominal voltage, 12 V): REVISION 2, new SHA-256 for the two
  limit sources in the test, docs updated.
- build_window: the bench seed is made under the holds again; only a seed with jobs is early (early=True, Rail Demo).
  A seed that fails leaves nothing behind (tested for both orders).
- for_workspace (both copies) refuses names it cannot use (an empty name, a name that is not text) in words, instead of
  mangling every name.
- report's "not recorded" line is asserted; SETTLED_POWER and STARTUP_POWER are compared with what Graphite worked out.

## Tests (fresh copy, seed made current; record_registry --check passed)
Both looks, every module OK, 0 failing:
  test_rail_demo 34, test_rail_demo_campaign 21, test_desk_acts 28, test_desk_scenes 5, test_campaign 23,
  test_resource_rules 15.
Fails-before: five fixes taken away at once in the copy (doer given the step's own arguments; DA17 without the profile
switch; every build trouble Blocked; the hold deleted; one list of pages) gave 7 failures and 1 error in test_rail_demo
and 3 failures and 1 error in test_rail_demo_campaign, each at the test that pins that fix. Copy put back, then deleted.

## Not done
- `tools/campaign.py list` on a damaged scene file still ends in a traceback (its last line is now the sentence, and no
  name is mangled). Catching it at the command was left: other damage (bad JSON, a missing run) did the same before.
- The other eight modules of the builder's list (test_release_check, test_delete_words, test_graphite, test_deployment,
  test_workspace_backup, test_system_menu, test_kasandra_highlight, test_presentation_settings) import nothing this run
  touched and were not run again. The full suite was not run.
- Not run with the owner's backup this time (A01, A16, A17, A27, P01a..d): their code path changed only in run_scene's
  one-line `args` and in for_workspace's check of names.
- Only Poppler 24.02 here. Nothing was run on the ThinkPad.
