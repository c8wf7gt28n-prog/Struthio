"""Graphite 1.1 B3 · Kas on the bar: her chip, HALT beside her name, her panel from the right edge, her cards from her chip.

PLAN_1.1.md, B3; the design direction's sections 2, 3 and 6 ("Familiar", section 9). Only her furniture moves here. Her
rules do not: every press below is the same call it was in 1.0 (halt.press and halt.release, waits_qt's presses through
HerColumn.take_step, the Kernel's checks at dispatch), and nothing here writes a record by being shown.

  her chip       the bar's kas slot (bar_qt.register_slot): "Kas", then her state's shape and word in her column's own
                 language (her_column_qt.STATES): ○ QUIET, ● WORKING, ◆ NEEDS YOUR WORD (with how many when more than one
                 waits), ✓ DONE, ▮▮ STOPPED, ‖ HELD. A press opens her panel, or closes it; a right-click offers the same and
                 the setting "Kas docked in Graphite".
  HALT           beside her name, in the same spot at every size: the triangle and the word; held, ▶ RESUME. It is 1.0's
                 button (halt_qt.HaltButton) drawn for the bar, so a press is halt.press(host) and nothing else: it stops all
                 of her work and nothing else, and RESUME restarts nothing by itself. Once it stands on the bar the head's
                 HALT goes (one place for each thing). The Pause key in Graphite presses HALT (never RESUME: that is a press).
  her panel      1.0's right column, the very same widgets (host.right_pane, with "Waits for you" at its top, never covered),
                 in a window of its own at the screen's right edge, 380 px wide, from the top of the screen to the bar, above
                 the apps and below the bar's flyouts. It slides in (220 ms; at once under Reduce motion) when her chip is
                 pressed and goes on Esc or another press of the chip. "Kas docked in Graphite" (on by default, in
                 ~/.config/graphite/kas_bar.json): inside Graphite's window her column stays docked at the right as in 1.0,
                 and a press of her chip while Graphite is in front shows her there; over other apps the panel slides. Off,
                 her column lives in the panel only and Graphite's window gives its room to the work.
  her cards      when something waits for the owner (waits_qt.items: Authorise step n, a grant in plain words, a review, a
                 Resume, her question) and her column is not in sight, a card rises from her chip above the bar with the same
                 rows and the same one press. It never takes the keys from the app in front (it accepts no focus), and it is
                 deaf for its first half second, so a click meant for the app behind it is not taken as a yes.

Everything here stands only where the bar stands (bar_qt.install: the dedicated session, or GRAPHITE_BAR=1, on X); without
the bar, Graphite is as 1.0 was: her column docked, HALT in the head.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPoint, QPointF, QPropertyAnimation, QRect, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetrics, QFontMetricsF, QGuiApplication, QKeySequence, QPainter, QPainterPath, QPen, QShortcut
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel, QMenu, QPushButton, QSizePolicy, QVBoxLayout, QWidget)

from . import bar_qt
from . import design_tokens as tokens
from . import halt_qt

PANEL_WIDTH = 380            # her panel, at the screen's right edge
SLIDE_MS = tokens.MOTION['panel']      # 220 ms: the panel slides from its edge
RISE_MS = 160                # a card rises 8 px from her chip
RISE_PX = 8
DEAF_MS = 500                # a card hears no press for its first half second
CARD_MOST = 3                # rows on a card; the rest are counted (they stand in her panel too)
TICK_MS = 1000               # the card and the chip follow what waits this often (a read of her column's rows, no Kernel)
SETTINGS = 'kas_bar.json'
DEFAULTS = {'docked': True}
WORDS = {      # furniture: the chip's menu and the card's controls (her own lines are kas_voice's and waits_qt's)
    'open': 'Open her panel', 'close': 'Close her panel', 'docked': 'Kas docked in Graphite', 'later': 'Later',
    'panel_link': 'Her panel →',
    'chip_tip': 'Kasandra (Kas): {state}\nPress to open her panel; press again or Esc to close it.',
    'chip_tip_docked': 'Kasandra (Kas): {state}\nPress to see her column. Over other apps her panel slides in from the right.',
    'card_tip': 'Waits for you. Your press here is the same press as in her panel. This card never takes your keys.',
}


# ---- the setting ----------------------------------------------------------------------------------------------------------------
def settings_file(environ=None):
    environ = os.environ if environ is None else environ
    base = environ.get('XDG_CONFIG_HOME') or os.path.join(environ.get('HOME') or str(Path.home()), '.config')
    return Path(base) / 'graphite' / SETTINGS


def read_settings(environ=None):
    """{'docked': bool}: a readable file of the owner's; a missing or broken one gives the defaults."""
    out = dict(DEFAULTS)
    try:
        got = json.loads(settings_file(environ).read_text(encoding='utf-8'))
        if isinstance(got.get('docked'), bool):out['docked'] = got['docked']
    except (OSError, ValueError, AttributeError):
        pass
    return out


