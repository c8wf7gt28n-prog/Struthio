"""Authenticated local ACTION inference: complete, source-bound proposals only."""
import hashlib,json,time,uuid
from pathlib import Path
from . import project_desk as records,slate_context as contexts,adaptive_contract as contract
JOB_TOOLS=frozenset({'brain.action'})


def method_continuations(frame):
    """Reuse a current checked mapping as a proposal, never execution authority."""
    target=next((r for r in frame['catalogue'] if r['operation']=='methods.instantiate' and r.get('available_now',True)),None)
    if target is None:return []
    accepted={(m['id'],m['revision']) for m in frame.get('accepted_methods',[])}
    current=[o for o in frame['observations'] if o['current_context']]
    prepared={records.canonical(o['arguments']) for o in current if o['operation']=='methods.instantiate'}
    result=[];seen=set()
    for row in current:
        actual=row['actual'];args=row['arguments'];key=records.canonical(args)
        if row['operation']!='methods.preview' or row['outcome']!='OBSERVED':continue
        if not actual.get('check_completed') or actual.get('state')!='SUPPORTED':continue
        if (args.get('method'),args.get('method_revision')) not in accepted or key in prepared|seen:continue
        if actual.get('method_id')!=args.get('method') or actual.get('method_revision')!=args.get('method_revision'):continue
        try:contract.validate_schema(args,target['arguments'])
        except ValueError:continue
        result.append({'from_observation':row['alias'],'operation':'methods.instantiate',
            'arguments':json.loads(key),'authority':'PROPOSAL_ONLY_RECHECKS_INPUTS_AND_GRANT',
            'description':'These preconditions are already checked. Prepare this mapping next if applying it; an unchanged preview is a duplicate. Preparation does not execute the method or create application outputs.'})
        seen.add(key)
        if len(result)==4:break
    return result


def phase_view(frame,operation=None):
    """Keep full bindings in the request; show the model relevant decision data."""
    problem=frame['problem']
    view={'problem':{k:problem[k] for k in ('title','original_request','goals','variables','assumptions','questions','sources') if k in problem},
        'frontier':frame['frontier'],'active_frontier':frame['active_frontier'],'working_files':frame['working_files'],
        'actual_observations':[{k:o[k] for k in ('alias','operation','arguments','outcome','tested_branch','problem_revision','current_context','actual')} for o in frame['observations']],
        'remaining_steps':frame['remaining_steps'],'used':frame['used'],'limits':frame['limits'],
        'finish_policy':frame['finish_policy'],'current_finish_citations':frame['finish_observations']}
    view['adverse_observations_requiring_interpretation']=frame['pending_adverse']
    view['tested_branches_requiring_interpretation']=frame['adverse_targets']
    if 'accepted_methods' in frame:view['accepted_methods']=frame['accepted_methods']
    if 'completion' in frame:view['completion']=frame['completion']
    continuations=method_continuations(frame)
    if continuations:
        view['checked_method_continuations']=[{k:v for k,v in row.items() if k!='arguments' or operation==row['operation']} for row in continuations]
    if operation is None:
        view['tools']=[{k:r[k] for k in ('operation','description','available_now','missing_inputs','installed','qualified','missing_dependencies') if k in r} for r in frame['catalogue']]
        if continuations:
            for tool in view['tools']:
                if tool['operation']=='methods.preview':
                    tool['description']+=' Current supported mappings are already checked in '+', '.join(r['from_observation'] for r in continuations)+'. Reuse those checks; methods.instantiate prepares their mappings. Use preview again only for a different mapping or changed inputs.'
        unknowns=[v['name'] for v in problem['variables'] if v['state']=='UNKNOWN']
        view['control_actions']=[{'operation':'ASK','available_now':bool(unknowns),
            'description':'Pause for a consequential declared unknown needed to complete the owner request. Do not invent its value.'},
            {'operation':'FINISH','available_now':bool(frame['finish_observations']) or 'Direct response permitted' in frame['finish_policy'],
            'description':'Return the conditional finding supported by current actual receipts when the full owner request and requested follow-ups are resolved. Also answers direct requests that need no experiment. No further tool call is needed just to report an already checked result.'}]
    else:
        view['selected_operation']=operation
        view['tool']=next((r for r in frame['catalogue'] if r['operation']==operation),None)
    return view


