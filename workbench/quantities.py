"""Quantities on a page (HATCH AGENT-01): numbers with units as owners write them, found where they stand and added exactly.

Pure functions, no eval, no model. ``extract`` reads one paragraph and returns every number it understands with the exact
character span it occupies, the number as a decimal string (never a float) and the unit as written, canonicalised and
named by dimension. ``sum_model`` turns such quantities into an ``arc.math-model/1`` model for ``math.evaluate`` (exact
rational arithmetic in the Kernel) and ``total_of`` reads the Kernel's answer back in the first quantity's unit.

Units. The Kernel's unit algebra (``math_units``, table ``stac.quantities.UNITS``) knows time, frequency, voltage, current,
power, memory and dimensionless numbers. Every spelling that maps onto it is canonicalised through ``unit_spec`` and
``canonical_unit`` and goes into the model with the Kernel's own unit, so the Kernel checks the dimension and does the
scaling (3 A + 500 mA = 3.5 A). Units the Kernel has no base for (mass, length, resistance, capacitance, inductance,
temperature, energy, volume, pressure, force, percent) are carried as local dimensions: the values enter the model scaled to
the dimension's base unit as dimensionless numbers, the model's assumptions say so, this module refuses to add two different
dimensions before any model is built, and the unit is restored on the result. ``accepted_spellings()`` lists every spelling
this module understands; the helper record (helpers.py) carries that list as its limits.

Honesty rules. A number followed directly by letters that are not a unit (``47k``, ``3rd``, ``v2``) is not a quantity.
A number followed by a space and an ordinary word (``3 apples``) is a plain number with unit None; plain numbers are summed
only when every chosen input is plain. Percent keeps its sign as the unit ``%`` so a share is never added to a count.
Times (14:30), dates (2026-11-05), fractions (3/4) and ranges (3-5) are left alone. Temperatures add as written; whether
that is meaningful is the owner's call, and the dimension name is on every record. Nothing here is a physical qualification.
"""
from __future__ import annotations
import re
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from . import math_units

MAX_MATCHES = 200          # the first 200 numbers of a paragraph; a page's total is bounded by the caller the same way
MAX_TEXT = 200000          # characters scanned per call
MAX_SUM = 64               # 2n-1 model nodes must stay within the IR's 128; the add tree is balanced, so depth stays small
SCHEMA = 'arc.math-model/1'

# -- the spellings ------------------------------------------------------------------------------------------------------
# Local dimensions the Kernel has no base for: dimension -> base unit (values are carried in it inside the model).
LOCAL_BASES = {'mass': 'g', 'length': 'm', 'resistance': 'ohm', 'capacitance': 'F', 'inductance': 'H', 'temperature': '°C',
               'temperature_f': '°F', 'ratio': '%', 'energy': 'J', 'volume': 'L', 'pressure': 'Pa', 'force': 'N'}
