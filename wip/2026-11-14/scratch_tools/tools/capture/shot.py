"""Orchestrator's own offscreen capture of the Graphite window, using the same holds as the project's review script:
disposable home/profile, no worker launch, no job submission, no provider request, no session/power command."""
import json, os, sys, tempfile, subprocess
from pathlib import Path
from unittest.mock import patch
PROGRAM = Path(sys.argv[1]).resolve(); OUT = Path(sys.argv[2]).resolve(); W, H = int(sys.argv[3]), int(sys.argv[4])
RUN = Path(tempfile.mkdtemp(prefix='graphite-shot-')); HOME = RUN / 'home'; HOME.mkdir()
SCREEN = RUN / 'screen.json'
SCREEN.write_text(json.dumps({'screens': [{'name': 'shot', 'x': 0, 'y': 0, 'width': W, 'height': H, 'logicalDpi': 96, 'logicalBaseDpi': 96, 'dpr': 1.0}]}))
os.environ.update(QT_QPA_PLATFORM='offscreen:configfile=' + str(SCREEN), ARC_LEDGER_EMBEDDED='1', ARC_LEDGER_DISABLE_BOOK_WATCHER='1',
                  HOME=str(HOME), ARC1_WORKBENCH_CONFIG_HOME=str(RUN / 'profile'), ARC_LEDGER_CONCERN=str(HOME / 'Concern'))
os.environ.pop('ARC_LEDGER_XSESSION', None)
os.chdir(RUN); sys.path.insert(0, str(PROGRAM)); sys.dont_write_bytecode = True
from PySide6.QtCore import QProcess
from PySide6.QtWidgets import QMessageBox
from PySide6.QtTest import QTest
from workbench.qt_app import make_app, WorkbenchWindow
from workbench import locations, clip, session_power
from workbench.engineering_kernel import Kernel
from workbench.session import Session
def held_power(request):
    raise OSError('no login session (held)')
patch.object(clip, '_request', side_effect=AssertionError('No provider request')).start()
patch.object(Kernel, 'launch', side_effect=AssertionError('No worker launch')).start()
patch.object(Kernel, 'submit', side_effect=AssertionError('No job submission')).start()
patch.object(session_power, 'system', side_effect=held_power).start()
patch.object(QMessageBox, 'question', return_value=QMessageBox.No).start()
app = make_app([]); root = locations.office(HOME / 'Concern' / 'Office'); session = Session(RUN / 'profile/session.json', root)
w = WorkbenchWindow(root, session, restore=False)
import platform; platform.processor()
patch.object(subprocess, 'Popen', side_effect=AssertionError('No process start')).start()
patch.object(os, 'system', side_effect=AssertionError('No shell command')).start()
patch.object(QProcess, 'startDetached', side_effect=AssertionError('No detached program')).start()
def settle(ms=60, n=6):
    for name in ('agenda_runner', 'study_idle'):
        obj = getattr(w, name, None)
        if obj and hasattr(obj, 'timer'): obj.timer.stop()
    for _ in range(n): app.processEvents(); QTest.qWait(ms)
w.resize(W, H); w.show(); settle()
print('window title:', w.windowTitle()); print('central:', type(w.centralWidget()).__name__)
print('attrs with boss/art:', [a for a in dir(w) if any(s in a.lower() for s in ('boss', 'art_mode', 'overview', 'worksheet', 'journal', 'screensaver'))][:40])

def save(widget, name):
    assert widget.grab().save(str(OUT / name), 'PNG'); print('saved', name, widget.width(), 'x', widget.height())
save(w, 'Graphite_01_Opened_%dx%d.png' % (W, H))
try:
    w.show_start(); settle(80, 10); save(w, 'Graphite_02_Home_%dx%d.png' % (W, H))
except Exception as exc:
    print('home failed:', repr(exc)[:300])
try:
    idle = w.idle_display; idle.preview(); settle(120, 14)
    tops = [x for x in app.topLevelWidgets() if x.isVisible() and x is not w]
    print('visible top-levels after preview:', [(type(x).__name__, x.width(), x.height()) for x in tops], 'showing:', idle.showing())
    target = None
    for attr in ('view', 'display', 'surface', 'widget', 'panel'):
        cand = getattr(idle, attr, None)
        if cand is not None and hasattr(cand, 'grab') and cand.isVisible(): target = cand; break
    if target is None and tops: target = max(tops, key=lambda x: x.width() * x.height())
    save(target if target is not None else w, 'Graphite_03_Screensaver_Preview_%dx%d.png' % (W, H))
    idle.dismiss(); settle()
except Exception as exc:
    print('screensaver failed:', repr(exc)[:300])
