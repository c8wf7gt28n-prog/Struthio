# private fix (third run, after the review)
- Applied private.patch in worktree wf_9807ad9e-481-7. Reviewed patch kept at private/fx/reviewed.patch.
- Code: find_names counts sheet records; cases_anchor.found pages intake.items, passes over unreadable calcs (names them for the calc lookups), logs reads via ctx.progress (FINDS added to A01/A16/A27 allowed); A01 drops pdf_source_sha; A27 keeps sheet/calc_settled/claim_settled (no hash) in its checkpoint; CAMPAIGN.md + fixture docstring qualified (release notes).
- New tests: test_rail_demo_campaign.TheSceneCaseWhereItsNamesAreFound (run_case in-process on Rail Demo, P01 in invented names; 3 tests); 2 new desks in test_each_name_is_found_once; TheRuns DA27 progress/checkpoint asserts; test_rail_demo.TheRecords: 2 new tests + Elsewhere wrapper.
- batch1 (copy, seed current): both looks all OK: rail_demo_campaign 26, rail_demo 38, desk_acts 30, desk_scenes 5, campaign 23, resource_rules 19, run_tiers 14; release_check 25 (default look).
- private.patch REWRITTEN after batch1 (21 files).
- DONE: fail-before runs (mut.sh, mut2.sh, mut3.sh) all failed as expected; the final TheRecords passed in both looks; the patch was rewritten and checked against a clean HEAD; private.fix.result.json was written; progress.md was appended; the copies were deleted.
- (was) Running: private/fx/mut.sh (fail-before A1/A2 on reviewed code, SAIDBACK, FINDNAMES, M3; then TheRecords both looks + test_campaign). Then: apply --check on clean copy, result json.
