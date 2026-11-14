try:        # this probe walks the Approve path: from 0.6.0 that is Stacy's hand at "Ask first" (it opens on "Do and show")
    from workbench import stacy_hand as _hand; _hand.choose(w, 'ask'); w.shell2.face.show_hand()
except ImportError: pass
# The mouse path of the owner's specification, with real mouse events and no keys:
# open a sheet tile, select and change a cell, save, Back to Field at the same tile, trace the affected calculation, approve its recheck.
# Then the same task through Stacy.
from PySide6.QtCore import QPoint, QPointF, QTimer, QEvent
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QLabel, QApplication, QDialogButtonBox, QPushButton
from workbench import context_menu
k = w.ledger_bridge.kernel; p = operator(); face = w.shell2.face
def cards(): return [face.lines.itemAt(i).widget() for i in range(face.lines.count()) if face.lines.itemAt(i).widget() is not None]
def said(card, n=4): return [l.text().replace('​', '')[:300].replace('\n', ' / ') for l in card.findChildren(QLabel)][:n]
w.a_field.trigger(); settle(); v = w.field_page.view; page = w.field_page
def tile(words): return next(o for o in v.field.objects if words in o.title)
def send(kind, pos, button=Qt.NoButton, buttons=Qt.NoButton):
    QApplication.sendEvent(v, QMouseEvent(kind, QPointF(pos), QPointF(v.mapToGlobal(pos)), button, buttons, Qt.NoModifier)); settle(10, 2)
def empty_ground():
    body = v._layout()
    for x in range(int(body.right()) - 48, int(body.left()), -24):      # clear of the bar at the right edge, which a press would drag instead of the surface
        for y in range(int(body.top()) + 30, int(body.bottom()) - 70, 24):      # and of the bar and the zoom strip along the bottom
            if v._hit(QPointF(x, y)) is None and not any(b.contains(QPointF(x, y)) for b, *_ in v._hot): return QPoint(x, y)
def bring(o):        # the mouse way to bring a tile into view: drag the surface
    for _ in range(12):
        body = v._layout(); r = v.sheet_rect(o.id, body)
        if body.adjusted(4, 4, -4, -30).contains(r): return True
        dx = 0 if body.left() + 4 <= r.left() and r.right() <= body.right() - 4 else (body.center().x() - r.center().x())
        dy = 0 if body.top() + 4 <= r.top() and r.bottom() <= body.bottom() - 30 else (body.center().y() - r.center().y())
        start = empty_ground(); end = QPoint(start.x() + int(max(-200, min(200, dx))), start.y() + int(max(-160, min(160, dy))))
        send(QEvent.MouseButtonPress, start, Qt.LeftButton, Qt.LeftButton); send(QEvent.MouseMove, end, Qt.NoButton, Qt.LeftButton); send(QEvent.MouseButtonRelease, end, Qt.LeftButton)
    return False
def click_tile(o, button=Qt.LeftButton):
    bring(o); QTest.mouseClick(v, button, pos=v.sheet_rect(o.id, v._layout()).center().toPoint()); settle(120, 5)
def hot(key):
    v.repaint(); settle(20, 2)
    return next(((box, words) for box, kk, text, words in v._hot if kk == key), None)
def click_hot(key):
    found = hot(key)
    if found is None: return None
    QTest.mouseClick(v, Qt.LeftButton, pos=found[0].center().toPoint()); settle(200, 6); return found[1]
keys_before = 0
# 1. open a sheet tile with a click
sheet = tile('07 Bench readings'); print('1. dragged the sheet into view:', bring(sheet))
send(QEvent.MouseMove, v.sheet_rect(sheet.id, v._layout()).center().toPoint()); print('   hover -> the tile under the pointer:', v.field.get(v._hover).title if v._hover else None)
click_tile(sheet); panel = w.tabs.currentWidget()
print('   click -> Field left: %s | in the centre: %s “%s”' % (not w._field_active, type(panel).__name__, panel.title() if hasattr(panel, 'title') else ''))
save('Graphite_Mouse_01_Sheet_In_The_Centre_%s.png' % tag)
# 2. select a cell, change it, save: all with the mouse
grid = panel.grid; item = grid.item(2, 1); rect = grid.visualItemRect(item)
QTest.mouseClick(grid.viewport(), Qt.LeftButton, pos=rect.center()); settle(40, 3); print('2. clicked the cell ->', panel.address.text(), '| it says', item.text())
def fill():
    dlg = QApplication.activeModalWidget()
    dlg.text.setPlainText('300'); ok = dlg.findChild(QDialogButtonBox).button(QDialogButtonBox.Ok); QTest.mouseClick(ok, Qt.LeftButton)
