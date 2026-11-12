"""Owner controls for paired exchange, offline releases and deployment preparation."""
from .text_prompts import writing_prompt
import json
from pathlib import Path
import shlex
import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox,QComboBox,QFileDialog,QFormLayout,QHBoxLayout,QLabel,
 QLineEdit,QPlainTextEdit,QScrollArea,QTabWidget,QVBoxLayout,QWidget)
from .shell2 import button,role,call_write


class DeploymentTab(QWidget):
 def __init__(self,host):
  super().__init__();self.host=host;self.busy=False;self.preview=None;self.inspected=None;self.update=None
  self.setObjectName('LibraryTab');self.setProperty('ledgerRoom',True)
  box=QVBoxLayout(self);box.setContentsMargins(20,18,20,16)
  box.addWidget(role(QLabel('Exchange & deployment'),'title'))
  self.message=QLabel('Choose a paired identity, review the exact files, and keep each acceptance separate.');self.message.setWordWrap(True);self.message.setTextFormat(Qt.PlainText);box.addWidget(self.message)
  self.pages=QTabWidget();box.addWidget(self.pages,1)
  self.build_exchange();self.build_updates();self.build_deployment()
  self.record=QPlainTextEdit();self.record.setReadOnly(True);self.record.setMaximumHeight(190);self.record.setAccessibleName('Exact receipt and review record');box.addWidget(self.record)
  self.reload()

 def title(self):return 'Exchange & deployment'
 def info(self):return 'Paired pills, signed offline updates and launch configuration'

 def page(self,title):
  scroll=QScrollArea();scroll.setWidgetResizable(True);body=QWidget();layout=QVBoxLayout(body);scroll.setWidget(body);self.pages.addTab(scroll,title);return layout

 def field(self,form,label,placeholder=''):
  item=QLineEdit();writing_prompt(item, placeholder);item.setAccessibleName(label);form.addRow(label,item);return item

 def actions(self,box,items):
  row=QHBoxLayout()
  for label,fn in items:
   item=button(label,'quiet');item.clicked.connect(fn);row.addWidget(item)
  box.addLayout(row)

 def note(self,box,text):
  item=QLabel(text);item.setWordWrap(True);item.setTextFormat(Qt.PlainText);box.addWidget(item)

 def show_record(self,value):self.record.setPlainText(json.dumps(value,ensure_ascii=False,indent=2))

 def run(self,op,args,done=None):
  if self.busy or self.host._closing:return
  from .register_tabs import Call
  from .engineering_kernel import operator
  from .engine import engineering
  from shiboken6 import isValid
  self.busy=True;self.pages.setEnabled(False);self.message.setText('Verifying the selected request…')
  if not hasattr(self.host,'service_workers'):self.host.service_workers=[]
  epoch=getattr(self.host,'_operation_epoch',0)
  worker=Call(engineering(self.host.root),op,args,operator(),self.host);self.host.service_workers.append(worker)
  def ready(response):
   if not isValid(self) or self.host._closing:return
   self.busy=False;self.pages.setEnabled(True)
   if epoch!=getattr(self.host,'_operation_epoch',0):self.message.setText('Stopped. Refresh the saved receipts before continuing.');return
   if not response.get('ok'):self.message.setText((response.get('error') or {}).get('message','Inspect the receipt before retrying.'));return
   value=response['result'];self.show_record(value);self.message.setText('Receipt saved. Review the next action.');
   if done:done(value)
  worker.ready.connect(ready);worker.finished.connect(lambda:self.host.service_workers.remove(worker) if worker in self.host.service_workers else None)
  worker.finished.connect(worker.deleteLater);worker.start()

 def build_exchange(self):
  box=self.page('Paired exchange');form=QFormLayout();box.addLayout(form)
  self.peers=QComboBox();form.addRow('Paired computer',self.peers)
  self.copies=QComboBox();form.addRow('Working copy',self.copies)
  self.request_title=self.field(form,'Request title','Clock hand revision')
  self.purpose=self.field(form,'Requested result','Describe the intended result and stop conditions')
  self.actions(box,[('Refresh identities & copies',self.reload),('Show my TLS card',lambda:self.run('exchange.identity',{},self.identity)),('Save my TLS card',self.save_card)])
  pair=QFormLayout();box.addLayout(pair);self.card_path=self.field(pair,'Other computer’s TLS card','Full path to its public JSON card');self.fingerprint=self.field(pair,'Verified full fingerprint','Compare all 64 hex characters through another trusted channel')
  self.actions(box,[('Pair this verified card',self.pair),('Revoke selected computer',lambda:self.run('exchange.revoke',{'peer':self.peers.currentData()},lambda v:self.reload())),('Rotate my certificate',lambda:self.run('exchange.rotate_certificate',{},self.identity))])
  self.actions(box,[('Preview request files',self.preview_request),('Export reviewed request',self.export_request),('Show exchange receipts',lambda:self.run('exchange.list',{}))])
  self.note(box,'Preview lists every pill/1 filename exclusion. Export queues bytes for an explicitly started TLS listener and also creates a USB-transferable .pill. No work is granted by transport.')
  incoming=QFormLayout();box.addLayout(incoming);self.incoming=self.field(incoming,'Received pill','Choose a quarantined .pill file')
  self.delegate=QCheckBox('Make an accepted request copy available to Graphite');box.addWidget(self.delegate)
  self.actions(box,[('Choose & inspect pill',self.inspect_pill),('Accept request as working copy',self.accept),('Stage returned edits for review',self.stage),('Open Changes',lambda:__import__('workbench.change_sets_qt',fromlist=['show']).show(self.host))])
  self.findings=QPlainTextEdit();writing_prompt(self.findings, 'Findings to return with the selected received working copy');self.findings.setMaximumHeight(100);box.addWidget(self.findings)
  self.actions(box,[('Export signed result',lambda:self.run('exchange.return',{'copy':self.copies.currentData(),'findings':self.findings.toPlainText()}))])
  net=QFormLayout();box.addLayout(net);self.address=self.field(net,'TLS address','192.168.1.20:7717');self.send_path=self.field(net,'Egress path in Files','Egress/Pills/<id>.pill')
  self.actions(box,[('Send selected export',lambda:self.run('exchange.send',{'peer':self.peers.currentData(),'address':self.address.text(),'path':self.send_path.text()})),('Fetch to quarantine',lambda:self.run('exchange.fetch',{'peer':self.peers.currentData(),'address':self.address.text()}))])
  self.note(box,'No listener starts here. A workstation listener is an explicit command described in docs/STAGE6.md. Both endpoints require TLS cards. Received results always need separate working-copy review; original publication remains in Changes.')

 def identity(self,value):
  self.my_card=value.get('card',value);self.show_record(self.my_card)
  self.message.setText('Public card. Verify its full certificate fingerprint on the other computer. Never share the identity state directory.')

 def save_card(self):
  def save(value):
   self.identity(value);path,_=QFileDialog.getSaveFileName(self,'Save public TLS card','ledger-tls-card.json','JSON (*.json)')
   if path:Path(path).write_text(json.dumps(self.my_card,indent=2)+'\n');self.message.setText('Public TLS card saved.')
  self.run('exchange.identity',{},save)

 def pair(self):
  try:value=json.loads(Path(self.card_path.text()).read_text())
  except (ValueError,OSError) as exc:self.message.setText(str(exc));return
  self.run('exchange.pair',{'card':value,'expected_fingerprint':self.fingerprint.text().strip()},lambda v:self.reload())

 def reload(self):
  if self.busy:return
  for op,target,rows,label,key in [('exchange.identity',self.peers,'peers','name','key'),('changes.workspaces',self.copies,'workspaces','name','id')]:
   response=call_write(self.host,op,{})
   if response.get('ok'):
    selected=target.currentData();target.clear()
    for value in response['result'][rows]:target.addItem(value[label],value[key])
    if selected is not None:target.setCurrentIndex(max(0,target.findData(selected)))

 def preview_request(self):
  def ready(value):self.preview=value;self.message.setText('Review the files and exclusions below before exporting.');self.show_record(value)
  self.run('exchange.preview',{'copy':self.copies.currentData(),'peer':self.peers.currentData(),'title':self.request_title.text(),'purpose':self.purpose.text()},ready)

 def export_request(self):
  if not self.preview:self.message.setText('Preview the exact request first.');return
  self.run('exchange.request',{'id':self.preview['id'],'expected_digest':self.preview['content_digest']},lambda v:self.send_path.setText(v['path']))

 def inspect_pill(self):
  path,_=QFileDialog.getOpenFileName(self,'Inspect received pill',self.incoming.text(),'Pills (*.pill)')
  if not path:return
  self.incoming.setText(path)
  def ready(value):self.inspected={'path':path,'value':value};self.message.setText('Verified envelope in quarantine. Choose acceptance or returned-edit review separately.')
  self.run('exchange.inspect',{'path':path},ready)

 def receive_args(self):
  if not self.inspected or self.inspected['path']!=self.incoming.text():self.message.setText('Inspect these exact pill bytes first.');return None
  return {'path':self.inspected['path'],'expected_sha256':self.inspected['value']['sha256']}

 def accept(self):
  args=self.receive_args()
  if args:self.run('exchange.accept',{**args,'for_slate':self.delegate.isChecked()},lambda v:self.reload())

 def stage(self):
  args=self.receive_args()
  if args:self.run('exchange.stage_result',args,lambda v:self.message.setText('Returned result staged. Open Changes to inspect and apply the frozen proposal.'))

 def build_updates(self):
  box=self.page('Offline updates');self.note(box,'Establish the real current UTC before reviewing offline metadata. Bootstrap only a publisher root whose full SHA-256 you verified independently. A signature establishes publisher identity; it does not qualify the new program.')
  self.actions(box,[('I checked the current UTC clock',lambda:self.run('releases.clock',{})),('Show update trust & journal',lambda:self.run('releases.status',{}))])
  form=QFormLayout();box.addLayout(form);self.root_path=self.field(form,'Publisher root file');self.root_hash=self.field(form,'Verified root SHA-256');self.bundle_path=self.field(form,'Signed offline bundle')
  self.actions(box,[('Bootstrap verified publisher root',lambda:self.run('releases.trust',{'root':self.root_path.text(),'expected_sha256':self.root_hash.text().strip()})),('Verify & preview update',self.preview_update)])
  self.release_dir=self.field(form,'New or owned release store','A directory outside the program and Office')
  self.actions(box,[('Prepare closed-Graphite install command',self.install_command)])
  self.note(box,'Close Graphite and its coordinator before running the command. Installation verifies a full workspace/profile backup, retains the old program, and switches a recoverable program pointer. It does not start code or migrate data. Pointer reversion does not restore data; use a verified backup into new destinations before an incompatible older program.')

 def preview_update(self):
  def ready(value):self.update=value;self.message.setText('Signed metadata and program bytes verified. Inspect the publisher, compatibility and version before closing Graphite to install.')
  self.run('releases.preview',{'bundle':self.bundle_path.text()},ready)

 def install_command(self):
  if not self.update or not self.release_dir.text():self.message.setText('Review an update and choose its release store first.');return
  from .session import config_dir
  command=[sys.executable,'-m','workbench.release_cli','--root',str(self.host.root),'--profile',str(config_dir()),'install',self.update['id'],'--digest',self.update['content_digest'],'--directory',self.release_dir.text()]
  self.record.setPlainText('Close Graphite and its coordinator, then run from this program directory:\n\n'+shlex.join(command));self.message.setText('Installation command prepared; no program pointer was changed.')

 def build_deployment(self):
  box=self.page('Computer & appliance');self.note(box,'Single-computer use remains the default. Prepare launch files for review here; activate them explicitly on the real host. Appliance display, protected workers and physical two-machine operation require their own walkthrough.')
  form=QFormLayout();box.addLayout(form);self.mode=QComboBox()
  for label,key in [('Single computer','SINGLE'),('Workstation','WORKSTATION'),('Appliance — Wayland / Cage','APPLIANCE')]:self.mode.addItem(label,key)
  form.addRow('Role',self.mode);self.folder=self.field(form,'New configuration folder')
  self.actions(box,[('Prepare launch configuration',lambda:self.run('deployment.prepare',{'mode':self.mode.currentData(),'directory':self.folder.text()})),('Show host & deployment status',lambda:self.run('deployment.status',{}))])
  self.actions(box,[('Share my work summaries with paired view phones',lambda:self.run('deployment.share_progress',{'enabled':True})),('Stop sharing work summaries',lambda:self.run('deployment.share_progress',{'enabled':False}))])
  self.note(box,'Progress sharing adds a read-only phone page with titles, states, reasons and budgets. It carries no task inputs, output contents, approval controls or execution grants. The existing phone connection remains a separate explicit setup.')


def show(host):
 host._close_start()
 for i in range(host.tabs.count()):
  tab=host.tabs.widget(i)
  if isinstance(tab,DeploymentTab):host.tabs.setCurrentWidget(tab);tab.reload();return tab
 tab=DeploymentTab(host);host.tabs.addTab(tab,tab.title());host.tabs.setCurrentWidget(tab);return tab
