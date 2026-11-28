"""The fact sheet (0.8.7 C4, "Kas's mind with the model, interwoven", lane C): a receipt cut into slots.

Every answer she gives is cut from its receipt into whole clauses (slots) that carry their own numbers, units, dates and
qualifiers, worked out here from the receipt and nowhere else. A frame (her plain words, or later a phrasing) only joins
the slots; the voice gate (voice_gate) checks the frame, fills it and checks the words again after the fill.

    Sheet   kind, state (HOLDS, FAILS, UNDECIDED), heading, slots in order, register, the receipt's digest
    Slot    name ({ANSWER}, {MARGIN}, ...), its text exactly, whether a frame must say it, and its facts
    Fact    one number, day, amount, count or name as the slot says it, with its exact value, how it was rounded and the
            receipt place it came from (a faint mark on screen leads there)

Receipts it cuts (sheet() picks by shape):

  a maths answer (ledger.math-answer/1) of a check against a limit (<=, <, >=, >):
      check      HOLDS or FAILS:  ANSWER (Yes, No), MARGIN (inside or over the limit, by how much), READING (each ranged
                 reading and its tolerance), and the caveats TOLERANCE (no tolerance on the desk for a reading; how far
                 one may go before the answer changes, from the settle stage) and RECHECK (a tolerance not applied)
      undecided  UNDECIDED: ANSWER (I cannot tell), WHY (whose tolerance reaches both sides of which limit), WITNESS (the
                 corner where it would not hold), DECIDER (the zone of the deciding reading: where it holds), KEEPS (how far
                 a reading taken as asked may go and hold across the whole tolerance)
      changed    any state, when a source changed since (freshness REVIEW_REQUIRED): ANSWER (I cannot tell yet), CHANGED
                 (what changed), WAS (the answer on the sources as they were)
  a period of days (either_way.period_ways): ANSWER, LAST_DAYS (each last day and the event it is counted from), CREDIT
      (what the ledger sheet shows by each), NEXT (what is yours to say)
  a search that found nothing (a dict, see search_sheet): ANSWER, LOOKED (what she looked for and where: the sheet, its
      rows, revision and days), NEXT, or with your COMPLETE word UNSEEN (the days the sheet does not reach)

**Rounding never claims more than is allowed** (0.8.5's rules, applied per slot): an exact decimal of at most six figures is
shown as it is; any other value is rounded to the places the desk's own numbers for that quantity carry (and to no fewer
than three figures), always toward the side the claim is safe on: an allowed upper end down (200/17 V is 11.76 V; the
settled current 16/49 A, read in mA, is 326 mA), an allowed lower end up, a margin to spare down, a range outward, a value
at a failing corner away from the limit, a tolerance that keeps an answer down. A margin over a sound range (not an exact
one) says "at least" and gives its near end only. A value under one V, A, W or s that has to be rounded is shown in its
milli unit (both ends of a range in one unit); one that is exact and short stays as it is (0.25 V).

The clause templates (CLAUSES) are 0.8.6 templates, registered with mind_words and swept by mind_words.check(): no digit in
their fixed words, every number slot naming the receipt place it is read from. Pure Python: no Qt, no Kernel, no model,
no float. model_calls is 0.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from datetime import date
from fractions import Fraction

from . import mind_words

VERSION = 1
KINDS = ('check', 'undecided', 'changed', 'period', 'search')
STATES = ('HOLDS', 'FAILS', 'UNDECIDED')
HEADINGS = {'HOLDS': 'Holds', 'FAILS': 'Does not hold', 'UNDECIDED': 'Cannot tell'}      # math_answers.HEADINGS, the Field's own
ANSWERS = {'HOLDS': 'Yes', 'FAILS': 'No', 'UNDECIDED': 'I cannot tell'}
REGISTERS = {'check': 'plain', 'undecided': 'plain', 'changed': 'plain', 'period': 'formal', 'search': 'warm'}
SHOWN_FIGURES = 6            # an exact decimal of at most this many figures is shown as it is
LEAST_FIGURES = 3            # a rounded value keeps at least this many figures
MOST_FIGURES = 6
MILLI = {'V': 'mV', 'A': 'mA', 'W': 'mW', 's': 'ms'}
MONTH_NAMES = ('January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November',
               'December')
COUNT_WORDS = {2: 'two', 3: 'three'}

# -- her clauses: the fixed words of every slot (0.8.6 templates; a slot of NUMBER_SLOTS names its receipt place) --------
CLAUSES = {
    'answer_yes': 'Yes',
    'answer_no': 'No',
    'answer_cannot': 'I cannot tell',
    'answer_yet': 'I cannot tell yet',
    'margin_inside': '{subject} is inside {limit} with {spare} to spare',
    'margin_above': '{subject} is above {limit} with {spare} to spare',
    'margin_over': '{subject} is over {limit} by {over}',
    'margin_short': '{subject} is short of {limit} by {over}',
    'limit_owned': "{owner}'s {limit} limit",
    'limit_plain': 'the {limit} limit',
    'at_least': 'at least {low}',
    'span': '{low} to {high}',
    'reading_even': '{reader} read {value}, good to {spare} either way',
    'reading_span': '{reader} read {value}, with your tolerance from {low} to {high}',
    'reading_plain': '{reader} read {value}',
    'why_one': 'your {name} tolerance reaches both sides of {limit}',
    'why_many': 'your tolerances reach both sides of {limit}',
    'why_sound': 'the range worked out reaches both sides of {limit}, and it may be wider than the true one',
    'witness_over': 'at {value} it would be {end}, over it',
    'witness_under': 'at {value} it would be {end}, under it',
    'decider_below': 'it holds only while {holder} stays at or below {end}',
    'decider_under': 'it holds only while {holder} stays below {end}',
    'decider_above': 'it holds only while {holder} stays at or above {end}',
    'decider_over': 'it holds only while {holder} stays above {end}',
    'keeps_up': 'up to {end} holds across your whole tolerance',
    'keeps_down': 'down to {end} holds across your whole tolerance',
    'tolerance_none': 'with no tolerance on the {name}, this is judged at the reading; the answer stands for any tolerance under {bound}',
    'tolerance_most': 'with no tolerance on the {name}, it is judged at the reading; the answer stands for tolerances up to {bound}',
    'recheck': 'your tolerance on {name} changed since you set it and needs your recheck, so it is not applied',
    'changed': '{source} has changed since this was worked out, and it needs your review first',
    'changed_source': 'a source of this answer',
    'was': 'on the sources as they were, {said}',
    'last_one': '{clause} gives its last day as {day}, counted from {event}',
    'last_many': '{clause} gives {count} last days: {days}',
    'last_each': '{day} counted from {event}',
    'credit_looked': 'nothing on the desk shows a credit of {amount} by {when}: I looked in {title}',
    'credit_none': 'no credit of {amount} came by {when}, by your word that {title} is complete',
    'credit_found': 'a credit of {amount} is on {title} by {when}',
    'credit_each': 'by {day} it {state}',
    'paid': 'a payment on {day} is {outcomes}',
    'paid_in_time': 'in time for {end}',
    'paid_late': 'late for {end}',
    'either_day': 'either day',
    'the_day': 'the last day',
    'next_complete': 'whether that sheet is complete is yours to say',
    'next_event': 'which event started the period is yours to say',
    'looked': 'nothing on the desk shows {thing}: I looked in {places}',
    'place': '{title} ({rows} rows, revision {n}, {start} to {end})',
    'place_plain': '{title}',
    'looked_complete': 'no {thing} was made from {start} to {end}, by your word that {title} is complete',
    'next_looked': 'whether none was made rests on that sheet being complete, which is yours to say',
    'next_looked_many': 'whether none was made rests on those sheets being complete, which is yours to say',
    'unseen': '{title} ends on {end}, so {count} days up to today are not seen',
}
LIMIT = 'ledger.math-answer/1 result.right (the limit cell)'
NUMBERS = {   # the receipt place each number slot of a clause is read from
    'margin_inside': {'spare': 'ledger.math-answer/1 result.slack, rounded down (a range outward)', 'limit': LIMIT},
    'margin_above': {'spare': 'ledger.math-answer/1 result.slack, rounded down (a range outward)', 'limit': LIMIT},
    'margin_over': {'over': 'ledger.math-answer/1 result.slack, a range rounded outward', 'limit': LIMIT},
    'margin_short': {'over': 'ledger.math-answer/1 result.slack, a range rounded outward', 'limit': LIMIT},
    'why_one': {'limit': LIMIT},
    'why_many': {'limit': LIMIT},
    'why_sound': {'limit': LIMIT},
    'tolerance_none': {'bound': 'ledger.math-answer/1 result.break_even[].tolerance, rounded down'},
    'tolerance_most': {'bound': 'ledger.math-answer/1 result.break_even[].tolerance, rounded down'},
    'limit_owned': {'limit': 'ledger.math-answer/1 result.right (the limit cell)'},
    'limit_plain': {'limit': 'ledger.math-answer/1 result.right (the limit cell)'},
    'at_least': {'low': 'ledger.math-answer/1 result.slack, near end, rounded down'},
    'span': {'low': 'the slot\'s own range, rounded outward', 'high': 'the slot\'s own range, rounded outward'},
    'reading_even': {'value': 'ledger.math-answer/1 inputs[].value', 'spare': 'ledger.math-answer/1 inputs[].range'},
    'reading_span': {'value': 'ledger.math-answer/1 inputs[].value', 'low': 'ledger.math-answer/1 inputs[].range',
                     'high': 'ledger.math-answer/1 inputs[].range'},
    'reading_plain': {'value': 'ledger.math-answer/1 inputs[].value'},
    'witness_over': {'value': 'ledger.math-answer/1 witness.assignment', 'end': 'ledger.math-answer/1 witness.value, away from the limit'},
    'witness_under': {'value': 'ledger.math-answer/1 witness.assignment', 'end': 'ledger.math-answer/1 witness.value, away from the limit'},
    'decider_below': {'end': 'ledger.math-answer/1 result.zones[].holds.upper, rounded down'},
    'decider_under': {'end': 'ledger.math-answer/1 result.zones[].holds.upper, rounded down'},
    'decider_above': {'end': 'ledger.math-answer/1 result.zones[].holds.lower, rounded up'},
    'decider_over': {'end': 'ledger.math-answer/1 result.zones[].holds.lower, rounded up'},
    'keeps_up': {'end': 'ledger.math-answer/1 result.moves[].rise.to, rounded down'},
    'keeps_down': {'end': 'ledger.math-answer/1 result.moves[].fall.to, rounded up'},
    'last_one': {'day': 'either_way.period_ways ways[].last_day'},
    'last_each': {'day': 'either_way.period_ways ways[].last_day'},
    'last_many': {'count': 'either_way.period_ways ways (distinct last days)'},
    'credit_looked': {'amount': 'either_way.period_ways receipt.amount'},
    'credit_none': {'amount': 'either_way.period_ways receipt.amount'},
    'credit_found': {'amount': 'either_way.period_ways receipt.amount'},
    'credit_each': {'day': 'either_way.period_ways ways[].last_day'},
    'paid': {'day': 'either_way.period_ways receipt.on'},
    'paid_in_time': {'end': 'either_way.period_ways ways[].last_day'},
    'paid_late': {'end': 'either_way.period_ways ways[].last_day'},
    'place': {'rows': 'the sheet searched: its row count', 'n': 'the sheet searched: its revision',
              'start': 'the sheet searched: its first day', 'end': 'the sheet searched: its last day'},
    'looked_complete': {'start': 'the sheet searched: its first day', 'end': 'the sheet searched: its last day'},
    'unseen': {'end': 'the sheet searched: its last day', 'count': 'days from its last day to today, by this computer\'s clock'},
}


def _say(key, **slots):return CLAUSES[key].format(**slots)


# -- the shapes ---------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Fact:
    """One number, day, amount, count or name as a slot says it."""
    said: str                        # as the slot reads: '11.76 V', '21 October', '1,200.00', '§ 12(a)'
    kind: str                        # quantity, day, amount, count, name
    exact: str = ''                  # the exact value: '200/17' (in `unit`), an ISO day, '1200.00'; '' for a name
    unit: str = ''                   # the unit `exact` is in
    rounding: str = 'EXACT'          # EXACT, DOWN, UP
    ref: dict = field(default_factory=dict)       # where on the receipt it came from

    def as_record(self):return {'said': self.said, 'kind': self.kind, 'exact': self.exact, 'unit': self.unit, 'rounding': self.rounding,
                                'ref': dict(self.ref)}


@dataclass(frozen=True)
class Slot:
    name: str
    text: str
    must: bool = True
    facts: tuple = ()
    state: str = ''                  # the ANSWER slot's verdict: HOLDS, FAILS or UNDECIDED

    def as_record(self):return {'name': self.name, 'text': self.text, 'must': self.must, 'state': self.state,
                                'facts': [f.as_record() for f in self.facts]}


@dataclass(frozen=True)
class Sheet:
    kind: str
    state: str
    heading: str
    slots: tuple
    register: str = 'plain'
    receipt: str = ''                # the receipt's digest
    complete: bool = False           # an absence here is read under your COMPLETE word
    version: int = VERSION
    model_calls: int = 0

    def slot(self, name):return next((s for s in self.slots if s.name == name), None)

    @property
    def names(self):return tuple(s.name for s in self.slots)

    @property
    def shape(self):
        """The sheet's shape: its kind and slot names, and the version of this cutter (ledger.phrasing/1 keys by it)."""
        return '%s/%d:%s' % (self.kind, self.version, '+'.join(self.names))

    def facts(self):return [f for s in self.slots for f in s.facts]

    def as_record(self):
        return {'kind': self.kind, 'state': self.state, 'heading': self.heading, 'register': self.register, 'receipt': self.receipt,
                'complete': self.complete, 'shape': self.shape, 'version': self.version, 'model_calls': self.model_calls,
                'slots': [s.as_record() for s in self.slots]}


