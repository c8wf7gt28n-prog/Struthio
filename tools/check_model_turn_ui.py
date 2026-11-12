"""Actual Qt check of the model turn applied to a real page (HATCH AGENT-02, owner decision D19), offscreen.

D19: a document edit the model proposes applies at once, visibly, and can be undone. The mechanical steps: open Documents
through the Hatch catalogue route, type two paragraphs with key events, select words, ask Slate in the typing strip in
words the explicit rules do not know; the plan path returns a canned proposal (the shape the 1.5B model proposed in the
AGENT-01 live trial: the right words and offsets, the wrong paragraph index and origin HUMAN) with a documents.edit for the
open page and a documents.get; the edit lands on the page and in the store as a revision with the model's origin, the
changed words carry a pencil-yellow wash that fades and clears, the card says APPLIED ON THE PAGE with the words, undo and
the Right/Wrong marks; the documents.get keeps Run/Edit; the owner's Right mark lands in the instruction matrix; the undo
word takes the edit back as a revision; under Reduce motion the wash holds and then clears; a second proposal made for a
revision the owner has since moved past (the owner kept typing while the model worked) is not applied and its card says
why, keeping Run/Edit; a proposal with two page edits written for the same revision (add a paragraph, then style the
paragraph that was second) applies the first, and the second is not moved onto the new revision, because the added
paragraph changed what its index means: its card says why and keeps Run/Edit. Captures at 1920 by 1200 and 1366 by 768.

How the model is held: brain.status, brain.ask, jobs.get, slate.progress and brain.result are answered on the Kernel's
dispatch path (Kernel.dispatch wrapped, every other operation passes through) with a canned reply shaped exactly like
local_brain.run_reply's, and the proposal is recorded in the instruction matrix the way run_reply records it. Disposable
profile and Concern; Kernel.launch, Kernel.submit and the provider request are held; no process may start; no model,
worker or job runs. Nothing here is owner-host, live-model or physical acceptance.
"""
import hashlib,json,os,subprocess,sys,tempfile,time,uuid
from pathlib import Path
from unittest.mock import patch
PROGRAM=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('ARC_LEDGER_MODEL_TURN_CAPTURE_DIR',str(PROGRAM/'build/ui_checks/model_turn')));OUT.mkdir(parents=True,exist_ok=True)
RUN=Path(tempfile.mkdtemp(prefix='ledger-agent02-model-turn-ui-'))
os.environ.update(QT_QPA_PLATFORM='offscreen',ARC_LEDGER_EMBEDDED='1',ARC_LEDGER_DISABLE_BOOK_WATCHER='1',
 ARC1_WORKBENCH_CONFIG_HOME=str(RUN/'profile'),ARC_LEDGER_CONCERN=str(RUN/'Concern'))
