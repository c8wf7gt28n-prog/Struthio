"""The desk written up as one page, from the records (no Qt).

The owner's specification asks for a result "I can open, use, edit, print, or hand to somebody", and for "a clear account
of what was actually checked". The brief is that account for a whole desk. It is not written by a model: every line is
read from a record, in a fixed order, and what Stacy doubts or cannot tell is said in the same page as what stands, so
the page cannot look better than the records do.

    what stands          each finding that stands, with what it stands on and how it is checked
    what waits for you   everything in the Field that waits, and why
    what I doubt         every doubt (workbench/field_doubt.py), with its reason
    what I cannot tell   what the records do not say
    the numbers          each calculation, its recipe, its inputs with their cells, and whether it still agrees with its sheet
    where it comes from  each source and how many things rest on it

    compose(kernel, principal, field)   the brief as lines (a read)
    keep(kernel, principal)             write it as a page (a change: it waits for the owner's go wherever it is offered)
    fingerprint(field)                  the desk as one number, so a kept brief knows when the desk has moved on
    standing(...)                       for Stacy's doubt: whether a kept brief is still the desk as it is

A kept brief is a page like any other: it can be edited, exported and printed. It carries the fingerprint of the desk it
was written from; when the desk changes, the Field shows the brief as waiting, and writing it again makes a new page that
takes its place (the earlier one is kept in Documents, as a recomputed calculation's is).
"""
import hashlib
import json
import time

from .field_doubt import ORDER, Doubt, _Once, doubts_for

PROFILE = 'field-brief/1'
TAG = 'BRIEF'
KIND_WORD = {'source': 'source', 'sheet': 'sheet', 'calculation': 'calculation', 'document': 'page', 'finding': 'finding', 'question': 'open question',
             'condition': 'total', 'job': 'job', 'method': 'method'}


def is_brief(obj):
    return obj is not None and obj.kind == 'document' and obj.tag == TAG


def fingerprint(field):
    """Everything the Field shows that a brief speaks of, as one number: each thing with its words and its state, and each
    wire. The briefs themselves are left out (writing one must not make it out of date), and so are jobs, which come and go."""
    quiet = {obj.id for obj in field.objects if is_brief(obj) or obj.kind == 'job'}
    # The facts a sheet carries (a revision, a version, what it stands on) are part of it: a record that was saved again
    # is a changed desk even when no state moved, because a doubt may have come or gone with it.
    things = sorted([obj.id, obj.kind, str(obj.title), str(obj.state), [str(line) for line in obj.lines]] for obj in field.objects if obj.id not in quiet)
    wires = sorted([link.source, link.target, str(link.label), bool(link.stale)] for link in field.links if link.source not in quiet and link.target not in quiet)
    return hashlib.sha256(json.dumps([things, wires], ensure_ascii=False, separators=(',', ':')).encode('utf-8')).hexdigest()


def _plural(count, word):
    return '%d %s%s' % (count, word, '' if count == 1 else 's')


def _read(kernel, principal, operation, arguments):
    try:
        answer = kernel.dispatch(operation, arguments, principal)
    except Exception:  # noqa: BLE001 - a record that cannot be read is said in its line; it never stops the page
        return None
    return answer['result'] if answer.get('ok') else None


PER_PART = 24                 # a brief is brief: each part says at most this many lines and then how many more there are


