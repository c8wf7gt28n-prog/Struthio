"""Relevance (Graphite 1.0, L3): how large and how near each neighbour of the focus is drawn on the board, and why.

The owner's paper, section 5: "Relevance belongs to the relationship between an object, a task, and a context. It is not a
permanent intrinsic property of the file." The board (L2) asks this module, for the focused object and the neighbours it
found, how large each tile is and where it stands; "Why am I shown?" asks it for the reasons in words.

A score from separately recorded reasons. Each reason is kept on its own, with its own words and its own whole-number weight
(WEIGHTS); the score is their sum, an exact int (or a Fraction, never a float). The reasons are the ones the plan names:

    a recorded dependency   what the neighbour is to the focus, as the records say: it supplies the focus ('input'), it was
                            made from it ('output'), it is quoted in it ('quoted_by'), it quotes it ('quotes'), a finding that
                            rests on it ('finding_on'), a question about it ('question_on'), another revision of it
                            ('revision_of'), a cross-reference ('cross_ref'). One of these, the one the link has.
    inferred vs verified    a link the desk only supposes (same words, same component, used together) is a weak reason and
                            says so: "possible match ...; not verified". It never becomes a recorded one here.
    current vs archived     the current revision is drawn larger; an archived one smaller (unless the task looks back:
                            "history", "earlier", "previous" ... then the earlier revision is the one that matters).
    unresolved              a contradiction (the evidence speaks against it, its evidence conflicts, it does not hold, it
                            failed) or an open question raises relevance. That is relevance, not truth: a refuted finding
                            is drawn larger because it needs attention, and its tile still says REFUTED.
    a change affects it     its source changed since it was made (recheck, stale).
    the task                the active assignment (K1), else the owner's last request on the desk, else none: a neighbour
                            that shares the task's distinguishing words, or that the assignment's steps use, rises.
    the owner's word        pinned by you: drawn large, first; turned down by you: put with the group at the edge, its
                            link kept. Both visible and reversible (Clear), kept in the Kernel, recorded on the trail.

Truth, confidence and authority are never folded into the score. Each keeps its own mark in `separate` (the record's
own state word, whether the link is recorded or only supposed, which revision it is), for the board to show beside the
size; they enter the score only through the reasons above.

Four sizes, stable. Size 4 is the largest (the focus itself is not ranked): 4 from a score of 60, 3 from 40, 2 from 20,
1 from 1; at most CAPACITY tiles of a size (the rest step down). A score of nothing or less, a turned-down neighbour and
the overflow of the smallest size form the periphery: group=True, shown as "and 12 more" that opens (more_words()).
Hysteresis: the previous ranking is kept in memory per workspace, focus and task (a task not seen on this board yet starts
from the board's latest ranking, so a new request moves only what it really changes). A neighbour whose score moved by no more
than a tenth of the score it was placed with (BAND) keeps that placing score: its size and its place do not change. A
larger change places it again. So a 3 % change of score moves nothing; a new reason (a finding refuted, a pin) does.

    rank(kernel, focus_id, candidates, task=None) -> [ {id, size, score, reasons, pinned, turned_down, group,
                                                        place, held, kind, title, separate}, ... ] in board order
        a candidate: {id, kind, state, relation, recorded, revision_current, basis}; optional: title (else read through
        the Kernel), stale (bool), words (more text that names it).
        task: None (the active assignment, else the owner's last request, else none), words (a str), an assignment's id,
        or {'words', 'title'?, 'ids'?, 'key'?}.
    why(kernel, focus_id, object_id, task=None) -> [reasons in words]
    pin / turn_down / clear (kernel, focus_id, object_id) -> the mark as kept (through Kernel.dispatch: on the trail)
    marks(kernel, focus_id) -> {object_id: 'pinned' | 'turned down'}
    note_request(kernel, words) -> the owner's last request, kept as the task when no assignment is active (12 hours)
    more_words(ranked) -> 'and 12 more' or ''

Kernel operations (registered in engineering_kernel and engineering_cli under "1.0 L3"):
    relevance.why        {focus, object, task?}   read      the reasons in words, the size and the owner's mark (observer)
    relevance.pin        {focus, object}          execute   pinned by you on this board
    relevance.turn_down  {focus, object}          execute   turned down by you on this board (the link is kept)
    relevance.clear      {focus, object}          execute   your mark taken back: sized by its reasons again

Tables of its own in the Kernel's database, made when first written: relevance_marks (the owner's marks, one row per owner,
board and object) and relevance_request (the owner's last request, one row per owner). Nothing else is written. No model.
"""
from __future__ import annotations

