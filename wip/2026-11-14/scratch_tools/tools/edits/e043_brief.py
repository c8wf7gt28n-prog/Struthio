import io
def edit(p, pairs):
    t = io.open(p, encoding='utf8').read()
    for old, new in pairs:
        assert t.count(old) == 1, (p, t.count(old), old[:70])
        t = t.replace(old, new)
    io.open(p, 'w', encoding='utf8').write(t)
W = '/home/user/Struthio/workbench/'

edit(W + 'documents.py', [('''def create(kernel, args, principal, derivation=None):
    blocks = normalize_blocks(from_text(args.get('text', '')))
''', '''def create(kernel, args, principal, derivation=None, brief=None, blocks=None):
    """`derivation` is for a calculation worked out from a sheet; `brief` marks a page written from the whole desk
    (workbench/field_brief.py), which may bring its own styled blocks. Neither can be set through the operation."""
    blocks = normalize_blocks(blocks if blocks is not None else from_text(args.get('text', '')))
'''), ('''        if derivation:
            doc['derivation'] = derivation
''', '''        if derivation:
            doc['derivation'] = derivation
        if brief:
            doc['brief'] = brief
''')])

edit(W + 'field_source.py', [('''            derivation = (got.get('document') or {}).get('derivation')
            if derivation and derivation.get('replaces'):''', '''            derivation = (got.get('document') or {}).get('derivation')
            mark = (got.get('document') or {}).get('brief')
            if isinstance(mark, dict) and mark.get('profile') == 'field-brief/1':      # the desk written up from the records: a page that knows which desk it described
                if mark.get('replaces'):self.replaced.add('document:' + str(mark['replaces']))
                self.briefs[ident] = mark
                self.add(FieldObject(ident, 'document', row.get('title') or row['id'], 'the desk written up from the records', STATE_CURRENT,
                                     ('revision %s' % row['revision'],) if row.get('revision') is not None else (), '', target, 'BRIEF',
                                     stac='documents.get %s | pick document.blocks | select text' % stac_json(id=row['id'])));continue
            if derivation and derivation.get('replaces'):'''),
    ('''        gone = {obj.id for obj in reader.objects if obj.id in reader.replaced and obj.kind == 'calculation'}
        reader.objects = [obj for obj in reader.objects if obj.id not in gone]
        reader.links = [link for link in reader.links if link.source not in gone and link.target not in gone]
        reader.retired = len(gone)
''', '''        gone = {obj.id for obj in reader.objects if obj.id in reader.replaced and (obj.kind == 'calculation' or obj.tag == 'BRIEF')}
        reader.objects = [obj for obj in reader.objects if obj.id not in gone]
        reader.links = [link for link in reader.links if link.source not in gone and link.target not in gone]
        reader.retired = len([ident for ident in gone if ident not in reader.briefs])
'''),
    ('''    return Field(reader.objects, reader.links, title, note=_left_out(reader), aside=aside, moved=moved), reader
''', '''    field = Field(reader.objects, reader.links, title, note=_left_out(reader), aside=aside, moved=moved)
    if reader.briefs:        # a kept brief describes one desk: when the desk is no longer that one, the brief waits to be written again
        from .field_brief import fingerprint
        now = fingerprint(field)
        for obj in field.objects:
            mark = reader.briefs.get(obj.id)
            if mark is not None and mark.get('fingerprint') != now:
                obj.state = STATE_RECHECK;obj.lines = ('the desk changed since it was written',) + tuple(obj.lines)[:1]
    return field, reader
''')])
t = io.open(W + 'field_source.py', encoding='utf8').read()
import re
m = re.search(r"\n(\s+)self\.replaced = set\(\)", t)
print('replaced init:', repr(t[m.start():m.start() + 200]) if m else None)
