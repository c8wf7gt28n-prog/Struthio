"""HATCH DESK D4: the dynamic right-click menu in the live window, offscreen, with the owner's captures.

The owner's brief: "Show two right-click menus on different kinds of objects and demonstrate one real command or capability
running against the selected object." Every menu here is opened by a real ContextMenu event on the widget under the pointer (what
the window system sends on a right-click), so the router, the finders and the providers of workbench/context_menu.py all run:

  01  a selected passage in a document: the passage named at the top with its page and revision; Bold, the other page edits and
      Move to notes first; the equivalent command to inspect in the line; Ask Stacy; the text edits last.
  02  Bold chosen: documents.edit through Kernel.dispatch with the page's id and the revision seen at the right-click; the page
      shows the bold words and its foot the new revision (the result where it belongs); Ctrl Z takes it back.
  03  two revisions of one file selected in Files: Compare revisions first (the two actual files passed to files.compare).
  04  Compare revisions chosen: the Compare room with the two files, the older first, the change in words.
  05  a running job in the System menu's process list: the job named with its state; Inspect output, Pause, Resume, Stop by state.
      TEST DATA, labelled on the image: no job may run in a check, so its jobs are records the check writes.
  05b Pause chosen on a queued job: the Kernel pauses it at once and the System menu's list shows it waiting, paused (TEST DATA).
  06  the cabinet tree's empty place: Refresh, View as (its submenu open, the current view marked yellow), New Idea, New Project,
      Import, Export.
  07  a real network connection in Log's Network stream, read by D5's network.observe from this computer's connection table: the
      check's own loopback connection, the stream filtered to its port: Ask Stacy about this, Follow this conversation, Show
      the process, Copy address (TEST DATA, so named and labelled, only where the table cannot be read).
  08  the passage's menu at 1366 by 768: whole, inside the window.
  09  (0.8.1) Then › on a table in Files: the line panel beside the menu, its line read once (language.parse and its one source
      read); Keep rows where › unit › is mA counted from that read; Count; nothing more read while choosing.
Measured at 14, 18 and 20 pt: the menu's row height, icon column and margin are the desk menu's with the glyphs at the size they
were drawn for (context_menu.context_metrics), every row one height, every word whole (tools/ui_fit), no screen scrolls, the menu
inside the window.

0.8.1 (the owner: "right click was too complex. We need to make its power easy to use and chain/pipe. With right click icons
too"): each menu is one short shape (up to four usual rows, Then or Start from, More); the captures show that shape.

Captures go to build/graphite_desk (or ARC_LEDGER_CONTEXT_MENU_CAPTURE_DIR) at 1920 by 1200, with context-menu-ui.json beside
them. Disposable profile and Concern; Kernel.launch, Kernel.submit and the provider request are held; every session and power
call is answered as "no logind session"; after the window exists no process, shell command or detached program may start.
Nothing here is owner-host acceptance.
"""
import hashlib,json,os,subprocess,sys,tempfile,time
from pathlib import Path
from unittest.mock import patch
PROGRAM=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('ARC_LEDGER_CONTEXT_MENU_CAPTURE_DIR',str(PROGRAM/'build/graphite_desk')));OUT.mkdir(parents=True,exist_ok=True)
RUN=Path(tempfile.mkdtemp(prefix='graphite-context-menu-ui-'))
SCREEN=RUN/'screen.json';SCREEN.write_text(json.dumps({'screens':[{'name':'review','x':0,'y':0,'width':1920,'height':1200,'logicalDpi':96,'logicalBaseDpi':96,'dpr':1.0}]}))
os.environ.update(QT_QPA_PLATFORM='offscreen:configfile='+str(SCREEN),ARC_LEDGER_EMBEDDED='1',ARC_LEDGER_DISABLE_BOOK_WATCHER='1',
 ARC1_WORKBENCH_CONFIG_HOME=str(RUN/'profile'),ARC_LEDGER_CONCERN=str(RUN/'Concern'))
