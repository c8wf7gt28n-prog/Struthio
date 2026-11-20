"""Money in lines (0.8.5, "Maths in lines"): amounts in a currency, exactly, on the one maths core (math_typed is the frame).

    math money | calculate "12 * rent + 4 * 80 USD" | given rent 950 USD
    math money | solve "4 * weekly <= 1200 USD" for weekly [| within 0 1200] [| step 0.01]
    math money | range "(2200 USD - rent) / 4" | given rent 950 1000 USD [| round 0.01]
    math money | check "24 * 212.50 EUR <= 36 * 148.90 EUR + 150 EUR"

An amount is a number with the ISO 4217 code the owner writes after it (1200 USD, 212.50 EUR), in the expression or in a
`given` (given NAME AMOUNT [AMOUNT] [CODE]: one value or a range; without a code it is a plain number). It is the exact
decimal written, an exact fraction inside, never floating point. Two currencies are never added or compared, unless the
owner gives the rate in the line (| rate EUR USD 1.08: one EUR is 1.08 USD); then every EUR amount is converted at it
before anything is worked out, and the receipt names the rate. An amount times or over a plain number is an amount; an
amount over an amount of the same currency is a plain number; an amount times an amount is refused. An amount written
another way (1,200 USD, $10, 10 usd, 1e3 USD) is refused with the way to write it.

Rounding happens only when the line asks for it (| round 0.01 in calculate and range: the number is the step, a positive
decimal, so 0.01 is whole cents and 1 whole units; any other step is refused), by one rule only: half away from
zero. An amount exactly halfway between two steps goes to the one further from zero, which is how bills, bank statements
and the euro conversion rules round, so a rounded amount here matches the one on the owner's papers; half to even would
be unbiased over many sums, but it would differ from them by a cent at every even half. The exact value always stands
beside the rounded one. In solve, | step 0.01 rounds an allowed end inward to whole cents, as the core does every step:
an allowance is never rounded up. An amount that does not end within its cents is shown to the cent (outward for a range,
inward for an allowed end) with its exact value beside it. This works out what the owner asks from his numbers; it gives
no advice.
"""
from __future__ import annotations
import ast
import math
import re
from fractions import Fraction
from . import math_typed as typed
from .math_answers import NUMBER, figure
from .math_units import number_record, rational

RULE = 'HALF_AWAY_FROM_ZERO'
RULE_WORDS = 'half away from zero'
CODES = frozenset('''AED AFN ALL AMD ANG AOA ARS AUD AWG AZN BAM BBD BDT BGN BHD BIF BMD BND BOB BRL BSD BTN BWP BYN BZD CAD
CDF CHF CLP CNY COP CRC CUP CVE CZK DJF DKK DOP DZD EGP ERN ETB EUR FJD FKP GBP GEL GHS GIP GMD GNF GTQ GYD HKD HNL HTG HUF IDR
ILS INR IQD IRR ISK JMD JOD JPY KES KGS KHR KMF KPW KRW KWD KYD KZT LAK LBP LKR LRD LSL LYD MAD MDL MGA MKD MMK MNT MOP MRU MUR
MVR MWK MXN MYR MZN NAD NGN NIO NOK NPR NZD OMR PAB PEN PGK PHP PKR PLN PYG QAR RON RSD RUB RWF SAR SBD SCR SDG SEK SGD SHP SLE
SOS SRD SSP STN SVC SYP SZL THB TJS TMT TND TOP TRY TTD TWD TZS UAH UGX USD UYU UZS VES VND VUV WST XAF XCD XCG XOF XPF YER ZAR
ZMW ZWG'''.split())                                     # ISO 4217, the currencies in use
PLACES = {**{code: 0 for code in 'BIF CLP DJF GNF ISK JPY KMF KRW PYG RWF UGX VND VUV XAF XOF XPF'.split()},
          **{code: 3 for code in 'BHD IQD JOD KWD LYD OMR TND'.split()}}           # minor units other than two (ISO 4217)
