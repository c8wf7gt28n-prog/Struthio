"""The phrasebook: the owner's own words, kept only when he says so (0.8.6 S7, "Kas's mind, no model"; lane A).

After a request she could not read by herself is settled (by the model's checked pick, or by his own button), she offers
once: "Keep “pop … up” as trace?". If he keeps it, the same words next time are read as he kept them, with no question
and no model (reading.read's KEPT route): asked once, never again for words he kept (design 4.1, rule 5).

    phrases.offer(kernel, principal, text, chosen, found=None)   the offer to show, or None (kept already, or struck)
    phrases.keep(kernel, principal, text, chosen, follows, shown)  his press: one phrasebook row
    phrases.kept(kernel, principal, world=None)                  what reading.read is given: the phrases in force, each
                                                                  pointed at the current revision when it follows it
    phrases.dispatch: phrases.list (read); phrases.keep, phrases.strike (approve: his press only); phrases.forget
                      (approve, and "*.forget" always asks: it leaves a tombstone)

Where it lives: rows of the existing instruction matrix (instruction_matrix.py), of the observed kind `reading`
(operation requests.read), told apart by their shape (PHRASE...). They are the owner's words: the matrix's examples for a
model, its patterns and its training-set export (the kit cutter) all leave them out (instruction_matrix.mine_only).

The rules, kept in the code:
  - nothing is promoted from silence: a row is written only by phrases.keep, which takes the approve scope (her principal
    holds read only, and no dial setting lists it), never by a read, a model answer or a repeated request;
  - a phrase never authorises a change: keep refuses any reading that is not a read or a move of the window, and a kept
    reading is a reading, so whatever it leads to still passes the dial (stacy_hand) exactly as typed words would;
  - a phrase that names a sheet with revisions either follows the current revision (FOLLOWS 'CURRENT': when a newer
    revision arrives and says it is current, the phrase moves to it and says so) or stays on the revision it was kept with
    ('THIS_REVISION'); he chooses which when he keeps it;
  - a struck phrase is never used and never offered again; forget removes the row and leaves a tombstone (its date and a
    digest, never its words).

0.8.7 B5 (your words, widened to sayings with slots; design 2.3 and 3.6): a READ reading the owner AGREES to (his Do, his
click on her question, or Remember) becomes rows here, in the same matrix, never a parallel store:

    a name row     (shape phrase:name:<key>)    his words for a thing: “the bench numbers” is “Rail Demo bench readings”
                                                 (fed to understand.inputs(names=...): rule 5's agreed name)
    a saying row   (shape phrase:saying:<key>)  his request with each step's words made a slot: “pull up where … came
                                                 from” means Trace. Next time the same saying, over the same thing or a new
                                                 one, is read by the desk with no model call (understand.by_sayings)

    phrases.agree(kernel, principal, text, steps, model_key=None)   his agreement: one name row a step, one saying row
    phrases.not_that(kernel, principal, verbs, model_key=None)      his correction: no row; it counts against the verb
    phrases.your_words(kernel, principal, model_key=None)          what READ is given: names, their dates, sayings, and
                                                                    the verbs dropped from the model's table
    phrases.fits(template, text)                                    where a saying's slots fall in a request (pure)
    phrases.strike(...) retires a name or a saying too (on screen: Retire); phrases.forget leaves a tombstone, as before

Rules: a reading he corrected or ignored makes no row; a saying never carries a change (a reading with a set step makes its
name rows only, and a saying is read again through understand_check, where any change is a model_pick proposal that always
asks); after five readings of a verb under one model key, more corrected than agreed drops that verb from the model's table
until the model key changes (the tally lives in the Kernel's settings, not in the phrasebook: a correction makes no row);
saying and name rows are phrase: rows, so the kit cutter (matrix.export) and the matrix's patterns leave them out.
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid

from . import instruction_matrix as M
from . import reading

SCHEMA = 'kas.phrase/1'
KIND = 'reading'                     # the observed kind of the matrix these rows belong to
OPERATION = 'requests.read'
SHAPE = M.PHRASE_SHAPE               # 'phrase:' + the words' key
TOMBSTONE = M.PHRASE_SHAPE + 'forgotten'
FOLLOWS = ('CURRENT', 'THIS_REVISION')
STATES = ('KEPT', 'STRUCK')
READ_FRAMES = ('VALUE', 'CHECK', 'SOLVE', 'MONEY', 'DATE', 'DAY')
NAVIGATES = ('traced', 'shown', 'side_by_side', 'tidy')
VERB = {'traced': 'trace', 'shown': 'select', 'side_by_side': 'side by side', 'tidy': 'tidy up'}
WORDS = {'offer': 'Keep “{words}” as {verb}?',
         'offer_revision': 'Keep “{words}” as {verb}? It names {title}: follow the current revision, or stay on this one?',
         'kept': 'Kept: “{words}” is {verb} from now on. Model calls: 0.',
         'moved': '“{was}” is no longer the current revision, so your phrase “{words}” now points at “{now}”.',
         'stays': 'Your phrase “{words}” stays on “{title}”, as you kept it.',
         'struck': 'Struck: I will not read “{words}” that way again, and I will not offer it again.',
         'forgotten': 'Forgotten. A tombstone says that a phrase was forgotten, and when; its words are gone.'}


def said_key(text):
    return reading.said_key(text)


def _changes(found):
    """Why a reading may not be kept ('' when it may): it must be a read, or moves of the window only."""
    if not isinstance(found, dict):return 'it is not a reading'
    frame = found.get('frame')
    if frame == 'DESK':
        bad = [g.get('template') for g in found.get('goals') or () if g.get('template') not in NAVIGATES]
        if bad or not found.get('goals'):return 'it would change something (%s)' % ', '.join(map(str, bad)) if bad else 'it names no goal'
        return ''
    if frame in READ_FRAMES:return ''
    return 'only a read, or a move of the window, can be kept'


def _titles(found):
    out = []
    for g in found.get('goals') or ():out += [v for v in (g.get('params') or {}).values() if isinstance(v, str)]
    for r in found.get('rows') or ():
        if r.get('title'):out.append(r['title'])
    return list(dict.fromkeys(out))


def _revisioned(found):
    return [t for t in _titles(found) if reading._mark(t)[0]]


def verb(chosen):
    found = chosen.get('reading') or {}
    goals = found.get('goals') or ()
    if found.get('frame') == 'DESK' and goals:return ' then '.join(VERB.get(g['template'], g['template']) for g in goals)
    return chosen.get('words') or 'that'


def _rows(db, owner, state=None):
    found = M.rows(db, owner, " AND shape LIKE ? AND shape!=?", (SHAPE + '%', TOMBSTONE), 5000)
    out = []
    for r in found:
        p = r['payload'] or {}
        if p.get('kind') != 'phrase':continue
        if state and p.get('state') != state:continue
        out.append({**r, 'phrase': p})
    return out


def _view(r):
    p = r['phrase']
    return {'id': r['id'], 'words': p.get('shown') or r['intent'], 'request': r['intent'], 'as': p.get('as'), 'verb': p.get('verb'),
            'follows': p.get('follows'), 'state': p.get('state'), 'kept': r['created'], 'changed': r['updated'], 'key': r['program'],
            'reading': p.get('reading'), 'kind': KIND}


def listing(kernel, principal):
    with kernel.db() as db:
        rows = _rows(db, principal.identity)
        tombs = M.rows(db, principal.identity, ' AND shape=?', (TOMBSTONE,), 5000)
        words = _word_rows(db, principal.identity)                     # 0.8.7 B5: names and sayings
    return {'schema': SCHEMA, 'phrases': [_view(r) for r in rows], 'tombstones': [{'id': t['id'], 'forgotten': t['created'],
                                                                                   'digest': (t['payload'] or {}).get('digest')} for t in tombs],
            'names': [_word_view(r) for r in words if r['payload'].get('kind') == 'name'],
            'sayings': [_word_view(r) for r in words if r['payload'].get('kind') == 'saying'],
            'dropped': list(dropped(kernel, principal)), 'kind': KIND, 'model_calls': 0}


def offer(kernel, principal, text, chosen, found=None):
    """What to offer after a request was settled by a pick: {'question', 'words', 'verb', 'revision_titles'}, or None when the
    same words are kept already, or the owner struck them (a struck phrase is never offered again), or the choice may not
    be kept (a change)."""
    if _changes(chosen.get('reading')):return None
    key = said_key(text)
    if not key:return None
    with kernel.db() as db:
        for r in _rows(db, principal.identity):
            if r['program'] == key:return None
    shown = (found and _shown(found)) or reading.plain(text)
    titles = _revisioned(chosen.get('reading') or {})
    words = WORDS['offer_revision'].format(words=shown, verb=verb(chosen), title='“%s”' % titles[0]) if titles else \
        WORDS['offer'].format(words=shown, verb=verb(chosen))
    return {'question': words, 'words': shown, 'verb': verb(chosen), 'revision_titles': titles, 'choices': list(FOLLOWS) if titles else ['CURRENT']}


def _shown(found):
    from .brief import shown_phrase
    return shown_phrase(found)


def keep(kernel, principal, text, chosen, follows='CURRENT', shown=''):
    """The owner's press: one phrase row. Refuses a reading that is not a read or a move of the window."""
    why = _changes(chosen.get('reading'))
    if why:raise ValueError('PHRASE_NOT_KEPT: %s; a phrase never carries a change' % why)
    if follows not in FOLLOWS:raise ValueError('PHRASE_FOLLOWS: CURRENT or THIS_REVISION')
    key = said_key(text)
    if not key:raise ValueError('PHRASE_EMPTY: no words to keep')
    found = dict(chosen['reading']);found['understood'] = chosen.get('words') or found.get('understood', '')
    payload = {'kind': 'phrase', 'schema': SCHEMA, 'reading': found, 'as': chosen.get('words'), 'verb': verb(chosen), 'follows': follows,
               'state': 'KEPT', 'shown': (shown or reading.plain(text))[:200], 'titles': _titles(found)}
    now = time.time()
    with kernel.db() as db:
        M.ensure(db)
        old = next((r for r in _rows(db, principal.identity) if r['program'] == key), None)
        if old is not None:
            db.execute('UPDATE instruction_matrix SET updated=?,intent=?,payload=?,mark=? WHERE id=? AND owner=?',
                       (now, reading.plain(text)[:600], json.dumps(payload, ensure_ascii=False), 'GOOD', old['id'], principal.identity))
            ident = old['id']
        else:
            ident = uuid.uuid4().hex
            db.execute('INSERT INTO instruction_matrix VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
                       (ident, principal.identity, now, now, reading.plain(text)[:600], key, SHAPE + key[:200], OPERATION, 'SUCCESS',
                        'kept by the owner', 'GOOD', None, json.dumps(payload, ensure_ascii=False)))
    return {'schema': SCHEMA, 'state': 'KEPT', 'id': ident, 'words': WORDS['kept'].format(words=payload['shown'], verb=payload['verb']),
            'follows': follows, 'model_calls': 0}


