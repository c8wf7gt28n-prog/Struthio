"""What a plausible result may hide (no Qt).

The owner's whole-build specification gives every situation a "difficult variation": the footnote that qualifies a rating,
the subtotal counted with its own rows, the check that looks at the wrong thing. Those are traps a result can pass straight
over while looking right. This module is Stacy's way of looking for them. For one object of the Field it puts a fixed set
of exact questions to the records and returns what it found, worst first:

    doubt         the records show something that does not hold
    cannot tell   the records do not say; it stays open, named
    note          worth knowing, neither good nor bad
    holds         the question was put and the records answer it

No model is asked and nothing is changed. Each row carries a staC line (`see`) that shows the evidence, so a doubt can be
checked by the owner the same way everything Stacy reads can. The rules are plain and few; add one here when a new trap is
met, with the line that shows it.

    doubts_for(kernel, principal, obj, field)   the rows for one object
    desk(kernel, principal, field)              every doubt and every cannot-tell on the desk
"""
import json
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from .field_model import carries

ORDER = {'doubt': 0, 'cannot tell': 1, 'note': 2, 'holds': 3}
GENERAL = ('both', 'all ', 'any ', 'always', 'every', 'throughout')      # a condition that covers the others


@dataclass
class Doubt:
    verdict: str
    about: str          # the question that was put, in two or three words
    why: str            # what the records say, with the values
    see: str = ''       # a staC line that shows it


def _js(**arguments):
    return json.dumps(arguments, ensure_ascii=False, separators=(',', ':'))


def _read(kernel, principal, operation, arguments):
    try:
        answer = kernel.dispatch(operation, arguments, principal)
    except Exception:  # noqa: BLE001 - a record that cannot be read is a "cannot tell", never a crash
        return None
    return answer['result'] if answer.get('ok') else None


def _number(text):
    try:
        return float(str(text).strip())
    except (TypeError, ValueError):
        return None


def _quantity(text):
    """'3.36 W' -> (3.36, 'W'), or None."""
    found = re.fullmatch(r'\s*(-?\d+(?:\.\d+)?)\s*(\S+)\s*', str(text or ''))
    return (float(found.group(1)), found.group(2)) if found else None


def _same(a, b):
    """Two numbers that are the same number, allowing only for how a float holds a decimal. The allowance is relative: in
    base units 1 nA and 2 nA are small numbers and still different ones."""
    return a is not None and b is not None and (a == b or abs(a - b) <= 1e-9 * max(abs(a), abs(b)))


def _plain(number):
    """A number as it is written on a sheet: 110, 3.36, never 110.0."""
    return ('%.10f' % number).rstrip('0').rstrip('.') if number != int(number) else str(int(number))


QUANTITY = re.compile(r'(?<![\w.])(-?\d+(?:\.\d+)?)\s*([A-Za-zµΩ°%]+)')


def measure(value, unit):
    """A written quantity in its base unit: (the kind of quantity, the number in its base unit), so 280 mA and 0.28 A are
    one thing and 3.36 mW is not 3.36 W. The Kernel's exact unit table decides where it knows the unit; the page-level
    table (workbench/quantities.py) decides the spellings and the kinds the Kernel does not carry. A unit neither knows
    stays as written, and then only the same spelling matches."""
    number = _number(value);unit = str(unit or '').strip()
    if number is None or not unit:return unit, number
    try:
        from . import math_units
        dimension, factor = math_units.unit_spec(unit)
        return str(math_units.dimension_name(dimension)), number * float(factor)
    except Exception:  # noqa: BLE001 - not a spelling the Kernel carries: the page-level table is asked next
        pass
    try:
        from . import math_units, quantities
        spec = quantities.resolve(unit)
        if not spec:return unit, number
        factor = float(spec.get('factor') or 1)
        if spec.get('kernel_unit'):factor *= float(math_units.unit_spec(spec['kernel_unit'])[1])
        return str(spec.get('dimension') or spec.get('base_unit') or unit), number * factor
    except Exception:  # noqa: BLE001 - an odd token is not a unit; it is compared as written
        return unit, number