import collections
import hashlib
import json
import re
import threading
import time
from fractions import Fraction

SCHEMA = 'graphite.relevance/1'

# The weight of each reason: whole numbers, so the score is exact. One relation weight applies, the link's own.
WEIGHTS = {
    'input': 40, 'output': 35, 'quoted_by': 35, 'quotes': 30, 'finding_on': 30, 'question_on': 30,
    'revision_of': 25, 'cross_ref': 20, 'recorded': 20,       # 'recorded': a recorded link of another kind
    'inferred': 6,                                            # a link the desk only supposes
    'current': 15, 'archived': -5, 'looking_back': 15,        # which revision; an earlier one when the task looks back
    'contradiction': 25, 'open': 25, 'changed': 20,           # unresolved; a change affects it
    'task_word': 20, 'task_uses': 40,                         # per distinguishing word of the task (TASK_WORDS at most)
    'pinned': 100, 'turned_down': -100,                       # the owner's word
}
TASK_WORDS = 2                     # task words counted at most, per neighbour
THRESHOLDS = ((4, 60), (3, 40), (2, 20), (1, 1))      # size from the placing score
CAPACITY = {4: 4, 3: 6, 2: 8, 1: 6}                  # tiles of a size at most; the rest step down, then join the group
BAND = Fraction(1, 10)             # a score within a tenth of its placing score keeps its size and place
LEAST_BAND = 2                     # ... and never less than this
REQUEST_LASTS = 12 * 3600          # the owner's last request is the task for a working day (field_model.LATELY)
REMEMBERED = 64                    # rankings kept in memory (workspace, focus, task)
DESCRIBED_FOR = 30                 # seconds a title read through the Kernel is reused
MAX_ID = 400
MAX_REQUEST = 400

PINNED, TURNED_DOWN = 'pinned', 'turned down'
PIN_WORDS, DOWN_WORDS = 'pinned by you', 'turned down by you (its link is kept)'
MARK_OPS = {'relevance.pin': PINNED, 'relevance.turn_down': TURNED_DOWN, 'relevance.clear': ''}
OBJECT = {'type': 'string', 'minLength': 1, 'maxLength': MAX_ID}
FIELDS = {
    'relevance.why': ({'focus': OBJECT, 'object': OBJECT, 'task': {'type': 'string', 'minLength': 1, 'maxLength': 2000}},
                      ['focus', 'object']),
    'relevance.pin': ({'focus': OBJECT, 'object': OBJECT}, ['focus', 'object']),
    'relevance.turn_down': ({'focus': OBJECT, 'object': OBJECT}, ['focus', 'object']),
    'relevance.clear': ({'focus': OBJECT, 'object': OBJECT}, ['focus', 'object']),
}
SCOPES = {'relevance.why': 'read', 'relevance.pin': 'execute', 'relevance.turn_down': 'execute', 'relevance.clear': 'execute'}
OBSERVERS = ('relevance.why',)

KIND_WORDS = {'source': 'source', 'sheet': 'sheet', 'calculation': 'calculation', 'document': 'page', 'page': 'page',
              'report': 'report', 'finding': 'finding', 'question': 'question', 'condition': 'total', 'method': 'method',
              'job': 'job', 'folder': 'folder', 'file': 'file', 'goal': 'goal', 'rule': 'rule card', 'word': 'word of yours',
              'investigation': 'investigation', 'app': 'app'}
PREFIX_KINDS = {'office': 'sheet', 'intake': 'source', 'claim': 'finding', 'document': 'page', 'fileid': 'file',
                'files': 'file', 'goal': 'goal', 'rule': 'rule', 'word': 'word', 'investigation': 'investigation',
                'job': 'job', 'condition': 'condition', 'app': 'app'}
