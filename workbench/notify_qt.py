"""Graphite 1.0 S5 · Notifications shown quietly: a toast at the foot of her column that never takes the focus.

notify_server keeps what programs send; this shows it. A toast stands just above the foot of her column (the right pane's
foot, where "ask Kasandra…" is), the newest at the bottom, at most SHOWN at once:

    ◆ NOTIFICATION · “Rail Demo app” · 14:02                                ✕
    Bench readings saved
    Rev B is on disk
    [Open] [Later]                                                kept in Log

An urgent one says ▲ URGENT (the word and the shape, its colour only beside them) and stays until you close it; the others
go after their time (the pointer resting on one holds it). Pressing an action sends ActionInvoked to the program; pressing
the words sends its "default" action when it has one; ✕ closes it (NotificationClosed, reason 2). None of it takes the
keyboard: the toast and its buttons never take the focus, so the writing line or the app you type in keeps it.

When an app is in front (Graphite's window is not the active one, on X), the toast is a small window of its own at the
upper right, made so the window manager never gives it the focus (an override-redirect tooltip window that does not accept
focus); otherwise it is part of Graphite's window. Offscreen it is always part of the window.

Settings ▸ This computer ▸ Notifications chooses between "Show a toast" and "Only keep them in Log" (urgent ones always show);
the choice is kept in the session (notifications.toasts). Every notification is kept in Log either way (Events), unless
the program marked it transient.
"""
from __future__ import annotations

import time

from PySide6.QtCore import QEvent, QObject, QRect, Qt, QTimer
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QSizePolicy, QToolButton, QVBoxLayout, QWidget

from . import boss_theme as bt
from . import notify_server as ns

SHOWN = 3                   # toasts on screen at once (the others wait their time out of sight, and are in Log)
WIDTH_MOST = 440            # a toast's width at 14 pt
GAP = 6
PAD = 6                     # the shelf's own margin around the toasts in Graphite's window


def toasts_on(host):
    try:return bool(((host.session.state.get('notifications') or {}).get('toasts', True)))
    except AttributeError:return True


def set_toasts(host, on):
    try:
        state = dict(host.session.state.get('notifications') or {});state['toasts'] = bool(on)
        host.session.state['notifications'] = state;host.session.save()
    except (AttributeError, OSError):
        pass


def scale_of(host):
    try:
        from .shell2 import scale_of as s
        return max(1.0, min(1.6, s(host)))
    except Exception:  # noqa: BLE001
        return 1.0


