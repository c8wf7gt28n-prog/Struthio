"""staC 0.2 restricted interpreter over Ledger's authoritative read interfaces.

It never executes shell, arbitrary SQL, LLM-generated code, or privileged tools.
Manufacturer requirements are emitted only after exact reviewed source binding.
"""
from __future__ import annotations
import copy
from hashlib import sha256
from decimal import Decimal, InvalidOperation
from .language import SCHEMA, SCHEMA_04, SCHEMA_05, SCHEMA_06, DIGEST_PROFILE, SIGNATURES, intent_hash, REF, PROPERTY, JOBID
from .source_facts import resolve_fact
from . import knowledge, obligations, witnesses, kernel_witness
from ..engineering_kernel import CAPABILITIES, Principal
from .. import record_io

READ_OPS = frozenset({'links.inspect', 'links.trace', 'records.status',
                      'vendor.status','vendor.facts','vendor.value','vendor.page','ledger.activity',
                      'jobs.get','evidence.read','project.inspect'})


class RunError(ValueError):
    pass


def _kernel_read(kernel, operation, arguments):
    if operation not in READ_OPS or CAPABILITIES.get(operation) != 'read':
        raise RunError('The read-only broker denied operation: ' + str(operation))
    caller = Principal('stac-readonly', frozenset({'read'}), mode='Tutor')
    envelope = kernel.dispatch(operation, arguments, caller)
    if not isinstance(envelope,dict) or not envelope.get('ok'):
        raise RunError('Ledger Kernel refused ' + operation + ': ' + str(envelope.get('error', 'UNKNOWN') if isinstance(envelope,dict) else 'INVALID_REPLY'))
    return envelope['result']


def _sources(result):
    """Native file hashes identify source bytes, not manufacturer design approval."""
    rows=[]
    for path,info in sorted(result.get('source_manifest',{}).items()):
        if not isinstance(info,dict):continue
        rows.append({'path':path, 'sha256':info.get('sha256'),
                     'state':'AVAILABLE' if info.get('sha256') else 'MISSING'})
    return rows


