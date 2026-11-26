"""The bulletin board, drawn (Graphite 1.0 L2): the centre's home at board depth.

The focused object sits in the middle, its neighbours on rings around it (board_model): what feeds it at the left, what
rests on it at the right, what is only possibly linked above and below, the nearer and larger the more relevant. Each tile
says its kind and state (KIND • STATE, with the state's mark, so the state never rests on colour alone), its title, the
basis of its link and where it comes from. Wires are solid when the records say the link and dashed when it is only
possible; a click on a wire opens a compact inspector with its basis in words. One click on a tile focuses it, through the
window's one navigation state (living_nav_qt, 1.0 L1): the tree reveals it and Back comes back. Opening (a double click,
Enter) is the route the Field always had (field_page.open_object); 1.0 L4 makes it the work depth.

The board lives in the Field's page (field_page.FieldPage): the page shows either the board or the Field, which is the
whole-desk map. Zooming out of the board (the wheel with Ctrl, the minus key, or "Whole desk" in its head) shows the Field;
"Board" on the Field brings the board back on the Field's selection. The Field's own acts (Do, Doubt, Trace, Brief, a
what-if) are drawn on the Field, so asking one while the board is in front shows the Field. One desk reading serves both:
the page reads the workspace with the board's reader (board_model.BoardReader), which keeps the answers the basis of each
link is read from.

Nothing here writes a file or a record. The one change it can ask for is the owner's word on a possible link
(board.keep, approve scope), and only from his press on "Keep this link".
"""
from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPainterPath, QPainterPathStroker, QPen, QPolygonF
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMenu, QPushButton, QSizePolicy, QToolButton, QVBoxLayout, QWidget

from . import boss_theme as t
from . import board_model as bm

ZOOM = (0.5, 1.6)                 # the board's sizes; below the least, the whole desk (the Field)
AUTO_LEAST = 0.74                 # shown whole only down to this size: below it the words are too small, and the board scrolls
SETTLED_WORDS = ('CURRENT', 'SUPPORTED', 'HOLDS', 'UP', 'RUNNING')
ATTENTION_WORDS = ('RECHECK', 'OPEN', 'HELD', 'REFUTED', 'WAITING', 'FAILED', 'DOES NOT HOLD', 'CANNOT TELL', 'DEPENDS', 'NOT READ')
QUIET_WORDS = ('ARCHIVED', 'REPLACED', 'UNAVAILABLE', 'ELSEWHERE')
RELATION_WORDS = {'reviewed': 'reviewed from its source', 'input': 'an input of a calculation', 'evidence': 'evidence for a finding',
                  'check': 'a check of a finding', 'revision': 'a revision', 'question': 'an open question', 'quote': 'a pinned quote',
                  'rests': 'what rests on it', 'condition': 'a total bound to words', 'same bytes': 'the same bytes',
                  'kept': 'kept by your word', 'same words': 'the same words', 'same component': 'the same component',
                  'used together': 'used together', 'revision by name': 'revisions by their names'}


def ink(colour, alpha=1.0):
    c = QColor(colour);c.setAlphaF(max(0.0, min(1.0, alpha)));return c


def state_ink(word):
    word = str(word or '').upper()
    if word in SETTLED_WORDS:return t.READY
    if word == 'RECHECK':return t.RECHECK
    if word in ATTENTION_WORDS:return t.OWNER
    return t.QUIET


def draw_mark(p, box, word, colour):
    """One mark per state, different in shape and not only in hue (as the Field's): settled a filled square, recheck half
    filled, open hollow, held or refuted crossed, waiting a dot, archived or replaced a dash."""
    word = str(word or '').upper();p.save();p.setPen(QPen(colour, 1.4));p.setBrush(Qt.NoBrush)
    if word in SETTLED_WORDS:
        p.setPen(Qt.NoPen);p.setBrush(colour);p.drawRect(box)
    elif word == 'RECHECK':
        p.drawRect(box);p.setPen(Qt.NoPen);p.setBrush(colour);p.drawRect(QRectF(box.left(), box.top(), box.width() / 2, box.height()))
    elif word in ('HELD', 'REFUTED', 'DOES NOT HOLD'):
        p.drawRect(box);p.drawLine(box.topLeft(), box.bottomRight())
    elif word in ('WAITING',):
        p.drawRect(box);p.setPen(Qt.NoPen);p.setBrush(colour);p.drawEllipse(box.center(), box.width() * 0.18, box.width() * 0.18)
    elif word in ('OPEN', 'CANNOT TELL', 'DEPENDS'):
        p.drawRect(box)
    else:
        p.drawLine(QPointF(box.left(), box.center().y()), QPointF(box.right(), box.center().y()))
    p.restore()


def kernel_of(host):
    return getattr(getattr(host, 'ledger_bridge', None), 'kernel', None)