def write_settings(environ=None, **changes):
    now = read_settings(environ)
    if isinstance(changes.get('docked'), bool):now['docked'] = changes['docked']
    path = settings_file(environ)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix('.tmp');temp.write_text(json.dumps(now, indent=1) + '\n', encoding='utf-8');os.replace(temp, path)
    except OSError:
        pass
    return now


def reduce_motion(host):
    try:
        from .document_qt import profile_of
        return bool(profile_of(host).get('reduce_motion'))
    except Exception:  # noqa: BLE001 - motion is a grace, never a reason to fail
        return False


# ---- her state, as the chip says it ---------------------------------------------------------------------------------------------
def chip_state(column, waiting=0):
    """(state, word, shape) for her chip from her column's shown state (her_column_qt.STATES: the same words and shapes as her
    column's head); waiting: how many things wait for the owner, said after the word when more than one does."""
    from .her_column_qt import STATES
    state = str(getattr(column, 'shown_state', '') or 'idle') if column is not None else 'idle'
    if state not in STATES:state = 'working' if state not in ('', 'viewing') else 'idle'
    word, shape, _ = STATES[state]
    if state == 'awaiting_approval' and waiting > 1:word = '%s [%d]' % (word, waiting)
    return state, word, shape


def shape_colour(state, c):
    """The third cue only: the shape's colour in the bar's tokens."""
    return {'working': c['live'], 'awaiting_approval': c['waiting'], 'completed': c['live'], 'blocked': c['danger'],
            'held': c['danger']}.get(state, c['secondary'])


def paint_shape(p, rect, state, colour):
    """Her state's shape, drawn: a ring (QUIET), a dot (WORKING), the table's diamond, check, pause or held marks."""
    from . import state_words as sw
    p.save();p.setRenderHint(QPainter.Antialiasing)
    if state == 'idle':
        p.setPen(QPen(QColor(colour), 1.5));p.setBrush(Qt.NoBrush);p.drawEllipse(rect.adjusted(1, 1, -1, -1))
    elif state == 'working':
        p.setPen(Qt.NoPen);p.setBrush(QColor(colour));p.drawEllipse(rect.adjusted(1, 1, -1, -1))
    else:
        key = {'awaiting_approval': 'needs_word', 'completed': 'done', 'blocked': 'stopped', 'held': 'held'}.get(state, 'needs_word')
        sw.paint(p, rect, key, colour)
    p.restore()


# ---- the chip and HALT ----------------------------------------------------------------------------------------------------------
class KasChip(bar_qt.BarButton):
    """"Kas", her state's shape and word. A press opens or closes her panel; a right-click offers the same and the setting."""

    def __init__(self, slot):
        super().__init__(slot, 'Kasandra');self.slot = slot;self.setText('Kas')
        self.clicked.connect(lambda: self.slot.ctl.toggle())
        self.setContextMenuPolicy(Qt.CustomContextMenu);self.customContextMenuRequested.connect(self.offer)

    def state(self):
        ctl = self.slot.ctl
        return chip_state(ctl.column(), len(ctl.waiting()))

    @staticmethod
    def metrics(h):
        """(pad, gap, side, the word's font): tighter on the short bar (1366x768), so the open windows keep their room."""
        tall = h >= bar_qt.TALL
        return (round(h * 0.3) if tall else 8), (8 if tall else 6), round(h * (0.32 if tall else 0.3)), \
            bar_qt.bar_font(h, None, None if tall else tokens.TYPE['footnote'][0])

    def natural(self, h):
        state, word, shape = self.state();pad, gap, side, font = self.metrics(h)
        return 2 * pad + QFontMetrics(bar_qt.bar_font(h, QFont.DemiBold)).horizontalAdvance('Kas') + gap + side + 5 + \
            QFontMetrics(font).horizontalAdvance(word)

    def paintEvent(self, event):
        c = bar_qt.ink();p = QPainter(self);w, h = self.width(), self.height()
        state, word, shape = self.state();pad, gap, side, word_font = self.metrics(h)
        r = self.ground(p, c, active=self.slot.ctl.panel_open())
        if state == 'awaiting_approval':      # what waits: a tint of its colour under the chip, with the shape and the word
            bar_qt.plate(p, r, tokens.over(c['waiting'], c['sidebar'], tokens.TINT['waiting']))
        x = pad;font = bar_qt.bar_font(h, QFont.DemiBold);p.setFont(font);p.setPen(QColor(c['text']))
        p.drawText(QRect(x, 0, w, h), Qt.AlignLeft | Qt.AlignVCenter, 'Kas')
        x += QFontMetrics(font).horizontalAdvance('Kas') + gap
        paint_shape(p, QRectF(x, (h - side) / 2.0, side, side), state, shape_colour(state, c))
        x += side + 5;p.setFont(word_font);p.setPen(QColor(c['text'] if state == 'awaiting_approval' else c['secondary']))
        p.drawText(QRect(x, 0, w - x, h), Qt.AlignLeft | Qt.AlignVCenter, word)
        if self.slot.ctl.panel_open():p.fillRect(QRectF(6, h - 5, w - 12, 2), QColor(c['accent']))      # open: the accent rule, as an active window's
        p.end()
        said = '%s %s' % (shape, word)
        tip = (WORDS['chip_tip_docked'] if self.slot.ctl.docked else WORDS['chip_tip']).format(state=said)
        if tip != self.toolTip():self.setToolTip(tip);self.setAccessibleName('Kasandra, ' + word)

    def offer(self, at):
        ctl = self.slot.ctl;menu = QMenu(self)
        menu.addAction(WORDS['close'] if ctl.panel_open() else WORDS['open'], ctl.toggle)
        docked = menu.addAction(WORDS['docked']);docked.setCheckable(True);docked.setChecked(ctl.docked)
        docked.toggled.connect(ctl.set_docked)
        ctl.last_menu = menu
        menu.popup(self.mapToGlobal(at))
        return menu


