"""Short packet summaries, original locators and expandable technical detail."""
from .text_prompts import writing_prompt
import json
from PySide6.QtCore import Qt,QTimer
from PySide6.QtWidgets import (QLabel,QHBoxLayout,QPushButton,QComboBox,QLineEdit,QTreeWidget,QTreeWidgetItem,QPlainTextEdit,QCheckBox,QTabWidget,QWidget,QVBoxLayout,QFileDialog)
from .register_tabs import ServiceTab

class EvidenceCompilerTab(ServiceTab):
    def __init__(self,host,source_tab):
        super().__init__(host);self.source_tab=source_tab;self.pending=None;self.current=None;self.map_view=None;self.epoch=0
        self.summary=QLabel('Choose an engineering map and ask a bounded question. Sources and unresolved gaps stay attached.');self.summary.setWordWrap(True);self.outer.addWidget(self.summary)
        row=QHBoxLayout();self.maps=QComboBox();self.maps.setAccessibleName('Evidence packet engineering map');self.maps.currentIndexChanged.connect(self.select_map);row.addWidget(self.maps,1)
        b=QPushButton('Refresh');b.clicked.connect(self.refresh);row.addWidget(b);self.outer.addLayout(row)
        row=QHBoxLayout();self.component=QLineEdit('U45');self.component.setAccessibleName('Evidence packet component');self.component.setMaximumWidth(100);row.addWidget(self.component)
        self.lookup=QLineEdit('tCEM');self.lookup.setAccessibleName('Original page lookup term');writing_prompt(self.lookup, 'Optional original page lookup term');row.addWidget(self.lookup,1);self.outer.addLayout(row)
        self.question=QLineEdit('What evidence is available for the selected PSRAM timing limit?');self.question.setMaxLength(1200);self.question.setAccessibleName('Engineering packet question');self.outer.addWidget(self.question)
        row=QHBoxLayout()
        for text,fn in [('Compile evidence packet',self.compile),('Cancel compilation',self.cancel),('Save packet…',self.export)]:
            b=QPushButton(text);b.clicked.connect(fn);row.addWidget(b)
        self.outer.addLayout(row);self.packets=QComboBox();self.packets.setAccessibleName('Private engineering evidence packets');self.packets.currentIndexChanged.connect(self.select_packet);self.outer.addWidget(self.packets)
        self.pages=QTabWidget();self.outer.addWidget(self.pages,1)
        self.evidence=QTreeWidget();self.evidence.setHeaderLabels(['Evidence','Location','State']);self.evidence.setAccessibleName('Packet evidence and authority');self.pages.addTab(self.evidence,'Evidence')
        source=QWidget();box=QVBoxLayout(source);self.sources=QTreeWidget();self.sources.setHeaderLabels(['Source','Locator','Authority']);self.sources.setAccessibleName('Packet source locators');self.sources.itemSelectionChanged.connect(self.select_source);box.addWidget(self.sources,1)
        self.excerpt=QPlainTextEdit();self.excerpt.setReadOnly(True);self.excerpt.setAccessibleName('Packet source text');box.addWidget(self.excerpt,1)
        b=QPushButton('Open selected original PDF page');b.clicked.connect(self.original);box.addWidget(b);self.pages.addTab(source,'Sources')
        self.gaps=QPlainTextEdit();self.gaps.setReadOnly(True);self.gaps.setAccessibleName('Packet uncertainties and contradictions');self.pages.addTab(self.gaps,'Uncertainties')
        self.command=QLineEdit();self.command.setReadOnly(True);self.command.setAccessibleName('The same packet read, as a line');self.outer.addWidget(self.command)
        self.toggle=QCheckBox('Technical packet details');self.outer.addWidget(self.toggle);self.details=QPlainTextEdit();self.details.setReadOnly(True);self.details.setMaximumHeight(150);self.details.setAccessibleName('Canonical engineering packet details');self.details.hide();self.toggle.toggled.connect(self.details.setVisible);self.outer.addWidget(self.details)
        self.outer.addWidget(self.status);self.timer=QTimer(self);self.timer.setInterval(700);self.timer.timeout.connect(self.poll);QTimer.singleShot(0,self.refresh)
    def refresh(self,select=None):
        def maps(value):
            old=self.maps.currentData();self.maps.blockSignals(True);self.maps.clear()
            for row in value['maps']:
                if row['availability']=='SOURCE_IDENTITIES_AVAILABLE':self.maps.addItem(row['id'][:12],row['id'])
            self.maps.setCurrentIndex(max(0,self.maps.findData(old)));self.maps.blockSignals(False);self.select_map()
        self.call('knowledge.map.list',{},maps)
        def packets(value):
            old=select or self.packets.currentData();self.packets.blockSignals(True);self.packets.clear()
            for row in value['packets']:self.packets.addItem(row['id'][:12]+' · '+row['state'],row['id'])
            self.packets.setCurrentIndex(max(0,self.packets.findData(old)));self.packets.blockSignals(False);self.select_packet()
        self.call('references.packets',{},packets)
    def select_map(self,*_):
        self.map_view=None;ident=self.maps.currentData()
        if not ident:return
        def loaded(value):
            if self.maps.currentData()==ident and value.get('state')=='REFERENCE_MAP_AVAILABLE':self.map_view=value
        self.call('knowledge.map.get',{'id':ident},loaded)
    def clear_packet(self):
        self.current=None;self.evidence.clear();self.sources.clear();self.excerpt.clear();self.gaps.clear();self.details.clear();self.command.clear()
    def select_packet(self,*_):
        self.epoch+=1;epoch=self.epoch;self.clear_packet();ident=self.packets.currentData()
        if not ident:return
        self.call('references.packet',{'id':ident},lambda value:self.show_packet(value) if self.epoch==epoch else None)
    def show_packet(self,value):
        self.clear_packet();self.last_result=value
        if value.get('state')!='CURRENT':self.summary.setText('Packet is stale or unavailable. Recheck its sources and compile a new edition.');return
        self.current=value;ctx=value['context'];self.summary.setText('%s · %d sources · %d unresolved gaps.'%(ctx['scope']['component'],len(ctx['passages']),len(ctx['gaps'])))
        self.details.setPlainText(json.dumps(value,ensure_ascii=False,indent=2));self.command.setText('packet '+value['id']+' | inspect')
        self.evidence.addTopLevelItem(QTreeWidgetItem(['Native part',ctx['scope']['mpn'],'Identity linked; applicability needs review']))
        for item in ctx['evidence_refs']:self.evidence.addTopLevelItem(QTreeWidgetItem(['Kernel job',item['job'],item.get('record_witness',{}).get('state',item.get('state','UNKNOWN'))]))
        for fact in ctx['facts']:self.evidence.addTopLevelItem(QTreeWidgetItem(['Reviewed reference fact',fact['id'],fact['property']+' · reference scope']))
        self.evidence.addTopLevelItem(QTreeWidgetItem(['Engineering compliance','Reviewed controller oracle','Not established']))
        for p in ctx['passages']:
            loc=p['locator'];label='physical page '+str(loc['page_index']+1) if 'page_index' in loc else loc.get('path',loc.get('board_path',str(loc)))
            item=QTreeWidgetItem([p['name'],label,p['authority']]);item.setData(0,Qt.UserRole,p['id']);self.sources.addTopLevelItem(item)
        self.gaps.setPlainText('\n'.join(ctx['gaps'])+('\n\nConflicts:\n'+json.dumps(ctx['contradictions'],ensure_ascii=False,indent=2) if ctx['contradictions'] else ''))
    def select_source(self):
        self.excerpt.clear();item=self.sources.currentItem()
        if item is None or not self.current:return
        ident=self.current['id'];source=item.data(0,Qt.UserRole);epoch=self.epoch
        def loaded(value):
            selected=self.sources.currentItem()
            if self.epoch==epoch and selected is not None and selected.data(0,Qt.UserRole)==source:self.excerpt.setPlainText(value['source']['text'])
        self.call('references.packet.source',{'id':ident,'source':source},loaded,lambda _:self.clear_packet())
    def compile(self):
        if self.pending:self.status.setText('Wait for the current compilation or cancel it.');return
        if not self.map_view:self.status.setText('Build an engineering map from Source connections first.');return
        args={'map':self.map_view['id'],'expected_revision':self.map_view['revision'],'component':self.component.text().strip(),'question':self.question.text().strip()}
        if self.lookup.text().strip():args['lookup']=self.lookup.text().strip()
        def submitted(job):self.pending=job['id'];self.timer.start();self.status.setText('Evidence Compiler · '+job['state'])
        self.call('references.packet.compile',args,submitted)
    def poll(self):
        ident=self.pending
        if not ident:return
        def loaded(job):
            if ident!=self.pending:return
            self.status.setText('Evidence Compiler · '+job['state'])
            if job['state'] in ('Completed','Failed','Cancelled','Interrupted'):
                self.pending=None;self.timer.stop()
                if job['state']=='Completed':
                    self.call('evidence.read',{'id':job['evidence']},lambda result:self.refresh(select=result.get('diagnostics',{}).get('packet')))
        self.call('jobs.get',{'id':ident},loaded)
    def cancel(self):
        if self.pending:self.call('jobs.cancel',{'id':self.pending},lambda _:None)
    def export(self):
        if not self.current:return
        path,_=QFileDialog.getSaveFileName(self,'Save private evidence packet','','JSON (*.json)')
        if path:self.call('references.packet.export',{'id':self.current['id'],'destination':path},lambda _:self.status.setText('Private packet saved.'))
    def original(self):
        item=self.sources.currentItem()
        if item is None or not self.current:return
        ident=self.current['id'];source=item.data(0,Qt.UserRole);epoch=self.epoch
        def loaded(value):
            if epoch!=self.epoch or not self.current:return
            p=value['source'];loc=p['locator']
            if p['authority']=='VENDOR_ORIGINAL_APPLICABILITY_UNREVIEWED' and 'page_index' in loc:
                packet=self.current
                def mapped(value):
                    if epoch==self.epoch and value.get('state')=='REFERENCE_MAP_AVAILABLE':self.source_tab.launch('knowledge.page',{'id':value['summary']['rom'],'record_id':p['name'],'page_index':loc['page_index'],'render':True})
                self.call('knowledge.map.get',{'id':packet['context']['scope']['map'],'expected_revision':packet['context']['scope']['view_revision']},mapped)
            else:self.status.setText('This source is a native/code locator. Its checked excerpt is shown above.')
        self.call('references.packet.source',{'id':ident,'source':source},loaded,lambda _:self.clear_packet())
    def shutdown_engineering(self):self.timer.stop();super().shutdown_engineering()