def _answer(state, yet=False):
    key = 'answer_yet' if yet else {'HOLDS': 'answer_yes', 'FAILS': 'answer_no'}.get(state, 'answer_cannot')
    return Slot('ANSWER', _say(key), True, (), state)


# -- numbers as she shows them ------------------------------------------------------------------------------------------
def _decimals(value):
    """The places a terminating decimal needs, or None when it does not terminate."""
    value = Fraction(value);d = value.denominator;n = 0
    while d % 10 == 0:d //= 10;n += 1
    twos = fives = 0
    while d % 2 == 0:d //= 2;twos += 1
    while d % 5 == 0:d //= 5;fives += 1
    return None if d != 1 else n + max(twos, fives)


def _figures(value, places):
    """The significant figures `value` shows with `places` decimals."""
    whole = abs(Fraction(value)) * Fraction(10) ** places
    return len(str(math.floor(whole))) if whole >= 1 else 0


def _text(value, places):
    """An exact multiple of 10**-places as a decimal string."""
    value = Fraction(value);sign = '-' if value < 0 else '';value = abs(value)
    scaled = value * 10 ** places
    if scaled.denominator != 1:raise ValueError('VOICE_ROUNDING: not on the places asked')
    digits = str(scaled.numerator).rjust(places + 1, '0')
    return sign + (digits[:-places] + '.' + digits[-places:] if places else digits)


