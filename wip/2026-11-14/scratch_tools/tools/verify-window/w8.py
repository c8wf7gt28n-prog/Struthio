from winbase import *
from workbench.document_qt import show as show_document
calls = []
real = w.close_tab
def spy(index):
    r = real(index); calls.append((index, r)); return r
w.close_tab = spy
show_document(w); settle(); where('one tab')
v = field(); where('Field over one tab'); print('   focus:', type(app.focusWidget()).__name__, '| window active:', w.isActiveWindow())
QTest.keyClick(v, Qt.Key_W, Qt.ControlModifier); settle(); where('Ctrl+W, one tab under the Field'); print('   close_tab calls:', calls, '| focus:', type(app.focusWidget()).__name__)
# as win2 s5: close last tab under the Field through close_tab, then again
if w._field_active: QTest.keyClick(v, Qt.Key_Escape); settle()
w._close_start(); settle()
calls.clear(); show_document(w); settle(); v = field(); where('Field over one tab (second time)'); print('   focus:', type(app.focusWidget()).__name__, '| active:', w.isActiveWindow(), '| a_close enabled:', w.a_close.isEnabled())
QTest.keyClick(v, Qt.Key_W, Qt.ControlModifier); settle(); where('Ctrl+W again'); print('   close_tab calls:', calls)
w.a_close.trigger(); settle(); where('a_close.trigger()'); print('   close_tab calls:', calls)
finish()