os.environ.pop('ARC_LEDGER_XSESSION',None)
sys.path.insert(0,str(PROGRAM));sys.path.insert(0,str(PROGRAM/'tools'));sys.dont_write_bytecode=True
import ui_fit
from PySide6.QtCore import Qt,QPoint,QProcess
from PySide6.QtGui import QContextMenuEvent,QPainter,QTextCursor
from PySide6.QtWidgets import QApplication,QMessageBox,QLabel
from PySide6.QtTest import QTest
from workbench.qt_app import make_app,WorkbenchWindow
from workbench import locations,clip,ledger_control,session_power,programs_qt,files_service
from workbench import context_menu as cm
from workbench.engineering_kernel import Kernel,operator
from workbench.session import Session
def no_logind(request):
 if request[0]=='logind':raise OSError('Caller does not belong to any known session')
 raise AssertionError('No session or power call: %r'%(request,))
provider=patch.object(clip,'_request',side_effect=AssertionError('No provider request')).start()
launcher=patch.object(Kernel,'launch',side_effect=AssertionError('No worker launch')).start()
submission=patch.object(Kernel,'submit',side_effect=AssertionError('No job submission')).start()
power=patch.object(session_power,'system',side_effect=no_logind).start()
question=patch.object(QMessageBox,'question',return_value=QMessageBox.Yes).start()
app=make_app([]);root=locations.office(RUN/'workspace');session=Session(RUN/'profile/session.json',root)
w=WorkbenchWindow(root,session,restore=False);k=w.ledger_bridge.kernel;bridge=w.ledger_bridge;bar=w.type_bar
import platform;platform.processor()  # the one host probe Python answers through a process, answered before the guards
popen=patch.object(subprocess,'Popen',side_effect=AssertionError('No process start')).start()
system=patch.object(os,'system',side_effect=AssertionError('No shell command')).start()
detached=patch.object(QProcess,'startDetached',side_effect=AssertionError('No detached program')).start()
checks=[];captures=[];measured={};dispatched=[]
def settle(ms=25):
 for name in ('agenda_runner','study_idle'):
  obj=getattr(w,name,None)
  if obj and hasattr(obj,'timer'):obj.timer.stop()
 for _ in range(3):app.processEvents();QTest.qWait(ms)
def check(text):checks.append(text);print(text,flush=True)
def call(op,args=None):
 value=k.dispatch(op,args or {},operator());assert value['ok'],value;return value['result']
def align(times=3):
 for _ in range(times):w.type_bar.align();settle()
def setting(key,value):
 row=next(r for r in ledger_control.settings(k)['settings'] if r['key']==key)
 call('ledger.settings.set',{'key':key,'value':value,'expected_revision':row['revision']});bridge.sync_profile(force=True);settle(40);align()
def ui_pt(points):setting('reading.ui_pt',float(points));settle();align(4)
# The captures whose own step's result is the status line's words (Bold, Compare revisions, the job paused); every other capture's
# status line is empty, so no capture carries an earlier step's words.
OWN_STATUS=('Graphite_Desk_D4_02_','Graphite_Desk_D4_04_','Graphite_Desk_D4_05b_')
def record(name,note,image,mode='ACTUAL_QT_WINDOW_GRAB_WITH_POPUPS'):
 status=w.statusBar().currentMessage()
 assert name.startswith(OWN_STATUS) or not status,(name,'an earlier step\'s words in the status line',status)
 target=OUT/name;assert image.save(str(target),'PNG'),name
 captures.append(dict(file=name,note=note,mode=mode,status=status,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),resolution=[image.width(),image.height()],bytes=target.stat().st_size))
superseded=[]
def supersede(*names):
 """An earlier name of a capture this check now writes under another (TEST DATA labelled, or real data): removed, so the folder
 never holds two contradictory captures of one thing."""
 for name in names:
  old=OUT/name
  if old.exists():old.unlink();superseded.append(name)
def labelled(image,words):
 """TEST DATA said on the image itself, on an eraser-pink band over the workspace's empty lower left, clear of the status line
 (as check_desk_ui labels Log's)."""
 from PySide6.QtCore import QRectF
 from PySide6.QtGui import QColor,QFont
 from workbench import shell2
 p=QPainter(image);font=QFont('IBM Plex Sans');font.setPixelSize(15);font.setWeight(QFont.DemiBold);p.setFont(font)
 width=p.fontMetrics().horizontalAdvance(words)+32;band=QRectF(390,image.height()-170,width,26)
 p.fillRect(band,QColor(shell2.ERASER));p.setPen(QColor(shell2.TEXT));p.drawText(band,Qt.AlignCenter,words);p.end();return image