PAGES = ('document', 'page', 'report')
RELATIONS = ('input', 'output', 'quoted_by', 'quotes', 'finding_on', 'question_on', 'revision_of', 'cross_ref')
# What a state word says that is unresolved, or changed; anything else adds nothing (it is truth, shown on its own).
CONTRADICTION = {'refuted': 'the evidence speaks against it', 'held': 'its evidence conflicts, unresolved',
                 'conflict': 'its evidence conflicts, unresolved', 'does not hold': 'it does not hold', 'failed': 'it failed'}
OPEN_WORDS = {'cannot tell': 'it cannot be told yet', 'depends': 'it depends on your choice of revision'}
CHANGED = ('recheck', 'stale', 'changed')
ARCHIVED = ('archived', 'superseded', 'replaced')
# Words that say nothing about which neighbour is meant: a basis line's own words, a revision's label, and the verbs a
# plan's steps begin with ("Read the Rev B limits" is about the limits, not about reading).
QUIET = frozenset('pdf rev revision version page reviewed cell cells possible match both name names named word words not '
                  'verified current archived from with read reads write writes recompute compute calculate work check '
                  'find make open save run show explain note confirm look see get set use keep'.split())
LOOKING_BACK = ('history', 'historical', 'earlier', 'previous', 'archive', 'archived', 'past', 'former', 'old')
HEX_ID = re.compile(r'(?<![0-9a-f])[0-9a-f]{32}(?![0-9a-f])')

_LOCK = threading.RLock()
_MEMORY = collections.OrderedDict()     # (root, focus, task key) -> {id: {'anchor', 'place'}}
_LAST = collections.OrderedDict()       # (root, focus, task key) -> {id: the ranked row}
_LATEST = {}                            # (root, focus) -> task key of the latest ranking of that board
_SEEN = collections.OrderedDict()       # (root, id) -> kind, from the candidates the board passed
_DESCRIBED = collections.OrderedDict()  # (root, id) -> (kind, title, when)


class Task:
    """What the owner is doing now, as relevance reads it: the words that tell neighbours apart and the records it uses."""

    def __init__(self, kind='', key='', label='', words='', ids=(), title=''):
        self.kind, self.key, self.label, self.words, self.title = kind, key, label, words, title
        self.ids = frozenset(ids)

    def __bool__(self):
        return bool(self.kind)

    def as_record(self):
        return {'kind': self.kind, 'label': self.label, 'title': self.title}


NO_TASK = Task()


# ---------------------------------------------------------------- small helpers

def _owner():
    from .engineering_kernel import operator
    return operator()


def _root(kernel):
    return str(getattr(kernel, 'root', ''))


def _remember(store, key, value, most=REMEMBERED):
    store[key] = value;store.move_to_end(key)
    while len(store) > most:store.popitem(last=False)


def _digest(text):
    return hashlib.sha256(str(text).encode()).hexdigest()[:16]


def _clean_id(value, name):
    if not isinstance(value, str) or not value.strip() or len(value) > MAX_ID or any(ord(c) < 32 for c in value):
        raise ValueError('RELEVANCE_INVALID: %s must name an object' % name)
    return value


def _words(code):
    return str(code or '').replace('_', ' ').strip().lower()


def _stem_tools():
    try:
        from .reading import STOP, stem
        return stem, STOP
    except Exception:  # noqa: BLE001 - her dictionary is the stemmer; without it a plain lower-case word is its own stem
        return (lambda w: w.lower()), frozenset()


def _stems(text):
    """{stem: the word as written} of the words that can name something: three letters or more, not small words."""
    stem, stop = _stem_tools();out = {}
    for word in re.findall(r'[A-Za-z]+', str(text or '')):
        low = word.lower()
        if len(low) < 3 or low in stop or low in QUIET:continue
        out.setdefault(stem(low), low)
    return out


def _read(kernel, operation, arguments):
    """One Kernel read as the owner; None when it does not answer. Only observer reads are used: showing is not an event."""
    try:
        answer = kernel.dispatch(operation, arguments, _owner())
    except Exception:  # noqa: BLE001 - a title that cannot be read is left out, the ranking is not
        return None
    return answer.get('result') if isinstance(answer, dict) and answer.get('ok') else None