class HaltOnBar(halt_qt.HaltButton):
    """1.0's HALT (halt_qt.HaltButton: its press, its reading of the hold every two seconds), drawn for the bar: the triangle and
    the word in an outlined plate, as wide as the longer of HALT and RESUME so nothing on the bar moves. Never takes the focus."""
    on_bar = True      # halt_qt.place_head: never placed in the head

    def __init__(self, host, parent):
        super().__init__(host, parent);self.setFocusPolicy(Qt.NoFocus);self.setObjectName('BarHalt')

    def bar_font(self, h):
        tall = h >= bar_qt.TALL
        f = bar_qt.bar_font(h, QFont.DemiBold, None if tall else tokens.TYPE['footnote'][0])
        f.setLetterSpacing(QFont.AbsoluteSpacing, 1.0 if tall else 0.6);return f

    @staticmethod
    def pad(h=None):
        return 10 if (h or 0) >= bar_qt.TALL else 8

    def need(self, height):
        fm = QFontMetricsF(self.bar_font(height));side = round(height * 0.34)
        return round(self.pad(height) + side + 6 + max(fm.horizontalAdvance(w) for w in ('HALT', 'RESUME')) + self.pad(height))

    def sizeHint(self):
        return QSize(self.need(bar_qt.SHORT), bar_qt.SHORT)

    def paintEvent(self, event):
        c = bar_qt.ink();marks = tokens.marks(bar_qt.look());p = QPainter(self);p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height();r = QRectF(2.5, 6.5, w - 5, h - 13)
        fill = c['pressed'] if self.isDown() else (c['hover_side'] if self.underMouse() else c['sidebar'])
        inverse = bar_qt.inverse(c)      # 1.1 N1: Night: HALT is inverse video, a block of the phosphor with its sign and word in the ground
        if inverse:fill = c['secondary'] if self.isDown() else c['accent_fill'];marks = dict(marks, HALT=c['on_accent'], HALT_HELD=c['on_accent'])
        p.setPen(QPen(QColor(c['stroke_strong'] if self.underMouse() else c['stroke']), 1));p.setBrush(QColor(fill))
        p.drawRoundedRect(r, tokens.RADIUS['control'], tokens.RADIUS['control'])
        side = round(h * 0.34);x = self.pad(h);cy = h / 2.0;path = QPainterPath()
        if self.held:      # ▶: go on, in the colour of what waits for the owner
            path.moveTo(QPointF(x, cy - side / 2));path.lineTo(QPointF(x + side * 0.9, cy));path.lineTo(QPointF(x, cy + side / 2))
        else:              # ▲: the stop sign, the live green (never red: it stops her, not the computer)
            path.moveTo(QPointF(x + side / 2, cy - side * 0.48));path.lineTo(QPointF(x + side, cy + side * 0.42));path.lineTo(QPointF(x, cy + side * 0.42))
        path.closeSubpath();p.setPen(Qt.NoPen);p.setBrush(QColor(marks['HALT_HELD'] if self.held else marks['HALT']));p.drawPath(path)
        font = self.bar_font(h);p.setFont(font);p.setPen(QColor(c['on_accent'] if inverse else c['text']))      # 1.1 N1
        tx = x + side + 6;p.drawText(QRectF(tx, 0, w - tx - 4, h), Qt.AlignLeft | Qt.AlignVCenter, self.text())
        if self.held:      # held: a short mark under the word (the shape, not only the colour)
            fm = QFontMetricsF(font);p.fillRect(QRectF(tx, cy + fm.ascent() / 2 + 3, fm.horizontalAdvance(self.text()), 2), QColor(marks['HALT_HELD']))
        p.end()


class KasSlot(QWidget):
    """The bar's kas slot: her chip, then HALT beside her name."""

    def __init__(self, bar):
        super().__init__(bar);self.bar = bar;self.ctl = controller(bar.host);self.setAccessibleName('Kasandra and HALT')
        self.chip = KasChip(self);self.halt = HaltOnBar(bar.host, self);self.halt.show()
        self.ctl.slot = self
        QTimer.singleShot(0, self.ctl.adopt_halt)

    def bar_width(self, h):
        return self.chip.natural(h) + 2 + self.halt.need(h)

    def resizeEvent(self, event):
        self.lay()

    def lay(self):
        h = self.height();cw = self.chip.natural(h)
        self.chip.setGeometry(0, 0, cw, h);self.halt.setGeometry(cw + 2, 0, self.halt.need(h), h)

    def refresh(self):
        """Her state changed: the chip's width follows its word (the bar lays its slots out again)."""
        try:
            if self.width() != self.bar_width(self.height() or bar_qt.SHORT):self.bar.arrange()
            else:self.lay()
            self.chip.update()
        except RuntimeError:
            pass