def with_popups(*popups):
 """The window grab with each popup (its own window) drawn where it is: what the owner sees."""
 pix=w.grab();p=QPainter(pix)
 for popup in popups:
  if popup is not None and popup.isVisible():p.drawPixmap(w.mapFromGlobal(popup.mapToGlobal(QPoint(0,0))),popup.grab())
 p.end();return pix.toImage()
def right_click(widget,point):
 """A real ContextMenu event, as the window system sends on a right-click; the menu it opened (None if none)."""
 before=getattr(w,'context_menu',None)
 QApplication.sendEvent(widget,QContextMenuEvent(QContextMenuEvent.Mouse,point,widget.mapToGlobal(point)));settle()
 menu=getattr(w,'context_menu',None);return menu if menu is not before else None
def recorder():
 real=cm.dispatch
 def through(host,operation,arguments):dispatched.append((operation,{k_:v for k_,v in arguments.items() if k_!='selection'}));return real(host,operation,arguments)
 return patch.object(cm,'dispatch',through)
def menu_rules(menu,name):
 """The desk menu's numbers with the glyphs at their drawn size, every row one height, every word whole, no scroll, inside the window."""
 m=cm.context_metrics(w);rows=list(menu.rows_by_key.values())
 heights={r.height() for r in rows}|({menu.heading.height()} if menu.heading is not None else set());columns={r.word_x() for r in rows}
 words=ui_fit.whole_words(menu)+ui_fit.side_scrolls(menu);area=menu.bounds()
 value=dict(row=m.row,icon_col=m.icon_col,margin=m.margin,menu=[menu.m.row,menu.m.icon_col,menu.m.margin],heights=sorted(heights),word_x=sorted(columns),
            width=menu.width(),height=menu.height(),inside=area.contains(menu.geometry()),clipped=len(words))
 assert [menu.m.row,menu.m.icon_col,menu.m.margin]==[m.row,m.icon_col,m.margin],(name,value)
 assert heights=={m.row} and columns=={m.pad+m.icon_col},(name,value)
 assert not words,(name,ui_fit.describe(words))
 assert value['inside'],(name,value,area)
 assert menu.scroll.verticalScrollBar().maximum()==0,(name,'no screen scrolls')
 if menu.heading is not None:
  value['heading']=[menu.heading.shown_label(),menu.heading.shown_noun()]
  assert value['heading']==[menu.heading.label,menu.heading.noun],(name,'the target named whole',value['heading'],[menu.heading.label,menu.heading.noun])
 return value
def close(menu):
 if menu is not None:menu.close_menu(restore=False)
 settle()

w.resize(1920,1200);w.show();settle(60);bridge.timer.stop()
try:bar.hatch.lifecycle.timer.stop()
except AttributeError:pass
align(4)

# 01 a selected passage in a document ---------------------------------------------------------------------------------------------
from workbench.document_qt import show as show_document
doc=show_document(w);settle()
doc.title_box.setText('Bench notes');doc.page.setPlainText('The bench supply holds 5 V within a hair across the whole load range.\nThe ripple stays under 10 mV.');settle();doc.flush();settle()
text=doc.page.toPlainText();start=text.index('within a hair');end=start+len('within a hair')
c=doc.page.textCursor();c.setPosition(start);c.setPosition(end,QTextCursor.KeepAnchor);doc.page.setTextCursor(c);settle()
point=doc.page.cursorRect(c).center();seen=doc.revision
menu=right_click(doc.page.viewport(),point);assert menu is not None
t=menu.target;assert (t.kind,t.label,t.ident,t.revision)==('passage','“within a hair”',doc.document_id,seen),t
assert (menu.heading.label,menu.heading.noun)==('“within a hair”','passage · Bench notes'),(menu.heading.label,menu.heading.noun)
assert menu.first_keys()==['mark:bold','mark:italic','notes','ask','then','more'],menu.first_keys()
assert menu.words()[:3]==['Bold','Italic','Move to notes'],menu.words()
for key in ('inspect','ask','search','edit:copy','edit:all'):assert key in menu.keys(),key
measured['passage_1920']=menu_rules(menu,'passage 1920');measured['passage_words']=menu.words()
record('Graphite_Desk_D4_01_Passage_Right_Click_1920x1200.png','Right-click on a selected passage ("within a hair") in a document at 1920 by 1200: the passage named at the top with its page; its four usual rows, each with its glyph (Bold, Italic, Move to notes, Ask Stacy about this); Then › (the passage\'s page as a line) and More › (Underline, Plain, Paragraph style, Search, the text edits, New document, Export, in their groups).',with_popups(menu))
check('01 a selected passage: the menu names "within a hair" (passage · Bench notes), four usual rows, Then and More, %d entries in all; the menu\'s numbers (row %d px, icon column %d px)'%(len(menu.entries),measured['passage_1920']['row'],measured['passage_1920']['icon_col']))

