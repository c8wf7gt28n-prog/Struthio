"""Actual Qt check of the resident agent loop (HATCH AGENT-01), offscreen: an assignment typed to Slate on a page, worked by
the driver between events, shown in the right column, bound to the page's words, paused by closing Ledger and resumed from Today.

The mechanical steps: open Documents through the Hatch catalogue route, type a paragraph with three quantities (12.5 kg,
3 kg, 0.5 kg) with key events, type "add up the numbers on this page" to Slate in the typing strip; the Work block shows
working on and doing now within a few driver ticks; the driver runs the assignment to DONE; the page shows the appended
total paragraph (16 kg) through its undo stack and the found line says so; change 3 kg to 4 kg on the page; after the
autosave the stale line appears under the page and the right column says needs you; the recheck word rewrites the total
(17 kg); a second assignment is stopped after its first step; a third is paused by closing the window ("Ledger closed");
a new window on the same profile lists it on Today with a resume word, and resuming runs it to DONE; the Related block
lists an earlier idea that shares the page's words and one is dismissed. Captures at 1920×1200 and 1366×768. Disposable
profile and Concern; Kernel.launch, Kernel.submit and the provider request are held; no process may start. No model runs:
every step is local computation or one registered operation, and the report says so. Nothing here is owner-host,
live-model or physical acceptance.
"""
import hashlib,json,os,subprocess,sys,tempfile,time
from pathlib import Path
from unittest.mock import patch
PROGRAM=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('ARC_LEDGER_AGENT_CAPTURE_DIR',str(PROGRAM/'build/ui_checks/agent')));OUT.mkdir(parents=True,exist_ok=True)
RUN=Path(tempfile.mkdtemp(prefix='ledger-agent01-agent-ui-'))
os.environ.update(QT_QPA_PLATFORM='offscreen',ARC_LEDGER_EMBEDDED='1',ARC_LEDGER_DISABLE_BOOK_WATCHER='1',
 ARC1_WORKBENCH_CONFIG_HOME=str(RUN/'profile'),ARC_LEDGER_CONCERN=str(RUN/'Concern'))
os.environ.pop('ARC_LEDGER_XSESSION',None)
sys.path.insert(0,str(PROGRAM));sys.dont_write_bytecode=True
from PySide6.QtCore import Qt,QProcess
from PySide6.QtWidgets import QLabel,QMessageBox,QScrollArea
from PySide6.QtTest import QTest
from workbench.qt_app import make_app,WorkbenchWindow
from workbench import locations,clip
from workbench.document_qt import DocumentsTab
from workbench.engineering_kernel import Kernel,operator
from workbench.session import Session
from workbench.shell2 import Bubble,TodayPage
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
REQUEST='add up the numbers on this page'
PARAGRAPH='Pellets 12.5 kg, grit 3 kg and oyster shell 0.5 kg this week.'
def settle(window,ms=30):
 for name in ('agenda_runner','study_idle'):
  obj=getattr(window,name,None)
  if obj and hasattr(obj,'timer'):obj.timer.stop()
 for _ in range(3):app.processEvents();QTest.qWait(ms)
def check(text):checks.append(text);print(text,flush=True)
def call(op,args=None):
 value=k.dispatch(op,args or {},operator());assert value['ok'],value;return value['result']
def capture(window,name,note):
 window.operations_panel.refresh();settle(window);pix=window.grab();target=OUT/name;assert pix.save(str(target),'PNG')
 captures.append(dict(file=name,note=note,mode='ACTUAL_QT_WINDOW_GRAB',sha256=hashlib.sha256(target.read_bytes()).hexdigest(),resolution=[window.width(),window.height()]))
def status(ident):return call('agent.status',{'id':ident})['assignments'][0]
def stored(ident):return call('documents.get',{'id':ident})['document']
def wait_for(predicate,limit_ms=8000,step=60):
 """Pump the event loop until the predicate holds or the bound passes: the driver ticks every 250 ms, the autosave at 1.5 s."""
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
  if bubble is not None:return bubble.text.text()
 return ''
def line(face,key):return face.work.lines[key].text()
def plain(html):
 import re
 from html import unescape
 return unescape(re.sub(r'<[^>]+>','',html))
def five_parts(window):
 parts=(window.nav_dock,window.ribbon_dock,window.central_stack,window.sim_dock,getattr(window,'type_dock',None))
 return all(p is not None and p.isVisible() for p in parts) and window.trash_can.isVisible() and window.shell2.top.programs.isVisible()
