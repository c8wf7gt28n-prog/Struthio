"""Adaptive profile of the existing continuing-work executor and Agenda.

Model proposals never alter grants. Every action has a durable intent, a checked
operation/copy/revision binding, and an actual retained observation before the
next decision. No separate queue, timer, database or grant store is introduced.
"""
from __future__ import annotations
import json,time,uuid
from . import project_desk as records,continuing_work as flow,adaptive_contract as contract
from . import problem_service as problems,math_service,work_scope,work_trail,change_sets,edit_storage as store
from . import slate_action
FIELDS=contract.FIELDS;SCOPES=contract.SCOPES


def binding(plan,state):
    return records.digest({'order':records.digest(plan),'problem':state['problem'],'copies':state['copies']})


def gate(kernel,plan,state,p,db=None):
    if plan.get('profile')!=contract.PROFILE:raise ValueError('Not an adaptive work order')
    if db is None:
        with kernel.db() as db:return gate(kernel,plan,state,p,db)
    flow.grant(db,plan);status=work_trail.work_status(kernel,db)
    if status['held'] or status['epoch']!=state['epoch']:raise ValueError('WORK_HELD_OR_EPOCH_CHANGED')
    return status


def check_problem(kernel,plan,state,p):
    problem=math_service.current(kernel,state['problem']['id'],p);problems.check_bound(problem,state['problem'])
    if slate_action.model_binding(kernel,p)!=plan['adaptive']['model']:raise ValueError('ADAPTIVE_MODEL_CONFIGURATION_CHANGED')
    return problem


def foundations(kernel,plan,state,p):
    flow.foundations(kernel,plan,state,p)
    return check_problem(kernel,plan,state,p)


def create(kernel,args,p):
    problem=math_service.current(kernel,args['id'],p);problems.check_bound(problem,args)
    if not problem.get('assignment'):raise ValueError('Adaptive work requires the problem assignment')
    operations=args['operations']
    if len(set(operations))!=len(operations) or any(op not in contract.OPS for op in operations):raise ValueError('ADAPTIVE_SELECTED_OPERATIONS')
    if 'changes.apply' in operations and 'changes.propose' not in operations:raise ValueError('Delegate proposal creation with working-copy application')
    completion=args.get('completion','OBSERVED_FINDING')
    if completion not in ('OBSERVED_FINDING',contract.APPLICATION_COMPLETION):raise ValueError('ADAPTIVE_COMPLETION_POLICY')
    if completion==contract.APPLICATION_COMPLETION and ('joined.run' not in operations or args.get('allow_direct',False)):
        raise ValueError('Application completion requires the joined job in the scope and actual cited evidence')
    if 'brain.action' not in p.tools:raise ValueError('ACTION_MODEL_TOOL_NOT_DELEGATED')
    model=slate_action.model_binding(kernel,p)
    from . import local_brain
    local_brain.recheck(local_brain.model(kernel,model['model_id']))
    if args['budget']['memory_mb']<model['config']['memory_mb']:raise ValueError('ADAPTIVE_MODEL_MEMORY_EXCEEDS_GRANT')
    if any(s['copy'] not in args['copies'] for s in problem['sources']):raise ValueError('Problem source copy outside the selected grant')
    options={'problem':{'id':problem['id'],'expected_revision':problem['revision'],'expected_context_digest':problem['context_digest']},
        'model':model,'limits':{**args['limits'],'failures':args['limits'].get('failures',2)},'operations':operations,'allow_direct':args.get('allow_direct',False),
        'completion':completion}
    return flow.create(kernel,{'assignment':problem['assignment'],'copies':args['copies'],'steps':[],
        'budget':args['budget'],'expires':args['expires'],'title':args['title']},p,adaptive=options)


def initialize(plan,state,options,problem):
    from .engineering_cli import schemas
    plan.update(profile=contract.PROFILE,adaptive=options,operations=sorted(options['operations']),
        effects=sorted(set(contract.OPS[op] for op in options['operations'])),restart='RECONCILE_THEN_EXPLICIT_RESUME')
    plan['operation_schemas']={op:schemas()[op] for op in plan['operations']}
    state.update(problem=options['problem'],steps=[],current=None,observations=[],decisions=[],seen=[],question=None,
        frontier=[{'key':'b'+str(i+1),'hypothesis':text,'assumptions':[],'status':'PROPOSED','problem_revision':problem['revision'],
                   'context_digest':problem['context_digest'],'origin':'OWNER_PROBLEM_CANDIDATE'} for i,text in enumerate((problem.get('candidates') or ['Investigate the saved question.'])[:options['limits']['frontier']])])


def read(kernel,ident,p):
    with kernel.db() as db:plan,state=flow.load(db,ident,p)
    if plan.get('profile')!=contract.PROFILE:raise ValueError('Not an adaptive investigation')
    return plan,state


def observation(kernel,ident,p):
    with kernel.db() as db:return records.read(db,'adaptive_observation',ident,p)