# 02 Bold, through Kernel.dispatch with the page's id and revision --------------------------------------------------------------
with recorder():menu.row('mark:bold').click();settle(80)
last=w._context_last;assert last['ok'],last
edit=next(a for op,a in dispatched if op=='documents.edit')
assert (edit['id'],edit['expected_revision'],edit['change'],edit['origin'])==(doc.document_id,seen,{'bold':True},'HUMAN'),edit
saved=call('documents.get',{'id':doc.document_id})['document'];assert saved['revision']==seen+1 and saved['blocks'][0]['marks']==[{'start':start,'end':end,'bold':True}],saved['blocks'][0]
probe=QTextCursor(doc.page.document());probe.setPosition(start+2);assert probe.charFormat().fontWeight()>=600,'the page shows it'
assert 'revision %d'%(seen+1) in doc.foot.text(),doc.foot.text()
c=doc.page.textCursor();c.clearSelection();c.setPosition(end);doc.page.setTextCursor(c);settle()
record('Graphite_Desk_D4_02_Bold_Applied_1920x1200.png','Bold chosen from that menu: documents.edit went through Kernel.dispatch with the page\'s id and the revision seen at the right-click (%d); the page shows "within a hair" in bold and its foot says revision %d ("%s"); Ctrl Z takes it back.'%(seen,seen+1,doc.foot.text()),with_popups())
measured['bold']=dict(dispatched=edit,foot=doc.foot.text(),revision_before=seen,revision_after=saved['revision'])
check('02 Bold applied through documents.edit with id and expected_revision %d: the saved page is revision %d with the words bold, the page shows them, the foot says it'%(seen,seen+1))
# refused when the page moved after the right-click (another edit landed first)
c=doc.page.textCursor();c.setPosition(start);c.setPosition(end,QTextCursor.KeepAnchor);doc.page.setTextCursor(c);settle()
menu=right_click(doc.page.viewport(),doc.page.cursorRect(c).center());moved=menu.target.revision
call('documents.edit',{'id':doc.document_id,'expected_revision':moved,'selection':{'block':1,'start':4,'end':10,'text':'ripple'},'change':{'italic':True},'origin':'HUMAN'})
menu.row('mark:italic').click();settle(60);outcome=w._context_last
assert not outcome['ok'] and 'moved on since you right-clicked it (revision %d, now %d)'%(moved,moved+1) in outcome['words'],outcome
again=call('documents.get',{'id':doc.document_id})['document'];assert again['blocks'][0]['marks']==[{'start':start,'end':end,'bold':True}],again['blocks'][0]
measured['refused']=outcome['words']
check('02 refused when the page moved after the right-click, nothing changed: "%s"'%outcome['words'][:100])
w.statusBar().clearMessage()

# 03 two revisions of one file in Files, 04 Compare revisions ----------------------------------------------------------------------
files=files_service.root(k)
(files/'regulator rev B.txt').write_text('Output 5.0 V\nRipple 20 mV\nFoldback at 1.2 A\n');time.sleep(0.05)
(files/'regulator rev C.txt').write_text('Output 5.0 V\nRipple 10 mV\nFoldback at 1.5 A\nSoft start 2 ms\n')
(files/'bench.csv').write_text('Part,Qty\nR1,4\nC2,9\n')
from workbench.files_qt import show as show_files
tab=show_files(w);settle();tab.mode='list';tab.reload();settle();view=tab.table
def row_of(name):
 for i in range(view.topLevelItemCount()):
  it=view.topLevelItem(i)
  if it.data(0,Qt.UserRole)['name']==name:return it
 raise AssertionError(name)