os.environ.pop('ARC_LEDGER_XSESSION',None)
sys.path.insert(0,str(PROGRAM));sys.dont_write_bytecode=True
from PySide6.QtCore import Qt,QProcess
from PySide6.QtGui import QTextCursor,QFont,QTextFormat
from PySide6.QtWidgets import QFrame,QMessageBox,QPushButton
from PySide6.QtTest import QTest
from workbench.qt_app import make_app,WorkbenchWindow
from workbench import locations,clip,instruction_matrix,model_turn,document_qt
from workbench.document_qt import DocumentsTab,from_qt,FLASH_MS
from workbench.engineering_kernel import Kernel,operator
from workbench.session import Session
from workbench.explore_qt import open_instrument
provider=patch.object(clip,'_request',side_effect=AssertionError('No provider request')).start()
launcher=patch.object(Kernel,'launch',side_effect=AssertionError('No worker launch')).start()
submission=patch.object(Kernel,'submit',side_effect=AssertionError('No job submission')).start()
question=patch.object(QMessageBox,'question',return_value=QMessageBox.Yes).start()
# -- the held model: the plan path's operations answered on the Kernel's dispatch path with a canned reply -----------------
MODEL_ID='bd5b55329ac2cfbd86bef1915ddf599c5f6a1cca484c156e00f54094308b0dae'   # Qwen2.5-1.5B-Instruct Q4_K_M (AGENT-01 live trial file set)
turn={'ready':False,'job':None,'message':None,'state':'Completed','proposal':None,'asks':[],'answered':{}}
real_dispatch=Kernel.dispatch
def held_dispatch(self,op,args=None,principal=None):
 args=args or {}
 if op=='brain.status' and turn['ready']:
  return {'ok':True,'result':{'schema':'arc.local-brain/1','state':'READY','selection':{'model_id':MODEL_ID},'worker':{'model_id':MODEL_ID,'backend':'CPU'},'note':'CANNED_FOR_CHECK'}}
 if op=='brain.ask' and turn['ready']:
  assert args.get('mode')=='plan',args
  turn['job']=uuid.uuid4().hex;turn['message']=args['message'];turn['asks'].append({'job':turn['job'],'message':args['message'],'proposal':turn['proposal']})
  instruction_matrix.propose(self,principal.identity,args['message'],turn['proposal']['actions'],MODEL_ID)  # as local_brain.run_reply records a plan
  turn['answered'][op]=turn['answered'].get(op,0)+1
  return {'ok':True,'result':{'id':turn['job'],'state':'Queued','tool':'brain.reply'}}
 if op=='jobs.get' and turn['job'] and args.get('id')==turn['job']:
  turn['answered'][op]=turn['answered'].get(op,0)+1
  return {'ok':True,'result':{'id':turn['job'],'tool':'brain.reply','state':turn['state'],'owner':principal.identity,'request_spec':{'brain':{'message':turn['message'],'mode':'plan'}}}}
 if op=='slate.progress' and turn['job'] and args.get('job')==turn['job']:return {'ok':True,'result':{'display_text':''}}
 if op=='brain.result' and turn['job'] and args.get('id')==turn['job']:
  turn['answered'][op]=turn['answered'].get(op,0)+1
  reply={'status':'REPLY_READY','model_id':MODEL_ID,'mode':'plan','text':json.dumps(turn['proposal'],ensure_ascii=False),'proposal':turn['proposal'],
         'qualification':'MODEL_GENERATED_NOT_FACT_VERIFIED','cloud_calls':0}
  return {'ok':True,'result':{'job_id':turn['job'],'state':'Completed','result':reply,'error':None}}
 return real_dispatch(self,op,args,principal)
held=patch.object(Kernel,'dispatch',held_dispatch).start()
app=make_app([]);root=locations.office(RUN/'workspace');session=Session(RUN/'profile/session.json',root)
w=WorkbenchWindow(root,session,restore=False);k=w.ledger_bridge.kernel;bridge=w.ledger_bridge
import platform;platform.processor()
popen=patch.object(subprocess,'Popen',side_effect=AssertionError('No process start')).start()
system=patch.object(os,'system',side_effect=AssertionError('No shell command')).start()
detached=patch.object(QProcess,'startDetached',side_effect=AssertionError('No detached program')).start()
checks=[];captures=[]
def settle(ms=30):
 for name in ('agenda_runner','study_idle'):
  obj=getattr(w,name,None)
  if obj and hasattr(obj,'timer'):obj.timer.stop()
 for _ in range(3):app.processEvents();QTest.qWait(ms)
def check(text):checks.append(text);print(text,flush=True)
def call(op,args=None):
 value=k.dispatch(op,args or {},operator());assert value['ok'],value;return value['result']
def capture(name,note):
 w.operations_panel.refresh();settle();pix=w.grab();target=OUT/name;assert pix.save(str(target),'PNG')
 captures.append(dict(file=name,note=note,mode='ACTUAL_QT_WINDOW_GRAB',sha256=hashlib.sha256(target.read_bytes()).hexdigest(),resolution=[w.width(),w.height()]))
def stored(ident):return call('documents.get',{'id':ident})
def cards():return [c for c in face.pending.findChildren(QFrame,'StacCard')] if face.pending is not None else []
def wait_for(predicate,ms=6000):
 end=time.monotonic()+ms/1000
 while time.monotonic()<end:
  if predicate():return True
  QTest.qWait(50)
 return predicate()
def five_parts():
 parts=(w.nav_dock,w.ribbon_dock,w.central_stack,w.sim_dock,getattr(w,'type_dock',None))
 return all(p is not None and p.isVisible() for p in parts) and w.trash_can.isVisible() and w.shell2.top.nice.isVisible()
