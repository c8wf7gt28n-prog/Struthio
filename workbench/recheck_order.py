"""What this change did (0.8.6, "if there is room", lane B; the read side only).

After a sheet changes, one card sorts everything on the desk that stands on that sheet into three piles:

  carried over   with its proof: what it reads did not change ("reads rows 2 and 4, which did not change"), or it reads
                 nothing of the sheet and rests on sources that did not change
  worked again   a calculation that reads a row that changed, worked again here exactly with its own recipe (reads only:
                 whether its page on the desk already says the new result is said beside it, and nothing is written)
  needs you      what no rule here can carry: a finding or a page whose words still carry a number that moved ("needs
                 new words"), a check that reads a row that changed, a calculation that cannot be worked again

It also says what each change did to the goals over the sheet (goals.candidates and the kept goals): each goal's state
and its room at the worst case, before and now, and for each goal whose state changed, the cell that caused it, found by
putting one changed cell back at a time.

"Before" is the sheet as it was saved last time (the Office keeps every earlier version of a working copy), or the
values the caller gives (`before`: {cell: value}). Both sides are worked the same way, in memory: math_answers over the
cells, the owner's tolerances held against each side's own cells. The card is computed on read and never stored.

    field.change   {id, before?}   read   the card for one sheet ('office:…', or a calculation 'document:…', which stands
                                          for its sheet)

    change(kernel, principal, ident, before=None) -> the card (a dict; see change())

What always holds here: nothing writes a record (every read is a Kernel observer or a record's own read function), no
model is asked (model_calls: 0) and none is imported, and every number is an exact Fraction; no float.
"""
from __future__ import annotations

import copy
import json
import re
from fractions import Fraction

from .mind_types import FAILS, HOLDS, STATE_WORDS, UNDECIDED

SCHEMA = 'ledger.change-card/1'
CARRIED, WORKED, YOURS = 'CARRIED_OVER', 'WORKED_AGAIN', 'NEEDS_YOU'
PILES = (WORKED, YOURS, CARRIED)
PILE_WORDS = {CARRIED: 'carried over', WORKED: 'worked again', YOURS: 'needs you'}
COLUMNS = ('A', 'B', 'C', 'D')              # parameter, value, unit, conditions: the reviewed sheet's four columns
ROW_LIMIT = 999
DEPENDS = 'DEPENDS'

FIELDS = {
    'field.change': ({'id': {'type': 'string', 'minLength': 1, 'maxLength': 200}, 'before': {'type': 'object'}}, ['id']),
}
SCOPES = {op: 'read' for op in FIELDS}
OBSERVERS = tuple(FIELDS)

# Her words here: fixed templates, a number always with its record (design 3.6: no sentence over 30 words).
WORDS = {
    'heading': 'What this change did to “{sheet}”',
    'changed': 'Row {row} ({parameter}) changed from {was} to {now}.',
    'nothing_changed': 'Nothing on “{sheet}” changed since it was saved last.',
    'carried_reads': '“{title}” is carried over: it reads {rows}, which did not change.',
    'carried_check': '“{title}” is carried over: its check reads {rows}, which did not change{rests}.',
    'carried_rests': '“{title}” is carried over: it reads nothing of this sheet, and rests on {sources}, which did not change.',
    'carried_none': '“{title}” is carried over: it reads nothing of this sheet.',
    'rests_too': '; it rests on {sources}',
    'worked': '“{title}” worked again: {was}, now {now}, because {rows} changed.',
    'worked_same': '“{title}” worked again: still {now}, though {rows} changed.',
    'worked_kept': 'Its page already says {now}.',
    'worked_unkept': 'Its page still says {page}; Recheck keeps the new result.',
    'new_words': '“{title}” needs new words: it says {was}; it is now {now}.',
    'check_moved': '“{title}” needs you: its check reads {rows}, which changed. Run the check again.',
    'check_unread': '“{title}” needs you: its check reads this sheet, and I cannot tell which rows.',
    'source_moved': '“{title}” needs you: it rests on {sources}, which changed.',
    'not_worked': '“{title}” needs you: it reads {rows}, which changed, and it cannot be worked again here: {why}',
    'state_same': 'Nothing changes state.',
    'state_moved': '“{statement}”: {was}, now {now}, because of {cause}.',
    'cause_together': 'these rows together: {rows}',
    'room': '“{statement}”: the room at the worst case {verb} from {was} to {now}.',
    'room_note': 'Room left, not a safety factor; a share of the limit.',
    'nothing_here': 'Nothing on the desk stands on this sheet.',
}


