"""The pulse: one small monitor beside Stop, in place of three separate chips (Slate's brain, "n running", nice levels).

    [cpu ▁▂▅▃]  [mem ▅▅▆▆]  ● Slate        Stop

Two pencil sparklines show the last minute of this computer's processor and memory; the dot says how Slate is (ring: no
brain, half: working, full: ready). Click it and it opens as a menu: the numbers in words, Slate's brain (choose, open,
stop), everything running or next on the Agenda with its nice level (now · normal · background), and the master Stop.
It only reads /proc and the Kernel; every change it offers goes through the same Kernel operations as the Agenda.
"""
from __future__ import annotations
import os
import shutil
from collections import deque
from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QMenu, QWidget
from .shell2 import AMBER, AMBER_EDGE, CARD, ERASER, ERASER_MARK, LINE, QUIET, SANS, TEXT, call, call_write

SAMPLES = 30  # one every two seconds: the last minute
NICE_WORDS = (('now', 'Now · ahead of everything'), ('normal', 'Normal'), ('background', 'Background · only when idle'))


def read_cpu():
    """(busy, total) jiffies from /proc/stat, or None where there is no /proc."""
    try:
        with open('/proc/stat') as f:parts = f.readline().split()[1:]
        values = [int(v) for v in parts[:8]];idle = values[3] + values[4]
        return sum(values) - idle, sum(values)
    except (OSError, ValueError, IndexError):return None


def read_memory():
    """(used, total) bytes from /proc/meminfo, or None."""
    try:
        info = {}
        with open('/proc/meminfo') as f:
            for line in f:
                key, _, rest = line.partition(':');info[key] = int(rest.split()[0]) * 1024
        return info['MemTotal'] - info.get('MemAvailable', info.get('MemFree', 0)), info['MemTotal']
    except (OSError, ValueError, KeyError):return None


def heading(menu, words):
    """A quiet heading in small capitals, like the Library's: menus here draw sections as bare lines."""
    if menu.actions():menu.addSeparator()
    a = menu.addAction(words.upper());a.setEnabled(False);f = a.font();f.setPixelSize(11);f.setLetterSpacing(QFont.AbsoluteSpacing, 1.2);a.setFont(f)
    return a


def gb(n):
    return '%.1f GB' % (n / 1e9)


