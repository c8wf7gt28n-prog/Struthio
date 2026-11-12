"""Pure, bounded staC engineering reasoning over *already retrieved* evidence.

These transformations NEVER infer a real measurement or promote design authority.
A scenario is explicitly hypothetical, even if arithmetic satisfies a constraint.
"""
from __future__ import annotations
from decimal import Decimal, InvalidOperation
from .quantities import Quantity, DimensionError
from .. import record_io


def _fact(value):
    if value.get('type')=='FactInquiry':return value['payload']
    body=value.get('payload',{})
    fact=body.get('fact_inquiry')
    if isinstance(fact, dict) and value.get('type') == 'WitnessJudgment' and body.get('state') != 'VERIFIED_SOURCE_REQUIREMENT':
        return {**fact, 'state':'UNKNOWN', 'original_verified':False,
                'original_page':None, 'reviewed_fact':None}
    return fact if isinstance(fact,dict) else None


def _limit(fact):
    """Return exact requirement upper bound; reject binary float inputs."""
    if fact.get('state')!='REVIEWED_FACT' or not fact.get('original_verified'):
        return None,'REVIEWED_ORIGINAL_REQUIRED'
    val=fact.get('reviewed_fact')
    if not isinstance(val,dict):return None,'INVALID_FACT'
    v=val.get('max');unit=val.get('unit')
    if v is None:return None,'NO_UPPER_BOUND_RECORDED'
    if isinstance(v,float) or isinstance(v,bool) or not isinstance(v,(str,int)):
        return None,'NON_EXACT_VENDOR_NUMBER'
    unit={'µs':'us','μs':'us'}.get(unit,unit)
    try:q=Quantity(Decimal(str(v)),unit)
    except (DimensionError,InvalidOperation,TypeError,ValueError):return None,'INVALID_VENDOR_QUANTITY'
    if q.dimension!='time':return None,'UNSUPPORTED_FACT_DIMENSION'
    return q,None


def assess(fact: dict) -> dict:
    limit,problem=_limit(fact)
    obligations=[]
    if problem:obligations.append(problem)
    # No simulation/physical observation is imported in this pass. Assessing a
    # requirement cannot be represented as passing simply because it exists.
    obligations += ['CURRENT_IMPLEMENTATION_TIMING_NOT_BOUND',
                    'REGISTERED_TEST_ORACLE_NOT_BOUND',
                    'APPLICABLE_TEST_RESULT_NOT_BOUND',
                    'PHYSICAL_QUALIFICATION_NOT_ESTABLISHED']
    return {'type':'QualificationAssessment','state':'UNKNOWN','applicability':'NOT_ASSESSED',
            'fact_inquiry':fact,'claim':'Current implementation complies with the selected requirement',
            'reviewed_upper_limit':({'value':str(limit.value),'unit':limit.unit} if limit else None),
            'proof_obligations':obligations,'claim_scope':'CURRENT_ENGINEERING_DESIGN',
            'observed_measurements':[], 'physical_qualification_granted':False,
            'reason':'No applicable instrumented implementation/test evidence was supplied to this assessment.'}


