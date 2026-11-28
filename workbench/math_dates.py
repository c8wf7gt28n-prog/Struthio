"""Dates in lines (0.8.5, "Maths in lines"): calendar dates, exactly, on the one maths core (math_typed is the frame).

    math dates | calculate "2028-03-01 - 2028-02-28"                     the days between two dates: 2 days
    math dates | calculate "2026-01-31 + 1 month"                        Saturday 2026-02-28 (clamped to the month's end)
    math dates | calculate "2026-11-20 + 10 business days" [| holidays 2026-11-26 ...]
    math dates | check "2026-12-21 <= service + 30 days" | given service 2026-11-20
    math dates | solve "deadline - 2026-11-20 <= 30 days" for deadline [| within D1 D2]
    math dates | range "deadline - start" | given start 2026-11-01 2026-11-05 | given deadline 2026-12-20
    math dates | deadline 30 days after 2026-11-20 [| end included|excluded] [| holidays ...]
    math dates | business days 2026-11-20 2026-12-04 [| holidays ...]

A date is a calendar day written ISO (2026-11-20): no time of day and no time zone. Inside, it is its day number (the
proleptic Gregorian count, 0001-01-01 being day 1), so the days between two dates are a subtraction and a date plus some
days an addition, both exact, and the core's solve, range and check take dates as they take any number. A length is
written with its unit: 30 days, 2 weeks (14 days). A date plus a date, a date times a number, or a plain number added to
a date is refused in words.

Months and years are not a fixed number of days, so they are counted the calendar's way, before the core sees the
expression, on the date that starts a sum (written there, or a name given one date) and left to right through the lengths
after it: the same day of the month N months on, and when the month has no such day (31 January plus one month), the
month's last day. That is the one month-end rule, clamping, and the receipt says when it applied. A month or a business
day anywhere else (after a minus, a times or another length, or before a times) is refused, so the order of operations is
never bent. Business days are Monday to Friday, less the holidays the owner lists in the line (| holidays ...); there are
none by default, and the receipt then says no holidays were counted. A deadline from a rule ("30 days after 2026-11-20")
counts from the day after the date: the date is day 0 and the end is day 30, so the count is at least 1. Whether the end
day itself is inside the period is the owner's rule to say (| end included, | end excluded); when he does not say, both
are shown, so no convention is hidden. With the end excluded, the last day inside is the day before the end (for business
days, the business day before it), and a period left with no day inside is refused. A date that falls outside the years
1 to 9999 is refused. This works out what the owner asks; it gives no legal advice.

The last day of a period after an event (0.8.6, "Kas's mind, no model": the dates delta, stage 'period', no line yet):

    math.dates {stage: period, count: 21, after: 2026-10-03, roll: {clause, words, skips}, holidays: [...], yearly: [MM-DD],
                holiday_clause, count_clause, labels, on, as_of}         one event
               {..., events: [2026-09-30, 2026-10-03]}                   an event on one of these days
               {..., between: [2026-09-30, 2026-10-03]}                  an event on some day of this range

The event's day is day 0, as for a deadline; the counting clause the owner recorded is quoted beside it. A last day that
falls on a day the owner's quoted rule passes over (Saturday, Sunday, a public holiday: `roll`) moves to the next day that
is none of these; the holidays are the owner's (listed days, and days of the month every year from a clause). When the
rule passes over holidays and none are recorded, every last day says so ("unless it is a public holiday; holidays not
recorded"); when no rule is recorded and day N is a weekend, the day a rule would move it to is shown beside it, earliest
first. An uncertain event gives every reading's last day, and a range of days gives its two ends, exact, since counting
on and passing over a day never move a date earlier. The break-even is by days: a day on or before the earliest last day
is within the period on every reading, and on or before the latest, on at least one (`on` asks it of one day). `as_of`
counts the days from each last day to that day; when the caller takes it from this computer's clock (the Kernel does:
engineering_kernel.today) the answer carries origin CLOCK, and freshness() reads REVIEW_REQUIRED once the clock shows
another day. Nothing here reads a clock.
"""
from __future__ import annotations
import ast
import math
import re
from datetime import date, timedelta
from fractions import Fraction
from . import math_typed as typed
from .math_answers import NUMBER, figure
from .math_units import number_record, rational

WEEKDAYS = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')
MONTHS = ('January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December')
MONTH_END = 'CLAMP_TO_LAST_DAY'
ISO = re.compile(r'\d{4}-\d{2}-\d{2}')
UNITS = {'day': 'days', 'days': 'days', 'week': 'weeks', 'weeks': 'weeks', 'month': 'months', 'months': 'months', 'year': 'years',
         'years': 'years', 'business day': 'business days', 'business days': 'business days'}
UNIT = r'business\s+days?|days?|weeks?|months?|years?'
CHAIN = re.compile(r'(?P<date>\b\d{4}-\d{2}-\d{2}\b|\b[A-Za-z][A-Za-z0-9_]*\b)(?P<lengths>(?:\s*[+-]\s*\d+\s*(?:%s)\b)+)' % UNIT)
TERM = re.compile(r'\s*(?P<sign>[+-])\s*(?P<n>\d+)\s*(?P<unit>%s)\b' % UNIT)
LEFT_OVER = re.compile(r'\d+\s*(business\s+days?|months?|years?)\b')
TOKEN = re.compile(r'(?P<date>(?<![\w.])\d{4}-\d{2}-\d{2}(?![\w.]))|(?<![\w.])(?P<n>\d+)\s*(?P<unit>days?|weeks?)\b')
ORDER = {'calculate': ('given', 'holidays'), 'solve': ('within', 'given', 'holidays'), 'range': ('given', 'holidays'), 'check': ('given', 'holidays')}
GIVENS, HOLIDAYS, LONGEST = 8, 30, 3660000
LAST = date.max.toordinal()
NAME = {'type': 'string', 'minLength': 1, 'maxLength': 64}
DAY = {'type': 'string', 'minLength': 10, 'maxLength': 10}
GIVEN = {'type': 'object', 'additionalProperties': False, 'properties': {'name': NAME, 'lo': NUMBER, 'hi': NUMBER, 'unit': {'type': 'string', 'enum': ['days', 'weeks']}},
         'required': ['name', 'lo']}
