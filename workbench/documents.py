"""Ledger documents: one page the owner and Slate write on in turns.

A document is a Project Desk record (kind ``document``): a title and ordered blocks, each a paragraph with a style
(Normal, Heading1, Heading2, Heading3, Code) and inline marks (bold, italic, underline) over character ranges. Every
change is a revision in the existing desk store (desk_records, desk_history, desk_events); nothing here adds a store,
a scheduler or a grant. A change is bound to the revision its actor saw: a stale revision is refused, never merged
quietly. Slate's edits name a selection (block, start, end) and quote the words it covers; the quoted words must still
be there, so a delayed reply cannot land on newer writing (WS01, CM03).

No model is needed for the direct edits. ``interpret`` resolves ordinary formatting requests ("make these words bold",
"italic", "underline", "make it a heading", "body text", "code", "plain", "replace x with y") through explicit rules
and nothing else: a request it does not recognise is left to the model path, which sees the same document and
selection. Recognition is conservative: every word of the request must belong to the formatting vocabulary.
"""
from __future__ import annotations
import re
import time
from html import escape
from . import project_desk as records

KIND = 'document'
SCHEMA = 'ledger.document/1'
STYLES = ('Normal', 'Heading1', 'Heading2', 'Heading3', 'Code')
MARKS = ('bold', 'italic', 'underline')
MAX_BLOCKS = 5000
MAX_BLOCK_TEXT = 32768
MAX_TEXT = 2000000
MAX_REQUEST = 400
ORIGINS = ('HUMAN', 'SLATE', 'IMPORTED')
EDIT_ORIGINS = (*ORIGINS, 'SLATE_MODEL')   # documents.edit alone: an edit the model proposed and the page applied (AGENT-02, D19/D30)
TITLE = {'type': 'string', 'minLength': 1, 'maxLength': 200}
ID = records.ID
OFFSET = {'type': 'integer', 'minimum': 0, 'maximum': MAX_BLOCK_TEXT}
# The selection names one paragraph (block index), the character offsets inside it and, when words are selected, the words themselves:
# the quoted words are checked against the saved revision before any change, so a delayed edit cannot land on newer writing.
SELECTION = {'type': 'object', 'properties': {'block': {'type': 'integer', 'minimum': 0, 'maximum': MAX_BLOCKS}, 'start': OFFSET, 'end': OFFSET,
                                               'text': {'type': 'string', 'maxLength': MAX_BLOCK_TEXT}}, 'required': ['block', 'start', 'end'], 'additionalProperties': False}
# One bounded change: marks on or off over the selected words, clear them, set the paragraph style, or replace the selected words.
CHANGE = {'type': 'object', 'properties': {'bold': {'type': 'boolean'}, 'italic': {'type': 'boolean'}, 'underline': {'type': 'boolean'}, 'clear': {'type': 'boolean'},
                                            'style': {'type': 'string', 'enum': list(STYLES)}, 'replace': {'type': 'string', 'maxLength': MAX_BLOCK_TEXT},
                                            'append': {'type': 'string', 'maxLength': MAX_BLOCK_TEXT}, 'append_style': {'type': 'string', 'enum': list(STYLES)}}, 'additionalProperties': False}
BLOCKS = {'type': 'array', 'maxItems': MAX_BLOCKS, 'items': {'type': 'object'}}
FIELDS = {
    'documents.create': ({'title': TITLE, 'project': ID, 'text': {'type': 'string', 'maxLength': 200000}, 'origin': {'type': 'string', 'enum': list(ORIGINS)}}, []),
    'documents.list': ({**records.PAGE, 'project': ID}, []),
    'documents.get': ({'id': ID}, ['id']),
    'documents.save': ({**records.EDIT, 'title': TITLE, 'blocks': BLOCKS, 'origin': {'type': 'string', 'enum': list(ORIGINS)}}, ['id', 'expected_revision', 'blocks']),
    'documents.edit': ({**records.EDIT, 'selection': SELECTION, 'change': CHANGE, 'origin': {'type': 'string', 'enum': list(EDIT_ORIGINS)},
                        'request': {'type': 'string', 'maxLength': MAX_REQUEST}}, ['id', 'expected_revision', 'selection', 'change']),
    'documents.interpret': ({'text': {'type': 'string', 'minLength': 1, 'maxLength': MAX_REQUEST}, 'selected': {'type': 'string', 'maxLength': MAX_BLOCK_TEXT}}, ['text']),
    'documents.render': ({'id': ID, 'format': {'type': 'string', 'enum': ['plain', 'markdown', 'html']}}, ['id']),
}
SCOPES = {op: 'read' if op.split('.')[1] in ('list', 'get', 'interpret', 'render') else 'execute' for op in FIELDS}
# Reads that refresh views; they do not fill the journal (activity.OBSERVER_OPERATIONS lists them).
OBSERVERS = ('documents.list', 'documents.get', 'documents.interpret', 'documents.render')


