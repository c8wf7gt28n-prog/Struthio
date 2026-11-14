"""Reviewer's common setup: the real window offscreen on a disposable copy of the worked case, with the project's holds.
usage in a probe:  from common import *   (after setting sys.argv: PROGRAM W H [empty])"""
import json, os, sys, tempfile, shutil, subprocess, time, hashlib, sqlite3
from pathlib import Path
from unittest.mock import patch
S = Path('/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad')
L = S / 'tools/rules-lens'
PROGRAM = Path(os.environ.get('PROBE_PROGRAM', '/home/user/Struthio')).resolve()
W, H = int(os.environ.get('PROBE_W', '1920')), int(os.environ.get('PROBE_H', '1200'))
CASE = os.environ.get('PROBE_CASE', 'case') != 'empty'
RUN = Path(tempfile.mkdtemp(prefix='run-', dir=str(L / 'run'))); HOME = RUN / 'home'; HOME.mkdir()
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
def where(tag):
    cur = w.central_stack.currentWidget(); tab = w.tabs.currentWidget()
    print('%-28s centre=%s field=%s home=%s title=%r tab=%s' % (tag, type(cur).__name__, w._field_active, w._home_active, w.windowTitle(), type(tab).__name__ if tab else None))
def open_window():
    w.resize(W, H); w.show(); w.activateWindow(); settle(); align()

def snapshot():
    """Every file under the run folder (size, sha256 for non-sqlite), and every table's row count in every sqlite database."""
    files = {}; tables = {}
    for path in sorted(RUN.rglob('*')):
        if not path.is_file(): continue
        rel = str(path.relative_to(RUN))
        if rel == 'screen.json': continue
        is_db = path.suffix in ('.sqlite3', '.sqlite', '.db') or rel.endswith(('-wal', '-shm'))
        try:
            files[rel] = ('db', 0) if is_db else (path.stat().st_size, hashlib.sha256(path.read_bytes()).hexdigest()[:16])
        except OSError as exc:
            files[rel] = ('unreadable', str(exc))
        if path.suffix in ('.sqlite3', '.sqlite', '.db'):
            try:
                db = sqlite3.connect('file:%s?mode=ro' % path, uri=True, timeout=5)
                names = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
                for name in names:
                    try: tables[rel + '::' + name] = db.execute('SELECT count(*) FROM "%s"' % name).fetchone()[0]
                    except sqlite3.Error as exc: tables[rel + '::' + name] = 'err ' + str(exc)[:40]
                tables[rel + '::<schema>'] = len(names)
                db.close()
            except sqlite3.Error as exc:
                tables[rel + '::<open>'] = 'err ' + str(exc)[:60]
    return files, tables

def diff(a, b, label):
    fa, ta = a; fb, tb = b; out = []
    for key in sorted(set(fa) | set(fb)):
        if fa.get(key) != fb.get(key):
            out.append('  file  %-70s %s -> %s' % (key, fa.get(key, 'ABSENT'), fb.get(key, 'ABSENT')))
    for key in sorted(set(ta) | set(tb)):
        if ta.get(key) != tb.get(key):
            out.append('  table %-70s %s -> %s' % (key, ta.get(key, 'ABSENT'), tb.get(key, 'ABSENT')))
    print('%s: %d differences' % (label, len(out)))
    for line in out: print(line)
    return out
