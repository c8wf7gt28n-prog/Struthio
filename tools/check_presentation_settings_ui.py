"""Actual Qt presentation checks. Every Kernel launcher and provider is held."""
import hashlib,json,os,sys,tempfile
from pathlib import Path
from unittest.mock import patch
PROGRAM=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('ARC_LEDGER_PRESENTATION_CAPTURE_DIR',str(PROGRAM/'build/ui_checks/presentation_settings')));OUT.mkdir(parents=True,exist_ok=True)
RUN=Path(tempfile.mkdtemp(prefix='ledger-presentation01-ui-'))
os.environ.update(QT_QPA_PLATFORM='offscreen',ARC_LEDGER_EMBEDDED='1',ARC_LEDGER_DISABLE_BOOK_WATCHER='1',
 ARC1_WORKBENCH_CONFIG_HOME=str(RUN/'profile'),ARC_LEDGER_CONCERN=str(RUN/'Concern'))
sys.path.insert(0,str(PROGRAM));sys.dont_write_bytecode=True
from PySide6.QtCore import Qt,QPoint
from PySide6.QtGui import QPainter
from PySide6.QtTest import QTest,QSignalSpy
from shiboken6 import isValid
from workbench.qt_app import make_app,WorkbenchWindow
from workbench import locations,clip,ledger_control,settings_registry
from workbench.engineering_kernel import operator,Kernel
from workbench.session import Session
from workbench.presentation_qt import fill_favorites_menu
provider=patch.object(clip,'_request',side_effect=AssertionError('No provider request')).start()
submission=patch.object(Kernel,'submit',side_effect=AssertionError('No job submission')).start()
launch=patch.object(Kernel,'launch',side_effect=AssertionError('No job launch')).start()
app=make_app([]);root=locations.office(RUN/'workspace');session=Session(RUN/'profile/session.json',root)
w=WorkbenchWindow(root,session,restore=False);bridge=w.ledger_bridge;k=bridge.kernel;checks=[];captures=[]
def settle(wait=25):
 for name in ('agenda_runner','study_idle'):
  obj=getattr(w,name,None)
  if obj and hasattr(obj,'timer'):obj.timer.stop()
 for _ in range(2):app.processEvents();QTest.qWait(wait)
def call(op,args=None):
 result=k.dispatch(op,args or {},operator());assert result['ok'],result;return result['result']
def row(key):return next(r for r in call('ledger.settings')['settings'] if r['key']==key)
def show(key):
 tab=bridge.show_settings(key=key);settle();return tab
def apply(tab):
 tab.scroll.ensureWidgetVisible(tab.apply_button);settle();QTest.mouseClick(tab.apply_button,Qt.LeftButton);settle()
def choose(tab,index,key):
 combo=tab.favorite_slots.slots[index];combo.setCurrentIndex(combo.findData(key))
def check(text):checks.append(text);print(text,flush=True)
def capture(name,note,popup=None):
 w.operations_panel.refresh();settle();pix=w.grab();mode='ACTUAL_QT_WINDOW_GRAB'
 if popup is not None:
  assert popup.isVisible();painter=QPainter(pix)
  painter.drawPixmap(w.mapFromGlobal(popup.mapToGlobal(QPoint(0,0))),popup.grab());painter.end()
  mode='ACTUAL_QT_WINDOW_AND_VISIBLE_POPUP_GRABS'
 target=OUT/name;assert pix.save(str(target),'PNG')
 captures.append(dict(file=name,note=note,mode=mode,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),resolution=[w.width(),w.height()]))
