"""W6 keys in the real window; (c) the menus; S then Esc."""
from winbase import *
from PySide6.QtGui import QContextMenuEvent, QGuiApplication
from workbench import context_menu, field_page
from workbench.field_model import Field, FieldObject as O, FieldLink as Ln
from workbench.document_qt import show as show_document
from workbench.engineering_kernel import operator
k = w.ledger_bridge.kernel
def kb():
    a = app.focusWidget(); return '%s%s' % (type(a).__name__ if a else None, '' if a is None else ':' + (a.objectName() or a.accessibleName() or '')[:30])
def pick(v, test):
    ident = next(o.id for o in v.field.objects if test(o)); v.field.select(ident); v._layout(); v._reveal(); v._describe(); v.update(); settle(10, 2); return v.selected()
docs = k.dispatch('documents.list', {}, operator())['result']['documents']
show_document(w, docs[0]['id']); settle()
v = field(); where('Field over a page')
print('== W6 Tab / Shift+Tab with something waiting:', sum(o.needs_attention() for o in v.field.objects), 'waiting | keyboard:', kb())
sel = v.field.selected; seq = []
for _ in range(3):
    QTest.keyClick(app.focusWidget() or w, Qt.Key_Tab); settle(10, 1); seq.append(kb())
print('   Tab x3 -> keyboard goes to:', seq, '| selection moved:', v.field.selected != sel, '| Field in front:', w._field_active)
QTest.keyClick(app.focusWidget() or w, Qt.Key_F9); settle(); print('   F9 from there -> keyboard:', kb(), '| Field in front:', w._field_active)
seq = []
for _ in range(3):
    QTest.keyClick(app.focusWidget() or w, Qt.Key_Backtab, Qt.ShiftModifier); settle(10, 1); seq.append(kb())
print('   Shift+Tab x3 -> keyboard goes to:', seq, '| selection moved:', v.field.selected != sel, '| Field in front:', w._field_active)
fw = app.focusWidget(); QTest.keyClick(fw or w, Qt.Key_Escape); settle(); where('   Esc with the keyboard outside the Field'); print('      keyboard:', kb())
if not w._field_active: v = field()
v.setFocus(); settle(10, 1)
real_field = v.field
objs = [O('s%d' % i, 'source', 'Source %d' % i) for i in range(9)] + [O('t1', 'sheet', 'Sheet one', state='recheck'), O('t2', 'sheet', 'Sheet two'), O('c1', 'calculation', 'Calc', state='held'),
        O('f1', 'finding', 'Finding', state='current'), O('q1', 'question', 'Why?', state='open'), O('j1', 'job', 'A job', state='failed')]
v.set_field(Field(objs, [Ln('s0', 't1'), Ln('s8', 't2'), Ln('t1', 'c1', '', True), Ln('c1', 'f1'), Ln('f1', 'q1')])); settle(10, 2)
seq = [v.field.selected]; vis = []
for _ in range(5):
    QTest.keyClick(v, Qt.Key_A); settle(5, 1); seq.append(v.field.selected); vis.append(v._layout().contains(v.sheet_rect(v.field.selected)))
print('   A x5 (waiting: t1 recheck, c1 held, q1 open, j1 failed):', seq, '| each wholly on screen:', vis, '| keyboard:', kb())
seq = [v.field.selected]
for _ in range(4):
    QTest.keyClick(v, Qt.Key_A, Qt.ShiftModifier); settle(5, 1); seq.append(v.field.selected)
print('   Shift+A x4:', seq)
y = []; 
for key, name in ((Qt.Key_Home, 'Home'), (Qt.Key_PageDown, 'PageDown'), (Qt.Key_PageDown, 'PageDown'), (Qt.Key_PageUp, 'PageUp'), (Qt.Key_End, 'End'), (Qt.Key_Home, 'Home')):
    QTest.keyClick(v, key); settle(5, 1); y.append('%s -> selected %s scroll_y %.0f' % (name, v.field.selected, v.scroll_y))
