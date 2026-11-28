"""Her column, as in the owner's picture (Graphite 1.0, P1).

The owner's picture of the desktop (PLAN_1.0 section 3) and their paper (section 14, "Kasandra's interface should explain, not
compete"): the right column is her operating area, not an endless transcript. Read top to bottom it says what she is
examining, what she found, what she intends to do next and whether a decision is yours:

    the stage            the equalizer's bars across the column's whole width (the processor's threads numbered 01 to 16,
                         then the kernel, memory, disks, network and graphics), a compact band. The equalizer moved here
                         from the head's upper left, which is left empty (HALT's place, K3). 1.0 P4 no avatar: no picture of
                         her stands here or anywhere (the owner, 26 Nov: "No kas avatar anymore").
    her name             "Kasandra" with a ring for her model (○ none loaded, ● ready) and her state word, each with its
                         own shape: ○ QUIET, ● WORKING, ◆ WAITS FOR YOU, ✓ DONE, ■ STOPPED. Under it what she speaks
                         with and her hand (a link: click to change it).
    the exchange         Talk's thread (shell2.SlateFace): the last few turns; the rest fold behind "earlier".
    the progress line    while an assignment works: its steps done, each a check row (✓, verified), and "Running…" with
                         its bar, its whole percent, the step and the time left (K1's clock); while her model answers,
                         "Running…" with no number, for none is known.
    ACTIVE WORK [n]      K1's open assignments (assignments.active_work): numbered, each with its state word, its bar, its
                         whole percent, its time left and its Stop (assignment.stop, your press). A title opens its steps
                         and journal in the exchange.
    FINDINGS (live)      the Kernel's findings, read again every few seconds (investigation.list and .sheet, observers):
                         refuted first, then supported, then what each investigation would do next. A row selects its
                         card on the Field.
    NEXT STEPS           up to four numbered buttons, the first the one to take (a mark ▸ and a filled face): each is one
                         assignment press (Authorise step n, Resume, Carry on) or one desk act on one card (it is selected
                         on the Field, then the Field's own DO, DOUBT or the desk's check runs). With no model they come
                         from the records alone.
    DO DOUBT TRACE BRIEF LINE CHECK ALL
                         the Field's six commands, compact, acting on the card selected on the Field ("this"); the Field's
                         foot no longer repeats them.
    › ask Kasandra…      at the foot of her column (the right pane's foot, DELETE's mirror), with a send arrow: your words go
                         to Talk exactly as the writing line's do (shell2.Shell2.ask), so with no model she answers what the
                         records can answer.

The moments that matter (a finding refuted, an assignment done, HALT) are a card over her exchange for a few seconds, the
moment in words; it goes at a click. K3 calls moment(host, 'halt') when HALT is pressed; until then a hold of her managed
work (work_trail) is read as HALT.

1.0 P4 no avatar (the owner, 26 Nov: "No kas avatar anymore"): no picture of her is drawn, in any look. Her column's top is
the equalizer across its width, then her name, her model and her state word with its shape (state_words). The portrait's
right-click offers and its question are gone; the kernel's kasandra.portrait.admit stays registered (records only), and
nothing on screen calls it. P3's hologram (her_hologram_qt) and the left pane's (hologram_qt) are not drawn.

Her rules hold here: nothing in this column writes a record by being shown (every read is an observer); a press is yours
(Stop, Authorise, Resume, Carry on, a desk act); sending anything out still asks where it always asks. Every colour that
carries meaning also has a word or a shape. No key is named in any of its words. Every word of hers is a fixed template
(WORDS, registered with mind_words); every number arrives through a slot that names its record.
"""
from __future__ import annotations

import re
import threading
import time

from PySide6.QtCore import QEvent, QObject, QPoint, QPointF, QRect, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QFont, QFontMetrics, QImage, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMenu, QMessageBox, QPushButton,
                               QSizePolicy, QToolButton, QVBoxLayout, QWidget)

from . import boss_theme as bt
from . import mind_words
from .assistant_identity import named
from .equalizer_qt import GROUPS, Equalizer

# Her words here: fixed templates (mind_words.check: no exclamation mark, no sentence over 30 words, no digit in the fixed
# words, every number through a slot that names its record). 1.1 KV: in her voice (kas_voice): short, dry, sure only of
# what is verified; her hand's lines (hand_*) are templates here too, so the sweep reads them.
WORDS = {
    'active': 'ACTIVE WORK',
    'active_count': 'ACTIVE WORK [{count}]',
    'findings': 'FINDINGS (live)',
    'next': 'NEXT STEPS',
    'nothing_active': 'No assignment open. Ask me for one.',
    'reading_work': 'Reading my journal…',      # 1.0 F3: until her journal is read after a start, never "nothing"
    'reading_desk': 'Reading the desk…',      # 1.0 F3
    'last_done': 'Last: “{title}”, {state}.',      # 1.0 X1: with nothing open, the last one and its journal, one press away
    'its_journal': 'Its journal',
    'nothing_found': 'No findings yet.',
    'nothing_next': 'Nothing waits for you.',
    'more': 'and {count} more',
    'running': 'Running…',
    'step_of': 'step {n} of {count}',
    'left': '{time} left',
    'answering': 'model answering',
    'ask': 'ask Kasandra…',
    'send': 'Send',
    'stop': 'Stop',
    'stopped': 'Stopped “{title}”. Done steps stay done. Nothing new starts.',
    'stop_refused': 'Not stopped: {why}',
    'press_refused': 'Refused: {why}',
    'press_done': '{words}: done.',
    'carry_started': 'Back on “{title}”. The bar shows how far.',
    'carry_ended': '“{title}”: {line}',
    'select_first': 'Select a card on the Field first. The command works on that card.',
    'no_field': 'The Field is not showing here, so this command has nothing to work on.',
    'journal_head': '“{title}”, {state}. {line}',
    'journal_step': 'Step {n}, {title}: {says}.',
    'journal_says': '{says}',
    'moment_refuted': 'Finding refuted: “{title}”.',
    'moment_done': 'Done, every step verified: “{title}”.',
    'moment_halt': 'HALT. All my work is stopped. Your Apps and the desktop run on.',
    'moment_hint': 'Click to put this away.',
    'model_none': 'no model loaded',
    'model_ready': 'model ready',
    'hand_acting': '▸ My hand in {program}: {act}',
    'hand_touch': '▮▮ You took over in {program}, so I stopped',
    'hand_halt': '▮▮ Stopped by HALT, in {program}',
    'hand_dialog': '◆ A dialog in {program} is yours to answer',
    'hand_done': '✓ Done, verified · {words}',
    'hand_not_verified': '◆ Not verified. I checked · {words}',
    'hand_refused': '■ I did not act · {words}',
}
NUMBERS = {'active_count': {'count': 'the open assignments (assignment.list)'},
           'more': {'count': 'the rows not shown (assignment.list, investigation.sheet)'},
           'step_of': {'n': 'the assignment\'s steps (assignment.status)', 'count': 'the assignment\'s steps (assignment.status)'},
           'journal_step': {'n': 'the assignment\'s steps (assignment.status)'}}
mind_words.register('her_column_qt', WORDS, kind='sentence', numbers=NUMBERS)

# The state of the work: (word, shape, the palette's name for its colour). Her model's ring: ○ none, ● ready.
# 1.0 D1: the words and shapes that mean a state of the table (state_words) are the table's: ◆ NEEDS YOUR WORD, ✓ DONE,
# ▮▮ STOPPED, ‖ HELD (her work under HALT); QUIET and WORKING are her own and stay.
from . import state_words as _sw
STATES = {'idle': ('QUIET', '○', 'QUIET'), 'working': ('WORKING', '●', 'READY'),
          'awaiting_approval': (_sw.word('needs_word'), _sw.shape('needs_word'), 'OWNER'),
          'completed': ('DONE', _sw.shape('done'), 'HONEY'), 'blocked': ('STOPPED', _sw.shape('stopped'), 'RED'),
          'held': ('HELD', _sw.shape('held'), 'RED')}
# An assignment's state word (K1) -> its shape and colour name.
WORK_LOOK = {'working': ('●', 'READY'), 'ready': ('▸', 'TEXT'), 'waiting for your word': ('◆', 'OWNER'), 'held': ('■', 'RED'),
             'interrupted': ('■', 'RED'), 'stopped by you': ('■', 'QUIET'), 'blocked': ('■', 'RED'), 'needs review': ('◆', 'OWNER'),
             'no steps yet': ('○', 'QUIET'), 'done': ('✓', 'HONEY'),
             'needs your grant': ('◆', 'OWNER'),      # 1.0 K3
             'running': ('●', 'READY'), 'paused': ('■', 'QUIET'), 'needs you': ('◆', 'OWNER')}      # 1.0 F2b: a 0.8.x assignment's own words (older_work)
for _words, _look in list(WORK_LOOK.items()):      # 1.0 D1: a step's state that the table names takes the table's shape
    if _sw.of_step(_words):WORK_LOOK[_words] = (_sw.shape(_sw.of_step(_words)), _look[1])
# A finding's evidence state -> (word, shape, colour name), in the order they are shown.
FINDING_LOOK = (('REFUTED', ('REFUTED', _sw.shape('refuted'), 'RED')), ('CONTESTED', ('CONTESTED', '◆', 'OWNER')),
                ('SUPPORTED', ('SUPPORTED', _sw.shape('supported'), 'READY')), ('UNKNOWN', ('OPEN', _sw.shape('open'), 'QUIET')))      # 1.0 D1: the table's shapes
COMMANDS = (('DO', 'do', 'What can be done about the card selected on the Field: the steps, numbered; nothing runs by being offered'),
            ('DOUBT', 'doubt', 'What a plausible result on the selected card may hide, worst first; nothing is changed'),
            ('TRACE', 'trace', 'Where the selected card comes from and what rests on it, hop by hop'),
            ('BRIEF', 'brief', 'The desk written up as one page from the records; keeping it as a page waits for your go'),
            ('LINE', 'line', 'The selected card\'s line in the writing line, to read or change; nothing runs'),
            ('CHECK ALL', 'check', 'Every check the desk has, run now; what ran and what waits is said in Talk'))
TICK = 2500                 # ms between readings of the work while her column is shown
DESK_EVERY = 4              # findings and the desk's waiting cards: every this many ticks (and after a press)
MOMENT_MS = 7000            # how long the full art stands for a moment that matters
KEEP_TURNS = 4              # the exchange keeps this many bubbles in view; the rest fold behind "earlier"
_MOMENT = {}                # host id -> monotonic time the moment ends (hologram_qt asks moment_on)


def say(key, **slots):
    return WORDS[key].format(**slots)


def scale(host):
    return float((getattr(host, 'reading_profile', None) or {}).get('ui_pt', 14.0)) / 14.0


def px(host, value):
    """A size at the interface scale; a size of words (9 and up) is never set under 9 pixels."""
    return max(9 if value >= 9 else 1, round(value * scale(host)))


def colour(name):
    return getattr(bt, name, bt.TEXT)


def ink(widget, size, colour_=None, weight=None, family=None, extra=''):
    """A widget's own words: its own style sheet, so the window's larger sizes for her column do not reach it."""
    css = 'font-size:%dpx;' % max(11, size)      # 1.0 D2: nothing under 11 px (her headings and command words were 9 to 10 px in Day)
    if colour_:css += 'color:%s;' % colour_
    if weight:css += 'font-weight:%d;' % weight
    if family:css += 'font-family:"%s";' % family
    widget.setProperty('herInk', css + 'background:transparent;' + extra);widget.setStyleSheet(css + 'background:transparent;' + extra)
    return widget


def recolour(widget, colour_):
    """The same words in another colour (a state's): its own style sheet again, with the colour last."""
    base = str(widget.property('herInk') or '')
    sheet = base + 'color:%s;' % colour_
    if widget.styleSheet() != sheet:widget.setStyleSheet(sheet)


def plain(text):
    """Words shown here are hers or the records' (titles, states): never a model's words as hers (model_words.plain_only)."""
    try:
        from .model_words import plain_only
        return str(plain_only(str(text)))
    except Exception:  # noqa: BLE001 - a text that is a model's is refused: it is not shown
        return ''


class Line(QLabel):
    """One line, shortened at its end to the room it has; the whole of it in its tooltip and accessible name."""

    def __init__(self, text='', mode=Qt.ElideRight):
        super().__init__();self._full = '';self.mode = mode;self.setTextFormat(Qt.PlainText)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed);self.setText(text)

    def setText(self, text):
        self._full = str(text);self.setToolTip(self._full if len(self._full) > 24 else '');self.setAccessibleName(self._full);self._fit()

    def full(self):return self._full

    def _fit(self):
        self.ensurePolished()
        shown = QFontMetrics(self.font()).elidedText(self._full, self.mode, max(8, self.contentsRect().width()))
        if super().text() != shown:super().setText(shown)

    def sizeHint(self):
        self.ensurePolished();fm = QFontMetrics(self.font())
        return QSize(min(fm.horizontalAdvance(self._full) + 4, 600), fm.height() + 2)

    def minimumSizeHint(self):
        self.ensurePolished();return QSize(16, QFontMetrics(self.font()).height() + 2)

    def resizeEvent(self, event):super().resizeEvent(event);self._fit()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QEvent.FontChange, QEvent.StyleChange):self._fit()