def compose(kernel, principal, field, now=None):
    """The brief of this Field: {'title', 'lines': [{'part', 'text', 'about'}], 'fingerprint', 'counts'}. A read."""
    from pathlib import Path
    home = Path(str(getattr(kernel, 'root', '') or '')).name      # the workspace's own name, when the desk has no single question to be named after
    kernel = _Once(kernel);things = [obj for obj in field.objects if not is_brief(obj)]
    desk = str(field.title or '').split('  ·  ')[0].strip() or home or 'This workspace'
    lines = [];said = {}

    def add(part, text, about=''):
        # One line of the page is one line: a record's own line breaks are spaces here. A part that runs long says so once.
        said[part] = said.get(part, 0) + 1
        if part in ('head', 'title', 'foot') or said[part] <= PER_PART:
            lines.append({'part': part, 'text': ' '.join(str(text).split()), 'about': about})
    found = {obj.id: sorted(doubts_for(kernel, principal, obj, field), key=lambda d: ORDER.get(d.verdict, 9)) for obj in things}
    doubts = [(obj, d) for obj in things for d in found[obj.id] if d.verdict == 'doubt']
    unsure = [(obj, d) for obj in things for d in found[obj.id] if d.verdict == 'cannot tell']
    waiting = [obj for obj in things if obj.needs_attention()]
    census = {}
    for obj in things:census[obj.kind] = census.get(obj.kind, 0) + 1
    add('head', '%s · brief' % desk)
    add('head', 'Written from the records on %s. Every line below is read from a record; no model wrote any of it.' % time.strftime('%Y-%m-%d %H:%M', time.localtime(now or time.time())))
    add('head', '%s on the desk: %s. %s for you. %s, and %s I cannot tell.' % (
        _plural(len(things), 'thing'), ', '.join(_plural(census[kind], KIND_WORD.get(kind, kind)) for kind in sorted(census, key=lambda kind: (list(KIND_WORD).index(kind) if kind in KIND_WORD else 99))) or 'nothing yet',
        ('%s waits' % _plural(len(waiting), 'thing')) if len(waiting) == 1 else ('%s wait' % _plural(len(waiting), 'thing')) if waiting else 'Nothing waits',
        _plural(len(doubts), 'doubt'), _plural(len(unsure), 'thing')))
    standing_now = [obj for obj in things if obj.kind == 'finding' and not obj.needs_attention() and obj.state == 'current']
    add('title', 'What stands')
    for obj in standing_now:
        holds = [d.why for d in found[obj.id] if d.verdict == 'holds' and d.about in ('what it stands on', 'a check')]
        weak = [d.about for d in found[obj.id] if d.verdict == 'doubt']
        add('stands', '%s — %s%s' % (str(obj.title).rstrip(), '; '.join(holds) or next((str(line) for line in obj.lines if line), 'it is recorded as standing'),
                                     (' (but see what I doubt: %s)' % ', '.join(dict.fromkeys(weak))) if weak else ''), obj.id)
    if not standing_now:add('stands', 'No finding stands yet.')
    add('title', 'What waits for you')
    for obj in waiting:
        why = next((str(line) for line in obj.lines if line), '') or str(obj.state)
        add('waits', '%s “%s” — %s' % (KIND_WORD.get(obj.kind, obj.kind).capitalize(), str(obj.title).rstrip(), why), obj.id)
    if not waiting:add('waits', 'Nothing waits.')
    add('title', 'What I doubt')
    for obj, d in doubts:
        add('doubt', '“%s” — %s: %s' % (str(obj.title).rstrip(), d.about, d.why), obj.id)
    if not doubts:add('doubt', 'Nothing, by the rules I have. They are few: a clean line here is not a proof.')
    add('title', 'What I cannot tell')
    for obj, d in unsure:
        add('cannot tell', '“%s” — %s: %s' % (str(obj.title).rstrip(), d.about, d.why), obj.id)
    if not unsure:add('cannot tell', 'Nothing is left open by the rules I have.')
    calculations = [obj for obj in things if obj.kind == 'calculation']
    if calculations:
        add('title', 'The numbers')
        for obj in calculations:
            got = _read(kernel, principal, 'documents.get', {'id': (obj.target or {}).get('id')}) or {}
            derivation = (got.get('document') or {}).get('derivation') or {}
            inputs = ', '.join('%s %s %s' % (i.get('cell'), i.get('value'), i.get('unit')) for i in derivation.get('inputs') or ())
            sheet = field.get('office:' + str(derivation.get('sheet')))
            add('number', '%s — %s%s%s — %s' % (str(obj.title).rstrip(), (derivation.get('recipe') or {}).get('expression') or 'its recipe cannot be read',
                                                 (', from “%s”' % sheet.title) if sheet is not None else '', (' (%s)' % inputs) if inputs else '',
                                                 'agrees with its sheet' if obj.state == 'current' else 'no longer agrees with its sheet' if obj.state == 'recheck' else str(obj.state)), obj.id)
    sources = [obj for obj in things if obj.kind == 'source']
    if sources:
        add('title', 'Where it comes from')
        for obj in sources:
            rests = len(field.feeds(obj.id))
            add('source', '%s — %s — %s on it' % (str(obj.title).rstrip(), obj.state or 'not decided', ('%s rests' % _plural(rests, 'thing')) if rests == 1 else ('%s rest' % _plural(rests, 'thing'))), obj.id)
    more = {part: count - PER_PART for part, count in said.items() if part not in ('head', 'title', 'foot') and count > PER_PART}
    if more:
        add('foot', 'Left out to keep this brief: %s. The Field has them all.' % ', '.join('%d more under %s' % (count, {
            'stands': 'what stands', 'waits': 'what waits', 'doubt': 'what I doubt', 'cannot tell': 'what I cannot tell', 'number': 'the numbers', 'source': 'where it comes from'}.get(part, part))
            for part, count in more.items()))
    add('foot', 'To see the evidence for any line: select the thing in the Field (F9), then X doubts it, T traces it, D says what can be done.')
    return {'title': '%s · brief' % desk, 'lines': lines, 'fingerprint': fingerprint(field),
            'counts': {'things': len(things), 'stand': len(standing_now), 'wait': len(waiting), 'doubts': len(doubts), 'cannot_tell': len(unsure)}}


