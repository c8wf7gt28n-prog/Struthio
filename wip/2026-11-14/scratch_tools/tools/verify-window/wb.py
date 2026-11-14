"""New things in the real window on the worked case: (a) the rail, (b) staC from the Field, (d) the window put back exactly."""
from winbase import *
from PySide6.QtGui import QImage, QFontMetricsF
from PySide6.QtCore import QRectF
from workbench import context_menu, field_qt, field_page, boss_qt
from workbench.field_model import Field
from workbench.document_qt import show as show_document
from workbench.engineering_kernel import operator
k = w.ledger_bridge.kernel
def pick(v, test):
    ident = next(o.id for o in v.field.objects if test(o)); v.field.select(ident); v._layout(); v._reveal(); v._describe(); v.update(); settle(10, 2); return v.selected()
def shot(v):
    img = QImage(v.size(), QImage.Format_ARGB32); v.render(img); return img
def kb(): 
    a = app.focusWidget(); b = w.focusWidget(); return '%s (window focus widget %s, window active %s)' % (type(a).__name__ if a else None, type(b).__name__ if b else None, w.isActiveWindow())
docs = k.dispatch('documents.list', {}, operator())['result']['documents']
show_document(w, docs[0]['id']); settle(); where('a page is open'); before = snap()
v = field(); where('Field'); body = v._layout()
print('== (a) the rail at %dx%d, desk art %r' % (w.width(), w.height(), v.art_mode))
print('   view %dx%d scale %.2f rail %.0f body %.0fx%.0f surface %.0fx%.0f scroll x %.0f | without the rail the body would be %.0f wide -> the sheets would %s' % (
    v.width(), v.height(), v.scale(), v.rail(), body.width(), body.height(), v._surface[0], v._surface[1], v.scroll_x, v.width(), 'fit' if v._surface[0] <= v.width() else 'still not fit'))
rail_left = v.width() - v.rail(); s = v.scale()
keep = v.field; sel = keep.selected
v.field = Field(); bare = shot(v); v.field = keep; keep.select(sel)
worst_left = None; outside = 0; cols_cut = {}
for o in list(v.field.objects):
    v.field.select(o.id); v._layout(); v._reveal(); img = shot(v); body = v._layout()
    xs = [x for y in range(int(body.top()), int(body.bottom()), 2) for x in range(int(rail_left), v.width(), 2) if img.pixel(x, y) != bare.pixel(x, y)]
    if xs:
        worst_left = min(xs) if worst_left is None else min(worst_left, min(xs))
    cut = sum(1 for i in v._placed if v.sheet_rect(i, body).right() > body.right() + 0.5 or v.sheet_rect(i, body).left() < body.left() - 0.5)
    cols_cut[o.title[:20]] = cut
print('   over all 14 selections: pixels of the rail that differ from the rail alone start at x=%s (rail starts %.0f, the staC box starts %.0f) -> %s' % (
    worst_left, rail_left, rail_left + 10 * s, 'only the staC box is drawn over her' if worst_left is not None and worst_left >= rail_left + 10 * s - 2 else 'SOMETHING ELSE IS DRAWN IN THE RAIL'))
print('   sheets not wholly on screen sideways, per selection: min %d max %d of %d' % (min(cols_cut.values()), max(cols_cut.values()), len(v._placed)))
for mode in ('ascii', 'clean', 'illustrated'):
    boss_qt.choose_art(w, mode); settle(20, 2); body = v._layout(); img = shot(v)
    rows = {img.pixelColor(3, y).name() for y in range(v.head_height() + 2, v.head_height() + 14)}
    print('   desk art %-11s -> art_mode %-11s rail %.0f texture flag %s scan lines painted %s | body %.0f wide, sideways scroll room %.0f' % (mode, v.art_mode, v.rail(), v.texture, len(rows) > 1, body.width(), max(0, v._surface[0] - body.width())))
print('== (b) staC from the Field')
class Spy(QFontMetricsF):
    log = []
    def elidedText(self, text, mode, width, flags=0):
        out = super().elidedText(text, mode, width, flags); Spy.log.append((text, out)); return out
field_qt.QFontMetricsF = Spy
bad = []
for o in v.field.objects:
    v.field.select(o.id); v._layout(); v._reveal(); Spy.log.clear(); shot(v)
    want = v.stac_lines(o.stac); shown = ''.join(t.strip() for t, out in Spy.log).replace(' ', ''); cutl = [(t, out) for t, out in Spy.log if t != out and (t.startswith('|') or t in want or t.startswith('    '))]
    whole = all(line.replace(' ', '') in shown or True for line in want)
    joined = ''.join(l.replace(' ', '') for l in want)
    rail_lines = [t for t, out in Spy.log if t and (t == want[0][:len(t)] or t.startswith('|') or t.startswith('    '))]
    got = ''.join(l.replace(' ', '') for l in rail_lines)
    if joined not in got or cutl: bad.append((o.kind, o.title[:24], 'lines cut %d' % len(cutl), 'whole code shown: %s' % (joined in got)))
