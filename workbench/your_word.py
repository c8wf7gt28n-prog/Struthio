"""Your word (0.8.6 S3, "Kas's mind, no model"): one family of records for what is yours to say on an open point.

A word is a Project Desk record (kind 'word', schema ledger.word/1, on screen "your word"). It is set only by your press:
word.set is approve scope and is named in stacy_hand.ALWAYS_ASKS, so it asks at every place of the dial, and her calls
(made as a principal that holds only read) cannot set one. Kasandra's own proposals are never records: her reasons show
them as "mine, not agreed", with an Agree button that issues word.set.

  sort       what it says                                       example
  CHOICE     which of named alternatives applies                "Rail Demo limits Rev B CURRENT" applies to this goal,
                                                                or to this desk where the revisions disagree
  READING    how a row's words read: an exact span and its      "Up to 40 ms" (Rev B, row 4) means 0 to 40 ms after
             meaning                                            switch-on
  COMPLETE   a sheet is complete for named dates                "Home Demo bank Sep-Nov" is complete from 1 September
                                                                to 17 November 2026
  SAYS       your own account, in your words                    "I received no itemised statement"
  STANDING   a standing choice for this desk                    when two revisions disagree, the one marked CURRENT
                                                                applies

Each word keeps: statement (fixed template words with the sheet's title, the row and the dates put in, never free words
except your own account, quoted), subject (record ids), value, scope ('goal' or 'desk'), because (the rows it rests on),
the rows and sheets it was said about as they stood (bound), set_by 'owner', and state IN or OUT. Setting a word aside
writes a new revision (OUT); taking it back writes another (IN); nothing is deleted, and word.get shows the history.
Saying a word again about the same subject is a new revision of the same record.

Freshness is computed on read, never stored: CURRENT, or RECONSIDER when a row it was said about, or one it rests on,
reads differently now (its parameter, value, unit or conditions), or when a sheet it covers as a whole (COMPLETE) was
saved again. A row of the same sheet that it does not name changes nothing. Nothing is undone automatically: a word to
reconsider stays IN, is shown with what changed, and is not applied by her reasons until you say it again.

  word.list  {all?, about?}                                                read   IN words (all: OUT too), each with
                                                                                  its freshness; about: a goal's id or key
  word.get   {id}                                                          read   the word, its freshness and history
  word.set   {sort, goal?, choice?, sheet?, cell?, span?, means?, from?,   approve  (ALWAYS_ASKS)
              to?, words?, standing?, because?}
             | {sort: CHOICE, rule, choice, cell} | {sort: CHOICE, rule,       which row applies past what a rule card covers,
               none: true}                                                 or none (0.8.6 S6, rules.beyond_word; scope 'rule')
             | {id, expected_revision, state}                              set aside (OUT) or take back (IN)

Pure Python apart from the Kernel's own record store; no Qt, no model, no float.
"""
from __future__ import annotations

import re
from datetime import date

from . import project_desk as records

KIND = 'word'
SCHEMA = 'ledger.word/1'
SHOWN = 'your word'
SORTS = ('CHOICE', 'READING', 'COMPLETE', 'SAYS', 'STANDING')
STATES = ('IN', 'OUT')
CURRENT, RECONSIDER = 'CURRENT', 'RECONSIDER'
STANDING_CHOICES = ('CURRENT_REVISION',)
MARKS = ('CURRENT', 'ARCHIVED', 'SUPERSEDED', 'DRAFT', 'OLD')      # words a sheet's title carries to mark its revision

_SHEET = {'type': 'string', 'pattern': '^owner:[a-f0-9]{32}$'}
_CELL = {'type': 'string', 'pattern': '^B[1-9][0-9]{0,2}$'}
_DATE = {'type': 'string', 'pattern': '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'}
_GOAL = {'type': 'string', 'pattern': '^([a-f0-9]{32}|[a-f0-9]{64})$'}
_TEXT = {'type': 'string', 'minLength': 1, 'maxLength': 300}
_ROW = {'type': 'object', 'additionalProperties': False, 'required': ['sheet', 'cell'], 'properties': {'sheet': _SHEET, 'cell': _CELL}}
FIELDS = {
    'word.list': ({'all': {'type': 'boolean'}, 'about': _GOAL}, []),
    'word.get': ({'id': records.ID}, ['id']),
    'word.set': ({'sort': {'type': 'string', 'enum': list(SORTS)}, 'goal': _GOAL, 'choice': _SHEET, 'sheet': _SHEET, 'cell': _CELL,
                  'span': _TEXT, 'means': _TEXT, 'from': _DATE, 'to': _DATE, 'words': _TEXT,
                  'standing': {'type': 'string', 'enum': list(STANDING_CHOICES)},
                  'because': {'type': 'array', 'maxItems': 8, 'items': _ROW},
                  'id': records.ID, 'expected_revision': records.REV, 'state': {'type': 'string', 'enum': list(STATES)},
                  'rule': {'type': 'string', 'pattern': '^[a-f0-9]{32}$'}, 'none': {'type': 'boolean'}}, []),   # 0.8.6 S6: past what a rule covers
}
WRITES = ('word.set',)
SCOPES = {op: 'approve' if op in WRITES else 'read' for op in FIELDS}
OBSERVERS = ('word.list', 'word.get')

