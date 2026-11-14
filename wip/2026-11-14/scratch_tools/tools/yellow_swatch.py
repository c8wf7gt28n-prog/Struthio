"""A Kasandra menu with a candidate highlight: python -B yellow_swatch.py <tree> <out.png> <soft> <edge> <text> <title>."""
import os, sys
tree, out, soft, edge, text, title = sys.argv[1:7]
sys.path.insert(0, tree); os.environ['GRAPHITE_APPEARANCE'] = 'kasandra'; os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from workbench import boss_theme as bt
for k, v in (('AMBER', soft), ('AMBER_SOFT', soft), ('AMBER_EDGE', edge), ('AMBER_TEXT', text)):
    bt.PALETTES['kasandra'][k] = v; setattr(bt, k, v)
from PySide6.QtWidgets import QApplication, QMenu, QWidget, QVBoxLayout, QLabel, QListWidget
from PySide6.QtGui import QPainter, QImage, QColor, QFont
from PySide6.QtCore import QPoint, Qt
app = QApplication([])
from workbench import shell2
try:shell2.load_fonts(__import__('pathlib').Path(tree))
except Exception as e:print('fonts', e)
from workbench.theme2 import QSS2
ink = sys.argv[7] if len(sys.argv) > 7 else None
qss = QSS2.replace('#83eaff', edge).replace('#b9f4ff', text).replace('#1d3d63', soft)
if ink:qss += '\nQMenu::item:selected, QListView::item:selected, QListWidget::item:selected {color:%s;}\n' % ink
app.setStyleSheet(qss)
host = QWidget(); host.resize(760, 420); host.setStyleSheet('background:%s;' % bt.GROUND); host.show()
menu = QMenu(host)
for w in ('Open', 'Ask Kasandra about it', 'Rename…', 'DELETE', 'Then ›', 'More ›'):menu.addAction(w)
menu.popup(host.mapToGlobal(QPoint(30, 60))); app.processEvents(); menu.setActiveAction(menu.actions()[1]); app.processEvents()
lst = QListWidget(host); lst.setGeometry(330, 60, 400, 150)
for w in ('Ask Kasandra · @files:07 Bench readings.csv', 'Keep as a note in Notes', '07 Bench readings.csv'):lst.addItem(w)
lst.setCurrentRow(0); lst.show()
lab = QLabel(title, host); lab.setGeometry(30, 14, 700, 30); lab.setStyleSheet('color:%s;background:transparent;font-family:"%s";font-size:20px;' % (bt.TEXT, bt.FACE)); lab.show()
for _ in range(5):app.processEvents()
img = host.grab().toImage(); p = QPainter(img); p.drawImage(menu.mapToGlobal(QPoint(0, 0)) - host.mapToGlobal(QPoint(0, 0)), menu.grab().toImage()); p.end()
img.save(out); print('saved', out)
