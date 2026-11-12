"""Mathematical observations and owned Office actions in the shared Kernel store."""
from __future__ import annotations
import argparse,hashlib,json,os,time
from pathlib import Path
from . import project_desk as records,problem_service as problems,math_model as core,math_backend as backend

MODEL={'type':'object'};TEXT={'type':'string','maxLength':1000};BACKEND={'type':'string','enum':['EXACT','SYMPY','Z3']}
INPUT={'expression':TEXT,'model':MODEL,'assumptions':records.STRINGS,'overrides':MODEL,'output_unit':{'type':'string','maxLength':64}}
BOUND=problems.BOUND
FIELDS={
 'math.status':({},[]),'math.units':({},[]),
 'math.validate':({'model':MODEL},['model']),
 'math.evaluate':({'model':MODEL,'output_unit':TEXT},['model']),
 'math.solve':({'model':MODEL,'backend':{'type':'string','enum':['SYMPY','Z3']}},['model','backend']),
 'math.preview':({'id':records.ID,**INPUT},['id']),
 'math.prepare':({**BOUND,**INPUT,'backend':BACKEND},list(BOUND)),
 'math.run':({'action':records.ID},['action']),
 'math.get':({'id':records.ID},['id']),
 'math.list':({'id':records.ID},['id']),
 'math.sweep':({'action':records.ID,'variable':TEXT,'start':TEXT,'stop':TEXT,'count':{'type':'integer','minimum':2,'maximum':201}},['action','variable','start','stop']),
 'math.office.prepare':({'receipt':records.ID},['receipt']),
 'math.office.run':({'action':records.ID,'expected_digest':problems.SHA},['action','expected_digest']),
 'math.office.publish':({'job':records.ID},['job']),
 'math.office.result':({'job':records.ID},['job']),
}
SCOPES={op:'execute' if op in ('math.prepare','math.run','math.office.prepare','math.office.run','math.office.publish') else 'read' for op in FIELDS}
JOB_TOOLS=frozenset({'math.office','math.joined','math.method','math.session'})
OPTIONS={'type':'object','additionalProperties':False,'properties':{'action':records.ID,'expected_digest':problems.SHA},'required':['action','expected_digest']}


def invoke(kernel,op,args,p):return records.result_of(kernel,op,args,p)


def current(kernel,ident,p):
    sheet=problems.get(kernel,ident,p)
    if sheet['freshness']['state']!='CURRENT':raise ValueError('MATH_SOURCE_CHANGED: reopen and explicitly rebind problem sources')
    return sheet['problem']


def components():
    return {name:hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() for name in
        ('math_model.py','math_units.py','math_backend.py','math_service.py','math_office.py','office_math_runtime.py','LedgerOffice.java')}


def model_for(problem,args):
    if ('model' in args)==('expression' in args):raise ValueError('Supply exactly one expression or typed model')
    variables={v['name']:{'unit':v['unit'],**({'value':v['value']} if v['state']=='KNOWN' else {})} for v in problem['variables'] if v['type']=='quantity'}
    overrides=args.get('overrides',{});assumptions=list(args.get('assumptions',[]))
    if len(overrides)>16:raise ValueError('Too many scenario overrides')
    for name,value in overrides.items():
        if name not in variables:raise ValueError('Override needs a declared quantity')
        from .math_units import rational
        rational(value);variables[name]['value']=value;assumptions.append('Scenario override: '+name+' = '+value+' '+variables[name]['unit'])
    ir=core.compile_expression(args['expression'],variables,assumptions) if 'expression' in args else core.validate(args['model'])
    bindings=[]
    for name,variable in ir['model']['variables'].items():
        source=next((v for v in problem['variables'] if v['name']==name),None)
        if source and source['type']!='quantity':raise ValueError('This profile needs a scalar quantity, not the '+source['type']+' variable '+name)
        matches=source and variable['unit']==source['unit'] and variable.get('value')==source.get('value')
        bindings.append({'name':name,'origin':'PROBLEM_REVISION' if matches else 'DECLARED_SCENARIO','problem_variable':source})
    if any(b['origin']=='DECLARED_SCENARIO' for b in bindings) and not ir['model']['assumptions']:
        raise ValueError('Scenario quantities require explicit model assumptions')
    if args.get('output_unit'):core.evaluate(ir,output_unit=args['output_unit'])
    return ir,bindings


