# probe4 (no model): what the worked case's records already say about "what comes next" for a finding and for a calculation.
import json, sqlite3, time
k = w.ledger_bridge.kernel; p = operator()
def d(op, args=None, principal=None): return k.dispatch(op, args or {}, principal or p)
def short(x, n=300):
    s = x if isinstance(x, str) else json.dumps(x, ensure_ascii=False, default=str)
    return s if len(s) <= n else s[:n] + '…'
print('== investigations in the worked case')
for inv in d('investigation.list')['result']['investigations']:
    s = d('investigation.sheet', {'id': inv['id']})['result']
    print(' ', inv['id'], '|', short(s['question'], 90), '|', s['state'], '|', short(s['reason'], 120))
    print('    budget', s['budget'], 'used', s['used'], '| next:', s['next'])
    for src in s['read']: print('    source', src['id'][:8], src['address'], src['state'], src['digest'][:10])
    for c in s['learned'] + s['unresolved']: print('    claim', c['id'][:8], c['role'], c['evidence_state'], c['review'], '|', short(c['text'], 110))
    for c in s['checked']: print('    check', c['id'][:8], c['expect'], repr(c['value']), c['last_outcome'], '|', short(c['program'], 160), '|', short(c['oracle'], 80))
    for st in s['attempted']: print('    step', st['seq'], st['kind'], st['outcome'], '|', short(st['program'], 140))
    inv_id = inv['id']
print('\n== the calculations: what documents.get says about whether they are current')
for doc in d('documents.list')['result']['documents']:
    full = d('documents.get', {'id': doc['id']})['result']
    der = full['document'].get('derivation') or {}
    print(' ', doc['id'], doc['title'], '| rev', full['document']['revision'], '| derivation profile:', der.get('profile'), '| source_state:', full.get('source_state'), '| keys:', sorted(full))
    if der: print('     sheet', der.get('sheet'), 'sheet_revision', str(der.get('sheet_revision'))[:12], '| recipe', der.get('recipe'))
calc = next(x for x in d('documents.list')['result']['documents'] if 'Settled' in x['title'])
# the recheck as the owner (approve) and as an assignment step (no approve)
r = d('office.datasheet.recheck', {'id': calc['id'], 'expected_revision': calc['revision']}, __import__('workbench.engineering_kernel', fromlist=['Principal']).Principal('desktop-owner', frozenset({'read', 'execute'})))
print('\noffice.datasheet.recheck without approve ->', r['ok'], '' if r['ok'] else r['error']['message'])
print('\n== investigation.refresh / continue on the worked case (execute scope)')
r = d('investigation.refresh', {'id': inv_id}); s = r['result'] if r['ok'] else None
print('refresh ->', r['ok'], short({'state': s['state'], 'reason': s['reason'], 'changed': s['changed'], 'next': s['next']} if s else r['error'], 600))
r = d('investigation.continue', {'id': inv_id}); s = r['result'] if r['ok'] else None
print('continue ->', r['ok'], short({'state': s['state'], 'reason': s['reason'], 'ran': s['ran'], 'authority': s['authority'], 'next': s['next']} if s else r['error'], 600))
print('\n== the Agenda and helpers, as they stand')
r = d('agenda.view'); print('agenda.view keys:', sorted(r['result']) if r['ok'] else r['error']); print('   ', short({kk: len(vv) if isinstance(vv, list) else vv for kk, vv in r['result'].items()}, 400))
r = d('helpers.list'); print('helpers.list:', short([(h.get('name'), h.get('uses'), h.get('state')) for h in r['result'].get('helpers', [])] if r['ok'] else r['error'], 600))
r = d('procedures.list'); print('procedures.list:', short(r['result'] if r['ok'] else r['error'], 200))
r = d('work.list'); print('work.list:', short(r['result'] if r['ok'] else r['error'], 200))
r = d('assignments.list'); print('assignments.list (project desk):', short(r['result'] if r['ok'] else r['error'], 300))
r = d('methods.list'); print('methods.list:', short(r['result'] if r['ok'] else r['error'], 300))
