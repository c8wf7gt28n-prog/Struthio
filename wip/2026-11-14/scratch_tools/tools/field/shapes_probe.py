import json
k = w.ledger_bridge.kernel; p = operator()
def op(name, args=None):
    r = k.dispatch(name, args or {}, p); return r['result'] if r['ok'] else {'REFUSED': r['error']['message']}
desk = op('field.read')
calc = next(o for o in desk['objects'] if o['kind'] == 'calculation'); sheet = next(o for o in desk['objects'] if o['kind'] == 'sheet')
d = op('documents.get', {'id': calc['id'].split(':', 1)[1]})['document']['derivation']
print('derivation input:', json.dumps(d['inputs'][1], ensure_ascii=False)[:600])
print('calculation outputs:', json.dumps(d['calculation'].get('outputs'), ensure_ascii=False)[:300])
for row in desk['objects']:
    if row['kind'] != 'sheet': continue
    s = op('office.get', {'id': row['id'].split(':', 1)[1]})
    cells = s['document']['sheets'][0]['cells']
    print('\nsheet', row['title'], '| source_state', s.get('source_state'), '| origin keys', sorted(s['origin']))
    print('  reviewed_rows[0]:', json.dumps(s['origin']['reviewed_rows'][0], ensure_ascii=False)[:420])
    for r_ in range(1, 6):
        line = [str((cells.get('%s%d' % (c, r_)) or {}).get('value', '')) for c in 'ABCD']
        if any(line): print('  row %d:' % r_, ' | '.join(line)[:200])
    print('  a cell:', json.dumps(cells.get('B2'), ensure_ascii=False)[:200])
inv = next(o for o in desk['objects'] if o['kind'] == 'finding'); f = op('field.read')
import re
for o in desk['objects']:
    if o['kind'] in ('finding', 'question'): print('\n', o['kind'], '|', o['title'], '|', o['id'], '| facts', o['facts'])
obj = next(o for o in __import__('workbench.field_source', fromlist=['read_field']).read_field(k, p)[0].objects if o.kind == 'finding')
sh = op('investigation.sheet', {'id': obj.target['id']})
print('\nchecked rows:', json.dumps(sh['checked'], ensure_ascii=False)[:900])
pa = op('investigation.path', {'claim': obj.id.split(':', 1)[1]}); print('\npath keys:', sorted(pa), '| support', pa.get('independent_support'), '| review', pa.get('review')); print('path step:', json.dumps(pa['path'][0], ensure_ascii=False)[:300])
