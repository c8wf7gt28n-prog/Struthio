"""Standalone view probes (no window, no kernel): Tab with nothing waiting, first selection below the fold, sideways overflow, measured contrast."""
import json, os, sys, tempfile
from pathlib import Path
L = Path('/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/rules-lens')
RUN = Path(tempfile.mkdtemp(prefix='view-', dir=str(L / 'run'))); HOME = RUN / 'home'; HOME.mkdir()
SCREEN = RUN / 'screen.json'
SCREEN.write_text(json.dumps({'screens': [{'name': 'shot', 'x': 0, 'y': 0, 'width': 1920, 'height': 1200, 'logicalDpi': 96, 'logicalBaseDpi': 96, 'dpr': 1.0}]}))
os.environ.update(PYTHONDONTWRITEBYTECODE='1', QT_QPA_PLATFORM='offscreen:configfile=' + str(SCREEN), ARC_LEDGER_EMBEDDED='1', ARC_LEDGER_DISABLE_BOOK_WATCHER='1',
                  HOME=str(HOME), ARC1_WORKBENCH_CONFIG_HOME=str(RUN / 'profile'), ARC_LEDGER_CONCERN=str(HOME / 'Concern'))
os.chdir(RUN); sys.path.insert(0, '/home/user/Struthio'); sys.dont_write_bytecode = True
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QFont, QColor
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLineEdit
from PySide6.QtTest import QTest
from workbench.qt_app import make_app
app = make_app([])
from workbench.field_model import Field, FieldObject, FieldLink, STATE_OPEN, STATE_RECHECK, STATE_HELD, STATE_CURRENT
from workbench.field_qt import FieldView
from workbench import boss_theme as t
def host(view, w=1366, h=1078, px=19):
    box = QWidget(); lay = QVBoxLayout(box); before = QLineEdit(); after = QLineEdit(); lay.addWidget(before); lay.addWidget(view); lay.addWidget(after)
    f = QFont(box.font()); f.setPixelSize(px); view.setFont(f); box.resize(w, h); box.show(); app.processEvents(); QTest.qWaitForWindowExposed(box); return box, before, after
# 1. Tab with nothing waiting / with one thing waiting
for waiting in (0, 1):
    objs = [FieldObject('a', 'source', 'A.pdf'), FieldObject('b', 'sheet', 'B'), FieldObject('c', 'question', 'Why?', state=STATE_OPEN if waiting else STATE_CURRENT)]
    v = FieldView(); v.set_field(Field(objs, [FieldLink('a', 'b')])); box, before, after = host(v); box.activateWindow(); v.setFocus(); app.processEvents()
    QTest.keyClick(v, Qt.Key_Tab); app.processEvents(); one = type(app.focusWidget()).__name__ if app.focusWidget() else None
    v.setFocus(); app.processEvents(); QTest.keyClick(v, Qt.Key_Backtab, Qt.ShiftModifier); app.processEvents(); two = type(app.focusWidget()).__name__ if app.focusWidget() else None
    print('waiting=%d: after Tab focus is on %s; after Shift+Tab focus is on %s' % (waiting, one, two)); box.close()
# 2. the first selection (what needs the owner) below the fold when the Field opens
objs = [FieldObject('f%02d' % i, 'finding', 'Finding %02d' % i) for i in range(30)]; objs[27] = FieldObject('f27', 'finding', 'Finding 27 must be rechecked', state=STATE_RECHECK)
v = FieldView(); box, _, _ = host(v); v.set_field(Field(objs, [])); app.processEvents(); img = QImage(v.size(), QImage.Format_ARGB32); v.render(img)
r = v.sheet_rect(v.field.selected, v._layout()); body = v.body()
print('opened on: %s | its sheet y %.0f..%.0f, body y %.0f..%.0f, scroll %.0f -> visible when the Field opens: %s' % (v.selected().title, r.top(), r.bottom(), body.top(), body.bottom(), v.scroll, body.contains(r.center())))
img.save(str(L / 'out/first_selection_below_fold.png')); box.close()
# 3. sideways overflow at the largest reading size
objs = [FieldObject('s', 'source', 'S.pdf'), FieldObject('t', 'sheet', 'T'), FieldObject('c', 'calculation', 'C'), FieldObject('f', 'finding', 'F'), FieldObject('q', 'question', 'Q?', state=STATE_OPEN)]
links = [FieldLink('s', 't'), FieldLink('t', 'c'), FieldLink('c', 'f'), FieldLink('f', 'q')]
for width, px in ((1030, 37), (492, 37), (708, 19), (664, 24)):
    v = FieldView(); box, _, _ = host(v, width + 24, 700, px); v.set_field(Field(list(objs), list(links))); app.processEvents(); body = v._layout()
    right = max(v.sheet_rect(i, body).right() for i in v._placed); sel = v.sheet_rect(v.field.selected, body)
    print('view %d px wide at font %d px (scale %.2f): rightmost sheet ends at x=%.0f; selected sheet spans x %.0f..%.0f -> %s' % (v.width(), px, v.scale(), right, sel.left(), sel.right(), 'cut off / off-screen' if sel.right() > v.width() else 'inside'))
    box.close()
