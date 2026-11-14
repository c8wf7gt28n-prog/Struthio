"""Actual Qt checks for the cat's programs list as the truthful doorway to the workshop (HATCH DESKTOP-01, WI-2: HT01, HT02, HT03,
VS02; the mechanical, offscreen parts of AC02 and AC15), rebuilt for HATCH DESK D2: the cat opens a flat programs list (the
owner's brief of 2026-11-06: "like the Programs folder in a Start menu ... one plain name and one small graphite icon"); New
Idea and New Project are under Work; Graphite services and leaving are in the System menu.

Disposable profile, Concern and records; Kernel.launch, Kernel.submit and the provider request are held; after the window
exists no process, shell command or detached program may start, and session_power.system (the one place a session or power
command could start) is held too. The steps of AC02 are walked with no model (this container has none and starts none): a
Graphite workspace, a checks-only route, a missing prerequisite, Graphite services and the leaving rows of the System menu;
every row's words are compared with the catalogue they come from. The keyboard steps of AC15 send real key events. Nothing
here is owner-host acceptance, and the with-a-model column of AC02 stays open.

Also here: Local model opened from the list as a room, New Idea chosen twice raising the one open sheet, an interrupted job
counted on the Local model row, the Explore tab keeping its rows after a failed refresh, and Exit running the leave review once.
"""
import hashlib,json,os,subprocess,sys,tempfile,time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
PROGRAM=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('ARC_LEDGER_HATCH_CAPTURE_DIR',str(PROGRAM/'build/ui_checks/hatch')));OUT.mkdir(parents=True,exist_ok=True)
RUN=Path(tempfile.mkdtemp(prefix='ledger-desktop01-hatch-ui-'))
os.environ.update(QT_QPA_PLATFORM='offscreen',ARC_LEDGER_EMBEDDED='1',ARC_LEDGER_DISABLE_BOOK_WATCHER='1',
 ARC1_WORKBENCH_CONFIG_HOME=str(RUN/'profile'),ARC_LEDGER_CONCERN=str(RUN/'Concern'))
os.environ.pop('ARC_LEDGER_XSESSION',None)  # an existing display; the dedicated-session label is exercised explicitly below
sys.path.insert(0,str(PROGRAM));sys.dont_write_bytecode=True
from PySide6.QtCore import Qt,QPoint,QProcess,QTimer
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QApplication,QDialog,QMessageBox,QMenu,QToolTip
from PySide6.QtTest import QTest
from workbench.qt_app import make_app,WorkbenchWindow
from workbench import locations,clip,explore,explore_qt,hatch_qt,capability_catalog,programs_qt,session_power
from workbench.engineering_kernel import Kernel,operator,CAPABILITIES
from workbench.session import Session
provider=patch.object(clip,'_request',side_effect=AssertionError('No provider request')).start()
launcher=patch.object(Kernel,'launch',side_effect=AssertionError('No worker launch')).start()
submission=patch.object(Kernel,'submit',side_effect=AssertionError('No job submission')).start()
question=patch.object(QMessageBox,'question',return_value=QMessageBox.Yes).start()
def held_system(request):
 """session_power.system held: logind answers that there is no session; no command may start."""
 if request[0]=='logind':raise OSError('held by the check: no session')
 raise AssertionError('No session or power command')
power=patch.object(session_power,'system',side_effect=held_system).start()
app=make_app([]);root=locations.office(RUN/'workspace');session=Session(RUN/'profile/session.json',root)
w=WorkbenchWindow(root,session,restore=False);k=w.ledger_bridge.kernel;bridge=w.ledger_bridge
hatch=w.type_bar.hatch;life=hatch.lifecycle;lst=hatch.programs;explore_button=w.type_bar.explore
# Host readings ask the platform for its processor once (`uname -p`); from here on nothing may start.
import platform;platform.processor()
popen=patch.object(subprocess,'Popen',side_effect=AssertionError('No process start')).start()
system=patch.object(os,'system',side_effect=AssertionError('No shell command')).start()
detached=patch.object(QProcess,'startDetached',side_effect=AssertionError('No detached program')).start()
checks=[];captures=[];observations={};PREFIX='Graphite_HATCH_Programs_List_'
def settle(ms=25):
 for name in ('agenda_runner','study_idle'):
  obj=getattr(w,name,None)
  if obj and hasattr(obj,'timer'):obj.timer.stop()
 for _ in range(2):app.processEvents();QTest.qWait(ms)
