"""Typed lines over the one maths core (0.8.5, "Maths in lines"): amounts of money and calendar dates, exactly.

A money line or a dates line carries the owner's own numbers, so it needs no problem sheet (docs/INTEGRATED_I02.md):

    math money | calculate "EXPR" [| given NAME A [B] [CODE]] ... [| rate FROM TO R] ... [| round STEP]
    math money | solve "REL" for NAME [| within LO HI] [| step S] [| given ...] ... [| rate ...] ...
    math money | range "EXPR" [| given ...] ... [| rate ...] ... [| round STEP]
    math money | check "REL" [| given ...] ... [| rate ...] ...
    math dates | calculate, solve, range or check as above, with dates [| given NAME D1 [D2]] ... [| holidays D ...]
    math dates | deadline N UNIT after DATE [| end included|excluded] [| holidays D ...]
    math dates | business days FROM TO [| holidays D ...]

What these add to the core is the kind of each value: an amount in a currency (math_money), a date or a number of days
(math_dates). The kinds are checked here first, and a mix the owner did not ask for (dollars plus euros, a date plus a
date) is refused in words. The expression then goes to the one maths core as plain exact fractions: math_answers.ask over
math_ranges answers it with its states, guarantee and steps, unchanged, and its record, ledger.math-answer/1, is set in
the kinds: every number carries its currency code, 'date' (a day number, 0001-01-01 being day 1, its ISO date beside it)
or 'days' as its unit. The words and the receipt are made here, since the core's words show four figures and no currency.
The frozen core files are not touched. No float anywhere, and nothing raises: a refusal is the record's state.
"""
from __future__ import annotations
import ast
import hashlib
import re
from pathlib import Path
from . import math_answers as answers, math_ranges as ranges, project_desk as records
from .math_units import rational

IMPLEMENTED = ('math_typed.py', 'math_money.py', 'math_dates.py')
OPS = {ast.Add: 'add', ast.Sub: 'sub', ast.Mult: 'mul', ast.Div: 'div'}
NAME = re.compile('[A-Za-z][A-Za-z0-9_]{0,63}')
RELATION = re.compile(r'(<=|>=|==|!=|<|>)')
PREFIXES = {'upper': 'Up to', 'lower': 'At least', 'below': 'Below', 'above': 'Above'}
NUMBERS = 'write each number as an exact decimal or fraction, such as 950.50 or 1/3, in at most 100 characters'
SHAPE = 'the question is missing a part, or a part is not written as the line writes it'
NOT_ADVICE ='It works out what you asked, from your numbers and the rules you state; it is not financial or legal advice.'
KEEP = ('The question:', 'Worked out', 'Interval arithmetic', 'The range from its exact form', 'Solved ', 'Its end')


def _hashes():
    return {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() for name in IMPLEMENTED}


OWN = _hashes()


def implementation():
    """sha256 of the core's files and of these three, as they were loaded."""
    return {**answers.implementation(), **OWN}


class Refused(ValueError):
    """A question refused before the core sees it: its state, and the owner's words for why."""
    def __init__(self, code, said):super().__init__(said);self.code = code


def refuse(code, said):raise Refused(code, said)


# -- the line ------------------------------------------------------------------------------------------------------------

def ordered(rest, order, repeatable):
    """The steps after a line's verb, each in its place in `order`; only the `repeatable` ones may come again."""
    last = -1
    for step in rest:
        if not step or step[0] not in order:raise ValueError('STAC_MATH_SYNTAX')
        place = order.index(step[0])
        if place < last or (place == last and step[0] not in repeatable):raise ValueError('STAC_MATH_STEP_ORDER')
        last = place
    return rest


def number(text, positive=False):
    """A number of a line, as the core reads one (math_units.rational); STAC_MATH_NUMBER otherwise."""
    try:value = rational(text)
    except ValueError:raise ValueError('STAC_MATH_NUMBER') from None
    if positive and value <= 0:raise ValueError('STAC_MATH_NUMBER')
    return text


def stage_args(verb, steps, order):
    """{'stage', 'expression', 'for'?} of a calculate, solve, range or check verb."""
    stage = verb[0] if verb else None
    if stage not in answers.STAGES or len(verb) != (4 if stage == 'solve' else 2) or (stage == 'solve' and (verb[2] != 'for' or not NAME.fullmatch(verb[3]))):
        raise ValueError('STAC_MATH_SYNTAX')
    ordered(steps, order[stage], ('given', 'rate'))
    return {'stage': stage, 'expression': verb[1], **({'for': verb[3]} if stage == 'solve' else {})}


