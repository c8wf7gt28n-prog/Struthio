# the icon option: Words (the default) and Icons, on the bar and on each work page; nothing but the face changes
from PySide6.QtWidgets import QApplication, QToolButton, QPushButton, QAbstractButton, QMenu
from PySide6.QtCore import QTimer, QPoint, QPointF, QEvent
from PySide6.QtGui import QHoverEvent, QMouseEvent, QHelpEvent
from workbench import tool_faces as faces
w.a_field.trigger(); settle(); v = w.field_page.view; bar = w.centre_bar
def open_tile(title):
    o = next((o for o in v.field.objects if o.title.startswith(title)), None)
    w.a_field.trigger(); settle(150, 4); v.field.select(o.id); v._describe(); QTest.keyClick(v, Qt.Key_Return); settle(900, 8); return w.tabs.currentWidget()
def tools(page):
    found = [b for b in bar.findChildren(QAbstractButton) if b.property('toolFace') and b.isVisible()]
    return found + [b for b in page.findChildren(QAbstractButton) if b.property('toolFace') and b.isVisible()]
def facts(page):
    return {b.text(): (b.width(), b.isEnabled(), faces.glyph_of(b)) for b in tools(page)}
print('a workspace that never chose opens with:', faces.mode(), '| session says:', w.session.state.get('buttons', '(nothing chosen)'))
opened_with = faces.mode(); faces.choose(w, 'words'); settle(200, 3)      # the widths in words are the measure
PAGES = (('Sheet', '07 Bench readings'), ('PDF', '07_Bench_Readings.pdf'), ('Writing', '07 Case conclusion'), ('Finding', 'Settled draw'))
before = {}
for name, tile in PAGES:
    page = open_tile(tile); before[name] = facts(page)
ok = True
faces.choose(w, 'icons'); settle(200, 3)
print('chosen:', faces.mode(), '| session keeps:', w.session.state.get('buttons'))
for n, (name, tile) in enumerate(PAGES):
    page = open_tile(tile); settle(200, 3); now = facts(page)
    same_words = set(now) == set(before[name]); ok &= same_words
    bare = [k for k, (wd, on, g) in now.items() if g in faces.BARE]; worded = [k for k, (wd, on, g) in now.items() if g and g not in faces.BARE]; plain = [k for k, (wd, on, g) in now.items() if not g]
    print('%-8s the same buttons by their words: %s | glyph alone: %s | glyph and words: %s | no glyph, kept as a plate: %s' % (name, same_words, bare, worded, plain))
    narrow = [k for k in bare if now[k][0] > 34]; ok &= not narrow
    if narrow: print('   WRONG: a bare glyph wider than 34 px:', narrow)
    save('Icons_%02d_%s_%s.png' % (n + 1, name, tag))
# a press still does what it did: the bar's + steps the PDF page; Next is where it was
page = open_tile('07_Bench_Readings.pdf'); settle(200, 3)
z0 = page.zoom.currentText(); QTest.mouseClick(bar.larger, Qt.LeftButton); settle(200, 3); z1 = page.zoom.currentText()
print('a click on the + glyph steps the page:', z0, '->', z1); ok &= z0 != z1
QTest.mouseClick(bar.smaller, Qt.LeftButton); settle(200, 3)
# under the pointer: green, and a bare glyph says its name first
def over(button):
    button.setAttribute(Qt.WA_UnderMouse, True); c = QPointF(button.rect().center())
    QApplication.sendEvent(button, QHoverEvent(QEvent.HoverEnter, c, c, QPointF(-1, -1)))
    QApplication.sendEvent(button, QMouseEvent(QEvent.MouseMove, c, button.mapToGlobal(c), Qt.NoButton, Qt.NoButton, Qt.NoModifier)); button.update()
over(bar.find); over(page.buttons['Copy citation']); settle(150, 2); save('Icons_05_Under_The_Pointer_%s.png' % tag)
shown = []
import PySide6.QtWidgets as QtW
real = QtW.QToolTip.showText
def note(pos, text, *rest): shown.append(text)
QtW.QToolTip.showText = note; faces.QToolTip.showText = note
for b in (bar.find, bar.undo, bar.smaller, page.more, page.next):
    QApplication.sendEvent(b, QHelpEvent(QEvent.ToolTip, b.rect().center(), b.mapToGlobal(b.rect().center())))
QtW.QToolTip.showText = real; faces.QToolTip.showText = real
print('tips of bare glyphs:', shown); ok &= len(shown) == 5 and all(s for s in shown)
for b in (bar.find, page.buttons['Copy citation']): b.setAttribute(Qt.WA_UnderMouse, False); b.update()
# the choice is in the menu, under Rules beside Desk artwork
work = next(b for b in w.findChildren(QToolButton) if b.objectName() == 'MoreMenus').menu(); work.aboutToShow.emit(); where = []
for a in work.actions():
    if a.menu() is not None:
        a.menu().aboutToShow.emit()
        for x in a.menu().actions():
            if x.menu() is not None and x.text().replace('&', '') == 'Buttons':
                x.menu().aboutToShow.emit(); where.append((a.text().replace('&', ''), [(y.text(), y.isChecked()) for y in x.menu().actions()]))
print('Work menu: Buttons is under', where); ok &= len(where) == 1 and where[0][1] == [('Words', False), ('Icons', True)]
# back to words: every button as wide as it was
faces.choose(w, 'words'); settle(200, 3)
for name, tile in PAGES:
    page = open_tile(tile); settle(200, 3); now = facts(page)
    moved = {k: (before[name][k][0], now[k][0]) for k in now if k in before[name] and abs(now[k][0] - before[name][k][0]) > 1}
    print('%-8s back to words, widths as before: %s %s' % (name, not moved, moved or '')); ok &= not moved
print('session keeps:', w.session.state.get('buttons'))
save('Icons_06_Words_Again_%s.png' % tag)
ok &= opened_with == 'icons'; faces.choose(w, 'icons'); settle(100, 2)
print('ICONS PROBE', 'PASS' if ok else 'FAIL')
