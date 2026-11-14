# 0.8.1, the owner: "I wish I could see some pictures of the program in action, menus open, and stuff like that."
# Each picture is the window with whatever is open over it (menus, cards, the right-click), laid where they stand.
from PySide6.QtCore import QPoint
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QApplication, QPushButton, QMenu
top = w.shell2.top; face = w.shell2.face; bar = w.type_bar
def popups():
    return [x for x in QApplication.topLevelWidgets() if x.isVisible() and x is not w and x.width() > 20 and x.height() > 20]
def shot(name):
    align(); settle(120, 3)
    base = w.grab().toImage(); p = QPainter(base); origin = w.mapToGlobal(QPoint(0, 0))
    for pop in sorted(popups(), key=lambda x: x.winId()):
        at = pop.mapToGlobal(QPoint(0, 0)) - origin; p.drawImage(at, pop.grab().toImage())
    p.end(); base.save(str(OUT / ('Action_%s_%s.png' % (name, tag)))); print('saved', name, '| open:', [type(x).__name__ for x in popups()])
def close_all():
    for pop in popups():
        try:pop.hide()
        except Exception:pass
    settle(80, 2)
# 1. Home, the Work menu open
w.a_home.trigger(); settle(300, 4)
words = getattr(top, 'bar_menus', [])
work = words[0] if words else None
menu = w.menu_groups['File']; menu.aboutToShow.emit()
menu.popup(work.mapToGlobal(QPoint(0, work.height())) if work is not None else w.mapToGlobal(QPoint(10, 60))); settle(200, 3); shot('01_Work_Menu'); menu.hide(); close_all()
# 2. Rules > Desk artwork > Appearance, nested
rules = w.menu_groups.get('Settings')
if rules is not None:
    rules.aboutToShow.emit(); head = next((x for x in words if x.text().replace('&', '').strip().startswith('Rules')), None)
    rules.popup(head.mapToGlobal(QPoint(0, head.height())) if head is not None else w.mapToGlobal(QPoint(300, 60))); settle(200, 3)
    art = next((a for a in rules.actions() if a.menu() is not None and 'Desk artwork' in a.text()), None)
    if art is not None:
        sub = art.menu(); rules.setActiveAction(art); sub.popup(rules.mapToGlobal(rules.actionGeometry(art).topRight())); settle(200, 3)
        look = next((a for a in sub.actions() if a.menu() is not None and 'Appearance' in a.text()), None)
        if look is not None:
            sub.setActiveAction(look); look.menu().aboutToShow.emit(); look.menu().popup(sub.mapToGlobal(sub.actionGeometry(look).topRight())); settle(200, 3)
    shot('02_Rules_Desk_Artwork_Appearance'); close_all()
# 3. Apps, open
top.programs.click(); settle(400, 4); shot('03_Apps'); close_all()
# 4. a meter card: CPU, then GPU
mon = top.pulse
for key in ('CPU', 'GPU'):
    v_ = mon.values[key]; QTest.mouseClick(mon, Qt.LeftButton, pos=v_.mapTo(mon, v_.rect().center())); settle(350, 4); shot('04_Meter_%s' % key)
    c = getattr(w, '_meter_card', None)
    if c is not None:c.hide()
    settle(100, 2)
# 5. the Field, a sheet selected, its right-click
w.a_field.trigger(); settle(300, 4); v = w.field_page.view
o = next(o for o in v.field.objects if o.title.startswith('07 Bench readings')); v.field.select(o.id); v._reveal(); v._describe(); v.update(); v.setFocus(); settle(100, 3)
from workbench import context_menu
context_menu.open_at_focus(w); settle(400, 4); shot('05_Field_Right_Click_On_A_Sheet'); close_all()
# 6. her hand menu
face.open_hand(); settle(300, 3); shot('06_Her_Hand'); close_all()
# 7. a change asked of her, then the typing line: words (red arrow) and a line (royal purple)
try:
    from workbench import stacy_hand as _hand; _hand.choose(w, 'ask'); face.show_hand()
except Exception:pass
w.shell2.ask('set B3 to 300'); settle(400, 6)
bar.box.setFocus(); QTest.keyClicks(bar.box, 'what is waiting for me'); settle(300, 3); shot('07_Words_To_Her_Red_Arrow'); bar.box.clear()
QTest.keyClicks(bar.box, 'field.read | pick waiting | count'); settle(400, 3); shot('08_A_Line_Royal_Purple_Arrow'); bar.box.clear(); close_all()
# 8. the Files tree with its light, the left pane's three views
nav = w.settings_navigator
nav.bar.buttons[0].click(); settle(300, 3); shot('09_Files_Tree_And_Trash')
print('ACTION SHOTS DONE')
