"""Mapped FPGA resources and native Yosys evidence in the existing workspace."""
import json
from pathlib import Path
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QComboBox,
    QTreeWidget,QTreeWidgetItem,QPlainTextEdit,QTabWidget,QHeaderView,QApplication)
from . import yosys_tools, record_io as io
from .engineering_kernel import operator
from .project_context import refusal

MEANINGS={'LUT4':'Four-input lookup table','TRELLIS_FF':'Flip-flop','DP16KD':'Embedded block RAM primitive',
          'MULT18X18D':'DSP multiplier','CCU2C':'Carry-chain arithmetic','EHXPLLL':'PLL',
          'PFUMX':'Logic multiplexer','L6MUX21':'Logic multiplexer','TRELLIS_DPR16X4':'Distributed RAM',
          'IDDRX1F':'DDR input','ODDRX1F':'DDR output','$_TBUF_':'Stock tri-state IO marker'}


class YosysTab(QWidget):
    def __init__(self,host):
        super().__init__();self.host=host;self.kernel=host.ledger_bridge.kernel;self.principal=operator()
        self.job_id=None;self.job_state=None;self.result=None
        box=QVBoxLayout(self);box.addWidget(QLabel('Yosys · FPGA synthesis'))
        self.tool=QLabel();self.tool.setWordWrap(True);box.addWidget(self.tool)
        row=QHBoxLayout();self.profile=QComboBox();self.profile.setStyleSheet('QComboBox { min-width:0px; }')
        self.profile.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon);self.profile.setMinimumContentsLength(1)
        for key,spec in yosys_tools.PROFILES.items():self.profile.addItem(spec['title'],key)
        row.addWidget(self.profile,1);self.run_button=QPushButton('Synthesize');self.stop_button=QPushButton('Stop job')
        self.stop_button.setEnabled(False);self.run_button.clicked.connect(lambda:self.start('yosys.'+self.profile.currentData()))
        self.stop_button.clicked.connect(self.stop);row.addWidget(self.run_button);row.addWidget(self.stop_button)
        for title,callback in (('Qualify Yosys',lambda:self.start('yosys.qualify')),('Jobs / evidence',host.show_engineering),('Refresh',self.refresh)):
            button=QPushButton(title);button.clicked.connect(callback);row.addWidget(button)
        from .command_rows import fold
        fold(row,keep=('Synthesize','Stop job'));box.addLayout(row)
        self.status=QLabel('No synthesis run selected.');self.status.setWordWrap(True);box.addWidget(self.status)
        row=QHBoxLayout();row.addWidget(QLabel('Recorded run'));self.runs=QComboBox();row.addWidget(self.runs,1)
        self.runs.activated.connect(self.choose_run);box.addLayout(row)
        self.pages=QTabWidget();box.addWidget(self.pages,1)
        self.cells=QTreeWidget();self.cells.setRootIsDecorated(False);self.cells.setHeaderLabels(['Native cell type','Count','Meaning'])
        self.cells.setColumnWidth(0,220);self.cells.setColumnWidth(1,100);self.cells.header().setSectionResizeMode(2,QHeaderView.Stretch)
        self.pages.addTab(self.cells,'Resources')
        self.ports=QTreeWidget();self.ports.setRootIsDecorated(False);self.ports.setHeaderLabels(['Top port','Direction','Bits'])
        self.ports.header().setSectionResizeMode(0,QHeaderView.Stretch);self.ports.setColumnWidth(1,150);self.ports.setColumnWidth(2,80)
        self.pages.addTab(self.ports,'Ports')
        self.logs=QPlainTextEdit();self.logs.setReadOnly(True);self.pages.addTab(self.logs,'Warnings / log')
        self.scope=QPlainTextEdit();self.scope.setReadOnly(True);self.pages.addTab(self.scope,'Sources / scope')
        page=QWidget();layout=QVBoxLayout(page);layout.setContentsMargins(0,0,0,0)
        row=QHBoxLayout();self.file=QComboBox();self.file.setStyleSheet('QComboBox { min-width:0px; }')
        self.file.currentIndexChanged.connect(self.select_file);row.addWidget(self.file,1)
        self.copy=QPushButton('Copy netlist path');self.copy.clicked.connect(self.copy_netlist);row.addWidget(self.copy);layout.addLayout(row)
        self.preview=QPlainTextEdit();self.preview.setReadOnly(True);layout.addWidget(self.preview,1);self.pages.addTab(page,'Native files')
        self.note=QLabel('Current R10 ECP5 profiles. Synthesis counts do not establish physical fit, routing or timing; programming HOLD.')
        self.note.setWordWrap(True);box.addWidget(self.note)
        self.timer=QTimer(self);self.timer.setInterval(500);self.timer.timeout.connect(self.poll);self.timer.start();self.refresh()
        host.master_stop_controller.completed.connect(lambda report:self.poll())

    def title(self):return 'Yosys · synthesis'

    def set_running(self,running):
        self.run_button.setEnabled(yosys_tools.discover()['state']=='DETECTED' and not running)
        self.stop_button.setEnabled(running);self.profile.setEnabled(not running);self.runs.setEnabled(not running)

    def refresh(self):
        response=self.kernel.dispatch('yosys.inspect',{},self.principal)
        if not response['ok']:self.status.setText(response['error']['message']);return
        data=response['result'];tool=data['tool'];self.tool.setText('Native Yosys detected · ECP5 / ABC9 capability rechecked each job' if tool['state']=='DETECTED' else tool['reason'])
        self.tool.setToolTip(tool.get('executable') or 'Yosys is not installed')
        jobs=[j for j in self.kernel.listing('jobs') if j['tool'].startswith('yosys.')]
        current=self.runs.currentData();self.runs.clear()
        for job in sorted(jobs,key=lambda j:j.get('created',0),reverse=True):self.runs.addItem(job['tool']+' · '+job['state']+' · '+job['id'][:8],job['id'])
        index=self.runs.findData(current or self.job_id)
        if index>=0:self.runs.setCurrentIndex(index)
        active=[j for j in jobs if j['state'] in ('Queued','Running')]
        if active:
            latest=max(active,key=lambda j:j['created'])
            if latest['id']!=self.job_id:self.watch_job(latest)
            return
        self.set_running(False)
        if data['latest'].get('schema')==yosys_tools.CONTRACT:self.result=data['latest'];self.display()
        else:self.status.setText(data['latest']['reason'])

    def choose_run(self,index):self.watch_job(self.kernel.record('jobs',self.runs.itemData(index)))

    def start(self,tool):
        response=self.kernel.dispatch('jobs.submit',{'tool':tool,'timeout':300},self.principal)
        if not response['ok']:self.status.setText(response['error']['message']);return
        if refusal(response['result']):self.status.setText(refusal(response['result']));return
        self.watch_job(response['result'])

    def watch_job(self,job):
        self.job_id=job['id'];self.job_state=None;self.result=None
        self.timer.start()
        self.cells.clear();self.ports.clear();self.logs.clear();self.scope.clear();self.file.clear();self.preview.clear()
        index=self.profile.findData(job['tool'].removeprefix('yosys.'))
        if index>=0:self.profile.setCurrentIndex(index)
        self.set_running(job['state'] in ('Queued','Running'));self.poll()

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
            self.set_running(False)
            if state in ('Completed','Failed'):
                report=self.kernel.dispatch('yosys.report',{'id':self.job_id},self.principal)
                if report['ok']:self.result=report['result'];self.display()
                else:self.status.setText(state+' · no intact synthesis record: '+report['error']['message'])
            else:self.status.setText(state+' · no complete mapped candidate for this attempt.')
            index=self.runs.findData(self.job_id)
            if index<0:self.runs.insertItem(0,job['tool']+' · '+state+' · '+job['id'][:8],job['id']);index=0
            self.runs.setCurrentIndex(index)

    def native_path(self,name):
        return io.project_path(self.host.root,'build/yosys/runs/'+self.result['id']+'/attempts/'+self.result['attempt']+'/native/'+name)

    def display(self):
        result=self.result;synthesis=result.get('synthesis',{});index=self.profile.findData(result['operation'])
        if index>=0:self.profile.setCurrentIndex(index)
        self.tool.setText('Recorded engine: '+result.get('tool',{}).get('version','unknown')+' · '+
                          ('capability fixtures passed' if result.get('qualification',{}).get('qualified') else 'qualification incomplete'))
        detail=str(synthesis.get('cell_count',0))+' mapped cells · '+str(len(result.get('warnings',[])))+' native warnings' if synthesis else result['reason']
        self.status.setText(result['status']+' · '+detail+'\nInputs '+result['source_currentness']+' · source '+
                            ('unchanged' if result.get('source_unchanged') else 'not verified')+' · STATIC_CHECK · physical gates HOLD')
        self.cells.clear();self.ports.clear()
        for name,count in sorted(synthesis.get('cells_by_type',{}).items(),key=lambda pair:(-pair[1],pair[0])):
            item=QTreeWidgetItem([name,str(count),MEANINGS.get(name,'Native ECP5 primitive')]);item.setToolTip(0,name);self.cells.addTopLevelItem(item)
        for name,port in synthesis.get('ports',{}).items():self.ports.addTopLevelItem(QTreeWidgetItem([name,port['direction'],str(port['bits'])]))
        prefix='Native warnings\n'+'\n'.join(result.get('warnings',[]))+'\n\nOriginal log preview\n'
        try:
            with self.native_path('yosys.log').open(errors='replace') as f:prefix+=f.read(100000)
        except (ValueError,OSError):prefix+=result['reason']
        self.logs.setPlainText(prefix+'\n\n[The complete original log is retained in the run.]')
        view={'profile':result.get('profile'),'top_interface_preserved':synthesis.get('port_interface_preserved'),
              'scope':synthesis.get('scope'),'routing':result['routing'],'timing':result['timing'],
              'programming':result['programming'],'source_currentness':result['source_currentness'],
              'pin_constraints':'Captured as context; not applied by this synthesis step.',
              'defaults':'Unmodified memory-enabled top parameters; native SYNTHESIS / YOSYS defines; ABC9 mapping.',
              'inputs':result.get('inputs'),'library_scope':result.get('library_scope'),
              'tool':result.get('tool'),'qualification':result.get('qualification')}
        self.scope.setPlainText(json.dumps(view,indent=2,ensure_ascii=False))
        self.file.clear()
        for name in ('statistics.json','mapped.json','elaborated.json','synthesis.ys','yosys.log','stderr.txt'):
            try:path=self.native_path(name)
            except (ValueError,OSError):continue
            self.file.addItem(name,str(path))
        self.copy.setEnabled(bool(synthesis));self.select_file();self.pages.setCurrentIndex(0 if synthesis else 3)
        self.note.setText('Mapped resource counts and port interfaces are checked. Physical fit, pin assignment, routing, timing closure and programming remain unqualified.' if synthesis else result['reason']+' No project candidate or physical qualification is claimed.')
        if hasattr(self.host,'arc_inspector'):self.host.arc_inspector.refresh()

    def select_file(self,*_):
        name=self.file.currentData()
        if not name:self.preview.clear();return
        with Path(name).open(errors='replace') as f:preview=f.read(20000)
        self.preview.setPlainText(name+'\n\n'+preview+'\n\n[Preview limited to 20,000 characters; complete file retained.]')

    def copy_netlist(self):
        if self.result and self.result.get('synthesis'):
            QApplication.clipboard().setText(str(self.native_path('mapped.json')))
            self.host.statusBar().showMessage('Copied the mapped-netlist path.',5000)
