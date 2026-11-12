"""A visible adaptive investigation within the existing problem workspace."""
from .text_prompts import writing_prompt
import json,time
from PySide6.QtCore import Qt,QTimer
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QComboBox,QLabel,
    QPlainTextEdit,QTableWidget,QTableWidgetItem,QHeaderView,QSpinBox,QLineEdit,QMenu,QAbstractItemView)
from .shell2 import button


def operations_for(profile):
    from .adaptive_contract import OPS,DEFAULT_OPS
    if profile==1:return [op for op in OPS if not op.startswith(('joined.','methods.'))]
    if profile==3:return ['work.read','methods.preview','methods.instantiate','methods.run','methods.result','joined.prepare','joined.run','joined.result']
    return list(DEFAULT_OPS)


class AdaptivePane(QWidget):
    def __init__(self,pane):
        super().__init__();self.pane=pane;self.current=None;self.context=None
        box=QVBoxLayout(self);self.status=QLabel('Prepare a bounded investigation, then start it with the displayed scope.');self.status.setWordWrap(True);self.status.setTextFormat(Qt.PlainText);box.addWidget(self.status)
        form=QFormLayout();self.profile=QComboBox();self.profile.addItems(['Read and calculate','Working-copy tools','Direct response allowed','Checked methods and applications']);form.addRow('Tools',self.profile)
        row=QHBoxLayout();self.steps=QSpinBox();self.steps.setRange(2,64);self.steps.setValue(20);row.addWidget(QLabel('Steps'));row.addWidget(self.steps)
        self.minutes=QSpinBox();self.minutes.setRange(1,60);self.minutes.setValue(10);row.addWidget(QLabel('Minutes'));row.addWidget(self.minutes)
        self.tokens=QSpinBox();self.tokens.setRange(8192,1000000);self.tokens.setSingleStep(8192);self.tokens.setValue(80000);row.addWidget(QLabel('Tokens'));row.addWidget(self.tokens);form.addRow('Limits',row);box.addLayout(form)
        self.profile.currentIndexChanged.connect(self.profile_changed)
        row=QHBoxLayout()
        for title,slot in [('Prepare investigation',self.prepare),('Start with this scope',self.authorize),('Refresh',self.reload)]:
            b=button(title,'primary' if title.startswith('Start') else 'quiet');b.clicked.connect(slot);row.addWidget(b)
        box.addLayout(row);self.orders=QComboBox();self.orders.setAccessibleName('Saved adaptive investigation');self.orders.currentIndexChanged.connect(self.open);box.addWidget(self.orders)
        self.scope=QLabel();self.scope.setWordWrap(True);self.scope.setTextFormat(Qt.PlainText);box.addWidget(self.scope)
        row=QHBoxLayout()
        for title,slot in [('Pause',lambda:self.control('work.pause')),('Resume',lambda:self.control('work.resume')),('Revoke',lambda:self.control('work.revoke'))]:
            b=button(title,'quiet');b.clicked.connect(slot);row.addWidget(b)
        box.addLayout(row)
        self.rationale=QLabel();self.rationale.setWordWrap(True);self.rationale.setTextFormat(Qt.PlainText);self.rationale.setAccessibleName('Reason for the next action');box.addWidget(self.rationale)
        self.frontier=QTableWidget(0,4);self.frontier.setHorizontalHeaderLabels(['Alternative','State','Assumptions','Context']);self.frontier.setAccessibleName('Investigation alternatives and rejected branches');self.frontier.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents);self.frontier.horizontalHeader().setStretchLastSection(True);self.frontier.setMaximumHeight(190);box.addWidget(self.frontier)
        self.observations=QTableWidget(0,3);self.observations.setHorizontalHeaderLabels(['Actual operation','Outcome','Result']);self.observations.setAccessibleName('Actual observations before the next model decision');self.observations.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents);self.observations.horizontalHeader().setStretchLastSection(True);self.observations.setMaximumHeight(160)
        self.observations.setContextMenuPolicy(Qt.CustomContextMenu);self.observations.customContextMenuRequested.connect(self.menu);box.addWidget(self.observations)
        for table in (self.frontier,self.observations):table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.frontier.setContextMenuPolicy(Qt.CustomContextMenu);self.frontier.customContextMenuRequested.connect(self.frontier_menu)
        self.question=QLabel();self.question.setWordWrap(True);self.question.setTextFormat(Qt.PlainText);self.question.setAccessibleName('Discriminating missing-input question');box.addWidget(self.question)
        self.inputs=QTableWidget(0,4);self.inputs.setHorizontalHeaderLabels(['Lifetime','Start','Stop','Time unit']);self.inputs.setAccessibleName('Owner-supplied half-open lifetimes');self.inputs.horizontalHeader().setStretchLastSection(True);self.inputs.setMaximumHeight(140);box.addWidget(self.inputs)
        self.note=QLineEdit();writing_prompt(self.note, 'Basis for these lifetimes');self.note.setAccessibleName('Lifetime answer basis');box.addWidget(self.note)
        b=button('Supply these lifetimes','primary');b.clicked.connect(self.answer);box.addWidget(b)
        self.detail=QPlainTextEdit();self.detail.setReadOnly(True);self.detail.setAccessibleName('Proposed finding and expandable receipt details');self.detail.setMinimumHeight(100);box.addWidget(self.detail,1)
        self.timer=QTimer(self);self.timer.setInterval(1200);self.timer.timeout.connect(self.poll)

    def call(self,op,args=None):return self.pane.call(op,args)

    def profile_changed(self,index):
        if index!=3:return
        for widget,previous,suggested in ((self.steps,20,32),(self.minutes,10,30),(self.tokens,80000,240000)):
            if widget.value()==previous:widget.setValue(suggested)
        self.status.setText('Finish with checked application outputs or a checked unsupported-method finding. Review the displayed limits before starting.')

    def reload(self):
        problem=self.pane.current
        if not problem:self.current=None;self.orders.clear();return
        value=self.call('work.list') or {};selected=self.current['plan']['id'] if self.current else None
        self.orders.blockSignals(True);self.orders.clear()
        for row in value.get('records',[]):
            full=self.call('work.get',{'id':row['id']})
            if full and full['plan'].get('adaptive',{}).get('problem',{}).get('id')==problem['id']:self.orders.addItem(full['plan']['title'],row['id'])
        if self.orders.findData(selected)>=0:self.orders.setCurrentIndex(self.orders.findData(selected))
        self.orders.blockSignals(False);self.open()

    def prepare(self):
        if not self.pane.lab.saved():return
        status=self.call('brain.status')
        if not status or status['state']!='READY':self.status.setText('Choose and start a local model in Brain first.');return
        config=status['selection']['config'];copies=sorted({s['copy'] for s in self.pane.current['sources']})
        if not copies and self.pane.copies.currentData():copies=[self.pane.copies.currentData()]
        ops=operations_for(self.profile.currentIndex())
        completion={}
        if self.profile.currentIndex()==3:
            from .adaptive_contract import APPLICATION_COMPLETION
            completion={'completion':APPLICATION_COMPLETION}
        value=self.call('work.investigate',{**self.pane.bound(),'copies':copies,'operations':ops,'title':self.pane.current['title']+' investigation',
            **completion,
            'budget':{'steps':self.steps.value(),'seconds':60*self.minutes.value(),'tokens':self.tokens.value(),'memory_mb':config['memory_mb'],'output_bytes':4194304,'files':20},
            'limits':{'frontier':8,'decisions':16,'max_tokens':768,'decision_seconds':180,'failures':3},'expires':time.time()+86400,'allow_direct':self.profile.currentIndex()==2})
        if value:self.current=value;self.reload();self.orders.setCurrentIndex(self.orders.findData(value['plan']['id']))

    def authorize(self):
        if not self.current:return
        value=self.call('work.authorize',{'id':self.current['plan']['id'],'expected_digest':self.current['content_digest']})
        if value:self.open()

    def open(self,*args):
        ident=self.orders.currentData()
        if not ident:self.current=None;return
        value=self.call('work.investigation',{'id':ident})
        if not value:return
        self.current=value;state=value['state'];plan=value['plan']
        labels={'DRAFT':'Prepared; waiting for your scoped start','READY':'Investigation active','WAITING':'Waiting for input or review','PAUSED':'Paused','REVIEW':'Proposed finding ready for review','LIMIT':'Stopped at a limit','REVOKED':'Grant revoked'}
        self.status.setText(labels.get(state['state'],state['state'])+' · '+(state.get('reason') or '').lower().replace('_',' '))
        self.scope.setText('Copies: %d · Tools: %s\nLimits: %d steps, %d seconds, %d tokens. Used: %d steps, %d tokens.'%(len(plan['copies']),', '.join(plan['operations']),plan['budget']['steps'],plan['budget']['seconds'],plan['budget']['tokens'],state['used']['steps'],state['used']['tokens']))
        from .adaptive_contract import APPLICATION_COMPLETION
        if plan['adaptive'].get('completion')==APPLICATION_COMPLETION:
            self.scope.setText(self.scope.text()+'\nFinish: checked application outputs, or a current verified method-precondition refusal.')
        rationale=value['decisions'][-1]['candidate'] if value['decisions'] else state.get('last_rationale',{})
        self.rationale.setText(('Decision uncertainty: '+rationale.get('uncertainty','')+'\nPredicted distinctions: '+'; '.join(rationale.get('expected',[]))) if rationale else 'The next model decision follows the actual observations below.')
        self.frontier.setRowCount(0)
        for branch in state['frontier']:
            row=self.frontier.rowCount();self.frontier.insertRow(row)
            for col,text in enumerate((branch['hypothesis'],branch['status'].lower().replace('_',' '),'; '.join(branch['assumptions']),('historical · ' if branch.get('historical') else '')+'revision '+str(branch['problem_revision']))):
                item=QTableWidgetItem(text);item.setToolTip(branch.get('reason',branch['hypothesis']));self.frontier.setItem(row,col,item)
            self.frontier.item(row,0).setData(Qt.UserRole,branch)
        self.observations.setRowCount(0)
        for obs in value['observations']:
            row=self.observations.rowCount();self.observations.insertRow(row)
            historical=obs['context_digest']!=state['problem']['expected_context_digest']
            outcome=('historical · ' if historical else '')+obs['outcome'].lower()
            for col,text in enumerate((obs['operation'],outcome,self.result_text(obs['summary']))):
                item=QTableWidgetItem(text);item.setToolTip('Problem revision '+str(obs['problem_revision'])+' · '+obs['id']);self.observations.setItem(row,col,item)
            self.observations.item(row,0).setData(Qt.UserRole,obs)
        question=state.get('question');old=self.inputs.property('question')
        self.question.setText(question['text'] if question else 'No owner input is currently requested.')
        if old!=(question or {}).get('id'):
            self.inputs.setProperty('question',(question or {}).get('id'));self.inputs.setRowCount(0)
            for name in (question or {}).get('missing',[]):
                row=self.inputs.rowCount();self.inputs.insertRow(row)
                for col,text in enumerate((name,'','','s')):self.inputs.setItem(row,col,QTableWidgetItem(text))
                self.inputs.item(row,0).setFlags(self.inputs.item(row,0).flags()&~Qt.ItemIsEditable)
        finding=state.get('finding');self.detail.setPlainText('Graphite proposes:\n'+finding['text']+'\n\nUnreviewed interpretation; actual observation identities remain available.' if finding else 'Right-click an actual observation to inspect its retained receipt.')
        if state['state']=='READY':self.timer.start()
        else:self.timer.stop()

    @staticmethod
    def result_text(value):
        if value.get('kind')=='method_preview':
            return 'Preconditions supported · method execution pending' if value['state']=='SUPPORTED' else 'Method preconditions unsupported' if value.get('precondition_rejected') else 'Precondition check unavailable · inspect the retained reason'
        if value.get('authority')=='PREPARED_DESCRIPTOR_NOT_EXECUTION_RESULT':return 'Prepared · execution pending'
        snapshot=value.get('snapshot',{})
        if 'peak' in snapshot:return '%s · peak %s %s'%(snapshot['state'],snapshot['peak']['rational'],snapshot['peak']['unit'])
        if 'outputs' in snapshot:
            out=snapshot['outputs'][0]
            if 'left' in out:return '%s · %s %s versus %s %s'%(snapshot['state'],out['left']['rational'],out['left']['unit'],out['right']['rational'],out['right']['unit'])
        return json.dumps(value,ensure_ascii=False)[:500]

    def poll(self):
        if not self.current:return
        self.call('work.advance',{'id':self.current['plan']['id']});self.open()

    def control(self,op):
        if not self.current:return
        args={'id':self.current['plan']['id']}
        if op=='work.revoke':args['reason']='Owner revoked the investigation grant.'
        if self.call(op,args):self.open()

    def answer(self):
        if not self.current or not self.current['state'].get('question'):return
        state=self.current['state'];values={}
        for row in range(self.inputs.rowCount()):values[self.inputs.item(row,0).text()]={key:self.inputs.item(row,col).text() for key,col in (('start',1),('stop',2),('unit',3))}
        value=self.call('work.answer',{'id':self.current['plan']['id'],'question':state['question']['id'],
            'expected_revision':state['problem']['expected_revision'],'expected_context_digest':state['problem']['expected_context_digest'],
            'lifetimes':values,'note':self.note.text() or 'Owner supplied in the investigation view.'})
        if value:
            # Refresh the same problem revision in the surrounding shared sheet.
            self.pane.open(state['problem']['id'])

    def menu(self,point):
        row=self.observations.rowAt(point.y());menu=self.menu_for_row(row)
        if menu:menu.exec(self.observations.viewport().mapToGlobal(point))

    def menu_for_row(self,row):
        if row<0:return None
        obs=self.observations.item(row,0).data(Qt.UserRole);menu=QMenu(self)
        action=menu.addAction('Inspect retained actual observation');action.triggered.connect(lambda:self.detail.setPlainText(json.dumps(obs,indent=2)))
        action=menu.addAction('Show the question this action addressed');action.triggered.connect(lambda:self.detail.setPlainText(json.dumps(self.action_context(obs),indent=2)))
        return menu

    def action_context(self,obs):
        value=self.current or {};steps=value.get('steps',[])
        index=next((i for i,s in enumerate(steps) if s['key']==obs['step']),0)
        decisions={d['turn']:d for d in value.get('decisions',[])}
        for step in reversed(steps[:index]):
            decision=decisions.get(step['key'])
            if decision:
                proposal=decision['candidate']
                return {'decision':decision['id'],'uncertainty':proposal['uncertainty'],'predicted_distinctions':proposal['expected'],
                    'proposed_action':proposal['next'],'authority':'Model proposal; actual result is in the retained observation.'}
        return {'notice':'No preceding model proposal is recorded for this action.','observation':obs['id']}

    def frontier_menu(self,point):
        menu=self.frontier_menu_for_row(self.frontier.rowAt(point.y()))
        if menu:menu.exec(self.frontier.viewport().mapToGlobal(point))

    def frontier_menu_for_row(self,row):
        if row<0 or row>=self.frontier.rowCount():return None
        branch=self.frontier.item(row,0).data(Qt.UserRole);menu=QMenu(self)
        action=menu.addAction('Inspect retained alternative');action.triggered.connect(lambda:self.detail.setPlainText(json.dumps(branch,indent=2)))
        if branch.get('decision'):
            decision=next((d for d in self.current['decisions'] if d['id']==branch['decision']),None)
            if decision:
                updates=[u for u in decision['candidate']['updates'] if u['candidate']==branch['key']]
                action=menu.addAction('Why Graphite changed this alternative');action.triggered.connect(lambda:self.detail.setPlainText(json.dumps({'interpretations':updates,'authority':'Model proposal for its recorded case; inspect the actual observations.'},indent=2)))
        if branch.get('observations'):
            aliases={'O'+str(i+1):o for i,o in enumerate(self.current['observations'])}
            observations=[aliases[a] for a in dict.fromkeys(branch['observations']) if a in aliases]
            action=menu.addAction('Inspect cited actual observations');action.triggered.connect(lambda:self.detail.setPlainText(json.dumps(observations,indent=2)))
        return menu
