"""Actual Qt navigation checks across the cabinet and Settings, with numbered captures; no inference or jobs. Kernel.launch,
Kernel.submit, the provider request and OS priority changes are held."""
import copy,hashlib,json,os,sys,tempfile
from pathlib import Path
from unittest.mock import patch
PROGRAM=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('ARC_LEDGER_NAVIGATION_CAPTURE_DIR',str(PROGRAM/'build/ui_checks/navigation')));OUT.mkdir(parents=True,exist_ok=True)
RUN=Path(tempfile.mkdtemp(prefix='ledger-navigation01-ui-'))
os.environ.update(QT_QPA_PLATFORM='offscreen',ARC_LEDGER_EMBEDDED='1',ARC_LEDGER_DISABLE_BOOK_WATCHER='1',
 ARC1_WORKBENCH_CONFIG_HOME=str(RUN/'profile'),ARC_LEDGER_CONCERN=str(RUN/'Concern'))
sys.path.insert(0,str(PROGRAM));sys.dont_write_bytecode=True
from PySide6.QtCore import Qt,QPoint
from PySide6.QtGui import QPainter
from PySide6.QtTest import QTest
from workbench.qt_app import make_app,WorkbenchWindow
from workbench import locations,clip,explore_qt,menus2
from workbench.engineering_kernel import operator,Kernel
from workbench.session import Session
provider=patch.object(clip,'_request',side_effect=AssertionError('No provider request')).start()
submission=patch.object(Kernel,'submit',side_effect=AssertionError('No job submission')).start()
from workbench import session_power  # D2-fix: the one session and power function is held for the whole run, on any computer
def held_power(request):
 """logind answers that there is no login session; no session or power command may start."""
 if request[0]=='logind':raise OSError('no login session (held by this check)')
 raise AssertionError('No session or power command: %r'%(request,))
held_logind=patch.object(session_power,'system',side_effect=held_power).start()
launcher=patch.object(Kernel,'launch',side_effect=AssertionError('No worker launch')).start()
priority=patch('os.setpriority',side_effect=AssertionError('No OS priority change')).start()
app=make_app([]);root=locations.office(RUN/'workspace');session=Session(RUN/'profile/session.json',root)
w=WorkbenchWindow(root,session,restore=False);bridge=w.ledger_bridge;k=bridge.kernel;checks=[];captures=[]
def settle():
 for name in ('agenda_runner','study_idle'):
  obj=getattr(w,name,None)
  if obj and hasattr(obj,'timer'):obj.timer.stop()
 for _ in range(2):app.processEvents();QTest.qWait(25)
def call(op,args=None):
 value=k.dispatch(op,args or {},operator());assert value['ok'],value;return value['result']
def check(text):checks.append(text);print(text,flush=True)
def capture(number,slug,title,note,popup=None):
 w.operations_panel.refresh();settle();pixmap=w.grab();mode='WINDOW_GRAB'
 if popup is not None:
  assert popup.isVisible();pos=w.mapFromGlobal(popup.pos());assert pos.x()>=0 and pos.y()>=0
  assert pos.x()+popup.width()<=w.width() and pos.y()+popup.height()<=w.height()
  painter=QPainter(pixmap);painter.drawPixmap(pos,popup.grab());painter.end();mode='WINDOW_AND_LIVE_POPUP_GRABS'
 name='Ledger_Slate_HATCH_Navigation_01_'+str(number).zfill(2)+'_'+slug+'.png';p=OUT/name
 assert pixmap.save(str(p),'PNG')
 captures.append(dict(number=number,file=name,title=title,note=note,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
                      resolution=[w.width(),w.height()],capture_mode=mode))
def menu_capture(number,slug,title,note,menu,anchor):
 menu.ensurePolished();menu.adjustSize();size=menu.sizeHint();point=anchor.mapTo(w,anchor.rect().bottomLeft())
 if anchor is w.cabinet_page.tree:
  point=anchor.viewport().mapTo(w,anchor.visualItemRect(anchor.currentItem()).center())
 x=min(max(8,point.x()),w.width()-size.width()-8)
 y=point.y() if point.y()+size.height()+8<=w.height() else max(8,point.y()-anchor.height()-size.height())
 pos=w.mapToGlobal(QPoint(x,y));menu.popup(pos);menu.move(pos);settle()
 capture(number,slug,title,note,menu);menu.hide();settle()
