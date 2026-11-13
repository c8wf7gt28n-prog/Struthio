"""Graphite's drawn icons: the glyphs a tool button may wear instead of its words (tool_faces).

The owner, 13 November 2026, after "No ugly white boxes that stand out like a sore thumb": "Or graphite themed icons can
be tried as an option also."

One hand drew all of them, in the language of Graphite's own mark (two cut facets that meet at a point): straight
strokes of one weight with sharp joins, arrow heads and folded corners as small solid facets, and a hexagon where another
program would draw a circle, because graphite is sheets of carbon in a hexagonal lattice. Each glyph is one idea, read in
one colour at 20 px; the accent only fills a facet and never carries the meaning.

Every glyph is a function draw(p, ink, accent) that paints inside a 20 x 20 unit box; the caller places and scales the
painter and chooses the two colours. Horizontal and vertical strokes sit on half-unit centres so that they are crisp at
the true size. This file imports only PySide6, so a contact sheet can be made from it alone.
"""
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QFont, QPainterPath, QPen, QPolygonF

WEIGHT = 1.6        # the one line weight, in units of the 20-unit box


def pen(p, ink, weight=WEIGHT, cap=Qt.FlatCap):
    q = QPen(ink, weight);q.setCapStyle(cap);q.setJoinStyle(Qt.MiterJoin);q.setMiterLimit(4.0)
    p.setPen(q);p.setBrush(Qt.NoBrush)


def line(p, *points, close=False):
    path = QPainterPath(QPointF(*points[0]))
    for point in points[1:]:path.lineTo(*point)
    if close:path.closeSubpath()
    p.drawPath(path)


def facet(p, colour, *points):
    """A small solid shape with no outline: an arrow head, a folded corner, a point."""
    p.save();p.setPen(Qt.NoPen);p.setBrush(colour);p.drawPolygon(QPolygonF([QPointF(*point) for point in points]));p.restore()


def mirrored(draw):
    """The same glyph facing the other way."""
    def other(p, ink, accent):
        p.save();p.translate(20, 0);p.scale(-1, 1)
        try:draw(p, ink, accent)
        finally:p.restore()
    return other


# ---- the bar above the work ------------------------------------------------------------------------------------------

def field(p, ink, accent):
    """The Field: two sheets and the wire between them."""
    facet(p, accent, (2.5, 2.5), (8.5, 2.5), (8.5, 8.5), (2.5, 8.5))
    pen(p, ink);p.drawRect(QRectF(2.5, 2.5, 6, 6));p.drawRect(QRectF(11.5, 11.5, 6, 6))
    line(p, (8.5, 5.5), (14.5, 5.5), (14.5, 11.5))


def find(p, ink, accent):
    """A lens, cut as a hexagon, and its handle."""
    pen(p, ink);line(p, (8.5, 2.7), (13.5, 5.6), (13.5, 11.4), (8.5, 14.3), (3.5, 11.4), (3.5, 5.6), close=True)
    pen(p, ink, 2.0);line(p, (12.4, 12.6), (17.0, 17.2))


def smaller(p, ink, accent):
    pen(p, ink, 1.8);line(p, (5.0, 10.5), (16.0, 10.5))


def larger(p, ink, accent):
    pen(p, ink, 1.8);line(p, (5.0, 10.5), (16.0, 10.5));line(p, (10.5, 5.0), (10.5, 16.0))


def undo(p, ink, accent):
    """Back along the line: a head to the left, and the turn it came by."""
    pen(p, ink);line(p, (7.0, 7.5), (12.5, 7.5), (16.5, 11.5), (12.5, 15.5), (8.0, 15.5))
    facet(p, ink, (2.6, 7.5), (8.0, 3.0), (8.0, 12.0))


redo = mirrored(undo)


def save(p, ink, accent):
    """The disk, its corner cut: the one facet every program already draws."""
    facet(p, accent, (6.5, 3.5), (12.5, 3.5), (12.5, 7.5), (6.5, 7.5))
    pen(p, ink);line(p, (3.5, 3.5), (13.5, 3.5), (16.5, 6.5), (16.5, 16.5), (3.5, 16.5), close=True)
    line(p, (6.5, 3.5), (6.5, 7.5), (12.5, 7.5), (12.5, 3.5));line(p, (6.5, 16.5), (6.5, 11.5), (13.5, 11.5), (13.5, 16.5))


# ---- a page of a document --------------------------------------------------------------------------------------------

def previous(p, ink, accent):
    pen(p, ink, 2.0);line(p, (12.5, 4.0), (6.5, 10.0), (12.5, 16.0))


following = mirrored(previous)


def cite(p, ink, accent):
    """Quotation marks, each a cut wedge."""
    for x in (0.0, 8.0):
        facet(p, ink, (3.0 + x, 14.5), (3.0 + x, 9.5), (6.0 + x, 4.5), (8.5 + x, 4.5), (6.4 + x, 9.5), (8.5 + x, 9.5), (8.5 + x, 14.5))


def table(p, ink, accent):
    facet(p, accent, (2.5, 4.5), (17.5, 4.5), (17.5, 8.5), (2.5, 8.5))
    pen(p, ink);p.drawRect(QRectF(2.5, 4.5, 15, 11));line(p, (2.5, 8.5), (17.5, 8.5));line(p, (7.5, 8.5), (7.5, 15.5));line(p, (12.5, 8.5), (12.5, 15.5))


def more(p, ink, accent):
    """Three points of the lattice."""
    for x in (4.0, 10.0, 16.0):facet(p, ink, (x - 2.0, 10.0), (x, 8.0), (x + 2.0, 10.0), (x, 12.0))


