import json
from workbench.engine import engineering
from workbench import field_doubt
k = engineering(w.root)
def d(op, a):
    r = k.dispatch(op, a, operator()); return r['result'] if r.get('ok') else {'ERROR': (r.get('error') or {}).get('message')}
def cell(typ, value, unit=''): return {'type': typ, 'value': value, 'unit': unit, 'formula': None}
# -- the counted-twice rule on its own, as a pure function
mixed = {'B2': cell('number', '1', 'V'), 'B3': cell('number', '2', 'A'), 'B4': cell('number', '3', 'mV'), 'B5': cell('number', '6', 'ms')}
print('PURE mixed units ->', [(x.verdict, x.about) for x in field_doubt._counted_twice('owner:x', mixed)])
money = {'A2': cell('text', 'Enclosure'), 'B2': cell('number', '40'), 'A3': cell('text', 'Board'), 'B3': cell('number', '25'), 'A4': cell('text', 'Parts subtotal'), 'B4': cell('number', '65'),
         'A5': cell('text', 'Cable'), 'B5': cell('number', '5'), 'A6': cell('text', 'Total'), 'B6': cell('number', '135')}
for x in field_doubt._counted_twice('owner:x', money): print('PURE money ->', x.verdict, '|', x.why, '|', x.see[:90])
plain = {**money, 'A4': cell('text', 'Fixings')}
for x in field_doubt._counted_twice('owner:x', plain): print('PURE unnamed ->', x.verdict, '|', x.why[:200])
fine = {**money, 'B6': cell('number', '70')}
print('PURE honest total ->', [(x.verdict, x.about) for x in field_doubt._counted_twice('owner:x', fine)])
# -- through the records: a CSV brought in as a sheet
path = w.root / 'costs_07.csv'; path.write_text('Item,Cost\nEnclosure,40\nBoard,25\nParts subtotal,65\nCable,5\nTotal,135\n')
pre = d('office.import.preview', {'path': str(path), 'csv': {'columns': {'B': 'number'}, 'units': {'B': 'EUR'}, 'header_rows': 1}})
print('IMPORT preview keys', sorted(pre)[:12], pre.get('ERROR'))
plan = pre.get('plan') if isinstance(pre.get('plan'), str) else (pre.get('plan') or {}).get('id') or pre.get('id')
com = d('office.import.commit', {'plan': plan, 'expected_digest': pre.get('digest') or pre.get('expected_digest') or (pre.get('plan') or {}).get('digest') if not isinstance(pre.get('plan'), str) else pre.get('digest')})
print('IMPORT commit', {key: (str(v)[:60]) for key, v in com.items()} if isinstance(com, dict) else com)
f = d('field.read', {})
for o in f['objects']:
    if o['kind'] == 'sheet' and 'cost' in o['title'].lower():
        print('SHEET on field', o['title'], o['state'])
        for row in d('field.doubt', {'id': o['id']}).get('rows', ()): print('    ', row['verdict'], '|', row['about'], '|', row['why'][:260])
print('field aside:', f.get('elsewhere'), '| sheets:', [o['title'] for o in f['objects'] if o['kind'] == 'sheet'])
# -- a prefix slip and the same quantity under another prefix, in new findings
inv = 'c574ae94d79542f582932d151fad631f'
inv = next(o for o in f['objects'] if o['kind'] == 'finding')['id'] and d('investigation.list', {})['investigations'][0]['id']
for text in ('Settled draw is 3360 mW.', 'Settled draw is 3.36 mW.', 'Total cost came to 13.36 W of nonsense.'):
    made = d('investigation.claim', {'id': inv, 'text': text, 'role': 'FINDING'}); print('CLAIM', text, '->', str(made)[:90])
f = d('field.read', {})
for o in f['objects']:
    if o['kind'] == 'finding' and ('3360' in o['title'] or '3.36 mW' in o['title'] or '13.36' in o['title']):
        rows = d('field.doubt', {'id': o['id']}).get('rows', ())
        print('NUMBERS of', o['title'], '->', [(r['verdict'], r['why'][:150]) for r in rows if r['about'] == 'its numbers'])
# -- a narrowed check on a number cell, then a ripple that would break it
revb = next(o['id'] for o in f['objects'] if o['title'].startswith('07 Limits Rev B'))
claim = next(o['id'] for o in f['objects'] if o['title'].startswith('Rev A allowed 120 ms'))[len('claim:'):]
print('ADD SOURCE', d('investigation.add_source', {'id': inv, 'address': revb}).get('ERROR', 'ok'))
chk = d('investigation.check', {'claim': claim, 'program': '@%s | pick document.sheets | select cells.B4.value' % revb, 'oracle': 'Cell B4 still says 80.', 'expect': 'CONTAINS', 'value': '"cells.B4.value": "80"', 'refutes_on_fail': True})
print('CHECK bound', chk.get('ERROR', 'ok')); ran = d('investigation.continue', {'id': inv}); print('RAN', [(x.get('outcome')) for x in ran.get('ran', [])] if isinstance(ran, dict) else ran)
r = d('field.ripple', {'id': revb, 'set': {'B4': '100'}})
for row in r.get('rows', ()):
    if row['way'] in ('checks it', 'watches it'): print('RIPPLE', row['way'], '|', row['title'][:44], '|', row['says_now'], '->', row['would_be'], '|', row['why'][:170])
r = d('field.ripple', {'id': revb, 'set': {'B4': '80'}})
print('RIPPLE same value ->', r.get('would_move'), [(row['way'], row['moves'], row['would_be']) for row in r.get('rows', ())][:4])
# -- a check on a calculation's page, by its address
calc = next(o for o in f['objects'] if o['kind'] == 'calculation' and 'Settled' in o['title'])
r = k.dispatch('language.run', {'text': '@%s | pick document.derivation.calculation.outputs | select value.decimal,value.unit' % calc['id']}, operator())
print('@document form ->', r.get('ok'), json.dumps((r.get('result') or {}).get('rows') if r.get('ok') else r.get('error'), ensure_ascii=False)[:160])
