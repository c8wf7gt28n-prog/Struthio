"""Compact source-linked map view over the same Kernel reads as staC and CLI."""
from .text_prompts import writing_prompt
import json
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QLabel,QHBoxLayout,QPushButton,QComboBox,QLineEdit,QTreeWidget,QTreeWidgetItem,QPlainTextEdit,QCheckBox
from .register_tabs import ServiceTab

class EngineeringMapTab(ServiceTab):
    def __init__(self,host,source_tab):
        super().__init__(host);self.source_tab=source_tab;self.pending=None;self.current=None;self.epoch=0
        self.summary=QLabel('Choose a reviewed reference snapshot and ROM to build a source-linked map.');self.summary.setWordWrap(True);self.outer.addWidget(self.summary)
        row=QHBoxLayout();self.baselines=QComboBox();self.baselines.setAccessibleName('Map reference snapshot');self.roms=QComboBox();self.roms.setAccessibleName('Map ROM source');row.addWidget(self.baselines,1);row.addWidget(self.roms,1);self.outer.addLayout(row)
        row=QHBoxLayout()
        for text,fn in [('Refresh maps',self.refresh),('Build source map',self.build),('Cancel map job',self.cancel)]:
            b=QPushButton(text);b.clicked.connect(fn);row.addWidget(b)
        self.outer.addLayout(row);self.maps=QComboBox();self.maps.setAccessibleName('Private engineering map');self.maps.currentIndexChanged.connect(self.select_map);self.outer.addWidget(self.maps)
        row=QHBoxLayout();self.query=QLineEdit('U45');self.query.setAccessibleName('Map part or net');row.addWidget(self.query,1)
        for text,fn in [('Part',self.part),('Net',self.net),('Evidence',self.evidence)]:
            b=QPushButton(text);b.clicked.connect(fn);row.addWidget(b)
        self.outer.addLayout(row);row=QHBoxLayout();self.start=QLineEdit('U23');self.end=QLineEdit('J10');self.start.setAccessibleName('Trace start');self.end.setAccessibleName('Trace end');row.addWidget(self.start);row.addWidget(self.end);b=QPushButton('Trace native path');b.clicked.connect(self.trace);row.addWidget(b);self.outer.addLayout(row)
        self.net_prefix=QLineEdit();writing_prompt(self.net_prefix, 'Optional trace net prefix, for example PSRAM_SCLK');self.net_prefix.setAccessibleName('Trace net prefix');self.outer.addWidget(self.net_prefix)
        self.rows=QTreeWidget();self.rows.setHeaderLabels(['Relationship','Identity / locator','State']);self.rows.setAccessibleName('Source-linked engineering relationships');self.outer.addWidget(self.rows,1)
        self.command=QLineEdit();self.command.setReadOnly(True);self.command.setAccessibleName('The same read, as a line');self.outer.addWidget(self.command)
        self.details_toggle=QCheckBox('Technical map details');self.outer.addWidget(self.details_toggle);self.details=QPlainTextEdit();self.details.setReadOnly(True);self.details.setMaximumHeight(160);self.details.hide();self.details_toggle.toggled.connect(self.details.setVisible);self.outer.addWidget(self.details)
        self.outer.addWidget(self.status);self.timer=QTimer(self);self.timer.setInterval(600);self.timer.timeout.connect(self.poll);QTimer.singleShot(0,self.refresh)
    def refresh(self):
        def sources(value):
            oldb=self.baselines.currentData();oldr=self.roms.currentData();self.baselines.clear();self.roms.clear()
            for row in value['sources']:
                if row['state']=='OWNER_SELECTED_REFERENCE_BASELINE':self.baselines.addItem(row['title'],row['id'])
                elif row['kind']=='ROM' and row['state']!='UNAVAILABLE_OR_STALE':self.roms.addItem(row['title'],row['id'])
            for combo,old in ((self.baselines,oldb),(self.roms,oldr)):
                if combo.findData(old)>=0:combo.setCurrentIndex(combo.findData(old))
        self.call('knowledge.status',{},sources)
        def loaded(value):
            old=self.maps.currentData();self.maps.blockSignals(True);self.maps.clear()
            for row in value['maps']:self.maps.addItem(row['id'][:12]+' · '+row['availability'],row['id'])
            self.maps.setCurrentIndex(max(0,self.maps.findData(old)));self.maps.blockSignals(False);self.select_map()
        self.call('knowledge.map.list',{},loaded)
    def select_map(self,*_):
        self.epoch+=1;epoch=self.epoch;self.current=None;self.rows.clear();self.details.clear();self.command.clear();ident=self.maps.currentData()
        if not ident:return
        def loaded(value):
            if epoch!=self.epoch:return
            if value['state']!='REFERENCE_MAP_AVAILABLE':self.summary.setText('Map is stale or unavailable. Recheck its source connections.');return
            self.current=value;row=value['summary'];self.summary.setText('%d components · %d nets · reference identities only; engineering acceptance remains open.'%(row['components'],row['nets']));self.details.setPlainText(json.dumps(value,ensure_ascii=False,indent=2))
        self.call('knowledge.map.get',{'id':ident},loaded)
    def build(self):
        if not self.baselines.currentData() or not self.roms.currentData():self.status.setText('Connect ROM and explicitly select a V1 reference snapshot in Source connections first.');return
        def submitted(job):self.pending=job['id'];self.timer.start();self.status.setText('Source map · '+job['state'])
        self.call('knowledge.map.build',{'baseline':self.baselines.currentData(),'rom':self.roms.currentData()},submitted)
    def poll(self):
        ident=self.pending
        if not ident:return
        def loaded(job):
            if self.pending!=ident:return
            self.status.setText('Source map · '+job['state'])
            if job['state'] in ('Completed','Failed','Cancelled','Interrupted'):
                self.pending=None;self.timer.stop()
                if job['state']=='Completed':self.refresh()
        self.call('jobs.get',{'id':ident},loaded)
    def cancel(self):
        if self.pending:self.call('jobs.cancel',{'id':self.pending},lambda _:None)
    def read(self,op,args,surface):
        if not self.current:return
        self.epoch+=1;epoch=self.epoch;args={'id':self.current['id'],'expected_revision':self.current['revision'],**args};self.rows.clear();self.details.clear();self.command.setText('map '+args['id']+'@'+args['expected_revision']+' | '+surface)
        def loaded(value):
            if self.epoch!=epoch:return
            self.last_result=value;self.details.setPlainText(json.dumps(value,ensure_ascii=False,indent=2))
            if value['state']!='REFERENCE_MAP_AVAILABLE':self.summary.setText('Source or scope changed. Refresh before using this map.');return
            if 'part' in value:
                if hasattr(self.host,'select_object'):self.host.select_object({'kind':'component','target':args['component'],'map':args['id']},principal=self.principal,origin=self)
                c=value['part'];self.summary.setText(c['reference']+' · '+(c['mpn'] or c['value'])+' · fitted grade and document applicability need review.')
                for p in c['pins']:self.rows.addTopLevelItem(QTreeWidgetItem(['Pin '+p['pin']+' · '+p['function'],p['net'],p['state']]))
                for doc in value['documents']:self.rows.addTopLevelItem(QTreeWidgetItem(['Vendor original',doc['record_id'],doc['availability']+' · applicability unreviewed']))
                for src in c['software']:self.rows.addTopLevelItem(QTreeWidgetItem(['Software declaration',src['path'],src['state']]))
                for src in c['code_candidates']:self.rows.addTopLevelItem(QTreeWidgetItem(['Code mention',src['path']+':'+str(src['line']),'UNREVIEWED IMPLEMENTATION ASSOCIATION']))
                for gap in value['gaps']:self.rows.addTopLevelItem(QTreeWidgetItem(['Gap',gap,'UNRESOLVED']))
            elif 'endpoints' in value:
                if hasattr(self.host,'select_object'):self.host.select_object({'kind':'net','target':args['net'],'map':args['id']},principal=self.principal,origin=self)
                self.summary.setText(value['net']['name']+' · native net membership; signal direction is not inferred.')
                for p in value['endpoints']:self.rows.addTopLevelItem(QTreeWidgetItem([p['reference']+'.'+p['pin'],p['net'],p['state']]))
            elif 'trace' in value:
                self.summary.setText(value['trace']['state']+' · component graph path; electrical conduction is not established.')
                for edge in value['trace']['edges']:
                    for p in edge['endpoints']:self.rows.addTopLevelItem(QTreeWidgetItem([p['reference']+'.'+p['pin'],p['net'],p['state']]))
            else:
                self.summary.setText('Registered job and artifact checks; controller compliance still needs its reviewed oracle.')
                for e in value.get('evidence',[]):self.rows.addTopLevelItem(QTreeWidgetItem(['Kernel job',e['job'],e.get('record_witness',{}).get('state',e.get('state','UNKNOWN'))]))
            self.rows.resizeColumnToContents(0);self.rows.resizeColumnToContents(2)
        self.call(op,args,loaded)
    def part(self):self.read('knowledge.map.part',{'component':self.query.text().strip()},'part '+self.query.text().strip())
    def net(self):self.read('knowledge.map.net',{'net':self.query.text().strip()},'net '+self.query.text().strip())
    def trace(self):
        args={'start':self.start.text().strip(),'end':self.end.text().strip()};suffix='trace '+args['start']+' '+args['end'];prefix=self.net_prefix.text().strip()
        if prefix:args['net_prefix']=prefix;suffix+=' on '+prefix
        self.read('knowledge.map.trace',args,suffix)
    def evidence(self):self.read('knowledge.map.evidence',{},'evidence')
    def shutdown_engineering(self):self.timer.stop();super().shutdown_engineering()
