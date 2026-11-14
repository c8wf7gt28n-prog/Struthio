# Second set: disabled/unavailable rows lit, captions on the bar, catch band over the bar, head word with the keyboard,
# a checked tool button, a combo with the keyboard. Exec'd by nomodel.py.
import json, traceback
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QPainter, QImage
from PySide6.QtWidgets import QApplication, QMenu, QToolButton, QPushButton, QComboBox
from workbench import boss_theme as bt, context_menu as cm, files_service, menu_catch
from workbench.files_qt import show as show_files
APP = bt.APPEARANCE;REC = {'appearance': APP, 'size': [W, H], 'frames': {}, 'notes': []}
PRE = '%s_%s' % (APP, tag)
def note(*a):
    s = ' '.join(str(x) for x in a);print('NOTE', s);REC['notes'].append(s)
def popups():
    return [x for x in QApplication.topLevelWidgets() if x.isVisible() and x is not w and x.width() > 20 and x.height() > 20]
def rect(widget):
    tl = widget.mapTo(w, QPoint(0, 0)) if widget.window() is w else widget.mapToGlobal(QPoint(0, 0)) - w.mapToGlobal(QPoint(0, 0))
    return [tl.x(), tl.y(), widget.width(), widget.height()]
def shot(name, widgets=None, crops=None):
    settle(30, 3);align(2)
    base = w.grab().toImage().convertToFormat(QImage.Format_RGB32);p = QPainter(base);origin = w.mapToGlobal(QPoint(0, 0));pops = []
    for pop in sorted(popups(), key=lambda x: x.winId()):
        at = pop.mapToGlobal(QPoint(0, 0)) - origin;image = pop.grab().toImage();p.drawImage(at, image)
        pops.append([type(pop).__name__, at.x(), at.y(), pop.width(), pop.height()])
    p.end();f = 'S_%s_%s.png' % (name, PRE);base.save(str(OUT / f))
    entry = {'file': f, 'popups': pops, 'widgets': {}}
    for k, v in (widgets or {}).items():
        try:
            if v is not None:entry['widgets'][k] = rect(v)
        except Exception as e:note('rect', k, e)
    for cname, (box, scale) in (crops or {}).items():
        crop = base.copy(QRect(*box))
        if scale != 1:crop = crop.scaled(crop.width() * scale, crop.height() * scale, Qt.IgnoreAspectRatio, Qt.FastTransformation)
        cf = 'S_%s_%s.png' % (cname, PRE);crop.save(str(OUT / cf));entry.setdefault('crops', {})[cname] = [cf, box, scale]
    REC['frames'][name] = entry;print('saved', f, pops)
def step(fn):
    try:fn()
    except Exception:note('FAILED', fn.__name__, traceback.format_exc()[-700:])
root = files_service.root(w.ledger_bridge.kernel)
(root / 'bench readings.csv').write_text('parameter,value,unit\nRail voltage,12,V\nSettled current,280,mA\n')
settle(60, 6)
top = w.shell2.top;prog = top.programs
words = [x for x in top.menu_words() if x.isVisible() and x.menu() is not None]
def disabled_rows():
    found = 0
    for word in words:
        menu = word.menu();menu.aboutToShow.emit()
        dis = [a for a in menu.actions() if not a.isSeparator() and not a.isEnabled() and a.text() and a.menu() is None]
        if not dis:continue
        menu.popup(word.mapToGlobal(QPoint(0, word.height())));QApplication.processEvents();settle(200, 2)
        menu.setActiveAction(dis[0]);settle(40, 2)
        r = rect(menu);geo = menu.actionGeometry(dis[0])
        note('disabled lit in', word.text(), repr(dis[0].text()), 'active is it', menu.activeAction() is dis[0], 'geo', [geo.top(), geo.height()], 'menu', r)
        shot('20_disabled_%s' % word.text(), {'menu': menu}, {'20x3_disabled_%s' % word.text(): ([r[0], r[1] + geo.top() - 6, min(r[2], 420), geo.height() + 12], 3)})
        menu.hide();settle(100, 2);found += 1
        if found >= 2:break
step(disabled_rows)
def head_word_focus():
    word = words[1] if len(words) > 1 else words[0]
    word.setFocus(Qt.TabFocusReason);settle(40, 2);r = rect(word)
    note('head word focus', word.text(), word.hasFocus())
    shot('21_head_word_focus', {'word': word}, {'21x3_head_word': ([max(0, r[0] - 10), 0, r[2] + 80, r[3] + 6], 3)})
