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
"""
from __future__ import annotations
from fractions import Fraction
from . import project_desk as records, problem_service as problems
from .math_units import rational

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
}
SCOPES = {op: 'approve' if op == 'tolerances.set' else 'read' for op in FIELDS}


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
    if op == 'tolerances.get':
        with kernel.db() as db:value = records.read(db, KIND, args['id'], principal);problem = problems.load(db, value['subject']['problem'], principal)
        return {'tolerance': value, 'state': state(value, problem), 'problem_revision_now': problem['revision']}
    if op == 'tolerances.list':
        rows = []
        with kernel.db() as db:
            for value in _all(db, principal, args.get('problem')):
                problem = problems.load(db, value['subject']['problem'], principal)
                rows.append({**value, 'state': state(value, problem), 'problem_revision_now': problem['revision']})
        return {'tolerances': rows}
    raise ValueError('Unknown tolerance operation')
