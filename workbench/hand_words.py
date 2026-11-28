"""The owner's words to her hand's goals: a deterministic match first, and the numbered goals a small model may pick from.

Kasandra's hand, first slice. What is matched here, in the owner's own words:

  trace X, follow X, where X comes from         the trace of X is shown
  show X, select X                              X is selected in the Field
  X beside its other revision, X beside Y,      X and its other revision are side by side
    put X side by side, compare X
  close what is open, tidy up                   nothing is left open over the window

Several clauses joined by "and", "then", a comma or a semicolon each give a goal, in the order said. A sheet is found by
desk_doers.find_sheet's rule: its exact title first, else the one title that holds the words; for a comparison, two titles
that are the two revisions of one sheet count as one (the comparison is the same pair from either side).

A request every clause of which matches, each sheet found, is a full match: her hand plans it with no model. Otherwise,
when the request names a desk verb or a sheet in sight, the GOAL turn asks the model one small question: which of these
numbered goals (at most 16, plus "none of these") did the owner mean. The answer is read by read_pick() and nothing else:
1 to 3 different numbers, in range, and "none" alone. The goals' words are templates with a title put in, never the model's.

Pure Python: no Qt.
"""
import json
import re
from dataclasses import dataclass, field

from . import goals as G

MOST = 16                       # numbered goals offered to the model, before "none of these"
PICK_MOST = 3
VERBS = ('trace', 'follow', 'show', 'select', 'put', 'compare', 'close', 'tidy', 'where', 'beside', 'side by side', 'point at')
STARTS = r'(?:trace|follow|show|select|put|place|lay|set|compare|close|tidy|clear|where|point|pick|bring)'
QUOTES = {'“': '', '”': '', '"': '', '‘': "'", '’': "'"}
# the model's list: what each goal does, as an order the owner could have given (templates; a title put in)
ASK_WORDS = {'traced': 'Trace “{s}”: show where it comes from and what rests on it',
             'shown': 'Select “{s}” in the Field',
             'side_by_side': 'Put “{a}” and “{b}” side by side',
             'tidy': 'Close whatever is open over the window'}
KEYWORDS = {'traced': {'trace', 'where', 'come', 'comes', 'from', 'follow', 'feeds', 'rests'},
            'shown': {'show', 'select', 'point', 'pick', 'see'},
            'side_by_side': {'beside', 'side', 'compare', 'revision', 'revisions', 'next', 'against', 'both'},
            'tidy': {'close', 'tidy', 'open', 'away', 'clear'}}
PHRASES = {'traced': ('come from', 'comes from', 'rests on'), 'shown': (), 'side_by_side': ('side by side', 'other revision'),
           'tidy': ('what is open',)}
TEMPLATE_ORDER = ('traced', 'side_by_side', 'shown', 'tidy')


@dataclass
class Match:
    goals: list = field(default_factory=list)       # [(template, params)] in the order said
    full: bool = False
    clauses: list = field(default_factory=list)
    unmatched: list = field(default_factory=list)   # clauses no pattern took, or whose sheet was not found
    ambiguous: list = field(default_factory=list)   # (words, the titles they could be)


def plain(text):
    text = str(text or '')
    for k, v in QUOTES.items():text = text.replace(k, v)
    return re.sub(r'\s+', ' ', text).strip().rstrip('.!?').strip()


def clauses(text):
    """The request cut where a new order starts: at "and", "then", a comma or a semicolon followed by a verb."""
    text = plain(text)
    parts = re.split(r'\s*(?:,|;|\band\b|\bthen\b)\s*(?=(?:(?:and|then|please)\s+)*' + STARTS + r'\b)', text, flags=re.IGNORECASE)
    out = []
    for p in parts:
        p = re.sub(r'^(?:(?:and|then|please|also|now)\s+)+', '', p.strip(' ,;'), flags=re.IGNORECASE).strip()
        if p:out.append(p)
    return out


def _name(words):
    words = re.sub(r"^(?:the|my|our|this|that)\s+", '', plain(words).strip(), flags=re.IGNORECASE)
    words = re.sub(r"\s+(?:sheet|sheets)$", '', words, flags=re.IGNORECASE)
    return re.sub(r"'s$", '', words).strip()


def find(words, titles):
    """desk_doers.find_sheet's rule over titles: the exact title, else the one that holds the words. (title or None, the
    titles it could be)."""
    want = _name(words).casefold()
    if not want:return None, []
    exact = [t for t in titles if t.casefold().strip() == want]
    if len(exact) == 1:return exact[0], exact
    near = exact or [t for t in titles if want in t.casefold()]
    if len(near) == 1:return near[0], near
    return None, near


