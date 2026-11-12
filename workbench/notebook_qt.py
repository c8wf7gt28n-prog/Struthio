"""Native notebook editing over catalog notes and checked Kernel references."""
import copy,json,uuid
from pathlib import Path
from PySide6.QtCore import Qt,QTimer
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import (QWidget,QDialog,QVBoxLayout,QHBoxLayout,QLabel,
 QPushButton,QLineEdit,QPlainTextEdit,QComboBox,QTreeWidget,QTreeWidgetItem,
 QHeaderView,QSplitter,QTabWidget,QDialogButtonBox,QFileDialog,QInputDialog,
 QCheckBox,QMessageBox,QGridLayout,QScrollArea)
from sdk.cli.arc1cli import notebook as core
from .engine import engineering
from .engineering_kernel import operator
from . import notebook_service
from . import locations

def plain(text=''):
    label=QLabel(text);label.setTextFormat(Qt.PlainText);label.setWordWrap(True);return label
def invoke(host,op,args=None):
    if host.concern.store is None or host.concern.store.path.resolve()!=notebook_service.path().resolve():raise ValueError('Notebook and desktop profiles differ. Reopen with one concern profile.')
    r=engineering(host.root).dispatch('notebook.'+op,args or {},operator())
    if not r['ok']:raise ValueError(r['error']['message'])
    return r['result']
def is_notebook(catalog,ident):
    with catalog.db() as db:
        return bool(db.execute("SELECT 1 FROM sqlite_master WHERE name='notebooks'").fetchone() and db.execute('SELECT 1 FROM notebooks WHERE id=?',(ident,)).fetchone())
def node_item(label,value):item=QTreeWidgetItem(label);item.setData(0,Qt.UserRole,value);return item

