"""Contextual Qt controls for the shared workshop and desktop tool services."""
from __future__ import annotations
from .text_prompts import writing_prompt
import hashlib
import json
from pathlib import Path
import threading
import uuid
from PySide6.QtCore import QObject, Signal, Qt, QTimer, QUrl
from PySide6.QtWidgets import (QApplication,QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,
    QPushButton,QComboBox,QPlainTextEdit,QTreeWidget,QTreeWidgetItem,QTabWidget,QSpinBox,QCheckBox,QMessageBox,QHeaderView)
from .engine import engineering
from .engineering_kernel import operator, Principal
from .project_context import refusal
from .command_rows import fold

class Call(QObject):
    ready=Signal(object)
    def __init__(self,parent,fn,callback):
        super().__init__(parent);self.fn=fn
        host=getattr(parent,'host',None);epoch=getattr(host,'_operation_epoch',0)
        def deliver(result):
            if host is not None and epoch!=getattr(host,'_operation_epoch',0):
                if hasattr(parent,'busy'):parent.busy=False
                return
            callback(result)
        self.ready.connect(deliver)
    def start(self):
        def run():
            try:r=self.fn()
            except Exception as exc:r={'ok':False,'error':{'message':str(exc)}}
            try:self.ready.emit(r)
            except RuntimeError:pass
        threading.Thread(target=run,daemon=True).start()

