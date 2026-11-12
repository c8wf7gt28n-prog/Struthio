"""Source connections with concise summaries and expandable technical details."""
from .text_prompts import writing_prompt
import json
from PySide6.QtCore import Qt,QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QLabel,QPushButton,QComboBox,
 QLineEdit,QTreeWidget,QTreeWidgetItem,QTextBrowser,QPlainTextEdit,QTabWidget,QFileDialog,QScrollArea,QCheckBox)
from sdk.cli.arc1cli import record_store as records
from .register_tabs import ServiceTab
from . import locations

class KnowledgeTab(ServiceTab):
    def __init__(self,host):
        super().__init__(host);self.pending=None;self.connection=None;self.epoch=0;self.source_count=0
        title=QLabel('GRAPHITE · SOURCE CONNECTIONS');title.setStyleSheet('font-size:18px;font-weight:bold');self.outer.addWidget(title)
        self.summary=QLabel('Connect ROM originals and identify a V1 reference snapshot.');self.summary.setWordWrap(True);self.outer.addWidget(self.summary)
        row=QHBoxLayout();self.connections=QComboBox();self.connections.setAccessibleName('Private source connection');self.connections.currentIndexChanged.connect(self.select_connection);row.addWidget(self.connections,1)
        refresh=QPushButton('Refresh');refresh.clicked.connect(self.refresh);row.addWidget(refresh);self.outer.addLayout(row);self.source_controls=[self.summary,self.connections,refresh]
        grid=QGridLayout()
        for i,(label,fn) in enumerate([('Connect ROM folder',self.attach),('Inspect locked project archive',self.baseline),('Cancel source job',self.cancel),('Revoke selected connection',self.revoke)]):
            button=QPushButton(label);button.setAccessibleName(label);button.clicked.connect(fn);grid.addWidget(button,i//2,i%2);self.source_controls.append(button)
        self.outer.addLayout(grid)
        self.pages=QTabWidget();self.outer.addWidget(self.pages,1)
        library=QWidget();box=QVBoxLayout(library);row=QHBoxLayout();self.query=QLineEdit();writing_prompt(self.query, 'Part number, parameter or original Chinese text');self.query.returnPressed.connect(self.search);row.addWidget(self.query,1)
        find=QPushButton('Search ROM');find.clicked.connect(self.search);row.addWidget(find);box.addLayout(row)
        self.hits=QTreeWidget();self.hits.setHeaderLabels(['Original','Physical page','Availability']);self.hits.setAccessibleName('Verified ROM search results');self.hits.itemSelectionChanged.connect(self.selected);box.addWidget(self.hits,1)
        self.excerpt=QTextBrowser();self.excerpt.setOpenExternalLinks(False);self.excerpt.setMaximumHeight(120);box.addWidget(self.excerpt)
        read=QPushButton('Reopen and render original page');read.clicked.connect(self.read_page);box.addWidget(read);self.pages.addTab(library,'ROM sources')
        original=QWidget();obox=QVBoxLayout(original);self.page_note=QLabel('Select a search result and reopen its original page.');self.page_note.setWordWrap(True);obox.addWidget(self.page_note)
        self.page_text=QPlainTextEdit();self.page_text.setReadOnly(True);self.page_text.setAccessibleName('Reextracted original text');obox.addWidget(self.page_text,1)
        self.image=QLabel();self.image.setAlignment(Qt.AlignCenter);self.image.setAccessibleName('Original PDF page image');scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(self.image);obox.addWidget(scroll,1);self.pages.addTab(original,'Original page')
        baseline=QWidget();bbox=QVBoxLayout(baseline);self.baseline_note=QLabel('A reference snapshot does not promote source into the active project.');self.baseline_note.setWordWrap(True);bbox.addWidget(self.baseline_note)
        self.baseline_sources=QTreeWidget();self.baseline_sources.setHeaderLabels(['V1 source path','Bytes','Identity']);bbox.addWidget(self.baseline_sources,1)
        select=QPushButton('Select as V1 reference baseline');select.clicked.connect(self.select_baseline);bbox.addWidget(select);self.pages.addTab(baseline,'Project snapshot')
        from .engineering_map_qt import EngineeringMapTab
        self.map_page=EngineeringMapTab(host,self);self.pages.addTab(self.map_page,'Engineering map')
        from .evidence_compiler_qt import EvidenceCompilerTab
        self.packet_page=EvidenceCompilerTab(host,self);self.pages.addTab(self.packet_page,'Evidence Compiler')
        from .investigation_qt import InvestigationTab
        self.investigation_page=InvestigationTab(host,self);self.pages.addTab(self.investigation_page,'Investigations')
        self.technical_toggle=QCheckBox('Technical details');self.technical_toggle.toggled.connect(self.toggle_details);self.outer.addWidget(self.technical_toggle)
        self.technical=QPlainTextEdit();self.technical.setReadOnly(True);self.technical.setAccessibleName('Source connection technical details');self.technical.setMaximumHeight(150);self.technical.hide();self.outer.addWidget(self.technical)
        self.outer.addWidget(self.status);self.timer=QTimer(self);self.timer.setInterval(600);self.timer.timeout.connect(self.poll)
        font=locations.program(host.root)/'branding/fonts/NotoSansCJKsc-Regular.otf'
        if font.is_file():
            from PySide6.QtGui import QFontDatabase,QFont
            ident=QFontDatabase.addApplicationFont(str(font));families=QFontDatabase.applicationFontFamilies(ident)
            if families:self.page_text.setFont(QFont(families[0],12))
        self.pages.currentChanged.connect(self.context_controls)
        QTimer.singleShot(0,self.refresh)
    def context_controls(self,*_):
        mapped=self.pages.currentWidget() in (self.map_page,self.packet_page,self.investigation_page)
        for widget in self.source_controls:widget.setVisible(not mapped)
        self.technical_toggle.setVisible(not mapped);self.technical.setVisible(not mapped and self.technical_toggle.isChecked())
    def title(self):return 'Graphite · Source connections'
    def info(self):return 'Original sources · %d private connection(s) · design acceptance remains separate'%self.source_count
    def toggle_details(self,value):self.technical.setVisible(value)
    def refresh(self):self.call('knowledge.status',{},self.loaded)
    def loaded(self,value):
        current=self.connections.currentData();self.connections.blockSignals(True);self.connections.clear()
        for row in value['sources']:self.connections.addItem(row['title']+' · '+row['state'],row['id'])
        self.source_count=len(value['sources']);self.connections.setCurrentIndex(max(0,self.connections.findData(current)));self.connections.blockSignals(False);self.select_connection()
        if not value['sources']:self.summary.setText('No private source connections yet. Choose a mounted ROM folder to begin.')
    def clear_page(self):
        self.page_text.clear();self.image.clear();self.page_note.setText('Original page not currently opened.')
    def select_connection(self,*_):
        self.epoch+=1;epoch=self.epoch;self.hits.clear();self.excerpt.clear();self.clear_page();self.connection=None;self.baseline_sources.clear();self.summary.setText('Checking the selected source connection.')
        ident=self.connections.currentData()
        if not ident:return
        def loaded(value):
            if self.epoch!=epoch:return
            self.connection=value;self.technical.setPlainText(json.dumps(value,ensure_ascii=False,indent=2))
            if value['kind']=='ROM':
                r=value['report'];self.summary.setText('%s · %d vendor PDFs · archive verified; current design applicability is separate.'%(value['title'],r['vendor_documents']));self.pages.setCurrentIndex(0)
                self.call('knowledge.sources',{'id':ident},lambda r:self.catalog_loaded(r,epoch))
            else:
                report=value['report'];self.summary.setText('V1 reference snapshot · '+value['state']);self.baseline_note.setText('Original archive preserved. '+value['state']+'. No source promotion or fabrication approval.')
                for row in report['selected_sources']:
                    self.baseline_sources.addTopLevelItem(QTreeWidgetItem([row['path'],str(row['bytes']),row['sha256'][:16]]))
                self.pages.setCurrentIndex(2)
        self.call('knowledge.get',{'id':ident},loaded)
    def catalog_loaded(self,value,epoch):
        if self.epoch!=epoch:return
        self.status.setText('%d vendor PDF identities. Search to select an exact physical page.'%value['total'])
    def attach(self):
        folder=QFileDialog.getExistingDirectory(self,'Select mounted ROM root containing VOLUME.json')
        if not folder:return
        try:expected=records.sha(records.inside(folder,'VOLUME.json'))
        except (OSError,ValueError):self.status.setText('Choose the mounted or extracted ROM root containing VOLUME.json.');return
        self.launch('knowledge.attach',{'path':folder,'manifest_sha256':expected})
    def baseline(self):
        path,_=QFileDialog.getOpenFileName(self,'Inspect the preserved locked user archive','','ZIP (*.zip)')
        if path:self.launch('knowledge.baseline.inspect',{'path':path,'archive_sha256':records.sha(path)})
    def launch(self,operation,args):
        self.epoch+=1;epoch=self.epoch;self.clear_page()
        def submitted(job):
            self.pending=job['id'];self.job_epoch=epoch;self.timer.start();self.status.setText('Source job '+job['id'][:12]+' · '+job['state'])
        self.call(operation,args,submitted)
    def poll(self):
        if not self.pending:return
        ident=self.pending
        def loaded(job):
            if self.pending!=ident:return
            self.status.setText(job['tool']+' · '+job['state'])
            if job['state'] in ('Completed','Failed','Cancelled','Interrupted'):
                self.timer.stop();self.pending=None
                if job['state']=='Completed':
                    if job['tool']=='knowledge.page':
                        epoch=self.job_epoch
                        if epoch==self.epoch:self.call('knowledge.page.result',{'job':job['id']},lambda value:self.show_page(value) if epoch==self.epoch else None)
                    else:self.refresh()
                else:self.clear_page()
        self.call('jobs.get',{'id':ident},loaded)
    def cancel(self):
        if self.pending:self.call('jobs.cancel',{'id':self.pending},lambda _:self.clear_page())
    def search(self):
        if not self.connection or self.connection['kind']!='ROM':return
        self.epoch+=1;epoch=self.epoch;self.hits.clear();self.excerpt.clear();self.clear_page()
        def loaded(value):
            if self.epoch!=epoch:return
            for row in value['hits']:
                item=QTreeWidgetItem([row['record_id'],str(row['page_index']+1),row['state']]);item.setData(0,Qt.UserRole,row);self.hits.addTopLevelItem(item)
            self.status.setText('%d archive matches. Reopen an original to check its current bytes.'%len(value['hits']))
        self.call('knowledge.search',{'id':self.connection['id'],'query':self.query.text(),'limit':30},loaded)
    def selected(self):
        item=self.hits.currentItem()
        self.clear_page()
        if item:
            row=item.data(0,Qt.UserRole);self.excerpt.setPlainText(row.get('excerpt') or 'Original unavailable; cached excerpt withheld.')
    def read_page(self):
        item=self.hits.currentItem()
        if not item or not self.connection:return
        row=item.data(0,Qt.UserRole)
        self.launch('knowledge.page',{'id':self.connection['id'],'record_id':row['record_id'],'page_index':row['page_index'],'render':True})
    def show_page(self,value):
        self.clear_page()
        if value.get('state')!='ORIGINAL_PAGE_REEXTRACTED':self.page_note.setText('Original unavailable or source changed.');return
        self.page_note.setText(value['record_id']+' · physical page '+str(value['page_index']+1)+' · original reextracted')
        self.page_text.setPlainText(value['text']);self.technical.setPlainText(json.dumps({k:v for k,v in value.items() if k not in ('text','segments')},ensure_ascii=False,indent=2))
        if value.get('image'):self.image.setPixmap(QPixmap(str(self.host.root/value['image'])).scaledToWidth(650,Qt.SmoothTransformation))
        self.pages.setCurrentIndex(1)
    def select_baseline(self):
        if self.connection and self.connection['kind']=='BASELINE':
            self.call('knowledge.baseline.select',{'id':self.connection['id'],'reason':'Owner selected this verified snapshot as the V1 reference baseline; engineering acceptance remains separate.'},lambda _:self.refresh())
    def revoke(self):
        if self.connection:self.call('knowledge.revoke',{'id':self.connection['id'],'reason':'Owner revoked this source connection.'},lambda _:self.refresh())
    def shutdown_engineering(self):self.timer.stop();self.map_page.shutdown_engineering();self.packet_page.shutdown_engineering();self.investigation_page.shutdown_engineering();super().shutdown_engineering()
