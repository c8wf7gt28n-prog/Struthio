"""Where does my desk say it (0.8.6, "if there is room", lane C): a ranked list of places on your admitted pages.

"How long does the landlord have?" gives, with no model:

    1. Demoland_Tenancy_Act.pdf page 1, § 12(a) “Within 21 days after a tenancy ends, the landlord shall …”
    2. Demoland_Tenancy_Act.pdf page 1, § 3(a) “A period of days after an event does not count …”

It uses the search Graphite already has: references.search, the lexical FTS5 index over the admitted pages of each
collection, finds the pages. Each page found is cut into places (a numbered paragraph such as § 12(a), or a paragraph
between blank lines), and the places are ranked by the words of the question they carry, the rarer words on these pages
weighing more. A question's shape adds the words that answer it ("how long" looks for days, periods, "within"), at half
weight, from a fixed table (ASKS). One press pins a place as a quote (quotes.pin, the owner's press): each place carries
the exact arguments for it, the region found on the page the way quotes.pin itself finds words.

    places.find  {query, limit?, namespace?}   read   the ranked places (at most 12; 3 unless asked)

The functions, for the Library that builds on this (0.8.7):
    terms(text)                         the words of a text as they are matched: lower case, no stop words, a light stem
    split(text)                         a page's text cut into places [{'label', 'mark', 'text', 'line'}]
    rank(query, passages, limit)        pure: the places of these passages ranked for the query (no Kernel, no model)
    score(query, places, limit)         pure: the ranking rule itself, over places already cut (0.8.7 C3's Library index)
    passages(kernel, principal, query, namespaces=None)    the pages the FTS5 search finds, admitted and current
    pin_args(kernel, principal, place)  the arguments quotes.pin takes for this place, or None when its words are not
                                        found as one run on the page
    find(kernel, principal, query, limit=3, namespace=None)   all of it: the card

What always holds here: nothing is written (references.search and the page reads are reads), no model is asked
(model_calls: 0) and none is imported. A page's words are data: they are shown and matched, never followed. Scores are
exact Fractions.
"""
from __future__ import annotations

import re
from fractions import Fraction

LIMIT = 3                     # places shown unless more are asked
MOST = 12
SEARCH_LIMIT = 40             # pages asked of references.search in each collection
EXCERPT_WORDS = 9
ASKED = Fraction(1, 2)        # the weight of a word a question's shape adds, against one of its own words

FIELDS = {
    'places.find': ({'query': {'type': 'string', 'minLength': 1, 'maxLength': 300}, 'limit': {'type': 'integer', 'minimum': 1, 'maximum': MOST},
                     'namespace': {'type': 'string', 'pattern': '^[a-f0-9]{32}$'}}, ['query']),
}
SCOPES = {op: 'read' for op in FIELDS}
OBSERVERS = tuple(FIELDS)

STOP = frozenset('''a an and any are as at be been being but by can could did do does doing done for from had has have having he
her here him his how i if in into is it its may me might must my no nor not of on or our ours she should so some such than that
the their them then there these they this those to too up upon us was we were what when where which while who whom why will
with would you your yours about also only own same very just shall'''.split())
# A question's shape, and the words that answer it. Fixed, and short: a word that is not here is never guessed.
ASKS = (
    (r'\bhow\s+long\b|\bby\s+when\b|\bhow\s+many\s+days\b|\bdeadline\b|\btime\s+limit\b', ('day', 'week', 'month', 'year', 'hour', 'period', 'within', 'until', 'after')),
    (r'\bwhen\b|\bwhat\s+date\b|\bwhich\s+day\b', ('day', 'date', 'within', 'after', 'before', 'until')),
    (r'\bhow\s+much\b|\bwhat\s+amount\b|\bhow\s+many\b', ('amount', 'sum', 'total', 'equal')),
    (r'\bwhat\s+if\s+not\b|\bexcept\b|\bunless\b|\bexception\b|\bdoes\s+not\s+apply\b', ('unless', 'except', 'apply')),
    (r'\bliable\b|\bowe[sd]?\b|\bpenalt', ('liable', 'amount', 'equal', 'pay')),
    (r'\bwhat\s+does\b.*\bmean\b|\bdefin', ('means', 'mean', 'defined', 'definition')),
)
MARK = re.compile(r'^\s*(§\s*\d+[A-Za-z]?\.?|\(\s*[a-z0-9]{1,4}\s*\)|\d{1,3}\.(?=\s)|[a-z]\)(?=\s))\s*')


