"""Coordinator checks and separately labeled real local-model case trials."""
from __future__ import annotations
import argparse,copy,json,os,subprocess,sys,tempfile,time
from pathlib import Path
from unittest.mock import patch
from . import clock_lab,locations,adaptive_work as controller,continuing_work as flow,slate_action
from .baseline import environment
from .problem_checks import invoke,bound

FAKE={'model_id':'f'*64,'config':{'context':4096,'memory_mb':128,'threads':1,'backend':'CPU'},'profile':'TEST_COORDINATOR_BINDING_NOT_MODEL_INFERENCE'}


def make_problem(kernel,p,home,title='Memory capacity',direct=False):
    source=clock_lab.copy_inputs(home/(title.replace(' ','_')+'_'+__import__('uuid').uuid4().hex[:8]))
    preview=invoke(kernel,'imports.preview',{'source':str(source),'profile':'ENGINEERING'},p)
    copy=invoke(kernel,'imports.accept',{'id':preview['id'],'expected_digest':preview['content_digest'],'for_slate':True},p)
    request=('Suggest a short title for an idea notebook. No engineering investigation is needed.' if direct else
        'Investigate memory capacity. Start with the all-concurrent case, identify missing lifetimes that could change the answer, and test the owner-supplied lifetimes when available. Report the conditional result without inventing lifetimes.')
    project=invoke(kernel,'projects.create',{'title':title,'intent':request},p)
    assignment=invoke(kernel,'assignments.create',{'project':project['id'],'request':request,'interpretation':request,
        'intended_output':'A concise proposal' if direct else 'Conditional capacity finding with actual receipts',
        'success':['Use actual observations for an engineering finding.'],'stop':['Wait for consequential missing input.'],
        'inputs':[] if direct else ['files:'+copy['work']+'/memory.csv']},p)
    spec=clock_lab.specification();names=('memory_limit','buffer_A','buffer_B','workspace','lifetime_A','lifetime_B','lifetime_workspace')
    problem=invoke(kernel,'problems.create',{'project':project['id'],'assignment':assignment['id'],'request':request,'title':title,
        'goals':[request],'variables':[] if direct else [v for v in spec['variables'] if v['name'] in names],
        'assumptions':[] if direct else ['Memory units are binary MiB.'],'questions':[] if direct else ['When is each allocation live?'],
        'candidates':['Propose a short notebook title.'] if direct else ['The selected allocations fit within capacity under a concurrent assumption.','A supplied lifetime schedule may fit despite the concurrent bound.'],
        'sources':[] if direct else [{'copy':copy['id'],'path':'memory.csv','label':'Saved memory amounts'}]},p)
    return {'problem':problem,'copy':copy,'source':str(source)}


def create_work(kernel,p,data,ops=None,direct=False,budget=None):
    return invoke(kernel,'work.investigate',{**bound(data['problem']),'copies':[data['copy']['id']],
        'operations':ops or ['work.read','math.calculate','math.schedule'],'allow_direct':direct,'title':data['problem']['title']+' investigation',
        'budget':budget or {'seconds':900,'steps':24,'tokens':120000,'memory_mb':6144,'output_bytes':4194304,'files':8},
        'limits':{'frontier':8,'decisions':16,'max_tokens':768,'decision_seconds':180,'failures':3},'expires':time.time()+3600},p)


def choose(kernel,p,ident,op,args):
    """TEST DRIVER ONLY: inject a choice to exercise the coordinator, never infer."""
    with kernel.db() as db:
        plan,state=flow.load(db,ident,p)
        if state['state']!='READY' or state.get('current'):raise ValueError('Test choice requires idle READY work')
        state['choice']={'kind':'CALL','candidate':'b1','operation':op,'arguments':args};flow.save(db,plan,state,'TEST_DRIVER_CHOICE_NO_MODEL_CALL')


def last_result(kernel,p,ident):
    value=invoke(kernel,'work.investigation',{'id':ident},p);return value['observations'][-1]['result']


