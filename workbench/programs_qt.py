"""The cat's programs list, and the desk's two launch menus' one design (HATCH DESK D2; the owner's brief of 2026-11-06: "The
cat opens a flat, predictable list of available programs and capabilities, like the Programs folder in a Start menu. Give each
entry one plain name and one small graphite icon. Think of it as the cat's toy box and my toolbox.").

  DeskMenu      a popup on paper made of rows; the programs list (this module) and the System menu (system_menu_qt) are both
                one, so they share every number: the row height, the icon column, the margins, the word sizes and the width
                rule; placed as point-mirror images (place): the programs list opens upward from the lower left, its left
                edge the band's inset from the window's left edge and its foot on the lower band's top; the System menu opens
                downward from the upper right, its right edge the same inset from the window's right edge and its top on the
                head band's foot. Both are as wide as the panes' content column (P less an inset each side), or as their
                widest row needs when that is more, one width for both (menu_width). Keyboard: Up and Down (wrapping), Home,
                End, Page Up and Down, Return, Enter and Space, Escape (focus back where it was), F1 (the highlighted row's
                descriptor into the writing line's note), and type-to-select (letters jump to the next row starting with
                them).
  MenuRow       one row: a small graphite icon in the icon column, one plain name, and a quiet caption at the right (a status
                in print; a menu's small caption in the Paper script, by the quiet-script rule).
  ProgramsList  the installed programs and capabilities that sat in the Hatch groups (explore.VIEWS through the ledger.explore
                read), one plain name each (PLAIN), sorted A to Z, then Explore the workshop. Opening an entry is navigation
                through the existing view factories (explore_qt.open_instrument); nothing is dispatched but the existing
                reads. Creation (New Idea, New Project: the Work menu), recent work, services and leaving are not in it.
"""
from __future__ import annotations
import time
from collections import namedtuple
from PySide6.QtCore import QEvent, QPoint, QPointF, QRect, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QAbstractButton, QApplication, QFrame, QScrollArea, QVBoxLayout, QWidget

# The menu's numbers at 14 pt, scaled with the interface (desk_qt.scaled: up to 1.4 for sizes that are not text; the words follow
# the interface size with no ceiling, as every word on the desk).
ICON = 16        # the small graphite icon, px square
ICON_GAP = 10    # from the icon to the word: the icon column is ICON + ICON_GAP
PAD = 12         # a row's inner padding at each end
ROW_PAD = 2      # above and below a row's line of text
MARGIN = 6       # the frame's room above the first row and below the last
CAPTION_GAP = 14 # the least room between a word and its caption
RULE = 9         # a hairline between groups, with its air
CAPTION = 13     # a caption's print size at 14 pt
Metrics = namedtuple('Metrics', 'scale px caption_px script_px line row icon icon_col pad margin caption_gap rule')
"""px: the words' size (the head menus', desk_qt.menu_px); caption_px and script_px: a caption in print and in the script;
line: the words' line height; row: every row's height; icon: the icon's size; icon_col: from a row's padding to its word (the
icon and its gap); pad, margin, caption_gap, rule: as above, scaled."""


def metrics(host):
    """The one set of numbers both menus use, at the host's interface size."""
    import math
    from .desk_qt import menu_px, scaled
    from .shell2 import SANS, scale_of
    s = scale_of(host);px = menu_px(s);font = QFont(SANS);font.setPixelSize(px)
    line = math.ceil(QFontMetricsF(font).height());icon = scaled(ICON, s)
    caption_px = max(10, round(CAPTION * s));script_px = round(max(caption_px, 15 * s) * 1.3)
    return Metrics(s, px, caption_px, script_px, line, max(line, icon) + 2 * scaled(ROW_PAD, s), icon, icon + scaled(ICON_GAP, s),
                   scaled(PAD, s), scaled(MARGIN, s), scaled(CAPTION_GAP, s), scaled(RULE, s))


def word_font(m, size=None):
    from .shell2 import SANS
    font = QFont(SANS);font.setPixelSize(int(size or m.px));return font


def caption_font(m, script=False):
    from PySide6.QtGui import QFontDatabase
    from .shell2 import SANS, SCRIPT, _script_ready
    if script and _script_ready():
        font = QFont(SCRIPT);font.setPixelSize(m.script_px);return font
    return word_font(m, m.caption_px)


def row_need(m, word, caption='', script=False):
    """The width a row needs: its padding, the icon column, its word and, when it has one, the gap and its caption."""
    import math
    need = 2 * m.pad + m.icon_col + QFontMetricsF(word_font(m)).horizontalAdvance(word)
    if caption:need += m.caption_gap + QFontMetricsF(caption_font(m, script)).horizontalAdvance(caption)
    return math.ceil(need)


def column(host):
    """The panes' content column: both panes are P wide and their contents an inset in from each side."""
    d = getattr(host, 'desk', None)
    if d is None:
        from .desk_qt import default_pane, inset
        from .shell2 import scale_of
        s = scale_of(host);return default_pane(s) - 2 * inset(s)
    return d.pane - 2 * d.inset


