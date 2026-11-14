"""The owner's review set for the desk (the brief's "What I want to review"), offscreen, in build/graphite_desk/review/.

The brief: "Show the desk with both launch menus closed, then show the cat's programs list and the upper-right system menu
separately. Show two right-click menus on different kinds of objects and demonstrate one real command or capability running
against the selected object." With the owner's later direction, Log's Network stream. One run of the real window, the same
holds as the desk's checks, each file named for what it shows, at 1920 by 1200 and 1366 by 768 where it applies:

  01  the desk with both launch menus closed
  02  the cat's programs list (opened with Return from the cat)
  03  the System menu from the Graphite symbol (two queued Agenda items show the order and the niceness apart)
  04  right-click on a selected passage in a document
  05  right-click on two revisions of one file selected in Files (a different kind of object)
  06  one real command against the selected object: Bold from the passage's menu (06a before, the row chosen; 06b after: the page
      shows the words bold and its foot the new revision; documents.edit went through Kernel.dispatch with the page's id and the
      revision seen at the right-click)
  07  the symmetry overlay (the axis and the mirrored guides over the window)
  08  Log at Half on its Network stream: this computer's real interfaces and connections as network.observe read them here, and the
      capture's state as the capability gives it here (here: unavailable, with its reason); 08b the packet stream, from the network
      capability's test fixture only (tests_integrated/test_network_watch.py: its small computer's /proc and its frames, read by
      network_watch's own parser), labelled TEST DATA on the image
Every word in the window and in each menu is whole (tools/ui_fit), every capture is listed with what it shows in review.json.

Disposable home, profile and Concern; Kernel.launch, Kernel.submit, the provider request and session_power.system are held (no
login session, no session or power command); after the window exists no process, shell command or detached program may start;
no capture is started (capture is the owner's action). Nothing here is owner-host acceptance.
"""
import hashlib,json,os,socket,subprocess,sys,tempfile,time
from pathlib import Path
from unittest.mock import patch
PROGRAM=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('ARC_LEDGER_DESK_REVIEW_DIR',str(PROGRAM/'build/graphite_desk/review')));OUT.mkdir(parents=True,exist_ok=True)
RUN=Path(tempfile.mkdtemp(prefix='graphite-review-'));HOME=RUN/'home';HOME.mkdir()
SCREEN=RUN/'screen.json';SCREEN.write_text(json.dumps({'screens':[{'name':'review','x':0,'y':0,'width':1920,'height':1200,'logicalDpi':96,'logicalBaseDpi':96,'dpr':1.0}]}))
os.environ.update(QT_QPA_PLATFORM='offscreen:configfile='+str(SCREEN),ARC_LEDGER_EMBEDDED='1',ARC_LEDGER_DISABLE_BOOK_WATCHER='1',HOME=str(HOME),
 ARC1_WORKBENCH_CONFIG_HOME=str(RUN/'profile'),ARC_LEDGER_CONCERN=str(HOME/'Concern'))
os.environ.pop('ARC_LEDGER_XSESSION',None)
sys.path.insert(0,str(PROGRAM));sys.path.insert(0,str(PROGRAM/'tools'));sys.dont_write_bytecode=True
import ui_fit
from PySide6.QtCore import Qt,QPoint,QProcess,QRectF
from PySide6.QtGui import QColor,QContextMenuEvent,QFont,QPainter,QPen,QTextCursor
from PySide6.QtWidgets import QApplication,QMessageBox
from PySide6.QtTest import QTest
from workbench.qt_app import make_app,WorkbenchWindow
from workbench import locations,clip,session_power,files_service,desk_qt,shell2,log_qt,network_watch
from workbench.engineering_kernel import Kernel,operator
from workbench.session import Session
def held_power(request):
 """logind answers that there is no login session (as in this container); no session or power command may start."""
 if request[0]=='logind':raise OSError('no login session (held by the review set)')
 raise AssertionError('No session or power command: %r'%(request,))
