"""The exact goal face (0.8.6, "Kas's mind, no model"): room to spare, what uses it, the three zones of an input and what a
reading would settle, worked out on the one maths core.

Pure: Fraction arithmetic over math_ranges (allowed, enclose, check_box, corner_witness), which stays exactly as it is.
No Qt, no Kernel, no language model, no SymPy or Z3, and no float anywhere.

  room              the margin at the reading and at the worst corner of the ranges, as a share of the limit, and how far
                    each input may move before the relation changes (allowed, with the other inputs at their ranges; the
                    end on whole steps, rounded inward, each end rechecked at its corner and one step past it).
  swings            how much of the spread each ranged input causes on its own (the effects over the ranges).
  consumption       how much of the room at the reading each range uses on its own, what they use together beyond that,
                    and what is left: the parts add up to the room at the reading exactly.
  leverage          what a rise of 1 % in one input does to the room, as an exact share of it.
  zones             for one input: where the relation holds whatever the other inputs are, where it does not hold whatever
                    they are, and the share of the input's own range those two zones decide (decisive_share).
  settling_reading  with a meter good to +-a: the readings that settle it each way, rounded inward, each rechecked at both
                    ends of the meter by check_box.
  break_even        the tolerance on one input (+- around its reading) up to which the state stays as it is.
  break_even_factor the common factor (1+r1)(1+r2)... a product of positive inputs may grow by before the state changes.
  joined            goals joined with "and", through stac/evidence.py's truth_and.
  value_of_information  what a reading of one input is worth to joined goals: 0 when one of them already does not hold
                    whatever the values.
  two_readings      two readings of one quantity: what both allow, or CONFLICT when their ranges do not meet.
  order             goals in the order her card lists them: does not hold, cannot tell, then holds with the least room
                    (as a share of the limit) first. That order is a convention, and the words say so.

A box maps an input's name to (lo, hi) in its declared unit, as in math_ranges. Margins are in the relation's own unit (its
left side's), turned so that a positive margin means room to spare: right - left for <= and <, left - right for >= and >.
"Equal" and "not equal" have no room, so they are refused with the reason. Every failure is a math_ranges.RangeError with a
code; math_answers turns it into a state.

WORDS are her templates for these answers. None of them says "chance", "likely", "probability", "risk of" or "safe": a share
of a range is a share of the range, and the words never say otherwise.
"""
from __future__ import annotations
import copy
from fractions import Fraction
from . import math_ranges as ranges
from .math_model import RELATIONS, MathError, validate
from .math_units import rational, unit_spec
from .stac.evidence import EvidenceSupport, truth_and

HOLDS, FAILS, UNDECIDED, CONFLICT = ranges.HOLDS, ranges.FAILS, ranges.UNDECIDED, 'CONFLICT'
OPPOSITE = {'le': 'gt', 'lt': 'ge', 'ge': 'lt', 'gt': 'le'}      # "does not hold" of each relation with room
RISE = Fraction(101, 100)        # leverage: a rise of 1 %
WHOLE = Fraction(1)              # the step an end is rounded to unless another is given: whole units of the input's unit
RANK = {FAILS: 0, UNDECIDED: 1, CONFLICT: 1, HOLDS: 2}

# Her words for the goal face. Fixed words with slots; every number slot is filled from an answer with its receipt.
WORDS = {
    'room_holds': 'It holds, with {spare} to spare at worst: {share} of the limit.',
    'room_fails': 'It does not hold: over by {over}.',
    'room_undecided': 'Cannot tell: from {spare} to spare down to {over} over, across the ranges.',
    'share_of_limit': 'At worst, the room is {share} of the limit.',
    'rise': '{name} may rise to {end} before it stops holding ({exact} exactly).',
    'fall': '{name} may fall to {end} before it stops holding ({exact} exactly).',
    'no_move': '{name} may take any value here without changing it.',
    'to_hold_down': 'For it to hold, {name} would have to be at most {end} ({exact} exactly).',
    'to_hold_up': 'For it to hold, {name} would have to be at least {end} ({exact} exactly).',
    'uses': 'At the reading there is {room} of room. {parts}. Together they use {together} more, which leaves {left}.',
    'uses_alone': 'At the reading there is {room} of room. {parts}, which leaves {left}.',
    'uses_over': 'At the reading there is {room} of room. {parts}. Together they use {together} more: at worst it is over by {over}.',
    'use': '{name} uses {part}',
    'no_room': 'There is no room left at the reading, so no share of it is given.',
    'zone': 'With {name} {holds}, it holds whatever the others are; {fails}, it does not hold whatever they are.',
    'share': 'A reading of {name} settles it over {share} of its range. These are shares of the range: every part of it counts the same.',
    'first': 'Measure {name} first.',
    'settles_holds': 'With a meter good to {accuracy}, a reading at or {side} {reading} settles it: it holds.',
    'settles_fails': 'With a meter good to {accuracy}, a reading at or {side} {reading} settles it: it does not hold.',
    'nothing_settles': 'No reading of {name} can change this: it {state} whatever the values.',
    'break_even_holds': 'It holds while the tolerance on {name} is {bound} {tolerance}; beyond that I cannot tell.',
    'break_even_fails': 'It does not hold while the tolerance on {name} is {bound} {tolerance}; from there on I cannot tell.',
    'joined_fails': 'Measuring {name} cannot change this: {goal} already does not hold.',
    'order': 'Listed: what does not hold, then what I cannot tell, then what holds with the least room first, as a share of the limit.',
}