# -- the model ---------------------------------------------------------------------------------------------------------

def block(text='', style='Normal', marks=()):
    import uuid
    return {'id': uuid.uuid4().hex, 'style': style, 'text': text, 'marks': list(marks)}


def _int(value, name):
    if type(value) is not int or value < 0: raise ValueError('DOCUMENT_' + name + '_NOT_AN_OFFSET')
    return value


def normalize_marks(marks, length):
    """Sorted, non-overlapping runs, each carrying only the attributes that are on; empty and attribute-less runs vanish.
    Overlapping input runs are unioned: a bold run over an italic run yields bold+italic where they cross."""
    if not isinstance(marks, list): raise ValueError('DOCUMENT_MARKS_NOT_A_LIST')
    spans = []
    for mark in marks:
        if not isinstance(mark, dict) or not set(mark) <= {'start', 'end', *MARKS}: raise ValueError('DOCUMENT_MARK_SHAPE')
        start = _int(mark.get('start'), 'MARK_START'); end = _int(mark.get('end'), 'MARK_END')
        if end > length: raise ValueError('DOCUMENT_MARK_BEYOND_TEXT')
        if start > end: raise ValueError('DOCUMENT_MARK_REVERSED')
        on = frozenset(k for k in MARKS if mark.get(k) is True)
        if any(mark.get(k) not in (None, True, False) for k in MARKS): raise ValueError('DOCUMENT_MARK_VALUE')
        if start < end and on: spans.append((start, end, on))
    if not spans: return []
    edges = sorted({e for span in spans for e in span[:2]})
    runs = []
    for a, b in zip(edges, edges[1:]):
        on = frozenset().union(*[s[2] for s in spans if s[0] <= a and s[1] >= b])
        if not on: continue
        if runs and runs[-1]['end'] == a and frozenset(k for k in MARKS if runs[-1].get(k)) == on: runs[-1]['end'] = b
        else: runs.append({'start': a, 'end': b, **{k: True for k in MARKS if k in on}})
    return runs


def normalize_block(value):
    if not isinstance(value, dict) or not {'text'} <= set(value) <= {'id', 'style', 'text', 'marks'}: raise ValueError('DOCUMENT_BLOCK_SHAPE')
    text = value['text']
    if not isinstance(text, str) or len(text) > MAX_BLOCK_TEXT: raise ValueError('DOCUMENT_BLOCK_TEXT')
    if '\n' in text or '\r' in text or '\x00' in text: raise ValueError('DOCUMENT_BLOCK_LINE_BREAK')
    style = value.get('style', 'Normal')
    if style not in STYLES: raise ValueError('DOCUMENT_BLOCK_STYLE')
    ident = value.get('id')
    if ident is None:
        import uuid
        ident = uuid.uuid4().hex
    if not isinstance(ident, str) or not re.fullmatch('[a-f0-9]{32}', ident): raise ValueError('DOCUMENT_BLOCK_ID')
    return {'id': ident, 'style': style, 'text': text, 'marks': normalize_marks(value.get('marks', []), len(text))}


def normalize_blocks(blocks):
    if not isinstance(blocks, list) or len(blocks) > MAX_BLOCKS: raise ValueError('DOCUMENT_BLOCK_LIMIT')
    out = [normalize_block(b) for b in blocks] or [block()]
    seen = set()
    for row in out:
        if row['id'] in seen: raise ValueError('DOCUMENT_BLOCK_ID_REPEATED')
        seen.add(row['id'])
    if sum(len(b['text']) for b in out) > MAX_TEXT: raise ValueError('DOCUMENT_SIZE')
    return out


