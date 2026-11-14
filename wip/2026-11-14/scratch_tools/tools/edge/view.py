"""Reviewer probe: FieldView offscreen with awkward models."""
import os, sys, time, traceback
from pathlib import Path
os.environ.update(QT_QPA_PLATFORM='offscreen', PYTHONDONTWRITEBYTECODE='1')
PROGRAM = Path('/home/user/Struthio'); OUT = Path(__file__).parent / 'out'
sys.path.insert(0, str(PROGRAM)); sys.dont_write_bytecode = True
from PySide6.QtCore import QPoint, QPointF, Qt, QEvent
from PySide6.QtGui import QFontDatabase, QFont, QWheelEvent
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLineEdit, QPushButton
from PySide6.QtTest import QTest
app = QApplication([])
for f in (PROGRAM / 'branding/fonts/plex').glob('*.ttf'): QFontDatabase.addApplicationFont(str(f))
base = QFont('IBM Plex Sans'); base.setPixelSize(16); app.setFont(base)
from workbench.field_qt import FieldView
from workbench.field_model import Field, FieldObject as O, FieldLink as L
errors = []
def hook(kind, value, tb):
    errors.append(''.join(traceback.format_exception(kind, value, tb))[-900:])
sys.excepthook = hook
def paint(v, tag, save=None):
    n = len(errors); t0 = time.time(); img = v.grab(); dt = time.time() - t0
    if save: img.save(str(OUT / save))
    bad = errors[n:]
    print('  paint %-34s %4dx%-4d %.3fs %s' % (tag, v.width(), v.height(), dt, ('EXCEPTION: ' + bad[0].strip().splitlines()[-1]) if bad else 'ok'))
    return dt
def view(field, w=1368, h=900):
    v = FieldView(); v.resize(w, h); v.set_field(field); v.show(); v.setFocus(); app.processEvents(); return v
models = {
 'empty': Field(),
 'one': Field([O('a', 'source', 'A')]),
 'cycle3': Field([O('a', 'source', 'A'), O('b', 'sheet', 'B'), O('c', 'calculation', 'C')], [L('a', 'b'), L('b', 'c'), L('c', 'a')]),
 '200col': Field([O('s%d' % i, 'source', 'S%d' % i) for i in range(200)]),
 '12ranks': Field([O('n%d' % i, 'source', 'N%d' % i) for i in range(12)], [L('n%d' % i, 'n%d' % (i + 1), 'page 1', i % 2 == 0) for i in range(11)]),
 'texts': Field([O('a', 'source', 'x' * 300 + '.pdf', lines=tuple('fact %d' % i for i in range(40)), where='w' * 400),
                 O('b', 'sheet', '', state='recheck'), O('c', 'finding', '電源レールの起動時間は規定値を三十ミリ秒超過した。' * 3, state='held'),
                 O('d', 'question', 'مرحبا بالعالم ' * 12, state='open'), O('e', 'calculation', 'A title\nwith\ttabs and\nnewlines ' * 6, state='some_odd_state_word_that_is_long'),
                 O('f', 'document', 'T', state='')],
                [L('a', 'b', 'a very long wire label that cannot fit', True), L('b', 'e', ''), L('e', 'c'), L('c', 'd', 'x')]),
}
print('== paint each model at several sizes')
for name, f in models.items():
    for w, h in ((300, 200), (600, 400), (814, 600), (1368, 900), (3000, 1600), (40, 40), (1, 1)):
        v = view(f, w, h); paint(v, name); v.deleteLater()
print('== long unbroken titles: time for one paint')
for n in (300, 1000, 2000):
    f = Field([O('a', 'source', 'x' * n), O('b', 'sheet', 'B')], [L('a', 'b')])
    v = view(f); paint(v, 'unbroken title of %d chars' % n); v.deleteLater()
