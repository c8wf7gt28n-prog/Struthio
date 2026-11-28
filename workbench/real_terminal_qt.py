"""Graphite 1.1.2 C0 · A real terminal in the drop-down: xterm, embedded in it (-into), running the owner's own shell.

PLAN_1.1.md, C0. B4's drop-down Terminal ran each line as a command with no terminal device, so vim, top, less and sudo's
password prompt could not work there. On X (the Graphite session is X) with xterm installed (graphite-session depends on
it), the drop-down's body is now an xterm reparented into it: a real pseudo-terminal, the owner's configured shell (the
account's login shell), started in the Files folder. Everything else is B4's: the keys, the slide, the header, the window
that had the keys getting them back. Off X, or without xterm, the drop-down stays B4's line Terminal.

  DOS words  when the shell is bash, it starts as `bash --rcfile <Graphite's rc> -i` (real_terminal_rc): the owner's own
             ~/.bashrc first, untouched, then Enter shows "dir → ls -l" and runs the Debian command. Another shell runs as is.
  the look   xterm's own options: the look's terminal ground and words (-bg, -fg, -cr), sixteen colours that read on that
             ground, IBM Plex Mono (Graphite's own copy given to fontconfig for this xterm only) at the Terminal's size.
  the keys   while it is down, xterm has the keyboard (X input focus on it). Win+`, Ctrl+Alt+T and Ctrl+Alt+` are grabbed on
             the drop-down's own window, so they reach Graphite even inside vim, and put it away (Fluxbox's grab of the
             first two, through graphite-do, does the same from the root). Put away, the shell and what runs keep running;
             exit in the shell ends xterm and puts the drop-down away; the next drop starts a new shell.
  the bar    a Terminal or DOS row of the bar's line (the owner's own press) is handed to the shell when it waits at its
             prompt: the line is queued in Graphite's own folder and one key (Ctrl+Alt+Shift+F12, bound by the rc) takes it
             in as if typed. While a program runs there, the line is not typed and the header says why.

Kasandra's hand never types here: nothing in her code reaches this terminal, and 1.0's in-window Terminal (the one her hand
reads) is unchanged.
"""
from __future__ import annotations

import ctypes
import os
import shutil
from ctypes import POINTER, byref, c_int, c_uint, c_ulong, c_void_p
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QProcess, QProcessEnvironment, QSocketNotifier, QTimer, Qt
from PySide6.QtGui import QColor, QGuiApplication, QPalette
from PySide6.QtWidgets import QApplication, QWidget

from . import real_terminal_rc as rc

FACE = 'IBM Plex Mono,DejaVu Sans Mono,monospace'
QUEUE_KEY = 'F12'                     # with Ctrl+Alt+Shift: xterm sends ESC [24;8~, which the rc binds to "take the queued line"
SHIFT, LOCK, CONTROL, MOD1, MOD2, MOD4 = 1, 2, 4, 8, 16, 64
LOCKS = (0, LOCK, MOD2, LOCK | MOD2)  # Caps Lock and Num Lock on or off
HIDE_KEYS = (('grave', MOD4), ('t', CONTROL | MOD1), ('grave', CONTROL | MOD1))
KeyPress = 2
GrabModeAsync = 1
LIGHT = ('#1d1d1f', '#b02020', '#146a37', '#8f4f00', '#0857b8', '#5a3fa0', '#0b6e78', '#5a5a60',
         '#626268', '#c62828', '#18773f', '#9a5400', '#0a66d8', '#6a4bb5', '#0e7c86', '#1d1d1f')
DARK = ('#2a2a2e', '#ff6b60', '#34c26a', '#f0a63a', '#4c93ff', '#b49cff', '#4fc8d8', '#d0d0d6',
        '#6a6a70', '#ff8a80', '#5fd68a', '#f5b95e', '#7fb2ff', '#c4b2ff', '#83eaff', '#f2f2f5')


def why_not(platform=None, which=shutil.which, environ=None):
    """'' when the drop-down can be a real terminal here, else why not (the line Terminal stays)."""
    environ = os.environ if environ is None else environ
    if str(environ.get('GRAPHITE_REAL_TERMINAL', '')).strip() == '0':return 'GRAPHITE_REAL_TERMINAL=0'
    if (platform or QGuiApplication.platformName()) != 'xcb':return 'not on X'
    if not which('xterm'):return 'xterm is not installed'
    return ''


