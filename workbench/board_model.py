"""The bulletin board (Graphite 1.0 L2): the focused object in the middle and its neighbours around it, each with the basis
of its link. This module is the model only: no Qt. board_qt.py draws it.

    the desk        one reading of the workspace's records (field_source.read_field) with a reader that keeps every answer
                    it was given (BoardReader), so the basis of a link is read from the same answers the Field was drawn from
                    and moving the focus reads nothing again
    recorded links  what the records say (each is a field inside a record, read by the Field's reader): a sheet reviewed
                    from a source's page, the cells a calculation used, the evidence and the checks of a finding, a total
                    bound to a page's words, the rows and quotes a goal or rule card rests on; and, read here: a calculation
                    worked again (the revision it replaced), an open question and the sources its investigation reads, a
                    plain file with the same bytes as an admitted source, and a link the owner kept by their word (board.keep)
    inferred links  possible, never facts: two things that name the same component, say the same words or the same
                    quantities, are used together by a third, or read as two revisions of one sheet by their names. Each is
                    labelled "not verified" and becomes recorded only by the owner's word (board.keep, approve scope, always
                    asks); nothing here ever writes one
    sizes           sizes(): workbench.relevance.rank when that module exists (1.0 L3), else a simple default of our own:
                    the focus largest (4), recorded and current near it (3), recorded but further or archived (2), possible (1);
                    at most CEILING around the focus, the rest grouped as a count that opens
    rings           layout(): the focus at the centre, rings around it; what feeds the focus on the left, what rests on it on
                    the right, possible links above and below; a tile's place depends only on the rings' geometry and the
                    order of the tiles, so a new reading of the same desk puts every tile where it was

Kernel operations (one block in engineering_kernel.py and engineering_cli.py, commented 1.0 L2):
    board.read   {focus?, task?}                  read     the board of one focus as data: tiles, wires, the basis of each
    board.links  {all?}                           read     the links the owner kept by their word (all: those set aside too)
    board.keep   {source, target, said?}          approve  keep a possible link as recorded, by the owner's word
                 | {id, state: IN | OUT}                   set it aside (OUT) or take it back (IN); nothing is deleted

No model, no floating point in anything checked (the layout's geometry is drawing, not a result), no network.
"""
from __future__ import annotations

import json
import math
import re
import time
from dataclasses import dataclass, field as dc_field
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .field_model import FieldObject, KIND_TAG, STATE_CURRENT, STATE_HELD, STATE_OPEN, STATE_RECHECK
from .field_source import Reader

RECORDED, INFERRED = 'recorded', 'inferred'
CEILING = 16                     # tiles around the focus before the rest is grouped as a count that opens
FOCUS_SIZE = 4
MORE = 'board:more'              # the id of the grouped count
KIND_WORD = dict(KIND_TAG, question='QUESTION', condition='TOTAL', app='APP', program='APP', more='MORE')
# The words a state is said in on a tile (KIND • STATE). A state not here is said as its own word.
STATE_WORDS = {STATE_CURRENT: 'CURRENT', STATE_RECHECK: 'RECHECK', STATE_OPEN: 'OPEN', STATE_HELD: 'HELD', 'refuted': 'REFUTED',
               'supported': 'SUPPORTED', 'archived': 'ARCHIVED', 'replaced': 'REPLACED', 'not read': 'NOT READ', 'unavailable': 'UNAVAILABLE',
               'elsewhere': 'ELSEWHERE', 'holds': 'HOLDS', 'does not hold': 'DOES NOT HOLD', 'cannot tell': 'CANNOT TELL', 'depends': 'DEPENDS'}
TITLE_MARKS = ('ARCHIVED', 'SUPERSEDED', 'OLD')        # a title that carries one of these is an older revision by its owner's own word
REVISION_TITLE = re.compile(r'^(?P<stem>.*?)\s*\b(?:rev(?:ision)?\.?)\s*(?P<rev>[A-Z0-9]{1,3})\b(?P<rest>.*)$', re.IGNORECASE)
# Which side of the focus a kind sits on when nothing says (material at the left, conclusions at the right) and its order there.
KIND_ORDER = ('source', 'folder', 'sheet', 'method', 'calculation', 'document', 'condition', 'finding', 'question', 'goal', 'rule', 'word', 'job')


# ---- the reading ---------------------------------------------------------------------------------------------------------
def _key(arguments):
    return json.dumps(arguments or {}, sort_keys=True, separators=(',', ':'), default=str)


class BoardReader(Reader):
    """The Field's reader that keeps every answer it was given: the board reads the basis of a link from them."""

    def __init__(self, kernel, principal, skip=()):
        super().__init__(kernel, principal, skip)
        self.answers = {}

    def call(self, operation, arguments=None, record=None):
        result = super().call(operation, arguments, record)
        if result is not None:self.answers[(operation, _key(arguments))] = result
        return result

    def got(self, operation, **arguments):
        return self.answers.get((operation, _key(arguments)))


def read_desk(kernel, principal, skip=()):
    """One reading of the workspace's work, as the Field reads it, with its answers kept. Returns (field, reader)."""
    from .field_source import read_field
    return read_field(kernel, principal, title='', skip=skip, reader=BoardReader(kernel, principal, skip))


# ---- the board -----------------------------------------------------------------------------------------------------------
@dataclass
class Edge:
    source: str
    target: str
    relation: str                    # reviewed, input, evidence, check, revision, question, quote, rests, condition, same bytes, kept,
    label: str = ''                  # and for possible links: same words, same component, used together, revision by name
    stale: bool = False
    kind: str = RECORDED
    said: str = ''                   # a possible link: what it names ("the startup duration"); a kept one: what was suggested
    strength: int = 0
    kept: str = ''                   # the owner's word that keeps it, its id


@dataclass
class Tile:
    id: str
    kind: str
    title: str
    state: str = ''
    kind_word: str = ''
    state_word: str = ''
    basis: str = ''                  # the basis line: how it is linked (or, for the focus, how it came to be)
    source: str = ''                 # the last line: where it comes from (a file, a sheet, an investigation)
    size: int = 1                    # 1..4; the focus is 4
    recorded: bool = True
    distance: int = 0                # 0 the focus, 1 a link to it, 2 a link to a neighbour
    side: str = ''                   # in (feeds the focus), out (rests on it), near (possible), '' the focus
    bridge: str = ''                 # a tile two steps away: the neighbour it is linked through
    reasons: list = dc_field(default_factory=list)
    pinned: bool = False
    turned_down: bool = False
    group: bool = False
    obj: object = None               # the FieldObject (or a stand-in) the window's openers understand
    members: list = dc_field(default_factory=list)       # the grouped count: the tiles it holds
    separate: dict = dc_field(default_factory=dict)      # relevance's own marks of truth, confidence and authority (1.0 L3), never its size


@dataclass
class Wire:
    source: str
    target: str
    kind: str                        # recorded | inferred
    relation: str
    label: str                       # the short words on the wire
    basis: list                      # the inspector's sentences
    stale: bool = False
    kept: str = ''
    said: str = ''                   # a possible link: what it names, in words ("both name the startup duration")

    @property
    def dashed(self):
        return self.kind == INFERRED

    def key(self):
        return (self.source, self.target, self.relation)


