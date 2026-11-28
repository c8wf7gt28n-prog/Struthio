"""Graphite 1.1 B2 · Start and the line: Start rises from the bar's Start slot (and on the Windows key); the line on the bar
finds and does, each row saying what Enter will do.

PLAN_1.1.md, B2; the design direction's section 1 (Calm's graft); the proposal "Familiar", section 6. This fills two of
B1's slots through bar_qt.register_slot, without editing the bar:

  start   Graphite's mark and "Start". A press, or the Windows key (graphite-do start, from any app), raises Start above the
          bar with the cursor already in the line: apps by kind (the apps' own desktop entries, as 1.0's Apps reads them;
          what the owner pinned first), recent files, and power: Lock, Suspend, Log out, Restart, Shut down, through 1.0's
          leave group (session_power: Log out, Restart and Shut down ask first, name the apps still open and ask each to
          close; nothing is ever killed). Typing turns Start into the line's rows. Esc closes it, as does the Windows key.
  line    the field's shape on the bar. A press (or Win+R, Win+S) raises the line's rows above it, the cursor in the line.

The rows are line_finder's: a sum (exact, the one maths core), an address, DOS words (the Debian command beside), apps,
settings, files, the desk, commands, operations by name, a program for the Terminal, and Ask Kasandra. The chosen row's
verb is what Enter does, and the line under the rows says it in words ("Enter: Open Firefox"). Whatever is summoned leaves
when done: a row done closes Start, except a sum, whose answer goes into the line (and is copied) so the sum can go on.

Nothing here acts without the owner's press: typing only reads. Asking Kasandra gives her the words in her column, where
she proposes and the owner decides. When the bar does not stand, Start rises at the bottom left of the screen.
"""
from __future__ import annotations

import threading
import time

from PySide6.QtCore import QPointF, QRect, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QGuiApplication, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (QAbstractButton, QAbstractItemView, QApplication, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QStackedWidget, QStyle, QStyledItemDelegate, QVBoxLayout, QWidget)

from . import bar_qt
from . import design_tokens as tokens
from . import line_finder as lf

PROMPT = 'Type to find or do: apps, files, settings, sums, commands, or ask Kasandra'
START_TIP = 'Start (the Windows key): apps by kind, recent files and power. Type to find or do anything.'
LINE_TIP = 'The line (Win+R): it finds and does: apps, files, settings, commands, sums, Ask Kasandra.\nEach row says what Enter will do.'
EMPTY_RECENT = 'Nothing opened yet. The files you open appear here.'
EMPTY_APPS = 'No apps were found in the desktop entries.'
HINTS = (('firefox', 'an app by its name or what it does'), ('report', 'a file, a folder or something on the desk'),
         ('12 * 7', 'a sum, answered exactly'), ('dir', 'DOS words: run in the Terminal, the Debian word beside'),
         ('?what is on today', 'a request: Ask Kasandra'))
REOPEN_MS = 300                      # a press on the slot that just closed Start (the popup's own outside press) does not reopen it
ROLE = Qt.UserRole + 1


# ---- sizes and inks ---------------------------------------------------------------------------------------------------------------
def tall_screen(screen=None):
    g = (screen or QGuiApplication.primaryScreen()).geometry()
    return bar_qt.height_for(g.width(), g.height()) >= bar_qt.TALL


def panel_size(mode, screen=None):
    tall = tall_screen(screen)
    if mode == 'start':return QSize(720, 600) if tall else QSize(640, 520)
    return QSize(680, 460) if tall else QSize(600, 420)


def font(px, weight=None, caps=False):
    f = QFont(tokens.face());f.setPixelSize(px)      # 1.1 N1: fixed-width in Night
    if weight is not None:f.setWeight(weight)
    if caps:f.setCapitalization(QFont.AllUppercase);f.setLetterSpacing(QFont.AbsoluteSpacing, 0.4)
    return f


def ink():
    return bar_qt.ink()


