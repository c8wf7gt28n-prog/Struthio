"""Pinned quotes (0.8.6 S6, "Kas's mind, no model", lane C): the exact words of an admitted page, kept with where they
stand, so a rule can rest on them and nothing can be cited without its page.

A pinned quote is a Project Desk record (kind 'quote', schema ledger.quote/1, on screen "pinned quote"): the exact words
(spaces as one), the page they stand on (page_index, from 0), the region of the page they were found in (rect, the parts
of the page from its top left corner, as arc.pdf-citation/1 gives a region), the admitted file (its collection, item, name
and SHA-256: the fingerprint of the file), the citation (arc.pdf-citation/1), a fingerprint of all four, your label (for
example "§ 12(a)"), set_by 'owner' and state IN.

It is pinned only by your press (quotes.pin, execute) and only when its words are found, word for word, in that region of
that page of an admitted file: otherwise QUOTE_NOT_ON_PAGE. So no invented statute or case can stand on the desk.

Its state is computed on read, never stored. A source's newer revision is a file of the same name admitted in the same
collection after it (the collection admits one file under a name at a time, so the one admitted now is the source as it
stands):

  CURRENT   the words stand in the same region of the same page of the file admitted now (the very same file, or a newer
            revision that kept them there);
  MOVED     the same words stand elsewhere in the file admitted now (another place on the page, or another page): you
            rebind them (quotes.rebind, approve, always asks);
  GONE      the words are found nowhere in the file admitted now, or no file of that name is admitted.

A rule resting on a quote that is not CURRENT goes to recheck and is not applied (rules.py). Taking a revision back (its
admission revoked, the earlier file admitted again) makes the quotes current again, since nothing was stored.

  quotes.pin     {namespace, item, source_sha256, page_index, rect, words, label?}   execute   your press
  quotes.list    {all?, item?}                                                     read      each with its state now
  quotes.get     {id}                                                              read      the quote, its state, history
  quotes.check   {id?}                                                             read      states against the files now
  quotes.rebind  {id, expected_revision}                                           approve   ALWAYS_ASKS; a MOVED quote
                                                                                             (or one CURRENT in a newer
                                                                                             revision) bound to where its
                                                                                             words stand now

A page's words are read from the admitted file (its native text layer, the same reading references.pdf.page gives); an
admitted file never changes under its SHA-256, so a page read once is kept for the process. Reading a page writes no
record. Region geometry is the PDF layer's own (parts of a page); the words are compared exactly, as text.
"""
from __future__ import annotations

from . import project_desk as records

KIND = 'quote'
SCHEMA = 'ledger.quote/1'
SHOWN = 'pinned quote'
CURRENT, MOVED, GONE = 'CURRENT', 'MOVED', 'GONE'
STATES = (CURRENT, MOVED, GONE)
STATE_WORDS = {CURRENT: 'current', MOVED: 'moved', GONE: 'gone'}
MAX_PAGES = 64                # pages of a newer revision searched for moved words
PAD = 0.002                   # the margin a moved quote's new region is given around its words

_ID = {'type': 'string', 'pattern': '^[a-f0-9]{32}$'}
_SHA = {'type': 'string', 'pattern': '^[a-f0-9]{64}$'}
_RECT = {'type': 'array', 'items': {'type': 'number', 'minimum': 0, 'maximum': 1}, 'minItems': 4, 'maxItems': 4}
FIELDS = {
    'quotes.pin': ({'namespace': _ID, 'item': _ID, 'source_sha256': _SHA, 'page_index': {'type': 'integer', 'minimum': 0, 'maximum': 511},
                    'rect': _RECT, 'words': {'type': 'string', 'minLength': 1, 'maxLength': 2000},
                    'label': {'type': 'string', 'minLength': 1, 'maxLength': 80}},
                   ['namespace', 'item', 'source_sha256', 'page_index', 'rect', 'words']),
    'quotes.list': ({'all': {'type': 'boolean'}, 'item': _ID}, []),
    'quotes.get': ({'id': records.ID}, ['id']),
    'quotes.check': ({'id': records.ID}, []),
    'quotes.rebind': ({'id': records.ID, 'expected_revision': records.REV}, ['id', 'expected_revision']),
}
WRITES = ('quotes.pin', 'quotes.rebind')
SCOPES = {'quotes.pin': 'execute', 'quotes.rebind': 'approve', 'quotes.list': 'read', 'quotes.get': 'read', 'quotes.check': 'read'}
OBSERVERS = ('quotes.list', 'quotes.get', 'quotes.check')

