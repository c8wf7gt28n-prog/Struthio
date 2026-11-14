"""The desk: one grid for the whole window, mirrored about its vertical centre (HATCH DESK D1a; the owner's brief of
2026-11-06: "a quieter, symmetrical desk" and "Be obsessive in symmetry").

    head band     | left slot  P | centre column: the menus, inset G                                | right slot  P |
    panes         |  left pane P | sep |             workspace (the remainder)              | sep | right pane P  |
    lower band    | left slot  P | centre column: the writing line, inset G                         | right slot  P |

One width P for both panes (the separators are one pixel each, theme2's QMainWindow::separator), the workspace the
remainder, so its centre is the window's axis and an odd pixel can only fall to it. The two bands are as tall as each other
(band_height) and use the same three columns: each slot is P wide, the centre column is the workspace with its separators.
One inset (INSET, scaled) is used everywhere: the band words nearest the window edges sit that far from them, the slot words
nearest the workspace sit that far from the pane edge, and the menus and the writing line sit that far inside the centre
column, so the head's menus and the writing line have matching insets.

D1-fix: the band words are drawn by their ink (InkWord: each word's box its ink and INK_AIR each side, its ink measured once
by ink_extent), so the menus' ink ends are the writing line's ends and the lower band's mirrored words mirror as drawn; the
lower band's words are set smaller in a narrow window, never elided (letter_px, letter_floor, fit_size); the word Graphite in
the script is sized by its capitals against the symbol (script_word_px); the separators show the resize cursor
(MirroredDrag.hover).

The pure part (constants, pane_width, desk, band_height, menu_row, tight_row, spread, grain, contrast, letter sizes, fit_size)
needs no QApplication and is tested by tests_integrated/test_desk.py; the Qt part (the grain tile, painting a band, ink_extent,
InkWord, apply, the mirrored drag) is measured by tools/check_desk_ui.py with tools/symmetry.py. docs/GRAPHITE_DESK.md says
what was chosen and why.
"""
from __future__ import annotations
import math
from collections import namedtuple

SCALE_MAX = 1.4     # sizes that are not text follow the interface size up to this factor (the cat's and the old columns' ceiling)
PANE = 268          # both panes at 14 pt when the owner has set no width (scaled); widened to what their words need
CENTRE = 400        # the workspace's floor at 14 pt, scaled (V01 W1's rule, kept: Home and the Finder fit before a pane widens)
INSET = 16          # the one inset at 14 pt, scaled
GAP = 12            # the gap between two words of a band slot at 14 pt, scaled
CLOSE_GAP = 4       # the least gap between two slot words at 14 pt, scaled: the gaps close up before a word elides
MENU_GAP = 2        # the least gap between two menu words at 14 pt, scaled (each menu word's own box carries a space each side)
MENU_PX = 15        # the menu words' size at 14 pt, scaled with the interface (no ceiling, as every word)
SYMBOL = 32         # the erased Graphite symbol's width at 14 pt, scaled (its height follows the mark, 177/224 of it)
SEPARATOR = 1       # theme2: QMainWindow::separator is one pixel wide, one each side of the workspace
BAND_PAD = 8        # above and below the tallest item of a band
CAT = 44            # the cat's height at 14 pt (typebar_qt.HATCH_ICON), scaled
WORD_CHROME = 22    # a band word's box around its line of text: a 3 px mark row and 4 px padding above and below, 4 px air
                    # each side; even, so the text inside a band word and inside the writing line lands on the same pixel row
SAVED = (160, 900)  # a saved pane width is used when it is in this range (session.SIMULATOR_WIDTHS, the wider of the two)
WORD_PX = 22        # the word Graphite at the upper left at 14 pt, scaled up to SCALE_MAX: plain Plex SemiBold (script off)
WORD_SCRIPT_PX = 34 # the same word in the Paper script (the owner, 2026-11-06: "upper left Graphite should be cursive"): the
                    # script's small x-height needs about 1.5 times the print size to stand as tall. D1-fix: the size the
                    # window uses is script_word_px, the size at which the script's capitals stand as tall as the symbol
