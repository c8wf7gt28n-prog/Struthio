"""Actual Qt checks of Graphite's service cycle: timers after a failed cycle, idle cost with job history, unreadable cycle rows,
stale running records, pre-cycle failures and readback after a committed ON; and the cycle's main path through the menu's own
On, Off and Reboot actions (taken in from the former SERVICE-01 lifecycle check): a declined confirmation, a confirmed Off that
saves the working file, cancels a queued record and waits for a running one, the provider in-flight hold, what is refused while
services are off, On that replays nothing and Reboot that keeps the source.
Disposable job rows only; Kernel.launch, Kernel.submit and clip._request are held for the whole run."""
import hashlib,json,os,sys,tempfile,time
from pathlib import Path
from unittest.mock import patch
PROGRAM=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('ARC_LEDGER_SERVICE_INTEGRATION_CAPTURE_DIR',str(PROGRAM/'build/ui_checks/service_integration')));OUT.mkdir(parents=True,exist_ok=True)
RUN=Path(tempfile.mkdtemp(prefix='ledger-integration01-service-ui-'))
os.environ.update(QT_QPA_PLATFORM='offscreen',ARC_LEDGER_EMBEDDED='1',ARC_LEDGER_DISABLE_BOOK_WATCHER='1',
 ARC1_WORKBENCH_CONFIG_HOME=str(RUN/'profile'),ARC_LEDGER_CONCERN=str(RUN/'Concern'))
sys.path.insert(0,str(PROGRAM));sys.dont_write_bytecode=True
from PySide6.QtCore import Qt,QPoint
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QMessageBox
from PySide6.QtTest import QTest
from workbench.qt_app import make_app,WorkbenchWindow
from workbench import locations,clip,local_brain,service_lifecycle as services,work_trail
from workbench.engineering_kernel import Kernel,operator
from workbench.session import Session
provider=patch.object(clip,'_request',side_effect=AssertionError('No provider request')).start()
launcher=patch.object(Kernel,'launch',side_effect=AssertionError('No worker launch')).start()
submission=patch.object(Kernel,'submit',side_effect=AssertionError('No job submission')).start()
from workbench import session_power  # D2-fix: the one session and power function is held for the whole run, on any computer
def held_power(request):
 """logind answers that there is no login session; no session or power command may start."""
 if request[0]=='logind':raise OSError('no login session (held by this check)')
 raise AssertionError('No session or power command: %r'%(request,))
held_logind=patch.object(session_power,'system',side_effect=held_power).start()
question=patch.object(QMessageBox,'question',return_value=QMessageBox.Yes).start()
app=make_app([]);root=locations.office(RUN/'workspace');session=Session(RUN/'profile/session.json',root)
w=WorkbenchWindow(root,session,restore=False);k=w.ledger_bridge.kernel;hatch=w.type_bar.hatch;life=hatch.lifecycle
checks=[];captures=[];warnings=[];timings={}
def settle(ms=25):
 # The Agenda and Study timers stay alive on purpose: their pause and return are under test.
 for _ in range(2):app.processEvents();QTest.qWait(ms)
def phase():return services.snapshot(k)['phase']
def wait_phase(expected):
 for _ in range(100):
  settle(15)
  if phase()==expected and not life.busy:return
 raise AssertionError((expected,phase(),life.pending,life.busy,warnings))
def check(text):checks.append(text);print(text,flush=True)
def panel():
 w.a_host_service.trigger();tab=w.tabs.currentWidget();tab.refresh();w.operations_panel.refresh();settle();return tab
def capture(name,note,popup=None):
 w.operations_panel.refresh();settle();pix=w.grab();mode='ACTUAL_QT_WINDOW_GRAB'
 if popup is not None:
  assert popup.isVisible();p=QPainter(pix);p.drawPixmap(w.mapFromGlobal(popup.mapToGlobal(QPoint(0,0))),popup.grab());p.end()
  mode='ACTUAL_QT_WINDOW_AND_VISIBLE_POPUP_GRABS'
 target=OUT/name;assert pix.save(str(target),'PNG')
 captures.append(dict(file=name,note=note,mode=mode,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),resolution=[w.width(),w.height()]))
def warning(parent,title,text,*args):
 warnings.append(dict(title=title,text=text));return QMessageBox.Ok