# Her words about a pinned quote (scanned by mind_words.check).
WORDS = {
    'current': '“{label}” stands where you pinned it.',
    'current_newer': '“{label}” stands in the same place in the revision admitted now.',
    'moved': '“{label}” stands elsewhere in the revision admitted now. Rebind it to use it.',
    'gone': '“{label}” is not in the revision admitted now. A rule resting on it goes to recheck.',
    'unadmitted': '“{label}”: no file named “{name}” is admitted in its collection now.',
    'not_on_page': 'Those words are not in that region of that page.',
    'pinned': 'Pinned: “{label}”.',
}


def _register():
    from . import mind_words
    mind_words.register('quotes', WORDS)


_register()


# ---- the words of a page ----------------------------------------------------------------------------------------------------

_PAGES = {}                   # (source_sha256, page_index) -> (words, page_count): a file never changes under its SHA-256


def norm(text):
    """Words as one line: every run of spaces or line breaks as one space."""
    return ' '.join(str(text).split())


def page(kernel, principal, namespace, item, sha, index):
    """(words, page_count) of one page of an admitted file: words [{'text', 'rect'}] in reading order. Refused when the file
    is not admitted now or the page is not in it."""
    key = (sha, index)
    if key in _PAGES:return _PAGES[key]
    from . import intake_service as intake, pdf_service
    from sdk.cli.arc1cli import pdf_evidence as pdf
    with kernel.db() as db:
        ns, found, _raw, _decision = pdf_service.original(db, {'namespace': namespace, 'item': item, 'source_sha256': sha}, principal.identity)
    result = pdf.bounded('page', intake.vault(ns).path(found['sha256']), found['sha256'], index)
    words = tuple({'text': w['text'], 'rect': list(w['rect'])} for w in ((result.get('native') or {}).get('words') or ()))
    value = (words, int(result.get('page_count') or 1))
    if len(_PAGES) > 256:_PAGES.clear()
    _PAGES[key] = value
    return value


def _inside(rect, word):
    """Whether a word's centre lies in the region (the rule references.pdf uses for a selection)."""
    x, y, w, h = rect;r = word['rect']
    cx = r[0] + r[2] / 2;cy = r[1] + r[3] / 2
    return x <= cx <= x + w and y <= cy <= y + h


def _find(tokens, needle):
    """The first index where `needle` (a list of words) stands in `tokens`, or -1."""
    n = len(needle)
    if not n:return -1
    for i in range(len(tokens) - n + 1):
        if tokens[i:i + n] == needle:return i
    return -1


def in_region(words, rect, quote_words):
    """Whether the quote's words stand, word for word and in order, among the words whose centres lie in the region."""
    tokens = [w['text'] for w in words if _inside(rect, w)]
    return _find(tokens, norm(quote_words).split()) >= 0


def located(words, quote_words):
    """The region of the first place the quote's words stand on this page ([x, y, w, h], padded), or None."""
    needle = norm(quote_words).split();at = _find([w['text'] for w in words], needle)
    if at < 0:return None
    rects = [w['rect'] for w in words[at:at + len(needle)]]
    x0 = max(0, min(r[0] for r in rects) - PAD);y0 = max(0, min(r[1] for r in rects) - PAD)
    x1 = min(1, max(r[0] + r[2] for r in rects) + PAD);y1 = min(1, max(r[1] + r[3] for r in rects) + PAD)
    return [round(x0, 6), round(y0, 6), round(x1 - x0, 6), round(y1 - y0, 6)]


# ---- the record ----------------------------------------------------------------------------------------------------------

def fingerprint(source_sha, index, rect, words):
    return records.digest({'source_sha256': source_sha, 'page_index': index, 'rect': rect, 'words': norm(words)})


