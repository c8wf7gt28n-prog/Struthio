"""Her dictionary (0.8.6 S4, "Kas's mind, no model"): the owner's words read from the desk's own vocabulary, with no model.

    reading.read(text, lex, today=None, kept=(), model_loaded=False)   one reading of a request: a dict, computed, never stored
    reading.lexicon(kernel, principal, world=None)                    the desk's vocabulary (a Lexicon), read once a turn
    reading.Lexicon.of(sheets=, calculations=, goals=, typed=, passages=, world=)   the same from plain data
    reading.work(kernel, principal, found, today=None)                the answers of a reading that is a read, worked out
                                                                     exactly by the maths that already exists
    requests.read {text, today?, work?, model_loaded?}   read         the Kernel's operation over the three

How a request is read (design 3.4). The phrasebook first: a phrase the owner kept (`kept`, the phrasebook is S7). Then the
fixed dictionary of this module (the frames below, relation words, units, revision words, calendar words and the "should
I" decline) over the desk's own vocabulary: the reviewed sheets' titles and rows, each unit's dimension from math_units,
the calculations, the goals over data the desk proposes (goals.candidates), the typed sheets, the rules and dated lines of
the admitted papers, and her hand's desk goals (hand_words, the half-build's own clauses, find and revision pairing). Slots
are bound by type: an unknown that is a current binds only to a row that is a current; a limit only to a limit row.

A request is cut into clauses where a new order or question starts; each clause gives one reading, in the order said:

    route        NONE      nothing on the desk or in her dictionary carries the words: no reading, and no model is asked
                 KEPT      a phrase the owner kept, read as he kept it
                 DECLINE   "should I ...": the fixed decline, then what she can work out from the rest, read only
                 DESK      her hand's desk goals (navigation only), and what the owner said not to do (`forbid`)
                 CHECK     goals over data to judge: one, or the covering set the words fit, judged together, no question
                 SOLVE     how far one reading may go and a goal still hold (the room), under the limit the words name
                 VALUE     the rows or calculations the words name, read (every revision's row, side by side)
                 MONEY     an allowance from a typed sheet, as of a day
                 DATE      the last day of a period from a rule on the desk, for every reading of its event, earliest first
                 DAY       a day named in calendar words, when only one day fits
                 ASK       an open point that is yours (which revision, a calendar convention): a question to you
                 MEANING   licensed readings that lead to different acts, or words she could not account for: the model's
                           GOAL question when one is loaded, else buttons. Never an option set that differs only in an
                           authority (revision, tolerance, counting rule, completeness): such a set is an ASK.
                 COMPOUND  clauses of different routes, each read
    readings     one per clause, in the order said
    words        every word with what it meant; `used` False for the words she did not use (shown in grey)
    understood   the request as she understood it, in her template words (WORDS)
    open         the open points (mind_types.OpenPoint records) the reading leaves
    options      the numbered options of an ASK or MEANING point: the same options are the buttons
    elimination  where a word was read by elimination: what it was taken as, the other sense, and why the other is out
    acts         'read' or 'navigates': a reading never carries a change in 0.8.6
    model_calls  0: reading asks no model
    key          sha256 of what the reading means (not where its words stood), so two phrasings that mean the same agree

Kasandra writes nothing here: requests.read is a read, and work() calls only reads (goals.judge, math_money.answer,
math_dates.answer). Her templates (WORDS) keep clear of the banned words of design section 5; mind_words.py (lane C)
scans them once it lands. Pure Python apart from lexicon() and work(), which read the desk: no Qt, no model, no float.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from fractions import Fraction

from . import hand_words
from .desk_ops import Sheet, World
from .mind_types import AUTHORITY, MEANING, YOU, DECISION, Leaf, OpenPoint, Way, who as _who

SCHEMA = 'kas.reading/1'
ROUTES = ('NONE', 'KEPT', 'DECLINE', 'DESK', 'CHECK', 'SOLVE', 'VALUE', 'MONEY', 'DATE', 'DAY', 'ASK', 'MEANING', 'COMPOUND')
READS = ('CHECK', 'SOLVE', 'VALUE', 'MONEY', 'DATE', 'DAY')        # routes work() can answer
OPTIONS = 4                       # buttons offered for one point, before "none of these" (design 1: two to four buttons)
COVER = 4                         # the most rows or goals a covering read takes before it asks which
TEXT = 600

# Her template words for a reading (design 3.6: plain, calm, no exclamation mark, at most 30 words a sentence). Each
# {slot} is filled from the desk's own records: a title, a row, a clause, a day.
WORDS = {
    'none': 'Nothing on the desk carries these words, so I have not read them as a request for the desk.',
    'kept': 'As you kept it: {understood}',
    'check': 'Whether {statement} holds.',
    'cover': 'Whether each of these holds, judged together: {statements}.',
    'solve': 'The most {unknown} can be while {statement} still holds{under}.',
    'under': ', under {choice}',
    'value': 'The value of {rows}.',
    'money': 'How much can be spent each {per} from “{title}” and stay within its plan, as of {day}.',
    'date': 'The last day under {clause}, counted by {counting}, for each day the event may have been.',
    'date_bare': 'The last day under {clause}, with no counting rule recorded.',
    'day': '“{phrase}” is {day}.',
    'ask_day': '“{phrase}”: {options}?',
    'ask_revision': 'Which revision did you mean: {options}?',
    'meaning': 'Which of these did you mean?',
    'desk': '{statements}.',
    'forbid': 'As you said, {what}.',
    'elimination': 'No {other} is on the desk, so I read this as {taken}. If you meant {other_a}, there is none to check against.',
    'decline_legal': 'Whether to {act} is yours to decide, and a lawyer can advise you.',
    'decline_medical': "I can't advise on medicines or treatment; your pharmacist or doctor can.",
    'decline': 'That choice is yours to make.',
    'decline_then': 'Here is what I can work out from your records.',
    'unread': 'Words I did not use: {words}.',
    'card': 'read from your words · model calls: 0',
}
FORBID = {'tidy': 'I close nothing', 'traced': 'I draw no trace of “{s}”', 'shown': 'I do not select “{s}”',
          'side_by_side': 'I do not put “{a}” and “{b}” side by side', 'field': 'I leave the Field as it is'}

# -- the fixed dictionary ------------------------------------------------------------------------------------------------
STOP = frozenset('''a an the this that these those it its i me my mine we us our ours you your yours he him his she her
they them their is are was were be been being am do does did doing done have has had having can could would will may might
to of in on at by for from with about into onto as and or but if so than then there here what which who whom whose where why
how much many please kindly just now also too very really quite still yet again ever even only any anything everything
something some all each every tell let know want need give get got see look find work out figure say think one ones thing
things up lot exactly roughly currently right moment bit'''.split())
NEG = frozenset(("don't", 'dont', 'not', 'never', "doesn't", "isn't", "aren't", "can't", 'cannot', "won't", "shouldn't",
                 "mustn't", "didn't", "wasn't", 'no'))
POLITE = re.compile(r"\b(?:please|kindly|now|just|pls)\b", re.I)
ASKING = re.compile(r"^(?:(?:can|could|would|will)\s+you\s+)+", re.I)
FOR_ME = re.compile(r"\s+for\s+me$", re.I)
NEG_LEAD = re.compile(r"^(?:(?:please|and|then|also)\s+)*(?:don't|dont|do\s+not|never|no\s+need\s+to|you\s+needn't)\s+", re.I)
WEEKDAYS = ('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday')
MONTHS = ('january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december')
DIMENSIONS = {'current': 'current', 'amps': 'current', 'amp': 'current', 'amperes': 'current', 'ampere': 'current',
              'milliamps': 'current', 'milliamp': 'current', 'milliamperes': 'current', 'milliampere': 'current',
              'voltage': 'voltage', 'volts': 'voltage', 'volt': 'voltage', 'millivolts': 'voltage', 'power': 'power',
              'watts': 'power', 'watt': 'power', 'milliwatts': 'power', 'wattage': 'power', 'time': 'time',
              'duration': 'time', 'long': 'time', 'milliseconds': 'time', 'millisecond': 'time', 'seconds': 'time'}
UNIT_WORDS = {'milliamps': 'mA', 'milliamp': 'mA', 'milliamperes': 'mA', 'milliampere': 'mA', 'ma': 'mA', 'amps': 'A',
              'amp': 'A', 'amperes': 'A', 'ampere': 'A', 'volts': 'V', 'volt': 'V', 'millivolts': 'mV', 'mv': 'mV',
              'watts': 'W', 'watt': 'W', 'milliwatts': 'mW', 'mw': 'mW', 'milliseconds': 'ms', 'millisecond': 'ms',
              'ms': 'ms', 'seconds': 's', 'second': 's'}
UNIT_DIMENSION = {'mA': 'current', 'A': 'current', 'V': 'voltage', 'mV': 'voltage', 'W': 'power', 'mW': 'power',
                  'ms': 'time', 's': 'time'}
UNIT_SCALE = {'mA': Fraction(1, 1000), 'A': Fraction(1), 'V': Fraction(1), 'mV': Fraction(1, 1000), 'W': Fraction(1),
              'mW': Fraction(1, 1000), 'ms': Fraction(1, 1000), 's': Fraction(1)}
LIMIT_WORDS = frozenset(('limit', 'limits', 'ceiling', 'ceilings', 'maximum', 'max', 'minimum', 'min', 'floor'))
HELPERS = frozenset(('stay', 'stays', 'keep', 'keeps', 'remain', 'remains', 'go', 'goes', 'be', 'get', 'rise', 'run', 'draw',
                     'take', 'takes', 'reach', 'push', 'allowed', 'allow'))
REVISION_WORDS = frozenset(('rev', 'revision', 'revisions', 'version', 'archived', 'older', 'old', 'previous', 'earlier',
                            'latest', 'newest', 'newer', 'new', 'marked'))
# the relation words (typed_pipeline.WORDS and goals.LIMIT_WORDS in the owner's speech) -> le or ge
RELATION = re.compile(r"\b(?P<neg>(?:don't|do\s+not|not|never|without)\s+(?:\w+\s+)?)?(?P<word>at\s+most|at\s+least|no\s+more\s+than|"
                      r"no\s+less\s+than|less\s+than|more\s+than|under|below|beneath|within|inside|over|above|exceed(?:s|ing)?|beyond|"
                      r"up\s+to)\b", re.I)
RELATION_OP = {'at most': 'le', 'no more than': 'le', 'less than': 'le', 'under': 'le', 'below': 'le', 'beneath': 'le',
               'within': 'le', 'inside': 'le', 'up to': 'le', 'at least': 'ge', 'no less than': 'ge', 'more than': 'ge',
               'over': 'ge', 'above': 'ge', 'exceed': 'ge', 'exceeds': 'ge', 'exceeding': 'ge', 'beyond': 'ge'}
RELATION_SAID = {'le': 'at most', 'ge': 'at least'}
CHECK = re.compile(r"\b(?:ok|okay|fine|alright|all\s+right|good|pass(?:es|ing)?|holds?|hold\s+up|in\s+spec|meets?|"
                   r"compl(?:y|ies)|too\s+(?:high|long|much|big|low)|(?:within|under|over|inside|below|above|exceeds?|beyond)\s+"
                   r"(?:the\s+|its\s+)?(?:\w+\s+){0,3}?(?:limits?|ceilings?|spec))\b", re.I)
QUESTION = re.compile(r"^(?:is|are|does|do|did|will|was|were|has|have)\b", re.I)
SOLVE = re.compile(r"\bhow\s+(?:much|many|far|high|low|long|big|large|small)\b|\b(?:what(?:'s|\s+is)|which\s+is)\s+the\s+"
                   r"(?:most|least|highest|lowest|largest|smallest|maximum|minimum|max|min)\b|\bup\s+to\s+what\b", re.I)
VALUE = re.compile(r"\b(?:what(?:'s|\s+is|\s+are|\s+was)|how\s+(?:much|many|long|high|big)\s+(?:is|are|was|does|do)|"
                   r"tell\s+me|read\s+me|give\s+me|value\s+of)\b", re.I)
MONEY = re.compile(r"\b(?:spend|spending|spent|afford|budget|allowance|save|saving)\b", re.I)
PER = re.compile(r"\b(?:(?:each|per|a|every|the)\s+(?P<per>day|week|month)|(?P<ly>daily|weekly|monthly))\b", re.I)
DATE = re.compile(r"\b(?:when|what\s+date|which\s+day|what\s+day|last\s+day|deadline|due|by\s+when|how\s+long\s+(?:do|does|has|have))\b", re.I)
DATE_WORDS = frozenset(('when', 'date', 'day', 'days', 'last', 'deadline', 'due', 'until', 'long'))
CALENDAR = re.compile(r"\b(?:(?P<which>next|this|coming|last)\s+(?P<wd>monday|tuesday|wednesday|thursday|friday|saturday|sunday)|"
                      r"(?P<rel>today|tomorrow|yesterday)|in\s+(?P<n>\d{1,3})\s+days?|"
                      r"(?:on\s+)?(?P<bare>monday|tuesday|wednesday|thursday|friday|saturday|sunday))\b", re.I)
SHOULD = re.compile(r"\b(?:should|shall|ought|must)\s+(?:i|we)\b|\b(?:i|we)\s+(?:should|ought\s+to)\b|\b(?:do|would)\s+you\s+"
                    r"(?:think|advise|recommend|suggest)\b|\bwhat\s+would\s+you\s+do\b|\bis\s+it\s+(?:wise|worth|a\s+good\s+idea|"
                    r"better|best)\b|\b(?:do|does|would)\s+(?:i|we)\s+(?:have|need)\s+to\b|\b(?:am\s+i|are\s+we)\s+better\s+off\b|"
                    r"\bwould\s+it\s+be\s+(?:wise|better|best)\b|\bwhat\s+(?:should|shall)\b|\bwhich\s+(?:should|shall)\s+(?:i|we)\b", re.I)
MEDICAL = re.compile(r"\b(?:medicines?|medications?|doses?|dosage|tablets?|pills?|treatments?|prescriptions?|drugs?|doctor|"
                     r"pharmacist|symptoms?|mg|antibiotics?|inhaler|insulin|painkillers?|ibuprofen|paracetamol)\b", re.I)
LEGAL = re.compile(r"\b(?:sue|suing|claim|court|tribunal|lawyer|solicitor|legal|law|act|statute|contract|lease|landlord|tenant|"
                   r"tenancy|deposit|complain|complaint|withhold|evict|eviction|agent|notice)\b", re.I)
CLAIM = re.compile(r"\b(?:sue|suing|claim|court|tribunal)\b", re.I)
SPLIT_START = (hand_words.STARTS[3:-1] + r"|is|are|does|do|did|will|how|what|what's|when|which|can|could|tell|give|check|"
               r"find|work|don't|never|should|shall")
SPLIT = re.compile(r"\s*(?:;|,\s*(?:and\s+|then\s+)*|\band\s+then\b|\band\b|\bthen\b)\s*(?=(?:(?:please|also|then)\s+)*(?:"
                   + SPLIT_START + r")\b)", re.I)
TOKEN = re.compile(r"§\s*\d+(?:\s*\([a-z]\))?|\d+(?:[.,]\d+)*|[A-Za-z]+(?:'[A-Za-z]+)?")
REVISION_TITLE = re.compile(r'^(?P<stem>.*?)\s*\brev(?:ision)?\.?\s*(?P<rev>[A-Za-z0-9]{1,3})\b', re.I)   # field_page's rule
# the papers: a rule's sections, a period after an event, the counting rules, and dated lines
SECTION = re.compile(r'§\s*(\d{1,4})\.\s*')
PERIOD = re.compile(r'\b[Ww]ithin\s+(\d{1,4})\s+days?\s+after\s+([^,.;]{3,80})')
DATED = re.compile(r"([A-Za-z][A-Za-z ,'-]{1,80}?):\s*(?:(?:Mon|Tues|Wednes|Thurs|Fri|Satur|Sun)day\s+)?(\d{4}-\d{2}-\d{2})\b")
ENDS = re.compile(r"\b(?:ends?|ended|ending|returned|handed\s+back|moved\s+out|vacated|terminated|finished)\b", re.I)


def plain(text):
    return re.sub(r'\s+', ' ', str(text or '').replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"')).strip()


def stem(word):
    """One word's stem, so that settle, settled and settling, or grocery and groceries, are one."""
    w = word.lower()
    if not w.isalpha():return w
    for suffix in ('ings', 'ing', 'ies', 'ied', 'ed', 'es', 's', 'e', 'y'):
        if w.endswith(suffix) and len(w) - len(suffix) >= 4:return w[:-len(suffix)]
    return w


