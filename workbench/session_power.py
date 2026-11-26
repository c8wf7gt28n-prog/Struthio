"""Leaving, logging out, restarting and shutting down, from the System menu (HATCH DESK D2; the owner's brief of 2026-11-06:
"Put Log out, Return to Debian, Restart, and Shut down in a separated group, as applicable, with session and machine scope
clear").

The brief supersedes the earlier rule that Graphite issues no session or power command (and the old menu's disabled row "not in
this edition"). What stays of that rule: Graphite never uses sudo, never asks for a password itself and never acts without the
owner's confirmation, and it uses only the system's own interfaces:

  availability   systemd-logind on the system D-Bus (org.freedesktop.login1, in this process, nothing started): the Manager's
                 CanReboot and CanPowerOff ('yes' is offered; 'challenge' is offered where the system can ask for permission,
                 but not in the dedicated session, which has no permission prompt; 'na' and 'no' show the action unavailable
                 with the reason) and this program's own login session (the session object 'self' and its Id)
  Log out        loginctl terminate-session <this session's id>       scope: this login session
  Restart        systemctl reboot                                     scope: this computer
  Shut down      systemctl poweroff                                   scope: this computer
  Return to Debian (the dedicated session, ARC_LEDGER_XSESSION=1) or Exit Graphite (elsewhere): the existing leave, no command
                                                                       scope: this Graphite session

One function, system(), asks logind, looks the two programs up and issues every command, so tests and checks patch one place.
With no logind session (a container, a program started outside a login) every action is unavailable with that reason, and
run_action refuses before anything is asked or issued.

The order of Log out, Restart and Shut down (D2-fix, after the review of D2):
  1. availability: unavailable -> refused with the whole reason, nothing asked, Graphite stays open;
  2. the leave flow's questions, nothing stopped yet (leave_steps: keep or skip a return copy, save or discard each edited file;
     Continue working ends it there);
  3. the confirmation naming the scope (Cancel is the default; Cancel leaves everything as it was, nothing stopped);
  4. availability again and the program looked up: either fails -> Graphite stays open and says why, nothing stopped;
  5. Graphite closes the ordinary way with nothing asked again (quiet_close: the window's own close, so running assignments
     pause or go to the Graphite service, Graphite's services close, the local model and the tracked command stop, the session
     is saved); if the close is refused, Graphite stays open and nothing is issued;
  6. the command, through system(). Ending the session or the computer ends Graphite's process and its display at once (logind
     sends every process of the session SIGTERM, and the X server goes with it), so nothing of the close can come after the
     command: it comes before. If the command then does not start (the system's own permission prompt declined, say), Graphite
     has already closed the ordinary way with the work saved; it says why in a last message, and you start it again.

Graphite 1.0 S1 (the session that survives) adds Lock and Suspend, which keep Graphite and the programs open, and the session
group reads, in GROUP's order: Lock, Suspend, Log out, Restart, Shut down, Return to Debian (each with its scope line):

  Lock           the screen locker, xsecurelock, started in a session of its own (session_launch.launch, so a Graphite crash
                 never unlocks the screen), told to touch a mark once the screen is locked; the lock counts as taken only when
                 that mark appears. The password is typed into the locker (the system's own PAM), never into Graphite. With no
                 locker installed, or no X display, Lock is unavailable and says why; nothing is done.
                                                                       scope: this screen
  Suspend        logind CanSuspend for availability (as CanReboot), the lock taken first and confirmed, then logind Suspend
                 (non-interactive). No lock, no suspend: if the locker cannot be had, Suspend is unavailable or refused with the
                 reason. Graphite saves its session first and stays open.  scope: this computer
  availability   lists all six actions (Return to Debian or Exit Graphite always available, with its tip).
  sleep_held     logind's delay lock on sleep (Inhibit "sleep", mode delay) while Kasandra writes a file, released when the
                 write is done, so a suspend never lands mid-write; without logind the write simply goes on.
  SleepGuard     in the dedicated session: a delay lock held while nothing is locked, so a suspend from anywhere (the lid,
                 logind's idle action) locks the screen first; logind's Lock signal for this session locks too.

Lock's start and Suspend's request go through system() as well ('start' and 'logind'), and the inhibitor ('inhibit').
"""
from __future__ import annotations
import contextlib
import os
import re
import sys
import time

