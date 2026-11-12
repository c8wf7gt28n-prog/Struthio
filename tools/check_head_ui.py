"""Actual Qt check of the Ledger Head by the owner's request (HATCH AGENT-01, UI-03), offscreen.

The mechanical steps: the four monitors (CPU · GPU · RAM · TXT) stand in the head immediately left of the Nice word with
explicit unavailable readings; there is no separate Stop in the head; Enter (and Space) on Nice opens its popup with the
kill switch "■ Stop everything" as the first row and focused, Escape closes it and focus returns to Nice; three Agenda
items made with agenda.add appear as queued rows, each with a horizontal niceness slider (left more urgent, right nicer,
the value in words); one keyboard step on a slider goes through agenda.nice and is read back through agenda.view (nothing
patched); Earlier reorders through agenda.reorder and agenda.view shows the new order; the menu button is taller than the
other strip words, it is the unlabeled cat named Open menu (GRAPHITE-01; graphite and paper pixels counted) and the left
floor is the row's own arithmetic; captures at 1920 by 1200 and 1366 by 768 with the popup open and closed; last, the kill switch row runs the
real Master Stop path with zero jobs: the controller's confirm dialog is a QMessageBox with a Stop all button, answered by
pressing that button (QMessageBox.exec patched for that one dialog; QMessageBox.question patched to Yes for any other
prompt), and the controller's stop thread runs to its report. Disposable profile and Concern; Kernel.launch, Kernel.submit
and the provider request are held; after the window exists no process, shell command or detached program may start (on
Linux the stop path reads /proc, so it starts none). session_power.system, the one session and power function, is held for
the whole run (D2-fix): logind answers that there is no login session on any computer and no command may start. Nothing here
is owner-host or physical acceptance.

HATCH DESK D1a: the Nice word gave way to the single erased Graphite symbol at the far right of the head, named System menu
(desktop_header_qt.SystemButton, still host.shell2.top.nice). The monitors stand immediately left of it; the strip's height is
the desk's band height and both panes are one width. HATCH DESK D2: the symbol opens the System menu (system_menu_qt): Game
first and focused from the keyboard, Stop all jobs directly beneath (the kill switch, its row now), then the process list (the
same queued rows, sliders, Earlier and Later, each queued row's place number at its left); the cat (pale paper on the band,
graphite eyes and paws) is named Open programs and opens the programs list. Every step above runs on that menu.
"""
import hashlib,json,os,subprocess,sys,tempfile,time
from pathlib import Path
from unittest.mock import patch
PROGRAM=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('ARC_LEDGER_HEAD_CAPTURE_DIR',str(PROGRAM/'build/ui_checks/head')));OUT.mkdir(parents=True,exist_ok=True)
RUN=Path(tempfile.mkdtemp(prefix='ledger-agent01-head-ui-'))
# A 1920 by 1200 offscreen screen (the plugin's default is 800 by 800), so the popup under Nice is on the screen at both sizes.
SCREEN=RUN/'screen.json';SCREEN.write_text(json.dumps({'screens':[{'name':'review','x':0,'y':0,'width':1920,'height':1200,'logicalDpi':96,'logicalBaseDpi':96,'dpr':1.0}]}))
os.environ.update(QT_QPA_PLATFORM='offscreen:configfile='+str(SCREEN),ARC_LEDGER_EMBEDDED='1',ARC_LEDGER_DISABLE_BOOK_WATCHER='1',
 ARC1_WORKBENCH_CONFIG_HOME=str(RUN/'profile'),ARC_LEDGER_CONCERN=str(RUN/'Concern'))
