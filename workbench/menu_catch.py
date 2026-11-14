"""The catch: a menu's opening, like a picture locking onto a tape.

0.8.2, from the owner's "Graphite after hours": "You right-click bench readings.csv. The menu opens immediately. A narrow
violet tracking band passes behind the second or third row. For an instant the right edge has a faint cyan duplicate. Then
the frame locks. When you move over Then, the child menu picks up its own sweep … entered through the edge nearest the
parent." And: "Someone who opens Then and hits Enter in one motion should get the exact same result as someone who waits."

So the catch is only light, laid over a popup for CATCH_MS as it opens, on a child widget the mouse goes through: the menu is
there and answers keys and clicks from its first instant, its rows and its highlight are drawn as always, and when the catch
ends the overlay is gone. It covers the menus across the head (QMenu) and the desk's own menus (the right-click, Apps),
which are drawn differently but open the same way. The brightest part is the frame. With motion reduced, or on the Clean
glow, nothing is laid over anything.

flash(widget) is the same light on a single edge, for a moment: the writing line when a line lands in it.
"""
import time

from PySide6.QtCore import QEvent, QObject, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QApplication, QMenu, QWidget

CATCH_MS = 150          # the owner's starting point: "I'd start at about 150 milliseconds"
FLASH_MS = 260          # the writing line's edge, when a line lands in it


def ink(colour, alpha):
    c = QColor(colour);c.setAlphaF(max(0.0, min(1.0, alpha)));return c


def calm(widget):
    """Whether this window asked for less motion, or the glow is off (Clean): then nothing is laid over a menu."""
    from . import boss_theme as t
    try:
        if t.glow() <= 0:return True
    except Exception:  # noqa: BLE001 - a theme that cannot be read is a still one
        return True
    host = widget.window() if widget is not None else None
    for candidate in (host, getattr(host, 'host', None), QApplication.activeWindow()):
        state = getattr(getattr(candidate, 'session', None), 'state', None)
        if isinstance(state, dict):
            from .reading_profile import DEFAULT
            return bool((state.get('reading_profile') or {}).get('reduce_motion', DEFAULT['reduce_motion']))
    return False


class Catch(QWidget):
    """The light over one opening popup: the tracking band, the cyan ghost on its far edge, the frame lit and settling."""
    def __init__(self, popup, side='down', ms=CATCH_MS, edge_only=False):
        super().__init__(popup)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True);self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setFocusPolicy(Qt.NoFocus);self.setObjectName('MenuCatch')
        self.side = side;self.ms = ms;self.edge_only = edge_only;self.began = time.monotonic()
        self.setGeometry(popup.rect());self.raise_();self.show()
        self.timer = QTimer(self);self.timer.setInterval(16);self.timer.timeout.connect(self.tick);self.timer.start()

    def progress(self):
        return min(1.0, (time.monotonic() - self.began) * 1000.0 / self.ms)

    def tick(self):
        if self.progress() >= 1.0:
            self.timer.stop();self.hide();self.deleteLater();return
        parent = self.parentWidget()
        if parent is not None and self.geometry() != parent.rect():self.setGeometry(parent.rect())
        self.update()

    def paintEvent(self, event):
        from . import boss_theme as t
        f = self.progress();w = self.width();h = self.height();p = QPainter(self)
        try:
            p.setRenderHint(QPainter.Antialiasing)
            # the frame, brightest at the opening and settling into the menu's own hairline
            p.setBrush(Qt.NoBrush);p.setPen(QPen(ink(getattr(t, 'VIOLET_PALE', t.VIOLET), 0.95 * (1.0 - f) ** 1.2), 2.0));p.drawRect(QRectF(1.0, 1.0, w - 2.0, h - 2.0))
            if self.edge_only:return
            # the cyan ghost on the far edge, for an instant
            if f < 0.6:
                ghost = (1.0 - f / 0.6) * 0.7
                x = w - 4.5 if self.side != 'left' else 3.0
                p.fillRect(QRectF(x, 2, 1.5, h - 4), ink(t.READY, ghost));p.fillRect(QRectF(x - 3.0 if self.side != 'left' else x + 3.0, 2, 1.0, h - 4), ink(t.READY, ghost * 0.35))
            # the tracking band: across the second and third rows for a top-level menu, in from the parent's side for a child
            if self.side == 'down':
                band = max(10.0, min(26.0, h * 0.09));y = h * 0.10 + (h * 0.34) * f
                g = QLinearGradient(0, y - band / 2, 0, y + band / 2)
            else:
                band = max(12.0, min(40.0, w * 0.18));x = (w * f * 0.9) if self.side == 'left' else (w - w * f * 0.9)
                g = QLinearGradient(x - band / 2, 0, x + band / 2, 0)
            strength = 0.42 * (1.0 - f) ** 0.6
            line = ink(getattr(t, 'ROYAL_INK', t.TEXT), 0.55 * (1.0 - f))      # the bright line at the band's heart, as a tape's tracking shows it
            g.setColorAt(0.0, ink(t.VIOLET, 0.0));g.setColorAt(0.5, ink(t.VIOLET, strength));g.setColorAt(1.0, ink(t.VIOLET, 0.0))
            if self.side == 'down':p.fillRect(QRectF(0, y - band / 2, w, band), g);p.fillRect(QRectF(2, y - 0.6, w - 4, 1.2), line)
            else:p.fillRect(QRectF(x - band / 2, 0, band, h), g);p.fillRect(QRectF(x - 0.6, 2, 1.2, h - 4), line)
        finally:
            p.end()


def side_of(popup):
    """'down' for a menu opened on its own; 'left' or 'right' for a child, the side its parent menu is on."""
    parent = getattr(popup, 'parent_menu', None)
    if parent is None and isinstance(popup, QMenu) and isinstance(popup.parentWidget(), QMenu) and popup.parentWidget().isVisible():
        parent = popup.parentWidget()
    if parent is None or not parent.isVisible():return 'down'
    return 'left' if parent.geometry().center().x() < popup.geometry().center().x() else 'right'


def catch(popup):
    """Lay the catch over a popup that has just opened (nothing, with motion reduced or the glow off)."""
    if popup is None or calm(popup):return None
    old = popup.findChild(Catch)
    if old is not None:old.timer.stop();old.deleteLater()
    return Catch(popup, side_of(popup))


def flash(widget, ms=FLASH_MS):
    """The frame of one widget lit for a moment, settling to nothing: where a line landed."""
    if widget is None or calm(widget):return None
    return Catch(widget, 'down', ms, edge_only=True)


class Watcher(QObject):
    """One filter on the application: a menu of this window that opens gets its catch."""
    def __init__(self, host):
        super().__init__(host);self.host = host

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Show and isinstance(obj, QWidget) and obj.isWindow():
            from .programs_qt import DeskMenu
            if isinstance(obj, (QMenu, DeskMenu)):
                QTimer.singleShot(0, lambda obj=obj:catch(obj) if obj.isVisible() else None)
        return False


def install(host):
    if getattr(host, 'menu_catch', None) is not None:return host.menu_catch
    watcher = Watcher(host);host.menu_catch = watcher
    app = QApplication.instance()
    if app is not None:app.installEventFilter(watcher)
    return watcher
