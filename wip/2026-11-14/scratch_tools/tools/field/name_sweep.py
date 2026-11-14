# 0.8.0: the language is never named where the owner can see it. Walk every widget's words (text, tip, status tip,
# placeholder, accessible name and description, window title) and every menu line (opened, so their rows are built),
# on Home, the Field and a sheet page, and list each that names it.
import re
from PySide6.QtWidgets import QWidget, QMenu, QAbstractButton, QLabel, QLineEdit, QPlainTextEdit, QTextEdit, QComboBox
from PySide6.QtGui import QAction
NAME = re.compile(r'stac(?!y)', re.I)
found = {}
def words_of(w):
    out = []
    for get in ('text', 'toolTip', 'statusTip', 'placeholderText', 'accessibleName', 'accessibleDescription', 'windowTitle', 'title'):
        f = getattr(w, get, None)
        if callable(f):
            try:v = f()
            except TypeError:continue
            if isinstance(v, str):out.append((get, v))
    if isinstance(w, QComboBox):out += [('item', w.itemText(i)) for i in range(w.count())]
    return out
def sweep(where):
    for w in w_all():
        for kind, v in words_of(w):
            if NAME.search(v):found.setdefault((type(w).__name__, kind, v[:120]), where)
    for a in w.findChildren(QAction):
        for kind in ('text', 'toolTip', 'statusTip'):
            v = getattr(a, kind)()
            if NAME.search(v):found.setdefault(('QAction', kind, v[:120]), where)
def w_all():
    return [x for x in w.findChildren(QWidget)] + [w]
def open_menus():
    for menu in w.findChildren(QMenu):
        try:menu.aboutToShow.emit()
        except Exception:pass
    settle(50, 2)
open_menus(); sweep('start')
w.a_home.trigger(); settle(300, 4); open_menus(); sweep('home')
w.a_field.trigger(); settle(300, 4); v = w.field_page.view
o = next(o for o in v.field.objects if o.title.startswith('07 Bench readings')); v.field.select(o.id); v._reveal(); v._describe(); v.update(); settle(100, 3)
open_menus(); sweep('field')
from workbench import context_menu
try:
    menu = context_menu.menu_for(w, v) if hasattr(context_menu, 'menu_for') else None
except Exception:menu = None
bar = w.type_bar; QTest.keyClicks(bar.box, 'files.list'); settle(400, 3); sweep('line with a line'); bar.box.clear()
QTest.keyClicks(bar.box, 'explain files.list'); settle(400, 3); sweep('line with explain'); bar.box.clear()
for (cls, kind, v_), where in sorted(found.items(), key=lambda kv: kv[1]):print('NAMED', where, '|', cls, kind, '|', repr(v_))
print('NAME SWEEP', len(found), 'places')