def read_action(kernel,ident,p,kind='math_action'):
    with kernel.db() as db:return records.read(db,kind,ident,p)


def check_action(kernel,action,p):
    problem=current(kernel,action['problem'],p)
    problems.check_bound(problem,{'expected_revision':action['problem_revision'],'expected_context_digest':action['context_digest']})
    if action['components']!=components():raise ValueError('MATH_CONTRACT_CHANGED: prepare a new calculation')
    return problem


def prepare(kernel,args,p):
    problem=current(kernel,args['id'],p);problems.check_bound(problem,args);ir,bindings=model_for(problem,args)
    operation='math.evaluate' if args.get('backend','EXACT')=='EXACT' else 'math.solve'
    from .engineering_cli import schemas
    action=records.new('math_action',p,schema='arc.tool-action/1',profile='arc.problem-math/1',problem=problem['id'],
        problem_revision=problem['revision'],context_digest=problem['context_digest'],sources=problem['sources'],
        model=ir['model'],model_digest=ir['model_digest'],variable_bindings=bindings,backend=args.get('backend','EXACT'),
        output_unit=args.get('output_unit') or None,operation=operation,operation_schema=schemas()[operation],components=components(),
        effects=['read'],expression=args.get('expression'),result=None,model_selected=False)
    action['binding_digest']=records.digest(action)
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE');problems.check_bound(problems.load(db,problem['id'],p),args)
        return records.write(db,action,p,'MATH_PREPARED')


def run(kernel,ident,p):
    action=read_action(kernel,ident,p)
    if action['result']:return {'receipt':read_action(kernel,action['result'],p,'math_result'),'replayed':True}
    check_action(kernel,action,p);args={'model':action['model']}
    if action['operation']=='math.solve':args['backend']=action['backend']
    elif action['output_unit']:args['output_unit']=action['output_unit']
    snapshot=invoke(kernel,action['operation'],args,p);check_action(kernel,action,p)
    if action['operation']=='math.solve' and action['output_unit'] and snapshot.get('evaluation'):
        snapshot['evaluation']=core.evaluate(core.validate(action['model']),snapshot.get('assignments',{}),action['output_unit'])
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE');live=records.read(db,'math_action',ident,p)
        problems.check_bound(problems.load(db,action['problem'],p),{'expected_revision':action['problem_revision'],'expected_context_digest':action['context_digest']})
        if live['result']:return {'receipt':records.read(db,'math_result',live['result'],p),'replayed':True}
        value=records.new('math_result',p,schema='arc.tool-result/1',problem=action['problem'],problem_revision=action['problem_revision'],
            context_digest=action['context_digest'],action=ident,action_binding_digest=action['binding_digest'],operation=action['operation'],
            snapshot=snapshot,output_digest=records.digest(snapshot),effects=['read'],completed=time.time(),model_calls=0)
        records.write(db,value,p,'MATH_OBSERVED');records.edit(live,1);live['result']=value['id'];records.write(db,live,p,'MATH_RESULT_BOUND',expected=1)
        return {'receipt':value,'replayed':False}


def office_prepare(kernel,receipt_id,p):
    from . import office_math_runtime
    receipt=read_action(kernel,receipt_id,p,'math_result');action=read_action(kernel,receipt['action'],p);problem=check_action(kernel,action,p)
    if receipt['snapshot'].get('state') not in ('FEASIBLE','INFEASIBLE'):raise ValueError('A successful numerical math observation is required before Office')
    ir=core.validate(action['model']);result=core.evaluate(ir,receipt['snapshot'].get('assignments',{}),action['output_unit'])
    if result['state'] not in ('FEASIBLE','INFEASIBLE'):raise ValueError('Complete valid numerical inputs are needed for Office')
    engine=office_math_runtime.probe()
    if not engine['available']:raise ValueError('OFFICE_UNO_PREREQUISITES_MISSING')
    value=records.new('math_office_action',p,schema='arc.tool-action/1',profile='arc.problem-office/1',problem=problem['id'],
        problem_revision=problem['revision'],context_digest=problem['context_digest'],calculation=action['id'],receipt=receipt_id,
        environment=engine,effects=['read','working_write'],components=components(),output_names=['Calculation.ods','Findings.docx','Findings.pdf'])
    value['output_directory']='Calculations/'+value['id']
    value['copy']=problem['sources'][0]['copy'] if problem['sources'] else None
    value['binding_digest']=records.digest(value)
    with kernel.db() as db:return records.write(db,value,p,'OWNED_OFFICE_PREPARED')


