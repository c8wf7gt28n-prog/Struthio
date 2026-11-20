"""The one maths core (0.8.5, "Maths in lines"): exact ranges, the decision rule, and the allowed set of "solve for".

Pure: Fraction arithmetic over math_model's validated IR, which stays exactly as it is (math_service hashes it). No Qt, no
Kernel, no language model, no SymPy or Z3, and no float anywhere (tests_integrated/test_math_core.py scans for one).

  Enclosure       a closed range [lo, hi] in base units, and how it was found: ATTAINED (its ends are values the expression
                  takes at corners of the ranges), SOUND_ENCLOSURE (it holds every value, perhaps more) or WIDENED (2048
                  bits were not enough, so its ends were moved outward to dyadic numbers).
  outward         that widening.
  enclose         the range of a node over a box of input ranges; a relation's node gives its slack, right minus left.
  decide          HOLDS, FAILS or UNDECIDED from a slack and a relation (the table of the design, rule 3).
  check_box       the one real value (state) and every value in the ranges (for_all), with the worst corner as witness.
  corner_witness  that corner, re-evaluated by math_model.evaluate.
  allowed         "solve for x": every value of x for which the relation holds at every corner of the ranges.
  freed           a copy of the model with x's declared value removed, where its witnesses are checked.

A box maps a variable's name to (lo, hi) in its declared unit. A range is exact (ATTAINED) when the expression is affine in
the ranged inputs (x - x cancels), or when each ranged input occurs once and never under an even power; otherwise it is a
sound enclosure. Every failure is a RangeError with a code (DIMENSION_MISMATCH, DOMAIN_ERROR, UNSUPPORTED, MISSING_INPUT,
EXACT_ARITHMETIC_SIZE_BOUND, DENOMINATOR_MAY_BE_ZERO); math_answers turns it into a state and never raises.
"""
from __future__ import annotations
import copy
import math
from fractions import Fraction
from itertools import product
from .math_model import RELATIONS, MathError, affine, evaluate, validate, witness_check
from .math_units import rational, unit_spec

BITS = 2048                  # the size limit of math_units.bounded, for a numerator and a denominator alike
ATTAINED, SOUND, WIDENED = 'ATTAINED', 'SOUND_ENCLOSURE', 'WIDENED'
HOLDS, FAILS, UNDECIDED = 'HOLDS', 'FAILS', 'UNDECIDED'
HOLDS_FOR_ALL, FAILS_FOR_SOME, FAILS_FOR_ALL = 'HOLDS_FOR_ALL', 'FAILS_FOR_SOME', 'FAILS_FOR_ALL'
ALLOWED, WHOLE_DOMAIN, EMPTY = 'ALLOWED', 'WHOLE_DOMAIN', 'EMPTY'
RANGED = 4                   # at most four inputs with a range at once: at most sixteen corners
# math_model's reasons name its solver fragment; the owner reads these instead.
REWORDED = {'Variable products are outside the linear fragment': 'it is multiplied by another quantity without a value',
            'A variable denominator is outside the linear fragment': 'a quantity without a value is under a division',
            'Z3 fragment admits linear arithmetic only': 'a quantity without a value is under a power'}


class RangeError(ValueError):
    def __init__(self, code, detail):super().__init__(detail);self.code=code


def fail(code, detail):raise RangeError(code, detail)


def fits(value):
    return max(abs(value.numerator).bit_length(), value.denominator.bit_length()) <= BITS


class Enclosure:
    """A closed range in base units, with how it was found."""
    __slots__ = ('lo', 'hi', 'status')

    def __init__(self, lo, hi, status=ATTAINED):
        if lo > hi:fail('DOMAIN_ERROR', 'A range runs from its low end to its high end')
        self.lo, self.hi, self.status = Fraction(lo), Fraction(hi), status

    def __contains__(self, value):return self.lo <= value <= self.hi
    def __eq__(self, other):return isinstance(other, Enclosure) and (self.lo, self.hi, self.status) == (other.lo, other.hi, other.status)
    __hash__ = None
    def __repr__(self):return 'Enclosure(%s, %s, %s)' % (self.lo, self.hi, self.status)
    def inside(self, other):return other.lo <= self.lo and self.hi <= other.hi


