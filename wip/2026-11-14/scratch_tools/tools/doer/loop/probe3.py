# probe3 (no model): the choice step, a given sequence of operations (staC lines included), reads-only budgets, pause/resume/stop,
# budgets, the investigation's checks, the network profile's "write waits for the owner", and the kill switch's agent side.
import json, sqlite3, time, re
from workbench import agent_loop, agent_qt
k = w.ledger_bridge.kernel; p = operator()
def d(op, args=None, principal=None): return k.dispatch(op, args or {}, principal or p)
def short(x, n=300):
    s = x if isinstance(x, str) else json.dumps(x, ensure_ascii=False, default=str)
    s = s.replace('​', '')
    return s if len(s) <= n else s[:n] + '…'
def steps_of(inv, wide=260):
    with k.db() as db:
        db.row_factory = sqlite3.Row
        for row in db.execute('SELECT * FROM inv_steps WHERE investigation=? ORDER BY seq', (inv,)):
            row = dict(row)
            print('   seq %2d %-12s %-12s auth=%-12s | %s' % (row['seq'], row['kind'], row['outcome'], row['authority'], row['purpose']))
            print('          program: %s' % short(row['program'], wide)); print('          summary: %s' % short(row['summary'], 240))
def claims_of(inv):
    with k.db() as db:
        db.row_factory = sqlite3.Row
        for row in db.execute('SELECT role, text FROM inv_claims WHERE investigation=? ORDER BY created', (inv,)): print('   claim %-8s %s' % (row['role'], short(row['text'], 260)))
def row_of(a): return short({kk: a[kk] for kk in ('profile', 'state', 'reason', 'doing_now', 'steps_used', 'model_used')}, 600)

# ---- 1. files_about with real matches: where the CHOICE happens ---------------------------------------------------------------
for name, text in (('notes/rail limits rev B.md', '# Rail limits Rev B\n6 W continuous. 8 W for up to 80 ms.'), ('notes/rail bench plan.md', 'Repeat the pulse capture at the load on the 12 V rail.'),
                   ('notes/startup pulse.txt', 'The startup pulse on the rail ran 110 ms.'), ('notes/rail ordering.md', 'Order two more rail connectors.'), ('notes/unrelated.md', 'Buy coffee.')):
    r = d('files.write', {'path': name, 'text': text}); print('files.write', name, r['ok'], '' if r['ok'] else r['error'])
r = d('agent.assign', {'request': 'find files about rail'}); a = r['result']['assignment']; print('\n[1] assigned:', row_of(a))
r = d('agent.run', {'id': a['id']}); a = r['result']['assignment']; print('    agent.run ran %d steps ->' % len(r['result']['ran']), row_of(a))
steps_of(a['investigation']); claims_of(a['investigation'])
for item in a['inspect']:
    if item['kind'] == 'document':
        page = d('documents.get', {'id': item['id']})['result']['document']; print('   findings page %r rev %d' % (page['title'], page['revision']))
        for blk in page['blocks']: print('      |', short(blk['text'], 230))

# ---- 2. operation_sequence: ANY registered operations as an assignment, a staC line among them ----------------------------------
docs = d('documents.list')['result']['documents']; calc = next(x for x in docs if 'Settled' in x['title'])
stac = 'documents.get {"id":"%s"} | pick document.derivation.inputs | select symbol,parameter,cell,conditions' % calc['id']
steps = [{'key': 'inputs', 'purpose': 'Read what the calculation takes in (a staC line)', 'operation': 'language.run', 'arguments': {'text': stac}},
         {'key': 'cards', 'purpose': 'List the condition cards', 'operation': 'conditions.list', 'arguments': {}},
         {'key': 'note', 'purpose': 'Write a note file (a write)', 'operation': 'files.write', 'arguments': {'path': 'notes/from the loop.md', 'text': 'written by an assignment step'}},
         {'key': 'after', 'purpose': 'Read it back', 'operation': 'files.get', 'arguments': {'path': 'notes/from the loop.md'}}]