# Her words about your word: fixed templates (design 3.6: no exclamation mark, no sentence over 30 words).
WORDS = {
    'choice_goal': '“{chosen}” applies to the goal “{goal}”',
    'choice_desk': 'For this desk, “{chosen}” applies where it and {others} disagree',
    'reading': '“{span}” ({title}, row {row}) means {means}',
    'complete': '“{title}” is complete from {start} to {end}',
    'says': 'You say: “{words}”',
    'standing': 'When two revisions disagree, the one marked CURRENT applies on this desk',
    'fresh': 'Your word stands as you said it.',
    'reconsider': 'Your word is to reconsider: {what} changed since you said it. I do not apply it until you say it again.',
    'mine': 'mine, not agreed',
}
MONTHS = ('January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December')


# ---- reading the desk ----------------------------------------------------------------------------------------------------

def _saved(sheet):
    from .office_service import store
    try:return store().get(sheet)
    except (ValueError, OSError, KeyError):return None


def _row_of(saved, cell):
    """A Value cell's row as it stands: tolerances.sheet_cell's shape, or None."""
    from .tolerances import sheet_cell
    return sheet_cell(saved, cell) if saved else None


def _bind_row(saved, cell):
    """A row bound as it stands now, as condition cards bind their words: what it says and on which revision."""
    found = _row_of(saved, cell)
    if not found:raise ValueError('WORD_ROW_NOT_FOUND: %s is not a Value cell of that sheet' % cell)
    return {'address': found['address'], 'sheet': found['sheet'], 'cell': found['cell'], 'title': found['title'], 'parameter': found['parameter'],
            'value': found['value'], 'unit': found['unit'], 'conditions': found['conditions'], 'revision': found['revision']}


def _bind_sheet(saved):
    return {'address': 'office:' + saved['id'], 'sheet': saved['id'], 'title': (saved.get('document') or {}).get('title') or '',
            'revision': saved['revision']}


def row_number(cell):
    return int(str(cell)[1:])


def short_name(title, others=()):
    """A revision's name as people say it: the title without the words every alternative shares at its start (keeping the
    last of them when what is left is a letter or two, as in 'Rev B'), and without a trailing mark such as CURRENT ('Rail
    Demo limits Rev B CURRENT' beside Rev A gives 'Rev B')."""
    words = str(title).split();rest = [str(o).split() for o in others if str(o) != str(title)]
    start = 0
    while rest and start < len(words) - 1 and all(len(o) > start and o[start] == words[start] for o in rest):start += 1
    if 0 < start < len(words) and len(words[start]) <= 2:start -= 1
    words = words[start:]
    while len(words) > 1 and words[-1] in MARKS:words = words[:-1]
    return ' '.join(words) or str(title)


def marked_current(alternatives):
    """The one alternative whose title carries the word CURRENT, or None: her proposal, never a choice made for you."""
    marked = [a for a in alternatives if 'CURRENT' in str(a.get('title', '')).split()]
    return marked[0] if len(marked) == 1 else None


def _goal(kernel, principal, ref):
    """A goal by a kept goal's id or a candidate's key: (goal, its id or '', its key)."""
    from . import goals
    if len(ref) == 32:
        for g in goals._records(kernel, principal):
            if g['id'] == ref:return g, g['id'], g.get('key', '')
        raise ValueError('WORD_GOAL_NOT_FOUND: no kept goal has that id')
    for g in goals.candidates(kernel, principal):
        if g['key'] == ref:return g, '', g['key']
    raise ValueError('WORD_GOAL_NOT_FOUND: the desk no longer proposes that goal; ask for the candidates again')


