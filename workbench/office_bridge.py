"""LibreOffice, from the inside (Graphite 1.0, K5): Writer and Calc through LibreOffice's own interface (UNO).

The owner's paper, sections 10 and 12: "if she asks Writer to update a report, the saved document revision is the relevant
output of another step. Neither should be called finished merely because a command was dispatched." And: "'Clicked Save'
and 'the expected revision exists on disk' are different observations; reliable completion requires the latter."

How it works. Graphite's own Python cannot import LibreOffice's uno module, so the bridge has two halves:

  this module      in Graphite (the Kernel's side): finds LibreOffice and a Python that has uno, owns a headless LibreOffice
                   of her own, checks every precondition, reads the saved file back itself and records its revision;
  office_uno_helper.py   a small helper run under that Python (on Debian /usr/bin/python3 with python3-uno), which speaks
                   UNO to her LibreOffice over a private pipe, and to this module in JSON lines on its stdin and stdout.

Her LibreOffice is owned as the Calc sessions of native_sessions.py are: a profile of its own (macros never run, no
recovery, her name on its lock files: "Kasandra (Graphite)"), a private pipe, its own process group, started for one piece
of work and ended after it in every case (terminate, then the group's TERM, then KILL); one at a time (a lock in the
Kernel's state); a session left behind by a crash is found and ended by the next one. It is headless: it never shows a
window, and the owner's own LibreOffice windows are never driven (his LibreOffice runs with his profile; hers with hers).

The rules the code keeps:
  - A document the owner has open in LibreOffice (its lock file .~lock.<name># is there and is not hers) is never edited
    behind his back: the change is refused with the reason.
  - A change is made only at the revision the plan read (expected_sha256), only where the passage is in exactly the
    places named (occurrences, 1 unless said), and only on an OpenDocument file (.odt, .ods); a cell holding a formula is
    never overwritten.
  - Before the save: HALT or Stop all (the work gate) leaves it unsaved; the version before is kept (Files' .versions); a
    suspend waits for the save (session_power.sleep_held, S1).
  - Verified, never assumed: the saved file is read back directly (its content.xml, parsed here, not by LibreOffice) and
    compared with what the change should give: every paragraph (or every cell) as before except the change. Only then is
    it "verified". Its new revision is recorded through revisions.record (L4), so the board marks what rests on it.
  - Without LibreOffice or without uno, the bridge says why ("LibreOffice's interface is not available here: ..."), reads
    OpenDocument files directly, and offers a change as prepared text (libreoffice.prepare) instead of making it.
  - No floating point: cell values are compared as Decimal from the text the file holds; times are whole milliseconds.

Kernel operations (registered in engineering_kernel and engineering_cli under "1.0 K5"):

  libreoffice.status    {}                                                        read     here or not, and why; the operations
  libreoffice.read      {path, sheet?, range?, expected_sha256?}                  read     paragraphs and tables, or a sheet's cells
  libreoffice.find      {path, text}                                              read     where a passage is
  libreoffice.prepare   {path, find+replace | cell+value, sheet?, occurrences?}   read     the change as prepared text: nothing written
  libreoffice.replace   {path, find, replace, occurrences?, expected_sha256?}     approve  a passage of a Writer document replaced, saved,
                                                                                           read back, its revision recorded
  libreoffice.cell      {path, cell, value, sheet?, kind?, expected_sha256?}      approve  a value cell of a Calc sheet set, saved, read
                                                                                           back (formulas recalculated), recorded

The two changes are marked for the owner's approval: in an assignment (K1) each is authorised by its own name, with its
arguments fixed when he authorises it. Their checks (assignments.CHECKS) look for the effect before it is made again and
verify it after. describe() lists the operations for the tool registry (K2); when K2's tools_registry is here, its slots
"office.read" and "office.edit" are filled with them. offer_update() is K4's: the step that puts a checked value in its
sentence of a report, or, when LibreOffice is not here, that change as prepared text.

The invented examples (place_examples): "Rail Demo summary report.odt", which says "Settled power is 3.0 W at 12 V." and
has a table of the Rev B limits, and "Rail Demo power sheet.ods", whose settled current (B3) feeds a formula (B4). Every
number in them is made up.
"""
from __future__ import annotations

import contextlib
import fcntl
import hashlib
import io
import json
import os
import re
import select
import shutil
import signal
import subprocess
import time
import uuid
import zipfile
import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation
from pathlib import Path
from xml.sax.saxutils import escape

from . import assignments as _asg

SCHEMA = 'graphite.office-bridge/1'
HELPER = Path(__file__).with_name('office_uno_helper.py')
PROGRAM = 'LibreOffice (Kasandra)'          # how her saves are named among a file's revisions (L4)
HER_NAME = ('Kasandra', '(Graphite)')       # the name her LibreOffice writes into a document's lock file
NOT_HERE = "LibreOffice's interface is not available here"
EDITS = ('.odt', '.ods')
READS = ('.odt', '.ods', '.fodt', '.fods', '.docx', '.doc', '.rtf', '.xlsx', '.xls')
DIRECT = ('.odt', '.ods')                   # what is read without LibreOffice (its content.xml)
PROBE_SECONDS = 300                         # how long what was found about LibreOffice is trusted
LOCK_SECONDS = 120                          # how long a piece of work waits for her LibreOffice to be free
START_SECONDS = 90                          # how long her LibreOffice may take to answer on its pipe
CALL_SECONDS = 60                           # one request
SAVE_SECONDS = 180                          # a save
BIGGEST = 256 * 1024 * 1024                 # a document larger than this is not opened
CONTENT_LIMIT = 64 * 1024 * 1024            # a content.xml larger than this is not read
MAX_ROWS, MAX_COLUMNS, MAX_CELLS = 100000, 1024, 200000

REL = {'type': 'string', 'minLength': 1, 'maxLength': 1000}
SHA = {'type': 'string', 'pattern': '^[0-9a-f]{64}$', 'minLength': 64, 'maxLength': 64}
PASSAGE = {'type': 'string', 'minLength': 1, 'maxLength': 4000}
NEW = {'type': 'string', 'maxLength': 4000}
SHEET = {'type': 'string', 'minLength': 1, 'maxLength': 200}
CELL = {'type': 'string', 'pattern': '^[A-Z]{1,3}[1-9][0-9]{0,6}$', 'minLength': 2, 'maxLength': 10}
RANGE = {'type': 'string', 'pattern': '^[A-Z]{1,3}[1-9][0-9]{0,6}(:[A-Z]{1,3}[1-9][0-9]{0,6})?$', 'minLength': 2, 'maxLength': 21}
VALUE = {'type': 'string', 'maxLength': 4000}
OCCURRENCES = {'type': 'integer', 'minimum': 1, 'maximum': 100}
FIELDS = {
    'libreoffice.status': ({}, []),
    'libreoffice.read': ({'path': REL, 'sheet': SHEET, 'range': RANGE, 'expected_sha256': SHA}, ['path']),
    'libreoffice.find': ({'path': REL, 'text': PASSAGE}, ['path', 'text']),
    'libreoffice.prepare': ({'path': REL, 'find': PASSAGE, 'replace': NEW, 'sheet': SHEET, 'cell': CELL, 'value': VALUE,
                             'occurrences': OCCURRENCES}, ['path']),
    'libreoffice.replace': ({'path': REL, 'find': PASSAGE, 'replace': NEW, 'occurrences': OCCURRENCES, 'expected_sha256': SHA},
                            ['path', 'find', 'replace']),
    'libreoffice.cell': ({'path': REL, 'cell': CELL, 'value': VALUE, 'sheet': SHEET, 'kind': {'type': 'string', 'enum': ['number', 'text']},
                          'expected_sha256': SHA}, ['path', 'cell', 'value']),
}
SCOPES = {'libreoffice.status': 'read', 'libreoffice.read': 'read', 'libreoffice.find': 'read', 'libreoffice.prepare': 'read',
          'libreoffice.replace': 'approve', 'libreoffice.cell': 'approve'}
CELL_RE = re.compile(r'^([A-Z]{1,3})([1-9][0-9]{0,6})$')
RANGE_RE = re.compile(r'^[A-Z]{1,3}[1-9][0-9]{0,6}(:[A-Z]{1,3}[1-9][0-9]{0,6})?$')
SHA_RE = re.compile(r'^[0-9a-f]{64}$')
NUMBER_RE = re.compile(r'^[+-]?\d{1,30}(\.\d{1,30})?$')

OFFICE = '{urn:oasis:names:tc:opendocument:xmlns:office:1.0}'
TEXT = '{urn:oasis:names:tc:opendocument:xmlns:text:1.0}'
TABLE = '{urn:oasis:names:tc:opendocument:xmlns:table:1.0}'
DRAW = '{urn:oasis:names:tc:opendocument:xmlns:drawing:1.0}'
ODT_TYPE = 'application/vnd.oasis.opendocument.text'
ODS_TYPE = 'application/vnd.oasis.opendocument.spreadsheet'


class Unavailable(ValueError):
    """LibreOffice's interface is not here (or not now); the message says why."""


class BridgeError(ValueError):
    """Her LibreOffice or the helper did not do what was asked; the message says what."""


# ---------------------------------------------------------------- is it here, and why not

_PROBE = {'at': None, 'value': None}


def _unavailable(reason, **more):
    return {'available': False, 'reason': reason, 'words': '%s: %s.' % (NOT_HERE, reason.rstrip('.')), **more}


def _python_candidates(program_dir):
    seen = []
    for candidate in (os.environ.get('GRAPHITE_UNO_PYTHON'), str(Path(program_dir) / 'python') if program_dir else None,
                      '/usr/bin/python3', shutil.which('python3')):
        if candidate and candidate not in seen and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            seen.append(candidate)
    return seen


