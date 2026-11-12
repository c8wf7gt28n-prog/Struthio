"""Actual Qt filing/edit checks on disposable private memory; no model runs."""
import json,os,sys,tempfile,hashlib,uuid
from pathlib import Path
from unittest.mock import patch
PROGRAM=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('ARC_LEDGER_MEMORY_CAPTURE_DIR',str(PROGRAM/'build/ui_checks/memory_cabinet')));OUT.mkdir(parents=True,exist_ok=True)
RUN=Path(tempfile.mkdtemp(prefix='ledger-memory01-ui-'))
os.environ.update(QT_QPA_PLATFORM='offscreen',ARC_LEDGER_EMBEDDED='1',ARC_LEDGER_DISABLE_BOOK_WATCHER='1',
 ARC1_WORKBENCH_CONFIG_HOME=str(RUN/'profile'),ARC_LEDGER_CONCERN=str(RUN/'Concern'))
sys.path.insert(0,str(PROGRAM));sys.dont_write_bytecode=True
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from workbench.qt_app import make_app,WorkbenchWindow
from workbench import locations,clip
from workbench.engineering_kernel import operator,Kernel
from workbench.session import Session
from workbench.settings_registry import BY_KEY,SPECS,MEMORY_KEYS
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
def call(op,args=None):
 r=k.dispatch(op,args or {},operator());assert r['ok'],r;return r['result']
def check(text):checks.append(text);print(text,flush=True)
def capture(name,window=w):
 window.operations_panel.refresh();settle(window);p=OUT/name;assert window.grab().save(str(p),'PNG')
 captures.append(dict(file=name,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),resolution=[window.width(),window.height()]))
def direction(text):
 return call('memory.feedback',dict(id=uuid.uuid4().hex,preference='technical_depth',context='general',feedback=1,instruction=text,
  source_reference='Owner direction kept during a power-study fixture',kind='owner_statement',soft=False))
def open_record(ident,window=w):
 window.cabinet_page.refresh(force=True);window.cabinet_page.select(ident,reveal=True);room=window.cabinet_page.open(ident);settle(window);return room
def save_correction(room):
 room.scroll.ensureWidgetVisible(room.direction_editor.save);settle();QTest.mouseClick(room.direction_editor.save,Qt.LeftButton);settle()
w.resize(1920,1200);w.show();settle()
seed=RUN/'owner-seed.json';seed.write_text(json.dumps({'schema':'arc.stacy.owner_personality_seed/1','name':'Owner fixture','version':'1',
 'stacy_expression':{'default_character':'Precise with sources; imaginative with ideas.','inherit_from_ryan':[],'retain_independently':[]}}))
