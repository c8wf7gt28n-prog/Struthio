"""Actual Qt check of work that continues while Ledger is closed (HATCH AGENT-02 WI-A), offscreen.

The mechanical steps: the setting agent.continue_when_closed is listed (Slate ▸ Assignments, default on); open Documents
through the Hatch catalogue route, type a paragraph with three quantities, type "add up the numbers on this page" to Slate;
one desktop step takes the lease, so a service step is refused (ASSIGNMENT_DRIVEN_BY_DESKTOP) and agent_loop.pump skips it;
close the window as a window attached to the Ledger service would (ledger_bridge.kernel.is_host_client patched True for the
close only): the assignment is released, not paused (RUNNING, driver None); a new window sees agent_loop.pump (the function
the service's 5 s tick calls, run in-process here) take a step: the Work block's doing-now line reads "in the Ledger service
· …"; pump finishes it (DONE, the total paragraph on the page, the sheet's steps say driver service); Today in the new
window says "While Ledger was closed, Slate took N steps on “…” · now done" and its button opens the investigation sheet;
with the setting off, closing pauses as before ("Ledger closed"); with it on again, a released assignment is taken back by
a reopened window (AgentDriver.adopt, the function the window's single-shot calls when attached to the service): the
desktop's step takes the lease, pump skips it, and the desktop runs it to DONE. Captures at 1920×1200 and 1366×768.

Disposable profile and Concern; Kernel.launch, Kernel.submit and the provider request are held; no process may start; the
real resident process is exercised by tools/check_continue_service.py, not here. No model runs. Nothing here is owner-host,
live-model or physical acceptance.
"""
import hashlib,json,os,subprocess,sys,tempfile,time
from pathlib import Path
from unittest.mock import patch
PROGRAM=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('ARC_LEDGER_CONTINUE_CAPTURE_DIR',str(PROGRAM/'build/ui_checks/continue')));OUT.mkdir(parents=True,exist_ok=True)
RUN=Path(tempfile.mkdtemp(prefix='ledger-agent02-continue-ui-'))
os.environ.update(QT_QPA_PLATFORM='offscreen',ARC_LEDGER_EMBEDDED='1',ARC_LEDGER_DISABLE_BOOK_WATCHER='1',
 ARC1_WORKBENCH_CONFIG_HOME=str(RUN/'profile'),ARC_LEDGER_CONCERN=str(RUN/'Concern'))
os.environ.pop('ARC_LEDGER_XSESSION',None)
sys.path.insert(0,str(PROGRAM));sys.dont_write_bytecode=True
from PySide6.QtCore import Qt,QProcess
from PySide6.QtWidgets import QLabel,QMessageBox,QPushButton,QScrollArea
from PySide6.QtTest import QTest
from workbench.qt_app import make_app,WorkbenchWindow
from workbench import locations,clip,agent_loop,agent_qt
from workbench.document_qt import DocumentsTab
from workbench.engineering_kernel import Kernel,operator
from workbench.investigations_qt import InvestigationTab
from workbench.session import Session
from workbench.shell2 import Bubble,TodayPage
from workbench.explore_qt import open_instrument
from workbench.shell2 import open_destination
provider=patch.object(clip,'_request',side_effect=AssertionError('No provider request')).start()
launcher=patch.object(Kernel,'launch',side_effect=AssertionError('No worker launch')).start()
submission=patch.object(Kernel,'submit',side_effect=AssertionError('No job submission')).start()
question=patch.object(QMessageBox,'question',return_value=QMessageBox.Yes).start()
app=make_app([]);root=locations.office(RUN/'workspace')
def window(width,height):
 win=WorkbenchWindow(root,Session(RUN/'profile/session.json',root),restore=False)
 win.resize(width,height);win.show();settle(win);win.ledger_bridge.timer.stop();win.type_bar.hatch.lifecycle.timer.stop();return win
def settle(win,ms=30):
 for name in ('agenda_runner','study_idle'):
  obj=getattr(win,name,None)
  if obj and hasattr(obj,'timer'):obj.timer.stop()
 for _ in range(3):app.processEvents();QTest.qWait(ms)