class ReferenceDialog(QDialog):
    OPTIONS=(('Saved concern note','note','catalog'),('Working requirement note','requirement','catalog'),
      ('Saved source file','source','file'),('Admitted original','source','intake'),
      ('Engineering register requirement','requirement','register'),('CSV table','table','csv'),
      ('Marginalia original (link only)','source','marginalia'),('Recorded job/result','result','job'),
      ('Find saved concern notes','query','catalog.search'),('List accessible jobs','query','jobs.list'),('Typed Office working table','table','office'))
    def __init__(self,host):
        super().__init__(host);self.host=host;self.value=None;self.setWindowTitle('Attach a checked reference');self.resize(720,540)
        box=QVBoxLayout(self);box.addWidget(plain('Choose an existing record or source. The notebook keeps a reference; its prose cannot alter that record.'))
        self.kind=QComboBox()
        for label,k,t in self.OPTIONS:self.kind.addItem(label,(k,t))
        self.kind.setAccessibleName('Notebook reference type');box.addWidget(self.kind)
        self.records=QComboBox();self.records.setAccessibleName('Existing concern note')
        for row in host.concern.store.snapshot()['objects']:
            if row['kind']=='note':self.records.addItem(row['title'],row['id'])
        box.addWidget(self.records);self.office_records=QComboBox();self.office_records.setAccessibleName('Saved Office working table');self.office_sheets=QComboBox();self.office_sheets.setAccessibleName('Referenced Office sheet');box.addWidget(self.office_records);box.addWidget(self.office_sheets);self.office_records.currentIndexChanged.connect(self.office_selected);self.office_sheets.currentIndexChanged.connect(self.clear);self.field_label=plain();box.addWidget(self.field_label)
        row=QHBoxLayout();self.field=QLineEdit();self.field.setAccessibleName('Source locator or read query');row.addWidget(self.field,1);self.browse=QPushButton('Choose file');self.browse.clicked.connect(self.choose_file);row.addWidget(self.browse);box.addLayout(row)
        self.inspect=QPushButton('Preview current reference');self.inspect.clicked.connect(self.prepare);box.addWidget(self.inspect)
        self.preview=QPlainTextEdit();self.preview.setReadOnly(True);self.preview.setAccessibleName('Checked reference preview');box.addWidget(self.preview,1)
        self.status=plain();box.addWidget(self.status);self.ack=QCheckBox('I reviewed this reference and its authority.');box.addWidget(self.ack)
        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);self.ok=buttons.button(QDialogButtonBox.Ok);self.ok.setText('Attach to draft');self.ok.setEnabled(False);buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject);box.addWidget(buttons)
        self.kind.currentIndexChanged.connect(self.changed);self.records.currentIndexChanged.connect(self.clear);self.field.textChanged.connect(self.clear);self.ack.toggled.connect(lambda checked:self.ok.setEnabled(bool(checked and self.value)));self.changed()
    def clear(self,*a):self.value=None;self.ack.setChecked(False);self.ok.setEnabled(False);self.preview.clear()
    def changed(self,*a):
        self.clear();kind,typ=self.kind.currentData();self.records.setVisible(typ=='catalog');self.field.setVisible(typ not in ('catalog','jobs.list','office'));self.browse.setVisible(typ in ('file','csv','marginalia'));self.office_records.setVisible(typ=='office');self.office_sheets.setVisible(typ=='office')
        label={'file':'File inside the attached workspace','csv':'CSV file inside the workspace; cells stay literal',
         'marginalia':'Original Marginalia file; linked as inert bytes, not executed',
         'intake':'Admitted intake item ID','register':'Existing engineering requirement record ID',
         'job':'Existing Kernel job ID','catalog.search':'Words to find in saved concern notes; read only',
         'jobs.list':'List accessible recorded jobs; read only','catalog':'Select a saved concern note','office':'Select a saved typed table and stable sheet identity'}
        self.field_label.setText(label[typ])
        if typ=='office':
            try:
                from .office_qt import invoke as office_invoke
                self.office_records.clear()
                for row in office_invoke(self.host,'list')['documents']:
                    if row['kind']=='table':self.office_records.addItem(row['title'],row['id'])
                self.office_selected()
            except (ValueError,OSError) as e:self.status.setText(str(e))
    def office_selected(self,*a):
        self.clear();self.office_sheets.clear();key=self.office_records.currentData()
        if not key:return
        try:
            from .office_qt import invoke as office_invoke
            value=office_invoke(self.host,'get',{'id':key})
            for s in value['document']['sheets']:self.office_sheets.addItem(s['name'],s['id'])
        except (ValueError,OSError) as e:self.status.setText(str(e))
    def choose_file(self):
        path,_=QFileDialog.getOpenFileName(self,'Choose an explicit source',str(self.host.root))
        if not path:return
        typ=self.kind.currentData()[1]
        if typ in ('file','csv'):
            try:path=Path(path).resolve().relative_to(self.host.root.resolve()).as_posix()
            except ValueError:self.status.setText('Choose a workspace file, or use the linked Marginalia profile for an external original.');return
        self.field.setText(str(path))
    def prepare(self):
        self.clear();kind,typ=self.kind.currentData();target={'type':typ}
        if typ=='catalog':target['object_id']=self.records.currentData()
        elif typ=='office':target.update(object_id=self.office_records.currentData(),sheet=self.office_sheets.currentData())
        elif typ in ('file','csv','marginalia'):
            target['path']=self.field.text()
            if typ=='marginalia':target['name']=Path(self.field.text()).name
        elif typ=='intake':target['item']=self.field.text().strip()
        elif typ=='register':target['record_id']=self.field.text().strip()
        elif typ=='job':target['id']=self.field.text().strip()
        elif typ=='catalog.search':target.update(query=self.field.text(),limit=20)
        else:target['limit']=20
        try:
            value=invoke(self.host,'reference.preview',{'kind':kind,'target':target})
            self.value=value;self.preview.setPlainText(json.dumps(value,indent=2,ensure_ascii=False));self.status.setText('Preview only. Attach adds this to the notebook draft; Save commits.')
        except (ValueError,OSError) as e:self.status.setText(str(e))