def check(text):checks.append(text);print(text,flush=True)
def call(op,args=None):
 value=k.dispatch(op,args or {},operator());assert value['ok'],value;return value['result']
def capture(name,note,*popups):
 w.operations_panel.refresh();settle();pix=w.grab();mode='ACTUAL_QT_WINDOW_GRAB';painter=QPainter(pix)
 for popup in popups:
  assert popup.isVisible();pos=w.mapFromGlobal(popup.mapToGlobal(QPoint(0,0)));assert pos.x()>=0 and pos.y()>=0,(name,pos)
  painter.drawPixmap(pos,popup.grab());mode='ACTUAL_QT_WINDOW_AND_VISIBLE_POPUP_GRABS'
 painter.end();target=OUT/(PREFIX+name);assert pix.save(str(target),'PNG')
 captures.append(dict(file=PREFIX+name,note=note,mode=mode,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),resolution=[w.width(),w.height()]))
def rows():return list(lst.rows_by_key.values())
def row(prefix):return next(r for r in rows() if r.word.startswith(prefix))
def instruments():return {r['key']:r for r in call('ledger.explore',{'kind':'INSTRUMENT'})['instruments']}
def jobs():return len(k.listing('jobs'))
def focus():return getattr(app.focusWidget(),'word',None)
def open_list(keyboard=False):hatch.open_list(keyboard);settle();assert lst.isVisible();return lst
def choose(r):
 """Choose a row as the pointer does: the list closes first, then the row's action runs."""
 open_list();QTest.mouseClick(r,Qt.LeftButton);settle(60);assert not lst.isVisible()
w.resize(1920,1200);w.show();settle();bridge.timer.stop();life.timer.stop()
project=call('projects.create',{'title':'Doorway workshop','intent':'Open every installed capability from the cat without replacing the work in progress.'})
IDEA_TEXT='Which doorway opens the workshop truthfully?';idea=call('ideas.capture',{'project':project['id'],'text':IDEA_TEXT})
w.cabinet_page.refresh(force=True);w.cabinet_page.select('idea:'+idea['id'],reveal=True);settle()
source=root/'Files/doorway_draft.py';source.parent.mkdir(exist_ok=True);source.write_text('original = True\n')
editor=w.open_document(source);editor.appendPlainText('# unsaved thought kept through every opening of the list');settle()
assert w.tabs.preview() is editor and editor.document().isModified();jobs_before=jobs();assert jobs_before==0
# 01 · HT01 (D2): the list's order and stable identities; creation, services and leaving have their own homes
PLAIN=sorted((programs_qt.PLAIN[v[0]] for v in explore.VIEWS),key=str.casefold);EXPECTED=PLAIN+['—','Explore the workshop','Game']  # 0.7.0: the game is the last of the programs
objects=rows()+[lst.explore_row];start=time.perf_counter();assert hatch.prepare();opening=time.perf_counter()-start
for _ in range(10):assert hatch.prepare()
assert lst.words()==EXPECTED and rows()+[lst.explore_row]==objects,lst.words()
assert set(lst.rows_by_key)=={v[0] for v in explore.VIEWS} and len(rows())==len(instruments())==len(explore.VIEWS),'every capability of the Hatch groups, once'
assert lst.explore_row.action is hatch.explore_action and hatch.explore_action.text()=='Explore the workshop'
assert hatch.accessibleName()==hatch.toolTip()=='Open apps' and lst.accessibleName()=='Apps' and 'F1 reads the highlighted row' in hatch.accessibleDescription()
assert len({r.icon_key for r in rows()})==len(rows()),'one small graphite icon each'
work_menu=w.menu_groups['File'];assert w.a_new_idea in work_menu.actions() and w.a_new_project in work_menu.actions() and hatch.idea_action is w.a_new_idea and hatch.project_action is w.a_new_project
assert not any(word.startswith(('New Idea','New Project','Services','Graphite services','Exit','Return to Debian','Log','Restart','Shut')) for word in lst.words())
open_list(True);capture('01_List_1920.png','The cat\'s programs list at 1920 by 1200, opened with Return: %d programs and capabilities A to Z, one plain name and one small graphite icon each, a status word at the right where one applies, then Explore the workshop; Agenda, the first row, under focus. Creation is under Work, services and leaving in the System menu.'%len(rows()),lst)
lst.close_menu();settle()
check('HT01 (D2): the cat opens a flat list of every capability the Hatch groups held (%d), A to Z by plain name, then Explore the workshop; every row is created once (identities stable across eleven openings); New Idea and New Project are Work entries (the same actions the cat\'s old menu triggered), Graphite services and leaving are the System menu\'s'%len(rows()))
# 02 · HT02: every row's descriptor is the catalogue's own words
listed=instruments();prefixes={v[0]:v[7] for v in explore.VIEWS}
for key,r in lst.rows_by_key.items():
 entry=listed[key];lines=r.toolTip().split('\n')
 assert r.action.property('title')==entry['title'] and r.word==programs_qt.PLAIN[key]
 assert lines[0]==entry['description'] and lines[1]=='Opens: '+entry['presentation'],lines[:2]
 slate=next(line for line in lines if line.startswith('Graphite can: '))
 named=[part.rsplit(' (',1) for part in slate[len('Graphite can: '):].split(' and ')[0].split(', ')]
 assert len(named)==min(entry['operations'],explore.SLATE_OPERATIONS_SHOWN)>0,(r.word,slate)
 for op,scope in named:assert CAPABILITIES[op]==scope.rstrip(')') and op.startswith(prefixes[key]),(op,scope)
 needs=lines[3];assert needs.startswith('Needs: ')==(entry['tool_status']=='Needs setup')==(r.caption=='needs setup'),(r.word,r.caption,needs)
 if needs.startswith('Needs: '):assert needs=='Needs: '+', '.join(entry['setup_needed'])
 assert 'Qualification: not assessed on this host.' in lines and 'Context: '+IDEA_TEXT+' · idea' in lines and 'Opening runs no tool.' in lines,lines
 assert r.isEnabled()==entry['view_available'] and entry['view_state']=='Workspace available' and entry['presentation_kind'] in explore.KINDS
 if entry['presentation_kind']=='checks':assert entry['group']=='Programs' and 'itself is not opened' in lines[1]
 assert not any(word in r.toolTip()+r.word for word in ('690','691','registered operations','registered job tools','ready to run'))