def summarize(value):
    """Bounded model view; complete results stay in owned receipts/steps."""
    if not isinstance(value,dict):return {'value':str(value)[:1000]}
    if value.get('kind')=='method_preview':
        return {**{k:value[k] for k in ('kind','state','precondition_rejected','reason','method_id','method_revision','declarations') if k in value},
            'check_completed':bool(value.get('binding_current') and (value['state']=='SUPPORTED' or value.get('precondition_rejected'))),
            'check_scope':'METHOD_PRECONDITIONS','method_execution_started':False}
    if 'receipt' in value:
        receipt=value['receipt'];summary={'receipt':receipt.get('id'),'action':receipt.get('action'),'snapshot':receipt.get('snapshot')}
        if receipt.get('kind') in ('method_result','joined_result'):
            summary.update(job=value.get('job',receipt['id']),method=receipt.get('method'),
                execution_started=True,execution_completed=True,applicability=value.get('state'))
            summary['snapshot']={k:v for k,v in receipt.get('snapshot',{}).items() if k in ('state','peak','capacity','fits','assumptions')}
            if receipt['kind']=='method_result':
                summary.update(receipt=receipt['receipt'],method_result=receipt['id'],execution_scope='EXACT_SCHEDULE_CHECK',application_outputs_created=False)
            else:
                summary.update(artifacts=receipt['artifacts'],process_outcome=receipt['process_outcome'],check_verdict=receipt['check_verdict'])
        return summary
    if value.get('kind')=='math_schedule_result':return {'receipt':value['id'],'snapshot':value['snapshot']}
    if 'observation' in value:
        body=value['observation'];return {'job':value.get('job'),'applicability':value.get('applicability'),'state':body['state'],
            'measurements':(body.get('parsed') or {}).get('measurements'),
            'execution':{k:body.get('execution',{}).get(k) for k in ('exit_code','trap','stdout','stderr')},
            'native_counts':body.get('native',{}).get('counts')}
    if value.get('kind') in ('lab_action','math_office_action') or value.get('schema')=='arc.tool-action/1':
        return {**{k:value.get(k) for k in ('id','kind','binding_digest','operation','copy','output_names','state')},
            'execution_started':False,'outputs_created':False,'authority':'PREPARED_DESCRIPTOR_NOT_EXECUTION_RESULT'}
    return {k:v for k,v in value.items() if k in ('id','state','sha256','text','bytes','content_digest','changes','reason','error','files')}


def classify(value,failed=False):
    if failed:return 'FAILURE'
    if value.get('state') in ('STALE','UNAVAILABLE'):return 'FAILURE'
    if value.get('kind')=='method_preview':
        return 'UNSUPPORTED_METHOD' if value.get('precondition_rejected') else 'OBSERVED' if value['state']=='SUPPORTED' else 'FAILURE'
    if value.get('schema')=='arc.tool-action/1' or value.get('kind') in ('lab_action','math_office_action'):return 'PREPARED'
    body=value.get('observation',value.get('receipt',{}).get('snapshot',value.get('snapshot',{})))
    status=body.get('state',value.get('state'))
    if status in ('EXECUTION_FAILED','OUTPUT_INVALID','Failed','Cancelled','Interrupted','UNKNOWN','UNSUPPORTED','UNAVAILABLE'):return 'FAILURE'
    if status in ('INFEASIBLE','VIOLATIONS','CONFLICT','REFUTED'):return 'ADVERSE'
    return 'OBSERVED'


def producer_readiness(catalogue,observations):
    """Advertise only IDs actually produced by this work, without choosing a call."""
    produced=[o['result'] for o in observations]
    action_kinds={'math.joined':('joined_action',None),'math.method':('method_action',None),
        'math.office':('math_office_action',None),'lab.python':('lab_action','PYTHON'),'lab.board':('lab_action','BOARD')}
    for row in catalogue:
        op=row['operation'];spec=row['arguments']['properties']
        if op in contract.JOBS:
            kind,operation=action_kinds[contract.JOBS[op]]
            used={o.get('arguments',{}).get('action') or o['result'].get('receipt',{}).get('action')
                for o in observations if o['operation']==op and isinstance(o['result'].get('receipt',{}),dict)}
            actions=[v for v in produced if v.get('kind')==kind and v.get('binding_digest') and v['id'] not in used and (operation is None or v.get('operation')==operation)]
            row['available_now']=bool(row.get('available_now',True) and actions)
            if actions:
                spec['action']={'type':'string','enum':[v['id'] for v in actions]}
                spec['expected_digest']={'type':'string','enum':[v['binding_digest'] for v in actions]}
            else:row['missing_dependencies']=['No unexecuted matching owned action remains. Prepare a new allowed action or continue from the actual completed result.']
        if op.endswith('.result'):
            run=op[:-7]+'.run'
            jobs=[o['result'].get('job',o['result'].get('id')) for o in observations if o['operation']==run]
            read_jobs={o.get('arguments',{}).get('job') for o in observations if o['operation']==op}
            jobs=[j for j in jobs if isinstance(j,str) and j not in read_jobs]
            row['available_now']=bool(row.get('available_now',True) and jobs)
            if jobs:spec['job']={'type':'string','enum':list(dict.fromkeys(jobs))}
            else:row['missing_dependencies']=['No matching owned job has been observed in this investigation.']
        if op=='joined.prepare':
            direct=[v['id'] for v in produced if v.get('kind')=='math_schedule_result']
            methods=[v for v in produced if isinstance(v.get('receipt'),dict) and v['receipt'].get('kind')=='method_result']
            receipts=direct+[v['receipt']['receipt'] for v in methods]
            row['available_now']=bool(row.get('available_now',True) and receipts)
            if receipts:
                spec['receipt']={'type':'string','enum':list(dict.fromkeys(receipts))}
                if methods:
                    spec['method_job']={'type':'string','enum':list(dict.fromkeys(v.get('job',v['receipt']['id']) for v in methods))}
                    if not direct:row['arguments']['required']=list(dict.fromkeys([*row['arguments']['required'],'method_job']))
            else:row['missing_dependencies']=row.get('missing_dependencies',[])+['Keep a current schedule or executed checked-method result in this investigation first.']
    return catalogue


