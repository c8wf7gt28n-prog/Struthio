# lines: independent review. FINISHED. Verdict: accept_after_fixes

Area: work/b084/lines/review/ (scripts setup.sh, t.sh, all.sh, all2.sh, mutate.py, before_after.sh, probe1..4.py; logs/). The copy of the
tree is deleted. Nothing in /home/user/Struthio was touched.

## What was run, with results
- Fresh copy of the tracked tree, lines.patch applied with patch -p1 (exit 0), seed made current (record_registry --check: no differences).
- Default look, the ten modules: test_line_rules 19, test_context_menu 44, test_typewriter_faces 13, test_writing_line 32, test_graphite 29,
  test_release_check 22, test_memory_settings 9, test_project_desk 11, test_desk_scenes 5, test_desk_acts 28 = 212 tests, 0 failed.
- Kasandra look, same modules: 212 tests, 3 failed (test_writing_line ModeTests.test_destination_hint_names_the_mode and
  .test_five_modes_and_the_old_targets_mapping; test_context_menu Window.test_a_passage_is_named_at_the_top_with_its_page_edits). All three
  assert "Stacy" where "Kasandra" is shown; with the patch reversed in the copy the same three fail (2 of 32, and 1 of 1). Not this patch's.
- Nine more modules that run lines indirectly (test_stacy_hand 19, test_kasandra 20, test_agent_loop 24, test_related 11,
  test_return_thread 9, test_cabinet_actions 9, test_browse 6, test_paper 17, test_documents 13) = 128 tests, 0 failed, in each look.
- mutate.py: 32 single-piece reverts of the fix, each against test_line_rules: 30 make new tests fail (every one of the seven faults is
  really guarded, and the callers' pieces too). Not noticed: the "numbers are too large" refusal of a total (no test), and the unary
  minus's precedence 3 against 1 (the two are equivalent; not a gap).
- probe2.py on the unpatched and the patched tree: all seven faults reproduce before and are gone after.
- probe1.py: 4000 random add expressions with a minus before a value agree with Python (0 mismatches); same() is transitive over 43 mixed
  values; = and is not split the rows in two for plain values; over/under agree with = for numbers.
- Through the Kernel: a quoted ; in a where runs; an address with ; (quoted or not, first source or joined) is refused; the type bar
  classes a line with a quoted ; as a line; 2000 rows cost 3 to 6 ms a line (2 to 4 before).
- The hunks of faults.patch and fixture.patch on tools/check_hatch.py and of name.patch on tests_integrated/test_context_menu.py apply
  on top of this patch; name.patch's sweep allows the parser's "Stacy language" refusal by file and words, which this patch keeps.
- No owner data, no "Programs", no key, no "pipeline"/"staC"/"Lain" in any new on-screen string. No file that should not be there.

## must_fix
1. Totals and add still round to six decimal places in silence (typed_pipeline.py: the total's `round(value,6)`, a line this patch
   rewrites, and calculate's `round(result,6)`). max q over 2.5e-6 and 1e-6 answers 3e-06, a value no row holds; sum q over 1.5e-7 and
   2.5e-7 answers 0.0; add x = q*2 with q 2.5e-7 answers 0.0. Through the Kernel: a CSV column Leak of 0.0000025, 0.0000015, 0.000001,
   0.000001 and `@files:parts.csv | rows | max Leak` gives 3e-06. It was there before the patch, but it is the class the task said to fix
   or list (silent coercion in the evaluator) and it is neither fixed nor in not_done, while the refusal now says "Nothing is left out
   in silence".
2. Two different numbers written as text are one value when a float cannot tell them apart (new with this patch: = was exact by type
   before, group and join exact by text). join on k: "1234567890123456.78" matches "1234567890123456.79"; group t | count gathers
   "1731500000.123456789" with "1731500000.123456790"; where v=0 keeps the text "1e-400". Text a float cannot hold (more than 15
   significant digits with a fraction or exponent; underflow to 0) should stay text, as "1e999" already does, or be compared exactly.

## should_fix
1. where a=@b compares with the text "@b"; is not @b, over @b and the rest compare with column b. Rows [{v:1,w:1},{v:1,w:2}]: where v=@w
   gives none, where v is not @w gives the second: the first is on neither side. The panel offers "is not @home" for a text value and the
   step compares with a column named home. Old fault; not_done names half of it. compare()'s `op=='='` branch cannot be reached from parse.
2. The Then menu's word() and the panel's literal() quote differently. word() leaves true, false, null and NaN bare and deletes quote
   marks: "is true" writes where f = true and keeps 0 of the 2 rows that hold the text; "is NaN" does not run. Use one function.
3. A CSV cell NaN or inf makes every line on that file refuse with "Out of range float values are not JSON compliant" (the file reader
   makes the cell a float; apply's size check raises). The same reader turns 0805 into 805, "1,2" into 12 and 1.10 into 1.1 before the
   rule can apply. Old, outside the evaluator, not in not_done.
4. For the owner to confirm: exponent text is a number ("1E1" gathers with "10", "2E4" sorts as 20000: hex offsets), though 0805 is kept
   as text for that very reason; group and join now take "1.10" and "1.1" as one value (the task said join keys "exactly as written");
   a total carries `blank` only when some row is blank, so the answer's shape, and whether group blank | max q runs, depend on the data.
5. where FIELD is not X (every named comparison) drops rows that lack the field, while group gathers them under nothing. Old, not listed.
6. Words: a wrongly written step says its form twice (where 384 letters, join 408); the Then menu shows the first 80, so none of the
   help. HELP add does not say a division by zero or an existing NAME. "Those signs cannot be part of a line" should now say a
   semicolon is text inside double quotes.
7. No test for the "numbers are too large" refusal of a total. The release note should say saved lines can answer differently after
   0.8.4 (join by exact keys, sum refusing on text, =1 keeping "1", numeric text sorted by value).
8. add x = a + b with whole numbers above 1e308 gives no value: all four operations are worked out before one is chosen.