view.clearSelection()
for name in ('regulator rev B.txt','regulator rev C.txt'):row_of(name).setSelected(True)
menu=right_click(view.viewport(),view.visualItemRect(row_of('regulator rev C.txt')).center());assert menu is not None
assert (menu.target.kind,len(menu.target.items))==('files',2) and menu.words()[0]=='Compare revisions',(menu.target,menu.words())
measured['two_files']=dict(words=menu.words(),rules=menu_rules(menu,'two files'))
record('Graphite_Desk_D4_03_Two_Revisions_Right_Click_1920x1200.png','Right-click on two revisions of one file selected in Files ("regulator rev B.txt" and "regulator rev C.txt"): both named at the top; Compare revisions first, then Copy to, Move to, Copy paths and, last, Delete.',with_popups(menu))
check('03 two revisions selected: the menu names both and offers Compare revisions first')
with recorder():menu.row('compare:revisions').click();settle(80)
room=w.tabs.currentWidget();assert room.title()=='Compare',room.title()
assert (room.data['before'],room.data['after'])==('regulator rev B.txt','regulator rev C.txt'),(room.data['before'],room.data['after'])
words=' '.join(l.text() for l in room.findChildren(QLabel));assert 'lines added' in words,words[:200]
record('Graphite_Desk_D4_04_Compare_Revisions_Result_1920x1200.png','Compare revisions chosen: files.compare on the two actual files (the older, rev B, before; rev C after) in the Compare room, the changed lines marked in words (added on a pencil wash, removed on an eraser wash); it is a tab you can keep open.',with_popups())
measured['compare']=dict(before=room.data['before'],after=room.data['after'],added=room.data.get('added'),removed=room.data.get('removed'))
check('04 Compare revisions ran files.compare on the two actual files: %d added, %d removed, shown in the Compare room'%(room.data.get('added',0),room.data.get('removed',0)))
w.statusBar().clearMessage();settle()  # each capture's status line says only its own step

# 05 jobs in the System menu's process list (TEST DATA: no job may run in a check, so the two jobs are records the check writes) --
JOBS_DATA='TEST DATA: two job records the check wrote (no job runs in a check: Kernel.launch and Kernel.submit are held)'
job='a'*32;queued='b'*32
k.save('jobs',dict(id=job,owner='desktop-owner',state='Running',tool='struthio.build',title='Build STRUTHIO desk mode',created=time.time()))
k.save('jobs',dict(id=queued,owner='desktop-owner',state='Queued',tool='struthio.build',title='Board checks for amp rev C',created=time.time()))
symbol=w.shell2.top.nice;sysmenu=symbol.open();settle(80);pop=sysmenu.work;pop.refresh();settle()
def job_menu(ident):
 pop.signature=None;pop.active_signature=None;pop.refresh();settle()
 item=next(pop.running.item(i) for i in range(pop.running.count()) if pop.running.item(i).data(Qt.UserRole)==ident)
 r=pop.running.visualItemRect(item);return right_click(pop.running.viewport(),QPoint(r.left()+24,r.top()+8))
menu=job_menu(job);assert menu is not None
assert (menu.target.kind,menu.target.ident,menu.target.revision)==('job',job,'Running'),menu.target
state={e.key:e.enabled for e in menu.entries if e.key in ('job:output','job:pause','job:resume','job:stop')}
assert state=={'job:output':True,'job:pause':True,'job:resume':False,'job:stop':True},state
measured['job']=dict(words=menu.words(),state=state,rules=menu_rules(menu,'job'))
assert menu.row('job:stop').caption=='asks' and menu.row('job:resume') is None,(menu.first_keys(),'Stop asks first; Resume cannot act on a running job: not at rest')
record('Graphite_Desk_D4_05_Job_Right_Click_TEST_DATA_1920x1200.png',JOBS_DATA+' (labelled on the image). Right-click on the running job in the System menu\'s process list: the job named at the top with its state (running); Inspect output, Pause, Stop (it asks first), Show in Jobs; Then › (its record as a line) and More › (Resume, dim: it is running; Copy the job id).',
       labelled(with_popups(sysmenu,menu),JOBS_DATA),'ACTUAL_QT_WINDOW_GRAB_WITH_POPUPS_ON_TEST_DATA_LABELLED')