def completion_evidence(kernel,plan,state,p):
    if plan['adaptive'].get('completion')!=contract.APPLICATION_COMPLETION:return None
    from . import joined_work,checked_methods
    eligible=[];kinds=[]
    for index,ident in enumerate(state['observations']):
        row=observation(kernel,ident,p)
        if row['context_digest']!=state['problem']['expected_context_digest']:continue
        value=row['result'];alias='O'+str(index+1)
        try:
            if row['operation'] in ('joined.run','joined.result') and value.get('receipt',{}).get('kind')=='joined_result':
                live=joined_work.result(kernel,value['job'],p)
                types={ref['type'] for ref in live.get('receipt',{}).get('artifacts',[])}
                if live['state']=='AVAILABLE' and set(contract.APPLICATION_TYPES)<=types:
                    eligible.append(alias);kinds.append('CURRENT_CHECKED_APPLICATION_CHAIN')
            elif row['operation']=='methods.preview' and value.get('precondition_rejected'):
                live=checked_methods.dispatch(kernel,'methods.preview',row['arguments'],p)
                if live.get('precondition_rejected') and records.digest(live)==records.digest(value):
                    eligible.append(alias);kinds.append('CURRENT_UNSUPPORTED_METHOD_PRECONDITION')
        except (ValueError,OSError,KeyError):continue
    return {'required_artifacts':list(contract.APPLICATION_TYPES),'satisfied':bool(eligible),
        'finish_observations':eligible,'basis':list(dict.fromkeys(kinds)),
        'notice':'Finish requires a current checked application chain, or a current tool-verified unsupported method precondition. Preparation and a mathematical result alone do not satisfy this owner-selected scope.'}


def frame(kernel,plan,state,p,problem):
    obs=[];produced=[]
    for n,ident in enumerate(state['observations']):
        row=observation(kernel,ident,p)
        if row['context_digest']==problem['context_digest']:produced.append({'operation':row['operation'],'arguments':row['arguments'],'result':row['result']})
        obs.append({'alias':'O'+str(n+1),'receipt':ident,'operation':row['operation'],'outcome':row['outcome'],'tested_branch':row.get('candidate'),
            'arguments':{k:v for k,v in row['arguments'].items() if k not in ('id','expected_revision','expected_context_digest')},
            'problem_revision':row['problem_revision'],'current_context':row['context_digest']==problem['context_digest'],
            'result_digest':row['result_digest'],'actual':row['summary'],'authority':'ACTUAL_COORDINATOR_OBSERVATION_NOT_MODEL_PREDICTION'})
    cat=contract.catalogue(plan,problem)
    accepted_methods=[]
    if any(op in plan['operations'] for op in ('methods.instantiate','methods.preview')):
        from . import checked_methods
        candidates=checked_methods.dispatch(kernel,'methods.list',{},p)['methods']
        for method in candidates:
            if method['state']!='ACCEPTED':continue
            try:checked_methods.require_accepted(kernel,checked_methods.reference(method),p)
            except (ValueError,OSError):continue
            accepted_methods.append({k:method[k] for k in ('id','revision','title','profile','typed_inputs','preconditions')})
            if len(accepted_methods)==4:break
        for row in cat:
            if row['operation'] in ('methods.instantiate','methods.preview'):
                row['available_now']=bool(accepted_methods) and any(v['type']=='quantity' and v['state']=='KNOWN' for v in problem['variables']) and any(v['type']=='interval' and v['state']=='KNOWN' for v in problem['variables'])
                if accepted_methods:row['arguments']['properties']['method']={'type':'string','enum':[m['id'] for m in accepted_methods]}
                else:row['missing_dependencies']=['No current owner-accepted checked method is available.']
    if 'joined.prepare' in plan['operations']:
        from . import office_math_runtime,experiment_runtime,lab_service
        installed=office_math_runtime.probe()['available'] and experiment_runtime.status()['available']
        qualified=bool(installed and lab_service.qualification(kernel,p)['qualified'])
        for row in cat:
            if row['operation']=='joined.prepare':
                row.update(installed=installed,qualified=qualified,available_now=qualified)
                if not qualified:row['missing_dependencies']=['Native Office and the protected Python profile must be installed and qualified.']
    cat=producer_readiness(cat,produced)
    files={copy:list(state['copies'][copy]['files'])[:100] for copy in plan['copies']}
    value={'profile':contract.PROFILE,'binding':binding(plan,state),'problem':problem,'frontier':state['frontier'],
        'observations':obs[-24:],'catalogue':cat,'working_files':files,'limits':plan['adaptive']['limits'],
        'used':state['used'],'remaining_steps':plan['budget']['steps']-state['used']['steps'],
        'notice':'Past-revision observations are historical. Proposed branches and explanations are not evidence or grants.'}
    if any(op in plan['operations'] for op in ('methods.instantiate','methods.preview')):value['accepted_methods']=accepted_methods
    value['finish_policy']='Direct response permitted when no experiment is needed.' if plan['adaptive']['allow_direct'] else 'Owner requires an actual observed finding; do not finish without cited real observations.'
    value['finish_observations']=[r['alias'] for r in value['observations'] if r['current_context'] and r['outcome'] in ('OBSERVED','ADVERSE')]
    completion=completion_evidence(kernel,plan,state,p)
    if completion is not None:
        value['completion']=completion;value['finish_observations']=completion['finish_observations']
        value['finish_policy']=completion['notice']
    value['active_frontier']=[b['key'] for b in state['frontier'] if not b.get('historical') and b['status']!='REJECTED_FOR_RECORDED_CASE']
    interpreted=set()
    with kernel.db() as db:
        for ident in state['decisions']:
            prior=records.read(db,'adaptive_decision',ident,p)
            interpreted.update((update['candidate'],alias) for update in prior['candidate']['updates'] for alias in update['observations'])
    value['pending_adverse']=[o['alias'] for o in value['observations'] if o['outcome']=='ADVERSE' and (o.get('tested_branch'),o['alias']) not in interpreted]
    value['adverse_targets']={o['alias']:o['tested_branch'] for o in value['observations'] if o['alias'] in value['pending_adverse'] and o.get('tested_branch') in {b['key'] for b in state['frontier']}}
    value['response_schema']=contract.response_schema(cat,[r['alias'] for r in value['observations']],[r['key'] for r in state['frontier']],
        [v['name'] for v in problem['variables'] if v['state']=='UNKNOWN'],plan['adaptive']['limits']['frontier'],plan['adaptive']['allow_direct'],value['finish_observations'],value['active_frontier'],value['pending_adverse'],value['adverse_targets'])
    if len(records.canonical(value).encode())>131072:raise ValueError('ACTION_FRAME_LIMIT')
    return value