# ========================================================================================================== the sheet

def _cells(document):
    return ((document or {}).get('sheets') or [{}])[0].get('cells') or {}


def _text(cells, key):
    return str((cells.get(key) or {}).get('value') or '').strip()


def _row_of(cell):
    found = re.fullmatch(r'[A-Z]{1,3}([1-9][0-9]{0,4})', str(cell).strip().upper())
    return int(found.group(1)) if found else None


def rows_words(rows):
    """'row 5', 'rows 2 and 4', 'rows 2, 3 and 4'."""
    rows = sorted(set(rows))
    if not rows:return 'no row'
    if len(rows) == 1:return 'row %d' % rows[0]
    return 'rows %s and %d' % (', '.join(str(r) for r in rows[:-1]), rows[-1])


def changed_rows(before, now):
    """The rows of a reviewed sheet that differ between two of its documents (any of parameter, value, unit, conditions):
    [{'row', 'cell' (its Value cell), 'parameter', 'was', 'now', 'unit_was', 'unit'}], in row order."""
    a, b = _cells(before), _cells(now);rows = set()
    for key in set(a) | set(b):
        row = _row_of(key)
        if row is not None and 1 < row <= ROW_LIMIT and key.rstrip('0123456789') in COLUMNS and (a.get(key) or {}).get('value') != (b.get(key) or {}).get('value'):
            rows.add(row)
    return [{'row': row, 'cell': 'B%d' % row, 'parameter': _text(b, 'A%d' % row) or _text(a, 'A%d' % row),
             'was': _text(a, 'B%d' % row), 'now': _text(b, 'B%d' % row), 'unit_was': _text(a, 'C%d' % row), 'unit': _text(b, 'C%d' % row)}
            for row in sorted(rows)]


def saved_versions(sheet, limit=256):
    """The sheet's earlier documents, newest first: [(version, document)]. A read of the Office's own history of the
    working copy (it keeps every earlier version, at most 256)."""
    from .office_service import store
    with store().catalog.db() as db:
        rows = db.execute('SELECT version, payload FROM office_history WHERE id=? ORDER BY version DESC LIMIT ?', (sheet, int(limit))).fetchall()
    return [(row[0], json.loads(row[1])) for row in rows]


def last_saved(sheet):
    """The sheet's document as it was saved last before now: (its version, the document), or (None, None) when it was
    never changed."""
    found = saved_versions(sheet, 1)
    return found[0] if found else (None, None)


def put_back(saved, changes, only=None):
    """A copy of the saved sheet with the changed rows put back as they were (all of them, or only the cells in `only`).
    In memory: nothing is saved."""
    back = copy.deepcopy(saved);cells = _cells(back.get('document'))
    for change in changes:
        if only is not None and change['cell'] not in only:continue
        for column, said in (('B', change['was']), ('C', change['unit_was'])):
            key = '%s%d' % (column, change['row'])
            if key in cells:cells[key] = {**cells[key], 'value': said}
            elif said:cells[key] = {'value': said}
    return back


