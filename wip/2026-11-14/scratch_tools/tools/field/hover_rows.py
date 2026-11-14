# does a row of a tree / list and a tab answer in green under the pointer?
from PySide6.QtWidgets import QTreeWidget, QTreeView, QListWidget, QListView, QTabBar, QApplication, QAbstractItemView, QScrollBar
from PySide6.QtGui import QMouseEvent, QHoverEvent
from PySide6.QtCore import QPointF, QEvent, QPoint
from workbench import boss_theme as t
GREENS = {t.TEAL_SOFT.lower(): 'TEAL_SOFT', t.TEAL_TEXT.lower(): 'TEAL_TEXT', t.TEAL_EDGE.lower(): 'TEAL_EDGE', t.READY.lower(): 'READY'}
def greens(pix):
    img = pix.toImage(); seen = {}
    for y in range(img.height()):
        for x in range(img.width()):
            c = img.pixelColor(x, y).name()
            if c in GREENS: seen[GREENS[c]] = seen.get(GREENS[c], 0) + 1
    return seen
def move(wd, pos):
    g = QPointF(wd.mapToGlobal(pos)); wd.setAttribute(Qt.WA_UnderMouse, True)
    QApplication.sendEvent(wd, QHoverEvent(QEvent.HoverMove, QPointF(pos), g, QPointF(-1, -1))); QApplication.sendEvent(wd, QMouseEvent(QEvent.MouseMove, QPointF(pos), g, Qt.NoButton, Qt.NoButton, Qt.NoModifier)); wd.update(); settle(30, 3)
w.a_field.trigger(); settle()
for view in [x for x in w.findChildren(QAbstractItemView) if x.isVisible() and x.model() is not None and x.model().rowCount() >= 1][:6]:
    top = view.model().index(0, 0); idx = view.model().index(1, 0) if view.model().rowCount() > 1 else (view.model().index(1, 0, top) if view.model().rowCount(top) > 1 else top); r = view.visualRect(idx)
    if not r.isValid() or r.isEmpty(): continue
    before = greens(view.viewport().grab(r)); move(view.viewport(), r.center()); after = greens(view.viewport().grab(r))
    print('rows of', type(view).__name__, repr(view.objectName()), '| own sheet:', bool(view.styleSheet()), '| before', before, '-> under the pointer', after)
v = w.field_page.view
for title in ('07 Bench readings', '07 Case conclusion'):
    o = next((o for o in v.field.objects if o.title.startswith(title)), None)
    if o is not None:
        w.a_field.trigger(); settle(); v.field.select(o.id); v._describe(); QTest.keyClick(v, Qt.Key_Return); settle(200, 6)
print('tab bars:', [(b.objectName(), b.count(), b.isVisible()) for b in w.findChildren(QTabBar)])
for bar in [b for b in w.findChildren(QTabBar) if b.isVisible() and b.count() > 1][:3]:
    other = next(i for i in range(bar.count()) if i != bar.currentIndex()); r = bar.tabRect(other)
    before = greens(bar.grab(r)); move(bar, r.center()); after = greens(bar.grab(r))
    print('tab', repr(bar.tabText(other)), 'of', repr(bar.objectName()), '| before', before, '-> under the pointer', after)
