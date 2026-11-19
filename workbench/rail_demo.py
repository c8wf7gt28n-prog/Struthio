"""Rail Demo: a small engineering workspace made entirely of invented data, built through the Kernel's own operations.

Scenes, campaign cases and tests need a real desk to stand on: sources that were admitted, sheets that were reviewed from
them, calculations that read the sheets, findings bound to what they rest on. The owner's own workspaces are never shipped,
so this one is kept in the program instead. Every number in it was made up for the purpose; nothing was measured, and it
says so wherever it shows (NOTICE is printed on each source, and the desk's title carries "invented data").

What it holds: a 12 V rail on a bench.

    sources        three one-page PDFs, written here byte by byte (source_pdf): the bench readings and two revisions of
                   the limits. They are put in Files, brought in and admitted like any other source.
    sheets         each PDF's table reviewed into a sheet: "Rail Demo bench readings" (12 V; settled current 250 mA;
                   startup current 900 mA; startup duration 45 ms), "Rail Demo limits Rev A ARCHIVED" and
                   "Rail Demo limits Rev B CURRENT" (three limits that differ between the two, and the nominal
                   voltage, which is the same row in both).
    calculations   settled power = 12 V x 250 mA = 3 W exactly; startup power = 12 V x 900 mA = 10.8 W.
    findings       four, each bound to what it rests on: one that holds (settled power is inside the Rev B limit; the
                   readings and Rev B support it), one that does not hold (startup is inside the Rev B limit of 40 ms;
                   the readings speak against it and its check on the sheet did not hold, the reading is 45 ms), one
                   that both revisions support (the limit changed), and one whose check on the Rev B sheet passed.
    a page         a short summary, a plain page.
    a question     one open question.

Changing the settled current to 300 mA (field.set) and working the settled power again (office.datasheet.recheck) gives
3.6 W exactly; the finding that still says 3 W waits for a recheck, and so does the other calculation of the sheet.

build() goes through Kernel.dispatch with the owner's principal for every record: the same doors a person uses (Files,
bring in, admit, open the page, review the table, calculate, investigate). It writes no table directly. The work that is
a job (reading the files in, indexing them, rendering a page) is run by the Kernel's own job runner; build() runs it in
this process (Kernel.run_job, what the worker process calls) so that nothing is left running behind it.

It needs what a PDF source needs anywhere in Graphite: pypdf and Poppler's pdftotext and pdftoppm. No network, no model.
It takes a few seconds, most of them the five jobs. Graphite starts a job only when it admits it (free memory, work not
held); a job of the build that is not started within JOB_WAIT seconds is cancelled and the build stops, saying what the
job was waiting for.

    from workbench import rail_demo
    kernel, owner, demo = rail_demo.workspace(folder)   # a workspace and a profile of its own under folder, Rail Demo in it
    demo = rail_demo.build(kernel, operator())      # in a workspace that is already open -> the ids of everything it made
    demo = rail_demo.find(kernel, operator())       # the same, read back from the records of a workspace built earlier
    rail_demo.set_settled_current(kernel, operator(), '300')         # -> settled power worked again: 3.6 W
"""
from __future__ import annotations

import hashlib
import os
import shutil
import threading
from decimal import Decimal, InvalidOperation
from pathlib import Path

NAME = 'Rail Demo'
NOTICE = 'Invented demonstration data. Nothing here was measured.'
REVISION = 2                 # bump when what build() makes changes: a campaign records it with each run
JOB_WAIT = 60                # seconds a job of the build may wait to be started before the build gives up, saying why
PAGE = 100                   # rows asked of a paged list at a time
QUESTION = 'Rail Demo (invented data)'           # the investigation's question: it is the desk's title, so the mark is always in sight
COLLECTION = 'Rail Demo sources'                 # the collection the sources are admitted to, and their folder in Files
HEADERS = ('Parameter', 'Value', 'Unit', 'Conditions')

# parameter, value, unit, conditions. Invented, every one.
READINGS = (('Rail voltage', '12', 'V', 'Bench at 25 C'),
            ('Settled current', '250', 'mA', 'Bench at 25 C'),
            ('Startup current', '900', 'mA', 'Bench at 25 C'),
            ('Startup duration', '45', 'ms', 'Bench at 25 C'))
LIMITS_A = (('Settled power limit', '5', 'W', 'Continuous'),
            ('Startup duration limit', '60', 'ms', 'From switch-on'),
            ('Startup power ceiling', '12', 'W', 'Up to 60 ms'),
            ('Nominal voltage', '12', 'V', 'At the rail'))