def strike(kernel, principal, ident):
    with kernel.db() as db:
        r = next((r for r in _rows(db, principal.identity) if r['id'] == ident), None)
        if r is None:
            w = next((w for w in _word_rows(db, principal.identity) if w['id'] == ident), None)      # 0.8.7 B5: Retire
            if w is not None:return _retire(db, principal, w)
        if r is None:raise ValueError('PHRASE_NOT_FOUND')
        p = dict(r['phrase']);p['state'] = 'STRUCK'
        db.execute('UPDATE instruction_matrix SET payload=?,updated=?,mark=? WHERE id=? AND owner=?',
                   (json.dumps(p, ensure_ascii=False), time.time(), 'BAD', ident, principal.identity))
    return {'schema': SCHEMA, 'state': 'STRUCK', 'id': ident, 'words': WORDS['struck'].format(words=p.get('shown') or r['intent'])}


def forget(kernel, principal, ident):
    with kernel.db() as db:
        M.ensure(db)
        count = M.forget_phrases(db, principal.identity, ident)
    if not count:raise ValueError('PHRASE_NOT_FOUND')
    return {'schema': SCHEMA, 'state': 'FORGOTTEN', 'rows': count, 'words': WORDS['forgotten']}


def _current(title, titles):
    """The current revision of the sheet `title` is a revision of, among `titles`: the one marked CURRENT with the latest
    revision mark, else the latest revision mark."""
    rev, _, stem = reading._mark(title)
    if not rev:return title
    same = [t for t in titles if reading._mark(t)[0] and reading._mark(t)[2].casefold() == stem.casefold()]
    if not same:return title
    order = lambda t: (len(reading._mark(t)[0]), reading._mark(t)[0])
    marked = [t for t in same if reading._mark(t)[1] == 'CURRENT']
    return max(marked or same, key=order)