def bounded_principal(p,operation,plan):
    from .engineering_kernel import Principal,CAPABILITIES
    tools=('brain.action',) if operation=='slate.action' else (contract.JOBS[operation],) if operation in contract.JOBS else ()
    return Principal(p.identity,frozenset({'read',CAPABILITIES.get(operation,'execute')}),p.paths,tools,p.mode)


def validate_call(kernel,plan,state,choice,p):
    validate=contract.validate_schema
    from .engineering_cli import schemas
    op=choice['operation']
    if op not in plan['operations']:raise ValueError('ADAPTIVE_OPERATION_OUTSIDE_GRANT')
    if choice.get('candidate')!='recovery' and not any(b['key']==choice.get('candidate') and not b.get('historical') and b['status']!='REJECTED_FOR_RECORDED_CASE' for b in state['frontier']):raise ValueError('ADAPTIVE_SELECTED_BRANCH_NO_LONGER_ACTIVE')
    problem=foundations(kernel,plan,state,p);row=next(r for r in contract.catalogue(plan,problem) if r['operation']==op)
    if not row.get('available_now',True):raise ValueError('ADAPTIVE_TOOL_WAITING_FOR_DECLARED_INPUTS')
    validate(choice['arguments'],row['arguments']);args={**choice['arguments'],**row['fixed_arguments']};validate(args,schemas()[op])
    if args.get('copy') is not None and args['copy'] not in plan['copies']:raise ValueError('ADAPTIVE_COPY_OUTSIDE_GRANT')
    previous=[observation(kernel,i,p)['result'] for i in state['observations']]
    if op=='changes.apply':
        proposal=flow.validate_call(kernel,plan,{'operation':op},args,{str(n):v for n,v in enumerate(previous)},p)
    else:proposal=None
    if op in contract.JOBS:
        # Only a prepared action actually produced by this order is launchable.
        actions={v.get('id'):v for v in previous if isinstance(v,dict) and v.get('binding_digest')}
        prepared=actions.get(args['action'])
        if not prepared or prepared['binding_digest']!=args['expected_digest']:raise ValueError('ADAPTIVE_ACTION_NOT_PRODUCED_BY_THIS_WORK')
        if prepared.get('copy') not in plan['copies']:raise ValueError('ADAPTIVE_ACTION_COPY_OUTSIDE_GRANT')
    if op in ('experiments.result','boards.result','math.office.result','joined.result','methods.result'):
        jobs={v.get('job',v.get('id')) for v in previous if isinstance(v,dict)}
        if args['job'] not in jobs:raise ValueError('ADAPTIVE_JOB_OUTSIDE_GRANT')
    if op=='math.office.prepare':
        receipts={v.get('receipt',{}).get('id') for v in previous}
        if args['receipt'] not in receipts:raise ValueError('ADAPTIVE_CALCULATION_OUTSIDE_GRANT')
    if op=='joined.prepare':
        receipts={v['id'] for v in previous if v.get('kind')=='math_schedule_result'}
        methods={v['receipt']['receipt']:v for v in previous if isinstance(v.get('receipt'),dict) and v['receipt'].get('kind')=='method_result'}
        receipts.update(methods)
        if args['receipt'] not in receipts:raise ValueError('ADAPTIVE_SCHEDULE_OUTSIDE_GRANT')
        applied=methods.get(args['receipt'])
        if applied and args.get('method_job')!=applied.get('job',applied['receipt']['id']):
            raise ValueError('ADAPTIVE_METHOD_PRODUCER_BINDING_REQUIRED')
        if args.get('method_job') and not applied:raise ValueError('ADAPTIVE_METHOD_RESULT_OUTSIDE_GRANT')
    if op=='math.calculate':
        import ast
        names={v['name'] for v in problem['variables'] if v['type']=='quantity'}
        try:tree=ast.parse(args['expression'],mode='eval')
        except SyntaxError as exc:raise ValueError('Invalid expression syntax') from exc
        used={n.id for n in ast.walk(tree) if isinstance(n,ast.Name)}
        if not used&names:raise ValueError('Use saved quantity VARIABLE NAMES to preserve units and source bindings, not numeric copies.')
    return args,proposal


def pending_key(current):
    if current.get('request'):return 'slate-action:'+current['request']
    prefix='math-office:' if contract.JOBS.get(current.get('operation')) in ('math.office','math.joined','math.method') else 'lab:'
    return prefix+str(current.get('arguments',{}).get('action',''))