class NotebookPanel(QWidget):
    def __init__(self,host,ident):
        super().__init__(host);self.host=host;self.ident=ident;self.writer=uuid.uuid4().hex;self.recovered_writer=None;self.loading=True;self.dirty=False;self.current_id=None;self.last_read=None
        self.setProperty('concern_id',ident);self.setProperty('ledgerTitle','Engineering notebook')
        QFontDatabase.addApplicationFont(str(locations.program(host.root)/'branding/fonts/NotoSansCJKsc-Regular.otf'))
        outer=QVBoxLayout(self);outer.setContentsMargins(0,0,0,0);self.scroll=QScrollArea();self.scroll.setWidgetResizable(True);outer.addWidget(self.scroll);content=QWidget();self.scroll.setWidget(content)
        box=QVBoxLayout(content);self.title_edit=QLineEdit();self.title_edit.setAccessibleName('Notebook title');box.addWidget(self.title_edit)
        box.addWidget(plain('Working notebook · references preserve original identity and authority. Save commits; recovery drafts stay separate.'))
        row=QGridLayout();self.add=QPushButton('Add idea');self.add.clicked.connect(self.add_idea);row.addWidget(self.add,0,0)
        self.attach=QPushButton('Attach reference');self.attach.setToolTip('Preview and attach a saved record, original, table or read-only query');self.attach.clicked.connect(self.attach_reference);row.addWidget(self.attach,0,1)
        self.save_button=QPushButton('Save notebook');self.save_button.clicked.connect(self.save_concern_note);row.addWidget(self.save_button,1,0)
        self.recover=QPushButton('Review recovery');self.recover.clicked.connect(self.review_recovery);row.addWidget(self.recover,1,1);box.addLayout(row)
        split=QSplitter(Qt.Horizontal);self.split=split;split.setChildrenCollapsible(False);left=QWidget();l=QVBoxLayout(left);l.setContentsMargins(0,0,0,0)
        self.blocks=QTreeWidget();self.blocks.setRootIsDecorated(False);self.blocks.setHeaderLabels(['Block','Kind']);self.blocks.header().setSectionResizeMode(0,QHeaderView.Stretch);self.blocks.setAccessibleName('Notebook blocks');self.blocks.itemSelectionChanged.connect(self.selected);l.addWidget(self.blocks,1)
        row=QHBoxLayout();up=QPushButton('Up');down=QPushButton('Down');remove=QPushButton('Remove');up.clicked.connect(lambda:self.move(-1));down.clicked.connect(lambda:self.move(1));remove.clicked.connect(self.remove);row.addWidget(up);row.addWidget(down);row.addWidget(remove);l.addLayout(row);split.addWidget(left)
        right=QWidget();r=QVBoxLayout(right);r.setContentsMargins(0,0,0,0);self.block_title=QLineEdit();self.block_title.setAccessibleName('Notebook block title');r.addWidget(self.block_title)
        self.kind_label=plain();r.addWidget(self.kind_label);self.pages=QTabWidget()
        self.body=QPlainTextEdit();self.body.setProperty('arcReadingRole','prose');self.body.setAccessibleName('Working block prose or caption');self.pages.addTab(self.body,'Working prose')
        self.reference=QPlainTextEdit();self.reference.setReadOnly(True);self.reference.setProperty('arcReadingRole','prose');self.reference.setAccessibleName('Referenced content and currentness');self.pages.addTab(self.reference,'Reference')
        self.reading=QPlainTextEdit();self.reading.setReadOnly(True);self.reading.setAccessibleName('Read-only referenced record details');self.pages.addTab(self.reading,'Record details');self.reading.textChanged.connect(self.present_reference);self.pages.setMinimumHeight(200);r.addWidget(self.pages,1)
        row=QVBoxLayout();self.inspect=QPushButton('Inspect reference');self.inspect.clicked.connect(self.inspect_reference);row.addWidget(self.inspect)
        self.refresh_ref=QPushButton('Review binding');self.refresh_ref.clicked.connect(self.rebind);row.addWidget(self.refresh_ref)
        self.run=QPushButton('Run read query');self.run.setToolTip('Run the saved read-only query; no engineering job or accepted fact is created');self.run.clicked.connect(self.run_query);row.addWidget(self.run);r.addLayout(row)
        self.keep_result=QPushButton('Keep result block');self.keep_result.clicked.connect(self.keep_query_result);r.addWidget(self.keep_result)
        split.addWidget(right);split.setStretchFactor(1,3);box.addWidget(split,1)
        self.status=plain();self.status.setAccessibleName('Notebook save and reference status');box.addWidget(self.status)
        self.original=QPushButton('Inspect import original and losses');self.original.clicked.connect(self.inspect_original);box.addWidget(self.original)
        for button in self.findChildren(QPushButton):button.setMinimumHeight(button.sizeHint().height())
        self.timer=QTimer(self);self.timer.setSingleShot(True);self.timer.setInterval(650);self.timer.timeout.connect(self.flush_draft)
        self.title_edit.textChanged.connect(self.title_changed);self.block_title.textChanged.connect(self.edit_current);self.body.textChanged.connect(self.edit_current)
        self.load(invoke(host,'get',{'id':ident}));self.loading=False
        if host.concern.store.path.resolve()!=notebook_service.path().resolve():
            for button in (self.add,self.attach,self.save_button,self.recover):button.setEnabled(False)
            self.body.setReadOnly(True);self.title_edit.setReadOnly(True);self.status.setText('Desktop and service profiles differ. Reopen with one concern profile before editing.')
    def resizeEvent(self,event):
        super().resizeEvent(event)
        if not hasattr(self,'split'):return
        narrow=self.width()<650;self.split.setOrientation(Qt.Vertical if narrow else Qt.Horizontal);self.split.setMinimumHeight(730 if narrow else 500);self.blocks.setMinimumHeight(110);self.blocks.setMaximumHeight(150 if narrow else 16777215)
    def present_reference(self):
        raw=self.reading.toPlainText()
        if not raw:self.reference.clear();return
        try:value=json.loads(raw)
        except ValueError:self.reference.setPlainText(raw);return
        record=value.get('record',value);lines=[value.get('state','Reviewed reading').replace('_',' ').capitalize()]
        if value.get('message'):lines.append(value['message'])
        if isinstance(record,dict):
            authority=record.get('authority',value.get('authority','Working material'))
            lines.append(authority.replace('_',' ').capitalize());lines.append('')
            for key in ('title','name','path'):
                if record.get(key):lines.append(str(record[key]))
            if isinstance(record.get('note'),dict):lines.append(record['note'].get('body',''))
            if isinstance(record.get('text'),str):lines.append(record['text'])
            if isinstance(record.get('rows'),list):
                for row in record['rows']:lines.append(' | '.join(str(v) for v in row) if isinstance(row,list) else str(row.get('title',row.get('tool',row.get('id','')))))
            if record.get('preview_truncated'):lines.append('Preview is truncated. The binding covers the complete bounded original.')
            if isinstance(record.get('record'),dict):
                saved=record['record'];job=saved.get('job')
                if isinstance(job,dict):lines.extend([str(job.get('tool','Recorded job'))+' · '+str(job.get('state','')),str(saved.get('facts',{}))])
                elif isinstance(saved.get('rows'),list):lines.extend(str(row.get('title',row.get('tool',row.get('id','')))) for row in saved['rows'])
            if record.get('definition'):lines.append('Saved read-only query: '+str(record['definition']))
        lines.extend(['','Working prose changes no referenced original or accepted fact.','Record details contains the exact locator, hash and structured reading.']);self.reference.setPlainText('\n'.join(lines))
    def title(self):return self.doc['title']+(' •' if self.dirty else '')
    def is_dirty(self):return self.dirty
    def set_dirty(self,value=True):
        self.dirty=value;self.save_button.setEnabled(value)
        if value:self.timer.start()
        else:self.timer.stop()
        index=self.host.tabs.indexOf(self)
        if index>=0:self.host.tabs.setTabText(index,self.title())
        self.host.concern.track_current()
    def load(self,saved):
        select=self.current_id;self.loading=True;self.base=saved;self.doc=copy.deepcopy(saved['document']);self.title_edit.setText(self.doc['title']);self.current_id=None;self.last_read=None;self.rebuild(select);self.loading=False;self.set_dirty(False);self.status.setText('Saved working notebook. References are checked when inspected.');self.buttons()
    def rebuild(self,select=None):
        self.blocks.clear()
        for b in self.doc['blocks']:self.blocks.addTopLevelItem(node_item([b['title'],b['kind']],b['id']))
        for i in range(self.blocks.topLevelItemCount()):
            item=self.blocks.topLevelItem(i)
            if item.data(0,Qt.UserRole)==select:self.blocks.setCurrentItem(item);break
        else:
            if self.blocks.topLevelItemCount():self.blocks.setCurrentItem(self.blocks.topLevelItem(0))
        if not self.blocks.topLevelItemCount():self.current_id=None;self.body.clear();self.block_title.clear()
    def current(self):return next((b for b in self.doc['blocks'] if b['id']==self.current_id),None)
    def selected(self):
        item=self.blocks.currentItem();self.loading=True;self.current_id=item.data(0,Qt.UserRole) if item else None;b=self.current()
        self.block_title.setText(b['title'] if b else '');self.body.setPlainText(b['body'] if b else '');self.reading.clear();self.last_read=None
        self.kind_label.setText((b['kind'].capitalize()+' · '+('working prose; no record authority' if b['kind'] in ('text','unsupported') else 'checked reference; prose does not change the original')) if b else 'Choose or add a block')
        self.loading=False;self.buttons()
    def buttons(self):
        b=self.current();reference=bool(b and b['kind'] not in ('text','unsupported'));self.inspect.setEnabled(reference and not self.dirty);self.refresh_ref.setEnabled(reference);self.run.setEnabled(bool(b and b['kind']=='query' and not self.dirty));self.keep_result.setEnabled(bool(self.last_read));self.block_title.setEnabled(b is not None);self.body.setEnabled(b is not None)
    def title_changed(self,text):
        if not self.loading:self.doc['title']=text;self.set_dirty();self.buttons()
    def edit_current(self,*a):
        if self.loading or not self.current():return
        b=self.current();b.update(title=self.block_title.text(),body=self.body.toPlainText());item=self.blocks.currentItem()
        if item:item.setText(0,b['title'])
        self.set_dirty();self.buttons()
    def add_idea(self):
        b=core.block();self.doc['blocks'].append(b);self.rebuild(b['id']);self.set_dirty();self.buttons();self.body.setFocus()
    def attach_reference(self):
        dialog=ReferenceDialog(self.host)
        if dialog.exec()!=QDialog.Accepted or not dialog.value:return
        v=dialog.value;b=core.block(v['kind'],dialog.kind.currentText(),target_value=v['target'],binding=v['binding']);self.doc['blocks'].append(b);self.rebuild(b['id']);self.set_dirty();self.buttons();self.reading.setPlainText(json.dumps(v,indent=2,ensure_ascii=False))
    def move(self,direction):
        b=self.current()
        if not b:return
        i=self.doc['blocks'].index(b);j=i+direction
        if not 0<=j<len(self.doc['blocks']):return
        self.doc['blocks'][i],self.doc['blocks'][j]=self.doc['blocks'][j],self.doc['blocks'][i];self.rebuild(b['id']);self.set_dirty();self.buttons()
    def remove(self):
        b=self.current()
        if b:self.doc['blocks'].remove(b);self.rebuild();self.set_dirty();self.buttons();self.status.setText('Removed from the draft. Save archives the block; its saved note is retained.')
    def flush_draft(self):
        if not self.dirty:return True
        try:invoke(self.host,'draft.save',{'id':self.ident,'writer':self.writer,'base_revision':self.base['revision'],'document':self.doc});self.status.setText('Unsaved notebook draft is recoverable. Save commits.');return True
        except (ValueError,OSError) as e:self.status.setText('Draft could not be stored: '+str(e));return False
    def save_concern_note(self):
        self.timer.stop()
        try:
            saved=invoke(self.host,'save',{'id':self.ident,'expected_revision':self.base['revision'],'document':self.doc})
            cleanup=[]
            for writer in {self.writer,self.recovered_writer}-{None}:
                try:invoke(self.host,'draft.discard',{'id':self.ident,'writer':writer})
                except (ValueError,OSError):cleanup.append(writer)
            self.recovered_writer=None;self.load(saved);self.host.concern.changed.emit();self.host.concern.rebuild();self.status.setText('Notebook saved. '+('A recovery draft could not be cleared; review it before recovering.' if cleanup else 'Original sources and engineering records are unchanged.'));return True
        except (ValueError,OSError) as e:self.flush_draft();self.status.setText(str(e)+' · Your working draft is retained.');return False
    def review_recovery(self):
        try:rows=invoke(self.host,'drafts',{'id':self.ident})['drafts'];saved=invoke(self.host,'get',{'id':self.ident})
        except ValueError as e:self.status.setText(str(e));return
        if not rows:self.status.setText('No recovery draft is stored.');return
        row=rows[0];dialog=QDialog(self);dialog.setWindowTitle('Review notebook recovery');dialog.resize(820,650);box=QVBoxLayout(dialog)
        box.addWidget(plain('Recovery loads a working draft. Save is still required. A changed saved base must be compared and merged explicitly.'))
        text=QPlainTextEdit();text.setReadOnly(True);text.setPlainText(json.dumps({'draft':row,'current_saved':saved['document']},indent=2,ensure_ascii=False));box.addWidget(text)
        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);buttons.button(QDialogButtonBox.Ok).setText('Recover for review');buttons.button(QDialogButtonBox.Ok).setEnabled(row['base_revision']==saved['revision']);buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);box.addWidget(buttons)
        if dialog.exec()==QDialog.Accepted:
            self.load(saved);self.doc=copy.deepcopy(row['document']);self.recovered_writer=row['writer'];self.loading=True;self.title_edit.setText(self.doc['title']);self.loading=False;self.rebuild();self.set_dirty();self.buttons();self.status.setText('Recovered into a draft. Save commits; accepted records stay separate.')
    def inspect_reference(self):
        b=self.current()
        if not b or self.dirty:return
        try:v=invoke(self.host,'resolve',{'id':self.ident,'block':b['id']});self.reading.setPlainText(json.dumps(v,indent=2,ensure_ascii=False));self.pages.setCurrentIndex(1);self.status.setText(v.get('message') or 'Reference '+v['state'].lower()+'. This read changes no source or accepted record.')
        except ValueError as e:self.status.setText(str(e))
    def rebind(self):
        b=self.current()
        if not b:return
        try:
            v=invoke(self.host,'reference.preview',{'kind':b['kind'],'target':b['target']});b['binding']=v['binding'];self.reading.setPlainText(json.dumps(v,indent=2,ensure_ascii=False));self.pages.setCurrentIndex(1);self.set_dirty();self.buttons();self.status.setText('Current reference preview loaded. Review it and Save to retain this binding.')
        except ValueError as e:self.status.setText(str(e))
    def run_query(self):
        b=self.current()
        if not b or self.dirty:return
        try:self.last_read=invoke(self.host,'query.run',{'id':self.ident,'block':b['id'],'expected_revision':self.base['revision']});self.reading.setPlainText(json.dumps(self.last_read,indent=2,ensure_ascii=False));self.pages.setCurrentIndex(1);self.status.setText('Read-only query recorded. No engineering job or source acceptance was created.');self.buttons()
        except ValueError as e:self.status.setText(str(e))
    def keep_query_result(self):
        if not self.last_read:return
        try:
            value=invoke(self.host,'reference.preview',{'kind':'result','target':{'type':'query_read','id':self.last_read['id']}})
            b=core.block('result','Recorded query reading',target_value=value['target'],binding=value['binding']);self.doc['blocks'].append(b);self.rebuild(b['id']);self.set_dirty();self.buttons()
        except ValueError as e:self.status.setText(str(e))
    def inspect_original(self):
        try:v=invoke(self.host,'original',{'id':self.ident});self.reading.setPlainText(json.dumps(v,indent=2,ensure_ascii=False));self.pages.setCurrentIndex(1)
        except ValueError as e:self.status.setText(str(e))
    def can_close_concern(self):
        if not self.dirty:return True
        self.flush_draft();box=QMessageBox(self);box.setWindowTitle('Keep notebook changes');box.setTextFormat(Qt.PlainText);box.setText('Save this notebook before closing? Discard removes this writer’s draft; other recovery drafts remain.');box.setStandardButtons(QMessageBox.Save|QMessageBox.Discard|QMessageBox.Cancel)
        result=box.exec()
        if result==QMessageBox.Save:return self.save_concern_note()
        if result==QMessageBox.Discard:
            try:invoke(self.host,'draft.discard',{'id':self.ident,'writer':self.writer});self.set_dirty(False);return True
            except ValueError as e:self.status.setText(str(e));return False
        return False

