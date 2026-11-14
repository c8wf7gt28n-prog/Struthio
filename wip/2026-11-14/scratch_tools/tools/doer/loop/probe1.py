# probe1: what is in the worked case, then one assignment (numbers_on_page) stepped by hand through agent.step, every recorded step printed.
import json, sqlite3
k = w.ledger_bridge.kernel; p = operator()
def d(op, args=None, principal=None):
    return k.dispatch(op, args or {}, principal or p)
def short(x, n=260):
    s = x if isinstance(x, str) else json.dumps(x, ensure_ascii=False, default=str)
    return s if len(s) <= n else s[:n] + '…'

print('== registry'); from workbench import agent_loop, agent_profiles
print('PROFILES enum for agent.assign:', agent_loop.PROFILES)
for name, prof in agent_profiles.PROFILES.items(): print('  ', name, '| needs', prof.needs, '| fits?', callable(getattr(prof, 'fits', None)), '|', prof.words)
print('UNAVAILABLE:', agent_profiles.UNAVAILABLE)
print('scopes:', {op: agent_loop.SCOPES[op] for op in agent_loop.FIELDS})

print('\n== documents in the worked case')
r = d('documents.list'); docs = r['result']['documents'] if r['ok'] else []; print(r['ok'], len(docs))
for doc in docs: print('  ', doc['id'], '|', doc.get('title'), '| rev', doc.get('revision'))
page = docs[0]['id'] if docs else None
full = d('documents.get', {'id': page})['result']['document']
for b in full['blocks']: print('   block', b.get('id', '')[:8], '|', short(b['text'], 150))

print('\n== request_profile on sample requests')
for text in ('add up the numbers on this page', 'total the values here', 'find files about rail', 'what documents do we have on bench readings', 'what ports are open',
             'check this finding again', 'bring this calculation up to date', 'recheck the settled draw', 'summarise this page', 'what is talking to the network?'):
    print('   %-48r -> %s' % (text, agent_loop.request_profile(text)))

print('\n== agent.list before:', d('agent.list')['result'])

print('\n== ASSIGN numbers_on_page on', page)
r = d('agent.assign', {'request': 'add up the numbers on this page', 'context': {'document': page}})
print('ok', r['ok'], '' if r['ok'] else r['error'])
a = r['result']['assignment']; ident = a['id']
print('assignment row:', short({kk: a[kk] for kk in ('id', 'investigation', 'profile', 'state', 'reason', 'working_on', 'doing_now', 'steps_used', 'budget', 'driver')}, 600))
print('sheet keys:', sorted(r['result']['sheet']))
print('sheet.objective:', r['result']['sheet']['objective']); print('sheet.state/reason:', r['result']['sheet']['state'], '|', r['result']['sheet']['reason'])
n = 0
while n < 20:
    n += 1
    r = d('agent.step', {'id': ident})
    if not r['ok']: print('step refused:', r['error']); break
    res = r['result']; a = res['assignment']
    print(' step %d -> state %s | next: %s' % (n, a['state'], short(res['next'], 200)))
    print('      step row:', short(res['step'], 500))
    print('      doing_now:', short(a['doing_now'], 200), '| found:', short(a['found'], 300), '| needs_you:', short(a['needs_you'], 300))
    if res['step'] is None or a['state'] != 'RUNNING': break
print('final status:', short(d('agent.status', {'id': ident})['result']['assignments'][0], 1500))

print('\n== every inv_steps row of its investigation')
with k.db() as db:
    db.row_factory = sqlite3.Row
    for row in db.execute('SELECT * FROM inv_steps WHERE investigation=? ORDER BY seq', (a['investigation'],)):
        row = dict(row)
        print('  seq %d kind %s outcome %s authority %s dup %s' % (row['seq'], row['kind'], row['outcome'], row['authority'], row['duplicate_of']))
        print('     purpose:', row['purpose']); print('     program:', short(row['program'], 420)); print('     inputs :', short(row['inputs'], 300)); print('     summary:', short(row['summary'], 300))
    print('  agent_assignments row:')
    row = dict(db.execute('SELECT * FROM agent_assignments WHERE id=?', (ident,)).fetchone())
    for kk, vv in row.items(): print('     %-14s %s' % (kk, short(vv, 700)))
sheet = d('investigation.sheet', {'id': a['investigation']})['result']
print('investigation.sheet: state', sheet['state'], '| reason', sheet['reason'], '| used', sheet['used'], '| next', sheet['next'])
print('   read:', len(sheet['read']), 'attempted:', len(sheet['attempted']), 'checked:', len(sheet['checked']), 'learned:', len(sheet['learned']), 'unresolved:', [(c['role'], c['text'], c['evidence_state']) for c in sheet['unresolved']])

print('\n== the page after')
full = d('documents.get', {'id': page})['result']['document']; print('revision', full['revision'])
for b in full['blocks'][-3:]: print('   block', b.get('id', '')[:8], '|', short(b['text'], 300))
r = d('conditions.list', {}); print('conditions.list:', r['ok'], short(r['result'] if r['ok'] else r['error'], 1200))
