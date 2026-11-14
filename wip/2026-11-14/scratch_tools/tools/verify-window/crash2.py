import os, sys
os.environ.update(QT_QPA_PLATFORM='offscreen', PYTHONDONTWRITEBYTECODE='1'); sys.path.insert(0, '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/wt'); sys.dont_write_bytecode = True
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt
app = QApplication([])
from workbench import field_qt
from workbench.field_qt import FieldView
from workbench.field_model import Field, FieldObject as O, FieldLink as L
name = sys.argv[1]; raised = []
def boom(self, *a, **kw):
    raised.append(1); raise RuntimeError('probe: %s failed' % name)
setattr(FieldView, name, boom)
said = []
real = field_qt.QPainter.drawText
v = FieldView(); v.resize(900, 600); v.faces = (('work', 'w'), ('network', 'n')); v.face = 'work'
v.set_field(Field([O('a', 'source', 'A'), O('b', 'sheet', 'B', state='recheck'), O('c', 'question', 'C', state='open')], [L('a', 'b', 'page 1', True), L('b', 'c')]) if name != '_empty' else Field())
v.show()
for _ in range(4): app.processEvents(); QTest.qWait(20)
for key in (Qt.Key_Left, Qt.Key_A, Qt.Key_PageDown):
    try: QTest.keyClick(v, key)
    except Exception: pass
for _ in range(3): app.processEvents(); QTest.qWait(20)
img = v.grab().toImage(); amber = sum(1 for x in range(28, 600, 2) for y in range(v.head_height() + 14, v.head_height() + 50, 2) if img.pixelColor(x, y).red() > 180 and img.pixelColor(x, y).blue() < 140)
print('%-12s raised %d times; still alive after normal paints and keys; amber message pixels under the head: %d' % (name, len(raised), amber), flush=True)
