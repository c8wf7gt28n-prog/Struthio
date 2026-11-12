"""Actual Qt checks for the paper vocabulary, prose font, writing marker and editors (HATCH DESKTOP-01, WI-3; VS01, VS03, AC15 mechanical parts).

A disposable PROJECT workspace and profile; Kernel.launch, Kernel.submit and the provider request are held; after the window
exists no process, shell command or detached program may start. Captures are real offscreen grabs (whole window and crops) with
sha256 and resolution at 1920x1200 and 1366x768. The marker phases are forced before each grab and the caret flash is disabled
in this process only, so every grab is deterministic (MK-13). Nothing here is owner-host acceptance.
"""
import hashlib,json,os,platform,subprocess,sys,tempfile,time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
PROGRAM=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('ARC_LEDGER_PAPER_CAPTURE_DIR',str(PROGRAM/'build/ui_checks/paper')));OUT.mkdir(parents=True,exist_ok=True)
RUN=Path(tempfile.mkdtemp(prefix='ledger-desktop01-paper-ui-'))
os.environ.update(QT_QPA_PLATFORM='offscreen',ARC_LEDGER_EMBEDDED='1',ARC_LEDGER_DISABLE_BOOK_WATCHER='1',
 ARC1_WORKBENCH_CONFIG_HOME=str(RUN/'profile'),ARC_LEDGER_CONCERN=str(RUN/'Concern'))
os.environ.pop('ARC_LEDGER_XSESSION',None)
sys.path.insert(0,str(PROGRAM));sys.dont_write_bytecode=True
from PySide6.QtCore import Qt,QPoint,QRect,QProcess
from PySide6.QtGui import QPainter,QTextCursor,QAccessible
from PySide6.QtWidgets import QApplication,QMessageBox,QDialog
from PySide6.QtTest import QTest
from workbench.qt_app import make_app,WorkbenchWindow
from workbench import locations,clip,ledger_control,settings_registry,reading_preferences,writing_marker,project_desk_qt,cabinet_actions_qt
from workbench.engineering_kernel import Kernel,operator
from workbench.session import Session
from workbench.shell2 import capture_dialog,AMBER,ERASER_DEEP,TEXT
from workbench.hardware_settings_qt import ViewModes,pane_keys
provider=patch.object(clip,'_request',side_effect=AssertionError('No provider request')).start()
launch=patch.object(Kernel,'launch',side_effect=AssertionError('No job launch')).start()
submission=patch.object(Kernel,'submit',side_effect=AssertionError('No job submission')).start()
question=patch.object(QMessageBox,'question',return_value=QMessageBox.Yes).start()
app=make_app([]);root=locations.ensure_workspace(RUN/'workspace',kind='PROJECT',name='Paper vocabulary check');locations.arrived(root,create=True)
session=Session(RUN/'profile/session.json',root)
FLASH=app.cursorFlashTime();app.setCursorFlashTime(0)  # this process only: a caret that does not blink, so grabs are deterministic
w=WorkbenchWindow(root,session,restore=False);bridge=w.ledger_bridge;k=bridge.kernel;checks=[];captures=[];measure={}
platform.processor()  # Python answers the processor probe once through uname and remembers it; from here no process may start
popen=patch.object(subprocess,'Popen',side_effect=AssertionError('No process start')).start()
system=patch.object(os,'system',side_effect=AssertionError('No shell command')).start()
detached=patch.object(QProcess,'startDetached',side_effect=AssertionError('No detached program')).start()
KEY=settings_registry.WRITING_MARKER_KEY;VIEWS=settings_registry.VIEW_MODES_KEY;controller=w.writing_marker
def settle(wait=25):
 for name in ('agenda_runner','study_idle'):
  obj=getattr(w,name,None)
  if obj and hasattr(obj,'timer'):obj.timer.stop()
 for _ in range(2):app.processEvents();QTest.qWait(wait)
def call(op,args=None):
 result=k.dispatch(op,args or {},operator());assert result['ok'],result;return result['result']