def stop_pending(kernel,plan,state,p):
    current=state.get('current') or {};ident=current.get('job')
    if not ident and current:
        key=pending_key(current)
        with kernel.db() as db:row=db.execute('SELECT job FROM requests WHERE owner=? AND key=?',(p.identity,key)).fetchone()
        ident=row[0] if row else None
    if not ident:return
    try:
        job=kernel.record('jobs',ident)
        if job['owner']==p.identity and job['state'] in ('Queued','Running'):
            records.result_of(kernel,'jobs.cancel',{'id':ident},bounded_principal(p,'jobs.cancel',plan))
    except (ValueError,KeyError):pass


def check_current(kernel,plan,state,p,db=None,expected_key=None):
    if db is None:
        with kernel.db() as db:return check_current(kernel,plan,state,p,db,expected_key)
    _,live=flow.load(db,plan['id'],p);gate(kernel,plan,live,p,db)
    key=expected_key or (state.get('current') or {}).get('key')
    if live['state'] not in ('READY','RUNNING') or (live.get('current') or {}).get('key')!=key:
        raise ValueError('ADAPTIVE_PROGRESS_REVOKED_OR_CHANGED')


def persist_observation(kernel,plan,state,item,value,p,failed=False):
    ident=uuid.uuid5(uuid.NAMESPACE_URL,'work-observation:'+plan['id']+':'+item['key']).hex
    row=records.new('adaptive_observation',p,id=ident,work=plan['id'],step=item['key'],problem=state['problem']['id'],
        problem_revision=state['problem']['expected_revision'],context_digest=state['problem']['expected_context_digest'],
        operation=item['operation'],arguments=item['arguments'],result=value,result_digest=records.digest(value),
        summary=summarize(value),outcome=classify(value,failed),model_self_attestation=False,physical_qualification=False)
    row['candidate']=item.get('candidate',(state.get('current') or {}).get('candidate'))
    with kernel.db() as db:
        check_current(kernel,plan,state,p,db)
        prior=db.execute('SELECT 1 FROM desk_records WHERE id=?',(ident,)).fetchone()
        if not prior:records.write(db,row,p,'ACTUAL_ADAPTIVE_TOOL_OBSERVED')
        else:row=records.read(db,'adaptive_observation',ident,p)
    return row


def finish_item(kernel,plan,state,item,value,p,failed=False):
    check_current(kernel,plan,state,p)
    key=state['current']['key']
    row=persist_observation(kernel,plan,state,item,value,p,failed)
    size=len(records.canonical(row).encode())
    if state['used']['output_bytes']+size>plan['budget']['output_bytes']:raise ValueError('BUDGET_OUTPUT_BYTES')
    state['used']['output_bytes']+=size
    state['observations'].append(row['id']);state['current']=None
    if row['outcome']=='FAILURE':state['failures']+=1
    item.update(state='DONE',result=value,result_digest=records.digest(value),observation=row['id'],finished=time.time())
    state.update(state='LIMIT' if state['failures']>=plan['adaptive']['limits']['failures'] else 'READY',reason='FAILURE_LIMIT' if state['failures']>=plan['adaptive']['limits']['failures'] else None)
    with kernel.db() as db:
        check_current(kernel,plan,state,p,db,key)
        flow.step_save(db,plan['id'],item);flow.save(db,plan,state,'ACTUAL_OBSERVATION_CONSUMED',{'step':item['key'],'outcome':row['outcome'],'receipt':row['id']})


def apply_decision(kernel,plan,state,value,p):
    check_current(kernel,plan,state,p)
    key=state['current']['key']
    candidate=value['candidate'];frame_value=value['frame_digest']
    if candidate['next']['kind']=='FINISH':
        completion=completion_evidence(kernel,plan,state,p)
        if completion is not None and (not completion['satisfied'] or not set(candidate['next']['observations'])&set(completion['finish_observations'])):
            raise ValueError('ADAPTIVE_REQUIRED_COMPLETION_EVIDENCE_MISSING_OR_STALE')
    for alternative in candidate['alternatives']:
        state['frontier'].append({**alternative,'status':'PROPOSED','origin':'MODEL_PROPOSAL','problem_revision':state['problem']['expected_revision'],'context_digest':state['problem']['expected_context_digest']})
    for update in candidate['updates']:
        branch=next(b for b in state['frontier'] if b['key']==update['candidate'])
        branch.update(status={'REJECT':'REJECTED_FOR_RECORDED_CASE','REFINE':'REFINED_PROPOSAL','RETAIN':'PROPOSED'}[update['disposition']],
            reason=update['reason'],observations=update['observations'],decision=value['id'])
    state['decisions'].append(value['id']);choice=candidate['next'];state['current']=None
    if choice['kind']=='ASK':
        state.update(state='WAITING',reason='MISSING_INPUT',question={'id':value['id'],'text':choice['question'],'missing':choice['missing'],
            'uncertainty':candidate['uncertainty'],'expected':candidate['expected'],'problem':state['problem']})
    elif choice['kind']=='FINISH':state.update(state='REVIEW',reason='MODEL_PROPOSED_FINDING',finding={'text':choice['text'],'observations':choice['observations'],'decision':value['id'],'review':'UNREVIEWED_MODEL_INTERPRETATION'})
    else:state.update(state='READY',reason='VALIDATED_NEXT_ACTION',choice=choice,last_rationale={'text':candidate['text'],'uncertainty':candidate['uncertainty'],'expected':candidate['expected'],'decision':value['id']})
    with kernel.db() as db:
        check_current(kernel,plan,state,p,db,key)
        flow.save(db,plan,state,'MODEL_DECISION_CONSUMED',{'decision':value['id'],'next':choice['kind'],'frame_digest':frame_value})


