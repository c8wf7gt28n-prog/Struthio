"""Actual Qt settings edits, shared typed requests, drafts and consumer readback. Kernel.launch, Kernel.submit and the provider
request are held: nothing here starts a worker, submits a job or sends a request."""
import os,sys,json,tempfile,hashlib
from pathlib import Path
PROGRAM=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('ARC_LEDGER_SETTINGS_CAPTURE_DIR',str(PROGRAM/'build/ui_checks/settings')))
OUT.mkdir(parents=True,exist_ok=True)
RUN=Path(tempfile.mkdtemp(prefix='ledger-settings-ui-'))
os.environ.update(QT_QPA_PLATFORM='offscreen',ARC_LEDGER_EMBEDDED='1',ARC_LEDGER_DISABLE_BOOK_WATCHER='1',ARC1_WORKBENCH_CONFIG_HOME=str(RUN/'profile'),ARC_LEDGER_CONCERN=str(RUN/'Concern'))
sys.path.insert(0,str(PROGRAM));sys.dont_write_bytecode=True
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette
from PySide6.QtTest import QTest
from workbench.qt_app import make_app,WorkbenchWindow
from workbench.session import Session
from unittest.mock import patch
from workbench import locations,ledger_control,stacy_control,settings_registry,clip
from workbench.engineering_kernel import operator,Principal,Kernel
provider=patch.object(clip,'_request',side_effect=AssertionError('No provider request')).start()
launcher=patch.object(Kernel,'launch',side_effect=AssertionError('No worker launch')).start()
submission=patch.object(Kernel,'submit',side_effect=AssertionError('No job submission')).start()
app=make_app([]);root=locations.office(RUN/'workspace');session=Session(RUN/'profile/session.json',root)
w=WorkbenchWindow(root,session,restore=False);bridge=w.ledger_bridge;k=bridge.kernel
checks=[];captures=[]
def settle():
 for name in ('agenda_runner','study_idle'):
  obj=getattr(w,name,None)
  if obj and hasattr(obj,'timer'):obj.timer.stop()
 for _ in range(3):app.processEvents();QTest.qWait(30)
def record(label):checks.append(label)
def row(key):return next(r for r in ledger_control.settings(k)['settings'] if r['key']==key)
def capture(name):
 settle();path=OUT/name;assert w.grab().save(str(path),'PNG')
 captures.append(dict(file=name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),resolution=[w.width(),w.height()]))
def select(key):
 nav=w.settings_navigator;item=nav.items['setting:'+key];parent=item.parent()
 while parent:parent.setExpanded(True);parent=parent.parent()
 nav.tree.scrollToItem(item);settle();QTest.mouseClick(nav.tree.viewport(),Qt.LeftButton,pos=nav.tree.visualItemRect(item).center());settle()
 tab=w.tabs.currentWidget();assert type(tab).__name__=='SettingsTab' and tab.key==key;return tab

def type_number(tab,value):
 field=tab.number.lineEdit();field.setFocus();QTest.keyClick(field,Qt.Key_A,Qt.ControlModifier);QTest.keyClicks(field,str(value));QTest.keyClick(field,Qt.Key_Tab);settle()
 assert tab.number.value()==value

def slate_set(key,value):
 principal=Principal('Slate:typed',frozenset({'read','execute'}));actions=stacy_control.parse('/set '+key+' '+json.dumps(value),k)
 stacy_control.validate_actions(actions,principal,provider=True,private_local=True)
 result=k.dispatch(actions[0]['operation'],actions[0]['arguments'],principal);assert result['ok'],result
 bridge.tick();settle();return result['result']

def selected_id(page):
 item=page.tree.currentItem();return item.data(0,Qt.UserRole)['id'] if item else None