def uno_python(program_dir=None):
    """(the Python that can import LibreOffice's uno module, its version, what was tried). The Python LibreOffice ships
    (its program/python) comes before the system's; GRAPHITE_UNO_PYTHON names one explicitly."""
    tried = []
    for python in _python_candidates(program_dir):
        try:
            run = subprocess.run([python, '-I', '-c', 'import uno, sys; print(sys.version.split()[0])'], stdin=subprocess.DEVNULL,
                                 capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.SubprocessError) as exc:
            tried.append('%s: %s' % (python, str(exc)[:120]))
            continue
        if run.returncode == 0:
            return python, run.stdout.strip(), tried
        tried.append('%s cannot import uno' % python)
    return None, '', tried


def _probe():
    if os.environ.get('GRAPHITE_LIBREOFFICE', '').strip().lower() in ('off', 'no', '0', 'false'):
        return _unavailable('the bridge is turned off on this computer (GRAPHITE_LIBREOFFICE=off)')
    from . import office_runtime
    try:
        office = office_runtime.probe()
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        return _unavailable('LibreOffice is installed but did not say its version (%s)' % str(exc)[:160])
    if not office.get('available'):
        return _unavailable('LibreOffice is not installed (no soffice); on Debian it is libreoffice-writer and libreoffice-calc')
    python, version, tried = uno_python(Path(office['executable']).parent)
    if not python:
        return _unavailable("no Python here can import LibreOffice's uno module (python3-uno is not installed; on Debian it is "
                            "the package python3-uno)", soffice=office['executable'], version=office.get('version', ''), tried=tried)
    if not HELPER.is_file():
        return _unavailable("the bridge's helper (office_uno_helper.py) is missing from this Graphite")
    return {'available': True, 'reason': '', 'soffice': office['executable'], 'version': office.get('version', ''), 'python': python,
            'python_version': version, 'words': "LibreOffice's interface is here: %s, through %s (Python %s)." % (
                office.get('version', 'LibreOffice'), python, version)}


def probe(fresh=False):
    """What was found about LibreOffice here: {'available', 'reason', 'words', 'soffice', 'version', 'python'}. Looked for
    again after PROBE_SECONDS, or when fresh."""
    now = time.monotonic()
    if fresh or _PROBE['value'] is None or now - _PROBE['at'] > PROBE_SECONDS:
        _PROBE.update(at=now, value=_probe())
    return dict(_PROBE['value'])


def available():
    """(whether her LibreOffice can be used here now, why not in words): the shape K2's registry asks of a slot."""
    found = probe()
    return bool(found['available']), '' if found['available'] else found['words']


# ---------------------------------------------------------------- OpenDocument, read directly (no LibreOffice)

def _collapse(parts):
    """A paragraph's text from its parts (text, literal): ODF's white-space rule (a run of spaces, tabs and line ends in the
    XML is one space; a leading one is dropped), with text:s, text:tab and text:line-break kept as they are."""
    out = []
    spaced = True
    for text, literal in parts:
        if literal:
            out.append(text)
            spaced = False
            continue
        for ch in text:
            if ch in ' \t\r\n':
                if not spaced:
                    out.append(' ')
                    spaced = True
            else:
                out.append(ch)
                spaced = False
    return ''.join(out)


SKIP_TEXT = {OFFICE + 'annotation', OFFICE + 'annotation-end', TEXT + 'note', TEXT + 'tracked-changes', DRAW + 'frame',
             TEXT + 'bookmark-start', TEXT + 'bookmark-end'}


def paragraph_text(element):
    parts = []

    def walk(node):
        if node.text:
            parts.append((node.text, False))
        for child in node:
            tag = child.tag
            if tag == TEXT + 's':
                try:
                    count = max(1, min(int(child.get(TEXT + 'c', '1') or 1), 10000))
                except ValueError:
                    count = 1
                parts.append((' ' * count, True))
            elif tag == TEXT + 'tab':
                parts.append(('\t', True))
            elif tag == TEXT + 'line-break':
                parts.append(('\n', True))
            elif tag not in SKIP_TEXT:
                walk(child)
            if child.tail:
                parts.append((child.tail, False))
    walk(element)
    return _collapse(parts)


def column_name(index):
    name = ''
    index += 1
    while index:
        index, rest = divmod(index - 1, 26)
        name = chr(65 + rest) + name
    return name


def _repeat(element, attribute, limit):
    try:
        return max(1, min(int(element.get(TABLE + attribute, '1') or 1), limit))
    except ValueError:
        return 1


def _rows(table):
    """A table's rows in order, through header rows, row groups and the like (not into a table inside a cell)."""
    for child in table:
        if child.tag == TABLE + 'table-row':
            yield child
        elif child.tag in (TABLE + 'table-header-rows', TABLE + 'table-rows', TABLE + 'table-row-group'):
            yield from _rows(child)


def _cell_view(cell):
    kind = cell.get(OFFICE + 'value-type') or ''
    paragraphs = [paragraph_text(p) for p in cell if p.tag in (TEXT + 'p', TEXT + 'h')]
    text = '\n'.join(paragraphs)
    formula = cell.get(TABLE + 'formula') or ''
    if not kind and not text and not formula:
        return None
    value = {'float': OFFICE + 'value', 'percentage': OFFICE + 'value', 'currency': OFFICE + 'value', 'date': OFFICE + 'date-value',
             'time': OFFICE + 'time-value', 'boolean': OFFICE + 'boolean-value', 'string': OFFICE + 'string-value'}.get(kind)
    found = cell.get(value) if value else None
    return {'type': kind or 'string', 'value': found if found is not None else text, 'text': text, 'formula': formula}


def table_cells(table, flat=None):
    """{A1: view} of a table (a sheet, or a table in a text), and each cell's paragraphs appended to flat in order."""
    cells = {}
    row_index = 0
    for row in _rows(table):
        repeat = _repeat(row, 'number-rows-repeated', MAX_ROWS)
        column = 0
        found = []
        for cell in row:
            if cell.tag not in (TABLE + 'table-cell', TABLE + 'covered-table-cell'):
                continue
            span = _repeat(cell, 'number-columns-repeated', MAX_COLUMNS)
            view = _cell_view(cell)
            if view is not None and column < MAX_COLUMNS:
                found.extend((column + k, view) for k in range(min(span, MAX_COLUMNS - column)))
                if flat is not None:
                    for k in range(min(span, 64)):
                        _walk_text(cell, flat, None)
            column += span
        if found:
            for r in range(min(repeat, MAX_ROWS - row_index)):
                for col, view in found:
                    cells['%s%d' % (column_name(col), row_index + r + 1)] = view
                if len(cells) >= MAX_CELLS:
                    return cells
        row_index += repeat
        if row_index >= MAX_ROWS:
            break
    return cells


SKIP_BLOCKS = {TEXT + 'tracked-changes', TEXT + 'sequence-decls', TEXT + 'variable-decls', TEXT + 'user-field-decls',
               OFFICE + 'forms', TEXT + 'table-of-content-source', OFFICE + 'annotation'}


def _walk_text(node, flat, blocks):
    for child in node:
        tag = child.tag
        if tag in (TEXT + 'p', TEXT + 'h'):
            text = paragraph_text(child)
            flat.append(text)
            if blocks is not None:
                blocks.append({'kind': 'paragraph', 'n': sum(1 for b in blocks if b['kind'] == 'paragraph') + 1, 'text': text,
                               'place': len(flat)})
        elif tag == TABLE + 'table':
            cells = table_cells(child, flat)
            if blocks is not None:
                blocks.append({'kind': 'table', 'name': child.get(TABLE + 'name') or 'Table',
                               'cells': {k: v['text'] for k, v in cells.items()}})
        elif tag in SKIP_BLOCKS:
            continue
        else:
            _walk_text(child, flat, blocks)


def read_odf(path):
    """An OpenDocument file read directly, without LibreOffice: {'kind': 'text' | 'spreadsheet', 'mimetype', 'paragraphs':
    every paragraph's text in order (the body's, then each table cell's where it stands), 'blocks': the body's paragraphs
    and tables, 'sheets': [{'name', 'cells'}]}. Raises ValueError when it is not one."""
    path = Path(path)
    try:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            mimetype = archive.read('mimetype').decode('utf-8', 'replace').strip() if 'mimetype' in names else ''
            info = archive.getinfo('content.xml')
            if info.file_size > CONTENT_LIMIT:
                raise ValueError('ODF_TOO_LARGE: %s is larger than Graphite reads directly' % path.name)
            content = archive.read(info)
    except (zipfile.BadZipFile, KeyError, OSError) as exc:
        raise ValueError('ODF_UNREADABLE: %s is not an OpenDocument file Graphite can read (%s)' % (path.name, str(exc)[:120])) from None
    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        raise ValueError('ODF_UNREADABLE: the content of %s is not well-formed (%s)' % (path.name, str(exc)[:120])) from None
    body = root.find(OFFICE + 'body')
    out = {'mimetype': mimetype, 'paragraphs': [], 'blocks': [], 'sheets': []}
    text = body.find(OFFICE + 'text') if body is not None else None
    sheet = body.find(OFFICE + 'spreadsheet') if body is not None else None
    if text is not None:
        out['kind'] = 'text'
        _walk_text(text, out['paragraphs'], out['blocks'])
    elif sheet is not None:
        out['kind'] = 'spreadsheet'
        for table in sheet.findall(TABLE + 'table'):
            out['sheets'].append({'name': table.get(TABLE + 'name') or 'Sheet', 'cells': table_cells(table)})
    else:
        raise ValueError('ODF_KIND: %s is neither a text document nor a spreadsheet' % path.name)
    return out


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def sha256_of(path):
    from .depths import sha256_of as whole
    return whole(path)


