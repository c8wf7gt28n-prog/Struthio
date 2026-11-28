"""Answers of the one maths core (0.8.5, "Maths in lines"): the record ledger.math-answer/1, its words, and math.answer.

One answer serves both faces. A line on a problem sheet,

    math problem:ID | solve "REL" for NAME [| within LO HI] [| step S] [| given NAME LO HI] (up to four) [| unit U]
    math problem:ID | range "EXPR" [| given NAME LO HI] (up to four) [| unit U]
    math problem:ID | check "REL" [| given NAME LO HI] (up to four)

compiles (stac_bridge) to the Kernel operation math.answer, a read: it reads the sheet with the freshness of its sources
(problems.get), the owner's tolerances (tolerances.standing) and the model math_service.model_for makes, and answers
through math_ranges. From the goal slice on, her goals call answer() in process with bindings to cells
(bindings_from_cells), and two more stages answer for a relation (0.8.6 S1, the exact goal face, through math_zones):

    room     the margin at the reading and at the worst corner, its share of the limit, how far each input may move before
             the relation changes, and what uses the room;
    settle   that, and for each input with a range its three zones, the share of its range a reading of it settles, the
             reading that would settle it with a meter of a given accuracy, and the tolerance it breaks even at.

math.answer writes no record of its own; the Kernel keeps its audit and activity rows, as for every read; stac.observe stores the answer.

The record carries the question as asked, the model and its digest, its assumptions and obligations, every input with its
origin (PROBLEM_REVISION, DECLARED_SCENARIO, GIVEN_IN_LINE, OWNER_TOLERANCE, SHEET_CELL or FREED), its source and its
tolerance, the result, the state (HOLDS, FAILS or UNDECIDED for the one real value; ANSWERED when the stage asks no
yes-or-no question; an error state otherwise), for_all (every value in the ranges), the witness, the guarantee, at most
eight steps of derivation, the freshness, the words the owner reads, and the hashes of its own implementation (the hashed
files of math_service are not touched, so a new answer never makes an older calculation historical). answer() never raises.
"""
from __future__ import annotations
import hashlib
import math
import re
from fractions import Fraction
from pathlib import Path
from . import math_ranges as ranges, project_desk as records
from .math_model import MathError, RELATIONS, evaluate
from .math_units import number_record, quantity_record, rational, unit_spec

SCHEMA = 'ledger.math-answer/1'
STAGES = ('calculate', 'solve', 'range', 'check')      # the line verbs (math_typed reads these)
GOAL_STAGES = ('room', 'settle')                       # 0.8.6 S1: the exact goal face, through math_zones
ALL_STAGES = STAGES + GOAL_STAGES
ERRORS = ('DIMENSION_MISMATCH', 'DOMAIN_ERROR', 'UNSUPPORTED', 'MISSING_INPUT', 'INCOMPATIBLE_OUTPUT_UNIT',
          'EXACT_ARITHMETIC_SIZE_BOUND', 'DENOMINATOR_MAY_BE_ZERO')
IMPLEMENTED = ('math_ranges.py', 'math_answers.py', 'math_model.py', 'math_units.py')
GOAL_IMPLEMENTED = ('math_zones.py',)                  # hashed too in a room or settle answer, which it works out
FIGURES = 4                  # significant figures of a number in words; the exact value stands beside it
HEADINGS = {'HOLDS': 'Holds', 'FAILS': 'Does not hold', 'UNDECIDED': 'Cannot tell'}      # the Field's own (field_page)
STAGE_HEADINGS = {'calculate': 'Worked out', 'range': 'Range', 'solve': 'Solve for %s', 'room': 'Room to spare', 'settle': 'What would settle it'}
SIGNS = {'le': '<=', 'lt': '<', 'ge': '>=', 'gt': '>', 'eq': '=', 'ne': '!='}
GUARANTEES = {'EXACT_VALUE': 'an exact value, in exact fractions throughout',
              'EXACT_RANGE': 'an exact range: both of its ends are values the expression takes',
              'SOUND_ENCLOSURE': 'a sound range: every value lies inside it, though it may be wider than the true range',
              'EXACT_ALLOWED_SET': 'the exact allowed set, its ends worked out again with the solved quantity freed'}
FRESHNESS = {'CURRENT': 'The sheet\'s sources are as they were when it was made.',
             'REVIEW_REQUIRED': 'The sheet\'s sources have changed since it was made: review them before relying on this.'}
TOLERANCE_STATES = {'APPLIES': 'said at this revision', 'CARRIED_OVER': 'carried over: the value has not changed since',
                    'RECHECK': 'needs your recheck: the value changed since, so it is not applied'}
NAME = {'type': 'string', 'minLength': 1, 'maxLength': 64}
NUMBER = {'type': 'string', 'minLength': 1, 'maxLength': 100}
GIVEN = {'type': 'object', 'additionalProperties': False, 'properties': {'name': NAME, 'lo': NUMBER, 'hi': NUMBER}, 'required': ['name', 'lo', 'hi']}
ACCURACY = {'type': 'object', 'additionalProperties': False, 'properties': {'name': NAME, 'amount': NUMBER}, 'required': ['name', 'amount']}
FIELDS = {'math.answer': ({'id': records.ID, 'stage': {'type': 'string', 'enum': list(ALL_STAGES)},
                           'expression': {'type': 'string', 'minLength': 1, 'maxLength': 1000}, 'for': NAME,
                           'within': {'type': 'array', 'minItems': 2, 'maxItems': 2, 'items': NUMBER}, 'step': NUMBER,
                           'given': {'type': 'array', 'maxItems': 4, 'items': GIVEN}, 'unit': {'type': 'string', 'minLength': 1, 'maxLength': 64},
                           'accuracy': {'type': 'array', 'maxItems': 4, 'items': ACCURACY}},
                          ['id', 'stage', 'expression'])}
SCOPES = {'math.answer': 'read'}


# What the owner reads when an answer cannot be worked out, by its state; a reason in the code's own terms is not shown.
REFUSALS = {'DIMENSION_MISMATCH': 'quantities of different kinds are added or compared, so their units do not fit together',
            'DOMAIN_ERROR': 'a value lies outside what it may take', 'UNSUPPORTED': 'the maths core does not answer this kind of question',
            'MISSING_INPUT': 'a quantity it needs has no value', 'INCOMPATIBLE_OUTPUT_UNIT': 'the answer is not a quantity that unit can show',
            'EXACT_ARITHMETIC_SIZE_BOUND': 'a number here is too long to work with exactly',
            'DENOMINATOR_MAY_BE_ZERO': 'a denominator may be zero over these ranges'}