# ---- the glyphs: a shape for every kind of row (the kind is also said in words, in the row's second line) ----------------------
def paint_glyph(p, rect, key, colour, accent=None):
    """A small drawn shape in `rect` (QRectF): sum, address, terminal, command, settings, file, folder, desk, ask, app, and the
    power row's lock, suspend, logout, restart, shutdown."""
    p.save();p.setRenderHint(QPainter.Antialiasing)
    s = min(rect.width(), rect.height());r = QRectF(rect.center().x() - s / 2, rect.center().y() - s / 2, s, s).adjusted(s * .12, s * .12, -s * .12, -s * .12)
    pen = QPen(QColor(colour), max(1.3, s / 14));pen.setCapStyle(Qt.RoundCap);pen.setJoinStyle(Qt.RoundJoin);p.setPen(pen);p.setBrush(Qt.NoBrush)
    cx, cy, w, h = r.center().x(), r.center().y(), r.width(), r.height()
    if key == 'sum':
        p.drawRoundedRect(r, w * .18, w * .18)
        for dy in (-.12, .12):p.drawLine(QPointF(cx - w * .24, cy + h * dy), QPointF(cx + w * .24, cy + h * dy))
    elif key == 'address':
        p.drawEllipse(r);p.drawEllipse(QRectF(cx - w * .22, r.top(), w * .44, h));p.drawLine(QPointF(r.left(), cy), QPointF(r.right(), cy))
    elif key == 'terminal':
        p.drawRoundedRect(r, w * .14, w * .14)
        p.drawPolyline([QPointF(r.left() + w * .2, cy - h * .16), QPointF(r.left() + w * .38, cy), QPointF(r.left() + w * .2, cy + h * .16)])
        p.drawLine(QPointF(cx, cy + h * .2), QPointF(r.right() - w * .18, cy + h * .2))
    elif key == 'command':
        p.drawPolyline([QPointF(cx - w * .18, r.top() + h * .18), QPointF(cx + w * .16, cy), QPointF(cx - w * .18, r.bottom() - h * .18)])
    elif key == 'settings':
        p.drawEllipse(QPointF(cx, cy), w * .2, w * .2)
        for n in range(8):
            import math
            a = n * math.pi / 4;p.drawLine(QPointF(cx + math.cos(a) * w * .32, cy + math.sin(a) * w * .32), QPointF(cx + math.cos(a) * w * .46, cy + math.sin(a) * w * .46))
    elif key == 'file':
        fold = w * .28;path = QPainterPath();x0, x1 = cx - w * .32, cx + w * .32
        path.moveTo(x0, r.top());path.lineTo(x1 - fold, r.top());path.lineTo(x1, r.top() + fold);path.lineTo(x1, r.bottom());path.lineTo(x0, r.bottom());path.closeSubpath()
        p.drawPath(path);p.drawPolyline([QPointF(x1 - fold, r.top()), QPointF(x1 - fold, r.top() + fold), QPointF(x1, r.top() + fold)])
    elif key == 'folder':
        path = QPainterPath();top = r.top() + h * .18
        path.moveTo(r.left(), r.bottom() - h * .1);path.lineTo(r.left(), top);path.lineTo(r.left() + w * .36, top);path.lineTo(r.left() + w * .46, top + h * .12)
        path.lineTo(r.right(), top + h * .12);path.lineTo(r.right(), r.bottom() - h * .1);path.closeSubpath();p.drawPath(path)
    elif key == 'desk':
        p.drawRect(r.adjusted(0, h * .14, 0, -h * .06));p.drawLine(QPointF(cx, r.top()), QPointF(cx, r.top() + h * .14))
        p.drawLine(QPointF(r.left() + w * .2, cy), QPointF(r.right() - w * .2, cy));p.drawLine(QPointF(r.left() + w * .2, cy + h * .18), QPointF(cx, cy + h * .18))
    elif key == 'ask':
        path = QPainterPath();body = r.adjusted(0, 0, 0, -h * .2);path.addRoundedRect(body, w * .2, w * .2);p.drawPath(path)
        p.drawPolyline([QPointF(r.left() + w * .26, body.bottom()), QPointF(r.left() + w * .22, r.bottom()), QPointF(r.left() + w * .46, body.bottom())])
        p.setBrush(QColor(accent or colour))
        for dx in (-.2, 0, .2):p.drawEllipse(QPointF(cx + w * dx, body.center().y()), w * .04, w * .04)
    elif key == 'lock':
        body = QRectF(r.left() + w * .14, cy - h * .04, w * .72, h * .5);p.drawRoundedRect(body, w * .08, w * .08)
        p.drawArc(QRectF(cx - w * .22, r.top() + h * .02, w * .44, h * .6), 0, 180 * 16);p.drawLine(QPointF(cx - w * .22, r.top() + h * .32), QPointF(cx - w * .22, body.top()))
        p.drawLine(QPointF(cx + w * .22, r.top() + h * .32), QPointF(cx + w * .22, body.top()))
    elif key == 'suspend':
        path = QPainterPath();path.addEllipse(r.adjusted(w * .1, h * .1, -w * .1, -h * .1))
        bite = QPainterPath();bite.addEllipse(r.adjusted(w * .34, -h * .04, w * .16, -h * .24));p.drawPath(path.subtracted(bite))
    elif key == 'logout':
        p.drawPolyline([QPointF(cx, r.top() + h * .1), QPointF(r.left() + w * .1, r.top() + h * .1), QPointF(r.left() + w * .1, r.bottom() - h * .1), QPointF(cx, r.bottom() - h * .1)])
        p.drawLine(QPointF(cx - w * .1, cy), QPointF(r.right(), cy));p.drawPolyline([QPointF(r.right() - w * .18, cy - h * .18), QPointF(r.right(), cy), QPointF(r.right() - w * .18, cy + h * .18)])
    elif key == 'restart':
        p.drawArc(r.adjusted(w * .08, h * .08, -w * .08, -h * .08), 110 * 16, 300 * 16)
        tip = QPointF(cx - w * .14, r.top() + h * .1);p.drawPolyline([tip + QPointF(-w * .16, -h * .08), tip, tip + QPointF(-w * .04, h * .18)])
    elif key == 'shutdown':
        p.drawArc(r.adjusted(w * .08, h * .12, -w * .08, -h * .04), 120 * 16, 300 * 16);p.drawLine(QPointF(cx, r.top()), QPointF(cx, cy))
    else:      # an app without a picture of its own: a tile with its first letter
        p.drawRoundedRect(r, w * .22, w * .22)
        if key:
            p.setFont(font(max(9, int(s * .42)), QFont.DemiBold));p.drawText(r, Qt.AlignCenter, key[:1].upper())
    p.restore()


_PICTURES = {}


def picture(path):
    """An app's own icon, read once."""
    if not path:return None
    if path not in _PICTURES:
        icon = QIcon(path);_PICTURES[path] = None if icon.isNull() else icon
    return _PICTURES[path]


