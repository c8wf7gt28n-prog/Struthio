"""Symmetry, measured (HATCH DESK D1a; the owner: "Be obsessive in symmetry"). One small helper the desk check shares.

The desk has one vertical axis, the centre of the window: a box at x, w wide mirrors to width - x - w. Everything here is read
from live widget geometry in window coordinates and every difference is returned in pixels (0 is symmetric); nothing is
changed and nothing is judged by eye.

    box(widget, window)                  (x, y, w, h) of the widget in the window
    pair(name, a, b, window, fields)     a on the left mirrors b on the right; the differences for the asked fields:
                                           outer   a's distance from the left edge less b's distance from the right edge
                                           inner   the mirror of a's right edge less b's left edge
                                           width   a's width less b's width
                                           top, bottom, height   a's less b's
                                           middle  a's vertical centre less b's (in pixels; a half pixel shows as 0.5)
    centred(name, widget_or_box, window) a box's left inset less its right inset (its centre on the axis: 0)
    same(name, values)                   the largest less the smallest of values that must be equal (heights, gaps, edges)
    within(name, measured, expected, t)  a value measured from drawn pixels against its design, 0 within t pixels (D1-fix)
    at_least(name, value, floor)         a value that must reach a floor (room around a drawing), 0 when it does (D1-fix)
    baseline(widget, window)             the window y of a word's text baseline, from the style's own content rect and the
                                         font (QPushButton: centred in SE_PushButtonContents; QLineEdit: Qt's own vertical
                                         rule in SE_LineEditContents less the text margins; QLabel and QToolButton: centred
                                         in the contents rect)
    worst(rows)                          the rows whose difference is not 0
    table(rows)                          the rows as one line each, for an assertion message or a report

A row is dict(pair=name, field=field, difference=pixels, left=..., right=...): the two numbers compared and their difference.
Used by tools/check_desk_ui.py; D1b adds its own pairs (tabs, trees, Trash) the same way.
"""
from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QLabel, QLineEdit, QPushButton, QStyle, QStyleOptionButton, QStyleOptionFrame, QToolButton

FIELDS = ('outer', 'inner', 'width', 'top', 'bottom', 'height', 'middle')


def box(widget, window):
    """The widget's (x, y, w, h) in window coordinates; a 4-tuple passes through."""
    if isinstance(widget, tuple):return widget
    p = widget.mapTo(window, QPoint(0, 0));return (p.x(), p.y(), widget.width(), widget.height())


def _row(name, field, left, right):
    difference = left - right
    if isinstance(difference, float) and difference.is_integer():difference = int(difference)
    return dict(pair=name, field=field, left=left, right=right, difference=difference)


def pair(name, a, b, window, fields=FIELDS):
    """a (on the left) mirrors b (on the right) about the window's axis."""
    W = window.width();(ax, ay, aw, ah), (bx, by, bw, bh) = box(a, window), box(b, window);rows = []
    values = {'outer':(ax, W - (bx + bw)), 'inner':(W - (ax + aw), bx), 'width':(aw, bw), 'top':(ay, by),
              'bottom':(ay + ah, by + bh), 'height':(ah, bh), 'middle':(ay + ah / 2.0, by + bh / 2.0)}
    for field in fields:rows.append(_row(name, field, *values[field]))
    return rows


def centred(name, widget, window):
    """The box's left inset from the window's left edge less its right inset from the right edge: 0 when its centre is the axis."""
    x, _, w, _ = box(widget, window);W = window.width()
    return [_row(name, 'centre on the axis', x, W - (x + w))]


def same(name, values, field='equal'):
    """Values that must be equal: the largest less the smallest (0 when all are equal)."""
    values = list(values)
    if not values:return []
    return [_row(name, field, max(values), min(values))]


def span(widgets, window):
    """The box that holds all the widgets (window coordinates)."""
    boxes = [box(w, window) for w in widgets]
    left = min(b[0] for b in boxes);top = min(b[1] for b in boxes)
    right = max(b[0] + b[2] for b in boxes);bottom = max(b[1] + b[3] for b in boxes)
    return (left, top, right - left, bottom - top)


def gaps(widgets, window):
    """The gaps between consecutive widgets of a row, left to right."""
    boxes = sorted(box(w, window) for w in widgets)
    return [b[0] - (a[0] + a[2]) for a, b in zip(boxes, boxes[1:])]


def baseline(widget, window):
    """The window y of the widget's text baseline (see the module note), as Qt places the text when it paints it."""
    fm = widget.fontMetrics();top = widget.mapTo(window, QPoint(0, 0)).y()
    if widget.property('inkWord'):return top + int(widget.property('inkBaseline') or 0)  # a band word drawn by its ink (desk_qt.InkWord)
    if isinstance(widget, QPushButton):
        option = QStyleOptionButton();widget.initStyleOption(option)
        r = widget.style().subElementRect(QStyle.SE_PushButtonContents, option, widget)
        return top + r.top() + (r.height() - fm.height()) / 2.0 + fm.ascent()
    if isinstance(widget, QLineEdit):
        option = QStyleOptionFrame();widget.initStyleOption(option)
        r = widget.style().subElementRect(QStyle.SE_LineEditContents, option, widget)
        m = widget.textMargins();r = r.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        return top + r.top() + (r.height() - fm.height() + 1) // 2 + fm.ascent()
    r = widget.contentsRect()
    if isinstance(widget, QLabel) and not widget.alignment() & Qt.AlignVCenter:
        return top + r.top() + fm.ascent() if widget.alignment() & Qt.AlignTop else top + r.bottom() + 1 - fm.descent()
    _ = QToolButton  # a tool button centres its words in its contents rect, as a label does
    return top + r.top() + (r.height() - fm.height()) / 2.0 + fm.ascent()


def within(name, measured, expected, tolerance, field='as drawn'):
    """A value measured from drawn pixels (sub-pixel, or a whole column found by coverage) against the value its design puts
    it at: difference 0 when it is within `tolerance` pixels (the measure's own uncertainty, said in the row), else the
    measured difference. A pixel's shift of what is drawn shows here even where the boxes still mirror."""
    d = float(measured) - float(expected)
    return [dict(pair=name, field=field, left=round(float(measured), 3), right=round(float(expected), 3),
                 difference=0 if abs(d) <= tolerance else round(d, 3), tolerance=tolerance)]


def at_least(name, value, floor, field='room'):
    """A value that must be at least `floor` (room around a drawing, a count of nothing clipped): 0 when it is, else how far short."""
    d = float(value) - float(floor)
    return [dict(pair=name, field=field, left=round(float(value), 3), right=round(float(floor), 3), difference=0 if d >= 0 else round(d, 3))]


def worst(rows):
    """The rows that are not symmetric (difference other than 0)."""
    return [r for r in rows if r['difference'] != 0]


def table(rows):
    return '; '.join('%s · %s: %s vs %s (%s px)' % (r['pair'], r['field'], r['left'], r['right'], r['difference']) for r in rows)