def stems(text):
    return frozenset(stem(w) for w in re.findall(r"[A-Za-z]+|\d+", str(text or '')) if w.lower() not in STOP)


@dataclass(frozen=True)
class Tok:
    i: int
    text: str
    low: str
    stem: str
    at: tuple


def tokens(text):
    out = []
    for m in TOKEN.finditer(text):
        raw = m.group(0);low = raw.lower()
        if low not in NEG and "'" in low:low = low.split("'")[0]           # the rail's, what's, it's: the word itself
        out.append(Tok(len(out), raw, low, stem(low), (m.start(), m.end())))
    return out


# -- the desk's vocabulary -------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Row:
    sheet: str
    title: str
    cell: str
    parameter: str
    value: str
    unit: str
    conditions: str
    dimension: str
    limit: object          # (stem, relation) for a limit row, else None
    stems: frozenset
    rev: str
    mark: str

    def ref(self):return {'sheet': self.sheet, 'title': self.title, 'cell': self.cell, 'parameter': self.parameter}

    def said(self):return '%s, %s %s (%s %s)' % (self.parameter, self.value, self.unit, self.title, self.cell)


def _dimension(unit):
    """The dimension's name of a unit as a sheet holds it ('mA' -> 'current'); '' when it is not a unit of the maths."""
    from .math_units import unit_spec, dimension_name
    try:
        from .math_answers import cell_unit
        return dimension_name(unit_spec(cell_unit(unit)[0])[0])
    except Exception:          # a unit the maths does not read is no dimension here: the row is still a word
        return ''


def _mark(title):
    m = REVISION_TITLE.match(title or '')
    mark = 'CURRENT' if re.search(r'\bCURRENT\b', title or '') else 'ARCHIVED' if re.search(r'\bARCHIVED\b', title or '') else ''
    return (m['rev'].upper() if m else ''), mark, (m['stem'].strip() if m else '')


def world_of(titles):
    """Her hand's World from sheet titles alone: two sheets are revisions of one when their titles match once the revision
    mark is taken off (field_page.revision_sibling's rule, read here without the window)."""
    marks = {t: REVISION_TITLE.match(t) for t in titles};out = []
    for t in titles:
        m = marks[t];sibling = None;older = False
        if m:
            for o in titles:
                n = marks[o]
                if o != t and n and n['stem'].strip().casefold() == m['stem'].strip().casefold() and n['rev'].casefold() != m['rev'].casefold():
                    sibling = o;older = (len(m['rev']), m['rev'].upper()) < (len(n['rev']), n['rev'].upper());break
        out.append(Sheet(t, 'sheet', sibling, older))
    return World(tuple(out))


def _sentence(text):
    text = plain(text);found = re.match(r'(.+?\.)(?:\s|$)', text)
    return found.group(1) if found else text