class Inspector(QFrame):
    """The compact inspector of one wire: what kind of link it is, its two ends, and its basis in words."""

    def __init__(self, view):
        super().__init__(view)
        self.view = view;self.wire = None
        self.setObjectName('BoardInspector');self.setAccessibleName('The link\'s basis')
        layout = QVBoxLayout(self);layout.setContentsMargins(14, 10, 14, 10);layout.setSpacing(6)
        self.head = QLabel(self);self.head.setObjectName('BoardInspectorHead')
        self.ends = QLabel(self);self.ends.setObjectName('BoardInspectorEnds');self.ends.setWordWrap(True)
        self.body = QLabel(self);self.body.setObjectName('BoardInspectorBody');self.body.setWordWrap(True);self.body.setTextFormat(Qt.RichText)
        self.body.setTextInteractionFlags(Qt.TextSelectableByMouse)
        for w in (self.head, self.ends, self.body):layout.addWidget(w)
        row = QHBoxLayout();row.setSpacing(8);row.setContentsMargins(0, 4, 0, 0)
        self.keep = QPushButton('Keep this link', self);self.keep.setObjectName('BoardInspectorKeep')
        self.keep.setToolTip('Your word: the link is recorded as kept by you, solid on the board. You can set your word aside again.')
        self.unkeep = QPushButton('Set your word aside', self);self.unkeep.setObjectName('BoardInspectorKeep')
        self.other = QPushButton('', self);self.other.setObjectName('BoardInspectorButton')
        self.close_button = QPushButton('Close', self);self.close_button.setObjectName('BoardInspectorButton')
        for b in (self.keep, self.unkeep, self.other, self.close_button):
            b.setCursor(Qt.PointingHandCursor);b.setFocusPolicy(Qt.TabFocus);row.addWidget(b)
        row.addStretch(1);layout.addLayout(row)
        self.keep.clicked.connect(lambda: self.view.keep_link(self.wire, True))
        self.unkeep.clicked.connect(lambda: self.view.keep_link(self.wire, False))
        self.other.clicked.connect(self.go_other)
        self.close_button.clicked.connect(self.view.close_inspector)
        self.hide()

    def restyle(self, dashed):
        s = self.view.scale()
        self.setStyleSheet(
            'QFrame#BoardInspector {background:%s;border:1px %s %s;border-radius:3px;}'
            'QLabel#BoardInspectorHead {font-family:"%s";font-size:%dpx;font-weight:600;color:%s;background:transparent;border:0;}'
            'QLabel#BoardInspectorEnds {font-family:"%s";font-size:%dpx;color:%s;background:transparent;border:0;}'
            'QLabel#BoardInspectorBody {font-family:"%s";font-size:%dpx;color:%s;background:transparent;border:0;}'
            'QPushButton#BoardInspectorButton, QPushButton#BoardInspectorKeep {font-family:"%s";font-size:%dpx;color:%s;background:%s;'
            'border:1px solid %s;padding:3px 10px;border-radius:2px;}'
            'QPushButton#BoardInspectorKeep {color:%s;border-color:%s;}'
            'QPushButton:hover {border-color:%s;color:%s;}' % (
                t.RAISED, 'dashed' if dashed else 'solid', t.LINE_STRONG,
                t.MONO, round(12 * s), state_ink('OPEN') if dashed else t.READY,
                t.FACE, round(14 * s), t.TEXT,
                t.FACE, round(14 * s), t.QUIET,
                t.FACE, round(13 * s), t.QUIET, t.PANEL, t.LINE,
                t.AMBER_TEXT, t.AMBER_EDGE, t.READY, t.TEXT))

    def show_for(self, wire, at=None, title='', sentences=None):
        from html import escape
        self.wire = wire;board = self.view.board
        if wire is not None:
            a = board.get(wire.source);b = board.get(wire.target)
            an = a.title if a else wire.source;bn = b.title if b else wire.target
            dashed = wire.kind == bm.INFERRED
            self.restyle(dashed)
            self.head.setText(('POSSIBLE LINK  ·  NOT VERIFIED' if dashed else 'RECORDED LINK') + '  ·  ' + RELATION_WORDS.get(wire.relation, wire.relation).upper())
            self.ends.setText('%s  %s  %s' % (an, '—' if dashed else '→', bn))
            lines = list(wire.basis)
            self.keep.setVisible(dashed);self.unkeep.setVisible(bool(wire.kept))
            if dashed:self.keep.setText('Keep this link')
            focus = board.focus.id if board.focus else ''
            other = wire.target if wire.source == focus else wire.source if wire.target == focus else wire.target
            o = board.get(other)
            self.other.setVisible(o is not None and other != focus)
            if o is not None:
                self.other.setText('Focus %s' % bm._short(o.title, 18));self.other.setProperty('ident', other);self.other.setToolTip('Focus ' + o.title)
            self.setAccessibleDescription(' '.join(lines))
        else:                             # a panel of words of the board's own ("why am I shown?")
            self.restyle(False);self.head.setText(title.upper());self.ends.setText('');lines = list(sentences or ())
            self.keep.hide();self.unkeep.hide();self.other.hide()
        self.ends.setVisible(bool(self.ends.text()))
        self.body.setText(''.join('<p style="margin:0 0 4px 0">%s</p>' % escape(str(x)) for x in lines))
        s = self.view.scale();width = min(round(470 * s), max(260, self.view.width() - 40))
        self.setFixedWidth(width);self.body.setFixedWidth(width - 28);self.ends.setFixedWidth(width - 28)
        self.adjustSize()
        x, y = (at.x(), at.y()) if at is not None else (self.view.width() - width - 20, self.view.head_height() + 16)
        x = max(12, min(self.view.width() - width - 12, x - width / 2));y = max(self.view.head_height() + 8, min(self.view.height() - self.height() - 12, y + 14))
        self.move(int(x), int(y));self.show();self.raise_()

    def go_other(self):
        ident = self.other.property('ident')
        if ident:self.view.close_inspector();self.view.choose(ident)


