import json
from workbench.engine import engineering
k = engineering(w.root)
def d(op, a):
    r = k.dispatch(op, a, operator()); return r['result'] if r.get('ok') else {'ERROR': (r.get('error') or {}).get('message')}
f = d('field.read', {})
ids = {o['title']: o['id'] for o in f['objects']}
bench = ids['07 Bench readings']; revb = ids['07 Limits Rev B CURRENT']; calc = next(i for t_, i in ids.items() if t_.startswith('07 Settled power'))
for name, ident, setting in (('bench B3=320', bench, {'B3': '320'}), ('rev B pulse duration=100', revb, {'pulse duration': '100'}), ('calc settled_current=320', ids[calc] if calc in ids else calc, {'settled_current': '320'}),
                             ('bad cell', bench, {'Z9': '1'}), ('bad number', bench, {'B3': 'lots'}), ('a finding', next(o['id'] for o in f['objects'] if o['kind'] == 'finding'), {'B3': '1'})):
    r = d('field.ripple', {'id': ident, 'set': setting})
    print('RIPPLE', name, '->', r.get('ERROR') or 'would move %s · cannot tell %s · untouched %s' % (r['would_move'], r['cannot_tell'], r['untouched']))
    for row in r.get('rows', ()): print('    ', row['way'], '|', row['kind'], '|', row['title'][:44], '|', row['says_now'][:30], '->', row['would_be'][:34], '|', row['moves'], '|', row['why'][:150])
r = k.dispatch('language.run', {'text': 'field.ripple {"id":"%s","set":{"B4":"100"}} | pick rows | where moves=yes | select way,title,would_be' % revb}, operator())
print('STAC', r.get('ok'), json.dumps(r.get('result') if r.get('ok') else r.get('error'), ensure_ascii=False)[:400])
print('DOUBT desk:', {key: d('field.doubt', {}).get(key) for key in ('doubts', 'cannot_tell', 'looked_at')})
for o in f['objects']:
    if o['kind'] in ('document', 'sheet') or 'ran 30 ms' in o['title']:
        r = d('field.doubt', {'id': o['id']})
        print('DOUBT', o['kind'], o['title'][:40])
        for row in r.get('rows', ()): print('    ', row['verdict'], '|', row['about'], '|', row['why'][:230])
b = d('field.brief', {})
print('BRIEF', b.get('title'), b.get('counts'), (b.get('fingerprint') or '')[:12])
for line in b.get('lines', ()): print('   [%s] %s' % (line['part'], line['text'][:210]))
