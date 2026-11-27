"""HALT in the head's upper-left slot (1.0 P2), in every look: a triangle and the word HALT; RESUME while her work is held.

The press is halt.press(host) (hold her work, stop what of hers runs, stop her hand, say what was stopped); RESUME is
halt.release(host). The button reads HALT's own hold every two seconds (1.0 K3: Stop all's hold of Graphite's jobs is its
own and no longer reads RESUME here).

Day (the owner's picture): a green triangle and the word HALT in the band's ink. Graphite: the triangle in its amber
stop colour, the word in the band's pale lettering. Kasandra: the triangle in her raspberry, the word in her typewriter
face. Held, in every look: a right-pointing triangle (the shape of "go on") in the colour of what waits for the owner, the
word RESUME, and a short mark under it. The colour is never alone: the shape and the word say the same.
"""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPainterPath
from PySide6.QtWidgets import QToolButton

from . import boss_theme as t

POLL_MS = 2000
NAMES = {False: ('HALT', "HALT: stop all of Kasandra's work now. The desktop and your apps keep running."),
         True: ('RESUME', "RESUME: lift the hold on Kasandra's work. Nothing stopped is restarted by this.")}


class HaltButton(QToolButton):
    """The master stop of her managed work, upper left."""

    def __init__(self, host, parent=None):
        super().__init__(parent);self.host = host;self.scale = 1.0;self.held = False;self.busy = False
        self.setObjectName('HaltButton');self.setCursor(Qt.PointingHandCursor);self.setFocusPolicy(Qt.StrongFocus)
        self.setAttribute(Qt.WA_Hover, True);self.setProperty('paperFunctionalInk', True);self.setAutoRaise(True)
        self.clicked.connect(self.act);self._name()
        self.timer = QTimer(self);self.timer.setInterval(POLL_MS);self.timer.timeout.connect(self.refresh);self.timer.start()
        QTimer.singleShot(0, self.refresh)

    def _name(self):
        word, said = NAMES[self.held]
        self.setText(word);self.setAccessibleName(word);self.setAccessibleDescription(said);self.setToolTip(said)

    def refresh(self, _read=None):
        if getattr(self.host, '_closing', False):return
        if self.busy:return      # 1.0 F3: your press is on its way; a reading made before it never puts the old word back
        from . import floor      # 1.0 F2: the timer's reading of the hold is made off the window's thread, then shown
        if _read is None and floor.gather(self.host, lambda read: read('halt.status'),
                                          lambda extra: self.refresh(_read=floor.answered(self.host, 'halt.status') or {}), key=('halt', id(self))):return
        if _read is not None and _read is not floor.MISS:now = bool(_read.get('held'))
        else:
            from .halt import held
            now = held(self.host)
        if now != self.held:
            self.held = now;self._name();self.update()

    def act(self):
        if self.busy:return
        self.busy = True
        from . import halt

        def landed(_out=None):      # 1.0 F3: the hold (or its lifting) made on a thread of its own; read again when it has landed
            self.busy = False;self.refresh()
        try:
            if self.held:halt.release(self.host, then=landed)
            else:halt.press(self.host, then=landed)
            self.held = not self.held;self._name();self.update()      # 1.0 F3: your press is said at once
        except Exception:  # noqa: BLE001 - read again as before
            from . import floor
            self.busy = False;self.refresh(_read=floor.MISS)

    # -- the face ---------------------------------------------------------------------------------------------------------
    def word_font(self):
        s = min(max(self.scale, 0.8), 1.4)
        if t.APPEARANCE == 'kasandra':
            f = QFont(t.DISPLAY);f.setPixelSize(max(15, round(18 * s)));f.setLetterSpacing(QFont.AbsoluteSpacing, 1.2 * s)
        elif t.LAUNCH:      # 1.0 P4: Day and Night
            f = QFont(t.FACE);f.setPixelSize(max(14, round(17 * s)));f.setWeight(QFont.DemiBold);f.setLetterSpacing(QFont.AbsoluteSpacing, 1.4 * s)
        else:
            f = QFont(t.MONO);f.setPixelSize(max(14, round(16 * s)));f.setWeight(QFont.DemiBold);f.setLetterSpacing(QFont.AbsoluteSpacing, 1.0 * s)
        return f

    def colours(self):
        """(the triangle, the word) in the look in force."""
        if self.held:return t.OWNER, t.ERASED
        if t.LAUNCH:return t.DAY_MARKS['HALT'], t.ERASED      # 1.0 P4: the live green in Day and Night (red in Night would read as an error)
        return t.STOP, t.ERASED

    def need(self, height):
        """The width the face needs at this height: the triangle, a gap and the longer of the two words (so it never jumps)."""
        fm = QFontMetricsF(self.word_font());side = self.side(height)
        return round(side + side * 0.55 + max(fm.horizontalAdvance(w) for w in ('HALT', 'RESUME')) + 2 * self.pad())

    def side(self, height):
        return max(12.0, round(height * 0.36))

    def pad(self):
        return round(8 * min(max(self.scale, 0.8), 1.4))

    def sizeHint(self):
        h = max(28, round(40 * self.scale));return QSize(self.need(h), h)

    def paintEvent(self, event):
        p = QPainter(self);p.setRenderHint(QPainter.Antialiasing)
        edge = max(2, round(2 * self.scale));w, h = self.width(), self.height()
        if self.underMouse() and not self.isDown():
            p.fillRect(self.rect(), QColor(t.TEAL_SOFT));p.fillRect(0, h - edge, w, edge, QColor(t.READY))
        elif self.hasFocus() or self.isDown():
            p.fillRect(self.rect(), QColor(t.AMBER_SOFT));p.fillRect(0, h - edge, w, edge, QColor(t.AMBER_EDGE))
        shape, ink = self.colours()
        side = self.side(h);x = self.pad();cy = h / 2.0
        path = QPainterPath()
        if self.held:      # ▶: go on
            path.moveTo(QPointF(x, cy - side / 2));path.lineTo(QPointF(x + side * 0.9, cy));path.lineTo(QPointF(x, cy + side / 2))
        else:              # ▲: the stop sign of the picture
            path.moveTo(QPointF(x + side / 2, cy - side * 0.48));path.lineTo(QPointF(x + side, cy + side * 0.42));path.lineTo(QPointF(x, cy + side * 0.42))
        path.closeSubpath();p.setPen(Qt.NoPen);p.setBrush(QColor(shape));p.drawPath(path)
        font = self.word_font();p.setFont(font);fm = QFontMetricsF(font)
        tx = x + side + side * 0.55;p.setPen(QColor(ink))
        rect = QRectF(tx, 0, max(0.0, w - tx - self.pad() / 2), h)
        p.drawText(rect, Qt.AlignLeft | Qt.AlignVCenter, fm.elidedText(self.text(), Qt.ElideRight, rect.width()))
        if self.held and not (self.hasFocus() or self.isDown() or self.underMouse()):      # held: a short mark under the word
            mark = max(2, round(2 * self.scale));y = round(cy + fm.ascent() / 2 + 4 * min(self.scale, 1.4))
            p.fillRect(QRectF(tx, min(h - mark - 1, y), fm.horizontalAdvance(self.text()), mark), QColor(shape))
        p.end()


def install_head(top):
    """shell2's head: HALT in the upper-left slot (1.0 P2). Returns the button."""
    button = HaltButton(top.host, top.first_row);top.halt = button;button.show()
    return button


def place_head(top, d):
    """shell2's head placement: HALT at the band's inset in the upper-left slot, no wider than the left column's room (the
    menus start at the middle column's edge)."""
    button = getattr(top, 'halt', None)
    if button is None:return
    button.scale = min(d.scale, 1.4);h = d.band;o = d.inset
    tall = max(24, h - 2 * round(6 * min(d.scale, 1.4)));room = max(0, d.pane - 2 * o)
    wide = min(room, button.need(tall))
    button.setGeometry(o, (h - tall) // 2, wide, tall);button.setVisible(wide >= 40);button.raise_()