def _provenance(value):
    kind=value['type'];p=value['payload']
    if kind in ('PartInspection','ConnectivityTrace'):
        return {'type':'ProvenanceReport','subject_type':kind,
                'record_state':p.get('state','UNKNOWN'),'native_source_revision':p.get('revision'),
                'source_files':_sources(p),'manufacturer_original_proven':False,
                'physical_operation_proven':False,
                'notes':['Native schematic connectivity does not prove routed copper or physical electrical operation.',
                         'Source hashes identify files; they do not certify engineering compliance.']}
    if kind in ('KernelJobInspection', 'KernelTestWitness'):
        return {'type':'ProvenanceReport', 'subject_type':kind,
                'record_state':p.get('state','UNKNOWN'),
                'job_id':p.get('id',p.get('job_id')),
                'evidence_id':p.get('evidence_id'),
                'job_record_digest':p.get('job_record_digest',p.get('record_digest')),
                'evidence_record_digest':p.get('evidence_record_digest'),
                'native_source_revision':p.get('source_revision',p.get('revision')),
                'source_applicability':p.get('source_applicability','NOT_ASSESSED'),
                'manufacturer_original_proven':False, 'physical_operation_proven':False,
                'notes':['Kernel job/evidence record linkage is not raw artifact readback.',
                         'Recorded tool success or host PASS cannot qualify physical hardware or a named requirement.']}
    if kind=='FactInquiry':
        original=p.get('original_page') if p.get('original_verified') else None
        return {'type':'ProvenanceReport','subject_type':kind,
                'record_state':p.get('state','UNKNOWN'),
                'native_source_revision':p.get('native_source_revision'),
                'component':p.get('component'),'property':p.get('property'),
                'fact_id':p.get('reviewed_fact',{}).get('fact_id') if p.get('reviewed_fact') else None,
                'reviewed_fact':p.get('reviewed_fact'), 'original_page':original,
                'vendor_record_set_sha256':p.get('vendor_record_set_sha256'),
                'source_files':[{'path':path,'sha256':info.get('sha256'),
                                 'state':'AVAILABLE' if info.get('sha256') else 'MISSING'}
                                for path,info in sorted(p.get('native_source_manifest',{}).items()) if isinstance(info,dict)],
                'manufacturer_original_proven':bool(original), 'physical_operation_proven':False,
                'notes':['Manufacturer requirement is not a physical measurement or proof of controller compliance.',
                         'The original-page hash identifies text extracted from a verified original, not a new review.']}
    if kind in ('QualificationAssessment','ScenarioAssessment','PredicateAssessment','EngineeringQuestion','ObligationReport'):
        report=_provenance({'type':'FactInquiry','payload':p['fact_inquiry']})
        report['subject_type']=kind
        report['record_state']=p.get('state','UNKNOWN')
        report['evaluation_scope']=p.get('claim_scope',p.get('applicability'))
        report['physical_operation_proven']=False
        report['notes'].append('Assessments and hypothetical scenarios never grant physical qualification.')
        return report
    if kind in ('ClaimCandidate', 'WitnessCandidate', 'WitnessJudgment'):
        locator = p.get('reviewed_source_witness') if kind == 'WitnessJudgment' else p.get('locator', p.get('claim', {}).get('source_locator'))
        verified = (kind == 'WitnessJudgment' and p.get('state') == 'VERIFIED_SOURCE_REQUIREMENT')
        return {'type':'ProvenanceReport','subject_type':kind,
                'record_state':p.get('state','UNKNOWN'),
                'claim_digest':p.get('claim_digest'),
                'source_locator':locator,
                'manufacturer_original_proven':bool(verified),
                'physical_operation_proven':False,
                'notes':['Only a fresh registered Ledger reader can validate the claimed original source.',
                         'An accepted vendor requirement witness does not establish actual RTL or physical compliance.']}
    if kind=='KnowledgePacket':
        sb=p.get('source_bindings',{})
        return {'type':'ProvenanceReport','subject_type':kind,
                'record_state':p.get('knowledge_state','UNKNOWN'),
                'native_source_revision':p.get('subject',{}).get('native_revision'),
                'manufacturer_original_proven':bool(sb.get('verified_original_page')),
                'physical_operation_proven':False,
                'source_files':sb.get('native_files',[]),
                'original_page':sb.get('verified_original_page'),
                'notes':['Packet is a local-only source index; its text is not automatically authorized for cloud disclosure.']}
    if kind=='ROMStatus':
        return {'type':'ProvenanceReport','subject_type':kind,
                'volumes':[{'volume_id':x.get('volume_id'),'manifest_sha256':x.get('manifest_sha256'),
                            'records':x.get('records'),'mounts':x.get('mounts')}
                           for x in p.get('volumes',[])],
                'manufacturer_original_proven':False,
                'notes':['ROM inventory is not current board compliance evidence.']}
    if kind=='VendorStatus':
        return {'type':'ProvenanceReport','subject_type':kind,
                'vendor_status':p.get('status','UNKNOWN'),
                'notes':['Vendor search metadata alone is not a reviewed electrical requirement.']}
    raise RunError('No provenance report for '+kind)