def papers(passages):
    """The rules and dated lines of the admitted papers: (periods, counting, events). A period is a subsection that says
    "within N days after <event>"; the counting rules are the subsections that say the day of the event is not counted,
    that a last day on a weekend or a holiday moves on, and which days are holidays; a dated line is "<label>: <day>"."""
    periods, counting, events, seen = [], {}, [], set()
    for passage in passages:
        text = plain(passage.get('text'));name = passage.get('name') or ''
        marks = list(SECTION.finditer(text))
        for n, m in enumerate(marks):
            body = text[m.end():marks[n + 1].start() if n + 1 < len(marks) else len(text)]
            first = re.search(r'\(a\)\s', body)
            heading = _sentence(body[:first.start()] if first else body)
            subs, at, letter = [], first.start() if first else -1, 'a'
            while at >= 0:
                nxt = re.search(r'\(%s\)\s' % chr(ord(letter) + 1), body[at + 3:])
                end = at + 3 + nxt.start() if nxt else len(body)
                subs.append((letter, _sentence(body[at + 3:end])))
                at = end if nxt else -1;letter = chr(ord(letter) + 1)
            for letter, words in subs:
                clause = '§ %s(%s)' % (m.group(1), letter);low = words.lower()
                found = PERIOD.search(words)
                if found and clause not in seen:
                    seen.add(clause)
                    periods.append({'clause': clause, 'words': words, 'count': int(found.group(1)), 'event': found.group(2).strip(),
                                    'heading': heading, 'source': name, 'stems': sorted(stems(words) | stems(heading))})
                if 'does not count the day' in low or 'day of the event' in low:counting.setdefault('count_clause', {'clause': clause, 'words': words})
                if 'falls on' in low and 'next day' in low:
                    skips = [s for s, w in (('saturday', 'saturday'), ('sunday', 'sunday'), ('holidays', 'holiday')) if w in low]
                    if skips:counting.setdefault('roll', {'clause': clause, 'words': words, 'skips': skips})
                if 'holidays are' in low:
                    days = ['%02d-%02d' % (MONTHS.index(mo.lower()) + 1, int(d)) for d, mo in re.findall(r'(\d{1,2})\s+(%s)' % '|'.join(MONTHS), words, re.I)]
                    if days:counting.setdefault('holiday_clause', {'clause': clause, 'words': words});counting.setdefault('yearly', days)
        lines = [line for line in str(passage.get('text') or '').splitlines() if line.strip()] or [text]
        for line in lines:
            for label, day in DATED.findall(line):
                words = label.split()
                while words and len(words) > 1 and words[0].isupper() and len(words[0]) > 1:words.pop(0)     # a notice in capitals
                label = ' '.join(words[-6:]).strip(' ,-')
                try:date.fromisoformat(day)
                except ValueError:continue
                if label and (label, day) not in {(e['label'], e['day']) for e in events}:
                    events.append({'label': label, 'day': day, 'source': name, 'ends': bool(ENDS.search(label))})
    return periods, counting, events


@dataclass
class Lexicon:
    """The desk's vocabulary for her dictionary: everything read() matches words against, gathered once."""
    rows: tuple = ()
    calculations: tuple = ()
    goals: tuple = ()
    typed: tuple = ()
    periods: tuple = ()
    counting: dict = field(default_factory=dict)
    events: tuple = ()
    world: World = field(default_factory=World)
    sheets: dict = field(default_factory=dict)
    known: frozenset = frozenset()
    digest: str = ''

    @classmethod
    def of(cls, sheets=(), calculations=(), goals=(), typed=(), passages=(), world=None):
        """sheets: [{'id', 'title', 'rows': [{'cell', 'parameter', 'value', 'unit', 'conditions'}]}] (reviewed sheets);
        calculations: [{'id', 'title', 'unit', 'expression', 'sheet'}]; goals: goals.candidates(); typed: [{'id', 'title',
        'rows': [[cell text, ...], ...] (the heading row first)}]; passages: [{'name', 'text'}] (admitted papers)."""
        from .goals import _limit
        rows, marks = [], {}
        for s in sheets:
            rev, mark, base = _mark(s['title']);marks[s['id']] = {'title': s['title'], 'rev': rev, 'mark': mark, 'stem': base}
            for r in s.get('rows') or ():
                if not r.get('parameter'):continue
                rows.append(Row(s['id'], s['title'], r['cell'], r['parameter'], str(r.get('value') or ''), str(r.get('unit') or ''),
                                str(r.get('conditions') or ''), _dimension(r.get('unit') or ''), _limit(r['parameter']),
                                stems(r['parameter']), rev, mark))
        calcs = tuple({**c, 'dimension': _dimension(c.get('unit') or ''), 'stems': stems(re.sub(r'^\s*\S+\s+Demo\s+', '', c.get('title') or ''))}
                      for c in calculations)
        enriched = []
        for g in goals:
            subject = g['statement'].split(' is ')[0]
            limit = next((s for s, role in (g.get('roles') or {}).items() if role == 'limit'), None)
            measured = {(c['sheet'], c['cell']) for s, c in g['cells'].items() if s != limit}
            alternatives = (g.get('alternatives') or {}).get(limit) or [g['cells'][limit]]
            cell_stems = frozenset().union(*[stems(c['parameter']) for s, c in g['cells'].items() if s != limit])
            title_stems = frozenset().union(*[stems(c['title']) for c in g['cells'].values()])
            limit_dim = next((r.dimension for r in rows if (r.sheet, r.cell) == (alternatives[0]['sheet'], alternatives[0]['cell'])), '')
            enriched.append({**g, '_subject': subject, '_stems': stems(subject), '_cells': cell_stems, '_titles': title_stems,
                             '_limit': limit, '_limit_stems': stems(g['cells'][limit]['parameter']), '_measured': measured,
                             '_alternatives': alternatives, '_limit_dim': limit_dim})
        kinds = []
        for t in typed:
            grid = [list(r) for r in t.get('rows') or ()]
            if not grid:continue
            head = [str(h).strip() for h in grid[0]];items = {}
            for r in grid[1:]:
                if r and str(r[0]).strip():items[str(r[0]).strip()] = {head[i] if i < len(head) else str(i): str(v).strip() for i, v in enumerate(r)}
            kinds.append({'id': t['id'], 'title': t['title'], 'stems': stems(t['title']), 'items': items, 'head': head,
                          'item_stems': {name: stems(name) for name in items}})
        periods, counting, events = papers(passages)
        titles = tuple(dict.fromkeys([s['title'] for s in sheets] + [t['title'] for t in typed]))
        known = set()
        for r in rows:known |= r.stems | stems(r.title)
        for c in calcs:known |= c['stems']
        for t in kinds:known |= t['stems'];[known.update(v) for v in t['item_stems'].values()]
        for p in periods:known |= set(p['stems'])
        part = {'sheets': [(s['id'], s['title'], [(r.get('cell'), r.get('parameter'), r.get('value'), r.get('unit')) for r in s.get('rows') or ()]) for s in sheets],
                'calculations': [(c.get('id'), c.get('title'), c.get('unit')) for c in calculations], 'goals': [g.get('key') for g in goals],
                'typed': [(t['id'], t['title'], t.get('rows')) for t in typed], 'periods': periods, 'counting': counting, 'events': events}
        digest = hashlib.sha256(json.dumps(part, sort_keys=True, ensure_ascii=False, default=str).encode('utf-8')).hexdigest()
        return cls(tuple(rows), calcs, tuple(enriched), tuple(kinds), tuple(periods), counting, tuple(events),
                   world if world is not None else world_of(titles), marks, frozenset(known), digest)

    def sheet_words(self, sheet):
        m = self.sheets.get(sheet) or {}
        if not m.get('rev'):return '“%s”' % m.get('title', sheet)
        return 'Rev %s%s' % (m['rev'], ' (marked current)' if m.get('mark') == 'CURRENT' else ' (marked archived)' if m.get('mark') == 'ARCHIVED' else '')


# -- one clause ------------------------------------------------------------------------------------------------------------
@dataclass
class Clause:
    text: str
    toks: list
    low: str = ''
    used: dict = field(default_factory=dict)       # token index -> what it meant
    negated: bool = False
    base: int = 0                                  # where the clause's text starts in the request (tokens' places are the request's)

    def content(self):
        return [t for t in self.toks if t.low not in STOP and t.low not in NEG]

    def use(self, tok, meant):
        if tok.i not in self.used:self.used[tok.i] = meant

    def use_span(self, start, end, meant):
        """Mark the tokens between two places of the clause's own text."""
        for t in self.toks:
            if t.at[0] >= start + self.base and t.at[1] <= end + self.base:self.use(t, meant)

    def unread(self):
        return [t for t in self.content() if t.i not in self.used]


def _clean(text):
    """The clause as her hand's patterns want it: no courtesy words, no "can you", no "for me"."""
    text = POLITE.sub(' ', text);text = re.sub(r'\s+', ' ', text).strip(' ,;')
    text = ASKING.sub('', text);text = FOR_ME.sub('', text)
    return hand_words.plain(text)


def _cut(text, toks):
    """The clauses of a request, each with its own tokens (their places are the request's)."""
    clauses, start = [], 0
    for m in SPLIT.finditer(text):
        clauses.append((start, m.start()));start = m.end()
    clauses.append((start, len(text)))
    out = []
    for a, b in clauses:
        piece = text[a:b].strip(' ,;.?!');lead = len(text[a:b]) - len(text[a:b].lstrip(' ,;.?!'))
        own = [t for t in toks if t.at[0] >= a and t.at[1] <= b]
        if not piece or all(t.low in STOP for t in own):continue          # "Please," alone is courtesy, not a clause
        out.append(Clause(piece, own, piece.lower(), base=a + lead))
    return out


def _option(n, words, found, kind='read'):
    return {'n': n, 'words': words, 'reading': found, 'kind': kind, 'authority_free': authority_free(found)}


