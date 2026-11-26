"""NET, the fifth meter at the foot (Graphite 1.0 D1; the design direction's section 5).

The meters are the computer's vital signs: CPU GPU RAM TXT and now NET, the network as K8 governs it (network_governed):
online, offline, not known, or "Kas: <host>" while her fetch runs. Each has a shape as well as a word (state_words: ●
online, ⊘ offline, ◌ not known, ⇣ her fetch), so the state never rests on colour. In each look's meter style: in Graphite
and Kasandra the shape stands where a ring's number stands, NET under it, and the word beside it where a ring keeps its
minute of history; in Day it is words, as the other four are ("NET ● online").

The head said the network's state left of Apps (K8's NetWord); the meter carries it now, so the head no longer does (one
place: network_qt.place_head). A click opens NET's card: the state and why, her fetch or her last fetch, and her web
reading (network_qt.show), where anything she fetches waits for your press.

It reads the network as K8's word did (network_qt.reading: a short local read when the last is stale); it changes nothing.
"""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QFont, QFontMetrics, QFontMetricsF, QPainter, QPen

from . import boss_theme as t
from . import state_words as sw
from .neon_meters import RingMeter, faint, glow_level, palette, words_only

KEY = 'NET'
DOOR = 'The network: online or not, her fetch, and her web reading'
RESERVE = 'offline'     # NET's room for its word on a wide window (online, offline; "not known" and her fetch are drawn where they fit)
WIDE = 1600             # pixels: a window this wide gives NET the room for its word (a narrower one: its shape, the word in its tip)
LONGEST = 22            # a host is shortened in its middle past this many letters ("Kas: datasheets.exa…le.org"), whole in the tip