def outward(lo, hi=None):
    """[lo, hi] (or the one value lo) as the narrowest range whose ends fit in 2048 bits: unchanged and ATTAINED when they
    already fit; otherwise its ends moved outward to dyadic numbers, WIDENED. Too large even for that: a state."""
    lo = Fraction(lo);hi = lo if hi is None else Fraction(hi)
    if fits(lo) and fits(hi):return Enclosure(lo, hi)
    whole = (math.floor(max(abs(lo), abs(hi))) + 1).bit_length()
    if BITS - 2 - whole < 0:fail('EXACT_ARITHMETIC_SIZE_BOUND', 'A number here needs more than 2048 bits even when rounded')
    scale = 2 ** (BITS - 2 - whole)
    return Enclosure(Fraction(math.floor(lo * scale), scale), Fraction(math.ceil(hi * scale), scale), WIDENED)


def exact(value):
    """A number of a range as an exact Fraction: a Fraction or int as it is, text through math_units.rational."""
    if isinstance(value, (Fraction, int)) and not isinstance(value, bool):return Fraction(value)
    try:return rational(value)
    except (ValueError, TypeError) as exc:
        if isinstance(value, str) and (len(value) > 100 or str(exc) in ('NUMBER_EXPONENT_BOUND', 'EXACT_ARITHMETIC_SIZE_BOUND')):
            fail('EXACT_ARITHMETIC_SIZE_BOUND', 'A number here is too long to work with exactly: write it in at most 100 characters')
        fail('UNSUPPORTED', 'Write each number as an exact decimal or fraction, such as 11.8 or 1/3')


def nodes_of(ir):return {n['id']: n for n in ir['model']['nodes']}


def output(ir):return ir['model']['outputs'][0]


def shape(ir, root=None):
    """For each variable the node at `root` (default: the output) reaches: how often it is used, and what it sits under
    ('power', 'even' for an even power, 'division' for either side of one)."""
    nodes = ir['model']['nodes'];uses = {n['id']: 0 for n in nodes};under = {n['id']: set() for n in nodes}
    uses[root or output(ir)] = 1
    for n in reversed(nodes):
        if not uses[n['id']]:continue
        marks = set(under[n['id']])
        if n['op'] == 'power':marks |= {'power'} | ({'even'} if n['exponent'] % 2 == 0 else set())
        if n['op'] == 'div':marks.add('division')
        for key in ('left', 'right', 'argument'):
            if key in n:uses[n[key]] += uses[n['id']];under[n[key]] |= marks
    found = {}
    for n in nodes:
        if n['op'] == 'variable' and uses[n['id']]:
            row = found.setdefault(n['name'], {'uses': 0, 'under': set()});row['uses'] += uses[n['id']];row['under'] |= under[n['id']]
    return found


def checked_box(ir, box):
    """The box as exact Fractions in declared units, after the checks every range gets."""
    variables = ir['model']['variables'];box = dict(box or {})
    if len(box) > RANGED:fail('UNSUPPORTED', 'At most four quantities may have a range at once')
    result = {}
    for name, span in box.items():
        if name not in variables:fail('MISSING_INPUT', 'The expression does not use ' + str(name))
        lo, hi = exact(span[0]), exact(span[1])
        if lo > hi:fail('DOMAIN_ERROR', 'The range of %s runs from its low end to its high end' % name)
        v = variables[name]
        if v.get('domain') == 'integer' and (lo.denominator != 1 or hi.denominator != 1):
            fail('DOMAIN_ERROR', '%s takes whole values only, so each end of its range is a whole number' % name)
        if ('lower' in v and lo < rational(v['lower'])) or ('upper' in v and hi > rational(v['upper'])):
            fail('DOMAIN_ERROR', 'The range of %s leaves the values it may take' % name)
        result[name] = (lo, hi)
    return result