def round_to(value, places, toward):
    """`value` rounded to `places` decimals: 'down' (toward minus infinity), 'up', or 'near' (half up). Exact."""
    scaled = Fraction(value) * Fraction(10) ** places
    n = math.floor(scaled) if toward == 'down' else math.ceil(scaled) if toward == 'up' else math.floor(scaled + Fraction(1, 2))
    return Fraction(n, 10 ** places)


def _short(value):
    """Whether `value` is an exact decimal of at most SHOWN_FIGURES figures (shown as it is)."""
    exact = _decimals(value)
    return exact is not None and len(_text(value, exact).lstrip('-').replace('.', '').lstrip('0')) <= SHOWN_FIGURES


def display(value, unit, milli=True):
    """(value, unit) as she shows it: a value under one V, A, W or s that has to be rounded is shown in its milli unit
    (16/49 A is 326 mA); one she can show exactly stays in its unit (0.25 V)."""
    value = Fraction(value)
    if milli and unit in MILLI and value != 0 and abs(value) < 1 and not _short(value):return value * 1000, MILLI[unit]
    return value, unit


def _in(value, unit, to):
    """`value` in `unit` converted to the unit `to` (only the milli steps this module makes)."""
    if unit == to:return Fraction(value)
    if MILLI.get(unit) == to:return Fraction(value) * 1000
    if MILLI.get(to) == unit:return Fraction(value) / 1000
    return None


