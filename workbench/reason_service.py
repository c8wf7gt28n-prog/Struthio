"""Durable proposed reason graphs, actual receipt comparisons and Chronicle."""
from . import project_desk as records, problem_service as problems, math_service, lab_service, reason_graph

FIELDS={
 'reasons.create':({**problems.BOUND,'graph':{'type':'object'}},[*problems.BOUND,'graph']),
 'reasons.memory':({**problems.BOUND,'calculation':records.ID,'experiment':records.ID},[*problems.BOUND,'calculation','experiment']),
 'reasons.get':({'id':records.ID},['id']),
 'reasons.list':({'id':records.ID},['id']),
 'reasons.evaluate':({'id':records.ID,'expected_revision':records.REV},['id','expected_revision']),
 'reasons.revise':({'id':records.ID,'expected_revision':records.REV,'graph':{'type':'object'}},['id','expected_revision','graph']),
 'reasons.impact':({'id':records.ID,'node':{'type':'string','maxLength':40}},['id','node']),
 'reasons.record':({'id':records.ID},['id']),
}
SCOPES={op:'read' if op in ('reasons.get','reasons.list','reasons.impact') else 'execute' for op in FIELDS}


def read(kernel,ident,p):return lab_service.read(kernel,'reason_graph',ident,p)


def observe(kernel,plan,node,p):
    """Only fixed comparisons of owned, completed receipts may set support bits."""
    try:
        if node['source']=='MATH':
            receipt=lab_service.read(kernel,'math_result',node['receipt'],p)
            action=math_service.read_action(kernel,receipt['action'],p)
            math_service.check_action(kernel,action,p)
            output=receipt['snapshot']['outputs'][node['index']]
            if output.get('kind')!='boolean' or output.get('state')!='EXACT' or type(output.get('value')) is not bool:raise ValueError('No exact boolean observation at this output')
            value=output['value'];context={'model_digest':action['model_digest'],'assumptions':action['model']['assumptions'],'variable_bindings':action['variable_bindings']}
        else:
            receipt=lab_service.result(kernel,node['receipt'],p)
            if receipt['state']!='AVAILABLE':raise ValueError('Observation job is not completed')
            if receipt['applicability']!='CURRENT':raise ValueError('Observation inputs changed')
            action=lab_service.read(kernel,'lab_action',receipt['action'],p);body=receipt['observation']
            if node['source']=='EXPERIMENT':
                if action['operation']!='PYTHON' or body['state']!='OBSERVED':raise ValueError('No executed valid Python result')
                rows=[v for v in body['parsed']['measurements'] if v['name']==node['measurement']]
                if len(rows)!=1 or type(rows[0]['value']) is not bool:raise ValueError('No exact boolean measurement')
                value=rows[0]['value']
                context={'parameters':action['parameters'],'reported_assumptions':body['parsed']['assumptions'],'script_sha256':action['inputs'][0]['sha256']}
            else:
                if action['operation']!='BOARD' or body.get('execution_status')!='COMPLETED':raise ValueError('No native board observation')
                value=body['native']['total']==0
                context={'scope':body['scope'],'native_version':body['native']['kicad_version']}
        if receipt['problem']!=plan['problem'] or receipt['problem_revision']!=plan['problem_revision'] or receipt['context_digest']!=plan['context_digest']:raise ValueError('Reason atom belongs to a different problem revision or context')
        return {'state':'OBSERVED','applicability':'CURRENT','value':value,'receipt':node['receipt'],
                'output_predicate_checked_by':'LEDGER_COORDINATOR','context':context,
                'interpretation':'Output comparison only. Proposed labels and inference rules still require review.'}
    except (OSError,ValueError,KeyError,IndexError,TypeError) as exc:
        return {'state':'UNAVAILABLE_OR_STALE','applicability':'STALE','value':None,'receipt':node['receipt'],'reason':str(exc)}


