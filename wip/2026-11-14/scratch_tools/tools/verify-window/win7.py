from winbase import *
from workbench.document_qt import show as show_document
show_document(w); settle(); w.a_files.trigger(); settle(); where('two tabs, Files in front')
v = field(); where('Field')
for name, key, mod in (('Ctrl+Tab', Qt.Key_Tab, Qt.ControlModifier), ('Ctrl+PgDown', Qt.Key_PageDown, Qt.ControlModifier), ('Ctrl+PgUp', Qt.Key_PageUp, Qt.ControlModifier), ('Ctrl+W', Qt.Key_W, Qt.ControlModifier)):
    sel = v.field.selected; QTest.keyClick(v, key, mod); settle(); where('%s while the Field shows' % name); print('   selection moved:', sel != v.field.selected)
    if not w._field_active: v = field()
# clicking a tab of the tab bar is impossible while the Field covers it; but the navigator on the left can open a file:
note = root / 'probe_note.txt'; note.write_text('x\n'); 
w.open_document(note); settle(); where('open_document() while the Field shows')
finish()
