# lines: progress (builder, key "lines")

Worktree: /home/user/Struthio/.claude/worktrees/wf_16a59868-66f-4 (nothing committed).
Scratch: work/b084/lines/ (recopy.sh makes a copy with a current seed; t.sh runs one module; probe.py shows the bugs;
logs/). Copies: lines/base (unchanged tree), lines/copy (the working tree).

## Done
- Read the rules, the evaluator (sdk/cli/arc1cli/typed_pipeline.py) and its callers (workbench/line_steps.py,
  chain_menu.py, context_menu.py LinePanel, stacy_language.py, field_ripple.py, chain_workbench_qt.py).
- All seven bugs reproduced on the unchanged copy: logs/probe.base.log.

## Half done
- Nothing edited yet.

## Next
- tests_integrated/test_line_rules.py (one test per bug + edge cases), see them fail on base.
- Fix typed_pipeline.py: one rule for "a number written as text" (number/same), unary minus, select spaces,
  quoted semicolon, group keys, sum, join naming.
- line_steps.py / chain_menu.py follow-through; list the module in tools/check_hatch.py FOCUSED_MODULES (far from the
  siblings' lines 40 and 53).
- Run: test_line_rules, test_context_menu, test_graphite, test_writing_line, test_memory_settings, test_desk_acts,
  test_desk_scenes, test_project_desk, test_release_check, test_typewriter_faces in both looks.