def consume_pending(kernel,plan,state,p):
    current=state['current'];job=kernel.record('jobs',current['job'])
    if job['state'] in ('Queued','Running'):return {'ran':plan['id'],'state':'READY','waiting_for_job':job['id']}
    with kernel.db() as db:item=flow.step_row(db,plan['id'],current['key'])
    foundations(kernel,plan,state,p)
    if current['phase']=='DECISION':
        result=slate_action.result(kernel,job['id'],p)
        if job['state']!='Completed':
            item.update(state='FAILED',reason=result.get('error'));state['current']=None;state['failures']+=1
            state.update(state='WAITING',reason='MODEL_DECISION_FAILED: '+str(result.get('error')))
            with kernel.db() as db:
                check_current(kernel,plan,state,p,db,current['key'])
                flow.step_save(db,plan['id'],item);flow.save(db,plan,state,'MODEL_RESPONSE_REJECTED')
            return {'ran':plan['id'],'state':state['state'],'reason':state['reason']}
        value=result['result']
        if value['request']!=current['request'] or value['turn']!=current['key']:raise ValueError('ACTION_RECEIPT_TURN_MISMATCH')
        item.update(state='DONE',result=value,result_digest=records.digest(value),finished=time.time())
        metrics=value['metrics'];charged=metrics['prompt_tokens_measured']+metrics['usage'].get('completion_tokens',plan['adaptive']['limits']['max_tokens'])
        state['used']['tokens']-=max(0,current['reserved_tokens']-charged)
        state['used']['seconds']-=max(0,current['reserved_seconds']-min(current['reserved_seconds'],metrics['elapsed_seconds']))
        with kernel.db() as db:flow.step_save(db,plan['id'],item)
        apply_decision(kernel,plan,state,value,p)
    else:
        op=current['operation']
        if job['state']=='Completed':
            endpoint={'lab.python':'experiments.result','lab.board':'boards.result','math.office':'math.office.result','math.joined':'joined.result','math.method':'methods.result'}[job['tool']]
            result=records.result_of(kernel,endpoint,{'job':job['id']},bounded_principal(p,endpoint,plan));failed=False
        else:result={'job':job['id'],'state':job['state'],'error':job.get('error')};failed=True
        state['used']['seconds']-=max(0,current['reserved_seconds']-min(current['reserved_seconds'],time.time()-current['started']))
        finish_item(kernel,plan,state,item,result,p,failed)
    return {'ran':plan['id'],'state':state['state']}


def advance(kernel,ident,p):
    plan,state=read(kernel,ident,p)
    if state['state']!='READY':return {'ran':None,'state':state['state'],'reason':state.get('reason')}
    ready_digest=records.digest(state)
    try:
        gate(kernel,plan,state,p);problem=foundations(kernel,plan,state,p)
        if state.get('current',{}):return consume_pending(kernel,plan,state,p)
        if state['used']['steps']>=plan['budget']['steps']:raise ValueError('BUDGET_STEPS')
        if state['failures']>=plan['adaptive']['limits']['failures']:raise ValueError('BUDGET_FAILURES')
        decision=state.get('choice') is None
        if decision and len(state['decisions'])>=plan['adaptive']['limits']['decisions']:raise ValueError('BUDGET_DECISIONS')
        if decision and not any(not b.get('historical') and b['status']!='REJECTED_FOR_RECORDED_CASE' for b in state['frontier']):raise ValueError('FRONTIER_EXHAUSTED')
        key='Step'+str(len(state['steps'])+1);phase='DECISION' if decision else 'ACTION'
        choice=state.get('choice');proposal=None;fingerprint=None
        if decision:op='slate.action';args={};seconds=plan['adaptive']['limits']['decision_seconds'];tokens=2*plan['adaptive']['model']['config']['context']
        else:
            op=choice['operation'];args,proposal=validate_call(kernel,plan,state,choice,p);seconds={'experiments.run':30,'boards.run':180,'math.office.run':220,'joined.run':220}.get(op,30);tokens=0
            fingerprint=records.digest({'operation':op,'arguments':args,'binding':binding(plan,state)})
            if fingerprint in state['seen']:raise ValueError('DUPLICATE_ACTION_ON_UNCHANGED_INPUTS')
        if state['used']['seconds']+seconds>plan['budget']['seconds']:raise ValueError('BUDGET_SECONDS')
        if state['used']['tokens']+tokens>plan['budget']['tokens']:raise ValueError('BUDGET_TOKENS')
        if proposal:
            files=sorted(set(state['used']['files'])|{proposal['copy']+':'+c['path'] for c in proposal['changes']})
            if len(files)>plan['budget']['files']:raise ValueError('BUDGET_FILES')
            state['used']['files']=files
        current={'key':key,'phase':phase,'operation':op,'arguments':args,'started':time.time(),'reserved_seconds':seconds,'reserved_tokens':tokens}
        item={'key':key,'operation':op,'arguments':args,'state':'RUNNING','attempts':1,'started':time.time(),
              'require':[],'proposal_id':uuid.uuid5(uuid.NAMESPACE_URL,ident+':'+key).hex}
        if not decision:current['candidate']=choice['candidate'];item['candidate']=choice['candidate']
        state['used']['steps']+=1;state['used']['seconds']+=seconds;state['used']['tokens']+=tokens
        state['steps'].append(key);state.update(state='RUNNING',current=current)
        if not decision:state.pop('choice',None);state['seen'].append(fingerprint)
        if decision:
            request=slate_action.prepare(kernel,plan,state,p,frame(kernel,plan,state,p,problem));current['request']=request['id']
        with kernel.db() as db:
            _,live=flow.load(db,ident,p);gate(kernel,plan,live,p,db)
            if records.digest(live)!=ready_digest:raise ValueError('ADAPTIVE_WORK_CHANGED_BEFORE_INTENT')
            flow.step_save(db,ident,item);flow.save(db,plan,state,'ADAPTIVE_INTENT',{'step':key,'operation':op})
        flow.fault('INTENT')
        def check(db=None):
            flow.guard(kernel,ident,p,state['epoch'],db)
            if time.time()-current['started']>seconds:raise ValueError('ADAPTIVE_STEP_TIME_LIMIT')
        scope={'work':ident,'step':key,'proposal':item['proposal_id'],'guard':check,'seconds':seconds,
               'memory_mb':plan['budget']['memory_mb'],'output_bytes':min(1048576,plan['budget']['output_bytes']-state['used']['output_bytes'])}
        bounded=bounded_principal(p,op,plan)
        effect_failed=False
        with work_scope.entered(scope):
            check()
            if decision:value=slate_action.submit(kernel,bounded,request)
            else:
                cached=flow.proposal_cache(kernel,item['proposal_id'],p) if op=='changes.propose' else None
                try:value=cached or records.result_of(kernel,op,args,bounded)
                except (ValueError,OSError) as exc:value={'state':'TOOL_ERROR','reason':str(exc)[:1000]};effect_failed=True
        flow.fault('EFFECT')
        check_current(kernel,plan,state,p)
        if effect_failed:
            state['used']['seconds']-=max(0,seconds-min(seconds,time.time()-current['started']))
            finish_item(kernel,plan,state,item,value,p,True)
            return {'ran':ident,'state':state['state'],'tool_outcome':'FAILURE'}
        if decision or op in contract.JOBS:
            current['job']=value['id'];state.update(state='READY',reason='AWAITING_ACTUAL_MODEL_RESULT' if decision else 'AWAITING_ACTUAL_TOOL_RESULT')
            with kernel.db() as db:
                check_current(kernel,plan,state,p,db,key)
                flow.save(db,plan,state,'OWNED_JOB_BOUND',{'step':key,'job':value['id']})
        else:
            expected=flow.expected_after(plan,state,proposal) if proposal else state['copies']
            if flow.signatures(kernel,plan['copies'],p)!=expected:raise ValueError('WORKING_COPY_CHANGED_DURING_ACTION')
            if proposal:state['source_successors']=flow.source_successors(plan,state,proposal,value)
            state['copies']=expected;foundations(kernel,plan,state,p)
            state['used']['seconds']-=max(0,seconds-min(seconds,time.time()-current['started']))
            finish_item(kernel,plan,state,item,value,p)
        return {'ran':ident,'state':state['state'],'operation':op}
    except (ValueError,OSError,KeyError,TypeError) as exc:
        reason=str(exc)[:500]
        with kernel.db() as db:
            _,live=flow.load(db,ident,p)
            if live['state'] in ('PAUSED','REVOKED'):return {'ran':ident,'state':live['state'],'reason':live.get('reason')}
            live.update(state='LIMIT' if reason.startswith('BUDGET_') else 'WAITING',reason=reason)
            flow.save(db,plan,live,'ADAPTIVE_STOPPED',{'reason':reason})
        stop_pending(kernel,plan,live,p)
        return {'ran':ident,'state':live['state'],'reason':reason}


