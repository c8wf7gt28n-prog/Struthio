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
    if program.lstrip().startswith('math '):
        tokens=shlex.split(program)
        if len(tokens) not in (5,8) or tokens[0]!='math' or tokens[2:4]!=['|','calculate']:raise ValueError('STAC_MATH_SYNTAX')
        # The quoted expression is data for the typed compiler.
        ident=tokens[1].removeprefix('problem:')
        if not re.fullmatch('[0-9a-f]{32}',ident):raise ValueError('STAC_MATH_PROBLEM_ID')
        args={'id':ident,'expression':tokens[4]}
        if len(tokens)==8:
            if tokens[5:7]!=['|','unit']:raise ValueError('STAC_MATH_UNIT_SYNTAX')
            args['output_unit']=tokens[7]
        body={'schema':'arc.stac.math-ir/1','operation':'math.preview','arguments':args,'effects':['read'],'result_type':'SourceBoundMathematicalPreview'}
        return {'kind':'MATH','ir':{**body,'program_id':c.digest(body)},'runtime_authorization':False}
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
        return {'schema':'arc.stac-kernel-result/1','program_id':ir['program_id'],'invocation_id':uuid.uuid4().hex,'result_type':ir.get('result_type','SourceBoundEngineeringRelationships'),'result':r['result'],'effects':['read'],'engineering_qualification':False}
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
    if op=='stac.status':return {'schema':'arc.stac-bridge/1','upstream':'0.6','discovery_grammar':'inquiries; inquiry ID | inspect; inquiry ID | history','algorithm_grammar':'algorithms; algorithms | find TEXT; algorithms | method ID','atlas_grammar':'atlas; atlas | find TEXT; atlas | operation ID; atlas | tool ID','workbench_grammar':'desk; desk | focus bring-in/understand/build/follow-through; desk | find TEXT; package ID | contents/gaps','workbench_scope':'Kernel bridge read extension; upstream POSIX grammar unchanged','knowledge_grammar':'source ID | search TEXT | take 5; map ID[@REV] | part REF; map ID | net NET; map ID | trace REF REF; map ID | evidence; map ID | status','execution_authority':'EXISTING_KERNEL','caller':'FORWARDED_WITHOUT_SCOPE_ESCALATION','reference_grammar':'library NS | search TEXT | take 5; library NS | reference ID; library NS | question SUBJECT PROPERTY VARIANT JSON','observation_store':'SHARED_KERNEL_MEMORY_AND_ACTIVITY','legacy_POSIX_CLI':'USER_INVOKED_ONLY_WINDOWS_IO_UNQUALIFIED','local_brain':'EXISTING_LEDGER_BRAIN'}
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
