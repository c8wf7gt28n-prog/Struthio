import sys
sys.path.insert(0, sys.argv[1])
from PySide6.QtGui import QGuiApplication, QImage, QPainter, QColor, QFont
from PySide6.QtCore import Qt
app = QGuiApplication([])
from workbench.glyph_set import GLYPHS
names = [n for n in GLYPHS if len(n) > 2]
cols = 10; cell = 96; rows = (len(names) + cols - 1) // cols
im = QImage(cols * cell, rows * cell, QImage.Format_RGB32); im.fill(QColor('#171b3c'))
p = QPainter(im); p.setRenderHint(QPainter.Antialiasing); f = QFont('DejaVu Sans'); f.setPixelSize(12)
for i, n in enumerate(names):
    x, y = (i % cols) * cell, (i // cols) * cell
    p.save(); p.translate(x + 28, y + 10); p.scale(2.0, 2.0); GLYPHS[n](p, QColor('#83eaff'), QColor('#5a8fc4')); p.restore()
    p.setFont(f); p.setPen(QColor('#e3e3ff')); p.drawText(x + 4, y + 76, n)
p.end(); im.save(sys.argv[2]); print(sys.argv[2])