def fake_model():
    from contextlib import ExitStack
    stack=ExitStack();stack.enter_context(patch.object(slate_action,'model_binding',return_value=FAKE))
    stack.enter_context(patch('workbench.local_brain.model',return_value={}))
    stack.enter_context(patch('workbench.local_brain.recheck',return_value=None));return stack


def owner_answer_checks(kernel,p,data):
    """Injected question, real owner answer and transaction; no model inference."""
    from . import problem_service as problems
    def waiting():
        work=create_work(kernel,p,data,['math.schedule']);ident=work['plan']['id']
        invoke(kernel,'work.authorize',{'id':ident,'expected_digest':work['content_digest']},p)
        with kernel.db() as db:
            plan,state=flow.load(db,ident,p)
            question={'id':__import__('uuid').uuid4().hex,'missing':['lifetime_A','lifetime_B','lifetime_workspace'],'text':'Supply the declared lifetimes.'}
            state.update(state='WAITING',reason='MISSING_INPUT',question=question)
            flow.save(db,plan,state,'TEST_DRIVER_QUESTION_NO_MODEL_CALL')
        return {'id':ident,'question':question['id'],'expected_revision':data['problem']['revision'],
            'expected_context_digest':data['problem']['context_digest'],'lifetimes':{
                'lifetime_A':{'start':'0','stop':'10','unit':'s'},'lifetime_B':{'start':'0','stop':'10','unit':'s'},
                'lifetime_workspace':{'start':'10','stop':'20','unit':'s'}},'note':'Synthetic transaction check.'}
    revoked=waiting();original=problems.content
    def revoke_after_preflight(*args,**kwargs):
        result=original(*args,**kwargs)
        invoke(kernel,'work.revoke',{'id':revoked['id'],'reason':'Injected concurrent owner revocation'},p)
        return result
    with patch.object(problems,'content',side_effect=revoke_after_preflight):
        refused=kernel.dispatch('work.answer',revoked,p)
    if refused['ok'] or invoke(kernel,'work.get',{'id':revoked['id']},p)['state']['state']!='REVOKED':raise ValueError('Owner answer overwrote a concurrent revocation')
    answer=waiting()
    with kernel.db() as db:before=db.execute('SELECT count(*) FROM desk_history WHERE id=?',(data['problem']['id'],)).fetchone()[0]
    with patch.object(flow,'save',side_effect=ValueError('TEST_INTERRUPTED_ANSWER_CHECKPOINT')):
        interrupted=kernel.dispatch('work.answer',answer,p)
    with kernel.db() as db:
        after=db.execute('SELECT count(*) FROM desk_history WHERE id=?',(data['problem']['id'],)).fetchone()[0]
        unchanged=problems.load(db,data['problem']['id'],p)
    if interrupted['ok'] or before!=after or unchanged['revision']!=answer['expected_revision']:raise ValueError('Interrupted answer committed a problem without its work checkpoint')
    state=invoke(kernel,'work.get',{'id':answer['id']},p)['state']
    if state['state']!='WAITING' or state['question']['id']!=answer['question']:raise ValueError('Interrupted answer lost its pending question')
    completed=invoke(kernel,'work.answer',answer,p)['state']
    if completed['state']!='READY' or completed['question'] or completed['problem']['expected_revision']!=answer['expected_revision']+1:raise ValueError('Retried answer did not commit one coherent revision')
    return {'state':'PASSED','interrupted_answer_rolled_back_problem_and_checkpoint':True,'revocation_preserved':True,'retry_committed_one_revision':True}