def _sheet_of(document, name=None):
    sheets = document.get('sheets') or []
    if not sheets:
        raise ValueError('ODF_NO_SHEET: the spreadsheet has no sheet')
    if name:
        for sheet in sheets:
            if sheet['name'] == name:
                return sheet
        raise ValueError('ODF_NO_SHEET: there is no sheet "%s" (there are %s)' % (name[:60], ', '.join(s['name'] for s in sheets)[:200]))
    return sheets[0]


def _same_value(view, value, kind):
    """Whether a cell as the file holds it is the value given: the same number exactly (Decimal), or the same text."""
    if view is None:
        return False
    if kind == 'number':
        if view.get('type') not in ('float', 'percentage', 'currency'):
            return False
        try:
            return Decimal(str(view.get('value'))) == Decimal(value.strip())
        except InvalidOperation:
            return False
    return view.get('type') == 'string' and view.get('text') == value


def sentences(paragraph):
    """A paragraph's sentences: a stop (. ! ?) ends one only when a space or the end follows it (so 3.0 stays whole)."""
    return [m.group(0).strip() for m in re.finditer(r'(?:[^.!?]|[.!?](?!\s|$))+[.!?]*', paragraph or '') if m.group(0).strip()]


# ---------------------------------------------------------------- the invented examples (Rail Demo)

REPORT_NAME = 'Rail Demo summary report.odt'
SHEET_NAME = 'Rail Demo power sheet.ods'
POWER_SENTENCE = 'Settled power is 3.0 W at 12 V.'
SETTLED_CELL = 'B3'
_NS = ('xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" '
       'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" '
       'xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" xmlns:meta="urn:oasis:names:tc:opendocument:xmlns:meta:1.0" '
       'xmlns:of="urn:oasis:names:tc:opendocument:xmlns:of:1.2"')


def _notice():
    try:
        from .rail_demo import NOTICE
        return NOTICE
    except Exception:  # noqa: BLE001 - the words are the same either way
        return 'Invented demonstration data. Nothing here was measured.'


def _package(mimetype, content):
    """An OpenDocument package, the same bytes every time (no clock in it)."""
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    styles = xml + '<office:document-styles %s office:version="1.3"><office:styles/></office:document-styles>' % _NS
    meta = xml + ('<office:document-meta %s office:version="1.3"><office:meta><meta:generator>Graphite (an invented example)'
                  '</meta:generator></office:meta></office:document-meta>' % _NS)
    manifest = xml + ('<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.3">'
                      '<manifest:file-entry manifest:full-path="/" manifest:version="1.3" manifest:media-type="%s"/>'
                      '<manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>'
                      '<manifest:file-entry manifest:full-path="styles.xml" manifest:media-type="text/xml"/>'
                      '<manifest:file-entry manifest:full-path="meta.xml" manifest:media-type="text/xml"/>'
                      '</manifest:manifest>' % mimetype)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        for name, data, how in (('mimetype', mimetype, zipfile.ZIP_STORED), ('content.xml', xml + content, zipfile.ZIP_DEFLATED),
                                ('styles.xml', styles, zipfile.ZIP_DEFLATED), ('meta.xml', meta, zipfile.ZIP_DEFLATED),
                                ('META-INF/manifest.xml', manifest, zipfile.ZIP_DEFLATED)):
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = how
            info.external_attr = 0o644 << 16
            archive.writestr(info, data.encode('utf-8'))
    return buffer.getvalue()


def _string_cell(text):
    return '<table:table-cell office:value-type="string"><text:p>%s</text:p></table:table-cell>' % escape(text)


def _number_cell(value):
    return '<table:table-cell office:value-type="float" office:value="%s"><text:p>%s</text:p></table:table-cell>' % (value, value)


def report_odt():
    """The invented 'Rail Demo summary report' (.odt): a heading, the notice, the settled power sentence, the startup
    sentence, and a table of the Rev B limits."""
    rows = (('Limit', 'Value', 'Unit'), ('Settled power limit', '4', 'W'), ('Startup duration limit', '40', 'ms'),
            ('Nominal voltage', '12', 'V'))
    table = ('<table:table table:name="Rev B limits"><table:table-column table:number-columns-repeated="3"/>'
             + ''.join('<table:table-row>%s</table:table-row>' % ''.join(_string_cell(c) for c in row) for row in rows)
             + '</table:table>')
    paragraphs = ('<text:h text:outline-level="1">Rail Demo summary report</text:h>'
                  '<text:p>%s</text:p>'
                  '<text:p>The 12 V rail was read on the bench at 25 C; the limits are those of Rev B, the current revision.</text:p>'
                  '<text:p>%s It is inside the Rev B limit of 4 W.</text:p>'
                  '<text:p>Startup takes 45 ms. Rev B allows 40 ms, so the startup question stays open.</text:p>'
                  '<text:p>The limits of Rev B:</text:p>%s'
                  '<text:p>Open: why startup takes longer than 40 ms.</text:p>') % (escape(_notice()), escape(POWER_SENTENCE), table)
    return _package(ODT_TYPE, '<office:document-content %s office:version="1.3"><office:body><office:text>%s</office:text>'
                              '</office:body></office:document-content>' % (_NS, paragraphs))


def sheet_ods():
    """The invented 'Rail Demo power sheet' (.ods): rail voltage (B2), settled current (B3, the cell to set) and the
    settled power worked from them (B4, a formula: =B2*B3/1000, 3 W)."""
    rows = [_string_cell('Parameter') + _string_cell('Value') + _string_cell('Unit') + _string_cell('Basis'),
            _string_cell('Rail voltage') + _number_cell('12') + _string_cell('V') + _string_cell('Bench readings'),
            _string_cell('Settled current') + _number_cell('250') + _string_cell('mA') + _string_cell('Bench readings'),
            _string_cell('Settled power') + '<table:table-cell table:formula="of:=[.B2]*[.B3]/1000" office:value-type="float" '
            'office:value="3"><text:p>3</text:p></table:table-cell>' + _string_cell('W') + _string_cell('Worked from B2 and B3'),
            _string_cell(_notice())]
    table = ('<table:table table:name="Power"><table:table-column table:number-columns-repeated="4"/>'
             + ''.join('<table:table-row>%s</table:table-row>' % r for r in rows) + '</table:table>')
    return _package(ODS_TYPE, '<office:document-content %s office:version="1.3"><office:body><office:spreadsheet>%s'
                              '</office:spreadsheet></office:body></office:document-content>' % (_NS, table))


def place_examples(kernel, folder='Rail Demo'):
    """Put the invented report and sheet in Files/<folder>/ (nothing already there is overwritten). Returns
    {'report': its path in Files, 'sheet': its path in Files, 'written': [the ones written now]}."""
    from . import files_service
    written = []
    out = {}
    for key, name, make in (('report', REPORT_NAME, report_odt), ('sheet', SHEET_NAME, sheet_ods)):
        rel = '%s/%s' % (folder.strip('/'), name) if folder.strip('/') else name
        target = files_service.resolve(kernel, rel, must_exist=False)
        if not target.exists():
            target.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
            temporary = target.with_name('.' + target.name + '.writing')
            temporary.write_bytes(make())
            os.replace(temporary, target)
            written.append(rel)
        out[key] = rel
    out['written'] = written
    return out


# ---------------------------------------------------------------- her LibreOffice, owned

def _area(kernel):
    area = Path(kernel.state) / 'office-bridge'
    area.mkdir(mode=0o700, parents=True, exist_ok=True)
    return area


def _profile(folder):
    """Her LibreOffice's profile: macros never run, no recovery or autosave, her name on the lock files it writes. Written
    each time, so the settings are always these and no list of recent documents is kept."""
    user = folder / 'user'
    user.mkdir(mode=0o700, parents=True, exist_ok=True)
    items = (('/org.openoffice.Office.Common/Security/Scripting', 'MacroSecurityLevel', '<value>3</value>'),
             ('/org.openoffice.Office.Common/Security/Scripting', 'SecureURL', '<value/>'),
             ('/org.openoffice.Office.Common/Security/Scripting', 'DisableMacrosExecution', '<value>true</value>'),
             ('/org.openoffice.UserProfile/Data', 'givenname', '<value>%s</value>' % HER_NAME[0]),
             ('/org.openoffice.UserProfile/Data', 'sn', '<value>%s</value>' % HER_NAME[1]),
             ('/org.openoffice.Office.Recovery/AutoSave', 'Enabled', '<value>false</value>'),
             ('/org.openoffice.Office.Recovery/RecoveryInfo', 'Enabled', '<value>false</value>'),
             ('/org.openoffice.Office.Common/Save/Document', 'WarnAlienFormat', '<value>false</value>'),
             ('/org.openoffice.Office.Common/Save/Document', 'CreateBackup', '<value>false</value>'))
    body = ''.join('<item oor:path="%s"><prop oor:name="%s" oor:op="fuse">%s</prop></item>' % item for item in items)
    (user / 'registrymodifications.xcu').write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<oor:items xmlns:oor="http://openoffice.org/2001/registry" '
        'xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">%s</oor:items>\n' % body,
        encoding='utf-8')
    with contextlib.suppress(OSError):
        (folder / '.lock').unlink()          # a profile lock left by a session that was ended (the sweep ended it)
    return folder.resolve().as_uri()