def select_record(ident):
 page=w.cabinet_page;page.select(ident,reveal=True);settle()
 item=page.items[ident];QTest.mouseClick(page.tree.viewport(),Qt.LeftButton,pos=page.tree.visualItemRect(item).center());settle()
 room=w.tabs.currentWidget();assert room.current==ident;return room
def current_id():return w.cabinet_page.tree.currentItem().data(0,Qt.UserRole)['id']
def explorer_select(tab,ident):
 for index in range(tab.results.topLevelItemCount()):
  item=tab.results.topLevelItem(index)
  if item.data(0,Qt.UserRole)['id']==ident:tab.results.setCurrentItem(item);settle();return item
 raise AssertionError('Missing Explore result '+ident)
w.resize(1920,1200);w.show();settle()
first=call('projects.create',{'title':'Ledger & Slate workshop','intent':'Turn a bold thought into questions, calculations and evidence. Keep each idea connected to its project while the instruments change around it.'})
second=call('projects.create',{'title':'Interface review','intent':'Review the cabinet, menus, writing passages and workspace transitions together.'})
idea=call('ideas.capture',{'project':first['id'],'text':'A cabinet should remember where an idea belongs while its tools and views change.'})
call('ideas.capture',{'text':'A thought that has not chosen its project yet.'})
call('projects.link',{'id':second['id'],'expected_revision':1,'role':'QUESTION','address':'idea:'+idea['id']})
page=w.cabinet_page;nav=w.settings_navigator;page.refresh(force=True);settle()
ref=next(n for n in page.model['nodes'] if n['role']=='reference' and n['canonical_id']=='idea:'+idea['id'])
room=select_record('project:'+first['id']);room.writing.setPlainText('Keep the work visible while we choose its next instrument.');settle()
assert room.breadcrumb.text().endswith('Concern / Projects') and current_id()==room.current
capture(1,'Cabinet','The cabinet and its current project','A real project, one unassigned idea and a second project. The yellow passage is unfinished writing.')
check('Opening a record follows its exact placement and shows its filing path without changing the typed identity')
source=root/'Files/navigation_draft.py';source.parent.mkdir(exist_ok=True);source.write_text('original = True\n')
original=(source.read_bytes(),source.stat().st_mode)
editor=w.open_document(source);editor.appendPlainText('# unfinished source writing');settle()
with patch.object(w.tabs,'dirty_choice',side_effect=AssertionError('Settings must not replace an edited Preview')):
 tab=bridge.show_settings(key='reading.family');settle()
assert tab.property('ledgerRoom') and w.tabs.indexOf(editor)>=0 and editor.document().isModified()
assert len(w.tabs.pinned())==0 and w.tabs.preview() is editor
check('Settings opens as a retained Room beside an edited Preview without a Save/Pin prompt or consuming one of five pins')
nav.items['settings:ledger:appearance'].setExpanded(False);nav.items['settings:slate'].setExpanded(False);nav.filter.setText('font')
tab=bridge.show_settings(key='memory.weight.owner_statement');settle()
assert nav.filter.text()=='' and not nav.items['setting:'+tab.key].isHidden()
assert nav.items['settings:slate'].isExpanded() and nav.items['settings:slate:memory'].isExpanded()
assert not nav.items['settings:ledger:appearance'].isExpanded()
check('Explicit Settings navigation clears an excluding filter, expands the destination path and leaves unrelated folds intact')
seed=RUN/'owner-reference.json';seed.write_text(json.dumps(dict(schema='arc.stacy.owner_personality_seed/1',name='Disposable UI review reference',version='1',
 stacy_expression=dict(default_character='Ask curious questions. Keep evidence and assumptions explicit.',inherit_from_ryan=[],retain_independently=[]))))
