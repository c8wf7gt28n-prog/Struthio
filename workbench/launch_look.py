"""Graphite 1.0 P4 · the launch look in the window: 1.0's one move to Day, said in one line, once.

DESIGN_DIRECTION_1.0.md section 9: "A fresh profile starts in Day; on the first start of 1.0 an existing profile moves to
Day once, with one line: 'Graphite 1.0 starts in Day. Your earlier look is in Arrange ▸ Appearance.'"

boss_theme decides the look when it is first imported (before any window): on a profile from before 1.0 (a session file
with no launch mark, presentation_preferences.LAUNCH_MARK) it starts in Day (boss_theme.MOVED_TO_DAY). Here, once the
window stands, the move is kept: the session's look becomes Day and the mark is written, so the next start neither moves
nor says anything again, and a look the owner chooses after it (Arrange ▸ Appearance) is kept as before. The line is shown
in a small card at the foot of the centre, a toast that never takes the focus (it goes at a click on ✕, or by itself after
LINE_MS).
A fresh profile has its mark from its first save (session.Session): it was never moved, and nothing is said. A look asked
for in the environment (GRAPHITE_APPEARANCE, a check's) moves nothing and marks nothing.

Nothing here touches the owner's system: it is the window's own presentation preference, in Graphite's session file.
Every colour of the card is a token (design_tokens), read through boss_theme's roles.
"""
from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QPoint, Qt, QTimer
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QToolButton

from . import boss_theme as bt
from . import design_tokens as dt
from .presentation_preferences import APPEARANCE_EARLIER, LAUNCH_MARK, LAUNCH_MARKED

LINE = 'Graphite 1.0 starts in Day. Your earlier look is in Arrange ▸ Appearance.'
LINE_MS = 15000


def install(host):
    """Called once the window is built (shell2's install): the move, a moment after the window shows."""
    host.launch_card = None;host.launch_said = ''
    QTimer.singleShot(0, lambda: first_start(host))
    return host


def first_start(host):
    """Keep 1.0's move to Day in the session and say it once. Returns the line said, or ''."""
    if getattr(host, '_closing', False):return ''
    session = getattr(host, 'session', None);state = getattr(session, 'state', None)
    if not isinstance(state, dict) or state.get(LAUNCH_MARK) == LAUNCH_MARKED:return ''
    if not bt.MOVED_TO_DAY:return ''      # a look asked for in the environment, or a session file that could not be read
    earlier = state.get('appearance') or APPEARANCE_EARLIER
    state['appearance'] = 'day';state[LAUNCH_MARK] = LAUNCH_MARKED
    try:session.save()
    except OSError:
        pass
    if earlier == 'day':return ''      # already Day: nothing changed that needs saying
    say(host, LINE)
    return LINE


def say(host, words):
    host.launch_said = words      # said once, on the card (not in the status line as well: one line, one place)
    card = LaunchCard(host, words);host.launch_card = card
    card.place();card.show();card.raise_()
    QTimer.singleShot(LINE_MS, card.close_card)
    return card


class LaunchCard(QFrame):
    """The one line, on a card at the foot of the centre: elevation 2, radius 10, a ✕ to put it away. It never takes the focus."""

    def __init__(self, host, words):
        super().__init__(host);self.host = host;self.setObjectName('LaunchLine');self.setFocusPolicy(Qt.NoFocus)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        box = QHBoxLayout(self);box.setContentsMargins(dt.PAD['m'], dt.PAD['xs'], dt.PAD['xs'], dt.PAD['xs']);box.setSpacing(dt.PAD['s'])
        self.words = QLabel(words);self.words.setTextFormat(Qt.PlainText);self.words.setObjectName('LaunchLineWords')
        self.close_ = QToolButton();self.close_.setText('✕');self.close_.setFocusPolicy(Qt.NoFocus);self.close_.setAutoRaise(True)
        self.close_.setToolTip('Put this away');self.close_.setAccessibleName('Put this away')
        self.close_.clicked.connect(self.close_card)
        box.addWidget(self.words, 1);box.addWidget(self.close_)
        px, _, weight, face, _, _ = dt.TYPE['body']
        self.setStyleSheet('QFrame#LaunchLine {background:%s; border:1px solid %s; border-radius:%dpx;}'
                           ' QLabel#LaunchLineWords {color:%s; background:transparent; font-family:"%s"; font-size:%dpx;}'
                           ' QToolButton {color:%s; background:transparent; border:0; border-radius:%dpx; padding:2px 6px;}'
                           ' QToolButton:hover {color:%s; background:%s;}'
                           % (bt.CARD, bt.LINE_MID, dt.RADIUS['toast'], bt.TEXT, bt.FACE if bt.LAUNCH else dt.FONT[face], px,
                              bt.QUIET, dt.RADIUS['control'], bt.TEXT, bt.PENCIL_DEEP))
        self.setAccessibleName(words)
        self._watch = _Follow(self);host.installEventFilter(self._watch)

    def place(self):
        host = self.host;self.adjustSize()
        width = min(max(self.sizeHint().width(), 360), max(240, host.width() - 48))
        bar = getattr(host, 'type_bar', None)
        try:foot = bar.mapTo(host, QPoint(0, 0)).y() if bar is not None and bar.isVisible() else host.height()
        except RuntimeError:
            foot = host.height()
        self.setFixedWidth(width)
        self.move((host.width() - width) // 2, max(0, foot - self.sizeHint().height() - dt.PAD['m']))

    def close_card(self):
        try:
            self.hide();self.host.removeEventFilter(self._watch);self.deleteLater()
        except RuntimeError:
            pass
        if getattr(self.host, 'launch_card', None) is self:self.host.launch_card = None


class _Follow(QObject):
    def __init__(self, card):
        super().__init__(card);self.card = card

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Resize:QTimer.singleShot(0, self.card.place)
        return False
