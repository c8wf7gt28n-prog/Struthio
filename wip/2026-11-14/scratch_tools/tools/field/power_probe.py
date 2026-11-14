# `this` in the writing strip, T to trace, "what if" in plain words
from PySide6.QtWidgets import QLabel
k = w.ledger_bridge.kernel; p = operator(); face = w.shell2.face; bar = w.type_bar; console = w.console
def cards(): return [face.lines.itemAt(i).widget() for i in range(face.lines.count()) if face.lines.itemAt(i).widget() is not None]
def said(card, n=4): return [l.text().replace('​', '')[:260].replace('\n', ' / ') for l in card.findChildren(QLabel)][:n]
def strip(text):
    bar.set_target('slate', focus=False); bar.box.setFocus(); bar.box.setText(text); settle(10, 2); bar.refresh_context(); settle(5, 2)
    hint = bar.context.text() if hasattr(bar, 'context') else ''
    console.last_program = None; QTest.keyClick(bar.box, Qt.Key_Return, Qt.ControlModifier); settle(80, 4)
    out = console.output.toPlainText().strip().splitlines()
    print('strip %-58r hint %-22r ran: %s' % (text, hint, (console.last_program or 'NOT RUN · ' + (bar.message or ''))[:150]))
    if console.last_program: print('      answer:', ' | '.join(l.strip() for l in out[-4:-1])[:230])
print('before the Field was ever opened:'); strip('this')
w.a_field.trigger(); settle(); v = w.field_page.view
calc = next(o for o in v.field.objects if o.kind == 'calculation' and 'Settled' in o.title); v.field.select(calc.id); v._describe(); v.update(); settle(5, 2)
print('with “%s” selected:' % calc.title)
strip('this'); strip('this | pick document.derivation.inputs | select symbol,value,unit'); strip('explain this'); strip('this | count')
strip('field.read | pick waiting | select kind,title')
v.setFocus(); settle(5, 2)
# T: trace
QTest.keyClick(v, Qt.Key_T); settle(100, 5); c = cards()[-1]; print('T on the calculation -> Field in front: %s | keyboard: %s' % (w._field_active, type(app.focusWidget()).__name__))
for line in said(c, 3): print('   |', line)
f = next(o for o in v.field.objects if o.kind == 'finding'); v.field.select(f.id); v._describe(); v.update(); settle(5, 2)
QTest.keyClick(v, Qt.Key_T); settle(100, 5); c = cards()[-1]
for line in said(c, 3)[2:]: print('T on a finding   |', line)
save('Graphite_Power_01_Trace_%s.png' % tag)
# what if
v.field.select(calc.id); v._describe(); v.update(); settle(5, 2)
for q in ('what if B3 were 320?', 'What if the settled current were 320 and voltage 11.4', 'what if the moon were 5', 'what if it rains'):
    w.shell2.ask(q); settle(100, 5); c = cards()[-1]; print('Q %-58r ->' % q, ' || '.join(said(c, 3))[:420])
save('Graphite_Power_02_What_If_%s.png' % tag)
v.field.select(f.id); v._describe(); v.update(); settle(5, 2); w.shell2.ask('what if B3 were 320?'); settle(100, 5); print('what-if with a finding selected ->', said(cards()[-1], 1)[0][:140])
# D shows the trace step; the sheet is untouched
v.field.select(calc.id); v._describe(); v.update(); settle(5, 2); QTest.keyClick(v, Qt.Key_D); settle(60, 4); print('D ->', [s[0] for s in v.steps])
r = k.dispatch('office.get', {'id': 'owner:db5f669f863d4c71b89fa7ba348957da'}, p); print('the sheet still says B3 =', r['result']['document']['sheets'][0]['cells']['B3']['value'], '| calculations:', [(o.title, o.state) for o in v.field.objects if o.kind == 'calculation'])