def _stem(word):
    for end, keep in (('ings', 4), ('ing', 4), ('ied', 3), ('ies', 3), ('ed', 4), ('es', 5), ('s', 4)):
        if word.endswith(end) and len(word) - len(end) >= keep:
            word = word[:-len(end)] + ('y' if end in ('ied', 'ies') else '')
            break
    return word


def words_of(text):
    return re.findall(r'[a-z0-9]+', str(text).casefold())


def terms(text):
    """The words of a text as they are matched: lower case, no stop words, a light stem ('days' and 'day' are one word)."""
    return [_stem(w) for w in words_of(text) if w not in STOP]


def asked(query):
    """The words a question's shape adds (ASKS), stemmed."""
    found = []
    for pattern, said in ASKS:
        if re.search(pattern, str(query).casefold()):
            found += [_stem(w) for w in said if _stem(w) not in found]
    return found


def split(text):
    """A page's text cut into places: a numbered paragraph (§ 12, (a), 1.) runs until the next mark or a blank line; other
    text is cut at blank lines. A section's mark is carried into its paragraphs' labels: § 12 then (a) is '§ 12(a)'.
    A line that is only a section's heading ('§ 3. Counting periods of days.') is a heading, not a place.
    Returns [{'label', 'mark', 'text', 'line' (where it starts, from 1)}]."""
    places = [];section = '';current = None
    def close():
        if current and current['text'].strip():
            current['text'] = re.sub(r'\s+', ' ', current['text']).strip();places.append(current)
    for n, line in enumerate(str(text).splitlines(), 1):
        if not line.strip():
            close();current = None;continue
        found = MARK.match(line)
        if found:
            close();mark = re.sub(r'\s+', '', found.group(1)).rstrip('.') if found.group(1).lstrip().startswith('§') else re.sub(r'\s+', '', found.group(1))
            body = line[found.end():]
            if mark.startswith('§'):
                section = mark.replace('§', '§ ')
                current = {'label': section, 'mark': mark, 'text': body, 'line': n, 'heading': True}
            else:
                current = {'label': (section + mark) if section else mark, 'mark': mark, 'text': body, 'line': n, 'heading': False}
            continue
        if current is None:current = {'label': '', 'mark': '', 'text': line, 'line': n, 'heading': False}
        else:current['text'] += ' ' + line
    close()
    out = []
    for place in places:            # a section's own line with nothing under it but its title is its heading, not a place
        if place.pop('heading') and len(terms(place['text'])) <= 4 and any(p['label'].startswith(place['label'] + '(') for p in places):continue
        out.append(place)
    return out


def excerpt(text, count=EXCERPT_WORDS):
    words = str(text).split()
    return ' '.join(words[:count]) + (' …' if len(words) > count else '')


def rank(query, passages, limit=LIMIT):
    """The places of these passages ranked for the query. passages: [{'text', and anything else, kept on each place}].
    Each query word a place carries scores how rare it is among the places here (places / places that carry it); a word
    the question's shape adds scores half that. Ties go to the place that carries more of the query's own words, then to
    reading order. Pure: no Kernel, no model, no float. Returns [{'rank', 'label', 'text', 'score' (a Fraction as text),
    'matched', **the passage's other fields}]."""
    cut = []
    for order, passage in enumerate(passages):
        for place in split(passage.get('text') or ''):
            cut.append({**place, 'order': order, 'terms': set(terms(place['text']))})
    out = []
    for n, (place, score_, matched) in enumerate(score(query, cut, limit), 1):
        passage = {k: v for k, v in passages[place['order']].items() if k != 'text'}
        out.append({**passage, 'rank': n, 'label': place['label'], 'text': place['text'], 'score': str(score_), 'matched': matched})
    return out


def score(query, places, limit=LIMIT):
    """The one ranking rule (rank() above, and 0.8.7's Library over its index, library_service): places already cut, each
    {'terms': its terms() as a set, 'order': its passage's reading order, 'line', and anything else}, scored for the query.
    Returns [(place, score as a Fraction, matched words)], best first, at most `limit`. Pure: no Kernel, no model, no float."""
    own = list(dict.fromkeys(terms(query)));extra = [w for w in asked(query) if w not in own]
    if not places or not (own or extra):return []
    count = len(places)
    def weight(word):
        df = sum(1 for place in places if word in place['terms'])
        return Fraction(count, df) if df else Fraction(0)
    weights = {w: weight(w) for w in own};weights.update({w: weight(w) * ASKED for w in extra})
    scored = []
    for place in places:
        matched = [w for w in own + extra if w in place['terms']]
        if not matched:continue
        total = sum((weights[w] for w in matched), Fraction(0))
        scored.append((-total, -sum(1 for w in matched if w in own), place['order'], place['line'], place, matched, total))
    scored.sort(key=lambda row: row[:4])
    return [(place, total, matched) for _, _, _, _, place, matched, total in scored[:limit]]


