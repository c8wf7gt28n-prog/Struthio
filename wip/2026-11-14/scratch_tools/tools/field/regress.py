"""Orchestrator's capture: the real Graphite window on a disposable copy of the restored After Hours 07 workspace,
with the project's usual holds (no worker launch, no job submission, no provider request, no session or power command,
no child process). Opens the Field by its menu action, walks it by keyboard, opens a record with Enter, comes back."""
import json, os, sys, tempfile, shutil, subprocess
from pathlib import Path
from unittest.mock import patch
S = Path('/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad')
PROGRAM = Path(sys.argv[1]).resolve(); OUT = Path(sys.argv[2]).resolve(); W, H = int(sys.argv[3]), int(sys.argv[4]); CASE = len(sys.argv) < 6 or sys.argv[5] != 'empty'
RUN = Path(tempfile.mkdtemp(prefix='run-', dir=str(S / 'tools/field/run'))); HOME = RUN / 'home'; HOME.mkdir()
if CASE:
    shutil.copytree(S / 'work/demo/After_Hours_07', RUN / 'ws'); shutil.copytree(S / 'work/demo/After_Hours_07-profile', RUN / 'prof')
SCREEN = RUN / 'screen.json'
SCREEN.write_text(json.dumps({'screens': [{'name': 'shot', 'x': 0, 'y': 0, 'width': W, 'height': H, 'logicalDpi': 96, 'logicalBaseDpi': 96, 'dpr': 1.0}]}))
os.environ.update(PYTHONDONTWRITEBYTECODE='1', QT_QPA_PLATFORM='offscreen:configfile=' + str(SCREEN), ARC_LEDGER_EMBEDDED='1', ARC_LEDGER_DISABLE_BOOK_WATCHER='1',
                  HOME=str(HOME), ARC1_WORKBENCH_CONFIG_HOME=str(RUN / ('prof' if CASE else 'profile')), ARC_LEDGER_CONCERN=str(HOME / 'Concern'))
if CASE: os.environ['ARC_LEDGER_WORKSPACE'] = str(RUN / 'ws')
os.environ.pop('ARC_LEDGER_XSESSION', None)
os.chdir(RUN); sys.path.insert(0, str(PROGRAM)); sys.dont_write_bytecode = True
from PySide6.QtCore import QProcess, Qt
from PySide6.QtWidgets import QMessageBox
from PySide6.QtTest import QTest
from workbench.qt_app import make_app, WorkbenchWindow
from workbench import locations, clip, session_power
from workbench.engineering_kernel import Kernel
from workbench.session import Session
patch.object(clip, '_request', side_effect=AssertionError('No provider request')).start()
patch.object(Kernel, 'launch', side_effect=AssertionError('No worker launch')).start()
patch.object(Kernel, 'submit', side_effect=AssertionError('No job submission')).start()
patch.object(session_power, 'system', side_effect=OSError('no login session (held)')).start()
patch.object(QMessageBox, 'question', return_value=QMessageBox.No).start()
app = make_app([])
if CASE: root = RUN / 'ws'; session = Session(RUN / 'prof/session.json', root)
else: root = locations.office(HOME / 'Concern' / 'Office'); session = Session(RUN / 'profile/session.json', root)
w = WorkbenchWindow(root, session, restore=False)
import platform; platform.processor()
patch.object(subprocess, 'Popen', side_effect=OSError('No process start (held)')).start()
patch.object(os, 'system', side_effect=AssertionError('No shell command')).start()
patch.object(QProcess, 'startDetached', side_effect=AssertionError('No detached program')).start()
def settle(ms=50, n=6):
    for name in ('agenda_runner', 'study_idle'):
        obj = getattr(w, name, None)
        if obj and hasattr(obj, 'timer'): obj.timer.stop()
    for _ in range(n): app.processEvents(); QTest.qWait(ms)
def align(times=3):
    bar = getattr(w, 'type_bar', None)
    for _ in range(times):
        if bar is not None: bar.align()
        settle(25, 3)
def save(name):
    align(); assert w.grab().save(str(OUT / name), 'PNG'); print('saved', name)
def where(tag):
    cur = w.central_stack.currentWidget(); tab = w.tabs.currentWidget()
    print('%-28s centre=%s field=%s home=%s title=%r tab=%s' % (tag, type(cur).__name__, w._field_active, w._home_active, w.windowTitle(), type(tab).__name__ if tab else None))