@dataclass
class Board:
    focus: Tile = None
    tiles: list = dc_field(default_factory=list)          # the neighbours (and the grouped count), the focus not among them
    wires: list = dc_field(default_factory=list)
    note: str = ''
    task: str = ''
    ranked_by: str = 'default'       # 'relevance' when workbench.relevance ranked the tiles

    def get(self, ident):
        if self.focus is not None and self.focus.id == ident:return self.focus
        return next((t for t in self.tiles if t.id == ident), None)

    def all(self):
        return ([self.focus] if self.focus is not None else []) + list(self.tiles)

    def wire(self, a, b):
        """The wire between two tiles (either way), recorded first."""
        found = [w for w in self.wires if {w.source, w.target} == {a, b}]
        found.sort(key=lambda w: w.kind != RECORDED)
        return found[0] if found else None

    def counts(self):
        shown = [t for t in self.tiles if t.id != MORE]
        return {'recorded': sum(1 for t in shown if t.recorded), 'possible': sum(1 for t in shown if not t.recorded),
                'grouped': sum(len(t.members) for t in self.tiles if t.id == MORE)}

    def as_data(self):
        def tile(t):
            return {'id': t.id, 'kind': t.kind, 'kind_word': t.kind_word, 'state': t.state, 'state_word': t.state_word, 'title': t.title,
                    'basis': t.basis, 'source': t.source, 'size': t.size, 'recorded': t.recorded, 'distance': t.distance, 'side': t.side,
                    'bridge': t.bridge, 'reasons': list(t.reasons), 'pinned': t.pinned, 'turned_down': t.turned_down, 'separate': dict(t.separate),
                    'members': [m.id for m in t.members]}
        return {'focus': tile(self.focus) if self.focus else None, 'tiles': [tile(t) for t in self.tiles],
                'wires': [{'source': w.source, 'target': w.target, 'kind': w.kind, 'relation': w.relation, 'label': w.label,
                           'basis': list(w.basis), 'stale': w.stale, 'dashed': w.dashed, 'kept': w.kept, 'said': w.said} for w in self.wires],
                'note': self.note, 'counts': self.counts(), 'ranked_by': self.ranked_by}


# ---- words ---------------------------------------------------------------------------------------------------------------
STOP = frozenset(('the a an and or of to in on at by for from with is are was were be been it its this that these those as not no '
                  'into over under than then so but if per each which what why how when where who does did do has have had can may '
                  'will shall would should could about after before up down out more most less very own same other only also just '
                  'there their they them his her him she he we our you your all any some one two three new now still being').split())
QUIET_WORDS = frozenset(('page', 'pages', 'sheet', 'sheets', 'revision', 'version', 'value', 'unit', 'units', 'parameter', 'reviewed', 'native',
                         'text', 'extraction', 'pdf', 'source', 'sources', 'calculation', 'document', 'file', 'files', 'invented',
                         'demonstration', 'data', 'nothing', 'here', 'measured', 'cells', 'cell', 'row', 'rows', 'exact', 'condition',
                         'conditions', 'reading', 'readings', 'current', 'archived', 'check', 'passed', 'supported', 'open', 'value'))
UNITS = r'(?:mA|uA|µA|A|mV|kV|V|mW|kW|W|Wh|mWh|kWh|ms|us|µs|s|min|h|Hz|kHz|MHz|GHz|°C|C|K|Ω|ohm|kΩ|mΩ|%|mm|cm|m|km|g|kg|N|Nm|Pa|kPa|bar)'
QUANTITY = re.compile(r'(?<![\w.])(\d+(?:\.\d+)?)\s?(' + UNITS + r')(?![\w])')
COMPONENT = re.compile(r'(?<![\w-])([A-Z]{1,3}\d{1,4}[A-Z]?|[A-Z]{2,}\d{2,}[A-Z0-9-]*)(?![\w-])')
WORD = re.compile(r"[A-Za-z][A-Za-z0-9'-]+")
TEXT_SUFFIXES = ('.txt', '.md', '.csv', '.tsv', '.json', '.py', '.ini', '.cfg', '.yaml', '.yml', '.log')
FILE_TEXT = 32 * 1024            # bytes of a plain text file read for its words
FILES_READ = 120                 # plain files read for their words, at most


def _quantity(number, unit):
    try:number = str(Decimal(number).normalize())
    except InvalidOperation:pass
    if 'E' in number:number = str(Decimal(number).quantize(Decimal(1)))
    return '%s %s' % (number, unit)


@dataclass
class Words:
    words: set
    pairs: dict                      # (a, b) -> 'a b' as said
    quantities: set
    components: set


def words_of(text, components_from=''):
    text = str(text or '')
    quantities = {_quantity(n, u) for n, u in QUANTITY.findall(text)}
    components = {c for c in COMPONENT.findall(str(components_from or ''))}
    tokens = [w.lower().strip("'-") for w in WORD.findall(QUANTITY.sub(' ', text))]
    keep = [w for w in tokens if len(w) >= 3 and w not in STOP]
    pairs = {}
    run = [w if (len(w) >= 3 and w not in STOP and w not in QUIET_WORDS) else None for w in tokens]
    for a, b in zip(run, run[1:]):
        if a and b and a != b:pairs[(a, b)] = '%s %s' % (a, b)
    return Words(set(w for w in keep if w not in QUIET_WORDS), pairs, quantities, components)


# ---- the desk as a graph -------------------------------------------------------------------------------------------------
def _calc_stem(title):
    return str(title or '').split(' · ')[0].strip()


def _short(text, most=48):
    text = ' '.join(str(text or '').split())
    return text if len(text) <= most else text[:most - 1].rstrip() + '…'


def _sheet_rows(sheet):
    """A reviewed sheet's rows as (parameter, value, unit) from its record's cells, the header left out."""
    cells = (((sheet or {}).get('document') or {}).get('sheets') or [{}])[0].get('cells') or {}
    rows = []
    for number in range(2, 400):
        a = (cells.get('A%d' % number) or {}).get('value')
        if a is None:
            if number > 2 and (cells.get('B%d' % number) or {}).get('value') is None:break
            continue
        rows.append((str(a), str((cells.get('B%d' % number) or {}).get('value') or ''), str((cells.get('C%d' % number) or {}).get('value') or '')))
    return rows


def _doc_text(got):
    blocks = ((got or {}).get('document') or {}).get('blocks') or ()
    return '\n'.join(str(b.get('text') or '') for b in blocks if isinstance(b, dict))[:6000]


