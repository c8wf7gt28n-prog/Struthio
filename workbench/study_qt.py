"""Study controls and trusted local input veto; work always uses Kernel jobs."""
from .text_prompts import writing_prompt
import json, time
from PySide6.QtCore import QObject,QEvent,QTimer
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QLineEdit,QPlainTextEdit,QComboBox,QTabWidget,QScrollArea,QFileDialog,QInputDialog)
from .register_tabs import ServiceTab,Call
from .engineering_kernel import operator
from . import study_service as service
from sdk.cli.arc1cli.host_cpu import HostCpuSampler

class IdleBridge(QObject):
    def __init__(self,host,kernel):
        super().__init__(host);self.host=host;self.kernel=kernel;self.owner=operator().identity;self.last_input=time.time();self.sampler=HostCpuSampler();self.worker=None;self.inhibited=False;self.inhibited_at=0;self.presence_written=0
        from PySide6.QtWidgets import QApplication
        QApplication.instance().installEventFilter(self);self.timer=QTimer(self);self.timer.setInterval(5000);self.timer.timeout.connect(self.tick);self.timer.start()
    def eventFilter(self,obj,event):
        if event.type() in (QEvent.KeyPress,QEvent.MouseButtonPress,QEvent.Wheel,QEvent.TouchBegin):
            self.last_input=time.time()
            if not self.host._closing:self.presence()
        return False
    def presence(self):
        with self.kernel.db() as db:cfg=service.settings(db,self.owner)
        if not cfg['idle_enabled'] or time.time()-self.presence_written<.25:return
        self.presence_written=time.time()
        from PySide6.QtCore import QProcess
        from PySide6.QtWidgets import QApplication
        overlay=getattr(self.host,'clip_overlay',None)
        busy=(self.host.process.state()!=QProcess.NotRunning or bool(overlay and (overlay.busy or overlay._requests_inflight)))
        cpu=self.sampler.snapshot()
        service.record_presence(self.kernel,self.owner,focused=bool(QApplication.activeWindow() is self.host),busy=busy,last_input=self.last_input,cpu=cpu)
    def inhibit(self):self.inhibited=True;self.inhibited_at=time.time();service.master_stop(self.kernel)
    def tick(self):
        if self.host._closing or self.worker and self.worker.isRunning():return
        from .ledger_control import value
        if not value(self.kernel,'stacy.enabled') or not value(self.kernel,'operations.services_enabled'):return
        with self.kernel.db() as db:cfg=service.settings(db,self.owner)
        if not cfg['idle_enabled']:return
        # Explicit re-arming is required after Master Stop; no timer restarts work.
        if self.inhibited and cfg.get('idle_armed_at',0)<=self.inhibited_at:return
        self.inhibited=False;self.presence()
        with self.kernel.db() as db:
            reason=service.idle_reason(self.kernel,db,self.owner,cfg['limits'])
        if reason:return
        worker=Call(self.kernel,'study.idle.poll',{},operator(),self.host);self.worker=worker;self.host.service_workers.append(worker)
        def done():
            if worker in self.host.service_workers:self.host.service_workers.remove(worker)
            self.worker=None;worker.deleteLater()
        worker.finished.connect(done);worker.start()

