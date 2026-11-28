"""Graphite 1.1 B4 · The drop-down Terminal: a real shell that drops from the top edge of the screen on one key, over any app.

PLAN_1.1.md, B4; the design direction's section 1 (Calm's graft: "a real terminal drops from the top edge on one key; whatever is
summoned leaves when done"). It is 1.0's Terminal (console_qt.Console's Shell page: the configured shell in your Files folder,
each line run as that shell runs it, its output as plain text, cd kept, Ctrl+C stops what runs, each command noted in the
Timeline) with W1's DOS words (dos_words: dir, cls, copy, del…, the Debian command shown above what it prints), in a window of
its own:

  where      the top of the screen, its whole width, 40 % of its height; on every desktop, above the apps and below the bar's
             flyouts (they are pop-ups). It slides down in 200 ms (at once under Reduce motion) and back up the same way.
  keys       Win+` and Ctrl+Alt+T from any app (graphite-do terminal, in Fluxbox's keys), Ctrl+Alt+T and Ctrl+Alt+` in Graphite;
             the same key puts it away, and so does exit. Esc never does: a shell needs Esc (here it clears the line, as cmd's).
  focus      it takes the keys while it is down; when it goes up the app that had them gets them back (_NET_ACTIVE_WINDOW, the
             window manager asked as a task list asks).

Nothing here acts for Kasandra or by itself: every line runs because the owner typed it and pressed Enter. HALT stops her work
and nothing else, so it does not stop what the owner runs here (Ctrl+C does, and Stop in the header).
"""
from __future__ import annotations

import os

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRect, Qt, QTimer
from PySide6.QtGui import QColor, QGuiApplication, QKeySequence, QPainter, QShortcut
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextBrowser, QTextEdit, QVBoxLayout, QWidget

from . import console_qt as cq

SLIDE_MS = 200                        # the slide down and up; none under Reduce motion
SHARE = 0.40                          # of the screen's height
LEAST = 160                           # the shortest it is on a small screen
HEAD_PX = 30                          # its header: the word Terminal, the folder, DOS words, the way to put it away
KEYS_WORDS = 'Win+` or Ctrl+Alt+T'
IN_WINDOW_KEYS = ('Ctrl+Alt+T', 'Ctrl+Alt+`')      # in Graphite's window (Fluxbox takes Win+` and Ctrl+Alt+T before any app)
HISTORY_MOST = 200
WELCOME = ('Terminal · your configured shell, in your Files folder.',
           'DOS words work too (dir, cls, copy, del, ipconfig…): the Debian command is shown above what it prints.',
           'Esc clears the line; %s, or exit, puts this away.' % KEYS_WORDS)


def band(x, y, width, height, share=SHARE):
    """(open, closed) as (x, y, w, h) for a screen at (x, y, width, height): the top `share` of it, and the same rect just
    above the screen's top edge (where it slides from)."""
    h = max(LEAST, round(height * share))
    return (x, y, width, h), (x, y - h, width, h)


def reduce_motion(host):
    try:
        from .kas_panel_qt import reduce_motion as rm
        return rm(host)
    except Exception:  # noqa: BLE001 - motion is a grace
        return False


# ---- the X window that had the keys ----------------------------------------------------------------------------------------------
def active_window():
    """The X window the window manager says is active now (_NET_ACTIVE_WINDOW), or 0 where X does not answer."""
    if QGuiApplication.platformName() != 'xcb':return 0
    try:
        from . import windows_x11 as wx
        xb = wx.XlibBackend()
    except Exception:  # noqa: BLE001 - not on X
        return 0
    try:
        with xb.calls():
            value = xb.prop(xb.root, '_NET_ACTIVE_WINDOW', wx.XA_WINDOW)
        return int(value[0]) if value else 0
    except Exception:  # noqa: BLE001
        return 0
    finally:
        xb.close_display()


def give_back(window):
    """The keys back to `window` (the window manager asked through _NET_ACTIVE_WINDOW). The backend's answer, or {} off X."""
    if not window or QGuiApplication.platformName() != 'xcb':return {}
    try:
        from . import windows_x11 as wx
        xb = wx.XlibBackend()
    except Exception:  # noqa: BLE001
        return {}
    try:
        with xb.calls():
            managed = bool(xb.manager())
        return xb.activate(int(window), managed) or {}
    except Exception as exc:  # noqa: BLE001
        return {'asked': False, 'reason': str(exc)[:120]}
    finally:
        xb.close_display()