os.environ.pop('ARC_LEDGER_XSESSION',None)
sys.path.insert(0,str(PROGRAM));sys.dont_write_bytecode=True
from PySide6.QtCore import Qt,QPoint,QProcess
from PySide6.QtGui import QPainter,QImage
from PySide6.QtWidgets import QApplication,QMessageBox,QLabel,QSlider,QAbstractButton
from PySide6.QtTest import QTest
from workbench.qt_app import make_app,WorkbenchWindow
from workbench import locations,clip,typebar_qt
from workbench.desktop_header_qt import KILL_WORDS,MONITORS_NOTE,TIERS,tier_words
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
w=WorkbenchWindow(root,session,restore=False);k=w.ledger_bridge.kernel;bridge=w.ledger_bridge;bar=w.type_bar;hatch=bar.hatch
import platform;platform.processor()  # the one host probe Python answers through a process, answered before the guards
popen=patch.object(subprocess,'Popen',side_effect=AssertionError('No process start')).start()
system=patch.object(os,'system',side_effect=AssertionError('No shell command')).start()
detached=patch.object(QProcess,'startDetached',side_effect=AssertionError('No detached program')).start()
checks=[];captures=[];observations={};PREFIX='Ledger_Slate_AGENT_01_Head_'
def settle(ms=25):
 for name in ('agenda_runner','study_idle'):
  obj=getattr(w,name,None)
  if obj and hasattr(obj,'timer'):obj.timer.stop()
 for _ in range(2):app.processEvents();QTest.qWait(ms)
def check(text):checks.append(text);print(text,flush=True)
def call(op,args=None):
 value=k.dispatch(op,args or {},operator());assert value['ok'],value;return value['result']
def rect(widget):
 p=widget.mapTo(w,widget.rect().topLeft());return [p.x(),p.y(),widget.width(),widget.height()]
def inside(outer,inner):return outer[0]<=inner[0] and outer[1]<=inner[1] and inner[0]+inner[2]<=outer[0]+outer[2] and inner[1]+inner[3]<=outer[1]+outer[3]
def capture(name,note,*popups):
 w.operations_panel.refresh();settle();pix=w.grab();mode='ACTUAL_QT_WINDOW_GRAB';painter=QPainter(pix)
 for popup in popups:
  assert popup.isVisible();pos=w.mapFromGlobal(popup.mapToGlobal(QPoint(0,0)));assert pos.x()>=0 and pos.y()>=0,(name,pos)
  painter.drawPixmap(pos,popup.grab());mode='ACTUAL_QT_WINDOW_AND_VISIBLE_POPUP_GRABS'
 painter.end();target=OUT/(PREFIX+name);assert pix.save(str(target),'PNG')
 captures.append(dict(file=PREFIX+name,note=note,mode=mode,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),resolution=[w.width(),w.height()]))
def align(times=3):
 for _ in range(times):bar.align();settle()
def five_parts():
 parts=(w.nav_dock,w.ribbon_dock,w.central_stack,w.sim_dock,getattr(w,'type_dock',None))
 return all(p is not None and p.isVisible() for p in parts) and w.trash_can.isVisible() and w.shell2.top.nice.isVisible() and w.operations_monitors.isVisible()
def row_widget(view,ident):return next(view.itemWidget(view.item(i)) for i in range(view.count()) if view.item(i).data(Qt.UserRole)==ident)
def row_index(view,ident):return next(i for i in range(view.count()) if view.item(i).data(Qt.UserRole)==ident)
def queue_order():return [r['id'] for r in call('agenda.view')['next'] if r.get('kind')!='job']
def cat_pixels(image):
 """HATCH DESK D2: the cat's graphite details (#504d46: its eyes at rest, paws' outline and toes) and its coat (#fffdf8, the
 workspace's warm paper white, brighter than the band's lettering)."""
 ink=paper=0
 for y in range(image.height()):
  for x in range(image.width()):
   c=image.pixelColor(x,y)
   if abs(c.red()-0x50)<14 and abs(c.green()-0x4d)<14 and abs(c.blue()-0x46)<14:ink+=1
   if c.red()>=0xfc and c.green()>=0xfa and c.blue()>=0xf4:paper+=1
 return ink,paper
