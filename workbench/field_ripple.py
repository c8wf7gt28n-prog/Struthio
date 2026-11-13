"""What would move if a number changed (no Qt).

The owner's specification asks, again and again, for the same thing in different clothes: a supplier's price changes, a
drawing date moves, a part is replaced, and the desk should "identify the specific results to recheck after a change". This
module answers before the change is made. Given one sheet (or a calculation, which stands for its sheet) and other values
for some of its cells, it follows the wires and says, for everything downstream, what it says now and what it would say:

    set              the cell itself, as it is and as it would be
    reads it         every calculation that reads one of those cells, worked again exactly with its own recipe
    reads the sheet  the other calculations of that sheet: their result would not move, but any saved change to a sheet
                     sends all its calculations to recheck until each is worked again
    says it          every finding, page and cell whose words carry a number that would move (the cell's own value, a
                     calculation's result, or a number made from two of the desk's values, as Stacy's doubt finds them)
    checks it        every check that reads the sheet: its own program is run on the sheet as it would be, and its own
                     expectation applied, so "would fail" and "would go on passing" are what the check itself would say
    watches it       every investigation that watches the sheet: its findings would wait for a look

Nothing is written and no model is asked. Quantities are compared in their base units, so 280 mA and 0.28 A are one
thing. What cannot be worked is said: a finding that compares in words ("allows 6 W") is not re-read by any rule here, so
it is for the owner to hold against the would-be values; totals bound to a page's words and Agenda watches are not
followed.

    ripple(kernel, principal, field, ident, changes) -> {'rows': [...], 'would_move': n, ...}
"""
import copy
import re

from .field_doubt import QUANTITY, _Once, _decimal, _plain, _quantities, _same, measure, said_quantities, unit_of, weak_check

NOT_WORKED = ('A finding that compares in words (“allows 6 W”) is not worked again here: read it against the would-be values. '
              'Totals bound to a page’s words and Agenda watches are not followed.')


def _read(kernel, principal, operation, arguments):
    try:
        answer = kernel.dispatch(operation, arguments, principal)
    except Exception:  # noqa: BLE001 - a record that cannot be read is said as one; it never stops the others
        return None
    return answer['result'] if answer.get('ok') else None


def _number(text):
    try:
        return float(str(text).strip())
    except (TypeError, ValueError):
        return None


def _label(cells, cell):
    """What a cell is called on its own sheet: the words at the left of its row."""
    found = re.fullmatch(r'([A-Z]+)(\d+)', cell)
    if not found:return ''
    for column in ('A', 'B'):
        held = cells.get(column + found.group(2)) or {}
        if column != found.group(1) and str(held.get('type') or '') == 'text' and str(held.get('value') or '').strip():
            return str(held['value']).strip()[:60]
    return ''


def cells_named(kernel, principal, obj):
    """For a sheet or a calculation of the Field: (the sheet's record id, {a name the owner may use, lower case: its cell}).
    A cell answers to its address, to its row's words, and for a calculation's inputs to their symbols."""
    target = obj.target if isinstance(obj.target, dict) else {}
    names = {};sheet = None
    if obj.kind == 'calculation':
        got = _read(kernel, principal, 'documents.get', {'id': target.get('id')}) or {}
        derivation = (got.get('document') or {}).get('derivation') or {};sheet = derivation.get('sheet')
        for item in derivation.get('inputs') or ():
            for name in (str(item.get('cell') or ''), str(item.get('symbol') or ''), str(item.get('symbol') or '').replace('_', ' '), str(item.get('parameter') or '')):
                if name.strip():names.setdefault(name.strip().lower(), str(item['cell']))
    elif obj.kind == 'sheet':
        sheet = target.get('id')
        got = _read(kernel, principal, 'office.get', {'id': sheet}) or {}
        cells = ((got.get('document') or {}).get('sheets') or [{}])[0].get('cells') or {}
        numbers = [name for name, held in cells.items() if str((held or {}).get('type') or '') != 'text' and _decimal((held or {}).get('value')) is not None]
        measured = [name for name in numbers if unit_of(cells, str(name))]       # on a sheet that gives units, a number without one is a page number or a count, not a value
        for name in sorted(measured or numbers, key=lambda name: (len(name), name)):      # column B before E: a row's words name its first number
            names[str(name).lower()] = str(name)
            said = _label(cells, str(name))
            if said and said.lower() not in names:names[said.lower()] = str(name)
    return sheet, names