def _repoint(found, swap):
    text = json.dumps(found, ensure_ascii=False)
    for was, now in swap.items():text = text.replace(json.dumps(was, ensure_ascii=False)[1:-1], json.dumps(now, ensure_ascii=False)[1:-1])
    return json.loads(text)


def kept(kernel, principal, world=None):
    """The phrases in force for reading.read's `kept`: [{'id', 'words' (the key), 'reading', 'follows', 'moved', 'note'}].
    A phrase that follows the current revision is pointed at it here, and says so; one kept on its revision stays."""
    with kernel.db() as db:
        rows = _rows(db, principal.identity, 'KEPT')
    return in_force(rows, world)


def in_force(rows, world=None):
    """kept() over rows already read (pure): each row's reading, re-pointed when it follows the current revision."""
    titles = [s.title for s in world.sheets] if world is not None else []
    out = []
    for r in rows:
        p = r['phrase'];found = dict(p.get('reading') or {})
        if _changes(found):continue                       # a row that would carry a change is never in force
        moved = [];note = ''
        shown = p.get('shown') or r.get('intent') or ''
        if titles:
            swap = {}
            for t in _revisioned(found):
                now = _current(t, titles)
                if p.get('follows') == 'CURRENT' and now != t:swap[t] = now;moved.append({'was': t, 'now': now})
            if swap:
                found = _repoint(found, swap)
                note = ' '.join(WORDS['moved'].format(was=m['was'], now=m['now'], words=shown) for m in moved)
            elif p.get('follows') == 'THIS_REVISION':
                held = [t for t in _revisioned(found) if _current(t, titles) != t]
                if held:note = WORDS['stays'].format(words=shown, title=held[0])
        if note:found['understood'] = (found.get('understood') or '') + ' (' + note + ')'
        out.append({'id': r['id'], 'words': r['program'], 'reading': found, 'follows': p.get('follows'), 'moved': moved, 'note': note,
                    'route': 'DESK' if found.get('frame') == 'DESK' else found.get('route') or found.get('frame')})
    return out


