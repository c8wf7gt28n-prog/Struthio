# the owner's own staC words: kept, run, piped, listed, forgotten; refusals
from PySide6.QtWidgets import QLabel
k = w.ledger_bridge.kernel; p = operator(); face = w.shell2.face; bar = w.type_bar; console = w.console
def d(op, a):
    r = k.dispatch(op, a, p); return r['result'] if r.get('ok') else {'ERROR': (r.get('error') or {}).get('message')}
def cards(): return [face.lines.itemAt(i).widget() for i in range(face.lines.count()) if face.lines.itemAt(i).widget() is not None]
def said(card, n=4): return [l.text().replace('​', '')[:400].replace('\n', ' / ') for l in card.findChildren(QLabel)][:n]
def strip(text):
    bar.set_target('slate', focus=False); bar.box.setFocus(); bar.box.setText(text); settle(10, 2); bar.refresh_context(); settle(5, 2)
    hint = bar.context.text() if hasattr(bar, 'context') else ''
    console.last_program = None; before = console.output.toPlainText()
    QTest.keyClick(bar.box, Qt.Key_Return, Qt.ControlModifier); settle(80, 4)
    out = console.output.toPlainText()[len(before):].strip().splitlines()
    print('strip %-62r hint %-24r ran: %s' % (text, hint, (console.last_program or 'NOT RUN · ' + (bar.message or ''))[:120]))
    print('      answer:', ' | '.join(l.strip() for l in out[-5:])[:300])
w.a_field.trigger(); settle(); v = w.field_page.view
print('words at first:', d('words.list', {}))
strip('word waits = field.read | pick waiting | select kind,title,state')
strip('waits'); strip('waits | count'); strip('explain waits'); strip('words')
strip('word doubts = field.doubt | pick rows | where verdict=doubt | select title,about')
strip('word mine = waits | where kind=question')          # a word built on a word is kept written out
strip('mine')
calc = next(o for o in v.field.objects if o.kind == 'calculation'); v.field.select(calc.id); v._describe(); v.update(); settle(5, 2)
strip('word inputs = this | pick document.derivation.inputs | select symbol,value,unit'); strip('inputs')
print('kept:', [(r['name'], r['line'][:70]) for r in d('words.list', {})['words']])
for bad in ('word field = field.read', 'word this = field.read', 'word office = field.read', 'word x = field.read', 'word waits', 'word Loud = field.read', 'word bad = /documents.create {"title":"x"}', 'word bad = not a line at all |||', 'word library = field.read', 'forget nothing-here'):
    strip(bad)
print('direct refusals:', d('words.keep', {'name': 'Bad Name', 'line': 'field.read'}).get('ERROR', '')[:90], '||', d('words.keep', {'name': 'w', 'line': 'field.read'}).get('ERROR', '')[:60])
# in conversation (Enter): Stacy reads the word
v.setFocus(); w.shell2.ask('waits'); settle(100, 5); c = cards()[-1]; print('ASK waits ->', ' || '.join(said(c, 3))[:330])
w.shell2.ask('words'); settle(100, 5); print('ASK words ->', said(cards()[-1], 3)[2][:260])
w.shell2.ask('word late = field.read | pick objects | where lately=yes | select kind,title'); settle(60, 4); print('ASK word late = … ->', said(cards()[-1], 1)[0][:200])
w.shell2.ask('forget late'); settle(60, 4); print('ASK forget late ->', said(cards()[-1], 1)[0][:120])
strip('forget mine'); strip('mine')
print('kept at the end:', [r['name'] for r in d('words.list', {})['words']])
# a word survives a fresh kernel read (it is a record, not a setting of this window)
from workbench.engine import engineering
print('through a fresh read:', [r['name'] for r in engineering(w.root).dispatch('words.list', {}, p)['result']['words']])
print('keyboard in:', type(app.focusWidget()).__name__, '| Field in front:', w._field_active)
