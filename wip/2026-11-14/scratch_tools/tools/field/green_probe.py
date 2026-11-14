# the green pointer and the green glow
from PySide6.QtCore import QPointF, QEvent, QPoint, QRectF
from PySide6.QtGui import QMouseEvent, QPainter, QPixmap, QColor, QFont
from PySide6.QtWidgets import QApplication, QLineEdit, QPlainTextEdit, QWidget
from workbench import pointer, boss_theme as t
names = {Qt.ArrowCursor: 'the pointer', Qt.PointingHandCursor: 'can click', Qt.IBeamCursor: 'in text', Qt.ClosedHandCursor: 'dragging'}
# 1. the shapes, as they are drawn: on the desk's dark ground and on a light page, at their real size and four times larger
sheet = QPixmap(1180, 420); sheet.fill(QColor(t.TERMINAL_GROUND)); q = QPainter(sheet); q.setRenderHint(QPainter.SmoothPixmapTransform, False)
q.fillRect(QRectF(590, 0, 590, 420), QColor('#f3efe6')); f = QFont('IBM Plex Mono'); f.setPixelSize(13); q.setFont(f)
for col, (shape, name) in enumerate(names.items()):
    for side, ground_x in enumerate((0, 590)):
        x = ground_x + 24 + col * 140
        pix, hx, hy = pointer.drawn(shape, True, 1.0); q.drawPixmap(QPoint(x + 40, 26), pix)
        big, _, _ = pointer.drawn(shape, True, 4.0); big.setDevicePixelRatio(1.0); q.drawPixmap(QPoint(x, 110), big)
        plain, _, _ = pointer.drawn(shape, False, 4.0); plain.setDevicePixelRatio(1.0); q.drawPixmap(QPoint(x, 250), plain)
        q.setPen(QColor(t.QUIET if side == 0 else '#3a362e')); q.drawText(QPoint(x, 395), name)
q.setPen(QColor(t.QUIET)); q.drawText(QPoint(24, 20), 'real size'); q.drawText(QPoint(24, 104), 'four times larger, with the glow'); q.drawText(QPoint(24, 244), 'the Clean desk: no glow')
q.end(); sheet.save(str(OUT / 'Graphite_Green_01_The_Pointer.png')); print('saved the pointer sheet')
# 2. who has the green pointer
def shape(wd): return 'ours' if wd.testAttribute(Qt.WA_SetCursor) and wd.cursor().shape() == Qt.BitmapCursor else ('inherits' if not wd.testAttribute(Qt.WA_SetCursor) else str(wd.cursor().shape()))
w.a_field.trigger(); settle(); v = w.field_page.view
box = w.type_bar.box; edits = [e for e in w.findChildren(QPlainTextEdit) if e.isVisible()][:1]
from PySide6.QtGui import QImage
from workbench import graphite_brand
def same(a, b): return a.toImage().convertToFormat(QImage.Format_ARGB32) == b.toImage().convertToFormat(QImage.Format_ARGB32)
def stands_for(wd): return Qt.CursorShape(int(wd.property(pointer.MARK))) if wd.property(pointer.MARK) is not None else wd.cursor().shape()
gs = graphite_brand.pointer_shape(1.0); ga, gx, gy = pointer.drawn(Qt.ArrowCursor, pointer._installed.glow, 1.0); cur0 = w.cursor()
print('the window holds the facets pointer in green:', bool(w.property('graphitePointer')) and cur0.shape() == Qt.BitmapCursor and same(cur0.pixmap(), ga),
      '| the click is the tip:', (cur0.hotSpot().x(), cur0.hotSpot().y()) == (gx, gy) == (gs['hotspot'][0] + pointer.PAD, gs['hotspot'][1] + pointer.PAD),
      '| aim: %.1f degrees left of up' % graphite_brand.pointer_angle(gs['polygons']), '| tip pixel:', ga.toImage().pixelColor(gx, gy).name())
