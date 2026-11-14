"""W4 contrast on receded sheets and the stale wire; W5 the marks per state, drawn at the size the view draws them."""
import json, os, sys, tempfile, itertools
from pathlib import Path
L = Path('/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/verify-window')
RUN = Path(tempfile.mkdtemp(prefix='view-', dir=str(L / 'run'))); HOME = RUN / 'home'; HOME.mkdir()
SCREEN = RUN / 'screen.json'
SCREEN.write_text(json.dumps({'screens': [{'name': 'shot', 'x': 0, 'y': 0, 'width': 1920, 'height': 1200, 'logicalDpi': 96, 'logicalBaseDpi': 96, 'dpr': 1.0}]}))
os.environ.update(PYTHONDONTWRITEBYTECODE='1', QT_QPA_PLATFORM='offscreen:configfile=' + str(SCREEN), ARC_LEDGER_EMBEDDED='1', ARC_LEDGER_DISABLE_BOOK_WATCHER='1',
                  HOME=str(HOME), ARC1_WORKBENCH_CONFIG_HOME=str(RUN / 'profile'), ARC_LEDGER_CONCERN=str(HOME / 'Concern'))
os.chdir(RUN); sys.path.insert(0, '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/wt'); sys.dont_write_bytecode = True
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QImage, QFont, QColor, QPainter
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLineEdit
from PySide6.QtTest import QTest
from workbench.qt_app import make_app
app = make_app([])
from workbench.field_model import Field, FieldObject, FieldLink, STATE_OPEN, STATE_RECHECK, STATE_HELD, STATE_CURRENT, ATTENTION, SETTLED
from workbench.field_qt import FieldView, WORD_INK, ink
from workbench import boss_theme as t
def host(view, w=1366, h=1078, px=19):
    box = QWidget(); lay = QVBoxLayout(box); lay.addWidget(view); f = QFont(box.font()); f.setPixelSize(px); view.setFont(f); box.resize(w, h); box.show(); app.processEvents(); QTest.qWaitForWindowExposed(box); return box
def lum(c):
    def f(x):
        x /= 255.0; return x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(c.red()) + 0.7152 * f(c.green()) + 0.0722 * f(c.blue())
def ratio(a, b):
    hi, lo = max(lum(a), lum(b)), min(lum(a), lum(b)); return (hi + 0.05) / (lo + 0.05)
def over(colour, alpha, ground):
    c, g = QColor(colour), QColor(ground); return QColor(round(c.red() * alpha + g.red() * (1 - alpha)), round(c.green() * alpha + g.green() * (1 - alpha)), round(c.blue() * alpha + g.blue() * (1 - alpha)))
print('== W4 by the theme\'s own numbers: every ink a sheet uses, at each step from the selection, on that step\'s ground')
grounds = (t.CARD, t.CARD, t.PANEL, t.GROUND)
for depth in range(4):
    keep = WORD_INK[depth]; g = QColor(grounds[depth]); row = []
    for name, colour, a in (('title TEXT', t.TEXT, keep), ('tag/fact QUIET', t.QUIET, keep), ('question tag AMBER_TEXT', t.AMBER_TEXT, keep), ('identity ' + ('FAINT' if depth <= 1 else 'QUIET'), t.FAINT if depth <= 1 else t.QUIET, keep),
                            ('settled word READY', t.READY, keep), ('waiting word AMBER_EDGE', t.AMBER_EDGE, max(keep, 0.85)), ('quiet word QUIET', t.QUIET, keep)):
        row.append('%s %.2f' % (name, ratio(over(colour, a, g), g)))
    print('   step %d ground %s keep %.2f: %s' % (depth, g.name(), keep, ' | '.join(row)))