def checkpoint_race_checks(kernel,p,data):
    """Inject owner controls between preflight and commit, without inference."""
    def fresh():
        work=create_work(kernel,p,data,['work.read']);ident=work['plan']['id']
        invoke(kernel,'work.authorize',{'id':ident,'expected_digest':work['content_digest']},p);return ident
    schema_work=fresh()
    from .engineering_cli import schemas
    changed=copy.deepcopy(schemas());changed['work.read']['properties']['path']['maxLength']=1
    with patch('workbench.engineering_cli.schemas',return_value=changed):stopped=invoke(kernel,'work.advance',{'id':schema_work},p)
    if stopped.get('reason')!='WORK_OPERATION_SCHEMA_CHANGED' or invoke(kernel,'work.get',{'id':schema_work},p)['steps']:raise ValueError('Changed registered schema did not stop before an adaptive action')
    invoke(kernel,'work.revoke',{'id':schema_work,'reason':'End schema-change boundary check'},p)
    ident=fresh();choose(kernel,p,ident,'work.read',{'copy':data['copy']['id'],'path':'memory.csv'})
    validate=controller.validate_call
    def pause_before_intent(*args,**kwargs):
        result=validate(*args,**kwargs);invoke(kernel,'work.pause',{'id':ident},p);return result
    with patch.object(controller,'validate_call',side_effect=pause_before_intent):invoke(kernel,'work.advance',{'id':ident},p)
    paused=invoke(kernel,'work.get',{'id':ident},p)
    if paused['state']['state']!='PAUSED' or paused['steps']:raise ValueError('Late adaptive intent overwrote a pause or executed an effect')
    foundations=controller.foundations
    def revoke_before_resume(*args,**kwargs):
        result=foundations(*args,**kwargs);invoke(kernel,'work.revoke',{'id':ident,'reason':'Injected concurrent revocation during resume'},p);return result
    with patch.object(controller,'foundations',side_effect=revoke_before_resume):refused=kernel.dispatch('work.resume',{'id':ident},p)
    if refused['ok'] or invoke(kernel,'work.get',{'id':ident},p)['state']['state']!='REVOKED':raise ValueError('Explicit resume overwrote a concurrent revocation')
    failed=fresh();job=__import__('uuid').uuid4().hex
    with kernel.db() as db:
        plan,state=flow.load(db,failed,p);state.update(steps=['Step1'],current={'key':'Step1','job':job,'phase':'DECISION','operation':'slate.action'},state='READY')
        flow.step_save(db,failed,{'key':'Step1','operation':'slate.action','state':'RUNNING','arguments':{},'attempts':1})
        flow.save(db,plan,state,'TEST_DRIVER_PENDING_FAILED_MODEL_NO_INFERENCE')
    record=kernel.record
    def failed_record(table,ident):return {'id':job,'owner':p.identity,'tool':'brain.action','state':'Failed','error':'Synthetic failure'} if table=='jobs' and ident==job else record(table,ident)
    def pause_before_failure_commit(*args,**kwargs):
        invoke(kernel,'work.pause',{'id':failed},p);return {'state':'Failed','error':'Synthetic failure'}
    with patch.object(kernel,'record',side_effect=failed_record),patch.object(slate_action,'result',side_effect=pause_before_failure_commit):
        invoke(kernel,'work.advance',{'id':failed},p)
    if invoke(kernel,'work.get',{'id':failed},p)['state']['state']!='PAUSED':raise ValueError('Late failed-model result overwrote a pause')
    return {'state':'PASSED','schema_change_stops_before_action':True,'pause_before_intent_preserved':True,'revocation_during_resume_preserved':True,'pause_during_failed_model_commit_preserved':True}


def child(mode,root,profile,home,ident):
    os.environ.update(environment(os.environ,root,profile));os.environ['HOME']=home
    from .engineering_kernel import Kernel,operator
    kernel=Kernel(root);p=operator()
    if mode=='live-reopen':
        before=invoke(kernel,'work.investigation',{'id':ident},p)
        if before['state']['state']!='WAITING' or not before['state']['question']:raise ValueError('Live checkpoint question missing')
        return {'state':'PASSED','automatic_execution':False,'observations':[r['id'] for r in before['observations']],'question':before['state']['question']['id']}
    with fake_model():
        if mode=='write-crash':
            flow.CRASH_AT='EFFECT'
            try:invoke(kernel,'work.advance',{'id':ident},p)
            except flow.Crash:os._exit(78)
            raise ValueError('Effect interruption did not occur')
        flow.pump(kernel);paused=invoke(kernel,'work.get',{'id':ident},p)
        if paused['state']['state']!='PAUSED':raise ValueError('Interrupted adaptive action resumed automatically')
        invoke(kernel,'work.resume',{'id':ident},p);resumed=invoke(kernel,'work.investigation',{'id':ident},p)
        with kernel.db() as db:count=db.execute('SELECT count(*) FROM edit_applications').fetchone()[0]
        if count!=1 or resumed['steps'][-1]['state']!='DONE' or resumed['observations'][-1]['operation']!='changes.apply':raise ValueError('Completed working write was not reconciled once with an actual observation')
        return {'state':'PASSED','applications':count,'effect_replayed':False,'actual_recovered_observation':True,'automatic_resume':False}


