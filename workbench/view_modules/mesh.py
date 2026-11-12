"""3D models: STL (text and binary), OBJ and 3MF meshes. Turn, zoom and measure; nothing is edited.

The mesh is read with the standard library and drawn with Qt's painter: shaded triangles in graphite and
pencil, the farthest first. The facts are measured from the triangles themselves: size along each axis, triangle count,
surface area and enclosed volume (meaningful when the mesh is closed). STEP models need a full CAD kernel and are not
drawn here; they stay readable as text.
"""
from __future__ import annotations
import io
import math
import re
import struct
import zipfile
from xml.etree import ElementTree as ET

KINDS = ('stl', 'obj', '3mf')
MAX_TRIANGLES = 1_000_000
DRAW_TRIANGLES = 40_000
M3 = '{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}'


def claim(source, head):
    suffix = source.suffix
    if suffix == '.obj' and re.search(rb'^\s*v\s+[-\d.]', head[:4096], re.M):return 'obj'
    if suffix == '.3mf' and head.startswith(b'PK\x03\x04'):return '3mf'
    return None


def triangles(source, kind):
    """A list of triangles, each ((x, y, z), (x, y, z), (x, y, z)) in model units. Plain Python: nothing to install."""
    raw = source.all()
    if kind == 'stl':
        if raw[:5].lower() == b'solid' and b'facet' in raw[:4096].lower():
            corners = [(float(a), float(b), float(c)) for a, b, c in re.findall(rb'vertex\s+(\S+)\s+(\S+)\s+(\S+)', raw)[:MAX_TRIANGLES * 3]]
            return [tuple(corners[i:i + 3]) for i in range(0, len(corners) - 2, 3)]
        count = min(struct.unpack('<I', raw[80:84])[0], MAX_TRIANGLES, (len(raw) - 84) // 50)
        out = []
        for values in struct.iter_unpack('<12fH', raw[84:84 + 50 * count]):
            out.append((values[3:6], values[6:9], values[9:12]))
        return out
    if kind == 'obj':
        text = raw.decode('utf-8', 'replace');vertices = [];out = []
        for line in text.splitlines():
            if line.startswith('v '):
                parts = line.split()
                if len(parts) >= 4:vertices.append((float(parts[1]), float(parts[2]), float(parts[3])))
            elif line.startswith('f '):
                index = [int(p.split('/')[0]) for p in line.split()[1:] if p.split('/')[0].lstrip('-').isdigit()]
                index = [i - 1 if i > 0 else len(vertices) + i for i in index]
                for k in range(1, len(index) - 1):  # a fan for polygons
                    a, b, c = index[0], index[k], index[k + 1]
                    if 0 <= min(a, b, c) and max(a, b, c) < len(vertices):out.append((vertices[a], vertices[b], vertices[c]))
            if len(out) > MAX_TRIANGLES:break
        return out
    if kind == '3mf':
        archive = zipfile.ZipFile(io.BytesIO(raw));model = next((n for n in archive.namelist() if n.lower().endswith('.model')), None)
        if model is None:return []
        root = ET.fromstring(archive.read(model));out = []
        for mesh in root.iter(M3 + 'mesh'):
            v = [(float(x.get('x')), float(x.get('y')), float(x.get('z'))) for x in mesh.iter(M3 + 'vertex')]
            for tri in mesh.iter(M3 + 'triangle'):
                a, b, c = int(tri.get('v1')), int(tri.get('v2')), int(tri.get('v3'))
                if max(a, b, c) < len(v):out.append((v[a], v[b], v[c]))
                if len(out) >= MAX_TRIANGLES:return out
        return out
    raise ValueError('Not a mesh')


def sub(a, b):return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def cross(a, b):return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def measure(t):
    if not t:return None
    low = [min(p[i] for tri in t for p in tri) for i in range(3)];high = [max(p[i] for tri in t for p in tri) for i in range(3)]
    area = volume = 0.0
    for a, b, c in t:
        n = cross(sub(b, a), sub(c, a));area += math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2) / 2
        k = cross(b, c);volume += a[0] * k[0] + a[1] * k[1] + a[2] * k[2]
    return {'size': [h - l for h, l in zip(high, low)], 'low': low, 'area': area, 'volume': abs(volume) / 6, 'triangles': len(t)}


