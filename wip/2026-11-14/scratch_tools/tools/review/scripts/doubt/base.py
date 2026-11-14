import json
f = d('field.read')
for o in f['objects']:
    print(o['kind'], '|', o['id'], '|', o['title'], '|', o['state'], '|', o['facts'])
print('moved', f['moved'])
for l in f['links']: print('  ', l['from'], '->', l['to'], l['label'], l['stale'])
print()
for o in f['objects']:
    r = d('field.doubt', {'id': o['id']})
    print('==', o['kind'], o['title'])
    for row in r.get('rows', [r]):
        print('   ', row.get('verdict'), '|', row.get('about'), '|', row.get('why'))