profile=call('memory.profile.import',{'path':str(seed)});tab.reload_latest()
nav.filter.setText('weight');bridge.show_settings(key='memory.weight.owner_correction');settle()
assert nav.filter.text()=='weight';tab=bridge.show_settings(key='memory.weight.owner_statement');nav.filter.clear()
tab.string.setText('3.25');QTest.mouseClick(tab.apply_button,Qt.LeftButton);settle()
assert call('memory.profile')['parameters']['weights']['owner_statement']==3.25
check('A matching Settings filter is retained and the existing Apply route still updates the original owner profile')
saved_key=tab.key;tab.string.setText('3.5');base_revision=tab.current['revision']
w.tabs.setCurrentWidget(room);settle()
assert nav.stack.currentIndex()==0 and current_id()=='project:'+first['id']
assert room.writing.toPlainText()=='Keep the work visible while we choose its next instrument.'
with patch.object(tab,'load_key',side_effect=AssertionError('Tab focus must not reload the Settings editor')):
 w.tabs.setCurrentWidget(tab);settle()
assert nav.stack.currentIndex()==1 and nav.selected_key()==saved_key and tab.string.text()=='3.5'
assert tab.current['revision']==base_revision
check('Focusing retained Cabinet and Settings tabs follows the correct tree while preserving both drafts and the original Settings revision')
with patch.object(room,'open',side_effect=AssertionError('Cabinet switch must not reread the record room')):
 QTest.mouseClick(nav.cabinet,Qt.LeftButton);settle()
assert w.tabs.currentWidget() is room and current_id()==room.current
check('The Cabinet word returns to the retained record room instead of leaving the Settings editor active')
page.query.setText('No matching drawer');settle()
with patch.object(room,'open',side_effect=AssertionError('Reveal must not reopen the writing form')):
 QTest.mouseClick(room.reveal_button,Qt.LeftButton);settle()