def compute(kernel,plan,p):
    graph=plan['graph'];nodes,_,_,_=reason_graph.validate(graph)
    try:
        problem=math_service.current(kernel,plan['problem'],p)
        problems.check_bound(problem,{'expected_revision':plan['problem_revision'],'expected_context_digest':plan['context_digest']})
        current=True
    except (OSError,ValueError):current=False
    observations={name:observe(kernel,plan,node,p) if current else {'state':'PROBLEM_CONTEXT_CHANGED','applicability':'STALE','value':None,'receipt':node['receipt']}
                  for name,node in nodes.items() if node['kind']=='ATOM'}
    value=reason_graph.compute(graph,observations)
    from pathlib import Path
    from .experiment_runtime import sha
    value['engine_binding']={name:sha(Path(__file__).parent/name) for name in ('reason_service.py','reason_graph.py','stac/evidence.py')}
    if not current:value['applicability']='STALE_PROBLEM_CONTEXT'
    return value


def evaluate(kernel,args,p):
    plan=read(kernel,args['id'],p)
    if plan['revision']!=args['expected_revision']:raise ValueError('REVISION_CHANGED: reopen reasons')
    snapshot=compute(kernel,plan,p)
    previous=lab_service.read(kernel,'reason_result',plan['latest'],p) if plan['latest'] else None
    change={'verdict_changed':previous is not None and previous['snapshot']['state']!=snapshot['state'],
            'reason_paths_changed':previous is not None and previous['snapshot']['reason_digest']!=snapshot['reason_digest'],
            'has_previous':previous is not None}
    value=records.new('reason_result',p,schema='ledger.reason-result/1',problem=plan['problem'],graph=plan['id'],
        graph_revision=plan['revision'],definition_digest=records.digest(plan['graph']),problem_revision=plan['problem_revision'],
        context_digest=plan['context_digest'],snapshot=snapshot,previous=plan['latest'],change=change,model_calls=0)
    with kernel.db() as db:
        live=records.read(db,'reason_graph',plan['id'],p);records.edit(live,args['expected_revision'])
        records.write(db,value,p,'REASONS_RECOMPUTED');live['latest']=value['id'];records.write(db,live,p,'REASON_SNAPSHOT_BOUND',expected=args['expected_revision'])
    from .stac import chronicle
    # Separate local transactions: a failed chronology append does not erase the
    # saved reason result. The get endpoint can expose and retry that append.
    try:event=chronicle.observe_reason(kernel.root,live,value)
    except (OSError,ValueError) as exc:event={'status':'PENDING','reason':str(exc),'retry_operation':'reasons.record'}
    return {'graph':live,'result':value,'chronicle':event}


def memory_graph(math_receipt,python_job):
    return {'nodes':[
        {'id':'exact','kind':'ATOM','label':'Exact concurrent memory comparison is false','source':'MATH','receipt':math_receipt,'index':0,'expected':False},
        {'id':'experiment','kind':'ATOM','label':'Executed memory comparison is false','source':'EXPERIMENT','receipt':python_job,'measurement':'memory_fits','expected':False},
        {'id':'concurrent','kind':'ASSUMPTION','label':'All three allocations are concurrent.'},
        {'id':'conclusion','kind':'CLAIM','label':'The declared concurrent memory model exceeds the limit.'}],
        'rules':[
            {'id':'via_exact','conclusion':'conclusion','polarity':'positive','premises':[{'id':'exact','polarity':'positive'},{'id':'concurrent','polarity':'positive'}]},
            {'id':'via_execution','conclusion':'conclusion','polarity':'positive','premises':[{'id':'experiment','polarity':'positive'},{'id':'concurrent','polarity':'positive'}]},
            {'id':'execution_disagrees','conclusion':'conclusion','polarity':'negative','premises':[{'id':'experiment','polarity':'negative'},{'id':'concurrent','polarity':'positive'}]}],
        'target':'conclusion','assumptions':['All three allocations are concurrent.','Proposed links compare computational outputs. Model interpretations and physical behavior remain unqualified.'],
        'coverage':'DECLARED_FINITE_GRAPH'}


