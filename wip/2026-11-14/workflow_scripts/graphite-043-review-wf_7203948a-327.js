export const meta = {
  name: 'graphite-043-review',
  description: 'Independent review of Graphite 0.4.3 (commit 702e4b8): four lenses find faults with reproductions, a second reader tries to refute each',
  phases: [
    { title: 'Find', detail: 'one reviewer per lens, each finding with a concrete failing scenario and a reproduction' },
    { title: 'Verify', detail: 'a second reader per lens re-runs or refutes every finding' },
  ],
}

const S = '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad'

const COMMON = `You are reviewing a change to Graphite, a local-first Python 3.13 / PySide6 desktop workspace, at /home/user/Struthio (branch claude/epic-galileo-c7k11y). The change under review is commit 702e4b8 ("Graphite 0.4.3") against its parent 164fe3c: run \`git -C /home/user/Struthio diff 164fe3c 702e4b8 -- workbench docs/RELEASE_NOTES_0.4.3.md\` to see it (about 1,200 added lines; new files workbench/field_ripple.py, workbench/field_brief.py, workbench/stac_words.py). I wrote it; I want a reader who did not. Do not take my word for anything: docs/RELEASE_NOTES_0.4.3.md says what it claims to do, and your job is to find where the code does not do that, or does something harmful.

RULES
- READ-ONLY on the repository: do not edit, create or delete any file under /home/user/Struthio, and do not commit. Write your own scripts only under ${S}/tools/review/scripts/<your lens>/ (create the directory).
- Do NOT run the project's test suites (tests_integrated/, tools/check_*.py): some kill processes and would take this session down.
- To reproduce through the real records, use the kernel-only harness: a fresh disposable copy of the worked case "After Hours 07" (3 sources, 3 reviewed sheets, 2 calculations, 1 page, 4 findings, 1 open question), no window, no Qt:
    cd /tmp && ${S}/work/venv/bin/python -B ${S}/tools/review/kern.py YOUR_SCRIPT.py
  Your script is exec'd with: k (the Kernel), p (the owner principal), d(op, args) -> result dict or {'ERROR': message}, field() -> the Field read now, root (the disposable workspace). Every run starts from a fresh copy, so writing through the Kernel is fine. See ${S}/tools/review/example.py. Pure functions can be imported directly from workbench.* inside such a script.
- Run at most one script at a time and keep each under a minute.

BACKGROUND YOU NEED
- Every action goes through Kernel.dispatch(op, args, principal) -> {ok, result|error}. Operations are declared in a module's FIELDS/SCOPES (scope read, execute or approve). The Kernel checks unknown/missing parameters and basic types but does NOT enforce JSON-schema 'pattern'. Kernel.dispatch catches only ValueError, OSError, KeyError, TypeError and sqlite3.Error: any other exception escaping an operation is a crash in the window.
- "The Field" shows a workspace's sources, sheets, calculations, pages, findings (investigation claims), questions as cards joined by wires (workbench/field_source.py reads it; field_model.py is the model). field_doubt.py holds exact rules that cross-examine one thing (verdict doubt / cannot tell / note / holds). field_do.py offers steps; a step whose operation is not a read waits for the owner's go (G). staC is a read-only pipeline language (op {json} | pick path | where f=v | select a,b | count ...), run by 'language.run'.
- Useful reads: field.read, field.doubt {id?}, field.ripple {id, set}, field.brief, field.trace {id}, words.list, office.get {id} (id like 'owner:<hex>'; a Field sheet id is 'office:owner:<hex>'), documents.get {id}, investigation.sheet {id}, investigation.list. Useful writes for building cases: investigation.claim {id, text, role:'FINDING'}, investigation.check {claim, program, oracle, expect:'CONTAINS', value, refutes_on_fail}, investigation.add_source {id, address}, investigation.continue {id}, office.save {id, expected_revision, document}, office.import.preview {path, csv:{columns:{'B':'number'}, units:{}, header_rows:1}} then office.import.commit {plan: preview['id'], expected_digest: preview['digest']}, office.datasheet.recheck {id, expected_revision}, documents.save {id, expected_revision, blocks}, field.brief.keep {shown?}, words.keep {name, line}.

WHAT COUNTS AS A FINDING
A concrete failing scenario: these inputs or this state, this wrong output / crash / data loss / wrong claim to the owner. Prefer a few real ones over many speculative ones. For each, either reproduce it with a script (give the script path and paste the decisive output) or, if it cannot be reproduced without a window, quote the exact lines that make it certain and say reproduced=false. Do not report style, naming or missing tests. Rank by harm to the owner: a wrong number or a wrong "holds" shown as true is worse than a crash, and a crash is worse than an awkward sentence. Also say plainly what you looked at and found sound, and what you did not get to.`