provider=patch.object(clip,'_request',side_effect=AssertionError('No provider request')).start()
launcher=patch.object(Kernel,'launch',side_effect=AssertionError('No worker launch')).start()
submission=patch.object(Kernel,'submit',side_effect=AssertionError('No job submission')).start()
power=patch.object(session_power,'system',side_effect=held_power).start()
question=patch.object(QMessageBox,'question',return_value=QMessageBox.Yes).start()
app=make_app([]);root=locations.office(HOME/'Concern'/'Office');session=Session(RUN/'profile/session.json',root)
w=WorkbenchWindow(root,session,restore=False);k=w.ledger_bridge.kernel;bridge=w.ledger_bridge;bar=w.type_bar
import platform;platform.processor()  # the one host probe Python answers through a process, answered before the guards
popen=patch.object(subprocess,'Popen',side_effect=AssertionError('No process start')).start()
system=patch.object(os,'system',side_effect=AssertionError('No shell command')).start()
detached=patch.object(QProcess,'startDetached',side_effect=AssertionError('No detached program')).start()
captures=[]
def settle(ms=25,n=3):
 for name in ('agenda_runner','study_idle'):
  obj=getattr(w,name,None)
  if obj and hasattr(obj,'timer'):obj.timer.stop()
 for _ in range(n):app.processEvents();QTest.qWait(ms)
def call(op,args=None):
 value=k.dispatch(op,args or {},operator());assert value['ok'],value;return value['result']
def align(times=4):
 for _ in range(times):bar.align();settle()
def size(width,height):
 w.resize(width,height);settle(60);align()
def home():
 w.statusBar().clearMessage();w.show_start();w.tabs.setFocus();settle();align(2)
def whole(*popups):
 """Every word whole in the window and in each popup shown, no wrapped label cut short (tools/ui_fit), nothing sideways in the
 workspace."""
 found=ui_fit.whole_words(w)+ui_fit.cut_lines(w)+ui_fit.side_scrolls(w.central_stack)
 for popup in popups:
  if popup is not None and popup.isVisible():found+=ui_fit.whole_words(popup)+ui_fit.cut_lines(popup)+ui_fit.side_scrolls(popup)
 assert not found,ui_fit.describe(found)
def grab(*popups):
 """The window with each popup (its own window) drawn where it is: what the owner sees."""
 pix=w.grab();p=QPainter(pix)
 for popup in popups:
  if popup is not None and popup.isVisible():p.drawPixmap(w.mapFromGlobal(popup.mapToGlobal(QPoint(0,0))),popup.grab())
 p.end();return pix.toImage()
def label(image,words,right,top):
 """TEST DATA said on the image itself, on an eraser-pink band as wide as its words, its right edge at right."""
 p=QPainter(image);font=QFont('IBM Plex Sans');font.setPixelSize(15);font.setWeight(QFont.DemiBold);p.setFont(font)
 width=p.fontMetrics().horizontalAdvance(words)+32;rect=QRectF(right-width,top,width,26)
 p.fillRect(rect,QColor(shell2.ERASER));p.setPen(QColor(shell2.TEXT));p.drawText(rect,Qt.AlignCenter,words);p.end();return image
def record(name,shows,image,*popups,data='real'):
 whole(*popups)
 target=OUT/name;assert image.save(str(target),'PNG'),name
 captures.append(dict(file=name,shows=shows,data=data,resolution=[image.width(),image.height()],sha256=hashlib.sha256(target.read_bytes()).hexdigest(),bytes=target.stat().st_size))
 print(name,flush=True)
def right_click(widget,point):
 before=getattr(w,'context_menu',None)
 QApplication.sendEvent(widget,QContextMenuEvent(QContextMenuEvent.Mouse,point,widget.mapToGlobal(point)));settle()
 menu=getattr(w,'context_menu',None);assert menu is not None and menu is not before,'a right-click opens a menu';return menu