def from_text(text):
    """Plain writing becomes Normal blocks, one per line; a blank line stays an empty block."""
    return [block(line.rstrip('\r')) for line in (text or '').split('\n')] or [block()]


def plain_text(doc):
    return '\n'.join(b['text'] for b in doc['blocks'])


def word_count(blocks):
    return sum(len(b['text'].split()) for b in blocks)


UNTITLED = 'Untitled document'


def clean_title(title, blocks=None):
    """A named document keeps its name; an unnamed one is called by its first words."""
    title = ' '.join(str(title or '').split())[:200]
    if title and title != UNTITLED: return title
    first = next((b['text'].strip() for b in blocks or [] if b['text'].strip()), '')
    return (first[:60] + ('…' if len(first) > 60 else '')) or UNTITLED


def summary(doc):
    return {'id': doc['id'], 'title': doc['title'], 'revision': doc['revision'], 'updated': doc.get('updated', doc['created']),
            'project': doc.get('project'), 'words': word_count(doc['blocks']), 'blocks': len(doc['blocks']), 'last_change': doc.get('last_change')}


# -- rendering --------------------------------------------------------------------------------------------------------------

def runs(b):
    """(text, attribute set) pieces covering the whole block, marks and gaps alike."""
    out = []; at = 0; text = b['text']
    for mark in b['marks']:
        if mark['start'] > at: out.append((text[at:mark['start']], frozenset()))
        out.append((text[mark['start']:mark['end']], frozenset(k for k in MARKS if mark.get(k))))
        at = mark['end']
    if at < len(text): out.append((text[at:], frozenset()))
    return out


def render(doc, fmt='plain'):
    if fmt == 'plain': return plain_text(doc)
    lines = []
    if fmt == 'markdown':
        lines.append('# ' + doc['title']); lines.append('')
        for b in doc['blocks']:
            if b['style'] == 'Code': lines += ['```', b['text'], '```']; continue
            body = ''
            for text, on in runs(b):
                core = text.strip(); lead = text[:len(text) - len(text.lstrip())]; tail = text[len(text.rstrip()):]
                if not core: body += text; continue
                piece = core  # emphasis markers hug the words; the spaces stay outside them, as Markdown needs
                if 'bold' in on and 'italic' in on: piece = '***' + piece + '***'
                elif 'bold' in on: piece = '**' + piece + '**'
                elif 'italic' in on: piece = '*' + piece + '*'
                if 'underline' in on: piece = '<u>' + piece + '</u>'
                body += lead + piece + tail
            prefix = {'Heading1': '## ', 'Heading2': '### ', 'Heading3': '#### '}.get(b['style'], '')
            lines.append(prefix + body); lines.append('')
        return '\n'.join(lines).rstrip('\n') + '\n'
    if fmt == 'html':
        lines.append('<!doctype html><meta charset="utf-8"><title>%s</title><article>' % escape(doc['title']))
        lines.append('<h1>%s</h1>' % escape(doc['title']))
        for b in doc['blocks']:
            if b['style'] == 'Code': lines.append('<pre>%s</pre>' % escape(b['text'])); continue
            body = ''
            for text, on in runs(b):
                piece = escape(text)
                if 'bold' in on: piece = '<strong>' + piece + '</strong>'
                if 'italic' in on: piece = '<em>' + piece + '</em>'
                if 'underline' in on: piece = '<u>' + piece + '</u>'
                body += piece
            tag = {'Heading1': 'h2', 'Heading2': 'h3', 'Heading3': 'h4'}.get(b['style'], 'p')
            lines.append('<%s>%s</%s>' % (tag, body, tag))
        lines.append('</article>')
        return '\n'.join(lines) + '\n'
    raise ValueError('DOCUMENT_FORMAT')


# -- the direct edits ----------------------------------------------------------------------------------------------------

