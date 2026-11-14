# the head: the familiar menus in the open, the name of what is open after them, Programs and System at the right
from PySide6.QtWidgets import QToolButton, QApplication
from PySide6.QtCore import QTimer
top = w.shell2.top; settle(200, 3)
words = [(b.text(), b.isVisible(), b.geometry().x(), b.width(), len([a for a in b.menu().actions() if not a.isSeparator()]) if b.menu() else 0) for b in top.bar_menus]
print('menus in the open:', [(t, v, x, wd, n) for t, v, x, wd, n in words]); print('fold button:', repr(top.more_menus.text()), 'shown', top.more_menus.isVisible(), '| name line at x', top.path.geometry().x(), 'wide', top.path.width())
w.a_field.trigger(); settle(); save('Head_00_Field_%s.png' % tag)
v = w.field_page.view; o = next(o for o in v.field.objects if o.title.startswith('07_Bench')); v.field.select(o.id); v._describe(); QTest.keyClick(v, Qt.Key_Return); settle(900, 8)
save('Head_01_Page_%s.png' % tag)
def shot(name):
    def go():
        m = QApplication.activePopupWidget()
        if m is None: print(name, 'no menu came up'); return
        try: print(name, 'menu up with', len([a for a in m.actions() if not a.isSeparator()]), 'lines, first:', [a.text().replace('&', '') for a in m.actions() if not a.isSeparator()][:4]); m.grab().save(str(OUT / ('Head_%s_%s.png' % (name, tag))))
        finally: m.close()
    return go
for n, b in enumerate([b for b in top.bar_menus if b.isVisible()][:4]):
    QTimer.singleShot(600, shot('02_Menu_%d_%s' % (n, b.text()))); QTest.mouseClick(b, Qt.LeftButton); settle(300, 3)
work = next(b for b in w.findChildren(QToolButton) if b.objectName() == 'MoreMenus').menu(); work.aboutToShow.emit(); print('the fold button still lists every menu:', [a.text().replace('&', '') for a in work.actions()])
w.resize(1000, 700); settle(300, 4); print('at 1000 wide: shown', [b.text() for b in top.bar_menus if b.isVisible()], '| fold shown', top.more_menus.isVisible(), repr(top.more_menus.text()), '| name wide', top.path.width()); save('Head_03_Narrow_%s.png' % tag)