def said_quantities(text):
    """Every number with a unit in a piece of writing, in order, once each: [(the number as written, the unit as written,
    the base unit, the number there)]. "3,360 mW" is 3360 mW; a time, a date and a page number are not quantities."""
    out = [];seen = set()
    try:
        from . import quantities
        rows = quantities.extract(str(text or ''))
    except Exception:  # noqa: BLE001
        rows = []
    for row in rows:
        if not row.get('unit') or (row['value'], row['unit']) in seen:continue
        seen.add((row['value'], row['unit']))
        base, scaled = measure(row['value'], row['unit'])
        if scaled is not None:out.append((row['value'], row['unit'], base, scaled))
    return out


def unit_of(cells, cell):
    """The unit a cell's number is in: the cell's own, or the unit column of its row on a reviewed sheet."""
    held = cells.get(cell) or {}
    if str(held.get('unit') or '').strip():return str(held['unit']).strip()
    found = re.fullmatch(r'([A-Z]+)(\d+)', str(cell))
    return str((cells.get('C' + found.group(2)) or {}).get('value') or '').strip() if found and found.group(1) == 'B' else ''


class _Once:
    """One look at each record for one pass: the same read is not made twice. Every read here is a read, so the answers
    cannot change between two rules of the same pass."""
    def __init__(self, kernel):
        self.kernel = kernel;self.seen = {}

    def dispatch(self, operation, arguments, principal):
        key = (operation, json.dumps(arguments, sort_keys=True, default=str))
        if key not in self.seen:self.seen[key] = self.kernel.dispatch(operation, arguments, principal)
        return self.seen[key]

    def __getattr__(self, name):               # whatever else is asked of it (its workspace, its store) is the Kernel's own
        return getattr(self.kernel, name)


# ---- a calculation --------------------------------------------------------------------------------------------------------
def _calculation(kernel, principal, obj, field):
    ident = obj.target['id'];got = _read(kernel, principal, 'documents.get', {'id': ident})
    if not got:
        return [Doubt('cannot tell', 'the calculation', 'its page cannot be read now')]
    out = [];document = got.get('document') or {};derivation = document.get('derivation') or {};inputs = derivation.get('inputs') or []
    state = (got.get('source_state') or {}).get('state')
    agrees = 'documents.get %s | pick source_state | select state' % _js(id=ident)
    if state == 'CURRENT':out.append(Doubt('holds', 'agrees with its sheet', 'it was worked out from the sheet as the sheet is now', agrees))
    elif state == 'RECHECK_SHEET_CHANGED':out.append(Doubt('doubt', 'agrees with its sheet', 'its sheet was changed after this was worked out', agrees))
    elif state == 'PDF_SOURCE_REVIEW_REQUIRED':out.append(Doubt('doubt', 'agrees with its sheet', 'the source of its sheet was decided again; the sheet has to be reviewed from its page first', agrees))
    else:out.append(Doubt('cannot tell', 'agrees with its sheet', 'its sheet cannot be reached', agrees))
    see = 'documents.get %s | pick document.derivation.inputs | select symbol,cell,value,unit,conditions,basis' % _js(id=ident)
    # 1. an input that is no longer what the source page said
    edited = [i for i in inputs if i.get('basis') != 'REVIEWED_PDF_ROW']
    for i in edited:
        was = i.get('original_cells') or []
        said = ('the reviewed page said %s %s' % (was[1], was[2])) if len(was) >= 3 else 'it was changed after it was reviewed from the page'
        out.append(Doubt('doubt', 'inputs as the page says', '%s (%s) is %s %s on the working sheet; %s' % (i.get('cell'), i.get('parameter') or i.get('symbol'), i.get('value'), i.get('unit'), said), see))
    if inputs and not edited:
        out.append(Doubt('holds', 'inputs as the page says', 'every input is the value that was reviewed from the source page', see))
    # 2. inputs read under different conditions
    named = [(i.get('symbol'), str(i.get('conditions') or '').strip()) for i in inputs]
    for symbol, words in named:
        if not words:out.append(Doubt('cannot tell', 'conditions', '%s has no condition recorded: when and how it was measured is not said' % symbol, see))
    specific = sorted({words.lower() for _, words in named if words and not any(mark in words.lower() + ' ' for mark in GENERAL)})
    if len(specific) > 1:
        out.append(Doubt('doubt', 'conditions', 'its inputs were read under different conditions: ' + '; '.join('%s “%s”' % pair for pair in named if pair[1]), see))
    elif named and all(words for _, words in named):
        out.append(Doubt('holds', 'conditions', 'its inputs go together: ' + '; '.join('%s “%s”' % pair for pair in named), see))
    # 3. what the result leans on: a 1 % move in each input, worked exactly with the page's own recipe
    try:
        from . import datasheet_work
        base = _quantity(datasheet_work.what_if(document, {inputs[0]['cell']: str(inputs[0]['value'])})['would_be']) if inputs else None
        leans = []
        for i in inputs:
            value = _number(i.get('value'))
            if base is None or not base[0] or value is None or not value:continue
            moved = _quantity(datasheet_work.what_if(document, {i['cell']: repr(value * 1.01)})['would_be'])
            if moved:leans.append((i['symbol'], (moved[0] - base[0]) / base[0] * 100.0))
        if leans:
            said = ', '.join('%s %+.2g %%' % (symbol, change) for symbol, change in sorted(leans, key=lambda pair: -abs(pair[1])))
            out.append(Doubt('note', 'what it leans on', 'a 1 %% rise in an input moves the result by: %s' % said,
                             'field.whatif %s | select says_now,would_be,set' % _js(id='document:' + ident, set={inputs[0]['cell']: repr((_number(inputs[0]['value']) or 0) * 1.01)})))
    except (ValueError, KeyError, TypeError, IndexError, ZeroDivisionError):
        pass
    return out