def coordinator_checks():
    from .engineering_kernel import Kernel,operator,Principal
    with tempfile.TemporaryDirectory(prefix='ledger-i04-control-') as temp:
        base=Path(temp);home=base/'Home';home.mkdir();root=base/'Office';profile=base/'profile'
        with patch.dict(os.environ,{**environment(os.environ,root,profile),'HOME':str(home)}),patch.object(Path,'home',return_value=home),fake_model():
            locations.office(root);kernel=Kernel(root);p=operator();data=make_problem(kernel,p,home)
            work=create_work(kernel,p,data,['work.read','math.calculate','changes.propose','changes.apply']);ident=work['plan']['id']
            from .engineering_cli import schemas
            if work['plan']['operation_schemas']!={op:schemas()[op] for op in work['plan']['operations']}:raise ValueError('Adaptive grant omitted its frozen operation schemas')
            with kernel.db() as db:plan,state=flow.load(db,ident,p)
            view=slate_action.phase_view(controller.frame(kernel,plan,state,p,data['problem']))
            if view['problem'].get('original_request')!=data['problem']['original_request']:raise ValueError('Compact model view omitted the original owner request')
            readonly=kernel.dispatch('work.authorize',{'id':ident,'expected_digest':work['content_digest']},Principal(p.identity))
            if readonly['ok']:raise ValueError('Read-only principal authorized an investigation')
            invoke(kernel,'work.authorize',{'id':ident,'expected_digest':work['content_digest']},p)
            choose(kernel,p,ident,'math.calculate',{'expression':'buffer_A + buffer_B + workspace <= memory_limit','assumptions':['All three allocations are concurrent.']})
            invoke(kernel,'work.advance',{'id':ident},p)
            value=invoke(kernel,'work.investigation',{'id':ident},p)
            if value['observations'][0]['outcome']!='ADVERSE' or value['observations'][0]['result']['receipt']['snapshot']['outputs'][0]['left']['rational']!='17':raise ValueError('Actual exact adverse observation missing')
            choose(kernel,p,ident,'changes.propose',{'copy':data['copy']['id'],'operations':[{'op':'CREATE','path':'method-note.txt','text':'One preserved working-copy change.\n'}]})
            invoke(kernel,'work.advance',{'id':ident},p);proposal=last_result(kernel,p,ident)
            choose(kernel,p,ident,'changes.apply',{'id':proposal['id'],'expected_digest':proposal['content_digest']})
            command=[sys.executable,'-m','workbench.adaptive_checks','--child']
            def run(mode,expected=0):
                result=subprocess.run(command+[mode,str(root),str(profile),str(home),ident],capture_output=True,text=True,env=locations.child_env(root),timeout=40)
                if result.returncode!=expected:raise ValueError('Adaptive checkpoint child failed: '+(result.stderr or result.stdout)[-1800:])
                return json.loads(result.stdout) if not expected else None
            run('write-crash',78);reopened=run('write-recover')
            # A duplicate action is detected on the same actual copy/problem bindings.
            choose(kernel,p,ident,'work.read',{'copy':data['copy']['id'],'path':'method-note.txt'})
            invoke(kernel,'work.advance',{'id':ident},p)
            choose(kernel,p,ident,'work.read',{'copy':data['copy']['id'],'path':'method-note.txt'})
            duplicate=invoke(kernel,'work.advance',{'id':ident},p)
            if duplicate.get('reason')!='DUPLICATE_ACTION_ON_UNCHANGED_INPUTS':raise ValueError('Unchanged duplicate did not stop')
            # A separate explicitly granted order refuses a different copy.
            work2=create_work(kernel,p,data,['work.read']);ident2=work2['plan']['id'];invoke(kernel,'work.authorize',{'id':ident2,'expected_digest':work2['content_digest']},p)
            choose(kernel,p,ident2,'work.read',{'copy':'a'*32,'path':'memory.csv'});outside=invoke(kernel,'work.advance',{'id':ident2},p)
            if outside['state']!='WAITING':raise ValueError('A copy outside the grant ran')
            invoke(kernel,'work.revoke',{'id':ident2,'reason':'Test revocation'},p)
            if invoke(kernel,'work.advance',{'id':ident2},p).get('ran') is not None:raise ValueError('Revoked work ran')
            races=checkpoint_race_checks(kernel,p,data);owner_answers=owner_answer_checks(kernel,p,data)
            with kernel.db() as db:health=db.execute('PRAGMA quick_check').fetchone()[0]
            if health!='ok':raise ValueError('Coordinator database health failed')
            return {'state':'PASSED','coordinator_contract_only':True,'model_calls':0,'actual_exact_adverse_result':'17 MiB > 16 MiB',
                'read_only_grant_refused':True,'outside_copy_refused':True,'revocation_stops_actions':True,'duplicate_action_stops':True,
                'complete_selected_operation_schemas_frozen':True,
                'original_problem_request_in_model_view':True,
                'fresh_process_write_recovery':reopened,'checkpoint_controls':races,'owner_answer_transaction':owner_answers,'database':health}