w=WorkbenchWindow(root,Session(RUN/'profile/session.json',root),restore=False);k=w.ledger_bridge.kernel
import platform;platform.processor()
popen=patch.object(subprocess,'Popen',side_effect=AssertionError('No process start')).start()
system=patch.object(os,'system',side_effect=AssertionError('No shell command')).start()
detached=patch.object(QProcess,'startDetached',side_effect=AssertionError('No detached program')).start()
checks=[];captures=[]
REQUEST='add up the numbers on this page'
PARAGRAPH='Pellets 12.5 kg, grit 3 kg and oyster shell 0.5 kg this week.'
KEY=agent_loop.SETTING
def check(text):checks.append(text);print(text,flush=True)
def call(op,args=None):
 value=k.dispatch(op,args or {},operator());assert value['ok'],value;return value['result']
def capture(win,name,note):
 win.operations_panel.refresh();settle(win);pix=win.grab();target=OUT/name;assert pix.save(str(target),'PNG')
 captures.append(dict(file=name,note=note,mode='ACTUAL_QT_WINDOW_GRAB',sha256=hashlib.sha256(target.read_bytes()).hexdigest(),resolution=[win.width(),win.height()]))
def status(ident):return call('agent.status',{'id':ident})['assignments'][0]
def stored(ident):return call('documents.get',{'id':ident})['document']
def wait_for(predicate,limit_ms=8000,step=60):
 began=time.monotonic()
 while time.monotonic()-began<limit_ms/1000:
  app.processEvents();QTest.qWait(step)
  if predicate():return True
 return bool(predicate())
def last_said(face):
 for i in range(face.lines.count()-1,-1,-1):
  widget=face.lines.itemAt(i).widget()
  if widget is None:continue
  bubble=widget if isinstance(widget,Bubble) else widget.findChild(Bubble)
  if bubble is not None:return bubble.text.property('plain') or bubble.text.text()
 return ''
def plain(html):
 import re
 from html import unescape
 return unescape(re.sub(r'<[^>]+>','',html))
def line(face,key):return plain(face.work.lines[key].text())
def five_parts(win):
 parts=(win.nav_dock,win.ribbon_dock,win.central_stack,win.sim_dock,getattr(win,'type_dock',None))
 return all(p is not None and p.isVisible() for p in parts) and win.trash_can.isVisible() and win.shell2.top.programs.isVisible()
def type_request(win,text):
 """Type to Slate in the strip and press Return; the driver's timer is stopped before any event is pumped, so the check steps by hand."""
 bar=win.type_bar;bar.set_target('slate');box=bar.box;box.clear();box.setFocus();settle(win)
 QTest.keyClicks(box,text);settle(win);QTest.keyClick(box,Qt.Key_Return);win.agent_driver.timer.stop();settle(win,80)
 assert last_said(win.shell2.face).startswith('Working on it: '+text),last_said(win.shell2.face)
 return win.agent_driver.running()[-1]
def quiet(win):
 face=win.shell2.face
 for timer in (face.agenda_timer,face.work.timer,face.related.timer,win.shell2.timer,win.agent_driver.timer):timer.stop()
def close_attached(win):
 """Close as a window attached to the Ledger service would: is_host_client is True on its Kernel for the close only."""
 quiet(win)
 with patch.object(win.ledger_bridge.kernel,'is_host_client',True,create=True):
  words=win.agent_driver.close_words();assert win.close()
 app.processEvents();assert win._closing and win.agent_driver.running()==[]
 return words
def set_setting(value):
 row=next(r for r in call('ledger.settings')['settings'] if r['key']==KEY)
 call('ledger.settings.set',{'key':KEY,'value':value,'expected_revision':row['revision']})
 assert agent_loop.continue_when_closed(k) is value
def steps_by(investigation):
 with k.db() as db:rows=db.execute("SELECT inputs FROM inv_steps WHERE investigation=? AND kind='STEP' ORDER BY seq",(investigation,)).fetchall()
 return [json.loads(r[0]).get('driver','desktop') for r in rows]

