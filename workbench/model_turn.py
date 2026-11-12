"""The model turn applied to a real page (HATCH AGENT-02, owner decision D19).

D19: Slate acts freely inside an assignment and asks only for originals, network and outside effects; a document edit the
model proposes applies at once, visibly, and can be undone. This module decides, without Qt and without any call, whether
one proposed action may apply by itself to the page the owner has open, and completes its arguments from the page:

    decide(action, page) -> {'apply': bool, 'arguments': completed documents.edit arguments or None,
                             'reason': words, 'notes': [what was filled in or corrected],
                             'corrections': [the notes Slate says aloud: where the model's proposal was changed]}

``page`` is what the open page knows: {'document': id, 'revision': n, 'blocks': n, 'caret_block': i,
'selection': {block, start, end, text} or None} and, optionally, 'texts' (each paragraph's words) so the quoted words
can be checked here as well as in the store. Only ``documents.edit`` on the open document applies by itself; every other
operation keeps the review words (Run / Edit). A proposal made for an older revision, for another document, with a
paragraph the page does not have, or with a change the store would not accept, is not applied, and the reason says why.

What decide may fill in or correct (each one is named in ``notes``):
- a missing id or expected_revision is taken from the page; a different one refuses (another page, a stale revision);
- a missing selection is the owner's selection on the page, or the caret's paragraph for a paragraph change;
- a selection that quotes exactly the owner's selected words but names a place that cannot hold them (the 1.5B model in
  the AGENT-01 live trial wrote paragraph 4, on a one-paragraph page, for words selected in paragraph 0) takes the owner's
  selection. A place that does hold the quoted words is kept, even when the owner selected the same words elsewhere (“make
  the fox in the first paragraph bold” with the second paragraph's “fox” selected lands on the first paragraph's);
- the origin is always the model's (the model may not sign as the owner: the live trial proposed origin HUMAN), and the
  request recorded is the owner's words, set by the page, never the model's.
A correction that changes where the edit lands, or who it is recorded as, is also in ``corrections``, and words() says
it, so the owner sees it in Slate's sentence and on the card.

``words(result, action, model_id, corrections=...)`` is the sentence Slate says after the page changed.
``keeps_places(change)`` says whether a change leaves every paragraph and offset of the page meaning what it meant (marks,
clear, style), which is when a later edit of the same proposal may follow it onto the revision it made (shell2.SlateFace).
Nothing here starts a job, a worker or a model.
"""
from __future__ import annotations
import re
from . import documents as store

OPERATION = 'documents.edit'
# The author recorded on the revision. 'SLATE_MODEL' is used as soon as documents.ORIGINS accepts it; until then the
# closest existing origin is 'SLATE' and the request words say that the model proposed the edit (see request_words).
# (The store may list it in EDIT_ORIGINS, the origins documents.edit alone accepts, or in ORIGINS.)
ORIGIN = 'SLATE_MODEL' if 'SLATE_MODEL' in getattr(store, 'EDIT_ORIGINS', store.ORIGINS) else 'SLATE'
ARGUMENTS = ('id', 'expected_revision', 'selection', 'change', 'origin', 'request')
CHANGE_KEYS = tuple(store.CHANGE['properties'])
NEEDS_WORDS = (*store.MARKS, 'clear', 'replace')   # these change selected words; style and append change the paragraph
KEEPS_PLACES = (*store.MARKS, 'clear', 'style')    # these change no words and add no paragraph (documents.apply_change)
HEX = re.compile('[0-9a-f]{32,64}')


def page_of(document, revision, blocks, caret_block=0, selection=None, texts=None, styles=None):
    """The page dict decide() reads (a helper for callers and tests). styles (AGENT-02, the live trial): each paragraph's style,
    so a style the paragraph already has is set aside instead of being reported as a change."""
    page = {'document': document, 'revision': revision, 'blocks': blocks, 'caret_block': caret_block, 'selection': selection}
    if texts is not None: page['texts'] = list(texts)
    if styles is not None: page['styles'] = list(styles)
    return page


def _offset(value):
    return type(value) is int and value >= 0


def _refuse(reason, notes=()):
    return {'apply': False, 'arguments': None, 'reason': reason, 'notes': list(notes), 'corrections': []}


