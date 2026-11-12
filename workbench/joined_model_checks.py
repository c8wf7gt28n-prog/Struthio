"""Explicit real local-model I05 trials; expected answers stay outside its frame."""
from pathlib import Path
from unittest.mock import patch
import argparse,csv,hashlib,json,os,subprocess,sys,time
from . import locations,local_brain,slate_action,continuing_work as flow,project_desk as records
from .baseline import environment
from .problem_checks import invoke,bound
from .joined_checks import fixture,chain,wait

OPS=['work.read','methods.preview','methods.instantiate','methods.run','methods.result','joined.prepare','joined.run','joined.result']
CASES=[{'name':'Current_A','pump':'4','overhead':'NONE','expected_peak':'9','expected_verdict':'FEASIBLE'},
       {'name':'Current_B','pump':'6','overhead':'NONE','expected_peak':'11','expected_verdict':'INFEASIBLE'},
       {'name':'Overhead_unknown','pump':'4','overhead':'PRESENT_UNBOUNDED','expected_verdict':'UNSUPPORTED'}]


def source_case(kernel,p,home,case):
    folder=home/case['name'];folder.mkdir();source=folder/'resources.csv'
    request='Apply the accepted capacity-over-time method to these scheduled current demands, if its preconditions apply. Carry the checked result through actual Calc, protected Python and Writer. Report a conditional finding with its evidence and limitations. Keep unsupported or unknown inputs explicit.'
    variables=[{'name':name,'type':'quantity','unit':'A','state':'KNOWN','value':amount,'basis':'Declared synthetic resources.csv'}
        for name,amount in [('current_limit','10'),('pump',case['pump']),('heater','3'),('controller','2')]]
    for name,start,stop,unit in [('pump_life','0','7000','ms'),('heater_life','0','7','s'),('controller_life','6','12','s')]:
        variables.append({'name':name,'type':'interval','unit':unit,'state':'KNOWN',
            'value':records.canonical({'start':start,'stop':stop,'unit':unit}),'basis':'Declared synthetic resources.csv'})
    assumptions=['Fixed current capacity; constant additive resource demands; half-open lifetimes; fragmentation and indivisibility are not required by this resource model.',
        'The demands are total declared envelopes including modeled overhead; no additional overhead is required.' if case['overhead']=='NONE' else
        'Additional per-resource overhead is present and unbounded. The listed amounts exclude that overhead. No bound has been supplied.']
    with source.open('w',newline='') as stream:
        out=csv.writer(stream);out.writerow(['name','type','value','unit'])
        for v in variables:out.writerow([v['name'],v['type'],v['value'],v['unit']])
        for text in assumptions:out.writerow(['assumption','text',text,''])
    preview=invoke(kernel,'imports.preview',{'source':str(folder),'profile':'ENGINEERING'},p)
    copy=invoke(kernel,'imports.accept',{'id':preview['id'],'expected_digest':preview['content_digest'],'for_slate':True},p)
    project=invoke(kernel,'projects.create',{'title':case['name'],'intent':request},p)
    assignment=invoke(kernel,'assignments.create',{'project':project['id'],'request':request,'interpretation':request,
        'intended_output':'Checked conditional findings and retained application outputs if the method applies.',
        'success':['Use actual current receipts and explicit method preconditions.'],'stop':['Do not guess consequential missing inputs or silently change preconditions.'],
        'inputs':['files:'+copy['work']+'/resources.csv']},p)
    problem=invoke(kernel,'problems.create',{'project':project['id'],'assignment':assignment['id'],'request':request,'title':case['name'],
        'goals':[request],'variables':variables,'assumptions':assumptions,'questions':[],
        'candidates':['The specified resource schedule fits the declared capacity.','A precondition violation or an adverse resource result may require a conditional refusal.'],
        'sources':[{'copy':copy['id'],'path':'resources.csv','label':'Declared resource quantities, lifetimes and model assumptions'}]},p)
    return {'problem':problem,'copy':copy,'source':source,'sha256':hashlib.sha256(source.read_bytes()).hexdigest()}