REWORDS = ((re.compile(r'Zero denominator\b.*'), 'a denominator is zero'), (re.compile(r'Negative power of zero\b.*'), 'zero is raised to a negative power'),
           (re.compile(r'UNKNOWN_OR_AMBIGUOUS_UNIT: (.+)'), r'\1 is not a unit Kas knows'))
INTERNAL = re.compile(r'\b[A-Z][A-Z0-9]*_[A-Z0-9_]+\b|\bn\d+\b|incompatible quantities|fragment|\bZ3\b|SymPy|\bnodes?\b')


def _hashes(names=IMPLEMENTED):
    return {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() for name in names}


IMPLEMENTATION = _hashes()      # hashed once, as loaded: the code that works the answers out, not the files as they are later
GOAL_IMPLEMENTATION = _hashes(GOAL_IMPLEMENTED)


def implementation(stage=None):
    """sha256 of each file an answer depends on (its own two and the exact base under them), as they were loaded; a room
    or settle answer adds math_zones, which works it out."""
    return {**IMPLEMENTATION, **(GOAL_IMPLEMENTATION if stage in GOAL_STAGES else {})}


# -- numbers as the owner reads them --------------------------------------------------------------------------------------

def rounded(value, toward=None):
    """`value` to four significant figures: 'down', 'up', or to the nearest."""
    value = Fraction(value)
    if value == 0:return value
    size = abs(value);power = len(str(size.numerator // size.denominator)) - 1 if size >= 1 else -1
    while size < Fraction(10) ** power:power -= 1
    scale = Fraction(10) ** (FIGURES - 1 - power);x = value * scale
    return (math.floor(x) if toward == 'down' else math.ceil(x) if toward == 'up' else math.floor(x + Fraction(1, 2))) / scale


def figure(value, unit, toward=None):
    """An exact value in words: its decimal when that is short and exact; otherwise four figures rounded `toward` ('down',
    'up'; outward for a range, inward for an allowed end) with the exact value beside it."""
    value = Fraction(value);exact = number_record(value);unit = '' if unit in ('1', '') else ' ' + unit
    if exact['decimal_exact'] and len(exact['decimal'].lstrip('-').replace('.', '').lstrip('0')) <= 6:return exact['decimal'] + unit
    near = number_record(rounded(value, toward))['decimal']
    return '%s%s (exact %s%s)' % (near, unit, exact['decimal'] if exact['decimal_exact'] else exact['rational'], unit)


def exactly(value, unit):
    """An exact value in words with nothing rounded: its decimal when that is exact, otherwise its fraction."""
    exact = number_record(Fraction(value));unit = '' if unit in ('1', '') else ' ' + unit
    return (exact['decimal'] if exact['decimal_exact'] else exact['rational']) + unit


def span_words(lo, hi, unit):
    """A range in words, rounded outward."""
    return figure(lo, unit) if lo == hi else '%s to %s' % (figure(lo, '', 'down').strip(), figure(hi, unit, 'up'))


def number(value, unit):return {**number_record(Fraction(value)), 'unit': unit}


def _dimension(ir, node):return ir['signatures'][node]['dimension']


def _quantity(base, ir, node, unit):
    return quantity_record(Fraction(base), _dimension(ir, node), unit or ir['signatures'][node]['unit'])


def _span(enclosure, ir, node, unit):
    return [_quantity(enclosure.lo, ir, node, unit), _quantity(enclosure.hi, ir, node, unit)]


# -- the record -----------------------------------------------------------------------------------------------------------

def _code(exc):
    if isinstance(exc, (MathError, ranges.RangeError)):return exc.code
    message = str(exc)
    return next((code for code in ERRORS if code in message), 'UNSUPPORTED')


def _inputs(ir, inputs, solved):
    """The record's inputs, and the box of ranges (exact, in declared units) the stage works over."""
    rows = [];box = {}
    for name, v in ir['model']['variables'].items():
        given = dict((inputs or {}).get(name) or {});span = given.get('range')
        if span is not None and name == solved:ranges.fail('UNSUPPORTED', '%s is what is solved for, so it cannot also have a range' % name)
        if span is not None:box[name] = (ranges.exact(span[0]), ranges.exact(span[1]))
        origin = 'FREED' if name == solved else given.get('origin') or ('GIVEN_IN_LINE' if span else 'DECLARED_SCENARIO')
        rows.append({'name': name, 'unit': v['unit'], 'value': number(rational(v['value']), v['unit']) if 'value' in v else None,
                     'range': [number(box[name][0], v['unit']), number(box[name][1], v['unit'])] if name in box else None,
                     'origin': origin, 'source': given.get('source'), 'tolerance': given.get('tolerance'), 'role': given.get('role')})
    return rows, box


def refused(stage, asked, code, reason, freshness='CURRENT'):
    """An answer that could not be worked out, as a record: the state says why, and nothing else is claimed."""
    value = {'schema': SCHEMA, 'stage': stage, 'asked': dict(asked or {}), 'model': None, 'model_digest': None, 'assumptions': [],
             'obligations': [], 'inputs': [], 'result': None, 'state': code, 'for_all': None, 'witness': None, 'guarantee': None,
             'derivation': [], 'freshness': freshness, 'reason': reason}
    return _sealed(value)


def _sealed(value):
    value.setdefault('reason', '')
    value.update(implementation=implementation(value.get('stage')), model_calls=0, physical_qualification=False)
    value['words'] = words(value)
    value['digest'] = records.digest({k: v for k, v in value.items() if k != 'digest'})
    return value


def _witness(found, ir, rows):
    if not found:return None
    units = {row['name']: row['unit'] for row in rows}
    return {'assignment': {name: number(value, units[name]) for name, value in found['assignment'].items()}, 'value': found['value']}


def _method(enclosure, box):
    if not box:return 'Worked out at the declared values in exact fractions.'
    if enclosure.status == ranges.WIDENED:return 'Interval arithmetic, its ends moved outward to stay within 2048 bits.'
    if enclosure.status == ranges.SOUND:return 'Interval arithmetic: a ranged quantity repeats or sits under an even power, so the range may be wider than the true one.'
    return 'The range from its exact form over the ranges: each end is reached at a corner of them.'


def answer(stage, ir, inputs=None, asked=None, freshness='CURRENT'):
    """ledger.math-answer/1 for one stage over a compiled model (math_model.compile_expression, declared values in it).
    inputs: {name: {'range': (lo, hi) in its declared unit or None, 'origin', 'source', 'tolerance'}}; a name left out has
    no range. asked: {'expression', 'for', 'within', 'step', 'unit'}. Never raises: a failure is the record's state."""
    asked = dict(asked or {});unit = asked.get('unit');solved = asked.get('for')
    if stage not in ALL_STAGES:return refused(stage, asked, 'UNSUPPORTED', 'Ask calculate, solve, range, check, room or settle', freshness)
    if solved and stage != 'solve':return refused(stage, asked, 'UNSUPPORTED', 'Only solve takes a quantity to solve for', freshness)
    try:rows, box = _inputs(ir, inputs, solved)
    except (ValueError, ZeroDivisionError) as exc:return refused(stage, asked, _code(exc), str(exc), freshness)
    if stage == 'calculate':
        box = {}
        for row in rows:row['range'] = None
    value = {'schema': SCHEMA, 'stage': stage, 'asked': asked, 'model': ir['model'], 'model_digest': ir['model_digest'],
             'assumptions': list(ir['model']['assumptions']), 'obligations': [dict(d) for d in ir['domain_conditions']], 'inputs': rows,
             'result': None, 'state': None, 'for_all': None, 'witness': None, 'guarantee': None, 'derivation': [], 'freshness': freshness}
    out = ranges.output(ir);node = ranges.nodes_of(ir)[out];relation = node['op'] if node['op'] in RELATIONS else None
    steps = value['derivation']
    steps.append('The question: %s %s%s.' % (stage, asked.get('expression') or 'the model', ' for ' + solved if solved else ''))
    try:
        if box:steps.append('Ranges: ' + '; '.join('%s %s' % (name, span_words(lo, hi, ir['model']['variables'][name]['unit'])) for name, (lo, hi) in sorted(box.items())) + '.')
        if stage == 'solve':_solve(value, ir, box, asked)
        elif stage in GOAL_STAGES:_goal_stage(value, ir, node, box, asked)
        elif relation is None and stage == 'check':ranges.fail('UNSUPPORTED', 'A check needs one comparison, such as <=')
        elif relation is None:_quantity_stage(value, ir, out, box, unit)
        else:_relation_stage(value, ir, node, box, unit)
    except (ValueError, ZeroDivisionError) as exc:
        code = _code(exc);value.update(state=code, reason=str(exc), result=None, for_all=None, witness=None, guarantee=None)
        if code == 'DENOMINATOR_MAY_BE_ZERO':value['obligations'].append({'condition': 'DENOMINATOR_MAY_BE_ZERO', 'detail': str(exc)})
    value['derivation'] = steps[:8]
    return _sealed(value)


def _quantity_stage(value, ir, out, box, unit):
    if value['stage'] == 'calculate':
        worked = evaluate(ir, output_unit=unit)
        if worked['state'] not in ('FEASIBLE', 'INFEASIBLE', 'UNKNOWN'):ranges.fail(worked['state'], worked.get('reason', ''))
        row = worked['outputs'][0]
        if row['state'] != 'EXACT':ranges.fail('MISSING_INPUT', 'No value for ' + ', '.join(worked['missing']))
        value.update(result={'value': row['value']}, state='ANSWERED', guarantee='EXACT_VALUE')
        value['derivation'].append('Worked out by the same exact evaluator as every calculation.');return
    enclosure = ranges.enclose(ir, box)
    value.update(result={'range': _span(enclosure, ir, out, unit), 'status': enclosure.status}, state='ANSWERED',
                 guarantee='EXACT_RANGE' if enclosure.status == ranges.ATTAINED else 'SOUND_ENCLOSURE')
    value['derivation'].append(_method(enclosure, box))


def _relation_stage(value, ir, node, box, unit):
    found = ranges.check_box(ir, box);left = node['left']
    value.update(result={'relation': found['relation'], 'left': _span(found['left'], ir, left, unit), 'right': _span(found['right'], ir, left, unit),
                         'slack': _span(found['slack'], ir, left, unit), 'status': found['slack'].status},
                 state=found['state'], for_all=found['for_all'], witness=_witness(found['witness'], ir, value['inputs']),
                 guarantee='EXACT_VALUE' if not box else 'EXACT_RANGE' if found['slack'].status == ranges.ATTAINED else 'SOUND_ENCLOSURE')
    steps = value['derivation'];steps.append(_method(found['slack'], box));slack = value['result']['slack']
    steps.append('Decided on the slack, right side minus left: %s.' % span_words(rational(slack[0]['rational']), rational(slack[1]['rational']), slack[0]['unit']))
    if value['witness']:
        steps.append('The corner furthest from holding, worked out again: %s gives %s %s.' % (
            ', '.join('%s %s %s' % (k, v['decimal'], v['unit']) for k, v in value['witness']['assignment'].items()), value['witness']['value']['decimal'], value['witness']['value']['unit']))


def _solve(value, ir, box, asked):
    name = asked.get('for')
    if not name:ranges.fail('UNSUPPORTED', 'Say which quantity to solve for')
    unit = asked.get('unit');declared = ir['model']['variables'].get(name, {}).get('unit')
    found = ranges.allowed(ir, name, box, asked.get('within'), asked.get('step'))
    shown = unit or found['unit']
    if unit_spec(shown)[0] != unit_spec(found['unit'])[0]:ranges.fail('INCOMPATIBLE_OUTPUT_UNIT', '%s is not a unit of %s' % (unit, name))
    def at(x):return number(Fraction(x) * unit_spec(declared)[1] / unit_spec(shown)[1], shown)
    def end(e):return None if e is None else {'value': at(e['value']), 'closed': e['closed'], **({'by': e['by']} if 'by' in e else {})}
    def point(row):return {'side': row['side'], 'at': at(row['at']), 'holds': row['holds'], 'left': row['left'],
                           'corner': {k: number(v, ir['model']['variables'][k]['unit']) for k, v in row['corner'].items()}}
    allowed = {'state': found['state'], 'name': name, 'unit': shown, 'relation': found['relation'], 'lower': end(found['lower']), 'upper': end(found['upper']),
               'needs': {side: end(e) for side, e in found['needs'].items()}, 'step': None if found['step'] is None else at(found['step']),
               'lattice': None if found['lattice'] is None else {side: None if x is None else at(x) for side, x in found['lattice'].items()},
               'declared': None if found['declared'] is None else at(found['declared']), 'declared_inside': found['declared_inside'],
               'checked': found['checked'], 'ends': [point(r) for r in found['ends']], 'beyond': [point(r) for r in found['beyond']],
               'corners': found['corners'], 'reason': found['reason']}
    # the exact allowed set is claimed only when its ends were worked out again: an open end, or none, claims nothing
    value.update(result={'allowed': allowed}, state='ANSWERED', guarantee='EXACT_ALLOWED_SET' if found['checked'] is True else None)
    steps = value['derivation']
    steps.append('Solved %s %s 0 for %s at %d corner%s of the ranges, keeping the tightest end.' % (
        'left - right', SIGNS[found['relation']], name, found['corners'], '' if found['corners'] == 1 else 's'))
    if asked.get('within'):steps.append('Kept within %s to %s %s, as asked.' % (asked['within'][0], asked['within'][1], declared))
    if found['step'] is not None:steps.append('Rounded inward to whole steps of %s %s.' % (figure(found['step'], '').strip(), declared))
    if found['checked'] is not None:steps.append('Its end%s worked out again with %s freed: %s.' % (
        's' if len(found['ends']) > 1 else '', name, 'holds' if found['checked'] else 'DOES NOT HOLD'))


# -- the exact goal face: room and settle (0.8.6 S1) ----------------------------------------------------------------------

def _end(e, unit):
    return None if e is None else {'value': number(e['value'], unit), 'closed': e['closed'], **({'by': e['by']} if e.get('by') else {})}


def _piece(piece, unit):
    if piece is None:return None
    lower, upper = piece
    return {'lower': None if lower is None else {'value': number(lower[0], unit), 'closed': lower[1]},
            'upper': None if upper is None else {'value': number(upper[0], unit), 'closed': upper[1]}}


def _share(value):return None if value is None else number_record(Fraction(value))


def _goal_stage(value, ir, node, box, asked):
    """room and settle: the relation over the ranges (check_box), its margin at the reading and at the worst corner, how
    far each input that is not a limit may move (math_zones.room), what uses the room and what moves it most; settle adds,
    for each input with a range, its three zones, the share of its range a reading settles, the reading that settles it
    with the meter's accuracy asked, and each input's break-even tolerance."""
    from . import math_zones as zones
    roles = {row['name']: row['role'] for row in value['inputs'] if row.get('role')}
    found = ranges.check_box(ir, box);left = node['left']
    room = zones.room(ir, box, asked.get('step'), roles);unit = room['unit']
    def num(x, u=unit):return None if x is None else number(x, u)
    def way(m, side, u):
        w = m[side]
        return None if not w else {'to': num(w['to'], u), 'on_step': num(w['on_step'], u), 'by': num(w['by'], u), 'share': _share(w['share'])}
    moves = [{'name': m['name'], 'unit': m['unit'], 'declared': num(m['declared'], m['unit']), 'state': m['state'], 'step': num(m['step'], m['unit']),
              'lower': _end(m['lower'], m['unit']), 'upper': _end(m['upper'], m['unit']), 'rise': way(m, 'rise', m['unit']),
              'fall': way(m, 'fall', m['unit']), 'rechecked': m['rechecked'], 'reason': m['reason']} for m in room['moves']]
    result = {'relation': found['relation'], 'left': _span(found['left'], ir, left, None), 'right': _span(found['right'], ir, left, None),
              'slack': _span(found['slack'], ir, left, None), 'status': found['slack'].status, 'unit': unit,
              'at_reading': num(room['at_reading']), 'worst': num(room['worst']), 'best': num(room['best']), 'limit': num(room['limit']),
              'share_of_limit': _share(room['share_of_limit']), 'moves': moves, 'uses': None, 'swings': None, 'leverage': {}}
    if box:
        try:
            uses = zones.consumption(ir, box);spread = zones.swings(ir, box)
            result['uses'] = {'at_reading': num(uses['at_reading']), 'parts': {k: num(v) for k, v in uses['uses'].items()},
                              'together': num(uses['together']), 'left': num(uses['left']), 'no_room': uses['no_room']}
            result['swings'] = {'whole': num(spread['whole']), 'by': {k: num(v) for k, v in spread['by'].items()},
                                'shares': {k: _share(v) for k, v in spread['shares'].items()}}
        except ranges.RangeError:pass          # an input with no value at the reading: no room at the reading to share out
    for name in sorted(ir['model']['variables']):
        if roles.get(name) == 'limit' or 'value' not in ir['model']['variables'][name]:continue
        try:result['leverage'][name] = _share(zones.leverage(ir, name))
        except ranges.RangeError:pass
    steps = value['derivation'];steps.append(_method(found['slack'], box))
    steps.append('The room: the margin at the reading and at the worst corner; each input solved for with the others at their ranges, rounded inward to whole steps and worked out again.')
    if value['stage'] == 'settle':
        accuracy = {row['name']: row['amount'] for row in asked.get('accuracy') or ()};rows = [];first = []
        for name in sorted(box):
            try:z = zones.zones(ir, box, name)
            except ranges.RangeError as exc:
                rows.append({'name': name, 'state': exc.code, 'reason': str(exc)});continue
            u = z['unit'];lo, hi = z['range']
            row = {'name': name, 'unit': u, 'state': 'ANSWERED', 'range': [num(lo, u), num(hi, u)], 'holds': _piece(z['holds'], u),
                   'fails': _piece(z['fails'], u), 'share': _share(z['share']), 'reading': None}
            if z['share'] is not None:first.append((z['share'], name))
            if name in accuracy:
                try:
                    s = zones.settling_reading(ir, box, name, accuracy[name], asked.get('step'))
                    def readings(pair):return None if pair is None else {'lower': num(pair[0], u), 'upper': num(pair[1], u)}
                    row['reading'] = {'accuracy': num(s['accuracy'], u), 'holds': readings(s['holds']), 'fails': readings(s['fails']),
                                      'checked': s['checked'], 'rechecks': [{'reading': num(r['reading'], u), 'range': [num(r['range'][0], u), num(r['range'][1], u)],
                                                                             'expected': r['expected'], 'state': r['state']} for r in s['rechecks']]}
                except ranges.RangeError as exc:row['reading'] = {'state': exc.code, 'reason': str(exc)}
            rows.append(row)
        best = max(first) if first else None
        ties = [name for share, name in first if best and share == best[0]]
        result['zones'] = rows
        result['first'] = ties[0] if found['state'] == ranges.UNDECIDED and best and best[0] > 0 and len(ties) == 1 else None
        result['nothing_settles'] = found['state'] != ranges.UNDECIDED
        result['break_even'] = []
        for name in sorted(ir['model']['variables']):
            if roles.get(name) == 'limit' or 'value' not in ir['model']['variables'][name]:continue
            try:b = zones.break_even(ir, box, name)
            except ranges.RangeError:continue
            result['break_even'].append({'name': name, 'unit': b['unit'], 'state': b['state'], 'tolerance': num(b['tolerance'], b['unit']),
                                         'closed': b['closed'], 'then': b['then']})
        steps.append('The zones: solved for each input twice, for the relation and for its opposite, with the others at their ranges.')
    value.update(result=result, state=found['state'], for_all=found['for_all'], witness=_witness(found['witness'], ir, value['inputs']),
                 guarantee='EXACT_VALUE' if not box else 'EXACT_RANGE' if found['slack'].status == ranges.ATTAINED else 'SOUND_ENCLOSURE')


# -- words ----------------------------------------------------------------------------------------------------------------

def _margin(record, relation):
    """The slack as the owner reads it, rounded outward: ('to spare' or 'over by' or ..., lo, hi, unit)."""
    lo, hi, unit = rational(record[0]['rational']), rational(record[1]['rational']), record[0]['unit']
    if relation in ('ge', 'gt'):lo, hi = -hi, -lo
    return lo, hi, unit


def _inputs_at(record, skip=()):
    """The inputs, as the answer was worked out at them: 'voltage 11.8 to 12.2 V and limit 6 W'."""
    parts = []
    for row in record['inputs']:
        if row['name'] in skip:continue
        if row['range']:parts.append('%s %s' % (row['name'], span_words(rational(row['range'][0]['rational']), rational(row['range'][1]['rational']), row['unit'])))
        elif row['value']:parts.append('%s %s' % (row['name'], figure(rational(row['value']['rational']), row['unit'])))
    return ', '.join(parts[:-1]) + (' and ' if len(parts) > 1 else '') + (parts[-1] if parts else '')


LOOSE = 'the margin was worked out as a sound range, which may be wider than the true one'


def _verdict(record):
    """The check in words. Over a sound range (not ATTAINED) only its near end is a true bound, so the words say 'at least'
    and say why; 'the ranges reach both sides' is said only of an exact range."""
    result = record['result'];relation = result['relation'];lo, hi, unit = _margin(result['slack'], relation)
    ranged = any(row['range'] for row in record['inputs']);loose = result['status'] != ranges.ATTAINED
    def by(near, far):return 'at least ' + figure(near, unit, 'down') if loose else span_words(near, far, unit)
    why = ' (%s)' % LOOSE if loose else ''
    if record['state'] == 'HOLDS':
        if relation == 'eq':return 'The two sides are equal.'
        if relation == 'ne':return 'The two sides never meet.'
        return 'It holds%s, with %s to spare%s.' % (' for every value in the ranges' if ranged else '', by(lo, hi), why)
    if record['state'] == 'FAILS':
        if relation == 'ne':return 'The two sides are equal.'
        if relation == 'eq':return 'The two sides differ by %s%s.' % (by(min(abs(lo), abs(hi)), max(abs(lo), abs(hi))), why)
        return 'It does not hold%s: %s by %s%s.' % (' for any value in the ranges' if ranged else '', 'short' if relation in ('ge', 'gt') else 'over',
                                                   by(-hi, -lo), why)
    if loose:said = 'Whether it holds cannot be told from this range: %s, and that range reaches both sides.' % LOOSE
    else:said = 'The ranges reach both sides of it, so whether the real value holds cannot be told from them.'
    witness = record['witness'];ranged = {row['name'] for row in record['inputs'] if row['range']}
    if witness:
        said += ' At %s it would not hold: %s.' % (', '.join('%s %s' % (k, figure(rational(v['rational']), v['unit'])) for k, v in witness['assignment'].items() if k in ranged),
                                                 figure(rational(witness['value']['rational']), witness['value']['unit']))
    return said


def _solve_words(record):
    found = record['result']['allowed'];name, unit = found['name'], found['unit']
    def at(e, toward=None):return figure(rational(e['value']['rational']), unit, toward)
    lattice = found['lattice'] or {}
    if found['state'] == 'EMPTY':
        needs = found['needs']
        wanted = ' and '.join('%s %s %s' % (name, ('>=' if needs[s]['closed'] else '>') if s == 'lower' else ('<=' if needs[s]['closed'] else '<'), at(needs[s]))
                              for s in ('lower', 'upper') if needs.get(s))
        return 'No value of %s holds%s. %s.' % (name, ': it needs ' + wanted if wanted else '', found['reason'])
    if found['state'] == 'WHOLE_DOMAIN':
        said = 'Every value of %s holds' % name
    else:
        upper = found['upper'] if found['upper'] and found['upper']['by'] == 'relation' else None
        lower = found['lower'] if found['lower'] and found['lower']['by'] == 'relation' else None
        def shown(side, e):
            inward = 'down' if side == 'upper' else 'up'
            if lattice.get(side):return figure(rational(lattice[side]['rational']), unit, inward)
            return at(e, inward)
        if upper and lower and found['relation'] == 'eq':said = 'Exactly ' + exactly(rational(upper['value']['rational']), unit)
        elif upper and lower:said = 'From %s to %s' % (shown('lower', lower), shown('upper', upper))
        elif upper:said = ('Up to ' if upper['closed'] or lattice.get('upper') else 'Below ') + shown('upper', upper)
        elif lower:said = ('At least ' if lower['closed'] or lattice.get('lower') else 'Above ') + shown('lower', lower)
        else:said = 'Every value of %s in the range asked holds' % name
    others = _inputs_at(record, (name,))
    return said + (', at ' + others if others else '') + '.'


def _solve_lines(record):
    found = record['result']['allowed'];name, unit = found['name'], found['unit'];lines = []
    if found['state'] == 'EMPTY':return lines
    lo, hi = found['lower'], found['upper'];lattice = found['lattice'] or {}
    def num(e, toward=None):return figure(rational(e['rational']), unit, toward)
    if lattice:
        low, high = [None if e is None else rational((lattice.get(s) or e['value'])['rational']) for s, e in (('lower', lo), ('upper', hi))]
        if low is not None and high is not None:steps = figure(low, unit) if low == high else '%s to %s' % (figure(low, '', 'up').strip(), figure(high, unit, 'down'))
        elif low is not None:steps = 'from ' + figure(low, unit, 'up')
        elif high is not None:steps = 'up to ' + figure(high, unit, 'down')
        else:steps = 'any value'
        lines.append('In whole steps of %s: %s.' % (num(found['step']), steps))
    exact = [figure(rational(e['value']['rational']), unit, 'up' if s == 'lower' else 'down') for s, e in (('lower', lo), ('upper', hi)) if e and e['by'] == 'relation']
    if lattice and exact:lines.append('The exact end is %s.' % exact[0] if len(exact) == 1 else 'The exact ends are %s and %s.' % tuple(exact))
    if found['declared'] is not None:
        lines.append('The declared %s lies %s.' % (num(found['declared']), 'inside' if found['declared_inside'] else 'outside'))
    for row, past in zip(found['ends'], found['beyond'] or [None] * len(found['ends'])):
        # an end rounded inward (a shown allowed number never claims more than is allowed), the step past it outward; the
        # one end of an equation in its exact value, since no rounding of it holds
        inward, outward = ('down', 'up') if row['side'] == 'upper' else ('up', 'down')
        end = exactly(rational(row['at']['rational']), unit) if found['relation'] == 'eq' else num(row['at'], inward)
        said = '%s %s (%s)' % (end, 'holds' if row['holds'] else 'does not hold', figure(rational(row['left']['rational']), row['left']['unit'])) if row['left'] else ''
        if past and past['left']:said += '; %s %s (%s)' % (num(past['at'], outward), 'holds' if past['holds'] else 'does not', figure(rational(past['left']['rational']), past['left']['unit']))
        if not said:continue
        said = said[0].upper() + said[1:] + ('' if not row['corner'] else ', at ' + ', '.join('%s %s' % (k, figure(rational(v['rational']), v['unit'])) for k, v in row['corner'].items())) + '.'
        if said not in lines:lines.append(said)       # an equation's one end is both of its ends: said once
    return lines


def _origin_words(row):
    source = row.get('source') or {}
    if row['origin'] == 'FREED':return 'solved for' + (' (declared %s)' % figure(rational(row['value']['rational']), row['unit']) if row['value'] else '')
    if row['origin'] == 'GIVEN_IN_LINE':return 'given in the line'
    if row['origin'] == 'OWNER_TOLERANCE':
        t = row['tolerance'] or {};return 'your tolerance (revision %s), %s' % (t.get('revision'), TOLERANCE_STATES.get(t.get('state'), ''))
    if row['origin'] == 'PROBLEM_REVISION':return 'problem sheet, revision %s' % source.get('revision')
    if row['origin'] == 'SHEET_CELL':return 'sheet cell %s, revision %s' % (source.get('cell'), str(source.get('revision'))[:12])
    return 'declared in the model'


def receipt(record):
    """The receipt in words: the inputs with their revisions and where each came from, the method, the guarantee, the sources."""
    lines = []
    for row in record.get('inputs') or ():
        if row['range']:shown = span_words(rational(row['range'][0]['rational']), rational(row['range'][1]['rational']), row['unit'])
        elif row['value']:shown = figure(rational(row['value']['rational']), row['unit'])
        else:shown = 'no value'
        said = '%s: %s · %s' % (row['name'], shown, _origin_words(row))
        t = row.get('tolerance')
        if t and row['origin'] != 'OWNER_TOLERANCE':said += ' · your tolerance (revision %s) %s' % (t.get('revision'), TOLERANCE_STATES.get(t.get('state'), ''))
        lines.append(said)
    lines += ['How: ' + step for step in record.get('derivation') or ()]
    if record.get('guarantee'):lines.append('Guarantee: ' + GUARANTEES.get(record['guarantee'], record['guarantee']) + '.')
    elif record.get('stage') == 'solve' and record.get('state') == 'ANSWERED':
        lines.append('Guarantee: none claimed, since no end of it was worked out again (an open end, or no end at all).')
    if record.get('obligations'):lines.append('Assumed: every denominator is not zero.' if all(o.get('condition') == 'DENOMINATOR_NONZERO' for o in record['obligations'])
                                             else 'Open: a denominator may be zero over the ranges.')
    lines += ['Assumption: ' + a for a in record.get('assumptions') or ()]
    lines.append(FRESHNESS.get(record.get('freshness'), ''))
    lines.append('Worked out by Kas in exact fractions; no model was asked. Nothing was measured here.')
    return [line for line in lines if line]


def _shown(name):
    said = str(name).replace('_', ' ');return said[:1].upper() + said[1:]


def _goal_lines(record):
    """The room and settle lines, in her templates (math_zones.WORDS)."""
    from .math_zones import WORDS
    result = record['result'];lines = [];state = record['state']
    def q(n, toward=None):return '' if n is None else figure(rational(n['rational']), n['unit'], toward)
    if result.get('share_of_limit') and state == 'HOLDS':
        lines.append(WORDS['share_of_limit'].format(share=figure(rational(result['share_of_limit']['rational']) * 100, '%')))
    for m in result['moves'] if state in ('HOLDS', 'FAILS') else ():      # cannot tell: the zones say it instead
        for side, toward in (('rise', 'down'), ('fall', 'up')):
            w = m.get(side)
            if not w:continue
            word = side if state == 'HOLDS' else 'to_hold_down' if side == 'rise' else 'to_hold_up'
            lines.append(WORDS[word].format(name=_shown(m['name']) if state == 'HOLDS' else _shown(m['name']).lower(), end=q(w['on_step'] or w['to'], toward),
                                            exact=exactly(rational(w['to']['rational']), m['unit'])))
        if m['state'] == ranges.WHOLE_DOMAIN and state == 'HOLDS':lines.append(WORDS['no_move'].format(name=_shown(m['name'])))
    uses = result.get('uses')
    if uses and uses['no_room']:lines.append(WORDS['no_room'])
    elif uses:
        parts = '; '.join(WORDS['use'].format(name=_shown(k) if not i else _shown(k).lower(), part=q(v)) for i, (k, v) in enumerate(uses['parts'].items()))
        left = rational(uses['left']['rational'])
        if left < 0:word = 'uses_over'
        elif len(uses['parts']) == 1 and not rational(uses['together']['rational']):word = 'uses_alone'
        else:word = 'uses'
        lines.append(WORDS[word].format(room=q(uses['at_reading']), parts=parts, together=q(uses['together']), left=q(uses['left']),
                                        over=figure(-left, uses['left']['unit'], 'up')))
    if record['stage'] != 'settle':return lines
    if result.get('first'):lines.append(WORDS['first'].format(name=_shown(result['first']).lower()))
    for row in result.get('zones') or ():
        if row.get('state') != 'ANSWERED':continue
        name = _shown(row['name']);holds, fails = row['holds'] or {}, row['fails'] or {}
        if result.get('nothing_settles'):
            lines.append(WORDS['nothing_settles'].format(name=name.lower(), state=HEADINGS[state].lower()));continue
        if holds.get('upper') and fails.get('lower'):
            h, f = holds['upper'], fails['lower']
            lines.append(WORDS['zone'].format(name=name.lower(), holds=('at or below ' if h['closed'] else 'below ') + q(h['value'], 'down'),
                                              fails=('at or above ' if f['closed'] else 'above ') + q(f['value'], 'up')))
        elif holds.get('lower') and fails.get('upper'):
            h, f = holds['lower'], fails['upper']
            lines.append(WORDS['zone'].format(name=name.lower(), holds=('at or above ' if h['closed'] else 'above ') + q(h['value'], 'up'),
                                              fails=('at or below ' if f['closed'] else 'below ') + q(f['value'], 'down')))
        if row['share']:lines.append(WORDS['share'].format(name=name.lower(), share=row['share']['rational']))
        reading = row.get('reading') or {}
        accuracy = '+-' + q(reading['accuracy']) if reading.get('accuracy') else ''
        for key, word in (('holds', 'settles_holds'), ('fails', 'settles_fails')):
            pair = reading.get(key)
            if not pair:continue
            if pair.get('upper') and not pair.get('lower'):side, value = 'below', pair['upper']
            elif pair.get('lower') and not pair.get('upper'):side, value = 'above', pair['lower']
            else:continue
            lines.append(WORDS[word].format(accuracy=accuracy, side=side, reading=q(value, 'down' if side == 'below' else 'up')))
    for b in result.get('break_even') or ():
        if b['tolerance'] is None or b['state'] not in ('HOLDS', 'FAILS') or not rational(b['tolerance']['rational']):continue
        bound = 'at most' if b['closed'] else 'under'
        lines.append(WORDS['break_even_holds' if b['state'] == 'HOLDS' else 'break_even_fails'].format(name=_shown(b['name']).lower(), bound=bound, tolerance=q(b['tolerance'])))
    return lines


def words(record):
    """{'heading', 'answer', 'lines', 'receipt'}: what the window shows for an answer, in the owner's words."""
    stage, state = record['stage'], record['state']
    asked = record.get('asked') or {};expression = asked.get('expression', '')
    if state in HEADINGS:heading = HEADINGS[state]
    elif stage == 'check':heading = 'Cannot tell'
    elif stage == 'solve':heading = STAGE_HEADINGS['solve'] % asked.get('for', '')
    else:heading = STAGE_HEADINGS.get(stage, 'Answer')
    lines = []
    if state in ERRORS:
        said = 'Cannot work it out: %s.' % plain(state, record.get('reason'), asked.get('unit'))
        if state == 'DENOMINATOR_MAY_BE_ZERO':said = 'Cannot tell: a denominator may be zero over these ranges, so no range is given.'
    elif state in HEADINGS:
        verdict = _verdict(record);said = '%s: %s' % (expression, verdict[0].lower() + verdict[1:])
        if stage in GOAL_STAGES and record.get('result'):lines += _goal_lines(record)
    elif stage == 'solve':said = _solve_words(record);lines += _solve_lines(record)
    elif stage == 'calculate':
        v = record['result']['value'];said = '%s = %s.' % (expression, figure(rational(v['rational']), v['unit']))
    else:
        lo, hi = record['result']['range'];status = record['result']['status']
        said = '%s: %s%s.' % (expression, span_words(rational(lo['rational']), rational(hi['rational']), lo['unit']),
                              '' if status == ranges.ATTAINED else ', a sound range that may be wider than the true one')
        others = _inputs_at(record)
        if others:said = said[:-1] + ', over ' + others + '.'
    if record.get('freshness') == 'REVIEW_REQUIRED':lines.append(FRESHNESS['REVIEW_REQUIRED'])
    return {'heading': heading, 'answer': said, 'lines': lines, 'receipt': receipt(record)}


def plain(state, reason, unit=None):
    """Why an answer could not be worked out, in the owner's words: the reason when it is already in them, otherwise the
    state's own sentence. A code, a node or a solver's term never reaches the screen."""
    reason = str(reason or '').strip().rstrip('.')
    for pattern, said in REWORDS:
        if pattern.fullmatch(reason):return pattern.sub(said, reason)
    if state == 'INCOMPATIBLE_OUTPUT_UNIT' and unit and (not reason or INTERNAL.search(reason)):return 'the answer cannot be shown in ' + unit
    if not reason or state == 'DIMENSION_MISMATCH' or INTERNAL.search(reason):return REFUSALS.get(state, REFUSALS['UNSUPPORTED'])
    return reason


def is_answer(value):
    """The math answer inside a line's result, or None."""
    if isinstance(value, dict) and value.get('schema') == SCHEMA:return value
    inner = value.get('result') if isinstance(value, dict) else None
    return inner if isinstance(inner, dict) and inner.get('schema') == SCHEMA else None


def screen_text(value):
    """A line's answer as plain text for the window: the heading, the answer, its lines. None when it is not one."""
    found = is_answer(value)
    if found:
        said = found['words'];return '\n'.join([said['heading'], said['answer'], *said['lines']])
    inner = value.get('result') if isinstance(value, dict) else None
    if isinstance(inner, dict) and isinstance(inner.get('evaluation'), dict):      # calculate: math.preview, unchanged
        rows = [r for r in inner['evaluation'].get('outputs') or () if r.get('kind') == 'quantity' and r.get('value')]
        if rows:
            v = rows[0]['value'];lines = ['Worked out', figure(rational(v['rational']), v['unit']) + '.']
            if value.get('freshness') == 'REVIEW_REQUIRED':lines.append(FRESHNESS['REVIEW_REQUIRED'])
            return '\n'.join(lines)
    return None


def receipt_text(value):
    found = is_answer(value)
    return None if not found else 'Receipt\n' + '\n'.join(found['words']['receipt'])


# -- a line on a problem sheet --------------------------------------------------------------------------------------------

def bindings_from_problem(problem, args, said=None):
    """(ir, inputs) for a line on a problem sheet: the model from math_service.model_for, each input's origin and source,
    its range from the line's `given` (GIVEN_IN_LINE) or else from the owner's tolerance when it APPLIES or is CARRIED_OVER
    (OWNER_TOLERANCE; one that needs a RECHECK is shown and not applied), and the solved one FREED. Ranges come only from
    the owner: a line Kasandra proposes never carries `given` (stacy_control.validate_actions refuses it)."""
    from . import math_service
    ir, bindings = math_service.model_for(problem, {'expression': args['expression']})
    given = {}
    for row in args.get('given') or ():
        if row['name'] in given:ranges.fail('UNSUPPORTED', 'Give each quantity one range')
        given[row['name']] = (row['lo'], row['hi'])
    if args.get('for') in given:ranges.fail('UNSUPPORTED', '%s is what is solved for, so it cannot also have a range' % args['for'])
    unused = sorted(set(given) - set(ir['model']['variables']))
    if unused:ranges.fail('UNSUPPORTED', 'The expression does not use ' + ', '.join(unused))
    inputs = {}
    for binding in bindings:
        name = binding['name'];tolerance = (said or {}).get(name)
        row = {'origin': binding['origin'], 'range': None, 'tolerance': None,
               'source': {'problem': problem['id'], 'revision': problem['revision'], 'context_digest': problem['context_digest'], 'variable': name}}
        if tolerance:row['tolerance'] = {'id': tolerance['id'], 'revision': tolerance['revision'], 'state': tolerance['state']}
        if name == args.get('for'):row['origin'] = 'FREED'
        elif name in given:row.update(origin='GIVEN_IN_LINE', range=given[name])
        elif tolerance and tolerance['state'] in ('APPLIES', 'CARRIED_OVER') and args['stage'] != 'calculate':
            row.update(origin='OWNER_TOLERANCE', range=(tolerance['lo'], tolerance['hi']))
        inputs[name] = row
    return ir, inputs


def cell_unit(unit):
    """(the calculator's unit, the factor to it) for a sheet's Unit cell, by datasheet_work.report's rule."""
    from . import quantities
    unit = str(unit or '').strip()
    if not unit:ranges.fail('MISSING_INPUT', 'A cell needs a reviewed unit: fill the Unit column, or enter 1 for a plain number')
    try:
        unit_spec(unit);return unit, Fraction(1)
    except ValueError:
        spec = quantities.resolve(unit)
        if not spec or not spec.get('kernel_unit'):ranges.fail('UNSUPPORTED', '%s is not a unit the exact calculator supports' % unit)
        return spec['kernel_unit'], rational(str(spec['factor']))


def bindings_from_cells(expression, cells, said=None, stage='check', roles=None, assumptions=()):
    """(ir, inputs) for a relation over sheet cells: the goal face's bindings. cells: {symbol: {'address', 'cell',
    'revision', 'value', 'unit'}} as the sheet holds them now (value and unit as reviewed text). Each input's origin is
    SHEET_CELL and its source {address, cell, revision}; its range comes only from the owner's tolerance on that cell
    (said: {(address, cell): {id, revision, state, lo, hi}}, lo and hi in the cell's unit) when it APPLIES or is
    CARRIED_OVER (OWNER_TOLERANCE; one that needs a RECHECK is shown and not applied); roles: {symbol: 'measured' or
    'limit'}. A cell that is not an exact number, or a unit the calculator does not support, raises with its code."""
    from .math_model import compile_expression
    variables = {};inputs = {}
    for symbol, cell in cells.items():
        unit, factor = cell_unit(cell.get('unit'))
        try:value = rational(str(cell.get('value')).strip()) * factor
        except ValueError:ranges.fail('UNSUPPORTED', '%s needs a reviewed exact number' % cell.get('cell'))
        variables[symbol] = {'value': str(value), 'unit': unit}
        row = {'origin': 'SHEET_CELL', 'range': None, 'tolerance': None, 'role': (roles or {}).get(symbol),
               'source': {'address': cell['address'], 'cell': cell['cell'], 'revision': cell.get('revision')}}
        tolerance = (said or {}).get((cell['address'], cell['cell']))
        if tolerance:
            row['tolerance'] = {'id': tolerance['id'], 'revision': tolerance['revision'], 'state': tolerance['state']}
            if tolerance['state'] in ('APPLIES', 'CARRIED_OVER') and stage != 'calculate':
                row.update(origin='OWNER_TOLERANCE', range=(rational(str(tolerance['lo'])) * factor, rational(str(tolerance['hi'])) * factor))
        inputs[symbol] = row
    try:ir = compile_expression(expression, variables, list(assumptions))
    except MathError as exc:ranges.fail(exc.code, str(exc))
    return ir, inputs


def ask(stage, expression, variables, inputs=None, asked=None, freshness='CURRENT', assumptions=()):
    """answer() from an expression and declared variables ({name: {unit, value?, lower?, upper?, domain?}}): the model is
    compiled here, and a model that cannot be compiled (DIMENSION_MISMATCH, MISSING_INPUT, UNSUPPORTED) is the record's state."""
    from .math_model import compile_expression
    asked = {'expression': expression, **dict(asked or {})}
    try:ir = compile_expression(expression, variables, list(assumptions))
    except (ValueError, ZeroDivisionError) as exc:return refused(stage, asked, _code(exc), str(exc), freshness)
    return answer(stage, ir, inputs, asked, freshness)


def line(problem, freshness, args, said=None):
    """The answer to one maths line on a problem sheet as it stands; `said`: the owner's tolerances for it."""
    asked = {k: args[k] for k in ('expression', 'for', 'within', 'step', 'unit', 'accuracy') if k in args}
    try:ir, inputs = bindings_from_problem(problem, args, said)
    except (ValueError, ZeroDivisionError) as exc:return refused(args['stage'], asked, _code(exc), str(exc), freshness)
    return answer(args['stage'], ir, inputs, asked, freshness)


def dispatch(kernel, op, args, p):
    from . import problem_service as problems, tolerances
    sheet = problems.get(kernel, args['id'], p)
    return line(sheet['problem'], sheet['freshness']['state'], args, tolerances.standing(kernel, sheet['problem'], p))
