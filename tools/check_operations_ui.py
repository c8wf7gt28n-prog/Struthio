"""Actual Qt checks of right-column observations and original queue controls."""
import json,os,sys,tempfile,hashlib
from pathlib import Path
from unittest.mock import patch
PROGRAM=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('ARC_LEDGER_OPERATIONS_CAPTURE_DIR',str(PROGRAM/'build/ui_checks/operations')));OUT.mkdir(parents=True,exist_ok=True)
RUN=Path(tempfile.mkdtemp(prefix='ledger-operations01-ui-'))
os.environ.update(QT_QPA_PLATFORM='offscreen',ARC_LEDGER_EMBEDDED='1',ARC_LEDGER_DISABLE_BOOK_WATCHER='1',
 ARC1_WORKBENCH_CONFIG_HOME=str(RUN/'profile'),ARC_LEDGER_CONCERN=str(RUN/'Concern'))
sys.path.insert(0,str(PROGRAM));sys.dont_write_bytecode=True
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QSlider
from workbench.qt_app import make_app,WorkbenchWindow
from workbench import locations,clip,host_observations
from workbench.engineering_kernel import operator,Kernel
from workbench.session import Session
offline=patch.object(clip,'_request',side_effect=AssertionError('No provider request')).start()
launcher=patch.object(Kernel,'launch',side_effect=AssertionError('No worker launch')).start()
submission=patch.object(Kernel,'submit',side_effect=AssertionError('No job submission')).start()
from workbench import session_power  # D2-fix: the one session and power function is held for the whole run, on any computer
def held_power(request):
 """logind answers that there is no login session; no session or power command may start."""
 if request[0]=='logind':raise OSError('no login session (held by this check)')
 raise AssertionError('No session or power command: %r'%(request,))
held_logind=patch.object(session_power,'system',side_effect=held_power).start()
priority=patch('os.setpriority',side_effect=AssertionError('No real OS priority change in the UI fixture')).start()
app=make_app([]);root=locations.office(RUN/'workspace');session=Session(RUN/'profile/session.json',root)
w=WorkbenchWindow(root,session,restore=False);bridge=w.ledger_bridge;k=bridge.kernel;checks=[];captures=[]
def settle():
 for name in ('agenda_runner','study_idle'):
  obj=getattr(w,name,None)
  if obj and hasattr(obj,'timer'):obj.timer.stop()
 for _ in range(2):app.processEvents();QTest.qWait(30)
def call(op,args=None):
 r=k.dispatch(op,args or {},operator());assert r['ok'],r;return r['result']
def record(text):checks.append(text);print(text,flush=True)
def capture(name):
 settle();p=OUT/name;assert w.grab().save(str(p),'PNG');captures.append(dict(file=name,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),resolution=[w.width(),w.height()]))
def row_index(ident):
 return next(i for i in range(work.queue.count()) if work.queue.item(i).data(Qt.UserRole)==ident)
def slider_for(view,ident):
 item=next(view.item(i) for i in range(view.count()) if view.item(i).data(Qt.UserRole)==ident)
 return view.itemWidget(item).findChild(QSlider)
w.resize(1920,1200);w.show();settle();panel=w.operations_panel
assert w.console_pages.currentWidget() is w.shell2.face  # 0.5: Stacy is the first thing on the right; this check then asks for Activity itself
w.shell2.show_operations_face();settle()
assert w.console_pages.currentWidget() is panel and w.shell2.operations_button.isChecked()
assert w.shell2.top.pulse.parentWidget() is w.operations_monitors
# UI-03: the monitors' holder stands in the head immediately left of Nice; the original Stop is the first row of Nice, not a second control.
assert w.operations_monitors is w.shell2.top.pulse_holder and w.operations_monitors.isVisible() and w.shell2.top.programs.isVisible() and not w.master_stop_button.isVisible()
record('Operations is a persistent right-column view; the original monitors stay in the head beside Nice and the original Stop is the first row of Nice (UI-03)')
project=call('projects.create',{'title':'A power supply worth understanding','intent':'Keep assumptions, calculations and evidence connected to this project.'})
idea=call('ideas.capture',{'project':project['id'],'text':'Can the power budget hold during the busiest frame?'})
source=root/'Files/power.txt';source.parent.mkdir(exist_ok=True);source.write_text('Declared source fixture.\n')
first=call('agenda.add',{'title':'Inspect the saved power model','program':'@files:power.txt','nice':'normal'})
dependent=call('agenda.add',{'title':'Compare the declared limits','program':'@files:power.txt','when':{'after':first['id']},'nice':'normal'})
idle=call('agenda.add',{'title':'Read reference notes while idle','program':'@files:power.txt','nice':'background'})
for ident,state,nice in [('c'*32,'Queued',8),('d'*32,'Running',5)]:
 k.save('jobs',dict(id=ident,owner='desktop-owner',state=state,tool='lab.python',cpu_nice=nice))