assert 'no model selected' in lst.rows_by_key['brain'].action.property('words')
check('HT02: every row\'s tooltip is the presentation contract (Opens / Graphite can with scopes / Needs or prerequisites / jobs / Qualification / Context / Opening runs no tool), each named operation and scope the registry\'s own; the catalogue\'s title stays with each row (its plain name is the row\'s word); the status word (needs setup) is the Needs line\'s')
# 03 · AC02 step: a Graphite workspace, with no model; the Files row opens the Files workspace (V-01)
brain=explore_qt.brain_state(k);observations['local_model_state']=brain.get('state');assert brain.get('state')=='NO_MODEL_SELECTED'
count=w.tabs.count();choose(row('Projects'));desk=w.tabs.currentWidget()
assert type(desk).__name__=='ProjectDeskTab' and desk.property('ledgerRoom') and w.tabs.count()==count+1 and w.tabs.preview() is editor and editor.document().isModified() and w.tabs.pinned()==[]
assert hatch.prepare() and row('Projects').caption=='open'
count=w.tabs.count();choose(row('Files'));files=w.tabs.currentWidget()
assert type(files).__name__=='FilesTab' and files.property('ledgerRoom') and w.tabs.count()==count+1 and w.tabs.preview() is editor
count=w.tabs.count();choose(row('Local model'));brain_tab=w.tabs.currentWidget()
assert type(brain_tab).__name__=='BrainTab' and brain_tab.property('ledgerRoom') and w.tabs.count()==count+1 and w.tabs.preview() is editor and editor.document().isModified()
assert hatch.prepare() and row('Local model').caption=='open' and row('Local model').action.property('words').endswith(' · no model selected'),row('Local model').action.property('words')
w.a_new_idea.trigger();settle();sheet=w._capture_dialog;w.a_new_idea.trigger();settle()
sheets=[d for d in w.findChildren(QDialog) if d.windowTitle()=='Jot it down' and d.isVisible()]
assert len(sheets)==1 and sheets[0] is sheet is w._capture_dialog,sheets;sheet.reject();settle()
assert jobs()==jobs_before;popen.assert_not_called()
check('AC02 step, workspace with no model: Projects opens the Project Desk as a retained room, Files the Files workspace itself (not the last open file), Local model a room, and their rows then say open (Local model\'s words no model selected); the edited Preview and the pins are untouched; Work ▸ New Idea chosen twice raises the one open Jot it down sheet; no job or process')
# 04 · AC02 steps: a checks-only route and a missing prerequisite (passive discovery held to "nothing found")
import shutil
with patch.object(shutil,'which',return_value=None):
 assert hatch.prepare();programs=[lst.rows_by_key[v[0]] for v in explore.VIEWS if v[3]=='Programs']
 assert len(programs)==6 and all(r.caption=='needs setup' and r.isEnabled() for r in programs),[(r.word,r.caption) for r in programs]
 kicad=row('KiCad checks');lines=kicad.toolTip().split('\n')
 assert lines[1]=="Opens: Graphite's KiCad checks and controls in a Graphite workspace; KiCad itself is not opened" and lines[3]=='Needs: kicad-cli',lines
 assert '\nNeeds: ngspice\n' in row('ngspice profiles').toolTip() and '\nNeeds: iverilog, surfer, verilator\n' in row('HDL simulation').toolTip() and '\nNeeds: ecppack, nextpnr-ecp5\n' in row('nextpnr').toolTip()
 observations['needs_setup_rows']=[(r.word,r.caption) for r in programs]
 open_list();capture('02_Needs_Setup_1920.png','Passive discovery finding no executable: each program\'s checks row says needs setup at its right, in its own words; the tooltip (asserted) says what opens, what Graphite can do, and which executable is missing (KiCad checks: kicad-cli).',lst);lst.close_menu();settle()
 assert 'Needs an attached project.' in row('KiCad checks').toolTip() and instruments()['kicad']['project_required'] is True
 count=w.tabs.count();choose(row('KiCad checks'));tab=w.tabs.currentWidget();observations['kicad_without_project_opens']=type(tab).__name__
 assert type(tab).__name__=='EmptyWorkspaceTab' and tab.property('ledgerRoom') and w.tabs.count()==count+1 and w.tabs.preview() is editor and editor.document().isModified()
 count=w.tabs.count();choose(row('Yosys synthesis'));tab=w.tabs.currentWidget()
 assert type(tab).__name__=='YosysTab' and tab.property('ledgerRoom') and w.tabs.count()==count+1 and w.tabs.preview() is editor and editor.document().isModified()
 popen.assert_not_called();system.assert_not_called();detached.assert_not_called();assert jobs()==jobs_before
