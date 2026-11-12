"""ARC Fairy 1 artwork and a local motion rehearsal. Presentation only.

The companion uses existing job states. The separate rehearsal has demonstration
events; it never imports the Kernel, reads a journal, moves a pointer or clicks.
"""
from pathlib import Path
import hashlib
import json
import math
import sys
import time
from PySide6.QtCore import QEvent, QPointF, QRect, QRectF, QTimer, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QRadialGradient
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QHBoxLayout,
    QLabel, QMainWindow, QPushButton, QVBoxLayout, QWidget)
from sdk.cli.arc1cli.host_cpu import HostCpuSampler
from sdk.cli.arc1cli.sprite_player import SpritePlayer
from . import locations

_CACHE = {}
_CPU = HostCpuSampler()
POSES = ('idle', 'glide', 'bank', 'guide_left', 'guide_right', 'celebrate',
         'inspect', 'attention', 'perch')
JOB_POSES = {'idle': 'idle', 'working': 'inspect', 'approval': 'attention',
             'paused': 'perch', 'done': 'celebrate', 'failed': 'attention'}


def cpu_caption(info):
    if info['percent'] is None:return 'Host CPU: Not instrumented — '+info['reason']
    return 'Host CPU: %.1f%% activity · %.2fs sample age · Linux /proc/stat' % (info['percent'],info['age_seconds'])


def refresh_cpu_hint(anchor):
    now=time.monotonic()
    if now-getattr(anchor,'_arcfairy_cpu_hint_at',float('-inf'))<1:return
    anchor._arcfairy_cpu_hint_at=now
    base=anchor.toolTip().split('\nHost CPU:')[0]
    anchor.setToolTip(base+'\n'+cpu_caption(_CPU.snapshot()))


def paint_cpu_sparkles(painter,area,phase,reduced=False,pixel=False):
    info=_CPU.snapshot()
    if info['percent'] is None:return
    level=info['percent']/100.;area=QRectF(area);painter.save();painter.setPen(Qt.NoPen)
    if reduced:
        center=area.center();radius=min(area.width(),area.height())*.4
        glow=QRadialGradient(center,radius)
        glow.setColorAt(0,QColor(255,164,65,int(18+70*level)));glow.setColorAt(1,QColor(255,164,65,0))
        painter.setBrush(glow);painter.drawEllipse(center,radius,radius)
    else:
        count=2+int(level*10)
        for i in range(count):
            f=(i+1)/(count+1)
            point=QPointF(area.left()+area.width()*(.07+.35*f),area.bottom()-area.height()*(.12+.25*f)+math.sin(phase*1.4+i)*1.5)
            painter.setBrush(QColor(255,174,75,int((35+125*level)*f)))
            radius=.6+level*.6+f*.55
            if pixel:painter.drawRect(QRectF(round(point.x()/2)*2,round(point.y()/2)*2,2,2))
            else:painter.drawEllipse(point,radius,radius)
    painter.restore()