def pair_of(words, world, other=None):
    """The (older, newer) revisions the words name: one sheet that has another revision; two sheets that are the two
    revisions of one; or words that only the two revisions of one sheet hold."""
    titles = tuple(s.title for s in world.sheets if s.sibling)      # only a sheet with another revision can be compared
    one, near = find(words, titles)
    if other is not None:
        two, _ = find(other, titles)
        if one and two and world.pair(one) and set(world.pair(one)) == {one, two}:return world.pair(one)
        return None
    if one and world.pair(one):return world.pair(one)
    pairs = {world.pair(t) for t in near}
    if len(near) == 2 and len(pairs) == 1 and None not in pairs:return pairs.pop()
    return None


def _clause(text, world, last=None):
    """(template, params) for one clause, or (None, why). "it" names the sheet of the clause before (`last`)."""
    titles = world.titles();I = re.IGNORECASE
    if last and re.search(r'\b(?:it|that|this|them)$', text.strip(), I):
        bare = re.sub(r'\s+(?:it|that|that one|this|this one|them)$', ' ' + last, text.strip(), flags=I)
        if bare != text.strip():text = bare
    m = (re.match(r'^(?:show(?: me)?|tell me|see)?\s*where\s+(?:do|does|did)?\s*(?P<x>.+?)\s+comes?\s+from$', text, I)
         or re.match(r'^(?:trace|follow)\s+(?:the\s+trace\s+of\s+)?(?P<x>.+)$', text, I))
    if m:
        x = text[m.start('x'):m.end('x')];t, near = find(x, titles)
        return ('traced', {'s': t}) if t else (None, ('ambiguous', x, near) if near else ('unknown', x, []))
    m = re.match(r'^(?:put|show|set|place|lay|bring)?\s*(?P<a>.+?)\s+(?:beside|next to|alongside|side by side with|against)\s+(?P<b>.+)$', text, I)
    if m:
        a = text[m.start('a'):m.end('a')];b = text[m.start('b'):m.end('b')]
        pair = pair_of(a, world) if re.fullmatch(r'(?:its|the)\s+other\s+(?:revision|one)', b.casefold().strip()) else pair_of(a, world, b)
        return ('side_by_side', {'a': pair[0], 'b': pair[1]}) if pair else (None, ('unknown', text, []))
    m = re.match(r'^(?:put|show|set|place|lay|bring)\s+(?P<x>.+?)\s+side\s+by\s+side$', text, I) or re.match(r'^compare\s+(?P<x>.+?)$', text, I)
    if m:
        x = text[m.start('x'):m.end('x')];pair = pair_of(x, world)
        return ('side_by_side', {'a': pair[0], 'b': pair[1]}) if pair else (None, ('unknown', x, []))
    if re.fullmatch(r"(?:close|put away|clear)\s+(?:what is open|what's open|everything|it all|all of it|the menus?|what you opened)|tidy(?:\s+up)?", text, I):
        return 'tidy', {}
    m = re.match(r'^(?:show(?: me)?|select|point at|pick|go to)\s+(?P<x>.+)$', text, I)
    if m:
        x = text[m.start('x'):m.end('x')];t, near = find(x, titles)
        return ('shown', {'s': t}) if t else (None, ('ambiguous', x, near) if near else ('unknown', x, []))
    return None, ('no pattern', text, [])


def match(text, world):
    """The deterministic match of a request (see the module's words). A goal said twice is kept once."""
    out = Match(clauses=clauses(text))
    seen = set()
    last = None
    for c in out.clauses:
        template, params = _clause(c, world, last)
        if template is None:
            out.unmatched.append(c)
            if params and params[0] == 'ambiguous':out.ambiguous.append((params[1], list(params[2])))
            continue
        last = params.get('s') or params.get('a') or last
        key = (template, tuple(sorted(params.items())))
        if key not in seen:seen.add(key);out.goals.append((template, params))
    out.full = bool(out.goals) and not out.unmatched
    return out


def goals_of(pairs, start=1, origin='OWNER'):
    """goals.Goal for each (template, params), numbered from `start`; the standing tidy goal is added by the hand."""
    return [G.make(t, p, start + n, origin=origin, persist=(t == 'tidy')) for n, (t, p) in enumerate(pairs)]


def desk_request(text, world, in_sight=()):
    """Whether the GOAL turn applies: the request names a desk verb, or a sheet in sight. Any other request keeps the path
    Talk has always taken."""
    low = plain(text).casefold()
    if any(re.search(r'\b' + re.escape(v) + r'\b', low) for v in VERBS):return True
    return any(t.casefold() in low or _stem(t) in low for t in in_sight)


