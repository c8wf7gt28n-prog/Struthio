"""Graphite 1.1 N1 · the phosphor Night's CRT effects: "Screen burns and all the fun" (the owner, 28 Nov 2026).

One setting, View ▸ Appearance ▸ CRT effects: Off, Subtle (the default) or Full (night_phosphor keeps it). Only in Night.
None of it costs a word its legibility, and Reduce motion stills everything that moves:

  burn-in      a static ghost of old screens (a READY. prompt, the Graphite mark, an old bar's layout) burnt into the
               ground of the window and of the bar, 3 % (Subtle) or 5 % (Full) of the phosphor over a panel's ground. It is laid with the
               Lighten mode, so it only lifts what is darker than it: it lies under every word and picture, never on them.
  afterglow    a line edit's glyphs and its cursor fade out over AFTERGLOW_MS when they change or move (persistence),
               laid with Lighten, so only where nothing is now lit. It moves, so Reduce motion stills it.
  warm-up      once, when the window first shows in Night: a horizontal line opens into the screen over WARM_MS. It moves.
  scanlines    very faint horizontal lines, 2 % (Subtle) or 3 % (Full) of black every third pixel row, and in Full a soft
               corner vignette of at most VIGNETTE_MAX (6 %) at the very corner. Measured: the faintest words (tertiary)
               stay 4.5:1 or more under both (tests_integrated/test_night_phosphor.py).
  cursor       a block cursor in the line edits and the bar's line (inverse video: the block of the phosphor, the glyph
               under it in the ground), blinking every BLINK_MS; steady under Reduce motion. In Full a faint bloom (a
               soft phosphor halo, no blur over the words themselves) on the head's menu words, the brightest text.

The drop-down xterm is a window of its own (xterm): only its colours follow the phosphor (real_terminal_qt).
Nothing here reads or changes anything outside the window's own painting.
"""
from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QPoint, QPointF, QRect, QRectF, Qt, QTimer, QVariantAnimation
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPixmap, QRadialGradient, QRegion
from PySide6.QtWidgets import QApplication, QGraphicsDropShadowEffect, QLineEdit, QWidget

from . import boss_theme as bt
from . import design_tokens as tokens

AFTERGLOW_MS = 160
WARM_MS = 400
BLINK_MS = 530
VIGNETTE_MAX = 16            # out of 255 at the very corner (6 %), Full only
BURN = dict(off=0, subtle=8, full=13)            # the ghost: share of the phosphor out of 255 (3 %, 5 %)
SCAN = dict(off=0, subtle=5, full=8)             # the scanlines: black out of 255 (2 %, 3 %)
MOVING = ('afterglow', 'warm_up', 'blink')


def effects(level, reduce_motion=False, night=True):
    """What is drawn, for a level ('off', 'subtle', 'full'), Reduce motion and whether Night is in force: a dict of each
    effect's strength (0 or False when it is off). The one place the switches are decided."""
    level = level if level in BURN else 'subtle'
    on = bool(night) and level != 'off';full = on and level == 'full'
    moves = on and not reduce_motion
    return dict(burn_in=BURN[level] if on else 0, scanlines=SCAN[level] if on else 0, vignette=VIGNETTE_MAX if full else 0,
                afterglow=AFTERGLOW_MS if moves else 0, warm_up=WARM_MS if moves else 0, block_cursor=on,
                blink=BLINK_MS if moves else 0, bloom=full)


def reduce_motion(host):
    try:
        from .document_qt import profile_of
        return bool(profile_of(host).get('reduce_motion'))
    except Exception:  # noqa: BLE001 - motion is a grace, never a reason to fail
        return False


def level_of(host):
    try:
        from .night_phosphor import CRT_KEY, crt_value
        return crt_value(host.session.state.get(CRT_KEY)) or bt.CRT
    except Exception:  # noqa: BLE001
        return bt.CRT


def now(host):
    return effects(level_of(host), reduce_motion(host), bool(getattr(bt, 'PHOSPHOR', '')))


