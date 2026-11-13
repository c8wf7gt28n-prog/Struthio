"""The equalizer in the head of the window: this computer at work, as bars that rise and fall.

The owner, 13 November 2026, of the head's middle (where the name and address of what is open stood): "Let's just leave
it out in the middle. Free up the space ... an equalizer, and make its style pulse up and down to represent something."

What it represents is true, not ornament: each bar is one of this computer's processor threads, and its height is how
hard that thread worked over the last second (from /proc/stat, two readings a second apart). When Stacy thinks, when a
calculation runs, when anything at all is at work, the bars rise; at rest they lie low. While Graphite itself has work
running, the bottom row is amber. A small mark above each bar holds its recent peak and sinks slowly, as on any
equalizer.

It moves only when the readings move: a bar glides to its new height in a few steps and stops, and with "reduce motion"
it changes at once. On a computer whose /proc/stat cannot be read it draws its rest and says so in its tip.
"""
from PySide6.QtCore import QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QSizePolicy, QWidget

from . import boss_theme as t

MOST = 16            # bars drawn; a computer with more threads shows them in equal groups
ROWS = 7             # lamps in a bar
EVERY = 1000         # milliseconds between readings
STEP = 40            # milliseconds between frames while a bar glides


def readings(path='/proc/stat'):
    """{thread number: (idle jiffies, all jiffies)} as the kernel counts them now; {} where it cannot be read."""
    out = {}
    try:
        with open(path) as stream:
            for line in stream:
                if not line.startswith('cpu') or line[3:4] in (' ', ''):continue
                parts = line.split()
                if not parts[0][3:].isdigit():continue
                counts = [int(n) for n in parts[1:9]]
                out[int(parts[0][3:])] = (counts[3] + (counts[4] if len(counts) > 4 else 0), sum(counts))
    except (OSError, ValueError, IndexError):
        return {}
    return out


def loads(before, now):
    """How hard each thread worked between two readings, 0 to 1, in thread order."""
    out = []
    for thread in sorted(now):
        if thread not in before:
            out.append(0.0);continue
        idle = now[thread][0] - before[thread][0];whole = now[thread][1] - before[thread][1]
        out.append(max(0.0, min(1.0, 1.0 - idle / whole)) if whole > 0 else 0.0)
    return out


def grouped(values, most=MOST):
    """At most `most` bars: with more threads than that, neighbours are averaged in equal groups."""
    if len(values) <= most:return list(values)
    size = -(-len(values) // most)
    return [sum(values[i:i + size]) / len(values[i:i + size]) for i in range(0, len(values), size)]


class Equalizer(QWidget):
    def __init__(self, host):
        super().__init__(host)
        self.host = host;self.setObjectName('HeadEqualizer');self.setAccessibleName('This computer at work')
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed);self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.before = readings();self.target = grouped([0.0] * max(1, len(self.before)));self.shown = list(self.target);self.peak = list(self.target)
        self.busy = False;self.still = None;self.readable = bool(self.before)
        self.clock = QTimer(self);self.clock.setInterval(EVERY);self.clock.timeout.connect(self.read)
        self.glide = QTimer(self);self.glide.setInterval(STEP);self.glide.timeout.connect(self.move)
        self.setToolTip('This computer at work: each bar is one processor thread over the last second. Amber along the bottom while Graphite itself is working.'
                        if self.readable else 'This computer\'s processor readings cannot be read here.')

    def sizeHint(self):
        return QSize(max(96, len(self.target) * 9 + 3), 40)      # a computer with few threads has wider bars, not a narrower equalizer

    def showEvent(self, event):
        super().showEvent(event)
        if self.readable and not self.clock.isActive():self.clock.start()

    def hideEvent(self, event):
        super().hideEvent(event);self.clock.stop();self.glide.stop()

    def calm(self):
        try:return bool(self.still()) if callable(self.still) else False
        except Exception:  # noqa: BLE001 - how it moves is never worth an error
            return True

    def read(self):
        if getattr(self.host, '_closing', False):return
        now = readings()
        if not now:return
        fresh = grouped(loads(self.before, now));self.before = now
        if len(fresh) != len(self.target):
            self.shown = list(fresh);self.peak = list(fresh);self.updateGeometry()
        self.target = fresh
        if self.calm():
            self.shown = list(fresh);self.peak = list(fresh);self.update()
        elif not self.glide.isActive():self.glide.start()

    def move(self):
        settled = True
        for i, goal in enumerate(self.target):
            gap = goal - self.shown[i]
            if abs(gap) > 0.01:
                self.shown[i] += gap * 0.38;settled = False
            else:self.shown[i] = goal
            if self.shown[i] >= self.peak[i]:self.peak[i] = self.shown[i]
            elif self.peak[i] - self.shown[i] > 0.01:
                self.peak[i] = max(self.shown[i], self.peak[i] - 0.035);settled = False
        if settled:self.glide.stop()
        self.update()

    def paintEvent(self, event):
        p = QPainter(self);n = len(self.shown)
        if not n:
            p.end();return
        try:
            from .boss_qt import glows
            level = t.glow() if glows(self.host) else 0.0
        except Exception:  # noqa: BLE001 - it is drawn whatever else is the matter
            level = 0.0
        wide = max(3.0, (self.width() - 3.0) / n - 3.0);tall = max(2.0, (self.height() - 8.0 - (ROWS - 1) * 2.0) / ROWS);foot = self.height() - 4.0
        for i, value in enumerate(self.shown):
            x = 1.5 + i * (wide + 3.0);lit = 0 if value < 0.02 else max(1, round(value * ROWS))
            for row in range(ROWS):
                y = foot - (row + 1) * tall - row * 2.0;box = QRectF(x, y, wide, tall)
                if row < lit:
                    colour = QColor(t.AMBER_EDGE if row >= ROWS - 2 else t.READY)       # the top of a bar is amber: a thread near its limit
                    if level > 0:
                        halo = QColor(colour);halo.setAlphaF(min(0.34, 0.085 * level));p.fillRect(box.adjusted(-2.0, -1.5, 2.0, 1.5), halo)
                    p.fillRect(box, colour)
                else:
                    rest = QColor(t.AMBER_EDGE if self.busy and row == 0 else t.TEAL_EDGE);rest.setAlphaF(0.75 if self.busy and row == 0 else 0.22)
                    p.fillRect(box, rest)
            high = round(self.peak[i] * ROWS)
            if high > lit and high > 0:                                                  # the peak it reached a moment ago, sinking
                y = foot - high * tall - (high - 1) * 2.0;mark = QColor(t.TEAL_TEXT);mark.setAlphaF(0.8);p.fillRect(QRectF(x, y, wide, 1.5), mark)
        p.end()