# ---- the rows ---------------------------------------------------------------------------------------------------------------------
class RowDelegate(QStyledItemDelegate):
    """One row: its shape (or the app's own picture), its title, what it is in words, and at the right the verb that says what
    Enter does on it (filled on the chosen row, with a rule at its left edge: shape and words, not colour alone)."""

    def __init__(self, view):
        super().__init__(view);self.view = view

    def sizeHint(self, option, index):
        row = index.data(ROLE)
        if isinstance(row, str):return QSize(10, 26 if row else 10)
        return QSize(10, self.view.row_height)

    def paint(self, p, option, index):
        c = ink();row = index.data(ROLE);r = QRectF(option.rect)
        p.save();p.setRenderHint(QPainter.Antialiasing)
        if isinstance(row, str):      # a section's heading, or a hairline before the fixed last rows
            if row:
                p.setFont(font(tokens.TYPE['caption'][0], QFont.Medium, caps=True));p.setPen(QColor(c['tertiary']))
                p.drawText(r.adjusted(12, 6, -12, 0), Qt.AlignLeft | Qt.AlignVCenter, row)
            else:
                p.fillRect(QRectF(r.left() + 12, r.center().y(), r.width() - 24, 1), QColor(c['hairline']))
            p.restore();return
        chosen = bool(option.state & QStyle.State_Selected)
        ground = r.adjusted(4, 1, -4, -1)
        if chosen:
            bar_qt.plate(p, ground, c['selection'], tokens.RADIUS['row'])
            p.setPen(Qt.NoPen);p.setBrush(QColor(c['accent']));p.drawRoundedRect(QRectF(ground.left(), ground.top() + 6, 3, ground.height() - 12), 1.5, 1.5)
        elif option.state & QStyle.State_MouseOver:
            bar_qt.plate(p, ground, c['hover'], tokens.RADIUS['row'])
        side = min(24, int(r.height() * .55));icon_box = QRectF(r.left() + 14, r.center().y() - side / 2, side, side)
        unavailable = row.kind == 'app' and not row.extra.get('available', True)
        tone = c['disabled'] if unavailable else c['secondary']
        pic = picture(row.icon) if row.kind == 'app' else None
        if pic is not None:pic.paint(p, icon_box.toRect(), Qt.AlignCenter, QIcon.Disabled if unavailable else QIcon.Normal)
        else:paint_glyph(p, icon_box, row.icon if row.icon in KINDS else (row.title if row.kind in ('app', 'hint') else row.icon), tone, c['accent'])
        verb = row.verb if row.kind != 'hint' else 'Try'
        shown = self.view.every_verb or chosen or bool(option.state & QStyle.State_MouseOver)
        vf = font(tokens.TYPE['footnote'][0], QFont.DemiBold);vw = QFontMetrics(vf).horizontalAdvance(verb) + 20
        pill = QRectF(r.right() - 12 - vw, r.center().y() - 11, vw, 22) if shown else QRectF(r.right() - 4, r.center().y(), 0, 0)
        x = icon_box.right() + 12;text_w = pill.left() - 10 - x
        title_f = font(tokens.TYPE['body'][0] + (1 if self.view.row_height >= 44 else 0), QFont.Medium)
        detail_f = font(tokens.TYPE['footnote'][0])
        title = row.title + (('   ' + row.beside) if row.beside else '')
        p.setFont(title_f);p.setPen(QColor(c['disabled'] if unavailable else c['text']))
        fm = QFontMetrics(title_f);line_h = fm.height();detail_h = QFontMetrics(detail_f).height()
        top = r.center().y() - (line_h + detail_h) / 2
        if row.beside:      # the other name beside it, quieter: the Debian command, or the Windows word
            head = fm.elidedText(row.title, Qt.ElideRight, int(text_w * .62))
            p.drawText(QRectF(x, top, text_w, line_h), Qt.AlignLeft | Qt.AlignVCenter, head)
            bx = x + fm.horizontalAdvance(head) + 10;p.setFont(font(tokens.TYPE['footnote'][0], QFont.Medium));p.setPen(QColor(c['accent_text']))
            p.drawText(QRectF(bx, top, max(0, x + text_w - bx), line_h), Qt.AlignLeft | Qt.AlignVCenter,
                       QFontMetrics(p.font()).elidedText(row.beside, Qt.ElideRight, int(max(0, x + text_w - bx))))
        else:
            p.drawText(QRectF(x, top, text_w, line_h), Qt.AlignLeft | Qt.AlignVCenter, fm.elidedText(title, Qt.ElideRight, int(text_w)))
        detail = row.detail + ((' · cannot start here: ' + row.extra.get('reason', '')) if unavailable and row.extra.get('reason') else '')
        p.setFont(detail_f);p.setPen(QColor(c['secondary']))
        p.drawText(QRectF(x, top + line_h, text_w, detail_h), Qt.AlignLeft | Qt.AlignVCenter, QFontMetrics(detail_f).elidedText(detail, Qt.ElideRight, int(text_w)))
        p.setFont(vf)
        if not shown:
            p.restore();return
        if chosen:
            p.setPen(Qt.NoPen);p.setBrush(QColor(c['accent_fill']));p.drawRoundedRect(pill, 11, 11);p.setPen(QColor(c['on_accent']))
        else:
            p.setPen(QPen(QColor(c['stroke']), 1));p.setBrush(Qt.NoBrush);p.drawRoundedRect(pill.adjusted(.5, .5, -.5, -.5), 11, 11);p.setPen(QColor(c['secondary']))
        p.drawText(pill, Qt.AlignCenter, verb)
        p.restore()


KINDS = ('sum', 'address', 'terminal', 'command', 'settings', 'file', 'folder', 'desk', 'ask', 'lock', 'suspend', 'logout', 'restart', 'shutdown')


class RowList(QListWidget):
    """Rows under the line (or Start's apps and recent files). It never takes the keyboard: the line keeps it, and Up, Down and
    Enter move and take the chosen row here."""
    chosen = Signal(object)

    def __init__(self, parent, row_height):
        super().__init__(parent);self.row_height = row_height;self.rows = [];self.every_verb = True      # Start's own lists: the verb on the chosen row
        self.setFocusPolicy(Qt.NoFocus);self.setMouseTracking(True);self.viewport().setMouseTracking(True);self.setUniformItemSizes(False)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel);self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setItemDelegate(RowDelegate(self));self.setFrameShape(QFrame.NoFrame)
        c = ink();self.setStyleSheet('QListWidget {background:transparent; border:0; outline:0;}')
        self.itemEntered.connect(lambda item: self.setCurrentItem(item) if isinstance(item.data(ROLE), lf.Row) else None)
        self.itemClicked.connect(lambda item: self.chosen.emit(item.data(ROLE)) if isinstance(item.data(ROLE), lf.Row) else None)
        self._c = c

    def show_rows(self, rows, headings=True):
        """Rows with a heading before each section, and a hairline before the fixed last rows (Terminal, Ask Kasandra)."""
        self.clear();self.rows = list(rows);section = None;first = None
        for n, row in enumerate(self.rows):
            if headings and row.section and row.section != section:self.add(row.section)
            elif headings and not row.section and section and n:self.add('')
            section = row.section
            item = self.add(row)
            if first is None:first = item
        if first is not None:self.setCurrentItem(first)
        return first

    def add(self, row):
        item = QListWidgetItem(self);item.setData(ROLE, row)
        if not isinstance(row, lf.Row):item.setFlags(Qt.NoItemFlags)
        return item

    def current(self):
        item = self.currentItem()
        return item.data(ROLE) if item is not None and isinstance(item.data(ROLE), lf.Row) else None

    def step(self, by):
        """The next row that can be chosen, `by` rows on (headings skipped); stays at the ends."""
        n = self.currentRow();total = self.count()
        if total == 0:return None
        target = n if n >= 0 else -1
        for _ in range(abs(by)):
            k = target
            while True:
                k += 1 if by > 0 else -1
                if k < 0 or k >= total:break
                if isinstance(self.item(k).data(ROLE), lf.Row):target = k;break
            if k < 0 or k >= total:break
        if target >= 0:self.setCurrentRow(target);self.scrollToItem(self.item(target))
        return self.current()


