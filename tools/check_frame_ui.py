"""Actual Qt checks for the permanent five-part desktop (HATCH DESKTOP-01, WI-1): AC01 mechanically, the side columns'
own floors across an interface-size excursion, Home with the right column, the typing strip's words and context, the
right column's one held-state sentence, the keyboard walk, and the top command row at 1366 by 768 and 1280 by 720.
GRAPHITE-01 (G-B): every word in the window whole (tools/ui_fit; outside the head and the centre only ui_fit.PENDING, words
awaiting edits in other files) and nothing in the centre scrolling sideways at Home at 1920 by 1200, 1366 by 768 and 18 pt
(Today one column under its width); the head's menu words fold into ⋯ before they clip, at every width from 1040 to 1400.
HATCH DESK D1a: the two side columns are the desk's two equal panes (desk_qt; tools/check_desk_ui.py measures the mirror
image): both are one width through the interface-size excursion, a drag of either separator moves both, the Workspace
setting sets both, and the saved width restores both. Explore left the strip, so the Tab walk goes cat, Line, Half, Tall.

Disposable profile, Concern and job rows; Kernel.launch, Kernel.submit and the provider request are held; after the
window exists no process may start. Offscreen captures at 1920 by 1200 and 1366 by 768. Nothing here is owner-host
acceptance: AC01 and AC15 keep their real-host and model columns open.
"""
import hashlib,json,os,subprocess,sys,tempfile,time
from pathlib import Path
from unittest.mock import patch
PROGRAM=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('ARC_LEDGER_FRAME_CAPTURE_DIR',str(PROGRAM/'build/ui_checks/frame')));OUT.mkdir(parents=True,exist_ok=True)
RUN=Path(tempfile.mkdtemp(prefix='ledger-desktop01-frame-'))
# A 1920 by 1200 offscreen screen (the plugin's default is 800 by 800), so fullscreen is a real round trip at the review size.
SCREEN=RUN/'screen.json';SCREEN.write_text(json.dumps({'screens':[{'name':'review','x':0,'y':0,'width':1920,'height':1200,'logicalDpi':96,'logicalBaseDpi':96,'dpr':1.0}]}))
os.environ.update(QT_QPA_PLATFORM='offscreen:configfile='+str(SCREEN),ARC_LEDGER_EMBEDDED='1',ARC_LEDGER_DISABLE_BOOK_WATCHER='1',
 ARC1_WORKBENCH_CONFIG_HOME=str(RUN/'profile'),ARC_LEDGER_CONCERN=str(RUN/'Concern'))
os.environ.pop('ARC_LEDGER_XSESSION',None)
sys.path.insert(0,str(PROGRAM));sys.path.insert(0,str(PROGRAM/'tools'));sys.dont_write_bytecode=True
import ui_fit
from PySide6.QtCore import Qt,QPoint,QProcess
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QApplication,QMessageBox,QLabel,QWidget
from PySide6.QtTest import QTest
from workbench.qt_app import make_app,WorkbenchWindow
from workbench import locations,clip,ledger_control,typebar_qt
from workbench.engineering_kernel import Kernel,operator
from workbench.session import Session
from workbench.service_lifecycle import SUMMARIES
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
checks=[];captures=[];focus_log=[];areas_log=[]
def settle(ms=25):
 for name in ('agenda_runner','study_idle'):
  obj=getattr(w,name,None)
  if obj and hasattr(obj,'timer'):obj.timer.stop()
 for _ in range(2):app.processEvents();QTest.qWait(ms)
def check(text):checks.append(text);print(text,flush=True)
def call(op,args=None):
 value=k.dispatch(op,args or {},operator());assert value['ok'],value;return value['result']
def name_of(widget):
 if widget is None:return None
 text=widget.text() if hasattr(widget,'text') and callable(widget.text) and isinstance(widget.text(),str) else ''
 return type(widget).__name__+(':'+widget.objectName() if widget.objectName() else '')+(':'+text.replace('&','')[:24] if text else '')
def focus(step):
 f=QApplication.focusWidget();focus_log.append(dict(step=step,focus=name_of(f)));return f
def areas(window):
 """The five parts as window-relative bounds: left column, Ledger Head, centre, right column, typing strip."""
 def rect(widget):
  if widget is None or not widget.isVisible():return None
  p=widget.mapTo(window,widget.rect().topLeft());return [p.x(),p.y(),widget.width(),widget.height()]
 return dict(left=rect(window.nav_dock),head=rect(window.ribbon_dock),centre=rect(window.central_stack),right=rect(window.sim_dock),strip=rect(getattr(window,'type_dock',None)))