# ---- the line -------------------------------------------------------------------------------------------------------------------
class Prompt(QLineEdit):
    """The Terminal's line: Enter runs it; Up and Down walk what was typed; Ctrl+C stops what runs (when nothing is chosen); Esc
    clears the line (never closes: a shell needs Esc); Ctrl+L clears the screen; Tab completes a name in the folder."""

    def __init__(self, term):
        super().__init__(term);self.term = term;self.setObjectName('DropTerminalLine');self.setFrame(False)
        self.setAccessibleName('Terminal: type a command, Enter runs it');self.setFont(cq.mono_font(15))

    def keyPressEvent(self, event):
        t = self.term;key = event.key();mods = event.modifiers()
        if key in (Qt.Key_Up, Qt.Key_Down):t.walk(-1 if key == Qt.Key_Up else 1);return
        if key == Qt.Key_Escape:self.clear();t.at = None;return
        if key == Qt.Key_Tab:t.complete();return
        if mods & Qt.ControlModifier and key == Qt.Key_C and t.process is not None and not self.hasSelectedText():t.stop_shell();return
        if mods & Qt.ControlModifier and key == Qt.Key_L:t.clear_screen();return
        super().keyPressEvent(event)

    def focusNextPrevChild(self, forward):
        return False      # Tab completes here; it never leaves the line


