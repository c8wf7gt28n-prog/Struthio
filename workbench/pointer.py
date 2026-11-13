"""The pointer, in the desk's green.

The owner (13 November 2026): "I'd probably like the mouse pointer to be the systems green. We kinda need more green
glowing." Green is the desk's colour for what is live, and the pointer is the most live thing on it. So the arrow, the
hand over something that can be clicked, the text bar and the grabbing hand are drawn here in the system green
(boss_theme.READY), with a dark edge so they read over a light page as well as over the dark desk, and a soft green glow
around them. The Clean desk keeps the green and drops the glow, as it drops every other ornament.

The shapes are drawn, not loaded: no picture file, any size, the same on every machine. One filter on the application
gives every window the green arrow and turns the standard arrow, hand and text bar of any widget into their green
counterparts as they are set. Cursors this module does not draw (the resize arrows, the wait cursor) stay the system's.

    install(app)        once, when the application is made
    restyle(glow)       when the desk art changes: Illustrated and ASCII glow, Clean does not
    drawn(shape, ...)   one pointer as a pixmap, for whoever wants to look at it
"""
from PySide6.QtCore import QEvent, QObject, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QCursor, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QApplication, QWidget

from . import boss_theme as t

BOX = 32                       # the drawing box of one pointer, in logical pixels
SHAPES = (Qt.ArrowCursor, Qt.PointingHandCursor, Qt.IBeamCursor, Qt.ClosedHandCursor, Qt.OpenHandCursor)
_installed = None


def _arrow():
    path = QPainterPath(QPointF(5, 3))
    for x, y in ((5, 22.5), (9.8, 18.2), (13.2, 25.6), (16.4, 24.2), (13.1, 17.0), (19.6, 17.0)):
        path.lineTo(x, y)
    path.closeSubpath()
    return path, (5, 3)


def _hand(pointing=True):
    """A hand: the palm, three folded fingers and the thumb; with the first finger out when it points."""
    path = QPainterPath();path.setFillRule(Qt.WindingFill)
    path.addRoundedRect(QRectF(9, 13, 14, 12.5), 3.6, 3.6)                    # the palm
    path.addRoundedRect(QRectF(15.2, 9.6, 3.9, 8), 1.9, 1.9)                  # folded fingers
    path.addRoundedRect(QRectF(19.1, 10.8, 3.9, 8), 1.9, 1.9)
    path.addRoundedRect(QRectF(5.6, 14.6, 5.4, 4.2), 2.1, 2.1)                # the thumb
    if pointing:path.addRoundedRect(QRectF(11.2, 3, 4.1, 14), 2.0, 2.0)       # the finger that points
    else:path.addRoundedRect(QRectF(11.2, 9.0, 4.1, 8), 2.0, 2.0)
    return path.simplified(), ((13, 3) if pointing else (16, 16))


def _bar():
    path = QPainterPath();path.setFillRule(Qt.WindingFill)
    path.addRect(QRectF(15, 6, 2, 20))
    path.addRect(QRectF(11.5, 5, 9, 2));path.addRect(QRectF(11.5, 25, 9, 2))
    return path.simplified(), (16, 16)


def _shape(shape):
    if shape == Qt.PointingHandCursor:return _hand(True)
    if shape in (Qt.ClosedHandCursor, Qt.OpenHandCursor):return _hand(False)
    if shape == Qt.IBeamCursor:return _bar()
    return _arrow()