@contextlib.contextmanager
def _one_at_a_time(area):
    fd = os.open(area / 'bridge.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    try:
        until = time.monotonic() + LOCK_SECONDS
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() > until:
                    raise BridgeError('LIBREOFFICE_BUSY: her LibreOffice is busy with another document; ask again in a moment') from None
                time.sleep(0.1)
        yield
    finally:
        os.close(fd)


def _group_alive(pgid):
    """Whether a process of the group still runs (a zombie waiting to be reaped by someone else does not count)."""
    proc = Path('/proc')
    if proc.is_dir():
        for entry in proc.iterdir():
            if not entry.name.isdigit():
                continue
            try:
                stat = (entry / 'stat').read_text(errors='replace')
            except OSError:
                continue
            fields = stat[stat.rfind(')') + 2:].split()
            if len(fields) > 2 and fields[2] == str(pgid) and fields[0] not in ('Z', 'X'):
                return True
        return False
    try:
        os.killpg(pgid, 0)
    except (ProcessLookupError, PermissionError):
        return False
    return True


def _end_group(pgid, process=None, wait=5):
    """End a process group: TERM, then KILL, each only while something of it still runs; reap the leader."""
    if process is not None:
        with contextlib.suppress(subprocess.TimeoutExpired, OSError):
            process.wait(timeout=0.05)
    for sig in (signal.SIGTERM, signal.SIGKILL):
        if not _group_alive(pgid):
            break
        try:
            os.killpg(pgid, sig)
        except (ProcessLookupError, PermissionError):
            break
        until = time.monotonic() + wait
        while time.monotonic() < until:
            if process is not None:
                with contextlib.suppress(subprocess.TimeoutExpired, OSError):
                    process.wait(timeout=0.05)
            if not _group_alive(pgid):
                break
            time.sleep(0.05)
    if process is not None:
        with contextlib.suppress(subprocess.TimeoutExpired, OSError):
            process.wait(timeout=2)


def _sweep(area):
    """End and clear what a session of hers left behind (a crash): its LibreOffice's process group, if it is still the same
    process, and its folder. Called with the bridge's lock held, so no session of hers is running."""
    from .operation_stop import process_identity, UNKNOWN
    ended = 0
    for folder in area.iterdir():
        if not folder.is_dir() or not re.fullmatch(r'[0-9a-f]{32}', folder.name):
            continue
        try:
            owner = json.loads((folder / 'owner.json').read_text(encoding='utf-8'))
        except (OSError, ValueError):
            owner = {}
        pid = owner.get('pid')
        start = owner.get('start')
        if isinstance(pid, int) and start not in (None, UNKNOWN) and process_identity(pid) == start:
            _end_group(pid)
            ended += 1
        shutil.rmtree(folder, ignore_errors=True)
    return ended


def lock_of(path):
    """A document's LibreOffice lock file (.~lock.<name>#), or None: {'path', 'hers', 'text'}."""
    lock = Path(path).with_name('.~lock.' + Path(path).name + '#')
    if not lock.exists():
        return None
    try:
        text = lock.read_text(encoding='utf-8', errors='replace')[:4000]
    except OSError:
        text = ''
    return {'path': lock, 'text': text, 'hers': ('office-bridge' in text and ' '.join(HER_NAME) in text)}


def owner_has_it_open(path):
    """'' or why the document must not be edited now: the owner (or anyone but her) has it open in LibreOffice."""
    lock = lock_of(path)
    if lock is None or lock['hers']:
        return ''
    return ('%s is open in LibreOffice (its lock file is there): I never edit a document behind your back. Save and close it '
            'there, then ask again.' % Path(path).name)


def _clear_her_lock(path):
    lock = lock_of(path)
    if lock is not None and lock['hers']:
        with contextlib.suppress(OSError):
            lock['path'].unlink()
        return True
    return False


class Session:
    """Her LibreOffice for one piece of work: headless, its own profile, a private pipe, its own process group; the helper
    beside it. `with Session(kernel) as office: office.call('open', {...})`. Ended in every case when the block ends."""

    def __init__(self, kernel, info=None):
        self.kernel = kernel
        self.info = info or probe()
        self.area = None
        self.folder = None
        self.office = None
        self.helper = None
        self.product = ''
        self.n = 0
        self.buffer = b''
        self._lock = None

    def __enter__(self):
        try:
            self.start()
        except BaseException:
            self.close()
            raise
        return self

    def __exit__(self, *exc):
        self.close()
        return False

    def start(self):
        if not self.info.get('available'):
            raise Unavailable(self.info.get('words') or NOT_HERE)
        from .operation_stop import process_identity
        from . import office_runtime
        self.area = _area(self.kernel)
        lock = _one_at_a_time(self.area)
        lock.__enter__()
        self._lock = lock
        _sweep(self.area)
        ident = uuid.uuid4().hex
        self.folder = self.area / ident
        self.folder.mkdir(mode=0o700)
        uri = _profile(self.area / 'profile')
        pipe = 'graphite-k5-' + ident
        env = {**os.environ, 'LANG': 'C.UTF-8', 'SAL_USE_VCLPLUGIN': 'svp',
               'FONTCONFIG_FILE': str(office_runtime.font_config(self.area / 'fonts'))}
        for name in ('DISPLAY', 'WAYLAND_DISPLAY', 'SESSION_MANAGER'):
            env.pop(name, None)              # headless: never a window on the owner's screen
        argv = [self.info['soffice'], '-env:UserInstallation=' + uri, '--headless', '--invisible', '--nologo', '--nodefault',
                '--norestore', '--nofirststartwizard', '--accept=pipe,name=%s;urp;StarOffice.ComponentContext' % pipe]
        with open(self.folder / 'office.log', 'wb') as log:
            self.office = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=log, stderr=log, env=env, cwd=str(self.folder),
                                           start_new_session=True, close_fds=True)
        (self.folder / 'owner.json').write_text(json.dumps({'pid': self.office.pid, 'start': process_identity(self.office.pid),
                                                            'pipe': pipe, 'at_ns': time.time_ns()}), encoding='utf-8')
        helper_env = {**os.environ, 'LANG': 'C.UTF-8'}
        for name in ('DISPLAY', 'WAYLAND_DISPLAY'):
            helper_env.pop(name, None)
        with open(self.folder / 'helper.log', 'wb') as log:
            self.helper = subprocess.Popen([self.info['python'], '-I', '-B', str(HELPER)], stdin=subprocess.PIPE,
                                           stdout=subprocess.PIPE, stderr=log, env=helper_env, cwd=str(self.folder), close_fds=True)
        hello = self._answer(30)
        if not hello.get('ok'):
            raise Unavailable('%s: %s' % (NOT_HERE, hello.get('error') or 'its helper did not start'))
        until = time.monotonic() + START_SECONDS
        while True:
            if self.office.poll() is not None and self.office.returncode not in (0, None):
                raise BridgeError('her LibreOffice ended as it started (%s)' % self._tail('office.log'))
            try:
                got = self.call('connect', {'pipe': pipe, 'timeout_ms': 3000}, timeout=30)
                break
            except BridgeError:
                if time.monotonic() > until:
                    raise BridgeError('her LibreOffice did not answer on its private pipe within %d s (%s)' % (
                        START_SECONDS, self._tail('office.log'))) from None
        self.product = got.get('product') or 'LibreOffice'
        return self

    def _tail(self, name):
        try:
            return (self.folder / name).read_text(encoding='utf-8', errors='replace').strip()[-400:] or 'nothing said'
        except OSError:
            return 'nothing said'

    def _answer(self, timeout):
        fd = self.helper.stdout.fileno()
        until = time.monotonic() + timeout
        while b'\n' not in self.buffer:
            left = until - time.monotonic()
            if left <= 0:
                raise BridgeError('LibreOffice did not answer within %d s' % timeout)
            ready, _, _ = select.select([fd], [], [], left)
            if ready:
                chunk = os.read(fd, 1 << 16)
                if not chunk:
                    raise BridgeError("the bridge's helper ended (%s)" % self._tail('helper.log'))
                self.buffer += chunk
        line, _, self.buffer = self.buffer.partition(b'\n')
        try:
            return json.loads(line.decode('utf-8'))
        except ValueError:
            raise BridgeError("the bridge's helper said something that is not an answer") from None

    def call(self, op, args=None, timeout=CALL_SECONDS):
        if self.helper is None or self.helper.poll() is not None:
            raise BridgeError("the bridge's helper is not running")
        self.n += 1
        self.helper.stdin.write((json.dumps({'id': self.n, 'op': op, 'args': args or {}}, ensure_ascii=False) + '\n').encode('utf-8'))
        self.helper.stdin.flush()
        answer = self._answer(timeout)
        if answer.get('id') != self.n:
            raise BridgeError("the bridge's helper answered out of turn")
        if not answer.get('ok'):
            raise BridgeError('LibreOffice (%s): %s' % (op, str(answer.get('error'))[:600]))
        return answer.get('result') or {}

    def close(self):
        """End her LibreOffice and the helper, in every case; clear the session's folder; free the bridge."""
        try:
            if self.helper is not None:
                if self.helper.poll() is None:
                    with contextlib.suppress(Exception):
                        self.call('terminate', {}, timeout=20)
                    with contextlib.suppress(OSError):
                        self.helper.stdin.close()
                    try:
                        self.helper.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        self.helper.kill()
                        with contextlib.suppress(subprocess.TimeoutExpired):
                            self.helper.wait(timeout=5)
                with contextlib.suppress(OSError):
                    self.helper.stdout.close()
            if self.office is not None:
                with contextlib.suppress(subprocess.TimeoutExpired):
                    self.office.wait(timeout=15)
                _end_group(self.office.pid, self.office)      # what is left of its group (soffice.bin) ends too
            if self.folder is not None:
                shutil.rmtree(self.folder, ignore_errors=True)
        finally:
            self.helper = self.office = None
            if self._lock is not None:
                lock, self._lock = self._lock, None
                lock.__exit__(None, None, None)


