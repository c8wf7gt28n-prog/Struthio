"""The owner's tolerances (0.8.5, "Maths in lines"): the range a quantity of a problem sheet may take, said by the owner.

A tolerance is a Project Desk record (kind 'tolerance', schema ledger.tolerance/1) in the shared desk store, as condition
cards are: subject {problem, variable} (the goal slice adds {address, cell}), at {revision, value, unit} (the sheet as it
was when it was said), said (plus_minus, percent or between, with amount, or lo and hi), unit, basis (the owner's words),
the exact lo and hi in that unit, and set_by 'owner'. One record per subject; saying it again makes a new revision.

  tolerances.get   {id}                                                                    read
  tolerances.list  {problem?}                                                              read
  tolerances.set   {id, expected_revision, expected_context_digest (the sheet), variable,
                    said, amount | lo and hi, basis}                                       approve

On read each tolerance is held against the sheet as it stands: APPLIES at the revision it was said on; CARRIED_OVER when
the sheet moved on but this quantity's value and unit did not; RECHECK when they changed, and then it is not applied.
Nothing is written in the background. Which range applies decides what Kasandra concludes, so tolerances.set is approve
scope and also among what always asks in her hand (stacy_hand.ALWAYS_ASKS): her calls run as the operator, who holds
approve scope, so that row is the real guard.

The goal slice (0.8.6 S1) adds tolerances on a reviewed sheet's cells, the subject {address, cell} ('office:' and the
sheet's id; a Value-column cell such as B5), said in the cell's own unit and held against the sheet the same way:
APPLIES at the sheet revision it was said on, CARRIED_OVER while that cell's value and unit are unchanged, RECHECK when
they changed. Her goals read them through on_cells.

  tolerances.set_cell {sheet, cell, expected_revision (the sheet's), said, amount | lo and hi, basis}   approve
"""
from __future__ import annotations
from fractions import Fraction
from . import project_desk as records, problem_service as problems
from .math_units import rational

SHEET_ID = {'type': 'string', 'pattern': '^owner:[a-f0-9]{32}$'}      # a working sheet of the office store (office_service.ID)
SHEET_REVISION = {'type': 'string', 'pattern': '^[a-f0-9]{64}$'}
CELL = {'type': 'string', 'pattern': '^B[1-9][0-9]{0,2}$'}           # a Value-column cell

KIND = 'tolerance'
SCHEMA = 'ledger.tolerance/1'
SAID = ('plus_minus', 'percent', 'between')
STATES = ('APPLIES', 'CARRIED_OVER', 'RECHECK')
NAME = {'type': 'string', 'minLength': 1, 'maxLength': 64}
NUMBER = {'type': 'string', 'minLength': 1, 'maxLength': 100}
FIELDS = {
    'tolerances.get': ({'id': records.ID}, ['id']),
    'tolerances.list': ({'problem': records.ID}, []),
    'tolerances.set': ({**problems.BOUND, 'variable': NAME, 'said': {'type': 'string', 'enum': list(SAID)}, 'amount': NUMBER,
                        'lo': NUMBER, 'hi': NUMBER, 'basis': {'type': 'string', 'minLength': 1, 'maxLength': 1000}},
                       [*problems.BOUND, 'variable', 'said', 'basis']),
    # 0.8.6 S1 (the exact goal face): a tolerance on a reviewed sheet's Value cell
    'tolerances.set_cell': ({'sheet': SHEET_ID, 'cell': CELL, 'expected_revision': SHEET_REVISION, 'said': {'type': 'string', 'enum': list(SAID)},
                             'amount': NUMBER, 'lo': NUMBER, 'hi': NUMBER, 'basis': {'type': 'string', 'minLength': 1, 'maxLength': 1000}},
                            ['sheet', 'cell', 'expected_revision', 'said', 'basis']),
}
WRITES = ('tolerances.set', 'tolerances.set_cell')
SCOPES = {op: 'approve' if op in WRITES else 'read' for op in FIELDS}


def span(said, value, args):
    """(lo, hi) exact, in the quantity's unit, from what the owner said about its declared value."""
    value = rational(value)
    if said == 'between':
        if set(args) & {'amount'} or not {'lo', 'hi'} <= set(args):raise ValueError('TOLERANCE_SAID_FIELDS: between takes lo and hi')
        lo, hi = rational(args['lo']), rational(args['hi'])
    else:
        if set(args) & {'lo', 'hi'} or 'amount' not in args:raise ValueError('TOLERANCE_SAID_FIELDS: %s takes an amount' % said)
        amount = rational(args['amount'])
        if amount < 0:raise ValueError('TOLERANCE_NEGATIVE: say the amount as a size')
        width = amount if said == 'plus_minus' else abs(value) * amount / 100
        lo, hi = value - width, value + width
    if lo > hi:raise ValueError('TOLERANCE_REVERSED: the low end comes first')
    return lo, hi


