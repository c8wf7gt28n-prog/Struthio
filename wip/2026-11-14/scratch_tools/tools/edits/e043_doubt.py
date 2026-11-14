import io
p = '/home/user/Struthio/workbench/field_doubt.py'
t = io.open(p, encoding='utf8').read()
def rep(old, new, count=1):
    global t
    assert t.count(old) == count, (t.count(old), old[:70])
    t = t.replace(old, new)

rep('''import json
import re
from dataclasses import dataclass
''', '''import json
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
''')

rep('''def _same(a, b):
    return a is not None and b is not None and abs(a - b) <= 1e-9 * max(1.0, abs(a), abs(b))
''', '''def _same(a, b):
    return a is not None and b is not None and abs(a - b) <= 1e-9 * max(1.0, abs(a), abs(b))


def _plain(number):
    """A number as it is written on a sheet: 110, 3.36, never 110.0."""
    return ('%.10f' % number).rstrip('0').rstrip('.') if number != int(number) else str(int(number))


QUANTITY = re.compile(r'(?<![\\w.])(-?\\d+(?:\\.\\d+)?)\\s*([A-Za-zµΩ°%]+)')


class _Once:
    """One look at each record for one pass: the same read is not made twice. Every read here is a read, so the answers
    cannot change between two rules of the same pass."""
    def __init__(self, kernel):
        self.kernel = kernel;self.seen = {}

    def dispatch(self, operation, arguments, principal):
        key = (operation, json.dumps(arguments, sort_keys=True, default=str))
        if key not in self.seen:self.seen[key] = self.kernel.dispatch(operation, arguments, principal)
        return self.seen[key]
''')

# ---- sheets: counted twice, and another sheet that says otherwise ----------------------------------------------------------
rep('''    rows = origin.get('reviewed_rows') or []
    if not rows:
        return out + [Doubt('note', 'cells as reviewed', 'this sheet was not reviewed from a page, so there is nothing to compare its cells with')]
    cells = ((got.get('document') or {}).get('sheets') or [{}])[0].get('cells') or {}
''', '''    rows = origin.get('reviewed_rows') or []
    cells = ((got.get('document') or {}).get('sheets') or [{}])[0].get('cells') or {}
    out += _counted_twice(ident, cells)
    if not rows:
        return out + [Doubt('note', 'cells as reviewed', 'this sheet was not reviewed from a page, so there is nothing to compare its cells with')]
    out += _said_otherwise(kernel, principal, obj, field, rows, cells)
''')

