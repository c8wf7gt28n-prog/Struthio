"""Exact unit algebra shared by staC quantities, calculators and solver adapters."""
from decimal import Decimal, localcontext
from fractions import Fraction
import re

BASES = ('time', 'voltage', 'current', 'memory')
DIMENSIONS = {'dimensionless': (0,0,0,0), 'time': (1,0,0,0), 'frequency': (-1,0,0,0),
              'voltage': (0,1,0,0), 'current': (0,0,1,0), 'power': (0,1,1,0), 'memory': (0,0,0,1)}


def dimension_name(dimension):
    return next((k for k,v in DIMENSIONS.items() if v == tuple(dimension)), canonical_unit(dimension))


def canonical_unit(dimension):
    names = ('s', 'V', 'A', 'B')
    common = {v:k for k,v in [('1',(0,0,0,0)),('s',(1,0,0,0)),('Hz',(-1,0,0,0)),
                             ('V',(0,1,0,0)),('A',(0,0,1,0)),('W',(0,1,1,0)),('B',(0,0,0,1))]}
    if tuple(dimension) in common:return common[tuple(dimension)]
    return '*'.join(name + ('^'+str(power) if power != 1 else '') for name,power in zip(names, dimension) if power) or '1'


def unit_spec(unit):
    from .stac.quantities import UNITS
    if not isinstance(unit,str) or not 1 <= len(unit) <= 64:raise ValueError('UNIT_TEXT_BOUND')
    tokens = re.split(r'([*/])', unit)
    dimension = [0,0,0,0]; factor = Fraction(1); sign = 1
    for index, token in enumerate(tokens):
        if index % 2:
            sign = -1 if token == '/' else 1; continue
        match = re.fullmatch(r'([A-Za-z]+|1)(?:\^(-?[1-8]))?', token)
        if not match or match[1] not in UNITS:raise ValueError('UNKNOWN_OR_AMBIGUOUS_UNIT: '+unit)
        exponent = int(match[2] or 1) * sign
        name, scale = UNITS[match[1]]
        dimension = [a + exponent*b for a,b in zip(dimension,DIMENSIONS[name])]
        factor *= Fraction(scale) ** exponent
    if any(abs(v)>16 for v in dimension):raise ValueError('UNIT_DIMENSION_BOUND')
    return tuple(dimension), factor


def rational(text):
    if not isinstance(text,str) or len(text)>100 or not re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d{1,3})?|[+-]?\d+/\d+',text):
        raise ValueError('EXACT_NUMBER_STRING_REQUIRED')
    if 'e' in text.lower() and abs(int(text.lower().split('e')[1]))>100:raise ValueError('NUMBER_EXPONENT_BOUND')
    try:value = Fraction(text)
    except (ValueError,ZeroDivisionError) as exc:raise ValueError('INVALID_EXACT_NUMBER') from exc
    return bounded(value)


def bounded(value):
    if max(abs(value.numerator).bit_length(), value.denominator.bit_length()) > 2048:raise ValueError('EXACT_ARITHMETIC_SIZE_BOUND')
    return value


def number_record(value):
    value = bounded(value); denominator = value.denominator
    for prime in (2,5):
        while denominator % prime == 0:denominator //= prime
    exact_decimal = denominator == 1
    with localcontext() as context:
        context.prec = max(28, len(str(abs(value.numerator)))+len(str(value.denominator))+4) if exact_decimal else 28
        decimal = format(Decimal(value.numerator)/Decimal(value.denominator),'f')
    if '.' in decimal:decimal = decimal.rstrip('0').rstrip('.')
    return {'rational': str(value), 'decimal': decimal, 'decimal_exact': exact_decimal}


def quantity_record(base_value, dimension, unit=None):
    unit = unit or canonical_unit(dimension)
    target, factor = unit_spec(unit)
    if tuple(dimension) != target:raise ValueError('INCOMPATIBLE_OUTPUT_UNIT')
    return {**number_record(base_value/factor), 'unit': unit,
            'dimension': {name:power for name,power in zip(BASES,dimension) if power}}
