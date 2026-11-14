from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItemIterator
from PySide6.QtCore import QRect
w.a_field.trigger(); settle(); settle(200, 3)
trees = [t for t in w.findChildren(QTreeWidget) if t.isVisible() and t.width() > 100]; print('visible trees:', [(type(t).__name__, t.objectName(), t.topLevelItemCount()) for t in trees])
tree = trees[0]; it = QTreeWidgetItemIterator(tree); deep = None
while it.value() is not None:
    item = it.value()
    if item.text(0) == 'Questions': deep = item
    it += 1
tree.setCurrentItem(deep); tree.setFocus(); settle(200, 3); print('current row:', deep.text(0), '<-', deep.parent().text(0) if deep.parent() else None)
pane = tree.window().grab(QRect(0, 60, 276, 500)); pane.save(str(OUT / ('Tree_lit_%s.png' % tag))); big = pane.scaled(pane.width() * 2, pane.height() * 2); big.save(str(OUT / ('Tree_lit_x2_%s.png' % tag))); print('saved tree pictures')