# -- kinds ---------------------------------------------------------------------------------------------------------------

def kinds(expression, literals, names, combine):
    """The kind of an expression's value (of a relation: of its two sides), node by node: `literals` maps a constant's
    (start, end) in the expression's bytes to its kind, `names` a name to its kind (None: a plain number), and
    combine(op, left, right) gives a node's kind or refuses. What the core refuses anyway is left to the core."""
    try:tree = ast.parse(expression, mode='eval')
    except (SyntaxError, RecursionError, ValueError):return None
    def visit(node):
        if isinstance(node, ast.Name):return names.get(node.id)
        if isinstance(node, ast.Constant):return literals.get((node.col_offset, node.end_col_offset))
        if isinstance(node, ast.UnaryOp):return combine('neg', visit(node.operand), None)
        if isinstance(node, ast.BinOp):
            if isinstance(node.op, ast.Pow):return combine('power', visit(node.left), None)
            return combine(OPS.get(type(node.op), 'other'), visit(node.left), visit(node.right))
        if isinstance(node, ast.Compare) and len(node.ops) == 1:return combine('compare', visit(node.left), visit(node.comparators[0]))
        return None
    return visit(tree.body)


def infer(expression, literals, names, combine, solved, candidates, describe=None):
    """The kind of the quantity solved for: the first candidate under which the kinds of the line fit together. When none
    fits, the refusal gives each candidate's reason, `describe`(kind) naming the kind, so no one reason stands for all."""
    reasons = []
    for kind in candidates:
        try:kinds(expression, literals, {**names, solved: kind}, combine);return kind
        except Refused as exc:reasons.append((kind, exc))
    said, seen = [], set()
    for kind, exc in reasons:
        if describe and str(exc) not in seen:seen.add(str(exc));said.append('If %s is %s, %s.' % (solved, describe(kind), str(exc).rstrip('.')))
    if len(said) < 2:raise reasons[0][1]
    refuse(reasons[0][1].code, 'no kind of value for %s fits this line. %s' % (solved, ' '.join(said)))


def is_relation(expression):
    try:return isinstance(ast.parse(expression, mode='eval').body, ast.Compare)
    except (SyntaxError, RecursionError, ValueError):return False


# -- through the core ----------------------------------------------------------------------------------------------------

def _set(value, kind, mark):
    if isinstance(value, list):return [_set(v, kind, mark) for v in value]
    if isinstance(value, dict) and 'rational' in value:return mark(dict(value), kind)
    return value


def relabel(record, named, out, solved, kit):
    """The core's record set in the kinds: `named` {input: kind}, `out` the kind of the output (of a relation: of its
    sides), `solved` the kind of the quantity solved for; kit['label'](kind) its unit, kit['mark'](number record, kind) the
    record in it, kit['difference'](kind) the kind of a difference of two such values."""
    mark, difference = kit['mark'], kit['difference']
    for row in record['inputs']:
        kind = named.get(row['name']);row['unit'] = kit['label'](kind)
        row['value'] = _set(row['value'], kind, mark);row['range'] = _set(row['range'], kind, mark)
    result = record.get('result') or {}
    if 'value' in result:result['value'] = _set(result['value'], out, mark)
    if 'range' in result:result['range'] = _set(result['range'], out, mark)
    for side in ('left', 'right'):
        if side in result:result[side] = _set(result[side], out, mark)
    if 'slack' in result:result['slack'] = _set(result['slack'], difference(out), mark)
    if record.get('witness'):
        w = record['witness'];w['assignment'] = {k: _set(v, named.get(k), mark) for k, v in w['assignment'].items()}
        w['value'] = _set(w['value'], out, mark)
    found = result.get('allowed')
    if found:
        found['unit'] = kit['label'](solved)
        for key in ('lower', 'upper'):
            if found[key]:found[key]['value'] = _set(found[key]['value'], solved, mark)
        found['needs'] = {s: e and {**e, 'value': _set(e['value'], solved, mark)} for s, e in found['needs'].items()}
        found['step'] = _set(found['step'], difference(solved), mark);found['declared'] = _set(found['declared'], solved, mark)
        if found['lattice']:found['lattice'] = {s: _set(v, solved, mark) for s, v in found['lattice'].items()}
        for row in found['ends'] + found['beyond']:
            row['at'] = _set(row['at'], solved, mark);row['left'] = _set(row['left'], out, mark)
            row['corner'] = {k: _set(v, named.get(k), mark) for k, v in row['corner'].items()}
    return record