LIMITS_B = (('Settled power limit', '4', 'W', 'Continuous'),
            ('Startup duration limit', '40', 'ms', 'From switch-on'),
            ('Startup power ceiling', '12', 'W', 'Up to 40 ms'),
            ('Nominal voltage', '12', 'V', 'At the rail'))          # the one row that is the same in both revisions

# key: (file name in Files, the sheet's title, the PDF's heading, its rows)
SOURCES = {'readings': ('Rail_Demo_Bench_Readings.pdf', 'Rail Demo bench readings', 'Rail Demo: bench readings of the 12 V rail', READINGS),
           'limits_a': ('Rail_Demo_Limits_Rev_A.pdf', 'Rail Demo limits Rev A ARCHIVED', 'Rail Demo: rail limits, Rev A (archived)', LIMITS_A),
           'limits_b': ('Rail_Demo_Limits_Rev_B.pdf', 'Rail Demo limits Rev B CURRENT', 'Rail Demo: rail limits, Rev B (current)', LIMITS_B)}
# key: (title before its result is known, expression, {symbol: cell of the readings sheet}, output unit)
CALCULATIONS = {'settled_power': ('Rail Demo settled power', 'V * I', {'V': 'B2', 'I': 'B3'}, 'W'),
                'startup_power': ('Rail Demo startup power', 'V * I', {'V': 'B2', 'I': 'B4'}, 'W')}
SETTLED_CELL = 'B3'          # settled current, on the readings sheet
SETTLED_POWER = '3'          # W, exactly: 12 V x 250 mA
STARTUP_POWER = '10.8'       # W, exactly: 12 V x 900 mA
FINDINGS = {'settled_holds': 'Settled power is 3 W, inside the Rev B limit of 4 W.',
            'startup_holds': 'Startup is inside the Rev B limit of 40 ms.',
            'limit_changed': 'The startup limit was 60 ms in Rev A and is 40 ms in Rev B.',
            'sheet_keeps': 'The Rev B sheet carries the 40 ms startup limit.'}
# finding, what the source says of it, the sources. The finding that does not hold is spoken against by the readings.
EVIDENCE = (('settled_holds', 'SUPPORTS', ('readings', 'limits_b')),
            ('limit_changed', 'SUPPORTS', ('limits_a', 'limits_b')),
            ('startup_holds', 'OPPOSES', ('readings',)))
# finding, the sheet its check reads, the rows the check looks for, what it would show, whether not finding them refutes it
CHECKS = (('startup_holds', 'readings', 'where parameter=Startup duration | where value at most 40',
           'Startup duration is at most the Rev B limit of 40 ms', True),
          ('sheet_keeps', 'limits_b', 'where parameter=Startup duration limit | where value="40"',
           'The Rev B sheet gives 40 ms as the startup duration limit', False))
OPEN_QUESTION = 'Why does startup take longer than 40 ms?'
NOTE = 'Startup duration: 45 ms on this page. Rev B allows 40 ms. (' + NOTICE + ')'
PAGE_TITLE = 'Rail Demo summary'
PAGE_TEXT = ('Rail Demo summary\n' + NOTICE + '\n'
             'The 12 V rail settles at 250 mA, which is 3 W: inside the Rev B limit of 4 W.\n'
             'Startup takes 45 ms. Rev A allowed 60 ms; Rev B allows 40 ms, so startup is 5 ms over.\n'
             'Open: why startup takes longer than 40 ms.')

# The page the sources are drawn on, in PDF points, and where the table sits on it.
PAGE_W, PAGE_H = 595, 420
COLUMNS = (48, 250, 330, 400)
TABLE_TOP, ROW_STEP, FONT = 300, 24, 11


class Unavailable(RuntimeError):
    """Rail Demo cannot be built, read or changed here; the message says why, in one sentence. Only available() says that a
    prerequisite is missing: anything else that stops a build is a fault."""


_NONE = object()


# ---------------------------------------------------------------- the sources, written byte by byte

def _pdf_text(text):
    if not all(32 <= ord(c) < 127 for c in text):
        raise ValueError('A demonstration source is written in plain ASCII')
    return text.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')