supersede('Graphite_Desk_D4_05_Job_Right_Click_1920x1200.png')
check('05 a running job: Inspect output, Pause, Stop (asks) and Show in Jobs at rest; Resume, which cannot act on it, under More')
with recorder():menu.row('job:pause').click();settle()
assert w._context_last['ok'] and call('jobs.get',{'id':job})['pause'] is True,w._context_last
assert [op for op,_ in dispatched[-2:]]==['jobs.get','jobs.pause'],dispatched[-2:]
assert w._context_last['words'].startswith('Asked to pause · Build STRUTHIO desk mode'),w._context_last
check('05 Pause on the running job went through jobs.pause with the job\'s id after its state was read again (jobs.get): "%s"'%w._context_last['words'])
# 05b the queued job paused: the Kernel moves it to Paused at once, and the System menu's list shows it waiting, paused
menu=job_menu(queued);assert menu is not None and menu.target.revision=='Queued',menu.target
with recorder():menu.row('job:pause').click();settle()
assert w._context_last['ok'] and call('jobs.get',{'id':queued})['state']=='Paused',w._context_last
assert [op for op,_ in dispatched[-2:]]==['jobs.get','jobs.pause'],dispatched[-2:]
sysmenu=symbol.open() if not sysmenu.isVisible() else sysmenu;settle(80);pop=sysmenu.work;pop.signature=None;pop.active_signature=None;pop.refresh();settle()
assert queued not in [pop.running.item(i).data(Qt.UserRole) for i in range(pop.running.count())],'no longer an active row'
assert pop.waiting.isVisible() and 'Paused' in pop.waiting.text(),pop.waiting.text()
said=w.statusBar().currentMessage();assert said.startswith('Paused · Board checks for amp rev C · now paused'),said
record('Graphite_Desk_D4_05b_Job_Paused_TEST_DATA_1920x1200.png',JOBS_DATA+' (labelled on the image). Pause chosen on the queued job\'s right-click: jobs.pause went through Kernel.dispatch with its id after its state was read again; the Kernel paused it at once, so the System menu\'s list no longer shows it among the active rows and its WAITING lines read it paused ("%s"); the status line says "%s".'%(pop.waiting.text().replace('\n',' · '),said),
       labelled(with_popups(sysmenu),JOBS_DATA),'ACTUAL_QT_WINDOW_GRAB_WITH_POPUPS_ON_TEST_DATA_LABELLED')
measured['job_paused']=dict(waiting=pop.waiting.text(),status=said)
check('05b the queued job paused through jobs.pause: the System menu\'s list shows it waiting, paused, and the status line says so')
sysmenu.hide();w.statusBar().clearMessage();settle()  # the next captures carry no word of this one

# 06 the cabinet tree's empty place ----------------------------------------------------------------------------------------------
nav=w.settings_navigator;nav.show_view('cabinet');settle(60);page=w.cabinet_page;page.refresh(force=True);settle()
tree=page.tree;menu=right_click(tree.viewport(),QPoint(12,tree.viewport().height()-6));assert menu is not None and menu.target.kind=='tree',menu
assert menu.keys()==['refresh','view','new:idea','new:project','import','export'],menu.keys()
sub=menu.open_child(menu.row('view'));settle()
assert [(r.word,r.entry.checked) for r in sub.rows_by_key.values()]==[('Logical cabinet',not page.using_legacy),('Existing views',page.using_legacy)]
measured['tree']=dict(words=menu.words(),view_as=sub.words(),rules=menu_rules(menu,'tree'))
record('Graphite_Desk_D4_06_Cabinet_Tree_Right_Click_1920x1200.png','Right-click on the cabinet tree\'s empty place: the tree named at the top; Refresh, View as (open: Logical cabinet marked with the short yellow mark, Existing views), New Idea, New Project, Import (Ingress) and Export (Egress): the homes of the cabinet\'s old Refresh, view choices and transfers.',with_popups(menu,sub))
check('06 the cabinet tree: Refresh, View as (its current view marked), New Idea, New Project, Import, Export')
close(menu);w.statusBar().clearMessage();settle()

# 07 a real network connection in Log, read by D5's network.observe ------------------------------------------------------------
# The check holds a loopback connection open (its own sockets, nothing leaves the computer); network.observe reads it from this
# computer's connection table like any other, and the line filters the stream to its port, so no other traffic is shown. Only
# where the table cannot be read does the check fall back to its own entries, named and labelled TEST DATA.
import socket
server=socket.socket();server.bind(('127.0.0.1',0));server.listen(1);port=server.getsockname()[1]
client=socket.create_connection(('127.0.0.1',port));accepted,_=server.accept();near=client.getsockname()[1]
bar.set_target('log',focus=False);w.console.set_size(1);settle(80);log=w.log_view;log.timer.stop();log.choose('network',remember=False,read=False);settle()
bar.box.setText('port %d'%port);bar.box.setFocus();QTest.keyClick(bar.box,Qt.Key_Return);settle(60)
mine=next((log.connections.item(i) for i in range(log.connections.count()) if (log.connections.item(i).data(Qt.UserRole) or {}).get('rport')==port
           and (log.connections.item(i).data(Qt.UserRole) or {}).get('lport')==near),None)
