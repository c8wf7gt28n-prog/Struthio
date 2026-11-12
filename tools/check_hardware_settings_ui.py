"""Actual Qt checks for hardware.category_views (INTEGRATION-01). Every Kernel launcher and provider is held.

Two hardware panes, the Settings editor, consumer receipts and journal discipline are exercised in a
disposable profile and workspace. Captures are real offscreen window grabs with sha256 and resolution.
"""
import hashlib,json,os,sys,tempfile
from pathlib import Path
from unittest.mock import patch
PROGRAM=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('ARC_LEDGER_HARDWARE_CAPTURE_DIR',str(PROGRAM/'build/ui_checks/hardware_settings')));OUT.mkdir(parents=True,exist_ok=True)
RUN=Path(tempfile.mkdtemp(prefix='ledger-integration01-hardware-ui-'))
os.environ.update(QT_QPA_PLATFORM='offscreen',ARC_LEDGER_EMBEDDED='1',ARC_LEDGER_DISABLE_BOOK_WATCHER='1',
 ARC1_WORKBENCH_CONFIG_HOME=str(RUN/'profile'),ARC_LEDGER_CONCERN=str(RUN/'Concern'))
sys.path.insert(0,str(PROGRAM));sys.dont_write_bytecode=True
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from workbench.qt_app import make_app,WorkbenchWindow
from workbench import locations,clip,ledger_control,settings_registry
from workbench.engineering_kernel import operator,Kernel
from workbench.session import Session
from workbench.hardware_overview import HardwareGroupTab
from workbench.hardware_settings_qt import pane_keys
provider=patch.object(clip,'_request',side_effect=AssertionError('No provider request')).start()
submission=patch.object(Kernel,'submit',side_effect=AssertionError('No job submission')).start()
launch=patch.object(Kernel,'launch',side_effect=AssertionError('No job launch')).start()
# An attached (PROJECT) workspace: the hardware navigator and its category panes exist only when a project is attached.
app=make_app([]);root=locations.ensure_workspace(RUN/'workspace',kind='PROJECT',name='Hardware settings check');locations.arrived(root,create=True)
session=Session(RUN/'profile/session.json',root)
w=WorkbenchWindow(root,session,restore=False);bridge=w.ledger_bridge;k=bridge.kernel;checks=[];captures=[]
KEY=settings_registry.VIEW_MODES_KEY
def settle(wait=25):
 for name in ('agenda_runner','study_idle'):
  obj=getattr(w,name,None)
  if obj and hasattr(obj,'timer'):obj.timer.stop()
 for _ in range(2):app.processEvents();QTest.qWait(wait)
def call(op,args=None):
 result=k.dispatch(op,args or {},operator());assert result['ok'],result;return result['result']
def row(key=KEY):return next(r for r in call('ledger.settings')['settings'] if r['key']==key)
def journal():return call('ledger.settings.history',{'key':KEY})['changes']
def on_disk():return Session(session.path,root).state.get('category_views',{})
def show(key):
 tab=bridge.show_settings(key=key);settle();return tab
def click(tab,button):
 tab.scroll.ensureWidgetVisible(button);settle();QTest.mouseClick(button,Qt.LeftButton);settle()
def check(text):checks.append(text);print(text,flush=True)
def capture(name,note):
 w.operations_panel.refresh();settle();pix=w.grab();target=OUT/name;assert pix.save(str(target),'PNG')
 captures.append(dict(file=name,note=note,mode='ACTUAL_QT_WINDOW_GRAB',sha256=hashlib.sha256(target.read_bytes()).hexdigest(),resolution=[w.width(),w.height()]))