# ---- a reviewed sheet -----------------------------------------------------------------------------------------------------
def _sheet(kernel, principal, obj, field):
    ident = obj.target['id'];got = _read(kernel, principal, 'office.get', {'id': ident})
    if not got:
        return [Doubt('cannot tell', 'the sheet', 'it cannot be read now')]
    out = [];origin = got.get('origin') or {};state = (got.get('source_state') or {}).get('state')
    stands = 'office.get %s | select source_state.state' % _js(id=ident)
    if state and (state.startswith('CURRENT') or state == 'UNCHANGED_ORIGINAL'):
        out.append(Doubt('holds', 'its source', 'the source it was %s stands as it did' % ('reviewed from' if origin.get('reviewed_rows') else 'brought in from'), stands))
    elif state and state.endswith('UNAVAILABLE'):
        out.append(Doubt('cannot tell', 'its source', 'the file it was brought in from cannot be reached now, so whether it still agrees is not known', stands))
    elif state:out.append(Doubt('doubt', 'its source', 'its source was decided again or changed after this sheet was made (%s)' % state.replace('_', ' ').lower(), stands))
    rows = origin.get('reviewed_rows') or []
    cells = ((got.get('document') or {}).get('sheets') or [{}])[0].get('cells') or {}
    out += _counted_twice(ident, cells)
    if str(got.get('formula_values') or '') and any((held or {}).get('formula') for held in cells.values()) and any(d.about == 'counted twice' for d in out):
        out.append(Doubt('note', 'counted twice', 'the numbers of the formula cells are the ones the file kept; Graphite has not worked the formulas again', stands))
    if not rows:
        return out + [Doubt('note', 'cells as reviewed', 'this sheet was not reviewed from a page, so there is nothing to compare its cells with')]
    out += _said_otherwise(kernel, principal, obj, field, rows, cells)
    see = 'office.get %s | pick origin.reviewed_rows | select sheet_row,parameter,value,unit,conditions' % _js(id=ident)
    changed = 0
    for row in rows:
        at = row.get('sheet_row')
        for column, key, name in (('A', 'parameter', 'its name'), ('B', 'value', 'its value'), ('C', 'unit', 'its unit'), ('D', 'conditions', 'its conditions')):
            now = str((cells.get('%s%s' % (column, at)) or {}).get('value') or '').strip();was = str(row.get(key) or '').strip()
            if now != was:
                changed += 1
                out.append(Doubt('doubt', 'cells as reviewed', '%s%s (%s, %s): the page said “%s”, the sheet says “%s”' % (column, at, row.get('parameter') or '', name, was, now),
                                 '@office:%s | pick document.sheets | select cells.%s%s.value' % (ident, column, at)))
        if row.get('ocr_uncertain'):
            out.append(Doubt('cannot tell', 'read from the page', 'row %s (%s) was read from an image and the reading was not certain' % (at, row.get('parameter') or ''), see))
        if not str(row.get('unit') or '').strip():
            out.append(Doubt('cannot tell', 'units', 'row %s (%s) has no unit' % (at, row.get('parameter') or ''), see))
        if not str(row.get('conditions') or '').strip():
            out.append(Doubt('cannot tell', 'conditions', 'row %s (%s) has no condition recorded' % (at, row.get('parameter') or ''), see))
    if not changed:
        out.append(Doubt('holds', 'cells as reviewed', 'all %d reviewed rows are as they were read from the page' % len(rows), see))
    return out


