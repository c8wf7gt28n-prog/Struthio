"""Actual Qt checks for launch defaults; worker execution is held at Kernel.launch."""
import hashlib,json,os,sys,tempfile
from pathlib import Path
from unittest.mock import patch
PROGRAM=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('ARC_LEDGER_MODEL_CAPTURE_DIR',str(PROGRAM/'build/ui_checks/model_settings')));OUT.mkdir(parents=True,exist_ok=True)
RUN=Path(tempfile.mkdtemp(prefix='ledger-model01-ui-'))
os.environ.update(QT_QPA_PLATFORM='offscreen',ARC_LEDGER_EMBEDDED='1',ARC_LEDGER_DISABLE_BOOK_WATCHER='1',
 ARC1_WORKBENCH_CONFIG_HOME=str(RUN/'profile'),ARC_LEDGER_CONCERN=str(RUN/'Concern'))
sys.path.insert(0,str(PROGRAM));sys.dont_write_bytecode=True
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from workbench.qt_app import make_app,WorkbenchWindow
from workbench import locations,clip,local_brain as brain,settings_registry
from workbench.engineering_kernel import operator,Kernel
from workbench.session import Session
from tests_integrated.test_model_settings import fixture_model
provider=patch.object(clip,'_request',side_effect=AssertionError('No provider request')).start()
launch=patch.object(Kernel,'launch',side_effect=AssertionError('No worker launch'));launch.start()
submission=patch.object(Kernel,'submit',side_effect=AssertionError('No job submission'));submission.start()
app=make_app([]);root=locations.office(RUN/'workspace');session=Session(RUN/'profile/session.json',root)
w=WorkbenchWindow(root,session,restore=False);bridge=w.ledger_bridge;k=bridge.kernel;checks=[];captures=[]
def settle(wait=25):
 for name in ('agenda_runner','study_idle'):
  obj=getattr(w,name,None)
  if obj and hasattr(obj,'timer'):obj.timer.stop()
 for _ in range(2):app.processEvents();QTest.qWait(wait)
def call(op,args=None):
 r=k.dispatch(op,args or {},operator());assert r['ok'],r;return r['result']
def row(key):return next(r for r in call('ledger.settings')['settings'] if r['key']==key)
def show(key):
 tab=bridge.show_settings(key=key);settle();return tab
def check(text):checks.append(text);print(text,flush=True)
def apply(tab):
 tab.scroll.ensureWidgetVisible(tab.apply_button);settle();QTest.mouseClick(tab.apply_button,Qt.LeftButton);settle()
def capture(name,note):
 w.operations_panel.refresh();settle();p=OUT/name;assert w.grab().save(str(p),'PNG')
 captures.append(dict(file=name,note=note,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),resolution=[w.width(),w.height()]))
w.resize(1920,1200);w.show();settle()
tab=show('brain.memory_mb')
assert all('setting:'+key in w.settings_navigator.items for key in settings_registry.MODEL_KEYS)
assert tab.number.value()==0 and tab.number.text()=='Auto' and tab.model_panel.isVisible()
assert tab.current['effective'] is None and tab.current['application_state']=='NO_MODEL_SELECTED'
assert not tab.model_panel.reload.isEnabled() and not tab.model_panel.restore.isEnabled()
capture('Ledger_Slate_HATCH_Model_01_Defaults.png','Actual Settings with no model selected. Auto is a saved launch preference; no worker is observed.')
check('Three genuine launch defaults appear under Slate / Local model; missing model state is not fabricated')
tab.number.setValue(4096);apply(tab);assert row('brain.memory_mb')['stored']==4096 and len(k.listing('jobs'))==0
QTest.mouseClick(tab.undo_button,Qt.LeftButton);settle();assert row('brain.memory_mb')['stored']==0
check('Apply and Undo change only saved defaults through the shared journal and submit no model job')
tab.number.setValue(256);apply(tab);assert row('brain.memory_mb')['stored']==0 and tab.number.value()==256
assert 'Auto' in tab.note.text();tab.reload_latest()
check('A manual memory cap below 512 MiB is refused while the highlighted draft is retained')
for key,value in [('brain.context',4096),('brain.threads',6)]:
 tab=show(key);tab.number.setValue(value);apply(tab)
