"""One Object Glass controller, with compact and full native Qt views."""
from __future__ import annotations
import json,time
from PySide6.QtCore import QObject,Signal,QTimer,Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QCheckBox, QPlainTextEdit, QScrollArea, QLayout
from sdk.cli.arc1cli import object_context as core
from . import object_context as service
from .engineering_kernel import operator
from .engine import engineering
from .register_tabs import Call

class Controller(QObject):
    changed=Signal(object)
    def __init__(self,host):
        super().__init__(host);self.host=host;self.kernel=engineering(host.root);self.principal=operator();self.origin=None
        if not hasattr(host,'service_workers'):host.service_workers=[]
        self.guard=core.Ticket();self.selector=None;self.binding=None;self.data={'state':'EMPTY','summary':'Select an object to inspect its context.'};self.workers=[]
        try:self.history=service.history(self.kernel,self.principal)
        except (ValueError,OSError):self.history=core.History()
        self.last_check=0;self.timer=QTimer(self);self.timer.setInterval(400);self.timer.timeout.connect(self.check_authority);self.timer.start()
        QTimer.singleShot(0,self.resume)
    def caller(self):return getattr(self.origin,'principal',self.principal)
    def publish(self,data):self.data=data;self.changed.emit(data)
    def resume(self):
        entry=self.history.current
        if not self.selector and entry:self.select(entry['selector'],entry=entry,remember=False)
    def check_authority(self):
        if self.host._closing:return
        current=self.caller()
        if core.principal_key(current)!=core.principal_key(self.principal):
            self.principal=current;self.guard.invalidate();self.selector=None;self.binding=None
            try:self.history=service.history(self.kernel,current)
            except (ValueError,OSError):self.history=core.History()
            self.publish({'state':'UNAVAILABLE','summary':'Caller permissions changed. Select the object again.'});return
        if self.selector and time.monotonic()-self.last_check>10 and not self.workers:self.refresh(False)
    def request(self,op,args,done):
        worker=Call(self.kernel,op,args,self.principal,self.host);self.workers.append(worker);self.host.service_workers.append(worker)
        worker.ready.connect(done)
        worker.finished.connect(lambda:self.workers.remove(worker) if worker in self.workers else None)
        worker.finished.connect(lambda:self.host.service_workers.remove(worker) if worker in self.host.service_workers else None)
        worker.finished.connect(worker.deleteLater);worker.start()
    def select(self,value,principal=None,origin=None,entry=None,remember=True,history_index=None):
        if self.host._closing:return
        value=core.selector(value);who=principal or self.principal
        if core.principal_key(who)!=core.principal_key(self.principal):
            try:self.history=service.history(self.kernel,who)
            except (ValueError,OSError):self.history=core.History()
        self.principal=who
        if origin is not None:self.origin=origin
        self.selector=value;self.binding=entry;caller=core.principal_key(who);ticket=self.guard.begin(value,caller);epoch=getattr(self.host,'_operation_epoch',0)
        self.last_check=time.monotonic();self.publish({'state':'LOADING','selector':value,'summary':'Checking selected identity, sources and permissions…'})
        args={'selector':value}
        if entry:args.update(expected_revision=entry['revision'],expected_object_id=entry['object_id'])
        def loaded(envelope):
            if self.host._closing or epoch!=getattr(self.host,'_operation_epoch',0) or not self.guard.accepts(ticket,value,core.principal_key(self.caller())):return
            if not envelope.get('ok'):
                self.publish({'state':'UNAVAILABLE','selector':value,'summary':'This object is unavailable to the current caller.'});return
            data=envelope['result']
            if data.get('state')=='AVAILABLE':
                self.binding={'object_id':data['object_id'],'revision':data['revision']}
                if history_index is not None:self.history.index=history_index
                if remember:self.history.add(data)
                try:service.remember(self.kernel,self.principal,self.history.export())
                except (ValueError,OSError):data={**data,'history_notice':'Navigation history could not be saved.'}
            elif history_index is not None:self.history.index=history_index
            self.publish(data)
        self.request('ledger.object.inspect',args,loaded)
    def refresh(self,accept_current=True):
        if not self.selector:return
        entry=self.binding
        if accept_current and entry:
            # Refresh is allowed to advance bytes, but cannot silently replace identity.
            args={'selector':self.selector,'expected_object_id':entry['object_id']}
            value=self.selector;caller=core.principal_key(self.caller());ticket=self.guard.begin(value,caller);epoch=getattr(self.host,'_operation_epoch',0);self.principal=self.caller();self.last_check=time.monotonic()
            self.publish({'state':'LOADING','selector':value,'summary':'Refreshing the matching object identity…'})
            def loaded(envelope):
                if self.host._closing or epoch!=getattr(self.host,'_operation_epoch',0) or not self.guard.accepts(ticket,value,core.principal_key(self.caller())):return
                data=envelope['result'] if envelope.get('ok') else {'state':'UNAVAILABLE','summary':'This object is unavailable to the current caller.'}
                if data.get('state')=='AVAILABLE':
                    self.binding={'object_id':data['object_id'],'revision':data['revision']}
                    self.history.add(data)
                    try:service.remember(self.kernel,self.principal,self.history.export())
                    except (ValueError,OSError):data={**data,'history_notice':'Navigation history could not be saved.'}
                self.publish(data)
            self.request('ledger.object.inspect',args,loaded)
        else:self.select(self.selector,entry=entry,remember=False)
    def move(self,step):
        entry=self.history.at(step)
        if entry:self.select(entry['selector'],entry=entry,remember=False,history_index=self.history.index+step)
    def clear(self):
        self.guard.invalidate();self.selector=None;self.binding=None;self.origin=None;self.history=core.History()
        try:service.remember(self.kernel,self.principal,self.history.export())
        except (ValueError,OSError):pass
        self.publish({'state':'EMPTY','summary':'Select an object to inspect its context.'})
    def action(self,ident):
        data=self.data
        if data.get('state')!='AVAILABLE':return
        value=data['selector'];caller=core.principal_key(self.caller());ticket=self.guard.current
        if not ticket or not self.guard.accepts(ticket,value,caller):return
        epoch=getattr(self.host,'_operation_epoch',0)
        args={'selector':value,'expected_revision':data['revision'],'expected_object_id':data['object_id'],'action':ident}
        def loaded(envelope):
            if self.host._closing or epoch!=getattr(self.host,'_operation_epoch',0) or not self.guard.accepts(ticket,value,core.principal_key(self.caller())):return
            if not envelope.get('ok'):
                self.publish({'state':'UNAVAILABLE','selector':value,'summary':'The action needs fresh context. Refresh or select the object again.'});return
            self.publish({**data,'action_result':envelope['result']})
        self.request('ledger.object.action',args,loaded)