QTimer.singleShot(300, fill); QTest.mouseDClick(grid.viewport(), Qt.LeftButton, pos=rect.center()); settle(80, 4)
print('   double-click, typed 300, OK -> the grid says', grid.item(2, 1).text(), '| unsaved:', panel.dirty)
w.centre_bar.sync(); print('   the bar’s Save reads', repr(w.centre_bar.save.text())); QTest.mouseClick(w.centre_bar.save, Qt.LeftButton); settle(200, 6)
r = k.dispatch('office.get', {'id': sheet.target['id']}, p)['result']; print('   clicked Save in the bar above -> the record says B3 =', r['document']['sheets'][0]['cells']['B3']['value'], '| unsaved:', panel.dirty)
# 3. back to the Field, at the same tile
back = w.concern.field_button; print('3. Back control: %r visible: %s' % (back.text(), back.isVisible()))
QTest.mouseClick(back, Qt.LeftButton); settle(200, 6); v = w.field_page.view
print('   clicked it -> Field in front: %s | selected: %s | the tile is in view: %s' % (w._field_active, v.selected().title, v._layout().intersects(v.sheet_rect(v.field.selected, v._layout()))))
calc = tile('07 Settled power'); print('   the calculation now:', calc.state)
# 4. trace the affected calculation: right-click selects it, the menu's Trace it goes there; the legend's T does the same by a click
click_tile(calc, Qt.RightButton); settle(60, 4)
m = QApplication.activePopupWidget(); print('4. right-click -> selected: %s | Field still in front: %s | a menu opened: %s' % (v.selected().title, w._field_active, m is not None or bool(context_menu)))
for widget in QApplication.topLevelWidgets():
    if type(widget).__name__ == 'ContextMenu' and widget.isVisible(): widget.close()
settle(40, 3)
click_hot(Qt.Key_Question); print('   clicked “? keys” -> card:', v.reading and v.reading['title'])
for _ in range(6):        # the card is longer than a small window: read on with a click on its “more ↓” until the row is in view
    if hot(Qt.Key_T) is not None: break
    more = next((b for b, k, tx, wd in v._hot if wd.startswith('Read on')), None)
    if more is None: break
    QTest.mouseClick(v, Qt.LeftButton, pos=more.center().toPoint()); settle(60, 3)
words = click_hot(Qt.Key_T); print('   clicked the card’s row for T (%s) -> card closed: %s | Talk: %s' % (words, v.reading is None, said(cards()[-1], 3)[-1][:140]))
# 5. approve its recheck: Actions (D) by a click, the step by a click, Approve by a click
words = click_hot(Qt.Key_D); print('5. clicked “D do” -> page: %s | steps: %s' % (v.reading and v.reading['title'][:44], [s_[0] for s_ in v.steps]))
save('Graphite_Mouse_02a_Steps_To_Click_%s.png' % tag)
n = next(i for i, s_ in enumerate(page.steps) if s_.words == 'Bring it up to date')
words = click_hot(Qt.Key_1 + n); print('   clicked its row (%s) -> page closed: %s | waits: %r | calculation still: %s' % (words[:60], v.reading is None, v.go, tile('07 Settled power').state))
save('Graphite_Mouse_02_Approve_On_The_Field_%s.png' % tag)
tip = click_hot(Qt.Key_G); settle(300, 6)
print('   clicked Approve (%s) -> calculations now: %s' % (tip[:90], [(o.title, o.state) for o in v.field.objects if o.kind == 'calculation']))
# 6. the reading pages by mouse: the doubt opens on a click, Close is a click
click_hot(Qt.Key_Question)
for _ in range(6):
    if hot(Qt.Key_X) is not None: break
    more = next((b for b, k, tx, wd in v._hot if wd.startswith('Read on')), None)
    if more is None: break
    QTest.mouseClick(v, Qt.LeftButton, pos=more.center().toPoint()); settle(60, 3)
click_hot(Qt.Key_X); print('6. clicked “? keys”, then the row for X -> page:', v.reading and v.reading['title'][:50])
save('Graphite_Mouse_02b_A_Page_With_Close_%s.png' % tag)
closed = click_hot(Qt.Key_Escape); print('   clicked “✕ Close” (%s) -> page closed: %s | Field in front: %s' % (closed, v.reading is None, w._field_active))
# 7. the same task through Stacy: asked in words, approved with a click
bench = tile('07 Bench readings'); click_tile(bench, Qt.RightButton)
for widget in QApplication.topLevelWidgets():
    if type(widget).__name__ == 'ContextMenu' and widget.isVisible(): widget.close()
settle(40, 3); w.shell2.ask('set the startup current to 700'); settle(200, 6); c = cards()[-1]
print('7. asked Stacy “set the startup current to 700” ->', said(c, 1)[0][:120]); print('   line:', said(c, 4)[2][:150]); print('   marks on the Field:', sorted(v.would.values())[:4], '| waits:', repr(v.go))
r = k.dispatch('office.get', {'id': bench.target['id']}, p)['result']; print('   nothing changed by asking: B4 =', r['document']['sheets'][0]['cells']['B4']['value'])
save('Graphite_Mouse_03_Stacy_Proposes_Approve_%s.png' % tag)
click_hot(Qt.Key_G); settle(300, 6)
r = k.dispatch('office.get', {'id': bench.target['id']}, p)['result']; print('   clicked Approve -> B4 =', r['document']['sheets'][0]['cells']['B4']['value'], '| Talk:', said(cards()[-1], 6)[-1][:160])
print('   calculations now:', [(o.title, o.state) for o in v.field.objects if o.kind == 'calculation'])
x = k.dispatch('field.doubt', {'id': bench.id}, p)['result']['rows']; print('   the doubt sees both edits:', [r_['why'][:70] for r_ in x if r_['about'] == 'cells as reviewed'])
print('keyboard in:', type(app.focusWidget()).__name__, '| Field in front:', w._field_active)
