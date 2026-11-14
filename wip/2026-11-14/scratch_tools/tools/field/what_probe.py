from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication
settle(600, 3); align()
for x, y in ((1012, 688), (1045, 688), (1100, 740), (1175, 740)):
    c = w.childAt(QPoint(x, y)); chain = []
    while c is not None and len(chain) < 5: chain.append('%s#%s%s' % (type(c).__name__, c.objectName(), (' "%s"' % c.toolTip()[:60]) if c.toolTip() else '')); c = c.parentWidget()
    print((x, y), ' < '.join(chain))
con = w.console; print('console sizes:', {k: (b.text(), b.isVisible()) for k, b in con.sizes.items()}, '| level', con.size_level, '| modes', getattr(con, 'mode', None))
print('size actions:', [(k, a.text(), a.shortcut().toString()) for k, a in w.a_sizes.items()])
print('DONE')