# ============================================================================================================ the desk

def passages(kernel, principal, query, namespaces=None):
    """The admitted, current pages the FTS5 search (references.search) finds for the query's words, in each collection
    (or only those named): [{'text', 'namespace', 'item', 'name', 'source_sha256', 'page_index', 'page_label', 'passage'}]."""
    def call(operation, arguments):
        answer = kernel.dispatch(operation, arguments, principal)
        if not answer.get('ok'):raise ValueError('%s could not be read: %s' % (operation, str((answer.get('error') or {}).get('message', ''))[:160]))
        return answer['result']
    words = list(dict.fromkeys(words_of(query) + asked(query) + terms(query)))
    asked_for = ' '.join(w for w in words if w not in STOP)[:300] or str(query)[:300]
    spaces = [ns['id'] for ns in call('intake.namespaces', {}).get('namespaces', ())]
    if namespaces:spaces = [ns for ns in spaces if ns in set(namespaces)]
    found = []
    for space in spaces:
        hits = call('references.search', {'namespace': space, 'query': asked_for, 'limit': SEARCH_LIMIT}).get('hits', ())
        for hit in hits:
            locator = hit.get('locator') or {}
            found.append({'text': str(hit.get('text') or ''), 'namespace': space, 'item': hit.get('item'), 'name': hit.get('name') or '',
                          'source_sha256': hit.get('source_sha256'), 'page_index': locator.get('page_index'),
                          'page_label': str(locator.get('page_label') or (int(locator['page_index']) + 1 if isinstance(locator.get('page_index'), int) else '')),
                          'passage': hit.get('id')})
    return found


def pin_args(kernel, principal, place):
    """What quotes.pin takes to pin this place as a quote (the owner's press), the region found on the page as quotes.pin
    finds it; None when the place is not on a PDF page or its words are not found there as one run."""
    from . import quotes
    if not isinstance(place.get('page_index'), int) or not place.get('item'):return None
    words = quotes.norm(place['text'])
    try:
        found, _ = quotes.page(kernel, principal, place['namespace'], place['item'], place['source_sha256'], place['page_index'])
    except (ValueError, OSError, KeyError):return None
    rect = quotes.located(found, words)
    if rect is None:return None
    args = {'namespace': place['namespace'], 'item': place['item'], 'source_sha256': place['source_sha256'], 'page_index': place['page_index'],
            'rect': rect, 'words': words}
    if place.get('label'):args['label'] = place['label']
    return args


def said(place):
    """One place as she says it: '1. Demoland_Tenancy_Act.pdf page 1, § 12(a) “Within 21 days after a tenancy ends, …”'."""
    where = '%s page %s' % (place.get('name') or 'an admitted file', place.get('page_label') or '?')
    return '%d. %s, %s“%s”' % (place['rank'], where, (place['label'] + ' ') if place.get('label') else '', excerpt(place['text']))


def find(kernel, principal, query, limit=LIMIT, namespace=None):
    """The card: {'query', 'terms', 'asked' (the words its shape added), 'places': rank() each with 'pin' (pin_args) and
    'words' (said), 'searched' (pages read), 'lines', 'ranking', 'model_calls': 0}. Nothing is written."""
    limit = max(1, min(int(limit or LIMIT), MOST))
    pages = passages(kernel, principal, query, [namespace] if namespace else None)
    places = rank(query, pages, limit)
    for place in places:
        place['pin'] = pin_args(kernel, principal, place);place['words'] = said(place)
    lines = [place['words'] for place in places] or ['Nothing on your admitted pages carries these words.']
    return {'query': str(query), 'terms': list(dict.fromkeys(terms(query))), 'asked': asked(query), 'places': places, 'searched': len(pages),
            'lines': lines, 'ranking': 'FTS5 pages (references.search), places ranked by the rarity of the words they carry; no model',
            'model_calls': 0}


def dispatch(kernel, op, args, principal):
    if op == 'places.find':return find(kernel, principal, args['query'], args.get('limit', LIMIT), args.get('namespace'))
    raise ValueError('Unknown places operation')