class Bar(QWidget):
    """A progress bar: a track and its whole-percent share filled; the number itself is said beside it in words. With no
    number known (her model answering), a short run of the fill stands at the left and the words say why."""

    def __init__(self, host):
        super().__init__();self.host = host;self.value = 0;self.known = True
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed);self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def set(self, value, known=True):
        value = max(0, min(100, int(value or 0)))
        if (value, known) != (self.value, self.known):self.value, self.known = value, known;self.update()

    def sizeHint(self):return QSize(60, px(self.host, 8))

    def minimumSizeHint(self):return QSize(24, px(self.host, 8))

    def paintEvent(self, event):
        p = QPainter(self);p.setRenderHint(QPainter.Antialiasing)
        h = max(4, min(self.height(), px(self.host, 7)));y = (self.height() - h) / 2.0;r = h / 2.0
        track = QRectF(0.5, y, self.width() - 1.0, h)
        p.setPen(QPen(QColor(bt.LINE_MID), 1));p.setBrush(QColor(bt.RAISED));p.drawRoundedRect(track, r, r)
        share = self.value * (self.width() - 1.0) // 100 if self.known else (self.width() - 1.0) // 5
        if share > 0:
            p.setPen(Qt.NoPen);p.setBrush(QColor(bt.READY));p.drawRoundedRect(QRectF(0.5, y, max(h, share), h), r, r)
        p.end()


def _kernel(host):
    from .engineering_kernel import operator
    kernel = getattr(getattr(host, 'ledger_bridge', None), 'kernel', None)
    if kernel is None:
        from .engine import engineering
        kernel = engineering(host.root)
    return kernel, operator()


def read(host, operation, arguments=None):
    """One read through the Kernel (an observer: showing her column is not an event): the result, or None."""
    from . import floor      # 1.0 F2: what was read off the window's thread for this drawing (floor.column_tick), when it was
    hit = floor.answered(host, operation, arguments)
    if hit is not floor.MISS:return hit
    try:
        kernel, owner = _kernel(host)
        answer = kernel.dispatch(operation, arguments or {}, owner)
    except Exception:  # noqa: BLE001 - a column never takes the window down
        return None
    return answer.get('result') if isinstance(answer, dict) and answer.get('ok') else None


def press(host, operation, arguments):
    """Your press, through the Kernel: (result, '') or (None, why in words)."""
    if operation in ('assignment.step', 'assignment.plan', 'assignment.resume', 'grant.give', 'program.answer'):  # 1.0 K9: your press is not a touch against her hand
        try:
            from .a11y_hand import owner_pressed
            owner_pressed()
        except Exception:  # noqa: BLE001
            pass
    try:
        kernel, owner = _kernel(host)
        answer = kernel.dispatch(operation, arguments or {}, owner)
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)[:240]
    if isinstance(answer, dict) and answer.get('ok'):return answer.get('result'), ''
    error = (answer or {}).get('error') if isinstance(answer, dict) else answer
    message = error.get('message') if isinstance(error, dict) else str(error)
    return None, str(message or 'refused').split(': ', 1)[-1][:240]


# ---------------------------------------------------------------------------------------------------------- the stage
class ColumnEqualizer(Equalizer):
    """The head's equalizer, in her column (1.0 P1): the same readings and card, the processor's tubes numbered 01 to 16 under
    them where the numbers fit (the others: every fourth, the first and the last), the grid floor and the trace of the last
    two minutes behind them. `hole` (a gap in the middle) is 0: 1.0 P4 no avatar, the tubes span the column's whole width.
    `in_column` tells the head's placing to leave it be."""
    in_column = True

    def __init__(self, host):
        super().__init__(host);self.hole = 0;self.setObjectName('ColumnEqualizer')
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)

    def sizeHint(self):return QSize(160, 64)

    def geometry_(self):
        # 1.0 P4: Day and Night: room under the tubes for their numbers at 11 px (nothing under 11 px); 1.0 D2: in every look
        return self.height() - 16, 5.0

    def places(self):
        key = (self.width(), tuple(self.sizes), self.hole)
        if self._places is not None and self._places[0] == key:return self._places[1]
        owner = []      # the group of each tube, in order
        for g, size in enumerate(self.sizes):owner += [g] * size
        n = len(owner) or 1;w = self.width();hole = max(0, min(self.hole, w - 40))
        if hole <= 0:      # 1.0 P4 no avatar: the tubes spread across the column's whole width, a little more room between groups
            bounds = sum(1 for i in range(1, n) if owner[i] != owner[i - 1]);extra = 6;margin = 6
            pitch = max(3.0, (w - 2 * margin - bounds * extra) / float(n));wide = max(2, min(14, int(pitch * 0.62)))
            xs = [];x = margin + (pitch - wide) / 2.0
            for i in range(n):
                if i and owner[i] != owner[i - 1]:x += extra
                xs.append(int(round(x)));x += pitch
            self._places = (key, (xs, wide))
            return xs, wide
        left_n = (n + 1) // 2;right_n = n - left_n
        side = max(10, (w - hole) // 2 - 3)
        gap, between = (2, 5) if side / max(1, left_n) >= 6 else (1, 3)

        def need(first, count, wide):
            bounds = sum(1 for i in range(first + 1, first + count) if owner[i] != owner[i - 1])
            return count * wide + bounds * between + (count - 1 - bounds) * gap if count else 0
        wide = 10
        while wide > 2 and (need(0, left_n, wide) > side or need(left_n, right_n, wide) > side):wide -= 1
        xs = [];x = (w - hole) // 2 - 3 - need(0, left_n, wide)
        for i in range(n):
            if i == left_n:x = (w + hole) // 2 + 3
            elif i and owner[i] != owner[i - 1]:x += between - gap
            xs.append(x);x += wide + gap
        self._places = (key, (xs, wide))
        return xs, wide

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.shown or self.height() < 24:return
        try:
            xs, wide = self.places();base, _ = self.geometry_()
            p = QPainter(self);font = QFont(bt.MONO);font.setPixelSize(11);p.setFont(font)      # 1.0 P4: 11 px in Day and Night; 1.0 D2: in every look (it was 7 to 8 px in Graphite and Kasandra)
            fm = QFontMetrics(font);p.setPen(QColor(bt.FAINT))
            cpu = self.sizes[0] if self.sizes else 0;y = self.height() - 2;pitch = (xs[1] - xs[0]) if len(xs) > 1 else wide
            every = 1 if fm.horizontalAdvance('00') + 2 <= pitch else 4
            right = -1e9      # 1.0 P3: beside her glass the sides are narrow; a word that would touch the last one is left out
            for i in range(min(cpu, len(xs))):
                if every == 1 or i % every == 0 or i == cpu - 1:
                    words = '%02d' % (i + 1);x = xs[i] + wide / 2.0 - fm.horizontalAdvance(words) / 2.0
                    if x < right + 3 or x < 0 or x + fm.horizontalAdvance(words) > self.width():continue
                    p.drawText(QPointF(x, y), words);right = x + fm.horizontalAdvance(words)
            at = cpu
            for group, size in zip(GROUPS[1:], self.sizes[1:]):
                if size and at + size - 1 < len(xs):
                    span = xs[at + size - 1] + wide - xs[at];words = group
                    x = xs[at] + span / 2.0 - fm.horizontalAdvance(words) / 2.0
                    if fm.horizontalAdvance(words) <= span + 6 and x >= right + 3 and x >= 0 and x + fm.horizontalAdvance(words) <= self.width():
                        p.drawText(QPointF(x, y), words);right = x + fm.horizontalAdvance(words)
                at += size
            p.end()
        except Exception:  # noqa: BLE001 - the numbers are a nicety; the tubes are drawn
            pass


class Portrait(QWidget):
    """1.0 P4 no avatar: her portrait is no longer drawn (the owner, 26 Nov: "No kas avatar anymore"). The widget stays,
    hidden and empty, for what still asks it her state; it offers nothing on a right-click."""

    def __init__(self, column):
        super().__init__();self.column = column;self.host = column.host;self.state = 'idle';self._image = None;self._key = None
        self.setObjectName('HerPortrait');self.setAccessibleName(named('Stacy') + ', her portrait')
        self.setContextMenuPolicy(Qt.NoContextMenu)      # 1.0 P4 no avatar: no "Use your picture" / "Go back to the shipped art"
        self.holo = None;self.figure = None;self.arranged = None
        self.hide()

    # -- which picture
    def source(self):
        """(image, focal x, focal y, zoom, key): 1.0 P4 no avatar, always none."""
        return QImage(), 0.5, 0.5, 1.0, 'none'

    def old_source(self):      # 0.8.x/P3's choice of picture, kept unread (1.0 P4 no avatar)
        found = self.column.portrait_state or {}
        mine = (found.get('in_force') or {}).get('path')
        if mine:
            image = QImage(mine)
            if not image.isNull():return image, 0.5, 0.36, 1.0, 'yours:' + found['in_force']['sha256']
        try:      # 1.0 P3: the shipped art in every look is her hologram's figure (tall: she stands as a hologram)
            from . import kasandra_art
            path = kasandra_art.mark(kasandra_art.folder(self.host.root), 'hologram.webp')
            image = kasandra_art.cutout(path) if path is not None else QImage()
            if not image.isNull():return image, 0.5, 0.30, 1.9, 'hologram'
        except Exception:  # noqa: BLE001 - the next picture in the order (the plate, in P1's circle)
            pass
        try:
            from .boss_qt import FACE, midnight_plate
            from .locations import program
            plate = midnight_plate(program(self.host.root) / 'branding' / 'boss')
            if not plate.isNull():
                region = QRect(round(plate.width() * FACE[0]), round(plate.height() * FACE[1]), round(plate.width() * FACE[2]), round(plate.height() * FACE[3]))
                return plate.copy(region), 0.5, 0.5, 1.0, 'plate'
        except Exception:  # noqa: BLE001
            pass
        return QImage(), 0.5, 0.5, 1.0, 'none'

    def image(self):
        if self._key is None or self._image is None:      # 1.0 P3: decoded once a picture (read_portrait asks again), never a frame
            found = self.source();self._key = found[4];self._image = found
        return self._image

    def set_state(self, state):
        if state != self.state:
            self.state = state;self.update()
            if self.holo is not None:self.holo.changed()      # 1.0 P3: a brief static at a change of her state

    def paintEvent(self, event):
        return      # 1.0 P4 no avatar: nothing is drawn
        side = min(self.width(), self.height()) - 4
        if side < 12:return
        box = QRectF((self.width() - side) / 2.0, (self.height() - side) / 2.0, side, side)
        p = QPainter(self);p.setRenderHint(QPainter.Antialiasing);p.setRenderHint(QPainter.SmoothPixmapTransform)
        ring = QColor(colour(STATES.get(self.state, STATES['idle'])[2]))
        p.setPen(Qt.NoPen);p.setBrush(QColor(bt.PANEL));p.drawEllipse(box)
        image, fx, fy, zoom, _ = self.image()
        clip = QPainterPath();clip.addEllipse(box.adjusted(2, 2, -2, -2))
        p.save();p.setClipPath(clip)
        if not image.isNull():
            cover = max(side / image.width(), side / image.height()) * zoom
            w, h = image.width() * cover, image.height() * cover
            x = box.center().x() - fx * w;y = box.center().y() - fy * h
            x = min(box.left(), max(box.right() - w, x));y = min(box.top(), max(box.bottom() - h, y))
            p.drawImage(QRectF(x, y, w, h), image)
        else:
            font = QFont(bt.DISPLAY);font.setPixelSize(round(side * 0.5));p.setFont(font);p.setPen(QColor(bt.TEXT))
            p.drawText(box, Qt.AlignCenter, named('Stacy')[:1])
        p.restore()
        p.setBrush(Qt.NoBrush);p.setPen(QPen(ring, max(2.0, side / 40.0)));p.drawEllipse(box.adjusted(1, 1, -1, -1))
        p.end()

    # 1.0 P4 no avatar: the right-click offers (your picture as her portrait, the shipped art back) and their question are
    # gone; kasandra.portrait.admit stays registered in the kernel, and nothing on screen calls it.


class Stage(QWidget):
    """The top of her column: the equalizer across its whole width (1.0 P4 no avatar: no portrait in its middle)."""

    def __init__(self, column, equalizer):
        super().__init__();self.column = column;self.equalizer = equalizer;self.setObjectName('HerStage')
        equalizer.setParent(self);equalizer.show()
        self.portrait = Portrait(column);self.portrait.setParent(self);self.portrait.hide()      # 1.0 P4 no avatar
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)

    def resizeEvent(self, event):
        super().resizeEvent(event);self.arrange()

    def arrange(self):
        w, h = self.width(), self.height()      # 1.0 P4 no avatar: the bars span the column, no gap left for her
        self.equalizer.hole = 0;self.equalizer.setGeometry(0, 0, w, h);self.equalizer._places = None
        self.equalizer._floor = None;self.equalizer._scope = None;self.equalizer._sprites = None
        self.portrait.setGeometry(0, 0, 0, 0);self.portrait.hide()