FIRST='The quick brown fox jumps over the lazy dog.';SECOND='It slept under the oak.'
REQUEST='make the words I picked stand out';STALE_REQUEST='draw a line under the picked words'
w.resize(1920,1200);w.show();settle();bridge.timer.stop();w.type_bar.hatch.lifecycle.timer.stop()
face=w.shell2.face
with k.db() as db:jobs_before=db.execute('SELECT count(*) FROM jobs').fetchone()[0]
# 01 · the page: Hatch catalogue route, two paragraphs typed with key events, words selected
entry=next(r for r in call('ledger.explore',{'kind':'INSTRUMENT'})['instruments'] if r['id']=='instrument:documents')
tab=open_instrument(w,entry);settle();assert isinstance(tab,DocumentsTab) and w.tabs.currentWidget() is tab and tab.document_id,tab
ident=tab.document_id
tab.page.setFocus();settle();QTest.keyClicks(tab.page,FIRST);QTest.keyClick(tab.page,Qt.Key_Return);QTest.keyClicks(tab.page,SECOND);settle()
assert tab.flush() and tab.page.toPlainText()==FIRST+'\n'+SECOND;rev=tab.revision
cursor=tab.page.textCursor();cursor.setPosition(4);cursor.setPosition(15,QTextCursor.KeepAnchor);tab.page.setTextCursor(cursor);settle()
assert tab.slate_selection()=={'block':0,'start':4,'end':15,'text':'quick brown'} and five_parts()
check('01 Hatch route opens Documents; two paragraphs typed with key events and saved as revision %d; “quick brown” selected in paragraph 1'%rev)
# 02 · the request typed to Slate in the strip goes to the plan path (the rules do not know it), with the page and the hint line
assert tab.slate_request(REQUEST) is None
APPLY={'text':'quick brown','actions':[
 {'operation':'documents.edit','arguments':{'id':ident,'expected_revision':rev,'selection':{'block':4,'start':4,'end':15,'text':'quick brown'},'change':{'bold':True},'origin':'HUMAN'}},
 {'operation':'documents.get','arguments':{'id':ident}}]}
turn.update(ready=True,proposal=APPLY,state='Completed')
bar=w.type_bar;bar.set_target('slate');box=bar.box;box.setFocus();settle()
QTest.keyClicks(box,REQUEST);settle();QTest.keyClick(box,Qt.Key_Return)
assert wait_for(lambda:len(cards())==2),(len(cards()),turn)
message=turn['asks'][0]['message']
hint='To change this page use documents.edit with id %s, expected_revision %d, selection {block, start, end, text} and change {bold|italic|underline|style|replace|append}.'%(ident,rev)
assert message.startswith(REQUEST+'\n\n(About the open item: ') and hint in message and 'selected words 4–15 of paragraph 1 (block index 0): “quick brown”' in message,message
assert len(hint)<200
check('02 “%s” typed in the strip is not an explicit rule; the plan path received the page context with the copyable line (%d characters): %s'%(REQUEST,len(hint),hint))
# 03 · the edit applied at once: the page, the store, the card
applied_card,review_card=cards()
after=stored(ident);doc=after['document']
assert doc['revision']==rev+1 and doc['blocks'][0]['marks']==[{'start':4,'end':15,'bold':True}] and doc['blocks'][1]['text']==SECOND,doc
assert doc['last_change']['actor']==model_turn.ORIGIN and doc['last_change']['request']==model_turn.request_words(REQUEST,MODEL_ID),doc['last_change']
assert after['events'][0]['action']=='DOCUMENT_EDITED_BY_'+model_turn.ORIGIN
assert from_qt(tab.page.document())[0]['marks']==[{'start':4,'end':15,'bold':True}] and tab.revision==rev+1 and not tab.dirty
probe=tab.page.textCursor();probe.setPosition(6);bold_weight=probe.charFormat().fontWeight();probe.setPosition(2);plain_weight=probe.charFormat().fontWeight()
assert bold_weight>=QFont.Bold>plain_weight
CORRECTIONS=['the model named paragraph 5, words 4–15, which do not hold “quick brown”; your selection in paragraph 1 is used','recorded as Graphite’s model, not HUMAN']
said='Changed on the page: made “quick brown” bold · revision %d · Ctrl Z or “undo” takes it back · proposed by the model bd5b5532 · %s'%(rev+1,'; '.join(CORRECTIONS))
assert applied_card.property('modelTurn')=='applied' and applied_card.words.text().replace('​','')==said,applied_card.words.text()
labels=[l.text() for l in applied_card.findChildren(type(applied_card.words))]
assert 'APPLIED ON THE PAGE' in labels and any('undo' in t for t in labels) and 'Was this right?' in labels,labels
assert sorted(b.text() for b in applied_card.findChildren(QPushButton))==['Right','Wrong']
assert review_card.property('modelTurn') is None and sorted(b.text() for b in review_card.findChildren(QPushButton))==['Edit','Run']
assert tab.model_edit['verdict']['notes']==CORRECTIONS and tab.model_edit['verdict']['corrections']==CORRECTIONS,tab.model_edit['verdict']   # said aloud, on the card
check('03 The proposed documents.edit applied at once: revision %d by %s (event %s, request “%s”); “quick brown” bold on the page (weight %d against %d); the paragraph index the model gave (5) cannot hold the quoted words, so the selected words were used, origin HUMAN not kept, and both corrections are in Slate’s sentence; card APPLIED ON THE PAGE says “%s”; the documents.get keeps Run/Edit'%(
 rev+1,model_turn.ORIGIN,after['events'][0]['action'],doc['last_change']['request'],bold_weight,plain_weight,said))