def row(key=KEY):return next(r for r in call('ledger.settings')['settings'] if r['key']==key)
def journal(key):return call('ledger.settings.history',{'key':key})['changes']
def check(text):checks.append(text);print(text,flush=True)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def capture(name,note,*popups,crop=None):
 w.operations_panel.refresh();settle();pix=w.grab();mode='ACTUAL_QT_WINDOW_GRAB';painter=QPainter(pix)
 for popup in popups:
  assert popup.isVisible();pos=w.mapFromGlobal(popup.mapToGlobal(QPoint(0,0)));painter.drawPixmap(pos,popup.grab());mode='ACTUAL_QT_WINDOW_AND_VISIBLE_POPUP_GRABS'
 painter.end()
 if crop is not None:pix=pix.copy(crop.intersected(w.rect()));mode+='_CROP'
 target=OUT/name;assert pix.save(str(target),'PNG')
 captures.append(dict(file=name,note=note,mode=mode,sha256=sha(target),resolution=[w.width(),w.height()],crop=[crop.x(),crop.y(),crop.width(),crop.height()] if crop else None))
def rect_in(widget):return QRect(widget.mapTo(w,QPoint(0,0)),widget.size())
def image():return w.grab().toImage()
def dominant(img,rect):
 counts={}
 for y in range(rect.top(),rect.bottom()+1,2):
  for x in range(rect.left(),rect.right()+1,2):
   name=img.pixelColor(x,y).name();counts[name]=counts.get(name,0)+1
 total=sum(counts.values());top=max(counts,key=counts.get);return top,round(counts[top]/total,3)
def ink(img,rect):
 n=0
 for y in range(rect.top(),rect.bottom()+1):
  for x in range(rect.left(),rect.right()+1):
   c=img.pixelColor(x,y)
   if (c.red()+c.green()+c.blue())/3<150:n+=1
 return n
def has_colour(img,rect,colour):
 for y in range(rect.top(),rect.bottom()+1):
  for x in range(rect.left(),rect.right()+1):
   if img.pixelColor(x,y).name()==colour:return True
 return False
def focus(widget):
 top=widget.window();top.activateWindow();QApplication.setActiveWindow(top);app.processEvents();widget.setFocus(Qt.OtherFocusReason);settle(5)
 assert widget.hasFocus(),('focus did not land',widget.objectName(),QApplication.focusWidget())
def select_record(ident):
 page=w.cabinet_page;page.refresh(force=True);settle();page.select(ident,reveal=True);settle()
 item=page.items[ident];QTest.mouseClick(page.tree.viewport(),Qt.LeftButton,pos=page.tree.visualItemRect(item).center());settle()
 room=w.tabs.currentWidget();assert getattr(room,'current',None)==ident,(type(room).__name__,getattr(room,'current',None));return room
def set_reading(**changes):
 rows={r['key']:r for r in ledger_control.settings(k,'Appearance')['settings']}
 batch=[dict(key='reading.'+key,value=value,expected_revision=rows['reading.'+key]['revision']) for key,value in changes.items() if rows['reading.'+key]['value']!=value]
 if batch:call('ledger.settings.apply',{'changes':batch})
 bridge.sync_profile(force=True);settle(40);return dict(w.reading_profile)
def passage_colours(widget,label,ms=3000,reveal=None):
 """The passage is painted yellow, without a box border, over the part of it a person sees (its visible region: a scroll
 viewport clips the rest). Measured until it holds or ms pass: under load a resize's relayout can land after the passage
 was scrolled into view, so `reveal` (scroll it into view) runs again before each reading. A wrong colour still fails."""
 end=time.monotonic()+ms/1000;tries=0
 while True:
  tries+=1
  if reveal:reveal();app.processEvents()
  img=image();seen=widget.visibleRegion().boundingRect();r=QRect(widget.mapTo(w,seen.topLeft()),seen.size()).intersected(w.rect().adjusted(0,0,-1,-1))
  if r.height()>20:
   colour,share=dominant(img,r)
   edges=[img.pixelColor(r.left()+1,r.center().y()).name(),img.pixelColor(r.right()-1,r.center().y()).name(),img.pixelColor(r.center().x(),r.top()+1).name()]
   if colour==AMBER and share>=0.6 and all(e==AMBER for e in edges):break
  if time.monotonic()>end:break
  app.processEvents();QTest.qWait(30)
 assert r.height()>20,(label,'passage not in view')
 measure.setdefault('passages',{})[label]=dict(dominant=colour,share=share,edges=edges,rect=[r.x(),r.y(),r.width(),r.height()],widget_rect=[*rect_in(widget).getRect()],reads=tries)
 assert colour==AMBER and share>=0.6,(label,colour,share);assert all(e==AMBER for e in edges),(label,edges)  # yellow passage, no box border
 return r