def menu_width(host):
    """Symmetry rule 6's width rule, one width for both menus: the panes' content column, or the widest row either menu can
    show when that is more (their words, their longest captions), never past the window's axis less an inset."""
    from .system_menu_qt import words_need
    m = metrics(host);need = max(column(host), programs_need(m), words_need(m))
    width = getattr(getattr(host, 'desk', None), 'width', None)
    if width:
        inset = host.desk.inset;need = min(need, width // 2 - inset)
    return int(need)


def room(host):
    """The most a menu may be tall: the window between the two bands (it never covers either band)."""
    head = getattr(host, 'ribbon_dock', None);lower = getattr(host, 'type_dock', None)
    used = (head.height() if head is not None and head.isVisible() else 0) + (lower.height() if lower is not None and lower.isVisible() else 0)
    return max(120, host.height() - used) if hasattr(host, 'height') else 600


def place(host, menu, side, anchor=None, height=None):
    """Symmetry rule 6: the menu's geometry in global coordinates. 'lower-left' (the programs list): its left edge the band's
    inset from the window's left edge, its foot on the lower band's top, opening upward. 'upper-right' (the System menu): its
    right edge the band's inset from the window's right edge, its top on the head band's foot, opening downward. Point-mirror
    images: the same inset from the side edge, the same band's height from the top or bottom edge. Without a desk (a bare
    host in tests) the menu sits against its anchor instead."""
    width = menu_width(host);height = min(menu.sizeHint().height() if height is None else int(height), room(host))
    d = getattr(host, 'desk', None)
    if d is None or not hasattr(host, 'mapToGlobal'):
        origin = anchor.mapToGlobal(QPoint(0, 0)) if anchor is not None else QPoint(0, 0)
        if side == 'lower-left':return QRect(origin.x(), origin.y() - height, width, height)
        return QRect(origin.x() + (anchor.width() if anchor is not None else 0) - width, origin.y() + (anchor.height() if anchor is not None else 0), width, height)
    top_left = host.mapToGlobal(QPoint(0, 0));W, H = host.width(), host.height()
    if side == 'lower-left':
        lower = host.type_dock.height() if getattr(host, 'type_dock', None) is not None else d.band
        return QRect(top_left.x() + d.inset, top_left.y() + H - lower - height, width, height)
    head = host.ribbon_dock.height() if getattr(host, 'ribbon_dock', None) is not None else d.band
    if side == 'upper-programs':
        control = getattr(getattr(getattr(host, 'shell2', None), 'top', None), 'programs', anchor)
        x = control.mapToGlobal(QPoint(0, 0)).x() if control is not None else top_left.x() + d.inset
        x = max(top_left.x() + d.inset, min(x, top_left.x() + W - d.inset - width))
        return QRect(x, top_left.y() + head, width, height)
    return QRect(top_left.x() + W - d.inset - width, top_left.y() + head, width, height)


# The small graphite icons ------------------------------------------------------------------------------------------------------
# Drawn here on an 18-unit grid with one line weight, so they stay sharp at any size and inside the palette (chain_icons' way).

def _icon_paths(key):
    """(strokes, fills) for one icon on the 18-unit grid: lists of QPainterPath."""
    strokes, fills = [], []
    def path(*points, close=False):
        p = QPainterPath(QPointF(*points[0]))
        for pt in points[1:]:p.lineTo(QPointF(*pt))
        if close:p.closeSubpath()
        strokes.append(p);return p
    def rect(x, y, w, h, r=1.6):
        p = QPainterPath();p.addRoundedRect(QRectF(x, y, w, h), r, r);strokes.append(p);return p
    def circle(x, y, r, fill=False):
        p = QPainterPath();p.addEllipse(QPointF(x, y), r, r);(fills if fill else strokes).append(p);return p
    def curve(start, *segments):
        p = QPainterPath(QPointF(*start))
        for c, e in segments:p.quadTo(QPointF(*c), QPointF(*e))
        strokes.append(p);return p
    if key == 'projects':  # a bulb: an idea
        curve((6.5, 11.5), ((3.5, 9), (4.5, 5.5)), ((6, 2.5), (9, 2.5)), ((12, 2.5), (13.5, 5.5)), ((14.5, 9), (11.5, 11.5)));path((6.5, 11.5), (6.5, 13.5), (11.5, 13.5), (11.5, 11.5))
        path((7, 15.8), (11, 15.8))
    elif key == 'inquiries':  # a question in a circle
        circle(9, 9, 7);curve((6.6, 7), ((6.8, 4.6), (9, 4.6)), ((11.4, 4.6), (11.4, 6.8)), ((11.4, 8.4), (9, 9.4)));path((9, 9.4), (9, 10.6));circle(9, 13, 0.9, True)
    elif key == 'calculate':  # a calculator
        rect(4, 2, 10, 14);rect(6, 4, 6, 3, 0.6)
        for x in (6.6, 9, 11.4):
            for y in (10, 13):circle(x, y, 0.8, True)
    elif key == 'laboratory':  # a flask
        path((7, 2.5), (7, 7.5), (3, 15), (15, 15), (11, 7.5), (11, 2.5));path((6, 2.5), (12, 2.5));path((5, 11.5), (13, 11.5))
    elif key == 'methods':  # a sigma
        path((13.5, 3.5), (4.5, 3.5), (9.5, 9), (4.5, 14.5), (13.5, 14.5))
    elif key == 'tools':  # an atlas: a folded map
        path((2.5, 4.5), (6.5, 3), (11.5, 4.5), (15.5, 3), (15.5, 13.5), (11.5, 15), (6.5, 13.5), (2.5, 15), close=True);path((6.5, 3), (6.5, 13.5));path((11.5, 4.5), (11.5, 15))
    elif key == 'office':  # an incoming tray
        path((2.5, 9.5), (5, 4), (13, 4), (15.5, 9.5));rect(2.5, 9.5, 13, 5.5, 1);path((2.5, 9.5), (6.5, 9.5), (7.5, 11.5), (10.5, 11.5), (11.5, 9.5), (15.5, 9.5))
    elif key == 'files':  # a folder
        path((2.5, 5), (2.5, 14.5), (15.5, 14.5), (15.5, 6.5), (8.5, 6.5), (7, 4.5), (3, 4.5), close=True)
    elif key == 'documents':  # a page with lines
        path((4, 2.5), (11, 2.5), (14, 5.5), (14, 15.5), (4, 15.5), close=True);path((11, 2.5), (11, 5.5), (14, 5.5))
        for y in (8.5, 11, 13.5):path((6.5, y), (11.5, y))
    elif key == 'investigations':  # a magnifier over a line of work
        circle(7.5, 7.5, 4.8);path((11, 11), (15.5, 15.5))
    elif key == 'agenda':  # an ordered list
        for y in (4.5, 9, 13.5):circle(4, y, 1, True);path((7, y), (15, y))
    elif key == 'brain':  # a chip: the local model
        rect(5, 5, 8, 8, 1)
        for v in (7, 11):
            path((v, 2.5), (v, 5));path((v, 13), (v, 15.5));path((2.5, v), (5, v));path((13, v), (15.5, v))
    elif key == 'knowledge':  # books on a shelf: sources
        rect(3, 3.5, 3.5, 12, 0.6);rect(7.5, 3.5, 3.5, 12, 0.6);path((12, 4.5), (15.3, 3.7), (15.8, 15), (13, 15.6), close=True)
    elif key == 'references':  # a book with a bookmark
        path((4, 3), (13.5, 3), (13.5, 15.5), (4, 15.5), close=True);path((6, 3), (6, 15.5));path((9, 3), (9, 8), (10.5, 6.8), (12, 8), (12, 3))
    elif key == 'memory':  # a bookmark ribbon: what was kept
        path((5, 2.5), (13, 2.5), (13, 15.5), (9, 12), (5, 15.5), close=True)
    elif key == 'settings':  # sliders
        for y, x in ((4.5, 11), (9, 6), (13.5, 12)):path((3, y), (15, y));circle(x, y, 1.6, True)
    elif key == 'activity':  # a trail of receipts
        path((4, 2.5), (14, 2.5), (14, 15.5), (12.3, 14.2), (10.6, 15.5), (9, 14.2), (7.4, 15.5), (5.7, 14.2), (4, 15.5), close=True);path((6.5, 6), (11.5, 6));path((6.5, 9.5), (11.5, 9.5))
    elif key == 'mail':
        rect(2.5, 4.5, 13, 9, 0.5);path((2.5, 5), (9, 10), (15.5, 5))
    elif key == 'blender':
        path((9, 2.5), (15, 6), (15, 12.5), (9, 16), (3, 12.5), (3, 6), close=True)
        path((3, 6), (9, 9.5), (15, 6));path((9, 9.5), (9, 16))
    elif key == 'godot':
        rect(3, 3.5, 12, 11, 1);path((7, 6), (12, 9), (7, 12), close=True)
    elif key == 'transfer':
        path((2.5, 6), (15.5, 6), (12.5, 3));path((15.5, 12), (2.5, 12), (5.5, 15))
    elif key == 'cartridge':
        rect(4, 2.5, 10, 13, 0.6);rect(6, 5, 6, 4, 0.3);path((6, 12), (12, 12))
    elif key == 'inkscape':
        path((3, 15), (5, 8), (12, 2.5), (15, 5.5), (9, 13), (3, 15));path((5, 8), (9, 13))
    elif key == 'media':
        path((2.5, 9), (5, 9), (7, 4), (9.5, 14), (12, 6.5), (14, 9), (15.5, 9))
    elif key == 'freecad':
        path((3, 4), (7, 4), (7, 11), (15, 11), (15, 15), (3, 15), close=True)
        path((9, 4), (15, 4), (15, 9));path((12, 4), (12, 6))
    elif key == 'print':
        rect(3, 7, 12, 6, 0.6);path((5, 7), (5, 3), (13, 3), (13, 7))
        path((5, 11), (5, 15), (13, 15), (13, 11));path((7, 13), (11, 13))
    elif key == 'delivery':
        rect(3, 4, 12, 11, 0.6);path((7, 4), (7, 9), (11, 9), (11, 4))
    elif key == 'kicad':  # a board with traces
        rect(2.5, 3.5, 13, 11, 1);path((5, 7), (8.5, 7), (10.5, 9), (13, 9));path((5, 11.5), (13, 11.5));circle(5, 7, 0.9, True);circle(13, 9, 0.9, True);circle(5, 11.5, 0.9, True)
    elif key == 'kibot':  # outputs: stacked sheets
        path((3, 6), (9, 3), (15, 6), (9, 9), close=True);path((3, 9.5), (9, 12.5), (15, 9.5));path((3, 13), (9, 16), (15, 13))
    elif key == 'spice':  # a wave
        curve((2.5, 9), ((4.5, 3), (6.5, 9)), ((8.5, 15), (10.5, 9)), ((12.5, 3), (15.5, 9)))
    elif key == 'yosys':  # a gate
        p = QPainterPath(QPointF(5, 4));p.lineTo(9, 4);p.arcTo(QRectF(4, 4, 10, 10), 90, -180);p.lineTo(5, 14);p.closeSubpath();strokes.append(p)
        path((2.5, 7), (5, 7));path((2.5, 11), (5, 11));path((14, 9), (15.8, 9))
    elif key == 'fpga':  # a grid of cells
        rect(3, 3, 12, 12, 1);path((7, 3), (7, 15));path((11, 3), (11, 15));path((3, 7), (15, 7));path((3, 11), (15, 11))
    elif key == 'hdl':  # a square wave
        path((2.5, 13), (5.5, 13), (5.5, 5), (9.5, 5), (9.5, 13), (12.5, 13), (12.5, 5), (15.5, 5))
    elif key == 'explore':  # a compass rose: the workshop to explore
        circle(9, 9, 6.8);path((9, 4.5), (10.6, 9), (9, 13.5), (7.4, 9), close=True)
    elif key == 'game':  # a pad
        path((5.5, 6), (12.5, 6));curve((5.5, 6), ((2, 6), (2.5, 11)), ((3, 14), (6, 12.5)), ((7.5, 11), (9, 11)), ((10.5, 11), (12, 12.5)), ((15, 14), (15.5, 11)), ((16, 6), (12.5, 6)))
        path((5, 8.5), (8, 8.5));path((6.5, 7), (6.5, 10));circle(12, 8.6, 0.9, True)
    elif key == 'stop':  # a square: stop
        rect(4, 4, 10, 10, 1.2)
    elif key == 'services':  # stacked bars: the services
        rect(3, 3, 12, 3.5, 0.8);rect(3, 7.25, 12, 3.5, 0.8);rect(3, 11.5, 12, 3.5, 0.8);circle(5.3, 4.75, 0.7, True);circle(5.3, 9, 0.7, True);circle(5.3, 13.25, 0.7, True)
    elif key == 'logout':  # a door and the way out
        path((10, 4.5), (10, 2.5), (3.5, 2.5), (3.5, 15.5), (10, 15.5), (10, 13.5));path((7, 9), (15.5, 9));path((13, 6.5), (15.5, 9), (13, 11.5))
    elif key == 'leave':  # out of the window: back to the system
        rect(2.5, 3.5, 9.5, 11, 1);path((8, 9), (15.5, 9));path((13, 6.5), (15.5, 9), (13, 11.5))
    elif key == 'restart':  # a turning arrow
        p = QPainterPath();p.arcMoveTo(QRectF(3, 3, 12, 12), 60);p.arcTo(QRectF(3, 3, 12, 12), 60, 300);strokes.append(p);path((14.2, 2.8), (12, 4.2), (14.6, 6.6))
    elif key == 'shutdown':  # the power mark
        p = QPainterPath();p.arcMoveTo(QRectF(3, 3.5, 12, 12), 55);p.arcTo(QRectF(3, 3.5, 12, 12), 55, 290);strokes.append(p);path((9, 2), (9, 8.5))
    elif key == 'unavailable':  # a small ring with a bar
        circle(9, 9, 6);path((5, 13), (13, 5))
    else:  # any other program: a window
        rect(3, 3.5, 12, 11, 1.2);path((3, 6.5), (15, 6.5))
    return strokes, fills


def paint_icon(p, rect, key, colour):
    """One icon in rect (square), in colour, one line weight (1.5 units on the 18-unit grid, at least one device pixel)."""
    import math
    strokes, fills = _icon_paths(key);s = min(rect.width(), rect.height()) / 18.0
    k = s * (math.sqrt(abs(p.deviceTransform().determinant())) or 1.0)
    p.save();p.setRenderHint(QPainter.Antialiasing);p.translate(rect.x() + (rect.width() - 18 * s) / 2, rect.y() + (rect.height() - 18 * s) / 2);p.scale(s, s)
    pen = QPen(QColor(colour), max(1.5, 1.0 / k if k else 1.5), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin);p.setPen(pen);p.setBrush(Qt.NoBrush)
    for path in strokes:p.drawPath(path)
    p.setPen(Qt.NoPen);p.setBrush(QColor(colour))
    for path in fills:p.drawPath(path)
    p.restore()


# One row --------------------------------------------------------------------------------------------------------------------------

class MenuRow(QAbstractButton):
    """One row of a desk menu: the icon in the icon column, the plain word, and a caption at the right end (print: a status or a
    scope; the script: a menu's small caption you may skip, by the quiet-script rule). The row under the pointer or with keyboard
    focus is washed in the menus' pencil wash (the theme's QMenu highlight); a disabled row is quiet. When a QAction backs it,
    the row follows the action's words, tooltip and enabled state and triggers it."""
    def __init__(self, menu, word, icon='', caption='', script=False, action=None, callback=None):
        super().__init__(menu.page);self.menu = menu;self.icon_key = icon;self.word = word;self.caption = caption;self.script = bool(script)
        self.unavailable = ''  # D2-fix: the reason a row cannot act now; it stays in the keyboard's order, quiet, and says why when chosen
        self.action = action;self.callback = callback;self.setFocusPolicy(Qt.StrongFocus);self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover, True);self.setMouseTracking(True);self.setProperty('deskMenuRow', True)
        self.setText(word);self.clicked.connect(self.choose);self.refont()
        if action is not None:action.changed.connect(self.follow);self.follow()
        self.describe()

    def refont(self):
        """The row's own font is the one it draws its word in (the menu's sheet sets it: readers and checks measure with it)."""
        self.setProperty('deskMenuRow', True)

    def follow(self):
        """The backing action's words, tooltip and enabled state."""
        a = self.action
        word = a.text().replace('&&', '&')
        if word != self.word:self.word = word;self.setText(word);self.updateGeometry()
        self.setEnabled(a.isEnabled());self.setToolTip(a.toolTip());caption = a.property('caption')
        if caption is not None and str(caption) != self.caption:self.caption = str(caption)
        self.describe();self.update()

    def set_caption(self, caption, script=None):
        if script is not None:self.script = bool(script)
        if caption != self.caption:self.caption = caption;self.describe();self.update()

    def describe(self):
        """The accessible description: the caption and the tooltip's first line; for an unavailable row also its whole reason
        (what a pointer reads in the tooltip, a screen reader and F1 read too)."""
        lines = (self.toolTip() or '').split('\n');why = ('Unavailable: ' + self.unavailable) if self.unavailable else ''
        self.setAccessibleName(self.word)
        self.setAccessibleDescription(' · '.join(part for part in (self.caption, lines[0], why) if part))

    def set_unavailable(self, reason):
        """Mark the row unavailable with its reason ('' makes it available): it stays enabled and in the keyboard's order (so F1
        and a screen reader reach the reason), its ink goes quiet, and choosing it lets its callback say why (nothing else)."""
        reason = str(reason or '')
        if reason != self.unavailable:self.unavailable = reason;self.describe();self.update()

    def choose(self):
        """Close the menu first (what opens is what you see), then act."""
        if not self.isEnabled():return
        self.menu.chosen(self)
        if self.action is not None:QTimer.singleShot(0, self.action.trigger)
        elif self.callback is not None:QTimer.singleShot(0, self.callback)

    def m(self):return self.menu.m

    def sizeHint(self):
        import math
        m = self.m();need = row_need(m, self.word, self.caption, self.script)
        own = math.ceil(2 * m.pad + m.icon_col + self.fontMetrics().horizontalAdvance(self.word) + (m.caption_gap + QFontMetricsF(caption_font(m, self.script)).horizontalAdvance(self.caption) if self.caption else 0))
        return QSize(max(need, own), m.row)  # its own font (the menu's sheet) as readers measure it, and the rule's

    def minimumSizeHint(self):return QSize(0, self.m().row)

    def active(self):return self.isEnabled() and (self.hasFocus() or (self.underMouse() and self.menu.pointer_moved))

    def icon_rect(self):
        m = self.m();return QRectF(m.pad, (self.height() - m.icon) / 2.0, m.icon, m.icon)

    def word_x(self):
        m = self.m();return m.pad + m.icon_col

    def caption_rect(self):
        """The caption's box, right-aligned at the row's padding (empty when there is none)."""
        if not self.caption:return QRectF()
        m = self.m();w = QFontMetricsF(caption_font(m, self.script)).horizontalAdvance(self.caption)
        return QRectF(self.width() - m.pad - w, 0, w, self.height())

    def enterEvent(self, event):
        if self.menu.pointer(event.globalPosition().toPoint()) and self.isEnabled() and not self.hasFocus():
            self.setFocus(Qt.MouseFocusReason)  # the pointer's row is the active row, once the pointer moves
        self.update();super().enterEvent(event)

    def mouseMoveEvent(self, event):
        if self.menu.pointer(event.globalPosition().toPoint()) and self.isEnabled() and not self.hasFocus():self.setFocus(Qt.MouseFocusReason);self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self.update();super().leaveEvent(event)

    def focusInEvent(self, event):
        self.menu.ensure_visible(self);self.update();super().focusInEvent(event)

    def focusOutEvent(self, event):
        self.update();super().focusOutEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Select) and not event.isAutoRepeat():self.click();return
        super().keyPressEvent(event)

    def paintEvent(self, event):
        from .shell2 import AMBER_SOFT, QUIET, TEXT
        m = self.m();p = QPainter(self);p.setRenderHint(QPainter.TextAntialiasing)
        if self.active():p.fillRect(self.rect(), QColor(AMBER_SOFT))
        ink = QColor(TEXT if self.isEnabled() and not self.unavailable else QUIET)
        paint_icon(p, self.icon_rect(), self.icon_key or 'window', ink)
        p.setFont(self.font());p.setPen(ink);p.drawText(QRectF(self.word_x(), 0, self.width() - self.word_x() - m.pad, self.height()), Qt.AlignLeft | Qt.AlignVCenter, self.word)
        if self.caption:
            p.setFont(caption_font(m, self.script));p.setPen(QColor(QUIET));p.drawText(self.caption_rect(), Qt.AlignRight | Qt.AlignVCenter, self.caption)
        p.end()