def desk_places(values, unit, to=None):
    """The most decimal places the desk's own numbers carry for a quantity: `values` [(value, unit)] in `to` (default
    `unit`). Non-terminating values and other units are passed over."""
    to = to or unit;most = 0
    for v, u in values:
        x = _in(v, u, to)
        if x is None:continue
        d = _decimals(x)
        if d is not None:most = max(most, d)
    return most


def shown(value, unit, toward='near', places=0, milli=True):
    """(said, rounding): a value in words, never claiming more than is allowed. An exact decimal of at most SHOWN_FIGURES
    figures as it is; otherwise rounded `toward` ('down', 'up') to `places` decimals of the shown unit, widened to at least
    LEAST_FIGURES figures and never past MOST_FIGURES."""
    v, u = display(value, unit, milli)
    if _short(v):
        text, rounding = _text(v, _decimals(v)), 'EXACT'
    else:
        p = max(0, int(places))
        while _figures(v, p) < LEAST_FIGURES and p < 12:p += 1
        while p > 0 and _figures(v, p) > MOST_FIGURES:p -= 1
        r = round_to(v, p, toward)
        text, rounding = _text(r, p), ('EXACT' if r == v else {'down': 'DOWN', 'up': 'UP'}.get(toward, 'NEAR'))
    return ('%s %s' % (text, u) if u not in ('', '1') else text), rounding


def _fact(value, unit, toward, desk, ref, milli=True):
    """A quantity fact, rounded `toward` at the places the desk's own numbers (`desk`: [(value, unit)]) carry in the unit
    it is shown in."""
    places = desk_places(desk, unit, display(value, unit, milli)[1])
    said, rounding = shown(value, unit, toward, places, milli)
    return Fact(said, 'quantity', str(Fraction(value)), unit, rounding, dict(ref))


def _number(part):
    """The number part of a fact's words ('11.76 V' -> '11.76')."""
    return part.split(' ')[0]


def day_words(day, year=False):
    day = date.fromisoformat(day) if isinstance(day, str) else day
    return '%d %s%s' % (day.day, MONTH_NAMES[day.month - 1], ' %d' % day.year if year else '')


def amount_words(amount):
    """'1200.00' -> '1,200.00': the amount as the papers write it, with its cents, grouped by thousands."""
    value = Fraction(str(amount).replace(',', ''));places = max(2, _decimals(value) or 2)
    text = _text(round_to(value, places, 'near'), places)
    whole, _, cents = text.lstrip('-').partition('.')
    grouped = '{:,}'.format(int(whole))
    return ('-' if text.startswith('-') else '') + grouped + ('.' + cents if cents else '')


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str, separators=(',', ':')).encode('utf-8')).hexdigest()


# -- a maths answer -------------------------------------------------------------------------------------------------------
def _q(record_value):
    return Fraction(record_value['rational']), record_value.get('unit', '')


def _label(labels, symbol, key, default=None):
    entry = (labels or {}).get(symbol) or {}
    if key in entry:return entry[key]
    name = entry.get('name') or str(symbol).replace('_', ' ')
    if key == 'name':return name
    if key in ('reader', 'holder'):return entry.get('holder') or 'the ' + name
    return default


def _limit_words(record, labels, ref):
    """("Rev B's 4 W limit", [fact]) for the constant side of the relation, or ('', []) when it is not constant."""
    result = record['result'];right = result.get('right') or ()
    if len(right) != 2 or right[0]['rational'] != right[1]['rational']:return '', []
    value, unit = _q(right[0])
    limit = next((row['name'] for row in record['inputs'] if row.get('role') == 'limit'), None)
    places = _desk_values(record)
    fact = _fact(value, unit, 'near', places, dict(ref, at='result.right'))
    owner = _label(labels, limit, 'owner') if limit else None
    words = _say('limit_owned', owner=owner, limit=fact.said) if owner else _say('limit_plain', limit=fact.said)
    return words, [fact]


def _desk_values(record):
    """Every (value, unit) the desk gave this answer: the readings, the range ends, the limit."""
    out = []
    for row in record.get('inputs') or ():
        if row.get('value'):out.append(_q(row['value']))
        for end in row.get('range') or ():out.append(_q(end))
    for end in (record.get('result') or {}).get('right') or ():out.append(_q(end))
    return out