def label_with(layout,word):
 for i in range(layout.count()):
  widget=layout.itemAt(i).widget()
  if isinstance(widget,QLabel) and word in getattr(widget,'_actions',{}):return widget
 return None
def type_request(window,text,hold=False):
 """Type to Slate in the strip and press Return. With hold, the driver's timer is stopped before any event is pumped, so
 the check steps the new assignment by hand (the assignment itself is created synchronously by the Return)."""
 bar=window.type_bar;bar.set_target('slate');box=bar.box;box.clear();box.setFocus();settle(window)
 QTest.keyClicks(box,text);settle(window);QTest.keyClick(box,Qt.Key_Return)
 if hold:window.agent_driver.timer.stop()
 settle(window,80)
w.resize(1920,1200);w.show();settle(w);bridge.timer.stop();w.type_bar.hatch.lifecycle.timer.stop()
with k.db() as db:jobs_before=db.execute('SELECT count(*) FROM jobs').fetchone()[0]
face=w.shell2.face;driver=w.agent_driver
idea=call('ideas.capture',{'text':'Pellets and grit: weigh the oyster shell each week and note the kg.'})   # an earlier record that shares the page's words
# 01 · the Hatch catalogue route opens the Documents room; the driver exists and the Work block is quiet
entry=next(r for r in call('ledger.explore',{'kind':'INSTRUMENT'})['instruments'] if r['id']=='instrument:documents')
tab=open_instrument(w,entry);settle(w)
assert isinstance(tab,DocumentsTab) and w.tabs.currentWidget() is tab and tab.document_id and tab.revision==1,tab
assert driver is not None and driver.running()==[] and not driver.timer.isActive() and face.work.isHidden() and five_parts(w)
assert call('agent.list')['assignments']==[]
ident=tab.document_id
check('01 Hatch route instrument:documents opens the Documents room (revision 1); the agent driver exists with nothing running; the Work block is hidden while no assignment exists; five parts visible')
# 02 · type the paragraph with key events; the Related block finds the earlier idea 1.5 s after the page changed
tab.page.setFocus();settle(w);QTest.keyClicks(tab.page,PARAGRAPH);settle(w)
assert tab.flush() and tab.revision==2 and stored(ident)['blocks'][0]['text']==PARAGRAPH
assert wait_for(lambda:any(r['id']=='idea:'+idea['id'] for r in face.related.visible_rows()),5000),face.related.rows
row=next(r for r in face.related.visible_rows() if r['id']=='idea:'+idea['id'])
assert not face.related.isHidden() and len(row['words'])>=2 and row['kind']=='idea' and row['open']=='project_desk',row
assert 'document:'+ident not in {r['id'] for r in face.related.rows}
check('02 Typed paragraph (QTest key events) saved as revision 2; the Related block lists the earlier idea sharing %d words (%s) by word match, no model; the page itself is excluded'%(len(row['words']),', '.join(row['words'][:4])))
# 03 · the request typed to Slate in the strip becomes an assignment; the Work block shows working on and doing now within two ticks
type_request(w,REQUEST,hold=True)
said=last_said(face);assert said.startswith('Working on it: '+REQUEST),said
assert len(driver.running())==1 and not driver.timer.isActive();first=driver.running()[0]
assert status(first)['state']=='READY' and status(first)['steps_used']==0
driver.tick();driver.tick();face.work.refresh();settle(w)   # two steps by hand so the running state can be seen and captured
row=status(first);assert row['state']=='RUNNING' and row['steps_used']==2 and row['profile']=='numbers_on_page',row
assert face.work.current['id']==first and not face.work.isHidden()
working=plain(line(face,'working_on'));doing=plain(line(face,'doing_now'))
assert REQUEST in working and 'running' in working and 'Adding them up' in doing and 'step 3 of 5' in doing,(working,doing)
assert 'Stop' in line(face,'inspect') and 'Pause' in line(face,'inspect') and 'Investigation' in line(face,'inspect') and 'Document' in line(face,'inspect')
assert w.console_pages.currentWidget() is face and five_parts(w)
check('03 Typing strip → Slate: “%s” became assignment %s (profile numbers_on_page) and Slate said “Working on it”; after two driver steps the Work block reads working on · %s · running and doing now · %s; Stop and Pause are words on the inspect line'%(REQUEST,first[:8],REQUEST,doing.split(' · ',1)[1]))
w.shell2.show_operations_face();settle(w)  # HATCH DESK D1b: the Work block is in the right pane's Activity
capture(w,'Ledger_Slate_AGENT_01_Work_01_Running_1920.png','Assignment running after two steps: the Work block in the right column\'s Activity with Stop and Pause; the page below the strip')
# 04 · the driver runs it to DONE between events; the page shows the appended total through its undo stack; the found line says so
driver.timer.start()
assert wait_for(lambda:status(first)['state']=='DONE',8000),status(first)
assert wait_for(lambda:'16 kg' in tab.page.toPlainText(),4000),tab.page.toPlainText()
doc=stored(ident);assert doc['revision']==3 and len(doc['blocks'])==2 and doc['blocks'][1]['text'].startswith('Total of the 3 quantities on this page: 16 kg · checked by Graphite'),doc['blocks']
assert tab.revision==3 and not tab.dirty and tab.page.document().isUndoAvailable() and tab.page.toPlainText().split('\n')[1]==doc['blocks'][1]['text']
assert driver.running()==[] and not driver.timer.isActive()
row=status(first);assert row['steps_used']==5 and row['model_used'] is False and [f['text'] for f in row['found']]==['The 3 quantities on this page total 16 kg.'],row
assert wait_for(lambda:'total 16 kg' in plain(line(face,'found')) and 'done' in plain(line(face,'working_on')),5000),(line(face,'found'),line(face,'working_on'))
with k.db() as db:recorded=db.execute('SELECT count(*) FROM inv_steps WHERE investigation=? AND kind=?',(row['investigation'],'STEP')).fetchone()[0]
assert recorded==5 and call('investigation.sheet',{'id':row['investigation']})['id']==row['investigation'],recorded
cards=call('conditions.list',{'document':ident})['conditions'];assert len(cards)==1 and cards[0]['state']=='CURRENT' and cards[0]['result']['text']=='16 kg',cards
condition=cards[0]['id'];assert any(i['kind']=='condition' and i['id']==condition for i in row['inspect'])
check('04 The driver stepped the assignment to DONE between events (5 steps, no model, %d recorded as STEP rows in the investigation); the page shows Slate’s appended paragraph “%s…” (revision 3) through its undo stack; the found line reads “%s”; one condition card CURRENT'%(recorded,doc['blocks'][1]['text'][:46],row['found'][0]['text']))
w.shell2.show_operations_face();settle(w)
capture(w,'Ledger_Slate_AGENT_01_Work_02_Done_1920.png','Assignment done: the total paragraph under the owner’s words, the found line in the right column\'s Activity')
# 05 · change 3 kg to 4 kg on the page; after the autosave the stale line appears and the right column says needs you
text=tab.page.toPlainText();at=text.index('grit 3 kg')+len('grit 3')
cursor=tab.page.textCursor();cursor.setPosition(at);tab.page.setTextCursor(cursor);tab.page.setFocus();settle(w)
QTest.keyClick(tab.page,Qt.Key_Backspace);QTest.keyClicks(tab.page,'4');assert tab.dirty and 'grit 4 kg' in tab.page.toPlainText()
assert wait_for(lambda:not tab.dirty and tab.revision==4,5000),(tab.dirty,tab.revision)   # the autosave, 1.5 s after the last key
assert not tab.stale.isHidden() and tab.stale_ids==[condition],(tab.stale.isHidden(),tab.stale_ids)
stale_words=plain(tab.stale.text());assert stale_words.startswith('A result on this page is stale') and 'recheck' in stale_words,stale_words
card=call('conditions.get',{'id':condition})['condition'];assert card['state']=='STALE' and '3 kg' in card['reason'] and '4 kg' in card['reason'],card['reason']
face.work.refresh();settle(w);needs=plain(line(face,'needs_you'))
assert 'A result on the page is stale' in needs and 'recheck' in needs and face.work.stale and face.work.stale[0]['id']==condition,needs
check('05 Changed 3 kg to 4 kg with key events; the autosave (revision 4) marked the card STALE (“%s”); the page shows “%s”; the right column’s needs-you line says the result is stale with its recheck word'%(card['reason'],stale_words))
w.shell2.show_operations_face();settle(w)
capture(w,'Ledger_Slate_AGENT_01_Work_03_Stale_1920.png','After the owner changed a number: the stale line under the page and needs you in the right column\'s Activity, each with the recheck word')
# 06 · the recheck word: the total is recomputed from the page as it is now and the paragraph rewritten, undoable
tab.stale.linkActivated.emit('recheck');settle(w,80)
doc=stored(ident);assert doc['revision']==5 and doc['blocks'][1]['text'].startswith('Total of the 3 quantities on this page: 17 kg'),doc['blocks']
assert tab.revision==5 and not tab.dirty and tab.page.toPlainText().split('\n')[1]==doc['blocks'][1]['text'] and tab.stale.isHidden() and tab.stale_ids==[]
assert tab.foot.text().startswith('Rechecked · Rechecked: the 3 quantities on this page total 17 kg'),tab.foot.text()
assert call('conditions.get',{'id':condition})['condition']['state']=='CURRENT' and tab.page.document().isUndoAvailable()
face.work.refresh();assert 'nothing' in plain(line(face,'needs_you'))
check('06 The recheck word rewrote the result paragraph to 17 kg (revision 5) on the page through its undo stack; the card is CURRENT again; the stale line is gone')
# 07 · a second assignment is stopped after its first step with the Stop word in the right column
type_request(w,REQUEST,hold=True);assert last_said(face).startswith('Working on it');second=driver.running()[0];assert second!=first
driver.tick();face.work.refresh();settle(w)
assert status(second)['state']=='RUNNING' and status(second)['steps_used']==1 and face.work.current['id']==second
face.work.lines['inspect'].linkActivated.emit('stop');settle(w)
row=status(second);assert row['state']=='STOPPED' and row['reason']=='By you: Stop' and row['steps_used']==1,row
assert driver.running()==[] and not driver.timer.isActive() and 'stopped' in plain(line(face,'working_on'))
assert next(i for i in call('investigation.list')['investigations'] if i['id']==row['investigation'])['state']=='STOPPED'
assert stored(ident)['revision']==5   # nothing was written by the stopped assignment
check('07 A second assignment was stopped after its first step with the Stop word: STOPPED “By you: Stop”, its investigation stopped, nothing written to the page')
# 08 · a third assignment is paused by closing the window
type_request(w,REQUEST,hold=True);third=driver.running()[0];driver.tick()
assert status(third)['state']=='RUNNING' and status(third)['steps_used']==1
for timer in (face.agenda_timer,face.work.timer,face.related.timer,w.shell2.timer):timer.stop()
assert w.close();app.processEvents()
row=status(third);assert row['state']=='PAUSED' and row['paused_reason']=='Graphite closed' and row['doing_now']=='Paused: Graphite closed',row
assert driver.running()==[] and w._closing
check('08 Closing the window paused the running assignment: PAUSED with reason “Graphite closed” after 1 step; nothing else stepped')
# 09 · a new window on the same profile: Today lists the paused assignment with a resume word; resuming runs it to DONE
session2=Session(RUN/'profile/session.json',root);w2=WorkbenchWindow(root,session2,restore=False)
w2.resize(1366,768);w2.show();settle(w2);w2.ledger_bridge.timer.stop();w2.type_bar.hatch.lifecycle.timer.stop()
w2.show_start();page=w2._empty_home_page.today;assert isinstance(page,TodayPage);page.fill();settle(w2)  # UI-04: the TodayPage is the Finder's first place
rows=[r for r in page.also_waiting() if r[1]=='resume'];assert len(rows)==1 and rows[0][0].startswith('Graphite paused: '+REQUEST) and 'Graphite closed' in rows[0][0],rows
label=label_with(page.waiting.body,'resume');assert label is not None and 'resume' in plain(label.text()) and 'Graphite paused' in plain(label.text()),label
scroller=page.findChild(QScrollArea);scroller.ensureWidgetVisible(page.waiting);scroller.ensureWidgetVisible(label);settle(w2)   # the Waiting card in the picture at 1366 by 768
assert five_parts(w2)
check('09 A new window on the same profile: Today’s Waiting card lists “%s” with the word resume'%rows[0][0])
capture(w2,'Ledger_Slate_AGENT_01_Today_04_Resume_1366.png','Today after reopening: the paused assignment with its resume word, at 1366 by 768')
label.linkActivated.emit('resume');settle(w2,80)
driver2=w2.agent_driver;assert third in driver2.running() or status(third)['state'] in ('RUNNING','DONE'),(driver2.running(),status(third)['state'])
assert wait_for(lambda:status(third)['state']=='DONE',8000),status(third)
tab2=w2.tabs.currentWidget();assert isinstance(tab2,DocumentsTab) and tab2.document_id==ident,tab2
assert wait_for(lambda:tab2.page.toPlainText().count('17 kg')==2,4000),tab2.page.toPlainText()
doc=stored(ident);assert doc['revision']==6 and len(doc['blocks'])==3 and doc['blocks'][2]['text'].startswith('Total of the 3 quantities on this page: 17 kg'),doc['blocks']
assert tab2.revision==6 and not tab2.dirty and w2.console_pages.currentWidget() is w2.shell2.face
face2=w2.shell2.face;assert wait_for(lambda:'total 17 kg' in plain(line(face2,'found')),5000),line(face2,'found')
assert len(call('conditions.list',{'document':ident})['conditions'])==2
check('10 The resume word brought the assignment back under the new window’s driver: RUNNING → DONE (revision 6, a second card); the page followed Slate’s paragraph and the Work block reads found · %s'%status(third)['found'][0]['text'])
# 11 · the Related block in the new window lists the earlier idea; one row is dismissed
assert wait_for(lambda:any(r['id']=='idea:'+idea['id'] for r in face2.related.visible_rows()),5000),face2.related.rows
before=len(face2.related.visible_rows());row_label=label_with(face2.related.list,'dismiss');assert row_label is not None
row_label.linkActivated.emit('dismiss');settle(w2)
dismissed=w2.session.state.get('related_dismissed') or [];assert len(dismissed)==1 and len(face2.related.visible_rows())==before-1 and dismissed[0] not in {r['id'] for r in face2.related.visible_rows()},(dismissed,before)
check('11 The Related block in the new window lists the earlier idea by shared words; its dismiss mark removed one row and the session keeps the dismissed id')
assert five_parts(w2) and tab2.page.isVisible()
capture(w2,'Ledger_Slate_AGENT_01_Work_05_Compact_1366.png','The page with two totals and the right column\'s Conversation (Related; the Work block is under Activity since HATCH DESK D1b) at 1366 by 768; all five parts visible')
check('12 1366×768: the page, the Work and Related blocks and the five parts stay visible')
# 13 · counters and records
with k.db() as db:jobs_after=db.execute('SELECT count(*) FROM jobs').fetchone()[0]
assert jobs_after==jobs_before and not launcher.called and not submission.called and not provider.called and not popen.called and not detached.called
brain=call('brain.status');assert brain['state']!='READY'
assert all(r['model_used'] is False for r in call('agent.status')['assignments'])
helpers_used={h['name']:h.get('uses',0) for h in call('helpers.list')['helpers']}
assert helpers_used.get('quantities_from_text',0)>=2,helpers_used
nodes={n['id'] for n in call('ledger.cabinet')['nodes']};assert 'document:'+ident in nodes
check('13 Zero jobs, launches, provider requests or processes; no model (%s); every assignment model_used False; the retained helper quantities_from_text records %d uses; the document is filed in the cabinet'%(brain['state'],helpers_used.get('quantities_from_text',0)))
report=dict(schema='ledger.agent01-agent-ui/1',checkpoint='HATCH AGENT-01',state='PASSED',mode='ACTUAL_QT_OFFSCREEN',checks=checks,captures=captures,
 document=ident,final_revision=stored(ident)['revision'],idea=idea['id'],condition=condition,
 assignments={'first':{'id':first,**{k2:status(first)[k2] for k2 in ('state','steps_used','reason')}},'stopped':{'id':second,**{k2:status(second)[k2] for k2 in ('state','steps_used','reason')}},
              'paused_then_resumed':{'id':third,**{k2:status(third)[k2] for k2 in ('state','steps_used','reason')}}},
 related_dismissed=dismissed,model_used=False,basis='LOCAL_STEPS_NO_MODEL',brain_state=brain['state'],helpers_used=helpers_used,
 real_job_submissions=0,worker_processes_started=0,model_generations=0,provider_requests=0,native_invocations=0,processes_started=0,
 acceptance_claimed=False,note='Mechanical offscreen evidence of the resident loop, the right column, the condition card and the pause/resume path without a model; the live-model choice path and the owner display remain open.')
w2.close();app.processEvents()
(OUT/'agent-ui.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(dict(state=report['state'],checks=len(checks),captures=len(captures),final_revision=report['final_revision'])))
