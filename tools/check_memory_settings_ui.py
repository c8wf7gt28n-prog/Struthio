"""Actual Qt checks of shared owner-memory Settings without inference."""
import copy,json,os,sys,tempfile,hashlib
from pathlib import Path
from unittest.mock import patch
PROGRAM=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('ARC_LEDGER_SETTINGS03_CAPTURE_DIR',str(PROGRAM/'build/ui_checks/memory_settings')));OUT.mkdir(parents=True,exist_ok=True)
RUN=Path(tempfile.mkdtemp(prefix='ledger-settings03-ui-'))
os.environ.update(QT_QPA_PLATFORM='offscreen',ARC_LEDGER_EMBEDDED='1',ARC_LEDGER_DISABLE_BOOK_WATCHER='1',
 ARC1_WORKBENCH_CONFIG_HOME=str(RUN/'profile'),ARC_LEDGER_CONCERN=str(RUN/'Concern'))
sys.path.insert(0,str(PROGRAM));sys.dont_write_bytecode=True
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from workbench.qt_app import make_app,WorkbenchWindow
from workbench import locations,clip,settings_registry,stacy_control
from workbench.engineering_kernel import operator,Principal,Kernel
from workbench.session import Session
app=make_app([]);root=locations.office(RUN/'workspace');session=Session(RUN/'profile/session.json',root)
provider=patch.object(clip,'_request',side_effect=AssertionError('No provider request')).start()
launcher=patch.object(Kernel,'launch',side_effect=AssertionError('No worker launch')).start()
submission=patch.object(Kernel,'submit',side_effect=AssertionError('No job submission')).start()
w=WorkbenchWindow(root,session,restore=False);k=w.ledger_bridge.kernel;checks=[];captures=[]
def settle(window=w):
 for name in ('agenda_runner','study_idle'):
  obj=getattr(window,name,None)
  if obj and hasattr(obj,'timer'):obj.timer.stop()
 for _ in range(2):app.processEvents();QTest.qWait(35)
def call(op,args=None,principal=None):
 r=k.dispatch(op,args or {},principal or operator());assert r['ok'],r;return r['result']
def row(key):return next(r for r in call('ledger.settings')['settings'] if r['key']==key)
def check(text):checks.append(text);print(text,flush=True)
def capture(name,window=w):
 window.operations_panel.refresh();settle(window);p=OUT/name;assert window.grab().save(str(p),'PNG')
 captures.append(dict(file=name,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),resolution=[window.width(),window.height()]))
def show(key,window=w):
 tab=window.ledger_bridge.show_settings(key=key);settle(window);return tab
def apply(tab):
 tab.scroll.ensureWidgetVisible(tab.apply_button);settle();QTest.mouseClick(tab.apply_button,Qt.LeftButton);settle()
w.resize(1920,1200);w.show();settle()
enabled='memory.profile.enabled';weight='memory.weight.owner_statement';tiny='memory.weight.owner_confirmed_choice'
tab=show(enabled)
assert not tab.apply_button.isEnabled() and tab.current['application_state']=='PROFILE_NOT_IMPORTED'
assert all('setting:'+key in w.settings_navigator.items for key in settings_registry.MEMORY_KEYS)
capture('Ledger_Slate_HATCH_Settings_03_Missing.png')
check('Five genuine memory settings appear under Slate / Memory; missing profiles remain unavailable rather than fabricated')
seed=RUN/'owner-reference.json';seed.write_text(json.dumps(dict(schema='arc.stacy.owner_personality_seed/1',name='Owner fixture',version='1',
 stacy_expression=dict(default_character='Keep questions curious and evidence explicit.',inherit_from_ryan=[],retain_independently=[]))))