rep('''# ---- a finding ------------------------------------------------------------------------------------------------------------
def _quantities(kernel, principal, field):''', '''def _decimal(text):
    try:
        value = Decimal(str(text).strip().replace(',', ''))
    except (InvalidOperation, ValueError):
        return None
    return value if value.is_finite() else None


def _counted_twice(ident, cells):
    """A total that adds a subtotal together with the rows the subtotal already adds (situation 07 of the owner's
    specification). Decided by arithmetic on the numbers as they stand, so it holds for typed values and for formula results
    alike: in one column, a cell that equals the rows above it added up, among which another cell equals the rows above *it*.
    When that inner cell's own row says total or sum, it is a doubt; when it does not say, it could be chance, and is named."""
    columns = {}
    for name, held in cells.items():
        found = re.fullmatch(r'([A-Z]+)(\\d+)', str(name))
        value = _decimal((held or {}).get('value')) if found and str((held or {}).get('type') or 'number') != 'text' else None
        if value is not None:columns.setdefault(found.group(1), {})[int(found.group(2))] = value
    label = lambda row: next((str((cells.get('%s%d' % (column, row)) or {}).get('value') or '').strip() for column in ('A', 'B', 'C')
                              if str((cells.get('%s%d' % (column, row)) or {}).get('type') or '') == 'text'
                              and str((cells.get('%s%d' % (column, row)) or {}).get('value') or '').strip()), '')
    out = []
    for column, numbers in sorted(columns.items()):
        rows = sorted(numbers);run = []
        for row in rows + [None]:
            if run and (row is None or row != run[-1] + 1):
                out += _twice_in_run(ident, column, run, numbers, label);run = []
            if row is not None:run.append(row)
    return out[:4]


def _twice_in_run(ident, column, run, numbers, label):
    out = []
    for t in range(3, len(run)):
        total = numbers[run[t]]
        if not total:continue
        start = next((s for s in range(0, t - 2) if sum(numbers[run[k]] for k in range(s, t)) == total), None)
        if start is None:continue
        for u in range(start + 2, t):
            inner = numbers[run[u]]
            first = next((s for s in range(start, u - 1) if inner and sum(numbers[run[k]] for k in range(s, u)) == inner), None)
            if first is None:continue
            at = lambda k: '%s%d' % (column, run[k])
            name = lambda k: (' (%s)' % label(run[k])[:40]) if label(run[k]) else ''
            without = total - inner
            said = '%s%s adds %s to %s, and %s%s is already %s to %s added up: those rows are counted twice. Without %s the total is %s, not %s' % (
                at(t), name(t), at(start), at(t - 1), at(u), name(u), at(first), at(u - 1), at(u), _plain_decimal(without), _plain_decimal(total))
            involved = ','.join('cells.%s.value' % at(k) for k in range(start, t + 1))[:400]
            see = '@office:%s | pick document.sheets | select %s' % (ident, involved)
            named = any(word in label(run[u]).lower() for word in ('total', 'sum', 'subtotal'))
            out.append(Doubt('doubt' if named else 'cannot tell', 'counted twice',
                             said if named else said.replace(': those rows are counted twice.', '. If %s is a subtotal, those rows are counted twice.' % at(u)), see))
            break
    return out


def _plain_decimal(value):
    text = format(value.normalize(), 'f') if value == value.to_integral_value() else format(value, 'f').rstrip('0').rstrip('.')
    return text or '0'


def _said_otherwise(kernel, principal, obj, field, rows, cells):
    """The same parameter, by its name, on another sheet of the desk with another value or another unit (situation 16: the
    part that fits and runs at a different voltage). Two revisions may rightly differ, so this is a note: whatever uses the
    parameter has to say which sheet it means."""
    mine = {}
    for row in rows:
        at = row.get('sheet_row');name = str((cells.get('A%s' % at) or {}).get('value') or '').strip()
        if name:mine[name.lower()] = (name, str((cells.get('B%s' % at) or {}).get('value') or '').strip(), str((cells.get('C%s' % at) or {}).get('value') or '').strip(), at)
    out = []
    for other in (field.objects if field is not None else ()):
        target = other.target if isinstance(other.target, dict) else {}
        if other.kind != 'sheet' or other.id == obj.id or not target.get('id'):continue
        got = _read(kernel, principal, 'office.get', {'id': target['id']}) or {}
        theirs = ((got.get('document') or {}).get('sheets') or [{}])[0].get('cells') or {}
        for row in (got.get('origin') or {}).get('reviewed_rows') or ():
            at = row.get('sheet_row');name = str((theirs.get('A%s' % at) or {}).get('value') or '').strip().lower()
            if name not in mine:continue
            value = str((theirs.get('B%s' % at) or {}).get('value') or '').strip();unit = str((theirs.get('C%s' % at) or {}).get('value') or '').strip()
            said, here, here_unit, here_at = mine[name]
            if (value, unit) != (here, here_unit) and not (unit == here_unit and _same(_number(value), _number(here))):
                out.append(Doubt('note', 'another sheet differs', '%s is %s %s here (B%s) and %s %s on “%s” (B%s); whatever uses it has to say which sheet it means' % (
                    said, here, here_unit, here_at, value, unit, other.title, at), '@office:%s | pick document.sheets | select cells.A%s.value,cells.B%s.value,cells.C%s.value' % (target['id'], at, at, at)))
    return out[:4]


# ---- a finding ------------------------------------------------------------------------------------------------------------
def _made_from(number, unit, desk_values):
    """A number that is on no sheet may still be two of the desk's values put together: one less the other, or the two
    added. Same unit only, exact, the first pair in the desk's own order. -> the words for it, or ''."""
    held = desk_values.get(unit) or ()
    if not number:return ''
    for a, where_a in held:
        for b, where_b in held:
            if where_a != where_b and a > b and _same(a - b, number):
                return '%s %s (%s) less %s %s (%s)' % (_plain(a), unit, where_a, _plain(b), unit, where_b)
    for index, (a, where_a) in enumerate(held):
        for b, where_b in held[index + 1:]:
            if where_a != where_b and _same(a + b, number):
                return '%s %s (%s) and %s %s (%s) together' % (_plain(a), unit, where_a, _plain(b), unit, where_b)
    return ''


def _quantities(kernel, principal, field):''')

