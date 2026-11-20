"""Rule cards (0.8.6 S6, "Kas's mind, no model", lane C): a rule from one of your sources, split by you into what it needs,
what stops it (unless) and what it gives, each part beside the exact words it came from, judged four-valued on your records.

A rule is a Project Desk record (kind 'rule', schema ledger.rule/1, on screen "rule card"). It is yours: you split it, and
rules.set is approve scope and named in stacy_hand.ALWAYS_ASKS, so it asks at every place of the dial; her calls cannot set
one. Kasandra may propose a split from a table row (rules.check {propose}), shown as "mine, not agreed"; a proposal writes
nothing, and she never applies a split you have not agreed.

  title     your label for it ("§ 12(c)", "R1"); saying a rule again under the same title is a new revision of it
  sort      STATUTE_TEXT | CONTRACT | SPECIFICATION | OTHER (a card resting on a STATUTE_TEXT or CONTRACT rule always
            carries the fixed footer, mind_words.FOOTER)
  needs     the elements, each {says, source, test}; unless: the exceptions, the same shape
  gives     {source, says?, limit? {value, unit}, amount? {of: source, times}}: what follows; its words are the source's
  beyond    {of: {row} | {calculation}, options: [rows]}: for a rule whose need bounds a quantity ("up to 40 ms"), what is
            judged past the bound and which rows could apply there (your CHOICE word, word.set {sort: CHOICE, rule, choice,
            cell} or {rule, none}, says which)

Every part rests on a source: a pinned quote (quotes.py: exact words on an admitted page) or a reviewed row (a sheet's
Value cell). A rule with a part that rests on neither is refused: RULE_WITHOUT_SOURCE.

A test says how an element is told on your records, never by guessing:

  {account: words, contrary?: words}       your own account (a SAYS word with exactly these words) holds it; the
                                           contrary words make it not hold
  {found: words, shows?: HOLDS | FAILS}    a pinned quote of exactly these words, current on its admitted page
  {absent: {sheet, amount, from, to}}      no row of that amount on the sheet between those days: holds only by your
                                           COMPLETE word for the sheet over those days; a row found makes it not hold
  {compare: {of, at_most | at_least, reading?}}   a row or a calculation, exactly, against a bound; a bound read from a
                                           row's words is used only once your READING word for those words is said
  {word: id, shows?}                       one of your words
  {open: premise}                          nothing on the desk tells it yet; the premise names who would settle it

Four values, never the fallacies (the Belnap lattice of stac/evidence.py, written out here: importing the stac
package from a module the Kernel imports would import the Kernel back): the needs are their conjunction; the exceptions
their disjunction; the rule fires on needs AND NOT exceptions. The conclusion is SUPPORTED only when the rule fires,
CONFLICT when the firing is in conflict ("the records disagree"), and otherwise UNKNOWN: needs that do not hold give no
conclusion either way, an exception that cannot be told never lets the rule fire, and a conclusion supported elsewhere
changes nothing in the needs (nothing here reasons backwards).

Freshness is computed on read: a rule resting on a quote that is not CURRENT (moved or gone in the revision admitted now),
or on a row that reads differently now, is STALE, goes to recheck and is not applied.

  rules.list   {all?}                                       read      each rule with its freshness
  rules.get    {id}                                         read      the rule, its card, its history
  rules.check  {id?} | {propose: {sheet, cell}}             read      the card(s) judged now; or her proposed split
  rules.set    {title, sort, needs, unless?, gives, beyond?}   approve   ALWAYS_ASKS
               | {id, expected_revision, state}             set aside (OUT) or take back (IN)

Her words are fixed templates (WORDS, scanned by mind_words.check): the card is titled as a question about your records,
the conclusion is the rule's own quoted words introduced by mind_words.INTRO. Pure Python apart from the Kernel's own
record store and the sheets it reads; no Qt, no model, no float: every number is an exact Fraction.
"""
from __future__ import annotations

import re
from datetime import date
from fractions import Fraction
from itertools import combinations, product

from . import project_desk as records
from . import mind_types as mt
from .mind_types import HOLDS, FAILS, UNDECIDED, CONFLICT

KIND = 'rule'
SCHEMA = 'ledger.rule/1'
SHOWN = 'rule card'
SORTS = ('STATUTE_TEXT', 'CONTRACT', 'SPECIFICATION', 'OTHER')
CURRENT, STALE = 'CURRENT', 'STALE'
SUPPORTED, UNKNOWN = 'SUPPORTED', 'UNKNOWN'          # a conclusion: SUPPORTED, UNKNOWN or CONFLICT; never REFUTED
CONCLUSIONS = (SUPPORTED, UNKNOWN, CONFLICT)
TESTS = ('account', 'found', 'absent', 'compare', 'word', 'open')
PARTS = ('needs', 'unless')
MAX_ELEMENTS = 8
MAX_OPEN = 8                  # open leaves weighed exactly (every completion); past it, the budget sentence

_ID = {'type': 'string', 'pattern': '^[a-f0-9]{32}$'}
_SHEET = {'type': 'string', 'pattern': '^owner:[a-f0-9]{32}$'}
_CELL = {'type': 'string', 'pattern': '^B[1-9][0-9]{0,2}$'}
_ROW = {'type': 'object', 'additionalProperties': False, 'required': ['sheet', 'cell'], 'properties': {'sheet': _SHEET, 'cell': _CELL}}
_SOURCE = {'type': 'object', 'additionalProperties': False, 'properties': {'quote': _ID, 'row': _ROW}}
_QTY = {'type': 'object', 'additionalProperties': False, 'required': ['value', 'unit'],
        'properties': {'value': {'type': 'string', 'minLength': 1, 'maxLength': 40}, 'unit': {'type': 'string', 'minLength': 1, 'maxLength': 16}}}
_OF = {'type': 'object', 'additionalProperties': False, 'properties': {'row': _ROW, 'calculation': _ID}}
_ELEMENT = {'type': 'object', 'additionalProperties': False, 'required': ['says', 'source', 'test'],
            'properties': {'says': {'type': 'string', 'minLength': 1, 'maxLength': 200}, 'source': _SOURCE, 'test': {'type': 'object'}}}
_GIVES = {'type': 'object', 'additionalProperties': False, 'required': ['source'],
          'properties': {'source': _SOURCE, 'says': {'type': 'string', 'minLength': 1, 'maxLength': 200}, 'limit': _QTY,
                         'amount': {'type': 'object', 'additionalProperties': False, 'required': ['of'],
                                    'properties': {'of': _SOURCE, 'times': {'type': 'integer', 'minimum': 1, 'maximum': 10}}}}}
_BEYOND = {'type': 'object', 'additionalProperties': False, 'required': ['of', 'options'],
           'properties': {'of': _OF, 'options': {'type': 'array', 'items': _ROW}}}
FIELDS = {
    'rules.list': ({'all': {'type': 'boolean'}}, []),
    'rules.get': ({'id': records.ID}, ['id']),
    'rules.check': ({'id': records.ID, 'propose': _ROW}, []),
    'rules.set': ({'title': {'type': 'string', 'minLength': 1, 'maxLength': 80}, 'sort': {'type': 'string', 'enum': list(SORTS)},
                   'needs': {'type': 'array', 'items': _ELEMENT}, 'unless': {'type': 'array', 'items': _ELEMENT}, 'gives': _GIVES,
                   'beyond': _BEYOND, 'id': records.ID, 'expected_revision': records.REV, 'state': {'type': 'string', 'enum': ['IN', 'OUT']}}, []),
}
WRITES = ('rules.set',)
SCOPES = {op: 'approve' if op in WRITES else 'read' for op in FIELDS}
OBSERVERS = ('rules.list', 'rules.get', 'rules.check')