def _describe(kernel, ident):
    """(kind, title) of a record, read through the Kernel when the board did not pass them; '' where unknown."""
    key = (_root(kernel), ident)
    with _LOCK:
        hit = _DESCRIBED.get(key)
    if hit is not None and time.monotonic() - hit[2] < DESCRIBED_FOR:return hit[0], hit[1]
    prefix, _, rest = str(ident).partition(':')
    kind = PREFIX_KINDS.get(prefix, '');title = ''
    if prefix == 'office' and rest:
        got = _read(kernel, 'office.get', {'id': rest}) or {}
        title = got.get('title') or (got.get('document') or {}).get('title') or ''
    elif prefix == 'document' and rest:
        page = (_read(kernel, 'documents.get', {'id': rest}) or {}).get('document') or {}
        title = page.get('title') or ''
        if page.get('derivation'):kind = 'calculation'
    elif prefix == 'intake' and rest:
        got = _read(kernel, 'intake.item', {'id': rest}) or {}
        title = got.get('name') or (got.get('item') or {}).get('name') or ''
    elif prefix == 'claim' and rest:
        got = _read(kernel, 'investigation.path', {'claim': rest}) or {}
        title = got.get('text') or ''
        if str(got.get('role', '')).upper() == 'QUESTION':kind = 'question'
    elif prefix == 'fileid':
        got = _read(kernel, 'objects.get', {'id': ident}) or {}
        title = got.get('name') or (got.get('object') or {}).get('name') or ''
    with _LOCK:
        _remember(_DESCRIBED, key, (kind, str(title), time.monotonic()), 512)
    return kind, str(title)


def _kind_of(kernel, ident):
    with _LOCK:
        seen = _SEEN.get((_root(kernel), ident))
    return seen or _describe(kernel, ident)[0] or 'item'


# ---------------------------------------------------------------- the owner's marks and his last request

MARK_TABLE = ('CREATE TABLE IF NOT EXISTS relevance_marks(owner TEXT NOT NULL, focus TEXT NOT NULL, object TEXT NOT NULL, '
              'mark TEXT NOT NULL, at REAL NOT NULL, PRIMARY KEY(owner, focus, object))')
REQUEST_TABLE = 'CREATE TABLE IF NOT EXISTS relevance_request(owner TEXT PRIMARY KEY, words TEXT NOT NULL, at REAL NOT NULL)'


def _has(db, table):
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def _marks(kernel, owner, focus):
    """{object: (mark, when)} of one board; a read never makes a table."""
    with kernel.db() as db:
        if not _has(db, 'relevance_marks'):return {}
        return {obj: (mark, at) for obj, mark, at in
                db.execute('SELECT object, mark, at FROM relevance_marks WHERE owner=? AND focus=?', (owner, focus))}


def marks(kernel, focus_id, principal=None):
    """The owner's marks on one board: {object_id: 'pinned' | 'turned down'}."""
    return {obj: mark for obj, (mark, _) in _marks(kernel, (principal or _owner()).identity, focus_id).items()}


def _set_mark(kernel, args, principal, mark):
    focus = _clean_id(args.get('focus'), 'focus');obj = _clean_id(args.get('object'), 'object')
    if focus == obj:raise ValueError('RELEVANCE_FOCUS: the focus is not ranked on its own board, so it takes no mark')
    with kernel.db() as db:
        db.execute(MARK_TABLE)
        row = db.execute('SELECT mark FROM relevance_marks WHERE owner=? AND focus=? AND object=?',
                         (principal.identity, focus, obj)).fetchone()
        was = row[0] if row else ''
        if mark:db.execute('INSERT OR REPLACE INTO relevance_marks VALUES(?,?,?,?,?)', (principal.identity, focus, obj, mark, time.time()))
        else:db.execute('DELETE FROM relevance_marks WHERE owner=? AND focus=? AND object=?', (principal.identity, focus, obj))
    if mark == PINNED:said = 'Pinned by you on this board: it is drawn large and first. Clear takes it back.'
    elif mark == TURNED_DOWN:said = 'Turned down by you on this board: it waits in the group at the edge, and its link is kept. Clear takes it back.'
    elif was:said = 'Your mark (%s) is taken back: it is sized by its reasons again.' % was
    else:said = 'There was no mark of yours on it.'
    return {'schema': SCHEMA, 'focus': focus, 'object': obj, 'mark': mark, 'was': was, 'words': said}