class Rule(QWidget):
    """A hairline between two groups of rows, with its air (the menus' one rule height)."""
    def __init__(self, menu, strong=False):
        super().__init__(menu.page);self.menu = menu;self.strong = strong;self.setFocusPolicy(Qt.NoFocus)

    def sizeHint(self):return QSize(0, self.menu.m.rule * (2 if self.strong else 1))

    def minimumSizeHint(self):return self.sizeHint()

    def paintEvent(self, event):
        from .shell2 import LINE, LINE_STRONG
        p = QPainter(self);y = self.height() // 2;p.fillRect(QRect(self.menu.m.pad, y, self.width() - 2 * self.menu.m.pad, 1), QColor(LINE_STRONG if self.strong else LINE));p.end()


class Margin(QWidget):
    """The room above a menu's first part or below its last: as tall as the menu's margin, read from its numbers."""
    def __init__(self, menu):
        super().__init__(menu.page);self.menu = menu;self.setFocusPolicy(Qt.NoFocus)

    def sizeHint(self):return QSize(0, self.menu.m.margin)

    def minimumSizeHint(self):return self.sizeHint()


class Caption(QWidget):
    """A menu's small caption you may skip, in the Paper script (print with View ▸ Pleasantries in script off), at the menu's
    far end from its anchor: the programs list's at its top, the System menu's at its foot (point-mirror images). One height
    in both menus: the script's line."""
    def __init__(self, menu, words):
        super().__init__(menu.page);self.menu = menu;self.words = words;self.setFocusPolicy(Qt.NoFocus)
        self.setAccessibleName(words);self.setProperty('quiet_caption', True)

    def font_(self):
        from .shell2 import _script_ready
        return caption_font(self.menu.m, script=_script_ready())

    def scripted(self):
        from .shell2 import SCRIPT
        return self.font_().family() == SCRIPT

    def sizeHint(self):
        import math
        from .shell2 import script_room
        m = self.menu.m;fm = QFontMetricsF(caption_font(m, True));room = script_room(self.words, m.script_px)
        return QSize(row_need(m, self.words, '', True), math.ceil(fm.height()) + room[2] + m.margin)

    def minimumSizeHint(self):return QSize(0, self.sizeHint().height())

    def paintEvent(self, event):
        from .shell2 import QUIET
        m = self.menu.m;p = QPainter(self);p.setRenderHint(QPainter.TextAntialiasing);p.setRenderHint(QPainter.Antialiasing)
        p.setFont(self.font_());p.setPen(QColor(QUIET))
        p.drawText(QRectF(m.pad + m.icon_col, 0, self.width() - 2 * m.pad - m.icon_col, self.height()), Qt.AlignLeft | Qt.AlignVCenter, self.words);p.end()


