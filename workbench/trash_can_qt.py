"""DELETE, as a can: apart from the Library tree, at the foot of the column, yet joined to it by a pencil stem.

The owner, 14 November 2026: "I want trash called DELETE." DELETE is the place, always in capitals and named like one
("in DELETE"); Delete is what sends a thing there; restore brings it back. The operations underneath keep their names
(files.trash, the .trash folder).

The can is drawn in the same hand as the Library's twigs (pencil gold stem, graphite can). When something is in it, a
crumpled sheet shows over the rim, and the count sits on the right like every other Library count. Click it to open DELETE;
drop files from Files on it to delete them (the same files.trash operation, so every deletion stays recoverable).
"""
from __future__ import annotations
from pathlib import Path
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget
from .shell2 import AMBER_EDGE, CARD, ERASER, ERASER_MARK, LINE_STRONG, QUIET, RAISED, SANS, TEXT

WORD = 'DELETE'          # the word drawn beside the can, measured as it is drawn


def draw_can(p, rect, full=False, line=None):
    """A trash can inside rect: lid with its handle, a tapered body with three ribs; a crumpled sheet when full."""
    p.save();p.setRenderHint(QPainter.Antialiasing)
    w, h = rect.width(), rect.height();u = min(w, h) / 24.0;x0, y0 = rect.left() + (w - 24 * u) / 2, rect.top() + (h - 24 * u) / 2
    P = lambda x, y:QPointF(x0 + x * u, y0 + y * u)
    pen = QPen(QColor(line or TEXT), max(1.2, min(1.5 * u, 2.6)));pen.setCapStyle(Qt.RoundCap);pen.setJoinStyle(Qt.RoundJoin)
    if full:  # a crumpled sheet over the rim, drawn first so the lid sits on it
        sheet = QPainterPath(P(7, 6.5));sheet.lineTo(P(9.5, 2.5));sheet.lineTo(P(12.5, 4));sheet.lineTo(P(15.5, 1.8));sheet.lineTo(P(17.5, 6.5));sheet.closeSubpath()
        p.setPen(QPen(QColor(LINE_STRONG), max(1.0, u)));p.setBrush(QColor(CARD));p.drawPath(sheet)
    body = QPainterPath(P(5.5, 8));body.lineTo(P(18.5, 8));body.lineTo(P(17.2, 21.5));body.quadTo(P(17, 22.5), P(16, 22.5))
    body.lineTo(P(8, 22.5));body.quadTo(P(7, 22.5), P(6.8, 21.5));body.closeSubpath()
    p.setPen(pen);p.setBrush(QColor(ERASER if full else CARD));p.drawPath(body)
    for x in (9.5, 12, 14.5):p.drawLine(P(x, 11), P(x + (x - 12) * .08, 19.5))
    p.setBrush(QColor(RAISED));p.drawRoundedRect(QRectF(P(4, 5.6), P(20, 8)), u, u)  # the lid
    p.setBrush(Qt.NoBrush);p.drawPolyline([P(10, 5.6), P(10.4, 4), P(13.6, 4), P(14, 5.6)])  # its handle
    p.restore()


def can_ink(can):
    """The can's ink inside its can-by-can square (draw_can's own geometry, u = can / 24): (left, top, right, bottom). The
    lid's outline is the widest part, the body's bottom line the lowest, the crumpled sheet of a full can the highest (the
    top is the full can's, so Trash keeps one height whether or not it holds anything)."""
    u = can / 24.0;pen = max(1.2, min(1.5 * u, 2.6));sheet = max(1.0, u)
    return 4 * u - pen / 2, min(4 * u - pen / 2, 1.8 * u - sheet), 20 * u + pen / 2, 22.5 * u + pen / 2