def resume(kernel,ident,p):
    work_trail.accepting(kernel)
    with flow.agenda_lock(kernel):
        plan,state=read(kernel,ident,p)
        expected_checkpoint=records.digest(state)
        def checkpoint(db):
            _,live=flow.load(db,ident,p);flow.grant(db,plan)
            status=work_trail.work_status(kernel,db)
            if status['held']:raise ValueError('WORK_HELD')
            if records.digest(live)!=expected_checkpoint:raise ValueError('WORK_CHANGED_DURING_EXPLICIT_RESUME')
            return status['epoch']
        with kernel.db() as db:flow.grant(db,plan)
        if state['state'] not in ('PAUSED','WAITING'):raise ValueError('Adaptive work is not resumable in this state')
        if state.get('question'):raise ValueError('Answer the discriminating question before resuming')
        current=state.get('current');recovered=None
        if current and not current.get('job'):
            with kernel.db() as db:item=flow.step_row(db,ident,current['key'])
            if current['operation']=='changes.apply':
                if flow.reconcile_apply(kernel,plan,state,item,p,checkpoint=checkpoint):
                    expected_checkpoint=records.digest(state)
                    with kernel.db() as db:recovered=flow.step_row(db,ident,current['key'])['result']
                else:
                    state['choice']={'kind':'CALL','candidate':current.get('candidate','recovery'),'operation':current['operation'],'arguments':current['arguments']}
                    state['seen']=state['seen'][:-1]
            elif current['operation'] in contract.JOBS or current['operation']=='slate.action':
                # A crash may follow submission but precede saving its job ID.
                key=pending_key(current)
                if key:
                    with kernel.db() as db:row=db.execute('SELECT job FROM requests WHERE owner=? AND key=?',(p.identity,key)).fetchone()
                    if row:current['job']=row[0]
                if not current.get('job'):
                    item.update(state='INTERRUPTED',reason='No durable job acceptance; explicit resumption permits a fresh decision.')
                    with kernel.db() as db:flow.step_save(db,ident,item)
                    state['current']=None
            else:
                # Read/calculation may retry only explicitly; proposal creation
                # uses its stable work/step identity to reconcile retained drafts.
                if current['operation']=='changes.propose':
                    cached=flow.proposal_cache(kernel,item['proposal_id'],p)
                    if cached:recovered=cached
                if state.get('current') and recovered is None:
                    problem=check_problem(kernel,plan,state,p)
                    fixed=next(r['fixed_arguments'] for r in contract.catalogue(plan,problem) if r['operation']==current['operation'])
                    state['choice']={'kind':'CALL','candidate':current.get('candidate','recovery'),'operation':current['operation'],'arguments':{k:v for k,v in current['arguments'].items() if k not in fixed}}
                    state['seen']=state['seen'][:-1];state['current']=None
            if current['operation']=='changes.apply' and recovered is None:state['current']=None
        if state.get('current') and state['current'].get('job'):
            job=kernel.record('jobs',state['current']['job'])
            if job['state'] in ('Cancelled','Failed','Interrupted'):
                state['current']=None;state['failures']+=1
        foundations(kernel,plan,state,p)
        if recovered is not None:
            with kernel.db() as db:
                state.update(state='RUNNING',epoch=checkpoint(db));flow.save(db,plan,state,'EXPLICIT_RECONCILIATION')
            finish_item(kernel,plan,state,item,recovered,p)
            expected_checkpoint=records.digest(state)
        with kernel.db() as db:
            state.update(state='READY',reason='EXPLICIT_RESUME',epoch=checkpoint(db));flow.save(db,plan,state,'EXPLICIT_ADAPTIVE_RESUME')
    return flow.get(kernel,ident,p)


