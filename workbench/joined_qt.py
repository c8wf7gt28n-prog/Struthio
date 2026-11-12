"""Connected findings, checked methods and an owned native working-file view."""
from .text_prompts import writing_prompt
from PySide6.QtCore import Qt,QTimer
from PySide6.QtGui import QGuiApplication,QWindow
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QLabel,QComboBox,
    QLineEdit,QTreeWidget,QTreeWidgetItem,QTabWidget,QTableWidget,QTableWidgetItem,QCheckBox,QHeaderView)
from .shell2 import button


class JoinedPane(QWidget):
    def __init__(self,pane):
        super().__init__();self.pane=pane;self.active=None;self.selected=None;self.session=None;self.pending=None
        self.native_window=None;self.native_container=None;self.reopen_after=False
        box=QVBoxLayout(self)
        self.status=QLabel('Select a checked lifetime result, then carry it through the applications.');self.status.setWordWrap(True);self.status.setTextFormat(Qt.PlainText);box.addWidget(self.status)
        self.schedules=QComboBox();self.schedules.setAccessibleName('Actual checked schedule receipt');box.addWidget(self.schedules)
        row=QHBoxLayout()
        for text,slot in [('Run across applications',self.run_chain),('Refresh',self.reload)]:
            b=button(text,'primary' if text.startswith('Run') else 'quiet');b.clicked.connect(slot);row.addWidget(b)
        box.addLayout(row);self.jobs=QComboBox();self.jobs.setAccessibleName('Connected application investigations');self.jobs.currentIndexChanged.connect(self.show);box.addWidget(self.jobs)
        self.tabs=QTabWidget();box.addWidget(self.tabs,1)
        page=QWidget();layout=QVBoxLayout(page);self.tabs.addTab(page,'Findings')
        self.finding=QLabel('No checked findings selected.');self.finding.setWordWrap(True);self.finding.setTextFormat(Qt.PlainText);layout.addWidget(self.finding)
        self.why=QTreeWidget();self.why.setHeaderLabels(['Inspect','Current record']);self.why.header().setSectionResizeMode(QHeaderView.ResizeToContents);self.why.header().setStretchLastSection(True);layout.addWidget(self.why,1)
        page=QWidget();layout=QVBoxLayout(page);self.tabs.addTab(page,'Methods')
        self.title=QLineEdit();writing_prompt(self.title, 'Method title');self.title.setAccessibleName('Checked method title');layout.addWidget(self.title)
        self.methods=QComboBox();self.methods.setAccessibleName('Proposed and accepted methods');self.methods.currentIndexChanged.connect(self.show_method);layout.addWidget(self.methods)
        self.method_details=QTreeWidget();self.method_details.setHeaderLabels(['Method record','Declared check or condition']);self.method_details.header().setSectionResizeMode(0,QHeaderView.ResizeToContents);self.method_details.header().setStretchLastSection(True);self.method_details.setMaximumHeight(220);layout.addWidget(self.method_details)
        row=QHBoxLayout()
        for text,slot in [('Save proposed method',self.save_method),('Accept selected method',self.accept_method)]:
            b=button(text,'quiet');b.clicked.connect(slot);row.addWidget(b)
        layout.addLayout(row)
        form=QFormLayout();self.capacity=QComboBox();self.capacity.setAccessibleName('Transfer capacity quantity');self.capacity.currentIndexChanged.connect(self.mapping_rows);form.addRow('Capacity',self.capacity);layout.addLayout(form)
        self.mapping=QTableWidget(0,3);self.mapping.setHorizontalHeaderLabels(['Allocation','Unit','Lifetime']);self.mapping.setAccessibleName('Explicit structural transfer mapping');self.mapping.horizontalHeader().setStretchLastSection(True);layout.addWidget(self.mapping,1)
        self.profile=QCheckBox('Confirm this mapping meets the declared model assumptions');layout.addWidget(self.profile)
        assumptions=QLabel('Additive constant demands, fixed capacity and half-open lifetimes. No additional overhead, fragmentation or indivisibility check is required for this model.');assumptions.setWordWrap(True);layout.addWidget(assumptions)
        self.basis=QLineEdit();writing_prompt(self.basis, 'Basis for these model assumptions');self.basis.setAccessibleName('Transfer precondition basis');layout.addWidget(self.basis)
        row=QHBoxLayout()
        for text,slot in [('Preview mapping',self.preview),('Run method across applications',self.run_method)]:
            b=button(text,'primary' if text.startswith('Run') else 'quiet');b.clicked.connect(slot);row.addWidget(b)
        layout.addLayout(row)
        page=QWidget();self.native_layout=QVBoxLayout(page);self.tabs.addTab(page,'Working file')
        row=QHBoxLayout()
        for text,slot in [('Open working file',self.open_file),('Recalculate in view',lambda:self.control('recalculate')),('Close owned file',self.close_owned)]:
            b=button(text,'quiet');b.clicked.connect(slot);row.addWidget(b)
        self.native_layout.addLayout(row);row=QHBoxLayout()
        for text,slot in [('Pause',lambda:self.control('pause')),('Take over',lambda:self.control('takeover')),('Resume',lambda:self.control('resume')),('Recheck edited inputs',self.refresh_edited)]:
            b=button(text,'quiet');b.clicked.connect(slot);row.addWidget(b)
        self.native_layout.addLayout(row)
        self.native_status=QLabel('Open an owned Calc working file to inspect or take over.');self.native_status.setWordWrap(True);self.native_status.setTextFormat(Qt.PlainText);self.native_layout.addWidget(self.native_status)
        self.native_placeholder=QLabel('The actual owned Calc window appears here on X11.');self.native_placeholder.setAlignment(Qt.AlignCenter);self.native_layout.addWidget(self.native_placeholder,1)
        self.timer=QTimer(self);self.timer.setInterval(750);self.timer.timeout.connect(self.poll)

    def call(self,op,args=None):return self.pane.call(op,args)

    def reload(self,*unused):
        problem=self.pane.current
        if not problem:self.jobs.clear();self.schedules.clear();self.capacity.clear();return
        value=self.call('joined.list',{'problem':problem['id']}) or {};old=self.jobs.currentData();self.jobs.blockSignals(True);self.jobs.clear()
        for row in value.get('jobs',[]):self.jobs.addItem(row['state']+' · '+row['id'][:8],row['id'])
        if self.jobs.findData(old)>=0:self.jobs.setCurrentIndex(self.jobs.findData(old))
        self.jobs.blockSignals(False)
        self.schedules.clear()
        for receipt in value.get('schedules',[]):
            snap=receipt['snapshot']
            self.schedules.addItem('Revision '+str(receipt['problem_revision'])+' · '+snap['state']+' · peak '+snap.get('peak',{}).get('rational','?')+' '+snap.get('peak',{}).get('unit',''),receipt)
        methods=self.call('methods.list') or {};old=self.methods.currentData();self.methods.clear()
        for method in methods.get('methods',[]):self.methods.addItem(method['title']+' · '+method['state'].lower()+' · revision '+str(method['revision']),method)
        if old:
            for i in range(self.methods.count()):
                if self.methods.itemData(i)['id']==old['id']:self.methods.setCurrentIndex(i);break
        self.capacity.blockSignals(True);old=self.capacity.currentData();self.capacity.clear()
        for v in problem['variables']:
            if v['type']=='quantity' and v['state']=='KNOWN':self.capacity.addItem(v['name']+' · '+v['unit'],v['name'])
        if self.capacity.findData(old)>=0:self.capacity.setCurrentIndex(self.capacity.findData(old))
        elif self.schedules.currentData():self.capacity.setCurrentIndex(self.capacity.findData(self.schedules.currentData()['arguments']['capacity']))
        self.capacity.blockSignals(False);self.mapping_rows();self.show()

    def show_method(self,*unused):
        self.method_details.clear();method=self.methods.currentData()
        if not method:return
        value=self.call('methods.get',{'id':method['id']})
        if not value:return
        for title,items in [('Typed inputs',value['typed_inputs']),('Preconditions',value['preconditions']),
                ('Expected checks',value['expected_checks']),('Failure cases',value['failure_cases']),
                ('Steps',[step['operation'] for step in value['steps']]),
                ('Evidence',[value['source_job'],value['evidence_digest']]),
                ('History',['Revision '+str(row['revision'])+' · '+row['state'].lower() for row in value['history']]),
                ('Authority',['A saved method carries no execution grant. Each mapping rechecks its inputs and preconditions.'])]:
            parent=QTreeWidgetItem([title,'']);self.method_details.addTopLevelItem(parent)
            for label,text in (items.items() if isinstance(items,dict) else [('',item) for item in items]):parent.addChild(QTreeWidgetItem([str(label),str(text)]))
        self.method_details.topLevelItem(1).setExpanded(True)

    def mapping_rows(self,*unused):
        self.mapping.setRowCount(0);problem=self.pane.current
        if not problem:return
        lives=[v['name'] for v in problem['variables'] if v['type']=='interval' and v['state']=='KNOWN']
        receipt=self.schedules.currentData();pairs={v['quantity']:v['lifetime'] for v in receipt['arguments']['allocations']} if receipt else {}
        for v in problem['variables']:
            if v['type']!='quantity' or v['state']!='KNOWN' or v['name']==self.capacity.currentData():continue
            row=self.mapping.rowCount();self.mapping.insertRow(row)
            for col,text in enumerate((v['name'],v['unit'])):
                item=QTableWidgetItem(text);item.setFlags(item.flags()&~Qt.ItemIsEditable);self.mapping.setItem(row,col,item)
            combo=QComboBox();combo.addItem('Choose lifetime',None)
            combo.addItem('Exclude from this mapping','__skip__')
            for life in lives:combo.addItem(life,life)
            if v['name'] in pairs:combo.setCurrentIndex(combo.findData(pairs[v['name']]))
            self.mapping.setCellWidget(row,2,combo)

    def select_job(self,ident):
        index=self.jobs.findData(ident)
        if index>=0:self.jobs.setCurrentIndex(index)
        self.selected=ident;self.show()

    def show(self,*unused):
        ident=self.jobs.currentData();self.selected=ident;self.why.clear()
        if not ident:self.finding.setText('No checked findings selected.');return
        value=self.call('joined.explain',{'job':ident})
        if not value:return
        self.finding.setText(value.get('finding',value['state'])+('\nNeeds rechecking: '+str(value.get('reason')) if value.get('reason') else ''))
        why=QTreeWidgetItem(['Why',value['state']]);self.why.addTopLevelItem(why)
        for item in value.get('why',[]):
            artifact=item['artifact'];child=QTreeWidgetItem([artifact['type'].replace('_',' ').title(),item['applicability']+' · revision '+str(artifact['revision'])]);why.addChild(child)
            child.addChild(QTreeWidgetItem(['Receipt',artifact['id']]))
            child.addChild(QTreeWidgetItem(['Bytes',artifact['sha256']]))
            child.addChild(QTreeWidgetItem(['Working file',item['working_file']]))
            for version in item.get('versions',[]):child.addChild(QTreeWidgetItem(['Retained revision '+str(version['revision']),version['sha256']]))
        for title,items in [('Alternatives',value.get('alternatives',[])),('What if',[value.get('what_if','No current scenario is selected.')]),('What is missing',value.get('missing') or ['No unknown inputs are declared for this result.'])]:
            parent=QTreeWidgetItem([title,'']);self.why.addTopLevelItem(parent)
            for text in items:parent.addChild(QTreeWidgetItem([str(text),'']))
        why.setExpanded(True)

    def run_chain(self):
        receipt=self.schedules.currentData()
        if not receipt:self.status.setText('Keep an actual current schedule result in Graphite investigation first.');return
        plan=self.call('joined.prepare',{'receipt':receipt['id'],'copy':self.pane.current['sources'][0]['copy']})
        if plan:self.track(self.call('joined.run',{'action':plan['id'],'expected_digest':plan['binding_digest']}),'joined.result')

    def track(self,job,endpoint):
        if job:self.active=(job['id'],endpoint);self.status.setText('Running the selected checked workflow.');self.timer.start()

    def save_method(self):
        if not self.selected:return
        method=self.call('methods.propose',{'job':self.selected,'title':self.title.text().strip() or self.pane.current['title']+' capacity method'})
        if method:self.reload();self.status.setText('Method saved as a proposal. Review its declared preconditions and linked checks before accepting it.')

    def accept_method(self):
        method=self.methods.currentData()
        if not method:return
        result=self.call('methods.accept',{'id':method['id'],'expected_revision':method['revision'],'note':'Owner accepted the declared capacity profile and linked application checks.'})
        if result:self.reload();self.status.setText('Method accepted. A new mapping still checks its inputs, units and preconditions before running.')

    def mapping_args(self):
        from .checked_methods import EXPECTED
        method=self.methods.currentData()
        if not method or not self.profile.isChecked() or not self.basis.text().strip():
            self.status.setText('Choose an accepted method, confirm its model assumptions and state their basis.');return None
        pairs=[]
        for row in range(self.mapping.rowCount()):
            life=self.mapping.cellWidget(row,2).currentData()
            if life=='__skip__':continue
            if not life:self.status.setText('Choose a declared lifetime for every selected allocation.');return None
            pairs.append({'quantity':self.mapping.item(row,0).text(),'lifetime':life})
        return {**self.pane.bound(),'method':method['id'],'method_revision':method['revision'],
            'capacity':self.capacity.currentData(),'allocations':pairs,'declarations':{**EXPECTED,'basis':self.basis.text().strip()}}

    def preview(self):
        args=self.mapping_args()
        if not args:return
        value=self.call('methods.preview',args)
        if value:self.status.setText('Mapping '+value['state'].lower()+': '+str(value.get('reason') or value.get('snapshot',{}).get('state')))

    def run_method(self):
        args=self.mapping_args()
        if not args:return
        action=self.call('methods.instantiate',args)
        if action:
            self.pending={'copy':self.pane.current['sources'][0]['copy']}
            self.track(self.call('methods.run',{'action':action['id'],'expected_digest':action['binding_digest']}),'methods.result')

    def open_file(self):
        if not self.selected:return
        value=self.call('joined.session.open',{'job':self.selected})
        if value:self.session=value['session']['id'];self.tabs.setCurrentIndex(2);self.timer.start();self.attach(value)

    def attach(self,value):
        self.session=value['session']['id']
        status=value.get('native');self.native_status.setText(value['session']['mode'].lower().replace('_',' ')+' · saved working copy · '+str(value['lease_remaining'])+' seconds in this session')
        if not status or value['session']['mode']=='CLOSED' or self.native_window or QGuiApplication.platformName()!='xcb':return
        self.native_window=QWindow.fromWinId(status['window_id'])
        if self.native_window:
            self.native_container=QWidget.createWindowContainer(self.native_window,self);self.native_container.setMinimumHeight(380)
            self.native_container.setFocusPolicy(Qt.StrongFocus);self.native_placeholder.hide();self.native_layout.addWidget(self.native_container,1)

    def detach(self):
        if self.native_window:
            try:self.native_window.setParent(None)
            except RuntimeError:pass
        if self.native_container:
            self.native_layout.removeWidget(self.native_container);self.native_container.deleteLater()
        self.native_window=None;self.native_container=None;self.native_placeholder.show()

    def control(self,op):
        if not self.session:return None
        value=self.call('joined.session.get',{'id':self.session})
        if not value:return None
        result=self.call('joined.session.'+op,{'id':self.session,'expected_revision':value['session']['revision']})
        if result:
            self.attach(result)
            if result.get('refresh_required'):self.native_status.setText('This working revision changed. Recheck edited inputs before continuing; earlier findings remain available as history.')
            self.show()
        return result

    def close_owned(self):
        if self.session:
            self.control('close');self.session=None
        self.detach()

    def refresh_edited(self):
        if not self.session:return
        value=self.call('joined.session.get',{'id':self.session})
        if not value:return
        result=self.call('joined.session.refresh',{'id':self.session,'expected_revision':value['session']['revision'],
            'note':'Owner requested rechecking the edited numeric inputs from the native working-file view.'})
        if result:
            plan=result['prepared'];self.close_owned();self.reopen_after=True
            self.pane.reload(self.pane.current['id'])
            self.track(self.call('joined.run',{'action':plan['id'],'expected_digest':plan['binding_digest']}),'joined.result')

    def poll(self):
        if self.active:
            ident,endpoint=self.active;value=self.call(endpoint,{'job':ident})
            if value:
                self.status.setText(value.get('progress',{}).get('stage',value['state']))
                if value['state'] not in ('Running','Queued'):
                    self.active=None
                    if endpoint=='methods.result' and value['state']=='AVAILABLE':
                        plan=self.call('joined.prepare',{'receipt':value['receipt']['receipt'],'copy':self.pending['copy'],'method_job':ident})
                        self.pending=None
                        if plan:self.track(self.call('joined.run',{'action':plan['id'],'expected_digest':plan['binding_digest']}),'joined.result')
                    else:
                        self.reload();self.select_job(ident)
                        if self.reopen_after and value['state']=='AVAILABLE':self.reopen_after=False;self.open_file()
        if self.session:
            value=self.call('joined.session.get',{'id':self.session})
            if value:
                if value['job_state'] in ('Running','Queued'):self.attach(value)
                else:self.native_status.setText('Session ended; the saved working copy and its history remain available.'+(' '+value['reason'] if value.get('reason') else ''))
        if not self.active and not self.session:self.timer.stop()
