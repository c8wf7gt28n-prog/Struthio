"""Connect staC's typed reads and observation journal to the caller's Kernel scope."""
from __future__ import annotations
import re, shlex, time, uuid
from sdk.cli.arc1cli import learning_contracts as c,record_store as records
from . import memory_service as memory,intake_service as intake

PROGRAM={'type':'string','minLength':1,'maxLength':4096}
INSPECTION_PROGRAM = {**PROGRAM, 'maxLength': 8192}
FIELDS={
 'stac.status':({},[]),'stac.compile':({'program':PROGRAM},['program']),
 'stac.inspect':({'program':INSPECTION_PROGRAM},['program']),
 'stac.translate':({'text':{'type':'string','maxLength':256}},['text']),
 'stac.run':({'program':PROGRAM},['program']),
 'stac.observe':({'program':PROGRAM},['program']),
 'stac.history':({},[]),
 'stac.export':({'program':PROGRAM,'destination':intake.TEXT},['program','destination'])}
SCOPES={op:'approve' if op=='stac.export' else 'execute' if op=='stac.observe' else 'read' for op in FIELDS}
START_WORDS = ('library', 'desk', 'package', 'map', 'source', 'packet', 'investigation',
               'inquiries', 'inquiry', 'algorithms', 'atlas', 'math', 'use')


def route_program(text, *, allow_inspection=False):
    """Choose inspection, typed staC, or query execution from the command line."""
    program = text.replace('\u200b', '').strip()
    first = program.split(maxsplit=1)
    if allow_inspection and first and first[0].lower() == 'explain':
        return 'stac.inspect', {'program': first[1] if len(first) > 1 else ''}
    if first and first[0].lower() in START_WORDS:
        return 'stac.run', {'program': program}
    return 'language.run', {'text': program}


def blocked_reason(result):
    """A successful dispatch can carry a typed read that was blocked."""
    if (isinstance(result, dict) and result.get('schema') == 'arc.stac-kernel-result/1'
            and result.get('state') == 'BLOCKED'):
        return result.get('reason') or 'The read was blocked.'
    return None


class CallerKernel:
    def __init__(self,kernel,principal):self.kernel=kernel;self.principal=principal
    def dispatch(self,op,args,upstream_principal):return self.kernel.dispatch(op,args,self.principal)
def reference_ir(program):
    # Finite extension; no alternate evaluator or shell expansion.
    lexer=shlex.shlex(program,posix=True,punctuation_chars='|');lexer.whitespace_split=True;lexer.commenters='';tokens=list(lexer);stages=[[]]
    for token in tokens:
        if token=='|':stages.append([])
        else:stages[-1].append(token)
    if len(stages)<2 or len(stages[0])!=2 or stages[0][0]!='library':raise ValueError('STAC_LIBRARY_SYNTAX')
    namespace=c.ident(stages[0][1]);command=stages[1];limit=5
    if len(stages)>3:raise ValueError('STAC_REFERENCE_STAGE_BOUND')
    if len(stages)==3:
        if len(stages[2])!=2 or stages[2][0]!='take' or not stages[2][1].isdigit():raise ValueError('STAC_REFERENCE_TAKE_SYNTAX')
        limit=int(stages[2][1])
        if not 1<=limit<=20:raise ValueError('STAC_REFERENCE_TAKE_BOUND')
    if len(command)==2 and command[0]=='search':op='references.search';args={'namespace':namespace,'query':c.text(command[1],300,False),'limit':limit};kind='List<LocatedReference>'
    elif len(command)==2 and command[0]=='reference' and len(stages)==2:op='references.resolve';args={'namespace':namespace,'id':c.ident(command[1],64)};kind='LocatedReference'
    elif len(command)==5 and command[0]=='question' and len(stages)==2:
        op='references.question';args={'namespace':namespace,'subject':command[1],'property':command[2],'variant':command[3],'conditions':records.strict(command[4])};kind='Question<SourceFact>'
    else:raise ValueError('STAC_REFERENCE_COMMAND_UNSUPPORTED')
    body={'schema':'arc.stac.reference-ir/1','operation':op,'arguments':args,'result_type':kind,'effects':['read'],'namespace':namespace}
    return {**body,'program_id':c.digest(body),'authority':'EXISTING_KERNEL_ACL_REQUIRED'}
