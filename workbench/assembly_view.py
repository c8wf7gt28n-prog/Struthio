"""CPU-rendered source geometry; display transforms never modify CAD."""
import json,math,sys
from pathlib import Path
from PySide6.QtCore import Qt,QPointF,QProcess,QTimer,Signal
from PySide6.QtGui import QPainter,QColor,QPolygonF,QPen
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QSlider,QCheckBox,QFileDialog
from .assembly_data import STEP, cache, sha, validate_triangles


class MeshCanvas(QWidget):
    picked=Signal(bool)
    def __init__(self):
        super().__init__();self.mesh=None;self.yaw=-0.5;self.pitch=0.7;self.zoom=1.;self.pan=[0.,0.]
        self.explode=0;self.labels=True;self.selected=False;self.last=None;self.setMinimumSize(240,180)
    def load(self,mesh):
        validate_triangles(mesh['triangles'])
        self.mesh=mesh
        pts=[p for t in mesh['triangles'] for p in t]
        low=[min(p[i] for p in pts) for i in range(3)];high=[max(p[i] for p in pts) for i in range(3)]
        self.center=[(low[i]+high[i])/2 for i in range(3)];self.span=max(high[i]-low[i] for i in range(3)) or 1
        self.bounds=[high[i]-low[i] for i in range(3)];self.update()
    def project(self,p):
        x,y,z=[p[i]-self.center[i] for i in range(3)]
        x,y=x*math.cos(self.yaw)-y*math.sin(self.yaw),x*math.sin(self.yaw)+y*math.cos(self.yaw)
        y,z=y*math.cos(self.pitch)-z*math.sin(self.pitch),y*math.sin(self.pitch)+z*math.cos(self.pitch)
        scale=min(self.width(),self.height())*.75/self.span*self.zoom
        return QPointF(self.width()/2+x*scale+self.pan[0],self.height()/2-y*scale+self.pan[1]),z
    def paintEvent(self,event):
        p=QPainter(self);p.fillRect(self.rect(),QColor('#14191e'));p.setRenderHint(QPainter.Antialiasing)
        if not self.mesh:
            p.setPen(QColor('#d8d5cc'));p.drawText(self.rect(),Qt.AlignCenter,'Geometry unavailable · source access remains available');return
        faces=[]
        for t in self.mesh['triangles']:
            projected=[self.project(v) for v in t];faces.append((sum(v[1] for v in projected),QPolygonF([v[0] for v in projected])))
        p.setPen(QPen(QColor('#557b70'),.4));p.setBrush(QColor('#c37848' if self.selected else '#31564c'))
        for _,poly in sorted(faces,key=lambda f:f[0]):p.drawPolygon(poly)
        if self.labels:
            p.setPen(QColor('#e9d5bb'));p.drawText(14,24,Path(self.mesh['source']).name)
            p.drawText(14,44,'Source-derived geometry · '+self.mesh['units'])
    def mousePressEvent(self,e):self.last=e.position();self.origin=e.position()
    def mouseMoveEvent(self,e):
        if self.last is None:return
        delta=e.position()-self.last;self.last=e.position()
        if e.buttons() & (Qt.RightButton|Qt.MiddleButton):self.pan[0]+=delta.x();self.pan[1]+=delta.y()
        else:self.yaw+=delta.x()*.01;self.pitch+=delta.y()*.01
        self.update()
    def mouseReleaseEvent(self,e):
        if self.last is not None and (e.position()-self.origin).manhattanLength()<4:
            # Pick by projected triangle containment, never by nearest guessed part.
            self.selected=any(QPolygonF([self.project(v)[0] for v in t]).containsPoint(e.position(),Qt.OddEvenFill) for t in self.mesh['triangles']) if self.mesh else False
            self.picked.emit(self.selected)
            self.update()
        self.last=None
    def wheelEvent(self,e):self.zoom=max(.1,min(15,self.zoom*1.12**(e.angleDelta().y()/120)));self.update()
    def reset(self):self.yaw=-.5;self.pitch=.7;self.zoom=1.;self.pan=[0.,0.];self.update()


