"""Small drawn pictures for the chain menu: what each link does, at a glance. Graphite lines on paper; the endings (then,
and what it offers) carry a touch of eraser pink. Drawn here, so they stay sharp at any size and inside the palette."""
from __future__ import annotations
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPen, QPixmap

GRAPHITE, PINK, SIZE = QColor('#504d46'), QColor('#cba5a4'), 18
_cache = {}
TEXT_GLYPHS = {'gt': '>', 'lt': '<', 'ge': '≥', 'le': '≤', 'eq': '=', 'ne': '≠', 'count': '#', 'sum': 'Σ', 'avg': 'x̄'}
ENDINGS = {'then', 'console', 'sheetsave', 'watch', 'agenda', 'keep', 'copy', 'shell'}


def icon(name):
    if name not in _cache:
        made = QIcon(draw(name))
        from . import boss_theme as t
        if t.APPEARANCE == 'kasandra':      # 0.8.3: the row under the pointer is her solid burnt-yellow bar: draw it in the bar's ink
            on_bar = draw(name, QColor(t.ON_BAR))
            for mode in (QIcon.Active, QIcon.Selected):made.addPixmap(on_bar, mode)
        _cache[name] = made
    return _cache[name]


def draw(name, ink=None):
    pix = QPixmap(SIZE * 2, SIZE * 2);pix.fill(Qt.transparent);pix.setDevicePixelRatio(2)
    p = QPainter(pix);p.setRenderHint(QPainter.Antialiasing)
    ink = ink if ink is not None else (PINK if name in ENDINGS else GRAPHITE)
    pen = QPen(ink, 1.6);pen.setCapStyle(Qt.RoundCap);pen.setJoinStyle(Qt.RoundJoin);p.setPen(pen);p.setBrush(Qt.NoBrush)
    L = lambda x1, y1, x2, y2:p.drawLine(QPointF(x1, y1), QPointF(x2, y2))
    R = lambda x, y, w, h, r=1.5:p.drawRoundedRect(QRectF(x, y, w, h), r, r)
    if name in TEXT_GLYPHS:
        font = QFont('IBM Plex Sans');font.setPixelSize(15);font.setWeight(QFont.DemiBold);p.setFont(font)
        p.drawText(QRectF(0, -1, SIZE, SIZE), Qt.AlignCenter, TEXT_GLYPHS[name])
    elif name == 'rows':
        for y in (4.5, 9, 13.5):L(3, y, 15, y)
    elif name == 'lines':
        for y, w in ((4.5, 12), (9, 8), (13.5, 10)):L(3, y, 3 + w, y)
    elif name in ('sheet', 'table'):
        R(2.5, 3, 13, 12);L(2.5, 7, 15.5, 7);L(7, 3, 7, 15);L(2.5, 11, 15.5, 11)
    elif name == 'headings':
        L(3, 4, 15, 4);L(5, 9, 15, 9);L(7, 14, 15, 14);p.setPen(QPen(ink, 2.4));L(3, 4, 4, 4)
    elif name == 'layers':
        for y in (5, 9, 13):
            path = QPainterPath(QPointF(9, y - 3));path.lineTo(15, y);path.lineTo(9, y + 3);path.lineTo(3, y);path.closeSubpath();p.drawPath(path)
    elif name == 'texts':
        L(4, 4, 14, 4);L(9, 4, 9, 14)
    elif name == 'facts':
        p.drawEllipse(QRectF(3, 3, 12, 12));L(9, 8, 9, 12.5);p.drawPoint(QPointF(9, 5.6))
    elif name == 'where':  # a funnel
        path = QPainterPath(QPointF(3, 4));path.lineTo(15, 4);path.lineTo(10.5, 9.5);path.lineTo(10.5, 14);path.lineTo(7.5, 15.5);path.lineTo(7.5, 9.5);path.closeSubpath();p.drawPath(path)
    elif name == 'sort':
        L(6, 3, 6, 15);L(3.5, 5.5, 6, 3);L(8.5, 5.5, 6, 3);L(12, 3, 12, 15);L(9.5, 12.5, 12, 15);L(14.5, 12.5, 12, 15)
    elif name == 'up':
        L(9, 15, 9, 3);L(5, 7, 9, 3);L(13, 7, 9, 3)
    elif name == 'down':
        L(9, 3, 9, 15);L(5, 11, 9, 15);L(13, 11, 9, 15)
    elif name == 'group':
        R(3, 3, 6, 5);R(3, 10, 6, 5);L(9, 5.5, 12, 9);L(9, 12.5, 12, 9);R(12, 7, 3.5, 4, 1)
    elif name == 'column':
        R(3, 3, 12, 12);p.fillRect(QRectF(7, 3, 4, 12), QColor(ink.red(), ink.green(), ink.blue(), 70));L(7, 3, 7, 15);L(11, 3, 11, 15)
    elif name == 'add':
        R(3, 3, 8, 12);L(7, 3, 7, 15);L(13.5, 6, 13.5, 12);L(10.5, 9, 16.5, 9)
    elif name == 'join':
        p.drawEllipse(QRectF(2.5, 5, 8, 8));p.drawEllipse(QRectF(7.5, 5, 8, 8))
    elif name == 'missing':
        p.drawArc(QRectF(3, 3, 12, 12), 40 * 16, 280 * 16);L(11, 9, 16, 9)
    elif name == 'take':
        for y in (4, 8):L(3, y, 15, y)
        p.setPen(QPen(QColor(ink.red(), ink.green(), ink.blue(), 90), 1.4));L(3, 12, 15, 12);L(3, 15, 15, 15)
    elif name in ('min', 'max'):
        L(3, 15, 15, 15);L(3, 15, 3, 3)
        for x, h in ((6, 6), (9.5, 10), (13, 4)):L(x, 15, x, 15 - h)
        p.setPen(QPen(ink, 2.4));x, h = ((13, 4) if name == 'min' else (9.5, 10));L(x, 15, x, 15 - h)
    elif name == 'then':
        L(3, 9, 14, 9);L(10, 5, 14, 9);L(10, 13, 14, 9)
    elif name == 'console':
        R(2, 3, 14, 12);L(5, 7, 7.5, 9);L(5, 11, 7.5, 9);L(9, 11.5, 13, 11.5)
    elif name == 'sheetsave':
        R(2.5, 2.5, 10, 9);L(2.5, 6, 12.5, 6);L(6.5, 2.5, 6.5, 11.5);L(13, 10, 13, 16);L(10.5, 13.5, 13, 16);L(15.5, 13.5, 13, 16)
    elif name == 'watch':
        path = QPainterPath(QPointF(2, 9));path.quadTo(9, 2, 16, 9);path.quadTo(9, 16, 2, 9);p.drawPath(path);p.drawEllipse(QRectF(6.8, 6.8, 4.4, 4.4))
    elif name == 'agenda':
        R(3.5, 3, 11, 13);L(6, 3, 6, 1.8);L(12, 3, 12, 1.8);L(6, 8, 7.5, 9.5);L(7.5, 9.5, 10.5, 6.5);L(6, 13, 12, 13)
    elif name == 'keep':
        path = QPainterPath(QPointF(5, 2.5));path.lineTo(13, 2.5);path.lineTo(13, 15.5);path.lineTo(9, 12);path.lineTo(5, 15.5);path.closeSubpath();p.drawPath(path)
    elif name == 'copy':
        R(2.5, 5.5, 9, 10);R(6.5, 2.5, 9, 10)
    elif name == 'shell':
        font = QFont('IBM Plex Mono');font.setPixelSize(14);font.setWeight(QFont.DemiBold);p.setFont(font);p.drawText(QRectF(0, -1, SIZE, SIZE), Qt.AlignCenter, '$')
    elif name in ('chain', 'start'):
        p.drawEllipse(QRectF(2, 6, 7, 6));p.drawEllipse(QRectF(9, 6, 7, 6))
        if name == 'start':p.setBrush(ink);p.drawEllipse(QRectF(3.5, 7.5, 4, 3))
    elif name == 'edit':
        L(4, 14, 13, 5);L(11, 3, 15, 7);L(4, 14, 3.5, 15.5)
    elif name == 'dot':
        p.setBrush(ink);p.drawEllipse(QRectF(7, 7, 4, 4))
    p.end()
    return pix