MATH_STEPS={'solve':('within','step','given','unit'),'range':('given','unit'),'check':('given',)}
MATH_NAME=re.compile('[A-Za-z][A-Za-z0-9_]{0,63}')


def _math_number(text):
    from .math_units import rational
    try:rational(text)
    except ValueError:raise ValueError('STAC_MATH_NUMBER') from None
    return text


def math_ir(program):
    """A maths line on a problem sheet (docs/INTEGRATED_I02.md): strict shell words, at most 40, its steps in this order.
      math problem:ID | calculate "EXPR" [| unit U]                                                 -> math.preview
      math problem:ID | solve "REL" for NAME [| within LO HI] [| step S] [| given NAME LO HI] (up to four) [| unit U]
      math problem:ID | range "EXPR" [| given NAME LO HI] (up to four) [| unit U]
      math problem:ID | check "REL" [| given NAME LO HI] (up to four)                               -> math.answer
      math money | calculate|solve|range|check ... [| given NAME A [B] [CODE]] [| rate FROM TO R] [| round S] -> math.money
      math dates | calculate|solve|range|check ... [| given NAME D1 [D2]] [| holidays D ...]         -> math.dates
      math dates | deadline N UNIT after DATE [| end included|excluded] [| holidays D ...]           -> math.dates
      math dates | business days FROM TO [| holidays D ...]                                          -> math.dates
    The quoted expression is data for the typed compiler; LO, HI and S are in that quantity's declared unit."""
    try:tokens=shlex.split(program)
    except ValueError:raise ValueError('STAC_MATH_SYNTAX') from None
    if len(tokens)>40:raise ValueError('STAC_MATH_TOKEN_BOUND')
    stages=[[]]
    for token in tokens:
        if token=='|':stages.append([])
        else:stages[-1].append(token)
    if len(stages)<2 or len(stages[0])!=2 or stages[0][0]!='math' or not stages[1]:raise ValueError('STAC_MATH_SYNTAX')
    if stages[0][1] in ('money','dates'):   # 0.8.5: the owner's own amounts and dates, no sheet (math_typed, math_money, math_dates)
        from . import math_money,math_dates
        line=math_money if stages[0][1]=='money' else math_dates
        body={'schema':'arc.stac.math-ir/1','operation':'math.'+stages[0][1],'arguments':line.line_args(stages[1],stages[2:]),'effects':['read'],'result_type':'ExactMathematicalAnswer'}
        return {**body,'program_id':c.digest(body)}
    ident=stages[0][1].removeprefix('problem:')
    if not re.fullmatch('[0-9a-f]{32}',ident):raise ValueError('STAC_MATH_PROBLEM_ID')
    verb,rest=stages[1],stages[2:]
    if verb[0]=='calculate':
        if len(verb)!=2 or len(rest)>1 or (rest and len(rest[0])!=2):raise ValueError('STAC_MATH_SYNTAX')
        args={'id':ident,'expression':verb[1]}
        if rest:
            if rest[0][0]!='unit':raise ValueError('STAC_MATH_UNIT_SYNTAX')
            args['output_unit']=rest[0][1]
        body={'schema':'arc.stac.math-ir/1','operation':'math.preview','arguments':args,'effects':['read'],'result_type':'SourceBoundMathematicalPreview'}
        return {**body,'program_id':c.digest(body)}
    stage=verb[0]
    if stage not in MATH_STEPS or len(verb)!=(4 if stage=='solve' else 2) or (stage=='solve' and (verb[2]!='for' or not MATH_NAME.fullmatch(verb[3]))):
        raise ValueError('STAC_MATH_SYNTAX')
    args={'id':ident,'stage':stage,'expression':verb[1],**({'for':verb[3]} if stage=='solve' else {})}
    order=MATH_STEPS[stage];last=-1
    for step in rest:
        if not step or step[0] not in order:raise ValueError('STAC_MATH_SYNTAX')
        place=order.index(step[0])
        if place<last or (place==last and step[0]!='given'):raise ValueError('STAC_MATH_STEP_ORDER')
        last=place
        if step[0]=='within' and len(step)==3:args['within']=[_math_number(step[1]),_math_number(step[2])]
        elif step[0]=='step' and len(step)==2:args['step']=_math_number(step[1])
        elif step[0]=='given' and len(step)==4:
            if not MATH_NAME.fullmatch(step[1]):raise ValueError('STAC_MATH_NAME')
            args.setdefault('given',[]).append({'name':step[1],'lo':_math_number(step[2]),'hi':_math_number(step[3])})
            if len(args['given'])>4:raise ValueError('STAC_MATH_GIVEN_BOUND')
        elif step[0]=='unit' and len(step)==2:args['unit']=step[1]
        else:raise ValueError('STAC_MATH_UNIT_SYNTAX' if step[0]=='unit' else 'STAC_MATH_SYNTAX')
    body={'schema':'arc.stac.math-ir/1','operation':'math.answer','arguments':args,'effects':['read'],'result_type':'ExactMathematicalAnswer'}
    return {**body,'program_id':c.digest(body)}