# Her words on a rule card: fixed templates, every number through a slot that names its record (mind_words.check).
WORDS = {
    'title': 'Do {rule}’s conditions, as you recorded them, hold on your records?',
    'holds': 'The conditions hold on your records.',
    'fails': 'The conditions do not hold, so this rule gives no conclusion either way.',
    'open': 'Whether the conditions hold cannot be told yet. What would settle it is below.',
    'conflict': 'Cannot tell: the records disagree about “{says}”.',
    'stale': 'This rule rests on words or rows that changed: {what}. I do not apply it until you set it again.',
    'element': '“{says}”: {state}, by {by}.',
    'element_open': '“{says}”: cannot tell. {settle}',
    'by_account': 'your word “{words}”',
    'settle_account': 'Your own account would settle it: “{words}”.',
    'by_found': 'the pinned quote “{label}”',
    'settle_found': 'A pinned quote of “{words}” from an admitted page would settle it.',
    'settle_found_stale': 'The pinned quote “{label}” is {state} in the revision admitted now.',
    'by_absent_found': 'row {row} of “{title}”, {amount} on {day}',
    'absent_none': 'Nothing on “{title}” ({rows} rows, {start} to {end}) shows a {kind} of {amount}.',
    'absent_yours': 'Whether none was made rests on that sheet being complete, which is yours to say.',
    'by_complete': 'your word that “{title}” is complete from {start} to {end}',
    'absent_complete': 'No {kind} of {amount} was made between {start} and {end}, by your word that the sheet is complete.',
    'settle_reading': 'How “{span}” reads is yours to say. I do not use a reading until you say Right.',
    'settle_unit': '“{unit}” is not a unit I read. It stays words until you say.',
    'settle_row': 'That row or calculation cannot be read now.',
    'settle_tolerance': '“{what}” is {low} to {high} against {bound}. A reading closer than that would settle it.',
    'by_compare': '“{what}” at {value} against {bound}',
    'by_word': 'your word “{statement}”',
    'settle_word': 'Your word would settle it.',
    'settle_YOU': 'It is yours to say.',
    'settle_WORLD': 'A document or reading not yet on the desk would settle it.',
    'settle_RECORDS': 'Your records would settle it.',
    'settle_MATHS': 'The maths would settle it.',
    'settle_MODEL': 'It is yours to say.',
    'conclusion': 'On the rules you recorded, against the text you admitted: “{words}”',
    'amount': 'Worked out: {parts} = {total}.',
    'no_conclusion': 'The conclusion gets no support from this rule.',
    'covers': 'The {limit} of “{rule}” covers only up to {bound}.',
    'uncovered': 'From {bound} to {end}, no row on the desk gives a limit. Which applies there is yours to say.',
    'beyond_option': 'If “{option}” applies: {state}, {value} against {limit}{room}.',
    'beyond_none': 'If none applies, no row on the desk limits it from {bound} to {end}.',
    'beyond_chosen': 'By your word, “{option}” applies past {bound}: {state}, {value} against {limit}{room}.',
    'beyond_chosen_none': 'By your word, no row applies from {bound} to {end}.',
    'over': ', over by {over}',
    'spare': ', {spare} to spare',
    'mine': 'mine, not agreed',
    'choice_row': 'Past what “{rule}” covers, “{parameter}” ({title}, row {row}) applies',
    'choice_none': 'Past what “{rule}” covers, no row on the desk applies',
}
NUMBERS = {
    'by_absent_found': {'amount': 'the sheet row found', 'day': 'the same row'},
    'absent_none': {'rows': 'the sheet as it stands', 'start': 'its first row', 'end': 'its last row', 'amount': 'the rule’s test'},
    'by_complete': {'start': 'your COMPLETE word', 'end': 'your COMPLETE word'},
    'absent_complete': {'amount': 'the rule’s test', 'start': 'the rule’s test', 'end': 'the rule’s test'},
    'settle_tolerance': {'low': 'the row and your tolerance', 'high': 'the row and your tolerance', 'bound': 'the rule’s test'},
    'by_compare': {'value': 'the row or calculation', 'bound': 'the rule’s test'},
    'amount': {'parts': 'the quote or row the amount is read from', 'total': 'worked out from those parts'},
    'covers': {'limit': 'the row the rule gives', 'bound': 'the rule’s need'},
    'uncovered': {'bound': 'the rule’s need', 'end': 'the row the need is judged on'},
    'beyond_option': {'value': 'the quantity judged', 'limit': 'the row named', 'room': 'worked out from both'},
    'beyond_none': {'bound': 'the rule’s need', 'end': 'the row the need is judged on'},
    'beyond_chosen': {'value': 'the quantity judged', 'limit': 'the row named', 'room': 'worked out from both', 'bound': 'the rule’s need'},
    'beyond_chosen_none': {'bound': 'the rule’s need', 'end': 'the row the need is judged on'},
    'over': {'over': 'worked out from the quantity and the limit'},
    'spare': {'spare': 'worked out from the quantity and the limit'},
}


def _register():
    from . import mind_words
    title = {'title': WORDS['title']}
    mind_words.register('rules', {k: v for k, v in WORDS.items() if k not in title and k not in ('mine',)}, numbers=NUMBERS)
    mind_words.register('rules', title, kind='title')
    mind_words.register('rules', {'mine': WORDS['mine']}, kind='button')


_register()


# ---- the four values, never the fallacies --------------------------------------------------------------------------------------

# A value as (told it holds, told it does not): HOLDS (1, 0), FAILS (0, 1), UNDECIDED (0, 0), CONFLICT (1, 1).
_TO = {HOLDS: (True, False), FAILS: (False, True), UNDECIDED: (False, False), CONFLICT: (True, True)}
_FROM = {v: k for k, v in _TO.items()}


def truth_and(a, b):
    return (a[0] and b[0], a[1] or b[1])


def truth_or(a, b):
    return (a[0] or b[0], a[1] and b[1])


def negate(a):
    return (a[1], a[0])


def _state(support):
    return _FROM[support]


def all_of(states):
    """Belnap conjunction of the needs (HOLDS for none)."""
    found = _TO[HOLDS]
    for s in states:found = truth_and(found, _TO[s])
    return _state(found)


def any_of(states):
    """Belnap disjunction of the exceptions (FAILS for none: no exception applies)."""
    found = _TO[FAILS]
    for s in states:found = truth_or(found, _TO[s])
    return _state(found)


def fires(needs, unless=()):
    """Whether the rule's conditions hold: needs AND NOT exceptions, four-valued."""
    return _state(truth_and(_TO[all_of(needs)], negate(_TO[any_of(unless)])))


def conclusion(fired):
    """What the rule gives its conclusion: SUPPORTED when it fires, CONFLICT when the records disagree, otherwise UNKNOWN.
    Never REFUTED: conditions that do not hold say nothing about the conclusion."""
    return SUPPORTED if fired == HOLDS else CONFLICT if fired == CONFLICT else UNKNOWN


# ---- reading the desk --------------------------------------------------------------------------------------------------------

def norm(text):
    return ' '.join(str(text).split())


def _saved(sheet):
    from .your_word import _saved as saved
    return saved(sheet)


def _row(sheet, cell):
    from .tolerances import sheet_cell
    saved = _saved(sheet)
    return sheet_cell(saved, cell) if saved else None


