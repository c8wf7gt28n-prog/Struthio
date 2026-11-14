import io
def edit(p, pairs):
    t = io.open(p, encoding='utf8').read()
    for old, new in pairs:
        assert t.count(old) == 1, (p, t.count(old), old[:70])
        t = t.replace(old, new)
    io.open(p, 'w', encoding='utf8').write(t)
W = '/home/user/Struthio/workbench/'
edit(W + 'field_source.py', [('''        self.replaced = set()        # calculations another calculation says it replaces (a recheck makes a new page)
''', '''        self.replaced = set()        # calculations another calculation says it replaces (a recheck makes a new page)
        self.briefs = {}             # a kept brief's id -> its mark (the fingerprint of the desk it was written from)
''')])
edit(W + 'field_service.py', [('''  field.ripple  read   {id, set}    a cell set to another value and followed along the wires: everything that would move
''', '''  field.ripple  read   {id, set}    a cell set to another value and followed along the wires: everything that would move
  field.brief   read   {}           the desk written up as one page, line by line, from the records (no model)

One operation here changes something, and so it is not a read and waits for the owner wherever it is offered:

  field.brief.keep  execute  {}     the brief written as a page in Documents; a later one takes its place
'''), ('''  field.ripple {"id":"office:<id>","set":{"B4":"100"}} | pick rows | select way,kind,title,says_now,would_be,why
''', '''  field.ripple {"id":"office:<id>","set":{"B4":"100"}} | pick rows | select way,kind,title,says_now,would_be,why
  field.brief | pick lines | select text
  field.brief | pick lines | where part=doubt | select text
'''), ('''    'field.ripple': ({'id': TEXT, 'set': {'type': 'object'}}, ['id', 'set']),
}
SCOPES = {operation: 'read' for operation in FIELDS}
OBSERVERS = tuple(FIELDS)
''', '''    'field.ripple': ({'id': TEXT, 'set': {'type': 'object'}}, ['id', 'set']),
    'field.brief': ({}, []),
    'field.brief.keep': ({}, []),
}
WRITES = ('field.brief.keep',)
SCOPES = {operation: 'execute' if operation in WRITES else 'read' for operation in FIELDS}
OBSERVERS = tuple(operation for operation in FIELDS if operation not in WRITES)
'''), ('''def dispatch(kernel, operation, args, principal):
''', '''def brief(kernel, principal):
    """The desk written up from the records (workbench/field_brief.py). A read: this is what the page would say."""
    from .field_brief import compose
    from .field_source import read_field
    field, _ = read_field(kernel, principal)
    return {'schema': SCHEMA, **compose(kernel, principal, field)}


def dispatch(kernel, operation, args, principal):
    if operation == 'field.brief':return brief(kernel, principal)
    if operation == 'field.brief.keep':
        from .field_brief import keep
        return {'schema': SCHEMA, **keep(kernel, principal)}
''')])
edit(W + 'activity.py', [("""'field.read','field.trace','field.whatif','field.doubt','field.ripple'})""", """'field.read','field.trace','field.whatif','field.doubt','field.ripple','field.brief'})""")])
edit(W + 'field_do.py', [('''def _page(kernel, principal, obj, field):
    ident = obj.target['id']
    return [Step('Read its words', 'read', 'documents.get %s | pick document.blocks | select text' % js(id=ident)),
            Step('See its history', 'read', 'documents.get %s | pick events | select revision,actor,action,at' % js(id=ident))]
''', '''def _page(kernel, principal, obj, field):
    ident = obj.target['id']
    out = [Step('Read its words', 'read', 'documents.get %s | pick document.blocks | select text' % js(id=ident)),
           Step('See its history', 'read', 'documents.get %s | pick events | select revision,actor,action,at' % js(id=ident))]
    if obj.tag == 'BRIEF':                    # the desk written up: what it would say now, and writing it again when the desk has moved on
        out.insert(1, Step('See what it would say now', 'read', 'field.brief | pick lines | select text'))
        if obj.state == 'recheck':
            out.insert(1, Step('Write it again', 'write', op('field.brief.keep'),
                               'the desk as it is now, as a new page; this one is kept in Documents', 'execute', True))
    return out
'''), ('''    if steps and obj.kind in ('calculation', 'sheet', 'finding', 'condition', 'source'):   # it can be cross-examined
''', '''    if steps and obj.kind in ('calculation', 'sheet', 'finding', 'condition', 'source', 'document'):   # it can be cross-examined
'''), ('''    for obj, _, steps in waiting:
        step = next((step for step in steps if step.kind == 'write' and step.settles), None)
        if step is not None and step.line not in seen:
            plan.append((obj, step));seen.add(step.line)
    return plan
''', '''    for obj, _, steps in waiting:
        step = next((step for step in steps if step.kind == 'write' and step.settles), None)
        if step is not None and step.line not in seen:
            plan.append((obj, step));seen.add(step.line)
    plan.sort(key=lambda pair: pair[0].tag == 'BRIEF')      # the brief is written last: it describes the desk the other changes leave
    return plan
''')])
print('ok')