class Desk:
    """One reading of the desk, as the board needs it: every object, every recorded link, and the words of each object."""

    def __init__(self, field, reader=None, files=None, kept=(), digest=None):
        self.field = field;self.reader = reader;self.files = files or {};self.digest = digest
        self.objects = {o.id: o for o in field.objects}
        self.edges = []
        self._words = {}
        self._df = None
        for link in field.links:
            self.edges.append(Edge(link.source, link.target, self._relation(link), link.label, bool(link.stale)))
        self._revisions()
        self._questions()
        self._checks()
        self._plain_files()
        self._kept(kept)
        try:      # 1.0 L4: a file saved again in another program: its earlier revision, admitted, and what rests on it are to recheck
            from .depths import mark_board;mark_board(self)
        except Exception:  # noqa: BLE001 - the board stands without it
            pass
        try:      # 1.0 A1: a file open in its program says so on its tile (OPEN IN GIMP, GIMP CLOSED); what you linked to it is rechecked
            from .app_files import mark_board as mark_programs;mark_programs(self)
        except Exception:  # noqa: BLE001 - 1.0 A1: the board stands without it
            pass
        self.assignments = []            # (objective, {object ids its steps read}) of the owner's recent assignments (1.0 K1)

    # ---- what the reader kept ------------------------------------------------------------------------------------------
    def got(self, operation, **arguments):
        if self.reader is None or not hasattr(self.reader, 'got'):return None
        return self.reader.got(operation, **arguments)

    def sheet(self, ident):
        """The office record of a sheet on the desk: (its row in office.list, its record)."""
        sheets = getattr(self.reader, 'sheets', None) or {}
        return sheets.get(ident, (None, None))

    def document(self, ident):
        return self.got('documents.get', id=str(ident).split(':', 1)[1]) if str(ident).startswith('document:') else None

    def investigation(self, inv):
        return self.got('investigation.sheet', id=inv)

    def path_of(self, claim_ident):
        return (self.got('investigation.path', claim=str(claim_ident).split(':', 1)[1]) or {}).get('path') or ()

    # ---- the links -----------------------------------------------------------------------------------------------------
    def _relation(self, link):
        a = self.objects.get(link.source);b = self.objects.get(link.target)
        ka = a.kind if a else '';kb = b.kind if b else ''
        if link.label == 'same bytes':return 'same bytes'
        if ka == 'source' and kb in ('sheet', 'document') and str(link.label).startswith('page'):return 'reviewed'
        if kb == 'calculation':return 'input'
        if kb in ('finding', 'question') and ka == 'source':return 'evidence'
        if kb in ('finding', 'question'):return 'check'
        if kb == 'condition':return 'condition'
        if kb == 'rule' and ka == 'source':return 'quote'
        return 'rests'

    def _revisions(self):
        """A calculation worked again is a new page that names the one it replaced: the earlier one is kept in Documents and
        drawn here as its earlier revision."""
        replaces = dict(getattr(self.reader, 'replaces', None) or {})
        for new, old in replaces.items():
            got = self.document(old)
            if old not in self.objects:
                doc = (got or {}).get('document') or {}
                if not doc:continue
                facts = []
                cells = ', '.join(str(i.get('cell')) for i in ((doc.get('derivation') or {}).get('inputs') or ()) if i.get('cell'))
                if cells:facts.append('cells ' + cells)
                if doc.get('revision') is not None:facts.append('revision %s' % doc['revision'])
                sheet = (doc.get('derivation') or {}).get('sheet')
                where = (self.objects.get('office:' + str(sheet)).title if self.objects.get('office:' + str(sheet)) else '')
                self.objects[old] = FieldObject(old, 'calculation', doc.get('title') or old, 'an earlier revision, kept in Documents', 'replaced',
                                                tuple(facts), where, {'kind': 'document', 'id': old.split(':', 1)[1]})
            if new in self.objects:
                self.edges.append(Edge(old, new, 'revision', 'worked again'))

    def _questions(self):
        """An open question is asked in an investigation; what that investigation reads is what the question is asked of."""
        for obj in list(self.objects.values()):
            if obj.kind != 'question' or not isinstance(obj.target, dict) or obj.target.get('kind') != 'investigation':continue
            sheet = self.investigation(obj.target.get('id')) or {}
            for read in sheet.get('read') or ():
                address = str(read.get('address') or '').lstrip('@')
                if address in self.objects:
                    self.edges.append(Edge(address, obj.id, 'question', 'asked of it'))

    def _checks(self):
        """A check an investigation keeps on a sheet (its own list, beside the claim's path): a recorded link from the sheet to
        the finding it checks, said in the check's last outcome."""
        from .field_source import CHECK_WORDS, words
        have = {(e.source, e.target) for e in self.edges}
        for (operation, _), sheet in list(getattr(self.reader, 'answers', {}).items()):
            if operation != 'investigation.sheet' or not isinstance(sheet, dict):continue
            for row in sheet.get('checked') or ():
                claim = 'claim:' + str(row.get('claim') or '')
                first = str(row.get('program') or '').split('|')[0].strip()
                address = first.lstrip('@') if first.startswith('@') else ''
                if claim in self.objects and address in self.objects and (address, claim) not in have:
                    outcome = str(row.get('last_outcome') or '').upper()
                    self.edges.append(Edge(address, claim, 'check', CHECK_WORDS.get(outcome, words(outcome) or 'check'), outcome == 'STALE'))
                    have.add((address, claim))

    def add_file(self, ident):
        for e in (self.files or {}).get('entries') or ():
            if e.get('id') == ident and ident not in self.objects:
                self.objects[ident] = file_object(e, (self.files or {}).get('root'));self._df = None
        return ident in self.objects

    def _plain_files(self):
        """A plain file in Files with the same bytes as an admitted source (its name first, then its digest)."""
        entries = list((self.files or {}).get('entries') or ())
        if not entries:return
        by_name = {}
        for e in entries:
            if e.get('kind') == 'file':by_name.setdefault(e.get('name'), []).append(e)
        for obj in list(self.objects.values()):
            if obj.kind != 'source' or not isinstance(obj.target, dict) or not obj.target.get('sha256'):continue
            for e in by_name.get(obj.title, ()):
                digest = self.digest(e['id']) if self.digest else None
                if digest and digest == obj.target.get('sha256'):
                    self.objects.setdefault(e['id'], file_object(e, self.files.get('root')))
                    self.edges.append(Edge(e['id'], obj.id, 'same bytes', 'same bytes'))

    def _kept(self, kept):
        for row in kept or ():
            if row.get('state') != 'IN':continue
            a, b = row.get('a'), row.get('b')
            if a in self.objects and b in self.objects:
                self.edges.append(Edge(a, b, 'kept', 'by your word', said=row.get('said') or '', kept=row.get('id') or ''))

    def recorded(self, ident):
        return [e for e in self.edges if ident in (e.source, e.target)]

    def set_assignments(self, rows):
        """The owner's assignments as read_assignments() gives them: each kept with the desk objects its steps name."""
        self.assignments = []
        for objective, ids in rows or ():
            named = {self.resolve(i) for i in ids} - {''}
            if len(named) >= 2:self.assignments.append((objective, named))

    def together(self, ident):
        """The objects named with this one among the inputs of one of the owner's assignments (1.0 K1): {id: its objective}."""
        out = {}
        for objective, ids in self.assignments:
            if ident in ids:
                for other in ids:out.setdefault(other, objective)
        return out

    def resolve(self, ident):
        """A record id as an assignment names it, as the board names it ('owner:…' -> 'office:owner:…')."""
        ident = str(ident or '').lstrip('@')
        for candidate in (ident, 'office:' + ident, 'document:' + ident, 'intake:' + ident, 'claim:' + ident):
            if candidate in self.objects:return candidate
        return ''

    # ---- words, for the possible links ---------------------------------------------------------------------------------
    def text_of(self, ident):
        obj = self.objects.get(ident)
        if obj is None:return '', ''
        if ident.startswith('fileid:'):       # a plain file: its name (without the suffix) and its first words; its folder says nothing
            stem = Path(obj.title).stem.replace('_', ' ').replace('-', ' ');text = self.file_text(ident)
            return stem + '\n' + text, stem + '\n' + text
        parts = [obj.title] + [str(x) for x in obj.lines]
        own = obj.title
        if obj.kind == 'sheet':
            _, record = self.sheet(ident)
            parts += ['%s %s %s' % row for row in _sheet_rows(record)]
        elif obj.kind in ('document', 'calculation'):
            text = _doc_text(self.document(ident));parts.append(text);own += '\n' + text
        return '\n'.join(parts), own

    def file_text(self, ident):
        obj = self.objects.get(ident)
        path = (obj.target or {}).get('path') if obj is not None and isinstance(obj.target, dict) else ''
        if not path or Path(path).suffix.lower() not in TEXT_SUFFIXES:return ''
        try:
            with open(path, 'rb') as stream:raw = stream.read(FILE_TEXT)
        except OSError:
            return ''
        if b'\x00' in raw:return ''
        return raw.decode('utf-8', 'replace')

    def words(self, ident):
        if ident not in self._words:
            text, own = self.text_of(ident)
            self._words[ident] = words_of(text, own)
        return self._words[ident]

    def frequency(self):
        """How many objects say each word, pair and quantity: what nearly every object says tells nothing about two of them."""
        if self._df is None:
            df = {}
            for ident in self.objects:
                w = self.words(ident)
                for token in set(w.words) | {('p', k) for k in w.pairs} | {('q', q) for q in w.quantities} | {('c', c) for c in w.components}:
                    df[token] = df.get(token, 0) + 1
            self._df = df
        return self._df

    def common(self, token):
        n = max(1, len(self.objects));count = self.frequency().get(token, 0)
        return count >= 3 and count * 2 >= n

    def desk_wide(self, word):
        """A word nearly every object says (the desk's own name, "Rail Demo"): a pair that holds it names the desk, not a thing."""
        n = max(1, len(self.objects));count = self.frequency().get(word, 0)
        return count >= 3 and count * 10 >= n * 7

    def add_files(self, limit=FILES_READ):
        """Plain files of Files as objects that a possible link may reach (their names, and a text file's first words)."""
        root = (self.files or {}).get('root')
        added = 0
        for e in (self.files or {}).get('entries') or ():
            if e.get('kind') != 'file' or e['id'] in self.objects:continue
            if added >= limit:break
            self.objects[e['id']] = file_object(e, root);added += 1
        self._df = None


