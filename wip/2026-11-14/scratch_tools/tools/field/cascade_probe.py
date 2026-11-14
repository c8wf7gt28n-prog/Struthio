# the right-click cascade on the Field: What if, Doubt it, Trace it, What can be done, Your words
from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QPainter
from PySide6.QtCore import QPoint
from workbench import context_menu
k = w.ledger_bridge.kernel; p = operator(); face = w.shell2.face
def cards(): return [face.lines.itemAt(i).widget() for i in range(face.lines.count()) if face.lines.itemAt(i).widget() is not None]
def said(card, n=4): return [l.text().replace('​', '')[:500].replace('\n', ' / ') for l in card.findChildren(QLabel)][:n]
w.a_field.trigger(); settle(); v = w.field_page.view; page = w.field_page
w.activateWindow(); QTest.qWaitForWindowActive(w, 1500); v.setFocus(); settle(10, 2)
def pick(words):
    o = next(o for o in v.field.objects if words in o.title); v.field.select(o.id); v._reveal(); v._describe(); v.update(); settle(5, 2); return o
def entries(): return context_menu.entries_for(w, context_menu.target_at(w, v, v.selected_point()))
def entry(key): return next(e for e in entries() if e.key == key)
k.dispatch('words.keep', {'name': 'inputs', 'line': 'this | pick document.derivation.inputs | select symbol,value,unit'}, p)
k.dispatch('words.keep', {'name': 'waits', 'line': 'field.read | pick waiting | select kind,title,state'}, p)
# -- a sheet
sheet = pick('07 Limits Rev B')
es = entries(); print('SHEET menu:', [(e.key, e.label, bool(e.submenu)) for e in es if e.key.startswith(('field:', 'words'))])
cells = entry('field:whatif').submenu(); print('What if >', [e.label for e in cells])
tries = next(e for e in cells if e.key == 'field:whatif:B4').submenu(); print('   B4 >', [e.label for e in tries])
tries[0].run(); settle(150, 5); print('   chose %r -> marks: %s | said: %s' % (tries[0].label, sorted(v.would.values())[:3], said(cards()[-1], 1)[0][:90]))
r = k.dispatch('office.get', {'id': sheet.target['id']}, p)['result']; print('   the sheet still says B4 =', r['document']['sheets'][0]['cells']['B4']['value'])
tries[-1].run(); settle(30, 3); print('   Another value… -> line: %r' % w.type_bar.box.text()); w.type_bar.box.clear(); v.setFocus(); QTest.keyClick(v, Qt.Key_Escape); settle(10, 2)
# -- a finding: Doubt it, Trace it, What can be done
f = pick('The reviewed sheet keeps')
rows = entry('field:doubt').submenu(); print('Doubt it >', [(e.label, e.enabled) for e in rows])
weak = next(e for e in rows if 'can fail' in e.label); print('   tooltip:', weak.tip[:150].replace('\n', ' / ')); weak.run(); settle(120, 5); print('   chose it -> Talk:', ' || '.join(said(cards()[-1], 3))[:300])
rows = entry('field:trace').submenu(); print('Trace it >', [(e.label, e.caption) for e in rows])
rows[1].run(); settle(20, 2); print('   chose %r -> selected: %s | Field in front: %s' % (rows[1].label, v.selected().title, w._field_active))
f = pick('The reviewed sheet keeps'); steps = entry('field:do').submenu(); print('What can be done >', [(e.label, e.caption) for e in steps])
read = next(e for e in steps if e.label.startswith('See why')); read.run(); settle(120, 5); print('   a read ran -> Talk:', said(cards()[-1], 1)[0][:90])
write = next(e for e in steps if e.caption == 'asks' and 'check that can fail' in e.label); n0 = len(k.dispatch('investigation.sheet', {'id': f.target['id']}, p)['result']['checked'])
write.run(); settle(150, 5); n1 = len(k.dispatch('investigation.sheet', {'id': f.target['id']}, p)['result']['checked'])
print('   a change was put up, not run: checks %d -> %d | go offered: %r | Talk: %s' % (n0, n1, v.go, said(cards()[-1], 1)[0][:100]))
QTest.keyClick(v, Qt.Key_Escape); settle(10, 2)
# -- your words on a calculation (a word that starts with `this`)
calc = pick('07 Settled power'); ws = entry('field:words').submenu(); print('Your words (on a calculation) >', [e.label for e in ws])
next(e for e in ws if e.label == 'inputs').run(); settle(120, 5); print('   inputs ->', ' || '.join(said(cards()[-1], 3))[:260])
# -- the Field's own menu
t2 = context_menu.target_at(w, v, QPoint(6, v.height() // 2)); own = context_menu.entries_for(w, t2); print('FIELD menu:', [e.label for e in own if e.key.startswith(('field:', 'words'))])
ws = next(e for e in own if e.key == 'field:words').submenu(); print('Your words >', [e.label for e in ws]); print('   waits >', [e.label for e in ws[1].submenu()] if ws[1].submenu else ws[1].label)
# -- the cascade as the owner sees it: the menu, What if, a number, the values
w.type_bar.box.clear(); pp = getattr(w.type_bar.box, 'popup', None); pp.hide() if pp is not None else None
sheet = pick('07 Limits Rev B'); v.setFocus(); settle(30, 3)
menu = context_menu.open_at_focus(w); settle(80, 6)
# 0.8.1: What if is under More (Look into it); deeper screens replace More's rows in place, under Back
print('first level:', menu.first_keys())
child = menu.open_child(menu.row('more'), keyboard=True); settle(80, 6)
child.drill(child.row('field:whatif').entry); settle(80, 6); print('What if >', [e.key for e in child.screen][:6])
grand = child.drill(next(e for e in child.screen if e.key == 'field:whatif:B4')); settle(80, 6); print('B4 >', [e.label for e in child.screen])
pix = w.grab(); q = QPainter(pix)
for m in (menu, child): q.drawPixmap(w.mapFromGlobal(m.mapToGlobal(QPoint(0, 0))), m.grab())
q.end(); pix.save(str(OUT / ('Graphite_Cascade_01_What_If_%s.png' % tag))); print('saved cascade | menus inside the window:', all(w.frameGeometry().contains(m.frameGeometry()) for m in (menu, child)), '| popups:', 2)
menu.close(); settle(20, 2)
print('keyboard in:', type(app.focusWidget()).__name__, '| Field in front:', w._field_active)
