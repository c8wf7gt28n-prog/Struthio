# probe2: drive assignments THROUGH THE WINDOW (the same functions the owner's Enter uses), no model.
import json, sqlite3, time
from PySide6.QtWidgets import QLabel
from workbench import agent_loop, agent_qt
from workbench.shell2 import open_destination
k = w.ledger_bridge.kernel; p = operator()
def d(op, args=None, principal=None): return k.dispatch(op, args or {}, principal or p)
def short(x, n=300):
    s = x if isinstance(x, str) else json.dumps(x, ensure_ascii=False, default=str)
    s = s.replace('​', '')
    return s if len(s) <= n else s[:n] + '…'
face = w.shell2.face
def bubbles(): return [face.lines.itemAt(i).widget() for i in range(face.lines.count()) if face.lines.itemAt(i).widget() is not None]
def said(card): return [l.text().replace('​', '') for l in card.findChildren(QLabel)]
def ask(text, wait=4.0):
    n = len(bubbles()); w.shell2.ask(text); t = time.time()
    while time.time() - t < wait and (w.agent_driver.running() or time.time() - t < 0.6): settle(60, 3)
    print('\nOWNER TYPES: %r' % text)
    for card in bubbles()[n + 1:]:
        for line in said(card): print('   STACY |', short(line, 600))
def work_block():
    blocks = w.findChildren(agent_qt.WorkBlock)
    for b in blocks[:1]:
        b.refresh()
        print('   WORK BLOCK visible=%s' % b.isVisible())
        for key, name in b.KEYS:
            import re
            print('      %-11s %s' % (name, short(re.sub(r'<[^>]+>', '', b.lines[key].text()), 500)))
def steps_of(inv):
    with k.db() as db:
        db.row_factory = sqlite3.Row
        for row in db.execute('SELECT * FROM inv_steps WHERE investigation=? ORDER BY seq', (inv,)):
            row = dict(row)
            print('   seq %2d %-12s %-7s auth=%-12s | %s' % (row['seq'], row['kind'], row['outcome'], row['authority'], row['purpose']))
            print('          program: %s' % short(row['program'], 330))
            print('          inputs : %s | summary: %s' % (short(row['inputs'], 170), short(row['summary'], 200)))
def claims_of(inv):
    with k.db() as db:
        db.row_factory = sqlite3.Row
        for row in db.execute('SELECT role, text FROM inv_claims WHERE investigation=? ORDER BY created', (inv,)): print('   claim %-8s %s' % (row['role'], short(row['text'], 300)))
def last_assignment(): return d('agent.status')['result']['assignments'][0]

print('driver installed:', type(w.agent_driver).__name__, '| tick ms', agent_qt.TICK_MS, '| hosted (service client):', agent_qt.hosted(w), '| close would:', w.agent_driver.close_words())

# ---- A. numbers on a page, typed in the window ---------------------------------------------------------------------------
r = d('documents.create', {'title': '07 Power figures to add', 'text': 'Settled draw 3.36 W.\nStartup draw 7.8 W.\nStandby draw 240 mW.'})
print('\n[A] documents.create:', r['ok'], short(r['result'] if r['ok'] else r['error'], 200)); doc = r['result']['document']['id'] if 'document' in r['result'] else r['result']['id']
tab = open_destination(w, 'documents:' + doc); settle(80, 4); print('    open tab:', type(w.tabs.currentWidget()).__name__, getattr(w.tabs.currentWidget(), 'document_id', None) == doc)
w.shell2.show_slate_face(); settle()
ask('add up the numbers on this page')
a = last_assignment(); print('   assignment:', short({kk: a[kk] for kk in ('profile', 'state', 'reason', 'doing_now', 'steps_used', 'model_used', 'driver')}, 500))
print('   found:', short(a['found'], 400)); print('   inspect:', short(a['inspect'], 400))
work_block(); steps_of(a['investigation']); claims_of(a['investigation'])
full = d('documents.get', {'id': doc})['result']['document']; print('   page revision now', full['revision'])
for b in full['blocks']: print('      block %s | %s' % (b['id'][:8], short(b['text'], 300)))
cards = d('conditions.list', {'document': doc})['result']['conditions']; print('   condition cards:', short(cards, 900))
if cards:
    c = d('conditions.get', {'id': cards[0]['id']})['result']; print('   conditions.get:', short(c, 1400))