def _power(span, exponent, ident):
    lo, hi = span
    if exponent < 0:
        if lo == hi == 0:fail('DOMAIN_ERROR', 'Negative power of zero at ' + ident)
        if lo <= 0 <= hi:fail('DENOMINATOR_MAY_BE_ZERO', 'The range under a negative power includes zero')
        lo, hi, exponent = 1 / hi, 1 / lo, -exponent
    if exponent == 0:return Fraction(1), Fraction(1)
    a, b = lo ** exponent, hi ** exponent
    if exponent % 2:return a, b
    return (Fraction(0) if lo <= 0 <= hi else min(a, b)), max(a, b)


def _intervals(ir, box):
    """Every node's range in base units by interval arithmetic (a relation's: right minus left), and whether a range had to
    be widened to stay inside 2048 bits."""
    variables = ir['model']['variables'];spans = {};widened = False
    for n in ir['model']['nodes']:
        op = n['op']
        if op == 'quantity':
            value = rational(n['value']) * unit_spec(n['unit'])[1];span = (value, value)
        elif op == 'variable':
            v = variables[n['name']];factor = unit_spec(v['unit'])[1]
            if n['name'] in box:span = (box[n['name']][0] * factor, box[n['name']][1] * factor)
            elif 'value' in v:
                value = rational(v['value']) * factor;span = (value, value)
            else:fail('MISSING_INPUT', 'No value or range for ' + n['name'])
        elif op == 'neg':
            lo, hi = spans[n['argument']];span = (-hi, -lo)
        elif op == 'power':span = _power(spans[n['argument']], n['exponent'], n['id'])
        else:
            (a, b), (c, d) = spans[n['left']], spans[n['right']]
            if op == 'add':span = (a + c, b + d)
            elif op == 'sub':span = (a - d, b - c)
            elif op in RELATIONS:span = (c - b, d - a)
            elif op == 'mul':
                ends = (a * c, a * d, b * c, b * d);span = (min(ends), max(ends))
            else:
                if c == d == 0:fail('DOMAIN_ERROR', 'Zero denominator at ' + n['id'])
                if c <= 0 <= d:fail('DENOMINATOR_MAY_BE_ZERO', 'The range of a denominator includes zero')
                ends = (a / c, a / d, b / c, b / d);span = (min(ends), max(ends))
        kept = outward(*span);widened = widened or kept.status == WIDENED
        spans[n['id']] = (kept.lo, kept.hi)
    return spans, widened


def _affine_span(ir, box, node):
    """The exact range of a node that is affine in the ranged inputs (constant plus each coefficient times its range), as
    (lo, hi) in base units; None when the model is not affine in them."""
    try:forms = affine(ir, free=tuple(box))
    except MathError as exc:
        if exc.code == 'DOMAIN_ERROR':fail('DOMAIN_ERROR', str(exc))
        return None
    constant, coefficients = forms[node]
    missing = sorted(set(coefficients) - set(box))
    if missing:fail('MISSING_INPUT', 'No value or range for ' + ', '.join(missing))
    lo = hi = constant
    for name, k in coefficients.items():
        ends = (k * box[name][0], k * box[name][1]);lo += min(ends);hi += max(ends)
    return lo, hi


def enclose(ir, box=None, node=None):
    """The range of `node` (default: the output) over the box, in base units; for a relation, its slack right - left."""
    box = checked_box(ir, box);node = node or output(ir)
    try:
        spans = _affine_span(ir, box, node)
        if spans is not None:
            lo, hi = spans
            if nodes_of(ir)[node]['op'] in RELATIONS:lo, hi = -hi, -lo     # affine gives left - right
            return outward(lo, hi)
        spans, widened = _intervals(ir, box)
    except (ValueError, ZeroDivisionError) as exc:
        if isinstance(exc, RangeError):raise
        fail('EXACT_ARITHMETIC_SIZE_BOUND' if 'EXACT_ARITHMETIC_SIZE_BOUND' in str(exc) else 'DOMAIN_ERROR', str(exc))
    lo, hi = spans[node]
    if widened:return Enclosure(lo, hi, WIDENED)
    used = shape(ir, node)
    once = all(used[name]['uses'] <= 1 and 'even' not in used[name]['under'] for name in box if name in used)
    return Enclosure(lo, hi, ATTAINED if once else SOUND)


