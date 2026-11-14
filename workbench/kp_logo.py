"""Kasandra's Apps: the owner's neon kp logo in the head's upper right (0.8.3).

The owner, 14 November 2026: "New logo for our upper right progman.exe menu ;) ... Omg I love it", and "Retire any other kp
icon". It is the only kp mark: the Apps button, about 44 px tall and 74 wide at 14 pt; its name for readers is Apps and its
tip says what Apps holds. The window's own icon is Graphite's sharpened point in both appearances (graphite_brand).

The file is the clean drawing (branding/kasandra/kp_neon.png, cut by tools/cut_kp_neon.py from the owner's file, whose neon
fringe was stored at alpha 1 of 255 and cannot be shown as it was). It is shown only when its bytes are the recorded ones
(kasandra_art.MARKS). The neon is drawn round it here, as light added to the band under it (Screen), never as paint over it:
  wide     the drawing in its own colours, blurred wide and soft
  close    the same blurred a little, close round each part
  ghosts   a cyan copy a little to the left and a magenta one a little to the right, as a neon sign doubles on glass
each in proportion to the Glow dial (boss_theme.glow(): Soft 1, Bright 1.9, Neon 3), and none at all on the Clean desk or
at a glow of 0. When Apps opens, the logo catches with its menu (menu_catch.CATCH_MS): its ghosts spread and its light
surges, then it settles on the frame it had. With Reduce motion, or the glow off, it is still.

Under the pointer the button answers as the head's words do (the pointer's green under it); holding the keyboard or held
down, a burnt-yellow edge under it and no fill: the logo's cyan light is never laid over yellow, which would read green.
"""
import time

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QToolButton

NAME = 'kp_neon.png'
HEIGHT, WIDTH = 44, 74            # the logo in the head at 14 pt (1401 x 838 drawn to 44 px tall is 73.6 wide)
GHOSTS = (('#83eaff', -1.0), ('#ff4fd8', 1.0))      # cyan to the left, magenta to the right
GHOST_AWAY = 1.5                  # px at 14 pt, settled; up to SPREAD times that as the logo catches
SPREAD = 2.6
WIDE, CLOSE = 0.2, 0.28           # the light's strength per step of the Glow dial (Neon 3: 0.6 and 0.84)
GHOST = 0.16                      # (Neon 3: 0.48)
BLUR_WIDE, BLUR_CLOSE = 8, 3      # how far each light reaches, px at 14 pt
MARGIN = 12                       # room round the drawing for its light, px at 14 pt

_images = {}                      # path -> the clean drawing, decoded once
_layers = {}                      # (image key, width, height, dpr) -> the drawing and its two lights and its mask, at that size


def logo(root):
    """The clean drawing as a premultiplied image when its bytes are the recorded ones (kasandra_art.mark), else null."""
    from . import kasandra_art
    path = kasandra_art.mark(kasandra_art.folder(root), NAME)
    if path is None:return QImage()
    key = str(path)
    if key not in _images:
        image = QImage(key)
        _images[key] = image.convertToFormat(QImage.Format_ARGB32_Premultiplied) if not image.isNull() else QImage()
    return _images[key]


def size(scale=1.0):
    """The logo's size in the head at this interface scale."""
    return QSize(round(WIDTH * scale), round(HEIGHT * scale))