def run_case(kernel,p,home,profile,case):
    data=source_case(kernel,p,home,case)
    prepared=invoke(kernel,'work.investigate',{**bound(data['problem']),'copies':[data['copy']['id']],
        'completion':__import__('workbench.adaptive_contract',fromlist=['APPLICATION_COMPLETION']).APPLICATION_COMPLETION,
        'operations':OPS,'allow_direct':False,'title':case['name']+' real-model method transfer',
        'budget':{'seconds':1800,'steps':32,'tokens':240000,'memory_mb':6144,'output_bytes':4194304,'files':12},
        'limits':{'frontier':6,'decisions':16,'max_tokens':768,'decision_seconds':180,'failures':2},'expires':time.time()+3600},p)
    ident=prepared['plan']['id'];invoke(kernel,'work.authorize',{'id':ident,'expected_digest':prepared['content_digest']},p)
    until=time.monotonic()+1500;last=None
    while time.monotonic()<until:
        invoke(kernel,'work.advance',{'id':ident},p);value=invoke(kernel,'work.investigation',{'id':ident},p);state=value['state']
        marker=(state['state'],state.get('reason'),len(value['decisions']),len(value['observations']))
        if marker!=last:print(case['name'],marker,flush=True);last=marker
        if state['state'] not in ('READY','RUNNING'):break
        time.sleep(.2)
    value=invoke(kernel,'work.investigation',{'id':ident},p);state=value['state'];failures=[];observations=value['observations']
    if state['state']!='REVIEW':failures.append('No completed proposed finding: '+str(state.get('reason')))
    joined=[o['result'] for o in observations if o['operation']=='joined.run']
    methods=[o for o in observations if o['operation']=='methods.run']
    if case['expected_verdict']=='UNSUPPORTED':
        if methods or joined:failures.append('Ran a method/application chain despite unbounded additional overhead')
        if not any(o['operation']=='methods.preview' and o['result'].get('precondition_rejected') for o in observations):
            failures.append('No actual source-bound unsupported-precondition receipt')
    else:
        if not methods:failures.append('No actual model-selected method execution')
        if not joined:failures.append('No actual model-selected joined application chain')
        for result in joined:
            snap=result.get('snapshot',{})
            if result.get('state')!='AVAILABLE' or snap.get('state')!=case['expected_verdict'] or snap.get('peak',{}).get('rational')!=case['expected_peak']:
                failures.append('Actual joined result differs from independent frozen expectation')
            refs=result.get('receipt',{}).get('artifacts',[])
            if len(refs)!=4 or not result.get('receipt',{}).get('method'):failures.append('Missing four checked artifacts or retained method binding')
    if hashlib.sha256(data['source'].read_bytes()).hexdigest()!=data['sha256']:failures.append('Source original changed')
    process=subprocess.run([sys.executable,'-m','workbench.joined_model_checks','--reopen',str(kernel.root),str(profile),str(home),ident],
        capture_output=True,text=True,env=locations.child_env(kernel.root),timeout=30)
    if process.returncode:failures.append('Fresh-process reopen failed: '+process.stderr[-1000:]);reopened=None
    else:
        reopened=json.loads(process.stdout)
        if reopened['observations']!=[o['id'] for o in observations]:failures.append('Fresh process changed retained observation references')
    return {'name':case['name'],'state':'FAILED' if failures else 'PASSED_MECHANICAL_MODEL_TRIAL',
        'acceptance_failures':failures,'model_finding':state.get('finding'),'work':value,'fresh_process_reopen':reopened,
        'validated_model_generations':2*len(value['decisions']),'semantic_review':'REQUIRED_SEPARATELY',
        'source_original_unchanged':hashlib.sha256(data['source'].read_bytes()).hexdigest()==data['sha256']}


