"""A helper for test_session_start, not a test module: one start of Graphite as the dedicated session's start script makes
it, in a process of its own. A start that ends inside Qt takes its process with it, and it must not take the tests.

    python -B tests_integrated/session_start_probe.py RUN [ACT ...]

RUN is a folder kept from one start to the next: the profile (with the session file) and the workspace are in it. The
start is workbench.qt_app.main itself, on what the start script sets (the Office edition, the whole screen, and the room
named by ARC_LEDGER_OPEN when the caller set it): the window is built on the saved session and shown, and that room is
opened at the first turn of the event loop. Then each ACT is done as the owner might do it (home: go Home), the window is
closed the ordinary way, which saves the session, and what was seen is printed as JSON on the last line: 'built' (the
window as it was built, before it was shown or anything was opened), 'opened' (after the script's opening), 'left' (after
the acts) and 'saved' (the session file). Every hold of the right-click's tests is in place (no provider request, no
worker launch, no job, no session or power call).
"""
import json
import os
import subprocess
import sys
import traceback
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0, str(ROOT))
ACTS = {'home': lambda w:w.show_start()}
TURNS = 12      # of the watch, 50 ms each, between the window coming up and the acts: the script's opening is at the first


def seen(w):
    """What is in the strip and what is in front."""
    current = w.tabs.currentWidget()
    return {'tabs': [type(w.tabs.widget(i)).__name__ for i in range(w.tabs.count())], 'current': type(current).__name__ if current is not None else None,
            'home': bool(w._home_active), 'workspace_in_front': w.central_stack.currentWidget() is w.workspace_split,
            'waiting': [row.get('kind') for _, row in w.tabs.waiting], 'deferred': [row.get('kind') for row in w.tabs.deferred],
            'last_surface': w.view_preferences.get('last_surface')}


def run(folder, acts):
    run = Path(folder)
    os.environ.update(QT_QPA_PLATFORM='offscreen', ARC_LEDGER_EMBEDDED='1', ARC_LEDGER_DISABLE_BOOK_WATCHER='1', ARC1_WORKBENCH_CONFIG_HOME=str(run / 'profile'),
                      ARC_LEDGER_CONCERN=str(run / 'Concern'), HOME=str(run / 'home'), ARC_LEDGER_EDITION='office', ARC_LEDGER_FULLSCREEN='1')
    for name in ('ARC_LEDGER_XSESSION', 'ARC_LEDGER_WORKSPACE'):os.environ.pop(name, None)
    (run / 'home').mkdir(exist_ok=True)
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QMessageBox
    from workbench import clip, qt_app, session_power
    from workbench.engineering_kernel import Kernel
    for hold in (patch.object(clip, '_request', side_effect=AssertionError('No provider request')),
                 patch.object(Kernel, 'launch', side_effect=AssertionError('No worker launch')),
                 patch.object(Kernel, 'submit', side_effect=AssertionError('No job submission')),
                 patch.object(session_power, 'system', side_effect=OSError('no login session (held)')),
                 patch.object(QMessageBox, 'question', return_value=QMessageBox.No)):hold.start()
    app = qt_app.make_app([]);out = {};windows = [];turns = [0]
    build = qt_app.WorkbenchWindow.__init__

    def built(w, *args, **kwargs):
        build(w, *args, **kwargs);windows.append(w);out['built'] = seen(w)

    def watch():
        if not windows or not windows[0].isVisible():return
        w = windows[0];turns[0] += 1
        if turns[0] == 1:      # nothing of the desk's own goes on working behind the start
            for name in ('agenda_runner', 'study_idle', 'ledger_bridge'):
                timer = getattr(getattr(w, name, None), 'timer', None)
                if timer is not None:timer.stop()
            try:w.type_bar.hatch.lifecycle.timer.stop()
            except AttributeError:pass
        if turns[0] != TURNS:return
        try:
            out['opened'] = seen(w)
            for name in acts:ACTS[name](w);app.processEvents()
            out['left'] = seen(w)
            out['closed'] = bool(w.close())
        except Exception:  # noqa: BLE001 - told to the test, and the start still ends
            out['error'] = traceback.format_exc()
        QTimer.singleShot(200, app.quit)

    timer = QTimer();timer.setInterval(50);timer.timeout.connect(watch);timer.start()
    with patch.object(qt_app.WorkbenchWindow, '__init__', built):out['code'] = qt_app.main()
    try:
        data = json.loads(windows[0].session.path.read_text(encoding='utf-8'));workspace = data.get('workspace') or {}
        out['saved'] = {'tabs': [row.get('kind') for row in workspace.get('tabs', [])], 'deferred': [row.get('kind') for row in workspace.get('deferred', [])],
                        'active': workspace.get('active'), 'last_surface': (data.get('view_preferences') or {}).get('last_surface')}
    except (OSError, ValueError, IndexError) as error:out['saved'] = repr(error)
    print(json.dumps(out, default=str))
    sys.stdout.flush();os._exit(0)


def probe(run, *acts, opening='office', timeout=300):
    """One start in a subprocess, with the room the start script opens (None: no room); its JSON. A start that did not
    end the ordinary way (a signal: -11 is a segmentation fault) is an AssertionError with what it left behind."""
    env = dict(os.environ);env.update(QT_QPA_PLATFORM='offscreen', PYTHONFAULTHANDLER='1')
    env.pop('ARC_LEDGER_OPEN', None)
    if opening:env['ARC_LEDGER_OPEN'] = opening
    done = subprocess.run([sys.executable, '-B', str(Path(__file__).resolve()), str(run)] + list(acts), cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=timeout)
    lines = [line for line in done.stdout.splitlines() if line.startswith('{')]
    if done.returncode or not lines:
        raise AssertionError('the start ended with exit code %s and no report:\n%s\n%s' % (done.returncode, done.stdout[-2000:], done.stderr[-4000:]))
    return json.loads(lines[-1])


if __name__ == '__main__':
    run(sys.argv[1], sys.argv[2:])