class Head(QWidget):
    """The stage; her name with her model's ring and her state word; what she speaks with and her hand."""

    def __init__(self, column, equalizer):
        super().__init__();self.column = column;host = column.host;self.setObjectName('HerHead')
        box = QVBoxLayout(self);box.setContentsMargins(0, 0, 0, 0);box.setSpacing(2)
        self.stage = Stage(column, equalizer);box.addWidget(self.stage)
        row = QHBoxLayout();row.setContentsMargins(0, 0, 0, 0);row.setSpacing(6)
        self.name = QLabel(named('Stacy'));self.name.setObjectName('HerName')
        self.ring = QLabel('○');self.ring.setObjectName('HerModelRing')
        self.word = QLabel();self.word.setObjectName('HerStateWord');self.word.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        row.addWidget(self.name);row.addWidget(self.ring);row.addStretch(1);row.addWidget(self.word)
        box.addLayout(row)
        self.second = QHBoxLayout();self.second.setContentsMargins(0, 0, 0, 0);self.second.setSpacing(6);box.addLayout(self.second)
        self.restyle()

    def take(self, model, hand):
        """What she speaks with and her hand (SlateFace's own widgets, moved here: their callers keep them)."""
        for w in (model, hand):
            if w is None:continue
            w.setParent(self);self.second.addWidget(w, 1 if w is model else 0, Qt.AlignVCenter);w.show()
        self.second.addStretch(0)

    def restyle(self):
        host = self.column.host
        ink(self.name, px(host, 17), bt.VIOLET_PALE if bt.APPEARANCE == 'kasandra' else bt.TEXT, 500, bt.DISPLAY)
        ink(self.ring, px(host, 13), bt.QUIET)
        ink(self.word, px(host, 13), None, 600, bt.MONO, 'letter-spacing:1px;')

    def show_state(self, state, ready):
        word, shape, name = STATES.get(state, STATES['idle'])
        said = '%s %s' % (shape, word)
        if self.word.text() != said:
            self.word.setText(said);recolour(self.word, colour(name))
            self.word.setAccessibleName(named('Stacy is ') + word.lower())
        ring = '●' if ready else '○'
        if self.ring.text() != ring:
            self.ring.setText(ring);self.ring.setToolTip(say('model_ready') if ready else say('model_none'))
            self.ring.setAccessibleName(say('model_ready') if ready else say('model_none'))


# ---------------------------------------------------------------------------------------------------------- the sections
def heading(host, text):
    label = QLabel(text);label.setObjectName('HerHeading')
    ink(label, px(host, 12), bt.VIOLET if bt.APPEARANCE == 'kasandra' else bt.QUIET, 600, bt.MONO, 'letter-spacing:1px;')
    return label


def row_label(host, text='', quiet=False, size=13, mode=Qt.ElideRight):
    label = Line(text, mode);ink(label, px(host, size), bt.QUIET if quiet else bt.TEXT, None, bt.FACE)
    return label


class Clickable(QWidget):
    """A row that is a place to click (a press runs `act`); a rule at its left while the pointer is over it."""

    def __init__(self, act=None, tip=''):
        super().__init__();self.act = act;self.setAttribute(Qt.WA_Hover, True)
        if act is not None:self.setCursor(Qt.PointingHandCursor);self.setToolTip(tip)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.act is not None:
            self.act();return
        super().mousePressEvent(event)

    def paintEvent(self, event):
        if self.act is not None and self.underMouse():
            p = QPainter(self);p.fillRect(QRect(0, 2, 2, self.height() - 4), QColor(bt.LINE_STRONG));p.end()


def small_button(host, text, tip='', primary=False):
    b = QPushButton(text);b.setCursor(Qt.PointingHandCursor);b.setToolTip(tip);b.setFocusPolicy(Qt.TabFocus)
    pad = '%dpx %dpx' % (px(host, 1), px(host, 6))
    if primary:
        css = ('QPushButton {font-size:%dpx;font-family:"%s";font-weight:600;color:%s;background:%s;border:2px solid %s;border-radius:4px;padding:%s;text-align:left;min-height:0px;} '
               'QPushButton:hover {background:%s;} QPushButton:disabled {color:%s;border-color:%s;}' % (
                   px(host, 13), bt.FACE, bt.TEXT, bt.TEAL_SOFT, bt.READY, pad, bt.RAISED, bt.FAINT, bt.LINE))
    else:
        css = ('QPushButton {font-size:%dpx;font-family:"%s";color:%s;background:transparent;border:1px solid %s;border-radius:4px;padding:%s;text-align:left;min-height:0px;} '
               'QPushButton:hover {background:%s;border-color:%s;} QPushButton:disabled {color:%s;}' % (
                   px(host, 13), bt.FACE, bt.TEXT, bt.LINE_MID, pad, bt.RAISED, bt.LINE_STRONG, bt.FAINT))
    b.setStyleSheet(css);b.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
    return b


def hand_words(live, now_ms=None):
    """1.0 K9: her hand's line: what it does in which program, or why it stopped; '' when it rests (or the news is old)."""
    live = live or {};state = live.get('state') or 'resting'
    age = (int(now_ms if now_ms is not None else time.time_ns() // 1000000) - int(live.get('at') or 0)) // 1000
    keep = {'acting': 60, 'stopped by your touch': 900, 'stopped by HALT': 900, 'waiting for you': 900, 'done': 120, 'not verified': 600, 'refused': 120}
    if state not in keep or age > keep[state]:return ''
    program = plain(live.get('program') or 'a program')
    if state == 'acting':      # 1.1 KV: her hand's lines are her templates (WORDS hand_*)
        return say('hand_acting', program=program, act=plain(live.get('act') or live.get('words') or ''))      # how she acts: in the tooltip
    if state == 'stopped by your touch':return say('hand_touch', program=program)      # what was done and not: the row's note (1.0 F1: D1's shape)
    if state == 'stopped by HALT':return say('hand_halt', program=program)
    if state == 'waiting for you':return say('hand_dialog', program=program)
    return say({'done': 'hand_done', 'not verified': 'hand_not_verified', 'refused': 'hand_refused'}[state], words=plain(live.get('words') or ''))


def _door_view():
    """1.0 F1: the door of her hand in this process (hand_door), or nothing."""
    try:
        from .hand_door import DOOR
        return DOOR.view()
    except Exception:  # noqa: BLE001 - a column never takes the window down
        return {}


class WorkLine(QWidget):
    """The progress line under the exchange: the working assignment's verified steps as check rows, then "Running…" with its
    bar, whole percent, step and time left. While her model answers, "Running…" with no number. Hidden when she rests."""

    def __init__(self, column):
        super().__init__();self.column = column;host = column.host;self.setObjectName('HerWorkLine')
        box = QVBoxLayout(self);box.setContentsMargins(0, 0, 0, 0);box.setSpacing(1);self.box = box
        self.checks = [];self.rows = QVBoxLayout();self.rows.setSpacing(1);box.addLayout(self.rows)
        line = QHBoxLayout();line.setSpacing(6)
        self.who = ink(QLabel(named('Stacy') + ':'), px(host, 13), bt.HONEY if bt.APPEARANCE == 'kasandra' else bt.QUIET, 600, bt.FACE)
        self.words = ink(QLabel(say('running')), px(host, 13), bt.TEXT, None, bt.FACE)
        self.bar = Bar(host);self.percent = ink(QLabel(), px(host, 13), bt.READY, 600, bt.MONO)
        for w, stretch in ((self.who, 0), (self.words, 0), (self.bar, 1), (self.percent, 0)):line.addWidget(w, stretch)
        box.addLayout(line)
        self.detail = row_label(host, '', quiet=True, size=12);box.addWidget(self.detail)
        self.hand = row_label(host, '', size=12);self.hand.setObjectName('HerHandLine');self.hand.hide()  # 1.0 K9
        hand_row = QHBoxLayout();hand_row.setSpacing(px(host, 6));hand_row.addWidget(self.hand, 1)      # 1.0 F1: her hand's line and your word to it, one row
        box.addLayout(hand_row);self.resting = True
        self.door = QWidget();door = QHBoxLayout(self.door);door.setContentsMargins(0, 0, 0, 0);door.setSpacing(px(host, 4))  # 1.0 F1: your word to a paused hand
        self.door_go = small_button(host, 'Continue', 'Let my hand go on from where your window is now')
        self.door_stop = small_button(host, 'Stop', 'Stop my hand for good: your window goes back as it was (menus I opened closed, your focus, cursor and selection back)')
        self.door_go.setObjectName('HerDoorContinue');self.door_stop.setObjectName('HerDoorStop')
        for b in (self.door_go, self.door_stop):b.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)      # their words in full, beside each other
        self.door_go.clicked.connect(self.door_continue);self.door_stop.clicked.connect(self.door_put_back)
        door.addWidget(self.door_go);door.addWidget(self.door_stop);hand_row.addWidget(self.door);self.door.hide()
        self.hide()

    def show_work(self, view, most_checks=2):
        """view: assignment.status of the working one, or None; with none, her model's answer (face.job) or nothing."""
        host = self.column.host
        self.resting = False
        for w in (self.who, self.words, self.bar, self.percent, self.detail):w.show()      # 1.0 K9: the hand line alone hides them
        if view is None:
            face = self.column.face
            if getattr(face, 'job', None) and getattr(self.column, 'brain_state', None) in (None, 'READY'):      # 1.0 F3: only while her model is up
                self._checks([]);self.bar.set(0, False);self.percent.setText('');self.detail.setText(say('answering'));self.show();return
            self.resting = True
            self.detail.setText('');self.hide();return      # 1.0 F3: nothing said of a model turn that is over
        done = [s for s in view.get('steps') or () if str(s.get('journal_says', '')).startswith('done')]
        self._checks([('✓', 'Step %d · %s · %s' % (s['n'], plain(s['title']), s['journal_says'])) for s in done][-most_checks:])
        self.bar.set(view.get('progress', 0));self.percent.setText('%d%%' % int(view.get('progress', 0) or 0))
        running = next((s for s in view.get('steps') or () if s.get('status') == 'running'), None)
        parts = []
        if running is not None:parts.append(say('step_of', n=running['n'], count=len(view['steps'])) + ': ' + plain(running['title']))
        parts.append(say('left', time=view.get('time_left', '')))
        self.detail.setText(' · '.join(parts));self.show()
        _ = host

    def show_hand(self, live):
        """1.0 K9: her hand in another program, as it acts, or why it stopped (a shape and a word, never colour alone)."""
        words = hand_words(live)
        door = _door_view()      # 1.0 F1: a hand paused by your touch waits for your word: Continue, or Stop to put the window back
        paused = door.get('hand') == 'program' and door.get('state') == 'paused'
        if paused:words = '%s, in %s' % (door.get('word') or '▮▮ stopped by you', plain(door.get('program') or 'your program'))
        self.door.setVisible(paused)
        tip = plain((live or {}).get('words') or '') + ((' (%s)' % plain(live.get('how'))) if (live or {}).get('how') else '')
        self.hand.setText(words);self.hand.setToolTip(tip if words else '');self.hand.setVisible(bool(words))
        if words and self.resting:
            self._checks([])
            for w in (self.who, self.words, self.bar, self.percent, self.detail):w.hide()
            self.show()

    def door_continue(self):
        """1.0 F1: your Continue: the door lets her hand go on, and the step your touch stopped is authorised again and carried on."""
        from . import hand_door
        host = self.column.host
        done, why = press(host, 'door.continue', {})      # 1.1 T1: the door's operations are door.*, not hand.* (a desk act's head)
        words = (done or {}).get('words') or why
        if done is not None and done.get('carried'):
            more = hand_door.carry_assignment(lambda op, args: press(host, op, args), (done.get('door') or {}).get('assignment') or '')
            if more:words = more
        self.column.say_words(words);self.column.refresh(force=True)

    def door_put_back(self):
        """1.0 F1: your Stop: her hand stops for good and your program window goes back as it was."""
        done, why = press(self.column.host, 'door.stop', {})      # 1.1 T1: the door's operations are door.*, not hand.* (a desk act's head)
        self.column.say_words((done or {}).get('words') or why);self.column.refresh(force=True)

    def _checks(self, rows):
        host = self.column.host
        while len(self.checks) < len(rows):
            row = QHBoxLayout();row.setSpacing(6)
            mark = ink(QLabel('✓'), px(host, 13), bt.READY, 700, bt.MONO);words = row_label(host, '', size=12)
            row.addWidget(mark);row.addWidget(words, 1);self.rows.addLayout(row);self.checks.append((mark, words))
        for i, (mark, words) in enumerate(self.checks):
            shown = i < len(rows)
            mark.setVisible(shown);words.setVisible(shown)
            if shown:mark.setText(rows[i][0]);words.setText(rows[i][1])


class WorkRow(QWidget):
    """One open assignment: its number, shape and title (a click shows its steps and journal in the exchange), its state
    word; its bar, whole percent, time left and Stop. Two lines in a tall column; in a short one, one line (the state word
    then rests in its shape and its tooltip)."""

    def __init__(self, column):
        super().__init__();self.column = column;host = column.host;self.ident = None;self.row = None;self.compact = None
        box = QVBoxLayout(self);box.setContentsMargins(0, 0, 0, 0);box.setSpacing(1)
        self.top = QHBoxLayout();self.top.setSpacing(5);self.low = QHBoxLayout();self.low.setSpacing(6)
        box.addLayout(self.top);box.addLayout(self.low)
        self.number = ink(QLabel(), px(host, 13), bt.QUIET, 600, bt.MONO)
        self.shape = ink(QLabel(), px(host, 13), bt.READY, 700, bt.MONO)
        self.title = Clickable(self.open_journal, 'Its steps and its journal, in Talk');tl = QHBoxLayout(self.title);tl.setContentsMargins(0, 0, 0, 0)
        self.title_words = row_label(host, '', size=13);self.title_words.setAttribute(Qt.WA_TransparentForMouseEvents);tl.addWidget(self.title_words)
        self.title.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.state = ink(QLabel(), px(host, 11), bt.QUIET, 600, bt.MONO, 'letter-spacing:1px;')
        self.bar = Bar(host);self.percent = ink(QLabel(), px(host, 12), bt.TEXT, None, bt.MONO)
        self.left = ink(QLabel(), px(host, 12), bt.QUIET, None, bt.MONO)
        self.stop = small_button(host, '■ ' + say('stop'), 'Stop this assignment: nothing more of it starts; what was done stays done')
        self.stop.setStyleSheet(self.stop.styleSheet().replace('font-size:%dpx' % px(host, 13), 'font-size:%dpx' % px(host, 11), 1))
        self.stop.setObjectName('HerWorkStop');self.stop.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed);self.stop.clicked.connect(self.press_stop)
        self.note = ink(QLabel(), px(host, 12), bt.TEXT, None, bt.FACE);self.note.setObjectName('HerWorkNote')  # 1.0 K7: a step that needs review, in its words
        self.note.setWordWrap(True);self.note.setTextFormat(Qt.PlainText);self.note.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Minimum)
        self.note.setContentsMargins(px(host, 14), 0, 0, 0);self.note.hide();box.addWidget(self.note)
        self.arrange(False)

    def arrange(self, compact):
        if compact == self.compact:return
        self.compact = compact;host = self.column.host
        for lay in (self.top, self.low):
            while lay.count():lay.takeAt(0)
        if compact:      # one line: the bar narrower, the state word in the tooltip
            self.bar.setFixedWidth(px(host, 44))
            for w, stretch in ((self.number, 0), (self.shape, 0), (self.title, 1), (self.bar, 0), (self.percent, 0), (self.left, 0), (self.stop, 0)):
                self.top.addWidget(w, stretch)
            self.state.hide();self.low.setContentsMargins(0, 0, 0, 0)
        else:
            self.bar.setMinimumWidth(24);self.bar.setMaximumWidth(16777215)
            for w, stretch in ((self.number, 0), (self.shape, 0), (self.title, 1), (self.state, 0)):self.top.addWidget(w, stretch)
            self.low.setContentsMargins(px(host, 14), 0, 0, 0)
            for w, stretch in ((self.bar, 1), (self.percent, 0), (self.left, 0), (self.stop, 0)):self.low.addWidget(w, stretch)
            self.state.show()

    def show_row(self, n, row, compact=False):
        self.arrange(compact)
        self.ident = row['id'];self.row = row
        words = str(row.get('state_words') or '');shape, name = WORK_LOOK.get(words, ('○', 'QUIET'))
        self.number.setText('%d' % n);self.shape.setText(shape);recolour(self.shape, colour(name))
        self.shape.setToolTip(str(row.get('state_word') or words.upper()))
        self.title_words.setText(plain(row.get('title') or ''))
        self.state.setText(str(row.get('state_word') or words.upper()))
        self.bar.set(row.get('progress', 0));self.percent.setText('%d%%' % int(row.get('progress', 0) or 0))
        self.left.setText(str(row.get('time_left') or ''));self.left.setToolTip(say('left', time=row.get('time_left') or ''))
        older = bool(row.get('older'))      # 1.0 F2b: a 0.8.x assignment keeps no bar or time left: the steps it took, and why it waits
        self.bar.setVisible(not older);self.percent.setVisible(not older)
        if older:self.left.setToolTip(plain(row.get('line') or '') or str(row.get('time_left') or ''))
        if older and compact:self.left.setText(str(row.get('steps_short') or row.get('time_left') or ''))      # one line: room for its words
        self.stop.setVisible(bool(row.get('stop')))
        note = plain(row.get('line') or '') if words == 'needs review' else ''  # 1.0 K7: e.g. a dialog's words and buttons, read through accessibility
        if getattr(self.column, 'waits', None) is not None:note = ''      # 1.0 D1: said in "Waits for you", with its press (one place)
        short = note.replace(' needs review: ', ': ', 1) if note.startswith('Step ') else note      # the row's state word says it already
        self.note.setText(short if len(short) <= 200 else short[:199] + '…');self.note.setToolTip(note if len(short) > 200 else '');self.note.setVisible(bool(note))
        self.setAccessibleName('%s, %s, %d%%, %s' % (row.get('title'), words, int(row.get('progress', 0) or 0), say('left', time=row.get('time_left') or '')))
        if older:self.setAccessibleName('%s, %s, %s' % (row.get('title'), words, row.get('time_left') or ''))      # 1.0 F2b

    def press_stop(self):
        call = (self.row or {}).get('stop')
        if not call:return
        done, why = press(self.column.host, call['operation'], call['arguments'])
        self.column.say_words(say('stopped', title=plain(self.row.get('title'))) if done is not None else say('stop_refused', why=why))
        if isinstance(done, dict) and done.get('state_words'):      # 1.0 F3: ACTIVE WORK follows your Stop at once, from what the Stop gave back
            row = dict(self.row, state_words=done['state_words'], state_word=done.get('state_word') or str(done['state_words']).upper(),
                       stop=done.get('stop'), actions=done.get('actions') or [], line=done.get('line') or self.row.get('line'))
            for i, r in enumerate(self.column.rows):
                if r.get('id') == self.ident:self.column.rows[i] = row
            try:self.show_row(int(self.number.text() or 1), row, self.compact)
            except (ValueError, RuntimeError):
                pass
        from . import floor;floor.column_soon(self.column)      # 1.0 F2: read again off the window's thread

    def open_journal(self):
        self.column.show_journal(self.ident)


