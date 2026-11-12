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
"""
from __future__ import annotations
import os
import re
import sys

ACTIONS = ('logout', 'restart', 'shutdown')
WORDS = {'logout': 'Log out', 'restart': 'Restart', 'shutdown': 'Shut down'}
SCOPES = {'logout': 'this login session', 'restart': 'this computer', 'shutdown': 'this computer', 'leave': 'this Graphite session'}
EFFECTS = {'logout': 'Ends your login session on this computer: Graphite and every program started in this session close. The computer stays on.',
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
        returns dict(ok, code, reason)."""
    kind = request[0]
    if kind == 'logind':return _logind(*request[1:])
    if kind == 'where':return _where(request[1])
    if kind == 'run':return _run(tuple(request[1]))
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
    if program not in PROGRAMS:raise ValueError('Graphite looks up only loginctl or systemctl here: %r' % (program,))
    return shutil.which(program)


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


def _unavailable(reason):
    return {action:dict(available=False, reason=reason, value=None, session=None) for action in ACTIONS}


def availability(platform=None, environ=None):
    """{action: dict(available, reason, value, session)} for Log out, Restart and Shut down, from logind. No session: every
    action unavailable with NO_SESSION. 'challenge' (the system asks for permission itself) is offered, except in the dedicated
    session: it starts no permission agent (LS_XSESSION.sh runs fluxbox and Graphite only) and the command runs without a
    terminal, so nothing could answer the system's question, and Graphite would have closed for nothing."""
    if not (platform or sys.platform).startswith('linux'):return _unavailable(NOT_LINUX)
    try:
        session = system(('logind', SELF, PROPERTIES, 'Get', 'org.freedesktop.login1.Session', 'Id'))
    except (OSError, ValueError, RuntimeError, ImportError) as exc:
        return _unavailable(NO_SESSION + ' (' + str(exc).strip()[:160] + ')')
    session = str(session or '')
    if not SESSION_ID.fullmatch(session):return _unavailable(NO_SESSION + ' (logind gave no session id)')
    out = {'logout':dict(available=True, reason='Ends login session %s (loginctl terminate-session).' % session, value='yes', session=session)}
    for action, method in CAN.items():
        try:value = str(system(('logind', *MANAGER, method)) or '')
        except (OSError, ValueError, RuntimeError) as exc:
            out[action] = dict(available=False, reason='logind did not answer %s: %s' % (method, str(exc).strip()[:160]), value=None, session=session);continue
        offered = value == 'yes' or (value == 'challenge' and not dedicated(environ))
        if value == 'yes':reason = 'Allowed for your account (logind %s: yes).' % method
        elif offered:reason = 'Allowed after the system asks for permission (logind %s: challenge).' % method
        elif value == 'challenge':reason = WORDS[action] + ' is unavailable here: ' + NO_PROMPT % {'restart':'reboot', 'shutdown':'poweroff'}[action] + '.'
        else:reason = WORDS[action] + ' is unavailable: ' + LOGIND_WORDS.get(value, 'logind answered %r' % value) + '.'
        out[action] = dict(available=offered, reason=reason, value=value, session=session)
    return out


def command(action, state):
    """The argv for an available action (the session id filled in for Log out)."""
    return tuple(part.replace('{session}', str(state.get('session') or '')) for part in COMMANDS[action])


def describe(action, state):
    """A row's tooltip: what the action does, its scope, what happens first, and whether it is available and why."""
    return '%s\nScope: %s.\n%s\n%s' % (EFFECTS[action], SCOPES[action], BEFORE, state['reason'] if state['available'] else 'Unavailable: ' + state['reason'])


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
    state = availability(platform)[action]
    if not state['available']:
        tell(host, WORDS[action] + ' is unavailable', state['reason'] + '\nGraphite stays open.');return dict(state='UNAVAILABLE', reason=state['reason'], closed=False)
    left = leave_steps(host)
    if left is None:return dict(state='CANCELLED', step='leave', closed=False)
    if not confirm(host, action):
        undo_leave(left);_say(host, WORDS[action] + ' cancelled · Graphite stays open; nothing was stopped')
        return dict(state='CANCELLED', step='confirm', left=left, closed=False)
    state = availability(platform)[action]  # again: the session or the permission may have changed while the questions were open
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
