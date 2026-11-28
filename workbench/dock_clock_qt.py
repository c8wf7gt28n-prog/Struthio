"""The clock at the dock's right end (Graphite 1.1 W1): the time and the date; a press shows the month.

PLAN_1.1.md, W1 (d). The dock (system_dock_qt.Dock) stands in the dedicated session across the top of the screen; its right
end now says the time and the date ("14:05 · Sat 28 Nov"), read again at each new minute. A press opens a small page with the
month (a calendar, today marked by the calendar's own frame and in words under it); a press elsewhere or Esc closes it.

1.1 B1: the clock stands in the bar's clock slot (bar_qt.BarClock: the time over the date), and the month rises above a
clock that sits low on its screen.
"""
from __future__ import annotations

import time

from PySide6.QtCore import QDate, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QFontMetrics, QPainter
from PySide6.QtWidgets import QAbstractButton, QCalendarWidget, QFrame, QLabel, QVBoxLayout

from . import boss_theme as bt


def words(now=None):
    """('14:05', 'Sat 28 Nov', 'Saturday 28 November 2026'): the time, the date short, and in full for a reader."""
    t = time.localtime(now)
    return time.strftime('%H:%M', t), time.strftime('%a %d %b', t).replace(' 0', ' '), time.strftime('%A %d %B %Y', t).replace(' 0', ' ')


class Month(QFrame):
    """The month, shown under the clock."""

    def __init__(self, anchor):
        super().__init__(None, Qt.Popup | Qt.FramelessWindowHint)
        self.setObjectName('GraphiteMonth');self.setAccessibleName('The month')
        layout = QVBoxLayout(self);layout.setContentsMargins(8, 8, 8, 8)
        self.calendar = QCalendarWidget(self);self.calendar.setGridVisible(True)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.today = QLabel(self);self.today.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.calendar);layout.addWidget(self.today)
        self.anchor = anchor

    def open(self, now=None):
        self.calendar.setSelectedDate(QDate.currentDate());self.calendar.showToday()
        self.today.setText('Today is ' + words(now)[2])
        self.adjustSize()
        at = self.anchor.mapToGlobal(self.anchor.rect().bottomRight())
        top = self.anchor.mapToGlobal(self.anchor.rect().topRight())  # 1.1 B1: the clock on the bar at the bottom: the month rises above it
        screen = self.anchor.screen().geometry() if self.anchor.screen() is not None else None  # 1.1 B1
        if screen is not None and top.y() > screen.center().y():self.move(max(screen.left(), top.x() + 1 - self.width()), top.y() - self.height() - 6);self.show();return self  # 1.1 B1
        self.move(at.x() - self.width(), at.y() + 2);self.show()
        return self


class Clock(QAbstractButton):
    """The time and the date, at the dock's right end."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName('GraphiteClock');self.setFocusPolicy(Qt.NoFocus);self.setCursor(Qt.PointingHandCursor)
        self.month = None
        self.timer = QTimer(self);self.timer.setSingleShot(True);self.timer.timeout.connect(self.tick)
        self.clicked.connect(self.show_month)
        self.tick()

    def tick(self):
        clock, day, whole = words()
        self.setText('%s · %s' % (clock, day));self.setAccessibleName('%s, %s' % (clock, whole))
        self.setToolTip('%s · a press shows the month' % whole)
        self.update()
        self.timer.start(max(500, int((60 - time.time() % 60) * 1000) + 50))      # at the next minute

    def natural(self, h):
        return QFontMetrics(self.font()).horizontalAdvance(self.text()) + round(h * 0.8)

    def sizeHint(self):
        return QSize(self.natural(24), 24)

    def show_month(self):
        if self.month is None:self.month = Month(self)
        return self.month.open()

    def paintEvent(self, event):
        p = QPainter(self)
        if self.isDown() or self.underMouse():p.fillRect(self.rect(), QColor(bt.RAISED))
        p.setPen(QColor(bt.TEXT))
        p.drawText(self.rect().adjusted(0, 0, -round(self.height() * 0.4), 0), Qt.AlignRight | Qt.AlignVCenter, self.text())
        p.end()


def attach(dock):
    """system_dock_qt.Dock makes its clock here."""
    return Clock(dock)


def place(clock, dock, h):
    """The clock's room at the dock's right end: its width (taken off the strip's room)."""
    if clock is None:return 0
    w = clock.natural(h);clock.setGeometry(dock.width() - w, 0, w, h)
    return w
