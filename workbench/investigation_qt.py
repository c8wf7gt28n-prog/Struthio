"""Compact investigation view with source links and explicit case limitations."""
import json
from PySide6.QtCore import Qt,QTimer
from PySide6.QtWidgets import QLabel,QHBoxLayout,QPushButton,QComboBox,QLineEdit,QTreeWidget,QTreeWidgetItem,QPlainTextEdit,QCheckBox,QSpinBox,QTabWidget,QFileDialog
from .register_tabs import ServiceTab

class InvestigationTab(ServiceTab):
    def __init__(self,host,source_tab):
        super().__init__(host);self.source_tab=source_tab;self.pending=None;self.current=None;self.selected_packet=None;self.method=None;self.epoch=0
        self.summary=QLabel('Select a checked packet and a bounded engineering case. Independent review remains separate.');self.summary.setWordWrap(True);self.outer.addWidget(self.summary)
        row=QHBoxLayout();self.packets=QComboBox();self.packets.setAccessibleName('Investigation source packet');self.packets.currentIndexChanged.connect(self.select_packet);row.addWidget(self.packets,1);b=QPushButton('Refresh');b.clicked.connect(self.refresh);row.addWidget(b);self.outer.addLayout(row)
        row=QHBoxLayout();self.cases=QComboBox();self.cases.addItem('PSRAM timing oracle','PSRAM_TCEM');self.cases.addItem('USB mux assumption','USB_MUX');self.cases.setAccessibleName('Engineering case profile');row.addWidget(self.cases,1)
        b=QPushButton('Run selected case');b.clicked.connect(self.run_case);row.addWidget(b);b=QPushButton('Cancel investigation');b.clicked.connect(self.cancel);row.addWidget(b);self.outer.addLayout(row)
        row=QHBoxLayout();self.clock=QSpinBox();self.clock.setRange(40,50);self.clock.setValue(40);self.clock.setSuffix(' MHz');self.clock.setAccessibleName('Case simulation clock MHz');self.length=QSpinBox();self.length.setRange(64,256);self.length.setValue(256);self.length.setSuffix(' bytes');self.length.setAccessibleName('Case burst length');self.address=QSpinBox();self.address.setRange(0,4096);self.address.setValue(900);self.address.setAccessibleName('Case starting address');row.addWidget(self.clock);row.addWidget(self.length);row.addWidget(self.address);self.outer.addLayout(row)
        self.profile_note=QLabel();self.profile_note.setWordWrap(True);self.outer.addWidget(self.profile_note);self.cases.currentIndexChanged.connect(self.profile_changed)
        self.jobs=QComboBox();self.jobs.setAccessibleName('Private engineering investigations');self.jobs.currentIndexChanged.connect(self.select_job);self.outer.addWidget(self.jobs)
        self.pages=QTabWidget();self.outer.addWidget(self.pages,1);self.results=QTreeWidget();self.results.setHeaderLabels(['Experiment / claim','Outcome','Scope']);self.results.setAccessibleName('Frozen engineering case outcomes');self.pages.addTab(self.results,'Results')
        self.sources=QTreeWidget();self.sources.setHeaderLabels(['Source','Locator','Identity']);self.sources.setAccessibleName('Investigation source locations');self.sources.itemSelectionChanged.connect(self.select_source);self.pages.addTab(self.sources,'Sources')
        self.gaps=QPlainTextEdit();self.gaps.setReadOnly(True);self.gaps.setAccessibleName('Engineering investigation gaps');self.pages.addTab(self.gaps,'Uncertainties')
        self.excerpt=QPlainTextEdit();self.excerpt.setReadOnly(True);self.excerpt.setMaximumHeight(110);self.excerpt.setAccessibleName('Checked investigation source excerpt');self.outer.addWidget(self.excerpt)
        row=QHBoxLayout();self.command=QLineEdit();self.command.setReadOnly(True);self.command.setAccessibleName('The same investigation read, as a line');row.addWidget(self.command,1);b=QPushButton('Save report…');b.clicked.connect(self.export);row.addWidget(b);self.outer.addLayout(row)
        self.toggle=QCheckBox('Technical investigation details');self.outer.addWidget(self.toggle);self.details=QPlainTextEdit();self.details.setReadOnly(True);self.details.setMaximumHeight(150);self.details.hide();self.toggle.toggled.connect(self.details.setVisible);self.outer.addWidget(self.details);self.outer.addWidget(self.status)
        self.timer=QTimer(self);self.timer.setInterval(900);self.timer.timeout.connect(self.poll);self.profile_changed();QTimer.singleShot(0,self.refresh)
    def profile_changed(self):
        psram=self.cases.currentData()=='PSRAM_TCEM'
        for widget in (self.clock,self.length,self.address):widget.setVisible(psram)
        self.profile_note.setText('Host RTL simulation with the preserved behavioral stand-in. Icarus Verilog must be installed separately.' if psram else 'Read-only native connectivity and loader callback analysis. Direct D213 control is a question, not an accepted fact.')
    def refresh(self,select=None):
        def methods(value):self.method=value['method'];self.status.setText('Method '+value['method'][:12]+' · Icarus '+value['icarus'])
        self.call('knowledge.investigation.methods',{},methods)
        def packets(value):
            old=self.packets.currentData();self.packets.blockSignals(True);self.packets.clear()
            for row in value['packets']:
                if row['state']=='CURRENT':self.packets.addItem(row['id'][:12],row['id'])
            self.packets.setCurrentIndex(max(0,self.packets.findData(old)));self.packets.blockSignals(False);self.select_packet()
        self.call('references.packets',{},packets)
        def jobs(value):
            old=select or self.jobs.currentData();self.jobs.blockSignals(True);self.jobs.clear()
            for row in reversed(value['jobs']):self.jobs.addItem(row['case']+' · '+row['id'][:10]+' · '+row['state'],row['id'])
            self.jobs.setCurrentIndex(max(0,self.jobs.findData(old)));self.jobs.blockSignals(False);self.select_job()
        self.call('knowledge.investigation.list',{},jobs)
    def select_packet(self,*_):
        self.selected_packet=None;ident=self.packets.currentData()
        if ident:
            def loaded(value):
                if self.packets.currentData()==ident and value['state']=='CURRENT':self.selected_packet=value
            self.call('references.packet',{'id':ident},loaded)
    def clear(self):
        self.current=None;self.results.clear();self.sources.clear();self.gaps.clear();self.excerpt.clear();self.details.clear();self.command.clear()
    def select_job(self,*_):
        self.epoch+=1;epoch=self.epoch;self.clear();ident=self.jobs.currentData()
        if ident:self.call('knowledge.investigation.result',{'job':ident},lambda value:self.show_result(value) if epoch==self.epoch else None)
    def show_result(self,value):
        self.clear();self.last_result=value
        if value['state']!='AVAILABLE':self.summary.setText('Investigation is stale or unavailable. Recheck its sources before use.');return
        self.current=value;report=value['report'];conclusion=report['conclusion'];self.summary.setText(conclusion['summary']);self.command.setText('investigation '+value['job']+' | inspect');self.details.setPlainText(json.dumps(report,ensure_ascii=False,indent=2));self.gaps.setPlainText('\n'.join(report['gaps']))
        self.results.addTopLevelItem(QTreeWidgetItem(['Current source assessment',conclusion['state'],'Reference scope; independent review open']))
        for item in report['experiments']:self.results.addTopLevelItem(QTreeWidgetItem([item['name'],item['oracle']['state'],'Expected '+item['expected']+' · max CE# '+item['oracle']['max_ce_low_ns']+' ns']))
        if 'direct_control_assumption' in conclusion:self.results.addTopLevelItem(QTreeWidgetItem(['Direct D213 membership assumption',conclusion['direct_control_assumption'],'Native net membership only']))
        for item in report['source_excerpts']:
            loc=item['locator'];row=QTreeWidgetItem([item['path'],str(loc['line_start'])+'–'+str(loc['line_end']),item['sha256'][:12]]);row.setData(0,Qt.UserRole,item['id']);self.sources.addTopLevelItem(row)
        for item in report['original_pages']:
            row=QTreeWidgetItem([item['record_id'],'Physical page '+str(item['page_index']+1),item['source_sha256'][:12]]);row.setData(0,Qt.UserRole,item['id']);self.sources.addTopLevelItem(row)
    def select_source(self):
        self.excerpt.clear();item=self.sources.currentItem()
        if item is None or not self.current:return
        source=item.data(0,Qt.UserRole);ident=self.current['job'];epoch=self.epoch
        def loaded(value):
            selected=self.sources.currentItem()
            if epoch!=self.epoch or selected is None or selected.data(0,Qt.UserRole)!=source:return
            if value['state']!='AVAILABLE':self.clear();return
            report=value['report'];text=next((s['text'] for s in report['source_excerpts']+report['original_pages'] if s['id']==source),'Source locator unavailable.');self.excerpt.setPlainText(text)
        self.call('knowledge.investigation.result',{'job':ident},loaded,lambda _:self.clear())
    def run_case(self):
        if self.pending:self.status.setText('Wait for the active investigation or cancel it.');return
        if self.selected_packet is None or self.method is None:self.status.setText('Compile a current evidence packet first.');return
        args={'packet':self.selected_packet['id'],'expected_context':self.selected_packet['context_digest'],'method':self.method,'case':self.cases.currentData()}
        if args['case']=='PSRAM_TCEM':args['variation']={'clock_hz':self.clock.value()*1000000,'length':self.length.value(),'address':self.address.value()}
        else:args['assumed_direct_controller']='U20'
        def submitted(job):self.pending=job['id'];self.timer.start();self.status.setText('Investigation · '+job['state'])
        self.call('knowledge.investigation.run',args,submitted)
    def poll(self):
        ident=self.pending
        if not ident:return
        def loaded(job):
            if ident!=self.pending:return
            self.status.setText('Investigation · '+job['state'])
            if job['state'] in ('Completed','Failed','Cancelled','Interrupted'):
                self.pending=None;self.timer.stop();self.refresh(select=ident)
        self.call('jobs.get',{'id':ident},loaded)
    def cancel(self):
        if self.pending:self.call('jobs.cancel',{'id':self.pending},lambda _:None)
    def export(self):
        if not self.current:return
        path,_=QFileDialog.getSaveFileName(self,'Save private investigation report','','JSON (*.json)')
        if path:self.call('knowledge.investigation.export',{'job':self.current['job'],'destination':path},lambda _:self.status.setText('Private report saved. Independent review remains open.'))
    def shutdown_engineering(self):self.timer.stop();super().shutdown_engineering()