def _quantity(problem, name):
    return next((v for v in problem['variables'] if v['name'] == name), None)


def state(value, problem):
    """APPLIES, CARRIED_OVER or RECHECK: this tolerance held against the sheet as it stands now."""
    at = value['at'];now = _quantity(problem, value['subject']['variable'])
    if not now or now['type'] != 'quantity' or now['state'] != 'KNOWN' or now['unit'] != at['unit']:return 'RECHECK'
    try:same = rational(now['value']) == rational(at['value'])
    except ValueError:return 'RECHECK'
    if not same:return 'RECHECK'
    return 'APPLIES' if problem['revision'] == at['revision'] else 'CARRIED_OVER'


def sheet_cell(saved, cell):
    """A Value-column cell of a working sheet as it stands: {'address', 'sheet', 'cell', 'revision', 'value', 'unit',
    'parameter', 'conditions', 'title'}, the value and unit as the sheet holds them (text); None when it is not there."""
    cells = ((saved.get('document') or {}).get('sheets') or [{}])[0].get('cells') or {}
    row = str(cell)[1:]
    if not str(cell).startswith('B') or not row.isdigit() or cell not in cells:return None
    def text(column):return str((cells.get(column + row) or {}).get('value') or '').strip()
    return {'address': 'office:' + saved['id'], 'sheet': saved['id'], 'cell': cell, 'revision': saved['revision'], 'value': text('B'),
            'unit': text('C'), 'parameter': text('A'), 'conditions': text('D'), 'title': (saved.get('document') or {}).get('title') or ''}


def _sheet(sheet):
    from .office_service import store
    return store().get(sheet)


def cell_state(value, saved):
    """APPLIES, CARRIED_OVER or RECHECK: a cell's tolerance held against the sheet as it stands now."""
    at = value['at'];now = sheet_cell(saved, value['subject']['cell']) if saved else None
    if not now or now['unit'] != at['unit']:return 'RECHECK'
    try:same = rational(now['value']) == rational(at['value'])
    except ValueError:return 'RECHECK'
    if not same:return 'RECHECK'
    return 'APPLIES' if saved['revision'] == at['revision'] else 'CARRIED_OVER'


def _state_now(value, db, principal):
    """A tolerance's state against what it is said of now: the problem sheet, or the working sheet of its cell."""
    if 'cell' in value['subject']:
        try:saved = _sheet(value['subject']['sheet'])
        except (ValueError, OSError, KeyError):saved = None
        return cell_state(value, saved), (saved or {}).get('revision')
    problem = problems.load(db, value['subject']['problem'], principal)
    return state(value, problem), problem['revision']


def on_cells(kernel, principal):
    """{(address, cell): {id, revision, state, lo, hi, said, unit}} for the owner's tolerances on sheet cells, each held
    against its sheet as it stands now."""
    with kernel.db() as db:said = [t for t in _all(db, principal) if 'cell' in t['subject']]
    found = {}
    for t in said:
        try:saved = _sheet(t['subject']['sheet'])
        except (ValueError, OSError, KeyError):saved = None
        found[(t['subject']['address'], t['subject']['cell'])] = {'id': t['id'], 'revision': t['revision'], 'state': cell_state(t, saved),
                                                                  'lo': t['lo'], 'hi': t['hi'], 'said': t['said'], 'unit': t['unit']}
    return found