def decide(slack, relation):
    """HOLDS, FAILS or UNDECIDED for `left relation right`, from its slack S = right - left (an Enclosure)."""
    lo, hi = slack.lo, slack.hi
    if relation in ('ge', 'gt'):
        lo, hi, relation = -hi, -lo, 'le' if relation == 'ge' else 'lt'
    if relation == 'le':return HOLDS if lo >= 0 else FAILS if hi < 0 else UNDECIDED
    if relation == 'lt':return HOLDS if lo > 0 else FAILS if hi <= 0 else UNDECIDED
    zero, apart = lo == hi == 0, lo > 0 or hi < 0
    if relation == 'eq':return HOLDS if zero else FAILS if apart else UNDECIDED
    if relation == 'ne':return HOLDS if apart else FAILS if zero else UNDECIDED
    fail('UNSUPPORTED', 'Unknown comparison')


def corners(box):
    """Each corner of a box, in sorted name order; a range of one value gives one end."""
    names = sorted(box)
    for ends in product(*((box[n][0],) if box[n][0] == box[n][1] else (box[n][0], box[n][1]) for n in names)):
        yield dict(zip(names, ends))


def text(value):
    """A Fraction as math_units.rational reads it."""
    return str(value)


def corner_witness(ir, box=None):
    """The corner of the ranges where the relation is furthest from holding, re-evaluated by math_model.evaluate: {'assignment':
    every input's value there, in its declared unit, 'value': the left side there (a quantity record), 'slack'}; None when
    the relation holds at every corner, or the re-evaluation does not agree."""
    box = checked_box(ir, box);node = nodes_of(ir)[output(ir)];relation = node['op']
    if relation not in RELATIONS:return None
    worst = None
    for corner in corners(box):
        s = enclose(ir, {k: (v, v) for k, v in corner.items()}).lo
        badness = {'le': -s, 'lt': -s, 'ge': s, 'gt': s, 'eq': abs(s), 'ne': -abs(s)}[relation]
        if decide(Enclosure(s, s), relation) == FAILS and (worst is None or badness > worst[0]):worst = (badness, corner, s)
    if worst is None:return None
    _, corner, s = worst
    try:checked = evaluate(ir, {k: text(v) for k, v in corner.items()})
    except ValueError:return None
    row = (checked.get('outputs') or [{}])[0]
    if checked['state'] != 'INFEASIBLE' or row.get('value') is not False:return None
    variables = ir['model']['variables']
    assignment = {name: corner[name] if name in corner else rational(v['value']) for name, v in variables.items() if name in corner or 'value' in v}
    return {'assignment': assignment, 'value': row['left'], 'slack': s}


def check_box(ir, box=None):
    """A relation over the ranges: {'relation', 'state' (the one real value), 'for_all' (every value in the ranges),
    'slack', 'left', 'right' (Enclosures), 'witness' (the worst corner, or None)}."""
    relation = nodes_of(ir)[output(ir)]['op']
    if relation not in RELATIONS:fail('UNSUPPORTED', 'A check needs one comparison, such as <=')
    node = nodes_of(ir)[output(ir)];slack = enclose(ir, box);state = decide(slack, relation)
    witness = corner_witness(ir, box) if state != HOLDS else None
    for_all = HOLDS_FOR_ALL if state == HOLDS else FAILS_FOR_ALL if state == FAILS else FAILS_FOR_SOME if witness else UNDECIDED
    return {'relation': relation, 'state': state, 'for_all': for_all, 'slack': slack,
            'left': enclose(ir, box, node['left']), 'right': enclose(ir, box, node['right']), 'witness': witness}


def freed(ir, name):
    """A copy of the model with `name`'s declared value removed: where a value found for it is checked again."""
    model = copy.deepcopy(ir['model']);model['variables'][name].pop('value', None)
    return validate(model)


def _fixed(ir, corner):
    model = copy.deepcopy(ir['model'])
    for name, value in corner.items():model['variables'][name]['value'] = text(value)
    try:return validate(model)
    except MathError as exc:fail(exc.code, str(exc))
    except ValueError:fail('EXACT_ARITHMETIC_SIZE_BOUND', 'A number of the ranges is too long to write exactly')


