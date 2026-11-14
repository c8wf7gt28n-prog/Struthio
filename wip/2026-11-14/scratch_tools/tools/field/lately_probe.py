# what changed lately is marked; a program with its own window is offered from the shelf through its own operation
import copy, time
from PySide6.QtWidgets import QLabel, QPushButton
k = w.ledger_bridge.kernel; p = operator(); face = w.shell2.face
def call(op, args=None):
    r = k.dispatch(op, args or {}, p); assert r['ok'], r; return r['result']
def cards(): return [face.lines.itemAt(i).widget() for i in range(face.lines.count()) if face.lines.itemAt(i).widget() is not None]
def said(card, n=6): return [l.text().replace('​', '')[:220].replace('\n', ' / ') for l in card.findChildren(QLabel)][:n]
w.a_field.trigger(); settle(); v = w.field_page.view; now = time.time()
print('restored case: head says', v.field.census(), '| marked lately:', [o.title for o in v.field.objects if o.lately(now)])
calc = next(o for o in v.field.objects if o.kind == 'calculation')
der = call('documents.get', {'id': calc.target['id']})['document']['derivation']
sheet = call('office.get', {'id': der['sheet']}); d = copy.deepcopy(sheet['document']); d['sheets'][0]['cells']['B3']['value'] = '300'
call('office.save', {'id': der['sheet'], 'expected_revision': sheet['revision'], 'document': d})
for key in (Qt.Key_C, Qt.Key_1, Qt.Key_G): QTest.keyClick(v, key); settle(150, 5)
now = time.time(); print('after settling:  head says', v.field.census(), '| marked lately:', [o.title for o in v.field.objects if o.lately(now)])
save('Graphite_Do_09_Changed_Lately_%s.png' % tag)
# the shelf: a room of Graphite's own, then a program with a window of its own
QTest.keyClick(v, Qt.Key_P); settle(40, 3)
proj = next(o for o in v.field.objects if o.id == 'app:projects'); v.field.select(proj.id); v._describe(); v.update(); settle(5, 2)
QTest.keyClick(v, Qt.Key_F); settle(20, 2); print('F on Projects ->', w.statusBar().currentMessage())
import io, zipfile
from pathlib import Path
files = Path(k.root) / 'Files' / 'Models'; files.mkdir(parents=True, exist_ok=True); buf = io.BytesIO()
with zipfile.ZipFile(buf, 'w') as z:
    z.writestr('Document.xml', '<?xml version="1.0" encoding="utf-8"?><Document SchemaVersion="4" ProgramVersion="0.21R0" FileVersion="1"><Properties Count="1"><Property name="Label" type="App::PropertyString"><String value="Bracket"/></Property></Properties><Objects Count="0"/><ObjectData Count="0"/></Document>')
(files / 'bracket.FCStd').write_bytes(buf.getvalue()); print('a small model file put in Files/Models')
fc = next(o for o in v.field.objects if o.id == 'app:freecad'); v.field.select(fc.id); v._describe(); v.update(); settle(5, 2)
QTest.keyClick(v, Qt.Key_D); settle(60, 4)
for step in w.field_page.steps: print('      %-5s %-8s %-34s %s' % (step.kind, step.scope, step.words, step.line[:130]))
QTest.keyClick(v, Qt.Key_Escape); settle(5, 2)
QTest.keyClick(v, Qt.Key_F); settle(80, 4); card = cards()[-1]
print('F on FreeCAD -> put up:', said(card, 1)[0][:160])
print('   go offered:', repr(v.go)); QTest.keyClick(v, Qt.Key_G); settle(120, 5); print('G (the go) -> ran=%r | %s' % (getattr(card, 'ran', None), said(card, 8)[-1][:260]))
print('Field in front:', w._field_active, '| face:', v.face, '| keyboard in:', type(app.focusWidget()).__name__)
