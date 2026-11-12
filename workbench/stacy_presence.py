"""Small, local character reactions over Slate's existing portrait and job states.

This layer only paints. It never submits work, changes a result or calls a
provider. The portrait remains the owner-selected cutout; movement is a short
duck/peek and lean, not a claim of new facial animation or character poses.
"""
from collections import deque
import math
import time
from PySide6.QtCore import QObject, QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class ReactionBubble(QWidget):
    """Brief, click-through speech near Slate; never takes keyboard focus."""
    def __init__(self, window):
        super().__init__(window)
        self.setObjectName('StacyReaction')
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.NoFocus)
        self.setFixedWidth(258)
        self.tail_left=False
        layout=QVBoxLayout(self);layout.setContentsMargins(13,9,23,12);layout.setSpacing(3)
        self.heading=QLabel();self.heading.setTextFormat(Qt.PlainText)
        self.heading.setStyleSheet('background:transparent;color:#ffba75;font-weight:700;font-size:15pt;')
        self.detail=QLabel();self.detail.setTextFormat(Qt.PlainText);self.detail.setWordWrap(True)
        self.detail.setStyleSheet('background:transparent;color:#edf3f9;font-size:12pt;')
        layout.addWidget(self.heading);layout.addWidget(self.detail)
        self.hide()

    def set_words(self, title, detail):
        self.heading.setText(title);self.detail.setText(detail)
        self.setAccessibleName('Graphite: '+title)
        self.setAccessibleDescription(detail)
        self.adjustSize()

    def paintEvent(self, event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing)
        area=QRectF(12 if self.tail_left else 1,1,self.width()-13,self.height()-3)
        path=QPainterPath();path.addRoundedRect(area,10,10)
        edge=area.left()+1 if self.tail_left else area.right()-1
        tip=2 if self.tail_left else self.width()-2
        path.moveTo(edge,area.top()+23)
        path.lineTo(tip,area.top()+31)
        path.lineTo(edge,area.top()+38);path.closeSubpath()
        fill=QLinearGradient(0,0,0,self.height())
        fill.setColorAt(0,QColor('#526171'));fill.setColorAt(.45,QColor('#2b3847'))
        fill.setColorAt(.5,QColor('#1d2936'));fill.setColorAt(1,QColor('#15202c'))
        p.setBrush(fill);p.setPen(QPen(QColor('#db8e48'),1));p.drawPath(path)
        p.setPen(QPen(QColor(255,255,255,100),1));p.drawLine(12,3,self.width()-27,3)
        p.end()


