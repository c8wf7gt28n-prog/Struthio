# the Field for the mouse: faces, the strip's words, the thumbs, − and +, the ⋯ on a sheet, the rail's keys, a page's "more", the second click
from PySide6.QtCore import QPointF, QEvent, QPoint, QTimer
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QMenu
w.a_field.trigger(); settle(); v = w.field_page.view; v.setFocus(); settle(20, 2)
def send(kind, pos, button=Qt.NoButton, buttons=Qt.NoButton, to=None):
    to = to or v; pos = QPoint(int(pos.x()), int(pos.y()))
    QApplication.sendEvent(to, QMouseEvent(kind, QPointF(pos), QPointF(to.mapToGlobal(pos)), button, buttons, Qt.NoModifier)); settle(10, 2)
def click(pos): send(QEvent.MouseMove, pos); send(QEvent.MouseButtonPress, pos, Qt.LeftButton, Qt.LeftButton); send(QEvent.MouseButtonRelease, pos, Qt.LeftButton)
def zone(test):
    v.repaint(); settle(10, 2); return next((b for b, k, tx, words in v._hot if test(k, words)), None)
def shape(): return Qt.CursorShape(int(v.property('greenPointer'))) if v.property('greenPointer') is not None else v.cursor().shape()
# 1. a face
z = zone(lambda k, words: ('programs face' in words.lower() or 'apps face' in words.lower())); send(QEvent.MouseMove, z.center()); print('1. over PROGRAMS: pointer', shape(), '| it is a place to click:', z is not None)
click(z.center()); settle(120, 4); print('   clicked -> face:', v.face); z = zone(lambda k, words: 'work face' in words.lower()); click(z.center()); settle(120, 4); print('   clicked WORK -> face:', v.face)
# 3. the thumb (the Field fits whole at 1920 by 1200 since 0.8.0: Z to reading size gives it bars to drag)
if not v._bars(v._layout()):QTest.keyClick(v, Qt.Key_Z); settle(400, 6)
bars = v._bars(v._layout()); print('3. bars:', [(b[0], round(b[2].height() if b[0] == 'v' else b[2].width())) for b in bars])
bar = next(b for b in bars if b[0] == 'v'); th = bar[2].center(); send(QEvent.MouseMove, th); print('   over the thumb: pointer', shape(), '| lit:', v._bar)
send(QEvent.MouseButtonPress, th, Qt.LeftButton, Qt.LeftButton); send(QEvent.MouseMove, th + QPointF(0, 120), Qt.NoButton, Qt.LeftButton); y1 = v.scroll_y
send(QEvent.MouseButtonRelease, th + QPointF(0, 120), Qt.LeftButton); print('   dragged it down 120: surface at %.0f of %.0f | let go: %s' % (y1, v._surface[1] - v.room()[1], v._grab is None))
save('Graphite_Mouse_01_Thumb_And_Strip_%s.png' % tag)
bar = next(b for b in v._bars(v._layout()) if b[0] == 'v'); click(QPointF(bar[1].center().x(), bar[1].top() + 3)); print('   clicked the track above the thumb: surface at %.0f' % v.scroll_y)
# 4. − and +
z = zone(lambda k, words: words.startswith('Smaller')); click(z.center()); a = v.zoom; z = zone(lambda k, words: words.startswith('Larger')); click(z.center()); print('4. clicked −: %.2f | clicked +: %.2f' % (a, v.zoom))
v.setFocus()
# 6. the rail's keys
v.setFocus(); z = zone(lambda k, words: words.startswith('Put this line')); print('6. “S line” in the rail can be clicked:', z is not None)
if z is not None: click(z.center()); settle(60, 3); print('   clicked -> the writing strip says:', w.type_bar.box.text()[:60])
v.setFocus(); settle(20, 2)
# 7. a page's “more”
QTest.keyClick(v, Qt.Key_Question); settle(80, 3); z = zone(lambda k, words: words.startswith('Read on')); print('7. the key card: “more ↓” can be clicked:', z is not None)
if z is not None: a0 = v._read_at; click(z.center()); print('   clicked -> read on by %.0f' % (v._read_at - a0))
QTest.keyClick(v, Qt.Key_Escape); settle(30, 2)
# 8. the second click of a double-click is dropped
o = next(o for o in v.field.objects if o.title == '07 Bench readings'); r = v.sheet_rect(o.id, v._layout())
if not v.body().contains(r.center()): v.field.select(o.id); v._reveal(); v.update(); settle(20, 2); r = v.sheet_rect(o.id, v._layout())
at = r.center() - QPointF(0, 10); send(QEvent.MouseMove, at); send(QEvent.MouseButtonPress, at, Qt.LeftButton, Qt.LeftButton); QApplication.sendEvent(v, QMouseEvent(QEvent.MouseButtonRelease, QPointF(at), QPointF(v.mapToGlobal(at.toPoint())), Qt.LeftButton, Qt.NoButton, Qt.NoModifier))
under = QApplication.widgetAt(v.mapToGlobal(at.toPoint())) or w; seen = []
class Spy(type(w).__mro__[-2] if False else object): pass
from PySide6.QtCore import QObject
class Watch(QObject):
    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.MouseButtonPress: seen.append(type(obj).__name__)
        return False
watch = Watch(); under.installEventFilter(watch)
local = under.mapFromGlobal(v.mapToGlobal(at.toPoint())); send(QEvent.MouseButtonPress, local, Qt.LeftButton, Qt.LeftButton, to=under); send(QEvent.MouseButtonRelease, local, Qt.LeftButton, to=under)
print('8. opened by a click: Field in front:', w._field_active, '| a second press at once reached the page under it:', bool(seen), '(', type(under).__name__, ')')
settle(650, 8); print('   after the double-click time the guard is lifted:', v._guard is None); under.removeEventFilter(watch)
print('keyboard in:', type(app.focusWidget()).__name__)