class Pulse(QWidget):
    def __init__(self, host):
        super().__init__();self.host = host;self.setObjectName('Pulse');self.setCursor(Qt.PointingHandCursor)
        self.setAccessibleName('This computer and Graphite');self.cpu = deque([0.0] * SAMPLES, maxlen=SAMPLES)
        self.mem = deque([0.0] * SAMPLES, maxlen=SAMPLES);self._last = read_cpu();self.brain = {};self.active = [];self.next = []
        self.font = QFont(SANS);self.font.setPixelSize(15)
        self.timer = QTimer(self, interval=2000);self.timer.timeout.connect(self.sample);self.timer.start()
        self.slow = QTimer(self, interval=5000);self.slow.timeout.connect(self.refresh);self.slow.start()
        QTimer.singleShot(0, self.refresh);self.sample()

    def sizeHint(self):
        return QSize(160, 32)

    def minimumSizeHint(self):
        return QSize(160, 32)

    # reading --------------------------------------------------------------------------------------------------------
    def sample(self):
        now = read_cpu()
        if now and self._last and now[1] > self._last[1]:self.cpu.append((now[0] - self._last[0]) / (now[1] - self._last[1]))
        self._last = now
        m = read_memory()
        if m:self.mem.append(m[0] / m[1])
        self.update();self.setToolTip(self.summary())

    def refresh(self):
        self.brain = call(self.host, 'brain.status') or {}
        agenda = call(self.host, 'agenda.view') or {}
        self.active = agenda.get('now', []);self.next = agenda.get('next', [])
        self.update();self.setToolTip(self.summary())

    def slate_state(self):
        if self.active:return 'working'
        return {'READY': 'ready', 'MODEL_STOPPED': 'stopped'}.get(self.brain.get('state'), 'none')

    def slate_words(self):
        state = self.slate_state()
        if state == 'working':return 'Graphite · %d running' % len(self.active)
        if state == 'ready':
            name = None
            try:name = self.host.shell2.model_name(self.brain)
            except Exception:pass
            return 'Graphite · ' + (name or 'ready')
        return {'stopped': 'Graphite · brain stopped', 'none': 'Graphite · no brain yet'}[state]

    def summary(self):
        return 'Processor %d%% · memory %d%% · %s · click for more' % (round(self.cpu[-1] * 100), round(self.mem[-1] * 100), self.slate_words())

    # drawing --------------------------------------------------------------------------------------------------------
    def spark(self, p, rect, values, label):
        """A tally column, not a box: a small-caps heading, the last minute as a pencil wash, closed by a ruled baseline."""
        inner = rect.adjusted(0, 11, 0, -2);n = len(values);step = inner.width() / max(1, n - 1)
        line = QPainterPath()
        for i, v in enumerate(values):
            pt = QPointF(inner.left() + i * step, inner.bottom() - max(0.04, min(1.0, v)) * inner.height())  # a resting line, never invisible
            line.lineTo(pt) if i else line.moveTo(pt)
        fill = QPainterPath(line);fill.lineTo(inner.right(), inner.bottom());fill.lineTo(inner.left(), inner.bottom());fill.closeSubpath()
        hot = values[-1] > .85  # nearly full: the wash turns eraser pink, the only warning it gives
        p.setPen(Qt.NoPen);p.setBrush(QColor(ERASER if hot else AMBER));p.drawPath(fill)
        p.setPen(QPen(QColor(ERASER_MARK if hot else AMBER_EDGE), 1.4));p.setBrush(Qt.NoBrush);p.drawPath(line)
        p.setPen(QPen(QColor(LINE), 1));p.drawLine(QPointF(inner.left(), inner.bottom() + 1.5), QPointF(inner.right(), inner.bottom() + 1.5))
        f = QFont(self.font);f.setPixelSize(11);f.setCapitalization(QFont.SmallCaps);f.setLetterSpacing(QFont.AbsoluteSpacing, 1.0);p.setFont(f)
        p.setPen(QColor(QUIET));p.drawText(QRectF(rect.left(), rect.top() - 1, rect.width(), 12), Qt.AlignLeft | Qt.AlignTop, label)
        p.drawText(QRectF(rect.left(), rect.top() - 1, rect.width(), 12), Qt.AlignRight | Qt.AlignTop, '%d' % round(values[-1] * 100))

    def paintEvent(self, event):
        p = QPainter(self);p.setRenderHint(QPainter.Antialiasing)
        h = self.height();y = (h - 30) / 2
        self.spark(p, QRectF(.5, y, 50, 30), list(self.cpu), 'cpu')
        self.spark(p, QRectF(60.5, y, 50, 30), list(self.mem), 'mem')
        # the third column: Slate, headed like the others; the dot is his state (ring none, half working, full ready)
        f = QFont(self.font);f.setPixelSize(11);f.setCapitalization(QFont.SmallCaps);f.setLetterSpacing(QFont.AbsoluteSpacing, 1.0);p.setFont(f)
        p.setPen(QColor(QUIET));p.drawText(QRectF(120, y - 1, 40, 12), Qt.AlignLeft | Qt.AlignTop, 'slate')
        cx, cy, r = 127, y + 21, 5.5;state = self.slate_state()
        p.setPen(QPen(QColor(TEXT), 1.4));p.setBrush(QColor(CARD));p.drawEllipse(QPointF(cx, cy), r, r)
        p.setBrush(QColor(TEXT));p.setPen(Qt.NoPen)
        if state == 'ready':p.drawEllipse(QPointF(cx, cy), r - 1.5, r - 1.5)
        elif state == 'working':p.drawPie(QRectF(cx - r + 1.5, cy - r + 1.5, 2 * r - 3, 2 * r - 3), 90 * 16, 180 * 16)
        elif state == 'stopped':p.setBrush(QColor(ERASER_MARK));p.drawEllipse(QPointF(cx, cy), r - 1.5, r - 1.5)
        if self.active:
            f.setCapitalization(QFont.MixedCase);f.setPixelSize(12);p.setFont(f);p.setPen(QColor(TEXT))
            p.drawText(QRectF(cx + 9, cy - 8, 30, 16), Qt.AlignLeft | Qt.AlignVCenter, str(len(self.active)))

    # the menu ---------------------------------------------------------------------------------------------------------
    def mousePressEvent(self, event):
        if event.button() in (Qt.LeftButton, Qt.RightButton):self.open_menu()

    def menu(self):
        from .shell2 import open_destination
        self.refresh();m = QMenu(self);m.setObjectName('PulseMenu')
        cores = os.cpu_count() or 1
        try:load = '%.2f' % os.getloadavg()[0]
        except OSError:load = '–'
        mem = read_memory()
        info = [('Processor  %d%%  ·  %d cores  ·  load %s' % (round(self.cpu[-1] * 100), cores, load))]
        if mem:info.append('Memory  %s of %s in use' % (gb(mem[0]), gb(mem[1])))
        try:
            from . import files_service
            from .engine import engineering
            free = shutil.disk_usage(str(files_service.root(engineering(self.host.root)))).free;info.append('Disk  %s free where Files are' % gb(free))
        except Exception:pass
        heading(m, 'This computer')
        for line in info:m.addAction(line).setEnabled(False)
        computer = getattr(self.host, 'a_computer', None)
        if computer is not None:m.addAction('What this computer supports…', computer.trigger)
        heading(m, 'Graphite')
        m.addAction(self.slate_words()).setEnabled(False)
        if self.slate_state() == 'none':
            m.addAction('Choose a model…', lambda:open_destination(self.host, 'slate').pick_model())
        m.addAction('Talk to Stacy', lambda:self.host.shell2.show_slate_face())
        m.addAction('Brain room', lambda:open_destination(self.host, 'slate'))
        if self.brain.get('state') == 'READY':m.addAction('Stop the brain', lambda:(call_write(self.host, 'brain.stop', {}), self.refresh()))
        heading(m, 'Running and next')
        rows = [r for r in self.active + self.next if r.get('id')][:10]
        if not rows:m.addAction('Nothing is running.').setEnabled(False)
        for row in rows:
            title = str(row.get('title', ''))[:48];agenda_item = 'nice' in row
            mark = '◐  ' if row in self.active else '     '
            if not agenda_item:
                m.addAction(mark + title + '  ·  Kernel job', lambda:self.host.ledger_bridge.navigation()['trail']());continue
            sub = m.addMenu(mark + title + '  ·  ' + row['nice'])
            heading(sub, 'Nice')
            for key, words in NICE_WORDS:
                a = sub.addAction(words, lambda k=key, i=row['id']:(call_write(self.host, 'agenda.nice', {'id': i, 'nice': k}), self.refresh()))
                a.setCheckable(True);a.setChecked(row['nice'] == key)
            sub.addSeparator()
            if row.get('state') in ('NEXT',):sub.addAction('Pause', lambda i=row['id']:(call_write(self.host, 'agenda.pause', {'id': i}), self.refresh()))
            if row.get('state') == 'PAUSED':sub.addAction('Resume', lambda i=row['id']:(call_write(self.host, 'agenda.resume', {'id': i}), self.refresh()))
            sub.addAction('Cancel this', lambda i=row['id']:(call_write(self.host, 'agenda.cancel', {'id': i, 'reason': 'Cancelled from the pulse.'}), self.refresh()))
        m.addAction("Graphite's Agenda", lambda:open_destination(self.host, 'agenda'))
        stop = getattr(self.host, 'a_master_stop', None)
        if stop is not None:m.addSeparator();m.addAction(stop)
        try:
            from . import chain_icons
            chain_icons.dress(m)
        except Exception:pass
        return m

    def open_menu(self):
        m = self.menu();edge = self.host.master_stop_button
        at = edge.mapToGlobal(edge.rect().bottomRight());at.setX(at.x() - m.sizeHint().width());at.setY(self.mapToGlobal(self.rect().bottomLeft()).y() + 6)
        m.exec(at)
