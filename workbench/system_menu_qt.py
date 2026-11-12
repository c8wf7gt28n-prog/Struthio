"""The System menu, from the erased Graphite symbol at the far right of the head (HATCH DESK D2; the owner's brief of 2026-11-06:
"Open the system menu from that symbol. Put Game first. ... Put Stop all jobs directly beneath it, scoped to work Graphite
manages. Then show the ordered process list, with a niceness slider on every active or queued row. Carry forward queue reorder
and distinguish it from niceness. Put Log out, Return to Debian, Restart, and Shut down in a separated group, as applicable,
with session and machine scope clear.").

Top to bottom (it opens downward from the upper right, the point-mirror image of the cat's programs list: programs_qt.DeskMenu
and place give both one design and Symmetry rule 6):

  Game                 STRUTHIO in its offline desk mode, paused at tick zero (workbench.struthio_qt.show)
  Stop all jobs        the existing Master Stop (its confirm dialog, its stop thread, Ctrl+Shift+F12), scoped in words to the
                       work Graphite manages
  the process list     desktop_header_qt.NicePopup as a section: the active jobs in the order they started and the queue in its
                       order, a niceness slider on every row (CPU nice through jobs.nice, the Agenda tier through agenda.nice); the
                       queue's order is its own control, a place number at the left of each queued row with drag, Earlier and
                       Later (agenda.reorder), so order and niceness read differently
  Graphite services    On · Off · Restart: Graphite's own services (service_lifecycle_qt.LedgerLifecycle, the cycles that were
                       Hatch's On / Off / Reboot); the row's word opens Service details
  ───────────────────  a separated group, each row with its scope and availability (logind is asked when the menu opens; an
                       unavailable row reads 'unavailable' in quiet ink, stays in the keyboard's order and says why):
  Log out              this login session (session_power: loginctl terminate-session)
  Return to Debian     this Graphite session, in the dedicated session (ARC_LEDGER_XSESSION=1); elsewhere Exit Graphite
  Restart              this computer (systemctl reboot)
  Shut down            this computer (systemctl poweroff)

Every action goes through what already exists (the Master Stop action, the operations' own dispatch inside NicePopup and
LedgerLifecycle, session_power's leave flow); this menu adds no operation, setting, scheduler, store or process.
"""
from __future__ import annotations
from PySide6.QtCore import QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QFontMetricsF, QPainter
from PySide6.QtWidgets import QAbstractButton, QWidget
from .programs_qt import Caption, DeskMenu, MenuRow, Rule, caption_font, row_need, word_font

GAME = 'Game'
GAME_CAPTION = 'STRUTHIO'                       # the game's name, in print (a name you read)
GAME_TIP = 'STRUTHIO in its offline desk mode, paused at tick zero'
STOP = 'Stop all jobs'
STOPPING = 'Stopping…'
STOP_SCOPE = 'work Graphite manages'            # the scope, in print: read before acting
STOP_TIP = ('Stop all jobs Graphite manages: confirm, then every Graphite job, build, console, host tool and the phone link is '
            'stopped (Ctrl+Shift+F12). Programs Graphite does not manage keep running. Source files and unsaved editor buffers are kept.')
SERVICES = 'Graphite services'
CHOICES = (('On', 'On'), ('Off', 'Off'), ('Reboot', 'Restart'))  # (LedgerLifecycle's key, the word shown)
CHOICE_TIPS = {'On':'Enable new authorized work; no jobs replayed and no model or phone started.',
               'Off':'Cancel queued jobs, finish running work, then close owned services. Keep the desktop open.',
               'Reboot':'Restart Graphite services here: cancel queued jobs, let running work finish, then start them again. A prior running model is requested again after the drain. The computer is not restarted.'}
BACKGROUND = 'Background CPU'                 # the process list's priority box (its whole words are the tooltip)
FOOT = 'each asks first and keeps your work'   # the menu's small caption at its foot (the programs list's is at its top)
ORDER = ('Game', 'Stop all jobs', 'processes', 'Graphite services', '—', 'Log out', 'leave', 'Restart', 'Shut down')


