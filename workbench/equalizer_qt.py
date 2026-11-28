"""The equalizer in the head of the window: this computer at work, as bars that rise and fall.

The owner, 13 November 2026, of the head's middle (where the name and address of what is open stood): "Let's just leave
it out in the middle. Free up the space ... an equalizer, and make its style pulse up and down to represent something."
And, having seen it show the processor alone: "Make the thinking/activity equalizer represent any and all data activity
available together actively showing SSD, RAM, GPU, CPU, kernel activity. Just a animated way to see that it's
working/reasoning/computing/busing data."

0.8.6, the owner, 20 November 2026: the equalizer moves upper left, over the left column, and "Now just work the upper
left equalizer to be radical". Of the four styles drawn for him the default is D, neon tubes over a scope: glowing rounded
tubes in the look's colours (neon_meters.palette), floating peak dots that sink, a faint grid floor, and behind them a
glowing trace of all activity over the last two minutes. With the room upper left every processor thread has its own tube.

So it is one picture of everything that moves, in six groups, left to right, with a small gap between them:

  CPU   one tube for each processor thread, up to MOST (16); more threads than that are averaged in equal groups
  KRN   the kernel: its share of the processor's time; and how fast it is switching between tasks and taking interrupts
  RAM   memory in use; and swapping (what is being moved between memory and the disk for want of room)
  SSD   the disks: being read; being written
  NET   the network: coming in; going out
  GPU   the graphics processor: how busy; and its own memory in use

What it shows is true, not ornament. Every height means one thing always: a share is drawn as that share; a rate
(bytes a second, switches a second) is drawn on a fixed logarithmic scale between a floor and a ceiling written below, so
the same height is the same rate today and tomorrow, and a quiet computer lies low. A source this computer does not have
(no graphics counter, say) rests (its tubes a dim stub) and the card says so. A tube at NEAR (0.8) or more is amber: near
its limit, and the card says which, in words. A dot holds a tube's recent peak and sinks. The trace behind the tubes is the
average of the groups this computer reports (each group's own mean), over the last two minutes, oldest at the left; the card
says what it stands at now. While Graphite itself has work running, the floor's front line is amber.

It moves only when the readings move: a tube glides to its new height in a few steps and stops, and a change too small to
see is not glided at all. With "reduce motion" it is held still: nothing glides or sinks, it is read every two seconds and
changes at once. It is cheap: the floor is drawn once per size, the trace once per reading, the tubes as a few strokes;
`spent` keeps the time it takes, for checks. A click shows what each group reads now, in words.
"""
import math
import re
import time
from collections import deque
from pathlib import Path

from PySide6.QtCore import QPoint, QPointF, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QFrame, QLabel, QSizePolicy, QVBoxLayout, QWidget

from . import boss_theme as t
from .neon_meters import NEAR, faint, glow_level, mix, palette, ramp

MOST = 16            # processor tubes drawn (0.8.6: one a thread up to 16); a computer with more shows them in equal groups
ROWS = 7             # the old lamps in a bar (0.5.3 to 0.8.5), kept for callers
EVERY = 500          # milliseconds between readings
STILL = 2000         # milliseconds between readings with reduce motion
STEP = 40            # milliseconds between frames while a tube glides
SCOPE = 120.0        # seconds of the trace behind the tubes
SHADES = 20          # the ramp's colours drawn as tubes once (Equalizer.sprites), besides the hot one
GLIDE = 0.5          # the share of the way a tube goes to its new height in a frame
SINK = 0.05          # how far a peak's dot sinks in a frame
PARTS = {'KRN': ('its share', 'switching'), 'RAM': ('in use', 'swapping'), 'SSD': ('reading', 'writing'), 'NET': ('in', 'out'),
         'GPU': ('busy', 'its memory')}      # what each tube of a pair is, for the card's words
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


def whole(bars, missing=()):
    """The trace's height: the average of the groups this computer reports, each group's own mean (0 to 1)."""
    means = [sum(bars[group]) / len(bars[group]) for group in GROUPS if group not in missing and bars.get(group)]
    return sum(means) / len(means) if means else 0.0