MATH_GRAMMAR='math problem:ID | calculate "EXPR" [| unit U]; math problem:ID | solve "REL" for NAME [| within LO HI] [| step S] [| given NAME LO HI] [| unit U]; math problem:ID | range "EXPR" [| given NAME LO HI] [| unit U]; math problem:ID | check "REL" [| given NAME LO HI]; at most four given, each typed by the owner; math money | calculate, solve, range or check "EXPR" with amounts such as 1200 USD [| given NAME A [B] [CODE]] [| rate FROM TO R] [| round STEP]; math dates | calculate, solve, range or check "EXPR" with dates such as 2026-11-20 and lengths such as 30 days or 1 month [| given NAME D1 [D2]] [| holidays D ...]; math dates | deadline N days after DATE [| end included or excluded]; math dates | business days FROM TO [| holidays D ...]'


def gives_ranges(program):
    """Whether a maths line carries a range of its own (a given step), read as route_program and compile_program would read
    it. Ranges are the owner's to write: a line Kasandra proposes never carries one, whichever command carries the line; her
    ranges come only from the owner's tolerances (stacy_control.validate_actions)."""
    text=str(program or '').replace('\u200b','').strip();first=text.split(maxsplit=1)
    if first and first[0].lower()=='explain':text=first[1].strip() if len(first)>1 else ''
    if text.split(maxsplit=1)[:1]!=['math']:return False
    try:ir=math_ir(text)
    except ValueError:return False
    return owners_only(ir['operation'],ir['arguments'])


def owners_only(op,args):
    """Whether a maths call carries what only the owner gives: a range on a sheet's line; in a money or dates line a
    range, an exchange rate or a list of holidays (a single amount or date is the question itself)."""
    if not isinstance(args,dict):return False
    if op=='math.answer':return bool(args.get('given'))
    if op in ('math.money','math.dates'):
        from . import math_money,math_dates
        return (math_money if op=='math.money' else math_dates).owners(args)
    return False


def _freshness(kernel,principal,result,ident):
    """CURRENT or REVIEW_REQUIRED: the problem sheet's sources as they stand (problems.get), for every maths result."""
    if isinstance(result,dict) and result.get('schema')=='ledger.math-answer/1':return result['freshness']
    r=kernel.dispatch('problems.get',{'id':ident},principal)
    return r['result']['freshness']['state'] if r.get('ok') else 'REVIEW_REQUIRED'