WORD_STROKE = 0.5   # a hairline of the same pale paper round the script's outline, so its thin strokes hold on the grain
LETTER_PX = 16      # the lower band's lettering at 14 pt (the controls' size), scaled with the interface, no ceiling
LETTER_FLOOR = 0.70 # D1-fix: in a narrow window the lower band's words are set smaller, down to this share, rather than elide
INK_AIR = 4         # D1-fix: a band word's box is its ink and this much each side, at 14 pt, scaled (no other padding)
INK_LEVEL = 0.25    # a pixel is part of a word's ink when at least this much of it is covered (the desk check measures alike)
MARK = 3            # the bands' marks (an action's eraser pink, the active choice's pencil yellow), px tall

Desk = namedtuple('Desk', 'width pane workspace band inset gap symbol scale left right line')
"""width: the window; pane: P, both panes and both band slots; workspace: the remainder between the separators; band: the
height of both bands in Line mode; inset, gap, symbol: scaled sizes; scale: the interface scale (ui_pt / 14, as given); left, right: the workspace's edges (left = P + 1,
right = width - P - 1, so left == width - right); line: the writing line's inset inside the centre column, the menus' own
inset when they lie on the column (equal gaps on whole pixels leave a few pixels over, shared by both ends), else `inset`."""


def clamp_scale(scale):
    return min(max(float(scale), 1.0), SCALE_MAX)


def scaled(value, scale):
    """A size that is not text: value at 14 pt, following the interface size from 1.0 up to SCALE_MAX, never smaller."""
    return round(value * clamp_scale(scale))


def default_pane(scale):return scaled(PANE, scale)


def centre_floor(scale):return scaled(CENTRE, scale)


def inset(scale):return scaled(INSET, scale)


def gap(scale):return scaled(GAP, scale)


def menu_gap(scale):return scaled(MENU_GAP, scale)


def close_gap(scale):return scaled(CLOSE_GAP, scale)


def menu_px(scale):return max(10, round(MENU_PX * float(scale)))


def symbol_px(scale):return scaled(SYMBOL, scale)


def cat_px(scale):return scaled(CAT, scale)


def ink_air(scale):return scaled(INK_AIR, scale)


def letter_px(scale):
    """The lower band's lettering at full size: the controls' 16 px at 14 pt, following the interface size."""
    return max(10, round(LETTER_PX * float(scale)))


def letter_floor(scale):
    """The least size the lower band's words may be set at in a narrow window (D1-fix: smaller, never elided)."""
    return max(11, round(letter_px(scale) * LETTER_FLOOR))


def fit_size(need, room, top, floor):
    """The largest size from top down to floor whose need(size) fits room; floor when none does (the panes widen to it)."""
    for size in range(int(top), int(floor) - 1, -1):
        if need(size) <= room:return size
    return int(floor)


def word_px(scale, script=True):
    """The word Graphite's size: the script's (WORD_SCRIPT_PX) or, with the script off, print's (WORD_PX), at 14 pt and
    following the interface size up to SCALE_MAX, as the cat and the symbol do."""
    return scaled(WORD_SCRIPT_PX if script else WORD_PX, scale)


def symbol_height(scale):
    """The System menu's symbol as drawn: its width symbol_px and its height 177/224 of it (graphite_brand.MARK_BOX)."""
    return symbol_px(scale) * 177.0 / 224.0


def script_word_px(scale):
    """The word Graphite's size in the script (D1-fix; the integrator: where equal height no longer makes sense for a script
    word against a symbol, pair their centres and their optical size): the size at which the script's capitals stand exactly
    as tall as the symbol (the face's cap height equals symbol_height to within half a pixel). WORD_SCRIPT_PX scaled when
    the face is missing. Needs a QApplication (the face's own metrics)."""
    from PySide6.QtGui import QFont, QFontDatabase, QFontMetricsF
    from .shell2 import SCRIPT
    if SCRIPT not in QFontDatabase.families():return word_px(scale)
    font = QFont(SCRIPT);font.setPixelSize(200);cap = QFontMetricsF(font).capHeight() / 200.0
    return round(symbol_height(scale) / cap) if cap > 0 else word_px(scale)


def word_stroke(scale, script=True):
    """The hairline round the script's outline (none for print): WORD_STROKE at 14 pt, scaled like the word."""
    return round(WORD_STROKE * clamp_scale(scale), 3) if script else 0.0


def word_height(line_px):
    """A band word's box (and the writing line's): its text line plus WORD_CHROME."""
    return int(line_px) + WORD_CHROME