# 4. measured ink on a receded sheet (depth 3) against its own ground
def lum(c):
    def f(x):
        x /= 255.0; return x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(c.red()) + 0.7152 * f(c.green()) + 0.0722 * f(c.blue())
def ratio(a, b):
    hi, lo = max(lum(a), lum(b)), min(lum(a), lum(b)); return (hi + 0.05) / (lo + 0.05)
objs = [FieldObject('s', 'source', 'S.pdf'), FieldObject('t', 'sheet', 'T'), FieldObject('c', 'calculation', 'C'), FieldObject('f', 'finding', 'Selected finding'),
        FieldObject('far', 'sheet', 'MMMMMMMMMM HHHHHH', 'sheet', STATE_CURRENT, ('HHHHHHHH MMMMMMMM',), 'MMMMMMMM.HHH'), FieldObject('x', 'source', 'X.pdf'), FieldObject('y', 'calculation', 'Y', state=STATE_RECHECK)]
links = [FieldLink('s', 't'), FieldLink('t', 'c'), FieldLink('c', 'f'), FieldLink('x', 'far'), FieldLink('far', 'y', '', True)]
v = FieldView(); box, _, _ = host(v); f = Field(objs, links); f.select('f'); v.set_field(f); v.texture = False; app.processEvents(); img = QImage(v.size(), QImage.Format_ARGB32); v.render(img)
print('depths:', v.field.depth())
r = v.sheet_rect('far', v._layout()); ground = img.pixelColor(int(r.left() + 4), int(r.bottom() - 4))
def brightest(x0, y0, x1, y1):
    best = ground
    for y in range(int(y0), int(y1)):
        for x in range(int(x0), int(x1)):
            c = img.pixelColor(x, y)
            if lum(c) > lum(best): best = c
    return best
s = v.scale(); pad = 12 * s
top = brightest(r.left() + pad, r.top() + pad, r.left() + r.width() * 0.45, r.top() + pad + 14 * s)
title = brightest(r.left() + pad, r.top() + pad + 16 * s, r.right() - pad, r.top() + pad + 44 * s)
where = brightest(r.left() + pad, r.bottom() - pad - 14 * s, r.right() - pad, r.bottom() - 4 * s)
print('receded sheet ground %s | kind tag ink %s %.2f:1 | title ink %s %.2f:1 | identity line ink %s %.2f:1' % (ground.name(), top.name(), ratio(top, ground), title.name(), ratio(title, ground), where.name(), ratio(where, ground)))
a = v.sheet_rect('far', v._layout()); b = v.sheet_rect('y', v._layout()); bg = QColor(t.TERMINAL_GROUND)
mx = int((a.right() + b.left()) / 2); wire = bg
for y in range(int(min(a.top(), b.top())), int(max(a.bottom(), b.bottom()))):
    c = img.pixelColor(mx, y)
    if lum(c) > lum(wire): wire = c
print('stale wire between two sheets not touching the selection: brightest pixel %s on %s = %.2f:1' % (wire.name(), bg.name(), ratio(wire, bg)))
img.save(str(L / 'out/contrast_probe.png')); box.close(); print('DONE')
