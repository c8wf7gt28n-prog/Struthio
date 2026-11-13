"""A document's page, seen in the desk's light.

A PDF page is a white sheet, and on a dark desk a white sheet is the one glaring thing in view (the owner, 13 November
2026: "No ugly white boxes that stand out like a sore thumb"). So where Graphite shows the picture of a page, it shows
it in the desk's light: the same page, every mark where it is, each colour multiplied by one low warm tone, so white
paper comes down to that tone and black ink stays black. Nothing of the document is changed: not the file, not its
citation, not what is exported, shared or read by OCR. Only how brightly the picture is shown here.

The page's own light is one line away (More, on a PDF page) and the choice is kept in the session as page_own_light.
"""
from PySide6.QtGui import QColor, QPainter, QPixmap

DESK_LIGHT = '#8c826b'      # what a page is multiplied by: white paper becomes this, black ink stays black


def own(host):
    """True when the owner has asked for pages as their files have them."""
    return bool(getattr(getattr(host, 'session', None), 'state', {}).get('page_own_light', False))


def wash(painter, rect):
    """Bring what was just painted in rect down into the desk's light."""
    painter.save();painter.setCompositionMode(QPainter.CompositionMode_Multiply);painter.fillRect(rect, QColor(DESK_LIGHT));painter.restore()


def lit(pixmap, own_light=False):
    """The picture of a page as it is to be shown: a copy in the desk's light, or the picture itself in its own."""
    if own_light or pixmap is None or pixmap.isNull():return pixmap
    shown = QPixmap(pixmap);painter = QPainter(shown);wash(painter, shown.rect());painter.end()
    return shown