def digest(text):
    return hashlib.sha256(str(text).encode('utf-8')).hexdigest()


# == 0.8.7 B5 · your words: agreed READ readings become name and saying rows of this phrasebook ================================
NAME_SHAPE = SHAPE + 'name:'
SAYING_SHAPE = SHAPE + 'saying:'
WORD_KINDS = ('name', 'saying')
TALLY_KEY = 'phrases.read_tally.'     # the Kernel's settings: {model_key, verbs: {verb: {agreed, corrected}}}; no phrasebook row
TALLY_MOST = 5                        # readings of a verb (agreed + corrected) before more corrected than agreed drops it
SLOT_MOST = 8                         # words one slot of a saying may take
SLOT = '…'
MONTHS = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')
MEANS = {'show': 'Show', 'card': 'Open its card', 'trace': 'Trace', 'compare': 'Compare', 'doubt': 'Doubt', 'what if': 'What if',
         'set': 'Set', 'count': 'Count', 'value': 'Read its value', 'within': 'Check it holds', 'tidy': 'Tidy the desk'}
WORDS.update({
    'remembered': 'Remembered: “{shown}” means {means}.',
    'remembered_name': 'Remembered: “{words}” means “{title}”.',
    'agreed_on': 'your words, agreed {day}',
    'retired': 'Retired: I will not read “{shown}” that way again.',
    'not_that': 'Not that: I will not read these words this way again, and I remember nothing of it.',
    'dropped': 'My model read “{verb}” wrongly more often than rightly for you, so I no longer offer it that verb.',
    'conflict': 'Two of your sayings read this differently, so which you meant is yours to say:',
    'conflict_after': 'Your sayings {sayings} both fit these words. Retire the one you did not mean, or I will ask again.',
})


