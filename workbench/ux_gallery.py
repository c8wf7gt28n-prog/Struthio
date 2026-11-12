"""Searchable, working asset gallery. Uses the installed resources, not mockups."""
from .text_prompts import writing_prompt
import html
from .static_bird import icon as bird_icon
from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QSplitter, QTabWidget, QTextBrowser, QVBoxLayout, QWidget)
from .ux_assets import assets, icon


class AssetGalleryTab(QWidget):
    def __init__(self,host):
        super().__init__();self.host=host;self.pack=assets(host.root)
        outer=QVBoxLayout(self);row=QHBoxLayout()
        title=QLabel('UX ASSET LIBRARY');title.setStyleSheet('font-weight:700;color:#ffad67;');row.addWidget(title)
        self.find=QLineEdit();writing_prompt(self.find, 'Search hardware, action, state or file type');self.find.setClearButtonEnabled(True)
        self.find.setAccessibleName('Find reusable UX asset');self.find.textChanged.connect(self.populate);row.addWidget(self.find,1)
        self.category=QComboBox();self.category.addItem('All categories','')
        for c in sorted({i['category'] for i in self.pack.icons.values()}):self.category.addItem(c.replace('_',' ').title(),c)
        self.category.currentIndexChanged.connect(self.populate);row.addWidget(self.category);outer.addLayout(row)
        self.status=QLabel();self.status.setWordWrap(True);outer.addWidget(self.status)
        self.pages=QTabWidget();outer.addWidget(self.pages,1)
        page=QWidget();layout=QVBoxLayout(page);layout.setContentsMargins(0,0,0,0)
        split=QSplitter(Qt.Vertical);self.icons=QListWidget();self.icons.setViewMode(QListWidget.IconMode)
        self.icons.setResizeMode(QListWidget.Adjust);self.icons.setMovement(QListWidget.Static)
        self.icons.setIconSize(QSize(32,32));self.icons.setGridSize(QSize(124,92));self.icons.setWordWrap(True)
        self.icons.setSelectionMode(QAbstractItemView.SingleSelection);self.icons.currentItemChanged.connect(self.describe)
        self.detail=QTextBrowser();self.detail.setOpenLinks(False);split.addWidget(self.icons);split.addWidget(self.detail);split.setSizes([440,165]);layout.addWidget(split)
        self.pages.addTab(page,icon(host.root,'asset-library'),'Icons')
        self.pages.addTab(self.pose_page(),icon(host.root,'clip'),'Slate')
        self.pages.addTab(self.part_page('03_components','UI components'),icon(host.root,'layout'),'Components')
        self.pages.addTab(self.part_page('05_arcos','ARC-OS assets'),icon(host.root,'arcos'),'ARC-OS')
        from .editorial_art import poster_panel
        self.pages.addTab(poster_panel(host.root),icon(host.root,'page-link'),'ARC Concern')
        QTimer.singleShot(0,self.populate)
    def title(self):return 'UX asset library'
    def populate(self,*_):
        self.icons.clear();q=self.find.text().casefold();category=self.category.currentData();rows=[]
        for row in self.pack.icons.values():
            if (not category or row['category']==category) and q in str(row).casefold():rows.append(row)
        for row in rows:
            item=QListWidgetItem(icon(self.host.root,row['id']),'Slate' if row['id']=='clip' else row['label']);item.setData(Qt.UserRole,row)
            item.setToolTip(row['meaning']);self.icons.addItem(item)
        self.status.setText('Aqua Glass · %d designs · %d shown · 6 SVG variants · offline'%(len(self.pack.icons),len(rows)))
        if rows:self.icons.setCurrentRow(0)
        else:self.detail.setHtml('<h3>No matching assets</h3><p>Clear the search or choose another category.</p>')
    def describe(self,item,*_):
        if item is None:return
        r=dict(item.data(Qt.UserRole));e=lambda v:html.escape(str(v))
        if r['id']=='clip':r.update(label='Slate',meaning='Open the ARC Ledger assistant conversation')
        self.detail.setHtml('<h2>'+e(r['label'])+'</h2><p>'+e(r['meaning'])+'</p><p><b>Asset ID</b> '+e(r['id'])+' · <b>Category</b> '+e(r['category'])+'</p><p>Aqua glass and polished silver, with dark, light, active and disabled materials. Compact masters simplify highlights for small controls. Monochrome and currentColor outlines remain available. PNG exports match the installed vectors.</p><p><code>02_icons/svg/dark/'+e(r['id'])+'.svg</code></p><p>Artwork conveys a meaning; it never grants a permission or establishes an engineering result.</p>')
    def pose_page(self):
        from PySide6.QtWidgets import QScrollArea
        body = QWidget(); layout = QVBoxLayout(body)
        preview = QLabel(); preview.setAlignment(Qt.AlignCenter)
        preview.setAccessibleName('Slate, your ARC Ledger assistant')
        preview.setPixmap(bird_icon(self.host.root).pixmap(300,300).scaled(
            QSize(340, 425), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        layout.addWidget(preview)
        title = QLabel('SLATE'); title.setAlignment(Qt.AlignCenter); layout.addWidget(title)
        note = QLabel('Slate is the Struthio bird. This preview uses the unchanged approved resting pose. The desktop bird faces into the work and admits brief event cues; its badge reports actual work state.')
        note.setWordWrap(True); layout.addWidget(note); layout.addStretch()
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(body); return scroll
    def part_page(self,prefix,title):
        from PySide6.QtWidgets import QScrollArea
        body=QWidget();v=QVBoxLayout(body);heading=QLabel(title);heading.setStyleSheet('font-weight:700;');v.addWidget(heading)
        names=[n for n in self.pack.meta['files'] if n.startswith(prefix+'/') and n.endswith('.svg') and ('/light/' not in n)]
        for name in names[:18]:
            label=QLabel(name.split('/')[-1].removesuffix('.svg').replace('-',' ').title());label.setWordWrap(True);v.addWidget(label)
            raw=self.pack.read(name)
            from PySide6.QtSvg import QSvgRenderer
            from PySide6.QtCore import QByteArray
            from PySide6.QtGui import QPixmap,QPainter
            renderer=QSvgRenderer(QByteArray(raw));size=renderer.defaultSize();size.scale(QSize(680,180),Qt.KeepAspectRatio)
            pix=QPixmap(size);pix.fill(Qt.transparent);painter=QPainter(pix);renderer.render(painter);painter.end()
            img=QLabel();img.setPixmap(pix);img.setAlignment(Qt.AlignLeft);v.addWidget(img)
        v.addStretch();scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(body);return scroll
