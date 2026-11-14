export const meta = {
  name: 'graphite-043-understand',
  description: 'Four readers map the exact machinery behind four planned additions to Graphite (read-only)',
  phases: [{ title: 'Read', detail: 'one reader per subsystem, structured map with file:line' }],
}

const PREFACE = `You are reading the source of Graphite, a local-first Python 3.13 / PySide6 desktop workspace, at /home/user/Struthio (git branch claude/epic-galileo-c7k11y, version 0.4.2).

This is a READ-ONLY mapping task. Do not edit, create or delete any file in the repository and do not commit.
HARD RULE: do not run the test suites (tests_integrated/, tools/check_*.py) and do not start the application. Some of those kill processes and would take this whole session down. You may read files (Read / Grep / Glob). If you must confirm how a pure function behaves you may run one short snippet from /home/user/Struthio with
  /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/venv/bin/python -B -c '...'
importing only non-Qt workbench modules and writing nothing.

Background. Every action goes through one dispatcher, Kernel.dispatch(op, args, principal) -> {ok, result|error}. Operations are declared by a module's FIELDS = {op: (properties, required)} and SCOPES, and wired in workbench/engineering_kernel.py (CAPABILITIES plus the dispatch route). "The Field" (workbench/field_*.py) is a surface that shows one workspace's sources, reviewed sheets, calculations, pages, findings (investigation claims), conditions and open questions as cards joined by wires. field_source.py reads it from the records; field_doubt.py holds exact rules that cross-examine one thing ("doubts": verdict doubt / cannot tell / note / holds); field_do.py lists what can be done about a thing as steps, each a staC line ("/op {json}") that either reads at once or waits for the owner's go; field_service.py exposes field.read / field.trace / field.whatif / field.doubt as read operations. staC is a read-only pipeline language: op {json} | pick path | where f=v | select a,b | count | group f | take N.

I am about to build an addition and need an exact map of the machinery it stands on. For everything you state give the file path and line number. Quote real record shapes with their keys exactly as the code has them. Say plainly what you could not determine. I will do the design; what I need from you is the ground truth, the hook points, and the gaps.`

const SCHEMA = {
  type: 'object',
  properties: {
    report: { type: 'string', description: 'The map, in markdown, with file:line for every statement and exact record shapes' },
    key_locations: { type: 'array', items: { type: 'object', properties: { what: { type: 'string' }, file: { type: 'string' }, line: { type: 'integer' } }, required: ['what', 'file', 'line'] } },
    gaps: { type: 'array', items: { type: 'string' }, description: 'What the records do not hold or what could not be determined' },
  },
  required: ['report', 'key_locations', 'gaps'],
}