def folder(environ=None):
    """Graphite's own folder for this terminal (its rc, its fonts list, the bar's queued line): never the owner's files."""
    environ = os.environ if environ is None else environ
    base = environ.get('XDG_RUNTIME_DIR') or os.path.join(environ.get('XDG_CACHE_HOME') or os.path.join(os.path.expanduser('~'), '.cache'))
    path = Path(base) / 'graphite-terminal';path.mkdir(parents=True, exist_ok=True)
    try:os.chmod(path, 0o700)
    except OSError:pass
    return path


def fonts_conf(where, root=rc.ROOT):
    """A fontconfig file for this xterm only: the system's own, plus Graphite's IBM Plex Mono. None when Graphite has no copy."""
    plex = Path(root) / 'branding' / 'fonts' / 'plex'
    if not plex.is_dir():return None
    path = Path(where) / 'fonts.conf'
    path.write_text('<?xml version="1.0"?>\n<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">\n<fontconfig>\n'
                    '  <include ignore_missing="yes">/etc/fonts/fonts.conf</include>\n  <dir>%s</dir>\n</fontconfig>\n' % plex,
                    encoding='utf-8')
    return path


def look():
    """(ground, words, sixteen colours, size in points) for the look in force."""
    from . import console_qt as cq
    ground, words = cq.TERMINAL_GROUND, cq.AMBER_TEXT
    light = QColor(ground).lightness() >= 128
    px = max(12, cq.mono_font(14).pixelSize())
    from . import boss_theme as _bt      # 1.1 N1: Night's xterm is the phosphor monitor: sixteen shades of the one phosphor
    if getattr(_bt, 'PHOSPHOR', ''):return ground, words, phosphor_colours(), round(px * 0.75 * 2) / 2
    return ground, words, LIGHT if light else DARK, round(px * 0.75 * 2) / 2


def phosphor_colours(look='night'):
    """1.1 N1: xterm's sixteen colours in the phosphor Night: black, then the phosphor at its secondary brightness for the
    eight dim colours and at full for the eight bright ones (one hue; ls and prompts keep their brightness, never a hue).
    Every one but black is 4.5:1 or more on the terminal's ground (design_tokens' measure)."""
    from . import design_tokens as tokens
    c = tokens.colours(look)
    return tuple([c['raised']] + [c['secondary']] * 6 + [c['text']] + [c['tertiary']] + [c['text']] * 7)


def argv(window, shell, rc_path, size=(100, 24), extra=()):
    """xterm's command line: embedded in `window`, the look's colours and face, then the shell (bash with Graphite's rc)."""
    ground, words, colours, points = look()
    res = ['XTerm*metaSendsEscape: true', 'XTerm*termName: xterm-256color', 'XTerm*selectToClipboard: true',
           'XTerm*allowTitleOps: false', 'XTerm*borderWidth: 0', 'XTerm*cursorBlink: false',
           'XTerm*VT100.translations: #override Shift Ctrl <Key>C: copy-selection(CLIPBOARD)\\n'
           'Shift Ctrl <Key>V: insert-selection(CLIPBOARD)']
    res += ['XTerm*color%d: %s' % (n, c) for n, c in enumerate(colours)]
    out = ['xterm', '-into', str(int(window)), '-geometry', '%dx%d' % size, '-fa', FACE, '-fs', ('%g' % points),
           '-bg', ground, '-fg', words, '-cr', words, '-b', '8', '+sb', '-sl', '5000', '-title', 'Graphite · Terminal', '-u8']
    for r in res:out += ['-xrm', r]
    out += list(extra)
    if os.path.basename(shell) == 'bash':return out + ['-e', shell, '--rcfile', str(rc_path), '-i']
    return out + ['-e', shell]