def _with_before(saved, before):
    """The sheet with the values the caller gives in place (before: {cell: value}): the "before" side when it is given."""
    changes = []
    cells = _cells(saved.get('document'))
    for cell, value in sorted((before or {}).items()):
        cell = str(cell).strip().upper();row = _row_of(cell)
        if row is None or not cell.startswith('B') or 'B%d' % row != cell or cell not in cells:
            raise ValueError('CHANGE_CELL: %s is not a Value cell of this sheet' % str(cell)[:12])
        changes.append({'row': row, 'cell': cell, 'parameter': _text(cells, 'A%d' % row), 'was': str(value).strip(), 'now': _text(cells, cell),
                        'unit_was': _text(cells, 'C%d' % row), 'unit': _text(cells, 'C%d' % row)})
    return [c for c in changes if c['was'] != c['now']]


# ========================================================================================================== working out

def _quantity_words(value, unit):
    from .math_answers import figure
    return figure(value, unit)


def _amount(value, unit):
    """An exact amount as she says it: '3.6 W', '0.9375 W (15/16 W)'."""
    from .math_answers import figure
    said = figure(value, unit)
    if Fraction(value).denominator != 1 and '(exact' not in said:said += ' (%s %s)' % (Fraction(value), unit) if unit else ' (%s)' % Fraction(value)
    return said


def work(calculation, saved):
    """A calculation worked exactly with its own recipe over the sheet as `saved` holds it: (Fraction, unit, '') or
    (None, '', why it could not be)."""
    from . import math_answers as answers, tolerances
    from .math_ranges import RangeError
    from .math_units import rational
    cells = {}
    for item in calculation['inputs']:
        cell = tolerances.sheet_cell(saved, item['cell'])
        if not cell:return None, '', '%s is no longer on the sheet' % item['cell']
        cells[item['symbol']] = cell
    try:ir, inputs = answers.bindings_from_cells(calculation['expression'], cells, None, stage='calculate')
    except (RangeError, ValueError) as exc:return None, '', answers.plain(getattr(exc, 'code', 'UNSUPPORTED'), str(exc))
    found = answers.answer('calculate', ir, inputs, {'expression': calculation['expression'], 'unit': calculation['unit'] or None})
    value = (found.get('result') or {}).get('value')
    if not value:return None, '', answers.plain(found.get('state'), found.get('reason'))
    return rational(value['rational']), value['unit'], ''


def _earlier_results(kernel, principal, ident, hops=50):
    """The results the pages a calculation's standing page replaces said, newest first: [(Fraction, unit)]. How the desk
    notices a finding that still quotes a result from before an earlier change, as the Field does."""
    from .math_units import rational
    out = [];seen = set()
    answer = kernel.dispatch('documents.get', {'id': ident}, principal)
    ident = (((answer.get('result') or {}).get('document') or {}).get('derivation') or {}).get('replaces') if answer.get('ok') else None
    while ident and ident not in seen and len(seen) < hops:
        seen.add(ident)
        answer = kernel.dispatch('documents.get', {'id': ident}, principal)
        if not answer.get('ok'):break
        derivation = (answer['result'].get('document') or {}).get('derivation') or {}
        value = (((derivation.get('calculation') or {}).get('outputs') or [{}])[0] or {}).get('value') or {}
        try:out.append((rational(value['rational']), value.get('unit') or ''))
        except (KeyError, ValueError):pass
        ident = derivation.get('replaces')
    return out


def _page_result(kernel, principal, ident):
    """What a calculation's page on the desk says: (Fraction, unit, the inputs it was worked from {cell: value}) or None."""
    answer = kernel.dispatch('documents.get', {'id': ident}, principal)
    if not answer.get('ok'):return None
    from .math_units import rational
    derivation = (answer['result'].get('document') or {}).get('derivation') or {}
    value = (((derivation.get('calculation') or {}).get('outputs') or [{}])[0] or {}).get('value') or {}
    try:said = rational(value['rational'])
    except (KeyError, ValueError):return None
    return said, value.get('unit') or '', {str(i.get('cell')): str(i.get('value')) for i in derivation.get('inputs') or ()}