# Base spellings: symbol -> (canonical spelling, dimension, kernel unit or None, exact factor to the kernel unit or the local base).
# Kernel dimensions name the Kernel's own unit; the factor converts the written unit into it (an hour is 3600 s).
BASES = {
    's': ('s', 'time', 's', '1'), 'min': ('min', 'time', 's', '60'), 'h': ('h', 'time', 's', '3600'), 'day': ('day', 'time', 's', '86400'),
    'Hz': ('Hz', 'frequency', 'Hz', '1'), 'V': ('V', 'voltage', 'V', '1'), 'A': ('A', 'current', 'A', '1'), 'W': ('W', 'power', 'W', '1'),
    'B': ('B', 'memory', 'B', '1'),
    'g': ('g', 'mass', None, '1'), 't': ('t', 'mass', None, '1000000'),
    'm': ('m', 'length', None, '1'),
    'ohm': ('ohm', 'resistance', None, '1'),
    'F': ('F', 'capacitance', None, '1'),
    'H': ('H', 'inductance', None, '1'),
    '°C': ('°C', 'temperature', None, '1'), '°F': ('°F', 'temperature_f', None, '1'),
    '%': ('%', 'ratio', None, '1'),
    'J': ('J', 'energy', None, '1'), 'Wh': ('Wh', 'energy', None, '3600'),
    'L': ('L', 'volume', None, '1'), 'l': ('L', 'volume', None, '1'),
    'Pa': ('Pa', 'pressure', None, '1'), 'bar': ('bar', 'pressure', None, '100000'),
    'N': ('N', 'force', None, '1'),
}
# Words owners write instead of symbols (matched without regard to case).
WORDS = {
    'sec': 's', 'secs': 's', 'second': 's', 'seconds': 's', 'mins': 'min', 'minute': 'min', 'minutes': 'min',
    'hr': 'h', 'hrs': 'h', 'hour': 'h', 'hours': 'h', 'days': 'day',
    'hertz': 'Hz', 'volt': 'V', 'volts': 'V', 'amp': 'A', 'amps': 'A', 'ampere': 'A', 'amperes': 'A', 'watt': 'W', 'watts': 'W',
    'byte': 'B', 'bytes': 'B', 'kilobyte': 'kB', 'kilobytes': 'kB', 'megabyte': 'MB', 'megabytes': 'MB', 'gigabyte': 'GB', 'gigabytes': 'GB',
    'gram': 'g', 'grams': 'g', 'gramme': 'g', 'grammes': 'g', 'kilogram': 'kg', 'kilograms': 'kg', 'kilo': 'kg', 'kilos': 'kg',
    'milligram': 'mg', 'milligrams': 'mg', 'tonne': 't', 'tonnes': 't',
    'metre': 'm', 'metres': 'm', 'meter': 'm', 'meters': 'm', 'kilometre': 'km', 'kilometres': 'km', 'kilometer': 'km', 'kilometers': 'km',
    'millimetre': 'mm', 'millimetres': 'mm', 'millimeter': 'mm', 'millimeters': 'mm', 'centimetre': 'cm', 'centimetres': 'cm',
    'centimeter': 'cm', 'centimeters': 'cm',
    'ohms': 'ohm', 'farad': 'F', 'farads': 'F', 'henry': 'H', 'henries': 'H', 'percent': '%', 'pct': '%',
    'joule': 'J', 'joules': 'J', 'litre': 'L', 'litres': 'L', 'liter': 'L', 'liters': 'L', 'millilitre': 'mL', 'millilitres': 'mL',
    'milliliter': 'mL', 'milliliters': 'mL', 'pascal': 'Pa', 'pascals': 'Pa', 'newton': 'N', 'newtons': 'N',
    'degc': '°C', 'degf': '°F',
}
# SI prefixes accepted in front of a base: prefix -> (canonical prefix, exact factor). The micro sign and Greek mu both read as u.
PREFIXES = {'p': ('p', '1e-12'), 'n': ('n', '1e-9'), 'u': ('u', '1e-6'), 'm': ('m', '0.001'), 'c': ('c', '0.01'),
            'k': ('k', '1000'), 'M': ('M', '1000000'), 'G': ('G', '1000000000'), 'T': ('T', '1000000000000')}
PREFIXABLE = ('s', 'Hz', 'V', 'A', 'W', 'B', 'g', 'm', 'ohm', 'F', 'H', 'J', 'Wh', 'L', 'l', 'Pa', 'N')
CENTI_ONLY = ('m', 'L', 'l')                      # centi is accepted for metres and litres only (no centiamperes on a page)
BINARY = {'KiB': '1024', 'MiB': '1048576', 'GiB': '1073741824', 'TiB': '1099511627776'}
# Letter pairs that would resolve as a prefix and a base but are never units on a page.
NOT_UNITS = frozenset({'am', 'pm', 'AM', 'PM', 'ms_', 'Mm', 'Tm', 'Gm', 'Ts', 'Gs', 'Ms', 'ks', 'cg', 'pg', 'Tg', 'Gg', 'pA', 'pV', 'pW',
                       'cs', 'cA', 'cV', 'cW', 'cB', 'cF', 'cH', 'cJ', 'cN', 'nB', 'pB', 'uB', 'mB', 'cPa', 'nPa', 'pPa', 'uPa', 'mPa'})