w.resize(1920,1200);w.show();settle(120);bridge.timer.stop();hatch.lifecycle.timer.stop();align();w.activateWindow();settle()
top=w.shell2.top;nice=top.nice;pulse=top.pulse;holder=top.pulse_holder
with k.db() as db:jobs_before=db.execute('SELECT count(*) FROM jobs').fetchone()[0]
# 01 · the four monitors in the head immediately left of Nice; explicit unavailable readings; no separate Stop ---------------
head=rect(w.ribbon_dock);ph=rect(holder);nh=rect(nice)
assert holder.isVisible() and pulse.isVisible() and w.operations_monitors is holder and holder.toolTip()==MONITORS_NOTE and pulse.toolTip()==MONITORS_NOTE
assert inside(head,ph) and inside(head,nh) and ph[0]+ph[2]<=nh[0] and nh[0]-(ph[0]+ph[2])<=24,(head,ph,nh)
assert list(pulse.values)==['CPU','GPU','RAM','TXT'] and all(pulse.values[key].isVisible() and pulse.labels[key].text()==key for key in pulse.values)
readings={key:pulse.values[key].text() for key in pulse.values};tips={key:pulse.values[key].toolTip() for key in pulse.values}
assert all(value=='—' or value.endswith('%') for value in readings.values()),readings
assert readings['TXT']=='—' and 'does not publish' in tips['TXT'],tips['TXT']  # the context monitor says why it has no number
assert all(('unavailable' in tips[key] or 'does not publish' in tips[key]) for key,value in readings.items() if value=='—'),tips  # a dash always says why
assert not w.master_stop_button.isVisible() and w.master_stop_button.accessibleName()=='Master stop: stop or kill all Graphite operations'
assert [b for b in w.ribbon_dock.findChildren(QAbstractButton) if b.isVisible() and 'stop' in b.text().lower()]==[],'no separate Stop in the head'
assert nice.isVisible() and nice.text()=='' and nice.accessibleName()==nice.toolTip()=='System menu' and type(nice).__name__=='SystemButton'
assert five_parts()
observations['head']=dict(head=head,monitors=ph,nice=nh,readings=readings,tooltips=tips)
capture('01_Nice_Closed_1920.png','The head at 1920 by 1200: CPU · GPU · RAM · TXT immediately left of the erased Graphite symbol, the System menu (unavailable readings are the explicit dash, the reason in the tooltip); no separate Stop; the cat at the left of the lower band.')
check('01 The four monitors stand in the head immediately left of the System menu\'s symbol (%d px gap) with explicit unavailable readings (%s); no separate Stop in the head; the five parts are visible'%(nh[0]-(ph[0]+ph[2]),', '.join('%s %s'%(key,value) for key,value in readings.items())))
# 02 · Enter on Nice opens the popup with the kill switch first and focused; Escape closes it ---------------------------------
nice.setFocus();settle();assert app.focusWidget() is nice,type(app.focusWidget()).__name__
QTest.keyClick(nice,Qt.Key_Return);settle(60);popup=nice.popup
assert popup is not None and popup.isVisible() and popup.items()[0] is popup.game and popup.items()[1] is popup.kill,'Game first, the kill switch directly beneath (D2)'
assert app.focusWidget() is popup.game and popup.game.hasFocus(),type(app.focusWidget()).__name__
QTest.keyClick(popup.game,Qt.Key_Down);settle();assert app.focusWidget() is popup.kill,'one Down reaches Stop all jobs'
assert popup.kill.text()==KILL_WORDS=='Stop all jobs' and popup.kill.width()>=popup.width()-30 and popup.kill.isEnabled() and popup.kill.caption=='work Graphite manages'
assert 'Ctrl+Shift+F12' in popup.kill.toolTip() and 'Stop advice' in popup.kill.toolTip(),popup.kill.toolTip()  # the controller's own detail
assert not hasattr(popup,'stop') or popup.stop is popup.kill,'one Stop, not two'
assert popup.running_label.words().startswith('ACTIVE JOBS') and 'as they started' in popup.running_label.words() and 'order they started' in popup.running_label.toolTip()  # QuietWords: its words as plain text (the note is the script)
observations['popup']=dict(position=[popup.x(),popup.y()],size=[popup.width(),popup.height()],kill=rect(popup.kill) if False else [popup.kill.x(),popup.kill.y(),popup.kill.width(),popup.kill.height()])
capture('02_Nice_Open_1920.png','The System menu opened with the Return key (D2): Game first, Stop all jobs directly beneath (the kill switch, here under the keyboard after one Down), scoped to the work Graphite manages; Nothing queued yet; active jobs keep the order they started in.',popup)
QTest.keyClick(popup.kill,Qt.Key_Escape);settle(60);assert not popup.isVisible();focus_after=app.focusWidget() is nice
QTest.keyClick(nice,Qt.Key_Space);settle(60);assert popup.isVisible() and app.focusWidget() is popup.game,'Space opens it too'
QTest.keyClick(popup.game,Qt.Key_Escape);settle(60);assert not popup.isVisible()
observations['popup']['focus_returns_to_nice']=focus_after
check('02 Enter and Space on the System menu\'s symbol open it with Game first and focused and the kill switch (%s) directly beneath, one Down away; Escape closes it (focus back on the symbol: %s)'%(KILL_WORDS,focus_after))
# 03 · three Agenda items: queued rows each with a slider; a keyboard step goes through agenda.nice; Earlier through agenda.reorder
items=[call('agenda.add',{'title':title,'program':'@files:head.txt','nice':tier}) for title,tier in
 (('Inspect the head notes','normal'),('Compare the monitor words','normal'),('Read reference notes while idle','background'))]