def answer(spec, kit):
    """A question through the one maths core, its record set in the kinds and sealed with these words. spec: 'stage',
    'expression' (the owner's), 'core' (the expression the core reads), 'variables', 'inputs', 'core_asked' ({'for',
    'within', 'step'} as the core reads them), 'asked' (as the owner wrote them), 'named', 'out', 'solved', 'block'
    ((name, dict) carried in the record), 'before' (steps taken before the core) and 'after' (record -> None, may refuse)."""
    record = answers.ask(spec['stage'], spec['core'], spec['variables'], spec['inputs'], {**spec['core_asked'], 'expression': spec['expression']})
    record['asked'] = dict(spec['asked'])
    refusal = None
    if record['state'] not in answers.ERRORS:
        relabel(record, spec['named'], spec['out'], spec.get('solved'), kit)
        try:
            if spec.get('after'):spec['after'](record)
        except Refused as exc:
            record.update(state=exc.code, reason=str(exc), result=None, for_all=None, witness=None, guarantee=None);refusal = str(exc)
    record['derivation'] = derivation(record, kit, spec.get('before', ()))
    return seal(record, spec['block'], kit, refusal)


def refused(stage, asked, block, kit, exc, before=()):
    """A question refused before the core saw it, as a record."""
    record = answers.refused(stage if stage in answers.STAGES else 'calculate', asked, exc.code, str(exc))
    record['derivation'] = ['The question: %s %s.' % (stage, asked.get('expression', '')), *before][:8]
    return seal(record, block, kit, str(exc))


def seal(record, block, kit, refusal=None):
    name, value = block
    record[name] = value;record['implementation'] = implementation()
    record['words'] = words(record, kit, refusal)
    record['digest'] = records.digest({k: v for k, v in record.items() if k != 'digest'})
    return record


# -- words ---------------------------------------------------------------------------------------------------------------

def _r(record):return rational(record['rational'])


def span(lo, hi, unit, show):
    """A range in words, its ends rounded outward when they are not short and exact."""
    return show(lo, unit) if lo == hi else '%s to %s' % (show(lo, unit, 'down', True), show(hi, unit, 'up'))


def inputs_at(record, show, skip=()):
    parts = []
    for row in record['inputs']:
        if row['name'] in skip:continue
        if row['range']:parts.append('%s %s' % (row['name'], span(_r(row['range'][0]), _r(row['range'][1]), row['unit'], show)))
        elif row['value']:parts.append('%s %s' % (row['name'], show(_r(row['value']), row['unit'])))
    return ', '.join(parts[:-1]) + (' and ' if len(parts) > 1 else '') + (parts[-1] if parts else '')


def derivation(record, kit, before=()):
    """At most eight steps, the core's own where they carry no number, the rest said again in the kinds."""
    show = kit['show'];core = [s for s in record.get('derivation') or () if s.startswith(KEEP)]
    steps = core[:1] + list(before)
    ranged = [row for row in record.get('inputs') or () if row['range']]
    if ranged:steps.append('Ranges: ' + '; '.join('%s %s' % (row['name'], span(_r(row['range'][0]), _r(row['range'][1]), row['unit'], show)) for row in ranged) + '.')
    steps += core[1:]
    result = record.get('result') or {};asked = record.get('asked') or {}
    if 'slack' in result:steps.append('Decided on the slack, right side minus left: %s.' % span(_r(result['slack'][0]), _r(result['slack'][1]), result['slack'][0]['unit'], show))
    found = result.get('allowed')
    if found and asked.get('within'):steps.append('Kept within %s to %s, as asked.' % tuple(_within(w, found['unit'], show) for w in asked['within']))
    if found and found['step'] is not None and asked.get('step'):steps.append('Rounded inward to whole steps of %s.' % show(_r(found['step']), found['step']['unit']))
    return steps[:8]


def _within(text, unit, show):
    try:return show(rational(text), unit)
    except ValueError:return text


def _margin(slack, relation):
    lo, hi = _r(slack[0]), _r(slack[1])
    return (-hi, -lo) if relation in ('ge', 'gt') else (lo, hi)


