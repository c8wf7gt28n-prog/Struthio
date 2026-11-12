"""Read-only typed pipelines over the existing Kernel authorization boundary."""
from sdk.cli.arc1cli import typed_pipeline
from . import stacy_foundation

FIELDS={'language.parse':({'text':{'type':'string','minLength':1,'maxLength':8192}},['text']),
        'language.run':({'text':{'type':'string','minLength':1,'maxLength':8192},'expected_seed':{'type':'string','maxLength':64}},['text'])}
SCOPES={name:'read' for name in FIELDS}

def _verified_seed_id(kernel):
    seed = stacy_foundation.seed_status(kernel.root)
    if seed['state'] != 'VERIFIED_SOURCE_BINDINGS':
        raise ValueError('Graphite seed/source binding is not current')
    return seed['seed_id']


def bind_actions(kernel,actions,principal):
    """Bind every proposed action to the same verified source revision."""
    from .engineering_kernel import CAPABILITIES
    from .engineering_cli import schemas
    from .agent_operations import validate
    seed_id = _verified_seed_id(kernel)
    plans=[]
    for action in actions:
        op=action['operation'];args=action['arguments']
        if op=='language.run':
            plan=_compile_plan(kernel,args['text'],principal,seed_id=seed_id)
            if args.get('expected_seed') not in (None,seed_id):raise ValueError('Proposed pipeline source binding is stale')
            _joined_plans(kernel, plan, principal)
            plans.append(plan);continue
        if op not in CAPABILITIES or CAPABILITIES[op] not in principal.scopes:raise ValueError('Plan exceeds the transport principal')
        validate(args,schemas()[op])
        plan={'schema':'arc.stacy-action-plan/1','language_version':1,'call':{'operation':op,'arguments':args},
              'transforms':[],'text':op+' '+typed_pipeline.canonical(args),'principal':principal.identity,
              'seed_id':seed_id,'permission':CAPABILITIES[op]}
        plan['plan_id']=typed_pipeline.digest(plan);plans.append(plan)
    return plans

def source(text):
    """A pipeline may start from any Ledger address: ``@notebook:owner:... | select title``."""
    if not isinstance(text,str) or not text.lstrip().startswith('@'):return text,None
    from . import addresses
    head,separator,rest=text.lstrip()[1:].partition('|');address=head.strip()
    addresses.parse(address)
    return 'ledger.address.read '+typed_pipeline.canonical({'address':address})+(' |'+rest if separator else ''),address

def _compile_plan(kernel, program, principal, *, seed_id=None):
    text,address=source(program)
    plan=typed_pipeline.parse(text);call=plan['call']
    if address:plan.update(address=address,text=program)
    validate_read_call(call, principal)
    if call['operation'] == 'ledger.address.read':
        validate_read_call(_resolved_read(call), principal)
    if seed_id is None:
        seed_id = _verified_seed_id(kernel)
    plan.update(principal=principal.identity,seed_id=seed_id,permission='read')
    plan['plan_id']=typed_pipeline.digest(plan)
    return plan


def validate_read_call(call, principal):
    from .engineering_kernel import CAPABILITIES
    from .engineering_cli import schemas
    from .agent_operations import validate

    operation = call['operation']
    if operation not in CAPABILITIES or CAPABILITIES[operation]!='read' or operation.startswith('language.') or operation=='stac.inspect':
        raise ValueError('A pipeline source must be a registered read-only Kernel operation')
    if 'read' not in principal.scopes:raise ValueError('Read scope required')
    definition=schemas()[operation]
    if set(call['arguments'])-set(definition['properties']) or set(definition['required'])-set(call['arguments']):raise ValueError('Unknown or missing pipeline source arguments')
    validate(call['arguments'],definition)


def _joined_plans(kernel, plan, principal):
    sides = {}
    for index, transform in enumerate(plan['transforms']):
        if transform['kind'] in ('join', 'missing'):
            side = _compile_plan(kernel, transform['source'], principal, seed_id=plan['seed_id'])
            if any(step['kind'] in ('join', 'missing') for step in side['transforms']):
                raise ValueError('A joined source cannot join again')
            sides[index] = side
    return sides


def _resolved_read(call):
    if call['operation'] != 'ledger.address.read':
        return call
    from .addresses import call as address_call

    _, operation, arguments = address_call(call['arguments']['address'])
    return {'operation': operation, 'arguments': arguments}


def inspect_plan(kernel, program, principal):
    """Describe all planned source reads and transforms before reading any rows."""
    plan = _compile_plan(kernel, program, principal)
    sides = _joined_plans(kernel, plan, principal)
    steps = [dict(command='read', **_resolved_read(plan['call']))]
    for side in sides.values():
        steps.append(dict(command='read joined source', **_resolved_read(side['call'])))
        steps.extend(dict(command='joined ' + step['kind'], arguments=step)
                     for step in side['transforms'])
    steps.extend(dict(command=step['kind'], arguments=step) for step in plan['transforms'])
    return plan, steps


def dispatch(kernel,op,args,principal):
    plan = _compile_plan(kernel, args['text'], principal)
    if args.get('expected_seed') not in (None,plan['seed_id']):raise ValueError('Plan source binding changed; inspect the plan again')
    sides = _joined_plans(kernel, plan, principal)
    if op=='language.parse':return plan
    limit=2000 if args.get('_join_side') else 200
    return _execute_plan(kernel, plan, principal, sides, limit)


def _execute_plan(kernel, plan, principal, sides, limit):
    call = plan['call']
    response=kernel.dispatch(call['operation'],call['arguments'],principal)
    if not response['ok']:raise ValueError(response['error']['message'])
    value=response['result']['object'] if 'address' in plan else response['result']
    transforms=[dict(t) for t in plan['transforms']]
    for index, side in sides.items():
        if _verified_seed_id(kernel) != side['seed_id']:
            raise ValueError('Plan source binding changed; inspect the plan again')
        transforms[index]['rows'] = _execute_plan(kernel, side, principal, {}, 2000)['rows']
    return {'schema':'arc.stacy-pipeline-result/1','plan':plan,'rows':typed_pipeline.apply(value,transforms,limit),
            'execution':'REGISTERED_READ_ONLY_KERNEL_CALL','model_calls':0}