class DropTerminal(QWidget):
    """The Terminal in a window of its own at the top of the screen (see the module note)."""
    # 1.0's Terminal, the very same code (console_qt.Console's Shell page): the line run as the configured shell runs it, cd,
    # the output as plain text, Stop, the Timeline's note, DOS words first (dos_words.in_terminal).
    say = cq.Console.say
    refused = cq.Console.refused
    link = cq.Console.link
    follow = cq.Console.follow
    font_css = cq.Console.font_css
    run_shell = cq.Console.run_shell
    shell_output = cq.Console.shell_output
    shell_error = cq.Console.shell_error
    stop_shell = cq.Console.stop_shell
    working_dir = cq.Console.working_dir
    short = cq.Console.short
    sign_text = cq.Console.sign_text
    moved = cq.Console.moved
    keep_end = cq.Console.keep_end
    to_end = cq.Console.to_end

    def __init__(self, host):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.host = host;self.mode = 'shell';self.process = None;self.links = {};self.blocks = 0;self.cwd = None
        self.at_end = True;self.opened = False;self.marked = False;self.before = 0;self.graphite_before = False;self.gave = None
        self.history = [];self.at = None;self.dos_env = {};self._dos_inner = False;self.welcomed = False
        self.px = max(12, cq.mono_font(14).pixelSize())
        self.setObjectName('DropTerminal');self.setWindowTitle('Graphite · Terminal');self.setAccessibleName('The Terminal')
        self.setAttribute(Qt.WA_X11NetWmWindowTypeUtility, True)
        box = QVBoxLayout(self);box.setContentsMargins(0, 0, 0, 2);box.setSpacing(0)
        head = QWidget(self);head.setObjectName('DropTerminalHead');head.setFixedHeight(HEAD_PX);self.head = head
        row = QHBoxLayout(head);row.setContentsMargins(14, 0, 8, 0);row.setSpacing(12)
        self.title = QLabel('Terminal', head);self.title.setObjectName('DropTerminalTitle')
        self.place = QLabel('', head);self.place.setObjectName('DropTerminalPlace')
        self.dos = QLabel('', head);self.dos.setObjectName('DropTerminalDos')
        self.running = QLabel('', head);self.running.setObjectName('DropTerminalRunning')
        self.stop = QPushButton('Stop', head);self.stop.setObjectName('DropTerminalStop');self.stop.setFocusPolicy(Qt.NoFocus)
        self.stop.setToolTip('Stop what runs (Ctrl+C)');self.stop.clicked.connect(self.stop_shell);self.stop.hide()
        self.away = QPushButton('Put away · %s' % KEYS_WORDS, head);self.away.setObjectName('DropTerminalAway')
        self.away.setFocusPolicy(Qt.NoFocus);self.away.setCursor(Qt.PointingHandCursor)
        self.away.setToolTip('The Terminal goes back up; what you were in gets the keys again. What runs keeps running.')
        self.away.clicked.connect(self.leave)
        for w in (self.title, self.place):row.addWidget(w)
        row.addStretch(1)
        for w in (self.running, self.stop, self.dos, self.away):row.addWidget(w)
        box.addWidget(head)
        self.output = QTextBrowser(self);self.output.setObjectName('DropTerminalOutput');self.output.setOpenLinks(False)
        self.output.anchorClicked.connect(self.follow);self.output.setAccessibleName('Terminal output')
        self.output.setLineWrapMode(QTextEdit.NoWrap);self.output.setFont(cq.mono_font(14));self.output.document().setDefaultFont(cq.mono_font(14))
        self.output.setProperty('arcReadingPreview', True);self.output.setFocusPolicy(Qt.ClickFocus)
        self.output.document().setDefaultStyleSheet('a {color:%s; text-decoration: underline;}' % cq.AMBER_TEXT)
        scroll = self.output.verticalScrollBar();scroll.actionTriggered.connect(self.moved);scroll.rangeChanged.connect(self.keep_end)
        box.addWidget(self.output, 1)
        line = QWidget(self);line.setObjectName('DropTerminalLineRow');lay = QHBoxLayout(line);lay.setContentsMargins(10, 4, 10, 6);lay.setSpacing(8)
        self.sign = QLabel('', line);self.sign.setObjectName('DropTerminalSign');self.sign.setFont(cq.mono_font(15))
        self.prompt = Prompt(self);self.prompt.returnPressed.connect(self.enter)
        lay.addWidget(self.sign);lay.addWidget(self.prompt, 1);box.addWidget(line)
        self.anim = QPropertyAnimation(self, b'pos', self);self.anim.setEasingCurve(QEasingCurve.OutCubic);self.anim.finished.connect(self.slid)
        for key in IN_WINDOW_KEYS + ('Meta+`',):
            QShortcut(QKeySequence(key), self, activated=self.leave)
        self.restyle();self.read_words()

    # -- look
    def restyle(self):
        from . import bar_qt
        c = bar_qt.ink()
        ground, text = cq.TERMINAL_GROUND, cq.AMBER_TEXT
        self.setStyleSheet(
            'QWidget#DropTerminal {background:%(ground)s;} '
            'QWidget#DropTerminalHead {background:%(head)s;} '
            'QLabel#DropTerminalTitle {color:%(ink)s; font-weight:600;} '
            'QLabel#DropTerminalPlace, QLabel#DropTerminalDos, QLabel#DropTerminalRunning {color:%(quiet)s;} '
            'QPushButton#DropTerminalAway, QPushButton#DropTerminalStop {color:%(ink)s; background:transparent; border:1px solid %(stroke)s;'
            ' border-radius:4px; padding:2px 10px;} '
            'QPushButton#DropTerminalAway:hover, QPushButton#DropTerminalStop:hover {background:%(hover)s;} '
            'QTextBrowser#DropTerminalOutput {background:%(ground)s; color:%(text)s; border:0; padding:6px 12px;} '
            'QWidget#DropTerminalLineRow {background:%(ground)s;} '
            'QLabel#DropTerminalSign {color:%(text)s;} '
            'QLineEdit#DropTerminalLine {background:%(ground)s; color:%(text)s; border:0; border-bottom:1px solid %(rule)s; padding:3px 2px;}'
            % dict(ground=ground, text=text, head=c['sidebar'], ink=c['text'], quiet=c['secondary'], stroke=c['stroke'],
                   hover=c['hover_side'], rule=cq.LINE))

    def paintEvent(self, event):
        from . import bar_qt
        c = bar_qt.ink();p = QPainter(self)
        p.fillRect(self.rect(), QColor(cq.TERMINAL_GROUND))
        p.fillRect(0, self.height() - 2, self.width(), 2, QColor(c['stroke']))      # its lower edge: a rule, never a glow
        p.end()

    def read_words(self):
        """The header's words: the folder, the DOS words' setting, and what runs."""
        try:
            from . import windows_hand
            mode = windows_hand.dos_words()
        except Exception:  # noqa: BLE001
            mode = 'on'
        self.dos.setText({'on': 'DOS words: on', 'show': 'DOS words: shown only', 'off': 'DOS words: off'}.get(mode, 'DOS words: ' + str(mode)))
        self.dos.setToolTip('Tools ▸ DOS words: on (dir, copy… run as their Debian command, shown first), show me only, or off')
        try:self.place.setText(self.short(self.working_dir()))
        except Exception:  # noqa: BLE001 - the folder is read again at the next command
            pass
        self.sign.setText(self.sign_text() if self.cwd is not None or self.place.text() else '$')
        busy = self.process is not None
        self.running.setText(('running: %s' % (getattr(self, 'shell_text', '') or '')[:60]) if busy else '')
        self.stop.setVisible(busy)

    # -- the shell (1.0's, borrowed above)
    def shell_done(self, code, status):
        cq.Console.shell_done(self, code, status);self.read_words()

    def enter(self):
        text = self.prompt.text().strip()
        if not text:return None
        self.prompt.clear();self.remember(text)
        return self.run(text, drop=False)

    def run(self, text, drop=True):
        """Run one line as the owner typed it (the bar's line hands its Terminal rows here). Drops the Terminal first."""
        text = str(text or '').strip()
        if text.startswith('$'):text = text[1:].strip()
        if drop and not self.opened:self.drop()
        if not text:return None
        if text not in self.history[-1:]:self.remember(text)
        self.run_shell(text);self.read_words()
        return text

    def remember(self, text):
        if not self.history or self.history[-1] != text:self.history.append(text)
        del self.history[:-HISTORY_MOST];self.at = None

    def walk(self, step):
        if not self.history:return
        self.at = (len(self.history) if self.at is None else self.at) + step
        self.at = max(0, min(len(self.history), self.at))
        self.prompt.setText(self.history[self.at] if self.at < len(self.history) else '')

    def complete(self):
        """Tab: the last word completed from the names in its folder when one name fits (two or more: they are listed)."""
        text = self.prompt.text();head, _, word = text.rpartition(' ')
        folder, _, stem = word.rpartition('/')
        base = os.path.expanduser(folder) if folder else str(self.working_dir())
        if folder and not os.path.isabs(base):base = os.path.join(str(self.working_dir()), base)
        try:names = sorted(n for n in os.listdir(base) if n.startswith(stem) and (stem.startswith('.') or not n.startswith('.')))
        except OSError:
            return []
        if len(names) == 1:
            name = names[0] + ('/' if os.path.isdir(os.path.join(base, names[0])) else '')
            self.prompt.setText(((head + ' ') if head else '') + ((folder + '/') if folder else '') + name)
        elif len(names) > 1:
            self.say(cq.escape('  '.join(names[:60])))
        return names

    def clear_screen(self):
        self.output.clear();self.blocks = 0

    def set_size(self, level):
        """DOS words' exit (and the console's own size words): 0 puts the Terminal away."""
        if not level:self.leave()

    # -- down and up
    def screen_rect(self):
        screen = None
        try:screen = self.host.screen()
        except (RuntimeError, AttributeError):pass
        return (screen or QGuiApplication.primaryScreen()).geometry()

    def rects(self):
        g = self.screen_rect();o, c = band(g.x(), g.y(), g.width(), g.height())
        return QRect(*o), QRect(*c)

    def drop(self):
        """Down from the top edge, the keys in its line; the window that had the keys is remembered to give them back."""
        if self.opened and self.isVisible():
            self.raise_();self.activateWindow();self.prompt.setFocus();return self.geometry()
        own = {int(self.winId())} if self.isVisible() else set()
        before = active_window()
        try:host_id = int(self.host.winId())
        except (RuntimeError, AttributeError):host_id = 0
        self.before = before if before and before not in own else 0
        self.graphite_before = bool(before and before == host_id) or (not before and self._graphite_active())
        o, c = self.rects();self.opened = True;self.anim.stop();self.setFixedSize(o.size())
        if not self.welcomed:
            self.welcomed = True;self.say('<span style="opacity:0.85;">%s</span>' % '<br>'.join(cq.escape(line) for line in WELCOME))
        self.read_words()
        if not self.marked:
            try:
                from .kas_panel_qt import mark_everywhere
                self.marked = mark_everywhere(self.winId())
            except Exception:  # noqa: BLE001 - on one desktop, then
                self.marked = False
        if reduce_motion(self.host):
            self.move(o.topLeft());self.show();self.raise_()
        else:
            self.move(c.topLeft());self.show();self.raise_()
            self.anim.setDuration(SLIDE_MS);self.anim.setStartValue(c.topLeft());self.anim.setEndValue(o.topLeft());self.anim.start()
        self.activateWindow();self.prompt.setFocus()
        QTimer.singleShot(0, self.prompt.setFocus)
        return o

    def leave(self):
        """Back up; the keys go back to the app (or Graphite) that had them. What runs keeps running."""
        if not self.opened:return False
        o, c = self.rects();self.opened = False;self.anim.stop()
        if reduce_motion(self.host) or not self.isVisible():
            self.hide();self.slid();return True
        self.anim.setDuration(SLIDE_MS);self.anim.setStartValue(self.pos());self.anim.setEndValue(c.topLeft());self.anim.start()
        return True

    def slid(self):
        if self.opened:return
        self.hide()
        if self.before:
            self.gave = dict(window=self.before, **(give_back(self.before) or {}))
            try:
                if self.before == int(self.host.winId()):self.host.activateWindow()
            except (RuntimeError, AttributeError):pass
        elif self.graphite_before:
            try:self.host.activateWindow();self.gave = dict(window='graphite', asked=True)
            except RuntimeError:pass
        else:
            self.gave = dict(window=0, asked=False)

    def toggle(self):
        """The key: down when it is up, up when it is down."""
        if self.opened:
            self.leave();return {'ok': True, 'words': 'The Terminal is put away.'}
        self.drop();return {'ok': True, 'words': 'The Terminal is down: type a command.'}

    def _graphite_active(self):
        try:return bool(self.host.isActiveWindow())
        except RuntimeError:return False

    def place_now(self):
        """The screen changed: the open Terminal follows the top edge."""
        if self.opened and self.anim.state() != QPropertyAnimation.Running:
            o, _ = self.rects();self.setFixedSize(o.size());self.move(o.topLeft())

    def status(self):
        return dict(open=self.opened, visible=self.isVisible(), geometry=self.geometry().getRect(), before=self.before,
                    gave=self.gave, running=self.process is not None, cwd=str(self.cwd or ''), history=len(self.history))


