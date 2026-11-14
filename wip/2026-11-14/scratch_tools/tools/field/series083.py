# 0.8.3 for the owner: a series of frames of the real window on After Hours 07, driven by desk acts where it can be.
# Run through nomodel.py (w, settle, OUT, tag, W, H in scope).
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QPainter, QImage
from PySide6.QtWidgets import QApplication
from workbench import boss_theme as bt, context_menu as cm, files_service, desk_doers
APP = bt.APPEARANCE
def popups():
    return [x for x in QApplication.topLevelWidgets() if x.isVisible() and x is not w and x.width() > 20 and x.height() > 20]
def shot(name, crops=None):
    settle(40, 3)
    base = w.grab().toImage().convertToFormat(QImage.Format_RGB32);p = QPainter(base);origin = w.mapToGlobal(QPoint(0, 0))
    for pop in sorted(popups(), key=lambda x: x.winId()):p.drawImage(pop.mapToGlobal(QPoint(0, 0)) - origin, pop.grab().toImage())
    p.end();base.save(str(OUT / ('S%s_%s_%s.png' % (name, APP, tag))));print('saved', name, flush=True)
    for cname, (box, scale) in (crops or {}).items():
        c = base.copy(QRect(*box))
        if scale != 1:c = c.scaled(int(c.width() * scale), int(c.height() * scale), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        c.save(str(OUT / ('S%s_%s_%s.png' % (cname, APP, tag))))
def act(act_name, **args):
    r = desk_doers.run(w, act_name, args, door='script');settle(80, 3)
    print('act', act_name, r.get('ok'), (r.get('words') or '')[:90], flush=True);return r
root = files_service.root(w.ledger_bridge.kernel)
(root / '07 Bench readings.csv').write_text('parameter,value,unit\nRail voltage,12,V\nSettled current,280,mA\nStartup current,650,mA\nStartup duration,110,ms\n')
settle(200, 6)
act('go.today');settle(400, 4)
shot('01_home')
act('go.field');act('point.zoom', to='whole');settle(300, 4)
shot('02_field', {'02b_hologram_and_tree': ([0, 60, 356, H - 120], 1.0), '02c_her_column': ([W - 356, 60, 356, H - 120], 1.0)})
act('point.sheet', title='07 Bench readings');act('sheet.trace');settle(1400, 6)
shot('03_trace')
act('point.sheet', title='07 Limits Rev B CURRENT');act('sheet.compare');settle(500, 4)
shot('04_rev_a_rev_b')
act('sheet.close');act('go.files', view='list');settle(400, 4)
act('menu.open', on='file', name='07 Bench readings.csv');settle(300, 3)
rc = getattr(w, 'context_menu', None) or next((x for x in popups() if isinstance(x, cm.ContextMenu)), None)
row = next((r for r in (rc.findChildren(cm.ContextRow) if rc else []) if r.isEnabled() and r.isVisible()), None)
if row is not None:row.setFocus();settle(60, 2)
shot('05_right_click')
act('menu.choose', path='then');act('then.keep', column='unit', words='is mA');act('then.count');settle(300, 3)
shot('06_then_panel')
act('menu.close');settle(200, 3)
top = w.shell2.top
words = [x for x in top.menu_words() if x.isVisible() and x.menu() is not None]
tools = next((x for x in words if x.text() == 'Tools'), words[0]);menu = tools.menu();menu.aboutToShow.emit()
menu.popup(tools.mapToGlobal(QPoint(0, tools.height())));QApplication.processEvents();settle(260, 3)
rows = [a for a in menu.actions() if not a.isSeparator() and a.isEnabled()]
menu.setActiveAction(rows[1] if len(rows) > 1 else rows[0]);settle(40, 2)
shot('07_head_menu')
menu.hide();settle(200, 2)
prog = top.programs;pr = prog.mapTo(w, QPoint(0, 0))
hatch = w.type_bar.hatch;hatch.open_list(keyboard=True);QApplication.processEvents();settle(320, 3)
shot('08_apps', {'08b_logo_x3': ([pr.x() - 40, 0, prog.width() + 50, max(60, prog.height() + 6)], 3)})
hatch.programs.hide();settle(150, 2)
box = w.type_bar.box;box.setFocus();box.setText('bench');box.update_results('bench');settle(220, 3)
pop = getattr(box, 'popup', None)
if pop is not None and pop.list.count() > 2:
    ok = [i for i in range(pop.list.count()) if pop.list.item(i).flags() & Qt.ItemIsEnabled]
    if len(ok) > 1:pop.list.setCurrentRow(ok[1])
shot('09_writing_line')
box.clear();settle(100, 2)
print('SERIES DONE', flush=True)
