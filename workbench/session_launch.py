"""Graphite 1.0 S1 · The session that survives: the launch path for programs, the hand-over to the session's supervisor, and
what Graphite says when the supervisor has started it again.

The dedicated session (LS_XSESSION.sh) is owned by a small supervisor: Fluxbox and the D-Bus session run for the whole
session, and Graphite's window is the supervisor's child, started again when it ends unexpectedly (a status other than 0),
with a growing wait between tries and a limit, after which the session ends at the text console with a plain message.
The session ends only when Graphite ends the ordinary way (status 0: Return to Debian, or the window's own close after Log
out, Restart or Shut down asked the system) or when the system ends it (logind, the X server). This module is Graphite's side
of that arrangement:

  launch(argv)       the one launch path for program windows. The program is started in a session and process group of its
                     own (setsid) through a short-lived helper, so it is not Graphite's child at all: it is not in Graphite's
                     process group, Graphite's descendants (what Stop all jobs looks through) do not include it, and when
                     Graphite's window crashes or is started again the program window stays open. argv only, never a shell;
                     never sudo, pkexec, su or doas. Graphite's own settings are taken out of the program's environment.
  launched()         the programs launch() started in this session that still run (each checked by its process id and the
                     kernel's start time of that process, so a reused id is never mistaken for the program).
  hand_over(env)     in the supervised session, starting Graphite again on another workspace (or in another look) is the
                     supervisor's to do: the request is written for it, Graphite closes the ordinary way, and the supervisor
                     starts it with those settings (it never ends the session for it). Elsewhere it returns False and the
                     caller starts the new window itself, as before.
  restart_note()     the plain line the window shows when the supervisor started it again after an unexpected end.

The supervisor exports ARC_LEDGER_SESSION_DIR (a private folder, mode 0700, for the hand-over request and the programs'
record), ARC_LEDGER_SESSION_RESTARTS (how many times it has started Graphite again in this session) and
ARC_LEDGER_SESSION_LAST_STATUS (the status of the last unexpected end). Nothing here needs Qt, except window_started().
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SESSION_DIR = 'ARC_LEDGER_SESSION_DIR'
RESTARTS = 'ARC_LEDGER_SESSION_RESTARTS'
LAST_STATUS = 'ARC_LEDGER_SESSION_LAST_STATUS'
HANDOVER = 'next-start'          # the hand-over request, in the session folder (read and removed by the supervisor)
REGISTRY = 'programs.jsonl'      # one line per program launch() started in this session
HANDED = ('ARC_LEDGER_', 'ARC1_', 'GRAPHITE_')   # the settings a hand-over may carry (the supervisor accepts only these)
SUPERVISOR_OWN = frozenset({'ARC_LEDGER_XSESSION', 'ARC_LEDGER_FULLSCREEN', SESSION_DIR, RESTARTS, LAST_STATUS})
NAME = re.compile(r'^[A-Z][A-Z0-9_]{0,63}$')
NEVER = frozenset({'sudo', 'pkexec', 'su', 'doas', 'run0'})
# Graphite's own settings, and what PySide6 or the venv put in Graphite's environment, are not a program's business
PRIVATE_PREFIXES = ('ARC_LEDGER_', 'ARC1_', 'GRAPHITE_', 'PYTHON')
PRIVATE = frozenset({'QT_PLUGIN_PATH', 'QML2_IMPORT_PATH', 'QML_IMPORT_PATH', 'QT_QPA_PLATFORM_PLUGIN_PATH', 'VIRTUAL_ENV',
                     'PYSIDE_DESIGNER_PLUGINS'})
SPAWN_SECONDS = 15

# The helper: a fresh, single-threaded Python that starts the program in a session of its own and ends at once, so the
# program's parent is gone and the system adopts it. It answers one JSON line: {"pid": n} or {"error": "..."}.
_SPAWN = r'''
import json, os, subprocess, sys
spec = json.loads(sys.stdin.buffer.read().decode('utf-8'))
out = None
try:
    out = open(spec['log'], 'ab') if spec.get('log') else subprocess.DEVNULL
    child = subprocess.Popen(spec['argv'], executable=spec['executable'], cwd=spec.get('cwd') or None, env=spec['env'],
                             stdin=subprocess.DEVNULL, stdout=out, stderr=out, close_fds=True, start_new_session=True)
    answer = {'pid': child.pid}
except (OSError, ValueError, subprocess.SubprocessError) as exc:
    answer = {'error': '%s: %s' % (type(exc).__name__, exc)}
sys.stdout.write(json.dumps(answer))
sys.stdout.flush()
os._exit(0)
'''


def supervised(environ=None):
    """True inside the dedicated session's supervisor (LS_XSESSION.sh exports the marker and the session folder)."""
    environ = os.environ if environ is None else environ
    folder = environ.get(SESSION_DIR, '')
    return environ.get('ARC_LEDGER_XSESSION') == '1' and bool(folder) and os.path.isdir(folder)


