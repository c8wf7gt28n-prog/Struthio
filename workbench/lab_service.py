"""Owned experiments and selected-board jobs in the existing Kernel lifecycle."""
from __future__ import annotations
import argparse, hashlib, json, os, time
from pathlib import Path
from . import project_desk as records, problem_service as problems, math_service, edit_storage as store, change_sets
from . import experiment_runtime as runtime

JOB_TOOLS = frozenset({'lab.qualify', 'lab.python', 'lab.board'})
OPTIONS = {'type':'object','additionalProperties':False,'properties':{'action':records.ID,'expected_digest':problems.SHA},'required':['action','expected_digest']}
PATH = change_sets.PATH
FIELDS = {
 'experiments.status': ({}, []), 'experiments.qualify': ({}, []),
 'experiments.create': ({**problems.BOUND,'copy':records.ID}, [*problems.BOUND,'copy']),
 'experiments.prepare': ({**problems.BOUND,'copy':records.ID,'script':PATH,'parameters':{'type':'object'},
     'inputs':{'type':'array','maxItems':16,'items':PATH}}, [*problems.BOUND,'copy','script','parameters']),
 'experiments.run': (OPTIONS['properties'], OPTIONS['required']),
 'experiments.result': ({'job':records.ID}, ['job']),
 'experiments.list': ({'id':records.ID}, ['id']),
 'experiments.publish': ({'job':records.ID}, ['job']),
 'boards.prepare': ({**problems.BOUND,'copy':records.ID,'board':PATH}, [*problems.BOUND,'copy','board']),
 'boards.run': (OPTIONS['properties'], OPTIONS['required']),
 'boards.result': ({'job':records.ID}, ['job']),
}
SCOPES = {op: 'read' if op.endswith(('.status','.result','.list')) else 'execute' for op in FIELDS}

SCRIPT = '''"""Coordinator-created experiment. Edit this working copy through Changes.
Results describe the declared concurrent-allocation model, not physical hardware.
"""
import json, csv, sys
from fractions import Fraction
p = json.load(open(sys.argv[1]))
required = ('buffer_A','buffer_B','workspace','memory_limit')
v = {name: Fraction(p[name]) for name in required}
total = v['buffer_A'] + v['buffer_B'] + v['workspace']
fits = total <= v['memory_limit']
result = {'schema':'ledger.experiment-output/1', 'measurements':[
    {'name':'memory_total','value':str(total),'unit':'MiB'},
    {'name':'memory_fits','value':fits,'unit':'1'}],
    'assumptions':['All three allocations are concurrent. Lifetimes remain unknown.']}
open(sys.argv[2]+'/result.json','w').write(json.dumps(result))
with open(sys.argv[2]+'/sweep.csv','w',newline='') as stream:
    out=csv.writer(stream); out.writerow(['workspace_MiB','total_MiB','fits'])
    for i in range(11):
        amount=v['buffer_A']+v['buffer_B']+i
        out.writerow([i,str(amount),amount<=v['memory_limit']])
print('Experiment executed; memory total =', total, 'MiB; fits =', fits)
'''


def read(kernel, kind, ident, p):
    with kernel.db() as db:return records.read(db, kind, ident, p)


def components():
    return {name:runtime.sha(Path(__file__).with_name(name)) for name in ('lab_service.py','board_runtime.py','experiment_runtime.py',
        'import_profiles.py','change_sets.py','edit_storage.py','problem_service.py','engineering_kernel.py','engineering_cli.py','kicad_tools.py')}


def delegated(kernel, copy, p):
    meta, row, root = store.workspace(kernel, copy, p)
    if not row['for_slate']:raise ValueError('LAB_COPY_DELEGATION_REQUIRED')
    return meta, row, root


def capture(kernel, copy, path, p, maximum=1048576):
    meta,row,root=delegated(kernel,copy,p); change_sets.check_path(meta,path)
    raw,info=store.read_bytes(root,path,maximum)
    return {'copy':copy,'path':path,'sha256':info['sha256'],'bytes':len(raw),'object':store.keep_bytes(kernel,raw)}


def check(kernel, plan, p):
    if plan['components']!=components():raise ValueError('LAB_IMPLEMENTATION_CHANGED: prepare a new action')
    if plan['operation']=='QUALIFY':
        if runtime.status()!=plan['environment']:raise ValueError('LAB_RUNTIME_CHANGED')
        return None
    problem=math_service.current(kernel,plan['problem'],p)
    problems.check_bound(problem,{'expected_revision':plan['problem_revision'],'expected_context_digest':plan['context_digest']})
    for item in plan['inputs']:
        _,_,root=delegated(kernel,item['copy'],p)
        observed=store.inspect_file(root,item['path'],32*1024*1024)
        if not observed or observed['sha256']!=item['sha256']:raise ValueError('LAB_INPUT_REVISION_CHANGED_OR_MISSING: '+item['path'])
    if plan['operation']=='PYTHON' and runtime.status()!=plan['environment']:raise ValueError('LAB_RUNTIME_CHANGED')
    if plan['operation']=='BOARD':
        from . import kicad_tools as cad
        if cad.discover()!=plan['environment']:raise ValueError('LAB_BOARD_TOOL_CHANGED')
    return problem


