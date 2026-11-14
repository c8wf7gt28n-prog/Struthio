import os, sys
os.environ.update(QT_QPA_PLATFORM='offscreen', PYTHONDONTWRITEBYTECODE='1'); sys.path.insert(0, '/home/user/Struthio'); sys.dont_write_bytecode = True
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
app = QApplication([])
from workbench.field_qt import FieldView
from workbench.field_model import Field, FieldObject as O
v = FieldView(); v.resize(800, 500)
v.set_field(Field([O('a', sys.argv[1], 'A thing of a kind the titles table does not list')]))
v.show(); print('shown; processing events (a normal paint, no grab)', flush=True)
for _ in range(5): app.processEvents(); QTest.qWait(30)
print('still alive after painting', flush=True)
