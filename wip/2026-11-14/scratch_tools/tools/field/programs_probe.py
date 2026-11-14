from PySide6.QtWidgets import QLabel
k = w.ledger_bridge.kernel; p = operator()
w.a_field.trigger(); settle(); v = w.field_page.view
print('faces:', v.faces)
QTest.keyClick(v, Qt.Key_P); settle(30, 4); align()
f = v.field; print('face:', v.face, '| objects:', len(f.objects), '| compact:', f.compact, '| heads:', f.heads, '| problem:', repr(v.problem))
for rank in f.ranks(): print('   %-7s' % f.rank_title(rank), [f.get(i).title for i in f.column(rank)])
body = v._layout(); print('view %dx%d | body %dx%d | surface %dx%d | sheet %dx%d | rail %d | scroll room: sideways %d, down %d' % (v.width(), v.height(), body.width(), body.height(), v._surface[0], v._surface[1], next(iter(v._placed.values())).w, v.sheet_height(), v.rail(), max(0, v._surface[0] - body.width()), max(0, v._surface[1] - body.height())))
print('selected:', v.selected().title if v.selected() else None, '| states:', sorted({o.state for o in f.objects}))
print('drawn without trouble:', not getattr(v, 'trouble', None), '| census:', f.census()); save('Graphite_Field_12_Programs_%s.png' % tag)
# walk: right, down; staC line; run it
for key in (Qt.Key_Right, Qt.Key_Right, Qt.Key_Down): QTest.keyClick(v, key); settle(5, 2)
sel = v.selected(); print('after Right Right Down:', sel.title, '|', sel.stac)
r = k.dispatch('language.run', {'text': sel.stac}, p); print('its staC answers:', r['ok'], (r['result'].get('rows') if r['ok'] else r['error']))
# Enter opens the room; the Field steps aside; coming back marks it in use
QTest.keyClick(v, Qt.Key_Return); settle(60, 5); tab = w.tabs.currentWidget(); where('Enter on ' + sel.title)
print('   opened:', type(tab).__name__ if tab else None)
save('Graphite_Field_13_Program_Room_%s.png' % tag)
w.a_field.trigger(); settle(30, 3); print('back in the Field: face', v.face, '| selected', v.selected().title, '| its state now:', repr(v.selected().state))
# a native program's room, and what its sheet says
fc = next(o for o in v.field.objects if o.id == 'app:freecad'); v.field.select(fc.id); v.update(); settle(5, 2)
print('FreeCAD sheet:', fc.title, '|', fc.role, '|', fc.where)
QTest.keyClick(v, Qt.Key_Return); settle(60, 5); where('Enter on FreeCAD'); print('   opened:', type(w.tabs.currentWidget()).__name__)
w.a_field.trigger(); settle(30, 3); QTest.keyClick(v, Qt.Key_W); settle(30, 3); print('W ->', v.face, len(v.field.objects), 'objects | compact:', v.field.compact)
QTest.keyClick(v, Qt.Key_P); settle(30, 3)
# ask Stacy about a program with no model
obj = next(o for o in v.field.objects if o.id == 'app:office'); v.field.select(obj.id); v.update(); settle(5, 2)
face = w.shell2.face; w.shell2.ask('what can this do?'); settle(80, 5)
card = [face.lines.itemAt(i).widget() for i in range(face.lines.count()) if face.lines.itemAt(i).widget() is not None][-1]
print('asked Stacy about Office (no model): staC card:', getattr(card, 'stac', None) == obj.stac, '| answered:', getattr(card, 'answered', None))
for l in card.findChildren(QLabel)[:3]: print('   |', l.text().replace('​', '')[:300].replace('\n', ' / '))
save('Graphite_Field_14_Ask_About_A_Program_%s.png' % tag)
