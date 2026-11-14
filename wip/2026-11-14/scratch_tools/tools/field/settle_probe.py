# settle the desk: stale both calculations, C, "settle what I can", one Run, and the check afterwards is the answer
import copy
from PySide6.QtWidgets import QLabel, QPushButton
k = w.ledger_bridge.kernel; p = operator(); face = w.shell2.face
def call(op, args=None):
    r = k.dispatch(op, args or {}, p)
    if not r['ok']: raise RuntimeError('%s refused: %s' % (op, r['error']))
    return r['result']
def cards(): return [face.lines.itemAt(i).widget() for i in range(face.lines.count()) if face.lines.itemAt(i).widget() is not None]
def said(card, n=8): return [l.text().replace('​', '')[:200].replace('\n', ' / ') for l in card.findChildren(QLabel)][:n]
w.a_field.trigger(); settle(); v = w.field_page.view
calc = next(o for o in v.field.objects if o.kind == 'calculation')
der = call('documents.get', {'id': calc.target['id']})['document']['derivation']
sheet = call('office.get', {'id': der['sheet']}); d = copy.deepcopy(sheet['document']); d['sheets'][0]['cells']['B3']['value'] = '300'; d['sheets'][0]['cells']['B4']['value'] = '700'
call('office.save', {'id': der['sheet'], 'expected_revision': sheet['revision'], 'document': d})
QTest.keyClick(v, Qt.Key_C); settle(60, 4); desk = cards()[-1]
print('checked:', said(desk, 1)[0], '| plan:', [(o.title, s.words) for o, s in desk.plan])
desk.plan and face.say_plan  # the link in the card calls the page's settle(); find it and follow it
link = [l for l in desk.findChildren(QLabel) if 'href="settle"' in l.text()][0]; link.linkActivated.emit('settle'); settle(60, 4)
plan = cards()[-1]; print('put up:', said(plan, 1)[0]); save('Graphite_Do_05_Settle_The_Desk_%s.png' % tag)
plan.findChild(QPushButton, 'PlanRun').click(); settle(200, 6)
print('ran:', [(ok, (res.get('document') or {}).get('title') if isinstance(res, dict) else res) for _, ok, res in plan.results], '| button:', plan.findChild(QPushButton, 'PlanRun').text())
for line in said(plan, 6)[1:]: print('   |', line)
after = cards()[-1]; print('checked again by itself:', said(after, 1)[0], '| still waiting:', [(o.title, why) for o, why, _ in after.waiting])
print('the Field now:', [(o.title, o.state) for o in v.field.objects if o.kind == 'calculation'], '| aside:', v.field.aside, '| keyboard in:', type(app.focusWidget()).__name__)
save('Graphite_Do_06_Settled_%s.png' % tag)

# the consequence: a finding that still quotes the old result is noticed, and says what can be done
for o, why, steps in after.waiting: print('   waits: %-44s %s' % (o.title[:44], why))
f = next((o for o in v.field.objects if o.kind == 'finding' and '3.36' in o.title), None)
if f is not None:
    print('in the Field:', f.title, '|', f.state, '|', f.lines)
    v.field.select(f.id); v._describe(); v.update(); settle(5, 2); QTest.keyClick(v, Qt.Key_D); settle(60, 4)
    for step in w.field_page.steps: print('      %-5s %-8s %-30s %s' % (step.kind, step.scope, step.words, step.line[:140]))
    n = next(i for i, s2 in enumerate(w.field_page.steps) if s2.words.startswith('Write it again'))
    QTest.keyClick(v, Qt.Key_1 + n); settle(60, 4); card = cards()[-1]; card.findChild(QPushButton, 'StagedRun').click(); settle(120, 5)
    print('wrote it again:', card.ran, '|', said(card, 6)[-1], '| findings now:', [(o.title[:42], o.state) for o in v.field.objects if o.kind == 'finding' and ('3.36' in o.title or '3.6 W' in o.title)])
    save('Graphite_Do_07_Finding_Follows_%s.png' % tag)
