import sys
from PySide6.QtWidgets import QApplication, QPushButton, QWidget, QVBoxLayout
from PySide6.QtCore import Qt, QPointF, QEvent
from PySide6.QtGui import QHoverEvent, QMouseEvent
app = QApplication(sys.argv)
def colours(b):
    img = b.grab().toImage(); seen = {}
    for y in range(img.height()):
        for x in range(img.width()):
            c = img.pixelColor(x, y).name(); seen[c] = seen.get(c, 0) + 1
    return sorted(seen.items(), key=lambda kv: -kv[1])[:3]
SHEET = "QPushButton {background:transparent;color:#eee9dd;border:0;border-radius:0;padding:6px 7px;text-decoration:underline;}\nQPushButton:hover {color:#cbf08b;}\nQPushButton:focus {border-bottom:2px solid #eee9dd;}"
for name, sheet in (('with background:transparent', SHEET), ('hover also sets a background', SHEET.replace('QPushButton:hover {color:#cbf08b;}', 'QPushButton:hover {color:#cbf08b;background:#1b2817;}')), ('hover with border', SHEET.replace('QPushButton:hover {color:#cbf08b;}', 'QPushButton:hover {color:#cbf08b;border-bottom:2px solid #c3ed74;}'))):
    host = QWidget(); lay = QVBoxLayout(host); b = QPushButton('Service details'); lay.addWidget(b); b.setStyleSheet(sheet); host.show(); app.processEvents()
    before = colours(b); b.setAttribute(Qt.WA_UnderMouse, True); c = QPointF(b.rect().center()); app.sendEvent(b, QHoverEvent(QEvent.HoverMove, c, QPointF(b.mapToGlobal(b.rect().center())), QPointF(-1, -1))); app.sendEvent(b, QMouseEvent(QEvent.MouseMove, c, QPointF(b.mapToGlobal(b.rect().center())), Qt.NoButton, Qt.NoButton, Qt.NoModifier)); b.update(); app.processEvents(); print(name, '|', before, '->', colours(b))