# 04 · the wash: an ExtraSelection over the changed words, fading, never in the document
washes=tab.page.extraSelections();record=tab.flash_record[-1]
assert len(washes)==1 and (washes[0].cursor.selectionStart(),washes[0].cursor.selectionEnd())==(4,15) and record['range']==[4,15] and not record['reduce_motion']
wash_alpha=washes[0].format.background().color().alpha()
assert not tab.page.textCursor().hasSelection()
capture('Ledger_Slate_AGENT_02_ModelTurn_01_Applied_Wash_1920.png','The model edit just landed: “quick brown” bold with the pencil-yellow wash fading; APPLIED ON THE PAGE card in the right column; the documents.get card keeps Run/Edit')
capture_alpha=record['alphas'][-1]
assert wait_for(lambda:record['cleared'],FLASH_MS+1500) and tab.page.extraSelections()==[]
alphas=record['alphas'];assert alphas[0]==255 and all(a>b for a,b in zip(alphas,alphas[1:])) and len(alphas)>=8,alphas
def backgrounds():
 found=[];block=tab.page.document().firstBlock()
 while block.isValid():
  it=block.begin()
  while not it.atEnd():
   if it.fragment().isValid() and it.fragment().charFormat().hasProperty(QTextFormat.BackgroundBrush):found.append(it.fragment().text())
   it+=1
  block=block.next()
 return found
