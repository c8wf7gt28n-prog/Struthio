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
from workbench import context_menu
w.resize(W, H); w.show(); w.activateWindow(); settle(); align()
w.a_field.trigger(); settle(); page = w.field_page; v = page.view
w.activateWindow(); QTest.qWaitForWindowActive(w, 1500); v.setFocus(); settle(10, 2)
ident = next(o.id for o in v.field.objects if o.kind == 'calculation' and 'Startup' in o.title); v.field.select(ident); v._describe(); v.update(); settle(20, 2)
menu = context_menu.open_at_focus(w); settle(60, 6)
t = menu.target if hasattr(menu, 'target') else None
print('menu for:', getattr(t, 'label', None), '|', getattr(t, 'noun', None), '| surface:', getattr(t, 'surface', None))
entries = context_menu.entries_for(w, t)
for e in entries: print('   %-18s %-34s %-10s %s%s' % (e.key, e.label, e.section, 'ok' if e.enabled else 'unavailable: ' + e.reason, '  [submenu]' if e.submenu else ''))
pix = w.grab()
from PySide6.QtGui import QPainter
from PySide6.QtCore import QPoint
p = QPainter(pix); p.drawPixmap(w.mapFromGlobal(menu.mapToGlobal(QPoint(0, 0))), menu.grab()); p.end(); assert pix.save(str(OUT / ('Graphite_Field_08_Instruments_%s.png' % tag))); print('saved 08')
fed = next(e for e in entries if e.key == 'field:fed'); rows = fed.submenu(); print('what feeds it:', [r.label for r in rows])
menu.close(); settle(20, 2); rows[0].run(); settle(20, 2); print('after choosing a feeder, selected:', v.selected().title, '| field still in front:', w._field_active)
e = next(e for e in context_menu.entries_for(w, context_menu.target_at(w, v, v.selected_point())) if e.key == 'field:inspect'); e.run(); settle()
print('inspect in the line ->', repr(w.type_bar.box.text()), '| field left:', not w._field_active)
w.a_field.trigger(); settle(); t2 = context_menu.target_at(w, v, QPoint(6, v.height() // 2)); print('empty place:', t2.label, t2.noun, [e.label for e in context_menu.entries_for(w, t2) if e.key.startswith('field:')])
w._closing = True; print('DONE')
