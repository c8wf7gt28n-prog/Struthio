# probe6 (2B model READY): where the loop consults the model, what it is asked, what it does; then a goal no profile handles.
import json, sqlite3, time, re, sys
sys.path.insert(0, '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/doer/loop')
import proto_profiles
from PySide6.QtWidgets import QLabel
from workbench import agent_loop, agent_qt
k = w.ledger_bridge.kernel; p = operator()
def d(op, args=None, principal=None): return k.dispatch(op, args or {}, principal or p)
def short(x, n=300):
    s = x if isinstance(x, str) else json.dumps(x, ensure_ascii=False, default=str)
    s = s.replace('​', '')
    return s if len(s) <= n else s[:n] + '…'
face = w.shell2.face
def bubbles(): return [face.lines.itemAt(i).widget() for i in range(face.lines.count()) if face.lines.itemAt(i).widget() is not None]
def choices_of(inv):
    with k.db() as db:
        db.row_factory = sqlite3.Row
        for row in db.execute('SELECT * FROM inv_steps WHERE investigation=? ORDER BY seq', (inv,)):
            row = dict(row)
            if row['kind'] in ('CHOICE', 'MODEL_CHOICE'):
                prog = json.loads(row['program'])
                print('   seq %2d %-12s %-7s %.1f s | %s' % (row['seq'], row['kind'], row['outcome'], row['finished'] - row['started'], row['summary']))
                if row['kind'] == 'MODEL_CHOICE':
                    print('        the model was sent (brain.ask mode choice, choices %s):' % prog['arguments'].get('choices'))
                    for line in str(prog['arguments'].get('message')).split('\n'): print('          >', line)
                    print('        options as the profile marked them:', short(prog['arguments'].get('options'), 500))
            else: print('   seq %2d %-12s %-7s | %s | %s' % (row['seq'], row['kind'], row['outcome'], row['purpose'], short(json.loads(row['program']).get('operation'), 60)))
def drive(ident, seconds=240):
    """As the window does: the driver ticks agent.step every 250 ms; a pending model choice keeps it RUNNING until answered."""
    w.agent_driver.start(ident); t = time.time(); said = set()
    while w.agent_driver.running() and time.time() - t < seconds:
        settle(100, 3); row = d('agent.status', {'id': ident})['result']['assignments'][0]
        if row['doing_now'] not in said: said.add(row['doing_now']); print('      %.1f s doing_now: %s' % (time.time() - t, short(row['doing_now'], 160)))
    row = d('agent.status', {'id': ident})['result']['assignments'][0]
    print('   -> %s in %.1f s | model_used %s | steps_used %s | %s' % (row['state'], time.time() - t, row['model_used'], row['steps_used'], short(row['reason'], 300)))
    return row
print('brain:', call('brain.status')['state'], '| profiles added at run time:', proto_profiles.install())

# ---- 1. files_about (an EXISTING profile): write the page, or read one more? ---------------------------------------------------
for name, text in (('notes/rail limits rev B.md', '# Rail limits Rev B\n6 W continuous. 8 W for up to 80 ms.'), ('notes/rail bench plan.md', 'Repeat the pulse capture at the load on the 12 V rail.'),
                   ('notes/startup pulse.txt', 'The startup pulse on the rail ran 110 ms.'), ('notes/rail ordering.md', 'Order two more rail connectors.')): d('files.write', {'path': name, 'text': text})
a = d('agent.assign', {'request': 'find files about rail'})['result']['assignment']; print('\n[1] files_about with a model READY')
r = d('agent.run', {'id': a['id']}); print('   agent.run returned after %d steps with state %s: %s' % (len(r['result']['ran']), r['result']['assignment']['state'], short(r['result']['assignment']['doing_now'], 120)))
a = drive(a['id']); choices_of(a['investigation'])

# ---- 2. the prototype "check a finding again": two acceptable options -----------------------------------------------------------
b = d('agent.assign', {'request': 'check the finding about the startup pulse again'})['result']['assignment']; print('\n[2] finding_again (prototype) with a model READY:', b['profile'], b['state'])
b = drive(b['id']); choices_of(b['investigation'])
for c in b['found']: print('   found:', short(c['text'], 400))

# ---- 3. a goal NO profile handles, with the model loaded ------------------------------------------------------------------------
r = d('agent.assign', {'request': 'bring the settled power calculation up to date'}); c = r['result']['assignment']
print('\n[3] agent.assign (auto) on an unhandled goal with a model READY ->', c['state'], '|', c['reason'])
w.shell2.show_slate_face(); settle()
def ask(text, seconds=300):
    n = len(bubbles()); t = time.time(); w.shell2.ask(text); settle(50, 3); job = face.job
    while face.job and time.time() - t < seconds: settle(150, 3)
    settle(150, 4); print('\nOWNER TYPES: %r  (%.1f s%s)' % (text, time.time() - t, ', STILL RUNNING' if face.job else ''))
    for card in bubbles()[n + 1:]:
        for l in card.findChildren(QLabel): print('   STACY |', short(re.sub(r'<[^>]+>', '', l.text()), 900))
    if job:
        j = call('jobs.get', {'id': job}); spec = (j.get('request_spec') or {}).get('brain') or {}
        print('   the job: tool %s state %s | mode %s | message sent: %s' % (j.get('tool'), j.get('state'), spec.get('mode'), short(spec.get('message'), 500)))
        res = (d('brain.result', {'id': job}).get('result') or {}).get('result') or {}
        print('   result keys:', sorted(res)); print('   proposal:', short(res.get('proposal'), 1500)); print('   action_plans:', short(res.get('action_plans'), 900))
        print('   metrics:', short(res.get('metrics') or res.get('usage'), 500))
    return job
before = len(d('agent.list')['result']['assignments'])
ask('bring the settled power calculation up to date')
ask('check the finding about the settled draw against the Rev B limit and write the result on the conclusion page')
print('\n   assignments created by those two typed requests:', len(d('agent.list')['result']['assignments']) - before)
save('doer_loop_model.png')
