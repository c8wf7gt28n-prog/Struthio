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

# guards: fix run after the review - DONE 20 Nov 02:25 UTC
Patch rewritten: work/b084b/guards.patch (26 files; checked and applied on a clean HEAD export: OK). Result:
work/b084b/guards.fix.result.json; notes guards.fix.md; logs and scripts under guards/fix/.
- must 1: test_release_check.Kit reads a temporary tree holding tools/planted_bugs; kit-shaped folder: 25 OK (was 1 failure).
- must 2: tests_integrated/seed_hold.py (one hold) used by test_desk_acts (also before an early seed), test_context_menu,
  test_rail_demo's Workspace; test_rail_demo_campaign.TheRuns skips on an edited seed with the reason. Stale seed:
  rail_demo 34 OK, campaign OK (skipped=1), desk_acts/context_menu/desk_scenes OK, project_desk only the Seed test fails.
- must 3: plant.py marker (.planted.json in the copy) + restore(); run.py restores and refreshes before the first bug.
  kill -9 then rerun on a real copy: M078 put back, M075 missed, file byte-identical.
- should: Ctrl-C stops at once (exit 130, 1.1 s); gone/error rows; refresh timeout; exit 1 on a tree error; default --out
  beside the copy; tier 0 + CHECKS.md test_record_paths; test_frame by parts (M155 caught); release-note caveat.
- New module test_planted_bugs (4 tests; FOCUSED_MODULES line of its own after test_viewer_kinds): old run.py 3F+1E, now OK.
- Both looks OK: desk_acts, rail_demo, frame, release_check, planted_bugs, run_tiers, desk_scenes, context_menu,
  kasandra_highlight (+ one_name and rail_demo_campaign once). Planted-bug totals not rerun as a whole (build's numbers).