class ActiveWork(QWidget):
    def __init__(self, column):
        super().__init__();self.column = column;host = column.host;self.setObjectName('HerActiveWork')
        box = QVBoxLayout(self);box.setContentsMargins(0, 0, 0, 0);box.setSpacing(px(host, 3))
        self.head = heading(host, say('active'));box.addWidget(self.head)
        self.rows = [];self.list = QVBoxLayout();self.list.setSpacing(px(host, 4));box.addLayout(self.list)
        self.more = row_label(host, '', quiet=True, size=12);box.addWidget(self.more)
        self.none = row_label(host, say('reading_work'), quiet=True, size=12);box.addWidget(self.none)      # 1.0 F3: until the first reading
        self.last = QLabel();self.last.setObjectName('HerLastWork');self.last.setWordWrap(True);self.last.setTextFormat(Qt.RichText)      # 1.0 X1
        ink(self.last, px(host, 12), bt.QUIET, None, bt.FACE);self.last.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.last.linkActivated.connect(lambda _=None: self.column.show_journal(self.last_id) if self.last_id else None)
        self.last_id = None;box.addWidget(self.last);self.last.hide()

    def show_last(self, row):
        """1.0 X1: with nothing open, the last assignment (done, stopped) and Its journal, so what she did is one press away
        after a restart too."""
        from html import escape
        self.last_id = (row or {}).get('id') or None
        if not self.last_id:
            self.last.hide();return
        words = say('last_done', title=plain(row.get('title') or ''), state=plain(row.get('state_words') or ''))
        self.last.setText('%s <a href="journal" style="color:%s">%s</a>' % (escape(words), bt.READY, escape(say('its_journal'))))
        self.last.setToolTip(plain(row.get('line') or ''));self.last.show()

    def show_rows(self, rows, most, total, compact=False):
        self.head.setText(say('active_count', count=total) if total else say('active'))
        while len(self.rows) < min(len(rows), most):
            row = WorkRow(self.column);self.rows.append(row);self.list.addWidget(row)
        for i, row in enumerate(self.rows):
            if i < min(len(rows), most):row.show_row(i + 1, rows[i], compact);row.show()
            else:row.hide()
        hidden = max(0, total - min(len(rows), most))
        self.more.setText(say('more', count=hidden) if hidden else '');self.more.setVisible(bool(hidden))
        self.none.setText(say('nothing_active'))      # 1.0 F3: read: now it may say so
        self.none.setVisible(not rows)


class Findings(QWidget):
    """FINDINGS (live): each a row with its shape, its word and its words; a click selects it on the Field."""

    def __init__(self, column):
        super().__init__();self.column = column;host = column.host;self.setObjectName('HerFindings')
        box = QVBoxLayout(self);box.setContentsMargins(0, 0, 0, 0);box.setSpacing(px(host, 2))
        box.addWidget(heading(host, say('findings')))
        self.rows = [];self.list = QVBoxLayout();self.list.setSpacing(1);box.addLayout(self.list)
        self.more = row_label(host, '', quiet=True, size=12);box.addWidget(self.more)
        self.none = row_label(host, say('reading_desk'), quiet=True, size=12);box.addWidget(self.none)      # 1.0 F3: until the first reading
        self.read_once = False

    def _row(self):
        host = self.column.host
        holder = Clickable(None);lay = QHBoxLayout(holder);lay.setContentsMargins(0, 0, 0, 0);lay.setSpacing(5)
        holder.shape = ink(QLabel(), px(host, 13), bt.READY, 700, bt.MONO);holder.word = ink(QLabel(), px(host, 11), bt.QUIET, 600, bt.MONO, 'letter-spacing:1px;')
        holder.words = row_label(host, '', size=13)
        for w in (holder.shape, holder.word, holder.words):w.setAttribute(Qt.WA_TransparentForMouseEvents)
        lay.addWidget(holder.shape);lay.addWidget(holder.word);lay.addWidget(holder.words, 1)
        holder.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        return holder

    def show_rows(self, rows, most):
        nexts = [r for r in rows if r['state'] == 'NEXT'][:1];found = [r for r in rows if r['state'] != 'NEXT']
        hidden = max(0, len(found) - (most - len(nexts)));rows = found[:most - len(nexts)] + nexts
        while len(self.rows) < min(len(rows), most):
            row = self._row();self.rows.append(row);self.list.addWidget(row)
        for i, holder in enumerate(self.rows):
            if i < min(len(rows), most):
                found = rows[i];word, shape, name = found['look']
                holder.shape.setText(shape)
                recolour(holder.shape, colour(name))
                holder.word.setText(word);holder.words.setText(plain(found['text']))
                holder.act = (lambda ident=found.get('field'): self.column.select_card(ident)) if found.get('field') else None
                holder.setCursor(Qt.PointingHandCursor if holder.act else Qt.ArrowCursor)
                holder.setToolTip('Select it on the Field' if holder.act else '')
                holder.setAccessibleName('%s: %s' % (word, found['text']));holder.show()
            else:holder.hide()
        self.more.setText(say('more', count=hidden) if hidden else '');self.more.setVisible(bool(hidden))
        self.none.setText(say('nothing_found') if self.read_once else say('reading_desk'))      # 1.0 F3
        self.none.setVisible(not rows)


class NextButton(QPushButton):
    """A next step: its number and verb on the first line (the one to take marked ▸), what it acts on under it."""

    def __init__(self, host, n, step, primary, compact=False):
        super().__init__();self.words = step['words'];self.setCursor(Qt.PointingHandCursor);self.setToolTip(step.get('tip', ''))
        self.setFocusPolicy(Qt.TabFocus);self.setObjectName('HerNextStepPrimary' if primary else 'HerNextStep')
        self.setAccessibleName(('The step to take: ' if primary else 'Next step: ') + step['words'])
        box = QVBoxLayout(self);box.setContentsMargins(px(host, 7), px(host, 3), px(host, 5), px(host, 3));box.setSpacing(0)
        verb = step.get('verb') or step['words']
        if compact and step.get('object'):verb = '%s · %s' % (verb, step['object'])      # one line in a short column
        self.verb = Line('%d %s %s' % (n, '▸' if primary else '·', verb))
        ink(self.verb, px(host, 12 if compact else 13), bt.TEXT, 600 if primary else 500, bt.FACE)
        self.object = Line(step.get('object') or '');ink(self.object, px(host, 11), bt.QUIET, None, bt.FACE)
        for w in (self.verb, self.object):w.setAttribute(Qt.WA_TransparentForMouseEvents);box.addWidget(w)
        self.object.setVisible(bool(step.get('object')) and not compact)
        if primary:
            css = 'QPushButton {background:%s;border:2px solid %s;border-radius:4px;min-height:0px;padding:0px;} QPushButton:hover {background:%s;}' % (bt.TEAL_SOFT, bt.READY, bt.RAISED)
        else:
            css = ('QPushButton {background:transparent;border:1px solid %s;border-radius:4px;min-height:0px;padding:0px;} '
                   'QPushButton:hover {background:%s;border-color:%s;}' % (bt.LINE_MID, bt.RAISED, bt.LINE_STRONG))
        self.setStyleSheet(css);self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)

    def sizeHint(self):
        h = self.layout().sizeHint().height();return QSize(120, h)

    def minimumSizeHint(self):return QSize(40, self.layout().sizeHint().height())