def source_pdf(heading, rows):
    """A one-page PDF with a heading, the notice and a four-column table. No clock, no random id and no library: the same
    bytes every time, so its SHA-256 is a fact of the program."""
    lines = ['BT /F1 14 Tf %d %d Td (%s) Tj ET' % (COLUMNS[0], PAGE_H - 48, _pdf_text(heading)),
             'BT /F1 9 Tf %d %d Td (%s) Tj ET' % (COLUMNS[0], PAGE_H - 66, _pdf_text(NOTICE))]
    for n, row in enumerate((HEADERS, *rows)):
        for x, cell in zip(COLUMNS, row):
            lines.append('BT /F1 %d Tf %d %d Td (%s) Tj ET' % (FONT, x, TABLE_TOP - n * ROW_STEP, _pdf_text(cell)))
    stream = '\n'.join(lines)
    objects = ['<< /Type /Catalog /Pages 2 0 R >>',
               '<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
               '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %d %d] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>' % (PAGE_W, PAGE_H),
               '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>',
               '<< /Length %d >>\nstream\n%s\nendstream' % (len(stream), stream)]
    out = '%PDF-1.4\n';offsets = []
    for number, body in enumerate(objects, 1):
        offsets.append(len(out));out += '%d 0 obj\n%s\nendobj\n' % (number, body)
    start = len(out)
    out += 'xref\n0 %d\n0000000000 65535 f \n' % (len(objects) + 1) + ''.join('%010d 00000 n \n' % at for at in offsets)
    out += 'trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (len(objects) + 1, start)
    return out.encode('ascii')


def table_region(rows):
    """Where the table is on the rendered page: [x, y, width, height] as parts of the page, from its top left corner."""
    top = (PAGE_H - TABLE_TOP - ROW_STEP * 0.75) / PAGE_H
    height = (len(rows) + 1) * ROW_STEP / PAGE_H
    return [round(v, 4) for v in (0.04, top, 0.92, height)]


def row_region(row):
    """Where one row of the table is on the page (row 1 is the first under the headings), in the same parts of the page."""
    top = (PAGE_H - TABLE_TOP + ROW_STEP * (row - 0.75)) / PAGE_H
    return [round(v, 4) for v in (0.04, top, 0.92, ROW_STEP / PAGE_H)]


def sources():
    """{key: {'name', 'title', 'bytes', 'sha256', 'rows'}} for the three sources, as build() admits them."""
    out = {}
    for key, (name, title, heading, rows) in SOURCES.items():
        raw = source_pdf(heading, rows)
        out[key] = {'name': name, 'title': title, 'bytes': raw, 'sha256': hashlib.sha256(raw).hexdigest(), 'rows': rows}
    return out


def available():
    """'' when the demonstration workspace can be built here, or the one sentence that says what is missing."""
    try:
        import pypdf  # noqa: F401
    except ImportError:
        return 'Rail Demo needs pypdf to read its PDF sources (pip install -r requirements-qt.txt).'
    missing = [name for name in ('pdftotext', 'pdftoppm') if not shutil.which(name)]
    if missing:
        return 'Rail Demo needs Poppler to read its PDF sources: %s not found (Debian: apt install poppler-utils).' % ' and '.join(missing)
    return ''


# ---------------------------------------------------------------- building it, one Kernel operation at a time

class _Desk:
    """The Kernel as Rail Demo uses it: every call is Kernel.dispatch with the owner's principal, and a refusal stops the
    work with what was being done (`doing`), the operation and Graphite's own reason."""

    def __init__(self, kernel, principal, doing='Rail Demo could not be built'):
        self.kernel = kernel;self.principal = principal;self.doing = doing;self.operations = []

    def call(self, operation, arguments=None):
        answer = self.kernel.dispatch(operation, arguments or {}, self.principal)
        self.operations.append(operation)
        if not answer.get('ok'):
            error = answer.get('error') or {}
            raise Unavailable('%s: %s was refused (%s).' % (self.doing, operation, str(error.get('message') or error.get('code') or error)[:300]))
        return answer['result']

    def job(self, operation, arguments):
        """An operation that is a job: submitted through its own operation, then run by the Kernel's job runner here, in this
        process, instead of by a worker process left behind. The job's record, evidence and result are the runner's own."""
        started = [];held = vars(self.kernel).get('launch', _NONE)
        self.kernel.launch = started.append          # the worker process's one call is run_job; it is made below instead
        try:
            job = self.call(operation, arguments)
        finally:                                     # a hold the caller had put on this Kernel is put back as it was
            if held is _NONE:del self.kernel.launch
            else:self.kernel.launch = held
        for ident in started:self.run(ident)
        done = self.call('jobs.get', {'id': job['id']})
        if done.get('state') != 'Completed':
            raise Unavailable('%s: the %s job ended %s (%s).' % (
                self.doing, operation, done.get('state'), str(done.get('error') or done.get('current_operation') or '')[:300]))
        return done

    def run(self, ident):
        """The Kernel's job runner on one job, with a deadline on its wait to be started. The runner starts a job only when
        Graphite admits it and waits until then, for as long as it takes; with a large model loaded that can be for ever.
        A job still queued after JOB_WAIT seconds is cancelled through its own operation, which ends the runner's wait,
        and the work stops with what the job was waiting for."""
        waited = []

        def give_up():
            try:
                job = self.call('jobs.get', {'id': ident})
                if job.get('state') != 'Queued':return       # started meanwhile: it runs to its own end
                waited.append('%s: the %s job was not started in %g s (%s).' % (
                    self.doing, job.get('tool'), JOB_WAIT, str(job.get('current_operation') or 'no reason was given')[:200]))
                self.call('jobs.cancel', {'id': ident})
            except Unavailable as refused:
                waited.append(str(refused))
        watch = threading.Timer(JOB_WAIT, give_up);watch.daemon = True;watch.start()
        try:
            self.kernel.run_job(ident)
        finally:
            watch.cancel();watch.join()
        if waited:
            raise Unavailable(waited[0])


