# 0.8.2 the catch: menus opening (the right-click, its Then child, Tools across the head) with the catch held at fixed moments.
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QApplication
from workbench import context_menu as cm, files_service, menu_catch
from workbench.files_qt import show as show_files
menu_catch.calm = lambda widget: False
def popups():
    return [x for x in QApplication.topLevelWidgets() if x.isVisible() and x is not w and x.width() > 20 and x.height() > 20]
def hold(f):
    for c in [c for pop in popups() for c in pop.findChildren(menu_catch.Catch)]:
        c.timer.stop(); c.progress = (lambda f=f: f); c.update()
def shot(name):
    settle(30, 2)
    base = w.grab().toImage(); p = QPainter(base); origin = w.mapToGlobal(QPoint(0, 0))
    for pop in sorted(popups(), key=lambda x: x.winId()):
        at = pop.mapToGlobal(QPoint(0, 0)) - origin; p.drawImage(at, pop.grab().toImage())
    p.end(); base.save(str(OUT / ('Catch_%s_%s.png' % (name, tag)))); print('saved', name, [type(x).__name__ for x in popups()])
root = files_service.root(w.ledger_bridge.kernel)
(root / 'bench readings.csv').write_text('parameter,value,unit\nRail voltage,12,V\nSettled current,280,mA\nStartup current,650,mA\nStartup duration,110,ms\n')
tab = show_files(w); settle(300, 4); tab.mode = 'list'; tab.reload(); settle(200, 3); view = tab.table
item = next(view.topLevelItem(i) for i in range(view.topLevelItemCount()) if view.topLevelItem(i).data(0, Qt.UserRole)['name'] == 'bench readings.csv')
menu = cm.open_at(w, view.viewport(), view.visualItemRect(item).center()); QApplication.processEvents()
for f in (0.25, 0.6):hold(f); shot('01_RightClick_%03d' % int(f * 100))
Catch_start = menu_catch.Catch.__init__
def held_init(self, *a, **k):
    Catch_start(self, *a, **k); self.timer.stop(); self.progress = (lambda: 0.3)
menu_catch.Catch.__init__ = held_init
child = menu.open_child(menu.row('then')); QApplication.processEvents(); settle(60, 2)
menu_catch.Catch.__init__ = Catch_start
for f in (0.3,):
    for c in child.findChildren(menu_catch.Catch):c.progress = (lambda f=f: f); c.update()
    for c in menu.findChildren(menu_catch.Catch):c.hide()
    shot('02_Then_From_Its_Parent_%03d' % int(f * 100))
menu.close_menu(restore=False); settle(80, 2)
tools = w.menu_groups.get('Tools') or next(iter(w.menu_groups.values()))
tools.aboutToShow.emit(); tools.popup(w.mapToGlobal(QPoint(160, 56))); QApplication.processEvents(); settle(20, 1)
for f in (0.3,):hold(f); shot('03_Tools_%03d' % int(f * 100))
tools.hide(); settle(50, 1)
cm.inspect_in_line(w, '@files:bench readings.csv | rows | where unit=mA | count'); QApplication.processEvents()
for c in w.type_bar.box.findChildren(menu_catch.Catch):c.timer.stop(); c.progress = (lambda: 0.2); c.update()
shot('04_A_Line_Lands'); w.type_bar.box.clear()
print('CATCH SHOTS DONE')