w.resize(1920,1200);w.show();settle();bridge.timer.stop()
if hasattr(w.type_bar,'hatch') and hasattr(w.type_bar.hatch,'lifecycle'):w.type_bar.hatch.lifecycle.timer.stop()
assert KEY in settings_registry.BY_KEY and 'setting:'+KEY in w.settings_navigator.items and controller is bridge.marker
# Session.load reads the marker field: a saved False is what a fresh Session sees.
probe=Session(RUN/'profile/loader-probe.json');probe.state['writing_marker']=False;probe.save();assert Session(RUN/'profile/loader-probe.json').state.get('writing_marker') is False
project=call('projects.create',{'title':'Paper workshop','intent':'Write on yellow passages with a quiet mark in the margin.'})
# 1. Writable passages (VS01, V-02): cabinet title and writing, New Idea sheet (dialog and Home), Project Desk title; selection visible.
form_id='catalog:projects' if 'catalog:projects' in w.cabinet_page.items else 'cabinet:projects'
form=select_record(form_id);assert form.new_title.isVisible() and form.writing.isVisible()
focus(form.writing);QTest.keyClicks(form.writing,'Keep the work visible while we choose');QTest.keyClick(form.writing,Qt.Key_Return);QTest.keyClicks(form.writing,'its next instrument.');settle()
passage_colours(form.writing,'cabinet_writing');passage_colours(form.new_title,'cabinet_title')
form.writing.selectAll();settle();assert has_colour(image(),rect_in(form.writing),ERASER_DEEP),'selection on the yellow passage is not visible'
cursor=QTextCursor(form.writing.document());cursor.movePosition(QTextCursor.End);form.writing.setTextCursor(cursor);settle()
assert form.writing.property('writingMark') and form.new_title.property('writingMark') and form.writing.property('arcReadingRole')=='prose'
controller.set_phase(True);settle()
capture('Ledger_Slate_HATCH_Desktop_01_Paper_01_Cabinet_Writing_1920.png','The project form in the cabinet record room: title line and writing passage are yellow passages without box borders; the graphite X sits in the page margin on the caret line of the focused passage.')
dialog=capture_dialog(w);settle(30);sheet=dialog.sheet.text;focus(sheet);QTest.keyClicks(sheet,'A rough idea, kept as written.');settle()
img=dialog.grab().toImage();r=QRect(sheet.mapTo(dialog,QPoint(0,0)),sheet.size());colour,share=dominant(img,r)
measure['passages']['new_idea_sheet']=dict(dominant=colour,share=share,edge=img.pixelColor(r.left()+1,r.center().y()).name())
assert colour==AMBER and share>=0.6 and img.pixelColor(r.left()+1,r.center().y()).name()==AMBER,(colour,share)
assert sheet.property('writingMark') and controller.mark_for(sheet) is not None and controller.mark_for(sheet).page is dialog
controller.set_phase(True);settle();mark=controller.mark_for(sheet);mr=mark.mark_rect();sheet_ink=ink(dialog.grab().toImage(),mr)
assert sheet_ink>10,('no X beside the New Idea sheet',dict(ink=sheet_ink,rect=[mr.x(),mr.y(),mr.width(),mr.height()],visible=mark.visible(),focus=sheet.hasFocus(),
 focus_widget=QApplication.focusWidget().objectName() if QApplication.focusWidget() else None,active_window=type(QApplication.activeWindow()).__name__,
 focused_mark=controller.focused().widget.objectName() if controller.focused() else None,stats=controller.stats(),dialog_size=[dialog.width(),dialog.height()]))
