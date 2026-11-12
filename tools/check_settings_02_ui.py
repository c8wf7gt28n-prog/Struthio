"""Actual Qt checks for Session batches, layout and credential-safe preferences."""
import os,sys,json,tempfile,hashlib
from unittest.mock import patch
from pathlib import Path
PROGRAM=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('ARC_LEDGER_SETTINGS_CAPTURE_DIR',str(PROGRAM/'build/ui_checks/settings_02')));OUT.mkdir(parents=True,exist_ok=True)
RUN=Path(tempfile.mkdtemp(prefix='ledger-settings02-ui-'))
os.environ.update(QT_QPA_PLATFORM='offscreen',ARC_LEDGER_EMBEDDED='1',ARC_LEDGER_DISABLE_BOOK_WATCHER='1',ARC1_WORKBENCH_CONFIG_HOME=str(RUN/'profile'),ARC_LEDGER_CONCERN=str(RUN/'Concern'))
sys.path.insert(0,str(PROGRAM));sys.dont_write_bytecode=True
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from workbench.qt_app import make_app,WorkbenchWindow
from workbench.session import Session
from workbench.reading_preferences import ReadingDialog,adjust_prose
from workbench import locations,ledger_control,clip,shell2
from workbench.engineering_kernel import operator,Kernel
offline=patch.object(clip,'_request',side_effect=AssertionError('This UI check must not make a provider request')).start()
launcher=patch.object(Kernel,'launch',side_effect=AssertionError('No worker launch')).start()
submission=patch.object(Kernel,'submit',side_effect=AssertionError('No job submission')).start()
path=clip.settings_path();path.parent.mkdir(parents=True,exist_ok=True)
credential={'dpapi':'opaque-ui-fixture'}
path.write_text(json.dumps(dict(schema=clip.SCHEMA,key=credential,model='',include_file=False)))
app=make_app([]);root=locations.office(RUN/'workspace');session=Session(RUN/'profile/session.json',root)
w=WorkbenchWindow(root,session,restore=False);bridge=w.ledger_bridge;k=bridge.kernel
checks=[];captures=[]
def settle():
 for name in ('agenda_runner','study_idle'):
  obj=getattr(w,name,None)
  if obj and hasattr(obj,'timer'):obj.timer.stop()
 for _ in range(3):app.processEvents();QTest.qWait(30)
def read(key):return next(r for r in ledger_control.settings(k)['settings'] if r['key']==key)
def record(label):checks.append(label)
def select(key):
 tab=bridge.show_settings(key=key);nav=w.settings_navigator;item=nav.items['setting:'+key];parent=item.parent()
 while parent:parent.setExpanded(True);parent=parent.parent()
 nav.tree.scrollToItem(item);settle();QTest.mouseClick(nav.tree.viewport(),Qt.LeftButton,pos=nav.tree.visualItemRect(item).center());settle()
 assert tab.key==key;return tab
def number(tab,value):
 field=tab.number.lineEdit();field.setFocus();QTest.keyClick(field,Qt.Key_A,Qt.ControlModifier);QTest.keyClicks(field,str(value));QTest.keyClick(field,Qt.Key_Tab);settle()
def apply(tab):
 QTest.mouseClick(tab.apply_button,Qt.LeftButton);settle();bridge.tick();settle()
 assert 'SETTING_' not in tab.note.text(),tab.note.text()
def capture(name):
 settle();p=OUT/name;assert w.grab().save(str(p),'PNG')
 captures.append(dict(file=name,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),resolution=[w.width(),w.height()]))