original_profile=call('memory.profile.import',{'path':str(seed)})
first=direction('Keep the assumptions visible before choosing a calculation.')
task=call('memory.task.create',{'title':'Power study: what remains uncertain?'})
checkpoint=call('memory.checkpoint.save',dict(task=task['id'],expected_previous='',note=dict(goal='State the uncertainty.',constraints=[],findings=[],contradictions=[],next_step='Read the original limits.',summary='Owner notes, not measured proof.'),references=[],jobs=[]))
lesson=call('memory.lesson.propose',{'title':'Compare the declared limits','body':'Read the original ratings, then record assumptions before calculating.','references':[]})
fid='memory:feedback:'+first['id'];room=open_record(fid)
assert {'memory:root','memory:directions','memory:tasks','memory:procedures'}<=set(w.cabinet_page.items)
assert room.data['node']['provider']=='slate_memory' and room.data['record']['id']==first['id']
check('The left cabinet files existing owner directions, task memory and procedures under stable typed identities')
assert 'Owner direction kept' in room.body.toPlainText() and 'actual context selection' in room.body.toPlainText()
assert room.direction_editor.begin.isEnabled();QTest.mouseClick(room.direction_editor.begin,Qt.LeftButton);settle()
ed=room.direction_editor;new_words='Separate assumptions, source statements and measured results.'
ed.writing.setPlainText(new_words);ed.reason.setText('Make the evidence distinction explicit.')
assert ed.writing.placeholderText()==ed.reason.placeholderText()=='poem'
room.scroll.ensureWidgetVisible(ed.writing);capture('Ledger_Slate_HATCH_Memory_01_Direction.png')
check('Direction editing shows origin and context, uses poem passages, and requires a reason for the correction')
save_correction(room);new_id=room.data['record']['id'];assert new_id!=first['id'] and room.current=='memory:feedback:'+new_id
events={row['id']:row for row in call('memory.feedback.list')['events']};assert events[first['id']]==first
assert events[new_id]['instruction']==new_words and first['id'] in events[new_id]['supersedes']
assert call('memory.profile')['original_sha256']==original_profile['original_sha256']
preferences=call('memory.preferences',{'context':'engineering_execution'})
assert preferences['profile_context']['data']['preferences'][0]['owner_direction']==new_words
check('Keep appends an owner correction through the original feedback logic and the existing local preference path; the imported original is unchanged')
room=open_record(fid);assert room.data['record']['state']=='SUPERSEDED' and not room.direction_editor.begin.isEnabled()
assert first['instruction'] in room.body.toPlainText();capture('Ledger_Slate_HATCH_Memory_01_History.png')
check('Earlier words remain readable as inactive history and cannot be silently edited in place')
active='memory:feedback:'+new_id;room=open_record(active);ed=room.direction_editor;ed.start()
proposed='Keep the unmeasured part visible beside every estimate.';reason='Retain the uncertainty in plain sight.'
ed.writing.setPlainText(proposed);ed.reason.setText(reason)
open_record('memory:task:'+task['id']);assert w.ledger_bridge.cabinet_drafts[active]==dict(text=proposed,title=reason)
assert w.return_thread.capture();stored=call('ledger.session.read');assert any(row['id']==active and row['text']==proposed for row in stored['drafts'])
check('Unfinished corrections survive record switches and use the existing return-copy draft format')
room=open_record(active);ed=room.direction_editor
assert ed.writing.toPlainText()==proposed and not ed.save.isEnabled() and ed.guard is None
check('Reopening a correction draft requires explicit review of the shown history before keeping')
ed.start();competing=direction('A second owner statement changes this preference history.')
before=call('memory.feedback.list');save_correction(room)
assert 'history changed' in room.note.text().lower() and ed.writing.toPlainText()==proposed
assert call('memory.feedback.list')==before
room.scroll.ensureWidgetVisible(ed.save);capture('Ledger_Slate_HATCH_Memory_01_Conflict.png')
check('A competing history change blocks the stale correction while retaining the proposed words')
room=open_record(active);ed=room.direction_editor;assert not ed.save.isEnabled();ed.start();save_correction(room)
current=room.current;current_id=room.data['record']['id'];assert current!=active
events={row['id']:row for row in call('memory.feedback.list')['events']}
assert {new_id,competing['id']}<=set(events[current_id]['supersedes']) and events[new_id]['instruction']==new_words
check('Explicit review of refreshed history permits the correction and retains all previous events')
room=open_record('memory:lesson:'+lesson['id']);assert room.data['record']['body'] is None and 'withheld here' in room.body.toPlainText()
capture('Ledger_Slate_HATCH_Memory_01_Procedure.png')
spec=room.data['actions'][0];assert spec['operation']=='memory.lessons';room.read_action(spec);settle()
assert lesson['body'] in room.result.toPlainText()
check('Procedure text is withheld during browsing and read only through the existing explicit source-checked command')
room=open_record('memory:task:'+task['id']);room.read_action(room.data['actions'][0]);settle()
assert checkpoint['id'] in room.result.toPlainText() and call('memory.checkpoint',{'id':checkpoint['id']})['verified_readback']
check('Task filing keeps the original checkpoint identity and independently verified readback route')
suggestions=call('ledger.explore',{'context':current})['suggestions'];assert [row['id'] for row in suggestions]==['memory','settings']
assert all(key in BY_KEY for key in MEMORY_KEYS)  # which definitions exist is the recorded registry's business (tools/check_release.py)
assert w.shell2.top.nice.isVisible()
check('Memory records link to the existing Memory and Settings workspaces without changing settings or execution controls')
room=open_record(current);ed=room.direction_editor;ed.start();pending='A return draft still needs owner review.'
ed.writing.setPlainText(pending);ed.reason.setText('Continue after returning.')
assert w.close() is True;settle();assert not w.desktop_lease.exists()
w2=WorkbenchWindow(root,Session(RUN/'profile/session.json',root),restore=False);w2.resize(1366,768);w2.show();settle(w2)
room2=open_record(current,w2);ed2=room2.direction_editor
assert ed2.writing.toPlainText()==pending and ed2.reason.text()=='Continue after returning.' and ed2.guard is None and not ed2.save.isEnabled()
check('A fresh desktop recovers correction writing and requires history review instead of silently rebasing it')
room2.scroll.ensureWidgetVisible(ed2.writing);settle(w2)
assert w2.trash_can.isVisible() and w2.shell2.top.nice.isVisible() and w2.operations_monitors.isVisible() and w2.return_thread.footer.isVisible()
capture('Ledger_Slate_HATCH_Memory_01_Compact.png',w2)
check('Laptop layout retains typed memory filing, the correction passage, fixed Trash, Stop, host monitors and the return footer')
assert w2.close() is True;settle(w2);assert not w2.desktop_lease.exists()
assert call('memory.profile')['original_sha256']==original_profile['original_sha256'] and k.listing('jobs')==[]
provider.assert_not_called();provider.stop();check('Clean close preserves the original profile and creates no tool job, provider request or model run')
result=dict(state='PASSED',mode='ACTUAL_QT_OFFSCREEN',checks=checks,captures=captures,jobs_submitted=0,
 model_calls=0,provider_requests=0,native_invocations=0,native_acceptance=False,
 source_check_fixture='OWNER_PROPOSED_PROCEDURE_WITH_EMPTY_REFERENCE_LIST',
 competing_history_case='REAL_SHARED_FEEDBACK_COMMAND',restored_corrections_require_explicit_history_review=True,clean_close=True)
(OUT/'memory-cabinet-ui.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)
