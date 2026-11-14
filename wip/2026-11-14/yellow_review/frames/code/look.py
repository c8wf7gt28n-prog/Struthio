# Review of the look (0.8.3 burnt yellow + neon kp): frames through nomodel.py (exec'd: w, app, settle, align, OUT, tag, W, H).
# Every state: the whole window with its popups laid on, plus crops. Rectangles of interest go to rects_<appearance>_<tag>.json.
import json, traceback
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QPainter, QImage
from PySide6.QtWidgets import QApplication, QMenu
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
def shot(name, widgets=None, crops=None, settle_first=True):
    if settle_first:settle(30, 3);align(2)
    base = w.grab().toImage().convertToFormat(QImage.Format_RGB32);p = QPainter(base);origin = w.mapToGlobal(QPoint(0, 0));pops = []
    for pop in sorted(popups(), key=lambda x: x.winId()):
        at = pop.mapToGlobal(QPoint(0, 0)) - origin;image = pop.grab().toImage();p.drawImage(at, image)
        pops.append([type(pop).__name__, at.x(), at.y(), pop.width(), pop.height()])
    p.end();f = 'R_%s_%s.png' % (name, PRE);base.save(str(OUT / f))
    entry = {'file': f, 'popups': pops, 'widgets': {}}
    for k, v in (widgets or {}).items():
        try:
            if v is not None:entry['widgets'][k] = rect(v)
        except Exception as e:note('rect', k, e)
    for cname, (box, scale) in (crops or {}).items():
        crop = base.copy(QRect(*box))
        if scale != 1:crop = crop.scaled(crop.width() * scale, crop.height() * scale, Qt.IgnoreAspectRatio, Qt.FastTransformation)
        cf = 'R_%s_%s.png' % (cname, PRE);crop.save(str(OUT / cf));entry.setdefault('crops', {})[cname] = [cf, box, scale]
    REC['frames'][name] = entry;print('saved', f, pops)
    return base
def step(fn):
    try:fn()
    except Exception:note('FAILED', fn.__name__, traceback.format_exc()[-600:])
root = files_service.root(w.ledger_bridge.kernel)
(root / 'bench readings.csv').write_text('parameter,value,unit\nRail voltage,12,V\nSettled current,280,mA\nStartup current,650,mA\nStartup duration,110,ms\n')
settle(60, 6)
top = w.shell2.top;prog = top.programs
from workbench import tool_faces
note('glyph mode', tool_faces.STATE.get('mode'), 'glow', bt.glow(), 'art', w.session.state.get('desk_art'))
G = {}
def s01():
    w.settings_navigator.cabinet.click();settle(60, 6)
    tree = w.cabinet_page.tree;G['tree'] = tree
    first = tree.topLevelItem(0)
    if first is not None:
        first.setExpanded(True);child = first.child(0) if first.childCount() else first;tree.setCurrentItem(child);child.setSelected(True)
    tree.setFocus();settle(60, 4)
    head = rect(prog);G['head'] = head
    wide = [max(0, head[0] - 260), 0, min(W, head[0] + head[2] + 10) - max(0, head[0] - 260), max(64, head[3] + 6)]
    note('apps rect', head, 'logo', getattr(prog, 'logo', None) is not None, 'scale', getattr(prog, 'scale', None), 'tip', prog.toolTip(), 'name', prog.accessibleName())
    shot('01_rest_tree', {'apps': prog, 'tree': tree, 'tabs': w.left_pane.tabs},
         {'01x4_logo': ([head[0] - 6, 0, head[2] + 12, head[3] + 4], 4), '01_head_right': (wide, 1), '01x3_tree': ([0, 50, 360, 200], 3)})