def keeps_places(change):
    """True when this change leaves the page's words and paragraphs as they were (marks, clear, style), so every
    paragraph index and offset written for the revision before it still means the same words on the revision after it."""
    return isinstance(change, dict) and bool(change) and set(change) <= set(KEEPS_PLACES)


def _holds(selection, blocks, texts):
    """Whether the place a selection names can be right on this page: the paragraph exists and, when the page's words
    are known, the quoted words are at those offsets. (Without the words the store checks them against the saved revision.)"""
    if type(blocks) is int and selection['block'] >= blocks: return False
    if texts is None: return True
    if selection['block'] >= len(texts): return False
    return texts[selection['block']][selection['start']:selection['end']] == selection.get('text')


def check_change(change):
    """None when documents.edit would accept this change, otherwise the words saying why not."""
    if not isinstance(change, dict) or not change: return 'it names no change'
    unknown = sorted(set(change) - set(CHANGE_KEYS))
    if unknown: return 'it asks for a change the page does not know (%s)' % ', '.join(str(k) for k in unknown)
    for key in store.MARKS:
        if key in change and type(change[key]) is not bool: return 'its %s value is not on or off' % key
    if 'clear' in change and change['clear'] is not True: return 'its clear value is not true'
    for key in ('style', 'append_style'):
        if key in change and change[key] not in store.STYLES: return 'its %s is not one of %s' % (key.replace('_', ' '), ', '.join(store.STYLES))
    for key in ('replace', 'append'):
        if key in change:
            value = change[key]
            if not isinstance(value, str) or '\n' in value or '\r' in value or '\x00' in value or len(value) > store.MAX_BLOCK_TEXT:
                return 'its %s words are not one line of text' % key
    if 'append_style' in change and 'append' not in change: return 'it gives a style for a paragraph it does not add'
    return None


KINDS = (('marks', store.MARKS), ('clear', ('clear',)), ('style', ('style',)), ('replace', ('replace',)), ('append', ('append', 'append_style')))


def kinds_of(change):
    """The kinds of change a change asks for: marks, clear, style, replace, append."""
    return [name for name, keys in KINDS if any(k in change for k in keys if k != 'append_style')]


def tidy_change(change, quoted=None):
    """AGENT-02, found in the live page trial: small models fill every optional key of a change. Drop what changes nothing or
    only rides along: an empty appended paragraph; replace with the very words quoted; a Normal style beside another kind of
    change; marks switched off beside a mark switched on. Returns (change, dropped words)."""
    out = dict(change); dropped = []
    if 'append' in out and not out['append'].strip():
        out.pop('append'); out.pop('append_style', None); dropped.append('an empty paragraph to add')
    if 'replace' in out and quoted is not None and out['replace'] == quoted:
        out.pop('replace'); dropped.append('replacing the words with themselves')
    if out.get('style') == 'Normal' and len(kinds_of(out)) > 1:
        out.pop('style'); dropped.append('body text riding along')
    if any(out.get(m) is True for m in store.MARKS):
        off = [m for m in store.MARKS if out.get(m) is False]
        for m in off: out.pop(m)
        if off: dropped.append('%s off, proposed beside a mark switched on, left as it is' % ' and '.join(off))
    return out, dropped


def _selection_shape(selection):
    if not isinstance(selection, dict) or not {'block', 'start', 'end'} <= set(selection) <= {'block', 'start', 'end', 'text'}: return False
    if not all(_offset(selection[k]) for k in ('block', 'start', 'end')) or selection['start'] > selection['end']: return False
    return 'text' not in selection or isinstance(selection['text'], str)