def words_need(m):
    """The widest row this menu can show, from its words alone (programs_qt.menu_width takes the larger of both menus)."""
    from . import session_power as power
    unavailable = ' · unavailable'
    rows = [row_need(m, GAME, GAME_CAPTION), row_need(m, STOP, STOP_SCOPE), row_need(m, FOOT, '', True),
            row_need(m, SERVICES) + choices_need(m), section_need(m)]
    for action in power.ACTIONS:rows.append(row_need(m, power.WORDS[action], power.SCOPES[action] + unavailable))
    for label in ('Return to Debian', 'Exit Graphite'):rows.append(row_need(m, label, power.SCOPES['leave']))
    return max(rows)


def choices_need(m):
    import math
    fm = QFontMetricsF(word_font(m));return math.ceil(sum(fm.horizontalAdvance(word) + 3 for _, word in CHOICES) + len(CHOICES) * m.caption_gap)


def section_need(m):
    """The process list's widest control at its own print size (the window's controls, 16 px at 14 pt): the Background CPU box
    and the Open Agenda and Work trail words, set from the menu's word column (its padding and icon column)."""
    import math
    from PySide6.QtGui import QFont
    from .shell2 import SANS
    font = QFont(SANS);font.setPixelSize(max(10, round(16 * m.scale)));fm = QFontMetricsF(font)
    box = fm.horizontalAdvance(BACKGROUND) + m.icon + 10 * m.scale
    words = fm.horizontalAdvance('Open Agenda') + fm.horizontalAdvance('Work trail') + 2 * 14 * m.scale + 8
    return math.ceil(2 * m.pad + m.icon_col + max(box, words))