assert hatch.prepare()
check('AC02 steps, checks-only route and missing prerequisite: every program\'s checks row says needs setup and names its missing executables (KiCad checks: kicad-cli); KiCad without an attached project opens the existing project-required explanation, as its tooltip said; Yosys synthesis opens Graphite\'s checks workspace as a room under the process guards; nothing ran')
# 05 · an unavailable adapter is disabled in words and opens nothing; the catalogue read failing hides the rows behind one row
original_source=capability_catalog.source
def missing(root,name):return dict(path=name,state='MISSING_OR_UNSAFE',sha256=None) if name=='workbench/brain_qt.py' else original_source(root,name)
with patch.object(capability_catalog,'source',side_effect=missing):
 assert hatch.prepare();local=row('Local model');assert not local.isEnabled() and local.caption=='unavailable' and 'View unavailable: workbench/brain_qt.py' in local.toolTip()
 before=w.tabs.count();hatch.launch(instruments()['brain'],None);settle();assert w.tabs.count()==before and 'unavailable' in w.statusBar().currentMessage()
assert hatch.prepare() and row('Local model').isEnabled()
real_dispatch=k.dispatch
def failing(op,args,principal):
 if op=='ledger.explore':return {'ok':False,'error':{'code':'FIXTURE_UNAVAILABLE','message':'Capability view unavailable for this check'}}
 return real_dispatch(op,args,principal)
with patch.object(k,'dispatch',side_effect=failing):
 assert hatch.prepare() is False and lst.words()==['Capabilities unavailable · Capability view unavailable for this check','—','Explore the workshop'],lst.words()