class NextSteps(QWidget):
    """Up to four numbered buttons in two rows; the first is the one to take (filled, and marked ▸ in its words)."""

    def __init__(self, column):
        super().__init__();self.column = column;host = column.host;self.setObjectName('HerNextSteps')
        box = QVBoxLayout(self);box.setContentsMargins(0, 0, 0, 0);box.setSpacing(px(host, 3))
        box.addWidget(heading(host, say('next')))
        self.grid = QGridLayout();self.grid.setSpacing(px(host, 4));self.grid.setContentsMargins(0, 0, 0, 0);box.addLayout(self.grid)
        self.grid.setColumnStretch(0, 1);self.grid.setColumnStretch(1, 1)
        self.buttons = [];self.steps = [];self.key = None
        self.none = row_label(host, say('nothing_next'), quiet=True, size=12);box.addWidget(self.none)

    def show_steps(self, steps, compact=False):
        key = tuple((s['words'], s.get('primary')) for s in steps) + (compact,)
        self.steps = steps
        if key == self.key:return
        self.key = key;host = self.column.host
        for b in self.buttons:self.grid.removeWidget(b);b.hide();b.deleteLater()
        self.buttons = []
        for i, step in enumerate(steps[:4]):
            b = NextButton(host, i + 1, step, i == 0, compact)
            b.clicked.connect(lambda checked=False, s=step: self.column.take_step(s))
            self.grid.addWidget(b, i // 2, i % 2);self.buttons.append(b)
        self.none.setVisible(not steps)


class CommandRow(QWidget):
    """DO, DOUBT, TRACE, BRIEF, LINE and CHECK ALL: the Field's six commands, compact, on the card selected there."""

    def __init__(self, column):
        super().__init__();self.column = column;host = column.host;self.setObjectName('HerCommands')
        row = QHBoxLayout(self);row.setContentsMargins(0, 0, 0, 0);row.setSpacing(px(host, 3));self.buttons = {}
        for words, key, tip in COMMANDS:
            b = QPushButton(words);b.setToolTip(tip);b.setCursor(Qt.PointingHandCursor)
            b.setObjectName('HerCommand');b.setAccessibleName(words.title() + ': ' + tip);b.setFocusPolicy(Qt.TabFocus)
            b.setStyleSheet('QPushButton {font-size:%dpx;font-family:"%s";font-weight:600;color:%s;background:transparent;min-height:0px;min-width:0px;'
                            'border:1px solid %s;border-radius:3px;padding:%dpx %dpx;} QPushButton:hover {background:%s;border-color:%s;color:%s;}' % (
                                px(host, 11), bt.MONO, bt.QUIET, bt.LINE, px(host, 2), px(host, 1), bt.RAISED, bt.LINE_STRONG, bt.TEXT))      # 1.0 D2: 2 px each side (was 3); 1.1 T1: 1 px, CHECK ALL was 2 px short at 1920 x 1200
            b.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            face = QFont(bt.MONO);face.setPixelSize(px(host, 11));face.setWeight(QFont.DemiBold)      # 1.0 D2: never narrower than its word ("CHECK ALI" at 1366x768)
            b.setMinimumWidth(QFontMetrics(face).horizontalAdvance(words) + 2 * px(host, 1) + 3)      # 1.1 T1: the padding is 1 px
            b.clicked.connect(lambda checked=False, key=key: self.column.command(key))
            row.addWidget(b, len(words) + 2);self.buttons[key] = b


class AskLine(QWidget):
    """"› ask Kasandra…" and the send arrow, at the foot of her column (the right pane's foot). Your words go to Talk as the
    writing line's do."""

    def __init__(self, column):
        super().__init__();self.column = column;host = column.host;self.setObjectName('HerAskLine')
        row = QHBoxLayout(self);row.setContentsMargins(0, 0, 0, 0);row.setSpacing(px(host, 6))
        self.prompt = ink(QLabel('›'), px(host, 18), bt.READY, 700, bt.MONO)
        self.edit = QLineEdit();self.edit.setObjectName('HerAsk');self.edit.setPlaceholderText(say('ask'))
        self.edit.setAccessibleName(named('Ask Stacy'));self.edit.returnPressed.connect(self.send)
        self.edit.setStyleSheet('QLineEdit {font-size:%dpx;font-family:"%s";color:%s;background:%s;border:1px solid %s;border-radius:4px;padding:%dpx %dpx;} '
                                'QLineEdit:focus {border-color:%s;}' % (px(host, 14), bt.FACE, bt.TEXT, bt.CARD if bt.LAUNCH else bt.PANEL, bt.LINE_MID if bt.LAUNCH else bt.LINE, px(host, 4), px(host, 6),
                                                                        bt.AMBER_EDGE if bt.LAUNCH else bt.READY))      # 1.0 P4: Day and Night: a field on the surface, the accent's focus (style only)
        self.arrow = QToolButton();self.arrow.setObjectName('HerAskSend');self.arrow.setText('➤');self.arrow.setCursor(Qt.PointingHandCursor)
        self.arrow.setToolTip(say('send'));self.arrow.setAccessibleName(named('Send to Stacy'));self.arrow.clicked.connect(self.send)
        self.arrow.setStyleSheet('QToolButton {font-size:%dpx;color:%s;background:transparent;border:0;padding:0 %dpx;} QToolButton:hover {color:%s;}' % (
            px(host, 18), bt.READY, px(host, 4), bt.TEXT))
        row.addWidget(self.prompt);row.addWidget(self.edit, 1);row.addWidget(self.arrow)

    def send(self):
        text = self.edit.text().replace('​', '').strip()
        if not text:return
        self.edit.clear();self.column.ask(text)


class Moment(QWidget):
    """The full art and its static, for a moment that matters: over her exchange, a few seconds, with the moment in words.
    Still (one frame) with Reduce motion; a click puts it away."""

    def __init__(self, column):
        super().__init__(column.face);self.column = column;self.host = column.host;self.setObjectName('HerMoment')
        self.kind = '';self.words = '';self.until = 0.0;self.frame = 0;self.art = None
        self.timer = QTimer(self);self.timer.setInterval(90);self.timer.timeout.connect(self.tick)
        self.setCursor(Qt.PointingHandCursor);self.hide()

    def full_art(self):
        return QImage()      # 1.0 P4 no avatar: a moment is said in words only
        found = self.column.portrait_state or {}
        mine = (found.get('in_force') or {}).get('path')
        if mine:
            image = QImage(mine)
            if not image.isNull():return image
        if bt.APPEARANCE == 'kasandra':
            try:
                from . import kasandra_art
                path = kasandra_art.mark(kasandra_art.folder(self.host.root), 'hologram.webp')
                image = kasandra_art.cutout(path) if path is not None else QImage()
                if not image.isNull():return image
            except Exception:  # noqa: BLE001
                pass
        try:
            from .boss_qt import midnight_plate
            from .locations import program
            return midnight_plate(program(self.host.root) / 'branding' / 'boss')
        except Exception:  # noqa: BLE001
            return QImage()

    def hologram(self):
        """Kasandra's hologram in the left pane: 1.0 P4 no avatar, never there (hologram_qt.install gives None)."""
        return getattr(self.host, 'hologram', None)

    def start(self, kind, words):
        self.kind = kind;self.words = words;self.until = time.monotonic() + MOMENT_MS / 1000.0;self.frame = 0
        if self.art is None:self.art = QImage()      # 1.0 P4 no avatar: words only
        self.place();self.show();self.raise_()
        _MOMENT[id(self.host)] = self.until
        if not self.still():self.timer.start()
        QTimer.singleShot(MOMENT_MS, self.end)
        self.setAccessibleName(words)

    def still(self):
        try:
            from .document_qt import profile_of
            return bool(profile_of(self.host).get('reduce_motion'))
        except Exception:  # noqa: BLE001
            return True

    def place(self):
        face = self.column.face;head = self.column.head      # 1.0 P4 no avatar: a card of words under her head
        top = head.geometry().bottom() + 4 if head is not None else 0
        band = getattr(self.column, 'waits', None)      # 1.0 F3: never over "Waits for you": the moment stands below it
        try:
            if band is not None and band.isVisible() and band.height() > 0:
                top = max(top, band.mapTo(face, QPoint(0, band.height())).y() + 4)
        except RuntimeError:
            pass
        tall = max(120, min(face.height() - top - 8, round(face.height() * 0.46)))
        if self.art is not None and self.art.isNull():tall = px(self.host, 92)      # words only: the hologram is the art
        if top + tall > face.height():tall = max(px(self.host, 48), face.height() - top - 4)      # 1.0 F3: a short column: smaller, never over the band
        self.setGeometry(0, top, face.width(), tall)

    def end(self):
        if time.monotonic() + 0.05 < self.until:return
        self.timer.stop();self.hide();_MOMENT.pop(id(self.host), None)
        stage = self.hologram()
        if stage is not None:
            try:stage.place_now()      # the moment is over: her hologram stands aside again
            except RuntimeError:pass

    def tick(self):
        if not self.isVisible():self.timer.stop();return
        self.frame += 1;self.update()

    def mousePressEvent(self, event):
        self.until = 0.0;self.end()

    def paintEvent(self, event):
        p = QPainter(self)      # 1.0 P4 no avatar: the moment in words, no figure;p.setRenderHint(QPainter.SmoothPixmapTransform);p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setBrush(QColor(bt.TERMINAL_GROUND));p.setPen(QPen(QColor(bt.LINE_STRONG), 1));p.drawRoundedRect(r, 6, 6)
        name = {'refuted': 'RED', 'done': 'HONEY', 'halt': 'RED'}.get(self.kind, 'TEXT')
        font = QFont(bt.FACE);font.setPixelSize(px(self.host, 14));p.setFont(font);fm = QFontMetrics(font)
        words_h = min(fm.lineSpacing() * 3 + 10, r.height() - 16)
        art_box = QRectF(r.left() + 8, r.top() + 8, r.width() - 16, r.height() - words_h - 16)
        image = self.art if self.art is not None else QImage()
        if not image.isNull() and art_box.height() > 20:
            fit = min(art_box.width() / image.width(), art_box.height() / image.height())
            w, h = image.width() * fit, image.height() * fit
            target = QRectF(art_box.center().x() - w / 2, art_box.top(), w, h)
            layer = QImage(max(1, round(w)), max(1, round(h)), QImage.Format_ARGB32_Premultiplied);layer.fill(Qt.transparent)
            lp = QPainter(layer);lp.setRenderHint(QPainter.SmoothPixmapTransform);lp.drawImage(QRectF(0, 0, w, h), image)
            try:      # her static: the hologram's own noise, laid on her only, its pattern moving each frame
                from .hologram_qt import noise_tiles, scan_tile
                tiles = noise_tiles();tile = tiles[self.frame % len(tiles)]
                lp.setCompositionMode(QPainter.CompositionMode_SourceAtop);lp.setOpacity(0.55)
                brush = QBrush(tile);brush.setTransform(brush.transform().translate((self.frame * 17) % 64, (self.frame * 29) % 64))
                lp.fillRect(QRectF(0, 0, w, h), brush);lp.setOpacity(1.0)
                scan = QBrush(scan_tile());scan.setTransform(scan.transform().translate(0, self.frame % 3))
                lp.fillRect(QRectF(0, 0, w, h), scan)
            except Exception:  # noqa: BLE001 - with no static she stands still
                pass
            lp.end();p.drawImage(target, layer)
        p.setPen(QColor(colour(name)))
        text_box = QRectF(r.left() + 12, r.bottom() - words_h - 4, r.width() - 24, words_h)
        if image.isNull():text_box = QRectF(r.left() + 12, r.top() + 10, r.width() - 24, r.height() - fm.lineSpacing() - 18)
        p.drawText(text_box, Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap, self.words)
        small = QFont(bt.FACE);small.setPixelSize(px(self.host, 11));p.setFont(small);p.setPen(QColor(bt.FAINT))
        p.drawText(QRectF(r.left() + 12, r.bottom() - fm.lineSpacing() - 4, r.width() - 24, fm.lineSpacing()), Qt.AlignRight | Qt.AlignBottom, say('moment_hint'))
        p.end()


def moment_on(host):
    """Whether a moment that matters is being shown now (hologram_qt: her hologram stands in the left pane only then)."""
    return time.monotonic() < _MOMENT.get(id(host), 0.0)


def moment(host, kind, title=''):
    """Show the full art for a moment that matters: 'refuted' (a finding), 'done' (an assignment), 'halt' (K3 calls this
    when HALT is pressed). Returns the words shown, or '' when her column is not in this window."""
    column = getattr(host, 'her_column', None)
    if column is None:return ''
    title = plain(title)
    if len(title) > 64:title = title[:62].rsplit(' ', 1)[0].rstrip(' ,;:“') + '…'      # 1.0 X1: a long title cut whole, not by the moment's edge
    words = {'refuted': say('moment_refuted', title=title), 'done': say('moment_done', title=title), 'halt': say('moment_halt')}.get(kind)
    if not words:return ''
    column.moment.start(kind, words)
    stage = getattr(host, 'hologram', None)
    if stage is not None:
        try:stage.place_now()
        except RuntimeError:pass
    return words


# ---------------------------------------------------------------------------------------------------------- the column
class HerColumn(QObject):
    """Her column's parts in SlateFace, their readings and their presses."""

    def __init__(self, host):
        super().__init__(host);self.host = host;shell = host.shell2;self.face = face = shell.face
        self.portrait_state = None;self.ticks = 0;self.seen_findings = None;self.seen_work = None;self.seen_held = None
        self.rows = [];self.findings_rows = [];self.waiting = [];self.last_desk = 0.0;self.carrying = set()
        self.equalizer = self.adopt_equalizer(shell)
        self.head = Head(self, self.equalizer)
        self.work_line = WorkLine(self);self.active = ActiveWork(self);self.found = Findings(self)
        self.next = NextSteps(self);self.commands = CommandRow(self)
        self.rebuild(face)
        self.ask_line = AskLine(self);self.place_ask()
        self.moment = Moment(self)
        face.KEEP_BUBBLES = KEEP_TURNS      # the last few turns; the rest behind "earlier" (SlateFace.fold_earlier)
        face.installEventFilter(self)
        self.read_portrait()
        from . import floor      # 1.0 F2: her column's reads are made off the window's thread, then drawn
        self.timer = QTimer(self);self.timer.setInterval(TICK);self.timer.timeout.connect(lambda: floor.column_tick(self));self.timer.start()
        self.brain_state = None      # 1.0 F3: her model's state as her column last read it (brain.status, with her work)
        QTimer.singleShot(0, lambda: floor.column_soon(self, first=True))      # 1.0 F3: at once, never behind the floor's queue
        stage = getattr(host, 'hologram', None)      # her hologram, placed before this column was, stands aside until a moment
        if stage is not None:QTimer.singleShot(0, stage.place_now)

    # -- building -----------------------------------------------------------------------------------------------------------
    def adopt_equalizer(self, shell):
        """The head's equalizer moves here: a ColumnEqualizer takes its place (top.equalizer, for its callers), with its
        stillness and its busy floor; the old one stops and goes. The head's upper left is left empty."""
        top = getattr(shell, 'top', None);old = getattr(top, 'equalizer', None)
        new = ColumnEqualizer(self.host)
        if old is not None:
            new.still = old.still;new.busy = old.busy
            try:old.clock.stop();old.glide.stop();old.hide();old.setParent(None);old.deleteLater()
            except RuntimeError:pass
        if top is not None:top.equalizer = new
        return new

    def rebuild(self, face):
        """SlateFace's column, in the picture's order. Its masthead or portrait row and its This and Now lines are kept,
        out of sight, for what still calls them (her state is read from them; the Agenda line counts what waits)."""
        outer = face.layout()
        keep = {face.scroll, face.input, getattr(face, 'input_hint', None), getattr(face, 'related', None)}
        self.parked = QWidget(face);self.parked.setObjectName('HerColumnParked');self.parked.hide()
        model, hand = face.model, face.hand

        def park(item):
            w = item.widget()
            if w is not None:
                if w in (model, hand):return
                if w in keep:return w
                w.setParent(self.parked);return None
            lay = item.layout()
            if lay is not None:
                while lay.count():park(lay.takeAt(0))
            return None
        kept = []
        while outer.count():
            item = outer.takeAt(0)
            if item.widget() is not None and item.widget() in keep:kept.append(item.widget());continue
            park(item)
        self.head.take(model, hand)
        related = getattr(face, 'related', None)
        outer.addWidget(self.head)
        try:      # 1.0 D1: "Waits for you", under her hologram, only when something waits (waits_qt)
            from .waits_qt import install as install_waits
            self.waits = install_waits(self, outer)
        except Exception:  # noqa: BLE001 - the column is whole without it
            self.waits = None
        outer.addWidget(face.scroll, 1)
        outer.addWidget(self.work_line)
        try:      # 1.0 K8: her network use, one line (her fetch, a step that needs the network, her last fetch)
            from .network_qt import install_column
            outer.addWidget(install_column(self))
        except Exception:  # noqa: BLE001 - the column is whole without it
            self.net_line = None
        outer.addWidget(self.active)
        try:      # 1.0 K3: the grants in force, and a grant asked for in plain words with its one press
            from .grants_qt import GrantFold
            self.grant_fold = GrantFold(self);outer.addWidget(self.grant_fold)
        except Exception:  # noqa: BLE001 - the column is whole without it
            self.grant_fold = None
        outer.addWidget(self.found)
        if related is not None:outer.addWidget(related)
        outer.addWidget(self.next)
        outer.addWidget(self.commands)
        # 1.0 P2: the room the exchange does not need, below the sections (they follow the exchange in order; fit_exchange)
        from PySide6.QtWidgets import QSpacerItem
        self.room = QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding);outer.addItem(self.room)
        face.exchange_room = self.exchange_room      # SlateFace.fold_earlier keeps the turns that fit this room
        face.thread.installEventFilter(self)
        for w in (face.input, getattr(face, 'input_hint', None)):
            if w is not None:outer.addWidget(w)
        outer.setSpacing(px(self.host, 8))
        m = outer.contentsMargins();outer.setContentsMargins(m.left(), px(self.host, 6), m.right(), m.bottom())

    def place_ask(self):
        """The ask line in the right pane's foot (the mirror of DELETE's place), as wide as the pane's content."""
        pane = getattr(self.host, 'right_pane', None);foot = getattr(pane, 'foot', None)
        if foot is None:
            self.face.layout().addWidget(self.ask_line);return
        self.ask_line.setParent(foot);self.ask_line.show();foot.installEventFilter(self);self.fit_ask()

    def fit_ask(self):
        foot = self.ask_line.parentWidget();pane = getattr(self.host, 'right_pane', None)
        if foot is None or pane is None or foot is self.face:return
        inset = getattr(pane, 'inset', 16);tall = min(foot.height() - 4, max(28, self.ask_line.sizeHint().height()))
        y = max(0, getattr(foot, 'slot', QRect()).y() if not getattr(foot, 'slot', QRect()).isNull() else (foot.height() - tall) // 2)
        y = min(y, max(0, foot.height() - tall - 2))
        self.ask_line.setGeometry(inset, y, max(60, foot.width() - 2 * inset), tall)

    def eventFilter(self, watched, event):
        if watched is getattr(self.face, 'thread', None):      # 1.0 P2: a turn added, folded or shown
            if event.type() in (QEvent.LayoutRequest, QEvent.Resize, QEvent.ChildRemoved):self.fit_soon()
            return False
        if event.type() == QEvent.Resize:
            if watched is self.face:
                self.size_parts()
                if self.moment.isVisible():self.moment.place()
                self.fit_soon()      # 1.0 P2
            elif getattr(self, 'ask_line', None) is not None and watched is self.ask_line.parentWidget():QTimer.singleShot(0, self.fit_ask)
        return False

    # -- 1.0 P2: the exchange takes the room its turns need ---------------------------------------------------------------
    def exchange_room(self):
        """The height the exchange and the free room below the sections have together: what the turns may take."""
        room = getattr(self, 'room', None)
        if room is None:return self.face.scroll.viewport().height()
        return self.face.scroll.geometry().height() + room.geometry().height()

    def fit_soon(self):
        if getattr(self, '_fit_pending', False):return
        self._fit_pending = True
        QTimer.singleShot(0, self.fit_exchange)

    def fit_exchange(self):
        """No empty gap above ACTIVE WORK: the exchange is as tall as its turns (the welcome card alone, at first) and the
        sections follow it in order, the room left over at the column's foot. When the turns need more than the room, the
        exchange takes all of it and the earlier turns fold behind "earlier" (SlateFace.fold_earlier) as before."""
        self._fit_pending = False
        face = self.face;scroll = face.scroll;outer = face.layout();room = getattr(self, 'room', None)
        if room is None or getattr(self.host, '_closing', False):return
        try:
            lines = face.lines;width = max(120, scroll.viewport().width())
            need = lines.totalHeightForWidth(width) if lines.hasHeightForWidth() else face.thread.sizeHint().height()
            need += 2 * scroll.frameWidth() + 2
            fits = need <= self.exchange_room()
            cap = need if fits else 16777215
            if scroll.maximumHeight() != cap:
                scroll.setMaximumHeight(cap);QTimer.singleShot(150, self.fit_soon)      # once more, when the turns have wrapped at the new size
            for i in range(outer.count()):
                item = outer.itemAt(i)
                if item.widget() is scroll and outer.stretch(i) != (0 if fits else 1):outer.setStretch(i, 0 if fits else 1)
                elif item.spacerItem() is room and outer.stretch(i) != (1 if fits else 0):outer.setStretch(i, 1 if fits else 0)
        except RuntimeError:      # the window is closing
            pass

    def compact(self):
        return self.face.height() < 700

    def squeezed(self):
        """1.0 D1: a short column (compact), or one where something waits and her hologram leaves too little room for every
        section whole: the exchange gives way first, then findings fold to their first two and NEXT STEPS to two; what waits
        for you never folds. Decided from what waits and the column's size, never from what is shown, so it does not flicker."""
        if self.compact():return True
        waits = getattr(self, 'waits', None)
        return waits is not None and bool(getattr(waits, 'shown', ())) and self.face.height() - self.head.height() < px(self.host, 800)

    def size_parts(self):
        # 1.0 P4 no avatar: the equalizer is a compact band (about 72 to 96 px at 1920x1200, less at 1366x768), the column's
        # height kept for the work below
        h = self.face.height()
        # 1.0 D2 (the coordinator: "very short"): a calm band whose tubes read, its numbers at 11 px under them, her name and
        # state word clear below it; about 108 px tall on a tall column, 64 px at 1366x768
        tall = max(64, px(self.host, 64)) if self.compact() else max(88, min(px(self.host, 112), round(h * 0.11)))      # 1.0 D2: 64 at 1366x768 (it was 48), so the exchange keeps its room
        if self.head.stage.height() != tall:self.head.stage.setFixedHeight(tall)
        air = px(self.host, 6)
        if self.head.layout().spacing() != air:self.head.layout().setSpacing(air)      # 1.0 D2: her name and state word stand clear under it
        spacing = px(self.host, 5 if self.compact() else 9)
        if self.face.layout().spacing() != spacing:self.face.layout().setSpacing(spacing)

    # -- reading ------------------------------------------------------------------------------------------------------------
    def read_portrait(self):
        self.portrait_state = {}      # 1.0 P4 no avatar: no picture of her is read or drawn
        self.head.stage.portrait._key = None;self.moment.art = None
        try:self.size_parts();self.head.stage.arrange()
        except Exception:  # noqa: BLE001 - laid out again at the next tick
            pass

    def kernel(self):
        return _kernel(self.host)

    def refresh(self, force=False, parts=None):
        """Read the work (every tick), and the findings and the desk's waiting cards (every DESK_EVERY ticks, or forced).
        1.0 F3: parts, what a gathering brought (her work alone after a press or at a start, then the desk)."""
        if getattr(self.host, '_closing', False):return
        if not force and not self.face.isVisible():return
        chosen = parts is not None;parts = parts or ('work', 'desk')      # 1.0 F3: parts as a gathering brought them (exactly), else as before
        if 'work' in parts:self.ticks += 1
        self.size_parts();self.fit_soon()      # 1.0 P2: the sections follow the exchange
        try:
            if 'work' in parts:self.read_work()      # 1.0 F3
        except Exception:  # noqa: BLE001 - a column never takes the window down
            pass
        try:      # 1.0 D1: what waits for you, read with the work
            if getattr(self, 'waits', None) is not None:
                self.waits.refresh()
                short = self.squeezed() and bool(self.waits.shown)      # the exchange gives way first; what waits never folds
                scroll = self.face.scroll;want = (1 if self.compact() and len(self.waits.shown) > 1 else px(self.host, 24)) if short else 0      # 1366x768 with several waiting: all of it
                if scroll.minimumHeight() != want:scroll.setMinimumHeight(want)
        except Exception:  # noqa: BLE001
            pass
        if ('desk' in parts or 'findings' in parts or 'cards' in parts) and (force or chosen or self.ticks % DESK_EVERY == 1):      # 1.0 F3: parts
            try:
                self.read_desk(findings='cards' not in parts or 'desk' in parts, cards='findings' not in parts or 'desk' in parts)
                if 'cards' not in parts or 'desk' in parts:self.found.read_once = True
            except Exception:  # noqa: BLE001
                pass
        try:self.show_state();self.found.show_rows(self.findings_rows, 2 if self.squeezed() else 4)      # 1.0 D1: squeezed (compact, as before, or something waits)
        except Exception:  # noqa: BLE001
            pass
        waits = getattr(self, 'waits', None);busy = waits is not None and bool(getattr(waits, 'shown', ())) and self.squeezed()      # 1.0 D1
        try:self.next.show_steps(self.next_steps()[:2] if busy else self.next_steps(), self.face.height() < 520 or busy)      # one line each only in a very short column (1.0 D1: or a short one where something waits)
        except Exception:  # noqa: BLE001
            pass

    def read_work(self):
        from . import assignments
        kernel, owner = self.kernel()
        self.follow_brain()      # 1.0 F3: her model's state first: the progress line below says "answering" only while it is up
        listing = read(self.host, 'assignment.list', {'open': True, 'limit': 5}) or {}
        rows = list(listing.get('assignments') or ())
        order = {'working': 0, 'waiting for your word': 1, 'needs review': 1, 'blocked': 1, 'interrupted': 1, 'held': 2, 'ready': 2,
                 'needs your grant': 1}      # 1.0 K3
        rows.sort(key=lambda r: order.get(r.get('state_words'), 3))
        self.rows = rows;compact = self.compact()
        waits = getattr(self, 'waits', None);busy = waits is not None and len(getattr(waits, 'shown', ())) > 1 and self.squeezed()      # 1.0 D1
        from . import older_work      # 1.0 F2b: a 0.8.x assignment left running, with its own words and its own Stop (the old path)
        older = older_work.rows(lambda op, args=None: read(self.host, op, args))
        self.active.show_rows(rows + older, 1 if busy else (2 if compact else 3), int(listing.get('total') or len(rows)) + len(older), compact)      # 1.0 D1: a column where things wait shows them there
        working = next((r for r in rows if r.get('state_words') == 'working'), None)
        view = read(self.host, 'assignment.status', {'id': working['id']}) if working else None
        self.work_line.show_work(view, 1 if compact else 2)
        self.work_line.show_hand((read(self.host, 'program.status', {'live': True}) or {}).get('live'))      # 1.0 K9: her hand in your programs
        # moments: an assignment that was open and is done now; her managed work held (HALT, until K3 says it itself)
        ids = {r['id']: r.get('title') for r in rows}
        try:      # 1.0 X1: nothing open: the last assignment, read once at start and again when one closes (not every tick)
            if not rows and not older and (getattr(self, '_x1_last', None) is None or any(i not in ids for i in (self.seen_work or {}))):
                self._x1_last = (list((read(self.host, 'assignment.list', {'limit': 1}) or {}).get('assignments') or ()) or [{}])[0]
            self.active.show_last(getattr(self, '_x1_last', None) if not rows and not older else None)
        except Exception:  # noqa: BLE001
            pass
        later = {}
        if self.seen_work is not None:
            from . import floor as _floor
            for ident, title in self.seen_work.items():
                if ident not in ids:
                    gone = _floor.answered(self.host, 'assignment.status', {'id': ident})      # 1.0 F3: as gathered, never read here
                    if gone is _floor.MISS and getattr(self.host, '_f2_answers', None):later[ident] = title;continue      # the next gathering reads it
                    gone = (gone if gone is not _floor.MISS else read(self.host, 'assignment.status', {'id': ident})) or {}
                    if gone.get('state') == 'done':moment(self.host, 'done', title)
        self.seen_work = dict(ids, **later)
        try:
            from . import halt_gate      # 1.0 K3: HALT's own hold (Stop all's hold of Graphite's jobs is not HALT)
            from . import floor      # 1.0 F2: as gathered off the window's thread, else read now
            held = bool(floor.halt_status(self.host, kernel).get('held'))
            _ = halt_gate
        except Exception:  # noqa: BLE001 - a gate that cannot be read is not said to be HALT
            held = bool(self.seen_held)
        try:
            if getattr(self, 'grant_fold', None) is not None:self.grant_fold.show_from(rows)      # 1.0 K3: grants, and a grant asked for
        except Exception:  # noqa: BLE001
            pass
        if self.seen_held is not None and held and not self.seen_held:moment(self.host, 'halt')
        self.seen_held = held
        _ = (assignments, kernel, owner)

    def follow_brain(self):
        """1.0 F3: her model line, her model's ring and "her model is answering" follow the brain's state as gathered with her
        work (never read here on the window's thread): "no model yet" only when no model is ready, never while one is."""
        from . import floor
        brain = floor.answered(self.host, 'brain.status')
        if brain is floor.MISS or not isinstance(brain, dict):return
        state = str(brain.get('state') or '');self.brain_state = state
        self.host._status_brain = {'READY': 'ready', 'MODEL_STOPPED': 'stopped', 'NO_MODEL_SELECTED': 'none yet'}.get(state, 'unknown')
        model = getattr(self.face, 'model', None)
        if model is None:return
        shown = model.text()
        if state == 'READY' and (not shown or 'no model yet' in shown):
            name = None
            models = floor.answered(self.host, 'brain.models')
            chosen = (brain.get('selection') or {}).get('model_id')
            for m in (models.get('models') or ()) if isinstance(models, dict) else ():
                if m.get('id') == chosen:
                    weights = next((f.get('name') for f in m.get('files') or () if f.get('role') == 'weights'), None)
                    if weights:name = re.sub(r'(?i)[-_.]?(q\d.*|f16|bf16)?\.gguf$', '', weights).replace('-', ' ')      # as shell2.model_name says it
            model.setText(name or 'a model')      # the face's own refresh adds the rest at its tick
        elif state != 'READY' and shown and 'no model yet' not in shown:
            model.setText('no model yet');model.setToolTip('no model yet')

    def read_desk(self, findings=True, cards=True):
        """FINDINGS (live): every open investigation's findings, refuted first; what each would do next. And the desk's
        waiting cards for NEXT STEPS (field.read, an observer). 1.0 F3: findings and cards, each as its own gathering brought
        it (at a start the findings are said before the whole desk is read)."""
        if not findings:
            rows = list(self.findings_rows or ())
            self._f3_cards(cards, rows);return
        rows = [];states = {}
        listing = read(self.host, 'investigation.list') or {}
        for inv in list(listing.get('investigations') or ())[:4]:
            sheet = read(self.host, 'investigation.sheet', {'id': inv['id']}) or {}
            for claim in list(sheet.get('learned') or ()) + list(sheet.get('unresolved') or ()):
                if claim.get('role') != 'FINDING' or claim.get('retired'):continue
                state = str(claim.get('evidence_state') or 'UNKNOWN').upper()
                look = dict(FINDING_LOOK).get(state, ('OPEN', '?', 'QUIET'))
                rows.append({'text': claim.get('text', ''), 'state': state, 'look': look, 'field': 'claim:' + claim['id'], 'id': claim['id']})
                states[claim['id']] = (state, claim.get('text', ''))
            reason = str(sheet.get('reason') or inv.get('reason') or '').strip()
            if reason and str(sheet.get('state') or inv.get('state')) not in ('DONE', 'CLOSED', 'ANSWERED'):
                rows.append({'text': reason, 'state': 'NEXT', 'look': ('NEXT', '→', 'TEXT'), 'field': None})
        order = [name for name, _ in FINDING_LOOK] + ['NEXT']
        rows.sort(key=lambda r: order.index(r['state']) if r['state'] in order else len(order))
        self.findings_rows = rows
        if self.seen_findings is not None:
            for ident, (state, text) in states.items():
                if state == 'REFUTED' and self.seen_findings.get(ident, ('', ''))[0] != 'REFUTED':moment(self.host, 'refuted', text)
        self.seen_findings = states
        self._f3_cards(cards, rows)

    def _f3_cards(self, cards, rows):
        """The desk's waiting cards (field.read) when this gathering brought them, else as last read (1.0 F3); the RECHECK
        marks on the findings from them."""
        if cards:
            desk = read(self.host, 'field.read') or {}
            self.waiting = list(desk.get('waiting') or ());self._f3_stale_from = desk
            self.last_desk = time.monotonic()
        desk = getattr(self, '_f3_stale_from', None) or {}
        # 1.0 X1: a finding the desk marks RECHECK (what it rests on changed since) says so here as the board does, never SUPPORTED
        stale = {str(r.get('id')) for r in desk.get('objects') or () if r.get('kind') == 'finding' and str(r.get('state')) == 'recheck'}
        for row in rows:
            if row.get('field') in stale and row['state'] != 'REFUTED':row['state'] = 'RECHECK';row['look'] = ('RECHECK', '◧', 'RECHECK')
        if stale:
            rank = ['REFUTED', 'RECHECK'] + [name for name, _ in FINDING_LOOK if name != 'REFUTED'] + ['NEXT']
            rows.sort(key=lambda r: rank.index(r['state']) if r['state'] in rank else len(rank))
        self.findings_rows = rows
        if cards:self.look_for_old_values()      # 1.0 X1

    def look_for_old_values(self):
        """1.0 X1 (day_notice): when the calculations marked RECHECK change, look off the window's thread for written words
        that still carry an old result; say each once, and offer Update in NEXT STEPS."""
        sig = tuple(sorted((str(w.get('id')), str(w.get('state'))) for w in self.waiting if w.get('kind') == 'calculation' and w.get('state') == 'recheck'))
        if sig == getattr(self, '_x1_sig', ()):return
        self._x1_sig = sig
        if not sig:
            self.noticed = [];return
        from . import day_notice, floor
        from .engineering_kernel import operator

        def plan(reading):
            try:reading.extra['x1_notices'] = day_notice.notices(day_notice.reader(reading.kernel, operator()))
            except Exception as exc:  # noqa: BLE001 - nothing is noticed rather than something wrong
                reading.extra['x1_notices'] = [];reading.extra['x1_why'] = repr(exc)[:300]

        def landed(extra):
            if getattr(self.host, '_closing', False) or self._x1_sig != sig:return
            self._x1_why = (extra or {}).get('x1_why', '') if extra is not None else 'not gathered'
            self.noticed = list((extra or {}).get('x1_notices') or ())
            said = getattr(self, '_x1_said', set());self._x1_said = said
            for notice in self.noticed:
                if notice['key'] not in said:said.add(notice['key']);self.say_words(day_notice.words(notice))
            try:self.next.show_steps(self.next_steps(), self.face.height() < 520)
            except Exception:  # noqa: BLE001
                pass
        if not floor.gather(self.host, plan, landed, key=('x1-notice', id(self))):
            self.noticed = []

    def state(self):
        """An Approve that waits for you, a fresh stop, her work (her model answering, a job, an assignment running), a
        fresh outcome, the Agenda's count of what waits for you, else quiet (kasandra_art's order, with K1's assignments)."""
        from .kasandra_art import column_state, current_state
        if self.seen_held:return 'held'      # 1.0 K3: while HALT holds her work; 1.0 D1: the table's word for it, ‖ HELD
        try:
            state = current_state(self.host)
            if state in ('idle', 'viewing', 'completed') and any(r.get('state_words') == 'working' for r in self.rows):state = 'working'
            elif state in ('idle', 'viewing') and any(r.get('state_words') in ('waiting for your word', 'needs your grant', 'needs review')
                                                       for r in self.rows):state = 'awaiting_approval'      # 1.0 K10: her work waits for you: said, never QUIET
            if state in ('idle', 'viewing'):state = column_state(self.host)
        except Exception:  # noqa: BLE001
            state = 'idle'
        return 'idle' if state == 'viewing' else state

    def show_state(self):
        state = self.state();ready = (self.brain_state == 'READY') if getattr(self, 'brain_state', None) else getattr(self.host, '_status_brain', '') == 'ready'      # 1.0 F3
        self.head.show_state(state, ready);self.head.stage.portrait.set_state(state)
        if state != getattr(self, 'shown_state', None):      # 1.0 D1: the dock says it too when it needs you (state_words)
            self.shown_state = state
            dock = getattr(self.host, 'system_dock', None)
            try:
                if dock is not None:dock.arrange()
            except Exception:  # noqa: BLE001 - the dock is whole without it
                pass

    # -- NEXT STEPS ---------------------------------------------------------------------------------------------------------
    def next_steps(self):
        """Up to four, the first the one to take: what an assignment waits for from you; then the desk's cards that wait,
        each with the Field's command that answers it; then a refuted finding to doubt; then carrying on; then the desk's
        check. Each is one press: an assignment's call, or a desk act on one card (it is selected, then the command runs)."""
        out = [];seen = set();later = []
        for row in self.rows:
            for action in row.get('actions') or ():
                if action.get('words') == 'Stop':continue
                if action.get('words') == 'Carry on':continue
                from .waits_qt import carried      # 1.0 D1: an Authorise or a grant is in "Waits for you" (said in one place)
                if carried(self, action):continue
                if action.get('words') == 'Resume' and row.get('state_words') == 'stopped by you':
                    later.append(row);continue      # you stopped it: Resume is offered, after what waits for you
                title = plain(row.get('title') or '')
                out.append({'words': '%s · %s' % (action['words'], title), 'verb': action['words'], 'object': title, 'kind': 'assignment',
                            'call': action, 'title': title, 'tip': '%s of “%s”: your press. %s' % (action['words'], title, row.get('line') or '')})
        try:      # 1.0 X1: written words that still carry an old result (day_notice): Update asks for the plan
            from . import day_notice
            planned = [plain(r.get('title') or '').lower() for r in self.rows]      # a plan already open for it: not offered twice
            out.extend(day_notice.step(n) for n in (getattr(self, 'noticed', None) or ())[:1]
                       if not any(t == n['objective'].lower() or ('recheck' in t and n['quantity'].lower() in t) for t in planned))
        except Exception:  # noqa: BLE001
            pass
        for card in self.waiting:
            ident = card.get('id');kind = str(card.get('kind') or '');state = str(card.get('state') or '')
            if not ident or ident in seen:continue
            seen.add(ident);title = plain(card.get('title') or '')
            command = 'doubt' if state in ('refuted', 'contested') else 'do'
            verb = 'Doubt' if command == 'doubt' else 'See its steps'
            out.append({'words': '%s: %s' % (verb, title), 'verb': verb, 'object': title, 'kind': 'desk', 'card': ident, 'command': command, 'title': title,
                        'tip': '“%s” %s. Selects it on the Field and asks the records %s.' % (
                            title, state or 'waits', 'what it may hide' if command == 'doubt' else 'what can be done; nothing runs by being offered')})
        for found in self.findings_rows:
            if found['state'] == 'REFUTED' and found.get('field') and found['field'] not in seen:
                seen.add(found['field'])
                out.append({'words': 'Doubt: %s' % plain(found['text']), 'verb': 'Doubt', 'object': plain(found['text']), 'kind': 'desk',
                            'card': found['field'], 'command': 'doubt',
                            'title': found['text'], 'tip': 'A refuted finding: selects it on the Field and asks the records what it may hide.'})
        for row in self.rows:
            for action in row.get('actions') or ():
                if action.get('words') == 'Carry on':
                    title = plain(row.get('title') or '')
                    out.append({'words': 'Carry on · %s' % title, 'verb': 'Carry on', 'object': title, 'kind': 'assignment', 'call': action, 'title': title,
                                'tip': 'Carry on with “%s” until a step needs you; every step is verified before it counts as done.' % title})
        for row in later:
            action = next(a for a in row.get('actions') or () if a.get('words') == 'Resume');title = plain(row.get('title') or '')
            out.append({'words': 'Resume · %s' % title, 'verb': 'Resume', 'object': title, 'kind': 'assignment', 'call': action, 'title': title,
                        'tip': 'You stopped “%s”. Resume inspects every step first and never repeats one that is done.' % title})
        out.append({'words': 'Check the desk', 'verb': 'Check the desk', 'object': 'every check, run now', 'kind': 'desk', 'command': 'check', 'title': '',
                    'tip': 'Every check the desk has, run now; what waits is said in Talk with the step that would settle it.'})
        mine = [id(s) for s in out if s['kind'] == 'assignment'][:4]      # 1.0 X1: an assignment's own press (Carry on, Resume)
        if any(i not in {id(s) for s in out[:4]} for i in mine):          # is never pushed off the four by the desk's cards: after
            room = 4 - len(mine)                                           # Authorise, Carry on is the only way to run the step
            desk = [id(s) for s in out if s['kind'] != 'assignment'][:room]
            out = [s for s in out if id(s) in mine or id(s) in desk]
        out = out[:4]
        if out:out[0]['primary'] = True
        return out

    def take_step(self, step):
        if step['kind'] == 'notice':      # 1.0 X1: Update: the plan asked for in the desk's words; offered, nothing changed
            self.ask(step['objective']);return
        if step['kind'] == 'assignment':
            call = step['call']
            if call.get('operation') in ('assignment.step', 'assignment.resume'):
                self.carry(call, step.get('title', ''));return
            done, why = press(self.host, call['operation'], call['arguments'])
            self.say_words(say('press_done', words=call['words']) if done is not None else say('press_refused', why=why))
            if done is not None and call.get('then'):      # 1.0 K3: one press: the grant, then carry on
                self.carry(call['then'], step.get('title', ''));return
            from . import floor;floor.column_soon(self);return      # 1.0 F2: read again off the window's thread
        card = step.get('card')
        if card and not self.select_card(card):return
        self.command(step.get('command') or 'do')

    def carry(self, call, title):
        """Resume or Carry on: run in a worker of its own (a fresh Kernel on the same workspace), so the window stays live;
        ACTIVE WORK and the progress line follow it. One at a time per assignment (K1's lock holds the rest)."""
        ident = call['arguments'].get('id')
        if ident in self.carrying:return
        self.carrying.add(ident)
        from .engineering_kernel import Kernel, operator
        kernel, _ = self.kernel();root = kernel.root;result = {}

        def work():
            try:
                answer = Kernel(root).dispatch(call['operation'], call['arguments'], operator())
                result['answer'] = answer
            except Exception as exc:  # noqa: BLE001
                result['answer'] = {'ok': False, 'error': {'message': str(exc)}}
        thread = threading.Thread(target=work, name='her-column-carry', daemon=True);thread.start()
        self.say_words(say('carry_started', title=title))

        def check():
            if thread.is_alive():QTimer.singleShot(400, check);return
            self.carrying.discard(ident)
            answer = result.get('answer') or {}
            view = answer.get('result') if answer.get('ok') else None
            line = (view or {}).get('line') if isinstance(view, dict) else None
            self.say_words(say('carry_ended', title=title, line=plain(line)) if line else say('press_refused', why=str((answer.get('error') or {}).get('message', ''))[:200]))
            from . import floor;floor.column_soon(self)      # 1.0 F2: read again off the window's thread
        from . import floor;QTimer.singleShot(400, check);floor.column_soon(self)      # 1.0 F2

    # -- the desk -----------------------------------------------------------------------------------------------------------
    def field(self):
        """The Field's page, brought to the front (a desk act, go.field, recorded as yours), or None."""
        if getattr(self.host, '_field_active', False) and getattr(self.host, 'field_page', None) is not None:return self.host.field_page
        try:
            from .desk_doers import run
            run(self.host, 'go.field', {'face': 'work'}, door='owner')
        except Exception:  # noqa: BLE001
            pass
        if not getattr(self.host, '_field_active', False):
            try:
                from .field_page import show_field
                show_field(self.host)
            except Exception:  # noqa: BLE001
                return None
        return getattr(self.host, 'field_page', None)

    def select_card(self, ident):
        """A card selected on the Field by its id (the desk act point.sheet, recorded as yours). True when it is."""
        page = self.field()
        if page is None:self.say_words(say('no_field'));return False
        try:
            from .desk_doers import run
            done = run(self.host, 'point.sheet', {'id': ident, 'by': 'direct'}, door='owner')
            if done.get('ok'):return True
            self.say_words(plain(done.get('words') or say('no_field')));return False
        except Exception as exc:  # noqa: BLE001
            self.say_words(say('press_refused', why=str(exc)[:200]));return False

    def command(self, key):
        """One of the six on the card selected on the Field: the Field's own D, X, T, B, S and C."""
        from . import field_page
        page = self.field()
        if page is None:self.say_words(say('no_field'));return None
        obj = page.view.selected()
        board_focus = self.board_focus(page)      # 1.0 F3: the card focused on the board is the one TRACE (and the rest) act on
        if board_focus is not None:obj = board_focus
        if key == 'brief':return field_page.brief(self.host)
        if key == 'check':      # 1.0 F3: CHECK ALL's reads rehearsed on a worker, then performed here from what was read
            from . import off_window
            from .field_do import sweep
            from .field_source import read_field

            def rehearse(kernel, principal):
                field, _ = read_field(kernel, principal, title='', skip=set())
                sweep(kernel, principal, field);kernel.dispatch('field.doubt', {}, principal)
            return off_window.with_reads(self.host, rehearse, lambda: field_page.check_desk(self.host), key=('f3-check', id(self)))
        if obj is None:self.say_words(say('select_first'));return None
        if key == 'do':return field_page.do(self.host, obj)
        if key == 'doubt':return field_page.doubt(self.host, obj)
        if key == 'trace':      # 1.0 F3: its line's read made on a worker first; the trace then answers from it at once
            from . import off_window
            from .field_do import call as line_call, js
            try:operation, arguments = line_call('field.trace %s | pick rows | select way,steps,kind,title,state,by' % js(id=obj.id))
            except Exception:  # noqa: BLE001 - traced as before
                return field_page.trace(self.host, obj)
            off_window.prefetch(self.host, operation, arguments, lambda: field_page.trace(self.host, obj))
            return None
        if key == 'line':return field_page.stac_in_line(self.host, obj) if obj.stac else self.say_words(say('select_first'))
        return None

    def board_focus(self, page):
        """1.0 F3: the card focused on the board (the Field's object), when the board is in front and has a focus; else None."""
        try:
            board = getattr(page, 'board', None);inner = getattr(board, 'board', None)
            focus = getattr(inner, 'focus', None) if inner is not None else None
            if focus is None or not board.isVisible():return None
            obj = page.view.field.get(focus.id)
            if obj is not None and page.view.field.selected != obj.id:
                page.view.field.select(obj.id)      # the Field's selection follows: one selection, as the board shows it
            return obj
        except Exception:  # noqa: BLE001 - the Field's own selection, as before
            return None

    # -- the exchange -------------------------------------------------------------------------------------------------------
    def say_words(self, words):
        try:
            shell = self.host.shell2
            if self.host.console_pages.currentWidget() is not self.face:shell.show_slate_face()
            self.face.say(plain(words))
        except Exception:  # noqa: BLE001
            pass

    def ask(self, text):
        self.host.shell2.ask(text)

    def show_journal(self, ident):
        view = read(self.host, 'assignment.status', {'id': ident})
        if not view:      # 1.0 F2b: a 0.8.x assignment: its own words, through the old path (agent.status)
            from . import older_work
            words = older_work.journal_words(read(self.host, 'agent.status', {'id': ident}))
            if words:self.say_words(words)
            return
        lines = [say('journal_head', title=plain(view['title']), state=view['state_words'], line=plain(view['line']))]
        for step in view.get('steps') or ():
            lines.append(say('journal_step', n=step['n'], title=plain(step['title']), says=step['journal_says']))
        self.say_words('\n'.join(lines))

    def describe(self):
        """What each part shows now, in words (for a reader of the window: frames, checks, her hand's read-back)."""
        def text(w):return w.full() if isinstance(w, Line) else w.text()
        return {'name': self.head.name.text() + ' ' + self.head.ring.text(), 'state': self.head.word.text(),
                'portrait': (self.head.stage.portrait.image() or (None,) * 5)[4],
                'equalizer': {'tubes': len(self.equalizer.shown), 'hole': self.equalizer.hole, 'in_column': self.equalizer.parentWidget() is self.head.stage},
                'progress': {'shown': self.work_line.isVisible(), 'percent': self.work_line.percent.text(), 'detail': text(self.work_line.detail),
                             'checks': [text(w) for m, w in self.work_line.checks if w.isVisible()]},
                'active': {'heading': self.active.head.text(), 'rows': [(r.number.text(), r.shape.text(), text(r.title_words), r.state.text(), r.percent.text(), r.left.text(), r.stop.isVisible())
                                                                        for r in self.active.rows if r.isVisible()]},
                'findings': [(h.shape.text(), h.word.text(), text(h.words)) for h in self.found.rows if h.isVisible()],
                'next': [b.words for b in self.next.buttons],
                'commands': [b.text() for b in self.commands.buttons.values()],
                'ask': self.ask_line.edit.placeholderText(), 'turns_kept': self.face.KEEP_BUBBLES,
                'moment': self.moment.words if self.moment.isVisible() else ''}


def install(host):
    """host.her_column: her column in SlateFace, in every look. When it cannot be built, the column stays as it was."""
    if getattr(host, 'her_column', None) is not None:return host.her_column
    try:
        column = HerColumn(host)
    except Exception:  # noqa: BLE001 - the window starts with her old column rather than not at all
        import traceback
        traceback.print_exc()
        host.her_column = None
        return None
    host.her_column = column
    try:      # 1.0 X1: a save in the Office (a sheet's new value) has her column read the desk at once, so what rests on it is seen
        from . import floor
        concern = getattr(host, 'concern', None)
        if concern is not None:concern.changed.connect(lambda c=column: floor.column_soon(c))
    except Exception:  # noqa: BLE001 - the column still reads on its own tick
        pass
    return column