def describe(source, view):
    kind = view['kind']
    if kind == 'stl':
        from ..universal_view import describe_stl
        describe_stl(source, view)
    t = triangles(source, kind);facts = measure(t)
    view['mesh'] = True
    if facts is None:view['notice'] = 'This model has no triangles to draw.';return
    x, y, z = facts['size']
    view['summary'] += [('Triangles', '{:,}'.format(facts['triangles'])), ('Size (model units)', '%.4g × %.4g × %.4g' % (x, y, z)),
                        ('Surface area', '%.4g' % facts['area']), ('Enclosed volume', '%.4g (if the mesh is closed)' % facts['volume'])]
    if facts['triangles'] >= MAX_TRIANGLES:view['notice'] = 'Read up to %s triangles.' % '{:,}'.format(MAX_TRIANGLES)


DESCRIBERS = {'stl': describe, 'obj': describe, '3mf': describe}


def project(t, yaw, pitch):
    """Rotate the triangles for the view; each with the light-facing shade, the farthest first."""
    cy, sy, cp, sp = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch)
    def turn(p):
        x, y, z = p
        return (cy * x + sy * z, sp * sy * x + cp * y - sp * cy * z, -cp * sy * x + sp * y + cp * cy * z)
    out = []
    for tri in t:
        a, b, c = (turn(p) for p in tri);n = cross(sub(b, a), sub(c, a));length = math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2) or 1
        out.append(((a[2] + b[2] + c[2]) / 3, abs(n[2]) / length, (a, b, c)))
    out.sort(key=lambda row:row[0])
    return [row[2] for row in out], [row[1] for row in out]


def render(t, width, height, yaw=-0.6, pitch=0.5, zoom=1.0):
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPolygonF
    image = QImage(width, height, QImage.Format_ARGB32_Premultiplied);image.fill(QColor('#eee9df'))
    if not t:return image
    step = max(1, len(t) // DRAW_TRIANGLES);t = t[::step]
    centre = [(min(p[i] for tri in t for p in tri) + max(p[i] for tri in t for p in tri)) / 2 for i in range(3)]
    t = [tuple(sub(p, centre) for p in tri) for tri in t]
    r, shade = project(t, yaw, pitch)
    extent = max(max(abs(p[0]), abs(p[1])) for tri in r for p in tri) or 1e-9;scale = zoom * 0.42 * min(width, height) / extent
    p = QPainter(image);p.setRenderHint(QPainter.Antialiasing, len(r) < 20000)
    light, dark = QColor('#f8edc9'), QColor('#6c675e')
    for tri, s in zip(r, shade):
        mix = 0.25 + 0.75 * s
        color = QColor(int(dark.red() + (light.red() - dark.red()) * mix), int(dark.green() + (light.green() - dark.green()) * mix),
                       int(dark.blue() + (light.blue() - dark.blue()) * mix))
        p.setPen(QPen(color, 0.6) if len(r) > 4000 else QPen(QColor('#7d776d'), 0.4));p.setBrush(color)
        p.drawPolygon(QPolygonF([QPointF(width / 2 + x * scale, height / 2 - y * scale) for x, y, _ in tri]))
    p.end();return image


def MeshPage(tab):
    from PySide6.QtGui import QPainter
    from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget
    t = triangles(tab.source, tab.view['kind']);facts = measure(t)

    class View(QWidget):
        def __init__(self):
            super().__init__();self.yaw, self.pitch, self.zoom = -0.6, 0.5, 1.0;self.last = None;self.setMinimumHeight(320)
            self.setAccessibleName('3D model view: drag to turn, wheel to zoom')

        def paintEvent(self, event):
            p = QPainter(self);p.drawImage(0, 0, render(t, self.width(), self.height(), self.yaw, self.pitch, self.zoom));p.end()

        def mousePressEvent(self, event):self.last = event.position()

        def mouseMoveEvent(self, event):
            if self.last is None:return
            d = event.position() - self.last;self.last = event.position()
            self.yaw += d.x() * 0.01;self.pitch = max(-1.5, min(1.5, self.pitch + d.y() * 0.01));self.update()

        def mouseReleaseEvent(self, event):self.last = None

        def wheelEvent(self, event):
            self.zoom = max(0.2, min(20.0, self.zoom * (1.15 if event.angleDelta().y() > 0 else 1 / 1.15)));self.update()

    page = QWidget();box = QVBoxLayout(page);box.setContentsMargins(0, 8, 0, 0)
    if facts:
        x, y, z = facts['size']
        label = QLabel('%.4g × %.4g × %.4g model units  ·  %s triangles  ·  drag to turn, wheel to zoom' % (x, y, z, '{:,}'.format(facts['triangles'])))
        label.setStyleSheet('color:#6c675e');box.addWidget(label)
    box.addWidget(View(), 1);return page


def pages(tab, view):
    if not view.get('mesh'):return []
    return [('Model', lambda:MeshPage(tab))]


def thumbnail(path, kind, size):
    from ..universal_view import Source
    return render(triangles(Source.file(path), kind), size, size)
