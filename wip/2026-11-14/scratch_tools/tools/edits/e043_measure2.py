import io
def edit(p, pairs):
    t = io.open(p, encoding='utf8').read()
    for old, new in pairs:
        assert t.count(old) == 1, (p, t.count(old), old[:80])
        t = t.replace(old, new)
    io.open(p, 'w', encoding='utf8').write(t)
W = '/home/user/Struthio/workbench/'
edit(W + 'field_source.py', [('from .field_model import Field, FieldLink, FieldObject, STATE_CURRENT, STATE_HELD, STATE_OPEN, STATE_RECHECK', 'from .field_model import Field, FieldLink, FieldObject, STATE_CURRENT, STATE_HELD, STATE_OPEN, STATE_RECHECK, carries'),
    ('''    field = Field(reader.objects, reader.links, title, note=_left_out(reader), aside=aside, moved=moved)
''', '''    field = Field(reader.objects, reader.links, title, note=_left_out(reader), aside=aside, moved=moved,
                  replaced=frozenset(ident.split(':', 1)[1] for ident in reader.replaced))
''')])
edit(W + 'field_model.py', [('''    moved: tuple = ()                   # results that changed when a calculation was brought up to date: (old words, new words, its title)
''', '''    moved: tuple = ()                   # results that changed when a calculation was brought up to date: (old words, new words, its title)
    replaced: frozenset = frozenset()   # record ids of pages a newer page took the place of (they are kept in Documents, not shown)
''')])
edit(W + 'field_do.py', [('''    quoted = next(((was, now, name) for was, now, name in (field.moved if field is not None else ()) if was in obj.title and now not in obj.title), None) if finding else None
''', '''    quoted = next(((was, now, name) for was, now, name in (field.moved if field is not None else ()) if carries(obj.title, was) and not carries(obj.title, now)), None) if finding else None
'''), ('''                quoted = next(((was, now, name) for was, now, name in field.moved if was in obj.title and now not in obj.title), None)
''', '''                quoted = next(((was, now, name) for was, now, name in field.moved if carries(obj.title, was) and not carries(obj.title, now)), None)
'''), ('''        out.append(Step('Write it again with %s' % now, 'write', op('investigation.claim', id=inv, text=str(obj.title).replace(was, now), role='FINDING'),
''', '''        out.append(Step('Write it again with %s' % now, 'write', op('investigation.claim', id=inv, text=rewritten(obj.title, was, now), role='FINDING'),
'''), ('''import hashlib
import json
from dataclasses import dataclass
''', '''import hashlib
import json
from dataclasses import dataclass

from .field_model import carries, rewritten
'''), ('''                    ('bind a check on its result', op('investigation.check', claim=claim,
                                                     program='documents.get %s | pick document.derivation.calculation.outputs | select value.decimal,value.unit' % js(id=record),
''', '''                    ('bind a check on its result', op('investigation.check', claim=claim,       # from the page's address, so the finding is wired to it and a look at its sources sees it
                                                     program='@document:%s | pick document.derivation.calculation.outputs | select value.decimal,value.unit' % record,
''')])

# ---- field_doubt: quantities in their base units -------------------------------------------------------------------------
p = W + 'field_doubt.py';t = io.open(p, encoding='utf8').read()
def rep(old, new, count=1):
    global t
    assert t.count(old) == count, (t.count(old), old[:80])
    t = t.replace(old, new)

rep('''QUANTITY = re.compile(r'(?<![\\w.])(-?\\d+(?:\\.\\d+)?)\\s*([A-Za-zµΩ°%]+)')
''', '''QUANTITY = re.compile(r'(?<![\\w.])(-?\\d+(?:\\.\\d+)?)\\s*([A-Za-zµΩ°%]+)')


def measure(value, unit):
    """A written quantity in its base unit: (the base unit, the number there), so 280 mA and 0.28 A are one thing and
    3.36 mW is not 3.36 W. The unit table is the page-level one (workbench/quantities.py); a unit it does not know stays
    as written, and then only the same spelling matches."""
    number = _number(value);unit = str(unit or '').strip()
    if number is None or not unit:return unit, number
    try:
        from . import quantities
        spec = quantities.resolve(unit)
    except Exception:  # noqa: BLE001 - an odd token is not a unit; it is compared as written
        spec = None
    if not spec:return unit, number
    return str(spec.get('base_unit') or spec.get('dimension') or unit), number * float(spec.get('factor') or 1)


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
    found = re.fullmatch(r'([A-Z]+)(\\d+)', str(cell))
    return str((cells.get('C' + found.group(2)) or {}).get('value') or '').strip() if found and found.group(1) == 'B' else ''
''')