r = d('agent.assign', {'request': 'read the calculation, then leave a note', 'profile': 'operation_sequence', 'context': {'steps': steps}, 'budget': {'effects': 'read'}})
b = r['result']['assignment']; print('\n[2] operation_sequence with budget.effects=read:', row_of(b))
r = d('agent.run', {'id': b['id']}); b = r['result']['assignment']; print('    after agent.run:', row_of(b)); print('    needs_you:', short(b['needs_you'], 500))
steps_of(b['investigation'], 380); claims_of(b['investigation'])
r = d('agent.resume', {'id': b['id']}); print('    agent.resume ->', r['result']['assignment']['state'] if r['ok'] else r['error'])
r = d('agent.run', {'id': b['id']}); b = r['result']['assignment']; print('    agent.run again (same read-only budget):', row_of(b))
# the same steps with the default budget (execute)
r = d('agent.assign', {'request': 'read the calculation, then leave a note (may write)', 'profile': 'operation_sequence', 'context': {'steps': steps}})
c = r['result']['assignment']; r = d('agent.run', {'id': c['id']}); c = r['result']['assignment']; print('    same steps, default budget:', row_of(c)); steps_of(c['investigation'], 200)
# a step that needs approve (never granted to a step)
r = d('agent.assign', {'request': 'try an approve-scoped operation', 'profile': 'operation_sequence', 'context': {'steps': [{'operation': 'work.list', 'arguments': {}}, {'operation': 'investigation.review', 'arguments': {'claim': '0' * 32, 'decision': 'RETIRE'}}]}})
e = r['result']['assignment']; r = d('agent.run', {'id': e['id']}); e = r['result']['assignment']; print('    approve-scoped step:', row_of(e))
# an unknown operation and a malformed plan
r = d('agent.assign', {'request': 'unknown op', 'profile': 'operation_sequence', 'context': {'steps': [{'operation': 'no.such.operation', 'arguments': {}}]}})
f = r['result']['assignment']; r = d('agent.run', {'id': f['id']}); print('    unknown operation:', row_of(r['result']['assignment']))
r = d('agent.assign', {'request': 'no steps', 'profile': 'operation_sequence'}); print('    operation_sequence without context.steps:', row_of(r['result']['assignment']))

# ---- 3. pause / resume / stop / budget -------------------------------------------------------------------------------------------
many = [{'key': 'r%d' % n, 'purpose': 'Read the page (%d)' % n, 'operation': 'documents.get', 'arguments': {'id': calc['id']}} for n in range(1, 7)]
r = d('agent.assign', {'request': 'read the page six times', 'profile': 'operation_sequence', 'context': {'steps': many}, 'budget': {'max_steps': 4}}); g = r['result']['assignment']
print('\n[3] six reads, budget max_steps 4'); r = d('agent.step', {'id': g['id']}); print('    step 1 ->', r['result']['assignment']['state'], '|', r['result']['next'])
r = d('agent.pause', {'id': g['id'], 'reason': 'lunch'}); print('    agent.pause ->', row_of(r['result']['assignment']))
r = d('agent.step', {'id': g['id']}); print('    agent.step while PAUSED ->', r['result']['next'])
r = d('agent.resume', {'id': g['id']}); print('    agent.resume ->', r['result']['assignment']['state'])
r = d('agent.run', {'id': g['id']}); g = r['result']['assignment']; print('    agent.run ->', row_of(g)); steps_of(g['investigation'], 120)
inv = d('investigation.sheet', {'id': g['investigation']})['result']; print('    its investigation:', inv['state'], '|', inv['reason'])
r = d('agent.resume', {'id': g['id']}); print('    agent.resume on STOPPED ->', r['ok'], '' if r['ok'] else r['error']['message'])
r = d('agent.assign', {'request': 'read the page six times (stop me)', 'profile': 'operation_sequence', 'context': {'steps': many}}); h = r['result']['assignment']
d('agent.step', {'id': h['id']}); r = d('agent.stop', {'id': h['id'], 'reason': 'enough'}); print('    agent.stop ->', row_of(r['result']['assignment']))
r = d('agent.stop', {'id': h['id']}); print('    agent.stop again ->', r['ok'], '' if r['ok'] else r['error']['message'])
r = d('agent.assign', {'request': 'x', 'budget': {'max_steps': 500}}); print('    budget max_steps 500 ->', r['ok'], '' if r['ok'] else r['error']['message'])
# another identity cannot see or step it
from workbench.engineering_kernel import Principal
other = Principal('someone-else', frozenset({'read', 'execute'}))
r = d('agent.step', {'id': g['id']}, other); print('    another identity agent.step ->', r['ok'], '' if r['ok'] else r['error']['message'])
r = d('agent.assign', {'request': 'add up the numbers on this page', 'context': {'document': calc['id']}}, Principal('reader', frozenset({'read'}))); print('    read-only principal agent.assign ->', r['ok'], '' if r['ok'] else r['error']['message'])