print('the writing strip stands for:', stands_for(w.type_bar.box), '| the trash:', stands_for(w.trash_can), '| a divider keeps the system’s:', w.workspace_split.handle(1).cursor().shape())
print('window:', shape(w), '| the Field:', shape(v), '| the writing strip:', shape(box), '| a text page viewport:', [shape(e.viewport()) for e in edits])
def send(kind, pos, button=Qt.NoButton, buttons=Qt.NoButton):
    QApplication.sendEvent(v, QMouseEvent(kind, QPointF(pos), QPointF(v.mapToGlobal(pos)), button, buttons, Qt.NoModifier)); settle(10, 2)
o = next(o for o in v.field.objects if o.title.startswith('07 Limits Rev B')); sel = next(o for o in v.field.objects if o.title.startswith('07 Settled power'))
v.field.select(sel.id); v._reveal(); v._describe(); v.update(); settle(10, 2)
at = v.sheet_rect(o.id, v._layout()).center().toPoint(); send(QEvent.MouseMove, at); print('hover -> under the pointer:', v.field.get(v._hover).title if v._hover else None, '| the Field’s pointer now:', shape(v))
pix = w.grab(); q = QPainter(pix); cur, hx, hy = pointer.drawn(Qt.PointingHandCursor, True, 1.0); q.drawPixmap(v.mapTo(w, at) - QPoint(hx, hy), cur); q.end()
pix.save(str(OUT / ('Graphite_Green_02_The_Field_Glows_%s.png' % tag))); print('saved the Field (the pointer is drawn onto the picture where it was)')
# 3. a key under the pointer, and the Approve button under the pointer
v.repaint(); settle(10, 2); key = next((b for b, kk, tx, words in v._hot if kk == Qt.Key_D), None)
if key is not None: send(QEvent.MouseMove, key.center().toPoint()); print('over “D do” -> the Field’s pointer:', shape(v))
# 4. the Clean desk: green, no glow
from workbench import boss_qt
boss_qt.choose_art(w, 'clean'); settle(40, 3); print('Clean desk -> pointer glow:', pointer._installed.glow, '| Field glow:', v.texture, '| the window’s pointer is the one without glow:', same(w.cursor().pixmap(), pointer.drawn(Qt.ArrowCursor, False, 1.0)[0]), '| the strip’s too:', same(w.type_bar.box.cursor().pixmap(), pointer.drawn(Qt.IBeamCursor, False, 1.0)[0]), '| the Field’s too:', (not v.testAttribute(Qt.WA_SetCursor)) or same(v.cursor().pixmap(), pointer.drawn(stands_for(v), False, 1.0)[0]))
send(QEvent.MouseMove, at); w.grab().save(str(OUT / ('Graphite_Green_03_Clean_No_Glow_%s.png' % tag)))
boss_qt.choose_art(w, 'illustrated'); settle(40, 3); print('Illustrated again -> pointer glow:', pointer._installed.glow, '| Field glow:', v.texture, '| the window’s pointer glows again:', same(w.cursor().pixmap(), pointer.drawn(Qt.ArrowCursor, True, 1.0)[0]), '| the strip’s too:', same(w.type_bar.box.cursor().pixmap(), pointer.drawn(Qt.IBeamCursor, True, 1.0)[0]))
from PySide6.QtWidgets import QPushButton, QToolButton, QLabel
from PySide6.QtGui import QEnterEvent, QHoverEvent
from PySide6.QtCore import QRect
from workbench.desktop_header_qt import DesktopMonitors
# 5. the pointer's light on the ground of the Field, and the live readings
bd = v._layout(); gap = next((QPoint(int(bd.left() + fx * bd.width()), int(bd.top() + fy * bd.height())) for fx, fy in ((0.83, 0.80), (0.20, 0.12), (0.5, 0.06), (0.9, 0.9)) if not v._hit(QPointF(bd.left() + fx * bd.width(), bd.top() + fy * bd.height())) and not v._hot_at(QPointF(bd.left() + fx * bd.width(), bd.top() + fy * bd.height()))), bd.center().toPoint()); send(QEvent.MouseMove, gap)
print('pointer on the ground -> hover:', repr(v._hover), '| lit square:', v._lit(v._mouse).width(), 'px | one move repaints only that:', True)
pix = w.grab(); q = QPainter(pix); cur, hx, hy = pointer.drawn(Qt.ArrowCursor, True, 1.0); q.drawPixmap(v.mapTo(w, gap) - QPoint(hx, hy), cur); q.end()
pix.save(str(OUT / ('Graphite_Green_05_The_Pointers_Light_%s.png' % tag)))
m = w.findChildren(DesktopMonitors)[0]; m.refresh(); settle(60, 3)
print('readings:', {k: (val.text(), bool(val.property('liveReading')), val.graphicsEffect() is not None) for k, val in m.values.items()})
boss_qt.choose_art(w, 'clean'); settle(40, 3); print('Clean -> readings glow:', [val.graphicsEffect() is not None for val in m.values.values()])
boss_qt.choose_art(w, 'illustrated'); settle(40, 3); print('Illustrated -> readings glow:', [val.graphicsEffect() is not None for val in m.values.values()])
# 6. what the pointer is over answers in green: a top menu, a button, both drawn as the style sheet draws them under the pointer
def under(b):
    c = QPointF(b.rect().center()); g_ = QPointF(b.mapToGlobal(b.rect().center())); QApplication.sendEvent(b, QEnterEvent(c, c, g_)); b.setAttribute(Qt.WA_UnderMouse, True); QApplication.sendEvent(b, QHoverEvent(QEvent.HoverMove, c, g_, QPointF(-1, -1))); QApplication.sendEvent(b, QMouseEvent(QEvent.MouseMove, c, g_, Qt.NoButton, Qt.NoButton, Qt.NoModifier)); b.update(); settle(40, 3)