def note_request(kernel, words, principal=None):
    """Keep the owner's last request on the desk (his words, as typed): the board's task when no assignment is active.
    One row per owner, replaced each time; nothing else is kept. Returns the words kept, or '' for none."""
    words = ' '.join(str(words or '').split())[:MAX_REQUEST]
    if not words:return ''
    with kernel.db() as db:
        db.execute(REQUEST_TABLE)
        db.execute('INSERT OR REPLACE INTO relevance_request VALUES(?,?,?)', ((principal or _owner()).identity, words, time.time()))
    return words


def last_request(kernel, principal=None, now=None):
    """The owner's last request when it is recent (REQUEST_LASTS), else ''."""
    with kernel.db() as db:
        if not _has(db, 'relevance_request'):return ''
        row = db.execute('SELECT words, at FROM relevance_request WHERE owner=?', ((principal or _owner()).identity,)).fetchone()
    if not row:return ''
    return row[0] if (now if now is not None else time.time()) - row[1] <= REQUEST_LASTS else ''


# ---------------------------------------------------------------- the task

def _assignment_task(kernel, principal, ident=None):
    try:
        from . import assignments
    except Exception:  # noqa: BLE001 - K1 missing: there is no assignment to be the task
        return None
    try:
        if ident is None:
            rows = [r for r in assignments.active_work(kernel, principal, limit=8) if r.get('state') not in ('stopped', 'done')]
            if not rows:return None
            ident = rows[0]['id']
        view = assignments.status(kernel, ident, principal)
    except Exception:  # noqa: BLE001 - an assignment that cannot be read is not the task
        return None
    steps = view.get('steps') or ()
    words = ' '.join([str(view.get('objective') or '')] + [str(s.get('title') or '') for s in steps])
    used = json.dumps([[s.get('inputs'), s.get('output')] for s in steps], ensure_ascii=True, default=str)
    title = str(view.get('title') or view.get('objective') or 'an assignment')
    return Task('assignment', 'assignment:' + view['id'], 'your assignment', words, HEX_ID.findall(used), title)


def resolve_task(kernel, task=None, principal=None):
    """The task the ranking is for: what was given; else the active assignment (K1); else the owner's last request on the
    desk; else none."""
    principal = principal or _owner()
    if isinstance(task, Task):return task
    if isinstance(task, dict):
        words = str(task.get('words') or task.get('objective') or task.get('text') or '')
        ids = [i for i in task.get('ids') or () if isinstance(i, str)]
        ids = [m for i in ids for m in (HEX_ID.findall(i) or [i])]
        return Task(str(task.get('kind') or 'given'), str(task.get('key') or 'given:' + _digest(words + '|' + ','.join(sorted(ids)))),
                    str(task.get('label') or 'your task'), words, ids, str(task.get('title') or ''))
    if isinstance(task, str) and task.strip():
        if re.fullmatch(r'[0-9a-f]{32}', task.strip()):
            found = _assignment_task(kernel, principal, task.strip())
            if found is not None:return found
        return Task('given', 'given:' + _digest(task.strip()), 'your task', task.strip())
    found = _assignment_task(kernel, principal)
    if found is not None:return found
    try:
        said = last_request(kernel, principal)
    except Exception:  # noqa: BLE001 - no request kept: no task
        said = ''
    if said:return Task('request', 'request:' + _digest(said), 'your last request', said, (), said)
    return NO_TASK


def _task_words(task, texts):
    """The task's words that tell the neighbours apart: in at least one neighbour and in no more than about half of them
    (a word every tile carries, such as the desk's own name, says nothing about which one is meant). [(stem, word)]."""
    if not task or not texts:return []
    said = _stems(task.words)
    counts = collections.Counter(s for text in texts.values() for s in set(_stems(text)) if s in said)
    n = len(texts)
    return [(s, w) for s, w in said.items() if counts.get(s) and counts[s] * 2 <= n + 1]


def _looks_back(task):
    if not task:return False
    stem, _ = _stem_tools()
    return bool(set(_stems(task.words)) & {stem(w) for w in LOOKING_BACK})


# ---------------------------------------------------------------- the reasons of one neighbour

