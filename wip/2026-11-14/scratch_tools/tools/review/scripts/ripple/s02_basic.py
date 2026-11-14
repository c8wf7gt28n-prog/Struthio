import json
f = d('field.read')
ids = {o['title']: o['id'] for o in f['objects']}
bench = ids['07 Bench readings']; revb = ids['07 Limits Rev B CURRENT']; reva = ids['07 Limits Rev A ARCHIVED']
def show(r):
    if 'ERROR' in r: print('  ERROR', r['ERROR']); return
    print('  would_move', r['would_move'], 'cannot_tell', r['cannot_tell'], 'untouched', r['untouched'], 'set', r['set'])
    for row in r['rows']:
        print('   -', row['way'], '|', row['kind'], '|', row['title'][:50], '|', row['says_now'], '->', row['would_be'], '| moves', row['moves'], '|', row['why'][:230])
page = d('documents.get', {'id': ids['07 Case conclusion · HOLD'].split(':',1)[1]})
print('PAGE plain:', page.get('plain'))
inv = d('investigation.list')
print(inv)
for i in inv['investigations']:
    s = d('investigation.sheet', {'id': i['id']})
    for c in s['checked']: print('CHECK', {k: c[k] for k in ('claim','claim_text','program','expect','value','oracle','last_outcome','refutes')})
    for r in s['read']: print('READ', r['address'], r['state'])
for name, ident, st in (('bench B3=320', bench, {'B3': '320'}), ('bench B2=24', bench, {'B2': '24'}), ('bench B5=100', bench, {'B5': '100'}),
                        ('revb B4=100', revb, {'B4': '100'}), ('revb pulse duration', revb, {'pulse duration': '100'}), ('reva B3=10', reva, {'B3': '10'}),
                        ('calc settled current', ids['07 Settled power · 3.36 W'], {'settled current': '320'})):
    print(name); show(d('field.ripple', {'id': ident, 'set': st}))
