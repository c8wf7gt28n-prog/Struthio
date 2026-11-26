"""One language of states (Graphite 1.0 D1; the design direction's section 2).

Every state that matters has one word and one shape, the same everywhere (the board's tiles and wires, her column's steps
and her own state, the "Waits for you" band, the dock, the meters), and a colour only as a third cue:

    state                 shape            word                                  where
    recorded link         solid line       recorded                              board wires
    inferred link         dashed line      possible · not verified               board wires
    current / supported   ■ filled square  CURRENT · SUPPORTED                   tiles, findings
    archived              — dash           ARCHIVED                              tiles
    refuted               ⊘                REFUTED                               tiles, findings
    open question         □ empty square   OPEN                                  tiles
    verified (done)       ✓                done (verified)                       steps, receipts
    prepared              ○                prepared                              steps
    sent, being checked   →                sent                                  steps
    waits for your word   ◆                NEEDS YOUR WORD                       steps, her state
    waits for your grant  ◆ with a key     NEEDS YOUR GRANT                      steps, grants
    needs your review     ◆ with an eye    NEEDS REVIEW                          steps (a dialog seen)
    blocked               ▭ hollow bar     blocked: <why>                        steps
    stopped               ▮▮               stopped by you · stopped by HALT      steps, her state
    held                  ‖                held                                  her work under HALT

and the network's own states (K8), which the foot's NET meter shows: ● online, ⊘ offline, ◌ not known, ⇣ her fetch; and a file
open in another program (A1), on its FILE tile: a window with its title bar filled (OPEN IN <PROGRAM>), its title bar hollow
while its window is looked for (OPENING IN <PROGRAM>), a dash once it closed (<PROGRAM> CLOSED).

This module is the table and nothing else: it reads no record and changes nothing. Each surface keeps its own words where
they already say the same thing (an assignment's "waiting for your word" is NEEDS YOUR WORD's own words in a sentence); what
it draws as a shape comes from here (`shape`, `paint`), so a state never rests on colour alone. Qt is imported only by the
drawing (`paint`, `Mark`), so the table itself can be read without a window.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class State:
    key: str
    shape: str          # the shape in words: what a line of text shows before the word
    word: str           # the word, as it is shown
    mark: str           # how a painted surface draws it (paint)
    colour: str         # the palette's name for its colour (boss_theme), the third cue
    where: tuple = ()


TABLE = (
    State('recorded', '━', 'recorded', 'solid', 'LINE_STRONG', ('board wires',)),
    State('possible', '┄', 'possible · not verified', 'dashed', 'LINE_STRONG', ('board wires',)),
    State('current', '■', 'CURRENT', 'filled', 'READY', ('tiles', 'findings')),
    State('supported', '■', 'SUPPORTED', 'filled', 'READY', ('tiles', 'findings')),
    State('archived', '—', 'ARCHIVED', 'dash', 'QUIET', ('tiles',)),
    State('refuted', '⊘', 'REFUTED', 'slashed', 'RED', ('tiles', 'findings')),
    State('open', '□', 'OPEN', 'hollow', 'OWNER', ('tiles',)),
    State('done', '✓', 'done (verified)', 'check', 'READY', ('steps', 'receipts')),
    State('prepared', '○', 'prepared', 'ring', 'QUIET', ('steps',)),
    State('sent', '→', 'sent', 'arrow', 'TEXT', ('steps',)),
    State('needs_word', '◆', 'NEEDS YOUR WORD', 'diamond', 'OWNER', ('steps', 'her state')),
    State('needs_grant', '◆', 'NEEDS YOUR GRANT', 'diamond_key', 'OWNER', ('steps', 'grants')),
    State('needs_review', '◆', 'NEEDS REVIEW', 'diamond_eye', 'OWNER', ('steps',)),
    State('blocked', '▭', 'blocked', 'bar', 'RED', ('steps',)),
    State('stopped', '▮▮', 'stopped by you', 'pause', 'QUIET', ('steps', 'her state')),
    State('stopped_halt', '▮▮', 'stopped by HALT', 'pause', 'RED', ('steps', 'her state')),
    State('held', '‖', 'held', 'held', 'RED', ('her work under HALT',)),
    # the network (1.0 K8), as NET says it at the foot and the head said it before
    State('net_online', '●', 'online', 'dot', 'READY', ('NET',)),
    State('net_offline', '⊘', 'offline', 'slashed', 'STOP', ('NET',)),
    State('net_unknown', '◌', 'not known', 'dotted', 'ERASED_QUIET', ('NET',)),
    State('net_fetching', '⇣', 'Kas: {host}', 'down', 'READY', ('NET',)),
    # a file open in another program (1.0 A1): the program's name stands in the word
    State('open_in', '▣', 'OPEN IN {program}', 'window', 'READY', ('tiles',)),
    State('opening_in', '▢', 'OPENING IN {program}', 'window_hollow', 'QUIET', ('tiles',)),
    State('program_closed', '—', '{program} CLOSED', 'dash', 'QUIET', ('tiles',)),
)
STATES = {s.key: s for s in TABLE}

# Each surface's own words for a state, read as the table's key. A word that is not here keeps the surface's own shape.
TILE = {'CURRENT': 'current', 'SUPPORTED': 'supported', 'HOLDS': 'current', 'UP': 'current', 'RUNNING': 'current',
        'ARCHIVED': 'archived', 'REPLACED': 'archived', 'REFUTED': 'refuted', 'DOES NOT HOLD': 'refuted', 'OPEN': 'open',
        'UNKNOWN': 'open', 'CANNOT TELL': 'open', 'DEPENDS': 'open'}
# An assignment's state words (assignments._state_words) and a step's status (assignments.STATUSES).
STEP = {'done': 'done', 'waiting for your word': 'needs_word', 'proposed': 'needs_word', 'needs your grant': 'needs_grant',
        'needs review': 'needs_review', 'blocked': 'blocked', 'needs the network': 'blocked', 'stopped by you': 'stopped',
        'held': 'held', 'interrupted': 'prepared', 'prepared': 'prepared', 'sent': 'sent', 'dispatched': 'sent'}
# Her own state (her column's head, the dock): her_column_qt.STATES' keys.
HER = {'awaiting_approval': 'needs_word', 'blocked': 'stopped', 'held': 'held', 'completed': 'done'}
# The network's kinds (network_qt.kind_of).
NET = {'online': 'net_online', 'offline': 'net_offline', 'unknown': 'net_unknown', 'fetching': 'net_fetching'}


def state(key):
    return STATES.get(key)


def shape(key, default=''):
    s = STATES.get(key);return s.shape if s is not None else default


def word(key, default=''):
    s = STATES.get(key);return s.word if s is not None else default


def said(key, why=''):
    """The shape and the word together, as a line of text shows them ("◆ NEEDS YOUR GRANT", "▭ blocked: needs the network")."""
    s = STATES.get(key)
    if s is None:return why
    if key == 'blocked' and why:return '%s blocked: %s' % (s.shape, why)
    return '%s %s' % (s.shape, s.word)


def of_tile(word_):
    """A tile's or a finding's state word (KIND • STATE) as the table's key, or ''."""
    word_ = str(word_ or '').strip().upper()
    if word_.startswith('OPEN IN '):return 'open_in'      # 1.0 A1's words, with the program's name in them
    if word_.startswith('OPENING IN '):return 'opening_in'
    if word_.endswith(' CLOSED') and len(word_) > len(' CLOSED'):return 'program_closed'
    return TILE.get(word_, '')