def authorize_job(kernel,tool,options,p):
    from . import office_math_runtime
    if tool not in JOB_TOOLS or set(options)!={'action','expected_digest'} or not {'read','execute'}<=p.scopes:raise ValueError('MATH_OFFICE_JOB_SCOPE')
    if tool!='math.office':
        from . import joined_work,checked_methods,native_sessions
        return {'math.joined':joined_work.authorize,'math.method':checked_methods.authorize,'math.session':native_sessions.authorize}[tool](kernel,options,p)
    action=read_action(kernel,options['action'],p,'math_office_action')
    if action['binding_digest']!=options['expected_digest']:raise ValueError('MATH_OFFICE_ACTION_DIGEST')
    check_action(kernel,read_action(kernel,action['calculation'],p),p)
    if office_math_runtime.probe()!=action['environment']:raise ValueError('MATH_OFFICE_ENVIRONMENT_CHANGED')
    if action['copy']:
        from .edit_storage import workspace
        if not workspace(kernel,action['copy'],p)[1]['for_slate']:raise ValueError('MATH_OFFICE_COPY_DELEGATION_REQUIRED')
    return action


def office_result(kernel,ident,p):
    from . import record_access
    job=record_access.read(kernel,'jobs',ident,p)
    if job['tool']!='math.office':raise ValueError('Not a mathematical Office job')
    if job['state']!='Completed':return {'state':job['state'],'job':ident,'error':job.get('error'),'files':[]}
    folder=kernel.state/'jobs'/ident;value=json.loads((folder/'math_office_result.json').read_text())
    if value['job']!=ident:raise ValueError('MATH_OFFICE_JOB_BINDING')
    for item in value['files']:
        if Path(item['name']).name!=item['name'] or hashlib.sha256((folder/item['name']).read_bytes()).hexdigest()!=item['sha256']:raise ValueError('MATH_OFFICE_OUTPUT_CHANGED')
    try:check_action(kernel,read_action(kernel,value['calculation'],p),p);state='AVAILABLE'
    except ValueError:state='HISTORICAL_INPUTS_CHANGED'
    return {**value,'state':state,'directory':str(folder)}


def office_work(kernel,ident):
    from .engineering_kernel import Principal
    from . import math_office,work_trail
    job=kernel.record('jobs',ident);p=Principal(job['owner'],frozenset({'read','execute'}));options=job['request_spec']['calculation']
    if job['tool']!='math.office':
        from . import joined_work,checked_methods,native_sessions
        return {'math.joined':joined_work.work,'math.method':checked_methods.work,'math.session':native_sessions.work}[job['tool']](kernel,job,p)
    plan=authorize_job(kernel,job['tool'],options,p);action=read_action(kernel,plan['calculation'],p);receipt=read_action(kernel,plan['receipt'],p,'math_result')
    problem=check_action(kernel,action,p);folder=kernel.state/'jobs'/ident
    def cancelled():return kernel.record('jobs',ident).get('cancel') or work_trail.execution_held(kernel)
    result=math_office.run(folder,problem,action,receipt,cancelled);check_action(kernel,action,p)
    if cancelled():raise ValueError('MATH_OFFICE_CANCELLED_BEFORE_COMMIT')
    value={'schema':'arc.math-office-result/1','job':ident,'problem':problem['id'],'problem_revision':problem['revision'],
        'context_digest':problem['context_digest'],'calculation':action['id'],'receipt':receipt['id'],'working_files':[],**result}
    (folder/'math_office_result.json').write_text(records.canonical(value))
    print(json.dumps({'outcome':'PASS','files':len(value['files']),'formula_measurements':len(value['measurement'])}))



