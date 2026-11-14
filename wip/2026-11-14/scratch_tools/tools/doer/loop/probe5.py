# probe5 (no model): two NEW kinds of job, registered at run time (nothing in the tree is changed), typed in the window like any request.
import json, sqlite3, time, re, sys
sys.path.insert(0, '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/doer/loop')
import proto_profiles
from PySide6.QtWidgets import QLabel
from workbench import agent_loop, agent_qt, agent_profiles
from workbench.shell2 import open_destination
k = w.ledger_bridge.kernel; p = operator()
def d(op, args=None, principal=None): return k.dispatch(op, args or {}, principal or p)
def short(x, n=300):
    s = x if isinstance(x, str) else json.dumps(x, ensure_ascii=False, default=str)
    s = s.replace('​', '')
    return s if len(s) <= n else s[:n] + '…'
face = w.shell2.face
def bubbles(): return [face.lines.itemAt(i).widget() for i in range(face.lines.count()) if face.lines.itemAt(i).widget() is not None]
def ask(text, wait=6.0):
    n = len(bubbles()); w.shell2.ask(text); t = time.time()
    while time.time() - t < wait and (w.agent_driver.running() or time.time() - t < 0.6): settle(60, 3)
    print('\nOWNER TYPES: %r' % text)
    for card in bubbles()[n + 1:]:
        for l in card.findChildren(QLabel): print('   STACY |', short(l.text(), 500))
def work_block():
    b = w.findChildren(agent_qt.WorkBlock)[0]; b.refresh()
    for key, name in b.KEYS: print('      %-11s %s' % (name, short(re.sub(r'<[^>]+>', '', b.lines[key].text()), 600)))
def steps_of(inv, wide=230):
    with k.db() as db:
        db.row_factory = sqlite3.Row
        for row in db.execute('SELECT * FROM inv_steps WHERE investigation=? ORDER BY seq', (inv,)):
            row = dict(row)
            print('   seq %2d %-12s %-7s auth=%-28s | %s' % (row['seq'], row['kind'], row['outcome'], row['authority'], row['purpose']))
            print('          program: %s' % short(row['program'], wide)); print('          summary: %s' % short(row['summary'], 260))
def claims_of(inv):
    with k.db() as db:
        db.row_factory = sqlite3.Row
        for row in db.execute('SELECT role, text FROM inv_claims WHERE investigation=? ORDER BY created', (inv,)): print('   claim %-8s %s' % (row['role'], short(row['text'], 420)))
def latest(): return d('agent.status')['result']['assignments'][0]
def row_of(a): return short({kk: a[kk] for kk in ('profile', 'state', 'reason', 'steps_used', 'model_used')}, 700)

print('registered at run time:', proto_profiles.install(), '| agent.assign profile enum (fixed at import):', agent_loop.PROFILES)
r = d('agent.assign', {'request': 'x', 'profile': 'finding_again'}); print('naming it in agent.assign ->', r['ok'], '' if r['ok'] else r['error']['message'])
for text in ('check the finding about the startup pulse again', 'bring the total on this page up to date'): print('   request_profile(%r) -> %s' % (text, agent_loop.request_profile(text)))

# ---- A. "check the finding … again", typed with nothing open ------------------------------------------------------------------
w.shell2.show_slate_face(); settle()
ask('check the finding about the startup pulse again')
a = latest(); print('   assignment:', row_of(a)); work_block(); steps_of(a['investigation']); claims_of(a['investigation'])

# ---- B. "bring the total on this page up to date": a write that waits ---------------------------------------------------------
r = d('documents.create', {'title': 'Power to add', 'text': 'Settled draw 3.36 W.\nStartup draw 7.8 W.'}); doc = r['result']['id']
r = d('agent.assign', {'request': 'add up the numbers on this page', 'context': {'document': doc}}); d('agent.run', {'id': r['result']['assignment']['id']})
full = d('documents.get', {'id': doc})['result']['document']
d('documents.edit', {'id': doc, 'expected_revision': full['revision'], 'selection': {'block': 0, 'start': 0, 'end': len(full['blocks'][0]['text'])}, 'change': {'replace': 'Settled draw 3.50 W.'}})
print('\n[B] a page with a total, then the owner changed a number:', [(c['state'], c['result']['text']) for c in d('conditions.list', {'document': doc})['result']['conditions']])
# B1: reads only (the owner's rule): the recheck is refused, the assignment waits, the owner does it, Resume verifies
r = d('agent.assign', {'request': 'bring the total on this page up to date', 'context': {'document': doc}, 'budget': {'effects': 'read'}}); b = r['result']['assignment']
print('   assigned with budget.effects=read:', row_of(b)); w.agent_driver.start(b['id']); t = time.time()
while w.agent_driver.running() and time.time() - t < 5: settle(60, 3)
b = d('agent.status', {'id': b['id']})['result']['assignments'][0]; print('   after the driver:', row_of(b)); work_block(); steps_of(b['investigation'])
blk = w.findChildren(agent_qt.WorkBlock)[0]; print('   the Work block offers recheck words for:', blk.stale)
if blk.stale: r = agent_qt.recheck(w, blk.stale[0]['id']); print('   owner uses the recheck word ->', short(r.get('result', {}).get('words') if isinstance(r, dict) and r.get('ok') else r, 200))
r = w.agent_driver.resume(b['id']); t = time.time()
while w.agent_driver.running() and time.time() - t < 5: settle(60, 3)
b = d('agent.status', {'id': b['id']})['result']['assignments'][0]; print('   after Resume:', row_of(b)); work_block(); steps_of(b['investigation']); claims_of(b['investigation'])
# B2: the same typed in the window (default budget: execute): the write runs by itself
full = d('documents.get', {'id': doc})['result']['document']
d('documents.edit', {'id': doc, 'expected_revision': full['revision'], 'selection': {'block': 0, 'start': 0, 'end': len(full['blocks'][0]['text'])}, 'change': {'replace': 'Settled draw 3.60 W.'}})
open_destination(w, 'documents:' + doc); settle(80, 4)
ask('bring the total on this page up to date')
c = latest(); print('   assignment:', row_of(c)); steps_of(c['investigation']); claims_of(c['investigation'])
print('   last paragraph:', short(d('documents.get', {'id': doc})['result']['document']['blocks'][-1]['text'], 200))
save('doer_loop_proto.png')