def _check_would(kernel, principal, check, address, would):
    """One check that reads the sheet, run as it would run: its own program applied to the sheet as it would be, and its own
    expectation applied to what comes back. -> ('would fail' | 'would still pass' | 'cannot tell', why)."""
    program = str(check.get('program') or '')
    try:
        from sdk.cli.arc1cli import typed_pipeline
        from . import investigations
        plan = _read(kernel, principal, 'language.parse', {'text': program})
        if not plan or plan.get('address') != address or any(step.get('kind') == 'join' for step in plan.get('transforms') or ()):
            return 'cannot tell', 'it reads this sheet in a way that is not worked here; run it after the change'
        rows = typed_pipeline.apply(copy.deepcopy(would), [dict(step) for step in plan['transforms']], 200)
        holds = investigations.oracle_holds(check.get('expect'), check.get('value'), {
            'schema': 'arc.stacy-pipeline-result/1', 'plan': plan, 'rows': rows, 'execution': 'REGISTERED_READ_ONLY_KERNEL_CALL', 'model_calls': 0})
    except Exception as exc:  # noqa: BLE001 - a program this cannot run is said as one, never guessed
        return 'cannot tell', 'its program could not be run on the would-be sheet (%s); run it after the change' % str(exc)[:80]
    if not holds:
        return 'would fail', 'its own program, run on the sheet as it would be, no longer gives what it looks for (%s)' % str(check.get('oracle') or check.get('value') or '')[:120]
    weak = weak_check(kernel, principal, check)
    if weak:
        return 'would still pass', 'it would go on passing without noticing: %s' % weak[0]
    return 'would still pass', 'its own program, run on the sheet as it would be, still gives what it looks for'


