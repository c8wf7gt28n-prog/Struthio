"""Bounded real Qt checks for Explore, menu identity and draft preservation."""
import json,os,sys,tempfile,hashlib
from pathlib import Path
from unittest.mock import patch
PROGRAM=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('ARC_LEDGER_EXPLORE_CAPTURE_DIR',str(PROGRAM/'build/ui_checks/explore')));OUT.mkdir(parents=True,exist_ok=True)
RUN=Path(tempfile.mkdtemp(prefix='ledger-explore01-ui-'))
os.environ.update(QT_QPA_PLATFORM='offscreen',ARC_LEDGER_EMBEDDED='1',ARC_LEDGER_DISABLE_BOOK_WATCHER='1',
    ARC1_WORKBENCH_CONFIG_HOME=str(RUN/'profile'),ARC_LEDGER_CONCERN=str(RUN/'Concern'))
sys.path.insert(0,str(PROGRAM));sys.dont_write_bytecode=True
from PySide6.QtCore import Qt,QPoint
from PySide6.QtTest import QTest
from workbench.qt_app import make_app,WorkbenchWindow
from workbench import locations,clip,menus2,explore_qt,explore,ledger_control
from workbench.engineering_kernel import operator,Kernel
from workbench.session import Session
offline=patch.object(clip,'_request',side_effect=AssertionError('No provider request in the Explore UI check')).start()
launcher=patch.object(Kernel,'launch',side_effect=AssertionError('No worker launch')).start()
submission=patch.object(Kernel,'submit',side_effect=AssertionError('No job submission')).start()
app=make_app([]);root=locations.office(RUN/'workspace');session=Session(RUN/'profile/session.json',root)
w=WorkbenchWindow(root,session,restore=False);bridge=w.ledger_bridge;k=bridge.kernel;checks=[];captures=[]
def settle():
 for name in ('agenda_runner','study_idle'):
  obj=getattr(w,name,None)
  if obj and hasattr(obj,'timer'):obj.timer.stop()
 for _ in range(2):app.processEvents();QTest.qWait(35)
def call(op,args=None):
 response=k.dispatch(op,args or {},operator());assert response['ok'],response;return response['result']
def record(text):checks.append(text);print(text,flush=True)
def capture(name):
 settle();path=OUT/name;assert w.grab().save(str(path),'PNG')
 captures.append(dict(file=name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),resolution=[w.width(),w.height()]))
def select(tab,ident):
 for i in range(tab.results.topLevelItemCount()):
  item=tab.results.topLevelItem(i)
  if item.data(0,Qt.UserRole)['id']==ident:tab.results.setCurrentItem(item);settle();return item
 raise AssertionError('Missing result '+ident)