def _verbs():
    from . import understand
    return understand.VERBS


def day_words(iso):
    """'20 Nov' for '2026-11-20' (the card's 'your words, agreed 20 Nov')."""
    try:
        y, m, d = (int(x) for x in str(iso)[:10].split('-'))
        return '%d %s' % (d, MONTHS[m - 1])
    except (ValueError, IndexError):
        return ''


def _word_rows(db, owner):
    """The name and saying rows (any state), newest change first."""
    found = M.rows(db, owner, " AND (shape LIKE ? OR shape LIKE ?)", (NAME_SHAPE + '%', SAYING_SHAPE + '%'), 5000)
    out = [r for r in found if (r['payload'] or {}).get('kind') in WORD_KINDS]
    return sorted(out, key=lambda r: -(r['updated'] or 0))


def _word_view(r):
    p = r['payload']
    view = {'id': r['id'], 'kind': p.get('kind'), 'state': p.get('state'), 'agreed': p.get('agreed'), 'changed': r['updated']}
    if p.get('kind') == 'name':view.update(words=p.get('words'), thing=p.get('thing'), title=p.get('title'))
    else:view.update(words=p.get('shown'), means=p.get('means'), steps=p.get('steps'))
    return view


def _template(text, steps):
    """A saying from an agreed reading: (items, plan, shown), or None when it cannot be one. `items` are the request's words
    in order, ['lit', stem] for his own fixed words and ['slot', j] where a step's words (or a value) stood; `plan` is each
    step's verb with the slot its words fill (a back-reference step keeps its words as said). At least one fixed word that
    carries meaning is needed: a saying of slots alone would fit every request."""
    plan, spans = [], []
    for s in steps:
        row = {'verb': s['verb']}
        if s['verb'] == 'tidy':plan.append(row);continue
        if str(s.get('handle') or '').startswith('S'):
            row.update(handle=s['handle'], words=s['words']);plan.append(row);continue
        row['slot'] = len(spans);spans.append(tuple(s['at']))
        if s.get('column'):row.update(column=s['column'], column_label=s.get('column_label') or '')
        if s.get('value') and s.get('value_at'):row['value_slot'] = len(spans);spans.append(tuple(s['value_at']))
        plan.append(row)
    if any(a < d and c < b for n, (a, b) in enumerate(spans) for (c, d) in spans[n + 1:]):return None
    items, seen, meaning = [], set(), False
    for t in reading.tokens(text):
        inside = next((j for j, (a, b) in enumerate(spans) if a <= t.at[0] and t.at[1] <= b), None)
        if inside is None:
            if any(a < t.at[1] and t.at[0] < b for a, b in spans):return None
            items.append(['lit', t.stem]);meaning = meaning or t.low not in reading.STOP
        elif inside not in seen:
            seen.add(inside);items.append(['slot', inside])
    if not meaning or len(seen) != len(spans):return None
    shown, pos = [], 0
    for a, b in sorted(spans):
        shown.append(text[pos:a]);shown.append(SLOT);pos = b
    shown.append(text[pos:])
    return items, plan, reading.plain(''.join(shown))