step(s01)
def logo_states():
    if getattr(prog, 'logo', None) is None:return
    from workbench import kp_logo, boss_qt
    head = G['head'];box = [head[0] - 6, 0, head[2] + 12, head[3] + 4]
    keep = bt.GLOW[0]
    for lv in (0.0, 1.0, 1.9, 3.0):
        bt.GLOW[0] = lv;prog.update();settle(20, 2)
        shot('11_logo_glow_%s' % str(lv).replace('.', ''), None, {'11x4_logo_glow_%s' % str(lv).replace('.', ''): (box, 4)})
    bt.GLOW[0] = keep
    orig = kp_logo.AppsButton.surge
    for sv in (1.0, 0.5):
        kp_logo.AppsButton.surge = lambda self, sv=sv: sv;prog.update();settle(20, 2)
        shot('11_logo_surge_%s' % str(sv).replace('.', ''), None, {'11x4_logo_surge_%s' % str(sv).replace('.', ''): (box, 4)})
    kp_logo.AppsButton.surge = orig
    um = kp_logo.AppsButton.underMouse
    kp_logo.AppsButton.underMouse = lambda self: True;prog.update();settle(20, 2)
    shot('11_logo_hover', None, {'11x4_logo_hover': (box, 4)})
    kp_logo.AppsButton.underMouse = um
    prog.setFocus(Qt.TabFocusReason);settle(30, 2)
    note('apps focus', prog.hasFocus())
    shot('11_logo_focus', None, {'11x4_logo_focus': (box, 4)})
    art = w.session.state.get('desk_art', 'illustrated')
    boss_qt.choose_art(w, 'clean');settle(60, 3)
    shot('11_logo_clean', None, {'11x4_logo_clean': (box, 4), '11_clean_head': ([max(0, head[0] - 260), 0, min(W, head[0] + head[2] + 10) - max(0, head[0] - 260), 64], 1)})
    boss_qt.choose_art(w, art);settle(60, 3)
    G['tree'].setFocus()
step(logo_states)
def head_menus():
    words = [x for x in top.menu_words() if x.isVisible() and x.menu() is not None]
    note('head words', [x.text() for x in words])
    def fills(m):
        m.aboutToShow.emit();return [a for a in m.actions() if not a.isSeparator()]
    # 2. Work menu, second enabled row lit
    for word in words[:1] + [x for x in words if x.text() in ('Rules',)]:
        menu = word.menu();menu.aboutToShow.emit();menu.popup(word.mapToGlobal(QPoint(0, word.height())));QApplication.processEvents();settle(220, 2)
        rows = [a for a in menu.actions() if not a.isSeparator() and a.isEnabled()]
        menu.setActiveAction(rows[1] if len(rows) > 1 else rows[0]);settle(30, 2)
        r = rect(menu);geo = menu.actionGeometry(menu.activeAction())
        shot('02_menu_%s' % word.text().replace(' ', ''), {'menu': menu}, {'02x3_menu_%s' % word.text().replace(' ', ''): ([r[0], r[1] + geo.top() - 8, min(r[2], 420), geo.height() + 16], 3)})
        note('menu', word.text(), 'lit', menu.activeAction().text(), 'row geo', [geo.left(), geo.top(), geo.width(), geo.height()], 'menu rect', r,
             'icon visible', bool(menu.activeAction().icon() and not menu.activeAction().icon().isNull()))
        # a disabled row lit, if any
        dis = [a for a in menu.actions() if not a.isSeparator() and not a.isEnabled() and a.text()]
        if dis:
            menu.setActiveAction(dis[0]);settle(30, 2);geo = menu.actionGeometry(dis[0])
            note('disabled lit', dis[0].text(), menu.activeAction() is dis[0])
            shot('02d_menu_disabled_%s' % word.text().replace(' ', ''), {'menu': menu}, {'02dx3_%s' % word.text().replace(' ', ''): ([r[0], r[1] + geo.top() - 8, min(r[2], 420), geo.height() + 16], 3)})
        # a child menu with a checked item
        deep = None
        for a in rows:
            if a.menu() is not None and [b for b in fills(a.menu()) if b.isEnabled()]:
                if any(b.isCheckable() and b.isChecked() for b in a.menu().actions()):deep = a;break
                deep = deep or a
        if deep is not None:
            menu.setActiveAction(deep);sub = deep.menu();sub.aboutToShow.emit()
            geo = menu.actionGeometry(deep);sub.popup(menu.mapToGlobal(QPoint(menu.width() - 4, geo.top())));QApplication.processEvents();settle(220, 2)
            inner = [a for a in sub.actions() if not a.isSeparator() and a.isEnabled()]
            checked = [a for a in inner if a.isCheckable() and a.isChecked()]
            pick = checked[0] if checked else (inner[0] if inner else None)
            if pick is not None:sub.setActiveAction(pick)
            note('child', deep.text(), 'lit', pick.text() if pick else None, 'checked', [a.text() for a in checked])
            rs = rect(sub)
            shot('03_child_%s' % word.text().replace(' ', ''), {'menu': menu, 'sub': sub}, {'03x2_child_%s' % word.text().replace(' ', ''): ([r[0], r[1], min(W - r[0], r[2] + rs[2]), max(r[3], rs[3] + rs[1] - r[1])], 2)})
            sub.hide()
        menu.hide();settle(80, 2)
    G['words'] = words
