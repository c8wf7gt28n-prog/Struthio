import sys, time, json, os
sys.path.insert(0, '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/rules-lens')
from common import *
from PySide6.QtGui import QAction, QShortcut, QKeySequence, QFontMetricsF, QImage
from PySide6.QtWidgets import QApplication
from workbench import field_page, field_qt, menus2, ledger_control, boss_qt
from workbench.engineering_kernel import operator
open_window(); settle(50, 10)
k = w.ledger_bridge.kernel; p = operator(); bridge = w.ledger_bridge
OUT = L / 'out/access'; OUT.mkdir(parents=True, exist_ok=True)
print('=== A. menus and F9')
f9 = [a for a in w.findChildren(QAction) if any(s.toString() == 'F9' for s in a.shortcuts())]
print('QActions bound to F9 in the window:', [(a.text(), a.shortcutContext().name) for a in f9], '| QShortcuts on F9:', [s for s in w.findChildren(QShortcut) if s.key().toString() == 'F9'])
ident = id(w.a_field); menu = w.menu_groups['Options']; menu_id = id(menu)
for n in range(2): menus2.rebuild(w); settle(10, 2)
acts = w.menu_groups['Options'].actions()
print('after two rebuilds: same QAction %s, same QMenu %s, times in Arrange %d, times in all menus %s, in window actions %d' % (
    id(w.a_field) == ident, id(w.menu_groups['Options']) == menu_id, sum(1 for a in acts if a is w.a_field),
    {name: sum(1 for a in m.actions() if a is w.a_field) for name, m in w.menu_groups.items()}, sum(1 for a in w.actions() if a is w.a_field)))
names = [a.text().replace('&', '') or '—' for a in acts]; at = acts.index(w.a_field); print('Arrange rows around it:', names[max(0, at - 2):at + 3], '| menu title:', w.menu_groups['Options'].title())
# F9 from several focus places
def press_f9(tag, widget):
    field_page.leave_field(w); settle(10, 2)
    if widget is not None: widget.setFocus(); settle(10, 2)
    QTest.keyClick(app.focusWidget() or w, Qt.Key_F9); settle(20, 3)
    print('   F9 with focus in %-26s -> field showing: %s, focus now: %s' % (tag, w._field_active, type(app.focusWidget()).__name__))
press_f9('window (nothing special)', None)
box = getattr(getattr(getattr(w, 'shell2', None), 'top', None), 'box', None)
press_f9('the writing line', box)
press_f9('navigator', getattr(w, 'tree', None) or getattr(w, 'nav', None))
print('=== B. keyboard alone')
w.show_field(); settle(20, 3); v = w.field_page.view
def keys(tag, key, mod=Qt.NoModifier):
    before = v.field.selected; QTest.keyClick(app.focusWidget() or v, key, mod); settle(10, 2)
    print('   %-12s selected %s -> %s | focus: %s | field showing: %s' % (tag, v.field.get(before).title[:28] if before else None, v.selected().title[:28] if v.selected() else None, type(app.focusWidget()).__name__, w._field_active))
print('waiting objects:', sum(1 for o in v.field.objects if o.needs_attention()))
keys('Tab', Qt.Key_Tab); keys('Tab', Qt.Key_Tab); keys('Shift+Tab', Qt.Key_Backtab, Qt.ShiftModifier)
keys('Left', Qt.Key_Left); keys('Tab', Qt.Key_Tab); keys('PageDown', Qt.Key_PageDown); keys('End', Qt.Key_End); keys('Home', Qt.Key_Home); keys('Space', Qt.Key_Space)
print('accessible name: %r' % v.accessibleName()); seen = set()
for key in (Qt.Key_Left, Qt.Key_Left, Qt.Key_Up, Qt.Key_Left, Qt.Key_Down):
    QTest.keyClick(v, key); settle(5, 1); d = v.accessibleDescription()
    if d not in seen: seen.add(d); print('   description: %r' % d)
print('=== C. Clean desk art while the Field is showing')
print('texture flag as shown:', v.texture, '| desk_art:', w.session.state.get('desk_art', 'illustrated'))
def body_shot():
    img = QImage(v.size(), QImage.Format_ARGB32); v.render(img); return img