def _decimal(text):
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
        found = re.fullmatch(r'([A-Z]+)(\d+)', str(name))
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
                out += _twice_in_run(ident, column, run, numbers, label, lambda row, column=column: unit_of(cells, '%s%d' % (column, row)));run = []
            if row is not None:run.append(row)
    return out[:4]


def _twice_in_run(ident, column, run, numbers, label, units):
    out = []
    for t in range(3, len(run)):
        total = numbers[run[t]]
        if not total:continue
        start = next((s for s in range(0, t - 2) if sum(numbers[run[k]] for k in range(s, t)) == total), None)
        if start is None:continue
        if len({units(run[k]) for k in range(start, t + 1)}) > 1:continue      # volts and amperes that happen to add up are not a total
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
            mine_base, mine_scaled = measure(here, here_unit);their_base, their_scaled = measure(value, unit)
            if _number(value) is None or _number(here) is None:
                if (value, unit) == (here, here_unit):continue
            elif mine_base == their_base and _same(mine_scaled, their_scaled):continue        # 280 mA here and 0.28 A there are the same thing
            out.append(Doubt('note', 'another sheet differs', '%s is %s %s here (B%s) and %s %s on “%s” (B%s); whatever uses it has to say which sheet it means' % (
                said, here, here_unit, here_at, value, unit, other.title, at), '@office:%s | pick document.sheets | select cells.A%s.value,cells.B%s.value,cells.C%s.value' % (target['id'], at, at, at)))
    return out[:4]


# ---- a finding ------------------------------------------------------------------------------------------------------------
def _made_from(scaled, base, desk_values):
    """A number that is on no sheet may still be two of the desk's values put together: one less the other, or the two
    added. Same kind of quantity only, exact, the first pair in the desk's own order. -> the words for it, or ''."""
    held = desk_values.get(base) or ()
    if not scaled:return ''
    for a, where_a, said_a in held:
        for b, where_b, said_b in held:
            if where_a != where_b and a > b and _same(a - b, scaled):
                return '%s (%s) less %s (%s)' % (said_a, where_a, said_b, where_b)
    for index, (a, where_a, said_a) in enumerate(held):
        for b, where_b, said_b in held[index + 1:]:
            if where_a != where_b and _same(a + b, scaled):
                return '%s (%s) and %s (%s) together' % (said_a, where_a, said_b, where_b)
    return ''


def _quantities(kernel, principal, field):
    """Every value with a unit that the desk holds: the reviewed rows of its sheets and the results of its calculations.
    -> {base unit: [(the number in that unit, where it is, as it is written there)]}"""
    found = {}
    for obj in field.objects:
        target = obj.target if isinstance(obj.target, dict) else {}
        if obj.kind == 'sheet' and target.get('id'):
            got = _read(kernel, principal, 'office.get', {'id': target['id']}) or {}
            cells = ((got.get('document') or {}).get('sheets') or [{}])[0].get('cells') or {}
            for row in (got.get('origin') or {}).get('reviewed_rows') or ():
                at = row.get('sheet_row');value = _number((cells.get('B%s' % at) or {}).get('value'));unit = str((cells.get('C%s' % at) or {}).get('value') or '').strip()
                if value is not None and unit:
                    base, scaled = measure(value, unit)
                    found.setdefault(base, []).append((scaled, '“%s” B%s (%s)' % (obj.title, at, row.get('parameter') or ''), '%s %s' % (_plain(value), unit)))
        elif obj.kind == 'calculation' and target.get('id'):
            got = _read(kernel, principal, 'documents.get', {'id': target['id']}) or {}
            value = (((((got.get('document') or {}).get('derivation') or {}).get('calculation') or {}).get('outputs') or [{}])[0] or {}).get('value') or {}
            if _number(value.get('decimal')) is not None and value.get('unit'):
                base, scaled = measure(value['decimal'], value['unit'])
                found.setdefault(base, []).append((scaled, 'the result of “%s”' % obj.title, '%s %s' % (value['decimal'], value['unit'])))
    return found


