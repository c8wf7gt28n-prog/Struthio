"""Kas 1.1 HX · the hero extras of Night (Night: Duo above all, the owner's hero look).

  clock     the bar's time in seven-segment digits, HH:MM as seven bars each like an old LED desk clock (crt_qt's
            Screen.seven_segment draws them), in her phosphor (amber in Duo and Amber; Green's and Paper's own, one hue there),
            over the faint unlit bars of 88:88; the date stays small under it in the chrome's mono face. Only in Night:
            Day, Pencil and Indigo keep their clock as it is. The clock's accessible name says the time in words.
  type-out  a new line of hers in her panel is run out by a block cursor in her phosphor, TYPE_CPS characters a second and
            never longer than TYPE_MAX_MS for the whole line, the characters just lit glowing behind it for crt_qt's
            AFTERGLOW_MS; a click shows it at once. Instant under Reduce motion, with CRT effects Off and outside Night
            (crt_qt.effects: no afterglow). Never for what waits for the owner's press: a card (a line with a button) is
            shown whole, at once.
  peak      a meter's peak mark: it holds the highest value of the last PEAK_HOLD_S seconds, then falls PEAK_FALL a second.

Nothing here reads or changes anything but the window's own painting.
"""
from __future__ import annotations

import html
import math
import time

from PySide6.QtCore import QEvent, QObject, QRectF, Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QAbstractButton

from . import boss_theme as bt
from . import design_tokens as tokens

TYPE_CPS = 600
TYPE_MAX_MS = 800
TYPE_TICK_MS = 16
UNLIT = 26                    # out of 255: the clock's unlit bars, her phosphor over the bar's ground
GLOW = (40, 22, 10)           # out of 255: the afterglow behind the cursor, youngest first (thirds of AFTERGLOW_MS)
PEAK_HOLD_S = 2.5
PEAK_FALL = 0.25              # of the whole scale, a second


def night():
    return bool(getattr(bt, 'PHOSPHOR', ''))


# ---- the clock --------------------------------------------------------------------------------------------------------------------
def clock_width(h):
    """The width the seven-segment HH:MM takes on a bar `h` high."""
    hh = _digit_height(h)
    return round(4.5 * 0.76 * hh) + 2


def _digit_height(h):
    return max(10.0, round(h * 0.40))


def paint_clock(p, area, c, text):
    """HH:MM in seven bars a digit, centred low in `area` (the top half of the clock), over the faint unlit 88:88."""
    from .crt_qt import Screen
    hh = min(_digit_height(area.height() * 2), area.height() - 1);cw = 0.76 * hh;width = (len(text) - 0.5) * cw
    box = QRectF(area.center().x() - width / 2, area.bottom() - hh, width, hh)
    Screen.seven_segment(p, QColor(tokens.over(c['kas_text'], c['window'], UNLIT)), ''.join('8' if ch.isdigit() else ch for ch in text), box)
    Screen.seven_segment(p, QColor(c['kas_text']), text, box)
    return box


# ---- her words type out ----------------------------------------------------------------------------------------------------------
def typing_on(host):
    """Whether her new lines type out: Night with CRT effects on and no Reduce motion (the afterglow is in force)."""
    if not night():return False
    fx = getattr(host, 'crt_fx', None)
    if not fx:
        from . import crt_qt
        fx = crt_qt.now(host)
    return bool(fx.get('afterglow'))


def type_ms(n):
    """How long a line of `n` characters takes: TYPE_CPS a second, never longer than TYPE_MAX_MS."""
    return min(n * 1000.0 / TYPE_CPS, float(TYPE_MAX_MS)) if n > 0 else 0.0


def shown_at(n, ms):
    """How many of `n` characters stand after `ms` milliseconds."""
    whole = type_ms(n)
    return n if ms >= whole or whole <= 0 else max(0, min(n, int(math.ceil(n * ms / whole))))


def is_card(bubble):
    """A line that waits for the owner's press: it carries a button, or more than its words."""
    box = getattr(bubble, 'box', None)
    return bool(bubble.findChildren(QAbstractButton)) or (box is not None and box.count() > 1)