# 0.8.6 S2, the dates delta: the last day of a period after an event (stage 'period')
SKIPS = ('saturday', 'sunday', 'holidays')          # what a rule may pass over, in the owner's quoted words
EVENTS, ROLL_STEPS = 8, 400
CLAUSE = {'type': 'object', 'additionalProperties': False, 'required': ['clause', 'words'],
          'properties': {'clause': {'type': 'string', 'minLength': 1, 'maxLength': 64}, 'words': {'type': 'string', 'minLength': 1, 'maxLength': 1000}}}
ROLL = {**CLAUSE, 'required': ['clause', 'words', 'skips'],
        'properties': {**CLAUSE['properties'], 'skips': {'type': 'array', 'minItems': 1, 'maxItems': 3, 'items': {'type': 'string', 'enum': list(SKIPS)}}}}
PERIOD = {'events': {'type': 'array', 'minItems': 2, 'maxItems': EVENTS, 'items': DAY}, 'between': {'type': 'array', 'minItems': 2, 'maxItems': 2, 'items': DAY},
          'labels': {'type': 'array', 'minItems': 1, 'maxItems': EVENTS, 'items': {'type': 'string', 'minLength': 1, 'maxLength': 120}},
          'roll': ROLL, 'count_clause': CLAUSE, 'holiday_clause': CLAUSE, 'yearly': {'type': 'array', 'maxItems': HOLIDAYS, 'items': {'type': 'string', 'minLength': 5, 'maxLength': 5}},
          'on': DAY, 'as_of': DAY}
FIELDS = {'math.dates': ({'stage': {'type': 'string', 'enum': ['calculate', 'solve', 'range', 'check', 'deadline', 'business', 'period']},
                          'expression': {'type': 'string', 'minLength': 1, 'maxLength': 1000}, 'for': NAME,
                          'within': {'type': 'array', 'minItems': 2, 'maxItems': 2, 'items': NUMBER},
                          'given': {'type': 'array', 'maxItems': GIVENS, 'items': GIVEN}, 'holidays': {'type': 'array', 'maxItems': HOLIDAYS, 'items': DAY},
                          'count': NUMBER, 'unit': {'type': 'string', 'enum': sorted(set(UNITS.values()))}, 'after': DAY, 'from': DAY, 'to': DAY,
                          'end': {'type': 'string', 'enum': ['included', 'excluded']}, **PERIOD}, ['stage'])}
SCOPES = {'math.dates': 'read'}


# -- the calendar --------------------------------------------------------------------------------------------------------

def day_of(text):
    """An ISO date as a date, or a refusal in words."""
    try:return date.fromisoformat(text) if ISO.fullmatch(text) else typed.refuse('UNSUPPORTED', 'write a date as year-month-day, such as 2026-11-20, not ' + text)
    except ValueError:typed.refuse('DOMAIN_ERROR', '%s is not a day on the calendar' % text)


def _beyond():typed.refuse('DOMAIN_ERROR', 'the date falls outside the calendar Kas reads, the years 1 to 9999')


def step_days(day, n):
    """The date `n` days after `day` (before, when n is negative)."""
    try:return date.fromordinal(day.toordinal() + n)
    except (ValueError, OverflowError):_beyond()


