# 0.4.3: the ripple on the Field, the brief, Backspace
from PySide6.QtWidgets import QLabel
k = w.ledger_bridge.kernel; p = operator(); face = w.shell2.face
def cards(): return [face.lines.itemAt(i).widget() for i in range(face.lines.count()) if face.lines.itemAt(i).widget() is not None]
def said(card, n=4): return [l.text().replace('​', '')[:900].replace('\n', ' / ') for l in card.findChildren(QLabel)][:n]
w.a_field.trigger(); settle(); v = w.field_page.view; page = w.field_page
def pick(words):
    o = next(o for o in v.field.objects if words in o.title); v.field.select(o.id); v._reveal(); v._describe(); v.update(); settle(5, 2); return o
# -- what if, on a sheet, in the owner's words
revb = pick('07 Limits Rev B')
w.shell2.ask('what if the pulse duration were 100?'); settle(120, 5); c = cards()[-1]
print('WHAT IF on a sheet ->', said(c, 1)[0][:200]); print('   line:', said(c, 3)[1][:200]); print('   rows:', said(c, 3)[2][:700])
print('   marks on the Field:', {v.field.get(i).title[:34]: words for i, words in v.would.items()}, '|', v.would_said)
save('Graphite_Ripple_01_What_If_On_A_Sheet_%s.png' % tag)
v.setFocus(); f = pick('Startup ran 30 ms'); settle(10, 2); save('Graphite_Ripple_02_A_Finding_That_Would_Move_%s.png' % tag)
print('   moving keeps the marks:', bool(v.would)); QTest.keyClick(v, Qt.Key_Escape); settle(10, 2); print('   first Esc clears them, Field still in front:', not v.would, w._field_active)
r = k.dispatch('office.get', {'id': revb.target['id']}, p); print('   the sheet still says B4 =', r['result']['document']['sheets'][0]['cells']['B4']['value'])
# -- what if, on a calculation, still works and now follows the wires
calc = pick('07 Settled power'); w.shell2.ask('what if B3 were 320?'); settle(120, 5); c = cards()[-1]
print('WHAT IF on a calculation ->', said(c, 3)[2][:420]); print('   marks:', sorted(v.would.values()))
w.shell2.ask('what if the moon were 5'); settle(80, 4); print('   a number it does not have ->', said(cards()[-1], 1)[0][:200])
pick('07 Bench readings'); w.shell2.ask('what if it rains'); settle(80, 4); print('   no number at all ->', said(cards()[-1], 1)[0][:200])
QTest.keyClick(v, Qt.Key_Escape); settle(10, 2)
# -- Backspace: where I was
v.setFocus(); a = pick('07 Bench readings'); b = pick('Rev A allowed'); c2 = pick('What stretched')
QTest.keyClick(v, Qt.Key_Backspace); settle(10, 2); one = v.selected().title; QTest.keyClick(v, Qt.Key_Backspace); settle(10, 2); two = v.selected().title
print('BACKSPACE -> %r then %r | Field in front: %s' % (one[:30], two[:30], w._field_active))
# -- B: the brief
QTest.keyClick(v, Qt.Key_B); settle(200, 6); staged = cards()[-1]
print('B -> page: %r | lines: %d | staged: %s | go offered: %r' % (v.reading and v.reading['title'], len(v.reading['lines']) if v.reading else 0, said(staged, 1)[0][:110], v.go))
print('   first lines:', [t_[:70] for _, t_ in (v.reading['lines'] if v.reading else ())][:4])
save('Graphite_Brief_01_Read_Before_It_Is_Kept_%s.png' % tag)
before = len([o for o in v.field.objects if o.kind == 'document'])
QTest.keyClick(v, Qt.Key_G); settle(250, 6)
brief = next((o for o in v.field.objects if o.tag == 'BRIEF'), None)
print('G -> pages before %d, now %d | brief on the Field: %s | state: %s | selected: %s' % (before, len([o for o in v.field.objects if o.kind == 'document']), bool(brief), brief and brief.state, v.selected().title[:40]))
save('Graphite_Brief_02_Kept_As_A_Page_%s.png' % tag)
got = k.dispatch('documents.get', {'id': brief.target['id']}, p)['result']; doc = got['document']
print('   the page: %d blocks, styles %s, origin %s, has a mark: %s, source_state in get: %s' % (len(doc['blocks']), sorted({b['style'] for b in doc['blocks']}), doc.get('origin'), bool(doc.get('brief')), 'source_state' in got))
QTest.keyClick(v, Qt.Key_X); settle(120, 5); print('   X on the brief ->', [(s_, t_[:90]) for s_, t_ in (v.reading['lines'] if v.reading else ())]); QTest.keyClick(v, Qt.Key_Escape); settle(10, 2)
# open it in Documents and come back
QTest.keyClick(v, Qt.Key_Return); settle(150, 5); print('   Enter opens it:', type(w.tabs.currentWidget()).__name__, '| field in front:', w._field_active)
w.a_field.trigger(); settle(60, 4); v = w.field_page.view
# the desk changes: a new finding. The brief waits; D offers to write it again; C settles it last
inv = k.dispatch('investigation.list', {}, p)['result']['investigations'][0]['id']
k.dispatch('investigation.claim', {'id': inv, 'text': 'The margin under Rev A was 10 ms.', 'role': 'FINDING'}, p)
QTest.keyClick(v, Qt.Key_R); settle(120, 5); brief = next(o for o in v.field.objects if o.tag == 'BRIEF'); print('after a new finding -> brief state:', brief.state, brief.lines)
v.field.select(brief.id); v._reveal(); v._describe(); v.update(); settle(5, 2)
QTest.keyClick(v, Qt.Key_D); settle(80, 4); print('D on the brief ->', [(s.words, s.kind) for s in page.steps])
n = next(i for i, s in enumerate(page.steps) if s.words == 'Write it again'); QTest.keyClick(v, Qt.Key_1 + n); settle(80, 4); QTest.keyClick(v, Qt.Key_G); settle(250, 6)
briefs = [o for o in v.field.objects if o.tag == 'BRIEF']; print('G -> briefs on the Field: %d | state: %s | aside: %r' % (len(briefs), briefs[0].state, v.field.aside))
docs = k.dispatch('documents.list', {}, p)['result']['documents']; print('   in Documents:', [(dd['title'][:28]) for dd in docs if 'brief' in dd['title']])
print('keyboard in:', type(app.focusWidget()).__name__, '| Field in front:', w._field_active)