def note(p, ink, accent):
    """A slip of paper with its corner turned up."""
    facet(p, accent, (16.5, 11.5), (11.5, 11.5), (11.5, 16.5))
    pen(p, ink);line(p, (3.5, 3.5), (16.5, 3.5), (16.5, 11.5), (11.5, 16.5), (3.5, 16.5), close=True);line(p, (16.5, 11.5), (11.5, 11.5), (11.5, 16.5))
    line(p, (6.5, 7.5), (13.5, 7.5));line(p, (6.5, 10.5), (9.0, 10.5))


# ---- a sheet of numbers ----------------------------------------------------------------------------------------------

def report(p, ink, accent):
    """The sum."""
    pen(p, ink, 1.8);line(p, (14.5, 6.2), (14.5, 3.5), (5.0, 3.5), (10.5, 10.0), (5.0, 16.5), (14.5, 16.5), (14.5, 13.8))


def recalc(p, ink, accent):
    """Round again: two turns of a hexagon, each ending in a head."""
    pen(p, ink);line(p, (3.5, 9.5), (3.5, 6.5), (6.5, 3.5), (12.0, 3.5));line(p, (16.5, 10.5), (16.5, 13.5), (13.5, 16.5), (8.0, 16.5))
    facet(p, ink, (16.6, 3.5), (11.5, 0.2), (11.5, 6.8));facet(p, ink, (3.4, 16.5), (8.5, 13.2), (8.5, 19.8))


def export(p, ink, accent):
    """Out of the tray."""
    pen(p, ink);line(p, (3.5, 11.5), (3.5, 16.5), (16.5, 16.5), (16.5, 11.5));line(p, (10.0, 13.0), (10.0, 7.0))
    facet(p, ink, (10.0, 2.0), (14.8, 7.6), (5.2, 7.6))


def cell(p, ink, accent):
    """The pencil, and the line it writes on."""
    facet(p, accent, (5.0, 15.0), (5.0, 11.4), (8.6, 15.0))
    pen(p, ink);line(p, (13.6, 2.8), (17.2, 6.4), (8.6, 15.0), (5.0, 15.0), (5.0, 11.4), close=True);line(p, (11.2, 5.2), (14.8, 8.8))
    line(p, (11.5, 17.5), (17.5, 17.5))


def source(p, ink, accent):
    """This row, and where it leads."""
    pen(p, ink);line(p, (3.0, 4.5), (10.0, 4.5));line(p, (3.0, 16.5), (10.0, 16.5));line(p, (3.0, 10.5), (12.5, 10.5))
    facet(p, ink, (17.6, 10.5), (12.0, 6.0), (12.0, 15.0))


# ---- writing, and a finding ------------------------------------------------------------------------------------------

def document(p, ink, accent):
    """A new page: its corner folded, and a plus."""
    facet(p, accent, (11.5, 2.5), (15.5, 6.5), (11.5, 6.5))
    pen(p, ink);line(p, (4.5, 2.5), (11.5, 2.5), (15.5, 6.5), (15.5, 17.5), (4.5, 17.5), close=True);line(p, (11.5, 2.5), (11.5, 6.5), (15.5, 6.5))
    line(p, (7.5, 12.5), (12.5, 12.5));line(p, (10.0, 10.0), (10.0, 15.0))


def again(p, ink, accent):
    """Two sources side by side, and the look from one to the other and back."""
    facet(p, accent, (2.5, 2.5), (8.5, 2.5), (8.5, 10.5), (2.5, 10.5))
    pen(p, ink);p.drawRect(QRectF(2.5, 2.5, 6, 8));p.drawRect(QRectF(11.5, 2.5, 6, 8));line(p, (6.5, 15.5), (13.5, 15.5))
    facet(p, ink, (2.4, 15.5), (7.0, 12.2), (7.0, 18.8));facet(p, ink, (17.6, 15.5), (13.0, 12.2), (13.0, 18.8))


def stop(p, ink, accent):
    facet(p, ink, (5.5, 5.5), (14.5, 5.5), (14.5, 14.5), (5.5, 14.5))


def letters(text, weight=QFont.DemiBold, italic=False, under=False, family='IBM Plex Sans', size=13.0):
    """A glyph that is type: the letter a writer already knows a style by."""
    def draw(p, ink, accent):
        font = QFont(family);font.setPixelSize(int(size));font.setWeight(weight);font.setItalic(italic)
        p.setFont(font);p.setPen(ink);p.drawText(QRectF(-4, 0, 28, 19 if under else 20), Qt.AlignCenter, text)
        if under:
            pen(p, ink, 1.4);line(p, (5.0, 17.5), (15.0, 17.5))
    return draw


GLYPHS = {
    'field': field, 'find': find, 'smaller': smaller, 'larger': larger, 'undo': undo, 'redo': redo, 'save': save,
    'previous': previous, 'next': following, 'cite': cite, 'table': table, 'more': more, 'note': note,
    'report': report, 'recalc': recalc, 'export': export, 'cell': cell, 'source': source,
    'document': document, 'again': again, 'stop': stop,
    'bold': letters('B', QFont.Bold, size=14.0), 'italic': letters('I', QFont.DemiBold, italic=True, size=14.0),
    'underline': letters('U', QFont.DemiBold, under=True, size=12.0),
    'h1': letters('H1'), 'h2': letters('H2', QFont.Medium, size=12.0), 'h3': letters('H3', QFont.Normal, size=11.0),
    'body': letters('¶', QFont.Normal, size=14.0), 'code': letters('{}', QFont.Medium, family='IBM Plex Mono', size=12.0),
    'plain': letters('Aa', QFont.Normal, size=12.0),
}