print('   ' + ' | '.join(y), '| surface', v._surface, 'body', v.body().height())
v.set_field(real_field); settle(10, 2)
print('== (c) menus')
o = pick(v, lambda o: o.kind == 'calculation' and 'Startup' in o.title)
QTest.keyClick(v, Qt.Key_Menu); settle(60, 4); menu = getattr(w, 'context_menu', None)
print('   Menu key on %r -> menu for %r (%s) | rows: %s | menu visible: %s' % (o.title, getattr(menu.target, 'label', None), getattr(menu.target, 'noun', None), menu.words(), menu.isVisible()))
gp = menu.mapToGlobal(QPoint(0, 0)); sr = v.sheet_rect(v.field.selected); print('   it opens at', v.mapFromGlobal(gp).x(), v.mapFromGlobal(gp).y(), 'in the view; selected sheet at %.0f,%.0f' % (sr.left(), sr.top()))
menu.close_menu() if hasattr(menu, 'close_menu') else menu.close(); settle(20, 2); print('   after closing the menu: keyboard', kb(), '| Field in front', w._field_active)
other = next(i for i in v._placed if i != v.field.selected and v._layout().contains(v.sheet_rect(i)) and v.field.get(i).kind == 'finding'); pt = v.sheet_rect(other).center().toPoint()
QTest.mouseClick(v, Qt.RightButton, Qt.NoModifier, pt); app.sendEvent(v, QContextMenuEvent(QContextMenuEvent.Mouse, pt, v.mapToGlobal(pt))); settle(60, 4); menu = w.context_menu
print('   right-click on another sheet -> it became the selected one: %s | menu for %r | rows: %s' % (v.field.selected == other, menu.target.label[:40], menu.words()))
want = ['Open', 'What feeds it', 'What it feeds', 'Inspect in the line', 'Run its staC', 'Ask Graphite about this', 'Copy its name']
print('   has all seven rows:', all(any(wd == x for wd in menu.words()) for x in want), '| missing:', [x for x in want if x not in menu.words()], '| extra:', [x for x in menu.words() if x not in want and x != '—'])
ents = {e.key: e for e in menu.entries}; menu.close_menu() if hasattr(menu, 'close_menu') else menu.close(); settle(20, 2)
obj = v.selected()
rows = ents['field:fed'].submenu() if ents['field:fed'].enabled else []; print('   What feeds it:', [r.label for r in rows], '| What it feeds enabled:', ents['field:feeds'].enabled, ents['field:feeds'].reason if not ents['field:feeds'].enabled else [r.label for r in ents['field:feeds'].submenu()])
if rows: rows[0].run(); settle(20, 2); print('      choosing the first -> selected %r, wholly on screen %s, Field in front %s, keyboard %s' % (v.selected().title, v._layout().contains(v.sheet_rect(v.field.selected)), w._field_active, kb()))
v.field.select(obj.id); v._describe()
ents['field:copy'].run(); settle(10, 1); print('   Copy its name -> clipboard == title:', QGuiApplication.clipboard().text() == obj.title, '| Field in front:', w._field_active)
ents['field:inspect'].run(); settle(); print('   Inspect in the line -> strip == obj.stac:', w.type_bar.box.text() == obj.stac, '| Field in front:', w._field_active, '| keyboard:', kb())
w.type_bar.box.clear(); v.setFocus(); settle(10, 1)
ents['field:run'].run(); settle(80, 6); print('   Run its staC -> last_program == obj.stac:', w.console.last_program == obj.stac, '| Field in front:', w._field_active, '| keyboard:', kb())
ents['field:ask'].run(); settle(); where('   Ask Graphite about this'); print('      strip:', repr(w.type_bar.box.text()), '| keyboard:', kb())
w.type_bar.box.clear(); v = field(); print('   back in the Field, selection kept:', v.selected().id == obj.id)
ents['field:open'].run(); settle(); where('   Open'); 
for face in ('work', 'network'):
    v = field()
    if v.face != face: QTest.keyClick(v, Qt.Key_N if face == 'network' else Qt.Key_W); settle(60, 4)
    body = v._layout(); spot = next((QPoint(x, y) for y in range(int(body.top()) + 30, int(body.bottom()) - 30, 9) for x in range(int(body.left()) + 4, int(body.right()) - 4, 9) if v._hit(QPointF(x, y)) is None), None)
    sel0 = v.field.selected
    app.sendEvent(v, QContextMenuEvent(QContextMenuEvent.Mouse, spot, v.mapToGlobal(spot))); settle(60, 4); menu = w.context_menu
    print('   empty place of the %s face at %s -> menu for %r (%s) | rows: %s | selection unchanged: %s' % (face, (spot.x(), spot.y()), menu.target.label, menu.target.noun, menu.words(), v.field.selected == sel0))
    ents = {e.key: e for e in menu.entries}; menu.close_menu() if hasattr(menu, 'close_menu') else menu.close(); settle(20, 2)
    sub = ents['field:stac'].submenu(); print('      This face in staC:', [(r.label, r.tip) for r in sub])
    sub[0].run(); settle(); print('      first line -> strip %r | Field in front %s' % (w.type_bar.box.text(), w._field_active)); w.type_bar.box.clear(); v.setFocus()
    seen = []; real = Kernel.dispatch
    def counting(self, operation, arguments=None, principal=None, *a, **kw):
        seen.append(operation); return real(self, operation, arguments, principal, *a, **kw)
    with patch.object(Kernel, 'dispatch', counting): ents['field:again'].run(); settle()
    print('      Look again -> Kernel reads:', len(seen), '| Field in front:', w._field_active)
    for key in ents:
        if key.startswith('field:face:'): ents[key].run(); settle(60, 4); print('      %s -> face now %s' % (ents[key].label, v.face))
    v = w.field_page.view
    if face == 'network':
        ents['field:back'].run(); settle(); where('      Back')
v = field()
if v.face != 'work': QTest.keyClick(v, Qt.Key_W); settle()
print('== S, then Esc in the writing strip')
o = pick(v, lambda o: o.kind == 'calculation' and 'Startup' in o.title); v.setFocus(); settle(10, 1)
QTest.keyClick(v, Qt.Key_S); settle(); print('   S -> keyboard:', kb(), '| Field in front:', w._field_active)
QTest.keyClick(app.focusWidget(), Qt.Key_Escape); settle(); print('   Esc -> keyboard:', kb(), '| window focus widget:', type(w.focusWidget()).__name__ if w.focusWidget() else None, '| Field in front:', w._field_active, '| strip still holds the line:', bool(w.type_bar.box.text()))
sel = v.field.selected
for key, name in ((Qt.Key_Left, 'Left'), (Qt.Key_Down, 'Down'), (Qt.Key_Return, 'Enter'), (Qt.Key_Escape, 'Esc')):
    QTest.keyClick(app.focusWidget() or w, key); settle(10, 2); print('      then %-5s -> selection moved %s | Field in front %s | keyboard %s' % (name, v.field.selected != sel, w._field_active, kb()))
QTest.keyClick(app.focusWidget() or w, Qt.Key_Tab); settle(10, 2); print('      then Tab   -> keyboard', kb())
QTest.keyClick(app.focusWidget() or w, Qt.Key_F9); settle(10, 2); print('      then F9    -> keyboard', kb(), '| Field in front', w._field_active)
finish()