def suppose(fact:dict, args:dict) -> dict:
    if set(args)!={'value_si','unit','dimension'} or args.get('unit')!='s' or args.get('dimension')!='time':
        raise ValueError('Invalid normalized hypothetical quantity')
    value=args['value_si']
    if not isinstance(value,str) or len(value)>60:
        raise ValueError('Invalid hypothetical number')
    try:q=Quantity(Decimal(value),'s')
    except (DimensionError,InvalidOperation,ValueError) as exc:
        raise ValueError('Invalid hypothetical duration') from exc
    if q.value < 0 or q.value > Decimal('86400'):
        raise ValueError('Hypothetical duration out of bounds')
    limit,problem=_limit(fact)
    comparison=None
    state='SCENARIO_UNASSESSED'
    if limit:
        comparison=q.compare(limit)
        state='SCENARIO_WITHIN_LIMIT' if comparison<=0 else 'SCENARIO_EXCEEDS_LIMIT'
    return {'type':'ScenarioAssessment', 'state':state, 'fact_inquiry':fact,
            'assumed_quantity':{'value':str(q.value),'unit':'s','provenance':'HYPOTHETICAL_USER_INPUT'},
            'reviewed_upper_limit':({'value':str(limit.value),'unit':limit.unit} if limit else None),
            'numeric_comparison':comparison,'reason':problem,
            'evidence_state':'UNKNOWN','applicability':'HYPOTHETICAL_ONLY',
            'simulation_pass_proven':False,'physical_qualification_granted':False,
            'proof_obligations':['ASSUMPTION_IS_NOT_MEASUREMENT','CURRENT_IMPLEMENTATION_NOT_PROVEN',
                                 'REGISTERED_TEST_RESULT_REQUIRED']}


def compare(scenario: dict, args: dict) -> dict:
    """Evaluate a typed, exact hypothetical predicate, never a hardware claim.

    The literal right-hand side is user-provided. It is NOT a vendor limit or a
    measured target value. Its boolean result is arithmetic only and has no
    engineering evidentiary force without separately verified observations.
    """
    if not isinstance(scenario, dict) or scenario.get('type') != 'ScenarioAssessment':
        raise ValueError('Compare requires a hypothetical ScenarioAssessment')
    assumed = scenario.get('assumed_quantity', {})
    if assumed.get('provenance') != 'HYPOTHETICAL_USER_INPUT' or assumed.get('unit') != 's':
        raise ValueError('Compare requires an explicitly hypothetical left operand')
    if set(args) != {'relation', 'value_si', 'unit', 'dimension'}:
        raise ValueError('Invalid comparison arguments')
    relation = args['relation']
    if relation not in ('<', '<=', '>', '>=', '==', '!='):
        raise ValueError('Unsupported comparison operator')
    if args['unit'] != 's' or args['dimension'] != 'time':
        raise ValueError('Comparison units must be temporal and dimension-compatible')
    try:
        lhs = Quantity(Decimal(assumed['value']), 's')
        rhs = Quantity(Decimal(args['value_si']), 's')
    except (DimensionError, InvalidOperation, ValueError, KeyError) as exc:
        raise ValueError('Invalid exact comparison operands') from exc
    if not (Decimal('0') <= lhs.value <= Decimal('86400') and
            Decimal('0') <= rhs.value <= Decimal('86400')):
        raise ValueError('Comparison operands out of supported range')
    cmp = lhs.compare(rhs)
    holds = {'<': cmp < 0, '<=': cmp <= 0,
             '>': cmp > 0, '>=': cmp >= 0,
             '==': cmp == 0, '!=': cmp != 0}[relation]
    return {'type': 'PredicateAssessment',
            'state': 'HYPOTHETICAL_PREDICATE_TRUE' if holds else 'HYPOTHETICAL_PREDICATE_FALSE',
            'predicate': {'relation': relation,
                          'left': {'value_si': format(lhs.value.normalize(), 'f'), 'unit': 's'},
                          'right': {'value_si': format(rhs.value.normalize(), 'f'), 'unit': 's'}},
            'comparison_holds': holds,
            'comparison_scope': 'TWO_USER_SUPPLIED_NUMERIC_VALUES',
            'vendor_limit_established_by_comparison': False,
            'fact_inquiry': scenario.get('fact_inquiry'),
            'scenario': scenario,
            'proof_obligations': ['ASSUMPTION_IS_NOT_MEASUREMENT',
                                  'INDEPENDENT_VENDOR_REQUIREMENT_REQUIRED',
                                  'CURRENT_IMPLEMENTATION_NOT_PROVEN',
                                  'REGISTERED_TEST_RESULT_REQUIRED'],
            'evidence_state': 'UNKNOWN',
            'applicability': 'HYPOTHETICAL_ONLY',
            'model_invoked': False,
            'simulation_pass_proven': False,
            'physical_qualification_granted': False}