def verdict(record, show):
    """A check in words, as the core's: over a sound range only its near end is a true bound, so it says 'at least'."""
    result = record['result'];relation = result['relation'];lo, hi = _margin(result['slack'], relation);unit = result['slack'][0]['unit']
    ranged = any(row['range'] for row in record['inputs']);loose = result['status'] != ranges.ATTAINED
    def by(near, far):return 'at least ' + show(near, unit, 'down') if loose else span(near, far, unit, show)
    why = ' (%s)' % answers.LOOSE if loose else ''
    if record['state'] == 'HOLDS':
        if relation in ('eq', 'ne'):return 'the two sides are equal.' if relation == 'eq' else 'the two sides never meet.'
        return 'it holds%s, with %s to spare%s.' % (' for every value in the ranges' if ranged else '', by(lo, hi), why)
    if record['state'] == 'FAILS':
        if relation == 'ne':return 'the two sides are equal.'
        if relation == 'eq':return 'the two sides differ by %s%s.' % (by(min(abs(lo), abs(hi)), max(abs(lo), abs(hi))), why)
        return 'it does not hold%s: %s by %s%s.' % (' for any value in the ranges' if ranged else '', 'short' if relation in ('ge', 'gt') else 'over', by(-hi, -lo), why)
    said = ('whether it holds cannot be told from this range: %s, and that range reaches both sides.' % answers.LOOSE if loose
            else 'the ranges reach both sides of it, so whether the real value holds cannot be told from them.')
    witness = record['witness'];ranged = {row['name'] for row in record['inputs'] if row['range']}
    if witness:
        said += ' At %s it would not hold: %s.' % (', '.join('%s %s' % (k, show(_r(v), v['unit'])) for k, v in witness['assignment'].items() if k in ranged),
                                                 show(_r(witness['value']), witness['value']['unit']))
    return said


def sides(record, show):
    """What each side of a check comes to, named by the owner's own words for it."""
    parts = RELATION.split(record['asked'].get('expression', ''), maxsplit=1)
    if len(parts) != 3:return []
    result = record['result']
    def at(key):return span(_r(result[key][0]), _r(result[key][1]), result[key][0]['unit'], show)
    return ['The left side, %s, comes to %s; the right side, %s, to %s.' % (parts[0].strip(), at('left'), parts[2].strip(), at('right'))]


def solve_words(record, show, prefixes):
    found = record['result']['allowed'];name, unit = found['name'], found['unit'];lattice = found['lattice'] or {};prefixes = prefixes(unit)
    if found['state'] == 'EMPTY':
        needs = found['needs']
        wanted = ' and '.join('%s %s %s' % (name, ('>=' if needs[s]['closed'] else '>') if s == 'lower' else ('<=' if needs[s]['closed'] else '<'), show(_r(needs[s]['value']), unit))
                              for s in ('lower', 'upper') if needs.get(s))
        return 'No value of %s holds%s. %s.' % (name, ': it needs ' + wanted if wanted else '', found['reason'])
    upper = found['upper'] if found['upper'] and found['upper']['by'] == 'relation' else None
    lower = found['lower'] if found['lower'] and found['lower']['by'] == 'relation' else None
    def end(side, e):
        inward = 'down' if side == 'upper' else 'up'
        return show(_r(lattice[side]), unit, inward) if lattice.get(side) else show(_r(e['value']), unit, inward)
    if found['state'] == 'WHOLE_DOMAIN':said = 'Every value of %s holds' % name
    elif upper and lower and found['relation'] == 'eq':said = 'Exactly ' + show(_r(upper['value']), unit)
    elif upper and lower:said = 'From %s to %s' % (end('lower', lower), end('upper', upper))
    elif upper:said = prefixes['upper' if upper['closed'] or lattice.get('upper') else 'below'] + ' ' + end('upper', upper)
    elif lower:said = prefixes['lower' if lower['closed'] or lattice.get('lower') else 'above'] + ' ' + end('lower', lower)
    else:said = 'Every value of %s in the range asked holds' % name
    others = inputs_at(record, show, (name,))
    return said + (', at ' + others if others else '') + '.'