class TrashCan(QWidget):
    """DELETE at the left pane's lower right (HATCH DESK D1b, larger; D1-fix: pinned by its ink). Its box is exactly what it
    draws, right-aligned: the can, the word DELETE and, when something is in it, the count, ending at the box's right edge,
    the can's bottom line on the box's bottom edge (room for a three-digit count is kept to the left, so nothing moves when
    DELETE fills). pane_qt.place puts the box an inset from the pane's inner edge and from its bottom, so the drawn DELETE is."""

    def __init__(self, host):
        super().__init__();self.host = host;self.count = 0;self.hover = False;self.setObjectName('TrashCan')
        self.setCursor(Qt.PointingHandCursor);self.setAcceptDrops(True);self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus);self._fit = None;self.fit(1.0)
        self.setAccessibleName(WORD);self.setToolTip('DELETE · what you delete waits here, and restore puts it back where it was · drop files here to delete them')

    def fit(self, scale):
        """HATCH DESK D1b: a larger Trash (the owner's brief), sized with the interface: a 30 px can and the word at the
        controls' size at 14 pt (22 px and 15 px before). D1-fix: the box is the drawing's own extent (pane_qt.trash_size)."""
        key = round(float(scale), 4)
        if key == self._fit:return self.size()
        import math
        from .desk_qt import scaled
        from .pane_qt import TRASH_CAN, TRASH_PAD, trash_size
        self._fit = key;self.can = scaled(TRASH_CAN, scale);self.pad = scaled(TRASH_PAD, scale);self.count_gap = max(4, self.pad // 2)
        self.word_font = QFont(SANS);self.word_font.setPixelSize(max(10, round(16 * float(scale))))
        # a name in capitals, spaced a little so it reads as a place: a typewriter's capitals in Kasandra, Plex in Graphite
        from . import boss_theme as _bt
        self.word_font.setLetterSpacing(QFont.AbsoluteSpacing, (1.0 if _bt.APPEARANCE == 'kasandra' else 0.8) * float(scale))
        self.count_font = QFont(SANS);self.count_font.setPixelSize(max(10, round(13 * float(scale))))
        self.word_ink = QRectF(*self.extent(self.word_font, WORD));self.ink = can_ink(self.can)  # the word's ink as drawn (desk_qt.ink_extent)
        self.word_width = self.word_ink.width();room = self.extent(self.count_font, '999')[2]
        self.setFixedSize(*trash_size(scale, math.ceil(self.word_width), math.ceil(room), self.ink, self.count_gap))
        self.update();return self.size()

    @staticmethod
    def extent(font, text):
        """(left, top, width, height) of text's ink as drawn from a whole-pixel origin (desk_qt.ink_extent)."""
        from .desk_qt import ink_extent
        l, t, r, b = ink_extent(font, text);return (l, t, r - l, b - t)

    def layout(self):
        """Where each part is drawn, right to left from the box's right edge: (can square's top-left, word origin, count
        origin or None). The word's (or the count's) last inked column ends at the box's right edge; the can's lid ends a
        pad before the word's first inked column; the can's bottom line is the box's bottom edge; the word is centred on
        the can's height."""
        right = float(self.width());count = None
        if self.count:
            c = QRectF(*self.extent(self.count_font, str(self.count)));count = QPointF(right - c.right(), 0.0);right = count.x() + c.left() - self.count_gap
        word = self.word_ink;wx = right - word.right()
        left, top, ink_right, bottom = self.ink;cx = wx + word.left() - self.pad - ink_right;cy = self.height() - bottom
        u = self.can / 24.0;empty_top = 4 * u - max(1.2, min(1.5 * u, 2.6)) / 2
        by = round(cy + (empty_top + bottom) / 2 - (word.top() + word.bottom()) / 2)
        if count is not None:count.setY(by)
        return QPointF(cx, cy), QPointF(wx, by), count

    def set_count(self, n):
        self.count = int(n or 0);self.update()

    def enterEvent(self, event):
        self.hover = True;self.update()

    def leaveEvent(self, event):
        self.hover = False;self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.rect().contains(event.position().toPoint()):
            from .shell2 import open_destination
            open_destination(self.host, 'trash')

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            from .shell2 import open_destination
            open_destination(self.host, 'trash');event.accept()
        else:super().keyPressEvent(event)

    def paintEvent(self, event):
        p = QPainter(self);p.setRenderHint(QPainter.Antialiasing);h = self.height();w = self.width();can, word, count = self.layout()
        if self.hover or self.hasFocus():  # the raised paper behind it, inside the box (no ink past the box)
            p.setPen(Qt.NoPen);p.setBrush(QColor(RAISED));p.drawRoundedRect(QRectF(0, 0, w, h), 6, 6)
        from . import boss_theme as _bt
        red = _bt.RED if _bt.APPEARANCE == 'kasandra' else None      # 0.8.1 (Kasandra): the can in red, the owner's experiment
        if red and not self._dropping:      # a little of its own light under the red can, as the desk's glow
            glow = QColor(red);glow.setAlphaF(min(0.35, 0.12 + 0.1 * _bt.glow()))
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):draw_can(p, QRectF(can.x() + dx, can.y() + dy, self.can, self.can), full=self.count > 0, line=glow.name(QColor.HexArgb))
        draw_can(p, QRectF(can.x(), can.y(), self.can, self.can), full=self.count > 0, line=ERASER_MARK if self._dropping else red)
        p.setFont(self.word_font);p.setPen(QColor(red or TEXT));p.drawText(word, WORD)
        if count is not None:p.setFont(self.count_font);p.setPen(QColor(QUIET));p.drawText(count, str(self.count))

    _dropping = False

    def paths(self, event):
        from .engine import engineering
        from . import files_service
        try:root = Path(files_service.root(engineering(self.host.root))).resolve()
        except Exception:return []
        out = []
        for url in event.mimeData().urls() if event.mimeData().hasUrls() else []:
            try:out.append(Path(url.toLocalFile()).resolve().relative_to(root).as_posix())
            except (ValueError, OSError):pass
        return out

    def dragEnterEvent(self, event):
        if self.paths(event):self._dropping = True;self.update();event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self._dropping = False;self.update()

    def dropEvent(self, event):
        from .shell2 import call_write
        self._dropping = False
        for rel in self.paths(event):call_write(self.host, 'files.trash', {'path': rel})
        event.acceptProposedAction()
        try:
            from .shell2 import refresh_library
            refresh_library(self.host)
        except Exception:pass
        self.update()
