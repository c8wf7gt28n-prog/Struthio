# 0.8.1 pictures of the new right-click: the short first level, More, and the line panel carried a few steps.
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QApplication
from workbench import context_menu as cm, files_service
from workbench.files_qt import show as show_files

def popups():
    return [x for x in QApplication.topLevelWidgets() if x.isVisible() and x is not w and x.width() > 20 and x.height() > 20]
def shot(name):
    settle(150, 4)
    base = w.grab().toImage(); p = QPainter(base); origin = w.mapToGlobal(QPoint(0, 0))
    for pop in sorted(popups(), key=lambda x: x.winId()):
        at = pop.mapToGlobal(QPoint(0, 0)) - origin; p.drawImage(at, pop.grab().toImage())
    p.end(); base.save(str(OUT / ('RightClick_%s_%s.png' % (name, tag)))); print('saved', name, '| open:', [type(x).__name__ for x in popups()])
def close_all():
    menu = getattr(w, 'context_menu', None)
    if menu is not None:
        try:menu.close_menu(restore=False)
        except RuntimeError:pass
    settle(80, 2)

root = files_service.root(w.ledger_bridge.kernel)
(root / 'bench readings.csv').write_text('parameter,value,unit\nRail voltage,12,V\nSettled current,280,mA\nStartup current,650,mA\nStartup duration,110,ms\n'
                                         'Idle current,35,mA\nRipple,40,mV\n')
tab = show_files(w); settle(300, 4); tab.mode = 'list'; tab.reload(); settle(200, 3)
view = tab.table
item = next(view.topLevelItem(i) for i in range(view.topLevelItemCount()) if view.topLevelItem(i).data(0, Qt.UserRole)['name'] == 'bench readings.csv')
at = view.visualItemRect(item).center()
# 1. a file: the first level
menu = cm.open_at(w, view.viewport(), at); settle(300, 4); print('first level:', menu.first_keys()); shot('01_A_File');
# 2. More, in its groups
more = menu.open_child(menu.row('more')); settle(300, 4); shot('02_More'); close_all()
# 3. Then: the line on its slab, read once
menu = cm.open_at(w, view.viewport(), at); settle(200, 3)
panel = menu.open_child(menu.row('then')); settle(400, 6); print('panel:', panel.count_words()); shot('03_Then_The_Line_Panel')
# 4. Keep rows where › unit: each value with what it keeps
panel.choose('step:where'); settle(200, 3); panel.choose('field:unit'); settle(300, 4); shot('04_Keep_Rows_Where_Unit')
# 5. chosen, then Count by
panel.choose('where unit=mA'); settle(300, 4); shot('05_Two_Steps_On')
panel.choose('step:sort'); settle(300, 4); shot('06_Sort_By'); panel.back(); settle(200, 3)
panel.choose('step:count'); settle(300, 4); print('line:', panel.line, '|', panel.count_words()); shot('07_Counted'); close_all()
# 6. the Field: the reviewed sheet
w.a_field.trigger(); settle(400, 5); v = w.field_page.view
o = next((o for o in v.field.objects if o.title.startswith('07 Bench readings')), None)
if o is not None:
    v.field.select(o.id); v._reveal(); v._describe(); v.update(); v.setFocus(); settle(150, 3)
    menu = cm.open_at_focus(w); settle(300, 4); print('field first level:', menu.first_keys()); shot('08_A_Sheet_In_The_Field')
    if menu.row('then') is not None:
        panel = menu.open_child(menu.row('then')); settle(500, 6); print('sheet panel:', panel.line, '|', panel.count_words()); shot('09_The_Sheets_Reviewed_Rows')
    close_all()
print('RIGHT-CLICK SHOTS DONE')
