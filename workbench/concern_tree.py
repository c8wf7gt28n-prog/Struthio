"""Native tree with visible ancestry connectors and normal Qt item semantics."""
from PySide6.QtCore import Qt, QEvent, QPointF, QRectF
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QTreeWidget


class ConcernTree(QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRootIsDecorated(True)
        self.setAccessibleName('ARC Concern navigator')
        self.reading_indent()

    def reading_indent(self):
        if getattr(self, 'desk_branches', False) and getattr(self, 'desk_indent', None):  # HATCH DESK D1b: the desk trees' indent
            self.setIndentation(self.desk_indent);return
        # twigs need room to bend and bud; plain rows keep the reading indent
        self.setIndentation(max(26 if getattr(self, 'twig_branches', False) else 20, round(self.fontMetrics().height() * (1.25 if getattr(self, 'twig_branches', False) else .8))))

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.FontChange:
            self.reading_indent()

    def _next_visible(self, index):
        parent = index.parent()
        return any(not self.isRowHidden(row, parent)
                   for row in range(index.row() + 1, self.model().rowCount(parent)))

    def drawBranches(self, painter, rect, index):
        if not getattr(self, '_path_watched', False):      # 0.5.1: the lit path follows the current row, so every branch is drawn again when it moves
            self._path_watched = True;self.currentItemChanged.connect(lambda *_: self.viewport().update())
        if getattr(self, 'desk_branches', False):  # HATCH DESK D1b: Existing views draw the desk trees' branch lines
            from .pane_qt import draw_branches
            return draw_branches(self, painter, rect, index)
        if getattr(self, 'twig_branches', False):return self.draw_twigs(painter, rect, index)
        super().drawBranches(painter, rect, index)
        if getattr(self, 'plain_branches', False):return  # 2.x: chevrons only, no connecting lines
        painter.save(); painter.setPen(QPen(QColor('#91a5b9'), 1.25))
        step = self.indentation()
        x = rect.right() - step // 2
        mid = rect.center().y()
        has_children = self.model().hasChildren(index)
        gap = 7 if has_children else 0
        if index.parent().isValid():
            painter.drawLine(x, rect.top(), x, mid - gap)
            painter.drawLine(x + gap, mid, rect.right(), mid)
        if self._next_visible(index):
            painter.drawLine(x, mid + gap, x, rect.bottom())
        ancestor = index.parent()
        while ancestor.isValid():
            x -= step
            if self._next_visible(ancestor):
                painter.drawLine(x, rect.top(), x, rect.bottom())
            ancestor = ancestor.parent()
        painter.restore()

    # 4.5: pencil twigs. Each section grows a soft graphite stem; every row leaves it on a curve, like a twig, and ends in a
    # small bud: pencil yellow for a leaf, a filled bud for an open folder, a hollow one for a closed folder (click it).
    STEM, FAINT_STEM, BUD, BUD_EDGE = '#7d776d', '#b3ac9f', '#d4b56a', '#6c675e'

    def draw_twigs(self, painter, rect, index):
        if not index.parent().isValid():return  # sections are the roots: their words stand on their own
        painter.save();painter.setRenderHint(QPainter.Antialiasing)
        step = self.indentation();depth = 0;ancestor = index.parent()
        while ancestor.parent().isValid():depth += 1;ancestor = ancestor.parent()
        x = rect.right() - step * 0.62;mid = rect.center().y();top, bottom = rect.top(), rect.bottom()
        stem = QPen(QColor(self.STEM if depth == 0 else self.FAINT_STEM), 1.6);stem.setCapStyle(Qt.RoundCap)
        # the stems of ancestors that still have rows below run through this row
        ax = x;ancestor = index.parent()
        while ancestor.parent().isValid():
            ax -= step
            if self._next_visible(ancestor):
                painter.setPen(QPen(QColor(self.FAINT_STEM), 1.3));painter.drawLine(QPointF(ax, top), QPointF(ax, bottom))
            ancestor = ancestor.parent()
        painter.setPen(stem)
        bend = min(step * 0.45, (bottom - top) * 0.45)
        twig = QPainterPath(QPointF(x, top))
        twig.lineTo(QPointF(x, mid - bend))
        twig.quadTo(QPointF(x, mid), QPointF(x + bend, mid))  # the twig bends out of the stem
        bud_x = rect.right() - 5
        twig.lineTo(QPointF(bud_x - 3, mid))
        painter.drawPath(twig)
        if self._next_visible(index):painter.drawLine(QPointF(x, mid - bend), QPointF(x, bottom))
        has_children = self.model().hasChildren(index)
        if has_children and self.isExpanded(index):
            painter.setPen(QPen(QColor(self.BUD_EDGE), 1));painter.setBrush(QColor(self.BUD))
            painter.drawEllipse(QRectF(bud_x - 4, mid - 4, 8, 8))
        elif has_children:
            painter.setPen(QPen(QColor(self.BUD_EDGE), 1.4));painter.setBrush(QColor('#fffdf8'))
            painter.drawEllipse(QRectF(bud_x - 4, mid - 4, 8, 8))
        else:
            painter.setPen(QPen(QColor('#c4a55a'), 0.8));painter.setBrush(QColor(self.BUD));painter.drawEllipse(QRectF(bud_x - 3, mid - 3, 6, 6))
        painter.restore()