def rows_differ(img):  # scan lines: do two neighbouring blank rows at the far left edge differ?
    x = 3; ys = range(v.head_height() + 2, v.head_height() + 14); return len({img.pixelColor(x, y).name() for y in ys}) > 1
print('scan texture painted now:', rows_differ(body_shot()))
boss_qt.choose_art(w, 'clean'); settle(20, 3)
print('after choosing Clean with the Field still showing: texture flag %s, scan texture painted %s' % (v.texture, rows_differ(body_shot())))
w.a_field.trigger(); settle(20, 3); print('after showing the Field again: texture flag %s, scan texture painted %s' % (v.texture, rows_differ(body_shot())))
boss_qt.choose_art(w, 'illustrated'); w.a_field.trigger(); settle(20, 3)
print('=== D. reading sizes')
class Spy(QFontMetricsF):
    log = []
    def elidedText(self, text, mode, width, flags=0):
        out = super().elidedText(text, mode, width, flags); Spy.log.append((text, out)); return out
field_qt.QFontMetricsF = Spy
fonts = {}
real_mono, real_sans = field_qt.FieldView.mono, field_qt.FieldView.sans
def mono(self, px, weight=None):
    f = real_mono(self, px, weight) if weight is not None else real_mono(self, px); fonts[('mono', px)] = f.pixelSize(); return f
def sans(self, px, weight=None):
    f = real_sans(self, px, weight) if weight is not None else real_sans(self, px); fonts[('sans', px)] = f.pixelSize(); return f
field_qt.FieldView.mono = mono; field_qt.FieldView.sans = sans
def call(op, args=None):
    r = k.dispatch(op, args or {}, p); assert r['ok'], r; return r['result']
def ui_pt(points):
    row = next(r for r in ledger_control.settings(k)['settings'] if r['key'] == 'reading.ui_pt')
    if row['value'] != float(points): call('ledger.settings.set', {'key': 'reading.ui_pt', 'value': float(points), 'expected_revision': row['revision']})
    bridge.sync_profile(force=True); settle(40, 3); align()
for size in ((1920, 1200), (1366, 768)):
    w.resize(*size); settle(30, 3)
    for points in (14, 18, 20, 28):
        ui_pt(points); w.a_field.trigger(); settle(30, 3); align()
        ident = next(o.id for o in v.field.objects if o.title.startswith('Startup ran')); v.field.select(ident); v._describe(); v.update(); settle(10, 2)
        Spy.log.clear(); fonts.clear(); img = QImage(v.size(), QImage.Format_ARGB32); v.render(img)
        cut = [(t, o) for t, o in Spy.log if o != t]
        titles = {o.title for o in v.field.objects}; drawn = {t for t, o in Spy.log}
        facts = [f for o in v.field.objects for f in o.lines]; facts_missing = [f for f in facts if f not in drawn]
        wheres_missing = [o.where for o in v.field.objects if o.where and o.where not in drawn]
        place = next(iter(v._placed.values())); body = v.body()
        print('%dx%d ui %2d pt: view %dx%d font %dpx scale %.2f | sheet %.0fx%.0f, gap %.0f, surface %.0f vs body %.0f (%s) | fonts px: %s' % (
            size[0], size[1], points, v.width(), v.height(), v.fontInfo().pixelSize(), v.scale(), place.w, place.h, v._gap, v._surface, body.height(),
            'scrolls' if v._surface > body.height() + 1 else 'fits', sorted(set(fonts.values()))))
        print('      strings cut with an ellipsis: %d of %d drawn; facts not drawn at all: %d of %d; identity lines not drawn: %d' % (len(cut), len(Spy.log), len(facts_missing), len(facts), len(wheres_missing)))
        for t, o in cut[:40]: print('         %r -> %r' % (t[:70], o[:70]))
        align(); w.grab().save(str(OUT / ('field_%dx%d_%02dpt.png' % (size[0], size[1], points))), 'PNG'); img.save(str(OUT / ('view_%dx%d_%02dpt.png' % (size[0], size[1], points))))
ui_pt(14)
# ui_fit cannot see painted words
sys.path.insert(0, str(PROGRAM / 'tools')); import ui_fit
w.a_field.trigger(); settle(20, 3)
print('ui_fit.whole_words(field view) findings:', ui_fit.whole_words(v), '| widgets it can measure under the view:', len(v.findChildren(object)))
w._closing = True; print('DONE')
