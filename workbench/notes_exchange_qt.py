"""Native optional exchange desk; existing concern notes remain the editor."""
from .text_prompts import writing_prompt
import json
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QLabel,QComboBox,
 QLineEdit,QPushButton,QFileDialog,QPlainTextEdit,QTreeWidget,QTreeWidgetItem,
 QHeaderView,QCheckBox,QTabWidget,QWidget,QSplitter,QDialogButtonBox)
from .engine import engineering
from .engineering_kernel import operator
from . import notes_exchange
from sdk.cli.arc1cli.notes_exchange import PROFILES
from . import locations
ACTION={'NEW':'New','UPDATE':'Update','RENAME':'Rename','ALIASES':'Link aliases','RESTORE_REFERENCE':'Reference restored','UNCHANGED':'Unchanged','CONFLICT':'Conflict','CONFLICT_HELD':'Conflict held','UPSTREAM_DELETED':'Upstream missing'}
GAP={'ACTIVE_MARKUP_OR_URI_RETAINED_AS_TEXT':'Active-looking markup stays literal text',
 'EMBEDS_ARE_REFERENCES_ONLY':'Embeds are references',
 'COMPLEX_YAML_RETAINED_UNINTERPRETED':'Complex metadata retained as text',
 'YAML_TAGS_ALIASES_INERT':'YAML tags and aliases stay inert',
 'LOGSEQ_QUERIES_EMBEDS_INERT':'Queries and embeds stay inert',
 'ORG_CODE_INCLUDE_AND_CALLS_INERT':'Code and includes stay inert',
 'WORKING_TEXT_NORMALIZED_ORIGINAL_BYTES_RETAINED':'Working line endings normalized; originals retained',
 'SAVED_NOTE_PRESERVED':'Saved note retained',
 'EDITED_WORKING_TEXT_EXPORTED_AS_UTF8_LF':'Edited notes use UTF-8 with LF line endings.',
 'UPSTREAM_DELETION_DID_NOT_DELETE_SAVED_NOTE':'Notes missing upstream were retained.',
 'LEDGER_PATH_ALIASES_REQUIRE_SIDECAR_OTHER_APPS_MAY_NOT_RESOLVE':'Rename aliases are in the Graphite sidecar; other apps may need updated links.',
 'UNRESOLVED_INCOMING_EXCLUDED_CURRENT_NOTE_EXPORTED':'Held incoming versions are excluded; current saved notes are exported.',
 'CATALOG_TITLE_RETAINED_IN_SIDECAR_BODY_NOT_REWRITTEN':'Catalog titles are in the sidecar; note text is unchanged.',
 'REMOVED_ATTACHMENTS_RETAINED_FOR_SAVED_NOTES':'Missing upstream attachments were retained for saved notes.'}

def plain(text=''):
    value=QLabel(text);value.setTextFormat(Qt.PlainText);value.setWordWrap(True);return value
def table(labels):
    t=QTreeWidget();t.setRootIsDecorated(False);t.setHeaderLabels(labels);t.header().setSectionResizeMode(0,QHeaderView.Stretch);return t
