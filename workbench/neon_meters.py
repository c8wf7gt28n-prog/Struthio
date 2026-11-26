"""The neon of the head's equalizer and of the foot's four meters (0.8.6).

The owner, 20 November 2026, of the equalizer upper left: "Now just work the upper left equalizer to be radical"; of the four
meters lower right: "Work the bottom right 4 display a lot more kewl like that". From the styles drawn for him, the defaults
taken: the equalizer in style D, neon tubes over a scope (equalizer_qt), and the meters in style H, a ring with a minute of
history (RingMeter, here).

One palette for both, in each look's own colours (palette):

  low, mid, high   a height's colour rises with it: the look's deep colour, its middle, its bright one (Kasandra violet to
                   cyan, Graphite its greens)
  hot              NEAR (0.8) or more: near its limit, amber (Kasandra's burnt yellow, Graphite's orange); it is also said
                   in words, on the equalizer's card and in a meter's tip, so the colour is never the only sign
  peak             the floating dots and the bright end of a trace
  rest, grid       a bar or ring at rest, the floor and the scales: quiet
  text, label, dim the number, the key word, and what has no reading (dim, with its dash and the words "no reading")

The glow is light: drawn as wider, fainter strokes of the same colour behind the stroke, at the Glow dial's strength, none
on the Clean desk; in Kasandra added as light (boss_theme.lays_light), so her amber is never mixed over her cyan.

RingMeter is one meter: a ring whose arc is the reading (a share, 0 to 100, clockwise from the top), the number inside, the
key word under it, and beside it a small trace of the last minute of readings ending in a bright dot. A meter with no reading
stays honestly dim: an empty ring, its dash, and "no reading" where the trace would be. It is a QLabel, so what reads it
(its text, its tip, its name for readers) is as before, and it is still a door: a click opens its card (desktop_header_qt).
"""
import time
from collections import deque

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QLabel, QSizePolicy

from . import boss_theme as t

NEAR = 0.8          # a height this or more is near its limit: hot, and said in words
MINUTE = 60.0       # seconds of history beside each meter


def mix(a, b, share):
    a, b = QColor(a), QColor(b);share = max(0.0, min(1.0, float(share)))
    return QColor(round(a.red() + (b.red() - a.red()) * share), round(a.green() + (b.green() - a.green()) * share),
                  round(a.blue() + (b.blue() - a.blue()) * share))


_palette = {}


def palette():
    """The colours by role in the look in force (kept: the look is chosen at start)."""
    look = t.APPEARANCE
    if look not in _palette:
        her = look == 'kasandra';ground = QColor(t.GROUND)
        low = QColor(t.VIOLET_DEEP if her else t.TEAL_EDGE);mid = QColor(t.VIOLET if her else t.TEAL)
        high = QColor(t.READY if her else t.TEAL_TEXT)
        _palette[look] = dict(low=low, mid=mid, high=high, hot=QColor(t.AMBER_EDGE), peak=QColor(t.TEAL_TEXT if her else t.TEXT),
                              rest=mix(ground, low, 0.24 if her else 0.16), grid=QColor(t.LINE) if her else mix(ground, low, 0.3),
                              text=QColor(t.TEXT), label=QColor(t.TEAL_TEXT), dim=mix(ground, t.TEXT, 0.42), trace=high)
        if t.LAUNCH:      # 1.0 P2: on light paper, near its limit is the colour of what waits for you (blue is a selection
            # there), and a dash or "no reading" is FAINT, an ink that reads (5.3:1 or more), never a pale mix
            # 1.0 P4: Day and Night: the bars take the accent and the live colours (design_tokens.marks)
            m = t.DAY_MARKS;low = QColor(m['EQ_LOW'])
            _palette[look].update(low=low, mid=QColor(m['EQ_MID']), high=QColor(m['EQ_HIGH']), hot=QColor(m['EQ_HOT']), trace=QColor(m['EQ_MID']),
                                  peak=QColor(t.TEXT), dim=QColor(t.FAINT), label=QColor(t.QUIET), rest=mix(ground, low, 0.28), grid=QColor(t.LINE))
    return _palette[look]


def words_only():
    """1.0 P2: in Day the foot's meters are words and numbers (the owner's picture: CPU 34% | GPU 24% | RAM 62% | TXT 18%)."""
    return t.LAUNCH      # 1.0 P4: Day and Night