def _gaps(value):
    kind,p=value['type'],value['payload']
    gaps=[]
    def add(code,msg):
        if not any(g['code']==code for g in gaps):gaps.append({'code':code,'detail':msg})
    if kind in ('KernelJobInspection', 'KernelTestWitness'):
        if kind == 'KernelJobInspection':
            add('UNVERIFIED_JOB_RECORD','A Kernel job must be re-read with its linked evidence before use')
        else:
            if not p.get('evidence_record_correlated'):
                add('KERNEL_EVIDENCE_NOT_CORROBORATED',str(p.get('reason','No consistent evidence')))
            if p.get('state') != 'RECORDED_HOST_PASS':
                add('REGISTERED_PASS_NOT_ESTABLISHED','No explicit passing registered Kernel outcome established')
            if p.get('source_applicability') != 'MATCHES_CURRENT_PROJECT_REVISION':
                add('CURRENT_SOURCE_NOT_MATCHED','Stored job revision is not the accepted current project source')
            for obligation in p.get('outstanding_obligations',[]):
                add(str(obligation),'Recorded Kernel job does not discharge this engineering obligation')
        add('PHYSICAL_NOT_VERIFIED','Host or static result is never an instrumented physical qualification')
    elif kind=='PartInspection':
        if not p.get('physical_measurements',False):add('PHYSICAL_NOT_VERIFIED','No instrumented physical measurement in this Brain Link result')
        if not p.get('routed_connectivity_verified',False):add('ROUTING_NOT_PROVED','Schematic connectivity is not routed copper verification')
        if p.get('state')!='CURRENT':add('SOURCE_REVIEW_REQUIRED','Native source binding not CURRENT')
        if not p.get('requirements'):add('REQUIREMENT_NOT_LINKED','No approved requirement bound to this component in the result')
        if not p.get('source_manifest'):add('NATIVE_SOURCES_UNAVAILABLE','Native source manifest absent')
    elif kind=='ConnectivityTrace':
        trace=p.get('trace',{})
        if not trace.get('electrical_operation_verified',False):add('ELECTRICAL_NOT_VERIFIED','Graph path does not establish electrical operation')
        if not p.get('routed_connectivity_verified',False):add('ROUTING_NOT_PROVED','PCB routing not certified')
        if trace.get('state')!='FOUND':add('SCHEMATIC_PATH_UNRESOLVED','No supported schematic path found')
    elif kind=='FactInquiry':
        if p.get('state')!='REVIEWED_FACT' or not p.get('original_verified'):
            add('REVIEWED_FACT_NOT_BOUND','No reviewed variant-specific original fact bound to this native component')
            add(p.get('reason','UNKNOWN_FACT'), 'Manufacturer source or fitment evidence requires review')
        if p.get('vendor_status')!='AVAILABLE':add('VENDOR_SOURCE_BLOCKED','Vendor source interface unavailable or blocked')
        add('CURRENT_IMPLEMENTATION_NOT_ASSESSED','RTL/firmware implementation and active timing conditions not checked')
        add('PHYSICAL_NOT_VERIFIED','No physical target qualification supplied')
    elif kind in ('QualificationAssessment','ScenarioAssessment','PredicateAssessment'):
        for code in p.get('proof_obligations',[]):add(code,'A separate source-bound observation or review is required')
        if kind in ('ScenarioAssessment','PredicateAssessment'):
            add('HYPOTHETICAL_ONLY','Arithmetic over assumed values cannot establish a test result')
    elif kind in ('EngineeringQuestion', 'ObligationReport'):
        for item in p.get('proof_obligations', p.get('obligations', [])):
            if isinstance(item, dict) and item.get('state') == 'OPEN':
                add(str(item.get('code')), str(item.get('reason', 'Evidence obligation is open')))
        if not p.get('physical_qualification_granted', False):
            add('PHYSICAL_NOT_VERIFIED', 'No physical target qualification established')
    elif kind=='ChallengeReport':
        add('NO_APPROVED_EXPERIMENT','Suggested questions have not become a reviewed tool plan or test')
        add('NO_NEW_EVIDENCE','No engineering tool was executed by challenge')
    elif kind in ('ClaimCandidate', 'WitnessCandidate', 'WitnessJudgment'):
        if p.get('state') != 'VERIFIED_SOURCE_REQUIREMENT':
            add('TRUSTED_SOURCE_WITNESS_NOT_VERIFIED','Source candidate is not a freshly checked Ledger original.')
        for code in p.get('outstanding_obligations', ['CURRENT_IMPLEMENTATION_TIMING', 'REGISTERED_TEST_ORACLE',
                                                     'APPLICABLE_TEST_RESULT', 'PHYSICAL_TARGET_QUALIFICATION']):
            add(str(code),'A separate engineering observation, acceptance rule or qualification is required.')
    elif kind=='KnowledgePacket':
        for item in p.get('unresolved',[]):add(str(item),'An evidence dependency is unresolved')
        if not p.get('reviewed_requirement'):add('REVIEWED_FACT_NOT_BOUND','Packet has no source-qualified numeric requirement')
        add('PHYSICAL_NOT_VERIFIED','Packet carries no physical qualification')
    elif kind=='ROMStatus':
        if not any(v.get('records',0) for v in p.get('volumes',[])):
            add('NO_ARCHIVED_RECORDS','No nonempty attached reference volume reported')
        if not p.get('physical_cd_verified',False):add('PHYSICAL_CD_NOT_VERIFIED','A burned disc has not been read back and verified here')
    elif kind=='VendorStatus':
        if p.get('status')!='AVAILABLE':add('VENDOR_SOURCE_BLOCKED','Vendor knowledge interface status is not AVAILABLE')
    elif kind=='ProvenanceReport':
        if not p.get('manufacturer_original_proven',False):add('ORIGINAL_NOT_CONFIRMED','No manufacturer original validated by this query')
        if not p.get('physical_operation_proven',False):add('PHYSICAL_NOT_VERIFIED','No physical target proof established')
        if p.get('record_state') in ('STALE','UNVERIFIED_EXPORT'):
            add('SOURCE_REVIEW_REQUIRED','Provenance source requires current applicability review')
    return {'type':'GapReport','subject_type':kind,'gaps':gaps,
            'note':'Derived only from the selected result; not a complete design qualification.'}