w.cabinet_page.refresh(force=True);w.cabinet_page.select('idea:'+idea['id'],reveal=True);room=w.cabinet_page.open('idea:'+idea['id']);settle()
w.shell2.show_operations_face();panel.refresh();settle();assert panel.model['selection']['id']=='idea:'+idea['id']
assert idea['text'] in panel.selection.text();record('Right-column selection follows the original cabinet identity')
# D1-fix: Activity is quiet; the work list (its rows, sliders, Earlier / Later and Stop) is the System menu's list, opened from the
# symbol at the upper right (Activity's Work list word opens the same list). Activity says what runs and waits in one line.
assert panel.jobs.words().startswith('WORK · 1 running · 4 queued'),panel.jobs.words()  # the Running job; the Queued job and the three Agenda items wait
panel.work_list.click();settle();work=w.shell2.top.nice.popup;assert work is not None and work.isVisible() and not work.embedded
assert work.queue.count()==3 and work.running.count()==2
waiting=next(r for r in panel.model['agenda']['next'] if r.get('id')==dependent['id'])
assert any('After Inspect' in reason for reason in waiting['schedule_checks']['reasons'])
item=work.queue.item(row_index(dependent['id']));assert 'After Inspect' in ' '.join(label.text() for label in work.queue.itemWidget(item).findChildren(__import__('PySide6.QtWidgets',fromlist=['QLabel']).QLabel))
record('Queue rows show actual dependency and idle waits without running work')
cpu=slider_for(work.running,'c'*32);assert cpu.value()==8 and cpu.isEnabled()
assert not slider_for(work.running,'d'*32).isEnabled()
shown=next(r for r in panel.model['agenda']['now'] if r['id']=='d'*32);assert shown['cpu_nice'] is None and shown['cpu_priority_basis']=='UNVERIFIED_PROCESS'
record('Queued CPU priority is a next-start request; an unverified running process has no claimed live value')
cpu.setFocus();QTest.keyClick(cpu,Qt.Key_Right);QTest.qWait(400);settle();panel.refresh();work.refresh()
assert k.record('jobs','c'*32)['cpu_nice']==9;priority.assert_not_called()
assert 'next worker start' in work.note.text();record('Keyboard CPU slider persists the next-start request through jobs.nice without changing a process')
work.queue.setCurrentRow(row_index(dependent['id']));QTest.mouseClick(work.earlier,Qt.LeftButton);settle();panel.refresh();work.refresh()
assert work.queue.item(0).data(Qt.UserRole)==dependent['id']
assert panel.model['first_queue_checks_passed']==first['id'];record('Accessible Earlier commits queue order while the dependency keeps the moved row from passing checks')
tier=slider_for(work.queue,idle['id']);tier.setFocus();QTest.keyClick(tier,Qt.Key_Left);QTest.qWait(400);settle();panel.refresh();work.refresh()
assert next(r for r in panel.model['agenda']['next'] if r.get('id')==idle['id'])['nice']=='normal';priority.assert_not_called()
record('Agenda tier slider changes scheduling eligibility independently of CPU nice')
metrics=w.shell2.top.pulse;metrics.timer.stop()
base=host_observations.snapshot();base['cpu']['counters']=[10,100];metrics.previous=None;metrics.render(base);assert metrics.values['CPU'].text()=='—'
base['cpu']['counters']=[20,140];metrics.render(base);assert metrics.values['CPU'].text()=='25%'
base['cpu']['counters']=None;metrics.render(base);assert metrics.values['CPU'].text()=='—'
assert metrics.values['TXT'].text()=='—';metrics.refresh();metrics.timer.start()
QTest.qWait(2100);settle()
record('CPU requires valid increasing samples and clears on failure; TXT never substitutes declared capacity for occupancy')
capture('Ledger_Slate_HATCH_Operations_01_Queue.png')
w.shell2.show_context_face();settle();assert w.arc_inspector.heading.text()=='Cabinet selection'
assert idea['text'] in w.arc_inspector.body.toPlainText() and idea['id'] in w.arc_inspector.body.toPlainText()
assert 'Object Glass' not in w.arc_inspector.heading.text();record('Context shows the selected saved record rather than a previous Object Glass file')
capture('Ledger_Slate_HATCH_Operations_01_Context.png')
w.shell2.show_slate_face();settle();assert w.console_pages.currentWidget() is w.shell2.face
assert w.operations_monitors.isVisible();w.shell2.show_operations_face();settle();record('Operations, Context and Slate remain reachable while host monitors stay visible')
editor=w.open_document(source);editor.appendPlainText('Unsaved review words.');settle();w.shell2.show_operations_face();panel.refresh()
assert editor.document().isModified() and source.read_text()=='Declared source fixture.\n'
record('Operation refresh and face switching preserve an edited document and its original bytes')
stop=[]
def saw_stop():stop.append(True)
w.a_master_stop.triggered.connect(saw_stop)
with patch.object(w.master_stop_controller,'request',return_value=True):
 # Inspect the connection identity without stopping fixture records or any process.
 assert w.master_stop_button.accessibleName()=='Master stop: stop or kill all Graphite operations'
 assert w.a_master_stop.shortcuts()
record('Original master Stop action, controller and shortcut remain connected; no stop was invoked')
w.resize(1366,768);settle();assert w.trash_can.isVisible() and w.shell2.top.programs.isVisible() and w.operations_monitors.isVisible()
assert w.shell2.top.pulse.parentWidget() is w.operations_monitors
capture('Ledger_Slate_HATCH_Operations_01_Compact.png');record('Compact layout retains fixed Trash, the host monitors in the head, Nice (which holds Stop) and a scrollable operations workspace')
assert w.type_bar.box.placeholderText()=='prompt';assert call('ideas.get',{'id':idea['id']})==idea
record('Poem and original record content remain intact')
editor.document().setModified(False)
for ident in ('c'*32,'d'*32):
 row=k.record('jobs',ident);row['state']='Cancelled';k.save('jobs',row)
w.close();app.processEvents();assert not w.desktop_lease.exists();offline.assert_not_called();priority.assert_not_called();offline.stop();priority.stop()
record('Clean close removes the lease; fixture records created no native process, provider request or tool job')
report=dict(state='PASSED',mode='ACTUAL_QT_OFFSCREEN',checks=checks,captures=captures,fixture_job_records=2,jobs_submitted=0,native_invocations=0,model_calls=0,provider_requests=0,os_priority_changes=0,
 native_acceptance=False,owner_ui_review='DEFERRED_UNTIL_COHESIVE_UI')
(OUT/'operations-ui.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