rep('''    for value, unit in re.findall(r'(?<![\\w.])(-?\\d+(?:\\.\\d+)?)\\s*([A-Za-zµΩ°%]+)', str(obj.title)):
        if unit not in desk_values:continue                   # not a quantity in a unit this desk uses (a name, a revision letter)
        places = [where for number, where in desk_values[unit] if _same(number, _number(value))]
        if places:
            out.append(Doubt('holds', 'its numbers', '%s %s is %s' % (value, unit, places[0] + (' and %d more' % (len(places) - 1) if len(places) > 1 else '')), 'field.read | pick objects | select kind,title'))
        else:
            out.append(Doubt('cannot tell', 'its numbers', '%s %s is not a value on any sheet nor the result of any calculation on the desk; if it was worked out, the working is not recorded' % (value, unit),
                             'field.read | pick objects | where kind=calculation | select title,state'))
    return out
''', '''    for value, unit in QUANTITY.findall(str(obj.title)):
        if unit not in desk_values:continue                   # not a quantity in a unit this desk uses (a name, a revision letter)
        places = [where for number, where in desk_values[unit] if _same(number, _number(value))]
        if places:
            out.append(Doubt('holds', 'its numbers', '%s %s is %s' % (value, unit, places[0] + (' and %d more' % (len(places) - 1) if len(places) > 1 else '')), 'field.read | pick objects | select kind,title'))
        else:
            out.append(_unplaced(value, unit, desk_values))
    return out


def _unplaced(value, unit, desk_values):
    """A quantity in the words that is no value on the desk: either it is two of the desk's values put together (said, as a
    note: the working is still not recorded), or where it comes from cannot be told."""
    made = _made_from(_number(value), unit, desk_values);see = 'field.read | pick objects | where kind=calculation | select title,state'
    if made:
        return Doubt('note', 'its numbers', '%s %s is on no sheet, but it is %s. If that is how it was worked out, no calculation records it' % (value, unit, made), see)
    return Doubt('cannot tell', 'its numbers', '%s %s is not a value on any sheet nor the result of any calculation on the desk; if it was worked out, the working is not recorded' % (value, unit), see)


# ---- a page ---------------------------------------------------------------------------------------------------------------
def _page(kernel, principal, obj, field):
    """A page of words: every quantity it says, against the desk. What a calculation has since given differently is a doubt;
    what is on no sheet is named; the rest is said once, together."""
    ident = obj.target['id'];got = _read(kernel, principal, 'documents.get', {'id': ident})
    if not got:
        return [Doubt('cannot tell', 'the page', 'it cannot be read now')]
    text = str(got.get('plain') or '');out = [];see = 'documents.get %s | pick document.blocks | select text' % _js(id=ident)
    from .field_brief import standing
    out += standing(kernel, principal, got, field)
    for was, now, name in field.moved:
        if was in text and now not in text:
            out.append(Doubt('doubt', 'its numbers', 'its words say %s; “%s” now gives %s' % (was, name, now), 'field.read | pick moved | select was,now,calculation'))
    desk_values = _quantities(kernel, principal, field);held = [];seen = set()
    for value, unit in QUANTITY.findall(text):
        if unit not in desk_values or (value, unit) in seen:continue
        seen.add((value, unit))
        if any(_same(number, _number(value)) for number, _ in desk_values[unit]):held.append('%s %s' % (value, unit))
        else:out.append(_unplaced(value, unit, desk_values))
    if held:
        out.append(Doubt('holds', 'its numbers', '%d of the quantities it says are values on the desk: %s' % (len(held), ', '.join(held[:14]) + (' …' if len(held) > 14 else '')), see))
    if not seen and not out:
        out.append(Doubt('note', 'its numbers', 'it says no quantity in a unit the desk uses, so there is nothing of its words to hold against the sheets', see))
    return out
''')

rep('''    for value, unit in re.findall(r'(?<![\\w.])(-?\\d+(?:\\.\\d+)?)\\s*([A-Za-zµΩ°%]+)', str(obj.title)):
        for other in field.objects:''', '''    for value, unit in QUANTITY.findall(str(obj.title)):
        for other in field.objects:''')

rep('''BY_KIND = {'calculation': _calculation, 'sheet': _sheet, 'finding': _claim, 'condition': _condition, 'source': _source}
''', '''BY_KIND = {'calculation': _calculation, 'sheet': _sheet, 'finding': _claim, 'condition': _condition, 'source': _source, 'document': _page}
''')

rep('''    """Every doubt and every cannot-tell on the desk: [(object, Doubt)], doubts first."""
    out = []
    for obj in field.objects:''', '''    """Every doubt and every cannot-tell on the desk: [(object, Doubt)], doubts first."""
    out = [];kernel = _Once(kernel)
    for obj in field.objects:''')
io.open(p, 'w', encoding='utf8').write(t)
print('ok')