class ExchangeDialog(QDialog):
    def __init__(self,host,parent='inbox'):
        super().__init__(host);self.host=host;self.kernel=engineering(host.root);self.principal=operator();self.parent_id=parent;self.plan=None;self.current=None;self.pending=None
        self.setWindowTitle('Notes exchange');self.resize(1000,820)
        QFontDatabase.addApplicationFont(str(locations.program(host.root)/'branding/fonts/NotoSansCJKsc-Regular.otf'))
        box=QVBoxLayout(self)
        box.addWidget(plain('Optional notes toolbox · working notes remain in the concern catalog. Originals, source acceptance and engineering evidence stay separate.'))
        self.status=plain();self.status.setAccessibleName('Notes exchange status')
        self.tabs=QTabWidget();box.addWidget(self.tabs,1)
        review=QWidget();r=QVBoxLayout(review)
        row=QHBoxLayout();self.profile=QComboBox()
        for key,title in PROFILES.items():self.profile.addItem(title,key)
        self.profile.setAccessibleName('Notes exchange format profile');row.addWidget(self.profile,1)
        self.collections=QComboBox();self.collections.setAccessibleName('Notes exchange collection');row.addWidget(self.collections,1);r.addLayout(row)
        row=QHBoxLayout();self.folder=QLineEdit();writing_prompt(self.folder, 'Choose an explicit notes export or vault folder');self.folder.setAccessibleName('Notes source folder')
        browse=QPushButton('Choose folder');browse.clicked.connect(self.browse);row.addWidget(self.folder,1);row.addWidget(browse);r.addLayout(row)
        self.prepare=QPushButton('Preview exchange');self.prepare.clicked.connect(self.prepare_plan);r.addWidget(self.prepare)
        self.details=QPushButton('Review exchange details');self.details.clicked.connect(self.show_details);r.addWidget(self.details)
        split=QSplitter(Qt.Vertical);self.changes=table(['Change','Note','Path','Gaps']);self.changes.setAccessibleName('Reviewed notes exchange changes');self.changes.itemSelectionChanged.connect(self.show_incoming);split.addWidget(self.changes)
        self.changes.header().setSectionResizeMode(0,QHeaderView.ResizeToContents);self.changes.header().setSectionResizeMode(1,QHeaderView.Stretch);self.changes.setColumnWidth(2,240);self.changes.setColumnWidth(3,240)
        self.preview=QPlainTextEdit();self.preview.setReadOnly(True);self.preview.setAccessibleName('Exact inert incoming note preview');split.addWidget(self.preview);split.setStretchFactor(1,2);r.addWidget(split,1)
        self.ack=QCheckBox('I reviewed this exchange. Conflicting local notes will be preserved for separate resolution.');self.ack.toggled.connect(self.buttons);r.addWidget(self.ack)
        self.commit=QPushButton('Commit reviewed exchange');self.commit.clicked.connect(self.commit_plan);r.addWidget(self.commit)
        self.tabs.addTab(review,'Review exchange')
        saved=QWidget();s=QVBoxLayout(saved);row=QHBoxLayout();self.saved=QComboBox();self.saved.setAccessibleName('Saved exchange collection');row.addWidget(self.saved,1)
        reload=QPushButton('Refresh collection');reload.clicked.connect(self.reload_saved);row.addWidget(reload);s.addLayout(row)
        split=QSplitter(Qt.Vertical);self.notes=table(['Saved note','Source path','State']);self.notes.setAccessibleName('Saved exchanged notes');self.notes.itemSelectionChanged.connect(self.show_saved);split.addWidget(self.notes)
        self.notes.setColumnWidth(1,240);self.notes.header().setSectionResizeMode(2,QHeaderView.ResizeToContents)
        self.reading=QPlainTextEdit();self.reading.setReadOnly(True);self.reading.setAccessibleName('Saved note and backlink reading');split.addWidget(self.reading);split.setStretchFactor(1,2);s.addWidget(split,1)
        row=QHBoxLayout();self.open=QPushButton('Open working note');self.open.clicked.connect(self.open_note);row.addWidget(self.open)
        self.export=QPushButton('Export collection ZIP');self.export.clicked.connect(self.export_saved);row.addWidget(self.export)
        self.conflict_button=QPushButton('Review incoming conflict');self.conflict_button.clicked.connect(self.review_conflict);row.addWidget(self.conflict_button);s.addLayout(row)
        self.resolve_ack=QCheckBox('I reviewed this incoming conflict and the current saved note.');self.resolve_ack.toggled.connect(self.buttons);s.addWidget(self.resolve_ack)
        row=QHBoxLayout();self.keep=QPushButton('Keep local note');self.take=QPushButton('Use incoming note');self.keep.clicked.connect(lambda:self.resolve('keep-local'));self.take.clicked.connect(lambda:self.resolve('use-incoming'));row.addWidget(self.keep);row.addWidget(self.take);s.addLayout(row)
        self.tabs.addTab(saved,'Saved collections');box.addWidget(self.status)
        close=QDialogButtonBox(QDialogButtonBox.Close);close.rejected.connect(self.reject);box.addWidget(close)
        self.folder.textChanged.connect(self.invalidate);self.profile.currentIndexChanged.connect(self.invalidate);self.collections.currentIndexChanged.connect(self.invalidate);self.saved.currentIndexChanged.connect(self.reload_saved)
        self.refresh_collections()
        if host.concern.store is None or host.concern.store.path.resolve()!=notes_exchange.path().resolve():
            self.prepare.setEnabled(False);self.status.setText('This window and the background service use different concern profiles. Reopen Graphite with one profile before exchanging notes.')
        self.buttons()
    def call(self,op,args=None):
        reply=self.kernel.dispatch('notes.exchange.'+op,args or {},self.principal)
        if not reply['ok']:self.status.setText(reply['error']['message']);return None
        return reply['result']
    def refresh_collections(self,select=None):
        reply=self.call('collections')
        if reply is None:return
        for widget in (self.collections,self.saved):
            prior=select or widget.currentData();widget.blockSignals(True);widget.clear()
            if widget is self.collections:widget.addItem('New collection in this working area',None)
            for c in reply['collections']:widget.addItem(c['title']+' · '+c['profile'],c['id'])
            widget.setCurrentIndex(max(0,widget.findData(prior)));widget.blockSignals(False)
        self.reload_saved()
    def invalidate(self,*a):
        self.plan=None;self.ack.setChecked(False);self.changes.clear();self.preview.clear();self.buttons()
    def buttons(self,*a):
        self.commit.setEnabled(bool(self.plan and self.ack.isChecked()))
        self.details.setEnabled(bool(self.plan))
        current=bool(self.current);self.open.setEnabled(current);self.conflict_button.setEnabled(current and self.current.get('pending_conflict',False))
        for button in (self.keep,self.take):button.setEnabled(bool(self.pending and self.resolve_ack.isChecked()))
        self.export.setEnabled(bool(self.saved.currentData()))
    def browse(self):
        path=QFileDialog.getExistingDirectory(self,'Choose optional notes source')
        if path:self.folder.setText(path)
    def prepare_plan(self):
        self.invalidate()
        args={'path':self.folder.text(),'profile':self.profile.currentData(),'parent':self.parent_id}
        if self.collections.currentData():args['collection']=self.collections.currentData()
        value=self.call('preview',args)
        if value is None:return
        self.plan=value
        for e in value['entries']:
            item=QTreeWidgetItem([ACTION.get(e['action'],e['action']),e['title'],e['path'],', '.join(GAP.get(w,w.replace('_',' ').capitalize()) for w in e['warnings'])])
            for i in range(4):item.setToolTip(i,item.text(i))
            item.setData(0,Qt.UserRole,e['key']);self.changes.addTopLevelItem(item)
        self.status.setText('Preview only · '+str(len(value['entries']))+' notes · '+str(len(value['assets']))+' attachments · '+str(len(value['graph']))+' static links. '+str(len(value['ignored']))+' configuration/unsupported entries excluded; review details for the full list. Nothing committed.')
        if self.changes.topLevelItemCount():self.changes.setCurrentItem(self.changes.topLevelItem(0))
        self.buttons()
    def show_details(self):
        if self.plan:self.preview.setPlainText(json.dumps({k:self.plan[k] for k in ('profile','source_fingerprint','ignored','assets','graph','authority','conversion')},indent=2,ensure_ascii=False))
    def show_incoming(self):
        item=self.changes.currentItem()
        if not self.plan or item is None:return
        value=self.call('plan_note',{'plan':self.plan['id'],'expected_digest':self.plan['digest'],'key':item.data(0,Qt.UserRole)})
        if value:
            self.preview.setPlainText((value['incoming_body'] if value['incoming_body'] is not None else 'Upstream deletion: the saved Graphite note will remain.')+'\n\nMetadata and gaps\n'+json.dumps(value['metadata'],indent=2,ensure_ascii=False)+'\n'+json.dumps(value['entry'],indent=2,ensure_ascii=False))
    def commit_plan(self):
        if not self.plan or not self.ack.isChecked():return
        value=self.call('commit',{'plan':self.plan['id'],'expected_digest':self.plan['digest']})
        if value:
            self.invalidate();self.host.concern.changed.emit();self.refresh_collections(value['collection']);self.tabs.setCurrentIndex(1);self.status.setText('Committed working notes: '+', '.join(str(n)+' '+ACTION.get(k,k).lower() for k,n in value['counts'].items())+'. Originals unchanged; no facts accepted.')
    def reload_saved(self,*a):
        self.notes.clear();self.reading.clear();self.current=None;self.pending=None;self.resolve_ack.setChecked(False)
        if self.saved.currentData():
            value=self.call('get',{'collection':self.saved.currentData()})
            if value:
                for n in value['notes']:
                    state='Conflict held' if n['pending_conflict'] else 'Upstream missing; note kept' if n['upstream_deleted'] else 'Saved'
                    item=QTreeWidgetItem([n['title'],n['path'],state]);item.setData(0,Qt.UserRole,n['key']);self.notes.addTopLevelItem(item)
                    for i in range(3):item.setToolTip(i,item.text(i))
                if self.notes.topLevelItemCount():self.notes.setCurrentItem(self.notes.topLevelItem(0))
        self.buttons()
    def show_saved(self):
        self.current=None;self.pending=None;self.resolve_ack.setChecked(False);item=self.notes.currentItem()
        if item:
            value=self.call('note',{'collection':self.saved.currentData(),'key':item.data(0,Qt.UserRole)})
            if value:
                self.current=value['note'];self.reading.setPlainText(self.current['body']+'\n\nMetadata\n'+json.dumps(self.current['metadata'],indent=2,ensure_ascii=False)+'\n\nBacklinks\n'+json.dumps(value['backlinks'],indent=2,ensure_ascii=False))
        self.buttons()
    def open_note(self):
        if self.current:
            editor=self.host.concern.open(self.current['object_id'])
            if editor is not None:editor.pages.setCurrentIndex(1)
            self.status.setText('The existing concern note editor is open. Save commits; recovery drafts remain separate.')
    def review_conflict(self):
        if not self.current:return
        value=self.call('conflict',{'collection':self.saved.currentData(),'key':self.current['key']})
        if value:
            self.pending=value;self.resolve_ack.setChecked(False);self.reading.setPlainText('CURRENT SAVED NOTE\n'+self.current['body']+'\n\nINCOMING FOR REVIEW\n'+value['body']+'\n\nIncoming SHA-256 '+value['sha256']);self.buttons()
    def resolve(self,choice):
        if not self.pending or not self.current or not self.resolve_ack.isChecked():return
        value=self.call('resolve',{'collection':self.saved.currentData(),'key':self.current['key'],'incoming_sha256':self.pending['sha256'],'expected_note_version':self.current['version'],'choice':choice})
        if value:self.host.concern.changed.emit();self.reload_saved();self.status.setText('Conflict resolved: '+choice+'. No source or engineering fact accepted.')
    def export_saved(self):
        if not self.saved.currentData():return
        filename,_=QFileDialog.getSaveFileName(self,'Export reviewed working notes','Ledger_notes_exchange.zip','ZIP exchange (*.zip)')
        if not filename:return
        value=self.call('export',{'collection':self.saved.currentData(),'path':filename})
        if value:self.status.setText('Exported '+str(value['files'])+' inert files. '+ ' '.join(dict.fromkeys(GAP.get(w['gap'],w['gap'].replace('_',' ').capitalize()) for w in value['warnings']))+' Full details are in the ZIP manifest.')
def show(host,parent='inbox'):
    dialog=ExchangeDialog(host,parent);host._notes_exchange_dialog=dialog;dialog.show();return dialog