def net_reading(host):
    """(state key of the table, the word shown, why) from K8's reading; ('net_unknown', 'not known', why) when it cannot be read."""
    try:
        from . import network_qt
        r = network_qt.reading(host)
        kind = network_qt.kind_of(r)
    except Exception as exc:  # noqa: BLE001 - a state that cannot be read is said not known
        return 'net_unknown', sw.word('net_unknown'), 'the network could not be read here: %s' % str(exc)[:120]
    key = sw.NET.get(kind, 'net_unknown')
    if key == 'net_fetching':
        where = str((r.get('fetching') or {}).get('host') or '')
        if len(where) > LONGEST:where = where[:LONGEST // 2] + '…' + where[-(LONGEST // 2 - 1):]
        words = 'Kas: %s' % where if where else 'Kas: fetching'
    else:
        words = sw.word(key)
    return key, words, str(r.get('why') or '')


class NetMeter(RingMeter):
    """The NET meter: a RingMeter in size and place, drawn as a state (a shape and a word), not a share."""

    def __init__(self, host, parent=None):
        super().__init__(KEY, parent);self.host = host;self.state_key = 'net_unknown';self.state_words = sw.word('net_unknown');self.why = ''
        self.setText('—');self.setAccessibleName('NET reading')

    # a state, never a number: the ring's arc and the hot mark have nothing to read
    def value(self):
        return None

    def read(self):
        key, words, why = net_reading(self.host)
        changed = (key, words, why) != (self.state_key, self.state_words, self.why)
        self.state_key, self.state_words, self.why = key, words, why
        self.setText(words)
        tip = 'NET: %s %s. %s' % (sw.shape(key), words, (why[0].upper() + why[1:] + '.') if why else '')
        self.setToolTip(tip.strip() + '\nClick: ' + DOOR + '.');self.setAccessibleDescription(self.toolTip())
        self.setProperty('liveReading', key == 'net_online')
        if changed:self.updateGeometry();self.update()
        return changed

    def colour(self):
        from . import network_qt
        return network_qt.colour_of(network_qt.SHAPE_COLOUR.get({'net_online': 'online', 'net_offline': 'offline',
                                                                  'net_fetching': 'fetching'}.get(self.state_key, 'unknown'), 'ERASED_QUIET'))

    def word_room(self):
        fm = QFontMetrics(self.word_font());return fm.horizontalAdvance(self.state_words) + 6

    def word_font(self):
        f = QFont(self.key_font);f.setPixelSize(max(12, self.number_font.pixelSize()));return f

    def sizeHint(self):
        if words_only():return self.words_size()
        return QSize(self.ring + 8 + self.word_room(), self.ring + 18)

    def minimumSizeHint(self):
        """The shape and its key, and on a wide window a fixed room for the word: the meters do not widen a narrow window's
        panes; the word is drawn whole where there is room for it (at 1366 px there may be none: the shape says it, and the tip
        and NET's card say the word)."""
        wide = self.window() is not None and self.window().width() >= WIDE      # a wide window has the room: the word is always said
        if words_only():
            fm = QFontMetrics(self.words_font())
            word = fm.horizontalAdvance(' ' + RESERVE) if wide else 0      # a fixed room (the widest of its usual words): the panes never jump
            return QSize(fm.horizontalAdvance(self.key + ' ') + fm.ascent() + word + 4, max(self.ring, fm.height() + 8))
        return QSize(self.ring + 4 + (8 + QFontMetrics(self.word_font()).horizontalAdvance(RESERVE) if wide else 0), self.ring + 14)

    # Day: words and numbers, as the other four ("NET ● online"; the shape drawn, not a letter of a font)
    def words(self):
        return self.key + ' ', self.state_words, ''

    def words_size(self):
        fm = QFontMetrics(self.words_font());side = fm.ascent()
        return QSize(fm.horizontalAdvance(self.key + ' ') + side + fm.horizontalAdvance(' ' + self.state_words) + 4, max(self.ring, fm.height() + 8))

    def word_fits(self):
        fm = QFontMetricsF(self.words_font())
        return fm.horizontalAdvance(self.key + ' ') + fm.ascent() + fm.horizontalAdvance(' ' + self.state_words) + 2 <= self.width()

    def words_span(self):
        fm = QFontMetricsF(self.words_font());side = fm.ascent()
        total = fm.horizontalAdvance(self.key + ' ') + side + (fm.horizontalAdvance(' ' + self.state_words) if self.word_fits() else 0)
        x = max(0.0, (self.width() - total) / 2.0);return x, x + total

    def paint_words(self, p):
        c = palette();f = self.words_font();p.setFont(f);fm = QFontMetricsF(f)
        x = self.words_span()[0];base = (self.height() + fm.ascent() - fm.descent()) / 2.0;side = fm.ascent() * 0.92
        p.setPen(c['label']);p.drawText(QPointF(x, base), self.key + ' ');x += fm.horizontalAdvance(self.key + ' ')
        sw.paint(p, QRectF(x, base - fm.ascent() + (fm.ascent() - side) / 2.0 + 1, side, side), self.state_key, self.colour());x += fm.ascent()
        if self.word_fits():      # whole, or not at all
            p.setPen(c['text'] if self.state_key != 'net_unknown' else c['dim']);p.drawText(QPointF(x, base), ' ' + self.state_words)

    def paintEvent(self, event):
        c = palette();level = glow_level(self) if self.glow else 0.0
        p = QPainter(self);p.setRenderHint(QPainter.Antialiasing)
        try:
            if words_only():
                self.paint_words(p);return
            key_h = self.key_font.pixelSize() + 3;d = min(float(self.ring), self.height() - key_h - 8.0)
            above = max(2.0, (self.height() - d - 2.0 - key_h) / 2.0 + 1.0)
            r = d / 2.0;cx = r + 3.0;cy = above + r;box = QRectF(cx - r, cy - r, d, d)
            width = max(2.0, d / 10.0);ink = self.colour()
            p.setPen(QPen(c['rest'], width));p.setBrush(Qt.NoBrush);p.drawEllipse(box.adjusted(width / 2, width / 2, -width / 2, -width / 2))
            shape = box.adjusted(d * 0.27, d * 0.27, -d * 0.27, -d * 0.27)
            if level > 0 and self.state_key == 'net_online':
                p.setPen(Qt.NoPen);p.setBrush(faint(ink, min(0.35, 0.09 * level)));p.drawEllipse(shape.adjusted(-d * 0.1, -d * 0.1, d * 0.1, d * 0.1))
            sw.paint(p, shape, self.state_key, ink)
            p.setFont(self.key_font);p.setPen(c['label'] if self.state_key != 'net_unknown' else c['dim'])
            p.drawText(QRectF(cx - r - 6, cy + r + 2.0, d + 12, key_h), Qt.AlignHCenter | Qt.AlignTop, self.key)
            x0 = cx + r + 5.0;x1 = self.width() - 2.0
            f = self.word_font();p.setFont(f);fm = QFontMetricsF(f)
            if x1 - x0 >= fm.horizontalAdvance(self.state_words):      # the word whole, or not at all (its shape and tip say it)
                p.setPen(c['text'] if self.state_key != 'net_unknown' else c['dim'])
                p.drawText(QRectF(x0, cy - fm.height() / 2.0, x1 - x0, fm.height()), Qt.AlignLeft | Qt.AlignVCenter, self.state_words)
        finally:
            p.end()


def net_card(host, anchor):
    """NET's card: the state in words with its shape, why, her fetch or her last fetch, and her web reading."""
    from .meter_cards import MeterCard
    card = MeterCard(host, 'NET · THE NETWORK')
    key, words, why = net_reading(host)
    card.line('%s %s%s' % (sw.shape(key), words, ('. ' + why[0].upper() + why[1:] + '.') if why else '.'))
    try:
        from . import network_qt
        r = network_qt.reading(host, read=False);last = r.get('last') or {}
        if last.get('host'):
            card.line(('Her last fetch: %s.' % last['host']) if last.get('ok') else ('Her last fetch from %s did not come: %s.' % (last['host'], last.get('why', ''))), quiet=True)
        card.line('Search words are only the words you type, shown before they are sent; a page she fetches is read as data.', quiet=True)
        card.word('Her web reading', lambda: network_qt.show(host), 'What she fetched, kept in quarantine; search words and addresses wait for your press')
    except Exception:  # noqa: BLE001 - the card says the state alone
        pass
    return card


def install(monitors):
    """desktop_header_qt.DesktopMonitors: NET beside CPU GPU RAM TXT (its fifth meter), and host.net_meter."""
    meter = NetMeter(monitors.host, monitors)
    monitors.host.net_meter = meter
    return meter