# ---- the line --------------------------------------------------------------------------------------------------------------------
def lens_icon(px, colour):
    pm = QPixmap(px * 2, px * 2);pm.setDevicePixelRatio(2);pm.fill(Qt.transparent)
    p = QPainter(pm);p.setRenderHint(QPainter.Antialiasing);p.setPen(QPen(QColor(colour), 1.6))
    side = px * .62;p.drawEllipse(QPointF(px * .44, px * .44), side / 2.2, side / 2.2)
    p.drawLine(QPointF(px * .44 + side * .32, px * .44 + side * .32), QPointF(px * .86, px * .86));p.end()
    return QIcon(pm)


class Line(QLineEdit):
    """The line in Start: it keeps the keyboard; Up and Down choose a row, Enter takes it, Tab moves between Start's parts,
    Esc or the Windows key closes Start; Win+E, Win+D and Win+L still do what they do from any app."""

    def __init__(self, panel):
        super().__init__(panel);self.panel = panel
        self.setPlaceholderText(PROMPT);self.setAccessibleName('The line: find or do');self.setClearButtonEnabled(True)
        self.addAction(lens_icon(16, ink()['secondary']), QLineEdit.LeadingPosition)

    def keyPressEvent(self, event):
        key = event.key();panel = self.panel
        if key in (Qt.Key_Escape, Qt.Key_Meta, Qt.Key_Super_L, Qt.Key_Super_R):panel.close();return
        if event.modifiers() & Qt.MetaModifier and key in WIN_KEYS:panel.windows_key(WIN_KEYS[key]);return
        if key in (Qt.Key_Down, Qt.Key_Up, Qt.Key_PageDown, Qt.Key_PageUp):
            panel.step({Qt.Key_Down: 1, Qt.Key_Up: -1, Qt.Key_PageDown: 5, Qt.Key_PageUp: -5}[key]);return
        if key in (Qt.Key_Return, Qt.Key_Enter):panel.enter();return
        if key in (Qt.Key_Tab, Qt.Key_Backtab):panel.next_part(-1 if key == Qt.Key_Backtab else 1);return
        if key in (Qt.Key_Left, Qt.Key_Right) and panel.part == 'power':panel.power_step(-1 if key == Qt.Key_Left else 1);return
        super().keyPressEvent(event)

    def focusNextPrevChild(self, forward):
        return False      # Tab is Start's own (keyPressEvent): the keyboard never leaves the line


WIN_KEYS = {Qt.Key_E: 'files', Qt.Key_D: 'show', Qt.Key_L: 'lock', Qt.Key_R: 'line', Qt.Key_S: 'line'}


# ---- power --------------------------------------------------------------------------------------------------------------------
class PowerButton(QAbstractButton):
    """One of the leave group's actions: its shape and its word; one the system does not offer here is drawn quiet with a
    slash through its shape, and its tip says why (a press still says why, in Graphite's window)."""

    def __init__(self, panel, key, word, scope):
        super().__init__(panel);self.panel = panel;self.key = key;self.word = word;self.scope = scope;self.reason = '';self.lit = False
        self.setText(word);self.setAccessibleName(word);self.setFocusPolicy(Qt.NoFocus);self.setCursor(Qt.PointingHandCursor);self.setAttribute(Qt.WA_Hover)
        self.setToolTip('%s · %s' % (word, scope))
        self.clicked.connect(lambda: panel.power(key))

    def sizeHint(self):
        return QSize(QFontMetrics(font(tokens.TYPE['body'][0])).horizontalAdvance(self.word) + 44, 34)

    def unavailable(self, reason):
        self.reason = reason or ''
        self.setToolTip('%s · %s%s' % (self.word, self.scope, ('\nUnavailable here: ' + self.reason) if self.reason else ''));self.update()

    def paintEvent(self, event):
        c = ink();p = QPainter(self);p.setRenderHint(QPainter.Antialiasing);r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        if self.isDown():bar_qt.plate(p, r, c['pressed'])
        elif self.underMouse() or self.lit:bar_qt.plate(p, r, c['hover'])
        if self.lit:p.setPen(QPen(QColor(c['accent']), 2));p.setBrush(Qt.NoBrush);p.drawRoundedRect(r.adjusted(1, 1, -1, -1), 6, 6)
        tone = c['disabled'] if self.reason else c['secondary']
        box = QRectF(10, (self.height() - 18) / 2, 18, 18);paint_glyph(p, box, self.key, tone)
        if self.reason:p.setPen(QPen(QColor(c['disabled']), 1.6));p.drawLine(box.bottomLeft() + QPointF(1, -1), box.topRight() + QPointF(-1, 1))
        p.setFont(font(tokens.TYPE['body'][0]));p.setPen(QColor(c['disabled'] if self.reason else c['text']))
        p.drawText(QRectF(box.right() + 7, 0, self.width() - box.right() - 9, self.height()), Qt.AlignLeft | Qt.AlignVCenter, self.word);p.end()