# ---- the screen: burn-in, scanlines, vignette, warm-up --------------------------------------------------------------------------
class Screen(QWidget):
    """A sheet over a window that takes no press and no focus: the ghost (Lighten), the scanlines, the vignette, the warm-up."""

    def __init__(self, window, ghost='window', fx=None):
        super().__init__(window);self.window_ = window;self.ghost = ghost;self.fx = dict(fx or effects('off'))
        self.setObjectName('CrtScreen');self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True);self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFocusPolicy(Qt.NoFocus);self._burnt = None;self._vignette = None;self.warmth = 1.0;self.warming = None
        c = tokens.colours('night');self.phosphor = QColor(c['text']);self.ground = QColor(c['surface'])      # the ghost lies over a panel's ground
        window.installEventFilter(self);self.setGeometry(window.rect());self.raise_()
        self.setVisible(self.drawn())

    def drawn(self):
        f = self.fx;return bool(f['burn_in'] or f['scanlines'] or f['vignette'] or self.warming is not None)

    def set_effects(self, fx):
        self.fx = dict(fx);self._burnt = self._vignette = None;self.setVisible(self.drawn());self.update()

    def eventFilter(self, watched, event):
        if watched is self.window_ and event.type() == QEvent.Resize:
            self.setGeometry(self.window_.rect());self._burnt = self._vignette = None;self.raise_()
        elif watched is self.window_ and event.type() == QEvent.ChildAdded:
            QTimer.singleShot(0, self._top)
        return False

    def _top(self):
        try:
            if self.isVisible():self.raise_()
        except RuntimeError:
            pass

    # the ghost, made once per size
    def burnt(self):
        if self._burnt is not None or not self.fx['burn_in']:return self._burnt
        w, h = max(1, self.width()), max(1, self.height());pix = QPixmap(w, h);pix.fill(Qt.black)
        ghost = QColor(self.ground);a = self.fx['burn_in']
        ghost.setRgb(*(min(255, (a * p + (255 - a) * g + 127) // 255) for p, g in
                       zip(self.phosphor.getRgb()[:3], self.ground.getRgb()[:3])))
        p = QPainter(pix);p.setRenderHint(QPainter.Antialiasing);p.setPen(ghost);p.setBrush(Qt.NoBrush)
        mono = QFont(tokens.FONT['mono'])
        if self.ghost == 'bar':      # an old bar's layout: a START plate, four window plates, a clock
            unit = max(8, h // 4);p.setBrush(ghost);p.setPen(Qt.NoPen)
            p.drawRect(QRectF(unit, unit, unit * 5, h - 2 * unit))
            for n in range(4):p.drawRect(QRectF(unit * (8 + n * 13), unit * 1.4, unit * 11, h - 2.8 * unit))
            p.drawRect(QRectF(w - unit * 9, unit, unit * 7, h - 2 * unit))
        else:      # READY. at the top left, the Graphite mark large in the middle, a prompt under it
            mono.setPixelSize(max(14, h // 40));p.setFont(mono)
            p.drawText(QRectF(w * 0.03, h * 0.08, w * 0.5, h * 0.05), Qt.AlignLeft | Qt.AlignVCenter, 'READY.')
            big = QFont(mono);big.setPixelSize(max(28, h // 9));big.setBold(True);p.setFont(big)
            p.drawText(QRectF(0, h * 0.36, w, h * 0.2), Qt.AlignCenter, 'GRAPHITE')
            p.setFont(mono);p.drawText(QRectF(w * 0.03, h * 0.84, w * 0.6, h * 0.05), Qt.AlignLeft | Qt.AlignVCenter, 'C:\\> _')
        p.end();self._burnt = pix
        return pix

    def vignette(self):
        if self._vignette is not None or not self.fx['vignette']:return self._vignette
        w, h = max(1, self.width()), max(1, self.height());pix = QPixmap(w, h);pix.fill(Qt.transparent)
        p = QPainter(pix);g = QRadialGradient(QPointF(w / 2, h / 2), (w * w + h * h) ** 0.5 / 2)
        g.setColorAt(0.0, QColor(0, 0, 0, 0));g.setColorAt(0.72, QColor(0, 0, 0, 0));g.setColorAt(1.0, QColor(0, 0, 0, self.fx['vignette']))
        p.fillRect(pix.rect(), QBrush(g));p.end();self._vignette = pix
        return pix

    def paintEvent(self, event):
        p = QPainter(self);area = event.rect()
        burnt = self.burnt()
        if burnt is not None:
            p.setCompositionMode(QPainter.CompositionMode_Lighten);p.drawPixmap(area, burnt, area)
            p.setCompositionMode(QPainter.CompositionMode_SourceOver)
        if self.fx['scanlines']:
            tile = QPixmap(4, 3);tile.fill(Qt.transparent);t = QPainter(tile);t.fillRect(0, 2, 4, 1, QColor(0, 0, 0, self.fx['scanlines']));t.end()
            p.fillRect(area, QBrush(tile))
        vignette = self.vignette()
        if vignette is not None:p.drawPixmap(area, vignette, area)
        if self.warming is not None:      # the warm-up: dark, with a line that opens from the middle
            h = self.height();open_ = self.warmth * h;top = (h - open_) / 2
            p.fillRect(QRectF(0, 0, self.width(), top), Qt.black);p.fillRect(QRectF(0, top + open_, self.width(), h), Qt.black)
            line = QColor(self.phosphor);line.setAlpha(round(255 * (1.0 - self.warmth)))
            p.fillRect(QRectF(0, top - 1, self.width(), 2), line);p.fillRect(QRectF(0, top + open_ - 1, self.width(), 2), line)
        p.end()

    def warm_up(self):
        """Once: the line opens into the screen over the effect's warm-up time. Nothing when it is off (Off, Reduce motion)."""
        ms = self.fx['warm_up']
        if not ms:return False
        self.warming = QVariantAnimation(self);self.warming.setStartValue(0.0);self.warming.setEndValue(1.0);self.warming.setDuration(ms)
        self.warming.valueChanged.connect(self._warm);self.warming.finished.connect(self._warm_done)
        self.warmth = 0.0;self.setVisible(True);self.raise_();self.warming.start()
        return True

    def _warm(self, value):
        self.warmth = float(value);self.update()

    def _warm_done(self):
        self.warming = None;self.warmth = 1.0;self.setVisible(self.drawn());self.update()


# ---- the line: block cursor, afterglow --------------------------------------------------------------------------------------------
class Persistence(QWidget):
    """Over one line edit: its block cursor (inverse video: Difference with the phosphor) blinking, and the afterglow of what
    was there before a change or a move (the line as it was, laid with Lighten and fading)."""

    def __init__(self, edit, fx):
        super().__init__(edit);self.edit = edit;self.fx = dict(fx);self.setObjectName('CrtPersistence')
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True);self.setFocusPolicy(Qt.NoFocus)
        self.phosphor = QColor(tokens.colours('night')['text']);self.lit = True;self.ghost = None;self.fade = 0.0
        self.old_cursor = None;self.before = None
        self.blink = QTimer(self);self.blink.timeout.connect(self._blink)
        if self.fx['blink']:self.blink.start(self.fx['blink'])
        self.glow = QVariantAnimation(self);self.glow.setStartValue(1.0);self.glow.setEndValue(0.0)
        self.glow.setDuration(max(1, self.fx['afterglow']));self.glow.valueChanged.connect(self._fade)
        edit.textChanged.connect(self._changed);edit.cursorPositionChanged.connect(self._moved)
        edit.installEventFilter(self);self.setGeometry(edit.rect());self.raise_();self.show();self._keep()

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Resize:self.setGeometry(self.edit.rect());QTimer.singleShot(0, self._keep)
        elif event.type() in (QEvent.FocusIn, QEvent.FocusOut):self.lit = True;self.update()
        return False

    def cursor_rect(self):
        r = self.edit.inputMethodQuery(Qt.ImCursorRectangle)
        r = r.toRect() if hasattr(r, 'toRect') else QRect(r)
        cell = max(6, self.edit.fontMetrics().horizontalAdvance('M'))
        return QRect(r.left(), r.top(), cell, max(r.height(), 8))

    def _keep(self):
        """The line as it is now (without this sheet), for the afterglow of the next change."""
        if not self.fx['afterglow']:return
        try:
            pix = QPixmap(self.edit.size());pix.fill(Qt.transparent)
            self.edit.render(pix, QPoint(), QRegion(), QWidget.RenderFlag.DrawWindowBackground);self.before = pix
        except RuntimeError:
            pass

    def _changed(self, *_):
        if self.fx['afterglow'] and self.before is not None:
            self.ghost = self.before;self.glow.stop();self.glow.start()
        QTimer.singleShot(0, self._keep)

    def _moved(self, old, new):
        if self.fx['afterglow'] and self.edit.hasFocus():
            self.old_cursor = self.cursor_rect().translated(-(new - old) * max(6, self.edit.fontMetrics().horizontalAdvance('M')), 0)
            if self.ghost is None:self.glow.stop();self.glow.start()
        self.lit = True;self.update()

    def _fade(self, value):
        self.fade = float(value)
        if self.fade <= 0.0:self.ghost = None;self.old_cursor = None
        self.update()

    def _blink(self):
        if self.edit.hasFocus():self.lit = not self.lit;self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        if self.ghost is not None and self.fade > 0.0:      # what was there, glowing out where nothing is lit now
            p.setCompositionMode(QPainter.CompositionMode_Lighten);p.setOpacity(0.55 * self.fade);p.drawPixmap(0, 0, self.ghost)
            p.setOpacity(1.0)
        if self.old_cursor is not None and self.fade > 0.0:
            p.setCompositionMode(QPainter.CompositionMode_Lighten);c = QColor(self.phosphor);c.setAlpha(round(110 * self.fade))
            p.fillRect(self.old_cursor, c)
        if self.edit.hasFocus() and self.lit and self.fx['block_cursor']:      # the block: inverse video over the glyph under it
            p.setCompositionMode(QPainter.CompositionMode_Difference);p.fillRect(self.cursor_rect(), self.phosphor)
        p.end()


# ---- the window: where it all is put ----------------------------------------------------------------------------------------------
class _Lines(QObject):
    """Gives each line edit that takes the focus its Persistence, once."""

    def __init__(self, host, fx):
        super().__init__(host);self.host = host;self.fx = fx

    def eventFilter(self, watched, event):
        if event.type() == QEvent.FocusIn and isinstance(watched, QLineEdit) and self.fx['block_cursor']:
            if watched.findChild(Persistence, options=Qt.FindDirectChildrenOnly) is None:Persistence(watched, self.fx)
        return False


def install(host):
    """Called once the window is built (launch_look.install): in Night only, the screen over the window, the bar's when it
    stands, the lines' cursor and afterglow, the bloom, and the warm-up once. Returns the effects in force."""
    host.crt_screen = None;host.crt_bar_screen = None;host.crt_fx = fx = now(host)
    if not getattr(bt, 'PHOSPHOR', ''):return fx
    if any(fx[k] for k in ('burn_in', 'scanlines', 'vignette', 'warm_up')):
        host.crt_screen = Screen(host, 'window', fx)
        QTimer.singleShot(0, host.crt_screen.warm_up)
    if fx['block_cursor']:
        host.crt_lines = _Lines(host, fx);app = QApplication.instance()
        if app is not None:app.installEventFilter(host.crt_lines)
    for wait in (0, 1500, 4000):QTimer.singleShot(wait, lambda: attach_bar(host))
    if fx['bloom']:QTimer.singleShot(0, lambda: bloom(host))
    return fx


def attach_bar(host):
    bar = getattr(host, 'graphite_bar', None);fx = getattr(host, 'crt_fx', None)
    if bar is None or not fx or getattr(host, 'crt_bar_screen', None) is not None:return None
    if not (fx['burn_in'] or fx['scanlines']):return None
    try:
        quiet = dict(fx, vignette=0, warm_up=0);host.crt_bar_screen = Screen(bar, 'bar', quiet)
    except RuntimeError:
        return None
    return host.crt_bar_screen


def bloom(host):
    """Full: a faint phosphor halo on the head's menu words (no blur on the words: a halo laid under them)."""
    top = getattr(getattr(host, 'shell2', None), 'top', None)
    words = list(getattr(top, 'bar_menus', []) or []) + list(getattr(host, 'bar_menus', []) or [])
    for widget in words:
        try:
            halo = QGraphicsDropShadowEffect(widget);halo.setOffset(0, 0);halo.setBlurRadius(10)
            c = QColor(tokens.colours('night')['text']);c.setAlpha(90);halo.setColor(c);widget.setGraphicsEffect(halo)
        except RuntimeError:
            pass
    return len(words)


def set_level(host, level):
    """The menu's choice, put in force at once where it can be (the screen and the bar's); the rest from the next start."""
    fx = effects(level, reduce_motion(host), bool(getattr(bt, 'PHOSPHOR', '')))
    for screen in (getattr(host, 'crt_screen', None), getattr(host, 'crt_bar_screen', None)):
        if screen is not None:
            try:screen.set_effects(dict(fx, warm_up=0))
            except RuntimeError:
                pass
    if getattr(host, 'crt_screen', None) is None and getattr(bt, 'PHOSPHOR', '') and (fx['burn_in'] or fx['scanlines']):
        host.crt_screen = Screen(host, 'window', dict(fx, warm_up=0))
    host.crt_fx = fx
    return fx