# ---- in the window ----------------------------------------------------------------------------------------------------------------
def terminal(host, make=True):
    """host.drop_terminal, made once (on first use: nothing is drawn until it is wanted)."""
    term = getattr(host, 'drop_terminal', None)
    if term is None and make:
        term = host.drop_terminal = DropTerminal(host)
        app = QApplication.instance()
        if app is not None:app.aboutToQuit.connect(lambda term=term: term.stop_shell())
        try:
            screen = host.screen() or QGuiApplication.primaryScreen()
            screen.geometryChanged.connect(lambda *_: QTimer.singleShot(0, term.place_now))
        except (RuntimeError, AttributeError):
            pass
    return term


def toggle(host):
    """graphite-do terminal (Win+` and Ctrl+Alt+T from any app), and Ctrl+Alt+T in Graphite: down, or back up."""
    try:return terminal(host).toggle()
    except Exception as exc:  # noqa: BLE001 - the key answers in words
        return {'ok': False, 'words': 'The Terminal could not drop: %s' % (str(exc)[:160] or type(exc).__name__)}


def run(host, text):
    """A line for the Terminal (the bar's line's Terminal and DOS rows): the Terminal drops and runs it."""
    return terminal(host).run(text)


def install(host):
    """shell2, once the window stands: the in-window keys (Ctrl+Alt+T always; Ctrl+Alt+` once the foot has folded, see
    foot_fold_qt). The window itself is made on first use."""
    if getattr(host, '_drop_terminal_keys', None) is not None:return host._drop_terminal_keys
    keys = [QShortcut(QKeySequence('Ctrl+Alt+T'), host, activated=lambda: toggle(host))]
    host._drop_terminal_keys = keys
    host.drop_terminal = getattr(host, 'drop_terminal', None)
    return keys