def _relation_words(relation, focus_kind):
    f = 'the selected ' + KIND_WORDS.get(focus_kind, 'item')
    known = {'input': 'supplies ' + f, 'output': 'made from ' + f,
             'quoted_by': 'quoted in the current report' if focus_kind in PAGES else 'quoted by ' + f,
             'quotes': 'quotes ' + f, 'finding_on': 'a finding that rests on ' + f,
             'question_on': 'a question asked about ' + f, 'revision_of': 'another revision of ' + f,
             'cross_ref': 'a cross-reference with ' + f}
    return known.get(relation) or ('recorded link with %s (%s)' % (f, _words(relation)) if relation else 'recorded link with ' + f)


def _recorded(c):
    """Whether the link is recorded: as the board says; a link it calls 'inferred' never is."""
    relation = str(c.get('relation') or '').strip().lower()
    return relation != 'inferred' and bool(c.get('recorded', relation != ''))


def _inferred_words(basis, relation):
    text = ' '.join(str(basis or '').split()).strip().rstrip('.')
    if not text:
        what = _words(relation) if relation and relation != 'inferred' else ''
        return 'possible link%s; not verified' % (' (%s)' % what if what else '')
    text = text[0].lower() + text[1:]
    if text.startswith('possible:'):text = 'possible match: ' + text[len('possible:'):].strip()
    elif not text.startswith('possible'):text = 'possible link: ' + text
    if 'not verified' not in text:text += '; not verified'
    return text


def _reasons(c, focus_kind, task, counted, text, mark, looking_back):
    """[(weight key, weight, words)], the owner's mark first, then the link, then the rest, each kept on its own."""
    out = []
    if mark == PINNED:out.append(('pinned', WEIGHTS['pinned'], PIN_WORDS))
    elif mark == TURNED_DOWN:out.append(('turned_down', WEIGHTS['turned_down'], DOWN_WORDS))
    relation = str(c.get('relation') or '').strip().lower()
    if _recorded(c):
        key = relation if relation in RELATIONS else 'recorded'
        out.append((key, WEIGHTS[key], _relation_words(relation, focus_kind)))
    else:
        out.append(('inferred', WEIGHTS['inferred'], _inferred_words(c.get('basis'), relation)))
    state = _words(c.get('state'));kind = str(c.get('kind') or '').lower()
    current = c.get('revision_current')
    if current is None and state in ARCHIVED:current = False
    if current is True:out.append(('current', WEIGHTS['current'], 'current revision'))
    elif current is False:
        if looking_back:out.append(('looking_back', WEIGHTS['looking_back'], 'an earlier revision, and your task looks back'))
        else:out.append(('archived', WEIGHTS['archived'], 'archived revision'))
    if state in CONTRADICTION:out.append(('contradiction', WEIGHTS['contradiction'], CONTRADICTION[state]))
    elif state == 'open' or (kind == 'question' and state in ('', 'open')):
        out.append(('open', WEIGHTS['open'], 'an open question' if kind == 'question' else 'not settled yet: nothing decides it'))
    elif state in OPEN_WORDS:out.append(('open', WEIGHTS['open'], OPEN_WORDS[state]))
    if state in CHANGED or c.get('stale') or c.get('changed'):
        out.append(('changed', WEIGHTS['changed'], 'a change affects it: it needs a recheck'))
    if task:
        hexes = set(HEX_ID.findall(str(c.get('id') or '')))
        if hexes & task.ids:
            out.append(('task_uses', WEIGHTS['task_uses'], 'used by %s “%s”' % (task.label, task.title) if task.title
                        else 'used by ' + task.label))
        mine = _stems(text)
        shared = [w for s, w in counted if s in mine]
        if shared:
            out.append(('task_word', WEIGHTS['task_word'] * min(len(shared), TASK_WORDS),
                        'shares words with %s: %s' % (task.label, ', '.join("'%s'" % w for w in shared[:3]))))
    return out


# ---------------------------------------------------------------- sizes and places, stable

def _band(anchor):
    return max(abs(Fraction(anchor)) * BAND, LEAST_BAND)


def _size_of(score):
    for size, least in THRESHOLDS:
        if score >= least:return size
    return 0


