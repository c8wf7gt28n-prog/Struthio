"""Fix harness: one window on the bench seed (test_desk_acts.build_window) in the builder's worktree, plus recorders for
anything that leaves the window or changes a record: an external open, a process start, a changing Kernel operation."""
import os, sys, json
TREE = os.environ['DESK_TREE']
sys.path.insert(0, TREE)
os.chdir(TREE)
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from unittest.mock import patch

LEFT = []          # (kind, detail) of everything that would leave the window, run, or change a record


def start(size=(1920, 1200), prefix='fix-', brain_ready=False):
    from tests_integrated import test_desk_acts as T
    from PySide6.QtCore import QProcess
    from PySide6.QtGui import QDesktopServices
    store = {}
    T.build_window(store, prefix)
    w = store['w']
    w.resize(*size); T.settle(store)
    from workbench.engineering_kernel import Kernel, CAPABILITIES
    real = Kernel.dispatch

    def spy(self, op, params=None, principal=None):
        if CAPABILITIES.get(op, 'approve') != 'read':
            LEFT.append(('dispatch', op, json.dumps(params, default=str)[:160]))
            if op == 'brain.ask':return {'ok': True, 'result': {'id': 'job-fake'}}
        if op == 'brain.status' and brain_ready:return {'ok': True, 'result': {'state': 'READY'}}
        return real(self, op, params, principal)
    holds = [patch.object(QDesktopServices, 'openUrl', side_effect=lambda url: LEFT.append(('openUrl', url.toString())) or True),
             patch.object(QProcess, 'start', side_effect=lambda *a, **k: LEFT.append(('QProcess.start', [str(x) for x in a[1:]]))),
             patch.object(Kernel, 'dispatch', spy)]
    for h in holds:h.start()
    store['holds'] = store['holds'] + holds
    store['T'] = T
    return store


def act(store, name, args=None, **kw):
    from workbench.desk_doers import run
    kw.setdefault('door', 'script');kw.setdefault('origin', 'desk-script:fix')
    out = run(store['w'], name, args or {}, **kw);store['T'].settle(store);return out


def short(env):
    return {k: env.get(k) for k in ('act', 'ok', 'by', 'words', 'error')} | {'result': json.dumps(env.get('result'), default=str, ensure_ascii=False)[:400]}


def p(label, env):
    print(label, json.dumps(short(env), ensure_ascii=False, default=str)[:700]);sys.stdout.flush()


def typed(store, line):
    """The owner's way: the line set in the writing line, then Enter."""
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    w = store['w'];bar = w.type_bar;box = bar.box
    bar.set_target('slate', focus=True);store['T'].settle(store)
    box.setFocus();box.setText(line);store['T'].settle(store)
    QTest.keyClick(box, Qt.Key_Return);store['T'].settle(store, 60)
    out = w.console.output.toPlainText()
    tail = out[out.rfind('graphite › ' + line[1:]):]
    print('TYPED', repr(line), '->', repr(tail[:300]), '| box after:', repr(box.text()));sys.stdout.flush()


def finish(store):
    store['T'].close_window(store)
