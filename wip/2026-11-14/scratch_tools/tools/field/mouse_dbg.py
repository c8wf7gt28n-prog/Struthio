from PySide6.QtCore import QPoint, QPointF, QTimer, QEvent
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication
w.a_field.trigger(); settle(); v = w.field_page.view; page = w.field_page
def tile(words): return next(o for o in v.field.objects if words in o.title)
def send(kind, pos, button=Qt.NoButton, buttons=Qt.NoButton):
    QApplication.sendEvent(v, QMouseEvent(kind, QPointF(pos), QPointF(v.mapToGlobal(pos)), button, buttons, Qt.NoModifier)); settle(10, 2)
def empty_ground():
    body = v._layout()
    for x in range(int(body.right()) - 12, int(body.left()), -24):
        for y in range(int(body.top()) + 30, int(body.bottom()) - 30, 24):
            if v._hit(QPointF(x, y)) is None and not any(b.contains(QPointF(x, y)) for b, *_ in v._hot): return QPoint(x, y)
o = tile('07 Bench readings')
print('view size', v.width(), v.height(), '| zoom', getattr(v, 'zoom', None), '| whole', getattr(v, 'whole', None), '| pan', getattr(v, 'pan', None), getattr(v, 'offset', None))
for n in range(6):
    body = v._layout(); r = v.sheet_rect(o.id, body)
    print(n, 'body', [round(x) for x in body.getRect()], '| tile', [round(x) for x in r.getRect()], '| inside', body.adjusted(4, 4, -4, -30).contains(r), '| hit at centre', getattr(v._hit(r.center()), 'title', None))
    dx = 0 if body.left() + 4 <= r.left() and r.right() <= body.right() - 4 else (body.center().x() - r.center().x())
    dy = 0 if body.top() + 4 <= r.top() and r.bottom() <= body.bottom() - 30 else (body.center().y() - r.center().y())
    start = empty_ground(); print('   start', start, 'dx', round(dx), 'dy', round(dy))
    if start is None: break
    end = QPoint(start.x() + int(max(-200, min(200, dx))), start.y() + int(max(-160, min(160, dy))))
    send(QEvent.MouseButtonPress, start, Qt.LeftButton, Qt.LeftButton); send(QEvent.MouseMove, end, Qt.NoButton, Qt.LeftButton); send(QEvent.MouseButtonRelease, end, Qt.LeftButton)
save('Mouse_dbg_%s.png' % tag)
print('DONE')