CODE = re.compile('[A-Z]{3}')
AMOUNT = re.compile(r'(?<![\w.])(\d+(?:\.\d+)?)\s*([A-Z]{3})\b')
DECIMAL = re.compile(r'[+-]?\d+(?:\.\d+)?')
ORDER = {'calculate': ('given', 'rate', 'round'), 'solve': ('within', 'step', 'given', 'rate'), 'range': ('given', 'rate', 'round'), 'check': ('given', 'rate')}
GIVENS, RATES = 8, 4
NAME = {'type': 'string', 'minLength': 1, 'maxLength': 64}
CODE_FIELD = {'type': 'string', 'minLength': 3, 'maxLength': 3}
GIVEN = {'type': 'object', 'additionalProperties': False, 'properties': {'name': NAME, 'lo': NUMBER, 'hi': NUMBER, 'currency': CODE_FIELD}, 'required': ['name', 'lo']}
RATE = {'type': 'object', 'additionalProperties': False, 'properties': {'from': CODE_FIELD, 'to': CODE_FIELD, 'rate': NUMBER}, 'required': ['from', 'to', 'rate']}
FIELDS = {'math.money': ({'stage': {'type': 'string', 'enum': ['calculate', 'solve', 'range', 'check']},
                          'expression': {'type': 'string', 'minLength': 1, 'maxLength': 1000}, 'for': NAME,
                          'within': {'type': 'array', 'minItems': 2, 'maxItems': 2, 'items': NUMBER}, 'step': NUMBER,
                          'given': {'type': 'array', 'maxItems': GIVENS, 'items': GIVEN}, 'rates': {'type': 'array', 'maxItems': RATES, 'items': RATE},
                          'round': {**NUMBER, 'description': 'the step to round to, as a decimal: 0.01 is whole cents, 1 is whole units'}}, ['stage', 'expression'])}
SCOPES = {'math.money': 'read'}


# -- the line ------------------------------------------------------------------------------------------------------------

def line_args(verb, steps):
    """The arguments of math.money from a line's verb and steps (stac_bridge.math_ir); a STAC_MATH_ code otherwise."""
    args = typed.stage_args(verb, steps, ORDER)
    for word, *rest in steps:
        if word == 'within' and len(rest) == 2:args['within'] = [typed.number(rest[0]), typed.number(rest[1])]
        elif word == 'step' and len(rest) == 1:args['step'] = typed.number(rest[0], True)
        elif word == 'given' and 2 <= len(rest) <= 4:
            name, *values = rest;code = values.pop() if len(values) > 1 and CODE.fullmatch(values[-1]) else None
            if not typed.NAME.fullmatch(name):raise ValueError('STAC_MATH_NAME')
            if len(values) not in (1, 2):raise ValueError('STAC_MATH_SYNTAX')
            row = {'name': name, 'lo': typed.number(values[0]), **({'hi': typed.number(values[1])} if len(values) == 2 else {}), **({'currency': code} if code else {})}
            args.setdefault('given', []).append(row)
            if len(args['given']) > GIVENS:raise ValueError('STAC_MATH_GIVEN_BOUND')
        elif word == 'rate' and len(rest) == 3 and CODE.fullmatch(rest[0]) and CODE.fullmatch(rest[1]):
            args.setdefault('rates', []).append({'from': rest[0], 'to': rest[1], 'rate': typed.number(rest[2], True)})
            if len(args['rates']) > RATES:raise ValueError('STAC_MATH_RATE_BOUND')
        elif word == 'round' and len(rest) == 1:args['round'] = typed.number(rest[0], True)
        else:raise ValueError('STAC_MATH_SYNTAX')
    return args


def owners(args):
    """What only the owner gives in a money line: a range or an exchange rate (never in a line Kasandra proposes)."""
    return any('hi' in row for row in args.get('given') or ()) or bool(args.get('rates'))


# -- amounts -------------------------------------------------------------------------------------------------------------

def half_away(value, step):
    """`value` to a whole number of `step`, an exact half going away from zero: the one rounding rule (RULE)."""
    q = Fraction(value) / Fraction(step);n = math.floor(abs(q) + Fraction(1, 2))
    return (n if q >= 0 else -n) * Fraction(step)


def _places(text, code):
    """An exact decimal written to at least the currency's minor unit (two places for most)."""
    places = PLACES.get(code, 2);whole, _, part = text.partition('.')
    return whole + ('.' + part.ljust(places, '0') if places or part else '')


def show(value, unit, toward=None, bare=False):
    """An amount in words: its exact decimal with its currency; one that does not end within its minor unit to that unit
    (rounded `toward` 'down' or 'up', otherwise to the nearest) with its exact value beside it. A plain number as the core says it."""
    value = Fraction(value)
    if unit in ('1', '', None):return figure(value, '1', toward)
    exact = number_record(value);tail = '' if bare else ' ' + unit
    if exact['decimal_exact']:return _places(exact['decimal'], unit) + tail
    step = Fraction(1, 10 ** PLACES.get(unit, 2));q = value / step
    near = (math.floor(q) if toward == 'down' else math.ceil(q) if toward == 'up' else half_away(q, 1)) * step
    return '%s%s (exact %s%s)' % (_places(number_record(near)['decimal'], unit), tail, exact['rational'], tail)


