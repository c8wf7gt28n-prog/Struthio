"""Orchestrator's MODEL REHEARSAL: a real small model started through Graphite's own operations; the real Graphite window on a disposable copy of the restored After Hours 07 workspace,
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
patch.object(session_power, 'system', side_effect=OSError('no login session (held)')).start()
patch.object(QMessageBox, 'question', return_value=QMessageBox.No).start()
app = make_app([])
if CASE: root = RUN / 'ws'; session = Session(RUN / 'prof/session.json', root)
else: root = locations.office(HOME / 'Concern' / 'Office'); session = Session(RUN / 'profile/session.json', root)
w = WorkbenchWindow(root, session, restore=False)
import platform; platform.processor()
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
import time, uuid
from workbench.engineering_kernel import operator
MODEL = os.environ['REHEARSAL_MODEL']
w.resize(W, H); w.show(); w.activateWindow(); settle(); align()
k = w.ledger_bridge.kernel; p = operator()
def call(op, args=None):
    r = k.dispatch(op, args or {}, p)
    if not r['ok']: raise RuntimeError('%s refused: %s' % (op, r['error']))
    return r['result']
def wait_job(ident, seconds=900, say=''):
    t = time.time()
    while time.time() - t < seconds:
        job = call('jobs.get', {'id': ident})
        if job['state'] in ('Completed', 'Failed', 'Cancelled', 'Interrupted'):
            print('   %s job %s: %s in %.1f s%s' % (say, job.get('tool'), job['state'], time.time() - t, (' | ' + str(job.get('error'))[:300]) if job['state'] != 'Completed' else '')); return job
        settle(100, 3)
    raise RuntimeError('job did not finish: ' + ident)
print('brain before:', call('brain.status')['state'], '| runtime:', {k2: v for k2, v in call('brain.runtime').items() if k2 in ('state', 'build', 'backend', 'backends', 'installed')})
job = call('brain.model.add', {'path': MODEL, 'origin': 'huggingface.co/unsloth/Qwen3.5-2B-GGUF', 'managed_copy': False})
print('add ->', {k2: job.get(k2) for k2 in ('id', 'tool', 'state')}); wait_job(job['id'], say='inspect')
models = call('brain.models')['models']; m = models[-1]
print('registered:', len(models), '|', {k2: m.get(k2) for k2 in ('id', 'name', 'architecture', 'parameters', 'quantization', 'context_length', 'declared_license', 'qualification', 'chat_template_sha256')})
job = call('brain.model.use', {'id': m['id'], 'options': {'backend': 'CPU', 'threads': 4, 'context': int(os.environ.get('REHEARSAL_CONTEXT', '4096'))}})
print('use ->', {k2: job.get(k2) for k2 in ('id', 'tool', 'state')}); done = wait_job(job['id'], say='activate')
st = call('brain.status'); print('brain after:', st['state'], '| worker:', st.get('worker')); print('   resource_stop:', st.get('resource_stop'))
exec(open(os.environ['REHEARSAL_SCRIPT']).read()) if os.environ.get('REHEARSAL_SCRIPT') else None
try: call('brain.stop')
except Exception as exc: print('stop:', exc)
w._closing = True; print('DONE')