class Choice(QAbstractButton):
    """One of Graphite services' three words in its row: print, an eraser-pink mark under it for the pointer and keyboard focus
    (an action), quiet when it cannot be chosen now."""
    def __init__(self, row, key, word, callback):
        super().__init__(row);self.row = row;self.key = key;self.setText(word);self.setFocusPolicy(Qt.StrongFocus);self.setCursor(Qt.PointingHandCursor)
        # D2-fix: read without its row (F1's note, a screen reader, the keyboard's order) the choice names its scope, so the
        # services' Restart is never mistaken for the computer's Restart two rows below (the row itself shows the scope as its word)
        self.word = SERVICES + ': ' + word
        self.setAttribute(Qt.WA_Hover, True);self.setAccessibleName(self.word);self.clicked.connect(callback);self.refont()

    def refont(self):
        self.setProperty('deskMenuRow', True)  # the menu's sheet sets its font: the menus' word size

    def sizeHint(self):
        import math
        m = self.row.menu.m;own = max(QFontMetricsF(word_font(m)).horizontalAdvance(self.text()), self.fontMetrics().horizontalAdvance(self.text()))
        return QSize(math.ceil(own) + 2, m.row)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and not event.isAutoRepeat():self.click();return
        if event.key() in (Qt.Key_Left, Qt.Key_Right):
            siblings = self.row.choices;i = siblings.index(self) + (1 if event.key() == Qt.Key_Right else -1)
            if 0 <= i < len(siblings):siblings[i].setFocus(Qt.TabFocusReason)
            return
        super().keyPressEvent(event)

    def focusInEvent(self, event):
        self.row.menu.ensure_visible(self.row);self.update();super().focusInEvent(event)

    def focusOutEvent(self, event):self.update();super().focusOutEvent(event)

    def paintEvent(self, event):
        from .shell2 import ERASER_MARK, QUIET, TEXT
        from .desk_qt import MARK
        m = self.row.menu.m;p = QPainter(self);p.setRenderHint(QPainter.TextAntialiasing);p.setFont(self.font())
        p.setPen(QColor(TEXT if self.isEnabled() else QUIET));p.drawText(QRectF(0, 0, self.width(), self.height()), Qt.AlignCenter, self.text())
        if self.isEnabled() and (self.hasFocus() or (self.underMouse() and self.row.menu.pointer_moved)):
            p.fillRect(QRectF(0, self.height() - MARK - max(1, m.row // 8), self.width(), MARK), QColor(ERASER_MARK))
        p.end()


class ServicesRow(MenuRow):
    """Graphite services: its word opens Service details; On, Off and Restart sit at the row's right end."""
    def __init__(self, menu, callback, choose):
        super().__init__(menu, SERVICES, 'services', callback=callback)
        self.choices = [Choice(self, key, word, lambda checked=False, key=key:choose(key)) for key, word in CHOICES]

    def sizeHint(self):
        return QSize(row_need(self.m(), SERVICES) + choices_need(self.m()), self.m().row)

    def resizeEvent(self, event):
        super().resizeEvent(event);m = self.m();x = self.width() - m.pad
        for choice in reversed(self.choices):
            w = choice.sizeHint().width();x -= w;choice.setGeometry(x, 0, w, self.height());x -= m.caption_gap


class SystemMenu(DeskMenu):
    """The System menu (see the module's words). Built once per window by the symbol (desktop_header_qt.SystemButton); each
    opening refreshes the process list, the services' rules and the availability of Log out, Restart and Shut down (logind is
    asked then, not when the menu is built). Older
    callers keep their names: `kill` is the Stop all jobs row, `game` the Game row, and the work list's parts (running, queue,
    running_label, queued_label, empty, earlier, later, note, waiting, background) are the process section's."""
    embedded = False

    def __init__(self, host, anchor):
        super().__init__(host, anchor, 'upper-right', 'SystemMenuList')
        self.setAccessibleName('System menu');self.setAccessibleDescription('Game, Stop all jobs, the process list, Graphite services, and leaving: Log out, '
                                                                          + self.leave_words()['label'] + ', Restart, Shut down')
        from . import session_power as power
        from .desktop_header_qt import NicePopup
        self.power = power;self.states = {}
        self.game = MenuRow(self, GAME, 'game', GAME_CAPTION, callback=self.open_game);self.game.setObjectName('GameRow')
        self.game.setToolTip(GAME_TIP);self.game.setAccessibleName('Game: ' + GAME_TIP);self.box.addWidget(self.game)
        self.kill = MenuRow(self, STOP, 'stop', STOP_SCOPE, callback=self.stop_all);self.kill.setObjectName('KillSwitch');self.box.addWidget(self.kill)
        self.stop = self.kill
        self.box.addWidget(Rule(self))
        self.work = NicePopup(host, anchor, section=True, menu=self);self.work.setParent(self.page);self.box.addWidget(self.work)
        self.box.addWidget(Rule(self))
        self.services = ServicesRow(self, self.show_services, self.cycle);self.box.addWidget(self.services)
        self.service_actions = {choice.key:choice for choice in self.services.choices}
        self.box.addWidget(Rule(self, strong=True))
        leave = self.leave_words()
        self.session_rows = {}
        for key, word, icon in (('logout', power.WORDS['logout'], 'logout'), ('leave', leave['label'], 'leave'),
                                ('restart', power.WORDS['restart'], 'restart'), ('shutdown', power.WORDS['shutdown'], 'shutdown')):
            row = MenuRow(self, word, icon, power.SCOPES[key], callback=lambda key=key:self.session(key));row.setObjectName('Session_' + key)
            self.session_rows[key] = row;self.box.addWidget(row)
        self.session_rows['leave'].setToolTip(leave['tip'] + '\nScope: ' + power.SCOPES['leave'] + '.')
        self.exit_action = self.session_rows['leave']
        self.caption = Caption(self, FOOT);self.box.addWidget(self.caption);self.end_rows()
        controller = getattr(host, 'master_stop_controller', None)
        if controller is not None and hasattr(controller, 'faces'):controller.faces.append(self.kill_words)
        self.kill_words(controller)
        life = self.lifecycle()
        if life is not None:life.changed.connect(self.render_services);self.render_services(life.state)
        # D2-fix: logind is asked when the menu opens (fill), never when it is built: building it asks the system nothing

    # what older callers read from the work list
    def __getattr__(self, name):
        if name in ('running', 'running_label', 'queue', 'queued_label', 'empty', 'earlier', 'later', 'note', 'waiting', 'background',
                    'commit_nice', 'commit_order', 'move_selected', 'render_data', 'job_row', 'rows_height', 'order_selection', 'priority',
                    'open_agenda', 'open_trail', 'timer'):
            work = self.__dict__.get('work') if hasattr(self, '__dict__') else None
            if work is None:
                try:work = QWidget.__getattribute__(self, 'work')
                except AttributeError:work = None
            if work is not None:return getattr(work, name)
        raise AttributeError(name)

    def leave_words(self):
        from .session_power import session_exit
        return session_exit()

    def lifecycle(self):
        hatch = getattr(getattr(self.host, 'type_bar', None), 'hatch', None)
        return getattr(hatch, 'lifecycle', None)

    # the rows' actions
    def open_game(self):
        """STRUTHIO in desk mode (workbench.struthio_qt.show): the game the head's mark opened until HATCH DESK D1a."""
        from .struthio_qt import show
        show(self.host)

    def stop_all(self):
        """The existing Master Stop through its action (its confirm dialog, its stop thread, its shortcut)."""
        self.host.a_master_stop.trigger()
    stop_everything = stop_work = stop_all  # older names

    def kill_words(self, controller=None):
        """The row says what the Master Stop controller knows: Stopping… while its thread runs; the controller's detail (the
        advice, its reasons, the shortcut, the held state) is the tooltip. Nothing here is a second stop."""
        controller = controller if controller is not None else getattr(self.host, 'master_stop_controller', None)
        running = bool(controller is not None and getattr(controller, 'running', False))
        word = STOPPING if running else STOP
        if self.kill.word != word:self.kill.word = word;self.kill.setText(word);self.kill.update()
        detail = str(getattr(controller, 'detail', '') or '') if controller is not None else ''
        self.kill.setToolTip(STOP_TIP + ('\n\n' + detail if detail else ''));self.kill.describe()

    def show_services(self):
        action = getattr(self.host, 'a_host_service', None)
        if action is None:self.host.statusBar().showMessage('Service details are not installed in this desktop.', 6000);return
        action.trigger()

    def cycle(self, key):
        """On, Off or Restart of Graphite's own services: the existing cycle (LedgerLifecycle.request, its own confirmation)."""
        self.close_menu(restore=False)
        life = self.lifecycle()
        if life is not None:QTimer.singleShot(0, lambda:life.request(key))

    def session(self, key):
        if key == 'leave':self.power.leave(self.host)
        else:self.power.run_action(self.host, key)

    # each opening
    def render_services(self, state):
        """On, Off and Restart follow the service cycle's rules (Hatch's, unchanged): none while a cycle drains or stops; On only
        while admission is held; Off not again once the services are off."""
        phase = state.get('phase');busy = phase in ('DRAINING', 'STOPPING', 'UNAVAILABLE');off = phase == 'OFF';summary = state.get('summary', '')
        for key, choice in self.service_actions.items():
            enabled = not busy and (key != 'On' or not state.get('admission_enabled') or state.get('work_held'))
            if key == 'Off' and off:enabled = False
            choice.setEnabled(bool(enabled))
            choice.setToolTip(summary + '\n' + ('Graphite services are already off; choose On to enable new work.' if key == 'Off' and off else CHOICE_TIPS[key]))
            choice.update()
        plane = str(state.get('control_plane') or '')
        self.services.setToolTip(summary + '\n' + (plane + '\n' if plane else '') + 'Opens Service details. On, Off and Restart act on Graphite\'s own services, never on the computer.')
        self.services.set_caption('');self.services.describe()

    def availability(self):
        """Log out, Restart and Shut down from logind (session_power.availability: read, nothing started). An unavailable row
        reads 'unavailable' after its scope in quiet ink and stays in the keyboard's order (D2-fix): its whole reason is its
        tooltip, its accessible description and F1's note, and choosing it says why in a dialog (run_action refuses before
        anything is asked or issued)."""
        self.states = self.power.availability()
        for key in self.power.ACTIONS:
            row = self.session_rows[key];state = self.states[key]
            row.setEnabled(True);row.set_caption(self.power.SCOPES[key] + ('' if state['available'] else ' · unavailable'))
            row.setToolTip(self.power.describe(key, state));row.set_unavailable('' if state['available'] else state['reason']);row.describe()
        return self.states

    def refresh(self):
        """The process list read again (older callers refreshed the work list's popup by this name)."""
        self.work.refresh()

    def fill(self):
        self.kill_words();self.availability()
        life = self.lifecycle()
        if life is not None:life.refresh()
        self.work.refresh()

    def showEvent(self, event):
        super().showEvent(event);self.work.timer.start()

    def hideEvent(self, event):
        self.work.timer.stop();super().hideEvent(event)

    def words(self):
        """The menu's parts top to bottom (for readers and checks): row words, 'processes' for the process list, '—' for rules."""
        from .programs_qt import Caption as _Caption
        out = []
        for w in self.items():
            if isinstance(w, _Caption):continue
            out.append('—' if isinstance(w, Rule) else 'processes' if w is self.work else w.word)
        return out