def decide(action, page):
    """Whether one proposed action applies by itself to the open page, with its completed arguments and the reason."""
    if not isinstance(action, dict) or not isinstance(action.get('arguments'), dict):
        return _refuse('the proposal has no operation and arguments')
    operation = action.get('operation')
    if operation != OPERATION:
        return _refuse('only an edit of the open page (documents.edit) applies by itself; %s waits for Run' % operation)
    if not isinstance(page, dict) or not page.get('document'):
        return _refuse('no document is open')
    arguments = action['arguments']; notes = []; corrections = []
    unknown = sorted(set(arguments) - set(ARGUMENTS))
    if unknown: return _refuse('it carries arguments documents.edit does not take (%s)' % ', '.join(str(k) for k in unknown))
    # the page: the same document, the revision the page shows
    ident = arguments.get('id')
    if ident is None: ident = page['document']; notes.append('the document is the open page')
    elif ident != page['document']: return _refuse('it names another document (%s), not the open page' % str(ident)[:32])
    revision = arguments.get('expected_revision'); current = page.get('revision')
    if revision is None: revision = current; notes.append('revision %s is the page’s' % current)
    elif type(revision) is not int: return _refuse('its revision is not a number')
    elif revision != current:
        return _refuse('it was made for revision %d and the page is at revision %s now, so it is stale' % (revision, current))
    # the change
    change = arguments.get('change')
    problem = check_change(change)
    if problem: return _refuse(problem)
    needs_words = any(k in change for k in NEEDS_WORDS)
    # the selection: the model's place stands when it can hold the words it quotes; the owner's selected words take its
    # place only when it cannot (a paragraph the page does not have, or offsets where those words are not)
    owner = page.get('selection') if isinstance(page.get('selection'), dict) else None
    owner_words = owner if owner and owner.get('end', 0) > owner.get('start', 0) and owner.get('text') else None
    blocks = page.get('blocks'); texts = page.get('texts') if isinstance(page.get('texts'), list) else None
    selection = arguments.get('selection')
    if selection is None:
        if owner_words: selection = dict(owner_words); notes.append('the selection is your selected words')
        elif needs_words: return _refuse('it changes words but names none, and no words are selected')
        else: selection = {'block': int(page.get('caret_block') or 0), 'start': 0, 'end': 0}; notes.append('the paragraph is the one with the caret')
    elif not _selection_shape(selection):
        return _refuse('its selection is not a paragraph and two offsets')
    else:
        selection = dict(selection)
        place = (selection['block'], selection['start'], selection['end'])
        if owner_words and place != (owner_words['block'], owner_words['start'], owner_words['end']):
            if selection.get('text') == owner_words['text'] and not _holds(selection, blocks, texts):
                said = ('the model named paragraph %d, words %d–%d, which do not hold “%s”; your selection in paragraph %d is used'
                        % (place[0] + 1, place[1], place[2], _short(owner_words['text']), owner_words['block'] + 1))
                notes.append(said); corrections.append(said); selection = dict(owner_words)
            elif needs_words and selection['start'] == selection['end'] and 'text' not in selection:
                said = 'the model named no words; your selected words “%s” are used' % _short(owner_words['text'])
                notes.append(said); corrections.append(said); selection = dict(owner_words)
        elif owner_words and 'text' not in selection:
            selection['text'] = owner_words['text']; notes.append('bound to your selected words')
    if type(blocks) is int and selection['block'] >= blocks:
        return _refuse('it names paragraph %d and the page has %d' % (selection['block'] + 1, blocks))
    if needs_words and selection['start'] == selection['end']:
        return _refuse('it changes words but its selection holds none; select the words first')
    if texts is not None and selection['block'] < len(texts):
        text = texts[selection['block']]
        if selection['end'] > len(text): return _refuse('its selection reaches past paragraph %d' % (selection['block'] + 1))
        if 'text' in selection and text[selection['start']:selection['end']] != selection['text']:
            return _refuse('the words it quotes (“%s”) are not at that place on the page' % _short(selection['text']))
        if 'text' not in selection and selection['end'] > selection['start']: selection['text'] = text[selection['start']:selection['end']]
    # AGENT-02 (the live trial): what rides along is dropped, and only one kind of change applies by itself
    change, dropped = tidy_change(change, selection.get('text') if selection.get('end', 0) > selection.get('start', 0) else None)
    styles = page.get('styles') if isinstance(page.get('styles'), list) else None
    if styles is not None and selection['block'] < len(styles) and change.get('style') == styles[selection['block']]:
        change.pop('style'); dropped.append('paragraph %d is already %s' % (selection['block'] + 1, store.STYLE_WORDS.get(styles[selection['block']], styles[selection['block']])))
    if not change: return _refuse('once what changes nothing is set aside (%s), it changes nothing' % '; '.join(dropped))
    kinds = kinds_of(change)
    if len(kinds) > 1:
        return _refuse('it mixes several kinds of change (%s); one kind at a time applies by itself, so this one waits for Run' % ', '.join(kinds))
    marks = [m for m in store.MARKS if m in change]
    if len(marks) > 1:
        return _refuse('it changes several marks at once (%s); one mark at a time applies by itself, so this one waits for Run' % ', '.join(marks))
    # replacing or deleting words (review of the fix): only the owner's own selected words, when the owner selected some;
    # a deletion only of the owner's selected words, never of words the owner did not select
    here = (selection['block'], selection['start'], selection['end'])
    mine = bool(owner_words) and here == (owner_words['block'], owner_words['start'], owner_words['end'])
    if 'replace' in change:
        if not change['replace'].strip() and not mine:
            return _refuse('it would delete words you did not select; select them and ask again')
        if owner_words and not mine:
            return _refuse('it would change “%s”, not your selected “%s”; Run applies it as proposed' % (_short(selection.get('text') or ''), _short(owner_words['text'])))
    # a paragraph change (a style or an added paragraph) belongs to the paragraph the owner is in (review of the fix: the
    # small models name paragraphs by number, one past the block index)
    if ('style' in change or 'append' in change) and selection['start'] == selection['end'] and not selection.get('text'):
        yours = owner_words['block'] if owner_words else int(page.get('caret_block') or 0)
        if selection['block'] != yours:
            return _refuse('it names paragraph %d but you are in paragraph %d; Run applies it as proposed' % (selection['block'] + 1, yours + 1))
    if dropped:
        said = 'set aside: %s' % '; '.join(dropped); notes.append(said); corrections.append(said)
    origin = arguments.get('origin')
    if origin not in (None, ORIGIN):
        said = 'recorded as Graphite’s model, not %s' % origin; notes.append(said); corrections.append(said)
    completed = {'id': ident, 'expected_revision': revision, 'selection': selection, 'change': dict(change), 'origin': ORIGIN}
    return {'apply': True, 'arguments': completed, 'reason': 'it edits the open page at its current revision', 'notes': notes, 'corrections': corrections}