def result(kernel, ident, p):
    from . import record_access
    job=record_access.read(kernel,'jobs',ident,p)
    if job['tool'] not in JOB_TOOLS:raise ValueError('Not an experiment or selected-board job')
    if job['state']!='Completed':return {'state':job['state'],'job':ident,'error':job.get('error'),'files':[],'execution_status':job['state'].upper()}
    value=read(kernel,'lab_result',ident,p);folder=kernel.state/'jobs'/ident
    for item in value['files']:
        path=Path(item['name'])
        if path.is_absolute() or '..' in path.parts or runtime.sha(folder/path)!=item['sha256']:raise ValueError('LAB_OBSERVED_OUTPUT_CHANGED')
    try:check(kernel,read(kernel,'lab_action',value['action'],p),p); applicability='CURRENT'
    except (OSError,ValueError):applicability='STALE'
    return {**value,'state':'AVAILABLE','applicability':applicability,'directory':str(folder)}


def qualification(kernel,p):
    binding=runtime.status()
    for job in reversed(kernel.listing('jobs')):
        if job.get('owner')==p.identity and job['tool']=='lab.qualify' and job['state']=='Completed':
            try:
                value=result(kernel,job['id'],p);q=value['observation']['qualification']
                if value['applicability']=='CURRENT' and q['qualified'] and q['binding']==binding and q['expires']>time.time():return {'qualified':True,'job':job['id'],'expires':q['expires']}
            except (OSError,ValueError,KeyError):pass
    return {'qualified':False,'reason':'Run the registered qualification job on this host; missing or changed runtimes are refused.'}


def save_plan(kernel,p,**values):
    plan=records.new('lab_action',p,schema='ledger.lab-action/1',components=components(),**values)
    plan['binding_digest']=records.digest(plan)
    with kernel.db() as db:return records.write(db,plan,p,'LAB_PREPARED')


def create(kernel,args,p):
    problem=math_service.current(kernel,args['id'],p);problems.check_bound(problem,args)
    delegated(kernel,args['copy'],p)
    folder='Experiments/'+__import__('uuid').uuid4().hex; path=folder+'/experiment.py'
    params={v['name']:v['value'] for v in problem['variables'] if v['state']=='KNOWN' and v['type']=='quantity'}
    # Existing frozen-change path owns the stub and journals its creation.
    proposal=records.result_of(kernel,'changes.propose',{'copy':args['copy'],'operations':[
        {'op':'CREATE','path':path,'text':SCRIPT},{'op':'CREATE','path':folder+'/parameters.json','text':records.canonical(params)}],
        'note':'Coordinator-created experiment stub; execution is a separate frozen action.','origin':'HUMAN'},p)
    # This endpoint is scoped to already delegated working copies, never originals.
    delegated(kernel,args['copy'],p)
    commit=change_sets.apply_proposal(kernel,{'id':proposal['id'],'expected_digest':proposal['content_digest']},p)
    return {'copy':args['copy'],'script':path,'parameters':params,'commit':commit['id'],'model_selected':False}


def prepare(kernel,args,p,board=False):
    problem=math_service.current(kernel,args['id'],p);problems.check_bound(problem,args)
    name=args['board'] if board else args['script']
    if Path(name).suffix!=('.kicad_pcb' if board else '.py'):raise ValueError('Select a native board or Python script of the required type')
    names=[name]+([] if board else args.get('inputs',[]))
    if len(names)!=len(set(names)):raise ValueError('Duplicate selected input')
    inputs=[capture(kernel,args['copy'],path,p,32*1024*1024 if board else 1048576) for path in names]
    if sum(i['bytes'] for i in inputs)>32*1024*1024:raise ValueError('LAB_SELECTED_INPUT_BUDGET')
    params=args.get('parameters',{})
    if len(records.canonical(params))>65536:raise ValueError('LAB_PARAMETER_BUDGET')
    if board:
        from . import kicad_tools as cad
        environment=cad.discover()
        if not environment['executable']:raise ValueError(environment['reason'])
    else:
        environment=runtime.status();q=qualification(kernel,p)
        if not environment['available'] or not q['qualified']:raise ValueError('LAB_PYTHON_NOT_QUALIFIED: '+str(q.get('reason')))
    return save_plan(kernel,p,operation='BOARD' if board else 'PYTHON',problem=problem['id'],problem_revision=problem['revision'],
        context_digest=problem['context_digest'],sources=problem['sources'],copy=args['copy'],inputs=inputs,
        parameters=params,environment=environment,qualification=None if board else q,
        effects=['read','owned_output_write'],model_selected=False,assumptions=problem['assumptions'])