def _alternatives_of(goal):
    """The goal's alternatives, flattened: [ref], for its one limit with revisions."""
    found = []
    for options in (goal.get('alternatives') or {}).values():found.extend(options)
    return found


def date_words(text):
    day = date.fromisoformat(text)
    return '%d %s %d' % (day.day, MONTHS[day.month - 1], day.year)


# ---- the record ----------------------------------------------------------------------------------------------------------

def _compose(kernel, principal, args):
    """(key, fields) of a word from what the owner pressed: the statement from a template, the subject, the value and the
    rows and sheets it is said about, bound as they stand."""
    sort = args.get('sort')
    if sort not in SORTS:raise ValueError('WORD_SORT: say which sort of word this is')
    allowed = {'CHOICE': {'goal', 'choice', 'because', 'rule', 'cell', 'none'}, 'READING': {'sheet', 'cell', 'span', 'means', 'because'},
               'COMPLETE': {'sheet', 'from', 'to', 'because'}, 'SAYS': {'words', 'goal', 'because'}, 'STANDING': {'standing'}}[sort]
    extra = set(args) - allowed - {'sort'}
    if extra:raise ValueError('WORD_FIELDS: a %s word does not take %s' % (sort, ', '.join(sorted(extra))))
    because = []
    for item in args.get('because') or ():
        saved = _saved(item['sheet'])
        if not saved:raise ValueError('WORD_ROW_NOT_FOUND: that sheet cannot be read')
        because.append(_bind_row(saved, item['cell']))
    bound = [];subject = {};value = {};scope = 'desk'
    if sort == 'CHOICE' and ('rule' in args or 'cell' in args or 'none' in args):   # 0.8.6 S6: which row applies past what a rule covers
        if not args.get('rule') or args.get('goal'):raise ValueError('WORD_FIELDS: a row past what a rule covers names the rule, and no goal')
        from .rules import beyond_word
        statement, subject, value, bound, ident_key = beyond_word(kernel, principal, args)
        fields = {'sort': sort, 'statement': statement, 'subject': subject, 'value': value, 'scope': 'rule', 'because': because, 'bound': bound,
                  'set_by': 'owner', 'state': 'IN'}
        return records.digest(list(ident_key)), fields
    if sort == 'CHOICE':
        if not args.get('choice'):raise ValueError('WORD_FIELDS: a choice names the sheet that applies')
        if args.get('goal'):
            goal, ident, key = _goal(kernel, principal, args['goal']);options = _alternatives_of(goal)
            chosen = next((a for a in options if a['sheet'] == args['choice']), None)
            if chosen is None:raise ValueError('WORD_NOT_AN_ALTERNATIVE: that sheet is not one of the revisions this goal reads')
            for ref in options:
                saved = _saved(ref['sheet'])
                if saved:bound.append(_bind_row(saved, ref['cell']))
            scope = 'goal';subject = {'goal': ident, 'goal_key': key, 'sheets': sorted({a['sheet'] for a in options})}
            others = [a['title'] for a in options if a['sheet'] != chosen['sheet']]
            statement = WORDS['choice_goal'].format(chosen=chosen['title'], goal=goal['statement'])
            ident_key = ('CHOICE', 'goal', args['goal'])
        else:
            from . import goals
            sets = [_alternatives_of(g) for g in goals.candidates(kernel, principal)]
            sets = [s for s in sets if any(a['sheet'] == args['choice'] for a in s)]
            if not sets:raise ValueError('WORD_NOT_AN_ALTERNATIVE: no two revisions on this desk include that sheet')
            refs = [a for s in sets for a in s];chosen = next(a for a in refs if a['sheet'] == args['choice'])
            for ref in sorted({(a['sheet'], a['cell']) for a in refs}):
                saved = _saved(ref[0])
                if saved:bound.append(_bind_row(saved, ref[1]))
            sheets = sorted({a['sheet'] for a in refs});titles = {a['sheet']: a['title'] for a in refs}
            others = [titles[s] for s in sheets if s != chosen['sheet']]
            subject = {'sheets': sheets}
            statement = WORDS['choice_desk'].format(chosen=chosen['title'], others=' and '.join('“%s”' % t for t in others))
            ident_key = ('CHOICE', 'desk', tuple(sheets))
        value = {'sheet': chosen['sheet'], 'title': chosen['title'], 'name': short_name(chosen['title'], others)}
    elif sort == 'READING':
        if not {'sheet', 'cell', 'span', 'means'} <= set(args):raise ValueError('WORD_FIELDS: a reading names the row, the exact words and what they mean')
        saved = _saved(args['sheet'])
        if not saved:raise ValueError('WORD_ROW_NOT_FOUND: that sheet cannot be read')
        row = _bind_row(saved, args['cell']);span = args['span'].strip()
        said = ' · '.join((row['parameter'], ('%s %s' % (row['value'], row['unit'])).strip(), row['conditions']))
        if not span or span not in said:raise ValueError('WORD_SPAN_NOT_IN_ROW: those words are not in row %d of “%s”' % (row_number(row['cell']), row['title']))
        bound.append(row);subject = {'sheet': row['sheet'], 'cell': row['cell']}
        value = {'span': span, 'means': args['means'].strip()}
        statement = WORDS['reading'].format(span=span, title=row['title'], row=row_number(row['cell']), means=value['means'])
        ident_key = ('READING', row['sheet'], row['cell'], span)
    elif sort == 'COMPLETE':
        if not {'sheet', 'from', 'to'} <= set(args):raise ValueError('WORD_FIELDS: say the sheet and the first and last day it is complete for')
        try:start, end = date.fromisoformat(args['from']), date.fromisoformat(args['to'])
        except ValueError:raise ValueError('WORD_DATE: a day is written as YYYY-MM-DD') from None
        if start > end:raise ValueError('WORD_DATE: the first day comes first')
        saved = _saved(args['sheet'])
        if not saved:raise ValueError('WORD_ROW_NOT_FOUND: that sheet cannot be read')
        sheet = _bind_sheet(saved);bound.append(sheet);subject = {'sheet': sheet['sheet']}
        value = {'from': args['from'], 'to': args['to']}
        statement = WORDS['complete'].format(title=sheet['title'], start=date_words(args['from']), end=date_words(args['to']))
        ident_key = ('COMPLETE', sheet['sheet'], args['from'], args['to'])
    elif sort == 'SAYS':
        if not args.get('words', '').strip():raise ValueError('WORD_FIELDS: say your account in your own words')
        words = ' '.join(args['words'].split())
        if args.get('goal'):
            goal, ident, key = _goal(kernel, principal, args['goal']);scope = 'goal';subject = {'goal': ident, 'goal_key': key}
        value = {'words': words};statement = WORDS['says'].format(words=words)
        ident_key = ('SAYS', scope, args.get('goal', ''), words.lower())
    else:
        if args.get('standing') not in STANDING_CHOICES:raise ValueError('WORD_FIELDS: a standing word names the standing choice')
        value = {'standing': args['standing']};statement = WORDS['standing'];ident_key = ('STANDING', args['standing'])
    fields = {'sort': sort, 'statement': statement, 'subject': subject, 'value': value, 'scope': scope, 'because': because, 'bound': bound,
              'set_by': 'owner', 'state': 'IN'}
    return records.digest(list(ident_key)), fields


