"""KiBot candidates inside the existing Ledger workspace and job lifecycle."""
from .text_prompts import writing_prompt
import json
from pathlib import Path
from PySide6.QtCore import Qt,QTimer
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,
    QComboBox,QTreeWidget,QTreeWidgetItem,QPlainTextEdit,QTabWidget,QHeaderView,QLineEdit)
from . import kibot_tools
from .engineering_kernel import operator
from .project_context import refusal


class KiBotTab(QWidget):
    def __init__(self,host):
        super().__init__();self.host=host;self.kernel=host.ledger_bridge.kernel;self.principal=operator()
        self.job_id=None;self.job_state=None;self.result=None
        box=QVBoxLayout(self);box.addWidget(QLabel('KiBot · BOM & fabrication candidates'))
        scope=QLabel('R10 · F133-B / D213ECV / ECP5 · protected source · FAB / ROUTE / programming HOLD')
        scope.setWordWrap(True);box.addWidget(scope)
        self.tool=QLabel();self.tool.setWordWrap(True);box.addWidget(self.tool)
        row=QHBoxLayout();self.bom_button=QPushButton('Generate BOM');self.fab_button=QPushButton('Fabrication candidate')
        self.stop_button=QPushButton('Stop job');self.stop_button.setEnabled(False)
        for button,callback in ((self.bom_button,lambda:self.start('kibot.bom')),
                                (self.fab_button,lambda:self.start('kibot.fabrication')),(self.stop_button,self.stop)):
            button.clicked.connect(callback);row.addWidget(button)
        for title,callback in (('Qualify outputs',lambda:self.start('kibot.qualify')),('KiCad checks',host.ledger_bridge.show_cad),
                               ('Jobs / evidence',host.show_engineering),('Refresh',self.refresh)):
            button=QPushButton(title);button.clicked.connect(callback);row.addWidget(button)
        from .command_rows import fold
        fold(row,keep=('Generate BOM','Fabrication candidate','Stop job'));box.addLayout(row)
        self.status=QLabel('No KiBot output selected.');self.status.setWordWrap(True);box.addWidget(self.status)
        history=QHBoxLayout();history.addWidget(QLabel('Recorded run'))
        self.runs=QComboBox();history.addWidget(self.runs,1);self.runs.activated.connect(self.choose_run);box.addLayout(history)
        self.pages=QTabWidget();box.addWidget(self.pages,1)
        bom=QWidget();layout=QVBoxLayout(bom);layout.setContentsMargins(0,0,0,0)
        self.search=QLineEdit();writing_prompt(self.search, 'Find reference, value, footprint or part number');layout.addWidget(self.search)
        self.components=QTreeWidget();self.components.setRootIsDecorated(False)
        self.components.setHeaderLabels(['Reference','Value','Footprint','MPN','Manufacturer'])
        for index,width in enumerate((100,120,235,190,140)):self.components.setColumnWidth(index,width)
        self.components.header().setSectionResizeMode(4,QHeaderView.Stretch);layout.addWidget(self.components,1)
        self.component=QPlainTextEdit();self.component.setReadOnly(True);self.component.setMaximumHeight(125);layout.addWidget(self.component)
        self.pages.addTab(bom,'BOM')
        files=QWidget();layout=QVBoxLayout(files);layout.setContentsMargins(0,0,0,0)
        self.files=QTreeWidget();self.files.setRootIsDecorated(False);self.files.setHeaderLabels(['Candidate file','Bytes','SHA-256'])
        self.files.setColumnWidth(0,320);self.files.setColumnWidth(1,80);self.files.header().setSectionResizeMode(2,QHeaderView.Stretch)
        layout.addWidget(self.files,2);self.preview=QPlainTextEdit();self.preview.setReadOnly(True);layout.addWidget(self.preview,1)
        self.pages.addTab(files,'Output files')
        self.logs=QPlainTextEdit();self.logs.setReadOnly(True);self.pages.addTab(self.logs,'Native warnings / logs')
        self.binding=QPlainTextEdit();self.binding.setReadOnly(True);self.pages.addTab(self.binding,'Inputs / compatibility / scope')
        self.note=QLabel('Each operation runs positive and negative fixtures. Generated files remain review candidates.')
        self.note.setWordWrap(True);box.addWidget(self.note)
        self.search.textChanged.connect(self.populate_bom);self.components.itemSelectionChanged.connect(self.selected_component)
        self.files.itemSelectionChanged.connect(self.selected_file)
        self.timer=QTimer(self);self.timer.setInterval(500);self.timer.timeout.connect(self.poll);self.timer.start()
        self.refresh()

    def title(self):return 'KiBot · outputs'

    def refresh(self):
        response=self.kernel.dispatch('kibot.inspect',{},self.principal)
        if not response['ok']:self.status.setText(response['error']['message']);return
        data=response['result'];tool=data['tool']
        self.tool.setText('KiBot detected · each job qualifies its own output operation' if tool['executable'] else tool['reason'])
        self.tool.setToolTip(tool.get('executable') or 'No KiBot executable found')
        jobs=[j for j in self.kernel.listing('jobs') if j['tool'].startswith('kibot.')]
        current=self.runs.currentData();self.runs.clear()
        for job in sorted(jobs,key=lambda j:j.get('created',0),reverse=True):
            self.runs.addItem(job['tool']+' · '+job['state']+' · '+job['id'][:8],job['id'])
        index=self.runs.findData(current or self.job_id)
        if index>=0:self.runs.setCurrentIndex(index)
        active=[j for j in jobs if j['state'] in ('Queued','Running')]
        if active:
            latest=max(active,key=lambda j:j['created'])
            if latest['id']!=self.job_id:self.watch_job(latest)
            return
        self.set_running(False)
        if data['latest'].get('schema')==kibot_tools.CONTRACT:
            self.result=data['latest'];self.display()
        else:self.status.setText(data['latest']['reason'])

    def set_running(self,running):
        available=bool(kibot_tools.discover()['executable'])
        self.bom_button.setEnabled(available and not running);self.fab_button.setEnabled(available and not running)
        self.stop_button.setEnabled(running);self.runs.setEnabled(not running)

    def choose_run(self,index):
        ident=self.runs.itemData(index)
        job=self.kernel.record('jobs',ident)
        self.watch_job(job)

    def start(self,tool):
        response=self.kernel.dispatch('jobs.submit',{'tool':tool,'timeout':240},self.principal)
        if not response['ok']:self.status.setText(response['error']['message']);return
        if refusal(response['result']):self.status.setText(refusal(response['result']));return
        self.watch_job(response['result'])

    def watch_job(self,job):
        self.job_id=job['id'];self.job_state=None;self.result=None
        self.components.clear();self.component.clear();self.files.clear();self.preview.clear();self.logs.clear();self.binding.clear()
        self.set_running(job['state'] in ('Queued','Running'));self.poll()

    def stop(self):
        if self.job_id:
            response=self.kernel.dispatch('jobs.cancel',{'id':self.job_id},self.principal)
            self.status.setText('Cancellation requested.' if response['ok'] else response['error']['message'])

    def poll(self):
        if self.host._closing or not self.job_id:return
        response=self.kernel.dispatch('jobs.get',{'id':self.job_id},self.principal)
        if not response['ok']:return
        job=response['result'];state=job['state']
        if state==self.job_state:return
        self.job_state=state;self.status.setText(state+' · '+job['tool']+' · '+job['id'][:8])
        if state in ('Completed','Failed','Cancelled','Paused'):
            self.set_running(False)
            if state in ('Completed','Failed'):
                result=self.kernel.dispatch('kibot.report',{'id':self.job_id},self.principal)
                if result['ok']:self.result=result['result'];self.display()
                else:self.status.setText(state+' · no intact output report: '+result['error']['message'])
            else:self.status.setText(state+' · no complete output candidate for this attempt.')
            index=self.runs.findData(self.job_id)
            if index<0:self.runs.insertItem(0,job['tool']+' · '+state+' · '+job['id'][:8],job['id']);index=0
            self.runs.setCurrentIndex(index)

    def display(self):
        result=self.result;native=result.get('native',{})
        version=result.get('tool',{}).get('version','unknown')
        self.tool.setText('Recorded engine: KiBot '+version+' · KiCad '+result.get('kicad',{}).get('version','unknown')+
                          ' · operation fixtures '+('passed' if result.get('qualification',{}).get('qualified') else 'incomplete'))
        detail=str(result.get('bom',{}).get('component_count',''))+' component rows' if result.get('bom') else '11 Gerbers · 1 drill · 1 job file' if result.get('fabrication_outputs') else result['reason']
        drc=result.get('drc',{})
        if drc:detail+=' · DRC '+str(drc['counts']['error'])+' errors / '+str(drc['counts']['warning'])+' warnings'
        self.status.setText(result['operation'].upper()+' · '+result['status']+' · '+detail+'\n'+
                            'Inputs '+result['source_currentness']+' · source '+('unchanged' if result.get('source_unchanged') else 'not verified')+
                            ' · '+str(native.get('warning_count',0))+' native '+('warning' if native.get('warning_count')==1 else 'warnings')+' · fabrication HOLD')
        self.files.clear()
        for path,row in result.get('artifacts',{}).items():
            if '/native/outputs/' not in path:continue
            item=QTreeWidgetItem([Path(path).name,str(row['bytes']),row['sha256']]);item.setData(0,Qt.UserRole,path)
            self.files.addTopLevelItem(item)
        if self.files.topLevelItemCount():self.files.setCurrentItem(self.files.topLevelItem(0))
        logs=[]
        for name,row in native.get('logs',{}).items():
            path=Path(row['path'])
            if path.is_file():logs.append(name+'\n'+path.read_text(errors='replace')[:120000])
        self.logs.setPlainText('\n\n'.join(logs) or 'No native output run. Read the scope record for the failure.')
        trimmed={k:v for k,v in result.items() if k!='bom'}
        if 'compatibility' in trimmed:
            trimmed={**trimmed,'compatibility':{k:({a:b for a,b in v.items() if a!='model'} if k in ('original','effective') else v) for k,v in trimmed['compatibility'].items()}}
        self.binding.setPlainText(json.dumps(trimmed,indent=2))
        if result.get('bom'):
            note='Complete source inventory, including mechanical and DNP entries. Native fields match; copied part data is unverified. Review the compatibility copy under Inputs. '
        elif result.get('fabrication_outputs'):
            note='Stored geometry and zone fills. Native DRC findings retained; CAM and manufacturing review required. '
        else:note=result['reason']+' '
        self.note.setText(note+'FAB / ROUTE / programming HOLD.')
        self.populate_bom();self.pages.setCurrentIndex(0 if result.get('bom') else 1 if result.get('fabrication_outputs') else 3)

    def populate_bom(self,*_):
        self.components.clear()
        query=self.search.text().casefold()
        for row in (self.result or {}).get('bom',{}).get('rows',[]):
            if query and query not in json.dumps(row).casefold():continue
            item=QTreeWidgetItem([row[k] for k in ('References','Value','Footprint Full','MPN','Manufacturer')])
            item.setData(0,Qt.UserRole,row)
            for i in range(5):item.setToolTip(i,item.text(i))
            self.components.addTopLevelItem(item)
        if self.components.topLevelItemCount():self.components.setCurrentItem(self.components.topLevelItem(0))

    def selected_component(self):
        item=self.components.currentItem();self.component.setPlainText(json.dumps(item.data(0,Qt.UserRole),indent=2) if item else '')

    def selected_file(self):
        item=self.files.currentItem()
        if not item:self.preview.clear();return
        path=self.host.root/item.data(0,Qt.UserRole)
        self.preview.setPlainText(path.read_text(errors='replace')[:16000])
