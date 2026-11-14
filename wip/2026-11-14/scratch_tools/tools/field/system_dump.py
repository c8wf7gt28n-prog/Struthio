from PySide6.QtWidgets import QApplication, QAbstractButton, QLabel, QWidget
from PySide6.QtCore import QTimer
top = w.shell2.top; settle(200, 3)
def dump():
    m = QApplication.activePopupWidget()
    if m is None: print('no menu'); return
    try:
        print('menu class:', type(m).__name__, m.objectName(), m.width(), 'x', m.height())
        rows = []
        for c in m.findChildren(QWidget):
            if not c.isVisible(): continue
            if isinstance(c, QAbstractButton): rows.append((c.mapTo(m, c.rect().topLeft()).y(), 'row   ', c.text().replace('\n', ' / ')[:70], c.isEnabled()))
            elif isinstance(c, QLabel) and c.text().strip(): rows.append((c.mapTo(m, c.rect().topLeft()).y(), 'label ', c.text().replace('\n', ' / ')[:70], True))
        for y, kind, text, on in sorted(rows): print('  %4d %s %s%s' % (y, kind, text, '' if on else '   (dim)'))
        m.grab().save(str(OUT / ('System_menu_%s.png' % tag)))
    finally: m.close()
QTimer.singleShot(900, dump); QTest.mouseClick(top.nice, Qt.LeftButton); settle(400, 4)
