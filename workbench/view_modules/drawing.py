"""Drawings: DXF 2D CAD (text DXF). Lines, polylines, circles, arcs, points and text, by layer. Pan, zoom, show or hide
layers, and measure between two clicked points. Nothing is edited; for drafting, use a CAD program.

The reader follows DXF's group-code pairs with the standard library. Blocks are not expanded (an INSERT shows as a mark),
and binary DXF is named but not drawn.
"""
from __future__ import annotations
import math

KINDS = ('dxf',)
MAX_ENTITIES = 200_000
DRAWN = ('LINE', 'LWPOLYLINE', 'POLYLINE', 'CIRCLE', 'ARC', 'POINT', 'TEXT', 'MTEXT', 'INSERT')


def claim(source, head):
    if source.suffix == '.dxf':return 'dxf'
    text = head[:64].replace(b'\r', b'')
    if text.lstrip().startswith(b'0\nSECTION') or text.lstrip().startswith(b'999\n'):return 'dxf'
    return None


def pairs(text):
    lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    for i in range(0, len(lines) - 1, 2):
        try:yield int(lines[i].strip()), lines[i + 1].strip()
        except ValueError:continue


def parse(text):
    """Entities from the ENTITIES section: [{'type', 'layer', ...geometry}]."""
    entities = [];section = None;current = None;polyline = None;expect_name = False
    def close():
        nonlocal current
        if current is not None and current['type'] in DRAWN and len(entities) < MAX_ENTITIES:entities.append(current)
        current = None
    for code, value in pairs(text):
        if code == 0:
            if value == 'SECTION':close();expect_name = True;continue
            if value == 'ENDSEC':close();section = None;continue
            if section != 'ENTITIES':continue
            if polyline is not None and current is not None and current['type'] == '_VERTEX':
                if 'x' in current and 'y' in current:polyline['points'].append((current['x'], current['y']))  # the vertex just read
                current = None
            if value == 'VERTEX' and polyline is not None:current = {'type': '_VERTEX'};continue
            if value == 'SEQEND' and polyline is not None:
                polyline.pop('x', None);polyline.pop('y', None)  # a POLYLINE's own 10/20 is a placeholder, not a point
                if len(entities) < MAX_ENTITIES:entities.append(polyline)
                polyline = None;continue
            close()
            current = {'type': value, 'layer': '0', 'points': []}
            if value == 'POLYLINE':polyline = current;current = None
            continue
        if expect_name and code == 2:section = value;expect_name = False;continue
        target = current if current is not None else polyline
        if target is None:continue
        try:
            if code == 8:target['layer'] = value
            elif code == 10:
                if target['type'] == 'LWPOLYLINE':target['points'].append([float(value), None])
                else:target['x'] = float(value)
            elif code == 20:
                if target['type'] == 'LWPOLYLINE' and target['points']:target['points'][-1][1] = float(value)
                else:target['y'] = float(value)
            elif code == 11:target['x2'] = float(value)
            elif code == 21:target['y2'] = float(value)
            elif code == 40:target['r'] = float(value)
            elif code == 50:target['a1'] = float(value)
            elif code == 51:target['a2'] = float(value)
            elif code == 1:target['text'] = value
            elif code == 70 and target['type'] in ('LWPOLYLINE', 'POLYLINE'):target['closed'] = bool(int(value) & 1)
        except ValueError:pass
    close()
    for e in entities:
        if e['type'] == 'LWPOLYLINE':e['points'] = [tuple(p) for p in e['points'] if p[1] is not None]
    return entities


def extents(entities):
    xs, ys = [], []
    for e in entities:
        if 'x' in e and 'y' in e:
            r = e.get('r', 0) if e['type'] in ('CIRCLE', 'ARC') else 0
            if e['type'] == 'ARC':  # only the part of the circle the arc sweeps
                a1, a2 = e.get('a1', 0.0), e.get('a2', 360.0);span = (a2 - a1) % 360 or 360
                for k in range(0, 33):
                    angle = math.radians(a1 + span * k / 32);xs.append(e['x'] + r * math.cos(angle));ys.append(e['y'] + r * math.sin(angle))
            else:xs += [e['x'] - r, e['x'] + r];ys += [e['y'] - r, e['y'] + r]
        if 'x2' in e:xs.append(e['x2']);ys.append(e['y2'])
        for x, y in e.get('points', []):xs.append(x);ys.append(y)
    return (min(xs), min(ys), max(xs), max(ys)) if xs else None


def describe(source, view):
    raw = source.read(0, 64 * 1024 * 1024)
    if raw.startswith(b'AutoCAD Binary DXF'):view['notice'] = 'A binary DXF: named here, not drawn.';return
    from ..universal_view import decode
    text, encoding = decode(raw);entities = parse(text)
    view['drawing'] = entities
    layers = {};kinds = {}
    for e in entities:layers[e['layer']] = layers.get(e['layer'], 0) + 1;kinds[e['type']] = kinds.get(e['type'], 0) + 1
    box = extents(entities)
    view['summary'] += [('Entities', '{:,}'.format(len(entities))), ('Layers', str(len(layers)))]
    view['summary'] += [(k.title(), str(v)) for k, v in sorted(kinds.items(), key=lambda kv:-kv[1])[:6]]
    if box:view['summary'].append(('Extents', '%.4g × %.4g' % (box[2] - box[0], box[3] - box[1])))
    if kinds.get('INSERT'):view['notice'] = 'Blocks (INSERT) show as small marks: their contents are not expanded.'


DESCRIBERS = {'dxf': describe}


