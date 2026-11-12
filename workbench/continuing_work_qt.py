"""Continuing work: prepare, grant once, observe, stop and review."""
from .text_prompts import writing_prompt
import json
import time
from PySide6.QtCore import QTimer,Qt
from PySide6.QtWidgets import (QCheckBox,QComboBox,QDialog,QFormLayout,QHBoxLayout,QInputDialog,QLabel,QLineEdit,QListWidget,
    QListWidgetItem,QPlainTextEdit,QScrollArea,QSpinBox,QSplitter,QTabWidget,QVBoxLayout,QWidget)
from .shell2 import button,call_write,role


class WorkTab(QWidget):
    def __init__(self,host):
        super().__init__();self.host=host;self.busy=False;self.current=None;self.copy=None
        self.setObjectName('LibraryTab');self.setProperty('ledgerRoom',True)
        outer=QVBoxLayout(self);outer.setContentsMargins(20,18,20,16)
        row=QHBoxLayout();row.addWidget(role(QLabel('Night Shift'),'title'),1)
        refresh=button('Refresh','quiet');refresh.clicked.connect(self.reload);row.addWidget(refresh);outer.addLayout(row)
        self.message=QLabel('Prepare an exact plan, review its copies and budgets, then authorize it once. Originals have their own review in Changes.')
        self.message.setWordWrap(True);self.message.setTextFormat(Qt.PlainText);outer.addWidget(self.message)
        split=QSplitter();outer.addWidget(split,1);self.orders=QListWidget();self.orders.setAccessibleName('Continuing assignments')
        self.orders.itemClicked.connect(lambda i:self.open(i.data(Qt.UserRole)));split.addWidget(self.orders)
        self.pages=QTabWidget();split.addWidget(self.pages);split.setSizes([240,850]);split.setStretchFactor(1,1)
        self.build_plan();self.build_review();self.build_workers();self.reload()
        self.timer=QTimer(self);self.timer.setInterval(5000);self.timer.timeout.connect(self.refresh_current);self.timer.start()

    def title(self):return 'Night Shift'
    def info(self):return 'Owner-granted assignments, budgets and qualified checks'

    def call(self,op,args=None):
        response=call_write(self.host,op,args or {})
        if not response.get('ok'):
            self.message.setText((response.get('error') or {}).get('message','Operation did not complete.'));return None
        return response['result']

    def run(self,op,args,done):
        if self.busy or self.host._closing:return
        from .register_tabs import Call
        from .engineering_kernel import operator
        from .engine import engineering
        from shiboken6 import isValid
        self.busy=True;self.pages.setEnabled(False);self.orders.setEnabled(False)
        self.message.setText('Verifying this request… Its saved state will show the outcome.')
        if not hasattr(self.host,'service_workers'):self.host.service_workers=[]
        epoch=getattr(self.host,'_operation_epoch',0)
        worker=Call(engineering(self.host.root),op,args,operator(),self.host);self.host.service_workers.append(worker)
        def ready(response):
            if not isValid(self) or self.host._closing:return
            self.busy=False;self.pages.setEnabled(True);self.orders.setEnabled(True)
            if epoch!=getattr(self.host,'_operation_epoch',0):self.message.setText('Stopped. Refresh the saved order before continuing.');return
            if not response.get('ok'):self.message.setText((response.get('error') or {}).get('message','Inspect saved state before retrying.'));return
            done(response['result'])
        worker.ready.connect(ready)
        worker.finished.connect(lambda:self.host.service_workers.remove(worker) if worker in self.host.service_workers else None)
        worker.finished.connect(worker.deleteLater);worker.start()

    def build_plan(self):
        scroll=QScrollArea();scroll.setWidgetResizable(True);body=QWidget();box=QVBoxLayout(body);scroll.setWidget(body)
        form=QFormLayout();self.assignments=QComboBox();self.assignments.setAccessibleName('Assignment to continue');form.addRow('Assignment',self.assignments)
        self.copies=QComboBox();self.copies.setAccessibleName('Delegated working copy');form.addRow('Working copy',self.copies)
        self.copies.currentIndexChanged.connect(self.copy_changed)
        self.name=QLineEdit();writing_prompt(self.name, 'Name this continuing assignment');form.addRow('Plan title',self.name)
        self.path=QComboBox();self.path.setEditable(True);form.addRow('Selected text path',self.path)
        self.kind=QComboBox()
        for title,key in [('Read selected text','READ'),('Draft a replacement for selected text','TEXT'),('Generate an assignment report','REPORT'),
            ('Check a parts table in a protected worker','PARTS'),('Ask a protected local model for exact patches','MODEL')]:self.kind.addItem(title,key)
        form.addRow('Preparation',self.kind);box.addLayout(form)
        self.text=QPlainTextEdit();self.text.setMinimumHeight(130);writing_prompt(self.text, 'Replacement text, or the goal for a model draft');self.text.setAccessibleName('Draft content or model goal');box.addWidget(self.text)
        read=button('Open current text as the draft','quiet');read.clicked.connect(self.open_text);box.addWidget(read)
        self.model=QComboBox();form2=QFormLayout();form2.addRow('Registered local model',self.model);box.addLayout(form2)
        self.apply_copy=QCheckBox('Include applying the exact frozen proposal to this working copy');box.addWidget(self.apply_copy)
        note=QLabel('A protected model/check pauses if this computer is unqualified. Applying to originals, exporting, network access and grant changes are outside this plan.')
        note.setWordWrap(True);box.addWidget(note)
        budgets=QFormLayout();self.seconds=self.spin(1,86400,300);budgets.addRow('Active seconds',self.seconds)
        self.steps=self.spin(1,200,10);budgets.addRow('Step attempts',self.steps)
        self.tokens=self.spin(0,1000000,8192);budgets.addRow('Reserved model tokens',self.tokens)
        self.memory=self.spin(128,65536,1024);budgets.addRow('Native worker memory MiB',self.memory)
        self.files=self.spin(0,1000,10);budgets.addRow('Files changed',self.files)
        self.expiry=self.spin(1,720,24);budgets.addRow('Grant lifetime hours',self.expiry);box.addLayout(budgets)
        build=button('Prepare steps','quiet');build.clicked.connect(self.prepare_steps);box.addWidget(build)
        self.steps_json=QPlainTextEdit();self.steps_json.setAccessibleName('Exact registered calls and dependencies');self.steps_json.setPlainText('[]');self.steps_json.setMinimumHeight(170);box.addWidget(self.steps_json)
        freeze=button('Freeze this plan for review','primary');freeze.clicked.connect(self.freeze);box.addWidget(freeze)
        self.pages.addTab(scroll,'Prepare')

    def spin(self,minimum,maximum,value):
        field=QSpinBox();field.setRange(minimum,maximum);field.setValue(value);return field

    def copy_changed(self):
        if self.busy or not self.copies.currentData():return
        def selected(value):
            self.copy=value;self.path.clear();self.path.addItems(sorted(value['files']))
            self.message.setText('Selected copy: '+value['name']+(' · delegated to Graphite' if value['for_slate'] else ' · enable delegation when importing this copy'))
        self.run('changes.workspace',{'id':self.copies.currentData()},selected)

    def prepare_steps(self):
        if not self.copy or not self.copy['for_slate']:self.message.setText('Select a working copy delegated to Graphite.');return
        copy=self.copy['id'];path=self.path.currentText();kind=self.kind.currentData();steps=[]
        if kind in ('READ','TEXT'):
            steps.append({'key':'Read','operation':'work.read','arguments':{'copy':copy,'path':path},'after':[]})
        if kind=='TEXT':
            steps.append({'key':'Draft','operation':'changes.propose','arguments':{'copy':copy,'note':'Prepared through the continuing assignment',
                'operations':[{'op':'WRITE','path':path,'base_sha256':{'$step':'Read','path':['sha256']},'text':self.text.toPlainText()}]},'after':['Read']})
        if kind=='REPORT':
            steps.append({'key':'Draft','operation':'changes.report','arguments':{'copy':copy,'assignment':self.assignments.currentData(),
                'name':path or 'assignment-report.md','format':'MARKDOWN'},'after':[]})
        if kind=='PARTS':
            steps.append({'key':'Check','operation':'workers.check','arguments':{'copy':copy,'paths':[path],'check':'PARTS'},'after':[],
                'seconds':30,'require':[{'path':['passed'],'equals':True}]})
        if kind=='MODEL':
            if not self.model.currentData():self.message.setText('Register a local GGUF in Brain before preparing a model draft.');return
            steps.append({'key':'Draft','operation':'workers.draft','arguments':{'copy':copy,'paths':[path],'goal':self.text.toPlainText(),
                'model':self.model.currentData(),'context':2048,'max_tokens':1024},'after':[],'seconds':120})
        if self.apply_copy.isChecked() and kind in ('TEXT','REPORT','MODEL'):
            steps.append({'key':'Apply','operation':'changes.apply','arguments':{
                'id':{'$step':'Draft','path':['proposal_id' if kind=='MODEL' else 'id']},
                'expected_digest':{'$step':'Draft','path':['proposal_digest' if kind=='MODEL' else 'content_digest']}},'after':['Draft']})
        self.steps_json.setPlainText(json.dumps(steps,ensure_ascii=False,indent=2));self.message.setText('Review these exact calls and budgets. Preparing steps has granted nothing.')

    def open_text(self):
        if self.copy:self.run('work.read',{'copy':self.copy['id'],'path':self.path.currentText()},lambda value:self.text.setPlainText(value['text']))

    def freeze(self):
        try:steps=json.loads(self.steps_json.toPlainText())
        except ValueError:self.message.setText('Steps must be a JSON list.');return
        args={'assignment':self.assignments.currentData(),'copies':[self.copies.currentData()],'title':self.name.text(),
            'steps':steps,'budget':{'seconds':self.seconds.value(),'steps':self.steps.value(),'tokens':self.tokens.value(),
            'memory_mb':self.memory.value(),'output_bytes':1048576,'files':self.files.value()},'expires':time.time()+self.expiry.value()*3600}
        self.run('work.create',args,self.show_work)

    def build_review(self):
        page=QWidget();box=QVBoxLayout(page);self.summary=QLabel();self.summary.setWordWrap(True);self.summary.setTextFormat(Qt.PlainText);box.addWidget(self.summary)
        self.checkpoint = QLabel('Choose an assignment to inspect its saved progress.')
        self.checkpoint.setTextFormat(Qt.PlainText)
        self.checkpoint.setWordWrap(True)
        box.addWidget(self.checkpoint)
        self.review=QPlainTextEdit();self.review.setReadOnly(True);self.review.setAccessibleName('Frozen plan, authority, budgets, steps and journal');box.addWidget(self.review,1)
        for actions in [[('Authorize this exact plan once',self.authorize),('Advance one ready step',lambda:self.action('work.advance')),('Pause',lambda:self.action('work.pause'))],
            [('Resume after inspection',lambda:self.action('work.resume')),('Revoke remaining authority',self.revoke),('Open Changes',self.open_changes),('Full frozen record',self.full_record)],
            [('Accept completed result',self.accept),('Save accepted plan as procedure',self.save_procedure),('Instantiate a procedure',self.instantiate)]]:
            row=QHBoxLayout()
            for label,fn in actions:
                b=button(label,'quiet');b.clicked.connect(fn);row.addWidget(b)
            box.addLayout(row)
        self.pages.addTab(page,'Context and progress')

    def show_work(self,value):
        self.current=value;state=value['state'];plan=value['plan'];used=state['used'];budget=plan['budget']
        adaptive=plan.get('profile')=='ledger.adaptive-investigation/1'
        self.summary.setText(plan['title']+' · '+state['state'].replace('_',' ').lower()+'\n'+str(state.get('reason') or 'Within the frozen grant').replace('_',' ')+
            '\nAttempts %d/%d · active seconds %.1f/%d · reserved tokens %d/%d · changed files %d/%d' %
            (used['steps'],budget['steps'],used['seconds'],budget['seconds'],used['tokens'],budget['tokens'],len(used['files']),budget['files']))
        lines=['ORIGINAL REQUEST',plan['original_request'],'','SELECTED WORKING COPIES']
        for copy in plan['copies']:lines.append(plan['initial_copies'][copy]['work']+' · '+str(len(plan['initial_copies'][copy]['files']))+' admitted files')
        authority=('Adaptive choices among these operations: '+', '.join(plan['operations'])+'.' if adaptive else 'Only these exact steps, within the displayed budgets and expiry.')
        lines+=['','AUTHORITY',authority,'Original-file updates, exports and network calls are excluded.',
            'Working application is '+('included in this plan.' if 'changes.apply' in plan['operations'] else 'not included in this plan.'),
            'Grant expires: '+time.strftime('%Y-%m-%d %H:%M %Z',time.localtime(plan['expires'])),'','INPUTS']
        lines += [str(b.get('address') or b['operation'])+' · revision '+b['revision'][:16] for b in plan['sources']] or ['No additional assignment sources selected.']
        status={s['key']:s for s in value['steps']}
        completed = [item for item in value['steps'] if item['state'] == 'DONE']
        if completed:
            last = max(completed, key=lambda item: item.get('finished') or 0)
            self.checkpoint.setText(f"Saved checkpoint · {len(completed)} completed · last step {last['key']}")
        else:
            self.checkpoint.setText('Saved plan · ready to inspect before the first step')
        if adaptive:
            lines+=['','VERSIONED PROBLEM',json.dumps(state['problem'],indent=2),'','ADAPTIVE PROGRESS']
            for item in value['steps']:
                lines += [item['key']+' · '+item['operation']+' · '+item['state'].lower()]
                if item.get('reason'):lines.append('Stopped: '+str(item['reason']))
                if item.get('observation'):lines.append('Actual observation: '+item['observation'])
            lines+=['Inspect alternatives, owner questions and findings in Problem sheet → Investigate → Graphite investigation.']
        for step in plan['steps']:
            item=status[step['key']]
            lines+=['','STEP '+step['key']+' · '+item['state'].lower(),step['operation'],
                'After: '+(', '.join(step['after']) or 'No prerequisite')+' · seconds '+str(step['seconds'])+' · permitted retries '+str(step['retries']),
                json.dumps(step['arguments'],ensure_ascii=False,indent=2)]
            if step['require']:lines.append('Completion checks: '+json.dumps(step['require'],ensure_ascii=False))
            if item.get('reason'):lines.append('Stopped: '+item['reason'])
            result=item.get('result') or {}
            if isinstance(result,dict):
                if result.get('text') is not None:lines.append('Read result:\n'+result['text'])
                if result.get('proposal_id'):lines.append('Frozen proposal: '+result['proposal_id'])
                if result.get('schema')=='arc.change-set/1':lines.append('Frozen proposal: '+result['id']+' · '+str(len(result['changes']))+' file changes')
                if result.get('schema')=='arc.change-commit/1':lines.append('Working commit: '+result['id']+' · '+result['state'])
                if result.get('checks'):lines.append('Named checks: '+json.dumps(result['checks'],ensure_ascii=False,indent=2))
        lines+=['','RECENT PROGRESS']+[e['event'].replace('_',' ').lower() for e in value['events'][-12:]]
        position=self.review.verticalScrollBar().value();self.review.setPlainText('\n'.join(lines));self.review.verticalScrollBar().setValue(position);self.pages.setCurrentIndex(1)
        self.message.setText('Permission needed: inspect the exact frozen calls before authorizing.' if state['state']=='DRAFT' else 'The saved state and journal describe what ran and why it stopped.')

    def open(self,ident):
        value=self.call('work.get',{'id':ident})
        if value:self.show_work(value)

    def action(self,op,extra=None):
        if not self.current:return
        ident=self.current['plan']['id']
        def completed(value):
            self.open(ident);self.reload(pickers=False)
        self.run(op,{'id':ident,**(extra or {})},completed)

    def authorize(self):
        if self.current:self.action('work.authorize',{'expected_digest':self.current['content_digest']})

    def revoke(self):
        if self.current:self.action('work.revoke',{'reason':'Owner revoked remaining work authority'})

    def accept(self):
        text,ok=QInputDialog.getText(self,'Review completed work','What did you accept?')
        if ok:self.action('work.review',{'decision':'ACCEPT','note':text})

    def open_changes(self):
        from .change_sets_qt import show
        show(self.host)

    def full_record(self):
        if not self.current:return
        dialog=QDialog(self);dialog.setWindowTitle('Full frozen work record');dialog.resize(850,650)
        box=QVBoxLayout(dialog);text=QPlainTextEdit();text.setReadOnly(True);text.setPlainText(json.dumps(self.current,ensure_ascii=False,indent=2));box.addWidget(text);dialog.exec()

    def save_procedure(self):
        if not self.current:return
        title,ok=QInputDialog.getText(self,'Reusable procedure','Procedure name:')
        if not ok:return
        raw,ok=QInputDialog.getMultiLineText(self,'Parameters','Optional scalar argument bindings as JSON (see STAGE5.md):','{}')
        if not ok:return
        try:parameters=json.loads(raw)
        except ValueError:self.message.setText('Parameters must be JSON.');return
        self.run('procedures.save',{'work':self.current['plan']['id'],'title':title,'parameters':parameters},
            lambda value:self.message.setText('Saved '+value['title']+'. Each new instance needs its own reviewed grant.'))

    def instantiate(self):
        value=self.call('procedures.list')
        if not value or not value['records']:self.message.setText('Accept a completed order and save it as a procedure first.');return
        names=[p['title']+' · '+p['id'][:8] for p in value['records']]
        choice,ok=QInputDialog.getItem(self,'Instantiate a procedure','Procedure:',names,0,False)
        if not ok:return
        procedure=value['records'][names.index(choice)]
        text,ok=QInputDialog.getMultiLineText(self,'Parameter values','Supply each declared parameter as JSON:\n'+json.dumps(procedure['parameters'],indent=2),'{}')
        if not ok:return
        try:values=json.loads(text)
        except ValueError:self.message.setText('Values must be JSON.');return
        self.run('procedures.instantiate',{'id':procedure['id'],'assignment':self.assignments.currentData(),'copies':[self.copies.currentData()],
            'values':values,'title':self.name.text() or procedure['title'],'expires':time.time()+self.expiry.value()*3600,
            'budget':{'seconds':self.seconds.value(),'steps':self.steps.value(),'tokens':self.tokens.value(),'memory_mb':self.memory.value(),
                'output_bytes':1048576,'files':self.files.value()}},self.show_work)

    def build_workers(self):
        page=QWidget();box=QVBoxLayout(page)
        note=QLabel('A qualified profile passed real forbidden-access, network, memory, child-process and termination probes on this boot. Refusal means unavailable, never contained.')
        note.setWordWrap(True);box.addWidget(note)
        self.coverage=QPlainTextEdit();self.coverage.setReadOnly(True);self.coverage.setAccessibleName('Actual worker protection coverage');box.addWidget(self.coverage,1)
        row=QHBoxLayout()
        for profile in ('PARSER','CHECK','MODEL'):
            b=button('Qualify '+profile.lower(),'quiet');b.clicked.connect(lambda checked=False,p=profile:self.qualify(p));row.addWidget(b)
        box.addLayout(row);refresh=button('Refresh coverage','quiet');refresh.clicked.connect(self.refresh_workers);box.addWidget(refresh)
        stop=button('Stop my protected workers','quiet');stop.clicked.connect(lambda:self.run('workers.stop',{},lambda value:self.refresh_workers()));box.addWidget(stop)
        self.pages.addTab(page,'Worker protection')

    def refresh_workers(self):
        value=self.call('workers.status')
        if value:self.coverage.setPlainText(json.dumps(value,ensure_ascii=False,indent=2))

    def qualify(self,profile):
        def done(value):
            self.refresh_workers()
            detail=value.get('reason') or ('Every required probe passed on this computer.' if value['state']=='QUALIFIED' else 'Required protection was not established; inspect the failed probes.')
            self.message.setText(profile.lower()+' · '+value['state'].replace('_',' ').lower()+': '+detail)
        self.run('workers.qualify',{'profile':profile},done)

    def reload(self,pickers=True):
        if self.busy:return
        value=self.call('work.list')
        if value:
            self.orders.clear()
            paused = None
            for row in value['records']:
                item=QListWidgetItem(row['title']+'\n'+row['state'].replace('_',' ').lower());item.setData(Qt.UserRole,row['id']);self.orders.addItem(item)
                if self.current and row['id']==self.current['plan']['id']:self.orders.setCurrentItem(item)
                if paused is None and row['state'] == 'PAUSED':
                    paused = item
            if self.current is None and paused is not None:
                self.orders.setCurrentItem(paused)
                self.open(paused.data(Qt.UserRole))
        if pickers:
            self.assignments.clear()
            for a in (self.call('assignments.list') or {}).get('records',[]):self.assignments.addItem(a['original_request'][:80],a['id'])
            copies=(self.call('changes.workspaces') or {}).get('workspaces',[])
            self.copies.blockSignals(True);self.copies.clear()
            for c in copies:self.copies.addItem(c['name'],c['id'])
            self.copies.blockSignals(False)
            self.model.clear()
            for m in (self.call('brain.models') or {}).get('models',[]):self.model.addItem(m.get('label') or m.get('name') or m['id'],m['id'])
            self.refresh_workers()
            if self.copies.currentData():self.copy_changed()

    def refresh_current(self):
        if self.busy or not self.current:return
        value=self.call('work.get',{'id':self.current['plan']['id']})
        if value and value!=self.current:
            page=self.pages.currentIndex();self.show_work(value);self.pages.setCurrentIndex(page);self.reload(pickers=False)


def show(host,ident=None):
    host._close_start()
    for i in range(host.tabs.count()):
        tab=host.tabs.widget(i)
        if isinstance(tab,WorkTab):
            host.tabs.setCurrentWidget(tab)
            if ident:tab.open(ident)
            return tab
    tab=WorkTab(host);host.tabs.addTab(tab,tab.title());host.tabs.setCurrentWidget(tab)
    if ident:tab.open(ident)
    return tab