# sheet: a source that is an imported file, as the Field itself reads it
rep('''    if state and state.startswith('CURRENT'):out.append(Doubt('holds', 'its source', 'the source it was reviewed from stands as it did', stands))
    elif state:out.append(Doubt('doubt', 'its source', 'its source was decided again or changed after this sheet was made (%s)' % state.replace('_', ' ').lower(), stands))
''', '''    if state and (state.startswith('CURRENT') or state == 'UNCHANGED_ORIGINAL'):
        out.append(Doubt('holds', 'its source', 'the source it was %s stands as it did' % ('reviewed from' if origin.get('reviewed_rows') else 'brought in from'), stands))
    elif state and state.endswith('UNAVAILABLE'):
        out.append(Doubt('cannot tell', 'its source', 'the file it was brought in from cannot be reached now, so whether it still agrees is not known', stands))
    elif state:out.append(Doubt('doubt', 'its source', 'its source was decided again or changed after this sheet was made (%s)' % state.replace('_', ' ').lower(), stands))
''')
rep('''    rows = origin.get('reviewed_rows') or []
    cells = ((got.get('document') or {}).get('sheets') or [{}])[0].get('cells') or {}
    out += _counted_twice(ident, cells)
''', '''    rows = origin.get('reviewed_rows') or []
    cells = ((got.get('document') or {}).get('sheets') or [{}])[0].get('cells') or {}
    out += _counted_twice(ident, cells)
    if str(got.get('formula_values') or '') and any((held or {}).get('formula') for held in cells.values()) and any(d.about == 'counted twice' for d in out):
        out.append(Doubt('note', 'counted twice', 'the numbers of the formula cells are the ones the file kept; Graphite has not worked the formulas again', stands))
''')
rep('''    for t in range(3, len(run)):
        total = numbers[run[t]]
        if not total:continue
        start = next((s for s in range(0, t - 2) if sum(numbers[run[k]] for k in range(s, t)) == total), None)
        if start is None:continue
''', '''    for t in range(3, len(run)):
        total = numbers[run[t]]
        if not total:continue
        start = next((s for s in range(0, t - 2) if sum(numbers[run[k]] for k in range(s, t)) == total), None)
        if start is None:continue
        if len({units(run[k]) for k in range(start, t + 1)}) > 1:continue      # volts and amperes that happen to add up are not a total
''')
rep('''def _twice_in_run(ident, column, run, numbers, label):
    out = []''', '''def _twice_in_run(ident, column, run, numbers, label, units):
    out = []''')
rep('''                out += _twice_in_run(ident, column, run, numbers, label);run = []''', '''                out += _twice_in_run(ident, column, run, numbers, label, lambda row, column=column: unit_of(cells, '%s%d' % (column, row)));run = []''')

# another sheet differs: by what the quantity is, not by how it is spelled
rep('''            if (value, unit) != (here, here_unit) and not (unit == here_unit and _same(_number(value), _number(here))):
''', '''            mine_base, mine_scaled = measure(here, here_unit);their_base, their_scaled = measure(value, unit)
            if _number(value) is None or _number(here) is None:
                if (value, unit) == (here, here_unit):continue
            elif mine_base == their_base and _same(mine_scaled, their_scaled):continue        # 280 mA here and 0.28 A there are the same thing
            if True:
''')

rep('''def _made_from(number, unit, desk_values):
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
''', '''def _made_from(scaled, base, desk_values):
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
''')
rep('''    """Every value with a unit that the desk holds: the reviewed rows of its sheets and the results of its calculations.
    -> ({(unit): [(value, where)]})"""
    found = {}''', '''    """Every value with a unit that the desk holds: the reviewed rows of its sheets and the results of its calculations.
    -> {base unit: [(the number in that unit, where it is, as it is written there)]}"""
    found = {}''')
rep('''                if value is not None and unit:found.setdefault(unit, []).append((value, '“%s” B%s (%s)' % (obj.title, at, row.get('parameter') or '')))
''', '''                if value is not None and unit:
                    base, scaled = measure(value, unit)
                    found.setdefault(base, []).append((scaled, '“%s” B%s (%s)' % (obj.title, at, row.get('parameter') or ''), '%s %s' % (_plain(value), unit)))
''')
rep('''            if _number(value.get('decimal')) is not None and value.get('unit'):
                found.setdefault(str(value['unit']), []).append((_number(value['decimal']), 'the result of “%s”' % obj.title))
''', '''            if _number(value.get('decimal')) is not None and value.get('unit'):
                base, scaled = measure(value['decimal'], value['unit'])
                found.setdefault(base, []).append((scaled, 'the result of “%s”' % obj.title, '%s %s' % (value['decimal'], value['unit'])))
''')
rep('''    for was, now, name in field.moved:
        if was in obj.title and now not in obj.title:
            out.append(Doubt('doubt', 'its numbers', 'its words say %s; “%s” now gives %s' % (was, name, now), 'field.read | pick moved | select was,now,calculation'))
    desk_values = _quantities(kernel, principal, field)
    for value, unit in QUANTITY.findall(str(obj.title)):
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
''', '''    for was, now, name in field.moved:
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
''')
rep('''    for was, now, name in field.moved:
        if was in text and now not in text:
            out.append(Doubt('doubt', 'its numbers', 'its words say %s; “%s” now gives %s' % (was, name, now), 'field.read | pick moved | select was,now,calculation'))
    desk_values = _quantities(kernel, principal, field);held = [];seen = set()
    for value, unit in QUANTITY.findall(text):
        if unit not in desk_values or (value, unit) in seen:continue
        seen.add((value, unit))
        if any(_same(number, _number(value)) for number, _ in desk_values[unit]):held.append('%s %s' % (value, unit))
        else:out.append(_unplaced(value, unit, desk_values))
    if held:
''', '''    for was, now, name in field.moved:
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
''')
rep('''    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        found = [Doubt('cannot tell', 'this', 'it could not be looked at: %s' % str(exc)[:120])]''', '''    except (KeyError, TypeError, ValueError, AttributeError, IndexError, ArithmeticError, ImportError) as exc:
        found = [Doubt('cannot tell', 'this', 'it could not be looked at: %s' % str(exc)[:120])]''')
rep('''from decimal import Decimal, InvalidOperation
''', '''from decimal import Decimal, InvalidOperation

from .field_model import carries
''')
io.open(p, 'w', encoding='utf8').write(t)
print('ok')