def checks(model_path,base,output):
    from .engineering_kernel import Kernel,operator
    base.mkdir(parents=True,exist_ok=False);home=base/'Home';home.mkdir();root=base/'Office';profile=base/'profile'
    spec={'schema':'ledger.i05-model-family-spec/1','frozen_before_inference':True,'cases':CASES,
        'owner_completion':'Actual checked application outputs or a tool-verified unsupported method precondition; selected before inference, no prescribed tool sequence.',
        'expected_answers_exposed_to_model':False,'interventions':'Owner supplies a qualified accepted method and one bounded grant per case; no model choice injection or automatic retry.',
        'model_config':{'context':6144,'threads':4,'memory_mb':4480},'source_components':__import__('workbench.joined_work',fromlist=['components']).components(),
        'executor_digest':flow.executor_identity(),'semantic_review':'Independently inspect conditional wording, assumptions, method validity and artifact citations.'}
    (base/'frozen-evaluation.json').write_text(json.dumps(spec,indent=2)+'\n')
    with patch.dict(os.environ,{**environment(os.environ,root,profile),'HOME':str(home)}),patch.object(Path,'home',return_value=home):
        locations.office(root);kernel=Kernel(root);p=operator()
        wait(kernel,p,invoke(kernel,'experiments.qualify',{},p),'experiments.result')
        memory=fixture(kernel,p,home,'Method_basis')
        schedule=invoke(kernel,'math.schedule',{**bound(memory['problem']),'capacity':memory['capacity'],'allocations':memory['allocations']},p)
        basis_job,basis=chain(kernel,p,memory,schedule['id'])
        method=invoke(kernel,'methods.propose',{'job':basis_job['id'],'title':'Checked capacity over declared half-open lifetimes'},p)
        method=invoke(kernel,'methods.accept',{'id':method['id'],'expected_revision':method['revision'],'note':'Synthetic evaluator owner accepts the checked additive profile; the model inherits no authority.'},p)
        def brain_wait(job):return wait(kernel,p,job,'brain.result',240)['result']
        registered=brain_wait(invoke(kernel,'brain.model.add',{'path':str(model_path.resolve()),'origin':'Explicit existing I04 reference-model file reused for an I05 local trial.','managed_copy':False},p))
        if hasattr(os,'posix_fadvise'):
            with model_path.open('rb') as stream:os.posix_fadvise(stream.fileno(),0,0,os.POSIX_FADV_DONTNEED)
        activation=brain_wait(invoke(kernel,'brain.model.use',{'id':registered['model_id'],'options':spec['model_config']},p))
        result={'state':'IN_PROGRESS','profile':'ACTUAL_LOCAL_MODEL_I05_TRIAL','expected_cases':len(CASES),
            'model':slate_action.model_binding(kernel,p),'executor_digest':flow.executor_identity(),'activation':activation,
            'qualifying_method':method,'qualifying_application_chain':basis,'cases':[],'cloud_calls':0,
            'native_visible_takeover':'NOT_QUALIFIED_BY_THIS_TRIAL','target_thinkpad':'PENDING'}
        output.write_text(json.dumps(result,indent=2)+'\n')
        try:
            for case in CASES:
                value=run_case(kernel,p,home,profile,case);result['cases'].append(value)
                result['state']='FAILED' if value['state']=='FAILED' else 'PASSED_MECHANICAL_MODEL_FAMILY_REVIEW_REQUIRED' if len(result['cases'])==len(CASES) else 'IN_PROGRESS'
                output.write_text(json.dumps(result,indent=2)+'\n')
                if value['state']=='FAILED':break
            return result
        finally:local_brain.stop(kernel,'I05_REFERENCE_TRIAL_FINISHED')


def main():
    if len(sys.argv)>1 and sys.argv[1]=='--reopen':
        from .engineering_kernel import Kernel,operator
        root,profile,home=map(Path,sys.argv[2:5]);ident=sys.argv[5]
        os.environ.update(environment(os.environ,root,profile));os.environ['HOME']=str(home)
        kernel=Kernel(root);before=len(kernel.listing('jobs'));value=invoke(kernel,'work.investigation',{'id':ident},operator())
        assert len(kernel.listing('jobs'))==before
        print(json.dumps({'state':'PASSED','work_state':value['state']['state'],'automatic_execution':False,'observations':[o['id'] for o in value['observations']]}));return 0
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--model',type=Path,required=True);parser.add_argument('--keep',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    result=checks(args.model,args.keep,args.output);print(json.dumps({'state':result['state'],'cases':len(result['cases'])}));return 1 if result['state']=='FAILED' else 0


if __name__=='__main__':raise SystemExit(main())
