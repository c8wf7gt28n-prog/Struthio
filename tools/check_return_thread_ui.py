"""Actual offscreen session/recovery checks over disposable saved records."""
import json,os,sys,tempfile,hashlib
from pathlib import Path
from unittest.mock import patch
PROGRAM=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('ARC_LEDGER_RETURN_CAPTURE_DIR',str(PROGRAM/'build/ui_checks/return_thread')));OUT.mkdir(parents=True,exist_ok=True)
RUN=Path(tempfile.mkdtemp(prefix='ledger-return01-ui-'))
os.environ.update(QT_QPA_PLATFORM='offscreen',ARC_LEDGER_EMBEDDED='1',ARC_LEDGER_DISABLE_BOOK_WATCHER='1',
 ARC1_WORKBENCH_CONFIG_HOME=str(RUN/'profile'),ARC_LEDGER_CONCERN=str(RUN/'Concern'))
sys.path.insert(0,str(PROGRAM));sys.dont_write_bytecode=True
from PySide6.QtCore import Qt,QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QMessageBox
from workbench.qt_app import make_app,WorkbenchWindow
from workbench import locations,clip
from workbench.engineering_kernel import operator,Kernel
from workbench.session import Session
app=make_app([]);root=locations.office(RUN/'workspace');session=Session(RUN/'profile/session.json',root)
provider=patch.object(clip,'_request',side_effect=AssertionError('No provider request')).start()
launcher=patch.object(Kernel,'launch',side_effect=AssertionError('No worker launch')).start()
submission=patch.object(Kernel,'submit',side_effect=AssertionError('No job submission')).start()
priority=patch('os.setpriority',side_effect=AssertionError('No OS priority change')).start()
w=WorkbenchWindow(root,session,restore=False);k=w.ledger_bridge.kernel;thread=w.return_thread;checks=[];captures=[]
def settle(window=w):
 for name in ('agenda_runner','study_idle'):
  obj=getattr(window,name,None)
  if obj and hasattr(obj,'timer'):obj.timer.stop()
 for _ in range(2):app.processEvents();QTest.qWait(35)
def call(op,args=None):
 r=k.dispatch(op,args or {},operator());assert r['ok'],r;return r['result']
def check(text):checks.append(text);print(text,flush=True)
def capture(name,widget=None,window=w):
 window.operations_panel.refresh();settle(window);target=widget or window;p=OUT/name;assert target.grab().save(str(p),'PNG')
 captures.append(dict(file=name,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),resolution=[target.width(),target.height()]))
