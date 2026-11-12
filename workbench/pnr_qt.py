"""Native placement, internal-clock timing and held bitstream evidence."""
import json
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QComboBox,
    QTreeWidget,QTreeWidgetItem,QPlainTextEdit,QTabWidget,QHeaderView,QApplication)
from . import pnr_tools as native,record_io as io
from .engineering_kernel import operator
from .project_context import refusal


class ImplementationTab(QWidget):
    def __init__(self,host):
        super().__init__();self.host=host;self.kernel=host.ledger_bridge.kernel;self.principal=operator()
        self.job_id=None;self.job_state=None;self.result=None
        box=QVBoxLayout(self);box.addWidget(QLabel('nextpnr + Project Trellis · FPGA implementation'))
        self.tools=QLabel();self.tools.setWordWrap(True);box.addWidget(self.tools)
        self.profile=QComboBox();self.profile.setStyleSheet('QComboBox { min-width:0px; }')
        for key,spec in native.PROFILES.items():self.profile.addItem(spec['title'],key)
        box.addWidget(self.profile)
        row=QHBoxLayout();self.route=QPushButton('Route');self.pack=QPushButton('Pack held');self.stop_button=QPushButton('Stop job')
        self.route.clicked.connect(lambda:self.start('nextpnr.'+self.profile.currentData()))
        self.pack.clicked.connect(lambda:self.start('trellis.pack_'+self.profile.currentData()));self.stop_button.clicked.connect(self.stop)
        for button in (self.route,self.pack,self.stop_button):row.addWidget(button)
        for title,callback in (('Qualify routing',lambda:self.start('nextpnr.qualify')),('Qualify Trellis',lambda:self.start('trellis.qualify')),
                               ('Jobs / evidence',host.show_engineering),('Refresh',self.refresh)):
            button=QPushButton(title);button.clicked.connect(callback);row.addWidget(button)
        from .command_rows import fold
        fold(row,keep=('Route','Pack held','Stop job'));box.addLayout(row)
        self.status=QLabel('Run synthesis for the selected profile, then Route.');self.status.setWordWrap(True);box.addWidget(self.status)
        row=QHBoxLayout();row.addWidget(QLabel('Recorded run'));self.runs=QComboBox();self.runs.setStyleSheet('QComboBox { min-width:0px; }')
        row.addWidget(self.runs,1);self.runs.activated.connect(lambda index:self.watch_job(self.kernel.record('jobs',self.runs.itemData(index))));box.addLayout(row)
        self.pages=QTabWidget();box.addWidget(self.pages,1)
        def table(labels):
            widget=QTreeWidget();widget.setRootIsDecorated(False);widget.setHeaderLabels(labels)
            widget.header().setSectionResizeMode(0,QHeaderView.Stretch);return widget
        self.clocks=table(['Native clock','Target MHz','Achieved MHz','Result']);self.pages.addTab(self.clocks,'Clocks')
        self.resources=table(['Native resource','Used','Available','Used %']);self.pages.addTab(self.resources,'Resources')
        self.pins=table(['Top IO','Constrained ball']);self.pages.addTab(self.pins,'Pins')
        self.logs=QPlainTextEdit();self.logs.setReadOnly(True);self.pages.addTab(self.logs,'Native log')
        self.scope=QPlainTextEdit();self.scope.setReadOnly(True);self.pages.addTab(self.scope,'Sources / scope')
        page=QWidget();layout=QVBoxLayout(page);layout.setContentsMargins(0,0,0,0)
        row=QHBoxLayout();self.file=QComboBox();self.file.setStyleSheet('QComboBox { min-width:0px; }');row.addWidget(self.file,1)
        self.copy=QPushButton('Copy path');self.copy.clicked.connect(self.copy_path);row.addWidget(self.copy);layout.addLayout(row)
        self.preview=QPlainTextEdit();self.preview.setReadOnly(True);layout.addWidget(self.preview,1);self.pages.addTab(page,'Native files')
        self.file.currentIndexChanged.connect(self.select_file)
        self.note=QLabel('One seed, speed 6. External IO/CDC and board timing remain unqualified. Physical release and programming HOLD.')
        self.note.setWordWrap(True);box.addWidget(self.note)
        self.timer=QTimer(self);self.timer.setInterval(500);self.timer.timeout.connect(self.poll);self.timer.start()
        host.master_stop_controller.completed.connect(lambda result:self.poll());self.refresh()

    def title(self):return 'FPGA · route / pack'

    def set_running(self,running):
        tools=native.discover();self.route.setEnabled(not running and tools['nextpnr']=='DETECTED')
        self.pack.setEnabled(not running and tools['trellis']=='DETECTED');self.stop_button.setEnabled(running)
        self.profile.setEnabled(not running);self.runs.setEnabled(not running)

    def refresh(self):
        tools=native.discover();self.tools.setText('nextpnr: '+tools['nextpnr']+' · Trellis: '+tools['trellis']+' · capability fixtures repeat each job')
        jobs=[j for j in self.kernel.listing('jobs') if j['tool'].startswith(('nextpnr.','trellis.'))]
        current=self.runs.currentData();self.runs.clear()
        for job in sorted(jobs,key=lambda j:j['created'],reverse=True):self.runs.addItem(job['tool']+' · '+job['state']+' · '+job['id'][:8],job['id'])
        index=self.runs.findData(current or self.job_id)
        if index>=0:self.runs.setCurrentIndex(index)
        active=[j for j in jobs if j['state'] in ('Queued','Running')]
        if active:self.watch_job(max(active,key=lambda j:j['created']));return
        self.set_running(False)
        if jobs and not self.result:self.watch_job(max(jobs,key=lambda j:j['created']))

    def start(self,tool):
        response=self.kernel.dispatch('jobs.submit',{'tool':tool,'timeout':600},self.principal)
        if response['ok'] and refusal(response['result']):self.status.setText(refusal(response['result']))
        elif response['ok']:self.watch_job(response['result'])
        else:self.status.setText(response['error']['message'])

    def watch_job(self,job):
        self.job_id=job['id'];self.job_state=None;self.result=None;self.timer.start()
        for widget in (self.clocks,self.resources,self.pins,self.logs,self.scope,self.file,self.preview):widget.clear()
        key=job['tool'].split('.')[1].removeprefix('pack_');index=self.profile.findData(key)
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
                result=self.kernel.dispatch(job['tool'].split('.')[0]+'.report',{'id':self.job_id},self.principal)
                if result['ok']:self.result=result['result'];self.display()
                else:self.status.setText(state+' · no intact implementation record: '+result['error']['message'])
            else:self.status.setText(state+' · no complete implementation verdict for this attempt.')
            index=self.runs.findData(self.job_id)
            if index<0:self.runs.insertItem(0,job['tool']+' · '+state+' · '+job['id'][:8],job['id']);index=0
            self.runs.setCurrentIndex(index)

    def display(self):
        data=self.result;route=data.get('route',data.get('route_summary',{}));profile=data.get('profile',{})
        label='PACKAGE PROXY · physical target TQFP144 unqualified' if profile.get('proxy') else '45F / CABGA381 source profile'
        self.status.setText(data['status']+' · '+label+'\nInputs '+data['source_currentness']+' · STATIC_CHECK · programming HOLD')
        for name,row in sorted(route.get('clocks',{}).items()):self.clocks.addTopLevelItem(QTreeWidgetItem([name,f"{row['constraint']:.3f}",f"{row['achieved']:.3f}",'MET' if row['met'] else 'MISSED']))
        for name,row in sorted(route.get('utilization',{}).items(),key=lambda pair:(-pair[1]['used'],pair[0])):
            self.resources.addTopLevelItem(QTreeWidgetItem([name,str(row['used']),str(row['available']),f"{100*row['used']/row['available']:.1f}" if row['available'] else '—']))
        for name,pin in sorted(route.get('io_locations',{}).items()):self.pins.addTopLevelItem(QTreeWidgetItem([name,pin]))
        packing=data.get('packing');self.note.setText(('HELD bitstream · '+str(packing['bytes'])+' bytes · decoded roundtrip verified. ' if packing else '')+
            ('CABGA256 package proxy only. ' if profile.get('proxy') else '')+'Reported internal clocks only; external IO/CDC and board timing unqualified. Programming HOLD.')
        prefix='build/'+data['family']+'/runs/'+data['id']+'/attempts/'+data['attempt']+'/'
        self.logs.clear();self.file.clear()
        for name in data['artifacts']:
            short=name.removeprefix(prefix)
            if short.startswith('native/'):
                if short.endswith(('nextpnr.log','stderr.txt')):
                    with io.project_path(self.host.root,name).open(errors='replace') as f:self.logs.appendPlainText(short+'\n'+f.read(100000))
                if not short.endswith(('mapped.json','corrupt.bit')):self.file.addItem(short,name)
        view={k:v for k,v in data.items() if k not in ('artifacts','route','route_summary','qualification')}
        view['limits']='Single seed 1 / speed 6; native internal clock fmax. No external IO delay or CDC sign-off. No physical hardware qualification. No programming operation exists here.'
        self.scope.setPlainText(json.dumps(view,indent=2,ensure_ascii=False));self.pages.setCurrentIndex(0 if route else 4)
        if not route:self.logs.setPlainText(data['reason'])
        if hasattr(self.host,'arc_inspector'):self.host.arc_inspector.refresh()

    def select_file(self,*_):
        name=self.file.currentData()
        if not name:self.preview.clear();return
        path=io.project_path(self.host.root,name)
        with path.open('rb') as f:raw=f.read(20000)
        text=raw[:256].hex(' ')+'\n[Binary preview limited to 256 bytes.]' if path.suffix=='.bit' else raw.decode(errors='replace')+'\n[Preview limited to 20,000 bytes.]'
        self.preview.setPlainText(name+'\n\n'+text)

    def copy_path(self):
        name=self.file.currentData()
        if name:QApplication.clipboard().setText(str(io.project_path(self.host.root,name)))
