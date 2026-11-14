# the desk read through the Kernel and through staC
import json
k = w.ledger_bridge.kernel; p = operator()
def op(name, args=None):
    r = k.dispatch(name, args or {}, p); return r['result'] if r['ok'] else {'REFUSED': r['error']['message']}
def stac(line):
    r = k.dispatch('language.run', {'text': line}, p)
    rows = r['result']['rows'] if r['ok'] else None
    print('\nstaC › ' + line); print('   ' + ('REFUSED: ' + r['error']['message'] if rows is None else '%d rows' % len(rows)))
    for row in (rows or [])[:7]: print('   ', json.dumps(row, ensure_ascii=False)[:230])
head = op('ledger.journal.status').get('head')
desk = op('field.read'); print('field.read:', {key: (len(v) if isinstance(v, list) else v) for key, v in desk.items()})
calc = next(o for o in desk['objects'] if o['kind'] == 'calculation' and 'Settled' in o['title']); finding = next(o for o in desk['objects'] if o['kind'] == 'finding')
stac('field.read | pick waiting | select kind,title,state')
stac('field.read | pick objects | group kind | count')
stac('field.read | pick links | select from,to,label,stale | take 4')
stac('field.read | pick objects | where lately=yes | select kind,title,changed_at')
stac('field.trace %s | pick rows | select way,steps,kind,title,state,by' % json.dumps({'id': calc['id']}, separators=(',', ':')))
stac('field.trace %s | pick rows | select way,steps,kind,title,by' % json.dumps({'id': finding['id']}, separators=(',', ':')))
t = op('field.trace', {'id': calc['id']}); print('\ntrace summary:', {key: t[key] for key in ('comes_from', 'rests_on_it', 'stale_on_the_way')})
stac('field.whatif %s | select says_now,would_be,exact,set,changed' % json.dumps({'id': calc['id'], 'set': {'B3': '320'}}, separators=(',', ':')))
stac('field.whatif %s | pick rows | select input,cell,value,set,unit' % json.dumps({'id': calc['id'], 'set': {'settled_current': '320', 'voltage': '11.4'}}, separators=(',', ':')))
for bad in ({'B9': '1'}, {'B3': 'lots'}, {}):
    print('whatif', bad, '->', op('field.whatif', {'id': calc['id'], 'set': bad}).get('REFUSED'))
print('whatif on a plain page ->', op('field.whatif', {'id': next(o for o in desk['objects'] if o['kind'] == 'document')['id'], 'set': {'B3': '1'}}).get('REFUSED'))
print('trace of nothing ->', op('field.trace', {'id': 'document:nope'}).get('REFUSED'))
print('the sheet is untouched:', op('office.get', {'id': 'owner:db5f669f863d4c71b89fa7ba348957da'})['document']['sheets'][0]['cells']['B3']['value'], '| journal grew by:', op('ledger.journal.status').get('head') - head, '(language.run lines are journaled; the field reads themselves are not)')