def add_months(day, n):
    """The date `n` months after `day` the calendar's way, and whether the month's last day was taken because the month
    has no such day (the one month-end rule: clamped)."""
    total = day.year * 12 + day.month - 1 + n;year, month = divmod(total, 12);month += 1
    if not 1 <= year <= 9999:_beyond()
    last = (date(year + month // 12, month % 12 + 1, 1) - timedelta(days=1)).day
    return date(year, month, min(day.day, last)), day.day > last


def step_business(day, n, holidays):
    """The date `n` business days after `day` (before, when negative): Monday to Friday, less the listed holidays. Whole
    weeks go at once (any seven days in a row hold five weekdays), so a long count takes a few steps, not one a day."""
    sign, left, held = (1 if n >= 0 else -1), abs(n), {h for h in holidays if h.weekday() < 5}
    if left > LONGEST:_beyond()
    while left > 5:
        weeks = (left - 1) // 5;later = step_days(day, sign * 7 * weeks)
        lo, hi = (day, later) if sign > 0 else (later, day)
        day, left = later, left - 5 * weeks + sum(1 for h in held if (lo < h <= hi if sign > 0 else lo <= h < hi))
    while left:
        day = step_days(day, sign)
        if day.weekday() < 5 and day not in held:left -= 1
    return day


def count_business(start, end, holidays):
    """The business days after `start` up to and including `end`: Monday to Friday, less the listed holidays."""
    weeks, rest = divmod((end - start).days, 7)
    count = weeks * 5 + sum(1 for i in range(1, rest + 1) if (start + timedelta(days=i)).weekday() < 5)
    return count - sum(1 for h in set(holidays) if start < h <= end and h.weekday() < 5)


def words_of(day):return '%s %s' % (WEEKDAYS[day.weekday()], day.isoformat())


# -- the last day of a period after an event (0.8.6 S2) ------------------------------------------------------------------

def yearly_of(texts):
    """Days of the month every year ('12-25'), as (month, day); 29 February is one, held in the years that have it."""
    out = set()
    for text in texts or ():
        found = re.fullmatch(r'(\d{2})-(\d{2})', text or '')
        month, day = (int(found.group(1)), int(found.group(2))) if found else (0, 0)
        if not 1 <= month <= 12 or not 1 <= day <= (29 if month == 2 else (date(2001, month % 12 + 1, 1) - timedelta(days=1)).day):
            typed.refuse('UNSUPPORTED', 'write a day held every year as month-day, such as 12-25 for 25 December, not ' + str(text))
        out.add((month, day))
    return out


def passed_over(day, skips, held=(), yearly=()):
    """Why a rule that passes over `skips` passes over `day` ('saturday', 'sunday' or 'holidays'), or None."""
    weekday = {5: 'saturday', 6: 'sunday'}.get(day.weekday())
    if weekday and weekday in skips:return weekday
    if 'holidays' in skips and (day in held or (day.month, day.day) in yearly):return 'holidays'
    return None


def roll(day, skips, held=(), yearly=()):
    """The day itself when the rule passes it by, else the next day the rule does not pass over; and the days passed over,
    each with why. Never earlier than `day`."""
    over = []
    for _ in range(ROLL_STEPS):
        why = passed_over(day, skips, held, yearly)
        if why is None:return day, over
        over.append((day, why));day = step_days(day, 1)
    typed.refuse('UNSUPPORTED', 'no day within %d days of the last day is one the rule does not pass over' % ROLL_STEPS)


def last_day(event, count, skips=(), held=(), yearly=()):
    """(day `count` after `event`, the event's day being day 0; the last day once the rule has moved it; the days passed
    over). Both steps never move a date earlier, so a later event never gives an earlier last day."""
    day = step_days(event, count)
    last, over = roll(day, skips, held, yearly)
    return day, last, over


def freshness(record, today):
    """CURRENT, or REVIEW_REQUIRED for an answer worked out as of a day read from this computer's clock once `today` (the
    caller reads the clock) is another day: its counts of days are of the day it was worked out. Reads no clock itself."""
    as_of = (record or {}).get('as_of') or {}
    if as_of.get('origin') == 'CLOCK' and as_of.get('day') != today.isoformat():return 'REVIEW_REQUIRED'
    return (record or {}).get('freshness') or 'CURRENT'


# -- the line ------------------------------------------------------------------------------------------------------------

def _date_text(text):
    if not ISO.fullmatch(text):raise ValueError('STAC_MATH_DATE')
    try:date.fromisoformat(text)
    except ValueError:raise ValueError('STAC_MATH_DATE') from None
    return text


def _whole(text):
    typed.number(text)
    if not re.fullmatch(r'\d{1,7}', text):raise ValueError('STAC_MATH_NUMBER')
    return text


def _steps(args, steps):
    for word, *rest in steps:
        if word == 'within' and len(rest) == 2:args['within'] = [_date_text(v) if ISO.fullmatch(v) else typed.number(v) for v in rest]
        elif word == 'given' and 2 <= len(rest) <= 4:
            name, *values = rest;unit = UNITS.get(values.pop()) if len(values) > 1 and values[-1] in ('day', 'days', 'week', 'weeks') else None
            if not typed.NAME.fullmatch(name):raise ValueError('STAC_MATH_NAME')
            if len(values) not in (1, 2):raise ValueError('STAC_MATH_SYNTAX')
            values = [_date_text(v) if ISO.fullmatch(v) else typed.number(v) for v in values]
            args.setdefault('given', []).append({'name': name, 'lo': values[0], **({'hi': values[1]} if len(values) == 2 else {}), **({'unit': unit} if unit else {})})
            if len(args['given']) > GIVENS:raise ValueError('STAC_MATH_GIVEN_BOUND')
        elif word == 'holidays' and 1 <= len(rest) <= HOLIDAYS:args['holidays'] = [_date_text(v) for v in rest]
        elif word == 'end' and len(rest) == 1 and rest[0] in ('included', 'excluded'):args['end'] = rest[0]
        else:raise ValueError('STAC_MATH_SYNTAX')
    return args


def line_args(verb, steps):
    """The arguments of math.dates from a line's verb and steps (stac_bridge.math_ir); a STAC_MATH_ code otherwise."""
    if verb and verb[0] == 'deadline':
        if 'after' not in verb or len(verb) < 5:raise ValueError('STAC_MATH_SYNTAX')
        after = verb.index('after');unit = UNITS.get(' '.join(verb[2:after]))
        if not unit or after != len(verb) - 2:raise ValueError('STAC_MATH_SYNTAX')
        typed.ordered(steps, ('end', 'holidays'), ())
        return _steps({'stage': 'deadline', 'count': _whole(verb[1]), 'unit': unit, 'after': _date_text(verb[-1])}, steps)
    if verb and verb[0] == 'business':
        if len(verb) != 4 or verb[1] != 'days':raise ValueError('STAC_MATH_SYNTAX')
        typed.ordered(steps, ('holidays',), ())
        return _steps({'stage': 'business', 'from': _date_text(verb[2]), 'to': _date_text(verb[3])}, steps)
    return _steps(typed.stage_args(verb, steps, ORDER), steps)


def owners(args):
    """What only the owner gives in a dates line: a range, or a list of holidays (never in a line Kasandra proposes); and in
    a period (0.8.6), the rule that moves a last day, the counting and holiday clauses, the days held every year, the day
    it is worked out as of, and an event that is one of several days or a range of them."""
    return (any('hi' in row for row in args.get('given') or ()) or bool(args.get('holidays'))
            or any(args.get(k) for k in ('roll', 'count_clause', 'holiday_clause', 'yearly', 'as_of', 'events', 'between')))


# -- kinds ---------------------------------------------------------------------------------------------------------------

KINDS = {'date': 'a date', 'days': 'a number of days', None: 'a plain number'}


def combine(op, a, b):
    """The kind of a node from its operands' ('date', 'days' or None, a plain number), or a refusal in words."""
    if op == 'add':
        if {a, b} == {'date', 'days'}:return 'date'
        if a == b == 'date':typed.refuse('DIMENSION_MISMATCH', 'two dates cannot be added: subtract one from the other for the days between them')
        if a == b:return a
    elif op == 'sub':
        if a == b:return 'days' if a == 'date' else a
        if (a, b) == ('date', 'days'):return 'date'
        if (a, b) == ('days', 'date'):typed.refuse('DIMENSION_MISMATCH', 'a date cannot be taken from a number of days')
    elif op == 'compare':
        if a == b:return a
        typed.refuse('DIMENSION_MISMATCH', '%s cannot be compared with %s: compare a date with a date, or days with days' % (KINDS[a], KINDS[b]))
    elif 'date' in (a, b) and op in ('mul', 'div', 'neg', 'power'):
        typed.refuse('DIMENSION_MISMATCH', 'a date cannot be %s: it is a day on the calendar, not an amount' % {'mul': 'multiplied', 'div': 'divided', 'neg': 'negated', 'power': 'raised to a power'}[op])
    elif op == 'mul':
        if a and b:typed.refuse('DIMENSION_MISMATCH', 'days times days are not days: multiply a number of days by a plain number')
        return a or b
    elif op == 'div':
        if b is None:return a
        if a == b:return None
        typed.refuse('DIMENSION_MISMATCH', 'a plain number divided by a number of days is not a length of time')
    elif op == 'power':
        if a:typed.refuse('DIMENSION_MISMATCH', 'a number of days cannot be raised to a power')
        return a
    else:return a
    plain = b if a is None else a
    typed.refuse('DIMENSION_MISMATCH', 'a plain number cannot be %s %s: say what it counts, such as 30 days or 2 weeks' % ('added to' if op == 'add' else 'subtracted from', KINDS[plain]))


def _starts_sum(head):
    """Whether what comes before a date begins a sum there: nothing, an opening bracket or a comparison."""
    return head[-1:] in ('', '(', '<', '>', '=')


def _calendar(text, singles, holidays, block, before):
    """Months, years and business days counted the calendar's way, before the core sees the expression, on the date that
    starts a sum (written there, or a name given one date) and left to right through the lengths after it; each length is
    a step of the receipt. A written date becomes the date reached; a name stays, plus the days reached, so the core
    still reads it."""
    for _ in range(16):
        for found in CHAIN.finditer(text):
            lengths = list(TERM.finditer(found.group('lengths')))
            if not any(t.group('unit').startswith(('business', 'month', 'year')) for t in lengths):continue
            head, tail = text[:found.start()].rstrip(), text[found.end():].lstrip()
            if not _starts_sum(head) or tail[:1] in ('*', '/'):continue
            what = found.group('date');named = not ISO.fullmatch(what)
            first = day = singles.get(what) if named else day_of(what)
            if day is None:continue
            for term in lengths:
                n = int(term.group('n')) * (1 if term.group('sign') == '+' else -1);unit = UNITS[' '.join(term.group('unit').split())]
                if unit == 'business days':end, clamped = step_business(day, n, holidays), False;block['business'] = True
                elif unit in ('days', 'weeks'):end, clamped = step_days(day, n * (7 if unit == 'weeks' else 1)), False
                else:end, clamped = add_months(day, n * (12 if unit == 'years' else 1))
                said = '%s %s %d %s is %s' % ('%s (%s)' % (what, words_of(day)) if named and day == first else words_of(day), term.group('sign'), abs(n),
                                              unit[:-1] if abs(n) == 1 else unit, words_of(end))
                if clamped:said += ': %s %d has only %d days, so the date is the month\'s last day' % (MONTHS[end.month - 1], end.year, end.day)
                before.append(said + '.')       # a date's words begin with its weekday; a name keeps the owner's spelling
                block['steps'].append({'from': day.isoformat(), 'count': n, 'unit': unit, 'to': end.isoformat(), 'clamped': clamped})
                day = end
            moved = (day - first).days
            text = text[:found.start()] + ('(%s %s %d days)' % (what, '-' if moved < 0 else '+', abs(moved)) if named else day.isoformat()) + text[found.end():]
            break
        else:break
    if LEFT_OVER.search(text):
        typed.refuse('UNSUPPORTED', 'months, years and business days are counted on the date that starts a sum, written there or given to a name as one date, '
                                    'and left to right through the lengths after it, such as 2026-01-31 + 1 month + 2 days')
    return text


def _written(text):
    """A length or a date written in a way the line does not read, said in words before anything is worked out."""
    if re.search(r'(?<![\w.])\d{1,4}[/.]\d{1,2}[/.]\d{1,4}(?![\w.])', text):typed.refuse('UNSUPPORTED', 'write a date as year-month-day, such as 2026-11-20')
    if re.search(r'\d\s*businessdays?\b', text, re.I):typed.refuse('UNSUPPORTED', 'write business days as two words, such as 10 business days')
    for found in re.finditer(r'\d\s*(business|days?|weeks?|months?|years?)\b', text, re.I):
        if found.group(1) != found.group(1).lower():typed.refuse('UNSUPPORTED', 'write a length in small letters, such as 30 days or 1 month')


def _dates(text):
    """The expression the core reads, each date its day number and each length its days, and the kind of each by its place."""
    out, literals, at = [], {}, 0
    for found in TOKEN.finditer(text):
        if found.group('date'):value, kind = day_of(found.group('date')).toordinal(), 'date'
        else:value, kind = int(found.group('n')) * (7 if found.group('unit').startswith('week') else 1), 'days'
        out.append(text[at:found.start()]);start = len(''.join(out).encode());piece = str(value)
        out.append(piece);literals[(start, start + len(piece.encode()))] = kind;at = found.end()
    out.append(text[at:])
    return ''.join(out), literals


def _names(expression):
    try:return {node.id for node in ast.walk(ast.parse(expression, mode='eval')) if isinstance(node, ast.Name)}
    except (SyntaxError, RecursionError, ValueError):return None


def _given(rows):
    named, variables, inputs, singles = {}, {}, {}, {}
    for row in rows or ():
        name = row['name'];ends = [row['lo']] + ([row['hi']] if 'hi' in row else [])
        if name in named:typed.refuse('UNSUPPORTED', 'Give %s one value or one range' % name)
        if all(ISO.fullmatch(e) for e in ends):kind, values = 'date', [day_of(e).toordinal() for e in ends]
        elif any(ISO.fullmatch(e) for e in ends):typed.refuse('UNSUPPORTED', 'Give %s two dates or two numbers, not one of each' % name)
        else:
            kind = 'days' if row.get('unit') else None;values = [rational(e) * (7 if row.get('unit') == 'weeks' else 1) for e in ends]
            if kind and any(v.denominator != 1 for v in values):typed.refuse('UNSUPPORTED', 'Give %s in whole days' % name)
        named[name] = kind;variables[name] = {'unit': '1', **({'domain': 'integer'} if kind else {})}
        if len(values) == 1:
            variables[name]['value'] = str(values[0]);inputs[name] = {'origin': 'GIVEN_IN_LINE'}
            if kind == 'date':singles[name] = date.fromordinal(values[0])
        else:inputs[name] = {'origin': 'GIVEN_IN_LINE', 'range': (values[0], values[1])}
    return named, variables, inputs, singles


def _checked(args):
    """What a dates question must carry, in words, before anything is worked out."""
    stage = args.get('stage')
    if stage not in ORDER and stage not in ('deadline', 'business', 'period'):
        typed.refuse('UNSUPPORTED', 'ask to calculate, solve, range or check, or for a deadline, a count of business days or the last day of a period')
    if len(args.get('holidays') or ()) > HOLIDAYS:typed.refuse('UNSUPPORTED', 'list at most %d holidays in a line' % HOLIDAYS)
    if stage == 'deadline':
        if not re.fullmatch(r'\d{1,7}', str(args.get('count', ''))) or int(args['count']) < 1:
            typed.refuse('UNSUPPORTED', 'count a period in whole days, weeks, months, years or business days, at least 1, such as 30 days after 2026-11-20')
        if args.get('unit') not in UNITS.values():typed.refuse('UNSUPPORTED', 'say what the count counts: days, weeks, months, years or business days')
        if not args.get('after'):typed.refuse('UNSUPPORTED', 'say the date the period runs after, such as 30 days after 2026-11-20')
        if args.get('end') not in (None, 'included', 'excluded'):typed.refuse('UNSUPPORTED', 'say end included or end excluded')
    elif stage == 'business':
        if not args.get('from') or not args.get('to'):typed.refuse('UNSUPPORTED', 'give the two dates to count business days between, such as 2026-11-20 2026-12-04')
    else:
        if not isinstance(args.get('expression'), str) or not args['expression'].strip():typed.refuse('UNSUPPORTED', 'write the expression to work out')
        if stage == 'solve' and not args.get('for'):typed.refuse('MISSING_INPUT', 'say which name to solve for')


def _excluded(start, end, unit, holidays):
    """The last day inside a period whose end day is excluded: the day before the end (for business days, the business
    day before it); None when that leaves no day after the start inside the period."""
    last = step_business(end, -1, holidays) if unit == 'business days' else step_days(end, -1)
    return last if last > start else None


def _spec(args, block):
    _checked(args)
    stage = args['stage'];holidays = sorted({day_of(h) for h in args.get('holidays') or ()})
    block['holidays'] = [h.isoformat() for h in holidays];before = []
    named, variables, inputs, singles = _given(args.get('given'))
    asked = {k: args[k] for k in ('expression', 'for', 'within', 'given', 'holidays', 'count', 'unit', 'after', 'from', 'to', 'end') if k in args}
    core_asked = {k: args[k] for k in ('for',) if k in args}
    if stage == 'deadline':
        start = day_of(args['after']);n = int(args['count']);unit = args['unit']
        if unit in ('days', 'weeks'):end = step_days(start, n * (7 if unit == 'weeks' else 1));clamped = False
        elif unit == 'business days':end, clamped = step_business(start, n, holidays), False;block['business'] = True
        else:end, clamped = add_months(start, n * (12 if unit == 'years' else 1))
        block['steps'].append({'from': start.isoformat(), 'count': n, 'unit': unit, 'to': end.isoformat(), 'clamped': clamped})
        asked = {**asked, 'rule': 'deadline', 'expression': '%d %s after %s' % (n, unit[:-1] if n == 1 else unit, args['after'])}
        last = _excluded(start, end, unit, holidays)
        if last is None and args.get('end') == 'excluded':
            typed.refuse('UNSUPPORTED', 'with the end day excluded, %s leaves no day inside the period: the start is day 0, and the first day after it is the end' % asked['expression'])
        core = '%d + %d' % (start.toordinal(), end.toordinal() - start.toordinal()) if unit in ('days', 'weeks') else str(end.toordinal())
        literals = _places(core, ('date', 'days'))
        out, after = 'date', _deadline(start, end, clamped, args.get('end'), last)
    elif stage == 'business':
        start, end = day_of(args['from']), day_of(args['to'])
        if end < start:typed.refuse('UNSUPPORTED', 'count business days from the earlier date to the later one')
        block['business'] = True;core, literals, out, after = str(count_business(start, end, holidays)), {}, None, None
        asked = {**asked, 'rule': 'business', 'expression': 'business days from %s to %s' % (args['from'], args['to'])}
    else:
        expression = args['expression'];solved = args.get('for')
        if solved in named:typed.refuse('UNSUPPORTED', '%s is what is solved for, so it cannot also be given' % solved)
        _written(expression)
        core, literals = _dates(_calendar(expression, singles, holidays, block, before))
        names = _names(core)
        if names is not None:
            unused = sorted(set(named) - names)
            if unused:typed.refuse('UNSUPPORTED', 'The expression does not use ' + ', '.join(unused))
            for name in sorted(names - set(named) - {solved}):typed.refuse('MISSING_INPUT', '%s has no value: give it one in the line, or solve for it' % name)
            if solved and solved not in names:typed.refuse('MISSING_INPUT', 'The relation does not use ' + solved)
        kind = None
        if solved:
            kind = typed.infer(core, literals, named, combine, solved, ['date', 'days', None], KINDS.get);named[solved] = kind
            variables[solved] = {'unit': '1', **({'domain': 'integer'} if kind else {})}
            if args.get('within'):core_asked['within'] = [str(day_of(w).toordinal()) if ISO.fullmatch(w) else w for w in args['within']]
        out, after = typed.kinds(core, literals, named, combine), _on_calendar
        block['solved'] = kind
    block.update(kinds=dict(named), result=out)
    return {'stage': 'calculate' if stage in ('deadline', 'business') else stage, 'expression': asked.get('expression', ''), 'core': core,
            'variables': variables, 'inputs': inputs, 'asked': asked, 'core_asked': core_asked, 'named': named, 'out': out,
            'solved': named.get(args.get('for')), 'block': ('calendar', block), 'before': before, 'after': after}


def _places(core, kinds):
    """The kinds of the numbers of a core expression the line wrote itself, by their places, in order."""
    literals, at = {}, 0
    for found, kind in zip(re.finditer(r'\d+', core), kinds):literals[(found.start(), found.end())] = kind
    return literals


def _dated(value):
    """Every date of a result, as its day number."""
    if isinstance(value, list):
        for v in value:yield from _dated(v)
    elif isinstance(value, dict):
        if value.get('unit') == 'date' and 'rational' in value:yield rational(value['rational'])
        for v in value.values():
            if isinstance(v, (list, dict)):yield from _dated(v)


def _on_calendar(record):
    """A date worked out is a whole day of the calendar Graphite reads, the years 1 to 9999: one that falls partway
    through a day, or outside those years, is refused."""
    value = (record.get('result') or {}).get('value')
    if isinstance(value, dict) and value.get('unit') == 'date' and rational(value['rational']).denominator != 1:
        typed.refuse('DOMAIN_ERROR', 'a date is a whole day, and this one falls partway through one')
    if any(not 1 <= day <= LAST for day in _dated(record.get('result'))):_beyond()


def _deadline(start, end, clamped, said, excluded):
    def day(d):return None if d is None else mark({**number_record(Fraction(d.toordinal()))}, 'date')
    def after(record):
        last = end if said == 'included' else excluded if said == 'excluded' else None
        record['result']['deadline'] = {'rule': record['asked']['expression'], 'count': int(record['asked']['count']), 'unit': record['asked']['unit'],
                                        'start': day(start), 'end': day(end), 'end_day': said, 'last_day': day(last),
                                        'last_day_if_excluded': day(excluded), 'clamped': clamped}
    return after


# -- the last day of a period after an event, as an answer (0.8.6 S2) ----------------------------------------------------

UNLESS = 'unless it is a public holiday; holidays not recorded'
NOT_COVERED = 'Not covered: the time of day, how a notice is served or received, court days, and periods counted backwards.'


def _day(value):return None if value is None else mark(number_record(Fraction(value.toordinal())), 'date')


def _period_events(args):
    """The event as the owner gave it: ('ONE', [day]), ('ONE_OF', days) or ('BETWEEN', [first, last]); in words otherwise."""
    if not re.fullmatch(r'\d{1,7}', str(args.get('count', ''))) or not 1 <= int(args['count']) <= LONGEST:
        typed.refuse('UNSUPPORTED', 'count a period after an event in whole days, at least 1, such as 21 days after 2026-09-30')
    if args.get('unit') not in (None, 'days'):
        typed.refuse('UNSUPPORTED', 'a period after an event is counted in days here; months, years and business days are counted by a deadline')
    if len([k for k in ('after', 'events', 'between') if args.get(k)]) != 1:
        typed.refuse('UNSUPPORTED', 'give the event once: the day it happened, the days it may have been, or the range of days it falls in')
    if args.get('after'):return 'ONE', [day_of(args['after'])]
    if args.get('events'):
        days = [day_of(d) for d in args['events']]
        if not 2 <= len(days) <= EVENTS or len(set(days)) != len(days):
            typed.refuse('UNSUPPORTED', 'give from 2 to %d different days the event may have been' % EVENTS)
        return 'ONE_OF', days
    days = [day_of(d) for d in args['between']]
    if len(days) != 2 or days[0] >= days[1]:typed.refuse('UNSUPPORTED', 'give the range of days the event falls in earlier day first, such as 2026-09-30 2026-10-03')
    return 'BETWEEN', days


def _period(args, block, today):
    kind, events = _period_events(args);n = int(args['count'])
    labels = list(args.get('labels') or ())
    if labels and len(labels) != len(events):typed.refuse('UNSUPPORTED', 'give one name for each day the event may have been')
    rule = args.get('roll') or None;skips = tuple(s for s in SKIPS if s in (rule or {}).get('skips', ()))
    held = {day_of(h) for h in args.get('holidays') or ()};yearly = yearly_of(args.get('yearly'))
    unless = 'holidays' in skips and not (held or yearly)
    as_of = day_of(args['as_of']) if args.get('as_of') else today
    origin = 'GIVEN_IN_LINE' if args.get('as_of') else 'CLOCK' if today else None
    on = day_of(args['on']) if args.get('on') else None
    rows, steps = [], ['The question: the last day, %d day%s after %s.' % (n, '' if n == 1 else 's', _event_words(kind, events))]
    for i, event in enumerate(events):
        day, last, over = last_day(event, n, skips, held, yearly)
        moved = None if rule else roll(day, SKIPS, held, yearly)[0]
        rows.append({'label': labels[i] if labels else None, 'event': _day(event), 'day': _day(day), 'last_day': _day(last),
                     'passed_over': [{'day': d.isoformat(), 'as': why} for d, why in over], 'if_moved': _day(moved) if moved != day else None,
                     'since': (as_of - last).days if as_of else None})
        steps.append('Day %d after %s is %s%s.' % (n, words_of(event), words_of(day), '' if last == day else
                     '; %s passes over %s: the last day is %s' % (rule['clause'], ', '.join(words_of(d) for d, _ in over), words_of(last))))
    lasts = [date.fromisoformat(row['last_day']['iso']) for row in rows];first, latest = min(lasts), max(lasts)
    if kind == 'BETWEEN':steps.append('Counting on and passing over a day never move a date earlier, so the earliest event gives the earliest last day '
                                      'and the latest event the latest: both ends are exact.')
    if kind != 'ONE':steps.append('Within the period on every reading: on or before %s; on at least one: on or before %s.' % (words_of(first), words_of(latest)))
    period = {'count': n, 'event': kind, 'readings': rows, 'every': _day(first), 'some': _day(latest), 'unless_holiday': unless,
              'roll': dict(rule) if rule else None, 'counting': 'EVENT_DAY_IS_DAY_0',
              'on': {'day': _day(on), 'readings': [on <= last for last in lasts], 'every': on <= first, 'some': on <= latest} if on else None}
    result = {'period': period, **({'value': _day(lasts[0])} if kind == 'ONE' else {'range': [_day(first), _day(latest)], 'status': typed.ranges.ATTAINED})}
    block.update(kinds={}, result='date', period={'counting': 'EVENT_DAY_IS_DAY_0', 'count_clause': args.get('count_clause'), 'roll': rule, 'skips': list(skips),
                                                 'yearly': sorted('%02d-%02d' % md for md in yearly), 'holiday_clause': args.get('holiday_clause'),
                                                 'holidays_recorded': bool(held or yearly), 'as_of': as_of.isoformat() if as_of else None, 'as_of_origin': origin})
    asked = {k: args[k] for k in ('count', 'after', 'events', 'between', 'labels', 'roll', 'count_clause', 'holiday_clause', 'holidays', 'yearly', 'on', 'as_of') if k in args}
    record = {'schema': typed.answers.SCHEMA, 'stage': 'calculate' if kind == 'ONE' else 'range',
              'asked': {**asked, 'rule': 'period', 'expression': '%d days after %s' % (n, _event_words(kind, events))},
              'model': None, 'model_digest': None, 'assumptions': [], 'obligations': [], 'inputs': [], 'result': result, 'state': 'ANSWERED',
              'for_all': None, 'witness': None, 'guarantee': 'EXACT_VALUE' if kind == 'ONE' else 'EXACT_RANGE', 'derivation': steps[:8],
              'freshness': 'CURRENT', 'reason': '', 'model_calls': 0, 'physical_qualification': False,
              'as_of': {'day': as_of.isoformat(), 'origin': origin} if as_of else None}
    return typed.seal(record, ('calendar', block), KIT)


def _event_words(kind, days):
    if kind == 'ONE':return words_of(days[0])
    if kind == 'BETWEEN':return 'an event between %s and %s' % (words_of(days[0]), words_of(days[1]))
    return 'an event on one of %s' % ', '.join(words_of(d) for d in days)


def _skip_words(skips):
    said = ['a ' + {'saturday': 'Saturday', 'sunday': 'Sunday', 'holidays': 'public holiday'}[s] for s in skips]
    return ', '.join(said[:-1]) + (' or ' if len(said) > 1 else '') + said[-1]


def _period_said(record):
    p = record['result']['period'];n, rows = p['count'], p['readings'];rule = p['roll'] or {}
    def day(row, key):return show(_r(row[key]), 'date')
    def event(row):return day(row, 'event') + (' (%s)' % row['label'] if row['label'] else '')
    unless = ', ' + UNLESS if p['unless_holiday'] else ''
    if p['event'] == 'ONE':said = '%d days after %s: the last day is %s%s.' % (n, event(rows[0]), day(rows[0], 'last_day'), unless)
    elif p['event'] == 'ONE_OF':
        said = '%d days after the event, the last day is %s%s.' % (n, '; '.join('%s if it was on %s' % (day(r, 'last_day'), event(r)) for r in rows),
                                                              ('; each ' + UNLESS) if unless else '')
    else:
        said = '%d days after an event between %s and %s, the last day is between %s and %s, exact at both ends%s.' % (
            n, event(rows[0]), event(rows[1]), day(rows[0], 'last_day'), day(rows[1], 'last_day'), ('; each ' + UNLESS) if unless else '')
    lines = []
    for r in rows:
        if r['passed_over']:lines.append('Day %d after %s is %s, and %s moves it to %s.' % (n, day(r, 'event'), day(r, 'day'), rule['clause'], day(r, 'last_day')))
        elif r['if_moved']:
            lines.append('Day %d after %s is %s. No rule of yours that moves a last day off a weekend or a holiday is recorded; with one, it '
                         'would be %s.' % (n, day(r, 'event'), day(r, 'day'), day(r, 'if_moved')))
    if p['event'] != 'ONE':
        lines.append('A day on or before %s is within the period on every reading; a day on or before %s, on at least one.' % (
            show(_r(p['every']), 'date'), show(_r(p['some']), 'date')))
    on = p['on']
    if on:
        when = show(_r(on['day']), 'date')
        if p['event'] == 'ONE' or on['every'] or not on['some']:
            lines.append('A day dated %s is %s.' % (when, ('within the period' + (' on every reading' if p['event'] != 'ONE' else '')) if on['every'] else
                                                   'after the last day' + (' on every reading' if p['event'] != 'ONE' else '')))
        elif p['event'] == 'ONE_OF':
            lines.append('A day dated %s is within the period only if the event was on %s.' % (when, ' or '.join(event(r) for r, inside in zip(rows, on['readings']) if inside)))
        else:lines.append('A day dated %s is within the period only if the event was late enough in the range: it is after %s.' % (when, show(_r(p['every']), 'date')))
    as_of = record.get('as_of')
    if as_of:
        since = [r['since'] for r in rows];when = words_of(date.fromisoformat(as_of['day'])) + (" (this computer's clock)" if as_of['origin'] == 'CLOCK' else '')
        if all(s > 0 for s in since) and len(since) == 1:lines.append('As of %s, the last day passed %s.' % (when, _days_ago(since)))
        elif all(s > 0 for s in since):lines.append('As of %s, %s passed: %s.' % (when, 'both last days have' if len(since) == 2 else 'every last day has', _days_ago(since)))
        else:lines.append('As of %s: %s.' % (when, '; '.join('%s %s' % (day(r, 'last_day'), _since_words(r['since'])) for r in rows)))
    return said, lines


def _listed(said):return ', '.join(said[:-1]) + (' and ' if len(said) > 1 else '') + said[-1]


def _days_ago(since):return _listed(['%d' % s for s in since]) + ' day%s ago' % ('' if since == [1] else 's')


def _quoted(clause):
    """A clause of the owner's source and its words, exactly as recorded, ending a sentence."""
    words = clause['words'].strip()
    return '%s: "%s"%s' % (clause['clause'], words, '' if words[-1:] in '.?!' else '.')


def _since_words(n):
    if n > 0:return 'passed %d day%s ago' % (n, '' if n == 1 else 's')
    return 'is that day' if n == 0 else 'is %d day%s later' % (-n, '' if n == -1 else 's')


def _period_told(block):
    p = block['period'];lines = ['Calendar: whole days written year-month-day, with no time of day and no time zone.']
    counted = p.get('count_clause')
    lines.append('Counting: the day of the event is day 0 and is not counted, by your source, ' + _quoted(counted) if counted else
                 'Counting: the day of the event is day 0 and is not counted; no counting clause of yours is recorded, so this is the line\'s own rule.')
    rule = p.get('roll')
    if rule:lines.append('A last day on %s moves to the next day that is none of these, by your source, %s' % (_skip_words(p['skips']), _quoted(rule)))
    else:lines.append('A last day on a weekend or a public holiday is not moved: no rule of yours that moves one is recorded.')
    yearly = [('%d %s' % (int(md[3:]), MONTHS[int(md[:2]) - 1])) for md in p.get('yearly') or ()]
    listed = [words_of(date.fromisoformat(h)) for h in block.get('holidays') or ()]
    if yearly or listed:
        clause = p.get('holiday_clause');parts = []
        if yearly:parts.append(_listed(yearly) + ' every year')
        if listed:parts.append(_listed(listed) + ', as listed')
        lines.append('Holidays: ' + '; and '.join(parts) + ('; every year\'s by your source, ' + _quoted(clause) if clause and yearly else '.'))
    elif 'holidays' in p.get('skips', ()):lines.append('Holidays: not recorded, so a last day may yet be a public holiday.')
    if p.get('as_of'):
        lines.append('As of: %s, %s.' % (words_of(date.fromisoformat(p['as_of'])), "from this computer's clock; worked out again when the day changes"
                                          if p['as_of_origin'] == 'CLOCK' else 'as given'))
    lines.append(NOT_COVERED)
    return lines


# -- words ---------------------------------------------------------------------------------------------------------------

def label(kind):return {'date': 'date', 'days': 'days'}.get(kind, '1')


def mark(record, kind):
    record['unit'] = label(kind)
    value = rational(record['rational'])
    if kind == 'date' and value.denominator == 1 and 1 <= value <= date.max.toordinal():record['iso'] = date.fromordinal(int(value)).isoformat()
    return record


def show(value, unit, toward=None, bare=False):
    """A date with its weekday (Friday 2026-11-20); a number of days with its unit; a plain number as the core says it."""
    value = Fraction(value)
    if unit == 'date':
        whole = math.ceil(value) if toward == 'up' else math.floor(value)
        if not 1 <= whole <= date.max.toordinal():return 'day number %s, outside the calendar Kas reads' % value
        said = words_of(date.fromordinal(whole))
        return said if value == whole else '%s (partway through it: exact day number %s)' % (said, value)
    if unit == 'days':
        if value.denominator == 1:return str(value) if bare else '%s day%s' % (value, '' if abs(value) == 1 else 's')
        return figure(value, '' if bare else 'days', toward)
    return figure(value, '1', toward)


def _r(record):return rational(record['rational'])


def heading(record):
    rule = (record.get('asked') or {}).get('rule')
    if record['state'] != 'ANSWERED':return None
    return 'Deadline' if rule == 'deadline' else 'Last day' if rule == 'period' else None


def said(record):
    asked = record.get('asked') or {}
    if asked.get('rule') == 'period':return _period_said(record)
    if asked.get('rule') == 'business':
        n = _r(record['result']['value'])
        return '%s business day%s from %s to %s.' % (n, '' if n == 1 else 's', words_of(date.fromisoformat(asked['from'])), words_of(date.fromisoformat(asked['to']))), [
            'The first day is not counted and the last is.']
    if asked.get('rule') != 'deadline':return None
    d = record['result']['deadline'];start, end = d['start'], d['end'];rule = '%s after %s' % (asked['expression'].rsplit(' after ', 1)[0], show(_r(start), 'date'))
    lines = ['%s is day 0 and counting starts the day after it; the end, %s, is %s.' % (show(_r(start), 'date'), show(_r(end), 'date'), _counted(d))]
    if d['end_day'] == 'included':
        said = '%s ends on %s, the end day included.' % (rule, show(_r(end), 'date'))
        lines.append('The end day is included, as you said: the last day inside the period is %s.' % show(_r(end), 'date'))
    elif d['end_day'] == 'excluded':
        said = '%s ends on %s, the end day (%s) excluded.' % (rule, show(_r(d['last_day']), 'date'), show(_r(end), 'date'))
        lines.append('The end day is excluded, as you said: the last day inside the period is %s.' % show(_r(d['last_day']), 'date'))
    else:
        excluded = d['last_day_if_excluded']
        before = 'on ' + show(_r(excluded), 'date') if excluded else 'no day is left inside it, since the first day after the start is the end'
        said = '%s is %s: with the end day included the period ends on %s; with it excluded, %s.' % (rule, show(_r(end), 'date'), show(_r(end), 'date'), before)
        lines.append('Your rule says which: add end included or end excluded to the line.')
    return said[0].upper() + said[1:], lines


def _counted(d):
    n, unit = d['count'], d['unit']
    if unit == 'business days':return 'business day %d, counting Monday to Friday' % n
    if unit in ('months', 'years'):
        return '%d %s on, the calendar\'s way%s' % (n, unit[:-1] if n == 1 else unit, ', the month\'s last day, since that month has no such day' if d['clamped'] else '')
    return 'day %d' % (n * (7 if unit == 'weeks' else 1))


def notes(record):
    value = (record.get('result') or {}).get('value')
    if record['stage'] == 'calculate' and isinstance(value, dict) and value.get('unit') == 'days' and 'relation' not in record['result']:
        n = _r(value)
        if n.denominator == 1 and abs(n) >= 7:
            weeks, days = divmod(abs(n), 7)
            return ['That is %d week%s%s.' % (weeks, '' if weeks == 1 else 's', ' and %d day%s' % (days, '' if days == 1 else 's') if days else '')]
    return []


def told(record):
    block = record.get('calendar') or {};lines = ['Calendar: whole days written year-month-day, with no time of day and no time zone.']
    if block.get('period'):return _period_told(block)
    if any(step['unit'] in ('months', 'years') for step in block.get('steps') or ()):
        lines.append("Months and years are counted the calendar's way: the same day of the month, or the month's last day when the month has no such day.")
    if block.get('business'):
        held = block.get('holidays') or []
        lines.append('Business days: Monday to Friday; ' + ('holidays from your list in this line: %s.' % ', '.join(words_of(date.fromisoformat(h)) for h in held)
                                                          if held else 'no holidays counted, since none were given.'))
    elif block.get('holidays'):lines.append('Holidays listed: none of them changes a count of calendar days.')
    if (record.get('asked') or {}).get('rule') == 'deadline':
        said = (record['asked'].get('end'))
        lines.append('The end day: ' + ({'included': 'included, as you said.', 'excluded': 'excluded, as you said.'}.get(said) or 'not said, so both are shown.'))
    return lines


KIT = {'show': show, 'label': label, 'mark': mark, 'difference': lambda kind:'days' if kind == 'date' else kind, 'told': told, 'notes': notes,
       'said': said, 'heading': heading, 'prefixes': lambda unit:{'upper': 'On or before', 'lower': 'On or after', 'below': 'Before', 'above': 'After'} if unit == 'date' else typed.PREFIXES}


def answer(args, today=None):
    """ledger.math-answer/1 for one dates line; its `calendar` field holds each name's kind, the calendar steps taken
    (and whether one was clamped), the holidays and their source, and the rules. Never raises: a refusal is its state.
    today: the day of this computer's clock, read by the caller (a period without as_of is worked out as of it, origin
    CLOCK); nothing here reads a clock."""
    args = dict(args or {});block = {'kinds': {}, 'result': None, 'steps': [], 'month_end': MONTH_END, 'business_days': 'MONDAY_TO_FRIDAY',
                                     'holidays': [], 'holiday_source': 'LISTED_IN_LINE' if args.get('holidays') else None, 'day_numbers': 'PROLEPTIC_GREGORIAN'}
    asked = {k: args[k] for k in ('expression', 'for', 'within', 'given', 'holidays', 'count', 'unit', 'after', 'from', 'to', 'end', *PERIOD) if k in args}
    stage = args['stage'] if isinstance(args.get('stage'), str) and args['stage'] in (*ORDER, 'deadline', 'business', 'period') else 'calculate'
    try:
        if stage == 'period':
            block['holidays'] = sorted({day_of(h).isoformat() for h in args.get('holidays') or ()})
            return _period(args, block, today)
        spec = _spec(args, block);return typed.answer(spec, KIT)
    except typed.Refused as exc:return typed.refused(stage, asked, ('calendar', block), KIT, exc)
    except (ValueError, ZeroDivisionError, OverflowError):return typed.refused(stage, asked, ('calendar', block), KIT, typed.Refused('UNSUPPORTED', typed.NUMBERS))
    except (KeyError, TypeError, AttributeError):return typed.refused(stage, asked, ('calendar', block), KIT, typed.Refused('UNSUPPORTED', typed.SHAPE))


def dispatch(kernel, op, args, p, today=None):
    """math.dates in the Kernel; `today` is the day of this computer's clock as the Kernel read it (engineering_kernel.today)."""
    return answer(args, today)