const FINDINGS = {
  type: 'object',
  properties: {
    findings: { type: 'array', items: { type: 'object', properties: {
      title: { type: 'string' }, file: { type: 'string' }, line: { type: 'integer' },
      severity: { type: 'string', enum: ['high', 'medium', 'low'] },
      scenario: { type: 'string', description: 'inputs/state -> the wrong output, crash or harm' },
      evidence: { type: 'string', description: 'the decisive output of your reproduction, or the exact code lines' },
      reproduced: { type: 'boolean' }, repro_script: { type: 'string' },
    }, required: ['title', 'file', 'severity', 'scenario', 'evidence', 'reproduced'] } },
    sound: { type: 'string', description: 'what you examined and found correct' },
    not_covered: { type: 'string' },
  },
  required: ['findings', 'sound', 'not_covered'],
}

const VERDICTS = {
  type: 'object',
  properties: {
    verdicts: { type: 'array', items: { type: 'object', properties: {
      title: { type: 'string' }, real: { type: 'boolean' },
      severity: { type: 'string', enum: ['high', 'medium', 'low', 'none'] },
      reason: { type: 'string' }, evidence: { type: 'string' },
    }, required: ['title', 'real', 'reason'] } },
  },
  required: ['verdicts'],
}

const LENSES = [
  { key: 'ripple', prompt: `${COMMON}

YOUR LENS: the ripple (workbench/field_ripple.py, the 'field.ripple' operation in workbench/field_service.py, datasheet_work.what_if, and the helpers it borrows from field_doubt.py: measure, said_quantities, unit_of, _quantities, weak_check).
Hunt for: a would-be value that is wrong (units, prefixes, the conversion back into the unit the words use, floats); a dependent that is missed or wrongly listed; a check reported "would still pass" that would fail or the reverse (the check's own program is run on a copy of the sheet with the cell replaced: is that copy what a real save would produce? is the plan the same as a real run's?); a calculation with two symbols on one cell; a sheet that is not a reviewed sheet (imported CSV, formula cells, text in number columns, empty); 'set' keys in odd forms (lower case, a row's words that match two rows, a symbol that looks like a cell); values like '0', '-5', '1e3', '1/3', ' 320 '; exceptions that are not ValueError/KeyError/TypeError/OSError escaping to the Kernel; anything that writes (it must be a pure read: confirm the sheet, the journal and the investigation are untouched after a ripple).` },
  { key: 'doubt', prompt: `${COMMON}

YOUR LENS: the doubt rules (workbench/field_doubt.py as changed, 'field.doubt' in field_service.py, the steps that go with them in workbench/field_do.py, and carries/rewritten in workbench/field_model.py).
Hunt for: a wrong "holds" (the worst case: something false shown as sound); a false doubt; in particular
- _counted_twice / _twice_in_run: runs with gaps, negative numbers, zeros, decimals, several totals, a grand total over subtotals only (which is correct accounting and must NOT be doubted), units mixed or absent, text cells typed as numbers, more than one sheet;
- measure / said_quantities / _placed: quantities whose units the tables do not know, '%', temperatures, '12 V' against '12 mV' on the desk, the same number under two kinds of unit, large and tiny numbers, thousands separators, negative values, a number that matches by chance;
- _made_from: coincidences on a desk with many values; the wording when it is wrong;
- _said_otherwise: parameters that rightly differ (min/typ/max rows with the same name on one sheet, conditions);
- _page and the brief's 'standing';
- the rule for a check that reads a replaced page (it matches a record id as a substring of the check's program);
- _Once (a per-pass read cache): can it serve a stale answer inside one operation, or leak between operations?
- carries/rewritten: numbers at the start or end of text, followed by punctuation, units with symbols such as %, µ, °;
- exceptions escaping doubts_for / desk (only some are caught) and the desk check as a whole when one record is odd.` },
  { key: 'records', prompt: `${COMMON}

YOUR LENS: authority and the integrity of records in the brief and the owner's words (workbench/field_brief.py, the 'field.brief' and 'field.brief.keep' operations, the change to workbench/documents.py create(), how workbench/field_source.py reads a kept brief and drops replaced pages, workbench/stac_words.py and its wiring in engineering_kernel.py / engineering_cli.py / activity.py, and the expansion of words in workbench/typebar_qt.py and workbench/shell2.py).
Hunt for: any way a kept word can do what a typed staC line could not (keep is supposed to accept only staC reads: try lines that start with '/', with '@', with a START word, with 'explain', with 'this', with control or zero-width characters, with a name that shadows an operation or a staC keyword, a word built on a word, a word redefined after another was built on it, very long lines, 200+ words); JSON or staC injection through a name or a line ('word NAME' becomes "where name=NAME"); whether words are per workspace and survive a new Kernel; whether 'words.keep' is journaled as a change and 'words.list' is not; whether a non-owner principal can keep or read words where it should not (compare with how agenda.py or documents.py treat principals); the brief: can 'field.brief.keep' write when 'shown' is stale, can two keeps race, does a kept brief ever replace or hide a page that is not a brief (the 'replaces' mark), can the 'brief' key be set or forged through documents.save / documents.create / an import so that an arbitrary page poses as a brief or hides another page, does the fingerprint change when nothing meaningful changed (so the brief nags) or stay the same when something did (so it lies), are record texts with line breaks, very long titles, or 5,000 findings handled, is the 24-lines-per-part cut said honestly, is anything written by 'field.brief' (it must be a read).` },
  { key: 'window', prompt: `${COMMON}

YOUR LENS: the window: keys, state and what the owner is shown (the changes in workbench/field_qt.py, workbench/field_page.py, workbench/shell2.py, workbench/context_menu.py, workbench/typebar_qt.py).
For this lens you may also drive the real window offscreen on a disposable copy of the same worked case (it is isolated; nothing reaches the repository). Write a script and run:
    cd ${S}/work && REHEARSAL_MODEL=x REHEARSAL_SCRIPT=/path/to/your_script.py timeout 300 ./venv/bin/python -B ${S}/tools/field/nomodel.py /home/user/Struthio ${S}/tools/review/scripts/window 1366 768
Your script is exec'd with: w (the main window), app, settle(ms, n) (let events run), QTest, Qt, operator, save(name) (a PNG into the output directory). Useful: w.a_field.trigger(); settle(); v = w.field_page.view (a FieldView: v.field.objects, v.field.select(id), v._reveal(), v._describe(), v.update(), v.selected(), v.would, v.would_said, v.steps, v.go); QTest.keyClick(v, Qt.Key_B); w.shell2.ask('what if B3 were 320?'); face = w.shell2.face; cards = [face.lines.itemAt(i).widget() for i in range(face.lines.count())]. See ${S}/tools/field/ui043_probe.py and ${S}/tools/field/edge043_probe.py for working examples (read them, do not edit them). One run at a time; each takes about 20 seconds.
Hunt for: a key that approves something it should not (only G is the owner's go; a digit only chooses); G running a staged change after the owner moved to another sheet, changed face, pressed Esc or re-read the Field; the what-if marks (v.would) surviving when they no longer describe the records (after R, after a step ran, after a face change) or naming a sheet that is gone; Esc order (steps and go first, then the marks, then leave); Backspace with an empty trail, after a re-read removed the sheet, across faces; B on the programs or network face, with an empty desk, pressed twice, with the Talk pane absent; the brief's read card and the staged card after a refusal; "what if" phrasings that set the wrong cell (a row name that is a prefix of another, 'and', units typed after the number, negative numbers, a number inside the name) or that silently do nothing; one-field rows shown as lines in Talk for results that are not writing; words typed in the strip (the hint, Ctrl+Enter, Enter) when the word's line starts with 'this' and nothing is selected; any exception that reaches the window (run with stderr visible and look for Traceback).` },
]

