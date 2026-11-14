"""Bounded actual Qt action/menu checks. Disposable records; no job execution."""
import json,os,sys,tempfile,hashlib
from pathlib import Path
from unittest.mock import patch
PROGRAM=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('ARC_LEDGER_ACTIONS_CAPTURE_DIR',str(PROGRAM/'build/ui_checks/cabinet_actions')));OUT.mkdir(parents=True,exist_ok=True)
RUN=Path(tempfile.mkdtemp(prefix='ledger-actions01-ui-'))
os.environ.update(QT_QPA_PLATFORM='offscreen',ARC_LEDGER_EMBEDDED='1',ARC_LEDGER_DISABLE_BOOK_WATCHER='1',
 ARC1_WORKBENCH_CONFIG_HOME=str(RUN/'profile'),ARC_LEDGER_CONCERN=str(RUN/'Concern'))
sys.path.insert(0,str(PROGRAM));sys.dont_write_bytecode=True
from PySide6.QtCore import Qt,QTimer
from PySide6.QtGui import QContextMenuEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QMenu
from workbench.qt_app import make_app,WorkbenchWindow
from workbench import locations,clip,cabinet_actions
from workbench.cabinet_actions_qt import perform,menu,model
from workbench.engineering_kernel import operator,Kernel
from workbench.session import Session
provider=patch.object(clip,'_request',side_effect=AssertionError('No provider request')).start()
launcher=patch.object(Kernel,'launch',side_effect=AssertionError('No worker launch')).start()
submission=patch.object(Kernel,'submit',side_effect=AssertionError('No job submission')).start()
app=make_app([]);root=locations.office(RUN/'workspace');session=Session(RUN/'profile/session.json',root)
w=WorkbenchWindow(root,session,restore=False);k=w.ledger_bridge.kernel;checks=[];captures=[]
def settle():
 for name in ('agenda_runner','study_idle'):
  obj=getattr(w,name,None)
  if obj and hasattr(obj,'timer'):obj.timer.stop()
 for _ in range(2):app.processEvents();QTest.qWait(35)
def call(op,args=None):
 r=k.dispatch(op,args or {},operator());assert r['ok'],r;return r['result']
def check(text):checks.append(text);print(text,flush=True)
def capture(name):
 w.operations_panel.refresh();settle();p=OUT/name;assert w.grab().save(str(p),'PNG')
 captures.append(dict(file=name,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),resolution=[w.width(),w.height()]))
w.resize(1920,1200);w.show();settle()
project=call('projects.create',{'title':'A supply worth understanding','intent':'Connect assumptions, quantities and evidence without losing the original idea.'})
idea=call('ideas.capture',{'text':'Can this power budget hold during the busiest frame?','project':project['id']})
second=call('ideas.capture',{'text':'A second question, with its own identity.'})
pid='project:'+project['id'];iid='idea:'+idea['id'];sid='idea:'+second['id']
w.cabinet_page.refresh(force=True);w.cabinet_page.select(pid,reveal=True);room=w.cabinet_page.open(pid);settle()
assert room.action_shelf.snapshot==model(w,pid)
assert room.action_shelf.buttons['write'].isEnabled()
check('The cabinet shelf uses the exact shared ledger.cabinet.actions snapshot')
room.writing.setPlainText('Unfinished writing survives a menu visit.');draft=room.writing.toPlainText()
QTest.mouseClick(room.action_shelf.buttons['write'],Qt.LeftButton);settle()
assert room.writing.toPlainText()==draft and room.writing.hasFocus()
assert len(call('ideas.list')['records'])==2
check('Prepare writing focuses the retained draft without saving another idea')
capture('Ledger_Slate_HATCH_Actions_01_Writing.png')
room.open(iid);w.cabinet_page.select(iid,reveal=True);settle()
assert [r['id'] for r in room.action_shelf.snapshot['actions']][1:5]==['workspace:documents','workspace:inquiries','workspace:calculate','workspace:laboratory']  # WORKSHOP-01: the page comes first for an idea
assert room.writing.isHidden();check('An idea offers related workspaces without presenting a project writing form')
capture('Ledger_Slate_HATCH_Actions_01_Selection.png')
# A real context-menu event follows the connected tree signal. Close it using
# the Qt timer rather than blocking the offscreen runner.
seen=[]
def inspect_popup():
 popup=QApplication.activePopupWidget()
 if isinstance(popup,QMenu):
  seen.append(popup.action_model)
  # The menu is a separate offscreen window: retain its actual QWidget grab.
  p=OUT/'Ledger_Slate_HATCH_Actions_01_Menu.png';assert popup.grab().save(str(p),'PNG')
  captures.append(dict(file=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),resolution=[popup.width(),popup.height()]))
  popup.close()