def _range_words(lo, hi, unit, places, ref):
    """(words, facts) for a range rounded outward, or one value when its ends meet."""
    if lo == hi:
        f = _fact(lo, unit, 'down', places, ref);return f.said, [f]
    # both ends in one unit: the milli unit only when both ends would take it
    milli = display(lo, unit)[1] != unit and display(hi, unit)[1] != unit
    a = _fact(lo, unit, 'down', places, ref, milli);b = _fact(hi, unit, 'up', places, ref, milli)
    if a.said.split(' ', 1)[1:] == b.said.split(' ', 1)[1:]:words = _say('span', low=_number(a.said), high=b.said)
    else:words = _say('span', low=a.said, high=b.said)
    return words, [a, b]


def _margin(record, subject, limit_words, ref):
    result = record['result'];relation = result['relation']
    lo, unit = _q(result['slack'][0]);hi, _ = _q(result['slack'][1])
    if relation in ('ge', 'gt'):lo, hi = -hi, -lo
    sound = result.get('status') != 'ATTAINED'
    places = _desk_values(record)
    at = dict(ref, at='result.slack')
    if record['state'] == 'HOLDS':
        if sound:f = _fact(lo, unit, 'down', places, at);words, facts = _say('at_least', low=f.said), [f]
        else:words, facts = _range_words(lo, hi, unit, places, at)
        key = 'margin_inside' if relation in ('le', 'lt') else 'margin_above'
        return _say(key, subject=subject, limit=limit_words, spare=words), facts
    if sound:f = _fact(-hi, unit, 'down', places, at);words, facts = _say('at_least', low=f.said), [f]
    else:words, facts = _range_words(-hi, -lo, unit, places, at)
    key = 'margin_over' if relation in ('le', 'lt') else 'margin_short'
    return _say(key, subject=subject, limit=limit_words, over=words), facts


def _ranged(record):
    return [row for row in record['inputs'] if row.get('range') and row.get('role') != 'limit']


def _reading(record, labels, ref):
    rows = _ranged(record) or [row for row in record['inputs'] if row.get('role') != 'limit' and row.get('value')][:1]
    parts, facts = [], []
    for row in rows[:2]:
        unit = row['unit'];places = _desk_values(record)
        at = dict(ref, at='inputs.%s' % row['name'], source=row.get('source') or {})
        reader = _label(labels, row['name'], 'reader')
        value = _fact(_q(row['value'])[0], unit, 'near', places, at) if row.get('value') else None
        if value is None:continue
        if row.get('range'):
            lo, hi = _q(row['range'][0])[0], _q(row['range'][1])[0];mid = _q(row['value'])[0]
            if hi - mid == mid - lo:
                half = _fact(hi - mid, unit, 'up', places, at)
                parts.append(_say('reading_even', reader=reader, value=value.said, spare=half.said));facts += [value, half]
            else:
                a = _fact(lo, unit, 'down', places, at);b = _fact(hi, unit, 'up', places, at)
                parts.append(_say('reading_span', reader=reader, value=value.said, low=a.said, high=b.said));facts += [value, a, b]
        else:
            parts.append(_say('reading_plain', reader=reader, value=value.said));facts.append(value)
    return ', and '.join(parts), facts


def _why(record, labels, limit_words):
    ranged = _ranged(record)
    if record['result'].get('status') != 'ATTAINED':return _say('why_sound', limit=limit_words)
    if len(ranged) == 1:return _say('why_one', name=_label(labels, ranged[0]['name'], 'name'), limit=limit_words)
    return _say('why_many', limit=limit_words)


def _witness(record, ref):
    witness = record.get('witness')
    if not witness:return None
    relation = record['result']['relation'];ranged = {row['name']: row for row in _ranged(record)}
    parts, facts = [], []
    for name, v in witness['assignment'].items():
        if name not in ranged:continue
        value, unit = _q(v)
        f = _fact(value, unit, 'near', _desk_values(record), dict(ref, at='witness.assignment.%s' % name));parts.append(f.said);facts.append(f)
    if not parts:return None
    value, unit = _q(witness['value'])
    toward = 'up' if relation in ('le', 'lt') else 'down'          # away from the limit: a failing corner stays failing
    end = _fact(value, unit, toward, _desk_values(record), dict(ref, at='witness.value'))
    key = 'witness_over' if relation in ('le', 'lt') else 'witness_under'
    return _say(key, value=' and '.join(parts), end=end.said), facts + [end]


def _decider(record, labels, ref):
    result = record['result'];zones = [z for z in result.get('zones') or () if z.get('state') == 'ANSWERED']
    if not zones:return None
    first = result.get('first');zone = next((z for z in zones if z['name'] == first), zones[0])
    holds = zone.get('holds') or {};unit = zone['unit']
    holder = _label(labels, zone['name'], 'holder');places = _desk_values(record)
    at = dict(ref, at='result.zones.%s.holds' % zone['name'])
    if holds.get('upper') and not holds.get('lower'):
        e = holds['upper'];f = _fact(_q(e['value'])[0], unit, 'down', places, at)
        return _say('decider_below' if e['closed'] else 'decider_under', holder=holder, end=f.said), [f]
    if holds.get('lower') and not holds.get('upper'):
        e = holds['lower'];f = _fact(_q(e['value'])[0], unit, 'up', places, at)
        return _say('decider_above' if e['closed'] else 'decider_over', holder=holder, end=f.said), [f]
    return None


