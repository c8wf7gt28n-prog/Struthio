"""The Menu key when the selected sheet is not (wholly) on screen."""
import os; os.environ['PROBE_W'] = '1366'; os.environ['PROBE_H'] = '768'
from winbase import *
from workbench import ledger_control
from workbench.engineering_kernel import operator
k = w.ledger_bridge.kernel; p = operator(); bridge = w.ledger_bridge
def ui_pt(points):
    row = next(r for r in ledger_control.settings(k)['settings'] if r['key'] == 'reading.ui_pt')
    if row['value'] != float(points):
        r = k.dispatch('ledger.settings.set', {'key': 'reading.ui_pt', 'value': float(points), 'expected_revision': row['revision']}, p); assert r['ok'], r
    bridge.sync_profile(force=True); settle(40, 3); align()
def menu_key(tag):
    w.activateWindow(); v.setFocus(); settle(10, 2); w.context_menu = None
    body = v._layout(); r = v.sheet_rect(v.field.selected, body); pt = v.selected_point()
    QTest.keyClick(v, Qt.Key_Menu); settle(50, 4); m = getattr(w, 'context_menu', None)
    print('   %-46s selected %r sheet y %.0f..%.0f, body y %.0f..%.0f | menu point (%d,%d) inside the body %s | menu for: %s | rows %s' % (
        tag, v.selected().title[:22], r.top(), r.bottom(), body.top(), body.bottom(), pt.x(), pt.y(), body.contains(QPointF(pt)), (m.target.label[:24], m.target.noun) if m is not None else None, m.words()[:3] if m is not None else None))
    if m is not None: m.close_menu() if hasattr(m, 'close_menu') else m.close()
    settle(10, 2)
v = field(); print('window active:', w.isActiveWindow(), '| view', v.width(), v.height())
QTest.keyClick(v, Qt.Key_Home); settle(5, 1); menu_key('14 pt, selection on screen')
for _ in range(4): QTest.keyClick(v, Qt.Key_PageDown)
settle(5, 1); menu_key('14 pt, after PageDown x4')
for _ in range(6): QTest.keyClick(v, Qt.Key_PageUp)
settle(5, 1); menu_key('14 pt, after PageUp x6')
ui_pt(28); settle(); v.setFocus()
for key, name in ((Qt.Key_Home, 'Home'), (Qt.Key_Left, 'Left'), (Qt.Key_Up, 'Up'), (Qt.Key_Up, 'Up'), (Qt.Key_Down, 'Down'), (Qt.Key_Right, 'Right')):
    QTest.keyClick(v, key); settle(5, 1); menu_key('28 pt, view %dx%d, after %s' % (v.width(), v.height(), name))
ui_pt(14); finish()