ACTIONS = ('logout', 'restart', 'shutdown')      # the actions that close Graphite and then ask the system (run_action)
STAYS = ('lock', 'suspend')                      # 1.0 S1: the actions that keep Graphite and the programs open
GROUP = ('lock', 'suspend', 'logout', 'restart', 'shutdown', 'leave')   # 1.0 S1: the session group, top to bottom
WORDS = {'lock': 'Lock', 'suspend': 'Suspend', 'logout': 'Log out', 'restart': 'Restart', 'shutdown': 'Shut down'}
SCOPES = {'lock': 'this screen', 'suspend': 'this computer', 'logout': 'this login session', 'restart': 'this computer',
          'shutdown': 'this computer', 'leave': 'this Graphite session'}
EFFECTS = {'lock': 'Locks the screen: Graphite and your apps keep running behind it. Your password unlocks it, typed into the '
                   'screen locker (the system\'s own), never into Graphite.',
           'suspend': 'Locks the screen, then puts this computer to sleep: everything stays open in memory and comes back when it '
                      'wakes. Your password unlocks it.',
           'logout': 'Ends your login session on this computer: Graphite and every program started in this session close. The computer stays on.',
           'restart': 'Restarts this computer: every program on it closes, then it starts again.',
           'shutdown': 'Shuts this computer down: every program on it closes and it powers off.'}
THEN = {'logout': 'your login session ends', 'restart': 'this computer restarts', 'shutdown': 'this computer shuts down'}
COMMANDS = {'logout': ('loginctl', 'terminate-session', '{session}'), 'restart': ('systemctl', 'reboot'), 'shutdown': ('systemctl', 'poweroff')}
PROGRAMS = ('loginctl', 'systemctl')  # the only programs run() starts; never sudo, never a shell
CAN = {'restart': 'CanReboot', 'shutdown': 'CanPowerOff'}
LOGIND = 'org.freedesktop.login1'
MANAGER = ('/org/freedesktop/login1', 'org.freedesktop.login1.Manager')
SELF = '/org/freedesktop/login1/session/self'  # logind's name for the caller's own session
PROPERTIES = 'org.freedesktop.DBus.Properties'
SESSION_ID = re.compile(r'^[A-Za-z0-9_.-]{1,64}$')
TIMEOUT_MS = 2000
NO_SESSION = ('No login session: Graphite is not running inside a systemd-logind session on this computer (as in a container, '
              'or when it was started without a login), so it cannot log out, restart or shut down. Use the system\'s own controls.')
NOT_LINUX = 'Log out, Restart and Shut down need Linux with systemd-logind; use the system\'s own controls.'
# 1.0 S1: Lock and Suspend
LOCKERS = ('xsecurelock',)                       # the only locker Graphite starts (the 1.0 System set carries it)
LOCK_SECONDS = 5.0                               # how long the locker has to say the screen is locked
CAN_SUSPEND = 'CanSuspend'
NOT_LINUX_STAYS = 'Lock and Suspend need Linux with an X display and systemd-logind; use the system\'s own controls.'
NO_LOCKER = ('No screen locker is installed on this computer: Lock needs xsecurelock (it is in the 1.0 System set, and Debian '
             'has it as the package xsecurelock). Without it Graphite cannot lock the screen, so nothing was done.')
NO_DISPLAY = 'Lock needs this session\'s X display, and there is none here (DISPLAY is not set), so nothing was done.'
STAYS_BEFORE = {'lock': 'Nothing is closed or stopped: Graphite and your apps keep running behind the lock.',
                'suspend': 'Graphite stays open and saves its session; the screen is locked first, and the computer is put to sleep '
                           'only once the lock is confirmed. A file Kasandra is writing is finished before it sleeps.'}
NO_PROMPT = ('this dedicated session has no permission prompt to answer it (logind: challenge). Return to Debian, then use '
             'systemctl %s at the text login, where the system asks for permission itself')
LEAVE = 'Save or discard open work, keep or skip a return copy, stop the local model and tracked commands, and close Graphite.'
BEFORE = ('First Graphite asks about your open work, as when you leave (keep or skip a return copy, save or discard each edited '
          'file), then asks you to confirm. Nothing is stopped before you confirm; then Graphite closes the ordinary way and asks '
          'the system.')
LOGIND_WORDS = {'na': 'this computer does not offer it (logind: na)', 'no': 'your account may not do it here (logind: no)'}