def near(bars, missing=()):
    """{group: words for its tubes at NEAR or more}: what the card says of what is drawn amber."""
    out = {}
    for group in GROUPS:
        values = bars.get(group) or []
        if group in missing:continue
        if group == 'CPU':
            hot = sum(1 for v in values if v >= NEAR)
            if hot:out[group] = '%d of %d %s near %s limit' % (hot, len(values), 'tube' if len(values) == 1 else 'tubes', 'its' if hot == 1 else 'their')
        else:
            hot = [PARTS[group][i] for i, v in enumerate(values[:2]) if v >= NEAR]
            if hot:out[group] = 'near its limit: ' + ' and '.join(hot)
    return out


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
        self.near = near(first['bars'], self.missing);self.trace = deque(maxlen=int(SCOPE * 1000 / EVERY) + 8)
        self.trace.append((time.monotonic(), whole(first['bars'], self.missing)))
        self.busy = False;self.still = None;self.readable = 'CPU' not in self.missing;self.card = None
        self._floor = None;self._scope = None;self._places = None;self._sprites = None
        self.spent = {'read': [0.0, 0], 'move': [0.0, 0], 'paint': [0.0, 0]}      # seconds and calls, for checks
        self.clock = QTimer(self);self.clock.setInterval(EVERY);self.clock.timeout.connect(self.read)
        self.glide = QTimer(self);self.glide.setInterval(STEP);self.glide.timeout.connect(self.move)
        self.setToolTip('This computer at work, left to right: processor (a tube a thread), kernel, memory, disks, network, graphics. '
                        'Amber is near its limit; the trace behind is the last two minutes of all of it; amber along the floor while '
                        'Kas itself is working. Click for what each reads now.')

    def sizeHint(self):
        return QSize(max(160, len(self.target) * 9 + (len(GROUPS) - 1) * 8 + 4), 44)

    def showEvent(self, event):
        super().showEvent(event)
        if not self.clock.isActive():self.clock.start()

    def hideEvent(self, event):
        super().hideEvent(event);self.clock.stop();self.glide.stop()

    def resizeEvent(self, event):
        super().resizeEvent(event);self._floor = None;self._scope = None;self._places = None;self._sprites = None

    def calm(self):
        try:return bool(self.still()) if callable(self.still) else False
        except Exception:  # noqa: BLE001 - how it moves is never worth an error
            return True

    def read(self):
        if getattr(self.host, '_closing', False):return
        started = time.perf_counter()
        try:
            try:got = self.activity.sample()
            except Exception:  # noqa: BLE001 - a counter that could not be read this once: the tubes stay as they are
                return
            fresh = [value for group in GROUPS for value in got['bars'][group]];self.words = got['words'];self.missing = got['missing']
            self.near = near(got['bars'], self.missing);self.trace.append((time.monotonic(), whole(got['bars'], self.missing)));self._scope = None
            calm = self.calm();every = STILL if calm else EVERY
            if self.clock.interval() != every:self.clock.setInterval(every)
            if len(fresh) != len(self.target):      # a processor thread came or went: the tubes are laid out again
                self.sizes = [len(got['bars'][group]) for group in GROUPS];self.shown = list(fresh);self.peak = list(fresh);self._places = None;self.updateGeometry()
            self.target = fresh
            if self.card is not None and self.card.isVisible():self.card.say(self.words, self.near, self.trace[-1][1])
            seen = 1.0 / max(8.0, self.height() * 0.7)      # a change of less than about a pixel is not glided
            if calm:self.glide.stop()
            if calm or (not self.glide.isActive() and all(abs(a - b) < seen for a, b in zip(fresh, self.shown))
                        and all(pk - v < seen for pk, v in zip(self.peak, fresh))):
                self.shown = list(fresh);self.peak = list(fresh) if calm else [max(v, pk) for v, pk in zip(fresh, self.peak)];self.update()
            elif not self.glide.isActive():self.glide.start()
        finally:
            spent = self.spent['read'];spent[0] += time.perf_counter() - started;spent[1] += 1

    def move(self):
        started = time.perf_counter();settled = True
        if not (len(self.shown) == len(self.target) == len(self.peak)):      # never out of step with what was last read
            self.shown = list(self.target);self.peak = list(self.target)
        for i, goal in enumerate(self.target):
            gap = goal - self.shown[i]
            if abs(gap) > 0.015:
                self.shown[i] += gap * GLIDE;settled = False
            else:self.shown[i] = goal
            if self.shown[i] >= self.peak[i]:self.peak[i] = self.shown[i]
            elif self.peak[i] - self.shown[i] > 0.015:
                self.peak[i] = max(self.shown[i], self.peak[i] - SINK);settled = False      # the peak's dot sinks
            else:self.peak[i] = self.shown[i]
        if settled:self.glide.stop()
        self.update()
        spent = self.spent['move'];spent[0] += time.perf_counter() - started;spent[1] += 1

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.rect().contains(event.position().toPoint()):self.show_card()
        super().mouseReleaseEvent(event)

    def show_card(self):
        """What each group reads now, in words, under the equalizer; a click anywhere else puts it away."""
        if self.card is None:self.card = ActivityCard(self.host)
        if self.card.isVisible():
            self.card.hide();return self.card
        self.card.say(self.words, self.near, self.trace[-1][1] if self.trace else 0.0);self.card.adjustSize()
        at = self.mapToGlobal(QPoint(max(0, self.width() // 2 - self.card.width() // 2), self.height() + 6));self.card.move(at);self.card.show()
        return self.card

    # The drawing (style D) ------------------------------------------------------------------------------------------------
    def geometry_(self):
        """(base, top): the floor's front line and the highest a tube reaches (room above for its peak's dot)."""
        h = self.height();return h - max(6, round(h * 0.19)), 5.0

    def places(self):
        """(left edges, tube width), whole pixels: the tubes in their groups, a small gap between tubes and a wider one
        between groups, centred when a few threads leave room."""
        key = (self.width(), tuple(self.sizes))
        if self._places is not None and self._places[0] == key:return self._places[1]
        groups = [size for size in self.sizes if size] or [1];n = sum(groups);w = self.width()
        gap, between = (3, 8) if w / n >= 9 else (2, 6)
        wide = max(2, min(12, (w - 4 - between * (len(groups) - 1) - gap * (n - len(groups))) // n))
        used = wide * n + between * (len(groups) - 1) + gap * (n - len(groups));x = (w - used) // 2;xs = []
        for size in groups:
            for j in range(size):
                xs.append(x);x += wide + (gap if j < size - 1 else 0)
            x += between
        self._places = (key, (xs, wide))
        return xs, wide

    def floor(self, colours):
        """The faint grid floor, drawn once per size: lines going back, and lines to a vanishing point at the middle."""
        if self._floor is not None:return self._floor
        dpr = self.devicePixelRatioF();w, h = self.width(), self.height();base, _ = self.geometry_()
        image = QPixmap(max(1, round(w * dpr)), max(1, round(h * dpr)));image.setDevicePixelRatio(dpr);image.fill(Qt.transparent)
        p = QPainter(image);p.setRenderHint(QPainter.Antialiasing);deep = h - base
        for k in range(1, 5):
            y = base + 1 + deep * (k * k) / 17.0;p.setPen(QPen(faint(colours['grid'], 0.75 - k * 0.13), 1));p.drawLine(QPointF(0, y), QPointF(w, y))
        p.setPen(QPen(faint(colours['grid'], 0.42), 1));vp = w / 2.0
        for k in range(-10, 11):p.drawLine(QPointF(vp + k * w / 50.0, base + 1), QPointF(vp + k * w / 8.0, h))
        p.setPen(QPen(faint(colours['grid'], 0.9), 1));p.drawLine(QPointF(0, base + 0.5), QPointF(w, base + 0.5))
        p.end();self._floor = image
        return image

    def scope(self, colours, level):
        """The glowing trace of the last two minutes behind the tubes, drawn once per reading."""
        if self._scope is not None and self._scope[0] == level:return self._scope[1]
        dpr = self.devicePixelRatioF();w, h = self.width(), self.height();base, top = self.geometry_()
        image = QPixmap(max(1, round(w * dpr)), max(1, round(h * dpr)));image.setDevicePixelRatio(dpr);image.fill(Qt.transparent)
        if self.trace:
            now = self.trace[-1][0];path = QPainterPath();first = True
            for when, value in self.trace:
                x = (w - 1.0) - (now - when) / SCOPE * (w - 1.0)
                if x < -4:continue
                point = QPointF(x, base - 3.0 - value * (base - top - 6.0))
                if first:path.moveTo(point);first = False
                else:path.lineTo(point)
            p = QPainter(image);p.setRenderHint(QPainter.Antialiasing)
            if level > 0:
                p.setPen(QPen(faint(colours['trace'], min(0.3, 0.07 * level)), 4.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin));p.drawPath(path)
            p.setPen(QPen(faint(colours['trace'], 0.62), 1.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin));p.drawPath(path)
            p.end()
        self._scope = (level, image)
        return image

    def sprites(self, colours, level, wide, span):
        """The tubes, drawn once: for each of SHADES colours of the ramp (and the hot one) a full-height tube with its bright
        core, and its light; a tube of any height is the top of one of them, so a frame is a few copies, not drawing. And
        the peak's dot with its light. Kept until the size, the glow or the look changes."""
        dpr = self.devicePixelRatioF();key = (wide, int(span), round(level * 10), t.APPEARANCE, round(dpr * 100))
        if self._sprites is not None and self._sprites[0] == key:return self._sprites[1]
        m = int(wide // 2 + 5);sw = wide + 2 * m;sh = int(span) + m + 2;radius = min(3.0, wide / 2.0)

        def canvas(width, height):
            image = QPixmap(max(1, round(width * dpr)), max(1, round(height * dpr)));image.setDevicePixelRatio(dpr);image.fill(Qt.transparent);return image
        shades = [ramp(min(NEAR - 1e-6, (i + 0.5) / SHADES * NEAR), colours) for i in range(SHADES)] + [colours['hot']]
        tubes = []
        for colour in shades:
            body = canvas(sw, sh);p = QPainter(body);p.setRenderHint(QPainter.Antialiasing);p.setPen(Qt.NoPen)
            p.setBrush(colour);p.drawRoundedRect(QRectF(m, m, wide, sh), radius, radius)      # runs past the bottom: a flat foot
            if wide >= 5:
                p.setBrush(faint(mix(colour, '#ffffff', 0.45), 0.55));p.drawRoundedRect(QRectF(m + wide * 0.3, m + 1.5, wide * 0.4, sh), wide * 0.2, wide * 0.2)
            p.end()
            light = None
            if level > 0:
                light = canvas(sw, sh);p = QPainter(light);p.setRenderHint(QPainter.Antialiasing);cx = sw / 2.0
                for reach, alpha in ((wide + 7.0, 0.05), (wide + 3.5, 0.11)):
                    p.setPen(QPen(faint(colour, min(0.5, alpha * level)), reach, Qt.SolidLine, Qt.RoundCap))
                    p.drawLine(QPointF(cx, m + reach / 2.0 - 1.0), QPointF(cx, sh + reach))
                p.end()
            tubes.append((body, light))
        dot = max(1.2, min(1.8, wide * 0.22));ds = int(dot * 5 + 4);spot = canvas(ds, ds)
        p = QPainter(spot);p.setRenderHint(QPainter.Antialiasing);p.setPen(Qt.NoPen);c = QPointF(ds / 2.0, ds / 2.0)
        if level > 0:p.setBrush(faint(colours['peak'], min(0.35, 0.09 * level)));p.drawEllipse(c, dot * 2.4, dot * 2.4)
        p.setBrush(colours['peak']);p.drawEllipse(c, dot, dot);p.end()
        made = (m, sw, tubes, spot, ds)
        self._sprites = (key, made)
        return made

    def paintEvent(self, event):
        started = time.perf_counter()
        n = len(self.shown)
        if not n or self.width() < 8 or self.height() < 12:return
        colours = palette();level = glow_level(self.host) if self.host is not None else 0.0;calm = self.calm()
        p = QPainter(self)
        try:
            p.drawPixmap(0, 0, self.floor(colours));p.drawPixmap(0, 0, self.scope(colours, level))
            base, top = self.geometry_();span = base - top - 2.0;xs, wide = self.places();dpr = self.devicePixelRatioF()
            m, sw, tubes, spot, ds = self.sprites(colours, level, wide, span)
            resting = set();at = 0
            for group, size in zip(GROUPS, self.sizes):
                if group in self.missing:resting.update(range(at, at + size))
                at += size
            standing = []
            for i, x in enumerate(xs[:n]):
                value = self.shown[i]
                if i in resting or value < 0.02:      # at rest: a dim stub, so the picture keeps its shape
                    p.fillRect(QRectF(x, base - 2, wide, 2), colours['rest']);continue
                shade = len(tubes) - 1 if value >= NEAR else min(SHADES - 1, int(value / NEAR * SHADES))
                standing.append((x, max(2, round(value * span)), tubes[shade]))
            if level > 0:      # the tubes' light; in Kasandra added as light, so her amber is never mixed over her cyan
                if t.APPEARANCE == 'kasandra':p.save();t.lays_light(p)
                for x, tall, (body, light) in standing:
                    p.drawPixmap(QRectF(x - m, base - tall - m, sw, tall + m), light, QRectF(0, 0, sw * dpr, (tall + m) * dpr))
                if t.APPEARANCE == 'kasandra':p.restore()
            for x, tall, (body, light) in standing:
                p.drawPixmap(QRectF(x - m, base - tall - m, sw, tall + m), body, QRectF(0, 0, sw * dpr, (tall + m) * dpr))
            if not calm:      # the peaks' dots, sinking
                for i, x in enumerate(xs[:n]):
                    high = self.peak[i] if i < len(self.peak) else 0.0
                    if i in resting or high < 0.04:continue
                    p.drawPixmap(round(x + wide / 2.0 - ds / 2.0), round(base - high * span - 3.0 - ds / 2.0), spot)
            if self.busy:      # Graphite itself at work: the floor's front line in amber
                p.fillRect(QRectF(0, base, self.width(), 2), colours['hot'])
        finally:
            p.end()
            spent = self.spent['paint'];spent[0] += time.perf_counter() - started;spent[1] += 1


class ActivityCard(QFrame):
    """The equalizer's card: each group by name with what it reads now, and in words what is drawn amber (near its limit)
    and what the trace stands at. A dark plate under the equalizer; it goes when anything else is clicked."""

    def __init__(self, host):
        super().__init__(host, Qt.Popup);self.setObjectName('ActivityCard');self.lines = {}
        self.setStyleSheet('QFrame#ActivityCard {background:%s;border:1px solid %s;} QLabel {background:transparent;color:%s;} QLabel[role="name"] {color:%s;} '
                           'QLabel[role="note"] {color:%s;}' % (t.RAISED, t.LINE_MID, t.TEXT, t.TEAL_TEXT, t.QUIET))
        box = QVBoxLayout(self);box.setContentsMargins(14, 10, 14, 12);box.setSpacing(4)
        head = QLabel('This computer, now');head.setProperty('role', 'name');box.addWidget(head)
        for group in GROUPS:
            line = QLabel();line.setTextFormat(Qt.PlainText);line.setMinimumWidth(330);box.addWidget(line);self.lines[group] = line
        self.scope = QLabel();self.scope.setTextFormat(Qt.PlainText);self.scope.setWordWrap(True);self.scope.setProperty('role', 'note');box.addWidget(self.scope)
        self.key = QLabel('A tube in amber is near its limit; a dot is its recent peak, sinking; amber along the floor while Kas itself is working.')
        self.key.setTextFormat(Qt.PlainText);self.key.setWordWrap(True);self.key.setProperty('role', 'note');box.addWidget(self.key)

    def say(self, words, hot=None, trace=None):
        hot = hot or {}
        for group in GROUPS:
            line = '%s: %s' % (NAMES[group], words.get(group, 'not reported'))
            if group in hot:line += ' — amber, ' + hot[group]
            self.lines[group].setText(line)
        self.scope.setText('The trace behind the tubes: all of it together (the average of the groups this computer reports) over the '
                           'last two minutes%s.' % ('' if trace is None else ', now %d%%' % round(100 * trace)))