# ---- Start ------------------------------------------------------------------------------------------------------------------
class StartPanel(QFrame):
    """Start (mode 'start'), or the line's rows (mode 'line'), rising above the bar: a popup that holds the keyboard."""
    done = Signal(dict)

    def __init__(self, host, mode='start', sources=None):
        super().__init__(None, Qt.Popup | Qt.FramelessWindowHint)
        self.host = host;self.mode = mode;self.part = 'results' if mode == 'line' else 'apps';self.last = None;self.power_states = {}
        self.sources = sources or lf.Sources(host);self.closed_at = 0.0
        size = panel_size(mode);tall = size.width() >= 680;self.row_h = 44 if tall else 40
        c = ink();self.setObjectName('GraphiteStart');self.setAccessibleName('Start' if mode == 'start' else 'The line')
        self.setAttribute(Qt.WA_DeleteOnClose, False)
        self.setStyleSheet('QFrame#GraphiteStart {background:%s; border:1px solid %s;}'
                           ' QLineEdit {background:%s; color:%s; border:1px solid %s; border-radius:%dpx; padding:6px 8px; font-size:%dpx;}'
                           ' QLineEdit:focus {border:2px solid %s;}'
                           ' QLabel {color:%s;}' % (c['surface'], c['stroke'], c['window'], c['text'], c['stroke'], tokens.RADIUS['control'],
                                                    tokens.TYPE['body'][0] + (2 if tall else 1), c['accent'], c['secondary']))
        box = QVBoxLayout(self);box.setContentsMargins(16, 16, 16, 12);box.setSpacing(10)
        self.line = Line(self);self.line.setMinimumHeight(38 if tall else 34);box.addWidget(self.line)
        self.stack = QStackedWidget(self);box.addWidget(self.stack, 1)
        self.results = RowList(self, self.row_h);self.results.chosen.connect(self.take)
        self.home = QWidget(self);self.stack.addWidget(self.home);self.stack.addWidget(self.results)
        self.apps = RowList(self.home, self.row_h - 4);self.recent = RowList(self.home, self.row_h - 4)
        if mode == 'start':self.apps.every_verb = self.recent.every_verb = False      # the line under them says what Enter does
        self.apps.chosen.connect(self.take);self.recent.chosen.connect(self.take)
        self.hint = QLabel(self);self.hint.setFont(font(tokens.TYPE['footnote'][0]));self.hint.setTextFormat(Qt.PlainText);box.addWidget(self.hint)
        self.power_buttons = {}
        if mode == 'start':
            self.build_home(c, box)
        else:
            lay = QVBoxLayout(self.home);lay.setContentsMargins(0, 0, 0, 0);lay.addWidget(self.apps)
            self.apps.show_rows([lf.Row('hint', words, what, 'Try', words) for words, what in HINTS], headings=False)
            self.apps.insertItem(0, QListWidgetItem());self.apps.item(0).setData(ROLE, 'What the line takes');self.apps.item(0).setFlags(Qt.NoItemFlags)
        self.resize(size);self.setFixedWidth(size.width())
        self.timer = QTimer(self);self.timer.setSingleShot(True);self.timer.setInterval(90);self.timer.timeout.connect(self.find)
        self.line.textChanged.connect(lambda _t: self.timer.start())
        self.say_enter()

    def build_home(self, c, box):
        lay = QHBoxLayout(self.home);lay.setContentsMargins(0, 0, 0, 0);lay.setSpacing(12)
        left = QVBoxLayout();right = QVBoxLayout()
        for column, title, view in ((left, 'Apps', self.apps), (right, 'Recent', self.recent)):
            head = QLabel(title, self.home);head.setFont(font(tokens.TYPE['subhead'][0], QFont.DemiBold))
            head.setStyleSheet('color:%s; padding-left:12px;' % c['text'])
            if view is self.apps:      # 1.1 B5: Apps' plus left the head; "Add an app to the list" is here, beside Start's Apps
                from .apps_qt import PlusButton
                line = QHBoxLayout();line.setSpacing(4);line.addWidget(head);line.addStretch(1)
                self.add_app = PlusButton(self.host, self.home);self.add_app.setFixedSize(28, 28);self.add_app.clicked.connect(self.close)
                line.addWidget(self.add_app);column.addLayout(line)
            else:column.addWidget(head)
            column.addWidget(view, 1)
        lay.addLayout(left, 58);rule = QFrame(self.home);rule.setFixedWidth(1);rule.setStyleSheet('background:%s;' % c['hairline']);lay.addWidget(rule)
        lay.addLayout(right, 42)
        self.fill_home()
        rule = QFrame(self);rule.setFixedHeight(1);rule.setStyleSheet('background:%s;' % c['hairline']);box.addWidget(rule)
        row = QHBoxLayout();row.setSpacing(4)
        self.power_caption = QLabel('Power', self);self.power_caption.setFont(font(tokens.TYPE['footnote'][0], QFont.DemiBold))
        self.power_caption.setStyleSheet('color:%s;' % c['secondary']);row.addWidget(self.power_caption);row.addStretch(1)
        for key, word, scope in lf.power_words():
            button = PowerButton(self, key, word, scope);self.power_buttons[key] = button;row.addWidget(button)
        box.addLayout(row)

    def fill_home(self):
        """Apps by kind (the apps' own desktop entries), and recent files."""
        try:
            from .apps_qt import listing
            listed = listing(self.host) if self.host is not None else __import__('workbench.apps_catalog', fromlist=['listing']).listing()
        except Exception:  # noqa: BLE001 - no apps read: says so
            listed = {}
        rows = []
        for kind, members in lf.apps_by_kind(listed):
            for app in members:
                row = lf.app_row(app);row.section = kind;row.detail = app.get('generic') if app.get('generic') and app.get('generic') != app.get('name') else kind
                rows.append(row)
        self.app_rows = rows
        if rows:self.apps.show_rows(rows)
        else:self.apps.clear();self.apps.add(EMPTY_APPS)
        recent = [lf.file_row(path, lf.home_words(__import__('pathlib').Path(path).parent), how) for path, how in self.sources.recent(10)]
        self.recent_rows = recent
        if recent:self.recent.show_rows(recent, headings=False)
        else:self.recent.clear();self.recent.add(EMPTY_RECENT)
        self.apps.setCurrentRow(-1);self.recent.setCurrentRow(-1)      # nothing chosen until Down or Tab: Enter on an empty line does nothing

    # -- rising above the bar
    def rise(self, anchor=None, bar=None):
        """Show it above `anchor` (a slot of the bar), its left edge at the slot's, its foot just above the bar; with no bar,
        at the bottom left of the screen."""
        screen = (anchor.screen() if anchor is not None else None) or (self.host.screen() if self.host is not None else None) or QGuiApplication.primaryScreen()
        g = screen.geometry();self.adjust_height()
        if bar is not None and anchor is not None:
            x = anchor.mapToGlobal(anchor.rect().topLeft()).x() + (0 if self.mode == 'start' else 0);top = bar.mapToGlobal(bar.rect().topLeft()).y()
        else:
            a = screen.availableGeometry();x = a.left() + 8;top = a.bottom() + 1
        x = max(g.left(), min(x, g.right() + 1 - self.width()))
        self.move(x, max(g.top(), top - self.height() - 6))
        self.show();self.raise_();self.activateWindow();self.line.setFocus(Qt.PopupFocusReason)
        self.grabs = 0;QTimer.singleShot(150, self.hold_keyboard)
        if self.mode == 'start':self.read_power()
        return self

    def hold_keyboard(self):
        """The keyboard is the line's while Start is up. A window manager that is still holding the Windows key when Start
        rises can refuse the first grab: it is asked again, for a moment."""
        if not self.isVisible():return
        handle = self.windowHandle()
        ok = bool(handle is not None and handle.setKeyboardGrabEnabled(True))
        self.grabs += 1
        if not ok and self.grabs < 12:QTimer.singleShot(150, self.hold_keyboard)
        self.line.setFocus(Qt.PopupFocusReason)

    def adjust_height(self):
        if self.mode == 'start':return
        view = self.results if self.stack.currentWidget() is self.results else self.apps
        need = sum(view.sizeHintForRow(i) for i in range(view.count())) + 8
        chrome = 16 + self.line.minimumHeight() + 10 + 10 + self.hint.sizeHint().height() + 12
        self.setFixedHeight(max(150, min(panel_size('line').height(), chrome + need)))

    def closeEvent(self, event):
        self.closed_at = time.monotonic();super().closeEvent(event)

    def hideEvent(self, event):
        self.closed_at = time.monotonic();super().hideEvent(event)
        for name in ('start', 'line'):
            slot = slot_of(self.host, name)
            if slot is not None:slot.update()

    # -- typing
    def find(self):
        text = self.line.text()
        if not lf.clean(text):
            self.stack.setCurrentWidget(self.home);self.part = 'apps' if self.mode == 'start' else 'results'
            if self.mode == 'start':
                self.apps.setCurrentRow(-1);self.recent.setCurrentRow(-1)
            self.adjust_height();self.say_enter();self.reposition();return []
        found = lf.rows(text, self.sources)
        self.results.show_rows(found);self.stack.setCurrentWidget(self.results);self.part = 'results'
        self.adjust_height();self.say_enter();self.reposition()
        return found

    def reposition(self):
        """The line's panel grows upward from the bar: its foot stays where it was."""
        if self.mode == 'start' or not self.isVisible():return
        foot = getattr(self, '_foot', None)
        if foot is None:self._foot = self.geometry().bottom();return
        self.move(self.x(), foot - self.height() + 1)

    def view(self):
        if self.part == 'results' and self.stack.currentWidget() is self.results:return self.results
        if self.part == 'recent':return self.recent
        if self.part == 'power':return None
        return self.apps

    def current(self):
        if self.part == 'power':
            key = next((k for k, b in self.power_buttons.items() if b.lit), None)
            return lf.Row('power', self.power_buttons[key].word, self.power_buttons[key].scope, self.power_buttons[key].word, key) if key else None
        view = self.view()
        return view.current() if view is not None else None

    def say_enter(self, words=None):
        if words is None:
            row = self.current()
            if row is None:
                words = ('Down or Tab chooses an app, a recent file or power' if self.mode == 'start' and self.stack.currentWidget() is self.home
                         else 'Type, then Enter does what the first row says')
            elif row.kind == 'hint':words = 'Enter: put “%s” in the line' % row.title
            elif row.kind == 'power':words = 'Enter: %s · %s' % (row.title, 'asks first and names the apps still open' if row.target in ('logout', 'restart', 'shutdown') else row.detail)
            else:words = row.enter_words()
            words += '   ·   ↑↓ choose   ·   Esc closes'
        self.hint.setToolTip(words)
        self.hint.setText(QFontMetrics(self.hint.font()).elidedText(words, Qt.ElideRight, max(80, self.width() - 34)))

    def step(self, by):
        view = self.view()
        if view is not None:view.step(by)
        self.say_enter()

    def next_part(self, by=1):
        """Tab: the apps, then recent files, then the power row (Start empty); the rows otherwise."""
        if self.mode != 'start' or self.stack.currentWidget() is self.results:return
        parts = ['apps', 'recent', 'power'];self.part = parts[(parts.index(self.part) + by) % len(parts)] if self.part in parts else 'apps'
        for view, name in ((self.apps, 'apps'), (self.recent, 'recent')):
            if name == self.part:
                if view.current() is None:view.step(1)
            else:view.setCurrentRow(-1)
        for b in self.power_buttons.values():b.lit = False;b.update()
        if self.part == 'power':
            first = self.power_buttons.get('lock');first.lit = True;first.update()
        self.say_enter()

    def power_step(self, by):
        keys = list(self.power_buttons);at = next((n for n, k in enumerate(keys) if self.power_buttons[k].lit), 0)
        for b in self.power_buttons.values():b.lit = False;b.update()
        b = self.power_buttons[keys[(at + by) % len(keys)]];b.lit = True;b.update();self.say_enter()

    # -- doing
    def enter(self):
        row = self.current()
        if row is None:
            text = lf.clean(self.line.text())
            if not text:return None
            found = self.find();row = found[0] if found else None
        return self.take(row) if row is not None else None

    def take(self, row):
        """Do what the row says (the owner's Enter or press). Start leaves when done, except for a sum and a hint."""
        if row is None:return None
        if row.kind == 'power':return self.power(row.target)
        if row.kind == 'hint':
            self.line.setText(row.target);self.line.end(False);self.find();return {'done': True, 'words': 'In the line.'}
        result = do(self.host, row, self)
        self.last = result;self.done.emit(result)
        if row.kind in ('sum', 'explain'):
            self.say_enter(result.get('words', ''));return result
        self.close()
        return result

    def windows_key(self, verb):
        if verb == 'line':
            self.line.selectAll();return None
        self.close()
        from .windows_keys_qt import act
        return act(self.host, verb)

    def power(self, key):
        """Lock, Suspend, Log out, Restart, Shut down: 1.0's leave group, in Graphite's window (its questions and its
        confirmation are there): Start closes, Graphite comes forward, then the group's own step runs."""
        self.close()
        bring_forward(self.host)
        from . import session_power as power
        if key in power.STAYS:
            run = power.run_lock if key == 'lock' else power.run_suspend
            QTimer.singleShot(120, lambda: run(self.host))
        else:
            QTimer.singleShot(60, lambda: power.run_action(self.host, key))
        self.last = {'done': True, 'words': power.WORDS[key], 'power': key};self.done.emit(self.last)
        return self.last

    def read_power(self):
        """Which of the five the system offers here (logind, the screen locker), read off the window's thread."""
        def read():
            try:
                from . import session_power as power
                self.power_states = power.availability(only=lf.POWER)
            except Exception as exc:  # noqa: BLE001 - unknown: each press says why itself
                self.power_states = {k: {'available': True, 'reason': str(exc)[:80]} for k in lf.POWER}
        worker = threading.Thread(target=read, daemon=True);worker.start()
        self._power_poll = QTimer(self);self._power_poll.setInterval(100)
        self._power_poll.timeout.connect(lambda: self.show_power(worker));self._power_poll.start()

    def show_power(self, worker):
        if worker.is_alive():return
        self._power_poll.stop()
        for key, state in (self.power_states or {}).items():
            button = self.power_buttons.get(key)
            if button is not None:button.unavailable('' if state.get('available') else state.get('reason', ''))
        if any(b.reason for b in self.power_buttons.values()):      # the slash is a shape; this says it in words
            self.power_caption.setText('Power\nslashed: not here')
            self.power_caption.setToolTip('A slashed one is not offered on this computer; its tip says why, and a press says it too.')


