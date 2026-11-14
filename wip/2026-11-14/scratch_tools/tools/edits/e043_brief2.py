import io
def edit(p, pairs):
    t = io.open(p, encoding='utf8').read()
    for old, new in pairs:
        assert t.count(old) == 1, (p, t.count(old), old[:80])
        t = t.replace(old, new)
    io.open(p, 'w', encoding='utf8').write(t)
W = '/home/user/Struthio/workbench/'
edit(W + 'field_brief.py', [
('''    quiet = {obj.id for obj in field.objects if is_brief(obj) or obj.kind == 'job'}
    things = sorted([obj.id, obj.kind, str(obj.title), str(obj.state)] for obj in field.objects if obj.id not in quiet)
''', '''    quiet = {obj.id for obj in field.objects if is_brief(obj) or obj.kind == 'job'}
    # The facts a sheet carries (a revision, a version, what it stands on) are part of it: a record that was saved again
    # is a changed desk even when no state moved, because a doubt may have come or gone with it.
    things = sorted([obj.id, obj.kind, str(obj.title), str(obj.state), [str(line) for line in obj.lines]] for obj in field.objects if obj.id not in quiet)
'''),
('''def compose(kernel, principal, field, now=None):
    """The brief of this Field: {'title', 'lines': [{'part', 'text', 'about'}], 'fingerprint', 'counts'}. A read."""
    kernel = _Once(kernel);things = [obj for obj in field.objects if not is_brief(obj)]
    desk = str(field.title or 'This workspace').split('  ·  ')[0].strip() or 'This workspace'
    lines = [];add = lambda part, text, about='': lines.append({'part': part, 'text': text, 'about': about})
''', '''PER_PART = 24                 # a brief is brief: each part says at most this many lines and then how many more there are


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
'''),
('''    add('foot', 'To see the evidence for any line: select the thing in the Field (F9), then X doubts it, T traces it, D says what can be done.')
    return {'title': '%s · brief' % desk, 'lines': lines, 'fingerprint': fingerprint(field),
''', '''    more = {part: count - PER_PART for part, count in said.items() if part not in ('head', 'title', 'foot') and count > PER_PART}
    if more:
        add('foot', 'Left out to keep this brief: %s. The Field has them all.' % ', '.join('%d more under %s' % (count, {
            'stands': 'what stands', 'waits': 'what waits', 'doubt': 'what I doubt', 'cannot tell': 'what I cannot tell', 'number': 'the numbers', 'source': 'where it comes from'}.get(part, part))
            for part, count in more.items()))
    add('foot', 'To see the evidence for any line: select the thing in the Field (F9), then X doubts it, T traces it, D says what can be done.')
    return {'title': '%s · brief' % desk, 'lines': lines, 'fingerprint': fingerprint(field),
'''),
('''def keep(kernel, principal):
    """Write the brief of the desk as it is now, as a page. A brief already on the desk is replaced by the new one (it stays in
    Documents). Returns the new page and what it took the place of."""
    from . import documents
    from .field_source import read_field
    field, _ = read_field(kernel, principal)
    made = compose(kernel, principal, field)
    prior = next((obj for obj in field.objects if is_brief(obj)), None)
    blocks = [documents.block(line['text'], 'Heading1' if at == 0 else STYLE.get(line['part'], 'Normal')) for at, line in enumerate(made['lines'])]
    mark = {'profile': PROFILE, 'fingerprint': made['fingerprint'], 'written': time.time(), 'counts': made['counts']}
''', '''def _words_digest(text):
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
            'words': _words_digest('\\n'.join(line['text'] for line in made['lines']))}
'''),
('''    see = 'field.brief | pick lines | select text'
    if mark.get('fingerprint') == fingerprint(field):
        return [Doubt('holds', 'the desk as it is', 'nothing on the desk has changed since this brief was written', see)]
    return [Doubt('doubt', 'the desk as it is', 'the desk has changed since this brief was written; B writes it again', see)]
''', '''    see = 'field.brief | pick lines | select text'
    out = [Doubt('holds', 'the desk as it is', 'nothing on the desk has changed since this brief was written', see) if mark.get('fingerprint') == fingerprint(field) else
           Doubt('doubt', 'the desk as it is', 'the desk has changed since this brief was written; B writes it again', see)]
    if mark.get('words') and mark['words'] != _words_digest(str(got.get('plain') or '')):
        out.append(Doubt('note', 'its words', 'this page was edited after Stacy wrote it: some of its lines are yours now, and not every line is read from a record',
                         'documents.get %s | pick events | select revision,actor,action,at' % json.dumps({'id': (got.get('document') or {}).get('id')}, separators=(',', ':'))))
    return out
''')])
edit(W + 'field_doubt.py', [('''    def dispatch(self, operation, arguments, principal):
        key = (operation, json.dumps(arguments, sort_keys=True, default=str))
        if key not in self.seen:self.seen[key] = self.kernel.dispatch(operation, arguments, principal)
        return self.seen[key]
''', '''    def dispatch(self, operation, arguments, principal):
        key = (operation, json.dumps(arguments, sort_keys=True, default=str))
        if key not in self.seen:self.seen[key] = self.kernel.dispatch(operation, arguments, principal)
        return self.seen[key]

    def __getattr__(self, name):               # whatever else is asked of it (its workspace, its store) is the Kernel's own
        return getattr(self.kernel, name)
''')])
edit(W + 'field_service.py', [('''    'field.brief.keep': ({}, []),
''', '''    'field.brief.keep': ({'shown': {'type': 'string', 'minLength': 64, 'maxLength': 64}}, []),
'''), ('''        from .field_brief import keep
        return {'schema': SCHEMA, **keep(kernel, principal)}
''', '''        from .field_brief import keep
        return {'schema': SCHEMA, **keep(kernel, principal, args.get('shown'))}
'''), ('''  field.brief.keep  execute  {}     the brief written as a page in Documents; a later one takes its place
''', '''  field.brief.keep  execute  {shown?}   the brief written as a page in Documents; a later one takes its place. `shown` is
                                        the fingerprint field.brief gave: with it, nothing is kept if the desk has changed since
''')])
edit(W + 'field_page.py', [('''    title = str(page.view.field.title or host.root.name).split('  ·  ')[0]
    face.answer_in_stac({'title': title, 'stac': 'field.brief | pick lines | select text', 'kind': 'desk', 'whole': True},
                        'The desk, written up from the records. This is what the page would say:')
    step = Step('Keep the brief as a page', 'write', op('field.brief.keep'),
''', '''    from .field_brief import fingerprint
    page.refresh(force=True)                   # the brief is of the desk as it is: read first, so what is shown and what would be kept are the same desk
    title = str(page.view.field.title or host.root.name).split('  ·  ')[0]
    face.answer_in_stac({'title': title, 'stac': 'field.brief | pick lines | select text', 'kind': 'desk', 'whole': True},
                        'The desk, written up from the records. This is what the page would say:')
    step = Step('Keep the brief as a page', 'write', op('field.brief.keep', shown=fingerprint(page.view.field)),
''')])
edit(W + 'field_qt.py', [('''            while self._trail:
                ident = self._trail.pop()
                if ident != self.field.selected and self.field.get(ident) is not None:
                    self._last = '';self.field.select(ident);break      # going back is not a step forward: it leaves no trail of its own
            else:
                return
''', '''            at = next((n for n in range(len(self._trail) - 1, -1, -1) if self._trail[n] != self.field.selected and self.field.get(self._trail[n]) is not None), None)
            if at is None:return                  # nothing on this face to go back to; what was visited on another face is kept for when it shows again
            ident = self._trail[at];del self._trail[at:]
            self._last = '';self.field.select(ident)      # going back is not a step forward: it leaves no trail of its own
''')])
print('ok')