def _stem(title):
    return re.sub(r'^\d+\s+', '', title.casefold()).strip()


def candidates(text, world, most=MOST):
    """The numbered goals the GOAL turn offers: every goal of this slice over the sheets on the desk (each comparison once,
    whichever revision names it), ranked by the clause of the request that fits it best (a sheet's own words count twice,
    the goal's verbs once and its phrase twice, the verbs only where the clause names the sheet), then by kind, then by
    title. A list, never more than `most`."""
    parts = [set(re.findall(r'[a-z0-9]+', c.casefold())) for c in clauses(text)] or [set()]
    lows = [c.casefold() for c in clauses(text)] or ['']
    found = {}
    for s in world.sheets:
        found[('traced', (('s', s.title),))] = ('traced', {'s': s.title})
        found[('shown', (('s', s.title),))] = ('shown', {'s': s.title})
        pair = world.pair(s.title)
        if pair:found[('side_by_side', (('a', pair[0]), ('b', pair[1])))] = ('side_by_side', {'a': pair[0], 'b': pair[1]})
    found[('tidy', ())] = ('tidy', {})

    def score(item):
        template, params = item
        named = set()
        for v in params.values():named |= {w for w in re.findall(r'[a-z0-9]+', v.casefold()) if len(w) > 1 and not w.isdigit() and w not in ('rev', 'revision')}
        def fit(words, low):
            verbs = len(words & KEYWORDS[template]) + 2 * sum(1 for phrase in PHRASES[template] if phrase in low)
            titled = len(words & named)
            # a goal's verbs count fully only in a clause that names its sheet (or for a goal that names none)
            return 2 * titled + verbs if (titled or not named) else verbs / 10.0
        best = max(fit(words, low) for words, low in zip(parts, lows))
        return -best, TEMPLATE_ORDER.index(template), json.dumps(params, sort_keys=True)
    ranked = sorted(found.values(), key=score)
    return ranked[:most]


def ask_words(template, params):
    return ASK_WORDS[template].format(**params)


PICK_SYSTEM = ('You match a request to numbered goals in Kas, a desk on this computer. Choose only the goals the request asks '
               'for, one for each thing it asks, in the order it asks for them: one to three numbers. Never add a goal it does not ask '
               'for. If it asks for none of them, choose only the last number, "none of these". Answer only as JSON {"pick": [n]} or '
               '{"pick": [n, m]}. Do not explain.')


def pick_message(text, cands):
    """The GOAL turn's one message: the request and the numbered goals, the last "none of these"."""
    rows = ['%d. %s' % (n, ask_words(t, p)) for n, (t, p) in enumerate(cands, 1)]
    rows.append('%d. None of these' % (len(cands) + 1))
    return 'Request: %s\nGoals:\n%s' % (plain(text)[:400], '\n'.join(rows))


def pick_schema(count):
    """The answer's shape for `count` numbered options (the last is "none of these")."""
    return {'type': 'object', 'properties': {'pick': {'type': 'array', 'items': {'type': 'integer', 'minimum': 1, 'maximum': count},
                                                      'minItems': 1, 'maxItems': PICK_MOST, 'uniqueItems': True}},
            'required': ['pick'], 'additionalProperties': False}


class Invalid(ValueError):
    """An answer that is not 1 to 3 different numbers in range, or "none" with others."""


def read_pick(answer, count):
    """The numbers an answer picks: a list of 1 to 3 different integers from 1 to `count`; [] when it picks only the last,
    "none of these". Anything else raises Invalid, and no act runs on it."""
    if isinstance(answer, str):
        try:answer = json.loads(answer)
        except ValueError:raise Invalid('the answer is not JSON') from None
    if not isinstance(answer, dict) or set(answer) != {'pick'}:raise Invalid('the answer is not {"pick": [...]}')
    picks = answer['pick']
    if not isinstance(picks, list) or not 1 <= len(picks) <= PICK_MOST:raise Invalid('the answer picks %s numbers' % (len(picks) if isinstance(picks, list) else 'no'))
    if any(type(n) is not int for n in picks):raise Invalid('the answer picks something that is not a whole number')
    if len(set(picks)) != len(picks):raise Invalid('the answer picks a number twice')
    if any(not 1 <= n <= count for n in picks):raise Invalid('the answer picks a number out of range')
    if count in picks:
        if len(picks) > 1:raise Invalid('the answer picks "none of these" with other goals')
        return []
    return picks