def authority_free(found):
    """What an option means with every authority taken out: the revision chosen (and a sheet's revision mark in a title),
    a tolerance, a counting rule, completeness. Two options with the same value differ only in an authority."""
    def strip(value):
        if isinstance(value, dict):
            return {k: strip(v) for k, v in value.items() if k not in ('choose', 'choice', 'choice_words', 'tolerance', 'counting', 'complete', 'n', 'words')}
        if isinstance(value, (list, tuple)):return [strip(v) for v in value]
        if isinstance(value, str):
            m = REVISION_TITLE.match(value)
            return m['stem'].strip().casefold() if m else value
        return value
    return hashlib.sha256(json.dumps(strip(found), sort_keys=True, ensure_ascii=False, default=str).encode('utf-8')).hexdigest()[:16]


def only_authority(options):
    """Whether two of these options differ only in an authority: such a set is never sent to the model (design 6.2, S4)."""
    keys = [o['authority_free'] for o in options]
    return len(set(keys)) != len(keys)


def _collapse(group, start=0):
    """Options that differ only in an authority made one: (options, revision_only). When every option is the same once the
    authorities are taken out, the point is yours (which revision), and the options stay as they are for your buttons;
    otherwise each such set is one option whose revision stays open, so no set the model sees differs only in an authority."""
    keys = {}
    for o in group:keys.setdefault(o['authority_free'], []).append(o)
    if len(group) > 1 and len(keys) == 1:return group, True
    out = []
    for same in keys.values():
        first = dict(same[0])
        if len(same) > 1:
            words = first['words']
            for o in same:
                for title in re.findall(r'“([^”]+)”', o['words']):
                    m = REVISION_TITLE.match(title)
                    if m:words = words.replace('“%s”' % title, '“%s”' % m['stem'].strip())
            first['words'] = words + ' (which revision is yours to say)'
            first['reading'] = {**first['reading'], 'revision_open': [o['reading'] for o in same]}
        out.append(first)
    for n, o in enumerate(out):o['n'] = start + n + 1
    if only_authority(out):return group, True          # never reached: kept so that the rule holds by the code itself
    return out, False


# -- the frames ----------------------------------------------------------------------------------------------------------------
def _desk(cl, lex, last):
    """Her hand's desk goals for a clause (hand_words' patterns), or what the owner said not to do."""
    text = _clean(cl.text);neg = NEG_LEAD.match(text)
    if neg:text = text[neg.end():]
    if re.fullmatch(r"(?:close|put away|clear|shut)\s+(?:anything|everything|all|it all|all of it|every\s*thing|the menus?|"
                    r"what you opened|what is open|what's open|whatever is open)|tidy(?:\s+up)?(?:\s+the\s+desk)?", text, re.I):
        template, params = 'tidy', {}
    else:
        template, params = hand_words._clause(text, lex.world, last)
    if template is None:
        why = params or ('no pattern', text, [])
        if why[0] == 'ambiguous' and why[2]:return {'_ambiguous': (why[1], list(why[2]), neg is not None)}
        return None
    cl.use_span(0, 10 ** 6, 'an order for her hand on the desk')
    for t in cl.toks:
        if t.low in NEG:cl.used[t.i] = 'not'
    goal = hand_words.G.make(template, params, 1)
    if neg:
        cl.negated = True
        return {'frame': 'DESK', 'route': 'DESK', 'goals': [], 'forbid': [{'template': template, 'params': dict(params), 'statement': goal.statement}]}
    return {'frame': 'DESK', 'route': 'DESK', 'goals': [{'template': template, 'params': dict(params), 'statement': goal.statement}], 'forbid': []}


def _revisions(cl, lex, sheets):
    """The revisions a clause names among `sheets` (sheet ids): (chosen ids, the tokens used, 'both' when "current" may
    also be a dimension)."""
    toks = cl.toks;chosen, used = [], []
    for n, t in enumerate(toks):
        nxt = toks[n + 1].low if n + 1 < len(toks) else ''
        if t.low in ('rev', 'revision') and nxt and re.fullmatch(r'[a-z0-9]{1,3}', nxt):
            want = nxt.upper();chosen += [s for s in sheets if lex.sheets.get(s, {}).get('rev') == want];used += [t, toks[n + 1]]
        elif t.low in ('archived', 'older', 'old', 'previous', 'earlier'):
            found = [s for s in sheets if lex.sheets.get(s, {}).get('mark') == 'ARCHIVED'] if t.low == 'archived' else \
                    sorted(sheets, key=lambda s: (len(lex.sheets.get(s, {}).get('rev', '')), lex.sheets.get(s, {}).get('rev', '')))[:1]
            chosen += found;used.append(t)
        elif t.low in ('latest', 'newest', 'newer'):
            chosen += sorted(sheets, key=lambda s: (len(lex.sheets.get(s, {}).get('rev', '')), lex.sheets.get(s, {}).get('rev', '')))[-1:];used.append(t)
    return list(dict.fromkeys(chosen)), used


def _current_sense(cl, n):
    """'revision', 'dimension' or 'both' for the word "current" at token n."""
    toks = cl.toks;nxt = toks[n + 1].low if n + 1 < len(toks) else ''
    prev = toks[n - 1].low if n else ''
    if nxt in ('revision', 'rev', 'version', 'sheet', 'one', 'limits', 'sheets'):return 'revision' if nxt != 'limits' else 'both'
    if nxt in LIMIT_WORDS and prev in ('the', 'its', 'our', 'my', 'under', 'below', 'within', 'over', 'above', 'than'):return 'both'
    if prev == 'marked':return 'revision'
    return 'dimension'


def _limit_choice(cl, lex, related, after):
    """Which limit the words after the relation name, for goals `related`: (goals, choose, elimination, open) where open
    is an options list when the words fit two different limits."""
    limit_toks = [t for t in cl.toks if t.at[0] >= after and t.low not in STOP]
    words = [t for t in limit_toks if t.low not in LIMIT_WORDS and t.low not in REVISION_WORDS and t.low != 'current' and t.low not in NEG]
    for t in limit_toks:
        if t.low in LIMIT_WORDS:cl.use(t, 'a limit')
    goals = related
    named = [t for t in words if any(t.stem in g['_limit_stems'] for g in related)]
    if named:
        goals = [g for g in related if all(t.stem in g['_limit_stems'] for t in named)] or related
        for t in named:cl.use(t, 'the limit: %s' % goals[0]['cells'][goals[0]['_limit']]['parameter'])
    sheets = sorted({a['sheet'] for g in goals for a in g['_alternatives']})
    choose, used = _revisions(cl, lex, sheets)
    for t in used:cl.use(t, 'the revision: %s' % ', '.join(lex.sheet_words(s) for s in choose) if choose else 'a revision')
    elimination = None
    for t in limit_toks:
        if t.low != 'current':continue
        n = cl.toks.index(t);sense = _current_sense(cl, n)
        amps = [g for g in goals if g['_limit_dim'] == 'current']
        marked = [s for s in sheets if lex.sheets.get(s, {}).get('mark') == 'CURRENT']
        if sense == 'revision' or (sense == 'both' and marked and not amps):
            if not marked:return goals, choose, None, {'none': 'no revision on the desk is marked current'}
            choose = list(dict.fromkeys(choose + marked));goals = [g for g in goals if g['_limit_dim'] != 'current'] or goals
            g = goals[0];alt = next((a for a in g['_alternatives'] if a['sheet'] in marked), g['_alternatives'][0])
            row = next((r for r in lex.rows if (r.sheet, r.cell) == (alt['sheet'], alt['cell'])), None)
            taken = "the current revision's limit: Rev %s's %s, %s %s" % (lex.sheets[alt['sheet']]['rev'], alt['parameter'][:1].lower() + alt['parameter'][1:],
                                                                         row.value if row else '', row.unit if row else '')
            cl.use(t, "the current revision" + (' (by elimination)' if sense == 'both' else ''))
            if sense == 'both':
                elimination = {'word': 'current', 'taken': taken.strip(), 'other': 'limit in amps', 'other_a': 'a limit in amps',
                               'why': 'No limit in amps is on the desk',
                               'said': WORDS['elimination'].format(other='limit in amps', taken=taken.strip(), other_a='a limit in amps')}
        elif sense == 'both' and amps and not marked:
            goals = amps;cl.use(t, 'a limit in amps (by elimination)')
            elimination = {'word': 'current', 'taken': 'a limit in amps', 'other': 'revision marked current', 'other_a': 'the current revision',
                           'why': 'No revision on the desk is marked current',
                           'said': WORDS['elimination'].format(other='revision marked current', taken='a limit in amps', other_a='the current revision')}
        elif sense == 'both' and amps and marked:
            return goals, choose, None, {'both': [g for g in amps] + [g for g in goals if g not in amps]}
        else:
            cl.use(t, 'a current')
    return goals, choose, elimination, None


def _relation(cl):
    m = RELATION.search(cl.text)
    if not m:return None
    op = RELATION_OP[re.sub(r'\s+', ' ', m.group('word').lower())]
    if m.group('neg'):op = {'le': 'ge', 'ge': 'le'}[op] if m.group('word').lower() not in ('within', 'inside', 'under', 'below') else op
    cl.use_span(m.start(), m.end(), RELATION_SAID[op])
    for t in cl.toks:
        if t.low in HELPERS and t.at[1] <= m.end() + cl.base:cl.use(t, 'stays')
    return op, m.end() + cl.base               # a place in the request, as the tokens' are


def _measured(lex, goals):
    keys = set()
    for g in goals:keys |= g['_measured']
    return [r for r in lex.rows if (r.sheet, r.cell) in keys]


