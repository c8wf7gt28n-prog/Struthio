"""Responsive task organizer and package desk over the shared Kernel read models."""
from .text_prompts import writing_prompt
import json
import time
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction
from shiboken6 import isValid
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QScrollArea,QLabel,
    QPushButton,QLineEdit,QComboBox,QTreeWidget,QTreeWidgetItem,QFrame,QPlainTextEdit,QCheckBox,
    QFileDialog,QSizePolicy,QLayout)
from sdk.cli.arc1cli.object_context import principal_key
from sdk.cli.arc1cli import work_organizer as vocabulary
from .engineering_kernel import operator
from .register_tabs import ServiceTab


def label(text,large=False):
    item=QLabel(text);item.setWordWrap(True);item.setTextFormat(Qt.PlainText)
    item.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Preferred)
    item.setProperty('arcReadingRole','heading' if large else 'prose')
    if large:item.setStyleSheet('color:#ffb566;font-weight:600')
    return item


class PrivateTab(ServiceTab):
    def __init__(self,bridge):
        super().__init__(bridge.host);self.bridge=bridge;self.actor=principal_key(self.principal)
        self.serial=0;self.data=None
        self.scroll=QScrollArea();self.scroll.setWidgetResizable(True)
        self.body=QWidget();self.box=QVBoxLayout(self.body);self.box.setSizeConstraint(QLayout.SetMinimumSize)
        self.scroll.setWidget(self.body);self.outer.addWidget(self.scroll)
        self.status.setTextFormat(Qt.PlainText)

    def guard(self):
        key=principal_key(self.principal)
        if key!=self.actor:
            self.serial+=1;self.actor=key;self.clear_private()
        return key

    def scoped(self,op,args,done,failed=None):
        key=self.guard()
        def receive(value):
            if key!=principal_key(self.principal):self.guard();return
            done(value)
        def failure(error):
            if key!=principal_key(self.principal):self.guard();return
            if failed:failed(error)
        return self.call(op,args,receive,failure)

    def desktop(self):
        self.guard()
        if principal_key(self.principal)!=principal_key(operator()):
            self.status.setText('This desktop opens workspaces for its local owner. Read-only views retain the current caller.');return False
        return True

    def clear_private(self):
        self.data=None

    def shutdown_engineering(self):
        for name in ('timer','debounce'):
            if hasattr(self,name):getattr(self,name).stop()
        super().shutdown_engineering()