nice.open();settle(100);assert popup.isVisible() and popup.queue.count()==3,popup.queue.count()
sliders={popup.queue.item(i).data(Qt.UserRole):popup.queue.itemWidget(popup.queue.item(i)).findChild(QSlider) for i in range(3)}
assert set(sliders)=={item['id'] for item in items}
assert all(s.isVisible() and s.isEnabled() and s.orientation()==Qt.Horizontal and (s.minimum(),s.maximum())==(0,2) for s in sliders.values())
idle=items[2]['id'];assert sliders[idle].value()==2 and sliders[items[0]['id']].value()==1 and sliders[items[1]['id']].value()==1
words={ident:[label.text() for label in row_widget(popup.queue,ident).findChildren(QLabel)] for ident in sliders}
assert any(text.endswith(tier_words('background')) for text in words[idle]) and any(text.endswith(tier_words('normal')) for text in words[items[0]['id']]),words
assert 'left more urgent, right nicer' in sliders[idle].accessibleName()
assert popup.running.count()==1 and popup.running.item(0).text()=='No active jobs'
tier=sliders[idle];tier.setFocus();settle();QTest.keyClick(tier,Qt.Key_Left);QTest.qWait(450);settle(60)
shown=next(r for r in call('agenda.view')['next'] if r.get('id')==idle);assert shown['nice']=='normal',shown['nice']
assert 'Agenda scheduling tier saved' in popup.note.text(),popup.note.text()
settle(60);assert row_widget(popup.queue,idle).findChild(QSlider).value()==TIERS.index('normal'),'the popup re-read the truth'
before=queue_order();assert before==[items[0]['id'],items[1]['id'],idle],before
popup.queue.setCurrentRow(row_index(popup.queue,items[1]['id']));settle();assert popup.earlier.isEnabled()
QTest.mouseClick(popup.earlier,Qt.LeftButton);settle(80)
after=queue_order();assert after==[items[1]['id'],items[0]['id'],idle],(before,after)
assert [popup.queue.item(i).data(Qt.UserRole) for i in range(3)]==after,'the rows follow agenda.view'
assert 'Agenda order saved' in popup.note.text(),popup.note.text()
observations['agenda']=dict(items=[item['id'] for item in items],order_before=before,order_after=after,row_words=words)
check('03 Three agenda.add items appear as queued rows each with a horizontal slider in words; one keyboard step put %s through agenda.nice (read back by agenda.view); Earlier moved %s first through agenda.reorder (read back by agenda.view)'%(tier_words('normal'),items[1]['title']))
popup.hide();settle()
# 04 · the menu button: taller than the strip words, the cat (GRAPHITE-01), the floor from the row ---------------------------
(lp,ls),(rp,rs)=bar.rows();assert bar.explore.isHidden(),'D1a: Explore left the strip';strip_words=[w.console.sizes[i] for i in (0,1,2)]+rp+rs
assert hatch.height()>max(b.height() for b in strip_words) and hatch.height()>=hatch.sizeHint().height(),(hatch.height(),[b.height() for b in strip_words],hatch.sizeHint().height())
assert hatch.iconSize().height()==typebar_qt.hatch_icon_px(1.0)==44 and hatch.text()=='' and hatch.accessibleName()==hatch.toolTip()=='Open programs'
assert bar.height()==w.desk.band==w.ribbon_dock.height() and hatch.height()==w.desk.band,'D1a: the strip is the desk\'s band, as tall as the head'
assert 'border:0' in hatch.styleSheet() and 'background:transparent' in hatch.styleSheet(),'no border and no wash: the cat paints itself'
image=hatch.grab().toImage();ink,eyes=cat_pixels(image)
assert ink>=60 and eyes>=600,(ink,eyes,image.width(),image.height())  # D2: a pale coat with graphite details
assert image.save(str(OUT/(PREFIX+'05_Hatch_Tile.png')),'PNG')
captures.append(dict(file=PREFIX+'05_Hatch_Tile.png',note='The cat alone at 44 px (D2: pale paper on the band, graphite eyes and paws, a pink nose and ears; GRAPHITE-01\'s graphite cat and the owner\'s egg before it).',mode='ACTUAL_QT_WIDGET_GRAB',sha256=hashlib.sha256((OUT/(PREFIX+'05_Hatch_Tile.png')).read_bytes()).hexdigest(),resolution=[image.width(),image.height()]))
floors=bar.floors();need=bar.row_need(lp,ls)
assert floors==[w.desk.pane]*2==[w.nav_dock.width(),w.sim_dock.width()] and need<w.desk.pane,(floors,need,w.desk)  # D1a: one width for both panes; the left slot's words fit it
from workbench import graphite_brand
assert all(b.width()>=b.sizeHint().width() and b.text()==bar.words.get(b,b.text()) for b in ls+rp+rs) and all(0<=l and r<=hatch.width() for l,_,r,_ in (graphite_brand.cat_ink(hatch.tile(),p) for p in graphite_brand.POSES.values())),'every strip word whole at 14 pt; the cat\'s button holds every pose (D1-fix)'
menu=hatch.programs;hatch.open_list(False);settle();assert menu.isVisible() and hatch.property('menuOpen') is True and hatch.cat.pose=='open'
menu.close_menu();settle();assert hatch.property('menuOpen') is False
observations['tile']=dict(hatch=rect(hatch),icon=[hatch.iconSize().width(),hatch.iconSize().height()],strip_height=bar.height(),strip_words=[b.height() for b in strip_words],cat_pixels=dict(graphite=ink,eye_paper=eyes,of=image.width()*image.height()),left_row_need=need,floors=floors,pane=w.desk.pane)
check('04 The cat\'s button (%d px, the band\'s height) is taller than every strip word (%d px at most) with the cat at 44 px (%d graphite detail and %d paper coat pixels); both panes are the desk\'s one width %d and the left slot\'s words (%d px) fit it whole; the menuOpen property follows the open programs list'%(hatch.height(),max(b.height() for b in strip_words),ink,eyes,floors[0],need))
# 05 · compact: 1366 by 768 with the popup closed and open --------------------------------------------------------------------
w.resize(1366,768);settle(60);align();head=rect(w.ribbon_dock);ph=rect(holder);nh=rect(nice)
assert five_parts() and inside(head,ph) and inside(head,nh) and ph[0]+ph[2]<=nh[0] and w.tabs.width()>=600,(head,ph,nh,w.tabs.width())
assert all(pulse.values[key].width()>=pulse.values[key].fontMetrics().horizontalAdvance(pulse.values[key].text()) for key in pulse.values),'the readings keep their width'
assert all(pulse.labels[key].text()==key for key in pulse.labels),'the key words are whole at 1366'
visible={b.text().replace('&',''):[b.width(),b.visibleRegion().boundingRect().width()] for b in w.command_menus.values()};assert all(width==shown for width,shown in visible.values()),visible
capture('03_Nice_Closed_1366.png','1366 by 768: the monitors keep their readings beside the System menu\'s symbol, every command word whole, the centre at least 600 px, the cat at the left of the lower band.')
nice.open(True);settle(100);assert popup.isVisible() and app.focusWidget() is popup.game and popup.queue.count()==3
capture('04_Nice_Open_1366.png','1366 by 768 with the System menu open (D2): Game, Stop all jobs, the three queued rows with their place numbers and sliders and Earlier / Later under them; the rest of the menu scrolls into view.',popup)
popup.hide();settle();observations['compact']=dict(head=head,monitors=ph,nice=nh,centre=w.tabs.width(),columns=[w.nav_dock.width(),w.sim_dock.width()])
w.resize(1920,1200);settle(60);align()
check('05 At 1366 by 768 the monitors stay readable beside the System menu\'s symbol, the command words stay whole and the list opens with the rows; the five parts stay')
# 06 · the kill switch runs the real Master Stop with zero jobs (last: the stop holds new work) ---------------------------------
controller=w.master_stop_controller;assert k.listing('jobs')==[] and not controller.running
def confirm(box):
 """The controller's own confirm dialog (a QMessageBox with Stop all and Cancel): press Stop all, as the owner would."""
 for button in box.buttons():
  if button.text()=='Stop all':button.click();return 0
 raise AssertionError('The Master Stop confirm dialog did not offer Stop all')
