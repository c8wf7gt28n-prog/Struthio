"""Condition cards (HATCH AGENT-01): a result bound to the exact words it was calculated from.

CONTRACT (registered by the integrator; the implementer fills this module without changing names, arguments or shapes).

A condition is a Project Desk record (kind 'condition', schema ledger.condition/1) in the existing desk store:
  document, document_revision, inputs [{block (block id), index, start, end, text, value, unit}], expression ('sum' now),
  result {value, unit, text}, method (the helper names used), assignment (agent assignment id or None),
  result_block (the document block id that holds the written result paragraph), state CURRENT | STALE | BROKEN, reason,
  checked_at, origin.
State rules: CURRENT while every input span still reads the same text at the same block; STALE when any input's words
changed, moved or vanished (the owner edited the page); BROKEN when the result paragraph itself is gone. A recheck reads
the current revision again, re-extracts, recomputes, rewrites the result paragraph through documents.edit (bound to the
result block's current words) and the card is CURRENT again on the new revision. Old revisions stay in desk_history.

Operations:
  conditions.list   {document?}  -> {conditions:[summaries]}            read
  conditions.get    {id}         -> {condition, document_revision_now}  read
  conditions.recheck{id}         -> {condition, document, words}        execute
Functions used by other modules:
  refresh_document(kernel, document_record, principal) -> [ids marked STALE or BROKEN]   (called by documents.save and documents.edit after every write)
  create(kernel, principal, *, document, inputs, expression, result, method, assignment, result_block) -> condition

Implementation notes (WI-B). The card binds to block ids, character offsets and the quoted words of the revision it was
made on; the result paragraph is known by its block id (result_block), never by its words, so the owner may edit the
sentence without confusing the page's other paragraphs with it. refresh_document reads the document's cards with one
query, compares in memory, writes only the cards whose state or reason changed, never writes the document and never
raises into the owner's save: a card it cannot update is still reported by its computed state. It returns every card of
the page that is STALE or BROKEN after this write (not only the newly changed ones) so the page's quiet line can follow
the truth on every save; a card whose words come back exactly (an undo) reads CURRENT again. A recheck re-extracts from
the current revision (page_quantities, excluding every result paragraph on the page), recomputes through math.evaluate
(exact arithmetic in the Kernel) and rewrites only the result paragraph through documents.edit with the paragraph's whole
current text quoted; when the inputs' dimensions now differ, or nothing is left to add, the paragraph says why and the
card stays STALE with that reason. A card whose result paragraph is gone (BROKEN) is not rewritten: ask Slate for the
total again and a new card is made.
"""
from __future__ import annotations
from .assistant_identity import named
import json
import sqlite3
import time
from . import project_desk as records
from . import quantities

ID = records.ID
KIND = 'condition'
SCHEMA = 'ledger.condition/1'
STATES = ('CURRENT', 'STALE', 'BROKEN')
EXPRESSIONS = ('sum',)
MAX_INPUTS = quantities.MAX_MATCHES
SPAN_KEYS = ('block', 'index', 'start', 'end', 'text', 'value', 'unit')
METHOD = ['quantities_from_text', 'sum_model']
FIELDS = {
    'conditions.list': ({'document': ID}, []),
    'conditions.get': ({'id': ID}, ['id']),
    'conditions.recheck': ({'id': ID}, ['id']),
}
SCOPES = {op: 'execute' if op == 'conditions.recheck' else 'read' for op in FIELDS}
OBSERVERS = ('conditions.list', 'conditions.get')


# -- words -----------------------------------------------------------------------------------------------------------------

def when(at=None):
    return time.strftime('%Y-%m-%d %H:%M', time.localtime(at or time.time()))


def result_words(chosen, total, note='', at=None):
    """The result paragraph: the total, who checked it and when, and the exact inputs it came from."""
    n = len(chosen)
    listed = ', '.join(q['text'] for q in chosen[:40]) + (' and %d more' % (n - 40) if n > 40 else '')
    return 'Total of the %d quantit%s on this page: %s · checked by Graphite %s · from: %s%s' % (
        n, 'y' if n == 1 else 'ies', total['text'], when(at), listed, (' · ' + note) if note else '')