def _all(db, principal):
    records.ensure(db)
    ids = [row[0] for row in db.execute('SELECT id FROM desk_records WHERE owner=? AND kind=? ORDER BY rowid', (principal.identity, KIND))]
    return [records.read(db, KIND, ident, principal) for ident in ids]


def read(kernel, principal, ident):
    with kernel.db() as db:
        records.ensure(db);return records.read(db, KIND, ident, principal)


def every(kernel, principal):
    with kernel.db() as db:return _all(db, principal)


def pin(kernel, args, principal):
    """Your press: the words pinned where they stand. QUOTE_NOT_ON_PAGE unless they are found, word for word, in that
    region of that page of the admitted file. Pinning the same words at the same place again gives the quote kept."""
    from sdk.cli.arc1cli import pdf_evidence as pdf
    from . import intake_service as intake
    words = norm(args['words'])
    if not words:raise ValueError('QUOTE_WORDS: say the exact words')
    try:citation = pdf.citation(args['namespace'], args['item'], args['source_sha256'], args['page_index'], args['rect'])
    except ValueError as exc:raise ValueError('QUOTE_REGION: %s' % exc) from None
    try:found, count = page(kernel, principal, args['namespace'], args['item'], args['source_sha256'], args['page_index'])
    except ValueError as exc:raise ValueError('QUOTE_NOT_ON_PAGE: that page of an admitted file cannot be read (%s)' % str(exc)[:120]) from None
    if not in_region(found, citation['rect'], words):raise ValueError('QUOTE_NOT_ON_PAGE: ' + WORDS['not_on_page'])
    with kernel.db() as db:
        records.ensure(db)                          # begins the write transaction (BEGIN IMMEDIATE)
        item = intake.load(db, 'items', args['item'])
        mark = fingerprint(args['source_sha256'], args['page_index'], citation['rect'], words)
        kept = next((q for q in _all(db, principal) if q.get('fingerprint') == mark), None)
        if kept is not None:return kept
        value = records.new(KIND, principal, schema=SCHEMA, key=mark, label=norm(args.get('label') or words[:60]), words=words,
                            source={'namespace': args['namespace'], 'item': args['item'], 'name': item['name'], 'source_sha256': args['source_sha256']},
                            page_index=args['page_index'], rect=citation['rect'], citation=citation, fingerprint=mark, set_by='owner', state='IN')
        return records.write(db, value, principal, 'QUOTE_PINNED')


# ---- its state now, computed on read ------------------------------------------------------------------------------------------

def _admitted_now(kernel, source):
    """The item admitted now under the quote's file name in its collection, or None."""
    from . import intake_service as intake
    with kernel.db() as db:
        try:
            row = db.execute('SELECT item FROM intake_catalog WHERE ns=? AND name=?', (source['namespace'], source['name'])).fetchone()
            return intake.load(db, 'items', row[0]) if row else None
        except Exception:                     # no collection store yet, or the item cannot be read: nothing is admitted
            return None


def state(kernel, principal, quote):
    """{'state': CURRENT | MOVED | GONE, 'words' (her sentence), 'revision': 'SAME' | 'NEWER' | None, 'now': where the
    words stand now ({namespace, item, name, source_sha256, page_index, rect}) or None}."""
    source = quote['source'];label = quote.get('label') or quote['words'][:60]
    now = _admitted_now(kernel, source)
    if now is None:
        return {'state': GONE, 'revision': None, 'now': None, 'words': WORDS['unadmitted'].format(label=label, name=source['name'])}
    here = {'namespace': source['namespace'], 'item': now['id'], 'name': now['name'], 'source_sha256': now['sha256']}
    if now['id'] == source['item'] and now['sha256'] == source['source_sha256']:
        return {'state': CURRENT, 'revision': 'SAME', 'now': {**here, 'page_index': quote['page_index'], 'rect': quote['rect']},
                'words': WORDS['current'].format(label=label)}
    try:
        first, count = page(kernel, principal, source['namespace'], now['id'], now['sha256'], 0)
        if quote['page_index'] < count:
            words = first if quote['page_index'] == 0 else page(kernel, principal, source['namespace'], now['id'], now['sha256'], quote['page_index'])[0]
            if in_region(words, quote['rect'], quote['words']):
                return {'state': CURRENT, 'revision': 'NEWER', 'now': {**here, 'page_index': quote['page_index'], 'rect': quote['rect']},
                        'words': WORDS['current_newer'].format(label=label)}
        for index in range(min(count, MAX_PAGES)):
            words = first if index == 0 else page(kernel, principal, source['namespace'], now['id'], now['sha256'], index)[0]
            place = located(words, quote['words'])
            if place:
                return {'state': MOVED, 'revision': 'NEWER', 'now': {**here, 'page_index': index, 'rect': place},
                        'words': WORDS['moved'].format(label=label)}
    except ValueError:
        pass                                  # the revision admitted now cannot be read: its words are not found
    return {'state': GONE, 'revision': 'NEWER', 'now': None, 'words': WORDS['gone'].format(label=label)}