class BoardView(QWidget):
    """The board of one focus. `focused` carries the object the owner chose (one click); `opened` the one he opened."""
    focused = Signal(object)
    opened = Signal(object)
    whole = Signal()
    left = Signal()

    def __init__(self, page):
        super().__init__(page)
        self.page = page;self.host = page.host
        self.board = bm.Board();self.ident = ''
        self.reading = None               # (field, reader) the page last read
        self.desk = None;self._desk_key = None
        self.zoom = 1.0;self.auto = True;self.pan_x = 0.0;self.pan_y = 0.0
        self.placed = {};self.ring_radii = [];self.bounds = (-1, -1, 1, 1);self._paths = []
        self.hover = '';self.hover_wire = None;self.chosen_wire = None;self._press = None;self._panned = False
        self.task = None
        self.problem = ''
        self._stale = True                # a new reading came while the board was not drawn: it is drawn again when shown
        self.inspector = Inspector(self)
        self.setMouseTracking(True);self.setFocusPolicy(Qt.StrongFocus)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored);self.setMinimumSize(0, 0)
        self.setObjectName('GraphiteBoard');self.setAccessibleName('Board: the focused object and what is linked to it')

    def sizeHint(self):
        return QSize(0, 0)

    def minimumSizeHint(self):
        return QSize(0, 0)

    # ---- measures ------------------------------------------------------------------------------------------------------
    def scale(self):
        return max(0.85, min(3.5, self.fontInfo().pixelSize() / 16.0))

    def mono(self, px, weight=QFont.Normal):
        f = QFont(t.MONO);f.setStyleHint(QFont.Monospace);f.setPixelSize(max(9, round(px * self.scale())));f.setWeight(weight);return f

    def sans(self, px, weight=QFont.Medium):
        f = QFont(t.FACE);f.setPixelSize(max(9, round(px * (0.97 if t.FACE != 'IBM Plex Sans' else 1.0) * self.scale())))
        f.setWeight(weight if t.FACE == 'IBM Plex Sans' else QFont.Normal)
        if t.FACE != 'IBM Plex Sans':f.setLetterSpacing(QFont.AbsoluteSpacing, -0.35)
        return f

    def display(self, px):
        if t.DISPLAY == t.MONO:return self.mono(px, QFont.Medium)
        f = QFont(t.DISPLAY);f.setPixelSize(max(12, round(px * 1.12 * self.scale())));return f

    def head_height(self):
        return round(max(40.0, 44 * self.scale()))

    def body(self):
        return QRectF(0, self.head_height(), self.width(), max(1, self.height() - self.head_height()))

    def centre(self):
        b = self.body();return QPointF(b.center().x(), b.center().y())

    def to_screen(self, x, y):
        c = self.centre();return QPointF(c.x() + (x - self.pan_x) * self.zoom, c.y() + (y - self.pan_y) * self.zoom)

    def to_surface(self, point):
        c = self.centre();return ((point.x() - c.x()) / self.zoom + self.pan_x, (point.y() - c.y()) / self.zoom + self.pan_y)

    def fit(self):
        """The size at which the whole board is in the window around its focus, at most the ordinary size, and never so small
        that its words cannot be read (AUTO_LEAST): then the board scrolls, the focus in the middle."""
        x0, y0, x1, y1 = self.bounds;b = self.body()
        half_w = max(-x0, x1, 1.0);half_h = max(-y0, y1, 1.0)
        if b.width() < 10:return 1.0
        return max(AUTO_LEAST, min(1.0, (b.width() - 16) / (2 * half_w), (b.height() - 8) / (2 * half_h)))

    # ---- the reading and the focus ---------------------------------------------------------------------------------------
    def desk_read(self, field, reader):
        """The page read the workspace (its work face): the board is drawn from this reading from now on."""
        self.reading = (field, reader);self._desk_key = None;self._stale = True
        if self.isVisible() or getattr(self.page, 'mode', '') == 'board':self.rebuild()

    def living(self):
        return getattr(self.host, 'living_nav', None)

    def make_desk(self):
        field, reader = self.reading if self.reading is not None else (None, None)
        kernel = kernel_of(self.host)
        if (field is None or not isinstance(reader, bm.BoardReader)) and kernel is not None:
            # the page's reading was made without the board's reader (the launch's), or there is none yet: one reading of ours
            from .engineering_kernel import operator
            try:
                field, reader = bm.read_desk(kernel, operator(), skip=getattr(self.page, 'unread', ()) or ())
                self.reading = (field, reader)
            except Exception as exc:  # noqa: BLE001 - the board says it could not read, never takes the window down
                self.problem = 'The desk could not be read: %s' % str(exc)[:160]
        if field is None:return None
        living = self.living();files = getattr(living, 'files', None) if living is not None else None
        kept = []
        if kernel is not None:
            from .engineering_kernel import operator
            try:
                answer = kernel.dispatch('board.links', {}, operator())
                kept = (answer.get('result') or {}).get('links', []) if answer.get('ok') else []
            except Exception:  # noqa: BLE001
                kept = []
        key = (id(field), id(files), tuple((k['id'], k['revision'], k['state']) for k in kept))
        if self.desk is None or key != self._desk_key:
            digest = getattr(living, 'digest_of', None) if living is not None else None
            self.desk = bm.Desk(field, reader, files, kept, digest);self._desk_key = key
            if kernel is not None:          # what the owner's assignments read together (1.0 K1): a possible link "used together"
                from .engineering_kernel import operator

                def call(op, args):
                    answer = kernel.dispatch(op, args, operator())
                    return answer.get('result') if answer.get('ok') else None
                self.desk.set_assignments(bm.read_assignments(call))
        return self.desk

    def rebuild(self, keep_place=True):
        desk = self.make_desk()
        kernel = kernel_of(self.host)
        if desk is None:
            self.board = bm.Board(note=self.problem or 'Graphite\'s records are not available in this window.')
        else:
            first = self.page.view.field.selected if getattr(self.page, 'view', None) is not None else ''
            self.board = bm.build(desk, self.ident, kernel, self.task, first=first)
            if self.board.focus is not None:self.ident = self.board.focus.id
        self._stale = False
        self.relayout()
        if self.auto:self.zoom = self.fit()
        if not keep_place:self.pan_x = self.pan_y = 0.0
        self.describe();self.update()

    def relayout(self):
        self.placed, self.ring_radii, self.bounds = bm.layout(self.board, self.scale())

    def focus_on(self, ident, again=False):
        """Bring this object to the middle (the window's navigation asks; a click here asks too). Returns whether it is on the
        board now. The Field's selection follows, so the window's "this" and the Field's acts are about the same object."""
        changed = ident != self.ident or again
        if ident:self.ident = ident
        if changed or not self.placed or self._stale:
            self.close_inspector();self.chosen_wire = None
            if again:self._desk_key = None
            self.rebuild(keep_place=False)
        self.sync_field()
        return self.board.focus is not None and self.board.focus.id == ident

    def sync_field(self):
        view = getattr(self.page, 'view', None)
        if view is None or self.board.focus is None:return
        ident = self.board.focus.id
        if view.field.get(ident) is not None and view.field.selected != ident:
            view.field.select(ident);view._reveal_pending = True;view._describe()

    def focus_obj(self):
        return self.board.focus.obj if self.board.focus is not None else None

    def describe(self):
        f = self.board.focus
        if f is None:
            self.setAccessibleDescription(self.board.note or 'Nothing in focus.');return
        said = ['In focus: %s, %s%s.' % (f.kind_word.lower(), f.title, (', ' + f.state_word.lower()) if f.state_word else '')]
        for tile in self.board.tiles:
            if tile.id == bm.MORE:said.append('%s, grouped.' % tile.title);continue
            said.append('%s %s%s: %s.' % (tile.kind_word.lower(), tile.title, (', ' + tile.state_word.lower()) if tile.state_word else '', tile.basis))
        self.setAccessibleDescription(' '.join(said))

    # ---- choosing -------------------------------------------------------------------------------------------------------
    def choose(self, ident):
        """The owner chose a tile: it is the focus now (the navigation hears of it, the tree reveals it)."""
        tile = self.board.get(ident)
        if tile is None or tile.id == bm.MORE:return
        obj = tile.obj
        if tile.id == self.ident:return
        self.focus_on(tile.id)
        self.focused.emit(obj)

    def open_tile(self, ident):
        tile = self.board.get(ident)
        if tile is None or tile.obj is None or tile.id == bm.MORE:return
        obj = tile.obj
        if isinstance(obj.target, dict) and obj.target.get('kind') == 'file':
            living = self.living()
            if living is not None:living.open(obj.id)
            else:
                from .living_nav_qt import open_path
                open_path(self.host, obj.target.get('path') or '')
            return
        view = getattr(self.page, 'view', None)
        if view is not None:view.opened.emit(view.field.get(obj.id) or obj)       # the route the Field always had (field_page.open_object)
        self.opened.emit(obj)

    def keep_link(self, wire, keep):
        """The owner's word on a link (board.keep, approve scope): only from his press here."""
        kernel = kernel_of(self.host)
        if wire is None or kernel is None:return
        from .engineering_kernel import operator
        args = {'source': wire.source, 'target': wire.target, 'said': (wire.said or '')[:300]} if keep else {'id': wire.kept, 'state': 'OUT'}
        answer = kernel.dispatch('board.keep', args, operator())
        bar = getattr(self.host, 'statusBar', None)
        if not answer.get('ok'):
            if bar:self.host.statusBar().showMessage('The link could not be kept: %s' % str((answer.get('error') or {}).get('message') or answer.get('error'))[:160], 8000)
            return
        if bar:self.host.statusBar().showMessage('Kept by your word: the link is recorded' if keep else 'Your word is set aside: the link is possible again, not verified', 6000)
        self._desk_key = None;self.close_inspector();self.rebuild()
        found = self.board.wire(wire.source, wire.target)
        if found is not None:self.open_wire(found)

    # ---- the inspector ------------------------------------------------------------------------------------------------------
    def open_wire(self, wire, at=None):
        self.chosen_wire = wire.key() if wire is not None else None
        if at is None and wire is not None:
            a = self.placed.get(wire.source);b = self.placed.get(wire.target)
            if a and b:at = self.to_screen((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        self.inspector.show_for(wire, at);self.update()

    def close_inspector(self):
        if self.inspector.isVisible():self.inspector.hide()
        self.chosen_wire = None;self.update()

    def why(self, tile):
        lines = list(tile.reasons)
        marks = [('truth', 'Its state'), ('confidence', 'Its link'), ('authority', 'Its revision')]
        separate = ['%s: %s.' % (word, tile.separate[key]) for key, word in marks if tile.separate.get(key)]
        module = bm.relevance_module()
        if module is not None and callable(getattr(module, 'why', None)):
            answer = _call(module.why, kernel_of(self.host), self.ident, tile.id)
            if isinstance(answer, dict):answer = answer.get('reasons') or answer.get('words')
            if isinstance(answer, (list, tuple)) and answer:lines = [str(x) for x in answer]
            elif isinstance(answer, str) and answer:lines = [answer]
        lines = (lines or ['It is linked to what is in focus.']) + (['Marked on their own, never in its size:'] + separate if separate else [])
        self.inspector.show_for(None, None, 'Why am I shown?  ·  ' + bm._short(tile.title, 40), lines)

    # ---- painting -----------------------------------------------------------------------------------------------------------
    def paintEvent(self, event):
        p = QPainter(self)
        try:
            p.setRenderHint(QPainter.Antialiasing);p.setRenderHint(QPainter.TextAntialiasing)
            p.fillRect(self.rect(), QColor(t.TERMINAL_GROUND))
            self._paths = []
            body = self.body()
            if self.board.focus is None:
                self._head(p);self._empty(p, body);return
            p.save();p.setClipRect(body)
            c = self.centre();p.translate(c);p.scale(self.zoom, self.zoom);p.translate(-self.pan_x, -self.pan_y)
            self._rings(p)
            self._wires(p)
            for tile in sorted(self.board.all(), key=lambda t: t.size):
                if tile.id in self.placed:self._tile(p, tile)
            self._wire_words(p)
            p.restore()
            self._head(p)
        except Exception as exc:  # noqa: BLE001 - said on the surface, never taking the window down
            p.setClipping(False);p.setPen(QColor(t.CUE_TEXT));p.setFont(self.mono(12))
            p.drawText(QRectF(24, self.head_height() + 12, self.width() - 48, 40), Qt.AlignLeft | Qt.AlignVCenter, 'The board could not be drawn: %s' % str(exc)[:160])
        finally:
            p.end()

    def _head(self, p):
        s = self.scale();h = self.head_height();x = 24 * s
        p.fillRect(QRectF(0, 0, self.width(), h), QColor(t.PANEL))
        p.setPen(QPen(QColor(t.LINE), 1));p.drawLine(QPointF(0, h - 0.5), QPointF(self.width(), h - 0.5))
        p.setFont(self.display(13));fm = QFontMetricsF(p.font());base = h / 2 + fm.ascent() / 2 - 2
        p.setPen(QColor(t.CUE_EDGE));p.drawText(QPointF(x, base), 'BOARD');x += fm.horizontalAdvance('BOARD') + 16 * s
        # the right: the legend (a solid wire is recorded, a dashed one only possible) and the way to the whole desk
        p.setFont(self.mono(12));fm2 = QFontMetricsF(p.font())
        counts = self.board.counts()
        whole = 'Whole desk';ww = fm2.horizontalAdvance(whole) + 26 * s
        right = self.width() - 18 * s
        self._whole_box = QRectF(right - ww, (h - 26 * s) / 2, ww, 26 * s)
        over = self._whole_box.contains(getattr(self, '_mouse', QPointF(-1, -1)))
        p.setPen(QPen(ink(t.READY if over else t.LINE_STRONG, 0.9), 1));p.setBrush(Qt.NoBrush);p.drawRect(self._whole_box)
        cx = self._whole_box.left() + 10 * s;cy = self._whole_box.center().y()
        p.drawEllipse(QPointF(cx, cy), 4.5 * s, 3.2 * s)          # a small ring: the whole desk is further out
        p.setPen(QColor(t.READY if over else t.QUIET));p.drawText(QPointF(cx + 9 * s, base), whole)
        right = self._whole_box.left() - 22 * s
        legend = [('possible, not verified', 'possible', True, counts['possible']), ('recorded', 'recorded', False, counts['recorded'])]
        for words, short, dashed, n in legend:
            label = '%d %s' % (n, words);w = fm2.horizontalAdvance(label);line = 26 * s
            if right - w - line - 10 * s < x + 200 * s:
                label = '%d %s' % (n, short);w = fm2.horizontalAdvance(label)
            if right - w - line - 10 * s < x + 90 * s:break
            p.setPen(QColor(t.QUIET));p.drawText(QPointF(right - w, base), label)
            pen = QPen(ink(t.TEAL_EDGE if t.APPEARANCE == 'kasandra' else t.LINE_STRONG, 0.95), 1.6)
            if dashed:pen.setStyle(Qt.CustomDashLine);pen.setDashPattern([4, 3])
            p.setPen(pen);y = base - fm2.ascent() / 2 + 1;p.drawLine(QPointF(right - w - line - 8 * s, y), QPointF(right - w - 8 * s, y))
            right -= w + line + 26 * s
        f = self.board.focus
        if f is not None:
            p.setFont(self.sans(16));fm3 = QFontMetricsF(p.font());p.setPen(QColor(t.TEXT))
            p.drawText(QPointF(x, h / 2 + fm3.ascent() / 2 - 2), fm3.elidedText(f.title, Qt.ElideRight, max(40.0, right - x - 10 * s)))

    def _empty(self, p, body):
        s = self.scale();p.setFont(self.sans(15));p.setPen(QColor(t.QUIET))
        p.drawText(body.adjusted(40 * s, 40 * s, -40 * s, -40 * s), Qt.AlignCenter | Qt.TextWordWrap, self.board.note or 'Nothing in focus.')

    def _rings(self, p):
        """The rings round the focus (green the inner, the wires' ink the outer ones) and the axis through the middle, with a
        small square handle at each end, as in the owner's picture."""
        s = self.scale()
        blue = t.TEAL_EDGE;green = t.READY
        radii = list(self.ring_radii)
        if not radii:return
        fw, fh = bm.FOCUS_DIMS[0] * s, bm.FOCUS_DIMS[1] * s
        inner = ((fw / 2 + radii[0][0]) / 2 * 0.98, (fh / 2 + radii[0][1]) / 2 * 0.98)
        for n, (rx, ry) in enumerate([inner] + radii):
            path = QPainterPath();pts = bm.ring_path(rx, ry)
            path.moveTo(QPointF(*pts[0]))
            for x, y in pts[1:]:path.lineTo(QPointF(x, y))
            path.closeSubpath()
            colour = green if n == 1 else blue
            p.setBrush(Qt.NoBrush);p.setPen(QPen(ink(colour, 0.34 if n == 1 else 0.26), (1.6 if n == 1 else 1.1) / max(0.6, self.zoom)));p.drawPath(path)
        top = -radii[-1][1] - 26 * s;bottom = radii[-1][1] + 26 * s
        p.setPen(QPen(ink(blue, 0.3), 1.0 / max(0.6, self.zoom)))
        p.drawLine(QPointF(0, top), QPointF(0, -fh / 2 - 6 * s));p.drawLine(QPointF(0, fh / 2 + 6 * s), QPointF(0, bottom))
        k = 7 * s;p.setBrush(ink(blue, 0.55));p.setPen(Qt.NoPen)
        for y in (top, bottom):p.drawRect(QRectF(-k / 2, y - k / 2, k, k))

    def rect_of(self, ident):
        x, y, w, h = self.placed[ident];return QRectF(x - w / 2, y - h / 2, w, h)

    @staticmethod
    def _edge_point(r, toward):
        """Where the line from a rectangle's centre toward a point leaves the rectangle."""
        c = r.center();dx = toward.x() - c.x();dy = toward.y() - c.y()
        if abs(dx) < 1e-6 and abs(dy) < 1e-6:return c
        tx = (r.width() / 2) / abs(dx) if abs(dx) > 1e-6 else math.inf;ty = (r.height() / 2) / abs(dy) if abs(dy) > 1e-6 else math.inf
        k = min(tx, ty);return QPointF(c.x() + dx * k, c.y() + dy * k)

    def _wire_path(self, wire):
        a = self.rect_of(wire.source);b = self.rect_of(wire.target)
        pa = self._edge_point(a, b.center());pb = self._edge_point(b, a.center())
        mid = QPointF((pa.x() + pb.x()) / 2, (pa.y() + pb.y()) / 2)
        dx = pb.x() - pa.x();dy = pb.y() - pa.y();length = math.hypot(dx, dy) or 1.0
        bend = 0.07 * length * (1 if (hash(wire.relation) & 1) else -1) if wire.kind == bm.INFERRED else 0.04 * length
        ctrl = QPointF(mid.x() - dy / length * bend, mid.y() + dx / length * bend)
        path = QPainterPath(pa);path.quadTo(ctrl, pb)
        return path, pa, pb

    def _wires(self, p):
        s = self.scale();focus = self.board.focus.id
        self._labels = []
        for wire in self.board.wires:
            if wire.source not in self.placed or wire.target not in self.placed:continue
            path, pa, pb = self._wire_path(wire)
            touching = focus in (wire.source, wire.target)
            hovered = self.hover_wire == wire.key() or (self.hover and self.hover in (wire.source, wire.target))
            chosen = self.chosen_wire == wire.key()
            base = t.TEAL_EDGE if t.APPEARANCE == 'kasandra' else t.LINE_STRONG
            colour = t.AMBER_EDGE if chosen else t.READY if hovered else t.RECHECK if wire.stale else base
            strength = 1.0 if (touching or hovered or chosen or wire.stale) else 0.62
            width = (2.4 if chosen else 1.8 if (touching or hovered) else 1.3)
            pen = QPen(ink(colour, strength), width, Qt.SolidLine, Qt.RoundCap)
            if wire.dashed:pen.setStyle(Qt.CustomDashLine);pen.setDashPattern([5, 4])
            p.setBrush(Qt.NoBrush);p.setPen(pen);p.drawPath(path)
            p.setPen(Qt.NoPen);p.setBrush(ink(colour, strength))
            for point in (pa, pb):p.drawEllipse(point, 3.4 * s, 3.4 * s)           # the round ends of the picture's wires
            if not wire.dashed:
                p.setPen(QPen(ink(t.TERMINAL_GROUND, 0.9), 1.1));p.setBrush(Qt.NoBrush)
                for point in (pa, pb):p.drawEllipse(point, 1.3 * s, 1.3 * s)
            stroker = QPainterPathStroker();stroker.setWidth(max(10.0, 12.0 / self.zoom))
            self._paths.append((stroker.createStroke(path), wire))
            if touching or hovered or chosen or wire.stale:
                word = wire.label if not wire.dashed else 'possible · not verified'
                if wire.stale and 'recheck' not in word:word = word + ' · recheck'
                self._labels.append((path.pointAtPercent(0.5), word, colour))

    def _wire_words(self, p):
        s = self.scale();p.setFont(self.mono(11));fm = QFontMetricsF(p.font())
        taken = []
        for point, word, colour in self._labels:
            w = fm.horizontalAdvance(word) + 10 * s;h = fm.height() + 2 * s
            box = QRectF(point.x() - w / 2, point.y() - h / 2, w, h)
            if any(box.intersects(r) for r in taken) or any(box.intersects(self.rect_of(i)) for i in self.placed):continue
            taken.append(box)
            p.setPen(Qt.NoPen);p.setBrush(ink(t.TERMINAL_GROUND, 0.88));p.drawRect(box)
            p.setPen(ink(colour, 0.95));p.drawText(box, Qt.AlignCenter, word)

    def _tile(self, p, tile):
        s = self.scale();r = self.rect_of(tile.id);focus = tile.id == self.board.focus.id
        over = self.hover == tile.id and not focus
        lit = focus and self.hasFocus()
        p.setBrush(QColor(t.CARD if tile.size >= 2 or focus else t.PANEL))
        edge = t.AMBER_EDGE if lit else t.READY if over else (t.LINE_STRONG if (focus or tile.size >= 3) else t.LINE_MID)
        pen = QPen(ink(edge, 1.0 if (focus or over) else 0.85), 2 if focus else 1)
        if tile.id == bm.MORE:pen.setStyle(Qt.CustomDashLine);pen.setDashPattern([2, 3])
        p.setPen(pen);p.drawRect(r)
        if focus:
            # the striped corner of the picture's focus tile, and the corner ticks that say "in focus" without colour
            p.save();p.setClipRect(r);p.setPen(QPen(ink(t.TEAL_EDGE, 0.55), 1.4 * s));k = 34 * s
            for i in range(5):
                o = i * 7 * s;p.drawLine(QPointF(r.right() - k + o, r.top()), QPointF(r.right(), r.top() + k - o))
            p.restore()
            p.setPen(QPen(ink(t.AMBER_EDGE if lit else t.LINE_STRONG, 1.0), 2));k = 10 * s;o = 6 * s
            for cx, cy, dx, dy in ((r.left() - o, r.top() - o, 1, 1), (r.right() + o, r.top() - o, -1, 1),
                                   (r.left() - o, r.bottom() + o, 1, -1), (r.right() + o, r.bottom() + o, -1, -1)):
                p.drawLine(QPointF(cx, cy), QPointF(cx + dx * k, cy));p.drawLine(QPointF(cx, cy), QPointF(cx, cy + dy * k))
        pad = (14 if focus else 11) * s;inner = r.adjusted(pad, pad - 3 * s, -pad, -pad + 3 * s)
        # the first line: the kind's glyph, KIND • STATE, the state's mark
        p.setFont(self.mono(12 if tile.size >= 3 or focus else 11, QFont.Medium));fm = QFontMetricsF(p.font());y = inner.top() + fm.ascent()
        lead = 0.0
        from .glyph_set import KIND as KIND_GLYPH
        draw = KIND_GLYPH.get(tile.kind)
        kind_ink = t.CUE_TEXT if tile.kind in ('question', 'condition') else t.QUIET
        if draw is not None and inner.width() > 80 * s:
            side = fm.height() * 1.1;box = QRectF(inner.left(), y - fm.ascent() + (fm.height() - side) / 2 - 1, side, side)
            p.save();p.translate(box.left(), box.top());p.scale(box.width() / 20.0, box.height() / 20.0);p.setPen(Qt.NoPen);p.setBrush(Qt.NoBrush)
            try:draw(p, ink(kind_ink, 1.0), ink(t.FAINT, 1.0))
            finally:p.restore()
            lead = side + 6 * s
        kind = tile.kind_word or 'THING';state = tile.state_word
        p.setPen(ink(kind_ink, 1.0));p.drawText(QPointF(inner.left() + lead, y), kind)
        x = inner.left() + lead + fm.horizontalAdvance(kind)
        if state:
            colour = state_ink(state);dot = ' • ';p.setPen(ink(t.FAINT, 1.0));p.drawText(QPointF(x, y), dot);x += fm.horizontalAdvance(dot)
            mark = 8 * s;room = inner.right() - x - mark - 6 * s
            p.setPen(ink(colour, 1.0));shown = fm.elidedText(state, Qt.ElideRight, max(10.0, room));p.drawText(QPointF(x, y), shown)
            draw_mark(p, QRectF(min(inner.right() - mark, x + fm.horizontalAdvance(shown) + 7 * s), y - fm.ascent() / 2 - mark / 2 + 1, mark, mark), state, ink(colour, 1.0))
        y += 5 * s
        # the title, whole words on up to two lines
        p.setFont(self.sans({4: 17, 3: 15, 2: 14, 1: 13}[4 if focus else tile.size]));fm = QFontMetricsF(p.font());p.setPen(QColor(t.TEXT))
        lines = 2 if (focus or tile.size >= 2) else 1
        for line in _wrap(tile.title, fm, inner.width(), lines):
            y += fm.height();p.drawText(QPointF(inner.left(), y - fm.descent()), line)
        # the basis line and the source
        p.setFont(self.mono(12 if focus or tile.size >= 3 else 11));fm = QFontMetricsF(p.font());y += 4 * s
        if tile.basis and y + fm.height() <= inner.bottom() + 2 * s:
            y += fm.height();p.setPen(ink(t.CUE_TEXT if not tile.recorded and t.APPEARANCE == 'kasandra' else t.QUIET, 1.0))
            p.drawText(QPointF(inner.left(), y - fm.descent()), fm.elidedText(tile.basis, Qt.ElideRight, inner.width()))
        if tile.source and y + fm.height() <= inner.bottom() + 2 * s:
            y += fm.height();p.setPen(QColor(t.FAINT))
            p.drawText(QPointF(inner.left(), y - fm.descent()), fm.elidedText(str(tile.source), Qt.ElideMiddle, inner.width()))

    # ---- the mouse and the keys ---------------------------------------------------------------------------------------------
    def tile_at(self, point):
        x, y = self.to_surface(point)
        for tile in sorted(self.board.all(), key=lambda t: -t.size):
            if tile.id in self.placed and self.rect_of(tile.id).contains(QPointF(x, y)):return tile
        return None

    def wire_at(self, point):
        x, y = self.to_surface(point)
        for shape, wire in reversed(self._paths):
            if shape.contains(QPointF(x, y)):return wire
        return None

    def mousePressEvent(self, event):
        self.setFocus(Qt.MouseFocusReason)
        pos = event.position()
        if event.button() == Qt.LeftButton:
            if getattr(self, '_whole_box', QRectF()).contains(pos):
                self.whole.emit();return
            self._press = (pos, self.pan_x, self.pan_y);self._panned = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        pos = event.position();self._mouse = pos
        if self._press is not None and event.buttons() & Qt.LeftButton:
            start, px, py = self._press
            if self._panned or (pos - start).manhattanLength() > 6:
                self._panned = True;self.pan_x = px - (pos.x() - start.x()) / self.zoom;self.pan_y = py - (pos.y() - start.y()) / self.zoom
                self.setCursor(Qt.ClosedHandCursor);self.update();return
        tile = self.tile_at(pos) if pos.y() > self.head_height() else None
        wire = None if tile is not None or pos.y() <= self.head_height() else self.wire_at(pos)
        hover = tile.id if tile is not None else ''
        hw = wire.key() if wire is not None else None
        if hover != self.hover or hw != self.hover_wire:
            self.hover = hover;self.hover_wire = hw;self.update()
        over_whole = getattr(self, '_whole_box', QRectF()).contains(pos)
        self.setCursor(Qt.PointingHandCursor if (tile is not None and tile.id != self.ident) or wire is not None or over_whole else Qt.ArrowCursor)
        if over_whole:self.update(self._whole_box.toRect().adjusted(-2, -2, 2, 2))
        if tile is not None:self.setToolTip(tile.title)
        elif wire is not None:self.setToolTip('The link\'s basis: click')
        else:self.setToolTip('')

    def mouseReleaseEvent(self, event):
        press = self._press;self._press = None
        if self._panned:
            self._panned = False;self.setCursor(Qt.ArrowCursor);return
        if press is None or event.button() != Qt.LeftButton:return super().mouseReleaseEvent(event)
        pos = event.position()
        tile = self.tile_at(pos)
        if tile is not None:
            if tile.id == bm.MORE:self.more_menu(tile, pos)
            elif tile.id != self.ident:self.choose(tile.id)
            return
        wire = self.wire_at(pos)
        if wire is not None:
            self.open_wire(wire, pos);return
        self.close_inspector()

    def mouseDoubleClickEvent(self, event):
        tile = self.tile_at(event.position())
        if tile is not None and tile.id != bm.MORE:
            if tile.id != self.ident:self.choose(tile.id)
            self.open_tile(tile.id)

    def leaveEvent(self, event):
        if self.hover or self.hover_wire:self.hover = '';self.hover_wire = None;self.update()

    def wheelEvent(self, event):
        turn = event.angleDelta().y() or event.angleDelta().x()
        if event.modifiers() & Qt.ControlModifier:
            if turn:self.zoom_by(1 if turn > 0 else -1)
            return
        if event.modifiers() & Qt.ShiftModifier:self.pan_x -= turn / 2.0 / self.zoom
        else:self.pan_x -= event.angleDelta().x() / 2.0 / self.zoom;self.pan_y -= event.angleDelta().y() / 2.0 / self.zoom
        self.update()

    def zoom_by(self, step):
        """Larger or smaller by a twentieth; smaller than the least is the whole desk (the Field)."""
        want = round(self.zoom * 20 + step) / 20.0
        if want < ZOOM[0] - 1e-9:      # out past the least: the whole desk; the board comes back whole the next time
            self.auto = True;self.whole.emit();return
        self.auto = False;self.zoom = max(ZOOM[0], min(ZOOM[1], want));self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.auto:self.zoom = self.fit()
        if self.inspector.isVisible():self.close_inspector()

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Escape:
            if self.inspector.isVisible():self.close_inspector()
            else:self.left.emit()
            return
        if key in (Qt.Key_Return, Qt.Key_Enter):
            if self.ident:self.open_tile(self.ident)
            return
        if key in (Qt.Key_Minus, Qt.Key_Underscore):self.zoom_by(-1);return
        if key in (Qt.Key_Plus, Qt.Key_Equal):self.zoom_by(1);return
        if key == Qt.Key_Z:self.whole.emit();return
        if key in (Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down):
            self.step(key);return
        if key == Qt.Key_Menu and self.board.focus is not None:
            self.tile_menu(self.board.focus, self.to_screen(*self.placed[self.board.focus.id][:2]));return
        super().keyPressEvent(event)

    def step(self, key):
        """The arrow keys: the nearest tile that way from the focus becomes the focus."""
        if self.board.focus is None or self.ident not in self.placed:return
        fx, fy = self.placed[self.ident][:2]
        want = {Qt.Key_Left: (-1, 0), Qt.Key_Right: (1, 0), Qt.Key_Up: (0, -1), Qt.Key_Down: (0, 1)}[key]
        best = None
        for tile in self.board.tiles:
            if tile.id not in self.placed or tile.id == bm.MORE:continue
            x, y = self.placed[tile.id][:2];dx, dy = x - fx, y - fy
            along = dx * want[0] + dy * want[1]
            if along <= 1:continue
            across = abs(dx * want[1]) + abs(dy * want[0])
            score = along + 2 * across
            if best is None or score < best[0]:best = (score, tile.id)
        if best is not None:self.choose(best[1])

    def contextMenuEvent(self, event):
        tile = self.tile_at(QPointF(event.pos()))
        if tile is None:
            wire = self.wire_at(QPointF(event.pos()))
            if wire is not None:self.open_wire(wire, QPointF(event.pos()))
            return
        self.tile_menu(tile, QPointF(event.pos()))

    def tile_menu(self, tile, at):
        menu = QMenu(self);menu.setObjectName('BoardMenu')
        if tile.id == bm.MORE:
            return self.more_menu(tile, at)
        if tile.id != self.ident:menu.addAction('Focus here', lambda i=tile.id: self.choose(i))
        menu.addAction('Open', lambda i=tile.id: self.open_tile(i))
        wire = self.board.wire(tile.id, self.ident) or (self.board.wire(tile.id, tile.bridge) if tile.bridge else None)
        if wire is not None:menu.addAction('The link\'s basis', lambda w=wire: self.open_wire(w))
        module = bm.relevance_module()          # 1.0 L3's: shown only when relevance is there
        if module is not None and tile.id != self.ident:
            menu.addSeparator()
            if callable(getattr(module, 'why', None)):menu.addAction('Why am I shown?', lambda x=tile: self.why(x))
            if callable(getattr(module, 'pin', None)):
                menu.addAction('Unpin' if tile.pinned else 'Pin', lambda x=tile: self.relevance_act('clear' if x.pinned else 'pin', x))
            if callable(getattr(module, 'turn_down', None)):
                menu.addAction('Turn up again' if tile.turned_down else 'Turn down', lambda x=tile: self.relevance_act('clear' if x.turned_down else 'turn_down', x))
        menu.addSeparator()
        menu.addAction('Whole desk', self.whole.emit)
        menu.exec(self.mapToGlobal(at.toPoint()))

    def relevance_act(self, name, tile):
        module = bm.relevance_module()
        fn = getattr(module, name, None) if module is not None else None
        if fn is None:return
        _call(fn, kernel_of(self.host), self.ident, tile.id)
        self.rebuild()

    def more_menu(self, tile, at):
        menu = QMenu(self);menu.setObjectName('BoardMenu')
        module = bm.relevance_module()
        for member in tile.members:
            menu.addAction('%s  ·  %s%s%s' % (member.kind_word, bm._short(member.title, 60), ('  ·  ' + member.state_word) if member.state_word else '',
                                              '  ·  turned down by you' if member.turned_down else ''),
                           lambda i=member.id: self.focus_member(i))
        turned = [m for m in tile.members if m.turned_down]
        if turned and module is not None and callable(getattr(module, 'clear', None)):      # reversible, where it is grouped
            menu.addSeparator()
            for member in turned:
                menu.addAction('Turn up again: %s' % bm._short(member.title, 50), lambda x=member: self.relevance_act('clear', x))
        menu.exec(self.mapToGlobal(at.toPoint()))

    def focus_member(self, ident):
        """A grouped tile chosen from the count: it becomes the focus."""
        tile = next((m for t in self.board.tiles if t.id == bm.MORE for m in t.members if m.id == ident), None)
        if tile is None:return
        self.focus_on(ident);self.focused.emit(tile.obj)


def _call(fn, kernel, focus, ident):
    """relevance.why / pin / turn_down, whichever of the two plain signatures it has."""
    try:return fn(kernel, focus, ident)
    except TypeError:
        try:return fn(kernel, ident)
        except Exception:  # noqa: BLE001
            return None
    except Exception:  # noqa: BLE001
        return None


def _wrap(text, fm, width, limit):
    words = str(text or '').split();lines = [];line = ''
    for word in words:
        trial = (line + ' ' + word).strip()
        if fm.horizontalAdvance(trial) <= width or not line:line = trial
        else:
            lines.append(line);line = word
            if len(lines) == limit:break
    if line and len(lines) < limit:lines.append(line)
    if len(lines) == limit and ' '.join(lines) != ' '.join(words):
        lines[-1] = fm.elidedText(lines[-1] + ' …', Qt.ElideRight, width)
    return [fm.elidedText(l, Qt.ElideRight, width) for l in lines]


# ---- the page: the board and the whole desk (the Field) in one place ----------------------------------------------------------
def board_of(page):
    return getattr(page, 'board', None) if page is not None else None


def attach(page):
    """Put the board in the Field's page (field_page.FieldPage calls this once): the page shows the board or the Field, and
    one reading of the desk serves both."""
    if board_of(page) is not None:return page.board
    board = BoardView(page);page.board = board;page.mode = 'map'
    page.layout().addWidget(board);board.hide()
    board.whole.connect(lambda: to_map(page, said=True))
    board.left.connect(lambda: _back(page))
    view = page.view
    original_refresh = page.refresh

    def refresh(force=False, reading=None, _original=original_refresh):
        kernel = kernel_of(page.host)
        if reading is None and page.face == 'work' and kernel is not None:
            from .engineering_kernel import operator
            if force:page.unread = set()
            try:reading = bm.read_desk(kernel, operator(), skip=page.unread)
            except Exception:  # noqa: BLE001 - the page reads as it always did, and says what it could not
                reading = None
        _original(force=force, reading=reading)
        if page.face == 'work':
            if reading is not None:board.desk_read(*reading)
            elif getattr(view, 'field', None) is not None:board.desk_read(view.field, None)
    page.refresh = refresh
    original_update = view.update

    def update(*args, _original=original_update):
        # the Field's acts (a page to read, the steps, a what-if, a trace, two revisions) are drawn on the Field: shown there
        if getattr(page, 'mode', '') == 'board' and (view.reading is not None or view.steps or view.would or view.revisions is not None
                                                     or getattr(view, '_route', None) is not None):
            to_map(page)
        return _original(*args)
    view.update = update
    # "Board" on the Field: the board on the Field's selection
    button = QToolButton(view);button.setObjectName('FieldToBoard');button.setText('Board')
    button.setToolTip('The board: the selected sheet in the middle, what is linked to it around it')
    button.setAccessibleName('Board');button.setCursor(Qt.PointingHandCursor);button.setFocusPolicy(Qt.TabFocus)
    button.clicked.connect(lambda: to_board(page, view.field.selected, said=True))
    page.board_button = button
    _style_button(page)
    original_resize = view.resizeEvent

    def resized(event, _original=original_resize):
        _original(event);_place_button(page)
    view.resizeEvent = resized
    _place_button(page)
    return board


def _style_button(page):
    s = page.board.scale()
    page.board_button.setStyleSheet('QToolButton#FieldToBoard {font-family:"%s";font-size:%dpx;color:%s;background:%s;border:1px solid %s;'
                                    'padding:3px 12px;border-radius:2px;} QToolButton#FieldToBoard:hover {color:%s;border-color:%s;}' % (
                                        t.MONO, round(12 * s), t.QUIET, t.PANEL, t.LINE_STRONG, t.READY, t.READY))


def _place_button(page):
    button = getattr(page, 'board_button', None)
    if button is None:return
    view = page.view;button.adjustSize()
    try:top = view.head_height() + 10
    except Exception:  # noqa: BLE001
        top = 50
    button.move(max(8, view.width() - button.width() - 22), top);button.raise_()


def _back(page):
    from . import field_page
    field_page.back(page.host)


def _title(page):
    try:page.host.setWindowTitle(('Board' if page.mode == 'board' else 'Field') + ' — Graphite')
    except RuntimeError:
        pass


def to_board(page, ident=None, said=False):
    """The board in front in the page, on this object (or on what it was on). Returns whether the object is in focus."""
    board = board_of(page)
    if board is None:return False
    if page.face != 'work':page.show_face('work')
    view = page.view
    # what the Field was showing over its work (a page to read, the steps, a trace) belongs to the Field: it closes
    view.reading = None;view.steps = ();view.would = {};view.would_said = '';view.revisions = None
    if getattr(view, '_route', None) is not None:
        view._route = None;view._surge_timer.stop()
    page.mode = 'board'
    view.hide();board.show()
    found = board.focus_on(ident or board.ident or view.field.selected)
    board.setFocus(Qt.OtherFocusReason);_title(page)
    if said and board.board.focus is not None:board.focused.emit(board.focus_obj())
    return found


def to_map(page, said=False):
    """The whole desk (the Field) in front, its selection on the board's focus."""
    board = board_of(page)
    if board is None:return
    page.mode = 'map'
    view = page.view;ident = board.ident
    board.close_inspector();board.hide();view.show()
    if ident and view.field.get(ident) is not None and view.field.selected != ident:
        view.field.select(ident);view._describe()
    view._reveal_pending = True
    if said:view.auto_fit = False;view._fitted = True;view.zoom = view.fit()        # zoomed out of the board: the whole desk
    view.setFocus(Qt.OtherFocusReason);_place_button(page);_title(page);view.update()


def as_field(page):
    """The Field asked for by name (F9, Arrange ▸ Field, "field"): the whole desk, as it always was."""
    if getattr(page, 'mode', 'map') == 'board':to_map(page)


def home(page):
    """At launch the centre's home is the board, on the desk's first object (what waits for the owner, else the conclusion)."""
    if page is None or board_of(page) is None or page.face != 'work':return
    to_board(page, page.view.field.selected)


def show_board(host, ident=None):
    """The board in front with this object in focus, from anywhere in the window."""
    from . import field_page
    page = getattr(host, 'field_page', None)
    if not getattr(host, '_field_active', False) or page is None:
        page = field_page.show_field(host)
    return to_board(page, ident)


def state(page):
    """How the board is seen, for the history (living_nav_qt.board_state): which of the two, its size and place."""
    board = board_of(page)
    if board is None:return {}
    return {'mode': getattr(page, 'mode', 'map'), 'bzoom': board.zoom, 'bauto': board.auto, 'bx': board.pan_x, 'by': board.pan_y}


def restore(page, saved):
    """Put the board as it was seen (living_nav_qt.set_board)."""
    board = board_of(page)
    if board is None or not saved or 'mode' not in saved:return
    if saved['mode'] == 'map':
        if page.mode != 'map':to_map(page)
        return
    if page.mode != 'board':to_board(page)
    board.auto = bool(saved.get('bauto', True))
    board.zoom = board.fit() if board.auto else max(ZOOM[0], min(ZOOM[1], float(saved.get('bzoom') or 1.0)))
    board.pan_x = float(saved.get('bx') or 0.0);board.pan_y = float(saved.get('by') or 0.0);board.update()
