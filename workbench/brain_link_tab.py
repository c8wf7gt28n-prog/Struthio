"""Interactive source-linked hardware selection in the existing central workspace."""
import html
from PySide6.QtCore import Qt, QSize, QTimer, Signal
from PySide6.QtGui import QColor,QFont,QPainter,QPen
from PySide6.QtWidgets import QComboBox, QGraphicsRectItem, QGraphicsScene, QGraphicsView, QGridLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QSplitter, QTabWidget, QTextBrowser, QTreeWidget, QTreeWidgetItem, QWidget
from .register_tabs import ServiceTab
from .ux_assets import icon
from . import record_io as io
from .ux_polish import overline, empty_hint


class LinkView(QGraphicsView):
    selected=Signal(str)
    def __init__(self,scene):
        super().__init__(scene);self.setRenderHint(QPainter.Antialiasing);self.setMinimumHeight(185)
        self.setDragMode(QGraphicsView.ScrollHandDrag);self.setStyleSheet('QGraphicsView {background:#101317;border:1px solid #343c43;border-radius:4px;}')
        self.setAccessibleName('Native schematic relationship graph')
    def mouseDoubleClickEvent(self,event):
        item=self.itemAt(event.position().toPoint())
        while item is not None:
            if item.data(0):self.selected.emit(str(item.data(0)));event.accept();return
            item=item.parentItem()
        super().mouseDoubleClickEvent(event)