def _solve(cl, lex):
    """How far one reading may go and a goal still hold: "How much current can the rail settle at and stay under the
    current limit?"."""
    m = SOLVE.search(cl.text)
    if not m or not lex.goals:return None
    rel = _relation(cl)
    if rel is None:return None
    op, after = rel;cl.use_span(m.start(), m.end(), 'how much: the unknown')
    dim, unit = '', ''
    head = [t for t in cl.toks if m.end() + cl.base <= t.at[0] < after]
    for t in head[:2]:
        if t.low in UNIT_WORDS:unit = UNIT_WORDS[t.low];dim = UNIT_DIMENSION[unit];cl.use(t, 'in %s' % unit)
        elif t.low in DIMENSIONS and not dim:dim = DIMENSIONS[t.low];cl.use(t, 'a %s' % dim if dim != 'time' else 'a time')
    for n, t in enumerate(cl.toks):
        if t.low == 'in' and n + 1 < len(cl.toks) and cl.toks[n + 1].low in UNIT_WORDS:
            unit = UNIT_WORDS[cl.toks[n + 1].low];cl.use(cl.toks[n + 1], 'in %s' % unit);dim = dim or UNIT_DIMENSION[unit]
    rows = [r for r in _measured(lex, lex.goals) if not dim or r.dimension == dim]
    words = [t for t in head if t.i not in cl.used and t.low not in STOP]
    def fit(r):return sum(1 for t in words if t.stem in r.stems)
    best = max((fit(r) for r in rows), default=0)
    picked = [r for r in rows if fit(r) == best]
    if not picked or len(picked) > COVER:return None
    if len(picked) > 1:
        return {'frame': 'SOLVE', 'route': 'MEANING', '_options': [('The most %s can be' % r.parameter, {'frame': 'SOLVE', 'unknown': r.ref()}) for r in picked]}
    row = picked[0]
    for t in words:
        if t.stem in row.stems:cl.use(t, row.said())
    related = [g for g in lex.goals if (row.sheet, row.cell) in g['_measured'] and (g['relation'] in ('le', 'lt')) == (op == 'le')]
    if not related:return None
    goals, choose, elimination, both = _limit_choice(cl, lex, related, after)
    if both is not None:
        if 'none' in both:return None
        opts = [('%s, %s' % (g['statement'], 'a limit in amps' if g['_limit_dim'] == 'current' else 'under the current revision'),
                 {'frame': 'SOLVE', 'goal': g['key']}) for g in both['both']]
        return {'frame': 'SOLVE', 'route': 'MEANING', '_options': opts}
    for t in cl.toks:          # the other rows of the goal the words name ("the rail" is Rail voltage)
        if t.i in cl.used or t.low in STOP:continue
        for g in goals:
            hit = next((r for r in _measured(lex, [g]) if t.stem in r.stems), None)
            if hit:cl.use(t, hit.said());break
    found = {'frame': 'SOLVE', 'route': 'SOLVE', 'stage': 'room', 'relation': op,
             'goals': [{'key': g['key'], 'statement': g['statement']} for g in goals],
             'unknown': {**row.ref(), 'symbol': next(s for s, c in goals[0]['cells'].items() if (c['sheet'], c['cell']) == (row.sheet, row.cell)),
                         'unit': row.unit}, 'unit': unit or row.unit,
             'choose': choose, 'choice_words': ', '.join(lex.sheet_words(s) for s in choose)}
    if elimination:found['elimination'] = elimination
    return found


def _goal_tiers(words, goals):
    """The goals a subject fits: those whose subject holds every word; else whose rows do; else whose sheets' titles do."""
    if not words:return []
    for key in ('_stems', '_cells', '_titles'):
        hit = [g for g in goals if all(t.stem in g[key] for t in words)]
        if hit:return hit
    return []


def _check(cl, lex):
    """Goals over data to judge: "is startup ok?" judges every goal its subject fits, together (a covering answer)."""
    m = CHECK.search(cl.text)
    rel = RELATION.search(cl.text) if QUESTION.match(cl.text) else None
    if not (m or rel) or not lex.goals:return None
    if m:cl.use_span(m.start(), m.end(), 'a check: does it hold')
    if rel:cl.use_span(rel.start(), rel.end(), 'a check: %s' % RELATION_SAID[RELATION_OP.get(re.sub(r'\s+', ' ', rel.group('word').lower()), 'le')])
    for t in cl.toks:
        if t.low in LIMIT_WORDS:cl.use(t, 'a limit')
    sheets = sorted({a['sheet'] for g in lex.goals for a in g['_alternatives']})
    choose, used = _revisions(cl, lex, sheets)
    for t in used:cl.use(t, 'the revision: %s' % ', '.join(lex.sheet_words(s) for s in choose))
    for n, t in enumerate(cl.toks):
        if t.low == 'current' and _current_sense(cl, n) == 'revision':
            marked = [s for s in sheets if lex.sheets.get(s, {}).get('mark') == 'CURRENT']
            if marked:choose = list(dict.fromkeys(choose + marked));cl.use(t, 'the current revision')
    words = [t for t in cl.content() if t.i not in cl.used and not t.low.isdigit()]
    hit = _goal_tiers(words, lex.goals)
    if not words and any(t.low in LIMIT_WORDS for t in cl.toks):hit = list(lex.goals)       # "are the limits ok?": every goal
    if not hit:return None
    for t in words:
        if any(t.stem in g['_stems'] | g['_cells'] | g['_titles'] for g in hit):cl.use(t, 'about: %s' % ', '.join(g['_subject'] for g in hit if t.stem in g['_stems'] | g['_cells'] | g['_titles']))
    if len(hit) > COVER:
        return {'frame': 'CHECK', 'route': 'MEANING', '_options': [('Whether %s holds' % g['statement'], {'frame': 'CHECK', 'goal': g['key']}) for g in hit]}
    return {'frame': 'CHECK', 'route': 'CHECK', 'goals': [{'key': g['key'], 'statement': g['statement']} for g in hit],
            'covering': len(hit) > 1, 'choose': choose, 'choice_words': ', '.join(lex.sheet_words(s) for s in choose)}


def _value(cl, lex):
    """Rows or calculations the words name, read: "what is the settled power limit?" reads it in every revision."""
    m = VALUE.search(cl.text)
    if not m:return None
    words = [t for t in cl.content() if t.i not in cl.used and t.low not in UNIT_WORDS]
    if not words:return None
    rows = [r for r in lex.rows if all(t.stem in r.stems for t in words)]
    calcs = [c for c in lex.calculations if all(t.stem in c['stems'] for t in words)] if not rows else []
    if not rows and not calcs:return None
    cl.use_span(m.start(), m.end(), 'a question: what it reads')
    sheets = sorted({r.sheet for r in rows})
    choose, used = _revisions(cl, lex, sheets)
    if choose:rows = [r for r in rows if r.sheet in choose]
    for t in used:cl.use(t, 'the revision: %s' % ', '.join(lex.sheet_words(s) for s in choose))
    for t in words:cl.use(t, ', '.join([r.parameter for r in rows][:1] + [c['title'] for c in calcs][:1]))
    for n, t in enumerate(cl.toks):
        if t.low == 'in' and n + 1 < len(cl.toks) and cl.toks[n + 1].low in UNIT_WORDS:cl.use(cl.toks[n + 1], 'in %s' % UNIT_WORDS[cl.toks[n + 1].low])
    found = [{**r.ref(), 'value': r.value, 'unit': r.unit, 'revision': lex.sheet_words(r.sheet) if r.rev else ''} for r in rows]
    found += [{'calculation': c['id'], 'title': c['title'], 'unit': c.get('unit', '')} for c in calcs]
    if len(found) > COVER:
        return {'frame': 'VALUE', 'route': 'MEANING', '_options': [('The value of %s' % (f.get('parameter') or f.get('title')), {'frame': 'VALUE', 'row': f}) for f in found]}
    unit = next((UNIT_WORDS[cl.toks[n + 1].low] for n, t in enumerate(cl.toks) if t.low == 'in' and n + 1 < len(cl.toks) and cl.toks[n + 1].low in UNIT_WORDS), '')
    return {'frame': 'VALUE', 'route': 'VALUE', 'rows': found, 'unit': unit, 'choose': choose}


def _money(cl, lex, today):
    """An allowance from a typed sheet: "How much can I spend each week on groceries and stay under the month?"."""
    m = MONEY.search(cl.text)
    if not m or not lex.typed:return None
    words = [t for t in cl.content() if t.i not in cl.used]
    sheets = [s for s in lex.typed if any(t.stem in s['stems'] for t in words)]
    if not sheets:sheets = [s for s in lex.typed if any(t.stem in v for t in words for v in s['item_stems'].values())]
    sheets = [s for s in sheets if any(k.casefold() == 'plan' for k in s['items'])]
    if len(sheets) != 1:
        if len(sheets) > 1:
            return {'frame': 'MONEY', 'route': 'MEANING', '_options': [('An allowance from “%s”' % s['title'], {'frame': 'MONEY', 'sheet': s['id']}) for s in sheets]}
        return None
    sheet = sheets[0];cl.use_span(m.start(), m.end(), 'spending: an allowance')
    for t in words:
        if t.stem in sheet['stems']:cl.use(t, 'the typed sheet “%s”' % sheet['title'])
    per = 'month'
    found = PER.search(cl.text)
    if found:
        per = (found.group('per') or {'daily': 'day', 'weekly': 'week', 'monthly': 'month'}[found.group('ly').lower()]).lower()
        cl.use_span(found.start(), found.end(), 'each %s' % per)
    rel = _relation(cl)
    for t in cl.toks:
        if t.low in ('month', 'plan', 'budget', 'november', 'left', 'remaining', 'rest') and t.i not in cl.used:cl.use(t, 'within the plan of “%s”' % sheet['title'])
    plan = next(k for k in sheet['items'] if k.casefold() == 'plan');spent = next((k for k in sheet['items'] if k.casefold() == 'spent'), None)
    others = [k for k in sheet['items'] if k not in (plan, spent)] if spent is None else []
    return {'frame': 'MONEY', 'route': 'MONEY', 'sheet': {'id': sheet['id'], 'title': sheet['title']}, 'per': per, 'plan': plan,
            'spent': spent, 'others': others, 'relation': rel[0] if rel else 'le', 'as_of': today.isoformat()}