def read_assignments(call, most=10):
    """The owner's recent assignments (1.0 K1) and the records their steps read: [(objective, {record ids})]. `call(op,
    args)` is a Kernel read that gives the result or None. Reads only; an assignment that cannot be read is left out."""
    out = []
    try:
        listed = call('assignment.list', {'limit': most}) or {}
    except Exception:  # noqa: BLE001 - no assignments (1.0 K1 not here, or nothing yet)
        return out
    for row in (listed.get('assignments') if isinstance(listed, dict) else listed) or ():
        try:got = call('assignment.status', {'id': row['id']}) or {}
        except Exception:  # noqa: BLE001
            continue
        ids = set()
        for step in got.get('steps') or ():
            arguments = step.get('arguments') or {}
            for key in ('id', 'sheet', 'document', 'claim', 'item'):
                if isinstance(arguments.get(key), str):ids.add(arguments[key])
            for value in (step.get('inputs') or {}).values():
                origin = (value or {}).get('origin') or {} if isinstance(value, dict) else {}
                if origin.get('kind') in ('RECORD', 'SOURCE') and origin.get('id'):ids.add(str(origin['id']))
        out.append((str(got.get('objective') or row.get('objective') or 'an assignment'), ids))
    return out


def _size_words(size):
    """A size in whole numbers: 812 bytes, 14 KB, 3 MB."""
    size = int(size or 0)
    if size < 1024:return '%d byte%s' % (size, '' if size == 1 else 's')
    if size < 1024 * 1024:return '%d KB' % ((size + 512) // 1024)
    return '%d MB' % ((size + 512 * 1024) // (1024 * 1024))


def file_object(entry, root):
    """A plain file of Files as the board draws it: a FILE tile (as living_nav_qt.LivingNav.with_focus draws it on the Field)."""
    folder = str(entry.get('path') or '').rpartition('/')[0]
    path = str(Path(root) / entry['path']) if root and entry.get('path') else ''
    if str(entry.get('path') or '').startswith('/') or entry.get('kind') == 'folder':      # 1.0 L6: elsewhere on this computer; a folder
        from .home_reach import folder_words, role_words, tilde
        place = str(entry.get('path') or '')
        where = folder_words(place) if place.startswith('/') else ('in ' + ('Files/' + folder if folder else 'Files'))
        role = role_words(place) if place.startswith('/') else 'in Files'
        folder_like = entry.get('kind') == 'folder'
        suffix = Path(str(entry.get('name') or '')).suffix
        said = 'a folder' if folder_like else (('%s file · %s' % (suffix[1:].upper(), _size_words(entry.get('size')))) if suffix else _size_words(entry.get('size')))
        return FieldObject(entry['id'], 'folder' if folder_like else 'source', entry.get('name') or 'a file', 'a %s %s' % ('folder' if folder_like else 'file', role),
                           '', (said, where), tilde(place) if place.startswith('/') else 'Files/' + place, {'kind': 'file', 'id': entry['id'], 'path': path},
                           'FOLDER' if folder_like else 'FILE')
    suffix = Path(str(entry.get('name') or '')).suffix
    said = ('%s file · %s' % (suffix[1:].upper(), _size_words(entry.get('size')))) if suffix else _size_words(entry.get('size'))
    return FieldObject(entry['id'], 'source', entry.get('name') or 'a file', 'a file in Files', '', (said, 'in ' + ('Files/' + folder if folder else 'Files')),
                       'Files/' + str(entry.get('path') or ''), {'kind': 'file', 'id': entry['id'], 'path': path}, 'FILE')


# ---- possible links ------------------------------------------------------------------------------------------------------
def possible(desk, focus, recorded_ids):
    """The links the desk can only suppose between the focus and another object, each with what it names. Returns {id: Edge}."""
    found = {}
    mine = desk.words(focus);fobj = desk.objects[focus]
    # used together: named among the inputs of one assignment of yours (1.0 K1), with nothing recorded between the two
    for ident, objective in desk.together(focus).items():
        if ident == focus or ident in recorded_ids or ident not in desk.objects:continue
        found.setdefault(ident, Edge(focus, ident, 'used together', 'used together', kind=INFERRED, strength=3,
                                     said='both are used in your assignment “%s”' % _short(objective, 70)))
    # revisions by their names: "… Rev A ARCHIVED" and "… Rev B CURRENT"
    mark = REVISION_TITLE.match(fobj.title or '')
    for ident, obj in desk.objects.items():
        if ident == focus or ident in recorded_ids or obj.kind != fobj.kind or not mark:continue
        theirs = REVISION_TITLE.match(obj.title or '')
        if theirs and theirs['stem'].strip().casefold() == mark['stem'].strip().casefold() and theirs['rev'].casefold() != mark['rev'].casefold():
            found[ident] = Edge(focus, ident, 'revision by name', 'another revision', kind=INFERRED, strength=4,
                                said='two revisions of one %s by their names (Rev %s, Rev %s)' % ('sheet' if obj.kind == 'sheet' else 'record', mark['rev'].upper(), theirs['rev'].upper()))
    # the same component, the same words, the same quantities
    for ident in desk.objects:
        if ident == focus or ident in recorded_ids or ident in found:continue
        theirs = desk.words(ident)
        components = sorted(c for c in mine.components & theirs.components if not desk.common(('c', c)))
        if components:
            found[ident] = Edge(focus, ident, 'same component', 'same component', kind=INFERRED, strength=3 + len(components),
                                said='both name %s' % _and(components[:2]))
            continue
        pairs = [mine.pairs[k] for k in sorted(set(mine.pairs) & set(theirs.pairs), key=lambda k: (desk.frequency().get(('p', k), 0), k))
                 if not desk.common(('p', k)) and not desk.desk_wide(k[0]) and not desk.desk_wide(k[1])]
        quantities = sorted((q for q in mine.quantities & theirs.quantities if not desk.common(('q', q))),
                            key=lambda q: (desk.frequency().get(('q', q), 0), q))
        single = sorted((w for w in mine.words & theirs.words if not desk.common(w)), key=lambda w: (desk.frequency().get(w, 0), w))
        score = 2 * len(pairs) + 2 * len(quantities) + len(single)
        if score < 2 or (not pairs and not quantities and len(single) < 2):continue
        if pairs:said = 'both name the %s' % _and(pairs[:2])
        elif quantities:said = 'both name %s' % _and(quantities[:2])
        else:said = 'both say %s' % _and(['“%s”' % w for w in single[:2]])
        found[ident] = Edge(focus, ident, 'same words', 'same words', kind=INFERRED, said=said, strength=min(score, 9))
    return found


def _and(items):
    items = [str(i) for i in items]
    if len(items) <= 1:return ''.join(items)
    return ', '.join(items[:-1]) + ' and ' + items[-1]


# ---- the basis of a link, in words ---------------------------------------------------------------------------------------
def _version_words(desk, sheet_ident, revision):
    """'version 1 (revision 1cf4712cf8a8)' for the sheet as it stands, or 'an earlier version (revision …); the sheet is at
    version 2 now'."""
    row, record = desk.sheet(sheet_ident)
    version = (record or {}).get('version') if record else (row or {}).get('version')
    now = (record or {}).get('revision')
    short = str(revision or '')[:12]
    if revision and now and revision == now:
        return 'version %s (revision %s)' % (version, short), True
    if revision:
        return 'an earlier version (revision %s); the sheet is at version %s now' % (short, version), False
    return 'version %s' % version if version is not None else 'its current version', True


def basis(desk, edge):
    """The inspector's sentences for one link, and the short words on its wire: (label, [sentences])."""
    a = desk.objects.get(edge.source);b = desk.objects.get(edge.target)
    an = a.title if a else edge.source;bn = b.title if b else edge.target
    if edge.kind == INFERRED:
        lines = ['Possible: %s; not verified.' % edge.said]
        if edge.relation == 'same words':
            lines.append('Found by matching their words, not by any record of Graphite\'s.')
        elif edge.relation == 'same component':
            lines.append('Found by the component\'s name in both, not by any record of Graphite\'s.')
        elif edge.relation == 'used together':
            lines.append('Each is recorded as used by that record; nothing records a link between the two of them.')
        elif edge.relation == 'revision by name':
            lines.append('Read from their titles only; nothing records that one replaced the other.')
        lines.append('It becomes a recorded link only by your word.')
        return 'possible · not verified', lines
    if edge.relation == 'kept':
        return 'by your word', ['Recorded by your word: you said “%s” and “%s” are linked.' % (_short(an, 70), _short(bn, 70)),
                                ('It was suggested because %s.' % edge.said) if edge.said else 'It was not one the desk had found.',
                                'You can set your word aside here; nothing else changes it.']
    if edge.relation == 'reviewed':
        row, record = desk.sheet(edge.target)
        pdf = ((record or {}).get('origin') or {}).get('pdf') or {}
        version = (record or {}).get('version') if record else (row or {}).get('version')
        lines = ['Reviewed from %s of %s into “%s”, version %s.' % (edge.label or 'a page', an, bn, version if version is not None else '?')]
        if pdf.get('source_sha256'):lines.append('The source as admitted: SHA-256 %s….' % str(pdf['source_sha256'])[:16])
        rows = _sheet_rows(record)
        if rows:lines.append('%d row%s reviewed: %s.' % (len(rows), '' if len(rows) == 1 else 's', _short(', '.join(r[0] for r in rows), 120)))
        if edge.stale:lines.append('Its source changed since: the sheet is to recheck.')
        return edge.label or 'reviewed', lines
    if edge.relation == 'input':
        got = desk.document(edge.target) or {}
        derivation = (got.get('document') or {}).get('derivation') or {}
        inputs = list(derivation.get('inputs') or ())
        if a is not None and a.kind == 'sheet' and inputs:
            said, now = _version_words(desk, edge.source, derivation.get('sheet_revision'))
            used = ['%s %s (cell %s, %s)' % (i.get('value'), i.get('unit') or '', i.get('cell'), i.get('parameter')) for i in inputs]
            lines = ['Used value%s %s from %s, %s, to calculate %s.' % ('' if len(used) == 1 else 's', _and(used), an, said, _calc_stem(bn))]
            value = ((((derivation.get('calculation') or {}).get('outputs') or [{}])[0] or {}).get('value')) or {}
            recipe = (derivation.get('recipe') or {}).get('expression')
            if value.get('decimal') is not None:
                lines.append('Worked exactly%s: %s %s%s.' % ((' as ' + recipe) if recipe else '', value['decimal'], value.get('unit') or '',
                                                             (' (exactly %s)' % value['rational']) if value.get('rational') and value['rational'] != value['decimal'] else ''))
            edits = [i for i in inputs if i.get('basis') == 'WORKING_SHEET_EDIT']
            for i in edits:
                original = (i.get('original_cells') or [None, None])[1]
                lines.append('%s is a working edit of the sheet%s.' % (i.get('cell'), (', not the reviewed reading of %s %s' % (original, i.get('unit') or '')) if original else ''))
            doc = got.get('document') or {}
            if doc.get('revision') is not None:lines.append('The calculation is revision %s of its page.' % doc['revision'])
            if edge.stale or not now:lines.append('The sheet changed after it was worked: the calculation is to recheck.')
            cells = ', '.join(str(i.get('cell')) for i in inputs if i.get('cell'))
            return ('cells ' + cells) if cells else (edge.label or 'input'), lines
        return edge.label or 'source page', ['Worked from %s of %s, for %s.' % (edge.label or 'the source page', an, _calc_stem(bn))]
    if edge.relation == 'evidence':
        note = ''
        for step in desk.path_of(edge.target):
            if str(step.get('address') or '').lstrip('@') == edge.source:note = step.get('note') or '';break
        verb = {'supports': 'supports', 'opposes': 'speaks against'}.get(edge.label, edge.label or 'bears on')
        inv = (b.where if b is not None else '') or 'its investigation'
        lines = ['%s %s the finding “%s”.' % (an, verb, _short(bn, 90)), 'Recorded as evidence in “%s”%s.' % (inv, (': “%s”' % note) if note else '')]
        if edge.stale:lines.append('The source changed since: the finding is to recheck.')
        return edge.label or 'evidence', lines
    if edge.relation == 'check':
        check = {}
        inv = (b.target or {}).get('id') if b is not None and isinstance(b.target, dict) else None
        for row in (desk.investigation(inv) or {}).get('checked') or ():
            if 'claim:' + str(row.get('claim')) == edge.target and edge.source in str(row.get('program') or ''):check = row;break
        rows = str(check.get('program') or '').split('|')[2:]
        where = ' and '.join(w.strip()[6:] if w.strip().startswith('where ') else w.strip() for w in rows if w.strip())
        lines = ['A check on %s%s %s.' % (an, (' (the rows where %s)' % where) if where else '', edge.label or 'ran')]
        if check.get('oracle'):lines.append('It looks for: “%s”.' % check['oracle'])
        lines.append('The finding: “%s”.' % _short(bn, 90))
        if edge.stale:lines.append('The sheet changed since the check ran: it no longer counts until it runs again.')
        return edge.label or 'check', lines
    if edge.relation == 'revision':
        was = desk.document(edge.source) or {};now = desk.document(edge.target) or {}
        def result(got):
            value = (((((got.get('document') or {}).get('derivation') or {}).get('calculation') or {}).get('outputs') or [{}])[0] or {}).get('value') or {}
            return ('%s %s' % (value.get('decimal'), value.get('unit') or '')).strip() if value.get('decimal') is not None else ''
        lines = ['“%s” was worked again: the new page is “%s”.' % (_calc_stem(an), bn)]
        if result(was) and result(now):lines.append('Its result went from %s to %s.' % (result(was), result(now)))
        lines.append('The earlier page is kept in Documents.')
        return 'worked again', lines
    if edge.relation == 'question':
        inv = (b.where if b is not None else '') or 'an investigation'
        return 'asked of it', ['The open question “%s” is asked in “%s”, which reads %s.' % (_short(bn, 90), inv, an)]
    if edge.relation == 'same bytes':
        digest = (b.target or {}).get('sha256') if b is not None and isinstance(b.target, dict) else ''
        return 'same bytes', ['The file %s in Files has the same bytes as the admitted source %s.' % (an, bn),
                              'Checked by their SHA-256%s.' % ((' (%s…)' % str(digest)[:16]) if digest else '')]
    if edge.relation == 'saved again':      # 1.0 L4: the file saved again in another program, and its earlier revision admitted
        from .depths import saved_again_basis
        return saved_again_basis(desk, edge)
    if edge.relation == 'condition':
        return edge.label or 'its words changed', ['A total bound to the words of “%s”: %s.' % (an, edge.label or 'its words changed')]
    if edge.relation == 'quote':
        return edge.label or 'pinned quote', ['The rule card “%s” rests on %s of %s, a quote you pinned.' % (_short(bn, 80), edge.label or 'words', an)]
    return edge.label or 'rests on it', ['“%s” rests on “%s”%s.' % (_short(bn, 80), _short(an, 80), (' (%s)' % edge.label) if edge.label else '')]


def short_basis(desk, edge, tile_id, focus=''):
    """The basis line on a tile: how it is linked, said about the tile ("it" is the focus; a tile two steps away names the
    neighbour it is linked through)."""
    other = edge.target if edge.source == tile_id else edge.source
    on = desk.objects.get(other);name = _short(on.title, 34) if on else ''
    it = 'it' if other == focus else '“%s”' % name
    feeds = edge.source == tile_id
    if edge.kind == INFERRED:return 'possible: %s · not verified' % edge.said
    if edge.relation == 'kept':return 'linked by your word'
    if edge.relation == 'reviewed':
        if feeds:return '%s reviewed into %s' % (edge.label or 'a page', name)
        row, record = desk.sheet(tile_id)
        version = (record or {}).get('version') if record else (row or {}).get('version')
        return 'reviewed from %s%s' % (edge.label or 'a page', (', version %s' % version) if version is not None else '')
    if edge.relation == 'input':
        if feeds:return 'gives %s%s' % (edge.label or 'its values', '' if other == focus else ' to ' + it)
        obj = desk.objects.get(tile_id)
        revision = next((f for f in (obj.lines if obj else ()) if str(f).startswith('revision')), '')
        return ', '.join(x for x in (edge.label or 'from %s' % name, revision) if x)
    if edge.relation == 'evidence':
        if feeds:return '%s %s' % ({'supports': 'supports', 'opposes': 'speaks against'}.get(edge.label, edge.label or 'bears on'), it)
        return '%s by %s' % ({'supports': 'supported', 'opposes': 'spoken against'}.get(edge.label, edge.label or 'read'), name)
    if edge.relation == 'check':
        return ('checked%s: %s' % ('' if other == focus else ' for ' + it, edge.label)) if feeds else ('its check on %s: %s' % (name, edge.label))
    if edge.relation == 'revision':return 'earlier revision' if feeds else 'worked again from it'
    if edge.relation == 'question':return 'read for the question' if feeds else 'asked of %s' % name
    if edge.relation == 'same bytes':return 'the same bytes'
    if edge.relation == 'saved again':return ('saved again · %s' % edge.said) if feeds else 'an earlier revision of %s · recheck' % it      # 1.0 L4
    return ('%s · %s' % (edge.label, name)) if edge.label else ('rests on %s' % name if not feeds else 'read by %s' % name)


# ---- sizes: relevance (L3) when it is there, a default of our own otherwise -------------------------------------------------
def relevance_module():
    try:
        from . import relevance           # 1.0 L3, built after the board
    except Exception:  # noqa: BLE001 - not built yet, or broken: the board stands on its own default
        return None
    return relevance if callable(getattr(relevance, 'rank', None)) else None


def relevance_relation(edge, ident, obj, recorded, distance):
    """What the candidate is to the focus in relevance's words (1.0 L3 reads "candidate <relation> focus"): input, output,
    quoted_by, quotes, finding_on, question_on, revision_of; 'recorded' for a recorded link of another kind or two steps away;
    'inferred' for a possible one."""
    if not recorded:return 'inferred'
    if distance != 1:return 'recorded'
    feeds = edge.source == ident             # the candidate feeds the focus: it supplies it
    if edge.relation == 'revision':return 'revision_of'
    if edge.relation == 'quote':return 'quoted_by' if feeds else 'quotes'
    if edge.relation in ('evidence', 'check', 'question') and not feeds:
        return 'question_on' if obj.kind == 'question' else 'finding_on'
    if edge.relation in ('kept', 'same bytes'):return 'recorded'
    return 'input' if feeds else 'output'


def revision_current(obj):
    """Which revision it is, where that is a question: True the current one, False an archived or replaced one, None when
    the object has no revisions to speak of."""
    if archived(obj):return False
    if obj.kind in ('sheet', 'source', 'calculation', 'document') and obj.state in (STATE_CURRENT, '', STATE_RECHECK):return True
    return None


def default_rank(candidates):
    """The board's own sizes, when relevance is not there: recorded before possible, current before archived, near before
    far. Whole numbers only. Returns one {id, size, score, reasons, pinned, turned_down, group} per candidate."""
    out = []
    for c in candidates:
        reasons = []
        if c['recorded']:
            reasons.append('a recorded link: %s' % c['relation_words'] if c['distance'] == 1 else 'two recorded links away, through “%s”' % _short(c['bridge_title'], 60))
            size = 3 if c['distance'] == 1 and not c['archived'] else 2
        else:
            reasons.append('a possible link, not verified: %s' % c['said'])
            size = 1
        if c['archived']:reasons.append('an earlier or archived revision')
        elif c['attention']:reasons.append('it waits for you (%s)' % c['state_word'].lower())
        score = size * 100 + (10 if c['attention'] else 0) - (5 if c['archived'] else 0) + min(9, int(c.get('strength') or 0))
        out.append({'id': c['id'], 'size': size, 'score': score, 'reasons': reasons, 'pinned': False, 'turned_down': False, 'group': False})
    order = sorted(out, key=lambda r: (-r['size'], -r['score'], _order_key(next(c for c in candidates if c['id'] == r['id']))))
    for at, row in enumerate(order):
        row['group'] = at >= CEILING
    return order


def _order_key(c):
    kind = c.get('kind', '')
    return (KIND_ORDER.index(kind) if kind in KIND_ORDER else len(KIND_ORDER), str(c.get('title', '')).casefold(), c['id'])


def sizes(kernel, focus, candidates, task=None):
    """One sizing per candidate, by id: workbench.relevance.rank(kernel, focus_id, candidates, task=None) when that module
    exists (its result per candidate: {id, size 1..4, score, reasons, pinned, turned_down, group}), else default_rank.
    Returns ({id: row}, 'relevance' | 'default')."""
    module = relevance_module()
    if module is not None and kernel is not None:
        try:
            rows = module.rank(kernel, focus, candidates, task=task)
            by = {str(r['id']): dict(r) for r in rows or () if isinstance(r, dict) and r.get('id') is not None}
            if by or not candidates:
                for c in candidates:      # a candidate relevance left out is still shown, small
                    by.setdefault(c['id'], {'id': c['id'], 'size': 1, 'score': 0, 'reasons': ['not ranked'], 'pinned': False, 'turned_down': False, 'group': False})
                for r in by.values():
                    r['size'] = max(1, min(4, int(r.get('size') or 1)))
                return by, 'relevance'
        except Exception:  # noqa: BLE001 - a relevance that fails leaves the board on its own default
            pass
    return {r['id']: r for r in default_rank(candidates)}, 'default'


# ---- the board for one focus ---------------------------------------------------------------------------------------------
def state_word(obj, edge_to_focus=None):
    state = str(obj.state or '')
    if obj.kind == 'finding' and state == STATE_CURRENT and any('supported' in str(f) for f in obj.lines):return 'SUPPORTED'
    if state in (STATE_CURRENT, '') and obj.kind in ('sheet', 'source') and any(m in str(obj.title).upper().split() for m in TITLE_MARKS):
        return 'ARCHIVED'
    return STATE_WORDS.get(state, state.upper())


def kind_word(obj):
    if obj.kind == 'more':return 'MORE'
    if obj.tag in ('FILE', 'FOLDER', 'BRIEF', 'WRITING'):return obj.tag
    return KIND_WORD.get(obj.kind, str(obj.kind).upper())


def archived(obj):
    return obj.state in ('replaced',) or state_word(obj) == 'ARCHIVED'


HOME_LINE = 'Select something on the left; what it is connected to appears here.'      # 1.0 D1: the empty board's one line


def build(desk, focus, kernel=None, task=None, first=None):
    """The board of one focus on this desk. `first` names the object to focus when `focus` is empty (the desk's own first)."""
    board = Board(task=task or '')
    focus = focus or first or (desk.field.first() if desk.field.objects else '')
    desk.add_files()
    if focus and focus not in desk.objects:desk.add_file(focus)        # a plain file of Files in focus, past those read for words
    if not focus or focus not in desk.objects:
        board.note = (HOME_LINE if not focus else      # 1.0 D1: the first state teaches
                      'That is not on this desk now. Choose something in the tree, or on the whole desk.')
        return board
    fobj = desk.objects[focus]
    # what is linked to it by the records, one step and two steps away
    near = {};bridge = {};link_of = {}
    for edge in desk.recorded(focus):
        other = edge.target if edge.source == focus else edge.source
        if other == focus or other not in desk.objects:continue
        if other not in near:near[other] = 1;link_of[other] = edge
    two = {}
    for first_ident in sorted(near, key=lambda i: _order_key({'id': i, 'kind': desk.objects[i].kind, 'title': desk.objects[i].title})):
        for edge in desk.recorded(first_ident):
            other = edge.target if edge.source == first_ident else edge.source
            if other in (focus, first_ident) or other in near or other in two or other not in desk.objects:continue
            two[other] = first_ident;link_of[other] = edge
    recorded_ids = set(near) | set(two)
    desk.add_files()
    guessed = possible(desk, focus, recorded_ids)
    candidates = []
    for ident in list(near) + list(two) + list(guessed):
        obj = desk.objects[ident];edge = link_of.get(ident) or guessed.get(ident)
        sw = state_word(obj)
        recorded = ident in recorded_ids;distance = 1 if ident in near or ident in guessed else 2
        candidates.append({'id': ident, 'kind': obj.kind, 'title': obj.title, 'state': obj.state, 'state_word': sw,
                           'recorded': recorded, 'distance': distance,
                           'relation': relevance_relation(edge, ident, obj, recorded, distance), 'board_relation': edge.relation,
                           'revision_current': revision_current(obj), 'basis': ('possible: ' + edge.said) if not recorded else basis(desk, edge)[1][0],
                           'words': _short(' '.join(str(x) for x in obj.lines), 200),
                           'relation_words': basis(desk, edge)[0], 'said': edge.said,
                           'bridge': two.get(ident, ''), 'bridge_title': desk.objects[two[ident]].title if ident in two else '',
                           'archived': archived(obj), 'attention': obj.needs_attention() or sw in ('REFUTED',), 'stale': edge.stale,
                           'strength': edge.strength, 'side': _side(edge, ident, near, two, link_of, focus)})
    ranked, board.ranked_by = sizes(kernel, focus, candidates, task)
    # the focus
    board.focus = Tile(focus, fobj.kind, fobj.title, fobj.state, kind_word(fobj), state_word(fobj),
                       ', '.join(str(x) for x in fobj.lines[:2]) or fobj.role, fobj.where, FOCUS_SIZE, True, 0, '', obj=fobj)
    shown = [];grouped = []
    if board.ranked_by == 'relevance':       # relevance's own order (its 'place'): it keeps a tile where it was
        order = sorted(candidates, key=lambda c: (int(ranked[c['id']].get('place', 10 ** 6)), _order_key(c)))
    else:
        order = sorted(candidates, key=lambda c: (-int(ranked[c['id']].get('size') or 1), -int(ranked[c['id']].get('score') or 0), _order_key(c)))
    for c in order:
        r = ranked[c['id']];obj = desk.objects[c['id']];edge = link_of.get(c['id']) or guessed.get(c['id'])
        tile = Tile(c['id'], obj.kind, obj.title, obj.state, kind_word(obj), c['state_word'], short_basis(desk, edge, c['id'], focus), obj.where,
                    max(1, min(4, int(r.get('size') or 1))), c['recorded'], c['distance'], c['side'], c['bridge'],
                    list(r.get('reasons') or ()), bool(r.get('pinned')), bool(r.get('turned_down')), bool(r.get('group')), obj)
        tile.separate = dict(r.get('separate') or {})
        (grouped if tile.group else shown).append(tile)
    board.tiles = shown
    if grouped:
        module = relevance_module() if board.ranked_by == 'relevance' else None
        words = ''
        if module is not None and callable(getattr(module, 'more_words', None)):
            try:words = module.more_words([ranked[t.id] for t in grouped])
            except Exception:  # noqa: BLE001
                words = ''
        words = words or 'and %d more' % len(grouped)
        more = FieldObject(MORE, 'more', words, 'grouped', '', (), '')
        board.tiles.append(Tile(MORE, 'more', words, '', 'MORE', '', 'opens: ' + _short(', '.join(t.title for t in grouped[:3]), 60),
                                '', 1, True, 2, 'near', obj=more, members=grouped, group=True))
    # the wires: every recorded link between the tiles shown, and each possible link from the focus
    ids = {t.id for t in board.all()}
    seen = set()
    for edge in desk.edges:
        if edge.source in ids and edge.target in ids and (edge.source, edge.target, edge.relation) not in seen:
            if focus not in (edge.source, edge.target) and not (edge.source in near or edge.target in near):continue
            seen.add((edge.source, edge.target, edge.relation))
            label, sentences = basis(desk, edge)
            board.wires.append(Wire(edge.source, edge.target, RECORDED, edge.relation, label, sentences, edge.stale, edge.kept, edge.said))
    for ident, edge in guessed.items():
        if ident in ids:
            label, sentences = basis(desk, edge)
            board.wires.append(Wire(focus, ident, INFERRED, edge.relation, label, sentences, False, '', edge.said))
    if not board.tiles:
        board.note = 'Nothing recorded links to it yet, and nothing here names what it names.'      # 1.0 D1: says why
    return board


def _side(edge, ident, near, two, link_of, focus):
    if edge.kind == INFERRED:return 'near'
    if ident in two:                     # two steps away: on the side of the neighbour it is linked through
        first = two[ident];e = link_of.get(first)
        return 'in' if e is not None and e.source == first and e.target == focus else 'out'
    return 'in' if edge.target == focus else 'out'


# ---- the rings -----------------------------------------------------------------------------------------------------------
DIMS = {4: (288, 140), 3: (246, 122), 2: (214, 100), 1: (190, 80)}
FOCUS_DIMS = (322, 136)              # the focus, larger than any neighbour
GAP = 22
ROUND = 3.4                      # the rings are rounded rectangles of this order (2 an ellipse): the tiles are wider than tall
SAMPLES = 720


def _ring_points(rx, ry):
    pts = []
    for k in range(SAMPLES):
        a = 2 * math.pi * k / SAMPLES
        c, s = math.cos(a), math.sin(a)
        pts.append((rx * math.copysign(abs(c) ** (2 / ROUND), c), ry * math.copysign(abs(s) ** (2 / ROUND), s), a))
    return pts


def ring_path(rx, ry):
    """The ring itself, as points to draw (x, y)."""
    return [(x, y) for x, y, _ in _ring_points(rx, ry)]


def _slots(rx, ry, n, start=math.pi):
    """n places on a ring at equal distances along it, the first at `start` (the left)."""
    pts = _ring_points(rx, ry)
    lengths = [0.0]
    for (x0, y0, _), (x1, y1, _) in zip(pts, pts[1:] + pts[:1]):
        lengths.append(lengths[-1] + math.hypot(x1 - x0, y1 - y0))
    total = lengths[-1]
    offset = next(i for i, p in enumerate(pts) if p[2] >= start - 1e-9) if start < 2 * math.pi else 0
    out = []
    for j in range(n):
        want = (lengths[offset] + total * j / n) % total
        i = min(range(len(pts)), key=lambda i: abs(lengths[i] - want))
        out.append((pts[i][0], pts[i][1], pts[i][2]))
    return out


def _overlap(a, b, gap):
    return abs(a[0] - b[0]) * 2 < a[2] + b[2] + 2 * gap and abs(a[1] - b[1]) * 2 < a[3] + b[3] + 2 * gap


PREFERRED = {'in': math.pi, 'out': 0.0}
RINGS_MOST = 4


def _ring_for(tiles, inner, rx, ry, pw, ph, scale):
    """One ring outside the last: its radii, the size of its places and its places, clear of every tile inside it."""
    gap = GAP * scale
    w = max(DIMS[t.size][0] for t in tiles) * scale;h = max(DIMS[t.size][1] for t in tiles) * scale
    rx += pw / 2 + w / 2 + gap * 1.2;ry += ph / 2 + h / 2 + gap
    for _ in range(14):                # grow the ring until its places clear the tiles inside it
        trial = _slots(rx, ry, 24)
        if not any(_overlap((x, y, w, h), r, gap / 2) for x, y, _ in trial for r in inner):break
        rx *= 1.06;ry *= 1.06
    n = 1
    for count in range(32, 0, -1):     # as many places as fit without touching
        places = _slots(rx, ry, count)
        if count == 1 or all(not _overlap((places[i][0], places[i][1], w, h), (places[(i + 1) % count][0], places[(i + 1) % count][1], w, h), gap / 2)
                             for i in range(count)):
            n = count;break
    return rx, ry, w, h, _slots(rx, ry, n)


def layout(board, scale=1.0):
    """Where each tile sits, the focus at (0, 0): ({id: (cx, cy, w, h)}, [(rx, ry)] of the rings drawn, bounds (x0, y0, x1, y1)).
    The inner ring holds the recorded neighbours (the larger tiles), the next the possible ones; a ring that is full passes
    the rest outward. What feeds the focus sits at the left, what rests on it at the right, a possible link above or below, a
    tile two steps away beside the neighbour it is linked through. Places are taken in the tiles' order (the more relevant
    first), each the free place nearest its own side, so the same desk is laid out the same way every time."""
    placed = {}
    if board.focus is None:return placed, [], (-1, -1, 1, 1)
    fw, fh = FOCUS_DIMS[0] * scale, FOCUS_DIMS[1] * scale
    placed[board.focus.id] = (0.0, 0.0, fw, fh)
    tiles = list(board.tiles)
    if not tiles:return placed, [], (-fw, -fh, fw, fh)
    bands = [b for b in ([t for t in tiles if t.size >= 2 and t.id != MORE], [t for t in tiles if t.size < 2 or t.id == MORE]) if b]
    rings_used = [];inner = [(0.0, 0.0, fw, fh)];rx, ry, pw, ph = fw / 2, fh / 2, fw, fh
    queue = []
    for band in bands + [[]] * RINGS_MOST:
        queue = queue + band
        if not queue or len(rings_used) >= RINGS_MOST:break
        rx, ry, w, h, places = _ring_for(queue, inner, rx, ry, pw, ph, scale)
        mine = queue[:len(places)];queue = queue[len(places):]
        rings_used.append((rx, ry))
        free = list(range(len(places)));count = {'up': 0, 'down': 0}
        groups = {}
        for t in mine:groups.setdefault((t.side, t.distance), []).append(t)
        for t in mine:
            if t.id == MORE:want = math.pi / 2
            elif t.side == 'near':
                way = 'up' if count['up'] <= count['down'] else 'down';count[way] += 1;k = count[way]
                want = (3 * math.pi / 2 if way == 'up' else math.pi / 2) + (0.0 if k == 1 else 0.34 * (k // 2) * (1 if k % 2 else -1))
            elif t.bridge and t.bridge in placed:
                bx, by = placed[t.bridge][0], placed[t.bridge][1];want = math.atan2(by, bx) % (2 * math.pi)
            else:
                group = groups[(t.side, t.distance)];k = group.index(t);m = len(group)
                spread = min(0.36, 2.4 / max(1, m))
                want = (PREFERRED.get(t.side, math.pi) + spread * (k - (m - 1) / 2) * (1 if t.side == 'in' else -1)) % (2 * math.pi)
            best = min(free, key=lambda i: (min(abs(places[i][2] - want), 2 * math.pi - abs(places[i][2] - want)), i))
            free.remove(best);x, y, _ = places[best]
            placed[t.id] = (x, y, DIMS[t.size][0] * scale, DIMS[t.size][1] * scale)
            inner.append(placed[t.id])
        pw, ph = w, h
    for t in queue:                      # more than the rings hold: grouped with the count
        t.group = True
    if queue:
        more = next((t for t in board.tiles if t.id == MORE), None)
        if more is not None:more.members.extend(queue)
        board.tiles = [t for t in board.tiles if t.id in placed]
    xs = [x - w / 2 for x, y, w, h in placed.values()] + [x + w / 2 for x, y, w, h in placed.values()]
    ys = [y - h / 2 for x, y, w, h in placed.values()] + [y + h / 2 for x, y, w, h in placed.values()]
    pad = 30 * scale
    return placed, rings_used, (min(xs) - pad, min(ys) - pad - 24 * scale, max(xs) + pad, max(ys) + pad + 24 * scale)


# ---- the owner's word on a link (board.keep) -----------------------------------------------------------------------------
OBJECT = {'type': 'string', 'pattern': '^[a-z]{2,16}:[A-Za-z0-9:_.-]{1,120}$'}
FIELDS = {
    'board.read': ({'focus': OBJECT, 'task': {'type': 'string', 'maxLength': 300}}, []),
    'board.links': ({'all': {'type': 'boolean'}}, []),
    'board.keep': ({'source': OBJECT, 'target': OBJECT, 'said': {'type': 'string', 'maxLength': 300},
                    'id': {'type': 'string', 'pattern': '^link:[a-f0-9]{32}$'}, 'state': {'type': 'string', 'enum': ['IN', 'OUT']}}, []),
}
SCOPES = {'board.read': 'read', 'board.links': 'read', 'board.keep': 'approve'}
OBSERVERS = ('board.read', 'board.links')


def ensure(db):
    db.execute('''CREATE TABLE IF NOT EXISTS board_links(id TEXT PRIMARY KEY, a TEXT, b TEXT, said TEXT, state TEXT, revision INTEGER,
                  set_by TEXT, at INTEGER, history TEXT)''')
    db.execute('CREATE UNIQUE INDEX IF NOT EXISTS board_links_pair ON board_links(a, b)')


def _row(r):
    return {'id': r[0], 'a': r[1], 'b': r[2], 'said': r[3], 'state': r[4], 'revision': r[5], 'set_by': r[6], 'at': r[7],
            'history': json.loads(r[8] or '[]')}


def kept_links(kernel, every=False):
    with kernel.db() as db:
        ensure(db)
        rows = db.execute('SELECT id, a, b, said, state, revision, set_by, at, history FROM board_links ORDER BY at, id').fetchall()
    out = [_row(r) for r in rows]
    return out if every else [r for r in out if r['state'] == 'IN']


def keep(kernel, args, principal):
    """The owner's word on a link. Approve scope: her calls (read only) never reach it, and it always asks."""
    import uuid
    now = int(time.time());who = getattr(principal, 'identity', 'owner')
    with kernel.db() as db:
        ensure(db)
        if args.get('id'):
            row = db.execute('SELECT id, a, b, said, state, revision, set_by, at, history FROM board_links WHERE id=?', (args['id'],)).fetchone()
            if row is None:raise ValueError('There is no such link of yours')
            state = args.get('state') or 'OUT';record = _row(row)
            history = record['history'] + [{'state': state, 'at': now, 'by': who}]
            db.execute('UPDATE board_links SET state=?, revision=?, at=?, history=? WHERE id=?', (state, record['revision'] + 1, now, json.dumps(history), args['id']))
            ident = args['id']
        else:
            a, b = str(args.get('source') or ''), str(args.get('target') or '')
            if not a or not b or a == b:raise ValueError('A link needs two different things')
            a, b = sorted((a, b))
            row = db.execute('SELECT id, a, b, said, state, revision, set_by, at, history FROM board_links WHERE a=? AND b=?', (a, b)).fetchone()
            if row is not None:
                record = _row(row);history = record['history'] + [{'state': 'IN', 'at': now, 'by': who}]
                db.execute('UPDATE board_links SET state=?, revision=?, at=?, history=?, said=? WHERE id=?',
                           ('IN', record['revision'] + 1, now, json.dumps(history), str(args.get('said') or record['said'] or '')[:300], record['id']))
                ident = record['id']
            else:
                ident = 'link:' + uuid.uuid4().hex
                db.execute('INSERT INTO board_links(id, a, b, said, state, revision, set_by, at, history) VALUES(?,?,?,?,?,?,?,?,?)',
                           (ident, a, b, str(args.get('said') or '')[:300], 'IN', 1, 'owner', now, json.dumps([{'state': 'IN', 'at': now, 'by': who}])))
        row = db.execute('SELECT id, a, b, said, state, revision, set_by, at, history FROM board_links WHERE id=?', (ident,)).fetchone()
    return _row(row)


def read(kernel, principal, focus='', task=None):
    """board.read: the board of one focus as data. Plain files are read through objects.files (a read)."""
    field, reader = read_desk(kernel, principal)
    files = None;digest = None
    try:
        answer = kernel.dispatch('objects.files', {}, principal)
        if answer.get('ok'):
            files = answer['result']

            def digest(ident):
                got = kernel.dispatch('objects.get', {'id': ident}, principal)
                found = got.get('result') if got.get('ok') else {}
                return found.get('digest') if found.get('digest_kind') == 'sha256' else None
    except Exception:  # noqa: BLE001 - the board stands without plain files
        files = None
    desk = Desk(field, reader, files, kept_links(kernel), digest)

    def call(op, args):
        answer = kernel.dispatch(op, args, principal)
        return answer.get('result') if answer.get('ok') else None
    desk.set_assignments(read_assignments(call))
    return build(desk, focus, kernel, task).as_data()


def dispatch(kernel, op, args, principal):
    if op == 'board.read':return read(kernel, principal, args.get('focus') or '', args.get('task'))
    if op == 'board.links':return {'links': kept_links(kernel, bool(args.get('all')))}
    if op == 'board.keep':return keep(kernel, args, principal)
    raise ValueError('Unknown board operation')
