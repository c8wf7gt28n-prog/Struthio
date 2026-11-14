"""(e) at 28 pt: every Field action once, at 1920x1200 and 1366x768; nothing may raise (uncaught or contained in the paint)."""
import sys, traceback
sys.path.insert(0, '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/verify-window')
from rl_common import *
from PySide6.QtCore import QPoint, QPointF
from PySide6.QtGui import QContextMenuEvent
from workbench import field_qt, ledger_control, context_menu, boss_qt
from workbench.engineering_kernel import operator
errors = []; contained = []
sys.excepthook = lambda kind, value, tb: (errors.append(''.join(traceback.format_exception(kind, value, tb))), print('   !! UNCAUGHT:', repr(value)[:200]))
for name in ('_layout', '_texture', '_art', '_stac', '_head', '_empty', '_columns', '_ghosts', '_wires', '_sheet', '_wire_words', '_more', '_foot', '_reveal', 'selected_point', '_hit'):
    def wrap(real, name=name):
        def inner(self, *a, **kw):
            try: return real(self, *a, **kw)
            except Exception as exc:
                contained.append((name, repr(exc))); raise
        return inner
    setattr(field_qt.FieldView, name, wrap(getattr(field_qt.FieldView, name)))
open_window(); settle(50, 6)
k = w.ledger_bridge.kernel; p = operator(); bridge = w.ledger_bridge
def call(op, args=None):
    r = k.dispatch(op, args or {}, p); assert r['ok'], r; return r['result']
def ui_pt(points):
    row = next(r for r in ledger_control.settings(k)['settings'] if r['key'] == 'reading.ui_pt')
    if row['value'] != float(points): call('ledger.settings.set', {'key': 'reading.ui_pt', 'value': float(points), 'expected_revision': row['revision']})
    bridge.sync_profile(force=True); settle(40, 3); align()
ui_pt(28)
for size in ((1920, 1200), (1366, 768)):
    w.resize(*size); settle(30, 3); w.show_start(); settle(); w.a_field.trigger(); settle(); v = w.field_page.view; v.setFocus(); did = []
    for mode in ('ascii', 'clean', 'illustrated'): boss_qt.choose_art(w, mode); settle(10, 2); v.grab(); did.append('art ' + mode)
    for key in (Qt.Key_Left, Qt.Key_Up, Qt.Key_Down, Qt.Key_Right, Qt.Key_Home, Qt.Key_End, Qt.Key_PageDown, Qt.Key_PageUp, Qt.Key_A): QTest.keyClick(v, key); settle(5, 1); v.grab()
    did.append('arrows, Home, End, paging, A')
    QTest.keyClick(v, Qt.Key_Menu); settle(40, 3); m = getattr(w, 'context_menu', None); did.append('Menu key: %d rows' % len(m.words()) if m is not None else 'Menu key: no menu'); m and (m.close_menu() if hasattr(m, 'close_menu') else m.close()); settle(10, 2)
    body = v._layout(); spot = next((QPoint(x, y) for y in range(int(body.top()) + 8, int(body.bottom()) - 8, 7) for x in range(int(body.left()) + 4, int(body.right()) - 4, 7) if v._hit(QPointF(x, y)) is None), None)
    if spot is not None:
        app.sendEvent(v, QContextMenuEvent(QContextMenuEvent.Mouse, spot, v.mapToGlobal(spot))); settle(40, 3); m = w.context_menu; did.append('empty-place menu: %s' % m.words()[:3]); m.close_menu() if hasattr(m, 'close_menu') else m.close(); settle(10, 2)
    v.setFocus(); QTest.keyClick(v, Qt.Key_S); settle(); did.append('S: strip holds the line %s' % (w.type_bar.box.text() == v.selected().stac)); w.type_bar.box.clear(); pop = getattr(w.type_bar.box, 'popup', None); pop and pop.hide(); v.setFocus(); settle(10, 2)
    QTest.keyClick(v, Qt.Key_Return, Qt.ShiftModifier); settle(80, 6); did.append('Shift+Enter: ran %s, Field in front %s' % (w.console.last_program == v.selected().stac, w._field_active)); v.grab(); w.grab()
    v.setFocus(); QTest.keyClick(v, Qt.Key_N); settle(60, 4); v.grab(); did.append('N: %s' % v.field.census()[:2]); QTest.keyClick(v, Qt.Key_Down); QTest.keyClick(v, Qt.Key_W); settle(60, 4); v.grab()
    QTest.keyClick(v, Qt.Key_R); settle(); QTest.keyClick(v, Qt.Key_Return); settle(); did.append('Enter: %s in front' % type(w.tabs.currentWidget()).__name__); w.a_field.trigger(); settle(); QTest.keyClick(w.field_page.view, Qt.Key_Escape); settle()
    w.console.set_size(0); settle()
    print('%dx%d at 28 pt (view %dx%d, scale %.2f): %s' % (size[0], size[1], v.width(), v.height(), v.scale(), ' | '.join(did)))
    print('   uncaught: %d | drawing errors contained by the paint: %d %s' % (len(errors), len(contained), contained[:3]))
ui_pt(14); w._closing = True; print('DONE')