# ---- X: our own connection (focus, size, the hide keys, the bar's one key) ----------------------------------------------------
class XKeyEvent(ctypes.Structure):
    _fields_ = [('type', c_int), ('serial', c_ulong), ('send_event', c_int), ('display', c_void_p), ('window', c_ulong),
                ('root', c_ulong), ('subwindow', c_ulong), ('time', c_ulong), ('x', c_int), ('y', c_int), ('x_root', c_int),
                ('y_root', c_int), ('state', c_uint), ('keycode', c_uint), ('same_screen', c_int)]


class X:
    """windows_x11's libX11 connection, with what an embedded terminal needs."""

    def __init__(self):
        from . import windows_x11 as wx
        self.wx = wx;self.b = wx.XlibBackend();x = self.b.x
        for fn, args, res in (('XMoveResizeWindow', [c_void_p, c_ulong, c_int, c_int, c_uint, c_uint], c_int),
                              ('XGrabKey', [c_void_p, c_int, c_uint, c_ulong, c_int, c_int, c_int], c_int),
                              ('XUngrabKey', [c_void_p, c_int, c_uint, c_ulong], c_int),
                              ('XStringToKeysym', [ctypes.c_char_p], c_ulong), ('XKeysymToKeycode', [c_void_p, c_ulong], ctypes.c_ubyte)):
            f = getattr(x, fn);f.argtypes = args;f.restype = res
        self.x = x;self.dpy = self.b.dpy;self.tst = None

    def code(self, name):
        return int(self.x.XKeysymToKeycode(self.dpy, self.x.XStringToKeysym(name.encode())))

    def children(self, window):
        with self.b.calls():return self.b.children(window)[0]

    def fit(self, window, w, h):
        with self.b.calls():self.x.XMoveResizeWindow(self.dpy, int(window), 0, 0, max(1, int(w)), max(1, int(h)))

    def focus(self, window):
        with self.b.calls():self.x.XSetInputFocus(self.dpy, int(window), self.wx.RevertToParent, self.wx.CurrentTime)
        return not self.wx._ERRORS

    def focused(self):
        win, revert = c_ulong(), c_int()
        with self.b.calls():self.x.XGetInputFocus(self.dpy, byref(win), byref(revert))
        return int(win.value)

    def grab(self, window, keys=HIDE_KEYS):
        done = []
        with self.b.calls():
            for name, mods in keys:
                code = self.code(name)
                if not code:continue
                for lock in LOCKS:
                    self.x.XGrabKey(self.dpy, code, mods | lock, int(window), 0, GrabModeAsync, GrabModeAsync);done.append((code, mods | lock))
        return done

    def ungrab(self, window, grabbed):
        with self.b.calls():
            for code, mods in grabbed:self.x.XUngrabKey(self.dpy, code, mods, int(window))

    def presses(self):
        """The key presses waiting on this connection: [(keycode, modifiers without the locks)]."""
        out = [];ev = self.wx.XEvent()      # windows_x11's event (XNextEvent is declared with it there)
        with self.wx._XLOCK:
            while self.x.XPending(self.dpy):
                self.x.XNextEvent(self.dpy, byref(ev))
                if ev.type == KeyPress:
                    key = ctypes.cast(byref(ev), POINTER(XKeyEvent)).contents
                    out.append((int(key.keycode), int(key.state) & ~(LOCK | MOD2)))
        return out

    def tap(self, name, mods=()):
        """One key through XTest (the bar's one key into the terminal that has the focus)."""
        if self.tst is None:
            self.tst = ctypes.CDLL('libXtst.so.6')
            self.tst.XTestFakeKeyEvent.argtypes = [c_void_p, c_uint, c_int, c_ulong];self.tst.XTestFakeKeyEvent.restype = c_int
        codes = [self.code(m) for m in mods] + [self.code(name)]
        with self.b.calls():
            for c in codes:self.tst.XTestFakeKeyEvent(self.dpy, c, 1, 0)
            for c in reversed(codes):self.tst.XTestFakeKeyEvent(self.dpy, c, 0, 0)
        return all(codes)

    def close(self):
        self.b.close_display()


# ---- the shell's state, from /proc ---------------------------------------------------------------------------------------------
def _stat(pid):
    try:text = Path('/proc/%d/stat' % pid).read_text()
    except OSError:return None
    rest = text[text.rfind(')') + 2:].split()
    return dict(state=rest[0], ppid=int(rest[1]), pgrp=int(rest[2]), tpgid=int(rest[5]))