original=call('memory.profile.import',{'path':str(seed)});tab=show(weight)
assert tab.editors.currentWidget() is tab.string and tab.string.placeholderText()=='poem'
assert tab.string.text()=='2.0' or tab.string.text()=='2'
check('Existing profile values are read directly and numeric writing uses a precise poem passage')
tab.string.setText('3.125');apply(tab)
assert call('memory.profile')['parameters']['weights']['owner_statement']==3.125
assert row(weight)['stored']==row(weight)['effective']==3.125
assert call('memory.profile')['original_sha256']==original['original_sha256']
capture('Ledger_Slate_HATCH_Settings_03_Memory.png')
check('Apply updates the original profile and shared setting history without altering the imported reference')
assert tab.undo_button.isEnabled();QTest.mouseClick(tab.undo_button,Qt.LeftButton);settle()
assert row(weight)['stored']==2 and 'restored' in tab.note.text().lower()
check('The existing Undo control restores a value as a new guarded journal revision')
tab.string.setText('3.25');old_revision=tab.current['revision']
parameters=copy.deepcopy(call('memory.profile')['parameters']);parameters['soft_half_life_days']=200
call('memory.profile.configure',{'parameters':parameters});tab.poll();settle()
assert tab.current['revision']==old_revision and tab.string.text()=='3.25'
apply(tab);assert 'REVISION_CHANGED' in tab.note.text() and tab.string.text()=='3.25' and row(weight)['stored']==2
capture('Ledger_Slate_HATCH_Settings_03_Conflict.png')
check('A direct legacy profile change blocks stale Apply while preserving the highlighted draft')
tab.reload_latest();tab.string.setText('3.25');apply(tab)
assert call('memory.profile')['parameters']['soft_half_life_days']==200
assert call('memory.profile')['parameters']['weights']['owner_statement']==3.25
check('Explicit reload and Apply preserve other profile parameters rather than replacing a stale whole profile')
QTest.mouseClick(tab.reset_button,Qt.LeftButton);settle();assert row(weight)['stored']==2
check('Default restores the genuine original parameter default through the same owner-checked route')
tab=show(enabled);tab.boolean.setCurrentIndex(0);apply(tab)
assert not call('memory.profile')['enabled'] and row(enabled)['effective'] is False
tab=show('memory.weight.owner_correction');assert tab.current['application_state']=='PROFILE_DISABLED' and tab.current['effective'] is None and tab.current['stored']==4
capture('Ledger_Slate_HATCH_Settings_03_Disabled.png')
check('A disabled profile shows stored parameters without claiming an active reply effect')
tab=show(enabled);tab.boolean.setCurrentIndex(1);apply(tab)
parameters=copy.deepcopy(call('memory.profile')['parameters']);parameters['weights']['owner_confirmed_choice']=1e-20
call('memory.profile.configure',{'parameters':parameters});tab=show(tiny)
assert tab.string.text()=='1e-20' and tab.editor_value()==1e-20 and tiny not in tab.drafts
check('An existing very small legal weight is displayed without rounding or a phantom draft')
tab.string.setText('not a number');apply(tab)
assert tab.string.text()=='not a number' and row(tiny)['stored']==1e-20 and 'preserved' in tab.note.text()
tab.reload_latest()
check('Invalid numeric writing leaves profile values unchanged and preserves the draft')
other=call('ledger.settings',principal=operator('another-owner'))
assert all(r['stored'] is None and r['latest_change'] is None for r in other['settings'] if r['key'] in settings_registry.MEMORY_KEYS)
context=call('ledger.context');assert settings_registry.MEMORY_KEYS.isdisjoint(context['settings'])
assert context['settings']['stacy.provider']=='local'
try:stacy_control.validate_actions([stacy_control.call('ledger.settings',{})],operator(),provider=True);raise AssertionError('Private broad read accepted')
except ValueError:pass
check('Owner-private values and histories are isolated and omitted from the optional activity-sharing aggregate')
assert call('memory.profile')['original_sha256']==original['original_sha256']
assert k.listing('jobs')==[];assert w.close() is True;settle();assert not w.desktop_lease.exists()
w2=WorkbenchWindow(root,Session(RUN/'profile/session.json',root),restore=False);w2.resize(1366,768);w2.show();settle(w2)
tab2=show(tiny,w2);assert tab2.string.text()=='1e-20' and tab2.current['stored']==1e-20
assert w2.shell2.top.programs.isVisible() and w2.trash_can.isVisible() and w2.operations_monitors.isVisible() and w2.return_thread.footer.isVisible()
capture('Ledger_Slate_HATCH_Settings_03_Compact.png',w2)
check('A fresh laptop-size desktop reads the same stored profile while retaining the fixed Trash, Stop, monitors and return footer')
assert w2.close() is True;settle(w2);assert not w2.desktop_lease.exists();provider.assert_not_called();provider.stop()
check('Clean close starts no model, provider request or tool job; stored preferences are not claimed as model compliance')
result=dict(state='PASSED',mode='ACTUAL_QT_OFFSCREEN',checks=checks,captures=captures,
 jobs_submitted=0,model_calls=0,provider_requests=0,native_invocations=0,native_acceptance=False,
 profile_fixture='DISPOSABLE_OWNER_REFERENCE',clean_close=True)
(OUT/'memory-settings-ui.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)