def challenge(value:dict) -> dict:
    f=_fact(value)
    if f is None:raise ValueError('Challenge requires an engineering fact or assessment')
    questions=[]
    if f.get('state')!='REVIEWED_FACT':
        questions.append({'question':'Can the applicable original manufacturer page and exact fitted variant be verified?',
                          'evidence_needed':'REVIEWED_ORIGINAL_FITMENT'})
    questions.extend([
        {'question':'What current RTL/firmware path implements this requirement, and does it match the source revision?',
         'evidence_needed':'CURRENT_IMPLEMENTATION_BINDING'},
        {'question':'Which reviewed test oracle could disprove compliance under the specified conditions?',
         'evidence_needed':'REGISTERED_TEST_ORACLE'},
        {'question':'Do applicable simulation results cover the boundary and relevant operating conditions?',
         'evidence_needed':'SOURCE_BOUND_SIMULATION_RESULT'},
        {'question':'What physical measurements would independently test the claim?',
         'evidence_needed':'AUTHORIZED_PHYSICAL_MEASUREMENT'},
    ])
    return {'type':'ChallengeReport','state':'PROPOSED_QUESTIONS_ONLY',
            'fact_inquiry':f,'questions':questions,
            'commands_executed':[], 'tests_executed':[], 'physical_qualification_granted':False,
            'note':'Questions are review prompts; no experimental design or tool action was approved.'}


def packet(value:dict) -> dict:
    f=_fact(value)
    if f is None:raise ValueError('Packet requires an engineering fact or assessment')
    selected=f.get('reviewed_fact') if f.get('state')=='REVIEWED_FACT' else None
    original=f.get('original_page') if f.get('original_verified') else None
    # Do not include original PDF content or unrestricted filesystem paths in
    # an LLM context packet. Source references and hashes permit later opening
    # through Ledger's existing authorized source reader.
    native=[]
    for path,metadata in sorted(f.get('native_source_manifest',{}).items()):
        if isinstance(path,str) and isinstance(metadata,dict):
            native.append({'path':path,'sha256':metadata.get('sha256'),
                           'state':'AVAILABLE' if metadata.get('sha256') else 'MISSING'})
    contents={'type':'KnowledgePacket','schema':'arc.stac.ekp/0.2',
              'subject':{'project':'ARC-1','board_revision':f.get('board_revision'),
                         'component':f.get('component'),'mpn':f.get('native_mpn'),
                         'property':f.get('property'),'native_revision':f.get('native_source_revision')},
              'source_bindings':{'native_files':native,'vendor_record_set_sha256':f.get('vendor_record_set_sha256'),
                                 'verified_original_page':original},
              'reviewed_requirement':selected,
              'knowledge_state':f.get('state','UNKNOWN'),
              'unresolved':([] if selected else [f.get('reason','REVIEWED_SOURCE_UNAVAILABLE')]),
              'derived_analysis':({'type':value['type'],
                                    'state':value['payload'].get('state'),
                                    'proof_obligations':value['payload'].get('proof_obligations',[])}
                                   if value['type']!='FactInquiry' else None),
              'witness_verification': ({'state':value['payload'].get('state'),
                                         'claim_digest':value['payload'].get('claim_digest'),
                                         'scope':'MANUFACTURER_REQUIREMENT_ONLY'}
                                       if value.get('type')=='WitnessJudgment' else None),
              'model_invoked':False,'execution_authority':'NONE',
              'cloud_disclosure':'NOT_AUTHORIZED',
              'physical_qualification_granted':False}
    contents['packet_digest_profile']='arc-record-io-json/1'
    contents['packet_sha256']=record_io.digest(contents)
    return contents