# ---- her panel ------------------------------------------------------------------------------------------------------------------
def mark_everywhere(window):
    """Her panel and her cards stand on every desktop, as the bar does (_NET_WM_DESKTOP all). False where X does not answer."""
    if QGuiApplication.platformName() != 'xcb':return False
    try:
        from . import system_dock_qt as sd
        from . import windows_x11 as wx
        xb = wx.XlibBackend()
    except Exception:  # noqa: BLE001 - not on X
        return False
    try:
        sd._declare(xb.x)
        with xb.calls():sd._put(xb, int(window), '_NET_WM_DESKTOP', wx.XA_CARDINAL, [sd.ALL_DESKTOPS])
        return True
    except Exception:  # noqa: BLE001
        return False
    finally:
        xb.close_display()


class KasPanel(QWidget):
    """Her panel: a window of its own at the screen's right edge, holding her column while it is open (or always, when she is
    not docked in Graphite). Esc closes it."""

    def __init__(self, ctl):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.ctl = ctl;self.opened = False;self.marked = False
        self.setObjectName('KasPanel');self.setWindowTitle('Graphite · Kasandra');self.setAccessibleName('Her panel')
        self.setAttribute(Qt.WA_X11NetWmWindowTypeUtility, True)
        box = QVBoxLayout(self);box.setContentsMargins(1, 0, 0, 0);box.setSpacing(0)
        self.anim = QPropertyAnimation(self, b'pos', self);self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.anim.finished.connect(self.slid)
        self.esc = QShortcut(QKeySequence(Qt.Key_Escape), self);self.esc.activated.connect(lambda: self.ctl.close_panel())

    def hold(self, pane):
        """Her column comes in: the window's own look (its style sheet, palette and type) comes with it."""
        host = self.ctl.host
        sheet = host.styleSheet()
        if self.styleSheet() != sheet:self.setStyleSheet(sheet)
        self.setPalette(host.palette());self.setFont(host.font())
        pane.setParent(self);self.layout().addWidget(pane, 1);pane.show()

    def band(self):
        """(open rect, closed x): 380 px at the right edge of the screen, from its top to the bar."""
        host = self.ctl.host;bar = getattr(host, 'graphite_bar', None)
        screen = (host.screen() if host is not None else None) or QGuiApplication.primaryScreen()
        g = screen.geometry()
        bottom = bar.y() if bar is not None and bar.isVisible() else g.y() + g.height()
        rect = QRect(g.x() + g.width() - PANEL_WIDTH, g.y(), PANEL_WIDTH, max(200, bottom - g.y()))
        return rect, g.x() + g.width()

    def slide_in(self):
        rect, off = self.band();self.opened = True;self.anim.stop()
        self.setFixedSize(rect.size())
        if not self.marked:self.marked = mark_everywhere(self.winId())
        if reduce_motion(self.ctl.host):
            self.move(rect.topLeft());self.show();self.raise_()
        else:
            self.move(off, rect.y());self.show();self.raise_()
            self.anim.setDuration(SLIDE_MS);self.anim.setStartValue(QPoint(off, rect.y()));self.anim.setEndValue(rect.topLeft());self.anim.start()
        self.activateWindow()
        return rect

    def slide_out(self):
        rect, off = self.band();self.opened = False;self.anim.stop()
        if reduce_motion(self.ctl.host) or not self.isVisible():
            self.hide();self.ctl.panel_gone();return
        self.anim.setDuration(SLIDE_MS);self.anim.setStartValue(self.pos());self.anim.setEndValue(QPoint(off, rect.y()));self.anim.start()

    def slid(self):
        if not self.opened:
            self.hide();self.ctl.panel_gone()

    def place_now(self):
        """The screen or the bar moved: the open panel follows its edge."""
        if self.opened and self.anim.state() != QPropertyAnimation.Running:
            rect, _ = self.band();self.setFixedSize(rect.size());self.move(rect.topLeft())

    def paintEvent(self, event):
        c = bar_qt.ink();p = QPainter(self);p.fillRect(self.rect(), QColor(c['surface']))
        p.fillRect(0, 0, 1, self.height(), QColor(c['stroke']));p.end()