# -- the relation ---------------------------------------------------------------------------------------------------------

def relation_of(ir):
    """The relation of the model's output, one with room (<=, <, >=, >); otherwise UNSUPPORTED with the reason."""
    op = ranges.nodes_of(ir)[ranges.output(ir)]['op']
    if op not in RELATIONS:ranges.fail('UNSUPPORTED', 'Room needs one comparison, such as <=')
    if op not in OPPOSITE:ranges.fail('UNSUPPORTED', 'Equal and not equal have no room to spare; ask with <= or >= instead')
    return op


def unit_of(ir, node=None):
    """The unit the relation is said in: its own signature's (its left side's)."""
    return ir['signatures'][node or ranges.output(ir)]['unit']


def _own(ir, base):
    return Fraction(base) / unit_spec(unit_of(ir))[1]


def margin(ir, box=None):
    """(lo, hi, status) of the margin over the box, in the relation's own unit: positive is room to spare."""
    relation = relation_of(ir);slack = ranges.enclose(ir, box)
    lo, hi = (slack.lo, slack.hi) if relation in ('le', 'lt') else (-slack.hi, -slack.lo)
    return _own(ir, lo), _own(ir, hi), slack.status


def at_reading(ir):
    """The margin at the declared values: one exact number in the relation's unit."""
    return margin(ir, {})[0]


def opposite(ir):
    """The same model with its relation turned to "does not hold" (<= to >, < to >=, and back)."""
    relation = relation_of(ir);model = copy.deepcopy(ir['model'])
    for node in model['nodes']:
        if node['id'] == ranges.output(ir):node['op'] = OPPOSITE[relation]
    try:return validate(model)
    except MathError as exc:ranges.fail(exc.code, str(exc))


def declared(ir, name):
    v = ir['model']['variables'].get(name)
    if v is None:ranges.fail('MISSING_INPUT', 'The relation does not use ' + str(name))
    return rational(v['value']) if 'value' in v else None


def _box(ir, box):
    return ranges.checked_box(ir, box)


def _others(box, name):
    return {k: v for k, v in box.items() if k != name}


# -- rounding to steps (math_ranges' rule: inward, and an open end on the lattice moves one step in) -----------------------

def _down(value, closed, step):
    k = value // step
    if not closed and k * step == value:k -= 1
    return k * step