def dispatch(kernel,op,args,p):
    if op=='reasons.memory':
        problem=math_service.current(kernel,args['id'],p);problems.check_bound(problem,args)
        receipt=lab_service.read(kernel,'math_result',args['calculation'],p)
        action=math_service.read_action(kernel,receipt['action'],p);math_service.check_action(kernel,action,p)
        expected,_=math_service.model_for(problem,{'expression':'buffer_A + buffer_B + workspace <= memory_limit','assumptions':action['model']['assumptions']})
        if action['model']!=expected['model'] or action['backend']!='EXACT':raise ValueError('Select the saved exact concurrent-memory calculation')
        experiment=lab_service.result(kernel,args['experiment'],p)
        if experiment['state']!='AVAILABLE':raise ValueError('Select a completed Python observation')
        plan=lab_service.read(kernel,'lab_action',experiment['action'],p)
        for name in ('buffer_A','buffer_B','workspace','memory_limit'):
            value=next((v for v in problem['variables'] if v['name']==name),None)
            if not value or value['state']!='KNOWN' or value['unit']!='MiB' or plan['parameters'].get(name)!=value['value']:raise ValueError('Memory comparison requires the saved MiB quantities; scenario overrides need their own proposed graph')
        graph=memory_graph(receipt['id'],experiment['job'])
        proposal={'problem':problem['id'],'problem_revision':problem['revision'],'context_digest':problem['context_digest']}
        if any(observe(kernel,proposal,node,p)['state']!='OBSERVED' for node in graph['nodes'] if node['kind']=='ATOM'):raise ValueError('Both selected observations must be current in this problem context')
        return dispatch(kernel,'reasons.create',{**{k:args[k] for k in problems.BOUND},'graph':graph},p)
    if op=='reasons.create':
        problem=math_service.current(kernel,args['id'],p);problems.check_bound(problem,args);reason_graph.validate(args['graph'])
        value=records.new('reason_graph',p,schema='ledger.reason-graph/1',problem=problem['id'],problem_revision=problem['revision'],
            context_digest=problem['context_digest'],graph=args['graph'],latest=None,origin='PROPOSED_RULES',physical_qualification=False)
        with kernel.db() as db:return records.write(db,value,p,'REASON_GRAPH_PROPOSED')
    if op=='reasons.get':
        plan=read(kernel,args['id'],p);latest=lab_service.read(kernel,'reason_result',plan['latest'],p) if plan['latest'] else None
        return {'graph':plan,'latest':latest,'preview':compute(kernel,plan,p),'automatic_execution':False}
    if op=='reasons.evaluate':return evaluate(kernel,args,p)
    if op=='reasons.record':
        from .stac import chronicle
        plan=read(kernel,args['id'],p)
        if not plan['latest']:raise ValueError('No saved reason result to record')
        return chronicle.observe_reason(kernel.root,plan,lab_service.read(kernel,'reason_result',plan['latest'],p))
    if op=='reasons.revise':
        reason_graph.validate(args['graph'])
        with kernel.db() as db:
            plan=records.read(db,'reason_graph',args['id'],p);records.edit(plan,args['expected_revision']);plan['graph']=args['graph']
            return records.write(db,plan,p,'REASON_GRAPH_REVISED',expected=args['expected_revision'])
    if op=='reasons.list':
        with kernel.db() as db:
            problem=problems.load(db,args['id'],p)
            return {'graphs':problems.related(db,problem,'reason_graph',p),'results':problems.related(db,problem,'reason_result',p)}
    if op=='reasons.impact':
        plan=read(kernel,args['id'],p);nodes,rules,order,edges=reason_graph.validate(plan['graph'])
        if args['node'] not in nodes:return {'tracked':[],'coverage':'UNKNOWN_DEPENDENCY','conclusion':'Cannot infer no impact from a missing edge.'}
        impacted={args['node']}
        for name in order:
            if edges[name]&impacted:impacted.add(name)
        return {'tracked':sorted(impacted),'coverage':plan['graph']['coverage'],'outside_graph':'UNKNOWN','conclusion':'Recompute tracked reasons; a stable verdict can hide changed support.'}
    raise ValueError('Unknown reason operation')