warn=patch.object(QMessageBox,'warning',side_effect=warning).start()
def job(ident,state='Running',**extra):
 clock=time.time();k.save('jobs',dict(id=ident,owner=operator().identity,tool='brain.infer',state=state,created=clock,started=clock,timeout=120,**extra))
def finish(ident):
 row=k.record('jobs',ident);row.update(state='Completed',finished=time.time());k.save('jobs',row)
def write_row(raw):
 with k.db() as db:db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',(services.KEY,raw))
def timed(fn,n=3):
 fn();best=None
 for _ in range(n):
  start=time.perf_counter();fn();best=min(best if best is not None else 9e9,time.perf_counter()-start)
 return best
def menu_actions(*texts):return [w.a_new_idea,w.a_new_project]  # HATCH DESK D2: creation is under Work (the cat opens the programs list)
system_menu=w.shell2.top.nice.menu_();choices=system_menu.service_actions  # D2: Graphite services On · Off · Restart are the System menu's (keys On, Off, Reboot)
w.resize(1920,1200);w.show();settle();w.ledger_bridge.timer.stop();life.timer.stop()
timers=[t for t in (getattr(getattr(w,name,None),'timer',None) for name in ('agenda_runner','study_idle')) if t is not None]
assert len(timers)==2 and all(t.isActive() for t in timers),timers
hatch.refresh();assert life.state['phase']=='ADMISSION_ON' and life.last_error is None
# A · paused Agenda and Study timers return after a cycle fails on a newer owner Stop.
job('a'*32);life.request('Reboot');settle()
assert phase()=='DRAINING' and life.pending=='Reboot' and not any(t.isActive() for t in timers) and len(life.paused)==2,(phase(),life.paused)
assert 'no live worker' in w.statusBar().currentMessage(),w.statusBar().currentMessage()
work_trail.hold(k,operator());finish('a'*32);life.drain();settle()
assert life.pending is None and phase()=='CHANGED' and work_trail.work_status(k)['held'] and not services.snapshot(k)['admission_enabled']
assert len(warnings)==1 and warnings[-1]['title']=='Graphite service cycle incomplete' and 'automatic restart' in warnings[-1]['text'],warnings
assert all(t.isActive() for t in timers) and life.paused==[],[t.isActive() for t in timers]
check('A newer owner Stop that fails a pending Reboot returns the paused Agenda and Study timers; the hold is preserved and nothing restarts by itself')
# B · failures before begin() are reported as "not started"; nothing is recorded.
before=services.snapshot(k)['cycle_id'];w.statusBar().clearMessage()
with patch.object(w,'save_all',return_value=False):life.request('Off')
assert w.statusBar().currentMessage()=='Off not started · save was cancelled or failed',w.statusBar().currentMessage()
assert services.snapshot(k)['cycle_id']==before and len(warnings)==1
with patch.object(w,'save_all',side_effect=OSError('Fixture save failure')):life.request('Off')
assert len(warnings)==2 and warnings[-1]['title']=='Graphite services · Off not started',warnings[-1]
assert 'Fixture save failure' in warnings[-1]['text'] and 'No service cycle was recorded' in warnings[-1]['text']
assert services.snapshot(k)['cycle_id']==before and phase()=='CHANGED' and life.pending is None
tab=panel();dialog=QMessageBox(QMessageBox.Warning,warnings[-1]['title'],warnings[-1]['text'],QMessageBox.Ok,w)
dialog.setWindowModality(Qt.WindowModal);dialog.show();settle()
capture('Ledger_Slate_HATCH_Integration_01_Not_Started.png','The actual warning when Save fails before any cycle begins: titled "not started"; no cycle row and no admission change were recorded.',dialog)
dialog.accept();settle()
check('Save cancellation and a save failure before begin() report "Off not started" with no cycle or admission change recorded, instead of an incomplete cycle')
life.request('On');settle();assert phase()=='ON' and not work_trail.work_status(k)['held'] and len(warnings)==2
message=w.statusBar().currentMessage();assert 'not changed by On' in message and 'stays off' not in message,message
check('Explicit On reports the phone listener as observed and unchanged by On, instead of asserting that phone access is off')
# C · a Running record whose worker has exited names the owner routes; Off completes once it is terminal.
job('b'*32,pid=999999,worker_start='gone');life.request('Off');settle()
assert phase()=='DRAINING' and life.pending=='Off'
counts=services.snapshot(k)['counts'];assert (counts['running'],counts['live_workers'],counts['protected_workers'],counts['stale_running'])==(1,0,0,1),counts
assert w.statusBar().currentMessage()=='1 running record has no live worker · use Master Stop or Work trail → recover',w.statusBar().currentMessage()
tab=panel();assert 'no live worker' in tab.cycle.text() and 'Finishing running work' in tab.cycle.text(),tab.cycle.text()
capture('Ledger_Slate_HATCH_Integration_01_Stale_Running.png','A disposable Running record whose recorded worker pid has exited: the drain hold names Master Stop and Work trail → recover instead of waiting silently. No worker exists.')
finish('b'*32);life.drain();wait_phase('OFF');assert work_trail.work_status(k)['held'] and not services.snapshot(k)['admission_enabled']
assert not any(t.isActive() for t in timers) and len(life.paused)==2
check('A Running record without a live worker is counted as stale_running and the drain names the route that resolves it; Off completes after the record is terminal')
# C2 · Off followed by Settings re-enable and Resume returns the timers through the ordinary refresh.
r1=k.dispatch('ledger.settings.set',{'key':'operations.services_enabled','value':True},operator());r2=k.dispatch('ledger.work.resume',{},operator())
assert r1['ok'] and r2['ok'],(r1,r2)
life.drain();settle();assert phase()=='CHANGED' and all(t.isActive() for t in timers) and life.paused==[]
check('After a completed Off, Settings re-enable plus Resume returns the paused timers through refresh(); no Hatch route is required')
# D · job history with exited worker pids no longer costs the idle 1 s tick.
clock=time.time()
with k.db() as db:
 for i in range(300):
  ident='%032x'%(0x100000+i);row=dict(id=ident,owner=operator().identity,state='Completed',tool='lab.python',pid=4000000-i,worker_start='1234567',created=clock,finished=clock)
  db.execute('INSERT INTO jobs VALUES(?,?,?,?)',(ident,operator().identity,'Completed',json.dumps(row)))