SIZES=((1920,1200),(1366,768))

w.resize(1920,1200);w.show();settle(60);bridge.timer.stop()
try:bar.hatch.lifecycle.timer.stop()
except AttributeError:pass
align();home()
hatch=bar.hatch;lst=hatch.programs;sym=w.shell2.top.nice

# 01 the desk, 02 the programs list, 07 the overlay ------------------------------------------------------------------------------
def overlay():
 """The axis (eraser pink) and the mirrored guides (pencil yellow, dashed): the band insets, the pane edges, the workspace column's
 inset shared by the menus' ink and the writing line, the band edges (as tools/check_desk_ui.py draws its overlay)."""
 pix=w.grab();p=QPainter(pix);W=w.width();H=w.height();d=w.desk
 p.setPen(QPen(QColor('#c99a2e'),1,Qt.DashLine))
 for x in sorted({d.inset,d.pane-d.inset,d.pane,d.pane+d.line}):
  for m in (x,W-x):p.drawLine(m,0,m,H)
 for y in (w.ribbon_dock.height(),w.type_dock.mapTo(w,QPoint(0,0)).y()):p.drawLine(0,y,W,y)
 p.setPen(QPen(QColor(desk_qt.ERASER_MARK),2));p.drawLine(W//2,0,W//2,H)
 if W%2:p.drawLine(W//2+1,0,W//2+1,H)
 # the two notes stacked at the workspace's foot, from the line's inset, clear of the head's menus and the room's own bar
 font=QFont('IBM Plex Sans');font.setPixelSize(14);font.setWeight(QFont.DemiBold);p.setFont(font);y=w.type_dock.mapTo(w,QPoint(0,0)).y()-2*34-6
 for text,colour,x in (('axis  x = %d / 2'%W,desk_qt.ERASER_MARK,d.pane+d.line+8),('both panes %d px · inset %d · menus and line inset %d · bands %d px'%(d.pane,d.inset,d.line,d.band),'#9a6f12',d.pane+d.line+8)):
  r=p.boundingRect(QRectF(x,y,900,24),Qt.AlignLeft|Qt.AlignVCenter,text).adjusted(-6,-3,6,3)
  p.fillRect(r,QColor('#fffdf8'));p.setPen(QColor(colour));p.drawRect(r);p.drawText(r,Qt.AlignCenter,text);y+=34
 p.end();return pix.toImage()
for wd,ht in SIZES:
 size(wd,ht);home()
 record('Graphite_Review_01_Desk_Menus_Closed_%dx%d.png'%(wd,ht),'The desk with both launch menus closed, %d by %d, 14 pt: the two graphite bands; Graphite in the script at the upper left and the erased Graphite symbol at the far right (the System menu); the eight menus across the workspace; CPU · GPU · RAM · TXT; the left pane (Machine · Cabinet · Settings, the active tree with its branch lines, Trash at its lower right) and the right pane (Conversation · Activity · Context), %d px each; the workspace (Today, the Finder) centred; the lower band: the cat, Line · Half · Tall, the writing line with its poem placeholder, and the four modes Assignment · Bash · Search · Log, Assignment marked.'%(wd,ht,w.desk.pane),grab())
 record('Graphite_Review_07_Symmetry_Overlay_%dx%d.png'%(wd,ht),'The same desk with the axis (pink) and the mirrored guides (dashed yellow): the bands\' insets, the pane edges, the workspace column\'s inset that the menus\' ink and the writing line share, and the band edges. tools/check_desk_ui.py measures every pair at 0 px at nine sizes and fonts.',overlay())
 hatch.setFocus();settle();QTest.keyClick(hatch,Qt.Key_Return);settle(60);assert lst.isVisible()
 record('Graphite_Review_02_Cat_Programs_List_%dx%d.png'%(wd,ht),'The cat\'s programs list, %d by %d, opened with Return from the cat (one click opens it too): %d programs and capabilities, one plain name and one small graphite icon each, A to Z, then Explore the workshop; its small caption in the script at the top; the cat\'s paw raised and its eyes yellow while the list is open. It opens upward from the lower left, the System menu\'s point-mirror image.'%(wd,ht,len(lst.rows())-1),grab(lst),lst)
 lst.close_menu();settle()

# 03 the System menu (two queued Agenda items: the queue's order and each row's niceness, two different controls) -----------------
for title in ('Read the bench notes','Compare the two drafts'):call('agenda.add',{'title':title,'program':'@files:bench.txt','nice':'normal'})
leave=session_power.session_exit()
for wd,ht in SIZES:
 size(wd,ht);home();sym.setFocus();settle();QTest.keyClick(sym,Qt.Key_Return);settle(80);menu=sym.popup
 assert menu.isVisible() and menu.words()[:2]==['Game','Stop all jobs'],menu.words()
 record('Graphite_Review_03_System_Menu_%dx%d.png'%(wd,ht),'The System menu, %d by %d, opened with Return from the Graphite symbol: Game (STRUTHIO, paused at tick zero) first; Stop all jobs directly beneath (scoped in words to the work Graphite manages); the process list: the queue\'s two Agenda items, each with its place number at the left (the order: drag, Earlier, Later) and its niceness slider under its title; Graphite services On · Off · Restart; then, set apart, Log out (this login session), %s (this Graphite session), Restart and Shut down (this computer). Here there is no login session, so those three say unavailable in quiet ink (their reason is the tooltip and F1); on your computer logind decides.%s'%(wd,ht,leave['label'],' At this height the menu scrolls.' if menu.scroll.verticalScrollBar().maximum()>0 else ''),grab(menu),menu)
 menu.close_menu();settle()

# 04 a selected passage, 06 Bold on it -----------------------------------------------------------------------------------------
size(1920,1200);home()
from workbench.document_qt import show as show_document
doc=show_document(w);settle()
doc.title_box.setText('Bench notes');doc.page.setPlainText('The bench supply holds 5 V within a hair across the whole load range.\nThe ripple stays under 10 mV at full load.');settle();doc.flush();settle()
text=doc.page.toPlainText();start=text.index('within a hair');end=start+len('within a hair')
def passage_menu():
 w.tabs.setCurrentWidget(doc);settle()
 c=doc.page.textCursor();c.setPosition(start);c.setPosition(end,QTextCursor.KeepAnchor);doc.page.setTextCursor(c);settle()
 r=doc.page.cursorRect(c);return right_click(doc.page.viewport(),QPoint(r.center().x()-40,r.bottom()-1))  # on the selected words, near their foot
for wd,ht in SIZES:
 size(wd,ht);menu=passage_menu();assert menu.target.kind=='passage'
 record('Graphite_Review_04_Right_Click_Selected_Passage_%dx%d.png'%(wd,ht),'Right-click on a selected passage in a document, %d by %d: the passage named at the top with its page and revision ("within a hair" · passage · Bench notes · revision %s); the changes first (Bold, Italic, Underline, Plain, Paragraph style, Move to notes); Inspect in the line (the equivalent staC command); Ask Stacy about this and Search; the text edits last.'%(wd,ht,menu.target.revision),grab(menu),menu)
 menu.close_menu(restore=False);settle()

# 05 two revisions of one file in Files: a different kind of object --------------------------------------------------------------
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
for wd,ht in SIZES:
 size(wd,ht);w.tabs.setCurrentWidget(tab);settle();tab.reload();settle();view.clearSelection()
 for name in ('regulator rev B.txt','regulator rev C.txt'):row_of(name).setSelected(True)
 r=view.visualItemRect(row_of('regulator rev C.txt'));menu=right_click(view.viewport(),QPoint(r.left()+120,r.bottom()-1))  # on its name, near its foot
 assert (menu.target.kind,len(menu.target.items))==('files',2) and menu.words()[0]=='Compare revisions',menu.words()
 record('Graphite_Review_05_Right_Click_Two_File_Revisions_%dx%d.png'%(wd,ht),'Right-click on two revisions of one file selected in Files, %d by %d: both named at the top; Compare revisions first (the two actual files go to files.compare), then Copy to, Move to, Copy paths and, last, Delete.'%(wd,ht),grab(menu),menu)
 menu.close_menu(restore=False);settle()

# 06 one real command against the selected object: Bold, before and after ------------------------------------------------------
size(1920,1200);menu=passage_menu();seen=menu.target.revision;bold=menu.row('mark:bold');bold.setFocus();settle()
record('Graphite_Review_06a_Bold_Before_1920x1200.png','Before: the passage "within a hair" selected on revision %s of Bench notes, its right-click menu open with Bold under the keyboard\'s focus.'%seen,grab(menu),menu)
bold.click();settle(80);last=w._context_last;assert last['ok'],last
saved=call('documents.get',{'id':doc.document_id})['document'];assert saved['revision']==seen+1 and saved['blocks'][0]['marks']==[{'start':start,'end':end,'bold':True}],saved['blocks'][0]
c=doc.page.textCursor();c.clearSelection();c.setPosition(end);doc.page.setTextCursor(c);settle()
assert 'revision %d'%(seen+1) in doc.foot.text(),doc.foot.text()
record('Graphite_Review_06b_Bold_After_1920x1200.png','After: Bold ran documents.edit through Kernel.dispatch with the page\'s id and the revision seen at the right-click (%s), the same checks as anywhere else; the page shows "within a hair" in bold where it was, its foot says revision %s, and the status line says what was done. Ctrl Z takes it back.'%(seen,saved['revision']),grab())
w.statusBar().clearMessage();settle()

# 08 Log at Half on Network: this computer, as observed here ------------------------------------------------------------------
# The review set holds one loopback connection open (its own sockets, nothing leaves the computer), so at least one connection
# with its process is there to see whatever the computer is doing; everything else is what network.observe read here.
server=socket.socket();server.bind(('127.0.0.1',0));server.listen(1);port=server.getsockname()[1]
client=socket.create_connection(('127.0.0.1',port));accepted,_=server.accept()
log=w.log_view
def network_half():
 home();bar.set_target('log',focus=False);w.console.set_size(1);settle(80);align(2);log.timer.stop();log.choose('network',remember=False,read=False)
 for _ in range(2):log.refresh(force=True);settle(60);time.sleep(0.6)  # rates appear from the second look
 log.refresh(force=True);settle(60)
real=[]
for wd,ht in SIZES:
 size(wd,ht);network_half()
 state=dict(log.capture);seen_connections=len(log.connections_seen);real.append(dict(size='%dx%d'%(wd,ht),capture=state.get('state'),reason=state.get('reason'),connections=seen_connections,interfaces=[i.get('name') for i in log.interfaces_seen]))
 assert log.observed and log.interfaces_seen and seen_connections,'network.observe read this computer'
 record('Graphite_Review_08_Log_Network_Half_This_Computer_%dx%d.png'%(wd,ht),'Log at Half on its Network stream, %d by %d: this computer\'s real interfaces (%s) with their receive and send rates and its %d open connections with their processes, as network.observe read them here through Kernel.dispatch (one is the review set\'s own loopback connection on port %d); the capture\'s state as the capability gives it here: %s%s. Nothing was captured.'%(wd,ht,', '.join(real[-1]['interfaces']),seen_connections,port,state.get('state','?').lower(),(' — "'+str(state.get('reason'))+'"') if state.get('reason') else ''),grab())
for s in (client,accepted,server):s.close()

# 08b the packet stream, from the capability's test fixture only (labelled TEST DATA) --------------------------------------------
import importlib.util
spec=importlib.util.spec_from_file_location('network_fixture',PROGRAM/'tests_integrated'/'test_network_watch.py');fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
tree=RUN/'fixture';proc,sys_root,etc=fixture.fake_tree(tree)
frames=[fixture.SYN,fixture.SYNACK,fixture.PUSH,fixture.ARP,fixture.DNS6]
packets=[]
for n,frame in enumerate(frames*4):
 p_=network_watch.decode({'data':frame,'linktype':1,'at':1_794_000_000+n*0.137,'length':len(frame)},interface='eth0');p_['seq']=n+1;packets.append(p_)
RUNNING={'state':'RUNNING','tool':'dumpcap (test fixture)','started':time.time()-9,'packets':len(packets),'filter':''}
class Fixture:
 """D5's four operations answered from the test fixture alone: observe reads the fixture's /proc, /sys and /etc with
 network_watch's own parser; read gives the fixture's frames decoded by network_watch.decode; a capture shows as running."""
 calls=[]
 def __call__(self,operation,arguments):
  self.calls.append(operation)
  if operation=='network.observe':return {'ok':True,'result':network_watch.observe(None,arguments,proc_root=proc,sys_root=sys_root,etc=etc,capture=dict(RUNNING))}
  if operation=='network.capture.read':
   after=int(arguments.get('after') or 0);rows=[p_ for p_ in packets if p_['seq']>after]
   return {'ok':True,'result':dict(packets=rows,next=str(rows[-1]['seq']) if rows else str(after),capture=dict(RUNNING))}
  raise AssertionError('The review set asks the fixture only to observe and read: '+operation)
real_dispatch=log.dispatch;log.dispatch=Fixture()
size(1920,1200);home();bar.set_target('log',focus=False);w.console.set_size(1);settle(80);align(2);log.timer.stop()
log.packet_cursor=None;log.packets.clear();log.choose('network',remember=False,read=False)
for _ in range(2):log.refresh(force=True);settle(40)
assert log.packets.count()>=len(packets)-1,log.packets.count()
log.chose(log.packets.item(2));settle()
FIXTURE='TEST DATA: the network capability\'s test fixture (tests_integrated/test_network_watch.py), not this computer'
image=grab();vx,vy=log.mapTo(w,QPoint(0,0)).x(),log.mapTo(w,QPoint(0,0)).y()
record('Graphite_Review_08b_Log_Network_Packets_TEST_DATA_1920x1200.png','TEST DATA, labelled on the image: the packet stream as Log shows it while a capture runs, from the network capability\'s test fixture only (its small computer\'s /proc, /sys and /etc read by network_watch.observe, and its frames decoded by network_watch.decode: headers only, never what a packet carries); one packet pinned at the top with Ask Stacy about this. This computer has no capture tool, so no real packet stream exists here.',
       label(image,FIXTURE,vx+log.width(),vy-30),data='TEST DATA (the network capability\'s test fixture)')
log.unpin();log.dispatch=real_dispatch;bar.set_target('slate',focus=False);w.console.set_size(0);settle()

result=dict(state='WRITTEN',folder=str(OUT.relative_to(PROGRAM)) if OUT.is_relative_to(PROGRAM) else str(OUT),captures=captures,network_here=real,
 fixture_calls=sorted(set(Fixture.calls)),jobs_submitted=submission.call_count,worker_processes_started=launcher.call_count,provider_requests=provider.call_count,
 session_or_power_commands=0,captures_started=0,owner_host_acceptance=False)
(OUT/'review.json').write_text(json.dumps(result,indent=1,ensure_ascii=False)+'\n')
print(json.dumps(dict(state=result['state'],captures=[c['file'] for c in captures]),ensure_ascii=False),flush=True)
for guard in (question,detached,system,popen,power,submission,launcher,provider):guard.stop()
w.close()
