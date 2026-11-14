import json
k = w.ledger_bridge.kernel; p = operator()
r = k.dispatch('ledger.explore', {'kind': 'INSTRUMENT'}, p)
rows = r['result']['instruments']
print('instruments:', len(rows)); print(json.dumps(rows[0], ensure_ascii=False)[:1500])
print(json.dumps(next(x for x in rows if x['id'] in ('freecad', 'instrument:freecad') or 'FreeCAD' in json.dumps(x)), ensure_ascii=False)[:1500])
for x in rows: print('  %-16s %-26s %-12s avail=%-5s %-18s %s' % (x.get('id'), x.get('title'), x.get('group'), x.get('view_available'), x.get('status') or x.get('state'), str(x.get('availability') or x.get('missing') or x.get('reason') or '')[:70]))