STYLE = {'title': 'Heading2'}


def _words_digest(text):
    return hashlib.sha256(str(text).encode('utf-8')).hexdigest()


def keep(kernel, principal, shown=None):
    """Write the brief of the desk as it is now, as a page. A brief already on the desk is replaced by the new one (it stays in
    Documents). `shown` is the fingerprint of the desk whose brief the owner was shown: when it is given and the desk is no
    longer that desk, nothing is written, so what is kept is what was read. Returns the new page and what it took the place of."""
    from . import documents
    from .field_source import read_field
    field, _ = read_field(kernel, principal)
    made = compose(kernel, principal, field)
    if shown and shown != made['fingerprint']:
        raise ValueError('The desk has changed since this brief was shown, so it was not kept. B reads it again.')
    prior = next((obj for obj in field.objects if is_brief(obj)), None)
    blocks = [documents.block(line['text'], 'Heading1' if at == 0 else STYLE.get(line['part'], 'Normal')) for at, line in enumerate(made['lines'])]
    mark = {'profile': PROFILE, 'fingerprint': made['fingerprint'], 'written': time.time(), 'counts': made['counts'],
            'words': _words_digest('\n'.join(line['text'] for line in made['lines']))}
    if prior is not None:mark['replaces'] = prior.target['id']
    doc = documents.create(kernel, {'title': made['title'], 'origin': 'SLATE'}, principal, brief=mark, blocks=blocks)
    return {'document': {'id': doc['id'], 'title': doc.get('title'), 'revision': doc.get('revision')}, 'lines': len(made['lines']),
            'replaces': ('document:' + prior.target['id']) if prior is not None else '', 'counts': made['counts']}


def standing(kernel, principal, got, field):
    """For Stacy's doubt of a page: when the page is a kept brief, whether it is still the desk as it is."""
    mark = (got.get('document') or {}).get('brief') or {}
    if mark.get('profile') != PROFILE:
        return []
    see = 'field.brief | pick lines | select text'
    out = [Doubt('holds', 'the desk as it is', 'nothing on the desk has changed since this brief was written', see) if mark.get('fingerprint') == fingerprint(field) else
           Doubt('doubt', 'the desk as it is', 'the desk has changed since this brief was written; B writes it again', see)]
    if mark.get('words') and mark['words'] != _words_digest(str(got.get('plain') or '')):
        out.append(Doubt('note', 'its words', 'this page was edited after Stacy wrote it: some of its lines are yours now, and not every line is read from a record',
                         'documents.get %s | pick events | select revision,actor,action,at' % json.dumps({'id': (got.get('document') or {}).get('id')}, separators=(',', ':'))))
    return out
