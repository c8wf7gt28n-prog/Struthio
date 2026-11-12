"""Actual Qt checks for the DESKTOP-01 machine and work navigator (WI-4): the mechanical steps of AC10, offscreen.

HATCH DESK D1b: the left pane shows only its tabs (Machine · Cabinet · Settings), the active tree and Trash. The strip's line is
the Machine row's tooltip, each row's details its tooltip, Import and Export Work menu entries, the settings filter's job Find's;
the steps below check those homes where they checked the old controls.

Disposable profile, Concern and records; Kernel.launch, Kernel.submit and the provider request are held; after the window
exists no process may start. The observations are of this container, not the owner's ThinkPad: nothing here is owner-host
acceptance, and the hardware words in the captures describe the machine the check ran on.
"""
import hashlib,json,os,re,subprocess,sys,tempfile,time
from pathlib import Path
from unittest.mock import patch
PROGRAM=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('ARC_LEDGER_MACHINE_CAPTURE_DIR',str(PROGRAM/'build/ui_checks/machine')));OUT.mkdir(parents=True,exist_ok=True)
RUN=Path(tempfile.mkdtemp(prefix='ledger-desktop01-machine-ui-'))
os.environ.update(QT_QPA_PLATFORM='offscreen',ARC_LEDGER_EMBEDDED='1',ARC_LEDGER_DISABLE_BOOK_WATCHER='1',
 ARC1_WORKBENCH_CONFIG_HOME=str(RUN/'profile'),ARC_LEDGER_CONCERN=str(RUN/'Concern'))
os.environ.pop('ARC_LEDGER_XSESSION',None)
sys.path.insert(0,str(PROGRAM));sys.dont_write_bytecode=True
from PySide6.QtCore import Qt,QProcess
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QMessageBox,QPushButton,QAbstractScrollArea
from PySide6.QtTest import QTest
from workbench.qt_app import make_app,WorkbenchWindow
from workbench import locations,clip,machine_overview
from workbench.engineering_kernel import Kernel,operator,CAPABILITIES
from workbench.session import Session
from workbench.settings_qt import VIEWS,PERSIST_MACHINE_MODE
provider=patch.object(clip,'_request',side_effect=AssertionError('No provider request')).start()
launcher=patch.object(Kernel,'launch',side_effect=AssertionError('No worker launch')).start()
submission=patch.object(Kernel,'submit',side_effect=AssertionError('No job submission')).start()
question=patch.object(QMessageBox,'question',return_value=QMessageBox.Yes).start()
app=make_app([]);root=locations.office(RUN/'workspace');session=Session(RUN/'profile/session.json',root)
w=WorkbenchWindow(root,session,restore=False);k=w.ledger_bridge.kernel;bridge=w.ledger_bridge;nav=w.settings_navigator;page=w.machine_page;strip=nav.strip
# Host readings ask the platform for its processor, which Python answers once through `uname -p` and then remembers.
import platform;platform.processor()
popen=patch.object(subprocess,'Popen',side_effect=AssertionError('No process start')).start()
system=patch.object(os,'system',side_effect=AssertionError('No shell command')).start()
detached=patch.object(QProcess,'startDetached',side_effect=AssertionError('No detached program')).start()
checks=[];captures=[];strip_samples=[]
STRIP=re.compile(r'^(?P<cpu>.+?) · (?P<ram>RAM [\d.]+ [KMGT]iB/[\d.]+ [KMGT]iB|RAM unavailable) · (?P<disk>[\d.]+ [KMGT]iB free|Storage unavailable) · net (?P<net>up|down|unavailable)$')
def settle(ms=25):
 for name in ('agenda_runner','study_idle'):
  obj=getattr(w,name,None)
  if obj and hasattr(obj,'timer'):obj.timer.stop()
 for _ in range(2):app.processEvents();QTest.qWait(ms)
def check(text):checks.append(text);print(text,flush=True)
def call(op,args=None):
 value=k.dispatch(op,args or {},operator());assert value['ok'],value;return value['result']
def capture(name,note):
 w.operations_panel.refresh();settle();pix=w.grab();target=OUT/name;assert pix.save(str(target),'PNG')
 captures.append(dict(file=name,note=note,mode='ACTUAL_QT_WINDOW_GRAB',sha256=hashlib.sha256(target.read_bytes()).hexdigest(),resolution=[w.width(),w.height()]))