def model_binding(kernel,p):
    from . import local_brain as brain,slate_reasoning
    worker=slate_reasoning.worker_ready(kernel)
    if worker.get('owner')!=p.identity:raise ValueError('ADAPTIVE_MODEL_OWNER')
    value=brain.model(kernel,worker['model_id']);config=worker['config']
    files={f['path']:{'bytes':f['bytes'],'sha256':f['sha256'],'stat':list((lambda s:(s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_ino))(Path(f['path']).stat()))} for f in value['files']}
    return {'model_id':worker['model_id'],'config':{**{k:config[k] for k in ('context','threads','memory_mb','backend')},'weight_loading':config.get('weight_loading','MMAPPED_LEGACY')},
        'runtime':worker['runtime'],'template_sha256':hashlib.sha256(value['message_template'].encode()).hexdigest(),
        'files':files,'thinking_enabled':False,'temperature':0,'profile':contract.PROFILE}


def validate(candidate,frame):
    schema_validate=contract.validate_schema
    schema_validate(candidate,frame['response_schema'])
    if set(candidate)!={'text','uncertainty','expected','alternatives','updates','next'}:raise ValueError('ACTION_COMPLETE_RESPONSE_REQUIRED')
    keys={c['key'] for c in frame['frontier']};new=set();aliases={r['alias']:r for r in frame['observations']}
    import re
    for branch in candidate['alternatives']:
        key=branch['key']
        if not re.fullmatch('[A-Za-z][A-Za-z0-9_]{0,39}',key) or key in keys|new:raise ValueError('ACTION_FRONTIER_KEY')
        new.add(key)
    if len(keys|new)>frame['limits']['frontier']:raise ValueError('ACTION_FRONTIER_LIMIT')
    if len({u['candidate'] for u in candidate['updates']})!=len(candidate['updates']):raise ValueError('ACTION_DUPLICATE_BRANCH_UPDATE')
    for update in candidate['updates']:
        if update['candidate'] not in keys:raise ValueError('ACTION_UNKNOWN_CANDIDATE')
        if any(alias not in aliases for alias in update['observations']):raise ValueError('ACTION_UNKNOWN_OBSERVATION')
        branch=next(b for b in frame['frontier'] if b['key']==update['candidate'])
        if update['disposition']=='REJECT' and not any(aliases[a]['outcome']=='ADVERSE' and aliases[a].get('problem_revision')==branch.get('problem_revision') for a in update['observations']):raise ValueError('TOOL_FAILURE_OR_PREDICTION_CANNOT_REFUTE_HYPOTHESIS')
    chosen=candidate['next']
    if chosen['kind']!='FINISH' and chosen['candidate'] not in keys|new:raise ValueError('ACTION_UNKNOWN_SELECTED_BRANCH')
    active={b['key'] for b in frame['frontier'] if not b.get('historical') and b.get('status')!='REJECTED_FOR_RECORDED_CASE'}
    active-={u['candidate'] for u in candidate['updates'] if u['disposition']=='REJECT'}
    if chosen['kind']!='FINISH' and chosen['candidate'] not in active|new:raise ValueError('ACTION_INACTIVE_SELECTED_BRANCH')
    interpreted={alias for update in candidate['updates'] for alias in update['observations']}
    if set(frame.get('pending_adverse',[]))-interpreted:raise ValueError('ACTION_ADVERSE_OBSERVATION_NEEDS_INTERPRETATION')
    for alias,key in frame.get('adverse_targets',{}).items():
        if not any(u['candidate']==key and alias in u['observations'] for u in candidate['updates']):raise ValueError('ACTION_TESTED_BRANCH_NEEDS_INTERPRETATION')
    if chosen['kind']=='ASK':
        unknown={v['name'] for v in frame['problem']['variables'] if v['state']=='UNKNOWN'}
        if not chosen['missing'] or len(set(chosen['missing']))!=len(chosen['missing']) or not set(chosen['missing'])<=unknown:raise ValueError('ACTION_ASK_REQUIRES_DECLARED_UNKNOWN')
    if chosen['kind']=='FINISH' and any(a not in aliases for a in chosen['observations']):raise ValueError('ACTION_FINISH_CITATIONS')
    if chosen['kind']=='CALL':
        if not candidate['expected']:raise ValueError('ACTION_DISCRIMINATING_EXPECTATION_REQUIRED')
        row=next((r for r in frame['catalogue'] if r['operation']==chosen['operation']),None)
        if row is None:raise ValueError('ACTION_OPERATION_OUTSIDE_SELECTED_CATALOGUE')
        schema_validate(chosen['arguments'],row['arguments'])
    return {'state':'ACTION_PROPOSAL_VALIDATED','authority':'DRAFT_NOT_GRANT_OR_EXECUTION','model_self_checked':False}


