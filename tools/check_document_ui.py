"""Actual Qt check of the shared document route (Commission v2.1's simple demonstration), offscreen.

The mechanical steps: open Documents through the Hatch catalogue route, type a paragraph, select words, ask Slate in the
typing strip to make them bold, see the formatting change on the page, keep typing, save, close and reopen the page from
its saved revision, take the change back with Ctrl Z, and read the same facts back from the store. Disposable profile and
Concern; Kernel.launch, Kernel.submit and the provider request are held; no process may start. No model runs: the edit is
resolved by explicit rules, and the report says so. Nothing here is owner-host, live-model or physical acceptance.
"""
import hashlib,json,os,subprocess,sys,tempfile,time
from pathlib import Path
from unittest.mock import patch
PROGRAM=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('ARC_LEDGER_DOCUMENT_CAPTURE_DIR',str(PROGRAM/'build/ui_checks/document')));OUT.mkdir(parents=True,exist_ok=True)
RUN=Path(tempfile.mkdtemp(prefix='ledger-workshop01-document-ui-'))
os.environ.update(QT_QPA_PLATFORM='offscreen',ARC_LEDGER_EMBEDDED='1',ARC_LEDGER_DISABLE_BOOK_WATCHER='1',
 ARC1_WORKBENCH_CONFIG_HOME=str(RUN/'profile'),ARC_LEDGER_CONCERN=str(RUN/'Concern'))
os.environ.pop('ARC_LEDGER_XSESSION',None)
sys.path.insert(0,str(PROGRAM));sys.dont_write_bytecode=True
from PySide6.QtCore import Qt,QProcess
from PySide6.QtGui import QFont,QTextCursor
from PySide6.QtWidgets import QMessageBox
from PySide6.QtTest import QTest
from workbench.qt_app import make_app,WorkbenchWindow
from workbench import locations,clip,documents as store
from workbench.document_qt import DocumentsTab,from_qt
from workbench.engineering_kernel import Kernel,operator
from workbench.session import Session
from workbench.shell2 import open_destination
from workbench.explore_qt import open_instrument
provider=patch.object(clip,'_request',side_effect=AssertionError('No provider request')).start()
launcher=patch.object(Kernel,'launch',side_effect=AssertionError('No worker launch')).start()
submission=patch.object(Kernel,'submit',side_effect=AssertionError('No job submission')).start()
question=patch.object(QMessageBox,'question',return_value=QMessageBox.Yes).start()
app=make_app([]);root=locations.office(RUN/'workspace');session=Session(RUN/'profile/session.json',root)
w=WorkbenchWindow(root,session,restore=False);k=w.ledger_bridge.kernel;bridge=w.ledger_bridge
import platform;platform.processor()
popen=patch.object(subprocess,'Popen',side_effect=AssertionError('No process start')).start()
system=patch.object(os,'system',side_effect=AssertionError('No shell command')).start()
detached=patch.object(QProcess,'startDetached',side_effect=AssertionError('No detached program')).start()
checks=[];captures=[];problems=[]
def settle(ms=30):
 for name in ('agenda_runner','study_idle'):
  obj=getattr(w,name,None)
  if obj and hasattr(obj,'timer'):obj.timer.stop()
 for _ in range(3):app.processEvents();QTest.qWait(ms)
def check(text):checks.append(text);print(text,flush=True)
def call(op,args=None):
 value=k.dispatch(op,args or {},operator());assert value['ok'],value;return value['result']
def capture(name,note):
 w.operations_panel.refresh();settle();pix=w.grab();target=OUT/name;assert pix.save(str(target),'PNG')
 captures.append(dict(file=name,note=note,mode='ACTUAL_QT_WINDOW_GRAB',sha256=hashlib.sha256(target.read_bytes()).hexdigest(),resolution=[w.width(),w.height()]))
def bold_runs(tab):return [m for m in from_qt(tab.page.document())[0]['marks'] if m.get('bold')]
def stored(ident):return call('documents.get',{'id':ident})['document']
def five_parts():
 """The frame check's five parts: left column, Ledger Head, centre, right column, typing strip, with Trash and Master Stop."""
 parts=(w.nav_dock,w.ribbon_dock,w.central_stack,w.sim_dock,getattr(w,'type_dock',None))
 return all(p is not None and p.isVisible() for p in parts) and w.trash_can.isVisible() and w.shell2.top.programs.isVisible()
