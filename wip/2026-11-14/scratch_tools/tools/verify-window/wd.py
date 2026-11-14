"""(d) what exactly differs in the window after S / Shift+Enter in the Field and Esc."""
from winbase import *
from PySide6.QtWidgets import QDockWidget, QSplitter
from workbench.document_qt import show as show_document
from workbench.engineering_kernel import operator
from workbench.field_model import Field, FieldObject as O
k = w.ledger_bridge.kernel
def detail():
    out = {'target': w.type_target, 'console size': w.console.size_level, 'console mode': getattr(w.console, 'mode', None), 'console visible': w.console.isVisible(), 'strip text': w.type_bar.box.text()[:30],
           'state': hashlib.sha256(bytes(w.saveState())).hexdigest()[:10], 'title': w.windowTitle(), 'focus': type(app.focusWidget()).__name__ if app.focusWidget() else None}
    for d in w.findChildren(QDockWidget): out['dock ' + (d.objectName() or d.windowTitle())] = (d.isVisible(), d.width(), d.height())
    for i, sp in enumerate(w.findChildren(QSplitter)[:8]): out['split %d %s' % (i, sp.objectName())] = tuple(sp.sizes())
    for name in ('context_bar', 'doc_info', 'workspace_status'): out[name] = getattr(w, name).isVisible()
    return out
def cmp(a, b, tag):
    ch = {key: (a.get(key), b.get(key)) for key in a if a.get(key) != b.get(key)}; print('   %s: %s' % (tag, 'identical' if not ch else ch)); return ch
def pick(v, test):
    ident = next(o.id for o in v.field.objects if test(o)); v.field.select(ident); v._layout(); v._reveal(); v._describe(); v.update(); settle(10, 2); return v.selected()
docs = k.dispatch('documents.list', {}, operator())['result']['documents']; show_document(w, docs[0]['id']); settle(); base = detail(); print('   before:', {key: base[key] for key in ('target', 'console size', 'console mode', 'console visible', 'focus', 'title')})
v = field(); QTest.keyClick(v, Qt.Key_Escape); settle(); cmp(base, detail(), 'Field -> Esc')
v = field(); pick(v, lambda o: o.kind == 'calculation'); QTest.keyClick(v, Qt.Key_S); settle(); QTest.keyClick(app.focusWidget(), Qt.Key_Escape); settle(); w.a_field.trigger(); settle(); QTest.keyClick(v, Qt.Key_Escape); settle()
cmp(base, detail(), 'Field -> S -> Esc (strip) -> F9 -> Esc')
w.type_bar.box.clear(); settle(); cmp(base, detail(), '   ... after the owner clears the strip')
v = field(); v.setFocus(); QTest.keyClick(v, Qt.Key_Return, Qt.ShiftModifier); settle(80, 6); v.setFocus(); QTest.keyClick(v, Qt.Key_Escape); settle(); cmp(base, detail(), 'Field -> Shift+Enter -> Esc')
w.console.set_size(base['console size']); settle(); cmp(base, detail(), '   ... after the working area is closed again')
print('== Home when the selection is already the Home sheet but paged out of view (standalone view)')
from workbench.field_qt import FieldView
objs = [O('s%d' % i, 'finding', 'Finding %d' % i) for i in range(30)]; objs[2] = O('s2', 'finding', 'Needs recheck', state='recheck')
fv = FieldView(); fv.resize(1000, 600); fv.set_field(Field(objs)); fv.show(); fv.setFocus(); app.processEvents(); fv.grab()
print('   first() =', fv.field.selected, '| on screen:', fv._layout().intersects(fv.sheet_rect(fv.field.selected)))
for _ in range(5): QTest.keyClick(fv, Qt.Key_PageDown)
app.processEvents(); print('   PageDown x5: scroll_y %.0f, selected sheet on screen: %s' % (fv.scroll_y, fv._layout().intersects(fv.sheet_rect(fv.field.selected))))
QTest.keyClick(fv, Qt.Key_Home); app.processEvents(); fv.grab(); print('   Home: selected %s, scroll_y %.0f, selected sheet on screen: %s' % (fv.field.selected, fv.scroll_y, fv._layout().intersects(fv.sheet_rect(fv.field.selected))))
QTest.keyClick(fv, Qt.Key_A); app.processEvents(); fv.grab(); print('   A (the only waiting one is already selected): on screen: %s' % fv._layout().intersects(fv.sheet_rect(fv.field.selected)))
QTest.keyClick(fv, Qt.Key_Up); QTest.keyClick(fv, Qt.Key_Down); app.processEvents(); print('   Up, Down: on screen: %s' % fv._layout().intersects(fv.sheet_rect(fv.field.selected)))
finish()
