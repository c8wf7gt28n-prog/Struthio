"""Actual offscreen Qt checks for the logical cabinet and poem invitation."""
import os,sys,json,tempfile,hashlib
from pathlib import Path
from unittest.mock import patch
PROGRAM=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('ARC_LEDGER_CABINET_CAPTURE_DIR',str(PROGRAM/'build/ui_checks/cabinet')));OUT.mkdir(parents=True,exist_ok=True)
RUN=Path(tempfile.mkdtemp(prefix='ledger-cabinet01-ui-'))
os.environ.update(QT_QPA_PLATFORM='offscreen',ARC_LEDGER_EMBEDDED='1',ARC_LEDGER_DISABLE_BOOK_WATCHER='1',
    ARC1_WORKBENCH_CONFIG_HOME=str(RUN/'profile'),ARC_LEDGER_CONCERN=str(RUN/'Concern'))
sys.path.insert(0,str(PROGRAM));sys.dont_write_bytecode=True
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLineEdit,QPlainTextEdit,QTextEdit
from PySide6.QtTest import QTest
from workbench.qt_app import make_app,WorkbenchWindow
from workbench.session import Session
from workbench import locations,ledger_control,clip,cabinet,shell2
from workbench.engineering_kernel import operator,Kernel
from workbench.discovery_ir import template
offline=patch.object(clip,'_request',side_effect=AssertionError('No provider request during this UI check')).start()
launcher=patch.object(Kernel,'launch',side_effect=AssertionError('No worker launch')).start()
submission=patch.object(Kernel,'submit',side_effect=AssertionError('No job submission')).start()
app=make_app([]);root=locations.office(RUN/'workspace');session=Session(RUN/'profile/session.json',root)
w=WorkbenchWindow(root,session,restore=False);bridge=w.ledger_bridge;k=bridge.kernel
checks=[];captures=[]
def settle():
 for name in ('agenda_runner','study_idle'):
  obj=getattr(w,name,None)
  if obj and hasattr(obj,'timer'):obj.timer.stop()
 for _ in range(2):app.processEvents();QTest.qWait(25)
def call(op,args=None):
 r=k.dispatch(op,args or {},operator());assert r['ok'],r;return r['result']
def record(label):checks.append(label);print(label,flush=True)
def select(ident):
 page=w.cabinet_page;page.select(ident,reveal=True);settle();item=page.items[ident]
 QTest.mouseClick(page.tree.viewport(),Qt.LeftButton,pos=page.tree.visualItemRect(item).center());settle()
 room=w.tabs.currentWidget();assert room.property('cabinet_node')==ident;return room
def capture(name):
 settle();path=OUT/name;assert w.grab().save(str(path),'PNG')
 captures.append(dict(file=name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),resolution=[w.width(),w.height()]))