def node(item):return item.data(0,Qt.UserRole)
def children(item):return [item.child(i) for i in range(item.childCount())]
def top():return [page.tree.topLevelItem(i) for i in range(page.tree.topLevelItemCount())]
def dominant(widget,colour):
 image=widget.grab().toImage();total=image.width()*image.height();hits=0;wanted=QColor(colour).rgb()
 for y in range(image.height()):
  for x in range(image.width()):
   if image.pixel(x,y)==wanted:hits+=1
 return hits/total if total else 0
w.resize(1920,1200);w.show();settle();bridge.timer.stop();w.type_bar.hatch.lifecycle.timer.stop()
project=call('projects.create',{'title':'Machine workshop','intent':'Keep the machine visible beside the work.'})
idea=call('ideas.capture',{'project':project['id'],'text':'Which disk holds the workspace?'})
w.cabinet_page.refresh(force=True);settle()
source=root/'Files/machine_draft.py';source.parent.mkdir(exist_ok=True);source.write_text('original = True\n')
editor=w.open_document(source);editor.appendPlainText('# unsaved thought kept through every machine step');settle()
assert w.tabs.preview() is editor and editor.document().isModified()
with k.db() as db:jobs_before=db.execute('SELECT count(*) FROM jobs').fetchone()[0]
# 01 · the strip and the tabs, before anything is chosen. HATCH DESK D1b: the left pane shows only its tabs (Machine · Cabinet ·
# Settings), the active tree and Trash; the strip's line moved into the Machine tab (the Machine row's tooltip), still sampled
# every 2 s, and its facts are the Processor, Memory, Storage and Connections rows.
assert nav.current_view()=='cabinet' and not strip.isVisible() and strip.timer.isActive() and strip.timer.interval()==2000
assert [b.text() for b in nav.bar.buttons]==['Machine','Cabinet','Settings'] and nav.cabinet.isChecked() and not nav.machine.isChecked()
assert nav.cabinet.accessibleDescription()=='Current view' and 'processor' in nav.machine.accessibleDescription()
match=STRIP.match(strip.label.full);assert match,strip.label.full;strip_samples.append(dict(view='cabinet',text=strip.label.full,sampled_at=strip.sample['sampled_at']))
dock_before=w.nav_dock.width();strip.refresh();settle();assert w.nav_dock.width()==dock_before and strip.label.minimumSizeHint().width()==0
assert strip.sample['memory'] is not None and strip.sample['space'] is not None,strip.sample
check('The machine strip\'s line (%s) is sampled every 2 s and widens nothing; the left pane\'s tabs read Machine · Cabinet · Settings, Cabinet chosen'%strip.label.full)
# 02 · AC10: inspect detected machine, storage and device state
nav.machine.click();settle(60);assert nav.current_view()=='machine' and nav.stack.currentWidget() is page and page.isVisible() and nav.machine.isChecked()
assert [t.text(0) for t in top()]==['Machine','Work','Settings'],[t.text(0) for t in top()]
strip.refresh();assert strip.label.full in page.items['machine'].toolTip(0),'the strip\'s line is the Machine row\'s tooltip (D1b)'
machine=page.items['machine'];sections=children(machine)
assert [s.text(0).split(' · ')[0] for s in sections]==['Processor','Memory','Storage','Connections','Devices','Installed tools']
for section in sections:
 data=node(section)['section']
 if section.childCount()==0:assert data['state'] in ('NONE','UNAVAILABLE') and (' · none detected' in section.text(0) or ' · unavailable' in section.text(0)),section.text(0)
 else:assert data['state'] in ('OBSERVED','PARTIAL'),(section.text(0),data['state'])
 for leaf in children(section):
  row=node(leaf)['item'];assert row['source'] and row['sampled_at'] and row['state'] in ('OBSERVED','PARTIAL','UNAVAILABLE') and leaf.toolTip(0)
 if data['order']=='natural':
  labels=[c.text(0) for c in children(section)];assert labels==sorted(labels,key=machine_overview.natural),labels