def _claim(kernel, principal, obj, field):
    inv = obj.target.get('id');claim = obj.id.split(':', 1)[1] if obj.id.startswith('claim:') else None
    if obj.kind != 'finding' or not inv or not claim:
        return []
    out = [];path = _read(kernel, principal, 'investigation.path', {'claim': claim});sheet = _read(kernel, principal, 'investigation.sheet', {'id': inv}) or {}
    why = 'investigation.path %s | pick path | select kind,address,direction,source_state,outcome' % _js(claim=claim)
    if path is None:
        out.append(Doubt('cannot tell', 'what it stands on', 'what it stands on cannot be read now', why))
    else:
        support = int(path.get('independent_support') or 0);against = int(path.get('independent_opposition') or 0)
        if against:out.append(Doubt('doubt', 'what it stands on', '%d independent source%s speak%s against it' % (against, '' if against == 1 else 's', 's' if against == 1 else ''), why))
        if support == 0:out.append(Doubt('doubt', 'what it stands on', 'nothing that counts supports it yet', why))
        elif support == 1:out.append(Doubt('doubt', 'what it stands on', 'only one independent source supports it', why))
        else:out.append(Doubt('holds', 'what it stands on', '%d independent sources support it' % support, why))
        if path.get('review') == 'NEEDS_REVIEW' or any(step.get('counts') is False for step in path.get('path', ())):
            out.append(Doubt('doubt', 'what it stands on', 'something it stands on changed since it was recorded', why))
    # its checks: is there one, did it pass, and could it fail at all
    checks = [c for c in sheet.get('checked', ()) if c.get('claim') == claim]
    listed = 'investigation.sheet %s | pick checked | select claim_text,program,expect,value,last_outcome' % _js(id=inv)
    if not checks:
        out.append(Doubt('cannot tell', 'a check', 'no check says what would show it true; it is recorded, not checked', listed))
    sound = [c for c in checks if weak_check(kernel, principal, c) is None]
    for check in checks:
        program = str(check.get('program') or '');weak = weak_check(kernel, principal, check)
        if weak:
            said, narrow, cell = weak
            if sound:      # an older check that cannot fail does no harm beside one that can; it cannot be removed, so it is only named
                out.append(Doubt('note', 'a check that can fail', 'an older check of it cannot fail (%s); a narrower one stands beside it' % said.split(',')[0], listed))
            else:
                out.append(Doubt('doubt', 'a check that can fail', said + ('. A check narrowed to cell %s could fail' % cell if cell else ''), narrow or listed))
        elif check.get('last_outcome') == 'PASSED':
            out.append(Doubt('holds', 'a check', 'its check passed: %s' % (check.get('oracle') or program)[:160], listed))
        elif check.get('last_outcome') == 'CHECK_FAILED':
            out.append(Doubt('doubt', 'a check', 'its check failed: %s' % (check.get('oracle') or program)[:160], listed))
        else:
            out.append(Doubt('cannot tell', 'a check', 'its check has not been run on things as they are now (%s)' % str(check.get('last_outcome') or '').replace('_', ' ').lower(), listed))
    # the numbers it says: are they anywhere on the desk
    for was, now, name in field.moved:
        if carries(obj.title, was) and not carries(obj.title, now):
            out.append(Doubt('doubt', 'its numbers', 'its words say %s; “%s” now gives %s' % (was, name, now), 'field.read | pick moved | select was,now,calculation'))
    for check in checks:                      # a check that reads a page a newer page took the place of goes on passing on the old one
        gone = next((ident for ident in getattr(field, 'replaced', ()) if ident and ident in str(check.get('program') or '')), None)
        if gone:
            out.append(Doubt('doubt', 'a check that can fail', 'its check reads a calculation page that has since been worked again; it goes on reading the old page and would pass whatever the new one gives', listed))
    desk_values = _quantities(kernel, principal, field)
    for value, unit, base, scaled in said_quantities(obj.title):
        placed = _placed(value, unit, base, scaled, desk_values)
        if placed is not None:out.append(placed)
    return out


