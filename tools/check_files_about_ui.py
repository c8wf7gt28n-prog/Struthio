"""Actual Qt check of the second assignment (HATCH AGENT-02, WI-C, files about something), offscreen.

The mechanical steps: a disposable Office workspace whose Files folder holds three files about pellets (one by name in a
subfolder, one by name as a table, one by its words), one about the coop roof and a copy in Egress, and whose Ingress folder
holds an invoice named for pellets, a receipt that is not, and a scan with the word only inside it. With no page open (no tab
at all), "find files about pellets" is typed to Slate in the typing strip with key events; Slate answers "Working on it"; the
request became an assignment of the profile files_about with context {} (its own words chose it: no model); two driver steps
by hand show the Work lines (working on · running, doing now · listing Ingress); the driver then works it to DONE between
events (where, find, the Ingress listing, two reads, the rule default "write the findings page", the page and its lines);
the found line carries the summary; the Document word on the inspect line opens the findings page in Documents, whose
paragraphs are the request, one line per match and "Looked in Files and Ingress on <date> · 5 matches · read 2"; at 1366 by
768 the page and the right column stay visible. Captures at 1920×1200 and 1366×768. Disposable profile and Concern;
Kernel.launch, Kernel.submit and the provider request are held; no process may start; no model runs (brain.status is not
READY, so the one choice takes the rule default and the record says so). Every read is inside Files except the Ingress
listing, which reads names only; nothing in Ingress is opened. Nothing here is owner-host, live-model or physical acceptance.
"""
import hashlib,json,os,re,subprocess,sys,tempfile,time
from pathlib import Path
from unittest.mock import patch
PROGRAM=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('ARC_LEDGER_FILES_ABOUT_CAPTURE_DIR',str(PROGRAM/'build/ui_checks/files_about')));OUT.mkdir(parents=True,exist_ok=True)
RUN=Path(tempfile.mkdtemp(prefix='ledger-agent02-files-about-ui-'))
os.environ.update(QT_QPA_PLATFORM='offscreen',ARC_LEDGER_EMBEDDED='1',ARC_LEDGER_DISABLE_BOOK_WATCHER='1',
 ARC1_WORKBENCH_CONFIG_HOME=str(RUN/'profile'),ARC_LEDGER_CONCERN=str(RUN/'Concern'))
os.environ.pop('ARC_LEDGER_XSESSION',None)
sys.path.insert(0,str(PROGRAM));sys.dont_write_bytecode=True
from PySide6.QtCore import Qt,QProcess
from PySide6.QtWidgets import QMessageBox
from PySide6.QtTest import QTest
from workbench.qt_app import make_app,WorkbenchWindow
from workbench import locations,clip,files_service,profile_files
from workbench.document_qt import DocumentsTab
from workbench.engineering_kernel import Kernel,operator
from workbench.session import Session
from workbench.shell2 import Bubble
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
checks=[];captures=[]
REQUEST='find files about pellets'
ALLOWED={'receiving.status','files.find','ledger.browse','files.get','documents.create','documents.edit'}
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
def wait_for(predicate,limit_ms=10000,step=60):
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
 from html import unescape
 return unescape(re.sub(r'<[^>]+>','',html))
def five_parts(window):
 parts=(window.nav_dock,window.ribbon_dock,window.central_stack,window.sim_dock,getattr(window,'type_dock',None))
 return all(p is not None and p.isVisible() for p in parts) and window.trash_can.isVisible() and window.shell2.top.nice.isVisible()
def type_request(window,text,hold=False):
 bar=window.type_bar;bar.set_target('slate');box=bar.box;box.clear();box.setFocus();settle(window)
 QTest.keyClicks(box,text);settle(window);QTest.keyClick(box,Qt.Key_Return)
 if hold:window.agent_driver.timer.stop()
 settle(window,80)
def put(rel,text,days=0):
 path=files/rel;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
 if days:stamp=time.time()-days*86400;os.utime(path,(stamp,stamp))
