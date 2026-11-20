# private: DONE (second run)

- Patch final: private.patch (21 files; applies to clean HEAD). Result: private.build.result.json.
- All touched modules pass in both looks; 51 modules in the default look; check_context_menu_ui PASSED on the copy.
- Not done: no run on the owner backup (look-only rule); release notes untouched (hard rule).

# private: FIX after review (third run) DONE
- must_fix 1: the run_case glue is now tested (test_rail_demo_campaign.TheSceneCaseWhereItsNamesAreFound: P01 in invented names, played by run_case on Rail Demo). It fails without said_back or without find_names.
- must_fix 2: find_names counts sheets by record; two sheets of one title are refused in words (tested).
- should_fix: A01 keeps no hash, and its admitted-source check is tested against a sheet hash that differs; found() pages intake.items, passes over unreadable calculations and logs its reads (allowed lists updated); A27 keeps its three ids in the checkpoint; CAMPAIGN.md and the fixture docstring are qualified (release notes left to the owner).
- Tests: 7 modules in both looks plus release_check, 0 failures; every fail-before run failed as expected. Patch rewritten (21 files, +658/-241); it applies to a clean HEAD.
- Result: private.fix.result.json; notes: private.fix.md. Not run: the cases on the backup, the planted-bug harness.