def compile_program(program):
    c.text(program,4096,False)
    if len(program.encode())>4096:raise ValueError('STAC_PROGRAM_BYTE_BOUND')
    if program.strip() == 'inquiries' or program.lstrip().startswith('inquiry '):
        from .discovery_service import compile_read
        return {'kind': 'ATLAS', 'ir': compile_read(program), 'runtime_authorization': False}
    if program.strip() == 'algorithms' or program.lstrip().startswith('algorithms '):
        from .algorithm_atlas import compile_read
        return {'kind': 'ATLAS', 'ir': compile_read(program), 'runtime_authorization': False}
    if program.strip() == 'atlas' or program.lstrip().startswith('atlas '):
        from .tool_atlas import compile_read
        return {'kind': 'ATLAS', 'ir': compile_read(program), 'runtime_authorization': False}
    if program.lstrip().startswith('math '):return {'kind':'MATH','ir':math_ir(program),'runtime_authorization':False}
    if program.strip()=='desk' or program.lstrip().startswith(('desk ','package ')):
        from sdk.cli.arc1cli.work_organizer import compile_read
        return {'kind':'WORKBENCH','ir':compile_read(program),'runtime_authorization':False}
    if program.lstrip().startswith('investigation '):
        if any(ch in program for ch in ('\n','\r','\x00')):raise ValueError('STAC_INVESTIGATION_READ_BOUND')
        parts=program.split()
        if len(parts)!=4 or parts[0]!='investigation' or not re.fullmatch('[0-9a-f]{32}',parts[1]) or parts[2]!='|' or parts[3] not in ('inspect','gaps','why'):raise ValueError('STAC_INVESTIGATION_READ_SYNTAX')
        body={'schema':'arc.stac.investigation-ir/1','operation':'knowledge.investigation.result','arguments':{'job':parts[1]},'presentation':parts[3],'effects':['read'],'result_type':'BoundedEngineeringInvestigation'}
        return {'kind':'KNOWLEDGE','ir':{**body,'program_id':c.digest(body),'authority':'EXISTING_CALLER_PRINCIPAL_REQUIRED'},'runtime_authorization':False}
    if program.lstrip().startswith('packet '):
        from sdk.cli.arc1cli.engineering_packets import compile_read
        return {'kind':'KNOWLEDGE','ir':compile_read(program),'runtime_authorization':False}
    if program.lstrip().startswith(('map ','source ')):
        from sdk.cli.arc1cli.engineering_map import compile_read
        return {'kind':'KNOWLEDGE','ir':compile_read(program),'runtime_authorization':False}
    if program.lstrip().startswith('library '):return {'kind':'REFERENCE','ir':reference_ir(program),'runtime_authorization':False}
    from .stac import redirection,semantics
    from .stac.language import intent_hash
    io = redirection.parse(program)
    if io.script:
        raise ValueError('EMBEDDED_STAC_SCRIPT_REQUIRES_EXPLICIT_SOURCE_OPEN')
    ir = io.compile_inline()
    return {'kind': 'ENGINEERING', 'ir': ir, 'program_id': intent_hash(ir),
            'semantics': semantics.inspect(ir), 'presentation_io_requested': bool(io.stdout or io.stderr),
            'runtime_authorization': False}
def run(kernel,principal,program):
    compiled=compile_program(program)
    if compiled['kind'] in ('REFERENCE','KNOWLEDGE','WORKBENCH','MATH','ATLAS'):
        ir=compiled['ir'];r=kernel.dispatch(ir['operation'],ir['arguments'],principal)
        if not r['ok']:raise ValueError(r['error']['message'])
        if compiled['kind']=='WORKBENCH' and ir.get('presentation')=='gaps':
            value=r['result'];r['result']={k:value[k] for k in ('id','state','sha256','encryption','issues','transport','rules_current')}
        out={'schema':'arc.stac-kernel-result/1','program_id':ir['program_id'],'invocation_id':uuid.uuid4().hex,'result_type':ir.get('result_type','SourceBoundEngineeringRelationships'),'result':r['result'],'effects':['read'],'engineering_qualification':False}
        if compiled['kind']=='MATH':out['freshness']=_freshness(kernel,principal,r['result'],ir['arguments'].get('id'))
        return out
    if compiled['presentation_io_requested']:raise ValueError('EMBEDDED_IO_REQUIRES_OWNER_STAC_EXPORT_ACTION')
    from .stac.runtime import evaluate,RunError
    try:return {'schema':'arc.stac-kernel-result/1','state':'READ_COMPLETED','result':evaluate(compiled['ir'],CallerKernel(kernel,principal)),'authority':'EXISTING_CALLER_PRINCIPAL','physical_qualification':False}
    except RunError as exc:return {'schema':'arc.stac-kernel-result/1','state':'BLOCKED','reason':str(exc),'result':None,'physical_qualification':False}