w.resize(1920,1200);w.show();settle(w);w.ledger_bridge.timer.stop();w.type_bar.hatch.lifecycle.timer.stop()
with k.db() as db:jobs_before=db.execute('SELECT count(*) FROM jobs').fetchone()[0]
# 01 · the setting is listed under Slate ▸ Assignments, on by default, read by both consumers
row=next(r for r in call('ledger.settings')['settings'] if r['key']==KEY)
assert (row['label'],row['stored'],row['default'],row['root'],row['group'],row['scope_id'],row['requires_owner'])==('Continue assignments while Graphite is closed',True,True,'Slate','Assignments','project_private',True),row
assert 'setting:'+KEY in w.settings_navigator.items and agent_loop.continue_when_closed(k) is True and agent_qt.continue_setting(w) is True
check('01 Setting “%s” (%s) is listed under Slate ▸ Assignments, project private, owner only, default on; the service reads it from the Kernel settings row and the window through ledger.settings.effective'%(row['label'],KEY))
# 02 · a page with three quantities; the request becomes an assignment; one desktop step takes the lease
entry=next(r for r in call('ledger.explore',{'kind':'INSTRUMENT'})['instruments'] if r['id']=='instrument:documents')
tab=open_instrument(w,entry);settle(w);assert isinstance(tab,DocumentsTab) and tab.document_id,tab
doc=tab.document_id;tab.page.setFocus();settle(w);QTest.keyClicks(tab.page,PARAGRAPH);settle(w);assert tab.flush() and stored(doc)['blocks'][0]['text']==PARAGRAPH
first=type_request(w,REQUEST);w.agent_driver.tick();w.shell2.face.work.refresh();settle(w)
row=status(first);assert (row['state'],row['driver'],row['lease_live'],row['steps_used'],row['service_steps'])==('RUNNING','desktop',True,1,0),row
refused=k.dispatch('agent.step',{'id':first,'driver':'service'},operator());assert not refused['ok'] and 'ASSIGNMENT_DRIVEN_BY_DESKTOP' in refused['error']['message'],refused
assert agent_loop.pump(k)==[] and status(first)['steps_used']==1
assert 'in the Graphite service' not in line(w.shell2.face,'doing_now') and 'running' in line(w.shell2.face,'working_on')
check('02 “%s” typed to Slate became assignment %s; one desktop step took the lease (driver desktop, lease live); a service step was refused (%s) and pump skipped it'%(REQUEST,first[:8],refused['error']['message'].split(':')[0]))
capture(w,'Ledger_Slate_AGENT_02_Continue_01_Desktop_1920.png','The assignment running under this window (one step), before Ledger closes')
# 03 · closing as a window attached to the Ledger service, with the setting on, releases instead of pausing
words=close_attached(w)
row=status(first);assert words=='release' and (row['state'],row['driver'],row['lease_live'],row['paused_reason'])==('RUNNING',None,False,None),row
assert w.agent_driver.handed=={'reason':'Graphite closed · the Graphite service continues','ids':[first]},w.agent_driver.handed
check('03 Closing the window (attached to the Ledger service, setting on) released the assignment instead of pausing it: RUNNING, driver None, no lease; the driver handed over [%s] with “%s”'%(first[:8],w.agent_driver.handed['reason']))
# 04 · a new window; the service's pump takes one step: the Work block says it happens in the Ledger service
w2=window(1920,1200);face2=w2.shell2.face
assert agent_qt.hosted(w2) is False and w2.agent_driver.adopt()==[]   # an in-process window does not take work back (no service there)
touched=agent_loop.pump(k);assert [(t['id'],t['state'],t['step']['driver']) for t in touched]==[(first,'RUNNING','service')],touched
row=status(first);assert (row['driver'],row['lease_live'],row['service_steps'],row['steps_used'])==('service',True,1,2),row
open_destination(w2,'documents:'+doc);w2.shell2.show_slate_face();settle(w2);face2.work.refresh();settle(w2)
assert w2.console_pages.currentWidget() is face2 and not face2.work.isHidden()
doing=line(face2,'doing_now');assert doing.startswith('Doing now · in the Graphite service · '),doing
check('04 A new window: pump (the function the service’s 5 s tick calls) took step 2 as driver service; the Work block reads “%s”'%doing)
w2.shell2.show_operations_face();settle(w2)  # HATCH DESK D1b: the Work block is in the right pane's Activity
capture(w2,'Ledger_Slate_AGENT_02_Continue_02_InService_1920.png','The Work block (the right column\'s Activity) while the Ledger service holds the lease: doing now · in the Ledger service · …')
# 05 · pump finishes it: DONE, the total on the page, the sheet's steps say driver service
for _ in range(10):
 if status(first)['state']!='RUNNING':break
 agent_loop.pump(k)