def band_height(scale, line_px):
    """Both bands' height in Line mode: the taller of the cat and a band word, with BAND_PAD above and below."""
    return max(cat_px(scale), word_height(line_px)) + 2 * BAND_PAD


def saved_pane(value):
    """A saved pane width, or None when the profile has none in range."""
    return value if type(value) is int and SAVED[0] <= value <= SAVED[1] else None


def pane_width(width, scale, owner=None, least=0, whole=0, centre=0):
    """The one width of both panes. The owner's width (a drag, the Workspace setting, the saved session) or else the default,
    raised to `whole` (every slot word whole and each pane's own content) while the workspace keeps its floor (the larger of
    centre_floor and `centre`, what the workspace's own content needs), and never under `least` (the slots' primary words
    whole, their quiet words at their elided minimum, each pane's own content)."""
    room = (int(width) - 2 * SEPARATOR - max(centre_floor(scale), int(centre))) // 2
    want = saved_pane(owner)
    want = default_pane(scale) if want is None else want
    return max(int(least), min(max(want, int(whole)), room))


def desk(width, scale, line_px, owner=None, least=0, whole=0, centre=0):
    """The desk for a window `width` wide at the interface `scale` with band lettering `line_px` high."""
    width = int(width);p = pane_width(width, scale, owner, least, whole, centre)
    return Desk(width, p, width - 2 * p - 2 * SEPARATOR, band_height(scale, line_px), inset(scale), gap(scale), symbol_px(scale),
                float(scale), p + SEPARATOR, width - p - SEPARATOR, inset(scale))


def mirror(x, w, width):
    """The left edge of the box mirrored about the window's axis: a box at x, w wide mirrors to width - x - w."""
    return int(width) - int(x) - int(w)


def spread(widths, start, end):
    """Words placed from `start` to `end`: the first word's left edge at start and the last word's right edge at end, the
    room between shared as equal gaps (a remainder of a few pixels goes one each to the gaps nearest the middle). Returns the
    left edges and the gaps, or None when the words are wider than the room. One word sits at start."""
    widths = [int(w) for w in widths];n = len(widths);room = int(end) - int(start) - sum(widths)
    if not n or room < 0:return None
    if n == 1:return [int(start)], []
    base, extra = divmod(room, n - 1);gaps = [base] * (n - 1)
    order = sorted(range(n - 1), key=lambda i:(abs(2 * i - (n - 2)), i))  # the middle gaps first
    for i in order[:extra]:gaps[i] += 1
    xs = [int(start)]
    for w, g in zip(widths, gaps):xs.append(xs[-1] + w + g)
    return xs, gaps