class BrainLinkTab(ServiceTab):
    def __init__(self,host):
        super().__init__(host);self.data=None;self.revision=None;self._requested=None
        row=QHBoxLayout();brand=overline('Brain Link');row.addWidget(brand)
        self.component=QComboBox();self.component.setEditable(True);self.component.setInsertPolicy(QComboBox.NoInsert)
        self.component.setMinimumWidth(200);self.component.setAccessibleName('Selected native component');row.addWidget(self.component,1)
        self.outer.addLayout(row)
        controls=QHBoxLayout();controls.addWidget(QLabel('Trace filter'))
        self.kind=QComboBox();self.kind.addItem('USB data nets','usb-data');self.kind.addItem('All signal nets','all');controls.addWidget(self.kind,1)
        refresh=QPushButton(icon(host.root,'refresh'),'Refresh');refresh.clicked.connect(self.refresh);controls.addWidget(refresh);self.outer.addLayout(controls)
        self.outer.addWidget(self.status)
        self.heading=QLabel('Read source identities, nets and linked engineering files.');self.heading.setWordWrap(True);self.heading.setStyleSheet('font-size:13pt;font-weight:600;');self.outer.addWidget(self.heading)
        self.scene=QGraphicsScene(self);self.graph=LinkView(self.scene);self.graph.selected.connect(self.choose)
        self.graph_note=QLabel('Solid silver lines = native netlist membership. Software links and physical evidence remain separate.');self.graph_note.setWordWrap(True)
        graph_page=QWidget();from PySide6.QtWidgets import QVBoxLayout
        graph_layout=QVBoxLayout(graph_page);graph_layout.setContentsMargins(0,0,0,0);graph_layout.addWidget(self.graph,1);graph_layout.addWidget(self.graph_note)
        self.pages=QTabWidget();self.pins=QTreeWidget();self.pins.setHeaderLabels(['Pin','Function','Net','Type']);empty_hint(self.pins,'Choose a component above to follow its pins and nets.');self.pins.setColumnWidth(0,60);self.pins.setColumnWidth(1,200);self.pins.setColumnWidth(2,230)
        self.pages.addTab(self.pins,icon(host.root,'pin'),'Pins / nets')
        self.sources=QTreeWidget();self.sources.setHeaderLabels(['Relationship','Current file','State']);self.sources.setColumnWidth(0,160);self.sources.setColumnWidth(1,420);self.sources.itemDoubleClicked.connect(lambda *_:self.open_source())
        self.pages.addTab(self.sources,icon(host.root,'page-link'),'Sources')
        self.records=QTreeWidget();self.records.setHeaderLabels(['Record','Statement','State']);self.records.setColumnWidth(0,240);self.records.setColumnWidth(1,460)
        self.pages.addTab(self.records,icon(host.root,'spreadsheet'),'Register')
        self.layers=QTextBrowser();self.layers.setOpenLinks(False);self.pages.addTab(self.layers,icon(host.root,'layers'),'Layers')
        for index,label in enumerate(('Native component pins and nets','Linked current source files','Related requirements and open issues','Engineering layer meanings')):self.pages.setTabToolTip(index,label)
        splitter=QSplitter(Qt.Vertical);splitter.addWidget(graph_page);splitter.addWidget(self.pages);splitter.setSizes([270,345]);self.outer.addWidget(splitter,1)
        self.action_layout=QGridLayout();self.action_buttons=[];self.action_columns=None
        for label,name,method in [('Trace to F133','brain-link',self.trace),('Open schematic','schematic',self.open_schematic),('Open source','page-link',self.open_source),('Engineering register','spreadsheet',self.open_register),('Discuss in Graphite','clip',self.discuss)]:
            b=QPushButton(icon(host.root,name),label);b.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Fixed);b.clicked.connect(method);self.action_buttons.append(b)
        self.outer.addLayout(self.action_layout);self.arrange_actions()
        self.component.activated.connect(lambda *_:self.inspect())
        self.component.lineEdit().returnPressed.connect(self.inspect);self.kind.currentIndexChanged.connect(self.inspect)
        QTimer.singleShot(0,self.refresh)
    def arrange_actions(self):
        available=self.width()-self.outer.contentsMargins().left()-self.outer.contentsMargins().right()
        width=max(b.sizeHint().width() for b in self.action_buttons);gap=max(0,self.action_layout.horizontalSpacing())
        columns=4 if available>=width*4+gap*3 else 2 if available>=width*2+gap else 1
        if columns==self.action_columns:return
        self.action_columns=columns
        while self.action_layout.count():self.action_layout.takeAt(0)
        for index,button in enumerate(self.action_buttons):self.action_layout.addWidget(button,index//columns,index%columns)
    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,'action_buttons'):self.arrange_actions()
    def title(self):return 'Brain Link'
    def selected_ref(self):
        value=self.component.currentText().split(' · ')[0].strip();return value if value else 'J14'
    def discuss(self):
        if not self.host.tabs.pin(self):return
        tab=self.host.show_clip_workspace()
        tab.load_component(self.selected_ref())
    def choose(self,ref):
        index=self.component.findData(ref)
        if index>=0:self.component.setCurrentIndex(index)
        else:self.component.setEditText(ref)
        self.inspect()
    def refresh(self):
        saved=getattr(self.host,'selection_context',None)
        desired=self.selected_ref() if self.component.count() else saved['reference'] if saved and saved['kind']=='component' else 'J14'
        def ready(data):
            self.catalog={row['reference']:row for row in data['components']}
            self.revision=data['revision'];self.component.blockSignals(True);self.component.clear()
            for c in data['components']:self.component.addItem(c['reference']+' · '+c['value'],c['reference'])
            index=self.component.findData(desired);self.component.setCurrentIndex(max(0,index));self.component.blockSignals(False)
            self.inspect()
        self.call('links.catalog',{'limit':1000},ready)
    def inspect(self):
        if not self.component.count():return
        ref=self.selected_ref();self._requested=ref
        args={'component':ref,'net_kind':self.kind.currentData()}
        if self.revision:args['expected_revision']=self.revision
        request=object();self._inspection=request
        self.call('links.inspect',args,lambda data:self.loaded(data,ref) if self._inspection is request else None)
    def loaded(self,data,ref):
        if self._requested!=ref:return
        if data['state']=='STALE':
            self.scene.clear();self.pins.clear();self.sources.clear();self.records.clear();self.data=None
            self.status.setText('STALE · native source changed · refresh before using these links');return
        self.data=data;self.revision=data['revision'];c=data['component']
        if hasattr(self.host,'bind_component'):
            self.host.bind_component(c['reference'],c['native_uuid'],data['revision'])
        self.status.setText('R10 · source '+self.revision[:12]+' · '+data.get('export_binding',{}).get('state','UNVERIFIED_EXPORT')+' · physical target BLOCKED')
        self.heading.setText(c['reference']+' · '+c['value'])
        self.component.setToolTip(self.component.currentText())
        self.heading.setToolTip('Native UUID '+c['native_uuid']+'\nFootprint '+c['footprint'])
        self.pins.clear()
        for p in c['pins']:
            row=QTreeWidgetItem([p['pin'],p['function'],p['net'],p['pin_type']]);row.setIcon(0,icon(self.host.root,'pin'));row.setToolTip(0,'R10:'+ref+':'+p['pin']+'\n'+c['native_uuid']);self.pins.addTopLevelItem(row)
        self.sources.clear()
        for source in data['source_links']:
            label=source['kind'].replace('_',' ');r=QTreeWidgetItem([label,source['path'],'CURRENT FILE' if source['available'] else 'MISSING']);r.setData(0,Qt.UserRole,source)
            r.setIcon(0,icon(self.host.root,'software-intent' if source['kind']=='software_intent' else 'page-link'));r.setToolTip(1,source['path']+'\n'+str(source['sha256']));self.sources.addTopLevelItem(r)
        if self.sources.topLevelItemCount():self.sources.setCurrentItem(self.sources.topLevelItem(0))
        self.records.clear()
        for row in data['requirements']:
            r=QTreeWidgetItem([row['record_id'],row['statement'],'DRAFT / target blocked']);r.setIcon(0,icon(self.host.root,'source-fact'));self.records.addTopLevelItem(r)
        for row in data['issues']:
            r=QTreeWidgetItem([row['id'],row['issue'],row['status']]);r.setIcon(0,icon(self.host.root,'state-warning'));self.records.addTopLevelItem(r)
        if not self.records.topLevelItemCount():self.records.addTopLevelItem(QTreeWidgetItem(['No directly linked record','Search the engineering register for broader relations.','']))
        self.layers.setHtml('<h2>Distinct engineering layers</h2><p>The graph displays native netlist membership, not copper continuity or a measured USB transaction.</p>'+''.join('<p><b>'+html.escape(x['label'])+'</b> · '+html.escape(x['state'])+'</p>' for x in data['layers'])+'<p>Native PCB inspection shows recorded geometry. Netlist adjacency cannot establish that a complete route is present. Missing measurement and model layers remain unavailable.</p>')
        self.draw_neighbors()
    def node(self,ref,x,y,selected=False):
        data=self.data;value=getattr(self,'catalog',{}).get(ref,{}).get('value','')
        box=QGraphicsRectItem(x,y,164,66);box.setPen(QPen(QColor('#ff9a32' if selected else '#63717e'),1.5));box.setBrush(QColor('#30251d' if selected else '#1b222a'));box.setData(0,ref);box.setToolTip(ref+' · '+value+'\nDouble-click to inspect current source')
        self.scene.addItem(box)
        symbol='usb-media' if ref=='J14' else 'usb-hub' if ref=='U26' else 'usb-mux' if ref in ('U25','U23') else 'f133' if ref=='U18' else 'pin'
        pix=self.scene.addPixmap(icon(self.host.root,symbol).pixmap(QSize(24,24)));pix.setParentItem(box);pix.setPos(x+11,y+12)
        title=self.scene.addText(ref,QFont('DejaVu Sans',11,QFont.Bold));title.setDefaultTextColor(QColor('#f0f2f4'));title.setParentItem(box);title.setPos(x+42,y+6)
        caption=self.scene.addText(value if len(value)<=23 else value[:21]+'…',QFont('DejaVu Sans',9));caption.setDefaultTextColor(QColor('#c6cdd4'));caption.setParentItem(box);caption.setPos(x+8,y+36)
    def draw_neighbors(self):
        self.scene.clear();ref=self.data['component']['reference'];neighbors=self.data['neighbors'][:4]
        cy=max(0,(len(neighbors)-1)*44);self.node(ref,0,cy,True)
        for i,row in enumerate(neighbors):
            y=i*88;line=self.scene.addLine(164,cy+33,290,y+33,QPen(QColor('#bac4cd'),1.5));line.setToolTip(', '.join(row['nets']))
            self.node(row['reference'],290,y)
        self.scene.setSceneRect(self.scene.itemsBoundingRect().adjusted(-24,-18,24,18));self.graph.resetTransform();self.graph.centerOn(self.scene.sceneRect().center())
        self.graph_note.setText('Native schematic links · '+str(self.data['total_neighbors'])+' matching neighbors'+(' · first four shown' if self.data['total_neighbors']>4 else '')+' · '+self.kind.currentText()+'. Silver lines are not routed copper.')
    def trace(self):
        if not self.data:return
        ref=self.selected_ref();revision=self.revision;kind=self.kind.currentData()
        self.call('links.trace',{'start':ref,'end':'U18','net_kind':kind,'expected_revision':revision},
            lambda data:self.show_trace(data) if (ref,revision,kind)==(self.selected_ref(),self.revision,self.kind.currentData()) else None)
    def show_trace(self,data):
        if data['state']=='STALE':self.loaded(data,self._requested);return
        trace=data['trace'];self.scene.clear()
        if trace['state']!='FOUND':self.status.setText('No native path within the bounded search and selected filter');return
        for i,ref in enumerate(trace['nodes']):self.node(ref,i*211,24,i==0)
        for i,edge in enumerate(trace['edges']):
            line=self.scene.addLine(i*211+164,57,(i+1)*211,57,QPen(QColor('#bac4cd'),1.5));line.setToolTip(', '.join(edge['nets']))
            label=self.scene.addText('/'.join(edge['nets']).replace('USBA3_','').replace('HUB_UP_',''),QFont('DejaVu Sans',8));label.setDefaultTextColor(QColor('#b6c2cc'));label.setPos(i*211+151,95)
        self.scene.setSceneRect(self.scene.itemsBoundingRect().adjusted(-20,-20,20,20));self.graph.resetTransform()
        if self.scene.sceneRect().width()>self.graph.viewport().width():self.graph.fitInView(self.scene.sceneRect(),Qt.KeepAspectRatio)
        self.graph_note.setText(' → '.join(trace['nodes'])+' · '+self.kind.currentText()+' · netlist topology only; hub/mux operation and routing are separate qualification.')
    def open_checked(self,source):
        if not self.data or not source['available']:return
        ref=self.data['component']['reference'];revision=self.revision
        def checked(result):
            if not self.data or (ref,revision)!=(self.data['component']['reference'],self.revision):return
            if result['state']=='STALE':self.loaded(result,self._requested);return
            p=io.project_path(self.host.root,source['path'])
            if io.sha(p)!=source['sha256']:self.status.setText('STALE · linked file changed; refresh before opening');return
            if not self.host.tabs.pin(self):return
            tab=self.host.open_document(p)
            if tab is not None and hasattr(tab,'component_find'):
                tab.component_find.setCurrentText(ref);QTimer.singleShot(50,tab.locate_component)
        self.call('links.inspect',{'component':ref,'expected_revision':revision},checked)
    def open_schematic(self):
        if self.data:
            row=next((r for r in self.data['source_links'] if r['kind']=='native_schematic'),None)
            if row:self.open_checked(row)
    def open_source(self):
        row=self.sources.currentItem()
        if row:self.open_checked(row.data(0,Qt.UserRole))
    def open_register(self):
        if not self.host.tabs.pin(self):return
        tab=self.host.show_engineering_register()
        if tab is None:return
        if self.data and self.data['requirements']:tab.focus_record(self.data['requirements'][0]['record_id'])
        elif self.data and self.data['issues']:tab.focus_record(self.data['issues'][0]['id'],'actions')
        else:tab.focus_record('R10:'+self.selected_ref(),'objects')