const results = await pipeline(
  LENSES,
  lens => agent(lens.prompt, { label: `find:${lens.key}`, phase: 'Find', schema: FINDINGS }),
  (found, lens) => {
    if (!found || !found.findings || !found.findings.length) return { lens: lens.key, found, verdicts: [] }
    const list = found.findings.map((f, i) => `${i + 1}. [${f.severity}] ${f.title}\n   file: ${f.file}${f.line ? ':' + f.line : ''}\n   scenario: ${f.scenario}\n   evidence given: ${f.evidence}\n   reproduced by the finder: ${f.reproduced}${f.repro_script ? ' (script: ' + f.repro_script + ')' : ''}`).join('\n\n')
    return agent(`${COMMON}

YOUR TASK IS DIFFERENT: you are the second reader. Another reviewer (lens: ${lens.key}) reported the findings below against commit 702e4b8. For each one, try to REFUTE it: read the code yourself, and re-run its reproduction or write your own under ${S}/tools/review/scripts/verify-${lens.key}/ (same harness rules${lens.key === 'window' ? '; for window findings you may use the offscreen window harness described here: cd ' + S + '/work && REHEARSAL_MODEL=x REHEARSAL_SCRIPT=/path/to/script.py timeout 300 ./venv/bin/python -B ' + S + '/tools/field/nomodel.py /home/user/Struthio ' + S + '/tools/review/scripts/verify-window 1366 768 (script gets w, app, settle, QTest, Qt, operator; see ' + S + '/tools/field/ui043_probe.py)' : ''}). A finding is real only if you saw it happen or the code makes it certain; if you cannot make it happen and the code does not force it, say real=false and why. Also judge the severity yourself (a wrong value or a wrong "holds" shown to the owner is high; a crash is medium or high; an awkward sentence is low). Do not add new findings unless you trip over one while verifying; if you do, list it with real=true and say it is new.

THE FINDINGS
${list}`, { label: `verify:${lens.key}`, phase: 'Verify', schema: VERDICTS }).then(v => ({ lens: lens.key, found, verdicts: (v && v.verdicts) || [] }))
  }
)

const done = results.filter(Boolean)
const confirmed = done.flatMap(r => r.verdicts.filter(v => v.real).map(v => ({ lens: r.lens, ...v })))
const refuted = done.flatMap(r => r.verdicts.filter(v => !v.real).map(v => ({ lens: r.lens, title: v.title, reason: v.reason })))
log(`${done.length} of ${LENSES.length} lenses returned; ${confirmed.length} findings confirmed, ${refuted.length} refuted`)
return { confirmed, refuted, lenses: done.map(r => ({ lens: r.lens, findings: r.found ? r.found.findings : [], sound: r.found ? r.found.sound : '', not_covered: r.found ? r.found.not_covered : '', verdicts: r.verdicts })), missing: LENSES.map(l => l.key).filter(k => !done.some(r => r.lens === k)) }