storage=page.items['storage'];storage.setExpanded(True);page.tree.setCurrentItem(storage);settle()
text=page.details.toPlainText();assert text.startswith('Storage · ') and 'Sources: ' in text and '/proc/mounts' in text and re.search(r'Observed \d\d:\d\d:\d\d',text),text
assert storage.toolTip(0)==text and not page.details.isVisible(),'D1b: the details are each row\'s tooltip; the details pane is out of the left pane'
workspace_row=page.items['storage:path:workspace'];page.tree.setCurrentItem(workspace_row);settle();text=page.details.toPlainText()
assert str(root) in text and 'os.statvfs' in text and re.search(r'Observed \d\d:\d\d:\d\d · source',text),text
mounts=[c for c in children(storage) if node(c)['item']['kind']=='mount'];assert mounts and any('holds the' in c.text(0) for c in mounts),[c.text(0) for c in mounts]
devices=page.items['devices'];page.tree.setCurrentItem(devices);settle();text=page.details.toPlainText()
assert text.startswith('Devices · ') and ('/sys/bus/usb/devices' in text) and any(word in text for word in ('observations','nothing detected','unavailable')),text
connections=page.items['connections'];assert connections.childCount()>0 and all('addresses: NOT_READ' in page.describe(node(c)) for c in children(connections))
tools=page.items['tools'];assert tools.childCount()==len(machine_overview.TOOL_NAMES) and all(' · ' in c.text(0) for c in children(tools))
assert 'nothing was run' in page.caption.text() and 'not owner host qualification' in page.caption.text()
popen.assert_not_called();system.assert_not_called();detached.assert_not_called()
page.tree.setCurrentItem(workspace_row);settle()
capture('Ledger_Slate_HATCH_Desktop_01_Machine_01_Machine_View.png','The Machine tab in the left pane: Machine with its six sections (Storage open, the workspace path selected; each row\'s tooltip names the source and the sampled time), Work with the project, Settings, with connecting branch lines; Trash at the lower right. Observations are of the check container, not the ThinkPad.')
check('Machine → Processor, Memory, Storage, Connections, Devices, Installed tools read from /proc, /sys and statvfs; every row names source and time; empty sections are leaves with an honest state; like siblings are in natural order; no process started')
# 03 · AC10 / NV02: a Work link selects the same cabinet identity
work=page.items['work'];ident='project:'+project['id'];link=page.items[ident]
assert [c.text(0) for c in children(work)]==['Machine workshop'] and node(link)['id']==ident==node(link)['node']['canonical_id']
assert ident in w.cabinet_page.items and node(w.cabinet_page.items[ident])['canonical_id']==ident  # one identity, no copy
page.tree.setCurrentItem(link);settle();assert 'the same record the cabinet shows' in page.details.toPlainText()
page.activate(link);settle()
current=w.cabinet_page.tree.currentItem();room=w.tabs.currentWidget()
assert nav.current_view()=='cabinet' and nav.cabinet.isChecked() and node(current)['id']==ident and type(room).__name__=='CabinetRecordTab' and room.current==ident
assert w.tabs.preview() is editor and editor.document().isModified() and w.tabs.pinned()==[]
with k.db() as db:assert db.execute('SELECT count(*) FROM jobs').fetchone()[0]==jobs_before
capture('Ledger_Slate_HATCH_Desktop_01_Machine_02_Work_Link_Selects_Cabinet_Record.png','Choosing the project under Work: the column returns to the cabinet with the same project:<id> selected and its record room open in the centre; the edited Preview and its unsaved line are untouched; no job was submitted.')
check('A Work link carries the cabinet\'s own project identity: choosing it selects that record in the cabinet and opens its room, keeps the edited Preview and submits nothing')
# 04 · NV03: Import, Export and the pinned Trash in every view. HATCH DESK D1b: Import and Export left the pane for the Work menu
# (the same transfers); Trash is larger and pinned at the pane's lower right.
transfers=[b for b in w.cabinet_page.findChildren(QPushButton) if b.accessibleName().endswith('transfer controls')]
assert sorted(b.text() for b in transfers)==['Export','Import'] and not any(b.isVisible() for b in transfers)
assert w.a_import in w.menu_groups['File'].actions() and w.a_export in w.menu_groups['File'].actions()
trash=w.trash_can;parent=trash.parentWidget()
while parent is not None:
 assert not isinstance(parent,QAbstractScrollArea),'Trash must stay outside the scrolling tree';parent=parent.parentWidget()
def trash_pinned(view):
 dock=w.nav_dock.geometry();pos=trash.mapTo(w,trash.rect().topLeft());stack_bottom=nav.stack.mapTo(w,nav.stack.rect().bottomLeft()).y()
 assert trash.isVisible() and not strip.isVisible(),view
 assert pos.x()>dock.center().x() and pos.x()+trash.width()<=dock.right()+1 and pos.y()>=stack_bottom-1 and pos.y()+trash.height()<=dock.bottom()+1,(view,pos,dock,stack_bottom)
 strip_samples.append(dict(view=view,text=strip.label.full,sampled_at=strip.sample['sampled_at']))
for view in VIEWS:
 nav.show_view(view);settle();assert nav.current_view()==view;trash_pinned(view);assert STRIP.match(strip.label.full),strip.label.full