field_qt.QFontMetricsF = QFontMetricsF
print('   rail shows the whole staC line (stages as written, nothing cut) for %d of %d sheets%s' % (len(v.field.objects) - len(bad), len(v.field.objects), (' | not whole: %s' % bad[:4]) if bad else ''))
o = pick(v, lambda o: o.kind == 'calculation' and 'Startup' in o.title); print('   selected:', o.title, '| stac:', o.stac)
QTest.keyClick(v, Qt.Key_S); settle(); box = w.type_bar.box
print('   S -> writing strip holds exactly obj.stac: %s | Field in front: %s | writing line mode: %s | keyboard: %s | console.last_program: %r' % (box.text() == o.stac, w._field_active, w.type_target, kb(), getattr(w.console, 'last_program', None)))
popup = getattr(box, 'popup', None); print('   completion popup showing over the Field:', bool(popup is not None and popup.isVisible()))
QTest.keyClick(app.focusWidget() or box, Qt.Key_Escape); settle(); print('   Esc in the writing strip -> Field in front: %s | strip text: %r | keyboard: %s' % (w._field_active, box.text()[:40], kb()))
QTest.keyClick(app.focusWidget() or box, Qt.Key_Escape); settle(); where('   a second Esc'); print('      keyboard:', kb())
if not w._field_active: v = field()
box.clear(); v.setFocus(); settle(10, 2)
size0 = w.console.size_level
QTest.keyClick(v, Qt.Key_Return, Qt.ShiftModifier); settle(80, 8)
print('   Shift+Enter -> console.last_program == obj.stac: %s | Field in front: %s | keyboard: %s | working area size %s -> %s | status: %r' % (w.console.last_program == o.stac, w._field_active, kb(), size0, w.console.size_level, status()[:90]))
sel0 = v.field.selected; QTest.keyClick(app.focusWidget() or v, Qt.Key_Left); settle(10, 2); print('   next arrow key moves the selection in the Field:', v.field.selected != sel0, '->', v.selected().title)
QTest.keyClick(app.focusWidget() or v, Qt.Key_Right); settle(10, 2)
# refused: the Kernel refuses language.run
real = Kernel.dispatch
def refusing(self, operation, arguments=None, principal=None, *a, **kw):
    if operation == 'language.run': return {'ok': False, 'error': {'code': 'PROBE_REFUSED', 'message': 'probe: the Kernel refused this line'}}
    return real(self, operation, arguments, principal, *a, **kw)
last = w.console.last_program; n = len(errors)
with patch.object(Kernel, 'dispatch', refusing):
    QTest.keyClick(v, Qt.Key_Return, Qt.ShiftModifier); settle(80, 8)
print('   Shift+Enter, Kernel refuses -> status: %r | Field in front: %s | keyboard: %s | last_program kept: %s | uncaught: %d' % (status(), w._field_active, kb(), w.console.last_program == last, len(errors) - n))
print('      working area says:', [l for l in w.console.output.toPlainText().splitlines() if l.strip()][-2:])
sel0 = v.field.selected; QTest.keyClick(app.focusWidget() or v, Qt.Key_Up); settle(10, 2); print('      next arrow key moves the selection:', v.field.selected != sel0, '| focus widget:', type(app.focusWidget()).__name__)
# refused: a line staC itself cannot run
v.setFocus(); o = v.selected(); keep_stac = o.stac; o.stac = 'no.such.operation {"id":"x"} | pick nothing'; n = len(errors)
QTest.keyClick(v, Qt.Key_Return, Qt.ShiftModifier); settle(80, 8)
print('   Shift+Enter, a line staC cannot run -> status: %r | Field in front: %s | keyboard: %s | uncaught: %d' % (status(), w._field_active, kb(), len(errors) - n)); o.stac = keep_stac
print('== (d) the window put back')
v.setFocus(); QTest.keyClick(v, Qt.Key_Escape); settle(); where('Esc after Shift+Enter'); after = snap(); ch = diff(before, after, 'page -> Field -> S, Shift+Enter x3 -> Esc')
print('   working area size now:', w.console.size_level, '(was', size0, 'before Shift+Enter)')
w.console.set_size(size0); box.clear(); settle(); (w.tabs.currentWidget().focusProxy() or w.tabs.currentWidget()).setFocus(); settle(); base = snap()
v = field(); QTest.keyClick(v, Qt.Key_Escape); settle(); diff(base, snap(), 'page -> Field -> Esc (nothing else)')
v = field(); w.resize(1366, 768); settle(30, 3); w.resize(1920, 1200); settle(30, 3); QTest.keyClick(v, Qt.Key_Escape); settle(); diff(base, snap(), 'page -> Field -> resize and back -> Esc')
v = field(); QTest.keyClick(v, Qt.Key_N); settle(); QTest.keyClick(v, Qt.Key_W); settle(); QTest.keyClick(v, Qt.Key_R); settle(); QTest.keyClick(v, Qt.Key_Escape); settle(); diff(base, snap(), 'page -> Field -> N, W, R -> Esc')
w.show_start(); settle(); hb = snap(); v = field(); QTest.keyClick(v, Qt.Key_Return, Qt.ShiftModifier); settle(80, 6); v.setFocus(); QTest.keyClick(v, Qt.Key_Escape); settle(); where('Home -> Field -> Shift+Enter -> Esc'); diff(hb, snap(), 'Home -> Field -> Shift+Enter -> Esc')
finish()