def label(kind):return kind or '1'


def mark(record, kind):
    record['unit'] = label(kind);return record


def combine(op, a, b):
    """The currency of a node from its operands' (None: a plain number), or a refusal in words."""
    if op in ('add', 'sub', 'compare'):
        if a == b:return a
        verb = 'compared' if op == 'compare' else 'added' if op == 'add' else 'subtracted'
        if a and b:typed.refuse('DIMENSION_MISMATCH', '%s and %s are different currencies, so they cannot be %s without an exchange rate; give yours in the line if you have one' % (a, b, verb))
        typed.refuse('DIMENSION_MISMATCH', 'a plain number cannot be %s with an amount in %s: write it as an amount, such as 5 %s' % (verb, a or b, a or b))
    if op == 'mul':
        if a and b:typed.refuse('DIMENSION_MISMATCH', 'an amount in %s times an amount in %s is not money: multiply an amount by a plain number' % (a, b))
        return a or b
    if op == 'div':
        if b is None:return a
        if a == b:return None
        if a is None:typed.refuse('DIMENSION_MISMATCH', 'a plain number divided by an amount in %s is not money' % b)
        typed.refuse('DIMENSION_MISMATCH', '%s and %s are different currencies, so one cannot be divided by the other without an exchange rate; give yours in the line if you have one' % (a, b))
    if op == 'power' and a:typed.refuse('DIMENSION_MISMATCH', 'an amount in %s cannot be raised to a power' % a)
    return a


def _rates(rows):
    rates = {}
    for row in rows or ():
        for code in (row['from'], row['to']):
            if code not in CODES:typed.refuse('UNSUPPORTED', '%s is not a currency code Graphite knows: write the three letters of ISO 4217, such as USD or EUR' % code)
        if row['from'] == row['to'] or row['from'] in rates:typed.refuse('UNSUPPORTED', 'Give one rate for each currency, from it to another')
        if not DECIMAL.fullmatch(row['rate']) or rational(row['rate']) <= 0:typed.refuse('UNSUPPORTED', 'Write a rate as a positive exact decimal, such as 1.08')
        rates[row['from']] = (row['to'], rational(row['rate']))
    if set(rates) & {to for to, _ in rates.values()}:
        typed.refuse('UNSUPPORTED', 'Give each rate straight into the currency you want: a rate into a currency that is itself converted is not followed')
    return rates


def _convert(value, code, rates, what, block):
    if code not in rates:return value, code
    to, rate = rates[code];block['converted'].append({'what': what, 'from': {**number_record(value), 'unit': code}, 'to': {**number_record(value * rate), 'unit': to}})
    return value * rate, to


def _amounts(expression, rates, block):
    """The expression the core reads, each amount's code taken off (converted at the owner's rate when he gave one), and
    the currency of each amount by its place (start, end) in the new expression's bytes."""
    out, literals, at = [], {}, 0
    for found in AMOUNT.finditer(expression):
        code = found.group(2)
        if code not in CODES:typed.refuse('UNSUPPORTED', '%s is not a currency code Graphite knows: write the three letters of ISO 4217, such as USD or EUR' % code)
        value, code = _convert(rational(found.group(1)), code, rates, found.group(0), block)
        out.append(expression[at:found.start()]);start = len(''.join(out).encode());text = number_record(value)['decimal']
        out.append(text);literals[(start, start + len(text.encode()))] = code;at = found.end()
    out.append(expression[at:])
    return ''.join(out), literals


def _names(expression):
    try:return {node.id for node in ast.walk(ast.parse(expression, mode='eval')) if isinstance(node, ast.Name)}
    except (SyntaxError, RecursionError, ValueError):return None


def _written(expression):
    """An amount written in a way the line does not read, said in words before anything is worked out."""
    if re.search(r'[$€£¥]', expression):typed.refuse('UNSUPPORTED', 'write the currency as its three letters after the amount, such as 10 USD')
    if re.search(r'\d,\d{3}', expression):typed.refuse('UNSUPPORTED', 'write an amount without a thousands comma, such as 1200 USD')
    if re.search(r'(?<![\w.])\d+(?:\.\d+)?[eE][+-]?\d', expression):typed.refuse('UNSUPPORTED', 'write an amount as a plain decimal, such as 1000 USD')
    for found in re.finditer(r'(?<![\w.])\d+(?:\.\d+)?\s*([A-Za-z]{3})\b', expression):
        if found.group(1) != found.group(1).upper() and found.group(1).upper() in CODES:
            typed.refuse('UNSUPPORTED', 'write the currency code in capitals, such as 10 %s' % found.group(1).upper())


