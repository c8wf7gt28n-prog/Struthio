"""Recorded event order, deliberately without invented board timing."""
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget, QSizePolicy
from sdk.cli.arc1cli.console_events import LANES, event_rows


class RecordedEvents(QWidget):
    def __init__(self):
        super().__init__()
        self.rows=[]
        self.setMinimumHeight(182)
        self.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Preferred)
        self.setAccessibleName('Recorded event order, not a physical timing waveform; text events below')

    def set_trace(self, trace):
        self.rows=event_rows(trace)
        self.update()

    def paintEvent(self,event):
        p=QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(),QColor('#101720'))
        f=self.font();f.setPointSizeF(10);p.setFont(f)
        left=145;right=self.width()-18
        p.setPen(QColor('#aebfce'))
        p.drawText(16,24,'Recorded event order')
        step=(self.height()-55)/4
        for lane,title in enumerate(LANES):
            y=49+lane*step
            p.setPen(QColor('#354555'));p.drawLine(left,int(y),right,int(y))
            p.setPen(QColor('#c4cfd9'));p.drawText(12,int(y+5),title)
        if not self.rows:
            p.setPen(QColor('#aebfce'))
            p.drawText(QRectF(left,40,max(1,right-left),100),Qt.AlignCenter|Qt.TextWordWrap,'Boot the model to record events.\nNo synthetic activity is displayed.')
            return
        total=max(1,self.rows[-1]['ordinal']-self.rows[0]['ordinal'])
        for row in self.rows:
            x=left+(right-left)*(row['ordinal']-self.rows[0]['ordinal'])/total
            y=49+row['lane']*step
            color=QColor('#ffad57' if row['class']=='RTL_SIM' else '#65c9bb')
            p.setPen(QPen(color,1));p.setBrush(color);p.drawEllipse(QRectF(x-3,y-3,6,6))
        p.setPen(QColor('#aebfce'));p.drawText(max(left,right-145),24,str(len(self.rows))+' recorded events')
