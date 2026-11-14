import json
f = d('field.read')
for o in f['objects']:
    print(o['kind'], '|', o['id'], '|', o['title'], '|', o['state'], '|', o.get('tag'))
print('LINKS')
for l in f.get('wires', f.get('links', [])):
    print(l)
print(list(f.keys()))
for o in f['objects']:
    if o['kind'] == 'sheet':
        got = d('office.get', {'id': o['id'].split(':',1)[1]})
        print('SHEET', o['title'], list(got.keys()))
        cells = got['document']['sheets'][0]['cells']
        for name in sorted(cells, key=lambda n:(int(''.join(c for c in n if c.isdigit())), n)):
            print('  ', name, cells[name])
        print('  origin keys', list((got.get('origin') or {}).keys()), 'source_state', got.get('source_state'))
    if o['kind'] == 'calculation':
        got = d('documents.get', {'id': o['id'].split(':',1)[1]})
        der = got['document']['derivation']
        print('CALC', o['title'], json.dumps({k: der[k] for k in ('sheet','recipe','inputs')}, default=str)[:1500])
        print('   out', der['calculation']['outputs'][0]['value'])