def _place(memory_key, scored, fallback=None):
    """Sizes and places. A neighbour whose score is within the band of the score it was placed with keeps that placing
    score (`anchor`), so its size and its place stay; pinned ones first and large, turned-down ones last in the group.
    The placing scores are this board's for this task; for a task not seen on this board yet, the board's latest (so a new
    task moves only the tiles whose scores it really changes)."""
    with _LOCK:
        before = dict(_MEMORY.get(memory_key) or (_MEMORY.get(fallback) if fallback else None) or {})
    for s in scored:
        was = before.get(s['id'])
        if was is not None and abs(s['natural'] - was['anchor']) <= _band(was['anchor']):s['anchor'] = was['anchor']
        else:s['anchor'] = s['natural']
        s['before'] = was['place'] if was is not None else len(before) + 1
        s['held'] = s['anchor'] != s['natural']
    pinned = sorted((s for s in scored if s['mark'] == PINNED), key=lambda s: (s['mark_at'], s['id']))
    down = sorted((s for s in scored if s['mark'] == TURNED_DOWN), key=lambda s: (-s['anchor'], s['before'], s['id']))
    rest = sorted((s for s in scored if s['mark'] not in (PINNED, TURNED_DOWN)), key=lambda s: (-s['anchor'], s['before'], s['id']))
    used = {4: len(pinned), 3: 0, 2: 0, 1: 0}
    for s in pinned:s['size'], s['group'] = 4, False
    for s in rest:
        size = _size_of(s['anchor'])
        while size >= 1 and used[size] >= CAPACITY[size]:size -= 1
        if size >= 1:s['size'], s['group'] = size, False;used[size] += 1
        else:s['size'], s['group'] = 1, True
    for s in down:s['size'], s['group'] = 1, True
    ordered = pinned + [s for s in rest if not s['group']] + [s for s in rest if s['group']] + down
    with _LOCK:
        _remember(_MEMORY, memory_key, {s['id']: {'anchor': s['anchor'], 'place': i} for i, s in enumerate(ordered)})
    return ordered


def _exact(value):
    value = Fraction(value)
    return int(value) if value.denominator == 1 else value


# ---------------------------------------------------------------- the interface the board calls

def rank(kernel, focus_id, candidates, task=None):
    """One dict per candidate in board order (see the module's words); the focus itself is not ranked."""
    principal = _owner();root = _root(kernel)
    task = resolve_task(kernel, task, principal)
    rows = [];seen = {focus_id}
    for c in candidates or ():
        if isinstance(c, dict) and isinstance(c.get('id'), str) and c['id'] and c['id'] not in seen:
            seen.add(c['id']);rows.append(c)
    with _LOCK:
        for c in rows:
            if c.get('kind'):_remember(_SEEN, (root, c['id']), str(c['kind']).lower(), 4096)
    focus_kind = _kind_of(kernel, focus_id)
    try:
        owned = _marks(kernel, principal.identity, focus_id)
    except Exception:  # noqa: BLE001 - marks that cannot be read are not invented; the board is still ranked
        owned = {}
    described = {}
    for c in rows:
        title = c.get('title')
        if not title:title = _describe(kernel, c['id'])[1] if task else ''
        described[c['id']] = str(title or '')
    texts = {c['id']: ' '.join((described[c['id']], str(c.get('basis') or ''), str(c.get('words') or ''))) for c in rows}
    counted = _task_words(task, texts)
    back = _looks_back(task)
    scored = []
    for c in rows:
        mark, at = owned.get(c['id'], ('', 0))
        reasons = _reasons(c, focus_kind, task, counted, texts[c['id']], mark, back)
        natural = sum((Fraction(w) for k, w, _ in reasons if k not in ('pinned', 'turned_down')), Fraction(0))
        owner_weight = sum((Fraction(w) for k, w, _ in reasons if k in ('pinned', 'turned_down')), Fraction(0))
        recorded = _recorded(c)
        current = c.get('revision_current')
        if current is None and _words(c.get('state')) in ARCHIVED:current = False
        scored.append({'id': c['id'], 'natural': natural, 'owner_weight': owner_weight, 'mark': mark, 'mark_at': at,
                       'reasons': reasons, 'kind': str(c.get('kind') or _kind_of(kernel, c['id'])), 'title': described[c['id']],
                       'separate': {'truth': _words(c.get('state')), 'confidence': 'recorded' if recorded else 'inferred, not verified',
                                    'authority': '' if current is None else ('current revision' if current else 'archived revision')}})
    memory_key = (root, focus_id, task.key)
    with _LOCK:
        latest = _LATEST.get((root, focus_id))
    ordered = _place(memory_key, scored, (root, focus_id, latest) if latest is not None else None)
    out = []
    for i, s in enumerate(ordered):
        out.append({'id': s['id'], 'size': s['size'], 'score': _exact(s['natural'] + s['owner_weight']),
                    'reasons': [words for _, _, words in s['reasons']], 'pinned': s['mark'] == PINNED,
                    'turned_down': s['mark'] == TURNED_DOWN, 'group': s['group'], 'place': i, 'held': s['held'],
                    'kind': s['kind'], 'title': s['title'], 'separate': s['separate']})
    with _LOCK:
        _remember(_LAST, memory_key, {row['id']: row for row in out})
        _LATEST[(root, focus_id)] = task.key
        if len(_LATEST) > 4 * REMEMBERED:_LATEST.pop(next(iter(_LATEST)))
    return out