assert hatch.prepare() and lst.words()==EXPECTED and rows()+[lst.explore_row]==objects
w.statusBar().clearMessage();settle()
check('HT03: a missing adapter disables only its row, in words (unavailable), with the module named, and choosing it opens nothing; a failed catalogue read puts one explained row in the list only for that opening, Explore the workshop staying')
# 06 · AC02 step: Graphite services in the System menu (the cycles that were the old menu's, kept)
sym=w.shell2.top.nice;menu=sym.open(False);settle();choices=menu.service_actions
assert [c.text() for c in menu.services.choices]==['On','Off','Restart'] and list(choices)==['On','Off','Reboot']
assert not choices['On'].isEnabled() and choices['Off'].isEnabled() and choices['Reboot'].isEnabled() and 'never on the computer' in menu.services.toolTip()
call('ledger.settings.set',{'key':'operations.services_enabled','value':False});life.refresh();settle()
assert choices['On'].isEnabled() and menu.services.toolTip().startswith('New work held'),menu.services.toolTip()
capture('03_Graphite_Services_1920.png','Admission held through the shared setting: the System menu\'s Graphite services row offers On (the way back), Off and Restart, the cycles the old menu held; its words say they act on Graphite\'s own services, never on the computer.',menu)
QTest.mouseClick(menu.services,Qt.LeftButton);settle(60);panel=w.tabs.currentWidget();assert type(panel).__name__=='HostPanel' and panel.property('ledgerRoom') and w.tabs.preview() is editor
call('ledger.settings.set',{'key':'operations.services_enabled','value':True});life.refresh();settle();assert not choices['On'].isEnabled()
FIXTURE_JOB='d'*32;k.save('jobs',dict(id=FIXTURE_JOB,owner=operator().identity,tool='brain.infer',state='Interrupted',created=time.time(),timeout=120))
assert hatch.prepare() and row('Local model').caption=='1 interrupted' and '1 interrupted for this owner' in row('Local model').toolTip(),row('Local model').caption
job=k.record('jobs',FIXTURE_JOB);job.update(state='Cancelled',finished=time.time());k.save('jobs',job)
assert hatch.prepare() and row('Local model').caption!='1 interrupted'
check('AC02 step, services: Graphite services sit in the System menu with On, Off and Restart under the cycle\'s rules (On disabled while admission is on, enabled while held); the row\'s word opens Service details as a room; an interrupted job is counted on the Local model row (1 interrupted) and in its tooltip')
# 07 · leaving: the System menu's separated group (the old disabled "not in this edition" row is gone: the owner's brief)
menu=sym.open(False);settle();states=menu.states;words=menu.words()
assert words[-5:]==['—','Log out','Exit Graphite','Restart','Shut down'],words
assert menu.session_rows['leave'].isEnabled() and 'stays open' in menu.session_rows['leave'].toolTip() and menu.session_rows['leave'].caption=='this Graphite session'
assert all(menu.session_rows[a].unavailable==states[a]['reason'] and states[a]['reason'].startswith(session_power.NO_SESSION) and menu.session_rows[a] in menu.focusables() for a in session_power.ACTIONS),states  # D2-fix: unavailable rows stay reachable and say why
assert [r.caption for r in (menu.session_rows['logout'],menu.session_rows['restart'],menu.session_rows['shutdown'])]==['this login session · unavailable','this computer · unavailable','this computer · unavailable']
capture('04_Leaving_1920.png','The System menu\'s separated group: Log out (this login session), Exit Graphite (this Graphite session), Restart and Shut down (this computer). This check holds the system\'s interfaces (no session), so the three are unavailable and say so; Exit Graphite is live.',menu)
tabs_before=w.tabs.count()
with patch.object(QMessageBox,'warning',return_value=QMessageBox.Ok) as warned:QTest.mouseClick(menu.session_rows['restart'],Qt.LeftButton);settle(60)
assert w.tabs.count()==tabs_before and not w._closing and w.isVisible() and warned.call_count==1 and warned.call_args[0][1]=='Restart is unavailable' and session_power.NO_SESSION in warned.call_args[0][2],'an unavailable row only says why'
menu=sym.open(False);settle()
menu.close_menu();settle()
with patch.dict(os.environ,{'ARC_LEDGER_XSESSION':'1'}):
 from workbench.system_menu_qt import SystemMenu
 fresh=SystemMenu(w,sym);assert fresh.session_rows['leave'].word=='Return to Debian' and 'Debian text login' in fresh.session_rows['leave'].toolTip();fresh.deleteLater();settle()