def shell_of(xterm_pid):
    """The shell xterm runs (its child), or 0."""
    try:kids = Path('/proc/%d/task/%d/children' % (xterm_pid, xterm_pid)).read_text().split()
    except OSError:
        kids = [p for p in os.listdir('/proc') if p.isdigit() and (_stat(int(p)) or {}).get('ppid') == xterm_pid]
    return int(kids[0]) if kids else 0


def at_prompt(shell_pid):
    """Whether the shell waits at its prompt: the terminal's foreground is the shell itself, no program of it."""
    s = _stat(shell_pid) if shell_pid else None
    return bool(s) and s['tpgid'] == s['pgrp']


# ---- the area in the drop-down ---------------------------------------------------------------------------------------------------
class RealTerminal(QWidget):
    """The drop-down's body: a native window xterm is reparented into (see the module note)."""

    def __init__(self, term):
        super().__init__(term)
        self.term = term;self.process = None;self.client = 0;self.x = None;self.notifier = None;self.grabbed = [];self.grab_on = 0
        self.home = folder();self.queue = self.home / 'queued-line';self.words = '';self.extra = ()
        self.setObjectName('DropTerminalReal');self.setAccessibleName('The Terminal: your shell')
        self.setAttribute(Qt.WA_NativeWindow, True);self.setAttribute(Qt.WA_DontCreateNativeAncestors, True)
        self.setFocusPolicy(Qt.StrongFocus);self.setAutoFillBackground(True)
        ground = look()[0];pal = self.palette();pal.setColor(QPalette.Window, QColor(ground));self.setPalette(pal)
        self.wait = QTimer(self);self.wait.setInterval(40);self.wait.timeout.connect(self.find_client);self.tries = 0
        # the hide keys are read on a timer as well: an XSync of our own calls can take an event off the socket into Xlib's queue
        self.keys = QTimer(self);self.keys.setInterval(80);self.keys.timeout.connect(self.read_keys)

    # -- X
    def xconn(self):
        if self.x is None:
            self.x = X()
            self.notifier = QSocketNotifier(self.x.b.fileno(), QSocketNotifier.Read, self)
            self.notifier.activated.connect(self.read_keys)
        return self.x

    def read_keys(self, *_):
        if self.x is None:return
        hide = {(self.x.code(n), m) for n, m in HIDE_KEYS}
        if any(p in hide for p in self.x.presses()):QTimer.singleShot(0, self.term.leave)

    # -- the shell
    def running(self):
        return self.process is not None and self.process.state() != QProcess.NotRunning

    def start(self):
        if self.running():return True
        from .typebar_qt import configured_shell
        shell = configured_shell()
        path = rc.write_rc(self.home)
        try:self.queue.write_text('', encoding='utf-8')
        except OSError:pass
        env = QProcessEnvironment.systemEnvironment()
        conf = fonts_conf(self.home)
        if conf is not None:env.insert('FONTCONFIG_FILE', str(conf));env.insert('GRAPHITE_TERMINAL_FONTS', str(conf))
        env.insert('GRAPHITE_TERMINAL_QUEUE', str(self.queue))
        for name in ('TERM', 'COLUMNS', 'LINES'):env.remove(name)
        self.window().winId();wid = int(self.winId())
        p = self.process = QProcess(self);p.setProcessEnvironment(env)
        try:p.setWorkingDirectory(str(self.term.working_dir()))
        except Exception:  # noqa: BLE001 - the Files folder unknown: the home folder
            p.setWorkingDirectory(str(Path.home()))
        p.finished.connect(self.ended)
        line = argv(wid, shell, path, extra=self.extra)
        p.start(line[0], line[1:])
        self.shell = os.path.basename(shell);self.client = 0;self.tries = 0;self.wait.start()
        self.words = 'your shell: %s%s' % (self.shell, '' if self.shell == 'bash' else ' (DOS words need bash)')
        return True

    def find_client(self):
        self.tries += 1
        if self.tries > 150 or not self.running():self.wait.stop();return
        kids = self.xconn().children(int(self.winId()))
        if not kids:return
        self.wait.stop();self.client = int(kids[0]);self.fit()
        if self.term.opened:QTimer.singleShot(30, self.focus)

    def ended(self, *_):
        self.client = 0;self.process = None;self.wait.stop()
        if self.term.opened:self.term.leave()

    def stop(self):
        if self.running():self.process.terminate();self.process.waitForFinished(1500)

    def pid(self):
        return int(self.process.processId()) if self.running() else 0

    def shell_pid(self):
        return shell_of(self.pid()) if self.pid() else 0

    # -- size and keys
    def fit(self):
        if self.client:
            r = self.devicePixelRatioF();self.xconn().fit(self.client, self.width() * r, self.height() * r)

    def resizeEvent(self, event):
        super().resizeEvent(event);self.fit()

    def focus(self):
        """The keyboard to xterm (while the drop-down is down)."""
        if self.client and self.term.opened and self.term.isVisible():return self.xconn().focus(self.client)
        return False

    def focusInEvent(self, event):
        super().focusInEvent(event);QTimer.singleShot(0, self.focus)

    def dropped(self):
        """drop(): the shell started if it is not running, the hide keys grabbed, the keyboard to xterm."""
        self.start()
        try:self.term.read_words()
        except Exception:  # noqa: BLE001 - the header's words wait for the next drop
            pass
        try:
            top = int(self.term.winId())
            if not self.grabbed or self.grab_on != top:self.grabbed = self.xconn().grab(top);self.grab_on = top
        except Exception:  # noqa: BLE001 - Fluxbox's keys still put it away
            self.grabbed = []
        if self.grabbed:self.keys.start()
        for ms in (0, 60, 250):QTimer.singleShot(ms, self.focus)

    def left(self):
        """leave(): the hide keys let go (the app that gets the keys back has all of them); the shell keeps running."""
        self.keys.stop()
        if self.grabbed and self.x is not None:
            try:self.x.ungrab(self.grab_on, self.grabbed)
            except Exception:  # noqa: BLE001
                pass
        self.grabbed = []

    # -- the bar's line (the owner's own press)
    def send(self, text, waited=0):
        """Hand one line to the shell, as if typed, when it waits at its prompt; words saying what happened."""
        text = ' '.join(str(text or '').splitlines()).strip()
        if not text:return 'Nothing to run.'
        if not self.running():self.start()
        shell = self.shell_pid()
        if not (self.client and shell and at_prompt(shell)):
            if waited < 50 and self.running() and not (self.client and shell):      # just started: wait for its prompt
                QTimer.singleShot(100, lambda: self.send(text, waited + 1));return 'In the Terminal: %s' % text
            self.term.running.setText('busy: the line was not typed');return 'The Terminal is busy (a program runs there): the line was not typed.'
        if waited:
            QTimer.singleShot(400, lambda: self._type(text));return 'In the Terminal: %s' % text
        self._type(text)
        return 'In the Terminal: %s' % text

    def _type(self, text):
        self.queue.write_text(text, encoding='utf-8')
        try:os.chmod(self.queue, 0o600)
        except OSError:pass
        self.focus();self.xconn().tap(QUEUE_KEY, ('Control_L', 'Alt_L', 'Shift_L'))

    def status(self):
        return dict(real=True, running=self.running(), client=self.client, shell=self.shell_pid(), grabbed=len(self.grabbed))


class _Activated(QObject):
    """The drop-down activated again (a click on it): the keyboard back to xterm."""

    def __init__(self, real):
        super().__init__(real);self.real = real

    def eventFilter(self, obj, event):
        if event.type() == QEvent.WindowActivate:QTimer.singleShot(0, self.real.focus)
        return False


def attach(term):
    """DropTerminal.__init__: the real terminal as its body where it can be (see why_not); None leaves B4's line Terminal."""
    if why_not():return None
    real = RealTerminal(term)
    box = term.layout()
    row = term.prompt.parentWidget()
    term.output.hide();row.hide()
    box.insertWidget(box.indexOf(term.output), real, 1)
    term.installEventFilter(_Activated(real))
    app = QApplication.instance()
    if app is not None:app.aboutToQuit.connect(real.stop)
    return real