w.resize(1920,1200);w.show();settle();bridge.tick();settle()
assert {'settings:ledger','settings:slate'}<=set(w.settings_navigator.items)
assert all('setting:'+spec['key'] in w.settings_navigator.items for spec in ledger_control.SPECS)
record(str(len(ledger_control.SPECS))+' registered definitions project into separate Ledger and Slate settings roots')
# Existing script menu and the registry share the same persisted setting and Undo.
w.shell2.script_action.setChecked(False);settle();bridge.tick();settle()
assert read('appearance.cursive')['stored'] is False and shell2.SCRIPT_ON[0] is False
assert Session(session.path,root).state['cursive'] is False
cursive=read('appearance.cursive')['latest_change'];assert cursive['key']=='appearance.cursive'
tab=select('appearance.cursive');QTest.mouseClick(tab.undo_button,Qt.LeftButton);settle();assert shell2.SCRIPT_ON[0] is True
record('Existing script menu writes shared history; saved preference reopens and registry Undo updates actual presentation')
# Numeric settings preserve integer typing and read back actual dock dimensions.
tab=select('layout.navigator_width');number(tab,420);apply(tab)
actual=read(tab.key);assert type(actual['stored']) is int and actual['stored']==420
assert actual['effective']==w.nav_dock.width(),actual
assert abs(w.nav_dock.width()-420)<=3,w.nav_dock.width()
record('Highlighted integer edit changes the actual left dock and reports measured width')
tab=select('layout.output_height');number(tab,260);apply(tab)
assert read(tab.key)['application_state']=='WAITING_FOR_PANEL',read(tab.key)
record('Output height stays pending while the real output panel is hidden')
capture('Ledger_Slate_HATCH_Settings_02_Layout.png')
tab=select('layout.output_visible');tab.boolean.setCurrentIndex(1);apply(tab);assert w.output_dock.isVisible()
bridge.publish_settings_readback();assert read('layout.output_height')['effective']==w.output_dock.height()
tab=select('layout.output_tab');tab.choice.setCurrentText('Problems');apply(tab)
assert w.output_tabs.tabText(w.output_tabs.currentIndex())=='Problems'
record('Showing the panel applies its height; output-page choice reads back the existing Problems tab')
tab=select('layout.output_visible');tab.boolean.setCurrentIndex(0);apply(tab)
# The earlier reading editor now commits through one shared validated profile batch.
dialog=ReadingDialog(w);dialog.show();settle();dialog.controls['code_pt'].setValue(18);dialog.controls['prose_pt'].setValue(20)
dialog.save();settle();assert 'shared settings' in dialog.note.text(),dialog.note.text()
code=read('reading.code_pt');prose=read('reading.prose_pt')
assert code['stored']==18 and prose['stored']==20
assert code['latest_change']['batch']==prose['latest_change']['batch']
dialog.close();settle();record('Legacy reading editor saves two values in one Session batch and the same per-key history')
source=root/'Files/settings_review.py';source.parent.mkdir(exist_ok=True);source.write_text('print("Shared reading settings")\n')
editor=w.open_document(source);settle();assert editor.font().pointSizeF()==18
record('A genuine code editor consumes the changed point size')
tab=select('reading.code_pt');QTest.mouseClick(tab.undo_button,Qt.LeftButton);settle()
assert read('reading.code_pt')['stored']==14 and read('reading.prose_pt')['stored']==20
adjust_prose(w,1);settle();assert read('reading.prose_pt')['stored']==21
record('Registry Undo and the existing prose-size shortcut both use the shared journal')
capture('Ledger_Slate_HATCH_Settings_02_Reading.png')
# A stale legacy dialog must retain the draft and apply none of its batch.
dialog=ReadingDialog(w);dialog.show();settle();dialog.controls['code_pt'].setValue(19);dialog.controls['prose_pt'].setValue(24)
opened=read('reading.prose_pt');result=k.dispatch('ledger.settings.set',dict(key=opened['key'],value=22,expected_revision=opened['revision']),operator());assert result['ok']
dialog.save();settle();assert 'SETTING_REVISION_CHANGED' in dialog.note.text()
assert dialog.controls['code_pt'].value()==19 and read('reading.code_pt')['stored']==14
assert read('reading.prose_pt')['stored']==22;dialog.close();settle()
record('Concurrent reading change refuses the whole legacy batch and preserves all unsaved dialog values')
# The preference editor does not touch credentials or make an API request.
tab=select('gemini.model');tab.string.setFocus();QTest.keyClick(tab.string,Qt.Key_A,Qt.ControlModifier);QTest.keyClicks(tab.string,'ui-review-model');apply(tab)
assert clip.preferences()['model']=='ui-review-model';assert json.loads(path.read_text())['key']==credential
w.open_clip();settle();overlay=w.clip_overlay;assert overlay.settings.model=='ui-review-model'
record('Gemini model preference reaches the existing file and next-request cache with credential bytes unchanged')
QTest.mouseClick(overlay.include,Qt.LeftButton);settle();bridge.tick();settle();assert read('gemini.include_file')['stored'] is True
assert read('gemini.include_file')['latest_change']['actor']=='desktop-owner'
tab=select('gemini.include_file');QTest.mouseClick(tab.undo_button,Qt.LeftButton);settle();bridge.tick();settle()
assert clip.preferences()['include_file'] is False and overlay.include.isChecked() is False
w.open_clip();settle()
record('Existing source-sharing control and registry Undo use the same owner-authorized setting')
tab=select('gemini.model');tab.note.setText('UI review fixture · preference only; no Gemini request was sent.')
capture('Ledger_Slate_HATCH_Settings_02_Provider.png')
# Optional corrupt configuration must not break the rest of Ledger or discard a draft.
tab.string.setText('unsaved-review-model');settle();path.write_text('invalid optional-provider fixture')
bridge.tick();settle();assert not tab.apply_button.isEnabled() and not tab.editors.isVisible()
assert bridge.settings_drafts['gemini.model']['value']=='unsaved-review-model'
overlay._ask();assert not overlay.busy
record('Unavailable provider store disables its editor, preserves the draft and keeps Ledger operational')
path.write_text(json.dumps(dict(schema=clip.SCHEMA,key=credential,model='repaired-review-model',include_file=False)))
bridge.tick();settle();assert tab.string.text()=='unsaved-review-model'
QTest.mouseClick(tab.apply_button,Qt.LeftButton);settle();assert 'SETTING_REVISION_CHANGED' in tab.note.text()
QTest.mouseClick(tab.reload_button,Qt.LeftButton);settle();assert tab.string.text()=='repaired-review-model'
record('Repair restores editing without silently replacing a retained draft or its original revision')
w.resize(1366,768);settle();assert w.size().width()==1366 and w.size().height()==768
assert w.trash_can.isVisible();record('Affected layout resizes to 1366 by 768 and Trash remains fixed outside the tree')
with k.db() as db:jobs=db.execute('SELECT count(*) FROM jobs').fetchone()[0]
assert jobs==0;w.close();app.processEvents();assert not w.desktop_lease.exists()
offline.assert_not_called()
record('Window close saves Session state and removes the desktop lease')
report=dict(state='PASSED',mode='ACTUAL_QT_OFFSCREEN',checks=checks,captures=captures,settings_count=len(ledger_control.SPECS),jobs=jobs,
 model_generations=0,provider_requests=0,engineering_solver_calls=0,native_acceptance=False,
 natural_language_setting_selection='NOT_TESTED_WITH_A_REAL_MODEL')
(OUT/'ui-smoke-02.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