def live_request(kernel,request,p,sources=True):
    from . import adaptive_work as controller,continuing_work as flow
    with kernel.db() as db:
        plan,state=flow.load(db,request['work'],p);flow.grant(db,plan)
        gate=controller.gate(kernel,plan,state,p,db)
    current=state.get('current') or {}
    if state['state'] not in ('READY','RUNNING') or current.get('key')!=request['turn'] or current.get('request')!=request['id']:raise ValueError('ACTION_TURN_NO_LONGER_CURRENT')
    if request['frame']['binding']!=controller.binding(plan,state):raise ValueError('ACTION_SOURCE_CONTEXT_CHANGED')
    if sources:
        controller.foundations(kernel,plan,state,p)
        if request['model']!=model_binding(kernel,p):raise ValueError('ACTION_MODEL_CHANGED')
    return plan,state


def prepare(kernel,plan,state,p,frame):
    from . import slate_stream
    model=model_binding(kernel,p)
    if model!=plan['adaptive']['model']:raise ValueError('ADAPTIVE_MODEL_CHANGED')
    messages=[{'role':'system','content':contract.SYSTEM},{'role':'user','content':records.canonical(phase_view(frame))}]
    from .slate_reasoning import worker_ready
    prompt=slate_stream.prompt_size(worker_ready(kernel),messages)
    if prompt+plan['adaptive']['limits']['max_tokens']+32>model['config']['context']:raise ValueError('ACTION_CONTEXT_BUDGET_EXCEEDED')
    key=state['current']['key'];ident=uuid.uuid5(uuid.NAMESPACE_URL,'slate-action:'+plan['id']+':'+key).hex
    return {'schema':'ledger.action-request/1','id':ident,'tool':'brain.action','owner':p.identity,'created':time.time(),
        'work':plan['id'],'turn':key,'model':model,'frame':frame,'messages':messages,'prompt_tokens':prompt,
        'max_tokens':plan['adaptive']['limits']['max_tokens'],'seconds':plan['adaptive']['limits']['decision_seconds']}


def submit(kernel,p,request):
    from . import work_scope,local_brain as brain
    scope=work_scope.current()
    if not scope or scope.get('work')!=request['work']:raise ValueError('ACTION_REQUIRES_ACTIVE_GRANTED_WORK')
    with kernel.db() as db:
        prior=db.execute('SELECT 1 FROM slate_records WHERE id=? AND owner=? AND kind=?',(request['id'],p.identity,'request')).fetchone()
        if prior:
            old=contexts.load(db,p.identity,'request',request['id'])
            if old['frame']!=request['frame'] or old['model']!=request['model']:raise ValueError('ACTION_REPLAY_CONTEXT_CHANGED')
            request=old
        else:contexts.save(db,p.identity,'request',request)
    return brain.submit(kernel,'brain.action',{'request_key':'slate-action:'+request['id']},p,{'conversation':request['id']})