class OrganizerTab(PrivateTab):
    def __init__(self,bridge):
        super().__init__(bridge);self.cards=[];self.columns=None;self.model=None
        from .result_surface import ResultSurface
        from sdk.cli.arc1cli.workbench_view import organizer
        self.surface=ResultSurface();self.surface.present(organizer(None));self.box.addWidget(self.surface)
        row=QHBoxLayout();self.search=QLineEdit();writing_prompt(self.search, 'Find work, a package or a next step…')
        self.search.setAccessibleName('Find organizer work');self.search.setMinimumWidth(0);self.search.setMaxLength(200)
        self.focus=QComboBox();self.focus.addItem('All work','all')
        for key,lane in vocabulary.FOCUS.items():self.focus.addItem(lane,key)
        self.focus.setAccessibleName('Organizer work focus');self.focus.setMaximumWidth(215)
        refresh=QPushButton('Refresh');refresh.clicked.connect(self.refresh)
        row.addWidget(self.search,1);row.addWidget(self.focus);row.addWidget(refresh);self.box.addLayout(row)
        self.overview=label('Reading your work…');self.box.addWidget(self.overview)
        self.box.addWidget(label('Next on your desk',True))
        self.next=QTreeWidget();self.next.setHeaderLabels(['Your work','Next move'])
        self.next.setRootIsDecorated(False);self.next.setMinimumHeight(150);self.next.setMaximumHeight(220)
        self.next.setColumnWidth(0,275);self.next.setAccessibleName('Owner work needing attention')
        self.next.itemActivated.connect(self.open_next);self.box.addWidget(self.next)
        self.open_next_button=QPushButton('Open selected work');self.open_next_button.clicked.connect(self.open_next)
        self.open_next_button.setEnabled(False);self.next.itemSelectionChanged.connect(lambda:self.open_next_button.setEnabled(bool(self.next.currentItem())))
        self.box.addWidget(self.open_next_button)
        self.grid=QGridLayout();self.grid.setSpacing(12);self.box.addLayout(self.grid)
        self.box.addWidget(label('The same desk as a line',True))
        self.stac=QLineEdit('desk');self.auto_program='desk';self.stac.setAccessibleName('Read-only organizer line');self.stac.setMinimumWidth(0)
        self.box.addWidget(self.stac)
        self.read=QPushButton('Read it');self.read.clicked.connect(self.run_stac);self.box.addWidget(self.read)
        self.stac_result=label('A read explains the same work. It does not open a workspace or run a job.');self.box.addWidget(self.stac_result)
        self.technical=QCheckBox('Technical detail');self.detail=QPlainTextEdit();self.detail.setReadOnly(True);self.detail.hide()
        self.technical.toggled.connect(self.detail.setVisible);self.box.addWidget(self.technical);self.box.addWidget(self.detail);self.box.addWidget(self.status)
        self.debounce=QTimer(self);self.debounce.setSingleShot(True);self.debounce.setInterval(220);self.debounce.timeout.connect(self.refresh)
        self.search.textChanged.connect(lambda:self.debounce.start());self.focus.currentIndexChanged.connect(self.refresh)
        self.timer=QTimer(self);self.timer.setInterval(5000);self.timer.timeout.connect(lambda:self.refresh() if self.isVisible() else None);self.timer.start()
        QTimer.singleShot(0,self.refresh)

    def title(self):return 'Organizer'

    def clear_private(self):
        super().clear_private();self.model=None;self.next.clear();self.open_next_button.setEnabled(False)
        from sdk.cli.arc1cli.workbench_view import organizer
        self.surface.present(organizer(None))
        self.overview.setText('Reading this caller’s work…');self.detail.clear();self.stac_result.clear()
        self.clear_cards()

    def clear_cards(self):
        for card in self.cards:self.grid.removeWidget(card);card.deleteLater()
        self.cards=[];self.columns=None

    def refresh(self,*_):
        self.guard();self.serial+=1;serial=self.serial
        args={'query':self.search.text()[:200],'focus':self.focus.currentData()}
        program='desk | find '+json.dumps(args['query']) if args['query'] else 'desk' if args['focus']=='all' else 'desk | focus '+args['focus']
        if self.stac.text()==self.auto_program:self.stac.setText(program)
        self.auto_program=program
        self.scoped('ledger.organizer',args,lambda value:self.loaded(serial,value))

    def loaded(self,serial,value):
        if serial!=self.serial:return
        signature=json.dumps(value,sort_keys=True)
        if signature==self.model:return
        self.model=signature;self.data=value;self.detail.setPlainText(json.dumps(value,indent=2,ensure_ascii=False))
        from sdk.cli.arc1cli.workbench_view import organizer
        self.surface.present(organizer(value))
        self.overview.setText(str(len(value['tasks']))+' workspaces · '+str(value['next_total'])+' next items · '+('Work held: explicit Resume required' if value['gate']['held'] else 'Choose a task; nothing starts automatically'))
        selected=self.next.currentItem().data(0,Qt.UserRole) if self.next.currentItem() else None
        self.next.clear()
        for item in value['next']:
            row=QTreeWidgetItem([item['title'],item['detail']]);row.setData(0,Qt.UserRole,item)
            row.setToolTip(0,item['title']);row.setToolTip(1,item['detail']);self.next.addTopLevelItem(row)
            if item==selected:self.next.setCurrentItem(row)
        if not value['next']:
            empty=QTreeWidgetItem(['No matching work needs attention','Choose a workspace below.']);empty.setFlags(Qt.NoItemFlags);self.next.addTopLevelItem(empty)
        self.clear_cards()
        for task in value['tasks']:
            card=QFrame();card.setObjectName('OrganizerCard')
            card.setStyleSheet('QFrame#OrganizerCard {background:transparent;border:0;border-top:1px solid #dad4c8;border-radius:0;}')  # 4.1: a hairline, not a tile
            box=QVBoxLayout(card);box.setContentsMargins(14,12,14,12)
            lane=label(task['lane'].upper());lane.setProperty('arcReadingRole','ui');lane.setStyleSheet('color:#6c675e;font-size:13px;letter-spacing:1px');box.addWidget(lane)
            title=label(task['title']);title.setStyleSheet('font-weight:600');box.addWidget(title);box.addWidget(label(task['detail']))
            if task['state']=='Project required':box.addWidget(label('Project attachment required for engineering actions.'))
            action=QPushButton('Open workspace');action.setAccessibleName(task['title'])
            action.clicked.connect(lambda checked=False,t=task:self.open_task(t));box.addWidget(action)
            self.cards.append(card)
        self.arrange()
        self.status.setText('The organizer opens existing controls. Saves, grants and acceptance remain explicit.')

    def arrange(self):
        columns=2 if self.scroll.viewport().width()>=720 else 1
        if columns==self.columns:return
        self.columns=columns
        for i,card in enumerate(self.cards):self.grid.removeWidget(card);self.grid.addWidget(card,i//columns,i%columns)
        for i in range(2):self.grid.setColumnStretch(i,1 if i<columns else 0)

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,'cards'):self.arrange()

    def open_task(self,task):
        if not self.desktop():return
        self.bridge.navigation()[task['destination']]()

    def open_next(self,*_):
        row=self.next.currentItem();item=row.data(0,Qt.UserRole) if row else None
        if not item or not self.desktop():return
        if item['kind']=='package':self.bridge.show_packages().focus_inspection(item['id'])
        elif item['kind']=='job':
            self.host.select_object({'kind':'job','target':item['id']},self.principal,self);self.host.show_object_glass()
        else:self.bridge.navigation()[item['destination']]()

    def run_stac(self):
        self.scoped('stac.run',{'program':self.stac.text()},self.stac_loaded)

    def stac_loaded(self,value):
        self.detail.setPlainText(json.dumps(value,indent=2,ensure_ascii=False))
        result=value.get('result');kind=value.get('result_type','Read result')
        if not isinstance(result,dict):
            self.stac_result.setText('Read '+value.get('state','unavailable').lower()+' · '+value.get('reason','No result available.'));return
        if kind=='WorkbenchOverview':
            detail=str(len(result['tasks']))+' workspaces · '+str(result['next_total'])+' next items'
        elif kind=='PackageInventory':detail=str(result['total'])+' files · '+result['state'].lower()
        elif kind=='PackageGaps':detail=result['state'].lower()+' · '+str(len(result['issues']))+' reported issues'
        else:detail=value.get('state','Read completed')
        self.stac_result.setText('Line · '+kind+' · '+detail+'. No action ran.')


