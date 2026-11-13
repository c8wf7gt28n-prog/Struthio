"""The pointer, in the desk's green.

The owner (13 November 2026): "I'd probably like the mouse pointer to be the systems green. We kinda need more green
glowing." Green is the desk's colour for what is live, and the pointer is the most live thing on it.

The pointer itself is the one the owner asked for earlier (HATCH DESK D1b, workbench/graphite_brand.py): "the two facets of
the Graphite mark ... Aim it at 11 o'clock, 30 degrees left of vertical, with the click at the tip." Its shape, its aim and
its hotspot are taken from there unchanged (graphite_brand.pointer_shape); only its ink is new. It was graphite with a
paper edge, made for the paper desk. Here it is the system green (boss_theme.READY) with a dark edge, so it reads over a
light page as well as over the dark desk, and a soft green glow. The hand over something that can be clicked, the text bar
and the closed hand of a drag are drawn in the same ink. The Clean desk keeps the green and drops the glow, as it drops
every other ornament.

The shapes are drawn, not loaded: no picture file, any size, the same on every machine. One filter on the application
gives every window the green pointer and turns the standard arrow, hand and text bar of any widget into their green
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
PAD = 4                        # room around the box for the glow, on every side (the hotspot moves with it)
SHAPES = (Qt.ArrowCursor, Qt.PointingHandCursor, Qt.IBeamCursor, Qt.ClosedHandCursor, Qt.OpenHandCursor)
MARK = 'greenPointer'          # on a widget that holds one of these pointers: which shape it stands for (a number)
_installed = None


def _number(shape):
    """A pointer shape as the number a widget property can keep (the shapes are an enumeration, not numbers)."""
    return int(getattr(shape, 'value', shape))


def _arrow():
    """The pointer: the mark's two facets, exactly as graphite_brand places them (the tip is the click, on a whole pixel)."""
    from .graphite_brand import pointer_shape
    shape = pointer_shape(1.0)
    path = QPainterPath();path.setFillRule(Qt.WindingFill)
    for wedge in shape['polygons']:
        path.moveTo(QPointF(*wedge[0]))
        for x, y in wedge[1:]:path.lineTo(QPointF(x, y))
        path.closeSubpath()
    return path, shape['hotspot']


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
    path, hot = _shape(shape);side = BOX + 2 * PAD
    pixmap = QPixmap(round(side * ratio), round(side * ratio));pixmap.setDevicePixelRatio(ratio);pixmap.fill(Qt.transparent)
    p = QPainter(pixmap);p.setRenderHint(QPainter.Antialiasing);p.translate(PAD, PAD)
    green = QColor(t.READY)
    if glow:
        for width, alpha in ((9.0, 0.07), (6.2, 0.12), (3.8, 0.2)):          # widest and faintest first: a halo, not a border
            halo = QColor(green);halo.setAlphaF(alpha)
            p.setPen(QPen(halo, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin));p.setBrush(Qt.NoBrush);p.drawPath(path)
    p.setPen(QPen(QColor(t.TERMINAL_GROUND), 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin));p.setBrush(green);p.drawPath(path)
    p.setPen(Qt.NoPen);p.drawPath(path)
    if shape == Qt.ArrowCursor:
        # The point's first device pixel, solid (as graphite_brand draws it): a sharp point covers only a sliver of the pixel
        # it starts in, which would draw it pale; the hotspot's pixel is the tip, so the click is visibly on it.
        p.setRenderHint(QPainter.Antialiasing, False);p.fillRect(QRectF(hot[0], hot[1], 1.0 / ratio, 1.0 / ratio), green)
    p.end()
    return pixmap, hot[0] + PAD, hot[1] + PAD


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
                if shape in self.cursors:
                    widget.setProperty(MARK, _number(shape));widget.setCursor(self.cursors[shape])
                elif shape == Qt.BitmapCursor and widget.property(MARK) is not None:      # one of ours, to be drawn again (the desk art changed)
                    widget.setCursor(self.cursors.get(Qt.CursorShape(int(widget.property(MARK))), self.cursors[Qt.ArrowCursor]))
                elif shape == Qt.BitmapCursor and widget.property('graphitePointer'):       # the mark's pointer in its graphite ink: the same facets, in green
                    widget.setProperty(MARK, _number(Qt.ArrowCursor));widget.setCursor(self.cursors[Qt.ArrowCursor])
            elif widget.isWindow():
                widget.setProperty(MARK, _number(Qt.ArrowCursor));widget.setCursor(self.cursors[Qt.ArrowCursor])
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
            try:
                if widget.property(MARK) is not None:self.give(widget)
            except RuntimeError:    # a widget on its way out
                pass


def arrow(window):
    """The green pointer for a window that asks for the Graphite pointer by name (graphite_brand.use_pointer): the cursor it
    was given, or None when the application has no green pointer (then the caller keeps its own)."""
    if _installed is None:return None
    try:
        window.setProperty(MARK, _number(Qt.ArrowCursor));window.setCursor(_installed.cursors[Qt.ArrowCursor])
    except RuntimeError:
        return None
    return _installed.cursors[Qt.ArrowCursor]


def install(app):
    """Give the application the green pointer. Safe to call more than once."""
    global _installed
    if _installed is None or _installed.app is not app:
        _installed = Pointer(app)
        app.installEventFilter(_installed)
        for widget in app.allWidgets():
            try:
                if widget.isVisible():_installed.give(widget)     # what is already on screen; the rest get theirs when shown
            except Exception:  # noqa: BLE001 - the pointer's colour never stops the application from being made
                pass
    return _installed


def restyle(glow):
    if _installed is not None:_installed.restyle(glow)