def session_dir(environ=None, create=True):
    """The session's private folder: the supervisor's, else one under XDG_RUNTIME_DIR, else under the state folder."""
    environ = os.environ if environ is None else environ
    named = environ.get(SESSION_DIR)
    if named:folder = Path(named)
    elif environ.get('XDG_RUNTIME_DIR'):folder = Path(environ['XDG_RUNTIME_DIR']) / 'graphite-session'
    else:
        state = environ.get('XDG_STATE_HOME')
        folder = (Path(state) if state else Path.home() / '.local' / 'state') / 'ledger-slate' / 'session'
    if create:
        folder.mkdir(parents=True, exist_ok=True)
        try:os.chmod(folder, 0o700)
        except OSError:pass
    return folder


def program_environment(environ=None):
    """The environment a program starts with: this session's (DISPLAY, the D-Bus session, HOME, PATH, the language), without
    Graphite's own settings and without what Python and PySide6 put there for Graphite's window."""
    environ = dict(os.environ if environ is None else environ)
    out = {k:v for k, v in environ.items() if k not in PRIVATE and not k.startswith(PRIVATE_PREFIXES)}
    if out.get('QT_QPA_PLATFORM') in ('offscreen', 'minimal'):out.pop('QT_QPA_PLATFORM')   # Graphite's checks, not the program's
    return out


def start_time(pid):
    """The kernel's start time of a process (field 22 of /proc/<pid>/stat), or None when it does not run."""
    try:raw = Path('/proc/%d/stat' % int(pid)).read_text()
    except (OSError, ValueError):return None
    fields = raw[raw.rfind(')') + 2:].split()
    if len(fields) < 20 or fields[0] == 'Z':return None
    return fields[19]


def _resolve(program, env):
    if '/' in program:
        path = Path(program)
        return str(path) if path.is_file() and os.access(path, os.X_OK) else None
    return shutil.which(program, path=env.get('PATH') or os.defpath)