def authorize_job(kernel,tool,options,p):
    if tool not in JOB_TOOLS or set(options)!={'action','expected_digest'} or not {'read','execute'}<=p.scopes:raise ValueError('LAB_JOB_SCOPE')
    plan=read(kernel,'lab_action',options['action'],p)
    if plan['binding_digest']!=options['expected_digest']:raise ValueError('LAB_ACTION_DIGEST')
    if tool!={'QUALIFY':'lab.qualify','PYTHON':'lab.python','BOARD':'lab.board'}[plan['operation']]:raise ValueError('LAB_ACTION_TOOL_BINDING')
    check(kernel,plan,p)
    if plan['operation']=='PYTHON' and not qualification(kernel,p)['qualified']:raise ValueError('LAB_QUALIFICATION_EXPIRED')
    return plan


def submit(kernel,plan,p):
    tool={'QUALIFY':'lab.qualify','PYTHON':'lab.python','BOARD':'lab.board'}[plan['operation']]
    return records.result_of(kernel,'jobs.submit',{'tool':tool,'lab':{'action':plan['id'],'expected_digest':plan['binding_digest']},
        'request_key':'lab:'+plan['id'],'goal':'Qualify Python runtime' if tool=='lab.qualify' else 'Observe a frozen owned experiment',
        'timeout':180 if tool in ('lab.qualify','lab.board') else runtime.LIMITS['seconds']},p)


def parse_output(path):
    from . import math_units
    raw=Path(path).read_bytes()
    if len(raw)>65536:raise ValueError('LAB_RESULT_SCHEMA_BUDGET')
    from .record_io import strict_json
    value=strict_json(raw)
    if not isinstance(value,dict) or set(value)!={'schema','measurements','assumptions'} or value['schema']!='ledger.experiment-output/1':raise ValueError('LAB_RESULT_SCHEMA')
    measurements=value['measurements'];names=set()
    if not isinstance(measurements,list) or not 1<=len(measurements)<=64:raise ValueError('LAB_RESULT_MEASUREMENTS')
    for row in measurements:
        if not isinstance(row,dict) or set(row)!={'name','value','unit'} or not isinstance(row['name'],str) or not 1<=len(row['name'])<=100 or row['name'] in names:raise ValueError('LAB_RESULT_MEASUREMENT')
        names.add(row['name']);math_units.unit_spec(row['unit'])
        if type(row['value']) is bool:
            if row['unit']!='1':raise ValueError('LAB_BOOLEAN_UNIT')
        elif type(row['value']) is str:math_units.rational(row['value'])
        else:raise ValueError('LAB_RESULT_EXACT_VALUE')
    if not isinstance(value['assumptions'],list) or len(value['assumptions'])>32 or any(type(x) is not str or len(x)>1000 for x in value['assumptions']):raise ValueError('LAB_RESULT_ASSUMPTIONS')
    return value


def work(kernel,ident):
    from .engineering_kernel import Principal
    job=kernel.record('jobs',ident);p=Principal(job['owner'],frozenset({'read','execute'}));options=job['request_spec']['lab']
    plan=authorize_job(kernel,job['tool'],options,p);folder=kernel.state/'jobs'/ident
    if plan['operation']=='QUALIFY':
        observation={'qualification':runtime.qualify(folder/'qualification'),'state':'QUALIFIED'}
    else:
        inp=folder/'selected-inputs';inp.mkdir(exist_ok=False)
        for n,item in enumerate(plan['inputs']):
            name='experiment.py' if plan['operation']=='PYTHON' and n==0 else 'board.kicad_pcb' if n==0 else 'selected/'+item['path']
            dest=inp/name;dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes(store.object_bytes(kernel,item['object'],32*1024*1024))
            if runtime.sha(dest)!=item['sha256']:raise ValueError('LAB_FROZEN_INPUT_CHANGED')
        (inp/'parameters.json').write_text(records.canonical(plan['parameters']))
        if plan['operation']=='PYTHON':
            runner=runtime.Runner(runtime.unpack(folder));execution=runner.execute(inp,folder/'outputs')
            observation={'execution':execution,'state':'EXECUTION_FAILED','parsed':None,'interpretation':'Declared model experiment; no physical qualification'}
            if execution['exit_code']==0 and not execution['trap']:
                try:observation.update(parsed=parse_output(folder/'outputs/result.json'),state='OBSERVED')
                except (OSError,ValueError,TypeError) as exc:observation.update(state='OUTPUT_INVALID',parse_error=str(exc))
        else:
            from . import board_runtime
            observation=board_runtime.run(kernel.root,plan['environment'],inp/'board.kicad_pcb',folder/'board-native')
        check(kernel,plan,p)
    # The guest cannot write this manifest or the Kernel database. Failed native
    # attempts remain Completed coordinator jobs with a failed observation.
    files=[]
    for path in sorted(folder.rglob('*')):
        if not path.is_file() or 'runtime' in path.relative_to(folder).parts or path.name in ('stdout.log','stderr.log'):continue
        if path.is_symlink():raise ValueError('LAB_OUTPUT_LINK')
        files.append({'name':path.relative_to(folder).as_posix(),'sha256':runtime.sha(path),'bytes':path.stat().st_size})
    value=records.new('lab_result',p,id=ident,schema='ledger.lab-result/1',job=ident,action=plan['id'],
        problem=plan.get('problem'),problem_revision=plan.get('problem_revision'),context_digest=plan.get('context_digest'),
        observation=observation,files=files,completed=time.time(),model_calls=0,physical_qualification=False)
    with kernel.db() as db:records.write(db,value,p,'LAB_OBSERVED')
    print(json.dumps({'job':ident,'observation':observation['state'],'files':len(files),'model_calls':0}))


