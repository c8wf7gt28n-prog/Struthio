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
from .assistant_identity import named
from PySide6.QtCore import QEasingCurve, QEvent, QPoint, QPointF, QRectF, QSize, Qt, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QKeyEvent, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QPolygonF, QRadialGradient, QRegion
from PySide6.QtWidgets import QSizePolicy, QToolTip, QWidget

from . import boss_theme as t
from . import tool_faces
from .glyph_set import KIND as KIND_GLYPH
from .field_model import ATTENTION, KIND_TAG, SETTLED, STATE_CURRENT, STATE_HELD, STATE_OPEN, STATE_RECHECK, Field

WORD_INK = (1.0, 0.94, 0.84, 0.78)          # how much of its ink a sheet's lettering keeps at each step from the selection
EDGE_INK = (1.0, 0.8, 0.5, 0.34)            # the sheet's edge and marks recede further: they are not lettering
STATE_WORD = {STATE_CURRENT: 'current', STATE_RECHECK: 'recheck', STATE_OPEN: 'open', STATE_HELD: 'held'}


def attention_ink(state):
    """The colour of a state that wants attention: a recheck is RECHECK, anything else that waits is OWNER (both amber in
    Graphite; lavender and raspberry in Kasandra)."""
    return t.RECHECK if state == STATE_RECHECK else t.OWNER
TITLE_LINES, FACT_LINES = 2, 2
LONGEST = 240                               # a title is cut to this many characters before it is measured: paint time must not follow its length