# The menu ---------------------------------------------------------------------------------------------------------------------

class DeskMenu(QFrame):
    """A launch menu on paper: rows in one column (scrolled when the window between the bands is too short), placed by `place`
    on `side`, with the keyboard of a menu and type-to-select. Subclasses fill self.page's layout with MenuRow, Rule and their
    own sections. Signals: shown(bool)."""
    shown = Signal(bool)
    SEARCH_MS = 1000  # type-to-select: letters typed within this long make one prefix

    def __init__(self, host, anchor, side, name):
        super().__init__(host if isinstance(host, QWidget) else None, Qt.Popup)
        self.host = host;self.anchor = anchor;self.side = side;self.m = metrics(host);self.typed = '';self.typed_at = 0.0;self.return_focus = None
        self.pointer_at = None;self.pointer_moved = False  # where the pointer was first seen in this opening; whether it has moved since
        self.setObjectName(name);self.setAccessibleName(name);self.setFocusPolicy(Qt.StrongFocus);self.keyboard = False
        self.apply_style()
        outer = QVBoxLayout(self);outer.setContentsMargins(1, 1, 1, 1);outer.setSpacing(0)
        self.scroll = QScrollArea();self.scroll.setWidgetResizable(True);self.scroll.setFrameShape(QFrame.NoFrame);self.scroll.setViewportMargins(0, 0, 0, 0)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff);self.scroll.setFocusPolicy(Qt.NoFocus);outer.addWidget(self.scroll)
        self.page = QWidget();self.page.setObjectName(name + 'Page');self.scroll.setWidget(self.page)
        self.box = QVBoxLayout(self.page);self.box.setSpacing(0);self.box.setContentsMargins(0, 0, 0, 0)
        self.top_margin = Margin(self);self.box.addWidget(self.top_margin)  # the menu's margins are widgets: always the numbers' own
        self.bottom_margin = Margin(self)  # added last by end_rows()
        if QApplication.instance() is not None:QApplication.instance().installEventFilter(self)  # the menu's keys, wherever focus is in it

    def apply_style(self):
        """Paper with a hairline; the rows' words in the menus' size (this sheet is nearer than the window's, so it wins)."""
        from .shell2 import CARD, LINE, SANS
        name = self.objectName()
        self.setStyleSheet('QFrame#%s {background:%s;border:1px solid %s;} QScrollArea, QScrollArea > QWidget > QWidget {background:transparent;border:0;} '
                           'QAbstractButton[deskMenuRow="true"] {font-family:"%s";font-size:%dpx;font-weight:400;}' % (name, CARD, LINE, SANS, self.m.px))

    def restyle_margins(self):
        """The room above the first row and below the last: two spacer widgets whose height is read from the menu's numbers
        each time the layout asks (stored layout margins were seen to go stale), the layout's own margins none."""
        for spacer in (self.top_margin, self.bottom_margin):spacer.updateGeometry()

    def end_rows(self):
        """Subclasses call this after their last row: the bottom margin goes last."""
        self.box.addWidget(self.bottom_margin)

    def items(self):
        """The menu's parts top to bottom, without its two margins."""
        out = []
        for i in range(self.box.count()):
            w = self.box.itemAt(i).widget()
            if w is not None and not isinstance(w, Margin):out.append(w)
        return out

    def margins(self):
        """(above the first part, below the last), as laid out."""
        m = self.box.contentsMargins();return self.top_margin.height() + m.top(), self.bottom_margin.height() + m.bottom()

    def restyle(self):
        """The numbers again at the interface's size (they are read when the menu opens)."""
        m = metrics(self.host)
        if m != self.m:
            self.m = m;self.restyle_margins();self.apply_style()
            for child in self.page.findChildren(QWidget):
                if hasattr(child, 'refont'):child.refont()
                child.updateGeometry()
            self.box.invalidate()

    def pointer(self, at):
        """Whether the pointer has moved since this opening (D2-fix, as a QMenu does): a pointer resting where the menu opens
        takes no row (the keyboard's first row keeps its focus; a resting pointer over an opening menu is not a choice); its first
        movement does. `at` is the pointer's global position in a row's enter or move event."""
        if not self.pointer_moved:
            if self.pointer_at is None:self.pointer_at = at
            elif at != self.pointer_at:self.pointer_moved = True
        return self.pointer_moved

    # what the keyboard visits, in order
    def focusables(self):
        out = []
        for w in self.page.findChildren(QWidget):
            if w.isVisibleTo(self) and w.isEnabled() and w.focusPolicy() & Qt.TabFocus and w.window() is self:out.append(w)
        out.sort(key=lambda w:(w.mapTo(self.page, QPoint(0, 0)).y(), w.mapTo(self.page, QPoint(0, 0)).x()))
        return out

    def rows(self):return [w for w in self.page.findChildren(MenuRow) if w.isVisibleTo(self)]

    def first(self):
        items = self.focusables();return items[0] if items else None

    def ensure_visible(self, widget):
        """The focused row in view; the first and the last bring the menu's own ends (the caption, the margin) with them."""
        items = self.focusables();bar = self.scroll.verticalScrollBar()
        if items and widget is items[0]:bar.setValue(0)
        elif items and widget is items[-1]:bar.setValue(bar.maximum())
        else:self.scroll.ensureWidgetVisible(widget, 0, self.m.margin)

    def step(self, direction, current=None):
        items = self.focusables()
        if not items:return None
        current = current if current is not None else QApplication.focusWidget()
        try:i = items.index(current)
        except ValueError:i = -1 if direction > 0 else 0
        target = items[(i + direction) % len(items)];target.setFocus(Qt.TabFocusReason);return target

    def jump(self, text):
        """Type-to-select: the next row whose word starts with the letters typed (one letter typed again cycles among the rows
        starting with it)."""
        now = time.monotonic()
        self.typed = (self.typed if now - self.typed_at <= self.SEARCH_MS / 1000.0 else '') + text.casefold();self.typed_at = now
        prefix = self.typed if len(set(self.typed)) > 1 else self.typed[0]
        rows = [r for r in self.rows() if r.isEnabled()]
        if not rows:return None
        current = QApplication.focusWidget();start = rows.index(current) + 1 if current in rows else 0
        if len(set(self.typed)) > 1 and current in rows and current.word.casefold().startswith(prefix):start -= 1  # still matching: stay
        for k in range(len(rows)):
            row = rows[(start + k) % len(rows)]
            if row.word.casefold().startswith(prefix):row.setFocus(Qt.TabFocusReason);return row
        return None

    def descriptor(self, widget):
        """One line for the writing line's note (F1): the row's words and its tooltip, as explore_qt.descriptor says them."""
        from .explore_qt import ROOM_NOTE
        word = getattr(widget, 'word', None) or (widget.text() if hasattr(widget, 'text') else '') or widget.accessibleName()
        lines = [line for line in (widget.toolTip() or '').split('\n') if line and line != ROOM_NOTE]
        caption = getattr(widget, 'caption', '')
        return word + ((' · ' + caption) if caption else '') + ((' — ' + ' · '.join(lines)) if lines else '')

    def eventFilter(self, obj, event):
        if not self.isVisible() or not isinstance(obj, QWidget) or (obj is not self and obj.window() is not self):return False
        kind = event.type()
        if kind == QEvent.ShortcutOverride and event.key() in (Qt.Key_F1, Qt.Key_Escape):event.accept();return True
        if kind != QEvent.KeyPress:return False
        key = event.key();focus = QApplication.focusWidget()
        from PySide6.QtWidgets import QAbstractSlider, QLineEdit
        if key == Qt.Key_Escape:self.close_menu();return True
        if key == Qt.Key_F1:
            if focus is not None and focus.window() is self and focus is not self:
                note = self.descriptor(focus);self.host.statusBar().showMessage(note, 12000) if hasattr(self.host, 'statusBar') else None
            return True
        if key in (Qt.Key_Down, Qt.Key_Up) and not isinstance(focus, QLineEdit):
            from PySide6.QtWidgets import QAbstractItemView
            if isinstance(focus, QAbstractItemView) and focus.model() is not None:  # inside a list the arrows choose its rows, then leave it
                row, count = focus.currentIndex().row(), focus.model().rowCount()
                if (key == Qt.Key_Down and row < count - 1) or (key == Qt.Key_Up and row > 0):return False
            self.step(1 if key == Qt.Key_Down else -1, focus);return True
        if key in (Qt.Key_Tab, Qt.Key_Backtab):self.step(1 if key == Qt.Key_Tab else -1, focus);return True
        if key in (Qt.Key_Home, Qt.Key_End) and not isinstance(focus, (QLineEdit, QAbstractSlider)):
            items = self.focusables()
            if items:(items[0] if key == Qt.Key_Home else items[-1]).setFocus(Qt.TabFocusReason)
            return True
        if key in (Qt.Key_PageDown, Qt.Key_PageUp) and not isinstance(focus, QAbstractSlider):
            for _ in range(max(1, self.scroll.viewport().height() // max(1, self.m.row) - 1)):self.step(1 if key == Qt.Key_PageDown else -1)
            return True
        text = event.text()
        if text and text.isprintable() and not text.isspace() and not (event.modifiers() & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier)) and not isinstance(focus, QLineEdit):
            self.jump(text);return True
        return False

    # opening and closing
    def fill(self):
        """Refill the rows (subclasses); called before each opening."""

    def open_menu(self, keyboard=False):
        """Fill, size and place the menu (Symmetry rule 6), show it, and on a keyboard opening put the first row under focus;
        on a pointer opening the menu itself holds focus and the first Down reaches the first row."""
        self.return_focus = QApplication.focusWidget();self.keyboard = bool(keyboard);self.pointer_at = None;self.pointer_moved = False
        self.restyle();self.restyle_margins();self.fill()
        width = menu_width(self.host);self.setFixedWidth(width);self.box.activate()
        rect = place(self.host, self, self.side, self.anchor);self.setFixedHeight(rect.height());self.setGeometry(rect)
        self.show();self.raise_();self.activateWindow()
        for _ in range(2):  # measured once shown: its words wrapped at the width they really have; the frame grows to them
            need = self.measured_height()
            if need == self.height() or self.height() >= room(self.host) and need > self.height():break
            rect = place(self.host, self, self.side, self.anchor, need);self.setFixedHeight(rect.height());self.setGeometry(rect)
        self.scroll.verticalScrollBar().setValue(0 if self.side in ('upper-right','upper-programs') else self.scroll.verticalScrollBar().maximum())
        first = self.first() if keyboard else None
        if first is not None:first.setFocus(Qt.TabFocusReason)
        else:self.setFocus(Qt.PopupFocusReason)
        return rect

    def measured_height(self):
        """The menu's height for all of its rows at the width its page has now (with no scroll bar), and the frame."""
        self.layout().activate();viewport = self.scroll.viewport()
        width = viewport.width() + (self.scroll.verticalScrollBar().width() if self.scroll.verticalScrollBar().isVisible() else 0)
        tall = self.page.heightForWidth(width) if self.page.hasHeightForWidth() else -1
        tall = max(tall, self.page.minimumSizeHint().height())
        return tall + (self.height() - viewport.height())

    def sizeHint(self):
        """The menu's whole height at its width (rows that wrap are measured at the width they will have), and the frame."""
        width = menu_width(self.host) - 2;self.box.activate()
        tall = self.box.heightForWidth(width) if self.box.hasHeightForWidth() else -1
        return QSize(width + 2, max(tall, self.page.sizeHint().height(), self.box.minimumSize().height()) + 2)

    def mousePressEvent(self, event):
        """A press outside closes the menu (a popup's rule); a press on its own anchor only closes it (no reopening)."""
        if not self.rect().contains(event.position().toPoint()) and self.anchor is not None:
            at = self.anchor.mapFromGlobal(event.globalPosition().toPoint())
            if self.anchor.rect().contains(at):self.setAttribute(Qt.WA_NoMouseReplay)
        super().mousePressEvent(event)

    def chosen(self, row):
        """A row was chosen: the menu closes first."""
        self.close_menu(restore=False)

    def close_menu(self, restore=True):
        if self.isVisible():self.hide()
        target = self.return_focus if restore else None
        if target is not None:
            try:target.setFocus(Qt.PopupFocusReason)
            except RuntimeError:pass

    def showEvent(self, event):
        super().showEvent(event);self.shown.emit(True)

    def hideEvent(self, event):
        super().hideEvent(event);self.shown.emit(False)
        if self.anchor is not None:self.anchor.update()
        if self.return_focus is not None and QApplication.focusWidget() is None:
            try:self.return_focus.setFocus(Qt.PopupFocusReason)
            except RuntimeError:pass


# The programs list ----------------------------------------------------------------------------------------------------------------

# One plain name per entry (the brief: "one plain name"); the catalogue's own title stays in each row's descriptor.
PLAIN = {'projects':'Projects', 'inquiries':'Questions', 'calculate':'Calculator', 'laboratory':'Laboratory', 'methods':'Methods',
         'tools':'Tool Atlas', 'office':'Office', 'files':'Files', 'documents':'Documents', 'investigations':'Assignments',
         'agenda':'Agenda', 'brain':'Local model', 'knowledge':'Sources', 'references':'References', 'memory':'Memory',
         'settings':'Settings', 'activity':'Work trail', 'mail':'Mail', 'blender':'Blender', 'godot':'Godot',
         'transfer':'Transfer', 'cartridge':'Cartridge Bay', 'inkscape':'Inkscape',
         'media':'Media Bench', 'freecad':'FreeCAD', 'print':'Print Proof', 'delivery':'Delivery',
         'kicad':'KiCad checks', 'kibot':'KiBot outputs', 'spice':'ngspice profiles',
         'yosys':'Yosys synthesis', 'fpga':'nextpnr & Trellis', 'hdl':'HDL simulation checks'}
EXPLORE = 'Explore the workshop'
EXPLORE_TIP = ('Opens: the Explore workspace, a Graphite workspace that searches every workspace, method and registered operation. '
               'Opening runs no tool.')
TOY_BOX = "the cat's toy box and your toolbox"
# The captions a program row can show (status, in print): its row is never wider than its word and the longest of these.
CAPTIONS = ('unavailable', 'needs setup', '99 running', '99 interrupted', 'open')


def plain_name(entry):
    return PLAIN.get(entry['key'], entry['title'])


def order():
    """The entries' keys in the list's order: by plain name, A to Z (case and accents aside), the catalogue's own order kept for
    equal names."""
    from . import explore
    return [row[0] for row in sorted(explore.VIEWS, key=lambda row:(PLAIN.get(row[0], row[1]).casefold(), row[0]))]


def programs_need(m):
    """The widest program row: its word and the longest caption any row can show; Explore the workshop; the caption."""
    from . import explore
    longest = max(QFontMetricsF(caption_font(m)).horizontalAdvance(c) for c in CAPTIONS)
    words = [PLAIN.get(row[0], row[1]) for row in explore.VIEWS]
    import math
    need = max(row_need(m, w) for w in words + [EXPLORE]) + m.caption_gap + math.ceil(longest)
    return max(need, row_need(m, TOY_BOX, '', True))


def caption_for(entry, opened):
    """A row's one status word, in print: unavailable, needs setup, the owner's running or interrupted jobs, or open."""
    if not entry['view_available']:return 'unavailable'
    if entry.get('tool_status') == 'Needs setup':return 'needs setup'
    if entry.get('running_jobs'):return '%d running' % entry['running_jobs']
    if entry.get('interrupted_jobs'):return '%d interrupted' % entry['interrupted_jobs']
    return 'open' if opened else ''


class ProgramsList(DeskMenu):
    """The cat's programs list. Rows are created once, one per adapter of explore.VIEWS and Explore the workshop, in a fixed
    order (order()); each opening refills their words, captions and tooltips from one ledger.explore read (the button's
    prepare). A failed read hides the program rows behind one explained row; Explore the workshop stays."""
    def __init__(self, host, anchor, actions, explore_action):
        super().__init__(host, getattr(getattr(getattr(host,'shell2',None),'top',None),'programs',anchor), 'upper-programs', 'ProgramsList')
        self.actions = actions;self.explore_action = explore_action
        self.setAccessibleName('Programs');self.setAccessibleDescription('The programs and capabilities, A to Z; type a name\'s first letters to jump to it')
        self.side = 'upper-programs';self.caption = Caption(self, 'applications and capabilities');self.box.addWidget(self.caption)
        self.unavailable = MenuRow(self, 'Capabilities unavailable', 'unavailable');self.unavailable.setEnabled(False);self.unavailable.hide();self.box.addWidget(self.unavailable)
        self.rows_by_key = {}
        for key in order():
            row = MenuRow(self, actions[key].text(), key, action=actions[key]);self.rows_by_key[key] = row;self.box.addWidget(row)
        self.rule = Rule(self);self.box.addWidget(self.rule)
        self.explore_row = MenuRow(self, EXPLORE, 'explore', action=explore_action);self.box.addWidget(self.explore_row)
        # 0.7.0: the game, among the programs (it was the System menu's first row).
        self.game_row = MenuRow(self, 'Game', 'game', 'STRUTHIO', callback=self.open_game);self.game_row.setObjectName('GameRow')
        self.game_row.setToolTip('STRUTHIO in its offline desk mode, paused at tick zero');self.game_row.setAccessibleName('Game: STRUTHIO in its offline desk mode, paused at tick zero')
        self.box.addWidget(self.game_row);self.end_rows()

    def open_game(self):
        from .struthio_qt import show
        show(self.host)

    def show_unavailable(self, message):
        self.unavailable.word = 'Capabilities unavailable · ' + message[:80];self.unavailable.setToolTip(message);self.unavailable.show()
        for row in self.rows_by_key.values():row.hide()
        self.unavailable.describe()

    def show_programs(self):
        self.unavailable.hide()
        for row in self.rows_by_key.values():row.show()

    def words(self):
        """The rows' words top to bottom, '—' for the rule (for readers and checks)."""
        out = []
        for i in range(self.box.count()):
            w = self.box.itemAt(i).widget()
            if w is None or not w.isVisibleTo(self) or isinstance(w, (Caption, Margin)):continue
            out.append('—' if isinstance(w, Rule) else w.word)
        return out