step(head_word_focus)
def apps_rows():
    hatch = w.type_bar.hatch;hatch.open_list(keyboard=True);QApplication.processEvents();settle(300, 3)
    lst = hatch.programs;from workbench.programs_qt import MenuRow
    rows = [x for x in lst.findChildren(MenuRow) if x.isVisible()]
    note('apps rows', [(x.word, x.caption, bool(getattr(x, 'unavailable', False))) for x in rows][:40])
    r = rect(lst)
    for want, name in ((lambda x: getattr(x, 'unavailable', False), 'unavailable'), (lambda x: x.caption and not getattr(x, 'unavailable', False), 'caption')):
        row = next((x for x in rows if want(x)), None)
        if row is None:note('no', name, 'row');continue
        row.setFocus();settle(40, 2);rr = rect(row)
        note('apps lit', name, row.word, row.caption, 'active', row.active())
        shot('22_apps_%s' % name, {'list': lst, 'row': row}, {'22x3_apps_%s' % name: ([rr[0], rr[1] - 4, rr[2], rr[3] + 8], 3)})
    lst.hide();settle(150, 2)
step(apps_rows)
def rc_catch():
    tab = show_files(w);settle(300, 4);tab.mode = 'list';tab.reload();settle(200, 3);view = tab.table
    item = next(view.topLevelItem(i) for i in range(view.topLevelItemCount()) if view.topLevelItem(i).data(0, Qt.UserRole)['name'] == 'bench readings.csv')
    view.setCurrentItem(item);item.setSelected(True);settle(60, 2)
    start = menu_catch.Catch.__init__;calm = menu_catch.calm;menu_catch.calm = lambda widget: False
    for fv in (0.1, 0.25):
        def held(self, *a, fv=fv, **k):
            start(self, *a, **k);self.timer.stop();self.progress = (lambda: fv)
        menu_catch.Catch.__init__ = held
        rc = cm.open_at(w, view.viewport(), view.visualItemRect(item).center());QApplication.processEvents();settle(60, 2)
        rows = [x for x in rc.findChildren(cm.ContextRow) if x.isEnabled() and x.isVisible()]
        # light the row the band crosses: the one whose centre is nearest the band's place
        h = rc.height();y = h * 0.10 + (h * 0.34) * fv
        pick = min(rows, key=lambda x: abs(x.mapTo(rc, QPoint(0, x.height() // 2)).y() - y)) if rows else None
        if pick is not None:pick.setFocus();settle(20, 1)
        note('rc catch', fv, 'band y', y, 'lit', pick.word if pick else None)
        r = rect(rc)
        shot('23_rc_catch_%s' % str(fv).replace('.', ''), {'rc': rc}, {'23x3_rc_catch_%s' % str(fv).replace('.', ''): ([r[0], r[1], min(r[2], 420), min(r[3], 140)], 3)})
        rc.close_menu(restore=False);settle(120, 2)
    # the Rules menu, its second row lit and the band across it
    word = next((x for x in words if x.text() == 'Rules'), words[0]);menu = word.menu()
    for fv in (0.5, 0.7):
        def held(self, *a, fv=fv, **k):
            start(self, *a, **k);self.timer.stop();self.progress = (lambda: fv)
        menu_catch.Catch.__init__ = held
        menu.aboutToShow.emit();menu.popup(word.mapToGlobal(QPoint(0, word.height())));QApplication.processEvents();settle(30, 2)
        rows = [a for a in menu.actions() if not a.isSeparator() and a.isEnabled() and a.menu() is None]
        h = menu.height();y = h * 0.10 + (h * 0.34) * fv
        pick = min(rows, key=lambda a: abs(menu.actionGeometry(a).center().y() - y)) if rows else None
        if pick is not None:menu.setActiveAction(pick)
        settle(20, 1);r = rect(menu)
        note('rules catch', fv, 'band y', y, 'lit', pick.text() if pick else None, 'geo', menu.actionGeometry(pick).getRect() if pick else None)
        shot('24_rules_catch_%s' % str(fv).replace('.', ''), {'menu': menu}, {'24x3_rules_catch_%s' % str(fv).replace('.', ''): ([r[0], r[1], min(r[2], 420), min(r[3], 170)], 3)})
        menu.hide();settle(120, 2)
    menu_catch.Catch.__init__ = start;menu_catch.calm = calm;settle(200, 2)
step(rc_catch)
def checked_buttons():
    found = []
    for b in w.findChildren(QPushButton) + w.findChildren(QToolButton):
        if b.isVisible() and b.isCheckable() and b.isChecked() and b.width() > 10:found.append(b)
    note('checked visible buttons', [(type(b).__name__, b.objectName(), b.text()[:20], b.property('arcButton')) for b in found[:12]])
    boxes = {}
    for i, b in enumerate(found[:4]):
        r = rect(b);boxes['25x3_checked_%d' % i] = ([max(0, r[0] - 8), max(0, r[1] - 6), r[2] + 16, r[3] + 12], 3)
    combos = [c for c in w.findChildren(QComboBox) if c.isVisible()]
    if combos:
        combos[0].setFocus();settle(40, 2);r = rect(combos[0]);boxes['25x3_combo_focus'] = ([max(0, r[0] - 8), max(0, r[1] - 6), r[2] + 16, r[3] + 12], 3)
        note('combo', combos[0].objectName(), combos[0].hasFocus())
    shot('25_checked', {}, boxes)
step(checked_buttons)
(OUT / ('rects2_%s.json' % PRE)).write_text(json.dumps(REC, indent=1));print('FRAMES DONE')
