try:        # this probe walks the Approve path: from 0.6.0 that is Stacy's hand at "Ask first" (it opens on "Do and show")
    from workbench import stacy_hand as _hand; _hand.choose(w, 'ask'); w.shell2.face.show_hand()
except ImportError: pass
# the pass for the eye and the hand: ? keys, the brief as a page, Talk at a glance, the strip under the sheets
from PySide6.QtWidgets import QLabel
k = w.ledger_bridge.kernel; p = operator(); face = w.shell2.face
def cards(): return [face.lines.itemAt(i).widget() for i in range(face.lines.count()) if face.lines.itemAt(i).widget() is not None]
def said(card, n=4): return [l.text().replace('​', '')[:900] for l in card.findChildren(QLabel)][:n]
w.a_field.trigger(); settle(); v = w.field_page.view; page = w.field_page
def pick(words):
    o = next(o for o in v.field.objects if words in o.title); v.field.select(o.id); v._reveal(); v._describe(); v.update(); settle(5, 2); return o
# ? : the keys
f = pick('The reviewed sheet keeps'); before = v.selected().id
QTest.keyClick(v, Qt.Key_Question, Qt.ShiftModifier, 0) if False else QTest.keyClicks(v, '?'); settle(40, 3)
print('? -> card open: %s | title: %r | can scroll: %s' % (v.reading is not None, v.reading and v.reading['title'], v._read_room > 1))
save('Graphite_UX_01_The_Keys_%s.png' % tag)
QTest.keyClick(v, Qt.Key_D); settle(20, 2); print('   D while the card is open does nothing: steps %s | card still open %s' % (bool(v.steps), v.reading is not None))
QTest.keyClick(v, Qt.Key_PageDown); settle(20, 2); at = v._read_at; QTest.keyClick(v, Qt.Key_Escape); settle(20, 2)
print('   PgDn scrolled to %.0f of %.0f | Esc closed it: %s | selection kept: %s | Field in front: %s' % (at, v._read_room, v.reading is None, v.selected().id == before, w._field_active))
# X: a doubt, in the column
QTest.keyClick(v, Qt.Key_X); settle(150, 5); c = cards()[-1]; lines = said(c, 3)
print('X -> page open: %s | light: %s | title: %r | %s' % (v.reading is not None, v.reading and v.reading['light'], v.reading and v.reading['title'][:50], [(s_, t_[:50]) for s_, t_ in (v.reading['lines'] if v.reading else ())][:4]))
print('   Talk card, in order:', [l.replace('\n', ' / ')[:70] for l in lines])
save('Graphite_UX_02_A_Doubt_On_The_Field_%s.png' % tag)
was = v.selected().id; QTest.keyClick(v, Qt.Key_Up); settle(20, 2); print('   an arrow steps it aside and moves: page %s | moved %s' % (v.reading is None, v.selected().id != was))
f = pick('The reviewed sheet keeps'); QTest.keyClick(v, Qt.Key_X); settle(150, 5); QTest.keyClick(v, Qt.Key_D); settle(80, 4); print('   X then D: page %s | steps offered %d' % (v.reading is None, len(v.steps)))
QTest.keyClick(v, Qt.Key_Escape); settle(10, 2); QTest.keyClick(v, Qt.Key_X); settle(150, 5); QTest.keyClick(v, Qt.Key_Escape); settle(10, 2); print('   X then Esc: page %s | Field in front %s' % (v.reading is None, w._field_active))
# what if: rows in the column, the strip under the sheets
sheet = pick('07 Limits Rev B'); w.shell2.ask('what if the pulse duration were 100?'); settle(150, 5); c = cards()[-1]; lines = said(c, 3)
print('WHAT IF ->', lines[0][:120]); print('   rows:\n      ' + lines[2][:560].replace('\n', '\n      '))
v.setFocus(); settle(20, 2); save('Graphite_UX_03_What_If_%s.png' % tag); QTest.keyClick(v, Qt.Key_Escape); settle(10, 2)
# T: a trace, in the column
f = pick('Settled draw is 3.36 W'); QTest.keyClick(v, Qt.Key_T); settle(150, 5); print('T -> rows:\n      ' + said(cards()[-1], 3)[2][:400].replace('\n', '\n      '))
# B: the brief as a page
n_cards = len(cards()); QTest.keyClick(v, Qt.Key_B); settle(200, 6)
print('B -> page open: %s | title: %r | lines: %d | go offered: %r | new Talk cards: %d | can scroll: %s' % (v.reading is not None, v.reading and v.reading['title'], len(v.reading['lines']) if v.reading else 0, v.go, len(cards()) - n_cards, v._read_room > 1))
save('Graphite_UX_04_The_Brief_As_A_Page_%s.png' % tag)
QTest.keyClick(v, Qt.Key_Down); QTest.keyClick(v, Qt.Key_Down); settle(20, 2); QTest.keyClick(v, Qt.Key_Escape); settle(30, 3)
print('   Esc closes the page and withdraws the go: page %s | go %r | pending %s | pages on the desk: %d' % (v.reading is None, v.go, page.pending is not None, len([o for o in v.field.objects if o.kind == 'document'])))
QTest.keyClick(v, Qt.Key_G); settle(100, 4); print('   G after Esc keeps nothing: briefs %d' % len([o for o in v.field.objects if o.tag == 'BRIEF']))
QTest.keyClick(v, Qt.Key_B); settle(200, 6); QTest.keyClick(v, Qt.Key_G); settle(300, 6)
print('B then G -> page closed: %s | brief on the desk: %s | selected: %s' % (v.reading is None, any(o.tag == 'BRIEF' for o in v.field.objects), v.selected().title[:40]))
print('keyboard in:', type(app.focusWidget()).__name__, '| Field in front:', w._field_active)