w.resize(1920,1200);w.show();settle()
assert thread.footer.isVisible();check('The return thread is reachable from the persistent activity footer')
project=call('projects.create',{'title':'A supply worth returning to','intent':'Keep original assumptions distinct from the next experiment.'})
pid='project:'+project['id'];w.cabinet_page.refresh(force=True);w.cabinet_page.select(pid,reveal=True)
room=w.cabinet_page.open(pid);room.writing.setPlainText('Compare the worst frame with the original power budget.');draft=room.writing.toPlainText()
thread.refresh_footer();assert '1' in thread.footer.text()
check('The footer counts unfinished cabinet writing without saving an idea')
source=root/'Files/power.txt';source.parent.mkdir(exist_ok=True);source.write_text('Original power budget.\n')
editor=w.open_document(source);editor.insertPlainText('Unfinished comparison. ');buffer=editor.toPlainText();editor.document().setModified(True)
for ident,state in [('e'*32,'Running'),('f'*32,'Queued')]:k.save('jobs',dict(id=ident,owner='desktop-owner',state=state,tool='lab.python'))
w.ledger_bridge.cabinet_drafts['project:missing']=dict(title='',text='An unavailable record must not take this writing with it.')
tab=thread.show();tab.writing.setPlainText('Begin with the declared limits; then ask what we can actually measure.');note=tab.writing.toPlainText()
QTest.mouseClick(tab.keep_button,Qt.LeftButton);settle();tab.refresh()
stored=call('ledger.session.read');assert stored['note']==note and stored['revision']==1
assert {r['id'] for r in stored['drafts']}=={pid,'project:missing'}
assert call('ideas.list')['records']==[] and call('projects.get',{'id':project['id']})==project
assert source.read_text()=='Original power budget.\n' and editor.toPlainText()==buffer
recovery=w.recovery.entries();assert len(recovery)==1 and recovery[0]['content']==buffer
check('Keep writes separate cabinet/return copies and the existing code recovery store without changing originals or creating an idea')
assert '1 active' in tab.activity_note.text() and '1 queued' in tab.activity_note.text()
check('Activity is labelled as caller-visible recorded states rather than a verified process census')
capture('Ledger_Slate_HATCH_Return_01_Thread.png')
item=next(tab.drafts.topLevelItem(i) for i in range(tab.drafts.topLevelItemCount()) if tab.drafts.topLevelItem(i).data(0,Qt.UserRole)=='project:missing')
tab.drafts.setCurrentItem(item);tab.open_draft();settle()
assert w.tabs.currentWidget() is tab and 'must not take this writing' in tab.detail.toPlainText()
check('Unavailable cabinet records retain reviewable recovery writing without reassignment')
# Returning to a live editor only navigates; no buffer is loaded or replaced.
item=next(tab.views.topLevelItem(i) for i in range(tab.views.topLevelItemCount()) if tab.views.topLevelItem(i).data(0,Qt.UserRole)==str(id(editor)))
tab.views.setCurrentItem(item);tab.open_view();settle();assert w.tabs.currentWidget() is editor and editor.toPlainText()==buffer
check('Open-work navigation returns to the same edited buffer')
w.tabs.setCurrentWidget(tab);tab.detail.hide();w.resize(1366,768);settle();tab.refresh()
assert thread.footer.isVisible() and w.shell2.top.programs.isVisible() and w.trash_can.isVisible() and w.operations_monitors.isVisible()
assert tab.writing.placeholderText()=='poem';capture('Ledger_Slate_HATCH_Return_01_Compact.png')
check('Compact layout retains the thread footer, poem writing, fixed Trash, monitors and Stop')
w.resize(1920,1200);settle();before=call('ledger.session.read')
dialog=thread.exit_dialog();dialog.show();settle()
assert 'Linux stays on' in thread.close_policy();assert dialog.back_button.hasFocus()
capture('Ledger_Slate_HATCH_Return_01_Leaving.png',dialog)
QTimer.singleShot(50,dialog.back_button.click);assert dialog.exec()==0
assert not w._closing and call('ledger.session.read')==before
check('Exit review defaults to continuing work; cancelling leaves return writing and shutdown state untouched')
# A second session updates the stored note while the local thread stays edited.
tab.writing.setPlainText('This desktop has a newer unfinished thought.');local_note=tab.writing.toPlainText()
call('ledger.session.keep',dict(expected_revision=before['revision'],note='A thread kept by another session.',drafts=before['drafts']))
assert not thread.capture() and 'changed in another session' in thread.error
assert tab.writing.toPlainText()==local_note and w.ledger_bridge.cabinet_drafts[pid]['text']==draft
tab.inspect();assert 'another session' in tab.detail.toPlainText() and tab.writing.toPlainText()==local_note
tab.refresh();capture('Ledger_Slate_HATCH_Return_01_Conflict.png')
check('A newer stored copy blocks replacement; inspecting it does not replace local writing or the retained revision')
inspected=call('ledger.session.read')
call('ledger.session.keep',dict(expected_revision=inspected['revision'],note='Another change after inspection.',drafts=inspected['drafts']))
with patch.object(QMessageBox,'question',return_value=QMessageBox.Yes):tab.replace_inspected()
assert call('ledger.session.read')['note']=='Another change after inspection.' and tab.writing.toPlainText()==local_note
check('Even an explicit replacement cannot overwrite a copy changed after inspection')
tab.inspect()
with patch.object(QMessageBox,'question',return_value=QMessageBox.Yes):tab.replace_inspected()
assert call('ledger.session.read')['note']==local_note and thread.error==''
check('Explicitly replacing the inspected revision resolves a conflict through the same guarded keep command')
latest=call('ledger.session.read')
call('ledger.session.keep',dict(expected_revision=latest['revision'],note='A thread kept by another session.',drafts=latest['drafts']))
with patch.object(w,'ask_save',return_value='cancel'),patch.object(thread,'capture',side_effect=AssertionError('No capture after cancel')):
 assert w.close() is False and not w._closing