check('Import and Export are Work menu entries (the same transfers); Trash stays pinned bottom-right of the left column outside any scroll area in the cabinet, settings and machine tabs, and the strip\'s line keeps its form')
# 05 · the settings hierarchy from the switch and from the tree; V-24 filter passage
nav.show_view('cabinet');settle();nav.settings.click();settle()
assert nav.current_view()=='settings' and nav.settings.isChecked() and nav.tree.isVisible() and nav.tree.topLevelItemCount()>0 and type(w.tabs.currentWidget()).__name__=='SettingsTab'
assert nav.filter.objectName()=='SettingsFilter' and nav.filter.placeholderText()=='poem' and not nav.filter.isVisible()
w.console.output.clear();w.console.run_find('Interface text');found=w.console.output.toPlainText();assert 'SETTINGS · ' in found and 'reading.ui_pt' in found,found[:300]  # D1b: the filter's job is Find's
capture('Ledger_Slate_HATCH_Desktop_01_Machine_03_Settings_With_Strip.png','Settings chosen from its tab: the settings hierarchy fills the left pane with its branch lines; finding a setting by its words is the writing line\'s Find (HATCH DESK D1b).')
nav.machine.click();settle(60);settings_leaf=page.items['settings'];page.tree.setCurrentItem(settings_leaf);settle()
assert 'definitions in the shared registry' in page.details.toPlainText();page.activate(settings_leaf);settle()
assert nav.current_view()=='settings' and type(w.tabs.currentWidget()).__name__=='SettingsTab'
assert w.session.state['settings_navigation']['mode']=='settings'
nav.machine.click();settle();expected='machine' if PERSIST_MACHINE_MODE else 'cabinet'
assert w.session.state['settings_navigation']['mode']==expected and Session(w.session.path,root).state['settings_navigation']['mode']==expected  # written, and read back through Session.load
check('The settings hierarchy is reachable from its tab and from the Settings row of the machine tree; a setting is found by its words from Find; the chosen view (%s) is saved and reloads through Session.load'%expected)
# 06 · ledger.machine as Slate would read it
result=call('ledger.machine');assert [s['id'] for s in result['sections']]==list(machine_overview.SECTIONS) and result['basis']=='CURRENT_LEDGER_HOST_NOT_OWNER_HOST_QUALIFICATION'
one=call('ledger.machine',{'section':'devices'});assert [s['id'] for s in one['sections']]==['devices'] and len(json.dumps(result))<512*1024
assert CAPABILITIES['ledger.machine']=='read'  # which operations exist is the recorded registry's business (tools/check_release.py)
with k.db() as db:assert db.execute('SELECT count(*) FROM jobs').fetchone()[0]==jobs_before
popen.assert_not_called();system.assert_not_called();detached.assert_not_called()
check('ledger.machine answers the whole view or one section as a bounded read with the host basis; nothing was started')
# 07 · compact
nav.machine.click();settle(60);w.resize(1366,768);settle()
assert page.isVisible() and not strip.isVisible() and trash.isVisible() and page.tree.isVisible() and page.tree.height()>200
assert STRIP.match(strip.label.full) and w.tabs.width()>=600,(strip.label.full,w.tabs.width())
page.tree.setCurrentItem(page.items['storage']);settle()
capture('Ledger_Slate_HATCH_Desktop_01_Machine_04_Compact_1366.png','The Machine tab at 1366 by 768: the tree fills the pane, Trash stays at the foot and the centre keeps at least 600 px.')
check('At 1366 by 768 the strip\'s line keeps its form, the machine tree fills the pane and the fixed Trash remains visible')
# close
editor.document().setModified(False);w.resize(1920,1200);settle()
assert w.close() is True;settle();assert not w.desktop_lease.exists()
launcher.assert_not_called();provider.assert_not_called();submission.assert_not_called();popen.assert_not_called();system.assert_not_called();detached.assert_not_called()
assert not strip.timer.isActive() or w._closing
check('Clean close with zero job, worker, model, provider, native or process activity')
result=dict(state='PASSED',mode='ACTUAL_QT_OFFSCREEN',acceptance='Mechanical offscreen steps only; owner-host observations are not claimed',
 checks=checks,captures=captures,strip_samples=strip_samples,views=list(VIEWS),machine_mode_persisted=PERSIST_MACHINE_MODE,
 disposable_records=dict(projects=1,ideas=1,files=1),jobs_submitted=0,worker_processes_started=0,model_generations=0,provider_requests=0,
 native_invocations=0,subprocesses=0,os_power_or_logout_commands=0,owner_host_acceptance=False,clean_close=True)
(OUT/'machine-ui.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)
for guard in (question,detached,system,popen,submission,launcher,provider):guard.stop()
