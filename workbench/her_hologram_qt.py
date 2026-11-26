"""Kas as a hologram (Graphite 1.0, P3).

The owner, 26 November 2026, with a tall full-figure picture of her (a glowing blue figure in a wide hat, on black): "Use
her as the on screen kas, like she is a hologram. Not the circle picture." Her column's portrait (her_column_qt.Portrait,
P1) stands as a hologram whenever her picture is taller than it is wide; a wide or square picture keeps P1's circle.

    the cut       her picture's dark ground becomes see-through: each pixel's alpha follows its brightness (the brightest
                  of its red, green and blue) on a soft ramp from KEY_LOW to KEY_HIGH, so the glow's edges stay soft and
                  she floats over the column. A picture that brings its own transparency (its corners clear) keeps it.
                  Done once a picture (keyed(), kept by the picture's key: the admitted bytes' SHA-256), never a frame.
    the slot      tall. In a tall column (1920 x 1200) she shows from her hat to below the hips (SHOW_TALL of her
                  height), in a short one (1366 x 768) from her hat to the waist (SHOW_COMPACT); her lowest part fades
                  into the column. The equalizer's bars stand behind and beside her (its hole narrower than she is, as in
                  the owner's picture). Her name, her model's ring and her state word stay under her, where P1 put them.
    her light     a soft glow round her, fine scan lines drifting down, a slow breath and a slow band of light passing
                  down through her (the shimmer); at a change of her state a brief static (the hologram's own noise, on
                  her only, and a tear). Each is a layer composed once a size; a frame is a few drawImage calls, at most
                  twelve a second, and none while she is not seen (hidden, the window minimised or not in front, a moment
                  over her) or when Reduce motion is on: then one still frame, no shimmer and no static.
    the looks     in Graphite and Kasandra she floats on the column; in Day she stands on a dark glass panel of her own
                  (the projector glass), so the light look stays light around her.
    a moment      for the moments that matter (P1's: a finding refuted, an assignment done, HALT) her full figure, larger,
                  stands in her stage's place with the moment in words under her, and a stronger static as she arrives
                  (still with Reduce motion). The 0.8.3 hologram in the left pane then stands aside: the owner's default,
                  "the full art for the moments that matter, in place of the lower-left hologram".

Her picture is the owner's kasandra/portrait.png once they admit it (her_portrait, P1); until then the shipped art, her
hologram's figure (branding/kasandra/hologram.webp), in this treatment in every look. The owner's picture never enters
the program: it is read from their workspace at run time, as P1 built.

No words of hers here (nothing to register with mind_words), no model, nothing written, no record read or changed. The
numbers here are light and sizes, never a checked sum.
"""
from __future__ import annotations

import math
import random
import time
from collections import deque

from PySide6.QtCore import QEvent, QObject, QPointF, QRect, QRectF, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QFont, QFontMetrics, QGuiApplication, QImage, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient

from . import boss_theme as bt

KEY_LOW, KEY_HIGH = 24, 150     # brightness at or under KEY_LOW is see-through, at or over KEY_HIGH solid; a soft ramp between
INK = 40                        # an alpha this strong or more is her ink (what her box is measured from)
MOST_TALL = 1400                # a taller picture is scaled down once before it is cut (a moment never shows her taller)
FRAME_MS = 83                   # twelve frames a second at most
SHIMMER_S = 6.5                 # a slow band of light passes down through her every this many seconds
BREATH_S = 4.6                  # her light breathes between 0.92 and 1 over this
STATIC_MS = 650                 # the brief static at a change of her state
ARRIVE_MS = 950                 # the stronger static as she arrives (a new picture, a moment)
SHOW_TALL = 0.78                # a tall column shows her from her hat to below the hips (a share of her ink's height)
SHOW_COMPACT = 0.56             # a short column: from her hat to the waist
FADE = 0.16                     # the lowest share of what is shown fades into the column
BANDS = 40                      # her width is measured in this many bands of her height (the shown part's width)
EQ_TOP = 0.34                   # in a tall slot the bars stand from this share of its height down (from her shoulders)
EQ_TOP_COMPACT = 0.20           # in a short one, from under her hat's crown
HOLE = 0.48                     # the bars' hole, as a share of her width: they stand behind her edges and beside her
SCAN_ALPHA = 62                 # one device row in three darkened this much: her scan lines
GLOW = '#62b8ff'                # her glow when her picture's own colour cannot be told (a white or grey picture)
GLASS = ('#0c1322', '#16233a', '#3a74b8')      # Day's projector glass: its top, its foot, its edge
KEEP = 2                        # pictures kept cut
_KEYED = {}                     # picture key -> Keyed
_SCAN = []


