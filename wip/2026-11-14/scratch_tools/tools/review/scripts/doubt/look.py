import json
f = d('field.read')
for o in f['objects']:
    if o['kind'] == 'sheet':
        g = d('office.get', {'id': o['id'].split(':',1)[1]})
        print('==', o['title'], list(g.keys()))
        print(json.dumps(g.get('origin'), indent=0)[:1500])
        print(json.dumps(g['document'], indent=0)[:2500])
        print('source_state', g.get('source_state'), 'rev', g.get('revision'), g.get('formula_values'))
    if o['kind'] == 'document':
        g = d('documents.get', {'id': o['id'].split(':',1)[1]})
        print('==', o['title'], list(g.keys()))
        print(g.get('plain'))
        print(json.dumps(g['document'], indent=0)[:1500])
