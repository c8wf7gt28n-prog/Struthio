"""Hardware properties, real footprint drawings and scoped file browsing."""
from .text_prompts import writing_prompt
from pathlib import Path
import html
import hashlib
from PySide6.QtCore import Qt, QRectF, QSize, QTimer, QSignalBlocker
from PySide6.QtGui import QColor, QPainter, QPen, QFont, QPixmap, QIcon, QImageReader
from PySide6.QtWidgets import QWidget, QLabel, QPushButton, QTextBrowser, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem, QHeaderView, QLineEdit, QComboBox, QStackedWidget, QListWidget, QListWidgetItem
from . import hardware_browser, hardware_review
from .hardware_nav import file_icon


class FootprintDrawing(QWidget):
    """Pad placement from native CAD, explicitly not a photograph or package outline."""
    def __init__(self, data):
        super().__init__(); self.data=data; self.setMinimumSize(190,200)
    def paintEvent(self, event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);p.fillRect(self.rect(),QColor('#101316'))
        pads=self.data['pads']
        if not pads:return
        xs=[v['at'][0]+sign*v['size'][0]/2 for v in pads for sign in (-1,1)]
        ys=[v['at'][1]+sign*v['size'][1]/2 for v in pads for sign in (-1,1)]
        scale=min((self.width()-44)/max(max(xs)-min(xs),1),(self.height()-65)/max(max(ys)-min(ys),1))
        p.translate(self.width()/2,self.height()/2-9);p.scale(scale,scale)
        p.translate(-(min(xs)+max(xs))/2,-(min(ys)+max(ys))/2)
        for v in pads:
            p.save();p.translate(*v['at']);p.rotate(-(v['angle']-self.data['rotation_deg']))
            p.setPen(QPen(QColor('#d59061'),.04));p.setBrush(QColor('#b9754c'))
            w,h=v['size'];rect=QRectF(-w/2,-h/2,w,h)
            p.drawEllipse(rect) if v['shape']=='circle' else p.drawRect(rect)
            p.restore()
        p.resetTransform();p.setPen(QColor('#adb7c1'));p.setFont(QFont('Segoe UI',8))
        p.drawText(self.rect().adjusted(5,self.height()-35,-5,-3),Qt.AlignCenter,
                   self.data['ref']+' · native CAD pad layout\nNot a photo or package outline')
        p.end()


class HardwareOverviewTab(QWidget):
    def __init__(self, window, device):
        super().__init__();self.window=window;self.device=device;self.path=None
        lay=QVBoxLayout(self);lay.setContentsMargins(12,9,12,9)
        head=QLabel(device.title);head.setObjectName('heading');lay.addWidget(head)
        role=QLabel(device.role);role.setObjectName('subheading');lay.addWidget(role)
        data=hardware_review.component(window.root,device.id)
        if data:
            top=QHBoxLayout();drawing=FootprintDrawing(data);top.addWidget(drawing,2)
            properties=QTextBrowser();properties.setMinimumHeight(220)
            rows=[('Reference',data['ref']),('CAD value',data['value']),('Footprint',data['footprint']),
                  ('Board anchor','%g, %g mm'%tuple(data['anchor_mm'])),('Rotation','%g°'%data['rotation_deg']),
                  ('Placement side',data['layer']),('Pad records',str(len(data['pads'])))]
            properties.setHtml('<h3>Physical placement · DESIGN</h3><table>'+''.join(
                '<tr><td style="color:#9ba6ae;padding:4px">'+html.escape(k)+'</td><td style="padding:4px">'+html.escape(v)+'</td></tr>' for k,v in rows)+'</table>')
            properties.setToolTip(data['source']+'\nSHA-256 '+data['sha256']);top.addWidget(properties,3)
            lay.addLayout(top)
        else:
            note=QLabel('No verified component photograph is included in this project.');note.setWordWrap(True);lay.addWidget(note)
        evidence=QTextBrowser();evidence.setObjectName('hardwareEvidence')
        evidence.setOpenExternalLinks(False);evidence.setMarkdown(self._overview_text());lay.addWidget(evidence,1)
        notice=QLabel('Expand this component in the hardware navigator for its files. Physical specifications remain design records; no board measurement is implied.')
        notice.setWordWrap(True);notice.setObjectName('subheading');lay.addWidget(notice)
    def _overview_text(self):
        if self.device.overview:
            source=self.window.root/self.device.overview
            if source.is_file():return source.read_text(encoding='utf-8',errors='replace')[:14000]+f'\n\nSource: `{self.device.overview}`'
        return 'No source-backed properties document is available.'
    def title(self):return self.device.title
    def info(self):return self.device.title+' · properties and placement from project sources · DESIGN'