f = Field([O('a', 'finding', '電源レールの起動時間は規定値を三十ミリ秒超過した。' * 40), O('b', 'sheet', 'B')], [L('b', 'a')])
v = view(f); paint(v, 'CJK sentence x40 (1000 chars, no spaces)'); v.deleteLater()
for n in (4000,):
    f = Field([O('a', 'finding', ('word ' * n).strip()), O('b', 'sheet', 'B')], [L('b', 'a')])
    v = view(f); paint(v, 'title of %d words' % n); v.deleteLater()
paint(view(models['texts'], 1368, 700), 'texts', 'view_texts.png')

print('== tall column: first selection, reveal, scroll, hit-testing')
objs = [O('s%d' % i, 'source', 'Source %d' % i) for i in range(30)] + [O('q', 'question', 'An open question', state='open')]
f = Field(objs, [L('s29', 'q')])
v = view(f, 1000, 600); paint(v, 'tall')
body = v.body(); r = v.sheet_rect(v.field.selected)
print('  first selected:', v.field.selected, 'rect y %.0f..%.0f' % (r.top(), r.bottom()), 'body y %.0f..%.0f' % (body.top(), body.bottom()), 'scroll', v.scroll, 'surface', v._surface)
# select the last source by keyboard: Left follows the wire
QTest.keyClick(v, Qt.Key_Left); app.processEvents(); r = v.sheet_rect(v.field.selected)
print('  after Left:', v.field.selected, 'visible:', body.contains(r), 'scroll', round(v.scroll))
keep = v.field.selected; scroll_before = v.scroll
v.set_field(Field(list(objs), [L('s29', 'q')])); app.processEvents(); paint(v, 'after set_field (F9 again)'); r = v.sheet_rect(v.field.selected); body = v.body()
print('  after set_field with the same records: selected', v.field.selected, '(kept:', v.field.selected == keep, ') scroll', v.scroll, 'selected sheet visible:', body.intersects(r), 'rect y %.0f..%.0f' % (r.top(), r.bottom()))
# initial selection below the fold
objs2 = [O('s%d' % i, 'finding', 'Finding %d' % i) for i in range(30)]; objs2[25] = O('s25', 'finding', 'Needs recheck', state='recheck')
v2 = view(Field(objs2), 1000, 600); paint(v2, 'first() below the fold', 'view_first_below_fold.png'); r = v2.sheet_rect(v2.field.selected); body2 = v2.body()
print('  first() =', v2.field.selected, 'visible on first paint:', body2.intersects(r), 'rect y %.0f..%.0f body bottom %.0f' % (r.top(), r.bottom(), body2.bottom()))
# wheel bounds
def wheel(w, dy):
    pos = QPointF(w.width() / 2, w.height() / 2)
    ev = QWheelEvent(pos, w.mapToGlobal(pos), QPoint(0, 0), QPoint(0, dy), Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False)
    app.sendEvent(w, ev)
for dy in (-120, -120000, 120000, 120, -1, 0):
    wheel(v, dy); print('  wheel %7d -> scroll %.1f (max %.1f)' % (dy, v.scroll, v._surface - v.body().height()))
# hit-testing while scrolled
wheel(v, -2400); app.processEvents(); paint(v, 'scrolled'); body = v.body()
hits = 0; wrong = 0
for ident in v._placed:
    r = v.sheet_rect(ident, body)
    c = r.center()
    if not body.contains(c): continue
    got = v._hit(c); hits += 1
    if got != ident: wrong += 1; print('   hit mismatch', ident, got)