def inspect_program(kernel, principal, program):
    """Describe what the existing compiler would run, without dispatching sources."""
    from . import stacy_language

    route, args = route_program(program, allow_inspection=True)
    if route == 'stac.inspect':
        raise ValueError('Explain takes a line without another explain prefix')
    if route == 'language.run':
        plan, steps = stacy_language.inspect_plan(kernel, args['text'], principal)
        operation = steps[0]['operation']
        source_binding = {'state': 'VERIFIED_SEED', 'seed_id': plan['seed_id']}
        effects = ['read']
    else:
        compiled = compile_program(args['program'])
        if compiled.get('presentation_io_requested'):
            raise ValueError('EMBEDDED_IO_REQUIRES_OWNER_STAC_EXPORT_ACTION')
        if compiled['kind'] == 'ENGINEERING':
            semantics = compiled['semantics']
            steps = semantics['typed_ast']
            effects = semantics['declared_effects']
            operation = None
            source_binding = {'state': semantics['source_binding_state'], 'context': semantics['symbolic_context']}
        else:
            ir = compiled['ir']
            operation = ir['operation']
            call = {'operation': operation, 'arguments': ir['arguments']}
            stacy_language.validate_read_call(call, principal)
            steps = [dict(command='read', **call)]
            source_binding = {'state': 'RUNTIME_CHECK_REQUIRED'}
            effects = ir['effects']
    return {'schema': 'arc.stac-inspection/1', 'program': program, 'operation': operation,
            'steps': steps, 'required_scope': 'read', 'effects': effects, 'source_binding': source_binding,
            'executed': False, 'model_calls': 0,
            'summary': 'Plan ready. Run the line itself to read its results.'}


def dispatch(kernel,op,args,principal):
    if op=='stac.status':return {'schema':'arc.stac-bridge/1','upstream':'0.6','discovery_grammar':'inquiries; inquiry ID | inspect; inquiry ID | history','algorithm_grammar':'algorithms; algorithms | find TEXT; algorithms | method ID','atlas_grammar':'atlas; atlas | find TEXT; atlas | operation ID; atlas | tool ID','workbench_grammar':'desk; desk | focus bring-in/understand/build/follow-through; desk | find TEXT; package ID | contents/gaps','workbench_scope':'Kernel bridge read extension; upstream POSIX grammar unchanged','math_grammar':MATH_GRAMMAR,'knowledge_grammar':'source ID | search TEXT | take 5; map ID[@REV] | part REF; map ID | net NET; map ID | trace REF REF; map ID | evidence; map ID | status','execution_authority':'EXISTING_KERNEL','caller':'FORWARDED_WITHOUT_SCOPE_ESCALATION','reference_grammar':'library NS | search TEXT | take 5; library NS | reference ID; library NS | question SUBJECT PROPERTY VARIANT JSON','observation_store':'SHARED_KERNEL_MEMORY_AND_ACTIVITY','legacy_POSIX_CLI':'USER_INVOKED_ONLY_WINDOWS_IO_UNQUALIFIED','local_brain':'EXISTING_LEDGER_BRAIN'}
    if op=='stac.compile':return compile_program(args['program'])
    if op=='stac.inspect':return inspect_program(kernel,principal,args['program'])
    if op=='stac.translate':
        from .stac.controlled_language import translate
        return translate(args['text'])
    if op=='stac.history':
        with kernel.db() as db:return {'observations':memory.listing(db,principal.identity,'observation'),'class':'HISTORICAL_READ_OBSERVATIONS_NOT_CURRENT_PROOF'}
    result=run(kernel,principal,args['program'])
    if op=='stac.run':return result
    if op=='stac.observe':
        value={'id':uuid.uuid4().hex,'created':time.time(),'program':args['program'],'result':result,'result_sha256':c.digest(result),'class':'RECORDED_READ_OBSERVATION_NOT_NEW_EVIDENCE'}
        with kernel.db() as db:memory.store(db,principal.identity,'observation',value['id'],value);memory.event(db,principal.identity,'STAC_OBSERVATION_RECORDED')
        return value
    if op=='stac.export':
        path=memory.fresh_destination(kernel,args['destination'],'.json');raw=records.canonical(result);memory.publish(path,raw)
        with kernel.db() as db:memory.event(db,principal.identity,'STAC_RESULT_EXPORTED')
        return {'state':'EXPORTED','bytes':len(raw),'path':str(path),'physical_qualification':False}
    raise ValueError('STAC_BRIDGE_OPERATION_UNKNOWN')