def ranked(kernel, focus_id, object_id, task=None):
    """The row of the latest ranking of this board for this object (for this task when one is given), or None."""
    root = _root(kernel)
    keys = []
    try:
        keys.append(resolve_task(kernel, task).key)
    except Exception:  # noqa: BLE001
        pass
    with _LOCK:
        if task is None and (root, focus_id) in _LATEST:keys.append(_LATEST[(root, focus_id)])
        for key in keys:
            row = (_LAST.get((root, focus_id, key)) or {}).get(object_id)
            if row is not None:return dict(row)
    return None


def why(kernel, focus_id, object_id, task=None, principal=None):
    """"Why am I shown?": the reasons in words, the owner's mark (as it is now) first."""
    row = ranked(kernel, focus_id, object_id, task)
    mark = marks(kernel, focus_id, principal).get(object_id, '')
    said = [r for r in (row or {}).get('reasons', ()) if r not in (PIN_WORDS, DOWN_WORDS)]
    head = [PIN_WORDS] if mark == PINNED else [DOWN_WORDS] if mark == TURNED_DOWN else []
    if row is None:said = ['not on this board now: open the board to see how it is linked']
    return head + said


def pin(kernel, focus_id, object_id):
    return _owner_call(kernel, 'relevance.pin', focus_id, object_id)


def turn_down(kernel, focus_id, object_id):
    return _owner_call(kernel, 'relevance.turn_down', focus_id, object_id)


def clear(kernel, focus_id, object_id):
    return _owner_call(kernel, 'relevance.clear', focus_id, object_id)


def _owner_call(kernel, operation, focus_id, object_id):
    """The owner's press, through the Kernel like any caller, so it is checked and recorded on the trail."""
    answer = kernel.dispatch(operation, {'focus': focus_id, 'object': object_id}, _owner())
    if not answer.get('ok'):raise ValueError((answer.get('error') or {}).get('message') or 'RELEVANCE_REFUSED')
    return answer['result']


def more_words(ranked_rows):
    """The periphery's words for the board: 'and 12 more' (it opens), or '' when nothing is grouped."""
    n = sum(1 for row in ranked_rows or () if row.get('group'))
    return 'and %d more' % n if n else ''


def dispatch(kernel, op, args, principal):
    if op == 'relevance.why':
        focus = _clean_id(args.get('focus'), 'focus');obj = _clean_id(args.get('object'), 'object')
        task = args.get('task')
        row = ranked(kernel, focus, obj, task)
        mark = marks(kernel, focus, principal).get(obj, '')
        return {'schema': SCHEMA, 'focus': focus, 'object': obj, 'reasons': why(kernel, focus, obj, task, principal), 'shown': row is not None,
                'size': row['size'] if row else None, 'score': str(row['score']) if row else None, 'group': row['group'] if row else None,
                'pinned': mark == PINNED, 'turned_down': mark == TURNED_DOWN, 'separate': row['separate'] if row else None,
                'task': resolve_task(kernel, task, principal).as_record(),
                'note': 'Relevance says why it is drawn this large; truth, confidence and authority are marked on their own.'}
    if op in MARK_OPS:return _set_mark(kernel, args, principal, MARK_OPS[op])
    raise ValueError('Unknown relevance operation')