def _row(widths, width, g):
    """A row of words with gap g centred on the axis: (left edges, gaps, widths). When the row and the window differ by an odd
    pixel the last box (the ⋯ that holds folded menus, or the last word) is one pixel wider, its word centred in it: the
    gaps stay equal and the row stays centred, nothing goes to one side."""
    widths = [int(w) for w in widths];n = len(widths)
    if (int(width) - sum(widths) - (n - 1) * g) % 2:widths[-1] += 1
    spare = int(width) - sum(widths) - (n - 1) * g
    xs = [spare // 2]
    for w in widths[:-1]:xs.append(xs[-1] + w + g)
    return xs, [g] * (n - 1), widths


def menu_row(widths, width, start, end, least):
    """The head's menu words across [start, end) (start == width - end: the centre column less its inset) with equal gaps,
    the first word at start and the last ending at end as nearly as whole pixels allow: the largest equal gap, the few pixels
    it leaves shared by the two ends (an odd one widens the last box, as _row says), so the row stays centred on the axis.
    None when the words do not fit there with the least gap. Returns (left edges, gaps, widths) as _row."""
    widths = [int(w) for w in widths];n = len(widths)
    if not n:return None
    room = int(end) - int(start) - sum(widths)
    if n == 1:return _row(widths, width, 0) if room >= 0 else None
    g = room // (n - 1)
    if (n - 1) % 2 and (int(width) - sum(widths) - (n - 1) * g) % 2 and g - 1 >= least:g -= 1  # an odd count of gaps: one
    if g < least:return None                                                                      # less each centres it exactly
    return _row(widths, width, g)


def tight_row(widths, width, least):
    """The words centred on the axis with the least gap (one more when that lets the two ends split evenly)."""
    widths = [int(w) for w in widths];n = len(widths);g = int(least)
    if n > 1 and (n - 1) % 2 and (int(width) - sum(widths) - (n - 1) * g) % 2:g += 1
    return _row(widths, width, g)


# The grain --------------------------------------------------------------------------------------------------------------
# Both bands are shaded like a graphite pencil: one tile, drawn once, the same in both bands and started at each band's own
# top-left (both bands start at the window's left edge), so their pixels match where no word is drawn. Deterministic: a fixed
# integer hash and a fixed stroke list, no random seed per run.

from . import boss_theme as _bt      # the band's own colours follow the appearance (Graphite or Kasandra) chosen at start
BAND = _bt.BAND                # near-black glass above and below the desk (deep indigo in Kasandra)
ERASED = _bt.ERASED            # lettering on a band: paper, as if erased from the shading
ERASED_QUIET = _bt.ERASED_QUIET  # quieter lettering on a band (the monitors' key words, Find and Kernel)
ERASER_MARK = _bt.BAND_MARK    # actions on a band: the hover and keyboard-focus mark (shell2.ERASER_MARK)
PENCIL = _bt.BAND_PENCIL       # an active choice on a band: the short pencil-yellow mark (shell2.AMBER_EDGE)
GRAIN_SIZE = (256, 128)        # the tile; the grain is fine enough that its repeat does not show
GRAIN_SEED = 0x6A7A           # the stroke list's fixed seed
GRAIN_AMPLITUDE = 2            # the grain stays within this many levels of the mean (quiet enough for small lettering)


def _hash(x, y, salt=0):
    """A fixed integer hash of a pixel, 0 … 1 (no state, no seed per run)."""
    h = (x * 374761393 + y * 668265263 + salt * 2246822519) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65535.0


def grain(size=GRAIN_SIZE, seed=GRAIN_SEED, amplitude=GRAIN_AMPLITUDE):
    """The tile's tone offsets from BAND, row by row (a list of ints, mean 0 to within rounding, each within ±amplitude):
    the paper's tooth (a fine hash noise) under long, light diagonal strokes leaning like hand shading (lower left to upper
    right), each stroke tapering at both ends and wrapping at the tile's edges so the tile repeats without a seam."""
    w, h = size;acc = [0.0] * (w * h)
    for y in range(h):
        for x in range(w):acc[y * w + x] = (_hash(x, y) - .5) * 1.2 + (_hash(x // 2, y // 2, 7) - .5) * .8
    state = seed & 0x7FFFFFFF
    def rnd():
        nonlocal state
        state = (1103515245 * state + 12345) & 0x7FFFFFFF;return state / 0x7FFFFFFF
    for _ in range(w * h // 90):
        x0, y0 = rnd() * w, rnd() * h;length = 18 + rnd() * 70;angle = math.radians(-58 + (rnd() - .5) * 10)
        weight = (rnd() - .45) * 2.6;dx, dy = math.cos(angle), math.sin(angle)
        for t in range(int(length)):
            taper = math.sin(math.pi * (t + .5) / length)
            xi, yi = int(x0 + t * dx) % w, int(y0 + t * dy) % h;acc[yi * w + xi] += weight * taper
    mean = sum(acc) / len(acc);spread_ = max(abs(v - mean) for v in acc) or 1.0
    k = amplitude / spread_
    return [max(-amplitude, min(amplitude, round((v - mean) * k))) for v in acc]


def tone(offset):
    """The colour of one grain level: BAND moved by offset on every channel."""
    return tuple(max(0, min(255, c + offset)) for c in BAND)


def _channel(c):
    c = c / 255.0;return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(rgb):
    """WCAG relative luminance of an (r, g, b) or '#rrggbb' colour."""
    if isinstance(rgb, str):rgb = tuple(int(rgb.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4))
    r, g, b = (_channel(c) for c in rgb[:3]);return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    """WCAG contrast ratio of two colours (1 … 21)."""
    la, lb = sorted((luminance(a), luminance(b)), reverse=True);return (la + 0.05) / (lb + 0.05)


def grain_report(values=None):
    """What the owner asked to be measured: the tile's mean tone and range, and the contrast of the band lettering, the
    quiet lettering and the two marks against the mean and against the lightest 5% of the grain (the worst place a letter
    can stand)."""
    values = grain() if values is None else values
    ordered = sorted(values);light = ordered[int(len(ordered) * .95)];mean = sum(values) / len(values)
    mean_rgb = tuple(c + mean for c in BAND)
    rows = {name:dict(colour=colour, on_mean=round(contrast(colour, mean_rgb), 2), on_light_grain=round(contrast(colour, tone(light)), 2))
            for name, colour in (('lettering', ERASED), ('quiet lettering', ERASED_QUIET), ('action mark', ERASER_MARK), ('active mark', PENCIL))}
    return dict(tile=list(GRAIN_SIZE), mean_offset=round(mean, 4), mean_tone='#%02x%02x%02x' % tuple(round(c) for c in mean_rgb),
                lightest_5_percent_offset=light, range=[ordered[0], ordered[-1]], contrast=rows)


# The Qt part ----------------------------------------------------------------------------------------------------------------

_TILE = []


def grain_tile():
    """The tile as a QPixmap, drawn once per process from grain()."""
    if _TILE:return _TILE[0]
    from PySide6.QtGui import QImage, QPixmap
    w, h = GRAIN_SIZE;values = grain();data = bytearray()
    for v in values:
        r, g, b = tone(v);data += bytes((b, g, r, 255))
    image = QImage(bytes(data), w, h, 4 * w, QImage.Format_ARGB32).copy()
    _TILE.append(QPixmap.fromImage(image));return _TILE[0]


def paint_band(widget, painter):
    """Shade a band edge to edge with the grain, the tile starting at the band's own top-left (both bands start at the
    window's left edge, so their columns of grain line up and neither looks lighter)."""
    from PySide6.QtGui import QBrush, QColor
    from .boss_theme import CUE_EDGE as AMBER_EDGE      # 0.8.3: the band's rule is a cue (Graphite's amber, her cyan line)
    painter.save();painter.setBrushOrigin(0, 0);painter.fillRect(widget.rect(), QBrush(grain_tile()))
    top = widget.objectName() == 'TopBar2'
    y = getattr(widget, 'command_band_height', widget.height()) - 2 if top else 0
    # The band's amber rule throws its light into the band (0.5.1: "I want way more glow effect"): a short fall of amber
    # from the rule, deeper and stronger as the desk's glow is turned up; none on the Clean desk.
    try:
        from .boss_qt import glows
        from .boss_theme import glow
        level = glow() if glows(widget.window()) else 0.0
    except Exception:  # noqa: BLE001 - a band is drawn whatever else is the matter
        level = 0.0
    if level > 0:
        from PySide6.QtGui import QLinearGradient
        deep = round(7 * level);start, end = (max(0, y), max(0, y) - deep) if top else (2, 2 + deep)
        fall = QLinearGradient(0, start, 0, end);lit = QColor(AMBER_EDGE);lit.setAlphaF(min(0.42, 0.11 * level));dark = QColor(AMBER_EDGE);dark.setAlphaF(0.0)
        fall.setColorAt(0.0, lit);fall.setColorAt(1.0, dark)
        painter.fillRect(0, min(start, end), widget.width(), deep, QBrush(fall))
    painter.fillRect(0, max(0, y), widget.width(), 2, QColor(AMBER_EDGE))
    painter.restore()


_INK = {}


def ink_extent(font, text):
    """(left, top, right, bottom) of `text` as drawn in `font` from an origin on a whole pixel (the start of its baseline at
    (0, 0)): the first and last columns and rows at least INK_LEVEL covered, right and bottom exclusive. Rendered once per
    font and text: the band words are drawn from whole-pixel origins (InkWord), so the ink lands exactly here."""
    key = (font.key(), text)
    if key in _INK:return _INK[key]
    from PySide6.QtGui import QColor, QFontMetrics, QImage, QPainter
    fm = QFontMetrics(font);pad = fm.height();w = max(1, fm.horizontalAdvance(text)) + 2 * pad;h = fm.height() + 2 * pad
    image = QImage(w, h, QImage.Format_ARGB32_Premultiplied);image.fill(0)
    p = QPainter(image);p.setFont(font);p.setPen(QColor(255, 255, 255));p.drawText(pad, pad + fm.ascent(), text);p.end()
    level = round(255 * INK_LEVEL);cols = [];rows = []
    for y in range(h):
        line = [x for x in range(w) if image.pixelColor(x, y).alpha() >= level]
        if line:rows.append(y);cols.extend((line[0], line[-1]))
    out = (min(cols) - pad, rows[0] - pad - fm.ascent(), max(cols) + 1 - pad, rows[-1] + 1 - pad - fm.ascent()) if cols else (0, 0, 0, 0)
    _INK[key] = out;return out


def ink_width(font, text):
    left, _, right, _ = ink_extent(font, text);return right - left


def line_px(px):
    """The height of a line of the lower band's lettering at px (the band words' and the writing line's font)."""
    from PySide6.QtGui import QFont, QFontMetrics
    from .shell2 import SANS
    font = QFont(SANS);font.setPixelSize(int(px));return QFontMetrics(font).height()


class InkWord:
    """A band word drawn by its ink (D1-fix; the reviews found the drawn words a few pixels off their boxes' symmetry): the
    word's own text from a whole-pixel origin set by the band's layout (place_ink), in the band's lettering (the quieter
    lettering for a quiet word), no padding, no bold; under its ink, exactly as long as it, a 3 px mark: eraser pink for an
    action's hover, keyboard focus or open menu, pencil yellow for the active choice. The widget keeps its text, tooltip,
    accessible words and clicks; only its painting is the band's. The box is the ink and INK_AIR each side, so mirrored boxes
    put mirrored ink, and the words' drawn gaps are their boxes' gaps and twice the air."""

    @staticmethod
    def install(widget):
        if widget.property('inkWord'):return
        from PySide6.QtCore import QObject, QEvent, Qt
        class Filter(QObject):
            def eventFilter(inner, obj, event):
                if event.type() == QEvent.Paint:InkWord.paint(obj);return True
                if event.type() in (QEvent.Enter, QEvent.Leave, QEvent.FocusIn, QEvent.FocusOut):obj.update()
                return False
        widget.setProperty('inkWord', True);widget.setAttribute(Qt.WA_Hover, True)
        widget._ink_filter = Filter(widget);widget.installEventFilter(widget._ink_filter)

    @staticmethod
    def place(widget, x, baseline):
        """The word's origin in its box: x the first inked column's offset less its ink's own left (so the ink starts at x),
        baseline the text's baseline row."""
        left = ink_extent(widget.font(), widget.text())[0];at = (int(x) - left, int(baseline))
        if (widget.property('inkX'), widget.property('inkBaseline')) != at:
            widget.setProperty('inkX', at[0]);widget.setProperty('inkBaseline', at[1]);widget.update()

    @staticmethod
    def span(widget):
        """(first inked column, last + 1, first inked row, last + 1) in the widget, as drawn."""
        left, top, right, bottom = ink_extent(widget.font(), widget.text())
        x = int(widget.property('inkX') or 0);y = int(widget.property('inkBaseline') or 0)
        return x + left, x + right, y + top, y + bottom

    @staticmethod
    def marked(widget):
        """The mark's colour now, or None: the keyboard's colour for a word that has the keyboard, is held down or has its menu
        open; the pointer's green for a word the pointer is over (so 'the pointer is here' is never mistaken for 'the keys go
        here'); the chosen colour for the active choice."""
        menu = widget.menu() if hasattr(widget, 'menu') else None
        if widget.hasFocus() or (hasattr(widget, 'isDown') and widget.isDown()) or (menu is not None and menu.isVisible()):return ERASER_MARK
        if widget.underMouse():
            from .boss_theme import READY
            return READY
        if hasattr(widget, 'isChecked') and widget.isChecked():
            return _bt.HONEY if widget.property('hers') and _bt.APPEARANCE == 'kasandra' else PENCIL      # Kasandra: her name, lit, in honey
        return None

    @staticmethod
    def paint(widget):
        from PySide6.QtGui import QColor, QPainter
        p = QPainter(widget);p.setRenderHint(QPainter.TextAntialiasing);p.setFont(widget.font())
        p.setPen(QColor(ERASED_QUIET if widget.property('arcQuiet') else ERASED))
        x = int(widget.property('inkX') or 0);y = int(widget.property('inkBaseline') or 0);p.drawText(x, y, widget.text())
        colour = InkWord.marked(widget)
        if colour is not None:
            a, b, _, _ = InkWord.span(widget);p.fillRect(a, widget.height() - MARK, b - a, MARK, QColor(colour))
        p.end()


def band_line(host):
    """The height of a line of band lettering, measured from a band word (the interface's control size)."""
    sizes = getattr(getattr(host, 'console', None), 'sizes', None)
    if sizes:return sizes[0].fontMetrics().height()
    from PySide6.QtGui import QFont, QFontMetrics
    from .shell2 import SANS, scale_of
    font = QFont(SANS);font.setPixelSize(max(10, round(16 * scale_of(host))))
    return QFontMetrics(font).height()


def owner_width(host):
    """The owner's width for both panes: the last drag or Workspace setting, else the saved session's width."""
    bar = getattr(host, 'type_bar', None)
    return getattr(bar, 'pane_owner', None) if bar is not None else None


def needs(host, d=None):
    """(least, whole, centre): what both band slots and both panes need (least: primary words whole, quiet words at their
    elided minimum; whole: every word whole), and what the workspace's own content needs."""
    from .shell2 import scale_of
    s = scale_of(host);least = whole = 0
    for part in (getattr(host, 'type_bar', None), getattr(getattr(host, 'shell2', None), 'top', None)):
        if part is not None and hasattr(part, 'slot_needs'):
            l, w = part.slot_needs(s, d);least = max(least, l);whole = max(whole, w)
    for dock in (getattr(host, 'nav_dock', None), getattr(host, 'sim_dock', None)):
        if dock is not None and dock.widget() is not None:
            content = dock.widget().minimumSizeHint().width();least = max(least, content);whole = max(whole, content)
    central = host.centralWidget()
    return least, whole, central.minimumSizeHint().width() if central is not None else 0


def _fixed(widget, width=None, height=None):
    """Fix a widget's width or height, touching it only when it changes (each change asks the window for a new layout)."""
    if widget is None:return
    if width is not None and (widget.minimumWidth() != width or widget.maximumWidth() != width):widget.setFixedWidth(width)
    if height is not None and (widget.minimumHeight() != height or widget.maximumHeight() != height):widget.setFixedHeight(height)


def apply(host, owner=None):
    """Lay the desk out now: one width for both panes, both bands' height, and every band word in its column. Returns the
    Desk."""
    from .shell2 import scale_of
    s = scale_of(host);line = band_line(host);owner = owner_width(host) if owner is None else owner
    least, whole, centre = needs(host)
    d = desk(host.width(), s, line, owner, least, whole, centre)
    fit = getattr(getattr(host, 'type_bar', None), 'fit_px', None)
    if fit is not None:  # D1-fix: the lower band's words take the size that keeps them whole in P; the band's height is theirs
        d = desk(host.width(), s, line_px(fit(d.pane, s)), owner, least, whole, centre)
    shell = getattr(host, 'shell2', None)
    side = getattr(host, 'sim_dock', None)
    evidence = 0
    worksheet = getattr(shell, 'worksheet', None) is not None
    if worksheet and side is not None and not side.isHidden():
        # The reference worksheet gives a quarter of the desk to the evidence rail.
        evidence = min(max(0, round(d.width * .25) - d.pane), max(0, d.workspace - max(centre, scaled(732, s))))
        d = d._replace(right=d.right - evidence, workspace=d.workspace - evidence)
    _fixed(getattr(host, 'nav_dock', None), width=d.pane)
    _fixed(side, width=d.pane + evidence)
    top = getattr(getattr(host, 'shell2', None), 'top', None);bar = getattr(host, 'type_bar', None)
    art = getattr(getattr(host, 'session', None), 'state', {}).get('desk_art', 'illustrated')
    strip = scaled(116, s) if worksheet and art == 'illustrated' and d.width >= 1250 and host.height() >= 820 else 0
    for widget in (top, getattr(host, 'ribbon_dock', None)):_fixed(widget, height=d.band + strip)
    for widget in (bar, getattr(host, 'type_dock', None)):_fixed(widget, height=d.band)
    if host.layout() is not None:host.layout().activate()
    host.desk = d
    if top is not None and hasattr(top, 'place'):
        top.place(d);plan = getattr(top, 'plan', None)
        if plan is not None and plan[4] is not None:d = d._replace(line=plan[4]);host.desk = d  # the line takes the menus' own inset
    if bar is not None and hasattr(bar, 'place'):bar.place(d)
    from . import pane_qt
    pane_qt.place(host, d)  # HATCH DESK D1b: both panes' tabs, contents and feet on the same numbers
    return d


def pane_at(host, point):
    """'left' or 'right' when point (window coordinates) is on the separator beside that pane (with the few pixels around
    it that QMainWindow's own separator handle takes), else None."""
    d = getattr(host, 'desk', None);nav = getattr(host, 'nav_dock', None)
    if d is None or nav is None or not nav.isVisible():return None
    top, bottom = nav.geometry().top(), nav.geometry().bottom()
    if not top <= point.y() <= bottom:return None
    x = point.x()
    if d.pane - 4 <= x <= d.pane + SEPARATOR + 3:return 'left'
    side = getattr(host, 'sim_dock', None)
    if side is not None and side.isVisible() and d.right - 4 <= x <= d.right + SEPARATOR + 3:return 'right'
    return None


def _event_point(event):
    pos = event.position() if hasattr(event, 'position') else event.pos()
    return pos.toPoint() if hasattr(pos, 'toPoint') else pos


class MirroredDrag:
    """The owner's hand on either separator moves both: dragging the left pane's edge by dx makes both panes P + dx, the
    right pane's edge by dx makes both P - dx, so they stay equal through the drag. Both panes are fixed at P (Qt's own
    separator move cannot run), so the drag is read from the window's mouse events here; the width is the owner's from the
    release on (TypeBar.pane_owner, saved with the session). Never under what the slots need, never so wide the workspace
    falls under its floor."""

    def __init__(self, host):
        from PySide6.QtCore import QObject
        class Filter(QObject):
            def eventFilter(inner, obj, event):return self.event(obj, event)
        self.host = host;self.side = None;self.start = None;self.resizing = False;self.saved = None
        self.filter = Filter(host);host.installEventFilter(self.filter)

    def hover(self, on):
        """The separators keep their resize cursor (D1-fix: with both docks fixed Qt no longer offers it, so the drag could
        not be found): over either separator the window shows the horizontal resize cursor, elsewhere its own pointer again."""
        from PySide6.QtCore import Qt
        if bool(on) == self.resizing:return
        self.resizing = bool(on);host = self.host
        if on:self.saved = host.cursor() if host.testAttribute(Qt.WA_SetCursor) else None;host.setCursor(Qt.SplitHCursor)
        elif self.saved is not None:host.setCursor(self.saved)
        else:host.unsetCursor()

    def event(self, obj, event):
        from PySide6.QtCore import QEvent, Qt
        host = self.host
        if obj is not host:return False
        kind = event.type()
        if kind in (QEvent.HoverMove, QEvent.HoverEnter, QEvent.MouseMove) and self.side is None:
            self.hover(pane_at(host, _event_point(event)) is not None)
            if kind != QEvent.MouseMove:return False
        if kind in (QEvent.HoverLeave, QEvent.Leave) and self.side is None:self.hover(False);return False
        if kind == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            side = pane_at(host, _event_point(event))
            if side is None:return False
            self.side = side;self.start = (_event_point(event).x(), host.desk.pane);self.hover(True);return True
        if kind == QEvent.MouseMove and self.side is not None:
            self.move(_event_point(event).x());return True
        if kind == QEvent.MouseButtonRelease and self.side is not None:
            self.move(_event_point(event).x());self.side = None;self.hover(pane_at(host, _event_point(event)) is not None);return True
        return False

    def move(self, x):
        from .shell2 import scale_of
        host = self.host;x0, p0 = self.start;dx = x - x0
        want = p0 + dx if self.side == 'left' else p0 - dx
        least, whole, centre = needs(host);s = scale_of(host)
        room = (host.width() - 2 * SEPARATOR - max(centre_floor(s), centre)) // 2
        low = max(least, min(whole, room))
        want = max(low, min(int(want), room, SAVED[1]))
        bar = getattr(host, 'type_bar', None)
        if bar is not None:bar.pane_owner = want;bar.owner = {host.nav_dock:want, host.sim_dock:want}
        apply(host, owner=want)