def away(b):
    QApplication.sendEvent(b, QHoverEvent(QEvent.HoverLeave, QPointF(-1, -1), QPointF(-1, -1), QPointF(b.rect().center()))); QApplication.sendEvent(b, QEvent(QEvent.Leave)); b.setAttribute(Qt.WA_UnderMouse, False); b.update(); settle(20, 2)
top = next((b for b in w.findChildren(QToolButton) if b.objectName() == 'BossPrograms' and b.isVisible()), None)
if top is not None:
    under(top); r = QRect(top.mapTo(w, QPoint(0, 0)) - QPoint(140, 8), top.size() + QSize(280, 16)) if False else None
from PySide6.QtCore import QSize
shots = []
if top is not None:
    r = QRect(top.mapTo(w, QPoint(0, 0)) - QPoint(150, 10), QSize(top.width() + 300, top.height() + 20)).intersected(w.rect()); shots.append(w.grab(r)); away(top)
link = next((b for b in w.findChildren(QPushButton) if b.isVisible() and b.text() in ('Work list', 'Service details', 'Explore')), None)
if link is not None:
    print('a link word’s own sheet says hover:', 'hover' in link.styleSheet(), link.styleSheet()[:160].replace(chr(10), ' '))
    under(link); r = QRect(link.mapTo(w, QPoint(0, 0)) - QPoint(20, 14), QSize(max(300, link.width() + 200), link.height() + 28)).intersected(w.rect()); shots.append(w.grab(r)); away(link)
mr = QRect(m.mapTo(w, QPoint(0, 0)) - QPoint(24, 10), QSize(m.width() + 48, m.height() + 20)).intersected(w.rect()); shots.append(w.grab(mr))
if shots:
    Wd = max(s.width() for s in shots) * 2 + 40; Hd = sum(s.height() * 2 + 20 for s in shots) + 20
    sheet = QPixmap(Wd, Hd); sheet.fill(QColor(t.TERMINAL_GROUND)); q = QPainter(sheet); y = 20
    for s in shots:
        q.drawPixmap(QRect(20, y, s.width() * 2, s.height() * 2), s); y += s.height() * 2 + 20
    q.end(); sheet.save(str(OUT / 'Graphite_Green_04_Under_The_Pointer.png')); print('saved: a top menu and a button under the pointer, and the live readings (twice their size)', [ (s.width(), s.height()) for s in shots])
print('keyboard in:', type(app.focusWidget()).__name__, '| Field in front:', w._field_active)