def _ramp():
    out = bytearray(256)
    for m in range(256):
        if m <= KEY_LOW:out[m] = 0
        elif m >= KEY_HIGH:out[m] = 255
        else:out[m] = round(255 * ((m - KEY_LOW) / (KEY_HIGH - KEY_LOW)) ** 0.85)
    return bytes(out)


RAMP = _ramp()
INKS = bytes(1 if a >= INK else 0 for a in range(256))


class Keyed:
    """Her figure cut free of its ground: the image (ARGB32 premultiplied), her ink's box in it, her width in BANDS bands of
    her height ((left, right) or None each), her own colour for the glow, and what the cut cost (milliseconds)."""
    __slots__ = ('image', 'ink', 'bands', 'tint', 'ms', 'own')


def keyed(image, key):
    """Her picture cut free of its dark ground, once a picture (kept by key, the last KEEP)."""
    if key in _KEYED:return _KEYED[key]
    started = time.perf_counter()
    k = _cut(image)
    k.ms = round((time.perf_counter() - started) * 1000, 1)
    _KEYED[key] = k
    while len(_KEYED) > KEEP:_KEYED.pop(next(iter(_KEYED)))
    return k


def forget():
    _KEYED.clear()


def _own_alpha(image):
    """Whether the picture brings its own transparency: an alpha channel and its four corners clear."""
    if not image.hasAlphaChannel():return False
    w, h = image.width(), image.height()
    return all(image.pixelColor(x, y).alpha() < 16 for x, y in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)))