def launch(argv, cwd=None, env=None, name=None, log=None, environ=None):
    """Start a program window in a session of its own, not as Graphite's child. argv: the program and its arguments (no
    shell); cwd: its working folder; env: its whole environment (default: program_environment()); name: the word for it; log:
    a file its output is appended to (default: none). Returns dict(ok, pid, name, argv, program, reason): ok only when the
    program was started (the helper saw it begin); a program that cannot start says why, and nothing is left running."""
    argv = [str(a) for a in (argv or ())]
    name = str(name or (Path(argv[0]).name if argv else ''))
    if not argv or not argv[0] or any('\0' in a for a in argv):
        return dict(ok=False, pid=None, name=name, argv=argv, program=None, reason='There is no program to start.')
    if Path(argv[0]).name in NEVER:
        return dict(ok=False, pid=None, name=name, argv=argv, program=None, reason='Graphite never starts a program through %s.' % Path(argv[0]).name)
    env = program_environment(environ) if env is None else {str(k):str(v) for k, v in env.items()}
    program = _resolve(argv[0], env)
    if program is None:
        return dict(ok=False, pid=None, name=name, argv=argv, program=None, reason='%s is not installed on this computer.' % argv[0])
    if cwd is not None and not Path(cwd).is_dir():
        return dict(ok=False, pid=None, name=name, argv=argv, program=program, reason='The folder %s is not there.' % cwd)
    spec = dict(argv=argv, executable=program, cwd=str(cwd) if cwd is not None else None, env=env, log=str(log) if log else None)
    try:
        done = subprocess.run([sys.executable, '-I', '-S', '-c', _SPAWN], input=json.dumps(spec).encode('utf-8'),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=SPAWN_SECONDS, start_new_session=True)
        answer = json.loads(done.stdout.decode('utf-8', 'replace') or '{}')
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        answer = {'error': str(exc)}
    pid = answer.get('pid')
    if not isinstance(pid, int) or pid <= 0:
        return dict(ok=False, pid=None, name=name, argv=argv, program=program, reason='%s did not start: %s' % (name, answer.get('error') or 'no answer from the start'))
    entry = dict(pid=pid, start=start_time(pid), name=name, program=program, utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
    try:_record(entry, environ)
    except OSError:pass   # the record helps Graphite find its programs again; the program runs without it
    return dict(ok=True, pid=pid, name=name, argv=argv, program=program, reason='%s started in a session of its own.' % name)


def _entries(environ=None):
    try:text = (session_dir(environ, create=False) / REGISTRY).read_text(encoding='utf-8')
    except OSError:return []
    out = []
    for line in text.splitlines():
        try:row = json.loads(line)
        except ValueError:continue
        if isinstance(row, dict) and isinstance(row.get('pid'), int):out.append(row)
    return out


def _alive(row):
    now = start_time(row['pid'])
    return now is not None and (row.get('start') is None or str(row.get('start')) == now)


def _record(entry, environ=None):
    """Keep the programs still running and add this one (written whole, then put in place)."""
    folder = session_dir(environ)
    rows = [row for row in _entries(environ) if _alive(row)][-199:] + [entry]
    fd, staged = tempfile.mkstemp(prefix='.programs-', dir=folder)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as out:out.write(''.join(json.dumps(row) + '\n' for row in rows))
        os.replace(staged, folder / REGISTRY)
    finally:
        if os.path.exists(staged):os.unlink(staged)


def launched(environ=None):
    """The programs launch() started in this session that still run: [dict(pid, name, program, utc)]."""
    return [row for row in _entries(environ) if _alive(row)]


# The hand-over: starting Graphite again is the supervisor's to do -------------------------------------------------------

def hand_over(env, environ=None):
    """In the supervised session: ask the supervisor to start Graphite again with `env`'s settings (those named by HANDED)
    once this window has closed the ordinary way. Writes the request (NUL-separated '+NAME=value' and '-NAME' entries,
    the change from this window's own settings) and returns True. Elsewhere returns False: the caller starts the new window
    itself, as before 1.0."""
    environ = os.environ if environ is None else environ
    if not supervised(environ):return False
    def handed(name):return name.startswith(HANDED) and name not in SUPERVISOR_OWN and bool(NAME.match(name))
    entries = ['+%s=%s' % (k, v) for k, v in sorted(env.items()) if handed(k) and '\0' not in str(v)]
    entries += ['-%s' % k for k in sorted(environ) if handed(k) and k not in env]
    folder = session_dir(environ)
    fd, staged = tempfile.mkstemp(prefix='.next-start-', dir=folder)
    try:
        with os.fdopen(fd, 'wb') as out:out.write(b''.join(e.encode('utf-8') + b'\0' for e in entries))
        os.replace(staged, folder / HANDOVER)
    finally:
        if os.path.exists(staged):os.unlink(staged)
    return True


def withdraw(environ=None):
    """The window did not close after all (a question was cancelled): the request is taken back, so the supervisor ends the
    session as usual when the window does close later."""
    try:(session_dir(environ, create=False) / HANDOVER).unlink()
    except OSError:pass


# What the window says when the supervisor started it again -------------------------------------------------------------

def restart_note(environ=None):
    """'' unless the supervisor started this window again after an unexpected end; then one plain line saying so."""
    environ = os.environ if environ is None else environ
    try:times = int(environ.get(RESTARTS) or 0)
    except ValueError:times = 0
    if times <= 0:return ''
    status = (environ.get(LAST_STATUS) or '').strip()
    how = 'it ended unexpectedly' + (' (status %s)' % status if status.isdigit() else '')
    again = 'again' if times == 1 else 'again (%d times in this session)' % times
    return 'Graphite started %s: %s. The apps you opened from Graphite stayed open.' % (again, how)


def window_started(window, environ=None):
    """Called once the window is shown (qt_app.main): the restart note in the status line, and in the dedicated session the
    guard that locks the screen before the computer sleeps (session_power.SleepGuard). Never fails the start."""
    environ = os.environ if environ is None else environ
    try:
        note = restart_note(environ)
        if note and hasattr(window, 'statusBar'):window.statusBar().showMessage(note, 20000)
    except Exception:  # noqa: BLE001 - a note that cannot be shown is no reason to stop the start
        pass
    if environ.get('ARC_LEDGER_XSESSION') == '1':
        try:
            from .session_power import SleepGuard
            window._sleep_guard = SleepGuard(window)
        except Exception:  # noqa: BLE001 - without logind or a locker, there is nothing to guard
            pass
