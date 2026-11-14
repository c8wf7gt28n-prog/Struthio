# the whole doer from the keyboard only: C, 1 (settle), 1 (run all); then A to the finding that waits, D, a digit, 1 (run)
import copy
from PySide6.QtWidgets import QLabel
k = w.ledger_bridge.kernel; p = operator(); face = w.shell2.face
def call(op, args=None):
    r = k.dispatch(op, args or {}, p); assert r['ok'], r; return r['result']
def cards(): return [face.lines.itemAt(i).widget() for i in range(face.lines.count()) if face.lines.itemAt(i).widget() is not None]
def first(card): return card.findChildren(QLabel)[0].text().replace('​', '')[:150]
w.a_field.trigger(); settle(); v = w.field_page.view
calc = next(o for o in v.field.objects if o.kind == 'calculation')
der = call('documents.get', {'id': calc.target['id']})['document']['derivation']
sheet = call('office.get', {'id': der['sheet']}); d = copy.deepcopy(sheet['document']); d['sheets'][0]['cells']['B3']['value'] = '300'
call('office.save', {'id': der['sheet'], 'expected_revision': sheet['revision'], 'document': d})
keys = []
def press(key, name):
    QTest.keyClick(v, key); settle(120, 5); keys.append(name)
    print('%-3s -> steps shown: %-52s | Talk: %s' % (name, str([x[0] for x in v.steps])[:52], first(cards()[-1])[:110]))
press(Qt.Key_C, 'C'); press(Qt.Key_1, '1'); print('   go offered:', repr(v.go)); save('Graphite_Do_08_Keyboard_Settle_%s.png' % tag)
press(Qt.Key_1, '1'); print('   a digit is never the go: calculations still', [(o.title, o.state) for o in v.field.objects if o.kind == 'calculation'], '| go still offered:', repr(v.go))
press(Qt.Key_G, 'G')
print('   calculations:', [(o.title, o.state) for o in v.field.objects if o.kind == 'calculation'])
QTest.keyClick(v, Qt.Key_A); settle(10, 2); keys.append('A'); print('A   -> selected:', v.selected().title, '|', v.selected().state)
if v.selected().kind != 'finding': QTest.keyClick(v, Qt.Key_A); settle(10, 2); keys.append('A'); print('A   -> selected:', v.selected().title, '|', v.selected().state)
press(Qt.Key_D, 'D')
n = next(i for i, s in enumerate(w.field_page.steps) if s.words.startswith('Write it again'))
press(Qt.Key_1 + n, str(n + 1)); print('   go offered:', repr(v.go)); press(Qt.Key_G, 'G')
print('   findings:', [(o.title[:44], o.state) for o in v.field.objects if o.kind == 'finding' and 'Settled draw' in o.title])
print('keys pressed, nothing else:', ' '.join(keys), '| keyboard still in:', type(app.focusWidget()).__name__, '| Field in front:', w._field_active)
