"""The kinds of pencil mark (0.8.7 C2, "Pages in pencil", lane C): a registry like the desk acts.

A pencil mark points at one value on one line of an admitted page and says what kind of thing it is: *limit · Input
voltage, VIN · -0.3 V to 6.5 V*. Whether the desk or the model found it, the value is always the page's own characters,
and the mark stays in pencil until you keep it.

Each kind declares:
  name      one lower-case word, as the model writes it in `L<n> <kind> | <label> | <value>`
  rule      how its value is checked (page_marks.check):
              NUMBER   a number that carries its own unit, adjacent to it (0.8.5's units table makes it a quantity; a unit
                       outside the table, such as °C, keeps it as words); a number whose unit belongs to another number is
                       refused (NUMBER_WITHOUT_ITS_OWN_UNIT)
              PERIOD   a number with a time unit (21 days, 13 months)
              DATE     a date that parses exactly; an order that could be read two ways (03/04/2026) is *cannot tell*
              MONEY    a decimal amount (950.00, 1,204.17); the currency only where the page writes one beside it
              CUE      cue words of the page itself (shall, must, may, means, unless, does not apply, except)
              WORDS    the page's words as they stand, never interpreted
  door      where Keep sends it: FACT (a reviewed reference fact), QUOTE (a pinned quote), RULE (a rule card proposal)
  shown     the kind in words, for the tag and the brief
  rank      the order of value when more than eight are found (lower first)

Packs are the kinds a page of one sort is read with: a domain-neutral core, plus engineering, legal, everyday and health.
The model is told the pack's kinds (message 4) and its grammar admits no other kind; the brief (message 1) lists every
kind once, so it is the same text for every page and is read once and kept.

Health pages are read in pencil only as the document's own words (rule WORDS), never interpreted.

Pure Python: no Qt, no model, no file, network or clock.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

NUMBER, PERIOD, DATE, MONEY, CUE, WORDS = 'NUMBER', 'PERIOD', 'DATE', 'MONEY', 'CUE', 'WORDS'
RULES = (NUMBER, PERIOD, DATE, MONEY, CUE, WORDS)
FACT, QUOTE, RULE = 'FACT', 'QUOTE', 'RULE'
DOORS = (FACT, QUOTE, RULE)
DOOR_WORDS = {FACT: 'a reviewed reference fact', QUOTE: 'a pinned quote', RULE: 'a rule card, proposed'}


@dataclass(frozen=True)
class MarkKind:
    name: str
    rule: str
    door: str
    shown: str
    rank: int

    def __post_init__(self):
        if not re.fullmatch(r'[a-z][a-z_]{1,15}', self.name):raise ValueError('MARK_KIND_NAME: lower-case, 2 to 16')
        if self.rule not in RULES:raise ValueError('MARK_KIND_RULE: %s' % self.rule)
        if self.door not in DOORS:raise ValueError('MARK_KIND_DOOR: %s' % self.door)


KINDS = {}


def register(kind):
    held = KINDS.get(kind.name)
    if held is not None and held != kind:raise ValueError('MARK_KIND_TAKEN: %s' % kind.name)
    KINDS[kind.name] = kind
    return kind


for _k in (
    # the core: any page
    MarkKind('quantity', NUMBER, FACT, 'a number with its unit', 30),
    MarkKind('amount', MONEY, FACT, 'money', 32),
    MarkKind('date', DATE, QUOTE, 'a date', 34),
    MarkKind('period', PERIOD, QUOTE, 'a length of time', 20),
    # engineering
    MarkKind('limit', NUMBER, FACT, 'a most or least value', 10),
    MarkKind('rating', NUMBER, FACT, 'a rated value', 12),
    MarkKind('pin', WORDS, QUOTE, 'a pin and what it does', 40),
    MarkKind('step', WORDS, QUOTE, 'a step of a procedure', 42),
    # legal
    MarkKind('party', WORDS, QUOTE, 'a party named', 44),
    MarkKind('duty', CUE, RULE, 'shall or must', 14),
    MarkKind('right', CUE, RULE, 'may', 16),
    MarkKind('exception', CUE, RULE, 'unless, except, does not apply', 18),
    MarkKind('definition', CUE, QUOTE, 'means', 22),
    # everyday
    MarkKind('amount_due', MONEY, FACT, 'money you are asked to pay', 11),
    MarkKind('due_date', DATE, QUOTE, 'the day it is due', 13),
    MarkKind('sender', WORDS, QUOTE, 'who sent it', 46),
    MarkKind('asks', WORDS, QUOTE, 'what they ask of you', 24),
    MarkKind('reference', WORDS, QUOTE, 'a reference number', 48),
    # health: the document's own words, never interpreted
    MarkKind('result', WORDS, QUOTE, 'a result with its printed range', 26),
    MarkKind('medicine', WORDS, QUOTE, 'a medicine and its dose', 28),
):
    register(_k)

CORE = ('quantity', 'amount', 'date', 'period')
PACKS = {
    'core': CORE,
    'engineering': CORE + ('limit', 'rating', 'pin', 'step'),
    'legal': CORE + ('party', 'duty', 'right', 'exception', 'definition'),
    'everyday': CORE + ('amount_due', 'due_date', 'sender', 'asks', 'reference'),
    'health': ('date', 'result', 'medicine'),
}
PACK_WORDS = {'core': 'any page', 'engineering': 'a datasheet or technical page', 'legal': 'a contract, lease or rule',
              'everyday': 'a bill, statement or letter', 'health': 'a health record, read as written'}

# What says which pack a page is (counted on the page's own words; ties go to the earlier pack).
_SIGNS = {
    'engineering': re.compile(r'(?<![\w.])\d+(?:\.\d+)?\s?(?:m?V|[mu]?A|k?Hz|MHz|m?W|°C|k?Ω|kOhm|ns|us|ms)(?![\w])'
                              r'|\b(?:datasheet|absolute maximum|operating conditions|pin|regulator|junction)\b', re.I),
    'legal': re.compile(r'\b(?:shall|tenant|landlord|lease|clause|agreement|hereby|party|parties|notice|deposit|tenancy)\b|§', re.I),
    'everyday': re.compile(r'(?<![\w.,])\d{1,3}(?:,\d{3})*\.\d{2}(?![\w.])|\b(?:statement|balance|invoice|bill|payment|due|account)\b', re.I),
    'health': re.compile(r'\b(?:mg|mmol/L|dose|tablet|tablets|reference range|prescription|blood)\b', re.I),
}
_ORDER = ('engineering', 'legal', 'everyday', 'health')


def pack_for(text):
    """The pack a page is read with: the sort whose signs it carries most (at least two), else the core."""
    counts = {name: len(_SIGNS[name].findall(str(text or ''))) for name in _ORDER}
    best = max(_ORDER, key=lambda n: (counts[n], -_ORDER.index(n)))
    return best if counts[best] >= 2 else 'core'


def kinds_of(pack):
    if pack not in PACKS:raise ValueError('MARK_PACK_UNKNOWN: %s' % pack)
    return PACKS[pack]


def kind(name):
    return KINDS.get(name)


def brief_lines():
    """Every kind, one line each, in a fixed order (the MARKS brief lists them all so it is the same for every page)."""
    return ['%s: %s' % (k.name, k.shown) for k in sorted(KINDS.values(), key=lambda k: (k.rank, k.name))]
