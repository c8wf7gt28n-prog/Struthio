RESTART NOTE (coordinator, 19 Nov 23:40 UTC): the container restarted while this work was running. The patch file named in this note's item (23:35 copy) is the latest: it equals the worktree at the moment of the restart. Apply it and carry on from 'Next'; do not redo what is listed as done.
For guards: guards.patch (saved 23:30) holds all the tests and tools listed as done. verify1/verify2 and the rerun of the planted bugs had not reported; run them again.

# guards: progress (builder)

Done (in the worktree; patch at work/b084b/guards.patch):
- tests for guarding gaps: M127 (new test_record_paths, in FOCUSED_MODULES after test_resource_rules), M097 test_stacy_hand,
  M028/M032/M034 test_desk_acts, M085/86/88/89/70 test_resource_rules (OwnersNumbers), M122 test_memory_settings,
  M076/78/40 test_model_settings, M007/08 test_change_sets, M019/24 test_continuing_work, M091/96 + the one seed-current test
  (test_project_desk.Seed), M079 + kit exclusion test test_release_check. Others: M057 test_line_rules, M059 test_context_menu.CompareText.
  Fast modules all pass in the default look (copy run 23:00 UTC).
- digest rule: seed_bound() hold in test_desk_acts.build_window (covers desk_scenes) and test_context_menu.setUpModule.
- tools/planted_bugs/{plant.py, run.py, bugs.json, README.md}; package_graphite NOT_SHIPPED keeps it out of the kit.
- Guarding baseline (0.8.2): 30 caught / 53 = 56.6%.

Half done / next:
- verify1 (test_desk_acts with new tests) running; verify2 (stale seed: window modules with and without the hold) next.
- rerun: run.py --group guarding on two copies (scratch bin/), then --group other --before gap; then Kasandra look for touched modules.
- Not attempted: M020 (adaptive pause), M036 (Files fallback point); other gaps: field_*, rooms, idle, images_plus, evidence_compiler, M015.