def _exact(text):
    from .math_units import rational
    return rational(str(text).replace(',', '').strip())


def _shown(value, unit=''):
    """An exact number as she says it: its decimal when it ends, otherwise the fraction; with its unit."""
    from .math_units import number_record
    found = number_record(value)
    text = found['decimal'] if found['decimal_exact'] else found['rational']
    return ('%s %s' % (text, unit)).strip()


def money(value):
    """An exact amount in whole cents with thousands marks (1,200.00); otherwise its exact fraction."""
    cents = value * 100
    if cents.denominator != 1:return str(value)
    whole = abs(cents.numerator)
    return '%s%s.%02d' % ('-' if value < 0 else '', '{:,}'.format(whole // 100), whole % 100)


def day_words(text):
    from .your_word import date_words
    return date_words(text)


def _calculation(kernel, principal, ident):
    """(value, unit, title) of a calculation page as it stands, or None."""
    from . import documents
    try:
        with kernel.db() as db:
            records.ensure(db);d = records.read(db, documents.KIND, ident, principal)
    except ValueError:
        return None
    value = ((((d.get('derivation') or {}).get('calculation') or {}).get('outputs') or [{}])[0] or {}).get('value') or {}
    if not value.get('rational'):return None
    return _exact(value['rational']), value.get('unit') or '', d.get('title') or ''


def quantity(kernel, principal, of, tolerances=None):
    """{lo, hi, unit, what, ref} of a row (with your tolerance on its cell, when it applies) or a calculation; None when it
    cannot be read."""
    if of.get('row'):
        row = _row(of['row']['sheet'], of['row']['cell'])
        if not row:return None
        try:value = _exact(row['value'])
        except ValueError:return None
        lo = hi = value
        said = (tolerances or {}).get((row['address'], row['cell']))
        if said and said.get('state') != 'RECHECK':
            lo, hi = _exact(said['lo']), _exact(said['hi'])
        return {'lo': lo, 'hi': hi, 'unit': row['unit'], 'what': row['parameter'], 'ref': 'office:%s#%s' % (row['sheet'], row['cell'])}
    if of.get('calculation'):
        found = _calculation(kernel, principal, of['calculation'])
        if not found:return None
        value, unit, title = found
        return {'lo': value, 'hi': value, 'unit': unit, 'what': title.split(' · ')[0], 'ref': 'document:' + of['calculation']}
    return None


def _base(value, unit):
    """(dimension, value in base units) or None when the unit is not one Graphite reads."""
    from .math_units import unit_spec
    try:dimension, factor = unit_spec(unit)
    except ValueError:return None
    return dimension, value * factor


def _in_unit(value, unit):
    """A base-unit value written back in `unit`."""
    from .math_units import unit_spec
    return value / unit_spec(unit)[1]


# ---- the record ----------------------------------------------------------------------------------------------------------------

def _all(db, principal):
    records.ensure(db)
    ids = [row[0] for row in db.execute('SELECT id FROM desk_records WHERE owner=? AND kind=? ORDER BY rowid', (principal.identity, KIND))]
    return [records.read(db, KIND, ident, principal) for ident in ids]


def every(kernel, principal):
    with kernel.db() as db:return _all(db, principal)


def read(kernel, principal, ident):
    with kernel.db() as db:
        records.ensure(db);return records.read(db, KIND, ident, principal)


def _source(kernel, principal, source, where):
    """A part's source checked and bound as it stands: {'quote': id, 'label', 'words'} or the row bound as condition cards
    bind it. RULE_WITHOUT_SOURCE when it names neither a pinned quote nor a reviewed row."""
    from . import quotes
    from .your_word import _bind_row
    source = source or {}
    if bool(source.get('quote')) == bool(source.get('row')):
        raise ValueError('RULE_WITHOUT_SOURCE: %s rests on neither a pinned quote nor a reviewed row; pin its words or name its row' % where)
    if source.get('quote'):
        try:quote = quotes.read(kernel, principal, source['quote'])
        except ValueError:raise ValueError('RULE_WITHOUT_SOURCE: %s names a quote that is not pinned' % where) from None
        if quote.get('state') != 'IN':raise ValueError('RULE_WITHOUT_SOURCE: %s names a quote you set aside' % where)
        return {'quote': quote['id'], 'label': quote['label'], 'words': quote['words']}
    saved = _saved(source['row']['sheet'])
    if not saved:raise ValueError('RULE_WITHOUT_SOURCE: %s names a sheet that cannot be read' % where)
    try:return {'row': _bind_row(saved, source['row']['cell'])}
    except ValueError:raise ValueError('RULE_WITHOUT_SOURCE: %s names a row that is not a reviewed Value cell' % where) from None


def _test(test, where):
    """A test as given, checked for its shape; refused in words otherwise."""
    if not isinstance(test, dict) or len([k for k in TESTS if k in test]) != 1:
        raise ValueError('RULE_TEST: %s says how it is told on your records, by one of %s' % (where, ', '.join(TESTS)))
    shows = test.get('shows', HOLDS)
    if shows not in (HOLDS, FAILS):raise ValueError('RULE_TEST: shows is HOLDS or FAILS')
    def text(value, n=300):
        if not isinstance(value, str) or not value.strip() or len(value) > n:raise ValueError('RULE_TEST: %s needs words of up to %d characters' % (where, n))
        return norm(value)
    if 'account' in test:
        if set(test) - {'account', 'contrary'}:raise ValueError('RULE_TEST: an account test takes account and contrary')
        return {'account': text(test['account']), **({'contrary': text(test['contrary'])} if test.get('contrary') else {})}
    if 'found' in test:
        if set(test) - {'found', 'shows'}:raise ValueError('RULE_TEST: a found test takes found and shows')
        return {'found': text(test['found'], 2000), 'shows': shows}
    if 'absent' in test:
        a = test['absent']
        if set(test) - {'absent', 'shows'} or not isinstance(a, dict) or set(a) != {'sheet', 'amount', 'from', 'to'}:
            raise ValueError('RULE_TEST: an absent test names the sheet, the amount and the first and last day')
        if not re.fullmatch(r'owner:[a-f0-9]{32}', str(a['sheet'])):raise ValueError('RULE_TEST: that is not a sheet')
        try:_exact(a['amount']);start, end = date.fromisoformat(a['from']), date.fromisoformat(a['to'])
        except (ValueError, TypeError):raise ValueError('RULE_TEST: an amount is an exact number and a day is YYYY-MM-DD') from None
        if start > end:raise ValueError('RULE_TEST: the first day comes first')
        return {'absent': dict(a), 'shows': shows}
    if 'compare' in test:
        c = test['compare']
        if set(test) != {'compare'} or not isinstance(c, dict) or len([k for k in ('at_most', 'at_least') if k in c]) != 1 or set(c) - {'of', 'at_most', 'at_least', 'reading'}:
            raise ValueError('RULE_TEST: a compare test names what (of), and at_most or at_least a bound')
        of = c.get('of') or {}
        if bool(of.get('row')) == bool(of.get('calculation')):raise ValueError('RULE_TEST: a compare test names one row or one calculation')
        bound = c.get('at_most') or c.get('at_least')
        if not isinstance(bound, dict) or set(bound) != {'value', 'unit'}:raise ValueError('RULE_TEST: a bound is a value and a unit')
        _exact(bound['value'])
        reading = c.get('reading')
        if reading is not None and (not isinstance(reading, dict) or set(reading) != {'sheet', 'cell', 'span'}):
            raise ValueError('RULE_TEST: a reading names the sheet, the row and the exact words')
        return {'compare': dict(c)}
    if 'word' in test:
        if set(test) - {'word', 'shows'} or not re.fullmatch(r'[a-f0-9]{32}', str(test['word'])):raise ValueError('RULE_TEST: a word test names your word')
        return {'word': test['word'], 'shows': shows}
    if test['open'] not in mt.WHO_ANSWERS or set(test) != {'open'}:raise ValueError('RULE_TEST: open names who would settle it (%s)' % ', '.join(mt.WHO_ANSWERS))
    return {'open': test['open']}


def compose(kernel, principal, args):
    """(key, fields) of a rule from what you pressed. Every part names its source; RULE_WITHOUT_SOURCE otherwise."""
    title = norm(args.get('title') or '')
    if not title:raise ValueError('RULE_FIELDS: give the rule a title, for example the section it comes from')
    if args.get('sort') not in SORTS:raise ValueError('RULE_FIELDS: say which sort of source the rule comes from (%s)' % ', '.join(SORTS))
    needs = list(args.get('needs') or ());unless = list(args.get('unless') or ())
    if not needs:raise ValueError('RULE_FIELDS: a rule needs at least one element')
    if len(needs) > MAX_ELEMENTS or len(unless) > MAX_ELEMENTS:raise ValueError('RULE_FIELDS: at most %d needs and %d exceptions' % (MAX_ELEMENTS, MAX_ELEMENTS))
    if not args.get('gives'):raise ValueError('RULE_WITHOUT_SOURCE: say what the rule gives, from its source')
    parts = {};sources = []
    for part, letter, items in (('needs', 'n', needs), ('unless', 'u', unless)):
        parts[part] = []
        for n, element in enumerate(items, 1):
            where = '%s %d' % ('need' if part == 'needs' else 'exception', n)
            if not isinstance(element, dict) or not norm(element.get('says') or ''):raise ValueError('RULE_FIELDS: %s says what it needs, in your words' % where)
            bound = _source(kernel, principal, element.get('source'), where);sources.append(bound)
            parts[part].append({'id': '%s%d' % (letter, n), 'says': norm(element['says']), 'source': element['source'], 'bound': bound,
                                'test': _test(element.get('test'), where)})
    gives = dict(args['gives']);bound = _source(kernel, principal, gives.get('source'), 'what it gives');sources.append(bound)
    gives['bound'] = bound
    if gives.get('limit'):_exact(gives['limit']['value'])
    if gives.get('amount'):
        times = gives['amount'].get('times', 1)
        if not isinstance(times, int) or not 1 <= times <= 10:raise ValueError('RULE_FIELDS: an amount is taken one to ten times')
        of = _source(kernel, principal, gives['amount'].get('of'), 'the amount');sources.append(of)
        _amount_of(of)
        gives['amount'] = {'of': gives['amount']['of'], 'times': times, 'bound': of}
    beyond = args.get('beyond')
    if beyond:
        options = beyond.get('options') or []
        if not 1 <= len(options) <= 4:raise ValueError('RULE_FIELDS: name one to four rows that could apply past the bound')
        of = beyond.get('of') or {}
        if bool(of.get('row')) == bool(of.get('calculation')):raise ValueError('RULE_FIELDS: past the bound, name one row or one calculation to judge')
        if not gives.get('limit'):raise ValueError('RULE_FIELDS: a rule judged past its bound gives a limit')
        for option in options:_source(kernel, principal, {'row': option}, 'a row past the bound')
        beyond = {'of': of, 'options': options}
    fields = {'title': title, 'sort': args['sort'], 'needs': parts['needs'], 'unless': parts['unless'], 'gives': gives, 'beyond': beyond or None,
              'quotes': sorted({s['quote'] for s in sources if 'quote' in s}), 'set_by': 'owner', 'state': 'IN'}
    return records.digest(['RULE', title.lower()]), fields


def _amount_of(bound):
    """The one amount a source holds: a row's value, or the one sum of money in a quote's words."""
    if 'row' in bound:return _exact(bound['row']['value'])
    found = re.findall(r'(?<![\w.,])\d{1,3}(?:,\d{3})*\.\d{2}(?![\d])|(?<![\w.,])\d+\.\d{2}(?![\d])', bound['words'])
    if len(found) != 1:raise ValueError('RULE_AMOUNT: those words hold %s amount; pin words with one amount in them' % ('no' if not found else 'more than one'))
    return _exact(found[0])


def put(kernel, args, principal):
    """Your approval: set a rule (a new record, or a new revision of the rule of the same title), or set one aside (OUT)
    and take it back (IN), each a new revision. Nothing is deleted."""
    if 'id' in args or 'state' in args or 'expected_revision' in args:
        if set(args) != {'id', 'expected_revision', 'state'}:raise ValueError('RULE_SET_FIELDS: set a rule aside or back by its id, revision and IN or OUT alone')
        with kernel.db() as db:
            records.ensure(db)
            value = records.read(db, KIND, args['id'], principal);expected = args['expected_revision']
            if value.get('state') == args['state']:raise ValueError('RULE_ALREADY_%s' % args['state'])
            records.edit(value, expected);value['state'] = args['state']
            return records.write(db, value, principal, 'RULE_SET_ASIDE' if args['state'] == 'OUT' else 'RULE_TAKEN_BACK', expected=expected)
    key, fields = compose(kernel, principal, args)
    with kernel.db() as db:
        records.ensure(db)
        old = next((r for r in _all(db, principal) if r.get('key') == key), None)
        if old is None:return records.write(db, records.new(KIND, principal, schema=SCHEMA, key=key, **fields), principal, 'RULE_SET')
        expected = old['revision'];records.edit(old, expected);old.update(fields)
        return records.write(db, old, principal, 'RULE_SET_AGAIN', expected=expected)


def _bounds(rule):
    """Every source the rule rests on, bound as it was when you set it."""
    out = [e['bound'] for part in PARTS for e in rule.get(part) or ()] + [rule['gives']['bound']]
    if (rule['gives'].get('amount') or {}).get('bound'):out.append(rule['gives']['amount']['bound'])
    return out


def resting_on(quote_ids, kernel, principal):
    """The rules (IN) that rest on any of these quotes: [{'id', 'title'}]."""
    wanted = set(quote_ids or ())
    if not wanted:return []
    return [{'id': r['id'], 'title': r['title']} for r in every(kernel, principal) if r.get('state') == 'IN' and wanted & set(r.get('quotes') or ())]


def freshness(kernel, principal, rule, quote_states=None):
    """(CURRENT or STALE, [what changed, in words]): every quote it rests on CURRENT in the revision admitted now, every row
    it rests on reading as it did."""
    from . import quotes
    changed = [];quote_states = quote_states if quote_states is not None else {}
    for bound in _bounds(rule):
        if 'quote' in bound:
            if bound['quote'] not in quote_states:
                try:quote_states[bound['quote']] = quotes.state(kernel, principal, quotes.read(kernel, principal, bound['quote']))
                except ValueError:quote_states[bound['quote']] = {'state': quotes.GONE}
            now = quote_states[bound['quote']]['state']
            if now != quotes.CURRENT:changed.append('“%s” is %s' % (bound['label'], quotes.STATE_WORDS[now]))
            continue
        row = bound['row'];now = _row(row['sheet'], row['cell'])
        if not now or any(now[k] != row[k] for k in ('parameter', 'value', 'unit', 'conditions')):
            changed.append('row %s of “%s”' % (row['cell'][1:], row['title']))
    return (STALE if changed else CURRENT), sorted(set(changed))


# ---- one element, told on your records -----------------------------------------------------------------------------------------

class _Desk:
    """What a judgement reads, read once: your words, the quotes and their states, the tolerances on cells."""

    def __init__(self, kernel, principal):
        from . import your_word, tolerances, quotes
        self.kernel = kernel;self.principal = principal
        self.words = your_word.standing(kernel, principal)
        self.quotes = [q for q in quotes.every(kernel, principal) if q.get('state') == 'IN']
        self.quote_states = {}
        try:self.tolerances = tolerances.on_cells(kernel, principal)
        except Exception:self.tolerances = {}

    def live(self, sort):
        return [w for w in self.words if w.get('sort') == sort and w.get('state') == 'IN' and w.get('freshness') == 'CURRENT']

    def quote_state(self, quote):
        from . import quotes
        if quote['id'] not in self.quote_states:self.quote_states[quote['id']] = quotes.state(self.kernel, self.principal, quote)
        return self.quote_states[quote['id']]


def _told(state, by, refs=(), **more):
    return {'state': state, 'by': by, 'refs': list(refs), **more}


def _open(premise, settle, refs=(), **more):
    return {'state': UNDECIDED, 'premise': premise, 'settle': settle, 'refs': list(refs), **more}


def _opposite(shows):
    return FAILS if shows == HOLDS else HOLDS


def tell(desk, element):
    """One element's value on your records: {'state', 'by' (her words for what tells it) or 'premise' and 'settle' (who
    would settle it and how), 'refs'}."""
    test = element['test']
    if 'account' in test:
        said = desk.live('SAYS')
        yes = [w for w in said if norm(w['value']['words']).lower() == test['account'].lower()]
        no = [w for w in said if test.get('contrary') and norm(w['value']['words']).lower() == test['contrary'].lower()]
        refs = ['word:' + w['id'] for w in yes + no]
        if yes and no:return _told(CONFLICT, WORDS['by_account'].format(words=yes[0]['value']['words']), refs)
        if yes:return _told(HOLDS, WORDS['by_account'].format(words=yes[0]['value']['words']), refs)
        if no:return _told(FAILS, WORDS['by_account'].format(words=no[0]['value']['words']), refs)
        return _open('OWN_ACCOUNT', WORDS['settle_account'].format(words=test['account']))
    if 'found' in test:
        same = [q for q in desk.quotes if norm(q['words']) == test['found']]
        current = [q for q in same if desk.quote_state(q)['state'] == 'CURRENT']
        if current:
            q = current[0];return _told(test['shows'], WORDS['by_found'].format(label=q['label']), ['quote:' + q['id']])
        if same:
            q = same[0];from .quotes import STATE_WORDS
            return _open('NEW_READING', WORDS['settle_found_stale'].format(label=q['label'], state=STATE_WORDS[desk.quote_state(q)['state']]), ['quote:' + q['id']])
        return _open('NEW_READING', WORDS['settle_found'].format(words=test['found']))
    if 'absent' in test:
        return _absent(desk, test['absent'], test['shows'])
    if 'compare' in test:
        return _compare(desk, test['compare'])
    if 'word' in test:
        found = next((w for w in desk.words if w['id'] == test['word']), None)
        if found and found.get('state') == 'IN' and found.get('freshness') == 'CURRENT':
            return _told(test['shows'], WORDS['by_word'].format(statement=found['statement']), ['word:' + found['id']])
        return _open('OWN_ACCOUNT', WORDS['settle_word'], ['word:' + test['word']])
    who = mt.who(test['open'])[0]
    return _open(test['open'], WORDS['settle_' + who])


def _absent(desk, a, shows):
    """Absent is not false: a row found tells it; nothing found tells it only by your COMPLETE word over those days."""
    from .tolerances import sheet_cell
    saved = _saved(a['sheet'])
    if not saved:return _open('ROW_NOT_READ', WORDS['settle_row'])
    title = (saved.get('document') or {}).get('title') or '';amount = _exact(a['amount'])
    cells = ((saved.get('document') or {}).get('sheets') or [{}])[0].get('cells') or {}
    rows = [sheet_cell(saved, k) for k in sorted(cells, key=lambda k: (len(k), k)) if re.fullmatch(r'B[1-9][0-9]{0,2}', k) and k != 'B1']
    rows = [r for r in rows if r and (r['value'] or r['parameter'])]
    start, end = a['from'], a['to'];days = [];found = [];unread = []
    for r in rows:
        day = r['conditions'] if re.fullmatch(r'\d{4}-\d{2}-\d{2}', r['conditions'] or '') else None
        if day:days.append(day)
        try:same = _exact(r['value']) == amount
        except ValueError:same = False
        if not same:continue
        if day is None:unread.append(r)
        elif start <= day <= end:found.append(r)
    kind = 'credit' if amount > 0 else 'payment';shown = money(abs(amount))
    ref = 'office:' + saved['id']
    if found:
        r = found[0]
        return _told(_opposite(shows), WORDS['by_absent_found'].format(row=r['cell'][1:], title=title, amount=money(_exact(r['value'])), day=day_words(r['conditions'])),
                     ['%s#%s' % (ref, r['cell'])])
    complete = [w for w in desk.live('COMPLETE') if (w.get('subject') or {}).get('sheet') == saved['id']
                and w['value']['from'] <= start and w['value']['to'] >= end]
    if complete and not unread:
        w = complete[0]
        return _told(shows, WORDS['by_complete'].format(title=title, start=day_words(w['value']['from']), end=day_words(w['value']['to'])),
                     [ref, 'word:' + w['id']], words=WORDS['absent_complete'].format(kind=kind, amount=shown, start=day_words(start), end=day_words(end)))
    seen = (day_words(min(days)), day_words(max(days))) if days else ('', '')
    said = WORDS['absent_none'].format(title=title, rows=len(rows), start=seen[0], end=seen[1], kind=kind, amount=shown)
    return _open('SHEET_COMPLETE', said + ' ' + WORDS['absent_yours'], [ref])


def _compare(desk, c):
    """A row or a calculation against a bound, exactly; with your tolerance on the cell, its whole range."""
    bound_key = 'at_most' if 'at_most' in c else 'at_least';bound = c[bound_key]
    if c.get('reading'):
        r = c['reading']
        said = [w for w in desk.live('READING') if (w.get('subject') or {}).get('sheet') == r['sheet'] and (w.get('subject') or {}).get('cell') == r['cell']
                and norm(w['value'].get('span', '')) == norm(r['span'])]
        if not said:return _open('RULE_READING', WORDS['settle_reading'].format(span=r['span']))
        reading_ref = ['word:' + said[0]['id']]
    else:
        reading_ref = []
    q = quantity(desk.kernel, desk.principal, c['of'], desk.tolerances)
    if q is None:return _open('ROW_NOT_READ', WORDS['settle_row'])
    b = _exact(bound['value']);lo = _base(q['lo'], q['unit']);hi = _base(q['hi'], q['unit']);limit = _base(b, bound['unit'])
    if not lo or not limit:return _open('CONVENTION', WORDS['settle_unit'].format(unit=q['unit'] if not lo else bound['unit']), [q['ref']])
    if lo[0] != limit[0]:return _open('CONVENTION', WORDS['settle_unit'].format(unit=q['unit']), [q['ref']])
    low, high, line = lo[1], hi[1], limit[1]
    if bound_key == 'at_most':state = HOLDS if high <= line else FAILS if low > line else UNDECIDED
    else:state = HOLDS if low >= line else FAILS if high < line else UNDECIDED
    refs = [q['ref']] + reading_ref;bound_words = _shown(b, bound['unit'])
    more = {'quantity': {'lo': str(q['lo']), 'hi': str(q['hi']), 'unit': q['unit'], 'bound': str(b), 'bound_unit': bound['unit'], 'kind': bound_key}}
    if state == UNDECIDED:
        return _open('NEW_READING', WORDS['settle_tolerance'].format(what=q['what'], low=_shown(q['lo'], q['unit']), high=_shown(q['hi'], q['unit']), bound=bound_words), refs, **more)
    value = _shown(q['lo'], q['unit']) if q['lo'] == q['hi'] else '%s to %s' % (_shown(q['lo'], q['unit']), _shown(q['hi'], q['unit']))
    if state == FAILS and bound_key == 'at_most':more['past'] = {'from': str(b), 'to': str(_in_unit(high, bound['unit'])), 'unit': bound['unit']}
    return _told(state, WORDS['by_compare'].format(what=q['what'], value=value, bound=bound_words), refs, **more)


# ---- the open point: who would settle it, and what each way would give -----------------------------------------------------

def _run(elements, assign):
    needs = [assign.get(e['id'], e['state']) for e in elements if e['part'] == 'needs']
    unless = [assign.get(e['id'], e['state']) for e in elements if e['part'] == 'unless']
    return fires(needs, unless)


def _forced(elements, open_ids, fixed):
    """The firing values over every completion of the open leaves not in `fixed`."""
    rest = [i for i in open_ids if i not in fixed]
    return {_run(elements, {**fixed, **dict(zip(rest, combo))}) for combo in product((HOLDS, FAILS), repeat=len(rest))}


def weigh(elements):
    """For the elements that cannot be told: whether each decides the conditions alone or in a pair (both ways), the sets
    that would make the conditions hold, and the single leaves that would make them not hold. Exact over every completion
    (each open leaf holds or does not); past MAX_OPEN leaves, the budget sentence."""
    open_ids = [e['id'] for e in elements if e['state'] == UNDECIDED]
    if len(open_ids) > MAX_OPEN:
        return {'decisive': {}, 'would_hold': [], 'would_not': [], 'budget': (0, len(open_ids), mt.Budget.sentence(0, len(open_ids), 'which of the open elements decide'))}
    good = {e['id']: (HOLDS if e['part'] == 'needs' else FAILS) for e in elements}
    decides = {}
    def both(fixed_ids):
        return all(len(_forced(elements, open_ids, dict(zip(fixed_ids, values)))) == 1 for values in product((HOLDS, FAILS), repeat=len(fixed_ids)))
    for i in open_ids:decides[i] = mt.ALONE if both([i]) else None
    if not any(decides.values()):
        for i, j in combinations(open_ids, 2):
            if both([i, j]):decides[i] = decides[i] or mt.PAIR;decides[j] = decides[j] or mt.PAIR
    decides = {i: d or mt.NOT_DECISIVE for i, d in decides.items()}
    would_hold = []
    for size in range(1, len(open_ids) + 1):
        for subset in combinations(open_ids, size):
            if any(set(s) <= set(subset) for s in would_hold):continue
            if _forced(elements, open_ids, {i: good[i] for i in subset}) == {HOLDS}:would_hold.append(subset)
            if len(would_hold) >= mt.BUDGET.make_hold_sets:break
        if len(would_hold) >= mt.BUDGET.make_hold_sets:break
    would_not = [(i,) for i in open_ids if HOLDS not in _forced(elements, open_ids, {i: _opposite(good[i])})]
    return {'decisive': decides, 'would_hold': would_hold, 'would_not': would_not, 'budget': (len(open_ids), len(open_ids), '')}


def open_point(rule, elements, weighed):
    """The one open point of a rule's conditions: its open elements as leaves (decisive first), and the ways that settle it."""
    order = {mt.ALONE: 0, mt.PAIR: 1, mt.NOT_DECISIVE: 2}
    leaves = []
    for e in elements:
        if e['state'] != UNDECIDED:continue
        who, kind = mt.who(e['premise'])
        leaves.append(mt.Leaf(id=e['id'], about=(rule['id'],) + tuple(e['refs']), premise=e['premise'], who=who,
                              decisive=weighed['decisive'].get(e['id'], mt.NOT_DECISIVE), values=(HOLDS, FAILS), words=e['settle']))
    leaves.sort(key=lambda leaf: order[leaf.decisive])
    good = {e['id']: (HOLDS if e['part'] == 'needs' else FAILS) for e in elements}
    ways = [mt.Way(choices=tuple((i, good[i]) for i in s), state=HOLDS, words='would make the conditions hold') for s in weighed['would_hold']]
    ways += [mt.Way(choices=((s[0], _opposite(good[s[0]])),), state=FAILS, words='would make the conditions not hold') for s in weighed['would_not']]
    who = mt.YOU if any(leaf.who == mt.YOU for leaf in leaves) else (leaves[0].who if leaves else mt.YOU)
    kind = mt.who(leaves[0].premise)[1] if leaves else mt.FACT_MISSING
    return mt.OpenPoint(about=(rule['id'],), kind=kind, who=who, leaves=tuple(leaves), outcomes=tuple(ways),
                        budget=weighed['budget'])


# ---- the card ------------------------------------------------------------------------------------------------------------------

def _limit_check(q, limit_value, limit_unit):
    """(state, room) of a quantity at most a limit: room > 0 is to spare, < 0 over by, in the limit's unit; exact."""
    lo = _base(q['lo'], q['unit']);hi = _base(q['hi'], q['unit']);line = _base(limit_value, limit_unit)
    if not lo or not line or lo[0] != line[0]:return UNDECIDED, None
    state = HOLDS if hi[1] <= line[1] else FAILS if lo[1] > line[1] else UNDECIDED
    room = (_in_unit(line[1] - hi[1], limit_unit), _in_unit(line[1] - lo[1], limit_unit))
    return state, room


def _room_words(room, unit):
    if room is None:return ''
    lo, hi = room
    if hi < 0:return WORDS['over'].format(over=_shown(-hi, unit) if lo == hi else '%s to %s' % (_shown(-hi, unit), _shown(-lo, unit)))
    if lo >= 0:return WORDS['spare'].format(spare=_shown(lo, unit) if lo == hi else '%s to %s' % (_shown(lo, unit), _shown(hi, unit)))
    return ''


def _beyond(desk, rule, past, gives_limit):
    """Past the bound a need of the rule set: the quantity judged against the row your CHOICE word names (or none), or, with
    no word, an open point with the outcome of each choice. Returns (state, words, open point or None, ways, value)."""
    from .your_word import short_name
    beyond = rule['beyond'];q = quantity(desk.kernel, desk.principal, beyond['of'], desk.tolerances)
    unit = past['unit'];start = _shown(_exact(past['from']), unit);end = _shown(_exact(past['to']), unit)
    if q is None:return UNDECIDED, [WORDS['settle_row']], None, (), None
    chosen = next((w for w in desk.live('CHOICE') if (w.get('subject') or {}).get('rule') == rule['id']), None)
    options = []
    for option in beyond['options']:
        row = _row(option['sheet'], option['cell'])
        if row:options.append((option, row))
    titles = [row['title'] for _, row in options]
    def judged(row):
        state, room = _limit_check(q, _exact(row['value']), row['unit'])
        return state, room, '%s %s' % (row['parameter'], short_name(row['title'], titles) if len(set(titles)) > 1 else ''), row
    if chosen is not None:
        if chosen['value'].get('none'):
            return HOLDS, [WORDS['beyond_chosen_none'].format(bound=start, end=end)], None, (), None
        hit = next(((o, r) for o, r in options if o['sheet'] == chosen['value']['sheet'] and o['cell'] == chosen['value']['cell']), None)
        if hit:
            state, room, _name, row = judged(hit[1])
            said = WORDS['beyond_chosen'].format(option=row['parameter'], bound=start, state=mt.STATE_WORDS[state], value=_shown(q['lo'], q['unit']),
                                                 limit=_shown(_exact(row['value']), row['unit']), room=_room_words(room, row['unit']))
            value = {'state': state, 'value': str(q['lo']), 'limit': str(_exact(row['value'])), 'unit': row['unit'], 'word': chosen['id'],
                     'over': str(-room[1]) if room and room[1] < 0 else None, 'spare': str(room[0]) if room and room[0] >= 0 else None}
            return state, [said], None, (), value
    ways = [mt.Way(choices=(('past %s' % start, 'none'),), state=HOLDS, words=WORDS['beyond_none'].format(bound=start, end=end))]
    said = [WORDS['uncovered'].format(bound=start, end=end)]
    for option, row in options:
        state, room, name, _row_ = judged(row)
        words = WORDS['beyond_option'].format(option=row['parameter'], state=mt.STATE_WORDS[state], value=_shown(q['lo'], q['unit']),
                                              limit=_shown(_exact(row['value']), row['unit']), room=_room_words(room, row['unit']))
        ways.append(mt.Way(choices=(('past %s' % start, 'office:%s#%s' % (option['sheet'], option['cell'])),), state=state,
                           room=room, unit=row['unit'], words=words))
        said.append(words)
    said.append(WORDS['beyond_none'].format(bound=start, end=end))
    leaf = mt.Leaf(id='past', about=(rule['id'],), premise='REVISION', who=mt.YOU, decisive=mt.ALONE,
                   values=('none',) + tuple('office:%s#%s' % (o['sheet'], o['cell']) for o, _ in options), words=said[0])
    point = mt.OpenPoint(about=(rule['id'],), kind=mt.AUTHORITY, who=mt.YOU, leaves=(leaf,), outcomes=tuple(ways))
    return UNDECIDED, said, point, tuple(ways), None


def evaluate(kernel, principal, rule, desk=None):
    """A rule card judged on your records as they stand: the question it answers, each element's value and what tells it,
    the conditions (needs AND NOT exceptions), the conclusion (SUPPORTED, UNKNOWN or CONFLICT, never REFUTED), the open
    points, her words, the footer, the judgement (mind_types.Judgement). Reads only; model_calls 0."""
    if isinstance(rule, str):rule = read(kernel, principal, rule)
    desk = desk or _Desk(kernel, principal)
    fresh, changed = freshness(kernel, principal, rule, desk.quote_states)
    from . import mind_words
    elements = []
    for part in PARTS:
        for e in rule.get(part) or ():
            told = tell(desk, e)
            elements.append({'id': e['id'], 'part': part, 'says': e['says'], 'source': e['source'], **told})
    title = WORDS['title'].format(rule=rule['title'])
    said = [];points = [];ways = ()
    fired = fires([e['state'] for e in elements if e['part'] == 'needs'], [e['state'] for e in elements if e['part'] == 'unless'])
    needs_state = all_of([e['state'] for e in elements if e['part'] == 'needs'])
    if fresh == STALE:
        fired = UNDECIDED
        said.append(WORDS['stale'].format(what=', '.join(changed)))
        leaf = mt.Leaf(id='recheck', about=(rule['id'],), premise='ALWAYS_ASKS', who=mt.YOU, decisive=mt.ALONE, words=said[-1])
        points.append(mt.OpenPoint(about=(rule['id'],), kind=mt.AUTHORITY, who=mt.YOU, leaves=(leaf,)))
    for e in elements:
        if e['state'] == UNDECIDED:said.append(WORDS['element_open'].format(says=e['says'], settle=e['settle']))
        elif e['state'] == CONFLICT:said.append(WORDS['conflict'].format(says=e['says']))
        else:said.append(WORDS['element'].format(says=e['says'], state=mt.STATE_WORDS[e['state']], by=e['by']))
        if e.get('words'):said.append(e['words'])
    weighed = None
    if fresh == CURRENT:
        said.append({HOLDS: WORDS['holds'], FAILS: WORDS['fails'], UNDECIDED: WORDS['open'], CONFLICT: WORDS['conflict'].format(says=rule['title'])}[fired])
        if fired == UNDECIDED:
            weighed = weigh(elements);points.append(open_point(rule, elements, weighed));ways = points[-1].outcomes
    concluded = conclusion(fired)
    gives = {'says': rule['gives'].get('says') or '', 'source': rule['gives']['source']}
    if concluded == SUPPORTED:
        bound = rule['gives']['bound']
        words = bound['words'] if 'quote' in bound else ' · '.join(x for x in (bound['row']['parameter'], ('%s %s' % (bound['row']['value'], bound['row']['unit'])).strip(), bound['row']['conditions']) if x)
        gives['words'] = words;said.append(WORDS['conclusion'].format(words=words))
        if rule['gives'].get('amount'):
            a = rule['gives']['amount'];each = _amount_of(a['bound']);total = each * a['times']
            gives['amount'] = {'each': str(each), 'times': a['times'], 'total': str(total), 'shown': money(total)}
            said.append(WORDS['amount'].format(parts=' + '.join([money(each)] * a['times']), total=money(total)))
    else:
        said.append(WORDS['no_conclusion'])
    state = fired;limit = None
    g = rule['gives']
    if fresh == CURRENT and g.get('limit') and rule.get('beyond'):
        q = quantity(kernel, principal, rule['beyond']['of'], desk.tolerances)
        cover, room = _limit_check(q, _exact(g['limit']['value']), g['limit']['unit']) if q else (UNDECIDED, None)
        limit = {'value': str(q['lo']) if q else None, 'unit': q['unit'] if q else '', 'limit': g['limit']['value'], 'limit_unit': g['limit']['unit'], 'covered': cover}
        if fired == HOLDS:
            state = cover
        else:
            past = next((e.get('past') for e in elements if e['part'] == 'needs' and e['state'] == FAILS and e.get('past')), None)
            if fired == FAILS and past:
                said.append(WORDS['covers'].format(limit=_shown(_exact(g['limit']['value']), g['limit']['unit']), rule=rule['title'], bound=_shown(_exact(past['from']), past['unit'])))
                after, words, point, more_ways, value = _beyond(desk, rule, past, g['limit'])
                said += words;state = _state(truth_and(_TO[cover], _TO[after]))
                limit.update(past=past, beyond=after, chosen=value)
                if point:points.append(point);ways = more_ways
            else:
                state = UNDECIDED if fired != CONFLICT else CONFLICT
    footer = mind_words.footer_for(rule['sort'])
    if footer:said.append(footer)
    rests = tuple(sorted({'quote:' + b['quote'] if 'quote' in b else 'office:%s#%s' % (b['row']['sheet'], b['row']['cell']) for b in _bounds(rule)}))
    proof = records.digest({'rule': rule['id'], 'revision': rule['revision'], 'elements': [[e['id'], e['state'], e['refs']] for e in elements],
                            'fresh': fresh, 'state': state, 'conclusion': concluded})
    budget = weighed['budget'] if weighed else (0, 0, '')
    judgement = mt.Judgement(about=(rule['id'],), state=state, ways=tuple(ways), open_points=tuple(points), proof=proof, rests_on=rests, budget=budget)
    return {'rule': rule['id'], 'revision': rule['revision'], 'title': title, 'sort': rule['sort'], 'freshness': fresh, 'changed': changed,
            'elements': elements, 'needs': needs_state, 'unless': any_of([e['state'] for e in elements if e['part'] == 'unless']),
            'conditions': fired, 'conclusion': concluded, 'gives': gives, 'limit': limit, 'state': state,
            'open_points': [p.as_record() for p in points], 'judgement': judgement.as_record(), 'words': said, 'footer': footer,
            'shown': SHOWN, 'model_calls': 0}


# ---- her proposal: a split read from a table row, never applied until you agree ---------------------------------------------

def propose(kernel, principal, row_ref):
    """Her proposed split of a limit row whose conditions read "Up to N unit": it needs a reading of the same kind at most
    N, gives the row's limit, and past N names the other limits of the sheet in the same unit. Writes nothing; shown as
    "mine, not agreed" until you set it."""
    from . import goals
    from .math_units import unit_spec
    row = _row(row_ref['sheet'], row_ref['cell'])
    if not row:raise ValueError('RULE_PROPOSE: that row cannot be read')
    found = re.fullmatch(r'\s*up\s+to\s+(\d+(?:\.\d+)?)\s*([A-Za-z]+)\s*', row['conditions'] or '', re.I)
    if not found:return {'proposed': None, 'agreed': False, 'words': 'I have no split to propose for that row.', 'model_calls': 0}
    value, unit = found.group(1), found.group(2)
    try:dimension = unit_spec(unit)[0];limit_dimension = unit_spec(row['unit'])[0]
    except ValueError:return {'proposed': None, 'agreed': False, 'words': WORDS['settle_unit'].format(unit=unit), 'model_calls': 0}
    head = (row['parameter'].split() or [''])[0].lower()
    def kind_of(u):
        try:return unit_spec(u)[0]
        except ValueError:return None
    measured = None;others = []
    for saved in goals._sheets():
        for r in goals._rows(saved):
            if saved['id'] == row['sheet']:
                if r['cell'] != row['cell'] and kind_of(r['unit']) == limit_dimension:others.append({'sheet': r['sheet'], 'cell': r['cell']})
            elif (measured is None and kind_of(r['unit']) == dimension and (r['parameter'].split() or [''])[0].lower() == head
                  and r['parameter'].split()[-1].lower() not in ('limit', 'ceiling', 'maximum', 'minimum')):
                measured = {'sheet': r['sheet'], 'cell': r['cell'], 'parameter': r['parameter']}
    judged = None
    for c in goals._calculations(kernel, principal):
        if kind_of(c['unit']) == limit_dimension and head in c['title'].lower().split():judged = {'calculation': c['id']};break
    if measured is None:return {'proposed': None, 'agreed': False, 'words': 'I have no reading of that kind on the desk to propose a split with.', 'model_calls': 0}
    span = row['conditions'].strip();ref = {'sheet': row['sheet'], 'cell': row['cell']}
    proposal = {'title': '%s, row %s' % (row['parameter'], row['cell'][1:]), 'sort': 'SPECIFICATION',
                'needs': [{'says': '%s is at most %s %s' % (measured['parameter'], value, unit), 'source': {'row': ref},
                           'test': {'compare': {'of': {'row': {'sheet': measured['sheet'], 'cell': measured['cell']}}, 'at_most': {'value': value, 'unit': unit},
                                                'reading': {'sheet': row['sheet'], 'cell': row['cell'], 'span': span}}}}],
                'gives': {'source': {'row': ref}, 'says': 'a %s %s %s' % (row['value'], row['unit'], row['parameter'].lower()), 'limit': {'value': row['value'], 'unit': row['unit']}}}
    if judged and others:proposal['beyond'] = {'of': judged, 'options': others}
    return {'proposed': proposal, 'agreed': False, 'words': WORDS['mine'], 'writes': 0, 'model_calls': 0}


# ---- your CHOICE word for past what a rule covers (word.set {sort: CHOICE, rule, ...}) ----------------------------------------

def beyond_word(kernel, principal, args):
    """(statement, subject, value, bound rows, identity) of your CHOICE word saying which row applies past what a rule
    covers, or that none does. Called by your_word when word.set names a rule."""
    from .your_word import _bind_row
    rule = read(kernel, principal, args['rule'])
    if not rule.get('beyond'):raise ValueError('WORD_NOT_AN_ALTERNATIVE: that rule names no rows for past what it covers')
    if args.get('none'):
        if args.get('choice') or args.get('cell'):raise ValueError('WORD_FIELDS: none, or a row; not both')
        return WORDS['choice_none'].format(rule=rule['title']), {'rule': rule['id']}, {'none': True}, [], ('CHOICE', 'rule', rule['id'])
    if not args.get('choice') or not args.get('cell'):raise ValueError('WORD_FIELDS: name the row that applies (its sheet and cell), or none')
    if {'sheet': args['choice'], 'cell': args['cell']} not in rule['beyond']['options']:
        raise ValueError('WORD_NOT_AN_ALTERNATIVE: that row is not one the rule names for past what it covers')
    saved = _saved(args['choice'])
    if not saved:raise ValueError('WORD_ROW_NOT_FOUND: that sheet cannot be read')
    row = _bind_row(saved, args['cell'])
    statement = WORDS['choice_row'].format(rule=rule['title'], parameter=row['parameter'], title=row['title'], row=row['cell'][1:])
    value = {'sheet': row['sheet'], 'cell': row['cell'], 'title': row['title'], 'parameter': row['parameter'], 'value': row['value'], 'unit': row['unit']}
    return statement, {'rule': rule['id']}, value, [row], ('CHOICE', 'rule', rule['id'])


def dispatch(kernel, op, args, principal):
    from .office_service import owner
    owner(principal)                 # the sheets a rule reads live in the owner's profile, as for office.get
    if op == 'rules.set':
        value = put(kernel, args, principal)
        return {'rule': value, 'card': evaluate(kernel, principal, value) if value.get('state') == 'IN' else None, 'model_calls': 0}
    if op == 'rules.list':
        rows = [r for r in every(kernel, principal) if args.get('all') or r.get('state') == 'IN']
        out = []
        for r in rows:
            fresh, changed = freshness(kernel, principal, r);out.append({**r, 'freshness': fresh, 'changed': changed})
        return {'rules': out, 'shown': SHOWN, 'model_calls': 0}
    if op == 'rules.get':
        with kernel.db() as db:
            records.ensure(db);value = records.read(db, KIND, args['id'], principal);history = records.history(db, value)
        return {'rule': value, 'card': evaluate(kernel, principal, value), 'history': history, 'model_calls': 0}
    if op == 'rules.check':
        if args.get('propose'):
            if args.get('id'):raise ValueError('RULE_CHECK_FIELDS: check a rule, or ask for a proposal; not both')
            return propose(kernel, principal, args['propose'])
        desk = _Desk(kernel, principal)
        rows = [read(kernel, principal, args['id'])] if args.get('id') else [r for r in every(kernel, principal) if r.get('state') == 'IN']
        return {'cards': [evaluate(kernel, principal, r, desk) for r in rows], 'model_calls': 0}
    raise ValueError('Unknown rule operation')