def states(kernel, principal, quotes=None):
    """{id: state(...)} for the quotes given, or every quote that is IN."""
    quotes = [q for q in every(kernel, principal) if q.get('state') == 'IN'] if quotes is None else quotes
    return {q['id']: state(kernel, principal, q) for q in quotes}


def rebind(kernel, args, principal):
    """Your approval: a quote whose words stand elsewhere (or in the same place of a newer revision) bound to where they
    stand now, as a new revision of the same record. A gone quote cannot be rebound: pin the new words."""
    quote = read(kernel, principal, args['id'])
    now = state(kernel, principal, quote)
    if now['state'] == GONE:raise ValueError('QUOTE_GONE: its words are not in the revision admitted now; pin the new words')
    if now['revision'] == 'SAME':raise ValueError('QUOTE_NOT_MOVED: it stands where you pinned it')
    from sdk.cli.arc1cli import pdf_evidence as pdf
    place = now['now']
    citation = pdf.citation(place['namespace'], place['item'], place['source_sha256'], place['page_index'], place['rect'])
    with kernel.db() as db:
        records.ensure(db)
        value = records.read(db, KIND, args['id'], principal);expected = args['expected_revision']
        records.edit(value, expected)
        mark = fingerprint(place['source_sha256'], place['page_index'], citation['rect'], value['words'])
        value.update(source={k: place[k] for k in ('namespace', 'item', 'name', 'source_sha256')}, page_index=place['page_index'],
                     rect=citation['rect'], citation=citation, rebound_from=value['fingerprint'], fingerprint=mark, key=mark)
        return records.write(db, value, principal, 'QUOTE_REBOUND', expected=expected)


def dispatch(kernel, op, args, principal):
    if op == 'quotes.pin':
        value = pin(kernel, args, principal)
        return {'quote': value, 'state': CURRENT, 'words': WORDS['pinned'].format(label=value['label']), 'model_calls': 0}
    if op == 'quotes.rebind':
        value = rebind(kernel, args, principal)
        return {'quote': value, 'state': CURRENT, 'model_calls': 0}
    if op == 'quotes.list':
        rows = [q for q in every(kernel, principal) if args.get('all') or q.get('state') == 'IN']
        if args.get('item'):rows = [q for q in rows if q['source']['item'] == args['item']]
        return {'quotes': [{**q, 'now': state(kernel, principal, q)} for q in rows], 'shown': SHOWN, 'model_calls': 0}
    if op == 'quotes.get':
        with kernel.db() as db:
            records.ensure(db);value = records.read(db, KIND, args['id'], principal);history = records.history(db, value)
        return {'quote': value, 'now': state(kernel, principal, value), 'history': history, 'model_calls': 0}
    if op == 'quotes.check':
        rows = [read(kernel, principal, args['id'])] if args.get('id') else [q for q in every(kernel, principal) if q.get('state') == 'IN']
        found = [{'id': q['id'], 'label': q['label'], 'words': q['words'], **state(kernel, principal, q)} for q in rows]
        counts = {s: sum(1 for f in found if f['state'] == s) for s in STATES}
        from . import rules
        waiting = rules.resting_on([f['id'] for f in found if f['state'] != CURRENT], kernel, principal)
        return {'quotes': found, 'counts': counts, 'rules_to_recheck': waiting, 'model_calls': 0}
    raise ValueError('Unknown quote operation')