def problem_words(reason, at=None):
    return 'The quantities on this page cannot be added as they stand: %s · checked by Graphite %s' % (reason, when(at))


def mismatch_question(error):
    """The QUESTION the owner sees when two inputs disagree in dimension; the ValueError names both quantities."""
    words = str(error).removeprefix('UNITS_DIFFER: ').removesuffix(' cannot be added')
    return 'The quantities use different units: %s; which should be summed?' % words


# -- the page ---------------------------------------------------------------------------------------------------------------

def page_quantities(blocks, exclude=(), limit=quantities.MAX_MATCHES):
    """Every quantity on the page with its block id and index, result paragraphs excluded by block id; bounded."""
    out = []; skip = set(exclude or ())
    for index, b in enumerate(blocks):
        if b['id'] in skip or not b.get('text'): continue
        for q in quantities.extract(b['text'], limit - len(out)):
            out.append({**q, 'block': b['id'], 'index': index})
        if len(out) >= limit: break
    return out


def span(q):
    return {'block': q['block'], 'index': q['index'], 'start': q['start'], 'end': q['end'], 'text': q['text'], 'value': q['value'], 'unit': q.get('unit_canonical')}


def assess(card, doc):
    """(state, reason) of a card against a document record: by block id, offsets and quoted words."""
    by_id = {b['id']: b for b in doc['blocks']}
    if card.get('result_block') not in by_id: return 'BROKEN', 'The result paragraph is no longer on the page.'
    for q in card.get('inputs') or []:
        b = by_id.get(q.get('block'))
        if b is None: return 'STALE', 'The paragraph that held “%s” is gone.' % q.get('text')
        now = b['text'][q['start']:q['end']]
        if now != q['text']:
            if q['text'] in b['text']: return 'STALE', 'The words “%s” moved within their paragraph.' % q['text']
            return 'STALE', ('The words “%s” now read “%s”.' % (q['text'], now)) if now.strip() else ('The words “%s” are no longer at their place.' % q['text'])
    return 'CURRENT', ''


# -- the store -----------------------------------------------------------------------------------------------------------

def cards(db, owner, document=None):
    """The owner's cards, newest first, optionally for one document: one query."""
    out = []
    for raw, sha in db.execute('SELECT payload,digest FROM desk_records WHERE kind=? AND owner=? ORDER BY rowid DESC', (KIND, owner)):
        value = json.loads(raw)
        if records.digest(value) != sha: raise ValueError('PROJECT_DESK_RECORD_DAMAGED')
        if value.get('schema') != SCHEMA or (document is not None and value.get('document') != document): continue
        out.append(value)
    return out


def result_blocks(kernel, document, principal):
    """The block ids of every result paragraph on this page (a profile excludes them before extracting)."""
    with kernel.db() as db:
        records.ensure(db)
        return [c['result_block'] for c in cards(db, principal.identity, document)]


def load(db, ident, principal):
    card = records.read(db, KIND, ident, principal)
    if card.get('schema') != SCHEMA: raise ValueError('CONDITION_SCHEMA_UNSUPPORTED')
    return card


def summary(card):
    return {'id': card['id'], 'document': card['document'], 'document_revision': card['document_revision'], 'state': card['state'], 'reason': card.get('reason', ''),
            'expression': card['expression'], 'result': card['result'], 'result_block': card['result_block'], 'assignment': card.get('assignment'),
            'inputs': len(card.get('inputs') or []), 'checked_at': card.get('checked_at'), 'updated': card.get('updated', card['created']), 'origin': card.get('origin')}


def _document(db, ident, principal):
    from . import documents
    return documents.load(db, ident, principal)


