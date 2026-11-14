from winbase import *
from PySide6.QtWidgets import QWidget, QLabel, QAbstractButton
def bars(tag):
    c = w.centralWidget(); out = []
    for child in c.findChildren(QWidget, options=Qt.FindDirectChildrenOnly):
        if child.isVisible():
            words = [x.text() for x in child.findChildren(QLabel) if x.isVisible() and x.text()][:3] + [x.text() for x in child.findChildren(QAbstractButton) if x.isVisible() and x.text()][:3]
            out.append('%s#%s h=%d %s' % (type(child).__name__, child.objectName(), child.height(), words if not isinstance(child, type(w.central_stack)) else ''))
    names = {n: getattr(w, n).isVisible() for n in ('context_bar', 'doc_info', 'workspace_status') if hasattr(w, n)}
    print('   %-40s %s\n      visible rows of the centre: %s' % (tag, names, out))
which = sys.argv[1]
if which == 'work':
    bars('the work, before the Field'); before = snap()
    v = field(); bars('Field opened from the work')
    w.resize(1280, 720); settle(30, 4); bars('Field after resizing to 1280x720')
    w.resize(1920, 1200); settle(30, 4); bars('Field after resizing back')
    QTest.keyClick(v, Qt.Key_Escape); settle(); where('Esc'); bars('after Esc')
if which == 'home':
    w.show_start(); settle(); bars('Home, before the Field'); before = snap()
    v = field(); bars('Field opened from Home'); save('edge_from_home_field.png')
    QTest.keyClick(v, Qt.Key_Escape); settle(); where('Esc'); bars('Home after Esc'); diff(before, snap(), 'Home -> Field -> Esc')
if which == 'tabwork':
    from workbench.document_qt import show as show_document
    show_document(w); settle(); bars('a page open, before the Field'); before = snap(); save('edge_work_before.png')
    v = field(); bars('Field opened over a page'); save('edge_work_field.png')
    QTest.keyClick(v, Qt.Key_Escape); settle(); where('Esc'); bars('after Esc'); diff(before, snap(), 'page -> Field -> Esc')
finish()