sheet = d('investigation.sheet', {'id': a['investigation']})['result']; print('   investigation: state %s | reason %s | next %s' % (sheet['state'], sheet['reason'], sheet['next']))
print('   learned %d | unresolved %s' % (len(sheet['learned']), [(c['role'], c['evidence_state']) for c in sheet['unresolved']]))
save('doer_loop_A_numbers_done.png')

# stale: change one number through documents.edit as the owner would
blk = full['blocks'][0]
r = d('documents.edit', {'id': doc, 'expected_revision': full['revision'], 'selection': {'block': 0, 'start': 0, 'end': len(blk['text'])}, 'change': {'replace': 'Settled draw 3.50 W.'}})
print('\n[A2] owner edit of a bound number:', r['ok'], short(r['result'].get('applied') if r['ok'] else r['error'], 300))
cards = d('conditions.list', {'document': doc})['result']['conditions']; print('   cards now:', [(c['id'][:8], c['state'], c.get('reason')) for c in cards]); work_block()
if cards:
    r = d('conditions.recheck', {'id': cards[0]['id']}); print('   conditions.recheck:', r['ok'], short(r['result'].get('words') if r['ok'] else r['error'], 300))
    full = d('documents.get', {'id': doc})['result']['document']; print('   last block now:', short(full['blocks'][-1]['text'], 300), '| card:', [(c['state']) for c in d('conditions.list', {'document': doc})['result']['conditions']])

# ---- B. files about a word, typed with the page still open -----------------------------------------------------------------
ask('find files about rail', wait=12)
b = last_assignment(); print('   assignment:', short({kk: b[kk] for kk in ('profile', 'state', 'reason', 'doing_now', 'steps_used', 'model_used')}, 600))
work_block(); steps_of(b['investigation']); claims_of(b['investigation'])
for item in b['inspect']:
    if item['kind'] == 'document':
        page = d('documents.get', {'id': item['id']})['result']['document']; print('   findings page %r rev %d' % (page['title'], page['revision']))
        for blk in page['blocks']: print('      |', short(blk['text'], 260))
save('doer_loop_B_files_done.png')

# ---- C. a goal no profile handles, typed in the window, page open and Field in front ---------------------------------------
before = len(d('agent.list')['result']['assignments'])
ask('bring this calculation up to date')
ask('check the finding about the startup pulse again and tell me if it still holds')
print('   assignments created by those two requests:', len(d('agent.list')['result']['assignments']) - before)
w.a_field.trigger(); settle(); v = w.field_page.view
calc = next(o for o in v.field.objects if o.kind == 'calculation'); v.field.select(calc.id); v.update(); settle(5, 2)
print('\n   Field in front, selected:', calc.kind, calc.title, '|', calc.stac)
ask('bring this calculation up to date')
finding = next(o for o in v.field.objects if o.kind == 'finding'); v.field.select(finding.id); v.update(); settle(5, 2)
print('\n   Field in front, selected:', finding.kind, finding.title, '|', finding.stac)
ask('check this finding again')
print('   assignments created in the Field:', len(d('agent.list')['result']['assignments']) - before)
save('doer_loop_C_unhandled.png')

# the same goal straight to the Kernel
r = d('agent.assign', {'request': 'bring the settled power calculation up to date'})
c = r['result']['assignment']; print('\n[C2] agent.assign with no profile:', short({kk: c[kk] for kk in ('profile', 'state', 'reason', 'doing_now', 'needs_you', 'inspect')}, 700))
print('   sheet.objective:', r['result']['sheet']['objective'])
r = d('agent.step', {'id': c['id']}); print('   agent.step ->', short(r['result']['next'] if r['ok'] else r['error'], 300))
r = d('agent.resume', {'id': c['id']}); print('   agent.resume ->', r['ok'], short(r['result']['assignment']['state'] if r['ok'] else r['error']))
r = d('agent.step', {'id': c['id']}); print('   agent.step ->', short({'state': r['result']['assignment']['state'], 'next': r['result']['next']} if r['ok'] else r['error'], 300))
r = d('agent.run', {'id': c['id']}); print('   agent.run ->', short({'state': r['result']['assignment']['state'], 'ran': r['result']['ran'], 'reason': r['result']['assignment']['reason']} if r['ok'] else r['error'], 400))
work_block()
print('\n   Today rows:'); [print('      ', short(row[0], 200), '|', row[1]) for row in agent_qt.today_rows(w)]
print('\n   agent.list:'); [print('      ', short({kk: row[kk] for kk in ('profile', 'state', 'working_on', 'steps_used', 'reason')}, 300)) for row in d('agent.list')['result']['assignments']]