def apply_change(blocks, selection, change):
    """Return (new blocks, words) for one bounded change on one block. Raises on a stale or malformed selection."""
    if not isinstance(selection, dict) or not {'block', 'start', 'end'} <= set(selection) <= {'block', 'start', 'end', 'text'}:
        raise ValueError('DOCUMENT_SELECTION_SHAPE')
    if not isinstance(change, dict) or not change or not set(change) <= {*MARKS, 'style', 'replace', 'clear', 'append', 'append_style'}: raise ValueError('DOCUMENT_CHANGE_SHAPE')
    if 'append_style' in change and 'append' not in change: raise ValueError('DOCUMENT_CHANGE_SHAPE')
    index = _int(selection['block'], 'SELECTION_BLOCK'); start = _int(selection['start'], 'SELECTION_START'); end = _int(selection['end'], 'SELECTION_END')
    if index >= len(blocks): raise ValueError('SELECTION_CHANGED: that paragraph is no longer there; select again')
    current = blocks[index]; text = current['text']
    if start > end or end > len(text): raise ValueError('SELECTION_CHANGED: the selection reaches past the paragraph; select again')
    quoted = selection.get('text')
    if quoted is not None and text[start:end] != quoted: raise ValueError('SELECTION_CHANGED: the words at that place changed; select again')
    new = {**current, 'marks': [dict(m) for m in current['marks']]}; words = []
    chosen = text[start:end]
    short = chosen if len(chosen) <= 40 else chosen[:38] + '…'
    for key in MARKS:
        if key in change:
            if type(change[key]) is not bool: raise ValueError('DOCUMENT_CHANGE_VALUE')
            if start == end: raise ValueError('SELECTION_REQUIRED: select the words first')
            if change[key]: new['marks'].append({'start': start, 'end': end, key: True}); words.append('made “%s” %s' % (short, key))
            else:
                new['marks'] = _without(new['marks'], start, end, key); words.append('removed %s from “%s”' % (key, short))
    if change.get('clear') is True:
        if start == end: raise ValueError('SELECTION_REQUIRED: select the words first')
        new['marks'] = _without(new['marks'], start, end, None); words.append('cleared the formatting of “%s”' % short)
    elif 'clear' in change: raise ValueError('DOCUMENT_CHANGE_VALUE')
    if 'style' in change:
        if change['style'] not in STYLES: raise ValueError('DOCUMENT_CHANGE_STYLE')
        new['style'] = change['style']; words.append('made the paragraph ' + STYLE_WORDS[change['style']])
    if 'replace' in change:
        replacement = change['replace']
        if not isinstance(replacement, str) or '\n' in replacement or len(replacement) > MAX_BLOCK_TEXT: raise ValueError('DOCUMENT_CHANGE_REPLACE')
        if start == end: raise ValueError('SELECTION_REQUIRED: select the words first')
        new['text'] = text[:start] + replacement + text[end:]
        if len(new['text']) > MAX_BLOCK_TEXT: raise ValueError('DOCUMENT_BLOCK_TEXT')
        delta = len(replacement) - (end - start); kept = []
        for mark in new['marks']:
            if mark['end'] <= start: kept.append(mark)
            elif mark['start'] >= end: kept.append({**mark, 'start': mark['start'] + delta, 'end': mark['end'] + delta})
            else:
                # a mark crossing the replaced words keeps its outside parts
                if mark['start'] < start: kept.append({**mark, 'end': start})
                if mark['end'] > end: kept.append({**mark, 'start': end + delta, 'end': mark['end'] + delta})
        new['marks'] = kept; words.append('replaced “%s” with “%s”' % (short, replacement if len(replacement) <= 40 else replacement[:38] + '…'))
        end = start + len(replacement)
    new['marks'] = normalize_marks(new['marks'], len(new['text']))
    out = list(blocks); out[index] = new; appended = None
    if 'append' in change:  # a new paragraph after the selected one (Slate writing a result under the owner's words); the selection itself is untouched
        text_new = change['append']
        if not isinstance(text_new, str) or '\n' in text_new or '\r' in text_new or len(text_new) > MAX_BLOCK_TEXT: raise ValueError('DOCUMENT_CHANGE_APPEND')
        appended = block(text_new, change.get('append_style', 'Normal')); out.insert(index + 1, appended)
        short_new = text_new if len(text_new) <= 40 else text_new[:38] + '…'
        words.append('added the paragraph “%s” after paragraph %d' % (short_new, index + 1))
    return out, {'words': ' and '.join(words), 'block': index, 'start': start, 'end': end, 'text': new['text'][start:end], **({'appended_block': appended['id'], 'appended_index': index + 1} if appended else {})}


