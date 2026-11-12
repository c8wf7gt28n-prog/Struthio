"""Optional local animation over the Graphite desk."""
from PySide6.QtCore import QElapsedTimer, QEvent, QObject, QTimer, Qt
from PySide6.QtGui import QActionGroup, QCursor, QPainter
from PySide6.QtWidgets import QApplication, QMenu, QWidget

from .locations import program
from .session import IDLE_DISPLAY_MINUTES


WAKE_EVENTS = (
    QEvent.KeyPress, QEvent.MouseMove, QEvent.MouseButtonPress, QEvent.MouseButtonDblClick,
    QEvent.Wheel, QEvent.TouchBegin, QEvent.TabletPress, QEvent.TabletMove, QEvent.InputMethod,
)


class IdleScreen(QWidget):
    def __init__(self, host):
        super().__init__(host)
        from .idle_display_art import IdleDisplayArt

        self.art = IdleDisplayArt(program(host.root) / 'branding' / 'boss')
        self.setAccessibleName('Fast-forward screensaver')
        self.setAccessibleDescription('Simulated operations. Move the pointer or press a key to return to work.')
        self.setAttribute(Qt.WA_OpaquePaintEvent)
        self.setAttribute(Qt.WA_AcceptTouchEvents)
        self.setMouseTracking(True)
        self.setCursor(Qt.BlankCursor)
        self.clock = QElapsedTimer()
        self.frame_timer = QTimer(self)
        self.frame_timer.setInterval(83)
        self.frame_timer.timeout.connect(self.update)

    def begin(self, reduced_motion):
        self.reduced_motion = reduced_motion
        self.clock.start()
        self.setGeometry(self.parentWidget().rect())
        self.show()
        self.raise_()
        if not reduced_motion:
            self.frame_timer.start()

    def hideEvent(self, event):
        self.frame_timer.stop()
        super().hideEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        try:
            seconds = 0.0 if self.reduced_motion else self.clock.elapsed() / 1000
            self.art.paint(painter, self.rect(), seconds, self.reduced_motion)
        finally:
            painter.end()


class IdleDisplay(QObject):
    def __init__(self, host):
        super().__init__(host)
        self.host = host
        self.app = QApplication.instance()
        self.screen = None
        self.listening = False
        self.wake_keys = set()
        self.wake_button = None
        self.idle_timer = QTimer(self)
        self.idle_timer.setSingleShot(True)
        self.idle_timer.timeout.connect(self.preview)
        self.app.applicationStateChanged.connect(self._application_changed)
        self._listen()

    @property
    def minutes(self):
        return self.host.session.state.get('idle_display_minutes', 0)

    @property
    def showing(self):
        return self.screen is not None and self.screen.isVisible()

    def _listen(self):
        needed = bool(self.minutes or self.showing or self.wake_keys or self.wake_button is not None)
        if needed != self.listening:
            if needed:
                self.app.installEventFilter(self)
            else:
                self.app.removeEventFilter(self)
            self.listening = needed

    def _desk_available(self):
        return (self.app.applicationState() == Qt.ApplicationActive and self.host.isVisible()
                and not self.host.isMinimized() and self.host.isActiveWindow())

    def _arm(self):
        if self.minutes and not self.showing and self._desk_available():
            self.idle_timer.start(self.minutes * 60_000)
        else:
            self.idle_timer.stop()

    def set_minutes(self, minutes):
        self.host.session.state['idle_display_minutes'] = minutes
        self.host.session.save()
        self._listen()
        self._arm()

    def preview(self):
        if self.showing or not self._desk_available():
            return
        if self.app.activeModalWidget() is not None or self.app.activePopupWidget() is not None:
            self._arm()
            return
        if self.screen is None:
            self.screen = IdleScreen(self.host)
        self.idle_timer.stop()
        self.pointer_at_start = QCursor.pos()
        profile = getattr(self.host, 'reading_profile', self.host.session.state.get('reading_profile', {}))
        self.screen.begin(bool(profile.get('reduce_motion', False)))
        self._listen()

    def dismiss(self):
        if self.screen is not None:
            self.screen.hide()
        self._listen()
        self._arm()

    def _application_changed(self, state):
        if state == Qt.ApplicationActive:
            self._arm()
        else:
            self.wake_keys.clear()
            self.wake_button = None
            self.dismiss()

    def eventFilter(self, watched, event):
        kind = event.type()
        if watched is self.host:
            if kind == QEvent.Resize and self.showing:
                self.screen.setGeometry(self.host.rect())
                self.screen.raise_()
            if kind in (QEvent.Show, QEvent.WindowActivate, QEvent.WindowStateChange):
                self._arm()
            if kind in (QEvent.Hide, QEvent.WindowDeactivate) or self.host.isMinimized():
                self.wake_keys.clear()
                self.wake_button = None
                self.dismiss()

        # Consume the entire wake chord, including modifiers and autorepeats.
        if self.wake_keys and kind in (QEvent.ShortcutOverride, QEvent.Shortcut, QEvent.KeyPress, QEvent.KeyRelease):
            if kind == QEvent.KeyPress:
                self.wake_keys.add(event.key())
            elif kind == QEvent.KeyRelease and not event.isAutoRepeat():
                self.wake_keys.discard(event.key())
                self._listen()
            event.accept()
            return True
        if self.wake_button is not None and kind == QEvent.MouseButtonRelease and event.button() == self.wake_button:
            self.wake_button = None
            self._listen()
            return True

        if kind in (QEvent.ShortcutOverride, QEvent.Shortcut) and self.showing:
            event.accept()
            return True
        if kind not in WAKE_EVENTS:
            return False
        if not self.showing:
            self._arm()
            return False
        if kind == QEvent.MouseMove and event.globalPosition().toPoint() == self.pointer_at_start:
            return True
        if kind == QEvent.KeyPress:
            self.wake_keys.add(event.key())
        elif kind in (QEvent.MouseButtonPress, QEvent.MouseButtonDblClick):
            self.wake_button = event.button()
        self.dismiss()
        event.accept()
        return True

    def menu(self, parent):
        menu = QMenu('Fast-forward screensaver', parent)
        preview = menu.addAction('Preview now')
        preview.triggered.connect(lambda: QTimer.singleShot(0, self.preview))
        menu.addSeparator()
        group = QActionGroup(menu)
        actions = {}
        for minutes in IDLE_DISPLAY_MINUTES:
            action = menu.addAction(f'After {minutes} minutes' if minutes else 'Automatic start off')
            action.setCheckable(True)
            group.addAction(action)
            action.triggered.connect(lambda checked=False, value=minutes: self.set_minutes(value))
            actions[minutes] = action
        menu.aboutToShow.connect(lambda: actions[self.minutes].setChecked(True))
        actions[self.minutes].setChecked(True)
        return menu