def _date(cl, lex):
    """The last day of a period from a rule on the desk: "when is the last day for the deposit?"."""
    m = DATE.search(cl.text)
    if not m or not lex.periods:return None
    words = [t for t in cl.content() if t.i not in cl.used and t.low not in DATE_WORDS]
    if not words:return None
    hit = [p for p in lex.periods if all(t.stem in p['stems'] for t in words)]
    if not hit:return None
    cl.use_span(m.start(), m.end(), 'a date question: the last day')
    for t in cl.toks:
        if t.low in DATE_WORDS and t.i not in cl.used:cl.use(t, 'the last day')
    if len(hit) > 1:
        return {'frame': 'DATE', 'route': 'MEANING', '_options': [('The last day under %s' % p['clause'], {'frame': 'DATE', 'rule': p['clause']}) for p in hit]}
    p = hit[0]
    for t in words:cl.use(t, '%s: “%s”' % (p['clause'], p['words']))
    events = sorted([e for e in lex.events if e['ends']], key=lambda e: e['day'])
    question = {'stage': 'period', 'count': str(p['count'])}
    if len(events) == 1:question['after'] = events[0]['day']
    elif len(events) > 1:question.update(events=[e['day'] for e in events][:8], labels=[e['label'][:120] for e in events][:8])
    for key in ('roll', 'count_clause', 'holiday_clause', 'yearly'):
        if lex.counting.get(key):question[key] = lex.counting[key]
    found = {'frame': 'DATE', 'route': 'DATE', 'rule': {k: p[k] for k in ('clause', 'words', 'count', 'event', 'source')},
             'events': [{'label': e['label'], 'day': e['day']} for e in events], 'counting': {k: v for k, v in lex.counting.items()},
             'question': question}
    if not events:
        found['open'] = [OpenPoint(about=(p['clause'],), kind='FACT_MISSING', who='WORLD', leaves=(Leaf(
            id='event', premise='NEW_READING', who='WORLD', words='No line on the desk gives the day %s.' % p['event']),)).as_record()]
    elif len(events) > 1:
        found['open'] = [OpenPoint(about=(p['clause'],), kind=MEANING, who=YOU, leaves=(Leaf(
            id='event', premise='RULE_READING', who=YOU, decisive='ALONE', values=tuple(e['day'] for e in events),
            words='Which day %s is yours to say.' % p['event']),),
            outcomes=tuple(Way(choices=(('event', e['label']),), words='%s, %s' % (e['label'], e['day'])) for e in events)).as_record()]
    return found


def _calendar(cl, today):
    """A day named in calendar words: one day, or the days it could be (a convention that is yours to say)."""
    out = []
    for m in CALENDAR.finditer(cl.text):
        phrase = m.group(0).strip();days = []
        if m.group('rel'):
            days = [today + timedelta(days={'today': 0, 'tomorrow': 1, 'yesterday': -1}[m.group('rel').lower()])]
        elif m.group('n'):
            days = [today + timedelta(days=int(m.group('n')))]
        else:
            wd = WEEKDAYS.index((m.group('wd') or m.group('bare')).lower());which = (m.group('which') or '').lower()
            ahead = (wd - today.weekday()) % 7
            if which == 'last':days = [today - timedelta(days=(today.weekday() - wd) % 7 or 7)]
            elif which == 'this':days = [today + timedelta(days=ahead)]
            else:
                coming = today + timedelta(days=ahead or 7)
                this_week = coming - timedelta(days=coming.weekday()) == today - timedelta(days=today.weekday())
                days = [coming, coming + timedelta(days=7)] if which == 'next' and (this_week or ahead == 0) else [coming]
        cl.use_span(m.start(), m.end(), 'a day: ' + ' or '.join(_day_words(d) for d in days))
        out.append({'phrase': phrase, 'days': [d.isoformat() for d in days]})
    return out


def _day_words(day):
    return '%s %d %s %d' % (WEEKDAYS[day.weekday()].capitalize(), day.day, MONTHS[day.month - 1].capitalize(), day.year)


def _sheets_named(cl, lex):
    """The sheets a clause's words name (her hand's find rule), for buttons when no frame read it."""
    words = [t for t in cl.content() if t.i not in cl.used]
    named = []
    for s in lex.world.sheets:
        ss = _naming(s.title) - _common(lex)
        if words and any(t.stem in ss for t in words):named.append(s.title)
    return named


def _naming(title):
    """The words of a title that name its sheet: not its revision mark ("Rev B", CURRENT, ARCHIVED), which names no sheet."""
    m = REVISION_TITLE.match(title or '')
    return stems(re.sub(r'\b(?:CURRENT|ARCHIVED)\b', ' ', m['stem'] if m else title or ''))


def _common(lex):
    """Words in every sheet title of the desk: the desk's own name, which tells no sheet apart."""
    titles = [stems(s.title) for s in lex.world.sheets]
    return frozenset.intersection(*titles) if len(titles) > 1 else frozenset()


def _meaning_options(cl, lex, frame_options=()):
    """The licensed options of a clause no frame could settle: every desk goal over a sheet its words name (hand_words'
    ranking), and the frames' own options. At most OPTIONS, then "none of these"."""
    found = [(w, f) for w, f in frame_options]
    words = [t for t in cl.content() if t.i not in cl.used and t.low not in LIMIT_WORDS]
    rows = [r for r in lex.rows if words and all(t.stem in r.stems for t in words) and r.limit is None] if words else []
    if rows and len(rows) <= COVER:          # a reading row named and nothing asked of it: reading its value is one option
        found.append(('Read %s' % ', '.join(sorted({r.parameter for r in rows})), {'frame': 'VALUE', 'rows': [
            {**r.ref(), 'value': r.value, 'unit': r.unit, 'revision': lex.sheet_words(r.sheet) if r.rev else ''} for r in rows]}))
        for t in words:cl.use(t, ', '.join(sorted({r.parameter for r in rows})))
    named = set(_sheets_named(cl, lex))
    if named:
        for template, params in hand_words.candidates(_clean(cl.text), lex.world):
            if set(params.values()) & named:
                found.append((hand_words.ask_words(template, params), {'frame': 'DESK', 'goals': [{'template': template, 'params': dict(params)}]}))
        for t in cl.toks:
            if t.i not in cl.used and any(t.stem in _naming(n) for n in named):cl.use(t, 'the sheet: ' + ', '.join(sorted(n for n in named if t.stem in _naming(n))))
            elif t.i not in cl.used and t.low in {'trace', 'follow', 'show', 'select', 'compare', 'beside', 'tidy', 'close'}:cl.use(t, 'a desk verb')
    return found


# -- the request -------------------------------------------------------------------------------------------------------------
def _decline(text, toks, lex, today):
    m = SHOULD.search(text)
    if not m:return None
    medical = MEDICAL.search(text);legal = LEGAL.search(text)
    if medical:said = WORDS['decline_medical']
    elif legal:said = WORDS['decline_legal'].format(act='bring a claim' if CLAIM.search(text) else 'do that')
    else:said = WORDS['decline']
    rest_text = (text[:m.start()] + ' ' + text[m.end():]).strip()
    rest = []
    if not medical:            # medicine: nothing read from the rest in 0.8.6 (design 5.8)
        for cl in _cut(rest_text, tokens(rest_text)):
            for reader in (lambda c: _money(c, lex, today), lambda c: _date(c, lex), lambda c: _solve(c, lex), lambda c: _check(c, lex), lambda c: _value(c, lex)):
                found = reader(cl)
                if found and found.get('route') in READS:rest.append(found);break
    related = [p['clause'] for p in lex.periods if stems(rest_text) & set(p['stems'])] if legal and not medical else []
    return {'route': 'DECLINE', 'decline': said, 'then': rest, 'then_words': WORDS['decline_then'] if rest else '',
            'related': related, 'medical': bool(medical), 'cue': m.group(0), 'at': m.span()}


def _understood(found, lex):
    route = found.get('route')
    if route == 'CHECK':
        if found.get('covering'):return WORDS['cover'].format(statements='; '.join('“%s”' % g['statement'] for g in found['goals']))
        return WORDS['check'].format(statement='“%s”' % found['goals'][0]['statement'])
    if route == 'SOLVE':
        return WORDS['solve'].format(unknown=found['unknown']['parameter'], statement='“%s”' % found['goals'][0]['statement'],
                                     under=WORDS['under'].format(choice=found['choice_words']) if found.get('choice_words') else '')
    if route == 'VALUE':return WORDS['value'].format(rows='; '.join(('%s %s' % (r.get('parameter') or r.get('title'), r.get('revision', ''))).strip() for r in found['rows']))
    if route == 'MONEY':return WORDS['money'].format(per=found['per'], title=found['sheet']['title'], day=_day_words(date.fromisoformat(found['as_of'])))
    if route == 'DATE':
        c = found.get('counting') or {}
        counting = ' and '.join(x['clause'] for x in (c.get('count_clause'), c.get('roll'), c.get('holiday_clause')) if x)
        return (WORDS['date'].format(clause=found['rule']['clause'], counting=counting) if counting else WORDS['date_bare'].format(clause=found['rule']['clause']))
    if route == 'DAY':return WORDS['day'].format(phrase=found['phrase'], day=_day_words(date.fromisoformat(found['days'][0])))
    if route == 'DESK':
        said = [g['statement'] for g in found['goals']]
        if found.get('forbid'):said.append(WORDS['forbid'].format(what=', '.join(FORBID[f['template']].format(**f['params']) for f in found['forbid'])).rstrip('.'))
        return WORDS['desk'].format(statements='; '.join(said)) if said else ''
    return ''


