"""Everyday questions and the tidy of a folder, from the desk (Graphite 1.0 X3).

Found by the everyday walkthrough (X3): two ordinary requests of a household had no route at all. With no model she
answered "I have no brain running yet" to the second, and to the first she showed what the records say about the file,
not what was spent. Both are the desk's own work, so they need no model; with a model loaded they go the same way (the
model proposes, the desk disposes: here there is nothing for the model to propose).

  "what did we spend on groceries this month?"   (also "how much did we spend on … last month / in November")
        The spreadsheet is the one in focus when it is one, else the one spreadsheet in your Documents whose name says
        budget. It is read through the registered read tool (K2's tool 18, libreoffice.read: through LibreOffice where it is
        here, else its content.xml), so the read has its receipts (dispatched, then verified at the revision on disk). Its
        header row names the columns (Date, Category, Amount); the rows of that category in that month are summed exactly
        (Fraction over the decimal text the cells hold, never floating point). Her answer names the total, the rows, the
        sheet, the file and its revision, and the receipt.
  "tidy my Downloads folder: sort the files by type into folders"   (tidy, sort, organise, clean up)
        A verb of the desk's planner (K4's PLAN_VERBS hook): the folder is the one of your home your words name (or the one in
        focus); each file at its top is given a folder by its kind (PDFs, Pictures, Spreadsheets, Documents, Archives, Text,
        Music, Other, by the end of its name: a deduction, said as such); the plan is registered steps only, tool 7
        (files.folder.new) for each folder not there yet and tool 6 (files.move) for each file, under your grant
        ("rename, move and copy files and make folders" in that folder, this assignment). Each step is verified as K2 verifies
        it (the folder is there; the same content in the new place and gone from the old). At most MOST_FILES files.
  "put my Downloads folder back as it was"   (put … back, undo the tidy)
        The undo of the last tidy of that folder, from its journal: each verified move moved back, as a plan of tool 6 steps
        under the same kind of grant. The folders it made are left, empty, for you to delete from the tree (deleting is
        yours: DELETE keeps them).

Her words are fixed templates (WORDS, registered with mind_words); every number arrives through a slot that names its
record.
"""
from __future__ import annotations

import re
import threading
from datetime import date
from fractions import Fraction
from pathlib import Path

MONTHS = ('january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december')
SPENT = re.compile(r'^\s*(?:(?:kas|kasandra)\s*[,:]\s*)?(?:what|how\s+much)\s+(?:did|have|do)\s+(?:we|i)\s+(?:spend|spent)\s+on\s+'
                   r'(?P<what>[a-z][a-z \-]{1,40}?)\s+(?P<when>this\s+month|last\s+month|in\s+(?P<month>%s)(?:\s+(?P<year>\d{4}))?)\s*\??\s*$'
                   % '|'.join(MONTHS), re.I)