def fits(template, text, most=4):
    """Where a saying's slots fall in `text`: [{slot: (start, end)}], every way it fits the whole request (at most `most`).
    His fixed words must stand in order, by their stems; each slot takes one to SLOT_MOST words, one of which carries
    meaning. Pure."""
    toks = reading.tokens(reading.plain(text)[:reading.TEXT]);out = []

    def go(k, p, slots):
        if len(out) >= most:return
        if k == len(template):
            if p == len(toks):out.append({j: (toks[a].at[0], toks[b - 1].at[1]) for j, (a, b) in slots.items()})
            return
        kind, what = template[k]
        if kind == 'lit':
            if p < len(toks) and toks[p].stem == what:go(k + 1, p + 1, slots)
            return
        for q in range(p + 1, min(len(toks), p + SLOT_MOST) + 1):
            if not any(t.low not in reading.STOP for t in toks[p:q]):continue
            slots[what] = (p, q);go(k + 1, q, slots);del slots[what]
    go(0, 0, {})
    return out


def _upsert(db, owner, shape, key, intent, payload, now):
    old = db.execute('SELECT id FROM instruction_matrix WHERE owner=? AND shape=?', (owner, shape)).fetchone()
    body = json.dumps(payload, ensure_ascii=False)
    if old is not None:
        db.execute('UPDATE instruction_matrix SET updated=?,intent=?,program=?,payload=?,mark=? WHERE id=? AND owner=?',
                   (now, intent[:600], key, body, 'GOOD', old[0], owner))
        return old[0]
    ident = uuid.uuid4().hex
    db.execute('INSERT INTO instruction_matrix VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
               (ident, owner, now, now, intent[:600], key, shape, OPERATION, 'SUCCESS', 'agreed by the owner', 'GOOD', None, body))
    return ident


def _agreed_steps(text, steps):
    """The steps of an agreed reading, checked again here: a verb of READ's table, his words where the reading says they
    stood in his request, a thing. Raises on anything else."""
    from . import understand_check
    verbs = _verbs();out = []
    for s in steps or ():
        if not isinstance(s, dict) or s.get('verb') not in verbs:raise ValueError('WORDS_VERB: not a verb of the reading table')
        if s['verb'] == 'tidy':out.append({'verb': 'tidy'});continue
        words = str(s.get('words') or '');at = s.get('at')
        if not words.strip() or not isinstance(at, (list, tuple)) or len(at) != 2:raise ValueError('WORDS_SHAPE: a step needs its words and where they stood')
        if tuple(at) not in understand_check.places(text, words):raise ValueError('WORDS_NOT_SAID: “%s” is not where the reading says' % words[:60])
        if s.get('value'):
            vat = s.get('value_at')
            if not isinstance(vat, (list, tuple)) or tuple(vat) not in understand_check.places(text, s['value']):raise ValueError('WORDS_NOT_SAID: the value')
        if not str(s.get('thing') or ''):raise ValueError('WORDS_THING: a step names no thing')
        out.append({k: s.get(k) for k in ('verb', 'handle', 'thing', 'title', 'words', 'at', 'column', 'column_label', 'value', 'value_at')})
    if not out:raise ValueError('WORDS_NOTHING: no step to remember')
    return out


