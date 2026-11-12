"""Native reviewed projections, before any per-device content publication."""
import base64,hashlib,json
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase,QImage,QPixmap
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QLabel,QComboBox,QPushButton,QPlainTextEdit,QCheckBox,QDialogButtonBox,QTabWidget,QScrollArea)
from .engine import engineering
from .engineering_kernel import operator
from . import locations

LABELS={'object':'Object','sources':'Sources','evidence':'Evidence','review':'Candidate review','pdf':'PDF page'}

class DeckDialog(QDialog):
    def __init__(self,host,window_id,principal=None):
        super().__init__(host);self.host=host;self.kernel=engineering(host.root);self.principal=principal or operator();self.ident=window_id;self.preview=None
        cjk=locations.program(host.root)/'branding/fonts/NotoSansCJKsc-Regular.otf'
        if cjk.is_file():QFontDatabase.addApplicationFont(str(cjk))
        self.setWindowTitle('Review a shared view');self.resize(860,700)
        box=QVBoxLayout(self);self.heading=QLabel();self.heading.setTextFormat(Qt.PlainText);self.heading.setWordWrap(True);box.addWidget(self.heading)
        self.note=QLabel('Review the exact reading content, then choose a live paired device. Overview and this selected view are published together.');self.note.setWordWrap(True);box.addWidget(self.note)
        row=QHBoxLayout();self.view=QComboBox();self.view.setAccessibleName('Shared content view');self.devices=QComboBox();self.devices.setAccessibleName('Recipient of reviewed view');row.addWidget(self.view);row.addWidget(self.devices,1);box.addLayout(row)
        self.tabs=QTabWidget();self.text=QPlainTextEdit();self.text.setReadOnly(True);self.text.setAccessibleName('Exact read-only publication preview');self.tabs.addTab(self.text,'Reading content')
        self.image=QLabel();self.image.setAlignment(Qt.AlignCenter);self.image.setAccessibleName('Exact original-bound publication page image');self.image_area=QScrollArea();self.image_area.setWidget(self.image);self.image_area.setWidgetResizable(False)
        self.tabs.addTab(self.image_area,'Original page image');self.tabs.setTabVisible(1,False);box.addWidget(self.tabs,1)
        self.consent=QCheckBox('I reviewed this content for the selected paired device');box.addWidget(self.consent)
        actions=QHBoxLayout();self.prepare=QPushButton('Prepare preview');self.publish=QPushButton('Publish reviewed view');self.revoke=QPushButton('Revoke all views for device')
        for button in (self.prepare,self.publish,self.revoke):actions.addWidget(button)
        box.addLayout(actions);self.status=QLabel();self.status.setWordWrap(True);self.status.setTextFormat(Qt.PlainText);box.addWidget(self.status)
        close=QDialogButtonBox(QDialogButtonBox.Close);close.rejected.connect(self.reject);box.addWidget(close)
        self.prepare.clicked.connect(self.prepare_view);self.publish.clicked.connect(self.publish_view);self.revoke.clicked.connect(self.revoke_view)
        self.view.currentIndexChanged.connect(self.clear_preview);self.devices.currentIndexChanged.connect(self.changed_device);self.consent.toggled.connect(self.buttons)
        snapshot=self.call('ledger.windows.snapshot',{'window_id':self.ident})
        self.revision=snapshot.get('source_revision') if snapshot else None
        if snapshot and snapshot.get('state')=='AVAILABLE':
            self.heading.setText(snapshot['title']+'\nOriginal revision '+self.revision)
            kinds=['pdf'] if snapshot['object']['kind']=='pdf' else ['object','sources','evidence']+(['review'] if snapshot['object']['kind']=='job' else [])
            for kind in kinds:self.view.addItem(LABELS[kind],kind)
        else:self.heading.setText('This view needs an owner refresh.');self.prepare.setEnabled(False)
        sessions=self.call('remote.sessions',{}) or []
        self.devices.addItem('Choose a paired device',None)
        for session in sessions:self.devices.addItem((session.get('device_name') or 'Paired device')+' · '+session['identity'],session['identity'])
        self.buttons()
    def call(self,op,args):
        reply=self.kernel.dispatch(op,args,self.principal)
        if not reply['ok']:self.status.setText(reply['error']['message']);return None
        return reply['result']
    def query(self):return {'window_id':self.ident,'view':self.view.currentData(),'expected_revision':self.revision}
    def clear_preview(self,*args):
        self.preview=None;self.text.clear();self.image.clear();self.tabs.setCurrentIndex(0);self.tabs.setTabVisible(1,False);self.consent.setChecked(False);self.buttons()
    def changed_device(self,*args):self.consent.setChecked(False);self.buttons()
    def buttons(self,*args):
        self.publish.setEnabled(bool(self.preview and self.devices.currentData() and self.consent.isChecked()))
        self.revoke.setEnabled(bool(self.devices.currentData()))
    def prepare_view(self):
        self.clear_preview();value=self.call('ledger.deck.preview',self.query())
        if value:
            content=value['content']
            if content['image']:
                result=self.call('ledger.deck.image',{**self.query(),'content_sha256':value['content_sha256']})
                try:
                    raw=base64.b64decode(result['image_b64'],validate=True)
                    if len(raw)>6*1024*1024 or hashlib.sha256(raw).hexdigest()!=content['image']['sha256']:raise ValueError('Page image changed')
                    page=QImage.fromData(raw,'PNG')
                    if page.isNull() or (page.width(),page.height())!=(content['image']['width'],content['image']['height']):raise ValueError('Page image unavailable')
                except (ValueError,TypeError,KeyError):
                    self.status.setText('Exact page image unavailable. Refresh and prepare this view again.');return
                self.image.setPixmap(QPixmap.fromImage(page));self.image.resize(page.size());self.tabs.setTabVisible(1,True)
            self.preview=value
            text=content['title']+'\n'+LABELS[content['view']]+' · read-only\n\n'+content['notice']
            for block in sorted(content['blocks'],key=lambda b:b['collapsed']):text+='\n\n'+block['title']+('\n[Excerpt: content was bounded]' if block['truncated'] else '')+'\n'+block['text']
            text+='\n\nExact publication identity\nObject '+content['object_id']+'\nRevision '+content['source_revision']+'\nContent '+value['content_sha256']
            if content['image']:text+='\n\nOriginal-bound PNG image\n'+json.dumps(content['image'],indent=2)
            self.text.setPlainText(text)
            if content['image']:self.tabs.setCurrentIndex(1)
            self.status.setText('Preview only. Nothing has been published; no engineering action runs.');self.buttons()
    def publish_view(self):
        if not self.preview or not self.consent.isChecked():return
        value=self.call('ledger.deck.publish',{**self.query(),'device':self.devices.currentData(),'content_sha256':self.preview['content_sha256']})
        if value:self.status.setText('Reviewed '+LABELS[value['view']]+' view published to '+self.devices.currentText()+'. Read-only; execution permission is unchanged.')
    def revoke_view(self):
        if not self.devices.currentData():return
        if self.call('ledger.windows.revoke',{'window_id':self.ident,'device':self.devices.currentData()}):self.status.setText('All views for this window and device revoked.');self.changed_device()

def show_content(host,window_id,principal=None):
    dialog=DeckDialog(host,window_id,principal);host._deck_dialog=dialog;dialog.show();return dialog

def share_pdf(tab):
    if not tab.page_result:return
    enabled=tab.kernel.dispatch('ledger.windows.status',{},tab.principal)
    if not enabled['ok'] or not enabled['result']['enabled']:
        from PySide6.QtWidgets import QMessageBox
        if QMessageBox.question(tab,'Enable shared views','Enable saved logical views for this owner? Sharing still requires reviewing content and choosing a paired device.',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:return
        result=tab.kernel.dispatch('ledger.windows.configure',{'enabled':True},tab.principal)
        if not result['ok']:tab.status.setText(result['error']['message']);return
    result=tab.kernel.dispatch('ledger.windows.pdf',{'job':tab.page_result['job_id']},tab.principal)
    if not result['ok']:tab.status.setText(result['error']['message']);return
    return show_content(tab.host,result['result']['window_id'],tab.principal)