class _Said:
    """The owner's tolerances on cells, held against one side's sheets (the side's own cells decide APPLIES or RECHECK)."""

    def __init__(self, kernel, principal):
        from . import tolerances
        with kernel.db() as db:self.records = [t for t in tolerances._all(db, principal) if 'cell' in t['subject']]

    def against(self, saved_of):
        from . import tolerances
        found = {}
        for t in self.records:
            saved = saved_of(t['subject']['sheet'])
            found[(t['subject']['address'], t['subject']['cell'])] = {'id': t['id'], 'revision': t['revision'], 'state': tolerances.cell_state(t, saved),
                                                                      'lo': t['lo'], 'hi': t['hi'], 'said': t['said'], 'unit': t['unit']}
        return found


def judge(goal, saved_of, said, fresh='CURRENT'):
    """A relation goal judged under every way the desk knows (as goals.judge does), over the sheets `saved_of` gives:
    {'state' (the ways' common state, or DEPENDS), 'ways': [{'choice', 'state', 'room': (lo, hi) or None}], 'worst': the
    least room over the ways (a Fraction) or None, 'unit'}. In memory; the same code works both sides of a change."""
    from . import goals, math_answers as answers, tolerances
    from .math_ranges import RangeError
    from .math_units import rational
    ways, _ = goals._ways(goal);rows = []
    for choice in ways:
        bound = {**goal['cells'], **choice};cells = {};missing = False
        for symbol, ref in bound.items():
            saved = saved_of(ref['sheet'])
            cell = tolerances.sheet_cell(saved, ref['cell']) if saved else None
            if not cell or cell['parameter'] != ref['parameter']:missing = True;break
            cells[symbol] = cell
        state = 'MISSING_INPUT';room = None;unit = ''
        if not missing:
            try:ir, inputs = answers.bindings_from_cells(goal['expression'], cells, said, roles=goal.get('roles'))
            except (RangeError, ValueError) as exc:state = getattr(exc, 'code', 'UNSUPPORTED')
            else:
                found = answers.answer('check', ir, inputs, {'expression': goal['expression']}, fresh)
                state = found['state'];slack = (found.get('result') or {}).get('slack')
                if slack:
                    lo, hi = rational(slack[0]['rational']), rational(slack[1]['rational']);unit = slack[0]['unit']
                    room = (lo, hi) if goal['relation'] in ('le', 'lt') else (-hi, -lo)
        rows.append({'choice': {s: c['title'] for s, c in choice.items()}, 'state': state, 'room': room, 'unit': unit})
    states = {row['state'] for row in rows}
    rooms = [row['room'][0] for row in rows if row['room'] is not None]
    return {'state': rows[0]['state'] if len(states) == 1 else DEPENDS, 'ways': rows, 'worst': min(rooms) if rooms else None,
            'unit': next((row['unit'] for row in rows if row['unit']), '')}


def _state_words(state):
    if state == DEPENDS:return 'depends on which revision applies'
    return STATE_WORDS.get(state, 'cannot tell')


# ========================================================================================================== the card

