from winbase import *
where('opened (the work, no tab)')
# -- S1: from the work, with a real tab open, and back
from workbench.document_qt import show as show_document
from workbench.field_source import read_field
from workbench.engineering_kernel import operator
k = w.ledger_bridge.kernel
docs = k.dispatch('documents.list', {}, operator())['result']['documents']
show_document(w, docs[0]['id']); settle(); where('a page is open')
before = snap()
v = field(); where('S1 Field from the work'); during = snap()
QTest.keyClick(v, Qt.Key_Escape); settle(); where('S1 Esc'); after = snap()
diff(before, after, 'work -> Field -> Esc')
print('   during the Field:', {k2: during[k2] for k2 in ('context_bar', 'doc_info', 'workspace_status', 'clip', 'output_dock', 'cart_dock', 'focus') if k2 in during})
# -- S2: from Home and back
w.show_start(); settle(); where('Home'); home_before = snap()
v = field(); where('S2 Field from Home')
QTest.keyClick(v, Qt.Key_Escape); settle(); where('S2 Esc'); home_after = snap()
diff(home_before, home_after, 'Home -> Field -> Esc')
# -- S3: Field twice from Home, then Esc
w.show_start(); settle(); v = field(); w.a_field.trigger(); settle(); where('S3 Field opened twice from Home')
print('   _field_from_home after the second F9:', w._field_from_home)
QTest.keyClick(v, Qt.Key_Escape); settle(); where('S3 Esc (came from Home)')
# -- S3b: Field from Home with NO tabs: twice then Esc
# -- S4: rooms while the Field is in front
for name in ('a_files', 'a_agenda', 'a_library', 'a_project_desk', 'a_changes', 'a_continuing', 'a_deployment', 'a_slate_panel', 'a_cabinet', 'a_console'):
    act = getattr(w, name, None)
    if act is None: print('   (no action %s)' % name); continue
    v = field(); n = len(errors)
    act.trigger(); settle(); where('S4 %s (%s) while the Field shows' % (name, act.text().replace('&', '')))
    if w._field_active: QTest.keyClick(v, Qt.Key_Escape); settle()
from workbench import document_qt
v = field(); document_qt.show(w); settle(); where('S4 Documents room (document_qt.show)')
v = field(); w.show_start(); settle(); where('S4 Home action while the Field shows')
w._close_start(); settle()
finish()