# ---- doing what a row says ------------------------------------------------------------------------------------------------------
def bring_forward(host):
    """Graphite's window forward (the bar's way when it stands: the window manager is asked as a task list asks)."""
    bar = getattr(host, 'graphite_bar', None)
    try:
        if bar is not None:return bar.bring_graphite()
        from .windows_keys_qt import bring
        bring(host)
    except (RuntimeError, AttributeError):
        pass
    return None


def status(host, words):
    try:host.statusBar().showMessage(str(words), 9000)
    except (AttributeError, RuntimeError):pass
    return words


def do(host, row, panel=None):
    """What Enter does on `row`, as its verb says: {done, words}. Every path is 1.0's own (apps.open, the default app, Settings,
    the board, the line page, the operations page, the Terminal, her column)."""
    kind = row.kind;target = row.target
    try:
        if kind == 'sum':
            QApplication.clipboard().setText(str(target))
            if panel is not None:
                panel.line.blockSignals(True);panel.line.setText(str(target));panel.line.end(False);panel.line.blockSignals(False)
            return {'done': True, 'words': 'Copied %s. Go on typing to use it.' % target}
        if kind == 'explain':
            return {'done': True, 'words': row.detail}
        if kind == 'app':
            if not row.extra.get('available', True):return {'done': False, 'words': status(host, row.extra.get('reason') or 'It cannot start here.')}
            from .apps_qt import open_app
            return {'done': True, 'words': open_app(host, target)}
        if kind == 'address':
            bar = getattr(host, 'type_bar', None)
            if bar is not None and callable(getattr(bar, 'open_web', None)):bar.open_web(target);return {'done': True, 'words': 'Opened in your browser.'}
            from PySide6.QtCore import QUrl
            from PySide6.QtGui import QDesktopServices
            url = target if '://' in target else 'https://' + target if not target.startswith('localhost') else 'http://' + target
            return {'done': bool(QDesktopServices.openUrl(QUrl(url))), 'words': 'Opened in your browser.'}
        if kind == 'file':
            return open_file(host, target, row.extra.get('how', 'file'))
        if getattr(host, 'foot_folded', False) and (kind in ('dos', 'terminal') or (kind == 'place' and target[0] == 'terminal')):  # 1.1 B4
            from .drop_terminal_qt import run as run_in_terminal, terminal  # 1.1 B4: the Terminal drops over the app in front
            if kind == 'place':terminal(host).drop();return {'done': True, 'words': 'The Terminal.'}  # 1.1 B4
            run_in_terminal(host, target);return {'done': True, 'words': 'In the Terminal: %s' % target}  # 1.1 B4
        bring_forward(host)
        if kind == 'setting':
            host.ledger_bridge.show_settings(key=target);return {'done': True, 'words': 'Settings · %s' % row.title}
        if kind == 'place':
            what, verb = target
            if what == 'settings':host.ledger_bridge.show_settings();return {'done': True, 'words': 'Settings.'}
            if what == 'terminal':host.console.open('shell');return {'done': True, 'words': 'The Terminal.'}
            from .windows_keys_qt import act
            return act(host, verb)
        if kind == 'desk':
            from .search_reach import open_record
            open_record(host, target);return {'done': True, 'words': row.title}
        if kind == 'command':
            target();return {'done': True, 'words': row.title}
        if kind == 'operation':
            from .shell2 import to_console
            to_console(host, 'kernel', target);return {'done': True, 'words': 'On the operations page: %s' % target}
        if kind in ('dos', 'terminal'):
            from .shell2 import to_console
            to_console(host, 'shell', target);return {'done': True, 'words': 'In the Terminal: %s' % target}
        if kind == 'line':
            from .foot_line import run_line
            return {'done': bool(run_line(host, target)), 'words': 'On the line page.'}
        if kind == 'ask':
            from .foot_line import ask_kasandra, GIVEN
            given = ask_kasandra(host, target)
            return {'done': bool(given), 'words': status(host, GIVEN if given else 'Her column is not on this window.')}
    except Exception as exc:  # noqa: BLE001 - the row could not be done here: said, and Graphite goes on
        return {'done': False, 'words': status(host, '%s: %s' % (row.verb, str(exc)[:160] or type(exc).__name__))}
    return {'done': False, 'words': 'Nothing to do.'}