class HardwareGroupTab(QWidget):
    def __init__(self, window, device, group):
        super().__init__();self.window=window;self.device=device;self.group=group;self.path=None;self.folder=None
        self.preview_cache={};self.generation=0;self.view_key=device.id+'/'+group.title
        lay=QVBoxLayout(self);lay.setContentsMargins(9,8,9,8)
        title=QLabel(f'{device.title} / {group.title}');title.setObjectName('heading');lay.addWidget(title)
        bar=QHBoxLayout();self.up=QPushButton('↑ Up');self.up.clicked.connect(self.go_up);bar.addWidget(self.up)
        self.home=QPushButton('Category');self.home.clicked.connect(lambda:self.navigate(None));bar.addWidget(self.home)
        self.location=QLabel();self.location.setWordWrap(True);bar.addWidget(self.location,1);lay.addLayout(bar)
        row=QHBoxLayout();self.filter=QLineEdit();writing_prompt(self.filter, 'Filter this folder…');self.filter.textChanged.connect(self.refresh);row.addWidget(self.filter,1)
        from .settings_registry import VIEW_MODES
        self.mode=QComboBox();self.mode.addItems(list(VIEW_MODES));self.mode.setAccessibleName(f'{device.title} {group.title} view mode')
        self.mode.setCurrentText(window.session.state.get('category_views',{}).get(self.view_key,VIEW_MODES[0]))
        self.mode.currentIndexChanged.connect(self.mode_chosen);row.addWidget(self.mode);lay.addLayout(row)
        self.stack=QStackedWidget();self.list=QTreeWidget();self.list.setRootIsDecorated(False);self.list.setAlternatingRowColors(True)
        self.list.setHeaderLabels(['Name','Kind','Size','Location']);self.list.header().setSectionResizeMode(0,QHeaderView.Stretch)
        self.list.setColumnWidth(1,88);self.list.setColumnWidth(2,65);self.list.setColumnWidth(3,120)
        self.list.itemActivated.connect(self.open_selected);self.stack.addWidget(self.list)
        self.tiles=QListWidget();self.tiles.setViewMode(QListWidget.IconMode);self.tiles.setResizeMode(QListWidget.Adjust)
        self.tiles.setMovement(QListWidget.Static);self.tiles.setIconSize(QSize(200,128));self.tiles.setGridSize(QSize(226,180))
        self.tiles.setWordWrap(True);self.tiles.itemActivated.connect(self.open_selected);self.stack.addWidget(self.tiles)
        self.list.setAccessibleName(f'{device.title} {group.title} files');lay.addWidget(self.stack,1)
        self.note=QLabel();self.note.setWordWrap(True);lay.addWidget(self.note);self.navigate(None)
    def navigate(self,folder):
        self.folder=folder;self.filter.blockSignals(True);self.filter.clear();self.filter.blockSignals(False);self.refresh()
    def go_up(self):
        sources=hardware_browser.roots(self.window.root,self.device,self.group.title)
        self.navigate(None if self.folder in sources else self.folder.parent if self.folder else None)
    def mode_chosen(self,*_):
        self.refresh();self.remember_mode()
    def remember_mode(self):
        """An explicit choice is one journaled hardware.category_views change; refreshes and unchanged picks write nothing."""
        bridge=getattr(self.window,'ledger_bridge',None)
        if bridge is None:return None
        from . import ledger_control
        from .engineering_kernel import operator
        mode=self.mode.currentText();response=None
        for attempt in range(2):  # a one-entry patch merges deterministically after a concurrent change
            row=next(r for r in ledger_control.settings(bridge.kernel)['settings'] if r['key']==ledger_control.VIEW_MODES_KEY)
            patched=ledger_control.category_view_patch(row['stored'],self.view_key,mode)
            if patched is None:return None
            response=bridge.kernel.dispatch('ledger.settings.set',dict(key=ledger_control.VIEW_MODES_KEY,value=patched,expected_revision=row['revision']),operator())
            if response['ok']:bridge.sync_profile(force=True);bridge.publish_settings_readback();return response['result']
            if 'SETTING_REVISION_CHANGED' not in response['error']['message']:break
        # A refused save leaves the store unchanged, so the pane shows the saved mode again and the row stays truthful.
        self.follow_saved(row['stored'] or {})
        self.window.statusBar().showMessage('Hardware view not saved: '+response['error']['message'].split('; your draft')[0]+' · the pane shows the saved mode',6000);return None
    def follow_saved(self,views):
        """Consumer-side update from the saved map; blocked signals so a synchronized pane never journals again."""
        mode=views.get(self.view_key,self.mode.itemText(0))
        if mode==self.mode.currentText():return
        with QSignalBlocker(self.mode):self.mode.setCurrentText(mode)
        self.refresh()
    def refresh(self,*_):
        self.generation+=1;generation=self.generation
        rows=hardware_browser.entries(self.window.root,self.device,self.group.title,self.folder)
        query=self.filter.text().casefold();visible=[r for r in rows if query in r['name'].casefold()]
        self.location.setText(str(self.folder.relative_to(self.window.root)) if self.folder else self.group.title)
        self.up.setEnabled(self.folder is not None);self.list.clear();self.tiles.clear()
        visual={'.png','.jpg','.jpeg','.webp','.bmp','.kicad_sch','.kicad_pcb','.step','.stl'}
        thumbs=self.mode.currentText()=='Thumbnails' or (self.mode.currentIndex()==0 and bool(rows) and all(r['is_dir'] or Path(r['path']).suffix.lower() in visual for r in rows))
        self.stack.setCurrentIndex(1 if thumbs else 0)
        for index,r in enumerate(visible):
            path=self.window.root/r['path'];icon=self.window.nav_icon('folder' if r['is_dir'] else file_icon(path))
            size='—' if r['is_dir'] else f'{r["bytes"]:,} B'
            item=QTreeWidgetItem([r['name'],r['kind'],size,str(Path(r['path']).parent)])
            item.setIcon(0,icon);item.setData(0,Qt.UserRole,r);item.setToolTip(0,r['path']);self.list.addTopLevelItem(item)
            if thumbs:
                tile=QListWidgetItem(icon,r['name']+'\n'+r['kind'])
                tile.setData(Qt.UserRole,r);tile.setToolTip(r['path']);self.tiles.addItem(tile)
                if index<32 and not r['is_dir']:
                    QTimer.singleShot(index*20, self, lambda p=path,t=tile,f=icon,g=generation:self.load_thumbnail(p,t,f,g))
        self.count=len(rows);self.note.setText(f'{len(visible)} of {len(rows)} items · double-click or Enter to open · folders stay separate from files')
    def load_thumbnail(self,path,tile,fallback,generation):
        if generation!=self.generation:return
        try:
            if path.stat().st_size>16*1024*1024:return
            key=(str(path),hashlib.sha256(path.read_bytes()).hexdigest())
            icon=self.preview_cache.get(key)
            if icon is None:
                icon=self.thumbnail(path,fallback)
                if len(self.preview_cache)>=32:self.preview_cache.pop(next(iter(self.preview_cache)))
                self.preview_cache[key]=icon
            tile.setIcon(icon)
        except (ValueError,OSError):pass
    def thumbnail(self,path,fallback):
        suffix=path.suffix.lower()
        if suffix in ('.png','.jpg','.jpeg','.webp','.bmp'):
            if path.stat().st_size>16*1024*1024:return fallback
            reader=QImageReader(str(path));size=reader.size()
            if size.width()*size.height()>40000000 or not size.isValid():return fallback
            reader.setAutoTransform(True);reader.setScaledSize(size.scaled(QSize(200,128),Qt.KeepAspectRatio));im=reader.read()
            if not im.isNull():return QIcon(QPixmap.fromImage(im))
        if suffix in ('.kicad_sch','.kicad_pcb'):
            if path.stat().st_size>2*1024*1024:return fallback
            from .viewer_tabs import CadViewerTab
            try:
                viewer=CadViewerTab(path)
                for item in viewer.scene.items():
                    if hasattr(item,'pen'):
                        pen=item.pen();pen.setCosmetic(True);pen.setWidthF(.8);item.setPen(pen)
                pix=QPixmap(200,128);pix.fill(QColor('#101316'));p=QPainter(pix)
                viewer.scene.render(p,QRectF(5,5,190,118),viewer.scene.itemsBoundingRect());p.end();viewer.deleteLater();return QIcon(pix)
            except (ValueError,OSError):return fallback
        if suffix in ('.c','.h','.sv','.v','.md','.txt','.json','.csv','.py','.log','.ld') or path.name=='Makefile':
            try:
                with path.open(encoding='utf-8',errors='replace') as f:text=f.read(1200)
                pix=QPixmap(200,128);pix.fill(QColor('#1b2025'));p=QPainter(pix);p.setPen(QColor('#aab8c4'));p.setFont(QFont('Monospace',6))
                p.drawText(QRectF(8,7,148,98),Qt.AlignLeft|Qt.AlignTop,'\n'.join(text.splitlines()[:11]));p.end();return QIcon(pix)
            except OSError:return fallback
        return fallback
    def open_selected(self,item,*_):
        r=item.data(0,Qt.UserRole) if isinstance(item,QTreeWidgetItem) else item.data(Qt.UserRole)
        path=self.window.root/r['path']
        if r['is_dir']:self.navigate(path)
        else:self.window.open_document(path)
    def title(self):return f'{self.device.id.upper()} / {self.group.title}'
    def info(self):return f'{self.count} folder items · {self.title()}'