def _ends(relation, rising, root):
    """(lower, upper) of {x : a*x + c REL 0} with root -c/a; each end (value, closed) or None; `rising`: a > 0."""
    if relation == 'eq':return (root, True), (root, True)
    closed = relation in ('le', 'ge')
    if (relation in ('le', 'lt')) == rising:return None, (root, closed)
    return (root, closed), None


def _tighter(new, old, upper):
    if old is None:return True
    if new[0] != old[0]:return new[0] < old[0] if upper else new[0] > old[0]
    return not new[1] and old[1]


def _holds(value, relation):
    return {'le': value <= 0, 'lt': value < 0, 'ge': value >= 0, 'gt': value > 0, 'eq': value == 0, 'ne': value != 0}[relation]


def _down(end, step):
    k = math.floor(end[0] / step)
    if not end[1] and k * step == end[0]:k -= 1
    return k * step


def _up(end, step):
    k = math.ceil(end[0] / step)
    if not end[1] and k * step == end[0]:k += 1
    return k * step


def _inside(value, lower, upper):
    return ((lower is None or value > lower[0] or (value == lower[0] and lower[1]))
            and (upper is None or value < upper[0] or (value == upper[0] and upper[1])))


def _at(fixed, name, point):
    """The relation and its left side with `name` at `point`, by math_model.evaluate: (holds, left quantity record)."""
    try:checked = evaluate(fixed, {name: text(point)})
    except ValueError:return None, None
    row = (checked.get('outputs') or [{}])[0]
    if checked['state'] not in ('FEASIBLE', 'INFEASIBLE'):return None, None
    return row.get('value') is True, row.get('left')