assert power.call_count>0 and all(c.args[0][0]=='logind' for c in power.call_args_list),'only logind reads'
popen.assert_not_called();system.assert_not_called();detached.assert_not_called()
check('AC02 step, leaving: Exit Graphite (Return to Debian under the dedicated-session marker) is live in the System menu\'s separated group; Log out, Restart and Shut down carry their scope words and, with the system\'s interfaces held (no session), are unavailable with that reason, still in the keyboard\'s order; choosing one only says why; only logind reads were asked, no command')
# 08 · AC15 mechanical keyboard steps with real key events (ACC-02, ACC-03, ACC-09, ACC-12)
def keyboard_session(opener,capture_name=None):
 rec={'error':None}
 w.activateWindow();hatch.setFocus();settle();rec['focus_before']=app.focusWidget() is hatch
 opener();settle(60)
 try:
  rec['visible']=lst.isVisible();rec['first_active']=focus();rec['tooltip_on_open']=QToolTip.isVisible()
  enabled=[r.word for r in lst.focusables()];walk=[]
  for _ in range(len(enabled)):QTest.keyClick(app.focusWidget(),Qt.Key_Down);walk.append(focus())
  rec['down_walk']=walk;rec['enabled']=enabled
  QTest.keyClick(app.focusWidget(),Qt.Key_Home);rec['home']=focus();QTest.keyClick(app.focusWidget(),Qt.Key_Up);rec['up_from_first']=focus();QTest.keyClick(app.focusWidget(),Qt.Key_Down);rec['down_to_first']=focus()
  lst.typed_at=0;QTest.keyClicks(app.focusWidget(),'lo');rec['typed_lo']=focus();lst.typed_at=0;QTest.keyClick(app.focusWidget(),Qt.Key_M);rec['typed_m']=focus();lst.typed_at=0;QTest.keyClick(app.focusWidget(),Qt.Key_M);rec['typed_m_again']=focus()
  lst.typed_at=0;QTest.keyClicks(app.focusWidget(),'fi');rec['typed_fi']=focus()
  QTest.keyClick(app.focusWidget(),Qt.Key_F1,Qt.ShiftModifier);settle(5);rec['f1_row']=w.statusBar().currentMessage();rec['f1_row_expected']=lst.descriptor(app.focusWidget());rec['f1_tooltip']=QToolTip.isVisible()
  rec['placeholder']=w.type_bar.box.placeholderText()
  if capture_name:capture(capture_name,'The programs list opened with the Return key: Agenda active on opening; typing lo jumped to Local model, m to Memory then Methods, fi to Files; Shift+F1 read the active row\'s descriptor into the writing line\'s note, not a tooltip.',lst)
 except Exception as exc:rec['error']=repr(exc)
 finally:
  if lst.isVisible():QTest.keyClick(app.focusWidget(),Qt.Key_Escape);settle(5)
  if lst.isVisible():lst.hide()
 rec['closed']=not lst.isVisible();rec['focus_after']=app.focusWidget() is hatch;return rec
assert hatch.prepare()
kb=keyboard_session(lambda:QTest.keyClick(hatch,Qt.Key_Return),'05_Keyboard_Typing_1920.png')
assert kb['error'] is None,kb;assert kb['focus_before'] and kb['visible'] and kb['first_active']=='Agenda' and not kb['tooltip_on_open'],kb
assert kb['down_walk']==kb['enabled'][1:]+kb['enabled'][:1] and kb['enabled']==PLAIN+['Explore the workshop'],(kb['down_walk'],kb['enabled'])
assert kb['home']=='Agenda' and kb['up_from_first']=='Explore the workshop' and kb['down_to_first']=='Agenda',kb
assert (kb['typed_lo'],kb['typed_m'],kb['typed_m_again'],kb['typed_fi'])==('Local model','Memory','Methods','Files'),kb
assert kb['f1_row']==kb['f1_row_expected'] and kb['f1_row'].startswith('Files · open — Read working material') and 'Opens: Graphite workspace' in kb['f1_row'] and 'Opening runs no tool.' in kb['f1_row'] and explore_qt.ROOM_NOTE not in kb['f1_row'],kb
assert not kb['f1_tooltip'] and kb['placeholder']=='prompt' and kb['closed'] and kb['focus_after'],kb
others={}
for name,key in (('space',Qt.Key_Space),('enter',Qt.Key_Enter)):
 rec=keyboard_session(lambda key=key:QTest.keyClick(hatch,key));others[name]=rec
 assert rec['error'] is None and rec['visible'] and rec['first_active']=='Agenda' and rec['up_from_first']=='Explore the workshop' and rec['closed'] and rec['focus_after'],(name,rec)