def _placed(value, unit, base, scaled, desk_values):
    """One quantity from someone's words, against the desk: it is a value there (holds), it has the digits of a value there
    under another unit (a doubt: the slip of a prefix), it is two values put together (a note), or it is nowhere (cannot
    tell). None when the desk measures nothing of that kind (a name, a count)."""
    if base not in desk_values:return None
    see = 'field.read | pick objects | select kind,title'
    places = [(where, said) for number, where, said in desk_values[base] if _same(number, scaled)]
    if places:
        where, said = places[0];same_words = said.replace(' ', '') == ('%s%s' % (_plain(_number(value)), unit)).replace(' ', '')
        return Doubt('holds', 'its numbers', '%s %s is %s%s%s' % (value, unit, '' if same_words else 'the same as %s, ' % said, where, ' and %d more' % (len(places) - 1) if len(places) > 1 else ''), see)
    slip = next(((where, said) for number, where, said in desk_values[base] if _same(_number(said.split(' ')[0]), _number(value))), None)
    if slip:
        return Doubt('doubt', 'its numbers', 'its words say %s %s; %s is %s: the same digits under another unit' % (value, unit, slip[0], slip[1]), see)
    return _unplaced(value, unit, base, scaled, desk_values)


def _unplaced(value, unit, base, scaled, desk_values):
    """A quantity in the words that is no value on the desk: either it is two of the desk's values put together (said, as a
    note: the working is still not recorded), or where it comes from cannot be told."""
    made = _made_from(scaled, base, desk_values);see = 'field.read | pick objects | where kind=calculation | select title,state'
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
    mine = standing(kernel, principal, got, field)
    if mine:return mine                       # a kept brief only repeats the desk's own lines: what there is to ask of it is whether the desk is still that desk
    for was, now, name in field.moved:
        if carries(text, was) and not carries(text, now):
            out.append(Doubt('doubt', 'its numbers', 'its words say %s; “%s” now gives %s' % (was, name, now), 'field.read | pick moved | select was,now,calculation'))
    desk_values = _quantities(kernel, principal, field);held = [];seen = set()
    for value, unit, base, scaled in said_quantities(text):
        placed = _placed(value, unit, base, scaled, desk_values)
        if placed is None:continue
        seen.add((value, unit))
        if placed.verdict == 'holds':held.append('%s %s' % (value, unit))
        else:out.append(placed)
    if held:
        out.append(Doubt('holds', 'its numbers', '%d of the quantities it says are values on the desk: %s' % (len(held), ', '.join(held[:14]) + (' …' if len(held) > 14 else '')), see))
    if not seen and not out:
        out.append(Doubt('note', 'its numbers', 'it says no quantity in a unit the desk uses, so there is nothing of its words to hold against the sheets', see))
    return out


def weak_check(kernel, principal, check):
    """A check that cannot fail, or None. Two ways are known. It looks for words in a whole record: a reviewed sheet's record
    also keeps the words as they were first reviewed, so the words are found whatever the cell says now. Or the words it
    looks for are in its own line, and the answer it is matched against carries that line. Returns (why, a narrowed line or
    '', the cell that line reads or '')."""
    program = str(check.get('program') or '');value = str(check.get('value') or '');expect = check.get('expect')
    whole = expect in ('CONTAINS', 'NOT_CONTAINS') and ' | ' not in program
    if not whole and not (expect == 'CONTAINS' and value and value.lower() in program.lower()):
        return None
    said = ('its check looks for “%s” in the whole record, which also keeps the words as they were first reviewed, so it passes even if the cell is changed' % value
            if whole else 'its check looks for “%s”, and those words are in the check’s own line, so it passes by itself' % value)
    if program.startswith('@office:'):
        got = _read(kernel, principal, 'office.get', {'id': program[len('@office:'):]}) or {}
        cells = ((got.get('document') or {}).get('sheets') or [{}])[0].get('cells') or {}
        cell = next((name for name, held in cells.items() if str(held.get('value') or '').strip() == value), None)
        if cell:
            return said, '%s | pick document.sheets | select cells.%s.value' % (program, cell), cell
    return said, '', ''