def name_for(text, parent_title=''):
    """Which picture a menu line gets, from its words."""
    words = text.split('    ')[0].strip().lower();parent = parent_title.split('    ')[0].strip().lower()
    exact = {'rows': 'rows', 'lines': 'lines', 'headings': 'headings', 'layers': 'layers', 'texts': 'texts', 'facts': 'facts',
             'where': 'where', 'sort': 'sort', 'group by': 'group', 'select': 'column', 'add a column…': 'add', 'join with': 'join', 'take': 'take',
             'count': 'count', 'then': 'then', 'over': 'gt', 'under': 'lt', 'at least': 'ge', 'at most': 'le', 'is': 'eq', 'is not': 'ne', 'has': 'facts',
             'smallest first': 'up', 'largest first': 'down', 'show it in the console': 'console', 'save as a sheet': 'sheetsave',
             'watch it': 'watch', 'add to the agenda': 'agenda', 'keep this chain…': 'keep', 'copy the stac': 'copy', 'shell': 'shell',
             'type a command…': 'shell', 'start from': 'start', 'console': 'console', 'edit the ledger menu…': 'edit', 'edit the graphite menu…': 'edit', 'choose columns…': 'column'}
    if words in exact:return exact[words]
    for lead, picture in (('sheet ', 'sheet'), ('sum ', 'sum'), ('avg ', 'avg'), ('min ', 'min'), ('max ', 'max'), ('join on', 'join'),
                          ('missing on', 'missing'), ('only ', 'column'), ('first ', 'take'), ('@', 'chain')):
        if words.startswith(lead):return picture
    if parent in ('where', 'sort', 'group by'):return 'column'
    if parent == 'join with':return 'table'
    if parent in ('over', 'under', 'at least', 'at most', 'is', 'is not', 'has'):return 'dot'
    if parent == 'start from':return 'table' if words.endswith(('.csv', '.xlsx')) else 'facts'
    return None


def dress(menu):
    """Give every line of a menu its picture, now and whenever it opens (menus that fill themselves when opened included)."""
    from PySide6.QtWidgets import QMenu
    from shiboken6 import isValid
    if not isValid(menu):return
    titles = {m.menuAction(): m for m in menu.findChildren(QMenu, options=Qt.FindDirectChildrenOnly)}
    for action in menu.actions():
        if not isValid(action) or action.isSeparator():continue
        picture = name_for(action.text(), menu.title())
        if picture:action.setIcon(icon(picture));action.setIconVisibleInMenu(True)
        sub = titles.get(action)
        if sub is not None and not sub.property('dressed'):
            sub.setProperty('dressed', True);sub.aboutToShow.connect(lambda m=sub:dress(m));dress(sub)
    if not menu.property('dressed'):menu.setProperty('dressed', True);menu.aboutToShow.connect(lambda m=menu:dress(m))