def explore_session():
 rec={'error':None};popup=explore_button.popup
 def driver():
  try:
   rec['visible']=popup.isVisible();rec['first_active']=popup.activeAction().text() if popup.activeAction() else None;rec['rows']=['—' if a.isSeparator() else a.text() for a in popup.actions()];rec['submenus']=len(popup.findChildren(QMenu))
   QTest.keyClick(popup,Qt.Key_F1);settle(5);rec['f1']=w.statusBar().currentMessage();rec['f1_tooltip']=QToolTip.isVisible()
   QTest.keyClick(popup,Qt.Key_Up);rec['up_from_first']=popup.activeAction().text() if popup.activeAction() else None
  except Exception as exc:rec['error']=repr(exc)
  finally:
   QTest.keyClick(popup,Qt.Key_Escape);settle(5)
   if popup.isVisible():popup.hide()
 w.activateWindow();explore_button.setFocus();settle();rec['focus_before']=app.focusWidget() is explore_button
 QTimer.singleShot(60,driver);QTest.keyClick(explore_button,Qt.Key_Return);settle()
 rec['closed']=not popup.isVisible();return rec
ex=explore_session();assert ex['error'] is None,ex
# HATCH DESK D1a: the Explore word left the lower band; the object and its menu stay for callers (its keys exercised on the hidden button).
assert explore_button.isHidden() and not ex['focus_before'] and ex['visible'] and ex['first_active']=='Explore the workshop…' and ex['submenus']==0,ex
assert ex['rows'][:2]==['Explore the workshop…','For '+IDEA_TEXT] and ex['rows'][-2:]==['—','Find saved work…'],ex['rows']
assert ex['f1'].startswith('Explore the workshop… — Opens: the Explore workspace') and not ex['f1_tooltip'] and ex['up_from_first']=='Find saved work…' and ex['closed'],ex
w.statusBar().clearMessage();settle();assert w.type_bar.box.placeholderText()=='prompt'
check('AC15 keyboard steps: Return, Enter and Space open the programs list with its first row (Agenda) active; Down visits every row in order and wraps, Home returns to the first, Up from the first reaches Explore the workshop; typing a name\'s first letters jumps to it (lo Local model, m Memory then Methods, fi Files); F1 and Shift+F1 read the active row\'s descriptor into the writing line\'s note with no tooltip and the poem placeholder intact; Escape closes and focus returns to the cat; the Explore word behaves the same')
# 09 · the Explore tab beside the doorway (VS02 de-duplication, V-10, V-17)
tab=explore_qt.show(w,'idea:'+idea['id']);settle();n=tab.results.topLevelItemCount();assert n==len(explore.VIEWS)
assert tab.status.text().startswith(str(tab.model['matches'])+' matches') and not any(word in tab.status.text() for word in ('690','691','operations','job tools')),tab.status.text()
kinds={tab.results.topLevelItem(i).text(1) for i in range(n)};assert kinds=={'Workspace','Tool checks','App operations'},kinds
states_=[tab.results.topLevelItem(i).text(2) for i in range(n)]
assert all(s.startswith(('Workspace available','View already open')) for s in states_) and not any(s.startswith('Open workspace') for s in states_),states_
item=next(tab.results.topLevelItem(i) for i in range(n) if tab.results.topLevelItem(i).data(0,Qt.UserRole)['key']=='kicad');tab.results.setCurrentItem(item);settle()
assert "Opens: Graphite's KiCad checks" in tab.readiness.text() and tab.open_button.text()=='Open workspace' and tab.readiness.text().startswith(('Workspace available','View already open'))
with patch.object(k,'dispatch',side_effect=failing):tab.refresh();settle()
assert tab.results.isEnabled() and tab.results.topLevelItemCount()==n and 'unavailable' in tab.note.text(),tab.note.text()
tab.refresh();settle();assert tab.results.isEnabled() and tab.results.topLevelItemCount()==n
count=w.tabs.count();choose(lst.explore_row);assert type(w.tabs.currentWidget()).__name__=='ExploreTab'
check('The Explore tab says Workspace available (the action word Open workspace is the button), shows the presentation kind in its Kind column and the Opens line in its readiness text, and carries no registration totals; a failed refresh keeps the previous rows usable; the list\'s Explore the workshop opens it')
# 10 · LAYOUT-04 / ACC-05 (D2): the list fits between the two bands in one column at 14 pt on 1366 by 768 and 1280 by 720, and scrolls (never over a band) when the window is shorter than its rows
def list_fit(tag):
 open_list();pos=w.mapFromGlobal(lst.mapToGlobal(QPoint(0,0)))
 info=dict(window=[w.width(),w.height()],box=[pos.x(),pos.y(),lst.width(),lst.height()],rows=len(lst.rows()),row_height=lst.m.row,
  bands=[w.ribbon_dock.height(),w.type_dock.height()],scrolls=lst.scroll.verticalScrollBar().maximum()>0,single_column=len({r.x() for r in lst.rows()})==1,
  between_the_bands=pos.y()>=w.ribbon_dock.height() and pos.y()+lst.height()==w.height()-w.type_dock.height())
 observations.setdefault('list_fit',{})[tag]=info;print(tag,json.dumps(info),flush=True);return info