# the disposable workspace's Files and Ingress
files=files_service.root(k);ingress=root/'Ingress';assert ingress.is_dir() and files==root/'Files',(files,ingress)
put('Coop/pellet_order.md','# Pellet order for November\nTwo bags of layer pellets from the mill.\n')
put('feed notes.txt','Grit and oyster shell on Sundays.\nPellets: 12.5 kg a week.\n',days=3)
put('pellet price.csv','supplier,kg,price\nMill,25,19.50\n')
put('Coop/roof.txt','The coop roof needs new felt.\n')
put('Egress/pellets_share.txt','A copy sent to the neighbour.\n')
(ingress/'Pellets invoice.pdf').write_bytes(b'%PDF-1.4 invoice');(ingress/'grit receipt.pdf').write_bytes(b'%PDF-1.4 receipt')
(ingress/'scan.txt').write_text('pellets pellets pellets\n')
w.resize(1920,1200);w.show();settle(w);bridge.timer.stop();w.type_bar.hatch.lifecycle.timer.stop()
with k.db() as db:jobs_before=db.execute('SELECT count(*) FROM jobs').fetchone()[0]
face=w.shell2.face;driver=w.agent_driver
# 01 · nothing open: no tab, no page; the driver exists with nothing running; the Work block is quiet
assert w.tabs.count()==0 and w.tabs.currentWidget() is None,(w.tabs.count(),w.tabs.currentWidget())
assert driver is not None and driver.running()==[] and not driver.timer.isActive() and face.work.isHidden() and five_parts(w)
assert call('agent.list')['assignments']==[] and call('documents.list')['documents']==[]
assert call('brain.status')['state']!='READY'
check('01 No page open (no tab at all); the agent driver exists with nothing running; the Work block is hidden; no document exists; no model is loaded; five parts visible')
# 02 · the request typed to Slate in the strip becomes an assignment with context {}; Slate says Working on it
type_request(w,REQUEST,hold=True)
said=last_said(face);assert said.startswith('Working on it: '+REQUEST),said
assert len(driver.running())==1 and not driver.timer.isActive();first=driver.running()[0]
row=status(first);assert (row['state'],row['profile'],row['steps_used'])==('READY','files_about',0),row
with k.db() as db:stored_context=json.loads(db.execute('SELECT context FROM agent_assignments WHERE id=?',(first,)).fetchone()[0])
assert stored_context=={},stored_context
assert w.tabs.count()==0   # still no page: the request needed none
check('02 Typing strip → Slate with key events: “%s” became assignment %s of profile files_about with context {} (its own words chose it, no model); Slate said “%s”'%(REQUEST,first[:8],said[:60]))
# 03 · two driver steps by hand: the Work lines read working on · running and doing now · listing Ingress
driver.tick();driver.tick();face.work.refresh();settle(w)
row=status(first);assert row['state']=='RUNNING' and row['steps_used']==2,row
assert face.work.current['id']==first and not face.work.isHidden()
working=plain(line(face,'working_on'));doing=plain(line(face,'doing_now'))
assert REQUEST in working and 'running' in working and 'Listing Ingress by name' in doing and 'step 3 of 5' in doing,(working,doing)
assert 'Stop' in line(face,'inspect') and 'Pause' in line(face,'inspect') and 'Investigation' in line(face,'inspect')
assert w.console_pages.currentWidget() is face and five_parts(w)
check('03 After two driver steps (receiving.status, files.find) the Work block reads working on · %s · running and doing now · %s; Stop and Pause are words on the inspect line'%(REQUEST,doing.split(' · ',1)[1]))
w.shell2.show_operations_face();settle(w)  # HATCH DESK D1b: the Work block is in the right pane's Activity
capture(w,'Ledger_Slate_AGENT_02_FilesAbout_01_Running_1920.png','Files about pellets, running after two steps with no page open: the Work block in the right column\'s Activity with Stop and Pause')
# 04 · the driver works it to DONE between events
driver.timer.start()
assert wait_for(lambda:status(first)['state']=='DONE',12000),status(first)
assert driver.running()==[] and not driver.timer.isActive()
row=status(first);assert row['reason']=='Found 5 files about pellets; the findings page is in Documents' and row['model_used'] is False,row
assert row['steps_used']==12,row['steps_used']
found=[f['text'] for f in row['found']];assert found[-1]=='5 files about pellets: 4 in Files, 1 waiting in Ingress; Graphite read the first lines of 2.',found
assert row['needs_you']==[] and [i['kind'] for i in row['inspect']]==['investigation','document'],row
assert wait_for(lambda:'Graphite read the first lines of 2' in plain(line(face,'found')) and 'done' in plain(line(face,'working_on')),5000),(line(face,'found'),line(face,'working_on'))
with k.db() as db:
 steps=[(r[0],json.loads(r[1]),r[2]) for r in db.execute('SELECT kind,program,outcome FROM inv_steps WHERE investigation=? ORDER BY seq',(row['investigation'],))]
