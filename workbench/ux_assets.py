"""ARC visual assets shared by existing Qt workspaces and future phone clients."""
from functools import lru_cache
from pathlib import Path
from PySide6.QtCore import QByteArray, QRectF, QSize, Qt
from PySide6.QtGui import QIcon, QIconEngine, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from sdk.cli.arc1cli.ui_assets import AssetPack
from . import locations


@lru_cache(maxsize=4)
def pack(root,mtime):return AssetPack(locations.program(root))


def assets(root):
    root=Path(root).resolve();p=locations.program(root)/'branding/ux17/catalog.json'
    return pack(str(root),p.stat().st_mtime_ns)


@lru_cache(maxsize=2048)
def renderer(root,mtime,name,variant,small):
    return QSvgRenderer(QByteArray(pack(root,mtime).svg(name,variant,16 if small else 24)))


class PackedIcon(QIconEngine):
    def __init__(self,root,name):
        super().__init__();self.root=str(Path(root).resolve());self.name=name
        self.mtime=(locations.program(root)/'branding/ux17/catalog.json').stat().st_mtime_ns
    def clone(self):return PackedIcon(self.root,self.name)
    def paint(self,painter,rect,mode,state):
        if rect.isEmpty():return  # an empty rectangle would make the renderer draw the artwork at its own size
        variant='disabled' if mode==QIcon.Disabled else 'active' if mode in (QIcon.Selected,QIcon.Active) or state==QIcon.On else 'dark'
        try:renderer(self.root,self.mtime,self.name,variant,rect.width()<=18).render(painter,QRectF(rect))
        except (OSError,ValueError,KeyError):
            # A missing/corrupt asset must not throw through Qt's paint callback.
            painter.drawRect(rect.adjusted(2,2,-2,-2))
    def pixmap(self,size,mode,state):
        if size.isEmpty():return QPixmap()  # an icon shown at no size (2.x Desk tabs) has nothing to paint
        p=QPixmap(size);p.fill(Qt.transparent);q=QPainter(p)
        try:self.paint(q,p.rect(),mode,state)
        finally:q.end()
        return p


def icon(root,name):
    if name in ('clip','stacy'):
        from .static_bird import icon as bird_icon
        return bird_icon(root)
    local={'focus_layout':'focus.svg','split_editor':'split.svg'}
    if name in local:
        return QIcon(str(locations.program(root)/'branding/noir'/local[name]))
    try:
        data=assets(root);ident=data.meta['aliases'].get(name,name)
        if ident not in data.icons:return QIcon()
        return QIcon(PackedIcon(root,ident))
    except (OSError,ValueError,KeyError):return QIcon()


def image(root,path,size=None):
    p=QPixmap();p.loadFromData(assets(root).read(path))
    if size:p=p.scaled(size,Qt.KeepAspectRatio,Qt.SmoothTransformation)
    return p


def polish_buttons(widget,root):
    """Present existing actions with matching symbols; never changes authority."""
    from PySide6.QtWidgets import QPushButton
    meanings=[('export','export'),('import','import'),('preview','diff'),('candidate','candidate'),('approve','approve'),
        ('reject','reject'),('rollback','rollback'),('build','build'),('test','test'),('run','play'),('refresh','refresh'),
        ('search','search'),('find','search'),('save','save'),('source','page-link'),('open','open-folder'),
        ('trace','trace'),('pause','pause'),('stop','stop'),('send','clip'),('pin','pin-workspace')]
    for button in widget.findChildren(QPushButton):
        if not button.icon().isNull():continue
        text=button.text().replace('&','').casefold()
        found=next((name for word,name in meanings if word in text),None)
        if found:button.setIcon(icon(root,found));button.setIconSize(QSize(18,18))
