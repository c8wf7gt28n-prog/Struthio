"""Exact peak occupancy for explicitly supplied, half-open allocation lifetimes."""
from fractions import Fraction
from . import project_desk as records, problem_service as problems, math_service, math_units as units

NAME={'type':'string','minLength':1,'maxLength':100}
INTERVAL={'type':'object','additionalProperties':False,'properties':{'start':NAME,'stop':NAME,'unit':NAME},'required':['start','stop','unit']}
PAIR={'type':'object','additionalProperties':False,'properties':{'quantity':NAME,'lifetime':NAME},'required':['quantity','lifetime']}
FIELDS={
 'math.concurrent':({**problems.BOUND,'capacity':NAME,'allocations':{'type':'array','minItems':1,'maxItems':32,'items':NAME}},[*problems.BOUND,'capacity','allocations']),
 'math.calculate':({**problems.BOUND,**math_service.INPUT,'backend':math_service.BACKEND},[*problems.BOUND]),
 'math.schedule':({**problems.BOUND,'capacity':NAME,'allocations':{'type':'array','minItems':1,'maxItems':32,'items':PAIR}},[*problems.BOUND,'capacity','allocations']),
 'math.schedule.get':({'id':records.ID},['id'])}
SCOPES={op:'read' if op.endswith('.get') else 'execute' for op in FIELDS}


def evaluate(problem,capacity,allocations):
    variables={v['name']:v for v in problem['variables']};cap=variables.get(capacity)
    if not cap or cap['type']!='quantity' or cap['state']!='KNOWN':raise ValueError('SCHEDULE_CAPACITY_UNKNOWN')
    dimension,factor=units.unit_spec(cap['unit']);limit=units.rational(cap['value'])*factor
    if limit<0:raise ValueError('SCHEDULE_NEGATIVE_CAPACITY')
    seen=set();events={};bound=[];missing=[]
    for pair in allocations:
        name=pair['quantity'];life=pair['lifetime']
        if name in seen:raise ValueError('SCHEDULE_DUPLICATE_ALLOCATION')
        seen.add(name);quantity=variables.get(name);interval=variables.get(life)
        if not quantity or quantity['type']!='quantity' or quantity['state']!='KNOWN':raise ValueError('SCHEDULE_QUANTITY_UNKNOWN: '+name)
        d,f=units.unit_spec(quantity['unit'])
        if d!=dimension:raise ValueError('SCHEDULE_DIMENSION_MISMATCH')
        amount=units.rational(quantity['value'])*f
        if amount<0:raise ValueError('SCHEDULE_NEGATIVE_ALLOCATION')
        if not interval or interval['type']!='interval':raise ValueError('SCHEDULE_LIFETIME_NOT_DECLARED: '+life)
        if interval['state']!='KNOWN':missing.append(life);continue
        from .record_io import strict_json
        value=strict_json(interval['value'].encode())
        from .agent_operations import validate
        validate(value,INTERVAL)
        if set(value)!={'start','stop','unit'}:raise ValueError('SCHEDULE_INTERVAL_FIELDS')
        td,tf=units.unit_spec(value['unit'])
        if td!=units.DIMENSIONS['time']:raise ValueError('SCHEDULE_TIME_UNIT_REQUIRED')
        declared,_=units.unit_spec(interval['unit'])
        if declared!=td:raise ValueError('SCHEDULE_INTERVAL_DECLARATION_UNIT')
        start=units.rational(value['start'])*tf;stop=units.rational(value['stop'])*tf
        if start<0 or start>=stop:raise ValueError('SCHEDULE_HALF_OPEN_INTERVAL_ORDER')
        events.setdefault(start,[]).append((name,amount,True));events.setdefault(stop,[]).append((name,amount,False))
        bound.append({'quantity':name,'lifetime':life,'amount':units.quantity_record(amount,dimension,cap['unit']),
                      'start':str(start),'stop':str(stop),'time_unit':'s','basis':interval['basis']})
    assumptions=['Half-open [start, stop) lifetimes; releases at a boundary occur before allocations at that boundary.',
                 'Additive capacity; no fragmentation, alignment, allocator overhead or indivisibility is modeled.']
    if missing:return {'state':'UNKNOWN','missing':sorted(set(missing)),'assumptions':assumptions,'observed':False}
    active={};current=Fraction(0);peak=Fraction(0);segments=[];times=sorted(events)
    for i,at in enumerate(times):
        for name,amount,begin in events[at]:
            if not begin:active.pop(name,None);current-=amount
        for name,amount,begin in events[at]:
            if begin:active[name]=amount;current+=amount
        if current<0:raise ValueError('SCHEDULE_SWEEP_INVARIANT')
        peak=max(peak,current)
        if i+1<len(times):segments.append({'start':str(at),'stop':str(times[i+1]),'unit':'s','active':sorted(active),
                                         'demand':units.quantity_record(current,dimension,cap['unit']),'fits':current<=limit})
    fits=peak<=limit
    return {'state':'FEASIBLE' if fits else 'INFEASIBLE','missing':[],'observed':True,'fits':fits,
        'peak':units.quantity_record(peak,dimension,cap['unit']),'capacity':units.quantity_record(limit,dimension,cap['unit']),
        'segments':segments,'inputs':bound,'assumptions':assumptions,'physical_qualification':False}


def dispatch(kernel,op,args,p):
    if op=='math.concurrent':
        problem=math_service.current(kernel,args['id'],p);problems.check_bound(problem,args)
        names=args['allocations'];declared={v['name'] for v in problem['variables'] if v['type']=='quantity'}
        if not names or len(set(names))!=len(names) or not set(names+[args['capacity']])<=declared or any(not name.isidentifier() for name in names+[args['capacity']]):raise ValueError('CONCURRENT_DECLARED_UNIQUE_QUANTITIES_REQUIRED')
        expression=' + '.join(names)+' <= '+args['capacity']
        action=math_service.prepare(kernel,{**{k:args[k] for k in problems.BOUND},'expression':expression,
            'assumptions':['All selected allocations are concurrent.'],'backend':'EXACT'},p)
        return math_service.run(kernel,action['id'],p)
    if op=='math.calculate':
        action=math_service.prepare(kernel,args,p);return math_service.run(kernel,action['id'],p)
    if op=='math.schedule.get':
        with kernel.db() as db:value=records.read(db,'math_schedule_result',args['id'],p)
        current=problems.get(kernel,value['problem'],p)
        from pathlib import Path
        import hashlib
        implementation=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==value['implementation_sha256']
        state='CURRENT' if implementation and current['freshness']['state']=='CURRENT' and current['problem']['context_digest']==value['context_digest'] else 'STALE'
        return {'receipt':value,'applicability':state,'implementation':'CURRENT' if implementation else 'HISTORICAL'}
    problem=math_service.current(kernel,args['id'],p);problems.check_bound(problem,args)
    snapshot=evaluate(problem,args['capacity'],args['allocations'])
    from pathlib import Path
    import hashlib
    value=records.new('math_schedule_result',p,schema='ledger.schedule-result/1',problem=problem['id'],problem_revision=problem['revision'],
        context_digest=problem['context_digest'],arguments=args,snapshot=snapshot,output_digest=records.digest(snapshot),
        implementation_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),model_calls=0,physical_qualification=False)
    with kernel.db() as db:
        problems.check_bound(problems.load(db,problem['id'],p),args);return records.write(db,value,p,'EXACT_SCHEDULE_OBSERVED')