def _cut(image):
    k = Keyed();k.ms = 0.0;k.own = False
    if image is None or image.isNull():
        k.image = QImage();k.ink = QRect();k.bands = ();k.tint = QColor(GLOW);return k
    k.own = own = _own_alpha(image)
    if image.height() > MOST_TALL:image = image.scaledToHeight(MOST_TALL, Qt.SmoothTransformation)
    src = image.convertToFormat(QImage.Format_RGBA8888_Premultiplied)      # bytes R, G, B, A on every machine
    w, h = src.width(), src.height()
    raw = bytes(src.constBits())[:w * h * 4]
    if own:
        alpha = raw[3::4]
    else:      # alpha from brightness: the brightest of R, G, B, through the ramp (C-speed: map, translate)
        alpha = bytes(map(max, raw[0::4], raw[1::4], raw[2::4])).translate(RAMP)
        mask = QImage(alpha, w, h, w, QImage.Format_Alpha8).copy()
        p = QPainter(src);p.setCompositionMode(QPainter.CompositionMode_DestinationIn);p.drawImage(0, 0, mask);p.end()
        raw = bytes(src.constBits())[:w * h * 4]
    # her own colour, weighted by how much of her each pixel is: the glow takes its hue
    total = sum(raw[3::4])
    if total:
        r, g, b = sum(raw[0::4]) / total, sum(raw[1::4]) / total, sum(raw[2::4]) / total
        mean = QColor.fromRgbF(min(1.0, r), min(1.0, g), min(1.0, b))
        hue, sat = mean.hsvHueF(), mean.hsvSaturationF()
        k.tint = QColor.fromHsvF(hue, min(1.0, 0.35 + sat), 1.0) if hue >= 0 and sat >= 0.12 else QColor(GLOW)
    else:
        k.tint = QColor(GLOW)
    # her ink: the rows and the reach of each, then her box and her width band by band
    marks = alpha.translate(INKS);rows = []
    for y in range(h):
        row = marks[y * w:(y + 1) * w];a = row.find(1)
        if a >= 0:rows.append((y, a, row.rfind(1)))
    if not rows:
        k.ink = QRect(0, 0, w, h);k.bands = ((0, w - 1),) * BANDS
    else:
        top, bottom = rows[0][0], rows[-1][0];left = min(r[1] for r in rows);right = max(r[2] for r in rows)
        k.ink = QRect(left, top, right - left + 1, bottom - top + 1);tall = bottom - top + 1;bands = [None] * BANDS
        for y, a, z in rows:
            i = min(BANDS - 1, (y - top) * BANDS // tall);was = bands[i]
            bands[i] = (a, z) if was is None else (min(was[0], a), max(was[1], z))
        k.bands = tuple(bands)
    k.image = src.convertToFormat(QImage.Format_ARGB32_Premultiplied)
    return k


def shown(k, share):
    """The part of her keyed picture shown for a share of her height, from her hat down: (QRect in the picture)."""
    ink = k.ink
    if ink.isEmpty():return QRect()
    n = max(1, min(BANDS, math.ceil(share * BANDS - 1e-9)));reach = [b for b in k.bands[:n] if b is not None]
    left = min(b[0] for b in reach) if reach else ink.left();right = max(b[1] for b in reach) if reach else ink.right()
    tall = max(1, round(ink.height() * min(1.0, share)))
    return QRect(left, ink.top(), right - left + 1, tall)


def fit(k, share, w, h, widest=1.0):
    """Her figure's box (QRect) for a share of her height in a room w x h: as tall as the room unless that makes her wider
    than `widest` of it; centred, standing on the room's foot."""
    part = shown(k, share)
    if part.isEmpty() or w < 8 or h < 8:return QRect()
    aspect = part.width() / part.height()
    fh = max(8, h - 2);fw = fh * aspect
    if fw > w * widest:fw = w * widest;fh = fw / aspect
    fw, fh = max(4, round(fw)), max(4, round(fh))
    return QRect((w - fw) // 2, h - fh, fw, fh)


def _scan_tile():
    if not _SCAN:
        tile = QImage(256, 3, QImage.Format_ARGB32_Premultiplied);tile.fill(Qt.transparent)
        ink = QColor('#020611');ink.setAlpha(SCAN_ALPHA)
        for x in range(256):tile.setPixelColor(x, 0, ink)
        _SCAN.append(tile)
    return _SCAN[0]


class Light:
    """Her layers at one size (device pixels): her figure faded at its foot, her glow, her figure with its scan lines in
    three phases, a bright twin for the shimmer, and (made when first needed) three of her with static."""

    def __init__(self, k, share, W, H, fade=FADE):
        self.size = (W, H);part = shown(k, share)
        figure = k.image.copy(part).scaled(W, H, Qt.IgnoreAspectRatio, Qt.SmoothTransformation).convertToFormat(QImage.Format_ARGB32_Premultiplied)
        if fade > 0:
            p = QPainter(figure);p.setCompositionMode(QPainter.CompositionMode_DestinationIn)
            top = int(H * (1.0 - fade));g = QLinearGradient(0, top, 0, H)
            g.setColorAt(0, QColor(0, 0, 0, 255));g.setColorAt(1, QColor(0, 0, 0, 0))
            p.fillRect(QRect(0, top, W, H - top), g);p.end()
        self.figure = figure
        m = self.margin = max(3, round(W * 0.08))
        canvas = QImage(W + 2 * m, H + 2 * m, QImage.Format_ARGB32_Premultiplied);canvas.fill(Qt.transparent)
        p = QPainter(canvas);p.drawImage(m, m, figure);p.end()
        small = canvas.scaled(max(1, (W + 2 * m) // 9), max(1, (H + 2 * m) // 9), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        glow = small.scaled(W + 2 * m, H + 2 * m, Qt.IgnoreAspectRatio, Qt.SmoothTransformation).convertToFormat(QImage.Format_ARGB32_Premultiplied)
        p = QPainter(glow);p.setCompositionMode(QPainter.CompositionMode_SourceIn);p.fillRect(glow.rect(), k.tint);p.end()
        self.glow = glow
        self.scans = []
        for phase in range(3):
            img = figure.copy();p = QPainter(img);p.setCompositionMode(QPainter.CompositionMode_SourceAtop)
            p.setBrushOrigin(0, phase);p.fillRect(QRect(0, 0, W, H), QBrush(_scan_tile()));p.end()
            self.scans.append(img)
        bright = figure.copy();p = QPainter(bright);p.setCompositionMode(QPainter.CompositionMode_SourceAtop)
        white = QColor(255, 255, 255, 150);p.fillRect(QRect(0, 0, W, H), white);p.end()
        self.bright = bright;self._statics = None

    def statics(self):
        if self._statics is None:
            from .hologram_qt import noise_tiles
            tiles = noise_tiles();W, H = self.size;out = []
            for i in range(3):
                img = self.scans[i].copy();p = QPainter(img);p.setCompositionMode(QPainter.CompositionMode_SourceAtop)
                p.setOpacity(0.8);p.setBrushOrigin(-(17 * i) % 64, -(29 * i) % 64)
                p.fillRect(QRect(0, 0, W, H), QBrush(tiles[(2 * i) % len(tiles)]));p.end()
                out.append(img)
            self._statics = out
        return self._statics


def glass(p, r, tint):
    """Day's projector glass: a dark panel of her own (soft shadow, deep gradient, a sheen, a thin edge, the projector's
    light at its foot)."""
    p.save();p.setRenderHint(QPainter.Antialiasing)
    shadow = QColor(bt.DAY_MARKS.get('SHADOW', '#1b2420') if hasattr(bt, 'DAY_MARKS') else '#1b2420');shadow.setAlpha(34)
    p.setPen(Qt.NoPen);p.setBrush(shadow);p.drawRoundedRect(r.translated(0, 2).adjusted(1, 1, -1, 0), 9, 9)
    path = QPainterPath();path.addRoundedRect(r, 8, 8)
    g = QLinearGradient(r.topLeft(), r.bottomLeft());g.setColorAt(0, QColor(GLASS[0]));g.setColorAt(1, QColor(GLASS[1]))
    p.fillPath(path, g)
    p.setClipPath(path)
    sheen = QLinearGradient(r.topLeft(), QPointF(r.left() + r.width() * 0.6, r.top() + r.height() * 0.45))
    sheen.setColorAt(0, QColor(255, 255, 255, 22));sheen.setColorAt(1, QColor(255, 255, 255, 0))
    p.fillRect(r, sheen)
    foot = QPointF(r.center().x(), r.bottom() - 1);reach = r.width() * 0.46
    light = QRadialGradient(foot, reach);c0 = QColor(tint);c0.setAlpha(80);c1 = QColor(tint);c1.setAlpha(0)
    light.setColorAt(0, c0);light.setColorAt(1, c1)
    p.save();p.translate(foot);p.scale(1.0, 0.32);p.translate(-foot);p.fillRect(QRectF(r.left(), r.bottom() - reach, r.width(), reach * 2), light);p.restore()
    edge = QColor(tint);edge.setAlpha(150);p.setPen(QPen(edge, 1.4))
    p.drawLine(QPointF(r.left() + r.width() * 0.2, r.bottom() - 1.5), QPointF(r.right() - r.width() * 0.2, r.bottom() - 1.5))
    p.setClipping(False)
    rim = QColor(GLASS[2]);rim.setAlpha(190);p.setPen(QPen(rim, 1));p.setBrush(Qt.NoBrush);p.drawPath(path)
    top = QColor(255, 255, 255, 30);p.setPen(QPen(top, 1));p.drawLine(QPointF(r.left() + 8, r.top() + 1.5), QPointF(r.right() - 8, r.top() + 1.5))
    p.restore()


def app_active():
    return QGuiApplication.applicationState() == Qt.ApplicationActive


class Hologram(QObject):
    """Her hologram on one widget: the picture she is drawn from, her layers at the size shown, the static she owes, and
    (for her stage) the clock of her frames."""

    def __init__(self, widget, host, clock=True):
        super().__init__(widget);self.widget = widget;self.host = host
        self.key = None;self.k = None;self.light = None;self.light_key = None
        self.static_until = 0.0;self.static_from = 0.0;self.strong = False;self.rng = random.Random(1003)
        self.paint_ms = deque(maxlen=120);self.frames = 0;self.seen_until = None
        self.timer = None
        if clock:
            self.timer = QTimer(self);self.timer.setTimerType(Qt.CoarseTimer);self.timer.setInterval(FRAME_MS);self.timer.timeout.connect(self.tick)
            widget.installEventFilter(self)
            try:host.installEventFilter(self)
            except Exception:  # noqa: BLE001 - a host that is not a widget: no window to watch
                pass
            try:QGuiApplication.instance().applicationStateChanged.connect(self.wake_or_sleep)
            except Exception:  # noqa: BLE001
                pass

    # -- what she is drawn from -------------------------------------------------------------------------------------------
    def take(self, image, key):
        if key == self.key and self.k is not None:return
        self.key = key;self.k = keyed(image, key);self.light = None;self.light_key = None
        self.arrive()

    def share_from(self, other):
        if other.k is not None and (other.key != self.key or self.k is None):
            self.key = other.key;self.k = other.k;self.light = None;self.light_key = None

    def aspect(self, share):
        part = shown(self.k, share) if self.k is not None else QRect()
        return part.width() / part.height() if not part.isEmpty() else 0.5

    # -- motion -----------------------------------------------------------------------------------------------------------
    def still(self):
        try:
            from .document_qt import profile_of
            return bool(profile_of(self.host).get('reduce_motion'))
        except Exception:  # noqa: BLE001 - when it cannot be told, she keeps still
            return True

    def covered(self):
        try:
            from .her_column_qt import moment_on
            return moment_on(self.host)
        except Exception:  # noqa: BLE001
            return False

    def running(self):
        """Her frames run only while she can be seen and motion is wanted."""
        w = self.widget
        try:
            window = w.window()
            return (not getattr(self.host, '_closing', False) and w.isVisible() and window is not None and not window.isMinimized()
                    and app_active() and not self.still() and not self.covered())
        except RuntimeError:      # the window is closing
            return False

    def wake_or_sleep(self, *_):
        if self.timer is None:return False
        run = self.running()
        if run and not self.timer.isActive():self.timer.start()
        elif not run and self.timer.isActive():self.timer.stop()
        return run

    def sleep(self):
        if self.timer is not None and self.timer.isActive():self.timer.stop()

    def tick(self):
        if not self.running():self.timer.stop();return
        self.widget.update()

    def changed(self):
        """Her state changed: a brief static (none when still)."""
        if self.still():return
        now = time.monotonic();self.static_from = now;self.static_until = now + STATIC_MS / 1000.0;self.strong = False
        self.wake_or_sleep()

    def arrive(self, strong=True):
        """She arrives (a new picture, a moment): a stronger static (none when still)."""
        if self.still():self.static_until = 0.0;return
        now = time.monotonic();self.static_from = now;self.static_until = now + ARRIVE_MS / 1000.0;self.strong = strong
        self.wake_or_sleep()

    def eventFilter(self, watched, event):
        kind = event.type()
        if watched is self.widget and kind in (QEvent.Show, QEvent.Hide):QTimer.singleShot(0, self.wake_or_sleep)
        elif kind in (QEvent.WindowStateChange, QEvent.ActivationChange):QTimer.singleShot(0, self.wake_or_sleep)
        return False

    # -- drawing ----------------------------------------------------------------------------------------------------------
    def layers(self, share, w, h, dpr, fade=FADE):
        W, H = max(4, round(w * dpr)), max(4, round(h * dpr));key = (self.key, round(share * 1000), W, H, round(fade * 1000))
        if self.light is None or self.light_key != key:self.light = Light(self.k, share, W, H, fade);self.light_key = key
        return self.light

    def paint_glass(self, p, room, dpr):
        """Day's glass, drawn once a size and kept (a frame lays the kept image down)."""
        x, y = math.floor(room.left()), math.floor(room.top())      # laid down on whole pixels: no resampling blurs its rim
        key = (round(room.width() * 2), round(room.height() * 2), room.left() - x, room.top() - y, dpr, self.k.tint.rgb())
        if getattr(self, '_glass', None) is None or self._glass[0] != key:
            image = QImage(max(1, math.ceil((room.width() + 2) * dpr)), max(1, math.ceil((room.height() + 4) * dpr)), QImage.Format_ARGB32_Premultiplied)
            image.setDevicePixelRatio(dpr);image.fill(Qt.transparent)
            q = QPainter(image);glass(q, QRectF(room.left() - x, room.top() - y, room.width(), room.height()), self.k.tint);q.end()
            self._glass = (key, image)
        p.drawImage(QPointF(x, y), self._glass[1])

    def paint(self, p, fig, share, room=None, fade=FADE):
        """One frame of her in fig (QRectF, the painter's coordinates); in Day, her glass over room first."""
        started = time.perf_counter()
        if self.k is None or self.k.image.isNull() or fig.width() < 4 or fig.height() < 4:return False
        dpr = self.widget.devicePixelRatioF();L = self.layers(share, fig.width(), fig.height(), dpr, fade)
        now = time.monotonic();still = self.still()
        p.save();p.setRenderHint(QPainter.SmoothPixmapTransform)
        if room is not None and bt.APPEARANCE == 'day':self.paint_glass(p, room, dpr)
        breath = 1.0 if still else 0.92 + 0.08 * (0.5 + 0.5 * math.sin(2 * math.pi * now / BREATH_S))
        m = L.margin / dpr;W, H = L.size
        p.setOpacity((0.70 if bt.APPEARANCE == 'day' else 0.55) * breath)
        p.drawImage(QRectF(fig.x() - m, fig.y() - m, fig.width() + 2 * m, fig.height() + 2 * m), L.glow)
        static = (not still) and now < self.static_until
        phase = 0 if still else int(now * 4) % 3
        her = L.statics()[self.frames % 3] if static else L.scans[phase]
        p.setOpacity(0.95 * breath);p.drawImage(fig, her)
        if static:      # a tear or two: a strip of her moved sideways, fading as the static ends
            share_left = max(0.0, (self.static_until - now) / max(0.05, self.static_until - self.static_from))
            for _ in range(2 if self.strong else 1):
                bh = max(2, round(H * self.rng.uniform(0.02, 0.07)));y = self.rng.randrange(0, max(1, H - bh))
                dx = self.rng.choice((-1, 1)) * self.rng.uniform(0.02, 0.07) * fig.width()
                p.setOpacity(0.85 * share_left)
                p.drawImage(QRectF(fig.x() + dx, fig.y() + y / dpr, fig.width(), bh / dpr), her, QRectF(0, y, W, bh))
        elif not still:      # the shimmer: a soft band of light passing down through her
            at = (now % SHIMMER_S) / SHIMMER_S;centre = (-0.12 + 1.24 * at) * H;half = max(4.0, H * 0.05)
            for lo, hi, alpha in ((-half, -half / 3, 0.12), (-half / 3, half / 3, 0.26), (half / 3, half, 0.12)):
                a, b = max(0.0, centre + lo), min(float(H), centre + hi)
                if b - a >= 1:
                    p.setOpacity(alpha * breath)
                    p.drawImage(QRectF(fig.x(), fig.y() + a / dpr, fig.width(), (b - a) / dpr), L.bright, QRectF(0, a, W, b - a))
        p.restore();self.frames += 1
        self.paint_ms.append((time.perf_counter() - started) * 1000)
        return True

    def describe(self):
        k = self.k
        return {'key': self.key, 'cut_ms': k.ms if k else None, 'own_alpha': k.own if k else None,
                'ink': (k.ink.x(), k.ink.y(), k.ink.width(), k.ink.height()) if k else None,
                'tint': k.tint.name() if k else None, 'running': bool(self.timer and self.timer.isActive()),
                'frames': self.frames, 'paint_ms_last': round(self.paint_ms[-1], 2) if self.paint_ms else None,
                'static': time.monotonic() < self.static_until}


# ---------------------------------------------------------------------------------------- her_column_qt's hooks (1.0 P3)
def tall(image):
    return image is not None and not image.isNull() and image.height() > image.width()


def standing(portrait):
    """Her hologram on her portrait when her picture is taller than it is wide, else None (P1's circle)."""
    try:
        image, _, _, _, key = portrait.image()
    except Exception:  # noqa: BLE001 - a portrait that cannot say its picture: P1's circle
        return None
    holo = getattr(portrait, 'holo', None)
    if not tall(image):
        if holo is not None:      # a wide or square picture now: her clock goes with her hologram
            portrait.holo = None;holo.sleep();holo.deleteLater()
        return None
    if holo is None:
        holo = Hologram(portrait, portrait.host);portrait.holo = holo
    holo.take(image, key)
    if holo.k is None or holo.k.image.isNull():return None
    return holo


def share_of(column):
    try:return SHOW_COMPACT if column.compact() else SHOW_TALL
    except Exception:  # noqa: BLE001
        return SHOW_TALL


def in_column(host):
    """Whether her column's portrait stands as a hologram (hologram_qt: the left pane's then stands aside)."""
    column = getattr(host, 'her_column', None)
    if column is None:return False
    try:return standing(column.head.stage.portrait) is not None
    except Exception:  # noqa: BLE001
        return False


def slot_height(column, h, fallback):
    """Her stage's height: tall when she stands as a hologram, else P1's."""
    try:
        if standing(column.head.stage.portrait) is None:return fallback
        from .her_column_qt import px
        host = column.host
        if column.compact():return max(80, min(px(host, 96), round(h * 0.16)))
        return max(px(host, 150), min(px(host, 340), round(h * 0.30)))
    except Exception:  # noqa: BLE001
        return fallback


def arrange(stage):
    """Her stage laid out for her hologram: her box (her figure and its glow; in Day her glass), and the equalizer's bars
    behind and beside her. False when she is P1's circle (P1 lays it out)."""
    portrait = stage.portrait;holo = standing(portrait)
    if holo is None:
        portrait.figure = None;return False
    w, h = stage.width(), stage.height();share = share_of(portrait.column);day = bt.APPEARANCE == 'day'
    fig = fit(holo.k, share, w - (24 if day else 8), h - (6 if day else 2), 0.60 if day else 0.86)      # Day: room for the bars beside her glass
    fig.translate((24 if day else 8) // 2, 6 if day else 2)
    if fig.isEmpty():
        portrait.figure = None;return False
    if day:
        pad = max(8, round(fig.width() * 0.07));top = max(0, fig.y() - pad)      # her glass: her size, standing on the stage's foot
        box = QRect(fig.x() - pad, top, fig.width() + 2 * pad, h - top)
    else:
        m = max(4, round(fig.width() * 0.08));box = fig.adjusted(-m, -m, m, m).intersected(stage.rect())
    portrait.setGeometry(box);portrait.figure = fig.translated(-box.topLeft());portrait.arranged = (holo.key, share, w, h)
    eq = stage.equalizer;top = round(h * (EQ_TOP_COMPACT if portrait.column.compact() else EQ_TOP))
    eq.hole = box.width() + 6 if day else max(24, round(fig.width() * HOLE))
    eq.setGeometry(0, top, w, h - top);eq._places = None;eq._floor = None;eq._scope = None;eq._sprites = None
    portrait.raise_()
    return True


def paint_portrait(portrait):
    """Her stage's frame, when she stands as a hologram; False for P1's circle."""
    holo = standing(portrait)
    if holo is None:return False
    share = share_of(portrait.column);stage = portrait.parentWidget()
    fig = getattr(portrait, 'figure', None)
    if fig is None or getattr(portrait, 'arranged', None) != (holo.key, share, stage.width() if stage else 0, stage.height() if stage else 0):
        def again():      # laid out for the circle until now: the tall slot, then her box
            try:portrait.column.size_parts();stage.arrange()
            except Exception:  # noqa: BLE001
                pass
        QTimer.singleShot(0, again)
        if fig is None:fig = fit(holo.k, share, portrait.width(), portrait.height())
    p = QPainter(portrait)
    try:
        p.setRenderHint(QPainter.Antialiasing)
        done = holo.paint(p, QRectF(fig), share, QRectF(portrait.rect()).adjusted(0.5, 0.5, -0.5, -0.5))
    finally:
        p.end()
    holo.wake_or_sleep()
    return done


# -- a moment that matters: her full figure, larger, in her stage's place --------------------------------------------------
def _words_height(moment):
    from .her_column_qt import px
    font = QFont(bt.FACE);font.setPixelSize(px(moment.host, 14));fm = QFontMetrics(font)
    return fm.lineSpacing() * 3 + fm.lineSpacing() + 18


def moment_box(moment):
    """The moment's card when she stands as a hologram: from her stage's top, as tall as her full figure at the column's
    width needs (at most four fifths of the column) and the moment's words under her. None for P1's card."""
    try:
        column = moment.column;holo = standing(column.head.stage.portrait)
        if holo is None:return None
        face = column.face;W, H = face.width(), face.height();words = _words_height(moment)
        aspect = holo.aspect(1.0);room_w = W - 16 - (24 if bt.APPEARANCE == 'day' else 0)
        fig_h = min(room_w / max(0.05, aspect), H * 0.80 - words - 16)
        tall = min(H - 8, round(max(120, fig_h) + words + 20))
        top = max(0, column.head.geometry().top() if column.head is not None else 0);bottom = top + min(tall, H - top - 4)
        lay = face.layout()      # never half a section: the card's foot goes to the end of the part it would cut through
        for i in range(lay.count() if lay is not None else 0):
            part = lay.itemAt(i).widget()
            if part is None or part.isHidden() or part is column.head or part is face.scroll:continue
            g = part.geometry()
            if g.top() < bottom < g.bottom():
                bottom = g.bottom() + 2 if g.bottom() + 2 <= H - 4 else g.top() - 4
                break
        return QRect(0, top, W, max(120, bottom - top))
    except Exception:  # noqa: BLE001
        return None


def paint_moment(moment):
    """The moment's card: her full figure as a hologram (in Day on her glass), the moment in words under her, the hint."""
    try:
        holo = standing(moment.column.head.stage.portrait)
    except Exception:  # noqa: BLE001
        holo = None
    if holo is None:return False
    box = moment_box(moment)
    if box is not None and box != moment.geometry():      # her column's sections moved under the card (a press, a new row)
        QTimer.singleShot(0, lambda: moment.setGeometry(box) if moment.isVisible() else None)
    mine = getattr(moment, 'holo', None)
    if mine is None:
        mine = moment.holo = Hologram(moment, moment.host, clock=False)
    mine.share_from(holo)
    if mine.seen_until != moment.until:      # a new moment: she arrives
        mine.seen_until = moment.until;mine.arrive(strong=True)
    from .her_column_qt import colour, px, say
    p = QPainter(moment);p.setRenderHint(QPainter.Antialiasing);p.setRenderHint(QPainter.SmoothPixmapTransform)
    try:
        r = QRectF(moment.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setBrush(QColor(bt.TERMINAL_GROUND));p.setPen(QPen(QColor(bt.LINE_STRONG if bt.APPEARANCE != 'day' else bt.LINE), 1));p.drawRoundedRect(r, 6, 6)
        font = QFont(bt.FACE);font.setPixelSize(px(moment.host, 14));p.setFont(font);fm = QFontMetrics(font)
        words_h = fm.lineSpacing() * 3 + 6;hint_h = fm.lineSpacing()
        art = QRectF(r.left() + 8, r.top() + 8, r.width() - 16, r.height() - words_h - hint_h - 22)
        day = bt.APPEARANCE == 'day'
        if art.height() > 40:
            inner = art.adjusted(12, 8, -12, -2) if day else art
            box = fit(mine.k, 1.0, round(inner.width()), round(inner.height()), 1.0)
            fig = QRectF(inner.left() + box.x(), inner.top() + box.y(), box.width(), box.height())
            room = QRectF(fig.left() - max(8, fig.width() * 0.07), art.top(), fig.width() + 2 * max(8, fig.width() * 0.07), art.height()) if day else None
            mine.paint(p, fig, 1.0, room, fade=0.08)
        name = {'refuted': 'RED', 'done': 'HONEY', 'halt': 'RED'}.get(moment.kind, 'TEXT')
        p.setOpacity(1.0);p.setFont(font);p.setPen(QColor(colour(name)))
        p.drawText(QRectF(r.left() + 12, r.bottom() - words_h - hint_h - 8, r.width() - 24, words_h), Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap, moment.words)
        small = QFont(bt.FACE);small.setPixelSize(px(moment.host, 11));p.setFont(small);p.setPen(QColor(bt.FAINT))
        p.drawText(QRectF(r.left() + 12, r.bottom() - hint_h - 4, r.width() - 24, hint_h), Qt.AlignRight | Qt.AlignBottom, say('moment_hint'))
    finally:
        p.end()
    return True
