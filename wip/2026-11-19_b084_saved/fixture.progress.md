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