def _without(marks, start, end, key):
    out = []
    for mark in marks:
        on = {k for k in MARKS if mark.get(k)}
        drop = on if key is None else {key} & on
        if not drop or mark['end'] <= start or mark['start'] >= end: out.append(mark); continue
        keep = {k: True for k in on - drop}
        if mark['start'] < start: out.append({'start': mark['start'], 'end': start, **{k: True for k in on}})
        if keep: out.append({'start': max(mark['start'], start), 'end': min(mark['end'], end), **keep})
        if mark['end'] > end: out.append({'start': end, 'end': mark['end'], **{k: True for k in on}})
    return out


STYLE_WORDS = {'Normal': 'body text', 'Heading1': 'a heading', 'Heading2': 'a subheading', 'Heading3': 'a minor heading', 'Code': 'code'}
_FILLER = {'make', 'makes', 'made', 'set', 'turn', 'put', 'render', 'please', 'can', 'could', 'you', 'would', 'will', 'kindly', 'slate', 'now',
           'these', 'those', 'this', 'that', 'the', 'a', 'an', 'my', 'it', 'them', 'all', 'of', 'in', 'into', 'as', 'to', 'be', 'is', 'are',
           'words', 'word', 'text', 'selection', 'selected', 'highlighted', 'highlight', 'line', 'part', 'passage', 'paragraph', 'sentence',
           'bit', 'piece', 'one', 'and', 'also', 'too', 'again', 'styled', 'font', 'face', 'type', 'up'}
_ON = {'bold': {'bold', 'bolder', 'bolded', 'strong', 'embolden', 'heavy', 'heavier'},
       'italic': {'italic', 'italics', 'italicise', 'italicize', 'italicised', 'italicized', 'slanted', 'slant', 'oblique', 'emphasis', 'emphasise', 'emphasize', 'emphasised', 'emphasized'},
       'underline': {'underline', 'underlined', 'underscore', 'underscored'}}
_OFF = {'remove', 'unbold', 'unitalic', 'ununderline', 'un', 'not', 'no', 'without', 'undo', 'clear', 'strip', 'drop', 'take', 'off', 'away', 'stop', 'longer', 'anymore'}
_STYLE = {'heading': 'Heading1', 'headline': 'Heading1', 'header': 'Heading1', 'title': 'Heading1', 'h1': 'Heading1', 'subheading': 'Heading2', 'subtitle': 'Heading2',
          'h2': 'Heading2', 'h3': 'Heading3', 'subsubheading': 'Heading3', 'body': 'Normal', 'normal': 'Normal', 'regular': 'Normal', 'ordinary': 'Normal', 'prose': 'Normal',
          'code': 'Code', 'monospace': 'Code', 'monospaced': 'Code', 'preformatted': 'Code', 'verbatim': 'Code'}
_CLEAR = {'plain', 'unformat', 'unformatted', 'unstyle', 'unstyled'}
_FORMAT_WORDS = {'formatting', 'format', 'formats', 'style', 'styles', 'styling', 'marks', 'mark', 'emphasis'}
_LEVELS = {'1': 'Heading1', 'one': 'Heading1', 'first': 'Heading1', '2': 'Heading2', 'two': 'Heading2', 'second': 'Heading2', '3': 'Heading3', 'three': 'Heading3', 'third': 'Heading3', 'minor': 'Heading3', 'small': 'Heading3', 'big': 'Heading1', 'large': 'Heading1', 'main': 'Heading1', 'level': None}
_REPLACE = re.compile(r'^\s*(?:please\s+)?(?:replace|change|swap|rewrite|turn)\s+(?P<old>["“”\']?.+?["“”\']?)\s+(?:with|to|by|into)\s+(?P<new>["“”\']?.+?["“”\']?)\s*[.!]?\s*$', re.I)


def _quoteless(value):
    return value.strip().strip('"“”\'').strip()


