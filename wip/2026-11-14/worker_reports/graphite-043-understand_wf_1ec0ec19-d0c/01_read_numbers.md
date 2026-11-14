{
 "report": "# Numbers, units and totals on the desk: ground truth for new doubt rules\n\nPaths: `W/` = `/home/user/Struthio/workbench/`, `S/` = `/home/user/Struthio/sdk/cli/arc1cli/`.\n\n## 0. Read this first: the tree changed under me while I was reading\n\nSomeone else is building in this working tree right now. None of it is mine; I edited nothing.\n\n- At HEAD (`164fe3c`) `W/field_doubt.py` is 290 lines. At 03:09:03 UTC it was rewritten in place to 449 lines (+166/\u22127, uncommitted).\n- By 03:12:49 UTC `git status` showed `M` on `W/activity.py`, `W/field_doubt.py`, `W/field_page.py`, `W/field_qt.py`, `W/field_service.py`, `W/shell2.py`, and a new untracked `W/field_ripple.py` (a `field.ripple` read operation).\n- The uncommitted `field_doubt.py` already contains a version of your candidates (a) and (c): `_counted_twice` (WT:179-199), `_twice_in_run` (WT:202-224), `_said_otherwise` (WT:232-254), plus `_made_from` (WT:258-271), `_unplaced` (WT:345-351), `_page` for kind `document` (WT:355-377) and a per-pass read cache `_Once` (WT:74-83).\n- `_page` does `from .field_brief import standing` (WT:362) and `W/field_brief.py` does not exist (checked 03:12:49). `ModuleNotFoundError` is caught neither by `doubts_for` (WT:436) nor by `Kernel.dispatch` (`W/engineering_kernel.py:528`). By reading, `field.doubt` on a desk holding a plain page raises as the tree stands.\n\nLine numbers below for `field_doubt.py` are given as `HEAD:n` and `WT:n` (working tree at mtime 03:09:03). Every other file cited was unmodified against HEAD at 03:12:49, except `field_service.py`, where I give both.\n\n## 1. Rules that already exist\n\nAt HEAD:\n- **Calculation** (`_calculation` HEAD:66-111): agrees with its sheet, from `source_state.state` (71-76); inputs as the page says, `basis != 'REVIEWED_PDF_ROW'` (78-85); conditions missing or differing across inputs (86-94); note of a 1 % sensitivity via `datasheet_work.what_if` (95-110).\n- **Sheet** (`_sheet` HEAD:115-145): its source (121-122); cells A\u2013D against `origin.reviewed_rows` (129-136, 143-144); `ocr_uncertain` row (137-138); row without unit (139-140); row without condition (141-142).\n- **Finding** (`_claim` HEAD:169-218): independent support and opposition (175-184); has a check, check outcome, check that cannot fail (186-204, `weak_check` 221-238); its words carry a superseded result, `field.moved` (206-208); each number-with-unit in its words is or is not a desk value (209-217).\n- **Condition** (HEAD:254-259): card state. **Source** (HEAD:262-267): admitted, and what rests on it.\n\nAdded in the uncommitted tree:\n- **Counted twice** (WT:146, 179-224): arithmetic on stored values in one column of `sheets[0]`.\n- **Another sheet differs** (WT:149, 232-254): same column-A name on another reviewed sheet with another value or unit; verdict `note`.\n- **Made from two desk values** (WT:258-271, 345-351): a finding's number that is the sum or difference of two same-unit desk values.\n- **Page** (WT:355-377): every quantity in a page's words against the desk.\n\n## 2. How a reviewed sheet is stored (Q1)\n\nStore: SQLite table `office_documents(id, version, payload, origin, original)` (`S/office_work.py:36`). `office.get` returns (`S/office_work.py:45`, `W/office_service.py:59-60`):\n\n```\n{'id':'owner:<32hex>','version':int,'revision':<sha256>,'document':{...},'origin':{...},\n 'authority':'OWNER_WORKING_OFFICE_COPY','engineering_acceptance':False,\n 'source_state':{'state':...},'formula_values':'STORED_VALUES_ARE_NOT_RECALCULATION_EVIDENCE'}\n```\n\nEvery `office.*` operation requires principal identity `desktop-owner` (`W/office_service.py:61-62,136`).\n\n**Document** (`S/office_tables.py:46-51,78-79`): `{'schema':'arc.office-table/1','title','sheets':[{'id':<32hex>,'name','cells':{'A1':cell,...}}]}`. A reviewed sheet has one sheet named `'Reviewed PDF data'` (`W/datasheet_work.py:162`).\n\n**Per cell**, exactly seven keys, enforced at `S/office_tables.py:60`, built at `:43-44`:\n\n```\n{'type','value','formula','formula_dialect','cache_state','number_format','unit'}\n```\n\n- `type` is one of `('text','number','boolean','date','duration','error','blank','excel-date-serial')` (`:19`).\n- A number's `value` is a decimal string kept verbatim (`:25-30`).\n\n**Layout of a reviewed sheet** (`W/datasheet_work.py:10,142-157`):\n- Row 1 holds the headers `('Parameter','Value','Unit','Conditions','PDF page','Extraction')`.\n- Data rows start at row 2. A = parameter (text). B = value. C = unit (text). D = conditions (text). E = PDF page as a number cell with no unit. F = `'Reviewed OCR'` or `'Reviewed native text'`.\n- B is `cell('number', value, unit=row['unit'])` when the value parses as a decimal, otherwise a text cell with `unit=''` (`:150-153`).\n- So the unit is recorded three times per row: `B<n>.unit`, `C<n>.value`, and `reviewed_rows[].unit`.\n\n**Origin** (`W/datasheet_work.py:163`): `{'profile':'reviewed-pdf-table-v1','pdf':source,'reviewed_rows':[...]}`.\n- `pdf` keys: `namespace, item, source_sha256, decision, name, page_index, rect, layer, job` (`:111-112`).\n- **Per row**, `reviewed_rows[]` (`:159-160`, schema `ROW` `:14-15`): `source_row, parameter, value, unit, conditions, sheet_row, original_cells, source_words, ocr_uncertain`.\n  - `original_cells` is a list of raw strings as split from the page, with no column roles (`:64-65`).\n  - `source_words` is `[{'text','rect'}]` (`:66`).\n  - `ocr_uncertain` is true if any word of the row was uncertain (`:67`).\n\n**Not recorded anywhere on a sheet**: `basis` (calculation inputs only), footnote, variant, min/typ/max, sheet-level conditions, the table's header row (dropped only when it is exactly parameter/value/unit/conditions, `:105-106`), and the preview's `gaps` (`:87-92`; the row schema is closed at `:20`).\n\n`source_state.state` for a reviewed sheet is `CURRENT_PDF_SOURCE` or `PDF_SOURCE_REVIEW_REQUIRED` (`W/datasheet_work.py:126-131`).\n\n## 3. Formulas (Q2)\n\n**A cell can hold one.** `formula` is text up to 2048 characters; `formula_dialect` is `'xlsx-a1' | 'odf-openformula' | 'unsupported'`; `cache_state` is then `'STORED_NOT_RECALCULATED'` and `value` is the cached result (`S/office_tables.py:72-75`).\n\nWho writes them:\n- **Imported spreadsheets**, via `office.import.preview` and `office.import.commit`.\n  - xlsx: `formula` is the `<f>` text with no leading `=`. Shared, array and data-table formulas become dialect `'unsupported'` with the raw `<f>` XML as the text (`S/office_tables.py:151-153,171`).\n  - ods: `'of:=SUM([.B2:.B5])'` (`:207,221`).\n  - csv: never a formula (`:126`).\n  - Import origin: `{'source':{'path','name','sha256','bytes'},'profile':'xlsx-cells-v1'|'ods-cells-v1'|'csv-utf8-explicit-types-v1','losses':[...]}` (`S/office_work.py:110`). State is `UNCHANGED_ORIGINAL | STALE_ORIGINAL | ORIGINAL_UNAVAILABLE` (`W/office_service.py:57-58`).\n- **The owner**, in the Office cell dialog (\"Formula definition (optional; never runs here)\"), saved through `office.save` (`W/office_qt.py:49-66,282-286`).\n- **Never the review flow**: `create_sheet` writes literals only (`W/datasheet_work.py:150-156`), and `report()` refuses a formula cell as an input (`:201-202`).\n\n**Evaluation.** Never in-process (\"Import never calculates\", `S/office_tables.py:3`). The only route is `office.operation.preview {mode:'recalculate'}` then `office.operation.run`, which sends an ODS to LibreOffice and records `measurement` rows in the job's `office_result.json`: `{sheet_id, sheet, cell, formula, stored_type, stored_value, measured_type, measured_value, state, engine}`. The sheet itself is not changed (`W/office_service.py:165-168,193-204,214`; `W/office_runtime.py:25-39`).\n\n**Reading a formula and its range without evaluating.**\n- Text: `got['document']['sheets'][i]['cells'][addr]['formula']` and `['formula_dialect']`.\n- Normalise: `office_tables.clean_formula(cell)` (`S/office_tables.py:242-258`) returns upper-case A1 text for either dialect, or raises `ValueError`. I ran it:\n  - `'=SUM($B$2:B5)+B6'` gives `'SUM(B2:B5)+B6'`.\n  - `'of:=SUM([.B2:.B5];[.B6])'` gives `'SUM(B2:B5,B6)'`.\n  - `Sheet2!B2`, `SUBTOTAL(9,\u2026)`, `IF(\u2026)` and dialect `unsupported` all raise.\n  - Only `SUM, PRODUCT, MIN, MAX, ABS, ROUND, AVERAGE, COUNT` are allowed (`:255`).\n- Addresses: `xy('B5')` gives `(5, 2)` and `address(5, 2)` gives `'B5'` (`:31-42`).\n- There is no range-expansion or precedent helper anywhere; you write that.\n\n**Other formula-bearing things, none on the Field:**\n- Workspace `.xlsx` files edited cell by cell: `W/sheet_edit.py:61-75,117-118` and `W/cell_edits.py:26,54-60` (kind `'FORMULA'`).\n- Job workbooks Graphite writes for LibreOffice, `{'kind':'formula'|'number'|'text','value':str}`: `W/math_office.py:14-44`, `W/joined_work.py:96-131`.\n- The spreadsheet viewer shows cached values only (`W/view_modules/sheets.py:3`).\n\n## 4. A calculation page (Q3)\n\nWritten by `datasheet_work.report` (`W/datasheet_work.py:181-265`) through `documents.create(..., derivation=...)` (`W/documents.py:356-366`). `documents.get` returns `{'document','summary','events','plain','source_state'}` (`W/documents.py:420-423`).\n\n```\ndocument = {'schema':'arc.project-desk.document/1','kind':'document','id':<32hex>,'owner','actor','revision':int,'created',\n  'document_schema':'ledger.document/1','title':'<sheet title> \u00b7 calculation','blocks':[{'id','style','text','marks'}],\n  'project','origin':'IMPORTED','updated','last_change',\n  'derivation':{\n    'profile':'pdf-sheet-calculation-v1','sheet':'owner:<32hex>','sheet_revision':<sha256>,'pdf':{\u2026as origin.pdf\u2026},\n    'inputs':[{'symbol','cell','parameter','value','unit','conditions',\n               'basis':'REVIEWED_PDF_ROW'|'WORKING_SHEET_EDIT','source_row','original_cells'}],\n    'calculation':{'state':'FEASIBLE','outputs':[{'node','kind':'quantity','state':'EXACT',\n        'value':{'rational':'84/25','decimal':'3.36','decimal_exact':True,'unit':'W','dimension':{'voltage':1,'current':1}}}],\n        'constraints','missing','assumptions','domain_conditions','model_digest',\n        'arithmetic':'EXACT_RATIONAL','scope':'DECLARED_MODEL_CONSEQUENCE','physical_qualification':False},\n    'recipe':{'expression','inputs':{symbol:'B2'},'output_unit'?,'assumption'?},\n    'replaces'?: <old document id>}}\n```\n\nSources: derivation `W/datasheet_work.py:249-251,257`; inputs `:224-226`; result shape `W/math_model.py:127-147` and `W/math_units.py:55-72` (shape confirmed by running `evaluate`).\n\nPoints that matter for rules:\n- **One calculation reads one sheet**: `derivation['sheet']` is a single id.\n- One to eight inputs, each a column-B number cell of a reviewed row with a named parameter and a non-empty unit (`:189-210`). Every symbol must be used (`:229-230`). The output is always a quantity (`:232-234`).\n- `basis` is string equality of parameter, value, unit and conditions against the reviewed row, not against `original_cells` (`:220-222,225`).\n- **The compiled model is not stored**, only `model_digest`. Recompile from `recipe` and `inputs` exactly as `what_if` does (`:290-306`).\n- The Office dialog always sends `output_unit` and `assumption`, possibly `''` (`W/datasheet_qt.py:293-295`).\n- The page's words are separate, editable text. Block 0 is `\"{expression} = {decimal} {unit}\"`, then `\"Exact value \u2026\"`, the source, the sheet, and one line per input (`:239-248`). Editing the page does not touch `derivation`.\n- `source_state.state` is `CURRENT | RECHECK_SHEET_CHANGED | PDF_SOURCE_REVIEW_REQUIRED | SHEET_UNAVAILABLE` (`:166-178`).\n\n## 5. Unit handling (Q4)\n\nThere is no pint or other units library (grep; `requirements-*.txt`). Two home-made layers exist.\n\n**The Kernel's exact algebra** (`W/math_units.py`):\n- Four bases: time, voltage, current, memory (`:6`). Named dimensions add frequency, power and dimensionless (`:7-8`).\n- Unit table `W/stac/quantities.py:19-42`, 22 entries: `s ms us ns Hz kHz MHz V mV 1 A mA uA W mW B kB MB GB KiB MiB GiB`, each `(dimension, Decimal factor)`.\n- `unit_spec(unit)` returns `(dimension tuple, Fraction factor)` and parses products, quotients and powers such as `V*A`, `W/V`, `A^-1` (`:23-38`). I ran it: `mA` gives `((0,0,1,0), 1/1000)`; `ohm` and `kW` raise `UNKNOWN_OR_AMBIGUOUS_UNIT`.\n- Readable as a read operation: `math.units` (`W/math_service.py:11,207-210`).\n\n**The page-level parser** (`W/quantities.py`):\n- `resolve(token)` returns `{unit_canonical, dimension, kernel_unit, factor, base_unit}` or `None` (`:105-133`). It knows SI prefixes `p n u m c k M G T` (`:73-74`), words (`:57-71`), and local dimensions the Kernel lacks, with `kernel_unit None`: mass, length, resistance, capacitance, inductance, temperature, ratio, energy, volume, pressure, force (`:36-55`). `dB`, `mAh` and `VA` return `None` (ran).\n- `extract(text)` is the parser for \"3.36 W\". It returns spans with `value` as a decimal string plus the spec, and handles `3,360 mW`, `\u00b5` and `\u03a9`; it refuses `47k` and ranges (`:152-204`; ran).\n\n**Where the result unit comes from.** It is computed by dimension, and optionally re-expressed in a typed unit that the Kernel checks.\n- Each input's unit is column C. It must pass `unit_spec`, or `resolve` to a Kernel unit, otherwise the report is refused: \"needs a unit supported by the exact calculator\" (`W/datasheet_work.py:208-218`). So no calculation page can have an input in ohm, \u00b0C, % and so on.\n- Add, subtract and compare of unlike dimensions raise `DIMENSION_MISMATCH` (`W/math_model.py:60`). Multiply and divide give `canonical_unit(dimension)`, for example `W`, or `V*A^-1` and never `ohm` (`:61-62`; `W/math_units.py:15-20`). Numeric literals in the expression are dimensionless (`W/math_model.py:162-163`).\n- The typed \"Result unit\" (`W/datasheet_qt.py:271-273`) goes to `evaluate(output_unit=\u2026)`. A unit of another dimension raises `ValueError('INCOMPATIBLE_OUTPUT_UNIT')` (`W/math_units.py:70`; ran: `v*i` with output `A` raises, output `mW` gives `3360`). It must be a Kernel spelling: `kW` is refused as an output although accepted as an input.\n\n## 6. The three candidate rules (Q5)\n\n### (a) A total that counts a subtotal with its rows\n\nWhat decides it exactly:\n- **Formulas.** A total cell whose normalised SUM range contains a cell S and also S's own SUM range. Needs only `cells[..]['formula']`, `clean_formula`, `xy` and `address`. No evaluation.\n- **Stored values.** Exact `Decimal` equality in a column: a cell equals the rows above it, among which another equals the rows above it. This is what the uncommitted `_counted_twice` does (WT:179-224).\n- **A calculation page.** `recipe.expression` is a sum over symbols and one input's scaled value equals the exact sum of others. Use Fractions via `math_units.rational` times the unit factor, as `what_if` does.\n- **A page total (condition card).** `card.inputs = [{block,index,start,end,text,value,unit}]`, `expression:'sum'` (`W/conditions.py:49,175-178`). The sum takes every quantity on the page except result paragraphs (`:86-94`; `W/profile_numbers.py:100-102`), so a \"Subtotal 3.36 W\" sentence is added in. Arithmetic on the inputs decides it.\n\nWhat is missing:\n- No record says \"this row is a subtotal\". There are only the row's words and arithmetic coincidence.\n- Reviewed sheets never carry formulas.\n- No range-expansion helper exists.\n- Shared and array formulas, cross-sheet references and `SUBTOTAL()` cannot be normalised, so those cases are \"cannot tell\".\n- Cached formula values are not recalculation evidence (`W/office_service.py:60`).\n- Only `sheets[0]` is looked at by any rule (HEAD:126), while an import may hold eight sheets (`S/office_tables.py:12`).\n- **A current condition card is not a Field object.** `Reader.totals` skips `CURRENT` (`W/field_source.py:285`), so `doubts_for` never sees a total that still \"adds up\".\n- The uncommitted `_counted_twice` never reads formulas and ignores units. I ran it on a reviewed-style sheet with B2 = 1 V, B3 = 2 A, B4 = 3 mV, B5 = 6 ms and it returned \"cannot tell \u00b7 counted twice\".\n\nSeparate defect that will sit beside any imported-sheet rule: `_sheet` treats any state not starting with `CURRENT` as a doubt (HEAD:121-122, WT:142-143). Ran with a stub: an unchanged imported sheet gives \"doubt \u00b7 its source \u2026 (unchanged original)\". The Field itself draws that sheet as current (`W/field_source.py:53-59`).\n\n### (b) Units that do not combine to the result unit, or a prefix slip\n\nFor a page written by `report()` the dimension check cannot fail after the fact. The Kernel refused it at write time (section 5), and prefix scaling is done exactly by `unit_spec` factors. A rule that re-derives the dimension from `inputs[].unit` and `recipe.expression` against `outputs[0].value.unit` and `.dimension` is exact and will always hold.\n\nWhere a slip is recorded and decidable exactly:\n1. **Sheet against the page's raw cells.** Compare `reviewed_rows[].value` and `.unit` (or `inputs[]`) with `quantities.extract` over `original_cells`. Same dimension, same digits, different factor is a prefix slip. Nothing checks this today; `basis` compares against the reviewed row only.\n2. **`B<n>.unit` against `C<n>.value`.** `report()` reads C (`W/datasheet_work.py:208`). Nothing compares the two.\n3. **A power-of-ten literal in `recipe.expression`** (for example `v*i/1000`) on top of the Kernel's own scaling. Read it from the AST and the inputs' factors.\n4. **Unit `1` typed for a row** whose `original_cells` show a unit (the dialog invites `1`, `:210`).\n5. **The finding's words against a result.** `_claim` compares unit strings only. Ran: with a 3.36 W result on the desk, \"3360 mW\" and \"3.36 mW\" both produce no row at all, because `mW` is not a desk unit key and is skipped (HEAD:211, WT:336). `unit_spec` or `resolve` factors would decide \"same quantity\" or \"same digits, other prefix\" exactly.\n6. **The page's own words against its derivation** (block 0 and the title are free text).\n\nWhat is missing: `original_cells` has no column roles (2, 3, 4 or other lengths, `:72-92`; the existing rule reads positions 1 and 2, HEAD:81-82). A unit that lives in the table header or a footnote is not recorded. Local dimensions never reach a calculation.\n\n### (c) Same parameter, different value or unit, on two current sheets feeding the same calculation or finding\n\n- **Two sheets cannot feed one calculation**: `derivation.sheet` is one id (`:249`).\n- **Two sheets can feed one finding.** `investigation.path` steps carry `kind:'SOURCE'` with `address`, or `kind:'CHECK'` with `inputs` and `program` (`W/investigations.py:355-370`). These become wires (`W/field_source.py:269-278`). Sheets also reach a finding through calculations (`:225-226`). Walk them with `field.fed_by` (`W/field_model.py:118-119`).\n- **Identity is the name text only**: column A, `reviewed_rows[].parameter`, `inputs[].parameter`. `symbol` exists only per calculation (`recipe.inputs` keys). There is no part, variant or subject field on a sheet. `references.fact.add` has `subject, property, variant, conditions, value, unit` (`W/reference_service.py:28-31`), but facts are neither on the Field nor linked to sheets.\n- **Exact comparison is available**: B decimal strings, C units, `quantities.resolve` for dimension and factor. \"Current\" is `source_state.state == 'CURRENT_PDF_SOURCE'`.\n- **Missing**: structured conditions (column D is free text; min, typ and max rows or 25 \u00b0C against 85 \u00b0C rows legitimately share a name), any \"supersedes\" relation between sheets (only `origin.pdf.item`, `source_sha256` and `page_index` hint at the same document), and which sheet a finding means.\n- The uncommitted `_said_otherwise` (WT:232-254) matches lower-cased names across reviewed sheets and emits a `note`. It ignores conditions, wires, state and prefix equivalence, so 280 mA against 0.28 A is reported as differing. Because it is a `note`, the desk check never lists it (HEAD:289, WT:448).\n\n## 7. `_quantities` and number matching (Q6)\n\n**`_quantities`** (HEAD:149-166, WT:274-291) returns `{unit string: [(float, where)]}`.\n- For each `sheet` object it reads `office.get`, takes `sheets[0]`, and for each row of `origin.reviewed_rows` takes `_number(B<row>.value)` and the stripped `C<row>.value`. Imported sheets have no reviewed rows and contribute nothing.\n- For each `calculation` object it takes `derivation.calculation.outputs[0].value.decimal` and `.unit`.\n- The key is the raw unit string. `mA` and `A`, or `\u03a9` and `ohm`, are different keys. There is no dimension and no factor.\n\n**Matching in a finding** (HEAD:209-217, WT:334-341):\n- Regex `(?<![\\w.])(-?\\d+(?:\\.\\d+)?)\\s*([A-Za-z\u00b5\u03a9\u00b0%]+)` over `obj.title` (now the constant `QUANTITY`, WT:71).\n- A unit that is not a key is silently skipped.\n- The number test is `_same`: floats, `abs(a-b) <= 1e-9 * max(1, |a|, |b|)` (HEAD:61-62). `_number` is `float(str(x).strip())` (HEAD:48-52).\n- `quoted_calculation` uses the same regex, with `result['unit'] == unit` and `_same` (HEAD:241-251).\n- `field.moved` matching is plain substring on `\"<decimal> <unit>\"` (`W/field_source.py:211-213,434-444`; HEAD:206-208).\n\n**Quirks I ran:**\n- \"3,360 mW\" is read as `('360','mW')`.\n- \"1.2e3 mA\" is read as `('1.2','e')`.\n- `V*A` or `W/V` in words truncates to `V` or `W`.\n- `_quantity('3.36')` returns `(3.3, '6')` (HEAD:55-58; it is used only on `what_if`'s `would_be`).\n- `quantities.extract` gets \"3,360 mW\" right, as value `3360`.\n- The uncommitted `_counted_twice` uses exact `Decimal` with no tolerance (WT:171-176), unlike `_same`.\n\n## 8. Hook points and hazards\n\n- **A rule** is `fn(kernel, principal, obj, field) -> [Doubt(verdict, about, why, see)]`, registered in `BY_KIND` (HEAD:270, WT:429). `obj.target['id']` is `'owner:<hex>'` for a sheet and the 32-hex id for a page. Read through `_read` (HEAD:40-45).\n- **`see` lines in use**: `office.get {\"id\":\u2026} | pick origin.reviewed_rows | select \u2026`; `@office:<id> | pick document.sheets | select cells.B3.value`; `documents.get {\"id\":\u2026} | pick document.derivation.inputs | select symbol,cell,value,unit,conditions,basis`.\n- **Exceptions.** `doubts_for` catches only `KeyError, TypeError, ValueError, AttributeError`, and then replaces all rows for that object with a single \"cannot tell\" (HEAD:273-281). `Kernel.dispatch` catches only `ValueError, OSError, KeyError, TypeError, sqlite3.Error` (`W/engineering_kernel.py:528`). `IndexError`, `ZeroDivisionError`, `decimal.InvalidOperation` and `ImportError` escape both.\n- **The desk check** lists only `doubt` and `cannot tell` (HEAD:284-290).\n- **\"Doubt it\" under D** is offered for a hard-coded tuple of kinds (`W/field_do.py:246`). `looked_at` was hard-coded at HEAD (`W/field_service.py:123`) and reads `BY_KIND` in the working tree (WT:126).\n- **Field ceilings**: 60 sheets, 300 pages (`W/field_source.py:43-44`).\n- **Wiring**, should an operation be added: scopes at `W/engineering_kernel.py:225`, route at `:624`, observer list at `W/activity.py:33`.\n- **Tests**: no file in `tests_integrated/`, `tools/` or `sdk/` references `field_doubt`, `doubts_for` or `field.doubt`.",
 "key_locations": [
  {
   "what": "Doubt rules, uncommitted working tree (449 lines, mtime 03:09:03 UTC): BY_KIND registry now includes 'document'; HEAD equivalent is line 270",
   "file": "/home/user/Struthio/workbench/field_doubt.py",
   "line": 429
  },
  {
   "what": "Uncommitted _counted_twice: subtotal rule by Decimal arithmetic on stored column values; ignores units and never reads formulas",
   "file": "/home/user/Struthio/workbench/field_doubt.py",
   "line": 179
  },
  {
   "what": "Uncommitted _said_otherwise: same column-A name on another reviewed sheet with other value/unit, verdict 'note'",
   "file": "/home/user/Struthio/workbench/field_doubt.py",
   "line": 232
  },
  {
   "what": "Uncommitted _page imports .field_brief, a module that does not exist; ModuleNotFoundError is not caught by doubts_for or Kernel.dispatch",
   "file": "/home/user/Struthio/workbench/field_doubt.py",
   "line": 362
  },
  {
   "what": "_quantities: desk values keyed by raw unit string, reviewed rows and calculation results only (HEAD line 149)",
   "file": "/home/user/Struthio/workbench/field_doubt.py",
   "line": 274
  },
  {
   "what": "QUANTITY regex used for finding/page number matching; _same tolerance at line 62, _number at 49, _quantity at 56 (HEAD: regex inline at 210 and 244)",
   "file": "/home/user/Struthio/workbench/field_doubt.py",
   "line": 71
  },
  {
   "what": "_sheet source-state test: any state not starting with 'CURRENT' is a doubt, so an unchanged imported sheet is doubted (HEAD lines 121-122)",
   "file": "/home/user/Struthio/workbench/field_doubt.py",
   "line": 142
  },
  {
   "what": "create_sheet: cell layout A-F, B number cell carrying unit, reviewed_rows shape (line 159-160) and origin (line 163)",
   "file": "/home/user/Struthio/workbench/datasheet_work.py",
   "line": 134
  },
  {
   "what": "report(): input rules (197-226), unit resolution (208-218), basis (220-225), evaluate with output_unit (231), derivation shape (249-251)",
   "file": "/home/user/Struthio/workbench/datasheet_work.py",
   "line": 181
  },
  {
   "what": "what_if(): recompiles a calculation from recipe + inputs; the pattern to reuse for exact re-derivation",
   "file": "/home/user/Struthio/workbench/datasheet_work.py",
   "line": 268
  },
  {
   "what": "candidate(): how raw page cells become parameter/value/unit/conditions; original_cells has no column roles",
   "file": "/home/user/Struthio/workbench/datasheet_work.py",
   "line": 72
  },
  {
   "what": "cell() constructor: the seven per-cell keys; validate() enforces them at line 60 and formula provenance at 72-75",
   "file": "/home/user/Struthio/sdk/cli/arc1cli/office_tables.py",
   "line": 43
  },
  {
   "what": "clean_formula(): normalises xlsx/ods formula text to A1 without evaluating; safe function list at line 255",
   "file": "/home/user/Struthio/sdk/cli/arc1cli/office_tables.py",
   "line": 242
  },
  {
   "what": "parse_xlsx formula capture; shared/array formulas become dialect 'unsupported' (152-153)",
   "file": "/home/user/Struthio/sdk/cli/arc1cli/office_tables.py",
   "line": 151
  },
  {
   "what": "xy() and address(): cell address to (row, col) and back, for range expansion",
   "file": "/home/user/Struthio/sdk/cli/arc1cli/office_tables.py",
   "line": 31
  },
  {
   "what": "Office._get: the stored record returned by office.get (id, version, revision, document, origin); import origin at line 110",
   "file": "/home/user/Struthio/sdk/cli/arc1cli/office_work.py",
   "line": 45
  },
  {
   "what": "source_state() for sheets and get() adding source_state and formula_values (59-60); owner check at 61-62; recalculate measurement at 193-204",
   "file": "/home/user/Struthio/workbench/office_service.py",
   "line": 36
  },
  {
   "what": "unit_spec(): dimension tuple and exact factor; quantity_record raises INCOMPATIBLE_OUTPUT_UNIT at line 70",
   "file": "/home/user/Struthio/workbench/math_units.py",
   "line": 23
  },
  {
   "what": "UNITS: the Kernel's 22-entry unit table",
   "file": "/home/user/Struthio/workbench/stac/quantities.py",
   "line": 19
  },
  {
   "what": "resolve(): unit spelling to dimension/kernel_unit/factor with SI prefixes; extract() at line 180 parses '3.36 W'",
   "file": "/home/user/Struthio/workbench/quantities.py",
   "line": 105
  },
  {
   "what": "validate(): DIMENSION_MISMATCH for add/sub/compare (60), result unit of mul/div (62); evaluate at 127; compile_expression at 150",
   "file": "/home/user/Struthio/workbench/math_model.py",
   "line": 60
  },
  {
   "what": "documents.create stores derivation; documents.get adds source_state at 421-423",
   "file": "/home/user/Struthio/workbench/documents.py",
   "line": 356
  },
  {
   "what": "Condition card record (inputs spans, expression 'sum', result); page_quantities at line 86 adds every quantity except result paragraphs",
   "file": "/home/user/Struthio/workbench/conditions.py",
   "line": 175
  },
  {
   "what": "Reader.totals skips CURRENT condition cards, so a total that still adds up is never a Field object",
   "file": "/home/user/Struthio/workbench/field_source.py",
   "line": 285
  },
  {
   "what": "Finding wires from investigation.path steps (sheet/calculation to claim); sheet-to-calculation wire at 225-226",
   "file": "/home/user/Struthio/workbench/field_source.py",
   "line": 269
  },
  {
   "what": "investigation.path result: SOURCE steps with address, CHECK steps with inputs/program",
   "file": "/home/user/Struthio/workbench/investigations.py",
   "line": 355
  },
  {
   "what": "Kernel.dispatch exception list: only ValueError, OSError, KeyError, TypeError, sqlite3.Error become ok:false",
   "file": "/home/user/Struthio/workbench/engineering_kernel.py",
   "line": 528
  },
  {
   "what": "steps_for: 'Doubt it' offered only for a hard-coded tuple of kinds",
   "file": "/home/user/Struthio/workbench/field_do.py",
   "line": 246
  },
  {
   "what": "field.doubt service; working tree adds field.ripple (FIELDS line 36, ripple at 129) and looked_at now reads BY_KIND (126)",
   "file": "/home/user/Struthio/workbench/field_service.py",
   "line": 108
  },
  {
   "what": "Untracked module created during this task by another writer: field.ripple, imports private names from field_doubt",
   "file": "/home/user/Struthio/workbench/field_ripple.py",
   "line": 23
  },
  {
   "what": "Result unit field in the calculation dialog; output_unit and assumption always sent, possibly empty (293-295)",
   "file": "/home/user/Struthio/workbench/datasheet_qt.py",
   "line": 271
  },
  {
   "what": "CellDialog: the owner can type a formula definition and unit annotation into any Office cell",
   "file": "/home/user/Struthio/workbench/office_qt.py",
   "line": 49
  },
  {
   "what": "references.fact.add: the only record with subject/property/variant/conditions/value/unit; not on the Field",
   "file": "/home/user/Struthio/workbench/reference_service.py",
   "line": 28
  }
 ],
 "gaps": [
  "The working tree was being edited by another writer during this task (field_doubt.py rewritten 03:09:03 UTC; activity.py, field_page.py, field_qt.py, field_service.py, shell2.py modified and field_ripple.py created by 03:12:49 UTC). Line numbers for those files may have moved again; I did not read the bodies of field_ripple.py, field_page.py, field_qt.py or shell2.py.",
  "workbench/field_brief.py, imported by the uncommitted _page rule, did not exist at 03:12:49 UTC. I could not determine what its standing() is meant to return.",
  "No tests and no application were run, per the rule. Everything about Kernel-backed paths (office.get against the real store, documents.get, investigation.path) is from reading code. Only pure functions were run: unit_spec, quantities.resolve/extract, math_model compile/evaluate, office_tables.clean_formula/cell/xy, and field_doubt helpers against a stub kernel.",
  "I did not open any real workspace data (no catalog or desk database), so I cannot say whether any imported sheet with formulas, any condition card, or any two sheets sharing a parameter exist on this machine, nor what real original_cells look like.",
  "Whether documents.get refuses an 'owner:<hex>' id (which would make the uncommitted _page rule report 'cannot tell' for every Office written document) is inferred from the ID schema (32 characters), not confirmed.",
  "I did not read the staC pipeline implementation, so the exact semantics of 'pick document.sheets | select cells.B3.value' on a list are taken from the existing see-lines, not verified.",
  "I did not read pdf_service.py: whether a table's header row or a page footnote survives anywhere outside the sheet record (for example in the rendered page job's words) is not determined. It is not in the sheet's origin.",
  "No record anywhere marks a row as a subtotal, links a parameter across sheets by identity, says one sheet supersedes another, or structures conditions (min/typ/max, temperature). These are absent from the code, not merely unfound.",
  "The records hold no compiled model for a calculation page, only model_digest; a rule must recompile from recipe and inputs.",
  "I did not check what else must be updated when an operation or kind is added (docs/GRAPHITE_0.1_REGISTRY.json, MANIFEST.json, tools/record_registry.py all mention doubt); I only saw that they exist.",
  "No test file references field_doubt, doubts_for or field.doubt in tests_integrated/, tools/ or sdk/ (grep), so there is no existing fixture pattern for doubt rules to copy."
 ]
}