"""Kasandra's hologram, standing in the empty lower part of the left pane (0.8.3).

The owner, 14 November 2026: "We're going to move the kasandra picture to lower left column where it's boring looking" and
"I will attach the new kas picture that I want to be like a hologram in its new position. If you can animate the static a
hologram would have that would be very kool."

HologramStage is a child of the left pane, laid over its content and foot where the tree has no rows and DELETE is not
(hologram.place says where; it is placed again at once whenever the rows change, so it never covers one). It takes no
clicks: the pointer goes through it to the tree and to DELETE. It paints its own ground, a beam and a breathing base in the
colour of the state of the work, and her picture with the life of a projection laid over it: static that lands on her only,
scan lines drifting down, a slow flicker, now and then a tear. In Kasandra only, with the Illustrated desk; the ASCII desk
draws her once in characters; the Clean desk shows nothing. With Reduce motion, or the Clean glow, she is one still frame.

Cost: the picture is decoded once (a picture that will not decode is never shown, and never decoded again); each size keeps
its layers (the last two sizes); her figure with each of its six static patterns and its fringe is composed once a state,
and her beam and base once a colour (only the part of the stage they light). A quiet frame is then the ground, her base,
her composed figure and the scan lines over it: four fills, none composed again. A band (at work, done) or a tear is
composed on a copy for the frames that show it. The timer runs at 12 frames a second only while she is shown, the window
is active and not minimised, the idle display is not up, and nothing asked for less motion.
"""
from __future__ import annotations

import math
import random
import time

from PySide6.QtCore import QEvent, QObject, QPointF, QRect, QRectF, Qt, QTimer
from PySide6.QtGui import (QBrush, QColor, QFont, QFontMetricsF, QGuiApplication, QImage, QLinearGradient, QPainter,
                           QPainterPath, QPen, QRadialGradient)
from PySide6.QtWidgets import QWidget

from . import boss_theme as t
from . import hologram as holo
from .assistant_identity import named

GROUND = '#171b3c'          # the pane's ground under her (boss_theme GROUND in Kasandra): she paints it herself
CYAN, PINK = '#83eaff', '#f23e6b'
WRITE = '#b9f4ff'
POWER_MS = 40               # the timer's pace during the power-up
QUIET_AFTER = 10.0          # hidden this long, she powers up again when she comes back
TOUCH_GAP = 1.5             # a touch tears at most this often
BASE_HEADROOM = 1.3         # the base layer is drawn this much stronger than at rest, and laid down at breath / this
NOISE_TILES = 6
TILE = 64


def app_active():
    """Whether this application is the one in front (a window of another program, or none, stops her frames)."""
    return QGuiApplication.applicationState() == Qt.ApplicationActive