class WorkshopTab(QWidget):
    def __init__(self,host,kernel):
        super().__init__();self.host=host;self.kernel=kernel;self.selected=None;self.busy=False
        layout=QVBoxLayout(self)
        title=QLabel('GRAPHITE · ENGINEERING WORKSHOP\nInspect current source → investigate → revise an isolated candidate → build and test → independent acceptance.')
        title.setWordWrap(True);layout.addWidget(title)
        self.goal=QLineEdit();writing_prompt(self.goal, 'Describe an observable defect or improvement')
        layout.addWidget(self.goal)
        row=QHBoxLayout();self.profile=QComboBox();self.profile.addItem('ARC-OS C','arcos');self.profile.addItem('Graphite Python','ledger')
        self.profile.currentIndexChanged.connect(self.profile_changed);row.addWidget(self.profile)
        self.path=QLineEdit('software/arcos/src/host.c');writing_prompt(self.path, 'One to five exact implementation paths, separated by commas');row.addWidget(self.path,1)
        b=QPushButton('Use editor');b.clicked.connect(self.use_editor);row.addWidget(b);layout.addLayout(row)
        row=QHBoxLayout();self.provider=QComboBox();self.provider.addItems(['gemini','external']);row.addWidget(self.provider)
        self.execution=QComboBox();self.execution.addItem('Automatic isolated tests','isolated');self.execution.addItem('Review each native revision','reviewed');row.addWidget(self.execution)
        self.calls=QSpinBox();self.calls.setRange(1,12);self.calls.setValue(6);self.calls.setPrefix('Calls ');row.addWidget(self.calls)
        self.runtime=QSpinBox();self.runtime.setRange(30,600);self.runtime.setValue(300);self.runtime.setSuffix(' s');row.addWidget(self.runtime)
        self.component=QLineEdit();self.component.setMaximumWidth(90);writing_prompt(self.component, 'Ref e.g. J14');row.addWidget(self.component);layout.addLayout(row)
        self.share=QCheckBox('Share the declared source roots and diagnostics with Gemini for this bounded task')
        self.share.setToolTip('Google unpaid-service terms permit product improvement and human review. Secrets and restricted vendor originals are excluded.');layout.addWidget(self.share)
        self.status=QLabel('Prepare a task, then review its complete scope before starting.');self.status.setWordWrap(True);layout.addWidget(self.status)
        row=QHBoxLayout()
        for label,fn in [('Prepare',self.prepare),('Review / start',lambda:self.control('start')),('Resume',lambda:self.control('resume')),
                         ('Pause',lambda:self.control('pause')),('Stop',lambda:self.control('cancel')),('Provider settings',host.open_clip)]:
            b=QPushButton(label);b.clicked.connect(fn);row.addWidget(b)
        fold(row,keep=('Prepare','Review / start','Stop'),groups=[('Task',('Pause','Resume'))])
        layout.addLayout(row)
        self.tasks=QTreeWidget();self.tasks.setHeaderLabels(['State','Goal','Task']);self.tasks.setMaximumHeight(100)
        self.tasks.itemSelectionChanged.connect(self.select);layout.addWidget(self.tasks)
        self.views=QTabWidget();self.findings=QPlainTextEdit();self.diff=QPlainTextEdit();self.context=QPlainTextEdit()
        for text,widget in [('Findings and checks',self.findings),('Exact diff',self.diff),('Context and task',self.context)]:
            widget.setReadOnly(True);self.views.addTab(widget,text)
        layout.addWidget(self.views,1)
        row=QHBoxLayout()
        for label,fn in [('Refresh',self.refresh),('Authorize exact test revision',self.authorize),('Submit passing candidate',self.finish),('Source and debugger tools',host.show_developer_tools)]:
            b=QPushButton(label);b.clicked.connect(fn);row.addWidget(b)
        fold(row,keep=('Authorize exact test revision','Submit passing candidate'))
        layout.addLayout(row)
        self.timer=QTimer(self);self.timer.timeout.connect(self.refresh);self.timer.start(2500)
        self.refresh();self.call('workshop.status',{},self.provider_status)
    def profile_changed(self):
        self.path.setText('software/arcos/src/host.c' if self.profile.currentData()=='arcos' else 'workbench/clip_workspace.py')
    def use_editor(self):
        ed=self.host.current_editor()
        if ed and getattr(ed,'path',None):
            try:
                path=ed.path.relative_to(self.host.root).as_posix();self.profile.setCurrentIndex(1 if path.startswith('workbench/') else 0);self.path.setText(path)
            except ValueError:self.status.setText('Select an implementation inside the current project.')
        else:self.status.setText('Open the source first, or enter its exact project path.')
    def call(self,op,args,callback=None,actor=None):
        if self.busy:return
        self.busy=True;self.status.setText(op+'…')
        def done(r):
            self.busy=False
            if not r['ok']:self.status.setText(r['error']['message']);return
            if refusal(r['result']):self.status.setText(refusal(r['result']));return
            if callback:callback(r['result'])
        self.worker=Call(self,lambda:self.kernel.dispatch(op,args,actor or operator()),done);self.worker.start()
    def provider_status(self,r):
        self.status.setText(('Gemini configured' if r['provider']['configured'] else 'Gemini awaits local settings')+' · '+
            ('isolated execution available' if r['isolation']['available'] else 'automatic isolation unavailable; reviewed execution remains explicit'))
    def prepare(self):
        args={'goal':self.goal.text(),'profile':self.profile.currentData(),'provider':self.provider.currentText(),
          'paths':[x.strip() for x in self.path.text().split(',') if x.strip()],'execution':self.execution.currentData(),
          'component':self.component.text().strip(),'max_calls':self.calls.value(),'max_runtime':self.runtime.value(),
          'share_source':self.share.isChecked(),'request_key':uuid.uuid4().hex}
        def done(j):self.selected=j['id'];self.refresh();self.status.setText('Task prepared. Review its context, tools and execution mode before starting.')
        actor=Principal('desktop-workshop',frozenset({'read','candidate','execute'}),operator().paths)
        self.call('workshop.prepare',args,done,actor)
    def control(self,name):
        if not self.selected:return
        if name in ('start','resume'):
            j=self.kernel.record('jobs',self.selected)
            message='Goal: '+j['goal']+'\nFiles: '+', '.join(j['scope'])+'\nTools: '+', '.join(j['authorized_tools'])+'\nProvider: '+j['provider']+'\nExecution: '+j['execution']+'\nMaximum calls: '+str(j['provider_budget']['max_calls'])+'\nSource acceptance stays separate.'
            if j['execution']=='reviewed':message+='\nBaseline tests run with your account. Candidate execution requires review of each exact revision; this mode has no OS sandbox.'
            if QMessageBox.question(self,'Bounded task authorization',message,QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:return
        self.call('workshop.'+name,{'id':self.selected},lambda r:self.refresh())
    def select(self):
        rows=self.tasks.selectedItems()
        if rows:self.selected=rows[0].data(0,Qt.UserRole);self.inspect()
    def refresh(self):
        if self.busy:return
        self.tasks.blockSignals(True);self.tasks.clear()
        for j in self.kernel.listing('jobs'):
            if j['tool']!='clip.workshop':continue
            item=QTreeWidgetItem([j['state'],j['goal'],j['id']]);item.setData(0,Qt.UserRole,j['id']);self.tasks.addTopLevelItem(item)
            if j['id']==self.selected:item.setSelected(True)
        self.tasks.blockSignals(False);self.tasks.resizeColumnToContents(0)
        if self.selected:self.inspect()
    def inspect(self):
        def done(r):
            j=r['task'];self.status.setText(j['state']+' · '+j['current_operation'])
            self.findings.setPlainText(json.dumps({'findings':j['findings'],'provider_summary':j.get('provider_summary'),
                'calls_attempted':j['provider_calls'],'diagnostics':r['diagnostics'],'source_current':r['source_current']},indent=2))
            self.context.setPlainText(json.dumps(r,indent=2))
            d=self.kernel.dispatch('candidates.diff',{'id':j['candidate']},operator())
            if d['ok']:self.diff.setPlainText('\n'.join(x['diff'] for x in d['result']['changes']) or 'No source change proposed.')
        self.call('workshop.inspect',{'id':self.selected},done)
    def authorize(self):
        if not self.selected:return
        j=self.kernel.record('jobs',self.selected);self.views.setCurrentWidget(self.diff)
        if QMessageBox.question(self,'Review exact native revision','Read the displayed diff before authorizing. The reviewed mode executes native code using your OS account, without a sandbox. Authorize this exact revision?',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)==QMessageBox.Yes:
            self.call('candidates.authorize_execution',{'id':j['candidate']},lambda r:self.status.setText('Exact revision authorized. Resume the task when ready.'))
    def finish(self):
        if not self.selected:return
        j=self.kernel.record('jobs',self.selected)
        self.call('workshop.act',{'id':j['id'],'request_key':uuid.uuid4().hex,'action':{'binding':j['binding'],
            'name':'finish','arguments':{'summary':'Operator submitted the current passing candidate for independent source review.'}}},lambda r:self.refresh())

class DeveloperToolsTab(QWidget):
    def __init__(self,host):
        super().__init__();self.host=host;self.kernel=engineering(host.root);self.editor=None;self.session=None;self.busy=False
        layout=QVBoxLayout(self);self.status=QLabel('C language assistance and the registered ARC-OS host debugger. Physical target debugging is unavailable.')
        self.status.setWordWrap(True);layout.addWidget(self.status)
        self.pages=QTabWidget();layout.addWidget(self.pages,1)
        language=QWidget();form=QVBoxLayout(language);self.pages.addTab(language,'C source assistance')
        self.source_path=QLineEdit('software/arcos/src/controller.c');form.addWidget(self.source_path)
        row=QHBoxLayout();self.line=QSpinBox();self.line.setRange(1,1000000);self.line.setPrefix('Line ');row.addWidget(self.line)
        self.column=QSpinBox();self.column.setRange(1,100000);self.column.setPrefix('Column ');row.addWidget(self.column)
        b=QPushButton('Use current editor');b.clicked.connect(self.capture_current);row.addWidget(b);form.addLayout(row)
        row=QHBoxLayout()
        for label,op in [('Diagnostics','diagnostics'),('Definition','definition'),('References','references'),('Completion','completion'),('Type / help','hover')]:
            b=QPushButton(label);b.clicked.connect(lambda checked=False,name=op:self.assist(name));row.addWidget(b)
        form.addLayout(row);self.results=QTreeWidget();self.results.setHeaderLabels(['Result','Location / type']);self.results.header().setSectionResizeMode(0,QHeaderView.Stretch);self.results.header().setSectionResizeMode(1,QHeaderView.ResizeToContents);self.results.itemDoubleClicked.connect(self.activate);form.addWidget(self.results,1)
        self.detail=QPlainTextEdit();self.detail.setReadOnly(True);form.addWidget(self.detail,1)
        self.results.itemSelectionChanged.connect(self.select_result)
        debug=QWidget();form=QVBoxLayout(debug);self.pages.addTab(debug,'Host debugger')
        label=QLabel('Registered ARC-OS launcher/controller diagnostic · native host code · ordinary account process, not an OS sandbox. Build first, then open at main.')
        label.setWordWrap(True);form.addWidget(label)
        row=QHBoxLayout()
        for label,fn in [('Build diagnostic',self.build),('Load symbols',lambda:self.open_debug(False)),('Run to main',lambda:self.open_debug(True)),('Next',lambda:self.debug('next')),('Step',lambda:self.debug('step')),('Continue',lambda:self.debug('continue'))]:
            b=QPushButton(label);b.clicked.connect(fn);row.addWidget(b)
        form.addLayout(row);row=QHBoxLayout()
        for name in ('locals','stack','registers','close'):
            b=QPushButton(name.title());b.clicked.connect(lambda checked=False,cmd=name:self.debug(cmd));row.addWidget(b)
        b=QPushButton('Break at selected source line');b.clicked.connect(lambda:self.debug('break'));row.addWidget(b);form.addLayout(row)
        b=QPushButton('Inspect source address map');b.clicked.connect(lambda:self.debug('source_lines'));row.addWidget(b)
        fold(row,keep=('Break at selected source line','Close'),groups=[('Inspect',('Locals','Stack','Registers','Inspect source address map'))])
        self.debug_output=QPlainTextEdit();self.debug_output.setReadOnly(True);form.addWidget(self.debug_output,1)
        app=QApplication.instance()
        if app:
            from .desktop_services import close_all
            app.aboutToQuit.connect(lambda:close_all(host.root))
    def title(self):return 'Source assistance · Host debugger'
    def call(self,op,args,callback):
        if self.busy:return
        self.busy=True;self.status.setText(op+'…')
        def done(r):
            self.busy=False
            if not r['ok']:self.status.setText(r['error']['message']);return
            self.status.setText(op+' completed · native host profile');callback(r['result'])
        self.worker=Call(self,lambda:self.kernel.dispatch(op,args,operator()),done);self.worker.start()
    def capture_current(self):
        ed=self.host.current_editor()
        if ed:self.capture_editor(ed)
        else:self.status.setText('Open a C source file, then use its Definition or Completion menu action.')
    def capture_editor(self,ed):
        self.editor=ed
        try:
            self.source_path.setText(ed.path.relative_to(self.host.root).as_posix());cursor=ed.textCursor()
            self.line.setValue(cursor.blockNumber()+1);self.column.setValue(cursor.positionInBlock()+1)
        except (ValueError,RuntimeError):self.editor=None
    def assist(self,operation):
        args={'path':self.source_path.text().strip(),'line':self.line.value()-1,'character':self.column.value()-1,'operation':operation}
        if self.editor:
            try:
                if self.editor.path.relative_to(self.host.root).as_posix()==args['path']:args['text']=self.editor.toPlainText()
            except (ValueError,RuntimeError):self.editor=None
        self.call('desktop.code',args,self.show_language)
    def show_language(self,r):
        self.last_language=r;self.results.clear();self.detail.setPlainText(json.dumps(r,indent=2))
        self.status.setText(r.get('context_state','UNASSESSED')+' · '+r.get('reason',r.get('reference_scope','')))
        if r.get('context_state')!='CURRENT_INPUTS':return
        value=r['result'];op=r['operation']
        if op=='completion':
            for item in value['items']:
                row=QTreeWidgetItem([item.get('label',''),item.get('detail','')]);row.setData(0,Qt.UserRole,{'completion':item});self.results.addTopLevelItem(row)
        elif op in ('definition','references'):
            for item in value or []:
                uri=item.get('uri',item.get('targetUri',''));position=item.get('range',item.get('targetSelectionRange',{})).get('start',{})
                location=Path(QUrl(uri).toLocalFile())
                try:label=location.relative_to(self.host.root).as_posix()
                except ValueError:label=uri
                row=QTreeWidgetItem([label,'Line '+str(position.get('line',0)+1)]);row.setToolTip(0,uri);row.setData(0,Qt.UserRole,{'uri':uri,'position':position});self.results.addTopLevelItem(row)
        elif op=='diagnostics':
            for publication in value:
                for diagnostic in publication.get('diagnostics',[]):
                    position=diagnostic['range']['start'];row=QTreeWidgetItem([diagnostic['message'],'Line '+str(position['line']+1)])
                    row.setData(0,Qt.UserRole,{'uri':publication['uri'],'position':position});self.results.addTopLevelItem(row)
            if not self.results.topLevelItemCount():self.results.addTopLevelItem(QTreeWidgetItem(['No diagnostics in this buffer','Native host C11']))
    def select_result(self):
        rows=self.results.selectedItems()
        if rows:self.detail.setPlainText(json.dumps(rows[0].data(0,Qt.UserRole),indent=2))
    def activate(self,item,column):
        if self.last_language:
            from .desktop_services import sha
            if any(not (self.host.root/n).is_file() or sha(self.host.root/n)!=h for n,h in self.last_language.get('context_inputs',{}).items()):
                self.status.setText('Source context changed; request current assistance again.');return
            if self.editor and hashlib.sha256(self.editor.toPlainText().encode()).hexdigest()!=self.last_language.get('buffer_sha256'):
                self.status.setText('Buffer changed; request current assistance again.');return
        data=item.data(0,Qt.UserRole) or {}
        if data.get('uri'):
            from PySide6.QtCore import QUrl
            path=Path(QUrl(data['uri']).toLocalFile()).resolve()
            if not path.is_relative_to(self.host.root):self.status.setText('Definition is outside the project; inspect its path in the result.');return
            self.host.open_document(path);ed=self.host.current_editor()
            if ed:ed.go_to(data['position'].get('line',0)+1,data['position'].get('character',0)+1)
        elif data.get('completion') and self.editor:
            try:
                raw=self.editor.toPlainText()
                if hashlib.sha256(raw.encode()).hexdigest()!=self.last_language['buffer_sha256']:
                    self.status.setText('Buffer changed; request current completion again.');return
                item=data['completion'];edit=item.get('textEdit')
                if edit:
                    bounds=edit.get('range',edit.get('replace'))
                    if not bounds:raise ValueError('Completion requires an unsupported edit form')
                    cursor=self.editor.textCursor();doc=self.editor.document()
                    a,b=bounds['start'],bounds['end']
                    cursor.setPosition(doc.findBlockByNumber(a['line']).position()+a['character'])
                    cursor.setPosition(doc.findBlockByNumber(b['line']).position()+b['character'],cursor.KeepAnchor)
                    cursor.insertText(edit['newText'])
                else:self.editor.insertPlainText(item.get('insertText',item['label']))
                self.status.setText('Completion inserted into the editor buffer; save explicitly.')
            except (RuntimeError,KeyError,ValueError) as exc:self.status.setText(str(exc))
    def build(self):
        def done(r):
            self.debug_output.setPlainText(json.dumps(r,indent=2))
            self.status.setText('Debug build submitted as job '+r['id']+'. Open after it completes in Engineering Jobs.')
        self.call('desktop.debug.build',{},done)
    def open_debug(self,run=True):
        def done(r):self.session=r['id'];self.debug_output.setPlainText('\n'.join(r['records']))
        self.call('desktop.debug.open',{'run':run},done)
    def debug(self,command):
        if not self.session:self.status.setText('Build and open the registered diagnostic first.');return
        args={'id':self.session,'command':command}
        if command in ('break','source_lines'):args.update(path=self.source_path.text().strip(),line=self.line.value())
        def done(r):
            self.debug_output.appendPlainText('\n'+command+' · '+r['state']+'\n'+'\n'.join(r['records']))
            if command=='close':self.session=None
        self.call('desktop.debug.command',args,done)