const READERS = [
  { key: 'numbers', prompt: `${PREFACE}

YOUR SUBJECT: numbers, units and totals on the desk — the ground for new exact doubt rules.

Read first: workbench/field_doubt.py (the rules that already exist; do not re-describe them at length, just list them in one line each so I do not duplicate), workbench/datasheet_work.py, and whatever stores and evaluates sheets and calculations (search workbench/ for datasheet, office, spreadsheet, formula, SUM, unit, quantity, math.evaluate, pint or any units handling; look at workbench/office*.py, workbench/math*.py, workbench/calc*.py and the 'office.datasheet.*' operations).

Answer exactly:
1. How a reviewed sheet is stored: the full record shape of an office sheet document (sheets, cells, per-cell keys such as value / unit / formula, the 'origin' with reviewed_rows, basis, original_cells, ocr_uncertain, conditions, anything like footnote/variant/min-typ-max). Which of these are per row and which per cell.
2. Can a sheet cell hold a formula (for example =SUM(B2:B5))? If so, where is it stored, how is it evaluated, and how can code read the formula text and its range without evaluating? If Graphite's own sheets cannot, say which other record kinds can (imported spreadsheets? 'office' workbooks?) and their shape.
3. How a calculation page is recorded (the document written by office.datasheet.report / datasheet_work.report): derivation keys, the recipe/expression, each input (symbol, cell, value, unit, conditions, basis), the result and its unit. Quote the shape.
4. What unit handling exists anywhere: is there dimensional analysis or prefix conversion (mA vs A, mW vs W), a table of units, a parser for "3.36 W"? Where does the result unit of a calculation come from — computed or typed?
5. For each of these three candidate rules say what recorded data would decide it EXACTLY with no model, and what is missing: (a) a total that counts a subtotal together with the rows the subtotal already sums; (b) inputs whose units do not combine to the stated result unit, or a prefix slip (a value in mA used as A); (c) the same parameter (same symbol or same parameter name) recorded with different values or different units on two current sheets that feed the same calculation or finding.
6. How field_doubt._quantities and the number-matching in findings work (regex, tolerance, unit comparison), since new rules must use the same matching.` },

  { key: 'ripple', prompt: `${PREFACE}

YOUR SUBJECT: what would move if one number changed — the ground for a read-only "ripple" (a what-if followed along the wires to everything downstream).

Read first: workbench/field_service.py (whatif), workbench/datasheet_work.py (what_if and report), workbench/field_source.py (how links between sheet -> calculation -> finding -> page are derived; _moved; Reader), workbench/field_doubt.py (_quantities, weak_check, quoted_calculation), workbench/field_do.py (_claim steps that write investigation.add_source / investigation.check), and the investigation module(s) that store claims, checks and evidence (search workbench/ for 'investigation.check', 'refutes_on_fail', 'CONTAINS', 'expect').

Answer exactly:
1. How a calculation names the sheet cells it reads: the keys in the calculation document that hold the source sheet id, the cell addresses, the symbols and the recipe. Given a sheet id and a cell address, how do I find every calculation that reads that cell (which function already does this, or which fields to compare)?
2. datasheet_work.what_if(document, changes): its exact signature, what keys 'changes' may use (symbol or cell), what it returns, how exact its arithmetic is (Decimal? float?), what it refuses. Does it check units of the supplied value?
3. How a finding (claim) is tied to numbers: where its text lives, how _moved / the 'says X; now Y' marking decides that a finding quotes a calculation's result, and how field_doubt matches quantities in a finding's text against sheet rows and calculation results.
4. How a check is stored on a claim (program, expect, value, refutes_on_fail, outcome, staleness) and how it is evaluated. Is there a way to evaluate a check's program against hypothetical data without writing anything (for instance by evaluating the staC program's result in memory and substituting one cell)? Name the functions.
5. Which other records depend on a sheet cell or a calculation result and would need another look if it changed: conditions (conditions.*), pages/documents that quote a result, agenda watches, jobs. For each, the field that ties it to the number.
6. The Field's wires: the Link shape (source, target, label, stale) and the helper methods on Field (feeds, fed_by, get) so a ripple can walk downstream from a sheet. Quote signatures.
7. Anything in the records that would make a hypothetical evaluation wrong or impossible (say it plainly: e.g. findings whose meaning is a comparison in prose, such as "allows 6 W", which no exact rule can re-evaluate).` },

  { key: 'pages', prompt: `${PREFACE}

YOUR SUBJECT: a page written from the records — the ground for "the brief", a one-page account of a desk (what stands and on what, what waits, what is doubted) that Stacy puts up as a staged change and the owner approves.

Read first: the documents module and its operations (search workbench/ for 'documents.create', 'documents.get', 'documents.revise', 'documents.update', FIELDS containing 'documents.'), workbench/datasheet_work.py (report: how a generated calculation page is written with its derivation — this is the model to follow), workbench/field_source.py (how a document becomes a 'page' or a 'calculation' card on the Field, what wires it gets, how 'replaces'/'retired' are read), workbench/field_do.py (Step, op(), _page and _claim enumerators, 'more' for multi-line steps), workbench/field_page.py (take, _await_go, go) and SlateFace.say_plan / run_plan / stage / run_staged in workbench/shell2.py. Also look at how the existing worked case writes its page "07 Case conclusion · HOLD" (search the repo for 'Case conclusion') and the investigation read operations (investigation.sheet / path / review) that return what stands for a claim.

Answer exactly:
1. The operation(s) that create and revise a document: exact argument schema (FIELDS entry), required keys, scope (read or write), what they return (id, revision), and any limits on body size or characters.
2. The body format of a document: plain text, markdown, blocks? What renders in the Documents tab — headings, lists, tables, links to other records (is there a link/reference syntax such as @kind:id that becomes clickable)?
3. What makes a document appear on the Field as a 'page', and which keys wire it to findings / calculations / sheets (derivation? references? investigation id? title prefix?). Give the exact rule from field_source.py so that a generated brief appears on the Field wired to what it cites, and say how a later brief can replace an earlier one (the 'replaces' mechanism used for recomputed calculations).
4. How a staged multi-line plan is put up and run: the Step fields, how 'more' lines are executed in order, how results from an earlier line (for example a created id) can or cannot be used by a later line, and how a refusal stops the run.
5. Whether a staC line / '/op {json}' can carry a long text argument (a body of a few thousand characters) through field_do.op / call and the Talk card without being cut — find every truncation ([:N]) on that path.
6. What read operations already return a claim's standing in plain data (support/opposition counts, evidence, checks with outcomes, sources and their states) that a brief could assemble without new queries; quote the result shapes.` },

  { key: 'words', prompt: `${PREFACE}

YOUR SUBJECT: the writing strip, staC words, and the Field's keys — the ground for (a) the owner's own named staC words (keep a line under a name, then type the name to run it) and (b) a "back" key on the Field that returns to the sheet the owner was on before.

Read first: workbench/typebar_qt.py (how what is typed is resolved: '/op', staC lines, start words, ctrl_enter, hints, expand_this), workbench/stacy_language.py and workbench/stac_bridge.py and any module that parses or runs staC (search for 'language.run', 'stac.run', 'explain', 'start word', 'START'), workbench/field_page.py (expand_this, FACES, the page's actions), workbench/field_qt.py (keyPressEvent: every key that is taken and what it does; how selection changes; signals), workbench/context_menu.py (how Field entries are declared), and whatever persists small per-workspace or per-owner settings (search for 'settings.set', 'settings.get', 'preferences', 'agenda.add', 'watch', 'keep_in_agenda', 'save_rows').

Answer exactly:
1. The path of a typed line from the strip to a result: functions in order, with file:line; where a first word is looked up as a start word and what the start-word table is (shape, where defined, whether it can be extended at run time).
2. Where 'this' is expanded (expand_this and its callers) — I intend to expand the owner's named words at the same points; list every caller so none is missed (typebar hint, ctrl_enter, Enter, SlateFace.preview_rows, others).
3. The staC grammar as implemented: the stage verbs, how the first stage (op + JSON) is parsed, what errors are returned for an unknown op. Is there any existing notion of a saved/named line, alias, macro or 'method' at the staC level? (Method Press / procedures.* exist for bigger things — say what procedures.* stores and whether a single read-only staC line fits it or it is too heavy.)
4. The best existing place to store name -> staC line pairs so they survive restart and belong to the workspace: the exact operations (FIELDS entry, scope, result shape), whether writes are journaled, and limits. If nothing fits, say which module would be the natural home for two tiny operations and how operations are registered (the three places to wire: module FIELDS/SCOPES, engineering_kernel CAPABILITIES + route, engineering_cli.schemas, plus activity.OBSERVER_OPERATIONS for unjournaled reads and docs/GRAPHITE_0.1_REGISTRY.json recorded by tools/record_registry.py). Quote how field_service is wired as the example, with line numbers.
5. Field keys: the full list of keys handled in field_qt.keyPressEvent with what each does, and which letters are free. In particular confirm whether B, K, M, N, P, W, L, H, Backspace, Tab, brackets are taken (N/P/W may be face switches handled elsewhere — find where).
6. How selection history could be kept: where selection changes funnel (field.select / move / mouse), whether FieldView keeps any previous selection today, and what happens to selection when the Field is re-read (R) or the face changes.` },
]

phase('Read')
const maps = await parallel(READERS.map(r => () => agent(r.prompt, { label: `read:${r.key}`, phase: 'Read', schema: SCHEMA }).then(m => m ? { key: r.key, ...m } : null)))
const got = maps.filter(Boolean)
log(`${got.length} of ${READERS.length} readers returned`)
return { maps: got, missing: READERS.map(r => r.key).filter(k => !got.some(m => m.key === k)) }