# ---------------------------------------------------------------- the operations

def _file(kernel, rel, edit=False):
    from . import files_service
    path = files_service.resolve(kernel, rel)
    if not path.is_file():
        raise ValueError('LIBREOFFICE_NOT_A_FILE: %s is not a file in Files' % str(rel)[:200])
    suffix = path.suffix.lower()
    if edit and suffix not in EDITS:
        raise ValueError('LIBREOFFICE_FORMAT: she edits OpenDocument files (.odt, .ods) through LibreOffice; %s is read only' % path.name)
    if suffix not in READS:
        raise ValueError('LIBREOFFICE_FORMAT: %s is not a document LibreOffice opens for her (%s)' % (path.name, ', '.join(READS)))
    if path.stat().st_size > BIGGEST:
        raise ValueError('LIBREOFFICE_TOO_LARGE: %s is larger than she opens' % path.name)
    return path, files_service.rel_of(kernel, path)


def _check_sha(args, path, now):
    expected = args.get('expected_sha256')
    if expected is not None and not SHA_RE.match(str(expected)):
        raise ValueError('LIBREOFFICE_REVISION: a revision is named by its SHA-256 (64 hex digits)')
    if expected and expected != now:
        raise ValueError('LIBREOFFICE_CHANGED: %s is not at the revision the plan read (it was saved since); read it again' % path.name)


def _held(kernel):
    from . import work_trail
    if work_trail.execution_held(kernel):
        raise ValueError('HELD: all of her work is held (HALT or Stop all): nothing was changed')


def _via(product):
    return '%s through its own interface (UNO): a headless LibreOffice of her own, its own profile and a private pipe' % product


def status(kernel, args, principal):
    found = probe(fresh=True)
    return {'schema': SCHEMA, **found, 'operations': describe(found)}


def read_document(kernel, args, principal):
    """libreoffice.read: the document's paragraphs and tables (Writer) or a sheet's cells (Calc), at the revision on disk."""
    path, rel = _file(kernel, args['path'])
    if args.get('range') and not RANGE_RE.match(args['range']):
        raise ValueError('LIBREOFFICE_RANGE: a range is a cell (B3) or two (A1:D20)')
    before, size = sha256_of(path)
    _check_sha(args, path, before)
    info = probe()
    out = {'schema': SCHEMA, 'path': rel, 'object': 'files:' + rel, 'name': path.name, 'revision': before, 'size': size}
    if info['available']:
        with Session(kernel, info) as office:
            doc = office.call('open', {'url': path.as_uri(), 'read_only': True}, timeout=SAVE_SECONDS)
            if doc['kind'] == 'writer':
                got = office.call('blocks', {'doc': doc['doc']}, timeout=SAVE_SECONDS)
                out.update(kind='text', blocks=got['blocks'], paragraphs=[b['text'] for b in got['blocks'] if b['kind'] == 'paragraph'])
            elif doc['kind'] == 'calc':
                got = office.call('cells', {'doc': doc['doc'], 'sheet': args.get('sheet'), 'range': args.get('range')}, timeout=SAVE_SECONDS)
                out.update(kind='spreadsheet', sheets=got['sheets'], sheet=got['sheet'], cells=got['cells'])
            else:
                raise ValueError('LIBREOFFICE_KIND: %s is neither a Writer document nor a Calc spreadsheet' % path.name)
            office.call('close', {'doc': doc['doc']})
            out.update(via=_via(office.product), interface={'available': True, 'product': office.product})
    else:
        if path.suffix.lower() not in DIRECT:
            raise Unavailable('%s, and %s is not an OpenDocument file Graphite reads by itself' % (info['words'].rstrip('.'), path.name))
        document = read_odf(path)
        if document['kind'] == 'text':
            out.update(kind='text', blocks=document['blocks'], paragraphs=[b['text'] for b in document['blocks'] if b['kind'] == 'paragraph'])
        else:
            sheet = _sheet_of(document, args.get('sheet'))
            # the same words for a cell's kind as LibreOffice's own (value, text, formula); the formula as the file has it
            out.update(kind='spreadsheet', sheets=[s['name'] for s in document['sheets']], sheet=sheet['name'],
                       cells={k: {'type': 'formula' if v['formula'] else 'value' if v['type'] in ('float', 'percentage', 'currency') else 'text',
                                  'formula': v['formula'], 'text': v['text'], 'value': v['value']}
                              for k, v in sheet['cells'].items()})
        out.update(via='the file read directly (its content.xml), not through LibreOffice: ' + info['words'],
                   interface={'available': False, 'reason': info['reason']})
    after, _ = sha256_of(path)
    if after != before:
        raise ValueError('LIBREOFFICE_CHANGED_WHILE_READ: %s was saved while it was read; read it again' % path.name)
    open_elsewhere = owner_has_it_open(path)
    what = ('%d paragraphs and %d tables' % (len(out.get('paragraphs') or []), sum(1 for b in out.get('blocks') or [] if b['kind'] == 'table'))
            if out['kind'] == 'text' else '%d cells of the sheet %s' % (len(out.get('cells') or {}), out.get('sheet')))
    out.update(complete=True, how='observed', open_in_libreoffice=bool(open_elsewhere),
               words='Read %s at revision %s…: %s.%s' % (path.name, before[:12], what,
                                                       ' It is open in LibreOffice: this is the file as last saved.' if open_elsewhere else ''))
    return out


def find_passage(kernel, args, principal):
    """libreoffice.find: where a passage is in the document (its paragraphs, or its cells)."""
    path, rel = _file(kernel, args['path'])
    text = args['text']
    before, _ = sha256_of(path)
    info = probe()
    if info['available']:
        with Session(kernel, info) as office:
            doc = office.call('open', {'url': path.as_uri(), 'read_only': True}, timeout=SAVE_SECONDS)
            got = office.call('find', {'doc': doc['doc'], 'text': text}, timeout=SAVE_SECONDS)
            office.call('close', {'doc': doc['doc']})
            places, via = got['places'], _via(office.product)
    else:
        if path.suffix.lower() not in DIRECT:
            raise Unavailable(info['words'])
        document = read_odf(path)
        if document['kind'] == 'text':
            places = [{'paragraph': p, 'place': n} for n, p in enumerate(document['paragraphs'], 1) for _ in range(p.count(text))]
        else:
            places = [{'sheet': s['name'], 'cell': k, 'text': v['text']} for s in document['sheets'] for k, v in s['cells'].items()
                      if text in v['text']]
        via = 'the file read directly (its content.xml): ' + info['words']
    if sha256_of(path)[0] != before:
        raise ValueError('LIBREOFFICE_CHANGED_WHILE_READ: %s was saved while it was read; read it again' % path.name)
    return {'schema': SCHEMA, 'path': rel, 'object': 'files:' + rel, 'revision': before, 'text': text, 'count': len(places),
            'places': places, 'via': via, 'complete': True, 'how': 'observed',
            'words': '"%s" is in %d place%s of %s.' % (text[:80], len(places), '' if len(places) == 1 else 's', path.name)}


def _passage_plan(path, find, replace, occurrences=None):
    document = read_odf(path)
    if document['kind'] != 'text':
        raise ValueError('LIBREOFFICE_KIND: a passage is replaced in a Writer document (.odt)')
    count = sum(p.count(find) for p in document['paragraphs'])
    expected = [p.replace(find, replace) for p in document['paragraphs']]
    changed = [{'place': n, 'before': b, 'after': a} for n, (b, a) in enumerate(zip(document['paragraphs'], expected), 1) if b != a]
    return document, count, expected, changed


def prepare(kernel, args, principal):
    """libreoffice.prepare: the change as prepared text, nothing written; what K4 offers when LibreOffice is not here."""
    path, rel = _file(kernel, args['path'], edit=True)
    sha, _ = sha256_of(path)
    info = probe()
    out = {'schema': SCHEMA, 'prepared': True, 'applied': False, 'path': rel, 'object': 'files:' + rel, 'revision': sha,
           'interface': {'available': bool(info['available']), 'reason': info['reason']}}
    tail = (' %s, so the change is yours to make.' % info['words'].rstrip('.')) if not info['available'] else \
        ' LibreOffice is here: approve it and she makes it through LibreOffice, then reads the saved file back.'
    if args.get('cell'):
        if 'value' not in args or not CELL_RE.match(args['cell']):
            raise ValueError('LIBREOFFICE_PREPARE: a cell change names the cell (B3) and its value')
        document = read_odf(path)
        if document['kind'] != 'spreadsheet':
            raise ValueError('LIBREOFFICE_KIND: a cell is set in a Calc spreadsheet (.ods)')
        sheet = _sheet_of(document, args.get('sheet'))
        was = sheet['cells'].get(args['cell'])
        out.update(kind='cell', sheet=sheet['name'], cell=args['cell'], value=args['value'], was=was,
                   words='Prepared, not applied: in %s, %s on the sheet %s would hold %s (it holds %s now).%s' % (
                       path.name, args['cell'], sheet['name'], args['value'], (was or {}).get('text') or 'nothing', tail))
        return out
    if 'find' not in args or 'replace' not in args:
        raise ValueError('LIBREOFFICE_PREPARE: give the passage and its new words (find, replace), or a cell and its value')
    _, count, expected, changed = _passage_plan(path, args['find'], args['replace'])
    wanted = int(args.get('occurrences') or 1)
    out.update(kind='passage', find=args['find'], replace=args['replace'], count=count, changed=changed,
               text='\n'.join(c['after'] for c in changed))
    if count != wanted:
        out['words'] = 'Prepared, not applied: "%s" is in %d places of %s, not %d; say which.' % (args['find'][:80], count, path.name, wanted)
    else:
        out['words'] = 'Prepared, not applied: in %s, %s would read "%s".%s' % (
            path.name, 'the paragraph' if len(changed) == 1 else '%d paragraphs' % len(changed), changed[0]['after'][:300] if changed else '', tail)
    return out