assert backgrounds()==[]
assert set(stored(ident)['document']['blocks'][0])=={'id','style','text','marks'}
check('04 The wash was one ExtraSelection over characters 4–15 (alpha %d when shown, %d at the capture), stepped down %s and cleared within %d ms; the document and the store carry no highlight'%(wash_alpha,capture_alpha,alphas,FLASH_MS))
# 05 · the owner's mark lands in the instruction matrix on the proposal's row
program=instruction_matrix.program_of('documents.edit',APPLY['actions'][0]['arguments'])
next(b for b in applied_card.findChildren(QPushButton) if b.text()=='Right').click();settle()
row=next(r for r in call('matrix.list',{'query':program[:200],'limit':5})['rows'] if r['program']==program)
assert row['mark']=='GOOD' and row['model']==MODEL_ID and row['intent'].startswith(REQUEST),row
check('05 Right on the card marked the proposal’s instruction-matrix row GOOD (model %s, outcome %s)'%(MODEL_ID[:8],row['outcome']))
# 06 · the undo word: the page's one undo stack, as a new revision
answer=applied_card.undo();settle()
assert 'Took the last change back (revision %d)'%(rev+2) in answer,answer
undone=stored(ident)['document'];assert undone['revision']==rev+2 and undone['blocks'][0]['marks']==[] and from_qt(tab.page.document())[0]['marks']==[]
check('06 The undo word took the model’s change back through the page’s undo stack: revision %d, no bold on the page or in the store; Slate said “%s”'%(rev+2,answer))
# 07 · Reduce motion: the wash holds for the whole time and then clears
profile=dict(document_qt.profile_of(w),reduce_motion=True)
with patch.object(document_qt,'profile_of',return_value=profile):
 start=FIRST.index('lazy dog')
 words=tab.apply_model_edit({'id':ident,'expected_revision':tab.revision,'selection':{'block':0,'start':start,'end':start+8,'text':'lazy dog'},'change':{'italic':True}},'make the dog lean',MODEL_ID)
 calm=tab.flash_record[-1];assert words.startswith('Changed on the page: made “lazy dog” italic · revision %d'%(rev+3)) and calm['reduce_motion'],words
 QTest.qWait(FLASH_MS//2);assert len(tab.page.extraSelections())==1 and calm['alphas']==[255] and not calm['cleared']
 assert wait_for(lambda:calm['cleared'],FLASH_MS+1500) and tab.page.extraSelections()==[] and calm['alphas']==[255]
check('07 Reduce motion: the wash stayed at full strength for %d ms (no fade steps) and then cleared; the italic landed as revision %d'%(FLASH_MS,rev+3))
# 08 · a stale proposal: the owner kept typing while the model worked; the proposal is not applied and the card says why
seen=tab.revision;cursor=tab.page.textCursor();cursor.setPosition(4);cursor.setPosition(15,QTextCursor.KeepAnchor);tab.page.setTextCursor(cursor);settle()
STALE={'text':'underline','actions':[{'operation':'documents.edit','arguments':{'id':ident,'expected_revision':seen,'selection':{'block':0,'start':4,'end':15,'text':'quick brown'},'change':{'underline':True}}}]}
turn.update(proposal=STALE,state='Running')
box.setFocus();settle();QTest.keyClicks(box,STALE_REQUEST);settle();QTest.keyClick(box,Qt.Key_Return)
assert wait_for(lambda:len(turn['asks'])==2) and 'expected_revision %d'%seen in turn['asks'][1]['message']
tab.page.setFocus();cursor=tab.page.textCursor();cursor.movePosition(QTextCursor.End);tab.page.setTextCursor(cursor);QTest.keyClicks(tab.page,' Then it woke.');settle()
assert tab.flush() and tab.revision==seen+1
turn['state']='Completed'
assert wait_for(lambda:len(cards())==1),len(cards())
stale_card=cards()[0];stale_words=stale_card.words.text().replace('​','')
expected='Not applied by itself: it was made for revision %d and the page is at revision %d now, so it is stale. Run tries it as proposed; Edit puts it in the strip.'%(seen,seen+1)
assert stale_card.property('modelTurn')=='not_applied' and stale_words==expected,stale_words
assert sorted(b.text() for b in stale_card.findChildren(QPushButton))==['Edit','Run']
latest=stored(ident)['document'];assert latest['revision']==seen+1 and latest['last_change']['actor']=='HUMAN' and not any(m.get('underline') for m in latest['blocks'][0]['marks'])
assert latest['blocks'][1]['text']==SECOND+' Then it woke.'
check('08 A proposal made for revision %d arrived after the owner’s typing saved revision %d: not applied, the page and store untouched by Slate; the card keeps Run/Edit and says “%s”'%(seen,seen+1,expected))
capture('Ledger_Slate_AGENT_02_ModelTurn_02_Stale_Not_Applied_1920.png','A stale proposal: the card says why it was not applied and keeps Run/Edit; the earlier APPLIED card and the undo answer above it')
# 09 · two page edits in one proposal, both written for the revision the model saw: the append lands; the paragraph style
#      for “paragraph 2” would now hit the added paragraph, so it is not moved onto the new revision (refused as stale)
CHAIN_REQUEST='put a line in between and give the second part more weight'
assert tab.slate_request(CHAIN_REQUEST) is None
base=tab.revision;BETWEEN='A line in between.'
CHAIN={'text':'two edits','actions':[
 {'operation':'documents.edit','arguments':{'id':ident,'expected_revision':base,'selection':{'block':0,'start':0,'end':0},'change':{'append':BETWEEN}}},
 {'operation':'documents.edit','arguments':{'id':ident,'expected_revision':base,'selection':{'block':1,'start':0,'end':0},'change':{'style':'Heading2'}}}]}
turn.update(proposal=CHAIN,state='Completed')
# AGENT-02 integration: a paragraph change applies by itself only on the owner's paragraph (the live trial's review), so the
# owner puts the caret in paragraph 1, where the line in between goes, before asking
from PySide6.QtGui import QTextCursor as _Cursor
tab.page.setTextCursor(_Cursor(tab.page.document().findBlockByNumber(0)));settle()
box.setFocus();settle();QTest.keyClicks(box,CHAIN_REQUEST);settle();QTest.keyClick(box,Qt.Key_Return)
assert wait_for(lambda:len(turn['asks'])==3 and len(cards())==2),(len(turn['asks']),len(cards()))
chain_applied,chain_refused=cards();chained=stored(ident)['document']
assert chain_applied.property('modelTurn')=='applied' and chain_refused.property('modelTurn')=='not_applied'
assert chained['revision']==base+1 and [(b['text'],b['style']) for b in chained['blocks']]==[(FIRST,'Normal'),(BETWEEN,'Normal'),(SECOND+' Then it woke.','Normal')],chained['blocks']
chain_words=chain_refused.words.text().replace('​','')
assert chain_words.startswith('Not applied by itself: it was made for revision %d and the page is at revision %d now, so it is stale.'%(base,base+1)),chain_words
assert 'An earlier edit in this proposal changed the page’s words, so the places this one names were not moved onto the new revision.' in chain_words,chain_words
assert sorted(b.text() for b in chain_refused.findChildren(QPushButton))==['Edit','Run'] and tab.revision==base+1
assert wait_for(lambda:tab.flash_record[-1]['cleared'],FLASH_MS+1500)
check('09 Two page edits in one proposal for revision %d (the owner’s caret in paragraph 1): the paragraph added after paragraph 1 landed as revision %d; the subheading meant for the old paragraph 2 was not moved onto revision %d (it would have styled the added line): no paragraph became a subheading, and its card keeps Run/Edit and says “%s”'%(base,base+1,base+1,chain_words))
turn['ready']=False
# 09 · compact size
w.resize(1366,768);settle(60);bar_=face.scroll.verticalScrollBar();bar_.setValue(bar_.maximum());settle();assert five_parts() and tab.page.isVisible()
capture('Ledger_Slate_AGENT_02_ModelTurn_03_Compact_1366.png','The same page and Slate column at 1366 by 768; all five parts visible')
check('10 1366×768: the page, the Slate column with the cards and the five parts stay visible')
# 10 · nothing ran
with k.db() as db:jobs_after=db.execute('SELECT count(*) FROM jobs').fetchone()[0]
assert jobs_after==jobs_before and not launcher.called and not submission.called and not provider.called and not popen.called and not detached.called and not system.called
check('11 Zero jobs, worker launches, job submissions, provider requests or processes; the model was a canned reply on the dispatch path (answered: %s)'%json.dumps(turn['answered'],sort_keys=True))
events=stored(ident)['events']
report=dict(schema='ledger.agent02-model-turn-ui/1',checkpoint='HATCH AGENT-02',work_item='WI-B the model turn applied to a real page',state='PASSED',mode='ACTUAL_QT_OFFSCREEN',
 owner_decision='D19: model-proposed document edits apply at once, visibly, undoable',
 checks=checks,captures=captures,document=ident,revisions={'typed':rev,'model_edit':rev+1,'undo':rev+2,'reduce_motion_edit':rev+3,'owner_typing':seen+1,'chain_append':base+1},
 origin_recorded=model_turn.ORIGIN,origin_note=('SLATE_MODEL is not an accepted documents origin yet; the closest existing origin SLATE is recorded and the request words say the model proposed it'
                                               if model_turn.ORIGIN=='SLATE' else 'SLATE_MODEL'),
 recorded_request=doc['last_change']['request'],slate_said=said,corrections_said=CORRECTIONS,stale_card=expected,hint_line=hint,
 canned_proposals={'applied':APPLY,'stale':STALE,'two_edits':CHAIN},chain_card=chain_words,canned_model_id=MODEL_ID,held_operations=sorted(turn['answered']),
 wash={'first':{k2:record[k2] for k2 in ('range','alphas','cleared','reduce_motion')},'reduce_motion':{k2:calm[k2] for k2 in ('range','alphas','cleared','reduce_motion')},'flash_ms':FLASH_MS},
 matrix_row={'mark':row['mark'],'outcome':row['outcome'],'model':row['model'],'program':row['program']},events=[e['action'] for e in events],
 model_used=False,model_generations=0,real_job_submissions=0,worker_processes_started=0,provider_requests=0,native_invocations=0,processes_started=0,
 acceptance_claimed=False,note='Mechanical offscreen evidence of D19 on a real page with a canned proposal; the live turn with the 1.5B model (kernel level, build container), the owner display and the owner host remain open.')
w.close();app.processEvents()
(OUT/'model-turn-ui.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(dict(state=report['state'],checks=len(checks),captures=len(captures),origin=model_turn.ORIGIN,revisions=report['revisions'])))
