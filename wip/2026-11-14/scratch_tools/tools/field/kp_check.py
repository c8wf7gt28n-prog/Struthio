b = w.shell2.top.programs
from PySide6.QtGui import QIcon
ic = b.icon(); pm = ic.pixmap(64, 64)
print('sizes', ic.availableSizes(), '| name', repr(ic.name()), '| pm', pm.size(), pm.devicePixelRatio(), '| iconSize', b.iconSize())
im = pm.toImage(); print([im.pixelColor(x, im.height() // 2).name() for x in range(0, im.width(), max(1, im.width() // 8))])
import workbench.kasandra_art as ka; p = ka.folder(w.root) / 'kp_monogram.png'; print('path', p, p.exists())
