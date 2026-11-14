import json
f = d('field.read')
for o in f['objects']:
    if o['kind'] == 'sheet':
        g = d('office.get', {'id': o['id'].split(':',1)[1]})
        cells = g['document']['sheets'][0]['cells']
        print('==', o['title'], g['version'], g['revision'][:8], {k:v for k,v in g['document'].items() if k!='sheets'}, {k:v for k,v in g['document']['sheets'][0].items() if k!='cells'})
        for name in sorted(cells, key=lambda n:(int(n[1:]), n[0])):
            c = cells[name]; print('   ', name, c['type'], repr(c['value']), repr(c['unit']), c.get('formula'), c.get('cache_state'))
        print([ (r['sheet_row'], r['parameter'], r['value'], r['unit'], r['conditions']) for r in g['origin']['reviewed_rows']])
    if o['kind'] in ('document','calculation'):
        g = d('documents.get', {'id': o['id'].split(':',1)[1]})
        print('==', o['title'], list(g.keys()))
        print(repr(g.get('plain')))
        doc = g['document']
        print({k:(v if k not in ('blocks','derivation') else '...') for k,v in doc.items()})
        if doc.get('derivation'): print(json.dumps(doc['derivation'])[:1800])
for inv in d('investigation.list')['investigations']:
    s = d('investigation.sheet', {'id': inv['id']})
    print(list(s.keys()))
    print(json.dumps(s.get('checked'), indent=0)[:1500])
    print(json.dumps(s.get('learned'), indent=0)[:1500])