from workbench import context_menu
from PySide6.QtGui import QFont
tag = '%dx%d' % (W, H)
w.resize(W, H); w.show(); w.activateWindow(); settle(); align()
state_before = bytes(w.saveState()); bars_before = [b.isVisible() for b in (w.concern.context_strip, w.workspace_status, w.context_bar, w.doc_info)]
w.a_field.trigger(); settle(); page = w.field_page; v = page.view
w.activateWindow(); QTest.qWaitForWindowActive(w, 1500); v.setFocus(); settle(10, 2)
body = v._layout(); print('view %dx%d scale %.2f | rail %d | body %d wide | surface %d wide | sideways scroll room %d | columns %d' % (v.width(), v.height(), v.scale(), v.rail(), body.width(), v._surface[0], max(0, v._surface[0] - body.width()), len(v.field.ranks())))
on = lambda: v.sheet_rect(v.field.selected, v._layout()); whole = lambda: v._layout().contains(on())
print('bars hidden under the Field:', [b.isVisible() for b in (w.concern.context_strip, w.workspace_status, w.context_bar, w.doc_info)])
save('Graphite_Field_10_Opened_%s.png' % tag)
# S, then Esc in the writing strip: the keyboard comes back to the Field
QTest.keyClick(v, Qt.Key_S); settle(); box = w.type_bar.box; print('after S, keyboard in:', type(app.focusWidget()).__name__)
QTest.keyClick(box, Qt.Key_Escape); settle(); print('after Esc in the strip, keyboard in:', type(app.focusWidget()).__name__, '| Field in front:', w._field_active)
before = v.field.selected; QTest.keyClick(app.focusWidget() or v, Qt.Key_Left); settle(10, 2); print('Left then moves the selection:', v.field.selected != before)
box.clear(); popup = getattr(box, 'popup', None); popup.hide() if popup is not None else None; v.setFocus(); settle(10, 2)
# Menu key with the selected sheet scrolled away, and for a plain page
for _ in range(4): QTest.keyClick(v, Qt.Key_PageDown)
settle(10, 2); menu = context_menu.open_at_focus(w); settle(40, 4); t = getattr(menu, 'target', None)
print('Menu key after PageDown x4 -> menu for:', getattr(t, 'label', None), '|', getattr(t, 'noun', None), '| sheet whole on screen:', whole()); menu.close(); settle(10, 2)
ident = next(o.id for o in v.field.objects if o.kind == 'document'); v.field.select(ident); v._describe(); v.update(); settle(10, 2)
menu = context_menu.open_at_focus(w); settle(40, 4); print('plain page heading:', repr(menu.target.noun)); menu.close(); settle(10, 2)
# Home after paging away
for _ in range(4): QTest.keyClick(v, Qt.Key_PageDown)
QTest.keyClick(v, Qt.Key_Home); settle(10, 2); print('Home after PageDown x4: selected', v.selected().title[:30], '| on screen:', v._layout().intersects(on()), '| whole:', whole())
# with a tab open: in, out, and everything as it was
QTest.keyClick(v, Qt.Key_Escape); settle(); w.show_files(); settle(); align()
bars = lambda: [b.isVisible() for b in (w.concern.context_strip, w.workspace_status, w.context_bar, w.doc_info)]
state_before = bytes(w.saveState()); bars_before = bars(); title_before = w.windowTitle()
w.a_field.trigger(); settle(); QTest.keyClick(v, Qt.Key_Escape); settle()
print('with a tab open, after F9 and Esc: dock state identical:', bytes(w.saveState()) == state_before, '| bars as before:', bars() == bars_before, bars_before, '| title as before:', w.windowTitle() == title_before, '| centre:', type(w.central_stack.currentWidget()).__name__)
# a large reading size on this screen: one sheet can still be seen whole
from workbench import ledger_control
k = w.ledger_bridge.kernel
from workbench.engineering_kernel import operator
def ui_pt(points):
    row = next(r for r in ledger_control.settings(k)['settings'] if r['key'] == 'reading.ui_pt')
    if row['value'] != float(points):
        r = k.dispatch('ledger.settings.set', {'key': 'reading.ui_pt', 'value': float(points), 'expected_revision': row['revision']}, operator()); assert r['ok'], r
    settle(40, 4)
for points in (14, 18, 28):
    ui_pt(points); w.a_field.trigger(); settle(30, 3); align(); v.field.select(v.field.first()); v._reveal_pending = True; v.update(); settle(20, 3)
    body = v._layout(); print('at %d pt: scale %.2f | head %d foot %d body %d high | sheet %dx%d | selected sheet whole on screen: %s | rail %d' % (points, v.scale(), v.head_height(), v.foot_height(), body.height(), v._placed[v.field.selected].w, v.sheet_height(), whole(), v.rail()))
    seen = 0; clear = 0
    for ident in list(v._placed):
        v.field.select(ident); v._layout(); v._reveal(); body = v._layout(); seen += whole()
        clear += body.adjusted(0, 0, 0, -24 * v.scale()).contains(on())
    print('   sheets that can be brought wholly on screen by the keyboard: %d of %d | and clear of the hint strip: %d' % (seen, len(v._placed), clear))
    save('Graphite_Field_11_Reading_%dpt_%s.png' % (points, tag)); QTest.keyClick(v, Qt.Key_Escape); settle()
ui_pt(14)
w._closing = True; print('DONE')