def open_notebook(host,ident):
    if host.concern.store is None or host.concern.store.path.resolve()!=notebook_service.path().resolve():
        host.statusBar().showMessage('Notebook and desktop profiles differ. Reopen with one concern profile.',10000)
        return None
    for i in range(host.tabs.count()):
        tab=host.tabs.widget(i)
        if isinstance(tab,NotebookPanel) and tab.ident==ident:
            host.tabs.setCurrentIndex(i);return tab
    tab=NotebookPanel(host,ident);i=host.tabs.addTab(tab,host.nav_icon('folder'),tab.title());host.tabs.setCurrentIndex(i);return tab
class NotebookHub(QDialog):
    def __init__(self,host,parent):
        super().__init__(host);self.host=host;self.parent_id=parent;self.setWindowTitle('Engineering notebooks');self.resize(620,460);box=QVBoxLayout(self)
        box.addWidget(plain('Working notebooks belong to the concern. Existing Marginalia originals can be linked from a notebook without executing or replacing them.'))
        self.list=QTreeWidget();self.list.setRootIsDecorated(False);self.list.setHeaderLabels(['Notebook','State']);self.list.header().setSectionResizeMode(0,QHeaderView.Stretch);box.addWidget(self.list,1)
        row=QHBoxLayout();new=QPushButton('New notebook');new.clicked.connect(self.create);row.addWidget(new);open_b=QPushButton('Open selected');open_b.clicked.connect(self.open);row.addWidget(open_b);imp=QPushButton('Import AppFlowy JSON');imp.clicked.connect(self.import_file);row.addWidget(imp);box.addLayout(row);self.status=plain();box.addWidget(self.status);self.reload()
    def reload(self):
        self.list.clear()
        try:
            for row in invoke(self.host,'list')['notebooks']:self.list.addTopLevelItem(node_item([row['title'],row['state']],row['id']))
        except ValueError as e:self.status.setText(str(e))
    def create(self):
        title,ok=QInputDialog.getText(self,'New engineering notebook','Title')
        if not ok:return
        try:v=invoke(self.host,'create',{'title':title,'parent':self.parent_id});self.host.concern.rebuild();open_notebook(self.host,v['id']);self.close()
        except ValueError as e:self.status.setText(str(e))
    def open(self):
        item=self.list.currentItem()
        if item:open_notebook(self.host,item.data(0,Qt.UserRole));self.close()
    def import_file(self):
        path,_=QFileDialog.getOpenFileName(self,'Choose an AppFlowy Editor document JSON','','JSON (*.json)')
        if not path:return
        try:value=invoke(self.host,'import.preview',{'path':path,'parent':self.parent_id})
        except ValueError as e:self.status.setText(str(e));return
        dialog=QDialog(self);dialog.setWindowTitle('Review one-way AppFlowy import');dialog.resize(850,700);box=QVBoxLayout(dialog)
        box.addWidget(plain('Literal working blocks only. Formatting/nesting losses and every unsupported block are listed. Imported instructions and queries stay inert.'))
        text=QPlainTextEdit();text.setReadOnly(True);text.setPlainText(json.dumps(value,indent=2,ensure_ascii=False));box.addWidget(text,1)
        ack=QCheckBox('I reviewed the original identity, working blocks and loss report.');box.addWidget(ack);buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);buttons.button(QDialogButtonBox.Ok).setText('Commit working notebook');buttons.button(QDialogButtonBox.Ok).setEnabled(False);ack.toggled.connect(buttons.button(QDialogButtonBox.Ok).setEnabled);buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);box.addWidget(buttons)
        if dialog.exec()!=QDialog.Accepted:return
        try:r=invoke(self.host,'import.commit',{'plan':value['id'],'expected_digest':value['digest']});self.host.concern.rebuild();open_notebook(self.host,r['notebook']);self.close()
        except ValueError as e:self.status.setText(str(e))
def hub(host,parent='inbox'):
    dialog=NotebookHub(host,parent);host._notebook_hub=dialog;dialog.show();return dialog