def system(request):
    """The one place Graphite speaks to the operating system's session and power interfaces (tests and checks patch it).

    ('logind', path, interface, method, *args): one systemd-logind call on the system D-Bus, in this process (QtDBus); returns
        the reply's first value, or raises OSError when there is no system bus or logind refuses.
    ('where', program): the path of loginctl or systemctl on PATH, or None (a look-up: nothing starts).
    ('run', argv): starts argv[0] (loginctl or systemctl, found on PATH, never sudo, no shell, no terminal) and waits for it;
        returns dict(ok, code, reason).
    ('start', argv): 1.0 S1, the screen locker (xsecurelock only) started in a session of its own through session_launch,
        not waited for; returns session_launch.launch's dict(ok, pid, reason, ...).
    ('inhibit', what, who, why, mode): 1.0 S1, logind's Inhibit on the system D-Bus; returns a file descriptor this process
        owns (closing it releases the lock), or raises OSError."""
    kind = request[0]
    if kind == 'logind':return _logind(*request[1:])
    if kind == 'where':return _where(request[1])
    if kind == 'run':return _run(tuple(request[1]))
    if kind == 'start':return _start(tuple(request[1]))
    if kind == 'inhibit':return _inhibit(*request[1:])
    raise ValueError('Unknown system request: %r' % (kind,))


def _logind(path, interface, method, *args):
    from PySide6.QtDBus import QDBusConnection, QDBusInterface, QDBusMessage
    bus = QDBusConnection.systemBus()
    if not bus.isConnected():raise OSError('no system D-Bus: ' + (bus.lastError().message() or 'not connected'))
    face = QDBusInterface(LOGIND, path, interface, bus);face.setTimeout(TIMEOUT_MS)
    reply = face.call(method, *args)
    if reply.type() == QDBusMessage.ErrorMessage:raise OSError(reply.errorMessage() or reply.errorName() or 'logind refused')
    values = reply.arguments()
    value = values[0] if values else None
    return value.variant() if hasattr(value, 'variant') else value


def _where(program):
    import shutil
    if program not in PROGRAMS + LOCKERS:raise ValueError('Graphite looks up only loginctl, systemctl or the screen locker here: %r' % (program,))
    return shutil.which(program)


def _start(argv):
    """1.0 S1: the screen locker, in a session of its own (it outlives a Graphite crash: the screen stays locked)."""
    if not argv or argv[0] not in LOCKERS:
        raise ValueError('Graphite starts only the screen locker here: %r' % (argv,))
    path = _where(argv[0])
    if path is None:return dict(ok=False, pid=None, reason=NO_LOCKER)
    from .session_launch import launch
    return launch([path, *argv[1:]], name=argv[0])


def _descriptor(value):
    """The file descriptor in logind's answer (a QDBusUnixFileDescriptor, or what PySide6 makes of it), duplicated so this
    process owns it; the wrapper closes its own copy when it goes."""
    if hasattr(value, 'variant') and not hasattr(value, 'fileDescriptor'):value = value.variant()
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:return os.dup(value)
    getter = getattr(value, 'fileDescriptor', None)
    fd = getter() if callable(getter) else -1
    if not isinstance(fd, int) or fd < 0:raise OSError('logind gave no file descriptor (%s)' % type(value).__name__)
    return os.dup(fd)


def _inhibit(what, who, why, mode):
    from PySide6.QtDBus import QDBusConnection, QDBusInterface, QDBusMessage
    bus = QDBusConnection.systemBus()
    if not bus.isConnected():raise OSError('no system D-Bus: ' + (bus.lastError().message() or 'not connected'))
    face = QDBusInterface(LOGIND, MANAGER[0], MANAGER[1], bus);face.setTimeout(TIMEOUT_MS)
    reply = face.call('Inhibit', str(what), str(who), str(why), str(mode))
    if reply.type() == QDBusMessage.ErrorMessage:raise OSError(reply.errorMessage() or reply.errorName() or 'logind refused')
    values = reply.arguments()
    return _descriptor(values[0] if values else None)