def ripple(kernel, principal, field, ident, changes):
    from . import datasheet_work
    start = field.get(ident)
    if start is None:
        raise ValueError('Nothing on the desk has the id %s. field.read lists the ids.' % str(ident)[:80])
    if start.kind not in ('sheet', 'calculation'):
        raise ValueError('A ripple starts from a sheet or a calculation: the place where a number is. “%s” is a %s.' % (str(start.title)[:60], 'page' if start.kind == 'document' else start.kind))
    if not isinstance(changes, dict) or not changes or len(changes) > 8 or not all(isinstance(k, str) and isinstance(v, str) and 0 < len(v) <= 40 for k, v in changes.items()):
        raise ValueError('"set" names one to eight cells, each with a number as text, for example {"B3": "320"}')
    kernel = _Once(kernel)
    sheet, names = cells_named(kernel, principal, start)
    record = _read(kernel, principal, 'office.get', {'id': sheet}) if sheet else None
    if not record:
        raise ValueError('The sheet “%s” reads cannot be read now' % str(start.title)[:60] if start.kind == 'calculation' else 'That sheet cannot be read now')
    cells = ((record.get('document') or {}).get('sheets') or [{}])[0].get('cells') or {}
    address = 'office:' + str(sheet)
    sheet_obj = field.get(address);sheet_title = sheet_obj.title if sheet_obj is not None else str((record.get('document') or {}).get('title') or 'the sheet')
    setting = {}
    for key, value in changes.items():
        cell = names.get(key.strip().lower()) or (key.strip().upper() if start.kind == 'sheet' and key.strip().upper() in cells else None)
        if cell is None:
            known = sorted({c for c in names.values()}, key=lambda c: (len(c), c))
            raise ValueError('%s is not a number on “%s”. Its numbers are in %s.' % (key[:40], str(start.title)[:60], ', '.join(known[:12]) or 'no cell'))
        if str((cells.get(cell) or {}).get('type') or '') == 'text' or _decimal((cells.get(cell) or {}).get('value')) is None:
            raise ValueError('%s holds words, not a number: a what-if sets a number' % cell)
        if _decimal(value) is None:
            raise ValueError('%s needs a plain number%s' % (cell, (', in ' + unit_of(cells, cell)) if unit_of(cells, cell) else ''))
        setting[cell] = value.strip()
    rows = [];moved = []          # moved: (the base unit, the old number there, the new number there, what carried it, in words)
    for cell, value in setting.items():
        now = str((cells.get(cell) or {}).get('value') or '').strip();unit = unit_of(cells, cell);said = _label(cells, cell)
        differs = not _same(_number(now), _number(value))
        rows.append({'way': 'set', 'kind': 'cell', 'title': '“%s” %s%s' % (sheet_title, cell, ' (%s)' % said if said else ''),
                     'says_now': ('%s %s' % (now, unit)).strip(), 'would_be': ('%s %s' % (value, unit)).strip(), 'moves': 'yes' if differs else 'no',
                     'why': 'the value you set' if differs else 'the value it already has', 'id': address})
        if differs and _number(now) is not None:
            base, old = measure(now, unit);_, new = measure(value, unit)
            moved.append((base, old, new, '“%s” %s' % (sheet_title, cell)))
            for other, held in sorted(cells.items()):      # words on the same sheet that carry the old number (a condition that repeats it)
                if other == cell or str((held or {}).get('type') or '') != 'text':continue
                if any(found_base == base and _same(found, old) for _, _, found_base, found in said_quantities(str(held.get('value') or ''))):
                    rows.append({'way': 'says it', 'kind': 'cell', 'title': '“%s” %s' % (sheet_title, other), 'says_now': str(held.get('value'))[:80],
                                 'would_be': 'would still say %s %s' % (now, unit), 'moves': 'yes', 'why': 'its words carry the old value of %s and nothing rewrites them' % cell, 'id': address})
    changed = any(row['moves'] == 'yes' for row in rows)
    untouched = 0
    for obj in field.objects:
        target = obj.target if isinstance(obj.target, dict) else {}
        if obj.kind != 'calculation' or not target.get('id'):continue
        got = _read(kernel, principal, 'documents.get', {'id': target['id']}) or {}
        document = got.get('document') or {};derivation = document.get('derivation') or {}
        if derivation.get('sheet') != sheet:continue
        result = (((derivation.get('calculation') or {}).get('outputs') or [{}])[0] or {}).get('value') or {}
        stands = ('%s %s' % (result.get('decimal'), result.get('unit'))) if result.get('decimal') is not None else ''
        touched = {cell: value for cell, value in setting.items() if any(str(i.get('cell')) == cell for i in derivation.get('inputs') or ())}
        if not touched:
            untouched += 1
            if changed:
                rows.append({'way': 'reads the sheet', 'kind': 'calculation', 'title': obj.title, 'says_now': stands, 'would_be': stands, 'moves': 'no',
                             'why': 'it reads other cells, so its result would not move; but any saved change to a sheet sends its calculations to recheck until each is worked again', 'id': obj.id})
            continue
        try:
            answer = datasheet_work.what_if(document, touched)
        except ValueError as exc:
            rows.append({'way': 'reads it', 'kind': 'calculation', 'title': obj.title, 'says_now': stands, 'would_be': '', 'moves': 'cannot tell',
                         'why': str(exc)[:200], 'id': obj.id});continue
        says = str(answer.get('says_now') or '');would_be = str(answer.get('would_be') or '');differs = says != would_be
        why = 'reads %s; worked again exactly with its own recipe%s' % (', '.join(sorted(touched)), ' (%s)' % answer['exact'] if answer.get('exact') else '')
        if obj.state == 'recheck':why += '; its page is already out of date'
        rows.append({'way': 'reads it', 'kind': 'calculation', 'title': obj.title, 'says_now': says, 'would_be': would_be, 'moves': 'yes' if differs else 'no', 'why': why, 'id': obj.id})
        was = QUANTITY.fullmatch(says.strip());will = QUANTITY.fullmatch(would_be.strip())
        if differs and was and will:
            base, old = measure(was.group(1), was.group(2));base_new, new = measure(will.group(1), will.group(2))
            if base == base_new:moved.append((base, old, new, 'the result of “%s”' % obj.title))
    desk_values = _quantities(kernel, principal, field) if moved else {}
    investigations = {}
    for obj in field.objects:
        target = obj.target if isinstance(obj.target, dict) else {}
        if obj.kind in ('finding', 'question') and target.get('id'):investigations.setdefault(target['id'], None)
        if obj.kind == 'finding':text = str(obj.title)
        elif obj.kind == 'document' and target.get('id') and obj.tag != 'BRIEF':text = str((_read(kernel, principal, 'documents.get', {'id': target['id']}) or {}).get('plain') or '')
        else:continue
        now = [];then = [];why = []
        for value, unit, base, scaled in said_quantities(text):
            back = lambda number, value=value, scaled=scaled: _plain(number * (_number(value) / scaled)) if scaled else _plain(number)     # in the unit the words use
            carried = next(((new, words) for moved_base, old, new, words in moved if moved_base == base and _same(old, scaled)), None)
            if carried:
                now.append('%s %s' % (value, unit));then.append('%s %s' % (back(carried[0]), unit));why.append('%s %s is %s' % (value, unit, carried[1]));continue
            if base not in desk_values or any(_same(held, scaled) for held, _, _ in desk_values[base]):continue
            made = _made_with(scaled, base, moved, desk_values)        # a number made from two of the desk's values, one of which would move
            if made:
                now.append('%s %s' % (value, unit));then.append('%s %s' % (back(made[0]), unit));why.append('%s %s is %s' % (value, unit, made[1]))
        if now:
            rows.append({'way': 'says it', 'kind': 'page' if obj.kind == 'document' else 'finding', 'title': obj.title, 'says_now': '; '.join(now), 'would_be': '; '.join(then),
                         'moves': 'yes', 'why': '; '.join(why)[:400], 'id': obj.id})
    would = None
    for inv in investigations:
        held = _read(kernel, principal, 'investigation.sheet', {'id': inv}) or {}
        for check in held.get('checked') or ():
            program = str(check.get('program') or '');verdict = None
            if address in program:
                if would is None:      # the sheet's whole record as an address read gives it, with the cells as they would be
                    would = copy.deepcopy((_read(kernel, principal, 'ledger.address.read', {'address': address}) or {}).get('object') or record)
                    table = ((would.get('document') or {}).get('sheets') or [{}])[0].get('cells') or {}
                    for cell, value in setting.items():
                        if cell in table:table[cell] = {**table[cell], 'value': value}
                verdict = _check_would(kernel, principal, check, address, would) if changed else ('would still pass', 'nothing would change')
            else:                      # a check on a calculation's page: the page itself does not change when the sheet does
                page = next((r for r in rows if r['way'] == 'reads it' and r['moves'] == 'yes' and r['id'].split(':', 1)[1] in program), None)
                if page is not None:
                    verdict = ('would still pass', 'it reads the page of “%s” as it stands; working the calculation again writes a new page, and this check would go on reading the old one' % page['title'])
            if verdict is None:continue
            rows.append({'way': 'checks it', 'kind': 'check', 'title': str(check.get('claim_text') or 'a finding'), 'says_now': str(check.get('last_outcome') or '').replace('_', ' ').lower(),
                         'would_be': verdict[0], 'moves': 'yes' if verdict[0] == 'would fail' else ('cannot tell' if verdict[0] == 'cannot tell' else 'no'), 'why': verdict[1], 'id': 'claim:' + str(check.get('claim'))})
        if changed and any(str(row.get('address')) == address and row.get('state') == 'CURRENT' for row in held.get('read') or ()):
            rows.append({'way': 'watches it', 'kind': 'investigation', 'title': str(held.get('question') or 'An investigation'), 'says_now': 'its source is as it was recorded',
                         'would_be': 'its findings would wait for a look', 'moves': 'yes', 'why': 'it watches “%s”, and a watched sheet that changes sends its findings to recheck' % sheet_title, 'id': address})
    return {'id': start.id, 'sheet': address, 'set': setting, 'rows': rows,
            'would_move': sum(1 for row in rows if row['moves'] == 'yes' and row['way'] != 'set'),
            'cannot_tell': sum(1 for row in rows if row['moves'] == 'cannot tell'),
            'untouched': untouched, 'not_worked': NOT_WORKED, 'changed': 'nothing'}