_MICRO = str.maketrans({'µ': 'u', 'μ': 'u'})


def _kernel_units():
    from .stac.quantities import UNITS
    return UNITS


def _normal(token):
    """One spelling for the characters owners type differently."""
    return (token.replace('Ω', 'ohm').replace('Ω', 'ohm').replace('℃', '°C').replace('℉', '°F')
            .translate(_MICRO))


def _spec(canonical, dimension, kernel_unit, factor):
    base = math_units.canonical_unit(math_units.unit_spec(kernel_unit)[0]) if kernel_unit else LOCAL_BASES[dimension]
    return {'unit_canonical': canonical, 'dimension': dimension, 'kernel_unit': kernel_unit, 'factor': factor, 'base_unit': base}


def _base_spec(symbol):
    if symbol in BASES: return _spec(*BASES[symbol])
    return None


def resolve(token, token2=None):
    """The unit a written token names, or None. token2 is the word after a lone prefix letter ('47k ohm')."""
    if not isinstance(token, str) or not 1 <= len(token) <= 24: return None
    raw = token
    token = _normal(token)
    if token2 is not None:                                       # a lone prefix letter, then the unit word: 47k ohm, 4.7 u F; nothing else
        if token in PREFIXES and len(token) == 1:
            base = _normal(token2)
            if base not in BASES and base.casefold() in WORDS: base = WORDS[base.casefold()]
            if base in PREFIXABLE: return resolve(token + base)
        return None
    if token in NOT_UNITS: return None
    units = _kernel_units()
    if token in units:                                           # the Kernel's own spelling: its unit, its dimension
        dimension_tuple = math_units.unit_spec(token)[0]
        return _spec(token, math_units.dimension_name(dimension_tuple), token, '1')
    if token in BINARY: return _spec(token, 'memory', 'B', BINARY[token])
    if token in BASES: return _base_spec(token)
    word = WORDS.get(raw.casefold())
    if word is not None: return resolve(word)
    if len(token) >= 2 and token[0] in PREFIXES:
        prefix, base = token[0], token[1:]
        if base not in PREFIXABLE and WORDS.get(base.casefold()) in PREFIXABLE: base = WORDS[base.casefold()]   # kohms, kvolts
        if base in PREFIXABLE and (prefix != 'c' or base in CENTI_ONLY):
            spec = _base_spec(base)
            canonical_prefix, scale = PREFIXES[prefix]
            factor = Decimal(scale) * Decimal(spec['factor'])
            return _spec(canonical_prefix + spec['unit_canonical'], spec['dimension'], spec['kernel_unit'], _plain(factor))
    return None


COMMON_PREFIXED = ('kg', 'mg', 'mm', 'cm', 'km', 'um', 'nm', 'kohm', 'Mohm', 'mohm', 'mF', 'uF', 'nF', 'pF', 'mH', 'uH', 'nH', 'kJ', 'mJ', 'kWh', 'mL', 'cL',
                   'kPa', 'MPa', 'mbar', 'kN', 'kV', 'kW', 'MW', 'GHz', 'TB')


def accepted_spellings():
    """Every spelling extract() understands, for the helper record's limits: symbols (the bases, the Kernel's table and the common
    prefixed forms), words, and the prefix rule that composes the rest."""
    symbols = sorted(set(BASES) | set(_kernel_units()) | set(BINARY) | set(COMMON_PREFIXED), key=str.casefold)
    return {'symbols': symbols, 'words': sorted(WORDS), 'prefixes': ''.join(sorted(PREFIXES)) + ' (µ and μ read as u; c only before m and L)',
            'prefixable': list(PREFIXABLE), 'plain_numbers': 'a number with no unit, or followed by a word that is not a unit, has unit None',
            'not_quantities': 'a number joined to letters that are not a unit (47k, 3rd), times (14:30), dates (2026-11-05), fractions (3/4) and ranges (3-5)'}