timings['drain_ms_300_completed_exited_pids']=round(timed(life.drain)*1000,1)
timings['operations_refresh_ms_300_completed_exited_pids']=round(timed(w.operations_panel.refresh)*1000,1)
assert timings['drain_ms_300_completed_exited_pids']<100,timings
with k.db() as db:db.execute("DELETE FROM jobs WHERE state='Completed' AND payload LIKE '%lab.python%'")
check('With 300 completed records carrying exited worker pids an idle drain() tick stays under 0.1 s; terminal rows are no longer probed')
# E · unreadable cycle rows: creation routes and Operations stay available; the status bar is told once.
write_row('{"schema":"unsupported"}');w.statusBar().clearMessage();life.drain();settle()
assert life.state['phase']=='UNAVAILABLE' and 'UNAVAILABLE' in w.statusBar().currentMessage(),w.statusBar().currentMessage()
w.statusBar().showMessage('An owner message that should survive')
for _ in range(3):life.drain();settle()
assert w.statusBar().currentMessage()=='An owner message that should survive',w.statusBar().currentMessage()
hatch.refresh();assert not any(a.isEnabled() for a in choices.values()),{word:a.isEnabled() for word,a in choices.items()}
creation=menu_actions('New Idea','New Project');assert len(creation)==2 and all(a.isEnabled() for a in creation)
w.operations_panel.refresh();settle()
assert w.operations_panel.work.queue.isEnabled() and 'unavailable' in w.operations_panel.services.text(),w.operations_panel.services.text()
tab=panel();assert 'status unavailable' in tab.cycle.text(),tab.cycle.text()
system_menu.open_menu(False);settle()
capture('Ledger_Slate_HATCH_Integration_01_Unavailable.png','An unreadable service-cycle row: the System menu\'s Graphite services On, Off and Restart disabled, New Idea and New Project (Work) available, the Operations queue and Agenda still readable, one status message instead of one per second.',system_menu)
system_menu.close_menu();settle()
check('An unreadable cycle row disables only the service actions; Operations keeps its queue and the UNAVAILABLE message is shown once, not every tick')
write_row(json.dumps(dict(schema='ledger.service-cycle/1',phase='OFF',id='c'*32)))
life.drain();tab.refresh();settle()
assert life.state['phase']=='UNAVAILABLE' and life.state['error'].startswith('SERVICE_CYCLE_UNAVAILABLE') and 'status unavailable' in tab.cycle.text(),life.state
reply=k.dispatch('ledger.operations',{},operator());assert reply['ok'] and reply['result']['services']['phase']=='UNAVAILABLE',reply
check('A partial cycle row reads UNAVAILABLE through the timer slot, the service room and ledger.operations without a KeyError')
with k.db() as db:db.execute('DELETE FROM settings WHERE key=?',(services.KEY,))
life.drain();settle();assert life.state['phase']=='ADMISSION_ON' and life.last_error is None
# F · a failure after the committed ON is journaled, never a downgrade; the model note follows observation.
hatch.refresh();life.request('Reboot');wait_phase('ON')
receipt=life.receipt;assert receipt['phase']=='ON' and receipt['action']=='Reboot' and services.snapshot(k)['model_restore']=='NOT_REQUESTED'
life.model_before={'model_id':'m'*64,'config':{'context':2048}}
with patch.object(k,'dispatch',side_effect=RuntimeError('Fixture dispatch failure')):note=life.restore_model()
assert 'could not be requested' in note and 'Fixture dispatch failure' in note,note
status=services.snapshot(k);assert (status['phase'],status['model_restore'],status['model_restore_display'],status['admission_enabled'])==('ON','FAILED','FAILED',True),status
services.fail(k,life.receipt,operator());status=services.snapshot(k)
assert status['phase']=='ON' and status['admission_enabled'] and not status['work_held'] and status['summary']=='New work enabled',status
hatch.refresh();assert not choices['On'].isEnabled() and choices['Off'].isEnabled() and choices['Reboot'].isEnabled()
tab=panel();assert 'New work enabled' in tab.cycle.text() and 'reload failed' in tab.cycle.text(),tab.cycle.text()
life.receipt=services.restore_note(k,life.receipt,operator(),'REQUESTED',job_id='e'*32,model_id='m'*64)
tab.refresh();assert 'reload requested; inspect' in tab.cycle.text(),tab.cycle.text()
ready={'state':'READY','selection':{'model_id':'m'*64},'worker':{'model_id':'m'*64}}
with patch.object(local_brain,'status',return_value=ready):tab.refresh();observed=tab.cycle.text();status=services.snapshot(k)
assert (status['model_restore'],status['model_restore_display'])==('REQUESTED','OBSERVED_RUNNING') and 'observed running' in observed,observed
k.save('jobs',dict(id='e'*32,owner=operator().identity,state='Failed',tool='brain.activate'))
tab.refresh();assert services.snapshot(k)['model_restore_display']=='REQUEST_FAILED' and 'did not complete' in tab.cycle.text(),tab.cycle.text()
capture('Ledger_Slate_HATCH_Integration_01_After_On.png','Readback after a committed ON whose later step failed: the phase stays ON with new work enabled; the model note says the reload request did not complete. Nothing is launched.')
check('A failure after the committed ON journals the problem and keeps ON readable; the model reload note follows the observed job and model state while the stored note stays a request')
# H · the main path through the menu's own service actions.
for timer in timers:timer.stop()  # the timers' pause and return were tested above; here only the cycle and its words
before=services.snapshot(k);assert before['phase'] in ('ON','ADMISSION_ON') and before['admission_enabled'],before
with patch.object(QMessageBox,'question',return_value=QMessageBox.Cancel):life.request('Off')
after=services.snapshot(k);assert (after['phase'],after['cycle_id'],after['admission_enabled'])==(before['phase'],before['cycle_id'],True) and len(warnings)==2
check('Declining the service confirmation leaves admission and the cycle journal untouched')
source=root/'Files/service_cycle_draft.py';source.parent.mkdir(exist_ok=True);source.write_text('original = True\n');mode=source.stat().st_mode
editor=w.open_document(source);editor.appendPlainText('# saved before a confirmed stop');settle()
job('f'*32);job('9'*32,state='Queued')
hatch.refresh();choices['Off'].click();settle()
for _ in range(80):
 settle(15)
 if not life.busy and k.record('jobs','9'*32)['state']=='Cancelled':break
