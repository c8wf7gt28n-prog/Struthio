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
    return {'schema': SCHEMA, 'phrases': [_view(r) for r in rows], 'tombstones': [{'id': t['id'], 'forgotten': t['created'],
                                                                                   'digest': (t['payload'] or {}).get('digest')} for t in tombs],
            'kind': KIND, 'model_calls': 0}


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
}
SCOPES = {'phrases.list': 'read', 'phrases.keep': 'approve', 'phrases.strike': 'approve', 'phrases.forget': 'approve'}


def dispatch(kernel, op, args, principal):
    if op == 'phrases.list':return listing(kernel, principal)
    if op == 'phrases.keep':return keep(kernel, principal, args['text'], args['chosen'], args.get('follows', 'CURRENT'), args.get('shown', ''))
    if op == 'phrases.strike':return strike(kernel, principal, args['id'])
    if op == 'phrases.forget':return forget(kernel, principal, args['id'])
    raise ValueError('Unknown phrasebook operation')