class StudyTab(ServiceTab):
    def __init__(self,host,memory):
        super().__init__(host);self.memory=memory;self.session=None;self.job=None
        label=QLabel('Bounded study · three source-bound read stages. Procedures stay candidates until a held-out check and your review.');label.setWordWrap(True);self.outer.addWidget(label);self.pages=QTabWidget();self.outer.addWidget(self.pages,1)
        study=QWidget();box=QVBoxLayout(study);self.choice=QComboBox();self.choice.setMinimumContentsLength(12);self.choice.currentIndexChanged.connect(self.load);box.addWidget(self.choice)
        self.goal=QLineEdit();writing_prompt(self.goal, 'Study question or investigation goal');box.addWidget(self.goal);self.unknowns=QPlainTextEdit();writing_prompt(self.unknowns, 'Unknowns / contradictions · one per line');self.unknowns.setMaximumHeight(75);box.addWidget(self.unknowns)
        self.bindings=QPlainTextEdit('[]');self.bindings.setMaximumHeight(60);box.addWidget(self.bindings);row=QHBoxLayout();box.addLayout(row)
        for text,fn in [('Attach references',lambda:self.bindings.setPlainText(memory.reference_json.toPlainText())),('Create study',self.create),('Reload',self.reload)]:b=QPushButton(text);b.clicked.connect(fn);row.addWidget(b)
        row=QHBoxLayout();box.addLayout(row)
        for text,fn in [('Next stage',self.advance),('Pause / cancel',self.pause),('Resume',self.resume)]:b=QPushButton(text);b.clicked.connect(fn);row.addWidget(b)
        row=QHBoxLayout();box.addLayout(row)
        for text,fn in [('Arm idle',lambda:self.arm(True)),('Disarm idle',lambda:self.arm(False)),('Relink restored',self.rebind)]:b=QPushButton(text);b.clicked.connect(fn);row.addWidget(b)
        self.state=QLabel('No study selected. Idle starts disabled.');self.state.setWordWrap(True);box.addWidget(self.state);self.details=QPlainTextEdit();self.details.setReadOnly(True);self.details.setMinimumHeight(230);box.addWidget(self.details,1);self.page(study,'1 · Study')
        procedure=QWidget();box=QVBoxLayout(procedure);self.trial_binding=QPlainTextEdit('{}');self.trial_binding.setMaximumHeight(95);writing_prompt(self.trial_binding, 'Exact reference binding from a second private library');box.addWidget(self.trial_binding)
        b=QPushButton('Use attached reference as test input');b.clicked.connect(self.attach_trial);box.addWidget(b);row=QHBoxLayout();box.addLayout(row)
        for text,fn in [('Held-out check',lambda:self.procedure_read(False)),('Run reviewed',lambda:self.procedure_read(True))]:b=QPushButton(text);b.clicked.connect(fn);row.addWidget(b)
        row=QHBoxLayout();box.addLayout(row)
        for text,approved in [('Approve procedure',True),('Reject procedure',False)]:b=QPushButton(text);b.clicked.connect(lambda checked=False,a=approved:self.review(a));row.addWidget(b)
        self.procedure_info=QPlainTextEdit();self.procedure_info.setReadOnly(True);self.procedure_info.setMinimumHeight(250);box.addWidget(self.procedure_info,1);self.page(procedure,'2 · Procedure')
        tools=QWidget();box=QVBoxLayout(tools);self.limits=QPlainTextEdit(json.dumps(service.c.DEFAULT,indent=2));self.limits.setMinimumHeight(220);box.addWidget(self.limits)
        note=QLabel('Limits apply to newly created sessions. Idle pilot: Linux, Graphite focused, no recent input, fresh CPU/RAM/power readings and no other Kernel work. No model tokens or cloud calls.');note.setWordWrap(True);box.addWidget(note)
        for text,fn in [('Save study limits',self.save_limits),('Show six feature proposals',lambda:self.call('study.radar',{},self.show_extra)),('Seal private edition',self.export_edition),('Restore private edition',self.restore_edition)]:b=QPushButton(text);b.clicked.connect(fn);box.addWidget(b)
        self.extra=QPlainTextEdit();self.extra.setReadOnly(True);self.extra.setMinimumHeight(260);box.addWidget(self.extra,1);self.page(tools,'3 · Limits / editions');self.outer.addWidget(self.status)
        self.timer=QTimer(self);self.timer.setInterval(700);self.timer.timeout.connect(self.poll);self.timer.start();QTimer.singleShot(0,self.reload)
    def page(self,w,title):s=QScrollArea();s.setWidgetResizable(True);s.setWidget(w);self.pages.addTab(s,title)
    def show_extra(self,v):self.extra.setPlainText(json.dumps(v,ensure_ascii=False,indent=2))
    def reload(self):
        def loaded(v):
            ident=getattr(self,'pending',None) or self.choice.currentData();self.pending=None;self.choice.blockSignals(True);self.choice.clear()
            for s in v['sessions']:self.choice.addItem(s['goal'][:65],s['id'])
            self.choice.setCurrentIndex(max(0,self.choice.findData(ident)));self.choice.blockSignals(False);self.load()
        self.call('study.list',{},loaded)
    def load(self,*args):
        ident=self.choice.currentData()
        if not ident:return
        def loaded(v):
            if self.choice.currentData()!=ident:return
            self.session=v;self.state.setText(('PAUSED · ' if v['paused'] else '')+str(len(v['stages']))+'/3 stages · '+v['applicability']+' · '+str(v.get('active_job_state') or 'no live job'))
            lines=[v['goal'],'','Frozen library: '+v['frozen']['namespace'],'Registry: '+v['registry_digest'],'']
            for stage in v['stages']:lines.extend([stage['stage'].upper(),json.dumps(stage['result'],ensure_ascii=False,indent=2),''])
            self.details.setPlainText('\n'.join(lines));self.procedure_info.setPlainText(json.dumps(v.get('procedure'),ensure_ascii=False,indent=2))
        self.call('study.get',{'id':ident},loaded)
    def create(self):
        try:refs=json.loads(self.bindings.toPlainText())
        except ValueError:self.status.setText('Reference addresses must be valid JSON.');return
        def created(v):self.pending=v['id'];self.reload()
        self.call('study.create',{'goal':self.goal.text(),'unknowns':[v.strip() for v in self.unknowns.toPlainText().splitlines() if v.strip()],'references':refs},created)
    def selected(self):return self.choice.currentData()
    def advance(self):
        if self.selected():self.call('study.advance',{'id':self.selected()},self.submitted)
    def submitted(self,v):
        self.job=v.get('job',{}).get('id');self.status.setText(v['state']);self.load()
    def poll(self):
        if not self.job or self.workers:return
        def loaded(v):
            if v['state'] in service.TERMINAL:self.job=None;self.status.setText('Study job '+v['state']);self.load()
        self.call('jobs.get',{'id':self.job},loaded)
    def pause(self):
        if self.selected():self.call('study.pause',{'id':self.selected(),'reason':'Owner paused the study from Graphite'},lambda v:(self.status.setText('Study paused; committed stages retained.'),self.load()))
    def resume(self):
        if self.selected():self.call('study.resume',{'id':self.selected()},lambda v:(self.status.setText('Resumed from persisted stages. Idle remains separately controlled.'),self.load()))
    def arm(self,enabled):
        if self.selected():self.call('study.idle.enable',{'id':self.selected(),'enabled':enabled},lambda v:self.status.setText('Idle armed within Linux focused-window pilot gates.' if enabled else 'Idle disabled.'))
    def attach_trial(self):
        try:values=json.loads(self.memory.reference_json.toPlainText());self.trial_binding.setPlainText(json.dumps(values[0] if values else {}))
        except ValueError:self.status.setText('Attach an indexed reference in Tasks / memory first.')
    def procedure_read(self,use):
        if not self.selected():return
        try:b=json.loads(self.trial_binding.toPlainText())
        except ValueError:self.status.setText('Test reference must be valid JSON.');return
        self.call('study.procedure.run' if use else 'study.procedure.test',{'id':self.selected(),'reference':b},lambda v:(self.procedure_info.setPlainText(json.dumps(v,indent=2)),self.status.setText('Current-original trial recorded. It does not measure model learning.')))
    def review(self,approved):
        if not self.selected():return
        reason,ok=QInputDialog.getText(self,'Review procedure','Reason:')
        if ok and reason.strip():self.call('study.procedure.review',{'id':self.selected(),'approved':approved,'reason':reason},lambda v:(self.status.setText('Procedure review recorded.'),self.load()))
    def rebind(self):
        if not self.selected():return
        def loaded(v):
            ns=v['namespaces']
            if not ns:self.status.setText('Review and index restored copies in Intake first.');return
            names=[n['name']+' · '+n['id'][:8] for n in ns];choice,ok=QInputDialog.getItem(self,'Relink identical originals','Reviewed library:',names,0,False)
            if ok:self.call('study.rebind',{'id':self.selected(),'namespace':ns[names.index(choice)]['id'],'reason':'Owner reviewed identical restored originals'},lambda v:(self.status.setText('Original bytes relinked. Select Resume when ready.'),self.load()))
        self.call('intake.namespaces',{},loaded)
    def save_limits(self):
        try:value=json.loads(self.limits.toPlainText())
        except ValueError:self.status.setText('Limits must be valid JSON.');return
        self.call('study.configure',{'limits':value},lambda v:(self.show_extra(v),self.status.setText('Limits saved for new studies; idle disabled.')))
    def export_edition(self):
        path,_=QFileDialog.getSaveFileName(self,'Seal a private dated edition','','ZIP (*.zip)')
        if not path:return
        key,_=QFileDialog.getSaveFileName(self,'Save recovery key separately',path+'.key','Key (*.key)')
        if key:self.call('study.edition.export',{'destination':path,'key_path':key},self.show_extra)
    def restore_edition(self):
        path,_=QFileDialog.getOpenFileName(self,'Restore private edition into empty owner profile','','ZIP (*.zip)')
        if not path:return
        key,_=QFileDialog.getOpenFileName(self,'Select separate recovery key','','Key (*.key)')
        if key:self.call('study.edition.restore',{'path':path,'key_path':key},lambda v:(self.show_extra(v),self.reload()))
    def shutdown_engineering(self):self.timer.stop();super().shutdown_engineering()
