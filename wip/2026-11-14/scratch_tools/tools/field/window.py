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
tag = '%dx%d' % (W, H)
w.resize(W, H); w.show(); w.activateWindow(); app.setActiveWindow(w) if hasattr(app, 'setActiveWindow') else None; settle(); align(); where('opened')
w.show_start(); settle(); where('home')
centre_min_before = w.centralWidget().minimumSizeHint().width()
assert w.a_field in w.actions() and w.a_field.shortcut().toString() == 'F9'
print('in Arrange menu:', w.a_field in w.menu_groups['Options'].actions(), '| typed "field" finds:', [(l, k) for l, k, f in w.shell2.top.box.commands('field')][:3])
w.a_field.trigger(); settle(); where('field (from home)')
page = w.field_page; v = page.view
w._close_start(); settle(20, 2); print('centre minimum width in the plain workspace (no Field, no Home):', w.centralWidget().minimumSizeHint().width(), '| field page hint:', page.minimumSizeHint().width(), page.view.minimumSizeHint().width(), page.minimumWidth())
w.a_field.trigger(); settle()
w.activateWindow(); w.raise_(); print('window active:', QTest.qWaitForWindowActive(w, 1500), '| focus widget:', type(app.focusWidget()).__name__)
v.setFocus(); settle(10, 2); print('view has focus:', v.hasFocus())
from workbench import activity
rows_before = None
print('census:', v.field.census(), '| refused:', page.problem, '| focus on view:', v.hasFocus(), '| selected:', getattr(v.selected(), 'title', None))
print('centre minimum width before/after the page exists:', centre_min_before, w.centralWidget().minimumSizeHint().width())
save('Graphite_Field_01_Opened_%s.png' % tag)
if CASE:
    QTest.keyClick(v, Qt.Key_Left); QTest.keyClick(v, Qt.Key_Up); QTest.keyClick(v, Qt.Key_Up); settle(20, 2)
    for want in ('Startup ran 30 ms past the Rev B limit.',):
        ident = next((o.id for o in v.field.objects if o.title == want), None)
        if ident: v.field.select(ident); v._describe(); v.update()
    settle(20, 2); print('selected:', v.selected().title, '|', v.accessibleDescription()); save('Graphite_Field_02_Finding_Selected_%s.png' % tag)
    ident = next(o.id for o in v.field.objects if o.kind == 'calculation' and 'Startup' in o.title); v.field.select(ident); v._describe(); v.update(); settle(20, 2)
    save('Graphite_Field_03_Calculation_Selected_%s.png' % tag)
    QTest.keyClick(v, Qt.Key_Return, Qt.ShiftModifier); settle(80, 10)
    print('Shift+Enter -> ran:', getattr(w.console, 'last_program', None) == v.selected().stac, '| field in front:', w._field_active, '| console size:', w.console.size_level, '| focus back on the Field:', v.hasFocus())
    save('Graphite_Field_09_Stacy_Runs_staC_%s.png' % tag)
    QTest.keyClick(v, Qt.Key_S); settle(); print('S ->', repr(w.type_bar.box.text())[:150], '| field in front:', w._field_active)
    popup = getattr(w.type_bar.box, 'popup', None)
    if popup is not None: popup.hide()
    w.type_bar.box.clear(); w.console.set_size(0); v.setFocus(); settle(20, 3)
    QTest.keyClick(v, Qt.Key_Return); settle(); where('Enter on the calculation')
    tab = w.tabs.currentWidget(); print('  opened page:', type(tab).__name__, getattr(tab, 'document_id', None) == v.selected().target['id'])
    save('Graphite_Field_04_Opened_Real_Page_%s.png' % tag)
    w.a_field.trigger(); settle(); where('F9 again'); print('  selection kept:', v.selected().title)
    ident = next(o.id for o in v.field.objects if o.kind == 'sheet' and 'Bench' in o.title); v.field.select(ident); v._describe(); v.update(); settle(20, 2)
    QTest.keyClick(v, Qt.Key_Return); settle(); where('Enter on the sheet'); tab = w.tabs.currentWidget(); print('  opened page:', type(tab).__name__, getattr(tab, 'ident', None))
    save('Graphite_Field_05_Opened_Real_Sheet_%s.png' % tag)
    w.a_field.trigger(); settle(); QTest.keyClick(v, Qt.Key_Escape); settle(); where('Esc from the field')
else:
    QTest.keyClick(v, Qt.Key_Escape); settle(); where('Esc from the empty field')
w._closing = True; print('DONE')