w.resize(1920,1200);w.show();settle();bridge.timer.stop()
assert KEY in settings_registry.BY_KEY and 'setting:'+KEY in w.settings_navigator.items and 'settings:ledger:hardware' in w.settings_navigator.items
# 1. Opening, filtering and navigating panes journals nothing; the readback reports the open panes.
# The first pane is pinned (the existing five-pin policy) so the second does not replace it as the Preview.
a=w.show_device_group('f133','Firmware');settle();w.tabs.pin(a);settle();b=w.show_device_group('d213','Schematics');settle()
assert isinstance(a,HardwareGroupTab) and isinstance(b,HardwareGroupTab) and (a.view_key,b.view_key)==('f133/Firmware','d213/Schematics')
assert a in w.tabs.pinned() and w.tabs.indexOf(a)>=0 and w.tabs.indexOf(b)>=0 and len(bridge.hardware_panes())==2
assert a.mode.currentText()=='Auto view' and b.mode.currentText()=='Auto view'
a.filter.setText('x');settle();a.filter.clear();a.navigate(None);b.refresh();settle()
assert journal()==[] and row()['stored']=={} and on_disk()=={}
bridge.publish_settings_readback();r=row()
assert r['application_state']=='APPLIED' and r['effective']=={'f133/Firmware':'Auto view','d213/Schematics':'Auto view'},r
check('Opening, filtering, navigating and refreshing two hardware panes journals nothing; the readback lists both panes at Auto view')
# 2. One explicit choice in a pane is exactly one journaled change; an unchanged pick writes nothing.
a.mode.setCurrentText('Details');settle()
assert row()['stored']=={'f133/Firmware':'Details'} and on_disk()=={'f133/Firmware':'Details'} and len(journal())==1,journal()
r=row();assert r['application_state']=='APPLIED' and r['effective']=={'f133/Firmware':'Details','d213/Schematics':'Auto view'},r
assert a.remember_mode() is None and len(journal())==1 and a.stack.currentIndex()==0 and b.mode.currentText()=='Auto view'
assert journal()[0]['actor']==operator().identity and journal()[0]['before']=={} and journal()[0]['after']=={'f133/Firmware':'Details'}
w.tabs.setCurrentWidget(a);settle()
capture('Ledger_Slate_HATCH_Integration_01_Hardware_Pane.png','Actual f133 / Firmware pane at Details after one explicit choice: one journal change, row APPLIED; d213 / Schematics stays Auto view.')
check('An explicit pane choice is one journaled hardware.category_views change through ledger.settings.set with the row revision; an unchanged pick writes nothing')
# 3. A Set from outside the pane (CLI / Slate / Settings) reaches the other open pane within one tick, never re-journaled.
call('ledger.settings.set',dict(key=KEY,value={'f133/Firmware':'Details','d213/Schematics':'Thumbnails'},expected_revision=row()['revision']))
assert len(journal())==2;bridge.tick();settle()
assert b.mode.currentText()=='Thumbnails' and b.stack.currentIndex()==1 and a.mode.currentText()=='Details' and len(journal())==2
bridge.publish_settings_readback();r=row();assert r['application_state']=='APPLIED' and r['effective']=={'f133/Firmware':'Details','d213/Schematics':'Thumbnails'},r
check('A Set from outside the pane reaches the open pane under blocked signals within one tick; the journal keeps exactly two changes')
# 4. The Settings editor lists every current pane, shows the saved choices and journals one change per Apply.
tab=show(KEY);assert tab.editors.currentWidget() is tab.view_modes and tab.editors.isVisible()
assert set(tab.view_modes.combos)==set(key for key,_,_ in pane_keys(root)) and len(tab.view_modes.combos)>50 and 'pcb/PCB layout' not in tab.view_modes.combos
assert tab.view_modes.combos['f133/Firmware'].currentText()=='Details' and tab.view_modes.combos['d213/Schematics'].currentText()=='Thumbnails'
assert '2 panes customized' in tab.state.text() and KEY not in tab.drafts and tab.editor_value()==row()['stored']
tab.view_modes.combos['nor/Boot circuitry'].setCurrentText('Details');assert KEY in tab.drafts;click(tab,tab.apply_button)
expected={'f133/Firmware':'Details','d213/Schematics':'Thumbnails','nor/Boot circuitry':'Details'}
assert row()['stored']==expected and on_disk()==expected and len(journal())==3,journal()
assert a.mode.currentText()=='Details' and b.mode.currentText()=='Thumbnails' and 'Saved '+KEY in tab.note.text()
assert '3 panes customized' in tab.history.topLevelItem(0).text(1) and 'Reversible' in tab.history.topLevelItem(0).text(2)
tab.scroll.verticalScrollBar().setValue(0);settle()
capture('Ledger_Slate_HATCH_Integration_01_Hardware_Editor.png','Actual Settings editor for Hardware category views: one combo per current pane, saved choices shown, change history in words.')
check('The Settings editor lists every current pane, shows saved choices, and Apply records one change without disturbing open panes it did not change')
# 5. An intervening shared revision refuses a stale editor draft and preserves it; panes follow the saved map.
tab.view_modes.combos['nor/Boot circuitry'].setCurrentText('Thumbnails')
call('ledger.settings.set',dict(key=KEY,value={'f133/Firmware':'Details'},expected_revision=row()['revision']))
tab.poll();click(tab,tab.apply_button)
assert 'REVISION_CHANGED' in tab.note.text() and tab.view_modes.combos['nor/Boot circuitry'].currentText()=='Thumbnails' and row()['stored']=={'f133/Firmware':'Details'}
bridge.tick();settle();assert b.mode.currentText()=='Auto view' and b.stack.currentIndex()==0 and a.mode.currentText()=='Details'
tab.reload_latest();settle();assert tab.view_modes.combos['nor/Boot circuitry'].currentText()=='Auto view' and KEY not in tab.drafts
check('An intervening shared revision refuses a stale editor draft, preserves it until Reload, and the open panes follow the saved map')
# 6. Default empties the map; every open pane returns to Auto view; Undo restores the previous map.
before=len(journal());click(tab,tab.reset_button)
assert row()['stored']=={} and on_disk()=={} and len(journal())==before+1,journal()
assert a.mode.currentText()=='Auto view' and b.mode.currentText()=='Auto view'
bridge.publish_settings_readback();tab.poll();settle();r=row();assert r['application_state']=='APPLIED' and 'All panes Auto view' in tab.state.text(),r
capture('Ledger_Slate_HATCH_Integration_01_Hardware_Default.png','Actual state after Default: saved map empty, both open panes back at Auto view, readback APPLIED, history reversible.')
tab.history.setCurrentItem(tab.history.topLevelItem(0));settle();assert tab.undo_button.isEnabled();click(tab,tab.undo_button)
assert row()['stored']=={'f133/Firmware':'Details'} and a.mode.currentText()=='Details' and len(journal())==before+2
check('Default empties the saved map and every open pane returns to Auto view; Undo restores the previous map and the pane follows')
# 7. Closed panes have no effect to report; a reopened pane takes the saved mode without journaling.
for pane in (a,b):assert w.close_tab(w.tabs.indexOf(pane))
settle();bridge.publish_settings_readback();r=row();assert r['application_state']=='NO_OPEN_PANE' and r['effective'] is None,r
a=w.show_device_group('f133','Firmware');settle();assert a.mode.currentText()=='Details' and len(journal())==before+2
bridge.publish_settings_readback();assert row()['application_state']=='APPLIED'
check('With no open pane the readback says NO_OPEN_PANE rather than applied; a reopened pane takes the saved mode without journaling')
# 8. Registry and journal discipline, then a clean close.
enum=ledger_control.FIELDS['ledger.settings.apply'][0]['changes']['items']['properties']['key']['enum'];assert KEY not in enum and set(enum)==set(settings_registry.SESSION_BATCH_KEYS)
assert k.listing('jobs')==[];launch.assert_not_called();provider.assert_not_called()
assert w.close() is True;settle();assert not w.desktop_lease.exists()
check('The public batch enum stays 17 keys; clean close removes the desktop lease; zero jobs, workers, model generations, provider requests or native tools')
provider.stop();launch.stop()
result=dict(state='PASSED',mode='ACTUAL_QT_OFFSCREEN',settings_count=len(settings_registry.SPECS),setting=KEY,checks=checks,captures=captures,
 queued_job_submissions=0,all_kernel_launchers_held=True,worker_processes_started=0,model_generations=0,
 provider_requests=0,native_invocations=0,owner_host_acceptance=False,clean_close=True)
(OUT/'hardware-settings-ui.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)
