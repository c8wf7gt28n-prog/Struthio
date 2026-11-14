"""Thumbnails for things people look at: pictures, PDF first pages, boards and drill files, the first lines of text.

Everything is drawn here from the file's own bytes with what Ledger already has (Qt's image and PDF readers, the
universal viewer's Gerber and drill parser). A file that cannot be drawn gets a plain card with its kind, never an error.
Results are cached by path, size and modification time.
"""
from __future__ import annotations
from pathlib import Path
from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QImage, QImageReader, QPainter, QPen, QPixmap
from .shell2 import CARD, LINE, LINE_STRONG, MONO, QUIET, RAISED, TEXT

TEXT_KINDS = ('text', 'code', 'markdown', 'csv', 'json')
_cache = {}
MAX_IMAGE_PIXELS = 64_000_000


# 4.5: thumbnails belong to the interface until a file is opened, so they are drawn in its own tones: dark parts in
# graphite, the middle in pencil, light parts in the paper sheet. The file itself shows its true colours when opened.
TONES = ((0.0, (0x50, 0x4d, 0x46)), (0.42, (0xa3, 0x9c, 0x8f)), (0.74, (0xe9, 0xd6, 0x9c)), (1.0, (0xff, 0xfd, 0xf8)))  # graphite, warm grey, pencil, sheet


def _ramp():
    table = []
    for level in range(256):
        x = level / 255
        for (x0, c0), (x1, c1) in zip(TONES, TONES[1:]):
            if x0 <= x <= x1:
                f = (x - x0) / (x1 - x0);table.append(tuple(round(a + (b - a) * f) for a, b in zip(c0, c1)));break
    return [bytes(c[i] for c in table) for i in range(3)]


RAMP = _ramp()


def paper_tone(image):
    """Any picture, in the interface's tones: by brightness, from graphite through pencil to sheet. Byte tables only."""
    if image is None or image.isNull():return image
    flat = QImage(image.size(), QImage.Format_ARGB32_Premultiplied);flat.fill(QColor(CARD))
    p = QPainter(flat);p.drawImage(0, 0, image);p.end()  # transparency sits on the sheet
    gray = flat.convertToFormat(QImage.Format_Grayscale8)
    width, height, stride = gray.width(), gray.height(), gray.bytesPerLine()
    raw = bytes(gray.constBits())[:stride * height]
    levels = b''.join(raw[row * stride:row * stride + width] for row in range(height))
    low, high = (min(levels), max(levels)) if levels else (0, 255)
    if high - low < 230 and high > low:  # a faint drawing is stretched across the whole range first, so its lines stay readable
        levels = levels.translate(bytes(max(0, min(255, round((v - low) * 255 / (high - low)))) for v in range(256)))
    out = bytearray(4 * width * height)
    out[0::4] = levels.translate(RAMP[2]);out[1::4] = levels.translate(RAMP[1]);out[2::4] = levels.translate(RAMP[0]);out[3::4] = b'\xff' * (width * height)
    toned = QImage(bytes(out), width, height, 4 * width, QImage.Format_ARGB32)
    return toned.copy()  # owns its pixels