class StacyPresence(QObject):
    COOLDOWN=20.0
    DURATION=2.8

    def __init__(self, anchor):
        super().__init__(anchor)
        self.anchor=anchor
        self.bubble=ReactionBubble(anchor.parentWidget())
        self.started=None
        self.last_automatic=float('-inf')
        self.seen=deque(maxlen=48)
        self.primed=False
        self.last_state=None
        self.last_cue=None

    @property
    def enabled(self):
        return self.anchor.parentWidget().session.state.get('layout',{}).get('stacy_reactions',True)

    def set_enabled(self, value):
        window=self.anchor.parentWidget()
        window.session.set_layout(stacy_reactions=bool(value));window.session.save()
        if not value:self.dismiss()

    def observe(self, state, job):
        """Consume fresh visible job transitions once; never replay a startup result."""
        previous=self.last_state;self.last_state=state
        if not self.primed:
            self.primed=True
            if job:self._remember(state,job)
            return
        if not job or state not in ('done','failed','approval','paused'):return
        key=self._key(state,job)
        if key in self.seen:return
        self.seen.append(key)
        if state==previous and state in ('approval','paused'):return
        words={
            'done':('That one’s done.','The job reported completion.'),
            'failed':('Whoopsie!','That job failed. See Jobs & evidence.'),
            'approval':('Your move.','This job is waiting for your approval.'),
            'paused':('Holding here.','The job is '+str(job.get('state','paused')).lower()+'.'),
        }
        self.react(*words[state])

    def _key(self,state,job):
        return (str(job.get('id') or job.get('tool','job')),state,str(job.get('finished') or ''))

    def _remember(self,state,job):
        self.seen.append(self._key(state,job))

    def command_finished(self, good, stopped, unavailable, label):
        label=str(label or 'Command')[:65]
        if stopped:words=('Stopped.','Your call. I’m here when you’re ready.')
        elif unavailable:words=('Not here yet.',label+' is unavailable on this host.')
        elif good:words=('That one’s done.',label+' finished successfully.')
        else:words=('Whoopsie!',label+' failed. See Output.')
        return self.react(*words)

    def cameo(self):
        return self.react('Whoopsie!','You found my little party trick.',manual=True)

    def react(self, title, detail, manual=False):
        window=self.anchor.parentWidget();now=time.monotonic()
        if not self.anchor.isVisible() or window.isMinimized() or getattr(window,'_home_active',False):return False
        if self.anchor._dragging:return False
        overlay=getattr(window,'clip_overlay',None)
        if not manual and (not self.enabled or self.anchor.collapsed or overlay is not None and overlay.isVisible()):return False
        if not manual and now-self.last_automatic<self.COOLDOWN:return False
        self.dismiss();self.started=now
        if not manual:self.last_automatic=now
        self.last_cue={'title':title,'detail':detail,'manual':manual}
        self.bubble.set_words(title,detail)
        self.anchor.setAccessibleDescription('Graphite: '+title+' '+detail)
        self.anchor.ticker.setInterval(40 if not self.anchor.reduce_motion() else 80)
        self.tick();self.anchor.update()
        return True

    def dismiss(self):
        self.started=None;self.bubble.hide()
        if hasattr(self.anchor,'ticker'):self.anchor.ticker.setInterval(80)
        if hasattr(self.anchor,'state'):self.anchor._describe()
        self.anchor.update()

    def position(self):
        window=self.anchor.parentWidget()
        bottom=window.height()-(window.statusBar().height() if window.statusBar().isVisible() else 0)
        x=self.anchor.x()-self.bubble.width()+8
        y=self.anchor.y()+4
        tail_left=x<8
        if x<8:
            x=self.anchor.x()+self.anchor.width()-8
            if x+self.bubble.width()>window.width()-8:x=8
            y=self.anchor.y()-self.bubble.height()-6
        if self.bubble.tail_left!=tail_left:
            self.bubble.tail_left=tail_left
            self.bubble.layout().setContentsMargins(23 if tail_left else 13,9,13 if tail_left else 23,12)
            self.bubble.update()
        self.bubble.move(max(6,min(x,window.width()-self.bubble.width()-6)),
                         max(6,min(y,bottom-self.bubble.height()-6)))
        self.bubble.raise_();self.anchor.raise_()

    def tick(self):
        if self.started is None:return
        if not self.anchor.isVisible() or getattr(self.anchor.parentWidget(),'_home_active',False):
            self.dismiss();return
        elapsed=time.monotonic()-self.started
        if elapsed>=self.DURATION:
            self.dismiss();return
        self.position()
        self.bubble.setVisible(self.anchor.reduce_motion() or elapsed>=.2)

    def pose(self):
        """Portrait offset/lean, within the existing companion rectangle."""
        if self.anchor.reduce_motion() or self.anchor.collapsed or self.anchor._dragging:return 0.0,0.0
        if self.started is not None:
            elapsed=time.monotonic()-self.started
            if elapsed<.13:
                return self.anchor.height()*.62*(elapsed/.13)**2,0.0
            if elapsed<.43:
                t=(elapsed-.13)/.30
                return self.anchor.height()*.62*(1-t)**3,-5.0*math.sin(math.pi*t)
            if elapsed<.85:
                t=(elapsed-.43)/.42
                return -2.0*math.sin(math.pi*t),2.2*math.sin(math.pi*t)
        if not self.enabled:return 0.0,0.0
        return 0.0, -1.5 if self.anchor.hover else .35*math.sin(self.anchor.phase*.55)