assert phase()=='DRAINING' and not work_trail.work_status(k)['held']
assert k.record('jobs','f'*32)['state']=='Running' and k.record('jobs','9'*32)['state']=='Cancelled'
assert '# saved before' in source.read_text() and source.stat().st_mode==mode,(source.read_text(),oct(source.stat().st_mode),oct(mode))
saved=source.read_bytes();hatch.refresh()
assert all(not action.isEnabled() for action in choices.values()),{word:a.isEnabled() for word,a in choices.items()}
creation=menu_actions('New Idea','New Project');assert len(creation)==2 and all(a.isEnabled() for a in creation)
capture('Graphite_Service_Draining.png','Off chosen from the menu: the working file was saved, one disposable Queued record was cancelled and one Running record keeps the cycle draining. New work is held while the window stays usable; no worker exists.')
check('Off from the menu saves the working file with its mode, cancels the queued record and waits for the running one; while draining all three service actions are disabled and New Idea and New Project stay available')
w.open_clip();settle();overlay=w.clip_overlay;assert overlay is not None
overlay.busy=True;overlay._requests_inflight.add(123456)
finish('f'*32);life.drain();assert phase()=='DRAINING' and not work_trail.work_status(k)['held']
overlay.busy=False;overlay._requests_inflight.clear();overlay.refresh()
life.drain();wait_phase('OFF');assert work_trail.work_status(k)['held'] and not services.snapshot(k)['admission_enabled']
check('The provider in-flight indicators hold the drain after every job is terminal; Off completes once they clear; no provider request is issued')
tab=panel();assert 'services off' in tab.cycle.text(),tab.cycle.text()
hatch.refresh();assert not choices['Off'].isEnabled() and 'already off' in choices['Off'].toolTip() and choices['On'].isEnabled()
with patch.object(w.process,'start',side_effect=AssertionError('No command starts while services are off')):
 w.run_tool(['fixture-that-must-not-run'],'Held command')