def of_step(words):
    """An assignment's or a step's state words as the table's key, or ''."""
    words = str(words or '').strip().lower()
    if words.startswith('needs your grant'):return 'needs_grant'
    if words.startswith('blocked') or words.startswith('needs the network'):return 'blocked'
    return STEP.get(words, '')


def of_her(state_):
    """Her state (her column's head, the dock) as the table's key, or '' where her own word stands (QUIET, WORKING)."""
    return HER.get(str(state_ or ''), '')


def colour_of(key, palette=None):
    """The state's colour in the look in force (the third cue only)."""
    s = STATES.get(key)
    if palette is None:
        from . import boss_theme as palette
    if s is None:return getattr(palette, 'TEXT', '#000000')
    return getattr(palette, s.colour, getattr(palette, 'TEXT', '#000000'))


# ---------------------------------------------------------------------------------------------------------------- drawing
def paint(p, rect, key_or_mark, colour, width=None):
    """Draw a state's shape in rect (a QRectF) with this colour: the same shape on every surface. key_or_mark is a key of the
    table or one of its marks. Returns False when there is nothing to draw for it."""
    from PySide6.QtCore import QPointF, QRectF, Qt
    from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPolygonF
    s = STATES.get(key_or_mark);mark = s.mark if s is not None else str(key_or_mark or '')
    c = QColor(colour);r = QRectF(rect);side = min(r.width(), r.height())
    box = QRectF(r.center().x() - side / 2, r.center().y() - side / 2, side, side)
    w = width or max(1.3, side / 7.5)
    p.save();p.setRenderHint(QPainter.Antialiasing, True)
    pen = QPen(c, w);pen.setCapStyle(Qt.RoundCap);pen.setJoinStyle(Qt.RoundJoin);p.setPen(pen);p.setBrush(Qt.NoBrush)
    inner = box.adjusted(w / 2, w / 2, -w / 2, -w / 2)
    try:
        if mark == 'filled':
            p.setPen(Qt.NoPen);p.setBrush(c);p.drawRect(inner)
        elif mark == 'hollow':
            p.drawRect(inner)
        elif mark == 'dash':
            p.drawLine(QPointF(inner.left(), inner.center().y()), QPointF(inner.right(), inner.center().y()))
        elif mark == 'slashed':
            p.drawEllipse(inner);d = inner.width() * 0.35
            p.drawLine(QPointF(inner.center().x() - d, inner.center().y() + d), QPointF(inner.center().x() + d, inner.center().y() - d))
        elif mark == 'check':
            path = QPainterPath();path.moveTo(inner.left(), inner.center().y());path.lineTo(inner.left() + inner.width() * 0.38, inner.bottom())
            path.lineTo(inner.right(), inner.top());p.drawPath(path)
        elif mark == 'ring':
            p.drawEllipse(inner)
        elif mark == 'dot':
            p.setPen(Qt.NoPen);p.setBrush(c);p.drawEllipse(inner.adjusted(side * 0.1, side * 0.1, -side * 0.1, -side * 0.1))
        elif mark == 'dotted':
            dotted = QPen(c, w);dotted.setStyle(Qt.DotLine);p.setPen(dotted);p.drawEllipse(inner.adjusted(side * 0.06, side * 0.06, -side * 0.06, -side * 0.06))
        elif mark in ('arrow', 'down'):
            y = inner.center().y();x = inner.center().x()
            if mark == 'arrow':
                p.drawLine(QPointF(inner.left(), y), QPointF(inner.right(), y))
                p.drawPolyline(QPolygonF([QPointF(inner.right() - side * 0.32, y - side * 0.3), QPointF(inner.right(), y), QPointF(inner.right() - side * 0.32, y + side * 0.3)]))
            else:
                p.drawLine(QPointF(x, inner.top()), QPointF(x, inner.bottom()))
                p.drawPolyline(QPolygonF([QPointF(x - side * 0.3, inner.bottom() - side * 0.32), QPointF(x, inner.bottom()), QPointF(x + side * 0.3, inner.bottom() - side * 0.32)]))
        elif mark.startswith('diamond'):
            cx, cy = inner.center().x(), inner.center().y();h = inner.width() / 2
            diamond = QPolygonF([QPointF(cx, cy - h), QPointF(cx + h, cy), QPointF(cx, cy + h), QPointF(cx - h, cy)])
            if mark == 'diamond':
                p.setPen(Qt.NoPen);p.setBrush(c);p.drawPolygon(diamond)
            else:      # the diamond's outline with what it waits for inside: a key (a grant) or an eye (a review)
                p.drawPolygon(diamond);thin = QPen(c, max(1.0, w * 0.8));thin.setCapStyle(Qt.RoundCap);p.setPen(thin)
                if mark == 'diamond_key':
                    ring = h * 0.28;p.drawEllipse(QPointF(cx - h * 0.22, cy), ring, ring)
                    p.drawLine(QPointF(cx - h * 0.22 + ring, cy), QPointF(cx + h * 0.42, cy))
                    p.drawLine(QPointF(cx + h * 0.3, cy), QPointF(cx + h * 0.3, cy + h * 0.22))
                else:
                    eye = QPainterPath();eye.moveTo(cx - h * 0.5, cy);eye.quadTo(cx, cy - h * 0.42, cx + h * 0.5, cy)
                    eye.quadTo(cx, cy + h * 0.42, cx - h * 0.5, cy);p.drawPath(eye)
                    p.setPen(Qt.NoPen);p.setBrush(c);p.drawEllipse(QPointF(cx, cy), h * 0.14, h * 0.14)
        elif mark in ('window', 'window_hollow'):      # a program's window: its title bar filled while open, a rule while looked for
            p.drawRect(inner);bar = QRectF(inner.left(), inner.top(), inner.width(), inner.height() * 0.34)
            if mark == 'window':p.setPen(Qt.NoPen);p.setBrush(c);p.drawRect(bar)
            else:p.drawLine(bar.bottomLeft(), bar.bottomRight())
        elif mark == 'bar':
            p.drawRect(QRectF(inner.left(), inner.center().y() - inner.height() * 0.22, inner.width(), inner.height() * 0.44))
        elif mark in ('pause', 'held'):
            p.setPen(Qt.NoPen);p.setBrush(c);bw = inner.width() * (0.26 if mark == 'pause' else 0.14)
            for x in (inner.left() + inner.width() * 0.18, inner.right() - inner.width() * 0.18 - bw):
                p.drawRect(QRectF(x, inner.top(), bw, inner.height()))
        elif mark in ('solid', 'dashed'):
            line = QPen(c, w);line.setCapStyle(Qt.FlatCap)
            if mark == 'dashed':line.setStyle(Qt.CustomDashLine);line.setDashPattern([3, 2.5])
            p.setPen(line);p.drawLine(QPointF(r.left(), r.center().y()), QPointF(r.right(), r.center().y()))
        else:
            return False
        return True
    finally:
        p.restore()


def Mark(key, colour=None, side=14, parent=None):
    """A small widget that draws one state's shape (her column's band, a legend); its tip and name are the state's word."""
    from PySide6.QtCore import QRectF, QSize
    from PySide6.QtGui import QPainter
    from PySide6.QtWidgets import QWidget

    class _Mark(QWidget):
        def __init__(self):
            super().__init__(parent);self.key = key;self.colour = colour;self.setFixedSize(QSize(side, side))
            self.setAccessibleName(word(key, key));self.setToolTip(word(key, key))

        def set(self, key_, colour_=None):
            if (key_, colour_) == (self.key, self.colour):return
            self.key = key_;self.colour = colour_;self.setAccessibleName(word(key_, key_));self.setToolTip(word(key_, key_));self.update()

        def paintEvent(self, event):
            p = QPainter(self)
            try:paint(p, QRectF(1, 1, self.width() - 2, self.height() - 2), self.key, self.colour or colour_of(self.key))
            finally:p.end()
    return _Mark()