w.resize(1920,1200);w.show();settle();bridge.timer.stop()
spies=[QSignalSpy(action.triggered) for action in w.favorite_actions.values()]
tab=show('favorites.file')
assert len(settings_registry.BY_KEY)==len(settings_registry.SPECS) and all('setting:'+key in w.settings_navigator.items for key in ('catalog.view','favorites.file','favorites.edit','favorites.view','favorites.options','favorites.help'))
assert tab.editors.currentWidget() is tab.favorite_slots
choose(tab,0,'new');choose(tab,1,'open');choose(tab,2,'save');apply(tab)
assert row('favorites.file')['stored']==['new','open','save'] and w.favorites['File']==['new','open','save']
assert row('favorites.file')['application_state']=='APPLIED' and k.listing('jobs')==[]
assert all(button.isHidden() for buttons in w.favorite_button_rows.values() for button in buttons)
capture('Ledger_Slate_HATCH_Presentation_01_Favorites.png','Actual Settings: three ordered Work favorites, original commands, saved and desktop-applied values.')
check('Six genuine settings appear in the shared tree; ordered word-based favorites apply without launching work or reviving the icon strip')
QTest.mouseClick(tab.undo_button,Qt.LeftButton);settle();assert row('favorites.file')['stored']==['open','save','save_all']
choose(tab,0,'open');choose(tab,1,'open');apply(tab)
assert row('favorites.file')['stored']==['open','save','save_all'] and tab.editor_value()==['open','open','save_all']
assert 'once' in tab.note.text();capture('Ledger_Slate_HATCH_Presentation_01_Draft.png','A duplicate favorite is refused; saved values stay unchanged and the highlighted draft remains available.')
tab.reload_latest();check('Apply and Undo use shared history; duplicate commands are refused with the three-slot draft retained')
source=root/'Files/presentation_draft.py';source.parent.mkdir(exist_ok=True);source.write_text('original = True\n')
original=(source.read_bytes(),source.stat().st_mode);editor=w.open_document(source);editor.appendPlainText('# unfinished source stays here')
tab=show('favorites.file');choose(tab,0,'new');choose(tab,1,'open');choose(tab,2,None)
call('ledger.settings.set',dict(key='favorites.file',value=['save'],expected_revision=row('favorites.file')['revision']))
tab.poll();apply(tab)
assert tab.editor_value()==['new','open'] and 'REVISION_CHANGED' in tab.note.text() and row('favorites.file')['stored']==['save']
assert editor.document().isModified() and w.tabs.indexOf(editor)>=0
tab.reload_latest();choose(tab,0,'new');choose(tab,1,'open');choose(tab,2,'save');apply(tab)
check('An intervening shared revision refuses a stale favorites draft while preserving the edited source Preview')
# Menu entries share the original actions, including their enabled states and shortcuts.
from workbench.menus2 import rebuild
saved={key:row(key)['stored'] for key in ('favorites.view','favorites.options')}
for key in saved:call('ledger.settings.set',dict(key=key,value=['reading']))
bridge.sync_profile(force=True);fill_favorites_menu(w)
assert sum(action is w.favorite_actions['reading'] for action in w.favorite_commands_menu.actions())==1
for key,value in saved.items():call('ledger.settings.set',dict(key=key,value=value))
bridge.sync_profile(force=True)
check('One command favorited in two groups appears once in the combined menu while both saved groups retain their choices')
rebuild(w);rebuild(w);menu=w.favorite_commands_menu;fill_favorites_menu(w)
assert sum(action is menu.menuAction() for action in w.menu_groups['Commands'].actions())==1
for key in ('new','open','save'):assert w.favorite_actions[key] in menu.actions()
assert not any(menu.menuAction() in sub.actions() for sub in w.menu_groups['Tools'].findChildren(type(menu)))
menu.popup(w.mapToGlobal(QPoint(1020,110)));settle()
assert all(spy.count()==0 for spy in spies) and all(isValid(action) for action in w.favorite_actions.values())
assert menu.width()<500 and menu.height()<780
capture('Ledger_Slate_HATCH_Presentation_01_Commands.png','Actual open Favorite commands popup, captured from the real Qt menu; original QAction objects retain labels, shortcuts and enabled states.',menu)
menu.hide();settle();check('Repeated menu rebuilds preserve one word-based favorites submenu and original action identity; opening it triggers no commands')
# Empty groups stay intentionally empty across reloading the session and desktop.
tab=show('favorites.help')
for index in range(3):choose(tab,index,None)
apply(tab);assert row('favorites.help')['stored']==[] and w.favorites['Help']==[]
assert Session(session.path,root).state['toolbar_favorites']['Help']==[]
check('An intentionally empty group persists through the original Session profile and stays empty in the desktop')
tab=show('catalog.view');snapshot=w.concern.store.snapshot();cabinet_before=dict(w.cabinet_page.saved)
tab.choice.setCurrentIndex(tab.choice.findData('offices'));apply(tab)
assert row('catalog.view')['stored']=='offices' and w.concern.view=='offices' and w.concern.selector.currentData()=='offices'
assert w.concern.store.snapshot()==snapshot and w.cabinet_page.saved==cabinet_before
assert row('catalog.view')['application_state']=='APPLIED' and 'Offices' in w.shell2.view_line.text()
w.settings_navigator.cabinet.click();settle();w.cabinet_page.set_legacy(True);settle()
tab=show('catalog.view');assert tab.choice.height()<90
w.settings_navigator.show(False,persist=False);settle()
capture('Ledger_Slate_HATCH_Presentation_01_Catalogue.png','Existing catalogue presentation is Offices. This preference changes Existing views only; filing identities and catalogue records are retained.')
w.settings_navigator.show(True,persist=False);settle()
check('Catalogue Apply changes the Existing views consumer while keeping logical cabinet state and every catalogue record intact')
w.concern.selector.setCurrentIndex(w.concern.selector.findData('archive'));settle();bridge.publish_settings_readback();tab.poll()
assert row('catalog.view')['stored']=='archive' and tab.editor_value()=='archive'
changes=call('ledger.settings.history',dict(key='catalog.view'))['changes'];assert len(changes)==2 and changes[0]['after']=='archive'
QTest.mouseClick(tab.undo_button,Qt.LeftButton);settle();assert row('catalog.view')['stored']=='offices' and w.concern.view=='offices'
check('The legacy catalogue chooser journals the same setting; Undo synchronizes it through the shared revision path')
# Direct SDK writes invalidate old drafts even when the catalogue returns to the same view.
tab.choice.setCurrentIndex(tab.choice.findData('work'));w.concern.store.set_preference('view','archive');w.concern.store.set_preference('view','offices')
tab.poll();apply(tab);assert 'REVISION_CHANGED' in tab.note.text() and tab.editor_value()=='work'
tab.reload_latest();check('A legacy catalogue change away and back invalidates a stale saved-view draft without replaying it')
tab=show('favorites.options');w.resize(1366,768);settle();tab.scroll.ensureWidgetVisible(tab.apply_button);settle()
assert w.trash_can.isVisible() and w.shell2.top.nice.isVisible() and w.operations_monitors.isVisible() and w.return_thread.footer.isVisible()
assert w.settings_navigator.selected_key()=='favorites.options' and tab.favorite_slots.isVisible()
capture('Ledger_Slate_HATCH_Presentation_01_Compact.png','Actual compact Settings editor: favorites slots scroll with the passage; fixed Trash, Stop, monitors and return thread remain reachable.')
check('Compact Settings keeps the selected key, three slots, fixed left-panel Trash, Stop, monitors and return thread reachable')
assert (source.read_bytes(),source.stat().st_mode)==original and editor.document().isModified()
assert k.listing('jobs')==[];launch.assert_not_called();provider.assert_not_called()
editor.document().setModified(False);assert w.close() is True;settle();assert not w.desktop_lease.exists()
check('Clean close retains original source bytes and mode, removes the desktop lease, and starts zero jobs, providers, models or native tools')
provider.stop();launch.stop()
result=dict(state='PASSED',mode='ACTUAL_QT_OFFSCREEN',checks=checks,captures=captures,
 queued_job_submissions=0,all_kernel_launchers_held=True,worker_processes_started=0,model_generations=0,
 provider_requests=0,native_invocations=0,owner_host_acceptance=False,clean_close=True)
(OUT/'presentation-settings-ui.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)