print('  hit-tests of visible centres while scrolled:', hits, 'wrong:', wrong)
# click on a sheet partly under the head: a point in the head must not select
top_ident = min((i for i in v._placed if v.sheet_rect(i, body).bottom() > body.top()), key=lambda i: v.sheet_rect(i, body).top())
r = v.sheet_rect(top_ident, body); print('  topmost partly-visible sheet', top_ident, 'y %.0f..%.0f head ends %.0f' % (r.top(), r.bottom(), body.top()), '| hit in head:', v._hit(QPointF(r.center().x(), body.top() - 3)), '| hit in foot:', v._hit(QPointF(r.center().x(), body.bottom() + 5)))
# real click + double click
opened = []; v.opened.connect(lambda o: opened.append(o.id))
target = next(i for i in v._placed if body.contains(v.sheet_rect(i, body)) and i != v.field.selected)
pt = v.sheet_rect(target, body).center().toPoint()
QTest.mouseClick(v, Qt.LeftButton, Qt.NoModifier, pt); print('  click selects:', v.field.selected == target, '| opened so far:', opened)
QTest.mouseDClick(v, Qt.LeftButton, Qt.NoModifier, pt); print('  double-click opens:', opened)
QTest.mouseDClick(v, Qt.RightButton, Qt.NoModifier, pt); print('  right double-click opens too:', opened)
QTest.mouseDClick(v, Qt.LeftButton, Qt.NoModifier, QPoint(500, 10)); print('  double-click on the head:', opened)

print('== keyboard')
left = []; v.left.connect(lambda: left.append(1))
v3 = view(Field(), 800, 500); o3 = []; l3 = []; v3.opened.connect(lambda o: o3.append(o)); v3.left.connect(lambda: l3.append(1))
for key in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down, Qt.Key_Home, Qt.Key_Tab, Qt.Key_Backtab, Qt.Key_Space, Qt.Key_A):
    QTest.keyClick(v3, key)
QTest.keyClick(v3, Qt.Key_Escape)
print('  empty field: opened', o3, 'left', l3, 'errors', len(errors))
# Tab with and without waiting objects, inside a window with other focusable widgets
def host(field):
    w = QWidget(); lay = QVBoxLayout(w); a = QLineEdit('before'); fv = FieldView(); fv.set_field(field); b = QPushButton('after'); lay.addWidget(a); lay.addWidget(fv, 1); lay.addWidget(b)
    w.resize(900, 600); w.show(); app.setActiveWindow(w) if hasattr(app, 'setActiveWindow') else None; w.activateWindow(); QTest.qWaitForWindowActive(w, 500); fv.setFocus(); app.processEvents(); return w, a, fv, b
calm = Field([O('a', 'source', 'A'), O('b', 'sheet', 'B')], [L('a', 'b')])
w, a, fv, b = host(calm); print('  no waiting objects: focus on view', fv.hasFocus())
QTest.keyClick(fv, Qt.Key_Tab); app.processEvents(); print('    Tab -> focus widget:', type(app.focusWidget()).__name__, getattr(app.focusWidget(), 'text', lambda: '')())
fv.setFocus(); QTest.keyClick(fv, Qt.Key_Backtab); app.processEvents(); print('    Shift+Tab -> focus widget:', type(app.focusWidget()).__name__, getattr(app.focusWidget(), 'text', lambda: '')())
waiting = Field([O('a', 'source', 'A'), O('b', 'sheet', 'B', state='recheck'), O('c', 'question', 'C', state='open')], [L('a', 'b'), L('b', 'c')])
w2, a2, fv2, b2 = host(waiting); seq = []
for _ in range(5):
    QTest.keyClick(fv2, Qt.Key_Tab); app.processEvents(); seq.append((fv2.field.selected, type(app.focusWidget()).__name__))
print('  two waiting objects: Tab x5 ->', seq)
seq = []
for _ in range(3):
    QTest.keyClick(fv2, Qt.Key_Backtab); app.processEvents(); seq.append((fv2.field.selected, type(app.focusWidget()).__name__))
print('    Shift+Tab x3 ->', seq)
one = Field([O('a', 'source', 'A'), O('c', 'question', 'C', state='open')], [L('a', 'c')])
w3, a3, fv3, b3 = host(one); seq = []
for _ in range(3):
    QTest.keyClick(fv3, Qt.Key_Tab); app.processEvents(); seq.append((fv3.field.selected, type(app.focusWidget()).__name__))
print('  one waiting object already selected: Tab x3 ->', seq, '(focus cannot leave by Tab or Shift+Tab)')
print('errors:', len(errors)); [print(e) for e in errors[:4]]