def open_file(host, path, how='file'):
    """A file in its app (the Kernel's apps.for, then apps.open, as Files opens it), Graphite's own documents in its viewer; a
    folder in Files."""
    from pathlib import Path
    if how == 'viewer' and callable(getattr(host, 'open_in_viewer', None)):
        bring_forward(host);host.open_in_viewer(path);return {'done': True, 'words': Path(path).name}
    if how == 'document' and callable(getattr(host, 'open_document', None)):
        bring_forward(host);host.open_document(Path(path));return {'done': True, 'words': Path(path).name}
    if how == 'folder' or Path(path).is_dir():
        bring_forward(host)
        from .search_reach import open_home
        if open_home(host, path):return {'done': True, 'words': Path(path).name}
    try:
        from .apps_qt import open_default
        if open_default(host, path):return {'done': True, 'words': Path(path).name}
    except Exception:  # noqa: BLE001 - the system's own opener below
        pass
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QDesktopServices
    return {'done': bool(QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))), 'words': Path(path).name}


# ---- the slots on the bar ---------------------------------------------------------------------------------------------------------
def panel_of(host):
    return getattr(host, 'start_panel', None)


def slot_of(host, name):
    bar = getattr(host, 'graphite_bar', None)
    try:return bar.slot(name) if bar is not None else None
    except RuntimeError:return None


