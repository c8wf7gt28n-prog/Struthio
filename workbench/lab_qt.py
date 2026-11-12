"""Experiments and Why/Alternatives inside the shared Project Desk problem."""
import json
from PySide6.QtCore import Qt,QTimer
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QLabel,QLineEdit,
    QPlainTextEdit,QComboBox,QTableWidget,QTableWidgetItem,QHeaderView,QMenu,QTabWidget)
from .shell2 import button


class LabPane(QWidget):
    def __init__(self,pane):
        super().__init__();self.pane=pane;self.active=None;self.selected_result=None;self.graph=None;self.context=None
        box=QVBoxLayout(self);self.status=QLabel();self.status.setWordWrap(True);self.status.setTextFormat(Qt.PlainText);box.addWidget(self.status)
        tabs=QTabWidget();box.addWidget(tabs,1);run=QWidget();layout=QVBoxLayout(run);tabs.addTab(run,'Experiment bench')
        row=QHBoxLayout()
        for title,slot in [('Qualify Python on this host',self.qualify),('Create experiment in selected copy',self.create)]:
            b=button(title,'quiet');b.clicked.connect(slot);row.addWidget(b)
        layout.addLayout(row);form=QFormLayout();layout.addLayout(form)
        self.script=QLineEdit();self.script.setAccessibleName('Selected experiment script');form.addRow('Python file',self.script)
        self.parameters=QPlainTextEdit();self.parameters.setAccessibleName('Frozen experiment parameters');self.parameters.setMaximumHeight(135);form.addRow('Parameters',self.parameters)
        row=QHBoxLayout();b=button('Freeze and run experiment','primary');b.clicked.connect(self.run_python);row.addWidget(b)
        b=button('Cancel active job','quiet');b.clicked.connect(self.cancel);row.addWidget(b);layout.addLayout(row)
        self.board=QLineEdit('clock_board.kicad_pcb');self.board.setAccessibleName('Selected native board');form=QFormLayout();form.addRow('Board file',self.board);layout.addLayout(form)
        b=button('Check board and export outline','quiet');b.clicked.connect(self.run_board);layout.addWidget(b)
        self.jobs=QComboBox();self.jobs.setAccessibleName('Retained experiment attempts');self.jobs.currentIndexChanged.connect(self.show_result);layout.addWidget(self.jobs)
        self.output=QPlainTextEdit();self.output.setReadOnly(True);self.output.setAccessibleName('Actual experiment output');layout.addWidget(self.output,1)
        b=button('Keep generated outputs in this copy','quiet');b.clicked.connect(self.publish);layout.addWidget(b)
        why=QWidget();layout=QVBoxLayout(why);tabs.addTab(why,'Why and alternatives')
        note=QLabel('Compare retained observations, inspect alternative reasons, and keep disagreement visible. Proposed links describe the declared model and assumptions.');note.setWordWrap(True);layout.addWidget(note)
        self.math=QComboBox();self.math.setAccessibleName('Exact memory comparison receipt');layout.addWidget(self.math)
        self.python=QComboBox();self.python.setAccessibleName('Executed memory comparison receipt');layout.addWidget(self.python)
        row=QHBoxLayout();b=button('Compare memory results','primary');b.clicked.connect(self.compare);row.addWidget(b)
        b=button('Recompute reasons','quiet');b.clicked.connect(self.recompute);row.addWidget(b);layout.addLayout(row)
        self.graphs=QComboBox();self.graphs.setAccessibleName('Saved proposed reason graph');self.graphs.currentIndexChanged.connect(self.show_graph);layout.addWidget(self.graphs)
        self.answer=QLabel('No reason graph selected.');self.answer.setAccessibleName('Verdict and reason changes');self.answer.setWordWrap(True);self.answer.setTextFormat(Qt.PlainText);layout.addWidget(self.answer)
        self.paths=QTableWidget(0,3);self.paths.setHorizontalHeaderLabels(['Direction','Reason path','Context']);self.paths.setAccessibleName('Alternative supporting and refuting paths')
        self.paths.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents);self.paths.horizontalHeader().setStretchLastSection(True)
        self.paths.setContextMenuPolicy(Qt.CustomContextMenu);self.paths.customContextMenuRequested.connect(self.context_menu);layout.addWidget(self.paths,1)
        self.detail=QPlainTextEdit();self.detail.setReadOnly(True);self.detail.setAccessibleName('Retained reason details');self.detail.setMaximumHeight(200);layout.addWidget(self.detail)
        from .adaptive_qt import AdaptivePane
        self.adaptive=AdaptivePane(pane);tabs.addTab(self.adaptive,'Graphite investigation')
        self.timer=QTimer(self);self.timer.setInterval(500);self.timer.timeout.connect(self.poll)

    def call(self,op,args=None):return self.pane.call(op,args)

    def saved(self):
        if not self.pane.current:self.status.setText('Save a problem and select its delegated working copy first.');return False
        value=self.pane.current;original={k:value[k] for k in ('title','goals','variables','assumptions','questions','candidates')}
        original['sources']=[{k:s[k] for k in ('copy','path','label')} for s in value['sources']]
        if self.pane.arguments()!=original:self.status.setText('Save the problem changes before preparing an experiment.');return False
        return True

    def reload(self):
        self.adaptive.reload()
        problem=self.pane.current
        if self.context!=(problem or {}).get('id'):
            self.context=(problem or {}).get('id');self.script.clear();self.parameters.clear();self.graph=None
        if not problem:self.jobs.clear();self.graphs.clear();self.answer.setText('Save or reopen a problem.');return
        state=self.call('experiments.status')
        if state:
            available=state['python']['available'];qualified=state['qualification']['qualified']
            self.status.setText('Python: '+('qualified on this host' if qualified else 'installed; qualification required' if available else 'unavailable')+
                '. Native board tool: '+('detected; each run checks its fixture binding' if state['board']['executable'] else 'unavailable')+'. Selected copy: '+self.pane.copies.currentText())
        rows=self.call('experiments.list',{'id':problem['id']}) or {};old=self.jobs.currentData();self.jobs.blockSignals(True);self.jobs.clear()
        for row in rows.get('jobs',[]):self.jobs.addItem(row['tool']+' · '+row['state']+' · '+row['id'][:8],row['id'])
        if self.jobs.findData(old)>=0:self.jobs.setCurrentIndex(self.jobs.findData(old))
        self.jobs.blockSignals(False);self.show_result()
        self.python.clear()
        for row in rows.get('results',[]):
            body=row['observation']
            if body.get('state')=='OBSERVED' and any(v['name']=='memory_fits' and type(v['value']) is bool for v in body['parsed']['measurements']):
                self.python.addItem('Executed memory result · '+row['id'][:8],row['id'])
        calculations=self.call('math.list',{'id':problem['id']}) or {};self.math.clear()
        for row in calculations.get('receipts',[]):
            outputs=row['snapshot'].get('outputs',[])
            if outputs and outputs[0].get('kind')=='boolean':self.math.addItem('Exact comparison · '+row['id'][:8],row['id'])
        reasons=self.call('reasons.list',{'id':problem['id']}) or {};old=self.graphs.currentData();self.graphs.blockSignals(True);self.graphs.clear()
        for graph in reasons.get('graphs',[]):self.graphs.addItem('Proposed reasons · '+graph['id'][:8],graph['id'])
        if self.graphs.findData(old)>=0:self.graphs.setCurrentIndex(self.graphs.findData(old))
        self.graphs.blockSignals(False);self.show_graph()

    def track(self,job):
        if job:self.active=job['id'];self.status.setText('Running '+job['tool']+'. Outputs and failures will be retained.');self.timer.start()

    def qualify(self):self.track(self.call('experiments.qualify'))

    def create(self):
        if not self.saved():return
        copy=self.pane.copies.currentData()
        if not copy:self.status.setText('Select a working copy on Sources and results.');return
        value=self.call('experiments.create',{**self.pane.bound(),'copy':copy})
        if value:self.script.setText(value['script']);self.parameters.setPlainText(json.dumps(value['parameters'],indent=2));self.status.setText('Experiment created in the selected copy. Edit it through Changes; each run freezes its exact bytes and parameters.')

    def run_python(self):
        if not self.saved():return
        try:params=json.loads(self.parameters.toPlainText())
        except ValueError:self.status.setText('Enter a valid parameters object.');return
        plan=self.call('experiments.prepare',{**self.pane.bound(),'copy':self.pane.copies.currentData() or '', 'script':self.script.text(),'parameters':params})
        if plan:self.track(self.call('experiments.run',{'action':plan['id'],'expected_digest':plan['binding_digest']}))

    def run_board(self):
        if not self.saved():return
        plan=self.call('boards.prepare',{**self.pane.bound(),'copy':self.pane.copies.currentData() or '', 'board':self.board.text()})
        if plan:self.track(self.call('boards.run',{'action':plan['id'],'expected_digest':plan['binding_digest']}))

    def cancel(self):
        if self.active:self.call('jobs.cancel',{'id':self.active})

    def poll(self):
        if not self.active:self.timer.stop();return
        result=self.call('experiments.result',{'job':self.active})
        if result and result['state'] not in ('Queued','Running'):
            selected=self.active;self.active=None;self.timer.stop();self.reload()
            self.jobs.setCurrentIndex(self.jobs.findData(selected))

    def show_result(self):
        self.selected_result=self.jobs.currentData()
        if not self.selected_result:self.output.setPlainText('No executed experiment has been retained yet.');return
        value=self.call('experiments.result',{'job':self.selected_result})
        if not value:return
        if value['state']!='AVAILABLE':self.output.setPlainText(value['state']+'\n'+str(value.get('error') or ''));return
        body=value['observation'];rows=[body['state'],'Source applicability: '+value['applicability']]
        if 'execution' in body:
            execution=body['execution'];rows+=['Python process exit: '+str(execution['exit_code']),execution['stdout'],execution['stderr']]
            if execution['trap']:rows+=['Runtime stopped: '+execution['trap']]
        if body.get('parsed'):
            rows+=['%s = %s %s'%(v['name'],v['value'],v['unit']) for v in body['parsed']['measurements']]
            rows+=['Assumptions: '+x for x in body['parsed']['assumptions']]
        if 'native' in body:rows+=['Native findings: '+str(body['native']['total']),body['scope']]
        rows+=['Retained files: '+str(len(value['files'])),'Physical qualification: not demonstrated']
        self.output.setPlainText('\n'.join(rows))

    def publish(self):
        if self.selected_result:
            value=self.call('experiments.publish',{'job':self.selected_result})
            if value:self.status.setText('Kept %d generated files in the working copy.'%len(value['files']))

    def compare(self):
        if not self.saved():return
        if not self.math.currentData() or not self.python.currentData():self.answer.setText('Keep an exact memory comparison and an executed memory result first.');return
        graph=self.call('reasons.memory',{**self.pane.bound(),'calculation':self.math.currentData(),'experiment':self.python.currentData()})
        if graph:
            self.graph=graph;self.recompute();self.reload();self.graphs.setCurrentIndex(self.graphs.findData(graph['id']))

    def recompute(self):
        if not self.graph:self.answer.setText('Choose or create a proposed reason graph.');return
        value=self.call('reasons.evaluate',{'id':self.graph['id'],'expected_revision':self.graph['revision']})
        if value:self.show_graph(self.graph['id'])

    def show_graph(self,ident=None):
        ident=ident if isinstance(ident,str) else self.graphs.currentData()
        if not ident:self.graph=None;self.paths.setRowCount(0);self.answer.setText('No proposed reason graph selected.');return
        value=self.call('reasons.get',{'id':ident})
        if not value:return
        self.graph=value['graph'];snapshot=value['preview'];latest=value['latest'];change=(latest or {}).get('change',{})
        message='Proposed conclusion: '+snapshot['state']+'. '
        if change.get('has_previous'):
            message+=('Verdict changed. ' if change['verdict_changed'] else 'Verdict stayed the same. ')+('Reason paths changed.' if change['reason_paths_changed'] else 'Retained reason paths stayed the same.')
        if latest and latest['snapshot']['reason_digest']!=snapshot['reason_digest']:message+=' Inputs changed since the saved snapshot; recompute to record the new reasons.'
        self.answer.setText(message);self.paths.setRowCount(0)
        nodes={n['id']:n for n in self.graph['graph']['nodes']}
        for polarity,paths in snapshot['paths'].items():
            for path in paths:
                row=self.paths.rowCount();self.paths.insertRow(row)
                for col,text in enumerate(('Supports' if polarity=='positive' else 'Refutes', ' + '.join(nodes[n]['label'] for n in path['atoms']), ' + '.join(nodes[n]['label'] for n in path['assumptions']))):self.paths.setItem(row,col,QTableWidgetItem(text))
                self.paths.item(row,0).setData(Qt.UserRole,path['atoms'])
        for inactive in snapshot['inactive_atoms']:
            row=self.paths.rowCount();self.paths.insertRow(row)
            for col,text in enumerate(('Inactive',nodes[inactive['id']]['label'],inactive['reason'])):self.paths.setItem(row,col,QTableWidgetItem(text))
            self.paths.item(row,0).setData(Qt.UserRole,[inactive['id']])
        self.detail.setPlainText('Coverage: declared finite graph. Unknown dependencies outside it remain unknown.\nProposed rules are not approved facts.\n\n'+'\n'.join(snapshot['assumption_context']))

    def context_menu(self,point):
        row=self.paths.rowAt(point.y())
        menu=self.menu_for_row(row)
        if menu:menu.exec(self.paths.viewport().mapToGlobal(point))

    def menu_for_row(self,row):
        if row<0 or not self.graph:return None
        atoms=self.paths.item(row,0).data(Qt.UserRole) or [];nodes={n['id']:n for n in self.graph['graph']['nodes']};menu=QMenu(self)
        for atom in atoms:
            node=nodes[atom]
            action=menu.addAction('Show retained output: '+node['label'][:60]);action.triggered.connect(lambda checked=False,n=node:self.open_atom(n))
            action=menu.addAction('Preview a change to '+atom);action.triggered.connect(lambda checked=False,n=atom:self.impact(n))
        return menu

    def open_atom(self,node):
        # Owned receipt resolution rechecks bytes and revision through the Kernel.
        if node['source']=='MATH':
            from .engine import engineering
            from .engineering_kernel import operator
            from .lab_service import read
            receipt=read(engineering(self.pane.host.root),'math_result',node['receipt'],operator())
            value=self.call('math.get',{'id':receipt['action']})
        else:value=self.call('experiments.result',{'job':node['receipt']})
        if value:self.detail.setPlainText(json.dumps(value,indent=2))

    def impact(self,node):
        value=self.call('reasons.impact',{'id':self.graph['id'],'node':node})
        if value:self.detail.setPlainText('Tracked consequences: '+', '.join(value['tracked'])+'\n'+value['conclusion']+'\nOutside this graph: unknown.')