def build(kernel, principal):
    """Build Rail Demo in this (empty) workspace. Returns the ids and titles of everything it made (see find())."""
    why = available()
    if why:
        raise Unavailable(why)
    desk = _Desk(kernel, principal)
    if any(space.get('name') == COLLECTION for space in desk.call('intake.namespaces').get('namespaces', ())):
        raise Unavailable('Rail Demo is already in this workspace.')
    made = sources()
    # 1. the sources: put in Files, brought in, admitted
    for item in made.values():
        written = desk.call('files.write', {'path': '%s/%s' % (COLLECTION, item['name']), 'text': item['bytes'].decode('ascii')})
        if written.get('sha256') not in (None, item['sha256']):
            raise Unavailable('Rail Demo could not be built: Files changed the bytes of %s.' % item['name'])
    folder = desk.call('files.list', {'path': COLLECTION})
    space = desk.call('intake.namespace.create', {'name': COLLECTION})
    desk.job('intake.import', {'namespace': space['id'], 'path': str(_folder(folder, kernel)), 'mode': 'snapshot'})
    listed = {row['name']: row for row in desk.call('intake.items', {'namespace': space['id']})['items']}
    for key, item in made.items():
        row = listed.get(item['name'])
        if row is None or row['sha256'] != item['sha256']:
            raise Unavailable('Rail Demo could not be built: %s was not brought in as written.' % item['name'])
        seen = desk.call('intake.item', {'id': row['id']})
        desk.call('intake.decide', {'id': row['id'], 'decision': 'ACCEPTED', 'expected_sha256': row['sha256'],
                                    'expected_policy_hash': seen['policy_hash'], 'expected_decision': '',
                                    'reason': 'Rail Demo: an invented demonstration source, admitted as written'})
        item['item'] = row['id']
    desk.job('references.index', {'namespace': space['id']})        # the collection can be searched, like any admitted one
    # 2. each source's table, reviewed into a sheet
    for key, item in made.items():
        page = desk.job('references.pdf.page', {'namespace': space['id'], 'item': item['item'], 'source_sha256': item['sha256'], 'page_index': 0})
        region = table_region(item['rows'])
        preview = desk.call('office.datasheet.preview', {'job': page['id'], 'rect': region, 'layer': 'native'})
        read = [(r['parameter'], r['value'], r['unit'], r['conditions']) for r in preview.get('rows', ())]
        if preview.get('state') != 'REVIEW' or read != [tuple(row) for row in item['rows']]:
            raise Unavailable('Rail Demo could not be built: the table of %s was not read as written (%r).' % (item['name'], read))
        sheet = desk.call('office.datasheet.create', {
            'job': page['id'], 'rect': region, 'layer': 'native', 'expected_digest': preview['digest'], 'title': item['title'],
            'rows': [{'source_row': r['source_row'], 'parameter': r['parameter'], 'value': r['value'], 'unit': r['unit'], 'conditions': r['conditions']}
                     for r in preview['rows']]})
        item['sheet'] = sheet['id'];item['page_job'] = page['id']
    # 3. the calculations, each named with its result
    for title, expression, inputs, unit in CALCULATIONS.values():
        sheet = desk.call('office.get', {'id': made['readings']['sheet']})
        worked = desk.call('office.datasheet.report', {'id': sheet['id'], 'expected_revision': sheet['revision'], 'expression': expression,
                                                       'inputs': inputs, 'output_unit': unit})
        document = worked['document'];value = worked['calculation']['outputs'][0]['value']
        desk.call('documents.save', {'id': document['id'], 'expected_revision': document['revision'], 'blocks': document['blocks'],
                                     'title': '%s · %s %s' % (title, value['decimal'], value['unit']), 'origin': 'HUMAN'})
    # 4. the page
    desk.call('documents.create', {'title': PAGE_TITLE, 'text': PAGE_TEXT, 'origin': 'HUMAN'})
    # 5. the investigation: its sources, its findings bound to them, the checks, the open question
    inv = desk.call('investigation.create', {'question': QUESTION, 'objective': NOTICE + ' Does the 12 V rail meet its limits?'})
    read = {key: desk.call('investigation.add_source', {'id': inv['id'], 'address': 'intake:' + item['item']})['source'] for key, item in made.items()}
    claims = {key: desk.call('investigation.claim', {'id': inv['id'], 'text': text, 'role': 'FINDING'})['claim'] for key, text in FINDINGS.items()}
    for claim, direction, keys in EVIDENCE:
        for key in keys:
            desk.call('investigation.evidence', {'claim': claims[claim], 'direction': direction, 'source': read[key],
                                                 'note': 'Read from %s' % made[key]['name']})
    for claim, sheet, rows, oracle, refutes in CHECKS:
        desk.call('investigation.check', {'claim': claims[claim], 'program': '@office:%s | pick origin.reviewed_rows | %s' % (made[sheet]['sheet'], rows),
                                          'oracle': oracle, 'expect': 'NONEMPTY', 'refutes_on_fail': refutes})
    desk.call('investigation.claim', {'id': inv['id'], 'text': OPEN_QUESTION, 'role': 'QUESTION'})
    desk.call('investigation.continue', {'id': inv['id']})      # the Kernel runs the two checks: one passes, one does not hold
    # 6. one note on the readings, where the startup row is
    place = made['readings']
    desk.call('references.pdf.annotation.save', {'namespace': space['id'], 'item': place['item'], 'source_sha256': place['sha256'], 'page_index': 0,
                                                 'rect': row_region(len(READINGS)), 'kind': 'NOTE', 'text': NOTE, 'expected_version': 0})
    return find(kernel, principal)