def live_case(kernel,p,home,profile,name,overlap=False,direct=False,ui=False,screenshot=None):
    data=make_problem(kernel,p,home,name,direct);work=create_work(kernel,p,data,['work.read','math.concurrent','math.schedule'],direct)
    ident=work['plan']['id'];invoke(kernel,'work.authorize',{'id':ident,'expected_digest':work['content_digest']},p)
    questions=[];reopens=[];end=time.monotonic()+1000;last=None;pane=None;app=None
    if ui:
        os.environ['QT_QPA_PLATFORM']='offscreen'
        from PySide6.QtWidgets import QApplication,QLabel
        from types import SimpleNamespace
        from .problem_qt import ProblemPane
        app=QApplication.instance() or QApplication(['ledger-i04-actual-observations'])
        pane=ProblemPane(SimpleNamespace(host=SimpleNamespace(root=kernel.root),project=None,assignment=None,message=QLabel()))
        pane.resize(1320,1100);pane.show();pane.reload(data['problem']['id']);pane.pages.setCurrentIndex(4)
        pane.lab.findChild(__import__('PySide6.QtWidgets',fromlist=['QTabWidget']).QTabWidget).setCurrentIndex(2)
    try:
        while time.monotonic()<end:
            invoke(kernel,'work.advance',{'id':ident},p);value=invoke(kernel,'work.investigation',{'id':ident},p);state=value['state']
            marker=(state['state'],state.get('reason'),len(value['steps']))
            if marker!=last:print(name,marker,flush=True);last=marker
            if app:pane.lab.adaptive.reload();app.processEvents()
            if state['state']=='WAITING' and state.get('question'):
                q=state['question'];questions.append(q)
                process=subprocess.run([sys.executable,'-m','workbench.adaptive_checks','--child','live-reopen',str(kernel.root),str(profile),str(home),ident],
                    capture_output=True,text=True,env=locations.child_env(kernel.root),timeout=30)
                if process.returncode:raise ValueError('Live process reopen failed: '+process.stderr[-1200:])
                reopened=json.loads(process.stdout)
                if reopened['observations']!=[r['id'] for r in value['observations']] or reopened['question']!=q['id']:raise ValueError('Fresh process lost observations or question')
                reopens.append(reopened)
                lifetimes={'lifetime_A':{'start':'0','stop':'10','unit':'s'},'lifetime_B':{'start':'0','stop':'10','unit':'s'},
                    'lifetime_workspace':{'start':'9' if overlap else '10','stop':'20','unit':'s'}}
                if not set(q['missing'])<=set(lifetimes):raise ValueError('Model asked for an unprovided input in this trial')
                if pane:
                    widget=pane.lab.adaptive;widget.open()
                    for row in range(widget.inputs.rowCount()):
                        name_key=widget.inputs.item(row,0).text()
                        for col,key in ((1,'start'),(2,'stop'),(3,'unit')):widget.inputs.item(row,col).setText(lifetimes[name_key][key])
                    widget.note.setText('Synthetic owner-supplied intervals for this trial; these are declared inputs.')
                    widget.answer();app.processEvents()
                else:
                    invoke(kernel,'work.answer',{'id':ident,'question':q['id'],'expected_revision':state['problem']['expected_revision'],
                        'expected_context_digest':state['problem']['expected_context_digest'],'lifetimes':{k:lifetimes[k] for k in q['missing']},
                        'note':'Synthetic owner-supplied intervals for this trial; these are declared inputs.'},p)
            elif state['state'] not in ('READY','RUNNING'):break
            time.sleep(.2)
        value=invoke(kernel,'work.investigation',{'id':ident},p);obs=value['observations'];state=value['state'];failures=[]
        if state['state']!='REVIEW':failures.append('No completed proposed finding: '+str(state.get('reason')))
        if direct:
            if obs or questions:failures.append('Direct-response trial performed unnecessary investigation')
        else:
            concurrent=[o for o in obs if o['operation']=='math.concurrent'];schedule=[o for o in obs if o['operation']=='math.schedule']
            concurrent_snapshot=concurrent[0]['result'].get('receipt',{}).get('snapshot',{}) if concurrent else {}
            if concurrent_snapshot.get('state')!='INFEASIBLE':failures.append('Missing actual all-concurrent 17-versus-16 adverse result')
            amounts={'buffer_A','buffer_B','workspace'}
            if concurrent:
                output=(concurrent_snapshot.get('outputs') or [{}])[0]
                if concurrent[0]['arguments']['capacity']!='memory_limit' or set(concurrent[0]['arguments']['allocations'])!=amounts or output.get('left',{}).get('rational')!='17' or output.get('right',{}).get('rational')!='16':failures.append('Concurrent check did not use the required saved allocations and capacity')
            if not questions:failures.append('No discriminating missing-lifetime question')
            expected='INFEASIBLE' if overlap else 'FEASIBLE'
            schedule_snapshot=schedule[-1]['result'].get('snapshot',{}) if schedule else {}
            if schedule_snapshot.get('state')!=expected:failures.append('Supplied lifetime variant not checked correctly')
            if schedule:
                pairs={(a['quantity'],a['lifetime']) for a in schedule[-1]['arguments']['allocations']}
                if schedule[-1]['arguments']['capacity']!='memory_limit' or pairs!={('buffer_A','lifetime_A'),('buffer_B','lifetime_B'),('workspace','lifetime_workspace')} or schedule_snapshot.get('peak',{}).get('rational')!=('17' if overlap else '12'):failures.append('Schedule did not test all required allocations or the expected exact peak')
            if not any(u['disposition'] in ('REJECT','REFINE') for d in value['decisions'] for u in d['candidate']['updates']):failures.append('No model-recorded rejection/refinement')
            if concurrent and questions:
                question_step=next(i for i,s in enumerate(value['steps']) if s.get('result',{}).get('id')==questions[0]['id'])
                observation_step=next(i for i,s in enumerate(value['steps']) if s.get('observation')==concurrent[0]['id'])
                if observation_step>=question_step:failures.append('Asked before observing the requested concurrent check')
        if pane:
            pane.lab.adaptive.reload();app.processEvents()
            if screenshot:pane.grab().save(str(screenshot))
        return {'state':'FAILED' if failures else 'PASSED','acceptance_failures':failures,'name':name,'overlap':overlap,'direct':direct,
            'model_generations_in_validated_decisions':2*len(value['decisions']),
            'generation_count_scope':'Completed SELECT and ARGUMENTS generations in retained validated decisions; failed/interrupted attempts are excluded.',
            'questions':questions,'fresh_process_reopens':reopens,'work':value,
            'model_finding':state.get('finding'),'ui_owner_answer':bool(pane and questions),'target_thinkpad':'PENDING'}
    finally:
        if pane:pane.close();app.processEvents()