class _Desk:
    """What one card reads, each once: the sheets, the calculations, the investigations, the pages and the goals."""

    def __init__(self, kernel, principal):
        self.kernel, self.principal = kernel, principal;self._saved = {}

    def call(self, operation, arguments=None):
        answer = self.kernel.dispatch(operation, arguments or {}, self.principal)
        if not answer.get('ok'):raise ValueError('%s could not be read: %s' % (operation, str((answer.get('error') or {}).get('message', ''))[:160]))
        return answer['result']

    def saved(self, sheet):
        if sheet not in self._saved:
            from .office_service import store
            try:self._saved[sheet] = store().get(sheet)
            except (ValueError, OSError, KeyError):self._saved[sheet] = None
        return self._saved[sheet]

    def name(self, address):
        """A source's name as the desk shows it: an admitted item's file name, a sheet's title; the address otherwise."""
        kind, _, ident = str(address).partition(':')
        try:
            if kind == 'intake':return str(self.call('intake.item', {'id': ident}).get('name') or address)
            if kind == 'office':return str((self.saved(ident) or {}).get('document', {}).get('title') or address)
        except ValueError:pass
        return str(address)

    def claims(self):
        """Every claim of every investigation with what it stands on: [(claim, its steps, investigation)]. The steps are its
        evidence path (investigation.path) and its checks as the investigation holds them (each as a CHECK step with its
        program), so a check counts whether or not it has run yet."""
        found = []
        for row in self.call('investigation.list').get('investigations', ()):
            sheet = self.call('investigation.sheet', {'id': row['id']})
            seen = {}
            for claim in list(sheet.get('unresolved') or ()) + list(sheet.get('learned') or ()):
                seen.setdefault(claim['id'], claim)
            checks = {}
            for check in sheet.get('checked') or ():
                checks.setdefault(check.get('claim'), []).append({'kind': 'CHECK', 'program': str(check.get('program') or ''), 'outcome': check.get('last_outcome')})
            for claim in seen.values():
                path = (self.call('investigation.path', {'claim': claim['id']}) or {}).get('path') or ()
                found.append((claim, list(path) + checks.get(claim['id'], []), row['id']))
        return found

    def pages(self):
        """The plain pages of the desk (not calculations): [(id, title, text)]."""
        from . import documents
        out = [];offset = 0
        while True:
            some = list(self.call('documents.list', {'limit': 100, 'offset': offset}).get('documents', ()))
            for row in some:
                doc = self.call('documents.get', {'id': row['id']}).get('document') or {}
                if doc.get('derivation'):continue
                out.append((row['id'], doc.get('title') or row.get('title') or '', documents.plain_text(doc)))
            offset += len(some)
            if len(some) < 100:break
        return out


def _check_rows(program, sheet, cells):
    """The rows of `sheet` a check's program reads, by the parameters it names; None when it reads the sheet and the rows
    cannot be told."""
    if ('@office:' + sheet) not in program and ('office:' + sheet) not in program:return set()
    names = [m.group(2).strip().lower() for m in re.finditer(r'where\s+parameter\s*=\s*("?)([^|"]+)\1', program)]
    if not names:return None
    rows = set()
    for name in names:
        hit = [_row_of(key) for key, cell in cells.items() if key.startswith('A') and str(cell.get('value') or '').strip().lower() == name]
        if not hit:return None
        rows.update(hit)
    return rows


def _sources_words(titles):
    titles = sorted(set(titles))
    if not titles:return 'nothing'
    return titles[0] if len(titles) == 1 else '%s and %s' % (', '.join(titles[:-1]), titles[-1])


def _sheet_of(desk, ident):
    ident = str(ident).strip()
    if ident.startswith('document:'):
        doc = desk.call('documents.get', {'id': ident.split(':', 1)[1]}).get('document') or {}
        sheet = (doc.get('derivation') or {}).get('sheet')
        if not sheet:raise ValueError('CHANGE_NOT_A_SHEET: that page was not worked from a sheet')
        return sheet
    return ident[len('office:'):] if ident.startswith('office:') else ident