def _folder(listing, kernel):
    """The folder in Files the sources were written to, as a path on this computer."""
    from . import files_service
    return Path(listing.get('root') or files_service.root(kernel)) / COLLECTION


def workspace(base):
    """Rail Demo in a workspace of its own under `base` (a new or empty folder, such as a test's temporary one), with a
    profile and a Concern folder of its own beside it. A reviewed sheet is kept in the profile, so this points the process's
    Graphite locations at those folders before anything is written (as workbench.edit_checks.fixture does): nothing of Rail
    Demo reaches the profile of the person at the computer. Returns (kernel, principal, what build() made). The caller
    deletes `base`, and puts the environment back if it goes on to other work (unittest.mock.patch.dict(os.environ))."""
    from .baseline import environment
    from .engineering_kernel import Kernel, operator
    from .locations import office
    base = Path(base);root = base / 'workspace'
    os.environ.update(environment(os.environ, root, base / 'profile'), ARC_LEDGER_CONCERN=str(base / 'Concern'))
    kernel = Kernel(office(root));principal = operator()
    return kernel, principal, build(kernel, principal)


# ---------------------------------------------------------------- reading it back, and the one change it is made for

def find(kernel, principal):
    """Rail Demo as the records of this workspace hold it now, found by its names: {'collection', 'sources': {key: {'item',
    'name', 'sha256'}}, 'sheets': {key: id}, 'calculations': {key: id of the one that stands now}, 'page', 'investigation',
    'findings': {key: claim id}, 'question'}. Raises Unavailable when it is not here, or not whole."""
    desk = _Desk(kernel, principal, 'Rail Demo could not be read')
    space = next((s for s in desk.call('intake.namespaces').get('namespaces', ()) if s.get('name') == COLLECTION), None)
    if space is None:
        raise Unavailable('Rail Demo is not in this workspace.')
    items = {row['name']: row for row in desk.call('intake.items', {'namespace': space['id']})['items']}
    here = {row['id'] for row in items.values()}
    sheets = {}
    for row in desk.call('office.list').get('documents', ()):       # sheets live in the profile: ours are the ones read from our sources
        if row.get('title') in {title for _, title, _, _ in SOURCES.values()}:
            origin = desk.call('office.get', {'id': row['id']}).get('origin') or {}
            if (origin.get('pdf') or {}).get('item') in here:sheets[row['title']] = row['id']
    pages = []
    while True:                 # every page of the workspace: a page of the list at a time, until a short one comes back
        some = list(desk.call('documents.list', {'limit': PAGE, 'offset': len(pages)}).get('documents', ()))
        pages.extend(some)
        if len(some) < PAGE:break
    replaced = set();derived = {}
    for row in pages:
        derivation = (desk.call('documents.get', {'id': row['id']}).get('document') or {}).get('derivation') or {}
        if derivation.get('replaces'):replaced.add(derivation['replaces'])
        if derivation:derived[row['id']] = row['title']
    inv = next((row for row in desk.call('investigation.list').get('investigations', ()) if row.get('question') == QUESTION), None)
    if inv is None:
        raise Unavailable('Rail Demo is not whole in this workspace: its findings are missing.')
    sheet = desk.call('investigation.sheet', {'id': inv['id']})
    claims = {}
    for claim in list(sheet.get('unresolved') or ()) + list(sheet.get('learned') or ()) + list(sheet.get('retired') or ()):
        claims.setdefault(claim['text'], claim['id'])
    try:
        return {'name': NAME, 'notice': NOTICE, 'revision': REVISION, 'collection': space['id'],
                'sources': {key: {'item': items[name]['id'], 'name': name, 'sha256': items[name]['sha256']} for key, (name, _, _, _) in SOURCES.items()},
                'sheets': {key: sheets[title] for key, (_, title, _, _) in SOURCES.items()},
                'calculations': {key: next(ident for ident, name in derived.items() if name.startswith(title) and ident not in replaced)
                                 for key, (title, _, _, _) in CALCULATIONS.items()},
                'page': next(row['id'] for row in pages if row['title'] == PAGE_TITLE),
                'investigation': inv['id'], 'findings': {key: claims[text] for key, text in FINDINGS.items()}, 'question': claims[OPEN_QUESTION]}
    except (KeyError, StopIteration) as missing:
        raise Unavailable('Rail Demo is not whole in this workspace: %s is missing.' % (missing.args[0] if missing.args else 'a record')) from None