def _record(kernel, rel, after, before, principal):
    from . import depths
    try:
        return depths.record(kernel, {'path': rel, 'expected_sha256': after, 'previous_sha256': before, 'how': 'full program',
                                      'program': PROGRAM}, principal)
    except Exception as exc:  # noqa: BLE001 - the change is on disk either way: it is said, not hidden
        return {'recorded': False, 'revision': None, 'why': str(exc)[:300]}


def _save(kernel, office, doc, path):
    """The last look before the effect (HALT), the version before kept, the save with a suspend held off."""
    from . import files_service
    from .session_power import sleep_held
    _held(kernel)
    kept = files_service.keep_version(kernel, path)
    with sleep_held('Kasandra is saving “%s” through LibreOffice' % path.name[:80]):
        office.call('store', {'doc': doc}, timeout=SAVE_SECONDS)
    office.call('close', {'doc': doc})
    return kept


def replace_passage(kernel, args, principal):
    """libreoffice.replace: a passage of a Writer document replaced where it is, saved, read back, its revision recorded."""
    from . import files_service
    path, rel = _file(kernel, args['path'], edit=True)
    if path.suffix.lower() != '.odt':
        raise ValueError('LIBREOFFICE_KIND: a passage is replaced in a Writer document (.odt)')
    files_service.may_change(kernel, path, principal)
    find, new = args['find'], args['replace']
    wanted = int(args.get('occurrences') or 1)
    if find == new:
        raise ValueError('LIBREOFFICE_NOTHING: the new words are the old ones')
    before_sha, _ = sha256_of(path)
    _check_sha(args, path, before_sha)
    _, count, expected, changed = _passage_plan(path, find, new)
    if count != wanted:
        raise ValueError('LIBREOFFICE_PASSAGE: "%s" is in %d places of %s, not %d; nothing was changed' % (find[:80], count, path.name, wanted))
    info = probe()
    if not info['available']:
        raise Unavailable('%s. Nothing was changed; the change can be offered as prepared text.' % info['words'].rstrip('.'))
    why = owner_has_it_open(path)
    if why:
        raise ValueError('LIBREOFFICE_OPEN: ' + why)
    _held(kernel)
    with Session(kernel, info) as office:
        cleared = _clear_her_lock(path)
        why = owner_has_it_open(path)
        if why:
            raise ValueError('LIBREOFFICE_OPEN: ' + why)
        doc = office.call('open', {'url': path.as_uri(), 'read_only': False}, timeout=SAVE_SECONDS)
        if doc['kind'] != 'writer':
            raise ValueError('LIBREOFFICE_KIND: LibreOffice did not open %s as a Writer document' % path.name)
        if sha256_of(path)[0] != before_sha:
            raise ValueError('LIBREOFFICE_CHANGED: %s was saved by another program as she opened it; nothing was changed' % path.name)
        done = office.call('replace', {'doc': doc['doc'], 'find': find, 'replace': new, 'expect': wanted}, timeout=SAVE_SECONDS)
        if done.get('replaced') != wanted or done.get('found') != count:
            raise ValueError('LIBREOFFICE_PASSAGE: LibreOffice finds "%s" in %d places, the file read directly in %d; nothing was saved'
                             % (find[:80], done.get('found', 0), count))
        kept = _save(kernel, office, doc['doc'], path)
        product = office.product
    after_sha, size = sha256_of(path)
    try:
        now = read_odf(path)['paragraphs']
    except ValueError as exc:
        now, unreadable = None, str(exc)
    else:
        unreadable = ''
    problems = []
    if after_sha == before_sha:
        problems.append('the file on disk is the same as before: the save did not change it')
    if now is None:
        problems.append('the saved file cannot be read back (%s)' % unreadable[:200])
    elif now != expected:
        if len(now) != len(expected):
            problems.append('the saved file has %d paragraphs, not %d' % (len(now), len(expected)))
        else:
            off = [n for n, (a, b) in enumerate(zip(now, expected), 1) if a != b]
            problems.append('paragraph %s of the saved file does not read as the change should leave it' % ', '.join(map(str, off[:5])))
    record = _record(kernel, rel, after_sha, before_sha, principal) if after_sha != before_sha else {'recorded': False, 'revision': None}
    verified = not problems
    shown = changed[0]['after'] if changed else new
    words = ('In %s, "%s" now reads "%s": the saved file, read back directly, says so; %s' % (
        path.name, find[:120], shown[:300], ('revision %d is recorded.' % record['revision']) if record.get('revision') else
        'its revision could not be recorded (%s).' % record.get('why', 'not recorded')) if verified else
        'Saved through LibreOffice, and not verified: %s.' % '; '.join(problems))
    return {'schema': SCHEMA, 'status': 'verified' if verified else 'not verified', 'operation': 'replace', 'path': rel,
            'object': 'files:' + rel, 'name': path.name, 'find': find, 'replace': new, 'occurrences': wanted, 'changed': changed,
            'previous': before_sha, 'digest': after_sha, 'size': size, 'revision': record.get('revision'),
            'recorded': bool(record.get('revision')), 'record': {k: record.get(k) for k in ('recorded', 'revision', 'words', 'why') if k in record},
            'kept_version': kept, 'cleared_her_lock': cleared, 'via': _via(product), 'problems': problems,
            'verified': ('the saved file, read back directly, holds the change; SHA-256 %s…' % after_sha[:16]) if verified else '',
            'words': words}


def set_cell(kernel, args, principal):
    """libreoffice.cell: a value cell of a Calc sheet set, saved, read back (formulas recalculated), its revision recorded."""
    from . import files_service
    path, rel = _file(kernel, args['path'], edit=True)
    if path.suffix.lower() != '.ods':
        raise ValueError('LIBREOFFICE_KIND: a cell is set in a Calc spreadsheet (.ods)')
    files_service.may_change(kernel, path, principal)
    cell, value = args['cell'], args['value']
    if not CELL_RE.match(cell):
        raise ValueError('LIBREOFFICE_CELL: a cell is named by its column and row (B3)')
    kind = args.get('kind') or ('number' if NUMBER_RE.match(value.strip()) else 'text')
    if kind == 'number' and not NUMBER_RE.match(value.strip()):
        raise ValueError('LIBREOFFICE_NUMBER: %s is not a plain number (digits, one point, a sign)' % value[:40])
    if kind == 'number':
        value = value.strip()
    before_sha, _ = sha256_of(path)
    _check_sha(args, path, before_sha)
    before = read_odf(path)
    if before['kind'] != 'spreadsheet':
        raise ValueError('LIBREOFFICE_KIND: a cell is set in a Calc spreadsheet (.ods)')
    sheet = _sheet_of(before, args.get('sheet'))
    was = sheet['cells'].get(cell)
    if was and was.get('formula'):
        raise ValueError('LIBREOFFICE_FORMULA: %s holds a formula (%s); she sets only a value cell' % (cell, was['formula'][:80]))
    info = probe()
    if not info['available']:
        raise Unavailable('%s. Nothing was changed; the change can be offered as prepared text.' % info['words'].rstrip('.'))
    why = owner_has_it_open(path)
    if why:
        raise ValueError('LIBREOFFICE_OPEN: ' + why)
    _held(kernel)
    with Session(kernel, info) as office:
        cleared = _clear_her_lock(path)
        why = owner_has_it_open(path)
        if why:
            raise ValueError('LIBREOFFICE_OPEN: ' + why)
        doc = office.call('open', {'url': path.as_uri(), 'read_only': False}, timeout=SAVE_SECONDS)
        if doc['kind'] != 'calc':
            raise ValueError('LIBREOFFICE_KIND: LibreOffice did not open %s as a Calc spreadsheet' % path.name)
        if sha256_of(path)[0] != before_sha:
            raise ValueError('LIBREOFFICE_CHANGED: %s was saved by another program as she opened it; nothing was changed' % path.name)
        done = office.call('set_cell', {'doc': doc['doc'], 'sheet': sheet['name'], 'cell': cell, 'value': value, 'kind': kind},
                           timeout=SAVE_SECONDS)
        if not done.get('set'):
            raise ValueError('LIBREOFFICE_CELL: %s was not set: %s; nothing was saved' % (cell, done.get('why', 'LibreOffice refused')))
        kept = _save(kernel, office, doc['doc'], path)
        product = office.product
    after_sha, size = sha256_of(path)
    problems = []
    recalculated = []
    try:
        after = read_odf(path)
        now_sheet = _sheet_of(after, sheet['name'])
    except ValueError as exc:
        after, now_sheet = None, None
        problems.append('the saved file cannot be read back (%s)' % str(exc)[:200])
    now = now_sheet['cells'].get(cell) if now_sheet else None
    if now_sheet is not None:
        if not _same_value(now, value, kind):
            problems.append('%s holds %s, not %s' % (cell, (now or {}).get('text') or 'nothing', value))
        old_sheets = {s['name']: s['cells'] for s in before['sheets']}
        new_sheets = {s['name']: s['cells'] for s in after['sheets']}
        if set(old_sheets) != set(new_sheets):
            problems.append('the sheets are not the ones there were')
        for name in sorted(set(old_sheets) & set(new_sheets)):
            a, b = old_sheets[name], new_sheets[name]
            for address in sorted(set(a) | set(b)):
                if name == sheet['name'] and address == cell:
                    continue
                old, new = a.get(address), b.get(address)
                if old == new:
                    continue
                if (old or {}).get('formula') or (new or {}).get('formula'):
                    if (old or {}).get('value') != (new or {}).get('value'):
                        recalculated.append({'sheet': name, 'cell': address, 'was': (old or {}).get('value'), 'now': (new or {}).get('value'),
                                             'formula': (new or old or {}).get('formula')})
                    continue
                problems.append('%s on %s changed too' % (address, name))
    if after_sha == before_sha:
        problems.append('the file on disk is the same as before: the save did not change it')
    record = _record(kernel, rel, after_sha, before_sha, principal) if after_sha != before_sha else {'recorded': False, 'revision': None}
    verified = not problems
    again = ('; worked again: ' + ', '.join('%s now %s' % (r['cell'], r['now']) for r in recalculated[:6])) if recalculated else ''
    words = ('In %s, %s on the sheet %s now holds %s (it held %s)%s: the saved file, read back directly, says so; %s' % (
        path.name, cell, sheet['name'], value, (was or {}).get('text') or 'nothing', again,
        ('revision %d is recorded.' % record['revision']) if record.get('revision') else
        'its revision could not be recorded (%s).' % record.get('why', 'not recorded')) if verified else
        'Saved through LibreOffice, and not verified: %s.' % '; '.join(problems[:6]))
    return {'schema': SCHEMA, 'status': 'verified' if verified else 'not verified', 'operation': 'cell', 'path': rel,
            'object': 'files:' + rel, 'name': path.name, 'sheet': sheet['name'], 'cell': cell, 'value': value, 'kind': kind,
            'was': was, 'now': now, 'recalculated': recalculated, 'previous': before_sha, 'digest': after_sha, 'size': size,
            'revision': record.get('revision'), 'recorded': bool(record.get('revision')),
            'record': {k: record.get(k) for k in ('recorded', 'revision', 'words', 'why') if k in record}, 'kept_version': kept,
            'cleared_her_lock': cleared, 'via': _via(product), 'problems': problems,
            'verified': ('the saved file, read back directly, holds %s in %s; SHA-256 %s…' % (value, cell, after_sha[:16])) if verified else '',
            'words': words}