model=fixture_model();brain.put(k,'model.'+model['id'],model)
selection=dict(model_id=model['id'],config=dict(context=1024,threads=2,memory_mb=2048),owner=operator().identity)
brain.put(k,'selection',selection);tab=show('brain.context')
assert tab.current['stored']==4096 and tab.current['effective'] is None and '1024 tokens' in tab.model_panel.summary.text()
assert 'model stopped' in tab.model_panel.summary.text()
capture('Ledger_Slate_HATCH_Model_01_Stopped.png','A disposable stored selection fixture has a different prior configuration. No worker is running, so effective remains unobserved.')
check('A recorded configuration is shown separately from saved defaults and never supplies a running value')
source=root/'Files/model_settings_draft.py';source.parent.mkdir(exist_ok=True);source.write_text('original = True\n')
original=(source.read_bytes(),source.stat().st_mode);editor=w.open_document(source);editor.appendPlainText('# preserve this unfinished source')
tab=show('brain.context');assert editor.document().isModified()
tab.number.setValue(6144);base_revision=tab.current['revision']
call('ledger.settings.set',dict(key='brain.context',value=5120,expected_revision=row('brain.context')['revision']))
tab.poll();apply(tab);assert tab.number.value()==6144 and row('brain.context')['stored']==5120 and 'REVISION_CHANGED' in tab.note.text()
tab.reload_latest();tab.number.setValue(4096);apply(tab)
check('Settings retains the edited source Preview and refuses an intervening saved-default revision without losing the draft')
tab.scroll.ensureWidgetVisible(tab.model_panel.reload);settle()
# Reload is the one step that queues a request: Kernel.submit runs once for real and its worker launch is recorded, never run.
submission.stop();launch.stop();recording=patch.object(Kernel,'launch');launch_mock=recording.start()
QTest.mouseClick(tab.model_panel.reload,Qt.LeftButton);settle(100)
control=w.tabs.currentWidget();assert type(control).__name__=='BrainTab'
for _ in range(12):
 settle(50)
 if k.listing('jobs') and launch_mock.call_count and control.job:break
jobs=k.listing('jobs');assert len(jobs)==1 and jobs[0]['tool']=='brain.activate' and jobs[0]['state']=='Queued'
job=jobs[0];assert launch_mock.call_count==1
assert job['brain_launch']['options']['context']==4096 and job['brain_launch']['options']['threads']==6
assert job['brain_launch']['options']['memory_mb']>=512
recording.stop();launch.start();submission.start()
check('Reload uses the original Brain control and queues one owned request; the native worker launcher is held')
tab=show('brain.memory_mb');tab.number.setValue(4096);apply(tab)
pending=call('jobs.get',{'id':job['id']});assert pending['brain_launch']==job['brain_launch']
assert tab.current['requested']==job['brain_launch']['options']['memory_mb'] and tab.current['effective'] is None
assert not tab.model_panel.reload.isEnabled() and 'frozen at submission' in tab.model_panel.summary.text()
capture('Ledger_Slate_HATCH_Model_01_Pending.png','One genuine queued model request has frozen options. Its native launch is held; later default edits do not rewrite it.')
check('A later default edit leaves the waiting request unchanged; requested, stored and unobserved running values stay distinct')
call('jobs.cancel',{'id':job['id']});control.refresh();settle()
w.tabs.setCurrentWidget(control);control.refresh_launch_defaults(force=True);control.threads.setValue(8)
tab=show('brain.threads');tab.number.setValue(7);apply(tab)
w.tabs.setCurrentWidget(control);control.refresh();settle()
assert control.threads.value()==8 and control._launch_saved['threads']==7 and 'overrides' in control.launch_defaults_note.text()
assert control.property('ledgerRoom') and w.tabs.indexOf(editor)>=0 and editor.document().isModified()
capture('Ledger_Slate_HATCH_Model_01_Model_Controls.png','The existing model controls retain a local thread override while the saved default changes. The fixture model is unqualified; no GGUF is loaded.')
check('Legacy model controls follow unchanged fields from shared defaults while preserving local request overrides and edited source')
QTest.mouseClick(control.defaults_button,Qt.LeftButton);settle()
assert control.threads.value()==7 and not control._launch_dirty
QTest.mouseClick(control.edit_defaults_button,Qt.LeftButton);settle()
assert type(w.tabs.currentWidget()).__name__=='SettingsTab' and w.tabs.currentWidget().key=='brain.context'
check('Use saved launch defaults deliberately clears local overrides; Edit defaults returns to the exact shared Settings key')
tab=show('brain.memory_mb');w.resize(1366,768);settle();tab.scroll.ensureWidgetVisible(tab.model_panel);settle()
assert w.trash_can.isVisible() and w.shell2.top.nice.isVisible() and w.operations_monitors.isVisible() and w.return_thread.footer.isVisible()
assert tab.model_panel.isVisible() and w.settings_navigator.selected_key()=='brain.memory_mb'
capture('Ledger_Slate_HATCH_Model_01_Compact.png','Actual compact Settings view. The queued fixture request is cancelled and no running worker is claimed.')
check('Compact Settings keeps the model readback, selected key, fixed Trash, Stop, monitors and return thread reachable')
assert (source.read_bytes(),source.stat().st_mode)==original
assert all(j['state']=='Cancelled' for j in k.listing('jobs'));assert launch_mock.call_count==1
editor.document().setModified(False);assert w.close() is True;settle();assert not w.desktop_lease.exists()
provider.assert_not_called();provider.stop();submission.stop();launch.stop()
check('Clean close preserves original source bytes/mode, removes the desktop lease and makes no provider or native-model call')
result=dict(state='PASSED',mode='ACTUAL_QT_OFFSCREEN',checks=checks,captures=captures,
 model_metadata_fixture='DISPOSABLE_UNQUALIFIED_CONFIGURATION_RECORD',queued_job_submissions=1,worker_launcher_held=True,
 worker_processes_started=0,model_generations=0,provider_requests=0,native_invocations=0,
 automatic_rollback_ui_qualification=False,real_model_and_owner_host_acceptance=False,clean_close=True)
(OUT/'model-settings-ui.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)