check('An existing file-save cancellation stops exit before the return checkpoint or shutdown')
with patch.object(w,'ask_save',return_value='discard'):
 assert w.close() is False and not w._closing
assert source.read_text()=='Original power budget.\n' and editor.toPlainText()==buffer
check('A return-copy conflict blocks normal close while the edited source and window remain intact')
with patch.object(w,'ask_save',return_value='discard'),patch.object(w.recovery,'put',side_effect=OSError('Controlled recovery write refusal')):
 assert w.close() is False and not w._closing
check('Recovery write failure stops exit before shutdown controllers')
# Exercise the explicit skip-new-copy choice. Existing source save prompts and
# their retained recovery behavior still run; no global Stop is invoked.
skipping=thread.exit_dialog();QTimer.singleShot(50,skipping.skip_button.click)
with patch.object(thread,'exit_dialog',return_value=skipping),patch.object(w,'ask_save',return_value='discard'),patch.object(w.master_stop_controller,'request',side_effect=AssertionError('No global Stop')):
 assert thread.review_exit() is True
settle();assert not thread.skip_keep_once and not w.desktop_lease.exists()
assert source.read_text()=='Original power budget.\n' and w.recovery.entries()[0]['content']==buffer
assert call('ledger.session.read')['note']=='A thread kept by another session.'
check('Explicit skip preserves the newer stored thread and dirty-file recovery while closing only the desktop')
recovery_offers=[]
with patch.object(WorkbenchWindow,'show_recovery',lambda self:recovery_offers.append(True)):
 w2=WorkbenchWindow(root,Session(RUN/'profile/session.json',root),restore=False);w2.resize(1920,1200);w2.show();settle(w2)
 assert recovery_offers
assert w2.return_thread.note=='A thread kept by another session.'
assert w2.ledger_bridge.cabinet_drafts[pid]['text']==draft
room2=w2.cabinet_page.open(pid);assert room2.writing.toPlainText()==draft
assert w2.recovery.entries()[0]['content']==buffer and source.read_text()=='Original power budget.\n'
check('A fresh desktop restores cabinet writing and the stored thread, and offers the original code recovery copy')
tab2=w2.return_thread.show();tab2.writing.setPlainText('Return after comparing the saved limits.');settle(w2);tab2.refresh()
capture('Ledger_Slate_HATCH_Return_01_Returned.png',window=w2)
for ident in ('e'*32,'f'*32):
 row=w2.ledger_bridge.kernel.record('jobs',ident);row['state']='Cancelled';w2.ledger_bridge.kernel.save('jobs',row)
assert w2.close() is True;settle(w2);assert not w2.desktop_lease.exists()
assert call('ledger.session.read')['note']=='Return after comparing the saved limits.'
check('Normal close keeps the current thread before shutdown and removes the desktop lease')
provider.assert_not_called();priority.assert_not_called();provider.stop();priority.stop()
result=dict(state='PASSED',mode='ACTUAL_QT_OFFSCREEN',checks=checks,captures=captures,
 fixture_job_records=2,jobs_submitted=0,model_calls=0,provider_requests=0,native_invocations=0,os_priority_changes=0,
 native_acceptance=False,unavailable_record_case='DISPOSABLE_MISSING_ID',recovery_failure_case='CONTROLLED_WRITE_REFUSAL',
 recovery_startup_dialog='OFFER_OBSERVED_NO_MODAL_INTERACTION',clean_close=True)
(OUT/'return-thread-ui.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)