pix=dialog.grab();target=OUT/'Ledger_Slate_HATCH_Desktop_01_Paper_02_New_Idea_Sheet_1920.png';assert pix.save(str(target),'PNG')
captures.append(dict(file=target.name,note='The Jot it down sheet (Hatch New Idea, Ctrl+Shift+N): a yellow passage with a bottom rule on focus, no card border; the X in the dialog margin.',mode='ACTUAL_QT_DIALOG_GRAB',sha256=sha(target),resolution=[dialog.width(),dialog.height()]))
dialog.reject();settle()
# Home's Jot it down sheet is the same CaptureBox (detached workspaces only; this check attaches a project for the hardware editor).
desk=project_desk_qt.show(w);settle();passage_colours(desk.project_title,'project_desk_title')
assert desk.project_title.objectName()=='ProjectTitle' and desk.project_title.placeholderText()=='poem'
calc=desk.problem_pane.calculator
assert all(f.placeholderText()=='poem' for f in (calc.expression,calc.assumptions,calc.start,calc.stop)) and calc.examples.accessibleName() and calc.backend.accessibleName()
capture('Ledger_Slate_HATCH_Desktop_01_Paper_04_Project_Desk_1920.png','Project Desk (Hatch New Project): the title line is a yellow passage; the heading words sit on their own row.')
assert 'QPlainTextEdit#SlateInput' in __import__('workbench.theme2',fromlist=['QSS2']).QSS2.split('Writable passages')[1]
check('The cabinet title and writing, the New Idea sheet and the Project Desk title are yellow passages with no box border, visible eraser-pink selection and the poem hint; the Slate composer and Home sheet share the theme rule')
# 2. Prose font (V-03) with adjust_prose: the written passages follow the prose family and size, the JSON viewers stay code.
room=select_record('project:'+project['id']);profile=dict(w.reading_profile)
prose_family=reading_preferences.family(profile['prose_family']);code_family=reading_preferences.family(profile['code_family'],True)
assert (room.writing.font().family(),round(room.writing.font().pointSizeF(),1))==(prose_family,profile['prose_pt']),(room.writing.font().family(),room.writing.font().pointSizeF())
assert (room.body.font().family(),round(room.body.font().pointSizeF(),1))==(prose_family,profile['prose_pt'])
assert room.detail.font().family()==code_family and round(room.detail.font().pointSizeF(),1)==profile['code_pt']
reading_preferences.adjust_prose(w,2);settle(40)
assert round(room.writing.font().pointSizeF(),1)==profile['prose_pt']+2 and round(room.body.font().pointSizeF(),1)==profile['prose_pt']+2
assert round(room.detail.font().pointSizeF(),1)==profile['code_pt'] and room.detail.font().family()==code_family
measure['prose']=dict(family=prose_family,size_before=profile['prose_pt'],size_after=room.writing.font().pointSizeF(),code_family=code_family)
reading_preferences.adjust_prose(w,-2);settle(40);assert round(room.writing.font().pointSizeF(),1)==profile['prose_pt']
thread=w.return_thread.show();settle();assert thread.writing.property('arcReadingRole')=='prose' and thread.writing.font().family()==prose_family and thread.writing.property('writingMark')
check('Cabinet writing, the saved record body and the return thread render in the prose family at reading.prose_pt and follow adjust_prose; the JSON viewers stay in the code font')
# 3. The writing marker (VS03, MK-01…MK-13): forced phases, pixel measurement, caret line, focus, reduce motion, the setting, 200 %.
w.tabs.setCurrentWidget(room);settle();focus(room.writing);room.writing.setPlainText('Keep the work visible while we choose\nits next instrument.')
cursor=QTextCursor(room.writing.document());cursor.movePosition(QTextCursor.End);room.writing.setTextCursor(cursor);settle()
mark=controller.mark_for(room.writing);assert mark is not None and controller.focused() is mark and controller.timer.isActive() and controller.timer.interval()==1000
controller.set_phase(True);settle();on_img=image();mr=mark.mark_rect();page_rect=QRect(mark.page.mapTo(w,mr.topLeft()),mr.size());passage=rect_in(room.writing)
controller.set_phase(False);settle();off_img=image()
on_ink,off_ink=ink(on_img,page_rect),ink(off_img,page_rect)
assert on_ink>20 and off_ink==0,(on_ink,off_ink)
assert mark.page is room.writing.parentWidget(),type(mark.page).__name__  # drawn on the cabinet page itself, never on an outer ancestor
assert page_rect.right()<passage.left() and on_img.copy(passage)==off_img.copy(passage),'the passage must be pixel-identical in both phases'
caret=QRect(room.writing.viewport().mapTo(w,room.writing.cursorRect().topLeft()),room.writing.cursorRect().size())
measure['marker']=dict(mark_rect=[page_rect.x(),page_rect.y(),page_rect.width(),page_rect.height()],caret_rect=[caret.x(),caret.y(),caret.width(),caret.height()],
 ink_on=on_ink,ink_off=off_ink,glyph_px=mark.glyph(),form=mark.form,clear_of_passage_px=passage.left()-page_rect.right()-1,page=type(mark.page).__name__,
 centre_offset_from_caret_centre=page_rect.center().y()-caret.center().y(),a11y_children_of_page=QAccessible.queryAccessibleInterface(mark.page).childCount())
