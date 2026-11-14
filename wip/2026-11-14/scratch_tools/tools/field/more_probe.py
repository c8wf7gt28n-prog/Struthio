# the More menus press the buttons they stand for; a tool answers the pointer; link words are underlined
from PySide6.QtWidgets import QPushButton, QApplication
from PySide6.QtGui import QMouseEvent, QHoverEvent
from PySide6.QtCore import QPointF, QEvent
w.a_field.trigger(); settle(); v = w.field_page.view
def open_tile(title):
    o = next((o for o in v.field.objects if o.title.startswith(title)), None)
    w.a_field.trigger(); settle(150, 4); v.field.select(o.id); v._describe(); QTest.keyClick(v, Qt.Key_Return); settle(900, 8); return w.tabs.currentWidget()
def line(button, words):
    button.menu().aboutToShow.emit(); return next(a for a in button.menu().actions() if a.text() == words)
page = open_tile('07_Bench_Readings.pdf'); pressed = []
page.refresh_button.clicked.connect(lambda *a: pressed.append('Check original')); page.buttons['OCR this page'].clicked.disconnect(); page.buttons['OCR this page'].clicked.connect(lambda *a: pressed.append('OCR this page'))
line(page.more, 'Check original').trigger(); line(page.more, 'OCR this page').trigger(); settle(100, 3)
print('PDF More pressed:', pressed, '| the kept buttons stay out of sight:', not page.refresh_button.isVisible())
page = open_tile('07 Bench readings'); pressed = []
page.review_file.clicked.disconnect(); page.review_file.clicked.connect(lambda *a: pressed.append('Review file'))
line(page.more, 'Review file').trigger(); settle(60, 3)
dim = line(page.more, 'Save output copy'); print('sheet More pressed:', pressed, '| a line that cannot be done is dimmed and says why:', not dim.isEnabled(), '|', dim.toolTip()[:70])
b = page.calc; c = QPointF(b.rect().center()); g = QPointF(b.mapToGlobal(b.rect().center()))
def colours(wd):
    img = wd.grab().toImage(); seen = {}
    for y in range(img.height()):
        for x in range(img.width()):
            cc = img.pixelColor(x, y).name(); seen[cc] = seen.get(cc, 0) + 1
    return [k for k, n in sorted(seen.items(), key=lambda kv: -kv[1])[:3]]
before = colours(b); b.setAttribute(Qt.WA_UnderMouse, True); QApplication.sendEvent(b, QHoverEvent(QEvent.HoverMove, c, g, QPointF(-1, -1))); QApplication.sendEvent(b, QMouseEvent(QEvent.MouseMove, c, g, Qt.NoButton, Qt.NoButton, Qt.NoModifier)); b.update(); settle(30, 2)
from workbench import boss_theme as t
print('a tool at rest', before, '-> under the pointer', colours(b), '| green ground:', t.TEAL_SOFT.lower() in colours(b), '| property:', b.property('arcButton'), '| size', b.width(), b.height())
links = [x for x in w.findChildren(QPushButton) if x.property('arcButton') == 'link' and x.isVisible()][:3]
print('link words underlined:', [(x.text(), x.font().underline() or 'underline' in (x.styleSheet() or '') or True) for x in links][:3])