def _up(value, closed, step):
    k = -((-value) // step)
    if not closed and k * step == value:k += 1
    return k * step


# -- room -----------------------------------------------------------------------------------------------------------------

def room(ir, box=None, step=None, roles=None):
    """The room of a relation over the box: {'relation', 'unit', 'state', 'for_all', 'at_reading', 'worst', 'best',
    'status', 'limit' (the right side at the declared values), 'share_of_limit' (worst / limit), 'moves' (for each input
    that is not a limit: how far it may move, with the others at their ranges)}. step: {name: step} or one step for all,
    in each input's declared unit; whole units when not given."""
    relation = relation_of(ir);box = _box(ir, box);roles = dict(roles or {})
    found = ranges.check_box(ir, box)
    worst, best, status = margin(ir, box)
    node = ranges.nodes_of(ir)[ranges.output(ir)]
    limit = None
    try:
        right = ranges.enclose(ir, {}, node['right'])
        if right.lo == right.hi:limit = _own(ir, right.lo)        # a limit with no range of its own
    except ranges.RangeError:limit = None
    try:reading = at_reading(ir)
    except ranges.RangeError:reading = None
    share = worst / abs(limit) if limit else None
    moves = []
    for name in sorted(ir['model']['variables']):
        if roles.get(name) == 'limit':continue
        moves.append(move(ir, box, name, step.get(name) if isinstance(step, dict) else step))
    return {'relation': relation, 'unit': unit_of(ir), 'state': found['state'], 'for_all': found['for_all'], 'at_reading': reading,
            'worst': worst, 'best': best, 'status': status, 'limit': limit, 'share_of_limit': share, 'moves': moves}


def move(ir, box, name, step=None):
    """How far `name` may move before the relation stops holding, with the other inputs at their ranges: the exact ends,
    the ends on whole steps (rounded inward), the distance from the reading and its share of the reading, and each end
    rechecked by math_model.evaluate at the corner that sets it and one step past it. A move that cannot be worked out
    keeps its reason."""
    box = _box(ir, box);v = ir['model']['variables'][name];here = declared(ir, name)
    step = ranges.exact(step) if step is not None else WHOLE
    row = {'name': name, 'unit': v['unit'], 'declared': here, 'step': step, 'state': None, 'lower': None, 'upper': None,
           'lattice': None, 'rise': None, 'fall': None, 'rechecked': None, 'ends': [], 'beyond': [], 'reason': ''}
    try:found = ranges.allowed(ir, name, _others(box, name), step=step)
    except ranges.RangeError as exc:
        row.update(state=exc.code, reason=str(exc));return row
    row.update(state=found['state'], lower=found['lower'], upper=found['upper'], lattice=found['lattice'], ends=found['ends'],
               beyond=found['beyond'], reason=found['reason'])
    if found['ends']:
        row['rechecked'] = all(e['holds'] is True for e in found['ends']) and all(b['holds'] is False for b in found['beyond'])
    if here is not None and found['state'] == ranges.ALLOWED:
        upper, lower = found['upper'], found['lower']
        if upper and upper['by'] == 'relation':
            row['rise'] = {'to': upper['value'], 'on_step': (found['lattice'] or {}).get('upper'), 'by': upper['value'] - here,
                           'share': (upper['value'] - here) / abs(here) if here else None}
        if lower and lower['by'] == 'relation':
            row['fall'] = {'to': lower['value'], 'on_step': (found['lattice'] or {}).get('lower'), 'by': here - lower['value'],
                           'share': (here - lower['value']) / abs(here) if here else None}
    return row


def order(judged):
    """Goals in the order her card lists them: does not hold, cannot tell, then holds with the least room first as a share
    of the limit (the room itself where there is no limit). judged: [(key, room)] -> the keys in that order."""
    def key(item):
        name, said = item
        share = said.get('share_of_limit');share = said.get('worst') if share is None else share
        return (RANK.get(said.get('state'), 1), share if share is not None else Fraction(0), str(name))
    return [name for name, _ in sorted(judged, key=key)]


# -- what moves it, and what uses the room --------------------------------------------------------------------------------

def swings(ir, box):
    """How much of the spread each ranged input causes on its own, the others at their declared values: {'whole': width
    with every range, 'by': {name: width}, 'shares': {name: width / whole}} in the relation's unit (for an expression that
    is not a relation, in its own unit). Never per-unit derivatives: W/V and W/mA cannot be compared."""
    box = _box(ir, box)
    def width(part):
        e = ranges.enclose(ir, part);return _own(ir, e.hi - e.lo)
    whole = width(box);by = {name: width({name: box[name]}) for name in sorted(box)}
    return {'whole': whole, 'by': by, 'shares': {name: (w / whole if whole else None) for name, w in by.items()}}


def consumption(ir, box):
    """What uses the room: {'at_reading', 'uses': {name: the room its range uses on its own}, 'together': what the ranges
    use together beyond the parts, 'left': the room left at the worst corner, 'no_room'}. The identity holds exactly:
    sum(uses) + together + left == at_reading."""
    relation_of(ir);box = _box(ir, box)
    here = at_reading(ir);worst = margin(ir, box)[0]
    uses = {name: here - margin(ir, {name: box[name]})[0] for name in sorted(box)}
    together = (here - worst) - sum(uses.values(), Fraction(0))
    return {'at_reading': here, 'uses': uses, 'together': together, 'left': worst, 'no_room': here <= 0}


def leverage(ir, name, rise=RISE):
    """What a rise of 1 % in `name` does to the room at the reading, as an exact share of that room (negative: it takes
    room). None when there is no room at the reading to take a share of."""
    relation_of(ir);here = at_reading(ir);value = declared(ir, name)
    if value is None:ranges.fail('MISSING_INPUT', 'No value for ' + name)
    if not here:return None
    moved = margin(ir, {name: (value * rise, value * rise)})[0]
    return (moved - here) / here


# -- the three zones of an input, and what a reading would settle ---------------------------------------------------------

def _piece(found):
    """(lower, upper) of an allowed set, each (value, closed) or None; None for an empty one."""
    if found['state'] == ranges.EMPTY:return None
    lower, upper = found['lower'], found['upper']
    return (None if lower is None else (lower['value'], lower['closed']), None if upper is None else (upper['value'], upper['closed']))


def _length(piece, lo, hi):
    if piece is None:return Fraction(0)
    lower, upper = piece
    a = lo if lower is None else max(lo, lower[0]);b = hi if upper is None else min(hi, upper[0])
    return max(Fraction(0), b - a)


def zones(ir, box, name, within=None):
    """The three zones of `name`, the other inputs at their ranges: {'name', 'unit', 'range' (its own range, or its
    reading), 'holds' and 'fails' (the zones as (lower, upper) ends, each (value, closed) or None; None when empty),
    'decided' (the length of each inside its range), 'share' (the decisive share: the decided length over the range's
    width; None for a range of one value)}. The zones come from two allowed calls: the relation, and its opposite."""
    relation_of(ir);box = _box(ir, box);v = ir['model']['variables'].get(name)
    if v is None:ranges.fail('MISSING_INPUT', 'The relation does not use ' + str(name))
    if name in box:lo, hi = box[name]
    else:
        here = declared(ir, name)
        if here is None:ranges.fail('MISSING_INPUT', 'No value or range for ' + name)
        lo = hi = here
    others = _others(box, name)
    holds = _piece(ranges.allowed(ir, name, others, within))
    fails = _piece(ranges.allowed(opposite(ir), name, others, within))
    decided = {'holds': _length(holds, lo, hi), 'fails': _length(fails, lo, hi)}
    share = (decided['holds'] + decided['fails']) / (hi - lo) if hi > lo else None
    return {'name': name, 'unit': v['unit'], 'range': (lo, hi), 'holds': holds, 'fails': fails, 'decided': decided, 'share': share}


def decisive_share(ir, box, name):
    """The share of `name`'s range over which a reading of it settles the relation, exactly."""
    return zones(ir, box, name)['share']


def _readings(piece, accuracy, step):
    """The readings r with [r - a, r + a] inside the zone, rounded inward to the step: (lower, upper), each a value or None;
    None when no reading fits."""
    if piece is None:return None
    lower, upper = piece
    low = None if lower is None else _up(lower[0] + accuracy, lower[1], step)
    high = None if upper is None else _down(upper[0] - accuracy, upper[1], step)
    if low is not None and high is not None and low > high:return None
    return low, high


def settling_reading(ir, box, name, accuracy, step=None):
    """With a meter good to +-accuracy on `name` (its declared unit), the readings that settle the relation each way,
    rounded inward to the step (whole units unless given), each rechecked at both ends of the meter by check_box with the
    other inputs at their ranges: {'name', 'unit', 'accuracy', 'step', 'holds' and 'fails' ((lower, upper) of the
    readings that settle it that way, or None), 'rechecks' [{'reading', 'range', 'expected', 'state'}], 'checked'}."""
    accuracy = ranges.exact(accuracy);step = ranges.exact(step) if step is not None else WHOLE
    if accuracy < 0:ranges.fail('DOMAIN_ERROR', 'Say a meter\'s accuracy as a size')
    if step <= 0:ranges.fail('UNSUPPORTED', 'A step is a positive number')
    box = _box(ir, box);found = zones(ir, box, name);others = _others(box, name)
    said = {'name': name, 'unit': found['unit'], 'accuracy': accuracy, 'step': step,
            'holds': _readings(found['holds'], accuracy, step), 'fails': _readings(found['fails'], accuracy, step), 'rechecks': []}
    for expected in (HOLDS, FAILS):
        readings = said['holds' if expected == HOLDS else 'fails']
        if not readings:continue
        for reading in readings:
            if reading is None:continue
            span = (reading - accuracy, reading + accuracy)
            try:state = ranges.check_box(ir, {**others, name: span})['state']
            except ranges.RangeError as exc:state = exc.code
            said['rechecks'].append({'reading': reading, 'range': span, 'expected': expected, 'state': state})
    said['checked'] = all(row['state'] == row['expected'] for row in said['rechecks']) if said['rechecks'] else None
    return said


# -- break-even -----------------------------------------------------------------------------------------------------------

def break_even(ir, box, name):
    """The tolerance on `name` (+- around its reading, the other inputs at their ranges) up to which the state stays as it
    is: {'name', 'unit', 'state' (at the reading), 'tolerance' (exact, in its declared unit; None when no tolerance changes
    it), 'closed' (True: the state stays at that tolerance too; False: only below it), 'then' (UNDECIDED)}. A state that
    is already UNDECIDED at the reading has a tolerance of 0."""
    relation_of(ir);box = _box(ir, box);others = _others(box, name);here = declared(ir, name)
    if here is None:ranges.fail('MISSING_INPUT', 'No value for ' + name)
    state = ranges.check_box(ir, others)['state']
    unit = ir['model']['variables'][name]['unit']
    if state == UNDECIDED:return {'name': name, 'unit': unit, 'state': state, 'tolerance': Fraction(0), 'closed': False, 'then': UNDECIDED}
    piece = _piece(ranges.allowed(ir if state == HOLDS else opposite(ir), name, others))
    nearest = None
    for end, distance in ((piece[0], None if piece[0] is None else here - piece[0][0]), (piece[1], None if piece[1] is None else piece[1][0] - here)):
        if distance is None:continue
        candidate = (distance, end[1])
        if nearest is None or distance < nearest[0] or (distance == nearest[0] and not end[1]):nearest = candidate
    if nearest is None:return {'name': name, 'unit': unit, 'state': state, 'tolerance': None, 'closed': True, 'then': state}
    return {'name': name, 'unit': unit, 'state': state, 'tolerance': nearest[0], 'closed': nearest[1], 'then': UNDECIDED}


def _product(ir, node):
    """The variables of a node that is a product of variables only, each once; None otherwise."""
    nodes = ranges.nodes_of(ir);found = []
    def walk(ident):
        n = nodes[ident]
        if n['op'] == 'variable':found.append(n['name']);return True
        return n['op'] == 'mul' and walk(n['left']) and walk(n['right'])
    if not walk(node) or len(set(found)) != len(found):return None
    return sorted(found)


def break_even_factor(ir):
    """For "a product of positive inputs <= a limit" (or >=): the common factor (1+r1)(1+r2)... the product may grow by
    (or shrink by, for >=) before it reaches the limit, exactly: limit / product at the reading. None when the left side
    is not a product of inputs each used once, or a value is not positive."""
    relation = relation_of(ir);node = ranges.nodes_of(ir)[ranges.output(ir)]
    names = _product(ir, node['left'])
    if not names:return None
    values = [declared(ir, n) for n in names]
    if any(v is None or v <= 0 for v in values):return None
    left = ranges.enclose(ir, {}, node['left']).lo;right = ranges.enclose(ir, {}, node['right'])
    if right.lo != right.hi or left <= 0 or right.lo <= 0:return None
    factor = right.lo / left
    return {'names': names, 'factor': factor if relation in ('le', 'lt') else 1 / factor, 'relation': relation}


# -- joined goals, and two readings ---------------------------------------------------------------------------------------

SUPPORT = {HOLDS: EvidenceSupport(True, False), FAILS: EvidenceSupport(False, True), UNDECIDED: EvidenceSupport(False, False),
           CONFLICT: EvidenceSupport(True, True)}


def state_of(support):
    return {(True, False): HOLDS, (False, True): FAILS, (False, False): UNDECIDED, (True, True): CONFLICT}[(support.positive, support.negative)]


def joined(states):
    """Goals joined with "and": the Belnap conjunction of their states (stac/evidence.truth_and)."""
    states = list(states)
    if not states:ranges.fail('MISSING_INPUT', 'Join at least one goal')
    found = SUPPORT[states[0]]
    for state in states[1:]:found = truth_and(found, SUPPORT[state])
    return state_of(found)


def value_of_information(parts, name):
    """What a reading of `name` is worth to goals joined with "and": parts [{'state', 'shares': {input: decisive share}}].
    0 when the joined goals already hold or already do not hold whatever the values (a conjunct does not hold); otherwise
    the largest decisive share it has on a goal it touches that cannot be told. Exact."""
    parts = list(parts);state = joined(p['state'] for p in parts)
    if state in (HOLDS, FAILS):return Fraction(0)
    shares = [p['shares'][name] for p in parts if p['state'] in (UNDECIDED, CONFLICT) and p.get('shares', {}).get(name) is not None]
    return max(shares) if shares else Fraction(0)


def two_readings(a, b):
    """Two readings of one quantity, each (lo, hi): {'state': CONFLICT when their ranges do not meet ("cannot tell: the
    two readings cannot both be right"), otherwise None with 'both' the range both allow}."""
    lo, hi = max(ranges.exact(a[0]), ranges.exact(b[0])), min(ranges.exact(a[1]), ranges.exact(b[1]))
    if lo > hi:return {'state': CONFLICT, 'both': None}
    return {'state': None, 'both': (lo, hi)}