w.resize(1366,768);settle();info=list_fit('14pt_1366x768');assert info['between_the_bands'] and info['single_column'] and not info['scrolls'],info
assert w.trash_can.isVisible() and w.shell2.top.programs.isVisible() and w.operations_monitors.isVisible() and w.return_thread.footer.isVisible()
capture('06_Compact_1366.png','The whole programs list at 1366 by 768 and 14 pt: one column between the two bands, no scrolling; Trash, the System menu\'s symbol, the monitors and the return footer stay visible.',lst);lst.close_menu();settle()
w.resize(1280,720);settle();info=list_fit('14pt_1280x720');assert info['between_the_bands'] and info['single_column'],info;lst.close_menu();settle()
call('ledger.settings.set',{'key':'reading.ui_pt','value':18});bridge.sync_profile(force=True);settle(50)
w.resize(1366,768);settle();info=list_fit('18pt_1366x768');assert info['between_the_bands'] and info['single_column'],info
capture('07_Compact_1366_18pt.png','The same list at 18 pt interface text on 1366 by 768: still one column between the bands; it scrolls when its rows are taller than the room (the keyboard brings the active row into view).',lst);lst.close_menu();settle()
call('ledger.settings.set',{'key':'reading.ui_pt','value':14});bridge.sync_profile(force=True);settle(50);w.resize(1920,1200);settle()
check('LAYOUT-04 / ACC-05 (D2): the list sits in one column between the head band and the lower band at 14 pt on 1366 by 768 (whole, no scrolling) and 1280 by 720, and at 18 pt on 1366 by 768 it scrolls rather than cover a band')
# 11 · zero execution on discovery, clean close
assert call('ledger.explore',{'kind':'INSTRUMENT'})['native_invocations']==0 and jobs()==jobs_before+1==1  # the one disposable fixture row
assert all(r['state'] in ('Completed','Cancelled','Failed') for r in k.listing('jobs'))
editor.document().setModified(False)
with patch.object(WorkbenchWindow,'close',return_value=True) as closed,patch.object(w.return_thread,'exit_dialog',return_value=SimpleNamespace(exec=lambda:1)):
 menu=sym.open(False);settle();QTest.mouseClick(menu.session_rows['leave'],Qt.LeftButton);settle(60);assert closed.call_count==1,closed.call_count
assert w.close() is True;settle();assert not w.desktop_lease.exists()
launcher.assert_not_called();provider.assert_not_called();submission.assert_not_called();popen.assert_not_called();system.assert_not_called();detached.assert_not_called()
assert all(c.args[0][0]=='logind' for c in power.call_args_list),'no session or power command'
check('Discovery ran nothing: no job, worker, model, provider, native tool, session or power command across every opening, descriptor, keyboard step and opened workspace; Exit Graphite runs the leave review and the ordinary close exactly once; clean close removed the lease')
result=dict(state='PASSED',mode='ACTUAL_QT_OFFSCREEN',checks=checks,captures=captures,observations=observations,
 keyboard=dict(return_key=kb,space=others['space'],enter=others['enter'],explore=ex),
 list_order=EXPECTED,list_rows=len(EXPECTED)-1,adapters=len(explore.VIEWS),list_opening_seconds_first=round(opening,3),
 ac02='MECHANICAL_OFFSCREEN_STEPS_WITH_NO_MODEL: Graphite workspace, checks-only route, missing prerequisite, Graphite services, leaving, descriptor against the catalogue; the with-a-model column is open',
 ac15='MECHANICAL_KEYBOARD_STEPS_ONLY: pointer and screen-reader use on the owner host are open',
 disposable_job_records=1,jobs_submitted=0,worker_processes_started=0,model_generations=0,provider_requests=0,native_invocations=0,os_power_or_logout_commands=0,
 owner_host_acceptance=False,acceptance_claimed=False,clean_close=True)
(OUT/'hatch-ui.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n');print(json.dumps(dict(result,keyboard='(recorded)'),indent=2,ensure_ascii=False),flush=True)
for guard in (power,question,detached,system,popen,submission,launcher,provider):guard.stop()
