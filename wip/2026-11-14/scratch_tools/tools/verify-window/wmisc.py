"""Follow-ups: where the keyboard is after Enter on a tab that exists; Home after paging; the key legend; the dock state after Shift+Enter."""
from winbase import *
from PySide6.QtGui import QFontMetricsF, QFont
from workbench.engineering_kernel import operator
from workbench.field_model import KIND_TAG
k = w.ledger_bridge.kernel
def kb():
    a = app.focusWidget(); return '%s' % (type(a).__name__ if a else None)
def pick(v, test):
    ident = next(o.id for o in v.field.objects if test(o)); v.field.select(ident); v._layout(); v._reveal(); v._describe(); v.update(); settle(10, 2); return v.selected()
def typed(tag):
    tab = w.tabs.currentWidget(); page = getattr(tab, 'page', None)
    if page is None: print('      %-44s keyboard %s (no text page in this room)' % (tag, kb())); return
    n = len(page.toPlainText()); QTest.keyClicks(app.focusWidget() or w, 'xyz'); settle(10, 2); m = len(page.toPlainText())
    print('      %-44s keyboard %-14s typing xyz -> %s' % (tag, kb(), 'arrives in the page' if m == n + 3 else 'GOES NOWHERE (page length %d -> %d)' % (n, m)))
print('== the keyboard after Enter')
v = field(); o = pick(v, lambda o: o.kind == 'document' and isinstance(o.target, dict) and o.target.get('kind') == 'document')
print('   object:', o.title)
QTest.keyClick(v, Qt.Key_Return); settle(); where('   Enter, no tab yet'); typed('new tab')
v = field(); QTest.keyClick(v, Qt.Key_Return); settle(); where('   Enter, its tab exists and is current'); typed('tab existed, was current')
w.a_files.trigger(); settle(); v = field(); QTest.keyClick(v, Qt.Key_Return); settle(); where('   Enter, its tab exists behind Files'); typed('tab existed, was behind')
w.a_files.trigger(); settle(); v = field(); pt = v.sheet_rect(v.field.selected, v._layout()).center().toPoint(); QTest.mouseDClick(v, Qt.LeftButton, Qt.NoModifier, pt); settle(); where('   double-click, its tab exists behind Files'); typed('double-click, tab was behind')
print('== Ctrl+W on the Field (two tabs)')
v = field(); QTest.keyClick(v, Qt.Key_W, Qt.ControlModifier); settle(); where('   Ctrl+W'); print('      keyboard:', kb(), '| window focus widget:', type(w.focusWidget()).__name__ if w.focusWidget() else None)
print('== Home / End after paging away')
w.resize(1366, 768); settle(30, 3); v = field(); v.setFocus(); body = v._layout()
QTest.keyClick(v, Qt.Key_Home); settle(5, 1); a = v._layout().contains(v.sheet_rect(v.field.selected)); s0 = v.field.selected
for _ in range(6): QTest.keyClick(v, Qt.Key_PageUp)
settle(5, 1); b = v._layout().intersects(v.sheet_rect(v.field.selected)); QTest.keyClick(v, Qt.Key_Home); settle(5, 1); c = v._layout().intersects(v.sheet_rect(v.field.selected))
print('   Home selects %r, on screen %s | PageUp x6 -> selected sheet on screen %s (scroll_y %.0f) | Home again (it is already the one) -> on screen %s' % (v.selected().title[:30], a, b, v.scroll_y, c))
QTest.keyClick(v, Qt.Key_End); settle(5, 1); e0 = v.field.selected
for _ in range(6): QTest.keyClick(v, Qt.Key_PageUp)
settle(5, 1); b = v._layout().intersects(v.sheet_rect(v.field.selected)); QTest.keyClick(v, Qt.Key_End); settle(5, 1); c = v._layout().intersects(v.sheet_rect(v.field.selected))
print('   End selects %r | PageUp x6 -> on screen %s | End again -> on screen %s' % (v.selected().title[:30], b, c))
QTest.keyClick(v, Qt.Key_Left); QTest.keyClick(v, Qt.Key_Right); settle(5, 1); print('   an arrow there and back -> on screen', v._layout().contains(v.sheet_rect(v.field.selected)))
print('== the key legend in the foot')
w.resize(1920, 1200); settle(30, 3); v = field(); s = v.scale(); fm = QFontMetricsF(v.mono(12)); x = 28 * s; wide = v.width() - 2 * x
keys = '← ↑ ↓ →  move      Enter  open      S  staC      Menu  more      A  next waiting      R  look again      Esc  back'
keys = '      '.join('%s  %s' % (letter.upper(), name) for name, letter in v.faces if name != v.face) + '      ' + keys
for o in v.field.objects:
    pass
shown = {}; 
for o in v.field.objects:
    tag = o.tag or KIND_TAG.get(o.kind, o.kind.upper())
    if o.state: tag += '  ·  ' + {'current': 'current', 'recheck': 'recheck', 'open': 'open', 'held': 'held'}.get(o.state, o.state).upper()
    shown[tag] = wide > fm.horizontalAdvance(keys) + QFontMetricsF(v.mono(12, QFont.Medium)).horizontalAdvance(tag) + 40 * s
print('   view %d wide at 1920x1200, legend %.0f px, room %.0f px: legend drawn per selected kind: %s' % (v.width(), fm.horizontalAdvance(keys), wide, shown))
print('   first selection when the Field opens:', v.field.get(v.field.first()).title, '->', 'legend drawn' if shown.get('OPEN QUESTION  ·  OPEN') else 'NO LEGEND')
old = '← ↑ ↓ →  move      Enter  open      Tab  next waiting      Esc  back'; fo = QFontMetricsF(v.mono(10.5))
print('   the legend as reviewed (63d9d2d) was %.0f px at this size: it was drawn for every kind: %s' % (fo.horizontalAdvance(old), all(wide > fo.horizontalAdvance(old) + fo.horizontalAdvance(tg) + 40 * s for tg in shown)))
for size in ((1600, 900), (1366, 768)):
    w.resize(*size); settle(30, 3); wide = v.width() - 2 * x
    print('   at %dx%d (view %d): legend drawn for %d of %d kinds of selection' % (size[0], size[1], v.width(), sum(wide > fm.horizontalAdvance(keys) + QFontMetricsF(v.mono(12, QFont.Medium)).horizontalAdvance(tg) + 40 * s for tg in shown), len(shown)))
w.resize(1920, 1200); settle(30, 3)
print('== the dock state after Shift+Enter')
QTest.keyClick(v, Qt.Key_Escape); settle(); before = snap(); size0 = w.console.size_level
v = field(); pick(v, lambda o: o.kind == 'calculation'); v.setFocus(); QTest.keyClick(v, Qt.Key_Return, Qt.ShiftModifier); settle(80, 6); v.setFocus(); QTest.keyClick(v, Qt.Key_Escape); settle()
after = snap(); diff(before, after, 'work -> Field -> Shift+Enter -> Esc'); print('   working area size', size0, '->', w.console.size_level)
w.console.set_size(size0); settle(); diff(before, snap(), 'the same after the working area is put back to its size')
finish()