class PackageTab(PrivateTab):
    def __init__(self,bridge):
        super().__init__(bridge);self.selected_id=None;self.offset=0;self.active_job=None;self.copy_state='Explicit choice required'
        self.box.addWidget(label('Package desk',True))
        self.box.addWidget(label('Inspect → Copy for review → Admit. Each is a separate choice; package contents cannot grant permission.'))
        row=QHBoxLayout();self.inspect_button=QPushButton('Inspect ZIP…');self.inspect_button.clicked.connect(self.choose)
        refresh=QPushButton('Refresh');refresh.clicked.connect(self.refresh)
        row.addWidget(self.inspect_button);row.addWidget(refresh);self.box.addLayout(row)
        self.saved=QComboBox();self.saved.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Fixed);self.saved.setAccessibleName('Your retained package inspections')
        self.saved.activated.connect(self.changed);self.box.addWidget(self.saved)
        self.stage=label('Inspection: choose a package\nCopy for review: explicit choice required\nAdmission: no permission granted');self.box.addWidget(self.stage)
        self.facts=label('No package selected. ZIP/Store/Deflate are qualified for bounded inspection; additional formats remain explicit.');self.box.addWidget(self.facts)
        self.issues=label('');self.box.addWidget(self.issues)
        self.members=QTreeWidget();self.members.setHeaderLabels(['Member','Bytes','SHA-256'])
        self.members.setRootIsDecorated(False);self.members.setColumnWidth(0,350);self.members.setColumnWidth(1,110)
        self.members.setMinimumHeight(230);self.members.setAccessibleName('Hashed package member inventory');self.box.addWidget(self.members)
        row=QHBoxLayout();previous=QPushButton('Previous');following=QPushButton('Next');self.page=label('')
        previous.clicked.connect(lambda:self.page_by(-1));following.clicked.connect(lambda:self.page_by(1))
        row.addWidget(previous);row.addWidget(self.page,1);row.addWidget(following);self.box.addLayout(row)
        self.box.addWidget(label('Where should this be reviewed?',True))
        self.libraries=QComboBox();self.libraries.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Fixed);self.libraries.setAccessibleName('Owner library for review copy');self.box.addWidget(self.libraries)
        self.copy_button=QPushButton('Copy / locate review batch');self.copy_button.setEnabled(False);self.copy_button.clicked.connect(self.copy_for_review);self.box.addWidget(self.copy_button)
        self.review_button=QPushButton('Open reference review');self.review_button.clicked.connect(self.open_review);self.box.addWidget(self.review_button)
        self.box.addWidget(label('No library yet? Open reference review and create one. Copying preserves originals and creates no admission.'))
        self.stac=QLineEdit();self.stac.setReadOnly(True);self.stac.setAccessibleName('Read of the selected package');self.stac.setMinimumWidth(0);self.box.addWidget(self.stac)
        self.technical=QCheckBox('Technical detail');self.detail=QPlainTextEdit();self.detail.setReadOnly(True);self.detail.hide()
        self.technical.toggled.connect(self.detail.setVisible);self.box.addWidget(self.technical);self.box.addWidget(self.detail);self.box.addWidget(self.status)
        self.timer=QTimer(self);self.timer.setInterval(800);self.timer.timeout.connect(self.poll_job)
        self.libraries.currentIndexChanged.connect(self.update_copy)
        QTimer.singleShot(0,self.refresh)

    def title(self):return 'Package desk'

    def clear_private(self):
        super().clear_private();self.selected_id=None;self.active_job=None;self.timer.stop();self.saved.clear();self.members.clear()
        self.libraries.clear();self.detail.clear();self.stac.clear();self.copy_button.setEnabled(False)
        self.stage.setText('Choose a package for this caller. No permission granted.');self.facts.clear();self.issues.clear()

    def refresh(self,*_,reload=True):
        self.guard()
        def loaded(value):
            self.saved.clear()
            for row in value['inspections']:self.saved.addItem(row['name']+' · '+row['state'].replace('_',' ').capitalize(),row['id'])
            index=self.saved.findData(self.selected_id)
            if index>=0:self.saved.setCurrentIndex(index)
            elif self.saved.count():self.selected_id=self.saved.currentData();self.offset=0
            if self.selected_id and (reload or not self.data or self.data['id']!=self.selected_id):self.load()
            self.status.setText('Retains up to '+str(value['retention'])+' owner inspections. Refresh reads receipts; it does not rescan files.')
        self.scoped('intake.package.list',{},loaded)
        def libraries(value):
            previous=self.libraries.currentData();self.libraries.clear()
            for row in value['namespaces']:
                if row['owner']==self.principal.identity:self.libraries.addItem(row['name'],row['id'])
            index=self.libraries.findData(previous)
            if index>=0:self.libraries.setCurrentIndex(index)
            self.update_copy()
        self.scoped('intake.namespaces',{},libraries)

    def focus_inspection(self,ident):
        self.selected_id=ident;self.offset=0;self.refresh()

    def changed(self,*_):
        self.active_job=None;self.timer.stop();self.selected_id=self.saved.currentData();self.offset=0;self.copy_state='Explicit choice required';self.load()

    def choose(self):
        if not self.desktop():return
        path,_=QFileDialog.getOpenFileName(self,'Inspect package without admission','','ZIP package (*.zip);;Other input (*)')
        if path:self.inspect_path(path)

    def inspect_path(self,path):
        self.guard();self.inspect_button.setEnabled(False);self.status.setText('Reading bounded package bytes. Nothing is extracted, executed or admitted…')
        worker=self.scoped('intake.package.inspect',{'path':str(path)},self.inspected)
        if worker:worker.finished.connect(lambda:self.inspect_button.setEnabled(True) if isValid(self) and not self.host._closing else None)

    def inspected(self,value):
        self.selected_id=value['id'];self.offset=0;self.copy_state='Explicit choice required';self.loaded(value);self.refresh(reload=False)

    def load(self):
        if not self.selected_id:return
        ident=self.selected_id;offset=self.offset
        self.data=None;self.members.clear();self.detail.clear();self.copy_button.setEnabled(False)
        self.facts.setText('Reading the selected inspection…');self.issues.clear()
        self.scoped('intake.package.get',{'id':ident,'offset':offset,'limit':100},
                    lambda value:self.loaded(value) if (ident,offset)==(self.selected_id,self.offset) else None)

    def loaded(self,value):
        self.data=value;self.selected_id=value['id'];self.members.clear()
        copy_state=self.copy_state
        if copy_state=='Explicit choice required' and value['copy_observation']['state']=='READY_BATCH':copy_state='Existing review batch located'
        self.stage.setText('Inspection: '+value['state'].capitalize()+'\nCopy for review: '+copy_state+'\nAdmission: separate reference decisions; inspection grants none')
        size=value['bytes'];size_text=str(size)+' bytes' if size<1024 else str(round(size/1024,1))+' KiB' if size<1048576 else str(round(size/1048576,2))+' MiB'
        self.facts.setText(str(value['total'])+' file(s) · '+size_text+' package · encryption '+value['encryption'].lower()+
                           '\nTransport manifest: '+value['transport']['state'].replace('_',' ').lower()+' · dependencies '+value['transport']['dependencies'].replace('_',' ').lower()+
                           '\nObserved '+time.strftime('%H:%M:%S',time.localtime(value['observed_at']))+'. Copy checks the original hash again.')
        issues=value['issues']+value['transport'].get('missing',[])
        self.issues.setText(' · '.join(x.replace('_',' ').capitalize() for x in issues) if issues else 'Ready to copy for review. This is an integrity observation, not source acceptance.')
        if not value['rules_current']:self.issues.setText('Inspection rules changed. Inspect the original again before copying.')
        for row in value['members']:
            item=QTreeWidgetItem([row['name'],str(row['bytes']),row['sha256'][:16]+'…'])
            item.setToolTip(0,row['name']);item.setToolTip(2,row['sha256']);self.members.addTopLevelItem(item)
        self.page.setText(str(min(value['total'],value['offset']+1))+'–'+str(min(value['total'],value['offset']+len(value['members'])))+' of '+str(value['total']))
        self.stac.setText('package '+value['id']+' | contents');self.detail.setPlainText(json.dumps(value,indent=2,ensure_ascii=False));self.update_copy()

    def update_copy(self,*_):
        self.copy_button.setEnabled(bool(self.data and self.data['state']=='READY' and self.data['rules_current'] and self.libraries.currentData() and 'approve' in self.principal.scopes and not self.active_job))

    def page_by(self,direction):
        if not self.data:return
        offset=self.offset+direction*100
        if 0<=offset<self.data['total']:self.offset=offset;self.load()

    def copy_for_review(self):
        self.guard()
        if not self.data or not self.libraries.currentData():return
        self.copy_button.setEnabled(False)
        self.scoped('intake.package.copy',{'id':self.selected_id,'namespace':self.libraries.currentData()},self.copied,lambda e:self.update_copy())

    def copied(self,value):
        self.active_job=value['job'] if value['state']=='COPY_REQUESTED' else None
        self.copy_state='Job '+value['job'][:12]+' · '+value.get('job_state','already copied')
        if self.data:self.loaded(self.data)
        if self.active_job:self.timer.start()
        self.status.setText('Originals remain preserved. Open reference review for the separate admission decision.')

    def poll_job(self):
        self.guard()
        if not self.active_job:return
        self.scoped('jobs.get',{'id':self.active_job},self.job_loaded)

    def job_loaded(self,value):
        self.copy_state='Job '+value['id'][:12]+' · '+value['state']
        if value['state'] in ('Completed','Failed','Cancelled','Interrupted'):
            self.active_job=None;self.timer.stop()
        if self.data:self.loaded(self.data)

    def open_review(self):
        if self.desktop():self.bridge.show_intake()


def install(bridge):
    action=QAction('Workbench organizer…',bridge.host)
    action.setShortcut('Ctrl+Shift+J');action.triggered.connect(bridge.show_organizer)
    bridge.host.menu_groups['View'].addAction(action);bridge.host.a_organizer=action