def change(kernel, principal, ident, before=None):
    """The card "What this change did" for one sheet. Returns {'schema', 'sheet': {id, title, version}, 'since': 'last
    save' or 'the values you gave', 'changes': changed_rows(), 'worked_again', 'needs_you', 'carried_over': [{'id',
    'kind' (calculation, finding, page), 'title', 'pile', 'rows' (what it reads of the sheet), 'because' (the changed
    rows that put it there), 'words', and for a calculation 'was', 'now', 'unit', 'kept'}], 'goals': [{'statement', 'key',
    'was', 'now', 'changed', 'cause', 'room': {'was', 'now', 'unit'}, 'words'}], 'changed_state': n, 'lines': her words,
    'writes': 0, 'model_calls': 0}. Nothing is written."""
    from . import goals as goal_face
    from .field_model import carries
    desk = _Desk(kernel, principal);sheet = _sheet_of(desk, ident);now = desk.saved(sheet)
    if now is None:raise ValueError('CHANGE_NOT_A_SHEET: no sheet of your Office has that id')
    title = (now.get('document') or {}).get('title') or sheet
    if before:
        changes = _with_before(now, before);since = 'the values you gave'
    else:
        version, earlier = last_saved(sheet);since = 'last save'
        changes = changed_rows(earlier, now.get('document')) if earlier else []
    then = put_back(now, changes)
    def side(saved):
        return lambda s: saved if s == sheet else desk.saved(s)
    moved_rows = {c['row'] for c in changes};by_row = {c['row']: c for c in changes}
    cells = _cells(now.get('document'))
    items = [];moved_words = []
    earlier = saved_versions(sheet) if changes else []
    for c in changes:                       # the changed cell itself, as a number with its unit, is words that moved: what it
        now_words = ('%s %s' % (c['now'], c['unit'])).strip()    # said last time and in every earlier version of the sheet
        for value, unit in [(c['was'], c['unit_was'])] + [(_text(_cells(doc), c['cell']), _text(_cells(doc), 'C%d' % c['row'])) for _, doc in earlier]:
            said = ('%s %s' % (value, unit)).strip()
            if value and c['now'] and said != now_words and (said, now_words) not in moved_words:moved_words.append((said, now_words))
    # 1. the calculations of the sheet that stand now
    for calc in goal_face._calculations(kernel, principal) if changes else ():
        if calc['sheet'] != sheet:continue
        reads = {_row_of(i['cell']) for i in calc['inputs']} - {None};hit = sorted(reads & moved_rows)
        name = re.split(r'\s+·\s+', calc['title'])[0]
        item = {'id': 'document:' + calc['id'], 'kind': 'calculation', 'title': name, 'rows': sorted(reads), 'because': hit}
        if not hit:
            item.update(pile=CARRIED, words=WORDS['carried_reads'].format(title=name, rows=rows_words(reads)))
            items.append(item);continue
        was, unit_was, why_was = work(calc, then)
        is_, unit, why = work(calc, now)
        if is_ is None:
            item.update(pile=YOURS, words=WORDS['not_worked'].format(title=name, rows=rows_words(hit), why=why))
            items.append(item);continue
        page = _page_result(kernel, principal, calc['id'])
        kept = page is not None and page[0] == is_ and page[1] == unit
        said_now = _quantity_words(is_, unit);said_was = _quantity_words(was, unit_was) if was is not None else ''
        words = (WORDS['worked'] if was is not None and (was, unit_was) != (is_, unit) else WORDS['worked_same']).format(
            title=name, was=said_was, now=said_now, rows=rows_words(hit))
        words += ' ' + (WORDS['worked_kept'].format(now=said_now) if kept else WORDS['worked_unkept'].format(
            page=_quantity_words(page[0], page[1]) if page else 'nothing I can read'))
        item.update(pile=WORKED, words=words, was=str(was) if was is not None else None, now=str(is_), unit=unit, kept=kept)
        items.append(item)
        if said_was and said_was != said_now:moved_words.append((said_was, said_now))
        if page and not kept:moved_words.append((_quantity_words(page[0], page[1]), said_now))
        for old, old_unit in _earlier_results(kernel, principal, calc['id']):      # what it said before an earlier change
            if _quantity_words(old, old_unit) != said_now:moved_words.append((_quantity_words(old, old_unit), said_now))
    # 2. the findings: those of an investigation that watches the sheet (a check or a source step reads it), and any
    #    finding whose words carry a number that moved
    claims = desk.claims() if changes else []
    watching = {inv for claim, path, inv in claims for step in path
                if ('office:' + sheet) in (str(step.get('address') or '') + ' ' + str(step.get('program') or '') + ' ' + ' '.join(map(str, step.get('inputs') or ())))}
    for claim, path, inv in claims:
        if str(claim.get('role', '')).upper() == 'QUESTION':continue
        text = claim.get('text') or claim['id'];stale = [(w, n) for w, n in moved_words if carries(text, w) and not carries(text, n)]
        if inv not in watching and not stale:continue
        item = {'id': 'claim:' + claim['id'], 'kind': 'finding', 'title': text, 'rows': [], 'because': []}
        if stale:
            item.update(pile=YOURS, words=WORDS['new_words'].format(title=text, was=stale[0][0], now=stale[0][1]),
                        says=stale[0][0], now_says=stale[0][1])
            items.append(item);continue
        read = set();unread = False;sources = [];moved_sources = []
        for step in path:
            if str(step.get('kind')).upper() == 'CHECK':
                rows = _check_rows(' '.join([str(step.get('program') or '')] + ['@' + str(a).lstrip('@') for a in step.get('inputs') or ()]), sheet, cells)
                if rows is None:unread = True
                else:read |= rows
            elif str(step.get('kind')).upper() == 'SOURCE' and step.get('address'):
                address = str(step['address']).lstrip('@')
                if address == 'office:' + sheet:unread = True;continue
                label = desk.name(address)
                from .field_source import source_word
                from .field_model import STATE_RECHECK
                (moved_sources if step.get('counts') is False or source_word(step.get('source_state')) == STATE_RECHECK else sources).append(str(label))
        hit = sorted(read & moved_rows);item['rows'] = sorted(read);item['because'] = hit
        if unread:item.update(pile=YOURS, words=WORDS['check_unread'].format(title=text))
        elif hit:item.update(pile=YOURS, words=WORDS['check_moved'].format(title=text, rows=rows_words(hit)))
        elif moved_sources:item.update(pile=YOURS, words=WORDS['source_moved'].format(title=text, sources=_sources_words(moved_sources)))
        elif read:item.update(pile=CARRIED, words=WORDS['carried_check'].format(
            title=text, rows=rows_words(read), rests=WORDS['rests_too'].format(sources=_sources_words(sources)) if sources else ''))
        elif sources:item.update(pile=CARRIED, words=WORDS['carried_rests'].format(title=text, sources=_sources_words(sources)))
        else:item.update(pile=CARRIED, words=WORDS['carried_none'].format(title=text))
        items.append(item)
    # 3. the plain pages whose words carry a number that moved
    for ident_, page_title, text in desk.pages() if moved_words else ():
        stale = [(w, n) for w, n in moved_words if carries(text, w) and not carries(text, n)]
        if stale:
            items.append({'id': 'document:' + ident_, 'kind': 'page', 'title': page_title, 'rows': [], 'because': [], 'pile': YOURS,
                          'says': stale[0][0], 'now_says': stale[0][1],
                          'words': WORDS['new_words'].format(title=page_title, was=', '.join(w for w, _ in stale), now=', '.join(n for _, n in stale))})
    # 4. the goals over the sheet: state and room, before and now, and the cell that caused each change of state
    said = _Said(kernel, principal);said_now = said.against(side(now));said_then = said.against(side(then))
    kept = {g.get('key'): g for g in goal_face._records(kernel, principal) if g.get('state') == 'IN'}
    goal_list = [dict(kept.get(c['key'], c)) for c in goal_face.candidates(kernel, principal)]
    goal_list += [g for k, g in kept.items() if k not in {c['key'] for c in goal_list}]
    fresh = goal_face._freshness(kernel, principal, now)
    goal_rows = []
    for goal in goal_list if changes else ():
        refs = list(goal['cells'].values()) + [a for alts in (goal.get('alternatives') or {}).values() for a in alts]
        if not any(ref['sheet'] == sheet for ref in refs):continue
        reads = sorted({_row_of(ref['cell']) for ref in refs if ref['sheet'] == sheet} - {None})
        a, b = judge(goal, side(then), said_then, fresh), judge(goal, side(now), said_now, fresh)
        row = {'statement': goal['statement'], 'key': goal.get('key'), 'goal': goal.get('id'), 'rows': reads,
               'was': a['state'], 'now': b['state'], 'changed': a['state'] != b['state'], 'cause': [],
               'room': {'was': str(a['worst']) if a['worst'] is not None else None, 'now': str(b['worst']) if b['worst'] is not None else None,
                        'unit': b['unit'] or a['unit']}, 'words': ''}
        if row['changed']:
            for c in changes:              # put one changed cell back: the one that brings the old state back is the cause
                one = put_back(now, changes, only={c['cell']})
                if judge(goal, side(one), said.against(side(one)), fresh)['state'] == a['state']:row['cause'].append(c['cell'])
            cause = row['cause'] or [c['cell'] for c in changes if c['row'] in reads]
            cause_words = ('row %d (%s)' % (by_row[_row_of(cause[0])]['row'], by_row[_row_of(cause[0])]['parameter'])) if len(cause) == 1 and _row_of(cause[0]) in by_row \
                else WORDS['cause_together'].format(rows=rows_words([_row_of(x) for x in cause]))
            row['cause'] = cause
            row['words'] = WORDS['state_moved'].format(statement=goal['statement'], was=_state_words(a['state']), now=_state_words(b['state']), cause=cause_words)
        elif a['worst'] is not None and b['worst'] is not None and a['worst'] != b['worst']:
            row['words'] = WORDS['room'].format(statement=goal['statement'], verb='falls' if b['worst'] < a['worst'] else 'rises',
                                                was=_amount(a['worst'], row['room']['unit']), now=_amount(b['worst'], row['room']['unit']))
        goal_rows.append(row)
    # her words: the change, the three piles, the states, the room
    lines = [WORDS['heading'].format(sheet=title)]
    lines += [WORDS['changed'].format(row=c['row'], parameter=c['parameter'] or 'a row', was=('%s %s' % (c['was'], c['unit_was'])).strip() or 'nothing',
                                      now=('%s %s' % (c['now'], c['unit'])).strip() or 'nothing') for c in changes] or [WORDS['nothing_changed'].format(sheet=title)]
    piles = {pile: [i for i in items if i['pile'] == pile] for pile in PILES}
    for pile in PILES:
        lines += [i['words'] for i in piles[pile]]
    if changes and not items and not goal_rows:lines.append(WORDS['nothing_here'])
    moved_states = [r for r in goal_rows if r['changed']]
    if changes and goal_rows:
        lines += [r['words'] for r in moved_states] or [WORDS['state_same']]
        rooms = [r['words'] for r in goal_rows if not r['changed'] and r['words']]
        lines += rooms + ([WORDS['room_note']] if rooms else [])
    return {'schema': SCHEMA, 'sheet': {'id': sheet, 'title': title, 'revision': now.get('revision')}, 'since': since, 'changes': changes,
            'worked_again': piles[WORKED], 'needs_you': piles[YOURS], 'carried_over': piles[CARRIED], 'goals': goal_rows,
            'changed_state': len(moved_states), 'lines': lines, 'writes': 0, 'model_calls': 0}


def dispatch(kernel, op, args, principal):
    from .office_service import owner
    owner(principal)                 # the sheets live in the owner's profile, as for office.get
    if op == 'field.change':
        before = args.get('before')
        if before is not None and (not isinstance(before, dict) or len(before) > 64 or any(len(str(v)) > 40 for v in before.values())):
            raise ValueError('CHANGE_BEFORE: give at most 64 cells, each with a value of at most 40 characters')
        return change(kernel, principal, args['id'], before)
    raise ValueError('Unknown change operation')