def set_settled_current(kernel, principal, value='300'):
    """The change Rail Demo is made for: the settled current set to another value on the working sheet (field.set), and the
    settled power worked again from it (office.datasheet.recheck). The reviewed source keeps its reading; the finding that
    still says the old result waits for a recheck, and so does the other calculation of the sheet. A change that was
    stopped after the cell was written and before the power was worked again is carried on by asking for the same value
    again: the cell is left as it is and the power is worked from it.
    Returns {'was', 'now', 'unit', 'sheet_revision', 'calculation': the new page's id, 'power', 'exact', 'power_unit'}."""
    desk = _Desk(kernel, principal, 'The settled current of Rail Demo could not be changed');demo = find(kernel, principal)
    sheet = desk.call('office.get', {'id': demo['sheets']['readings']})
    page = desk.call('documents.get', {'id': demo['calculations']['settled_power']})['document']
    cell = ((sheet['document'].get('sheets') or [{}])[0].get('cells') or {}).get(SETTLED_CELL) or {}
    read = next((i.get('value') for i in (page.get('derivation') or {}).get('inputs') or () if i.get('cell') == SETTLED_CELL), None)
    if _same(cell.get('value'), value) and read is not None and not _same(read, value):
        # the cell already says it and the settled power was worked from another value: carried on from the recheck
        changed = {'was': str(read), 'now': str(cell.get('value')), 'unit': str(cell.get('unit') or '').strip(), 'revision': sheet['revision']}
    else:
        changed = desk.call('field.set', {'id': 'office:' + sheet['id'], 'cell': SETTLED_CELL, 'value': str(value), 'expected_revision': sheet['revision']})
    worked = desk.call('office.datasheet.recheck', {'id': page['id'], 'expected_revision': page['revision']})
    result = worked['calculation']['outputs'][0]['value']
    return {'was': changed['was'], 'now': changed['now'], 'unit': changed['unit'], 'sheet_revision': changed['revision'],
            'calculation': worked['document']['id'], 'power': result['decimal'], 'exact': result['rational'], 'power_unit': result['unit']}


def _same(a, b):
    """Whether two values written as text are the same number."""
    try:
        return Decimal(str(a).strip()) == Decimal(str(b).strip())
    except InvalidOperation:
        return False
