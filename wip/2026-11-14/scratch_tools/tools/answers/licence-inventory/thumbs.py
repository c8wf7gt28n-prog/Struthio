import sys, os
from PySide6.QtGui import QImage, QPainter, QColor, QGuiApplication, QFont
from PySide6.QtCore import Qt, QRect
app = QGuiApplication([])
out = sys.argv[1]; files = sys.argv[2:]
cols = 10; cell = 150; rows = (len(files)+cols-1)//cols
sheet = QImage(cols*cell, rows*(cell+24), QImage.Format_RGB32); sheet.fill(QColor(60,60,60))
p = QPainter(sheet); p.setPen(QColor(255,255,255)); p.setFont(QFont("DejaVu Sans", 9))
for i,f in enumerate(files):
    im = QImage(f)
    x = (i%cols)*cell; y = (i//cols)*(cell+24)
    if im.isNull():
        p.drawText(QRect(x,y,cell,cell), Qt.AlignCenter, "NULL "+os.path.basename(f)); continue
    t = im.scaled(cell-8, cell-8, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    p.drawImage(x+4, y+4, t)
    p.drawText(QRect(x,y+cell,cell,24), Qt.AlignCenter, f"{os.path.basename(f)} {im.width()}x{im.height()}")
p.end(); sheet.save(out); print(out, sheet.width(), sheet.height())