def _made_with(scaled, base, moved, desk_values):
    """A number in someone's words that is one desk value less another (or the two together), where one of the two would
    move: (what it would then be, the words for how it is made), or None. Everything in the base unit."""
    held = desk_values.get(base) or ()
    for moved_base, old, new, words in moved:
        if moved_base != base:continue
        for other, where, said in held:
            if _same(other, old):continue
            for was, will, how in ((other - old, other - new, '%s (%s) less %s' % (said, where, words)),
                                   (old - other, new - other, '%s less %s (%s)' % (words, said, where)),
                                   (old + other, new + other, '%s and %s (%s) together' % (words, said, where))):
                if was > 0 and _same(was, scaled):return will, how
    return None


def marks(result):
    """For the Field: {object id: the few words to draw on that sheet}, from a ripple's rows."""
    out = {}
    for row in result.get('rows') or ():
        if row.get('moves') != 'yes' or not row.get('id'):continue
        if row['way'] == 'set':said = '%s → %s' % (row['title'].split('” ', 1)[-1].split(' ', 1)[0], row['would_be'])
        elif row['way'] == 'reads it':said = 'would be ' + row['would_be']
        elif row['way'] == 'checks it':said = 'its check would fail'
        elif row['way'] == 'watches it':continue
        elif row['kind'] == 'cell':said = '%s keeps the old value' % row['title'].rsplit(' ', 1)[-1]
        else:said = 'would say ' + row['would_be']
        out[row['id']] = (out[row['id']] + ' · ' + said) if row['id'] in out else said
    return out