# ---- her card -------------------------------------------------------------------------------------------------------------------
class CardRow(QFrame):
    """One thing that waits, on the card: its shape and word, what it is about, its words (a grant's whole), its one press."""

    def __init__(self, card):
        super().__init__(card);self.card = card;self.fn = None;self.item = None
        self.setObjectName('KasCardRow')
        box = QVBoxLayout(self);box.setContentsMargins(10, 6, 8, 6);box.setSpacing(3)
        top = QHBoxLayout();top.setSpacing(6)
        from . import state_words as sw
        self.mark = sw.Mark('needs_word', None, 13);top.addWidget(self.mark, 0, Qt.AlignVCenter)
        self.word = QLabel();self.title = QLabel();self.title.setTextFormat(Qt.PlainText)
        top.addWidget(self.word);top.addWidget(self.title, 1);box.addLayout(top)
        self.words = QLabel();self.words.setWordWrap(True);self.words.setTextFormat(Qt.PlainText);box.addWidget(self.words)
        low = QHBoxLayout();low.setSpacing(0)
        self.press = QPushButton();self.press.setObjectName('KasCardPress');self.press.setFocusPolicy(Qt.NoFocus)
        self.press.setCursor(Qt.PointingHandCursor);self.press.clicked.connect(self.pressed)
        low.addWidget(self.press, 0, Qt.AlignLeft);low.addStretch(1);box.addLayout(low)

    def show_item(self, item):
        from . import state_words as sw
        key, title, words, press, fn, tip = item;c = bar_qt.ink()
        self.item = item;self.fn = fn
        self.mark.set(key, c['waiting']);self.word.setText(sw.word(key).upper() if key == 'held' else sw.word(key))
        self.word.setStyleSheet('color:%s;font-family:"%s";font-size:11px;font-weight:600;letter-spacing:1px;' % (c['waiting_text'], tokens.FONT['mono']))
        self.title.setText(title);self.title.setVisible(bool(title))
        self.title.setStyleSheet('color:%s;font-size:12px;' % c['secondary'])
        fm = QFontMetrics(self.title.font());self.title.setText(fm.elidedText(title, Qt.ElideRight, 200));self.title.setToolTip(title)
        self.words.setText(words);self.words.setVisible(bool(words));self.words.setStyleSheet('color:%s;font-size:13px;' % c['text'])
        self.press.setText(press);self.press.setToolTip(tip)
        self.setAccessibleName('%s: %s. %s' % (sw.word(key), title, words))

    def pressed(self):
        if self.fn is None or not self.card.awake():return      # deaf for its first half second
        self.card.carry(self.fn, self.press.text())