programs=[p for kind,p,_ in steps if kind=='STEP'];choices=[(kind,o) for kind,_,o in steps if kind in ('CHOICE','MODEL_CHOICE')]
operations=[p['operation'] for p in programs]
assert set(operations)<=ALLOWED and operations[:6]==['receiving.status','files.find','ledger.browse','files.get','files.get','documents.create'] and operations[6:]==['documents.edit']*6,operations
assert choices==[('CHOICE','DONE')],choices
reads=[p['arguments']['path'] for p in programs if p['operation']=='files.get'];assert reads==['Coop/pellet_order.md','pellet price.csv'],reads
for rel in reads:assert files.resolve() in (files/rel).resolve().parents
browsed=[p['arguments']['path'] for p in programs if p['operation']=='ledger.browse'];assert browsed==[str(ingress)],browsed
check('04 The driver worked it to DONE between events: %d steps (receiving.status, files.find, ledger.browse on Ingress only, files.get ×2 inside Files, documents.create, documents.edit ×6), one CHOICE row (no model: the rule default, write the page); found · “%s”'%(len(programs),found[-1]))
capture(w,'Ledger_Slate_AGENT_02_FilesAbout_02_Done_1920.png','Files about pellets, done: the found line with the summary and the inspect line with Investigation and Document')
# 05 · the Document word on the inspect line opens the findings page in Documents
document=row['inspect'][1]['id'];key='i%d'%next(n for n,i in enumerate(row['inspect']) if i['kind']=='document')   # the WorkBlock's word for that inspect entry
face.work.refresh();settle(w);assert 'Document' in plain(line(face,'inspect'))
face.work.lines['inspect'].linkActivated.emit(key);settle(w,80)
assert wait_for(lambda:isinstance(w.tabs.currentWidget(),DocumentsTab) and w.tabs.currentWidget().document_id==document,5000),w.tabs.currentWidget()
tab=w.tabs.currentWidget();doc=call('documents.get',{'id':document})['document'];texts=[b['text'] for b in doc['blocks']]
assert doc['title']=='Files about pellets' and doc['revision']==7 and len(texts)==7,(doc['title'],doc['revision'],texts)
assert texts[0]=='Request: “find files about pellets” · Graphite searched Files for “pellet”',texts[0]
assert texts[1].startswith('pellet_order.md · Files › Coop · ') and texts[1].endswith('first line: “# Pellet order for November”'),texts[1]
assert texts[2].startswith('pellet price.csv · Files · ') and texts[2].endswith('matched by name · Table · columns supplier, kg, price · 1 row'),texts[2]
assert texts[3].startswith('feed notes.txt · Files · ') and 'matched on line 2: Pellets: 12.5 kg a week.' in texts[3],texts[3]
assert texts[4].startswith('pellets_share.txt · Files › Egress · '),texts[4]
assert texts[5].startswith('Pellets invoice.pdf · Ingress · ') and texts[5].endswith('waiting to be received, not read'),texts[5]
assert re.match(r'^Looked in Files and Ingress on \d{4}-\d{2}-\d{2} · 5 matches · read 2$',texts[6]),texts[6]
assert not any(word in ' '.join(texts) for word in ('roof','grit receipt','scan.txt')),texts
shown=tab.page.toPlainText().split('\n');assert shown==texts,(shown,texts)
assert tab.revision==7 and not tab.dirty and five_parts(w)
check('05 The Document word on the inspect line opened the findings page “%s” in Documents (revision 7): the request, four lines for Files (best first, the Egress copy last), one for Ingress (“waiting to be received, not read”) and “%s”; roof.txt, the receipt and the scan are not on it'%(doc['title'],texts[6]))
capture(w,'Ledger_Slate_AGENT_02_FilesAbout_03_Page_1920.png','The findings page opened from the inspect line: one paragraph per match and the last line saying where Slate looked')
# 06 · 1366 by 768: the page and the right column stay visible
w.resize(1366,768);settle(w,60);face.work.refresh();settle(w)
assert five_parts(w) and tab.page.isVisible() and not face.work.isHidden()
check('06 1366×768: the findings page, the Work block and the five parts stay visible')
capture(w,'Ledger_Slate_AGENT_02_FilesAbout_04_Compact_1366.png','The findings page and the right column at 1366 by 768')
# 07 · counters and records
with k.db() as db:jobs_after=db.execute('SELECT count(*) FROM jobs').fetchone()[0]
assert jobs_after==jobs_before and not launcher.called and not submission.called and not provider.called and not popen.called and not detached.called
brain=call('brain.status');assert brain['state']!='READY'
assert all(r['model_used'] is False for r in call('agent.status')['assignments'])
assert [d['id'] for d in call('documents.list')['documents']]==[document]
check('07 Zero jobs, launches, provider requests or processes; no model (%s); model_used False; the one document in the workspace is the findings page'%brain['state'])
report=dict(schema='ledger.agent02-files-about-ui/1',checkpoint='HATCH AGENT-02 WI-C',state='PASSED',mode='ACTUAL_QT_OFFSCREEN',checks=checks,captures=captures,
 request=REQUEST,typed_with_no_page_open=True,assignment={'id':first,**{k2:status(first)[k2] for k2 in ('profile','state','steps_used','reason')}},
 context_at_assign=stored_context,operations=operations,reads=reads,browsed=browsed,choices=[{'kind':c[0],'outcome':c[1]} for c in choices],
 findings_page={'id':document,'title':doc['title'],'revision':doc['revision'],'paragraphs':texts},found=found,
 model_used=False,basis='LOCAL_STEPS_NO_MODEL',brain_state=brain['state'],profile_module='workbench/profile_files.py',read_limit=profile_files.READ_LIMIT,
 real_job_submissions=0,worker_processes_started=0,model_generations=0,provider_requests=0,native_invocations=0,processes_started=0,
 acceptance_claimed=False,note='Mechanical offscreen evidence of the files-about assignment typed with no page open, worked by the desktop driver without a model, and its findings page opened from the inspect line; the live-model advice (read one more or write) and the owner display remain open.')
w.close();app.processEvents()
(OUT/'files-about-ui.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(dict(state=report['state'],checks=len(checks),captures=len(captures),document=document)))
