{
 "report": "# Ground map for a read-only \"ripple\" (what would move if one number changed)\n\nRoot: `/home/user/Struthio`. Bare file names below mean `/home/user/Struthio/workbench/<name>`; `typed_pipeline.py`, `office_tables.py`, `office_work.py`, `evidence_contracts.py` are under `/home/user/Struthio/sdk/cli/arc1cli/`. Nothing was edited by me.\n\n## 0. Read this first: the tree moved while I was reading it\n\n- HEAD is `164fe3c` (0.4.2). At my first reads the working tree equalled HEAD.\n- Between 03:09Z and 03:13Z (2026-11-13) another writer changed the working tree. Last look (03:13Z): modified `activity.py`, `field_doubt.py`, `field_page.py`, `field_qt.py`, `field_service.py`, `shell2.py`; untracked new `field_ripple.py` (238 lines, still changing).\n- That writer is already wiring `field.ripple {id, set}`: added to `FIELDS` and `dispatch` in the working copy of `field_service.py`, and to `OBSERVER_OPERATIONS` in `activity.py`. `field_ripple.ripple(kernel, principal, field, ident, changes)` is at `field_ripple.py:111`.\n- Working-copy `field_doubt.py` (449 lines) imports `from .field_brief import standing` at line 362; `workbench/field_brief.py` did not exist at 03:12Z.\n- The staC seed went from `VERIFIED_SOURCE_BINDINGS` to `STALE` (changed: `workbench/activity.py`, `workbench/shell2.py`); I read `stacy_foundation.seed_status` before and after. While stale, `language.run` and `language.parse` refuse with \"Graphite seed/source binding is not current\" (`stacy_language.py:9-13, 53-54`), so every staC line and every check run through the Kernel refuses until the seed is rebuilt (`stacy_foundation.build_seed`, `stacy_foundation.py:531`; called from `tools/package_graphite.py:102`).\n- Line numbers for the six modified files are HEAD line numbers. All other files were identical to HEAD at last look.\n\n## 1. How a calculation names the cells it reads\n\nA calculation is a desk document with a `derivation`, written at `datasheet_work.py:249-251` (`replaces` added at 257):\n\n```\nderivation = {'profile': 'pdf-sheet-calculation-v1',            # REPORT, datasheet_work.py:8\n  'sheet': 'owner:<32 hex>',                                    # the Office sheet id\n  'sheet_revision': <sheet revision sha>,\n  'pdf': <the sheet's origin.pdf>,\n  'inputs': [{'symbol','cell','parameter','value','unit','conditions',\n              'basis': 'REVIEWED_PDF_ROW'|'WORKING_SHEET_EDIT','source_row','original_cells'}],   # :224-226\n  'calculation': <math_model.evaluate result>,\n  'recipe': {'expression', 'inputs': {symbol: cell}, 'output_unit'?, 'assumption'?},\n  'replaces'?: <id of the page this one took the place of>}\n```\n\n- Result: `derivation['calculation']['outputs'][0]['value']` = `{'rational','decimal','decimal_exact','unit','dimension'}` (`math_model.py:134-136`, `math_units.py:55-72`).\n- Inputs are always column B of a reviewed row with a literal number (`datasheet_work.py:197-202`). Units come from `C<row>` (208). A unit the exact calculator cannot carry is refused (211-218), so only time, frequency, voltage, current, power, memory and `1` reach a calculation (`stac/quantities.py:19-42`).\n- `documents.get` returns `{'document','summary','events','plain','source_state'}` (`documents.py:420-424`). `source_state.state` is `CURRENT`, `RECHECK_SHEET_CHANGED`, `PDF_SOURCE_REVIEW_REQUIRED` or `SHEET_UNAVAILABLE` (`datasheet_work.py:166-178`).\n- Staleness is per sheet revision, not per cell (174): any saved edit of the sheet puts every calculation on it into recheck.\n- Sheet record (`office.get`, `office_work.py:45`, `office_service.py:59-60`): `{'id','version','revision','document':{'schema','title','sheets':[{'id','name','cells':{addr: {'type','value','formula','formula_dialect','cache_state','number_format','unit'}}}]},'origin':{'profile','pdf','reviewed_rows':[{'source_row','parameter','value','unit','conditions','sheet_row','original_cells','source_words','ocr_uncertain'}]},'authority','engineering_acceptance','source_state','formula_values'}`. Columns are A parameter, B value, C unit, D conditions, E page, F extraction; row 1 is headers (`datasheet_work.py:10, 142-157`).\n\n**Sheet + cell \u2192 calculations.** No function does this at HEAD. Compare `derivation['sheet'] == sheet_id` and `any(i['cell'] == cell for i in derivation['inputs'])`, and skip pages named in another page's `derivation.replaces` (`field_source.py:209-210, 409-413`).\n- Via the Field: `field.feeds('office:' + sheet_id)` gives the sheet\u2192calculation wires, label `'cells B2, B3'` (`field_source.py:219, 226`). The label is text; the Field reads at most the 300 newest pages (44, 201).\n- The desk store has no index by sheet (`project_desk.py:86-87`).\n- The in-flight `field_ripple.py:151-157` does exactly this comparison.\n\n## 2. `datasheet_work.what_if`\n\n- Signature: `def what_if(document, changes)` (`datasheet_work.py:268`). `document` is the `document` member of `documents.get` (`field_service.py:102`).\n- `changes` keys: an input's symbol or its cell, matched case-insensitively (276-281). Values: text that passes `math_units.rational` (285-289; `math_units.py:41-47`): decimal, `a/b`, or exponent form.\n- Returns (311-315): `{'calculation','expression','says_now':'<decimal> <unit>'|'','would_be':'<decimal> <unit>','exact':'<rational> <unit>','set':'i = 320 mA','rows':[{'input','cell','parameter','value','set','unit'}],'changed':'nothing'}`. `field.whatif` adds `'schema':'graphite.field/1'` and `'id'`.\n- Arithmetic is exact rational (`fractions.Fraction`), no float (`math_units.py:45`, `math_model.py:90-124, 147`). `would_be` is the decimal rendering, rounded to 28 digits when not terminating (`math_units.py:55-64`); `decimal_exact` is not passed through.\n- Refuses: not a sheet calculation (273-275); a key that is not an input (282-284); not a plain number (285-288); no exact result, e.g. zero denominator (306-309). `field_service.whatif` adds: 1 to 8 entries, string values of 1 to 40 characters (`field_service.py:100-101`).\n- Units of the supplied value are **not** checked. The number is taken in the input's recorded unit (292, 301); `\"320 mA\"` is refused as not a plain number. No sign or range check: `-5` and `0` are accepted (I ran it).\n- It never reads the sheet: untouched inputs keep the values recorded on the page (269-272, 292), which may be stale.\n- **Pitfall I confirmed by running it:** when two symbols read the same cell, a cell key sets only the last symbol. `(a+b)*i` with a and b both on B2: `{\"B2\":\"10\"}` gave 44 W, not 40 W. Set by symbol for every input whose `cell` matches.\n\n## 3. How a finding is tied to numbers\n\n- The text lives in `inv_claims.text` (`investigations.py:82-83, 404`). No operation edits it; a rewrite is a new claim plus `RETIRE` (`field_do.py:159-163`). The Field puts the whole text in `FieldObject.title` (`field_source.py:264`).\n- `_moved(reader)` (`field_source.py:434-444`) exists only after a real recheck. It follows `derivation.replaces` and returns `(old words, new words, title)`, the words being `'%s %s' % (decimal, unit)` (211-213).\n- The \"says X; now Y\" mark (`field_source.py:417-422`): a finding in state `current` goes to `recheck` when `was in obj.title and now not in obj.title`. That is a substring test. `field_do.py:156, 289` and `field_doubt.py` HEAD:206-208 reuse it.\n- `field_doubt._quantities` (HEAD:149-166) collects `{unit: [(float, where)]}` from each sheet's reviewed rows (B value, C unit as written) and each calculation's result.\n- `_claim` (HEAD:209-217) runs the regex `(?<![\\w.])(-?\\d+(?:\\.\\d+)?)\\s*([A-Za-z\u00b5\u03a9\u00b0%]+)` over the title. The unit must equal a desk unit string exactly; the number matches by float within 1e-9 (HEAD:61-62). There is no unit conversion.\n- `quoted_calculation(kernel, principal, obj, field)` (HEAD:241-251) returns the first calculation whose result unit and decimal match a number in the title: `(calc object, decimal, unit)`.\n\n## 4. Checks: storage, evaluation, dry run\n\nStorage (`investigations.py:78-93`):\n- `inv_checks(id, claim, program, oracle, expect, value, refutes, created)`. The column is `refutes`; `refutes_on_fail` is only the argument name (59, 424). `expect` is one of `NONEMPTY, CONTAINS, NOT_CONTAINS, COUNT_AT_LEAST` (41). A check cannot be edited or removed.\n- The outcome is on the step, not the check: `inv_steps(id, investigation, seq, kind, purpose, program, inputs, input_key, check_id, outcome, result_digest, summary, duplicate_of, authority, started, finished, stale)`.\n- `investigation.sheet` \u2192 `checked` rows: check columns plus `claim_text, last_outcome, last_step, last_authority`. `last_outcome` is `NOT_RUN`, `STALE` or the step's outcome (238-244).\n- `investigation.path` steps (355-370): `{kind:'SOURCE', address, digest, counts, source_state, direction, note, independence}` or `{kind:'CHECK', step, program, inputs:{address: digest}, outcome, result_digest, ran_with, counts, \u2026}`. Staleness shows as `counts: False`.\n\nEvaluation:\n- `continue_` (294) \u2192 `execute` (156-191) \u2192 `route_program` (`stac_bridge.py:22-30`) \u2192 `language.run` \u2192 `stacy_language._execute_plan` (116-127) \u2192 `typed_pipeline.apply` (`typed_pipeline.py:212`) \u2192 `oracle_holds(expect, value, result)` (`investigations.py:108-119`).\n- `oracle_holds` searches the casefolded JSON of the whole result, which includes the plan and the program text.\n- `execute` always writes a step row, and may write evidence and counters (183-190). `language.run` is not an observer operation, so it is journaled (`activity.py:8-33`).\n- A step's inputs are only the `@kind:id` addresses in the program (43, 147-153). `refresh` stales only steps that hold the changed address (342-347). Only `NOT_RUN`, `FAILED`, `STALE` are due again (265).\n\nDry run: no function does it end to end, but the parts are pure.\n1. `stacy_language.source(text)` (38-44) and `typed_pipeline.parse(text)` (44-106) give the plan without the seed check.\n2. Read the source with the plan's call; the value is `result['object']` for an `@address` (`stacy_language.py:118-120`).\n3. Substitute in memory: `value['document']['sheets'][0]['cells']['B3']['value']`.\n4. `typed_pipeline.apply(value, plan['transforms'], 200)`.\n5. Wrap as `{'schema':'arc.stacy-pipeline-result/1','plan':plan,'rows':rows,'execution':'REGISTERED_READ_ONLY_KERNEL_CALL','model_calls':0}` and call `investigations.oracle_holds`.\n\nI ran this in memory with no Kernel:\n- A narrowed cell check flips true \u2192 false when B3 goes 280 \u2192 320.\n- A whole-record `CONTAINS \"280\"` stays true, because `origin.reviewed_rows` keeps the old value.\n- A threshold written as `\u2026 | where value.decimal at most 6 | \u2026` with `NONEMPTY` flips correctly.\n\nPrograms starting with a word in `START_WORDS` (`stac_bridge.py:18-19`) take the `stac.run` route and are not covered. Joins need their side rows resolved first (`stacy_language.py:74-82`).\n\n## 5. Other records that depend on a cell or a result\n\n| Record | Field that ties it to the number | Where |\n|---|---|---|\n| Calculation | `derivation.sheet`, `sheet_revision`, `inputs[].cell` | `datasheet_work.py:249-251` |\n| Finding, by evidence | `inv_sources.address` (`office:owner:<hex>` or `document:<id>`), digest of the whole read | `investigations.py:141-144, 327-352` |\n| Finding, by check | `inv_checks.program` text; `inv_steps.inputs` | `investigations.py:147-153` |\n| Finding, by words | number + unit in `inv_claims.text` | section 3 |\n| Condition card | `document`, `inputs[]{'block','index','start','end','text','value','unit'}`, `result_block`, `result{'value','unit','text'}` | `conditions.py:49, 175-178` |\n| Plain page | none; only its words (`documents.get` \u2192 `plain`) | `field_source.py:216-217` |\n| Agenda watch | `agenda_items.program` (staC text holding the record id), `watch`, `last_rows` | `agenda.py:76-84, 221-223, 357-369` |\n| Job | none on the Field; Office conversion jobs hold the sheet id through their plan | `field_source.py:294-311`, `office_service.py:123-124, 170-177` |\n| Notebook block | target `{'type':'office','object_id','sheet'}` | `notebook_service.py:56-66` |\n\n- A condition card moves only when its own document is saved or edited (`documents.py:380, 394, 398-404`; `conditions.py:182-199`). Nothing ties it to a sheet cell or a derivation. A recheck writes a new page (`datasheet_work.py:263`), so a card on the old page stays `CURRENT`. Cards are created only by `profile_numbers.py:111`, and only `sum` exists (`conditions.py:47`).\n- The Field shows only cards that are not current (`field_source.py:285`). Use `conditions.list {document}` for the rest; it returns at most 100 (`conditions.py:206`).\n- A Field watch on a calculation reads `source_state.state` (`field_do.py:73, 88`), so it reports a change after any edit of its sheet. A Field watch on a sheet reads the PDF source state (`field_source.py:179`) and does not see cells.\n- `agenda.view` has read scope but updates rows (`agenda.py:143-165`). Agenda items are not on the Field.\n- `field_do.sweep` (297-309) marks every finding of an investigation whose current source digest moved.\n\n## 6. The wires\n\n```\n@dataclass class FieldLink:  source: str; target: str; label: str = ''; stale: bool = False     # field_model.py:58-63\nField.get(self, ident)      -> FieldObject | None                                                 # :112\nField.feeds(self, ident)    -> [link for link in self.links if link.source == ident]              # :115\nField.fed_by(self, ident)   -> [link for link in self.links if link.target == ident]              # :118\nReader.link(self, source, target, label='', stale=False)                                          # field_source.py:125\nread_field(kernel, principal, title='', skip=()) -> (Field, reader)                               # field_source.py:403\n```\n\n- `FieldObject(id, kind, title, role, state, lines, where, target, tag, stac, column, touched)` (`field_model.py:35-55`). Ids: `intake:<id>`, `office:owner:<hex>`, `document:<hex>`, `claim:<hex>`, `condition:<id>`, `job:<id>`. `target` is `{'kind':'office'|'document'|'investigation'|\u2026,'id':\u2026}`.\n- `Field.__post_init__` (89-109) keeps one wire per (source, target), ORs `stale`, keeps the first non-empty label, and drops wires with an end not on the Field.\n- Wires that exist:\n  - source \u2192 sheet, label `page N` (`field_source.py:198`)\n  - sheet \u2192 calculation, label `cells \u2026` (226)\n  - address \u2192 finding for SOURCE evidence, label `supports` / `opposes` (272)\n  - address \u2192 finding for CHECK evidence, label from `CHECK_WORDS` (273-278)\n  - page \u2192 non-current condition, label `its words changed` (292)\n- There are no wires for calculation \u2192 plain page, calculation \u2192 finding (unless the claim's evidence names `document:<calc id>`), jobs, or agenda items.\n- An existing downstream walker: `field_service.trace` (63-91), breadth-first, `REACH = 8`.\n\n## 7. What makes a hypothetical evaluation wrong or impossible\n\n1. Findings are free text. No rule parses a comparison such as \"allows 6 W\"; only a check written as a staC threshold can be re-evaluated.\n2. The check that `field_do.py:146-155` binds on a calculation's result uses `documents.get {\"id\":\u2026}` with no `@` address. Consequences:\n   - no wire to the finding (`field_source.py:275`);\n   - `refresh` never stales it;\n   - after a pass it is never due again;\n   - it reads the old page id for ever, because a recheck makes a new page.\n   A ripple that walks only wires, or only checks naming `office:<sheet>`, misses it.\n3. Whole-record `CONTAINS` checks pass whatever the cell says (`weak_check`, `field_doubt.py` HEAD:221-238).\n4. The duplicate rule (`investigations.py:163-166, 184`): a rerun with the same inputs after an earlier pass records no new evidence, even on failure.\n5. Word matching is substring and format-bound: \"13.36 W\" contains \"3.36 W\"; \"3.36W\", \"3360 mW\" and \"3.4 W\" are missed by `_moved`. Matching uses floats.\n6. `what_if` uses recorded inputs, not the sheet, and has the same-cell-two-symbols fault.\n7. Source evidence is whole-record: any cell edit changes the digest, so the claim goes to review whether or not its number moved.\n8. Ceilings hide records: 60 sheets, 300 pages, 6 investigations, 40 claims each, 20 jobs (`field_source.py:43-49, 234, 299`).\n9. `documents.get \u2026 | select \u2026` without a leading `pick` reads the `events` list (`typed_pipeline.py:215-217`). A staC line cannot contain `< > ;` (16) and has at most seven transforms (25).\n10. Sheets live in the owner's profile store, and `office.*` requires identity `desktop-owner` (`office_service.py:61-62`).\n\n## Hook points\n\n- A new field read needs only `field_service.FIELDS` plus its `dispatch` branch. `CAPABILITIES` (`engineering_kernel.py:225`), the schema (`engineering_cli.py:89, 184`) and the route (`engineering_kernel.py:624`) follow automatically.\n- The hand-kept list is `activity.OBSERVER_OPERATIONS` (HEAD `activity.py:33`). `activity.py` is a seed input, so touching it stales the seed.\n- UI: `field_qt.py` HEAD:230-246 (keys), `field_page.py` HEAD:300-324 (trace, doubt), `shell2.py` HEAD:1792-1822 (what-if in words), `context_menu.py:1257-1285`.\n- `references.impact` (`reference_service.py:548-563`) is house precedent for a preview: `'preview_only': True, 'mutations': 0, 'coverage': 'CAPTURED_DEPENDENCIES_ONLY_UNTRACKED_IMPACT_UNKNOWN'`.\n\n## The in-flight `field_ripple.py` against this map (as seen 03:13Z, still moving)\n\n- Line 161 passes cell keys to `what_if`: the same-cell fault applies.\n- Line 198 looks only at checks whose program contains `office:<sheet>`: calculation-result checks (point 7.2) are not seen.\n- Checks are judged by a regex on `value` (79-101), not by evaluating the program.\n- No condition cards, no agenda watches.\n- Calculations on the sheet that do not read the cell are counted `untouched`, though a real save would put them all in recheck.",
 "key_locations": [
  {
   "what": "what_if(document, changes): signature, keys, refusals, return dict",
   "file": "/home/user/Struthio/workbench/datasheet_work.py",
   "line": 268
  },
  {
   "what": "derivation record written by report(): profile, sheet, sheet_revision, inputs, calculation, recipe (replaces at 257)",
   "file": "/home/user/Struthio/workbench/datasheet_work.py",
   "line": 249
  },
  {
   "what": "derivation.inputs item shape {symbol, cell, parameter, value, unit, conditions, basis, source_row, original_cells}",
   "file": "/home/user/Struthio/workbench/datasheet_work.py",
   "line": 224
  },
  {
   "what": "report_state: per-sheet-revision staleness (RECHECK_SHEET_CHANGED)",
   "file": "/home/user/Struthio/workbench/datasheet_work.py",
   "line": 166
  },
  {
   "what": "recheck dispatch: new page made from prior recipe, replaces the old one",
   "file": "/home/user/Struthio/workbench/datasheet_work.py",
   "line": 318
  },
  {
   "what": "field.whatif service wrapper and its limits on 'set' (HEAD line; working copy is being modified)",
   "file": "/home/user/Struthio/workbench/field_service.py",
   "line": 94
  },
  {
   "what": "FIELDS / SCOPES / OBSERVERS for field.* reads (HEAD line; working copy now also has field.ripple)",
   "file": "/home/user/Struthio/workbench/field_service.py",
   "line": 29
  },
  {
   "what": "field.trace: existing breadth-first walk along wires, REACH = 8 (HEAD line)",
   "file": "/home/user/Struthio/workbench/field_service.py",
   "line": 63
  },
  {
   "what": "FieldLink(source, target, label, stale)",
   "file": "/home/user/Struthio/workbench/field_model.py",
   "line": 58
  },
  {
   "what": "Field.get / feeds (115) / fed_by (118)",
   "file": "/home/user/Struthio/workbench/field_model.py",
   "line": 112
  },
  {
   "what": "Field.__post_init__: one wire per pair, stale ORed, wires with a missing end dropped",
   "file": "/home/user/Struthio/workbench/field_model.py",
   "line": 89
  },
  {
   "what": "Reader.pages_and_calculations: sheet -> calculation wire, label 'cells ...', results and replaces recorded",
   "file": "/home/user/Struthio/workbench/field_source.py",
   "line": 200
  },
  {
   "what": "Reader.findings: claim objects and wires from SOURCE (272) and CHECK (273-278) path steps",
   "file": "/home/user/Struthio/workbench/field_source.py",
   "line": 230
  },
  {
   "what": "Reader.totals: only non-current condition cards shown, wire page -> condition",
   "file": "/home/user/Struthio/workbench/field_source.py",
   "line": 281
  },
  {
   "what": "read_field and the 'says X; now Y' marking of findings (417-422)",
   "file": "/home/user/Struthio/workbench/field_source.py",
   "line": 403
  },
  {
   "what": "_moved(reader): (old words, new words, title) from derivation.replaces chains",
   "file": "/home/user/Struthio/workbench/field_source.py",
   "line": 434
  },
  {
   "what": "_quantities: desk values by unit from sheets and calculation results (HEAD line; working copy 274)",
   "file": "/home/user/Struthio/workbench/field_doubt.py",
   "line": 149
  },
  {
   "what": "_claim 'its numbers': regex over finding text matched against desk values (HEAD lines 205-217; working copy 330-341)",
   "file": "/home/user/Struthio/workbench/field_doubt.py",
   "line": 205
  },
  {
   "what": "weak_check: a check that cannot fail (HEAD line; working copy 380)",
   "file": "/home/user/Struthio/workbench/field_doubt.py",
   "line": 221
  },
  {
   "what": "quoted_calculation: the calculation whose result a finding's words carry (HEAD line; working copy 400)",
   "file": "/home/user/Struthio/workbench/field_doubt.py",
   "line": 241
  },
  {
   "what": "_claim steps: writes investigation.add_source / investigation.check lines (weak-check repair 137-144, calc-result check 146-155 with no @address)",
   "file": "/home/user/Struthio/workbench/field_do.py",
   "line": 113
  },
  {
   "what": "_watch: agenda.add watch step; program is the object's staC line",
   "file": "/home/user/Struthio/workbench/field_do.py",
   "line": 62
  },
  {
   "what": "sweep: read-only digest comparison of investigation sources",
   "file": "/home/user/Struthio/workbench/field_do.py",
   "line": 279
  },
  {
   "what": "Investigation tables: inv_sources, inv_claims, inv_checks, inv_steps, inv_evidence",
   "file": "/home/user/Struthio/workbench/investigations.py",
   "line": 78
  },
  {
   "what": "oracle_holds(expect, value, result): pure oracle over the whole result JSON",
   "file": "/home/user/Struthio/workbench/investigations.py",
   "line": 108
  },
  {
   "what": "execute: runs a check program and always writes a step row (duplicate rule 163-166, evidence 184-188)",
   "file": "/home/user/Struthio/workbench/investigations.py",
   "line": 156
  },
  {
   "what": "inputs_of / ADDRESS (43): only @kind:id addresses become step inputs",
   "file": "/home/user/Struthio/workbench/investigations.py",
   "line": 147
  },
  {
   "what": "sheet(): 'checked' rows with last_outcome NOT_RUN / STALE / step outcome",
   "file": "/home/user/Struthio/workbench/investigations.py",
   "line": 231
  },
  {
   "what": "refresh: source CHANGED, evidence and steps stale, claims NEEDS_REVIEW",
   "file": "/home/user/Struthio/workbench/investigations.py",
   "line": 327
  },
  {
   "what": "path(): SOURCE and CHECK step shapes",
   "file": "/home/user/Struthio/workbench/investigations.py",
   "line": 355
  },
  {
   "what": "investigation.check dispatch: stores program, oracle, expect, value, refutes",
   "file": "/home/user/Struthio/workbench/investigations.py",
   "line": 417
  },
  {
   "what": "route_program: check program -> language.run (or stac.run for START_WORDS)",
   "file": "/home/user/Struthio/workbench/stac_bridge.py",
   "line": 22
  },
  {
   "what": "source() (38), _compile_plan (46, seed check 53-54), _execute_plan (116): the staC pipeline run and its result envelope",
   "file": "/home/user/Struthio/workbench/stacy_language.py",
   "line": 116
  },
  {
   "what": "typed_pipeline.parse (44) and apply (212): pure in-memory pipeline; auto-pick of 'events' etc. at 215-217",
   "file": "/home/user/Struthio/sdk/cli/arc1cli/typed_pipeline.py",
   "line": 212
  },
  {
   "what": "Condition card create: record shape and input span keys (SPAN_KEYS at 49)",
   "file": "/home/user/Struthio/workbench/conditions.py",
   "line": 152
  },
  {
   "what": "refresh_document: cards go stale only when their own document is written",
   "file": "/home/user/Struthio/workbench/conditions.py",
   "line": 182
  },
  {
   "what": "documents.get result shape incl. source_state for calculations",
   "file": "/home/user/Struthio/workbench/documents.py",
   "line": 415
  },
  {
   "what": "office.get wrapper; owner() identity requirement at 61",
   "file": "/home/user/Struthio/workbench/office_service.py",
   "line": 59
  },
  {
   "what": "Office._get: sheet record shape and revision hash",
   "file": "/home/user/Struthio/sdk/cli/arc1cli/office_work.py",
   "line": 45
  },
  {
   "what": "rational(): accepted number strings; number_record (55) decimal/rational rendering",
   "file": "/home/user/Struthio/workbench/math_units.py",
   "line": 41
  },
  {
   "what": "evaluate(): exact rational result record, 'arithmetic': 'EXACT_RATIONAL'",
   "file": "/home/user/Struthio/workbench/math_model.py",
   "line": 127
  },
  {
   "what": "Kernel unit table (what a calculation input's unit may be)",
   "file": "/home/user/Struthio/workbench/stac/quantities.py",
   "line": 19
  },
  {
   "what": "agenda.add: watch needs a staC program (221-223); watch_words at 357; view() updates rows at 162-165",
   "file": "/home/user/Struthio/workbench/agenda.py",
   "line": 198
  },
  {
   "what": "OBSERVER_OPERATIONS: hand-kept list holding field.* names (HEAD line 33); file is a seed input",
   "file": "/home/user/Struthio/workbench/activity.py",
   "line": 33
  },
  {
   "what": "CAPABILITIES includes field_service.SCOPES (225); dispatch route at 624; observer check at 510",
   "file": "/home/user/Struthio/workbench/engineering_kernel.py",
   "line": 225
  },
  {
   "what": "seed_status: staC refuses unless VERIFIED_SOURCE_BINDINGS; SEED_INPUTS at 200; build_seed at 531",
   "file": "/home/user/Struthio/workbench/stacy_foundation.py",
   "line": 366
  },
  {
   "what": "Stacy's what-if in words (HEAD line; working copy is being modified)",
   "file": "/home/user/Struthio/workbench/shell2.py",
   "line": 1792
  },
  {
   "what": "references.impact: existing preview-only impact read and its honesty fields",
   "file": "/home/user/Struthio/workbench/reference_service.py",
   "line": 548
  },
  {
   "what": "In-flight, untracked draft of the ripple by another writer: ripple() (what_if keyed by cell at 161; checks filtered by sheet address at 198). File is still changing.",
   "file": "/home/user/Struthio/workbench/field_ripple.py",
   "line": 111
  },
  {
   "what": "Only creator of condition cards (numbers-on-the-page profile)",
   "file": "/home/user/Struthio/workbench/profile_numbers.py",
   "line": 111
  }
 ],
 "gaps": [
  "The working tree changed during this mapping (another writer, not me). At 03:13Z on 2026-11-13: modified activity.py, field_doubt.py, field_page.py, field_qt.py, field_service.py, shell2.py; untracked field_ripple.py. Line numbers for those six modified files are HEAD (164fe3c) numbers; field_ripple.py line numbers are from a file that was still being rewritten and may have shifted.",
  "An implementation of field.ripple is already being written into the working tree (workbench/field_ripple.py, wired in the working copies of field_service.py and activity.py). I could not determine who is writing it or whether it is the addition this map was requested for.",
  "Working-copy field_doubt.py imports workbench/field_brief.py (line 362), which did not exist at 03:12Z. I did not run it, so I cannot say what field.doubt does on a page in that state.",
  "The staC seed read STALE at 03:12Z (changed sources: workbench/activity.py, workbench/shell2.py). I did not rebuild it and did not confirm the refusal through Kernel.dispatch; the refusal is read from stacy_language.py:9-13.",
  "No live records were read: I opened no workspace database and no Office catalog, and dispatched nothing through the Kernel. Whether real workspaces hold condition cards on calculation pages, checks without @addresses, or two symbols on one cell is unknown. All shapes are from the code that writes them.",
  "The dry-run check evaluation was confirmed only with pure functions on synthetic in-memory values (typed_pipeline.parse/apply, investigations.oracle_holds, stacy_language.source). The full plan dict that language.parse returns (principal, seed_id, permission, plan_id) is read from code, not observed.",
  "Check programs that start with a START_WORDS word take the stac.run route (stac_bridge.py:113-124, workbench/stac/runtime.py). I did not read that evaluator, so I cannot say how to dry-run those.",
  "How the Office editor writes one cell (cell_edits.py, sheet_edit.py, sheet_workbench_qt.py) was not traced beyond office.save (office_service.py:152) and Office._save (office_work.py:65-74). In particular I did not confirm that origin.reviewed_rows is never rewritten on a save, only that _save updates the payload column.",
  "The jobs.list row shape and any job-to-sheet tie beyond the Office conversion plan were not traced in the Kernel; the Field uses only id, state, goal, tool, updated (field_source.py:294-311).",
  "Notebook references to an Office sheet were read only at notebook_service.py:49-66; how a notebook reports a changed sheet was not traced.",
  "Other possible dependents were not examined: reason graphs (reasons.get / reasons.impact), math.get saved calculations, typed artifacts, slate contexts, agent-loop step inputs beyond profile_numbers.py:66-70.",
  "No existing rule can re-evaluate a finding whose meaning is a comparison in prose (for example \"allows 6 W\"). I found no record field that stores a limit or a relation for a claim; only a check written as a staC threshold carries one."
 ]
}