def _checked(args):
    """What a money question must carry, in words: its stage and expression, what solve is for, a rounding step."""
    if args.get('stage') not in ORDER:typed.refuse('UNSUPPORTED', 'ask to calculate, solve, range or check')
    if not isinstance(args.get('expression'), str) or not args['expression'].strip():typed.refuse('UNSUPPORTED', 'write the expression to work out')
    if args['stage'] == 'solve' and not args.get('for'):typed.refuse('MISSING_INPUT', 'say which name to solve for')
    if 'round' in args and (not isinstance(args['round'], str) or not re.fullmatch(r'\d+(?:\.\d+)?', args['round']) or rational(args['round']) <= 0):
        typed.refuse('UNSUPPORTED', 'round to a step written as a positive decimal, such as 0.01 for whole cents')


def _spec(args, block):
    _checked(args)
    stage, expression, solved = args['stage'], args['expression'], args.get('for')
    _written(expression)
    rates = _rates(args.get('rates'));core, literals = _amounts(expression, rates, block)
    named, variables, inputs = {}, {}, {}
    for row in args.get('given') or ():
        name, code = row['name'], row.get('currency')
        if name in named:typed.refuse('UNSUPPORTED', 'Give %s one value or one range' % name)
        if code and code not in CODES:typed.refuse('UNSUPPORTED', '%s is not a currency code Graphite knows: write the three letters of ISO 4217, such as USD or EUR' % code)
        ends = [rational(row['lo'])] + ([rational(row['hi'])] if 'hi' in row else [])
        if code and not all(DECIMAL.fullmatch(row[k]) for k in ('lo', 'hi') if k in row):typed.refuse('UNSUPPORTED', 'Write an amount as an exact decimal, such as 950.50')
        converted = [_convert(end, code, rates, name, block) for end in ends] if code else [(end, None) for end in ends]
        named[name] = converted[0][1];values = [v for v, _ in converted]
        if len(values) == 1:variables[name] = {'unit': '1', 'value': str(values[0])};inputs[name] = {'origin': 'GIVEN_IN_LINE'}
        else:variables[name] = {'unit': '1'};inputs[name] = {'origin': 'GIVEN_IN_LINE', 'range': (values[0], values[1])}
    names = _names(core)
    if solved in named:typed.refuse('UNSUPPORTED', '%s is what is solved for, so it cannot also be given' % solved)
    if names is not None:
        unused = sorted(set(named) - names)
        if unused:typed.refuse('UNSUPPORTED', 'The expression does not use ' + ', '.join(unused))
        for name in sorted(names - set(named) - {solved}):
            if name in CODES:typed.refuse('UNSUPPORTED', 'write an amount with its number before the currency, such as 5 %s' % name)
            typed.refuse('MISSING_INPUT', '%s has no value: give it one in the line, or solve for it' % name)
        if solved and solved not in names:typed.refuse('MISSING_INPUT', 'The relation does not use ' + solved)
    kind = None
    if solved:
        seen = sorted({c for c in literals.values() if c} | {c for c in named.values() if c})
        kind = typed.infer(core, literals, named, combine, solved, [None, *seen], lambda code:'an amount in ' + code if code else 'a plain number')
        named[solved] = kind;variables[solved] = {'unit': '1'}
    out = typed.kinds(core, literals, named, combine)
    block.update(currencies=dict(named), amounts=sorted(set(literals.values())), result=out)
    if args.get('round'):block['rounding'] = {'step': {**number_record(rational(args['round'])), 'unit': label(out)}, 'rule': RULE}
    before = ['Converted at your rate: %s.' % '; '.join('%s is %s' % (row['what'] if row['what'] in named else show(rational(row['from']['rational']), row['from']['unit']),
                                                                   show(rational(row['to']['rational']), row['to']['unit'])) for row in block['converted'])] if block['converted'] else []
    asked = {k: args[k] for k in ('expression', 'for', 'within', 'step', 'given', 'rates', 'round') if k in args}
    return {'stage': stage, 'expression': expression, 'core': core, 'variables': variables, 'inputs': inputs, 'asked': asked,
            'core_asked': {k: args[k] for k in ('for', 'within', 'step') if k in args}, 'named': named, 'out': out, 'solved': kind,
            'block': ('money', block), 'before': before, 'after': _rounded if args.get('round') else None}


