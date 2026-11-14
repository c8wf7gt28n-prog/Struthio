"""montage.py OUT COLUMNS WIDTH files...: a contact sheet with each picture's name under it."""
import sys
from PySide6.QtGui import QGuiApplication, QImage, QPainter, QColor, QFont
from PySide6.QtCore import Qt, QRect
app = QGuiApplication([])
out, cols, width = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]); files = sys.argv[4:]
imgs = [QImage(f) for f in files]; h = max(round(i.height() * width / i.width()) for i in imgs if not i.isNull()); cell = h + 22
rows = (len(files) + cols - 1) // cols
sheet = QImage(cols * (width + 8), rows * cell, QImage.Format_RGB32); sheet.fill(QColor('#222222'))
p = QPainter(sheet); p.setRenderHint(QPainter.SmoothPixmapTransform); f = QFont('DejaVu Sans'); f.setPixelSize(13); p.setFont(f); p.setPen(QColor('#eeeeee'))
for n, (name, im) in enumerate(zip(files, imgs)):
    x, y = (n % cols) * (width + 8), (n // cols) * cell
    p.drawImage(QRect(x, y, width, round(im.height() * width / im.width())), im)
    p.drawText(x + 2, y + h + 16, name.split('/')[-1][:70])
p.end(); sheet.save(out); print(out, sheet.size())