def authorize_job(kernel,tool,options,p):
    if tool not in JOB_TOOLS:return
    if set(options)!={'conversation'}:raise ValueError('ACTION_REQUIRES_FROZEN_REQUEST')
    with kernel.db() as db:request=contexts.load(db,p.identity,'request',options['conversation'])
    if request.get('tool')!=tool:raise ValueError('ACTION_TOOL_REQUEST_BINDING')
    live_request(kernel,request,p)


def run_job(kernel,job):
    from .engineering_kernel import Principal
    from . import slate_stream,slate_reasoning,local_brain as brain
    p=Principal(job['owner'],frozenset({'read','execute'}))
    with kernel.db() as db:request=contexts.load(db,p.identity,'request',job['request_spec']['brain']['conversation'])
    live_request(kernel,request,p);worker=slate_reasoning.worker_ready(kernel)
    def stopped():
        if brain.cancelled(kernel,job['id']):return True
        try:live_request(kernel,request,p,sources=False);return False
        except ValueError:return True
    began=time.monotonic();frame=request['frame'];keys=frame['active_frontier']
    unknowns=[v['name'] for v in frame['problem']['variables'] if v['state']=='UNKNOWN']
    operations=[r['operation'] for r in frame['catalogue'] if r.get('available_now',True)]+(['ASK'] if unknowns else [])
    if frame['finish_observations'] or 'Direct response permitted' in frame['finish_policy']:operations.append('FINISH')
    selection_schema=contract.obj({'operation':{'type':'string','enum':operations},'candidate':{'type':'string','enum':keys},
        'why':contract.text(180),'uncertainty':contract.text(160),'expected':contract.array(contract.text(100),2)})
    messages=request['messages']+[{'role':'user','content':'SELECT phase: honor problem.original_request and its requested order. Continue from actual_observations. Perform ready requested checks before asking about inputs needed only for a later check. Choose one new useful tool, ASK when further progress now depends on consequential missing input, or FINISH when current observations resolve the full request and requested follow-ups. A result already checked needs reporting, not another identical check. candidate is an active frontier key. Interpret adverse feedback against its tested branch. Do not provide arguments yet.'}]
    selected=slate_stream.complete(worker,messages,min(256,request['max_tokens']//3),selection_schema,
        cancelled=stopped,seconds=request['seconds'],kernel=kernel)
    folder=kernel.state/'jobs'/job['id'];(folder/'action-selection.txt').write_text(selected['text'])
    selection=brain.record_io.strict_json(selected['text'])
    schema_validate=contract.validate_schema
    schema_validate(selection,selection_schema)
    op=selection['operation'];full_schema=frame['response_schema'];base={k:full_schema['properties'][k] for k in ('alternatives','updates')}
    base['alternatives']={**base['alternatives'],'maxItems':min(1,base['alternatives']['maxItems'])}
    base['updates']={**base['updates'],'maxItems':min(2,base['updates']['maxItems'])}
    if op=='ASK':extra={'question':contract.text(1000),'missing':{'type':'array','minItems':1,'maxItems':min(16,len(unknowns)),'uniqueItems':True,'items':{'type':'string','enum':unknowns}}}
    elif op=='FINISH':
        extra={'text':contract.text(2000),'observations':{'type':'array','minItems':0 if 'Direct response permitted' in frame['finish_policy'] else 1,'maxItems':min(16,len(frame['finish_observations'])),'uniqueItems':True,'items':{'type':'string','enum':frame['finish_observations']}}}
        if not frame['finish_observations']:extra['observations']={'type':'array','maxItems':0,'items':{'type':'string'}}
    else:extra={'arguments':next(r['arguments'] for r in frame['catalogue'] if r['operation']==op)}
    details_schema=contract.obj({**base,**extra})
    messages=[{'role':'system','content':contract.SYSTEM},{'role':'user','content':records.canonical(phase_view(frame,op))},
        {'role':'assistant','content':selected['text']},{'role':'user','content':
        'ARGUMENTS phase: supply the selected operation '+op+'. Be brief. Do not choose another operation. Prefer [] for alternatives: existing frontier branches normally suffice. Interpret new actual adverse observations in updates: cite the observation alias and explain whether a candidate should be rejected, refined or retained. An INFEASIBLE checked constraint is an adverse mathematical result, not a broken tool. Before observations, use [] for updates. Saved variable names preserve units; a checked constraint needs a comparison. A tool failure never refutes a hypothesis.'+
        (' For FINISH, state what follows under the tested inputs and assumptions. A passing case establishes sufficiency, not necessity or uniqueness. Keep untested cases unexamined; do not imply an exhaustive solution or a physical guarantee.' if op=='FINISH' else '')}]
    remaining=request['seconds']-(time.monotonic()-began)
    if remaining<1:raise ValueError('ACTION_TWO_PHASE_TIME_BUDGET')
    response=slate_stream.complete(worker,messages,request['max_tokens']-min(256,request['max_tokens']//3),details_schema,
        on_delta=None,cancelled=stopped,seconds=remaining,kernel=kernel)
    (folder/'action-arguments.txt').write_text(response['text']);details=brain.record_io.strict_json(response['text']);schema_validate(details,details_schema)
    chosen={'kind':op if op in ('ASK','FINISH') else 'CALL'}
    if op!='FINISH':chosen['candidate']=selection['candidate']
    if op=='ASK':chosen.update(question=details['question'],missing=details['missing'])
    elif op=='FINISH':chosen.update(text=details['text'],observations=details['observations'])
    else:chosen.update(operation=op,arguments=details['arguments'])
    candidate={'text':selection['why'],'uncertainty':selection['uncertainty'],'expected':selection['expected'],
        'alternatives':details['alternatives'],'updates':details['updates'],'next':chosen}
    (folder/'action-response.txt').write_text(records.canonical(candidate))
    validation=validate(candidate,frame);live_request(kernel,request,p)
    argument_metrics={k:v for k,v in response.items() if k!='text'}
    response['prompt_tokens_measured']+=selected['prompt_tokens_measured']
    response['usage']={'completion_tokens':selected['usage'].get('completion_tokens',0)+response['usage'].get('completion_tokens',0)}
    response['elapsed_seconds']=time.monotonic()-began
    response['proposal_phases']={'select':{k:v for k,v in selected.items() if k!='text'},'arguments':argument_metrics}
    value={'status':'ACTION_PROPOSAL_VALIDATED','task':'ACTION','request':request['id'],'work':request['work'],'turn':request['turn'],
        'candidate':candidate,'validation':validation,'frame_digest':records.digest(request['frame']),'model':request['model'],
        'metrics':{k:v for k,v in response.items() if k!='text'},'authority':'PROPOSAL_NOT_PERMISSION_OR_OBSERVATION','cloud_calls':0}
    # This retained record supplies an immutable digest binding beyond the legacy
    # on-disk Brain result. The model cannot write this shared record store.
    value=records.new('adaptive_decision',p,id=request['id'],**value)
    with kernel.db() as db:records.write(db,value,p,'COMPLETE_ACTION_RESPONSE_VALIDATED')
    return value


def result(kernel,ident,p):
    from . import local_brain as brain
    value=brain.result(kernel,ident,p)
    if value['state']!='Completed':return value
    job=kernel.record('jobs',ident)
    if job['tool']!='brain.action':raise ValueError('Not an ACTION job')
    with kernel.db() as db:receipt=records.read(db,'adaptive_decision',job['request_spec']['brain']['conversation'],p)
    return {**value,'result':receipt}