class HardwareReviewTab(QWidget):
    def __init__(self,window):
        super().__init__();self.window=window;self.path=None
        lay=QVBoxLayout(self);row=QHBoxLayout();title=QLabel('Hardware source audit');title.setObjectName('heading');row.addWidget(title,1)
        refresh=QPushButton('Recheck sources');refresh.clicked.connect(self.refresh);row.addWidget(refresh);lay.addLayout(row)
        self.text=QTextBrowser();lay.addWidget(self.text,1);self.refresh()
    def refresh(self):
        try:
            self.report=self.window.engine_hardware_review();r=self.report;c=r['counts'];d=r['archived_drc'];b=c['board']
            md=f'''# {r['status'].replace('_',' ')} · fabrication HOLD
+Fresh read-only cross-check of the installed PCB, netlist and board plan. No KiCad ERC/DRC or physical board test was run.
+
+| Current source observation | Count |
+|---|---:|
+| PCB footprints / netlist components / planned components | {b['footprints']} / {c['components_xml']} / {c['components_board_plan']} |
+| PCB pad records | {b['pads']} |
+| Copper segments / vias | {b['segments']} / {b['vias']} |
+| Named connected nets in netlist | {c['nets_connected']} |
+| Source disagreements / warnings | {c['errors']} / {c['warnings']} |
+
+## Archived DRC — not rerun
+**{d['unconnected_items']} unconnected items · {d['violations']} violations · {d['schematic_parity']} schematic-parity items.**
+
+Recorded {d['date']} with KiCad {d['kicad_version']}. This archive is not bound to the current PCB hash; it cannot certify today's board. Copper segment counts do not measure routing completion.
+
+## Evidence freshness
+P8 source hashes: **{'MATCH' if r['p8_evidence_fresh'] else 'STALE'}**. Source agreement means matching records, not a routed or electrically validated board.
+
+## Next engineering work
+Close unconnected routing; qualify footprints, power rails, high-speed links and startup on silicon. The workbench can inspect these sources but cannot replace native KiCad or bench measurements.
+
+## Source hashes
+'''.replace('\n+','\n')
            for path,digest in r['source_hashes_sha256'].items():md+=f'\n- `{path}`\n  SHA-256 `{digest}`\n'
            for kind,items in r['findings'].items():
                if items:md+='\n## '+kind+'\n'+str(items)
            self.text.setMarkdown(md)
        except (ValueError,OSError,KeyError) as exc:self.text.setPlainText('Source audit unavailable: '+str(exc))
    def title(self):return 'Hardware source audit'
    def info(self):return 'STATIC_CHECK · read-only source audit · fabrication HOLD'