def interpret(text, selected=None):
    """One explicit rule set over the request words. Returns a dict; ``recognized`` False leaves the request to the model."""
    raw = ' '.join(str(text or '').split())
    result = {'recognized': False, 'change': None, 'words': None, 'needs_selection': True, 'basis': 'EXPLICIT_RULES_NO_MODEL', 'request': raw[:MAX_REQUEST]}
    if not raw or len(raw) > MAX_REQUEST: return result
    match = _REPLACE.match(raw)
    if match:
        old = _quoteless(match.group('old')); new = _quoteless(match.group('new'))
        if old and new and '\n' not in new and len(old.split()) <= 24 and len(new.split()) <= 48:
            change = {'replace': new}; narrow = None
            if selected is not None:
                at = selected.casefold().find(old.casefold())
                if at < 0: return {**result, 'recognized': True, 'change': change, 'needs_selection': True, 'words': 'replace “%s” with “%s”' % (old, new),
                                   'problem': 'The selected words do not contain “%s”.' % old}
                narrow = (at, at + len(old))
            return {**result, 'recognized': True, 'change': change, 'words': 'replace “%s” with “%s”' % (old, new), 'narrow': narrow, 'old': old}
    tokens = [t for t in re.findall(r"[a-z0-9]+(?:'[a-z]+)?", raw.casefold())]
    if not tokens or len(tokens) > 14: return result
    change = {}; off = any(t in _OFF for t in tokens); words = []; unknown = []
    if off and any(t in _FORMAT_WORDS for t in tokens): change['clear'] = True; words.append('plain')  # "clear the formatting", "no styling"
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token.startswith('un') and len(token) > 4 and any(token[2:] in vocabulary for vocabulary in _ON.values()): token, off = token[2:], True  # unbold, unitalic
        if token in _FILLER or token in _OFF or token in _FORMAT_WORDS: i += 1; continue
        found = next((k for k, vocabulary in _ON.items() if token in vocabulary), None)
        if found:
            change[found] = not off; words.append(found); i += 1; continue
        if token in _STYLE:
            style = _STYLE[token]
            if style == 'Heading1' and i + 1 < len(tokens) and tokens[i + 1] in _LEVELS:
                level = _LEVELS[tokens[i + 1]]
                if level is None and i + 2 < len(tokens) and tokens[i + 2] in _LEVELS: level = _LEVELS[tokens[i + 2]]; i += 1
                style = level or style; i += 1
            change['style'] = style; words.append(STYLE_WORDS[style]); i += 1; continue
        if token in _CLEAR:
            change['clear'] = True; words.append('plain'); i += 1; continue
        if token in _LEVELS: i += 1; continue
        unknown.append(token); i += 1
    if unknown or not change: return result
    if off and not any(k in change for k in MARKS):
        if 'style' in change and change['style'] != 'Normal': change = {'style': 'Normal'}; words = ['body text']
        elif 'style' not in change: change = {'clear': True}; words = ['plain']
    if change.get('clear'):
        for key in MARKS: change.pop(key, None)
        change = {'clear': True, **({'style': change['style']} if 'style' in change else {})}
    needs = any(k in change for k in MARKS) or 'clear' in change
    removed = [k for k in MARKS if change.get(k) is False]; added = [w for w in words if w not in removed]
    phrase = []
    if added: phrase.append(('make the selection ' if needs else 'make the paragraph ') + ' and '.join(added))
    if removed: phrase.append('remove ' + ' and '.join(removed) + ' from the selection')
    return {**result, 'recognized': True, 'change': change, 'needs_selection': needs, 'words': ' and '.join(phrase)}


# -- the store -------------------------------------------------------------------------------------------------------------

def load(db, ident, principal):
    doc = records.read(db, KIND, ident, principal)
    if doc.get('document_schema') != SCHEMA: raise ValueError('DOCUMENT_SCHEMA_UNSUPPORTED')
    return doc


def create(kernel, args, principal, derivation=None, brief=None, blocks=None):
    """`derivation` is for a calculation worked out from a sheet; `brief` marks a page written from the whole desk
    (workbench/field_brief.py), which may bring its own styled blocks. Neither can be set through the operation."""
    blocks = normalize_blocks(blocks if blocks is not None else from_text(args.get('text', '')))
    with kernel.db() as db:
        records.ensure(db)
        if args.get('project'): records.read(db, 'project', args['project'], principal)
        doc = records.new(KIND, principal, document_schema=SCHEMA, title=clean_title(args.get('title'), blocks), blocks=blocks,
                          project=args.get('project'), origin=args.get('origin', 'HUMAN'), updated=time.time(),
                          last_change={'actor': args.get('origin', 'HUMAN'), 'words': 'started the document', 'at': time.time()})
        if derivation:
            doc['derivation'] = derivation
        if brief:
            doc['brief'] = brief
        return records.write(db, doc, principal, 'DOCUMENT_CREATED')


