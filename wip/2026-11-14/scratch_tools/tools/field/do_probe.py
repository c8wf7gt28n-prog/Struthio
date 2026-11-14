# the doer in the real window: make a calculation stale, ask what can be done (D), take a read, take the write (Run), check the desk (C)
import copy
from PySide6.QtWidgets import QLabel, QPushButton
k = w.ledger_bridge.kernel; p = operator(); face = w.shell2.face
def call(op, args=None):
    r = k.dispatch(op, args or {}, p)
    if not r['ok']: raise RuntimeError('%s refused: %s' % (op, r['error']))
    return r['result']
def cards(): return [face.lines.itemAt(i).widget() for i in range(face.lines.count()) if face.lines.itemAt(i).widget() is not None]
def said(card, n=6): return [l.text().replace('​', '')[:230].replace('\n', ' / ') for l in card.findChildren(QLabel)][:n]
w.a_field.trigger(); settle(); v = w.field_page.view; page = w.field_page
calc = next(o for o in v.field.objects if o.kind == 'calculation' and 'Settled' in o.title)
der = call('documents.get', {'id': calc.target['id']})['document']['derivation']
sheet = call('office.get', {'id': der['sheet']}); d = copy.deepcopy(sheet['document']); d['sheets'][0]['cells']['B3']['value'] = '300'
call('office.save', {'id': der['sheet'], 'expected_revision': sheet['revision'], 'document': d})
QTest.keyClick(v, Qt.Key_R); settle(30, 3)
print('after the cell changed:', [(o.title, o.state) for o in v.field.objects if o.kind == 'calculation'])
# C: check the desk
QTest.keyClick(v, Qt.Key_C); settle(60, 4); card = cards()[-1]
print('C -> Talk in front:', w.console_pages.currentWidget() is face, '| keyboard in:', type(app.focusWidget()).__name__, '| waiting:', [(o.title, why) for o, why, _ in getattr(card, 'waiting', [])])
for line in said(card, 7): print('   |', line)
save('Graphite_Do_01_Check_The_Desk_%s.png' % tag)
# D on the stale calculation
v.field.select(calc.id); v._describe(); v.update(); settle(5, 2)
QTest.keyClick(v, Qt.Key_D); settle(60, 4)
print('D -> steps in the Field:', v.steps)
for step in page.steps: print('   %-5s %-8s %s' % (step.kind, step.scope, step.line[:150]))
save('Graphite_Do_02_What_Can_Be_Done_%s.png' % tag)
QTest.keyClick(v, Qt.Key_2); settle(80, 4); card = cards()[-1]; print('2 (a read) ->', said(card, 3))
n = next(i for i, s in enumerate(page.steps) if s.kind == 'write' and 'recheck' in s.line)
QTest.keyClick(v, Qt.Key_1 + n); settle(60, 4); card = cards()[-1]
print('%d (a change) -> staged, not run: ran=%r | Field still shows: %s' % (n + 1, card.ran, [(o.title, o.state) for o in v.field.objects if o.kind == 'calculation']))
for line in said(card, 4): print('   |', line)
save('Graphite_Do_03_Waits_For_You_%s.png' % tag)
card.findChild(QPushButton, 'StagedRun').click(); settle(120, 5)
print('Run -> ran=%r | %s' % (card.ran, said(card, 6)[-1]))
print('the Field now:', [(o.title, o.state) for o in v.field.objects if o.kind == 'calculation'], '| selected:', v.selected().title, '| aside:', v.field.aside, '| keyboard in:', type(app.focusWidget()).__name__)
card.findChild(QPushButton, 'StagedRun').click(); settle(30, 2); print('a second click does nothing: still', card.ran, '| button:', card.findChild(QPushButton, 'StagedRun').text(), card.findChild(QPushButton, 'StagedRun').isEnabled())
save('Graphite_Do_04_Done_%s.png' % tag)
# D on the other kinds: only that it offers steps and that every read step runs
for kind in ('sheet', 'finding', 'question', 'source', 'document', 'calculation'):
    obj = next(o for o in v.field.objects if o.kind == kind); v.field.select(obj.id); v._describe(); v.update(); settle(5, 2)
    QTest.keyClick(v, Qt.Key_D); settle(40, 3)
    ran = []
    for i, step in enumerate(page.steps):
        if step.kind != 'read': ran.append('%d:waits' % (i + 1)); continue
        QTest.keyClick(v, Qt.Key_1 + i); settle(60, 3); c = cards()[-1]; ran.append('%d:%s' % (i + 1, 'ok' if getattr(c, 'answered', False) else 'REFUSED ' + said(c, 3)[-1][:120]))
    print('%-11s %-34s %d steps: %s' % (kind, obj.title[:34], len(page.steps), ' '.join(ran)))
    for step in page.steps: print('      %-5s %s' % (step.kind, step.words))
QTest.keyClick(v, Qt.Key_Escape); settle(5, 2); print('Esc closes the steps:', v.steps == (), '| Field still in front:', w._field_active)
QTest.keyClick(v, Qt.Key_C); settle(60, 4); card = cards()[-1]; print('C again:', said(card, 2)[0])