step(head_menus)
def catch_held():
    words = G['words'];word = words[0];menu = word.menu()
    start = menu_catch.Catch.__init__;calm = menu_catch.calm
    menu_catch.calm = lambda widget: False
    for fv in (0.08, 0.3):
        def held(self, *a, fv=fv, **k):
            start(self, *a, **k);self.timer.stop();self.progress = (lambda: fv)
        menu_catch.Catch.__init__ = held
        menu.aboutToShow.emit();menu.popup(word.mapToGlobal(QPoint(0, word.height())));QApplication.processEvents();settle(30, 2)
        rows = [a for a in menu.actions() if not a.isSeparator() and a.isEnabled()]
        menu.setActiveAction(rows[1] if len(rows) > 1 else rows[0]);settle(20, 1)
        r = rect(menu)
        shot('04_catch_%s' % str(fv).replace('.', ''), {'menu': menu}, {'04x3_catch_%s' % str(fv).replace('.', ''): ([r[0], r[1], min(r[2], 460), min(r[3], 220)], 3)})
        menu.hide();settle(120, 2)
    menu_catch.Catch.__init__ = start;menu_catch.calm = calm;settle(200, 2)
step(catch_held)
def right_click():
    tab = show_files(w);settle(300, 4);tab.mode = 'list';tab.reload();settle(200, 3);view = tab.table;G['view'] = view
    item = next(view.topLevelItem(i) for i in range(view.topLevelItemCount()) if view.topLevelItem(i).data(0, Qt.UserRole)['name'] == 'bench readings.csv')
    view.setCurrentItem(item);item.setSelected(True);view.setFocus();settle(60, 2)
    rc = cm.open_at(w, view.viewport(), view.visualItemRect(item).center());QApplication.processEvents();settle(250, 3)
    rows = [r for r in rc.findChildren(cm.ContextRow) if r.isEnabled() and r.isVisible()]
    if rows:rows[0].setFocus();settle(40, 2)
    r = rect(rc)
    shot('05_right_click', {'files_list': view, 'rc': rc}, {'05x3_rc': ([r[0], r[1], min(r[2], 420), min(r[3], 160)], 3)})
    child = rc.open_child(rc.row('then'), keyboard=True);QApplication.processEvents();settle(300, 3)
    prow = [x for x in child.findChildren(cm.ContextRow) if x.isEnabled() and x.isVisible()] if child is not None else []
    if prow:prow[min(1, len(prow) - 1)].setFocus();settle(40, 2)
    c = rect(child) if child is not None else r
    shot('06_line_panel', {'files_list': view, 'rc': rc, 'child': child}, {'06x2_panel': ([min(r[0], c[0]), min(r[1], c[1]), min(W - min(r[0], c[0]), max(r[0] + r[2], c[0] + c[2]) - min(r[0], c[0])), max(r[1] + r[3], c[1] + c[3]) - min(r[1], c[1])], 2)})
    rc.close_menu(restore=False);settle(150, 2)
    view.setFocus();settle(40, 2)
    vr = rect(view);ir = view.visualItemRect(item)
    tb = w.tabs.tabBar() if hasattr(w.tabs, 'tabBar') else None
    crops = {'07x3_list_row': ([vr[0], vr[1] + view.header().height() + ir.top() - 6, min(vr[2], 520), ir.height() + 12], 3)}
    if tb is not None:
        t_ = rect(tb);crops['07x3_centre_tabs'] = ([t_[0], t_[1], min(t_[2], 600), t_[3]], 3)
    shot('07_list_tabs', {'files_list': view, 'centre_tabs': tb}, crops)