def save(kernel, args, principal):
    blocks = normalize_blocks(args['blocks'])
    with kernel.db() as db:
        records.ensure(db)
        doc = load(db, args['id'], principal); previous = doc['revision']
        if doc['blocks'] == blocks and doc['title'] == clean_title(args.get('title', doc['title']), blocks):
            return {'document': doc, 'saved': False, 'reason': 'UNCHANGED'}
        records.edit(doc, args['expected_revision'])
        doc.update(blocks=blocks, title=clean_title(args.get('title', doc['title']), blocks),
                   last_change={'actor': args.get('origin', 'HUMAN'), 'words': 'saved the writing', 'at': time.time(), 'words_count': word_count(blocks)})
        saved = records.write(db, doc, principal, 'DOCUMENT_SAVED', expected=previous)
    return {'document': saved, 'saved': True, 'conditions_stale': conditions_after_write(kernel, saved, principal)}


def edit(kernel, args, principal):
    with kernel.db() as db:
        records.ensure(db)
        doc = load(db, args['id'], principal); previous = doc['revision']
        if doc['revision'] != args['expected_revision']: raise ValueError('REVISION_CHANGED: the document moved on; reopen before editing')
        blocks, applied = apply_change(doc['blocks'], args['selection'], args['change'])
        records.edit(doc, previous)
        actor = args.get('origin', 'SLATE')
        doc.update(blocks=normalize_blocks(blocks), last_change={'actor': actor, 'words': applied['words'], 'at': time.time(), 'block': applied['block'],
                                                                 'start': applied['start'], 'end': applied['end'], 'request': args.get('request', '')[:MAX_REQUEST]})
        saved = records.write(db, doc, principal, 'DOCUMENT_EDITED_BY_' + actor, expected=previous)
    stale = conditions_after_write(kernel, saved, principal)
    return {'document': saved, 'applied': applied, 'actor': actor, 'basis': {'SLATE': 'EXPLICIT_RULES_NO_MODEL', 'SLATE_MODEL': 'MODEL_PROPOSAL_CHECKED_AND_APPLIED'}.get(actor, 'OWNER_EDIT'), 'model_used': actor == 'SLATE_MODEL', 'conditions_stale': stale}


def conditions_after_write(kernel, doc, principal):
    """AGENT-01: results bound to this page's words (condition cards) read stale when the words they used changed."""
    try:
        from . import conditions
        return conditions.refresh_document(kernel, doc, principal)
    except ImportError: return []
    except NotImplementedError: return []


def listing(kernel, args, principal):
    with kernel.db() as db:
        records.ensure(db)
        rows = records.listing(db, KIND, args, principal)
    rows['documents'] = [summary(r) for r in rows.pop('records') if r.get('document_schema') == SCHEMA]
    return rows


def get(kernel, ident, principal):
    with kernel.db() as db:
        records.ensure(db); doc = load(db, ident, principal)
        events = [dict(zip(('revision', 'actor', 'action', 'at'), row)) for row in db.execute(
            'SELECT revision,actor,action,at FROM desk_events WHERE record=? ORDER BY at DESC LIMIT 32', (ident,))] if _has_events(db) else []
    result = {'document': doc, 'summary': summary(doc), 'events': events, 'plain': plain_text(doc)}
    if doc.get('derivation'):
        from .datasheet_work import report_state
        result['source_state'] = report_state(kernel, principal, doc['derivation'])
    return result


def _has_events(db):
    return bool(db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='desk_events'").fetchone())


def dispatch(kernel, op, args, principal):
    if op == 'documents.create': return create(kernel, args, principal)
    if op == 'documents.list': return listing(kernel, args, principal)
    if op == 'documents.get': return get(kernel, args['id'], principal)
    if op == 'documents.save': return save(kernel, args, principal)
    if op == 'documents.edit': return edit(kernel, args, principal)
    if op == 'documents.interpret': return interpret(args['text'], args.get('selected'))
    if op == 'documents.render':
        with kernel.db() as db:
            records.ensure(db); doc = load(db, args['id'], principal)
        fmt = args.get('format', 'plain')
        return {'id': doc['id'], 'revision': doc['revision'], 'format': fmt, 'text': render(doc, fmt)}
    raise ValueError('Unknown document operation')
