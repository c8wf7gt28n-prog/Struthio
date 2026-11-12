"""Approved bird pixels with directional, event-driven presentation; no tool authority."""
from functools import lru_cache
from pathlib import Path
import hashlib,json
from PySide6.QtCore import Qt,QRectF,QSize
from PySide6.QtGui import QPixmap,QIcon,QPainter
from PySide6.QtWidgets import QWidget,QSizePolicy
from . import locations


@lru_cache(maxsize=18)
def sprite(root,pose="rest"):
    base=locations.program(root)/'branding/slate'
    data=json.loads((base/'assets.json').read_text())
    row=data['files']['slate_keyposes.png'];raw=(base/'slate_keyposes.png').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=row['sha256'] or len(raw)!=row['bytes']:
        raise ValueError('SLATE_ART_CHANGED')
    pix=QPixmap();pix.loadFromData(raw)
    row=next((p for p in data['poses'] if p['name']==pose),data['poses'][0])
    rect=QRectF(*row['rect'])
    if pix.isNull() or not QRectF(pix.rect()).contains(rect):
        raise ValueError('SLATE_ART_RECT')
    return pix,rect


def paint(painter,root,area,facing="right",pose="rest"):
    try:pix,rect=sprite(str(Path(root).resolve()),pose)
    except (OSError,ValueError,KeyError):
        painter.drawText(QRectF(area),Qt.AlignCenter,'Slate');return
    area=QRectF(area);scale=min(area.width()/rect.width(),area.height()/rect.height())
    target=QRectF(area.center().x()-rect.width()*scale/2,
                  area.bottom()-rect.height()*scale,rect.width()*scale,rect.height()*scale)
    painter.save();painter.setRenderHint(QPainter.SmoothPixmapTransform)
    if facing=="left":
        painter.translate(target.center().x(),0);painter.scale(-1,1);painter.translate(-target.center().x(),0)
    painter.drawPixmap(target,pix,rect);painter.restore()


def icon(root):
    try:
        pix,rect=sprite(str(Path(root).resolve()))
        return QIcon(pix.copy(rect.toRect()))
    except (OSError,ValueError,KeyError):return QIcon()


class BirdView(QWidget):
    def __init__(self,root,parent=None):
        super().__init__(parent);self.root=root
        self.setAccessibleName('Slate, the Struthio bird')
        self.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Expanding)
        self.setMinimumSize(80,80)
    def sizeHint(self):return QSize(250,220)
    def paintEvent(self,event):
        painter=QPainter(self);paint(painter,self.root,self.rect().adjusted(8,8,-8,-8))