def five_visible(step,window=None):
 window=window or w;bounds=areas(window);areas_log.append(dict(step=step,**bounds))
 missing=[key for key,value in bounds.items() if value is None]
 assert not missing,(step,missing)
 inside=all(0<=x and 0<=y and x+width<=window.width() and y+height<=window.height() for x,y,width,height in bounds.values())
 assert inside,(step,bounds,window.size())
 assert bounds['left'][0]<bounds['centre'][0]<bounds['right'][0] and bounds['head'][1]<bounds['centre'][1]<bounds['strip'][1],(step,bounds)
 # UI-03: Stop is the first row of Nice (no separate Stop in the head) and the monitors' holder stands in the head beside Nice.
 assert window.trash_can.isVisible() and window.shell2.top.programs.isVisible() and window.operations_monitors.isVisible() and not window.master_stop_button.isVisible(),step
 return bounds
def capture(name,note,*popups,window=None):
 window=window or w;window.operations_panel.refresh();settle();pix=window.grab();mode='ACTUAL_QT_WINDOW_GRAB';painter=QPainter(pix)
 for popup in popups:
  assert popup.isVisible();pos=window.mapFromGlobal(popup.mapToGlobal(QPoint(0,0)));painter.drawPixmap(pos,popup.grab());mode='ACTUAL_QT_WINDOW_AND_VISIBLE_POPUP_GRABS'
 painter.end();target=OUT/name;assert pix.save(str(target),'PNG')
 captures.append(dict(file=name,note=note,mode=mode,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),resolution=[window.width(),window.height()]))
def align(times=3):
 for _ in range(times):bar.align();settle()
def setting(key,value):
 row=next(r for r in ledger_control.settings(k)['settings'] if r['key']==key)
 call('ledger.settings.set',{'key':key,'value':value,'expected_revision':row['revision']});bridge.sync_profile(force=True);settle(40);align()