with patch.object(QMessageBox,'exec',confirm):
 nice.open(True);settle(60);assert app.focusWidget() is popup.game;QTest.keyClick(popup.game,Qt.Key_Down);settle();assert app.focusWidget() is popup.kill
 QTest.keyClick(popup.kill,Qt.Key_Space);settle(60)
assert not popup.isVisible() and controller.running,'the kill switch started the Master Stop'
began=time.monotonic()
while controller.last_report is None and time.monotonic()-began<30:app.processEvents();QTest.qWait(50)
report=controller.last_report;assert report is not None,'the stop thread did not report'
assert report['result']=='STOPPED' and report['cancel_requested']==[] and report['jobs_pending']==[] and report['errors']==[],report
assert (root/'.ledger/master-stop/latest.json').is_file() and json.loads((root/'.ledger/master-stop/latest.json').read_text())['result']=='STOPPED'
from workbench.work_trail import work_status
assert work_status(k)['held'],'the stop holds new work, as before'
settle(60);assert not controller.running and popup.kill.text()==KILL_WORDS and 'held' in popup.kill.toolTip(),popup.kill.toolTip()
popen.assert_not_called();system.assert_not_called();detached.assert_not_called();launcher.assert_not_called();submission.assert_not_called();provider.assert_not_called()
assert held_logind.call_count>0 and all(c.args[0][0]=='logind' for c in held_logind.call_args_list),'D2-fix: each opening read availability through the held function only'
observations['master_stop']=dict(result=report['result'],cancel_requested=report['cancel_requested'],sessions_closed=report['sessions_closed'],process_results=report['process_results'],unverified=report['unverified'],seconds=round(time.monotonic()-began,2))
check('06 The kill switch ran the existing Master Stop: its confirm dialog (Stop all pressed), its stop thread, a %s report with zero jobs to cancel and zero processes, and the work hold; no process, shell command, job, worker, model or provider request'%report['result'])
# 07 · clean close -------------------------------------------------------------------------------------------------------------
with k.db() as db:jobs_after=db.execute('SELECT count(*) FROM jobs').fetchone()[0]
assert jobs_after==jobs_before==0
assert w.close() is True;settle();assert not w.desktop_lease.exists()
check('07 Zero job records; clean close removed the lease')
result=dict(schema='ledger.agent01-head-ui/1',checkpoint='HATCH AGENT-01',work_item='UI-03',state='PASSED',mode='ACTUAL_QT_OFFSCREEN',checks=checks,captures=captures,observations=observations,
 decisions=dict(kill_switch='first row of Nice, full width, eraser pink, bound to the existing Master Stop action (same confirm dialog, stop thread and Ctrl+Shift+F12); the controller\'s own button stays hidden; no separate Stop in the head',
  slider_mapping='active jobs: Linux CPU nice 0 … 19 left to right through jobs.nice, said in words (normal · a little nicer · nicer · much nicer · nicest); queued items: the Agenda tiers now → normal → background left to right through agenda.nice; active jobs are not reorderable (no operation) and the note says so',
  tile_size='the cat 44 px high at 14 pt (GRAPHITE-01; the egg until then), scaled with the interface size up to 1.4, painted; the strip follows its tallest item; the left floor is the row\'s own arithmetic'),
 jobs_submitted=0,worker_processes_started=0,model_generations=0,provider_requests=0,native_invocations=0,processes_started=0,os_power_or_logout_commands=0,
 master_stop_confirm='QMessageBox.exec patched for the controller\'s own dialog to press its Stop all button; the stop thread ran unpatched',
 owner_host_acceptance=False,acceptance_claimed=False,clean_close=True)
(OUT/'head-ui.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(dict(state=result['state'],checks=len(checks),captures=len(captures),master_stop=observations['master_stop']['result']),ensure_ascii=False),flush=True)
for guard in (question,detached,system,popen,submission,launcher,provider):guard.stop()
