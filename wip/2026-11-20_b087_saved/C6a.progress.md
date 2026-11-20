# C6a progress: tables that check themselves (DONE)

Built on HEAD 4bcabd3. Patch: /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/b087/C6a.patch (applies to a clean export of HEAD).

Done
- workbench/tables.py (new): table cutter (header-anchored alignment by overlap, header-less clustering, tab and Markdown pipe
  tables; flagged lines never rows; a blank line ends a run), three cards (statement, datasheet, invoice) with header
  dictionary, roles, role fits (money = page_marks AMOUNT rule, units = page_marks.unit_at), exact closures (Fraction via
  math_units.rational, no float), the closure search over open readings, the COLUMNS turn (turns.register, grammars.columns,
  check_reading, fallback ASK_OWNER), read_page/read_text, kernel op library.table (read).
- Registrations: engineering_kernel.py (import, CAPABILITIES, dispatch), engineering_cli.py (FIELDS), mind_words.MODULES
  (+ workbench.tables, so her words are scanned). docs/GRAPHITE_0.1_REGISTRY.json regenerated in the copy and copied back.
- Smoke: 21 PASS, 0 FAIL (b087/C6a/smoke.out).

Not done (out of scope, said in result): no UI button "Read this table" (reference_qt.py not touched); Keep of a sheet to
office.datasheet.create / an everyday sheet not built; PDF word-layout cutting (datasheet_work.lines_in_region) not used:
text pages only; no real model run.
