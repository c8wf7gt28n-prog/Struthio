from PySide6.QtGui import QColor
w.a_field.trigger(); settle(); v = w.field_page.view; bar = w.centre_bar; fl = bar.finder
o = next(o for o in v.field.objects if o.title.startswith('Settled draw')); v.field.select(o.id); v._describe(); QTest.keyClick(v, Qt.Key_Return); settle(900, 8)
QTest.mouseClick(bar.find, Qt.LeftButton); settle(150, 2); QTest.keyClicks(fl.line, 'rev b'); settle(400, 3)
m = fl.mark; print('mark:', m is not None, m.geometry() if m else None, '| sheet:', repr(m.styleSheet()) if m else None, '| class', type(m).__name__, '| frameShape', m.frameShape() if m else None)
img = m.grab().toImage(); print('edge pixel:', QColor(img.pixel(0, 3)).name(), QColor(img.pixel(3, 0)).name(), '| inside:', QColor(img.pixel(5, 5)).name())
lab = fl.found[fl.at]; print('label:', type(lab).__name__, lab.objectName(), lab.geometry(), 'focus policy', lab.focusPolicy(), 'has focus', lab.hasFocus())
img2 = w.grab().toImage(); g = m.mapTo(w, m.rect().topLeft()); print('in the window at', g, ':', QColor(img2.pixel(g.x() + 20, g.y())).name(), QColor(img2.pixel(g.x(), g.y() + 5)).name())