SEPARATOR = '|'
HOT_MARK = '▲'      # near its limit: a shape beside the number, as well as its colour and the words in its tip


def ramp(value, colours=None):
    """A height's colour: rising from low through mid to high; NEAR or more is hot."""
    c = colours or palette();v = max(0.0, min(1.0, float(value)))
    if v >= NEAR:return c['hot']
    return mix(c['low'], c['mid'], v / 0.5) if v < 0.5 else mix(c['mid'], c['high'], (v - 0.5) / 0.5)


def glow_level(widget):
    """The Glow dial's strength for this widget's window: none on the Clean desk."""
    try:
        from .boss_qt import glows
        return t.glow() if glows(widget.window()) else 0.0
    except Exception:  # noqa: BLE001 - drawn whatever else is the matter
        return 0.0


def faint(colour, alpha):
    c = QColor(colour);c.setAlphaF(max(0.0, min(1.0, alpha)));return c


class RingMeter(QLabel):
    """One of the four meters at the foot, in style H (see the module's words). Its text is the reading as before ('62%', or
    '—'); push() adds a reading to its minute of history."""

    def __init__(self, key, parent=None):
        super().__init__('—', parent);self.key = key;self.history = deque(maxlen=64);self.glow = False
        self.setObjectName('MonitorReading');self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.number_font = QFont(t.MONO);self.number_font.setPixelSize(12);self.key_font = QFont(t.MONO);self.key_font.setPixelSize(10)
        self.ring = 28;self.trace = 48

    def size_to(self, ring, number_px, key_px):
        """The ring's diameter and the two faces' sizes (the interface size, desktop_header_qt.restyle)."""
        self.ring = int(ring);self.number_font.setPixelSize(int(number_px));self.key_font.setPixelSize(int(key_px))
        self.updateGeometry();self.update()

    def sizeHint(self):
        if words_only():return self.words_size()
        return QSize(self.ring + 6 + self.trace, self.ring + 18)

    def minimumSizeHint(self):
        if words_only():return self.words_size()
        return QSize(self.ring + 4, self.ring + 14)

    def words_font(self):
        f = QFont(t.MONO);f.setPixelSize(max(12, self.number_font.pixelSize() + 1));return f

    def words_size(self):
        """Day: room for the key and the widest reading ('100%' and its mark), on one line."""
        from PySide6.QtGui import QFontMetrics
        fm = QFontMetrics(self.words_font())
        widest = getattr(self, 'reserve', None) or '%s 100%%%s' % (self.key, HOT_MARK)      # 1.0 D1: a meter with no reading source reserves its dash
        return QSize(fm.horizontalAdvance(widest) + 4, max(self.ring, fm.height() + 8))

    def words(self):
        """(key, reading, mark) as Day shows them."""
        v = self.value();hot = v is not None and v >= NEAR
        return self.key + ' ', ('—' if v is None else str(round(v * 100)) + '%'), (HOT_MARK if hot else '')

    def words_span(self):
        """Day: where the words stand in the meter, (left, right) in its own pixels (the separators stand between)."""
        from PySide6.QtGui import QFontMetricsF
        fm = QFontMetricsF(self.words_font());total = fm.horizontalAdvance(''.join(self.words()))
        x = max(0.0, (self.width() - total) / 2.0);return x, x + total

    def paint_words(self, p):
        """Day: 'CPU 34%' in plain words and numbers; '—' with no reading (honest, in FAINT), and near its limit the number
        in the colour of what waits for you with ▲ beside it."""
        c = palette();v = self.value();f = self.words_font();p.setFont(f);fm = p.fontMetrics()
        key, shown, mark = self.words();hot = bool(mark)
        x = self.words_span()[0]
        base = (self.height() + fm.ascent() - fm.descent()) / 2.0
        p.setPen(c['label'] if v is not None else c['dim']);p.drawText(QPointF(x, base), key);x += fm.horizontalAdvance(key)
        p.setPen(c['hot'] if hot else (c['text'] if v is not None else c['dim']));p.drawText(QPointF(x, base), shown + mark)

    def value(self):
        """The reading as a share 0 to 1, or None when there is none."""
        text = self.text().strip().rstrip('%')
        try:return max(0.0, min(1.0, int(text) / 100.0))
        except ValueError:return None

    def push(self, now=None):
        """Keep the reading shown now in the minute of history (a gap where there was none)."""
        now = time.monotonic() if now is None else now
        self.history.append((now, self.value()))
        while self.history and now - self.history[0][0] > MINUTE + 4:self.history.popleft()
        self.update()

    def paintEvent(self, event):
        c = palette();v = self.value();level = glow_level(self) if self.glow else 0.0
        p = QPainter(self);p.setRenderHint(QPainter.Antialiasing)
        if words_only():      # 1.0 P2
            try:self.paint_words(p)
            finally:p.end()
            return
        try:
            key_h = self.key_font.pixelSize() + 3;d = min(float(self.ring), self.height() - key_h - 8.0)
            above = max(2.0, (self.height() - d - 2.0 - key_h) / 2.0 + 1.0)      # the ring and its word, centred in the band
            r = d / 2.0;cx = r + 3.0;cy = above + r;box = QRectF(cx - r, cy - r, d, d)
            width = max(2.0, d / 10.0)
            p.setPen(QPen(c['rest'], width));p.setBrush(Qt.NoBrush);p.drawEllipse(box.adjusted(width / 2, width / 2, -width / 2, -width / 2))
            arc = box.adjusted(width / 2, width / 2, -width / 2, -width / 2)
            if v is not None and v > 0.005:
                colour = ramp(v, c);span = -round(360 * 16 * v)
                if level > 0:
                    if t.APPEARANCE == 'kasandra':t.lays_light(p)
                    pen = QPen(faint(colour, min(0.42, 0.11 * level)), width * 3.2, Qt.SolidLine, Qt.RoundCap);p.setPen(pen);p.drawArc(arc, 90 * 16, span)
                    p.setCompositionMode(QPainter.CompositionMode_SourceOver)
                p.setPen(QPen(colour, width, Qt.SolidLine, Qt.RoundCap));p.drawArc(arc, 90 * 16, span)
            p.setFont(self.number_font);p.setPen(c['text'] if v is not None else c['dim'])
            p.drawText(box, Qt.AlignCenter, '—' if v is None else str(round(v * 100)))
            p.setFont(self.key_font);p.setPen(c['label'] if v is not None else c['dim'])
            p.drawText(QRectF(cx - r - 6, cy + r + 2.0, d + 12, key_h), Qt.AlignHCenter | Qt.AlignTop, self.key)
            # the minute beside the ring, when there is room for it
            x0 = cx + r + 5.0;x1 = self.width() - 3.0
            if x1 - x0 < 16:return
            top, foot = cy - r + 2.0, cy + r - 1.0
            p.setPen(QPen(c['grid'], 1));p.drawLine(QPointF(x0, foot + 0.5), QPointF(x1, foot + 0.5))
            if v is None:      # honest: no trace, and the words, on one line or two as the room allows
                small = QFont(self.key_font);small.setPixelSize(max(8, self.key_font.pixelSize() - 1));p.setFont(small);p.setPen(c['dim'])
                room = x1 - x0;fm = p.fontMetrics()
                words = 'no reading' if fm.horizontalAdvance('no reading') <= room else 'no\nreading' if fm.horizontalAdvance('reading') <= room else ''
                p.drawText(QRectF(x0, top - 2.0, room, foot - top + 2.0), Qt.AlignCenter, words)
                return
            now = self.history[-1][0] if self.history else time.monotonic()
            path = QPainterPath();started = False;last = None
            for when, seen in self.history:
                if seen is None:
                    started = False;continue
                x = x1 - (now - when) / MINUTE * (x1 - x0)
                if x < x0:continue
                point = QPointF(x, foot - seen * (foot - top))
                if started:path.lineTo(point)
                else:path.moveTo(point);started = True
                last = point
            colour = ramp(v, c)
            if level > 0:
                p.setPen(QPen(faint(colour, min(0.35, 0.09 * level)), 3.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin));p.drawPath(path)
            p.setPen(QPen(faint(colour, 0.9), 1.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin));p.drawPath(path)
            if last is not None:
                dot = max(1.6, width * 0.75)
                if level > 0:p.setPen(Qt.NoPen);p.setBrush(faint(c['peak'], min(0.4, 0.1 * level)));p.drawEllipse(last, dot * 2.2, dot * 2.2)
                p.setPen(Qt.NoPen);p.setBrush(c['peak']);p.drawEllipse(last, dot, dot)
        finally:
            p.end()