def _keeps(record, ref):
    ranged = {row['name'] for row in _ranged(record)}
    if not ranged:return None
    for m in (record['result'].get('moves') or ()):
        if m['name'] in ranged or any(row['name'] == m['name'] and row.get('role') == 'limit' for row in record['inputs']):continue
        unit = m['unit'];places = _desk_values(record)
        if m.get('rise') and not m.get('fall'):
            f = _fact(_q(m['rise']['to'])[0], unit, 'down', places, dict(ref, at='result.moves.%s.rise' % m['name']))
            return _say('keeps_up', end=f.said), [f]
        if m.get('fall') and not m.get('rise'):
            f = _fact(_q(m['fall']['to'])[0], unit, 'up', places, dict(ref, at='result.moves.%s.fall' % m['name']))
            return _say('keeps_down', end=f.said), [f]
    return None


def _tolerance(record, labels, ref):
    """The caveat for a reading the desk has no tolerance for: how far one may go before the answer changes (settle)."""
    ranged = {row['name'] for row in _ranged(record)};limits = {row['name'] for row in record['inputs'] if row.get('role') == 'limit'}
    found = []
    for b in (record['result'].get('break_even') or ()):
        if b['name'] in ranged or b['name'] in limits or not b.get('tolerance') or b['state'] not in ('HOLDS', 'FAILS'):continue
        value, unit = _q(b['tolerance'])
        if value <= 0:continue
        found.append((value, b, unit))
    if not found:return None
    value, b, unit = min(found, key=lambda x: x[0])
    f = _fact(value, unit, 'down', _desk_values(record), dict(ref, at='result.break_even.%s' % b['name']))
    return _say('tolerance_most' if b['closed'] else 'tolerance_none', name=_label(labels, b['name'], 'name'), bound=f.said), [f]


def _recheck(record, labels):
    for row in record['inputs']:
        if (row.get('tolerance') or {}).get('state') == 'RECHECK':return _say('recheck', name=_label(labels, row['name'], 'name'))
    return None


def math_sheet(record, labels=None, subject='', changed=''):
    """The fact sheet of a maths check against a limit. labels: {symbol: {'name', 'holder', 'reader', 'owner'}} in the
    desk's words (owner: whose limit, e.g. "Rev B"); subject: what is judged ("settled power"); changed: what changed, for
    a receipt whose sources changed since."""
    from . import math_answers
    if not isinstance(record, dict) or record.get('schema') != math_answers.SCHEMA:raise ValueError('VOICE_RECEIPT: not a maths answer')
    state = record.get('state')
    if state not in STATES:raise ValueError('VOICE_SHAPE: the fact sheet cuts a check that holds, does not hold or cannot be told')
    result = record.get('result') or {}
    if result.get('relation') not in ('le', 'lt', 'ge', 'gt') or len(result.get('slack') or ()) != 2:
        raise ValueError('VOICE_SHAPE: the fact sheet cuts a check against a limit')
    ref = {'record': record.get('digest', ''), 'schema': math_answers.SCHEMA}
    subject = subject or 'it'
    limit_words, limit_facts = _limit_words(record, labels, ref)
    if not limit_words:raise ValueError('VOICE_SHAPE: the limit side of the check is not one value')
    stale = record.get('freshness') == 'REVIEW_REQUIRED'
    if state in ('HOLDS', 'FAILS'):
        margin, margin_facts = _margin(record, subject, limit_words, ref)
        reading, reading_facts = _reading(record, labels, ref)
        core = [Slot('MARGIN', margin, True, tuple(limit_facts + margin_facts))]
        if reading:core.append(Slot('READING', reading, False, tuple(reading_facts)))
    else:
        why = _why(record, labels, limit_words)
        core = [Slot('WHY', why, True, tuple(limit_facts))]
        for name, cut, must in (('WITNESS', _witness(record, ref), False), ('DECIDER', _decider(record, labels, ref), False),
                                ('KEEPS', _keeps(record, ref), False)):
            if cut:core.append(Slot(name, cut[0], must, tuple(cut[1])))
    if stale:
        lead = core[0]
        slots = (_answer('UNDECIDED', yet=True), Slot('CHANGED', _say('changed', source=changed or _say('changed_source')), True),
                 Slot('WAS', _say('was', said=lead.text), True, lead.facts))
        return Sheet('changed', 'UNDECIDED', HEADINGS['UNDECIDED'], slots, REGISTERS['changed'], _digest(record.get('digest') or record))
    slots = [_answer(state)] + core
    tol = _tolerance(record, labels, ref) if state in ('HOLDS', 'FAILS') else None
    if tol:slots.append(Slot('TOLERANCE', tol[0], True, tuple(tol[1])))
    recheck = _recheck(record, labels)
    if recheck:slots.append(Slot('RECHECK', recheck, True))
    kind = 'check' if state in ('HOLDS', 'FAILS') else 'undecided'
    return Sheet(kind, state, HEADINGS[state], tuple(slots), REGISTERS[kind], _digest(record.get('digest') or record))