def _validate_ir(ir):
    """Defense in depth: do not trust caller-provided type/effect declarations."""
    if not isinstance(ir,dict) or set(ir)!={'schema','version','digest_profile','context','binding','nodes','result_type','effects'}:
        raise RunError('Invalid IR fields')
    if (ir['schema'], ir['version']) not in ((SCHEMA, 2), (SCHEMA_04, 4), (SCHEMA_05, 5), (SCHEMA_06, 6)) or ir['digest_profile']!=DIGEST_PROFILE:
        raise RunError('Unrecognized IR schema/version/digest profile')
    if ir['binding']!={'state':'SYMBOLIC_UNPINNED','source_generation':None}:
        raise RunError('Only compiled symbolic instructions may be executed')
    if ir['context'] not in ({'project':'ARC-1','board':'R10'}, {'project':'Ledger','board':'CURRENT'}):
        raise RunError('Only explicit ARC1@R10 or LEDGER@CURRENT context is permitted')
    ledger_context = ir['context']['project'] == 'Ledger'
    nodes=ir['nodes']
    if not isinstance(nodes,list) or not 1<=len(nodes)<=20 or not isinstance(ir['result_type'],str):
        raise RunError('Invalid program node count or result type')
    typ='Context';aggregate=set()
    for i,node in enumerate(nodes):
        if not isinstance(node,dict) or set(node)!={'op','arguments','input_type','output_type','effects'}:
            raise RunError('Unexpected IR node fields')
        if node['op']=='context.select':
            if (i!=0 or node['arguments']!=ir['context'] or node['effects']!=[] or
                node['input_type']!='Context' or node['output_type']!='Context'):
                raise RunError('Invalid context selector')
            typ='Context';continue
        matches=[(verb,s) for verb,s in SIGNATURES.items()
                 if s[3]==node['op'] and typ in s[0] and
                    node['input_type']==typ and node['output_type']==s[1] and
                    node['effects']==list(s[2])]
        if len(matches)!=1:raise RunError('IR type/effect signature mismatch')
        verb=matches[0][0];args=node['arguments']
        if (ledger_context and verb not in ('job','verify-test','why','gaps')) or (not ledger_context and verb in ('job','verify-test')):
            raise RunError('IR context/operation separation failed')
        if not isinstance(args,dict):raise RunError('Invalid IR argument object')
        if verb=='part':
            if set(args)!={'component'} or not isinstance(args['component'],str) or not REF.fullmatch(args['component']):
                raise RunError('Invalid part arguments')
        elif verb=='job':
            if set(args)!={'id'} or not isinstance(args['id'],str) or not JOBID.fullmatch(args['id']):
                raise RunError('Invalid registered Kernel job identifier')
        elif verb=='trace':
            if set(args)!={'start','end'} or any(not isinstance(x,str) or not REF.fullmatch(x) for x in args.values()):
                raise RunError('Invalid trace arguments')
        elif verb=='fact':
            if set(args)!={'property'} or not isinstance(args['property'],str) or not PROPERTY.fullmatch(args['property']):
                raise RunError('Invalid fact arguments')
        elif verb in ('suppose','compare'):
            required={'value_si','unit','dimension'} | ({'relation'} if verb=='compare' else set())
            if (set(args)!=required or args['unit']!='s' or args['dimension']!='time'
                or not isinstance(args['value_si'],str) or
                (verb=='compare' and args['relation'] not in ('<','<=','>','>=','==','!='))):
                raise RunError('Invalid hypothetical number format')
            try:value=Decimal(args['value_si'])
            except (InvalidOperation,ValueError):raise RunError('Invalid hypothetical decimal')
            if not value.is_finite() or not 0<=value<=Decimal('86400') or format(value,'f')!=args['value_si']:
                raise RunError('Hypothetical input must be canonical finite seconds')
        elif args:
            raise RunError('Unexpected arguments for '+verb)
        aggregate.update(node['effects']);typ=node['output_type']
    witness_ops = any(n['op'] in ('stac.claim', 'stac.witness', 'stac.verify', 'stac.compare') for n in nodes)
    question_ops = any(n['op'] in ('stac.question', 'stac.obligations') for n in nodes)
    kernel_ops = any(n['op'] in ('jobs.get','stac.verify-test') for n in nodes)
    version_expected = 6 if kernel_ops else (5 if witness_ops else (4 if question_ops else 2))
    if ir['version'] != version_expected:
        raise RunError('IR schema upgrade or downgrade mismatch')
    if typ!=ir['result_type'] or ir['effects']!=sorted(aggregate) or aggregate-{'read'}:
        raise RunError('IR result/effect mismatch')
    return nodes