def dispatch(kernel, op, args, principal):
    if op == 'libreoffice.status':
        return status(kernel, args, principal)
    if op == 'libreoffice.read':
        return read_document(kernel, args, principal)
    if op == 'libreoffice.find':
        return find_passage(kernel, args, principal)
    if op == 'libreoffice.prepare':
        return prepare(kernel, args, principal)
    if op == 'libreoffice.replace':
        return replace_passage(kernel, args, principal)
    if op == 'libreoffice.cell':
        return set_cell(kernel, args, principal)
    raise ValueError('Unknown LibreOffice operation')


# ---------------------------------------------------------------- the checks of her changes (assignments, K1; receipts, K2)

def _revision_n(kernel, rel, sha, principal):
    """The revision number recorded for these bytes; recorded now when the bytes on disk are new to the records."""
    from . import depths
    try:
        rows = depths.listing(kernel, {'path': rel}).get('revisions') or []
    except Exception:  # noqa: BLE001
        rows = []
    for row in reversed(rows):
        if row.get('digest') == sha:
            return row.get('n')
    if principal is None:
        return None
    return _record(kernel, rel, sha, '', principal).get('revision')


class _Change(_asg.Check):
    """A change she makes through LibreOffice: looked for before it is made again (resume), verified by reading the saved
    file back, and still there or not on a later look."""
    repeatable = True
    standin_ms = 15000

    def _ready(self, kernel, arguments, path):
        info = probe()
        if not info['available']:
            raise _asg.Blocked('%s; the change can be offered as prepared text instead' % info['words'].rstrip('.'))
        why = owner_has_it_open(path)
        if why:
            raise _asg.Blocked(why)
        sha, _ = sha256_of(path)
        expected = arguments.get('expected_sha256')
        if expected and expected != sha:
            raise _asg.Blocked('%s is not at the revision the plan read: it was saved since' % path.name)
        return sha

    def _observation(self, kernel, rel, sha, words, extra, principal=None):
        n = _revision_n(kernel, rel, sha, principal)
        return {'object': 'files:' + rel, 'revision': sha, 'by': 'sha256', 'revision_n': n, 'path': rel, **extra,
                'complete': True, 'how': 'observed', 'tool': 'office.edit',
                'words': '%s%s' % (words, (' Revision %d is on disk (SHA-256 %s…).' % (n, sha[:12])) if n else
                                   ' The new revision is on disk (SHA-256 %s…).' % sha[:12])}

    def verify(self, kernel, read, arguments, result, prepared, step):
        if isinstance(result, dict) and result.get('status') == 'not verified':
            raise _asg.NotVerified('; '.join(result.get('problems') or ['the saved file does not hold the change'])[:400])
        found = self.find(kernel, read, arguments, prepared)
        if not found:
            raise _asg.NotVerified('the saved file, read back, does not hold the change')
        if isinstance(result, dict) and result.get('digest') and result['digest'] != found['revision']:
            raise _asg.NotVerified('the document changed again after she saved it')
        return found

    def still(self, kernel, read, step):
        from . import files_service
        obs = step.get('observation') or {}
        try:
            path = files_service.resolve(kernel, obs.get('path') or '')
        except ValueError:
            return 'the document is no longer there'
        if not path.is_file():
            return 'the document is no longer there'
        return '' if sha256_of(path)[0] == obs.get('revision') else 'the document has changed since'


class PassageCheck(_Change):
    """libreoffice.replace: done when the saved document, read back directly, reads as the change leaves it."""
    kind = 'document'
    effect = 'a passage of a document replaced through LibreOffice'
    how = 'the saved document, read back directly, holds the new words where the old ones were; its new revision is recorded'
    expected = 'the document saved with the new words, read back, at its new revision'

    def prepare(self, kernel, read, arguments):
        path, rel = _file(kernel, arguments['path'], edit=True)
        sha = self._ready(kernel, arguments, path)
        _, count, expected, changed = _passage_plan(path, arguments['find'], arguments['replace'])
        wanted = int(arguments.get('occurrences') or 1)
        if count != wanted:
            raise _asg.Blocked('"%s" is in %d places of %s, not %d' % (arguments['find'][:80], count, path.name, wanted))
        return {'path': rel, 'before': sha, 'expected': digest(expected), 'places': [c['place'] for c in changed], 'at': time.time()}

    def find(self, kernel, read, arguments, prepared):
        from . import files_service
        path = files_service.resolve(kernel, prepared['path'], must_exist=False)
        if not path.is_file():
            return None
        sha, _ = sha256_of(path)
        if sha == prepared['before']:
            return None
        try:
            now = read_odf(path)['paragraphs']
        except ValueError:
            return None
        if digest(now) != prepared['expected']:
            return None
        places = prepared.get('places') or []
        shown = now[places[0] - 1] if places and places[0] <= len(now) else arguments.get('replace', '')
        from .engineering_kernel import operator
        return self._observation(kernel, prepared['path'], sha, 'The saved document, read back directly, says "%s".' % shown[:200],
                                 {'place': {'path': prepared['path'], 'paragraphs': places}}, operator())


class CellCheck(_Change):
    """libreoffice.cell: done when the saved sheet, read back directly, holds the value in that cell."""
    kind = 'cell'
    effect = 'a cell of a spreadsheet set through LibreOffice'
    how = 'the saved sheet, read back directly, holds the value in that cell; its new revision is recorded'
    expected = 'the sheet saved with the value in its cell, read back, at its new revision'

    @staticmethod
    def _kind(arguments):
        value = arguments['value']
        return arguments.get('kind') or ('number' if NUMBER_RE.match(value.strip()) else 'text')

    def prepare(self, kernel, read, arguments):
        path, rel = _file(kernel, arguments['path'], edit=True)
        sha = self._ready(kernel, arguments, path)
        document = read_odf(path)
        if document['kind'] != 'spreadsheet':
            raise _asg.Blocked('%s is not a spreadsheet' % path.name)
        try:
            sheet = _sheet_of(document, arguments.get('sheet'))
        except ValueError as exc:
            raise _asg.Blocked(str(exc)) from None
        was = sheet['cells'].get(arguments['cell'])
        if was and was.get('formula'):
            raise _asg.Blocked('%s holds a formula; she sets only a value cell' % arguments['cell'])
        return {'path': rel, 'before': sha, 'sheet': sheet['name'], 'cell': arguments['cell'], 'value': arguments['value'].strip()
                if self._kind(arguments) == 'number' else arguments['value'], 'kind': self._kind(arguments),
                'was': (was or {}).get('text'), 'at': time.time()}

    def find(self, kernel, read, arguments, prepared):
        from . import files_service
        path = files_service.resolve(kernel, prepared['path'], must_exist=False)
        if not path.is_file():
            return None
        sha, _ = sha256_of(path)
        if sha == prepared['before']:
            return None
        try:
            sheet = _sheet_of(read_odf(path), prepared['sheet'])
        except ValueError:
            return None
        now = sheet['cells'].get(prepared['cell'])
        if not _same_value(now, prepared['value'], prepared['kind']):
            return None
        from .engineering_kernel import operator
        return self._observation(kernel, prepared['path'], sha, 'The saved sheet, read back directly, holds %s in %s.' % (
            prepared['value'], prepared['cell']), {'place': {'path': prepared['path'], 'sheet': prepared['sheet'], 'cell': prepared['cell']},
                                                    'value': (now or {}).get('value')}, operator())


CHECKS = {'libreoffice.replace': PassageCheck(), 'libreoffice.cell': CellCheck()}


# ---------------------------------------------------------------- what the bridge offers, for the tool registry (K2)