# -- a period of days -----------------------------------------------------------------------------------------------------
def _quoted(words):return '“%s”' % str(words).replace('“', '').replace('”', '')


def period_sheet(found, looked=None):
    """The fact sheet of a period of days (either_way.period_ways' answer). looked: optional details of the ledger sheet
    read ({'rows', 'revision', 'from', 'to'}), for where she looked."""
    period = found.get('period') or {};receipt = found.get('receipt') or {};ways = list(found.get('ways') or ())
    if not ways or not period.get('clause'):raise ValueError('VOICE_SHAPE: a period needs its clause and its ways')
    state = found.get('state') if found.get('state') in STATES else 'UNDECIDED'
    ref = {'proof': found.get('proof', ''), 'clause': period['clause']}
    clause = Fact(period['clause'], 'name', ref=dict(ref))
    year = len({w['last_day'][:4] for w in ways}) > 1
    days = sorted({w['last_day'] for w in ways})
    day_fact = {d: Fact(day_words(d, year), 'day', d, '', 'EXACT', dict(ref, at='ways.last_day')) for d in days}
    events = {}
    for w in sorted(ways, key=lambda w: (w['last_day'], w['choice'].get('event', ''))):events.setdefault(w['last_day'], w['choice'].get('event', ''))
    names = [Fact(_quoted(events[d]), 'name', ref=dict(ref, at='ways.choice.event')) for d in days]
    if len(days) == 1:
        last = _say('last_one', clause=clause.said, day=day_fact[days[0]].said, event=names[0].said)
        last_facts = [clause, day_fact[days[0]], names[0]]
    else:
        count = Fact(COUNT_WORDS.get(len(days), str(len(days))), 'count', str(len(days)), '', 'EXACT', dict(ref, at='ways'))
        each = ', and '.join(_say('last_each', day=day_fact[d].said, event=n.said) for d, n in zip(days, names))
        last = _say('last_many', clause=clause.said, count=count.said, days=each)
        last_facts = [clause, count] + [day_fact[d] for d in days] + names
    amount = receipt.get('amount')
    title = Fact(_quoted(receipt.get('title') or 'the sheet'), 'name', ref=dict(ref, at='receipt.title'))
    amount_fact = Fact(amount_words(amount), 'amount', str(amount), '', 'EXACT', dict(ref, at='receipt.amount')) if amount else None
    when = _say('either_day') if len(days) == 2 else _say('the_day')
    states = {w['state'] for w in ways};complete = bool(receipt.get('word'))
    credit_facts = [title] + ([amount_fact] if amount_fact else [])
    if receipt.get('on'):
        on = Fact(day_words(receipt['on'], year), 'day', receipt['on'], '', 'EXACT', dict(ref, at='receipt.on'))
        parts = [_say('paid_in_time' if w['state'] == 'HOLDS' else 'paid_late', end=day_fact[w['last_day']].said)
                 for w in sorted(ways, key=lambda w: w['last_day'])]
        credit, credit_facts = _say('paid', day=on.said, outcomes=', and '.join(parts)), [on] + [day_fact[d] for d in days]
    elif states == {'UNDECIDED'} and amount_fact:
        credit = _say('credit_looked', amount=amount_fact.said, when=when, title=title.said)
        if looked:
            details = _place(dict(looked, title=receipt.get('title') or 'the sheet'), ref)
            credit = _say('credit_looked', amount=amount_fact.said, when=when, title=details[0]);credit_facts = details[1] + [amount_fact]
    elif states == {'FAILS'} and amount_fact and complete:
        credit = _say('credit_none', amount=amount_fact.said, when=when, title=title.said)
    elif states == {'HOLDS'} and amount_fact:
        credit = _say('credit_found', amount=amount_fact.said, when=when, title=title.said)
    else:
        from .mind_types import STATE_WORDS
        credit = ', and '.join(_say('credit_each', day=day_fact[w['last_day']].said, state=STATE_WORDS.get(w['state'], 'cannot tell'))
                               for w in sorted(ways, key=lambda w: w['last_day']))
        credit_facts = [day_fact[d] for d in days]
    slots = [_answer(state), Slot('LAST_DAYS', last, True, tuple(last_facts)), Slot('CREDIT', credit, True, tuple(credit_facts))]
    if state == 'UNDECIDED':
        if len(states) > 1:slots.append(Slot('NEXT', _say('next_event'), True))
        elif not complete and not receipt.get('on'):slots.append(Slot('NEXT', _say('next_complete'), True))
    return Sheet('period', state, HEADINGS[state], tuple(slots), REGISTERS['period'], _digest(found.get('proof') or receipt), complete)


# -- a search that found nothing ------------------------------------------------------------------------------------------
def _place(place, ref):
    """(words, facts) for one place she looked: the sheet, and its rows, revision and days when the desk gives them."""
    title = Fact(_quoted(place['title']), 'name', ref=dict(ref, at='looked.title'))
    if place.get('rows') is None or place.get('revision') is None or not place.get('from') or not place.get('to'):
        return _say('place_plain', title=title.said), [title]
    year = place['from'][:4] != place['to'][:4]
    rows = Fact(str(int(place['rows'])), 'count', str(int(place['rows'])), '', 'EXACT', dict(ref, at='looked.rows'))
    n = Fact(str(place['revision']), 'count', str(place['revision']), '', 'EXACT', dict(ref, at='looked.revision'))
    start = Fact(day_words(place['from'], year), 'day', place['from'], '', 'EXACT', dict(ref, at='looked.from'))
    end = Fact(day_words(place['to'], True), 'day', place['to'], '', 'EXACT', dict(ref, at='looked.to'))
    return _say('place', title=title.said, rows=rows.said, n=n.said, start=start.said, end=end.said), [title, rows, n, start, end]


