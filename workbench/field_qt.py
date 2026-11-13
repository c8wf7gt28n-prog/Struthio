"""The Field, drawn: real work objects as sheets in the dark, with the wires that say what feeds what.

Master specification, sections 70 to 72: "Let me move between an overview of an assignment and close work on an artifact."
The selected sheet is the brightest; what touches it stays near; the rest recedes. Enter opens the real editor for the
selected object; the host brings the Field back with the same selection, still in view. Nothing is edited or run from here.

Presentation follows the BOSS desk: charcoal ground, cream reading ink, amber for the selection and what waits for the
owner, small green marks for what is settled. The surface is static: no timers, no animation.

Reading comes first. A sheet is never squeezed below the size its words need and never narrower than a readable column:
when the sheets do not fit, the surface is larger than the window and scrolls, both ways, and the selected sheet is always
brought into view. Lettering follows the owner's reading size without a ceiling, and the smallest lettering is 14 px at the
default size. A sheet recedes by its ground and its edge, not by fading its words below what can be read. Every state has
its own mark, so colour is never the only signal.

Stacy is staC, and here she says it. staC is Graphite's command language, said "Stacy". In the Illustrated desk her still
After Midnight portrait stands in a rail at the right of the Field, in the dark beside the work, and under her the rail
shows the staC line for the selected sheet: the exact read-only pipeline that reads that object through the Kernel. S puts
that line in the writing strip to read or change; Shift+Enter runs it and the answer appears in the working area. The work
comes first: the rail appears only when the sheets keep their room and it never covers a sheet or a wire. Without the rail
(a narrow window, the ASCII or Clean desk) the same line is in the foot and the same keys work.
"""
from PySide6.QtCore import QPoint, QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QPolygonF, QRadialGradient
from PySide6.QtWidgets import QSizePolicy, QWidget

from . import boss_theme as t
from .field_model import ATTENTION, KIND_TAG, SETTLED, STATE_CURRENT, STATE_HELD, STATE_OPEN, STATE_RECHECK, Field

WORD_INK = (1.0, 0.94, 0.84, 0.78)          # how much of its ink a sheet's lettering keeps at each step from the selection
EDGE_INK = (1.0, 0.8, 0.5, 0.34)            # the sheet's edge and marks recede further: they are not lettering
STATE_WORD = {STATE_CURRENT: 'current', STATE_RECHECK: 'recheck', STATE_OPEN: 'open', STATE_HELD: 'held'}
TITLE_LINES, FACT_LINES = 2, 2
LONGEST = 240                               # a title is cut to this many characters before it is measured: paint time must not follow its length

# Every key of the Field, for the card that ? shows. ('h', heading) or ('k', 'the keys<TAB>what they do').
KEYS = (('h', 'Move'),
        ('k', '← ↑ ↓ →\tfollow the wires from sheet to sheet'),
        ('k', 'Home  End\tthe first sheet, the last sheet'),
        ('k', 'PgUp  PgDn\tscroll the surface'),
        ('k', 'A\tthe next thing that waits for you (Shift+A the one before)'),
        ('k', 'Backspace\tback to the sheet you were on before'),
        ('k', 'W  P  N\tthe faces: the work, every program as a shelf, this computer’s network'),
        ('h', 'Open'),
        ('k', 'Enter\topen the real page for this sheet; Esc there comes back here'),
        ('k', 'R\tread the records again'),
        ('k', 'Esc\tclose what is open here (this card, the steps, a what-if’s marks), then leave the Field'),
        ('h', 'Ask · these only read, nothing is changed'),
        ('k', 'X\tdoubt it: what does not hold, what cannot be told, what holds'),
        ('k', 'T\ttrace it: where it comes from and what rests on it'),
        ('k', 'C\tcheck the whole desk: what waits, and what Stacy doubts'),
        ('k', 'B\tthe brief: the desk written up as one page, from the records'),
        ('k', 'S\tthis sheet’s staC line, into the writing strip'),
        ('k', 'Shift+Enter\trun that line; the answer opens in the working area'),
        ('k', 'what if …\tin the writing strip, with a sheet selected: “what if B4 were 100?” marks everything that would move'),
        ('h', 'Do'),
        ('k', 'D\twhat can be done about this sheet, as numbered steps'),
        ('k', '1 – 9\tchoose a step. A read runs at once; a change is put up in Talk and waits'),
        ('k', 'G\tyour go for the change that waits. Only G approves; a digit never does'),
        ('k', 'F\ton the shelf: this program in its own full window'),
        ('h', 'Also'),
        ('k', 'Menu key\tor right-click: the same things as a cascading menu, on the sheet under the pointer'),
        ('k', 'F9\tthe Field, from anywhere in Graphite'),
        ('k', 'this\tin the writing strip: the selected sheet (this | count, then Ctrl+Enter)'),
        ('k', 'word\tin the writing strip: word NAME = LINE keeps a staC line under a word of your own'))


def ink(colour, alpha=1.0):
    c = QColor(colour);c.setAlphaF(max(0.0, min(1.0, alpha)));return c