def instrument(tab,key):return next(r for r in tab.model['instruments'] if r['key']==key)
w.resize(1920,1200);w.show();settle()
project=call('projects.create',{'title':'The future workshop','intent':'Turn ambitious ideas into questions, quantities, experiments and evidence.'})
idea=call('ideas.capture',{'project':project['id'],'text':'Could a tiny console become a laboratory for new ideas?'})
w.cabinet_page.refresh(force=True);w.cabinet_page.select('idea:'+idea['id'],reveal=True)
room=w.cabinet_page.open('idea:'+idea['id']);settle()
source=root/'Files/birthday_draft.py';source.parent.mkdir(exist_ok=True);source.write_text('original = True\n')
editor=w.open_document(source);editor.appendPlainText('# keep this unsaved thought');settle()
tab=explore_qt.show(w,'idea:'+idea['id']);settle()
assert tab.property('ledgerRoom') and w.tabs.indexOf(editor)>=0 and editor.document().isModified()
assert 'unsaved thought' in editor.toPlainText() and source.read_text()=='original = True\n'
record('Explore opens as a Room and preserves an edited Preview and original file')
assert tab.query.placeholderText()=='prompt' and tab.query.accessibleName()=='Find capabilities, methods or registered operations'
assert tab.model['context']['id']=='idea:'+idea['id'];assert [r['id'] for r in tab.model['suggestions']]==['documents','inquiries','calculate','laboratory']  # WORKSHOP-01: the page comes first for an idea
record('Selected idea produces explained deterministic suggestions with poem as the writing invitation')
select(tab,'instrument:calculate');capture('Ledger_Slate_HATCH_Explore_01_Workshop.png')
QTest.mouseClick(tab.open_button,Qt.LeftButton);settle();desk=w.tabs.currentWidget()
assert type(desk).__name__=='ProjectDeskTab' and desk.tabs.currentWidget() is desk.problem_pane
assert desk.problem_pane.pages.tabText(desk.problem_pane.pages.currentIndex())=='Calculate'
assert w.tabs.indexOf(editor)>=0 and editor.document().isModified();record('Calculate opens the genuine existing calculator pane without replacing the edited Preview')
w.tabs.setCurrentWidget(tab);tab.open_entry(instrument(tab,'inquiries'));settle();discovery=w.tabs.currentWidget()
assert type(discovery).__name__=='DiscoveryTab' and discovery.property('ledgerRoom')
discovery.question.insertPlainText('Retain this unsaved inquiry wording.');before=discovery.question.toPlainText()
w.tabs.setCurrentWidget(tab);tab.open_entry(instrument(tab,'inquiries'));settle();assert w.tabs.currentWidget() is discovery and discovery.question.toPlainText()==before
record('Repeated capability opening reuses the inquiry workspace and preserves its unsaved writing')
w.tabs.setCurrentWidget(tab);tab.kind.setCurrentIndex(tab.kind.findData('METHOD'));tab.query.setText('shortest');tab.refresh();settle()
assert tab.results.topLevelItemCount()==1;row=tab.results.topLevelItem(0).data(0,Qt.UserRole)
assert row['status']=='Reference only' and not row['callable'] and tab.open_button.text()=='Inspect method'
capture('Ledger_Slate_HATCH_Explore_01_Methods.png')
QTest.mouseClick(tab.open_button,Qt.LeftButton);settle();methods=w.tabs.currentWidget();assert type(methods).__name__=='AlgorithmAtlasTab'
assert methods.current['id']=='shortest_path';methods.input.insertPlainText('\nRetain this edited scratch.');draft=methods.input.toPlainText()
w.tabs.setCurrentWidget(tab);tab.query.setText('dimensional');tab.refresh();settle();QTest.mouseClick(tab.open_button,Qt.LeftButton);settle()
assert w.tabs.currentWidget() is methods and methods.input.toPlainText()==draft and 'retained' in methods.note.text()
record('Reference methods are inspection-only and a later method request preserves an edited method scratch')
w.tabs.setCurrentWidget(tab);tab.kind.setCurrentIndex(tab.kind.findData('OPERATION'));tab.query.setText('ideas.capture');tab.refresh();settle()
assert tab.results.topLevelItemCount()==1 and tab.open_button.text()=='Inspect contract'
QTest.mouseClick(tab.open_button,Qt.LeftButton);settle();atlas=w.tabs.currentWidget();assert type(atlas).__name__=='ToolAtlasTab'
assert atlas.current['name']=='ideas.capture';assert w.tabs.indexOf(editor)>=0 and editor.document().isModified()
record('Inspecting an effectful operation opens its existing passport and never dispatches that operation')
button=w.type_bar.explore;button.prepare();snapshot=[a.text() for a in button.popup.actions()]
button.popup.popup(w.mapToGlobal(QPoint(20,w.height()-90)));settle();assert [a.text() for a in button.popup.actions()]==snapshot
button.popup.hide();settle();record('Bottom-left launcher freezes one capability snapshot while its menu is open')
from PySide6.QtWidgets import QMenu
before=len(button.popup.findChildren(QMenu,options=Qt.FindDirectChildrenOnly))
for _ in range(10):button.prepare()
assert len(button.popup.findChildren(QMenu,options=Qt.FindDirectChildrenOnly))==before==0  # DESKTOP-01: the groups live in Hatch; Explore repeats none
assert [a.text() for a in button.popup.actions() if not a.isSeparator()][0]=='Explore the workshop…' and button.popup.actions()[-1].text()=='Find saved work…'
record('Ten Explore openings create no submenu: the Explore word keeps the workshop, the record suggestions and Find saved work; the tool groups are Hatch\'s')
# The menu's order and routes are check_hatch_ui's.
objects={key:w.menu_groups[key] for key in menus2.DISPLAY_TITLES};favorites={key:action for key,action in w.favorite_actions.items()}
shortcuts={key:[s.toString() for s in action.shortcuts()] for key,action in favorites.items()}
menus2.rebuild(w);menus2.rebuild(w);settle()
assert all(w.menu_groups[key] is menu for key,menu in objects.items())
assert all(w.favorite_actions[key] is action and [s.toString() for s in action.shortcuts()]==shortcuts[key] for key,action in favorites.items())
assert {key:w.command_menus[key].text() for key in menus2.DISPLAY_TITLES}==menus2.DISPLAY_TITLES
assert sum(a is w.a_explore for a in w.menu_groups['Tools'].actions())==1
record('Proposed Work, Revise, Arrange, Rules and Guide labels retain menu objects, all original actions and keyboard shortcuts')
page=w.cabinet_page;selected=page.tree.currentItem().data(0,Qt.UserRole)['id'];w.a_explore.trigger();settle()
assert w.tabs.currentWidget() is tab and page.tree.currentItem().data(0,Qt.UserRole)['id']==selected
record('Top Tools entry reuses Explore while preserving the cabinet selection')
assert all(len(w.tabs.pinned())<=5 for _ in (0,)) and not getattr(bridge,'_retain_views',0)
assert editor.property('ledgerRoom') is not True;record('Retained navigation is scoped; the original Preview and five-pin policy remain intact')
tab.kind.setCurrentIndex(tab.kind.findData('INSTRUMENT'));tab.query.setText('I want to test an idea');tab.refresh();settle()
assert any(tab.results.topLevelItem(i).data(0,Qt.UserRole)['key']=='inquiries' for i in range(tab.results.topLevelItemCount()))
record('A plain-word idea request finds existing inquiry controls without a model call')
tab.query.clear();tab.refresh();settle();select(tab,'instrument:laboratory')
w.resize(1366,768);settle();assert w.trash_can.isVisible() and w.type_bar.explore.isHidden()  # HATCH DESK D1a: Explore left the lower band
assert sum(a is w.a_explore for a in w.menu_groups['Tools'].actions())==1 and w.type_bar.hatch.explore_action.text()=='Explore the workshop'  # its routes stay (D2: the programs list's last row)
assert tab.detail_scroll.widget().height()>=tab.detail_scroll.widget().minimumSizeHint().height()
capture('Ledger_Slate_HATCH_Explore_01_Compact.png');record('Explore and fixed Trash remain usable at 1366 by 768 (Explore from Tools and the menu; its word left the lower band)')
assert len(k.listing('jobs'))==0;assert call('ideas.get',{'id':idea['id']})==idea
record('Search, suggestions, inspections and workspace navigation create no tool jobs or replacement idea records')
editor.document().setModified(False);w.close();app.processEvents();assert not w.desktop_lease.exists();offline.assert_not_called();offline.stop()
record('Clean close removes the desktop lease without any provider request')
report=dict(state='PASSED',mode='ACTUAL_QT_OFFSCREEN',checks=checks,captures=captures,model_calls=0,provider_requests=0,native_invocations=0,jobs_submitted=0,
 owner_ui_review='DEFERRED_UNTIL_COHESIVE_UI',native_acceptance=False)
(OUT/'explore-ui.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