def create(kernel, principal, *, document, inputs, expression, result, method, assignment, result_block, origin='SLATE', request=''):
    """A new card, CURRENT on the document's saved revision; every input must read its words at its place on that revision."""
    if 'execute' not in principal.scopes: raise ValueError('Operation is outside the authorized mode/scope: a condition card is a write')
    if expression not in EXPRESSIONS: raise ValueError('CONDITION_EXPRESSION: only sum in this pass')
    if not isinstance(inputs, list) or not 1 <= len(inputs) <= MAX_INPUTS: raise ValueError('CONDITION_INPUTS: 1 to %d spans' % MAX_INPUTS)
    if not isinstance(result, dict) or not isinstance(result.get('text'), str) or not result['text'].strip(): raise ValueError('CONDITION_RESULT: {value, unit, text}')
    if not isinstance(method, (list, tuple)) or not all(isinstance(m, str) and m for m in method): raise ValueError('CONDITION_METHOD: the helper names used')
    if assignment is not None and not (isinstance(assignment, str) and len(assignment) == 32): raise ValueError('CONDITION_ASSIGNMENT')
    if origin not in ('SLATE', 'HUMAN'): raise ValueError('CONDITION_ORIGIN')
    with kernel.db() as db:
        records.ensure(db)
        doc = _document(db, document, principal)
        by_id = {b['id']: (i, b) for i, b in enumerate(doc['blocks'])}
        if result_block not in by_id: raise ValueError('CONDITION_RESULT_BLOCK: that paragraph is not on the page')
        spans = []
        for q in inputs:
            if not isinstance(q, dict) or not set(SPAN_KEYS) <= set(q): raise ValueError('CONDITION_INPUT_SHAPE: ' + ', '.join(SPAN_KEYS))
            if type(q['start']) is not int or type(q['end']) is not int or q['start'] < 0 or q['end'] < q['start']: raise ValueError('CONDITION_INPUT_OFFSETS')
            found = by_id.get(q['block'])
            if found is None or found[1]['text'][q['start']:q['end']] != q['text']:
                raise ValueError('CONDITION_INPUT_NOT_ON_PAGE: “%s” is not at that place on the saved page' % str(q.get('text'))[:60])
            if q['block'] == result_block: raise ValueError('CONDITION_INPUT_IS_THE_RESULT: a result cannot be its own input')
            spans.append({**{k: q[k] for k in SPAN_KEYS}, 'index': found[0]})
        card = records.new(KIND, principal, schema=SCHEMA, project=doc.get('project'), document=document, document_revision=doc['revision'],
                           inputs=spans, expression=expression, result={'value': result.get('value'), 'unit': result.get('unit'), 'text': result['text']},
                           method=list(method), assignment=assignment, result_block=result_block, state='CURRENT', reason='', checked_at=time.time(),
                           origin=origin, request=' '.join(str(request or '').split())[:400], rechecks=0)
        return records.write(db, card, principal, 'CONDITION_CREATED')


def refresh_document(kernel, doc, principal):
    """Mark the cards bound to this document STALE or BROKEN when their words changed; return their ids.
    One query, in-memory comparison, a write only for a card whose state or reason moved; the document is never written and
    nothing raises into the owner's save."""
    out = []
    try:
        with kernel.db() as db:
            for card in cards(db, principal.identity, doc['id']):
                state, reason = assess(card, doc)
                if state != 'CURRENT': out.append(card['id'])
                if state == card.get('state') and reason == card.get('reason', ''): continue
                previous = card['revision']; records.edit(card, previous)
                card.update(state=state, reason=reason, seen_revision=doc['revision'], seen_at=time.time())
                try: records.write(db, card, principal, 'CONDITION_' + state, expected=previous)
                except ValueError: pass          # another writer moved this card between the read and the write; the next save compares again
    except (sqlite3.Error, ValueError, KeyError, TypeError):
        return out
    return out


def listing(kernel, args, principal):
    with kernel.db() as db:
        records.ensure(db)
        if args.get('document'): _document(db, args['document'], principal)
        return {'conditions': [summary(c) for c in cards(db, principal.identity, args.get('document'))[:100]]}


def get(kernel, ident, principal):
    with kernel.db() as db:
        records.ensure(db)
        card = load(db, ident, principal)
        try: now = _document(db, card['document'], principal)['revision']
        except ValueError: now = None
    return {'condition': card, 'document_revision_now': now}