# ---- 4. the investigation under an assignment: bind a check to its finding, run it, see CRITERIA_SATISFIED ------------------------
r = d('documents.create', {'title': 'Power to add', 'text': 'Settled draw 3.36 W.\nStartup draw 7.8 W.'}); doc = r['result']['id']
r = d('agent.assign', {'request': 'add up the numbers on this page', 'context': {'document': doc}}); j = r['result']['assignment']; r = d('agent.run', {'id': j['id']}); j = r['result']['assignment']
print('\n[4] numbers assignment:', row_of(j)); claim = j['found'][0]['id']; card = next(i['id'] for i in j['inspect'] if i['kind'] == 'condition')
sheet = d('investigation.sheet', {'id': j['investigation']})['result']; print('    investigation after DONE: %s | %s' % (sheet['state'], sheet['next']))
program = 'conditions.get {"id":"%s"} | pick condition | select state,result' % card
r = d('language.run', {'text': program}); print('    the check line alone:', r['ok'], short(r['result'].get('rows') if r['ok'] else r['error'], 300))
r = d('investigation.check', {'claim': claim, 'program': program, 'oracle': 'The card that binds the total to its numbers is CURRENT', 'expect': 'CONTAINS', 'value': '"state": "CURRENT"', 'refutes_on_fail': True})
print('    investigation.check ->', r['ok'], short(r['result'] if r['ok'] else r['error'], 300))
r = d('investigation.continue', {'id': j['investigation']}); s = r['result'] if r['ok'] else None
print('    investigation.continue ->', r['ok'], short({'state': s['state'], 'reason': s['reason'], 'ran': s['ran'], 'authority': s['authority'], 'learned': [(c['text'], c['evidence_state']) for c in s['learned']]} if s else r['error'], 700))
print('    agent.status found now:', short(d('agent.status', {'id': j['id']})['result']['assignments'][0]['found'], 300))
r = d('investigation.path', {'claim': claim}); print('    investigation.path:', short(r['result'] if r['ok'] else r['error'], 700))
# the owner changes a number: the card goes STALE; the check, run again, does not hold
full = d('documents.get', {'id': doc})['result']['document']
d('documents.edit', {'id': doc, 'expected_revision': full['revision'], 'selection': {'block': 0, 'start': 0, 'end': len(full['blocks'][0]['text'])}, 'change': {'replace': 'Settled draw 3.50 W.'}})
r = d('investigation.continue', {'id': j['investigation']}); s = r['result']; print('    after the owner changed a number, investigation.continue ->', short({'state': s['state'], 'reason': s['reason'], 'ran': s['ran']}, 400))
with k.db() as db:
    row = db.execute('SELECT id FROM inv_checks WHERE claim=?', (claim,)).fetchone()
print('    (continue runs a check only when its last outcome is NOT_RUN, FAILED or STALE; a PASSED check is not run again by itself)')
r = d('investigation.step', {'id': j['investigation'], 'program': program, 'purpose': 'Look at the card again'}); print('    investigation.step ->', short(r['result'] if r['ok'] else r['error'], 400))
steps_of(j['investigation'], 200)

# ---- 5. network_talk: a write that waits for the owner ---------------------------------------------------------------------------
r = d('agent.assign', {'request': 'capture the traffic on port 443'}); n = r['result']['assignment']; print('\n[5] assigned:', row_of(n))
r = d('agent.run', {'id': n['id']}); n = r['result']['assignment']; print('    after agent.run:', row_of(n)); print('    needs_you:', short(n['needs_you'], 700)); steps_of(n['investigation'], 200)
r = d('agent.resume', {'id': n['id']}); r = d('agent.run', {'id': n['id']}); n = r['result']['assignment']; print('    resume + run:', row_of(n)); steps_of(n['investigation'], 160)

# ---- 6. the kill switch's assignment side, and Today ------------------------------------------------------------------------------
r = d('agent.assign', {'request': 'read the page six times (for the stop)', 'profile': 'operation_sequence', 'context': {'steps': many}}); m = r['result']['assignment']
w.agent_driver.start(m['id']); settle(60, 2); print('\n[6] driver running:', w.agent_driver.running())
paused = w.agent_driver.pause_all('Master Stop'); print('    driver.pause_all("Master Stop") ->', paused, '| status:', row_of(d('agent.status', {'id': m['id']})['result']['assignments'][0]))
print('    Today rows:'); [print('       ', short(row[0], 200), '|', row[1]) for row in agent_qt.today_rows(w)]
r = agent_qt.resume_from_today(w, m['id']); t = time.time()
while w.agent_driver.running() and time.time() - t < 6: settle(60, 3)
print('    resume_from_today ->', r.get('ok'), '| status:', row_of(d('agent.status', {'id': m['id']})['result']['assignments'][0]))
blocks = w.findChildren(agent_qt.WorkBlock); print('    WorkBlocks in the window:', len(blocks), [(type(b.parentWidget()).__name__, b.isVisible()) for b in blocks])
print('    service-side pump with no setting stored:', agent_loop.continue_when_closed(k), '| pump returns', agent_loop.pump(k))
