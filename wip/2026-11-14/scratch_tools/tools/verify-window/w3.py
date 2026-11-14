"""W3 again: reading sizes 14/18/20/28 pt at 1920x1200 and 1366x768 in the real window: elided share, sheet size, both-way scroll, keyboard reach."""
import sys, copy, traceback
sys.path.insert(0, '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/verify-window')
from rl_common import *
from PySide6.QtCore import QRectF, QPointF
from PySide6.QtGui import QFontMetricsF, QImage, QPainter
from workbench import field_page, field_qt, ledger_control
from workbench.engineering_kernel import operator
import workbench.field_page as _fp; print('program under test:', Path(_fp.__file__).parent.parent)
errors = []
sys.excepthook = lambda kind, value, tb: (errors.append(''.join(traceback.format_exception(kind, value, tb))), print('   !! UNCAUGHT:', value))
contained = []
for name in ('_layout', '_texture', '_art', '_stac', '_head', '_empty', '_columns', '_ghosts', '_wires', '_sheet', '_wire_words', '_more', '_foot'):
    def wrap(real, name=name):
        def inner(self, *a, **kw):
            try: return real(self, *a, **kw)
            except Exception as exc:
                contained.append((name, repr(exc))); raise
        return inner
    setattr(field_qt.FieldView, name, wrap(getattr(field_qt.FieldView, name)))
open_window(); settle(50, 6)
k = w.ledger_bridge.kernel; p = operator(); bridge = w.ledger_bridge
OUT = L / 'out/access'; OUT.mkdir(parents=True, exist_ok=True)
w.show_field(); settle(20, 3); v = w.field_page.view
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
def path_to(field, start, goal):
    """Shortest list of keys (arrows, Home, End) that takes the model's selection from start to goal."""
    seen = {start: []}; edge = [start]
    while edge:
        nxt = []
        for ident in edge:
            for key, how in (('left', Qt.Key_Left), ('right', Qt.Key_Right), ('up', Qt.Key_Up), ('down', Qt.Key_Down)):
                f = copy.copy(field); f.selected = ident; got = f.move(key)
                if got not in seen: seen[got] = seen[ident] + [how]; nxt.append(got)
        edge = nxt
    return seen.get(goal)
summary = []
for size in ((1920, 1200), (1366, 768)):
    w.resize(*size); settle(30, 3)
    for points in (14, 18, 20, 28):
        n_err, n_con = len(errors), len(contained)
        ui_pt(points)
        if not w._field_active: w.a_field.trigger()
        settle(30, 3); align(); v.setFocus(); settle(10, 2)
        ident = next(o.id for o in v.field.objects if o.title.startswith('Startup ran')); v.field.select(ident); v._layout(); v._reveal(); v._describe(); v.update(); settle(10, 2)
        Spy.log.clear(); fonts.clear(); img = QImage(v.size(), QImage.Format_ARGB32); v.render(img)
        seen_log = list(Spy.log); cut_seen = [(t, o) for t, o in seen_log if o != t]
        body = v._layout(); place = next(iter(v._placed.values())); depth = v.field.depth()
        # every sheet, drawn on its own (the view only paints what is on screen)
        Spy.log.clear(); scratch = QImage(int(place.w) + 4, int(place.h) + 4, QImage.Format_ARGB32); qp = QPainter(scratch)
        for o in v.field.objects: v._sheet(qp, o, QRectF(1, 1, place.w, place.h), depth.get(o.id, 3))
        qp.end(); sheet_log = list(Spy.log); cut_sheet = [(t, o) for t, o in sheet_log if o != t]; drawn = {t for t, o in sheet_log}
        facts = [str(f) for o in v.field.objects for f in o.lines[:2]]; facts_missing = [f for f in facts if f not in drawn]
        wheres_missing = [o.where for o in v.field.objects if o.where and str(o.where) not in drawn]
        # keyboard alone: walk to every sheet from the current one with the arrows; is it then on screen?
        whole = part = lost = unreachable = 0; worst = 1.0
        for o in v.field.objects:
            keys = path_to(v.field, v.field.selected, o.id)
            if keys is None: unreachable += 1; continue
            for key in keys: QTest.keyClick(v, key)
            settle(5, 1); body = v._layout(); r = v.sheet_rect(o.id, body)
            assert v.field.selected == o.id, (o.title, v.selected().title)
            inter = r.intersected(body); share = (inter.width() * inter.height()) / (r.width() * r.height()) if inter.isValid() else 0.0; worst = min(worst, share)
            if body.contains(r): whole += 1
            elif share > 0.5: part += 1
            else: lost += 1
        v.field.select(ident); v._layout(); v._reveal(); v.update(); settle(5, 1)
        body = v._layout(); total = len(v.field.objects)
        line = ('%dx%d ui %2d pt: view %dx%d font %dpx scale %.2f rail %.0f | body %.0fx%.0f sheet %.0fx%.0f surface %.0fx%.0f (%s) | fonts px %s\n'
                '      as seen (selected finding, one screen): %d of %d strings cut (%.0f%%)\n'
                '      all %d sheets drawn one by one: %d of %d strings cut (%.0f%%); facts not drawn %d of %d; identity lines not drawn %d\n'
                '      keyboard alone (arrows): wholly on screen %d, more than half %d, half or less %d, unreachable %d of %d; least share shown %.0f%%; new uncaught %d, contained drawing errors %d' % (
            size[0], size[1], points, v.width(), v.height(), v.fontInfo().pixelSize(), v.scale(), v.rail(), body.width(), body.height(), place.w, place.h, v._surface[0], v._surface[1],
            ' and '.join(x for x in ('scrolls sideways' if v._surface[0] > body.width() + 1 else '', 'scrolls down' if v._surface[1] > body.height() + 1 else '') if x) or 'fits', sorted(set(fonts.values())),
            len(cut_seen), len(seen_log), 100.0 * len(cut_seen) / max(1, len(seen_log)),
            total, len(cut_sheet), len(sheet_log), 100.0 * len(cut_sheet) / max(1, len(sheet_log)), len(facts_missing), len(facts), len(wheres_missing),
            whole, part, lost, unreachable, total, worst * 100, len(errors) - n_err, len(contained) - n_con))
        print(line)
        for t, o in cut_sheet[:6]: print('         sheet: %r -> %r' % (t[:60], o[:60]))
        for t, o in [c for c in cut_seen if c not in cut_sheet][:4]: print('         head/foot/rail: %r -> %r' % (t[:70], o[:70]))
        align(); w.grab().save(str(OUT / ('field_%dx%d_%02dpt.png' % (size[0], size[1], points))), 'PNG')
        # PageDown / PageUp / End / Home
        y0 = v.scroll_y; QTest.keyClick(v, Qt.Key_PageDown); settle(5, 1); y1 = v.scroll_y; QTest.keyClick(v, Qt.Key_PageUp); settle(5, 1); y2 = v.scroll_y
        QTest.keyClick(v, Qt.Key_End); settle(5, 1); e = v.selected().title[:24]; ev = v._layout().contains(v.sheet_rect(v.field.selected)); QTest.keyClick(v, Qt.Key_Home); settle(5, 1); h = v.selected().title[:24]; hv = v._layout().intersects(v.sheet_rect(v.field.selected))
        print('      PageDown scroll_y %.0f -> %.0f, PageUp -> %.0f | End selects %r (wholly visible %s) | Home selects %r (on screen %s)' % (y0, y1, y2, e, ev, h, hv))
ui_pt(14)
print('uncaught:', len(errors), '| contained drawing errors:', contained[:5])
for e in errors[:3]: print(e[-600:])
w._closing = True; print('DONE')