assert page.query.text()=='' and current_id()==room.current and room.writing.toPlainText().startswith('Keep the work')
check('Show in cabinet reveals a filtered placement without reopening its form or overwriting writing')
room=select_record(ref['id']);assert current_id()==ref['id'] and 'Interface review' in room.breadcrumb.text()
assert room.data['node']['canonical_id']=='idea:'+idea['id']
assert call('ideas.get',{'id':idea['id']})==idea
capture(2,'Reference','One idea, a second filing reference','The highlighted placement belongs to Interface review; the reference still resolves the same original idea in Ledger & Slate workshop.')
check('A second-project reference keeps its exact placement, canonical identity and original project instead of jumping to the owning home')
assert not w.navigation_controller.reveal_record('idea:'+'f'*32)
assert page.tree.currentItem() is None and 'outside this cabinet view' in page.status.text()
assert room.current==ref['id'];QTest.mouseClick(room.reveal_button,Qt.LeftButton);settle()
assert current_id()==ref['id']
check('An unavailable placement clears a misleading highlight and reports the bounded-view limit without substituting another record')
w.tabs.setCurrentWidget(tab);tab.reload_latest();settle()
capture(3,'Settings','Memory settings in the shared tree','Owner-scoped saved values, effects and history. Settings stays open alongside source writing.')
tab.string.setText('3.5');parameters=copy.deepcopy(call('memory.profile')['parameters']);parameters['soft_half_life_days']=180
call('memory.profile.configure',{'parameters':parameters});tab.poll();QTest.mouseClick(tab.apply_button,Qt.LeftButton);settle()
assert tab.string.text()=='3.5' and 'REVISION_CHANGED' in tab.note.text()
capture(4,'Conflict','A newer profile preserves the draft','A direct legacy profile edit intervened. Apply refuses the stale revision and leaves the writing in place.')
check('Navigation retains the original memory revision guard; a later legacy edit still refuses stale Apply and preserves writing')
room=select_record('project:'+first['id']);settle()
hatch=w.type_bar.hatch;hm=hatch.programs;assert hatch.prepare() and all(r.isVisible() or not hm.isVisible() for r in hm.rows())  # D2: the cat's programs list
hatch.open_list(False);settle();assert hm.isVisible() and len(hm.rows())==len(hatch.entries)+1
capture(5,'Menu','The programs list beside a selected project','The cat\'s programs list (HATCH DESK D2) renders as a real popup while a project is selected; its order and rows are checked by check_hatch_ui. Nothing is triggered.',hm);hm.close_menu();settle()
menu_capture(6,'Work_Menu','Work menu','Existing file, receiving, copy and recovery routes under the proposed Work heading.',w.menu_groups['File'],w.command_menus['File'])
menu_capture(7,'Arrange_Menu','Arrange menu','Existing workspace, presentation and console choices under Arrange.',w.menu_groups['Options'],w.command_menus['Options'])
menu_capture(8,'Rules_Menu','Rules menu','Shared Settings and retained configuration routes under Rules. The wording is ready for owner review.',w.menu_groups['Settings'],w.command_menus['Settings'])
from workbench.cabinet_actions_qt import menu
popup=menu(w,room.current,page.tree)
menu_capture(9,'Record_Actions','With this record','The live contextual menu uses the checked record captured when it opens. It does not execute an action during capture.',popup,page.tree)
check('Hatch, Work, Arrange, Rules and the checked record-action menu render as actual Qt popups without triggering their commands')
explorer=explore_qt.show(w,ref['id']);settle()
assert nav.stack.currentIndex()==0 and current_id()==ref['id'] and explorer.model['context']['id']==ref['id']
explorer_select(explorer,'instrument:calculate')
capture(10,'Explore','Choose an instrument for the work','Existing workspaces and explained suggestions. Opening a view leaves execution to its own controls.')
check('Explore carries the checked reference placement into the left cabinet without changing the record or replacing the source Preview')
explorer.kind.setCurrentIndex(explorer.kind.findData('METHOD'));explorer.query.setText('shortest');explorer.refresh();settle()
assert explorer.results.topLevelItemCount()==1
assert explorer.results.topLevelItem(0).data(0,Qt.UserRole)['status']=='Reference only'
QTest.mouseClick(explorer.open_button,Qt.LeftButton);settle()
methods=w.tabs.currentWidget();assert type(methods).__name__=='AlgorithmAtlasTab' and methods.current['id']=='shortest_path'
capture(11,'Methods','Inspect a method','The existing Algorithm & Theory Atlas opens a reference-only shortest-path method. No solver or job is run.')
check('Method inspection opens the original Atlas and preserves the edited source Preview')
queue_source=root/'Files/navigation_notes.txt';queue_source.write_text('Disposable review source.\n')
queued=call('agenda.add',{'title':'Inspect the saved interface notes','program':'@files:navigation_notes.txt','nice':'normal'})
call('agenda.add',{'title':'Compare the next layout','program':'@files:navigation_notes.txt','when':{'after':queued['id']},'nice':'normal'})
call('agenda.add',{'title':'Read references when idle','program':'@files:navigation_notes.txt','nice':'background'})
room=select_record('project:'+first['id']);w.shell2.show_operations_face();w.operations_panel.refresh();settle()
assert len(k.listing('jobs'))==0 and w.operations_panel.jobs.words().startswith('WORK · 3 queued'),w.operations_panel.jobs.words()  # D1-fix: Activity says it in one line
w.shell2.top.nice.open();settle();assert w.shell2.top.nice.popup.queue.count()==3;w.shell2.top.nice.popup.close_menu();settle()  # the rows are the System menu's process list (D2)
capture(12,'Operations','Operations and the pending queue','Three disposable saved Agenda items show ordering, dependency and idle waits. No tool job or live worker has started.')
w.shell2.show_context_face();settle();w.arc_inspector.refresh()
assert w.arc_inspector.heading.text()=='Cabinet selection' and first['title'] in w.arc_inspector.body.toPlainText()
capture(13,'Context','The selected record in Context','Context follows the current cabinet identity. Selection is distinct from source or engineering qualification.')
check('Operations and Context retain the cabinet identity and show real pending Agenda metadata without a job submission')
w.shell2.show_operations_face()
ret=w.return_thread.show();ret.writing.setPlainText('Next: review these 15 views and adjust the menu words, spacing and filing transitions.');ret.keep();settle()
assert w.return_thread.saved['note'].startswith('Next: review') and any(r['text'].startswith('Keep the work') for r in w.return_thread.saved['drafts'])
capture(14,'Return_Thread','Leave a thread for the next session','The existing return copy keeps cabinet writing and code recovery. Unfinished Settings writing still uses its own desktop-local drafts.')
check('The existing return-copy route retains the cabinet draft and source recovery while navigation leaves the source file unchanged')
w.tabs.setCurrentWidget(room);settle();fold=page.tree.currentItem().parent();fold.setExpanded(False)
w.resize(1440,900);settle();assert not fold.isExpanded()
fold.setExpanded(True);w.resize(1366,768);settle()
assert nav.stack.currentIndex()==0 and w.trash_can.isVisible() and w.shell2.top.programs.isVisible() and w.operations_monitors.isVisible()
assert room.reveal_button.isVisible() and room.reveal_button.width()>=room.reveal_button.minimumSizeHint().width()
assert w.return_thread.footer.isVisible() and room.writing.toPlainText().startswith('Keep the work')
assert page.tree.viewport().rect().contains(page.tree.visualItemRect(page.tree.currentItem()).center())
check('Resizing the left column keeps its expanded selected row in view without reopening the record or expanding a deliberately folded branch')
room.scroll.ensureWidgetVisible(room.writing);settle()
assert room.scroll.viewport().rect().intersects(room.writing.rect().translated(room.writing.mapTo(room.scroll.viewport(),QPoint(0,0))))
capture(15,'Compact','The compact writing desk','The same current project at 1366 by 768, scrolled to its unfinished writing. Fixed Trash, Stop, monitors and the return thread stay reachable.')
check('The compact desktop retains the filing control, unfinished project writing and fixed Trash, Stop, monitors and return footer')
assert (source.read_bytes(),source.stat().st_mode)==original and editor.document().isModified()
assert call('ideas.get',{'id':idea['id']})==idea
assert call('memory.profile')['original_sha256']==profile['original_sha256']
assert len(k.listing('jobs'))==0 and len(w.tabs.pinned())==0 and w.tabs.preview() is editor
check('Original source bytes/mode, imported reference, idea ownership and the five-pin policy survive all transitions')
objects={key:w.menu_groups[key] for key in menus2.DISPLAY_TITLES};favorites=dict(w.favorite_actions)
shortcuts={key:[s.toString() for s in a.shortcuts()] for key,a in favorites.items()}
menus2.rebuild(w);menus2.rebuild(w)
assert all(w.menu_groups[key] is obj for key,obj in objects.items())
assert all(w.favorite_actions[key] is a and [s.toString() for s in a.shortcuts()]==shortcuts[key] for key,a in favorites.items())
check('Repeated menu rebuild preserves original menu objects, QAction identities and keyboard shortcuts')
assert [c['number'] for c in captures]==list(range(1,len(captures)+1))
editor.document().setModified(False);assert w.close() is True;app.processEvents();assert not w.desktop_lease.exists()
provider.assert_not_called();submission.assert_not_called();launcher.assert_not_called();priority.assert_not_called()
provider.stop();submission.stop();launcher.stop();priority.stop()
check('Clean close removes the desktop lease; guarded provider, job submission and OS-priority routes were never called')
result=dict(state='PASSED',mode='ACTUAL_QT_OFFSCREEN',checks=checks,captures=captures,source_fixture='DISPOSABLE_SOURCE_AND_OWNER_REFERENCE',
 agenda_fixture_items=3,jobs_submitted=0,model_calls=0,provider_requests=0,native_invocations=0,os_priority_changes=0,
 popup_capture='Window and visible live Qt popup grabs composited at their actual window positions; no mock UI',
 native_acceptance=False,clean_close=True)
(OUT/'navigation-ui.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)