def is_open(host, mode=None):
    panel = panel_of(host)
    try:return bool(panel is not None and panel.isVisible() and (mode is None or panel.mode == mode))
    except RuntimeError:return False


_X = {}
GRAB_WAIT_MS = 40                    # how often the keyboard is looked at while another program holds it
GRAB_MOST_MS = 2000                  # and for how long, at most


def keyboard_free():
    """Whether no other program holds the keyboard. A window manager holds it while the key it runs a command on is down
    (Fluxbox, the Windows key): Start, which takes the keyboard for its line, rises once the key is let go, as Windows' Start
    rises on the key's release. True off X, or when X cannot be asked."""
    if QGuiApplication.platformName() != 'xcb':return True
    try:
        import ctypes
        if 'lib' not in _X:
            lib = ctypes.CDLL('libX11.so.6')
            lib.XOpenDisplay.restype = ctypes.c_void_p;lib.XOpenDisplay.argtypes = [ctypes.c_char_p]
            lib.XDefaultRootWindow.restype = ctypes.c_ulong;lib.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
            lib.XGrabKeyboard.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_ulong]
            lib.XUngrabKeyboard.argtypes = [ctypes.c_void_p, ctypes.c_ulong];lib.XSync.argtypes = [ctypes.c_void_p, ctypes.c_int]
            _X['lib'] = lib;_X['dpy'] = lib.XOpenDisplay(None)
        lib, dpy = _X['lib'], _X['dpy']
        if not dpy:return True
        got = lib.XGrabKeyboard(dpy, lib.XDefaultRootWindow(dpy), 0, 1, 1, 0)      # GrabModeAsync, CurrentTime
        if got == 0:lib.XUngrabKeyboard(dpy, 0)
        lib.XSync(dpy, 0)
        return got == 0
    except (OSError, AttributeError):
        return True


def open_start(host, mode='start', sources=None):
    """Start (or the line's rows, mode 'line') above the bar, the cursor in the line; a second call closes it (the Windows key
    pressed again). While another program holds the keyboard (the window manager, the Windows key still down) Start waits
    for it, a moment at most. Returns {ok, words}, as graphite-do's words answer."""
    panel = panel_of(host)
    try:
        if panel is not None and panel.isVisible():return rise(host, mode, sources)
    except RuntimeError:
        pass
    waiting = getattr(host, '_start_waiting', None)
    if waiting is not None:return {'ok': True, 'words': 'Start rises once the Windows key is let go.'}
    if keyboard_free():return rise(host, mode, sources)
    began = time.monotonic();timer = QTimer();timer.setInterval(GRAB_WAIT_MS);host._start_waiting = timer

    def look():
        if keyboard_free() or (time.monotonic() - began) * 1000 >= GRAB_MOST_MS:
            timer.stop();host._start_waiting = None;rise(host, mode, sources)
    timer.timeout.connect(look);timer.start()
    return {'ok': True, 'words': 'Start rises once the Windows key is let go.'}


def rise(host, mode='start', sources=None):
    panel = panel_of(host)
    try:
        if panel is not None and panel.isVisible():
            same = panel.mode == mode;panel.close()
            if same:return {'ok': True, 'words': 'Start is closed.' if mode == 'start' else 'The line is closed.'}
        elif panel is not None and time.monotonic() - panel.closed_at < REOPEN_MS / 1000.0 and panel.mode == mode:
            return {'ok': True, 'words': 'Start is closed.'}
    except RuntimeError:
        pass
    if panel is not None:
        try:panel.deleteLater()
        except RuntimeError:pass
    panel = StartPanel(host, mode, sources);host.start_panel = panel
    bar = getattr(host, 'graphite_bar', None)
    anchor = slot_of(host, 'start' if mode == 'start' else 'line') if bar is not None else None
    try:visible = bool(bar is not None and bar.isVisible())
    except RuntimeError:visible = False
    panel.rise(anchor if visible else None, bar if visible else None)
    for name in ('start', 'line'):
        slot = slot_of(host, name)
        if slot is not None:slot.update()
    return {'ok': True, 'words': 'Start is open.' if mode == 'start' else 'The line is open.'}


class StartSlot(bar_qt.StartButton):
    """The bar's Start: Graphite's mark and the word; a press raises Start (a filled plate while it is up)."""

    def __init__(self, bar):
        super().__init__(bar);self.setToolTip(START_TIP);self.setAccessibleName('Start')

    def start(self):
        return open_start(self.bar.host, 'start')

    def paintEvent(self, event):
        from .graphite_brand import mark_icon
        c = ink();p = QPainter(self);h = self.height();self.ground(p, c, is_open(self.bar.host, 'start'))
        px = round(h * 0.45);x = round(h * 0.3)
        mark_icon(px).paint(p, QRect(x, (h - px) // 2, px, px));x += px + 8
        p.setFont(bar_qt.bar_font(h, QFont.DemiBold));p.setPen(QColor(c['text']))
        p.drawText(QRect(x, 0, self.width() - x, h), Qt.AlignLeft | Qt.AlignVCenter, 'Start');p.end()


class LineSlot(bar_qt.LineField):
    """The bar's line: the field's shape and its words; a press raises the line's rows above it (its ring in the accent while
    they are up)."""
    WORDS = 'Search or do'

    def __init__(self, bar):
        super().__init__(bar);self.setToolTip(LINE_TIP);self.setAccessibleName('The line: find or do')
        self.clicked.connect(lambda: open_start(self.bar.host, 'line'))

    def paintEvent(self, event):
        super().paintEvent(event)
        if is_open(self.bar.host, 'line'):
            c = ink();p = QPainter(self);p.setRenderHint(QPainter.Antialiasing);r = QRectF(4, 6, self.width() - 8, self.height() - 12)
            p.setPen(QPen(QColor(c['accent']), 2));p.setBrush(Qt.NoBrush);p.drawRoundedRect(r.adjusted(1, 1, -1, -1), r.height() / 2 - 1, r.height() / 2 - 1);p.end()


def install(host):
    """shell2 calls this before the bar stands: Start and the line fill the bar's two slots (bar_qt.register_slot), and the
    Windows key's word (graphite-do start) opens Start."""
    bar_qt.register_slot('start', StartSlot)
    bar_qt.register_slot('line', LineSlot)
    host.start_panel = None
    host.open_start = lambda mode='start': open_start(host, mode)
    return True