class View(QWidget):
    def __init__(self,host,compact=False):
        super().__init__();self.host=host;self.controller=host.object_glass;self.compact=compact
        outer=QVBoxLayout(self);outer.setContentsMargins(0,0,0,0)
        self.scroll=QScrollArea();self.scroll.setWidgetResizable(True)
        body=QWidget();box=QVBoxLayout(body);box.setSizeConstraint(QLayout.SetMinimumSize)
        self.scroll.setWidget(body);outer.addWidget(self.scroll)
        box.setContentsMargins(0,0,0,0);box.setAlignment(Qt.AlignTop);row=QVBoxLayout() if compact else QHBoxLayout();self.back=QPushButton('Back');self.forward=QPushButton('Forward');self.refresh=QPushButton('Refresh')
        for button,fn in [(self.back,lambda:self.controller.move(-1)),(self.forward,lambda:self.controller.move(1)),(self.refresh,lambda:self.controller.refresh(True))]:button.clicked.connect(fn);row.addWidget(button)
        box.addLayout(row)
        from .result_surface import ResultSurface
        self.surface=ResultSurface(compact=compact);box.addWidget(self.surface)
        self.summary=self.surface.labels['summary'];self.summary.setAccessibleName('Selected object summary')
        self.binding=self.surface.labels['context']
        for label in (self.summary,self.binding):
            policy=label.sizePolicy();policy.setHeightForWidth(True);label.setSizePolicy(policy)
        self.context=QPlainTextEdit(self);self.context.setReadOnly(True);self.context.setAccessibleName('Selected object sources evidence and gaps');self.context.hide()
        self.actions=QVBoxLayout();box.addLayout(self.actions);self.buttons=[]
        self.expand=QCheckBox('Technical detail');self.expand.setAccessibleName('Expand selected object technical detail');box.addWidget(self.expand)
        self.detail=QPlainTextEdit();self.detail.setReadOnly(True);self.detail.setAccessibleName('Exact selected object technical data');self.detail.setMinimumHeight(140);self.detail.hide();self.expand.toggled.connect(self.detail.setVisible);box.addWidget(self.detail,1)
        if not compact:
            from .slate_windows_qt import WindowsPanel
            self.windows=WindowsPanel(host);box.addWidget(self.windows)
        row=QVBoxLayout() if compact else QHBoxLayout()
        if compact:
            full=QPushButton('Open Object Glass');full.clicked.connect(host.show_object_glass);row.addWidget(full)
        clear=QPushButton('Clear context');clear.clicked.connect(self.controller.clear);row.addWidget(clear);box.addLayout(row)
        if compact:box.addSpacing(130)  # Keep controls above Slate's resting corner.
        self.controller.changed.connect(self.loaded);self.loaded(self.controller.data)
    def title(self):return 'Object Glass'
    def loaded(self,data):
        from sdk.cli.arc1cli.workbench_view import selected_object
        self.surface.present(selected_object(data))
        self.summary.setText(data.get('summary',data.get('state','Unavailable')))
        self.binding.setText('Object '+data['object_id'][:16]+'\nRevision '+data['revision'][:16] if data.get('object_id') and data.get('revision') else data.get('state','EMPTY'))
        parts=[]
        if data.get('state')=='AVAILABLE':
            parts=['Sources: '+str(len(data['sources'])),'Evidence: '+str(len(data['evidence'])),'Gaps:']
            parts += [str(x).replace('_',' ').lower().capitalize()+'.' for x in data['gaps'][:4]]
            parts+=['Checked snapshot. Every action checks sources and permissions again.']
        self.context.setPlainText('\n'.join(parts));self.context.hide()
        for button in self.buttons:self.actions.removeWidget(button);button.deleteLater()
        self.buttons=[]
        for action in data.get('actions',[]):
            label={'source':'Relationships' if data.get('selector',{}).get('kind')!='file' else 'Saved text','evidence':'Evidence','job':'Job record','register':'Register'}.get(action['id'],action['label']) if self.compact else action['label']
            button=QPushButton(label);button.setEnabled(action['enabled']);button.setToolTip(action['reason']);button.setAccessibleName(action['label']+' for selected object');button.clicked.connect(lambda checked=False,key=action['id']:self.controller.action(key));self.actions.addWidget(button);self.buttons.append(button)
        self.detail.setPlainText(json.dumps(data,ensure_ascii=False,indent=2));self.back.setEnabled(self.controller.history.at(-1) is not None);self.forward.setEnabled(self.controller.history.at(1) is not None)
