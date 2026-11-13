"""The equalizer in the head of the window: this computer at work, as bars that rise and fall.

The owner, 13 November 2026, of the head's middle (where the name and address of what is open stood): "Let's just leave
it out in the middle. Free up the space ... an equalizer, and make its style pulse up and down to represent something."
And, having seen it show the processor alone: "Make the thinking/activity equalizer represent any and all data activity
available together actively showing SSD, RAM, GPU, CPU, kernel activity. Just a animated way to see that it's
working/reasoning/computing/busing data."

So it is one picture of everything that moves, in six groups, left to right, with a small gap between them:

  CPU   one bar for each processor thread (in pairs or fours when there are more than eight): how hard it worked
  KRN   the kernel: its share of the processor's time; and how fast it is switching between tasks and taking interrupts
  RAM   memory in use; and swapping (what is being moved between memory and the disk for want of room)
  SSD   the disks: being read; being written
  NET   the network: coming in; going out
  GPU   the graphics processor: how busy; and its own memory in use

What it shows is true, not ornament. Every height means one thing always: a share is drawn as that share; a rate
(bytes a second, switches a second) is drawn on a fixed logarithmic scale between a floor and a ceiling written below, so
the same height is the same rate today and tomorrow, and a quiet computer lies low. A source this computer does not have
(no graphics counter, say) rests, and the card says so. The top two lamps of a bar are amber: near its limit. A small
mark holds a bar's recent peak and sinks. While Graphite itself has work running, the bottom row is amber.

It moves only when the readings move: a bar glides to its new height in a few steps and stops, and with "reduce motion"
it changes at once. A click shows what each group reads now, in words.
"""
import math
import re
import time
from pathlib import Path

from PySide6.QtCore import QPoint, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QFrame, QLabel, QSizePolicy, QVBoxLayout, QWidget

from . import boss_theme as t

MOST = 8             # processor bars drawn; a computer with more threads shows them in equal groups
ROWS = 7             # lamps in a bar
EVERY = 500          # milliseconds between readings
STEP = 40            # milliseconds between frames while a bar glides
GROUPS = ('CPU', 'KRN', 'RAM', 'SSD', 'NET', 'GPU')
NAMES = {'CPU': 'Processor', 'KRN': 'Kernel', 'RAM': 'Memory', 'SSD': 'Disks', 'NET': 'Network', 'GPU': 'Graphics'}
# The fixed scales for rates: (floor, ceiling). At or under the floor a bar rests; at the ceiling it is full; between, logarithmic.
SCALES = {'switches': (500.0, 200000.0),         # task switches a second
          'interrupts': (300.0, 100000.0),       # interrupts a second
          'paging': (16e3, 500e6),               # bytes a second swapped in or out
          'disk': (16e3, 500e6),                 # bytes a second read or written
          'net': (1e3, 100e6)}                   # bytes a second in or out
WHOLE_DISK = re.compile(r'^(sd[a-z]+|vd[a-z]+|xvd[a-z]+|hd[a-z]+|nvme\d+n\d+|mmcblk\d+)$')      # a disk itself, not one of its partitions


def readings(path='/proc/stat'):
    """{thread number: (idle jiffies, all jiffies)} as the kernel counts them now; {} where it cannot be read."""
    out = {}
    try:
        with open(path) as stream:
            for line in stream:
                if not line.startswith('cpu') or line[3:4] in (' ', ''):continue
                parts = line.split()
                if not parts[0][3:].isdigit():continue
                counts = [int(n) for n in parts[1:9]]
                out[int(parts[0][3:])] = (counts[3] + (counts[4] if len(counts) > 4 else 0), sum(counts))
    except (OSError, ValueError, IndexError):
        return {}
    return out


def loads(before, now):
    """How hard each thread worked between two readings, 0 to 1, in thread order."""
    out = []
    for thread in sorted(now):
        if thread not in before:
            out.append(0.0);continue
        idle = now[thread][0] - before[thread][0];whole = now[thread][1] - before[thread][1]
        out.append(max(0.0, min(1.0, 1.0 - idle / whole)) if whole > 0 else 0.0)
    return out