def allowed(ir, name, box=None, within=None, step=None):
    """Solve for `name`: every value of it (in its declared unit) for which the relation holds at every corner of the
    ranges, intersected with its declared lower and upper and with `within` (lo, hi), rounded to `step` (or to whole units
    for an integer quantity). {'state': ALLOWED, WHOLE_DOMAIN or EMPTY, 'lower', 'upper' (each {'value', 'closed', 'by'}
    or None), 'needs' (what the relation alone asks), 'step', 'lattice', 'declared', 'declared_inside', 'checked' (each
    reported end holds again on the freed copy at every corner), 'ends' and 'beyond' (the end and the next step past it,
    evaluated at the corner that sets it), 'corners', 'reason'}. Not affine in `name`, a second quantity without a value,
    a variable denominator, or ranges whose corners need not be the extremes: UNSUPPORTED with the reason."""
    relation = nodes_of(ir)[output(ir)]['op'];variables = ir['model']['variables']
    if relation not in RELATIONS:fail('UNSUPPORTED', 'Solve for needs one comparison, such as <=')
    if relation == 'ne':fail('UNSUPPORTED', 'Not equal leaves two pieces; ask with < or > instead')
    if name not in variables:fail('MISSING_INPUT', 'The relation does not use ' + str(name))
    if name in (box or {}):fail('UNSUPPORTED', name + ' is what is solved for, so it cannot also have a range')
    box = checked_box(ir, box);used = shape(ir)
    for other in sorted(box):
        row = used.get(other, {'uses': 0, 'under': set()})
        if row['uses'] > 1:fail('UNSUPPORTED', other + ' appears more than once, so the corners of its range need not be the extremes')
        if row['under'] & {'power', 'division'}:fail('UNSUPPORTED', other + ' sits under a division or a power, so the corners of its range need not be the extremes')
    loose = freed(ir, name);rows = []
    for corner in corners(box):
        fixed = _fixed(loose, corner)
        try:constant, coefficients = affine(fixed, free=(name,))[output(ir)]
        except MathError as exc:fail(exc.code, '%s: %s' % (name, REWORDED.get(str(exc), str(exc))) if exc.code == 'UNSUPPORTED' else str(exc))
        others = sorted(set(coefficients) - {name})
        if others:fail('UNSUPPORTED', 'A second quantity without a value: %s; give it a value or a range' % ', '.join(others))
        rows.append((corner, fixed, coefficients.get(name, Fraction(0)), constant))
    v = variables[name];declared = rational(v['value']) if 'value' in v else None
    step = exact(step) if step is not None else Fraction(1) if v.get('domain') == 'integer' else None
    if step is not None and step <= 0:fail('UNSUPPORTED', 'A step is a positive number')
    domain = []
    if 'lower' in v:domain.append(('lower', (rational(v['lower']), True), 'domain'))
    if 'upper' in v:domain.append(('upper', (rational(v['upper']), True), 'domain'))
    if within is not None:
        lo, hi = exact(within[0]), exact(within[1])
        if lo > hi:fail('DOMAIN_ERROR', 'Within runs from its low end to its high end')
        domain += [('lower', (lo, True), 'within'), ('upper', (hi, True), 'within')]
    result = {'state': ALLOWED, 'name': name, 'relation': relation, 'unit': v['unit'], 'lower': None, 'upper': None,
              'needs': {'lower': None, 'upper': None}, 'step': step, 'lattice': None, 'declared': declared, 'declared_inside': None,
              'checked': None, 'ends': [], 'beyond': [], 'corners': len(rows), 'reason': ''}
    signs = {(a > 0) - (a < 0) for _, _, a, _ in rows}
    ends = {'lower': None, 'upper': None};by = {};binding = {}
    if signs == {0}:
        if not all(_holds(c, relation) for _, _, _, c in rows):
            result.update(state=EMPTY, reason='It does not hold for any value of %s: %s cancels out of it' % (name, name));return result
        result['state'] = WHOLE_DOMAIN
    elif len(signs) > 1 or 0 in signs:
        fail('UNSUPPORTED', 'Over the ranges the factor of %s changes sign or vanishes, so the corners need not be the extremes' % name)
    else:
        for corner, fixed, a, c in rows:
            for side, end in zip(('lower', 'upper'), _ends(relation, a > 0, -c / a)):
                if end is not None and _tighter(end, ends[side], side == 'upper'):ends[side] = end;by[side] = 'relation';binding[side] = (corner, fixed)
        result['needs'] = {side: None if end is None else {'value': end[0], 'closed': end[1]} for side, end in ends.items()}
    for side, end, origin in domain:
        if _tighter(end, ends[side], side == 'upper'):ends[side] = end;by[side] = origin;binding.pop(side, None)
    lower, upper = ends['lower'], ends['upper']
    result['lower'] = None if lower is None else {'value': lower[0], 'closed': lower[1], 'by': by['lower']}
    result['upper'] = None if upper is None else {'value': upper[0], 'closed': upper[1], 'by': by['upper']}
    if lower is not None and upper is not None and (lower[0] > upper[0] or (lower[0] == upper[0] and not (lower[1] and upper[1]))):
        result.update(state=EMPTY, reason='What the relation needs lies outside the values %s may take' % name);return result
    if declared is not None:result['declared_inside'] = _inside(declared, lower, upper)
    points = {}
    if step is not None:
        lattice = {'lower': None if lower is None else _up(lower, step), 'upper': None if upper is None else _down(upper, step)}
        result['lattice'] = lattice
        if lattice['lower'] is not None and lattice['upper'] is not None and lattice['lower'] > lattice['upper']:
            result.update(state=EMPTY, reason='No whole step of %s lies inside what the relation allows' % text(step));return result
        points = {side: value for side, value in lattice.items() if value is not None}
    else:
        points = {side: end[0] for side, end in (('lower', lower), ('upper', upper)) if end is not None and end[1]}
    if points:
        result['checked'] = all(witness_check(fixed, {name: text(point)}) for point in points.values() for _, fixed, _, _ in rows)
    for side, point in points.items():
        if side not in binding:continue
        corner, fixed = binding[side];holds, left = _at(fixed, name, point)
        result['ends'].append({'side': side, 'at': point, 'corner': corner, 'holds': holds, 'left': left})
        if step is not None:
            past = point + step if side == 'upper' else point - step;holds, left = _at(fixed, name, past)
            result['beyond'].append({'side': side, 'at': past, 'corner': corner, 'holds': holds, 'left': left})
    return result