def _key(found):
    keep = {'route': found['route'], 'readings': [{k: v for k, v in r.items() if not k.startswith('_') and k not in ('open', 'clause')} for r in found['readings']],
            'forbid': found.get('forbid', []), 'options': [o['reading'] for o in found.get('options', [])], 'decline': found.get('decline')}
    return hashlib.sha256(json.dumps(keep, sort_keys=True, ensure_ascii=False, default=str).encode('utf-8')).hexdigest()


def said_key(text):
    """The key a kept phrase is found by (S7's phrasebook): the stems of the request's words that carry meaning, in order."""
    return ' '.join(t.stem for t in tokens(plain(text)[:TEXT]) if t.low not in STOP)


def read(text, lex, today=None, kept=(), model_loaded=False):
    """One reading of the owner's request over the desk's vocabulary `lex` (see the module's words). `today` is the day the
    request is said on (calendar words and an allowance's as-of day); `kept` the phrases the owner kept (S7's phrasebook:
    [{'words': the request's words, 'reading': the reading he kept}]); `model_loaded` whether a MEANING point goes to the
    model (else to you, as buttons). Never asks a model and never writes."""
    text = plain(text)[:TEXT];today = today or date.today()
    if isinstance(today, str):today = date.fromisoformat(today)
    toks = tokens(text)
    out = {'schema': SCHEMA, 'text': text, 'route': 'NONE', 'readings': [], 'words': [], 'understood': '', 'open': [], 'options': [],
           'forbid': [], 'elimination': [], 'acts': 'read', 'model_calls': 0, 'lexicon': lex.digest, 'complete': True}
    said = ' '.join(t.stem for t in toks if t.low not in STOP)
    for k in kept or ():
        if k.get('words') == said:
            out.update(route='KEPT', readings=[k['reading']], understood=WORDS['kept'].format(understood=k['reading'].get('understood', '')))
            out['words'] = [{'word': t.text, 'at': list(t.at), 'used': True, 'meant': 'a phrase you kept'} for t in toks]
            if k['reading'].get('frame') == 'DESK' and k['reading'].get('goals'):out['acts'] = 'navigates'     # S7: a phrase moves the window at most
            if k.get('id'):out['phrase'] = {'id': k['id'], 'follows': k.get('follows'), 'moved': k.get('moved') or [], 'note': k.get('note') or ''}
            out['card'] = WORDS['card']
            out['key'] = _key(out);return out
    declined = _decline(text, toks, lex, today)
    if declined:
        out.update(route='DECLINE', decline=declined['decline'], readings=declined['then'], understood=declined['decline'],
                   related=declined['related'], then=declined['then_words'])
        out['open'] = [OpenPoint(about=('words',), kind=DECISION, who=YOU, leaves=(Leaf(id='decision', premise='SHOULD_I', who=YOU,
                                                                                       words=declined['decline']),)).as_record()]
        cue = (declined['at'][0], declined['at'][1])
        out['words'] = [{'word': t.text, 'at': list(t.at), 'used': cue[0] <= t.at[0] and t.at[1] <= cue[1],
                         'meant': 'a decision: yours to make' if cue[0] <= t.at[0] and t.at[1] <= cue[1] else ''} for t in toks]
        out['key'] = _key(out);return out
    clauses = _cut(text, toks);readings = [];last = None;opens = [];options = []
    for cl in clauses:
        cl.negated = any(t.low in NEG for t in cl.toks)
        days = _calendar(cl, today)
        found = _desk(cl, lex, last)
        ambiguous = found.pop('_ambiguous') if found and '_ambiguous' in found else None
        if ambiguous:found = None
        for reader in (lambda c: _money(c, lex, today), lambda c: _date(c, lex), lambda c: _solve(c, lex), lambda c: _check(c, lex),
                       lambda c: _value(c, lex)):
            if found is not None:break
            before = dict(cl.used);found = reader(cl)
            if found is None:cl.used = before          # a frame that did not read the clause leaves no word marked
        for t in cl.toks:
            if t.low in NEG and t.i not in cl.used:cl.used[t.i] = 'not'
        if found is None and days:
            if len(days) == 1 and len(days[0]['days']) == 1:found = {'frame': 'DAY', 'route': 'DAY', **days[0]}
            else:found = {'frame': 'DAY', 'route': 'ASK'}
        if found is None:
            frame_options = []
            if ambiguous:
                phrase, near, _ = ambiguous
                frame_options = [(hand_words.ask_words('shown', {'s': t}), {'frame': 'DESK', 'goals': [{'template': 'shown', 'params': {'s': t}}]}) for t in near]
            opts = _meaning_options(cl, lex, frame_options)
            if opts:found = {'frame': 'WORDS', 'route': 'MEANING', '_options': opts}
            else:found = {'frame': 'NONE', 'route': 'NONE'}
        if found['route'] == 'DESK':last = next((g['params'].get('s') or g['params'].get('a') for g in found['goals'] if g['params']), last)
        if cl.negated and found['route'] != 'DESK':found['negated'] = True
        for d in days:
            if len(d['days']) > 1:
                opens.append(OpenPoint(about=('words:%s' % d['phrase'],), kind=AUTHORITY, who=YOU, leaves=(Leaf(
                    id='day', premise='CONVENTION', who=YOU, decisive='ALONE', values=tuple(d['days']),
                    words=WORDS['ask_day'].format(phrase=d['phrase'], options=' or '.join(_day_words(date.fromisoformat(x)) for x in d['days']))),),
                    outcomes=tuple(Way(choices=((d['phrase'], x),), words=_day_words(date.fromisoformat(x))) for x in d['days'])).as_record())
                options += [_option(len(options) + 1, _day_words(date.fromisoformat(x)), {'frame': 'DAY', 'phrase': d['phrase'], 'days': [x]}) for x in d['days']]
                found['route'] = 'ASK';found['days'] = d['days'];found['phrase'] = d['phrase']
            elif found['frame'] != 'DAY':found.setdefault('when', []).append(d)
        unread = cl.unread()
        if unread and found['route'] in READS + ('DESK',):
            found['_options'] = [(_understood(found, lex) or found['route'], {k: v for k, v in found.items() if not k.startswith('_')})]
            found['route'] = 'MEANING';out['complete'] = False
        if found['route'] == 'MEANING':
            group = [_option(len(options) + n + 1, w, f) for n, (w, f) in enumerate(found.pop('_options', [])[:16])]
            group, revision_only = _collapse(group, len(options))
            if revision_only:          # the options differ only in which revision: yours, never the model's
                found['route'] = 'ASK'
                opens.append(OpenPoint(about=('words:%s' % cl.text,), kind=AUTHORITY, who=YOU, leaves=(Leaf(
                    id='revision', premise='REVISION', who=YOU, decisive='ALONE', values=tuple(o['words'] for o in group)),)).as_record())
            else:
                asked, kind = _who('WHICH_GOAL', model_loaded)
                opens.append(OpenPoint(about=('words:%s' % cl.text,), kind=kind, who=asked, leaves=(Leaf(
                    id='meaning', premise='WHICH_GOAL', who=asked, values=tuple(o['words'] for o in group[:OPTIONS if asked == YOU else 16])),)).as_record())
            options += group[:OPTIONS if not model_loaded else 16]
        found.pop('_options', None)
        opens += found.pop('open', [])
        if found.get('elimination'):out['elimination'].append(found['elimination'])
        out['forbid'] += found.get('forbid', [])
        found['clause'] = cl.text
        readings.append((cl, found))
    routes = [f['route'] for _, f in readings]
    reads = [r for r in routes if r != 'NONE']
    if not reads:route = 'NONE'
    elif 'ASK' in reads:route = 'ASK'
    elif 'MEANING' in reads:route = 'MEANING'
    elif len(set(reads)) == 1:route = reads[0]
    else:route = 'COMPOUND'
    if reads and len(reads) != len(routes):out['complete'] = False          # a clause nothing on the desk carries
    out.update(route=route, readings=[f for _, f in readings], open=opens, options=options)
    out['acts'] = 'navigates' if any(f['route'] == 'DESK' and f.get('goals') for _, f in readings) else 'read'
    words = []
    for t in toks:
        meant = next((cl.used.get(t.i) for cl, _ in readings if t in cl.toks and t.i in cl.used), '')
        words.append({'word': t.text, 'at': list(t.at), 'used': bool(meant), 'meant': meant or '',
                      'carries': t.low not in STOP and t.low not in NEG or bool(meant)})
    out['words'] = words
    unread = [w['word'] for w in words if w['carries'] and not w['used']]
    parts = [_understood(f, lex) for _, f in readings if f['route'] in READS + ('DESK',)]
    if route == 'NONE':parts = [WORDS['none']]
    elif route == 'ASK':parts = [p['leaves'][0]['words'] or WORDS['ask_revision'].format(options=' or '.join(p['leaves'][0]['values'])) for p in opens if p['who'] == YOU][:1] or parts
    elif route == 'MEANING':parts = [WORDS['meaning']]
    out['understood'] = ' '.join(p for p in parts if p)
    out['unread'] = unread
    if unread and route != 'NONE':out['unread_words'] = WORDS['unread'].format(words=', '.join('“%s”' % w for w in unread))
    if route in READS + ('DESK', 'COMPOUND') and out['complete']:out['card'] = WORDS['card']
    out['key'] = _key(out)
    return out