# -- the numbers --------------------------------------------------------------------------------------------------------
_SPACES = '    '
_TOKEN = r'(?:%|[A-Za-zµμΩΩ°℃℉][A-Za-zµμΩΩ°]*)'
_NUMBER = re.compile(
    r'(?<![\w.,:/#\-−–°%])'                                   # not inside a word, a date, a time, a fraction or a range
    r'(?P<sign>[-−–])?'
    r'(?:(?P<int>\d{1,3}(?:,\d{3})+|\d+)(?P<frac>\.\d+|,\d{1,2}(?!\d))?|(?P<lone>\.\d+))'
    r'(?:[' + _SPACES + r']*(?P<unit>' + _TOKEN + r')(?:[' + _SPACES + r']+(?P<unit2>[A-Za-zΩΩ]+))?)?'
    r'(?![\w°µμΩΩ%:/\-−–])')


def _plain(decimal):
    """A Decimal as a plain decimal string, no exponent, no trailing zeros, '-0' never."""
    text = format(decimal.normalize(), 'f') if decimal != 0 else '0'
    if text.startswith('-0') and Decimal(text) == 0: text = '0'
    return text


def _value(match):
    """The number as written, as a decimal string: thousands commas dropped, a decimal comma made a point, .25 made 0.25, the
    minus made ASCII. Digits are kept exactly (12.50 stays 12.50)."""
    whole = (match.group('int') or '').replace(',', '')
    frac = match.group('frac') or match.group('lone') or ''
    if frac.startswith(','): frac = '.' + frac[1:]
    text = (whole or '0') + frac
    if match.group('sign'): text = '-' + text
    try: Decimal(text)
    except InvalidOperation: return None
    return text


def extract(text, limit=MAX_MATCHES):
    """Every number this module understands in one paragraph, in order, with its exact span. Bounded; never raises on words."""
    if not isinstance(text, str): raise ValueError('QUANTITIES_TEXT_IS_A_STRING')
    text = text[:MAX_TEXT]
    out = []
    for match in _NUMBER.finditer(text):
        if len(out) >= limit: break
        value = _value(match)
        if value is None: continue
        unit = match.group('unit'); unit2 = match.group('unit2')
        number_end = match.end('frac') if match.group('frac') else match.end('lone') if match.group('lone') else match.end('int')
        spec = None; end = number_end; written = None
        if unit:
            attached = match.start('unit') == number_end
            spec = resolve(unit, unit2) if unit2 else None
            if spec is not None: end = match.end('unit2'); written = unit + ' ' + unit2
            else:
                spec = resolve(unit)
                if spec is not None: end = match.end('unit'); written = unit
                elif attached: continue            # 47k, 3rd, v2: a number joined to letters that are not a unit is not a quantity
        row = {'start': match.start(), 'end': end, 'text': text[match.start():end], 'value': value, 'unit': written,
               'unit_canonical': None, 'dimension': None, 'kernel_unit': None, 'factor': '1', 'base_unit': None}
        if spec is not None: row.update(spec)
        out.append(row)
    return out


# -- the sum --------------------------------------------------------------------------------------------------------------

def choose(quantities):
    """Which quantities a page's total should use: the ones with units when any has one, else all the plain numbers.
    Returns (chosen, left_out, note)."""
    rows = list(quantities or [])
    with_units = [q for q in rows if q.get('dimension')]
    if with_units:
        left = [q for q in rows if not q.get('dimension')]
        note = '' if not left else '%d plain number%s without a unit left out' % (len(left), '' if len(left) == 1 else 's')
        return with_units, left, note
    return rows, [], ('plain numbers without a unit; the total is a count, not a measurement' if rows else '')