def _all(db, principal):
    records.ensure(db)
    ids = [row[0] for row in db.execute('SELECT id FROM desk_records WHERE owner=? AND kind=? ORDER BY rowid', (principal.identity, KIND))]
    return [records.read(db, KIND, ident, principal) for ident in ids]


def put(kernel, args, principal):
    """The owner's press: say a word (a new record, or a new revision of the word about the same subject), or set one aside
    (OUT) and take it back (IN), each a new revision. Nothing is deleted."""
    if 'id' in args or 'state' in args or 'expected_revision' in args:
        if set(args) != {'id', 'expected_revision', 'state'}:raise ValueError('WORD_SET_FIELDS: set a word aside or back by its id, revision and IN or OUT alone')
        with kernel.db() as db:
            records.ensure(db)                          # begins the write transaction (BEGIN IMMEDIATE)
            value = records.read(db, KIND, args['id'], principal);expected = args['expected_revision']
            if value.get('state') == args['state']:raise ValueError('WORD_ALREADY_%s: the word is %s already' % (args['state'], 'aside' if args['state'] == 'OUT' else 'in'))
            records.edit(value, expected);value['state'] = args['state']
            return records.write(db, value, principal, 'WORD_SET_ASIDE' if args['state'] == 'OUT' else 'WORD_TAKEN_BACK', expected=expected)
    key, fields = _compose(kernel, principal, args)
    with kernel.db() as db:
        records.ensure(db)                              # begins the write transaction (BEGIN IMMEDIATE)
        old = next((w for w in _all(db, principal) if w.get('key') == key), None)
        if old is None:return records.write(db, records.new(KIND, principal, schema=SCHEMA, key=key, **fields), principal, 'WORD_SAID')
        expected = old['revision'];records.edit(old, expected);old.update(fields)
        return records.write(db, old, principal, 'WORD_SAID_AGAIN', expected=expected)