class SpriteSet:
    def __init__(self, root):
        base = locations.program(root) / 'branding/arcfairy'
        data = json.loads((base / 'assets.json').read_text(encoding='utf-8'))
        if data['schema'] != 'arc.arcfairy.assets/1':
            raise ValueError('Unsupported ARC fairy assets')
        row = data['files']['staC-arcfairy-atlas.png']
        path = base / 'staC-arcfairy-atlas.png'
        raw = path.read_bytes()
        if len(raw) != row['bytes'] or hashlib.sha256(raw).hexdigest() != row['sha256']:
            raise ValueError('ARC fairy atlas failed its integrity check')
        self.pixmap = QPixmap(str(path))
        if self.pixmap.isNull() or [self.pixmap.width(), self.pixmap.height()] != data['atlas_size']:
            raise ValueError('ARC fairy atlas size does not match')
        self.rects = {name: QRectF(*data['poses'][name]['rect']) for name in POSES}
        bounds = QRectF(self.pixmap.rect())
        if any(not bounds.contains(rect) or rect.width() < 1 or rect.height() < 1 for rect in self.rects.values()):
            raise ValueError('ARC fairy pose outside the atlas')
        game=data['game_sprite'];path=base/game['file'];raw=path.read_bytes()
        if len(raw)!=data['files'][game['file']]['bytes'] or hashlib.sha256(raw).hexdigest()!=data['files'][game['file']]['sha256']:
            raise ValueError('ARC fairy game sheet failed its integrity check')
        sheet=QPixmap(str(path));bounds=QRect(sheet.rect())
        if sheet.isNull() or [sheet.width(),sheet.height()]!=game['sheet_size'] or game['logical_size']!=[128,128]:
            raise ValueError('Invalid ARC fairy game sheet')
        self.frames=[];self.logical=128
        if len(game['frames'])!=128:raise ValueError('Expected 128 game frames')
        for row in game['frames']:
            frame=QRect(*row)
            if not bounds.contains(frame):raise ValueError('Game frame leaves the atlas')
            self.frames.append(sheet.copy(frame).scaled(self.logical,self.logical,Qt.IgnoreAspectRatio,Qt.FastTransformation))
        if any(i>=len(self.frames) for clip in game['clips'].values() for i in clip['frames']):
            raise ValueError('Missing game frame')
        self.player=SpritePlayer(game['clips'])

    def paint(self, painter, area, pose='idle', phase=0, reduced=False,game=True,now=None):
        if game:
            frame=self.player.frame(pose,now=now,reduced=reduced)
            scale=max(1,int(min(area.width(),area.height())//self.logical));side=self.logical*scale
            x=round((area.center().x()-side/2)/scale)*scale;y=round((area.center().y()-side/2)/scale)*scale
            painter.save();painter.setRenderHint(QPainter.SmoothPixmapTransform,False)
            if frame['mirror']:
                painter.translate(x+side,y);painter.scale(-1,1);x=y=0
            painter.drawPixmap(QRectF(x,y,side,side),self.frames[frame['frame']],QRectF(0,0,self.logical,self.logical))
            painter.restore();return
        source = self.rects.get(pose, self.rects['idle'])
        side = min(area.width(), area.height())
        bob = 0 if reduced else 1.8 * math.sin(phase * 1.3)
        target = QRectF(area.center().x()-side/2, area.center().y()-side/2+bob, side, side)
        painter.save()
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.drawPixmap(target, self.pixmap, source)
        painter.restore()


def sprites(root):
    key = str(Path(root).resolve())
    if key not in _CACHE:
        try:
            _CACHE[key] = SpriteSet(root)
        except (OSError, ValueError, KeyError, TypeError):
            _CACHE[key] = None
    return _CACHE[key]


def paint_companion(painter, root, area, state, phase, reduced=False, collapsed=False, offset=0., lean=0.,game=True):
    art = sprites(root)
    if art is None:
        return False
    paint_cpu_sparkles(painter,area,phase,reduced,game)
    if collapsed:
        # A code-drawn amber wisp remains readable at the existing collapsed size.
        painter.save();painter.setPen(Qt.NoPen)
        c = QPointF(area.center());radius = min(area.width(), area.height()) * .43
        glow = QRadialGradient(c, radius)
        glow.setColorAt(0, QColor(255, 235, 186, 235))
        glow.setColorAt(.35, QColor(255, 156, 48, 210))
        glow.setColorAt(1, QColor(255, 123, 15, 0))
        painter.setBrush(glow);painter.drawEllipse(c, radius, radius)
        painter.setPen(QPen(QColor('#ffe2a7'), 1));painter.setBrush(QColor(255, 185, 79, 100))
        for sign in (-1, 1):
            path = QPainterPath(c)
            path.cubicTo(c+QPointF(sign*radius, -radius), c+QPointF(sign*radius, radius*.4), c)
            painter.drawPath(path)
        painter.setBrush(QColor('#fff4dc'));painter.setPen(Qt.NoPen);painter.drawEllipse(c, 3, 3)
        painter.restore()
    else:
        painter.save()
        pivot=QPointF(area.center().x(),area.y()+area.height()*.78)
        painter.translate(pivot.x(),pivot.y()+(round(offset/2)*2 if game else offset))
        if not game:painter.rotate(lean)
        painter.translate(-pivot.x(),-pivot.y())
        art.paint(painter, QRectF(area), JOB_POSES.get(state, 'idle'), phase, reduced,game)
        painter.restore()
    return True


def add_sprite_menu(anchor,menu):
    action=menu.addAction('16-bit game sprite rendering')
    action.setCheckable(True);action.setChecked(getattr(anchor,'_arcfairy_game',True))
    action.setToolTip('Use 128 timed sprite frames across eight actions. Turn off for ARC glass artwork. This choice lasts for this window.')
    def changed(value):anchor._arcfairy_game=bool(value);anchor.update()
    action.toggled.connect(changed)


class QuietCanvas(QWidget):
    """Only this explicitly empty canvas is a flight zone in the rehearsal."""
    def __init__(self, art):
        super().__init__();self.art = art;self.pose = 'idle';self.phase = 0.;self.reduced = False
        self.roaming = False;self.guiding = False;self.started = 0.;self.wake = time.monotonic();self.game=True
        self.trail = [];self.setMinimumSize(320, 270)
        self.setAttribute(Qt.WA_TransparentForMouseEvents);self.setFocusPolicy(Qt.NoFocus)
        self.setAccessibleName('ARC fairy motion demonstration in reserved empty space')
        self.clock = QTimer(self);self.clock.setInterval(16);self.clock.timeout.connect(self.tick);self.clock.start();self.previous_tick=time.monotonic()

    def pause_for_input(self):
        self.wake = time.monotonic()+1.2

    def tick(self):
        now=time.monotonic();elapsed=min(.1,max(0.,now-self.previous_tick));self.previous_tick=now
        if not self.reduced and now >= self.wake:
            self.phase += elapsed
        self.update()

    def position(self):
        w, h = self.width(), self.height();size = min(180., w*.36, h*.57)
        center = QPointF(w*.5, h*.52)
        if not self.reduced and (self.roaming or self.guiding):
            t = self.phase
            center = QPointF(w*.5 + math.sin(t*.7)*(w-size-28)*.36,
                             h*.5 + math.sin(t*1.1)*(h-size-30)*.29)
        if self.guiding:
            goal = QPointF(w-size*.55-18, h-size*.55-16)
            progress = 1 if self.reduced else min(1, max(0, (self.phase-self.started)/2))
            smooth = progress*progress*(3-2*progress)
            center = center*(1-smooth)+goal*smooth
        elif self.pose == 'perch' and not self.roaming:
            center = QPointF(w-size*.65-24, h-size*.6-32)
        return QRectF(center.x()-size/2, center.y()-size/2, size, size)

    def paintEvent(self, event):
        p = QPainter(self);p.setRenderHint(QPainter.Antialiasing)
        fill = QLinearGradient(0, 0, 0, self.height())
        fill.setColorAt(0, QColor('#151d26'));fill.setColorAt(1, QColor('#0b1118'))
        p.fillRect(self.rect(), fill)
        p.setPen(QPen(QColor('#27323e'), 1))
        for x in range(24, self.width(), 36):
            for y in range(32, self.height(), 36):p.drawPoint(x, y)
        p.setPen(QColor('#96a3af'));p.drawText(18, 25, 'RESERVED QUIET SPACE  /  DEMONSTRATION')
        target = self.position();point = target.center()
        if not self.reduced and (self.roaming or self.guiding):
            if not self.trail or (self.trail[-1]-point).manhattanLength() > 2:
                self.trail.append(point)
            info=_CPU.snapshot();level=None if info['percent'] is None else info['percent']/100.
            self.trail = self.trail[-(3+int(19*level)):] if level is not None else []
            for i, pos in enumerate(self.trail):
                p.setPen(Qt.NoPen);p.setBrush(QColor(255, 157, 53, int((45+150*level)*(i+1)/len(self.trail))))
                p.drawEllipse(pos, 1.2+i*.07, 1.2+i*.07)
        else:self.trail.clear()
        if self.pose == 'perch' and not self.roaming and not self.guiding:
            base = QRectF(point.x()-28, target.bottom()-8, 56, 13)
            p.setPen(QPen(QColor('#e8b276'), 1));p.setBrush(QColor(255, 161, 60, 45));p.drawRoundedRect(base, 6, 6)
            p.setPen(QColor('#9daab8'));p.drawText(int(base.x()-5), int(base.bottom()+19), 'HOME PERCH')
        pose = 'guide_right' if self.guiding else (('glide' if math.cos(self.phase*.7)<0 else 'bank') if self.roaming else self.pose)
        paint_cpu_sparkles(p,target,self.phase,self.reduced,self.game)
        self.art.paint(p, target, pose, self.phase, self.reduced,self.game)
        if self.guiding:
            p.setPen(QColor('#ffb35b'));p.drawText(18, self.height()-18, 'Why here: example build completed. View results below.')
        p.end()


class Rehearsal(QMainWindow):
    def __init__(self, root):
        super().__init__();self.setWindowTitle('staC the ARC fairy — local motion rehearsal')
        self.resize(1024, 720);self.manual_clicks = 0
        art = SpriteSet(root);body = QWidget();self.setCentralWidget(body);box = QVBoxLayout(body)
        title = QLabel('staC  /  THE ARC FAIRY');title.setStyleSheet('font-size:24px;font-weight:700;color:#ffb15c;');box.addWidget(title)
        note = QLabel('Presentation rehearsal · host CPU readout · no Graphite jobs, journal access or model inference');note.setWordWrap(True);box.addWidget(note)
        self.cpu_label=QLabel(cpu_caption(_CPU.snapshot()));self.cpu_label.setWordWrap(True);box.addWidget(self.cpu_label)
        self.cpu_clock=QTimer(self);self.cpu_clock.setInterval(1000);self.cpu_clock.timeout.connect(lambda:self.cpu_label.setText(cpu_caption(_CPU.snapshot())));self.cpu_clock.start()
        self.canvas = QuietCanvas(art);box.addWidget(self.canvas, 1)
        row = QHBoxLayout();row.addWidget(QLabel('Pose'))
        self.choice = QComboBox();self.choice.addItems(POSES);self.choice.currentTextChanged.connect(self.choose);row.addWidget(self.choice, 1)
        self.mode=QComboBox();self.mode.addItems(['Game sprite','ARC glass']);self.mode.currentIndexChanged.connect(self.set_mode);row.addWidget(self.mode)
        self.roam = QCheckBox('Roam in quiet space');self.roam.toggled.connect(self.set_roaming);row.addWidget(self.roam)
        self.motion = QCheckBox('Reduce motion');self.motion.toggled.connect(self.set_reduced);row.addWidget(self.motion);box.addLayout(row)
        row = QHBoxLayout();guide = QPushButton('Rehearse next click guidance');guide.clicked.connect(self.guide);row.addWidget(guide)
        row.addStretch(1)
        rest = QPushButton('Rest');rest.clicked.connect(self.rest);row.addWidget(rest)
        self.result = QPushButton('View results');self.result.setMinimumWidth(170);self.result.clicked.connect(self.clicked_results);row.addWidget(self.result);box.addLayout(row)
        rituals = QHBoxLayout()
        greet = QPushButton('Greet staC');greet.clicked.connect(self.greet);rituals.addWidget(greet)
        spark = QPushButton('Offer a spark');spark.clicked.connect(self.offer_spark);rituals.addWidget(spark)
        ritual_note = QLabel('Pet rituals are a local visual experiment, with no saved needs or growth score.');ritual_note.setWordWrap(True);rituals.addWidget(ritual_note, 1);box.addLayout(rituals)
        self.receipt = QLabel('Your cursor stays yours. Flight canvas is click-through; controls stay usable.');self.receipt.setWordWrap(True);box.addWidget(self.receipt)
        self.setStyleSheet('QWidget { background:#111821;color:#dae1e7;font-family:Sans-Serif;font-size:14px; } QPushButton,QComboBox { background:#263341;border:1px solid #536373;border-radius:5px;padding:9px; } QPushButton:hover { border-color:#ffab4b; }')
        QApplication.instance().installEventFilter(self)

    def eventFilter(self, obj, event):
        if isinstance(obj, QWidget) and obj.window() is self and event.type() in (QEvent.MouseMove, QEvent.MouseButtonPress, QEvent.KeyPress, QEvent.Wheel):
            self.canvas.pause_for_input()
        return super().eventFilter(obj, event)

    def closeEvent(self, event):
        QApplication.instance().removeEventFilter(self)
        super().closeEvent(event)

    def choose(self, pose):
        self.canvas.pose = pose;self.canvas.guiding = False
        self.canvas.art.player.select(pose,restart=True);self.canvas.update()
    def set_mode(self,index):self.canvas.game=index==0;self.canvas.update()
    def set_roaming(self, checked):
        self.canvas.roaming = checked;self.canvas.guiding = False;self.canvas.update()
    def set_reduced(self, checked):
        self.canvas.reduced = checked;self.canvas.trail.clear();self.canvas.update()
    def guide(self):
        self.canvas.guiding = True;self.canvas.started = self.canvas.phase
        self.receipt.setText('Example cue only: a build finished, so staC points toward View results. Your click opens it.')
    def clicked_results(self):
        self.manual_clicks += 1;self.canvas.guiding = False;self.choice.setCurrentText('celebrate')
        self.choose('celebrate')
        self.receipt.setText('Manual result clicks: '+str(self.manual_clicks)+'. No action was triggered by the fairy.')
    def rest(self):
        self.roam.setChecked(False);self.canvas.guiding = False;self.choice.setCurrentText('perch');self.canvas.update()
        self.receipt.setText('Home perch. She rests here until you invite her back. This is a presentation state.')
    def greet(self):
        self.roam.setChecked(False);self.choice.setCurrentText('attention')
        self.receipt.setText('Hello again. A greeting ritual for the prototype; no relationship score is saved.')
    def offer_spark(self):
        self.roam.setChecked(False);self.choice.setCurrentText('celebrate')
        self.choose('celebrate')
        self.receipt.setText('One little spark, offered. A visual celebration; no Graphite job or reward score was created.')


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    window = Rehearsal(Path(__file__).resolve().parents[1]);window.show()
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
