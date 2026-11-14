"""Kasandra's column without her picture (0.8.3): a masthead, as a terminal's, over her words.

The owner, 14 November 2026: "The right column will have more space for kas text. We could revisit that column appearance
because the picture will be gone." Her picture stands in the left pane now (hologram_qt). Her column is her terminal: a
darker ground (TERMINAL_GROUND), a teal edge on its inner side (pane_qt), and at its top one masthead:

    Kasandra ▮                                    quiet      her name, a cursor in the colour of the state of the work, the state
    a model, shortened in the middle · does and shows        what she speaks with, and her hand (a link: click to change it)
    ━━━━──────────────────────────────────────────────────   a rule level with the left pane's tab rule; a teal tick at its left

Her name is said once, at the size of her words (13 November: "Probably don't even need the Stacy name tag taking up space").
The state's word and colour are the hologram's (hologram.STATE_LOOK), so her base and the cursor always agree. The cursor is
steady; while something waits for the owner it breathes with her base, and with Reduce motion it is steady then too.
"""
from __future__ import annotations

import math
import time

from PySide6.QtCore import QPoint, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from . import boss_theme as bt
from . import hologram as holo
from .assistant_identity import named


def scale(host):
    return float((getattr(host, 'reading_profile', None) or {}).get('ui_pt', 14.0)) / 14.0


class ElidedLabel(QLabel):
    """One line shortened in the middle to the room it has (what she speaks with: a model's name can be long); text()
    is what is shown, full() what was given."""

    def __init__(self, text=''):
        super().__init__();self._full = '';self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed);self.setText(text)

    def setText(self, text):
        self._full = str(text);self._fit()

    def full(self):return self._full

    def _fit(self):
        shown = QFontMetrics(self.font()).elidedText(self._full, Qt.ElideMiddle, max(1, self.width()))
        if super().text() != shown:super().setText(shown)

    def sizeHint(self):
        fm = QFontMetrics(self.font());return QSize(fm.horizontalAdvance(self._full) + 2, fm.height())

    def minimumSizeHint(self):
        fm = QFontMetrics(self.font());return QSize(min(fm.horizontalAdvance('…') * 6, self.sizeHint().width()), fm.height())

    def resizeEvent(self, event):super().resizeEvent(event);self._fit()

    def changeEvent(self, event):super().changeEvent(event);self._fit()


class Cursor(QWidget):
    """A block cursor beside her name: 0.45 em wide, 0.78 em tall, standing on the name's baseline, in the state's colour."""

    def __init__(self, name, masthead):
        super().__init__();self.name = name;self.masthead = masthead;self.colour = QColor(bt.VIOLET);self.breathing = False
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._timer = QTimer(self);self._timer.setInterval(140);self._timer.timeout.connect(self.update)

    def em(self):
        return float(QFontMetrics(self.name.font()).height()) * 0.85 or 14.0

    def sizeHint(self):
        return QSize(max(4, round(self.em() * 0.45)), self.name.sizeHint().height())

    def minimumSizeHint(self):return self.sizeHint()

    def set_state(self, colour, breathing, still):
        self.colour = QColor(colour);self.breathing = bool(breathing) and not still
        if self.breathing and self.isVisible():self._timer.start()
        else:self._timer.stop()
        self.update()

    def alpha(self):
        """1.0, or while something waits for the owner 0.6 to 1.0 over 2.8 s, in phase with her hologram's base."""
        if not self.breathing:return 1.0
        return 0.8 + 0.2 * math.sin(2 * math.pi * time.monotonic() / holo.BREATH)

    def showEvent(self, event):
        super().showEvent(event)
        if self.breathing:self._timer.start()

    def hideEvent(self, event):super().hideEvent(event);self._timer.stop()

    def paintEvent(self, event):
        fm = QFontMetrics(self.name.font());h = self.height()
        baseline = (h - fm.height()) / 2 + fm.ascent();tall = fm.ascent() * 0.78 / 0.8;tall = min(tall, baseline)
        ink = QColor(self.colour);ink.setAlphaF(self.alpha())
        p = QPainter(self);p.fillRect(QRectF(0, baseline - tall, self.width(), tall), ink);p.end()


