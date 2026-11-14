import sys
from PySide6.QtGui import QImage
src, out, x, y, w, h = sys.argv[1], sys.argv[2], *map(int, sys.argv[3:7])
img = QImage(src); img.copy(x, y, w, h).save(out); print(out, img.width(), img.height())