assert abs(measure['marker']['centre_offset_from_caret_centre'])<=3
controller.set_phase(True);settle()
capture('Ledger_Slate_HATCH_Desktop_01_Paper_05_Marker_On_1920.png','Marker shown phase (forced): the graphite X in the cabinet page margin on the caret line; caret flash disabled in this check.')
capture('Ledger_Slate_HATCH_Desktop_01_Paper_05b_Marker_On_crop.png','Crop of the writing passage with the X shown.',crop=passage.adjusted(-60,-20,20,20))
controller.set_phase(False);settle()
capture('Ledger_Slate_HATCH_Desktop_01_Paper_06_Marker_Off_Phase_1920.png','Marker hidden phase (forced): the margin is empty; the caret alone shows the insertion point.')
capture('Ledger_Slate_HATCH_Desktop_01_Paper_06b_Marker_Off_crop.png','Crop of the writing passage with the X hidden.',crop=passage.adjusted(-60,-20,20,20))
cursor.movePosition(QTextCursor.Start);room.writing.setTextCursor(cursor);settle();controller.set_phase(True);settle();line1=mark.mark_rect()
assert line1.center().y()<mr.center().y() and ink(image(),QRect(mark.page.mapTo(w,line1.topLeft()),line1.size()))>20
assert select_record(form_id) is room and room.new_title.isVisible()  # the projects form: the same room with its title line shown
focus(room.new_title);controller.set_phase(True);settle();title_mark=controller.mark_for(room.new_title)
assert not mark.visible() and title_mark.visible(),(mark.visible(),title_mark.visible())
writing_slot=mark.mark_rect();title_slot=title_mark.mark_rect();img=image()  # the writing passage's margin slot is empty while the title line carries the X
assert ink(img,QRect(mark.page.mapTo(w,writing_slot.topLeft()),writing_slot.size()))==0 and ink(img,QRect(mark.page.mapTo(w,title_slot.topLeft()),title_slot.size()))>10,(writing_slot,title_slot)
focus(room.writing);cursor=QTextCursor(room.writing.document());cursor.movePosition(QTextCursor.End);room.writing.setTextCursor(cursor);settle()
check('The X is drawn in the page margin beside the focused passage only, follows the caret line, blinks with a 1 s half-period while focused, and leaves the passage pixel-identical between phases; the page gains no accessible child')
# reduce motion wins: static X, no timer, zero repaints over eight ticks
set_reading(reduce_motion=True);assert w.reading_profile['reduce_motion'] is True
assert not controller.timer.isActive() and controller.on and mark.visible(),controller.stats()
paints=controller.stats()['page_paints']
for _ in range(8):controller.tick();app.processEvents()
assert controller.stats()['page_paints']==paints and controller.on and not controller.timer.isActive()
assert controller.readback()['motion']=='static'
bridge.publish_settings_readback();r=row();assert r['application_state']=='APPLIED' and r['effective'] is True and 'static' in r['effective_source'],r
capture('Ledger_Slate_HATCH_Desktop_01_Paper_07_Marker_Static_Reduce_Motion_1920.png','reading.reduce_motion on (set through ledger.settings.apply): the X stands still, no timer runs; readback APPLIED with motion static.')
set_reading(reduce_motion=False);assert controller.timer.isActive()
measure['reduce_motion']=dict(ticks_without_repaint=8,readback=r['effective_source'])
check('Under reading.reduce_motion the X is static with no timer and zero repaints over eight ticks; the setting still reads APPLIED with motion static')
# the setting: Off hides the mark immediately through sync_profile; readback is a controller receipt; Undo brings it back
before_journal=len(journal(KEY));change=call('ledger.settings.set',dict(key=KEY,value=False,expected_revision=row()['revision']))
bridge.sync_profile(force=True);settle();disk=json.loads(session.path.read_text()).get('writing_marker')
assert disk is False and len(journal(KEY))==before_journal+1
assert not controller.enabled and not mark.visible() and ink(image(),QRect(mark.page.mapTo(w,mr.topLeft()),mr.size()))==0
bridge.publish_settings_readback();r=row();assert (r['stored'],r['effective'],r['application_state'])==(False,False,'APPLIED'),r
assert 'off on' in r['effective_source'] and r['desktop_effects'][0]['passages']>=4
call('ledger.settings.undo',dict(id=change['id']));bridge.sync_profile(force=True);settle()
assert controller.enabled and json.loads(session.path.read_text()).get('writing_marker') is True
bridge.publish_settings_readback();r=row();assert (r['stored'],r['effective'],r['application_state'])==(True,True,'APPLIED'),r
check('appearance.writing_marker Off reaches the controller on the next profile sync, hides the X and reads back APPLIED with motion off; Undo restores it; the Session field holds the value')
# 200 %: the glyph scales with the passage font; the X never enters the passage (narrow form on a fixed margin)
set_reading(ui_pt=28.0,prose_pt=32.0,code_pt=28.0,navigation_pt=28.0);w.tabs.setCurrentWidget(room);settle();room.scroll.ensureWidgetVisible(room.writing,40,60);settle();focus(room.writing)
cursor=QTextCursor(room.writing.document());cursor.movePosition(QTextCursor.End);room.writing.setTextCursor(cursor);settle();controller.set_phase(True);settle()
big=mark.mark_rect();edge=mark.page_child.mapTo(mark.page,QPoint(0,0)).x()
measure['marker_200pct']=dict(glyph_px=mark.glyph(),form=mark.form,clamped=mark.clamped,page_margin_px=edge,mark_rect=[big.x(),big.y(),big.width(),big.height()],clear_px=edge-big.right()-1)
assert mark.page is room.writing.parentWidget() and mark.form=='narrow' and edge<=24,measure['marker_200pct']  # still the cabinet page, X shrunk to its margin
assert mark.glyph()>=20 and big.right()<edge and ink(image(),QRect(mark.page.mapTo(w,big.topLeft()),big.size()))>10,measure['marker_200pct']
capture('Ledger_Slate_HATCH_Desktop_01_Paper_08_Marker_200pct_1920.png','Interface 28 pt, prose 32 pt (200 %): the X scales with the passage font; on the fixed 22 px page margin it shrinks to the margin (narrow form) and never enters the passage.')
set_reading(ui_pt=14.0,prose_pt=16.0,code_pt=14.0,navigation_pt=15.0);settle(40)
check('At 200 % the X scales with the passage font and, on a page margin narrower than its strip, shrinks to the margin instead of entering the passage (recorded as the narrow form)')
# 4. Hardware category views editor (V-08, ACC-06, ACC-07, ACC-10): one frame that follows its rows up to a scaled cap, keyboard-only change.
tab=bridge.show_settings(key=VIEWS);settle();vm=tab.view_modes;assert tab.editors.currentWidget() is vm and len(vm.combos)>50
assert vm.scroll.height()==vm.frame_cap()==320 and vm.scroll.verticalScrollBar().isVisible() and vm.scroll.focusPolicy()==Qt.NoFocus
assert all(line.maximumWidth()==vm.row_width()==720 for line in vm.lines)
assert all(c.accessibleName().endswith(' view') and c.accessibleDescription()==c.currentText() for c in vm.combos.values())
first_key=next(iter(vm.combos));focus(vm.first_combo);QTest.keyClick(vm.first_combo,Qt.Key_Down);settle()
assert vm.first_combo.currentText()=='Details' and vm.first_combo.accessibleDescription()=='Details' and VIEWS in tab.drafts
stops=0;seen=[]
while stops<len(vm.combos)+5:
 QTest.keyClick(app.focusWidget(),Qt.Key_Tab);settle(5);stops+=1;current=app.focusWidget();seen.append(current.accessibleName())
 if current is tab.apply_button:break