print('== W4 measured: a sheet three steps away, painted')
for texture in (False, True):
    objs = [FieldObject('s', 'source', 'S.pdf'), FieldObject('t', 'sheet', 'T'), FieldObject('c', 'calculation', 'C'), FieldObject('f', 'finding', 'Selected finding'),
            FieldObject('far', 'sheet', 'MMMMMMMMMM HHHHHH', 'sheet', STATE_CURRENT, ('HHHHHHHH MMMMMMMM',), 'MMMMMMMM.HHH'), FieldObject('x', 'source', 'X.pdf'), FieldObject('y', 'calculation', 'Y', state=STATE_RECHECK),
            FieldObject('u', 'sheet', 'HHHH MMMM', 'sheet', 'unavailable', ('MMMM HHHH',), 'HHH.MMM')]
    links = [FieldLink('s', 't'), FieldLink('t', 'c'), FieldLink('c', 'f'), FieldLink('x', 'far'), FieldLink('far', 'y', '', True), FieldLink('x', 'u')]
    v = FieldView(); box = host(v); f = Field(objs, links); f.select('f'); v.set_field(f); v.texture = texture; app.processEvents(); img = QImage(v.size(), QImage.Format_ARGB32); v.render(img)
    body = v._layout(); depths = v.field.depth(); s = v.scale(); pad = 12 * s
    def brightest(x0, y0, x1, y1, start):
        best = start
        for y in range(int(y0), int(y1)):
            for x in range(int(x0), int(x1)):
                c = img.pixelColor(x, y)
                if lum(c) > lum(best): best = c
        return best
    for ident in ('far', 'u'):
        r = v.sheet_rect(ident, body); ground = img.pixelColor(int(r.left() + 4), int(r.bottom() - 4))
        tag = brightest(r.left() + pad, r.top() + pad - 2 * s, r.left() + r.width() * 0.4, r.top() + pad + 14 * s, ground)
        word = brightest(r.left() + r.width() * 0.55, r.top() + pad - 2 * s, r.right() - pad, r.top() + pad + 14 * s, ground)
        title = brightest(r.left() + pad, r.top() + pad + 20 * s, r.right() - pad, r.top() + pad + 40 * s, ground)
        fact = brightest(r.left() + pad, r.top() + pad + 20 * s + 2 * 24 * s, r.right() - pad, r.bottom() - pad - 22 * s, ground)
        where = brightest(r.left() + pad, r.bottom() - pad - 14 * s, r.right() - pad, r.bottom() - 4 * s, ground)
        print('   texture %-5s sheet %-3s (step %d, state %s) on screen %s ground %s | kind %.2f | state word+mark %.2f | title %.2f | fact %.2f | identity %.2f' % (
            texture, ident, depths[ident], v.field.get(ident).state, body.contains(r), ground.name(), ratio(tag, ground), ratio(word, ground), ratio(title, ground), ratio(fact, ground), ratio(where, ground)))
    a = v.sheet_rect('far', body); b = v.sheet_rect('y', body); bg = QColor(t.TERMINAL_GROUND)
    x0, x1 = int(a.right() + 6), int(b.left() - 6); wire = None; base = None
    for y in range(int(min(a.top(), b.top())), int(max(a.bottom(), b.bottom()))):
        for x in range(x0, x1):
            c = img.pixelColor(x, y)
            if base is None or lum(c) < lum(base): base = c
            if wire is None or lum(c) > lum(wire): wire = c
    nominal = over(t.AMBER_EDGE, 0.95, bg)
    print('   texture %-5s stale wire far from the selection (steps %d and %d), between x %d and %d: brightest pixel %s on darkest ground there %s = %.2f:1 ; against the bare ground %s = %.2f:1 ; nominal ink %s = %.2f:1' % (
        texture, depths['far'], depths['y'], x0, x1, wire.name(), base.name(), ratio(wire, base), bg.name(), ratio(wire, bg), nominal.name(), ratio(nominal, bg)))
    ok = FieldLink('x', 'far'); xa = v.sheet_rect('x', body); wire2 = None
    for y in range(int(min(a.top(), xa.top())), int(max(a.bottom(), xa.bottom()))):
        for x in range(int(xa.right() + 6), int(a.left() - 6)):
            c = img.pixelColor(x, y)
            if wire2 is None or lum(c) > lum(wire2): wire2 = c
    print('      for comparison an ordinary wire far from the selection: %s = %.2f:1' % (wire2.name(), ratio(wire2, bg)))
    img.save(str(L / ('out/contrast_texture_%s.png' % texture))); box.close()
print('== W5 the marks, as drawn (8 px at the default size; 1 = ink)')
v = FieldView(); states = ['current', 'recheck', 'open', 'held', 'waiting', 'paused', 'failed', 'interrupted', 'unavailable', 'not read', 'down', 'odd word']
masks = {}
for scale_px in (16, 19):
    f = QFont(v.font()); f.setPixelSize(scale_px); v.setFont(f); mark = 8 * v.scale(); size = int(mark) + 6
    for st in states:
        img = QImage(size, size, QImage.Format_ARGB32); img.fill(QColor('#000000')); p = QPainter(img); p.setRenderHint(QPainter.Antialiasing)
        v._mark(p, QRectF(3, 3, mark, mark), st, QColor('#ffffff')); p.end()
        masks[(scale_px, st)] = tuple(tuple(1 if img.pixelColor(x, y).red() > 110 else 0 for x in range(size)) for y in range(size))
    if scale_px == 16:
        for row in range(size):
            print('   ' + '   '.join(''.join('#' if c else '.' for c in masks[(16, st)][row]) for st in ('current', 'recheck', 'open', 'held', 'waiting', 'failed', 'unavailable', 'not read')))
        print('   ' + '   '.join(('%-' + str(size) + 's') % st[:size] for st in ('current', 'recheck', 'open', 'held', 'waiting', 'failed', 'unavail', 'not read')))
    same = []; close = []
    for a, b in itertools.combinations(states, 2):
        d = sum(x != y for ra, rb in zip(masks[(scale_px, a)], masks[(scale_px, b)]) for x, y in zip(ra, rb))
        if d == 0: same.append((a, b))
        elif d < 6: close.append((a, b, d))
    print('   at %d px text (mark %.1f px): identical marks %s | differ by fewer than 6 pixels %s' % (scale_px, mark, same, close))
# on a narrow sheet: does the mark stay when the word gives way?
from workbench import field_qt
objs = [FieldObject('a%d' % i, 'question' if st == 'open' else 'document', 'T', state=st, tag='WRITING NOTE') for i, st in enumerate(('recheck', 'open', 'held', 'unavailable', 'not read'))]
v2 = FieldView(); box = host(v2, 400, 1000, 16); v2.set_field(Field(objs)); app.processEvents(); body = v2._layout()
img = QImage(v2.size(), QImage.Format_ARGB32); v2.render(img); img.save(str(L / 'out/narrow_marks.png'))
p0 = next(iter(v2._placed.values())); print('   narrow sheets %.0f px wide at 16 px text; saved out/narrow_marks.png' % p0.w)
print('DONE')