def publish(kernel,ident,p):
    value=result(kernel,ident,p);plan=read(kernel,'lab_action',value['action'],p)
    if value['state']!='AVAILABLE' or value['applicability']!='CURRENT' or plan['operation']=='QUALIFY':raise ValueError('LAB_PUBLISH_CURRENT_RESULT_REQUIRED')
    check(kernel,plan,p);copied=[]
    # Generated outputs only; selected source snapshots and runtime stay private.
    items=[i for i in value['files'] if i['name'].startswith('outputs/') or i['name'] in ('board-native/drc/drc.json','board-native/export/board.svg')]
    with store.lock(kernel,plan['copy']):
        meta,row,root=delegated(kernel,plan['copy'],p)
        for item in items:
            relative='Experiments/Results/'+ident+'/'+Path(item['name']).name;change_sets.check_path(meta,relative)
            raw=(Path(value['directory'])/item['name']).read_bytes()
            with store.parent(root,relative,create=True) as (directory,name):
                try:fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=directory)
                except FileExistsError:
                    if store.read_bytes(root,relative,2*1024*1024)[1]['sha256']!=item['sha256']:raise ValueError('LAB_PUBLICATION_CONFLICT')
                else:
                    with os.fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
                    os.fsync(directory)
            copied.append({**item,'copy':plan['copy'],'path':relative,'address':'files:'+row['work']+'/'+relative})
    return {'files':copied,'originals_changed':False}


def dispatch(kernel,op,args,p):
    if op=='experiments.status':
        from . import kicad_tools
        return {'python':runtime.status(),'qualification':qualification(kernel,p),'board':kicad_tools.discover(),'model_calls':0}
    if op=='experiments.qualify':
        environment=runtime.status()
        if not environment['available']:raise ValueError('PYTHON_WASI_UNAVAILABLE: '+environment['reason'])
        return submit(kernel,save_plan(kernel,p,operation='QUALIFY',environment=environment,effects=['owned_output_write']),p)
    if op=='experiments.create':return create(kernel,args,p)
    if op in ('experiments.prepare','boards.prepare'):return prepare(kernel,args,p,op=='boards.prepare')
    if op in ('experiments.run','boards.run'):
        plan=read(kernel,'lab_action',args['action'],p)
        expected='BOARD' if op=='boards.run' else 'PYTHON'
        if plan['operation']!=expected or plan['binding_digest']!=args['expected_digest']:raise ValueError('LAB_ACTION_BINDING')
        return submit(kernel,plan,p)
    if op in ('experiments.result','boards.result'):return result(kernel,args['job'],p)
    if op=='experiments.publish':return publish(kernel,args['job'],p)
    if op=='experiments.list':
        with kernel.db() as db:
            problem=problems.load(db,args['id'],p)
            actions=problems.related(db,problem,'lab_action',p);results=problems.related(db,problem,'lab_result',p)
        ids={a['id'] for a in actions}
        jobs=[j for j in kernel.listing('jobs') if j['owner']==p.identity and j['tool'] in JOB_TOOLS and j.get('request_spec',{}).get('lab',{}).get('action') in ids]
        return {'actions':actions,'results':results,'jobs':jobs}
    raise ValueError('Unknown lab operation')


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--job',required=True);a=ap.parse_args()
    from .engineering_kernel import Kernel
    work(Kernel(a.root),a.job)