step(right_click)
def apps_open():
    hatch = w.type_bar.hatch;hatch.open_list(keyboard=True);QApplication.processEvents();settle(300, 3)
    lst = getattr(hatch, 'programs', None)
    r = rect(lst) if lst is not None else [0, 0, 10, 10]
    head = G.get('head', [W - 100, 0, 90, 60])
    shot('08_apps_open', {'apps': prog, 'list': lst}, {'08x3_apps_rows': ([r[0], r[1], min(r[2], 460), min(r[3], 150)], 3), '08x4_logo': ([head[0] - 6, 0, head[2] + 12, head[3] + 4], 4)})
    if lst is not None:lst.hide()
    settle(150, 2)
step(apps_open)
def results():
    box = w.type_bar.box;box.setFocus();box.setText('bench');box.update_results('bench');settle(200, 3)
    pop = getattr(box, 'popup', None)
    if pop is not None and pop.list.count() > 2:
        rows_ = [i for i in range(pop.list.count()) if pop.list.item(i).flags() & Qt.ItemIsEnabled]
        if len(rows_) > 1:pop.list.setCurrentRow(rows_[1])
    pr = rect(pop) if pop is not None else [0, 0, 10, 10];br = rect(box)
    shot('09_results', {'results': pop, 'line': box}, {'09x2_results': ([pr[0], pr[1], min(pr[2], 700), pr[3]], 2), '09x3_line': ([max(0, br[0] - 30), br[1] - 14, min(br[2] + 60, 700), br[3] + 28], 3)})
    # the words selected in the line
    if pop is not None:pop.hide()
    box.setFocus();box.selectAll();settle(60, 2)
    shot('09b_line_selection', {'line': box}, {'09bx3_line_sel': ([max(0, br[0] - 30), br[1] - 14, min(br[2] + 60, 700), br[3] + 28], 3)})
    box.clear();settle(100, 2)
step(results)
def find_field():
    bar = getattr(w, 'centre_bar', None);field = None
    if bar is not None and bar.open_find():
        settle(120, 2);field = bar.finder.line;field.setFocus();field.setText('bench');settle(200, 3)
    if field is not None:
        f = rect(field)
        shot('10_find', {'field': field}, {'10x3_find': ([f[0] - 40, f[1] - 24, f[2] + 80, f[3] + 48], 3)})
step(find_field)
def settings_machine():
    for name in ('settings', 'machine'):
        b = getattr(w.settings_navigator, name, None)
        if b is None:continue
        b.click();settle(200, 4)
        from PySide6.QtWidgets import QTreeWidget, QListWidget, QTreeView
        page = w.settings_navigator
        views = [v for v in w.left_pane.findChildren(QTreeView) if v.isVisible()] + [v for v in w.left_pane.findChildren(QListWidget) if v.isVisible()]
        note(name, 'views', [type(v).__name__ + ':' + v.objectName() for v in views])
        for v in views[:1]:
            m = v.model()
            if m is not None and m.rowCount() > 1:
                idx = m.index(1, 0);v.setCurrentIndex(idx);v.setFocus();settle(60, 2)
        shot('12_left_%s' % name, {}, {'12x2_left_%s' % name: ([0, 50, 360, 300], 2)})
    w.settings_navigator.cabinet.click();settle(100, 2)
step(settings_machine)
def field():
    w.show_field();settle(400, 6)
    fp = getattr(w, 'field_page', None)
    view = getattr(fp, 'view', None)
    if view is not None:
        view.setFocus();settle(60, 2)
        from PySide6.QtTest import QTest
        for key in (Qt.Key_Right, Qt.Key_Down):
            QTest.keyClick(view, key);settle(60, 2)
    shot('13_field', {'view': view})
    from workbench.field_page import leave_field
    leave_field(w);settle(200, 3)
step(field)
(OUT / ('rects_%s.json' % PRE)).write_text(json.dumps(REC, indent=1));print('FRAMES DONE')
