"""Native KiCad findings in the existing Ledger workspace."""
from .text_prompts import writing_prompt
import json
from PySide6.QtCore import Qt,QTimer
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QComboBox,
    QLineEdit,QTreeWidget,QTreeWidgetItem,QPlainTextEdit,QTabWidget,QHeaderView)
from . import kicad_tools
from .engineering_kernel import operator
from .project_context import refusal


class KiCadTab(QWidget):
    def __init__(self,host):
        super().__init__();self.host=host;self.kernel=host.ledger_bridge.kernel;self.principal=operator()
        self.job_id=None;self.job_state=None;self.result=None
        box=QVBoxLayout(self)
        box.addWidget(QLabel('KiCad · native board checks'))
        scope=QLabel('R10 source · protected snapshot · source and native reports bound by hashes · physical gates HOLD')
        scope.setWordWrap(True);box.addWidget(scope)
        self.tool=QLabel();self.tool.setWordWrap(True);box.addWidget(self.tool)
        row=QHBoxLayout()
        self.run_button=QPushButton('Run native DRC');self.qualify_button=QPushButton('Qualify DRC')
        self.stop_button=QPushButton('Stop job');self.stop_button.setEnabled(False)
        for button,callback in ((self.run_button,lambda:self.start('cad.drc')),
                                (self.qualify_button,lambda:self.start('cad.qualify')),
                                (self.stop_button,self.stop)):
            button.clicked.connect(callback);row.addWidget(button)
        for label,callback in (('Native board',host.show_native_board),('Jobs / evidence',host.show_engineering),('Refresh',self.refresh)):
            button=QPushButton(label);button.clicked.connect(callback);row.addWidget(button)
        from .command_rows import fold
        fold(row,keep=('Run native DRC','Stop job','Jobs / evidence'));box.addLayout(row)
        self.status=QLabel('No native check selected.');self.status.setWordWrap(True);box.addWidget(self.status)
        filters=QHBoxLayout();self.severity=QComboBox();self.severity.addItems(['All severities','error','warning','exclusion'])
        filters.addWidget(self.severity);self.search=QLineEdit();writing_prompt(self.search, 'Filter native findings');filters.addWidget(self.search,1)
        box.addLayout(filters)
        self.pages=QTabWidget();box.addWidget(self.pages,1)
        findings=QWidget();layout=QVBoxLayout(findings);layout.setContentsMargins(0,0,0,0)
        self.findings=QTreeWidget();self.findings.setRootIsDecorated(False)
        self.findings.setHeaderLabels(['Severity','Native type','Finding']);self.findings.setColumnWidth(0,95);self.findings.setColumnWidth(1,215)
        self.findings.header().setSectionResizeMode(2,QHeaderView.Stretch);layout.addWidget(self.findings,1)
        self.detail=QPlainTextEdit();self.detail.setReadOnly(True);self.detail.setMaximumHeight(130);layout.addWidget(self.detail)
        self.pages.addTab(findings,'Findings')
        self.native=QPlainTextEdit();self.native.setReadOnly(True);self.pages.addTab(self.native,'Original native JSON')
        self.binding=QPlainTextEdit();self.binding.setReadOnly(True);self.pages.addTab(self.binding,'Inputs / rules / scope')
        self.note=QLabel();self.note.setWordWrap(True);box.addWidget(self.note)
        self.findings.itemSelectionChanged.connect(self.selected)
        self.severity.currentTextChanged.connect(self.populate);self.search.textChanged.connect(self.populate)
        self.timer=QTimer(self);self.timer.setInterval(500);self.timer.timeout.connect(self.poll);self.timer.start()
        self.refresh()

    def title(self):return 'KiCad · native checks'

    def refresh(self):
        response=self.kernel.dispatch('cad.inspect',{},self.principal)
        if not response['ok']:
            self.status.setText(response['error']['message']);return
        data=response['result']
        if data.get('status')=='PROJECT_NOT_ATTACHED':
            self.status.setText(data['reason']);return
        tool=data['tool'];qualification=data['qualification']
        self.tool.setText(('KiCad '+qualification['version']+' · cached DRC capability; rechecked at run' if qualification
                           else 'KiCad detected · DRC qualification required' if tool['executable'] else tool['reason']))
        self.tool.setToolTip(tool.get('executable') or 'No supported executable found')
        active_jobs=[j for j in self.kernel.listing('jobs') if j['tool'].startswith('cad.') and j['state'] in ('Queued','Running')]
        if active_jobs:
            latest=max(active_jobs,key=lambda j:j.get('created',0))
            if latest['id']!=self.job_id:self.watch_job(latest)
        active=self.job_id is not None and self.job_state not in ('Completed','Failed','Cancelled','Paused')
        self.run_button.setEnabled(bool(tool['executable']) and not active);self.qualify_button.setEnabled(bool(tool['executable']) and not active)
        if active:return
        if data['latest'].get('schema')==kicad_tools.CONTRACT:
            self.result=data['latest'];self.display()
        else:self.status.setText('Native inputs ready: '+str(len(data['inputs']))+' captured project files. '+data['latest']['reason'])

    def start(self,tool):
        response=self.kernel.dispatch('jobs.submit',{'tool':tool,'timeout':180},self.principal)
        if not response['ok']:self.status.setText(response['error']['message']);return
        if refusal(response['result']):self.status.setText(refusal(response['result']));return
        self.watch_job(response['result'])

    def watch_job(self,job):
        self.job_id=job['id'];self.job_state=None
        self.result=None;self.findings.clear();self.native.clear();self.binding.clear()
        self.run_button.setEnabled(False);self.qualify_button.setEnabled(False);self.stop_button.setEnabled(True)
        self.status.setText(job['state']+' '+job['tool']+' · '+self.job_id[:8]);self.poll()

    def stop(self):
        if self.job_id:
            result=self.kernel.dispatch('jobs.cancel',{'id':self.job_id},self.principal)
            self.status.setText('Cancellation requested.' if result['ok'] else result['error']['message'])

    def poll(self):
        if self.host._closing or not self.job_id:return
        response=self.kernel.dispatch('jobs.get',{'id':self.job_id},self.principal)
        if not response['ok']:return
        job=response['result'];state=job['state']
        if state==self.job_state:return
        self.job_state=state;self.status.setText(state+' · '+job['tool']+' · '+job['id'][:8])
        if state in ('Completed','Failed','Cancelled','Paused'):
            self.stop_button.setEnabled(False)
            if state=='Completed':
                report=self.kernel.dispatch('cad.report',{'id':self.job_id},self.principal)
                if report['ok']:self.result=report['result'];self.display()
                else:self.status.setText('Job finished; report unavailable: '+report['error']['message'])
            else:self.status.setText(state+' · no complete native board verdict for this attempt. '+job.get('error',''))
            tool=kicad_tools.discover();self.run_button.setEnabled(bool(tool['executable']));self.qualify_button.setEnabled(bool(tool['executable']))

    def display(self):
        result=self.result;native=result.get('native',{})
        if result.get('qualification',{}).get('qualified'):
            self.tool.setText('Report engine: KiCad '+result['tool']['version']+' · DRC capability qualified for this recorded run')
        if native:
            counts=native['counts'];connection_count=sum(r['group']=='unconnected_items' for r in native['findings'])
            self.status.setText('DRC '+result['status']+' · '+str(counts['error'])+' errors · '+str(counts['warning'])+' warnings · '+
                                str(counts['exclusion'])+' exclusions\n'+str(connection_count)+' unconnected items · inputs '+result['source_currentness']+
                                ' · original source '+('unchanged' if result['source_unchanged'] else 'CHANGED'))
            path=self.host.root/native['native_report']
            self.native.setPlainText(path.read_text())
            ignored=len(native.get('ignored_checks',[]));missing=len(result.get('external_inputs',{}).get('missing_references',[]))
            self.note.setText('Native exit '+str(native['exit_status'])+' · '+str(ignored)+' ignored checks retained from the native rules · '+
                              str(missing)+' unresolved external footprint references. Stored fills; ERC and schematic parity are separate checks.')
        else:
            self.status.setText(result['status']+' · '+result['reason']);self.native.clear();self.note.setText(result['reason'])
        self.binding.setPlainText(json.dumps({k:v for k,v in result.items() if k!='native'},indent=2))
        self.populate()

    def populate(self,*_):
        self.findings.clear()
        if not self.result:return
        severity=self.severity.currentText();query=self.search.text().casefold()
        rows=self.result.get('native',{}).get('findings',[])
        visible=[r for r in rows if (severity=='All severities' or r.get('severity')==severity)
                 and (not query or query in json.dumps(r).casefold())]
        for row in visible[:2000]:
            item=QTreeWidgetItem([row.get('severity','other'),row.get('type',row['group']),row['description']])
            item.setData(0,Qt.UserRole,row);item.setToolTip(2,row['description']);self.findings.addTopLevelItem(item)
        if len(visible)>2000:self.note.setText(self.note.text()+' Displaying the first 2,000 matching findings; the original JSON contains all findings.')
        if self.findings.topLevelItemCount():self.findings.setCurrentItem(self.findings.topLevelItem(0))

    def selected(self):
        item=self.findings.currentItem()
        self.detail.setPlainText(json.dumps(item.data(0,Qt.UserRole),indent=2) if item else '')
