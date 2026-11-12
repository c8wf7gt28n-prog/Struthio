"""Native research review over the shared Kernel, embedded beside memory and staC."""
from .text_prompts import writing_prompt
import json
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (QWidget,QLabel,QPushButton,QLineEdit,QPlainTextEdit,QComboBox,QCheckBox,QSpinBox,QVBoxLayout,QHBoxLayout,QFormLayout,QTabWidget,QFileDialog,QInputDialog,QScrollArea,QListWidget,QListWidgetItem,QSizePolicy)
from .register_tabs import ServiceTab

class ResearchTab(ServiceTab):
    def __init__(self,host,memory):
        super().__init__(host);self.memory=memory;self.preview=None;self.return_value=None;self.pending_request=None
        note=QLabel('Review each outgoing packet and returned finding. Sharing is explicit.');note.setWordWrap(True);self.outer.addWidget(note)
        self.pages=QTabWidget();self.outer.addWidget(self.pages,1)
        policy=QWidget();box=QVBoxLayout(policy);self.libraries=QListWidget();self.libraries.setAccessibleName('Libraries permitted for selected research excerpts');box.addWidget(QLabel('Permit selected excerpts from these libraries:'));box.addWidget(self.libraries,1)
        self.manual=QCheckBox('Allow reviewed manual ZIP exports');self.gemini=QCheckBox('Allow reviewed Gemini requests using the configured key and model');box.addWidget(self.manual);box.addWidget(self.gemini)
        form=QFormLayout();self.max_calls=QSpinBox();self.max_calls.setRange(0,100);self.max_bytes=QSpinBox();self.max_bytes.setRange(1024,60000);self.max_tokens=QSpinBox();self.max_tokens.setRange(128,8192)
        for label,w in [('Max calls (lifetime)',self.max_calls),('Max request bytes',self.max_bytes),('Max output tokens',self.max_tokens)]:form.addRow(label,w)
        box.addLayout(form);budget=QLabel('Failed/uncertain calls count. No automatic retries. These are usage limits; use provider billing controls for a monetary cap. Activity and personality are excluded.');budget.setWordWrap(True);box.addWidget(budget)
        self.usage=QLabel();box.addWidget(self.usage);row=QHBoxLayout();box.addLayout(row)
        for label,fn in [('Reload policy',self.refresh_policy),('Save sharing and usage policy',self.save_policy)]:b=QPushButton(label);b.clicked.connect(fn);row.addWidget(b)
        self.add_page(policy,'1 · Sharing')
        compose=QWidget();box=QVBoxLayout(compose);self.question=QLineEdit();writing_prompt(self.question, 'One precise question');box.addWidget(self.question)
        self.why=QLineEdit();writing_prompt(self.why, 'Why escalate: missing evidence, contradiction or local limitation');box.addWidget(self.why)
        self.constraints=QPlainTextEdit();writing_prompt(self.constraints, 'Constraints · one per line');self.attempts=QPlainTextEdit();writing_prompt(self.attempts, 'Approaches already attempted · one per line');self.unknowns=QPlainTextEdit();writing_prompt(self.unknowns, 'Unknowns · one per line')
        for w in (self.constraints,self.attempts,self.unknowns):w.setMaximumHeight(65);box.addWidget(w)
        attach=QPushButton('Use source addresses attached in Tasks / memory');attach.clicked.connect(self.attach);box.addWidget(attach);self.bindings=QPlainTextEdit('[]');self.bindings.setMaximumHeight(65);self.bindings.setAccessibleName('Research source bindings JSON');box.addWidget(self.bindings)
        row=QHBoxLayout();box.addLayout(row)
        for label,fn in [('Create reviewable request',self.create),('Export reviewed request ZIP',self.export),('Send reviewed request to Gemini',self.send_gemini)]:b=QPushButton(label);b.clicked.connect(fn);row.addWidget(b)
        self.outgoing=QPlainTextEdit();self.outgoing.setReadOnly(True);self.outgoing.setMinimumHeight(200);self.outgoing.setAccessibleName('Exact outgoing question and source excerpts');box.addWidget(self.outgoing,1);self.add_page(compose,'2 · Request')
        history=QWidget();box=QVBoxLayout(history);row=QHBoxLayout();box.addLayout(row);self.request_choice=QComboBox();self.request_choice.currentIndexChanged.connect(self.load_request);box.addWidget(self.request_choice)
        b=QPushButton('Reload exchanges');b.clicked.connect(self.reload);row.addWidget(b);b=QPushButton('Import returned ZIP');b.clicked.connect(self.import_return);row.addWidget(b)
        self.return_choice=QComboBox();self.return_choice.currentIndexChanged.connect(self.load_return);box.addWidget(self.return_choice)
        self.return_state=QLabel('No return selected.');self.return_state.setWordWrap(True);box.addWidget(self.return_state)
        self.return_data=QPlainTextEdit();self.return_data.setReadOnly(True);self.return_data.setMinimumHeight(220);self.return_data.setAccessibleName('Returned evidence, interpretations and proposals');box.addWidget(self.return_data,1)
        row=QHBoxLayout();box.addLayout(row)
        for label,value in [('Approve for read evaluation','approved_for_evaluation'),('Keep inconclusive','inconclusive'),('Reject return','rejected')]:b=QPushButton(label);b.clicked.connect(lambda checked=False,v=value:self.review(v));row.addWidget(b)
        row=QHBoxLayout();box.addLayout(row);self.proposals=QComboBox();row.addWidget(self.proposals,1);b=QPushButton('Evaluate selected read through Graphite');b.clicked.connect(self.evaluate);row.addWidget(b)
        row=QHBoxLayout();box.addLayout(row);self.citations=QComboBox();row.addWidget(self.citations,1);b=QPushButton('Resolve current original citation');b.clicked.connect(self.resolve);row.addWidget(b)
        self.add_page(history,'3 · Return');self.outer.addWidget(self.status)
        short={'Reload exchanges':'Reload','Import returned ZIP':'Import ZIP','Approve for read evaluation':'Approve reads','Keep inconclusive':'Inconclusive','Reject return':'Reject','Evaluate selected read through Graphite':'Evaluate read','Resolve current original citation':'Open original','Save sharing and usage policy':'Save policy','Use source addresses attached in Tasks / memory':'Use attached references','Create reviewable request':'Create preview','Export reviewed request ZIP':'Export ZIP','Send reviewed request to Gemini':'Ask Gemini'}
        for b in self.findChildren(QPushButton):
            if b.text() in short:original=b.text();b.setText(short[original]);b.setAccessibleName(original);b.setToolTip(original)
        for combo in self.findChildren(QComboBox):combo.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Fixed);combo.setMinimumWidth(70)
        QTimer.singleShot(0,self.refresh_policy);QTimer.singleShot(0,self.reload)
    def add_page(self,widget,title):
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(widget);self.pages.addTab(scroll,title)
    def show_data(self,v):self.return_data.setPlainText(json.dumps(v,ensure_ascii=False,indent=2))
    def show_return(self,v):
        response=v['response'];lines=['EXTERNAL REVIEW · '+response['reviewer'],'']
        labels={'original_evidence':'CITED ORIGINAL EVIDENCE','new_source':'NEW SOURCE · UNADMITTED','interpretation':'INTERPRETATION · UNVERIFIED'}
        for finding in response['findings']:
            lines.extend([labels[finding['kind']],finding['text'],'Citations: '+(', '.join(finding['citations']) or 'none'),''])
        lines.extend(['STILL UNKNOWN',*response['unknowns'],'','PROPOSED READS'])
        for i,p in enumerate(response['proposals']):lines.append(str(i+1)+'. '+p['operation']+' · '+p['reason'])
        if response['new_sources']:lines.extend(['','New documents remain sealed inside the original return ZIP; use Intake review before admission.'])
        lines.extend(['','Recorded read evaluations: '+str(len(v['evaluations'])),'Return SHA256: '+v['id']])
        self.return_data.setPlainText('\n'.join(lines))
    def refresh_policy(self):
        def loaded(p):
            self.manual.setChecked(p['manual']);self.gemini.setChecked(p['gemini']);self.max_calls.setValue(p['max_calls']);self.max_bytes.setValue(p['max_input_bytes']);self.max_tokens.setValue(p['max_output_tokens']);self.usage.setText('Recorded Gemini attempts: '+str(p.get('usage',{}).get('calls',0)))
            def libs(v):
                self.libraries.clear()
                from PySide6.QtCore import Qt
                for ns in v['namespaces']:
                    item=QListWidgetItem(ns['name']);item.setData(Qt.UserRole,ns['id']);item.setFlags(item.flags()|Qt.ItemIsUserCheckable);item.setCheckState(Qt.Checked if ns['id'] in p['namespaces'] else Qt.Unchecked);self.libraries.addItem(item)
            self.call('intake.namespaces',{},libs)
        self.call('research.policy',{},loaded)
    def save_policy(self):
        from PySide6.QtCore import Qt
        ids=[self.libraries.item(i).data(Qt.UserRole) for i in range(self.libraries.count()) if self.libraries.item(i).checkState()==Qt.Checked]
        self.call('research.policy.set',{'namespaces':ids,'manual':self.manual.isChecked(),'gemini':self.gemini.isChecked(),'max_calls':self.max_calls.value(),'max_input_bytes':self.max_bytes.value(),'max_output_tokens':self.max_tokens.value()},lambda v:(self.status.setText('Policy saved. Create a new preview after policy changes.'),self.refresh_policy()))
    def attach(self):self.bindings.setPlainText(self.memory.reference_json.toPlainText())
    def create(self):
        try:bindings=json.loads(self.bindings.toPlainText())
        except ValueError:self.status.setText('Source addresses must be valid JSON.');return
        lines=lambda w:[s.strip() for s in w.toPlainText().splitlines() if s.strip()]
        self.call('research.create',{'question':self.question.text(),'why':self.why.text(),'constraints':lines(self.constraints),'attempts':lines(self.attempts),'unknowns':lines(self.unknowns),'references':bindings},self.created)
    def created(self,v):self.preview=v;self.pending_request=v['id'];self.outgoing.setPlainText(json.dumps(v,ensure_ascii=False,indent=2));self.status.setText('Review this saved request. Later form edits require a new request.');self.reload()
    def export(self):
        if not self.preview:self.status.setText('Create or load a request preview first.');return
        path,_=QFileDialog.getSaveFileName(self,'Export reviewed research ZIP','','ZIP (*.zip)')
        if path:self.call('research.export',{'id':self.preview['id'],'expected_digest':self.preview['digest'],'destination':path},lambda v:(self.status.setText('Request ZIP exported for your manual upload; no upload performed.'),self.show_data(v),self.reload()))
    def send_gemini(self):
        if not self.preview:self.status.setText('Create or load a request preview first.');return
        self.status.setText('Sending the saved, reviewed request through the configured Gemini access…')
        self.call('research.gemini',{'id':self.preview['id'],'expected_digest':self.preview['digest']},lambda v:(self.show_data(v),self.refresh_policy(),self.reload()),lambda v:self.refresh_policy())
    def reload(self):
        def loaded(v):
            req=self.pending_request or self.request_choice.currentData();self.pending_request=None;ret=self.return_choice.currentData();self.request_choice.blockSignals(True);self.return_choice.blockSignals(True);self.request_choice.clear();self.return_choice.clear()
            for r in v['requests']:self.request_choice.addItem(r['question'][:75],r['id'])
            for r in v['returns']:self.return_choice.addItem(r['response']['reviewer']+' · '+r['disposition'],r['id'])
            self.request_choice.setCurrentIndex(max(0,self.request_choice.findData(req)));self.return_choice.setCurrentIndex(max(0,self.return_choice.findData(ret)));self.request_choice.blockSignals(False);self.return_choice.blockSignals(False);self.load_request();self.load_return()
        self.call('research.list',{},loaded)
    def load_request(self,*args):
        ident=self.request_choice.currentData()
        if ident:
            def loaded(v):
                if self.request_choice.currentData()!=ident:return
                self.preview=v['request'];self.outgoing.setPlainText(json.dumps(v,ensure_ascii=False,indent=2))
            self.call('research.request',{'id':ident},loaded)
    def import_return(self):
        path,_=QFileDialog.getOpenFileName(self,'Import external research return','','ZIP (*.zip)')
        if path:self.call('research.import',{'path':path},lambda v:(self.show_data(v),self.status.setText('Returned data retained. Review it before evaluating a proposal.'),self.reload()))
    def load_return(self,*args):
        ident=self.return_choice.currentData()
        if not ident:return
        def loaded(v):
            if self.return_choice.currentData()!=ident:return
            self.return_value=v;self.show_return(v);self.return_state.setText(v['applicability']+' · '+v['disposition']+' · external findings remain unverified');self.proposals.clear();self.citations.clear()
            for i,p in enumerate(v['response']['proposals']):self.proposals.addItem(p['operation']+' · '+p['reason'],i)
            def request_loaded(r):
                if not self.return_value or self.return_value['id']!=ident:return
                for b in r['request']['bindings']:self.citations.addItem(b['name']+' · '+b['id'][:12],b)
            self.call('research.request',{'id':v['request']},request_loaded)
        self.call('research.return',{'id':ident},loaded)
    def review(self,disposition):
        if not self.return_value:return
        reason,ok=QInputDialog.getText(self,'Record return disposition','Reason for this review:')
        if ok and reason.strip():self.call('research.review',{'id':self.return_value['id'],'disposition':disposition,'reason':reason},lambda v:(self.show_data(v),self.reload()))
    def evaluate(self):
        if self.return_value and self.proposals.currentData() is not None:self.call('research.evaluate',{'id':self.return_value['id'],'index':self.proposals.currentData()},lambda v:(self.show_data(v),self.status.setText('Graphite read evaluated. This receipt is not physical or engineering acceptance.')))
    def resolve(self):
        b=self.citations.currentData()
        if b:self.call('references.resolve',{k:b[k] for k in ('namespace','id','item')},self.show_data)