def solve_lines(record, show):
    found = record['result']['allowed'];unit = found['unit'];lines = []
    if found['state'] == 'EMPTY':return lines
    lattice = found['lattice'] or {}
    for side in ('lower', 'upper'):
        e = found[side]
        if e and e['by'] == 'relation' and lattice.get(side) and _r(lattice[side]) != _r(e['value']):
            lines.append('The exact end is %s.' % show(_r(e['value']), unit))
    for row, past in zip(found['ends'], found['beyond'] or [None] * len(found['ends'])):
        inward, outward = ('down', 'up') if row['side'] == 'upper' else ('up', 'down')
        if not row['left']:continue
        said = '%s %s (%s)' % (show(_r(row['at']), unit, inward), 'holds' if row['holds'] else 'does not hold', show(_r(row['left']), row['left']['unit']))
        if past and past['left']:said += '; %s %s (%s)' % (show(_r(past['at']), unit, outward), 'holds' if past['holds'] else 'does not', show(_r(past['left']), past['left']['unit']))
        corner = ', '.join('%s %s' % (k, show(_r(v), v['unit'])) for k, v in row['corner'].items())
        said = said[0].upper() + said[1:] + (', at ' + corner if corner else '') + '.'
        if said not in lines:lines.append(said)
    return lines


def receipt(record, kit):
    """The receipt: the inputs and where each came from, the rules this kind of line follows, the steps, the guarantee."""
    show = kit['show'];lines = []
    for row in record.get('inputs') or ():
        if row['range']:shown = span(_r(row['range'][0]), _r(row['range'][1]), row['unit'], show)
        elif row['value']:shown = show(_r(row['value']), row['unit'])
        else:shown = None
        lines.append('%s: solved for' % row['name'] if row['origin'] == 'FREED' else '%s: %s · given in this line' % (row['name'], shown or 'no value'))
    lines += kit['told'](record)
    lines += ['How: ' + step for step in record.get('derivation') or ()]
    if record.get('guarantee'):lines.append('Guarantee: ' + answers.GUARANTEES.get(record['guarantee'], record['guarantee']) + '.')
    elif record.get('stage') == 'solve' and record.get('state') == 'ANSWERED':
        lines.append('Guarantee: none claimed, since no end of it was worked out again (an open end, or no end at all).')
    if record.get('obligations'):lines.append('Assumed: every denominator is not zero.' if all(o.get('condition') == 'DENOMINATOR_NONZERO' for o in record['obligations'])
                                             else 'Open: a denominator may be zero over the ranges.')
    lines.append('Worked out by Graphite in exact fractions from the numbers in this line; no model was asked.')
    lines.append(NOT_ADVICE)
    return lines


def words(record, kit, refusal=None):
    """{'heading', 'answer', 'lines', 'receipt'} in the owner's words: amounts with their currency and exact value, dates
    with their weekday; never a code, an operation or a key."""
    show = kit['show'];stage, state = record['stage'], record['state'];asked = record.get('asked') or {};expression = asked.get('expression', '')
    heading = kit.get('heading') and kit['heading'](record)
    if not heading:
        heading = (answers.HEADINGS[state] if state in answers.HEADINGS else 'Cannot tell' if stage == 'check'
                   else answers.STAGE_HEADINGS['solve'] % asked.get('for', '') if stage == 'solve' else answers.STAGE_HEADINGS.get(stage, 'Answer'))
    lines = []
    if state in answers.ERRORS:
        said = 'Cannot work it out: %s.' % (refusal.rstrip('.') if refusal else answers.plain(state, record.get('reason')))
        if state == 'DENOMINATOR_MAY_BE_ZERO':said = 'Cannot tell: a denominator may be zero over these ranges, so no range is given.'
    elif kit.get('said') and kit['said'](record):said, lines = kit['said'](record)
    elif state in answers.HEADINGS:
        said = '%s: %s' % (expression, verdict(record, show));lines += sides(record, show)
    elif stage == 'solve':said = solve_words(record, show, kit.get('prefixes', lambda unit:PREFIXES));lines += solve_lines(record, show)
    elif stage == 'calculate':
        v = record['result']['value'];said = '%s = %s.' % (expression, show(_r(v), v['unit']))
    else:
        lo, hi = record['result']['range']
        said = '%s: %s%s.' % (expression, span(_r(lo), _r(hi), lo['unit'], show), '' if record['result']['status'] == ranges.ATTAINED else ', a sound range that may be wider than the true one')
        others = inputs_at(record, show)
        if others:said = said[:-1] + ', over ' + others + '.'
    if state not in answers.ERRORS:lines += kit['notes'](record)
    return {'heading': heading, 'answer': said, 'lines': lines, 'receipt': receipt(record, kit)}