def _short(text, limit=40):
    text = ' '.join(str(text or '').split())
    return text if len(text) <= limit else text[:limit - 2] + '…'


def model_short(model_id):
    """A model id in a few characters: the first eight of a file-set digest, or a name as given."""
    if not model_id: return ''
    model_id = str(model_id).strip()
    return model_id[:8] if HEX.fullmatch(model_id) else _short(model_id, 40)


def request_words(request, model_id=None):
    """The request recorded on the revision: the owner's words; while the store has no SLATE_MODEL origin, followed by
    who proposed the edit, so the saved record says a model was involved."""
    request = ' '.join(str(request or '').split())
    if ORIGIN == 'SLATE_MODEL': return request[:store.MAX_REQUEST]
    tail = ' · proposed by the model' + ((' ' + model_short(model_id)) if model_id else '')
    return (request[:max(0, store.MAX_REQUEST - len(tail))] + tail).strip(' ·')[:store.MAX_REQUEST]


def words(result, action=None, model_id=None, undoable=True, corrections=()):
    """What Slate says after a model edit landed: what changed, the revision, how to take it back, whose proposal it was,
    and any correction decide made to the proposal (``corrections``: where it landed instead, who it is recorded as).
    ``undoable`` False: the page had to reload the saved revision to show the edit exactly, so its undo does not reach it."""
    applied = (result or {}).get('applied') or {}; doc = (result or {}).get('document') or {}
    said = applied.get('words') or 'the change'
    short = model_short(model_id)
    back = 'Ctrl Z or “undo” takes it back' if undoable else 'the page reloaded the saved revision to show it, so Ctrl Z does not reach it'
    told = '; '.join(str(c) for c in corrections or () if c)
    return 'Changed on the page: %s · revision %s · %s · proposed by the model%s%s' % (said, doc.get('revision', '?'), back, (' ' + short) if short else '',
                                                                                    (' · ' + told) if told else '')


def not_applied_words(verdict):
    """The card's words when a proposed page edit could not apply by itself."""
    return 'Not applied by itself: %s. Run tries it as proposed; Edit puts it in the strip.' % (verdict or {}).get('reason', 'it does not fit the open page')


def changed_range(result):
    """The page range to highlight after an edit: the words changed, the paragraph styled, or the paragraph added."""
    applied = (result or {}).get('applied') or {}
    if 'appended_index' in applied: return {'block': applied['appended_index'], 'start': 0, 'end': None}
    block = applied.get('block', 0); start = applied.get('start', 0); end = applied.get('end', 0)
    if end > start: return {'block': block, 'start': start, 'end': end}
    return {'block': block, 'start': 0, 'end': None}   # a paragraph change: the whole paragraph
