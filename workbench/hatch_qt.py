"""The cat at the lower left of the desk and the programs list it opens (HATCH DESK D2; Hatch stays the internal name).

The owner's brief of 2026-11-06: "The cat opens a flat, predictable list of available programs and capabilities, like the
Programs folder in a Start menu. Give each entry one plain name and one small graphite icon. ... Put creation, recent work, and
system controls in their appropriate areas." The list (programs_qt.ProgramsList) holds the installed programs and capabilities
that sat in the Hatch groups (explore.VIEWS through the ledger.explore read) and Explore the workshop; New Idea and New Project
are under Work (menus2) and, with D4, on the Work tree's right-click; Graphite services, Return to Debian or Exit Graphite, Log
out, Restart and Shut down are in the System menu (system_menu_qt, session_power). The older Hatch rule that the menu names no
session or power command and its disabled "not in this edition" row are superseded by the brief; this module still issues
none (session_power does, for the System menu, through its one function).

Opening a capability is navigation through the existing view factories; execution keeps its own checks, grants and receipts.
Opening the list dispatches nothing but the `ledger.explore` read. The button keeps the Graphite services' lifecycle
(LedgerLifecycle, `hatch.lifecycle`, which the System menu's services row uses and the window shuts down on close).
"""
from PySide6.QtCore import QEvent, QSize, Qt, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QToolButton
from .service_lifecycle_qt import LedgerLifecycle
from .session_power import LEAVE, session_exit  # noqa: F401 (the leave words, for older callers)

CHOICES = 'Programs and capabilities, A to Z · Explore the workshop'
SERVICES_MENU = 'Graphite services'  # the services' place is the System menu now; the word is kept for callers
ORDER = ('programs A to Z', '—', 'Explore the workshop')  # the list's order, for readers and checks (programs_qt.order())


def elide(text, limit=70):return text if len(text) <= limit else text[:limit - 1].rstrip() + '…'


from .explore_qt import LauncherKeys, F1_NOTE