real=mine is not None
if real:
 entry=mine.data(Qt.UserRole);assert (entry['remote'],entry['state'],entry.get('pid'))==('127.0.0.1','ESTABLISHED',os.getpid()),entry
 name='Graphite_Desk_D4_07_Network_Connection_Right_Click_1920x1200.png';other='Graphite_Desk_D4_07_Network_Connection_Right_Click_TEST_DATA_1920x1200.png'
 far='127.0.0.1:%d'%port;program=entry['process'].split()[0]
else:
 log.apply_filter('');bar.box.clear()
 log.show_connections([dict(proto='tcp',local='192.0.2.20',lport=51544,remote='198.51.100.7',rport=443,state='ESTABLISHED',process='test-browser',pid=4242)]);settle()
 mine=log.connections.item(0);entry=mine.data(Qt.UserRole)
 name='Graphite_Desk_D4_07_Network_Connection_Right_Click_TEST_DATA_1920x1200.png';other='Graphite_Desk_D4_07_Network_Connection_Right_Click_1920x1200.png'
 far='198.51.100.7:443';program='test-browser'
menu=right_click(log.connections.viewport(),log.connections.visualItemRect(mine).center());assert menu is not None
assert menu.target.kind=='connection' and menu.first_keys()==['ask','follow','process','copy:address','then'],menu.first_keys()
assert menu.target.label=='%s → %s'%(program,far) and menu.row('process').isEnabled() and menu.row('copy:address').caption==far,(menu.target,menu.row('copy:address').caption)
measured['connection']=dict(real=real,words=menu.words(),label=menu.target.label,noun=menu.target.noun,process=program,rules=menu_rules(menu,'connection'))
if real:
 record(name,'A real connection, read by D5\'s network.observe from this computer\'s connection table: the check\'s own loopback connection (127.0.0.1, port %d; nothing leaves the computer), the stream filtered to its port in the line (port %d, Enter). Right-click on it: named by who talks to whom ("%s"); Ask Stacy about this (an assignment with the connection as its context), Follow this conversation (the stream filtered to the far host and port, the entry pinned), Show the process (%s, pid %d: this check), Copy address (%s). No notes: the owner replaced them with the network.'%(port,port,menu.target.label,program,os.getpid(),far),
        with_popups(menu))
else:
 record(name,'TEST DATA (this computer\'s connection table could not be read here, so the check shows its own entry, labelled on the image): right-click on a network connection in Log\'s Network stream: Ask Stacy about this, Follow this conversation, Show the process, Copy address.',
        labelled(with_popups(menu),'TEST DATA: the check\'s own entry (the connection table could not be read here)'),'ACTUAL_QT_WINDOW_GRAB_WITH_POPUPS_ON_TEST_DATA_LABELLED')
supersede(other)
menu.row('follow').click();settle();assert bar.box.text()=='host %s port %s'%tuple(far.rsplit(':',1)) and log.pinned is not None,bar.box.text()
check('07 a %s network connection (%s): Ask Stacy about this, Follow this conversation (the filter in the line, the entry pinned), Show the process (%s), Copy address'
      %('real' if real else 'TEST DATA',menu.target.label,program))
bar.box.clear();log.unpin();log.apply_filter('');log.choose('events',remember=False,read=False);bar.set_target('slate',focus=False);w.console.set_size(0);w.statusBar().clearMessage();settle()
for s in (client,accepted,server):s.close()

# 08 the passage's menu at 1366 by 768, and the numbers at 18 and 20 pt ---------------------------------------------------------
w.tabs.setCurrentWidget(doc);settle()
def passage_menu():
 c=doc.page.textCursor();c.setPosition(start);c.setPosition(end,QTextCursor.KeepAnchor);doc.page.setTextCursor(c);settle()
 return right_click(doc.page.viewport(),doc.page.cursorRect(c).center())