def publish(kernel,ident,p):
    from . import edit_storage,change_sets
    value=office_result(kernel,ident,p)
    if value['state']!='AVAILABLE':raise ValueError('Publish only a completed current mathematical Office result')
    job=kernel.record('jobs',ident);plan=read_action(kernel,job['request_spec']['calculation']['action'],p,'math_office_action')
    authorize_job(kernel,'math.office',job['request_spec']['calculation'],p)
    if not plan['copy']:return {'files':[],'directory':value['directory'],'notice':'No source working copy is selected'}
    copied=[]
    with edit_storage.lock(kernel,plan['copy']):
        meta,row,root=edit_storage.workspace(kernel,plan['copy'],p)
        for item in value['files']:
            relative=plan['output_directory']+'/'+item['name'];change_sets.check_path(meta,relative)
            raw=(Path(value['directory'])/item['name']).read_bytes()
            with edit_storage.parent(root,relative,create=True) as (directory,name):
                try:fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=directory)
                except FileExistsError:
                    if edit_storage.read_bytes(root,relative,32*1024*1024)[1]['sha256']!=item['sha256']:raise ValueError('Generated output changed; preserve it and make a new calculation')
                else:
                    with os.fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
                    os.fsync(directory)
            copied.append({'copy':plan['copy'],'path':relative,'address':'files:'+row['work']+'/'+relative,**item})
    return {'files':copied,'directory':str(root/plan['output_directory']),'originals_changed':False}


def dispatch(kernel,op,args,p):
    if op=='math.status':
        from . import office_math_runtime
        return {'schema':'arc.math-status/1','backends':backend.status(),'office':office_math_runtime.probe(),'exact_arithmetic':'BUILT_IN','model_calls':0}
    if op=='math.units':
        from .stac.quantities import UNITS
        from .math_units import unit_spec
        return {'units':[{'unit':name,'dimension':kind,'exact_base_factor':str(unit_spec(name)[1])} for name,(kind,_) in UNITS.items()], 'compound':'Products, division and integer powers; MB and MiB are distinct'}
    if op in ('math.validate','math.evaluate','math.solve'):
        ir=core.validate(args['model'])
        return ir if op=='math.validate' else core.evaluate(ir,output_unit=args.get('output_unit')) if op=='math.evaluate' else backend.solve(ir,args['backend'])
    if op=='math.preview':
        with kernel.db() as db:problem=problems.load(db,args['id'],p)
        ir,bindings=model_for(problem,args)
        return {'problem':problem['id'],'problem_revision':problem['revision'],'context_digest':problem['context_digest'],
            'model':ir['model'],'variable_bindings':bindings,'evaluation':core.evaluate(ir,output_unit=args.get('output_unit'))}
    if op=='math.prepare':return prepare(kernel,args,p)
    if op=='math.run':return run(kernel,args['action'],p)
    if op=='math.get':
        action=read_action(kernel,args['id'],p)
        try:check_action(kernel,action,p);applicability='CURRENT'
        except ValueError:applicability='HISTORICAL_INPUTS_CHANGED'
        return {'action':action,'receipt':read_action(kernel,action['result'],p,'math_result') if action['result'] else None,'applicability':applicability}
    if op=='math.list':
        with kernel.db() as db:
            value=problems.load(db,args['id'],p)
            return {'actions':problems.related(db,value,'math_action',p),'receipts':problems.related(db,value,'math_result',p)}
    if op=='math.sweep':
        action=read_action(kernel,args['action'],p);check_action(kernel,action,p)
        return core.sweep(core.validate(action['model']),args['variable'],args['start'],args['stop'],args.get('count',81),action['output_unit'])
    if op=='math.office.prepare':return office_prepare(kernel,args['receipt'],p)
    if op=='math.office.run':
        authorize_job(kernel,'math.office',args,p)
        return invoke(kernel,'jobs.submit',{'tool':'math.office','calculation':args,'request_key':'math-office:'+args['action'],'timeout':220},p)
    if op=='math.office.publish':return publish(kernel,args['job'],p)
    if op=='math.office.result':return office_result(kernel,args['job'],p)
    raise ValueError('Unknown mathematical operation')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);parser.add_argument('--job',required=True);args=parser.parse_args()
    from .engineering_kernel import Kernel
    office_work(Kernel(args.root),args.job)


if __name__=='__main__':main()