row=status(first);assert (row['state'],row['service_steps'],row['steps_used'],row['driver'])==('DONE',4,5,'service'),row
page=stored(doc);assert page['blocks'][-1]['text'].startswith('Total of the 3 quantities on this page: 16 kg'),page['blocks']
assert steps_by(row['investigation'])==['desktop','service','service','service','service']
sheet=call('investigation.sheet',{'id':row['investigation']});assert [json.loads(s['inputs']).get('driver') for s in sheet['attempted']][1:]==['service']*4
tab2=w2.tabs.currentWidget();assert isinstance(tab2,DocumentsTab) and tab2.document_id==doc
assert wait_for(lambda:(face2.work.refresh(),'16 kg' in tab2.page.toPlainText())[1],5000),tab2.page.toPlainText()
check('05 pump ran it to DONE: 5 steps (1 desktop, 4 service), “%s…” on the page (revision %d); the investigation sheet’s attempted steps carry driver service'%(page['blocks'][-1]['text'][:44],page['revision']))
# 06 · Today in the new window says what Slate did while Ledger was closed; its button opens the sheet
w2.resize(1366,768);w2.shell2.show_slate_face();w2.show_start();today=w2._empty_home_page.today;assert isinstance(today,TodayPage);today.fill();settle(w2)
rows=[r for r in today.also_waiting() if r[0].startswith('While Graphite was closed')]
expected='While Graphite was closed, it took 4 steps on “%s” · now done'%REQUEST
assert len(rows)==1 and rows[0][0]==expected and rows[0][1]=='inspect',rows
# Today draws a non-resume row as a flat button (shell2 TodayPage.fill); with the proposed wrapping sentence it is a label whose word is inspect
button=next((b for b in today.waiting.findChildren(QPushButton) if b.text()==expected),None)
label=next((l for l in today.waiting.findChildren(QLabel) if 'inspect' in getattr(l,'_actions',{}) and expected in plain(l.text())),None)
assert button is not None or label is not None
scroller=today.findChild(QScrollArea);scroller.ensureWidgetVisible(today.waiting,0,40);scroller.horizontalScrollBar().setValue(0);settle(w2)
assert five_parts(w2) and today.isVisible() and today.waiting.isVisible()
check('06 Today (1366×768) lists “%s” with the word inspect'%expected)
capture(w2,'Ledger_Slate_AGENT_02_Continue_03_Today_1366.png','Today after reopening: what Slate did in the Ledger service while Ledger was closed, with inspect')
(button.click() if button is not None else label.linkActivated.emit('inspect'));settle(w2)
sheet_tab=w2.tabs.currentWidget();assert isinstance(sheet_tab,InvestigationTab) and sheet_tab.ident==row['investigation'],sheet_tab
check('07 The Today row’s button opened the investigation sheet %s in Investigations'%row['investigation'][:8])
# 08 · with the setting off, closing pauses as before
set_setting(False);assert agent_qt.continue_setting(w2) is False
open_destination(w2,'documents:'+doc);settle(w2);second=type_request(w2,REQUEST);w2.agent_driver.tick()
assert status(second)['state']=='RUNNING'
words=close_attached(w2);row=status(second)
assert words=='pause' and (row['state'],row['paused_reason'],row['service_steps'])==('PAUSED','Graphite closed',0),row
assert agent_loop.pump(k)==[]
check('08 With the setting off, closing the attached window paused the assignment as in AGENT-01 (PAUSED “Graphite closed”); pump does nothing')
# 09 · setting on again: a released assignment is taken back by a reopened window (the desktop has priority)
set_setting(True)
w3=window(1920,1200);open_destination(w3,'documents:'+doc);settle(w3);third=type_request(w3,REQUEST);w3.agent_driver.tick()
assert close_attached(w3)=='release' and status(third)['driver'] is None
agent_loop.pump(k);row=status(third);assert (row['driver'],row['service_steps'],row['steps_used'])==('service',1,2),row
w4=window(1366,768);face4=w4.shell2.face;driver4=w4.agent_driver
with patch.object(w4.ledger_bridge.kernel,'is_host_client',True,create=True):taken=driver4.adopt()
assert taken==[third] and driver4.running()==[third],(taken,driver4.running())
driver4.timer.stop();driver4.tick();row=status(third)
assert (row['driver'],row['lease_live'],row['steps_used'],row['service_steps'])==('desktop',True,3,1),row
assert agent_loop.pump(k)==[] and status(third)['steps_used']==3   # the service leaves it to the window
open_destination(w4,'documents:'+doc);w4.shell2.show_slate_face();settle(w4);face4.work.refresh();settle(w4)
assert w4.console_pages.currentWidget() is face4 and face4.work.current['id']==third and 'running' in line(face4,'working_on')
assert line(face4,'doing_now').startswith('Doing now · ') and 'in the Graphite service' not in line(face4,'doing_now') and five_parts(w4)
check('09 A reopened window took the released assignment back (adopt → %s): its step took the desktop lease and pump left it alone (steps 3, service steps 1); the Work block reads “%s” without the service prefix'%(third[:8],line(face4,'doing_now')))
w4.shell2.show_operations_face();settle(w4)
capture(w4,'Ledger_Slate_AGENT_02_Continue_04_TakenBack_1366.png','At 1366 by 768: the reopened window took the work back; the Work block (the right column\'s Activity) runs it here, without the service prefix')
driver4.timer.start();assert wait_for(lambda:status(third)['state']=='DONE',8000),status(third)
row=status(third);assert (row['state'],row['service_steps'],row['steps_used'])==('DONE',1,5) and steps_by(row['investigation'])==['desktop','service','desktop','desktop','desktop'],row
w4.show_start();today4=w4._empty_home_page.today;today4.fill();settle(w4)
mentions=[r[0] for r in today4.also_waiting() if r[0].startswith('While Graphite was closed')]
assert 'While Graphite was closed, it took 1 step on “%s” · now done'%REQUEST in mentions and expected in mentions,mentions
paused=[r for r in today4.also_waiting() if r[1]=='resume' and r[0].startswith('Graphite paused: '+REQUEST)];assert len(paused)==1,paused   # the one paused in step 08
assert five_parts(w4)
check('10 The desktop ran it to DONE (driver sequence desktop, service, desktop×3); Today lists both service mentions and the assignment paused with the setting off, with its resume word')
# 11 · counters
with k.db() as db:jobs_after=db.execute('SELECT count(*) FROM jobs').fetchone()[0]
assert jobs_after==jobs_before and not launcher.called and not submission.called and not provider.called and not popen.called and not detached.called and not system.called
brain=call('brain.status');assert brain['state']!='READY'
assert all(r['model_used'] is False for r in call('agent.status')['assignments'])
check('11 Zero jobs, launches, provider requests or processes; no model (%s); the resident process itself is exercised by tools/check_continue_service.py'%brain['state'])
report=dict(schema='ledger.agent02-continue-ui/1',checkpoint='HATCH AGENT-02 WI-A',state='PASSED',mode='ACTUAL_QT_OFFSCREEN',checks=checks,captures=captures,
 setting={'key':KEY,'default':True},document=doc,lease_seconds=agent_loop.LEASE_SECONDS,
 assignments={k2:{'id':v,**{f:status(v)[f] for f in ('state','steps_used','service_steps','driver','paused_reason')}} for k2,v in (('released_then_pumped',first),('paused_with_setting_off',second),('taken_back',third))},
 host_client='patched True on the window Kernel for the close and the adopt call only; pump ran in-process (the function the service tick calls)',
 model_used=False,real_job_submissions=0,worker_processes_started=0,model_generations=0,provider_requests=0,native_invocations=0,processes_started=0,
 acceptance_claimed=False,note='Mechanical offscreen evidence of the release-on-close, the service pump, the Today words and the take-back; the real resident process is checked by tools/check_continue_service.py.')
quiet(w4);w4.close();app.processEvents()
(OUT/'continue-ui.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(dict(state=report['state'],checks=len(checks),captures=len(captures))))