def search_sheet(found):
    """The fact sheet of a search that found nothing. found: {'thing': words naming what was looked for ('a credit'),
    'amount'?: its amount as the papers write it, 'looked': [{'title', 'rows'?, 'revision'?, 'from'?, 'to'?}] (at most
    three are named), 'complete': your COMPLETE word covers the one sheet looked in, 'today'?: ISO day, for the days not
    seen}. Absent is not false: without your word she cannot tell."""
    looked = list(found.get('looked') or ())
    if not looked or not found.get('thing'):raise ValueError('VOICE_SHAPE: a search needs what she looked for and where')
    ref = {'search': _digest(found)}
    thing_words = str(found['thing']).strip();facts = []
    if found.get('amount'):
        a = Fact(amount_words(found['amount']), 'amount', str(found['amount']), '', 'EXACT', dict(ref, at='amount'))
        thing_words = '%s of %s' % (thing_words, a.said);facts.append(a)
    if found.get('complete') and len(looked) == 1 and looked[0].get('from') and looked[0].get('to'):
        place = looked[0];title = Fact(_quoted(place['title']), 'name', ref=dict(ref, at='looked.title'))
        year = place['from'][:4] != place['to'][:4]
        start = Fact(day_words(place['from'], year), 'day', place['from'], '', 'EXACT', dict(ref, at='looked.from'))
        end = Fact(day_words(place['to'], True), 'day', place['to'], '', 'EXACT', dict(ref, at='looked.to'))
        bare = re.sub(r'^(?:a|an|the|any)\s+', '', thing_words, flags=re.I)
        said = _say('looked_complete', thing=bare, title=title.said, start=start.said, end=end.said)
        slots = [_answer('FAILS'), Slot('LOOKED', said, True, tuple(facts + [title, start, end]))]
        today = found.get('today')
        if today and today > place['to']:
            gap = (date.fromisoformat(today) - date.fromisoformat(place['to'])).days
            count = Fact(str(gap), 'count', str(gap), '', 'EXACT', dict(ref, at='today'))
            end_short = Fact(day_words(place['to']), 'day', place['to'], '', 'EXACT', dict(ref, at='looked.to'))
            slots.append(Slot('UNSEEN', _say('unseen', title=title.said, end=end_short.said, count=count.said), True, (title, end_short, count)))
        return Sheet('search', 'FAILS', HEADINGS['FAILS'], tuple(slots), REGISTERS['search'], ref['search'], True)
    places, place_facts = [], []
    for place in looked[:3]:
        words, f = _place(place, ref);places.append(words);place_facts += f
    said = _say('looked', thing=thing_words, places='; '.join(places))
    slots = [_answer('UNDECIDED'), Slot('LOOKED', said, True, tuple(facts + place_facts)),
             Slot('NEXT', _say('next_looked' if len(looked) == 1 else 'next_looked_many'), True)]
    return Sheet('search', 'UNDECIDED', HEADINGS['UNDECIDED'], tuple(slots), REGISTERS['search'], ref['search'])


def sheet(receipt, **kw):
    """The fact sheet of any receipt this module cuts: a maths answer, a period's answer, or a search (kind 'search')."""
    if isinstance(receipt, dict) and receipt.get('schema'):return math_sheet(receipt, **kw)
    if isinstance(receipt, dict) and receipt.get('kind') == 'search':return search_sheet(receipt)
    if isinstance(receipt, dict) and receipt.get('period'):return period_sheet(receipt, **kw)
    raise ValueError('VOICE_RECEIPT: not a receipt the fact sheet cuts')


# -- the desk values the WORDS check reads (answer_check, 0.8.6 S7, when it is in this program) ---------------------------
def desk_values(sheet_):
    """[answer_check.Value] for every fact on the sheet: its exact value and, when rounded, its shown value too (the shown
    number is made from the desk by the rounding the fact names). [] when answer_check is not in this program."""
    try:
        from . import answer_check
    except ImportError:
        return []
    out = []
    for f in sheet_.facts():
        where = 'the receipt (%s)' % (f.ref.get('at') or f.kind)
        try:
            if f.kind == 'quantity':
                v = answer_check.value(f.exact, f.unit, where, ref=f.ref)
                number, _, unit = f.said.partition(' ')
                s = answer_check.value(number, unit, where + ', ' + f.rounding.lower(), ref=f.ref) if unit else None
                out += [x for x in (v, s) if x is not None]
            elif f.kind == 'day':
                out.append(answer_check.day_value(f.exact, where, ref=f.ref))
        except (ValueError, TypeError, AttributeError):
            continue
    return out


# -- registered with 0.8.6's templates: swept by mind_words.check() -------------------------------------------------------
mind_words.register('voice_facts', CLAUSES, numbers=NUMBERS)