def drawn(shape, glow=True, ratio=1.0):
    """One pointer: (pixmap, hot x, hot y). Green, a dark edge, and (unless glow is off) a soft halo of the same green."""
    path, hot = _shape(shape)
    pixmap = QPixmap(round(BOX * ratio), round(BOX * ratio));pixmap.setDevicePixelRatio(ratio);pixmap.fill(Qt.transparent)
    p = QPainter(pixmap);p.setRenderHint(QPainter.Antialiasing)
    green = QColor(t.READY)
    if glow:
        for width, alpha in ((9.0, 0.07), (6.2, 0.12), (3.8, 0.2)):          # widest and faintest first: a halo, not a border
            halo = QColor(green);halo.setAlphaF(alpha)
            p.setPen(QPen(halo, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin));p.setBrush(Qt.NoBrush);p.drawPath(path)
    p.setPen(QPen(QColor(t.TERMINAL_GROUND), 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin));p.setBrush(green);p.drawPath(path)
    p.setPen(Qt.NoPen);p.drawPath(path)
    p.end()
    return pixmap, hot[0], hot[1]


class Pointer(QObject):
    def __init__(self, app, glow=True):
        super().__init__(app)
        self.app = app;self.glow = bool(glow);self.cursors = {};self.busy = False
        self.build()

    def build(self):
        try:
            ratio = float(self.app.primaryScreen().devicePixelRatio()) if self.app.primaryScreen() is not None else 1.0
        except Exception:  # noqa: BLE001 - no screen yet: draw at 1
            ratio = 1.0
        self.cursors = {}
        for shape in SHAPES:
            pixmap, x, y = drawn(shape, self.glow, ratio)
            self.cursors[shape] = QCursor(pixmap, x, y)

    def give(self, widget):
        """This widget's pointer in green: a window with no pointer of its own gets the arrow (its children inherit it); a
        widget that set one of the standard shapes gets that shape's green counterpart. Anything else is left alone."""
        if self.busy or not isinstance(widget, QWidget):return
        self.busy = True
        try:
            if widget.testAttribute(Qt.WA_SetCursor):
                shape = widget.cursor().shape()
                if shape in self.cursors:widget.setCursor(self.cursors[shape])
                elif shape == Qt.BitmapCursor and widget.property('graphitePointer') is not None:
                    widget.setCursor(self.cursors.get(Qt.CursorShape(int(widget.property('graphitePointer'))), self.cursors[Qt.ArrowCursor]))
                    return
                else:return
                widget.setProperty('graphitePointer', int(shape))
            elif widget.isWindow():
                widget.setCursor(self.cursors[Qt.ArrowCursor]);widget.setProperty('graphitePointer', int(Qt.ArrowCursor))
        except RuntimeError:        # the widget is going away
            pass
        finally:
            self.busy = False

    def eventFilter(self, watched, event):
        """Never in the way: whatever happens here, the event goes on as if this filter were not there. A widget is only
        touched once it is shown (Polish, Show), or when one that is already on screen changes its pointer. A widget still
        being made sets its pointer inside its own constructor; touching it then breaks its making, so it is left until it
        is shown."""
        try:
            kind = event.type()
            if kind not in (QEvent.Polish, QEvent.Show, QEvent.CursorChange) or not isinstance(watched, QWidget):return False
            if kind == QEvent.CursorChange:
                if not watched.isVisible():return False
                if watched.testAttribute(Qt.WA_SetCursor) and watched.cursor().shape() == Qt.BitmapCursor:
                    return False        # already one of ours (or a picture of someone's own): nothing to do
            elif kind == QEvent.Show and watched.isWindow() and hasattr(watched, 'session'):
                # the desk's own window says which art it wears: the Clean desk has no glow
                self.restyle(watched.session.state.get('desk_art', 'illustrated') != 'clean')
            self.give(watched)
        except Exception:  # noqa: BLE001 - a pointer's colour is never worth an event
            pass
        return False

    def restyle(self, glow):
        if bool(glow) == self.glow:return
        self.glow = bool(glow);self.build()
        for widget in self.app.allWidgets():
            if widget.property('graphitePointer') is not None:self.give(widget)


def install(app):
    """Give the application the green pointer. Safe to call more than once."""
    global _installed
    if _installed is None or _installed.app is not app:
        _installed = Pointer(app)
        app.installEventFilter(_installed)
        for widget in app.allWidgets():_installed.give(widget)
    return _installed


def restyle(glow):
    if _installed is not None:_installed.restyle(glow)
