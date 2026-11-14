from PySide6.QtWidgets import QPushButton, QApplication, QStyleOptionButton, QStyle
from PySide6.QtGui import QEnterEvent, QColor
from PySide6.QtCore import QPointF, QEvent
link = next(b for b in w.findChildren(QPushButton) if b.isVisible() and b.text() == 'Service details')
def colours(b):
    img = b.grab().toImage(); seen = {}
    for y in range(0, img.height()):
        for x in range(0, img.width()):
            c = img.pixelColor(x, y).name(); seen[c] = seen.get(c, 0) + 1
    return sorted(seen.items(), key=lambda kv: -kv[1])[:4]
print('before:', colours(link))
c = QPointF(link.rect().center()); QApplication.sendEvent(link, QEnterEvent(c, c, QPointF(link.mapToGlobal(link.rect().center())))); link.setAttribute(Qt.WA_UnderMouse, True); link.update(); settle(40, 3)
opt = QStyleOptionButton(); opt.initFrom(link)
print('under:', link.underMouse(), '| WA_Hover:', link.testAttribute(Qt.WA_Hover), '| state has MouseOver:', bool(opt.state & QStyle.State_MouseOver), '| enabled:', link.isEnabled())
print('after:', colours(link))
print('own sheet:', link.styleSheet().replace(chr(10), ' ')[:300])
p_ = link.parentWidget(); chain = []
while p_ is not None:
    if p_.styleSheet(): chain.append((type(p_).__name__, p_.objectName(), [l for l in p_.styleSheet().split(chr(10)) if 'settingsAction' in l or 'QPushButton' in l][:6]))
    p_ = p_.parentWidget()
for row in chain: print('  parent sheet:', str(row)[:600])