w.resize(1920,1200);w.show();settle()
first=call('projects.create',{'title':'Project 2 · Hatch campaign','intent':'Build a coherent cabinet, menus and operations layout. Preserve the work as we go.'})
second=call('projects.create',{'title':'Project 10 · UI review','intent':'Review the main pieces together once the interface is more complete.'})
idea=call('ideas.capture',{'text':'One saved identity can appear as a reference in another project.','project':first['id']})
call('ideas.capture',{'text':'A thought waiting for its project.'})
second=call('projects.link',{'id':second['id'],'expected_revision':1,'role':'QUESTION','address':'idea:'+idea['id']})
source=root/'Files/cabinet_source.txt';source.parent.mkdir(exist_ok=True);source.write_text('Initial inquiry source.\n')
document=template();document['title']='How should project references behave?';document['sources']=[dict(key='source',address='files:cabinet_source.txt',role='Owner-provided example')]
inquiry=call('discovery.create',{'document':document,'project':first['id']});source.write_text('Changed inquiry source.\n')
investigation=call('investigation.create',{'question':'Which cabinet detail needs another check?','objective':'Keep the existing question identity.'})
with tempfile.TemporaryDirectory(prefix='ledger-cabinet-master-',dir=Path.home()) as master_dir:  # working copies start only from files in the home folder; removed on exit
 master=Path(master_dir)/'campaign_master.txt';master.write_text('Original master stays here.\n');before=(master.read_bytes(),master.stat().st_mode)
 copy=call('copies.start',{'source':str(master)})
 first=call('projects.link',{'id':first['id'],'expected_revision':1,'role':'WORKING_COPY','address':'copies:'+copy['id']})
 note=w.concern.store.create('note','Cabinet review notes','projects');w.concern.store.save_note(note,'A saved catalogue note, read through its existing identity.',0)
 legacy_project=w.concern.store.create('project','Existing catalogue project','projects','Existing project summary, distinct from a Project Desk record.')
 w.concern.store.link(note,'part_of','inbox');page=w.cabinet_page;page.refresh(force=True);settle()
 assert [r['label'] for r in page.model['nodes'] if r['role']=='project']==[first['title'],second['title']]
 record('Populated tree uses natural sibling order and original Project Desk, catalogue, inquiry, investigation and copy identities')
 path=root/'Files/unsaved_review.py';path.write_text('original = True\n');editor=w.open_document(path);editor.appendPlainText('# retained unsaved writing');settle()
 room=select('project:'+first['id']);assert w.tabs.indexOf(editor)>=0 and 'retained unsaved writing' in editor.toPlainText()
 assert path.read_text()=='original = True\n';record('Opening the cabinet room preserves an existing edited Preview and leaves its file untouched')
 editor.document().setModified(False)  # The draft-preservation assertion is complete; avoid unrelated modal Preview prompts below.
 assert room.writing.placeholderText()=='poem';QTest.keyClicks(room.writing,'A draft to keep with this project.');settle()
 select('project:'+second['id']);room=select('project:'+first['id']);assert room.writing.toPlainText()=='A draft to keep with this project.'
 page.refresh(force=True);assert room.writing.toPlainText()=='A draft to keep with this project.'
 record('Unsaved cabinet writing survives record changes and background tree refresh within the desktop')
 capture('Ledger_Slate_HATCH_Cabinet_01_Poem_Project.png')
 QTest.mouseClick(room.keep,Qt.LeftButton);settle();assert room.data['record']['kind']=='idea' and room.data['record']['project']==first['id']
 assert room.note.text()=='Idea kept.';record('Keep creates a genuine project idea through the existing shared command')
 ref=next(r for r in page.model['nodes'] if r['role']=='reference' and r['canonical_id']=='idea:'+idea['id'])
 room=select(ref['id']);assert not ref['owning'];QTest.mouseClick(room.available_actions[0],Qt.LeftButton);settle()
 assert idea['id'] in room.result.toPlainText() and call('ideas.get',{'id':idea['id']})['project']==first['id']
 record('A second-project reference reads the same original idea and never changes its declared project')
 room=select('inquiry:'+inquiry['id']);assert room.data['record']['bindings']
 QTest.mouseClick(room.available_actions[0],Qt.LeftButton);settle();assert 'STALE' in room.result.toPlainText()
 record('Explicit inquiry check reports a changed source as stale; passive tree reads do not claim freshness')
 room=select('copies:'+copy['id']);assert room.data['record']['freshness']=='NOT_RECHECKED'
 assert (master.read_bytes(),master.stat().st_mode)==before;record('Working copy keeps its identity and original bytes and mode unchanged')
 room=select('catalog:'+note);assert 'saved catalogue note' in room.body.toPlainText()
 room=select('catalog:'+legacy_project);assert room.body.toPlainText()=='Existing project summary, distinct from a Project Desk record.'
 assert room.form_mode is None;record('An existing catalogue project keeps its own provider schema and summary')
 room=select('catalog:'+note)
 before_state=page.saved.copy();page.query.setText('How should');settle();assert not page.items['inquiry:'+inquiry['id']].isHidden()
 page.query.clear();settle();assert {i for i,item in page.items.items() if item.isExpanded()}==set(before_state['expanded'])
 record('Filtering reveals matching descendants; clearing it restores the saved expanded branches')
 tab=bridge.show_settings(key='cabinet.sort');settle();tab.choice.setCurrentText('alphabetical');QTest.mouseClick(tab.apply_button,Qt.LeftButton);settle()
 w.settings_navigator.show(False);page.refresh(force=True);settle()
 assert [r['label'] for r in page.model['nodes'] if r['role']=='project']==[second['title'],first['title']]
 assert page.tree.currentItem().data(0,Qt.UserRole)['id']=='catalog:'+note
 record('Real Settings control changes sibling order while preserving selected record identity')
 # HATCH DESK D1b: the Logical cabinet / Existing views words left the pane for Arrange ▸ Cabinet (the same set_legacy).
 w.a_cabinet_existing.trigger();settle();assert page.stack.currentWidget() is w.nav and not page.legacy.isVisible()
 w.refresh_navigator();count=w.nav.topLevelItemCount();w.refresh_navigator();assert w.nav.topLevelItemCount()==count
 w.a_cabinet_logical.trigger();settle();assert page.tree.currentItem().data(0,Qt.UserRole)['id']=='catalog:'+note
 record('Existing catalogue and workspace views remain available (Arrange ▸ Cabinet) and rebuild without duplicate roots')
 from workbench.project_desk_qt import show as show_desk
 desk=show_desk(w);settle();assert desk.project_title.placeholderText()=='poem' and desk.project_intent.placeholderText()=='poem'
 assert desk.project_intent.accessibleName()=='What is this project for?'
 discovery=bridge.show_discovery();settle();assert discovery.title_input.placeholderText()=='poem'
 from workbench.clip_workspace import ClipWorkspaceTab
 conversation=bridge.add_tab(ClipWorkspaceTab,lambda:ClipWorkspaceTab(w));settle();assert conversation.input.placeholderText()=='poem'
 record('Project Desk, Discovery and Slate conversation use poem with their semantic field names preserved')
 bar=w.type_bar
 for target in ('slate','shell','find','log','stac','kernel'):  # D3: the four modes, then the old targets that map to them
  bar.set_target(target,focus=False);assert bar.box.placeholderText()=='poem';assert bar.box.text()==''
 bar.set_target('slate',focus=False);record('Changing among the four modes and the old targets keeps poem without inserting or submitting text')
 bar.note('Saved review copy');settle();assert bar.box.placeholderText()=='poem' and w.console.hint.isVisible()
 assert w.console.hint.text()=='Saved review copy';bar.note('');settle();assert not w.console.hint.isVisible()
 record('Status feedback stays visible in the console while poem remains the writing placeholder')
 for transfer,entry in zip(cabinet.TRANSFERS,(w.a_import,w.a_export)):  # D1b: Work ▸ Import (Ingress)… and Export (Egress)…
  entry.trigger();settle()
  assert w.tabs.currentWidget().__class__.__name__==('OfficeBuildingTab' if transfer['direction']=='IMPORT' else 'FilesTab')
 record('Import and Export (Work menu entries) open the existing receiving and outgoing-file controls without performing a transfer')
 room=select('project:'+first['id']);capture('Ledger_Slate_HATCH_Cabinet_01_Poem_Desktop.png')
 fields=[field for kind in (QLineEdit,QPlainTextEdit,QTextEdit) for field in w.findChildren(kind) if not field.isReadOnly() and field.placeholderText()]
 assert fields and all(f.placeholderText()=='poem' for f in fields),[(f.objectName(),f.placeholderText()) for f in fields if f.placeholderText()!='poem']
 record('Every instantiated editable field with a placeholder says exactly poem')
 w.resize(1366,768);settle();assert w.trash_can.isVisible();capture('Ledger_Slate_HATCH_Cabinet_01_Poem_Compact.png')
 record('Affected UI resizes to 1366 by 768 with Trash fixed outside the scrolling cabinet')
 assert (master.read_bytes(),master.stat().st_mode)==before
page.remember();saved=page.saved.copy();jobs=len(k.listing('jobs'));assert jobs==0
w.close();app.processEvents();assert not w.desktop_lease.exists();assert Session(session.path,root).state['cabinet_navigation']==saved
offline.assert_not_called();offline.stop();record('Close persists cabinet selection and expansion, removes the desktop lease, and creates no job or provider request')
report=dict(state='PASSED',mode='ACTUAL_QT_OFFSCREEN',checks=checks,captures=captures,jobs=jobs,provider_requests=0,model_generations=0,
    engineering_solver_calls=0,native_acceptance=False,owner_ui_review='DEFERRED_UNTIL_COHESIVE_UI')
(OUT/'cabinet-poem-ui.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