# Every key of the Field, for the card that ? shows. ('h', heading) or ('k', 'the keys<TAB>what they do').
KEYS = (('h', 'Move'),
        ('k', '← ↑ ↓ →\tfollow the wires from sheet to sheet'),
        ('k', 'Home  End\tthe first sheet, the last sheet'),
        ('k', 'PgUp  PgDn\tscroll the surface'),
        ('k', 'Z\tthe whole desk in the window, Z again for its ordinary size; + and − for larger and smaller'),
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
        ('k', named('C\tcheck the whole desk: what waits, and what Stacy doubts')),
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
        ('h', 'With the mouse'),
        ('k', 'click\topen a sheet; the right button shows what can be done with the sheet under it'),
        ('k', 'drag\tthe ground, or the bars at the edges, to move the surface; Ctrl and the wheel for size'),
        ('k', 'every key\tshown on the surface is a place to click, and does what the key does'),
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
    menu_asked = Signal()              # a click on "Menu": the selected sheet's own menu

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
        # The mouse does what the keys do: every key the surface shows is also a place to click. Each painting leaves the
        # places here as (rectangle, key, the text that key types, what it does in words).
        self._hot = []
        self._through = []                  # places on a page for reading whose click first closes the page, then does what the key does
        self._hover = ''                    # the sheet under the pointer: its wires show, and its whole name
        self._press = None                  # where a press began: (position, the sheet there, the scroll then)
        self._mouse = QPointF(-1, -1)       # where the pointer is, so what it is over can answer in its green
        self._shape = None                  # the pointer's shape here, as last set (see _point)
        self._panned = False
        self._grab = None                   # a scroll thumb held by the mouse: ('v' or 'h', where in the thumb it was taken)
        self._bar = ''                      # the scroll thumb under the pointer: 'v', 'h' or ''
        self.setMouseTracking(True)
        self._plate = None;self._plate_drawn = (None, None)
        self._face_boxes = []
        self.scroll_x = 0.0;self.scroll_y = 0.0
        self.zoom = 1.0                     # how large the sheets are drawn: 1 is the owner's reading size; Z fits the whole desk in the window
        self.on_zoom = None                 # told (zoom, whole desk?) when the owner changes how the desk is seen, so it can be kept
        self.still = None                   # asked whether motion is to be reduced (the profile's setting); None: it may move
        self._gliding = None
        self._fitted = False                # Z asked for the whole desk: it stays whole when the window or the desk changes, until the size is set by hand
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
        if self._fitted:self.zoom = self.fit()    # the whole desk was asked for: a new reading is shown whole too
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

    def display(self, px):
        """The face of headings: Plex Mono in Graphite, the typewriter face in Kasandra (boss_theme.DISPLAY)."""
        if t.DISPLAY == 'IBM Plex Mono':return self.mono(px, QFont.Medium)
        f = QFont(t.DISPLAY);f.setPixelSize(max(12, round(px * 1.12 * self.scale())));return f

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
        if t.APPEARANCE == 'kasandra':      # Kasandra's rail: her stills are there, whichever the state of the work asks for
            if self._kasandra('assistant_rail', 'idle') is None:return 0.0
        else:
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

    ZOOM = (0.35, 1.6)                   # the smallest and the largest the sheets are drawn
    GLIDE = 190                          # milliseconds Z takes to draw the desk back or bring it near (glide)
    FAR = 0.6                            # below this no word on a sheet can be read: a sheet is drawn as its glyph and its name (_far)

    def room(self, body=None):
        """The room the sheets have, in their own measure: the body of the Field seen through the zoom. At half size the
        same window holds twice as much each way."""
        body = body or self.body();return body.width() / self.zoom, body.height() / self.zoom

    def set_zoom(self, zoom, about=None, said=True):
        """Draw the sheets larger or smaller. `about` is the point of the window that stays where it is (the pointer, for
        the wheel); without one the selected sheet is kept in view. The head, the foot and a page being read keep the
        owner's reading size: only the surface of sheets is seen from further away."""
        zoom = max(self.ZOOM[0], min(self.ZOOM[1], float(zoom)));self._fitted = False
        if abs(zoom - self.zoom) < 1e-6:return
        body = self.body();was = self.zoom
        if about is not None and body.contains(about):
            x = self.scroll_x + (about.x() - body.left()) / was;y = self.scroll_y + (about.y() - body.top()) / was
            self.zoom = zoom;self.scroll_x = x - (about.x() - body.left()) / zoom;self.scroll_y = y - (about.y() - body.top()) / zoom
            self._layout()
        else:
            self.zoom = zoom;self._layout();self._reveal();self._layout()
        self._rehover();self.update()
        if said:self._zoom_said()

    def glide(self, zoom, whole):
        """Z: the desk draws back to show all of itself, or comes near again, in a short glide and not a cut, so the eye
        keeps its place on it. At once when the profile asks for less motion, or when the Field is not showing."""
        zoom = max(self.ZOOM[0], min(self.ZOOM[1], float(zoom)))
        if self._gliding is not None:
            moving = self._gliding;self._gliding = None;moving.stop()
        calm = False
        try:calm = bool(self.still()) if callable(self.still) else False
        except Exception:  # noqa: BLE001 - how it moves is never worth an error
            calm = True
        if calm or not self.isVisible() or abs(zoom - self.zoom) < 1e-6:
            self.set_zoom(zoom, said=False);self._fitted = whole;self._zoom_said();return
        move = QVariantAnimation(self);move.setDuration(self.GLIDE);move.setEasingCurve(QEasingCurve.OutCubic)
        move.setStartValue(float(self.zoom));move.setEndValue(zoom)
        move.valueChanged.connect(lambda value: self.set_zoom(float(value), said=False) if self._gliding is move else None)

        def arrived():
            if self._gliding is not move:return
            self._gliding = None;self.set_zoom(zoom, said=False);self._fitted = whole;self._zoom_said();self.update()
        move.finished.connect(arrived);self._gliding = move;move.start(QVariantAnimation.DeleteWhenStopped)

    def _zoom_said(self):
        if callable(self.on_zoom):
            try:self.on_zoom(self.zoom, self._fitted)
            except Exception:  # noqa: BLE001 - remembering a size is never worth an error
                pass

    def fit(self):
        """The zoom at which the whole desk is in the window: the largest step at which nothing runs off either way."""
        body = self.body();s = self.scale();high = body.height() - 26 * s      # clear of the strip that says how it is seen
        for step in range(20, int(self.ZOOM[0] * 20) - 1, -1):
            zoom = step / 20.0
            # The desk is placed in the room it will really have. (Until 0.5 it was placed in the whole height and then asked to
            # be shorter than the height less the strip; a desk is never shorter than the room it is placed in, so nothing
            # ever fitted and Z always drew the desk at its smallest, however large the window.)
            _, wide, tall = self.field.place(body.width() / zoom, high / zoom, s, self.sheet_height(), self.least_width())
            if wide <= body.width() / zoom + 0.5 and tall <= high / zoom + 0.5:return zoom
        return self.ZOOM[0]

    def _rehover(self):
        """After the surface moves under a still pointer (a scroll, a zoom, a key that brings a sheet into view), the sheet
        under the pointer is looked up again, so the green answer is never left on a sheet the pointer is no longer over."""
        if self._mouse.x() < 0 or self.reading is not None:return
        bar = self._bar_at(self._mouse);hot = None if bar else self._hot_at(self._mouse);ident = '' if hot or bar else (self._hit(self._mouse) or '')
        if ident != self._hover:self._hover = ident
        self._bar = bar[0] if bar else ''
        self._point(Qt.PointingHandCursor if hot or ident or bar else Qt.ArrowCursor)

    def _layout(self):
        body = self.body();s = self.scale();wide_room, tall_room = self.room(body)
        self._placed, wide, tall = self.field.place(wide_room, tall_room, s, self.sheet_height(), self.least_width())
        self._surface = (wide, tall)
        lefts = sorted({round(place.x, 1) for place in self._placed.values()})
        widths = [place.w for place in self._placed.values()]
        self._gap = (lefts[1] - lefts[0] - widths[0]) if len(lefts) > 1 else 34.0
        if self._reveal_pending:
            self._reveal_pending = False;self._reveal(body)
        self.scroll_x = max(0.0, min(self.scroll_x, max(0.0, wide - wide_room)))
        self.scroll_y = max(0.0, min(self.scroll_y, max(0.0, tall - tall_room)))
        return body

    def sheet_rect(self, ident, body=None):
        """Where a sheet is in the window, as it is seen (through the zoom): what a click, the pointer and a menu go by."""
        body = body or self.body();p = self._placed.get(ident);z = self.zoom
        return None if p is None else QRectF(body.left() + (p.x - self.scroll_x) * z, body.top() + (p.y - self.scroll_y) * z, p.w * z, p.h * z)

    def _drawn_rect(self, ident, body=None):
        """Where a sheet is drawn, in the surface's own measure: the painter is scaled by the zoom about the body's corner
        while the sheets and wires are drawn, so they are placed as if at their ordinary size."""
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
        wide, high = self.room(body);strip = 26 * s / self.zoom
        low = strip if high >= p.h + strip else max(0.0, min(room, high - p.h))
        top = max(0.0, min(room, high - p.h - low))
        if p.y - top < self.scroll_y:self.scroll_y = max(0.0, p.y - top - min(26 * s, max(0.0, high - p.h - top - low)))
        elif p.y + p.h + low > self.scroll_y + high:self.scroll_y = p.y + p.h + low - high
        if p.x - room < self.scroll_x:self.scroll_x = max(0.0, p.x - room)
        elif p.x + p.w + room > self.scroll_x + wide:self.scroll_x = p.x + p.w + room - wide

    def resizeEvent(self, event):
        self._reveal_pending = True
        if self._fitted:self.zoom = self.fit()      # the whole desk was asked for: it stays whole in the new window
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
        self.show_reading('The keys of the Field', KEYS, 'Esc  close')

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
            self._layout();high = self.room()[1];step = high * 0.85 * (1 if key == Qt.Key_PageDown else -1)
            self.scroll_y = max(0.0, min(max(0.0, self._surface[1] - high), self.scroll_y + step));self._rehover();self.update();return
        elif key == Qt.Key_Z and plain:      # Z: the whole desk in the window; again, its ordinary size
            fitted = self.fit();whole = not (abs(self.zoom - fitted) < 1e-6 or (fitted >= 1.0 and self.zoom != 1.0))
            self.glide(fitted if whole else 1.0, whole and fitted < 1.0);return
        elif event.text() in ('+', '=') or key in (Qt.Key_Plus, Qt.Key_Equal):       # larger
            self.set_zoom(round(self.zoom * 20 + 2) / 20.0);return
        elif event.text() in ('-', '−') or key == Qt.Key_Minus:                      # smaller
            self.set_zoom(round(self.zoom * 20 - 2) / 20.0);return
        elif key == Qt.Key_0 and event.modifiers() & Qt.ControlModifier:             # Ctrl+0: the ordinary size
            self.set_zoom(1.0);return
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
        self._layout();self._reveal();self._rehover();self.update()        # a selecting key always brings the sheet into view, changed or not
        if self.field.selected != before:self._describe()

    def _hit(self, pos):
        body = self._layout()
        if not body.contains(pos):return None
        depth = self.field.depth()
        for ident in sorted(self._placed, key=lambda i: depth.get(i, 3)):       # the nearest sheet wins where two overlap
            if self.sheet_rect(ident, body).contains(pos):return ident
        return None

    KEY_OF = {'Enter': (Qt.Key_Return, ''), 'Esc': (Qt.Key_Escape, ''), '⌫': (Qt.Key_Backspace, ''), 'Backspace': (Qt.Key_Backspace, ''), '?': (Qt.Key_Question, '?'),
              'Menu': (Qt.Key_Menu, ''), 'Menu key': (Qt.Key_Menu, ''), 'Shift+Enter': ((Qt.Key_Return, Qt.ShiftModifier), '')}

    def _key_of(self, label):
        """The key a shown label stands for ('D', '1', 'Esc', '?'): (key, the text it types), or None for a label that names no one key."""
        label = str(label).strip()
        if label in self.KEY_OF:return self.KEY_OF[label]
        if len(label) == 1 and label.isdigit() and label != '0':return Qt.Key_0 + int(label), label
        if len(label) == 1 and label.isascii() and label.isalpha():return getattr(Qt, 'Key_' + label.upper()), label.lower()
        return None

    def press_key(self, key, text=''):
        """Do what a key does, for a click: the same event the keyboard sends, so the mouse can never do something else. A
        key held with Shift is (key, Shift). The few places that no key reaches (the − and + beside Z) carry what they do
        themselves."""
        if callable(key):
            key();return
        if key == Qt.Key_Menu:
            self.menu_asked.emit();return
        held = Qt.NoModifier
        if isinstance(key, tuple):key, held = key
        self.keyPressEvent(QKeyEvent(QEvent.KeyPress, key, held, text))

    def _bars(self, body=None):
        """The scroll thumbs, when the surface runs beyond the window: [(which, its track, the thumb)], 'v' down the right
        edge and 'h' along the foot of the sheets. The thumb's length is the share of the surface the window shows."""
        body = body or self.body();s = self.scale();wide, tall = self._surface;room_w, room_h = self.room(body);thick = 6.0 * s;strip = 24.0 * s;out = []
        down = tall - room_h > 1;across = wide - room_w > 1
        if down:
            track = QRectF(body.right() - thick - 3 * s, body.top() + 6 * s, thick, max(40.0, body.height() - strip - 12 * s))
            size = min(track.height(), max(30.0 * s, track.height() * room_h / tall))
            out.append(('v', track, QRectF(track.left(), track.top() + (track.height() - size) * min(1.0, self.scroll_y / (tall - room_h)), thick, size)))
        if across:
            track = QRectF(body.left() + 6 * s, body.bottom() - strip - thick - 3 * s, max(40.0, body.width() - 12 * s - (thick + 6 * s if down else 0)), thick)
            size = min(track.width(), max(30.0 * s, track.width() * room_w / wide))
            out.append(('h', track, QRectF(track.left() + (track.width() - size) * min(1.0, self.scroll_x / (wide - room_w)), track.top(), size, thick)))
        return out

    def _bar_at(self, pos):
        """The scroll bar under a point, with room around it for the hand: (which, its track, the thumb), or None."""
        if self.reading is not None or not self.field.objects:return None
        reach = 5.0 * self.scale()
        return next((bar for bar in self._bars() if bar[1].adjusted(-reach, -reach, reach, reach).contains(pos)), None)

    def _scrollbars(self, p, body):
        """Draw the thumbs: quiet until the pointer is on one or the hand holds it, then the pointer's green."""
        for which, track, thumb in self._bars(body):
            lit = which == self._bar or (self._grab is not None and self._grab[0] == which)
            p.fillRect(track, ink(t.LINE, 0.35))
            p.fillRect(thumb, ink(t.READY, 0.9) if lit else QColor(t.LINE_MID))      # found, not shining; the pointer's green when it is on it

    def _hot_at(self, pos):
        return next(((box, key, text, words) for box, key, text, words in reversed(self._hot) if box.contains(pos)), None)

    def _keys_line(self, p, x, base, items, colour, room, target=''):
        """Draw 'KEY  what it does' items along one line, each a place to click that does what its key does. An item whose key
        is G is the owner's go, so it is drawn as an Approve button and says what it would apply, and to what. Items that do
        not fit are left out from the end. Returns the x after the last one drawn.

        0.5.2 (the owner: "We don't need to display keyboard shortcuts anywhere ... keep it sleek and tidy"): what is drawn
        is the words alone, as a button. The key still does what it did, and is still what the item is found by; an item
        that only told of a key and could not be clicked is not drawn at all."""
        s = self.scale();fm = QFontMetricsF(p.font());gap = fm.horizontalAdvance('      ');end = x + room
        for item in items:
            label, _, words = str(item).partition('  ');words = words.strip();found = self._key_of(label)
            if label.strip() == 'G':
                wide = fm.horizontalAdvance('Approve') + 16 * s;said = fm.elidedText(words, Qt.ElideRight, max(40.0, end - x - wide - 8 * s))
                total = wide + 8 * s + fm.horizontalAdvance(said)
                if x + wide > end:break
                box = QRectF(x, base - fm.ascent() - 3 * s, wide, fm.height() + 6 * s)
                over = QRectF(x, box.top(), total, box.height()).contains(self._mouse)      # the same place a click lands on
                self._halo(p, box, t.READY if over else t.OWNER, 1.8 if over else 2.0)      # it waits for the owner (amber; raspberry in Kasandra); under the pointer: green
                p.save();p.setPen(Qt.NoPen);p.setBrush(QColor(t.OWNER));p.drawRect(box)
                p.setPen(QColor(t.GROUND));p.drawText(box, Qt.AlignCenter, 'Approve');p.restore()
                p.setPen(QColor(colour));p.drawText(QPointF(x + wide + 8 * s, base), said)
                self._hot.append((QRectF(x, box.top(), total, box.height()), Qt.Key_G, 'g',
                                  'Approve: %s%s. Nothing is changed until you do' % (words, (' · for “%s”' % str(target)[:80]) if target else '')))
            else:
                if found is None or not words:continue          # it only named a key: not shown
                said = words[:1].upper() + words[1:];total = fm.horizontalAdvance(said)
                if x + total > end:break
                spot = QRectF(x - 4 * s, base - fm.ascent() - 4 * s, total + 8 * s, fm.height() + 8 * s)
                over = found is not None and spot.contains(self._mouse)
                if found is not None:        # a key that can be clicked is a button, and looks like one: a dark plate with a quiet edge, green under the pointer
                    box = spot.adjusted(-2 * s, 0.5, 2 * s, -0.5)
                    p.save();p.setPen(QPen(QColor(t.TEAL_EDGE if over else t.LINE), 1));p.setBrush(QColor(t.TEAL_SOFT if over else t.RAISED));p.drawRect(box);p.restore()
                p.setPen(QColor(t.TEAL_TEXT if over else colour));p.drawText(QPointF(x, base), said)
                if found is not None:
                    self._hot.append((spot, found[0], found[1], said))
            x += total + gap
        return x

    def mousePressEvent(self, event):
        """A click on something the surface shows as a key does what that key does. A click on a sheet opens it (on release,
        so that a drag can move the surface instead); the right button selects the sheet for its menu and opens nothing."""
        self.setFocus(Qt.MouseFocusReason);pos = event.position()
        if event.button() == Qt.LeftButton:
            hot = self._hot_at(pos)
            if hot is not None:
                if any(hot[0] is box for box in self._through):self.close_reading()      # a row of the key card: the card steps aside, then the key acts
                self.press_key(hot[1], hot[2]);return
        if self.reading is not None:          # a click beside the page closes it; a click on it is for reading
            if not self._reading_rect(self.body()).contains(pos):
                self.steps = ();self.go = '';self.close_reading();self.reading_closed.emit()
            return
        for box, name in self._face_boxes:
            if box.contains(pos):
                self.face_chosen.emit(name);return
        bar = self._bar_at(pos) if event.button() == Qt.LeftButton else None
        if bar is not None:                   # a scroll bar: its thumb is taken hold of; a click on its track moves a window's worth that way
            which, track, thumb = bar
            if thumb.adjusted(-5, -5, 5, 5).contains(pos):
                self._grab = (which, (pos.y() - thumb.top()) if which == 'v' else (pos.x() - thumb.left()));self.update()
            elif which == 'v':self.press_key(Qt.Key_PageUp if pos.y() < thumb.top() else Qt.Key_PageDown)
            else:                              # the track of the bar along the foot: a window's width that way
                self._layout();wide = self.room()[0];way = -1 if pos.x() < thumb.left() else 1
                self.scroll_x = max(0.0, min(max(0.0, self._surface[0] - wide), self.scroll_x + way * wide * 0.85));self._rehover();self.update()
            return
        ident = self._hit(pos)
        if event.button() == Qt.LeftButton:
            self._press = (QPointF(pos), ident, (self.scroll_x, self.scroll_y));self._panned = False
            return
        if ident and ident != self.field.selected:
            self.field.select(ident);self._describe();self.update()
        super().mousePressEvent(event)

    def _point(self, shape):
        """The pointer's shape over this surface, set only when it changes: the hand moves many times a second, and each
        change is drawn in the desk's green by workbench/pointer.py."""
        if shape != self._shape:
            self._shape = shape;self.setCursor(shape)

    def mouseMoveEvent(self, event):
        pos = event.position()
        if self._grab is not None and event.buttons() & Qt.LeftButton:       # a thumb in the hand: the surface follows it
            which, held = self._grab;bar = next((b for b in self._bars() if b[0] == which), None)
            if bar is not None:
                _, track, thumb = bar;wide, high = self.room()
                if which == 'v':
                    span = max(1.0, track.height() - thumb.height());self.scroll_y = max(0.0, min(1.0, (pos.y() - held - track.top()) / span)) * max(0.0, self._surface[1] - high)
                else:
                    span = max(1.0, track.width() - thumb.width());self.scroll_x = max(0.0, min(1.0, (pos.x() - held - track.left()) / span)) * max(0.0, self._surface[0] - wide)
                self._mouse = QPointF(pos);self.update()
            return
        if self._grab is not None:            # the button came up somewhere this surface did not see: the thumb is let go
            self._grab = None;self.update()
        if self._press is not None and event.buttons() & Qt.LeftButton:      # a drag moves the surface
            start, _, (x, y) = self._press;delta = pos - start
            if self._panned or abs(delta.x()) + abs(delta.y()) > 6:
                self._panned = True;self._layout();wide, high = self.room()
                self.scroll_x = max(0.0, min(max(0.0, self._surface[0] - wide), x - delta.x() / self.zoom))
                self.scroll_y = max(0.0, min(max(0.0, self._surface[1] - high), y - delta.y() / self.zoom))
                self._point(Qt.ClosedHandCursor);self._mouse = QPointF(pos);self.update()
            return
        bar = self._bar_at(pos);hot = None if bar else self._hot_at(pos)
        ident = '' if hot or bar or self.reading is not None else (self._hit(pos) or '')
        self._point(Qt.PointingHandCursor if hot or ident or bar else Qt.ArrowCursor)
        over = self._hot_at(self._mouse);was = QPointF(self._mouse);self._mouse = QPointF(pos);which = bar[0] if bar else ''
        if ident != self._hover or which != self._bar or (hot is None) != (over is None) or (hot is not None and over is not None and hot[0] != over[0]):
            self._hover = ident;self._bar = which;self.update()
        elif self.texture and self.reading is None:      # the pointer's light moved: only the two places it was and is are drawn again
            self.update(QRegion(self._lit(was)).united(QRegion(self._lit(self._mouse))))
        obj = self.field.get(ident) if ident else None
        tip = hot[3] if hot else ('%s%s\nClick opens it · right-click for what can be done' % (obj.title, (' · ' + STATE_WORD.get(obj.state, obj.state)) if obj.state else '')) if obj is not None else ''
        if tip:QToolTip.showText(event.globalPosition().toPoint(), tip, self)
        else:QToolTip.hideText()

    def mouseReleaseEvent(self, event):
        if self._grab is not None and event.button() == Qt.LeftButton:
            self._grab = None;self._rehover();self.update();return
        press, self._press = self._press, None
        if press is None or event.button() != Qt.LeftButton:return super().mouseReleaseEvent(event)
        if self._panned:
            self._panned = False;self._point(Qt.ArrowCursor);return
        ident = press[1]
        if ident and self._hit(event.position()) == ident:      # a click on a sheet: it is the selected one, and it opens
            if ident != self.field.selected:
                self.field.select(ident);self._describe()
            self.update();lift = self._guard_second_click(event.timestamp());self.opened.emit(self.selected());lift()

    def _guard_second_click(self, stamp=0):
        """A sheet opens on one click. A hand that double-clicks to open would land its second click on whatever the newly
        opened page puts under the pointer, and press it. So the second click of that double-click is dropped: any press
        of the left button in this window that was made within a double-click's time of the opening click, however late
        it is delivered (opening a page can take longer than that, and the second click waits in the queue meanwhile). A
        click made later than that is a new intention and goes through. The keyboard is not touched and nothing is delayed.
        Returns what to call when the page has been opened: it lets the guard go a moment after."""
        import time
        from PySide6.QtCore import QObject, QTimer
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance();window = self.window()
        if app is None or getattr(self, '_guard', None) is not None:return lambda: None
        within = max(150, min(600, app.doubleClickInterval()));began = time.monotonic()

        class Guard(QObject):
            def eventFilter(guard, watched, event):
                try:
                    if event.type() in (QEvent.MouseButtonPress, QEvent.MouseButtonDblClick, QEvent.MouseButtonRelease) and event.button() == Qt.LeftButton \
                            and isinstance(watched, QWidget) and watched.window() is window:
                        made = event.timestamp()
                        return not (stamp and made and made - stamp > within)      # made after the double-click's time: a new click
                except Exception:  # noqa: BLE001 - a guard never breaks an event
                    pass
                return False

        self._guard = Guard(self);app.installEventFilter(self._guard)

        def gone():
            guard, self._guard = self._guard, None
            if guard is not None:
                app.removeEventFilter(guard);guard.deleteLater()

        def lift():        # the page is open: what was clicked meanwhile is in the queue and is seen before this fires
            QTimer.singleShot(max(180, within - int((time.monotonic() - began) * 1000)), gone)
        return lift

    def leaveEvent(self, event):
        self._mouse = QPointF(-1, -1)
        if self._hover or self._hot or self.texture or self._bar:
            self._hover = '';self._bar = '';self.update()
        super().leaveEvent(event)

    def wheelEvent(self, event):
        if self.reading is not None:
            self._read_at = max(0.0, min(self._read_room, self._read_at - event.angleDelta().y() / 2.0));self.update();return
        if event.modifiers() & Qt.ControlModifier:       # Ctrl and the wheel: larger or smaller, about the pointer
            turn = event.angleDelta().y() or event.angleDelta().x()
            if turn:self.set_zoom(round(self.zoom * 20 + (1 if turn > 0 else -1)) / 20.0, event.position())
            return
        self._layout();wide, high = self.room();room_x = max(0.0, self._surface[0] - wide);room_y = max(0.0, self._surface[1] - high)
        dx = event.angleDelta().x();dy = event.angleDelta().y()
        if event.modifiers() & Qt.ShiftModifier or (room_y <= 0 and not dx):dx, dy = dy or dx, 0     # Shift, or nothing to scroll down: sideways
        if (not room_x or not dx) and (not room_y or not dy):return super().wheelEvent(event)
        self.scroll_x = max(0.0, min(room_x, self.scroll_x - dx / 2.0 / self.zoom));self.scroll_y = max(0.0, min(room_y, self.scroll_y - dy / 2.0 / self.zoom))
        self._rehover();self.update()

    # ---- drawing ---------------------------------------------------------------------------------------------------
    def paintEvent(self, event):
        p = QPainter(self)
        try:                                 # a drawing error is contained: the painter is always ended, the window stays
            p.setRenderHint(QPainter.Antialiasing);p.setRenderHint(QPainter.TextAntialiasing)
            import time
            self._now = time.time();self._hot = []
            p.fillRect(self.rect(), QColor(t.TERMINAL_GROUND))
            body = self._layout()
            if self.texture:self._texture(p, body)
            self._light(p, body)
            self._art(p, body)
            self._stac(p, body)
            self._head(p)
            if not self.field.objects:
                self._empty(p, body)
            else:
                p.save();p.setClipRect(body)
                if self.zoom != 1.0:         # the surface is seen from nearer or further: scaled about the body's corner
                    p.translate(body.topLeft());p.scale(self.zoom, self.zoom);p.translate(-body.topLeft())
                depth = self.field.depth()
                self._columns(p, body)
                wide, high = self.room(body);seen = QRectF(body.left() - 40, body.top() - 40, wide + 80, high + 80)
                order = [i for i in sorted(self._placed, key=lambda i: -depth.get(i, 3)) if self._drawn_rect(i, body).intersects(seen)]
                for ident in order:self._ghosts(p, self._drawn_rect(ident, body), depth.get(ident, 3))
                self._labels = []
                self._wires(p, body, depth, seen)
                for ident in order:self._sheet(p, self.field.get(ident), self._drawn_rect(ident, body), depth.get(ident, 3))
                self._wire_words(p)
                p.restore()
                self._more(p, body)
                self._scrollbars(p, body)
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
        self._hot = [];self._through = []     # while a page is read, only its own controls are places to click
        whole = QRectF(body.left(), body.top(), body.width(), self.height() - body.top())      # the work and its foot: the page's own foot says the keys now
        p.save()
        p.fillRect(QRectF(0, self.height() - self.foot_height(), self.width(), self.foot_height()), ink(t.GROUND, 0.86))      # the foot's keys do not act while the page is read
        p.setClipRect(whole)
        p.fillRect(whole, ink(t.TERMINAL_GROUND, 0.72))        # the work recedes while the page is read
        if self.hasFocus():self._halo(p, r, t.AMBER_EDGE, 1.3)       # the page has the keyboard now
        p.setPen(QPen(ink(t.AMBER_EDGE, 0.9), 1.4));p.setBrush(QColor(t.GROUND));p.drawRect(r)
        title_font = self.sans(17 if tight else 19);fm_title = QFontMetricsF(title_font);y = r.top() + pad + fm_title.ascent()
        close_font = self.mono(12);fm_close = QFontMetricsF(close_font);close = '✕  Close';close_w = fm_close.horizontalAdvance(close)
        p.setFont(close_font);p.setPen(QColor(t.QUIET));p.drawText(QPointF(r.right() - pad - close_w, y), close)
        self._hot.append((QRectF(r.right() - pad - close_w - 8 * s, y - fm_close.ascent() - 6 * s, close_w + 16 * s, fm_close.height() + 12 * s), Qt.Key_Escape, '', 'Close this page (Esc)'))
        p.setFont(title_font);p.setPen(QColor(t.TEXT))
        heading = self._flow(read['title'], fm_title, r.width() - 2 * pad - close_w - 16 * s)       # a long name takes a second line before it is cut
        if len(heading) > 2:heading = [heading[0], fm_title.elidedText(' '.join(heading[1:]), Qt.ElideRight, r.width() - 2 * pad - close_w - 16 * s)]
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
        spots = []                             # a key and its words are a place to click: (top, bottom, the key's label, its words)
        calm = False                           # under a heading that says something holds (or that nothing waits), the marks are green
        for style, text in read['lines']:
            if style == 'h':
                calm = str(text).strip().lower().startswith(('holds', 'nothing'))
                at += (16 * s if rows else 2 * s)
                rows.append((at + fm_head.ascent(), 0.0, head_font, t.READY if calm else t.AMBER_TEXT, str(text).upper()));at += fm_head.height() + 6 * s
            elif style == 'k':
                keys, _, words = str(text).partition('\t');lines = self._flow(words, fm_text, inner.width() - key_w);began = at
                rows.append((at + fm_text.ascent(), 0.0, key_font, t.AMBER_TEXT, keys))
                for line in lines:
                    rows.append((at + fm_text.ascent(), key_w, text_font, t.TEXT, line));at += fm_text.height()
                spots.append((began, at, keys, words));at += 5 * s
            else:
                font, fm, colour = (quiet_font, fm_quiet, t.QUIET) if style == 'q' else (text_font, fm_text, t.TEXT)
                hang = fm.horizontalAdvance('·  ') if style == 'b' else 0.0
                for index, line in enumerate(self._flow(text, fm, inner.width() - hang)):
                    if style == 'b' and index == 0:rows.append((at + fm.ascent(), 0.0, font, t.READY if calm else t.AMBER_EDGE, '·'))
                    rows.append((at + fm.ascent(), hang, font, colour, line));at += fm.height()
                at += 7 * s
        self._read_room = max(0.0, at - inner.height());self._read_at = max(0.0, min(self._read_room, self._read_at))
        p.setClipRect(inner.adjusted(0, -2, 0, 2))
        for y_at, x, font, colour, text in rows:
            y_seen = inner.top() + y_at - self._read_at
            if y_seen < inner.top() - 30 * s or y_seen > inner.bottom() + 30 * s:continue
            p.setFont(font);p.setPen(QColor(colour));p.drawText(QPointF(inner.left() + x, y_seen), text)
        for began, ended, keys, words in spots:      # each key's row does what the key does; on a page for reading, the page closes first
            found = self._key_of(keys);top_seen = inner.top() + began - self._read_at;bottom_seen = inner.top() + ended - self._read_at
            if found is None or bottom_seen < inner.top() + 4 or top_seen > inner.bottom() - 4:continue
            box = QRectF(inner.left() - 6 * s, max(inner.top(), top_seen), inner.width() + 12 * s, min(inner.bottom(), bottom_seen) - max(inner.top(), top_seen))
            self._hot.append((box, found[0], found[1], words[:1].upper() + words[1:]))
            if not read.get('light'):self._through.append(box)
        p.setClipRect(whole)
        base = r.bottom() - pad / 2 - fm_foot.descent();p.setFont(self.mono(12))
        more = ('↑ more   ' if self._read_at > 1 else '') + ('more ↓' if self._read_room - self._read_at > 1 else '')
        if more:
            at = r.right() - pad - fm_foot.horizontalAdvance(more)
            for word, key, tip in (('↑ more   ', Qt.Key_PageUp, 'Read back'), ('more ↓', Qt.Key_PageDown, 'Read on')):
                if word not in more:continue
                wide = fm_foot.horizontalAdvance(word);spot = QRectF(at - 4 * s, base - fm_foot.ascent() - 5 * s, fm_foot.horizontalAdvance(word.strip()) + 8 * s, fm_foot.height() + 10 * s)
                p.setPen(QColor(t.READY if spot.contains(self._mouse) else t.AMBER_TEXT));p.drawText(QPointF(at, base), word)
                self._hot.append((spot, key, '', tip));at += wide
        self._keys_line(p, r.left() + pad, base, [item for item in read['foot'].split('      ') if item.strip()], t.QUIET, r.width() - 2 * pad - fm_foot.horizontalAdvance(more) - 16 * s)
        if code:
            p.setPen(QColor(t.TEAL_EDGE));p.drawText(QPointF(r.left() + pad, base - fm_foot.height() - 6 * s), fm_foot.elidedText('staC  ' + code, Qt.ElideRight, r.width() - 2 * pad))
        p.restore()

    def _kasandra(self, slot, state):
        """Kasandra's still for a place of the Field (kasandra_art.choose), or None."""
        host = getattr(self.parentWidget(), 'host', None)
        if host is None:return None
        from . import kasandra_art
        try:return kasandra_art.choose(kasandra_art.folder(host.root), slot, state)
        except Exception:  # noqa: BLE001 - art is never worth an error: the rail gives way
            return None

    def kasandra_state(self):
        host = getattr(self.parentWidget(), 'host', None)
        from .kasandra_art import current_state
        return current_state(host) if host is not None else 'idle'

    def _art(self, p, body):
        """The desk's artwork in its own place. Illustrated: the still portrait in the rail, veiled and fading into the ground at
        its inner edge so she sits in the dark beside the work. ASCII: a small character mark in the corner. Clean: nothing.
        Kasandra: her still for what the work is doing (notes while it runs, a hand by Enter while it waits for you)."""
        w = self.rail();s = self.scale()
        if w:
            r = QRectF(self.width() - w, body.top(), w, body.height());size = (round(r.width()), round(r.height()))
            scene = self._kasandra('assistant_rail', self.kasandra_state()) if t.APPEARANCE == 'kasandra' else None
            key = (size, scene['id'] if scene else None, self.devicePixelRatioF())
            if self._plate_drawn[0] != key:        # drawn once for a size and a still, not on every repaint
                from .boss_qt import draw_plate
                dpr = self.devicePixelRatioF()
                pix = QPixmap(QSize(round(size[0] * dpr), round(size[1] * dpr)));pix.setDevicePixelRatio(dpr);pix.fill(QColor(t.TERMINAL_GROUND));q = QPainter(pix)
                if scene is not None:
                    from . import kasandra_art
                    host = self.parentWidget().host
                    image = kasandra_art.picture(kasandra_art.folder(host.root), scene, size[0], size[1], dpr)
                    if not image.isNull():q.drawImage(QRectF(0, 0, size[0], size[1]), image)
                else:
                    draw_plate(q, QRectF(0, 0, size[0], size[1]), self._plate, 0.0)
                q.fillRect(QRectF(0, 0, size[0], size[1]), ink(t.VEIL, 0.16))
                edge = QLinearGradient(0, 0, size[0] * 0.34, 0);edge.setColorAt(0.0, QColor(t.TERMINAL_GROUND));edge.setColorAt(1.0, ink(t.TERMINAL_GROUND, 0.0))
                q.fillRect(QRectF(0, 0, size[0], size[1]), edge)
                foot = QLinearGradient(0, size[1] * 0.86, 0, size[1]);foot.setColorAt(0.0, ink(t.TERMINAL_GROUND, 0.0));foot.setColorAt(1.0, ink(t.TERMINAL_GROUND, 0.85))
                q.fillRect(QRectF(0, 0, size[0], size[1]), foot);q.end()
                self._plate_drawn = (key, pix)
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
        p.setFont(self.mono(12, QFont.Medium));p.setPen(QColor(t.TEAL_TEXT));p.drawText(QPointF(x, y), 'staC')
        said = 'says how this is read';said_w = head.horizontalAdvance(said)
        if inner_w > head.horizontalAdvance('staC') + said_w + 12 * s:
            p.setPen(QColor(t.QUIET));p.setFont(self.mono(12));p.drawText(QPointF(box.right() - pad - said_w, y), said)
        y += 4 * s + head.descent()
        p.setFont(self.mono(12))
        for line in lines:
            y += fm.height();p.setPen(QColor(t.TEAL_EDGE if line.startswith(('|', ' ')) else t.TEAL_TEXT))      # staC is green wherever it is said
            p.drawText(QPointF(x, y - fm.descent()), fm.elidedText(line, Qt.ElideRight, inner_w))
        y += 6 * s + head.ascent()
        p.setFont(self.mono(12));fm_keys = QFontMetricsF(p.font());at = x;sep = '  ·  ';end = x + inner_w
        keys = (('S', 'Line', 'Put this line in the writing strip; nothing runs'), ('Shift+Enter', 'Run', 'Run this line: a read, nothing is changed'))
        for index, (label, words, tip) in enumerate(keys):
            if end - at < fm_keys.horizontalAdvance(words):break          # no room to say it: the key itself still works
            shown = words;wide = fm_keys.horizontalAdvance(shown)      # 0.5.2: the words alone; the key is not shown
            spot = QRectF(at - 4 * s, y - fm_keys.ascent() - 4 * s, wide + 8 * s, fm_keys.height() + 8 * s);found = self._key_of(label)
            p.setPen(QColor(t.READY if spot.contains(self._mouse) else t.QUIET));p.drawText(QPointF(at, y), shown)
            self._hot.append((spot, found[0], found[1], tip));at += wide
            if index + 1 < len(keys) and end - at - fm_keys.horizontalAdvance(sep) >= fm_keys.horizontalAdvance(keys[index + 1][1]):
                p.setPen(QColor(t.FAINT));p.drawText(QPointF(at, y), sep);at += fm_keys.horizontalAdvance(sep)      # a dot only between two keys that are both there
            else:break

    def _do(self, p, body, w):
        """The same place in Stacy's rail, when the owner asked what can be done (D): the steps the records offer for the selected
        sheet, numbered. A step that changes something says it asks first."""
        s = self.scale();p.setFont(self.mono(12));fm = QFontMetricsF(p.font());head = QFontMetricsF(self.mono(12, QFont.Medium))
        pad = 12 * s;inner_w = w - 2 * 10 * s - 2 * pad;asks = 'asks';asks_w = fm.horizontalAdvance(asks) + 8 * s
        rows = []
        for n, (words, kind) in enumerate(self.steps[:9]):
            write = kind == 'write';room = inner_w - (asks_w if write else 0)
            for at, line in enumerate(self._wrap('%d  %s' % (n + 1, words), fm, room, 2)):
                rows.append((line if at == 0 else '   ' + line, write and at == 0, n))
        going = self._wrap('G  ' + self.go, fm, inner_w, 3) if self.go else []
        tall = pad * 2 + head.height() + 4 * s + (len(rows) + len(going)) * fm.height() + (4 * s if rows and going else 0) + 6 * s + head.height()
        if tall > body.height() - 24 * s:return           # no room under her: the foot still says them
        box = QRectF(self.width() - w + 10 * s, body.bottom() - tall - 12 * s, w - 20 * s, tall)
        if self.go:self._halo(p, box, t.OWNER, 1.0)      # something in it waits for the owner's Approve
        p.setPen(QPen(ink(t.OWNER if self.go else t.AMBER_EDGE, 0.8), 1));p.setBrush(ink(t.TERMINAL_GROUND, 0.92));p.drawRect(box)
        x = box.left() + pad;y = box.top() + pad + head.ascent()
        p.setFont(self.mono(12, QFont.Medium));p.setPen(QColor(t.AMBER_TEXT));p.drawText(QPointF(x, y), 'DO')
        said = 'what can be done';said_w = head.horizontalAdvance(said)
        if inner_w > head.horizontalAdvance('DO') + said_w + 12 * s:
            p.setPen(QColor(t.QUIET));p.setFont(self.mono(12));p.drawText(QPointF(box.right() - pad - said_w, y), said)
        y += 4 * s + head.descent();p.setFont(self.mono(12))
        for line, write, n in rows:
            y += fm.height();p.setPen(QColor(t.TEXT));p.drawText(QPointF(x, y - fm.descent()), fm.elidedText(line, Qt.ElideRight, inner_w - (asks_w if write else 0)))
            self._hot.append((QRectF(x - 4 * s, y - fm.height(), inner_w + 8 * s, fm.height()), Qt.Key_1 + n, str(n + 1),
                              'Take this step: %s' % ('it is put up for you to approve; nothing is changed yet' if self.steps[n][1] == 'write' else
                                                       named('it changes something: Stacy does it at once and shows it, with an Undo where there is one') if self.steps[n][1] == 'does' else 'a read, it runs at once')))
            if write:
                p.setPen(QColor(t.AMBER_TEXT));p.drawText(QPointF(box.right() - pad - fm.horizontalAdvance(asks), y - fm.descent()), asks)
        if going:                            # what waits in Talk for the owner's go, and the key that gives it
            if rows:y += 4 * s
            p.setPen(QColor(t.AMBER_TEXT))
            for at, line in enumerate(going):
                y += fm.height();p.drawText(QPointF(x, y - fm.descent()), fm.elidedText(line if at == 0 else '   ' + line, Qt.ElideRight, inner_w))
                self._hot.append((QRectF(x - 4 * s, y - fm.height(), inner_w + 8 * s, fm.height()), Qt.Key_G, 'g', 'Approve: %s. Nothing is changed until you do' % self.go))
        # (0.5.2: a line of keys stood here, "1-6 take · G go · Esc close". The rows above are clicked; keys are not shown.)

    def _texture(self, p, body):
        """A still scan texture and a darker rim: depth without movement."""
        p.save();p.setClipRect(body);p.setPen(Qt.NoPen)
        line = ink('#ffffff', 0.016);step = 3
        y = int(body.top())
        while y < body.bottom():
            p.fillRect(QRectF(body.left(), y, body.width(), 1), line);y += step
        rim = QRadialGradient(body.center(), max(body.width(), body.height()) * 0.72)      # a darker rim: depth that does not move
        rim.setColorAt(0.0, ink(t.VEIL, 0.0));rim.setColorAt(0.6, ink(t.VEIL, 0.0));rim.setColorAt(1.0, ink(t.VEIL, 0.6))
        p.fillRect(body, rim)
        # The desk's two lights, very low: amber rising from the foot, where what is selected is named and what waits is
        # approved, and green falling from the head, where the live faces are. They do not move and they say nothing; they
        # are the room the sheets are in.
        s = self.scale();reach = min(body.height() * 0.42, 190 * s)
        floor = QLinearGradient(QPointF(0, body.bottom()), QPointF(0, body.bottom() - reach))
        floor.setColorAt(0.0, ink(t.AMBER_EDGE, 0.075));floor.setColorAt(0.45, ink(t.AMBER_EDGE, 0.022));floor.setColorAt(1.0, ink(t.AMBER_EDGE, 0.0))
        p.fillRect(QRectF(body.left(), body.bottom() - reach, body.width(), reach), floor)
        sky = QLinearGradient(QPointF(0, body.top()), QPointF(0, body.top() + reach * 0.7))
        sky.setColorAt(0.0, ink(t.READY, 0.04));sky.setColorAt(1.0, ink(t.READY, 0.0))
        p.fillRect(QRectF(body.left(), body.top(), body.width(), reach * 0.7), sky)
        p.restore()

    LIGHT = 150.0                        # how far the pointer's light reaches on the ground, before the interface scale

    def _lit(self, at):
        """The square of the surface the pointer's light falls on when the pointer is at this point."""
        reach = self.LIGHT * self.scale() + 2
        return QRectF(at.x() - reach, at.y() - reach, 2 * reach, 2 * reach).toAlignedRect()

    def _light(self, p, body):
        """The pointer is green and it glows, so it lights the desk a little where it is: a faint pool of the same green on
        the ground under it, beneath the sheets and the wires, the way a lamp shows under glass. It moves only when the hand
        moves it, nothing here moves by itself. The Clean desk has none, and a page being read is not lit from behind."""
        if not self.texture or self.reading is not None or not body.contains(self._mouse):return
        level = min(t.glow(), 2.4);reach = self.LIGHT * self.scale() * (1.0 + 0.18 * (level - 1.0))
        pool = QRadialGradient(self._mouse, reach)
        pool.setColorAt(0.0, ink(t.READY, min(0.4, 0.14 * level)));pool.setColorAt(0.35, ink(t.READY, min(0.2, 0.065 * level)));pool.setColorAt(1.0, ink(t.READY, 0.0))
        p.save();p.setClipRect(body);p.setPen(Qt.NoPen);p.setBrush(pool);p.drawEllipse(self._mouse, reach, reach);p.restore()

    def _head(self, p):
        s = self.scale();h = self.head_height();x = 28 * s
        if t.APPEARANCE == 'kasandra' and self.art_mode == 'illustrated' and self.texture:      # her wires over the rooftops, faint, under the Field's words
            scene = self._kasandra('field_edge', 'viewing')
            if scene is not None:
                from . import kasandra_art
                image = kasandra_art.picture(kasandra_art.folder(self.parentWidget().host.root), scene, self.width(), h, self.devicePixelRatioF())
                if not image.isNull():
                    p.save();p.setOpacity(0.42);p.drawImage(QRectF(0, 0, self.width(), h), image);p.restore()
                    shade = QLinearGradient(0, 0, self.width(), 0);shade.setColorAt(0.0, ink(t.GROUND, 0.78));shade.setColorAt(0.55, ink(t.GROUND, 0.45));shade.setColorAt(1.0, ink(t.GROUND, 0.62))
                    p.fillRect(QRectF(0, 0, self.width(), h), shade)
        p.setPen(QPen(QColor(t.LINE), 1));p.drawLine(QPointF(0, h - 0.5), QPointF(self.width(), h - 0.5))
        p.setFont(self.display(13));p.setPen(QColor(t.AMBER_EDGE))
        label = 'FIELD';fm = QFontMetricsF(p.font());base = h / 2 + fm.ascent() / 2 - 2
        p.drawText(QPointF(x, base), label);x += fm.horizontalAdvance(label) + 14 * s
        p.setFont(self.mono(13, QFont.Medium));fm = QFontMetricsF(p.font())      # the faces' words: the working face
        self._face_boxes = []
        for name, letter in self.faces:      # the faces of the Field: the one showing is underlined, each says its key
            word = name.upper();w = fm.horizontalAdvance(word);on = name == self.face
            spot = QRectF(x - 6 * s, 0, w + 12 * s, h)
            if on:self._bloom(p, QPointF(x, base), word, t.AMBER_EDGE, 1.2)
            else:self._hot.append((spot, getattr(Qt, 'Key_' + letter.upper(), Qt.Key_unknown), letter, 'The %s face of the Field (%s)' % (name, letter.upper())))
            p.setPen(QColor(t.AMBER_TEXT if on else t.READY if spot.contains(self._mouse) else t.QUIET));p.drawText(QPointF(x, base), word)
            if on:
                if self.texture:             # the chosen face's rule is lit from below
                    for width, alpha in ((7.0, 0.07), (4.0, 0.14)):
                        p.setPen(QPen(ink(t.AMBER_EDGE, alpha), width * s, Qt.SolidLine, Qt.RoundCap));p.drawLine(QPointF(x, base + 6 * s), QPointF(x + w, base + 6 * s))
                p.setPen(QPen(QColor(t.AMBER_EDGE), 2));p.drawLine(QPointF(x, base + 6 * s), QPointF(x + w, base + 6 * s))
            self._face_boxes.append((QRectF(x - 4 * s, 0, w + 8 * s, h), name));x += w + 16 * s
        if self.faces:x += 4 * s
        p.setFont(self.sans(17) if t.DISPLAY == 'IBM Plex Mono' else self.display(17));fm2 = QFontMetricsF(p.font());p.setPen(QColor(t.TEXT))
        said = self.field.title or 'This workspace';parts = self.field.census()
        p.setFont(self.mono(12.5));fm3 = QFontMetricsF(p.font());room = self.width() - x - 28 * s
        waiting = [part for part in parts if 'recheck' in part or 'open question' in part]
        while parts and fm3.horizontalAdvance('  ·  '.join(parts)) + 44 * s + fm2.horizontalAdvance(said) > room:
            parts = waiting if parts != waiting and waiting else []        # the title keeps its room; the counts give way, what waits last
            waiting = []
        census = '  ·  '.join(parts);census_w = fm3.horizontalAdvance(census)
        p.setFont(self.sans(17) if t.DISPLAY == 'IBM Plex Mono' else self.display(17))
        p.drawText(QPointF(x, h / 2 + fm2.ascent() / 2 - 2), fm2.elidedText(said, Qt.ElideRight, max(60.0, room - (census_w + 44 * s if census else 0))))
        if census:
            p.setFont(self.mono(12.5));p.setPen(QColor(t.QUIET));left = self.width() - 28 * s - census_w
            if any(obj.needs_attention() for obj in self.field.objects):
                # Something on the desk waits, here or out of sight: one lamp says so, and the counts beside it are the place to
                # click for the next thing that waits (what A does).
                mark = 8 * s;lamp = QRectF(left - mark - 10 * s, base - fm3.ascent() / 2 - mark / 2 + 1, mark, mark)
                over = QRectF(lamp.left() - 6 * s, 0, census_w + mark + 22 * s, h)
                self._mark(p, lamp, 'waiting', QColor(t.OWNER))
                self._hot.append((over, Qt.Key_A, 'a', 'Go to the next thing that waits for you'))
                p.setPen(QColor(t.READY if over.contains(self._mouse) else t.AMBER_TEXT))
            p.drawText(QPointF(left, base), census)

    def _columns(self, p, body):
        s = self.scale();far = self.zoom < self.FAR      # far off, a column's name keeps its reading size as the sheets' names do
        p.setFont(self.mono(11 / self.zoom if far else 12, QFont.Medium));fm = QFontMetricsF(p.font())
        for rank in self.field.ranks():
            ids = self.field.column(rank)
            if not ids or ids[0] not in self._placed:continue
            first = self._placed[ids[0]]
            x = body.left() + first.x - self.scroll_x;y = body.top() + (min(first.y - 6 * s, fm.ascent() + 6 * s / self.zoom) if far else 24 * s) - self.scroll_y
            p.setPen(ink(t.QUIET, 0.95))
            p.drawText(QPointF(x, y), self.field.rank_title(rank))
            p.setPen(QPen(ink(t.LINE, 0.9), 1))
            start = x + fm.horizontalAdvance(self.field.rank_title(rank)) + 10 * s
            if start < x + first.w:p.drawLine(QPointF(start, y - fm.ascent() / 2 + 1), QPointF(x + first.w, y - fm.ascent() / 2 + 1))

    def _wires(self, p, body, depth, seen):
        s = self.scale()
        for link in self.field.links:
            a = self._drawn_rect(link.source, body);b = self._drawn_rect(link.target, body)
            if a is None or b is None or not a.united(b).intersects(seen):continue
            near = min(depth.get(link.source, 3), depth.get(link.target, 3))
            touching = self.field.selected in (link.source, link.target) or (bool(self._hover) and self._hover in (link.source, link.target))
            # A wire that asks for a recheck is always at full strength: it must be findable without selecting one of its ends.
            strength = 1.0 if touching or link.stale else (0.5 if near <= 1 else 0.3)
            start = QPointF(a.right(), a.center().y());end = QPointF(b.left(), b.center().y())
            if end.x() < start.x():      # a wire that would run backwards leaves from the left and arrives at the right
                start = QPointF(a.left(), a.center().y());end = QPointF(b.right(), b.center().y())
            reach = max(24.0 * s, abs(end.x() - start.x()) * 0.5) * (1 if end.x() >= start.x() else -1)
            path = QPainterPath(start);path.cubicTo(QPointF(start.x() + reach, start.y()), QPointF(end.x() - reach, end.y()), end)
            hovered = bool(self._hover) and self._hover in (link.source, link.target) and self.field.selected not in (link.source, link.target)
            colour = t.RECHECK if link.stale else t.READY if hovered else (t.TEXT if touching else t.TEAL_EDGE)
            if self.texture:      # the light a wire carries, under the line, wide and faint: green when it is live, amber when it asks for a recheck
                lamp = t.RECHECK if link.stale else t.READY
                gain = (2.6 if touching else (2.0 if link.stale else 1.0)) * min(t.glow(), 2.6)
                for width, alpha in ((7.0, 0.035), (4.0, 0.07)):
                    p.setBrush(Qt.NoBrush);p.setPen(QPen(ink(lamp, alpha * gain * (1.0 if near <= 1 or touching or link.stale else 0.6)), width * s));p.drawPath(path)
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

    def _halo(self, p, rect, colour, strength=1.0):
        """A soft glow around a rectangle: three outlines, the widest the faintest. Still, like everything on this surface.
        The Clean desk has none."""
        if not self.texture:return
        s = self.scale();level = t.glow();strength = strength * level;p.save();p.setBrush(Qt.NoBrush)
        rings = ((7.0, 8.0, 0.05), (4.0, 5.0, 0.09), (1.5, 2.5, 0.17))
        if level >= 1.5:rings = ((13.0, 12.0, 0.022),) + rings        # a brighter desk throws its light further, not only harder
        if level >= 2.5:rings = ((20.0, 15.0, 0.014),) + rings
        for grow, width, alpha in rings:
            p.setPen(QPen(ink(colour, min(1.0, alpha * strength)), width * s));p.drawRect(rect.adjusted(-grow * s, -grow * s, grow * s, grow * s))
        p.restore()

    def _bloom(self, p, at, text, colour, strength=1.0):
        """The light a lit word throws: the same word drawn faintly a little off in eight directions, under the crisp word
        the caller draws next. The letters stay as sharp as they were; only the dark around them warms. For the few words
        that are lit (the sheet that has the keyboard, the chosen face), never for running text. The Clean desk has none."""
        if not self.texture:return
        s = self.scale();level = t.glow();p.save();p.setPen(ink(colour, min(1.0, 0.085 * strength * min(level, 2.4))))
        for reach in ((1.1 * s, 2.2 * s, 3.6 * s) if level >= 1.5 else (1.1 * s, 2.2 * s)):
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (0.7, 0.7), (-0.7, 0.7), (0.7, -0.7), (-0.7, -0.7)):
                p.drawText(QPointF(at.x() + dx * reach, at.y() + dy * reach), text)
        p.restore()

    def _mark(self, p, box, state, colour):
        """One mark per state, different in shape and not only in hue: settled a filled square, recheck half filled, open
        hollow, held crossed, waiting a dot inside, failed a cross, cannot be read or reached a dash. What is settled glows
        a little in the desk's green: it is what is live. What waits for the owner is lit in amber around its mark and never
        inside it: the shapes are the sign that does not depend on colour, and a hollow mark filled with light would read as
        a full one."""
        p.save();pen = QPen(colour, 1.5)
        if self.texture and state in SETTLED:
            level = t.glow();reach = box.width() * (2.6 + 1.1 * (level - 1.0))
            glow = QRadialGradient(box.center(), reach);inner = QColor(colour);inner.setAlphaF(min(1.0, colour.alphaF()) * min(0.85, 0.42 * (0.7 + 0.3 * level)))
            outer = QColor(colour);outer.setAlphaF(0.0);glow.setColorAt(0.0, inner);glow.setColorAt(1.0, outer)
            p.setPen(Qt.NoPen);p.setBrush(glow);p.drawEllipse(box.center(), reach, reach)
        elif state in ATTENTION:
            self._halo(p, box, colour, 1.6 * min(1.0, colour.alphaF() + 0.15))
        p.setPen(pen);p.setBrush(Qt.NoBrush)
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
        touched = bool(self._hover) and obj.id == self._hover and not selected      # under the pointer: it answers in the pointer's green
        # The light outside a sheet says where the hand is: green under the pointer, amber on the sheet that has the keyboard
        # (one on the whole surface, and the strongest, because it is where a key will act). What a sheet's state is, is
        # lit inside it, at its mark; so a sheet that waits can be under the pointer and say both.
        if touched:self._halo(p, r, t.READY, 1.5)
        elif selected and focus:self._halo(p, r, t.AMBER_EDGE, 1.9)
        p.setBrush(QColor((t.CARD, t.CARD, t.PANEL, t.GROUND)[depth]))       # a sheet recedes by its ground and its edge; its words stay readable
        edge = t.AMBER_EDGE if selected and focus else t.READY if touched else (t.LINE_STRONG if depth <= 1 else t.LINE)
        p.setPen(QPen(ink(edge, 1.0 if selected else 0.85 if touched else edge_keep + 0.1), 2 if selected else 1));p.drawRect(r)
        if obj.state == STATE_RECHECK and t.APPEARANCE != 'graphite' and not (selected and focus) and not touched:
            dashed = QPen(ink(t.RECHECK, max(0.8, edge_keep + 0.2)), 1.6);dashed.setStyle(Qt.CustomDashLine);dashed.setDashPattern([3, 3])      # Kasandra: a recheck has a lavender dashed edge
            p.save();p.setBrush(Qt.NoBrush);p.setPen(dashed);p.drawRect(r);p.restore()
        if selected:                         # corner ticks: the selection reads without colour too
            p.setPen(QPen(ink(t.AMBER_EDGE if focus else t.LINE_STRONG, 1.0), 2));k = 9 * s;o = 5 * s
            for cx, cy, dx, dy in ((r.left() - o, r.top() - o, 1, 1), (r.right() + o, r.top() - o, -1, 1),
                                   (r.left() - o, r.bottom() + o, 1, -1), (r.right() + o, r.bottom() + o, -1, -1)):
                p.drawLine(QPointF(cx, cy), QPointF(cx + dx * k, cy));p.drawLine(QPointF(cx, cy), QPointF(cx, cy + dy * k))
        if obj.lately(self._now):            # its record changed in the last hours: a small turned corner, the mark of what was just worked on
            fold = 9 * s;p.save();p.setPen(Qt.NoPen);p.setBrush(ink(t.AMBER_EDGE, 0.55 + 0.4 * keep))
            p.drawPolygon(QPolygonF([QPointF(r.right() - fold, r.top()), QPointF(r.right(), r.top()), QPointF(r.right(), r.top() + fold)]));p.restore()
        pad = 12 * s;inner = r.adjusted(pad, pad - 2 * s, -pad, -pad + 2 * s);would = self.would.get(obj.id)
        if self.zoom < self.FAR:             # seen from far off: its glyph, its state's mark and its name, and nothing that cannot be read
            self._far(p, obj, r, keep, selected and focus)
            self._would_edge(p, r, would, touched, selected and focus);return
        # Kind at the left, state at the right. A narrow sheet keeps its kind and the state's mark; the state's word gives way.
        p.setFont(self.mono(12, QFont.Medium));fm = QFontMetricsF(p.font());y = inner.top() + fm.ascent()
        state = STATE_WORD.get(obj.state, obj.state or '')
        state_colour = t.READY if obj.state in SETTLED else (attention_ink(obj.state) if obj.state in ATTENTION else t.QUIET)
        mark = 8 * s;state_w = (fm.horizontalAdvance(state.upper()) + mark + 6 * s) if state else 0.0
        full = obj.tag or KIND_TAG.get(obj.kind, obj.kind.upper())
        worded = bool(state) and inner.width() >= fm.horizontalAdvance(full) + state_w + 8 * s
        if state and not worded:state_w = mark
        kind_ink = t.AMBER_TEXT if obj.kind in ('question', 'condition') else t.QUIET;lead = 0.0
        if tool_faces.mode() == 'icons' and obj.kind in KIND_GLYPH and inner.width() > 90 * s:      # the owner chose icons: the kind's glyph leads its word
            side = fm.height() * 1.08;lead = side + 5 * s
            self._glyph(p, KIND_GLYPH[obj.kind], QRectF(inner.left(), y - fm.ascent() + (fm.height() - side) / 2 - 1, side, side), ink(kind_ink, keep), ink(t.FAINT, keep))
        tag = fm.elidedText(full, Qt.ElideRight, max(10.0, inner.width() - state_w - 8 * s - lead))
        if lead and tag != full:tag = ''     # no room for both: the glyph alone says the kind, whole, rather than half a word beside it
        p.setPen(ink(kind_ink, keep));p.drawText(QPointF(inner.left() + lead, y), tag)
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
            y += fm.height()
            if selected and focus:self._bloom(p, QPointF(inner.left(), y - fm.descent()), line, t.AMBER_EDGE)      # the name of the sheet that has the keyboard is lit
            p.drawText(QPointF(inner.left(), y - fm.descent()), line)
        # Facts, while they fit above the identity line.
        p.setFont(self.mono(12.5));fm = QFontMetricsF(p.font());fm_where = QFontMetricsF(self.mono(12));where_h = fm_where.height() if obj.where else 0
        y += 4 * s
        facts = () if self.field.compact else (((would,) + tuple(obj.lines[:FACT_LINES - 1])) if would else obj.lines[:FACT_LINES])
        for at, fact in enumerate(facts):
            if y + fm.height() > inner.bottom() - where_h + 1:break
            y += fm.height();p.setPen(ink(t.AMBER_TEXT, 1.0) if would and at == 0 else ink(t.QUIET, keep))
            p.drawText(QPointF(inner.left(), y - fm.descent()), fm.elidedText(str(fact)[:LONGEST], Qt.ElideRight, inner.width()))
        self._would_edge(p, r, would, touched, selected and focus)
        if obj.where and not self.field.compact and inner.bottom() - fm_where.descent() > y + 2:
            p.setFont(self.mono(12));p.setPen(ink(t.FAINT if depth <= 1 else t.QUIET, keep))
            p.drawText(QPointF(inner.left(), inner.bottom() - fm_where.descent()), fm_where.elidedText(str(obj.where)[:LONGEST], Qt.ElideMiddle, inner.width()))

    def _would_edge(self, p, r, would, touched, lit):
        """A sheet a what-if would move: a broken amber edge, which reads as "would" without colour too."""
        if not would:return
        s = self.scale()
        if self.go and not touched and not lit:      # a change that waits for Approve would move this: lit, faintly. A what-if that only asks is not.
            self._halo(p, r.adjusted(-3 * s, -3 * s, 3 * s, 3 * s), t.AMBER_EDGE, 0.7)
        pen = QPen(ink(t.AMBER_EDGE, 0.95), 1.6);pen.setStyle(Qt.CustomDashLine);pen.setDashPattern([4, 4])
        p.setPen(pen);p.setBrush(Qt.NoBrush);p.drawRect(r.adjusted(-3 * s, -3 * s, 3 * s, 3 * s))

    @staticmethod
    def _glyph(p, draw, box, line, fill):
        """One of Graphite's drawn glyphs (glyph_set) in this box, in these two inks."""
        p.save();p.translate(box.left(), box.top());p.scale(box.width() / 20.0, box.height() / 20.0);p.setPen(Qt.NoPen);p.setBrush(Qt.NoBrush)
        try:draw(p, line, fill)
        finally:p.restore()

    def _far(self, p, obj, r, keep, lit):
        """A sheet seen from far off. With the whole desk in the window a sheet's words are five pixels high and say nothing,
        so the sheet is drawn as a map draws a town: the glyph of its kind, the mark of its state, and its name in letters
        that stay large enough to read however far away the desk is. Sizes here are in screen pixels, turned into the units
        the sheets are drawn in (one pixel is 1 / zoom of them)."""
        s = self.scale();px = 1.0 / self.zoom;pad = 6 * s * px
        side = min(20 * s * px, r.height() - 2 * pad);kind_ink = t.AMBER_TEXT if obj.kind in ('question', 'condition') else t.QUIET
        draw = KIND_GLYPH.get(obj.kind)
        if draw is not None:self._glyph(p, draw, QRectF(r.left() + pad, r.top() + pad, side, side), ink(kind_ink, max(keep, 0.75)), ink(t.FAINT, keep))
        mark = 7 * s * px;room = 0.0
        if obj.state:                        # its state, in the corner: the same mark it has near to, the same light
            colour = t.READY if obj.state in SETTLED else (attention_ink(obj.state) if obj.state in ATTENTION else t.QUIET)
            self._mark(p, QRectF(r.right() - pad - mark, r.top() + pad, mark, mark), obj.state, ink(colour, max(keep, 0.85) if obj.state in ATTENTION else keep))
            room = mark + 4 * s * px
        left = r.left() + pad + side + 6 * s * px;width = r.right() - pad - left - room
        if width < 30 * s * px:return
        p.setFont(self.sans(11.5 * px));fm = QFontMetricsF(p.font());p.setPen(ink(t.TEXT, max(keep, 0.8)))
        lines = self._wrap(obj.title, fm, width, max(1, int((r.height() - 2 * pad) / fm.height())))
        y = r.top() + pad + max(0.0, (min(side, r.height() - 2 * pad) - fm.height()) / 2) if len(lines) == 1 else r.top() + pad - 2 * px
        for text in lines:
            y += fm.height()
            if lit:self._bloom(p, QPointF(left, y - fm.descent()), text, t.AMBER_EDGE)
            p.drawText(QPointF(left, y - fm.descent()), text)

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
        """The strip at the foot of the sheets: what is being said about them (a what-if, what the reader left out, what could
        not be read), and how large they are seen, with the three controls that change it. Where the surface goes on beyond
        the window is shown by the bars at its edges, which also move it: it is not said in words a second time."""
        s = self.scale();p.setFont(self.mono(12));wide, tall = self._surface;wide_room, tall_room = self.room(body)
        beyond = tall - tall_room > 1 or wide - wide_room > 1
        # How the surface is being seen, and the key that changes it, as a place to click: offered when there is more than
        # the window shows, and whenever the sheets are not at their ordinary size.
        size = ''
        if abs(self.zoom - 1.0) > 1e-6:
            size = 'Z  %s · %d%%' % ('ordinary size' if self._fitted else 'whole desk', round(self.zoom * 100))
        elif beyond:size = 'Z  whole desk'
        note = ' · '.join(part for part in ((self.would_said + ' · nothing is changed') if self.would_said else '', self.field.note, self.problem) if part)
        aside = self.field.aside if not note else ''      # what belongs elsewhere is said quietly, when nothing louder is being said
        if note or size or aside:           # on its own strip of ground, so it is read over whatever sheet lies under it
            p.fillRect(QRectF(body.left(), body.bottom() - 24 * s, body.width(), 24 * s), ink(t.TERMINAL_GROUND, 0.9))
        fm = QFontMetricsF(p.font());room = body.width() - 56 * s;base = body.bottom() - 13 * s + (fm.ascent() - fm.descent()) / 2;tail = 0.0
        if size:                           # at the right end of the strip
            size_w = fm.horizontalAdvance(size.partition('  ')[2]);sign_w = 24 * s      # the words alone are drawn (0.5.2)
            if size_w + 2 * sign_w < room * 0.6:
                self._keys_line(p, body.right() - 28 * s - size_w, base, [size], t.QUIET, size_w + 2)      # (drawn as its words; Z is not shown)
                at = body.right() - 28 * s - size_w - 10 * s
                for sign, step, tip in (('+', 2, 'Larger'), ('−', -2, 'Smaller')):
                    at -= sign_w;spot = QRectF(at, body.bottom() - 24 * s, sign_w, 24 * s);over = spot.contains(self._mouse)
                    box = spot.adjusted(2 * s, 3 * s, -2 * s, -3 * s)
                    p.save();p.setPen(QPen(QColor(t.TEAL_EDGE if over else t.LINE), 1));p.setBrush(QColor(t.TEAL_SOFT if over else t.RAISED));p.drawRect(box);p.restore()
                    p.setPen(QColor(t.TEAL_TEXT if over else t.QUIET));p.drawText(spot, Qt.AlignCenter, sign)
                    self._hot.append((spot, lambda step=step: self.set_zoom(round(self.zoom * 20 + step) / 20.0), '', tip))
                tail = size_w + 10 * s + 2 * sign_w + 3 * fm.horizontalAdvance(' ');room -= tail
        if note or aside:
            p.setPen(QColor(t.AMBER_TEXT if note else t.QUIET))
            p.drawText(QRectF(body.left() + 28 * s, body.bottom() - 22 * s, room, 18 * s), Qt.AlignLeft | Qt.AlignVCenter, fm.elidedText(note or aside, Qt.ElideRight, room))

    def _empty(self, p, body):
        s = self.scale();p.setFont(self.mono(13));fm = QFontMetricsF(p.font())
        if self.problem:
            p.setPen(QColor(t.AMBER_TEXT));lines = ('// the records could not be read', '', '   ' + self.problem + '.')
        else:
            p.setPen(QColor(t.QUIET));lines = ('// nothing in the field yet', '', '   bring material in through Ingress, or open a file;',
                                               '   what you work on appears here with what it came from.')
        y = body.center().y() - len(lines) * fm.height() / 2;x = max(28 * s, body.center().x() - 240 * s)
        for line in lines:
            y += fm.height();p.drawText(QPointF(x, y), line)

    def _foot(self, p):
        s = self.scale();h = self.foot_height();top = self.height() - h;x = 28 * s
        p.fillRect(QRectF(0, top, self.width(), h), QColor(t.GROUND))
        p.setPen(QPen(QColor(t.LINE), 1));p.drawLine(QPointF(0, top + 0.5), QPointF(self.width(), top + 0.5))
        obj = self.selected()
        # The buttons of the foot, in the order they are read; when the line is too narrow they give way one at a time, the
        # least needed first. Only what has no other home on this surface is here (0.4.9, the audit of what repeats what):
        # a click on a sheet opens it, so there is no Open; the faces are at the head; the lamp at the head goes to what waits;
        # Z is on the strip above; the right button is the menu. Every key is still on the card that ? shows.
        legend = [(2, 'D  do'), (4, 'X  doubt'), (6, 'T  trace'), (5, 'C  check all'), (6.5, 'B  brief'), (10, 'R  look again'), (12, '⌫  where I was'), (0, 'Esc  back')]
        if not self.rail():legend.insert(5, (7, 'S  staC'))       # where Stacy's rail is not shown, the line's key is offered here instead
        p.setFont(self.mono(12));fm = QFontMetricsF(p.font())
        if obj is None:
            self._keys_line(p, x, top + h / 2 + fm.ascent() / 2, ['R  look again', 'Esc  back'], t.QUIET, self.width() - 2 * x);return
        wide = self.width() - 2 * x;compact = h < 60 * s
        p.setFont(self.mono(12, QFont.Medium));p.setPen(QColor(t.AMBER_TEXT))
        tag = obj.tag or KIND_TAG.get(obj.kind, obj.kind.upper())
        if obj.state:tag += '  ·  ' + STATE_WORD.get(obj.state, obj.state).upper()
        if compact:                          # a short window at a large reading size: one line, the kind and the title
            p.drawText(QPointF(x, top + h / 2 + fm.ascent() / 2 - 1), tag)
            p.setFont(self.sans(15));fm2 = QFontMetricsF(p.font());p.setPen(QColor(t.TEXT));left = x + fm.horizontalAdvance(tag) + 18 * s
            p.drawText(QPointF(left, top + h / 2 + fm2.ascent() / 2 - 1), fm2.elidedText(str(obj.title)[:LONGEST], Qt.ElideRight, max(40.0, self.width() - x - left)))
            p.setFont(self.mono(12))
            if self.go:                      # even on one line, what waits can be approved with a click
                p.fillRect(QRectF(self.width() * 0.5, top + 2, self.width() * 0.5, h - 4), QColor(t.GROUND))
                self._keys_line(p, self.width() * 0.5 + 8 * s, top + h / 2 + fm.ascent() / 2 - 1, ['G  ' + self.go], t.AMBER_TEXT, self.width() * 0.5 - x - 8 * s, obj.title)
            return
        p.drawText(QPointF(x, top + 24 * s), tag)
        room = wide - fm.horizontalAdvance(tag) - 40 * s
        while legend and fm.horizontalAdvance('      '.join(word for _, word in legend)) > room:
            legend.remove(max(legend))
        if legend:
            keys = '      '.join(word for _, word in legend);keys_w = fm.horizontalAdvance(keys)
            p.setFont(self.mono(12));self._keys_line(p, self.width() - x - keys_w, top + 24 * s, [word for _, word in legend], t.QUIET, keys_w + 2)
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
            # The go comes first, as a button: it is never the item that does not fit. Each step is a place to click, as a digit is a key.
            items = (['G  ' + self.go] if self.go else []) + ['%d  %s%s' % (n + 1, words, ' (asks first)' if kind == 'write' else '') for n, (words, kind) in enumerate(self.steps[:9])]
            p.setPen(QColor(t.AMBER_TEXT));p.drawText(QPointF(x, top + h - 14 * s), 'DO')
            self._keys_line(p, x + fm3.horizontalAdvance('DO      '), top + h - 14 * s, items, t.AMBER_TEXT, wide - fm3.horizontalAdvance('DO      '), obj.title)
            return
        code_w = min(fm3.horizontalAdvance(code), wide * 0.5) if code else 0.0
        p.drawText(QPointF(x, top + h - 14 * s), fm3.elidedText(said, Qt.ElideRight, wide - (code_w + 28 * s if code else 0)))
        if code:
            p.setPen(QColor(t.TEAL_TEXT));p.drawText(QPointF(self.width() - x - code_w, top + h - 14 * s), fm3.elidedText(code, Qt.ElideRight, code_w))