def live_checks(model_path,base,output,ui=False,screenshot=None):
    from .engineering_kernel import Kernel,operator
    from . import local_brain
    base.mkdir(parents=True,exist_ok=False);home=base/'Home';home.mkdir();root=base/'Office';profile=base/'profile'
    with patch.dict(os.environ,{**environment(os.environ,root,profile),'HOME':str(home)}),patch.object(Path,'home',return_value=home):
        locations.office(root);kernel=Kernel(root);p=operator()
        def wait(job):
            until=time.monotonic()+240
            while kernel.record('jobs',job['id'])['state'] in ('Queued','Running') and time.monotonic()<until:time.sleep(.2)
            result=invoke(kernel,'brain.result',{'id':job['id']},p)
            if result['state']!='Completed':raise ValueError('Reference model startup failed: '+str(result))
            return result['result']
        registered=wait(invoke(kernel,'brain.model.add',{'path':str(model_path),'origin':'Explicit reference-model file for a local execution-host trial','managed_copy':False},p))
        if hasattr(os,'posix_fadvise'):
            with model_path.open('rb') as stream:os.posix_fadvise(stream.fileno(),0,0,os.POSIX_FADV_DONTNEED)
        activated=wait(invoke(kernel,'brain.model.use',{'id':registered['model_id'],'options':{'context':6144,'threads':4,'memory_mb':4480}},p))
        try:
            model=slate_action.model_binding(kernel,p);cases=[]
            for name,overlap,direct in [('Capacity_A',False,False),('Capacity_B',True,False),('Direct_title',False,True)]:
                result=live_case(kernel,p,home,profile,name,overlap,direct,ui and not direct,screenshot if name=='Capacity_A' else None);cases.append(result)
                complete=len(cases)==3;failed=any(c['state']!='PASSED' for c in cases)
                partial={'state':'FAILED' if failed else 'PASSED' if complete else 'IN_PROGRESS','expected_cases':3,
                    'profile':'ACTUAL_LOCAL_MODEL_TRIAL','model':model,'activation':activated,'cases':cases,'cloud_calls':0,'target_thinkpad':'PENDING'}
                if output:output.write_text(json.dumps(partial,indent=2)+'\n')
                if result['state']!='PASSED':
                    print('ACCEPTANCE_FAILED',result['acceptance_failures'],flush=True);break
            return partial
        finally:local_brain.stop(kernel,'REFERENCE_TRIAL_FINISHED')


def main():
    if len(sys.argv)>1 and sys.argv[1]=='--child':print(json.dumps(child(*sys.argv[2:])));return 0
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path);parser.add_argument('--live',action='store_true');parser.add_argument('--model',type=Path);parser.add_argument('--keep',type=Path);parser.add_argument('--ui',action='store_true');parser.add_argument('--screenshot',type=Path);args=parser.parse_args()
    if args.live and (not args.model or not args.keep):raise ValueError('Live checks require an explicit model path and a new retained fixture folder')
    value=live_checks(args.model,args.keep,args.output,args.ui,args.screenshot) if args.live else coordinator_checks();raw=json.dumps(value,indent=2)+'\n'
    if args.output:args.output.write_text(raw)
    print(json.dumps({'state':value['state'],'model_generations_in_validated_decisions':sum(c['model_generations_in_validated_decisions'] for c in value['cases'])}) if args.live else raw,end='\n');return 0 if value['state']=='PASSED' else 1


if __name__=='__main__':raise SystemExit(main())
