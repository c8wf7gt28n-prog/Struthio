"""ARC-1 native, read-only 2D inspection panes for PNG and KiCad sources.

Rendered inside the existing Workbench Qt center tabs. KiCad drawings are
source-derived inspection sketches and MUST NOT be used for design release,
netlist equivalence, manufacturing signoff or electrical connectivity claims.
"""
from __future__ import annotations

from pathlib import Path
import math
import hashlib

from PySide6.QtCore import QPointF, Qt, QRegularExpression, QRectF, Signal
from PySide6.QtGui import QColor, QBrush, QPen, QFont, QPixmap, QPainter, QSyntaxHighlighter, QTextCharFormat, QPainterPath
from PySide6.QtWidgets import (QCheckBox, QGraphicsScene, QGraphicsView, QHBoxLayout, QGridLayout,
                               QLabel, QPushButton, QVBoxLayout, QWidget, QComboBox)

from . import viewer_data


SOURCE_FORMATS = {'.c', '.h', '.s', '.cpp', '.hpp', '.py', '.js', '.mjs', '.json', '.css', '.html'}
IMAGE_FORMATS = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.ppm'}
CAD_FORMATS = {'.kicad_sch', '.kicad_pcb'}


class SourceHighlighter(QSyntaxHighlighter):
    """Simple deterministic source highlighting; no language server or execution."""
    def __init__(self, document, suffix, paper=False):
        super().__init__(document)
        suffix = suffix.lower()
        patterns = []
        def add(regex, color, bold=False):
            if paper:
                color = {'#f69a62':'#8b370e','#72c7db':'#07586c',
                         '#bfb1ef':'#663a99','#b3d18b':'#386220',
                         '#7b8791':'#526270'}[color]
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color))
            if bold:
                fmt.setFontWeight(QFont.Weight.Bold)
            patterns.append((QRegularExpression(regex), fmt))
        add(r'\b(?:if|else|while|for|do|switch|case|break|continue|return|struct|enum|union|typedef|static|const|volatile|extern|inline|void|int|char|float|double|unsigned|signed|short|long|sizeof|class|public|private|include|define|ifdef|endif|elif|import|from|def|lambda|with|try|except|finally|raise|async|await|function|let|var|export|default|null|true|false)\b', '#f69a62', True)
        add(r'\b(?:uint(?:8|16|32|64)_t|int(?:8|16|32|64)_t|size_t|bool|NULL|True|False)\b', '#72c7db')
        add(r'\b(?:0x[0-9a-fA-F]+|\d+(?:\.\d+)?)\b', '#bfb1ef')
        add(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', '#b3d18b')
        if suffix in ('.py',):
            add(r'#[^\n]*', '#7b8791')
        elif suffix in ('.css', '.html'):
            add(r'/\*.*?\*/|<!--.*?-->', '#7b8791')
        else:
            add(r'//[^\n]*|/\*.*?\*/', '#7b8791')
        self.rules = patterns

    def highlightBlock(self, text):
        for expression, fmt in self.rules:
            it = expression.globalMatch(text)
            while it.hasNext():
                match = it.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)


class ZoomCanvas(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        self.setBackgroundBrush(QColor('#101216'))

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.zoom(factor)
        event.accept()

    def zoom(self, factor):
        current = self.transform().m11()
        if .015 <= current * factor <= 150:
            self.scale(factor, factor)

    def fit(self):
        bounds = self.scene().itemsBoundingRect()
        if bounds.isValid() and not bounds.isEmpty():
            self.fitInView(bounds.adjusted(-12, -12, 12, 12), Qt.AspectRatioMode.KeepAspectRatio)

    def mouseDoubleClickEvent(self, event):
        self.fit()
        event.accept()


class ImageViewerTab(QWidget):
    def __init__(self, path):
        super().__init__()
        self.path = Path(path)
        if self.path.stat().st_size > 50 * 1024 * 1024:
            raise viewer_data.ViewerError('Image exceeds the 50 MiB view limit')
        pix = QPixmap(str(self.path))
        if pix.isNull() or pix.width() * pix.height() > 64_000_000:
            raise viewer_data.ViewerError('Image format invalid or dimensions too large')
        self.scene = QGraphicsScene(self)
        self.scene.addPixmap(pix)
        self.view = ZoomCanvas(self.scene)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        row = QHBoxLayout()
        row.addWidget(QLabel(f'PNG / Image  ·  {pix.width()} × {pix.height()}  ·  read-only'))
        row.addStretch()
        for text, cb in (('−', lambda: self.view.zoom(1/1.25)), ('+', lambda: self.view.zoom(1.25)),
                         ('100%', self.actual_size), ('Fit', self.view.fit)):
            button = QPushButton(text)
            button.clicked.connect(cb)
            row.addWidget(button)
        layout.addLayout(row)
        layout.addWidget(self.view, 1)
        layout.addWidget(QLabel('Drag to pan · wheel to zoom · double-click to fit'))
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self.view.fit)

    def actual_size(self):
        self.view.resetTransform()

    def title(self):
        return self.path.name

    def info(self):
        return f'Image preview · {self.path.name} · source file unchanged'