assert app.focusWidget() is tab.apply_button and stops==len(vm.combos),(stops,len(vm.combos),seen[-3:])
assert all(name.endswith(' view') for name in seen[:-1]),seen[:3]
measure['hardware']=dict(combos=len(vm.combos),tab_stops_from_first_combo_to_apply=stops,frame_height=vm.scroll.height(),frame_cap=vm.frame_cap(),row_width=vm.row_width())
before=len(journal(VIEWS));QTest.keyClick(tab.apply_button,Qt.Key_Space);settle()
assert len(journal(VIEWS))==before+1 and row(VIEWS)['stored']=={first_key:'Details'} and 'Saved '+VIEWS in tab.note.text()
tab.scroll.verticalScrollBar().setValue(0);settle()
capture('Ledger_Slate_HATCH_Desktop_01_Paper_09_Hardware_Editor_1920.png','Hardware category views editor after a keyboard-only change (Down on the first pane, Tab through the panes to Apply, Space): one frame at the 320 px cap, rows within 720 px, one scrollbar.')
set_reading(ui_pt=28.0);settle(40);assert vm.scroll.height()==vm.frame_cap()==640 and tab.editors.height()>=vm.scroll.height(),(vm.scroll.height(),tab.editors.height())
measure['hardware']['frame_height_at_28pt']=vm.scroll.height();set_reading(ui_pt=14.0);settle(40);assert vm.scroll.height()==320
empty=ViewModes(SimpleNamespace(root=root,_nav_devices=set(),reading_profile=w.reading_profile),lambda *a:None);empty.configure(None,{});empty.show();settle()
assert empty.scroll.height()<120 and empty.scroll.verticalScrollBarPolicy()==Qt.ScrollBarAlwaysOff and not empty.combos;measure['hardware']['no_navigator_frame_height']=empty.scroll.height();empty.close()
check('The hardware editor frame follows its rows up to a cap that scales with the interface size (320 px at 14 pt, 640 at 28 pt) and collapses to its sentence with no navigator; Tab runs pane by pane into Apply; every combo is named <device> / <group> view with the mode as its description; a keyboard-only change journals once')
# 5. Small presentation fixes: Service details room, Brain words, record-menu heading, the Logical cabinet word, the leave dialog.
w.a_host_service.trigger();settle();panel=w.tabs.currentWidget();assert type(panel).__name__=='HostPanel' and panel.title()=='Service details'
assert not panel.words['Reconnect'].isVisible() and not panel.words['Stop service…'].isVisible() and panel.words['Master Stop…'].isVisible()
assert panel.words['Refresh'].width()<=panel.words['Refresh'].sizeHint().width()+4,(panel.words['Refresh'].width(),panel.words['Refresh'].sizeHint().width())
capture('Ledger_Slate_HATCH_Desktop_01_Paper_10_Service_Details_1920.png','Service details: one name, words at their own width, the two host-client controls absent in the embedded desktop.')
brain=bridge.show_brain();settle();assert brain.status.text().startswith('no model selected') and not brain.progress.isTextVisible(),brain.status.text()
popup=cabinet_actions_qt.menu(w,'project:'+project['id'],w.cabinet_page.tree)
assert popup.heading.text().startswith('With ') and not popup.heading.isEnabled() and popup.heading.font().italic() and popup.actions()[1].isSeparator()
logical=w.cabinet_page.logical;assert logical.width()>=logical.fontMetrics().horizontalAdvance(logical.text())+10,(logical.width(),logical.fontMetrics().horizontalAdvance(logical.text()))
leave=w.return_thread.exit_dialog();leave.show();settle()
assert leave.keep_button.width()<=leave.keep_button.sizeHint().width()+4 and leave.back_button.hasFocus();leave.reject();settle()
check('Service details keeps one name with inert controls hidden, the Brain room says no model selected in words, the record menu opens with a visible italic heading, the Logical cabinet word is whole, and the leave dialog shows its actions as words')
# 6. Compact 1366x768: the same passages, the hardware editor and the Project Desk header.
w.resize(1366,768);settle();room=select_record('project:'+project['id']);room.scroll.ensureWidgetVisible(room.writing,40,60);settle();focus(room.writing);controller.set_phase(True);settle()
passage_colours(room.writing,'cabinet_writing_1366',reveal=lambda:room.scroll.ensureWidgetVisible(room.writing,40,60))
capture('Ledger_Slate_HATCH_Desktop_01_Paper_11_Cabinet_Writing_1366.png','1366x768: the cabinet writing passage with the X in the margin.')
tab=bridge.show_settings(key=VIEWS);settle();assert tab.view_modes.scroll.height()==320
capture('Ledger_Slate_HATCH_Desktop_01_Paper_12_Hardware_Editor_1366.png','1366x768: the hardware editor keeps one frame at the cap and rows within 720 px.')
desk=project_desk_qt.show(w);settle()
assert all(b.width()>=b.sizeHint().width() for b in desk.heading_words) and desk.heading_label.width()>=desk.heading_label.sizeHint().width(),[(b.text(),b.width(),b.sizeHint().width()) for b in desk.heading_words]
measure['project_desk_1366']=[(b.text(),b.width(),b.sizeHint().width()) for b in desk.heading_words]
capture('Ledger_Slate_HATCH_Desktop_01_Paper_13_Project_Desk_1366.png','1366x768: the Project Desk heading on its own line and its three words whole on the row below (V-07).')
check('At 1366x768 the passages, the hardware editor and the Project Desk header hold: no clipped heading word')
# 7. Discipline and a clean close.
enum=ledger_control.FIELDS['ledger.settings.apply'][0]['changes']['items']['properties']['key']['enum'];assert KEY not in enum and set(enum)==set(settings_registry.SESSION_BATCH_KEYS)
assert k.listing('jobs')==[];launch.assert_not_called();submission.assert_not_called();provider.assert_not_called();popen.assert_not_called();system.assert_not_called();detached.assert_not_called()
app.setCursorFlashTime(FLASH);assert w.close() is True;settle();assert not w.desktop_lease.exists()
check('The public batch enum stays 17 keys; clean close removes the desktop lease; zero jobs, workers, model generations, provider requests, native tools, processes or shell commands')
for guard in (question,detached,system,popen,submission,launch,provider):guard.stop()
result=dict(state='PASSED',mode='ACTUAL_QT_OFFSCREEN',settings_count=len(settings_registry.SPECS),setting=KEY,checks=checks,captures=captures,measurements=measure,
 cursor_flash_time_default_ms=FLASH,queued_job_submissions=0,all_kernel_launchers_held=True,worker_processes_started=0,model_generations=0,
 provider_requests=0,native_invocations=0,processes_started=0,owner_host_acceptance=False,clean_close=True)
(OUT/'paper-ui.json').write_text(json.dumps(result,indent=2,default=str)+'\n');print(json.dumps(result,indent=2,default=str),flush=True)
