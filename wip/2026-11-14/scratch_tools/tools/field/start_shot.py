"""Orchestrator's probe of the START: the real Graphite window, constructed as a real launch does (restore=True) on a disposable copy of the restored After Hours 07 workspace,
with the project's usual holds (no worker launch, no job submission, no provider request, no session or power command,
no child process). Opens the Field by its menu action, walks it by keyboard, opens a record with Enter, comes back."""
import json, os, sys, tempfile, shutil, subprocess
from pathlib import Path
from unittest.mock import patch
S = Path('/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad')
PROGRAM = Path(sys.argv[1]).resolve(); OUT = Path(sys.argv[2]).resolve(); W, H = int(sys.argv[3]), int(sys.argv[4]); CASE = len(sys.argv) < 6 or sys.argv[5] != 'empty'; POLICY = sys.argv[6] if len(sys.argv) > 6 else 'last'
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
session.state['view_preferences']['startup'] = POLICY
w = WorkbenchWindow(root, session, restore=True)
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
w.resize(W, H); w.show(); w.activateWindow(); settle(); align(); where('launched (%s, policy %s)' % ('worked case' if CASE else 'empty workspace', POLICY))
v = getattr(getattr(w, 'field_page', None), 'view', None)
if w._field_active:
    print('  field objects:', len(v.field.objects), '| selected:', v.selected().title if v.selected() else None, '| keyboard in:', type(app.focusWidget()).__name__, '| bars hidden:', not any(b.isVisible() for b in (w.workspace_status, w.context_bar, w.doc_info)))
    save('Graphite_Start_On_The_Work_%s.png' % tag)
    QTest.keyClick(v, Qt.Key_Escape); settle(); where('Esc from the first Field')
    w.a_field.trigger(); settle(); where('F9 again')
else:
    print('  no Field at launch | field page built:', getattr(w, 'field_page', None) is not None)
    save('Graphite_UX_First_01_Home_At_First_Boot_%s.png' % tag)
    w.a_field.trigger(); settle(); where('F9'); v = w.field_page.view; print('  field objects:', len(v.field.objects)); QTest.keyClick(v, Qt.Key_Escape); settle(); where('Esc')
w._closing = True; print('DONE')