class AssemblyTab(QWidget):
    def __init__(self,host,case=False,source=None):
        super().__init__();self.host=host;self.case=case;self.path=host.root/source if source else None
        self.source=source or STEP;self.process=None
        v=QVBoxLayout(self);v.addWidget(QLabel('CASE · mechanical inspection' if case else 'ARC-1 · CONSOLE HOME'))
        self.notice=QLabel('Case geometry absent. PCB STEP contains one solid; component/package models are missing. Exploded assembly remains incomplete. Fabrication HOLD.')
        self.notice.setWordWrap(True);v.addWidget(self.notice)
        controls=QHBoxLayout()
        for label,fn in [('Reset view',lambda:self.canvas.reset()),('Open PCB',host.show_native_board),
                         ('Verification',host.show_hardware_proof),('Open STEP / STL',self.choose),('Cancel import',self.cancel)]:
            b=QPushButton(label);b.clicked.connect(fn);controls.addWidget(b)
        v.addLayout(controls)
        self.canvas=MeshCanvas();self.canvas.picked.connect(self.select_source);v.addWidget(self.canvas,1)
        self.status=QLabel();self.status.setWordWrap(True);v.addWidget(self.status)
        row=QHBoxLayout();labels=QCheckBox('Labels');labels.setChecked(True);labels.toggled.connect(self.labels);row.addWidget(labels)
        self.separation=QSlider(Qt.Horizontal);self.separation.setRange(0,100);self.separation.setEnabled(False)
        self.separation.setToolTip('One solid is available. Separation requires independently identified assembly parts.');row.addWidget(self.separation)
        v.addLayout(row)
        self.deadline=QTimer(self);self.deadline.setSingleShot(True);self.deadline.timeout.connect(self.cancel)
        if case and not source:self.status.setText('Enclosure CAD: missing. Open a real STEP/STL source to inspect it. STL units must be supplied by its author.')
        else:QTimer.singleShot(0,self.load)
    def title(self):return 'Case' if self.case else 'Console Home'
    def info(self):return 'Source geometry · current PCB correspondence unverified · HOLD'
    def labels(self,value):self.canvas.labels=value;self.canvas.update()
    def select_source(self,selected):
        if selected and self.source==STEP:
            item=next((it for it in self.host._nav_items() if it.data(0,Qt.UserRole+2)=='nav_device' and it.data(0,Qt.UserRole+4)=='pcb'),None)
            if item:
                self.host.nav.setCurrentItem(item);self.host._accepted_nav_item=item
                self.host.clip_dock.set_context('Main PCB · Electrical','pcb')
    def choose(self):
        name,_=QFileDialog.getOpenFileName(self,'Inspect project geometry',str(self.host.root),'Geometry (*.step *.stp *.stl)')
        if name:
            try:self.source=Path(name).resolve().relative_to(self.host.root).as_posix();self.load()
            except ValueError:self.status.setText('Choose a source inside this project.')
    def load(self):
        self.cancel()
        try:
            target=cache(self.host.root,self.source)
            packaged=self.host.root/'assets/geometry/pcb.json'
            for candidate in (target,packaged):
                if candidate.is_file() and candidate.stat().st_size<64*1024*1024:
                    mesh=json.loads(candidate.read_text())
                    if mesh['source']==self.source and mesh['sha256']==sha(self.host.root/self.source) and mesh['converter_sha256']==sha(Path(__file__).with_name('assembly_data.py')):
                        self.show_mesh(mesh);return
            self.process=QProcess(self);self.process.setWorkingDirectory(str(self.host.root))
            from .operation_priority import watch_qprocess
            watch_qprocess(self.process,self.host.root)
            self.process.finished.connect(self.finished)
            self.process.start(sys.executable,['-m','workbench.assembly_data','--root',str(self.host.root),'--source',self.source])
            self.deadline.start(60000);self.status.setText('Converting geometry in background · 60 second limit · Cancel available')
        except (OSError,ValueError,KeyError) as e:self.status.setText(str(e))
    def finished(self,code,*args):
        self.deadline.stop()
        if code!=0:
            self.status.setText('Import failed: '+bytes(self.process.readAllStandardError()).decode(errors='replace')[-1200:]);return
        try:self.show_mesh(json.loads(cache(self.host.root,self.source).read_text()))
        except (OSError,ValueError,KeyError) as e:self.status.setText('Invalid derived mesh: '+str(e))
    def show_mesh(self,mesh):
        self.canvas.load(mesh)
        self.status.setText('%s · %d triangles · bounds %s · SHA256 %s\nConverter %s · PCB export freshness against current board remains unverified.' %
                            (mesh['units'],len(mesh['triangles']),str(self.canvas.bounds),mesh['sha256'][:16],mesh['converter']))
    def cancel(self):
        self.deadline.stop()
        if self.process and self.process.state()!=QProcess.NotRunning:
            self.process.finished.disconnect(self.finished)
            self.process.kill();self.process.waitForFinished(1000);self.status.setText('Import cancelled; source unchanged')
    def shutdown_engineering(self):self.cancel()
