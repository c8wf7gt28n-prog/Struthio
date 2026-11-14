# zoom and fit: Z, + and -, Ctrl+wheel about the pointer, a click and a drag while zoomed, the reading page unzoomed
from PySide6.QtCore import QPointF, QEvent, QPoint
from PySide6.QtGui import QMouseEvent, QWheelEvent
from PySide6.QtWidgets import QApplication
w.a_field.trigger(); settle(); v = w.field_page.view; v.setFocus(); settle(20, 2)
def seen():
    body = v._layout(); return sum(1 for i in v._placed if body.contains(v.sheet_rect(i, body))), len(v._placed)
def send(kind, pos, button=Qt.NoButton, buttons=Qt.NoButton):
    QApplication.sendEvent(v, QMouseEvent(kind, QPointF(pos), QPointF(v.mapToGlobal(pos)), button, buttons, Qt.NoModifier)); settle(10, 2)
print('at 100%%: sheets whole in the window %d of %d | zoom %.2f' % (*seen(), v.zoom))
QTest.keyClick(v, Qt.Key_Z); settle(120, 4)
print('Z: sheets whole in the window %d of %d | zoom %.2f | fitted stays: %s | scroll %.0f,%.0f' % (*seen(), v.zoom, v._fitted, v.scroll_x, v.scroll_y))
save('Graphite_Zoom_01_The_Whole_Desk_%s.png' % tag)
# a click on a sheet as it is seen opens that sheet
o = next(o for o in v.field.objects if o.title.startswith('07 Limits Rev B')); r = v.sheet_rect(o.id, v._layout()); at = r.center().toPoint()
send(QEvent.MouseMove, at); print('hover while zoomed ->', v.field.get(v._hover).title if v._hover else None)
send(QEvent.MouseButtonPress, at, Qt.LeftButton, Qt.LeftButton); send(QEvent.MouseButtonRelease, at, Qt.LeftButton); settle(200, 6)
print('click while zoomed -> selected:', v.field.get(v.field.selected).title, '| Field in front:', w._field_active)
w.a_field.trigger(); settle(100, 4); v.setFocus(); settle(20, 2); print('back in the Field: zoom %.2f fitted %s' % (v.zoom, v._fitted))
# keys walk while zoomed, and the selected sheet stays in view
for key in (Qt.Key_Right, Qt.Key_Down, Qt.Key_Left):
    QTest.keyClick(v, key); settle(10, 2)
body = v._layout(); print('after arrows: selected', v.field.get(v.field.selected).title[:28], '| in view:', body.contains(v.sheet_rect(v.field.selected, body)))
# the reading page keeps the reading size
QTest.keyClick(v, Qt.Key_Question); settle(60, 3); print('key card open:', v.reading is not None, '| its rect width:', round(v._reading_rect(v.body()).width())); save('Graphite_Zoom_02_Keys_While_Zoomed_%s.png' % tag); QTest.keyClick(v, Qt.Key_Escape); settle(20, 2)
QTest.keyClick(v, Qt.Key_Z); settle(120, 4); print('Z again: zoom %.2f | fitted %s' % (v.zoom, v._fitted))
# + and -
QTest.keyClick(v, Qt.Key_Minus); settle(10, 2); a = v.zoom; QTest.keyClick(v, Qt.Key_Minus); settle(10, 2); b = v.zoom; QTest.keyClick(v, Qt.Key_Plus, Qt.ShiftModifier); settle(10, 2); c = v.zoom
print('- - + ->', a, b, c)
# Ctrl+wheel about the pointer: where the surface has room to move, the sheet under the pointer stays under it
v.set_zoom(1.0); settle(10, 2)
def wheel(pos, dy, mods=Qt.ControlModifier):
    QApplication.sendEvent(v, QWheelEvent(QPointF(pos), QPointF(v.mapToGlobal(pos.toPoint())), QPoint(0, 0), QPoint(0, dy), Qt.NoButton, mods, Qt.NoScrollPhase, False)); settle(10, 2)
body = v._layout(); mid = next((i for i in v._placed if body.contains(v.sheet_rect(i, body).center()) and v.sheet_rect(i, body).center().x() > body.center().x() - 80 and v.sheet_rect(i, body).center().y() > body.top() + 120), None)
at = v.sheet_rect(mid, body).center() if mid else body.center(); name = v.field.get(mid).title if mid else None
for _ in range(6): wheel(at, 120)
print('Ctrl+wheel in x6 about “%s”: zoom %.2f | under the pointer still: %s' % (name, v.zoom, v.field.get(v._hit(at)).title if v._hit(at) else None))
for _ in range(3): wheel(at, -120)
print('Ctrl+wheel out x3: zoom %.2f | under the pointer still: %s' % (v.zoom, v.field.get(v._hit(at)).title if v._hit(at) else None))
save('Graphite_Zoom_03_Nearer_%s.png' % tag)
# a drag while zoomed moves the surface by what the hand moved
v.set_zoom(1.4); settle(10, 2); sx, sy = v.scroll_x, v.scroll_y; body = v._layout(); start = QPoint(int(body.center().x()), int(body.bottom() - 60))
free = next((QPoint(x, y) for y in range(int(body.top()) + 30, int(body.bottom()) - 30, 17) for x in range(int(body.left()) + 30, int(body.right()) - 30, 23) if not v._hit(QPointF(x, y))), start)
send(QEvent.MouseButtonPress, free, Qt.LeftButton, Qt.LeftButton); send(QEvent.MouseMove, free - QPoint(70, 56), Qt.NoButton, Qt.LeftButton); send(QEvent.MouseButtonRelease, free - QPoint(70, 56), Qt.LeftButton)
print('drag by (70,56) at 140%%: scroll moved by (%.1f, %.1f) of a possible (%.1f, %.1f)' % (v.scroll_x - sx, v.scroll_y - sy, 70 / 1.4, 56 / 1.4), '| room to scroll:', round(v._surface[0] - v.room()[0]), round(v._surface[1] - v.room()[1]))
QTest.keyClick(v, Qt.Key_0, Qt.ControlModifier); settle(10, 2); print('Ctrl+0: zoom %.2f' % v.zoom)
# the foot shows Z as a place to click
v.repaint(); settle(10, 2); z = next((b for b, kk, tx, words in v._hot if kk == Qt.Key_Z), None); print('Z can be clicked (the foot or the strip):', z is not None)
if z is not None:
    send(QEvent.MouseButtonPress, z.center().toPoint(), Qt.LeftButton, Qt.LeftButton); send(QEvent.MouseButtonRelease, z.center().toPoint(), Qt.LeftButton); print('clicked Z: zoom %.2f' % v.zoom)
print('keyboard in:', type(app.focusWidget()).__name__)
