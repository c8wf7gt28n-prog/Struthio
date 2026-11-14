"""What is the row under the Field at 28 pt on 1366x768?"""
import sys
sys.path.insert(0, '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/verify-window')
from rl_common import *
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QWidget, QLabel, QAbstractButton
from workbench import ledger_control
from workbench.engineering_kernel import operator
open_window(); settle(50, 6)
k = w.ledger_bridge.kernel; p = operator(); bridge = w.ledger_bridge
def call(op, args=None):
    r = k.dispatch(op, args or {}, p); assert r['ok'], r; return r['result']
def ui_pt(points):
    row = next(r for r in ledger_control.settings(k)['settings'] if r['key'] == 'reading.ui_pt')
    if row['value'] != float(points): call('ledger.settings.set', {'key': 'reading.ui_pt', 'value': float(points), 'expected_revision': row['revision']})
    bridge.sync_profile(force=True); settle(40, 3); align()
def under(tag):
    v = w.field_page.view; page = w.field_page; c = w.centralWidget()
    rows = []
    for child in c.findChildren(QWidget, options=Qt.FindDirectChildrenOnly):
        if child.isVisible(): rows.append('%s#%s %dx%d at y=%d' % (type(child).__name__, child.objectName(), child.width(), child.height(), child.y()))
    below = w.childAt(v.mapTo(w, QPoint(v.width() // 2, v.height() + 30))); chain = []
    x = below
    while x is not None and x is not w and len(chain) < 6: chain.append('%s#%s' % (type(x).__name__, x.objectName())); x = x.parentWidget()
    words = [l.text()[:40] for l in (below.parentWidget() or below).findChildren(QLabel) if l.isVisible() and l.text()][:4] + [b.text()[:40] for b in (below.parentWidget() or below).findChildren(QAbstractButton) if b.isVisible() and b.text()][:4] if below is not None else []
    print('   %-34s view %dx%d | bars: context_bar %s doc_info %s workspace_status %s | console visible %s size %s | 30 px under the Field: %s %s' % (
        tag, v.width(), v.height(), w.context_bar.isVisible(), w.doc_info.isVisible(), w.workspace_status.isVisible(), w.console.isVisible(), w.console.size_level, ' < '.join(chain), words))
    print('      visible rows of the centre:', rows)
w.resize(1366, 768); settle(30, 3)
w.show_field(); settle(20, 3); under('Field at 14 pt')
for pts in (18, 20, 28):
    ui_pt(pts); under('after the text size is set to %d pt' % pts)
QTest.keyClick(w.field_page.view, Qt.Key_Escape); settle(); w.show_field(); settle(20, 3); under('Esc and F9 at 28 pt')
ui_pt(14); under('back at 14 pt')
w._closing = True; print('DONE')