class WaitCard(QFrame):
    """What waits for the owner, risen from her chip above the bar: never takes the keys, deaf for its first half second."""

    def __init__(self, ctl):
        # never managed by the window manager (override-redirect), so no manager can give it the keys; above every app
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus | Qt.X11BypassWindowManagerHint)
        self.ctl = ctl;self.rows = [];self.signature = None;self.later = None;self.shown_at = 0.0;self.outcome_until = 0.0
        self.setObjectName('KasWaitCard');self.setWindowTitle('Graphite · Waits for you');self.setAccessibleName('Waits for you, from her chip');self.setToolTip(WORDS['card_tip'])
        for attr in (Qt.WA_ShowWithoutActivating, Qt.WA_X11DoNotAcceptFocus, Qt.WA_X11NetWmWindowTypeNotification):self.setAttribute(attr, True)
        self.setFocusPolicy(Qt.NoFocus);self.marked = False
        box = QVBoxLayout(self);box.setContentsMargins(12, 10, 12, 10);box.setSpacing(6)
        head = QHBoxLayout();head.setSpacing(6)
        from . import state_words as sw
        self.mark = sw.Mark('needs_word', None, 14);head.addWidget(self.mark, 0, Qt.AlignVCenter)
        self.head = QLabel();head.addWidget(self.head, 1);box.addLayout(head)
        self.list = QVBoxLayout();self.list.setSpacing(6);box.addLayout(self.list)
        self.more = QLabel();self.more.hide();box.addWidget(self.more)
        self.said = QLabel();self.said.setWordWrap(True);self.said.setTextFormat(Qt.PlainText);self.said.hide();box.addWidget(self.said)
        foot = QHBoxLayout();foot.setSpacing(8)
        self.panel_link = QPushButton(WORDS['panel_link']);self.later_button = QPushButton(WORDS['later'])
        for b in (self.panel_link, self.later_button):b.setFocusPolicy(Qt.NoFocus);b.setFlat(True);b.setCursor(Qt.PointingHandCursor)
        self.panel_link.clicked.connect(self.open_panel);self.later_button.clicked.connect(self.put_off)
        foot.addWidget(self.panel_link);foot.addStretch(1);foot.addWidget(self.later_button);box.addLayout(foot)
        self.anim = QPropertyAnimation(self, b'pos', self);self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.wake = QTimer(self);self.wake.setSingleShot(True);self.wake.timeout.connect(self.woken)
        self.restyle()

    def restyle(self):
        c = bar_qt.ink()
        self.setStyleSheet(
            'QFrame#KasWaitCard {background:%s; border:1px solid %s; border-radius:%dpx;}'
            ' QFrame#KasCardRow {background:%s; border:1px solid %s; border-left:3px solid %s; border-radius:6px;}'
            ' QLabel {background:transparent; border:0;}'
            ' QPushButton#KasCardPress {background:%s; color:%s; border:0; border-radius:6px; padding:5px 12px; font-weight:600;}'
            ' QPushButton#KasCardPress:hover {background:%s;}'
            ' QPushButton#KasCardPress:disabled {background:%s; color:%s;}'
            ' QPushButton[flat="true"] {color:%s; background:transparent; border:0; padding:2px 4px;}'
            ' QPushButton[flat="true"]:hover {text-decoration:underline;}' % (
                c['surface'], c['stroke_strong'], tokens.RADIUS['toast'], c['surface'], c['stroke'], c['waiting'],
                c['accent_fill'], c['on_accent'], c['accent'], c['raised'], c['disabled'], c['accent_text']))
        self.head.setStyleSheet('color:%s;font-family:"%s";font-size:12px;font-weight:600;letter-spacing:1px;' % (c['waiting_text'], tokens.FONT['mono']))
        self.more.setStyleSheet('color:%s;font-size:12px;' % c['secondary']);self.said.setStyleSheet('color:%s;font-size:13px;' % c['text'])
        self.mark.set('needs_word', c['waiting'])

    # -- hearing
    def awake(self):
        return time.monotonic() - self.shown_at >= DEAF_MS / 1000.0

    def woken(self):
        for row in self.rows:row.press.setEnabled(True)

    # -- what it shows
    def show_items(self, found):
        from .waits_qt import WORDS as WAITS
        from .kas_voice import say as her
        self.restyle();self.said.hide()
        while len(self.rows) < min(len(found), CARD_MOST):
            row = CardRow(self);self.rows.append(row);self.list.addWidget(row)
        for i, row in enumerate(self.rows):
            if i < min(len(found), CARD_MOST):row.show_item(found[i]);row.show()
            else:row.hide()
        hidden = max(0, len(found) - CARD_MOST)
        self.more.setText(her('card_more', count=hidden) if hidden else '');self.more.setVisible(bool(hidden))
        self.head.setText(WAITS['head_count'].format(count=len(found)) if len(found) > 1 else WAITS['head'])
        self.later_button.show()

    def width_for(self):
        bar = getattr(self.ctl.host, 'graphite_bar', None)
        return 380 if bar is not None and bar.height() >= bar_qt.TALL else 340

    def rise(self):
        """Above her chip, its right edge on the chip's right edge (inside the screen), 6 px over the bar; it rises 8 px."""
        bar = getattr(self.ctl.host, 'graphite_bar', None);slot = self.ctl.slot
        self.setFixedWidth(self.width_for());self.adjustSize()
        layout = self.layout();self.setFixedHeight(layout.totalHeightForWidth(self.width()) if layout.hasHeightForWidth() else layout.sizeHint().height())
        screen = (bar.screen() if bar is not None else None) or QGuiApplication.primaryScreen();g = screen.geometry()
        if bar is not None and slot is not None:
            right = slot.mapToGlobal(QPoint(slot.width(), 0)).x();top = bar.mapToGlobal(QPoint(0, 0)).y()
        else:
            right = g.x() + g.width() - 8;top = g.y() + g.height()
        x = max(g.x() + 8, min(right, g.x() + g.width() - 8) - self.width());y = top - self.height() - 6
        was = self.isVisible()
        if not self.marked:self.marked = mark_everywhere(self.winId())
        if was:
            self.anim.stop();self.move(x, y);return QRect(x, y, self.width(), self.height())
        self.shown_at = time.monotonic()
        for row in self.rows:row.press.setEnabled(False)
        self.wake.start(DEAF_MS)
        if reduce_motion(self.ctl.host):
            self.move(x, y);self.show()
        else:
            self.move(x, y + RISE_PX);self.show()
            self.anim.setDuration(RISE_MS);self.anim.setStartValue(QPoint(x, y + RISE_PX));self.anim.setEndValue(QPoint(x, y));self.anim.start()
        self.raise_()
        return QRect(x, y, self.width(), self.height())

    # -- the presses
    def carry(self, fn, words):
        """The row's own press (waits_qt's: HerColumn.take_step or show_journal), then what she said about it, here, for a few
        seconds (her column is not in sight)."""
        column = self.ctl.column();said = []
        original = getattr(column, 'say_words', None)
        if column is not None and original is not None:
            column.say_words = lambda w, original=original: (said.append(w), original(w))
        try:
            fn()
        finally:
            if column is not None and original is not None:
                try:del column.say_words
                except AttributeError:pass
        try:
            from . import floor
            if column is not None:floor.column_soon(column)      # read again off the window's thread, as the band's press does
        except Exception:  # noqa: BLE001
            pass
        self.signature = None
        if said:
            from .her_column_qt import plain
            for row in self.rows:row.hide()
            self.more.hide();self.later_button.hide();self.said.setText(plain(said[-1]));self.said.show()
            self.outcome_until = time.monotonic() + 5.0;self.rise()
        else:
            self.hide()
        return said

    def open_panel(self):
        self.hide();self.ctl.open_panel()

    def put_off(self):
        """Later: the card goes until what waits changes (it still waits in her panel, and her chip still says so)."""
        self.later = self.signature;self.hide()


# ---- the controller -------------------------------------------------------------------------------------------------------------
def signature(found):
    return tuple((k, t, w, p) for k, t, w, p, _, _ in found)