w.resize(1920,1200);w.show();settle();nav=w.settings_navigator;cabinet=w.cabinet_page;cabinet.refresh(force=True);settle()
cabinet.select(cabinet.tree.topLevelItem(0).data(0,Qt.UserRole)['id'],reveal=True);settle();cabinet_selection=selected_id(cabinet);assert cabinet_selection
bridge.show_settings();settle();assert nav.stack.currentIndex()==1
tab=select('reading.code_pt');type_number(tab,18);QTest.mouseClick(tab.apply_button,Qt.LeftButton);settle()
assert tab.apply_button.palette().color(QPalette.ButtonText).name()=='#885e64'
assert row(tab.key)['stored']==18 and row(tab.key)['effective']==18;assert w.reading_profile['code_pt']==18
record('Human keyboard entry and Apply reach the existing reading store and actual desktop profile')
# The real code editor consumes that profile. Preview replacement is intentional.
source=root/'Files/settings_example.py';source.parent.mkdir(exist_ok=True);source.write_text('print("Shared settings example")\n')
code=w.open_document(source);settle();assert code.font().pointSizeF()==18,code.font().pointSizeF()
record('Existing code editor font reads back the changed point size')
tab=bridge.show_settings(key='reading.code_pt');settle();change=slate_set(tab.key,19)
assert tab.number.value()==19 and row(tab.key)['effective']==19
assert any(tab.history.topLevelItem(i).data(0,Qt.UserRole)['actor']=='Slate:typed' for i in range(tab.history.topLevelItemCount()))
record('Deterministic Slate typed request uses the same command, value, revision and history; no model inference')
QTest.mouseClick(tab.undo_button,Qt.LeftButton);settle();assert row(tab.key)['stored']==18 and row(tab.key)['effective']==18
record('Human Undo reverses the Slate typed edit as a new journal revision')
capture('Ledger_Slate_HATCH_Settings_01_Shared.png')
# Drafts survive key switching and replacement of the preview workspace.
type_number(tab,21);base_revision=tab.current['revision'];select('workspace.startup');tab=select('reading.code_pt')
assert tab.number.value()==21 and tab.current['revision']==base_revision
w.open_document(source);settle();tab=bridge.show_settings(key='reading.code_pt');settle()
assert tab.number.value()==21 and tab.current['revision']==base_revision
record('Unsaved settings draft survives key switching and preview replacement')
slate_set(tab.key,22);assert tab.number.value()==21;assert 'newer' in tab.note.text()
QTest.mouseClick(tab.apply_button,Qt.LeftButton);settle()
assert row(tab.key)['stored']==22 and tab.number.value()==21 and 'SETTING_REVISION_CHANGED' in tab.note.text()
record('Concurrent command edit is visible; Apply refuses the stale revision and retains the draft')
capture('Ledger_Slate_HATCH_Settings_01_Conflict.png')
QTest.mouseClick(tab.reload_button,Qt.LeftButton);settle();assert tab.number.value()==22
QTest.mouseClick(tab.reset_button,Qt.LeftButton);settle();assert row(tab.key)['stored']==14
QTest.mouseClick(tab.undo_button,Qt.LeftButton);settle();assert row(tab.key)['stored']==22
record('Explicit reload, shared Default and Undo use current revisions')
# The highlighted string editor retains real selection, insertion and undo semantics.
tab=select('reading.code_family');before=tab.string.text();tab.string.setFocus();QTest.keyClick(tab.string,Qt.Key_A,Qt.ControlModifier)
QTest.keyClicks(tab.string,'Temporary font');QTest.keyClick(tab.string,Qt.Key_Z,Qt.ControlModifier);settle()
assert tab.string.text()==before;record('Native highlighted text selection and keyboard Undo remain available')
# A saved startup policy cannot claim it already changed this desktop launch.
tab=select('workspace.startup');tab.choice.setFocus();QTest.keyClick(tab.choice,Qt.Key_End);settle();assert tab.choice.currentText()=='home'
QTest.mouseClick(tab.apply_button,Qt.LeftButton);settle();pending=row(tab.key)
assert pending['stored']=='home' and pending['effective']=='last' and pending['application_state']=='PENDING_NEXT_LAUNCH'
record('Startup saved as home remains pending with last as the consumed launch policy')
capture('Ledger_Slate_HATCH_Settings_01_Pending.png')
# Separate view structures and persistence, including the fixed footer Trash.
slate_root=nav.items['settings:slate'];slate_root.setExpanded(False);settle();saved=Session(session.path,root).state['settings_navigation']
assert saved['mode']=='settings' and saved['selected']=='setting:workspace.startup' and 'settings:slate' not in saved['expanded']
nav.filter.setText('Appearance');settle()
assert not nav.items['setting:reading.code_pt'].isHidden() and nav.items['setting:workspace.startup'].isHidden()
nav.filter.clear();settle();assert not slate_root.isExpanded()
record('Settings search reveals matching groups and restores the owner’s expansion choices')
trash=w.trash_can;assert trash.parentWidget() is not nav.tree and trash.isVisible()
QTest.mouseClick(nav.cabinet,Qt.LeftButton);settle();assert nav.stack.currentWidget() is cabinet and selected_id(cabinet)==cabinet_selection,(selected_id(cabinet),cabinet_selection)
w.a_ledger_settings.trigger();settle();assert nav.stack.currentIndex()==1 and nav.selected_key()=='workspace.startup'
record('Cabinet page and its selected record survive switching; settings key and expansion reload; Trash stays outside tree scrolling')
# The previous Tools category retains the real tool and adapter inventory.
tab=bridge.show_settings('Tools');settle();assert tab.tools.isVisible() and tab.tools.topLevelItemCount()>0
record('Legacy Tools destination still opens genuine inventory, separate from settings values')
bridge.show_settings(key='workspace.startup');settle()
w.resize(1366,768);settle();assert w.width()==1366 and w.height()==768,(w.width(),w.height())
# HATCH DESK D1b: the settings filter left the left pane (its job is the writing line's Find); the tree fills the Settings tab.
assert w.settings_navigator.tree.isVisible() and not w.settings_navigator.filter.isVisible() and tab is not None
record('Affected layout resizes to 1366 × 768 with scrollable settings content; the Settings tab shows its tree (the filter\'s job is Find\'s)')
with k.db() as db:jobs=db.execute('SELECT count(*) FROM jobs').fetchone()[0]
assert jobs==0
w.close();app.processEvents()
assert row('reading.code_pt')['application_state']=='NO_LIVE_DESKTOP_READBACK',dict(state=row('reading.code_pt')['application_state'],lease=w.desktop_lease.exists(),closing=w._closing,root=str(k.root))
record('A closed desktop receipt is not reported as live even while its process remains alive')
report=dict(state='PASSED',mode='ACTUAL_QT_OFFSCREEN',checks=checks,captures=captures,jobs=jobs,model_generations=0,
 natural_language_setting_selection='NOT_TESTED_NO_REAL_MODEL',native_acceptance=False,
 coverage_keys=[r['key'] for r in ledger_control.SPECS],typed_nodes=settings_registry.nodes(),pending_example={key:pending[key] for key in ('key','stored','effective','application_state','revision')})
(OUT/'ui-smoke.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({key:report[key] for key in ('state','checks','captures','jobs','model_generations')}),flush=True)