def recheck(kernel, ident, principal):
    """Read the page again, add up what is there now, rewrite the result paragraph (bound to its current words) and bind the card anew."""
    from . import documents, helpers
    with kernel.db() as db:
        records.ensure(db)
        card = load(db, ident, principal); doc = _document(db, card['document'], principal)
        others = [c['result_block'] for c in cards(db, principal.identity, card['document'])]
    by_id = {b['id']: (i, b) for i, b in enumerate(doc['blocks'])}
    if card['result_block'] not in by_id or not by_id[card['result_block']][1]['text']:
        card = _write_state(kernel, principal, card, 'BROKEN', 'The result paragraph is no longer on the page.' if card['result_block'] not in by_id
                            else 'The result paragraph is empty.', doc['revision'])
        return {'condition': card, 'document': doc, 'words': named('The result paragraph is gone from the page; ask Stacy for the total again and a new card is made.')}
    index, block = by_id[card['result_block']]
    helpers.ensure_built_in(kernel, principal, METHOD)
    found = page_quantities(doc['blocks'], exclude=others)
    chosen, left_out, note = quantities.choose(found)
    helpers.record_use(kernel, principal, 'quantities_from_text', True, '%d quantities on page %s at revision %d' % (len(found), doc['id'][:8], doc['revision']))
    total = None; problem = None; at = time.time()
    if not chosen: problem = 'no quantities are left on the page'
    else:
        try:
            model = quantities.sum_model(chosen)
            evaluation = records.result_of(kernel, 'math.evaluate', {'model': model}, principal)
            total = quantities.total_of(evaluation, chosen)
            helpers.record_use(kernel, principal, 'sum_model', True, 'recheck: %s from %d quantities' % (total['text'], len(chosen)))
        except ValueError as exc:
            problem = str(exc).removeprefix('UNITS_DIFFER: ')
            helpers.record_use(kernel, principal, 'sum_model', False, 'recheck: ' + problem)
    text = result_words(chosen, total, note, at) if total else problem_words(problem, at)
    edited = documents.edit(kernel, {'id': doc['id'], 'expected_revision': doc['revision'], 'selection': {'block': index, 'start': 0, 'end': len(block['text']), 'text': block['text']},
                                     'change': {'replace': text}, 'origin': 'SLATE', 'request': 'recheck the total on this page'}, principal)
    saved = edited['document']
    with kernel.db() as db:
        card = load(db, ident, principal)                 # documents.edit refreshed the cards; take the card as it is now
        previous = card['revision']; records.edit(card, previous)
        if total:
            card.update(inputs=[span(q) for q in chosen], result={'value': total['value'], 'unit': total['unit'], 'text': total['text']}, state='CURRENT', reason='')
        else:
            card.update(inputs=[span(q) for q in chosen], state='STALE', reason='Could not be added: ' + problem + '.')
        card.update(document_revision=saved['revision'], checked_at=at, method=list(METHOD), rechecks=int(card.get('rechecks') or 0) + 1,
                    seen_revision=saved['revision'], seen_at=at)
        card = records.write(db, card, principal, 'CONDITION_RECHECKED', expected=previous)
    words = ('Rechecked: the %d quantit%s on this page total %s; the result paragraph was rewritten.' % (len(chosen), 'y' if len(chosen) == 1 else 'ies', total['text'])
             if total else 'The quantities on this page cannot be added as they stand: %s. The result paragraph says so; the card stays stale.' % problem)
    return {'condition': card, 'document': saved, 'words': words}


def _write_state(kernel, principal, card, state, reason, seen_revision):
    with kernel.db() as db:
        card = load(db, card['id'], principal)
        if card['state'] == state and card.get('reason') == reason: return card
        previous = card['revision']; records.edit(card, previous)
        card.update(state=state, reason=reason, seen_revision=seen_revision, seen_at=time.time())
        return records.write(db, card, principal, 'CONDITION_' + state, expected=previous)


def dispatch(kernel, op, args, principal):
    if op == 'conditions.list': return listing(kernel, args, principal)
    if op == 'conditions.get': return get(kernel, args['id'], principal)
    if op == 'conditions.recheck': return recheck(kernel, args['id'], principal)
    raise ValueError('Unknown condition operation')
