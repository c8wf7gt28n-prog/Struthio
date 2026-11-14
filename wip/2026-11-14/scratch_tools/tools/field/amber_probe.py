try:        # this probe walks the Approve path: from 0.6.0 that is Stacy's hand at "Ask first" (it opens on "Do and show")
    from workbench import stacy_hand as _hand; _hand.choose(w, 'ask'); w.shell2.face.show_hand()
except ImportError: pass
# the amber glow: the sheet that has the keyboard, what waits, a stale wire, Approve, the reading page
from PySide6.QtCore import QPointF, QEvent, QPoint
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication
k = w.ledger_bridge.kernel; p = operator()
w.a_field.trigger(); settle(); v = w.field_page.view; page = w.field_page
def pick(title):
    o = next(o for o in v.field.objects if o.title.startswith(title)); v.field.select(o.id); v._reveal(); v._describe(); v.update(); settle(10, 2); return o
pick('07 Settled power'); v.setFocus(); settle(20, 2)
save('Graphite_Amber_01_Has_The_Keyboard_%s.png' % tag); print('saved: the selected sheet glows amber | focus in the Field:', v.hasFocus())
# make something wait: change a cell of the sheet through the desk's own set, approved
sheet = next(o for o in v.field.objects if o.title == '07 Bench readings')
got = k.dispatch('office.get', {'id': sheet.target['id']}, p) if sheet.target else None
w.shell2.ask('set B3 to 300') if False else None
pick('07 Bench readings'); w.shell2.ask('set B3 to 300'); settle(200, 6)
print('waits:', repr(v.go)[:80])
v.setFocus(); v.repaint(); settle(20, 2); save('Graphite_Amber_02_A_Change_Waits_%s.png' % tag)
QTest.keyClick(v, Qt.Key_G); settle(300, 8); v.setFocus(); settle(30, 3)
print('after approve:', [(o.title[:24], o.state) for o in v.field.objects if o.kind == 'calculation'])
pick('07 Settled power'); v.setFocus(); settle(30, 3)
save('Graphite_Amber_03_What_Waits_Glows_%s.png' % tag)
v.repaint(); settle(10, 2); lamp = next((b for b, kk, tx, words in v._hot if kk == Qt.Key_A), None); print('a lamp at the head says something waits, and can be clicked:', lamp is not None)
if lamp is not None:
    was = v.field.selected
    QApplication.sendEvent(v, QMouseEvent(QEvent.MouseButtonPress, QPointF(lamp.center()), QPointF(v.mapToGlobal(lamp.center().toPoint())), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)); settle(20, 2)
    print('clicked the lamp -> selected:', v.field.get(v.field.selected).title[:30], '| state:', v.field.get(v.field.selected).state)
pick('07 Settled power'); v.setFocus(); settle(30, 3)
QTest.keyClick(v, Qt.Key_X); settle(200, 6); save('Graphite_Amber_04_A_Page_Has_The_Keyboard_%s.png' % tag); QTest.keyClick(v, Qt.Key_Escape); settle(30, 3)