class Masthead(QWidget):
    """The top of her column: her name, a cursor, the state of the work; what she speaks with and her hand; a rule."""

    def __init__(self, host, face):
        super().__init__(face);self.host = host;self.face = face;self.setObjectName('KasandraMasthead')
        s = scale(host);self.state = None
        self.name = QLabel(named('Stacy'));self.name.setObjectName('MastheadName')
        self.name.setStyleSheet('QLabel#MastheadName {color:%s;font-weight:400;font-family:"%s";}' % (bt.VIOLET_PALE, bt.FACE))
        self.cursor = Cursor(self.name, self)
        self.word = QLabel();self.word.setObjectName('MastheadState')
        self.word.setStyleSheet(bt.face_css(bt.FACE, round(14 * s)) + 'color:%s;' % bt.QUIET)
        self.word.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        model = face.model;model.setObjectName('MastheadModel')
        model.setStyleSheet(bt.face_css(bt.MONO, round(13 * s)) + 'color:%s;' % bt.FAINT)
        font = QFont(bt.MONO);font.setPixelSize(round(13 * s));model.setFont(font)
        dot = QLabel('·');dot.setStyleSheet(bt.face_css(bt.MONO, round(13 * s)) + 'color:%s;' % bt.FAINT);self.dot = dot
        hand = face.hand;hand.setStyleSheet(bt.face_css(bt.FACE, round(14 * s)) + 'padding:0 0 1px 0;')      # a link: no button's padding
        top = QHBoxLayout();top.setContentsMargins(0, 0, 0, 0);top.setSpacing(round(4 * s))
        top.addWidget(self.name, 0, Qt.AlignVCenter);top.addWidget(self.cursor, 0, Qt.AlignVCenter);top.addStretch(1);top.addWidget(self.word, 0, Qt.AlignVCenter)
        second = QHBoxLayout();second.setContentsMargins(0, 0, 0, 0);second.setSpacing(round(6 * s))
        second.addWidget(model, 0, Qt.AlignVCenter);second.addWidget(dot, 0, Qt.AlignVCenter);second.addWidget(hand, 0, Qt.AlignVCenter);second.addStretch(1)
        box = QVBoxLayout(self);box.setContentsMargins(0, round(2 * s), 0, round(4 * s) + 1);box.setSpacing(1)
        box.addStretch(1);box.addLayout(top);box.addLayout(second)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self._watch = QTimer(self);self._watch.setInterval(1000);self._watch.timeout.connect(self.follow);self._watch.start()
        from . import kasandra_art
        kasandra_art.watch(host, self)
        self.show_state('idle');QTimer.singleShot(0, self.fit)

    # the state of the work ---------------------------------------------------------------------------------------------
    def update(self, *args):      # kasandra_art.nudge: an act ended
        if not args:self.follow()
        super().update(*args)

    def follow(self):
        stage = getattr(self.host, 'hologram', None)
        if stage is not None:stage.follow(force=True);return      # the hologram reads it and tells the masthead
        from .kasandra_art import current_state
        try:state = current_state(self.host)
        except Exception:  # noqa: BLE001
            state = 'idle'
        self.show_state(state)

    def colour(self):
        return QColor(getattr(bt, holo.look(self.state)[1]))

    def show_state(self, state):
        state = 'idle' if state in (None, 'viewing') else state
        word, _ = holo.look(state)
        if state == self.state and self.word.text() == word:return
        self.state = state;self.word.setText(word)
        self.setAccessibleName(named('Stacy is ') + word);self.word.setAccessibleName(named('Stacy is ') + word)
        from . import pane_qt
        try:still = pane_qt.still(self)
        except Exception:  # noqa: BLE001
            still = True
        self.cursor.set_state(self.colour(), state == 'awaiting_approval', still)

    # its height and its rule ---------------------------------------------------------------------------------------------
    def fit(self):
        """As tall as it needs, and at least as tall as reaches the left pane's tab rule, so the two rules are one line."""
        natural = self.layout().sizeHint().height()
        want = natural
        left = getattr(self.host, 'left_pane', None)
        try:
            if left is not None and left.tabs.isVisible() and self.isVisible():
                rule = left.tabs.mapTo(self.window(), QPoint(0, left.tabs.height() - 1)).y()
                top = self.mapTo(self.window(), QPoint(0, 0)).y()
                want = max(natural, rule - top + 1)
        except RuntimeError:
            return
        if self.height() != want or self.minimumHeight() != want:self.setFixedHeight(want)

    def showEvent(self, event):super().showEvent(event);QTimer.singleShot(0, self.fit)

    def moveEvent(self, event):super().moveEvent(event);QTimer.singleShot(0, self.fit)

    def rule_y(self):
        return self.height() - 1

    def paintEvent(self, event):
        s = scale(self.host);p = QPainter(self);y = self.rule_y()
        p.setPen(QPen(QColor(bt.LINE), 1));p.drawLine(0, y, self.width() - 1, y)
        tick = round(32 * s);thick = max(2, round(2 * s))
        try:
            from .boss_qt import glows
            lit = glows(self.host)
        except Exception:  # noqa: BLE001
            lit = False
        if lit:      # the tick's own light, on a desk that glows
            for spread, alpha in ((4, 0.10), (2, 0.22)):
                halo = QColor(bt.TEAL);halo.setAlphaF(min(0.6, alpha * bt.glow() / 3.0 + alpha / 2))
                p.fillRect(QRectF(0, y + 1 - thick - spread, tick + spread, thick + 2 * spread - 1), halo)
        p.fillRect(QRectF(0, y + 1 - thick, tick, thick), QColor(bt.TEAL))
        p.end()


class Hug(QWidget):
    """A row holding one of your bubbles at its right, as wide as its words up to 85% of the thread (set again on resize)."""

    def __init__(self, bubble):
        super().__init__();self.bubble = bubble
        bubble.text.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        bubble.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
        bubble.setStyleSheet('QFrame#SlateMine {border-radius:8px;}')
        row = QHBoxLayout(self);row.setContentsMargins(0, 0, 0, 0);row.setSpacing(0);row.addStretch(1);row.addWidget(bubble)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        most = max(80, int(self.width() * 0.85));label = self.bubble.text
        words = str(label.property('plain') or label.text())
        margins = self.bubble.layout().contentsMargins();frame = 2 * self.bubble.frameWidth() + 2
        natural = max(QFontMetrics(label.font()).horizontalAdvance(line) for line in (words.split('\n') or [''])) + margins.left() + margins.right() + frame + 4
        width = min(most, natural)
        if self.bubble.width() != width or self.bubble.minimumWidth() != width:self.bubble.setFixedWidth(width)