def _blur(image, reach):
    """A soft copy of `image` (same size): drawn down by `reach` and up again, each way smoothly (an area average, then a
    bilinear spread), which is a blur of about that many pixels."""
    if reach <= 1:return image
    small = image.scaled(max(1, round(image.width() / reach)), max(1, round(image.height() / reach)), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    return small.scaled(image.width(), image.height(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)


def layers(image, width, height, dpr=1.0, scale=1.0):
    """(drawing, wide light, close light, mask, margin): the drawing at width x height logical pixels on a canvas with room
    round it for its light, at the device pixel ratio; each kept for the next paint."""
    key = (image.cacheKey(), int(width), int(height), round(dpr * 100), round(scale * 100))
    if key in _layers:return _layers[key]
    margin = round(MARGIN * scale * dpr);w, h = max(1, round(width * dpr)), max(1, round(height * dpr))
    drawing = QImage(w + 2 * margin, h + 2 * margin, QImage.Format_ARGB32_Premultiplied);drawing.fill(0)
    p = QPainter(drawing);p.setRenderHint(QPainter.SmoothPixmapTransform)
    p.drawImage(QRectF(margin, margin, w, h), image.scaled(w, h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation));p.end()
    mask = QImage(drawing.size(), QImage.Format_ARGB32_Premultiplied);mask.fill(QColor('#ffffff'))
    p = QPainter(mask);p.setCompositionMode(QPainter.CompositionMode_DestinationIn);p.drawImage(0, 0, drawing);p.end()
    made = (drawing, _blur(drawing, BLUR_WIDE * scale * dpr), _blur(drawing, BLUR_CLOSE * scale * dpr), mask, margin / dpr)
    for image_ in made[:4]:image_.setDevicePixelRatio(dpr)
    _layers[key] = made
    while len(_layers) > 12:_layers.pop(next(iter(_layers)))
    return made


_tints = {}                       # (mask key, colour) -> a ghost


def tinted(mask, colour):
    """The drawing's shape in one colour (a ghost), kept for the next paint."""
    key = (mask.cacheKey(), colour)
    if key not in _tints:
        out = QImage(mask.size(), QImage.Format_ARGB32_Premultiplied);out.fill(QColor(colour))
        p = QPainter(out);p.setCompositionMode(QPainter.CompositionMode_DestinationIn);p.drawImage(0, 0, mask);p.end()
        out.setDevicePixelRatio(mask.devicePixelRatio());_tints[key] = out
        while len(_tints) > 24:_tints.pop(next(iter(_tints)))
    return _tints[key]


def strengths(level, surge=0.0):
    """(wide, close, ghost) light at Glow `level` (0: none), `surge` 0 to 1 while it catches."""
    if level <= 0:return 0.0, 0.0, 0.0
    boost = 1.0 + 0.6 * max(0.0, min(1.0, surge))
    return min(0.9, WIDE * level * boost), min(1.0, CLOSE * level * boost), min(0.75, GHOST * level * boost)


def paint(p, rect, image, level, scale=1.0, surge=0.0):
    """The logo in `rect` (logical, its own size), its neon round it at Glow `level` (0 or the Clean desk: none), caught by
    `surge` (0 settled, 1 at the catch's start). Returns the strengths used, for checks."""
    dpr = p.device().devicePixelRatioF() if p.device() is not None else 1.0
    drawing, wide, close, mask, margin = layers(image, rect.width(), rect.height(), dpr, scale)
    at = QPointF(rect.left() - margin, rect.top() - margin)
    used = strengths(level, surge)
    if level > 0:
        p.save();p.setCompositionMode(QPainter.CompositionMode_Screen)      # light added to the band, never paint over it
        for layer, alpha in ((wide, used[0]), (close, used[1])):
            p.setOpacity(alpha);p.drawImage(at, layer)
        away = GHOST_AWAY * scale * (1.0 + (SPREAD - 1.0) * max(0.0, min(1.0, surge)))
        p.setOpacity(used[2])
        for colour, side in GHOSTS:p.drawImage(at + QPointF(side * away, 0), tinted(mask, colour))
        p.restore()
    p.drawImage(at, drawing)
    return used


class AppsButton(QToolButton):
    """The head's Apps button. With the logo (apps_mark gives it one in Kasandra) it paints the logo and its neon itself;
    without it, it is a tool button with its words, as in Graphite."""

    def __init__(self, parent=None):
        super().__init__(parent);self.logo = None;self.scale = 1.0;self.caught_at = None
        self._catch = QTimer(self);self._catch.setInterval(16);self._catch.timeout.connect(self._tick)

    def host(self):
        return self.window()

    def level(self):
        """The Glow dial's strength here: none on the Clean desk."""
        from . import boss_theme as t
        try:
            from .boss_qt import glows
            return t.glow() if glows(self.window()) else 0.0
        except Exception:  # noqa: BLE001 - a button with no desk behind it: no ornament
            return 0.0

    def catch(self):
        """Apps opened: the logo catches with its menu (none with Reduce motion or with the glow off)."""
        from .menu_catch import calm
        if self.logo is None or calm(self) or self.level() <= 0:return False
        self.caught_at = time.monotonic();self._catch.start();self.update();return True

    def surge(self):
        from .menu_catch import CATCH_MS
        if self.caught_at is None:return 0.0
        f = (time.monotonic() - self.caught_at) * 1000.0 / CATCH_MS
        return 0.0 if f >= 1.0 else (1.0 - f) ** 1.5

    def _tick(self):
        if self.surge() <= 0.0:
            self._catch.stop();self.caught_at = None
        self.update()

    def logo_rect(self):
        s = size(self.scale);return QRectF((self.width() - s.width()) / 2.0, (self.height() - s.height()) / 2.0, s.width(), s.height())

    def paintEvent(self, event):
        if self.logo is None:return super().paintEvent(event)
        from . import boss_theme as t
        p = QPainter(self);p.setRenderHint(QPainter.SmoothPixmapTransform)
        try:
            edge = max(2, round(2 * self.scale))
            if self.underMouse() and not self.isDown():
                p.fillRect(self.rect(), QColor(t.TEAL_SOFT));p.fillRect(0, self.height() - edge, self.width(), edge, QColor(t.READY))
            elif self.hasFocus() or self.isDown():      # the keyboard's place: her edge alone, so no light falls on yellow
                p.fillRect(0, self.height() - edge, self.width(), edge, QColor(t.AMBER_EDGE))
            paint(p, self.logo_rect(), self.logo, self.level(), self.scale, self.surge())
        finally:
            p.end()