class TypeOut(QObject):
    """Runs one bubble's words out behind a block cursor; a click, a card or the end shows them whole."""

    def __init__(self, face, bubble, c=None):
        super().__init__(bubble);self.face, self.bubble, self.label = face, bubble, bubble.text
        self.c = c or tokens.colours('night');self.full = self.label.text();self.format = self.label.textFormat()
        self.n = len(self.full);self.began = time.monotonic();self.lit = [];self.done = False
        self.timer = QTimer(self);self.timer.setInterval(TYPE_TICK_MS);self.timer.timeout.connect(self.tick)
        for w in (self.label, self.bubble):w.installEventFilter(self)
        self.label.setTextFormat(Qt.RichText);self.show(0, 0.0);self.timer.start()

    def eventFilter(self, watched, event):
        if event.type() == QEvent.MouseButtonPress and not self.done:self.finish()
        return False

    def tick(self):
        try:
            if self.done:return
            if is_card(self.bubble):return self.finish()
            ms = (time.monotonic() - self.began) * 1000.0;k = shown_at(self.n, ms)
            if k >= self.n:return self.finish()
            self.reserve();self.show(k, ms);self.follow()
        except RuntimeError:      # the bubble went
            self.timer.stop()

    def reserve(self):
        """The whole line's height, from the first tick its width is known: nothing below it moves as it types."""
        if getattr(self, 'held', False) or self.label.width() < 24:return
        from PySide6.QtCore import QRect
        from PySide6.QtGui import QFontMetrics
        tall = QFontMetrics(self.label.font()).boundingRect(QRect(0, 0, self.label.width(), 100000), Qt.TextWordWrap, self.full).height()
        self.label.setMinimumHeight(tall + 4);self.held = True

    def follow(self):
        """Her thread stays at its end, where the cursor is."""
        scroll = getattr(self.face, 'scroll', None)
        if scroll is not None:
            bar = scroll.verticalScrollBar();bar.setValue(bar.maximum())

    def show(self, k, ms):
        from .crt_qt import AFTERGLOW_MS
        while len(self.lit) < k:self.lit.append(ms)      # when each character was lit
        ground = self.c['kas_ground'];ink = self.c['kas_text'];parts = []
        start = 0
        for i in range(k):
            age = ms - self.lit[i]
            band = int(age * 3 // max(1, AFTERGLOW_MS)) if age < AFTERGLOW_MS else 3
            if i == 0 or band != prev:
                if i:parts.append((start, i, prev))
                start, prev = i, band
        if k:parts.append((start, k, prev))
        out = []
        for a, b, band in parts:
            words = html.escape(self.full[a:b]).replace('\n', '<br>')
            out.append('<span style="background:%s">%s</span>' % (tokens.over(ink, ground, GLOW[band]), words) if band < 3 else words)
        cursor = '<span style="background:%s;color:%s">&nbsp;</span>' % (ink, self.c['on_accent'])
        self.label.setText('<span style="white-space:pre-wrap">%s%s</span>' % (''.join(out), cursor))

    def finish(self):
        self.done = True;self.timer.stop()
        try:
            for w in (self.label, self.bubble):w.removeEventFilter(self)
            self.label.setTextFormat(self.format);self.label.setText(self.full);self.label.setMinimumHeight(0)
            fold = getattr(self.face, 'fold_earlier', None)
            if fold is not None:QTimer.singleShot(0, fold)
            QTimer.singleShot(30, self.face, self.follow) if isinstance(self.face, QObject) else None
        except RuntimeError:
            pass
        return True


# ---- peak marks ------------------------------------------------------------------------------------------------------------------
class Peak:
    """A peak mark: it holds the highest value of the last PEAK_HOLD_S seconds, then falls PEAK_FALL a second, never under
    the value now."""

    def __init__(self):
        self.value = 0.0;self.at = None;self.last = None

    def feed(self, value, now=None):
        """The value now; returns True while the mark stands above it (held or falling)."""
        now = time.monotonic() if now is None else now;v = max(0.0, float(value or 0.0))
        if self.at is None or v >= self.value:
            self.value, self.at = v, now
        elif now - self.at >= PEAK_HOLD_S:
            since = max(self.last if self.last is not None else now, self.at + PEAK_HOLD_S)
            self.value = max(v, self.value - PEAK_FALL * max(0.0, now - since))
        self.last = now
        return self.value > v


def peaks_for(owner, n):
    """`owner`'s n peak marks (kept on it), made afresh when their number changes."""
    marks = getattr(owner, 'hx_peaks', None)
    if marks is None or len(marks) != n:marks = owner.hx_peaks = [Peak() for _ in range(n)]
    return marks


def paint_meter_peak(p, meter, c, value, left, right, y):
    """Under a Night meter's words: a slim bar of its reading in the computer's green and the amber peak mark (Duo)."""
    from .neon_meters import NEAR
    if value is None or right - left < 8:return None
    mark = peaks_for(meter, 1)[0];mark.feed(value);span = right - left
    p.save();p.setPen(Qt.NoPen)
    p.setBrush(c['rest']);p.drawRect(QRectF(left, y, span, 2))
    p.setBrush(c['hot'] if value >= NEAR else c['mid']);p.drawRect(QRectF(left, y, max(1.0, span * value), 2))
    x = left + span * mark.value;p.setBrush(c['peak']);p.drawRect(QRectF(min(right - 2, max(left, x - 1)), y - 2, 2, 6))
    p.restore()
    return mark.value


def type_out(face, bubble):
    """SlateFace.say's: her new line types out when typing_on; returns the TypeOut, or None (shown whole at once)."""
    try:
        if bubble.mine or bubble.code or not typing_on(getattr(face, 'host', None)) or is_card(bubble):return None
        if not bubble.text.text():return None
        bubble.type_out = TypeOut(face, bubble)
        return bubble.type_out
    except Exception:  # noqa: BLE001 - her words are shown whole rather than not at all
        return None