def draw(scene, entities, hidden=()):
    from PySide6.QtCore import QPointF, QRectF
    from PySide6.QtGui import QColor, QFont, QPainterPath, QPen
    pen = QPen(QColor('#504d46'), 0);pen.setCosmetic(True);pen.setWidthF(1.2)
    marks = QPen(QColor('#cba5a4'), 0);marks.setCosmetic(True);marks.setWidthF(1.5)
    for e in entities:
        if e['layer'] in hidden:continue
        kind = e['type']
        if kind == 'LINE' and 'x2' in e:scene.addLine(e['x'], e['y'], e['x2'], e['y2'], pen)
        elif kind in ('LWPOLYLINE', 'POLYLINE') and len(e['points']) > 1:
            path = QPainterPath(QPointF(*e['points'][0]))
            for point in e['points'][1:]:path.lineTo(QPointF(*point))
            if e.get('closed'):path.closeSubpath()
            scene.addPath(path, pen)
        elif kind == 'CIRCLE' and 'r' in e:scene.addEllipse(QRectF(e['x'] - e['r'], e['y'] - e['r'], 2 * e['r'], 2 * e['r']), pen)
        elif kind == 'ARC' and 'r' in e:
            a1, a2 = e.get('a1', 0.0), e.get('a2', 360.0);span = (a2 - a1) % 360 or 360
            rect = QRectF(e['x'] - e['r'], e['y'] - e['r'], 2 * e['r'], 2 * e['r'])
            path = QPainterPath();path.arcMoveTo(rect, -a1);path.arcTo(rect, -a1, -span);scene.addPath(path, pen)
        elif kind in ('POINT', 'INSERT') and 'x' in e:
            size = 0.5;scene.addLine(e['x'] - size, e['y'], e['x'] + size, e['y'], marks);scene.addLine(e['x'], e['y'] - size, e['x'], e['y'] + size, marks)
        elif kind in ('TEXT', 'MTEXT') and 'x' in e and e.get('text'):
            item = scene.addSimpleText(e['text'].replace('\\P', ' ')[:200]);item.setBrush(QColor('#504d46'))
            height = e.get('r') or 2.5;f = QFont('IBM Plex Sans');f.setPixelSize(12);item.setFont(f)
            item.setScale(height / 12);item.setPos(e['x'], e['y'] + height);item.setTransform(item.transform().scale(1, -1))


def DrawingPage(tab):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QTransform
    from PySide6.QtWidgets import QGraphicsScene, QGraphicsView, QLabel, QVBoxLayout, QWidget
    from ..shell2 import sentence
    entities = tab.view['drawing'];layers = sorted({e['layer'] for e in entities})
    state = {'hidden': set(), 'first': None}
    page = QWidget();box = QVBoxLayout(page);box.setContentsMargins(0, 8, 0, 0)
    words = QLabel();words.setWordWrap(True);box.addWidget(words)
    reading = QLabel('Click two points to measure between them. Drag to pan, wheel to zoom.');reading.setStyleSheet('color:#6c675e');box.addWidget(reading)

    class Canvas(QGraphicsView):
        def wheelEvent(self, event):
            f = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15;self.scale(f, f)

        def mousePressEvent(self, event):
            super().mousePressEvent(event)
            if event.button() != Qt.LeftButton:return
            point = self.mapToScene(event.position().toPoint())
            if state['first'] is None:state['first'] = point;reading.setText('From (%.4g, %.4g): click the second point.' % (point.x(), point.y()))
            else:
                a = state['first'];state['first'] = None;d = math.hypot(point.x() - a.x(), point.y() - a.y())
                reading.setText('Distance %.4g  ·  Δx %.4g  ·  Δy %.4g (drawing units)' % (d, point.x() - a.x(), point.y() - a.y()))

    scene = QGraphicsScene();canvas = Canvas(scene);canvas.setTransform(QTransform().scale(1, -1));canvas.setDragMode(QGraphicsView.ScrollHandDrag)
    canvas.setBackgroundBrush(QColor('#fffdf8'));canvas.setAccessibleName('DXF drawing');box.addWidget(canvas, 1)

    def redraw(fit=False):
        scene.clear();draw(scene, entities, state['hidden'])
        if fit and not scene.itemsBoundingRect().isEmpty():canvas.fitInView(scene.itemsBoundingRect().adjusted(-1, -1, 1, 1), Qt.KeepAspectRatio)
        actions = {'L%d' % i: (('show ' if name in state['hidden'] else '') + name, lambda name=name:toggle(name)) for i, name in enumerate(layers[:40])}
        actions['fit'] = ('fit to window', lambda:redraw(True))
        sentence('Layers: ' + '  ·  '.join('{L%d}' % i for i in range(len(layers[:40]))) + '  ·  {fit}', actions, words)

    def toggle(name):
        state['hidden'] ^= {name};redraw()
    redraw()
    from PySide6.QtCore import QTimer
    QTimer.singleShot(60, lambda:redraw(True))
    return page


def pages(tab, view):
    if not view.get('drawing'):return []
    return [('Drawing', lambda:DrawingPage(tab))]


def thumbnail(path, kind, size):
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QColor, QImage, QPainter
    from PySide6.QtWidgets import QGraphicsScene
    from ..universal_view import Source, decode
    text, _ = decode(Source.file(path).read(0, 16 * 1024 * 1024));entities = parse(text)
    if not entities:return None
    scene = QGraphicsScene();draw(scene, entities)
    image = QImage(size, size, QImage.Format_ARGB32_Premultiplied);image.fill(QColor('#fffdf8'))
    p = QPainter(image);p.setRenderHint(QPainter.Antialiasing);p.translate(0, size);p.scale(1, -1)
    m = size * .08;scene.render(p, QRectF(m, m, size - 2 * m, size - 2 * m), scene.itemsBoundingRect(), Qt.KeepAspectRatio);p.end()
    return image
