"""Ledger-native review queue over deterministic, owner-scoped Kernel intake."""
from .text_prompts import writing_prompt
import html,json
from PySide6.QtCore import Qt,QTimer
from PySide6.QtWidgets import (QLabel,QPushButton,QLineEdit,QComboBox,QHBoxLayout,QVBoxLayout,QGridLayout,
    QTreeWidget,QTreeWidgetItem,QTextBrowser,QPlainTextEdit,QTabWidget,QSplitter,QWidget,QFileDialog,QInputDialog,QCheckBox,QAbstractItemView)
from .register_tabs import ServiceTab
from . import intake_service

def esc(value):return html.escape(str(value))

class IntakeTab(ServiceTab):
    def __init__(self,host):
        super().__init__(host);self.job=None;self.detail_data=None;self.offset=0;self.total=0;self.generation=0;self.catalog_count=0;self._refreshing=False
        self.setAcceptDrops(True)
        title=QLabel('GRAPHITE · REFERENCE INTAKE');title.setStyleSheet('font-size:18px;color:#edaa69;font-weight:bold');self.outer.addWidget(title)
        self.note=QLabel('Import a copy into private quarantine. Review each file with its dependencies. Admission starts a V1 reference catalog; engineering qualification stays separate.');self.note.setWordWrap(True);self.outer.addWidget(self.note)
        row=QHBoxLayout();self.namespaces=QComboBox();self.namespaces.setAccessibleName('Private reference library');self.namespaces.currentIndexChanged.connect(self.changed_namespace);row.addWidget(self.namespaces,1)
        create=QPushButton('New library');create.clicked.connect(self.create);row.addWidget(create);refresh=QPushButton('Refresh');refresh.clicked.connect(self.refresh);row.addWidget(refresh);self.outer.addLayout(row)
        source=QGridLayout();self.buttons={}
        for i,(label,fn) in enumerate([('Import ZIP / file',self.import_file),('Import folder',self.import_folder),('Review batch',self.review_batch),('Cancel job',self.cancel)]):
            button=QPushButton(label);button.setAccessibleName(label);button.clicked.connect(fn);source.addWidget(button,i//2,i%2);self.buttons[label]=button
        self.outer.addLayout(source)
        package=QPushButton('Inspect package before importing…');package.clicked.connect(lambda:host.ledger_bridge.show_packages());self.outer.addWidget(package)
        self.auto=QCheckBox('Allow automatic structural admission');self.auto.setToolTip('Owner authorization for text, DOCX, JSON, CSV and source-bound chip profiles only. Code, CAD, PDF and images still require an individual reference decision.');self.auto.clicked.connect(self.set_auto);self.outer.addWidget(self.auto)
        self.outer.addWidget(self.status)
        self.pages=QTabWidget();queue=QWidget();qbox=QVBoxLayout(queue);qbox.setContentsMargins(0,0,0,0)
        filters=QHBoxLayout();self.batches=QComboBox();self.batches.setAccessibleName('Intake batch');self.batches.currentIndexChanged.connect(self.filter_changed);filters.addWidget(self.batches,2)
        self.states=QComboBox();self.states.addItems(['All states','UNREVIEWED','ACCEPTED','HELD','REJECTED','REVOKED']);self.states.currentIndexChanged.connect(self.filter_changed);filters.addWidget(self.states,1);qbox.addLayout(filters)
        self.queue=QTreeWidget();self.queue.setHeaderLabels(['File','Admission','Profile']);self.queue.setColumnWidth(0,220);self.queue.setColumnWidth(1,125);self.queue.setAccessibleName('Quarantine review queue');self.queue.itemSelectionChanged.connect(self.selected);qbox.addWidget(self.queue,1)
        self.queue.setSelectionMode(QAbstractItemView.ExtendedSelection)
        pager=QHBoxLayout();previous=QPushButton('Previous');previous.clicked.connect(lambda:self.page(-1));pager.addWidget(previous);self.page_label=QLabel();pager.addWidget(self.page_label,1);following=QPushButton('Next');following.clicked.connect(lambda:self.page(1));pager.addWidget(following);qbox.addLayout(pager)
        self.pages.addTab(queue,'Quarantine')
        accepted=QWidget();abox=QVBoxLayout(accepted);abox.setContentsMargins(0,0,0,0);searchrow=QHBoxLayout();self.query=QLineEdit();writing_prompt(self.query, 'Search admitted reference text');self.query.returnPressed.connect(self.search);searchrow.addWidget(self.query,1);find=QPushButton('Search');find.clicked.connect(self.search);searchrow.addWidget(find);abox.addLayout(searchrow)
        self.accepted=QTreeWidget();self.accepted.setHeaderLabels(['V1 reference','Qualification']);self.accepted.setColumnWidth(0,270);self.accepted.itemSelectionChanged.connect(self.select_accepted);abox.addWidget(self.accepted,1)
        packet=QPushButton('Create packet from selected reference');packet.clicked.connect(self.packet);abox.addWidget(packet);self.pages.addTab(accepted,'Accepted V1')
        saved=QWidget();sbox=QVBoxLayout(saved);sbox.setContentsMargins(0,0,0,0);self.checkpoints=QComboBox();self.checkpoints.setAccessibleName('Catalog checkpoints');sbox.addWidget(self.checkpoints)
        for label,fn in [('Save catalog checkpoint',self.checkpoint),('Restore selected checkpoint',self.restore),('Export accepted V1 ZIP',self.export),('Recover interrupted imports',self.recover)]:
            button=QPushButton(label);button.clicked.connect(fn);sbox.addWidget(button)
        recovery=QLabel('Restore verifies original bytes, current policy and dependencies. Old packets remain stale after a reversal. Interrupted scans require a new import; verified objects are reused.');recovery.setWordWrap(True);sbox.addWidget(recovery);sbox.addStretch(1);self.pages.addTab(saved,'Recovery / export')
        self.details=QTabWidget();self.summary=QTextBrowser();self.summary.setOpenLinks(False);self.preview=QPlainTextEdit();self.preview.setReadOnly(True);self.receipts=QPlainTextEdit();self.receipts.setReadOnly(True)
        for label,widget in [('Review details',self.summary),('Literal preview',self.preview),('Decision receipts',self.receipts)]:self.details.addTab(widget,label)
        split=QSplitter(Qt.Vertical);split.addWidget(self.pages);split.addWidget(self.details);split.setSizes([240,210]);self.outer.addWidget(split,1)
        self.reason=QLineEdit();writing_prompt(self.reason, 'Reason for the owner decision (required)');self.reason.setAccessibleName('Intake decision reason');self.outer.addWidget(self.reason)
        actions=QGridLayout()
        for i,(label,decision) in enumerate([('Admit as reference','ACCEPTED'),('Hold','HELD'),('Reject','REJECTED'),('Revoke admission','REVOKED')]):
            button=QPushButton(label);button.setAccessibleName(label);button.clicked.connect(lambda checked=False,d=decision:self.decide(d));actions.addWidget(button,i//2,i%2);self.buttons[label]=button
        self.outer.addLayout(actions)
        bundle=QPushButton('Admit selected bundle');bundle.setToolTip('Admit selected files as references. Select related unadmitted files with Ctrl or Shift. Every member and dependency must pass; the whole decision commits together.');bundle.clicked.connect(self.admit_bundle);self.outer.addWidget(bundle);self.buttons[bundle.text()]=bundle
        self.summary.setHtml('<p>Create a private reference library, then import a ZIP, file or folder.</p><p>Automatic admission starts disabled. Originals are copied without running imported content.</p>')
        self.timer=QTimer(self);self.timer.setInterval(900);self.timer.timeout.connect(self.poll);self.timer.start();QTimer.singleShot(0,self.load_namespaces)
    def title(self):return 'Graphite · Intake'
    def info(self):return 'Reference intake · %d available V1 files · catalog generation %d · hardware unqualified'%(self.catalog_count,self.generation)
    def ns(self):return self.namespaces.currentData()
    def load_namespaces(self):self.call('intake.namespaces',{},self.loaded_namespaces)
    def loaded_namespaces(self,result):
        current=self.ns();self.namespaces.blockSignals(True);self.namespaces.clear()
        for value in result['namespaces']:self.namespaces.addItem(value['name'],value['id'])
        self.namespaces.setCurrentIndex(max(0,self.namespaces.findData(current)));self.namespaces.blockSignals(False);self.changed_namespace()
    def create(self):
        name,ok=QInputDialog.getText(self,'New private reference library','Library name')
        if ok and name:self.call('intake.namespace.create',{'name':name},self.created)
    def created(self,value):
        self.namespaces.addItem(value['name'],value['id']);self.namespaces.setCurrentIndex(self.namespaces.count()-1);self.refresh()
    def changed_namespace(self,*args):
        self.detail_data=None;self.queue.clear();self.accepted.clear();self.offset=0;self.refresh()
    def refresh(self):
        if self.stopping or not self.ns():self.status.setText('No private reference library selected.');return
        ident=self.ns()
        def policy(value):
            if self.ns()!=ident:return
            self.policy=value;self.auto.blockSignals(True);self.auto.setChecked(bool(value['auto_profiles']));self.auto.blockSignals(False)
        self.call('intake.policy',{'namespace':ident},policy)
        def batches(value):
            if self.ns()!=ident:return
            current=self.batches.currentData();self.batches.blockSignals(True);self.batches.clear()
            for batch in value['batches']:self.batches.addItem('%s · %s · %s files'%(batch['id'][:8],batch['state'],batch.get('files',0)),batch['id'])
            self.batches.setCurrentIndex(max(0,self.batches.findData(current)));self.batches.blockSignals(False);self.load_items()
        self.call('intake.batches',{'namespace':ident},batches)
        self.load_catalog();self.call('intake.checkpoints',{'namespace':ident},self.loaded_checkpoints)
    def filter_changed(self,*args):self.offset=0;self.load_items()
    def load_items(self):
        if not self.ns():return
        args={'namespace':self.ns(),'offset':self.offset,'limit':100}
        if self.batches.currentData():args['batch']=self.batches.currentData()
        if self.states.currentIndex()>0:args['state']=self.states.currentText()
        ident=self.ns();batch=self.batches.currentData()
        def loaded(value):
            if self.ns()!=ident or self.batches.currentData()!=batch:return
            current=self.queue.currentItem();selected=current.data(0,Qt.UserRole)['id'] if current else None
            self.queue.blockSignals(True);self.queue.clear();self.total=value['total'];self.generation=value['generation']
            for row in value['items']:
                item=QTreeWidgetItem([row['name'],row['admission'],row['profile']]);item.setData(0,Qt.UserRole,row);self.queue.addTopLevelItem(item)
                if row['id']==selected:self.queue.setCurrentItem(item)
            self.queue.blockSignals(False);self.page_label.setText('%d–%d of %d'%(min(self.total,self.offset+1),min(self.total,self.offset+100),self.total))
            self.status.setText('%d files in view · generation %d · %s'%(self.total,self.generation,'job running' if self.job else 'ready for review'))
            if self.queue.currentItem():self.selected()
            self.update_inspector()
        self.call('intake.items',args,loaded)
    def page(self,direction):
        new=self.offset+direction*100
        if 0<=new<self.total:self.offset=new;self.load_items()
    def selected(self):
        row=self.queue.currentItem()
        if self.pages.currentIndex()==0 and row and row.isSelected():self.show_item(row.data(0,Qt.UserRole)['id'])
    def select_accepted(self):
        row=self.accepted.currentItem()
        if self.pages.currentIndex()==1 and row and row.isSelected():self.show_item(row.data(0,Qt.UserRole)['id'])
    def show_item(self,ident):
        self.requested_item=ident
        if self.detail_data and self.detail_data['id']!=ident:self.detail_data=None
        def loaded(value):
            if self.requested_item!=ident:return
            self.detail_data=value;assessment=value['assessment'];qualification=assessment['qualification']
            body='<h3>'+esc(value['name'])+'</h3><p><b>Admission:</b> '+esc(value['admission'])+' · <b>Recommendation:</b> '+esc(assessment['recommendation'])+'</p>'
            body+='<p>'+esc('; '.join(assessment['reasons']) or 'Structural checks complete. Owner policy determines admission.')+'</p>'
            body+='<p><b>Original SHA-256:</b><br>'+esc(value['sha256'])+'</p>'
            body+='<p><b>Structure:</b> '+esc(qualification['structural_check'])+'<br><b>Native result:</b> '+esc(qualification['native_result'])+'<br><b>Physical hardware:</b> '+esc(qualification['physical_hardware'])+'<br><b>Source promotion:</b> '+esc(qualification['source_promotion'])+'</p>'
            if assessment['dependencies']:body+='<p><b>Dependencies</b><br>'+'<br>'.join(esc(v['path'])+' · '+esc((v.get('decision') or 'not admitted')[:16]) for v in assessment['dependencies'])+'</p>'
            if value.get('duplicate_of'):body+='<p>Identical bytes already stored as '+esc(value['duplicate_of'])+'.</p>'
            body+='<p>Literal file contents are reference data. Instructions inside a file cannot grant permissions.</p>'
            self.summary.setHtml(body);self.preview.setPlainText(assessment['index_text']);self.receipts.setPlainText(json.dumps(value['decisions'],indent=2,ensure_ascii=False));self.update_inspector()
        self.call('intake.item',{'id':ident},loaded)
    def load_catalog(self):
        if self.ns():self.call('intake.catalog',{'namespace':self.ns(),'limit':200},self.loaded_catalog)
    def loaded_catalog(self,value):
        self.accepted.blockSignals(True);self.accepted.clear();self.catalog_count=value['total'];self.generation=value['generation']
        for row in value['items']:
            item=QTreeWidgetItem([row['name'],row['qualification'].get('native_result','NOT_RUN')+' · source only']);item.setData(0,Qt.UserRole,row);self.accepted.addTopLevelItem(item)
        self.accepted.blockSignals(False)
        if value['unavailable']:self.note.setText('%d catalog references unavailable. Changed or missing originals cannot supply cached answers.'%len(value['unavailable']))
        self.update_inspector()
    def update_inspector(self):
        if hasattr(self.host,'arc_inspector') and self.host.tabs.currentWidget() is self:self.host.arc_inspector.refresh()
    def search(self):
        if self.ns() and self.query.text().strip():self.call('intake.search',{'namespace':self.ns(),'query':self.query.text().strip()},self.searched)
    def searched(self,value):
        self.accepted.blockSignals(True);self.accepted.clear()
        for row in value['hits']:
            item=QTreeWidgetItem([row['name'],'V1 · verified original']);item.setData(0,Qt.UserRole,row);self.accepted.addTopLevelItem(item)
        self.accepted.blockSignals(False)
        self.note.setText('%d admitted references matched. Held, rejected, revoked and inaccessible content are excluded.'%len(value['hits']))
    def import_file(self):
        path,_=QFileDialog.getOpenFileName(self,'Copy source into quarantine','','Reference sources (*.*)')
        if path:self.add_source(path)
    def import_folder(self):
        path=QFileDialog.getExistingDirectory(self,'Copy folder into quarantine')
        if path:self.add_source(path)
    def add_source(self,path):
        if not self.ns():self.note.setText('Create a private reference library first.');return
        self.launch('intake.import',{'namespace':self.ns(),'path':str(path),'mode':'snapshot'})
    def review_batch(self):
        if self.ns() and self.batches.currentData():self.launch('intake.review',{'namespace':self.ns(),'batch':self.batches.currentData()})
    def launch(self,op,args):
        if self.job:self.note.setText('An intake job is already running in this panel.');return
        self.call(op,args,self.watched)
    def watched(self,job):self.job=job['id'];self.note.setText(job['tool']+' · running through the shared Kernel. Originals remain unchanged.');self.refresh()
    def poll(self):
        if not self.job or self.stopping:return
        value=self.kernel.dispatch('jobs.get',{'id':self.job},self.principal)
        if not value['ok']:return
        job=value['result']
        if job['state'] in ('Completed','Failed','Cancelled','Interrupted'):
            self.job=None;self.note.setText(job['tool']+' · '+job['state']+' · '+str(job.get('error','')));self.refresh()
    def cancel(self):
        if self.job:self.call('jobs.cancel',{'id':self.job},lambda value:self.note.setText('Cancellation requested; partial scans never become admitted references.'))
    def set_auto(self,enabled):
        if not self.ns() or not hasattr(self,'policy'):return
        args={'namespace':self.ns(),'auto_profiles':list(intake_service.profiles.AUTO_PROFILES) if enabled else [],
            'variants':self.policy['variants'],'scope':self.policy['scope'],'expected_policy_hash':self.policy['policy_hash'],
            'reason':'Owner enabled structural reference admission' if enabled else 'Owner disabled automatic admission'}
        self.call('intake.policy.set',args,lambda value:self.refresh(),failed=lambda error:self.refresh())
    def decide(self,decision):
        value=self.detail_data
        if not value or len(self.reason.text().strip())<3:self.note.setText('Select a file and enter a reason of at least three characters.');return
        args={'id':value['id'],'expected_decision':value.get('decision_id') or '', 'reason':self.reason.text().strip()}
        op='intake.revoke' if decision=='REVOKED' else 'intake.decide'
        if op=='intake.decide':args.update(decision=decision,expected_sha256=value['sha256'],expected_policy_hash=value['policy_hash'])
        def completed(receipt):
            self.note.setText(receipt['decision']+' · receipt '+receipt['id'][:12]+' · source promotion NOT GRANTED');self.refresh();self.show_item(value['id'])
        self.call(op,args,completed)
    def packet(self):
        row=self.accepted.currentItem()
        if not row or not self.ns():return
        self.call('intake.packet.create',{'namespace':self.ns(),'items':[row.data(0,Qt.UserRole)['id']]},self.packet_created)
    def packet_created(self,value):
        self.last_packet=value;self.note.setText('Reference packet '+value['id'][:12]+' · '+value['state']+' · local only');self.receipts.setPlainText(json.dumps(value,indent=2,ensure_ascii=False));self.details.setCurrentWidget(self.receipts)
    def admit_bundle(self):
        selected=[v.data(0,Qt.UserRole)['id'] for v in self.queue.selectedItems()]
        if not selected or not hasattr(self,'policy') or len(self.reason.text().strip())<3:self.note.setText('Select related files in Quarantine and enter a reason.');return
        args={'namespace':self.ns(),'items':selected,'expected_generation':self.generation,'expected_policy_hash':self.policy['policy_hash'],'reason':self.reason.text().strip()}
        self.call('intake.bundle.decide',args,self.bundle_done)
    def bundle_done(self,value):self.note.setText('%d related files admitted atomically as references · source promotion NOT GRANTED'%value['files']);self.refresh()
    def checkpoint(self):
        if not self.ns():return
        label,ok=QInputDialog.getText(self,'Catalog checkpoint','Checkpoint label')
        if ok and label:self.call('intake.checkpoint',{'namespace':self.ns(),'label':label},lambda value:self.refresh())
    def loaded_checkpoints(self,value):
        current=self.checkpoints.currentData();self.checkpoints.clear()
        for row in value['checkpoints']:self.checkpoints.addItem(row['label']+' · generation '+str(row['generation']),row['id'])
        self.checkpoints.setCurrentIndex(max(0,self.checkpoints.findData(current)))
    def restore(self):
        if not self.checkpoints.currentData() or len(self.reason.text().strip())<3:self.note.setText('Choose a checkpoint and enter a reason.');return
        self.call('intake.catalog.restore',{'id':self.checkpoints.currentData(),'expected_generation':self.generation,'reason':self.reason.text().strip()},lambda value:self.refresh())
    def recover(self):
        if self.ns():self.call('intake.recover',{'namespace':self.ns()},lambda value:self.refresh())
    def export(self):
        if not self.ns():return
        path,_=QFileDialog.getSaveFileName(self,'Export admitted V1 reference originals','','ZIP archive (*.zip)')
        if path:self.launch('intake.export',{'namespace':self.ns(),'destination':path,'expected_generation':self.generation})
    def dragEnterEvent(self,event):
        urls=event.mimeData().urls()
        if len(urls)==1 and urls[0].isLocalFile():event.acceptProposedAction()
    def dropEvent(self,event):
        urls=event.mimeData().urls()
        if len(urls)==1 and urls[0].isLocalFile():self.add_source(urls[0].toLocalFile());event.acceptProposedAction()
    def shutdown_engineering(self):self.timer.stop();super().shutdown_engineering()