# ---- freshness, computed on read ------------------------------------------------------------------------------------------

def freshness(word, saved_of=None):
    """(CURRENT or RECONSIDER, [what changed, in words]): every row the word was said about, or rests on, held against the
    sheet as it stands; a sheet it covers as a whole, against its revision."""
    saved_of = saved_of or _saved;changed = []
    for bound in list(word.get('bound') or ()) + list(word.get('because') or ()):
        saved = saved_of(bound['sheet'])
        if 'cell' not in bound:
            if not saved or saved.get('revision') != bound['revision']:changed.append('“%s”' % bound['title'])
            continue
        now = _row_of(saved, bound['cell'])
        if not now or any(now[k] != bound[k] for k in ('parameter', 'value', 'unit', 'conditions')):
            changed.append('row %d of “%s”' % (row_number(bound['cell']), bound['title']))
    return (RECONSIDER if changed else CURRENT), changed


def standing(kernel, principal):
    """The words that are IN, each with its freshness: what her reasons may read. A sheet is read once per call."""
    with kernel.db() as db:said = [w for w in _all(db, principal) if w.get('state') == 'IN']
    cache = {}
    def saved_of(sheet):
        if sheet not in cache:cache[sheet] = _saved(sheet)
        return cache[sheet]
    out = []
    for w in said:
        fresh, changed = freshness(w, saved_of)
        out.append({**w, 'freshness': fresh, 'changed': changed})
    return out


def choice_for(words, goal, ident='', key=''):
    """Which alternative your word picks for this goal: (alternative ref, the word) or (None, None). A word to reconsider is
    not applied. A word about this goal comes first, then one for this desk, then the standing choice."""
    options = _alternatives_of(goal)
    if not options:return None, None
    live = [w for w in words if w.get('state') == 'IN' and w.get('freshness', CURRENT) == CURRENT]
    by_sheet = {a['sheet']: a for a in options}
    for w in live:
        if w['sort'] == 'CHOICE' and w['scope'] == 'goal' and ((ident and w['subject'].get('goal') == ident) or (key and w['subject'].get('goal_key') == key)):
            if w['value']['sheet'] in by_sheet:return by_sheet[w['value']['sheet']], w
    for w in live:
        if w['sort'] == 'CHOICE' and w['scope'] == 'desk' and w['value']['sheet'] in by_sheet and set(by_sheet) <= set(w['subject'].get('sheets') or ()):
            return by_sheet[w['value']['sheet']], w
    for w in live:
        if w['sort'] == 'STANDING' and w['value'].get('standing') == 'CURRENT_REVISION':
            found = marked_current(options)
            if found:return found, w
    return None, None


def about_goal(word, ident='', key=''):
    subject = word.get('subject') or {}
    return bool((ident and subject.get('goal') == ident) or (key and subject.get('goal_key') == key))


def dispatch(kernel, op, args, principal):
    from .office_service import owner
    owner(principal)                 # the sheets a word is said about live in the owner's profile, as for office.get
    if op == 'word.set':return {'word': put(kernel, args, principal), 'model_calls': 0}
    if op == 'word.list':
        rows = standing(kernel, principal) if not args.get('all') else None
        if rows is None:
            with kernel.db() as db:every = _all(db, principal)
            rows = []
            for w in every:
                fresh, changed = freshness(w);rows.append({**w, 'freshness': fresh, 'changed': changed})
        if args.get('about'):rows = [w for w in rows if about_goal(w, args['about'], args['about'])]
        return {'words': rows, 'shown': SHOWN, 'model_calls': 0}
    if op == 'word.get':
        with kernel.db() as db:
            records.ensure(db);value = records.read(db, KIND, args['id'], principal);history = records.history(db, value)
        fresh, changed = freshness(value)
        words = WORDS['fresh'] if fresh == CURRENT else WORDS['reconsider'].format(what=', '.join(changed))
        return {'word': value, 'freshness': fresh, 'changed': changed, 'words': words, 'history': history, 'model_calls': 0}
    raise ValueError('Unknown word operation')