def _rounded(record):
    """The rounding the line asked for, beside the exact result: the one rule, named."""
    result = record['result'];step = rational(record['asked']['round'])
    def at(r):return {**number_record(half_away(rational(r['rational']), step)), 'unit': r['unit']}
    if 'value' in result and isinstance(result['value'], dict) and 'rational' in result['value'] and 'relation' not in result:
        result['rounded'] = {'step': {**number_record(step), 'unit': result['value']['unit']}, 'rule': RULE, 'value': at(result['value'])}
    elif 'range' in result:result['rounded'] = {'step': {**number_record(step), 'unit': result['range'][0]['unit']}, 'rule': RULE, 'range': [at(r) for r in result['range']]}
    else:typed.refuse('UNSUPPORTED', 'there is no amount to round: the line asks whether something holds')


# -- words ---------------------------------------------------------------------------------------------------------------

def _r(record):return rational(record['rational'])


def exactly(value, unit):
    """An amount as it is exactly: its decimal when it has one, otherwise its fraction, with its currency."""
    exact = number_record(Fraction(value))
    if unit in ('1', '', None):return exact['decimal'] if exact['decimal_exact'] else exact['rational']
    return '%s %s' % (_places(exact['decimal'], unit) if exact['decimal_exact'] else exact['rational'], unit)


def said(record):
    """A calculation rounded as asked: the rounded amount, the rule and the exact value, in one sentence."""
    rounded = (record.get('result') or {}).get('rounded')
    if not rounded or 'value' not in rounded:return None
    exact, near, step = record['result']['value'], rounded['value'], rounded['step']
    return ('%s = %s, rounded to %s %s (exact %s).' % (record['asked']['expression'], show(_r(near), near['unit']), show(_r(step), step['unit']), RULE_WORDS,
                                                       exactly(_r(exact), exact['unit']))), []


def notes(record):
    rounded = (record.get('result') or {}).get('rounded')
    if not rounded or 'range' not in rounded:return []
    step = rounded['step'];lo, hi = rounded['range']
    return ['Rounded to %s %s: %s.' % (show(_r(step), step['unit']), RULE_WORDS, typed.span(_r(lo), _r(hi), lo['unit'], show))]


def told(record):
    block = record.get('money') or {};lines = []
    for row in (record.get('asked') or {}).get('rates') or ():
        used = any(c['from']['unit'] == row['from'] for c in block.get('converted') or ())
        lines.append('Exchange rate: 1 %s = %s %s, as you gave it in this line%s.' % (row['from'], row['rate'], row['to'],
                                                                                     '; every %s amount was converted at it' % row['from'] if used else ', though no %s amount was in it' % row['from']))
    if block.get('rounding'):
        lines.append('Rounding: to %s, only because you asked, by one rule: %s (an amount exactly halfway between two steps goes to the one further from zero, '
                     'as bills, bank statements and the euro conversion rules round). The exact value stands beside it.' % (show(_r(block['rounding']['step']), block['rounding']['step']['unit']), RULE_WORDS))
    else:lines.append('Rounding: none was asked. An amount that does not end within its cents is shown to the cent with its exact value beside it.')
    return lines


KIT = {'show': show, 'label': label, 'mark': mark, 'difference': lambda kind:kind, 'told': told, 'notes': notes, 'said': said}


def answer(args):
    """ledger.math-answer/1 for one money line; its `money` field holds each name's currency, the result's, the rates
    and what they converted, and the rounding asked for. Never raises: a refusal is the record's state."""
    args = dict(args or {});block = {'currencies': {}, 'amounts': [], 'result': None, 'rates': [dict(row) for row in args.get('rates') or ()], 'converted': [], 'rounding': None}
    asked = {k: args[k] for k in ('expression', 'for', 'within', 'step', 'given', 'rates', 'round') if k in args}
    stage = args['stage'] if isinstance(args.get('stage'), str) and args['stage'] in ORDER else 'calculate'
    try:spec = _spec(args, block);return typed.answer(spec, KIT)
    except typed.Refused as exc:return typed.refused(stage, asked, ('money', block), KIT, exc)
    except (ValueError, ZeroDivisionError, OverflowError):return typed.refused(stage, asked, ('money', block), KIT, typed.Refused('UNSUPPORTED', typed.NUMBERS))
    except (KeyError, TypeError, AttributeError):return typed.refused(stage, asked, ('money', block), KIT, typed.Refused('UNSUPPORTED', typed.SHAPE))


def dispatch(kernel, op, args, p):return answer(args)