def answer(kernel,args,p):
    validate=contract.validate_schema
    from .schedule_math import INTERVAL
    with flow.agenda_lock(kernel):
        plan,state=read(kernel,args['id'],p);question=state.get('question')
        if state['state']!='WAITING' or not question or question['id']!=args['question']:raise ValueError('No matching pending owner question')
        if args['expected_revision']!=state['problem']['expected_revision'] or args['expected_context_digest']!=state['problem']['expected_context_digest']:raise ValueError('OWNER_ANSWER_PROBLEM_REVISION_CHANGED')
        problem=foundations(kernel,plan,state,p)
        if set(args['lifetimes'])!=set(question['missing']):raise ValueError('Supply exactly the requested lifetime variables')
        variables=json.loads(records.canonical(problem['variables']))
        for name,value in args['lifetimes'].items():
            validate(value,INTERVAL);variable=next(v for v in variables if v['name']==name)
            if variable['type']!='interval' or variable['state']!='UNKNOWN':raise ValueError('Owner answer supports declared unknown lifetimes only')
            from .schedule_math import evaluate
            variable.update(state='KNOWN',value=records.canonical(value),basis='Owner supplied for adaptive question '+question['id']+': '+args['note'])
        # Validate interval values even before the next model chooses a schedule.
        from . import math_units as units
        for value in args['lifetimes'].values():
            d,f=units.unit_spec(value['unit']);a=units.rational(value['start']);b=units.rational(value['stop'])
            if d!=units.DIMENSIONS['time'] or a<0 or b<=a:raise ValueError('Invalid half-open owner lifetime')
        if len(state['frontier'])>=plan['adaptive']['limits']['frontier']:raise ValueError('FRONTIER_LIMIT_BEFORE_OWNER_REVISION')
        # Problem history and the work checkpoint share one Kernel transaction.
        # An interrupted owner answer cannot leave a new problem revision with
        # an old investigation cursor, and a concurrent revoke cannot be lost.
        validated=problems.content(kernel,{'variables':variables},p)['variables']
        with kernel.db() as db:
            db.execute('BEGIN IMMEDIATE');live_plan,live_state=flow.load(db,plan['id'],p)
            if live_state!=state:raise ValueError('OWNER_QUESTION_CHANGED_DURING_ANSWER')
            flow.grant(db,plan)
            if work_trail.work_status(kernel,db)['held']:raise ValueError('WORK_HELD')
            revised=problems.load(db,state['problem']['id'],p);problems.check_bound(revised,state['problem'])
            expected=revised['revision'];records.edit(revised,expected);revised['variables']=validated
            revised['context_digest']=problems.context_digest(revised)
            records.write(db,revised,p,'OWNER_LIFETIMES_REVISED',expected=expected)
            state['problem']={'id':revised['id'],'expected_revision':revised['revision'],'expected_context_digest':revised['context_digest']}
            for branch in state['frontier']:branch['historical']=True
            state['frontier'].append({'key':'owner'+str(revised['revision']),'hypothesis':'Evaluate the explicitly supplied owner lifetimes.',
                'assumptions':[],'status':'PROPOSED','origin':'OWNER_ANSWER','problem_revision':revised['revision'],'context_digest':revised['context_digest']})
            state['question']=None;state.update(state='READY',reason='OWNER_INPUT_SUPPLIED')
            flow.save(db,plan,state,'OWNER_LIFETIMES_BOUND',{'question':question['id'],'revision':revised['revision'],'note':args['note']})
    return flow.get(kernel,plan['id'],p)


def dispatch(kernel,op,args,p):
    if op=='work.investigate':return create(kernel,args,p)
    if op=='work.answer':return answer(kernel,args,p)
    if op=='slate.action':raise ValueError('ACTION_INFERENCE_IS_STARTED_ONLY_BY_THE_GRANTED_EXECUTOR')
    if op=='slate.action.result':return slate_action.result(kernel,args['job'],p)
    plan,state=read(kernel,args['id'],p)
    if op=='work.frontier':return {'problem':state['problem'],'frontier':state['frontier'],'question':state.get('question'),'finding':state.get('finding'),'state':state['state'],'reason':state.get('reason')}
    if op=='work.investigation':
        value=flow.get(kernel,args['id'],p);value['observations']=[observation(kernel,i,p) for i in state['observations']]
        with kernel.db() as db:value['decisions']=[records.read(db,'adaptive_decision',i,p) for i in state['decisions']]
        return value
    raise ValueError('Unknown adaptive operation')