def describe_unit(q):
    return q['unit_canonical'] if q.get('unit_canonical') else 'no unit'


def sum_model(quantities):
    """The arc.math-model/1 model that adds these quantities. Raises ValueError naming the two quantities whose dimensions differ."""
    rows = list(quantities or [])
    if not rows: raise ValueError('NOTHING_TO_ADD: no quantities were given')
    if len(rows) > MAX_SUM: raise ValueError('TOO_MANY_TO_ADD: at most %d quantities in one sum; %d were given' % (MAX_SUM, len(rows)))
    first = rows[0]
    for q in rows[1:]:
        if q.get('dimension') != first.get('dimension'):
            raise ValueError('UNITS_DIFFER: %s (%s) and %s (%s) cannot be added' % (first['text'], describe_unit(first), q['text'], describe_unit(q)))
    nodes = []
    for n, q in enumerate(rows, 1):
        try: scaled = Decimal(q['value']) * Decimal(q.get('factor') or '1')
        except InvalidOperation as exc: raise ValueError('QUANTITY_VALUE: ' + str(q.get('value'))) from exc
        nodes.append({'id': 'q%d' % n, 'op': 'quantity', 'value': _plain(scaled), 'unit': q.get('kernel_unit') or '1'})
    level = [node['id'] for node in nodes]; count = 0
    while len(level) > 1:                               # a balanced tree keeps the depth within the IR's bound of 24
        nxt = []
        for i in range(0, len(level) - 1, 2):
            count += 1; ident = 'a%d' % count
            nodes.append({'id': ident, 'op': 'add', 'left': level[i], 'right': level[i + 1]}); nxt.append(ident)
        if len(level) % 2: nxt.append(level[-1])
        level = nxt
    assumptions = ['Sum of %d quantit%s written on the page, in the order written' % (len(rows), 'y' if len(rows) == 1 else 'ies')]
    if first.get('dimension') is None:
        assumptions.append('Plain numbers without a unit: the total is a number, not a measurement')
    elif first.get('kernel_unit') is None:
        assumptions.append('%s is outside the Kernel unit algebra: values carried in %s as dimensionless numbers; the result is read back in %s'
                           % (first['dimension'], first['base_unit'], first['unit_canonical']))
    return {'schema': SCHEMA, 'variables': {}, 'nodes': nodes, 'outputs': [level[0]], 'constraints': [], 'assumptions': assumptions}


def total_of(evaluation, quantities):
    """The Kernel's exact answer read back in the first quantity's unit: {value, unit, text, rational, exact, dimension}."""
    rows = list(quantities or [])
    if not rows: raise ValueError('NOTHING_TO_ADD')
    if not isinstance(evaluation, dict) or evaluation.get('state') != 'FEASIBLE' or not evaluation.get('outputs'):
        raise ValueError('SUM_NOT_EVALUATED: ' + str((evaluation or {}).get('state')) + ' ' + str((evaluation or {}).get('reason') or ''))
    row = evaluation['outputs'][0]
    if row.get('state') != 'EXACT' or not isinstance(row.get('value'), dict): raise ValueError('SUM_NOT_EXACT')
    first = rows[0]
    base = Fraction(row['value']['rational'])                       # in the first quantity's kernel unit, or the local base
    value = base / Fraction(first.get('factor') or '1')
    record = math_units.number_record(value)
    unit = first.get('unit_canonical')
    text = record['decimal'] + ((' ' + unit) if unit and unit != '%' else ('%' if unit == '%' else ''))
    return {'value': record['decimal'], 'unit': unit, 'text': text, 'rational': record['rational'], 'exact': record['decimal_exact'],
            'dimension': first.get('dimension'), 'count': len(rows)}