class Toast(QFrame):
    """One notification. Built from plain labels and buttons that never take the focus."""

    def __init__(self, shelf, note, floating=False):
        flags = (Qt.ToolTip | Qt.FramelessWindowHint | Qt.WindowDoesNotAcceptFocus) if floating else Qt.Widget
        super().__init__(None if floating else shelf.stack_widget(), flags)
        self.shelf = shelf;self.note = note;self.floating = floating
        self.setObjectName('GraphiteToast');self.setFocusPolicy(Qt.NoFocus)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        if floating:self.setAttribute(Qt.WA_X11DoNotAcceptFocus, True)
        self.setCursor(Qt.ArrowCursor)
        s = scale_of(shelf.host)
        outer = QVBoxLayout(self);outer.setContentsMargins(round(14 * s), round(10 * s), round(10 * s), round(10 * s));outer.setSpacing(round(4 * s))
        head = QHBoxLayout();head.setSpacing(round(8 * s))
        self.kind = QLabel();self.kind.setTextFormat(Qt.PlainText);self.kind.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        self.who = QLabel();self.who.setTextFormat(Qt.PlainText);self.who.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred);self.who_full = ''
        self.close_ = QToolButton();self.close_.setText('✕');self.close_.setFocusPolicy(Qt.NoFocus);self.close_.setAutoRaise(True)
        self.close_.setToolTip('Close this notification');self.close_.setAccessibleName('Close this notification')
        self.close_.clicked.connect(lambda: shelf.dismiss(self.note['id']))
        head.addWidget(self.kind);head.addWidget(self.who, 1);head.addWidget(self.close_)
        outer.addLayout(head)
        self.summary = QLabel();self.summary.setTextFormat(Qt.PlainText);self.summary.setWordWrap(True)
        self.body = QLabel();self.body.setTextFormat(Qt.PlainText);self.body.setWordWrap(True)
        for label in (self.summary, self.body):label.setFocusPolicy(Qt.NoFocus);label.setCursor(Qt.PointingHandCursor);label.installEventFilter(self)
        outer.addWidget(self.summary);outer.addWidget(self.body)
        self.foot = QHBoxLayout();self.foot.setSpacing(round(6 * s));outer.addLayout(self.foot)
        self.kept = QLabel();self.kept.setTextFormat(Qt.PlainText);self.kept.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        # (fill puts it on its own line under the actions, so the actions keep their whole words)
        self.buttons = []
        self.fill(note)

    def fill(self, note):
        self.note = note;s = scale_of(self.shelf.host)
        urgent = note['urgency'] == 2
        edge = bt.STOP if urgent else bt.READY
        from .design_tokens import RADIUS      # 1.0 P4: Day and Night: a hairline stroke and the tokens' toast radius
        self.setStyleSheet('QFrame#GraphiteToast {background:%s; border:1px solid %s; border-left:%dpx solid %s; border-radius:%dpx;}'
                           ' QLabel {background:transparent; border:0;}'
                           ' QToolButton {color:%s; background:transparent; border:0; padding:0 4px;} QToolButton:hover {color:%s;}'
                           % (bt.CARD, bt.LINE_MID if bt.LAUNCH else bt.LINE_STRONG, max(3, round(3 * s)), edge, RADIUS['toast'] if bt.LAUNCH else 6, bt.QUIET, bt.TEXT))
        self.kind.setText('▲ URGENT' if urgent else '◆ NOTIFICATION')
        self.kind.setStyleSheet('QLabel {color:%s; font-family:"%s"; letter-spacing:1px;}' % (edge, bt.MONO))
        self.who_full = '· “%s” · %s' % (note['app'] or 'an app', ns.clock(note['at']));self.who.setText(self.who_full)
        self.who.setStyleSheet('QLabel {color:%s;}' % bt.QUIET)
        self.summary.setText(note['summary'] or '(no title)')
        font = QFont(self.summary.font());font.setWeight(QFont.DemiBold);self.summary.setFont(font)
        self.summary.setStyleSheet('QLabel {color:%s;}' % bt.TEXT)
        body = note['body']
        lines = body.splitlines()
        if len(lines) > 3 or len(body) > 260:body = ('\n'.join(lines[:3]))[:257].rstrip() + '…'
        self.body.setText(body);self.body.setVisible(bool(body))
        self.body.setStyleSheet('QLabel {color:%s;}' % bt.QUIET)
        default = any(k == 'default' for k, _ in note['actions'])
        tip = 'Press the words to answer the app (its default action).' if default else ''
        self.summary.setToolTip(tip);self.body.setToolTip(tip)
        while self.foot.count():
            item = self.foot.takeAt(0)
            widget = item.widget()
            if widget is not None and widget is not self.kept:widget.deleteLater()
        self.buttons = []
        from .shell2 import button
        for key, label in note['actions']:      # the default action too, by its own words (pressing the toast's words also sends it)
            b = button(label, 'tool', 'Tell the app: ' + label);b.setFocusPolicy(Qt.NoFocus);b.setAccessibleName(label)
            b.clicked.connect(lambda checked=False, key=key: self.shelf.invoke(self.note['id'], key))
            self.foot.addWidget(b);self.buttons.append(b)
        self.foot.addStretch(1)
        self.foot.removeWidget(self.kept);self.layout().removeWidget(self.kept)
        if not self.buttons:self.foot.addWidget(self.kept)      # no actions: on the foot's own line
        else:self.layout().addWidget(self.kept)
        self.kept.setText('kept in Log' if note.get('logged') else ('not kept (the app asked)' if note.get('transient') else 'shown only'))
        self.kept.setStyleSheet('QLabel {color:%s;}' % bt.FAINT)
        words = '%s from “%s”: %s. %s' % ('Urgent notification' if urgent else 'Notification', note['app'] or 'an app', note['summary'], note['body'])
        self.setAccessibleName(words.strip());self.setToolTip('')
        self.adjustSize()

    def fit(self, width):
        """At this width: the program's name cut short to the room the head leaves it; the height the words need."""
        self.setFixedWidth(width)
        m = self.layout().contentsMargins();spacing = self.layout().itemAt(0).layout().spacing()
        room = width - m.left() - m.right() - self.kind.sizeHint().width() - self.close_.sizeHint().width() - 2 * spacing
        self.who.setText(self.who.fontMetrics().elidedText(self.who_full, Qt.ElideRight, max(20, room - 6)))      # 1.0 D2: 6 px for the label's own edges (its ellipsis was clipped by 3 px)
        h = self.layout().totalHeightForWidth(width) if self.layout().hasHeightForWidth() else -1
        h = h if h > 0 else self.sizeHint().height()
        self.setFixedHeight(h)
        return h

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonRelease and obj in (self.summary, self.body):
            if any(k == 'default' for k, _ in self.note['actions']):self.shelf.invoke(self.note['id'], 'default')
            return True
        return super().eventFilter(obj, event)

    def enterEvent(self, event):
        self.shelf.hold(self.note['id'], True);super().enterEvent(event)

    def leaveEvent(self, event):
        self.shelf.hold(self.note['id'], False);super().leaveEvent(event)

    def words(self):
        """The toast as it reads (the smoke script's view of it)."""
        parts = [self.kind.text(), self.who_full, self.summary.text()]
        if self.body.isVisible():parts.append(self.body.text())
        parts += ['[%s]' % b.text() for b in self.buttons] + [self.kept.text()]
        return ' | '.join(p for p in parts if p)