item=w.cabinet_page.items[iid];point=w.cabinet_page.tree.visualItemRect(item).center()
QTimer.singleShot(120,inspect_popup)
event=QContextMenuEvent(QContextMenuEvent.Mouse,point,w.cabinet_page.tree.viewport().mapToGlobal(point))
QApplication.sendEvent(w.cabinet_page.tree.viewport(),event);settle()
assert seen and seen[0]==model(w,iid);check('Tree right-click opens the same ordered model and preserves the selected identity')
frozen=model(w,iid);w.cabinet_page.select(sid,reveal=True)
perform(w,iid,'record',frozen['signature']);settle()
assert room.current==iid and idea['text'] in room.result.toPlainText() and second['text'] not in room.result.toPlainText()
check('An old menu reads its captured identity even after the tree selects another idea')
old=model(w,pid);call('projects.link',{'id':project['id'],'expected_revision':1,'role':'QUESTION','text':'A later saved question'})
try:perform(w,pid,'write',old['signature']);raise AssertionError('Stale action was accepted')
except ValueError as exc:assert 'changed' in str(exc)
assert room.current==iid;check('A changed record signature stops the old action before navigation or writing')
room.open(pid);assert room.writing.toPlainText()==draft;check('Record changes and rejected stale actions preserve unsaved writing')
# Observe a missing-view condition without touching any delivered source file.
original=cabinet_actions.capability_catalog.source
def missing(root,name):
 return {'state':'MISSING_OR_UNSAFE'} if name=='workbench/discovery_qt.py' else original(root,name)
with patch.object(cabinet_actions.capability_catalog,'source',side_effect=missing):
 room.open(iid);settle();spec=next(r for r in room.action_shelf.snapshot['actions'] if r['id']=='workspace:inquiries')
 assert not spec['enabled'] and not room.action_shelf.buttons['workspace:inquiries'].isEnabled()
 assert 'missing or unsafe' in room.action_shelf.buttons['workspace:inquiries'].toolTip()
 capture('Ledger_Slate_HATCH_Actions_01_Unavailable.png')
 check('Unavailable workspace actions retain a visible reason and a disabled control')
room.open(iid)
# Workspace navigation retains the existing document editor and its bytes.
source=root/'Files/retained.txt';source.parent.mkdir(exist_ok=True);source.write_text('Original bytes.\n');editor=w.open_document(source);settle()
assert editor is not None;editor.insertPlainText('Unsaved thought. ');buffer=editor.toPlainText();editor.document().setModified(True)
perform(w,iid,'workspace:inquiries',model(w,iid)['signature']);settle()
assert editor.toPlainText()==buffer and source.read_text()=='Original bytes.\n'
assert call('ideas.get',{'id':idea['id']})['project']==project['id']
check('Opening a related workspace preserves edited source, original bytes and project membership')
room=w.cabinet_page.open(iid);w.resize(1366,768);w.shell2.show_operations_face();settle()
assert w.shell2.top.programs.isVisible() and w.operations_monitors.isVisible() and w.trash_can.isVisible()
assert room.action_shelf.isVisible();capture('Ledger_Slate_HATCH_Actions_01_Compact.png')
check('Laptop layout retains the action shelf, fixed Trash, monitors and visible Stop')
assert room.writing.placeholderText()=='prompt' and w.cabinet_page.query.placeholderText()=='prompt'
assert call('ideas.get',{'id':idea['id']})['text']==idea['text'];assert k.listing('jobs')==[];provider.assert_not_called()
check('Poem, saved text and empty job records survive the pass with no provider request')
result=dict(state='PASSED',mode='ACTUAL_QT_OFFSCREEN',checks=checks,captures=captures,jobs_submitted=0,
 model_calls=0,provider_requests=0,native_invocations=0,native_acceptance=False,
 missing_workspace_case='CONTROLLED_SOURCE_OBSERVATION',owner_ui_review='READY_FOR_COHESIVE_REVIEW')
# Close without asking to save the intentionally edited fixture document.
editor.document().setModified(False);w.close();settle();provider.stop()
assert not w.desktop_lease.exists();result['clean_close']=True
(OUT/'cabinet-actions-ui.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)