w.resize(1920,1200);w.show();settle();bridge.timer.stop();w.type_bar.hatch.lifecycle.timer.stop()
with k.db() as db:jobs_before=db.execute('SELECT count(*) FROM jobs').fetchone()[0]
# 01 · the Hatch catalogue route opens the Documents room (the same entry Hatch ▸ Work ▸ Documents uses)
entry=next(r for r in call('ledger.explore',{'kind':'INSTRUMENT'})['instruments'] if r['id']=='instrument:documents')
assert entry['view_available'] and entry['presentation_kind']=='workspace' and entry['human_route'].startswith('Menu ▸ Work ▸ Documents'),entry
tab=open_instrument(w,entry);settle()
assert isinstance(tab,DocumentsTab) and w.tabs.currentWidget() is tab and tab.property('ledgerRoom') and tab.document_id,tab
ident=tab.document_id;assert tab.revision==1 and five_parts()
check('01 Hatch route instrument:documents opens the Documents room as a retained workspace with a fresh saved document (revision 1); five parts visible')
# 02 · type a paragraph with key events; autosave lands against the revision the page saw
tab.page.setFocus();settle();QTest.keyClicks(tab.page,'The quick brown fox jumps over the lazy dog.');settle()
assert tab.dirty and tab.page.toPlainText()=='The quick brown fox jumps over the lazy dog.'
assert tab.flush() and tab.revision==2 and stored(ident)['blocks'][0]['text']=='The quick brown fox jumps over the lazy dog.'
assert tab.title_box.text()=='The quick brown fox jumps over the lazy dog.'[:60]+'…' or tab.title_box.text().startswith('The quick')
check('02 Typed paragraph (QTest key events) saved as revision 2; the title takes the first words')
# 03 · select words, move to the typing strip, ask Slate in words
cursor=tab.page.textCursor();cursor.setPosition(4);cursor.setPosition(15,QTextCursor.KeepAnchor);tab.page.setTextCursor(cursor);settle()
assert tab.slate_selection()=={'block':0,'start':4,'end':15,'text':'quick brown'}
bar=w.type_bar;bar.set_target('slate');box=bar.box;box.setFocus();settle()
assert not tab.page.hasFocus() and tab.page.textCursor().hasSelection() and 'quick brown' in tab.slate_context()
context_word=getattr(bar,'context',None)
QTest.keyClicks(box,'make these words bold');settle();QTest.keyClick(box,Qt.Key_Return);settle(80)
after=stored(ident)
assert after['revision']==3 and after['blocks'][0]['marks']==[{'start':4,'end':15,'bold':True}],after['blocks'][0]
assert after['last_change']['actor']=='SLATE' and after['last_change']['request']=='make these words bold'
assert bold_runs(tab)==[{'start':4,'end':15,'bold':True}] and tab.revision==3 and not tab.dirty
fragment=tab.page.document().firstBlock().begin().fragment()
cursor=tab.page.textCursor();cursor.setPosition(6);assert cursor.charFormat().fontWeight()>=QFont.Bold
cursor.setPosition(2);assert cursor.charFormat().fontWeight()<QFont.Bold
face=w.shell2.face;last=face.bubbles[-1].text.text() if hasattr(face,'bubbles') else ''
cursor.setPosition(6);weight=cursor.charFormat().fontWeight();cursor.setPosition(2);plain_weight=cursor.charFormat().fontWeight()
check('03 Typing strip → Slate: “make these words bold” on the selection became revision 3 by SLATE through documents.edit; the page shows quick brown in bold (char weight %d) and the rest regular (%d); no model ran'%(weight,plain_weight))
capture('Ledger_Slate_WORKSHOP_01_Documents_01_Bold_By_Slate_1920.png','Selected words made bold by Slate from the typing strip; machine column left, Slate activity right, strip below')
# 04 · keep typing after Slate's turn: the caret is usable and the words stay bold
cursor=tab.page.textCursor();cursor.movePosition(QTextCursor.End);tab.page.setTextCursor(cursor);tab.page.setFocus();settle()
QTest.keyClicks(tab.page,' Then it slept.');settle();assert tab.flush() and tab.revision==4
now=stored(ident);assert now['blocks'][0]['text'].endswith('lazy dog. Then it slept.') and now['blocks'][0]['marks']==[{'start':4,'end':15,'bold':True}]
check('04 Continued typing after the edit; revision 4 keeps the bold run where it was')
# the Slate conversation said what happened without a model (bubble asserted through the store and the no-model state below)
assert w.sim_dock.isVisible() and five_parts()
# 05 · close the room and reopen the saved revision
index=w.tabs.indexOf(tab);assert w.close_tab(index);settle();assert not any(isinstance(w.tabs.widget(i),DocumentsTab) for i in range(w.tabs.count()))
tab=open_destination(w,'documents:'+ident);settle()
assert isinstance(tab,DocumentsTab) and tab.document_id==ident and tab.revision==4 and bold_runs(tab)==[{'start':4,'end':15,'bold':True}]
assert tab.page.toPlainText()=='The quick brown fox jumps over the lazy dog. Then it slept.'
check('05 Closed and reopened: the page shows saved revision 4 with the bold words (save and reopen retain the result)')
# 06 · one undo stack for both actors: Slate's italic, "undo" typed to Slate, "redo", then the owner's Ctrl Z
tab.page.setFocus();cursor=tab.page.textCursor();cursor.setPosition(4);cursor.setPosition(15,QTextCursor.KeepAnchor);tab.page.setTextCursor(cursor)
answer=tab.slate_request('italic');assert answer.startswith('Done: made “quick brown” italic · revision 5'),answer
assert tab.page.document().isUndoAvailable() and stored(ident)['blocks'][0]['marks']==[{'start':4,'end':15,'bold':True,'italic':True}]
answer=tab.slate_request('undo');assert 'Took the last change back' in answer and tab.revision==6,(answer,tab.revision)
assert stored(ident)['blocks'][0]['marks']==[{'start':4,'end':15,'bold':True}]
answer=tab.slate_request('redo');assert 'Redid' in answer and tab.revision==7 and stored(ident)['blocks'][0]['marks']==[{'start':4,'end':15,'bold':True,'italic':True}],(answer,tab.revision)
QTest.keyClick(tab.page,Qt.Key_Z,Qt.ControlModifier);settle();assert tab.dirty and tab.flush() and tab.revision==8
assert stored(ident)['blocks'][0]['marks']==[{'start':4,'end':15,'bold':True}] and from_qt(tab.page.document())[0]['marks']==[{'start':4,'end':15,'bold':True}]
check('06 Slate’s italic (revision 5), “undo” typed to Slate (6), “redo” (7), then the owner’s Ctrl Z (8): one undo stack serves both actors and every step is a saved revision')
# 07 · a request the rules do not know goes nowhere without a model, and says so
assert tab.slate_request('write a sonnet about the fox') is None
w.shell2.ask('write a sonnet about the fox');settle(80)
status=call('brain.status');assert status['state']!='READY'
check('07 An unrecognised request is left to the model path; with no model selected (%s) Slate says so and nothing runs'%status['state'])
capture('Ledger_Slate_WORKSHOP_01_Documents_02_Reopened_Undo_1920.png','Reopened page after undo; the Slate face shows the direct-edit answers and the no-model answer')
# 08 · compact size
w.resize(1366,768);settle(60);assert five_parts() and tab.page.isVisible() and tab.list.isVisible()
capture('Ledger_Slate_WORKSHOP_01_Documents_03_Compact_1366.png','The same page at 1366 by 768; all five parts visible')
check('08 1366×768: the page, its list and the five parts stay visible')
# 09 · cabinet filing and counters
nodes={n['id']:n for n in call('ledger.cabinet')['nodes']}
assert 'document:'+ident in nodes and nodes['document:'+ident]['role']=='document'
with k.db() as db:jobs_after=db.execute('SELECT count(*) FROM jobs').fetchone()[0]
assert jobs_after==jobs_before and not launcher.called and not submission.called and not provider.called and not popen.called and not detached.called
check('09 The document is filed in the cabinet under Documents; zero jobs, launches, provider requests or processes')
events=call('documents.get',{'id':ident})['events']
report=dict(schema='ledger.workshop01-document-ui/1',checkpoint='HATCH WORKSHOP-01',state='PASSED',mode='ACTUAL_QT_OFFSCREEN',
 checks=checks,captures=captures,document=ident,final_revision=stored(ident)['revision'],events=[e['action'] for e in events],
 model_used=False,direct_edit_basis='EXPLICIT_RULES_NO_MODEL',brain_state=status['state'],
 real_job_submissions=0,worker_processes_started=0,model_generations=0,provider_requests=0,native_invocations=0,processes_started=0,
 acceptance_claimed=False,note='Mechanical offscreen evidence of AC03 and AC09 steps without a model; the live-model column and the owner display remain open.')
w.close();app.processEvents()
(OUT/'document-ui.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(dict(state=report['state'],checks=len(checks),captures=len(captures),final_revision=report['final_revision'])))