# -- the desk, read for the dictionary ------------------------------------------------------------------------------------------
def _typed_sheets():
    """The typed sheets of the office store (not reviewed from a PDF): [{'id', 'title', 'rows'}], the heading row first."""
    from .office_service import store
    from .datasheet_work import SHEET
    out = []
    for row in store().listing():
        try:saved = store().get(row['id'])
        except (ValueError, OSError, KeyError):continue
        if (saved.get('origin') or {}).get('profile') == SHEET:continue
        cells = ((saved.get('document') or {}).get('sheets') or [{}])[0].get('cells') or {}
        grid = {}
        for address, cell in cells.items():
            m = re.fullmatch(r'([A-Z])(\d{1,4})', address)
            if m:grid.setdefault(int(m.group(2)), {})[m.group(1)] = _cell_text((cell or {}).get('value'))
        if not grid:continue
        width = max(ord(c) - 64 for r in grid.values() for c in r)
        out.append({'id': saved['id'], 'title': (saved.get('document') or {}).get('title') or row.get('title') or '',
                    'rows': [[r.get(chr(65 + i), '') for i in range(width)] for _, r in sorted(grid.items())]})
    return out


def _cell_text(value):
    """A cell's value as text; a typed 600.00 the store holds as a number is written back as its exact decimal."""
    if value is None:return ''
    if isinstance(value, bool):return str(value)
    if isinstance(value, int):return str(value)
    if not isinstance(value, str):
        text = repr(value);return text[:-2] if text.endswith('.0') else text
    return value


def _passages(kernel, principal):
    """The admitted papers that hold a period or a dated line: [{'name', 'text'}] (intake.search, accepted sources only)."""
    out, seen = [], set()
    try:spaces = (kernel.dispatch('intake.namespaces', {}, principal).get('result') or {}).get('namespaces') or ()
    except Exception:return out
    for space in list(spaces)[:8]:
        for query in ('days after', 'ends', 'returned'):
            got = kernel.dispatch('intake.search', {'namespace': space['id'], 'query': query, 'limit': 20}, principal)
            for hit in (got.get('result') or {}).get('hits') or () if got.get('ok') else ():
                if hit.get('id') in seen:continue
                seen.add(hit.get('id'));out.append({'name': hit.get('name') or '', 'text': hit.get('text') or ''})
    return out


def lexicon(kernel, principal, world=None):
    """The desk's vocabulary as the records hold it now: the reviewed sheets and their rows, the calculations, the goals the
    desk proposes, the typed sheets, and the admitted papers' rules and dated lines. Reads only."""
    from . import goals as G
    sheets = [{'id': s['id'], 'title': (s.get('document') or {}).get('title') or '',
               'rows': [{k: r[k] for k in ('cell', 'parameter', 'value', 'unit', 'conditions')} for r in G._rows(s)]} for s in G._sheets()]
    return Lexicon.of(sheets=sheets, calculations=G._calculations(kernel, principal), goals=G.candidates(kernel, principal),
                      typed=_typed_sheets(), passages=_passages(kernel, principal), world=world)


# -- the answers of a read, worked out ------------------------------------------------------------------------------------------
def _rational(record):
    return Fraction(record['rational']) if record and record.get('rational') else None


def _in(value, have, want):
    """An exact value in `have` units as `want` units (both of UNIT_SCALE), or unchanged."""
    if value is None or want == have or have not in UNIT_SCALE or want not in UNIT_SCALE:return value
    return value * UNIT_SCALE[have] / UNIT_SCALE[want]


def work(kernel, principal, found, today=None):
    """The answers of each clause of a reading that is a read, exactly, by the maths that already exists: goals.judge for a
    check or a room, math_money for an allowance, math_dates for a period, the rows for a value. Reads only; model_calls 0.
    [{'clause', 'route', 'answers'...}]."""
    from . import goals as G, math_money, math_dates
    today = today or date.today()
    if isinstance(today, str):today = date.fromisoformat(today)
    out = [];candidates = None
    for r in found.get('readings') or ():
        route = r.get('route')
        if route in ('CHECK', 'SOLVE'):
            candidates = candidates if candidates is not None else {g['key']: g for g in G.candidates(kernel, principal)}
            stage = 'room' if route == 'SOLVE' else 'check'
            judged = [G.judge(kernel, principal, candidates[g['key']], r.get('choose') or (), (stage,)) for g in r['goals'] if g['key'] in candidates]
            row = {'clause': r['clause'], 'route': route, 'judged': [{'statement': j['statement'], 'state': j['state'],
                   'ways': [{'choice': w['choice'], 'state': w['state'], 'words': w['answers'][stage]['words']['answer']} for w in j['ways']]} for j in judged]}
            if route == 'SOLVE':
                want = r.get('unit') or r['unknown']['unit'];allowed = []
                for j in judged:
                    for w in j['ways']:
                        result = w['answers']['room'].get('result') or {}
                        move = next((m for m in result.get('moves') or () if m['name'] == r['unknown']['symbol']), None)
                        if not move:continue
                        have = move['unit'];upper = _rational((move.get('upper') or {}).get('value'))
                        step = _rational(((move.get('rise') or {}).get('on_step')))
                        allowed.append({'choice': w['choice'], 'state': w['state'], 'unit': want,
                                        'upper': str(_in(upper, have, want)) if upper is not None else None,
                                        'whole': str(_in(step, have, want)) if step is not None else None, 'closed': (move.get('upper') or {}).get('closed')})
                row['allowed'] = allowed
            out.append(row)
        elif route == 'MONEY':
            sheet = next((t for t in _typed_sheets() if t['id'] == r['sheet']['id']), None)
            if sheet is None:out.append({'clause': r['clause'], 'route': route, 'refused': 'the typed sheet is no longer on the desk'});continue
            head = [h.strip() for h in sheet['rows'][0]];items = {row[0].strip(): dict(zip(head, row)) for row in sheet['rows'][1:] if row and row[0].strip()}
            month_end = (today.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
            left = math_dates.answer({'stage': 'calculate', 'expression': '%s - %s' % (month_end.isoformat(), today.isoformat())}, today)
            days = int(Fraction(left['result']['value']['rational']))
            names = {};given = []
            for item in [r['plan']] + ([r['spent']] if r.get('spent') else r.get('others') or []):
                name = re.sub(r'[^a-z0-9]+', '_', item.lower()).strip('_') or 'item';names[item] = name
                cells = items.get(item) or {};entry = {'name': name, 'lo': cells.get('Amount') or cells.get('Low') or '0'}
                if cells.get('Low') and cells.get('High'):entry = {'name': name, 'lo': cells['Low'], 'hi': cells['High']}
                given.append(entry)
            rest = ' - '.join(names[i] for i in names if i != r['plan'])
            left_expr = '%s - %s' % (names[r['plan']], rest) if rest else names[r['plan']]
            span = {'day': 1, 'week': 7, 'month': days}[r['per']]
            exact = math_money.answer({'stage': 'calculate' if not any('hi' in g for g in given) else 'range',
                                       'expression': '%d * (%s) / %d' % (span, left_expr, days), 'given': given})
            down = math_money.answer({'stage': 'solve', 'expression': '%d * per <= %d * (%s)' % (days, span, left_expr), 'given': given,
                                      'for': 'per', 'step': '0.01'})
            res = exact.get('result') or {};cents = (((down.get('result') or {}).get('allowed') or {}).get('lattice') or {}).get('upper') or {}
            out.append({'clause': r['clause'], 'route': route, 'as_of': today.isoformat(), 'days_left': days, 'per': r['per'],
                        'exact': (res.get('value') or {}).get('rational') or [x.get('rational') for x in res.get('range') or ()],
                        'in_cents': cents.get('rational'), 'in_cents_decimal': cents.get('decimal'),
                        'state': down.get('state'), 'answers': {'exact': exact.get('digest'), 'solve': down.get('digest')}})
        elif route == 'DATE':
            asked = dict(r['question'])
            got = math_dates.answer({**asked, 'as_of': today.isoformat()}, today)
            period = (got.get('result') or {}).get('period') or {}
            out.append({'clause': r['clause'], 'route': route, 'state': got.get('state'), 'as_of': today.isoformat(),
                        'readings': [{'label': x.get('label'), 'event': (x.get('event') or {}).get('iso'), 'last_day': (x.get('last_day') or {}).get('iso'),
                                      'since': x.get('since')} for x in period.get('readings') or ()],
                        'words': (got.get('words') or {}).get('answer'), 'answer': got.get('digest')})
        elif route == 'VALUE':
            out.append({'clause': r['clause'], 'route': route, 'rows': r['rows']})
        elif route == 'DAY':
            out.append({'clause': r['clause'], 'route': route, 'days': r['days']})
    return out


# -- the operation --------------------------------------------------------------------------------------------------------------
_DAY = {'type': 'string', 'minLength': 10, 'maxLength': 10, 'pattern': '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'}
FIELDS = {'requests.read': ({'text': {'type': 'string', 'minLength': 1, 'maxLength': TEXT}, 'today': _DAY, 'work': {'type': 'boolean'},
                             'model_loaded': {'type': 'boolean'}}, ['text'])}
SCOPES = {'requests.read': 'read'}


def dispatch(kernel, op, args, principal, today=None):
    """requests.read: the reading of the owner's words over the desk as it stands, and with work, the answers of a read.
    `today` is the day of this computer's clock as the Kernel read it (engineering_kernel.today), unless the request names
    its own day."""
    from .office_service import owner
    if op != 'requests.read':raise ValueError('Unknown reading operation')
    owner(principal)                 # the sheets live in the owner's profile, as for office.get and goals.*
    day = date.fromisoformat(args['today']) if args.get('today') else (today or date.today())
    lex = lexicon(kernel, principal)
    from . import phrases          # 0.8.6 S7: the phrasebook first (only what the owner kept, pointed at the current revision)
    found = read(args['text'], lex, today=day, kept=phrases.kept(kernel, principal, lex.world), model_loaded=bool(args.get('model_loaded')))
    if args.get('work') and found['acts'] == 'read' and found['route'] in READS + ('COMPOUND',) and found['complete']:
        found['answers'] = work(kernel, principal, found, day)
    return found
