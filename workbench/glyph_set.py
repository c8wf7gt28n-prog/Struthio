"""Graphite's drawn icons: the glyphs a tool button may wear instead of its words (tool_faces).

The owner, 13 November 2026, after "No ugly white boxes that stand out like a sore thumb": "Or graphite themed icons can
be tried as an option also."

One hand drew all of them, in the language of Graphite's own mark (two cut facets that meet at a point): straight
strokes of one weight with sharp joins, arrow heads and folded corners as small solid facets, and a hexagon where another
program would draw a circle, because graphite is sheets of carbon in a hexagonal lattice. Each glyph is one idea, read in
one colour at 20 px; the accent only fills a facet and never carries the meaning.

The same hand draws the kinds of sheet on the Field (KIND): a source, a sheet, a calculation, a finding, a question and
the rest. Seen from far off, where no word can be read, a sheet on the desk is its kind's glyph and its name (field_qt).

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


def pin(p, ink, accent):
    """A pin: this stays open."""
    facet(p, accent, (7.5, 3.5), (12.5, 3.5), (12.5, 9.5), (7.5, 9.5))
    pen(p, ink);line(p, (5.5, 3.5), (14.5, 3.5));line(p, (7.5, 3.5), (7.5, 9.5));line(p, (12.5, 3.5), (12.5, 9.5))
    line(p, (4.0, 9.5), (16.0, 9.5));line(p, (10.0, 9.5), (10.0, 17.5))


def stop(p, ink, accent):
    facet(p, ink, (5.5, 5.5), (14.5, 5.5), (14.5, 14.5), (5.5, 14.5))


# ---- the kinds of sheet on the Field ----------------------------------------------------------------------------------

HEX = ((10.0, 2.5), (16.5, 6.25), (16.5, 13.75), (10.0, 17.5), (3.5, 13.75), (3.5, 6.25))      # one cell of the lattice


def page(p, ink, accent):
    """A source: a page as it came, its corner folded."""
    facet(p, accent, (11.5, 2.5), (15.5, 6.5), (11.5, 6.5))
    pen(p, ink);line(p, (4.5, 2.5), (11.5, 2.5), (15.5, 6.5), (15.5, 17.5), (4.5, 17.5), close=True);line(p, (11.5, 2.5), (11.5, 6.5), (15.5, 6.5))
    line(p, (7.5, 10.5), (12.5, 10.5));line(p, (7.5, 13.5), (12.5, 13.5))


def found(p, ink, accent):
    """A finding: a cell of the lattice, ticked."""
    pen(p, ink);line(p, *HEX, close=True)
    pen(p, ink, 1.8);line(p, (6.6, 10.2), (9.2, 12.8), (13.6, 7.4))


def asked(p, ink, accent):
    """An open question."""
    pen(p, ink, 1.8);line(p, (6.5, 7.2), (6.5, 5.0), (9.0, 2.5), (11.0, 2.5), (13.5, 5.0), (13.5, 7.5), (10.0, 10.5), (10.0, 13.0))
    facet(p, ink, (10.0, 14.6), (11.9, 16.5), (10.0, 18.4), (8.1, 16.5))


def limit(p, ink, accent):
    """A condition: no more than this."""
    pen(p, ink, 1.8);line(p, (14.5, 3.0), (5.5, 7.5), (14.5, 12.0));line(p, (5.0, 16.5), (15.0, 16.5))


def steps(p, ink, accent):
    """A method: the steps, one after another."""
    pen(p, ink);line(p, (2.5, 16.5), (7.5, 16.5), (7.5, 11.5), (12.5, 11.5), (12.5, 6.5), (17.5, 6.5))
    facet(p, accent, (12.5, 6.5), (17.5, 6.5), (17.5, 3.0))


def running(p, ink, accent):
    """A job: a cell of the lattice, at work."""
    pen(p, ink);line(p, *HEX, close=True)
    facet(p, ink, (8.0, 6.3), (14.2, 10.0), (8.0, 13.7))


def folder(p, ink, accent):
    facet(p, accent, (2.5, 4.5), (8.0, 4.5), (10.0, 7.5), (2.5, 7.5))
    pen(p, ink);line(p, (2.5, 4.5), (8.0, 4.5), (10.0, 7.5), (17.5, 7.5), (17.5, 15.5), (2.5, 15.5), close=True)


def port(p, ink, accent):
    """An interface of this computer: a socket and its lead."""
    pen(p, ink);p.drawRect(QRectF(4.5, 6.5, 11, 7));line(p, (7.5, 6.5), (7.5, 2.5));line(p, (12.5, 6.5), (12.5, 2.5));line(p, (10.0, 13.5), (10.0, 18.0))


def window(p, ink, accent):
    """A program that is running: its window."""
    facet(p, accent, (2.5, 4.5), (17.5, 4.5), (17.5, 8.5), (2.5, 8.5))
    pen(p, ink);p.drawRect(QRectF(2.5, 4.5, 15, 11));line(p, (2.5, 8.5), (17.5, 8.5))
    facet(p, ink, (5.0, 11.0), (8.5, 12.75), (5.0, 14.5))


def reach(p, ink, accent):
    """Where it reaches: the line arrives at a far wall."""
    pen(p, ink);line(p, (2.5, 10.5), (9.0, 10.5));line(p, (16.5, 3.5), (16.5, 17.5))
    facet(p, ink, (14.6, 10.5), (9.0, 6.0), (9.0, 15.0))


def rooms(p, ink, accent):
    """A program Graphite can open: four rooms, one lit."""
    facet(p, accent, (3.5, 3.5), (8.5, 3.5), (8.5, 8.5), (3.5, 8.5))
    pen(p, ink)
    for x, y in ((3.5, 3.5), (11.5, 3.5), (3.5, 11.5), (11.5, 11.5)):p.drawRect(QRectF(x, y, 5, 5))


# ---- what the menus name ---------------------------------------------------------------------------------------------

def copy(p, ink, accent):
    """Two sheets, one over the other."""
    facet(p, accent, (3.5, 6.5), (12.5, 6.5), (12.5, 17.5), (3.5, 17.5))
    pen(p, ink);p.drawRect(QRectF(3.5, 6.5, 9, 11));line(p, (7.5, 6.5), (7.5, 2.5), (16.5, 2.5), (16.5, 13.5), (12.5, 13.5))


def paste(p, ink, accent):
    """The board a sheet is clipped to."""
    pen(p, ink);p.drawRect(QRectF(4.5, 4.5, 11, 13));line(p, (7.5, 10.5), (12.5, 10.5));line(p, (7.5, 13.5), (12.5, 13.5))
    facet(p, ink, (7.5, 2.5), (12.5, 2.5), (12.5, 6.5), (7.5, 6.5))


def cut(p, ink, accent):
    """Scissors."""
    pen(p, ink);line(p, (5.0, 2.5), (13.2, 13.2));line(p, (15.0, 2.5), (6.8, 13.2))
    for x in (5.5, 14.5):facet(p, ink, (x - 2.5, 15.5), (x, 13.0), (x + 2.5, 15.5), (x, 18.0))


def select(p, ink, accent):
    """All of it: a marked-off field."""
    facet(p, accent, (6.5, 6.5), (13.5, 6.5), (13.5, 13.5), (6.5, 13.5))
    pen(p, ink)
    for a, b in (((3.5, 3.5), (8.0, 3.5)), ((12.0, 3.5), (16.5, 3.5)), ((3.5, 16.5), (8.0, 16.5)), ((12.0, 16.5), (16.5, 16.5)),
                 ((3.5, 3.5), (3.5, 8.0)), ((3.5, 12.0), (3.5, 16.5)), ((16.5, 3.5), (16.5, 8.0)), ((16.5, 12.0), (16.5, 16.5))):line(p, a, b)


def full(p, ink, accent):
    """The whole screen: four corners."""
    pen(p, ink, 1.8)
    line(p, (3.5, 8.0), (3.5, 3.5), (8.0, 3.5));line(p, (12.0, 3.5), (16.5, 3.5), (16.5, 8.0))
    line(p, (3.5, 12.0), (3.5, 16.5), (8.0, 16.5));line(p, (12.0, 16.5), (16.5, 16.5), (16.5, 12.0))


def home(p, ink, accent):
    """Today: the house."""
    facet(p, accent, (8.5, 16.5), (8.5, 12.5), (11.5, 12.5), (11.5, 16.5))
    pen(p, ink);line(p, (2.5, 10.5), (10.0, 3.5), (17.5, 10.5));line(p, (5.5, 9.0), (5.5, 16.5), (14.5, 16.5), (14.5, 9.0))


def sliders(p, ink, accent):
    """Settings: three rules, each set somewhere."""
    pen(p, ink)
    for y, x in ((5.5, 7.0), (10.5, 13.0), (15.5, 9.0)):
        line(p, (3.0, y), (17.0, y));facet(p, ink, (x - 1.6, y - 2.6), (x + 1.6, y - 2.6), (x + 1.6, y + 2.6), (x - 1.6, y + 2.6))


def prompt(p, ink, accent):
    """The terminal: a prompt and its cursor."""
    pen(p, ink, 1.8);line(p, (4.0, 5.0), (9.5, 10.0), (4.0, 15.0));line(p, (11.0, 15.5), (17.0, 15.5))


def lines(p, ink, accent):
    """A log: lines, one after another."""
    pen(p, ink);line(p, (3.0, 5.5), (17.0, 5.5));line(p, (3.0, 10.5), (12.5, 10.5));line(p, (3.0, 15.5), (15.0, 15.5))


def info(p, ink, accent):
    """About: a cell of the lattice with an i in it."""
    pen(p, ink);line(p, *HEX, close=True)
    pen(p, ink, 1.8);line(p, (10.0, 9.5), (10.0, 14.2));facet(p, ink, (10.0, 5.2), (11.4, 6.6), (10.0, 8.0), (8.6, 6.6))


def close(p, ink, accent):
    pen(p, ink, 1.8);line(p, (5.0, 5.0), (15.0, 15.0));line(p, (15.0, 5.0), (5.0, 15.0))


def receive(p, ink, accent):
    """Into the tray."""
    pen(p, ink);line(p, (3.5, 11.5), (3.5, 16.5), (16.5, 16.5), (16.5, 11.5));line(p, (10.0, 2.5), (10.0, 9.0))
    facet(p, ink, (10.0, 14.0), (5.2, 8.4), (14.8, 8.4))


def chip(p, ink, accent):
    """This computer: a chip and its pins."""
    facet(p, accent, (8.0, 8.0), (12.0, 8.0), (12.0, 12.0), (8.0, 12.0))
    pen(p, ink);p.drawRect(QRectF(5.5, 5.5, 9, 9))
    for a in (8.0, 12.0):
        line(p, (a, 5.5), (a, 2.5));line(p, (a, 14.5), (a, 17.5));line(p, (5.5, a), (2.5, a));line(p, (14.5, a), (17.5, a))


def book(p, ink, accent):
    """A book, open."""
    pen(p, ink);line(p, (10.0, 5.5), (3.5, 4.0), (3.5, 15.0), (10.0, 16.5), (16.5, 15.0), (16.5, 4.0), (10.0, 5.5));line(p, (10.0, 5.5), (10.0, 16.5))


def key(p, ink, accent):
    """A key of the keyboard."""
    facet(p, accent, (6.5, 5.5), (13.5, 5.5), (13.5, 11.5), (6.5, 11.5))
    pen(p, ink);p.drawRect(QRectF(3.5, 3.5, 13, 13));p.drawRect(QRectF(6.5, 5.5, 7, 6))


def stack(p, ink, accent):
    """The library: layers, as graphite is layers."""
    facet(p, accent, (10.0, 3.0), (17.0, 6.5), (10.0, 10.0), (3.0, 6.5))
    pen(p, ink);line(p, (10.0, 3.0), (17.0, 6.5), (10.0, 10.0), (3.0, 6.5), close=True);line(p, (3.0, 10.0), (10.0, 13.5), (17.0, 10.0));line(p, (3.0, 13.5), (10.0, 17.0), (17.0, 13.5))


def delta(p, ink, accent):
    """What changed."""
    pen(p, ink, 1.8);line(p, (10.0, 3.5), (17.0, 16.5), (3.0, 16.5), close=True)


def agenda(p, ink, accent):
    """A list of things, the first one done."""
    facet(p, ink, (3.0, 4.0), (6.5, 4.0), (6.5, 7.5), (3.0, 7.5))
    pen(p, ink);p.drawRect(QRectF(3.5, 9.5, 2.5, 2.5));p.drawRect(QRectF(3.5, 14.5, 2.5, 2.5))
    for y in (5.5, 10.5, 15.5):line(p, (9.0, y), (17.0, y))


def chain(p, ink, accent):
    """Two links."""
    pen(p, ink);p.drawRect(QRectF(2.5, 7.5, 8.5, 5.5));p.drawRect(QRectF(9.0, 7.5, 8.5, 5.5))


def star(p, ink, accent):
    """A favourite; what is new."""
    points = ((10.0, 2.5), (12.2, 7.8), (17.5, 10.0), (12.2, 12.2), (10.0, 17.5), (7.8, 12.2), (2.5, 10.0), (7.8, 7.8))
    facet(p, accent, *points);pen(p, ink);line(p, *points, close=True)


def split(p, ink, accent):
    """One view made two."""
    pen(p, ink);p.drawRect(QRectF(2.5, 4.5, 15, 11));line(p, (10.0, 4.5), (10.0, 15.5))


def picture(p, ink, accent):
    """Artwork: a framed view."""
    pen(p, ink);p.drawRect(QRectF(2.5, 4.5, 15, 11));line(p, (4.5, 13.5), (8.5, 9.5), (11.0, 12.0), (13.5, 9.0), (16.0, 12.0))
    facet(p, accent, (5.0, 6.5), (7.5, 6.5), (7.5, 9.0), (5.0, 9.0))


def letters(text, weight=QFont.DemiBold, italic=False, under=False, family='IBM Plex Sans', size=13.0):
    """A glyph that is type: the letter a writer already knows a style by."""
    def draw(p, ink, accent):
        font = QFont(family);font.setPixelSize(int(size));font.setWeight(weight);font.setItalic(italic)
        p.setFont(font);p.setPen(ink);p.drawText(QRectF(-4, 0, 28, 19 if under else 20), Qt.AlignCenter, text)
        if under:
            pen(p, ink, 1.4);line(p, (5.0, 17.5), (15.0, 17.5))
    return draw


# ---- the right-click (0.8.1, the owner: "We need to make its power easy to use and chain/pipe. With right click icons too")

def trash(p, ink, accent):
    """The Trash: a straight-sided can, its lid a facet."""
    facet(p, accent, (7.5, 2.5), (12.5, 2.5), (12.5, 4.5), (7.5, 4.5))
    pen(p, ink);line(p, (3.5, 4.5), (16.5, 4.5));line(p, (7.5, 4.5), (7.5, 2.5), (12.5, 2.5), (12.5, 4.5))
    line(p, (5.0, 4.5), (6.0, 17.5), (14.0, 17.5), (15.0, 4.5));line(p, (8.5, 7.5), (8.5, 14.5));line(p, (11.5, 7.5), (11.5, 14.5))


def pause(p, ink, accent):
    """Held: two solid bars (stop stays one square)."""
    facet(p, ink, (5.0, 4.5), (8.5, 4.5), (8.5, 15.5), (5.0, 15.5));facet(p, ink, (11.5, 4.5), (15.0, 4.5), (15.0, 15.5), (11.5, 15.5))


def funnel(p, ink, accent):
    """Keep rows where: a funnel of straight strokes, its band the accent."""
    facet(p, accent, (4.6, 5.5), (15.4, 5.5), (12.6, 8.5), (7.4, 8.5))
    pen(p, ink);line(p, (2.5, 3.5), (17.5, 3.5), (11.5, 10.5), (11.5, 17.0), (8.5, 15.5), (8.5, 10.5), close=True)


def ordering(p, ink, accent):
    """Sort by: two stems, one head up and one down."""
    pen(p, ink);line(p, (6.5, 6.5), (6.5, 17.5));line(p, (13.5, 2.5), (13.5, 13.5))
    facet(p, ink, (6.5, 2.0), (2.8, 7.0), (10.2, 7.0));facet(p, ink, (13.5, 18.0), (9.8, 13.0), (17.2, 13.0))


def gathered(p, ink, accent):
    """Count by: three short rules gathered by a bracket into one head."""
    pen(p, ink);line(p, (2.5, 4.5), (8.5, 4.5));line(p, (2.5, 10.5), (8.5, 10.5));line(p, (2.5, 16.5), (8.5, 16.5))
    line(p, (10.5, 4.5), (12.5, 4.5), (12.5, 16.5), (10.5, 16.5));line(p, (12.5, 10.5), (14.0, 10.5))
    facet(p, ink, (18.0, 10.5), (14.0, 7.2), (14.0, 13.8))


def watch(p, ink, accent):
    """Watch it: straight lids around a diamond pupil."""
    pen(p, ink);line(p, (2.0, 10.5), (6.5, 6.0), (13.5, 6.0), (18.0, 10.5), (13.5, 15.0), (6.5, 15.0), close=True)
    facet(p, ink, (10.0, 7.6), (12.9, 10.5), (10.0, 13.4), (7.1, 10.5))


def trace(p, ink, accent):
    """Trace it: three nodes on an elbow wire, ending in a facet."""
    facet(p, accent, (2.5, 2.5), (6.5, 2.5), (6.5, 6.5), (2.5, 6.5))
    pen(p, ink);p.drawRect(QRectF(2.5, 2.5, 4, 4));line(p, (4.5, 6.5), (4.5, 14.5), (11.5, 14.5))
    p.drawRect(QRectF(8.5, 8.5, 3, 3));line(p, (6.5, 10.0), (8.5, 10.0))
    facet(p, ink, (17.5, 14.5), (12.5, 11.2), (12.5, 17.8))


GLYPHS = {
    'trash': trash, 'pause': pause, 'filter': funnel, 'sort': ordering, 'group': gathered, 'watch': watch, 'trace': trace,
    'count': letters('#', QFont.DemiBold, size=14.0),
    'field': field, 'find': find, 'smaller': smaller, 'larger': larger, 'undo': undo, 'redo': redo, 'save': save,
    'previous': previous, 'next': following, 'cite': cite, 'table': table, 'more': more, 'note': note,
    'report': report, 'recalc': recalc, 'export': export, 'cell': cell, 'source': source,
    'document': document, 'again': again, 'stop': stop, 'pin': pin,
    'copy': copy, 'paste': paste, 'cut': cut, 'select': select, 'full': full, 'home': home, 'sliders': sliders, 'prompt': prompt,
    'lines': lines, 'info': info, 'close': close, 'receive': receive, 'chip': chip, 'book': book, 'key': key, 'stack': stack,
    'delta': delta, 'agenda': agenda, 'chain': chain, 'star': star, 'split': split, 'picture': picture,
    # the kinds of sheet, by what they draw, so a menu or a tab can wear them too
    'page': page, 'found': found, 'asked': asked, 'limit': limit, 'steps': steps, 'running': running, 'folder': folder,
    'port': port, 'window': window, 'reach': reach, 'rooms': rooms,
    'bold': letters('B', QFont.Bold, size=14.0), 'italic': letters('I', QFont.DemiBold, italic=True, size=14.0),
    'underline': letters('U', QFont.DemiBold, under=True, size=12.0),
    'h1': letters('H1'), 'h2': letters('H2', QFont.Medium, size=12.0), 'h3': letters('H3', QFont.Normal, size=11.0),
    'body': letters('¶', QFont.Normal, size=14.0), 'code': letters('{}', QFont.Medium, family='IBM Plex Mono', size=12.0),
    'plain': letters('Aa', QFont.Normal, size=12.0),
}

# What each kind of sheet on the Field is drawn as (field_model.KINDS). A sheet seen from far off is this glyph and its name.
KIND = {'source': page, 'folder': folder, 'sheet': table, 'method': steps, 'calculation': report, 'job': running,
        'document': cell, 'finding': found, 'question': asked, 'condition': limit,
        'interface': port, 'program': window, 'endpoint': reach, 'app': rooms}