def _run(argv):
    import subprocess
    if not argv or argv[0] not in PROGRAMS or any(part in ('sudo', 'pkexec', 'su', 'doas') for part in argv):
        raise ValueError('Graphite runs only loginctl or systemctl here, never through sudo: %r' % (argv,))
    path = _where(argv[0])
    if path is None:return dict(ok=False, code=None, reason=argv[0] + ' is not installed on this computer')
    try:
        done = subprocess.run([path, *argv[1:]], stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as exc:
        return dict(ok=False, code=None, reason=str(exc))
    said = (done.stderr or done.stdout or '').strip()
    return dict(ok=done.returncode == 0, code=done.returncode, reason=said[-500:] or ('exit status %d' % done.returncode))


def dedicated(environ=None):
    """True in the dedicated session (the marker ARC_LEDGER_XSESSION=1 that LS_XSESSION.sh exports)."""
    environ = os.environ if environ is None else environ
    return environ.get('ARC_LEDGER_XSESSION') == '1'


def session_exit(environ=None):
    """The leave row's words, by the session Graphite was started in: Return to Debian in the dedicated session, Exit Graphite
    elsewhere. Both close Graphite the ordinary way."""
    if dedicated(environ):
        return dict(dedicated=True, label='Return to Debian', scope=SCOPES['leave'],
                    tip=LEAVE + ' This ends the dedicated graphical session and returns to the Debian text login. The computer stays on.')
    return dict(dedicated=False, label='Exit Graphite', scope=SCOPES['leave'],
                tip=LEAVE + ' The desktop you started Graphite from stays open. The computer stays on.')


def _unavailable(reason, actions=ACTIONS):
    return {action:dict(available=False, reason=reason, value=None, session=None) for action in actions}


def _lock_state(environ):
    """1.0 S1: Lock's availability: the locker installed, and an X display to lock. A failure to look is 'unavailable'."""
    try:found = system(('where', LOCKERS[0]))
    except Exception as exc:  # noqa: BLE001 - reading availability never fails the menu; it says what went wrong
        return dict(available=False, reason='Graphite could not look for a screen locker: %s' % (str(exc).strip()[:160] or type(exc).__name__),
                    value=None, session=None, program=None)
    if not found:return dict(available=False, reason=NO_LOCKER, value=None, session=None, program=None)
    if not environ.get('DISPLAY'):return dict(available=False, reason=NO_DISPLAY, value=None, session=None, program=found)
    return dict(available=True, reason='Locks with %s (installed at %s).' % (LOCKERS[0], found), value='yes', session=None, program=found)


def _ordered(out):
    return {key:out[key] for key in GROUP if key in out}


def availability(platform=None, environ=None, only=None):
    """{action: dict(available, reason, value, session)} for the session group's six actions (1.0 S1), in GROUP's order: Lock
    (the locker and a display), Suspend, Log out, Restart and Shut down (from logind), and the leave row (always available,
    with its label). `only`: the actions wanted (run_action asks for its own alone). No session: Suspend, Log out, Restart and
    Shut down unavailable with NO_SESSION. 'challenge' (the system asks for permission itself) is offered, except in the
    dedicated session: it starts no permission agent (LS_XSESSION.sh runs fluxbox and Graphite only) and the command runs
    without a terminal, so nothing could answer the system's question, and Graphite would have closed for nothing. Suspend
    needs Lock: no locker, no suspend."""
    environ = os.environ if environ is None else environ
    wanted = [key for key in GROUP if only is None or key in only]
    out = {}
    if 'leave' in wanted:
        leave = session_exit(environ)
        out['leave'] = dict(available=True, reason=leave['tip'], value=None, session=None, label=leave['label'])
    if not (platform or sys.platform).startswith('linux'):
        out.update(_unavailable(NOT_LINUX, [a for a in ACTIONS if a in wanted]))
        out.update(_unavailable(NOT_LINUX_STAYS, [a for a in STAYS if a in wanted]))
        return _ordered(out)
    lock = _lock_state(environ) if ('lock' in wanted or 'suspend' in wanted) else None
    if 'lock' in wanted:out['lock'] = lock
    logind = [a for a in ('suspend', *ACTIONS) if a in wanted]
    if not logind:return _ordered(out)
    try:
        session = system(('logind', SELF, PROPERTIES, 'Get', 'org.freedesktop.login1.Session', 'Id'))
    except (OSError, ValueError, RuntimeError, ImportError) as exc:
        out.update(_unavailable(NO_SESSION + ' (' + str(exc).strip()[:160] + ')', logind));return _ordered(out)
    session = str(session or '')
    if not SESSION_ID.fullmatch(session):out.update(_unavailable(NO_SESSION + ' (logind gave no session id)', logind));return _ordered(out)
    if 'logout' in wanted:
        out['logout'] = dict(available=True, reason='Ends login session %s (loginctl terminate-session).' % session, value='yes', session=session)
    asked = {action:method for action, method in (*CAN.items(), ('suspend', CAN_SUSPEND)) if action in wanted}
    for action, method in asked.items():
        try:value = str(system(('logind', *MANAGER, method)) or '')
        except Exception as exc:  # noqa: BLE001 - an answer that cannot be read is 'unavailable', with what went wrong
            out[action] = dict(available=False, reason='logind did not answer %s: %s' % (method, str(exc).strip()[:160] or type(exc).__name__), value=None, session=session);continue
        offered = value == 'yes' or (value == 'challenge' and not dedicated(environ))
        if value == 'yes':reason = 'Allowed for your account (logind %s: yes).' % method
        elif offered:reason = 'Allowed after the system asks for permission (logind %s: challenge).' % method
        elif value == 'challenge':reason = WORDS[action] + ' is unavailable here: ' + NO_PROMPT % {'restart':'reboot', 'shutdown':'poweroff', 'suspend':'suspend'}[action] + '.'
        else:reason = WORDS[action] + ' is unavailable: ' + LOGIND_WORDS.get(value, 'logind answered %r' % value) + '.'
        if action == 'suspend' and offered and not lock['available']:
            offered = False;reason = 'Suspend is unavailable here: it locks the screen first. ' + lock['reason']
        elif action == 'suspend' and offered:reason += ' The screen is locked first, with ' + LOCKERS[0] + '.'
        out[action] = dict(available=offered, reason=reason, value=value, session=session)
    return _ordered(out)


def command(action, state):
    """The argv for an available action (the session id filled in for Log out)."""
    return tuple(part.replace('{session}', str(state.get('session') or '')) for part in COMMANDS[action])


def describe(action, state):
    """A row's tooltip: what the action does, its scope, what happens first, and whether it is available and why."""
    before = STAYS_BEFORE.get(action, BEFORE)   # 1.0 S1: Lock and Suspend close nothing
    return '%s\nScope: %s.\n%s\n%s' % (EFFECTS[action], SCOPES[action], before, state['reason'] if state['available'] else 'Unavailable: ' + state['reason'])


# The leave flow's questions, without closing the window and without stopping anything ---------------------------------------

def leave_steps(host):
    """The existing leave flow's questions, in its order, while the window stays open: the return copy (Keep and close / Close
    without a new return copy / Continue working, return_thread_qt's own dialog), each working area's own close question, and
    each edited file (save or discard, the window's own question; a discarded file keeps a recovery copy, as on close, and its
    buffer stays as it is). Nothing is stopped and no return copy is taken here: those belong to the close, after the owner
    confirms. None when the owner chose to continue working or a save failed (anything set aside is put back); else
    dict(keep, discarded, owned)."""
    thread = getattr(host, 'return_thread', None);keep = True
    if thread is not None and hasattr(thread, 'exit_dialog'):
        answer = thread.exit_dialog().exec()
        if answer not in (1, 2):return None
        keep = answer == 1
    left = dict(keep=keep, discarded=[], owned=[]);tabs = getattr(host, 'tabs', None)
    if tabs is not None:
        for i in range(tabs.count()):
            tab = tabs.widget(i)
            if hasattr(tab, 'can_close_concern') and not tab.can_close_concern():return None
            if hasattr(tab, 'can_close_pdf') and not tab.can_close_pdf():return None
        for i in range(tabs.count()):
            editor = tabs.widget(i)
            if type(editor).__name__ != 'CodeEditor' or not editor.document().isModified():continue
            tabs.setCurrentWidget(editor);answer = host.ask_save(editor.path.name)
            if answer == 'cancel' or (answer == 'save' and not host.save_document(editor)):undo_leave(left);return None
            if answer == 'discard':
                from . import engine
                owned = getattr(editor, 'recovery_owned', False)
                try:host.recovery.put(engine.rel(editor.path, host.root), editor.toPlainText(), editor.disk_sha256);editor.recovery_owned = False
                except (OSError, ValueError) as exc:
                    host.statusBar().showMessage('Recovery copy unavailable: ' + str(exc), 10000);undo_leave(left);return None
                left['discarded'].append(editor);left['owned'].append(owned)
    return left


def undo_leave(left):
    """Cancel after the questions: each discarded file's buffer stays edited (it always did) and owns its recovery copy again,
    as before the question; nothing else was changed (a file you chose to save stays saved)."""
    for editor, owned in zip(left.get('discarded', ()), left.get('owned', ())):
        try:editor.recovery_owned = owned
        except RuntimeError:pass


def quiet_close(host, left):
    """Close Graphite the ordinary way, the questions already answered in leave_steps, so the close asks none again: the return
    copy is taken by the close only when the owner chose to keep one (as return_thread_qt.review_exit does), a discarded file's
    buffer no longer counts as edited (its recovery copy stays). Everything else is the window's own close: running assignments
    pause or go to the Graphite service, Graphite's services close, the local model and the tracked command stop, the session is
    saved. Returns True when the window closed; when its close was refused, the discarded buffers count as edited again."""
    thread = getattr(host, 'return_thread', None);discarded = list(left.get('discarded', ()))
    for editor in discarded:editor.document().setModified(False)
    if thread is not None and hasattr(thread, 'skip_keep_once'):thread.skip_keep_once = not left.get('keep', True)
    try:closed = host.close() is not False
    finally:
        if thread is not None and hasattr(thread, 'skip_keep_once'):thread.skip_keep_once = False
    if not closed:
        for editor in discarded:editor.document().setModified(True)
    return closed


def confirm(host, action):
    """The confirmation naming the action's scope; Cancel is the default. Nothing has been stopped when it is asked."""
    from PySide6.QtWidgets import QMessageBox
    title = {'logout':'Log out of this login session?', 'restart':'Restart this computer?', 'shutdown':'Shut down this computer?'}[action]
    text = (EFFECTS[action] + '\n\nGraphite closes first, the ordinary way: the return copy and your open files as you chose, running '
            'assignments paused (or continued by the Graphite service), the local model and the tracked command stopped, the session '
            'saved. Then ' + THEN[action] + '.\n\nCancel leaves Graphite open as it is: nothing has been stopped.')
    return QMessageBox.question(host, title, text, QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel) == QMessageBox.Yes


def tell(host, title, text):
    """Say why in a dialog (the whole reason) and, while the window is open, in the status line (the title only: a long line
    there would take room from the panes while it lasts). After Graphite has closed, the dialog stands alone."""
    from PySide6.QtWidgets import QMessageBox
    open_ = host is not None and (not hasattr(host, 'isVisible') or host.isVisible())
    if open_ and hasattr(host, 'statusBar'):host.statusBar().showMessage(title + ' · Graphite stays open', 10000)
    QMessageBox.warning(host if open_ else None, title, text)


def _say(host, text):
    if hasattr(host, 'statusBar'):host.statusBar().showMessage(text, 8000)


def _end(app):
    """Graphite closed for the action: the application ends as after any close (the last window's automatic quit was held so a
    last message could still be shown)."""
    if app is not None:app.quit()


def run_action(host, action, platform=None):
    """Log out, Restart or Shut down, in the module's order: availability, the leave flow's questions, the confirmation naming
    the scope, availability again and the program looked up, the ordinary close, then the system's own command through system().
    Returns dict(state=UNAVAILABLE | CANCELLED | FAILED | STARTED, closed, ...). Nothing is issued without a logind session,
    nothing is stopped before the owner confirms, and the command comes only after Graphite has closed."""
    if action not in ACTIONS:raise ValueError('Unknown action: %r' % (action,))
    state = availability(platform, only=(action,))[action]
    if not state['available']:
        tell(host, WORDS[action] + ' is unavailable', state['reason'] + '\nGraphite stays open.');return dict(state='UNAVAILABLE', reason=state['reason'], closed=False)
    left = leave_steps(host)
    if left is None:return dict(state='CANCELLED', step='leave', closed=False)
    if not confirm(host, action):
        undo_leave(left);_say(host, WORDS[action] + ' cancelled · Graphite stays open; nothing was stopped')
        return dict(state='CANCELLED', step='confirm', left=left, closed=False)
    state = availability(platform, only=(action,))[action]  # again: the session or the permission may have changed while the questions were open
    if not state['available']:
        undo_leave(left);tell(host, WORDS[action] + ' is unavailable', state['reason'] + '\nGraphite stays open; nothing was stopped.')
        return dict(state='UNAVAILABLE', reason=state['reason'], left=left, closed=False)
    argv = command(action, state)
    try:found = system(('where', argv[0]))
    except (OSError, ValueError, RuntimeError) as exc:found = None;missing = str(exc)
    else:missing = argv[0] + ' is not installed on this computer'
    if not found:
        undo_leave(left);tell(host, WORDS[action] + ' cannot start', '%s cannot start: %s.\n\nGraphite stays open; nothing was stopped.' % (WORDS[action], missing))
        return dict(state='FAILED', reason=missing, argv=list(argv), left=left, closed=False)
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance();quit_rule = app.quitOnLastWindowClosed() if app is not None else None
    if app is not None:app.setQuitOnLastWindowClosed(False)  # the close must not end the application before the command and its answer
    closed = False
    try:
        closed = quiet_close(host, left)
        if not closed:
            undo_leave(left);_say(host, WORDS[action] + ' stopped: Graphite did not close · nothing was issued')
            return dict(state='CANCELLED', step='close', left=left, closed=False)
        try:result = system(('run', argv))
        except (OSError, ValueError, RuntimeError) as exc:result = dict(ok=False, code=None, reason=str(exc))
        if not result.get('ok'):
            tell(host, WORDS[action] + ' did not start', '%s did not start: %s\n\nGraphite had already closed the ordinary way (it must, before '
                 'the session or the computer ends): your work was saved or set aside as you chose and its session is saved. Start '
                 'Graphite again, or use the system\'s own controls.' % (WORDS[action], result.get('reason') or 'no reason given'))
            return dict(state='FAILED', reason=result.get('reason'), argv=list(argv), left=left, closed=True)
        return dict(state='STARTED', argv=list(argv), left=left, closed=True)
    finally:
        if app is not None:app.setQuitOnLastWindowClosed(quit_rule)
        if closed:_end(app)


def leave(host):
    """Return to Debian or Exit Graphite: the existing leave, the return-thread review (default Continue working), then the
    window's own close with its save prompts. No command is issued."""
    thread = getattr(host, 'return_thread', None)
    if thread is not None and hasattr(thread, 'review_exit'):return thread.review_exit()
    return host.close()


# 1.0 S1 · Lock, Suspend, the sleep inhibitor and the guard -----------------------------------------------------------------

def locked_by(environ=None):
    """The process id of the screen locker Graphite started that still runs (the screen is locked), or None."""
    from .session_launch import launched
    for row in launched(environ):
        if row.get('name') in LOCKERS:return row['pid']
    return None


def lock_screen(platform=None, environ=None, wait=LOCK_SECONDS, nap=time.sleep):
    """Lock the screen: the locker started through system() in a session of its own, told to touch a mark once the screen is
    locked. Returns dict(state, locked, reason, pid): LOCKED only when the mark appeared (or Graphite's locker already runs);
    UNAVAILABLE (no locker, no display: nothing done), FAILED (it did not start, or ended without locking) or UNCONFIRMED (it
    runs, but did not say so within `wait` seconds)."""
    environ = os.environ if environ is None else environ
    state = availability(platform, environ, only=('lock',))['lock']
    if not state['available']:return dict(state='UNAVAILABLE', locked=False, pid=None, reason=state['reason'])
    held = locked_by(environ)
    if held:return dict(state='LOCKED', locked=True, pid=held, reason='The screen is already locked.')
    from .session_launch import session_dir, start_time
    try:folder = session_dir(environ)
    except OSError as exc:return dict(state='FAILED', locked=False, pid=None, reason='Graphite has no session folder for the lock\'s mark: %s' % exc)
    mark = folder / ('locked-%d-%d' % (os.getpid(), time.monotonic_ns()))
    try:started = system(('start', (LOCKERS[0], '--', 'touch', str(mark))))
    except (OSError, ValueError, RuntimeError) as exc:started = dict(ok=False, reason=str(exc))
    if not started.get('ok'):
        return dict(state='FAILED', locked=False, pid=None, reason='The screen locker did not start: ' + str(started.get('reason') or 'no reason given'))
    pid = started['pid'];deadline = time.monotonic() + max(0.0, float(wait))
    while True:
        if mark.exists():
            try:mark.unlink()
            except OSError:pass
            return dict(state='LOCKED', locked=True, pid=pid, reason='The screen is locked (%s confirmed it).' % LOCKERS[0])
        if start_time(pid) is None:
            return dict(state='FAILED', locked=False, pid=pid, reason='The screen locker ended without locking the screen (another program may be holding the keyboard).')
        if time.monotonic() >= deadline:
            return dict(state='UNCONFIRMED', locked=False, pid=pid,
                        reason='The screen locker started but did not say the screen was locked within %d seconds.' % round(wait))
        nap(0.05)


def _save_session(host):
    session = getattr(host, 'session', None)
    try:
        if session is not None and hasattr(session, 'save'):session.save()
    except Exception:  # noqa: BLE001 - a session that cannot be saved now is saved at the ordinary close; the suspend goes on
        pass


def run_lock(host, platform=None):
    """Lock, from the session group: nothing is closed or stopped. Says why when the screen could not be locked."""
    result = lock_screen(platform)
    if result['locked']:_say(host, 'Locked · your password unlocks it');return result
    title = {'UNAVAILABLE':'Lock is unavailable', 'UNCONFIRMED':'Lock is not confirmed'}.get(result['state'], 'Lock did not happen')
    tell(host, title, result['reason'] + '\nGraphite stays open as it is; nothing else was done.')
    return result


def run_suspend(host, platform=None):
    """Suspend, from the session group: availability (logind CanSuspend, and the locker), Graphite's session saved, the screen
    locked and the lock confirmed, then logind Suspend. No confirmed lock, no suspend. Graphite stays open throughout.
    Returns dict(state=UNAVAILABLE | FAILED | STARTED, locked, step, reason)."""
    state = availability(platform, only=('suspend',))['suspend']
    if not state['available']:
        tell(host, 'Suspend is unavailable', state['reason'] + '\nGraphite stays open; nothing was done.')
        return dict(state='UNAVAILABLE', locked=False, step='availability', reason=state['reason'])
    _save_session(host)
    locked = lock_screen(platform)
    if not locked['locked']:
        tell(host, 'Suspend did not start', 'Suspend locks the screen first, and the lock was not confirmed: ' + locked['reason']
             + '\nSo the computer was not put to sleep; Graphite stays open as it is.')
        return dict(state='FAILED', locked=False, step='lock', reason=locked['reason'])
    try:system(('logind', *MANAGER, 'Suspend', False))
    except (OSError, ValueError, RuntimeError) as exc:
        reason = str(exc).strip()[:300] or 'no reason given'
        tell(host, 'Suspend did not start', 'The screen is locked, but logind did not put the computer to sleep: %s\nGraphite stays open as it is.' % reason)
        return dict(state='FAILED', locked=True, step='suspend', reason=reason)
    return dict(state='STARTED', locked=True, step='suspend', pid=locked.get('pid'), reason='Locked, then logind was asked to suspend.')


@contextlib.contextmanager
def sleep_held(why, who='Graphite'):
    """While Kasandra writes a file: logind's delay lock on sleep (Inhibit 'sleep', mode 'delay'), so a suspend waits until
    the write is done (logind waits at most its InhibitDelayMaxSec). Yields True when the lock is held; without logind (no
    system bus, another system) it yields False and the write goes on. Released however the write ends."""
    fd = None
    try:
        got = system(('inhibit', 'sleep', who, why, 'delay'))
        fd = got if isinstance(got, int) and not isinstance(got, bool) and got >= 0 else None
    except Exception:  # noqa: BLE001 - no inhibitor here: the write is not held up for it
        fd = None
    try:yield fd is not None
    finally:
        if fd is not None:
            try:os.close(fd)
            except OSError:pass


_GUARD = None


def SleepGuard(parent=None, environ=None):  # noqa: N802 - built like a class, made on first use (Qt is imported then)
    """In the dedicated session: lock the screen before the computer sleeps, whoever asked for the sleep (the lid, logind's
    idle action, Suspend). Holds logind's delay lock on sleep while the screen is not locked; on PrepareForSleep(true) it locks
    (lock_screen, up to LOCK_SECONDS) and lets go, on PrepareForSleep(false) it takes the lock again. logind's Lock signal for
    this session locks too. Raises OSError where it cannot work (no locker, no system bus, logind not listening): then it
    holds nothing, so it never delays a suspend for nothing."""
    global _GUARD
    if _GUARD is None:_GUARD = _guard_class()
    return _GUARD(parent, environ)


def _guard_class():
    from PySide6.QtCore import QObject, SLOT, Slot
    from PySide6.QtDBus import QDBusConnection

    class Guard(QObject):
        WHY = 'Lock the screen before the computer sleeps'

        def __init__(self, parent=None, environ=None):
            super().__init__(parent)
            self.environ = os.environ if environ is None else environ;self.fd = None;self.seen = []
            lock = availability(environ=self.environ, only=('lock',))['lock']
            if not lock['available']:raise OSError(lock['reason'])
            bus = QDBusConnection.systemBus()
            if not bus.isConnected():raise OSError('no system D-Bus')
            self.listening = bool(bus.connect(LOGIND, MANAGER[0], MANAGER[1], 'PrepareForSleep', self, SLOT('sleeping(bool)')))
            if not self.listening:raise OSError('logind\'s PrepareForSleep cannot be heard here')
            path = self.session_path()
            self.locks = bool(path) and bool(bus.connect(LOGIND, path, 'org.freedesktop.login1.Session', 'Lock', self, SLOT('locking()')))
            self.hold()

        def session_path(self):
            try:
                ident = system(('logind', SELF, PROPERTIES, 'Get', 'org.freedesktop.login1.Session', 'Id'))
                value = system(('logind', *MANAGER, 'GetSession', str(ident or '')))
            except Exception:  # noqa: BLE001 - without the session's path, logind's Lock signal is not heard; the guard still works
                return ''
            path = value.path() if hasattr(value, 'path') else str(value or '')
            return path if path.startswith('/org/freedesktop/login1/session/') else ''

        def hold(self):
            if self.fd is not None:return
            try:fd = system(('inhibit', 'sleep', 'Graphite', self.WHY, 'delay'))
            except Exception:  # noqa: BLE001 - without the delay lock the guard still locks on PrepareForSleep, if logind waits
                fd = None
            self.fd = fd if isinstance(fd, int) and not isinstance(fd, bool) and fd >= 0 else None

        def release(self):
            fd, self.fd = self.fd, None
            if fd is not None:
                try:os.close(fd)
                except OSError:pass

        @Slot(bool)
        def sleeping(self, going):
            self.seen.append(('sleep', bool(going)))
            if going:
                try:self.seen.append(('lock', lock_screen(environ=self.environ)['state']))
                finally:self.release()
            else:self.hold()

        @Slot()
        def locking(self):
            self.seen.append(('lock', lock_screen(environ=self.environ, wait=0)['state']))

    return Guard