def quoted_calculation(kernel, principal, obj, field):
    """The calculation on the desk whose result a finding's words carry: (the calculation's object, the decimal as written,
    the unit), or None. A match of the number and its unit, as _claim's own "its numbers" row is."""
    for value, unit in QUANTITY.findall(str(obj.title)):
        for other in field.objects:
            if other.kind != 'calculation' or not isinstance(other.target, dict):continue
            got = _read(kernel, principal, 'documents.get', {'id': other.target.get('id')}) or {}
            result = (((((got.get('document') or {}).get('derivation') or {}).get('calculation') or {}).get('outputs') or [{}])[0] or {}).get('value') or {}
            if result.get('unit') == unit and _same(_number(result.get('decimal')), _number(value)):
                return other, str(result['decimal']), unit
    return None


def _condition(kernel, principal, obj, field):
    ident = obj.id.split(':', 1)[1];got = (_read(kernel, principal, 'conditions.get', {'id': ident}) or {}).get('condition') or {}
    see = 'conditions.get %s | pick condition | select state,reason,result' % _js(id=ident)
    if got.get('state') == 'CURRENT':return [Doubt('holds', 'the total', 'it still adds up from the words on the page', see)]
    if got.get('state'):return [Doubt('doubt', 'the total', str(got.get('reason') or 'the page changed under it'), see)]
    return [Doubt('cannot tell', 'the total', 'it cannot be read now', see)]


def _source(kernel, principal, obj, field):
    fed = [field.get(link.target) for link in field.feeds(obj.id)]
    out = [Doubt('holds' if obj.state == 'current' else 'doubt', 'admitted', 'it is %s' % (obj.state or 'not decided'), obj.stac)]
    out.append(Doubt('note', 'what rests on it', ('%d thing%s on the desk rest on it: %s' % (len(fed), '' if len(fed) == 1 else 's', ', '.join('“%s”' % o.title for o in fed if o is not None)[:300]))
                     if fed else 'nothing on the desk rests on it yet', 'field.trace %s | pick rows | select way,steps,kind,title' % _js(id=obj.id)))
    return out


BY_KIND = {'calculation': _calculation, 'sheet': _sheet, 'finding': _claim, 'condition': _condition, 'source': _source, 'document': _page}


def doubts_for(kernel, principal, obj, field):
    made = BY_KIND.get(obj.kind);target = obj.target if isinstance(obj.target, dict) else {}
    try:
        found = made(kernel, principal, obj, field) if made and (target or obj.kind == 'condition') else []
    except (KeyError, TypeError, ValueError, AttributeError, IndexError, ArithmeticError, ImportError) as exc:
        found = [Doubt('cannot tell', 'this', 'it could not be looked at: %s' % str(exc)[:120])]
    if not found:
        found = [Doubt('note', 'this', 'there is nothing I know how to doubt about a %s yet' % ('page' if obj.kind == 'document' else obj.kind))]
    return sorted(found, key=lambda doubt: ORDER.get(doubt.verdict, 9))


def desk(kernel, principal, field):
    """Every doubt and every cannot-tell on the desk: [(object, Doubt)], doubts first."""
    out = [];kernel = _Once(kernel)
    for obj in field.objects:
        if obj.kind not in BY_KIND:continue
        out.extend((obj, doubt) for doubt in doubts_for(kernel, principal, obj, field) if doubt.verdict in ('doubt', 'cannot tell'))
    return sorted(out, key=lambda pair: ORDER.get(pair[1].verdict, 9))