class Shelf(QObject):
    """The toasts of one window: shown, timed, placed above the foot of her column."""

    def __init__(self, host, service):
        super().__init__(host);self.host = host;self.service = service
        self.toasts = {};self.timers = {};self.order = [];self.stack = None
        service.notes.listen(self.changed)
        host.installEventFilter(self)
        pane = getattr(host, 'right_pane', None)
        if pane is not None:pane.installEventFilter(self)

    # the notes
    def changed(self, kind, note):
        if getattr(self.host, '_closing', False):return
        if kind in ('shown', 'replaced'):
            self.arm(note)
            if note['urgency'] == 2 or toasts_on(self.host):self.show_note(note)
        elif kind == 'closed':
            self.drop(note['id'])

    def arm(self, note):
        timer = self.timers.pop(note['id'], None)
        if timer is not None:timer.stop();timer.deleteLater()
        if note['seconds']:
            timer = QTimer(self);timer.setSingleShot(True);timer.setInterval(int(note['seconds'] * 1000))
            timer.timeout.connect(lambda ident=note['id']: self.service.expire(ident))
            timer.start();self.timers[note['id']] = timer

    def hold(self, ident, on):
        timer = self.timers.get(ident)
        if timer is None:return
        if on:timer.stop()
        else:timer.start(max(3000, min(timer.interval(), 6000)))

    def stack_widget(self):
        """The shelf in Graphite's window: an opaque band the toasts stand on, so nothing of the column shows between them."""
        if self.stack is None:
            self.stack = QFrame(self.host);self.stack.setObjectName('GraphiteToastShelf');self.stack.setFocusPolicy(Qt.NoFocus)
            self.stack.setStyleSheet('QFrame#GraphiteToastShelf {background:%s; border:0;}' % bt.GROUND)
            self.stack.setAccessibleName('Notifications');self.stack.hide()
        return self.stack

    def floating(self):
        """A toast of its own above the apps: only on X, while an app (not Graphite's window) is in front."""
        app = QApplication.instance()
        if app is None or QApplication.platformName() != 'xcb':return False
        active = QApplication.activeWindow()
        return active is None or (active is not self.host and active.window() is not self.host)

    def show_note(self, note):
        toast = self.toasts.get(note['id'])
        if toast is not None:
            try:toast.fill(note)
            except RuntimeError:toast = None
        if toast is None:
            toast = Toast(self, note, floating=self.floating());self.toasts[note['id']] = toast
        if note['id'] in self.order:self.order.remove(note['id'])
        self.order.append(note['id'])
        self.place()

    def drop(self, ident):
        timer = self.timers.pop(ident, None)
        if timer is not None:timer.stop();timer.deleteLater()
        toast = self.toasts.pop(ident, None)
        if ident in self.order:self.order.remove(ident)
        if toast is not None:
            toast.hide();toast.deleteLater()
        self.place()

    def dismiss(self, ident):
        self.service.dismiss(ident)

    def invoke(self, ident, key):
        self.service.invoke(ident, key)

    def shown(self):
        """The toasts on screen, oldest first."""
        return [self.toasts[i] for i in self.order[-SHOWN:] if i in self.toasts]

    # where they stand
    def anchor(self):
        """(x, bottom, width) in the window: above the foot of her column; else the lower right of the window."""
        host = self.host;s = scale_of(host)
        pane = getattr(host, 'right_pane', None);foot = getattr(pane, 'foot', None)
        if pane is not None and foot is not None and pane.isVisible() and pane.width() > 200:
            inset = getattr(pane, 'inset', 16)
            top_left = pane.mapTo(host, foot.geometry().topLeft())
            x = pane.mapTo(host, pane.rect().topLeft()).x() + inset
            width = min(round(WIDTH_MOST * s), pane.width() - 2 * inset)
            return x, top_left.y() - GAP, width
        width = min(round(WIDTH_MOST * s), host.width() - 32)
        return host.width() - width - 16, host.height() - 48, width

    def place(self):
        if getattr(self.host, '_closing', False):return
        shown = self.shown();x, bottom, width = self.anchor()
        hidden = [t for i, t in self.toasts.items() if t not in shown]
        for t in hidden:t.hide()
        floating = [t for t in shown if t.floating];inside = [t for t in shown if not t.floating]
        if floating:      # at the upper right of the screen, below the dock when it stands, the newest lowest
            screen = (self.host.screen() or QApplication.primaryScreen()).availableGeometry()
            y = screen.top() + 16
            dock = getattr(self.host, 'system_dock', None)
            if dock is not None and getattr(dock, 'at_bottom', False):  # 1.1 B1: the bar at the bottom: they rise above its clock, the newest lowest
                try:y = dock.geometry().top() - 12
                except RuntimeError:y = screen.bottom() - 16
                for toast in reversed(floating):  # 1.1 B1
                    h = toast.fit(width);y -= h;toast.move(screen.right() - width - 16, y);y -= GAP  # 1.1 B1
                    toast.show();toast.raise_()  # 1.1 B1
                floating = []  # 1.1 B1
            elif dock is not None:
                try:y = max(y, dock.geometry().bottom() + 12)
                except RuntimeError:pass
            for toast in floating:
                h = toast.fit(width);toast.move(screen.right() - width - 16, y);y += h + GAP
                toast.show();toast.raise_()
        stack = self.stack
        if not inside:
            if stack is not None:stack.hide()
            return
        heights = [t.fit(width) for t in inside]
        total = sum(heights) + GAP * (len(inside) - 1) + 2 * PAD
        stack.setGeometry(x - PAD, max(0, bottom - total + PAD), width + 2 * PAD, total)
        y = PAD
        for toast, h in zip(inside, heights):      # oldest first, the newest at the bottom, nearest the foot
            toast.move(PAD, y);toast.show();y += h + GAP
        stack.show();stack.raise_()

    def eventFilter(self, obj, event):
        if event.type() in (QEvent.Resize, QEvent.Show) and self.toasts:QTimer.singleShot(0, self.place)
        return False


def log_note(host, note):
    """Kept in Log: one line in the activity journal (Log's Events), the program's name as the name it gave."""
    from . import activity
    result = activity.record(host.root, 'DESKTOP', 'notification', 'SHOWN', ns.log_words(note))
    return result.get('committed', False)


def install(host):
    """The notes, the server (when Graphite is the session's notification server here) and the shelf; host.notifications
    is the Service (its status() says whether it serves and why not)."""
    notes = ns.Notes(log=lambda note: log_note(host, note))
    service = ns.Service(notes)
    try:service.start()
    except Exception as exc:  # noqa: BLE001 - a bus that broke never stops the window
        service.state, service.why = 'failed', 'Kas could not offer its notifications: %s' % (str(exc)[:160] or type(exc).__name__)
    host.notifications = service
    host.notification_shelf = Shelf(host, service)
    app = QApplication.instance()
    if app is not None:app.aboutToQuit.connect(service.stop)
    host.destroyed.connect(lambda *_: service.stop())
    return service