def agree(kernel, principal, text, steps, model_key=None, today=None, tally=True):
    """His agreement to a reading (Do, a click on her question, Remember): one name row a step (his words for the thing)
    and one saying row (his request with each step's words a slot), upserted by key; and one 'agreed' a verb on the tally.
    A reading with a change in it makes its name rows only: a saying never carries a change."""
    from datetime import date
    text = reading.plain(text)[:reading.TEXT]
    steps = _agreed_steps(text, steps)
    day = (today or date.today()).isoformat() if not isinstance(today, str) else today
    now = time.time();owner = principal.identity;names = [];saying = None
    with kernel.db() as db:
        M.ensure(db)
        for s in steps:
            if s['verb'] == 'tidy' or str(s.get('handle') or '').startswith('S'):continue
            key = said_key(s['words'])
            if not key:continue
            payload = {'kind': 'name', 'schema': SCHEMA, 'words': s['words'], 'thing': s['thing'], 'title': s.get('title') or '',
                       'state': 'KEPT', 'agreed': day}
            names.append(_upsert(db, owner, NAME_SHAPE + key[:200], key, s['words'], payload, now))
        made = None if any(s['verb'] == 'set' for s in steps) else _template(text, steps)
        if made is not None:
            items, plan, shown = made
            key = ' '.join(SLOT if k == 'slot' else w for k, w in items)
            means = ', then '.join(MEANS.get(s['verb'], s['verb']) for s in steps)
            payload = {'kind': 'saying', 'schema': SCHEMA, 'template': items, 'steps': plan, 'shown': shown, 'means': means,
                       'state': 'KEPT', 'agreed': day}
            saying = _upsert(db, owner, SAYING_SHAPE + hashlib.sha256(key.encode('utf-8')).hexdigest()[:32], key, text, payload, now)
            words = WORDS['remembered'].format(shown=shown, means=means)
        else:
            first = next((s for s in steps if s.get('words') and not str(s.get('handle') or '').startswith('S')), steps[0])
            words = WORDS['remembered_name'].format(words=first.get('words') or '', title=first.get('title') or '')
    if tally:_count(kernel, principal, [s['verb'] for s in steps], 'agreed', model_key)      # a click on her question is not counted
    return {'schema': SCHEMA, 'state': 'AGREED', 'names': names, 'saying': saying, 'words': words, 'model_calls': 0}


def not_that(kernel, principal, verbs, model_key=None):
    """His correction of a model's reading: no row anywhere in the phrasebook; one 'corrected' a verb on the tally."""
    known = _verbs()
    verbs = [v for v in verbs or () if v in known]
    _count(kernel, principal, verbs, 'corrected', model_key)
    return {'schema': SCHEMA, 'state': 'NOT_THAT', 'rows': 0, 'words': WORDS['not_that'], 'dropped': list(dropped(kernel, principal, model_key))}


def _retire(db, principal, w):
    p = dict(w['payload']);p['state'] = 'STRUCK'
    db.execute('UPDATE instruction_matrix SET payload=?,updated=?,mark=? WHERE id=? AND owner=?',
               (json.dumps(p, ensure_ascii=False), time.time(), 'BAD', w['id'], principal.identity))
    return {'schema': SCHEMA, 'state': 'STRUCK', 'id': w['id'], 'kind': p.get('kind'),
            'words': WORDS['retired'].format(shown=p.get('shown') or p.get('words') or '')}


def _model_key(kernel):
    try:
        from .agent_loop import model_key
        return model_key(kernel)
    except Exception:  # noqa: BLE001 - no model known: nothing to count against
        return None


def _tally_key(principal):
    return TALLY_KEY + hashlib.sha256(str(principal.identity).encode('utf-8')).hexdigest()[:16]


def _tally(db, principal):
    row = db.execute('SELECT value FROM settings WHERE key=?', (_tally_key(principal),)).fetchone()
    held = json.loads(row[0]) if row else {}
    return held if isinstance(held, dict) else {}


def _count(kernel, principal, verbs, which, model_key=None):
    """One reading of each verb, agreed or corrected, under the model key (a new key starts the tally again)."""
    key = model_key if model_key is not None else _model_key(kernel)
    if not key or not verbs:return None
    try:
        with kernel.db() as db:
            held = _tally(db, principal)
            if held.get('model_key') != key:held = {'model_key': key, 'verbs': {}}
            for v in dict.fromkeys(verbs):
                c = held['verbs'].setdefault(v, {'agreed': 0, 'corrected': 0});c[which] += 1
            db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)', (_tally_key(principal), json.dumps(held, sort_keys=True)))
    except Exception:  # noqa: BLE001 - no settings table: nothing is counted, nothing is dropped
        return None
    return held


def dropped(kernel, principal, model_key=None):
    """The verbs taken out of the model's table for this owner and this model key: after TALLY_MOST readings of a verb,
    more corrected than agreed. A new model key gives every verb back."""
    key = model_key if model_key is not None else _model_key(kernel)
    if not key:return ()
    try:
        with kernel.db() as db:held = _tally(db, principal)
    except Exception:  # noqa: BLE001 - no settings table: nothing dropped
        return ()
    if held.get('model_key') != key:return ()
    return tuple(sorted(v for v, c in (held.get('verbs') or {}).items()
                        if int(c.get('agreed', 0)) + int(c.get('corrected', 0)) >= TALLY_MOST and int(c.get('corrected', 0)) > int(c.get('agreed', 0))))