_CHANGE_FROM = ('OWNER_WORDS', 'RECORD', 'SOURCE', 'DEDUCTION', 'STEP')
_READ_FROM = _CHANGE_FROM + ('MODEL_PICK',)


def describe(found=None):
    """The bridge's operations as the tool registry lists them: key, words, inputs (and where each may come from),
    preconditions, effects, undo class, the grant each needs, how its effect is verified, and whether it can be used here."""
    found = found or probe()
    here = {'available': bool(found['available']), 'why': '' if found['available'] else found['words']}
    path = {'name': 'path', 'words': 'the document, in Files', 'from': _READ_FROM}
    no = {'class': 'read', 'words': 'it only reads: there is nothing to undo'}
    change = {'class': 'change', 'words': 'the version before is kept in Files (.versions): Revert puts it back (yours to press)'}
    rows = [
        {'key': 'libreoffice.status', 'scope': 'read', 'words': "Whether LibreOffice's interface is here, and why not.", 'inputs': [],
         'preconditions': [], 'effects': 'nothing: a look', 'undo': no, 'grant': 'none: reading needs no grant',
         'verification': 'LibreOffice and a Python with its uno module, looked for now'},
        {'key': 'libreoffice.read', 'scope': 'read', 'words': 'Read a Writer document (its paragraphs and tables) or a Calc sheet '
         "(its cells) through LibreOffice's own interface.", 'inputs': [path, {'name': 'sheet', 'words': 'which sheet', 'from': _READ_FROM},
                                                                    {'name': 'range', 'words': 'which cells (A1:D20)', 'from': _READ_FROM}],
         'preconditions': ['the document is in Files', "LibreOffice's interface is here (else an OpenDocument file is read directly)"],
         'effects': 'nothing: a read', 'undo': no, 'grant': 'none: reading needs no grant',
         'verification': 'its digest on disk is the same before and after the read; the revision read is named'},
        {'key': 'libreoffice.find', 'scope': 'read', 'words': 'Find where a passage is in a document.',
         'inputs': [path, {'name': 'text', 'words': 'the passage', 'from': _READ_FROM}], 'preconditions': ['the document is in Files'],
         'effects': 'nothing: a read', 'undo': no, 'grant': 'none: reading needs no grant',
         'verification': 'its digest on disk is the same before and after the read'},
        {'key': 'libreoffice.prepare', 'scope': 'read', 'words': 'Prepare a change as text (a passage and its new words, or a cell '
         'and its value) without making it: what is offered when LibreOffice is not here.',
         'inputs': [path, {'name': 'find', 'words': 'the passage', 'from': _CHANGE_FROM}, {'name': 'replace', 'words': 'its new words', 'from': _CHANGE_FROM},
                    {'name': 'cell', 'words': 'or the cell', 'from': _CHANGE_FROM}, {'name': 'value', 'words': 'and its value', 'from': _CHANGE_FROM}],
         'preconditions': ['the document is an OpenDocument file in Files'], 'effects': 'nothing: the change is prepared, not made',
         'undo': no, 'grant': 'none: nothing is changed', 'verification': 'the file read directly; the revision it was prepared on is named'},
        {'key': 'libreoffice.replace', 'scope': 'approve', 'words': 'Replace a passage of a Writer document through LibreOffice, save '
         'it, and read the saved file back.', 'inputs': [path, {'name': 'find', 'words': 'the passage, as the document has it', 'from': _CHANGE_FROM},
                                                         {'name': 'replace', 'words': 'its new words', 'from': _CHANGE_FROM},
                                                         {'name': 'expected_sha256', 'words': 'the revision the plan read', 'from': _CHANGE_FROM}],
         'preconditions': ["LibreOffice's interface is here", 'the document is an .odt in Files, at the revision the plan read',
                           'the passage is in exactly the places named (one, unless said)', 'it is not open in LibreOffice elsewhere',
                           'her work is not held (HALT)'],
         'effects': 'a new revision of the document', 'undo': change,
         'grant': 'change a passage of the document (the records mark it for your approval: authorised by its own name)',
         'verification': 'the saved file, read back directly, reads as the change leaves it, every other paragraph as it was; its new '
                         'revision is recorded (revisions.record)'},
        {'key': 'libreoffice.cell', 'scope': 'approve', 'words': 'Set a value cell of a Calc sheet through LibreOffice, save it, and '
         'read the saved file back (formulas recalculated).',
         'inputs': [path, {'name': 'cell', 'words': 'the cell (B3)', 'from': _CHANGE_FROM}, {'name': 'value', 'words': 'its value', 'from': _CHANGE_FROM},
                    {'name': 'sheet', 'words': 'which sheet', 'from': _CHANGE_FROM},
                    {'name': 'expected_sha256', 'words': 'the revision the plan read', 'from': _CHANGE_FROM}],
         'preconditions': ["LibreOffice's interface is here", 'the sheet is an .ods in Files, at the revision the plan read',
                           'the cell holds a value, not a formula', 'it is not open in LibreOffice elsewhere', 'her work is not held (HALT)'],
         'effects': 'a new revision of the spreadsheet; formulas that read the cell are worked again', 'undo': change,
         'grant': 'set a cell of the spreadsheet (the records mark it for your approval: authorised by its own name)',
         'verification': 'the saved file, read back directly, holds the value in that cell (the same number exactly), every other '
                         'value cell as it was; its new revision is recorded (revisions.record)'},
    ]
    for row in rows:
        row.update(here if row['key'] != 'libreoffice.status' else {'available': True, 'why': ''})
    return rows


# ---------------------------------------------------------------- K4's step: a checked value put in its sentence

def offer_update(kernel, principal, path, old, new, basis=None, key='report', title=None):
    """The step that puts `new` in place of `old` in its one sentence of a Writer document, through LibreOffice
    (libreoffice.replace, the whole sentence as the passage, at the revision read now); or, when LibreOffice's interface is
    not here (or the document is open elsewhere), that change as prepared text. `basis`: where the new words come from (an
    origin: {'kind': 'RECORD', 'id', 'rev'} of the checked value, or a DEDUCTION). Returns {'step', 'available', 'why',
    'prepared', 'sentence', 'revised'}; 'step' is None when the change is only prepared."""
    target, rel = _file(kernel, path, edit=True)
    sha, _ = sha256_of(target)
    document = read_odf(target)
    if document['kind'] != 'text':
        raise ValueError('LIBREOFFICE_KIND: a sentence is updated in a Writer document (.odt)')
    found = [s for p in document['paragraphs'] for s in sentences(p) if old in s]
    if len(found) != 1:
        raise ValueError('LIBREOFFICE_PASSAGE: "%s" is in %d sentences of %s; say which' % (old[:80], len(found), target.name))
    sentence = found[0]
    revised = sentence.replace(old, new)
    occurrences = sum(p.count(sentence) for p in document['paragraphs'])
    read_here = {'kind': 'RECORD', 'id': 'files:' + rel, 'rev': sha}
    step = {'key': key, 'title': (title or 'Update %s: "%s"' % (target.name, revised))[:200], 'operation': 'libreoffice.replace',
            'arguments': {'path': rel, 'find': sentence, 'replace': revised, 'expected_sha256': sha, 'occurrences': occurrences},
            'origins': {'path': read_here, 'find': read_here, 'expected_sha256': read_here, 'occurrences': read_here,
                        'replace': basis or {'kind': 'DEDUCTION', 'proof': 'the sentence as the document has it, with %s in place of %s' % (new, old)}},
            'outputs': {'revision': ['revision_n'], 'digest': ['revision']},
            'expected': ('%s saved with "%s", read back, at its new revision' % (target.name, revised))[:400]}
    info = probe()
    why = '' if info['available'] else info['words']
    why = why or owner_has_it_open(target)
    if not why:
        return {'step': step, 'available': True, 'why': '', 'prepared': None, 'sentence': sentence, 'revised': revised}
    prepared = prepare(kernel, {'path': rel, 'find': sentence, 'replace': revised, 'occurrences': occurrences}, principal)
    return {'step': None, 'available': False, 'why': why, 'prepared': prepared, 'sentence': sentence, 'revised': revised}


# ---------------------------------------------------------------- joined to the assignments (K1) and the tool registry (K2)

def _join():
    """Her checks into the assignments' CHECKS, the words of the grants and of the tool; K2's slots filled when K2 is here.
    Guarded: whatever is not here is left as it is."""
    try:
        _asg.CHECKS.update(CHECKS)
        _asg.GRANT_WORDS.setdefault('libreoffice.replace', 'change a passage of a document through LibreOffice')
        _asg.GRANT_WORDS.setdefault('libreoffice.cell', 'set a cell of a spreadsheet through LibreOffice')
        _asg.TOOL_WORDS.setdefault('libreoffice', 'LibreOffice')
    except Exception:  # noqa: BLE001 - the assignments keep their own checks
        pass
    try:
        from . import tools_registry
    except Exception:  # noqa: BLE001 - K2 is not in this Graphite: describe() is the list
        return False
    fill = getattr(tools_registry, 'fill', None)
    if not callable(fill):
        return False
    filled = False
    for key, operations, function in (('office.read', ('libreoffice.read', 'libreoffice.find', 'libreoffice.prepare'),
                                       'workbench.office_bridge:read_document'),
                                      ('office.edit', ('libreoffice.replace', 'libreoffice.cell'), 'workbench.office_bridge:replace_passage')):
        try:
            fill(key, available=available, operations=operations, callable=function)
            filled = True
        except Exception:  # noqa: BLE001 - a slot shaped otherwise is left for the coordinator
            pass
    with contextlib.suppress(Exception):
        _asg.CHECKS.update(CHECKS)          # K2's fill may install its own; hers are these
    return filled


JOINED_TOOLS = _join()