class HatchButton(LauncherKeys, QToolButton):
    """The cat in the lower band (graphite_brand.Cat; HATCH DESK D2: pale paper on the band, graphite eyes and paws, yellow
    irises when awake to you, a pink nose and inner ears), HATCH_ICON px high at 14 pt, following the interface size up to 1.4
    (typebar_qt.cat_tile). One click or keyboard activation (Space, Return, Enter) opens the programs list at once, from any pose,
    sleep included; tooltip and accessible name Open programs. Its poses follow the pointer, the list and a stretch of
    inactivity (Reduce motion switches them directly); a short eraser-pink mark under it shows keyboard focus. It sits whole on
    its ground in its tile, the tile centred in the band's height, placed by its drawing at rest (typebar_qt.TypeBar.place_cat,
    cat_x). Keyboard behaviour: LauncherKeys (a keyboard opening starts at the first row), and in the list Up, Down, Home, End,
    Escape, F1 and type-to-select (programs_qt.DeskMenu)."""
    NAME = 'Open programs'

    def __init__(self, host):
        super().__init__();self.host = host
        from . import explore
        from .graphite_brand import Cat
        from .programs_qt import EXPLORE, EXPLORE_TIP, ProgramsList, PLAIN
        self.setObjectName('Hatch');self.setProperty('paperIcon', True)
        self.setAccessibleName(self.NAME);self.setToolTip(self.NAME);self.setAccessibleDescription(CHOICES + ' · ' + F1_NOTE)
        self.setToolButtonStyle(Qt.ToolButtonIconOnly);self._icon_px = None
        self.setMinimumHeight(34);self.setCursor(Qt.PointingHandCursor);self.setFocusPolicy(Qt.StrongFocus)
        self.setStyleSheet('QToolButton#Hatch {background:transparent;border:0;padding:2px 3px;}')  # the cat paints itself
        self.cat = Cat(self, lambda:bool((getattr(host, 'reading_profile', None) or {}).get('reduce_motion', False)))
        self.face('normal');self.fit()
        self.lifecycle = LedgerLifecycle(host)
        # Every entry is created once, one per adapter, its identity stable; each opening refills its words from one read.
        self.snapshot = None;self.entries = {}
        for row in explore.VIEWS:
            key = row[0];a = QAction(PLAIN.get(key, row[1]).replace('&', '&&'), self);a.setProperty('key', key);a.setProperty('caption', '')
            a.triggered.connect(lambda checked=False, key=key:self.choose(key));self.entries[key] = a
        self.explore_action = QAction(EXPLORE, self);self.explore_action.setToolTip(EXPLORE_TIP);self.explore_action.triggered.connect(self.explore)
        self.programs = ProgramsList(host, self, self.entries, self.explore_action)
        self.programs.shown.connect(lambda shown:self.face('pressed' if shown else 'normal'))
        self.clicked.connect(lambda checked=False:self.open_list(self.keyboard_flag()))  # Space (and an accessible press)
        self.lifecycle.changed.connect(self.services_changed)

    # older callers: New Idea and New Project live under Work now (menus2: host.a_new_idea, host.a_new_project)
    @property
    def idea_action(self):return self._work_action('a_new_idea', 'New Idea', self.new_idea)

    @property
    def project_action(self):return self._work_action('a_new_project', 'New Project', self.new_project)

    def _work_action(self, name, word, callback):
        action = getattr(self.host, name, None)
        if action is None:
            own = '_' + name
            if getattr(self, own, None) is None:
                a = QAction(word, self);a.triggered.connect(lambda checked=False:callback());setattr(self, own, a)
            action = getattr(self, own)
        return action

    def menu(self):
        """The programs list (it is no QMenu: programs_qt.ProgramsList); kept under this name for older callers."""
        return self.programs

    def fit(self):
        """The cat's height follows the interface size (44 px at 14 pt, cap 1.4); the width keeps the drawing's proportion."""
        from .shell2 import scale_of
        from .typebar_qt import cat_tile
        size = cat_tile(scale_of(self.host))
        if size == self._icon_px:return
        self._icon_px = size;self.setIconSize(QSize(*size));self.updateGeometry()

    def event(self, event):
        if event.type() == QEvent.StyleChange:QTimer.singleShot(0, self.fit)  # the interface size changed: the tile follows it now
        return super().event(event)

    def refresh(self):
        self.lifecycle.refresh()

    def keyboard_flag(self):
        """True once after LauncherKeys saw Space, Return or Enter (the opening that puts the first row under focus)."""
        flag = self._keyboard_open;self._keyboard_open = False;return flag

    def showMenu(self):
        """LauncherKeys' Return and Enter: open the list from the keyboard."""
        self.open_list(self.keyboard_flag())

    def mousePressEvent(self, event):
        """One click opens the list at once, on the press as a menu does, from any pose (sleep included)."""
        if event.button() == Qt.LeftButton:
            self._keyboard_open = False;event.accept()
            if not self.programs.isVisible():self.open_list(False)
            return
        super().mousePressEvent(event)

    def open_list(self, keyboard=False):
        """One ledger.explore read, then the list opens upward from the lower left (programs_qt.place), the first row under
        focus when the keyboard opened it."""
        self.cat.wake();self.prepare()
        return self.programs.open_menu(keyboard=bool(keyboard))

    def prepare(self):
        """One ledger.explore read per opening; nothing moves while the list is open. True when the read answered."""
        from .engineering_kernel import operator
        from .explore_qt import selected_record, brain_state, capability_tip, view_open, capability_text
        from .programs_qt import caption_for
        kernel = self.host.ledger_bridge.kernel;ident = selected_record(self.host);args = {'kind':'INSTRUMENT'}
        if ident:args['context'] = ident
        response = kernel.dispatch('ledger.explore', args, operator());ok = bool(response.get('ok'))
        if not ok:
            message = str((response.get('error') or {}).get('message') or 'Capability view unavailable')
            self.programs.show_unavailable(message);return False
        value = response['result'];self.snapshot = value;context = value.get('context');brain = brain_state(kernel)
        self.programs.show_programs()
        for entry in value['instruments']:
            a = self.entries.get(entry['key'])
            if a is None:continue
            opened = view_open(self.host, entry);caption = caption_for(entry, opened)
            a.setProperty('caption', caption);a.setProperty('words', capability_text(entry, opened, brain).replace('&&', '&'));a.setProperty('title', entry['title'])
            a.setEnabled(entry['view_available']);a.setToolTip(capability_tip(entry, brain, context))
            row = self.programs.rows_by_key.get(entry['key'])
            if row is not None:row.follow()
        return True

    def services_changed(self, state):
        """The service summary rides in the cat's accessible description (the services' rows are the System menu's)."""
        self.setAccessibleDescription(str(state.get('summary', '')) + ' · ' + CHOICES + ' · ' + F1_NOTE)

    def face(self, state):
        """'pressed' while the list is open (the open pose wins over hover), 'normal' when it closes (rest or hover by the
        pointer's position); the menuOpen property says which for the checks."""
        open_ = state == 'pressed'
        if self.cat.poses.open != open_:self.cat.menu(open_)
        if bool(self.property('menuOpen')) != open_:self.setProperty('menuOpen', open_)
        self.update()

    cat_x = None  # the tile's left edge in the button, set by the lower band (typebar_qt.TypeBar.place_cat); else centred

    def tile(self):
        """The cat's tile in the button: its own size, at cat_x, centred in the button's height (the band's: D1-fix, the
        cat sits whole inside the band with the band's padding above and below)."""
        from PySide6.QtCore import QRectF
        w, h = self.iconSize().width(), self.iconSize().height()
        return QRectF((self.width() - w) / 2 if self.cat_x is None else self.cat_x, (self.height() - h) / 2, w, h)

    def paintEvent(self, event):
        """The cat in its tile; nothing else is drawn."""
        from PySide6.QtGui import QPainter
        p = QPainter(self);self.cat.paint(p, self.tile(), self.hasFocus());p.end()

    def enterEvent(self, event):
        self.cat.enter();super().enterEvent(event)

    def leaveEvent(self, event):
        self.cat.leave();super().leaveEvent(event)

    def focusInEvent(self, event):
        self.cat.wake();self.update();super().focusInEvent(event)

    def focusOutEvent(self, event):
        self.update();super().focusOutEvent(event)

    def new_idea(self):
        from .shell2 import capture_dialog
        capture_dialog(self.host)

    def new_project(self):
        from .project_desk_qt import show
        tab = show(self.host);tab.project_title.setFocus();tab.project_title.selectAll()

    def explore(self):
        from .explore_qt import show, selected_record
        show(self.host, selected_record(self.host))

    def entry(self, key):
        """The adapter's row from the last read (read now when there was none)."""
        if self.snapshot is None:self.prepare()
        return next((r for r in (self.snapshot or {}).get('instruments', ()) if r['key'] == key), None)

    def choose(self, key):
        entry = self.entry(key)
        if entry is None:self.host.statusBar().showMessage('This workspace is unavailable. Refresh Explore for details.', 6000);return
        self.launch(entry, (self.snapshot or {}).get('context'))

    def launch(self, entry, context=None):
        """Navigation only: the existing factories open the view; no operation other than the read is dispatched."""
        from .explore_qt import open_instrument
        try:open_instrument(self.host, entry, context)
        except (ValueError, OSError, ImportError) as exc:self.host.statusBar().showMessage(str(exc), 6000)

    def leave(self):
        """Return to Debian or Exit Graphite (the System menu's row): the existing leave, through session_power."""
        from .session_power import leave
        return leave(self.host)