def your_words(kernel, principal, model_key=None):
    """What READ is given from the phrasebook: {'names': {key: thing id}, 'agreed': {key: '20 Nov'}, 'sayings': [...] newest
    first, 'dropped': verbs}. Retired rows are not in force."""
    with kernel.db() as db:
        rows = _word_rows(db, principal.identity)
    names, agreed, sayings = {}, {}, []
    for r in rows:
        p = r['payload']
        if p.get('state') != 'KEPT':continue
        if p['kind'] == 'name' and r['program'] not in names:
            names[r['program']] = p.get('thing');agreed[r['program']] = day_words(p.get('agreed'))
        elif p['kind'] == 'saying' and p.get('template') and p.get('steps'):
            sayings.append({'id': r['id'], 'template': p['template'], 'steps': p['steps'], 'shown': p.get('shown') or '',
                            'means': p.get('means') or '', 'agreed': day_words(p.get('agreed'))})
    return {'names': names, 'agreed': agreed, 'sayings': sayings, 'dropped': dropped(kernel, principal, model_key)}
# == end 0.8.7 B5 ==============================================================================================================


ID = {'type': 'string', 'pattern': '^[0-9a-f]{32}$', 'maxLength': 32}
_READING = {'type': 'object'}
FIELDS = {
    'phrases.list': ({}, []),
    'phrases.keep': ({'text': {'type': 'string', 'minLength': 1, 'maxLength': 600},
                      'chosen': {'type': 'object', 'properties': {'words': {'type': 'string', 'maxLength': 400}, 'reading': _READING},
                                 'required': ['reading']},
                      'follows': {'type': 'string', 'enum': list(FOLLOWS)}, 'shown': {'type': 'string', 'maxLength': 200}}, ['text', 'chosen']),
    'phrases.strike': ({'id': ID}, ['id']),
    'phrases.forget': ({'id': ID}, ['id']),
    # 0.8.7 B5: his agreement to a READ reading (name and saying rows), and his correction (no row: the verb's tally only)
    'phrases.agree': ({'text': {'type': 'string', 'minLength': 1, 'maxLength': 600},
                       'steps': {'type': 'array', 'minItems': 1, 'maxItems': 4, 'items': {'type': 'object'}},
                       'model_key': {'type': 'string', 'maxLength': 200}, 'tally': {'type': 'boolean'}}, ['text', 'steps']),
    'phrases.not_that': ({'verbs': {'type': 'array', 'maxItems': 4, 'items': {'type': 'string', 'maxLength': 16}},
                          'model_key': {'type': 'string', 'maxLength': 200}}, ['verbs']),
}
SCOPES = {'phrases.list': 'read', 'phrases.keep': 'approve', 'phrases.strike': 'approve', 'phrases.forget': 'approve',
          'phrases.agree': 'approve', 'phrases.not_that': 'approve'}       # 0.8.7 B5: agree and not_that are his presses only


def dispatch(kernel, op, args, principal):
    if op == 'phrases.agree':return agree(kernel, principal, args['text'], args['steps'], args.get('model_key') or None, tally=args.get('tally', True) is not False)   # 0.8.7 B5
    if op == 'phrases.not_that':return not_that(kernel, principal, args['verbs'], args.get('model_key') or None)         # 0.8.7 B5
    if op == 'phrases.list':return listing(kernel, principal)
    if op == 'phrases.keep':return keep(kernel, principal, args['text'], args['chosen'], args.get('follows', 'CURRENT'), args.get('shown', ''))
    if op == 'phrases.strike':return strike(kernel, principal, args['id'])
    if op == 'phrases.forget':return forget(kernel, principal, args['id'])
    raise ValueError('Unknown phrasebook operation')