def grouped(values, most=MOST):
    """At most `most` bars: with more threads than that, neighbours are averaged in equal groups."""
    if len(values) <= most:return list(values)
    size = -(-len(values) // most)
    return [sum(values[i:i + size]) / len(values[i:i + size]) for i in range(0, len(values), size)]


def scaled(rate, floor, ceiling):
    """A rate on its fixed logarithmic scale: 0 at or under the floor, 1 at or over the ceiling."""
    if rate is None or rate <= floor:return 0.0
    if rate >= ceiling:return 1.0
    return math.log(rate / floor) / math.log(ceiling / floor)


def kernel_counts(path='/proc/stat'):
    """{'system': jiffies in the kernel (system, irq, softirq), 'all': all jiffies, 'switches': n, 'interrupts': n}; {} if unreadable."""
    out = {}
    try:
        with open(path) as stream:
            for line in stream:
                parts = line.split()
                if not parts:continue
                if parts[0] == 'cpu':
                    counts = [int(n) for n in parts[1:9]]
                    out['system'] = counts[2] + (counts[5] if len(counts) > 5 else 0) + (counts[6] if len(counts) > 6 else 0);out['all'] = sum(counts)
                elif parts[0] == 'ctxt':out['switches'] = int(parts[1])
                elif parts[0] == 'intr':out['interrupts'] = int(parts[1])
    except (OSError, ValueError, IndexError):
        return {}
    return out


def memory_counts(meminfo='/proc/meminfo', vmstat='/proc/vmstat'):
    """{'used': share of memory in use, 0 to 1, 'paged': bytes swapped in and out since the computer started}; a part that
    cannot be read is left out."""
    out = {}
    try:
        info = {}
        with open(meminfo) as stream:
            for line in stream:
                key, _, text = line.partition(':')
                if key in ('MemTotal', 'MemAvailable'):info[key] = int(text.split()[0])
        if info.get('MemTotal', 0) > 0 and 0 <= info.get('MemAvailable', -1) <= info['MemTotal']:
            out['used'] = 1.0 - info['MemAvailable'] / info['MemTotal']
    except (OSError, ValueError, IndexError):
        pass
    try:
        # Swapping, not all disk traffic: pswpin and pswpout count pages moved between memory and swap (pgpgin and pgpgout
        # count every block read or written, which is the disks' own bars over again).
        paged = 0;seen = False
        with open(vmstat) as stream:
            for line in stream:
                key, _, text = line.partition(' ')
                if key in ('pswpin', 'pswpout'):paged += int(text) * 4096;seen = True      # counted in pages
        if seen:out['paged'] = paged
    except (OSError, ValueError):
        pass
    return out


def disk_counts(path='/proc/diskstats'):
    """{'read': bytes read, 'written': bytes written} over the whole disks (not their partitions); {} if unreadable."""
    read = written = 0;seen = False
    try:
        with open(path) as stream:
            for line in stream:
                parts = line.split()
                if len(parts) < 10 or not WHOLE_DISK.match(parts[2]):continue
                read += int(parts[5]) * 512;written += int(parts[9]) * 512;seen = True      # sectors are 512 bytes here whatever the disk's own
    except (OSError, ValueError, IndexError):
        return {}
    return {'read': read, 'written': written} if seen else {}


def net_counts(path='/proc/net/dev'):
    """{'in': bytes received, 'out': bytes sent} over every interface but the loopback; {} if unreadable."""
    got = sent = 0;seen = False
    try:
        with open(path) as stream:
            for line in stream:
                name, colon, rest = line.partition(':')
                if not colon or name.strip() == 'lo':continue
                parts = rest.split()
                if len(parts) < 9:continue
                got += int(parts[0]);sent += int(parts[8]);seen = True
    except (OSError, ValueError, IndexError):
        return {}
    return {'in': got, 'out': sent} if seen else {}


def gpu_counts(root='/sys/class/drm'):
    """{'busy': 0 to 1, 'memory': share of the graphics memory in use} from the busiest adapter that reports; a part that
    is not reported is left out (many drivers report neither)."""
    out = {}
    try:cards = sorted(card / 'device' for card in Path(root).iterdir() if re.fullmatch(r'card\d+', card.name))[:8]      # the cards themselves, not their connectors (card0-DP-1 ...)
    except OSError:return out
    for card in cards:
        try:
            busy = int((card / 'gpu_busy_percent').read_text()[:32].strip())
            if 0 <= busy <= 100:out['busy'] = max(out.get('busy', 0.0), busy / 100.0)
        except (OSError, ValueError):
            pass
        try:
            used = int((card / 'mem_info_vram_used').read_text()[:32].strip());whole = int((card / 'mem_info_vram_total').read_text()[:32].strip())
            if whole > 0 and 0 <= used <= whole:out['memory'] = max(out.get('memory', 0.0), used / whole)
        except (OSError, ValueError):
            pass
    return out


def amount(per_second):
    """A rate of bytes in words: '12 MB/s'."""
    if per_second is None:return 'not reported'
    for unit, size in (('GB', 1e9), ('MB', 1e6), ('kB', 1e3)):
        if per_second >= size:return '%.0f %s/s' % (per_second / size, unit) if per_second >= 10 * size else '%.1f %s/s' % (per_second / size, unit)
    return '%d B/s' % per_second


class Activity:
    """Everything that moves, read twice and compared: for each group its bars (0 to 1) and what it reads in words.
    The paths can be given (the tests give their own); the clock can be given too."""

    def __init__(self, stat='/proc/stat', meminfo='/proc/meminfo', vmstat='/proc/vmstat', diskstats='/proc/diskstats', netdev='/proc/net/dev',
                 drm='/sys/class/drm', clock=time.monotonic):
        self.paths = dict(stat=stat, meminfo=meminfo, vmstat=vmstat, diskstats=diskstats, netdev=netdev, drm=drm);self.clock = clock
        self.before = None;self.threads = max(1, len(readings(stat)))

    def raw(self):
        p = self.paths
        return dict(at=self.clock(), threads=readings(p['stat']), kernel=kernel_counts(p['stat']), memory=memory_counts(p['meminfo'], p['vmstat']),
                    disk=disk_counts(p['diskstats']), net=net_counts(p['netdev']), gpu=gpu_counts(p['drm']))

    def sample(self):
        """{'bars': {group: [0..1, ...]}, 'words': {group: what it reads now}, 'missing': [groups this computer does not report]}.
        The first sample has nothing to compare with: everything that is a rate rests."""
        now = self.raw();before, self.before = self.before, now
        span = max(1e-3, now['at'] - before['at']) if before else None

        def rate(group, key):
            if not before or key not in now[group] or key not in before[group]:return None
            return max(0.0, (now[group][key] - before[group][key]) / span)

        bars = {};words = {};missing = []
        threads = loads(before['threads'], now['threads']) if before else [0.0] * len(now['threads'])
        bars['CPU'] = grouped(threads) or [0.0]
        words['CPU'] = ('%d threads, %d%% at work' % (len(threads), round(100 * sum(threads) / len(threads)))) if threads else 'not reported'
        if not now['threads']:missing.append('CPU')
        share = None
        if before and now['kernel'].get('all', 0) > before['kernel'].get('all', 0):
            share = max(0.0, min(1.0, (now['kernel']['system'] - before['kernel']['system']) / (now['kernel']['all'] - before['kernel']['all'])))
        switches = rate('kernel', 'switches');interrupts = rate('kernel', 'interrupts')
        bars['KRN'] = [share or 0.0, max(scaled(switches, *SCALES['switches']), scaled(interrupts, *SCALES['interrupts']))]
        words['KRN'] = ('%d%% of the processor; %s task switches and %s interrupts a second' % (
            round(100 * (share or 0.0)), 'no' if not switches else format(round(switches), ','), 'no' if not interrupts else format(round(interrupts), ','))
            if now['kernel'] else 'not reported')
        if not now['kernel']:missing.append('KRN')
        used = now['memory'].get('used');paged = rate('memory', 'paged')
        bars['RAM'] = [used or 0.0, scaled(paged, *SCALES['paging'])]
        words['RAM'] = ('%d%% in use; %s' % (round(100 * used), 'swapping not reported' if paged is None else 'not swapping' if paged < 1 else 'swapping ' + amount(paged))) if used is not None else 'not reported'
        if used is None:missing.append('RAM')
        read = rate('disk', 'read');written = rate('disk', 'written')
        bars['SSD'] = [scaled(read, *SCALES['disk']), scaled(written, *SCALES['disk'])]
        words['SSD'] = ('reading %s, writing %s' % (amount(read or 0.0), amount(written or 0.0))) if now['disk'] else 'no disk is reported here'
        if not now['disk']:missing.append('SSD')
        got = rate('net', 'in');sent = rate('net', 'out')
        bars['NET'] = [scaled(got, *SCALES['net']), scaled(sent, *SCALES['net'])]
        words['NET'] = ('in %s, out %s' % (amount(got or 0.0), amount(sent or 0.0))) if now['net'] else 'no network interface is reported here'
        if not now['net']:missing.append('NET')
        gpu = now['gpu']
        bars['GPU'] = [gpu.get('busy', 0.0), gpu.get('memory', 0.0)]
        words['GPU'] = ('; '.join(part for part in (('%d%% busy' % round(100 * gpu['busy'])) if 'busy' in gpu else '',
                                                    ('%d%% of its memory in use' % round(100 * gpu['memory'])) if 'memory' in gpu else '') if part)
                        if gpu else 'this graphics driver reports nothing')
        if not gpu:missing.append('GPU')
        return {'bars': bars, 'words': words, 'missing': missing}


class Equalizer(QWidget):
    def __init__(self, host, activity=None):
        super().__init__(host)
        self.host = host;self.setObjectName('HeadEqualizer');self.setAccessibleName('This computer at work')
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed);self.setCursor(Qt.PointingHandCursor)
        self.activity = activity or Activity();first = self.activity.sample()
        self.sizes = [len(first['bars'][group]) for group in GROUPS];self.words = first['words'];self.missing = first['missing']
        self.target = [value for group in GROUPS for value in first['bars'][group]];self.shown = list(self.target);self.peak = list(self.target)
        self.busy = False;self.still = None;self.readable = 'CPU' not in self.missing;self.card = None
        self.clock = QTimer(self);self.clock.setInterval(EVERY);self.clock.timeout.connect(self.read)
        self.glide = QTimer(self);self.glide.setInterval(STEP);self.glide.timeout.connect(self.move)
        self.setToolTip('This computer at work, left to right: processor, kernel, memory, disks, network, graphics. Amber along the bottom while Graphite itself is working. Click for what each reads now.')

    def sizeHint(self):
        return QSize(max(120, len(self.target) * 7 + (len(GROUPS) - 1) * 5 + 3), 40)

    def showEvent(self, event):
        super().showEvent(event)
        if not self.clock.isActive():self.clock.start()

    def hideEvent(self, event):
        super().hideEvent(event);self.clock.stop();self.glide.stop()

    def calm(self):
        try:return bool(self.still()) if callable(self.still) else False
        except Exception:  # noqa: BLE001 - how it moves is never worth an error
            return True

    def read(self):
        if getattr(self.host, '_closing', False):return
        try:got = self.activity.sample()
        except Exception:  # noqa: BLE001 - a counter that could not be read this once: the bars stay as they are
            return
        fresh = [value for group in GROUPS for value in got['bars'][group]];self.words = got['words'];self.missing = got['missing']
        if len(fresh) != len(self.target):      # a processor thread came or went: the bars are laid out again
            self.sizes = [len(got['bars'][group]) for group in GROUPS];self.shown = list(fresh);self.peak = list(fresh);self.updateGeometry()
        self.target = fresh
        if self.card is not None and self.card.isVisible():self.card.say(self.words)
        if self.calm():
            self.shown = list(fresh);self.peak = list(fresh);self.update()
        elif not self.glide.isActive():self.glide.start()

    def move(self):
        settled = True
        if not (len(self.shown) == len(self.target) == len(self.peak)):      # never out of step with what was last read
            self.shown = list(self.target);self.peak = list(self.target)
        for i, goal in enumerate(self.target):
            gap = goal - self.shown[i]
            if abs(gap) > 0.01:
                self.shown[i] += gap * 0.38;settled = False
            else:self.shown[i] = goal
            if self.shown[i] >= self.peak[i]:self.peak[i] = self.shown[i]
            elif self.peak[i] - self.shown[i] > 0.01:
                self.peak[i] = max(self.shown[i], self.peak[i] - 0.035);settled = False
        if settled:self.glide.stop()
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.rect().contains(event.position().toPoint()):self.show_card()
        super().mouseReleaseEvent(event)

    def show_card(self):
        """What each group reads now, in words, under the equalizer; a click anywhere else puts it away."""
        if self.card is None:self.card = ActivityCard(self.host)
        if self.card.isVisible():
            self.card.hide();return self.card
        self.card.say(self.words);self.card.adjustSize()
        at = self.mapToGlobal(QPoint(self.width() // 2 - self.card.width() // 2, self.height() + 6));self.card.move(at);self.card.show()
        return self.card

    def paintEvent(self, event):
        p = QPainter(self);n = len(self.shown)
        if not n:
            p.end();return
        try:
            from .boss_qt import glows
            level = t.glow() if glows(self.host) else 0.0
        except Exception:  # noqa: BLE001 - it is drawn whatever else is the matter
            level = 0.0
        between = 5.0;groups = [size for size in self.sizes if size] or [n]
        wide = max(3.0, (self.width() - 3.0 - between * (len(groups) - 1)) / n - 2.0)
        tall = max(2.0, (self.height() - 8.0 - (ROWS - 1) * 2.0) / ROWS);foot = self.height() - 4.0
        x = 1.5;i = 0
        for size in groups:
            for _ in range(size):
                if i >= n:break
                value = self.shown[i];lit = 0 if value < 0.02 else max(1, round(value * ROWS))
                for row in range(ROWS):
                    y = foot - (row + 1) * tall - row * 2.0;box = QRectF(x, y, wide, tall)
                    if row < lit:
                        colour = QColor(t.AMBER_EDGE if row >= ROWS - 2 else t.READY)       # the top of a bar is amber: near its limit
                        if level > 0:
                            halo = QColor(colour);halo.setAlphaF(min(0.34, 0.085 * level));p.fillRect(box.adjusted(-2.0, -1.5, 2.0, 1.5), halo)
                        p.fillRect(box, colour)
                    else:
                        rest = QColor(t.AMBER_EDGE if self.busy and row == 0 else t.TEAL_EDGE);rest.setAlphaF(0.75 if self.busy and row == 0 else 0.22)
                        p.fillRect(box, rest)
                high = round(self.peak[i] * ROWS) if i < len(self.peak) else 0
                if high > lit and high > 0:                                                  # the peak it reached a moment ago, sinking
                    y = foot - high * tall - (high - 1) * 2.0;mark = QColor(t.TEAL_TEXT);mark.setAlphaF(0.8);p.fillRect(QRectF(x, y, wide, 1.5), mark)
                x += wide + 2.0;i += 1
            x += between
        p.end()


class ActivityCard(QFrame):
    """The equalizer's card: each group by name with what it reads now. A dark plate under the equalizer; it goes when
    anything else is clicked."""

    def __init__(self, host):
        super().__init__(host, Qt.Popup);self.setObjectName('ActivityCard');self.lines = {}
        self.setStyleSheet('QFrame#ActivityCard {background:%s;border:1px solid %s;} QLabel {background:transparent;color:%s;} QLabel[role="name"] {color:%s;}'
                           % (t.RAISED, t.LINE_MID, t.TEXT, t.TEAL_TEXT))
        box = QVBoxLayout(self);box.setContentsMargins(14, 10, 14, 12);box.setSpacing(4)
        head = QLabel('This computer, now');head.setProperty('role', 'name');box.addWidget(head)
        for group in GROUPS:
            line = QLabel();line.setTextFormat(Qt.PlainText);line.setMinimumWidth(330);box.addWidget(line);self.lines[group] = line

    def say(self, words):
        for group in GROUPS:self.lines[group].setText('%s: %s' % (NAMES[group], words.get(group, 'not reported')))