assert 'SERVICES_OFF' in w.statusBar().currentMessage(),w.statusBar().currentMessage()
overlay._ask();assert not overlay.busy and not overlay._requests_inflight
provider.assert_not_called()
check('While services are off: Off is unavailable with the reason already off and On is the way back; the service room says services off; a direct desktop command and a new cloud reply are refused while editing stays available')
editor.appendPlainText('# unfinished edit retained across On and Reboot');assert editor.document().isModified()
hatch.refresh();choices['On'].click();settle()
assert phase()=='ON' and not work_trail.work_status(k)['held'] and editor.document().isModified()
assert k.record('jobs','9'*32)['state']=='Cancelled' and source.read_bytes()==saved
check('On from the menu reopens admission and releases the hold together; it replays no cancelled record and leaves the unfinished edit in its tab')
hatch.refresh();choices['Reboot'].click();wait_phase('ON')
assert services.snapshot(k)['action']=='Reboot' and source.stat().st_mode==mode and '# unfinished edit retained' in source.read_text()
editor.document().setModified(False);check('Reboot from the menu cycles the services in the same window and saves the unfinished edit with its mode kept')
assert len(warnings)==2
# G · desktop close stops the lifecycle timer and joins the close thread.
life.timer.start();assert life.timer.isActive()
assert w.close() is True;settle()
assert not life.timer.isActive() and not w.desktop_lease.exists() and (life.worker is None or not life.worker.is_alive())
assert all(row['state'] in ('Completed','Failed','Cancelled') for row in k.listing('jobs'))
launcher.assert_not_called();submission.assert_not_called();provider.assert_not_called();assert len(warnings)==2
check('Clean close runs LedgerLifecycle.shutdown(): the 1 s timer stops and the close thread is joined; zero native, model or provider launches')
result=dict(state='PASSED',mode='ACTUAL_QT_OFFSCREEN',checks=checks,captures=captures,timings_ms=timings,warnings=warnings,
 disposable_job_records=5,history_fixture_rows=300,real_job_submissions=0,all_kernel_launchers_held=True,worker_processes_started=0,
 model_generations=0,provider_requests=0,native_invocations=0,owner_host_acceptance=False,clean_close=True)
(OUT/'service-integration-ui.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)
warn.stop();question.stop();submission.stop();launcher.stop();provider.stop()