def card(size, words, sub=''):
    image = QImage(size, size, QImage.Format_ARGB32_Premultiplied);image.fill(QColor(CARD))
    p = QPainter(image);p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QPen(QColor(LINE), 1));p.drawRoundedRect(QRectF(.5, .5, size - 1, size - 1), 8, 8)
    f = QFont('IBM Plex Sans');f.setPixelSize(max(11, size // 7));f.setWeight(QFont.DemiBold);p.setFont(f);p.setPen(QColor(TEXT))
    p.drawText(QRectF(8, 0, size - 16, size * .62), Qt.AlignHCenter | Qt.AlignBottom | Qt.TextWordWrap, words)
    if sub:
        f.setWeight(QFont.Normal);f.setPixelSize(max(10, size // 10));p.setFont(f);p.setPen(QColor(QUIET))
        p.drawText(QRectF(8, size * .66, size - 16, size * .3), Qt.AlignHCenter | Qt.AlignTop, sub)
    p.end();return image


def peek(path, limit=3):
    """How many sheets to draw peeking out of a folder: its visible entries, up to three. Reads one directory listing."""
    if path is None:return 1
    try:
        n = 0
        with __import__('os').scandir(path) as entries:
            for entry in entries:
                if not entry.name.startswith('.'):
                    n += 1
                    if n >= limit:break
        return n
    except OSError:return 0


EMBLEMS = {'exports': 'out', 'export': 'out', 'arrived': 'in', 'received': 'in', 'deliveries': 'in', 'inbox': 'in',
           'slate': 'slate', 'working copies': 'copies', 'projects': 'code', 'code': 'code', 'src': 'code', 'notes': 'lines', 'ideas': 'lines'}


def emblem(p, kind, cx, cy, u):
    """A small graphite mark on the front of a well-known folder, drawn in the same hand as the menu icons."""
    from PySide6.QtCore import QPointF
    pen = QPen(QColor(TEXT), max(1.3, u * .75));pen.setCapStyle(Qt.RoundCap);pen.setJoinStyle(Qt.RoundJoin);p.setPen(pen);p.setBrush(Qt.NoBrush)
    P = lambda x, y:QPointF(cx + x * u, cy + y * u)
    if kind == 'trash':
        p.drawLine(P(-4, -3), P(4, -3));p.drawLine(P(-1.5, -4.5), P(1.5, -4.5))
        p.drawPolyline([P(-3, -3), P(-2.4, 4), P(2.4, 4), P(3, -3)]);p.drawLine(P(0, -1), P(0, 2.5))
    elif kind in ('in', 'out'):
        p.drawPolyline([P(-4.5, 1), P(-4.5, 4), P(4.5, 4), P(4.5, 1)])
        if kind == 'in':p.drawLine(P(0, -5), P(0, 1.5));p.drawPolyline([P(-2.2, -.8), P(0, 1.5), P(2.2, -.8)])
        else:p.drawLine(P(0, 1.5), P(0, -5));p.drawPolyline([P(-2.2, -2.8), P(0, -5), P(2.2, -2.8)])
    elif kind == 'slate':
        f = QFont('Parisienne');f.setPixelSize(max(12, round(u * 11)));p.setFont(f);p.setPen(QColor(TEXT))
        p.drawText(QRectF(cx - 8 * u, cy - 6.5 * u, 16 * u, 13 * u), Qt.AlignCenter, 'S')
    elif kind == 'copies':
        p.setBrush(QColor(CARD));p.drawRoundedRect(QRectF(cx - 4 * u, cy - 4.5 * u, 6 * u, 7.5 * u), u, u)
        p.drawRoundedRect(QRectF(cx - 1.5 * u, cy - 2.5 * u, 6 * u, 7.5 * u), u, u)
    elif kind == 'code':
        p.drawPolyline([P(-2, -3), P(-5, 0), P(-2, 3)]);p.drawPolyline([P(2, -3), P(5, 0), P(2, 3)]);p.drawLine(P(1, -4), P(-1, 4))
    elif kind == 'lines':
        for y in (-3, 0, 3):p.drawLine(P(-4.5, y), P(4.5 if y < 3 else 1.5, y))


def folder(size, path=None):
    """A pencil folder with depth: the back with its tab, sheets peeking out (as many as it holds, up to three), the
    front flap with a lit edge, and a small graphite mark on the folders everyone knows (Trash, Egress, Ingress, Slate…)."""
    image = QImage(size, size, QImage.Format_ARGB32_Premultiplied);image.fill(Qt.transparent)
    p = QPainter(image);p.setRenderHint(QPainter.Antialiasing)
    from .shell2 import PENCIL_DEEP
    from .boss_theme import CUE as AMBER, CUE_EDGE as AMBER_EDGE      # 0.8.3: a drawn icon, not a highlight
    u = size / 96.0;w, h = size * .80, size * .58;x, y = (size - w) / 2, size * .27
    edge = QPen(QColor(AMBER_EDGE), max(1.0, 1.3 * u))
    # the back, with its tab
    from PySide6.QtGui import QPainterPath
    back = QPainterPath();r = 6 * u;tab_w, tab_h = w * .38, 9 * u
    back.moveTo(x, y + r);back.quadTo(x, y - tab_h, x + r, y - tab_h);back.lineTo(x + tab_w - 3 * u, y - tab_h)
    back.quadTo(x + tab_w, y - tab_h, x + tab_w + 4 * u, y);back.lineTo(x + w - r, y);back.quadTo(x + w, y, x + w, y + r)
    back.lineTo(x + w, y + h - r);back.quadTo(x + w, y + h, x + w - r, y + h);back.lineTo(x + r, y + h);back.quadTo(x, y + h, x, y + h - r);back.closeSubpath()
    p.setPen(edge);p.setBrush(QColor(PENCIL_DEEP));p.drawPath(back)
    # sheets peeking out: one per entry, up to three, each a little higher and turned
    n = peek(path)
    for i in range(n):
        p.save();p.translate(x + w / 2, y + h * .5);p.rotate((-3.5, 2.5, -1)[i] if n > 1 else -1.5)
        sw, sh = w * (.80 - .04 * i), h * .9;top = -h * .5 - (5 + 3.5 * i) * u
        p.setPen(QPen(QColor(LINE), max(1.0, u)));p.setBrush(QColor(CARD));p.drawRoundedRect(QRectF(-sw / 2, top, sw, sh), 2 * u, 2 * u)
        if i == n - 1:  # the top sheet carries a few written lines
            p.setPen(QPen(QColor(LINE_STRONG), max(1.0, .9 * u)))
            for k, frac in enumerate((.62, .78, .5)):p.drawLine(int(-sw / 2 + 7 * u), int(top + (6 + 5 * k) * u), int(-sw / 2 + 7 * u + sw * frac * .8), int(top + (6 + 5 * k) * u))
        p.restore()
    # the front flap, a touch lower than the back, its top edge lit
    fy = y + h * .2;front = QRectF(x, fy, w, h - (fy - y))
    p.setPen(edge);p.setBrush(QColor(AMBER));p.drawRoundedRect(front, r, r)
    p.setPen(QPen(QColor(CARD), max(1.0, 1.2 * u)));p.drawLine(int(x + r), int(fy + 1.6 * u), int(x + w - r), int(fy + 1.6 * u))
    p.setPen(QPen(QColor(PENCIL_DEEP), max(1.0, 1.4 * u)));p.drawLine(int(x + r), int(fy + front.height() - 2 * u), int(x + w - r), int(fy + front.height() - 2 * u))
    mark = EMBLEMS.get(Path(path).name.lower()) if path is not None else None
    if mark:emblem(p, mark, x + w / 2, fy + front.height() / 2 + u, u * 1.9)
    p.end();return image


def smart_folder(size):
    """A folder that is a question: the pencil folder with a graphite lens on it."""
    image = folder(size);p = QPainter(image);p.setRenderHint(QPainter.Antialiasing)
    r = size * .11;cx, cy = size * .5, size * .64
    p.setPen(QPen(QColor(TEXT), max(1.5, size / 40)));p.setBrush(QColor(CARD));p.drawEllipse(QRectF(cx - r, cy - r, 2 * r, 2 * r))
    p.drawLine(int(cx + r * .7), int(cy + r * .7), int(cx + r * 1.8), int(cy + r * 1.8));p.end()
    return image


def picture(path, size):
    reader = QImageReader(str(path));reader.setAutoTransform(True)
    full = reader.size()
    if not full.isValid() or full.width() * full.height() > MAX_IMAGE_PIXELS:return None
    reader.setScaledSize(full.scaled(QSize(size, size), Qt.KeepAspectRatio))
    image = reader.read()
    return None if image.isNull() else image


def pdf(path, size):
    from PySide6.QtPdf import QPdfDocument
    document = QPdfDocument()
    if document.load(str(path)) != QPdfDocument.Error.None_ or document.pageCount() < 1:return None
    page = document.pagePointSize(0)
    target = page.toSize().scaled(QSize(size, size), Qt.KeepAspectRatio) if page.isValid() else QSize(size, size)
    image = document.render(0, target);document.close()
    if image.isNull():return None
    framed = QImage(image.size(), QImage.Format_ARGB32_Premultiplied);framed.fill(QColor('#ffffff'))
    p = QPainter(framed);p.drawImage(0, 0, image);p.setPen(QPen(QColor(LINE), 1));p.drawRect(0, 0, framed.width() - 1, framed.height() - 1);p.end()
    return framed


def board(path, size):
    from PySide6.QtWidgets import QGraphicsScene
    from .universal_view import Source, describe
    from .universal_viewer_qt import UniversalViewerTab
    view = describe(Source.file(path), with_hash=False)
    layers = (view.get('gerber') or {}).get('layers') or []
    if not layers:return None
    scene = QGraphicsScene()
    for layer in layers:UniversalViewerTab.draw_layer(scene, layer)
    from PySide6.QtWidgets import QAbstractGraphicsShapeItem, QGraphicsLineItem
    for shape in scene.items():  # at thumbnail size a 0.1 mm line is thinner than a pixel: draw every stroke at least 1.5 px
        if isinstance(shape, QGraphicsLineItem):
            pen = shape.pen();pen.setCosmetic(True);pen.setWidthF(max(1.5, pen.widthF()));shape.setPen(pen)
        elif isinstance(shape, QAbstractGraphicsShapeItem) and shape.pen().style() != Qt.NoPen:
            pen = shape.pen();pen.setCosmetic(True);pen.setWidthF(1.2);shape.setPen(pen)
    bounds = scene.itemsBoundingRect()
    if bounds.isEmpty():return None
    image = QImage(size, size, QImage.Format_ARGB32_Premultiplied);image.fill(QColor(RAISED))  # a recessed sheet, never a dark slab
    p = QPainter(image);p.setRenderHint(QPainter.Antialiasing)
    margin = size * .08;target = QRectF(margin, margin, size - 2 * margin, size - 2 * margin)
    p.translate(0, size);p.scale(1, -1)  # boards are drawn with y up
    scene.render(p, target, bounds, Qt.KeepAspectRatio);p.end()
    return image


def text(path, size):
    with open(path, 'rb') as f:raw = f.read(2048)
    lines = raw.decode('utf-8', 'replace').replace('\t', '  ').splitlines()[:14]
    image = QImage(size, size, QImage.Format_ARGB32_Premultiplied);image.fill(QColor(CARD))
    p = QPainter(image);p.setPen(QPen(QColor(LINE), 1));p.drawRect(0, 0, size - 1, size - 1)
    f = QFont(MONO);f.setPixelSize(max(7, size // 16));p.setFont(f);p.setPen(QColor(TEXT))
    step = f.pixelSize() + 2;y = 6 + f.pixelSize()
    for line in lines:
        p.drawText(6, y, line[:60]);y += step
        if y > size - 4:break
    p.end();return image


def thumbnail(path, kind, size=96):
    """A QPixmap for one entry in Files. Never raises."""
    path = Path(path)
    try:
        stat = path.stat();key = (str(path), stat.st_size, stat.st_mtime, size)
    except OSError:
        return QPixmap.fromImage(card(size, '?'))
    if key in _cache:return _cache[key]
    image = None
    try:
        from .view_modules import thumbnail as module_thumbnail
        image = module_thumbnail(path, kind, size) if kind != 'folder' else None
        if image is not None:pass
        elif kind == 'folder':image = folder(size, path)
        elif kind == 'smart':image = smart_folder(size)
        elif kind == 'image':image = picture(path, size)
        elif kind == 'pdf':image = pdf(path, size)
        elif kind in ('gerber', 'excellon'):image = board(path, size)
        elif kind in TEXT_KINDS:image = text(path, size)
    except Exception:
        image = None
    if image is not None and kind not in ('folder', 'smart') + TEXT_KINDS:image = paper_tone(image)  # cards, folders and text are drawn in the tones already
    if image is None:
        from .files_service import KIND_WORDS
        image = card(size, (path.suffix[1:].upper() or KIND_WORDS.get(kind, kind.title()))[:8], KIND_WORDS.get(kind, ''))
    pixmap = QPixmap.fromImage(image)
    if len(_cache) > 2000:_cache.clear()
    _cache[key] = pixmap
    return pixmap