def put_cell(kernel, args, principal):
    saved = _sheet(args['sheet'])
    if saved['revision'] != args['expected_revision']:raise ValueError('REVISION_CHANGED: reopen the sheet before saying a tolerance on it')
    cell = sheet_cell(saved, args['cell'])
    if not cell:raise ValueError('TOLERANCE_NEEDS_A_KNOWN_QUANTITY: %s is not a Value cell of this sheet' % args['cell'])
    try:rational(cell['value'])
    except ValueError:raise ValueError('TOLERANCE_NEEDS_A_KNOWN_QUANTITY: %s holds no exact number' % args['cell']) from None
    if not cell['unit']:raise ValueError('TOLERANCE_NEEDS_A_KNOWN_QUANTITY: %s has no reviewed unit' % args['cell'])
    if not args['basis'].strip():raise ValueError('TOLERANCE_BASIS: say where the tolerance comes from')
    lo, hi = span(args['said'], cell['value'], {k: args[k] for k in ('amount', 'lo', 'hi') if k in args})
    fields = {'subject': {'address': cell['address'], 'sheet': cell['sheet'], 'cell': cell['cell']},
              'at': {'revision': saved['revision'], 'value': cell['value'], 'unit': cell['unit'], 'parameter': cell['parameter']},
              'said': args['said'], 'amount': args.get('amount'), 'unit': cell['unit'], 'basis': args['basis'],
              'lo': str(Fraction(lo)), 'hi': str(Fraction(hi)), 'set_by': 'owner'}
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE')
        old = next((t for t in _all(db, principal) if t['subject'].get('address') == cell['address'] and t['subject'].get('cell') == cell['cell']), None)
        if old is None:return records.write(db, records.new(KIND, principal, schema=SCHEMA, **fields), principal, 'TOLERANCE_SAID')
        expected = old['revision'];records.edit(old, expected);old.update(fields)
        return records.write(db, old, principal, 'TOLERANCE_SAID_AGAIN', expected=expected)


def _all(db, principal, problem=None):
    ids = [row[0] for row in db.execute('SELECT id FROM desk_records WHERE owner=? AND kind=? ORDER BY rowid', (principal.identity, KIND))]
    found = [records.read(db, KIND, ident, principal) for ident in ids]
    return [t for t in found if problem is None or t['subject'].get('problem') == problem]


def standing(kernel, problem, principal):
    """{variable: {id, revision, state, lo, hi, said, unit}} for the sheet's tolerances, as they stand against it now."""
    with kernel.db() as db:said = _all(db, principal, problem['id'])
    return {t['subject']['variable']: {'id': t['id'], 'revision': t['revision'], 'state': state(t, problem), 'lo': t['lo'], 'hi': t['hi'],
                                       'said': t['said'], 'unit': t['unit']} for t in said}


def put(kernel, args, principal):
    with kernel.db() as db:problem = problems.load(db, args['id'], principal)
    problems.check_bound(problem, args)
    quantity = _quantity(problem, args['variable'])
    if not quantity or quantity['type'] != 'quantity' or quantity['state'] != 'KNOWN':
        raise ValueError('TOLERANCE_NEEDS_A_KNOWN_QUANTITY: %s is not a quantity with a value on this sheet' % args['variable'])
    if not args['basis'].strip():raise ValueError('TOLERANCE_BASIS: say where the tolerance comes from')
    lo, hi = span(args['said'], quantity['value'], {k: args[k] for k in ('amount', 'lo', 'hi') if k in args})
    fields = {'subject': {'problem': problem['id'], 'variable': args['variable']},
              'at': {'revision': problem['revision'], 'value': quantity['value'], 'unit': quantity['unit']},
              'said': args['said'], 'amount': args.get('amount'), 'unit': quantity['unit'], 'basis': args['basis'],
              'lo': str(Fraction(lo)), 'hi': str(Fraction(hi)), 'set_by': 'owner'}
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE');problems.check_bound(problems.load(db, args['id'], principal), args)
        old = next((t for t in _all(db, principal, problem['id']) if t['subject']['variable'] == args['variable']), None)
        if old is None:return records.write(db, records.new(KIND, principal, schema=SCHEMA, **fields), principal, 'TOLERANCE_SAID')
        expected = old['revision'];records.edit(old, expected);old.update(fields)
        return records.write(db, old, principal, 'TOLERANCE_SAID_AGAIN', expected=expected)


def dispatch(kernel, op, args, principal):
    if op == 'tolerances.set':return put(kernel, args, principal)
    if op == 'tolerances.set_cell':return put_cell(kernel, args, principal)
    if op == 'tolerances.get':
        with kernel.db() as db:
            value = records.read(db, KIND, args['id'], principal);now, revision = _state_now(value, db, principal)
        key = 'sheet_revision_now' if 'cell' in value['subject'] else 'problem_revision_now'
        return {'tolerance': value, 'state': now, key: revision}
    if op == 'tolerances.list':
        rows = []
        with kernel.db() as db:
            for value in _all(db, principal, args.get('problem')):
                now, revision = _state_now(value, db, principal)
                key = 'sheet_revision_now' if 'cell' in value['subject'] else 'problem_revision_now'
                rows.append({**value, 'state': now, key: revision})
        return {'tolerances': rows}
    raise ValueError('Unknown tolerance operation')