def ui_pt(points):setting('reading.ui_pt',float(points));w.operations_panel.refresh();settle();align()
def rows(group=None):return [hatch.entries[v[0]] for v in __import__('workbench.explore',fromlist=['VIEWS']).VIEWS if group in (None,v[3])]  # D2: the programs list's rows (flat)
def row(prefix,group=None):return next(a for a in rows(group) if (a.property('title') or a.text()).startswith(prefix) or a.text().startswith(prefix))
def widths():return [w.nav_dock.width(),w.sim_dock.width()]
def spare():return max(0,w.centralWidget().width()-w.centralWidget().minimumSizeHint().width())  # what the centre can give up
def drag(dock,dx):
 # The owner's hand: press on the separator beside the pane, move, release (LP01). D1a: the desk reads the drag itself
 # (desk_qt.MirroredDrag) and moves both panes; the separator is the pixel column beside the pane.
 g=dock.geometry();y=g.center().y();edge=g.right()+1 if dock is w.nav_dock else g.left()-1
 start=QPoint(edge,y);end=start+QPoint(dx,0)
 QTest.mousePress(w,Qt.LeftButton,Qt.NoModifier,start);QTest.qWait(20);QTest.mouseMove(w,start+QPoint(dx//2,0));QTest.qWait(20)
 QTest.mouseMove(w,end);QTest.qWait(20);QTest.mouseRelease(w,Qt.LeftButton,Qt.NoModifier,end);settle();align()
def floors():return bar.floors()
def bar_words():
 (lp,ls),(rp,rs)=bar.rows();return dict(primary=lp+rp,secondary=ls+rs)
def cat_inside(b):  # D1-fix: the cat's button holds every pose of its drawing (graphite_brand.cat_ink in its tile), whole
 from workbench import graphite_brand
 return all(0<=l and r<=b.width() for l,_,r,_ in (graphite_brand.cat_ink(b.tile(),p) for p in graphite_brand.POSES.values()))
def whole(buttons):return all((cat_inside(b) if b is hatch else b.width()>=b.sizeHint().width()) and b.text()==bar.words.get(b,b.text()) for b in buttons)
def tab_strip_y():return w.tabs.tabBar().mapTo(w,w.tabs.tabBar().rect().topLeft()).y()
def card_lines(card):
 import re
 from PySide6.QtWidgets import QAbstractButton
 return [re.sub('<[^>]+>','',widget.text()).replace('&','') for widget in card.findChildren(QWidget) if isinstance(widget,(QLabel,QAbstractButton)) and widget.text()]
w.resize(1920,1200);w.show();settle(120);bridge.timer.stop();hatch.lifecycle.timer.stop();align()
# 01 · AC01 step: start with no project (Today, the program's Home route for a bare office) ---------------------------------
w.show_start();settle();align()
assert w._home_active and type(w.central_stack.currentWidget()).__name__=='FinderPage' and type(w.central_stack.currentWidget().today).__name__=='TodayPage',type(w.central_stack.currentWidget()).__name__  # UI-04: Home is the Finder; Today is its first place
five_visible('start, no project');focus('start')
fresh_widths=widths();fresh_floors=floors()
assert fresh_widths==fresh_floors==[w.desk.pane,w.desk.pane],(fresh_widths,fresh_floors,w.desk)  # D1a: one width for both panes
from workbench import desk_qt
need_least,need_whole,need_centre=desk_qt.needs(w);assert w.desk.pane==desk_qt.pane_width(w.width(),1.0,bar.pane_owner,need_least,need_whole,need_centre),(w.desk,need_least,need_whole,need_centre)
assert whole(bar_words()['primary']) and whole(bar_words()['secondary']),[(b.text(),b.width(),b.sizeHint().width()) for b in bar_words()['primary']+bar_words()['secondary']]
assert w.sim_dock.isVisible() and w.console_pages.currentWidget() is w.shell2.face  # 0.5: Stacy is the first thing on the right (it was Activity); Activity is one word away
page=w._empty_home_page;assert page.layout().contentsMargins().right()==0,'Today sits in the centre; the right panel is shown, not compensated for'
assert bar.context.isVisible() and bar.context_text=='Home' and bar.context.text().endswith('Home'),(bar.context_text,bar.context.text())
capture('Ledger_Slate_DESKTOP_01_Frame_01_Start_Home.png','Start with no project: Today in the centre with both side columns, the Ledger Head and the typing strip; the right column shows Operations. The context word reads Home.')
check('Start with no project keeps the five parts visible; both side columns are the desk\'s one pane width (%d/%d) and every strip word is whole'%tuple(fresh_floors))
# 02 · open an existing project; the context word follows the selected record ----------------------------------------------
project=call('projects.create',{'title':'Desktop frame workshop','intent':'Keep the five parts of the desktop visible through every route.'})
idea=call('ideas.capture',{'project':project['id'],'text':'Does the frame hold while work opens?'})
w.cabinet_page.refresh(force=True);w.cabinet_page.select('idea:'+idea['id'],reveal=True);room=w.cabinet_page.open('idea:'+idea['id']);settle();align()
assert not w._home_active and w.tabs.currentWidget() is room
five_visible('project opened');focus('project opened')
assert bar.context_text==idea['text'] and bar.context.isVisible(),(bar.context_text,bar.context.text())
assert bar.context.width()<=bar.box.width()//3 and bar.box.textMargins().right()>=bar.context.width(),(bar.context.width(),bar.box.width(),bar.box.textMargins().right())
source=root/'Files/frame_draft.py';source.parent.mkdir(exist_ok=True);source.write_text('original = True\n')
editor=w.open_document(source);editor.appendPlainText('# unsaved thought kept through every route');settle();align()
assert w.tabs.preview() is editor and editor.document().isModified()
check('Opening a project record and a source file keeps the frame; the context word names the selected record inside the box, clear of the typed text')
# 03 · launch two supported workspaces from Hatch; navigation executes nothing --------------------------------------------
assert hatch.prepare();count=w.tabs.count();row('Projects').trigger();settle();desk=w.tabs.currentWidget()
assert type(desk).__name__=='ProjectDeskTab' and desk.property('ledgerRoom')
hatch.prepare();row('Activity').trigger();settle();trail=w.tabs.currentWidget();assert type(trail).__name__=='WorkTrailTab'
assert w.tabs.count()==count+2 and w.tabs.preview() is editor and editor.document().isModified() and w.tabs.pinned()==[]
popen.assert_not_called();system.assert_not_called();detached.assert_not_called();launcher.assert_not_called();submission.assert_not_called()
five_visible('two workspaces from Hatch');focus('two workspaces from Hatch');align()
assert bar.context_text==idea['text'],'a selected cabinet record stays the context while rooms open'
w.cabinet_page.tree.setCurrentItem(None);align();assert bar.context_text==trail.property('ledgerTitle')=='Work trail',(bar.context_text,trail.property('ledgerTitle'))
capture('Ledger_Slate_DESKTOP_01_Frame_02_Workspaces_From_Hatch.png','Project Desk and Activity & receipts opened from Hatch as rooms beside the edited Preview; the five parts stay; the context word names the current workspace.')
check('Two workspaces launched from Hatch open as rooms with the edited Preview kept, no pin used and zero job, worker, model, provider or process activity')
# 04 · maximize centre work: F11 round trip keeps the columns ---------------------------------------------------------------
before=widths();w.toggle_fullscreen();settle(60);assert w.isFullScreen();five_visible('fullscreen');w.toggle_fullscreen();settle(80);w.resize(1920,1200);settle(60);align()
assert not w.isFullScreen() and all(abs(a-b)<=2 for a,b in zip(widths(),before)),(before,widths())
five_visible('after F11 round trip');focus('after F11 round trip')
check('F11 round trip keeps both column widths (%d/%d) and the five parts'%tuple(widths()))
# 05 · switch tabs: the strip and page top hold still; drafts kept ------------------------------------------------------------
ys={}
for name,target in (('desk',desk),('editor',editor),('trail',trail),('record',room)):
 w.tabs.setCurrentWidget(target);settle();ys[name]=tab_strip_y();five_visible('tab '+name)
w.ledger_bridge.show_settings();settle();ys['settings']=tab_strip_y();w.a_host_service.trigger();settle();ys['service']=tab_strip_y()
assert len(set(ys.values()))==1,ys
assert editor.document().isModified() and '# unsaved thought' in editor.toPlainText()
focus('after tab switches')
check('Switching among six tabs leaves the tab strip at one height (y=%d) and keeps the unsaved draft'%ys['desk'])
# 06 · the typing strip: words, quiet routes, destination and context, no lingering message -----------------------------------
# HATCH DESK D3: the strip's words are the writing line's four modes (the Shell word is Bash only when the configured shell is bash)
assert [b.text() for b in (bar.targets[key] for key,_ in typebar_qt.TARGETS)]==['Assignment',typebar_qt.shell_label(typebar_qt.configured_shell()),'Search','Log']
assert typebar_qt.QUIET_TARGETS==() and not [b for b in bar.targets.values() if b.property('arcQuiet')]
assert bar.box.placeholderText()=='prompt'
bar.set_target('shell',focus=False);assert bar.box.accessibleDescription().startswith(bar.labels['shell']+' · ') and w.console.mode=='shell' and w.type_target=='shell'
bar.set_target('slate',focus=False);assert bar.box.accessibleDescription().startswith('Assignment · ')
w.statusBar().showMessage('Saved as frame_draft.py');settle()
assert w.console.hint.isVisible() and w.console.hint.text()=='Saved as frame_draft.py' and bar.box.placeholderText()=='prompt' and bar._note_timer.isActive() and bar._note_timer.interval()==typebar_qt.NOTE_MS
bar.expire_note();settle();assert not w.console.hint.isVisible() and bar.box.accessibleDescription().startswith('Assignment · ') and bar.box.toolTip()==bar._box_tip
check('The strip reads Assignment · %s · Search · Log (D3: the writing line\'s four modes); the box keeps poem, its description names the mode, and a status message leaves after %d s'%(bar.labels['shell'],typebar_qt.NOTE_MS//1000))
# 07 · the right column: one sentence for the held state, scaled metadata, unclipped rows ---------------------------------------
w.tabs.setCurrentWidget(room);settle();w.shell2.show_operations_face();panel=w.operations_panel
first=call('agenda.add',{'title':'Inspect the saved interface notes before the review meeting','program':'@files:frame_draft.py','nice':'normal'})
panel.refresh();settle();enabled_height=panel.services.height();enabled_text=panel.services.text()
call('ledger.settings.set',{'key':'operations.services_enabled','value':False});panel.refresh();settle();assert hatch.prepare()
system_menu=w.shell2.top.nice.menu_();hatch.lifecycle.refresh();settle()  # D2: Graphite services are the System menu's row
held=SUMMARIES['ADMISSION_HELD'];assert panel.services.text()=='GRAPHITE SERVICES · '+held and system_menu.services.toolTip().startswith(held[:40]),(panel.services.text(),system_menu.services.toolTip())
assert panel.services.height()==enabled_height,(enabled_height,panel.services.height())
assert 'New Graphite work off' not in panel.slate.text() and 'New Ledger work off' not in panel.slate.text() and 'New work held' not in panel.slate.text()
work=w.shell2.top.nice;work.open();settle();work=work.popup  # D1-fix: the queue rows are the System menu's list (Activity says it in one line)
item=work.queue.item(0);widget=work.queue.itemWidget(item);texts=[label.text() for label in widget.findChildren(QLabel)]
assert any(held in text for text in texts) and not any(text in ('Ledger services off','Graphite services off') for text in texts),texts
assert all(label.width()<=work.queue.viewport().width() for label in widget.findChildren(QLabel)) and item.sizeHint().height()>=widget.sizeHint().height(),(item.sizeHint().height(),widget.sizeHint().height())
assert work.queue.verticalScrollBar().maximum()==0,'one row never scrolls'
assert panel.jobs.words().startswith('WORK · 1 queued'),panel.jobs.words()
from workbench.operations_qt import caption_px
assert 'font-size:%dpx'%caption_px(w,12) in w.shell2.top.pulse.labels['CPU'].styleSheet() and w.shell2.top.pulse.toolTip()=='Current Graphite host · CPU / GPU / RAM / TXT'  # UI-03: the column note's words are the pulse's tooltip
work.hide();settle()
capture('Ledger_Slate_DESKTOP_01_Frame_03_Held_State_Words.png','Admission held: the Services line, the queue row reason and the System menu\'s Graphite services row say the one sentence from service_lifecycle.SUMMARIES; the line keeps its two-line height; metadata is sized from the interface setting.')
call('ledger.settings.set',{'key':'operations.services_enabled','value':True});panel.refresh();settle();assert panel.services.text()==enabled_text
check('Held state is one sentence on the Services line, the queue row and the System menu\'s Graphite services row; the Services line does not shift the column; queue rows are elided to their width and sized from their words')
# 08 · the columns through an interface-size excursion (14 → 20 → 14; 16, 18 and 28 pt measured) --------------------------------
w.tabs.setCurrentWidget(editor);settle();start=widths();heights={14:(bar.height(),bar.box.height())}
excursion={}
for points in (16,18,20):
 ui_pt(points);excursion[points]=dict(widths=widths(),floors=floors(),bar=bar.height(),box=bar.box.height())
 assert whole(bar_words()['primary']) and whole(bar_words()['secondary']),(points,[(b.text(),b.width(),b.sizeHint().width()) for b in bar_words()['primary']+bar_words()['secondary']])
 assert widths()[0]==widths()[1]==floors()[0]==floors()[1]==w.desk.pane,(points,widths(),floors())  # D1a: one width for both panes at every size
 heights[points]=(bar.height(),bar.box.height())
assert heights[20][0]>heights[14][0] and heights[20][1]>heights[14][1] and bar.height()==w.desk.band==w.ribbon_dock.height(),heights  # D1a: both bands one height
capture('Ledger_Slate_DESKTOP_01_Frame_04_Interface_20pt.png','Interface text at 20 pt: both panes widened together to %d px; every strip word whole; both bands taller, the same height.'%floors()[0])
ui_pt(28);words28=bar_words();assert whole(words28['primary']),[(b.text(),b.width(),b.sizeHint().width()) for b in words28['primary']]
assert widths()[0]==widths()[1],widths()
elided=[b.text() for b in words28['secondary'] if b.text()!=bar.words[b]]
assert all(b.toolTip().startswith(bar.words[b]) for b in words28['secondary'] if b.text()!=bar.words[b]),'the whole word stays in the tooltip'
capture('Ledger_Slate_DESKTOP_01_Frame_05_Interface_28pt.png','Interface text at 28 pt (200%%): both panes %d px; the cat and the four modes Assignment, Shell, Search and Log stay whole (D3); the secondary words elide by the documented rule (%s).'%(widths()[0],', '.join(elided) or 'none needed'))
ui_pt(14);align(3)
assert floors()==fresh_floors and widths()==start,(fresh_floors,floors(),start,widths())
assert whole(bar_words()['primary']) and whole(bar_words()['secondary'])
give=min(60,spare()//4);assert give>=16,('the centre is at its minimum; no room to drag',spare())
drag(w.nav_dock,give);drag(w.sim_dock,-give);owner=widths();assert owner==[fresh_floors[0]+2*give]*2 and [bar.owner[w.nav_dock],bar.owner[w.sim_dock]]==owner and bar.pane_owner==owner[0],(owner,bar.owner,give)  # each drag moved both
ui_pt(16);assert widths()==owner,(widths(),owner);ui_pt(14);align();assert widths()==owner and floors()==owner,(widths(),floors())
drag(w.sim_dock,owner[1]-fresh_floors[1]+80);least_width=widths()[0];assert widths()[0]==widths()[1]<fresh_floors[0],'dragged under the default, both panes go down to what their words need: '+str(widths())
setting('layout.navigator_width',fresh_floors[0]);bridge.tick();settle()
readback=next(r for r in ledger_control.settings(k,'Workspace')['settings'] if r['key']=='layout.navigator_width')
assert readback['stored']==readback['effective']==fresh_floors[0] and readback['application_state']=='APPLIED' and widths()==fresh_floors,{key:readback[key] for key in ('stored','effective','application_state')}
setting('layout.navigator_width',420);bridge.tick();settle()
readback=next(r for r in ledger_control.settings(k,'Workspace')['settings'] if r['key']=='layout.navigator_width')
assert readback['effective']==420 and readback['application_state']=='APPLIED' and widths()==[420,420],(readback['effective'],readback['application_state'],widths())
check('14 → 16 → 18 → 20 → 28 → 14 pt: both panes stay one width and come back to %d/%d with no ratchet; a width the owner dragged (either separator moves both) survives the excursion; dragged narrow, both stop at what their words need (%d); layout.navigator_width reads back as requested and sets both panes'%(tuple(fresh_floors)+(least_width,)))
# 09 · keyboard: Pin → Hatch in one Tab; the forward cycle from Hatch returns without a trap -----------------------------------
# A source editor or a writing passage in the centre takes Tab as indentation by design, so the cycle is walked with the
# Work trail room current (lists and words only).
w.tabs.setCurrentWidget(trail);settle()
w.tabs.pin_button.setFocus();settle();QTest.keyClick(w,Qt.Key_Tab);app.processEvents();assert QApplication.focusWidget() is hatch,name_of(QApplication.focusWidget())
walk=[];stops=[]
for _ in range(90):
 QTest.keyClick(w,Qt.Key_Tab);app.processEvents();f=QApplication.focusWidget();walk.append(name_of(f));stops.append(f)
 if f is hatch:break
assert stops[-1] is hatch and len(walk)<=80,(len(walk),walk)
assert not any(a is b for a,b in zip(stops,stops[1:])),('a stop repeated twice in a row (a trap)',walk)
assert walk[:5]==['QPushButton:Line','QPushButton:Half','QPushButton:Tall','OneBox:OneBox','QPushButton:Assignment'],walk[:5]  # D1a: Explore left the strip; D3: the modes
assert w.console_pages.focusPolicy()==Qt.NoFocus
focus('after keyboard walk')
check('Tab from Pin / Unpin reaches the cat in one stop; with a room in the centre the forward cycle from the cat returns to it in %d stops through the strip (Line, Half, Tall, the line, Assignment, Shell, Search, Log), the System menu\'s symbol in the head (whose list holds Stop) and the right panel, with no stop trapped (a source editor keeps Tab for indentation, as before)'%len(walk))
# 10 · Home again with a waiting job in words -----------------------------------------------------------------------------------
k.save('jobs',dict(id='d'*32,owner=operator().identity,tool='brain.infer',state='Interrupted',created=time.time(),timeout=120))
w.show_start();settle();page=w._empty_home_page.today;page.fill();settle();align()  # UI-04: the TodayPage inside the Finder
assert w._home_active and w.sim_dock.isVisible() and w.central_stack.currentWidget() is w._empty_home_page
lines=card_lines(page.waiting);assert any('Local model · interrupted' in text for text in lines) and not any(text=='brain.infer' for text in lines),lines
five_visible('home with right column');focus('home')
capture('Ledger_Slate_DESKTOP_01_Frame_06_Home_Right_Column.png','Home after work: Today in the centre, the right column still showing Operations, the typing strip below; the Waiting for you card says the interrupted job in words (Local model · interrupted).')
job=k.record('jobs','d'*32);job.update(state='Cancelled',finished=time.time());k.save('jobs',job)
w.resume_workspace();settle();assert not w._home_active and w.tabs.indexOf(editor)>=0 and editor.document().isModified()
check('Home keeps the right column and names a waiting job in words; leaving Home returns the workspace with the draft intact')
# 11 · compact: 1366 by 768 and 1280 by 720 -----------------------------------------------------------------------------------
compact={};top=w.shell2.top
for size in ((1366,768),(1280,720)):
 w.resize(*size);settle(60);align(3);five_visible('%dx%d'%size)
 buttons=[b for b in w.command_menus.values() if b.isVisible()];visible={b.text().replace('&',''):[b.width(),b.visibleRegion().boundingRect().width()] for b in buttons}
 compact['%dx%d'%size]=dict(widths=widths(),floors=floors(),centre=w.tabs.width(),brand=w.shell2.top.brand_holder.width(),right_holder=w.shell2.top.right_holder.width(),words=visible,
  folded=[h.text() for h in top.folded_menus],ribbon_scroll=w.ribbon_scroll.horizontalScrollBar().maximum())
 assert all(width==shown for width,shown in visible.values()) and w.ribbon_scroll.horizontalScrollBar().maximum()==0,visible  # G-B: a word that would not fit is folded into ⋯, never clipped
 assert len(buttons)+len(top.folded_menus)==len(w.command_menus) and top.more_menus.isVisible()==bool(top.folded_menus) and not ui_fit.whole_words(w.ribbon_dock),(compact['%dx%d'%size],ui_fit.describe(ui_fit.whole_words(w.ribbon_dock)))
 # Every strip word whole (restored, D1-fix: the reach review found this loosened so Kernel could shrink to 'Ke…'): when the
 # workspace's own content needs the room (here a room with a wide minimum), both panes give it up together and the lower
 # band's words are set smaller (desk_qt.letter_floor at the least), never elided; the cat's button holds every pose whole.
 elided_compact=[b for b in bar_words()['secondary'] if b.text()!=bar.words[b]]
 assert whole(bar_words()['primary']) and whole(bar_words()['secondary']) and not elided_compact,(size,w.desk,bar.px,[(b.text(),b.width(),b.sizeHint().width()) for b in bar_words()['primary']+bar_words()['secondary']])
 assert not ui_fit.whole_words(w.type_dock) and w.nav_dock.width()==w.sim_dock.width(),(size,ui_fit.describe(ui_fit.whole_words(w.type_dock)))
 compact['%dx%d'%size]['elided']=[b.text() for b in elided_compact];compact['%dx%d'%size]['workspace_content_minimum']=w.centralWidget().minimumSizeHint().width();compact['%dx%d'%size]['band_words_px']=bar.px
 if size==(1366,768):
  assert w.tabs.width()>=600,w.tabs.width()
  capture('Ledger_Slate_DESKTOP_01_Frame_07_Compact_1366.png','1366 by 768: both panes one width, the centre keeps %d px, every command word whole (they fold into ⋯ before they would scroll), the five parts and the fixed controls visible.'%w.tabs.width())
 else:
  capture('Ledger_Slate_DESKTOP_01_Frame_08_Compact_1280.png','1280 by 720: the top command row keeps Work … Guide whole; the centre keeps %d px.'%w.tabs.width())
w.resize(1920,1200);settle(60);align()
check('At 1366 by 768 and 1280 by 720 every top command word is whole without scrolling and the five parts stay (window minimum 1040 by 640: under the row\'s width the rightmost words fold into ⋯, never clipped or scrolled); every strip word is whole too, the lower band\'s words set at %s px where the room needs it, never elided'%' and '.join(str(compact[k]['band_words_px']) for k in compact))
# 11b · every word whole (G-B): Home at 1920 by 1200, 1366 by 768 and 18 pt; the head folds into ⋯ at 1100 by 700 and 18 pt -----
# (D1a: at 14 pt the eight menu words fit even at 1100 by 700, spilling evenly into both head slots, so the fold is shown at 18 pt)
fits={};w.show_start();settle();align();home=w._empty_home_page;today=home.today
for size,points in (((1920,1200),14),((1366,768),14),((1366,768),18)):
 if points!=14:ui_pt(points)
 w.resize(*size);settle(60);align(3);home.go('today');settle();align()
 clipped,elsewhere=ui_fit.regions(w,w.ribbon_dock,w.central_stack);sideways=ui_fit.side_scrolls(w.central_stack);key='%dx%d %dpt'%(size[0],size[1],points)
 fits[key]=dict(today_columns=today.columns,finder_folded=list(home.folded),head_folded=[h.text() for h in top.folded_menus],clipped=clipped,sideways=sideways,elsewhere=elsewhere)
 assert not clipped and not sideways and not ui_fit.unexplained(elsewhere),(key,ui_fit.describe(clipped+sideways+ui_fit.unexplained(elsewhere)))  # outside the head and the centre only ui_fit.PENDING
 assert today.columns==(2 if size[0]==1920 else 1) and today.scroller.horizontalScrollBar().maximum()==0,fits[key]
 five_visible('fit '+key)
 if size[0]==1366:capture('Ledger_Slate_GRAPHITE_01_Frame_11_Fit_%dpt_1366.png'%points,'Home at %d pt and 1366 by 768: Today in one column, every word in the head and the centre whole (labels and buttons measured against the room the style gives them), nothing in the centre scrolls sideways; the Finder toolbar folds %s into ⋯.'%(points,' · '.join(home.folded) or 'nothing'))
w.resize(1100,700);settle(60);align(3)
head=[b for b in w.command_menus.values() if b.isVisible()];top.fill_more_menus();subs=[a.menu() for a in top.more_menus.menu().actions()]
fits['1100x700 18pt head']=dict(shown=[b.text() for b in head],folded=[h.text() for h in top.folded_menus],ribbon_scroll=w.ribbon_scroll.horizontalScrollBar().maximum())
assert top.folded_menus and top.more_menus.isVisible() and subs==[h.menu() for h in top.folded_menus] and w.ribbon_scroll.horizontalScrollBar().maximum()==0,fits['1100x700 18pt head']
assert all(b.width()==b.visibleRegion().boundingRect().width() for b in head) and not ui_fit.whole_words(w.ribbon_dock),ui_fit.describe(ui_fit.whole_words(w.ribbon_dock))
capture('Ledger_Slate_GRAPHITE_01_Frame_12_Head_Folds_1100.png','1100 by 700 at 18 pt: the head keeps %s whole and folds %s into ⋯ (the same menus, as its rows); nothing scrolls.'%(' · '.join(fits['1100x700 18pt head']['shown']),' · '.join(fits['1100x700 18pt head']['folded'])))
ui_pt(14);sweep={}  # every width from the window's minimum to 1400 in 10 px steps: the head never scrolls and never clips a word or ⋯
for width in range(1040,1401,10):
 w.resize(width,720);settle(20);align(2);words=ui_fit.whole_words(w.ribbon_dock);scroll=w.ribbon_scroll.horizontalScrollBar().maximum()
 sweep[w.width()]=[h.text() for h in top.folded_menus];assert scroll==0 and not words,(width,w.width(),scroll,ui_fit.describe(words))
fits['head sweep 1040-1400 at 720']=dict(widths=len(sweep),folded_at={str(k):v for k,v in sweep.items() if v})
w.resize(1920,1200);settle(60);align(3);assert not top.folded_menus and top.more_menus.isHidden(),[h.text() for h in top.folded_menus]
w.resume_workspace();settle();align();assert not w._home_active and w.tabs.indexOf(editor)>=0
check('Every word in the window whole (outside the head and the centre only the pending bold words) and nothing in the centre sideways at Home at 1920 by 1200 (Today in two columns), 1366 by 768 and 18 pt (one column); at 1100 by 700 and 18 pt the head keeps %s and folds %s into ⋯, whose rows are the same menus; at all %d widths from 1040 to 1400 the head neither scrolls nor clips a word; at 1920 every menu word is back'%(' · '.join(fits['1100x700 18pt head']['shown']),' · '.join(fits['1100x700 18pt head']['folded']),len(sweep)))
# 12 · save and reopen: widths and the frame come back -------------------------------------------------------------------------
setting('layout.navigator_width',420);give=min(60,spare()//3);drag(w.sim_dock,-give);w.save_session();remembered=widths()
saved=dict(w.session.layout);assert saved['navigator_width']==saved['simulator_width']==remembered[0]==remembered[1]==420+give,(saved,remembered,give)  # D1a: one saved width for both
focus('before close');editor.document().setModified(False)
assert w.close() is True;settle();assert not w.desktop_lease.exists()
w2=WorkbenchWindow(root,Session(RUN/'profile/session.json',root),restore=True);w2.resize(1920,1200);w2.show();settle(120);w2.ledger_bridge.timer.stop();w2.type_bar.hatch.lifecycle.timer.stop()
for _ in range(3):w2.type_bar.align();settle()
reopened=[w2.nav_dock.width(),w2.sim_dock.width()];assert reopened==remembered,(reopened,remembered)
five_visible('reopened from the saved session',w2);f=QApplication.focusWidget();focus_log.append(dict(step='reopened',focus=name_of(f)))
assert w2.tabs.indexOf(w2.tabs.currentWidget())>=0 or w2._home_active
capture('Ledger_Slate_DESKTOP_01_Frame_09_Reopened.png','The window reopened from the saved session: both remembered column widths (%d/%d) and the five parts are back.'%tuple(reopened),window=w2)
w2.resize(1366,768);settle(60)
for _ in range(2):w2.type_bar.align();settle()
five_visible('reopened at 1366',w2);capture('Ledger_Slate_DESKTOP_01_Frame_10_Reopened_1366.png','The reopened window at 1366 by 768.',window=w2)
assert w2.close() is True;settle()
launcher.assert_not_called();provider.assert_not_called();submission.assert_not_called();popen.assert_not_called();system.assert_not_called();detached.assert_not_called()
assert all(r['state'] in ('Completed','Cancelled','Failed') for r in k.listing('jobs'))
check('Save and reopen restore the one remembered pane width on both sides and the five parts; clean close with zero job, worker, model, provider, native or OS session activity')
result=dict(state='PASSED',mode='ACTUAL_QT_OFFSCREEN',checks=checks,captures=captures,
 fresh_floors=fresh_floors,fresh_widths=fresh_widths,excursion={str(key):value for key,value in excursion.items()},strip_heights={str(key):value for key,value in heights.items()},
 elided_at_28pt=elided,compact=compact,words_whole=fits,tab_strip_y=ys,tab_order_from_hatch=walk,focus_observed=focus_log,areas_observed=areas_log,
 column_policy=dict(desk='one width for both panes (workbench/desk_qt.py; tools/check_desk_ui.py measures the mirror image)',pane_px_at_14pt=desk_qt.PANE,
  centre_floor_px_at_14pt=desk_qt.CENTRE,scale_max=desk_qt.SCALE_MAX,
  elision='the cat and the four modes stay whole (D3); Line/Half/Tall share the room left in the slot, whole word in the tooltip',
  status_message_ceiling_ms=typebar_qt.NOTE_MS,window_minimum=[w2.minimumWidth(),w2.minimumHeight()]),
 disposable_job_records=1,jobs_submitted=0,worker_processes_started=0,model_generations=0,provider_requests=0,native_invocations=0,
 os_power_or_logout_commands=0,owner_host_acceptance=False,clean_close=True)
(OUT/'frame-ui.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)
for guard in (question,detached,system,popen,submission,launcher,provider):guard.stop()