class KasBar(QObject):
    """host.kas_bar: her chip's slot, her panel, her card and the setting, for one window."""

    def __init__(self, host):
        super().__init__(host);self.host = host;self.slot = None;self.panel = None;self.card = None;self.away = None
        self.home = None;self.last_menu = None;self.docked = read_settings()['docked'];self.halt_adopted = False
        self.timer = QTimer(self);self.timer.setInterval(TICK_MS);self.timer.timeout.connect(self.tick)
        self.pause = QShortcut(QKeySequence(Qt.Key_Pause), host);self.pause.setContext(Qt.ApplicationShortcut)
        self.pause.activated.connect(self.pause_key)
        app = QGuiApplication.instance()
        if app is not None:app.focusWindowChanged.connect(self.focus_moved)
        dock = getattr(host, 'sim_dock', None)
        if dock is not None:dock.installEventFilter(self)

    # -- reading
    def column(self):
        return getattr(self.host, 'her_column', None)

    def waiting(self):
        """What waits for the owner now (waits_qt.items: a read of her column's rows, nothing written)."""
        column = self.column()
        if column is None:return []
        band = getattr(column, 'waits', None)
        if band is not None and getattr(band, 'shown', None) is not None and band.isVisible():return list(band.shown)
        try:
            from .waits_qt import items
            return items(column)
        except Exception:  # noqa: BLE001 - the chip is whole without it
            return []

    def standing(self):
        bar = getattr(self.host, 'graphite_bar', None)
        return bar is not None and self.slot is not None and bar.slot('kas') is self.slot

    def panel_open(self):
        return self.panel is not None and self.panel.opened

    def pane_home(self):
        pane = getattr(self.host, 'right_pane', None)
        return pane is not None and self.home is not None and pane.parentWidget() is self.home[0]

    def graphite_in_front(self):
        host = self.host
        try:return host.isActiveWindow() and not host.isMinimized() and host.isVisible()
        except RuntimeError:return False

    def in_sight(self):
        """Her column is in sight: her panel is open, or she is docked in Graphite and Graphite's window is the one in front."""
        if self.panel_open():return True
        pane = getattr(self.host, 'right_pane', None)
        shown = pane is None or pane.isVisible()      # the owner may have put Graphite's right side away
        return self.docked and self.graphite_in_front() and (self.home is None or self.pane_home()) and shown

    # -- the bar's slot stands
    def stood(self):
        """The bar stands with her chip: she reads her work while her column is out of sight (her chip says it above every
        app); she is put where the setting says; the card follows what waits."""
        column = self.column()
        if column is not None:column.reads_unseen = True      # floor.column_tick (1.1 B3)
        if not self.docked:self.undock()
        self.timer.start();self.tick()

    def adopt_halt(self):
        """HALT on the bar: once the bar stands with it, the head's HALT goes (one place for each thing); halt.py's own refresh
        after a press then reads the bar's button (shell2.top.halt). True when it was moved."""
        if self.slot is None:return False
        bar = getattr(self.host, 'graphite_bar', None)
        if bar is None or not getattr(bar, 'standing', False) or bar.slot('kas') is not self.slot:
            tries = getattr(self, '_halt_tries', 0)
            if tries < 40 and not getattr(self.host, '_closing', False):
                self._halt_tries = tries + 1;QTimer.singleShot(150, self.adopt_halt)
            return False
        top = getattr(getattr(self.host, 'shell2', None), 'top', None)
        if top is not None:
            old = getattr(top, 'halt', None)
            if old is not None and old is not self.slot.halt:
                try:old.timer.stop();old.hide();old.setParent(None);old.deleteLater()
                except (RuntimeError, AttributeError):pass
            top.halt = self.slot.halt
        self.halt_adopted = True
        if not self.timer.isActive():self.stood()
        return True

    # -- the presses
    def toggle(self):
        """Her chip's press: her panel goes when it is open; docked and with Graphite in front, her column is shown where it
        stands; else her panel slides in."""
        if self.panel_open():return self.close_panel()
        if self.docked and self.graphite_in_front() and (self.home is None or self.pane_home()):return self.show_column()
        return self.open_panel()

    def show_column(self):
        try:
            self.host.shell2.show_slate_face()
            edit = getattr(getattr(self.column(), 'ask_line', None), 'edit', None)
            if edit is not None:edit.setFocus()
        except Exception:  # noqa: BLE001
            pass
        return 'docked'

    def ensure_panel(self):
        if self.panel is None:self.panel = KasPanel(self)
        return self.panel

    def take_pane(self):
        """Her column (the right pane) comes out of Graphite's window into her panel; a line of words keeps its place."""
        pane = getattr(self.host, 'right_pane', None);panel = self.ensure_panel()
        if pane is None:return False
        if pane.parentWidget() is panel:return True
        holder = pane.parentWidget();lay = holder.layout() if holder is not None else None
        if lay is None:return False
        index = lay.indexOf(pane);self.home = (holder, index)
        lay.removeWidget(pane)
        if self.away is None:
            from .kas_voice import say as her
            self.away = QLabel(her('panel_away'));self.away.setWordWrap(True);self.away.setAlignment(Qt.AlignCenter)
            self.away.setObjectName('KasAway');self.away.setContentsMargins(16, 16, 16, 16)
        lay.insertWidget(max(0, index), self.away, 1);self.away.show()
        panel.hold(pane)
        return True

    def give_pane(self):
        """Her column goes back to its place in Graphite's window."""
        pane = getattr(self.host, 'right_pane', None)
        if pane is None or self.home is None:return False
        holder, index = self.home
        if pane.parentWidget() is holder:return True
        lay = holder.layout()
        if self.away is not None:
            lay.removeWidget(self.away);self.away.hide()
        if self.panel is not None:self.panel.layout().removeWidget(pane)
        pane.setParent(holder);lay.insertWidget(max(0, index), pane, 1);pane.show()
        try:
            from . import desk_qt
            QTimer.singleShot(0, lambda: desk_qt.apply(self.host))
        except Exception:  # noqa: BLE001
            pass
        return True

    def open_panel(self):
        if not self.take_pane():return None
        if self.card is not None:self.card.hide()
        rect = self.panel.slide_in()
        edit = getattr(getattr(self.column(), 'ask_line', None), 'edit', None)
        if edit is not None:QTimer.singleShot(0, edit.setFocus)
        self.repaint_chip()
        return rect

    def close_panel(self):
        if self.panel is None or not self.panel.opened:return False
        self.panel.slide_out();self.repaint_chip()
        return True

    def panel_gone(self):
        """The panel has slid out: docked, her column goes home."""
        if self.docked:self.give_pane()
        self.repaint_chip();self.tick()

    def set_docked(self, on):
        """"Kas docked in Graphite": on, her column stands at the right of Graphite's window as in 1.0 (her panel slides over
        other apps); off, it lives in her panel only. Kept in ~/.config/graphite/kas_bar.json."""
        self.docked = bool(on);write_settings(docked=self.docked)
        if self.docked:
            if not self.panel_open():self.give_pane()
            dock = getattr(self.host, 'sim_dock', None)
            if dock is not None:dock.show()
        else:
            self.undock()
        self.repaint_chip();self.tick()
        return self.docked

    def undock(self):
        self.take_pane()
        dock = getattr(self.host, 'sim_dock', None)
        if dock is not None:dock.hide()

    def pause_key(self):
        """The Pause key in Graphite presses HALT; it never presses RESUME (RESUME is a press, never a key)."""
        button = self.slot.halt if self.slot is not None else getattr(getattr(getattr(self.host, 'shell2', None), 'top', None), 'halt', None)
        if button is None:return None
        if button.held:
            from .kas_voice import say as her
            try:self.host.statusBar().showMessage(her('pause_held'), 6000)
            except (AttributeError, RuntimeError):pass
            return False
        button.act();return True

    # -- following
    def repaint_chip(self):
        if self.slot is not None:
            try:self.slot.refresh()
            except RuntimeError:self.slot = None

    def tick(self):
        """Every second while the bar stands: the chip's word, and the card (what waits, when her column is out of sight)."""
        if getattr(self.host, '_closing', False):self.timer.stop();return
        self.repaint_chip()
        found = self.waiting() if self.slot is not None else []
        card = self.card
        if card is not None and time.monotonic() < card.outcome_until and card.isVisible():return      # her answer to a card's press, for a moment
        if not found or self.in_sight():
            if card is not None:card.hide();card.later = None if not found else card.later
            return
        sign = signature(found)
        if card is None:card = self.card = WaitCard(self)
        if card.later is not None and card.later == sign:return      # put off until what waits changes
        if sign != card.signature or not card.isVisible():
            card.signature = sign;card.show_items(found);card.rise()

    def focus_moved(self, window):
        """Docked: when Graphite's own window comes in front, her open panel goes, and her column is back in its place there."""
        try:
            if window is not None and self.docked and self.panel_open() and window is self.host.windowHandle():self.close_panel()
        except RuntimeError:
            pass

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Show and obj is getattr(self.host, 'sim_dock', None) and not self.docked and self.standing():
            QTimer.singleShot(0, obj.hide)      # not docked: the right of Graphite's window is the work's (her panel holds her column)
        return False

    def status(self):
        return dict(standing=self.standing(), docked=self.docked, panel_open=self.panel_open(), pane_home=self.pane_home() if self.home else True,
                    card=bool(self.card is not None and self.card.isVisible()), halt_on_bar=self.halt_adopted,
                    chip=chip_state(self.column(), len(self.waiting()))[1])


def controller(host):
    """host.kas_bar, made once."""
    ctl = getattr(host, 'kas_bar', None)
    if ctl is None:
        ctl = KasBar(host);host.kas_bar = ctl
    return ctl


def install(host):
    """shell2, before the bar: her chip and HALT fill the bar's kas slot wherever the bar stands (bar_qt.register_slot). Without
    the bar nothing here is made, and her column and HALT stay where 1.0 put them."""
    controller(host)
    bar_qt.register_slot('kas', KasSlot)
    return host.kas_bar