w.resize(1366,768);settle(60);align(4);menu=passage_menu();assert menu is not None
measured['passage_1366']=menu_rules(menu,'passage 1366')
record('Graphite_Desk_D4_08_Passage_Right_Click_1366x768.png','The same passage\'s menu at 1366 by 768: whole, inside the window, the desk\'s row height and icon column.',with_popups(menu))
check('08 at 1366 by 768 the passage\'s menu is whole and inside the window')
close(menu);w.resize(1920,1200);settle(60);align(4)
for points in (18,20):
 ui_pt(points);menu=passage_menu();assert menu is not None;measured['passage_%dpt'%points]=menu_rules(menu,'passage %d pt'%points);close(menu)
ui_pt(14)
check('08 at 14, 18 and 20 pt the menu\'s row height, icon column and margin are the desk menu\'s with 20 px glyphs (%s)'%', '.join('%s: %s'%(key,measured[key]['menu']) for key in ('passage_1920','passage_18pt','passage_20pt')))

# 09 Then ›: the line panel on a table in Files (0.8.1) ------------------------------------------------------------------------
from workbench import boss_theme as bt
tab=show_files(w);settle();tab.mode='list';tab.reload();settle()
(files/'bench readings.csv').write_text('parameter,value,unit\nRail voltage,12,V\nSettled current,280,mA\nStartup current,650,mA\nStartup duration,110,ms\n')
tab.reload();settle();view=tab.table
item=next(view.topLevelItem(i) for i in range(view.topLevelItemCount()) if view.topLevelItem(i).data(0,Qt.UserRole)['name']=='bench readings.csv')
menu=right_click(view.viewport(),view.visualItemRect(item).center());assert menu is not None
assert menu.first_keys()==['open','ask','rename','trash','then','more'],menu.first_keys()
before=len(dispatched)
with recorder():
 panel=menu.open_child(menu.row('then'));settle(80)
 read=[op for op,_ in dispatched[before:]]
 assert isinstance(panel,cm.LinePanel) and read==['language.parse','ledger.address.read'],read
 assert panel.slab.styleSheet()==bt.line_sheet() and panel.count_words()=='4 rows · 6 steps left',panel.count_words()
 panel.choose('step:where');panel.choose('field:unit');settle()
 assert panel.row('where unit=mA').caption=='2 rows',panel.row('where unit=mA').caption
 values=with_popups(menu,panel)
 panel.choose('where unit=mA');panel.choose('step:count');settle()
 assert panel.line=='@files:bench readings.csv | rows | where unit=mA | count' and panel.preview_rows()==[{'count':2}],(panel.line,panel.preview_rows())
 assert [op for op,_ in dispatched[before:]]==['language.parse','ledger.address.read'],'nothing more read while choosing'
measured['line_panel']=dict(line=panel.line,count=panel.count_words(),reads=read,rules=menu_rules(panel,'line panel'))
record('Graphite_Desk_D4_09_Then_Line_Panel_Values_1920x1200.png','Then › on bench readings.csv in Files: the line panel beside the menu, the line on its slab (@files:bench readings.csv | rows), 4 rows and 6 steps left, the first rows; Keep rows where › unit open: is mA 2 rows, is V 1 row, is ms 1 row, and the ones to leave out, each counted from the one read.',values)
record('Graphite_Desk_D4_09b_Then_Line_Panel_Counted_1920x1200.png','Two steps on: where unit=mA, then Count; the panel says 1 row (the count, 2) and 4 steps left. Two reads in all, both when the panel opened (language.parse and the file read); Show it would be the third.',with_popups(menu,panel))
check('09 Then › on a table: the line read once (%s), "is mA" counted 2 rows from that read, the line carried to %s with nothing more read'%(', '.join(read),panel.line))
close(menu)

result=dict(state='PASSED',checks=checks,captures=captures,superseded=superseded,measured=measured,dispatched=[[op,{x:str(v)[:80] for x,v in a.items()}] for op,a in dispatched],
 providers=[name for name,_ in cm.PROVIDERS],finders=[f.__name__ for f in cm.FINDERS],sections=list(cm.SECTIONS),folded=len(cm.FOLDED),
 jobs_submitted=0,worker_processes_started=0,model_generations=0,provider_requests=0,native_invocations=0,os_power_or_logout_commands=0,
 owner_host_acceptance=False,clean_close=True)
(OUT/'context-menu-ui.json').write_text(json.dumps(result,indent=1,ensure_ascii=False)+'\n')
print(json.dumps(dict(state=result['state'],checks=checks,captures=[c['file'] for c in captures]),ensure_ascii=False),flush=True)
for guard in (question,detached,system,popen,power,submission,launcher,provider):guard.stop()
w.close()
