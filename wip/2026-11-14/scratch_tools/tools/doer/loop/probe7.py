# probe7 (no model): (a) a finished assignment's recorded steps run again as an operation_sequence; (b) a changed source under a finding:
# the investigation's own machinery, and the prototype waiting for the owner's approve-scoped decision.
import json, sqlite3, time, re, sys
sys.path.insert(0, '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/doer/loop')
import proto_profiles
from workbench import agent_loop, agent_qt
k = w.ledger_bridge.kernel; p = operator()
def d(op, args=None, principal=None): return k.dispatch(op, args or {}, principal or p)
def short(x, n=300):
    s = x if isinstance(x, str) else json.dumps(x, ensure_ascii=False, default=str)
    return s if len(s) <= n else s[:n] + '…'
def rows_of(inv):
    with k.db() as db:
        db.row_factory = sqlite3.Row
        return [dict(r) for r in db.execute('SELECT * FROM inv_steps WHERE investigation=? ORDER BY seq', (inv,))]
def show(inv):
    for row in rows_of(inv): print('   seq %2d %-12s %-12s auth=%-14s | %s | %s' % (row['seq'], row['kind'], row['outcome'], row['authority'][:14], row['purpose'][:70], short(row['summary'], 150)))
def row_of(a): return short({kk: a[kk] for kk in ('profile', 'state', 'reason', 'steps_used')}, 500)

# ---- (a) replay ------------------------------------------------------------------------------------------------------------------
for name, text in (('notes/rail limits rev B.md', '6 W continuous.'), ('notes/rail bench plan.md', 'Repeat the pulse capture.')): d('files.write', {'path': name, 'text': text})
a = d('agent.assign', {'request': 'find files about rail'})['result']['assignment']; a = d('agent.run', {'id': a['id']})['result']['assignment']; print('[a] first run:', row_of(a))
steps = []
for row in rows_of(a['investigation']):
    if row['kind'] != 'STEP': continue
    prog = json.loads(row['program']); steps.append({'key': 's%d' % row['seq'], 'purpose': row['purpose'], 'operation': prog['operation'], 'arguments': prog['arguments']})
print('    its recorded steps as a list of %d {operation, arguments}:' % len(steps), [s['operation'] for s in steps])
b = d('agent.assign', {'request': 'run the steps of “find files about rail” again', 'profile': 'operation_sequence', 'context': {'steps': steps}})['result']['assignment']
b = d('agent.run', {'id': b['id']})['result']['assignment']; print('    replayed as operation_sequence:', row_of(b)); show(b['investigation'])
reads = [s for s in steps if agent_loop.SCOPES.get(s['operation']) == 'read' or __import__('workbench.engineering_kernel', fromlist=['CAPABILITIES']).CAPABILITIES.get(s['operation']) == 'read']
c = d('agent.assign', {'request': 'run only its reads again', 'profile': 'operation_sequence', 'context': {'steps': reads}, 'budget': {'effects': 'read'}})['result']['assignment']
c = d('agent.run', {'id': c['id']})['result']['assignment']; print('    only its %d reads, read-only budget:' % len(reads), row_of(c))
dup = [(r['seq'], bool(r['duplicate_of'])) for r in rows_of(c['investigation'])]; print('    duplicates marked inside one investigation only:', dup)

# ---- (b) a changed source ----------------------------------------------------------------------------------------------------------
doc = d('documents.create', {'title': 'Bench note', 'text': 'Settled draw 3.36 W.\nLimit 6 W.'})['result']['id']
inv = d('investigation.create', {'question': 'Is the settled draw inside the limit?'})['result']['id']
r = d('investigation.add_source', {'id': inv, 'address': 'document:' + doc}); print('\n[b] add_source ->', r['ok'], short(r['result'] if r['ok'] else r['error'], 200)); src = r['result']['source']
claim = d('investigation.claim', {'id': inv, 'text': 'The settled draw of 3.36 W is inside the 6 W limit.', 'role': 'FINDING'})['result']['claim']
r = d('investigation.evidence', {'claim': claim, 'direction': 'SUPPORTS', 'source': src, 'note': 'the bench note'}); print('    evidence ->', r['ok'], short(r['result']['evidence_state'] if r['ok'] else r['error']))
r = d('investigation.check', {'claim': claim, 'program': '@document:%s' % doc, 'oracle': 'The bench note still says 3.36 W', 'expect': 'CONTAINS', 'value': '3.36 W', 'refutes_on_fail': True}); print('    check ->', r['ok'], short(r['result'] if r['ok'] else r['error'], 200))
s = d('investigation.continue', {'id': inv})['result']; print('    continue -> %s | ran %s | authority %s' % (s['state'], s['ran'], s['authority']))
full = d('documents.get', {'id': doc})['result']['document']
d('documents.edit', {'id': doc, 'expected_revision': full['revision'], 'selection': {'block': 0, 'start': 0, 'end': len(full['blocks'][0]['text'])}, 'change': {'replace': 'Settled draw 6.40 W.'}})
print('    the owner changes the note to 6.40 W; nothing else is touched. investigation.sheet next:', d('investigation.sheet', {'id': inv})['result']['next'])
print('    prototype installed:', proto_profiles.install())
e = d('agent.assign', {'request': 'check the finding about the settled draw again'})['result']['assignment']; w.agent_driver.start(e['id']); t = time.time()
while w.agent_driver.running() and time.time() - t < 6: settle(60, 3)
e = d('agent.status', {'id': e['id']})['result']['assignments'][0]; print('    typed "check the finding about the settled draw again":', row_of(e)); show(e['investigation'])
print('    needs_you:', short(e['needs_you'], 600))
s = d('investigation.sheet', {'id': inv})['result']; print('    the finding\'s own investigation now: %s | next %s | claims %s' % (s['state'], s['next'], [(c['evidence_state'], c['review']) for c in s['unresolved'] + s['learned']]))
r = d('investigation.review', {'claim': claim, 'decision': 'ACCEPT_CHANGE'}); print('    the owner decides (investigation.review ACCEPT_CHANGE, approve) ->', r['ok'], short(r['result']['evidence_state'] if r['ok'] else r['error']))
w.agent_driver.resume(e['id']); t = time.time()
while w.agent_driver.running() and time.time() - t < 6: settle(60, 3)
e = d('agent.status', {'id': e['id']})['result']['assignments'][0]; print('    after Resume:', row_of(e)); show(e['investigation'])
s = d('investigation.continue', {'id': inv})['result']; print('    investigation.continue on the finding\'s investigation -> %s | ran %s | claims %s' % (s['state'], s['ran'], [(c['text'][:40], c['evidence_state']) for c in s['unresolved'] + s['learned']]))