class FieldView(QWidget):
    """One Field on one surface. `opened` carries the FieldObject the owner asked to open; `left` asks the host to go back."""
    opened = Signal(object)
    left = Signal()
    selection_changed = Signal(object)
    face_chosen = Signal(str)          # the owner asked for another face of the Field (its name)
    look_again = Signal()              # the owner asked for the records to be read again
    stac_line = Signal(object)         # S: the selected object's staC line goes to the writing strip (nothing runs)
    stac_run = Signal(object)          # Shift+Enter: the selected object's staC line is run; the answer shows in the working area
    do_asked = Signal(object)          # D: what can be done about the selected object (the page answers by setting .steps)
    step_chosen = Signal(object, int)  # a digit while the steps show: take that step
    full_asked = Signal(object)        # F on the shelf: the selected program in its full window
    check_asked = Signal()             # C: check the desk (everything read again, what waits said with its next step)
    go_asked = Signal()                # G: the owner's go for what waits in Talk. Never a digit: digits only choose
    trace_asked = Signal(object)       # T: where the selected object comes from and what rests on it
    doubt_asked = Signal(object)       # X: cross-examine the selected object for what a plausible result may hide
    brief_asked = Signal()             # B: the desk written up as one page, from the records
    reading_closed = Signal()          # the reading sheet was closed by the owner (Esc, or a click beside it)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.field = Field()
        self.texture = True                 # the quiet scan texture behind the sheets; the Clean desk turns it off
        self.faces = ();self.face = ''      # the faces the page offers (name, key letter) and the one showing
        self.art_mode = 'clean'             # the desk's artwork choice: 'illustrated' (the portrait rail), 'ascii' (a mark), 'clean'
        self.art_folder = None              # branding/boss of the program that serves this workspace; the page sets it
        self.problem = ''                   # what could not be read, in words; shown on the surface, never hidden
        self.steps = ()                     # what can be done about the selected sheet, while the owner looks at it: (words, kind) pairs
        self._now = 0.0                     # the time of this painting, for "changed lately"
        self.go = ''                        # what G would run now, in words, while something waits in Talk for the owner's go
        self.would = {}                     # a what-if followed along the wires: {object id: the few words of what it would say}
        self.would_said = ''                # the what-if itself, in words, for as long as its marks show
        self._trail = [];self._last = ''    # the sheets the owner was on before this one, for Backspace
        self.reading = None                 # a page to read, shown over the work: {'title', 'lines': [(style, text)], 'foot', 'code'}
        self._read_at = 0.0;self._read_room = 0.0      # how far it is scrolled, and how far it can be
        self._plate = None;self._plate_drawn = (None, None)
        self._face_boxes = []
        self.scroll_x = 0.0;self.scroll_y = 0.0
        self._placed = {};self._surface = (0.0, 0.0);self._gap = 34.0;self._labels = [];self._reveal_pending = False
        self.setFocusPolicy(Qt.StrongFocus)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setAccessibleName('Field: the work in this workspace and what feeds what')
        self.setObjectName('GraphiteField')

    # ---- content ---------------------------------------------------------------------------------------------------
    def set_field(self, field):
        """A new reading of the records. The selection is kept when its object is still there, and so is the place: the
        selected sheet is brought into view at the next layout (when the Field opens, when the owner comes back)."""
        keep = self.field.selected if self.field else ''
        self.field = field or Field()
        kept = bool(keep and self.field.get(keep))
        if kept:self.field.select(keep)
        else:self.scroll_x = self.scroll_y = 0.0
        self.would = {};self.would_said = ''      # a what-if is about the records as they were read: a new reading ends it
        self.reading = None                       # and so is a page shown over them
        self._reveal_pending = True
        self._describe();self.update()

    def selected(self):
        return self.field.get(self.field.selected)

    def _describe(self):
        obj = self.selected();self.steps = ();self.go = ''      # the steps and the go belong to the sheet they were asked for: another sheet, or a new reading, closes them
        now = self.field.selected
        if self._last and now and now != self._last and (not self._trail or self._trail[-1] != self._last):
            self._trail.append(self._last);del self._trail[:-40]       # where the owner was: Backspace goes back along it
        if now:self._last = now
        if obj is None:
            self.setAccessibleDescription(self.problem or 'Nothing is here yet.')
        else:
            feeds = [self.field.get(l.target).title for l in self.field.feeds(obj.id)]
            fed = [self.field.get(l.source).title for l in self.field.fed_by(obj.id)]
            said = '%s: %s' % ((obj.tag or KIND_TAG.get(obj.kind, obj.kind)).capitalize(), str(obj.title).rstrip('. '))
            if not said.endswith(('?', '!')):said += '.'
            if obj.state:said += ' State: %s.' % STATE_WORD.get(obj.state, obj.state)
            if fed:said += ' %s %s.' % (self.field.verbs[0].capitalize(), ', '.join(fed))
            if feeds:said += ' %s %s.' % (self.field.verbs[1].capitalize(), ', '.join(feeds))
            self.setAccessibleDescription(said)
        self.selection_changed.emit(obj)

    # ---- measures --------------------------------------------------------------------------------------------------
    def scale(self):
        """The owner's reading size: the interface font over the default 16 px, with no ceiling (28 pt reads at 200%)."""
        return max(0.85, min(3.5, self.fontInfo().pixelSize() / 16.0))

    def mono(self, px, weight=QFont.Normal):
        f = QFont('IBM Plex Mono');f.setStyleHint(QFont.Monospace);f.setPixelSize(max(11, round(px * self.scale())));f.setWeight(weight);return f

    def sans(self, px, weight=QFont.Medium):
        f = QFont('IBM Plex Sans');f.setPixelSize(max(12, round(px * self.scale())));f.setWeight(weight);return f

    def head_height(self):
        return round(min(58 * self.scale(), max(44.0, self.height() * 0.16)))

    def foot_height(self):
        """Three lines for the selected sheet, or one when the window is too short for a whole sheet above them: at a large
        reading size on a small screen the sheets come first and the foot keeps only the title."""
        s = self.scale();full = round(96 * s)
        if self.height() - self.head_height() - full < self.sheet_height() + 40 * s:return round(44 * s)
        return full

    def least_width(self):
        """The narrowest a sheet may be. A little narrower in the Illustrated desk, so that Stacy keeps her rail beside five columns."""
        if self.field.compact:return 152 * self.scale()
        return (164 if self.art_mode == 'illustrated' and self.art_folder is not None else 176) * self.scale()

    def rail(self):
        """The width of Stacy's rail at the right of the Field: only in the Illustrated desk, only when the plate is there, and
        only when the sheets keep their room. The work comes first; on a narrow screen the rail gives way entirely."""
        if self.art_mode != 'illustrated' or self.art_folder is None:return 0.0
        s = self.scale()
        if self.height() < 520 * s:return 0.0
        if self._plate is None:
            from .boss_qt import midnight_plate
            self._plate = midnight_plate(self.art_folder, 'portrait')
        if self._plate.isNull():return 0.0
        # The columns are counted first, at their narrowest; she takes what they leave, and nothing when that is too little.
        columns = len(self.field.ranks())
        needed = columns * self.least_width() + max(0, columns - 1) * 22 * s + 2 * 16 * s if columns else 0.0
        room = self.width() - needed
        if room < 200 * s:return 0.0
        return float(int(min(340 * s, self.width() * 0.25, room)))

    def body(self):
        return QRectF(0, self.head_height(), self.width() - self.rail(), max(1, self.height() - self.head_height() - self.foot_height()))

    def sheet_height(self):
        """What one sheet needs for its words at this reading size: the kind line, the title, the facts and the identity line."""
        s = self.scale()
        tag = QFontMetricsF(self.mono(12, QFont.Medium)).height();title = QFontMetricsF(self.sans(15)).height()
        fact = QFontMetricsF(self.mono(12.5)).height();where = QFontMetricsF(self.mono(12)).height()
        if self.field.compact:return 2 * 12 * s + tag + 6 * s + TITLE_LINES * title        # a shelf: the name and the state; the foot says the rest
        return 2 * 12 * s + tag + 6 * s + TITLE_LINES * title + 4 * s + FACT_LINES * fact + where + 4 * s

    def _layout(self):
        body = self.body();s = self.scale()
        self._placed, wide, tall = self.field.place(body.width(), body.height(), s, self.sheet_height(), self.least_width())
        self._surface = (wide, tall)
        lefts = sorted({round(place.x, 1) for place in self._placed.values()})
        widths = [place.w for place in self._placed.values()]
        self._gap = (lefts[1] - lefts[0] - widths[0]) if len(lefts) > 1 else 34.0
        if self._reveal_pending:
            self._reveal_pending = False;self._reveal(body)
        self.scroll_x = max(0.0, min(self.scroll_x, max(0.0, wide - body.width())))
        self.scroll_y = max(0.0, min(self.scroll_y, max(0.0, tall - body.height())))
        return body

    def sheet_rect(self, ident, body=None):
        body = body or self.body();p = self._placed.get(ident)
        return None if p is None else QRectF(body.left() + p.x - self.scroll_x, body.top() + p.y - self.scroll_y, p.w, p.h)

    def selected_point(self):
        """Where the keyboard's menu opens: just inside the selected sheet, or the middle of the Field when nothing is selected."""
        body = self._layout()
        if self.field.selected not in self._placed:return self.rect().center()
        self._reveal(body);self._layout();self.update()       # the sheet is brought into view first: the menu is for it, wherever it was
        seen = self.sheet_rect(self.field.selected, body).intersected(body)
        if seen.isEmpty():return self.rect().center()
        return seen.topLeft().toPoint() + QPoint(round(min(24.0, seen.width() / 2)), round(min(24.0, seen.height() / 2)))

    def _reveal(self, body=None):
        """Bring the selected sheet into view, both ways, with a little room around it."""
        body = body or self.body();p = self._placed.get(self.field.selected);s = self.scale();room = 14 * s
        if p is None:return
        # Under the sheet: clear of the strip that says where the surface goes on. Above it: what room is left, a little when there is some.
        high = body.height();strip = 26 * s
        low = strip if high >= p.h + strip else max(0.0, min(room, high - p.h))
        top = max(0.0, min(room, high - p.h - low))
        if p.y - top < self.scroll_y:self.scroll_y = max(0.0, p.y - top - min(26 * s, max(0.0, high - p.h - top - low)))
        elif p.y + p.h + low > self.scroll_y + high:self.scroll_y = p.y + p.h + low - high
        if p.x - room < self.scroll_x:self.scroll_x = max(0.0, p.x - room)
        elif p.x + p.w + room > self.scroll_x + body.width():self.scroll_x = p.x + p.w + room - body.width()

    def resizeEvent(self, event):
        self._reveal_pending = True
        super().resizeEvent(event)

    # ---- a page to read, over the work -----------------------------------------------------------------------------
    def show_reading(self, title, lines, foot='', code='', light=False):
        """Show writing over the work, to be read: a title, lines of ('h' heading | 'p' paragraph | 'q' quiet | 'b' bullet |
        'k' a key and its words, tab between), a foot that says the keys, and the staC line that reads it. The arrow keys
        scroll it; Esc closes it. The sheets stay as they were underneath. A light page (an answer about one sheet) also
        steps aside at any key that is not a reading key, and that key then does what it always does."""
        self.reading = {'title': str(title), 'lines': tuple(lines), 'foot': str(foot), 'code': str(code), 'light': bool(light)}
        self._read_at = 0.0
        self.setAccessibleDescription(str(title) + '. ' + ' '.join(str(text).replace('\t', ': ') for _, text in lines)[:4000])
        self.update()

    def close_reading(self):
        if self.reading is not None:
            self.reading = None;self._describe_quietly();self.update()

    def _describe_quietly(self):
        steps, go = self.steps, self.go;self._describe();self.steps, self.go = steps, go      # the description follows the sheet again; what waits is not withdrawn

    def show_keys(self):
        self.show_reading('The keys of the Field', KEYS, 'Esc  close      ↑ ↓  read on      ?  close')

    def _reading_key(self, event):
        """The keys while a page is being read. A page (the brief, the keys) takes reading keys only, so a letter meant for
        it cannot act on a sheet. A light page scrolls when it has more to show, and otherwise steps aside: False is
        returned and the key does what it always does."""
        key = event.key();step = 3 * QFontMetricsF(self.sans(15)).height();light = self.reading.get('light');more = self._read_room > 1
        if key == Qt.Key_Escape or (event.text() == '?' and not light):
            self.steps = ();self.go = '';self.close_reading();self.reading_closed.emit()
        elif key == Qt.Key_G and self.go:self.go_asked.emit()
        elif key in (Qt.Key_Down, Qt.Key_Up) and (more or not light):self._read_at += step if key == Qt.Key_Down else -step
        elif key in (Qt.Key_PageDown, Qt.Key_PageUp, Qt.Key_Space) and (more or not light):self._read_at += self._reading_rect(self.body()).height() * 0.7 * (-1 if key == Qt.Key_PageUp else 1)
        elif key == Qt.Key_Home and (more or not light):self._read_at = 0.0
        elif key == Qt.Key_End and (more or not light):self._read_at = self._read_room
        elif light:
            self.close_reading();return False
        self._read_at = max(0.0, min(self._read_room, self._read_at));self.update()
        return True

    # ---- input -----------------------------------------------------------------------------------------------------
    def keyPressEvent(self, event):
        key = event.key();before = self.field.selected;plain = not (event.modifiers() & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier))
        if self.reading is not None and plain and self._reading_key(event):
            return
        if plain and event.text() == '?':     # ?: every key of the Field, on a card
            self.show_keys();return
        moves = {Qt.Key_Left: 'left', Qt.Key_Right: 'right', Qt.Key_Up: 'up', Qt.Key_Down: 'down'}
        if key in moves:self.field.move(moves[key])
        elif key == Qt.Key_Home:self.field.select(self.field.first())
        elif key == Qt.Key_End:self.field.select(self.field.last())
        elif key in (Qt.Key_PageDown, Qt.Key_PageUp):
            body = self._layout();step = body.height() * 0.85 * (1 if key == Qt.Key_PageDown else -1)
            self.scroll_y = max(0.0, min(max(0.0, self._surface[1] - body.height()), self.scroll_y + step));self.update();return
        elif key == Qt.Key_A and plain:      # A: the next thing that waits for the owner; Shift+A the one before. Tab leaves, as everywhere.
            self.field.next_attention(backwards=bool(event.modifiers() & Qt.ShiftModifier))
        elif key in (Qt.Key_Return, Qt.Key_Enter):
            obj = self.selected()
            if obj is not None and event.modifiers() & Qt.ShiftModifier:
                if obj.stac:self.stac_run.emit(obj)
            elif obj is not None:self.opened.emit(obj)
            return
        elif key == Qt.Key_S and plain:
            if self.selected() is not None and self.selected().stac:self.stac_line.emit(self.selected())
            return
        elif key == Qt.Key_Escape:
            if self.steps or self.go:        # the first Esc closes the steps and withdraws the go from the keyboard; the next one leaves
                self.steps = ();self.go = '';self.update();return
            if self.would:                   # then a what-if's marks are cleared: the desk shows what is, again
                self.would = {};self.would_said = '';self.update();return
            self.left.emit();return
        elif key == Qt.Key_Backspace and plain:      # back to the sheet the owner was on before this one, and the one before that
            at = next((n for n in range(len(self._trail) - 1, -1, -1) if self._trail[n] != self.field.selected and self.field.get(self._trail[n]) is not None), None)
            if at is None:return                  # nothing on this face to go back to; what was visited on another face is kept for when it shows again
            ident = self._trail[at];del self._trail[at:]
            self._last = '';self.field.select(ident)      # going back is not a step forward: it leaves no trail of its own
        elif key == Qt.Key_B and plain:      # B: the brief
            self.brief_asked.emit();return
        elif key == Qt.Key_D and plain:      # D: what can be done about this. The page asks the records and fills .steps
            if self.selected() is not None:self.do_asked.emit(self.selected())
            return
        elif plain and self.steps and Qt.Key_1 <= key <= Qt.Key_9:
            if key - Qt.Key_1 < len(self.steps):self.step_chosen.emit(self.selected(), key - Qt.Key_1)
            return
        elif key == Qt.Key_X and plain:      # X: doubt it
            if self.selected() is not None:self.doubt_asked.emit(self.selected())
            return
        elif key == Qt.Key_T and plain:      # T: trace
            if self.selected() is not None:self.trace_asked.emit(self.selected())
            return
        elif key == Qt.Key_G and plain:      # G: go. Only while something waits in Talk and says so here
            if self.go:self.go_asked.emit()
            return
        elif key == Qt.Key_C and plain:      # C: check the desk
            self.check_asked.emit();return
        elif key == Qt.Key_F and plain:      # F on the shelf: this program in its full window
            if self.selected() is not None and self.selected().kind == 'app':self.full_asked.emit(self.selected())
            return
        elif key == Qt.Key_R and plain:
            self.look_again.emit();return
        elif plain and any(event.text().lower() == letter for _, letter in self.faces):
            self.face_chosen.emit(next(name for name, letter in self.faces if event.text().lower() == letter));return
        else:
            return super().keyPressEvent(event)
        self._layout();self._reveal();self.update()        # a selecting key always brings the sheet into view, changed or not
        if self.field.selected != before:self._describe()

    def _hit(self, pos):
        body = self._layout()
        if not body.contains(pos):return None
        depth = self.field.depth()
        for ident in sorted(self._placed, key=lambda i: depth.get(i, 3)):       # the nearest sheet wins where two overlap
            if self.sheet_rect(ident, body).contains(pos):return ident
        return None

    def mousePressEvent(self, event):
        self.setFocus(Qt.MouseFocusReason)
        if self.reading is not None:          # a click beside the page closes it; a click on it is for reading
            if not self._reading_rect(self.body()).contains(event.position()):
                self.steps = ();self.go = '';self.close_reading();self.reading_closed.emit()
            return
        for box, name in self._face_boxes:
            if box.contains(event.position()):
                self.face_chosen.emit(name);return
        ident = self._hit(event.position())
        if ident and ident != self.field.selected:
            self.field.select(ident);self._describe();self.update()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        ident = self._hit(event.position())
        if ident:
            self.field.select(ident);self._describe();self.update();self.opened.emit(self.selected())

    def wheelEvent(self, event):
        if self.reading is not None:
            self._read_at = max(0.0, min(self._read_room, self._read_at - event.angleDelta().y() / 2.0));self.update();return
        body = self._layout();room_x = max(0.0, self._surface[0] - body.width());room_y = max(0.0, self._surface[1] - body.height())
        dx = event.angleDelta().x();dy = event.angleDelta().y()
        if event.modifiers() & Qt.ShiftModifier or (room_y <= 0 and not dx):dx, dy = dy or dx, 0     # Shift, or nothing to scroll down: sideways
        if (not room_x or not dx) and (not room_y or not dy):return super().wheelEvent(event)
        self.scroll_x = max(0.0, min(room_x, self.scroll_x - dx / 2.0));self.scroll_y = max(0.0, min(room_y, self.scroll_y - dy / 2.0));self.update()

    # ---- drawing ---------------------------------------------------------------------------------------------------
    def paintEvent(self, event):
        p = QPainter(self)
        try:                                 # a drawing error is contained: the painter is always ended, the window stays
            p.setRenderHint(QPainter.Antialiasing);p.setRenderHint(QPainter.TextAntialiasing)
            import time
            self._now = time.time()
            p.fillRect(self.rect(), QColor(t.TERMINAL_GROUND))
            body = self._layout()
            if self.texture:self._texture(p, body)
            self._art(p, body)
            self._stac(p, body)
            self._head(p)
            if not self.field.objects:
                self._empty(p, body)
            else:
                p.save();p.setClipRect(body)
                depth = self.field.depth()
                self._columns(p, body)
                seen = body.adjusted(-40, -40, 40, 40)
                order = [i for i in sorted(self._placed, key=lambda i: -depth.get(i, 3)) if self.sheet_rect(i, body).intersects(seen)]
                for ident in order:self._ghosts(p, self.sheet_rect(ident, body), depth.get(ident, 3))
                self._labels = []
                self._wires(p, body, depth, seen)
                for ident in order:self._sheet(p, self.field.get(ident), self.sheet_rect(ident, body), depth.get(ident, 3))
                self._wire_words(p)
                p.restore()
                self._more(p, body)
            self._foot(p)
            if self.reading is not None:self._reading(p, body)
        except Exception as exc:  # noqa: BLE001 - say it on the surface instead of taking the program down
            p.setClipping(False);p.setPen(QColor(t.AMBER_TEXT));p.setFont(self.mono(12))
            p.drawText(QRectF(28, self.head_height() + 12, self.width() - 56, 40), Qt.AlignLeft | Qt.AlignVCenter, 'The Field could not be drawn: %s' % str(exc)[:160])
        finally:
            p.end()

    def _tight(self, body):
        """A large reading size on a small screen: the page gives up its margins and its staC line so the writing keeps room."""
        s = self.scale()
        return body.width() < 700 * s or self.height() - body.top() < 520 * s

    def _reading_rect(self, body):
        s = self.scale();edge = (6 if self._tight(body) else 20) * s;top = (6 if self._tight(body) else 14) * s
        wide = min(body.width() - 2 * edge, 940 * s)
        return QRectF(body.left() + (body.width() - wide) / 2, body.top() + top, wide, self.height() - body.top() - 2 * top)

    @staticmethod
    def _flow(text, fm, width):
        """Whole words on as many lines as they need; a word wider than the line is cut where it stops fitting."""
        out = [];line = ''
        for word in str(text).split():
            while fm.horizontalAdvance(word) > width and len(word) > 2:
                low, high = 1, len(word) - 1
                while low < high:
                    mid = (low + high + 1) // 2
                    if fm.horizontalAdvance(word[:mid]) <= width:low = mid
                    else:high = mid - 1
                if line:out.append(line);line = ''
                out.append(word[:low]);word = word[low:]
            trial = (line + ' ' + word).strip()
            if not line or fm.horizontalAdvance(trial) <= width:line = trial
            else:
                out.append(line);line = word
        if line:out.append(line)
        return out or ['']

    def _reading(self, p, body):
        """A page to read, over the work: the brief, the keys. Opaque ground, an amber edge, type at the owner's reading size;
        what does not fit scrolls, and the foot says the keys that act here."""
        s = self.scale();r = self._reading_rect(body);tight = self._tight(body);pad = (14 if tight else 26) * s;read = self.reading
        whole = QRectF(body.left(), body.top(), body.width(), self.height() - body.top())      # the work and its foot: the page's own foot says the keys now
        p.save()
        p.fillRect(QRectF(0, self.height() - self.foot_height(), self.width(), self.foot_height()), ink(t.GROUND, 0.86))      # the foot's keys do not act while the page is read
        p.setClipRect(whole)
        p.fillRect(whole, ink(t.TERMINAL_GROUND, 0.72))        # the work recedes while the page is read
        p.setPen(QPen(ink(t.AMBER_EDGE, 0.9), 1.4));p.setBrush(QColor(t.GROUND));p.drawRect(r)
        title_font = self.sans(17 if tight else 19);fm_title = QFontMetricsF(title_font);y = r.top() + pad + fm_title.ascent()
        p.setFont(title_font);p.setPen(QColor(t.TEXT))
        heading = self._flow(read['title'], fm_title, r.width() - 2 * pad)       # a long name takes a second line before it is cut
        if len(heading) > 2:heading = [heading[0], fm_title.elidedText(' '.join(heading[1:]), Qt.ElideRight, r.width() - 2 * pad)]
        for index, line in enumerate(heading):
            if index:y += fm_title.height()
            p.drawText(QPointF(r.left() + pad, y), line)
        top = y + fm_title.descent() + (8 if tight else 12) * s
        p.setPen(QPen(QColor(t.LINE_STRONG), 1));p.drawLine(QPointF(r.left() + pad, top), QPointF(r.right() - pad, top))
        code = '' if tight else read['code']      # when room is short the line that read it gives way to the writing; S still has it for a sheet
        fm_foot = QFontMetricsF(self.mono(12));foot_h = (fm_foot.height() + 10 * s) * (2 if code else 1) + 8 * s
        inner = QRectF(r.left() + pad, top + 10 * s, r.width() - 2 * pad, r.bottom() - foot_h - pad / 2 - top - 10 * s)
        text_font = self.sans(15);fm_text = QFontMetricsF(text_font);head_font = self.mono(12.5, QFont.Medium);fm_head = QFontMetricsF(head_font)
        quiet_font = self.sans(14);fm_quiet = QFontMetricsF(quiet_font);key_font = self.mono(13, QFont.Medium);fm_key = QFontMetricsF(key_font)
        key_w = min(inner.width() * 0.32, max([fm_key.horizontalAdvance(text.split('\t', 1)[0]) for style, text in read['lines'] if style == 'k'] or [0.0]) + 22 * s)
        rows = [];at = 0.0                     # (y from the top of the writing, x, font, colour, text)
        for style, text in read['lines']:
            if style == 'h':
                at += (16 * s if rows else 2 * s)
                rows.append((at + fm_head.ascent(), 0.0, head_font, t.AMBER_TEXT, str(text).upper()));at += fm_head.height() + 6 * s
            elif style == 'k':
                keys, _, words = str(text).partition('\t');lines = self._flow(words, fm_text, inner.width() - key_w)
                rows.append((at + fm_text.ascent(), 0.0, key_font, t.AMBER_TEXT, keys))
                for line in lines:
                    rows.append((at + fm_text.ascent(), key_w, text_font, t.TEXT, line));at += fm_text.height()
                at += 5 * s
            else:
                font, fm, colour = (quiet_font, fm_quiet, t.QUIET) if style == 'q' else (text_font, fm_text, t.TEXT)
                hang = fm.horizontalAdvance('·  ') if style == 'b' else 0.0
                for index, line in enumerate(self._flow(text, fm, inner.width() - hang)):
                    if style == 'b' and index == 0:rows.append((at + fm.ascent(), 0.0, font, t.AMBER_EDGE, '·'))
                    rows.append((at + fm.ascent(), hang, font, colour, line));at += fm.height()
                at += 7 * s
        self._read_room = max(0.0, at - inner.height());self._read_at = max(0.0, min(self._read_room, self._read_at))
        p.setClipRect(inner.adjusted(0, -2, 0, 2))
        for y_at, x, font, colour, text in rows:
            y_seen = inner.top() + y_at - self._read_at
            if y_seen < inner.top() - 30 * s or y_seen > inner.bottom() + 30 * s:continue
            p.setFont(font);p.setPen(QColor(colour));p.drawText(QPointF(inner.left() + x, y_seen), text)
        p.setClipRect(whole)
        base = r.bottom() - pad / 2 - fm_foot.descent();p.setFont(self.mono(12))
        more = ('↑ more   ' if self._read_at > 1 else '') + ('more ↓' if self._read_room - self._read_at > 1 else '')
        if more:
            p.setPen(QColor(t.AMBER_TEXT));p.drawText(QPointF(r.right() - pad - fm_foot.horizontalAdvance(more), base), more)
        p.setPen(QColor(t.QUIET));p.drawText(QPointF(r.left() + pad, base), fm_foot.elidedText(read['foot'], Qt.ElideRight, r.width() - 2 * pad - fm_foot.horizontalAdvance(more) - 16 * s))
        if code:
            p.setPen(QColor(t.FAINT));p.drawText(QPointF(r.left() + pad, base - fm_foot.height() - 6 * s), fm_foot.elidedText('staC  ' + code, Qt.ElideRight, r.width() - 2 * pad))
        p.restore()

    def _art(self, p, body):
        """The desk's artwork in its own place. Illustrated: the still portrait in the rail, veiled and fading into the ground at
        its inner edge so she sits in the dark beside the work. ASCII: a small character mark in the corner. Clean: nothing."""
        w = self.rail();s = self.scale()
        if w:
            r = QRectF(self.width() - w, body.top(), w, body.height());size = (round(r.width()), round(r.height()))
            if self._plate_drawn[0] != size:        # drawn once for a size, not on every repaint
                from .boss_qt import draw_plate
                pix = QPixmap(QSize(*size));pix.fill(QColor(t.TERMINAL_GROUND));q = QPainter(pix)
                draw_plate(q, QRectF(0, 0, size[0], size[1]), self._plate, 0.0)
                q.fillRect(pix.rect(), ink('#000000', 0.16))
                edge = QLinearGradient(0, 0, size[0] * 0.34, 0);edge.setColorAt(0.0, QColor(t.TERMINAL_GROUND));edge.setColorAt(1.0, ink(t.TERMINAL_GROUND, 0.0))
                q.fillRect(pix.rect(), edge)
                foot = QLinearGradient(0, size[1] * 0.86, 0, size[1]);foot.setColorAt(0.0, ink(t.TERMINAL_GROUND, 0.0));foot.setColorAt(1.0, ink(t.TERMINAL_GROUND, 0.85))
                q.fillRect(pix.rect(), foot);q.end()
                self._plate_drawn = (size, pix)
            p.drawPixmap(r.topLeft(), self._plate_drawn[1])
        elif self.art_mode == 'ascii' and body.width() > 760 * s and body.height() > 420 * s:
            from .boss_qt import BRACKET
            p.setFont(self.mono(12));fm = QFontMetricsF(p.font());p.setPen(ink(t.FAINT, 0.55))
            wide = max(fm.horizontalAdvance(line) for line in BRACKET);x = body.right() - wide - 22 * s;y = body.bottom() - len(BRACKET) * fm.height() - 26 * s
            for line in BRACKET:
                y += fm.height();p.drawText(QPointF(x, y), line)

    @staticmethod
    def stac_lines(code):
        """A staC line as it is shown: one stage to a line, long record numbers shortened for the eye (the line itself stays exact)."""
        import re
        out = []
        for index, stage in enumerate(part.strip() for part in str(code).split(' | ')):
            stage = re.sub(r'([0-9a-f]{6})[0-9a-f]{20,}', '\\1…', stage)
            out.append(stage if index == 0 else '| ' + stage)
        return out

    def _stac(self, p, body):
        """Stacy's rail speaks staC: under her portrait, the pipeline that reads the selected sheet, and the two keys for it."""
        w = self.rail();obj = self.selected()
        if not w or obj is None:return
        if self.steps or self.go:return self._do(p, body, w)
        if not obj.stac:return
        s = self.scale()
        p.setFont(self.mono(12));fm = QFontMetricsF(p.font());head = QFontMetricsF(self.mono(12, QFont.Medium))
        pad = 12 * s;inner_w = w - 2 * 10 * s - 2 * pad
        lines = []
        for stage in self.stac_lines(obj.stac):      # a stage wider than the rail goes on at a comma or a space, indented: nothing of the code is cut
            while fm.horizontalAdvance(stage) > inner_w and len(lines) < 7:
                fits = max((n for n in range(8, len(stage)) if stage[n - 1] in ', ' and fm.horizontalAdvance(stage[:n]) <= inner_w), default=0)
                if not fits:break
                lines.append(stage[:fits].rstrip());stage = '    ' + stage[fits:].lstrip()
            lines.append(stage)
        lines = lines[:8]
        tall = pad * 2 + head.height() + 4 * s + len(lines) * fm.height() + 6 * s + head.height()
        if tall > body.height() - 24 * s:return           # no room for the code under her: the foot and the keys still carry it
        box = QRectF(self.width() - w + 10 * s, body.bottom() - tall - 12 * s, w - 20 * s, tall)
        p.setPen(QPen(ink(t.LINE_STRONG, 0.7), 1));p.setBrush(ink(t.TERMINAL_GROUND, 0.9));p.drawRect(box)
        x = box.left() + pad;y = box.top() + pad + head.ascent()
        p.setFont(self.mono(12, QFont.Medium));p.setPen(QColor(t.AMBER_TEXT));p.drawText(QPointF(x, y), 'staC')
        said = 'says how this is read';said_w = head.horizontalAdvance(said)
        if inner_w > head.horizontalAdvance('staC') + said_w + 12 * s:
            p.setPen(QColor(t.QUIET));p.setFont(self.mono(12));p.drawText(QPointF(box.right() - pad - said_w, y), said)
        y += 4 * s + head.descent()
        p.setFont(self.mono(12))
        for line in lines:
            y += fm.height();p.setPen(QColor(t.QUIET if line.startswith(('|', ' ')) else t.TEXT))
            p.drawText(QPointF(x, y - fm.descent()), fm.elidedText(line, Qt.ElideRight, inner_w))
        y += 6 * s + head.ascent()
        p.setFont(self.mono(12));p.setPen(QColor(t.QUIET))
        p.drawText(QPointF(x, y), QFontMetricsF(p.font()).elidedText('S  line  ·  Shift+Enter  run', Qt.ElideRight, inner_w))

    def _do(self, p, body, w):
        """The same place in Stacy's rail, when the owner asked what can be done (D): the steps the records offer for the selected
        sheet, numbered. A step that changes something says it asks first."""
        s = self.scale();p.setFont(self.mono(12));fm = QFontMetricsF(p.font());head = QFontMetricsF(self.mono(12, QFont.Medium))
        pad = 12 * s;inner_w = w - 2 * 10 * s - 2 * pad;asks = 'asks';asks_w = fm.horizontalAdvance(asks) + 8 * s
        rows = []
        for n, (words, kind) in enumerate(self.steps[:9]):
            write = kind == 'write';room = inner_w - (asks_w if write else 0)
            for at, line in enumerate(self._wrap('%d  %s' % (n + 1, words), fm, room, 2)):
                rows.append((line if at == 0 else '   ' + line, write and at == 0))
        going = self._wrap('G  ' + self.go, fm, inner_w, 3) if self.go else []
        tall = pad * 2 + head.height() + 4 * s + (len(rows) + len(going)) * fm.height() + (4 * s if rows and going else 0) + 6 * s + head.height()
        if tall > body.height() - 24 * s:return           # no room under her: the foot still says them
        box = QRectF(self.width() - w + 10 * s, body.bottom() - tall - 12 * s, w - 20 * s, tall)
        p.setPen(QPen(ink(t.AMBER_EDGE, 0.8), 1));p.setBrush(ink(t.TERMINAL_GROUND, 0.92));p.drawRect(box)
        x = box.left() + pad;y = box.top() + pad + head.ascent()
        p.setFont(self.mono(12, QFont.Medium));p.setPen(QColor(t.AMBER_TEXT));p.drawText(QPointF(x, y), 'DO')
        said = 'what can be done';said_w = head.horizontalAdvance(said)
        if inner_w > head.horizontalAdvance('DO') + said_w + 12 * s:
            p.setPen(QColor(t.QUIET));p.setFont(self.mono(12));p.drawText(QPointF(box.right() - pad - said_w, y), said)
        y += 4 * s + head.descent();p.setFont(self.mono(12))
        for line, write in rows:
            y += fm.height();p.setPen(QColor(t.TEXT));p.drawText(QPointF(x, y - fm.descent()), fm.elidedText(line, Qt.ElideRight, inner_w - (asks_w if write else 0)))
            if write:
                p.setPen(QColor(t.AMBER_TEXT));p.drawText(QPointF(box.right() - pad - fm.horizontalAdvance(asks), y - fm.descent()), asks)
        if going:                            # what waits in Talk for the owner's go, and the key that gives it
            if rows:y += 4 * s
            p.setPen(QColor(t.AMBER_TEXT))
            for at, line in enumerate(going):
                y += fm.height();p.drawText(QPointF(x, y - fm.descent()), fm.elidedText(line if at == 0 else '   ' + line, Qt.ElideRight, inner_w))
        y += 6 * s + head.ascent();p.setPen(QColor(t.QUIET))
        keys = [('1-%d  take' % min(9, len(self.steps)) if len(self.steps) > 1 else '1  take')] if self.steps else []
        if self.go:keys.append('G  go')
        p.drawText(QPointF(x, y), fm.elidedText('  ·  '.join(keys + ['Esc  close']), Qt.ElideRight, inner_w))

    def _texture(self, p, body):
        """A still scan texture and a darker rim: depth without movement."""
        p.save();p.setClipRect(body);p.setPen(Qt.NoPen)
        line = ink('#ffffff', 0.016);step = 3
        y = int(body.top())
        while y < body.bottom():
            p.fillRect(QRectF(body.left(), y, body.width(), 1), line);y += step
        rim = QRadialGradient(body.center(), max(body.width(), body.height()) * 0.72)      # a darker rim: depth that does not move
        rim.setColorAt(0.0, ink('#000000', 0.0));rim.setColorAt(0.6, ink('#000000', 0.0));rim.setColorAt(1.0, ink('#000000', 0.6))
        p.fillRect(body, rim)
        p.restore()

    def _head(self, p):
        s = self.scale();h = self.head_height();x = 28 * s
        p.setPen(QPen(QColor(t.LINE), 1));p.drawLine(QPointF(0, h - 0.5), QPointF(self.width(), h - 0.5))
        p.setFont(self.mono(13, QFont.Medium));p.setPen(QColor(t.AMBER_EDGE))
        label = 'FIELD';fm = QFontMetricsF(p.font());base = h / 2 + fm.ascent() / 2 - 2
        p.drawText(QPointF(x, base), label);x += fm.horizontalAdvance(label) + 14 * s
        self._face_boxes = []
        for name, letter in self.faces:      # the faces of the Field: the one showing is underlined, each says its key
            word = name.upper();w = fm.horizontalAdvance(word);on = name == self.face
            p.setPen(QColor(t.AMBER_TEXT if on else t.QUIET));p.drawText(QPointF(x, base), word)
            if on:p.setPen(QPen(QColor(t.AMBER_EDGE), 2));p.drawLine(QPointF(x, base + 6 * s), QPointF(x + w, base + 6 * s))
            self._face_boxes.append((QRectF(x - 4 * s, 0, w + 8 * s, h), name));x += w + 16 * s
        if self.faces:x += 4 * s
        p.setFont(self.sans(17));fm2 = QFontMetricsF(p.font());p.setPen(QColor(t.TEXT))
        said = self.field.title or 'This workspace';parts = self.field.census()
        p.setFont(self.mono(12.5));fm3 = QFontMetricsF(p.font());room = self.width() - x - 28 * s
        waiting = [part for part in parts if 'recheck' in part or 'open question' in part]
        while parts and fm3.horizontalAdvance('  ·  '.join(parts)) + 24 * s + fm2.horizontalAdvance(said) > room:
            parts = waiting if parts != waiting and waiting else []        # the title keeps its room; the counts give way, what waits last
            waiting = []
        census = '  ·  '.join(parts);census_w = fm3.horizontalAdvance(census)
        p.setFont(self.sans(17))
        p.drawText(QPointF(x, h / 2 + fm2.ascent() / 2 - 2), fm2.elidedText(said, Qt.ElideRight, max(60.0, room - (census_w + 24 * s if census else 0))))
        if census:
            p.setFont(self.mono(12.5));p.setPen(QColor(t.QUIET))
            p.drawText(QPointF(self.width() - 28 * s - census_w, base), census)

    def _columns(self, p, body):
        s = self.scale();p.setFont(self.mono(12, QFont.Medium));fm = QFontMetricsF(p.font())
        for rank in self.field.ranks():
            ids = self.field.column(rank)
            if not ids or ids[0] not in self._placed:continue
            first = self._placed[ids[0]]
            x = body.left() + first.x - self.scroll_x;y = body.top() + 24 * s - self.scroll_y
            p.setPen(ink(t.QUIET, 0.95))
            p.drawText(QPointF(x, y), self.field.rank_title(rank))
            p.setPen(QPen(ink(t.LINE, 0.9), 1))
            start = x + fm.horizontalAdvance(self.field.rank_title(rank)) + 10 * s
            if start < x + first.w:p.drawLine(QPointF(start, y - fm.ascent() / 2 + 1), QPointF(x + first.w, y - fm.ascent() / 2 + 1))

    def _wires(self, p, body, depth, seen):
        s = self.scale()
        for link in self.field.links:
            a = self.sheet_rect(link.source, body);b = self.sheet_rect(link.target, body)
            if a is None or b is None or not a.united(b).intersects(seen):continue
            near = min(depth.get(link.source, 3), depth.get(link.target, 3))
            touching = self.field.selected in (link.source, link.target)
            # A wire that asks for a recheck is always at full strength: it must be findable without selecting one of its ends.
            strength = 1.0 if touching or link.stale else (0.5 if near <= 1 else 0.3)
            start = QPointF(a.right(), a.center().y());end = QPointF(b.left(), b.center().y())
            if end.x() < start.x():      # a wire that would run backwards leaves from the left and arrives at the right
                start = QPointF(a.left(), a.center().y());end = QPointF(b.right(), b.center().y())
            reach = max(24.0 * s, abs(end.x() - start.x()) * 0.5) * (1 if end.x() >= start.x() else -1)
            path = QPainterPath(start);path.cubicTo(QPointF(start.x() + reach, start.y()), QPointF(end.x() - reach, end.y()), end)
            colour = t.AMBER_EDGE if link.stale else (t.TEXT if touching else t.TEAL_EDGE)
            pen = QPen(ink(colour, strength * (0.95 if link.stale or touching else 0.8)), 1.8 if touching or link.stale else 1.0)
            if link.stale:pen.setStyle(Qt.CustomDashLine);pen.setDashPattern([5, 4])
            p.setBrush(Qt.NoBrush);p.setPen(pen);p.drawPath(path)
            p.setPen(Qt.NoPen);p.setBrush(ink(colour, strength))
            for point in (start, end):p.drawEllipse(point, 2.6 * s, 2.6 * s)
            word = 'recheck' if link.stale and not link.label else link.label
            if word and (touching or link.stale) and abs(end.x() - start.x()) > 56 * s:
                # The word sits in the open gap beside the sheet the wire leaves, never under a sheet further along.
                gap = min(abs(end.x() - start.x()), max(34.0 * s, self._gap)) / 2
                want = start.x() + (gap if end.x() >= start.x() else -gap)
                at = min((n / 40.0 for n in range(1, 40)), key=lambda f: abs(path.pointAtPercent(f).x() - want))
                self._labels.append((path.pointAtPercent(at), word, link.stale))

    def _mark(self, p, box, state, colour):
        """One mark per state, different in shape and not only in hue: settled a filled square, recheck half filled, open
        hollow, held crossed, waiting a dot inside, failed a cross, cannot be read or reached a dash."""
        p.save();pen = QPen(colour, 1.5);p.setPen(pen);p.setBrush(Qt.NoBrush)
        if state in SETTLED:
            p.setPen(Qt.NoPen);p.setBrush(colour);p.drawRect(box)
        elif state == STATE_RECHECK:
            p.drawRect(box);p.setPen(Qt.NoPen);p.setBrush(colour);p.drawRect(QRectF(box.left(), box.top(), box.width() / 2, box.height()))
        elif state in (STATE_HELD, 'refuted'):
            p.drawRect(box);p.drawLine(box.topLeft(), box.bottomRight())
        elif state in ('waiting', 'paused'):
            p.drawRect(box);p.setPen(Qt.NoPen);p.setBrush(colour);p.drawEllipse(box.center(), box.width() * 0.18, box.width() * 0.18)
        elif state in ('failed', 'interrupted'):
            p.drawLine(box.topLeft(), box.bottomRight());p.drawLine(box.topRight(), box.bottomLeft())
        elif state == STATE_OPEN:
            p.drawRect(box)
        else:                                # unavailable, not read, down: a dash
            p.drawLine(QPointF(box.left(), box.center().y()), QPointF(box.right(), box.center().y()))
        p.restore()

    def _sheet(self, p, obj, r, depth):
        s = self.scale();depth = min(depth, 3);keep = WORD_INK[depth];edge_keep = EDGE_INK[depth];selected = depth == 0;focus = self.hasFocus()
        p.setBrush(QColor((t.CARD, t.CARD, t.PANEL, t.GROUND)[depth]))       # a sheet recedes by its ground and its edge; its words stay readable
        edge = t.AMBER_EDGE if selected and focus else (t.LINE_STRONG if depth <= 1 else t.LINE)
        p.setPen(QPen(ink(edge, 1.0 if selected else edge_keep + 0.1), 2 if selected else 1));p.drawRect(r)
        if selected:                         # corner ticks: the selection reads without colour too
            p.setPen(QPen(ink(t.AMBER_EDGE if focus else t.LINE_STRONG, 1.0), 2));k = 9 * s;o = 5 * s
            for cx, cy, dx, dy in ((r.left() - o, r.top() - o, 1, 1), (r.right() + o, r.top() - o, -1, 1),
                                   (r.left() - o, r.bottom() + o, 1, -1), (r.right() + o, r.bottom() + o, -1, -1)):
                p.drawLine(QPointF(cx, cy), QPointF(cx + dx * k, cy));p.drawLine(QPointF(cx, cy), QPointF(cx, cy + dy * k))
        if obj.lately(self._now):            # its record changed in the last hours: a small turned corner, the mark of what was just worked on
            fold = 9 * s;p.save();p.setPen(Qt.NoPen);p.setBrush(ink(t.AMBER_EDGE, 0.55 + 0.4 * keep))
            p.drawPolygon(QPolygonF([QPointF(r.right() - fold, r.top()), QPointF(r.right(), r.top()), QPointF(r.right(), r.top() + fold)]));p.restore()
        pad = 12 * s;inner = r.adjusted(pad, pad - 2 * s, -pad, -pad + 2 * s)
        # Kind at the left, state at the right. A narrow sheet keeps its kind and the state's mark; the state's word gives way.
        p.setFont(self.mono(12, QFont.Medium));fm = QFontMetricsF(p.font());y = inner.top() + fm.ascent()
        state = STATE_WORD.get(obj.state, obj.state or '')
        state_colour = t.READY if obj.state in SETTLED else (t.AMBER_EDGE if obj.state in ATTENTION else t.QUIET)
        mark = 8 * s;state_w = (fm.horizontalAdvance(state.upper()) + mark + 6 * s) if state else 0.0
        full = obj.tag or KIND_TAG.get(obj.kind, obj.kind.upper())
        worded = bool(state) and inner.width() >= fm.horizontalAdvance(full) + state_w + 8 * s
        if state and not worded:state_w = mark
        tag = fm.elidedText(full, Qt.ElideRight, max(10.0, inner.width() - state_w - 8 * s))
        p.setPen(ink(t.AMBER_TEXT if obj.kind in ('question', 'condition') else t.QUIET, keep));p.drawText(QPointF(inner.left(), y), tag)
        if state:
            sx = inner.right() - state_w;box = QRectF(sx, y - fm.ascent() / 2 - mark / 2 + 1, mark, mark)
            self._mark(p, box, obj.state, ink(state_colour, max(keep, 0.85) if obj.state in ATTENTION else keep))
            if worded:
                p.setPen(ink(state_colour, max(keep, 0.85) if obj.state in ATTENTION else keep))
                p.drawText(QPointF(sx + mark + 6 * s, y), state.upper())
        y += 6 * s
        # Title: whole words on up to two lines; only a title longer than that is cut, once.
        p.setFont(self.sans(15));fm = QFontMetricsF(p.font());p.setPen(ink(t.TEXT, keep))
        for line in self._wrap(obj.title, fm, inner.width(), TITLE_LINES):
            y += fm.height();p.drawText(QPointF(inner.left(), y - fm.descent()), line)
        # Facts, while they fit above the identity line.
        p.setFont(self.mono(12.5));fm = QFontMetricsF(p.font());fm_where = QFontMetricsF(self.mono(12));where_h = fm_where.height() if obj.where else 0
        y += 4 * s
        would = self.would.get(obj.id)
        facts = () if self.field.compact else (((would,) + tuple(obj.lines[:FACT_LINES - 1])) if would else obj.lines[:FACT_LINES])
        for at, fact in enumerate(facts):
            if y + fm.height() > inner.bottom() - where_h + 1:break
            y += fm.height();p.setPen(ink(t.AMBER_TEXT, 1.0) if would and at == 0 else ink(t.QUIET, keep))
            p.drawText(QPointF(inner.left(), y - fm.descent()), fm.elidedText(str(fact)[:LONGEST], Qt.ElideRight, inner.width()))
        if would:                            # and a broken amber edge: it reads as "would", without colour too
            pen = QPen(ink(t.AMBER_EDGE, 0.95), 1.6);pen.setStyle(Qt.CustomDashLine);pen.setDashPattern([4, 4])
            p.setPen(pen);p.setBrush(Qt.NoBrush);p.drawRect(r.adjusted(-3 * s, -3 * s, 3 * s, 3 * s))
        if obj.where and not self.field.compact and inner.bottom() - fm_where.descent() > y + 2:
            p.setFont(self.mono(12));p.setPen(ink(t.FAINT if depth <= 1 else t.QUIET, keep))
            p.drawText(QPointF(inner.left(), inner.bottom() - fm_where.descent()), fm_where.elidedText(str(obj.where)[:LONGEST], Qt.ElideMiddle, inner.width()))

    def _wire_words(self, p):
        s = self.scale();p.setFont(self.mono(12));fm = QFontMetricsF(p.font())
        for point, word, stale in self._labels:
            w = fm.horizontalAdvance(word) + 10 * s
            if w > self._gap - 6 * s:continue          # no room between the columns: the foot still names the link in words
            box = QRectF(point.x() - w / 2, point.y() - fm.height() / 2 - 1, w, fm.height() + 2)
            p.setPen(Qt.NoPen);p.setBrush(QColor(t.TERMINAL_GROUND));p.drawRect(box)
            p.setPen(QColor(t.AMBER_TEXT if stale else t.QUIET));p.drawText(box, Qt.AlignCenter, word)

    def _ghosts(self, p, r, depth):
        """The sheets behind a sheet: two outlines stepping back into the dark. Drawn before the wires so no wire starts under one."""
        s = self.scale();keep = EDGE_INK[min(depth, 3)];selected = depth == 0
        for step, alpha in ((2, 0.2), (1, 0.36)):
            ghost = r.translated(step * 5 * s, step * 5 * s)
            p.setBrush(ink(t.TERMINAL_GROUND, 1.0));p.setPen(QPen(ink(t.LINE_STRONG if selected else t.LINE, alpha * keep * (1.6 if selected else 1.0)), 1))
            p.drawRect(ghost)

    @staticmethod
    def _wrap(text, fm, width, limit):
        """Whole words on up to `limit` lines. A word wider than the sheet (a file name, a line without spaces) is cut where it
        stops fitting, found by halving, and the text is first cut to LONGEST characters: the cost does not follow its length."""
        text = str(text)[:LONGEST];width = max(8.0, width);out = [];line = '';pieces = []
        for word in text.split():
            while fm.horizontalAdvance(word) > width and len(word) > 2:
                low, high = 1, len(word) - 1
                while low < high:
                    mid = (low + high + 1) // 2
                    if fm.horizontalAdvance(word[:mid]) <= width:low = mid
                    else:high = mid - 1
                pieces.append(word[:low]);word = word[low:]
            pieces.append(word)
        used = 0
        for piece in pieces:
            trial = (line + ' ' + piece).strip()
            if not line or fm.horizontalAdvance(trial) <= width:line = trial;used += 1
            elif len(out) + 1 == limit:break
            else:
                out.append(line);line = piece;used += 1
        if line:out.append(line)
        if used < len(pieces) and out:out[-1] = out[-1] + ' ' + ' '.join(pieces[used:])      # the last line carries the rest, cut once
        return [fm.elidedText(l, Qt.ElideRight, width) for l in out]

    def _more(self, p, body):
        """Where the surface goes on beyond the window, and what the reader left out. Said, never hidden."""
        s = self.scale();p.setFont(self.mono(12));wide, tall = self._surface
        said = []
        if self.scroll_y > 1:said.append('↑ more above')
        if tall - body.height() - self.scroll_y > 1:said.append('more below ↓')
        if self.scroll_x > 1:said.append('← more')
        if wide - body.width() - self.scroll_x > 1:said.append('more →')
        note = ' · '.join(part for part in ((self.would_said + ' · nothing is changed · Esc clears') if self.would_said else '', self.field.note, self.problem) if part)
        if not note and self.field.aside:  # what belongs elsewhere is said quietly, when nothing louder is being said
            said.insert(0, self.field.aside)
        if said or note:                   # on its own strip of ground, so it is read over whatever sheet lies under it
            p.fillRect(QRectF(body.left(), body.bottom() - 24 * s, body.width(), 24 * s), ink(t.TERMINAL_GROUND, 0.9))
        fm = QFontMetricsF(p.font());room = body.width() - 56 * s
        if note:                           # what is being said comes first; where the surface goes on takes what is left, the sideways words giving way first
            note = fm.elidedText(note, Qt.ElideRight, room)
            left = room - fm.horizontalAdvance(note) - 28 * s
            while said and fm.horizontalAdvance('   '.join(said)) > left:said.pop()
            p.setPen(QColor(t.AMBER_TEXT))
            p.drawText(QRectF(body.left() + 28 * s, body.bottom() - 22 * s, room, 18 * s), Qt.AlignLeft | Qt.AlignVCenter, note)
        if said:
            p.setPen(QColor(t.QUIET))
            p.drawText(QRectF(body.left(), body.bottom() - 22 * s, body.width() - 28 * s, 18 * s), Qt.AlignRight | Qt.AlignVCenter, '   '.join(said))

    def _empty(self, p, body):
        s = self.scale();p.setFont(self.mono(13));fm = QFontMetricsF(p.font())
        if self.problem:
            p.setPen(QColor(t.AMBER_TEXT));lines = ('// the records could not be read', '', '   ' + self.problem + '.', '   R looks again.')
        else:
            p.setPen(QColor(t.QUIET));lines = ('// nothing in the field yet', '', '   bring material in through Ingress, or open a file;',
                                               '   what you work on appears here with what it came from.', '', '   ?  shows every key of the Field.')
        y = body.center().y() - len(lines) * fm.height() / 2;x = max(28 * s, body.center().x() - 240 * s)
        for line in lines:
            y += fm.height();p.drawText(QPointF(x, y), line)

    def _foot(self, p):
        s = self.scale();h = self.foot_height();top = self.height() - h;x = 28 * s
        p.fillRect(QRectF(0, top, self.width(), h), QColor(t.GROUND))
        p.setPen(QPen(QColor(t.LINE), 1));p.drawLine(QPointF(0, top + 0.5), QPointF(self.width(), top + 0.5))
        obj = self.selected()
        # The keys, in the order they are read; when the line is too narrow they give way one at a time, the least needed first.
        legend = [(3, '← ↑ ↓ →  move'), (1, 'Enter  open'), (2, 'D  do'), (4, 'X  doubt'), (5, 'C  check all'), (6, 'T  trace'), (6.5, 'B  brief'), (7, 'S  staC'), (9, 'Menu  more'), (8, 'A  next waiting'),
                  (10, 'R  look again'), (12, '⌫  where I was'), (0.5, '?  keys'), (0, 'Esc  back')]
        legend = [(11, '%s  %s' % (letter.upper(), name)) for name, letter in self.faces if name != self.face] + legend
        p.setFont(self.mono(12));fm = QFontMetricsF(p.font())
        if obj is None:
            p.setPen(QColor(t.QUIET));p.drawText(QPointF(x, top + h / 2 + fm.ascent() / 2), 'R  look again      ?  keys      Esc  back');return
        wide = self.width() - 2 * x;compact = h < 60 * s
        p.setFont(self.mono(12, QFont.Medium));p.setPen(QColor(t.AMBER_TEXT))
        tag = obj.tag or KIND_TAG.get(obj.kind, obj.kind.upper())
        if obj.state:tag += '  ·  ' + STATE_WORD.get(obj.state, obj.state).upper()
        if compact:                          # a short window at a large reading size: one line, the kind and the title
            p.drawText(QPointF(x, top + h / 2 + fm.ascent() / 2 - 1), tag)
            p.setFont(self.sans(15));fm2 = QFontMetricsF(p.font());p.setPen(QColor(t.TEXT));left = x + fm.horizontalAdvance(tag) + 18 * s
            p.drawText(QPointF(left, top + h / 2 + fm2.ascent() / 2 - 1), fm2.elidedText(str(obj.title)[:LONGEST], Qt.ElideRight, max(40.0, self.width() - x - left)))
            return
        p.drawText(QPointF(x, top + 24 * s), tag)
        room = wide - fm.horizontalAdvance(tag) - 40 * s
        while legend and fm.horizontalAdvance('      '.join(word for _, word in legend)) > room:
            legend.remove(max(legend))
        if legend:
            keys = '      '.join(word for _, word in legend);keys_w = fm.horizontalAdvance(keys)
            p.setFont(self.mono(12));p.setPen(QColor(t.QUIET));p.drawText(QPointF(self.width() - x - keys_w, top + 24 * s), keys)
        p.setFont(self.sans(16));fm2 = QFontMetricsF(p.font());p.setPen(QColor(t.TEXT))
        p.drawText(QPointF(x, top + 24 * s + fm2.height() + 2 * s), fm2.elidedText(str(obj.title)[:LONGEST], Qt.ElideRight, wide))
        fed = [self.field.get(l.source).title for l in self.field.fed_by(obj.id)];feeds = [self.field.get(l.target).title for l in self.field.feeds(obj.id)]
        said = obj.role or ''
        if fed:said += ('   ·   ' if said else '') + self.field.verbs[0] + ' ' + ', '.join(str(f)[:60] for f in fed[:6])
        if feeds:said += ('   ·   ' if said else '') + self.field.verbs[1] + ' ' + ', '.join(str(f)[:60] for f in feeds[:6])
        if not said:said = obj.where
        p.setFont(self.mono(12.5));fm3 = QFontMetricsF(p.font());p.setPen(QColor(t.QUIET))
        marked = bool(self.would.get(obj.id))
        if marked:                           # a what-if marks this sheet: the foot says it whole, and has the line to itself
            said = 'WHAT IF      ' + self.would_said.replace('what if ', '', 1) + '      ' + self.would[obj.id];p.setPen(QColor(t.AMBER_TEXT))
        code = '' if self.rail() or not obj.stac or marked else 'staC  ' + '  '.join(self.stac_lines(obj.stac))      # no rail: the line is said here
        if self.steps or self.go:            # the owner asked what can be done: the foot says the steps and the go, wherever the rail is
            said = 'DO      ' + '      '.join(['%d  %s%s' % (n + 1, words, ' (asks first)' if kind == 'write' else '') for n, (words, kind) in enumerate(self.steps[:9])]
                                              + (['G  ' + self.go] if self.go else []))
            code = '';p.setPen(QColor(t.AMBER_TEXT))
        code_w = min(fm3.horizontalAdvance(code), wide * 0.5) if code else 0.0
        p.drawText(QPointF(x, top + h - 14 * s), fm3.elidedText(said, Qt.ElideRight, wide - (code_w + 28 * s if code else 0)))
        if code:
            p.setPen(QColor(t.AMBER_TEXT));p.drawText(QPointF(self.width() - x - code_w, top + h - 14 * s), fm3.elidedText(code, Qt.ElideRight, code_w))