def evaluate(ir:dict,kernel)->dict:
    """Execute typed read-only IR against Ledger's fixed Kernel operations."""
    nodes=_validate_ir(ir)
    value={'type':'Context','payload':ir['context']}
    native_revision=None;native_ref=None;fact_used=False;resolved_fact=None;history=[]
    kernel_job_inspection=None;kernel_test_judgment=None
    observed_native={}
    def capture_native(payload):
        for path, row in payload.get('source_manifest', {}).items():
            if isinstance(row, dict):
                observed_native[path] = row.get('sha256')
    for node in nodes:
        operation=node['op'];args=node['arguments']
        if operation=='context.select':
            history.append({'op':operation,'state':'SELECTED'});continue
        if operation=='links.inspect':
            params=dict(args)
            if native_revision:params['expected_revision']=native_revision
            result=_kernel_read(kernel,operation,params)
            if result.get('state')=='STALE':raise RunError('STALE_SOURCE: native source changed')
            if result.get('board_revision')!='R10' or not result.get('revision'):
                raise RunError('Native revision identity unavailable')
            if native_revision and result['revision']!=native_revision:
                raise RunError('STALE_SOURCE: native revision drifted')
            native_revision=result['revision'];native_ref=args['component']
            capture_native(result)
            value={'type':'PartInspection','payload':result}
        elif operation=='links.trace':
            params=dict(args)
            if native_revision:params['expected_revision']=native_revision
            result=_kernel_read(kernel,operation,params)
            if result.get('state')=='STALE':raise RunError('STALE_SOURCE: native source changed')
            if result.get('board_revision')!='R10' or not result.get('revision'):
                raise RunError('Native revision identity unavailable')
            native_revision=result['revision']
            capture_native(result)
            value={'type':'ConnectivityTrace','payload':result}
        elif operation in ('records.status','vendor.status'):
            value={'type':node['output_type'],'payload':_kernel_read(kernel,operation,{})}
        elif operation == 'jobs.get':
            result = kernel_witness.inspect_job(args['id'], lambda op,p:_kernel_read(kernel,op,p))
            kernel_job_inspection = result
            value={'type':'KernelJobInspection','payload':result}
        elif operation == 'stac.verify-test':
            result = kernel_witness.verify_test(value, lambda op,p:_kernel_read(kernel,op,p))
            kernel_test_judgment = result
            value={'type':'KernelTestWitness','payload':result}
        elif operation=='stac.fact':
            fact_used=True
            result=resolve_fact(value['payload'],args['property'],lambda op,p:_kernel_read(kernel,op,p))
            resolved_fact=result if result.get('state')=='REVIEWED_FACT' else None
            value={'type':'FactInquiry','payload':result}
        elif operation=='stac.question':
            value={'type':'EngineeringQuestion','payload':obligations.question(value)}
        elif operation=='stac.obligations':
            value={'type':'ObligationReport','payload':obligations.report(value)}
        elif operation=='stac.claim':
            value={'type':'ClaimCandidate','payload':witnesses.claim_from_fact(value)}
        elif operation=='stac.witness':
            value={'type':'WitnessCandidate','payload':witnesses.witness_from_claim(value)}
        elif operation=='stac.verify':
            result=witnesses.verify_witness(value,lambda op,p:_kernel_read(kernel,op,p))
            if result.get('state')=='VERIFIED_SOURCE_REQUIREMENT':
                resolved_fact=result['fact_inquiry']  # freshly revalidated original
            else:
                resolved_fact=None  # no stale or forged current-source binding
            value={'type':'WitnessJudgment','payload':result}
        elif operation=='stac.assess':
            fact = knowledge._fact(value) if value['type']=='WitnessJudgment' else value['payload']
            value={'type':'QualificationAssessment','payload':knowledge.assess(fact)}
        elif operation=='stac.suppose':
            value={'type':'ScenarioAssessment','payload':knowledge.suppose(value['payload'],args)}
        elif operation=='stac.compare':
            value={'type':'PredicateAssessment','payload':knowledge.compare(value['payload'],args)}
        elif operation=='stac.challenge':
            value={'type':'ChallengeReport','payload':knowledge.challenge(value)}
        elif operation=='stac.packet':
            value={'type':'KnowledgePacket','payload':knowledge.packet(value)}
        elif operation=='stac.why':
            value={'type':'ProvenanceReport','payload':_provenance(value)}
        elif operation=='stac.gaps':
            value={'type':'GapReport','payload':_gaps(value)}
        else:raise RunError('Operation is not in the interpreter allowlist')
        history.append({'op':operation,'state':'COMPLETED','type':value['type']})
    if any(n['op']=='stac.verify' for n in nodes) and resolved_fact is not None:
        checked_vendor=_kernel_read(kernel,'vendor.status',{})
        if (checked_vendor.get('status')!='AVAILABLE' or
            checked_vendor.get('record_set_sha256')!=resolved_fact['vendor_record_set_sha256']):
            raise RunError('VENDOR_SOURCE_DRIFT_AFTER_WITNESS_CHECK')
        # Final original-page barrier: fresh PDF extraction must remain available
        # and retain the same document identity/text across this invocation.
        original=resolved_fact['original_page']
        last=_kernel_read(kernel,'vendor.page',{'document_id':original['document_id'],
                                                'page_index':original['page_index'],
                                                'original':True})
        page=last.get('page') if isinstance(last,dict) else None
        document=last.get('document') if isinstance(last,dict) else None
        if (not isinstance(page,dict) or not isinstance(document,dict) or
            last.get('record_set_sha256')!=resolved_fact['vendor_record_set_sha256'] or
            document.get('source_state')!='CURRENT' or
            document.get('source_sha256')!=original['source_sha256'] or
            document.get('current_sha256')!=original['source_sha256'] or
            page.get('document_id')!=original['document_id'] or
            page.get('page_index')!=original['page_index'] or
            page.get('source_sha256')!=original['source_sha256'] or
            not isinstance(page.get('page_text'),str) or
            sha256(page['page_text'].encode('utf-8')).hexdigest()!=original['original_text_sha256']):
            raise RunError('VENDOR_ORIGINAL_DRIFT_AFTER_WITNESS_CHECK')
    if fact_used and native_ref and native_revision:
        # Source drift during external original-page reads invalidates the bind.
        checked=_kernel_read(kernel,'links.inspect',{'component':native_ref,'expected_revision':native_revision})
        if (checked.get('state')=='STALE' or checked.get('revision')!=native_revision or
            checked.get('board_revision')!='R10'):
            raise RunError('STALE_SOURCE: native inputs changed during fact resolution')
    bound_ir=copy.deepcopy(ir)
    if kernel_test_judgment is not None:
        if kernel_test_judgment.get('evidence_record_correlated'):
            binding={'state':'KERNEL_EVIDENCE_BOUND',
                     'source_generation':kernel_test_judgment['source_revision'],
                     'job_id':kernel_test_judgment['job_id'],
                     'evidence_id':kernel_test_judgment['evidence_id'],
                     'job_record_digest':kernel_test_judgment['job_record_digest'],
                     'evidence_record_digest':kernel_test_judgment['evidence_record_digest']}
            bound_ir['binding']=binding
            digest=record_io.digest(bound_ir)
        else:
            binding={'state':'KERNEL_EVIDENCE_UNRESOLVED', 'source_generation':None}
            digest=None
    elif kernel_job_inspection is not None:
        binding={'state':'KERNEL_JOB_UNVERIFIED','source_generation':None}
        digest=None
    elif resolved_fact is not None:
        binding={'state':'NATIVE_AND_VENDOR_BOUND','source_generation':native_revision,
                 'vendor_record_set_sha256':resolved_fact['vendor_record_set_sha256'],
                 'reviewed_fact_id':resolved_fact['reviewed_fact']['fact_id'],
                 'vendor_original_sha256':resolved_fact['original_page']['source_sha256'],
                 'vendor_page_index':resolved_fact['original_page']['page_index'],
                 'original_text_sha256':resolved_fact['original_page']['original_text_sha256']}
        bound_ir['binding']=binding
        digest=record_io.digest(bound_ir)
    elif fact_used:
        binding={'state':'NATIVE_BOUND_FACT_UNRESOLVED','source_generation':native_revision}
        digest=None
    elif native_revision:
        binding={'state':'SOURCE_BOUND','source_generation':native_revision}
        bound_ir['binding']=binding
        digest=record_io.digest(bound_ir)
    else:
        binding={'state':'LIVE_DYNAMIC','source_generation':None}
        digest=None
    deps = [{'kind':'native_file','path':path,'sha256':sha}
            for path,sha in sorted(observed_native.items())]
    if kernel_test_judgment is not None and kernel_test_judgment.get('evidence_record_correlated'):
        deps.extend([
          {'kind':'kernel_job_record', 'id':kernel_test_judgment['job_id'], 'sha256':kernel_test_judgment['job_record_digest']},
          {'kind':'kernel_evidence_record', 'id':kernel_test_judgment['evidence_id'], 'sha256':kernel_test_judgment['evidence_record_digest']},
        ])
    if resolved_fact is not None:
        original = resolved_fact.get('original_page', {})
        if original.get('source_sha256'):
            deps.append({'kind':'vendor_original','document_id':original.get('document_id'),
                         'sha256':original['source_sha256']})
    return {'schema': ('arc.stac.result/0.6' if ir['version']==6 else ('arc.stac.result/0.5' if ir['version']==5 else ('arc.stac.result/0.4' if ir['version']==4 else 'arc.stac.result/0.2'))),'ok':True,
            'intent_digest':intent_hash(ir),'resolved_program_digest':digest,
            'digest_profile':DIGEST_PROFILE,'binding':binding,
            'result':value,'history':history,'source_dependencies':deps,
            'engineering_authority':'LEDGER_KERNEL_READ_ONLY',
            'model_invoked':False,'physical_qualification_granted':False}
