"""Reviewer probe base: the REAL window offscreen on a disposable copy of the case, with the harness's holds."""
import json, os, sys, tempfile, shutil, subprocess, hashlib, traceback
from pathlib import Path
from unittest.mock import patch
S = Path('/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad')
PROGRAM = S / 'work/wt'; OUT = S / 'tools/verify-reader/shots'
W, H = int(os.environ.get('PROBE_W', 1920)), int(os.environ.get('PROBE_H', 1200)); CASE = os.environ.get('PROBE_CASE', 'case') != 'empty'
RUN = Path(tempfile.mkdtemp(prefix='run-', dir=str(S / 'tools/verify-reader/run'))); HOME = RUN / 'home'; HOME.mkdir()
if CASE:
    shutil.copytree(S / 'work/demo/After_Hours_07', RUN / 'ws'); shutil.copytree(S / 'work/demo/After_Hours_07-profile', RUN / 'prof')
SCREEN = RUN / 'screen.json'
SCREEN.write_text(json.dumps({'screens': [{'name': 'shot', 'x': 0, 'y': 0, 'width': max(W, 1920), 'height': max(H, 1200), 'logicalDpi': 96, 'logicalBaseDpi': 96, 'dpr': 1.0}]}))
os.environ.update(PYTHONDONTWRITEBYTECODE='1', QT_QPA_PLATFORM='offscreen:configfile=' + str(SCREEN), ARC_LEDGER_EMBEDDED='1', ARC_LEDGER_DISABLE_BOOK_WATCHER='1',
                  HOME=str(HOME), ARC1_WORKBENCH_CONFIG_HOME=str(RUN / ('prof' if CASE else 'profile')), ARC_LEDGER_CONCERN=str(HOME / 'Concern'))
if CASE: os.environ['ARC_LEDGER_WORKSPACE'] = str(RUN / 'ws')
os.environ.pop('ARC_LEDGER_XSESSION', None)
os.chdir(RUN); sys.path.insert(0, str(PROGRAM)); sys.dont_write_bytecode = True
from PySide6.QtCore import QProcess, Qt, QPoint, QPointF
from PySide6.QtWidgets import QMessageBox, QDockWidget, QApplication
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
errors = []
def hook(kind, value, tb):
    errors.append(''.join(traceback.format_exception(kind, value, tb)))
    print('   !! UNCAUGHT in a slot:', ''.join(traceback.format_exception_only(kind, value)).strip()[:300])
sys.excepthook = hook
app = make_app([])
if CASE: root = RUN / 'ws'; session = Session(RUN / 'prof/session.json', root)
else: root = locations.office(HOME / 'Concern' / 'Office'); session = Session(RUN / 'profile/session.json', root)
w = WorkbenchWindow(root, session, restore=False)
import platform; platform.processor()
patch.object(subprocess, 'Popen', side_effect=OSError('No process start (held)')).start()
patch.object(os, 'system', side_effect=AssertionError('No shell command')).start()
patch.object(QProcess, 'startDetached', side_effect=AssertionError('No detached program')).start()
def settle(ms=40, n=5):
    for name in ('agenda_runner', 'study_idle'):
        obj = getattr(w, name, None)
        if obj and hasattr(obj, 'timer'): obj.timer.stop()
    for _ in range(n): app.processEvents(); QTest.qWait(ms)
def align(times=2):
    bar = getattr(w, 'type_bar', None)
    for _ in range(times):
        if bar is not None: bar.align()
        settle(25, 2)
def save(name):
    align(); assert w.grab().save(str(OUT / name), 'PNG'); print('saved', OUT / name)
def where(tag):
    cur = w.central_stack.currentWidget(); tab = w.tabs.currentWidget()
    print('%-44s centre=%s field=%s home=%s title=%r tabs=%d tab=%s' % (tag, type(cur).__name__, w._field_active, w._home_active, w.windowTitle(), w.tabs.count(), type(tab).__name__ if tab else None))
def snap():
    """What the owner would notice: title, what is in the centre, and which bars and panels are visible."""
    out = {'title': w.windowTitle(), 'centre': type(w.central_stack.currentWidget()).__name__, 'tabs': w.tabs.count(), 'tab': w.tabs.currentIndex(),
           'state': hashlib.sha256(bytes(w.saveState())).hexdigest()[:12], 'geometry': (w.width(), w.height())}
    for name in ('context_bar', 'doc_info', 'workspace_status', 'clip', 'output_dock', 'cart_dock'):
        obj = getattr(w, name, None)
        if obj is not None: out[name] = obj.isVisible()
    for dock in w.findChildren(QDockWidget):
        out['dock:' + (dock.objectName() or dock.windowTitle())] = (dock.isVisible(), dock.isFloating())
    fw = app.focusWidget(); out['focus'] = type(fw).__name__ if fw else None
    return out
def diff(a, b, tag):
    changed = {k: (a.get(k), b.get(k)) for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k)}
    print('   %s: %s' % (tag, 'identical' if not changed else 'CHANGED ' + json.dumps(changed, default=str)))
    return changed
def status():
    return w.statusBar().currentMessage()
w.resize(W, H); w.show(); w.activateWindow(); settle(); align()
def field():
    w.a_field.trigger(); settle(); return w.field_page.view
def finish():
    w._closing = True; print('uncaught errors:', len(errors)); print('DONE')