def _noise_tiles(seed=83):
    """Six 64 x 64 tiles of static: one pixel in nine lit, at a random strength, half pale and half dark. Built from random
    bytes once, shared by every size (a brush repeats them)."""
    tiles = []
    for k in range(NOISE_TILES):
        rng = random.Random(seed + k)
        pick = rng.randbytes(TILE * TILE);strength = rng.randbytes(TILE * TILE)
        raw = bytearray(TILE * TILE * 4)
        for i in range(TILE * TILE):
            s = pick[i]
            if s >= 28:continue                      # 28 of 256: about one in nine
            a = strength[i]
            if s < 14:raw[4 * i:4 * i + 4] = bytes((a, a, a, a))       # pale (premultiplied white)
            else:raw[4 * i:4 * i + 4] = bytes((0x1e * a // 255, 0x08 * a // 255, 0x0a * a // 255, a))       # dark #0a081e
        tiles.append(QImage(bytes(raw), TILE, TILE, TILE * 4, QImage.Format_ARGB32_Premultiplied).copy())
    return tiles


_TILES = []


def noise_tiles():
    if not _TILES:_TILES.extend(_noise_tiles())
    return _TILES


_SCAN = []
SCAN_ALPHA = 70             # each third row of her, a little of the ground (27%) laid over: her scan lines


def scan_tile():
    """The scan lines' tile, built once: one row in three of the ground's colour at SCAN_ALPHA, laid over her each frame
    (a brush repeats it; its origin moves with the drift). 256 px wide: a tile one pixel wide made Qt's tiled fill go a
    pixel at a time (0.5 ms a frame at 281 x 380); this one fills a row in a few spans."""
    if not _SCAN:
        tile = QImage(256, 3, QImage.Format_ARGB32_Premultiplied);tile.fill(Qt.transparent)
        ink = QColor(GROUND);ink.setAlpha(SCAN_ALPHA)
        for x in range(256):tile.setPixelColor(x, 0, ink)
        _SCAN.append(tile)
    return _SCAN[0]


def silhouette(figure, colour):
    out = QImage(figure.size(), QImage.Format_ARGB32_Premultiplied);out.fill(QColor(colour))
    p = QPainter(out);p.setCompositionMode(QPainter.CompositionMode_DestinationIn);p.drawImage(0, 0, figure);p.end()
    return out


FRINGE = 0.10               # the projector's cyan fringe, a pixel to her right, under her


def layers(cut, w, h):
    """Her figure at w x h device pixels, faded over its lowest 14% (she rises out of her beam), with its cyan and pink
    silhouettes, a grey twin, the frame buffer reused for every frame of this size that is composed again (one pixel wider
    than her, for the fringe), and her composed figures (still_part)."""
    figure = cut.scaled(w, h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation).convertToFormat(QImage.Format_ARGB32_Premultiplied)
    p = QPainter(figure);p.setCompositionMode(QPainter.CompositionMode_DestinationIn)
    fade = QLinearGradient(0, h * 0.86, 0, h);fade.setColorAt(0, QColor(0, 0, 0, 255));fade.setColorAt(1, QColor(0, 0, 0, 0))
    p.fillRect(QRect(0, int(h * 0.86), w, h - int(h * 0.86)), fade);p.end()
    grey = figure.convertToFormat(QImage.Format_Grayscale8).convertToFormat(QImage.Format_ARGB32_Premultiplied)
    q = QPainter(grey);q.setCompositionMode(QPainter.CompositionMode_DestinationIn);q.drawImage(0, 0, figure);q.end()
    return dict(size=(w, h), figure=figure, cyan=silhouette(figure, CYAN), pink=silhouette(figure, PINK), grey=grey,
                frame=QImage(w + 1, h, QImage.Format_ARGB32_Premultiplied), still={})


def still_part(L, static, grey, noise_index, noise_offset, keep=True):
    """Her figure, greyed when blocked, with one of the six static patterns on her only, over the projector's fringe: what
    a frame shows before its scan lines (laid over at paint time), a band and a tear. One pixel wider than her. Composed
    once and kept (six at most a size: the patterns a state cycles through); keep=False for the power-up's stronger static."""
    key = (round(static, 3), round(grey, 3), noise_index, tuple(noise_offset))
    kept = L['still']
    if keep and key in kept:return kept[key]
    w, h = L['size']
    her = L['figure'].copy();p = QPainter(her)
    if grey > 0:p.setOpacity(grey);p.drawImage(0, 0, L['grey']);p.setOpacity(1.0)
    if static > 0:
        p.setCompositionMode(QPainter.CompositionMode_SourceAtop);p.setOpacity(min(1.0, static))
        ox, oy = noise_offset;p.setBrushOrigin(-ox, -oy)      # a moved origin keeps Qt's fast tiled fill
        p.fillRect(QRect(0, 0, w, h), QBrush(noise_tiles()[noise_index]))
    p.end()
    image = QImage(w + 1, h, QImage.Format_ARGB32_Premultiplied);image.fill(Qt.transparent)
    q = QPainter(image);q.setOpacity(FRINGE);q.drawImage(1, 0, L['cyan']);q.setOpacity(1.0);q.drawImage(0, 0, her);q.end()
    if keep:
        while len(kept) >= holo.NOISE_KEYS:kept.pop(next(iter(kept)))
        kept[key] = image
    return image


def paint_scan(p, rect, offset):
    """Her scan lines, over her rect (logical pixels): a tiled fill, its origin moved down by the drift."""
    p.setBrushOrigin(QPointF(rect.x(), rect.y() + offset));p.fillRect(rect, QBrush(scan_tile()));p.setBrushOrigin(QPointF(0, 0))


def compose(L, plan, s=1.0):
    """One frame of her (device pixels, one pixel wider than her): her composed figure (still_part), and, only in the frames
    that show one, a write band (at work), the lock sweep (done) or a tear, composed on a copy in L['frame']. The scan lines
    are laid over at paint time (paint_scan). Returns the frame."""
    power = plan['power']
    static = plan['static'] * (3.0 - 2.0 * reveal(power) if power is not None else 1.0)
    base = still_part(L, static, plan['grey'], plan['noise_index'], plan['noise_offset'], keep=power is None)
    tear = plan['tear']
    if plan['write_y'] is None and plan['sweep_y'] is None and tear is None:return base
    frame = L['frame'];w, h = L['size']
    p = QPainter(frame);p.setCompositionMode(QPainter.CompositionMode_Source);p.drawImage(0, 0, base)
    p.setCompositionMode(QPainter.CompositionMode_SourceAtop)
    for y, alpha, band in ((plan['write_y'], 0.18, 20 * s), (plan['sweep_y'], 0.25, 14 * s)):
        if y is None:continue
        top = y * h - band / 2;g = QLinearGradient(0, top, 0, top + band)
        for at, a in ((0.0, 0.0), (0.5, alpha), (1.0, 0.0)):
            c = QColor(WRITE);c.setAlphaF(a);g.setColorAt(at, c)
        p.fillRect(QRectF(0, top, w + 1, band), g)
    p.end()
    if tear is not None:
        band_h = max(2, round(tear['h'] * s));y = int(max(0, min(h - band_h, tear['y'] * h)));dx = round(tear['dx'] * s)
        strip = QRect(0, y, w + 1, band_h);piece = frame.copy(strip)
        p = QPainter(frame);p.setCompositionMode(QPainter.CompositionMode_Source);p.fillRect(strip, Qt.transparent)
        p.setCompositionMode(QPainter.CompositionMode_SourceOver);p.drawImage(dx, y, piece)
        p.setClipRect(strip);p.setOpacity(0.22)
        p.drawImage(QRectF(dx - 1, y, w, band_h), L['cyan'], QRectF(0, y, w, band_h))
        p.drawImage(QRectF(dx + 1, y, w, band_h), L['pink'], QRectF(0, y, w, band_h))
        p.end()
    return frame


def reveal(power):
    """The share of her shown during a power-up (0 to 1): nothing for its first third, while her base lights."""
    if power is None:return 1.0
    return max(0.0, min(1.0, (power * holo.POWER * 1000 - 120) / 240))


class HologramStage(QWidget):
    """Her place in the left pane: placed by place(), painted by paintEvent, moved on by its own timer."""

    def __init__(self, host, pane, path):
        super().__init__(pane);self.host = host;self.pane = pane;self.path = path
        self.setObjectName('HologramStage')
        self.setAttribute(Qt.WA_TransparentForMouseEvents);self.setAttribute(Qt.WA_OpaquePaintEvent);self.setFocusPolicy(Qt.NoFocus)
        self.stance = None;self.figure = QRect();self.layers = None;self._sizes = {};self.memo = {};self.rng = random.Random(83)
        self.state = 'idle';self.state_at = time.monotonic();self._read_at = 0.0;self.colour_from = None;self.colour_at = 0.0
        self.shown_at = None;self.hidden_at = time.monotonic() - 3600;self.power_at = None;self.touched_at = 0.0;self._inside = False
        self.clock = None            # None: time.monotonic(); a function: the frames' own clock (held for frames and tests)
        self.paint_ms = []           # the last frames' compose-and-paint times
        self._timer = QTimer(self);self._timer.setTimerType(Qt.CoarseTimer);self._timer.setInterval(holo.FRAME_MS)
        self._timer.timeout.connect(self.tick)
        self._watch = QTimer(self);self._watch.setInterval(1000);self._watch.timeout.connect(self.follow)
        self._ascii = None
        from . import kasandra_art
        kasandra_art.watch(host, self)
        self.hide();self.set_name()

    # -- what is true now ------------------------------------------------------------------------------------------------
    def now(self):
        return self.clock() if self.clock is not None else time.monotonic()

    def desk(self):
        try:return self.host.session.state.get('desk_art', 'illustrated')
        except Exception:  # noqa: BLE001 - a host without a session: the Illustrated desk
            return 'illustrated'

    def still(self):
        """Reduce motion (the reading profile), or the Clean glow: one still frame."""
        from . import menu_catch, pane_qt
        try:
            return bool(pane_qt.still(self.pane)) or bool(menu_catch.calm(self))
        except Exception:  # noqa: BLE001 - when it cannot be told, she keeps still
            return True

    def set_name(self):
        self.setAccessibleName(named('Stacy') + ', projected · ' + holo.look(self.state)[0])

    def base_colour(self):
        """The colour of the state of the work (hologram.STATE_LOOK), which her masthead's cursor shares."""
        return QColor(getattr(t, holo.look(self.state)[1]))

    def update(self, *args):      # kasandra_art.nudge: an act ended, so the state is read now
        if not args:self.follow(force=True)
        super().update(*args)

    def follow(self, force=False):
        """Read the state of the work (at most every 250 ms); a change repaints once, and is shown on her masthead."""
        stamp = time.monotonic()
        if not force and stamp - self._read_at < 0.25:return
        self._read_at = stamp
        from .kasandra_art import column_state
        try:state = column_state(self.host)
        except Exception:  # noqa: BLE001
            state = 'idle'
        if state == 'viewing':state = 'idle'
        if state == self.state:return
        self.colour_from = self.base_colour();self.colour_at = self.now()
        self.state = state;self.state_at = self.now();self.memo = {};self.set_name()
        mast = getattr(getattr(getattr(self.host, 'shell2', None), 'face', None), 'masthead', None)
        if mast is not None:mast.show_state(state)
        QWidget.update(self)

    # -- where she stands ------------------------------------------------------------------------------------------------
    def tree(self):
        """The tree shown in the left pane now, or None (Settings: she stands aside there)."""
        nav = getattr(self.host, 'settings_navigator', None)
        trees = getattr(self.host, 'desk_trees', None) or []
        if nav is None or not trees:return None
        page = nav.stack.currentWidget()
        for tree in trees[:2]:      # Machine, Files; never Settings
            if tree is page or (page is not None and page.isAncestorOf(tree)):return tree
        return None

    def rows_end(self, tree):
        """Where the rows end in the pane, worked out from the rows that are open (so she moves aside before the tree has
        laid itself out), or None when they would scroll."""
        from PySide6.QtCore import QPoint

        def count(item):
            n = 0 if item.isHidden() else 1
            if n and item.isExpanded():n += sum(count(item.child(i)) for i in range(item.childCount()))
            return n
        rows = sum(count(tree.topLevelItem(i)) for i in range(tree.topLevelItemCount()))
        row = tree.row_height or tree.sizeHintForRow(0) or 1
        viewport = tree.viewport()
        top = viewport.mapTo(self.pane, QPoint(0, 0)).y()
        return holo.rows_bottom(rows, row, top, viewport.height())

    def placement(self):
        tree = self.tree()
        if tree is None or not tree.isVisibleTo(self.pane):return None
        foot = self.pane.foot;trash = foot.trash
        if trash is None:return None
        delete = (foot.slot.x(), foot.y() + foot.slot.y(), foot.slot.width(), foot.slot.height())
        s = float(getattr(getattr(self.host, 'desk', None), 'scale', 1.0) or 1.0)
        return holo.place(self.rows_end(tree), foot.y(), delete, self.pane.width(), getattr(self.pane, 'inset', 16), s)

    def place_now(self, *_):
        """Placed again at once (inside the signal that changed the rows), so she never covers a row for a frame."""
        if getattr(self.host, '_closing', False):return
        try:self._place()
        except RuntimeError:  # a part of the window already gone (it is closing)
            pass

    def _place(self):
        if self.desk() == 'clean':
            self.stand_aside(drop=True);return
        found = self.placement()
        if found is None:
            self.stand_aside();return
        self.stance, figure, stage = found
        box = QRect(*stage)
        self.figure = QRect(figure[0] - box.x(), figure[1] - box.y(), figure[2], figure[3])
        moved = self.geometry() != box or self.isHidden()
        if self.geometry() != box:self.setGeometry(box)
        if self.isHidden():
            stamp = time.monotonic()
            if self.shown_at is None or stamp - self.hidden_at >= QUIET_AFTER:self.power_at = self.now()      # she powers up
            self.shown_at = stamp;self.show()
        if not self._watch.isActive():self._watch.start()
        self.follow();self.wake_or_sleep()
        if moved:self.raise_();QWidget.update(self)      # the desk asks again every half second: only a change is drawn again

    def stand_aside(self, drop=False):
        if not self.isHidden():self.hidden_at = time.monotonic();self.hide()
        self._timer.stop();self._watch.stop()
        if drop:self.layers = None;self._sizes.clear();self._ascii = None;self.shown_at = None

    # -- the clock -------------------------------------------------------------------------------------------------------
    def wake_or_sleep(self, *_):
        """Run the frames only while they can be seen and are wanted; asleep she keeps her last frame."""
        window = self.window()
        idle = getattr(getattr(self.host, 'idle_display', None), 'showing', False)      # a property (a bool); a function in a test
        idle = idle() if callable(idle) else bool(idle)
        run = (t.APPEARANCE == 'kasandra' and self.desk() == 'illustrated' and not self.isHidden() and self.isVisible()
               and window is not None and not window.isMinimized()
               and app_active()
               and not idle and not self.still())
        pace = POWER_MS if self.power_at is not None and self.now() - self.power_at < holo.POWER else holo.FRAME_MS
        if run:
            if self._timer.interval() != pace:self._timer.setInterval(pace)
            if not self._timer.isActive():self._timer.start()
        elif self._timer.isActive():self._timer.stop()
        mast = getattr(getattr(getattr(self.host, 'shell2', None), 'face', None), 'masthead', None)
        if mast is not None:mast.cursor.wake_or_sleep()      # her cursor sleeps and wakes with her
        return run

    def tick(self):
        if self.power_at is not None and self.now() - self.power_at >= holo.POWER:
            self.power_at = None;self._timer.setInterval(holo.FRAME_MS)
        QWidget.update(self)

    def touch(self, point):
        """The pointer reached her (a point in the pane): one small tear and a little more light, at most every 1.5 s."""
        inside = self.isVisible() and self.geometry().contains(point) and self.figure.translated(self.pos()).contains(point)
        awake = self._timer.isActive()      # asleep (another program in front, minimised), no frame would follow to mend a tear
        if inside and not self._inside and awake and not self.still() and self.state not in ('awaiting_approval', 'blocked'):
            stamp = time.monotonic()
            if stamp - self.touched_at >= TOUCH_GAP:
                self.touched_at = stamp
                if self.memo is None:self.memo = {}
                self.memo['touch'] = True;QWidget.update(self)
        self._inside = inside

    # -- painting --------------------------------------------------------------------------------------------------------
    def size_layers(self, w, h):
        key = (w, h)
        if key not in self._sizes:
            from .kasandra_art import cutout
            self._sizes[key] = layers(cutout(self.path), w, h)
            while len(self._sizes) > 2:self._sizes.pop(next(iter(self._sizes)))
        self.layers = self._sizes[key]
        return self.layers

    def plan(self, now=None):
        now = self.now() if now is None else now
        from .kasandra_art import glitch_rows
        since_show = (now - self.power_at) if self.power_at is not None else None
        self._still = self.still()      # read once a frame (base_rgb asks too)
        return holo.frame_plan(self.state, now, self.rng, self._still, now - self.state_at, since_show, self.memo, glitch_rows(self.path))

    def base_rgb(self, plan, now):
        """The base's colour: the plan's, cross-faded from the last state's over 400 ms (at once when still)."""
        to = QColor(*plan['base_rgb'])
        if self.colour_from is None or getattr(self, '_still', True):return to
        share = max(0.0, min(1.0, (now - self.colour_at) / 0.4))
        if share >= 1.0:self.colour_from = None;return to
        a = self.colour_from
        return QColor(round(a.red() + (to.red() - a.red()) * share), round(a.green() + (to.green() - a.green()) * share),
                      round(a.blue() + (to.blue() - a.blue()) * share))

    def paintEvent(self, event):
        started = time.perf_counter()
        p = QPainter(self);p.fillRect(self.rect(), QColor(GROUND))
        if self.figure.isEmpty():p.end();return
        if self.desk() == 'ascii':self.paint_ascii(p);p.end();return
        now = self.now();plan = self.plan(now);s = float(getattr(getattr(self.host, 'desk', None), 'scale', 1.0) or 1.0)
        dpr = self.devicePixelRatioF();fig = self.figure;w, h = fig.width(), fig.height()
        L = self.size_layers(max(2, round(w * dpr)), max(2, round(h * dpr)))
        frame = compose(L, plan, s * dpr);W, H = L['size']
        colour = self.base_rgb(plan, now);breath = plan['base_alpha']
        rim = 1.0;shown = 1.0
        if plan['power'] is not None:
            ms = plan['power'] * holo.POWER * 1000;rim = min(1.0, ms / 120.0);shown = reveal(plan['power'])
        # the beam and the base she stands on, drawn once for this size and colour and laid down at the breath's strength
        lit, top = self.base_layer(colour, s, dpr)
        p.setOpacity(min(1.0, breath * rim / BASE_HEADROOM));p.drawImage(QRectF(0, top, self.width(), self.height() - top), lit);p.setOpacity(1.0)
        # her, revealed from the bottom up while she powers up
        if shown < 1.0:
            cut = fig.top() + round((1.0 - shown) * h);p.save();p.setClipRect(QRect(fig.left(), cut, w + 1, fig.bottom() - cut + 1))
        opacity = plan['opacity'] * plan['flicker'] * (1.06 if plan['tear'] is not None and plan['tear'].get('touch') else 1.0)
        p.setOpacity(min(1.0, opacity));p.drawImage(QRectF(fig.x(), fig.y(), (W + 1) / dpr, H / dpr), frame)      # her, with her fringe
        p.setOpacity(1.0);paint_scan(p, QRectF(fig.x(), fig.y(), w + 1, h), plan['scan_offset'])
        if shown < 1.0:
            p.restore()
            if shown > 0:p.fillRect(QRectF(fig.left(), fig.top() + (1.0 - shown) * h - 1, w, 2), QColor(t.READY))      # the scan edge
        p.end()
        self.paint_ms.append((time.perf_counter() - started) * 1000);del self.paint_ms[:-120]
        if plan['power'] is None and self._timer.interval() != holo.FRAME_MS and self._timer.isActive():self._timer.setInterval(holo.FRAME_MS)

    def base_layer(self, colour, s, dpr):
        """Her beam (from her base up through her, fading to nothing), the base's glow and its rim, on a clear image as wide as
        the stage and as tall as the part they light (from the beam's top down), at BASE_HEADROOM times their strength so a
        breath above 1 still shows. Returns (image, its top in the stage). Kept while the size and the colour stay; a colour
        is kept to steps of 4, so a slow fade draws it again only now and then."""
        q = QColor(colour);colour = QColor((q.red() // 4) * 4, (q.green() // 4) * 4, (q.blue() // 4) * 4)
        key = (self.width(), self.height(), self.figure.getRect(), colour.rgb(), round(s * 100), dpr)
        if getattr(self, '_base_key', None) == key:return self._base
        fig = self.figure;w, h = fig.width(), fig.height();cx = fig.center().x() + 0.5;base = fig.bottom() + 1;k = BASE_HEADROOM
        lit = max(0, math.floor(base - 0.45 * h) - 1)      # nothing above the beam's top is lit
        image = QImage(max(1, round(self.width() * dpr)), max(1, round((self.height() - lit) * dpr)), QImage.Format_ARGB32_Premultiplied)
        image.setDevicePixelRatio(dpr);image.fill(Qt.transparent)
        p = QPainter(image);p.setRenderHint(QPainter.Antialiasing);p.translate(0, -lit)
        beam = QPainterPath();top = base - 0.45 * h
        beam.moveTo(cx - 0.16 * w, base);beam.lineTo(cx + 0.16 * w, base);beam.lineTo(cx + 0.46 * w, top);beam.lineTo(cx - 0.46 * w, top);beam.closeSubpath()
        g = QLinearGradient(0, base, 0, top);c0 = QColor(colour);c0.setAlphaF(min(1.0, 0.10 * k));c1 = QColor(colour);c1.setAlphaF(0.0)
        g.setColorAt(0, c0);g.setColorAt(1, c1);p.fillPath(beam, g)
        rx, ry = 0.36 * w, 0.058 * w;centre = QPointF(cx, base - 3)
        glow = QRadialGradient(centre, rx);inner = QColor(colour);inner.setAlphaF(min(1.0, 0.42 * k));outer = QColor(colour);outer.setAlphaF(0.0)
        glow.setColorAt(0, inner);glow.setColorAt(1, outer)
        p.save();p.translate(centre);p.scale(1.0, ry / rx);p.translate(-centre);p.setPen(Qt.NoPen);p.setBrush(glow);p.drawEllipse(centre, rx, rx);p.restore()
        edge = QColor(colour);edge.setAlphaF(min(1.0, 0.55 * k));p.setPen(QPen(edge, 1.5 * s));p.setBrush(Qt.NoBrush);p.drawEllipse(centre, rx, ry)
        p.end();self._base_key, self._base = key, (image, lit)
        return self._base

    def paint_ascii(self, p):
        """The ASCII desk: her figure once, in characters (the mono face, by light and cover), standing on a line in the
        colour of the state of the work. No motion."""
        s = float(getattr(getattr(self.host, 'desk', None), 'scale', 1.0) or 1.0)
        font = QFont(t.MONO);font.setPixelSize(max(7, round(9 * s)));fm = QFontMetricsF(font)
        fig = self.figure;cols = max(4, int(fig.width() / max(1.0, fm.horizontalAdvance('M'))));rows = max(4, int(fig.height() / max(1.0, fm.height())))
        if self._ascii is None or self._ascii[0] != (cols, rows):
            from .kasandra_art import cutout
            small = cutout(self.path).scaled(cols, rows, Qt.IgnoreAspectRatio, Qt.SmoothTransformation).convertToFormat(QImage.Format_ARGB32)
            ramp = ' .:-=+*#%@'
            lines = []
            for y in range(rows):
                line = ''
                for x in range(cols):
                    c = small.pixelColor(x, y);value = c.lightnessF() * c.alphaF()
                    line += ramp[min(len(ramp) - 1, int(value * len(ramp)))]
                lines.append(line)
            self._ascii = ((cols, rows), lines)
        ink = QColor(t.VIOLET_PALE);ink.setAlphaF(0.8);p.setPen(ink);p.setFont(font)
        for row, line in enumerate(self._ascii[1]):p.drawText(QPointF(fig.x(), fig.y() + fm.ascent() + row * fm.height()), line)
        p.setPen(QPen(self.base_colour(), max(1.0, 1.5 * s)));p.drawLine(QPointF(fig.x(), fig.bottom() + 4), QPointF(fig.right(), fig.bottom() + 4))

    def showEvent(self, event):super().showEvent(event);self.wake_or_sleep()

    def hideEvent(self, event):super().hideEvent(event);self._timer.stop()


class _Watch(QObject):
    """The pointer over the tree and the foot (she takes no clicks, so she is told where it is), and the window's state."""

    def __init__(self, stage):
        super().__init__(stage);self.stage = stage

    def eventFilter(self, watched, event):
        kind = event.type()
        if kind == QEvent.MouseMove and isinstance(watched, QWidget):
            try:self.stage.touch(watched.mapTo(self.stage.pane, event.position().toPoint()))
            except RuntimeError:  # noqa: PERF203 - a widget on its way out
                pass
        elif kind in (QEvent.WindowStateChange, QEvent.ActivationChange):
            QTimer.singleShot(0, self.stage.wake_or_sleep)
        return False


def install(host):
    """host.hologram: her stage in the left pane, in Kasandra only and only when the picture's bytes are the owner's
    (kasandra_art.mark); else None, and the left pane is as it was."""
    host.hologram = None
    if t.APPEARANCE != 'kasandra':return None
    pane = getattr(host, 'left_pane', None)
    if pane is None:return None
    from . import kasandra_art
    path = kasandra_art.mark(kasandra_art.folder(host.root), 'hologram.webp')
    if path is None:return None
    if kasandra_art.cutout(path).isNull():return None      # its bytes are hers but it will not decode here (no WebP reader)
    stage = HologramStage(host, pane, path);host.hologram = stage
    for tree in (getattr(host, 'desk_trees', None) or [])[:3]:
        tree.itemExpanded.connect(stage.place_now);tree.itemCollapsed.connect(stage.place_now)
        model = tree.model()
        for signal in (model.rowsInserted, model.rowsRemoved, model.modelReset, model.layoutChanged):signal.connect(stage.place_now)
        tree.verticalScrollBar().rangeChanged.connect(stage.place_now)
    nav = getattr(host, 'settings_navigator', None)
    if nav is not None:nav.stack.currentChanged.connect(stage.place_now)
    watch = _Watch(stage);stage._watcher = watch
    for tree in (getattr(host, 'desk_trees', None) or [])[:2]:
        tree.viewport().setMouseTracking(True);tree.viewport().installEventFilter(watch)
    pane.foot.setMouseTracking(True);pane.foot.installEventFilter(watch)
    host.installEventFilter(watch)
    QGuiApplication.instance().applicationStateChanged.connect(stage.wake_or_sleep)
    return stage


def place(host):
    stage = getattr(host, 'hologram', None)
    if stage is not None:stage.place_now()