NUMBER = re.compile(r'^-?\d{1,12}(?:\.\d{1,6})?$')
TIDY = r'tidy(?:\s+up)?|sort\s+out|sort|organi[sz]e|clean\s+up'
PUT_BACK = r'put\s+(?:\S+\s+){0,4}?back|undo\s+the\s+(?:tidy|sort)'
MOST_FILES = 24               # files one tidy moves at most (a step each; K1 keeps at most 32 steps)
KINDS = (('PDFs', ('.pdf',)), ('Pictures', ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tif', '.tiff', '.heic', '.svg')),
         ('Spreadsheets', ('.ods', '.xlsx', '.xls', '.csv', '.tsv')), ('Documents', ('.odt', '.docx', '.doc', '.rtf', '.odp', '.pptx')),
         ('Archives', ('.zip', '.tar', '.gz', '.tgz', '.xz', '.bz2', '.7z', '.rar')), ('Text', ('.txt', '.md')),
         ('Music', ('.mp3', '.ogg', '.oga', '.flac', '.wav', '.m4a', '.opus')))
OTHER = 'Other'

WORDS = {
    'reading': 'I am reading “{file}” for {what} in {month}.',
    'spent': 'We spent {total} on {what} in {month}: {count} rows of the sheet “{sheet}” in “{file}” ({rows}), read at revision {revision}.',
    'none_spent': 'Nothing was spent on {what} in {month}. No row of the sheet “{sheet}” in “{file}” says so, read at revision {revision}.',
    'receipt': 'Receipt: {tool}, {object}, sheet {sheet}, revision {revision}, {complete}, {status}.',
    'no_budget': 'I found no spreadsheet to read for that. Put the budget in focus, or keep one spreadsheet named budget in Documents.',
    'two_budgets': 'Two spreadsheets could be meant, “{one}” and “{two}”: put the one you mean in focus and ask again.',
    'no_columns': 'The sheet “{sheet}” in “{file}” has no header row naming Date, Category and Amount. So I do not add it up.',
    'not_read': 'I could not read “{file}”: {why}',
    'odd_amount': 'Row {row} of “{sheet}” holds “{text}” as an amount, which is not a number, so I give no total.',
}
try:
    from . import mind_words
    mind_words.register('everyday_desk', WORDS, kind='sentence', numbers={'spent': {      # 1.1 KV: the sweep reads these now
        'total': 'the sum of the amounts read (the budget sheet)', 'count': 'the rows read (the budget sheet)',
        'rows': 'the rows read (the budget sheet)'}})
except Exception:  # noqa: BLE001 - the words stand without the check
    pass


def say(key, **slots):
    return WORDS[key].format(**slots)


# ---------------------------------------------------------------- the spending question
def month_of(match, today):
    """(year, month) the words name: this month, last month, or a month (of this year, or the year said)."""
    when = match.group('when').lower()
    if when.startswith('this'):return today.year, today.month
    if when.startswith('last'):return (today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)
    month = MONTHS.index(match.group('month').lower()) + 1
    year = int(match.group('year')) if match.group('year') else (today.year if month <= today.month else today.year - 1)
    return year, month


def month_words(year, month):
    return '%s %d' % (MONTHS[month - 1].capitalize(), year)


def _focused_path(host):
    living = getattr(host, 'living_nav', None)
    try:
        focus = living.nav.focus if living is not None else ''
        found = living.call('objects.get', {'id': focus}) if focus else None
        path = (found or {}).get('path') or (found or {}).get('abs') or ''
        return Path(path) if path and str(path).startswith('/') else None
    except Exception:  # noqa: BLE001 - no focus: the budget is looked for in Documents
        return None


def budget_for(host):
    """(path, '') of the spreadsheet to read, or (None, her words why not)."""
    from . import home_reach
    focus = _focused_path(host)
    if focus is not None and focus.suffix.lower() in ('.ods', '.xlsx', '.xls') and focus.is_file():return focus, ''
    docs = home_reach.home() / 'Documents'
    found = sorted(p for p in docs.glob('*') if p.is_file() and p.suffix.lower() in ('.ods', '.xlsx') and 'budget' in p.name.lower()) if docs.is_dir() else []
    if len(found) == 1:return found[0], ''
    if len(found) > 1:return None, say('two_budgets', one=found[0].name, two=found[1].name)
    return None, say('no_budget')


def _cell(ref):
    m = re.match(r'^([A-Z]{1,3})(\d{1,7})$', ref)
    return (m.group(1), int(m.group(2))) if m else (None, None)


ISO_DAY = re.compile(r'^(\d{4})-(\d{2})-(\d{2})')
SERIAL = re.compile(r'^(\d{1,6})(?:\.0+)?$')


def day_of(cell):
    """A date cell's day as YYYY-MM-DD: the date the file holds (office:date-value), or Calc's day number (days from
    30 December 1899, as LibreOffice gives a date cell's value), or ISO text; '' when it is none of these."""
    from datetime import timedelta
    number = cell.get('value') if cell.get('value') is not None else (cell.get('formula') if cell.get('type') == 'value' else None)
    for raw, may_be_number in ((cell.get('value'), False), (number, True), (cell.get('text'), False)):
        text = str(raw if raw is not None else '').strip()
        if ISO_DAY.match(text):return text[:10]
        m = SERIAL.match(text)
        if m and may_be_number:return (date(1899, 12, 30) + timedelta(days=int(m.group(1)))).isoformat()
    return ''


def add_up(cells, what, year, month):
    """From a sheet's cells ({ref: {text, value, type}}): {'total', 'rows', 'count', 'column'}, or {'why': key, ...}."""
    grid = {}
    for ref, cell in (cells or {}).items():
        col, row = _cell(ref)
        if col:grid.setdefault(row, {})[col] = cell
    head = None
    for row in sorted(grid)[:5]:
        names = {str(c.get('text') or '').strip().casefold(): col for col, c in grid[row].items()}
        if {'date', 'category', 'amount'} <= set(names):head = (row, names);break
    if head is None:return {'why': 'no_columns'}
    at, names = head
    want = what.strip().casefold()
    stem = want[:-1] if want.endswith('s') else want
    prefix = '%04d-%02d' % (year, month)
    total, rows = Fraction(0), []
    for row in sorted(r for r in grid if r > at):
        cells_ = grid[row]
        category = str((cells_.get(names['category']) or {}).get('text') or '').strip().casefold()
        if not category or not (category == want or category.rstrip('s') == stem or category.startswith(stem)):continue
        if not day_of(cells_.get(names['date']) or {}).startswith(prefix):continue
        amount = cells_.get(names['amount']) or {}
        held = amount.get('value') if amount.get('value') is not None else (amount.get('formula') if amount.get('type') == 'value' else None)
        text = str(held if held is not None and NUMBER.match(str(held).strip()) else amount.get('text') or '').strip().replace(',', '')
        if not NUMBER.match(text):return {'why': 'odd_amount', 'row': row, 'text': text[:40]}
        total += Fraction(text);rows.append(row)
    cents = total * 100
    if cents.denominator != 1:return {'why': 'odd_amount', 'row': rows[-1] if rows else at, 'text': str(total)}
    sign = '-' if cents < 0 else ''
    return {'total': '%s%d.%02d' % ((sign,) + divmod(abs(int(cents)), 100)), 'rows': rows, 'count': len(rows),
            'column': names['amount']}


def _rows_words(rows, column):
    if not rows:return 'no rows'
    runs, start = [], rows[0]
    for a, b in zip(rows, rows[1:] + [None]):
        if b != a + 1:runs.append('%s%d' % (column, start) if start == a else '%s%d:%s%d' % (column, start, column, a));start = b
    return 'cells ' + ', '.join(runs)


def answer_spent(kernel, principal, path, what, year, month):
    """The question worked out: {'words', 'receipt_words', 'total', 'receipts'} (the read through tool 18, with receipts)."""
    from . import home_reach
    shown = home_reach.tilde(path)
    used = kernel.dispatch('tools.use', {'number': 18, 'arguments': {'path': shown},
                                         'origins': {'path': {'kind': 'DEDUCTION', 'proof': 'the spreadsheet in focus, or the one budget in your Documents'}}},
                           principal)
    if not used.get('ok'):
        return {'words': say('not_read', file=path.name, why=str((used.get('error') or {}).get('message') or 'refused')[:200])}
    got = used['result']
    read = got.get('result') or {}
    if got.get('status') != 'verified' or not read.get('cells'):
        return {'words': say('not_read', file=path.name, why=str(got.get('words') or 'the read was not verified')[:200])}
    sheet = read.get('sheet') or ''
    if sheet.casefold() != 'spending' and 'Spending' in (read.get('sheets') or ()):      # a budget's spending sheet, when it has one
        again = kernel.dispatch('tools.use', {'number': 18, 'arguments': {'path': shown, 'sheet': 'Spending'},
                                              'origins': {'path': {'kind': 'DEDUCTION', 'proof': 'the same spreadsheet'}}}, principal)
        if again.get('ok') and again['result'].get('status') == 'verified':got = again['result'];read = got.get('result') or {};sheet = read.get('sheet') or sheet
    revision = str(read.get('revision') or '')[:12]
    summed = add_up(read.get('cells'), what, year, month)
    month_ = month_words(year, month)
    if 'why' in summed:
        return {'words': say(summed['why'], sheet=sheet, file=path.name, row=summed.get('row', ''), text=summed.get('text', ''))}
    key = 'spent' if summed['count'] else 'none_spent'
    words = say(key, total=summed['total'], what=what.strip(), month=month_, count=summed['count'], sheet=sheet, file=path.name,
                rows=_rows_words(summed['rows'], summed['column']), revision=revision)
    last = (got.get('receipts') or [{}])[-1]
    receipt = say('receipt', tool='%s (tool %s)' % (last.get('tool', ''), last.get('number', '')), object=last.get('object', ''), sheet=sheet,
                  revision=str(last.get('revision') or '')[:12], complete='complete' if last.get('complete') else 'partial',
                  status=last.get('status_words') or last.get('status', ''))
    return {'words': words, 'receipt_words': receipt, 'total': summed['total'], 'rows': summed['rows'], 'receipts': got.get('receipts') or []}


def asked(face, text):
    """Shell2's ask: True when the words are a spending question; the answer is worked off the window's thread."""
    m = SPENT.match(text or '')
    if not m:return False
    from PySide6.QtCore import QTimer
    from .engineering_kernel import Kernel, operator
    host = face.host
    path, why = budget_for(host)
    face.thing = None;face.mine(text)
    if path is None:
        face.say(why);return True
    year, month = month_of(m, date.today())
    what = m.group('what').strip()
    card = face.say(say('reading', file=path.name, what=what, month=month_words(year, month)))
    try:root = host.ledger_bridge.kernel.root
    except AttributeError:
        from .locations import default_root
        root = default_root()
    result = {}

    def work():
        try:result['answer'] = answer_spent(Kernel(root), operator(), path, what, year, month)
        except Exception as exc:  # noqa: BLE001 - said in her words, never raised into the window
            result['answer'] = {'words': say('not_read', file=path.name, why=str(exc)[:200])}
    face.her_reading = True      # 1.0 K10: her state word says WORKING while she reads for you (her work)
    thread = threading.Thread(target=work, name='her-everyday-read', daemon=True);thread.start()

    def done():
        if thread.is_alive():
            QTimer.singleShot(150, done);return
        face.her_reading = False      # 1.0 K10
        answer = result.get('answer') or {}
        words = answer.get('words', '') + ((' ' + answer['receipt_words']) if answer.get('receipt_words') else '')
        try:card.set_text(words)
        except Exception:  # noqa: BLE001 - the card went: said again
            face.say(words)
        face.last_everyday = answer
    QTimer.singleShot(150, done)
    return True


# ---------------------------------------------------------------- the tidy of a folder (K4's desk planner)
def kind_of(name):
    suffix = Path(name).suffix.lower()
    return next((folder for folder, ends in KINDS if suffix in ends), OTHER)


def folder_named(words, desk=None):
    """The folder of your home the words name ("my Downloads folder", "Downloads", "~/Downloads"), or None."""
    from . import home_reach
    home = home_reach.home()
    if not home.is_dir():return None
    names = {p.name.casefold(): p for p in home.iterdir() if p.is_dir() and not p.name.startswith('.')}
    for token in re.findall(r"[~/\w][\w .\-/]*", words or ''):
        for word in re.split(r'[\s/]+', token.strip()):
            hit = names.get(word.casefold().strip('~'))
            if hit is not None:return hit
    return None


def _span_of(objective, name):
    m = re.search(re.escape(name), objective, re.I)
    return {'kind': 'OWNER_WORDS', 'start': m.start(), 'end': m.end()} if m else None


def plan_tidy(b, clause, objective, desk, seen, thing):
    """PLAN_VERBS['tidy']: folders by kind and a move for each file at the folder's top (registered tools 7 and 6)."""
    from .objective_plan import Refusal
    folder = folder_named(clause.words) or folder_named(objective)
    if folder is None:raise Refusal('say which folder of your home: tidy my Downloads, for one')
    if any(getattr(s, 'tidied', None) == folder for s in seen):return None        # "tidy Downloads: sort the files …" is one tidy
    files = sorted((p for p in folder.iterdir() if p.is_file() and not p.name.startswith('.')), key=lambda p: p.name.casefold())
    if not files:raise Refusal('%s has no files at its top to sort' % folder.name)
    if len(files) > MOST_FILES:raise Refusal('%s has %d files at its top; I sort at most %d at a time' % (folder.name, len(files), MOST_FILES))
    from . import home_reach
    where = home_reach.tilde(folder)
    named = _span_of(objective, folder.name) or {'kind': 'DEDUCTION', 'proof': 'the folder in focus'}
    groups = {}
    for p in files:groups.setdefault(kind_of(p.name), []).append(p)
    if len(groups) == 1 and (folder / next(iter(groups))).is_dir():raise Refusal('everything in %s is already one kind' % folder.name)
    for kind, members in sorted(groups.items()):
        target = folder / kind
        if not target.exists():
            b.add({'key': b.key('folder_' + kind), 'title': 'Make the folder %s in %s' % (kind, where), 'operation': 'files.mkdir',
                   'tool_key': 'files.folder.new', 'arguments': {'path': str(folder), 'name': kind},
                   'origins': {'path': named, 'name': {'kind': 'DEDUCTION', 'proof': 'the kind of %d file(s) here, by the end of their names' % len(members)}},
                   'basis': 'owner_words', 'expected': 'the folder %s in %s' % (kind, where)})
        elif not target.is_dir():raise Refusal('%s in %s is a file, not a folder' % (kind, where))
        for p in members:
            b.add({'key': b.key('move_' + p.stem), 'title': 'Move %s into %s' % (p.name, kind), 'operation': 'files.move', 'tool_key': 'files.move',
                   'arguments': {'path': str(p), 'to': str(target)},
                   'origins': {'path': {'kind': 'DEDUCTION', 'proof': 'a file at the top of %s, listed now' % where},
                               'to': {'kind': 'DEDUCTION', 'proof': 'the folder for %s files (its name ends %s)' % (kind, p.suffix.lower() or 'with no ending')}},
                   'basis': 'owner_words', 'expected': '%s in %s/%s' % (p.name, where, kind)})
    return _Tidied(folder)


class _Tidied:
    """What a tidy clause was about, for the clauses after it (the same folder is not planned twice)."""
    handle = ''

    def __init__(self, folder):
        self.tidied = folder;self.handle = str(folder);self.kind = 'folder';self.title = folder.name


def _last_moves(desk, folder):
    """The verified moves of the last tidy of `folder`, from the journals: [(where it is now, where it was)]."""
    from .engineering_kernel import Kernel, operator
    from .locations import default_root
    kernel, principal = Kernel(default_root()), operator()
    listed = kernel.dispatch('assignment.list', {}, principal)
    rows = (listed.get('result') or {}).get('assignments') or [] if listed.get('ok') else []
    for row in sorted(rows, key=lambda r: -(r.get('created') or 0)):
        got = kernel.dispatch('assignment.status', {'id': row['id']}, principal)
        view = got.get('result') or {} if got.get('ok') else {}
        moves = []
        for step in view.get('steps') or ():
            a = step.get('inputs') or step.get('resolved') or step.get('arguments') or {}
            a = {k: (v.get('value') if isinstance(v, dict) and 'value' in v else v) for k, v in a.items()}
            if step.get('operation') == 'files.move' and step.get('status') == 'done' and str(a.get('to', '')).startswith(str(folder) + '/'):
                moves.append((Path(a['to']) / Path(a['path']).name, Path(a['path'])))
        if moves:return moves
    return []


def plan_put_back(b, clause, objective, desk, seen, thing):
    """PLAN_VERBS['put back']: each verified move of the last tidy of the folder, moved back (tool 6)."""
    from .objective_plan import Refusal
    folder = folder_named(clause.words) or folder_named(objective)
    if folder is None:raise Refusal('say which folder of your home to put back')
    moves = [(now, was) for now, was in _last_moves(desk, folder) if now.is_file() and not was.exists()]
    if not moves:raise Refusal('I find no tidy of %s to put back' % folder.name)
    for now, was in moves:
        b.add({'key': b.key('back_' + now.stem), 'title': 'Move %s back to %s' % (now.name, folder.name), 'operation': 'files.move',
               'tool_key': 'files.move', 'arguments': {'path': str(now), 'to': str(was.parent)},
               'origins': {'path': {'kind': 'DEDUCTION', 'proof': 'where the tidy put it, from its journal'},
                           'to': {'kind': 'DEDUCTION', 'proof': 'where it was before the tidy, from its journal'}},
               'basis': 'owner_words', 'expected': '%s back in %s' % (now.name, folder.name)})
    return _Tidied(folder)


def _install():
    """Her desk's planner learns the two verbs (K4's PLAN_VERBS hook, as K9's replace)."""
    try:
        from . import objective_plan as op
    except Exception:  # noqa: BLE001 - K4 is not in this Graphite
        return
    have = {v[0] for v in op.VERBS}
    more = tuple(v for v in (('put back', PUT_BACK, (6,), True), ('tidy', TIDY, (7, 6), True)) if v[0] not in have)
    if more:op.VERBS = more + tuple(op.VERBS)      # before 'read' and 'check': "put … back" holds no verb of theirs
    if hasattr(op, 'PLAN_VERBS'):op.PLAN_VERBS.update({'tidy': plan_tidy, 'put back': plan_put_back})


_install()
