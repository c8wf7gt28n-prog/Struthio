# setting (remove appearance.cursive) - progress (second run, worktree wf_9807ad9e-481-2)
- DONE. Patch final (setting.patch, 16 files, dry-run applies to a clean HEAD export). Result: setting.build.result.json.
- Tier-1 61 modules both looks (1033 tests each): one failure, test_presentation_settings enum 17->16, fixed in the test.
- Added test_lit_controls.TheScriptSwitch. Final re-run of the 3 touched modules both looks: OK. 4 settings window checks both looks: exit 0.
- Revert checks (setting/revert/summary.txt): R1 spec, R2 session, R4 pleasantry, R5 refresh, R6 sync each fail their test; R3 readback line alone is unreachable (publish filters unknown keys).