class CadViewerTab(QWidget):
    componentSelected=Signal(str,str)
    SCALE = 5  # Native KiCad coordinates in mm; Qt scene units in 5 px / mm.

    def __init__(self, path, opener=None):
        super().__init__()
        self.path = Path(path)
        self.opener = opener
        self.source_sha256=hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.model = (viewer_data.schematic(self.path) if self.path.suffix.lower() == '.kicad_sch'
                      else viewer_data.pcb(self.path))
        if hashlib.sha256(self.path.read_bytes()).hexdigest()!=self.source_sha256:raise viewer_data.ViewerError('Native source changed while opening')
        self.scene = QGraphicsScene(self)
        self.view = ZoomCanvas(self.scene)
        self.groups = {}
        self.checks = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        header = QHBoxLayout()
        header.addWidget(QLabel(('Schematic' if self.model['kind']=='schematic' else 'PCB') + ' · ' + self.path.name))
        header.addStretch()
        for text, cb in (('−', lambda: self.view.zoom(1/1.2)), ('+', lambda: self.view.zoom(1.2)),
                         ('Fit', self.view.fit)):
            button = QPushButton(text)
            button.clicked.connect(cb)
            header.addWidget(button)
        layout.addLayout(header)
        if self.model['kind'] == 'schematic':
            self.render_schematic()
            labels = [('Symbols', 'symbols'), ('Wiring', 'wiring'), ('Net labels', 'labels')]
            detail = 'Drawn from KiCad S-expressions · approximate geometry, not native KiCad rendering'
        else:
            self.render_pcb()
            labels = [(x, x) for x in self.groups]
            detail = ('Source geometry inspection · %d filled zones omitted · %d unsupported pad shapes shown as bounds' %
                      (self.model['zones_omitted'],self.model['unsupported_pads']))
        self.scene.setSceneRect(self.scene.itemsBoundingRect().adjusted(-200,-200,200,200))
        lookup = QHBoxLayout()
        self.component_find = QComboBox();self.component_find.setEditable(True)
        self.component_find.setInsertPolicy(QComboBox.NoInsert)
        self.ref_positions = ({x['ref']:x['origin'] for x in self.model['symbols'] if x['ref']}
                              if self.model['kind']=='schematic' else {ref:at for at,ref in self.model['refs'] if ref})
        self.component_find.addItems(sorted(self.ref_positions))
        lookup.addWidget(QLabel('Component'));lookup.addWidget(self.component_find,1)
        locate=QPushButton('Locate');locate.clicked.connect(self.locate_component);lookup.addWidget(locate)
        if self.model['kind']=='schematic' and opener:
            self.sheet_picker=QComboBox()
            for sheet in sorted(self.path.parent.glob('*.kicad_sch')):
                if sheet.is_file() and not sheet.is_symlink():self.sheet_picker.addItem(sheet.stem,str(sheet))
            self.sheet_picker.setCurrentIndex(self.sheet_picker.findData(str(self.path)))
            self.sheet_picker.activated.connect(lambda index:opener(Path(self.sheet_picker.itemData(index))))
            lookup.addWidget(QLabel('Sheet'));lookup.addWidget(self.sheet_picker,1)
        layout.addLayout(lookup)
        self.lookup_note=QLabel('Locate a reference to center the drawing; no electrical connectivity inferred.')
        self.lookup_note.setWordWrap(True);layout.addWidget(self.lookup_note)
        toggles = QGridLayout()
        toggles.setHorizontalSpacing(10)
        toggles.setVerticalSpacing(3)
        for index, (name, key) in enumerate(labels):
            check = QCheckBox(name)
            check.setChecked(key not in ('B.Cu','In1.Cu','In2.Cu','In3.Cu','In4.Cu','F.SilkS'))
            check.toggled.connect(lambda on, group=key: self.set_group(group, on))
            self.checks[key] = check
            toggles.addWidget(check, index // 5, index % 5)
        layout.addLayout(toggles)
        layout.addWidget(self.view, 1)
        notice = QLabel('DESIGN / FABRICATION HOLD · READ-ONLY · ' + detail)
        notice.setObjectName('simBanner')
        notice.setWordWrap(True)
        layout.addWidget(notice)
        layout.addWidget(QLabel('Drag to pan · wheel to zoom · double-click to fit · use KiCad for ERC/DRC and authoritative geometry'))
        for name, check in self.checks.items():
            self.set_group(name, check.isChecked())
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self.view.fit)

    def p(self, value):
        return QPointF(value[0] * self.SCALE, value[1] * self.SCALE)

    def pen(self, color, width=1):
        return QPen(QColor(color), width)

    def put(self, key, item, tooltip=None):
        self.groups.setdefault(key, []).append(item)
        if tooltip:
            item.setToolTip(tooltip)
        return item

    def line(self, key, start, end, color, width=1, tooltip=None):
        a, b = self.p(start), self.p(end)
        return self.put(key, self.scene.addLine(a.x(),a.y(),b.x(),b.y(),self.pen(color,width)), tooltip)

    def dot(self, key, point, radius, color, tip=None):
        c = self.p(point)
        r = max(1., radius * self.SCALE)
        item = self.scene.addEllipse(c.x()-r,c.y()-r,2*r,2*r,
                                     self.pen(color,0.8),QBrush(QColor(color)))
        return self.put(key,item,tip)

    def text(self,key,point,string,color,scale=.56,tip=None):
        if not string:
            return
        t = self.scene.addSimpleText(str(string)[:100])
        t.setBrush(QColor(color))
        t.setPos(self.p(point))
        t.setScale(scale)
        return self.put(key,t,tip)

    def rect(self,key,a,b,color,fill=None,tooltip=None):
        p1,p2=self.p(a),self.p(b)
        item=self.scene.addRect(QRectF(p1,p2).normalized(),self.pen(color,.9),
                                QBrush(QColor(fill)) if fill else QBrush(Qt.BrushStyle.NoBrush))
        return self.put(key,item,tooltip)

    def render_schematic(self):
        model=self.model
        for points in model['wires']:
            for a,b in zip(points,points[1:]):
                self.line('wiring',a,b,'#63c798',1.1)
        for typ,p in model['junctions']:
            if typ=='junction':
                self.dot('wiring',p,.45,'#63c798')
            else:
                self.line('wiring',(p[0]-.7,p[1]-.7),(p[0]+.7,p[1]+.7),'#7f91a2')
                self.line('wiring',(p[0]-.7,p[1]+.7),(p[0]+.7,p[1]-.7),'#7f91a2')
        for label,p,typ in model['labels']:
            self.text('labels',p,label,'#eab45d',.47,typ)
        for symbol in model['symbols']:
            tip=f"{symbol['ref']} · {symbol['value']} · {symbol['lib_id']}"
            for a,b in symbol['rectangles']:
                self.rect('symbols',a,b,'#7bafcb','#1d2b36',tip)
            for center,r in symbol['circles']:
                c=self.p(center);radius=r*self.SCALE
                self.put('symbols',self.scene.addEllipse(c.x()-radius,c.y()-radius,radius*2,radius*2,
                                        self.pen('#7bafcb')),tip)
            for vertices in symbol['lines']:
                for a,b in zip(vertices,vertices[1:]):
                    self.line('symbols',a,b,'#7bafcb',.9,tip)
            for a,b in symbol['pins']:
                self.line('symbols',a,b,'#b69fc9',.8,tip)
            # Use the instance as text anchor; no assertion about KiCad font-placement fidelity.
            x,y=symbol['origin']
            if symbol['ref']:
                self.text('symbols',(x+2,y-4),symbol['ref'],'#f4a168',.6,tip)
            if symbol['value']:
                self.text('symbols',(x+2,y-1),symbol['value'],'#c3cbd2',.39,tip)
        if model['missing_symbols']:
            self.text('labels',(8,8),f"{model['missing_symbols']} unavailable symbol definitions",'#ff7a3c',.9)

    def render_pcb(self):
        model=self.model
        palette={'F.Cu':'#ed9263','B.Cu':'#78aedb','In1.Cu':'#ac8fe4','In2.Cu':'#93cb9b',
                 'In3.Cu':'#e2b0cb','In4.Cu':'#dbc779','F.SilkS':'#d4dce1','Edge.Cuts':'#ffffff'}
        for a,b,width,layer in model['tracks']:
            self.line(layer,a,b,palette.get(layer,'#bfc5c8'),max(.7,width*self.SCALE),f'{layer} · track {width} mm')
        for center,diameter in model['vias']:
            self.dot('Vias',center,diameter/2,'#d9c78e','Via, native source')
        for index,(center,w,h,angle,layers,label) in enumerate(model['pads']):
            layer = ('F.Cu' if 'F.Cu' in layers or '*.Cu' in layers else
                     'B.Cu' if 'B.Cu' in layers else next((x for x in layers if x.endswith('.Cu')),'Pads'))
            shape,ratio=model['pad_shapes'][index]
            path=QPainterPath();rect=QRectF(-w*self.SCALE/2,-h*self.SCALE/2,w*self.SCALE,h*self.SCALE)
            if shape=='circle':path.addEllipse(rect)
            elif shape in ('oval','roundrect'):
                radius=min(w,h)*self.SCALE*(.5 if shape=='oval' else ratio)
                path.addRoundedRect(rect,radius,radius)
            else:path.addRect(rect)
            item=self.scene.addPath(path,self.pen(palette.get(layer,'#a7a7a7'),.7))
            item.setPos(self.p(center));item.setRotation(-angle)
            self.put(layer,item,f'Pad {label} · {shape} · {angle:g}°; layers {", ".join(layers)}')
        for tag,a,b,mid,layer in model['graphics']:
            if tag=='gr_line':
                self.line(layer,a,b,palette.get(layer,'#ccd3d6'),1.8)
            elif tag=='gr_rect':
                self.rect(layer,a,b,palette.get(layer,'#ccd3d6'))
            elif tag=='gr_circle':
                c=self.p(a);r=math.dist(a,b)*self.SCALE
                self.put(layer,self.scene.addEllipse(c.x()-r,c.y()-r,2*r,2*r,self.pen('#eeeeee',1.5)))
            elif tag=='gr_arc':
                points=viewer_data.arc_points(a,mid,b)
                path=QPainterPath(self.p(points[0]))
                for point in points[1:]:path.lineTo(self.p(point))
                self.put(layer,self.scene.addPath(path,self.pen(palette.get(layer,'#d1d5d8'),.9)))
        for at,ref in model['refs']:
            if ref:
                self.text('References',at,ref,'#e7e9eb',.40)
        for layer in ('F.Cu','B.Cu','In1.Cu','In2.Cu','In3.Cu','In4.Cu',
                      'F.SilkS','Edge.Cuts','Vias','References'):
            self.groups.setdefault(layer,[])

    def locate_component(self):
        if not self.path.is_file() or hashlib.sha256(self.path.read_bytes()).hexdigest()!=self.source_sha256:
            self.lookup_note.setText('Native drawing changed; reopen it before locating or cross-probing.');return False
        ref=self.component_find.currentText().strip()
        point=self.ref_positions.get(ref)
        if point is None:
            self.lookup_note.setText('Reference not found on this drawing: '+ref);return False
        if 'References' in self.checks:self.checks['References'].setChecked(True)
        if 'symbols' in self.checks:self.checks['symbols'].setChecked(True)
        p=self.p(point)
        bounds=QRectF(p.x()-70,p.y()-70,140,140)
        if self.model['kind']=='schematic':
            symbol=next((s for s in self.model['symbols'] if s['ref']==ref),None)
            if symbol:
                points=[pt for key in ('rectangles','lines','pins') for pair in symbol.get(key,[]) for pt in pair]
                if points:
                    xs=[pt[0]*self.SCALE for pt in points];ys=[pt[1]*self.SCALE for pt in points]
                    bounds=QRectF(min(xs),min(ys),max(xs)-min(xs),max(ys)-min(ys)).adjusted(-45,-25,45,25)
        self.view.fitInView(bounds,Qt.KeepAspectRatio)
        self.lookup_note.setText(ref+' · centered at source position · inspect layer visibility as needed')
        symbol=next((s for s in self.model.get('symbols',[]) if s['ref']==ref),None)
        if symbol and symbol.get('native_uuid'):self.componentSelected.emit(ref,symbol['native_uuid'])
        return True

    def set_group(self, group, shown):
        for item in self.groups.get(group, ()):
            item.setVisible(shown)

    def title(self):
        return self.path.name

    def info(self):
        return ('Read-only native KiCad source inspection · not ERC, DRC or KiCad parity · '
                + self.path.name)
