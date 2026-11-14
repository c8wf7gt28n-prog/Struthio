# an audit inventory: every menu line and every visible control, by surface
from PySide6.QtWidgets import QAbstractButton, QMenu, QToolButton, QComboBox, QLineEdit, QLabel
from PySide6.QtGui import QAction
from PySide6.QtCore import QPoint
def lines(menu, depth=0, out=None, seen=None):
    out = [] if out is None else out; seen = set() if seen is None else seen
    if id(menu) in seen or depth > 3: return out
    seen.add(id(menu))
    try: menu.aboutToShow.emit()
    except Exception: pass
    for a in menu.actions():
        if a.isSeparator(): continue
        text = a.text().replace('&', '').split('\t')[0]
        if not text: continue
        out.append('%s%s%s%s' % ('   ' * depth, text, '' if a.isEnabled() else '  (dimmed)', '  ›' if a.menu() else ''))
        if a.menu() is not None: lines(a.menu(), depth + 1, out, seen)
    return out
def region(wd):
    names = []; p_ = wd
    while p_ is not None:
        n = p_.objectName() or type(p_).__name__
        if n in ('TopBar2', 'TypeBar', 'CentreBar', 'ProjectDock', 'PaneBody', 'OperationsPanel', 'SlateFace', 'GraphiteField', 'WorkspaceTabs', 'TypeDock', 'CommandRibbon') or type(p_).__name__ in ('OfficePanel', 'PdfDocumentTab', 'DocumentsTab', 'InvestigationTab', 'FieldPage', 'TodayPage', 'FinderPage', 'ConcernDossier'): names.append(n if n not in ('PaneBody',) else type(p_).__name__)
        p_ = p_.parentWidget()
    return ' < '.join(names[:3]) or '?'
def controls(label):
    rows = {}
    for b in w.findChildren(QAbstractButton):
        if b.isVisible() and (b.text() or b.toolTip()):
            g = b.mapTo(w, QPoint(0, 0))
            if 0 <= g.x() <= w.width() and 0 <= g.y() <= w.height(): rows.setdefault(region(b), []).append((b.text() or '[' + b.toolTip()[:24] + ']') + ('' if b.isEnabled() else ' (dimmed)'))
    print('== ' + label)
    for k in sorted(rows): print('   %-44s %s' % (k[:44], ' | '.join(rows[k])[:400]))
for name in ('MoreMenus', 'BossPrograms', 'SystemMenu'):
    b = next((x for x in w.findChildren(QToolButton) if x.objectName() == name), None)
    m = b.menu() if b is not None and b.menu() is not None else None
    print('== top menu %s (%s): %s' % (name, b.text() if b else None, 'a QMenu' if m else 'no QMenu (its own list)'))
    if m is not None:
        for row in lines(m): print('   ' + row)
print('== window actions with a shortcut:', sorted({(a.text().replace('&', '').split('\t')[0], a.shortcut().toString()) for a in w.findChildren(QAction) if a.shortcut().toString() and a.text()})[:80])
w.show_start() if hasattr(w, 'show_start') else None; settle(300, 6); controls('Home')
w.a_field.trigger(); settle(); v = w.field_page.view; v.repaint(); settle(20, 2); controls('the Field in front')
print('   Field click places:', [words[:34] for b, k, tx, words in v._hot])
def open_tile(title):
    o = next((o for o in v.field.objects if o.title.startswith(title)), None)
    w.a_field.trigger(); settle(150, 4); v.field.select(o.id); v._describe(); QTest.keyClick(v, Qt.Key_Return); settle(900, 8); return w.tabs.currentWidget()
open_tile('07 Bench readings'); controls('a sheet open')
open_tile('07_Bench_Readings.pdf'); controls('a PDF open')
open_tile('07 Case conclusion'); controls('a page of writing open')
from workbench import chain_menu
m = chain_menu.root_menu(w); print('== what Actions ▾ opens now (the chain root):'); [print('   ' + r) for r in lines(m)[:40]]
