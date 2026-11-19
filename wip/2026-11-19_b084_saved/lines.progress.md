# lines: progress (builder, key "lines"), second builder: FINISHED

Worktree: /home/user/Struthio/.claude/worktrees/wf_023c5420-966-4 (nothing committed). Patch: work/b084/lines.patch
(971 lines, 7 files; applies to HEAD 155c24c, checked in a throwaway index by lines/applies.sh).
Scratch: work/b084/lines/ (recopy.sh, t.sh, many.sh, save.sh, matrix.sh, applies.sh, before_kas.sh, probe.py, logs/).
No copy of the tree is left (lines/base and lines/copy deleted).

## Done
- The first builder's patch (partial/lines.partial.patch) applied, read through and kept whole.
- All seven bugs: one test each (tests_integrated/test_line_rules.py, TheSevenFaults.test_1 .. test_7), failing on the
  unchanged tree, passing after. Before (unchanged tree + the new module): Ran 19, failures=11, errors=8
  (logs/BEFORE.test_line_rules.base.log). After: Ran 19, OK in both looks.
- One rule (typed_pipeline.RULE; number, identity, same, compare) for where, the comparisons, group, sum/avg/min/max,
  join, missing, sort, add. Help words per step in typed_pipeline.HELP; a wrongly written step answers with them.
- Same class, fixed: sort of numeric text; add reading fields, overflow, empty brackets; group on a list; group by a
  field named count/sum_x/blank refused instead of overwritten; join on a nested field; keep rows with spaces.
- Callers: line_steps (number, literal, values, sortable, groupable); chain_menu (word, number, numeric,
  where_values, shape); stacy_language.source; test_context_menu's sort assertion; check_hatch lists the module.

## Tested (lines/near.default.txt, lines/near.kasandra.txt, logs/)
- Default look: 10 modules, 212 tests, 0 failed.
- kasandra look: 10 modules, 212 tests, 3 failed, all three about the name on screen ("Stacy" asserted, "Kasandra"
  shown): test_writing_line ModeTests.test_destination_hint_names_the_mode and
  .test_five_modes_and_the_old_targets_mapping; test_context_menu
  Window.test_a_passage_is_named_at_the_top_with_its_page_edits. The same three fail with this patch taken out of the
  copy (logs/BEFORE.test_writing_line.kasandra.log, logs/BEFORE.test_context_menu.one.kasandra.log): they belong to the
  item "name", not to this one, and were left alone so the two patches do not collide.

## Not done (reported)
- A line ending in `group FIELD` with no count or total after it still gives its rows ungathered.
- `add NAME = ...` replaces an existing field NAME.
- A text that starts with @ in a comparison is read as a field name, quoted or not.
- `has` searches Python's text of a value; select of a field no row has gives empty values.
- `over`/`under` order text by its characters while sort folds capitals.
- Sheet names in the sheet lens match in any case.
- The whole suite was not run (the coordinator runs it at merge); no frames; nothing on the owner's machine.
