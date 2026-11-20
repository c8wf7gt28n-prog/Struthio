# guards: progress (builder) - DONE 20 Nov 00:50 UTC

Patch: work/b084b/guards.patch (20 files; applies to a clean HEAD). Result: work/b084b/guards.build.result.json.

Done:
- Tests for every 0.8.2 guarding gap (23) and for M002, M055, M060, M111, M155, M057, M059 in the other group.
- Digest rule: seed_bound() hold in test_desk_acts.build_window (covers test_desk_scenes) and test_context_menu.setUpModule.
  On a stale seed (comment in engineering_kernel.py): test_project_desk fails exactly one test (Seed current), test_desk_acts
  30 OK; first run: test_context_menu and test_desk_scenes OK with the hold, 2 and 5 failures without it.
- tools/planted_bugs (plant.py, run.py, bugs.json with verdict_0_8_4, README); NOT_SHIPPED in package_graphite.
- Modules touched and importers: 19 modules OK in default and Kasandra looks (final.sh phases A, C); test_change_sets,
  test_line_rules rechecked after the last edits in both looks.
- Planted bugs rerun: guarding 51/53 (96.2%) with a current seed, M093/M096 caught on a stale seed (packaging refused);
  overall 100/131 (76.3%). Results: guards/final_guarding.jsonl, final_other.jsonl, final_extra.jsonl, final_m060.jsonl.

Open: M071, M075 (not in the 0.8.2 valid set), M063, M114, M150 and 26 other gaps not rerun (listed in the result).
